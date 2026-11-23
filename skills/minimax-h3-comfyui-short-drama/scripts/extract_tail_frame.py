#!/usr/bin/env python3
"""Extract a hand-off frame from a clip: the last moving frame, or the first frame after a hard cut.

    python3 extract_tail_frame.py clips/seg_01.mp4 --out bible/handoff/seg_01_tail.png [--back 0.2] [--trim-freeze 1.0]
    python3 extract_tail_frame.py drafts/two_shot_probe.mp4 --out bible/firstframes/s04_reverse.png --after-cut 1

Default: the frame at (end - --back) seconds; --back is 0.2 s, which steps off the very last frames (they are the ones
most often smeared by motion). observe_take.py shows the frames around the same point on its sheet. With --trim-freeze N the last N seconds (the declared freeze
tail) are ignored, so the frame comes from the last MOVING second; <clip>_trimmed.mp4 is also written next to
the clip without that tail (--no-trimmed-clip skips it; make_edl.py trims the tail by itself, so the file is
only a convenience). Use --size with the generation canvas when the frame will be a first frame: take it from
the refined take and scale it down, and look at it first - a frame with burned-in text or UI makes a bad anchor.

--after-cut N: the first clean frame of the shot that starts at the N-th hard cut (1 = first cut). This is
how a reverse shot or a close-up gets a first frame that belongs to the SAME space: generate a short draft
whose prompt asks for two shots with a hard cut from the master frame, then harvest the frame after the cut
and use it as the first frame of the real segment. Falls back to the tail frame (and says so) when the clip
has fewer cuts than asked for.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import signals  # noqa: E402


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()


def duration(p):
    if not Path(p).is_file():
        raise FileNotFoundError(2, "No such file", str(p))
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(p)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    try:
        return float(json.loads(out)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        print(f"{p} is not a video ffprobe can read", file=sys.stderr)
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("clip")
    ap.add_argument("--out", required=True)
    ap.add_argument("--back", type=float, default=0.2, help="seconds before the (trimmed) end")
    ap.add_argument("--trim-freeze", type=float, default=0.0, help="seconds of declared freeze tail to cut")
    ap.add_argument("--after-cut", type=int, default=0, help="take the first frame after the N-th hard cut instead of the tail")
    ap.add_argument("--size", help="WxH: scale and centre-crop the frame to the generation canvas (e.g. 1344x768) - a first frame "
                                   "must have the size of the clip it starts")
    ap.add_argument("--no-trimmed-clip", action="store_true", help="with --trim-freeze: do not write <clip>_trimmed.mp4")
    a = ap.parse_args()
    clip = Path(a.clip)
    dur = duration(clip)
    end = dur - a.trim_freeze
    t, what = max(0.0, end - a.back), "tail frame"
    if a.after_cut > 0:
        info = signals.probe(clip)
        det = signals.detect_cuts(clip, info["fps"], end if a.trim_freeze else None)
        cuts = [c["t"] for c in det["cuts"]]
        if len(cuts) >= a.after_cut:
            t = min(end, cuts[a.after_cut - 1] + 2.0 / (info["fps"] or 24.0))     # two frames in: past any blended frame
            what = f"first frame after cut {a.after_cut} (cut at {cuts[a.after_cut - 1]:.3f}s)"
        else:
            print(f"only {len(cuts)} hard cut(s) found (asked for cut {a.after_cut}): the clip did not cut as prompted - "
                  f"falling back to the tail frame; check the draft before using it")
            what = "tail frame (FALLBACK - no such cut)"
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    vf = []
    if a.size:
        w, h = (int(x) for x in a.size.lower().split("x"))
        vf = ["-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(clip), "-frames:v", "1", *vf, a.out], check=True)
    print(f"{what} @ {t:.3f}s -> {a.out}" + (f" ({a.size})" if a.size else ""))
    if a.trim_freeze > 0 and not a.no_trimmed_clip:
        trimmed = clip.with_name(clip.stem + "_trimmed.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-t", f"{end:.3f}", "-c", "copy", str(trimmed)], check=True)
        print(f"trimmed clip ({a.trim_freeze}s freeze removed) -> {trimmed}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
