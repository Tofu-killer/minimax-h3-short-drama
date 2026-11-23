#!/usr/bin/env python3
"""Submit an API-format ComfyUI workflow, wait for it, download the outputs - safely re-runnable.

Works against a stock ComfyUI server (default http://127.0.0.1:8188). Standard library only, so it runs
inside any agent sandbox or on Windows with the ComfyUI-embedded python.

    # 1) export the workflow from ComfyUI with "Export (API)" -> yz_ref2va.api.json
    # 2) override inputs by node id or by node title, upload media, run:
    python3 comfy_submit.py yz_ref2va.api.json \
        --set 12.text=@prompts/ep01/s03.txt \
        --set-title "Reference Image 1".image=@bible/fengyi_face.png \
        --set 7.seed=12345 --set 7.steps=8 \
        --batch 3 --out takes/ep01/s03 --tag s03 --log logs/takes.csv

    # or let the segment file from build_prompts.py do the wiring (prompt, frame count, every reference in order):
    python3 comfy_submit.py yz_ref2va.api.json --media prompts/ep01/s03.media.json \
        --batch 3 --out takes/ep01/s03 --tag s03 --log logs/takes.csv

    python3 comfy_submit.py wf.api.json ... --dry-run          # show the batch, spend nothing
    python3 comfy_submit.py wf.api.json ... --confirm 3f9a1c2b7d10   # run only if the batch is still that one

--media replaces whatever references the exported workflow carried: it adds one LoadImage / LoadAudio node per
reference and links them as "ref_images.ref_image_0", "ref_audios.ref_audio_0", ... on the single
MiniMaxH3ReferenceToVideo node (I2VA / FL2VA: first_frame / last_frame on MiniMaxH3ImageToVideo). A Ref2VA
segment that has a first frame gets it as <Picture 1> - a reference the prompt names as the first frame, which is
how ComfyUI's multiframe reference template treats its first picture. With --anchor the script also pins that
picture at frame 0 by adding one MiniMaxH3AddGuide node behind the reference node (the template uses that node
for the keyframes of later shots). Everything else in the workflow - models, LoRA, sampler, resolution - stays as
you exported it; --set still works on top.

Overrides
  --set <node_id>.<input>=<value> / --set-title "<title>".<input>=<value>
    value `@path` reads a text file (prompts) or, for media (image / audio / video inputs or media file
    extensions), uploads the file to ComfyUI's input folder and substitutes the returned name.
    Other values are parsed as JSON when possible (numbers / booleans).
  --batch N queues N runs with seed+i on every node that has a literal `seed` or `noise_seed` input (KSampler-style
  nodes, or RandomNoise / SamplerCustom as in the official H3 templates), each saved under
    <out>/<tag>_<seed>/.

Before anything is queued (skip with --no-preflight; --preflight-only stops after it)
  every node class must exist on the server, every model / LoRA / sampler name must be one the server
  offers (with the closest match when it is not), required inputs must be present, MiniMax H3 frame counts
  must sit on the 17k+5 grid, widths / heights must be multiples of 32, and the H3 reference inputs must be
  the flat keys ComfyUI reads ("ref_images.ref_image_0", ...). Free VRAM is printed.

Re-running the same command is safe
  * every take gets a fingerprint (the final workflow + the content of every uploaded file). A take that
    already finished with the same fingerprint is skipped.
  * the prompt id is written to <take>/handle.json the moment the server accepts the job. If this script
    is interrupted, run the same command again: it looks the job up (/history, then /queue) and collects
    or waits for it instead of submitting a second time. Only a job the server no longer knows is resubmitted.
  * results of an earlier, different run in the same take folder are moved to <take>/_prev_<id>/, not overwritten.

Exit codes: 0 ok; 1 a take failed, produced nothing or timed out; 2 nothing was queued (preflight failed, workflow
rejected, server unreachable, bad input, batch changed since --confirm); 130 interrupted (jobs keep running).
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import mimetypes
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()

MEDIA_INPUTS = {"image", "audio", "video", "image_path", "audio_path", "video_path"}
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".flac", ".mp4", ".mov", ".webm"}


_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _is_local(server: str) -> bool:
    host = (urllib.parse.urlparse(server).hostname or "").lower()
    return host in ("localhost", "::1") or host.startswith(("127.", "10.", "192.168.")) or \
        (host.startswith("172.") and host.split(".")[1].isdigit() and 16 <= int(host.split(".")[1]) <= 31)


def http(server, path, data=None, headers=None, method=None, timeout=120):
    """A ComfyUI on this machine or the LAN is reached directly: a system proxy (common on machines that
    need one for HuggingFace / GitHub) would otherwise swallow requests to 127.0.0.1."""
    req = urllib.request.Request(server + path, data=data, headers=headers or {}, method=method)
    opener = _DIRECT.open if _is_local(server) else urllib.request.urlopen
    with opener(req, timeout=timeout) as r:
        return r.read()


def die(msg: str, code: int = 2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def get_json(server, path, default=None):
    try:
        return json.loads(http(server, path))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, ConnectionError):
        return default


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def upload(server, path: Path) -> str:
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n").encode() + path.read_bytes() + \
           f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n".encode()
    res = json.loads(http(server, "/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}))
    name = res["name"]
    return f"{res['subfolder']}/{name}" if res.get("subfolder") else name


def parse_value(raw: str, input_name: str, server: str, media: dict, do_upload: bool):
    """media collects {substituted name: sha256} for every file that goes to the server."""
    if raw.startswith("@"):
        p = Path(raw[1:])
        if not p.exists():
            die(f"file not found: {p}")
        if input_name in MEDIA_INPUTS or p.suffix.lower() in MEDIA_EXT:
            name = upload(server, p) if do_upload else p.name
            media[name] = sha256_file(p)
            return name
        return p.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def find_by_title(wf: dict, title: str) -> str:
    hits = [k for k, v in wf.items() if v.get("_meta", {}).get("title") == title]
    if len(hits) != 1:
        die(f"title {title!r} matched {len(hits)} nodes: {hits}")
    return hits[0]


def apply_sets(wf, sets, server, media, do_upload, by_title=False):
    for s in sets:
        target, _, raw = s.partition("=")
        node, _, inp = target.rpartition(".")
        node = node.strip('"')
        nid = find_by_title(wf, node) if by_title else node
        if nid not in wf:
            die(f"node {nid} not in workflow")
        wf[nid]["inputs"][inp] = parse_value(raw, inp, server, media, do_upload)


H3_REF, H3_I2V, H3_EMPTY = "MiniMaxH3ReferenceToVideo", "MiniMaxH3ImageToVideo", "EmptyMiniMaxH3LatentAV"
H3_SHIFT = "MiniMaxH3SigmaShift"
H3_GUIDE = "MiniMaxH3AddGuide"
REF_GROUPS = ("ref_images.", "ref_videos.", "ref_video_audios.", "ref_audios.")


def image_size(path: Path) -> tuple[int, int] | None:
    """(width, height) of a PNG / JPEG / WebP read from the file header - no imaging library needed. None if unknown."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(32)
            if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
                return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                kind = head[12:16]
                if kind == b"VP8X":
                    return int.from_bytes(head[24:27], "little") + 1, int.from_bytes(head[27:30], "little") + 1
                if kind == b"VP8 ":
                    return int.from_bytes(head[26:28], "little") & 0x3FFF, int.from_bytes(head[28:30], "little") & 0x3FFF
                if kind == b"VP8L":
                    bits = int.from_bytes(head[21:25], "little")
                    return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
                return None
            if head[:2] == b"\xff\xd8":                                   # JPEG: walk the segments to the frame header
                fh.seek(2)
                while True:
                    byte = fh.read(1)
                    if not byte:
                        return None
                    if byte != b"\xff":
                        continue
                    marker = fh.read(1)
                    while marker == b"\xff":
                        marker = fh.read(1)
                    if not marker:
                        return None
                    m = marker[0]
                    if m in (0x00, 0x01, 0xD8) or 0xD0 <= m <= 0xD7:      # stuffing / standalone markers carry no length
                        continue
                    size = fh.read(2)
                    if len(size) < 2:
                        return None
                    if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):  # a start-of-frame segment
                        data = fh.read(5)
                        return (int.from_bytes(data[3:5], "big"), int.from_bytes(data[1:3], "big")) if len(data) == 5 else None
                    fh.seek(int.from_bytes(size, "big") - 2, 1)
    except OSError:
        return None
    return None


