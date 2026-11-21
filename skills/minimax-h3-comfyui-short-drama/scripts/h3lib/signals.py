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


def probe(path: Path) -> dict:
    """{duration, fps, width, height, frames (estimate), has_audio}"""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,width,height,r_frame_rate,nb_frames", "-of", "json", str(path)],
                       capture_output=True, text=True)
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
        lo, hi = max(1, i - 2), min(n - 1, i + 2)                              # the exact first frame of the new shot
        j = max(range(lo, hi + 1), key=lambda q: _diff(frames[q], frames[q - 1]))
        if j - 2 >= 0 and j + 3 < n:                                           # a flash of 1-3 frames returns to the old picture
            across = min(_diff(frames[j - 2], frames[j + 1]), _diff(frames[j - 2], frames[j + 3]))
            if across < MIN_PERSIST * _diff(frames[j], frames[j - 1]):
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
                        *vf, str(dest)], capture_output=True, text=True)
    return r.returncode == 0 and Path(dest).exists()
