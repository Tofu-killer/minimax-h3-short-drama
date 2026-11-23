#!/usr/bin/env python3
"""Check this machine can run the skill's QC and post-production scripts - no GPU, no models, about a minute.

    python selfcheck.py                # everything that needs only ffmpeg
    python selfcheck.py --keep work    # keep the generated files to look at

It makes three short synthetic clips with ffmpeg (two shots in one of them, a declared freeze tail in
another), writes a matching storyboard, and runs the real scripts on them: validate_episode ->
build_prompts -> qc_probe (cut check) -> contact_sheet -> make_edl -> retime_subtitles and qc_dialogue (fed
ready-made word timings, so no speech model is needed) -> voice_check -> mix_episode (with music and a burned
subtitle) -> export_otio / export_capcut_draft when their packages are installed. Each step prints PASS,
FAIL or SKIP with the reason. Optional packages are reported, not required.

Run it once after installing the skill, and again after changing ffmpeg or Python. It does not test
ComfyUI, speech recognition itself or face recognition - only that the tool chain works here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()
HERE = Path(__file__).resolve().parent
RESULTS: list[tuple[str, str, str]] = []


def record(name: str, status: str, note: str = "") -> None:
    RESULTS.append((name, status, note))
    print(f"{status:4s} {name}" + (f" - {note}" if note else ""), flush=True)


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def script(name: str, args: list[str], cwd: Path, ok_codes=(0,)) -> tuple[bool, str]:
    r = run([sys.executable, str(HERE / name), *args], cwd)
    tail = (r.stdout.strip().splitlines() or [""])[-1] if r.returncode in ok_codes else \
        " | ".join((r.stderr.strip() or r.stdout.strip()).splitlines()[-3:])
    return r.returncode in ok_codes, tail[:300]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--keep", help="keep the working files in this folder")
    a = ap.parse_args()

    print(f"python {sys.version.split()[0]} on {sys.platform}")
    if sys.version_info < (3, 10):
        record("python >= 3.10", "FAIL", "the scripts use 3.10 syntax")
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        if not path:
            record(tool, "FAIL", "not on PATH - install ffmpeg (https://ffmpeg.org/download.html) and reopen the terminal")
        else:
            ver = (run([tool, "-version"], HERE).stdout.splitlines() or ["?"])[0]
            record(tool, "PASS", ver[:70])
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        sys.exit(1)
    filters = run(["ffmpeg", "-hide_banner", "-filters"], HERE).stdout
    for f, why in (("drawtext", "time stamps on contact sheets"), ("subtitles", "burning subtitles"),
                   ("loudnorm", "loudness measurement"), ("alimiter", "limiter"), ("sidechaincompress", "music ducking fallback")):
        record(f"ffmpeg filter {f}", "PASS" if f" {f} " in filters else "FAIL", "" if f" {f} " in filters else f"needed for {why}: use a full ffmpeg build")
    for mod, why in (("faster_whisper", "qc_dialogue.py, retime_subtitles.py"), ("pypinyin", "homophone-proof line matching"),
                     ("cv2", "identity_gate.py, identity_gate_anime.py"), ("numpy", "identity gates, voice_check.py, faster-whisper"),
                     ("onnxruntime", "identity_gate_anime.py"),
                     ("pyJianYingDraft", "export_capcut_draft.py"), ("opentimelineio", "export_otio.py")):
        have = importlib.util.find_spec(mod) is not None
        record(f"optional package {mod}", "PASS" if have else "SKIP", "" if have else f"not installed (only needed for {why})")
    sys.path.insert(0, str(HERE / "h3lib"))
    import signals  # noqa: E402
    font = signals.find_font()
    record("font for stamps", "PASS" if font else "SKIP", str(font) if font else "no TrueType font found: sheets will be unstamped (set H3_QC_FONT)")
    skill_md = HERE.parent / "SKILL.md"
    if skill_md.exists():                                  # the limits an installer checks before it accepts the skill
        head = skill_md.read_text(encoding="utf-8").split("\n---", 1)[0].splitlines()
        size = {k: len(line.split(":", 1)[1].strip()) for line in head for k in ("description", "compatibility") if line.startswith(k + ":")}
        over = [f"{k} {size[k]} > {cap}" for k, cap in (("description", 1024), ("compatibility", 500)) if size.get(k, 0) > cap]
        record("skill header within the install limits", "FAIL" if over else "PASS",
               "; ".join(over) if over else f"description {size.get('description', 0)}/1024, compatibility {size.get('compatibility', 0)}/500 characters")

    with tempfile.TemporaryDirectory() as td:
        work = Path(a.keep).resolve() if a.keep else Path(td)
        work.mkdir(parents=True, exist_ok=True)
        (work / "selects").mkdir(exist_ok=True)
        (work / "bible").mkdir(exist_ok=True)
        # ---- synthetic material ------------------------------------------------------------------
        def clip(name: str, graph: str, seconds: float, tone: int) -> bool:
            # a tone with harmonics, so the pitch check has something voice-like to read
            voice = "+".join(f"{0.24 / k:.3f}*sin(2*PI*{tone * k}*t)" for k in range(1, 6))
            r = run(["ffmpeg", "-v", "error", "-y", "-filter_complex",
                     f"{graph};aevalsrc='{voice}':d={seconds}:s=32000,aformat=channel_layouts=stereo[a]",
                     "-map", "[v]", "-map", "[a]", "-t", f"{seconds}", "-r", "24", "-c:v", "libx264", "-preset", "ultrafast",
                     "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "32000", str(work / "selects" / name)], work)
            return r.returncode == 0
        ok = clip("s01.mp4", "testsrc2=s=1344x768:r=24:d=4[v]", 4, 180)
        ok &= clip("s02.mp4", "testsrc2=s=1344x768:r=24:d=3[x];mandelbrot=s=1344x768:r=24,trim=duration=3,setpts=PTS-STARTPTS[y];"
                             "[x][y]concat=n=2:v=1:a=0[v]", 6, 150)
        ok &= clip("s03.mp4", "smptebars=s=1344x768:r=24:d=4,noise=alls=20:allf=t,trim=duration=4,setpts=PTS-STARTPTS[m];"
                             "[m]tpad=stop_mode=clone:stop_duration=1[v]", 5, 220)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=20,tremolo=f=3:d=0.7", "-ar", "44100",
             str(work / "music.wav")], work)
        for n in ("face.png", "room.png"):
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=512x512:d=1", "-frames:v", "1", str(work / "bible" / n)], work)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1344x768:d=1", "-frames:v", "1", str(work / "bible" / "first_s03.png")], work)
        shutil.copyfile(work / "bible" / "first_s03.png", work / "bible" / "key_s02_2.png")
        record("make synthetic clips", "PASS" if ok else "FAIL", "" if ok else "ffmpeg could not encode test clips (libx264 / aac missing?)")
        if not ok:
            sys.exit(1)

        cjk = signals.cjk_fonts()
        record("font with Chinese glyphs for burned subtitles", "PASS" if cjk else "FAIL",
               cjk[0] if cjk else "none found: burned subtitles would be empty boxes - install one (Linux: fonts-noto-cjk; "
                                   "Windows and macOS ship one) or pass --font to retime_subtitles.py")

        # three scripts turn "seconds asked for" into "frames H3 really makes" (17k+5): they have to agree, or a
        # correctly generated take is reported as the wrong length
        try:
            def load(name):
                spec = importlib.util.spec_from_file_location(f"_selfcheck_{name}", Path(__file__).parent / f"{name}.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
            sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
            import storyboard as _sb
            probe_mod, lint_mod = load("qc_probe"), load("lint_prompt")
            bad = [sec for sec in range(4, 16)
                   if not (abs(probe_mod.grid_seconds(sec) - _sb.frames_for_seconds(sec) / 24.0) < 1e-6
                           and abs(lint_mod.effective_seconds(sec) - _sb.frames_for_seconds(sec) / 24.0) < 1e-6)]
            record("frame grid (17k+5) agrees across validator, linter and qc_probe", "FAIL" if bad else "PASS",
                   f"disagree at {bad} s" if bad else f"13 s -> {_sb.frames_for_seconds(13)} frames = {_sb.frames_for_seconds(13) / 24:.3f} s")
        except Exception as e:  # noqa: BLE001
            record("frame grid (17k+5) agrees across validator, linter and qc_probe", "FAIL", f"{type(e).__name__}: {e}")

        def shot(i, start, framing, action, text=None):
            d = {"index": i, "start": start, "framing": framing, "camera": "The camera holds a static shot",
                 "action": action, "on_screen_characters": ["hero"]}
            if text:
                d["dialogue"] = [{"speaker": "hero", "language": "Chinese", "text": text}]
            return d
        ep = {"title": "selfcheck", "ratio": "16:9", "style": "Live-action, cinematic",
              "characters": [{"id": "hero", "name": "Hero", "identity_phrase": "a tall man in a grey coat", "reference_images": ["bible/face.png"]}],
              "scenes": [{"id": "room", "name": "the test room", "description": "A plain room with one window", "reference_images": ["bible/room.png"]}],
              "segments": [
                  {"id": "s01", "duration": 4, "scene_id": "room", "character_ids": ["hero"], "soundscape": "A steady electrical hum fills the room.",
                   "continuity": "Opening segment: establish the room and the grey coat.", "end_state": "Hero stands at frame centre facing the window, hands at his sides.",
                   "shots": [shot(1, 0, "a wide shot of the room", "Hero walks from the door to the window and stops there, looking out.")]},
                  {"id": "s02", "duration": 6, "scene_id": "room", "character_ids": ["hero"], "soundscape": "The hum continues, a chair creaks once.",
                   "continuity": "Hero stands at frame centre facing the window, hands at his sides.", "end_state": "Hero sits on the chair at frame left, facing the camera.",
                   "shots": [shot(1, 0, "a medium shot from behind Hero", "Hero turns from the window toward the chair and walks to it slowly."),
                             dict(shot(2, 3.0, "a close-up on Hero's face", "Hero sits down, looks into the lens and speaks one calm sentence.", "开始吧"),
                                  keyframe="bible/key_s02_2.png", keyframe_note="{hero} seated, facing the lens")]},
                  {"id": "s03", "duration": 5, "scene_id": "room", "character_ids": ["hero"], "soundscape": "The hum fades under a soft breath.",
                   "first_frame": "bible/first_s03.png",
                   "continuity": "Hero sits on the chair at frame left, facing the camera.", "end_state": "Hero sits still at frame left, eyes closed.",
                   "shots": [dict(shot(1, 0, "a medium close-up on Hero", "Hero breathes out, lowers his shoulders and closes his eyes, then holds still."), end_hold=True)]}]}
        (work / "ep.json").write_text(json.dumps(ep, ensure_ascii=False, indent=1), encoding="utf-8")

        # ---- the real scripts -----------------------------------------------------------------------
        ok, note = script("validate_episode.py", ["ep.json", "--rhythm"], work)
        record("validate_episode.py", "PASS" if ok else "FAIL", note)
        ok, note = script("build_prompts.py", ["ep.json", "--out", "prompts"], work)
        record("build_prompts.py", "PASS" if ok else "FAIL", note)
        ok, note = script("lint_prompt.py", ["prompts/s02.txt", "--seconds", "6", "--images", "3", "--audios", "0"], work)
        record("lint_prompt.py", "PASS" if ok else "FAIL", note)

        # a mistyped path or a broken JSON file must end in one line, not in a Python traceback
        (work / "broken.json").write_text('{"segments": ', encoding="utf-8")
        slips = [run([sys.executable, str(HERE / "validate_episode.py"), "no_such_file.json"], work),
                 run([sys.executable, str(HERE / "mix_episode.py"), "broken.json", "--out", "x.mp4"], work)]
        plain = all(r.returncode == 2 and "Traceback" not in (r.stdout + r.stderr) for r in slips)
        record("a wrong path or broken JSON ends in one line", "PASS" if plain else "FAIL",
               "" if plain else " | ".join((r.stderr.strip() or r.stdout.strip())[-120:] for r in slips))
        (work / "broken.json").unlink()

        # the linter must report a broken prompt, not crash on it: full-width brackets are the classic paste accident
        (work / "prompts" / "broken.txt").write_text(
            "integrated_multimodal_description: [Shot 1] Live-action, a medium shot of a man （the doctor） who stops at the door. "
            "The camera holds a static shot.\n\noverall_soundscape: A quiet room tone.\n\nnon_diegetic_music: N/A\n", encoding="utf-8")
        r = run([sys.executable, str(HERE / "lint_prompt.py"), "prompts/broken.txt", "--seconds", "5"], work)
        caught = r.returncode == 1 and "full-width bracket" in r.stdout and "Traceback" not in (r.stdout + r.stderr)
        record("lint_prompt.py rejects a prompt with full-width brackets", "PASS" if caught else "FAIL",
               "" if caught else (r.stderr.strip() or r.stdout.strip())[-200:])
        (work / "prompts" / "broken.txt").unlink()

        # comfy_submit.py without a server: a dry run must wire the references in the numbered order and pin the first frame
        wf = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
              "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax"}},
              "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}},
              "5": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
              "3": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {"clip": ["2", 0], "vae": ["4", 0], "audio_vae": ["5", 0], "prompt": "",
                                                                          "width": 1344, "height": 768, "length": 124, "ref_image_size": "match"}},
              "10": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1}},
              "11": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
              "6": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "strength_model": 1.0,
                                                                    "lora_name": "minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors"}},
              "12": {"class_type": "BasicScheduler", "inputs": {"model": ["6", 0], "scheduler": "simple", "steps": 8, "denoise": 1.0}},
              "13": {"class_type": "BasicGuider", "inputs": {"model": ["6", 0], "conditioning": ["3", 0]}},
              "14": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["10", 0], "guider": ["13", 0], "sampler": ["11", 0],
                                                                      "sigmas": ["12", 0], "latent_image": ["3", 1]}}}
        (work / "wf.api.json").write_text(json.dumps(wf), encoding="utf-8")
        base = [sys.executable, str(HERE / "comfy_submit.py"), "wf.api.json", "--server", "http://127.0.0.1:9", "--media", "prompts/s03.media.json",
                "--batch", "2", "--dry-run"]
        r = run(base + ["--write-workflow", "qc/wired.api.json"], work)
        r2 = run(base + ["--anchor", "--write-workflow", "qc/wired_anchor.api.json"], work)
        try:
            wired = json.loads((work / "qc/wired.api.json").read_text(encoding="utf-8"))
            h3 = wired["3"]["inputs"]
            pics = [wired[h3[k][0]]["inputs"]["image"] for k in sorted(k for k in h3 if k.startswith("ref_images."))]
            plain = not any(v["class_type"] == "MiniMaxH3AddGuide" for v in wired.values()) and wired["13"]["inputs"]["conditioning"] == ["3", 0]
            pinned_wf = json.loads((work / "qc/wired_anchor.api.json").read_text(encoding="utf-8"))
            guide = [k for k, v in pinned_wf.items() if v["class_type"] == "MiniMaxH3AddGuide"]
            pinned = len(guide) == 1 and pinned_wf["13"]["inputs"]["conditioning"] == [guide[0], 0] \
                and pinned_wf[pinned_wf[guide[0]]["inputs"]["image"][0]]["inputs"]["image"] == pics[0] \
                and pinned_wf[guide[0]]["inputs"]["frame_idx"] == 0
            # the two-shot segment carries a keyframe for shot 2 (cut at 3.0 s): a <Picture N> by default, pinned at frame 72 with --anchor
            r3 = run([sys.executable, str(HERE / "comfy_submit.py"), "wf.api.json", "--server", "http://127.0.0.1:9", "--media", "prompts/s02.media.json",
                      "--dry-run", "--anchor", "--write-workflow", "qc/wired_key.api.json"], work)
            key_wf = json.loads((work / "qc/wired_key.api.json").read_text(encoding="utf-8"))
            kg = [v["inputs"] for v in key_wf.values() if v["class_type"] == "MiniMaxH3AddGuide"]
            keyed = r3.returncode == 0 and len(kg) == 1 and kg[0]["frame_idx"] == 72 \
                and key_wf[kg[0]["image"][0]]["inputs"]["image"].startswith("key_s02_2_") \
                and "keyframe corresponds to <Picture 1>" in (work / "prompts/s02.txt").read_text(encoding="utf-8")
            good = r.returncode == 0 and r2.returncode == 0 and pics[0].startswith("first_s03_") and len(pics) == 3 and plain and pinned \
                and h3["length"] == 124 and "2 take(s)" in r.stdout and keyed
            record("comfy_submit.py --dry-run (references in order; --anchor pins the first frame and a shot keyframe)", "PASS" if good else "FAIL",
                   f"pictures {pics}; with --anchor: guide {guide}, keyframe at frame {kg[0]['frame_idx']}" if good
                   else (r.stderr.strip() or r2.stderr.strip() or r3.stderr.strip() or r.stdout.strip())[-300:])
        except Exception as e:  # noqa: BLE001
            record("comfy_submit.py --dry-run", "FAIL", f"{type(e).__name__}: {e}; {(r.stderr.strip() or r.stdout.strip())[-200:]}")

        # with no server the checks that need none still run: a frame count off the grid stops the batch, and a seed
        # the workflow takes from a Primitive node (templates often wire it so) can still be set
        try:
            off = json.loads(json.dumps(wf)); off["3"]["inputs"]["length"] = 240
            (work / "wf_off.api.json").write_text(json.dumps(off), encoding="utf-8")
            r = run([sys.executable, str(HERE / "comfy_submit.py"), "wf_off.api.json", "--server", "http://127.0.0.1:9",
                     "--out", "qc/static", "--dry-run"], work)
            said = r.stdout + r.stderr
            stopped = r.returncode == 2 and "17k+5" in said and "226" in said and "243" in said and "Traceback" not in said
            prim = json.loads(json.dumps(wf)); prim["40"] = {"class_type": "PrimitiveInt", "inputs": {"value": 77}}
            prim["10"]["inputs"]["noise_seed"] = ["40", 0]
            (work / "wf_prim.api.json").write_text(json.dumps(prim), encoding="utf-8")
            r2 = run([sys.executable, str(HERE / "comfy_submit.py"), "wf_prim.api.json", "--server", "http://127.0.0.1:9",
                      "--media", "prompts/s03.media.json", "--batch", "2", "--dry-run", "--write-workflow", "qc/wired_prim.api.json"], work)
            seeded = r2.returncode == 0 and "seed 77 " in r2.stdout and "seed 78 " in r2.stdout \
                and json.loads((work / "qc/wired_prim.api.json").read_text(encoding="utf-8"))["10"]["inputs"]["noise_seed"] == ["40", 0]
            record("comfy_submit.py without a server (stops on a frame count off the grid; sets a seed held by a Primitive node)",
                   "PASS" if stopped and seeded else "FAIL",
                   "" if stopped and seeded else f"grid check {stopped}, primitive seed {seeded}: {(said.strip() or r2.stderr.strip() or r2.stdout.strip())[-240:]}")
        except Exception as e:  # noqa: BLE001
            record("comfy_submit.py without a server", "FAIL", f"{type(e).__name__}: {e}")

        # the workflows shipped with the skill: each takes a segment of the matching mode, at the settings the docs state
        flows = HERE.parent / "assets" / "workflows"
        if flows.is_dir():
            try:
                notes = []
                for name, media_file, want in (("h3_ref2va.api.json", "prompts/s03.media.json", ("1344x768", "8 steps", "ref2v_turbo_8step_v1.1_768p")),
                                               ("h3_ref2va_sage.api.json", "prompts/s02.media.json", ("1344x768", "8 steps", "sage_attention auto")),
                                               ("h3_ref2va_refine.api.json", "prompts/s01.media.json", ("second pass to 1920x1088", "steps_override 2")),
                                               ("h3_ref2va_sage_refine.api.json", "prompts/s01.media.json", ("second pass to 1920x1088", "sage_attention auto"))):
                    r = run([sys.executable, str(HERE / "comfy_submit.py"), str(flows / name), "--server", "http://127.0.0.1:9",
                             "--media", media_file, "--dry-run"], work)
                    if r.returncode != 0 or not all(w in r.stdout for w in want) or "advice:" in r.stdout:
                        notes.append(f"{name}: {(r.stderr.strip() or r.stdout.strip())[-200:]}")
                r = run([sys.executable, str(HERE / "comfy_submit.py"), str(flows / "h3_ref2va.api.json"), "--server", "http://127.0.0.1:9",
                         "--media", "prompts/s03.media.json", "--set", "146.value=false", "--dry-run"], work)
                if r.returncode != 0 or "20 steps" not in r.stdout or "LoraLoaderModelOnly" in r.stdout:
                    notes.append(f"h3_ref2va with the LoRA switched off: {(r.stderr.strip() or r.stdout.strip())[-200:]}")
                # --keep-latent adds the split and the two SaveLatent nodes; --from-latent feeds the refine node from kept files
                r = run([sys.executable, str(HERE / "comfy_submit.py"), str(flows / "h3_ref2va.api.json"), "--server", "http://127.0.0.1:9",
                         "--media", "prompts/s03.media.json", "--keep-latent", "--dry-run", "--write-workflow", "qc/keep.api.json"], work)
                kept_wf = json.loads((work / "qc/keep.api.json").read_text(encoding="utf-8"))
                saves = [v for v in kept_wf.values() if v["class_type"] == "SaveLatent"]
                split = [v for v in kept_wf.values() if v["class_type"] == "LTXVSeparateAVLatent"]
                if r.returncode != 0 or len(saves) != 2 or len(split) != 1 or split[0]["inputs"]["av_latent"] != ["125", 0]:
                    notes.append(f"--keep-latent: {(r.stderr.strip() or r.stdout.strip())[-200:]}")
                (work / "kept_take").mkdir(exist_ok=True)
                for n in ("h3_video_00001_.latent", "h3_audio_00001_.latent"):
                    (work / "kept_take" / n).write_bytes(b"selfcheck")
                r = run([sys.executable, str(HERE / "comfy_submit.py"), str(flows / "h3_ref2va_refine.api.json"), "--server", "http://127.0.0.1:9",
                         "--media", "prompts/s03.media.json", "--from-latent", "kept_take", "--dry-run", "--write-workflow", "qc/from.api.json"], work)
                from_wf = json.loads((work / "qc/from.api.json").read_text(encoding="utf-8"))
                src = from_wf["300"]["inputs"]["latent"]
                if r.returncode != 0 or from_wf[src[0]]["class_type"] != "LTXVConcatAVLatent" or "kept first-pass latent" not in r.stdout \
                        or "BasicScheduler" in r.stdout:
                    notes.append(f"--from-latent: {(r.stderr.strip() or r.stdout.strip())[-200:]}")
                # stills: what the workflow still lacks is refused with the --set that supplies it; a complete job shows size and prompt
                (work / "bust.txt").write_text("a studio portrait of a tall man in a grey coat, soft window light", encoding="utf-8")
                t2i = [sys.executable, str(HERE / "comfy_submit.py"), str(flows / "qwen21_t2i.api.json"), "--server", "http://127.0.0.1:9", "--out", "qc/t2i", "--dry-run"]
                edit = [sys.executable, str(HERE / "comfy_submit.py"), str(flows / "qwen_edit2511_2ref.api.json"), "--server", "http://127.0.0.1:9", "--out", "qc/edit",
                        "--dry-run", "--set", "170:151.prompt=Keep the same person as Picture 1, in the room of Picture 2", "--set", "41.image=@bible/face.png"]
                for what, r, need in (("an empty prompt", run(t2i, work), "prompt is empty"),
                                      ("a misspelt --set name", run(t2i + ["--set", "459:452.text=@bust.txt", "--set", "459:452.prompt=@bust.txt"], work), "no input `text`"),
                                      ("a picture slot left open", run(edit, work), "no file given yet")):
                    if r.returncode != 2 or need not in (r.stdout + r.stderr):
                        notes.append(f"stills, {what}: {(r.stderr.strip() or r.stdout.strip())[-160:]}")
                r = run(edit + ["--set", "42.image=@bible/room.png"], work)
                if r.returncode != 0 or "1344x768" not in r.stdout or "prompt (" not in r.stdout or "image2" not in r.stdout:
                    notes.append(f"stills, a complete edit job: {(r.stderr.strip() or r.stdout.strip())[-200:]}")
                r = run([sys.executable, str(HERE / "lint_prompt.py"), str(flows / "smoke_test_prompt.txt"), "--seconds", "5", "--images", "0", "--audios", "0"], work)
                if r.returncode != 0:
                    notes.append(f"smoke_test_prompt.txt does not lint: {r.stdout.strip()[-160:]}")
                broken = [f.name for f in sorted(flows.glob("*.api.json"))
                          if not all(isinstance(v, dict) and "class_type" in v and "inputs" in v for v in json.loads(f.read_text(encoding="utf-8")).values())]
                good = not notes and not broken and len(list(flows.glob("*.api.json"))) >= 11
                record("shipped workflows (draft, Sage, refine, LoRA switch, kept latent; stills refuse what is still missing)", "PASS" if good else "FAIL",
                       f"{len(list(flows.glob('*.api.json')))} workflow files" if good else "; ".join(notes + broken)[:300])
            except Exception as e:  # noqa: BLE001
                record("shipped workflows", "FAIL", f"{type(e).__name__}: {e}")

        # a misspelt field would otherwise be ignored in silence, and a negation is the instruction the model most often draws
        typo = json.loads(json.dumps(ep))
        typo["segments"][1]["shots"][0]["on_screen_charcters"] = typo["segments"][1]["shots"][0]["on_screen_characters"]
        typo["segments"][0]["shots"][0]["action"] = "Hero walks from the door to the window and does not look back."
        (work / "ep_typo.json").write_text(json.dumps(typo, ensure_ascii=False, indent=1), encoding="utf-8")
        r = run([sys.executable, str(HERE / "validate_episode.py"), "ep_typo.json"], work)
        warned = r.returncode == 0 and "did you mean 'on_screen_characters'" in r.stdout and "negation" in r.stdout
        record("validate_episode.py warns about a misspelt field and a negation", "PASS" if warned else "FAIL",
               "" if warned else (r.stderr.strip() or r.stdout.strip())[-300:])

        # an accepted segment keeps the prompt its take was made from: a same-seed refine run has to start from it
        try:
            script("build_prompts.py", ["ep.json", "--out", "prompts_kept"], work)
            before = (work / "prompts_kept/s01.txt").read_bytes()
            later = json.loads(json.dumps(ep))
            later["segments"][0].update(status="accepted", observed_end_state="Hero stands at frame centre facing the window, hands at his sides.")
            later["segments"][0]["shots"][0]["action"] = "Hero walks from the door to the window, stops there and folds his arms."
            (work / "ep_later.json").write_text(json.dumps(later, ensure_ascii=False, indent=1), encoding="utf-8")
            r = run([sys.executable, str(HERE / "build_prompts.py"), "ep_later.json", "--out", "prompts_kept"], work)
            same = (work / "prompts_kept/s01.txt").read_bytes() == before and "kept as they are: s01" in r.stdout
            r = run([sys.executable, str(HERE / "build_prompts.py"), "ep_later.json", "--out", "prompts_kept", "--only", "s01"], work)
            rebuilt = (work / "prompts_kept/s01.txt").read_bytes() != before
            record("build_prompts.py leaves an accepted segment's prompt alone (rebuilds it with --only)", "PASS" if same and rebuilt else "FAIL",
                   "" if same and rebuilt else f"kept {same}, rebuilt on request {rebuilt}: {(r.stderr.strip() or r.stdout.strip())[-200:]}")
        except Exception as e:  # noqa: BLE001
            record("build_prompts.py leaves an accepted segment's prompt alone", "FAIL", f"{type(e).__name__}: {e}")

        # plan first, reconcile after: a take confirmed with --as-planned leaves the next segment's prompt (and its drafts) valid
        try:
            flow = json.loads(json.dumps(ep))
            flow["segments"][1]["continuity"] = "@observed"
            (work / "ep_flow.json").write_text(json.dumps(flow, ensure_ascii=False, indent=1), encoding="utf-8")
            r1 = run([sys.executable, str(HERE / "build_prompts.py"), "ep_flow.json", "--out", "prompts_flow"], work)
            r2 = run([sys.executable, str(HERE / "build_prompts.py"), "ep_flow.json", "--out", "prompts_flow", "--allow-planned"], work)
            planned = (work / "prompts_flow/s02.txt").read_bytes()
            r3 = run([sys.executable, str(HERE / "observe_take.py"), "selects/s01.mp4", "--episode", "ep_flow.json", "--segment", "s01",
                      "--as-planned", "--out", "qc/observe_flow"], work)
            r4 = run([sys.executable, str(HERE / "build_prompts.py"), "ep_flow.json", "--out", "prompts_flow"], work)
            kept = "WAITING" in r1.stdout and "planned end of s01" in r2.stdout and r3.returncode == 0 \
                and (work / "prompts_flow/s02.txt").read_bytes() == planned and "[unchanged]" in r4.stdout
            r5 = run([sys.executable, str(HERE / "observe_take.py"), "selects/s01.mp4", "--episode", "ep_flow.json", "--segment", "s01",
                      "--write", "Hero stands by the door with his back to the window, one hand on the handle.", "--confidence", "medium",
                      "--deviation", "he went to the door, not the window", "--out", "qc/observe_flow"], work)
            r6 = run([sys.executable, str(HERE / "build_prompts.py"), "ep_flow.json", "--out", "prompts_flow"], work)
            changed = r5.returncode == 0 and "CHANGED since the last build" in r6.stdout
            record("plan first, reconcile after (--allow-planned, observe_take --as-planned, change report)", "PASS" if kept and changed else "FAIL",
                   "" if kept and changed else f"kept {kept}, change reported {changed}: {(r4.stdout.strip() + ' | ' + r6.stdout.strip())[-260:]}")
        except Exception as e:  # noqa: BLE001
            record("plan first, reconcile after", "FAIL", f"{type(e).__name__}: {e}")

        # QC over a folder looks at each take once: superseded takes and trimmed copies are left out, a file named alone is not
        both, n_skipped = signals.live_takes([Path("t/s01_1/a.mp4"), Path("t/s01_1/a_trimmed.mp4"), Path("t/s01_1/_prev_ab/a.mp4")])
        alone, _n = signals.live_takes([Path("t/s01_1/a_trimmed.mp4")])
        once = [x.name for x in both] == ["a.mp4"] and n_skipped == 2 and [x.name for x in alone] == ["a_trimmed.mp4"]
        record("QC counts each take once (superseded takes and trimmed copies left out)", "PASS" if once else "FAIL",
               "" if once else f"{both}, {alone}")

        r = run([sys.executable, str(HERE / "qc_probe.py"), "selects/*.mp4", "--episode", "ep.json", "--freeze-tail", "1.0",
                 "--expect-size", "1344x768", "--out", "qc/probe"], work)
        try:
            rows = {Path(x["file"]).stem: x for x in json.loads((work / "qc/probe/probe_report.json").read_text(encoding="utf-8"))}
            cuts_ok = rows["s01"]["cuts"] == [] and len(rows["s02"]["cuts"]) == 1 and abs(rows["s02"]["cuts"][0] - 3.0) < 0.2 \
                and rows["s02"]["cut_check"]["ok"]
            record("qc_probe.py (cut found at 3.0 s, matches the storyboard)", "PASS" if cuts_ok else "FAIL",
                   f"cuts: s01 {rows['s01']['cuts']}, s02 {rows['s02']['cuts']}, s03 {rows['s03']['cuts']}")
        except Exception as e:  # noqa: BLE001
            record("qc_probe.py", "FAIL", f"{type(e).__name__}: {e}; {r.stderr.strip()[-200:]}")

        ok, note = script("contact_sheet.py", ["selects/s02.mp4", "--out-dir", "qc/sheets"], work)
        record("contact_sheet.py", "PASS" if ok and (work / "qc/sheets/s02_sheet.png").exists() else "FAIL", note)
        ok, note = script("extract_tail_frame.py", ["selects/s02.mp4", "--out", "qc/after_cut.png", "--after-cut", "1"], work)
        record("extract_tail_frame.py --after-cut", "PASS" if ok and "after cut 1" in note else "FAIL", note)

        ok, note = script("make_edl.py", ["ep.json", "--selects", "selects", "--out", "edit/ep.edl.json"], work)
        record("make_edl.py", "PASS" if ok else "FAIL", note)
        if ok:
            edl = json.loads((work / "edit/ep.edl.json").read_text(encoding="utf-8"))
            tail_cut = edl["segments"][2]["out_frame"] == edl["segments"][2]["frames_total"] - 24
            record("make_edl.py cut the declared 1 s freeze tail", "PASS" if tail_cut else "FAIL",
                   f"s03 uses frames [{edl['segments'][2]['in_frame']}, {edl['segments'][2]['out_frame']}) of {edl['segments'][2]['frames_total']}")
            edl["music"] = {"file": "music.wav", "gain_db": -10, "loop": True}
            (work / "edit/ep.edl.json").write_text(json.dumps(edl, ensure_ascii=False, indent=1), encoding="utf-8")
            # word timings a recogniser would give for the one line, so the subtitle / dialogue-QC plumbing runs without a model
            (work / "units").mkdir(exist_ok=True)
            units = [{"text": "开", "start": 3.5, "end": 3.8}, {"text": "始", "start": 3.8, "end": 4.1}, {"text": "吧", "start": 4.1, "end": 4.5}]
            (work / "units/s02.units.json").write_text(json.dumps(units, ensure_ascii=False), encoding="utf-8")
            ok, note = script("retime_subtitles.py", ["edit/ep.edl.json", "--out", "subs/ep", "--aligner", "units", "--units-dir", "units"], work)
            edl = json.loads((work / "edit/ep.edl.json").read_text(encoding="utf-8"))
            ln = edl["segments"][1]["lines"][0]
            timed = ok and ln.get("start") is not None and abs(ln["start"] - 3.42) < 0.1 and (work / "subs/ep.ass").exists()
            record("retime_subtitles.py (text from the script, times from word timings, written back)", "PASS" if timed else "FAIL",
                   f"line at {ln.get('start')}-{ln.get('end')} s of its segment" if ok else note)
            ok, note = script("qc_dialogue.py", ["--episode", "ep.json", "--targets", "selects/s02.mp4", "--out", "qc/dialogue",
                                                 "--aligner", "units", "--units-dir", "units"], work)
            record("qc_dialogue.py (plumbing only - recognition itself is not tested here)", "PASS" if ok and "pass" in note or "warn" in note else "FAIL", note)
            if importlib.util.find_spec("faster_whisper"):
                try:
                    import faster_whisper  # noqa: F401
                    record("faster-whisper imports", "PASS", "the first real run downloads the model (small: about 500 MB)")
                except Exception as e:  # noqa: BLE001
                    record("faster-whisper imports", "FAIL", f"{type(e).__name__}: {e}")
            if importlib.util.find_spec("numpy"):
                r = run([sys.executable, str(HERE / "voice_check.py"), "edit/ep.edl.json", "--out", "qc/voice"], work)
                try:
                    f0 = json.loads((work / "qc/voice/voice_report.json").read_text(encoding="utf-8"))["lines"][0]["f0_hz"]
                    record("voice_check.py (reads the 150 Hz test voice)", "PASS" if f0 and abs(f0 - 150) < 8 else "FAIL", f"measured {f0} Hz")
                except Exception as e:  # noqa: BLE001
                    record("voice_check.py", "FAIL", f"{type(e).__name__}: {e}; {r.stderr.strip()[-200:]}")
            else:
                record("voice_check.py", "SKIP", "numpy not installed")
            r = run([sys.executable, str(HERE / "mix_episode.py"), "edit/ep.edl.json", "--out", "final/ep.mp4", "--ass", "subs/ep.ass",
                     "--preset", "ultrafast"], work)
            last = (r.stdout.strip().splitlines() or [""])[-1]
            record("mix_episode.py (cut, mix, duck, master, burn, verify)", "PASS" if r.returncode == 0 else "FAIL",
                   last[:260] if r.returncode == 0 else (r.stderr.strip() or r.stdout.strip())[-300:])
            if r.returncode == 0:
                rep = json.loads((work / "final/ep.mix.report.json").read_text(encoding="utf-8"))
                record("mixed programme: frames, length, loudness", "PASS" if all(rep["checks"].values()) else "FAIL",
                       f"{rep['total_frames']} frames, {rep['loudness']['measured_lufs']} LUFS, music ducked {rep['music_duck_db']} dB")
            if importlib.util.find_spec("opentimelineio"):
                ok, note = script("export_otio.py", ["edit/ep.edl.json", "--out", "edit/ep", "--mix", "final/ep.mix.wav"], work)
                record("export_otio.py", "PASS" if ok else "FAIL", note)
            else:
                record("export_otio.py", "SKIP", "opentimelineio not installed")
            if importlib.util.find_spec("pyJianYingDraft"):
                (work / "drafts").mkdir(exist_ok=True)
                ok, note = script("export_capcut_draft.py", ["edit/ep.edl.json", "--drafts", "drafts", "--overwrite",
                                                             "--report", "final/ep.mix.report.json", "--mix", "final/ep.mix.wav"], work)
                record("export_capcut_draft.py (with the mix report and the master mix track)",
                       "PASS" if ok and (work / "drafts/ep/draft_content.json").exists() else "FAIL", note)
            else:
                record("export_capcut_draft.py", "SKIP", "pyJianYingDraft not installed")
        if a.keep:
            print(f"files kept in {work}")

    fails = [n for n, s, _ in RESULTS if s == "FAIL"]
    skips = [n for n, s, _ in RESULTS if s == "SKIP"]
    print(f"\n{len(RESULTS) - len(fails) - len(skips)} passed, {len(skips)} skipped, {len(fails)} failed")
    if fails:
        print("failed: " + "; ".join(fails))
        sys.exit(1)
    print("the QC and post-production tool chain works on this machine"
          + (" (optional parts skipped - see above)" if skips else ""))


if __name__ == "__main__":
    main()