def frame_fit(role: str, path: Path, canvas: dict) -> str | None:
    """A first frame is stretched to the canvas (the node does not crop it); a last frame is cover-cropped.
    Say so when the picture's shape differs from the canvas enough to be seen."""
    size, w, h = image_size(path), canvas.get("width"), canvas.get("height")
    if not size or not isinstance(w, int) or not isinstance(h, int) or not size[1] or not h:
        return None
    img, can = size[0] / size[1], w / h
    if abs(img / can - 1) <= 0.01:
        return None
    shapes = f"advice: {path.name} is {size[0]}x{size[1]} ({img:.3f}:1) and the canvas is {w}x{h} ({can:.3f}:1): "
    if role == "first_frame":
        factor = can / img
        change = f"{(factor - 1) * 100:.1f}% wider" if factor > 1 else f"{(1 - factor) * 100:.1f}% narrower"
        return (shapes + f"the node stretches a first frame to the canvas without cropping, so everything in it becomes {change} "
                         f"- make the first frame at the canvas ratio")
    what = "a last frame" if role == "last_frame" else "a pinned frame"
    return shapes + f"the node crops {what} to the canvas from the centre, {(1 - min(img, can) / max(img, can)) * 100:.1f}% of it is cut away"


def apply_media(wf: dict, media_json: Path, server: str, media: dict, do_upload: bool, node_id: str | None,
                anchor: bool = False) -> list[str]:
    """Put a segment into the workflow exactly as build_prompts.py numbered it: prompt text, frame count, and one
    Load node per reference wired to ref_images.ref_image_0.. / ref_audios.ref_audio_0.. (Ref2VA) or to
    first_frame / last_frame (I2VA / FL2VA). Whatever references the workflow carried before are replaced.
    A Ref2VA segment's frame pictures (its first frame, the keyframes of later shots) are references the prompt
    names as those frames; with `anchor` each is also pinned on the timeline by a MiniMaxH3AddGuide node, chained
    between the reference node and whatever read its conditioning. Returns the lines of the wiring table."""
    spec = json.loads(media_json.read_text(encoding="utf-8"))
    mode = spec.get("mode", "ref2va")
    want = H3_REF if mode == "ref2va" else H3_I2V
    hits = [k for k, v in wf.items() if v.get("class_type") == want]
    if node_id:
        if node_id not in wf:
            die(f"--h3-node {node_id} is not in the workflow")
        hits = [node_id]
    if len(hits) != 1:
        die(f"--media: the segment is {mode}, which needs exactly one {want} node in the workflow; found {len(hits)}"
            + (f" ({', '.join(hits)}) - pick one with --h3-node" if hits else " - export a workflow built on that node"))
    nid = hits[0]
    inputs = wf[nid]["inputs"]
    prompt_file = media_json.parent / spec.get("prompt_file", f"{spec['segment']}.txt")
    if not prompt_file.exists():
        die(f"--media: prompt file not found: {prompt_file}")
    inputs["prompt"] = prompt_file.read_text(encoding="utf-8")
    frames = spec.get("frames")
    lines = [f"segment {spec['segment']} ({mode}) -> node {nid} ({want}); prompt {prompt_file.name}, {len(inputs['prompt'].split())} words"]
    if frames:
        inputs["length"] = int(frames)
        for k, v in wf.items():
            if v.get("class_type") == H3_EMPTY and not isinstance(v["inputs"].get("length"), list):
                v["inputs"]["length"] = int(frames)
        lines.append(f"length = {frames} frames ({frames / 24:.3f} s)")
    for key in [k for k in inputs if k.startswith(REF_GROUPS) or k in ("ref_images", "ref_videos", "ref_video_audios", "ref_audios")]:
        del inputs[key]
    if want == H3_I2V:                                  # frames the exported workflow carried: this segment brings its own or none
        for key in ("first_frame", "last_frame"):
            inputs.pop(key, None)
    next_id = max([int(k) for k in wf if str(k).isdigit()] + [0]) + 1000        # ids well clear of the exported ones

    def load_node(kind: str, path: Path, title: str) -> str:
        nonlocal next_id
        if not path.exists():
            die(f"--media: reference file not found: {path}")
        name = upload(server, path) if do_upload else path.name
        media[name] = sha256_file(path)
        new = str(next_id)
        next_id += 1
        wf[new] = {"class_type": "LoadImage" if kind == "image" else "LoadAudio",
                   "inputs": {"image" if kind == "image" else "audio": name}, "_meta": {"title": title}}
        return new

    n_img = n_aud = 0
    guides = [k for k, v in wf.items() if v.get("class_type") == H3_GUIDE]        # guide nodes the export already carried
    anchors: list[dict] = []                                                      # frame pictures of this segment
    for item in spec.get("media", []):
        path = Path(item["path"])
        if item["type"] == "image" and item.get("role") in ("first_frame", "last_frame"):
            new = load_node("image", path, item["role"])
            inputs[item["role"]] = [new, 0]
            lines.append(f"{item['role']:12s} <- {path.name}")
            fit = frame_fit(item["role"], path, literals(wf, inputs)) if want == H3_I2V else None
            if fit:
                lines.append(fit)
        elif item["type"] == "image":
            if mode != "ref2va":
                die(f"--media: a reference image in a {mode} segment has nowhere to go ({path.name})")
            new = load_node("image", path, f"Picture {n_img + 1}")
            inputs[f"ref_images.ref_image_{n_img}"] = [new, 0]
            n_img += 1
            mark = item.get("anchor")                    # "first_frame", or {"shot": n, "frame": f} for a later shot's keyframe
            if not mark:
                lines.append(f"<Picture {n_img}>  <- {path.name}")
                continue
            frame = 0 if mark == "first_frame" else int(mark.get("frame", 0))
            what = "the first frame" if mark == "first_frame" else f"keyframe of shot {mark.get('shot', '?')}"
            anchors.append({"picture": n_img, "load": new, "frame": frame, "what": what, "path": path, "line": len(lines)})
            lines.append(f"<Picture {n_img}>  <- {path.name}   ({what}: a reference the prompt names as that frame)")
        elif item["type"] == "audio":
            new = load_node("audio", path, f"Audio {n_aud + 1}")
            inputs[f"ref_audios.ref_audio_{n_aud}"] = [new, 0]
            n_aud += 1
            lines.append(f"<Audio {n_aud}>    <- {path.name}")
    # --anchor: pin every frame picture where it belongs on the timeline - one MiniMaxH3AddGuide per picture, chained
    # behind the reference node as ComfyUI's multiframe reference template chains them for its keyframes
    if anchors and anchor and not guides:
        total = inputs.get("length") if isinstance(inputs.get("length"), int) else None
        if not isinstance(inputs.get("vae"), list):
            lines.append("advice: --anchor cannot pin the frame pictures: the H3 reference node has no `vae` input - connect the video VAE")
        else:
            prev = [nid, 0]
            guide_ids = []
            for a in anchors:
                if total is not None and a["frame"] >= total:
                    lines.append(f"advice: {a['what']} would be pinned at frame {a['frame']}, past the end of the {total}-frame take - left as a reference only")
                    continue
                guide = str(next_id)
                next_id += 1
                wf[guide] = {"class_type": H3_GUIDE, "_meta": {"title": f"{a['what']} anchor"},
                             "inputs": {"positive": prev, "vae": inputs["vae"], "latent": [nid, 1], "image": [a["load"], 0], "frame_idx": a["frame"]}}
                prev = [guide, 0]
                guide_ids.append(guide)
                lines[a["line"]] = (f"<Picture {a['picture']}>  <- {a['path'].name}   ({a['what']}: also pinned at frame {a['frame']} - "
                                    f"{H3_GUIDE} [{guide}] added)")
                fit = frame_fit("anchor", a["path"], literals(wf, inputs))
                if fit:
                    lines.append(fit)
            if guide_ids:
                for k, other in wf.items():              # whatever read the reference node's conditioning now reads the last guide's
                    if k in guide_ids:
                        continue
                    for name, val in other.get("inputs", {}).items():
                        if isinstance(val, list) and len(val) == 2 and str(val[0]) == nid and val[1] == 0:
                            other["inputs"][name] = prev
    elif anchors and not anchor:
        lines.append("--anchor would also pin " + ("these pictures" if len(anchors) > 1 else "this picture")
                     + " on the timeline (" + ", ".join(f"<Picture {a['picture']}> at frame {a['frame']}" for a in anchors) + ")")
    if guides and want == H3_REF:
        ids = ", ".join(guides)
        lines.append(f"advice: the exported workflow already has {H3_GUIDE} node(s) [{ids}]; they are left as exported, so whatever "
                     "picture they load is pinned into this take"
                     + (" and --anchor adds nothing for this segment" if anchors and anchor else "")
                     + " - export the draft workflow without guide nodes")
    return lines


