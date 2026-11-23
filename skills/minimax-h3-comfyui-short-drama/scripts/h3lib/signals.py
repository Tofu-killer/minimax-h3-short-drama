"""Picture signals read straight from a clip: hard cuts, black spans, frozen spans, sample frames.

Standard library + ffmpeg only. Shared by qc_probe.py (cut-count check against the storyboard),
contact_sheet.py (frames on both sides of every cut) and extract_tail_frame.py (--after-cut).

Hard-cut detection does NOT use ffmpeg's scene score with a fixed threshold: on real H3 footage a
cut between two shots of the same room scored 0.19-0.28 while flying paper and hand-held shake in
a single shot scored up to 0.30, so no threshold separates them. Instead each frame is reduced to
32x18 RGB and three things are required of a cut at frame i:
  step         the average picture of the 4 frames before i differs from the 4 frames after i
  isolation    that step is >= 4x the typical step on the calmer side of i (motion raises both sides)
  persistence  the picture stays different afterwards (a flash of 1-3 frames returns to the old picture)
Calibrated on one 38 s H3 film (7 of 7 cuts found, 0 false) plus synthetic cuts / flashes / pans.
Dissolves and fades are not hard cuts and are not reported. Treat the result as evidence, not truth.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from statistics import median

W, H, K = 32, 18, 4
MIN_STEP, MIN_RATIO, MIN_PERSIST, NEIGHBOURHOOD, FLOOR = 0.05, 4.0, 0.5, 24, 0.004


def live_takes(paths: list) -> tuple[list, int]:
    """A wildcard also finds files that are not takes of their own: comfy_submit.py moves a superseded take into a
    `_prev_*` folder inside the take folder, and extract_tail_frame.py --trim-freeze writes `<take>_trimmed.mp4`
    next to a take. They are left out when the take they belong to is in the list too - so a pattern over a
    folder looks at each take once, and a file named on its own is still looked at. -> (live paths, number skipped)."""
    from pathlib import Path as _P
    paths = [_P(p) for p in paths]
    in_prev = [any(part.startswith("_prev_") for part in p.parts) for p in paths]
    drop_prev = not all(in_prev)                      # every file is a superseded take: they were asked for by name
    present = {(p.parent, p.stem) for p in paths}
    live = []
    for p, old in zip(paths, in_prev):
        if old and drop_prev:
            continue
        if p.stem.endswith("_trimmed") and (p.parent, p.stem[:-len("_trimmed")]) in present:
            continue
        live.append(p)
    return live, len(paths) - len(live)


def take_label(path) -> str:
    """Name a take by its last two path parts when the file name alone says nothing ("s03_101/ComfyUI_00001_")."""
    from pathlib import Path as _P
    p = _P(path)
    return p.stem if not p.parent.name or p.parent.name in (".", "") else f"{p.parent.name}/{p.name}"


def probe(path: Path) -> dict:
    """{duration, fps, width, height, frames (estimate), has_audio}"""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,width,height,r_frame_rate,nb_frames", "-of", "json", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    import json
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    out = {"duration": float(d.get("format", {}).get("duration") or 0), "has_audio": any(
        s.get("codec_type") == "audio" for s in d.get("streams", [])), "fps": 0.0, "width": 0, "height": 0, "frames": 0}
    if v:
        num, den = (v.get("r_frame_rate") or "0/1").split("/")
        out["fps"] = float(num) / float(den or 1) if float(den or 1) else 0.0
        out["width"], out["height"] = int(v.get("width") or 0), int(v.get("height") or 0)
        try:
            out["frames"] = int(v.get("nb_frames"))
        except (TypeError, ValueError):
            out["frames"] = int(round(out["duration"] * out["fps"]))
    return out


def _thumbs(path: Path, seconds: float | None) -> list[list[int]]:
    cmd = ["ffmpeg", "-v", "error", "-i", str(path)]
    if seconds and seconds > 0:
        cmd += ["-t", f"{seconds:.3f}"]
    cmd += ["-an", "-vf", f"scale={W}:{H}:flags=area", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    size = W * H * 3
    return [list(raw[i:i + size]) for i in range(0, len(raw) - size + 1, size)]


def _diff(a: list[int], b: list[int]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / (W * H * 3 * 255.0)


def _mean2(a: list[int], b: list[int]) -> list[float]:
    return [(x + y) / 2 for x, y in zip(a, b)]


def _locate(frames: list[list[int]], i: int, n: int) -> int:
    """First frame of the new shot near i. The biggest frame-to-frame change is not good enough: when the new
    shot opens on violent motion (paper flying through the frame) a later frame changes more than the cut
    itself. A cut at j is where the two frames before differ from the two frames after, while the frames on
    each side agree with each other."""
    best, best_j = -1.0, i
    for j in range(max(2, i - 2), min(n - 2, i + 2) + 1):
        score = _diff(_mean2(frames[j - 2], frames[j - 1]), _mean2(frames[j], frames[j + 1])) \
            - 0.5 * (_diff(frames[j - 1], frames[j - 2]) + _diff(frames[j + 1], frames[j]))
        if score > best:
            best, best_j = score, j
    return best_j


def clipping(path: Path) -> dict | None:
    """{"peak_db", "flat_factor", "clipped"} for the first audio stream; None without audio.
    A high peak is not clipping. Clipping is a run of samples stuck at full scale (flat factor > 0)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "astats=metadata=0", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = r.stderr[r.stderr.rfind("Overall"):] if "Overall" in r.stderr else ""
    pk = re.search(r"Peak level dB: (-?[\d.]+|-?inf)", tail)
    ff = re.search(r"Flat factor: ([\d.]+)", tail)
    pc = re.search(r"Peak count: ([\d.]+)", tail)
    ns = re.search(r"Number of samples: (\d+)", tail)
    if not pk:
        return None
    try:
        peak = float(pk.group(1))
    except ValueError:
        peak = -120.0
    flat = float(ff.group(1)) if ff else 0.0
    share = (float(pc.group(1)) / max(1, int(ns.group(1)))) if pc and ns else 0.0
    return {"peak_db": round(peak, 2), "flat_factor": round(flat, 2),
            "clipped": (flat > 0 and peak >= -0.3) or (peak >= -0.05 and share > 0.001)}


