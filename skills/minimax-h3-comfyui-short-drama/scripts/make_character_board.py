#!/usr/bin/env python3
"""Assemble single-view character images into one 16:9 review board (for people to look at, not for the model).

    python3 make_character_board.py --face bible/chars/lin_face.png \
        --views bible/chars/lin_full.png bible/chars/lin_side.png bible/chars/lin_back.png \
        --out bible/chars/lin_sheet.png

Layout: the head-and-shoulders close-up fills the left third, the full-body views share the right two thirds,
each fitted into its cell on white with nothing cropped (views generated on the same canvas come out at the
same scale, so heights can be compared). The board is a REVIEW aid: check that
face, hair, outfit and proportions agree across the views. Do not use it as a reference image - references stay
single-person, single-view (references/image-stage.md).

Needs ffmpeg; standard library only.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--face", required=True, help="head-and-shoulders close-up")
    ap.add_argument("--views", nargs="+", required=True, help="1-4 full-body views, in the order they should appear (front, side, back)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="2560x1440", help="board size WxH (16:9; multiples of 32 recommended)")
    ap.add_argument("--margin", type=int, default=32)
    a = ap.parse_args()
    paths = [Path(a.face)] + [Path(v) for v in a.views]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        sys.exit("missing image(s): " + ", ".join(missing))
    if not 1 <= len(a.views) <= 4:
        sys.exit("give 1 to 4 full-body views")
    w, h = (int(x) for x in a.size.lower().split("x"))
    m = a.margin
    left_w = w // 3
    n = len(a.views)
    cell_w = (w - left_w) // n
    inner_h = h - 2 * m

    def fit(i: int, cw: int) -> str:                      # scale into the cell, keep aspect, centre on white
        return (f"[{i}:v]scale={cw - 2 * m}:{inner_h}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={cw}:{h}:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1[c{i}]")
    chains = [fit(0, left_w)] + [fit(i + 1, cell_w) for i in range(n)]
    graph = ";".join(chains) + ";" + "".join(f"[c{i}]" for i in range(n + 1)) + f"hstack=inputs={n + 1}," \
        f"pad={w}:{h}:(ow-iw)/2:0:color=white[out]"
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for p in paths:
        cmd += ["-i", str(p)]
    cmd += ["-filter_complex", graph, "-map", "[out]", "-frames:v", "1", "-update", "1", str(a.out)]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit("ffmpeg failed: " + r.stderr.strip()[-400:])
    print(f"{a.out}: {w}x{h}, face + {n} view(s) - a review board, not a reference image")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
