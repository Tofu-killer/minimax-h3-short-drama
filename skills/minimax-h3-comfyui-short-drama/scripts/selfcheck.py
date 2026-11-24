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
import os
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


class in_dir:
    """Paths in an edit list are relative to the project root the scripts run from: checks made inside this process
    have to stand there too, or every file reads as missing."""
    def __init__(self, path: Path):
        self.path, self.back = path, None

    def __enter__(self):
        self.back = os.getcwd()
        os.chdir(self.path)

    def __exit__(self, *exc):
        os.chdir(self.back)


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

        # a shot's length is judged on what the storyboard wrote for it, not on the set-up and end state the builder adds;
        # the rhythm audit objects to nothing the shot table allows; the mixer says why a line gives it no speech window
        try:
            words = json.loads((work / "prompts/s02.media.json").read_text(encoding="utf-8")).get("shot_words") or {}
            counted = all(isinstance(words.get(k), dict) and 0 < words[k]["own"] <= words[k]["all"] for k in ("1", "2")) \
                and words["1"]["own"] < words["1"]["all"]                       # shot 1 carries the set-up the builder adds
            (work / "prompts_long").mkdir(exist_ok=True)
            long_text = (work / "prompts/s02.txt").read_text(encoding="utf-8").replace(
                " [Shot 2]", " " + " ".join(["He lifts the cup and puts it down again"] * 32) + ". [Shot 2]", 1).replace(
                "\n[Shot 2]", " " + " ".join(["He lifts the cup and puts it down again"] * 32) + ".\n[Shot 2]", 1)
            (work / "prompts_long/s02.txt").write_text(long_text, encoding="utf-8")
            shutil.copyfile(work / "prompts/s02.media.json", work / "prompts_long/s02.media.json")
            r_ok = run([sys.executable, str(HERE / "lint_prompt.py"), "prompts/s02.txt"], work)
            r_long = run([sys.executable, str(HERE / "lint_prompt.py"), "prompts_long/s02.txt"], work)
            judged = counted and "words of its own" not in r_ok.stdout and "runs to" not in r_ok.stdout and "[Shot 1] carries" in r_long.stdout
            dense = json.loads(json.dumps(ep))
            dense["segments"][2]["shots"] = [shot(1, 0, "a medium close-up on Hero", "Hero looks up and speaks.", "我们开始吧"),
                                             dict(shot(2, 3.0, "a close-up on Hero's hands", "His hands fold on his knees."), end_hold=True)]
            (work / "ep_dense.json").write_text(json.dumps(dense, ensure_ascii=False, indent=1), encoding="utf-8")
            packed = json.loads(json.dumps(dense))
            packed["segments"][2]["shots"][0]["dialogue"] += [{"speaker": "hero", "language": "Chinese", "text": "好"},
                                                              {"speaker": "hero", "language": "Chinese", "text": "走"}]
            (work / "ep_packed.json").write_text(json.dumps(packed, ensure_ascii=False, indent=1), encoding="utf-8")
            a1 = run([sys.executable, str(HERE / "validate_episode.py"), "ep_dense.json", "--rhythm"], work)
            a2 = run([sys.executable, str(HERE / "validate_episode.py"), "ep_packed.json", "--rhythm"], work)
            agrees = "overloaded" not in a1.stdout and "overloaded" in a2.stdout          # 5 s: 2 shots + 1 line is in the table, + 3 lines is not
            mix_mod = load("mix_episode")
            why = [mix_mod.untimed_reason([{"text": "a"}]),
                   mix_mod.untimed_reason([{"text": "a", "start": 0.3, "end": 1.4, "needs_review": "not_heard"}]),
                   mix_mod.heard({"start": 0.3, "end": 1.4, "needs_review": "not_heard", "locked": True})]
            named = "run retime_subtitles.py" in why[0] and "did not hear" in why[1] and "run retime_subtitles.py before" not in why[1] and why[2] is True
            good = judged and agrees and named
            record("advice that does not contradict itself (a shot judged on its own words, rhythm audit vs shot table, why a line has no speech window)",
                   "PASS" if good else "FAIL",
                   "" if good else f"own words {judged} ({words}), rhythm {agrees}, mixer {named}: {r_long.stdout.strip()[-160:]} | {a1.stdout.strip()[-160:]}")
        except Exception as e:  # noqa: BLE001
            record("advice that does not contradict itself", "FAIL", f"{type(e).__name__}: {e}")

        # the setup check reads a server's own answers: an old CUDA build, a loading flag, a node pack that is not installed,
        # a model file that is missing or sits one folder too deep must each be named
        try:
            setup = load("check_setup")
            facts, warned = setup.system_findings({"system": {"comfyui_version": "0.37.2", "python_version": "3.12.9 (x)", "pytorch_version": "2.8.0+cu126",
                                                               "ram_total": 64 * 2**30, "ram_free": 40 * 2**30,
                                                               "argv": ["main.py", "--windows-standalone-build", "--lowvram", "--use-ck-attention"],
                                                               "comfy_package_versions": [{"name": "comfy-kitchen", "installed": "0.2.30", "required": "0.2.35"}]},
                                                    "devices": [{"name": "cuda:0 NVIDIA GeForce RTX 4090", "type": "cuda",
                                                                 "vram_total": 24 * 2**30, "vram_free": 23 * 2**30}]})
            told = any("CUDA 12.6 build" in w for w in warned) and any("--lowvram" in w for w in warned) \
                and any("--use-ck-attention" in w and "WITHOUT `_sage`" in w for w in warned) \
                and any("comfy-kitchen" in w and "0.2.35" in w for w in warned) and not any("VRAM" in w for w in warned)
            ref = json.loads((HERE.parent / "assets/workflows/h3_ref2va_sage_refine.api.json").read_text(encoding="utf-8"))
            fake = {}
            for node in ref.values():                        # a server that has every core node, none of the packs, and one file in a sub-folder
                if node["class_type"] in setup.PACKS:
                    continue
                spec = fake.setdefault(node["class_type"], {"input": {"required": {}}})["input"]["required"]
                for name, val in node["inputs"].items():
                    if isinstance(val, str) and val.lower().endswith(".safetensors"):
                        offered = ["sub\\" + val] if "lora" in name else ([] if "unet" in name else [val])
                        spec.setdefault(name, [[]])[0].extend(offered)      # two VAE loaders share one class
            classes, files = setup.workflow_state(ref, fake)
            found = set(classes.values()) == {"kijai/ComfyUI-KJNodes", "tazmannner/ComfyUI-H3-ResCascade"} \
                and any(i == "lora_name" and near.startswith("sub") for i, _v, near in files) \
                and any(i == "unet_name" and near == "" for i, _v, near in files) and not any(i == "vae_name" for i, _v, _n in files)
            record("check_setup.py names what a server lacks (old CUDA build, loading flag, node packs, missing or misplaced model files)",
                   "PASS" if told and found else "FAIL", "" if told and found else f"system {told}: {warned} | workflow {found}: {classes} {files}")
        except Exception as e:  # noqa: BLE001
            record("check_setup.py", "FAIL", f"{type(e).__name__}: {e}")

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
                                               ("h3_ref2va_sage_refine.api.json", "prompts/s01.media.json", ("second pass to 1920x1088", "sage_attention auto")),
                                               ("h3_ref2va_refine_split.api.json", "prompts/s01.media.json", ("second pass in chunks", "0.45, 0.225, 0.0", "73 frames"))):
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
                        or "BasicScheduler" in r.stdout or "s03_refine_" not in r.stdout:      # a refine files itself beside the draft
                    notes.append(f"--from-latent: {(r.stderr.strip() or r.stdout.strip())[-200:]}")
                # the job around a kept latent follows the take it belongs to: canvas and length come from its record; a canvas
                # or length the command sets itself against that record is warned about, with the fix
                (work / "kept_take/run.json").write_text(json.dumps({
                    "status": "success", "seed": 7, "frames": 124,
                    "first_pass": "MiniMaxH3ReferenceToVideo [136]: 960x544, 124 frames = 5.17s, ref_image_size match, 2 reference image(s), 0 audio"}),
                    encoding="utf-8")
                from_cmd = [sys.executable, str(HERE / "comfy_submit.py"), str(flows / "h3_ref2va_refine.api.json"), "--server", "http://127.0.0.1:9",
                            "--media", "prompts/s03.media.json", "--from-latent", "kept_take", "--dry-run"]
                r_auto = run(from_cmd, work)
                r_other = run(from_cmd + ["--set", "136.width=1344", "--set", "136.height=768"], work)
                r_len = run(from_cmd + ["--set", "136.length=73"], work)
                if not ("node 136 set from the kept take's record" in r_auto.stdout and "1344x768 -> 960x544" in r_auto.stdout
                        and "continues the take in kept_take (same canvas, same length)" in r_auto.stdout and "!!" not in r_auto.stdout
                        and "enlarges the first pass 2.00x (960x544 -> 1920x1088)" in r_auto.stdout
                        and "WARNING: continues the take in kept_take" in r_other.stdout and "960x544 canvas" in r_other.stdout
                        and "--set 136.width=960 --set 136.height=544" in r_other.stdout and "!! 1 take(s) above carry a WARNING" in r_other.stdout
                        and "124 frames long and the H3 node is now set to 73" in r_len.stdout):
                    notes.append(f"--from-latent, canvas / length from the take: {r_auto.stdout.strip()[-200:]} | {r_other.stdout.strip()[-160:]}")
                # a take keeps what it was made from (prompt.txt + media.json): submitting from that copy files beside that take
                made = work / "takes/keep/s03/s03_7"
                made.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(work / "prompts/s03.txt", made / "prompt.txt")
                copy = json.loads((work / "prompts/s03.media.json").read_text(encoding="utf-8"))
                copy.update(prompt_file="prompt.txt", copied_from="prompts/s03.media.json")
                (made / "media.json").write_text(json.dumps(copy, ensure_ascii=False), encoding="utf-8")
                (made / "run.json").write_text(json.dumps({"status": "success", "seed": 7}), encoding="utf-8")
                r = run([sys.executable, str(HERE / "comfy_submit.py"), str(flows / "h3_ref2va_refine.api.json"), "--server", "http://127.0.0.1:9",
                         "--media", str(made / "media.json"), "--seed", "7", "--dry-run"], work)
                if r.returncode != 0 or "prompt prompt.txt" not in r.stdout or "s03_refine_7" not in r.stdout \
                        or f"output folder: {made.parent}" not in r.stdout:
                    notes.append(f"--media from a take's own copy: {(r.stderr.strip() or r.stdout.strip())[-220:]}")
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
                # the text-to-picture model for projects that earn money: its prompt input is called `text`, not `prompt`
                zt = [sys.executable, str(HERE / "comfy_submit.py"), str(flows / "zimage_turbo_t2i.api.json"), "--server", "http://127.0.0.1:9",
                      "--out", "qc/zt2i", "--dry-run"]
                for what, r, need, code in (
                        ("Z-Image, an empty prompt", run(zt, work), "--set 57:27.text=@", 2),
                        ("Z-Image, a master", run(zt + ["--set", "57:27.text=@bust.txt", "--set", "57:13.width=2048", "--set", "57:13.height=1152"], work),
                         "2048x1152", 0)):
                    if r.returncode != code or need not in (r.stdout + r.stderr) or (code == 0 and "advice:" in r.stdout):
                        notes.append(f"stills, {what}: {(r.stderr.strip() or r.stdout.strip())[-160:]}")
                # the score: what a music encoder calls its prompt is `tags`; the preview states the length, tempo and key
                mu = [sys.executable, str(HERE / "comfy_submit.py"), str(flows / "acestep15_music.api.json"), "--server", "http://127.0.0.1:9",
                      "--out", "qc/score", "--tag", "score", "--dry-run"]
                for what, r, need, code in (
                        ("music, no description", run(mu, work), "--set 94.tags=@", 2),
                        ("music, a 62 s instrumental", run(mu + ["--set", "94.tags=low strings, felt piano, dark and restrained", "--set", "120.value=62",
                                                                  "--set", "94.bpm=72", "--set", "94.keyscale=D minor"], work),
                         "62 s, 72 BPM, D minor", 0)):
                    if r.returncode != code or need not in (r.stdout + r.stderr) or (code == 0 and "[Instrumental]" not in r.stdout):
                        notes.append(f"{what}: {(r.stderr.strip() or r.stdout.strip())[-200:]}")
                # a job queued into a take folder earlier and never collected (the script was stopped, the conversation lost):
                # another command for the same folder does not queue over it, and names the way to fetch it
                pend = work / "qc/pend/take_1"
                pend.mkdir(parents=True, exist_ok=True)
                (pend / "handle.json").write_text(json.dumps({"prompt_id": "p-1", "fingerprint": "of another command", "seed": 1, "queued_at": 1.0,
                                                              "server": "http://127.0.0.1:9", "command": "x"}), encoding="utf-8")
                st = [sys.executable, str(HERE / "comfy_submit.py"), str(flows / "selftest_no_model.api.json"), "--server", "http://127.0.0.1:9",
                      "--set", "1.image=@bible/face.png", "--out", "qc/pend", "--tag", "take", "--dry-run"]
                r_dry = run(st, work)
                r_col = run([sys.executable, str(HERE / "comfy_submit.py"), "--collect", "qc/pend/take_1"], work)
                r_none = run([sys.executable, str(HERE / "comfy_submit.py"), "--collect", "qc/pend/nothing_here"], work)
                if "[pending] NOT queued" not in r_dry.stdout or "--collect" not in r_dry.stdout or "add --confirm" in r_dry.stdout \
                        or not (pend / "handle.json").exists():
                    notes.append(f"an uncollected job in the take folder: {(r_dry.stderr.strip() or r_dry.stdout.strip())[-240:]}")
                if r_col.returncode != 2 or "cannot reach ComfyUI" not in r_col.stderr or r_none.returncode != 1 or "no readable handle.json" not in r_none.stderr:
                    notes.append(f"--collect without a server / without a handle: {r_col.stderr.strip()[-160:]} | {r_none.stderr.strip()[-160:]}")
                # slips the server would accept or answer with a bare HTTP 400: a prompt file named without @, a size typed as WxH,
                # a size this pipeline has no use for (advice only)
                for what, r, need, code in (
                        ("a prompt file without @", run(t2i + ["--set", "459:452.prompt=bust.txt"], work), "that is a file name", 2),
                        ("a size written as WxH", run(t2i + ["--set", "459:452.prompt=@bust.txt", "--set", "459:456.width=2688x1536"], work), "takes a number", 2),
                        ("an unusual size", run(edit + ["--set", "42.image=@bible/room.png", "--set", "170:300.width=1920", "--set", "170:300.height=1080"], work),
                         "not a size this pipeline uses", 0)):
                    if r.returncode != code or need not in (r.stdout + r.stderr):
                        notes.append(f"stills, {what}: {(r.stderr.strip() or r.stdout.strip())[-160:]}")
                # a first-frame segment has its own refine workflow (same second pass, on the FL2VA weights with their shift)
                i2v = json.loads(json.dumps(ep))
                i2v["segments"][2]["mode"] = "i2va"
                (work / "ep_i2v.json").write_text(json.dumps(i2v, ensure_ascii=False, indent=1), encoding="utf-8")
                run([sys.executable, str(HERE / "build_prompts.py"), "ep_i2v.json", "--out", "prompts_i2v", "--only", "s03"], work)
                r = run([sys.executable, str(HERE / "comfy_submit.py"), str(flows / "h3_fl2va_refine.api.json"), "--server", "http://127.0.0.1:9",
                         "--media", "prompts_i2v/s03.media.json", "--dry-run"], work)
                if r.returncode != 0 or not all(w in r.stdout for w in ("second pass to 1920x1088", "first_frame", "shift video 6.0")) or "advice:" in r.stdout:
                    notes.append(f"h3_fl2va_refine with a first-frame segment: {(r.stderr.strip() or r.stdout.strip())[-200:]}")
                r = run([sys.executable, str(HERE / "lint_prompt.py"), str(flows / "smoke_test_prompt.txt"), "--seconds", "5", "--images", "0", "--audios", "0"], work)
                if r.returncode != 0:
                    notes.append(f"smoke_test_prompt.txt does not lint: {r.stdout.strip()[-160:]}")
                broken = [f.name for f in sorted(flows.glob("*.api.json"))
                          if not all(isinstance(v, dict) and "class_type" in v and "inputs" in v for v in json.loads(f.read_text(encoding="utf-8")).values())]
                good = not notes and not broken and len(list(flows.glob("*.api.json"))) >= 18
                record("shipped workflows (draft, Sage, refine for both families, LoRA switch, kept latent; stills refuse what is missing or mistyped)", "PASS" if good else "FAIL",
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

        # the model checker tells a missing file from one that did not finish downloading, without touching anything
        try:
            (work / "cf/models/vae").mkdir(parents=True, exist_ok=True)
            (work / "cf/models/vae/minimax_h3_audio_vae_fp32.safetensors").write_bytes(b"x" * 1000)
            r = run([sys.executable, str(HERE / "fetch_models.py"), "--comfyui", "cf", "--sets", "ref2va"], work)
            told = r.returncode == 1 and "INCOMPLETE models/vae/minimax_h3_audio_vae_fp32.safetensors" in r.stdout \
                and "MISSING    models/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors" in r.stdout \
                and (work / "cf/models/vae/minimax_h3_audio_vae_fp32.safetensors").stat().st_size == 1000
            record("fetch_models.py (check only: missing and unfinished files told apart)", "PASS" if told else "FAIL",
                   "" if told else (r.stderr.strip() or r.stdout.strip())[-240:])
        except Exception as e:  # noqa: BLE001
            record("fetch_models.py", "FAIL", f"{type(e).__name__}: {e}")

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

        # the stills planner: every picture the storyboard names gets a prompt file and a command with the right workflow and inputs
        try:
            look = "a Chinese man in his forties, about 180 cm and lean, with a long face, short black hair and a grey wool coat over a white shirt"
            st = json.loads(json.dumps(ep))
            st["characters"][0].update(sheet_phrase=look, reference_images=["bible/chars/hero_face.png", "bible/chars/hero_full.png"])
            st["scenes"][0]["reference_images"] = ["bible/scenes/room_master.png"]          # none of these pictures exists yet
            st["segments"][2]["first_frame"] = "first/s03.png"
            st["segments"][2]["first_frame_prompt"] = (
                f"Keep exactly the same person as Picture 1: same face, hairstyle and clothes ({look}). The room is the one in Picture 2: "
                "same walls, furniture and light direction. New photo: A cinematic film still. A medium close-up, the man sits on the chair "
                "at the window, lips closed. Exactly 1 person in the frame. Soft daylight from the window on the left.")
            (work / "ep_stills.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
            plan_cmd = [sys.executable, str(HERE / "plan_stills.py"), "ep_stills.json", "--prompts", "stills/prompts", "--out", "stills/plan.md"]
            r = run(plan_cmd, work)
            plan_text = (work / "stills/plan.md").read_text(encoding="utf-8") if (work / "stills/plan.md").exists() else ""
            files = sorted(x.name for x in (work / "stills/prompts").glob("*.txt")) if (work / "stills/prompts").is_dir() else []
            r2 = run(plan_cmd, work)
            good = r.returncode == 0 and "5 to make = 18 candidates" in r.stdout and "keyframe_prompt" in r.stdout \
                and files == ["first_s03.txt", "hero_bust.txt", "hero_face.txt", "hero_full.txt", "room_master.txt"] \
                and "qwen_edit2511_2ref.api.json" in plan_text and "41.image=@bible/chars/hero_face.png" in plan_text \
                and "42.image=@bible/scenes/room_s03_crop.png" in plan_text and "41.image=@bible/chars/hero_bust.png" in plan_text \
                and "-> `first/s03.png`" in plan_text and "--set 459:456.width=2688 --set 459:456.height=1536" in plan_text \
                and look in (work / "stills/prompts/hero_full.txt").read_text(encoding="utf-8") \
                and "5 kept as they were" in r2.stdout
            rz = run([sys.executable, str(HERE / "plan_stills.py"), "ep_stills.json", "--prompts", "stills/prompts", "--out", "stills/plan_z.md",
                      "--t2i", "zimage"], work)
            plan_z = (work / "stills/plan_z.md").read_text(encoding="utf-8") if (work / "stills/plan_z.md").exists() else ""
            good = good and rz.returncode == 0 and "zimage_turbo_t2i.api.json" in plan_z and "57:27.text=@stills/prompts/hero_bust.txt" in plan_z \
                and "--set 57:13.width=2048 --set 57:13.height=1152" in plan_z and "qwen21_t2i" not in plan_z \
                and "qwen_edit2511_2ref.api.json" in plan_z           # the edit model stays the same
            # a choice made once holds: the bare command another tool prints must not fall back to the research-licence model
            # or to the default canvas; giving the option again changes it, --forget drops what was remembered
            base_cmd = [sys.executable, str(HERE / "plan_stills.py"), "ep_stills.json", "--prompts", "stills/prompts"]
            rz2 = run(base_cmd + ["--out", "stills/plan_z2.md", "--canvas", "1536x864"], work)
            rz3 = run(base_cmd + ["--out", "stills/plan_z3.md"], work)
            rz4 = run(base_cmd + ["--out", "stills/plan_z4.md", "--forget"], work)
            pz = {n: ((work / f"stills/plan_z{n}.md").read_text(encoding="utf-8") if (work / f"stills/plan_z{n}.md").exists() else "") for n in (2, 3, 4)}
            good = good and "as chosen in an earlier run" in rz2.stdout and "--t2i zimage" in rz2.stdout and "qwen21_t2i" not in pz[2] \
                and "170:300.width=1536 --set 170:300.height=864" in pz[2] \
                and "--canvas 1536x864" in rz3.stdout and "zimage_turbo_t2i.api.json" in pz[3] and "170:300.width=1536" in pz[3] \
                and "as chosen in an earlier run" not in rz4.stdout and "qwen21_t2i.api.json" in pz[4] and "170:300.width=1536" not in pz[4] \
                and run(base_cmd + ["--canvas", "1536x860"], work).returncode != 0
            record("plan_stills.py (prompt files and one command per picture, inputs read from the Picture N sentences)", "PASS" if good else "FAIL",
                   "" if good else f"{files} | {(r.stderr.strip() or r.stdout.strip())[-260:]} | {rz.stdout.strip()[-160:]}")
            # pictures the storyboard names but nobody has made yet are a to-do list, not errors: the storyboard is checked before the stills exist
            v = run([sys.executable, str(HERE / "validate_episode.py"), "ep_stills.json"], work)
            listed = v.returncode == 0 and " + bible/chars/hero_face.png" in v.stdout and " + first/s03.png" in v.stdout \
                and "still to make" in v.stdout and "ERROR" not in v.stdout
            record("validate_episode.py lists the pictures still to make (not errors)", "PASS" if listed else "FAIL",
                   "" if listed else (v.stderr.strip() or v.stdout.strip())[-260:])
            # after a picture is made the storyboard changes: the prompt file follows, the picture is listed to make again;
            # a prompt file edited by hand is left as it is
            (work / "first").mkdir(exist_ok=True)
            (work / "first/s03.png").write_bytes(b"selfcheck")
            run(plan_cmd, work)                                   # sees the picture: made from the prompt of now
            st["segments"][2]["first_frame_prompt"] = st["segments"][2]["first_frame_prompt"].replace("sits on the chair", "stands")
            (work / "ep_stills.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
            r3 = run(plan_cmd, work)
            (work / "stills/prompts/hero_bust.txt").write_text("my own portrait text\n", encoding="utf-8")
            st["characters"][0]["sheet_phrase"] = look + ", a silver ring on the left hand"       # the storyboard moves on after the hand edit
            (work / "ep_stills.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
            r4 = run(plan_cmd, work)
            follows = "1 updated from the storyboard (first_s03.txt)" in r3.stdout and "MAKE AGAIN (1)" in r3.stdout \
                and "stands at the window" in (work / "stills/prompts/first_s03.txt").read_text(encoding="utf-8") \
                and (work / "stills/prompts/hero_bust.txt").read_text(encoding="utf-8") == "my own portrait text\n" \
                and "hero_bust.txt differs from what the storyboard gives now and was kept as it is" in r4.stdout.replace("\\", "/") \
                and "silver ring" in (work / "stills/prompts/hero_full.txt").read_text(encoding="utf-8") and "MAKE AGAIN (1)" in r4.stdout
            # a picture made from another picture goes out of date when that input is made again: the first frame of a
            # two-step frame, a frame made from a face picture
            (work / "first/s03.png").write_bytes(b"made from the prompt of now")
            (work / "bible/chars").mkdir(parents=True, exist_ok=True)
            (work / "bible/chars/hero_face.png").write_bytes(b"face v1")
            run(plan_cmd, work)                                   # both on disk: recorded as belonging together
            (work / "bible/chars/hero_face.png").write_bytes(b"face v2")
            r5 = run(plan_cmd, work)
            plan5 = (work / "stills/plan.md").read_text(encoding="utf-8")
            follows = follows and "first/s03.png" in r5.stdout.split("MAKE AGAIN")[-1] \
                and "made from an earlier version of bible/chars/hero_face.png" in plan5 \
                and "For other candidates of the same prompt" in plan5      # a picture on disk keeps its command
            # a scene crop is cut by hand from the scene master: when the master is made again, the crop is listed to cut again
            (work / "bible/scenes").mkdir(parents=True, exist_ok=True)
            (work / "bible/scenes/room_master.png").write_bytes(b"master v1")
            (work / "bible/scenes/room_s03_crop.png").write_bytes(b"crop of v1")
            run(plan_cmd, work)                                   # both on disk: the crop belongs to this master
            (work / "bible/scenes/room_master.png").write_bytes(b"master v2")
            r6 = run(plan_cmd, work)
            follows = follows and "CUT AGAIN (1): bible/scenes/room_s03_crop.png" in r6.stdout \
                and "CUT AGAIN - the scene master was made again" in (work / "stills/plan.md").read_text(encoding="utf-8")
            # a newer version of the skill words a template differently: same storyboard, so the prompt file and the picture stand
            import hashlib as _hl
            mf = work / "stills/prompts/.stills_plan.json"
            man = json.loads(mf.read_text(encoding="utf-8"))
            earlier = "A studio portrait in the wording of an earlier version.\n"
            (work / "stills/prompts/hero_full.txt").write_text(earlier, encoding="utf-8")
            man["prompts"]["hero_full.txt"] = _hl.sha256(earlier.strip().encode("utf-8")).hexdigest()[:16]
            mf.write_text(json.dumps(man), encoding="utf-8")
            r7 = run(plan_cmd, work)
            follows = follows and "written by another version of this script" in r7.stdout and "hero_full.txt" in r7.stdout \
                and (work / "stills/prompts/hero_full.txt").read_text(encoding="utf-8") == earlier and "updated from the storyboard" not in r7.stdout
            # the person an over-the-shoulder frame looks past gets the back view once one is planned, never the face
            ots = json.loads(json.dumps(st))
            ots["characters"].append({"id": "guest", "name": "Guest", "sheet_phrase": "a woman in her thirties with a short bob and a red scarf",
                                      "reference_images": ["bible/chars/guest_face.png"]})
            ots["segments"][2]["character_ids"] = ["hero", "guest"]
            ots["segments"][2]["shots"][0]["framing"] = "a medium shot of {hero} over the shoulder of {guest}"
            ots["segments"][2]["shots"][0]["on_screen_characters"] = ["hero", "guest"]
            ots["segments"][2]["first_frame_prompt"] = (
                f"Keep exactly the same person as Picture 1 ({ots['characters'][0]['sheet_phrase']}). Keep the same person as Picture 2 "
                "(a woman in her thirties with a short bob and a red scarf). New photo: a medium shot of the man over her shoulder.")
            (work / "ep_ots.json").write_text(json.dumps(ots, ensure_ascii=False, indent=1), encoding="utf-8")
            ots_cmd = [sys.executable, str(HERE / "plan_stills.py"), "ep_ots.json", "--prompts", "stills/prompts_ots", "--out", "stills/plan_ots.md"]
            o1 = run(ots_cmd, work)
            p1 = (work / "stills/plan_ots.md").read_text(encoding="utf-8")
            o2 = run(ots_cmd + ["--back", "guest"], work)
            p2 = (work / "stills/plan_ots.md").read_text(encoding="utf-8")
            follows = follows and "over the shoulder of guest" in o1.stdout and "42.image=@bible/chars/guest_face.png" in p1 \
                and "over the shoulder of guest" not in o2.stdout and "42.image=@bible/chars/guest_back.png" in p2
            record("plan_stills.py follows the storyboard (changed prompt rewritten, its picture listed to make again, hand edits kept)",
                   "PASS" if follows else "FAIL", "" if follows else f"{r3.stdout.strip()[-260:]} | {r4.stdout.strip()[-200:]} | {r5.stdout.strip()[-200:]}")
        except Exception as e:  # noqa: BLE001
            record("plan_stills.py", "FAIL", f"{type(e).__name__}: {e}")

        # a take is checked against what it was made from: another segment's take and a draft made from an earlier prompt
        # are refused, the out-of-date drafts are listed on every build, and a changed earlier ending keeps being warned about
        try:
            import takes as take_records  # noqa: E402
            from storyboard import frames_for_seconds as _frames  # noqa: E402
            s1, s2 = flow["segments"][0], flow["segments"][1]
            (work / "ep_guard.json").write_text(json.dumps(flow, ensure_ascii=False, indent=1), encoding="utf-8")
            run([sys.executable, str(HERE / "build_prompts.py"), "ep_guard.json", "--out", "prompts/guard", "--allow-planned"], work)
            spec = json.loads((work / "prompts/guard" / f"{s2['id']}.media.json").read_text(encoding="utf-8"))
            cwd = os.getcwd()
            os.chdir(work)                      # the references of a .media.json are relative to the project root
            try:
                sha0 = take_records.media_inputs_sha(Path("prompts/guard") / f"{s2['id']}.media.json")
            finally:
                os.chdir(cwd)
            draft = work / "takes/guard" / s2["id"] / f"{s2['id']}_1001"
            draft.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(work / "selects/s02.mp4", draft / "clip.mp4")
            (draft / "run.json").write_text(json.dumps({"status": "success", "seed": 1001, "segment": s2["id"], "inputs_sha": sha0,
                                                        "frames": _frames(s2["duration"]), "opens_from": spec.get("opens_from"),
                                                        "media_json": f"prompts/guard/{s2['id']}.media.json"}), encoding="utf-8")
            obs = [sys.executable, str(HERE / "observe_take.py")]
            common = ["--episode", "ep_guard.json", "--out", "qc/observe_guard"]
            g1 = run(obs + ["selects/s01.mp4", "--segment", s1["id"], "--as-planned"] + common, work)
            b1 = run([sys.executable, str(HERE / "build_prompts.py"), "ep_guard.json", "--out", "prompts/guard"], work)
            fresh = g1.returncode == 0 and "[unchanged]" in b1.stdout and "EARLIER" not in b1.stdout and sha0 is not None
            g2 = run(obs + ["selects/s01.mp4", "--segment", s1["id"], "--write",
                            "Hero stands by the door with his back to the window, one hand on the handle.", "--confidence", "medium",
                            "--deviation", "he went to the door"] + common, work)
            b2 = run([sys.executable, str(HERE / "build_prompts.py"), "ep_guard.json", "--out", "prompts/guard"], work)
            b3 = run([sys.executable, str(HERE / "build_prompts.py"), "ep_guard.json", "--out", "prompts/guard"], work)
            lasting = g2.returncode == 0 and "CHANGED since the last build" in b2.stdout and "[unchanged]" in b3.stdout \
                and "1 finished take(s)" in b2.stdout and "1 finished take(s)" in b3.stdout
            g3 = run(obs + [str(draft / "clip.mp4"), "--segment", s2["id"], "--as-planned"] + common, work)
            state3 = json.loads((work / "ep_guard.json").read_text(encoding="utf-8"))["segments"][1].get("status", "planned")
            g4 = run(obs + [str(draft / "clip.mp4"), "--segment", s1["id"], "--as-planned"] + common, work)
            refused = g3.returncode != 0 and "EARLIER version" in (g3.stderr + g3.stdout) and not state3.startswith("accepted") \
                and g4.returncode != 0 and f"made for segment {s2['id']}" in (g4.stderr + g4.stdout)
            g5 = run(obs + [str(draft / "clip.mp4"), "--segment", s2["id"], "--as-planned", "--stale-ok"] + common, work)
            took = json.loads((work / "ep_guard.json").read_text(encoding="utf-8"))["segments"][1].get("accepted_take") or {}
            v1 = run([sys.executable, str(HERE / "validate_episode.py"), "ep_guard.json"], work)
            knowingly = g5.returncode == 0 and took.get("inputs_sha") == sha0 and took.get("cut_checked") and "another state than" not in v1.stdout
            g6 = run(obs + ["selects/s01.mp4", "--segment", s1["id"], "--write",
                            "Hero sits on the floor under the window with both hands on his knees, facing the door.", "--confidence", "high",
                            "--deviation", "he sat down"] + common, work)
            v2 = run([sys.executable, str(HERE / "validate_episode.py"), "ep_guard.json"], work)
            g7 = run(obs + [str(draft / "clip.mp4"), "--segment", s2["id"], "--as-planned", "--stale-ok"] + common, work)
            v3 = run([sys.executable, str(HERE / "validate_episode.py"), "ep_guard.json"], work)
            warned = g6.returncode == 0 and "CHECK THE CUT" in g6.stdout and "another state than" in v2.stdout \
                and g7.returncode == 0 and "another state than" not in v3.stdout          # looked at and confirmed: the warning ends
            # the accepted take is a file: the validator says so when it is gone or has other content than when it was accepted
            moved = json.loads((work / "ep_guard.json").read_text(encoding="utf-8"))
            moved["segments"][0]["accepted_take"]["path"] = "selects/no_longer_here.mp4"
            moved["segments"][1]["accepted_take"]["sha256"] = "0" * 64
            (work / "ep_guard_moved.json").write_text(json.dumps(moved, ensure_ascii=False, indent=1), encoding="utf-8")
            v4 = run([sys.executable, str(HERE / "validate_episode.py"), "ep_guard_moved.json"], work)
            warned = warned and "is not on disk" in v4.stdout and "has other content than the take that was accepted" in v4.stdout \
                and "is not on disk" not in v3.stdout and "has other content" not in v3.stdout
            good = fresh and lasting and refused and knowingly and warned
            record("takes are checked against what they were made from (wrong segment, out-of-date draft, changed earlier ending)",
                   "PASS" if good else "FAIL",
                   "" if good else f"fresh {fresh}, lasting marker {lasting}, refused {refused}, --stale-ok {bool(knowingly)}, warned {warned}: "
                                   f"{(g3.stderr.strip() or g3.stdout.strip())[-200:]} | {b3.stdout.strip()[-200:]} | {v2.stdout.strip()[-200:]}")
            # the edit list says so when a clip is not the accepted take nor a second pass of it; a copy in a selects folder
            # is traced to the take it was copied from
            seg_takes = work / "takes/guard" / s2["id"]
            other, refine = seg_takes / f"{s2['id']}_1002", seg_takes / f"{s2['id']}_refine_1001"
            for folder, seed, source, tagged in ((other, 1002, "selects/s03.mp4", "other"), (refine, 1001, "selects/s02.mp4", "refine")):
                folder.mkdir(parents=True, exist_ok=True)
                run(["ffmpeg", "-v", "error", "-y", "-i", source, "-c", "copy", "-metadata", f"comment={tagged}", str(folder / "clip.mp4")], work)
                (folder / "run.json").write_text(json.dumps({"status": "success", "seed": seed, "segment": s2["id"], "inputs_sha": sha0}),
                                                 encoding="utf-8")
            (work / "picked").mkdir(exist_ok=True)
            shutil.copyfile(refine / "clip.mp4", work / "picked/final_cut.mp4")                 # a copy without a record beside it
            edl = [sys.executable, str(HERE / "make_edl.py"), "ep_guard.json", "--selects", "selects", "--overwrite"]
            e1 = run(edl + ["--out", "edit/guard_a.edl.json", "--pick", f"{s2['id']}={other / 'clip.mp4'}"], work)
            e2 = run(edl + ["--out", "edit/guard_b.edl.json", "--pick", f"{s2['id']}={refine / 'clip.mp4'}"], work)
            e3 = run(edl + ["--out", "edit/guard_c.edl.json", "--pick", f"{s2['id']}={work / 'picked/final_cut.mp4'}"], work)
            e4 = run(edl + ["--out", "edit/guard_d.edl.json", "--pick", f"{s2['id']}={draft / 'clip.mp4'}"], work)
            e5 = run([sys.executable, str(HERE / "make_edl.py"), "ep_guard.json", "--selects", "selects", "--out", "edit/guard_a.edl.json"], work)
            told = f"WARN {s2['id']}" in e1.stdout and "another seed" in e1.stdout and "CHECK: " in e1.stdout \
                and all(f"WARN {s2['id']}" not in e.stdout and "cannot tell what this file was made from" not in e.stdout
                        and "which is not the accepted take" not in e.stdout and e.returncode == e1.returncode
                        for e in (e2, e3, e4)) \
                and f"WARN {s2['id']} (entry kept from guard_a.edl.json" in e5.stdout    # a kept entry is checked again on every run
            # a line edited in the storyboard after its take was accepted: the subtitles would show words nobody says
            edited = json.loads((work / "ep_guard.json").read_text(encoding="utf-8"))
            spoken = edited["segments"][1]["shots"][1]["dialogue"][0]["text"]
            edited["segments"][1]["shots"][1]["dialogue"][0]["text"] = "现在就开始"
            (work / "ep_guard_edited.json").write_text(json.dumps(edited, ensure_ascii=False, indent=1), encoding="utf-8")
            e6 = run([sys.executable, str(HERE / "make_edl.py"), "ep_guard_edited.json", "--selects", "selects", "--out", "edit/guard_e.edl.json",
                      "--pick", f"{s2['id']}={draft / 'clip.mp4'}"], work)
            told = told and "lines are not the ones the accepted take was made with" in e6.stdout and spoken in e6.stdout \
                and "lines are not the ones" not in e4.stdout
            # the accepted take's prompt and seed with other settings (a 20-step re-shoot) is another take, not a second pass
            twin = seg_takes / f"{s2['id']}_full_1001"
            twin.mkdir(parents=True, exist_ok=True)
            run(["ffmpeg", "-v", "error", "-y", "-i", str(draft / "clip.mp4"), "-c", "copy", "-metadata", "comment=twin", str(twin / "clip.mp4")], work)
            drec = json.loads((draft / "run.json").read_text(encoding="utf-8"))
            drec["first_pass"] = "BasicScheduler [124]: 8 steps, scheduler simple; MiniMaxH3ReferenceToVideo [136]: 1344x768, 148 frames"
            (draft / "run.json").write_text(json.dumps(drec), encoding="utf-8")
            (twin / "run.json").write_text(json.dumps(dict(drec, first_pass=drec["first_pass"].replace("8 steps", "20 steps"))), encoding="utf-8")
            e7 = run(edl + ["--out", "edit/guard_t.edl.json", "--pick", f"{s2['id']}={twin / 'clip.mp4'}"], work)
            (twin / "run.json").write_text(json.dumps(drec), encoding="utf-8")          # made again with the same settings: the same take
            e8 = run(edl + ["--out", "edit/guard_t2.edl.json", "--pick", f"{s2['id']}={twin / 'clip.mp4'}"], work)
            shutil.rmtree(twin)
            told = told and "but was made with other settings" in e7.stdout and "20 steps" in e7.stdout and f"WARN {s2['id']}" not in e8.stdout
            # a rough cut made before the takes were chosen carries no warning of its own: the mix looks at the storyboard again
            rough = json.loads((work / "edit/guard_b.edl.json").read_text(encoding="utf-8"))
            undecided = json.loads((work / "ep_guard.json").read_text(encoding="utf-8"))
            undecided["segments"][1]["status"] = "planned"
            undecided["segments"][1].pop("accepted_take", None)
            (work / "ep_guard_undecided.json").write_text(json.dumps(undecided, ensure_ascii=False), encoding="utf-8")
            (work / "edit/guard_rough.edl.json").write_text(json.dumps(dict(rough, episode="ep_guard_undecided.json"), ensure_ascii=False), encoding="utf-8")
            m_ok = run([sys.executable, str(HERE / "mix_episode.py"), "edit/guard_b.edl.json", "--out", "final/g.mp4", "--dry-run"], work)
            m_rough = run([sys.executable, str(HERE / "mix_episode.py"), "edit/guard_rough.edl.json", "--out", "final/g.mp4", "--dry-run"], work)
            told = told and rough.get("episode") == "ep_guard.json" and f"WARN  {s2['id']}:" not in m_ok.stdout \
                and f"WARN  {s2['id']}: the storyboard records no accepted take" in m_rough.stdout \
                and "checked against the storyboard as it is now" in m_rough.stdout
            record("make_edl.py compares each clip with the accepted take (another seed warned; a refine, and a copy of it, pass)",
                   "PASS" if told else "FAIL", "" if told else f"{e1.stdout.strip()[-200:]} | {e3.stdout.strip()[-200:]} | {e5.stdout.strip()[-160:]} | "
                                                             f"twin: {e7.stdout.strip()[-200:]} / {e8.stdout.strip()[-120:]} | mix: "
                                                             f"{(m_ok.stderr.strip() or m_ok.stdout.strip())[-160:]} / {(m_rough.stderr.strip() or m_rough.stdout.strip())[-200:]}")
            # the overview of a project reads all of this back: what is accepted, which second pass belongs to it, what the
            # edit uses, and - for a storyboard nothing has been made from yet - the first step
            st_a = run([sys.executable, str(HERE / "project_status.py"), "ep_guard.json", "--prompts", "prompts/guard", "--takes", "takes/guard",
                        "--selects", "selects", "--edl", "edit/guard_b.edl.json", "--json", "qc/status.json"], work)
            st_b = run([sys.executable, str(HERE / "project_status.py"), "ep.json", "--prompts", "prompts_none", "--takes", "takes/none",
                        "--edl", "edit/none.edl.json"], work)
            status = json.loads((work / "qc/status.json").read_text(encoding="utf-8")) if (work / "qc/status.json").exists() else {}
            seen = st_a.returncode == 0 and f"second pass {s2['id']}_refine_1001" in st_a.stdout and "of the accepted take" in st_a.stdout \
                and "the accepted take or a second pass of it" in st_a.stdout and len(status.get("segments", [])) == len(flow["segments"]) \
                and st_b.returncode == 0 and "not built yet" in st_b.stdout and "build_prompts.py" in st_b.stdout and "no edit list yet" in st_b.stdout
            # an edit list that holds another clip than the accepted take, and no second pass yet: the command that swaps it in
            shutil.copytree(work / "takes/guard", work / "takes/guard_nr")
            shutil.rmtree(work / "takes/guard_nr" / s2["id"] / f"{s2['id']}_refine_1001")
            st_c = run([sys.executable, str(HERE / "project_status.py"), "ep_guard.json", "--prompts", "prompts/guard", "--takes", "takes/guard_nr",
                        "--selects", "selects", "--edl", "edit/guard_a.edl.json"], work)
            seen = seen and st_c.returncode == 0 and "the edit list holds another clip for this segment" in st_c.stdout \
                and f"--pick {s2['id']}=" in st_c.stdout and "a cut that is not the final one" not in st_a.stdout
            # someone who speaks in a later ref2va segment and has no voice sample: said at the top, before any segment
            novoice = json.loads((work / "ep_guard.json").read_text(encoding="utf-8"))
            spoken_seg = next(g for g in novoice["segments"] if any(sh.get("dialogue") for sh in g["shots"]))
            said = next(d for sh in spoken_seg["shots"] for d in sh.get("dialogue") or [])
            later_seg = novoice["segments"][novoice["segments"].index(spoken_seg) + 1]      # the same person speaks again, not accepted yet
            later_seg["shots"][0]["dialogue"] = [dict(said)]
            (work / "ep_guard_novoice.json").write_text(json.dumps(novoice, ensure_ascii=False, indent=1), encoding="utf-8")
            st_d = run([sys.executable, str(HERE / "project_status.py"), "ep_guard_novoice.json", "--prompts", "prompts/guard", "--takes", "takes/guard",
                        "--selects", "selects", "--edl", "edit/guard_b.edl.json"], work)
            top = st_d.stdout.split("\n" + s1["id"] + "  ")[0]
            wanted = said["speaker"]
            seen = seen and st_d.returncode == 0 and "first (a voice sample" not in st_a.stdout and "first (a voice sample" in top \
                and wanted in top and "is accepted - cut the sample from its take now" in top and f"build the prompt of {later_seg['id']}" in top \
                and "voice sample" in st_d.stdout.split("\n" + later_seg["id"] + "  ")[-1].split("after the segments")[0]
            # the commands it prints repeat how the project is run: the workflow file and the canvas of the drafts it already has
            # (not a one-off switch), and the takes log
            earlier = work / "takes/guard_nr" / s1["id"] / "made_before"
            earlier.mkdir(parents=True, exist_ok=True)
            (earlier / "run.json").write_text(json.dumps({"status": "success", "seed": 7, "workflow": "x/h3_ref2va_sage.api.json",
                                                          "overrides": ["136.width=864", "136.height=480", "146.value=false"]}), encoding="utf-8")
            st_f = run([sys.executable, str(HERE / "project_status.py"), "ep_guard.json", "--prompts", "prompts/guard", "--takes", "takes/guard_nr",
                        "--selects", "selects", "--edl", "edit/guard_a.edl.json"], work)
            drafts_line = next((ln for ln in st_f.stdout.splitlines() if "make drafts:" in ln), "")
            seen = seen and "h3_ref2va_sage.api.json" in drafts_line and "--set 136.width=864 --set 136.height=480" in drafts_line \
                and "146.value" not in drafts_line and "--log logs/takes.csv" in drafts_line
            # a first frame made before the segment it follows was accepted with another ending than planned: said until it
            # is made again or confirmed
            import takes as _tk
            ff = json.loads((work / "ep_guard.json").read_text(encoding="utf-8"))
            ff["segments"][0]["status"] = "accepted_with_deviation"
            ff["segments"][0]["accepted_deviations"] = ["he stops short of the window"]
            ff["segments"][0].setdefault("observed_end_state", "Hero stands short of the window.")
            follower = ff["segments"][1]
            follower.update(status="planned", continuity="@observed", first_frame="bible/first_s03.png")
            follower.pop("accepted_take", None)
            with in_dir(work):
                os.utime("bible/first_s03.png", (1, 1))
                old_pic = _tk.stale_first_frames(ff, Path("ep_guard.json"), Path("no_record.json"))
                Path("fits.json").write_text(json.dumps({"fits": {"bible/first_s03.png": _tk.text_sha(ff["segments"][0]["observed_end_state"].strip())}}),
                                             encoding="utf-8")
                confirmed = _tk.stale_first_frames(ff, Path("ep_guard.json"), Path("fits.json"))
                os.utime("bible/first_s03.png", None)
                remade = _tk.stale_first_frames(ff, Path("ep_guard.json"), Path("no_record.json"))
            seen = seen and list(old_pic) == [follower["id"]] and "older than the accepted take" in old_pic[follower["id"]]["why"] \
                and "he stops short of the window" in old_pic[follower["id"]]["why"] and not confirmed and not remade
            # the accepted take's file is gone, or has other content than when it was accepted: the overview says so too
            st_g = run([sys.executable, str(HERE / "project_status.py"), "ep_guard_moved.json", "--prompts", "prompts/guard", "--takes", "takes/guard",
                        "--selects", "selects", "--edl", "edit/guard_b.edl.json"], work)
            seen = seen and "NOT ON DISK" in st_g.stdout and "THE FILE WAS REPLACED since" in st_g.stdout and "accept it again" in st_g.stdout
            # a reference path written as an absolute path of another root (the project was moved): found by its tail
            with in_dir(work):
                moved_ref = _tk.find_media("/a/root/that/is/gone/bible/first_s03.png")
                alone = _tk.find_media("/a/root/that/is/gone/first_s03.png")
            seen = seen and moved_ref.as_posix() == "bible/first_s03.png" and alone.is_absolute()
            # a job that was queued for a segment and never fetched: named, and fetching it is the next step
            lost = work / "takes/guard" / s2["id"] / f"{s2['id']}_3001"
            lost.mkdir(parents=True, exist_ok=True)
            (lost / "handle.json").write_text(json.dumps({"prompt_id": "p-9", "fingerprint": "f", "seed": 3001, "queued_at": 1.0}), encoding="utf-8")
            st_e = run([sys.executable, str(HERE / "project_status.py"), "ep_guard.json", "--prompts", "prompts/guard", "--takes", "takes/guard",
                        "--selects", "selects", "--edl", "edit/guard_b.edl.json"], work)
            shutil.rmtree(lost)
            seen = seen and "queued and never collected" in st_e.stdout and f"--collect {Path('takes/guard') / s2['id'] / (s2['id'] + '_3001')}" in st_e.stdout \
                and "never collected" not in st_a.stdout
            record("project_status.py (what is accepted, refined and in the edit; the next step for a new storyboard)", "PASS" if seen else "FAIL",
                   "" if seen else f"{(st_a.stderr.strip() or st_a.stdout.strip())[-260:]} | {(st_b.stderr.strip() or st_b.stdout.strip())[-200:]} | "
                                   f"{(st_c.stderr.strip() or st_c.stdout.strip())[-300:]} | voices {wanted}: {(st_d.stderr.strip() or st_d.stdout.strip())[:300]} | "
                                   f"drafts: {drafts_line[-300:] or st_f.stdout.strip()[-300:]} | first frame: {old_pic} {confirmed} {remade}")
        except Exception as e:  # noqa: BLE001
            record("takes are checked against what they were made from", "FAIL", f"{type(e).__name__}: {e}")

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
            # what a mix is made from besides the cut: the music bed (settings and the file itself), the time of a line, the
            # subtitle file that was burned in - each changed after the mix, each has to be noticed
            if r.returncode == 0:
                import edl as _edl_s
                with in_dir(work):
                    edl_file, rep_file = Path("edit/ep.edl.json"), Path("final/ep.mix.report.json")
                    base = json.loads(edl_file.read_text(encoding="utf-8"))
                    clean = _edl_s.mix_is_stale(base, report_path=rep_file, edl_path=edl_file)
                    quieter, moved = json.loads(json.dumps(base)), json.loads(json.dumps(base))
                    quieter["music"]["gain_db"] = -13
                    moved["segments"][1]["lines"][0]["start"] += 0.3
                    said = [_edl_s.mix_is_stale(x, report_path=rep_file, edl_path=edl_file) for x in (quieter, moved)]
                    music_file = _edl_s.resolve(edl_file, base["music"]["file"])
                    was = music_file.read_bytes()
                    music_file.write_bytes(was + bytes(64))                  # another piece of music under the same name
                    said.append(_edl_s.mix_is_stale(base, report_path=rep_file, edl_path=edl_file))
                    music_file.write_bytes(was)
                    ass_text = Path("subs/ep.ass").read_text(encoding="utf-8")
                    Path("subs/ep.ass").write_text(ass_text + "\n; timed again\n", encoding="utf-8")
                    burned = _edl_s.mix_is_stale(base, report_path=rep_file, edl_path=edl_file)
                    Path("subs/ep.ass").write_text(ass_text, encoding="utf-8")
                    back = _edl_s.mix_is_stale(base, report_path=rep_file, edl_path=edl_file)
                    film = Path("final/ep.mp4")
                    film_was = film.read_bytes()
                    film.write_bytes(film_was + bytes(32))                   # another file under the film's name
                    swapped = _edl_s.mix_is_stale(base, report_path=rep_file, edl_path=edl_file)
                    film.write_bytes(film_was)
                good = clean is None and back is None and all(x and "sound in the edit list changed" in x for x in said) \
                    and bool(burned) and "burned into the picture" in burned and bool(swapped) and "is not the file this mix made" in swapped
                # a score that ends before the film: said before anything is rendered; a bed that loops is not complained about
                run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=330:duration=1", "short_music.wav"], work)
                brief = json.loads(json.dumps(base))
                brief["music"] = {"file": "short_music.wav", "gain_db": -10, "loop": False}
                (work / "edit/ep_short_music.edl.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
                short = run([sys.executable, str(HERE / "mix_episode.py"), "edit/ep_short_music.edl.json", "--out", "final/x.mp4", "--dry-run"], work)
                looped = run([sys.executable, str(HERE / "mix_episode.py"), "edit/ep.edl.json", "--out", "final/x.mp4", "--dry-run"], work)
                good = good and "before the film ends" in short.stdout and "120.value=" in short.stdout and "before the film ends" not in looped.stdout
                record("a mix is checked against its music, levels, line times and burned subtitles, not only against the cut",
                       "PASS" if good else "FAIL", "" if good else f"clean {clean} | {said} | {burned} | back {back} | {short.stdout.strip()[-200:]}")
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
            # a new take copied over a selected clip under the same name: names and frame numbers stay, the content does not -
            # the line times, the mix and the edit-list entry all belong to the old clip and each tool has to say so
            if r.returncode == 0:
                fresh = run([sys.executable, str(HERE / "mix_episode.py"), "edit/ep.edl.json", "--out", "final/ep_b.mp4", "--dry-run"], work)
                shutil.copyfile(work / "selects/s02.mp4", work / "selects/s02_first_version.mp4")
                run(["ffmpeg", "-v", "error", "-y", "-i", "selects/s02_first_version.mp4", "-c", "copy", "-metadata", "comment=another take",
                     "-f", "mp4", "selects/s02_new.tmp"], work)
                shutil.move(str(work / "selects/s02_new.tmp"), str(work / "selects/s02.mp4"))
                after = run([sys.executable, str(HERE / "mix_episode.py"), "edit/ep.edl.json", "--out", "final/ep_b.mp4", "--dry-run"], work)
                again = run([sys.executable, str(HERE / "make_edl.py"), "ep.json", "--selects", "selects", "--out", "edit/ep.edl.json"], work)
                import edl as _edl
                edl_now = json.loads((work / "edit/ep.edl.json").read_text(encoding="utf-8"))
                with in_dir(work):
                    old_mix = _edl.mix_is_stale(edl_now, report_path=Path("final/ep.mix.report.json"), edl_path=Path("edit/ep.edl.json"))
                (work / "selects/s02_first_version.mp4").unlink()
                seen = "clips changed" not in fresh.stdout and "clips changed after the subtitles were timed" in after.stdout \
                    and "has other content than when this entry was made" in again.stdout and bool(old_mix) and "other clips" in old_mix
                record("a clip replaced under the same name is noticed (line times, mix report, edit-list entry)", "PASS" if seen else "FAIL",
                       "" if seen else f"{after.stdout.strip()[-200:]} | {again.stdout.strip()[-200:]} | {old_mix}")
                # a second clip for one segment in the selects folder: said on a plain re-run, refused (not guessed at) on --overwrite,
                # and --overwrite keeps the edit list's own settings (the music set above)
                shutil.copyfile(work / "selects/s03.mp4", work / "selects/s03_refine.mp4")
                edl_cmd = [sys.executable, str(HERE / "make_edl.py"), "ep.json", "--selects", "selects", "--out", "edit/ep.edl.json"]
                plain, forced = run(edl_cmd, work), run(edl_cmd + ["--overwrite"], work)
                kept_edl = json.loads((work / "edit/ep.edl.json").read_text(encoding="utf-8"))
                picked = run(edl_cmd + ["--pick", "s03=selects/s03_refine.mp4"], work)
                (work / "selects/s03_refine.mp4").unlink()
                decided = "also holds s03_refine.mp4" in plain.stdout and plain.returncode == 0 \
                    and "AMBIGUOUS s03" in forced.stdout and forced.returncode == 2 \
                    and len(kept_edl["segments"]) == 3 and (kept_edl.get("music") or {}).get("file") == "music.wav" \
                    and picked.returncode == 0 and "s03_refine.mp4" in picked.stdout
                record("make_edl.py does not guess between two clips of one segment (and --overwrite keeps the edit list's settings)",
                       "PASS" if decided else "FAIL",
                       "" if decided else f"{plain.stdout.strip()[-160:]} | {forced.stdout.strip()[-200:]} | {picked.stdout.strip()[-120:]}")
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