def _window_sums(frames: list[list[int]], k: int) -> list[list[int] | None]:
    """sums[i] = per-pixel sum of frames[i : i + k] (None where the window does not fit)."""
    n = len(frames)
    out: list[list[int] | None] = [None] * n
    if n < k:
        return out
    cur = [sum(px) for px in zip(*frames[:k])]
    out[0] = cur
    for i in range(1, n - k + 1):
        add, sub = frames[i + k - 1], frames[i - 1]
        cur = [c + x - y for c, x, y in zip(cur, add, sub)]
        out[i] = cur
    return out


def detect_cuts(path: Path, fps: float | None = None, analyse_seconds: float | None = None) -> dict:
    """-> {"cuts": [{"t", "frame", "step", "ratio"}], "edge_jumps": [{"t", "frame", "jump"}], "frames": n, "fps": fps}
    `t` is the time of the first frame of the new shot. analyse_seconds limits the scan (drop a freeze tail).
    edge_jumps are abrupt picture changes inside the first / last 8 frames - too close to an end to be
    confirmed as a cut, but visible as a glitch when clips are joined."""
    fps = fps or probe(path)["fps"] or 24.0
    frames = _thumbs(path, analyse_seconds)
    n = len(frames)
    if n < 4 * K:
        return {"cuts": [], "edge_jumps": [], "frames": n, "fps": fps}
    sums = _window_sums(frames, K)
    norm = K * W * H * 3 * 255.0
    step = [0.0] * n
    for i in range(K, n - K + 1):
        a, b = sums[i - K], sums[i]
        step[i] = sum(abs(x - y) for x, y in zip(a, b)) / norm
    cuts = []
    for i in range(K, n - K + 1):
        s = step[i]
        if s < MIN_STEP or s < max(step[max(K, i - 6):i + 7]):
            continue
        before = [v for v in step[max(K, i - K - NEIGHBOURHOOD):max(K, i - K)]]
        after = [v for v in step[i + K + 1:i + K + 1 + NEIGHBOURHOOD]]
        sides = [median(x) for x in (before, after) if len(x) >= 6]
        base = max(min(sides), FLOOR) if sides else FLOOR
        ratio = s / base
        if ratio < MIN_RATIO:
            continue
        if i - 2 * K < 0 or i + 2 * K > n or sums[i + K] is None:              # too close to an end to confirm:
            continue                                                           # reported as an edge jump instead
        far = sum(abs(x - y) for x, y in zip(sums[i - 2 * K], sums[i + K])) / norm
        if far < MIN_PERSIST * s:                                              # the change does not last: a flash
            continue
        j = _locate(frames, i, n)                                              # the exact first frame of the new shot
        jump = _diff(frames[j], frames[j - 1])
        if jump < 0.5 * s:                                                     # no single frame carries the change: a flash or a blur
            continue
        if j - 2 >= 0 and j + 3 < n:                                           # a flash of 1-3 frames returns to the old picture
            across = min(_diff(frames[j - 2], frames[j + 1]), _diff(frames[j - 2], frames[j + 3]))
            if across < MIN_PERSIST * jump:
                continue
        if cuts and j - cuts[-1]["frame"] < 6:
            if s > cuts[-1]["step"]:
                cuts[-1] = {"t": round(j / fps, 3), "frame": j, "step": round(s, 3), "ratio": round(ratio, 1)}
            continue
        cuts.append({"t": round(j / fps, 3), "frame": j, "step": round(s, 3), "ratio": round(ratio, 1)})
    # A different picture in the first / last few frames (a stray frame of the neighbouring shot, a flash)
    # cannot be confirmed as a cut, but it shows as a glitch at the join: report it separately.
    edge = []
    for zone in (range(1, 2 * K), range(n - 2 * K, n)):
        d = sorted(((_diff(frames[q], frames[q - 1]), q) for q in zone), reverse=True)
        (top, q), second = d[0], d[1][0]
        if top >= MIN_STEP and top >= 3 * max(second, FLOOR) and not any(abs(q - c["frame"]) < 3 for c in cuts):
            edge.append({"t": round(q / fps, 3), "frame": q, "jump": round(top, 3)})      # one isolated jump, not motion
    return {"cuts": cuts, "edge_jumps": edge, "frames": n, "fps": fps}