def literal(wf: dict, value, depth: int = 0):
    """A value as the server will see it, where that can be told without running the graph: a literal stays as it
    is; a link to a Primitive* node (the official templates feed width, steps, prompt ... through those) yields
    that node's `value`. Anything computed inside the graph (switches, math, selectors) -> None."""
    if not isinstance(value, (list, dict)):
        return value
    if isinstance(value, list) and len(value) == 2 and depth < 4:
        node = wf.get(str(value[0]))
        if node and str(node.get("class_type", "")).startswith("Primitive"):
            return literal(wf, node.get("inputs", {}).get("value"), depth + 1)
    return None


def upstream(wf: dict, link) -> set[str]:
    """Ids of every node a link depends on (the node it comes from, and everything wired into that node)."""
    seen: set[str] = set()
    todo = [link]
    while todo:
        cur = todo.pop()
        if not (isinstance(cur, list) and len(cur) == 2 and str(cur[0]) in wf) or str(cur[0]) in seen:
            continue
        seen.add(str(cur[0]))
        todo.extend(v for v in wf[str(cur[0])].get("inputs", {}).values() if isinstance(v, list))
    return seen


def literals(wf: dict, inputs: dict) -> dict:
    out = {}
    for name, value in inputs.items():
        got = literal(wf, value)
        if got is not None:
            out[name] = got
    return out


