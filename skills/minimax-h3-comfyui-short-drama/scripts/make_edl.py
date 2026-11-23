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
Re-running keeps your manual edits for segments that already exist in --out unless --overwrite is given.

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


def find_clip(selects: Path, seg_id: str) -> Path | None:
    direct = [selects / f"{seg_id}{e}" for e in VIDEO_EXT]
    for p in direct:
        if p.exists():
            return p
    pools = [sorted(selects.glob(f"{seg_id}_*")), sorted((selects / seg_id).glob("*")) if (selects / seg_id).is_dir() else []]
    for pool in pools:
        for p in pool:
            if p.suffix.lower() in VIDEO_EXT:
                return p
    for p in sorted(selects.rglob("*")):
        if p.suffix.lower() in VIDEO_EXT and seg_id in re.split(r"[^A-Za-z0-9]+", p.stem):
            return p
    return None


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
    old = {}
    if out_path.exists() and not a.overwrite:
        old = {s["id"]: s for s in json.loads(out_path.read_text(encoding="utf-8")).get("segments", [])}
    prev = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() and not a.overwrite else {}

    selects = Path(a.selects)
    picks = {}
    for item in a.pick:
        k, _, v = item.partition("=")
        if not Path(v).exists():
            sys.exit(f"--pick {k}: clip not found: {v}")
        picks[k.strip()] = Path(v)
    segments, missing, doubts, untraced = [], [], [], []
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
        if sid in old and sid not in picks:
            segments.append(old[sid])
            kept_clip = Path(str(old[sid].get("video") or ""))
            if kept_clip.is_file():                          # the accepted take may have changed since this entry was made
                check(seg, kept_clip, old[sid], kept=True)
            continue
        clip = picks.get(sid) or find_clip(selects, sid)
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
        segments.append({"id": sid, "video": str(clip), "frames_total": info["frames"], "src_fps": round(info["fps"], 4),
                         "in_frame": in_f, "out_frame": out_f,
                         "audio": "native" if info["has_audio"] else None, "nondialogue": None,
                         "l_cut": a.l_cut if lines else 0.0, "j_cut": 0.0, "scene": seg.get("scene_id"), "lines": lines})
        print(f"{sid}: {clip.name} {info['frames']} frames -> use [{in_f}, {out_f}) = {(out_f - in_f) / info['fps']:.3f}s"
              f"{' (end freeze cut)' if cut else ''}, {len(lines)} line(s)")
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
    if doubts:
        print(f"CHECK: {', '.join(doubts)} - the clip in the edit is not the take that was accepted, nor a second pass of it "
              f"(WARN lines above). To use another clip: --pick <segment>=<clip> (rebuilds that segment's entry only)")
    if not any_accepted:
        print("note: the storyboard records no accepted takes (observe_take.py was not used), so the clips are taken as given")
    if missing:
        print(f"MISSING selected clips for: {', '.join(missing)} (looked under {selects})")
        sys.exit(2)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
