#!/usr/bin/env python3
"""Build the edit decision list (EDL) for an episode from the storyboard and the selected takes.

    python3 make_edl.py episodes/ep01.json --selects selects/ep01 --out edit/ep01.edl.json

"Selecting" a take means copying (or moving) the chosen, refined clip into the selects folder under a name that
starts with its segment id - one clip per segment. For every storyboard segment the script takes the first match of
    <selects>/<seg_id>.mp4, <selects>/<seg_id>_*.mp4, <selects>/<seg_id>/*.mp4,
    or any video under <selects> whose file name contains the segment id as a token
(or the clip named with --pick <seg_id>=<clip>, which also replaces an existing entry) -
counts its frames with ffprobe and writes one entry:

    in_frame   frames dropped at the head (default 2: H3 takes often open on a stray onset syllable)
    out_frame  exclusive end frame = frame count minus the declared end freeze
               (both count frames of the clip itself; src_fps records the clip's frame rate)
               (--freeze-tail seconds, applied to segments whose last shot has "end_hold": true,
               or to every segment with --freeze-tail-all)
    lines      the locked dialogue lines (speaker name + text) - subtitle text always comes from here;
               retime_subtitles.py adds "start" / "end" in seconds FROM THE SEGMENT'S IN POINT
    l_cut / j_cut, scene, audio ("native" = the take's own sound, or a path to a dialogue stem)

Everything downstream reads this single file: retime_subtitles.py (fills line times),
mix_episode.py (cuts, mixes, masters), export_capcut_draft.py / export_otio.py (editable projects).
Hand edits belong here too: nudge a cut, add "music" / "ambience", set an L-cut.
Re-running keeps your manual edits for segments that already exist in --out unless --overwrite is given
(--overwrite rebuilds the segment entries; name, ambience, music and loudness of the edit list stay). A clip added to
the selects folder later does not replace a kept entry by itself - the script says that it is there and gives the
--pick that switches to it. Two clips for one segment in the selects folder are not guessed at: AMBIGUOUS, exit 2.

Each clip is compared with the take the storyboard records as accepted (observe_take.py): the accepted file itself and
a second pass of it (same prompt, references and seed) pass in silence; anything else - another seed, a draft made from
an earlier prompt, a segment without an accepted take - gets a WARN line. The edit list is written either way.

Needs ffprobe on PATH. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import edl as edl_lib  # noqa: E402
import takes as take_records  # noqa: E402


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                        "-show_entries", "stream=nb_read_frames,r_frame_rate,width,height",
                        "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        st = json.loads(r.stdout)["streams"][0]
        num, den = st["r_frame_rate"].split("/")
        frames = int(st["nb_read_frames"])
    except Exception:  # noqa: BLE001
        sys.exit(f"ffprobe could not read {path}: {r.stderr.strip()[:200]}")
    a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"frames": frames, "fps": float(num) / float(den or 1), "width": int(st["width"]),
            "height": int(st["height"]), "has_audio": bool(a.stdout.strip())}


def candidates(selects: Path, seg_id: str) -> list[Path]:
    """Every clip in the selects folder that belongs to this segment by its name: <id>.mp4, <id>_*.mp4, <id>/*.mp4, or
    the id as a word of the file name. One per segment is the rule; more than one is reported, not guessed at."""
    pools = [[selects / f"{seg_id}{e}" for e in sorted(VIDEO_EXT)], sorted(selects.glob(f"{seg_id}_*")),
             sorted((selects / seg_id).glob("*")) if (selects / seg_id).is_dir() else [],
             [p for p in sorted(selects.rglob("*")) if seg_id in re.split(r"[^A-Za-z0-9]+", p.stem)]]
    out: list[Path] = []
    for pool in pools:
        for p in pool:
            if p.suffix.lower() in VIDEO_EXT and p.is_file() and p not in out:
                out.append(p)
    return out


def find_clip(selects: Path, seg_id: str) -> Path | None:
    found = candidates(selects, seg_id)
    return found[0] if found else None


def keep_locked_lines(new: dict, before: dict | None) -> str:
    """An entry is built again (--pick, --overwrite): line times fixed by hand ("locked") are carried over when the
    clip is the same file content and starts on the same frame - then they are still true. Returns a sentence when
    locked times had to be left behind."""
    locked = [ln for ln in (before or {}).get("lines") or [] if ln.get("locked")]
    if not locked:
        return ""
    same = before.get("clip_sha") and before.get("clip_sha") == new.get("clip_sha") and before.get("in_frame") == new.get("in_frame")
    if not same:
        return (f"{len(locked)} line time(s) locked by hand in the earlier entry were not carried over: the clip or its in point is "
                f"another one, so those times no longer point at the words - run retime_subtitles.py and lock them again")
    for ln in new.get("lines") or []:
        old = next((o for o in locked if o.get("speaker") == ln.get("speaker") and o.get("text") == ln.get("text")), None)
        if old:
            ln.update({k: old[k] for k in ("start", "end", "locked", "gain_db") if k in old})
    return ""


def source_take(clip: Path, acc: dict, episode: Path) -> Path | None:
    """The file below the segment's takes folder that `clip` is a copy of (same bytes) - a clip copied into
    selects/ has no run.json beside it, the take it was copied from has."""
    rel = Path(str(acc.get("path") or ""))
    if not rel.name:
        return None
    try:
        size, digest = clip.stat().st_size, None
        for base in ([Path()] if rel.is_absolute() else [Path.cwd(), episode.resolve().parent.parent]):
            folder = (base / rel).parent.parent              # takes/<episode>/<segment>
            if not folder.is_dir():
                continue
            for cand in sorted(folder.glob("*/*")):
                if cand.suffix.lower() in VIDEO_EXT and cand.is_file() and cand.stat().st_size == size:
                    digest = digest or take_records.sha256_file(clip)
                    if take_records.sha256_file(cand) == digest:
                        return cand
            break
    except OSError:
        pass
    return None


