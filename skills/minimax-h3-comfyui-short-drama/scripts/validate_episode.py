#!/usr/bin/env python3
"""Validate a storyboard episode JSON before spending GPU time.

    python3 validate_episode.py episodes/ep01.json [--catalog props.json]

Checks: segment duration 4-15 s, dialogue budget (chars/4.5 + 2 s), one speaker
per shot, unknown asset ids, props without reference images, empty
end_state/continuity, action sentences shorter than 8 words, consecutive static
dialogue segments, hand-off state ("@observed" continuity, accepted takes that were never observed),
and (with --catalog) items mentioned in text but not bound. --rhythm adds a pacing audit done by
arithmetic. Warnings are printed with "~" and do not fail the run; exit code 1 only on errors.
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
    # reference media must exist on disk — a missing prop/character image is exactly how hallucinated props happen
    from pathlib import Path as _P
    for c in ep.characters:
        for f in c.reference_images:
            if not _P(f).exists(): problems.append(f"character {c.id}: reference image missing: {f}")
        if c.voice_reference and not _P(c.voice_reference).exists(): problems.append(f"character {c.id}: voice reference missing: {c.voice_reference}")
    for sc in ep.scenes:
        for f in sc.reference_images:
            if not _P(f).exists(): problems.append(f"scene {sc.id}: reference image missing: {f}")
    for pr in ep.props:
        for f in pr.reference_images:
            if not _P(f).exists(): problems.append(f"prop {pr.id}: reference image missing: {f}")
    if a.catalog:
        from catalog import check as check_catalog  # type: ignore
        problems += check_catalog(Path(a.episode), Path(a.catalog))
    # reference-slot budget: 9 images per segment (chars up to 3 each + scene + props); the builder would silently drop extras
    for seg in ep.segments:
        n = sum(min(3, len(ep.char(c).reference_images)) for c in seg.character_ids)
        n += 1 if ep.scene(seg.scene_id).reference_images else 0
        n += sum(1 for p in seg.prop_ids if ep.prop(p).reference_images)
        n += 1 if (seg.mode == "ref2va" and seg.first_frame) else 0
        if n > 9: problems.append(f"segment {seg.id}: {n} reference images exceed the 9-slot limit (drop a character detail image or a prop)")
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
    if errors:
        print(f"{len(errors)} problem(s):")
        for p in errors:
            print(" -", p)
        print("NOT OK: " + totals)
        sys.exit(1)
    print("OK: " + totals)


if __name__ == "__main__":
    main()
