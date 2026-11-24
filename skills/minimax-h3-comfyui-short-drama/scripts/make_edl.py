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

VIDEO_EXT = take_records.VIDEO_EXT


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


source_take, lines_of_take, script_drift, provenance = (take_records.source_take, take_records.lines_of_take,
                                                         take_records.script_drift, take_records.provenance)


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

    def also_there(seg: dict, used: Path) -> None:
        """Clips of this segment in the selects folder that the edit does not use: say what each one is. A rough cut's
        clip left there is offered back by name on every run, and --overwrite would put it into the film."""
        sid = seg["id"]
        for c in candidates(selects, sid):
            if used.exists() and c.resolve() == used.resolve():
                continue
            level, why = provenance(seg, c, ep_path)
            if level == "WARN" and any_accepted:
                print(f"  note {sid}: {selects} also holds {c.name}, which is not the accepted take nor a second pass of it "
                      f"({why[:150]}). It is not used - take it out of the folder, so that nothing picks it up again")
            elif level == "note":
                print(f"  note {sid}: {selects} also holds {c.name} (nothing says what it was made from); the edit uses {used}. "
                      f"To use it instead: --pick {sid}={c}")
            else:
                print(f"  note {sid}: the edit list uses {used}; {selects} also holds {c.name}. To use it instead: --pick {sid}={c}")

    def in_selects(clip: Path) -> bool:
        try:
            clip.resolve().relative_to(selects.resolve())
            return True
        except ValueError:
            return False

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
            also_there(seg, kept_clip)                       # a clip added to selects/ later does not replace a kept entry by itself
            continue
        found = [picks[sid]] if sid in picks else candidates(selects, sid)
        earlier = Path(str((before.get(sid) or {}).get("video") or ""))
        if a.overwrite and sid not in picks and earlier.is_file() and not in_selects(earlier):
            # the entry was made from a clip named with --pick (a take in its own folder): --overwrite measures that clip
            # again, it does not fall back to whatever lies in the selects folder
            found = [earlier]
            print(f"  note {sid}: rebuilt from {earlier} (the clip this entry was picked from), not from {selects}")
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
        if not in_selects(clip) or len(candidates(selects, sid)) > 1:
            also_there(seg, clip)

    edl = {"name": prev.get("name") or ep_path.stem, "title": ep.get("title", ""), "fps": a.fps, "width": w, "height": h,
           "episode": str(ep_path),                          # mix_episode.py compares the clips with it again, at mix time
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
