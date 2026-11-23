#!/usr/bin/env python3
"""Measure voice drift before fixing it: median pitch of every spoken line, compared per character.

    python3 voice_check.py edit/ep01.edl.json --out qc/voice
    python3 voice_check.py edit/ep01.edl.json --episode episodes/ep01.json --out qc/voice      # use voice_reference files as anchors
    python3 voice_check.py edit/ep01.edl.json --anchor lin_lan=bible/voices/lin_lan.wav --out qc/voice

H3 gives a character a slightly different voice in every take. Converting every line with a voice changer
damages the lines that were fine, so measure first: for each line with times in the EDL (run
retime_subtitles.py before this) the script takes the sound that will be in the cut, finds the voiced
frames and their median fundamental frequency, and compares it with the character's anchor - the
`voice_reference` from the storyboard, a file given with --anchor, or else the median of that character's
own lines in this episode.

    |offset| <= 0.5 semitone   same voice as far as pitch can tell - leave it
    0.5 - 2 semitones          drift: listen; convert only if the timbre also sounds off
    > 2 semitones              a different register: re-roll the take, or convert and check by ear

Pitch is only one cue. A shouted or whispered line is legitimately higher or lower. Music or loud effects
under a line scatter the estimate; such lines are reported as `unreadable` rather than given a number (on a
real H3 film with effects under the dialogue only one line in five was readable - measure on separated vocal
stems when the mix is busy). Use the table to decide which lines to LISTEN to, not as a verdict.

Needs ffmpeg and numpy.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path
from statistics import median

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import edl as edl_lib  # noqa: E402


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()

SR, WIN, HOP, FMIN, FMAX = 16000, 1024, 256, 70.0, 420.0


def pcm(path: Path, start: float | None = None, end: float | None = None):
    import numpy as np
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vn"]
    if start is not None and end is not None:
        cmd += ["-af", f"atrim=start={max(0.0, start):.4f}:end={end:.4f},asetpts=PTS-STARTPTS"]
    cmd += ["-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def f0_track(x) -> tuple[list[float], int]:
    """-> (f0 in Hz of every voiced frame, number of frames analysed). Autocorrelation per frame; the shortest
    lag whose peak is within 10% of the best one is taken, which avoids landing an octave low."""
    import numpy as np
    if len(x) < WIN:
        return [], 0
    lo, hi = int(SR / FMAX), int(SR / FMIN)
    win = np.hanning(WIN).astype(np.float32)
    frames = [x[i:i + WIN] for i in range(0, len(x) - WIN + 1, HOP)]
    rms = np.array([float(np.sqrt(np.mean(f * f))) for f in frames])
    gate = max(0.01, 0.15 * float(np.percentile(rms, 95))) if len(rms) else 1.0
    out = []
    for f, e in zip(frames, rms):
        if e < gate:
            continue
        w = (f - f.mean()) * win
        spec = np.fft.rfft(w, 2 * WIN)
        ac = np.fft.irfft(spec * np.conj(spec))[:WIN]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        seg = ac[lo:hi]
        k = int(np.argmax(seg))
        best = float(seg[k])
        if best < 0.6:                                   # not periodic enough: unvoiced, noise or music
            continue
        ok = np.where(seg >= 0.9 * best)[0]
        cand = int(ok[0])                                # shortest lag that is nearly as good
        while cand + 1 < len(seg) and seg[cand + 1] > seg[cand]:
            cand += 1                                    # climb to that peak's top
        out.append(SR / (lo + cand))
    return out, len(frames)


MIN_VOICED, MAX_IQR = 20, 4.0      # >= 20 voiced frames (~0.3 s) and an interquartile range <= 4 semitones


def summarise(f0: list[float], n_frames: int) -> dict:
    """A spoken line keeps its pitch within a few semitones; music, effects or noise under it scatter the
    estimates over an octave. Lines that are too short or too scattered are reported as unreadable instead of
    being given a number that means nothing (checked against a second estimator on real H3 takes)."""
    base = {"voiced_frames": len(f0), "voiced_ratio": round(len(f0) / n_frames, 2) if n_frames else 0.0}
    if len(f0) < MIN_VOICED:
        return {"f0_hz": None, "iqr_semitones": None, "why": "too few voiced frames", **base}
    srt = sorted(f0)
    q1, q3 = srt[len(srt) // 4], srt[(3 * len(srt)) // 4]
    iqr = 12.0 * math.log2(q3 / q1)
    if iqr > MAX_IQR:
        return {"f0_hz": None, "iqr_semitones": round(iqr, 1), "why": f"pitch scattered over {iqr:.0f} semitones", **base}
    return {"f0_hz": round(float(median(f0)), 1), "iqr_semitones": round(iqr, 1), "why": "", **base}


def semitones(f: float, ref: float) -> float:
    return 12.0 * math.log2(f / ref)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--episode", help="storyboard JSON: characters[].voice_reference become the anchors")
    ap.add_argument("--anchor", action="append", default=[], help="speaker_id=path to an approved voice sample (repeatable)")
    ap.add_argument("--warn", type=float, default=0.5, help="semitones of offset reported as drift")
    ap.add_argument("--fail", type=float, default=2.0, help="semitones of offset reported as a different register")
    a = ap.parse_args()
    try:
        import numpy  # noqa: F401
    except ImportError:
        sys.exit("numpy is not installed: pip install numpy")

    edl_path = Path(a.edl)
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    fps, plan, _total = edl_lib.timeline(edl)
    anchors: dict[str, Path] = {}
    if a.episode:
        ep_path = Path(a.episode)
        for c in json.loads(ep_path.read_text(encoding="utf-8")).get("characters", []):
            if c.get("voice_reference"):
                q = Path(c["voice_reference"])
                anchors[c["id"]] = q if q.is_absolute() or q.exists() else ep_path.parent / q
    for item in a.anchor:
        k, _, v = item.partition("=")
        anchors[k] = Path(v)

    rows = []
    for p in plan:
        seg = p["seg"]
        if not seg.get("audio"):
            continue
        src = edl_lib.resolve(edl_path, seg["video"] if seg["audio"] == "native" else seg["audio"])
        for i, ln in enumerate(seg.get("lines") or []):
            if ln.get("start") is None or ln.get("end") is None or ln.get("speaker") in (None, "narrator"):
                continue
            t0, t1 = p["src_in"] + float(ln["start"]), p["src_in"] + float(ln["end"])
            f0, n = f0_track(pcm(src, t0, t1))
            rows.append({"segment": p["id"], "line": i, "speaker": ln["speaker"], "name": ln.get("name", ln["speaker"]),
                         "text": ln["text"], "timeline_s": round(p["start_s"] + float(ln["start"]), 2), **summarise(f0, n)})
    if not rows:
        sys.exit("no timed lines in the EDL - run retime_subtitles.py first")

    refs: dict[str, dict] = {}
    for spk in sorted({r["speaker"] for r in rows}):
        own = [r["f0_hz"] for r in rows if r["speaker"] == spk and r["f0_hz"]]
        if spk in anchors and anchors[spk].exists():
            f0, n = f0_track(pcm(anchors[spk]))
            s = summarise(f0, n)
            if s["f0_hz"]:
                refs[spk] = {"hz": s["f0_hz"], "source": f"anchor {anchors[spk]}"}
                continue
            print(f"NOTE {spk}: could not read a pitch from the anchor {anchors[spk]} - using the episode median instead")
        elif spk in anchors:
            print(f"NOTE {spk}: anchor file not found: {anchors[spk]} - using the episode median instead")
        if own:
            refs[spk] = {"hz": round(float(median(own)), 1), "source": f"median of {len(own)} line(s) in this episode"}

    for r in rows:
        ref = refs.get(r["speaker"])
        if not r["f0_hz"]:
            r.update({"offset_semitones": None, "verdict": "unreadable",
                      "note": f"{r.get('why') or 'no clear pitch'}: music or effects under the line, a whisper, or a very short line"})
        elif not ref:
            r.update({"offset_semitones": None, "verdict": "no_reference", "note": ""})
        else:
            off = round(semitones(r["f0_hz"], ref["hz"]), 2)
            verdict = "ok" if abs(off) <= a.warn else "drift" if abs(off) <= a.fail else "different_register"
            r.update({"offset_semitones": off, "verdict": verdict, "note": ""})

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    spread = {}
    for spk in refs:
        offs = [r["offset_semitones"] for r in rows if r["speaker"] == spk and r["offset_semitones"] is not None]
        if offs:
            spread[spk] = round(max(offs) - min(offs), 2)
    (out / "voice_report.json").write_text(json.dumps({"references": refs, "spread_semitones": spread, "lines": rows},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "voice_summary.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["segment", "speaker", "timeline_s", "f0_hz", "offset_semitones", "voiced_ratio", "verdict", "text"])
        for r in rows:
            w.writerow([r["segment"], r["name"], r["timeline_s"], r["f0_hz"] or "", "" if r["offset_semitones"] is None else r["offset_semitones"],
                        r["voiced_ratio"], r["verdict"], r["text"]])
    for spk, ref in refs.items():
        print(f"{spk}: reference {ref['hz']} Hz ({ref['source']})" + (f", spread across lines {spread[spk]} semitones" if spk in spread else ""))
    for r in rows:
        off = "   n/a" if r["offset_semitones"] is None else f"{r['offset_semitones']:+6.2f}"
        print(f"  {r['verdict']:18s} {r['segment']:>5} {r['name']:<8} {str(r['f0_hz'] or '-'):>6} Hz  {off} st  voiced {r['voiced_ratio']:.0%}  {r['text'][:16]}"
              + (f"  ({r['note']})" if r["note"] else ""))
    counts = {k: sum(1 for r in rows if r["verdict"] == k) for k in ("ok", "drift", "different_register", "unreadable", "no_reference")}
    print(f"{len(rows)} line(s): {counts} -> {out / 'voice_report.json'}")
    if counts["unreadable"]:
        print("unreadable lines have no usable pitch in the mixed sound: separate the dialogue first (references/audio-and-post.md, "
              "section 2 step 3), point the EDL's `audio` at the vocal stem and run this again - or just listen to them")
    if any(src["source"].startswith("median") for src in refs.values()):
        print("no anchor for some characters: offsets are relative to that character's own lines in this episode - "
              "keep an approved sample (>= 6 s) per lead in bible/voices/ to compare across episodes")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