def black_and_freeze(path: Path, analyse_seconds: float | None = None, freeze_min: float = 1.0,
                     black_min: float = 0.25) -> dict:
    """-> {"black": [[start, end]], "freeze": [[start, end]]} (seconds)."""
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path)]
    if analyse_seconds and analyse_seconds > 0:
        cmd += ["-t", f"{analyse_seconds:.3f}"]
    cmd += ["-an", "-vf", f"freezedetect=n=-60dB:d={freeze_min},blackdetect=d={black_min}:pix_th=0.05", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    black = [[round(float(a), 3), round(float(b), 3)] for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)]
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", err)]
    limit = analyse_seconds or probe(path)["duration"]
    freeze = [[round(s, 3), round(ends[i] if i < len(ends) else limit, 3)] for i, s in enumerate(starts)]
    return {"black": black, "freeze": freeze}


def motion(path: Path, analyse_seconds: float | None = None) -> float | None:
    """Median frame-to-frame change (mean absolute grey difference at 240 px width, 0-255 scale).
    Field numbers for H3: action shots >= 2.5, close-up acting >= 1.8, below 1.0 the clip is close to a still."""
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path)]
    if analyse_seconds and analyse_seconds > 0:
        cmd += ["-t", f"{analyse_seconds:.3f}"]
    cmd += ["-an", "-vf", "scale=240:-2,format=gray,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
            "-f", "null", "-"]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    vals = [float(x) for x in re.findall(r"YAVG=([\d.]+)", out)][1:]          # the first frame has nothing to differ from
    return round(median(vals), 2) if vals else None


