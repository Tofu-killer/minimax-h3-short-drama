#!/usr/bin/env python3
"""Character identity gate for stills and generated clips (real-face track).

Checks whether the faces in first frames / takes are the characters they are supposed to be,
using OpenCV's YuNet detector + SFace recogniser (both run on CPU, licences MIT / Apache-2.0).

    # with the storyboard: references and per-segment expectations come from the episode JSON
    python3 identity_gate.py --episode episodes/ep01.json --targets "takes/ep01/**/*.mp4" --out qc/identity

    # without a storyboard
    python3 identity_gate.py --ref lin_lan=bible/lin_lan_face.png,bible/lin_lan_full.png \
        --ref dr_zhou=bible/dr_zhou_face.png --targets "frames/*.png" --expect lin_lan,dr_zhou --out qc/identity

What it reports per image / per sampled video frame:
  * every usable face, the character it was assigned to (optimal one-to-one assignment), the cosine
    similarity and a verdict:  pass >= --match (0.55) | warn >= --borderline (0.363) | fail below
  * `resembles_unexpected:<id>`  the face looks like a character who is not expected in this segment
  * `duplicate_of:<id>`          a second face that also matches an already-assigned character (clone)
  * `extra_face`                 a face that matches nobody in the bible
  * `absent:<id>`                an expected character with no face in this frame (info only: back views
                                 and off-screen moments are normal)
  * `no_usable_face`             nothing detectable (profile, back view, tiny or stylised faces) - never a fail
Per clip it adds min / p10 / median per character, the share of failing frames and the first failing
timestamp; a clip fails when more than 20% of its face frames fail or its first face frame fails.

Before judging targets it calibrates on the references themselves: if two different characters are as
similar to each other as one character is to itself (`bible_ambiguous`), fix the character design -
do not tune thresholds.

Default is advisory (exit 0). `--strict` exits 1 when any target fails.
Scores are a warning signal, not ground truth: stylised / anime faces are usually not detected at all
(you will see `no_usable_face` everywhere - use identity_gate_anime.py for 2D / 3D-toon characters), and thresholds
come from OpenCV's SFace defaults (0.363 same-identity) plus a stricter delivery bar (0.55).

Needs: opencv-python(-headless) >= 4.8, numpy, ffmpeg/ffprobe on PATH for video targets.
Models are fetched once from HuggingFace (opencv/face_detection_yunet, opencv/face_recognition_sface)
into --models-dir unless --offline is given.
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


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()

MODELS = {
    "yunet": ("face_detection_yunet_2023mar.onnx",
              "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx"),
    "sface": ("face_recognition_sface_2021dec.onnx",
              "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx"),
}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv"}
MAX_SIDE = 1600          # detection runs on a copy no larger than this


def need(mod: str):
    try:
        return __import__(mod)
    except ImportError:
        sys.exit(f"missing dependency: pip install {'opencv-python-headless' if mod == 'cv2' else mod}")


cv2 = need("cv2")
np = need("numpy")


# ----------------------------------------------------------------------------- models / io

def ensure_models(models_dir: Path, offline: bool) -> dict[str, str]:
    models_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for key, (name, url) in MODELS.items():
        p = models_dir / name
        if not p.exists() or p.stat().st_size < 100_000:
            if offline:
                sys.exit(f"model missing: {p}\n  download {url}\n  and place it there, or drop --offline")
            print(f"downloading {name} ...", file=sys.stderr)
            urllib.request.urlretrieve(url, p)
        out[key] = str(p)
    return out


def imread(path: Path):
    """cv2.imread that survives non-ASCII paths on Windows."""
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"cannot decode image: {path}")
    return img


def imwrite(path: Path, img) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(path.suffix or ".jpg", img)
    if ok:
        buf.tofile(str(path))


def video_duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"ffprobe failed on {path}: {r.stderr.strip()[:200]}") from e


def grab_frame(path: Path, t: float, tmp: Path):
    """One frame at time t via ffmpeg (handles any codec / path ffmpeg can read)."""
    dest = tmp / f"f_{int(round(t * 1000)):08d}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(t, 0):.3f}", "-i", str(path), "-frames:v", "1", str(dest)],
                   capture_output=True)
    return imread(dest) if dest.exists() else None


def sample_times(duration: float, fps: float, freeze_tail: float, cuts: list[float]) -> list[float]:
    end = max(0.0, duration - freeze_tail - 0.05)
    ts = {0.0, round(end, 3)}
    k = 1
    while k / fps < end:
        ts.add(round(k / fps, 3))
        k += 1
    for c in cuts:                      # right after each declared cut the framing changes
        if 0 < c + 0.3 < end:
            ts.add(round(c + 0.3, 3))
    return sorted(ts)


# ----------------------------------------------------------------------------- faces

class FaceEngine:
    def __init__(self, models: dict[str, str], det_score: float, min_face: int):
        self.det = cv2.FaceDetectorYN.create(models["yunet"], "", (320, 320), det_score, 0.3, 5000)
        self.rec = cv2.FaceRecognizerSF.create(models["sface"], "")
        self.min_face = min_face

    def faces(self, img):
        """-> (list of {box, score, size, feat}), number of faces dropped for being too small."""
        h, w = img.shape[:2]
        scale = min(1.0, MAX_SIDE / max(h, w))
        work = cv2.resize(img, (int(round(w * scale)), int(round(h * scale)))) if scale < 1.0 else img
        self.det.setInputSize((work.shape[1], work.shape[0]))
        _, found = self.det.detect(work)
        out, dropped = [], 0
        for row in (found if found is not None else []):
            x, y, fw, fh = (float(v) / scale for v in row[:4])
            if min(fw, fh) < self.min_face:
                dropped += 1
                continue
            feat = self.rec.feature(self.rec.alignCrop(work, row)).flatten().astype("float32")
            feat /= (np.linalg.norm(feat) + 1e-9)
            out.append({"box": [round(x), round(y), round(fw), round(fh)], "score": round(float(row[14]), 3),
                        "size": int(round(min(fw, fh))), "feat": feat})
        out.sort(key=lambda f: -f["size"])
        return out, dropped


def hungarian(cost: list[list[float]]) -> list[int]:
    """Minimum-cost assignment for an n x m matrix with n <= m. Returns the column for each row."""
    n, m = len(cost), len(cost[0])
    INF = float("inf")
    u, v, p, way = [0.0] * (n + 1), [0.0] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = [INF] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    res = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            res[p[j] - 1] = j - 1
    return res


def sim_to(feat, gallery) -> float:
    return float(max(float(feat @ g) for g in gallery)) if gallery else -1.0


def judge_frame(faces: list[dict], bible: dict[str, list], expected: list[str], a) -> dict:
    """Assign faces to expected characters and attach verdicts / flags."""
    flags: list[str] = []
    rows = []
    if not faces:
        return {"faces": [], "flags": ["no_usable_face"], "verdict": "none"}
    exp = [c for c in expected if c in bible]
    sims = [[sim_to(f["feat"], bible[c]) for c in exp] for f in faces]
    assigned: dict[int, str] = {}
    if exp:
        if len(faces) <= len(exp):                                  # rows = faces
            cols = hungarian([[-s for s in row] for row in sims])
            assigned = {i: exp[c] for i, c in enumerate(cols) if c >= 0}
        else:                                                       # rows = characters
            t = [[-sims[i][j] for i in range(len(faces))] for j in range(len(exp))]
            cols = hungarian(t)
            assigned = {fi: exp[j] for j, fi in enumerate(cols) if fi >= 0}
    worst = "pass"
    for i, f in enumerate(faces):
        all_sims = {c: sim_to(f["feat"], g) for c, g in bible.items()}
        best_c = max(all_sims, key=all_sims.get) if all_sims else None
        row = {"box": f["box"], "det_score": f["score"], "size": f["size"], "assigned": assigned.get(i),
               "best_overall": best_c, "best_overall_sim": round(all_sims.get(best_c, -1.0), 3) if best_c else None}
        if i in assigned:
            s = all_sims[assigned[i]]
            row["sim"] = round(s, 3)
            row["verdict"] = "pass" if s >= a.match else "warn" if s >= a.borderline else "fail"
            if best_c and best_c != assigned[i] and all_sims[best_c] >= a.borderline and all_sims[best_c] > s + 0.05:
                # the slot of `assigned[i]` is filled by a face that is really someone else
                row["flag"] = (f"duplicate_of:{best_c}" if best_c in exp else f"resembles_unexpected:{best_c}")
                row["verdict"] = "fail"
        else:
            row["sim"] = round(all_sims.get(best_c, -1.0), 3) if best_c else None
            if best_c and all_sims[best_c] >= a.borderline:
                if best_c in exp:
                    row["flag"], row["verdict"] = f"duplicate_of:{best_c}", "warn"
                else:
                    row["flag"], row["verdict"] = f"resembles_unexpected:{best_c}", "fail"
            else:
                row["flag"], row["verdict"] = "extra_face", "warn"
        if row.get("flag"):
            flags.append(row["flag"])
        worst = {"pass": worst, "warn": "warn" if worst == "pass" else worst, "fail": "fail"}[row["verdict"]]
        rows.append(row)
    for c in exp:
        if c not in assigned.values():
            flags.append(f"absent:{c}")
    return {"faces": rows, "flags": flags, "verdict": worst}


# ----------------------------------------------------------------------------- bible / calibration

def load_bible(a, engine: FaceEngine):
    refs: dict[str, list[str]] = {}
    seg_expect: dict[str, list[str]] = {}
    seg_cuts: dict[str, list[float]] = {}
    if a.episode:
        ep_path = Path(a.episode)
        ep = json.loads(ep_path.read_text(encoding="utf-8"))
        for c in ep.get("characters", []):
            refs[c["id"]] = [str(p if (p.is_absolute() or p.exists()) else ep_path.parent / p)      # JSON folder, or project root
                             for p in map(Path, c.get("reference_images", []))]
        for s in ep.get("segments", []):
            seg_expect[s["id"]] = list(s.get("character_ids", []))
            seg_cuts[s["id"]] = [float(sh.get("start", 0)) for sh in s.get("shots", []) if float(sh.get("start", 0)) > 0]
    for item in a.ref or []:
        cid, _, paths = item.partition("=")
        refs.setdefault(cid.strip(), []).extend(p.strip() for p in paths.split(",") if p.strip())
    if not refs:
        sys.exit("no references: give --episode or at least one --ref id=path")
    bible, notes = {}, []
    for cid, paths in refs.items():
        gallery = []
        for p in paths:
            pp = Path(p)
            if not pp.exists():
                notes.append(f"{cid}: reference missing: {p}")
                continue
            faces, _ = engine.faces(imread(pp))
            if not faces:
                notes.append(f"{cid}: no face detected in reference {pp.name} (profile / back view / stylised?)")
            gallery.extend(f["feat"] for f in faces[:6])
        if gallery:
            bible[cid] = gallery
        else:
            notes.append(f"{cid}: no usable reference face - this character cannot be checked")
    return bible, seg_expect, seg_cuts, notes


def calibrate(bible: dict[str, list], a) -> dict:
    same, cross = {}, []
    ids = list(bible)
    for cid in ids:
        g = bible[cid]
        pairs = [float(g[i] @ g[j]) for i in range(len(g)) for j in range(i + 1, len(g))]
        if pairs:
            same[cid] = {"min": round(min(pairs), 3), "median": round(float(np.median(pairs)), 3), "pairs": len(pairs)}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            s = max(float(x @ y) for x in bible[ids[i]] for y in bible[ids[j]])
            cross.append({"a": ids[i], "b": ids[j], "max_sim": round(s, 3)})
    warnings = []
    for c in cross:
        lim = min([same[k]["min"] for k in (c["a"], c["b"]) if k in same] or [a.match])
        if c["max_sim"] >= a.borderline or c["max_sim"] >= lim:
            warnings.append(f"bible_ambiguous: {c['a']} vs {c['b']} similarity {c['max_sim']} "
                            f"(same-identity threshold {a.borderline}) - redesign one of them, do not tune thresholds")
    for cid, st in same.items():
        if st["min"] < a.borderline:
            warnings.append(f"bible_inconsistent: {cid}'s own references disagree (min {st['min']}) - "
                            f"one reference is probably a different face or too small")
    return {"same": same, "cross": cross, "warnings": warnings}


# ----------------------------------------------------------------------------- targets

def expected_for(path: Path, seg_expect: dict[str, list[str]], override: list[str], everyone: list[str]):
    if override:
        return override, None
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", str(path)) if t]
    hit = None
    for t in tokens:
        if t in seg_expect:
            hit = t
    if hit:
        return seg_expect[hit], hit
    return everyone, None


def draw(img, frame_result: dict):
    out = img.copy()
    colour = {"pass": (60, 180, 60), "warn": (0, 190, 255), "fail": (40, 40, 230)}
    for f in frame_result["faces"]:
        x, y, w, h = f["box"]
        col = colour.get(f.get("verdict"), (160, 160, 160))
        cv2.rectangle(out, (x, y), (x + w, y + h), col, max(2, out.shape[1] // 480))
        label = f"{f.get('flag') or f.get('assigned') or '?'} {f.get('sim')}"
        cv2.putText(out, label, (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, max(0.5, out.shape[1] / 1600), col, 2)
    return out


def sheet(frames: list, cols: int = 4, width: int = 480):
    if not frames:
        return None
    thumbs = []
    for f in frames:
        h = int(f.shape[0] * width / f.shape[1])
        thumbs.append(cv2.resize(f, (width, h)))
    h = max(t.shape[0] for t in thumbs)
    thumbs = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(20, 20, 20)) for t in thumbs]
    cols = min(cols, len(thumbs))
    while len(thumbs) % cols:
        thumbs.append(np.full_like(thumbs[0], 20))
    return np.vstack([np.hstack(thumbs[i:i + cols]) for i in range(0, len(thumbs), cols)])


def pct(vals: list[float], q: float) -> float:
    return round(float(np.percentile(vals, q)), 3)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--episode", help="episode JSON: references and per-segment expected characters")
    ap.add_argument("--ref", action="append", help="id=path[,path...] (repeatable); adds to / replaces --episode references")
    ap.add_argument("--targets", nargs="+", required=True, help="image / video paths or globs (** allowed)")
    ap.add_argument("--expect", help="comma-separated character ids expected in every target (overrides the storyboard)")
    ap.add_argument("--out", required=True, help="output directory for report.json, summary.csv and box sheets")
    ap.add_argument("--match", type=float, default=0.55, help="delivery bar (strict: 0.65)")
    ap.add_argument("--borderline", type=float, default=0.363, help="OpenCV SFace same-identity cosine threshold")
    ap.add_argument("--det-score", type=float, default=0.6)
    ap.add_argument("--min-face", type=int, default=40, help="ignore faces whose short side is below this many pixels")
    ap.add_argument("--fps", type=float, default=2.0, help="video sampling rate")
    ap.add_argument("--freeze-tail", type=float, default=1.0, help="seconds of declared end-freeze to skip in clips")
    ap.add_argument("--models-dir", default=str(Path.home() / ".cache" / "h3-skill" / "models"))
    ap.add_argument("--offline", action="store_true", help="never download models")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any target fails")
    a = ap.parse_args()

    if a.episode and not a.ref:           # look before downloading models: no pictures means there is nothing to compare with
        ep_chars = json.loads(Path(a.episode).read_text(encoding="utf-8")).get("characters", [])
        if not any(c.get("reference_images") for c in ep_chars):
            sys.exit("no character in this episode has a reference picture: this gate has nothing to compare with - skip it "
                     "(identity then rests on the eye check of the contact sheets)")
    engine = FaceEngine(ensure_models(Path(a.models_dir), a.offline), a.det_score, a.min_face)
    bible, seg_expect, seg_cuts, notes = load_bible(a, engine)
    if not bible:
        for n in notes:
            print("NOTE ", n)
        sys.exit("no usable reference face for any character: references must show a detectable, reasonably frontal "
                 "face (>= --min-face px). Stylised / anime boards are not supported by this track.")
    cal = calibrate(bible, a)
    override = [c.strip() for c in (a.expect or "").split(",") if c.strip()]
    unknown = [c for c in override if c not in bible]
    if unknown:
        notes.append(f"--expect ids without usable references: {unknown}")

    paths: list[Path] = []
    for pat in a.targets:
        hits = sorted(glob.glob(pat, recursive=True)) or ([pat] if Path(pat).exists() else [])
        paths.extend(Path(h) for h in hits if Path(h).suffix.lower() in IMAGE_EXT | VIDEO_EXT)
    live = [p for p in paths if not any(part.startswith("_prev_") for part in p.parts)]      # superseded takes kept by comfy_submit.py
    if len(live) != len(paths):
        print(f"note: {len(paths) - len(live)} file(s) in _prev_* folders skipped")
    paths = live
    if not paths:
        sys.exit("no image / video targets matched")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    results, any_fail = [], False
    for p in paths:
        exp, seg = expected_for(p, seg_expect, override, list(bible))
        entry = {"target": str(p), "segment": seg, "expected": exp}
        boxed = []
        try:
            if p.suffix.lower() in IMAGE_EXT:
                img = imread(p)
                faces, dropped = engine.faces(img)
                fr = judge_frame(faces, bible, exp, a)
                entry.update({"kind": "image", "dropped_small_faces": dropped, **fr})
                entry["verdict"] = "pass" if fr["verdict"] == "none" else fr["verdict"]
                boxed.append(draw(img, fr))
            else:
                dur = video_duration(p)
                frames = []
                with tempfile.TemporaryDirectory() as td:
                    for t in sample_times(dur, a.fps, a.freeze_tail, seg_cuts.get(seg, []) if seg else []):
                        img = grab_frame(p, t, Path(td))
                        if img is None:
                            continue
                        faces, dropped = engine.faces(img)
                        fr = judge_frame(faces, bible, exp, a)
                        frames.append({"t": t, "dropped_small_faces": dropped, **fr})
                        if len(boxed) < 12 and fr["faces"]:
                            boxed.append(draw(img, fr))
                face_frames = [f for f in frames if f["faces"]]
                per_char: dict[str, list[tuple[float, float]]] = {}
                for f in face_frames:
                    for row in f["faces"]:
                        if row.get("assigned") and row.get("sim") is not None:
                            per_char.setdefault(row["assigned"], []).append((f["t"], row["sim"]))
                stats = {}
                for c, vals in per_char.items():
                    sims = [s for _, s in vals]
                    bad = [t for t, s in vals if s < a.borderline]
                    stats[c] = {"frames": len(sims), "min": round(min(sims), 3), "p10": pct(sims, 10),
                                "median": pct(sims, 50), "fail_fraction": round(len(bad) / len(sims), 3),
                                "first_fail_t": bad[0] if bad else None}
                n_fail = sum(1 for f in face_frames if f["verdict"] == "fail")
                frac = n_fail / len(face_frames) if face_frames else 0.0
                first_bad = bool(face_frames) and face_frames[0]["verdict"] == "fail"
                verdict = "fail" if (frac > 0.2 or first_bad) else \
                    "warn" if any(f["verdict"] in ("warn", "fail") for f in face_frames) else "pass"
                flags = sorted({fl for f in frames for fl in f["flags"] if not fl.startswith("absent:")})
                if not face_frames:
                    flags = ["no_usable_face"]
                entry.update({"kind": "video", "duration": round(dur, 3), "sampled_frames": len(frames),
                              "face_frames": len(face_frames), "fail_frame_fraction": round(frac, 3),
                              "first_face_frame_failed": first_bad, "per_character": stats, "flags": flags,
                              "verdict": verdict, "frames": frames})
        except Exception as e:  # noqa: BLE001  (one unreadable file must not stop the batch)
            entry.update({"kind": "error", "verdict": "error", "error": str(e)[:300], "flags": ["unreadable"]})
        img_sheet = sheet(boxed)
        if img_sheet is not None:
            sp = out / "sheets" / (re.sub(r"[^A-Za-z0-9_.-]+", "_", str(p.with_suffix("")))[-120:] + "_faces.jpg")
            imwrite(sp, img_sheet)
            entry["sheet"] = str(sp)
        any_fail |= entry["verdict"] == "fail"
        results.append(entry)
        extra = ""
        if entry.get("kind") == "video":
            extra = f" face_frames={entry['face_frames']}/{entry['sampled_frames']} fail_frac={entry['fail_frame_fraction']}"
        print(f"{entry['verdict']:5s} {p}{extra} {' '.join(entry.get('flags', []))}")

    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k != "feat"}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o

    report = {"embedder": "opencv-sface (cosine)", "detector": "opencv-yunet",
              "thresholds": {"match": a.match, "borderline": a.borderline, "det_score": a.det_score, "min_face_px": a.min_face},
              "characters": {c: len(g) for c, g in bible.items()}, "calibration": cal, "notes": notes,
              "targets": strip(results)}
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "summary.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["target", "segment", "kind", "verdict", "expected", "flags", "per_character_min", "per_character_median"])
        for e in results:
            pc = e.get("per_character", {})
            if e.get("kind") == "image":
                pc = {r["assigned"]: {"min": r.get("sim"), "median": r.get("sim")} for r in e.get("faces", []) if r.get("assigned")}
            w.writerow([e["target"], e.get("segment") or "", e.get("kind"), e["verdict"], " ".join(e.get("expected", [])),
                        " ".join(e.get("flags", [])),
                        " ".join(f"{c}={v['min']}" for c, v in pc.items()),
                        " ".join(f"{c}={v['median']}" for c, v in pc.items())])
    for w_ in cal["warnings"] + notes:
        print("NOTE ", w_)
    counts = {k: sum(1 for e in results if e["verdict"] == k) for k in ("pass", "warn", "fail", "error")}
    print(f"{len(results)} target(s): {counts}  -> {out / 'report.json'}")
    sys.exit(1 if (a.strict and any_fail) else 0)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
