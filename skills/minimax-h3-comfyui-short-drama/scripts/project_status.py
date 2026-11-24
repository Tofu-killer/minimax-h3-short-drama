#!/usr/bin/env python3
"""Where an episode stands: for every segment what exists and what comes next. Reads only; nothing is changed.

    python project_status.py episodes/ep01.json
    python project_status.py episodes/ep01.json --json logs/status.json

Made for the moment work is picked up again - after a break, a restart, a new conversation: one screen instead of
re-reading folders. For each segment it says
  * whether the pictures and sound files the storyboard names are on disk
  * whether its prompt is built, and whether the storyboard has changed since
  * which takes exist: drafts (how many belong to the prompt of now), second passes
  * which take is accepted, and whether a second pass of exactly that take exists
  * which clip the edit list uses for it, and what that clip is
  * the next step, as a command
and after the segments: the edit list, the subtitle timing, the mix - each with whether it still belongs to the cut.

Folders are found by the names the other scripts use: prompts/<episode>, takes/<episode>, selects/<episode>,
edit/<episode>.edl.json, final/<episode>.mp4 (<episode> = the storyboard's file name without .json). Give another
place with --prompts / --takes / --selects / --edl / --final. Run it from the project root.

It reports what the files say. Whether a picture is good or a take is the right one is not something it can see.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "h3lib"))
import edl as edl_lib  # noqa: E402
import prompt_builder  # noqa: E402
import signals  # noqa: E402
import takes as take_records  # noqa: E402
from storyboard import NotObservedYet, load_episode, voice_plan, missing_media  # noqa: E402

FLOWS = HERE.parent / "assets" / "workflows"


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def cli(path) -> str:
    text = Path(path).as_posix() if not isinstance(path, str) else path
    return f'"{text}"' if re.search(r"\s", text) else text


def py(script: str) -> str:
    return f"python {cli(HERE / script)}"


def is_url(f: str) -> bool:
    return str(f).startswith(("http://", "https://", "mm_file://", "data:"))


def missing_files(ep, seg, base: Path) -> list[str]:
    """Pictures and sound files this segment needs that are not on disk, named as the storyboard writes them."""
    return missing_media(ep, seg, base)


def prompt_state(ep, seg, prompts: Path) -> tuple[str, str]:
    """(state, sentence): missing | kept | waits | blocked | built | changed."""
    txt, media = prompts / f"{seg.id}.txt", prompts / f"{seg.id}.media.json"
    if not txt.exists() or not media.exists():
        return "missing", "not built yet"
    if seg.status.startswith("accepted"):
        return "kept", "kept as it was built (the segment is accepted)"
    try:
        spec = json.loads(media.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "changed", f"{media} cannot be read - build it again"
    planned = ((spec.get("opens_from") or {}).get("source") == "planned")
    prompt_builder.ALLOW_PLANNED = planned        # compare with a build of the same kind as the one on disk
    try:
        now = next(c["text"] for c in prompt_builder.build(ep, seg).content if c["type"] == "text")
    except NotObservedYet:
        return "waits", "built from the plan; the segment before it is not accepted yet"
    except FileNotFoundError as e:
        return "blocked", f"cannot be built now: {e}"
    except ValueError as e:
        return "blocked", f"cannot be built now: {str(e)[:160]}"
    finally:
        prompt_builder.ALLOW_PLANNED = False
    if now != txt.read_text(encoding="utf-8"):
        return "changed", "out of date: the storyboard (or the end of the segment before it) changed after it was built"
    return "built", "built" + (" from the planned end of the segment before it" if planned else "")


def clip_size(clip: Path) -> str:
    try:
        info = signals.probe(clip)
        return f"{info['width']}x{info['height']}" if info.get("width") else ""
    except Exception:  # noqa: BLE001 - ffprobe missing or a broken file: the size is a convenience
        return ""


def main_clip(folder: Path, rec: dict) -> Path | None:
    """The video file of a take: the one its record names, else the first video in the folder."""
    for f in rec.get("files") or []:
        p = Path(f)
        if p.suffix.lower() in take_records.VIDEO_EXT and "_trimmed" not in p.stem:
            return p if p.exists() else folder / p.name
    hits = sorted(p for p in folder.glob("*") if p.suffix.lower() in take_records.VIDEO_EXT and "_trimmed" not in p.stem)
    return hits[0] if hits else None


def segment_report(ep, seg, raw_seg: dict, ep_path: Path, prompts: Path, takes: Path, entry: dict | None) -> dict:
    rep: dict = {"id": seg.id, "seconds": seg.duration, "mode": seg.mode, "status": seg.status}
    rep["missing_files"] = missing_files(ep, seg, ep_path.resolve().parent)
    rep["prompt"], rep["prompt_note"] = prompt_state(ep, seg, prompts)
    folder = takes / seg.id
    current = take_records.media_inputs_sha(prompts / f"{seg.id}.media.json")
    drafts, passes = [], []
    for name, rec in take_records.finished_takes(folder):
        # a second pass says so in its record; takes made before that was written are told by their workflow or folder name
        second = bool(rec.get("second_pass") or rec.get("from_latent")) or "refine" in Path(str(rec.get("workflow") or "")).name \
            or "_refine" in name
        (passes if second else drafts).append((name, rec))
    rep["drafts"] = [n for n, _r in drafts]
    # queued and never fetched (the script was stopped, the conversation lost): invisible to everything that reads records
    rep["pending"] = [{"take": n, "folder": str(folder / n), "seed": h.get("seed"), "queued_at": h.get("queued_at")}
                      for n, h in take_records.pending_takes(folder)]
    rep["drafts_out_of_date"] = [n for n, r in drafts if current and r.get("inputs_sha") and r["inputs_sha"] != current]
    acc = raw_seg.get("accepted_take") or {}
    accepted = seg.status.startswith("accepted") and bool(acc.get("path"))
    rep["accepted"] = None
    if accepted:
        p = Path(str(acc["path"]))
        in_take = (p.parent / "run.json").exists()            # else a file accepted from somewhere else: name the file itself
        rep["accepted"] = {"take": p.parent.name if in_take else str(p), "file": str(p), "seed": acc.get("seed"), "on_disk": p.exists(),
                           "deviation": seg.status == "accepted_with_deviation"}
    rep["second_passes"] = []
    for name, rec in passes:
        of_accepted = bool(accepted and acc.get("inputs_sha") and rec.get("inputs_sha") == acc["inputs_sha"]
                           and (acc.get("seed") is None or rec.get("seed") == acc.get("seed")))
        clip = main_clip(folder / name, rec)
        rep["second_passes"].append({"take": name, "of_accepted": of_accepted, "size": clip_size(clip) if clip else "",
                                     "file": str(clip) if clip else "", "warnings": rec.get("warnings") or []})
    rep["edit"] = None
    if entry:
        clip = Path(str(entry.get("video") or ""))
        level, why = take_records.provenance(raw_seg, clip, ep_path) if clip.is_file() else ("WARN", "the clip is not on disk")
        rep["edit"] = {"clip": str(clip), "size": entry.get("src_size") or "", "level": level, "note": why}
    rep["script_drift"] = take_records.script_drift(raw_seg, ep_path) if accepted else ""
    return rep


def ways_so_far(takes: Path) -> dict:
    """What the finished takes tell about how this project is run - the workflow file and the size overrides of the most
    recent draft and of the most recent second pass, per family: {'h3_ref2va': {'draft': (file name, [--set ...]), ...}}.
    The commands printed here repeat them: a bare command would fall back to the workflow's own 1344x768."""
    found: dict = {}
    for rj in takes.glob("*/*/run.json"):
        if rj.parent.name.startswith("_prev_"):
            continue
        try:
            rec = json.loads(rj.read_text(encoding="utf-8"))
            when = rj.stat().st_mtime
        except (OSError, json.JSONDecodeError):
            continue
        name = Path(str(rec.get("workflow") or "")).name
        family = next((f for f in ("h3_ref2va", "h3_fl2va") if name.startswith(f)), None)
        if rec.get("status") != "success" or not family:
            continue
        kind = "refine" if rec.get("second_pass") or rec.get("from_latent") or "refine" in name else "draft"
        sizes = [o for o in rec.get("overrides") or [] if str(o).split("=", 1)[0].rsplit(".", 1)[-1] in ("width", "height")]
        if kind not in found.setdefault(family, {}) or when > found[family][kind][2]:
            found[family][kind] = (name, sizes, when)
    return found


