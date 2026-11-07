#!/usr/bin/env python3
"""Turn a validated episode JSON into one prompt + ordered media list per segment.

    python3 build_prompts.py episodes/ep01.json --out prompts/ep01

Writes <out>/<segment_id>.txt (the final H3 prompt with <Subject N>/<Picture N>
labels filled in) and <out>/<segment_id>.media.json (ordered list of
{"type","path","role"} — this order IS the <Picture N> numbering, wire the
images into ComfyUI in exactly this order).  Also writes <out>/cues.srt with
dialogue timings for burn-in later.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
from storyboard import load_episode, validate_episode  # noqa: E402
from prompt_builder import build, dialogue_cues  # noqa: E402


def srt_time(t: float) -> str:
    h, m = divmod(int(t), 3600); m, s = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{int((t - int(t)) * 1000):03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true", help="build even if validation fails")
    a = ap.parse_args()
    ep = load_episode(a.episode)
    problems = validate_episode(ep)
    if problems and not a.force:
        print("validation failed, fix first (or --force):"); [print(" -", p) for p in problems]
        sys.exit(1)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    srt, idx, offset = [], 1, 0.0
    for seg in ep.segments:
        bp = build(ep, seg)
        text = next(c["text"] for c in bp.content if c["type"] == "text")
        media = [c for c in bp.content if c["type"] != "text"]
        (out / f"{seg.id}.txt").write_text(text, encoding="utf-8")
        (out / f"{seg.id}.media.json").write_text(json.dumps(
            {"segment": seg.id, "mode": seg.mode, "duration": seg.duration, "labels": bp.labels, "media": media},
            ensure_ascii=False, indent=1), encoding="utf-8")
        for start, end, who, line in dialogue_cues(ep, seg, offset):
            srt.append(f"{idx}\n{srt_time(start)} --> {srt_time(end)}\n{line}\n"); idx += 1
        offset += seg.duration
        print(f"{seg.id}: {seg.mode} {seg.duration}s, {len(text)} chars, {len(media)} media")
    (out / "cues.srt").write_text("\n".join(srt), encoding="utf-8")


if __name__ == "__main__":
    main()
