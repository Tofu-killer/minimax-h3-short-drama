#!/usr/bin/env python3
"""What the running ComfyUI can and cannot do for this skill - asked from the server itself; nothing is changed.

    python check_setup.py                                        # the server at http://127.0.0.1:8188
    python check_setup.py --server http://127.0.0.1:8188 --json logs/setup.json

It reads /system_stats and /object_info and reports
  * ComfyUI, Python and PyTorch versions, the start-up flags, the GPU and its memory, system memory
  * settings that cost speed before a single job is queued: a PyTorch build older than CUDA 13 (the fast int8
    kernels are not used), start-up flags that change how models are loaded, package versions ComfyUI asked for
    and did not get
  * for every workflow shipped with the skill: READY, or which node pack has to be installed and which model files
    the server does not list (with the fetch_models.py command that checks and fetches them)

What it cannot see from outside: the `sageattention` Python package (the first job with a `_sage` workflow tells),
the start-up log (`Found comfy_kitchen backend cuda: ...`), files that are only partly downloaded (fetch_models.py
compares sizes and hashes), the Windows driver setting "CUDA - Sysmem Fallback Policy".

Exit code: 0 when the Ref2VA draft workflow (h3_ref2va.api.json) is ready, 1 when it is not, 2 when the server
does not answer.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__

HERE = Path(__file__).resolve().parent
FLOWS = HERE.parent / "assets" / "workflows"

# node classes that do not come with ComfyUI itself -> the pack that brings them (GitHub owner/name)
PACKS = {"PathchSageAttentionKJ": "kijai/ComfyUI-KJNodes", "MiniMaxH3MemoryEfficientSageAttentionPatch": "kijai/ComfyUI-KJNodes",
         "H3HiresFix": "tazmannner/ComfyUI-H3-ResCascade", "H3LatentUpscaleLBH": "tazmannner/ComfyUI-H3-ResCascade",
         "MMH3SplitUpscale": "LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler",
         "MMH3TemporalSplitParamsV10": "LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler"}
MODEL_EXT = (".safetensors", ".gguf", ".pth", ".pt", ".ckpt", ".sft")
# flags that leave the default loading path of an NVIDIA card (DynamicVRAM) or move work off the GPU
LOAD_FLAGS = {"--disable-dynamic-vram": "switches DynamicVRAM off", "--highvram": "keeps models in VRAM (DynamicVRAM is not used)",
              "--gpu-only": "keeps everything on the GPU (DynamicVRAM is not used)", "--novram": "DynamicVRAM is not used",
              "--lowvram": "an older low-memory mode; the default (no flag) already loads on demand",
              "--cpu": "everything runs on the CPU"}
WHAT_FOR = {"selftest_no_model": "connection test (no model)", "h3_ref2va": "Ref2VA drafts", "h3_ref2va_sage": "Ref2VA drafts with Sage attention",
            "h3_ref2va_refine": "Ref2VA refine", "h3_ref2va_sage_refine": "Ref2VA refine (Sage)",
            "h3_ref2va_refine_split": "Ref2VA refine in chunks", "h3_ref2va_sage_refine_split": "Ref2VA refine in chunks (Sage)",
            "h3_fl2va": "first-frame / first-last-frame / text-only drafts", "h3_fl2va_sage": "the same with Sage attention",
            "h3_fl2va_refine": "FL2VA refine", "h3_fl2va_sage_refine": "FL2VA refine (Sage)",
            "h3_fl2va_refine_split": "FL2VA refine in chunks", "h3_fl2va_sage_refine_split": "FL2VA refine in chunks (Sage)",
            "qwen21_t2i": "stills: text to picture (Qwen-Image 2.1, research licence)",
            "zimage_turbo_t2i": "stills: text to picture (Z-Image-Turbo, Apache-2.0)",
            "qwen_edit2511_1ref": "stills: edit, 1 input picture", "qwen_edit2511_2ref": "stills: edit, 2 input pictures",
            "qwen_edit2511_3ref": "stills: edit, 3 input pictures"}


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def get_json(server: str, path: str, timeout: float = 60.0):
    try:
        with urllib.request.urlopen(server.rstrip("/") + path, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, ConnectionError, OSError):
        return None


def choices_of(spec) -> list | None:
    """The values a combo input offers, None when the input is not a combo."""
    if not isinstance(spec, (list, tuple)) or not spec:
        return None
    if isinstance(spec[0], list):
        return spec[0]
    if spec[0] == "COMBO" and len(spec) > 1 and isinstance(spec[1], dict):
        return spec[1].get("options")
    return None


def system_findings(st: dict) -> tuple[list[str], list[str]]:
    """(facts, warnings) from /system_stats."""
    sysinfo, facts, warns = st.get("system", {}), [], []
    torch = str(sysinfo.get("pytorch_version") or "?")
    facts.append(f"ComfyUI {sysinfo.get('comfyui_version', '?')}, Python {str(sysinfo.get('python_version', '?')).split()[0]}, PyTorch {torch}"
                 + (", embedded Python (portable build)" if sysinfo.get("embedded_python") else ""))
    m = re.search(r"\+cu(\d+)", torch)
    if m and int(m.group(1)) < 130:
        warns.append(f"PyTorch is a CUDA {m.group(1)[:-1]}.{m.group(1)[-1]} build: the fast int8 kernels (comfy-kitchen's cuda backend) need the "
                     f"CUDA 13 build, so int8 weights run on the slow path. The default portable package "
                     f"(ComfyUI_windows_portable_nvidia.7z) ships cu130; the _cu126 package is for 10-series cards")
    elif not m and "+cpu" not in torch:
        facts.append("the PyTorch version string names no CUDA build - check the start-up log line `Found comfy_kitchen backend cuda: ...`")
    for d in st.get("devices", []):
        total, free = d.get("vram_total", 0) / 2**30, d.get("vram_free", 0) / 2**30
        facts.append(f"device {d.get('name', '?')}: {free:.1f} of {total:.1f} GB free")
        if d.get("type") == "cuda" and total < 22:
            warns.append(f"{total:.0f} GB of VRAM: the shipped settings (1344x768, 10 s segments) are sized for 24 GB - use a smaller "
                         f"canvas or shorter segments (references/local-stack-and-acceleration.md)")
        if d.get("type") == "cuda" and total >= 22 and free < 0.6 * total:
            warns.append(f"only {free:.1f} of {total:.1f} GB of VRAM is free right now: close what else uses the GPU "
                         f"(a browser with hardware acceleration, another ComfyUI, a game) before a batch")
    ram, ram_free = sysinfo.get("ram_total", 0) / 2**30, sysinfo.get("ram_free", 0) / 2**30
    if ram:
        facts.append(f"system memory: {ram_free:.1f} of {ram:.1f} GB free")
        if ram < 31:
            warns.append(f"{ram:.0f} GB of system memory: the 15.7 GB text encoder and the 21 GB model pass through it when they are "
                         f"swapped - expect page-file use; keep the page file on the SSD")
    argv = [str(x) for x in sysinfo.get("argv", [])]
    flags = [a for a in argv[1:] if a.startswith("--")]
    facts.append("started with: " + (" ".join(argv[1:]) if argv[1:] else "no arguments"))
    for f in flags:
        if f in LOAD_FLAGS:
            warns.append(f"start-up flag {f}: {LOAD_FLAGS[f]}. The notes of this skill assume the default loading path "
                         f"(log lines such as `... patches attached.` belong to it)")
    for p in sysinfo.get("comfy_package_versions", []) or []:
        if p.get("installed") and p.get("required") and p["installed"] != p["required"]:
            warns.append(f"package {p.get('name')}: {p['installed']} installed, ComfyUI {sysinfo.get('comfyui_version', '')} asks for "
                         f"{p['required']} - update it with ComfyUI's own Python (pip install -r requirements.txt)")
    return facts, warns


def workflow_state(wf: dict, info: dict) -> tuple[dict, list]:
    """({class: pack or ''} for node classes the server does not have, [(input, file, closest)] for model files it does not list)."""
    classes, files = {}, []
    for node in wf.values():
        cls = node.get("class_type")
        if cls not in info:
            classes[cls] = PACKS.get(cls, "")
            continue
        spec = info[cls].get("input", {})
        every = {**(spec.get("required", {}) or {}), **(spec.get("optional", {}) or {})}
        for name, val in node.get("inputs", {}).items():
            if not (isinstance(val, str) and val.lower().endswith(MODEL_EXT)):
                continue
            offered = choices_of(every.get(name))
            if offered is not None and val not in offered:
                names = [str(c) for c in offered]
                moved = [c for c in names if re.split(r"[\\/]", c)[-1] == val]        # the right file, one folder too deep
                near = moved or difflib.get_close_matches(val, names, n=1, cutoff=0.85)
                files.append((name, val, near[0] if near else ""))
    return classes, files


def main():
    _utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--server", default="http://127.0.0.1:8188")
    ap.add_argument("--json", help="also write the findings to this file")
    a = ap.parse_args()

    st = get_json(a.server, "/system_stats", timeout=15)
    if not isinstance(st, dict):
        print(f"ComfyUI at {a.server} does not answer. Start it (run_nvidia_gpu.bat in the portable folder), wait for "
              f"`To see the GUI go to: http://127.0.0.1:8188`, then run this again; another address: --server http://host:port")
        sys.exit(2)
    facts, warns = system_findings(st)
    print(f"== the server at {a.server}")
    for f in facts:
        print("  " + f)

    info = get_json(a.server, "/object_info", timeout=120)
    if not isinstance(info, dict) or not info:
        print("could not read /object_info from the server - is it still starting?")
        sys.exit(2)
    manifest = {}
    try:
        for item in json.loads((FLOWS / "models.json").read_text(encoding="utf-8")).get("files", []):
            manifest[Path(item["path"]).name] = item
    except (OSError, json.JSONDecodeError, KeyError):
        pass

    print(f"\n== the workflows shipped with the skill ({FLOWS})")
    report, packs, missing_files, upgrade = {}, {}, {}, set()
    for f in sorted(FLOWS.glob("*.api.json")):
        key = f.name[:-len(".api.json")]
        try:
            wf = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"  ??       {f.name}: cannot be read ({e})")
            continue
        classes, files = workflow_state(wf, info)
        report[key] = {"missing_node_classes": classes, "missing_files": [{"input": i, "file": v, "closest": c} for i, v, c in files]}
        what = WHAT_FOR.get(key, "")
        if not classes and not files:
            print(f"  READY    {f.name}" + (f"  - {what}" if what else ""))
            continue
        why = []
        for cls, pack in classes.items():
            if pack:
                packs.setdefault(pack, set()).add(cls)
                why.append(f"node {cls} (pack {pack})")
            else:
                upgrade.add(cls)
                why.append(f"node {cls} (not in this ComfyUI)")
        for inp, val, near in files:
            missing_files.setdefault(val, near)
            why.append(f"file {val}")
        print(f"  MISSING  {f.name}" + (f"  - {what}" if what else "") + "\n             " + "; ".join(why))

    todo = []
    for pack, classes in sorted(packs.items()):
        todo.append(f"install the node pack https://github.com/{pack} (git clone into ComfyUI/custom_nodes, restart ComfyUI) - "
                    f"it brings {', '.join(sorted(classes))}")
    if upgrade:
        todo.append(f"this ComfyUI has no node {', '.join(sorted(upgrade))}: the shipped workflows were exported from 0.37.2 - upgrade "
                    f"ComfyUI to that version or newer")
    if missing_files:
        sets = sorted({manifest[n]["set"] for n in missing_files if n in manifest})
        for name, near in sorted(missing_files.items()):
            item = manifest.get(name)
            where = f"models/{item['folder']}/ (from {item['repo']}, {item['size'] / 1e9:.1f} GB)" if item else "the matching models/ folder"
            if near and re.split(r"[\\/]", near)[-1] == name:
                hint = (f"; the server lists it as `{near}` - it sits in a sub-folder: move the file up into the folder itself "
                        f"(the workflows name it without a sub-folder)")
            else:
                hint = f"; the server lists a similar name, `{near}` - another version of the file?" if near else ""
            todo.append(f"model file {name} is not listed by the server - it goes into {where}{hint}")
        if sets:
            todo.append(f"check and fetch them in one go: python {HERE / 'fetch_models.py'} --comfyui <ComfyUI folder> --sets {' '.join(sets)} "
                        f"[--download] - then press R in ComfyUI or restart it so the new files are listed")
    if warns or todo:
        print("\n== to look at")
        for w in warns:
            print("  ! " + w)
        for t in todo:
            print("  - " + t)
    sage = [k for k in report if "_sage" in k and not report[k]["missing_node_classes"] and not report[k]["missing_files"]]
    print("\n== not visible from here")
    print("  - the `sageattention` package" + (": the Sage nodes are installed, the package is only loaded when a job runs - "
          "the first `_sage` job tells (references/local-stack-and-acceleration.md, section 0b)" if sage else ""))
    print("  - the start-up log: look for `Found comfy_kitchen backend cuda: {'available': True, ...}`")
    print("  - partly downloaded files: fetch_models.py compares sizes (and hashes with --verify-hash)")
    ready = [k for k, v in report.items() if not v["missing_node_classes"] and not v["missing_files"]]
    print(f"\n{len(ready)} of {len(report)} workflow(s) ready" + ("" if "h3_ref2va" in ready else
          " - the Ref2VA draft workflow (h3_ref2va.api.json) is not: nothing can be drafted yet"))
    if a.json:
        out = Path(a.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"server": a.server, "system": st.get("system"), "devices": st.get("devices"), "facts": facts,
                                   "warnings": warns, "todo": todo, "workflows": report}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"written: {out}")
    sys.exit(0 if "h3_ref2va" in ready else 1)


if __name__ == "__main__":
    sys.path.insert(0, str(HERE / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