def voice_first(voices: list[dict]) -> str:
    """What has to happen before a segment is drafted when someone who speaks in it has no voice sample yet."""
    parts = []
    for v in voices:
        if v["first_accepted"]:
            parts.append(f"{v['character']}'s voice sample is still to cut from the accepted take of {v['first']} and to write to "
                         f"voice_reference (the block at the top)")
        else:
            parts.append(f"{v['character']} first speaks in {v['first']}, which is not accepted yet - accept it and cut the voice "
                         f"sample there (the block at the top)")
    return "; ".join(parts)


def next_step(rep: dict, ep_path: Path, prompts: Path, takes: Path, selects: Path, edl_path: Path, prev: dict | None,
              from_plan: bool = False, voices: list[dict] | None = None, ways: dict | None = None) -> str:
    sid, media = rep["id"], prompts / f"{rep['id']}.media.json"
    family = "h3_ref2va" if rep["mode"] == "ref2va" else "h3_fl2va"
    way = (ways or {}).get(family, {})
    draft_wf, draft_sets, as_before = FLOWS / f"{family}.api.json", "", ""
    if "draft" in way:                       # the workflow file (Sage or not) and the canvas of the drafts this project has
        if (FLOWS / way["draft"][0]).exists():
            draft_wf = FLOWS / way["draft"][0]
        draft_sets = "".join(f" --set {o}" for o in way["draft"][1])
        as_before = " (workflow and size as in the drafts this project already has)"
    refine_wf, refine_sets = FLOWS / (draft_wf.name.replace(".api.json", "_refine.api.json")), ""
    if not refine_wf.exists():
        refine_wf = FLOWS / f"{family}_refine.api.json"
    if "refine" in way:
        if (FLOWS / way["refine"][0]).exists():
            refine_wf = FLOWS / way["refine"][0]
        refine_sets = "".join(f" --set {o}" for o in way["refine"][1])
    log = " --log logs/takes.csv"            # every take goes into the takes log (qc-and-assembly.md)
    if rep.get("pending"):               # before anything else: a new job would queue behind it, and it may be the take wanted
        return (f"fetch the job(s) queued earlier and never collected: {py('comfy_submit.py')} --collect "
                + " ".join(cli(Path(x["folder"])) for x in rep["pending"])
                + " (it waits if the job is still running; nothing is queued) - then run this overview again")
    # a sample attached later changes this segment's prompt: whatever is drafted before that has to be drafted again
    before = f"first the voice: {voice_first(voices)}. This segment's prompt changes with the sample, so drafts come after it. Then: " if voices else ""
    if rep["missing_files"]:
        return (f"make the missing file(s) first - pictures: {py('plan_stills.py')} {cli(ep_path)} lists each with its command; "
                f"a voice sample is recorded, or cut from an accepted take (references/audio-and-post.md)"
                + (f". Also before this segment is drafted: {voice_first(voices)}" if voices else ""))
    if rep["prompt"] in ("missing", "changed"):
        return before + f"build the prompts: {py('build_prompts.py')} {cli(ep_path)} --out {cli(prompts)}" + (" --allow-planned" if from_plan else "")
    if rep["prompt"] == "blocked":
        return "fix what stops the build (see the prompt line), then build the prompts again"
    if not rep["accepted"]:
        good = [d for d in rep["drafts"] if d not in rep["drafts_out_of_date"]]
        if rep.get("first_check") and not good:      # drafts come from this picture: settle it before any GPU time is spent
            return (f"before any draft, the first frame: {rep['first_check']['why']}. Look at it against that ending - make it "
                    f"again (change this segment's first_frame_prompt and its first shot to the observed ending, then "
                    f"{py('plan_stills.py')} {cli(ep_path)} lists it under MAKE AGAIN), or, if it still fits: "
                    f"{py('plan_stills.py')} {cli(ep_path)} --fits {rep['first_check']['picture']}")
        if not good:
            return before + (f"make drafts: {py('comfy_submit.py')} {cli(draft_wf)} --media {cli(media)} --batch 3 --keep-latent"
                             f"{draft_sets}{log} --dry-run"
                             + (as_before if as_before else " (with Sage installed: the _sage file)")
                             + ", then the same command with --confirm <batch id>")
        unanchored = (f" These drafts were made without a voice sample ({voice_first(voices)}): the voice in them is not anchored - "
                      f"keep one and measure the voices after the mix (voice_check.py), or attach the sample and draft again.") if voices else ""
        if prev and not str(prev["status"]).startswith("accepted"):
            return (f"{len(good)} draft(s) wait - choose one after {prev['id']} is accepted (its real ending decides whether they still fit)"
                    + unanchored)
        pattern = f'"{(takes / sid).as_posix()}/**/*.mp4"'
        return (f"look at the {len(good)} draft(s), then choose one. Checks (SKILL.md step 7): {py('qc_probe.py')} {pattern} "
                f"--episode {cli(ep_path)} --out qc/probe; {py('qc_dialogue.py')} --episode {cli(ep_path)} --targets {pattern} "
                f"--out qc/dialogue; {py('contact_sheet.py')} {pattern} --episode {cli(ep_path)} (faces: identity_gate.py). "
                f"Write the chosen one back: {py('observe_take.py')} <the clip> --episode {cli(ep_path)} "
                f"--segment {sid} (look), then --as-planned or --write \"...\" --confidence ..." + unanchored)
    if not rep["accepted"]["on_disk"]:
        return f"the accepted take is not on disk - see {py('validate_episode.py')} {cli(ep_path)}"
    mine = [p for p in rep["second_passes"] if p["of_accepted"]]
    if not mine:
        folder = Path(rep["accepted"]["file"]).parent
        has_latent = any(folder.glob("*video*.latent"))
        own = folder / "media.json"
        refine = (f"{py('comfy_submit.py')} {cli(refine_wf)} --media {cli(own if own.exists() else media)} "
                  + (f"--from-latent {cli(folder)}" if has_latent else f"--seed {rep['accepted']['seed']}{draft_sets}")
                  + f"{refine_sets}{log} --dry-run"
                  + (" (target size as in the second passes this project already has)" if refine_sets else ""))
        if rep["edit"] and rep["edit"]["level"] != "WARN":      # the draft is in the edit: a decision, not an open step
            rep["optional"] = f"no second pass: the draft is in the edit as it is. To refine it after all: {refine}"
            return ""
        edl_cmd = f"{py('make_edl.py')} {cli(ep_path)} --selects {cli(selects)} --out {cli(edl_path)} --pick {sid}="
        if rep["edit"]:                                         # the edit list has this segment, with a clip that is not this take
            return (f"refine the accepted take: {refine} - the edit list holds another clip for this segment (the edit line above), so "
                    f"afterwards put the refined clip in its place: {edl_cmd}<the refined clip>; to use the accepted draft as it is: "
                    f"{edl_cmd}{cli(rep['accepted']['file'])}")
        return f"refine the accepted take: {refine} (or put the draft into the edit as it is: {edl_cmd}{cli(rep['accepted']['file'])})"
    if not rep["edit"]:
        return (f"put it into the edit: {py('make_edl.py')} {cli(ep_path)} --selects {cli(selects)} --out {cli(edl_path)} "
                f"--pick {sid}={cli(mine[-1]['file'])}")
    if rep["edit"]["level"] == "WARN" or (mine and Path(rep["edit"]["clip"]).resolve() == Path(rep["accepted"]["file"]).resolve()):
        return (f"the edit list does not use the second pass yet: {py('make_edl.py')} {cli(ep_path)} --selects {cli(selects)} "
                f"--out {cli(edl_path)} --pick {sid}={cli(mine[-1]['file'])}")
    return ""