def settings_summary(wf: dict) -> list[str]:
    """What this workflow will actually run with - for the batch preview."""
    out = []
    for k, v in wf.items():
        cls, inp = v.get("class_type", ""), v.get("inputs", {})
        lit = literals(wf, inp)
        if cls in (H3_REF, H3_I2V, H3_EMPTY) and not {"width", "height"} <= set(lit):
            refs = sum(1 for n in inp if n.startswith("ref_images.")), sum(1 for n in inp if n.startswith("ref_audios."))
            out.append(f"{cls} [{k}]: canvas is computed inside the workflow (not readable here), {lit.get('length', '?')} frames"
                       + (f", {refs[0]} reference image(s), {refs[1]} audio" if cls == H3_REF else ""))
        elif cls in (H3_REF, H3_I2V, H3_EMPTY) and "width" in lit:
            secs = f" = {lit['length'] / 24:.2f}s" if isinstance(lit.get("length"), int) else ""
            refs = sum(1 for n in inp if n.startswith("ref_images.")), sum(1 for n in inp if n.startswith("ref_audios."))
            extra = f", {refs[0]} reference image(s), {refs[1]} audio" if cls == H3_REF else ""
            out.append(f"{cls} [{k}]: {lit.get('width')}x{lit.get('height')}, {lit.get('length')} frames{secs}"
                       + (f", ref_image_size {lit['ref_image_size']}" if "ref_image_size" in lit else "") + extra)
        elif "steps" in lit and ("cfg" in lit or "sampler_name" in lit):
            out.append(f"{cls} [{k}]: {lit.get('steps')} steps, cfg {lit.get('cfg')}, {lit.get('sampler_name', '?')} / {lit.get('scheduler', '?')}")
        elif cls == "BasicScheduler" and "steps" not in lit:
            out.append(f"{cls} [{k}]: steps are computed inside the workflow (a switch or a formula) - check them in the ComfyUI window")
        elif "steps" in lit and "scheduler" in lit:                       # BasicScheduler of the SamplerCustomAdvanced chain
            out.append(f"{cls} [{k}]: {lit['steps']} steps, scheduler {lit['scheduler']}"
                       + (f", denoise {lit['denoise']}" if lit.get("denoise") not in (None, 1, 1.0) else ""))
        elif cls == "KSamplerSelect" and "sampler_name" in lit:
            out.append(f"{cls} [{k}]: sampler {lit['sampler_name']}")
        elif cls in ("CFGGuider", "DualCFGGuider") and "cfg" in lit:
            out.append(f"{cls} [{k}]: cfg {lit['cfg']}")
        elif "lora_name" in lit:
            out.append(f"{cls} [{k}]: {lit['lora_name']} @ {lit.get('strength_model', lit.get('strength', '?'))}")
        elif "unet_name" in lit:
            out.append(f"{cls} [{k}]: {lit['unet_name']}")
        elif "shift_video" in lit:
            out.append(f"{cls} [{k}]: shift video {lit['shift_video']} / audio {lit.get('shift_audio')}")
        elif cls == H3_GUIDE:
            out.append(f"{cls} [{k}]: pins " + ("a picture" if isinstance(inp.get("image"), list) else "audio only")
                       + f" at frame {lit.get('frame_idx', '?')}")
    return out


def job_size(wf: dict) -> tuple[int, int]:
    """(frames, pixels per frame) of the H3 job in this workflow, (0, 0) when it cannot be read."""
    for v in wf.values():
        inp = literals(wf, v.get("inputs", {}))
        if v.get("class_type") in (H3_REF, H3_I2V, H3_EMPTY) and all(isinstance(inp.get(k), int) for k in ("width", "height", "length")):
            return inp["length"], inp["width"] * inp["height"]
    return 0, 0


RATIOS = {"21:9": 21 / 9, "16:9": 16 / 9, "4:3": 4 / 3, "1:1": 1.0, "3:4": 3 / 4, "9:16": 9 / 16}


# Video flow shift each lightx2v Turbo file is run at by its authors: the spec table of ModelTC/Minimax-H3-Turbo and the
# configs of ModelTC/LightX2V (read 2026-11-22). Files that are not listed there have no published value -> no advice.
TURBO_SHIFT = {("fl2v", 4, "1.0", True): 6.0, ("fl2v", 8, "1.0", True): 6.0, ("fl2v", 8, "1.2", True): 12.0,
               ("fl2v", 4, "0.1", False): 12.0, ("fl2v", 8, "1.0", False): 12.0, ("ref2v", 4, "0.1", False): 12.0}


def turbo_shift(lora_name: str) -> float | None:
    m = re.search(r"minimax_h3_(fl2v|ref2v)_turbo_(\d+)step_v(\d+\.\d+)(_768p)?", lora_name.lower())
    return TURBO_SHIFT.get((m.group(1), int(m.group(2)), m.group(3), bool(m.group(4)))) if m else None


