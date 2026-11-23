#!/usr/bin/env python3
"""Character identity gate for anime / hand-drawn / 3D-toon pictures and clips (the real-face gate cannot see them).

    # first frames and derived views against the bible, before any video GPU time is spent
    python3 identity_gate_anime.py --episode episodes/ep01.json --targets "first/*.png" --out qc/identity_anime

    # takes: the segment id in the path tells which character is expected
    python3 identity_gate_anime.py --episode episodes/ep01.json --targets "takes/ep01/**/*.mp4" --out qc/identity_anime

    # without a storyboard
    python3 identity_gate_anime.py --ref lin=bible/lin_bust.png,bible/lin_full.png --ref zhou=bible/zhou_bust.png \
        --targets "views/lin_*.png" --expect lin --out qc/identity_anime

It uses CCIP (deepghs, "contrastive anime character image pre-training"): a model trained to tell whether two
anime pictures show the same character regardless of pose, outfit and drawing style. Each picture gets one
feature for the WHOLE picture, and the model returns a difference between two pictures (0 = identical):

    difference <= 0.178   same character      (the model's own default threshold, F1 0.917 on its test set)
    0.178 - 0.30          borderline: look    (provisional band from a 12-picture check: same-character pairs
                                               reached 0.28, different characters started at 0.34)
    > 0.30                a different character

Because the whole picture is compared, it only judges pictures with ONE expected character. Frames of a
segment with two or more characters are listed with their differences but not judged (use the VLM judge
prompt for those), and a wide shot where the character is small will read as borderline. Its best use is
the image stage: derived views and single-character first frames against the frozen anchor.

Before judging it checks the bible itself: two characters closer than the same-character threshold are
flagged `bible_ambiguous` (give them clearly different hair colour, silhouette or palette - do not tune the
threshold), and references of one character further apart than the borderline are `bible_inconsistent`.

Default is advisory (exit 0); --strict exits 1 when a target fails.
Needs: onnxruntime, numpy, opencv-python(-headless); ffmpeg / ffprobe for clips. The model (150 MB,
OpenRAIL licence - read its terms before commercial use) is fetched once from HuggingFace
(deepghs/ccip_onnx) into --models-dir unless --offline is given.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__

sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import signals  # noqa: E402


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()

REPO = "https://huggingface.co/deepghs/ccip_onnx/resolve/main/ccip-caformer-24-randaug-pruned"
FILES = ("model_feat.onnx", "model_metrics.onnx")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv"}
MEAN, STD = (0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)


def ensure_models(models_dir: Path, offline: bool) -> dict[str, Path]:
    d = models_dir / "ccip-caformer-24-randaug-pruned"
    d.mkdir(parents=True, exist_ok=True)
    out = {}
    for name in FILES:
        p = d / name
        if not p.exists() or p.stat().st_size < 1000:
            if offline:
                sys.exit(f"model missing: {p}\n  download {REPO}/{name}\n  and place it there, or drop --offline")
            print(f"downloading {name} from deepghs/ccip_onnx ...", flush=True)
            tmp = p.with_suffix(".part")
            urllib.request.urlretrieve(f"{REPO}/{name}", tmp)
            tmp.replace(p)
        out[name] = p
    return out


class Ccip:
    def __init__(self, models: dict[str, Path]):
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        self.feat = ort.InferenceSession(str(models["model_feat.onnx"]), opts, providers=["CPUExecutionProvider"])
        self.metric = ort.InferenceSession(str(models["model_metrics.onnx"]), opts, providers=["CPUExecutionProvider"])

    def feature(self, bgr):
        """Same preprocessing as the reference implementation (384x384 bilinear, CLIP normalisation); with
        OpenCV's bilinear resize the differences agree with it to within 0.001."""
        import cv2
        import numpy as np
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        x = cv2.resize(rgb, (384, 384), interpolation=cv2.INTER_LINEAR).transpose(2, 0, 1).astype(np.float32) / 255.0
        x = (x - np.array(MEAN, np.float32)[:, None, None]) / np.array(STD, np.float32)[:, None, None]
        return self.feat.run(["output"], {"input": x[None].astype(np.float32)})[0][0]

    def differences(self, feats: list):
        import numpy as np
        return self.metric.run(["output"], {"input": np.stack(feats).astype(np.float32)})[0]


