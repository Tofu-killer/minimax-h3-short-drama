#!/usr/bin/env python3
"""Turn a validated episode JSON into one prompt + ordered media list per segment.

    python3 build_prompts.py episodes/ep01.json --out prompts/ep01

Writes <out>/<segment_id>.txt (the final H3 prompt with <Subject N>/<Picture N>
labels filled in) and <out>/<segment_id>.media.json (ordered list of
{"type","path","role"} — this order IS the <Picture N> numbering, wire the
images into ComfyUI in exactly this order).  Also writes <out>/cues.srt with
the planned dialogue timings (the real subtitles come from retime_subtitles.py after assembly).

A segment whose `continuity` starts with "@observed" opens from where the previous segment's ACCEPTED take
really ended (observe_take.py writes that back into the episode). Until that exists the segment is not
built - use --allow-planned for drafts, and --only s03,s04 to (re)build single segments.
"""
import argparse, json, sys
from pathlib import Path
sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
from storyboard import load_episode, validate_episode, effective_continuity  # noqa: E402
import prompt_builder  # noqa: E402
from prompt_builder import build, dialogue_cues  # noqa: E402


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()


def srt_time(t: float) -> str:
    h, m = divmod(int(t), 3600); m, s = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{int((t - int(t)) * 1000):03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true", help="build even if validation fails")
    ap.add_argument("--allow-planned", action="store_true",
                    help='drafts only: a continuity of "@observed" may use the previous segment\'s PLANNED end_state '
                         "when its accepted take has not been observed yet")
    ap.add_argument("--only", help="comma-separated segment ids to build (others are left untouched)")
    a = ap.parse_args()
    ep = load_episode(a.episode)
    problems = [p for p in validate_episode(ep) if ": WARN " not in p]
    if problems and not a.force:
        print("validation failed, fix first (or --force):"); [print(" -", p) for p in problems]
        sys.exit(1)
    prompt_builder.ALLOW_PLANNED = a.allow_planned
    only = set(a.only.split(",")) if a.only else None
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    srt, idx, offset = [], 1, 0.0
    blocked = []
    for seg in ep.segments:
        if only and seg.id not in only:
            offset += seg.duration
            continue
        try:
            _text, source = effective_continuity(ep, seg, a.allow_planned)
        except ValueError as e:
            blocked.append(str(e))
            offset += seg.duration
            continue
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
        note = {"authored": ""}.get(source, f"  [opens from {source.replace(':', ' end of ')}]")
        print(f"{seg.id}: {seg.mode} {seg.duration}s, {len(text)} chars, {len(media)} media{note}")
    if not only:
        (out / "cues.srt").write_text("\n".join(srt), encoding="utf-8")
    if blocked:
        print("NOT BUILT:")
        for b in blocked:
            print(" -", b)
        sys.exit(1)


if __name__ == "__main__":
    main()
