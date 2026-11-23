#!/usr/bin/env python3
"""Contact sheets for visual QC: frames picked where problems hide, each stamped with its time.

    python3 contact_sheet.py "takes/ep01/s03/**/*.mp4" --episode episodes/ep01.json
    python3 contact_sheet.py final/ep01.mp4 --max 24 --cols 6 --out-dir qc/sheets

Instead of 12 evenly spaced frames, each sheet holds: the first frame, the last moving frame ("end": with --episode
the declared 1 s end hold of a segment is left out automatically) and the very last
frame, any frame qc_probe would flag as an abrupt change at a clip end, the frame just
before and just after every hard cut (so a shot that never happened, or one that was invented, is visible
at a glance), one or two frames from the middle of every shot, and the first frame of any black / frozen
span. Frames are in time order; the stamp reads "<seconds>s <tag>".
Use the sheet to choose in / out points and to check identity, props and staging shot by shot.

Writes <clip>_sheet.png next to the clip, or <take folder>_<clip>_sheet.png into --out-dir, and prints the legend.
Files inside _prev_* folders (superseded takes) are skipped.
Needs ffmpeg / ffprobe; standard library only. Stamps need a TrueType font: Arial / DejaVu are found
automatically, or set H3_QC_FONT=<path to .ttf>; without a font the sheet is unstamped and the printed
legend gives the times.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
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

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}


def plan_samples(dur: float, usable: float, fps: float, cuts: list[float], black: list, freeze: list, limit: int,
                 edge_jumps: list[int] = (), n_frames: int = 0) -> list[tuple[float, str]]:
    f = 1.0 / (fps or 24.0)
    must = [(min(2 * f, usable / 2), "start"), (max(0.0, usable - 2 * f), "end")]
    # ffmpeg's seek returns the first frame at or after the time asked for: a quarter frame before frame k's
    # timestamp lands on frame k exactly, also after rounding to milliseconds
    for k in edge_jumps:                            # frames qc_probe flags as an abrupt change at a clip end
        must.append((max(0.0, (k - 0.25) * f), "edge jump"))
    if n_frames and usable >= dur - f:              # the very last frame too: a stray frame there flashes at the join
        must.append((max(0.0, (n_frames - 1.25) * f), "last frame"))
    for c in cuts:
        must += [(max(0.0, c - 2 * f), "before cut"), (min(usable, c + f), "after cut")]
    for s, _e in black:
        must.append((s + f, "black"))
    for s, _e in freeze:
        must.append((s + f, "frozen"))
    bounds = [0.0] + list(cuts) + [usable]
    shots = sorted(((e - s, s, e) for s, e in zip(bounds, bounds[1:])), reverse=True)
    extra = []
    for length, s, e in shots:                       # middles: longest shots first, a second frame for long ones
        if length >= 1.5:
            extra.append((s + length / 2, "mid"))
    for length, s, e in shots:
        if length >= 5.0:
            extra += [(s + length / 4, "mid"), (s + 3 * length / 4, "mid")]
    seen: list[tuple[float, str]] = []                 # one frame, one tile: keep the first label for the same frame
    for item in must:
        if all(abs(item[0] - t) > 0.4 * f for t, _tag in seen):
            seen.append(item)
    picked = seen[:limit]
    for item in extra:
        if len(picked) >= limit:
            break
        if all(abs(item[0] - t) > 3 * f for t, _tag in picked):
            picked.append(item)
    return sorted(picked)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+", help="clips or glob patterns (quote them on Windows)")
    ap.add_argument("--freeze-tail", type=float, default=None,
                    help="length of the declared end freeze to leave out, so that \"end\" is the last MOVING frame. Default: 1.0 "
                         "with --episode, on the segments whose last shot has end_hold (the rule make_edl.py, qc_probe.py and "
                         "observe_take.py use); 0 without --episode. Given without --episode it applies to every clip")
    ap.add_argument("--episode", help="storyboard JSON (the segment id is read from each clip's path)")
    ap.add_argument("--max", type=int, default=12, help="frames per sheet")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--width", type=int, default=480, help="width of one frame in the sheet")
    ap.add_argument("--out-dir")
    a = ap.parse_args()
    if a.freeze_tail is None:
        a.freeze_tail = 1.0 if a.episode else 0.0

    paths: list[Path] = []
    for pat in a.files:
        hits = sorted(glob.glob(pat, recursive=True)) or ([pat] if Path(pat).exists() else [])
        paths += [Path(h) for h in hits if Path(h).suffix.lower() in VIDEO_EXT]
    paths, skipped = signals.live_takes(paths)
    if skipped:
        print(f"note: {skipped} file(s) skipped: superseded takes in _prev_* folders, and *_trimmed.mp4 copies (extract_tail_frame.py) of takes that are in the list")
    if not paths:
        sys.exit("no clips matched")
    used: set[str] = set()
    stems = [x.stem for x in paths]
    segs = {}
    if a.episode:
        segs = {x["id"]: x for x in json.loads(Path(a.episode).read_text(encoding="utf-8"))["segments"]}
    font = signals.find_font()
    if not font:
        print("NOTE: no TrueType font found (set H3_QC_FONT) - sheets are unstamped, use the legend below")
    for p in paths:
        info = signals.probe(p)
        if not info["width"]:
            print(f"skip {p}: no video stream")
            continue
        dur = info["duration"]
        seg = next((segs[t] for t in re.split(r"[^A-Za-z0-9]+", str(p)) if t in segs), None)
        shots = (seg or {}).get("shots") or []
        hold = a.freeze_tail > 0 and (not segs or bool(shots and shots[-1].get("end_hold")))
        usable = max(0.2, dur - a.freeze_tail) if hold else dur
        det = signals.detect_cuts(p, info["fps"], usable if hold else None)
        bf = signals.black_and_freeze(p, usable if hold else None)
        samples = plan_samples(dur, usable, info["fps"], [c["t"] for c in det["cuts"]], bf["black"], bf["freeze"], a.max,
                               [e["frame"] for e in det["edge_jumps"]], det["frames"])
        dest_dir = Path(a.out_dir) if a.out_dir else p.parent
        name = p.stem
        take_folder = re.fullmatch(r".+_\d+", p.parent.name)             # "<tag>_<seed>": the folder comfy_submit.py makes per take
        if a.out_dir and p.parent.name not in name and (take_folder or stems.count(p.stem) > 1):
            name = f"{p.parent.name}_{name}"                              # "s03_101/ComfyUI_00001_.mp4" -> s03_101_ComfyUI_00001_
        base, k = name, 2
        while name in used:                                               # never overwrite a sheet made in this run
            name, k = f"{base}_{k}", k + 1
        used.add(name)
        sheet = (dest_dir / f"{name}_sheet.png").resolve()
        try:
            signals.stamped_sheet(p, samples, sheet, a.width, a.cols, font)
        except RuntimeError as e:
            sys.exit(str(e))
        print(f"{sheet}")
        print(f"  {dur:.2f}s, {len(det['cuts']) + 1} shot(s), cuts at {[c['t'] for c in det['cuts']] or 'none'}"
              + (f", black {bf['black']}" if bf["black"] else "") + (f", frozen {bf['freeze']}" if bf["freeze"] else ""))
        print("  " + " | ".join(f"{i + 1}: {t:.2f}s {tag}" for i, (t, tag) in enumerate(samples)))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