def imread(path: Path):
    import cv2
    import numpy as np
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)     # works with non-ASCII paths on Windows


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def frames_of(path: Path, fps: float, freeze_tail: float, tmp: Path) -> list[tuple[float, Path]]:
    end = max(0.1, duration(path) - freeze_tail - 0.05)
    times, t = [], 0.0
    while t < end:
        times.append(round(t, 3))
        t += 1.0 / fps
    if not times or end - times[-1] > 0.3:              # the last moving frame, unless a sample already sits next to it
        times.append(round(end, 3))
    out = []
    for t in sorted(set(times)):
        dest = tmp / f"{abs(hash(str(path))) % 10**8}_{int(t * 1000):07d}.png"
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", str(dest)],
                           capture_output=True)
        if r.returncode == 0 and dest.exists():
            out.append((t, dest))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--episode", help="episode JSON: references and per-segment expected characters")
    ap.add_argument("--ref", action="append", default=[], help="id=path[,path...] (repeatable); adds to / replaces --episode references")
    ap.add_argument("--targets", nargs="+", required=True, help="image / video paths or globs (** allowed; quote them)")
    ap.add_argument("--expect", help="the character id expected in every target (overrides the storyboard)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--match", type=float, default=0.178, help="difference at or below this = same character (model default)")
    ap.add_argument("--borderline", type=float, default=0.30, help="difference above this = a different character (provisional)")
    ap.add_argument("--fps", type=float, default=1.0, help="video sampling rate")
    ap.add_argument("--freeze-tail", type=float, default=1.0, help="seconds of declared end freeze to skip in clips")
    ap.add_argument("--models-dir", default=str(Path.home() / ".cache" / "h3-skill" / "models"))
    ap.add_argument("--offline", action="store_true", help="never download models")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any target fails")
    a = ap.parse_args()
    for mod, pip in (("onnxruntime", "onnxruntime"), ("numpy", "numpy"), ("cv2", "opencv-python-headless")):
        try:
            __import__(mod)
        except ImportError:
            sys.exit(f"missing dependency: pip install {pip}")

    refs: dict[str, list[Path]] = {}
    seg_expect: dict[str, list[str]] = {}
    if a.episode:
        ep_path = Path(a.episode)
        ep = json.loads(ep_path.read_text(encoding="utf-8"))
        for c in ep.get("characters", []):
            paths = [p if p.is_absolute() or p.exists() else ep_path.parent / p for p in map(Path, c.get("reference_images", []))]
            if paths:
                refs[c["id"]] = paths
        seg_expect = {s["id"]: list(s.get("character_ids", [])) for s in ep.get("segments", [])}
    for item in a.ref:
        k, _, v = item.partition("=")
        refs[k.strip()] = [Path(x) for x in v.split(",") if x.strip()]
    if not refs:
        sys.exit("no references: give --episode or at least one --ref id=path")

    engine = Ccip(ensure_models(Path(a.models_dir), a.offline))
    bible: dict[str, list] = {}
    for cid, paths in refs.items():
        feats = []
        for p in paths:
            img = imread(p) if p.exists() else None
            if img is None:
                print(f"NOTE {cid}: reference not readable: {p}")
                continue
            feats.append(engine.feature(img))
        if feats:
            bible[cid] = feats
    if not bible:
        sys.exit("no readable reference image for any character")

    # ---- the bible checks itself -----------------------------------------------------------------
    ids = list(bible)
    flat = [(cid, f) for cid in ids for f in bible[cid]]
    dm = engine.differences([f for _c, f in flat])
    calib = {"within": {}, "between": {}, "warnings": []}
    for cid in ids:
        idx = [i for i, (c, _f) in enumerate(flat) if c == cid]
        worst = max((float(dm[i][j]) for i in idx for j in idx if i < j), default=0.0)
        calib["within"][cid] = round(worst, 3)
        if worst > a.borderline:
            calib["warnings"].append(f"bible_inconsistent:{cid} (its own references differ by {worst:.2f})")
    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            ix = [i for i, (c, _f) in enumerate(flat) if c == ids[x]]
            iy = [i for i, (c, _f) in enumerate(flat) if c == ids[y]]
            closest = min(float(dm[i][j]) for i in ix for j in iy)
            calib["between"][f"{ids[x]}|{ids[y]}"] = round(closest, 3)
            if closest <= a.match:
                calib["warnings"].append(f"bible_ambiguous:{ids[x]}|{ids[y]} (difference {closest:.2f}: the model cannot tell them apart)")
            elif closest <= a.borderline:
                calib["warnings"].append(f"bible_close:{ids[x]}|{ids[y]} (difference {closest:.2f}: borderline verdicts will be unreliable)")
    for w in calib["warnings"]:
        print("BIBLE", w)

    def diff_to(feat, cid: str) -> float:
        return float(min(engine.differences([feat, r])[0][1] for r in bible[cid]))

    paths: list[Path] = []
    for pat in a.targets:
        hits = sorted(glob.glob(pat, recursive=True)) or ([pat] if Path(pat).exists() else [])
        paths += [Path(h) for h in hits if Path(h).suffix.lower() in IMAGE_EXT | VIDEO_EXT]
    paths, skipped = signals.live_takes(paths)
    if skipped:
        print(f"note: {skipped} file(s) skipped: superseded takes in _prev_* folders, and *_trimmed.mp4 copies (extract_tail_frame.py) of takes that are in the list")
    if not paths:
        sys.exit("no image / video targets matched")
    override = [a.expect.strip()] if a.expect else None
    if override and override[0] not in bible:
        sys.exit(f"--expect {override[0]} has no reference in the bible ({', '.join(bible)})")

    results, any_fail = [], False
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for p in paths:
            expected = override
            if expected is None:
                expected = []
                for tok in re.split(r"[^A-Za-z0-9]+", str(p)):
                    if tok in seg_expect:
                        expected = seg_expect[tok]
                if not expected and not seg_expect and len(bible) == 1:
                    expected = list(bible)
            frames = [(None, p)] if p.suffix.lower() in IMAGE_EXT else frames_of(p, a.fps, a.freeze_tail, tmp)
            rows = []
            for t, fp in frames:
                img = imread(fp)
                if img is None:
                    continue
                feat = engine.feature(img)
                d = {cid: round(diff_to(feat, cid), 3) for cid in bible}
                rows.append({"t": t, "differences": d})
            entry = {"target": str(p), "expected": expected, "frames": len(rows)}
            exp_known = [c for c in expected if c in bible]
            if not rows:
                entry.update({"verdict": "error", "flags": ["unreadable"]})
            elif len(exp_known) != 1:
                why = "no_expected_character" if not exp_known else "multi_character_frame"
                entry.update({"verdict": "skip", "flags": [why],
                              "closest": {cid: min(r["differences"][cid] for r in rows) for cid in bible}})
            else:
                cid = exp_known[0]
                vals = [r["differences"][cid] for r in rows]
                verdicts = ["pass" if v <= a.match else "warn" if v <= a.borderline else "fail" for v in vals]
                seen: dict[str, list] = {}
                for r in rows:
                    other = min(((v, o) for o, v in r["differences"].items() if o != cid), default=None)
                    if other and other[0] <= a.match and other[0] < r["differences"][cid]:
                        seen.setdefault(other[1], []).append(r["t"])
                flags = [f"resembles_unexpected:{o}" + (f"@{ts[0]}s" if ts[0] is not None else "")
                         + (f"(+{len(ts) - 1} more frame(s))" if len(ts) > 1 else "") for o, ts in seen.items()]
                fail_share = verdicts.count("fail") / len(verdicts)
                if len(rows) == 1:
                    verdict = verdicts[0]
                else:
                    verdict = "fail" if (fail_share > 0.2 or verdicts[0] == "fail") else "warn" if ("fail" in verdicts or "warn" in verdicts) else "pass"
                    first_bad = next((r["t"] for r, v in zip(rows, verdicts) if v == "fail"), None)
                    entry.update({"fail_share": round(fail_share, 2), "first_fail_s": first_bad})
                if flags and verdict == "pass":
                    verdict = "warn"
                entry.update({"verdict": verdict, "character": cid, "difference_median": round(sorted(vals)[len(vals) // 2], 3),
                              "difference_worst": round(max(vals), 3), "flags": sorted(set(flags))})
            entry["per_frame"] = rows
            any_fail |= entry["verdict"] == "fail"
            results.append(entry)
            extra = "" if entry["verdict"] in ("skip", "error") else f" {entry['character']} median {entry['difference_median']} worst {entry['difference_worst']}"
            print(f"{entry['verdict']:5s} {p}{extra} {' '.join(entry['flags'])}".rstrip())

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps({"embedder": "deepghs CCIP ccip-caformer-24-randaug-pruned (difference, lower = more alike)",
                                                 "thresholds": {"match": a.match, "borderline": a.borderline},
                                                 "calibration": calib, "targets": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "summary.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["target", "verdict", "character", "difference_median", "difference_worst", "frames", "flags"])
        for e in results:
            w.writerow([e["target"], e["verdict"], e.get("character", ""), e.get("difference_median", ""), e.get("difference_worst", ""),
                        e["frames"], " ".join(e["flags"])])
    counts = {k: sum(1 for e in results if e["verdict"] == k) for k in ("pass", "warn", "fail", "skip", "error")}
    print(f"{len(results)} target(s): {counts} -> {out / 'report.json'}")
    if counts["skip"]:
        print("skipped targets have none or several expected characters: this gate compares whole pictures, so it judges "
              "single-character pictures only - use assets/judge-take-prompt.md for the rest")
    sys.exit(1 if (a.strict and any_fail) else 0)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
