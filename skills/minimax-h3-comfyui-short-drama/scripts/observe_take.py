#!/usr/bin/env python3
"""Record where an ACCEPTED take really ends, so the next segment opens from reality instead of from the plan.

    # 1. look: writes a sheet with the first frame, three middle frames and the last moving frame(s)
    python3 observe_take.py takes/ep01/s02/s02_101/s02_101.mp4 --episode episodes/ep01.json --segment s02

    # 2. write back what the last frames show (same style as end_state, {asset_id} placeholders)
    python3 observe_take.py takes/ep01/s02/s02_101/s02_101.mp4 --episode episodes/ep01.json --segment s02 \
        --write "{lin_lan} sits at the left end of the sofa facing {dr_zhou}, the envelope open on her knees; {dr_zhou} stands by the door with one hand on the door frame." \
        --confidence high --deviation "she sat down instead of staying on her feet"

Which take, which segment: the take is the one you ACCEPTED for a segment (the draft take is fine as long as it is only refined by a latent second pass,
which keeps the composition; a re-run with other steps, LoRA or resolution is a new take - observe that one), given where comfy_submit.py saved it; --segment is the segment that take belongs
to, not the one that follows.

Why: a storyboard's end_state is a plan. The take that gets accepted often ends a little differently (someone
sat down, the prop changed hands, the light moved). If the next segment is written from the plan, the two do
not join and the error travels on. This script stores the observed state in the episode JSON
(status, accepted_take, observed_end_state, observation_confidence, accepted_deviations).
A following segment whose `continuity` is "@observed" then opens from it automatically (build_prompts.py),
and validate_episode.py warns about accepted takes that were never observed.

Only write what the frames show. Whether an action finished, where a camera move is in its arc and anything
about sound cannot be read from stills - leave them out, or use --confidence low.

Before a take is accepted it is checked against the record comfy_submit.py left beside it (run.json):
  * made for another segment, or of another length than this segment  -> refused (--force records it anyway)
  * made from an EARLIER prompt or other references than the segment has now (the previous segment was observed
    to end differently, a voice sample was attached, a picture was replaced)  -> refused: re-make the drafts from
    the current prompt, or - when you have looked at this take and it joins the previous one - accept it knowingly
    with --stale-ok (refine it with the prompt kept beside it then: --media <take folder>/media.json)
  * smaller than a draft canvas (a quick look made at reduced width / height)  -> refused: previews are not what
    the second pass is built for; --small-ok when that size is the one you work at
What the take was made from is stored with it in the episode, so validate_episode.py keeps warning when an
earlier segment is accepted again with another ending.

Needs ffmpeg / ffprobe; standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import signals  # noqa: E402
import takes as take_records  # noqa: E402
from storyboard import frames_for_seconds  # noqa: E402


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


def handover(raw: dict, i: int) -> str:
    """The state of the previous segment that segment i opens from right now ('' unless its continuity is "@observed")."""
    seg = raw["segments"][i]
    if i == 0 or not str(seg.get("continuity") or "").strip().startswith("@observed"):
        return ""
    prev = raw["segments"][i - 1]
    if str(prev.get("observed_end_state") or "").strip() and str(prev.get("status") or "").startswith("accepted"):
        return prev["observed_end_state"].strip()
    return str(prev.get("end_state") or "").strip()


def check_take(take: Path, raw: dict, i: int) -> tuple[list[str], list[str], dict]:
    """(wrong, stale, record): reasons this clip is not a take of the segment at all, reasons it was made from
    something the segment no longer has, and the run.json beside it ({} when there is none)."""
    seg = raw["segments"][i]
    rec = take_records.take_record(take) or {}
    wrong, stale = [], []
    made_for = rec.get("segment")
    if made_for and made_for != seg["id"]:
        wrong.append(f"it was made for segment {made_for} (run.json beside it), not for {seg['id']}")
    want = frames_for_seconds(seg["duration"])
    if rec.get("frames"):
        if int(rec["frames"]) != want:
            wrong.append(f"it has {rec['frames']} frames; segment {seg['id']} ({seg['duration']} s) is {want} frames long")
    else:                                            # a copy without its record (selects/...): only the length can be compared,
        info = signals.probe(take)                   # and a copy with the freeze tail cut off is up to about a second shorter
        over = (info.get("duration") or want / 24.0) - want / 24.0
        if over > 0.3 or over < -1.3:
            wrong.append(f"it runs {info['duration']:.2f} s; segment {seg['id']} is {want / 24.0:.2f} s ({want} frames) long")
    places = [Path(rec["media_json"])] if rec.get("media_json") else []
    if len(take.resolve().parents) > 2:              # takes/<episode>/<segment>/<take>/<clip>  ->  prompts/<episode>/<segment>.media.json
        places.append(Path("prompts") / take.resolve().parents[2].name / f"{seg['id']}.media.json")
    media_json = next((c for c in places if c.exists()), None)
    if rec.get("inputs_sha") and media_json is not None and not wrong:
        now = take_records.media_inputs_sha(media_json)
        if now and now != rec["inputs_sha"]:
            detail = take_records.what_changed(rec, media_json, take.parent)
            voice = any("voice sample" in d and "was added" in d for d in detail)
            stale.append(f"the prompt or the references in {media_json} have changed since it was made"
                         + (f" ({'; '.join(detail)})" if detail else "")
                         + (" - a voice sample attached after a take was made changes that segment's prompt: accept the take first "
                            "and write voice_reference afterwards, an accepted segment's prompt is left alone" if voice else ""))
    opened = (rec.get("opens_from") or {}).get("sha")
    state = handover(raw, i)
    if opened and state and take_records.text_sha(state) != opened and not wrong:
        prev = raw["segments"][i - 1]["id"]
        stale.append(f"it opens from another state than {prev} ends in now"
                     + ("" if stale else f" (the prompt files were not rebuilt after {prev} changed: run build_prompts.py)"))
    return wrong, stale, rec


DRAFT_PIXELS = 750_000      # the draft canvases (1344x768, 768x1344, 1024x1024 ...) hold about a million pixels; quick looks about half


def preview_size(take: Path) -> str:
    """'WxH' when the clip is smaller than a draft canvas - a quick look made with a reduced --set width / height.
    Such a take is not the one the second pass is built for (it enlarges 1344x768 by 1.43), and the same seed at
    the full canvas is another take. '' for a draft-size or refined clip."""
    info = signals.probe(take)
    w, h = int(info.get("width") or 0), int(info.get("height") or 0)
    return f"{w}x{h}" if 0 < w * h < DRAFT_PIXELS else ""


def refine_hint(take: Path) -> str:
    """How to refine a take that was accepted although its prompt has moved on: with what it was made from."""
    folder = take.parent
    if (folder / "media.json").is_file() and (folder / "prompt.txt").is_file():
        return (f"Refine it with the prompt and references it was made from, which are kept beside it: comfy_submit.py <refine "
                f"workflow> --media {folder / 'media.json'} --from-latent {folder} (without a kept latent: --seed <its seed> "
                f"instead of --from-latent) - the segment's prompt files of now would steer the second pass with other text")
    return ("Refine it from its kept latent (--from-latent); a --seed re-run would follow the prompt as it is now and give "
            "another take. (This take was made before prompts were kept beside takes: the second pass will be steered by the "
            "prompt of now - the preview says so.)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("take")
    ap.add_argument("--episode", required=True)
    ap.add_argument("--segment", required=True)
    ap.add_argument("--freeze-tail", type=float, default=None,
                    help="seconds of declared end freeze (the last MOVING frame is before it); default: 1.0 when the segment's "
                         "last shot has end_hold, else 0")
    ap.add_argument("--out", default="qc/observe", help="folder for the observation sheet")
    ap.add_argument("--write", help="the observed end state, one or two sentences")
    ap.add_argument("--confidence", choices=["low", "medium", "high"], help="how sure the frames make you (required with --write)")
    ap.add_argument("--deviation", action="append", default=[], help="what differs from the planned end_state and is accepted anyway (repeatable)")
    ap.add_argument("--as-planned", action="store_true",
                    help="the take ends the way the storyboard's end_state says: accept it and hand that sentence on unchanged "
                         "(the next segment's prompt, built earlier from the plan, then stays valid - and so do its takes)")
    ap.add_argument("--reject", action="store_true", help="mark the segment's take as rejected instead")
    ap.add_argument("--stale-ok", action="store_true",
                    help="accept a take that was made from an earlier prompt or other references than the segment has now: you looked "
                         "at it and it joins the previous segment's accepted take")
    ap.add_argument("--small-ok", action="store_true",
                    help="accept a take smaller than a draft canvas (a quick look at reduced size): this size is the one you work at")
    ap.add_argument("--force", action="store_true", help="record a clip that was made for another segment or has another length")
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
    if a.freeze_tail is None:
        shots = seg.get("shots") or []
        a.freeze_tail = 1.0 if shots and shots[-1].get("end_hold") else 0.0

    if a.reject:
        seg["status"] = "rejected"
        for k in ("observed_end_state", "observation_confidence", "accepted_take", "accepted_deviations"):
            seg.pop(k, None)
        ep_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{a.segment}: marked rejected in {ep_path}")
        return

    wrong, stale, rec = check_take(take, raw, i)
    if a.as_planned:
        if a.write or a.deviation:
            sys.exit("--as-planned means there is nothing to add: leave out --write and --deviation, or describe the end state with --write")
        if not (seg.get("end_state") or "").strip():
            sys.exit(f"segment {a.segment} has no planned end_state to confirm - describe what the frames show with --write")
        a.write, a.confidence = seg["end_state"], a.confidence or "high"
    if a.write:
        if not a.confidence:
            sys.exit("--write needs --confidence low|medium|high")
        text = a.write.strip()
        if len(text.split()) < 8:
            sys.exit("the observed state is too short to hand over positions, posture and props (write one or two full sentences)")
        import re as _re
        assets = {x["id"] for kind in ("characters", "scenes", "props") for x in raw.get(kind, [])}
        named = _re.findall(r"\{([A-Za-z0-9_\u4e00-\u9fff-]+)\}", text)
        unknown = [k for k in named if k not in assets]
        if unknown:
            sys.exit(f"not an asset of this episode: {', '.join('{' + k + '}' for k in unknown)} (assets: {', '.join(sorted(assets))})")
        framed = _re.search(r"\bframe[- ](?:left|right|centre|center)\b|\b(?:left|right|centre|center) (?:side |edge )?of (?:the )?frame\b"
                            r"|\bin the (?:foreground|background)\b", text, _re.I)
        if framed:
            print(f"note: \"{framed.group(0)}\" is a place in this take's picture; the next segment opens on another camera. "
                  f"Prefer where the person is in the room (next to what, to whose left or right, facing whom).")
        if wrong and not a.force:
            sys.exit(f"{take.name} is not a take of {a.segment}: " + "; ".join(wrong) + ". Nothing was written. "
                     "(--force records it anyway.)")
        if stale and not a.stale_ok:
            folder = take.parent.parent
            sys.exit(f"{take.parent.name} was made from an EARLIER version of {a.segment}: " + "; ".join(stale) + ". Nothing was written.\n"
                     f"  either  re-make the drafts from the current prompt (comfy_submit.py <workflow> --media <{a.segment}.media.json> "
                     f"--batch N; build_prompts.py lists the takes in {folder} that are out of date)\n"
                     f"  or      look at this take next to the previous segment's accepted one: if it joins, accept it as it is by "
                     f"adding --stale-ok. {refine_hint(take)}")
        small = "" if a.small_ok else preview_size(take)
        if small and not wrong:
            sys.exit(f"{take.name} is {small}: smaller than a draft canvas (1344x768 for 16:9), so it looks like a quick preview. "
                     f"Nothing was written.\n"
                     f"  A preview is not the take to accept: the second pass enlarges a 1344x768 first pass by 1.43, and the same seed "
                     f"at the full canvas gives another take. Make the drafts at the draft size and choose among those;\n"
                     f"  if this size is the one you work at on purpose, add --small-ok.")
        before = (seg.get("observed_end_state") or "").strip()
        seg["status"] = "accepted_with_deviation" if a.deviation else "accepted"
        seg["accepted_take"] = {"path": str(take), "sha256": sha256_file(take)}
        for key in ("seed", "inputs_sha", "opens_from"):
            if rec.get(key) is not None and not wrong:
                seg["accepted_take"][key] = rec[key]
        state = handover(raw, i)
        if state:
            if "opens_from" not in seg["accepted_take"] and not stale:      # a take without that record: taken as made from the state of now
                prev = raw["segments"][i - 1]
                seg["accepted_take"]["opens_from"] = {"segment": prev["id"], "sha": take_records.text_sha(state),
                                                      "source": "observed" if str(prev.get("status") or "").startswith("accepted") else "planned"}
            if stale:                                # --stale-ok: the join was looked at against the state of now
                seg["accepted_take"]["cut_checked"] = take_records.text_sha(state)
        seg["observed_end_state"] = text
        seg["observation_confidence"] = a.confidence
        if a.deviation:
            seg["accepted_deviations"] = a.deviation
        else:
            seg.pop("accepted_deviations", None)
        ep_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{a.segment}: {seg['status']}, observed end state written to {ep_path} (confidence {a.confidence})"
              + (" - accepted although it was made from an earlier prompt (--stale-ok)" if stale else ""))
        if stale:
            print("  " + refine_hint(take))
        if nxt:
            cont = (nxt.get("continuity") or "").strip()
            nxt_done = str(nxt.get("status") or "").startswith("accepted")
            if cont.startswith("@observed") and nxt_done:
                made = ((nxt.get("accepted_take") or {}).get("opens_from") or {}).get("sha")
                checked = (nxt.get("accepted_take") or {}).get("cut_checked")
                now_sha = take_records.text_sha(text)
                if (made or checked) and now_sha not in (made, checked) or (not made and not checked and before and before != text):
                    print(f"CHECK THE CUT: {nxt['id']} is already accepted, and its take was made to open from the state {a.segment} "
                          f"had before. It is kept as it is. Look at {a.segment} -> {nxt['id']}: if they still join, confirm it "
                          f"(observe_take.py <the {nxt['id']} take> --episode {ep_path} --segment {nxt['id']} --as-planned or --write ... "
                          f"--stale-ok); if not, rebuild {nxt['id']} (build_prompts.py ... --only {nxt['id']}) and make its take again. "
                          f"validate_episode.py warns about it until then.")
            elif cont.startswith("@observed"):
                first = nxt.get("first_frame")
                print(f"next: {nxt['id']} opens from this state - rebuild its prompt: build_prompts.py {ep_path} --out <prompts dir> --only {nxt['id']}"
                      f"\n  if it comes out [unchanged], the drafts already made for {nxt['id']} stay valid; if [CHANGED], re-make them"
                      + (f" and, when the opening pose or positions differ, its first frame {first} as well" if first else ""))
                bound = set(nxt.get("character_ids", [])) | set(nxt.get("prop_ids", [])) | {nxt.get("scene_id")}
                loose = sorted({k for k in named if k not in bound})
                if loose:
                    print(f"  {', '.join('{' + k + '}' for k in loose)} {'is' if len(loose) == 1 else 'are'} not bound to {nxt['id']}: "
                          f"the prompt names {'it' if len(loose) == 1 else 'them'} in words (no reference picture is attached there)")
            elif nxt.get("scene_id") == seg.get("scene_id"):
                print(f"next: {nxt['id']} plays in the same scene but has a hand-written continuity:\n    {cont}\n"
                      f"  check it against what you just observed, or set it to \"@observed\" (plus any wardrobe / light note) "
                      f"so it follows the take automatically")
            if a.deviation:
                act = str(((nxt.get("shots") or [{}])[0]).get("action") or "").strip()
                print(f"the take deviates from the plan: {nxt['id']} was written for the planned state - re-read its first shot and "
                      f"edit it if it no longer follows from what you observed"
                      + (f":\n    {nxt['id']} shot 1 action: {act[:240]}" if act else ""))
        return

    info = signals.probe(take)
    if not info["width"]:
        sys.exit(f"{take}: no video stream")
    for why in wrong:
        print(f"NOT A TAKE OF {a.segment}: {why}")
    if stale:
        print(f"OUT OF DATE: this take was made from an earlier version of {a.segment} - {'; '.join(stale)}. Accepting it needs "
              f"--stale-ok (see --help); the usual answer is to re-make the drafts from the current prompt.")
    if preview_size(take) and not wrong:
        print(f"PREVIEW SIZE: this clip is {preview_size(take)}, smaller than a draft canvas - a quick look, not the take to accept "
              f"(accepting it needs --small-ok; the usual answer is to make the drafts at the draft size).")
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
Look at the LAST frames of the sheet and write one or two sentences in the style of end_state, with {asset_id} placeholders.
The text is pasted into the next segment's prompt after "As the video opens,", so write a state, in English:
  each person  where in the ROOM (next to which piece of the set, to whose left or right), which way they face,
               posture, what the hands hold, wardrobe state
  key props    where they are now
  light        direction and colour, if it differs from the start
The next segment opens on another camera, so do not write places in the picture ("at frame left", "in the
foreground"). Any asset of the episode may be named; one the next segment does not bind is written in words there.
Leave out what stills cannot show: whether an action finished, the phase of a camera move, anything about sound.
If the frames differ from the plan and you keep the take, say how with --deviation.""")
    def cli(path) -> str:                                # a path as it has to stand on a command line
        text = Path(path).as_posix()
        return f'"{text}"' if re.search(r"\s", text) else text

    print(f"\nthen:\n  python {cli(Path(__file__).resolve())} {cli(take)} --episode {cli(ep_path)} --segment {a.segment} "
          f"--write \"<observed state>\" --confidence high|medium|low [--deviation \"<what differs>\"]")
    if nxt and not (nxt.get("continuity") or "").strip().startswith("@observed") and nxt.get("scene_id") == seg.get("scene_id"):
        print(f"\nnote: {nxt['id']} follows in the same scene with a hand-written continuity; consider \"@observed\" there.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
