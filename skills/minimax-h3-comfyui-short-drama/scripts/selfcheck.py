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
        record("make synthetic clips", "PASS" if ok else "FAIL", "" if ok else "ffmpeg could not encode test clips (libx264 / aac missing?)")
        if not ok:
            sys.exit(1)

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
                             shot(2, 3.0, "a close-up on Hero's face", "Hero sits down, looks into the lens and speaks one calm sentence.", "开始吧")]},
                  {"id": "s03", "duration": 5, "scene_id": "room", "character_ids": ["hero"], "soundscape": "The hum fades under a soft breath.",
                   "continuity": "Hero sits on the chair at frame left, facing the camera.", "end_state": "Hero sits still at frame left, eyes closed.",
                   "shots": [dict(shot(1, 0, "a medium close-up on Hero", "Hero breathes out, lowers his shoulders and closes his eyes, then holds still."), end_hold=True)]}]}
        (work / "ep.json").write_text(json.dumps(ep, ensure_ascii=False, indent=1), encoding="utf-8")

        # ---- the real scripts -----------------------------------------------------------------------
        ok, note = script("validate_episode.py", ["ep.json", "--rhythm"], work)
        record("validate_episode.py", "PASS" if ok else "FAIL", note)
        ok, note = script("build_prompts.py", ["ep.json", "--out", "prompts"], work)
        record("build_prompts.py", "PASS" if ok else "FAIL", note)
        ok, note = script("lint_prompt.py", ["prompts/s02.txt", "--seconds", "6", "--images", "2", "--audios", "0"], work)
        record("lint_prompt.py", "PASS" if ok else "FAIL", note)

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
