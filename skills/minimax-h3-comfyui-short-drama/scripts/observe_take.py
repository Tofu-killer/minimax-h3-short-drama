#!/usr/bin/env python3
"""Record where an ACCEPTED take really ends, so the next segment opens from reality instead of from the plan.

    # 1. look: writes a sheet with the first frame, three middle frames and the last moving frame(s)
    python3 observe_take.py selects/ep01/s02.mp4 --episode episodes/ep01.json --segment s02 --freeze-tail 1.0

    # 2. write back what the last frames show (same style as end_state, {asset_id} placeholders)
    python3 observe_take.py selects/ep01/s02.mp4 --episode episodes/ep01.json --segment s02 \
        --write "{lin_lan} sits on the left end of the sofa facing frame right, the envelope open on her knees; {dr_zhou} stands by the door, one hand on the frame." \
        --confidence high --deviation "she sat down instead of staying on her feet"

Why: a storyboard's end_state is a plan. The take that gets accepted often ends a little differently (someone
sat down, the prop changed hands, the light moved). If the next segment is written from the plan, the two do
not join and the error travels on. This script stores the observed state in the episode JSON
(status, accepted_take, observed_end_state, observation_confidence, accepted_deviations).
A following segment whose `continuity` is "@observed" then opens from it automatically (build_prompts.py),
and validate_episode.py warns about accepted takes that were never observed.

Only write what the frames show. Whether an action finished, where a camera move is in its arc and anything
about sound cannot be read from stills - leave them out, or use --confidence low.

Needs ffmpeg / ffprobe; standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import signals  # noqa: E402


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("take")
    ap.add_argument("--episode", required=True)
    ap.add_argument("--segment", required=True)
    ap.add_argument("--freeze-tail", type=float, default=0.0, help="seconds of declared end freeze (the last MOVING frame is before it)")
    ap.add_argument("--out", default="qc/observe", help="folder for the observation sheet")
    ap.add_argument("--write", help="the observed end state, one or two sentences")
    ap.add_argument("--confidence", choices=["low", "medium", "high"], help="how sure the frames make you (required with --write)")
    ap.add_argument("--deviation", action="append", default=[], help="what differs from the planned end_state and is accepted anyway (repeatable)")
    ap.add_argument("--reject", action="store_true", help="mark the segment's take as rejected instead")
    a = ap.parse_args()

    take, ep_path = Path(a.take), Path(a.episode)
    if not take.exists():
        sys.exit(f"take not found: {take}")
    raw = json.loads(ep_path.read_text(encoding="utf-8"))
    ids = [s["id"] for s in raw["segments"]]
    if a.segment not in ids:
        sys.exit(f"segment {a.segment} not in {ep_path} (have: {', '.join(ids)})")
    i = ids.index(a.segment)
    seg = raw["segments"][i]
    nxt = raw["segments"][i + 1] if i + 1 < len(raw["segments"]) else None

    if a.reject:
        seg["status"] = "rejected"
        for k in ("observed_end_state", "observation_confidence", "accepted_take", "accepted_deviations"):
            seg.pop(k, None)
        ep_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{a.segment}: marked rejected in {ep_path}")
        return

    if a.write:
        if not a.confidence:
            sys.exit("--write needs --confidence low|medium|high")
        text = a.write.strip()
        if len(text.split()) < 8:
            sys.exit("the observed state is too short to hand over positions, posture and props (write one or two full sentences)")
        seg["status"] = "accepted_with_deviation" if a.deviation else "accepted"
        seg["accepted_take"] = {"path": str(take), "sha256": sha256_file(take)}
        seg["observed_end_state"] = text
        seg["observation_confidence"] = a.confidence
        if a.deviation:
            seg["accepted_deviations"] = a.deviation
        else:
            seg.pop("accepted_deviations", None)
        ep_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{a.segment}: {seg['status']}, observed end state written to {ep_path} (confidence {a.confidence})")
        if nxt:
            cont = (nxt.get("continuity") or "").strip()
            if cont.startswith("@observed"):
                print(f"next: {nxt['id']} opens from this state - rebuild its prompt: build_prompts.py {ep_path} --out <prompts dir> --only {nxt['id']}")
            elif nxt.get("scene_id") == seg.get("scene_id"):
                print(f"next: {nxt['id']} plays in the same scene but has a hand-written continuity:\n    {cont}\n"
                      f"  check it against what you just observed, or set it to \"@observed\" (plus any wardrobe / light note) "
                      f"so it follows the take automatically")
            if a.deviation:
                print("the take deviates from the plan: check that later segments do not still assume the planned state")
        return

    info = signals.probe(take)
    if not info["width"]:
        sys.exit(f"{take}: no video stream")
    dur = info["duration"]
    end = max(0.2, dur - a.freeze_tail)
    f = 1.0 / (info["fps"] or 24.0)
    samples = [(min(2 * f, end / 2), "first"), (end * 0.25, "middle"), (end * 0.5, "middle"), (end * 0.75, "middle"),
               (max(0.0, end - 0.5), "half a second before the end"), (max(0.0, end - 2 * f), "last moving frame")]
    if a.freeze_tail:
        samples.append((max(0.0, dur - 2 * f), "end of the hold"))
    sheet = Path(a.out) / f"{a.segment}_observe.png"
    try:
        signals.stamped_sheet(take, samples, sheet, width=640, cols=3)
    except RuntimeError as e:
        sys.exit(str(e))
    print(f"sheet: {sheet.resolve()}")
    print("  " + " | ".join(f"{k + 1}: {t:.2f}s {tag}" for k, (t, tag) in enumerate(samples)))
    print(f"\nplanned end_state of {a.segment}:\n  {seg.get('end_state', '(none)')}")
    print("""
Look at the LAST frames of the sheet and write one or two sentences in the style of end_state, with {asset_id} placeholders:
  each person  where in frame (left / centre / right, near / far), which way they face, posture, what the hands hold, wardrobe state
  key props    where they are now
  light        direction and colour, if it differs from the start
Leave out what stills cannot show: whether an action finished, the phase of a camera move, anything about sound.
If the frames differ from the plan and you keep the take, say how with --deviation.""")
    print(f"\nthen:\n  python3 observe_take.py {take} --episode {ep_path} --segment {a.segment} --write \"<observed state>\" "
          f"--confidence high|medium|low [--deviation \"<what differs>\"]")
    if nxt and not (nxt.get("continuity") or "").strip().startswith("@observed") and nxt.get("scene_id") == seg.get("scene_id"):
        print(f"\nnote: {nxt['id']} follows in the same scene with a hand-written continuity; consider \"@observed\" there.")


if __name__ == "__main__":
    main()
