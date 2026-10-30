#!/usr/bin/env python3
"""Technical QC + stitching.

  python stitch.py examples/episode01.json --clips out/<ep>/clips --picks picks.json --out final.mp4
  python stitch.py examples/episode01.json --qc-only --clips out/<ep>/clips

Steps (FFmpeg is the v1 backend, same as huobao-drama and MiniMax-H3-Codex-Drama):
  1. ffprobe every chosen clip: resolution, fps, duration vs requested, audio track present
  2. normalise all clips to one codec/size/fps/audio layout (avoids concat A/V drift)
  3. concat demuxer
  4. burn SRT subtitles generated from the storyboard dialogue (H3 cannot render exact text reliably)
  5. optional background music with ducking
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from prompt_builder import dialogue_cues
from storyboard import load_episode


def ffprobe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def qc_clip(path: Path, expected_duration: int, ratio: str) -> list[str]:
    issues = []
    info = ffprobe(path)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if not v:
        return ["no video stream"]
    if not a:
        issues.append("no audio stream (H3 should return stereo audio)")
    elif a.get("channels", 0) < 2:
        issues.append(f"audio has {a.get('channels')} channel(s), expected stereo")
    dur = float(info["format"]["duration"])
    if abs(dur - expected_duration) > 0.6:
        issues.append(f"duration {dur:.2f}s vs requested {expected_duration}s")
    w, h = int(v["width"]), int(v["height"])
    want_w, want_h = map(int, ratio.split(":"))
    if abs(w / h - want_w / want_h) > 0.05:
        issues.append(f"aspect {w}x{h} does not match {ratio}")
    if min(w, h) < 720:
        issues.append(f"short edge {min(w, h)}px < 720 (draft quality?)")
    # loudness / clipping check
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "max_volume" in line and line.strip().endswith("0.0 dB"):
            issues.append("audio peaks at 0 dBFS (possible clipping)")
    return issues


def srt_time(t: float) -> str:
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def write_srt(ep, order: list[str], dest: Path) -> Path:
    offset = 0.0
    n = 0
    lines = []
    for seg in ep.segments:
        if seg.id not in order:
            continue
        for start, end, name, text in dialogue_cues(ep, seg, offset):
            n += 1
            lines += [str(n), f"{srt_time(start)} --> {srt_time(end)}", text if name == "旁白" else f"{name}：{text}", ""]
        offset += seg.duration
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest


def target_size(ratio: str, short_edge: int = 1080) -> tuple[int, int]:
    w, h = map(int, ratio.split(":"))
    if w >= h:
        return (round(short_edge * w / h / 2) * 2, short_edge)
    return (short_edge, round(short_edge * h / w / 2) * 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--clips", required=True, help="directory with <segment>_<res>_tN.mp4")
    ap.add_argument("--picks", help="JSON {segment_id: filename}; default = first succeeded take per segment")
    ap.add_argument("--out", default="final.mp4")
    ap.add_argument("--short-edge", type=int, default=1080, help="1080 → 1080x1920 for 9:16; use 1440 for 2K")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--music", help="background music file (ducked under dialogue)")
    ap.add_argument("--no-subs", action="store_true")
    ap.add_argument("--qc-only", action="store_true")
    args = ap.parse_args()

    ep = load_episode(args.episode)
    clips_dir = Path(args.clips)
    picks = json.loads(Path(args.picks).read_text()) if args.picks else {}
    chosen: list[tuple[str, Path]] = []
    for seg in ep.segments:
        if seg.id in picks:
            f = clips_dir / picks[seg.id]
        else:
            cands = sorted(clips_dir.glob(f"{seg.id}_*.mp4"))
            if not cands:
                print(f"  ! missing clip for {seg.id}", file=sys.stderr)
                continue
            f = cands[0]
        chosen.append((seg.id, f))

    # 1. QC
    hard_fail = False
    for sid, f in chosen:
        seg = next(s for s in ep.segments if s.id == sid)
        issues = qc_clip(f, seg.duration, ep.ratio)
        status = "OK " if not issues else "WARN"
        print(f"  [{status}] {f.name}" + ("" if not issues else " — " + "; ".join(issues)))
        if any(i.startswith("no video") for i in issues):
            hard_fail = True
    if args.qc_only or hard_fail:
        sys.exit(1 if hard_fail else 0)

    # 2. normalise + 3. concat
    w, h = target_size(ep.ratio, args.short_edge)
    tmp = Path(tempfile.mkdtemp(prefix="h3stitch_"))
    norm = []
    for sid, f in chosen:
        o = tmp / f"{sid}.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(f),
                        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={args.fps}",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(o)], check=True)
        norm.append(o)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in norm))
    concat = tmp / "concat.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(concat)],
                   check=True)

    # 4. subtitles + 5. music
    srt = write_srt(ep, [sid for sid, _ in chosen], tmp / "subs.srt")
    out = Path(args.out)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(concat)]
    filters = []
    if args.music:
        cmd += ["-stream_loop", "-1", "-i", args.music]
        filters.append("[1:a]volume=0.35[m];[0:a][m]sidechaincompress=threshold=0.05:ratio=6:attack=50:release=400[mix]")
    vf = [] if args.no_subs else [f"subtitles={srt}:force_style='FontSize=16,Outline=2,MarginV=160,Alignment=2'"]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    if filters:
        cmd += ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[mix]", "-shortest"]
    cmd += ["-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    shutil.copy(srt, out.with_suffix(".srt"))
    print(f"✓ {out}  ({w}x{h}, {len(chosen)} segments, {sum(s.duration for s in ep.segments if s.id in dict(chosen))} s)")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