def lines_of_take(seg: dict, episode: Path) -> list[str] | None:
    """The dialogue lines the accepted take was made with, read from the prompt kept beside it (prompt.txt in the take's
    folder) or, for takes made before prompts were kept, from the prompt file its run.json names. None when neither
    can be read."""
    acc = seg.get("accepted_take") or {}
    rel = Path(str(acc.get("path") or ""))
    if not rel.name:
        return None
    for base in ([Path()] if rel.is_absolute() else [Path.cwd(), episode.resolve().parent.parent]):
        take = base / rel
        places = [take.parent / "prompt.txt"]
        rec = take_records.take_record(take) or {}
        if rec.get("media_json"):
            media = Path(rec["media_json"]) if Path(rec["media_json"]).is_absolute() else base / rec["media_json"]
            try:
                spec = json.loads(media.read_text(encoding="utf-8"))
                places.append(media.parent / spec.get("prompt_file", f"{spec.get('segment', seg['id'])}.txt"))
            except (OSError, json.JSONDecodeError):
                pass
        for f in places:
            try:
                return [" ".join(t.split()) for t in re.findall(r"<d>\[[^\]]*\]\s*(.*?)</d>", f.read_text(encoding="utf-8"), re.S)]
            except OSError:
                continue
    return None


def script_drift(seg: dict, episode: Path) -> str:
    """The storyboard's lines against the lines the accepted take was made with. Subtitles are written from the
    storyboard: when a line was edited after the take was accepted, they would show words nobody says."""
    made = lines_of_take(seg, episode)
    if made is None:
        return ""
    now = [" ".join(str(d.get("text", "")).split()) for sh in seg.get("shots", []) for d in sh.get("dialogue", [])]
    if sorted(made) == sorted(now):
        return ""
    gone = [t for t in made if t not in now]
    new = [t for t in now if t not in made]
    return ("the storyboard's lines are not the ones the accepted take was made with"
            + (f" - in the take: {' / '.join(gone)[:120]}" if gone else "") + (f" - in the storyboard now: {' / '.join(new)[:120]}" if new else "")
            + ". Subtitles come from the storyboard: put the line back as it is spoken, or rebuild the segment "
              "(build_prompts.py --only) and make its take again")