def main():
    _utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("episode")
    ap.add_argument("--prompts", help="default: prompts/<episode>")
    ap.add_argument("--takes", help="default: takes/<name of the prompts folder>")
    ap.add_argument("--selects", help="default: selects/<episode>")
    ap.add_argument("--edl", help="default: edit/<episode>.edl.json")
    ap.add_argument("--final", help="default: final/<episode>.mp4")
    ap.add_argument("--json", help="also write the findings to this file")
    a = ap.parse_args()

    ep_path = Path(a.episode)
    ep = load_episode(ep_path)
    raw = json.loads(ep_path.read_text(encoding="utf-8"))
    name = ep_path.stem
    prompts = Path(a.prompts) if a.prompts else Path("prompts") / name
    takes = Path(a.takes) if a.takes else Path("takes") / prompts.resolve().name
    selects = Path(a.selects) if a.selects else Path("selects") / name
    edl_path = Path(a.edl) if a.edl else Path("edit") / f"{name}.edl.json"
    final = Path(a.final) if a.final else Path("final") / f"{name}.mp4"
    edl = {}
    if edl_path.exists():
        try:
            edl = json.loads(edl_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            edl = {}
    entries = {s["id"]: s for s in edl.get("segments", [])}

    total = sum(s.duration for s in ep.segments)
    print(f"{ep.title} - {len(ep.segments)} segment(s), {total} s  ({ep_path})")
    print(f"  prompts {prompts} | takes {takes} | selects {selects} | edit list {edl_path}"
          + ("" if edl_path.exists() else " (not made yet)"))
    # voice samples come before everything they change: say so at the top and again at each segment that waits for one
    status_of = {seg.id: seg.status for seg in ep.segments}
    accepted_file = {r["id"]: str((r.get("accepted_take") or {}).get("path") or "") for r in raw["segments"]}
    voices = [dict(v, first_accepted=status_of[v["first"]].startswith("accepted"), first_file=accepted_file.get(v["first"], ""))
              for v in voice_plan(ep) if v["later"]]
    if voices:
        print("\nfirst (a voice sample changes the prompts of the segments named here - drafts made before it is attached have to be made again)")
        for v in voices:
            later = ", ".join(v["later"])
            if v["first_accepted"]:
                print(f"     voice      {v['character']} has no sample: {v['first']}, where the character first speaks, is accepted - cut the sample "
                      f"from its take now" + (f" ({v['first_file']})" if v["first_file"] else "") + f", write it to voice_reference "
                      f"(references/audio-and-post.md §2), then build the prompt of {later}")
            else:
                print(f"     voice      {v['character']} has no sample: first speaks in {v['first']}, which is not accepted yet - draft and accept "
                      f"{v['first']}, cut the sample from that take, write voice_reference (references/audio-and-post.md §2), and only "
                      f"then draft {later}")
    reports, prev = [], None
    ways = ways_so_far(takes)
    first_checks = take_records.stale_first_frames(raw, ep_path)
    # one build command for the whole episode: drafts made in one go open from the PLANNED end of a segment that is not accepted yet
    from_plan = any((b.continuity or "").strip().startswith("@observed") and not a_.status.startswith("accepted")
                    for a_, b in zip(ep.segments, ep.segments[1:]))
    for seg, raw_seg in zip(ep.segments, raw["segments"]):
        rep = segment_report(ep, seg, raw_seg, ep_path, prompts, takes, entries.get(seg.id))
        rep["first_check"] = first_checks.get(seg.id)
        rep["next"] = next_step(rep, ep_path, prompts, takes, selects, edl_path, prev, from_plan,
                                [v for v in voices if seg.id in v["later"]], ways)
        reports.append(rep)
        acc = rep["accepted"]
        head = (f"accepted{' with a deviation' if acc['deviation'] else ''}: {acc['take']}"
                + (f", seed {acc['seed']}" if acc.get("seed") is not None else "")
                + ("" if acc["on_disk"] else "  !! NOT ON DISK")) if acc else ("rejected" if seg.status == "rejected" else "not accepted")
        print(f"\n{seg.id}  {seg.duration} s {seg.mode}  -  {head}")
        if rep["missing_files"]:
            print(f"     files      {len(rep['missing_files'])} missing: {', '.join(rep['missing_files'][:4])}"
                  + (" ..." if len(rep["missing_files"]) > 4 else ""))
        if rep["first_check"]:
            print(f"     first      !! {rep['first_check']['why']}")
        print(f"     prompt     {rep['prompt_note']}")
        if rep["script_drift"]:
            print(f"     !!         {rep['script_drift']}")
        stale = [] if acc else rep["drafts_out_of_date"]         # once a take is accepted the other drafts no longer matter
        line = f"{len(rep['drafts'])} draft(s)" + (f", {len(stale)} of them made from an earlier prompt ({', '.join(stale[:3])})" if stale else "")
        if not acc and rep["prompt"] == "changed" and len(rep["drafts"]) > len(stale):
            line += " - made from the prompt on disk, which is out of date (the prompt line): once it is rebuilt they count as made from an earlier prompt"
        if acc and acc["take"] in rep["drafts_out_of_date"]:
            line += " (the accepted one was made from an earlier prompt: a second pass takes the media.json kept in its folder)"
        if rep["pending"]:
            line += (f"; !! {len(rep['pending'])} job(s) queued and never collected (" + ", ".join(x["take"] for x in rep["pending"][:3])
                     + ") - running, finished or gone on the server")
        for p in rep["second_passes"]:
            line += (f"; second pass {p['take']}" + (f" {p['size']}" if p["size"] else "")
                     + (" of the accepted take" if p["of_accepted"] else " (not of the accepted take)")
                     + (" - made in spite of a warning" if p["warnings"] else ""))
        print(f"     takes      {line}")
        if rep["edit"]:
            e = rep["edit"]
            what = {"": "the accepted take or a second pass of it", "note": "a file that cannot be traced to a take"}.get(e["level"], "!! " + e["note"][:200])
            print(f"     edit       {e['clip']}" + (f" {e['size']}" if e["size"] else "") + f" - {what}")
        elif edl:
            print("     edit       not in the edit list")
        if rep["next"]:
            print(f"     next       {rep['next']}")
        elif rep.get("optional"):
            print(f"     optional   {rep['optional']}")
        prev = rep

    # ---- the episode as a whole ---------------------------------------------------------------------------
    print("\nafter the segments")
    post = {"edit_list": edl_path.exists(), "segments_in_edit": len(entries), "subtitles": None, "mix": None}
    todo = ""
    if not edl:
        print("     edit       no edit list yet")
        if all(r["accepted"] for r in reports):
            todo = f"{py('make_edl.py')} {cli(ep_path)} --selects {cli(selects)} --out {cli(edl_path)}"
    else:
        absent = [r["id"] for r in reports if not r["edit"]]
        print(f"     edit       {len(entries)} of {len(reports)} segment(s) in {edl_path}" + (f"; missing: {', '.join(absent)}" if absent else ""))
        sub = edl.get("subtitles")
        lines = [ln for s in edl.get("segments", []) for ln in s.get("lines") or []]
        if not lines:
            post["subtitles"] = "no lines"
            print("     subtitles  the episode has no lines")
        elif not sub:
            post["subtitles"] = "not timed"
            print("     subtitles  not timed yet")
            todo = todo or f"{py('retime_subtitles.py')} {cli(edl_path)} --out {cli(Path('subs') / name)}"
        elif edl_lib.subtitles_stale(edl, edl_path):
            post["subtitles"] = "stale"
            print("     subtitles  timed on another cut (a clip or an in / out frame changed since)")
            todo = todo or f"{py('retime_subtitles.py')} {cli(edl_path)} --out {cli(Path('subs') / name)}"
        else:
            review = [ln for ln in lines if ln.get("needs_review")]
            post["subtitles"] = "timed"
            print("     subtitles  timed for this cut" + (f"; {len(review)} line(s) marked for review" if review else ""))
        report = final.with_suffix(".mix.report.json")
        if not final.exists():
            post["mix"] = "not made"
            print(f"     mix        not made yet ({final})")
            if not absent and post["subtitles"] in ("timed", "no lines"):
                todo = todo or f"{py('mix_episode.py')} {cli(edl_path)} --out {cli(final)}" \
                               + (f" --ass {cli(Path('subs') / (name + '.ass'))}" if post["subtitles"] == "timed" else "")
        else:
            stale = edl_lib.mix_is_stale(edl, report_path=report if report.exists() else None, edl_path=edl_path)
            post["mix"] = "stale" if stale else "made"
            unfinished = bool(absent) or any(r["edit"] and r["edit"]["level"] == "WARN" for r in reports)
            print(f"     mix        {final}" + (f" - !! {stale}" if stale else " belongs to this cut")
                  + (" - a cut that is not the final one (see the edit lines above)" if unfinished and not stale else ""))
            if stale:
                todo = todo or f"{py('mix_episode.py')} {cli(edl_path)} --out {cli(final)}"
        # the score is optional and belongs to the finished cut: its length is the length of the cut
        music = edl.get("music") if isinstance(edl.get("music"), dict) else None
        if music and music.get("file"):
            there = edl_lib.resolve(edl_path, music["file"]).exists()
            post["music"] = "set" if there else "missing"
            print(f"     music      {music['file']}" + ("" if there else "  !! NOT ON DISK - the mix stops on a missing file"))
        else:
            post["music"] = "none"
            try:
                fps_cut, _plan, n_frames = edl_lib.timeline(edl)
            except (KeyError, ValueError, TypeError):
                fps_cut, n_frames = 24.0, 0
            if absent or not n_frames:
                print("     music      none in the edit list (optional) - make a score once every segment is in the cut: the cut's length "
                      "is the length to ask for")
            else:
                print(f"     music      none in the edit list (optional). The cut is {n_frames / fps_cut:.1f} s; a score for it: "
                      f"{py('comfy_submit.py')} {cli(FLOWS / 'acestep15_music.api.json')} --set \"94.tags=<genre, instruments, mood>\" "
                      f"--set 120.value={max(10, math.ceil(n_frames / fps_cut) + 2)} --out {cli(Path('audio') / name)} --tag score --dry-run; "
                      f"then name the file under \"music\" in {edl_path} and mix again (references/audio-and-post.md §2)")
    if todo and not any(r["next"] for r in reports):
        print(f"     next       {todo}")
    open_segments = [r["id"] for r in reports if r["next"]]
    print(f"\n{len(reports) - len(open_segments)} of {len(reports)} segment(s) need nothing more"
          + (f"; open: {', '.join(open_segments)}" if open_segments else ""))
    if a.json:
        out = Path(a.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"episode": str(ep_path), "voices": voices, "segments": reports, "post": post, "next": todo},
                                  ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"written: {out}")


if __name__ == "__main__":
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