def advice(wf: dict, ratio: str | None) -> list[str]:
    """Things the server cannot object to but that usually mean a mistake. Printed with the preview; never blocks."""
    out, steps, cfg, loras = [], None, None, []
    for v in wf.values():
        cls, raw = v.get("class_type", ""), v.get("inputs", {})
        inp = {**raw, **literals(wf, raw)}                      # links to Primitive* nodes read as their values
        if isinstance(inp.get("steps"), int) and ("cfg" in inp or "sampler_name" in inp):
            steps, cfg = inp["steps"], inp.get("cfg")
        elif isinstance(inp.get("steps"), int) and "scheduler" in inp and steps is None:      # BasicScheduler
            steps = inp["steps"]
        if cls in ("CFGGuider", "DualCFGGuider") and isinstance(inp.get("cfg"), (int, float)):
            cfg = inp["cfg"]
        if isinstance(inp.get("lora_name"), str):
            loras.append(inp["lora_name"])
        if cls == H3_REF:
            n_img = sum(1 for n in inp if n.startswith("ref_images."))
            n_aud = sum(1 for n in inp if n.startswith("ref_audios."))
            if n_img and not isinstance(inp.get("vae"), list):
                out.append("the H3 reference node has no `vae` input: reference pictures are then read by the text encoder only "
                           "and identity holds less well - connect the video VAE")
            if n_aud and not isinstance(inp.get("audio_vae"), list):
                out.append("voice references are wired but the H3 reference node has no `audio_vae` input: the samples are then "
                           "not heard by the model at all (only their labels reach the text encoder) - connect the audio VAE")
        if cls in (H3_REF, H3_I2V, H3_EMPTY) and ratio in RATIOS and isinstance(inp.get("width"), int) and isinstance(inp.get("height"), int):
            w, h = inp["width"], inp["height"]
            got = w / h
            if abs(got / RATIOS[ratio] - 1) > 0.005:
                if got < RATIOS[ratio]:                          # taller than the episode: rows come off
                    keep = int(round(w / RATIOS[ratio] / 2)) * 2
                    how = f"crop {(h - keep) // 2} px top and bottom to {w}x{keep}, then scale"
                else:                                            # wider: columns come off
                    keep = int(round(h * RATIOS[ratio] / 2)) * 2
                    how = f"crop {(w - keep) // 2} px left and right to {keep}x{h}, then scale"
                out.append(f"the canvas {w}x{h} is {got:.3f}:1, the episode is {ratio} ({RATIOS[ratio]:.3f}:1): "
                           f"bring it to {ratio} in the edit ({how}); mix_episode.py does this for the delivery size")
    distilled = [x for x in loras if any(t in x.lower() for t in ("turbo", "pdd", "lightx2v", "distill", "step"))]
    # flow shift: the model's own default is video 12 / audio 3; MiniMaxH3SigmaShift changes it for whatever is wired after it
    shift_nodes = {k: literals(wf, v.get("inputs", {})) for k, v in wf.items() if v.get("class_type") == H3_SHIFT}
    shift = next((x.get("shift_video") for x in shift_nodes.values() if isinstance(x.get("shift_video"), (int, float))),
                 None if shift_nodes else 12.0)                                   # None: set by something the preview cannot read
    if shift is not None and abs(shift - 12.0) > 1e-6:
        for k, v in wf.items():
            if v.get("class_type") == "BasicScheduler" and not set(shift_nodes) & upstream(wf, v.get("inputs", {}).get("model")):
                out.append(f"BasicScheduler [{k}] takes its model from before {H3_SHIFT}: the step schedule is then built with the "
                           f"default video shift 12 while the model is told {shift:g} - feed the scheduler from the shift node's output too")
    for name in distilled:
        want = turbo_shift(name)
        if want is not None and shift is not None and abs(shift - want) > 1e-6:
            fix = (f"set {H3_SHIFT} to 6 / 3 and wire the guider and the scheduler after it" if want == 6.0
                   else f"leave the shift at the model default (no {H3_SHIFT} node, or 12 / 3)")
            out.append(f"{name}: its authors run this file at video shift {want:g} / audio 3; this workflow runs video shift {shift:g}"
                       + ("" if shift_nodes else " (the model default - there is no shift node)") + f" - {fix}")
    canvas = next((literals(wf, v.get("inputs", {})) for v in wf.values() if v.get("class_type") in (H3_REF, H3_I2V, H3_EMPTY)), {})
    px = canvas.get("width", 0) * canvas.get("height", 0) if isinstance(canvas.get("width"), int) and isinstance(canvas.get("height"), int) else 0
    for name in distilled:
        low = name.lower()
        if "minimax_h3" in low and "turbo" in low:
            if px >= 1344 * 768 * 0.9 and "768p" not in low:
                out.append(f"{name} is the 544p-tier Turbo LoRA and the canvas is {canvas['width']}x{canvas['height']}: at 768p use the "
                           f"file with `_768p_` in its name (slower and softer otherwise)")
            want = 4 if "4step" in low else 8 if "8step" in low else None
            if want and steps is not None and steps != want:
                out.append(f"{name} is a {want}-step LoRA but the workflow runs {steps} steps")
    if steps is not None and steps <= 10 and not distilled:
        out.append(f"{steps} steps and no distillation LoRA in the workflow: the base model wants about 20 steps - "
                   f"is the Turbo LoRA missing?")
    if steps is not None and steps >= 16 and distilled:
        out.append(f"{steps} steps with {distilled[0]} loaded: a refinement pass runs without the Turbo LoRA")
    if isinstance(cfg, (int, float)) and abs(cfg - 1.0) > 1e-6:
        out.append(f"cfg {cfg}: the open weights are CFG-distilled, keep cfg at 1.0")
    return out


LOG_HEADER = ["time", "tag", "seed", "status", "seconds", "workflow", "fingerprint", "output", "overrides", "score", "frames", "pixels", "settings"]


def log_take(path: Path, row: dict) -> None:
    """Append one row; a log written by an older version of this script gets the new columns added."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    if path.exists():
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
    rows.append(row)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_HEADER, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in LOG_HEADER})


def estimate(history: list[tuple[float, int, int]], frames: int, pixels: int, n: int, where: str) -> str:
    """history: (seconds, frames, pixels) of finished takes. Scaled to this job's size when the sizes are known."""
    scaled = [sec / (f * px) * frames * pixels for sec, f, px in history if f and px and frames and pixels]
    if scaled:
        per = statistics.median(scaled)
        note = f"median of {len(scaled)} finished take(s) {where}, scaled to this job's frame count and canvas"
    else:
        per = statistics.median(sec for sec, _f, _px in history)
        note = f"median of {len(history)} finished take(s) {where}; frame count or canvas is not known for both, so this is not scaled"
    return f"about {per * n / 60:.1f} min at {per:.0f}s per take ({note})"


SEED_KEYS = ("seed", "noise_seed")      # KSampler-style nodes / RandomNoise and SamplerCustom (the official H3 templates use the latter)


def seed_nodes(wf) -> list[tuple[str, str]]:
    """(node id, input name) of every literal seed in the workflow."""
    return [(k, key) for k, v in wf.items() for key in SEED_KEYS
            if key in v.get("inputs", {}) and not isinstance(v["inputs"][key], (list, dict))]


def fingerprint(wf: dict, media: dict) -> str:
    blob = json.dumps(wf, sort_keys=True, ensure_ascii=False) + "|" + json.dumps(sorted(media.items()))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---- preflight -----------------------------------------------------------------------------------------
def combo_choices(spec):
    """Choices of a combo input in either object_info dialect; None when the input is not a combo."""
    if not isinstance(spec, (list, tuple)) or not spec:
        return None
    if isinstance(spec[0], list):
        return spec[0]
    if spec[0] == "COMBO" and len(spec) > 1 and isinstance(spec[1], dict):
        return spec[1].get("options")
    return None


