#!/usr/bin/env python3
"""Technical QC for generated clips (needs ffprobe/ffmpeg on PATH).

    python3 qc_probe.py takes/ep01/s03/*.mp4 --expect-seconds 10 --expect-size 1344x768

Reports per file: resolution, fps, duration, audio presence, peak level,
frozen/black frames.  Exit 1 if any hard check fails.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(p: Path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(p)])
    return json.loads(r.stdout or "{}")


def peak_db(p: Path):
    r = run(["ffmpeg", "-v", "info", "-i", str(p), "-af", "volumedetect", "-f", "null", "-"])
    m = re.search(r"max_volume: ([-\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def freezes(p: Path):
    r = run(["ffmpeg", "-v", "info", "-i", str(p), "-vf", "freezedetect=n=-60dB:d=1.0,blackdetect=d=0.5", "-f", "null", "-"])
    return len(re.findall(r"freeze_start", r.stderr)), len(re.findall(r"black_start", r.stderr))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--expect-seconds", type=float)
    ap.add_argument("--expect-size", help="WxH")
    ap.add_argument("--tolerance", type=float, default=0.6, help="seconds")
    a = ap.parse_args()
    bad = 0
    for f in a.files:
        p = Path(f); info = probe(p)
        v = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), None)
        au = next((s for s in info.get("streams", []) if s["codec_type"] == "audio"), None)
        if not v:
            print(f"FAIL {p.name}: no video stream"); bad += 1; continue
        dur = float(info["format"].get("duration", 0))
        num, den = v.get("r_frame_rate", "0/1").split("/"); fps = float(num) / float(den or 1)
        size = f"{v['width']}x{v['height']}"
        peak = peak_db(p) if au else None
        fr, bl = freezes(p)
        problems = []
        if a.expect_seconds and abs(dur - a.expect_seconds) > a.tolerance: problems.append(f"duration {dur:.2f}s != {a.expect_seconds}")
        if a.expect_size and size != a.expect_size: problems.append(f"size {size} != {a.expect_size}")
        if abs(fps - 24) > 0.5: problems.append(f"fps {fps:.2f}")
        if not au: problems.append("no audio track")
        elif peak is not None and peak > -0.5: problems.append(f"audio clipping peak {peak} dB")
        if fr: problems.append(f"{fr} frozen span(s)")
        if bl: problems.append(f"{bl} black span(s)")
        tag = "FAIL" if problems else "ok  "
        bad += bool(problems)
        print(f"{tag} {p.name}: {size} {fps:.0f}fps {dur:.2f}s audio={'yes' if au else 'no'} peak={peak} {'; '.join(problems)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
