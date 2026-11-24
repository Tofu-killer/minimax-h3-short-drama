"""What a take was made from.

comfy_submit.py writes a run.json beside every take; build_prompts.py and observe_take.py read it back to tell
whether a take still belongs to the prompt and the references a segment has NOW. One definition of the
fingerprint lives here so the three scripts cannot drift apart.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_name(path: Path) -> str:
    """The name a file gets in ComfyUI's input folder: its stem in plain ASCII plus the first 8 hex digits of its
    content hash. Two different files that share a base name (face.png of two characters) can then not overwrite
    each other, the same file always lands on the same name, and a Chinese file name never has to travel in an
    HTTP header."""
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("._") or "file"
    return f"{stem}_{sha256_file(path)[:8]}{path.suffix.lower()}"


def text_sha(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()[:16]


def inputs_sha(prompts: list, media: dict) -> str:
    """Hash of what the model is asked to render: the prompt text and the content of every file sent along.
    `media` maps upload name -> sha256. A workflow that carries the same prompt on two H3 nodes (a second pass with
    its own conditioning node) gives the same value as one that carries it once."""
    texts = sorted({str(p) for p in prompts if p})
    return hashlib.sha256(("\x1f".join(texts) + "\x1e" + "\x1f".join(sorted(media.values()))).encode()).hexdigest()[:16]


def media_inputs_sha(media_json: Path) -> Optional[str]:
    """The inputs_sha a take gets when it is submitted with `--media <this file>` as it is on disk now.
    None when the file, its prompt or one of its references cannot be read."""
    try:
        spec = json.loads(Path(media_json).read_text(encoding="utf-8"))
        prompt = (Path(media_json).parent / spec.get("prompt_file", f"{spec['segment']}.txt")).read_text(encoding="utf-8")
        media = {}
        for item in spec.get("media", []):
            p = Path(item["path"])
            media[upload_name(p)] = sha256_file(p)
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return None
    return inputs_sha([prompt], media)


AUDIO_EXT = (".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac")


def what_changed(rec: dict, media_json: Path, take_folder: Optional[Path] = None) -> list:
    """What differs between the inputs a take was made from (its run.json: upload name -> sha256 of every file sent,
    and the prompt.txt kept beside it) and what `--media media_json` would send now. Sentences for a message;
    [] when nothing can be told apart (a record without the file list)."""
    then = {k: v for k, v in (rec.get("media_sha256") or {}).items() if not k.lower().endswith(".latent")}
    try:
        spec = json.loads(Path(media_json).read_text(encoding="utf-8"))
        now_prompt = (Path(media_json).parent / spec.get("prompt_file", f"{spec['segment']}.txt")).read_text(encoding="utf-8")
        now = {}
        for item in spec.get("media", []):
            now[upload_name(Path(item["path"]))] = Path(item["path"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return []
    if not then and now:                                   # an old record without the file list
        return []

    def stem(name: str) -> str:                            # upload name = <stem>_<8 hex of the content><suffix>
        return re.sub(r"_[0-9a-f]{8}(\.[A-Za-z0-9]+)$", r"\1", name)

    old_stems = {stem(n) for n in then}
    out = []
    for name, path in now.items():
        if name in then:
            continue
        kind = "voice sample" if path.suffix.lower() in AUDIO_EXT else "picture"
        out.append(f"the {kind} {path.name} " + ("has other content now" if stem(name) in old_stems else "was added since"))
    gone = [n for n in then if n not in now and stem(n) not in {stem(m) for m in now}]
    if gone:
        out.append(f"{len(gone)} file(s) it was given are no longer in the list ({', '.join(stem(n) for n in gone[:3])})")
    kept = (Path(take_folder) / "prompt.txt") if take_folder else None
    if kept is not None and kept.is_file():
        if kept.read_text(encoding="utf-8") != now_prompt:
            out.append("the prompt text is another one")
    elif not out:
        out.append("the prompt text is another one")       # same files, another fingerprint: only the text is left
    return out


def take_record(take: Path) -> Optional[dict]:
    """run.json of the take a clip belongs to (the clip, or its _trimmed copy, lies in the take's folder)."""
    try:
        rec = json.loads((Path(take).parent / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return rec if isinstance(rec, dict) else None


def finished_takes(folder: Path) -> list:
    """[(take folder name, run.json)] of the finished takes below a segment's folder (takes/<episode>/<segment>),
    superseded ones (_prev_*) left out."""
    out = []
    if not Path(folder).is_dir():
        return out
    for rj in sorted(Path(folder).glob("*/run.json")):
        if rj.parent.name.startswith("_prev_"):
            continue
        try:
            rec = json.loads(rj.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(rec, dict) and rec.get("status") == "success":
            out.append((rj.parent.name, rec))
    return out


STILLS_RECORD = Path("bible/prompts/.stills_plan.json")       # plan_stills.py's manifest, at its default place


def stale_first_frames(raw: dict, episode: Path, stills_record: Path | None = None) -> dict:
    """{segment id: {"picture", "previous", "deviations", "why"}} for first frames that were made BEFORE the segment
    they follow got the ending it has now. A segment that continues the one before it ("@observed") opens from that
    segment's accepted take; when the take was accepted with a deviation from the plan, a first frame painted for the
    planned ending may show another pose or other positions. The picture is older than the accepted take (or than its
    acceptance), nobody has confirmed that it still fits, and the segment itself is not accepted yet: look at it."""
    out: dict = {}
    try:
        fits = json.loads((stills_record or STILLS_RECORD).read_text(encoding="utf-8")).get("fits") or {}
    except (OSError, json.JSONDecodeError, AttributeError):
        fits = {}
    segs = raw.get("segments") or []
    for prev, seg in zip(segs, segs[1:]):
        first = seg.get("first_frame")
        if not first or not str(seg.get("continuity") or "").strip().startswith("@observed") \
                or str(seg.get("status") or "").startswith("accepted") or prev.get("status") != "accepted_with_deviation":
            continue
        pic = Path(first) if Path(first).exists() else Path(episode).parent / first
        acc = prev.get("accepted_take") or {}
        take = Path(str(acc.get("path") or ""))
        try:
            made = pic.stat().st_mtime
        except OSError:
            continue                                         # not made yet: the stills plan lists it
        since = float(acc.get("accepted_at") or 0)
        try:
            since = max(since, take.stat().st_mtime)
        except OSError:
            pass
        observed = str(prev.get("observed_end_state") or "").strip()
        if made >= since or (observed and fits.get(str(first)) == text_sha(observed)):
            continue
        devs = [str(d) for d in prev.get("accepted_deviations") or []]
        out[seg["id"]] = {"picture": str(first), "previous": prev["id"], "deviations": devs,
                          "why": (f"{first} is older than the accepted take of {prev['id']}, which ends differently from the plan"
                                  + (f" ({'; '.join(devs)})" if devs else "") + " - it was made for the planned ending")}
    return out


def pending_takes(folder: Path) -> list:
    """[(take folder name, handle.json)] of the jobs that were queued for a segment and whose result was never fetched:
    a handle without a record beside it. The job may still be running, be finished on the server, or be gone."""
    out = []
    if not Path(folder).is_dir():
        return out
    for hj in sorted(Path(folder).glob("*/handle.json")):
        if hj.parent.name.startswith("_prev_") or (hj.parent / "run.json").exists():
            continue
        try:
            h = json.loads(hj.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(h, dict) and h.get("prompt_id"):
            out.append((hj.parent.name, h))
    return out


def stale_takes(folder: Path, current_sha: Optional[str]) -> list:
    """Names of the finished takes in a segment's folder that were made from another prompt or other references
    than the segment has now. Takes without a recorded fingerprint cannot be judged and are not listed."""
    if not current_sha:
        return []
    return [name for name, rec in finished_takes(folder) if rec.get("inputs_sha") and rec["inputs_sha"] != current_sha]


# ---- which take a clip is, and what the accepted take was made with -----------------------------------------
# Used where clips enter the edit (make_edl.py) and in the overview of a project (project_status.py).

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}


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
                    digest = digest or sha256_file(clip)
                    if sha256_file(cand) == digest:
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
        rec = take_record(take) or {}
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
        if sha256_file(clip) == acc.get("sha256"):
            return "", ""
    except OSError:
        pass
    rec, made_in = take_record(clip), clip.parent.name
    if rec is None:                                          # a copy in selects/: find the take it was copied from
        src = source_take(clip, acc, episode)
        if src is not None:
            rec, made_in = take_record(src), src.parent.name
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