def provenance(seg: dict, clip: Path, episode: Path) -> tuple[str, str]:
    """Is this clip the take the storyboard records as accepted, or a second pass of it (same prompt, references
    and seed)? ('', '') when it is; ('WARN', why) when its record says it is something else or the segment has no
    accepted take; ('note', why) when nothing says what the file was made from. The edit is built either way."""
    acc = seg.get("accepted_take") or {}
    if not str(seg.get("status") or "").startswith("accepted") or not acc:
        return "WARN", ("the storyboard records no accepted take for this segment (observe_take.py writes it) - "
                        "nothing says this clip is the one that was chosen")
    try:
        if take_records.sha256_file(clip) == acc.get("sha256"):
            return "", ""
    except OSError:
        pass
    rec, made_in = take_records.take_record(clip), clip.parent.name
    if rec is None:                                          # a copy in selects/: find the take it was copied from
        src = source_take(clip, acc, episode)
        if src is not None:
            rec, made_in = take_records.take_record(src), src.parent.name
    was = Path(str(acc.get("path") or "?")).parent.name
    if rec and rec.get("inputs_sha") and acc.get("inputs_sha"):
        if rec["inputs_sha"] == acc["inputs_sha"] and (acc.get("seed") is None or rec.get("seed") == acc.get("seed")):
            if rec.get("warnings"):                          # submitted although the preview warned (another canvas, length ...)
                return "WARN", (f"{made_in} is a second pass of the accepted take ({was}), but it was submitted in spite of a warning: "
                                f"{str(rec['warnings'][0])[:300]}")
            return "", ""                                    # a second pass of the accepted take
        why = ("another seed" if rec["inputs_sha"] == acc["inputs_sha"] else "another prompt or other references")
        return "WARN", (f"this is not the accepted take ({was}) nor a refine of it: {made_in} was made with {why} "
                        f"(seed {rec.get('seed', '?')}; accepted: seed {acc.get('seed', '?')})")
    return "note", (f"cannot tell what this file was made from: it is not the accepted take ({was}) byte for byte, has no "
                    f"run.json beside it and is not a copy of a take in that segment's folder. Expected for a clip finished in "
                    f"another tool (upscaled, interpolated); otherwise pick the file with --pick")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("episode")
    ap.add_argument("--selects", required=True, help="folder holding one chosen (refined) clip per segment")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--size", default="1920x1080", help="delivery size WxH")
    ap.add_argument("--lead-trim-frames", type=int, default=2)
    ap.add_argument("--freeze-tail", type=float, default=1.0, help="seconds of declared end freeze to cut")
    ap.add_argument("--freeze-tail-all", action="store_true", help="cut the freeze tail on every segment, not only end_hold ones")
    ap.add_argument("--l-cut", type=float, default=0.25, help="seconds the sound of a segment outlasts its picture")
    ap.add_argument("--pick", action="append", default=[], metavar="SEG=CLIP",
                    help="use this clip for this segment instead of looking in --selects (repeatable), e.g. --pick s03=takes/ep01/s03/s03_103/out.mp4")
    ap.add_argument("--overwrite", action="store_true", help="rebuild entries even if --out already has them")
    a = ap.parse_args()

    ep_path = Path(a.episode)
    ep = json.loads(ep_path.read_text(encoding="utf-8"))
    names = {c["id"]: c.get("name", c["id"]) for c in ep.get("characters", [])}
    w, h = (int(x) for x in a.size.lower().split("x"))
    out_path = Path(a.out)
    # the earlier edit list: its entries are kept unless --overwrite / --pick rebuilds them; its name, ambience, music,
    # loudness and subtitle record are the project's settings and stay in either case
    prev = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    before = {s["id"]: s for s in prev.get("segments", [])}
    old = {} if a.overwrite else before

    selects = Path(a.selects)
    picks = {}
    for item in a.pick:
        k, _, v = item.partition("=")
        if not Path(v).exists():
            sys.exit(f"--pick {k}: clip not found: {v}")
        picks[k.strip()] = Path(v)
    segments, missing, doubts, untraced, replaced, ambiguous, drifted = [], [], [], [], [], [], []
    any_accepted = any(seg.get("accepted_take") for seg in ep["segments"])

    def check(seg: dict, clip: Path, entry: dict, kept: bool = False) -> None:
        level, doubt = provenance(seg, clip, ep_path)
        if level == "WARN" and not any_accepted:
            level = ""                                       # an episode made without observe_take.py: said once, below
        entry.pop("take_check", None)
        if level:
            (doubts if level == "WARN" else untraced).append(seg["id"])
            where = f" (entry kept from {out_path.name}: {clip})" if kept else ""
            print(f"  {level} {seg['id']}{where}: {doubt}")
        if level == "WARN":
            entry["take_check"] = doubt                      # mix_episode.py repeats it: the master should not pass in silence

    for seg in ep["segments"]:
        sid = seg["id"]
        drift = script_drift(seg, ep_path)
        if drift:
            drifted.append(sid)
            print(f"  WARN {sid}: {drift}")
        if sid in old and sid not in picks:
            segments.append(old[sid])
            kept_clip = Path(str(old[sid].get("video") or ""))
            if kept_clip.is_file():                          # the accepted take may have changed since this entry was made
                check(seg, kept_clip, old[sid], kept=True)
                was = old[sid].get("clip_sha")
                if was and was != edl_lib.clip_sha(kept_clip):
                    replaced.append(sid)
                    print(f"  WARN {sid} (entry kept from {out_path.name}): {kept_clip} has other content than when this entry was made - "
                          f"its in / out frames and line times were measured on the old clip. Rebuild the entry: --pick {sid}={kept_clip}")
            others = [c for c in candidates(selects, sid) if not (kept_clip.exists() and c.resolve() == kept_clip.resolve())]
            if others:                                       # a clip added to selects/ later does not replace a kept entry by itself
                print(f"  note {sid}: the edit list keeps {kept_clip}; {selects} also holds {', '.join(c.name for c in others)}. "
                      f"To use one of them instead: --pick {sid}={others[0]}")
            continue
        found = [picks[sid]] if sid in picks else candidates(selects, sid)
        if len(found) > 1:                                   # which of them is the film? not for this script to guess
            ambiguous.append(sid)
            print(f"AMBIGUOUS {sid}: {len(found)} clips in {selects} belong to this segment ({', '.join(c.name for c in found)}) - "
                  f"one per segment. Take out the ones that are not the final clip, or name it: --pick {sid}={found[-1]}")
            if sid in before:
                segments.append(before[sid])                 # the entry of the earlier edit list stays until it is decided
            continue
        clip = found[0] if found else None
        if clip is None:
            missing.append(sid)
            continue
        info = probe(clip)
        if abs(info["fps"] - a.fps) > 0.01:
            print(f"NOTE {sid}: clip is {info['fps']:.3f} fps, timeline is {a.fps:g} fps - mix_episode.py conforms it "
                  f"(frame numbers in the EDL stay in clip frames; src_fps records the clip rate)")
        hold = a.freeze_tail_all or bool(seg["shots"] and seg["shots"][-1].get("end_hold"))
        cut = int(round(a.freeze_tail * info["fps"])) if hold else 0
        in_f = min(a.lead_trim_frames, max(0, info["frames"] - 1))
        out_f = max(in_f + 1, info["frames"] - cut)
        lines = []
        for sh in seg["shots"]:
            for d in sh.get("dialogue", []):
                lines.append({"speaker": d["speaker"], "name": "旁白" if d["speaker"] == "narrator" else names.get(d["speaker"], d["speaker"]),
                              "text": d["text"], "shot": sh["index"], **({"en": d["en"]} if d.get("en") else {})})
        segments.append({"id": sid, "video": str(clip), "clip_sha": edl_lib.clip_sha(clip), "frames_total": info["frames"],
                         "src_fps": round(info["fps"], 4), "src_size": f"{info['width']}x{info['height']}",
                         "in_frame": in_f, "out_frame": out_f,
                         "audio": "native" if info["has_audio"] else None, "nondialogue": None,
                         "l_cut": a.l_cut if lines else 0.0, "j_cut": 0.0, "scene": seg.get("scene_id"), "lines": lines})
        print(f"{sid}: {clip.name} {info['width']}x{info['height']}, {info['frames']} frames -> use [{in_f}, {out_f}) = "
              f"{(out_f - in_f) / info['fps']:.3f}s{' (end freeze cut)' if cut else ''}, {len(lines)} line(s)")
        lost = keep_locked_lines(segments[-1], before.get(sid))
        if lost:
            print(f"  note {sid}: {lost}")
        check(seg, clip, segments[-1])

    edl = {"name": prev.get("name") or ep_path.stem, "title": ep.get("title", ""), "fps": a.fps, "width": w, "height": h,
           "segments": segments,
           "ambience": prev.get("ambience", {}),
           "music": prev.get("music"),
           "loudness": prev.get("loudness", {"dialogue_lufs": -16, "program_lufs": -14, "true_peak": -1.5})}
    if prev.get("subtitles"):
        edl["subtitles"] = prev["subtitles"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(edl, ensure_ascii=False, indent=1), encoding="utf-8")
    _fps, _plan, total = edl_lib.timeline(edl)
    print(f"wrote {out_path}: {len(segments)} segment(s), {total} frames = {total / a.fps:.3f}s")
    sizes: dict[str, list[str]] = {}
    for e in segments:                                       # one size for the whole film, or some segments were left unrefined
        if e.get("src_size"):
            sizes.setdefault(e["src_size"], []).append(e["id"])
    if len(sizes) > 1:
        biggest = max(sizes, key=lambda z: int(z.split("x")[0]) * int(z.split("x")[1]))
        rest = "; ".join(f"{z}: {', '.join(ids)}" for z, ids in sizes.items() if z != biggest)
        print(f"note: the clips are not all the same size - {biggest}: {', '.join(sizes[biggest])}; {rest}. mix_episode.py scales "
              f"everything to the delivery size, so a smaller clip is shown enlarged: if it is a draft whose refine was not made or "
              f"not picked, the film will be soft there")
    if doubts:
        print(f"CHECK: {', '.join(doubts)} - the clip in the edit is not a clean second pass of the take that was accepted "
              f"(WARN lines above say what it is). To use another clip: --pick <segment>=<clip> (rebuilds that segment's entry only)")
    if not any_accepted:
        print("note: the storyboard records no accepted takes (observe_take.py was not used), so the clips are taken as given")
    if missing:
        print(f"MISSING selected clips for: {', '.join(missing)} (looked under {selects})")
    if ambiguous:
        print(f"NOT DECIDED: {', '.join(ambiguous)} - more than one clip each (AMBIGUOUS lines above); the edit list "
              + ("keeps their earlier entries" if all(x in before for x in ambiguous) else "has no entry for them yet") + " until you choose")
    if missing or ambiguous:
        sys.exit(2)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
