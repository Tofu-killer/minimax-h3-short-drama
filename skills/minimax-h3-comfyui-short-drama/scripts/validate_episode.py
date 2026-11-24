#!/usr/bin/env python3
"""Validate a storyboard episode JSON before spending GPU time.

    python3 validate_episode.py episodes/ep01.json [--catalog props.json]

Checks: segment duration 4-15 s, dialogue budget (chars/4.5 + 2 s), one speaker
per shot, unknown asset ids, props without reference images, empty
end_state/continuity, action sentences shorter than 8 words, consecutive static
dialogue segments, hand-off state ("@observed" continuity, accepted takes that were never observed),
and (with --catalog) items mentioned in text but not bound. --rhythm adds a pacing audit done by
arithmetic. Warnings are printed with "~" and do not fail the run; exit code 1 only on errors.

Pictures and sounds the storyboard names but that are not on disk yet are listed with "+" - they are work still to
do (plan_stills.py lists the commands), not errors of the storyboard, and do not change the exit code. Prompts for
a segment are built only once its files exist.
"""
import argparse, sys
from pathlib import Path
sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
from storyboard import load_episode, validate_episode, rhythm_warnings, frames_for_seconds  # noqa: E402


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
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--catalog", help="prop catalog JSON from catalog.py build")
    ap.add_argument("--rhythm", action="store_true",
                    help="also audit pacing by arithmetic (overloaded segments, even shot lengths, three shots of one size "
                         "in a row, lines too long for their shot, a slow opening) - advice, never an error")
    a = ap.parse_args()
    ep = load_episode(a.episode)
    problems = validate_episode(ep)
    # Pictures and sounds the storyboard names but that are not on disk yet. Not a fault of the storyboard: at this
    # stage the first frames (often every picture) are still to be made - but prompts cannot be built without them,
    # and a prop or a face without its picture is exactly how hallucinated props and drifting faces happen.
    from pathlib import Path as _P
    base = _P(a.episode).resolve().parent
    todo: list[tuple[str, str]] = []

    def need(owner: str, f) -> None:
        if f and not str(f).startswith(("http://", "https://", "mm_file://", "data:")) and not _P(f).exists():
            try:
                shown = _P(f).resolve().relative_to(base).as_posix()      # as it is written in the storyboard
            except ValueError:
                shown = str(f)
            todo.append((shown, owner))

    for c in ep.characters:
        for f in c.reference_images:
            need(f"character {c.id}: reference image", f)
        need(f"character {c.id}: voice sample", c.voice_reference)
    for sc in ep.scenes:
        for f in sc.reference_images:
            need(f"scene {sc.id}: reference image", f)
    for pr in ep.props:
        for f in pr.reference_images:
            need(f"prop {pr.id}: reference image", f)
    for seg in ep.segments:                                # frame pictures named by a segment or a shot
        need(f"segment {seg.id}: first_frame", seg.first_frame)
        need(f"segment {seg.id}: last_frame", seg.last_frame)
        for sh in seg.shots:
            need(f"segment {seg.id} shot {sh.index}: keyframe", sh.keyframe)
    if a.catalog:
        from catalog import check as check_catalog  # type: ignore
        problems += check_catalog(Path(a.episode), Path(a.catalog))
    # reference-slot budget: 9 images per segment (chars up to 3 each + scene + props); the builder would silently drop extras
    for seg in ep.segments:
        n = sum(min(3, len(ep.char(c).reference_images)) for c in seg.character_ids)
        n += 1 if ep.scene(seg.scene_id).reference_images else 0
        n += sum(1 for p in seg.prop_ids if ep.prop(p).reference_images)
        n += 1 if (seg.mode == "ref2va" and seg.first_frame) else 0
        n += sum(1 for sh in seg.shots if sh.keyframe and sh.index > 1) if seg.mode == "ref2va" else 0
        if n > 9: problems.append(f"segment {seg.id}: {n} reference images exceed the 9-slot limit (drop a character detail image or a prop)")
    # an accepted take is a file on disk: gone, or with other content than when it was accepted, the storyboard points at nothing
    import hashlib
    for seg in ep.segments:
        acc = seg.accepted_take or {}
        if not seg.status.startswith("accepted") or not acc.get("path"):
            continue
        rel = _P(str(acc["path"]))
        found = next((c for c in ([rel] if rel.is_absolute() else [_P.cwd() / rel, base.parent / rel]) if c.is_file()), None)
        if found is None:
            problems.append(f"segment {seg.id}: WARN its accepted take {acc['path']} is not on disk (moved, or its folder was run again and "
                            f"the old files went into _prev_...?) - accept the take that is there now with observe_take.py, or put the file back")
            continue
        if acc.get("sha256"):
            h = hashlib.sha256()
            with open(found, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != acc["sha256"]:
                problems.append(f"segment {seg.id}: WARN {acc['path']} has other content than the take that was accepted (the file was "
                                f"replaced) - look at it and accept it again with observe_take.py, so that what follows is built on what is there")
    try:                                   # a first frame made for the planned ending of a segment accepted with another one
        import json as _json
        import takes as _takes
        for sid, c in _takes.stale_first_frames(_json.loads(_P(a.episode).read_text(encoding="utf-8")), _P(a.episode)).items():
            problems.append(f"segment {sid}: WARN {c['why']} - look at it before drafting {sid}: make it again, or confirm that it "
                            f"fits with plan_stills.py {a.episode} --fits {c['picture']}")
        for sid, why in _takes.unread_first_shots(_json.loads(_P(a.episode).read_text(encoding="utf-8"))).items():
            problems.append(f"segment {sid}: WARN {why}")
    except (OSError, ValueError):
        pass
    warnings = [p.replace(": WARN ", ": ", 1) for p in problems if ": WARN " in p]
    errors = [p for p in problems if ": WARN " not in p]
    rhythm = rhythm_warnings(ep) if a.rhythm else []
    warnings += ["rhythm - " + w for w in rhythm]
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(" ~", w)
    if a.rhythm and not rhythm:
        print("rhythm check: no findings")
    gen = sum(frames_for_seconds(s.duration) for s in ep.segments) / 24.0
    holds = sum(1 for s in ep.segments if s.shots and s.shots[-1].end_hold)
    cut = gen - holds * 1.0 - len(ep.segments) * 2 / 24.0
    totals = (f"{ep.title} — {len(ep.segments)} segments, {sum(s.duration for s in ep.segments)} s requested = {gen:.1f} s generated "
              f"(17k+5 frame grid); about {cut:.1f} s in the cut after trimming {holds} declared end hold(s) and the lead frames")
    if todo:
        print(f"{len(todo)} file(s) named in the storyboard are not on disk yet (looked for beside the storyboard and in the folder "
              f"this runs from):")
        for shown, owner in todo:
            print(f" + {shown}   ({owner})")
        print("   Make them before the prompts are built - plan_stills.py <this storyboard> writes each picture's prompt and "
              "command; build_prompts.py leaves out a segment whose files are missing.")
    if errors:
        print(f"{len(errors)} problem(s):")
        for p in errors:
            print(" -", p)
        print("NOT OK: " + totals)
        sys.exit(1)
    print(("OK (the storyboard itself; the files listed above are still to make): " if todo else "OK: ") + totals)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
