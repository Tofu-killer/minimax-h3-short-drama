#!/usr/bin/env python3
"""Extract the hand-off frame from the end of a clip (duration - 0.2 s by default).

    python3 extract_tail_frame.py clips/seg_01.mp4 --out bible/handoff/seg_01_tail.png [--back 0.2] [--trim-freeze 1.0]

With --trim-freeze N also writes <clip>_trimmed.mp4 with the last N seconds
(the declared freeze tail) removed, so the frame comes from the last *moving*
second and the trimmed clip is what goes to the editor.
"""
import argparse, json, subprocess
from pathlib import Path


def duration(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(p)],
                         capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip"); ap.add_argument("--out", required=True)
    ap.add_argument("--back", type=float, default=0.2, help="seconds before the (trimmed) end")
    ap.add_argument("--trim-freeze", type=float, default=0.0, help="seconds of declared freeze tail to cut")
    a = ap.parse_args()
    clip = Path(a.clip); dur = duration(clip)
    end = dur - a.trim_freeze
    t = max(0.0, end - a.back)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(clip), "-frames:v", "1", a.out], check=True)
    print(f"tail frame @ {t:.3f}s -> {a.out}")
    if a.trim_freeze > 0:
        trimmed = clip.with_name(clip.stem + "_trimmed.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-t", f"{end:.3f}", "-c", "copy", str(trimmed)], check=True)
        print(f"trimmed clip ({a.trim_freeze}s freeze removed) -> {trimmed}")


if __name__ == "__main__":
    main()
