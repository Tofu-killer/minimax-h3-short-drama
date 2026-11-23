#!/usr/bin/env python3
"""Turn a validated episode JSON into one prompt + ordered media list per segment.

    python3 build_prompts.py episodes/ep01.json --out prompts/ep01

Writes <out>/<segment_id>.txt (the final H3 prompt with <Subject N>/<Picture N>
labels filled in) and <out>/<segment_id>.media.json: the frame count on the model's
17k+5 grid and the ordered list of {"type","path","role"} - this order IS the
<Picture N> / <Audio N> numbering. comfy_submit.py --media <that file> puts the prompt,
the frame count and the references into the workflow in exactly this order.  Also writes <out>/planned_cues.srt:
the PLANNED dialogue timings, for previews only (the real subtitles come from retime_subtitles.py after assembly).

A storyboard with validation errors is not built; --force builds it anyway (warnings never block).
A ref2va segment in which nothing has a reference picture or a voice sample is built as plain text-to-video.

A segment whose `continuity` starts with "@observed" opens from where the previous segment's ACCEPTED take
really ended (observe_take.py writes that back into the episode). Until that exists the segment is not
built - use --allow-planned for drafts, and --only s03,s04 to (re)build single segments.
"""
import argparse, json, sys
from pathlib import Path
sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
from storyboard import NotObservedYet, load_episode, validate_episode, effective_continuity, frames_for_seconds  # noqa: E402
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
    ms = int(round((t - int(t)) * 1000))
    if ms >= 1000:
        return srt_time(int(t) + 1.0)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


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
    blocked, waiting = [], []
    for seg in ep.segments:
        if only and seg.id not in only:
            continue
        try:
            _text, source = effective_continuity(ep, seg, a.allow_planned)
            bp = build(ep, seg)
        except NotObservedYet as e:
            waiting.append(str(e))
            continue
        except ValueError as e:
            blocked.append(str(e))
            continue
        except FileNotFoundError as e:                 # a reference file named in the storyboard is not on disk
            blocked.append(f"{seg.id}: {e} - fix the path in the storyboard, or put the file there "
                           "(validate_episode.py lists every missing file at once)")
            continue
        text = next(c["text"] for c in bp.content if c["type"] == "text")
        media = [c for c in bp.content if c["type"] != "text"]
        frames = frames_for_seconds(seg.duration)
        (out / f"{seg.id}.txt").write_text(text, encoding="utf-8")
        (out / f"{seg.id}.media.json").write_text(json.dumps(
            {"segment": seg.id, "mode": bp.mode or seg.mode, "ratio": ep.ratio, "duration": seg.duration, "frames": frames,
             "effective_seconds": round(frames / 24, 3),
             "prompt_file": f"{seg.id}.txt", "labels": bp.labels, "media": media},
            ensure_ascii=False, indent=1), encoding="utf-8")
        note = {"authored": ""}.get(source, f"  [opens from {source.replace(':', ' end of ')}]")
        if len(text) > 7000:
            note += f"  [{len(text)} characters: over the hosted API's 7000 limit - fine for the local node, but trim if it can be]"
        built_as = bp.mode or seg.mode
        if built_as != seg.mode:
            note += f"  [built as {built_as}: nothing bound to this segment has a reference picture or voice sample]"
        print(f"{seg.id}: {built_as} {seg.duration}s = {frames} frames, {len(text.split())} words, {len(media)} media{note}")
    # planned subtitle cues for the whole episode (they depend on the storyboard only, not on which prompts were built)
    srt, idx, offset = [], 1, 0.0
    for seg in ep.segments:
        for start, end, who, line in dialogue_cues(ep, seg, offset):
            srt.append(f"{idx}\n{srt_time(start)} --> {srt_time(end)}\n{line}\n")
            idx += 1
        offset += frames_for_seconds(seg.duration) / 24.0
    (out / "planned_cues.srt").write_text("\n".join(srt), encoding="utf-8")       # a preview of the PLAN, not the subtitles
    stale = out / "cues.srt"                                                       # name used by earlier versions
    if stale.exists():
        stale.unlink()
    if waiting:
        print("WAITING for a take to be accepted (expected at this stage, the other segments were written):")
        for w in waiting:
            print(" -", w)
    if blocked:
        print("NOT BUILT (the other segments were written):")
        for b in blocked:
            print(" -", b)
        sys.exit(1)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
