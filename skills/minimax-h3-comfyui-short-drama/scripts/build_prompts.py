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

Every build says, per segment, whether the prompt is [unchanged] or [CHANGED] against the files that were there,
and - each time, not only on the build that changed it - how many finished takes in takes/<name of --out>/<segment>
were made from another prompt or other references than the segment has now. Those takes do not show what the
prompt now asks for: re-make them, or look at the one you want and accept it knowingly (observe_take.py --stale-ok).
"""
import argparse, json, sys
from pathlib import Path
sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
from storyboard import NotObservedYet, load_episode, validate_episode, effective_continuity, frames_for_seconds, voice_plan, handover_state  # noqa: E402
import prompt_builder  # noqa: E402
import takes as take_records  # noqa: E402
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
    kept = []
    kept_stale = []
    takes_root = Path("takes") / out.resolve().name          # where comfy_submit.py --media puts a segment's takes by default
    for seg in ep.segments:
        if only and seg.id not in only:
            continue
        if seg.status.startswith("accepted") and not only and (out / f"{seg.id}.txt").exists():
            kept.append(seg.id)        # its take was rendered from these files: a same-seed refine run needs them unchanged
            made_from = (seg.accepted_take or {}).get("inputs_sha")
            if made_from and made_from != take_records.media_inputs_sha(out / f"{seg.id}.media.json"):
                kept_stale.append(seg.id)
            continue
        try:
            _text, source = effective_continuity(ep, seg, a.allow_planned)
            bp = build(ep, seg)
        except NotObservedYet as e:
            waiting.append(str(e) + (f" (the {seg.id} files in {out} are from an earlier build and were left as they are)"
                                     if (out / f"{seg.id}.txt").exists() else ""))
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
        target = out / f"{seg.id}.txt"
        before = target.read_text(encoding="utf-8") if target.exists() else None
        try:                                # the state the earlier build opened from: only a change of THAT makes the first frame stale
            opened_before = (json.loads((out / f"{seg.id}.media.json").read_text(encoding="utf-8")).get("opens_from") or {}).get("sha")
        except (OSError, json.JSONDecodeError):
            opened_before = None
        target.write_text(text, encoding="utf-8")
        spec = {"segment": seg.id, "mode": bp.mode or seg.mode, "ratio": ep.ratio, "duration": seg.duration, "frames": frames,
                "effective_seconds": round(frames / 24, 3),
                "prompt_file": f"{seg.id}.txt", "labels": bp.labels, "media": media,
                # per shot: the words that come from that shot's own fields (framing, action, performance, camera, lines) -
                # lint_prompt.py judges a shot's length on these, not on the set-up and end state the builder adds
                "shot_words": {str(k): v for k, v in bp.own_words.items()}}
        if source != "authored":            # which state of the previous segment this prompt opens from (observe_take.py compares it later)
            kind, prev_id = source.split(":", 1)
            spec["opens_from"] = {"segment": prev_id, "source": kind, "sha": take_records.text_sha(handover_state(ep, seg, a.allow_planned))}
        (out / f"{seg.id}.media.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        note = {"authored": ""}.get(source, f"  [opens from {source.replace(':', ' end of ')}]")
        if len(text) > 7000:
            note += f"  [{len(text)} characters: over the hosted API's 7000 limit - fine for the local node, but trim if it can be]"
        built_as = bp.mode or seg.mode
        if built_as != seg.mode:
            note += f"  [built as {built_as}: nothing bound to this segment has a reference picture or voice sample]"
        if before is not None:              # takes made from the earlier text stay valid only when nothing changed
            note += "  [unchanged]" if before == text else "  [CHANGED since the last build - takes made from the earlier prompt no longer match it]"
            opened_now = (spec.get("opens_from") or {}).get("sha")
            if before != text and seg.first_frame and source != "authored" and opened_now != opened_before:
                note += (f"  [its first frame {seg.first_frame} was made for the earlier opening: re-make it too if the pose or the "
                         f"positions differ, and re-read this segment's first shot - its action was written for the planned state]")
        # said on every build, not only on the one that changed the prompt: takes that belong to an earlier version of it
        old_takes = take_records.stale_takes(takes_root / seg.id, take_records.media_inputs_sha(out / f"{seg.id}.media.json"))
        if old_takes:
            shown = ", ".join(old_takes[:4]) + (f" and {len(old_takes) - 4} more" if len(old_takes) > 4 else "")
            note += (f"  [{len(old_takes)} finished take(s) in {takes_root / seg.id} were made from an EARLIER prompt or other references "
                     f"({shown}): they do not show what this prompt asks for - re-make them from this build]")
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
    if kept:
        print(f"kept as they are: {', '.join(kept)} - accepted, and a refine run must start from the prompt the accepted take was "
              f"made from. To rebuild one on purpose (its take then has to be made again): --only <segment>")
    if kept_stale:
        print(f"note: the accepted take of {', '.join(kept_stale)} was made from an earlier version of its prompt files (it was accepted "
              f"with --stale-ok). Refine it with what it was made from - comfy_submit.py keeps that beside every take: "
              f"--media <take folder>/media.json (plus --from-latent <take folder>, or --seed <its seed>). The files in {out} "
              f"as they are now would steer the second pass with other text.")
    pending = [v for v in voice_plan(ep) if v["later"]]
    if pending and not only:
        who = "; ".join(f"{v['character']} first speaks in {v['first']}" for v in pending)
        later = sorted({s for v in pending for s in v["later"]})
        print(f"ORDER - voice samples still to come ({who}): draft and accept the segment(s) a sample is cut from first, cut the sample "
              f"(references/audio-and-post.md §2), set voice_reference and build again - only then batch {', '.join(later)}. "
              f"Their prompts change when a sample is attached, and drafts made before that carry no voice anchor.")
    status = {seg.id: seg.status for seg in ep.segments}
    once = [v for v in voice_plan(ep) if not v["later"] and not status[v["first"]].startswith("accepted")] if not only else []
    if once:
        who = "; ".join(f"{v['character']} speaks only in {v['first']}" for v in once)
        print(f"note - voice ({who}): no later segment needs a sample of that voice. If you cut one anyway (for the next episode), "
              f"accept that take first and write voice_reference afterwards: attached before, it changes that segment's prompt and "
              f"puts the drafts already made for it out of date.")
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
