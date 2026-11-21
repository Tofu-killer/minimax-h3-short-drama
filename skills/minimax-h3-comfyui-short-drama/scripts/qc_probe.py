#!/usr/bin/env python3
"""Technical QC for generated clips: container facts, audio peak, black / frozen spans, and whether the
clip cut where the storyboard said it should (needs ffprobe / ffmpeg on PATH; standard library only).

    python3 qc_probe.py "takes/ep01/s03/*.mp4" --expect-seconds 10 --expect-size 1344x768 --freeze-tail 1.0
    python3 qc_probe.py "takes/ep01/**/*.mp4" --episode episodes/ep01.json --freeze-tail 1.0 --out qc/probe

Hard checks (FAIL, exit 1): no video / no audio stream, wrong size (with --expect-size), wrong frame rate,
duration off by more than --tolerance, clipped audio (samples stuck at full scale), frozen span > 1 s or
black span > 0.25 s outside the declared freeze tail.
Warnings: a sample peak above -1 dBFS that is not clipped (the mix re-levels it), a picture whose aspect does
not match the storyboard's ratio, caption-like text burned into the lower third (needs numpy; a heuristic
for white text with a dark outline - see h3lib/signals.py).
--freeze-tail N is the length of the declared end freeze. With --episode the last N seconds are left unchecked
only on segments whose last shot has "end_hold": true - the same rule make_edl.py uses to cut them off. On
every other segment that second goes into the cut, so it is checked. (--freeze-tail-all skips it everywhere;
without --episode it is skipped on every clip.)
Shot check (WARN; FAIL with --strict-cuts): hard cuts found in the picture are compared with the shot start
times - from --episode (the segment id is read from the path: a folder or file-name token equal to it; its
duration is used as --expect-seconds too) or from --shots 0,3.5,7.2. A missing cut means H3 ran two shots
together, an extra cut means it invented one; both are storyboard failures, re-rolling the seed rarely
fixes them. Also reported: an abrupt picture change in the first / last 8 frames (a stray frame that will
flash at the join - trim it), and a near-still clip (median frame change below --min-motion).
The cut detector is calibrated on a small amount of footage (see h3lib/signals.py); look at the contact
sheet before acting on a WARN.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
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

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}


RATIOS = {"21:9": 21 / 9, "16:9": 16 / 9, "4:3": 4 / 3, "1:1": 1.0, "3:4": 3 / 4, "9:16": 9 / 16}


def declared_hold(seg: dict | None) -> bool:
    """Does the storyboard say this segment ends in a freeze that is cut off later? (last shot has end_hold)"""
    shots = (seg or {}).get("shots") or []
    return bool(shots and shots[-1].get("end_hold"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+", help="clips or glob patterns (quote them on Windows)")
    ap.add_argument("--episode", help="storyboard JSON: expected duration and shot starts per segment")
    ap.add_argument("--segment", help="force this segment id for every file (when paths carry no id)")
    ap.add_argument("--shots", help="shot start times in seconds, e.g. 0,3.5,7.2 (instead of --episode)")
    ap.add_argument("--expect-seconds", type=float)
    ap.add_argument("--expect-size", help="WxH")
    ap.add_argument("--expect-fps", type=float, default=24.0)
    ap.add_argument("--tolerance", type=float, default=0.6, help="seconds allowed on the duration")
    ap.add_argument("--cut-tolerance", type=float, default=0.5, help="seconds allowed between a planned and a found cut")
    ap.add_argument("--freeze-tail", type=float, default=0.0,
                    help="length of the declared end freeze (skill default 1.0). With --episode it is skipped only on segments "
                         "whose last shot has end_hold; without a storyboard it is skipped on every clip")
    ap.add_argument("--freeze-tail-all", action="store_true", help="skip the freeze tail on every clip even with --episode")
    ap.add_argument("--min-motion", type=float, default=1.2,
                    help="warn below this median frame change (240 px grey difference; action >= 2.5, close-up acting >= 1.8)")
    ap.add_argument("--strict-cuts", action="store_true", help="a shot-count mismatch fails the clip")
    ap.add_argument("--no-cuts", action="store_true", help="skip cut detection (faster)")
    ap.add_argument("--no-text", action="store_true", help="skip the burned-in text check (it needs numpy and is skipped without it)")
    ap.add_argument("--out", help="folder for probe_report.json")
    a = ap.parse_args()

    paths: list[Path] = []
    for pat in a.files:
        hits = sorted(glob.glob(pat, recursive=True)) or ([pat] if Path(pat).exists() else [])
        paths += [Path(h) for h in hits if Path(h).suffix.lower() in VIDEO_EXT]
    if not paths:
        sys.exit("no clips matched")
    segs, ep, ep_ratio = {}, {}, None
    if a.episode:
        ep = json.loads(Path(a.episode).read_text(encoding="utf-8"))
        segs = {s["id"]: s for s in ep["segments"]}
        ep_ratio = RATIOS.get(str(ep.get("ratio", "")))
    manual_shots = [float(x) for x in a.shots.split(",")] if a.shots else None

    rows, bad = [], 0
    for p in paths:
        info = signals.probe(p)
        row = {"file": str(p), "size": f"{info['width']}x{info['height']}", "fps": round(info["fps"], 3),
               "duration": round(info["duration"], 3), "audio": info["has_audio"]}
        problems, warns = [], []
        if not info["width"]:
            print(f"FAIL {p.name}: no video stream")
            rows.append({**row, "verdict": "fail", "problems": ["no video stream"]})
            bad += 1
            continue
        sid = a.segment
        if not sid and segs:
            for tok in re.split(r"[^A-Za-z0-9]+", str(p)):
                if tok in segs:
                    sid = tok
        seg = segs.get(sid) if sid else None
        if segs and not seg:
            warns.append("no segment id in the path: storyboard checks skipped (use --segment)")
        expect_s = a.expect_seconds if a.expect_seconds else (float(seg["duration"]) if seg else None)
        dur = info["duration"]
        if expect_s and abs(dur - expect_s) > a.tolerance:
            problems.append(f"duration {dur:.2f}s != {expect_s:g}")
        if a.expect_size and row["size"] != a.expect_size:
            problems.append(f"size {row['size']} != {a.expect_size}")
        if abs(info["fps"] - a.expect_fps) > 0.5:
            problems.append(f"fps {info['fps']:.2f} != {a.expect_fps:g}")
        clip = signals.clipping(p) if info["has_audio"] else None
        peak = clip["peak_db"] if clip else None
        row["peak_db"] = peak
        if not info["has_audio"]:
            problems.append("no audio track")
        elif clip and clip["clipped"]:
            problems.append(f"audio is clipped (peak {peak} dB, samples stuck at full scale) - the distortion is baked in: re-roll")
        elif peak is not None and peak > -1.0:
            warns.append(f"audio peak {peak} dB is hot but not clipped - fine as a take, mix_episode.py re-levels it")
        if not a.expect_size and ep_ratio and info["height"]:
            got = info["width"] / info["height"]
            if abs(got / ep_ratio - 1) > 0.03:
                warns.append(f"picture is {row['size']} ({got:.2f}:1) but the storyboard says {ep.get('ratio')} - it will be cropped or padded at assembly")
        # the last second is only skipped where the storyboard declares a freeze tail (same rule as make_edl.py):
        # on any other segment that second goes into the cut and has to be checked
        hold = a.freeze_tail > 0 and (a.freeze_tail_all or seg is None and not segs or declared_hold(seg))
        usable = dur - a.freeze_tail if hold else None
        row["freeze_tail_excluded"] = a.freeze_tail if hold else 0
        bf = signals.black_and_freeze(p, usable)
        row.update(bf)
        if bf["freeze"]:
            problems.append("frozen " + ", ".join(f"{s:.2f}-{e:.2f}s" for s, e in bf["freeze"]))
        if bf["black"]:
            problems.append("black " + ", ".join(f"{s:.2f}-{e:.2f}s" for s, e in bf["black"]))
        text = None if a.no_text else signals.burned_text(p, usable)
        if text:
            row["burned_text"] = text
            warns.append("text is burned into the lower third at " + ", ".join(f"{s0:.1f}-{s1:.1f}s" for s0, s1 in text)
                         + " (F-BURN-TEXT): trim it if it is a flash, otherwise regenerate - and do not burn subtitles over it")
        row["motion"] = signals.motion(p, usable)
        if row["motion"] is not None and row["motion"] < a.min_motion:
            warns.append(f"motion {row['motion']} is below {a.min_motion:g}: close to a still picture - check it is not a slideshow take")
        if not a.no_cuts:
            det = signals.detect_cuts(p, info["fps"], usable)
            row["cuts"] = [c["t"] for c in det["cuts"]]
            row["edge_jumps"] = [e["t"] for e in det["edge_jumps"]]
            for e in det["edge_jumps"]:
                where = "head" if e["t"] < 1 else "tail"
                warns.append(f"abrupt picture change at {e['t']:.3f}s ({where}): a stray frame will flash at the join - trim it")
            shots = manual_shots if manual_shots is not None else ([float(sh["start"]) for sh in seg["shots"]] if seg else None)
            if shots is not None:
                limit = usable if usable else dur
                expected = [t for t in shots if 0 < t < limit]
                chk = signals.match_cuts(expected, row["cuts"], a.cut_tolerance)
                row["cut_check"] = chk
                if not chk["ok"]:
                    msg = f"shots: planned {len(expected) + 1}, found {len(row['cuts']) + 1}"
                    if chk["missing"]:
                        msg += f"; no cut near {', '.join(f'{t:g}s' for t in chk['missing'])}"
                    if chk["extra"]:
                        msg += f"; unplanned cut at {', '.join(f'{t:g}s' for t in chk['extra'])}"
                    (problems if a.strict_cuts else warns).append(msg)
                late = [m for m in chk["matched"] if abs(m["offset"]) > 0.3]
                if late:
                    warns.append("cut timing off: " + ", ".join(f"{m['expected']:g}s -> {m['detected']:g}s" for m in late))
        verdict = "fail" if problems else "warn" if warns else "ok"
        bad += bool(problems)
        row.update({"segment": sid, "verdict": verdict, "problems": problems, "warnings": warns})
        rows.append(row)
        cuts_txt = ("" if a.no_cuts else f" cuts={row['cuts']}") + (f" (last {a.freeze_tail:g}s = declared freeze, not checked)" if hold else "")
        print(f"{verdict.upper():4s} {p.name}: {row['size']} {info['fps']:.0f}fps {dur:.2f}s audio={'yes' if info['has_audio'] else 'no'} "
              f"peak={peak} motion={row['motion']}{cuts_txt}" + ("  " + "; ".join(problems + warns) if problems or warns else ""))
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "probe_report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"report -> {out / 'probe_report.json'}")
    counts = {k: sum(1 for r in rows if r["verdict"] == k) for k in ("ok", "warn", "fail")}
    print(f"{len(rows)} clip(s): {counts}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