def burned_text(path: Path, analyse_seconds: float | None = None, start: float | None = None) -> list[list[float]] | None:
    """Spans [[start, end]] where caption-like text sits in the lower third of the picture; None without numpy.

    What it looks for: bright strokes with a dark edge right next to them (white glyphs with an outline or
    shadow), many separate strokes along a row, spread across the middle of the frame, no column filled
    from top to bottom (that would be bars or blinds, not writing), and - the decisive part - the same
    pixels lit in consecutive samples for at least half a second while the picture goes on.
    Checked on one real film whose takes carried burned captions (all five caption spans found to within
    0.2 s, none reported on the take without captions or on test patterns). Dark or coloured text without
    an outline is not detected; treat an empty result as "nothing obvious", not as proof."""
    try:
        import numpy as np
    except ImportError:
        return None
    w, h, fps = 480, 270, 6
    bh = int(h * 0.34)
    cmd = ["ffmpeg", "-v", "error"]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(path)]
    if analyse_seconds and analyse_seconds > 0:
        cmd += ["-t", f"{analyse_seconds:.3f}"]
    cmd += ["-an", "-vf", f"fps={fps},scale={w}:{h},crop={w}:{bh}:0:{h - bh},format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (w * bh)
    if n < 3:
        return []
    band = np.frombuffer(raw[:n * w * bh], np.uint8).reshape(n, bh, w)
    flags, prev = [], None
    for y in band:
        bright, dark = y > 200, y < 70
        near = np.zeros_like(dark)
        for dx, dy in ((1, 0), (-1, 0), (2, 0), (-2, 0), (0, 1), (0, -1), (0, 2), (0, -2)):
            near |= np.roll(np.roll(dark, dy, axis=0), dx, axis=1)
        m = bright & near
        ok = False
        count = int(m.sum())
        if count >= 40:
            ys, xs = np.where(m)
            rows = m[ys.min():ys.max() + 1]
            transitions = int((np.diff(rows.astype(np.int8), axis=1) == 1).sum(axis=1).max())
            column_fill = float(m.sum(axis=0).max()) / bh
            same = float((m & prev).sum()) / max(1, int((m | prev).sum())) if prev is not None else 0.0
            ok = (xs.max() - xs.min() >= 60 and transitions >= 6 and 0.2 <= xs.mean() / w <= 0.8
                  and column_fill <= 0.6 and same >= 0.5)
        flags.append(ok)
        prev = m
    spans, i, off = [], 0, float(start or 0.0)
    while i < n:
        if flags[i]:
            j = i
            while j + 1 < n and flags[j + 1]:
                j += 1
            if j - i + 1 >= 3:                                        # held for at least half a second
                spans.append([round(off + max(0, i - 1) / fps, 2), round(off + (j + 1) / fps, 2)])
            i = j + 1
        else:
            i += 1
    return spans


def match_cuts(expected: list[float], detected: list[float], tolerance: float = 0.5) -> dict:
    """Pair expected cut times (shot starts from the storyboard) with detected ones."""
    left = list(detected)
    pairs, missing = [], []
    for e in expected:
        best = min(left, key=lambda d: abs(d - e), default=None)
        if best is not None and abs(best - e) <= tolerance:
            pairs.append({"expected": round(e, 3), "detected": best, "offset": round(best - e, 3)})
            left.remove(best)
        else:
            missing.append(round(e, 3))
    return {"expected": len(expected), "detected": len(detected), "matched": pairs, "missing": missing,
            "extra": [round(d, 3) for d in left], "ok": not missing and not left}


def grab_frame(path: Path, t: float, dest: Path, width: int | None = None) -> bool:
    vf = ["-vf", f"scale={width}:-2"] if width else []
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(path), "-frames:v", "1",
                        *vf, str(dest)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0 and Path(dest).exists()


FONTS = ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"]


def find_font() -> Path | None:
    """A TrueType font for frame stamps: H3_QC_FONT, then Arial / DejaVu, then any .ttf under the system font folders."""
    import glob
    import os
    for c in [os.environ.get("H3_QC_FONT")] + FONTS:
        if c and Path(c).is_file():
            return Path(c)
    for root in ("/usr/share/fonts", "/usr/local/share/fonts"):
        hits = sorted(glob.glob(root + "/**/*.ttf", recursive=True))
        if hits:
            return Path(hits[0])
    return None


CJK_FAMILIES = ["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Source Han Sans SC", "Noto Sans SC", "WenQuanYi Zen Hei",
                "WenQuanYi Micro Hei", "SimHei", "Heiti SC"]
CJK_FILES = {"Microsoft YaHei": ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyh.ttf"], "SimHei": ["C:/Windows/Fonts/simhei.ttf"],
             "PingFang SC": ["/System/Library/Fonts/PingFang.ttc"], "Heiti SC": ["/System/Library/Fonts/STHeiti Medium.ttc"]}


def cjk_fonts() -> list[str]:
    """Installed font families that can draw Chinese, best guess first. Uses fontconfig when it is there (Linux,
    Homebrew ffmpeg), otherwise the well-known system font files (Windows, macOS). [] = none found."""
    import shutil
    import subprocess
    found: list[str] = []
    if shutil.which("fc-list"):
        r = subprocess.run(["fc-list", ":lang=zh", "family"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        have = {name.strip().replace("\\", "") for line in r.stdout.splitlines() for name in line.split(",") if name.strip()}
        found = [f for f in CJK_FAMILIES if f in have] + sorted(have - set(CJK_FAMILIES))
    for family, files in CJK_FILES.items():
        if family not in found and any(Path(f).is_file() for f in files):
            found.append(family)
    return found


def subtitle_font_note(requested: str, text_has_cjk: bool = True) -> str | None:
    """None when the font the subtitles ask for is installed (or nothing can be checked). Otherwise one sentence
    saying what the renderer will do instead - before a file full of empty boxes is rendered and accepted."""
    if not text_has_cjk:
        return None
    have = cjk_fonts()
    if requested in have:
        return None
    if not have:
        return (f"no font with Chinese glyphs was found on this machine (asked for \"{requested}\"): burned subtitles would show "
                f"empty boxes. Install one (Linux: fonts-noto-cjk) or pass --font with an installed family")
    return f"subtitle font \"{requested}\" is not installed: the renderer falls back to another font - use --font \"{have[0]}\" to choose it yourself"


def stamped_sheet(path: Path, samples: list[tuple[float, str]], sheet: Path, width: int = 480, cols: int = 4,
                  font: Path | None = None) -> None:
    """Tile the frames at the given (seconds, tag) into one image, each stamped "<seconds>s <tag>".
    Tags must be plain words (letters, digits, spaces). Raises RuntimeError when ffmpeg fails."""
    import tempfile
    font = font if font is not None else find_font()
    path, sheet = Path(path).resolve(), Path(sheet).resolve()
    sheet.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for i, (t, tag) in enumerate(samples):
            vf = f"scale={width}:-2"
            if font:                                 # run inside the font folder so the filter needs no path escaping
                vf += (f",drawtext=fontfile={font.name}:text='{t:.2f}s {tag}':x=8:y=h-th-10:fontsize={max(14, width // 22)}"
                       f":fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=6")
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(path), "-frames:v", "1",
                                "-vf", vf, str(tmp / f"f_{i:03d}.png")], capture_output=True, text=True, encoding="utf-8", errors="replace",
                               cwd=str(font.parent) if font else None)
            if r.returncode != 0 or not (tmp / f"f_{i:03d}.png").exists():
                # asked for a time at or past the last frame: take the last frame the file has
                r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-1", "-i", str(path), "-vf", vf, "-update", "1",
                                    str(tmp / f"f_{i:03d}.png")], capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   cwd=str(font.parent) if font else None)
            if r.returncode != 0 or not (tmp / f"f_{i:03d}.png").exists():
                raise RuntimeError(f"ffmpeg could not extract a frame at {t:.2f}s from {path}: {r.stderr.strip()[-300:]}")
        cols = max(1, min(cols, len(samples)))
        rows = -(-len(samples) // cols)
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(tmp / "f_%03d.png"),
                            "-vf", f"tile={cols}x{rows}:padding=4:color=black", "-frames:v", "1", "-update", "1", str(sheet)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg could not build the sheet: {r.stderr.strip()[-300:]}")
