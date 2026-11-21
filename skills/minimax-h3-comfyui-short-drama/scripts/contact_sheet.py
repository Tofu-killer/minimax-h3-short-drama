#!/usr/bin/env python3
"""Contact sheets for visual QC: frames picked where problems hide, each stamped with its time.

    python3 contact_sheet.py "takes/ep01/s03/*.mp4" --freeze-tail 1.0
    python3 contact_sheet.py final/ep01.mp4 --max 24 --cols 6 --out-dir qc/sheets

Instead of 12 evenly spaced frames, each sheet holds: the first and the last moving frame, the frame just
before and just after every hard cut (so a shot that never happened, or one that was invented, is visible
at a glance), one or two frames from the middle of every shot, and the first frame of any black / frozen
span. Frames are in time order; the stamp reads "<seconds>s <tag>".
Use the sheet to choose in / out points and to check identity, props and staging shot by shot.

Writes <clip>_sheet.png next to the clip (or into --out-dir) and prints the legend.
Needs ffmpeg / ffprobe; standard library only. Stamps need a TrueType font: Arial / DejaVu are found
automatically, or set H3_QC_FONT=<path to .ttf>; without a font the sheet is unstamped and the printed
legend gives the times.
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import signals  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}
FONTS = ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"]


def find_font() -> Path | None:
    for c in [os.environ.get("H3_QC_FONT")] + FONTS:
        if c and Path(c).is_file():
            return Path(c)
    for root in ("/usr/share/fonts", "/usr/local/share/fonts"):
        hits = sorted(glob.glob(root + "/**/*.ttf", recursive=True))
        if hits:
            return Path(hits[0])
    return None


def plan_samples(dur: float, usable: float, fps: float, cuts: list[float], black: list, freeze: list, limit: int) -> list[tuple[float, str]]:
    f = 1.0 / (fps or 24.0)
    must = [(min(2 * f, usable / 2), "start"), (max(0.0, usable - 2 * f), "end")]
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
    picked = must[:limit]
    for item in extra:
        if len(picked) >= limit:
            break
        if all(abs(item[0] - t) > 3 * f for t, _tag in picked):
            picked.append(item)
    return sorted(picked)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+", help="clips or glob patterns (quote them on Windows)")
    ap.add_argument("--freeze-tail", type=float, default=0.0, help="seconds of declared end freeze to leave out")
    ap.add_argument("--max", type=int, default=12, help="frames per sheet")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--width", type=int, default=480, help="width of one frame in the sheet")
    ap.add_argument("--out-dir")
    a = ap.parse_args()

    paths: list[Path] = []
    for pat in a.files:
        hits = sorted(glob.glob(pat, recursive=True)) or ([pat] if Path(pat).exists() else [])
        paths += [Path(h) for h in hits if Path(h).suffix.lower() in VIDEO_EXT]
    if not paths:
        sys.exit("no clips matched")
    font = find_font()
    if not font:
        print("NOTE: no TrueType font found (set H3_QC_FONT) - sheets are unstamped, use the legend below")
    for p in paths:
        info = signals.probe(p)
        if not info["width"]:
            print(f"skip {p}: no video stream")
            continue
        dur = info["duration"]
        usable = max(0.2, dur - a.freeze_tail)
        det = signals.detect_cuts(p, info["fps"], usable if a.freeze_tail else None)
        bf = signals.black_and_freeze(p, usable if a.freeze_tail else None)
        samples = plan_samples(dur, usable, info["fps"], [c["t"] for c in det["cuts"]], bf["black"], bf["freeze"], a.max)
        dest_dir = Path(a.out_dir) if a.out_dir else p.parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        sheet = (dest_dir / f"{p.stem}_sheet.png").resolve()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            for i, (t, tag) in enumerate(samples):
                vf = f"scale={a.width}:-2"
                if font:                             # run inside the font folder so the filter needs no path escaping
                    vf += (f",drawtext=fontfile={font.name}:text='{t:.2f}s {tag}':x=8:y=h-th-10:fontsize={max(14, a.width // 22)}"
                           f":fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=6")
                r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(p.resolve()), "-frames:v", "1",
                                    "-vf", vf, str(tmp / f"f_{i:03d}.png")], capture_output=True, text=True,
                                   cwd=str(font.parent) if font else None)
                if r.returncode != 0 or not (tmp / f"f_{i:03d}.png").exists():
                    sys.exit(f"ffmpeg could not extract a frame at {t:.2f}s from {p}: {r.stderr.strip()[-300:]}")
            cols = min(a.cols, len(samples))
            rows = -(-len(samples) // cols)
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(tmp / "f_%03d.png"),
                                "-vf", f"tile={cols}x{rows}:padding=4:color=black", "-frames:v", "1", "-update", "1", str(sheet)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                sys.exit(f"ffmpeg could not build the sheet: {r.stderr.strip()[-300:]}")
        print(f"{sheet}")
        print(f"  {dur:.2f}s, {len(det['cuts']) + 1} shot(s), cuts at {[c['t'] for c in det['cuts']] or 'none'}"
              + (f", black {bf['black']}" if bf["black"] else "") + (f", frozen {bf['freeze']}" if bf["freeze"] else ""))
        print("  " + " | ".join(f"{i + 1}: {t:.2f}s {tag}" for i, (t, tag) in enumerate(samples)))


if __name__ == "__main__":
    main()