def preflight(server: str, wf: dict, media: dict) -> list[str]:
    info = get_json(server, "/object_info")
    if not isinstance(info, dict) or not info:
        return [f"could not read {server}/object_info - is ComfyUI running?"]
    errors = []
    for nid, node in wf.items():
        cls = node.get("class_type")
        title = node.get("_meta", {}).get("title") or cls
        where = f"node {nid} ({title})"
        if cls not in info:
            near = difflib.get_close_matches(cls or "", list(info), n=1)
            errors.append(f"{where}: node class {cls!r} is not installed on this ComfyUI"
                          + (f" (closest: {near[0]})" if near else "") + " - install the custom node pack or upgrade ComfyUI")
            continue
        spec = info[cls].get("input", {})
        req, opt = spec.get("required", {}) or {}, spec.get("optional", {}) or {}
        inputs = node.get("inputs", {})
        for name in req:
            if name not in inputs:
                errors.append(f"{where}: required input {name!r} is missing")
        for name, val in inputs.items():
            if isinstance(val, (list, dict)):             # a link to another node, or a group of links
                continue
            choices = combo_choices(req.get(name) or opt.get(name))
            if choices and isinstance(val, str) and val not in choices and val not in media:   # empty list = filled at run time
                near = difflib.get_close_matches(val, [str(c) for c in choices], n=1, cutoff=0.4)
                errors.append(f"{where}: {name} = {val!r} is not offered by the server"
                              + (f" (closest: {near[0]!r})" if near else f" ({len(choices)} choice(s) available)"))
        if cls and "MiniMaxH3" in cls:
            for group, prefix in (("ref_images", "ref_image_"), ("ref_videos", "ref_video_"),
                                  ("ref_video_audios", "ref_video_audio_"), ("ref_audios", "ref_audio_")):
                if group in inputs:                       # ComfyUI reads "ref_images.ref_image_0", never a list or an object
                    errors.append(f"{where}: `{group}` is written as a {'list' if isinstance(inputs[group], list) else 'nested object'} - "
                                  f"ComfyUI only reads flat keys \"{group}.{prefix}0\", \"{group}.{prefix}1\", ... (each a link "
                                  f"[\"<node id>\", 0]); other shapes are silently dropped and the references never reach the model")
                keys = sorted((k for k in inputs if k.startswith(group + ".")), key=lambda k: k)
                idx = []
                for k in keys:
                    tail = k[len(group) + 1:]
                    if not (tail.startswith(prefix) and tail[len(prefix):].isdigit()):
                        errors.append(f"{where}: unexpected key {k!r} (expected {group}.{prefix}<number from 0>)")
                    else:
                        idx.append(int(tail[len(prefix):]))
                if idx and sorted(idx) != list(range(len(idx))):
                    errors.append(f"{where}: {group} keys must be numbered 0..{len(idx) - 1} without gaps (found {sorted(idx)}) - "
                                  f"the order is the <Picture N> / <Audio N> numbering")
            text = inputs.get("prompt")
            if cls == H3_REF and isinstance(text, str):      # does the prompt talk about references that are not wired?
                import re as _re
                for label, group in (("Picture", "ref_images."), ("Audio", "ref_audios."), ("Video", "ref_videos.")):
                    used = [int(x) for x in _re.findall(rf"<{label} (\d+)>", text)]
                    wired = sum(1 for k in inputs if k.startswith(group))
                    if used and max(used) > wired:
                        errors.append(f"{where}: the prompt refers to <{label} {max(used)}> but {wired} reference "
                                      f"{label.lower()}(s) are wired to this node - without them the model invents the look "
                                      f"(use --media <segment>.media.json to wire them in prompt order)")
                    elif wired and not used:
                        errors.append(f"{where}: {wired} reference {label.lower()}(s) are wired but the prompt never mentions <{label} N>")
            n = inputs.get("length")
            if isinstance(n, int) and (n - 5) % 17 != 0:
                k = round((n - 5) / 17)
                errors.append(f"{where}: length {n} is not on the 17k+5 frame grid (nearest {17 * k + 5} or {17 * (k + 1) + 5})")
            for dim in ("width", "height"):
                v = inputs.get(dim)
                if isinstance(v, int) and v % 32 != 0:
                    errors.append(f"{where}: {dim} {v} is not a multiple of 32")
    return errors


def print_system(server: str) -> str | None:
    st = get_json(server, "/system_stats")
    if not isinstance(st, dict):
        return None
    ver = st.get("system", {}).get("comfyui_version")
    devs = ", ".join(f"{d.get('name', '?')}: {d.get('vram_free', 0) / 2**30:.1f} / {d.get('vram_total', 0) / 2**30:.1f} GB free"
                     for d in st.get("devices", []))
    print(f"ComfyUI {ver or '?'} @ {server}  {devs}")
    return ver


# ---- queue / wait / collect ------------------------------------------------------------------------------
def queue(server, wf, client_id):
    try:
        res = json.loads(http(server, "/prompt", json.dumps({"prompt": wf, "client_id": client_id}).encode(),
                              {"Content-Type": "application/json"}))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            d = json.loads(body)
            msg = d.get("error", {}).get("message") or body[:400]
            for nid, ne in (d.get("node_errors") or {}).items():
                for err in ne.get("errors", []):
                    msg += f"\n  node {nid} ({ne.get('class_type')}): {err.get('message')} {err.get('details', '')}"
        except json.JSONDecodeError:
            msg = body[:800]
        die(f"ComfyUI rejected the workflow (HTTP {e.code}): {msg}")
    if "error" in res:
        die(f"queue rejected: {json.dumps(res, ensure_ascii=False)[:2000]}")
    return res["prompt_id"]


def lookup(server, pid) -> tuple[str, dict | None]:
    """-> ("done", history entry) | ("queued", None) | ("lost", None) | ("unreachable", None)"""
    hist = get_json(server, f"/history/{pid}")
    if hist is None:
        return "unreachable", None
    if pid in hist:
        return "done", hist[pid]
    q = get_json(server, "/queue")
    if q is None:
        return "unreachable", None
    for item in (q.get("queue_running") or []) + (q.get("queue_pending") or []):
        if len(item) > 1 and item[1] == pid:
            return "queued", None
    return "lost", None


def lookup_stable(server, pid) -> tuple[str, dict | None]:
    """A job is 'lost' only when three look-ups in a row find it in neither /history nor /queue: there is a
    short gap between a job leaving the queue and its history entry appearing."""
    state, entry = lookup(server, pid)
    for _ in range(2):
        if state != "lost":
            break
        time.sleep(2)
        state, entry = lookup(server, pid)
    return state, entry


def wait(server, pid, poll, timeout):
    t0 = time.time()
    misses = 0
    while time.time() - t0 < timeout:
        state, entry = lookup(server, pid)
        if state == "done":
            return entry
        if state == "lost":
            misses += 1                                   # between "leaves the queue" and "enters history" there is a gap
            if misses >= 3:
                die(f"the server no longer knows job {pid} (restarted?) - run the same command again to resubmit", 1)
        else:
            misses = 0
        time.sleep(poll if state != "lost" else min(poll, 3))
    die(f"timed out after {timeout:.0f}s waiting for {pid}; the job may still be running - "
        f"run the same command again to collect it", 1)


