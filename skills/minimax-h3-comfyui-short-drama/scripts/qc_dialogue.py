#!/usr/bin/env python3
"""Dialogue QC for takes: was every locked line actually spoken, completely, once, and when?

    python3 qc_dialogue.py --episode episodes/ep01.json --targets "takes/ep01/**/*.mp4" --out qc/dialogue
    python3 qc_dialogue.py --episode episodes/ep01.json --targets takes/ep01/s03/*.mp4 --out qc/dialogue --strict

The segment a take belongs to is read from its path (a folder or file-name token equal to the segment id).
Each take is transcribed WITHOUT any text hint (a hinted recogniser "hears" lines that were never spoken)
and compared with the storyboard lines by sound (pinyin) when pypinyin is installed.

Checks (thresholds from the production notes collected in references/qc-and-assembly.md):
  F-DIALOGUE-TEXT   overall similarity < 0.72
  head_missing / tail_missing   none of the first / last 3 characters of a line was heard
  inserted_words    recognised length > locked length x 1.15 + 2 characters (repeats, improvised words)
  unexpected_speech a segment with no dialogue contains >= 2 recognised words with no_speech_prob < 0.5
  late_start (warn) first word later than --late-start seconds (default 2.5): dead air to trim with in_frame in
                    the EDL, unless the acting before the line is wanted
  ends_..._before_the_end / ..._into_the_declared_freeze (warn)
                    the last word stops less than 0.2 s before the usable end of the clip (the clip end, or the
                    start of the freeze tail on segments that declare end_hold): the line may be cut off
  low_confidence (warn)  the recogniser was unsure (mean word probability < 0.65) - listen
  short_line (warn)      a line of one or two characters: a match proves little - listen
Word times are pulled to where the voice actually rises and falls (the recogniser tends to start early).
Also reports first / last word time per line and characters per second - make_edl.py and the editor use
those to place cuts.  A failing take should be re-rolled with a NEW seed (speech rhythm follows the seed);
the same failure on two batches means the storyboard / prompt needs changing, not another seed.

Default is advisory (exit 0); --strict exits 1 when any take fails.
Needs ffmpeg/ffprobe + faster-whisper (pypinyin recommended). Use --model large-v3 --device cuda when the GPU is free.
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
from pathlib import Path

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import speech  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".wav", ".flac"}


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--episode", required=True)
    ap.add_argument("--targets", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--segment", help="force this segment id for every target (when paths carry no id)")
    ap.add_argument("--freeze-tail", type=float, default=1.0,
                    help="length of the declared end freeze; only applied to segments whose last shot has end_hold")
    ap.add_argument("--freeze-tail-all", action="store_true", help="treat the last --freeze-tail seconds of every take as freeze")
    ap.add_argument("--late-start", type=float, default=2.5)
    ap.add_argument("--min-similarity", type=float, default=0.72)
    ap.add_argument("--aligner", choices=["faster-whisper", "cmd", "units"], default="faster-whisper")
    ap.add_argument("--model", default="small")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--language", default="zh")
    ap.add_argument("--aligner-cmd")
    ap.add_argument("--units-dir")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    ep = json.loads(Path(a.episode).read_text(encoding="utf-8"))
    names = {c["id"]: c.get("name", c["id"]) for c in ep.get("characters", [])}
    seg_lines, seg_hold = {}, {}
    for s in ep["segments"]:
        seg_lines[s["id"]] = [{"speaker": d["speaker"], "name": names.get(d["speaker"], d["speaker"]), "text": d["text"],
                               "shot": sh["index"]} for sh in s["shots"] for d in sh.get("dialogue", [])]
        seg_hold[s["id"]] = bool(s["shots"] and s["shots"][-1].get("end_hold"))
    paths: list[Path] = []
    for pat in a.targets:
        hits = sorted(glob.glob(pat, recursive=True)) or ([pat] if Path(pat).exists() else [])
        paths.extend(Path(h) for h in hits if Path(h).suffix.lower() in VIDEO_EXT)
    if not paths:
        sys.exit("no targets matched")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, any_fail = [], False
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for p in paths:
            sid = a.segment
            if not sid:
                for tok in re.split(r"[^A-Za-z0-9]+", str(p)):
                    if tok in seg_lines:
                        sid = tok
            if not sid:
                rows.append({"take": str(p), "segment": None, "verdict": "skip", "flags": ["no_segment_id_in_path"]})
                print(f"skip  {p} (no segment id in path; use --segment)")
                continue
            lines = seg_lines[sid]
            dur = duration(p)
            hold = a.freeze_tail > 0 and (seg_hold[sid] or a.freeze_tail_all)     # same rule as make_edl.py / qc_probe.py
            usable = max(0.0, dur - a.freeze_tail) if hold else dur
            wav = tmp / (re.sub(r"[^A-Za-z0-9_]+", "_", str(p))[-80:] + ".wav")
            entry = {"take": str(p), "segment": sid, "duration": round(dur, 3), "expected_lines": len(lines)}
            flags, warns = [], []
            env, hop = None, 0.01
            if not speech.extract_wav(p, wav):
                units, segs = [], []
                if lines:
                    flags.append("no_audio_track")
            else:
                try:
                    env, hop = speech.envelope(wav)
                except ImportError:
                    env = None
                units, segs = speech.get_units(a.aligner, wav, lines or [{"text": ""}], model=a.model, language=a.language,
                                               device=a.device, cmd=a.aligner_cmd, tmp=tmp, bias=False,
                                               units_file=Path(a.units_dir) / f"{p.stem}.units.json" if a.units_dir else None)
            if not lines:
                speechy = [s for s in segs if s["no_speech_prob"] < 0.5]
                heard = "".join(speech.norm(u["text"]) for u in units)
                if len(units) >= 2 and len(heard) >= 2 and (speechy or not segs):
                    flags.append("unexpected_speech")
                entry.update({"heard": heard, "similarity": None})
            else:
                m = speech.map_lines(lines, units)
                per = []
                for ln in m["lines"]:
                    n = len(speech.norm(ln["text"]))
                    if ln["first_s"] is not None and env is not None:       # recogniser times drift early: pull them to the voice
                        ln["first_s"], ln["last_s"], _shift = speech.refine_span(env, hop, ln["first_s"], ln["last_s"])
                    span = (ln["last_s"] - ln["first_s"]) if ln["first_s"] is not None else None
                    conf = ln.get("confidence")
                    if ln["first_s"] is not None and conf is not None and conf < 0.65:
                        warns.append(f"low_confidence:{ln['text'][:8]}")
                    elif ln["first_s"] is not None and n <= 2:
                        warns.append(f"short_line:{ln['text'][:8]}")
                    per.append({"speaker": ln["name"], "text": ln["text"], "coverage": ln["coverage"], "confidence": conf,
                                "first_word_s": ln["first_s"], "last_word_s": ln["last_s"],
                                "chars_per_s": round(n / span, 2) if span and span > 0.2 else None,
                                "head_missing": ln["head_missing"], "tail_missing": ln["tail_missing"]})
                    if ln["first_s"] is None:
                        flags.append(f"line_not_heard:{ln['text'][:8]}")
                    else:
                        if ln["head_missing"]:
                            flags.append(f"head_missing:{ln['text'][:8]}")
                        if ln["tail_missing"]:
                            flags.append(f"tail_missing:{ln['text'][:8]}")
                if m["similarity"] < a.min_similarity:
                    flags.append("F-DIALOGUE-TEXT")
                if m["hyp_chars"] > m["ref_chars"] * 1.15 + 2:
                    flags.append("inserted_words")
                firsts = [x["first_word_s"] for x in per if x["first_word_s"] is not None]
                lasts = [x["last_word_s"] for x in per if x["last_word_s"] is not None]
                if firsts and firsts[0] > a.late_start:
                    warns.append(f"late_start:{firsts[0]:.2f}s")
                if lasts and usable and usable - lasts[-1] < 0.2:
                    gap = usable - lasts[-1]
                    warns.append(f"ends_{abs(gap):.2f}s_{'into_the_declared_freeze' if hold and gap < 0 else 'before_the_end' if gap >= 0 else 'past_the_end'}")
                entry.update({"similarity": m["similarity"], "heard": m["hyp_text"], "locked_chars": m["ref_chars"],
                              "heard_chars": m["hyp_chars"], "inserted_chars": m["inserted_chars"], "lines": per,
                              "first_word_s": firsts[0] if firsts else None, "last_word_s": lasts[-1] if lasts else None,
                              "matching": m["matching"]})
            verdict = "fail" if flags else "warn" if warns else "pass"
            entry.update({"verdict": verdict, "flags": flags + warns})
            any_fail |= verdict == "fail"
            rows.append(entry)
            sim = "" if entry.get("similarity") is None else f" sim={entry['similarity']}"
            print(f"{verdict:5s} {p} [{sid}]{sim} heard={entry.get('heard', '')!r} {' '.join(entry['flags'])}")

    (out / "dialogue_report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "dialogue_summary.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["take", "segment", "verdict", "similarity", "first_word_s", "last_word_s", "heard", "flags"])
        for r in rows:
            w.writerow([r["take"], r.get("segment") or "", r["verdict"], r.get("similarity", ""), r.get("first_word_s", ""),
                        r.get("last_word_s", ""), r.get("heard", ""), " ".join(r.get("flags", []))])
    counts = {k: sum(1 for r in rows if r["verdict"] == k) for k in ("pass", "warn", "fail", "skip")}
    print(f"{len(rows)} take(s): {counts} -> {out / 'dialogue_report.json'}"
          f"  [matching: {'pinyin' if speech.PHONETIC else 'exact characters (pip install pypinyin)'}; model {a.model}]")
    sys.exit(1 if (a.strict and any_fail) else 0)


if __name__ == "__main__":
    main()
