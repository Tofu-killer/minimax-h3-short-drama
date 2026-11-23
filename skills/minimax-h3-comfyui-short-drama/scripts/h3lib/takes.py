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


def stale_takes(folder: Path, current_sha: Optional[str]) -> list:
    """Names of the finished takes in a segment's folder that were made from another prompt or other references
    than the segment has now. Takes without a recorded fingerprint cannot be judged and are not listed."""
    if not current_sha:
        return []
    return [name for name, rec in finished_takes(folder) if rec.get("inputs_sha") and rec["inputs_sha"] != current_sha]