def download(server, entry, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    for node_out in entry.get("outputs", {}).values():
        for key in ("videos", "gifs", "images", "audio"):
            for f in node_out.get(key, []):
                if f.get("type") != "output":
                    continue
                q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": "output"})
                data = http(server, f"/view?{q}", timeout=600)
                dest = out / f["filename"]
                dest.write_bytes(data)
                saved.append(dest)
    return saved


def take_state(dest: Path, fp: str) -> str:
    """done | resume | new"""
    run_json, handle = dest / "run.json", dest / "handle.json"
    if run_json.exists():
        try:
            run = json.loads(run_json.read_text(encoding="utf-8"))
            if run.get("fingerprint") == fp and run.get("status") == "success" and run.get("files") \
                    and all(Path(f).exists() for f in run["files"]):
                return "done"
        except json.JSONDecodeError:
            pass
        return "new"
    if handle.exists():
        try:
            if json.loads(handle.read_text(encoding="utf-8")).get("fingerprint") == fp:
                return "resume"
        except json.JSONDecodeError:
            pass
    return "new"


def holds_earlier_run(dest: Path) -> bool:
    """True when the take folder already has files that a new, different run would push aside."""
    try:
        return dest.is_dir() and any(not p.name.startswith("_prev_") for p in dest.iterdir())
    except OSError:
        return False


def archive_previous(dest: Path) -> None:
    """Keep what an earlier, different run left in this take folder."""
    old = [p for p in dest.iterdir() if not p.name.startswith("_prev_")] if dest.exists() else []
    if not old:
        return
    tag = "unknown"
    for name in ("run.json", "handle.json"):
        try:
            tag = json.loads((dest / name).read_text(encoding="utf-8")).get("fingerprint", tag)[:8]
            break
        except (OSError, json.JSONDecodeError):
            continue
    keep = dest / f"_prev_{tag}"
    n = 1
    while keep.exists():
        n += 1
        keep = dest / f"_prev_{tag}_{n}"
    keep.mkdir(parents=True)
    for p in old:
        p.rename(keep / p.name)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__[__doc__.index("    # 1) export"):])
    ap.add_argument("workflow", help="API-format workflow JSON")
    ap.add_argument("--media", help="<segment>.media.json from build_prompts.py: sets the prompt and the frame count on the H3 node and "
                                    "wires every reference in the order that numbered <Picture N> / <Audio N>")
    ap.add_argument("--h3-node", help="node id of the H3 conditioning node when the workflow has more than one")
    ap.add_argument("--write-workflow", metavar="PATH",
                    help="also write the workflow exactly as it will be queued (after --media / --set, before the seed is set) "
                         "to this file - to see the wiring the script made, or to open it in ComfyUI")
    ap.add_argument("--anchor", action="store_true",
                    help="Ref2VA segments with frame pictures (a first frame, keyframes of later shots): besides wiring them as "
                         "<Picture N>, pin each on the timeline with a MiniMaxH3AddGuide node - the first frame at frame 0 (an exact "
                         "opening, e.g. when continuing from the previous take's last frame), a keyframe at its shot's cut. "
                         "Default: references only")
    ap.add_argument("--server", default="http://127.0.0.1:8188")
    ap.add_argument("--set", action="append", default=[], help="node_id.input=value (value may be @file)")
    ap.add_argument("--set-title", action="append", default=[], help='"Node title".input=value')
    ap.add_argument("--batch", type=int, default=1, help="number of seeds to queue (抽卡)")
    ap.add_argument("--seed", type=int, help="first seed; default keeps the workflow's seed")
    ap.add_argument("--out", help="folder for the takes; default with --media: takes/<name of the prompts folder>/<segment>")
    ap.add_argument("--tag", help="prefix of each take's folder; default: the segment id with --media, else `take`")
    ap.add_argument("--poll", type=float, default=20.0,
                    help="seconds between status polls (polling mid-sample stalls the sampler 18-43 s, keep >= 20)")
    ap.add_argument("--timeout", type=float, default=7200.0, help="seconds to wait for one take")
    ap.add_argument("--free-every", type=int, default=0, help="POST /free (unload models, free memory) after every N runs; 0 = never")
    ap.add_argument("--no-preflight", action="store_true")
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the batch (what is new / resumable / already done) and stop")
    ap.add_argument("--confirm", help="run only if the batch id printed by --dry-run is still this one")
    ap.add_argument("--force", action="store_true", help="run takes again even when an identical finished take exists")
    ap.add_argument("--log", help="append one row per take to this CSV (e.g. logs/takes.csv)")
    a = ap.parse_args()

    wf = json.loads(Path(a.workflow).read_text(encoding="utf-8"))
    if "nodes" in wf and "links" in wf:
        die("this is a UI workflow; export with 'Export (API)' instead")
    offline = a.dry_run
    media: dict[str, str] = {}
    wiring: list[str] = []
    ratio = None
    if a.media:
        try:
            meta_in = json.loads(Path(a.media).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            die(f"cannot read {a.media}: {e}")
        ratio = meta_in.get("ratio")
        if not a.out:
            a.out = str(Path("takes") / Path(a.media).resolve().parent.name / str(meta_in.get("segment", "segment")))
        a.tag = a.tag or str(meta_in.get("segment", "take"))
    if not a.out:
        die("--out is required when there is no --media to derive it from")
    a.tag = a.tag or "take"
    try:
        if a.media:
            wiring = apply_media(wf, Path(a.media), a.server, media, do_upload=not offline, node_id=a.h3_node, anchor=a.anchor)
        apply_sets(wf, a.set, a.server, media, do_upload=not offline)
        apply_sets(wf, a.set_title, a.server, media, do_upload=not offline, by_title=True)
    except urllib.error.URLError as e:
        die(f"cannot reach ComfyUI at {a.server}: {e.reason}")
    if a.write_workflow:
        Path(a.write_workflow).parent.mkdir(parents=True, exist_ok=True)
        Path(a.write_workflow).write_text(json.dumps(wf, ensure_ascii=False, indent=1), encoding="utf-8")
    snodes = seed_nodes(wf)
    if (a.batch > 1 or a.seed is not None) and not snodes:
        die("--batch / --seed need a node with a literal `seed` or `noise_seed` input (KSampler, RandomNoise, SamplerCustom ...); "
            "this workflow has none - if the seed comes from a primitive or another node, set it on that node with --set")
    base_seed = a.seed if a.seed is not None else (wf[snodes[0][0]]["inputs"][snodes[0][1]] if snodes else 0)

    version = print_system(a.server)
    if version is None and not offline:
        die(f"cannot reach ComfyUI at {a.server}")
    if not a.no_preflight and version is not None:
        problems = preflight(a.server, wf, media)
        if problems:
            print("PREFLIGHT FAILED - nothing was queued:\n  " + "\n  ".join(problems)
                  + "\n(the check compares the workflow with what this server reports; if you are sure the workflow is "
                    "right, re-run with --no-preflight)", file=sys.stderr)
            sys.exit(2)
        print(f"preflight ok: {len(wf)} node(s)")
    if a.preflight_only:
        return

    out = Path(a.out)
    plan = []
    for i in range(a.batch):
        seed = base_seed + i
        for n, key in snodes:
            wf[n]["inputs"][key] = seed
        fp = fingerprint(wf, media)
        dest = out / f"{a.tag}_{seed}"
        state = "new" if a.force else take_state(dest, fp)
        plan.append({"seed": seed, "fp": fp, "dest": dest, "state": state})
    batch_id = hashlib.sha256("|".join(p["fp"] for p in plan).encode()).hexdigest()[:12]
    frames, pixels = job_size(wf)
    past = []
    for rj in out.glob("*/run.json"):
        try:
            r = json.loads(rj.read_text(encoding="utf-8"))
            if r.get("status") == "success" and r.get("seconds"):
                past.append((float(r["seconds"]), int(r.get("frames") or 0), int(r.get("pixels") or 0)))
        except (OSError, json.JSONDecodeError, ValueError):
            pass
    todo = [p for p in plan if p["state"] != "done"]
    where = "in this folder"
    if not past and todo and a.log and Path(a.log).exists():               # no history here: look in the takes log
        try:
            with open(a.log, newline="", encoding="utf-8-sig") as fh:
                past = [(float(r["seconds"]), int(r.get("frames") or 0), int(r.get("pixels") or 0)) for r in csv.DictReader(fh)
                        if r.get("workflow") == Path(a.workflow).name and r.get("status") == "success" and r.get("seconds")]
            where = f"of this workflow in {a.log}"
        except (OSError, ValueError, KeyError):
            past = []
    if not todo:
        est = "nothing to do"
    elif past:
        est = estimate(past, frames, pixels, len(todo), where)
    else:
        est = "no finished take to estimate the time from yet"
    for line in wiring:
        print("  " + line)
    for line in settings_summary(wf):
        print("  " + line)
    for line in advice(wf, ratio):
        print("  advice: " + line)
    print(f"  output folder: {out}")
    print(f"batch {batch_id}: {len(plan)} take(s) -> {len(todo)} to run; {est}")
    for p in plan:
        note = {"done": "already finished with identical inputs - skipped", "resume": "was queued before - will be collected, not resubmitted",
                "new": "will be queued"}[p["state"]]
        if p["state"] == "new" and holds_earlier_run(p["dest"]):
            note += ("; this folder already holds an earlier run (another workflow or other inputs) - its files will be "
                     "moved into _prev_... inside it. To keep both side by side, give this run its own --tag "
                     f"(e.g. --tag {a.tag}_refine)")
        print(f"  seed {p['seed']:<12} {p['dest']}  [{p['state']}] {note}")
    if a.dry_run:
        print(f"nothing queued (--dry-run). To run exactly this batch: add --confirm {batch_id}")
        return
    if a.confirm and a.confirm != batch_id:
        print(f"the batch is now {batch_id}, not the confirmed {a.confirm}: inputs changed since it was approved - "
              f"show the new --dry-run and confirm again", file=sys.stderr)
        sys.exit(2)

    client = uuid.uuid4().hex
    rc, ran = 0, 0
    try:
        for i, p in enumerate(plan):
            if p["state"] == "done":
                continue
            seed, fp, dest = p["seed"], p["fp"], p["dest"]
            for n, key in snodes:
                wf[n]["inputs"][key] = seed
            pid, t0, entry = None, time.time(), None
            if p["state"] == "resume":
                h = json.loads((dest / "handle.json").read_text(encoding="utf-8"))
                state, entry = lookup_stable(a.server, h["prompt_id"])
                if state in ("done", "queued"):
                    pid, t0 = h["prompt_id"], float(h.get("queued_at", t0))
                    print(f"[{i + 1}/{len(plan)}] seed={seed}: job {pid} is {'finished' if state == 'done' else 'still on the server'} - collecting",
                          flush=True)
                elif state == "unreachable":
                    die(f"cannot reach ComfyUI at {a.server}")
                else:
                    print(f"[{i + 1}/{len(plan)}] seed={seed}: the server no longer knows job {h['prompt_id']} - resubmitting", flush=True)
            if pid is None:
                archive_previous(dest)
                dest.mkdir(parents=True, exist_ok=True)
                pid = queue(a.server, wf, client)
                (dest / "handle.json").write_text(json.dumps({"prompt_id": pid, "fingerprint": fp, "seed": seed, "queued_at": t0,
                                                              "server": a.server}, indent=1), encoding="utf-8")
                print(f"[{i + 1}/{len(plan)}] queued {pid} seed={seed}", flush=True)
            if entry is None:
                entry = wait(a.server, pid, a.poll, a.timeout)
            status = entry.get("status", {})
            ok = status.get("status_str") != "error"
            files = download(a.server, entry, dest) if ok else []
            meta = {"prompt_id": pid, "seed": seed, "fingerprint": fp, "seconds": round(time.time() - t0, 1),
                    "status": "success" if ok and files else ("error" if not ok else "no_output"),
                    "files": [str(f) for f in files], "workflow": str(a.workflow), "comfyui_version": version,
                    "overrides": a.set + a.set_title, "media_sha256": media, "frames": frames, "pixels": pixels}
            (dest / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            ran += 1
            if a.log:
                log_take(Path(a.log), {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": a.tag, "seed": seed, "status": meta["status"],
                                       "seconds": meta["seconds"], "workflow": Path(a.workflow).name, "fingerprint": fp[:12],
                                       "output": files[0].name if files else "", "overrides": " ".join(a.set + a.set_title),
                                       "score": "", "frames": frames, "pixels": pixels,
                                       "settings": "; ".join(settings_summary(wf))})
            if a.free_every and ran % a.free_every == 0:
                try:
                    http(a.server, "/free", json.dumps({"unload_models": True, "free_memory": True}).encode(),
                         {"Content-Type": "application/json"})
                    print("  /free sent")
                except Exception as e:  # noqa: BLE001
                    print("  /free failed:", e)
            if not ok:
                rc = 1
                msgs = [m for m in status.get("messages", []) if m and m[0] == "execution_error"]
                print("  ERROR:", json.dumps(msgs, ensure_ascii=False)[:1500])
            elif not files:
                rc = 1
                print("  finished but produced no output files - does the workflow end in a Save node?")
            else:
                print(f"  done in {meta['seconds']}s -> {', '.join(f.name for f in files)}")
    except KeyboardInterrupt:
        print("\ninterrupted: jobs already queued keep running on the server; run the same command again to collect them",
              file=sys.stderr)
        sys.exit(130)
    sys.exit(rc)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
