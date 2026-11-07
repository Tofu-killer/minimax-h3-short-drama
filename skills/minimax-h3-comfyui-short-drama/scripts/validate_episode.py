#!/usr/bin/env python3
"""Validate a storyboard episode JSON before spending GPU time.

    python3 validate_episode.py episodes/ep01.json [--catalog props.json]

Checks: segment duration 4-15 s, dialogue budget (chars/4.5 + 2 s), one speaker
per shot, unknown asset ids, props without reference images, empty
end_state/continuity, action sentences shorter than 8 words, consecutive static
dialogue segments, and (with --catalog) items mentioned in text but not bound.
Exit code 1 when any error is found.
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
from storyboard import load_episode, validate_episode  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--catalog", help="prop catalog JSON from catalog.py build")
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
        from catalog import check_episode  # type: ignore
        problems += check_episode(a.episode, a.catalog)
    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print(f"OK: {ep.title} — {len(ep.segments)} segments, "
          f"{sum(s.duration for s in ep.segments)} s total")


if __name__ == "__main__":
    main()
