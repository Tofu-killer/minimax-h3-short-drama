#!/usr/bin/env python3
"""Submit an API-format ComfyUI workflow, wait for it, download the outputs.

Works against a stock ComfyUI server (default http://127.0.0.1:8188).  No extra
dependencies — stdlib only — so it runs inside any agent sandbox or on Windows
with the ComfyUI-embedded python.

    # 1) export the workflow from ComfyUI with "Export (API)" -> yz_ref2va.api.json
    # 2) override inputs by node id or by node title, upload media, run:
    python3 comfy_submit.py yz_ref2va.api.json \
        --set 12.text=@prompts/ep01/s03.txt \
        --set-title "Reference Image 1".image=@bible/fengyi_face.png \
        --set 7.seed=12345 --set 7.steps=8 \
        --out takes/ep01/s03 --tag seed12345

Rules:
  * `--set <node_id>.<input>=<value>` / `--set-title "<title>".<input>=<value>`
    - value `@path` reads a text file (for prompts) or, when the input name is
      `image` / `audio` / `video`, uploads that file to ComfyUI's input folder
      and substitutes the returned filename.
    - plain values are parsed as JSON when possible (numbers / booleans).
  * `--batch N` queues N runs with seed+i on every node that has a `seed` input
    (抽卡), each saved under <out>/<tag>_<seed>/.
  * exit code 1 when the server reports an execution error.
"""
import argparse, json, mimetypes, sys, time, urllib.request, urllib.parse, uuid
from pathlib import Path

MEDIA_INPUTS = {"image", "audio", "video", "image_path", "audio_path", "video_path"}


def http(server, path, data=None, headers=None, method=None):
    req = urllib.request.Request(server + path, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def upload(server, path: Path, kind="image") -> str:
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n").encode() + path.read_bytes() + \
           f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n".encode()
    res = json.loads(http(server, "/upload/image", body,
                          {"Content-Type": f"multipart/form-data; boundary={boundary}"}))
    name = res["name"]
    return f"{res['subfolder']}/{name}" if res.get("subfolder") else name


def parse_value(raw: str, input_name: str, server: str):
    if raw.startswith("@"):
        p = Path(raw[1:])
        if not p.exists():
            raise FileNotFoundError(p)
        if input_name in MEDIA_INPUTS or p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".flac", ".mp4", ".mov", ".webm"}:
            return upload(server, p)
        return p.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def find_by_title(wf: dict, title: str) -> str:
    hits = [k for k, v in wf.items() if v.get("_meta", {}).get("title") == title]
    if len(hits) != 1:
        raise SystemExit(f"title {title!r} matched {len(hits)} nodes: {hits}")
    return hits[0]


def apply_sets(wf, sets, server, by_title=False):
    for s in sets:
        target, _, raw = s.partition("=")
        node, _, inp = target.rpartition(".")
        node = node.strip('"')
        nid = find_by_title(wf, node) if by_title else node
        if nid not in wf:
            raise SystemExit(f"node {nid} not in workflow")
        wf[nid]["inputs"][inp] = parse_value(raw, inp, server)


def seed_nodes(wf):
    return [k for k, v in wf.items() if "seed" in v.get("inputs", {}) and not isinstance(v["inputs"]["seed"], list)]


def queue(server, wf, client_id):
    res = json.loads(http(server, "/prompt", json.dumps({"prompt": wf, "client_id": client_id}).encode(),
                          {"Content-Type": "application/json"}))
    if "error" in res:
        raise SystemExit(f"queue rejected: {json.dumps(res, ensure_ascii=False)[:2000]}")
    return res["prompt_id"]


def wait(server, pid, poll=5.0, timeout=7200):
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = json.loads(http(server, f"/history/{pid}"))
        if pid in hist:
            return hist[pid]
        time.sleep(poll)
    raise SystemExit("timed out waiting for ComfyUI")


def download(server, entry, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    for node_out in entry.get("outputs", {}).values():
        for key in ("videos", "gifs", "images", "audio"):
            for f in node_out.get(key, []):
                if f.get("type") != "output":
                    continue
                q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": "output"})
                data = http(server, f"/view?{q}")
                dest = out / f["filename"]
                dest.write_bytes(data)
                saved.append(dest)
    return saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow", help="API-format workflow JSON")
    ap.add_argument("--server", default="http://127.0.0.1:8188")
    ap.add_argument("--set", action="append", default=[], help="node_id.input=value (value may be @file)")
    ap.add_argument("--set-title", action="append", default=[], help='"Node title".input=value')
    ap.add_argument("--batch", type=int, default=1, help="number of seeds to queue (抽卡)")
    ap.add_argument("--seed", type=int, help="first seed; default keeps the workflow's seed")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="take")
    ap.add_argument("--poll", type=float, default=20.0, help="seconds between /history polls (polling mid-sample stalls the sampler 18-43 s, keep >= 20)")
    ap.add_argument("--free-every", type=int, default=0, help="POST /free (unload models, free memory) after every N runs; 0 = never")
    a = ap.parse_args()

    wf = json.loads(Path(a.workflow).read_text(encoding="utf-8"))
    if "nodes" in wf and "links" in wf:
        raise SystemExit("this is a UI workflow; export with 'Export (API)' instead")
    apply_sets(wf, a.set, a.server)
    apply_sets(wf, a.set_title, a.server, by_title=True)
    snodes = seed_nodes(wf)
    base_seed = a.seed if a.seed is not None else (wf[snodes[0]]["inputs"]["seed"] if snodes else 0)
    client = uuid.uuid4().hex
    rc = 0
    for i in range(a.batch):
        seed = base_seed + i
        for n in snodes:
            wf[n]["inputs"]["seed"] = seed
        pid = queue(a.server, wf, client)
        t0 = time.time()
        print(f"[{i+1}/{a.batch}] queued {pid} seed={seed}", flush=True)
        entry = wait(a.server, pid, a.poll)
        status = entry.get("status", {})
        dest = Path(a.out) / f"{a.tag}_{seed}"
        files = download(a.server, entry, dest)
        meta = {"prompt_id": pid, "seed": seed, "seconds": round(time.time() - t0, 1),
                "status": status.get("status_str"), "files": [str(f) for f in files],
                "overrides": a.set + a.set_title}
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        if a.free_every and (i + 1) % a.free_every == 0:
            try:
                http(a.server, "/free", json.dumps({"unload_models": True, "free_memory": True}).encode(), {"Content-Type": "application/json"})
                print("  /free sent")
            except Exception as e:  # noqa: BLE001
                print("  /free failed:", e)
        if status.get("status_str") == "error":
            rc = 1
            msgs = [m for m in status.get("messages", []) if m[0] == "execution_error"]
            print("  ERROR:", json.dumps(msgs, ensure_ascii=False)[:1500])
        else:
            print(f"  done in {meta['seconds']}s -> {', '.join(f.name for f in files) or '(no output files)'}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
