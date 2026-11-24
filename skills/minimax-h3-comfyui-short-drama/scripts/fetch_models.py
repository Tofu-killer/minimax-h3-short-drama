#!/usr/bin/env python3
"""Check - and, when asked, download - the model files the shipped workflows load.

    python fetch_models.py --comfyui D:\\ComfyUI_windows_portable\\ComfyUI                     # check only (default)
    python fetch_models.py --comfyui <ComfyUI folder> --sets ref2va stills refine --download     # fetch what is missing
    python fetch_models.py --comfyui <ComfyUI folder> --verify-hash                              # also compare SHA-256

The list is assets/workflows/models.json: for every file its HuggingFace repository, the folder under ComfyUI/models
it belongs in, its size and its SHA-256 (as listed on HuggingFace on the date in that file). Sets: ref2va (the main
video path), stills (= t2i, Qwen-Image 2.1, + edit, Qwen-Image-Edit-2511), refine (the latent upscaler), fl2va (first /
last frame and text-only segments), zimage (Z-Image-Turbo, the Apache-2.0 text-to-picture model), music (ACE-Step 1.5
XL turbo for the score). Without --sets:
ref2va, stills and refine. A project that earns money: --sets ref2va edit zimage refine.

Check (default) tells for each file: ok / missing / incomplete (smaller than it should be: an interrupted download,
the usual cause of "header too small" or a model that will not load) / wrong size / in the wrong folder (found
elsewhere under models/). It never changes anything.

--download fetches what is missing or incomplete, straight from huggingface.co, into the right folder. A download
that was interrupted continues where it stopped (the partial file is kept as <name>.part). Only the standard
library is used - no huggingface_hub, no token (the repositories are public). --verify-hash reads every file once
more to compare its SHA-256 (slow: about a minute per 10 GB on an SSD); a freshly downloaded file is always hashed
while it is written.

Exit code: 0 everything asked for is in place; 1 something is missing, incomplete or different; 2 bad arguments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MANIFEST = HERE.parent / "assets" / "workflows" / "models.json"
CHUNK = 8 * 1024 * 1024


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def gb(n: int) -> str:
    return f"{n / 1e9:.2f} GB" if n >= 1e8 else f"{n / 1e6:.0f} MB"


def sha256_of(path: Path, show: str = "") -> str:
    h, done, size, t0 = hashlib.sha256(), 0, path.stat().st_size, time.time()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(CHUNK)
            if not block:
                break
            h.update(block)
            done += len(block)
            if show and time.time() - t0 > 5:
                print(f"\r    hashing {show}: {done * 100 // max(size, 1)}%", end="", flush=True)
    if show and time.time() - t0 > 5:
        print("\r" + " " * 70 + "\r", end="")
    return h.hexdigest()


def state(models: Path, item: dict, verify: bool) -> tuple[str, str]:
    """-> (status, detail); status: ok | missing | incomplete | wrong_size | wrong_hash | elsewhere"""
    name = Path(item["path"]).name
    dest = models / item["folder"] / name
    if not dest.exists():
        part = dest.with_name(name + ".part")
        if part.exists():
            return "incomplete", f"a partial download of {gb(part.stat().st_size)} of {gb(item['size'])} is waiting ({part.name})"
        other = [p for p in models.rglob(name) if p.is_file()] if models.is_dir() else []
        if other:
            return "elsewhere", f"found at {other[0].relative_to(models)} - ComfyUI looks for it in {item['folder']}/"
        return "missing", ""
    have = dest.stat().st_size
    if have < item["size"]:
        return "incomplete", f"{gb(have)} of {gb(item['size'])} - the download did not finish"
    if have > item["size"]:
        return "wrong_size", f"{have} bytes on disk, {item['size']} expected - another file under this name?"
    if verify:
        got = sha256_of(dest, name)
        if got != item["sha256"]:
            return "wrong_hash", f"SHA-256 {got[:16]}... differs from the listed {item['sha256'][:16]}... - damaged, or the repository has a newer file"
    return "ok", ""


def download(models: Path, item: dict) -> tuple[bool, str]:
    """Fetch one file, continuing a partial one. The SHA-256 is computed while writing and compared at the end."""
    name = Path(item["path"]).name
    folder = models / item["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    dest, part = folder / name, folder / (name + ".part")
    if dest.exists() and dest.stat().st_size < item["size"] and not part.exists():
        dest.rename(part)                                   # an unfinished file from another tool: carry on from it
    url = f"https://huggingface.co/{item['repo']}/resolve/main/{item['path']}"
    h = hashlib.sha256()
    have = part.stat().st_size if part.exists() else 0
    if have > item["size"]:
        part.unlink()
        have = 0
    if have:                                               # hash what is already there, then continue after it
        with open(part, "rb") as fh:
            for block in iter(lambda: fh.read(CHUNK), b""):
                h.update(block)
    t0, last = time.time(), 0.0
    for attempt in range(1, 6):
        if have >= item["size"]:
            break
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-", "User-Agent": "fetch_models.py"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp, open(part, "ab") as out:
                if have and resp.status != 206:             # the server ignored the range: start over
                    out.truncate(0)
                    have, h = 0, hashlib.sha256()
                while True:
                    block = resp.read(CHUNK)
                    if not block:
                        break
                    out.write(block)
                    h.update(block)
                    have += len(block)
                    if time.time() - last > 2:
                        last = time.time()
                        rate = have / max(time.time() - t0, 1e-6)
                        print(f"\r    {name}: {have * 100 // item['size']}%  {gb(have)} of {gb(item['size'])}  ({rate / 1e6:.0f} MB/s)   ",
                              end="", flush=True)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            print(f"\n    interrupted ({e}); attempt {attempt} of 5 - continuing from {gb(have)}")
            time.sleep(min(30, 3 * attempt))
    print("\r" + " " * 100 + "\r", end="")
    if have != item["size"]:
        return False, f"got {gb(have)} of {gb(item['size'])} - run the same command again to continue"
    if h.hexdigest() != item["sha256"]:
        return False, (f"downloaded, but its SHA-256 {h.hexdigest()[:16]}... is not the listed {item['sha256'][:16]}... - the repository may "
                       f"have replaced the file since {MANIFEST.name} was written; it was left as {part.name}")
    part.replace(dest)
    return True, f"{gb(have)} in {time.time() - t0:.0f} s"


def main() -> None:
    _utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__[__doc__.index("The list is"):])
    ap.add_argument("--comfyui", required=True, help="the ComfyUI folder (the one that holds main.py and models/)")
    ap.add_argument("--sets", nargs="+", default=["ref2va", "stills", "refine"], help="ref2va, stills (= t2i + edit), refine, fl2va, zimage, music; default: ref2va stills refine. A project that earns money takes `ref2va edit zimage refine`: t2i is Qwen-Image 2.1 (research licence), zimage its Apache-2.0 replacement")
    ap.add_argument("--download", action="store_true", help="fetch what is missing or incomplete (default: only check)")
    ap.add_argument("--verify-hash", action="store_true", help="also compare the SHA-256 of files already on disk (slow)")
    a = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    aliases = manifest.get("aliases", {})                   # stills = t2i + edit
    asked, a.sets = a.sets, []
    for name in asked:
        for real in aliases.get(name, [name]):
            if real not in a.sets:
                a.sets.append(real)
    unknown = [s for s in a.sets if s not in manifest["sets"]]
    if unknown:
        sys.exit(f"unknown set(s) {unknown}; there are: {', '.join(list(manifest['sets']) + list(aliases))}")
    root = Path(a.comfyui)
    models = root / "models"
    if not models.is_dir():
        hint = " - did you mean its ComfyUI subfolder?" if (root / "ComfyUI" / "models").is_dir() else ""
        print(f"{root} has no models/ folder: give the folder that holds main.py and models/{hint}", file=sys.stderr)
        sys.exit(2)

    items = [f for f in manifest["files"] if f["set"] in a.sets]
    need = sum(f["size"] for f in items)
    print(f"{len(items)} file(s), {gb(need)} in all, for: " + "; ".join(f"{s} = {manifest['sets'][s]}" for s in a.sets))
    todo, bad = [], 0
    for f in items:
        st, detail = state(models, f, a.verify_hash)
        where = f"models/{f['folder']}/{Path(f['path']).name}"
        print(f"  {st.upper():10s} {where}  ({gb(f['size'])}; {f['repo']})" + (f" - {detail}" if detail else ""))
        if st in ("missing", "incomplete"):
            todo.append(f)
        elif st != "ok":
            bad += 1
    if todo and not a.download:
        print(f"\n{len(todo)} file(s) to fetch, {gb(sum(f['size'] for f in todo))}. Add --download to fetch them here, or download by hand:")
        for f in todo:
            print(f"  https://huggingface.co/{f['repo']}/resolve/main/{f['path']}\n      -> {models / f['folder']}")
    if a.download and todo:
        try:
            import shutil
            free = shutil.disk_usage(models).free
            want = sum(f["size"] for f in todo)
            if free < want:
                print(f"\nonly {gb(free)} free on this drive, {gb(want)} still to fetch - free some space first", file=sys.stderr)
                sys.exit(1)
        except OSError:
            pass
        print()
        left = []
        for f in todo:
            print(f"  fetching {Path(f['path']).name} ({gb(f['size'])}) from {f['repo']}")
            ok, detail = download(models, f)
            print(f"    {'done' if ok else 'NOT COMPLETE'}: {detail}")
            if not ok:
                left.append(f)
        todo = left
    if todo or bad:
        print(f"\nnot ready: {len(todo)} missing or incomplete, {bad} to look at")
        sys.exit(1)
    print("\nall in place" + ("" if a.verify_hash else " (sizes match; --verify-hash also compares the SHA-256)"))


if __name__ == "__main__":
    sys.path.insert(0, str(HERE / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
