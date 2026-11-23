#!/usr/bin/env python3
"""Subtitles from the locked script: text comes from the EDL lines, only the timing comes from the audio.

    python3 retime_subtitles.py edit/ep01.edl.json --out subs/ep01
    python3 retime_subtitles.py edit/ep01.edl.json --out subs/ep01 --model large-v3 --device cuda --bilingual

For every EDL segment that has dialogue lines it decodes the sound that will actually be in the cut
([in_frame, out_frame) plus the L-cut), gets word timings (faster-whisper by default, or any external
forced aligner via --aligner cmd), matches them to the locked lines (by sound when pypinyin is installed,
so ASR homophone slips do not matter) and writes:

    <out>.srt / <out>.ass     timeline subtitles (ASS: 1080p-scaled style, optional second language line)
    <out>.cues.json           every cue with coverage and review flags
    EDL lines[].start/.end    segment-local times written back (skip with --no-write-back)

Timing rules: in = first word - 0.08 s, out = last word + 0.25 s, at least 0.8 s, reading speed capped at
9 characters per second, >= 2 frames between cues, everything snapped to frames.
A recogniser's word times drift (on real H3 takes whisper-small put the first word 0.3-1.2 s before the voice),
so each line's start and end are pulled inwards to where the speech band actually rises and falls
(--no-refine turns that off). It is still an estimate: watch the result once.

To correct a cue by hand, edit that line's "start" / "end" in the EDL (seconds from the segment's in point)
and add "locked": true - later runs keep it and only rewrite the files.
Lines whose words were mostly not heard get `needs_review` (not_heard / low_coverage) and a fallback slot
instead of being dropped; a line whose last word touches the out point gets `ends_at_cut` (move out_frame
later in the EDL, or rely on the L-cut and listen). Run qc_dialogue.py on the takes first if many lines
end up flagged.

Needs ffmpeg/ffprobe; faster-whisper for the default aligner (pypinyin optional but recommended for Chinese).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True      # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import edl as edl_lib  # noqa: E402
import signals  # noqa: E402
import speech  # noqa: E402


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()

LEAD, TAIL, MIN_DUR, MAX_CPS = 0.08, 0.25, 0.8, 9.0


def srt_time(t: float) -> str:
    """Times are floored, never rounded: a cue snapped to frame k then starts at or just before that frame's
    timestamp and is drawn on frame k. Rounding up by a fraction of a millisecond would show it one frame late."""
    ms = int(math.floor(t * 1000 + 1e-6))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ass_time(t: float) -> str:
    cs = int(math.floor(t * 100 + 1e-6))       # ASS has centiseconds only: floor keeps the cue on its frame
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def default_font() -> str:
    """Microsoft YaHei on Windows, PingFang SC on macOS, otherwise the first installed family that can draw Chinese
    (Noto Sans CJK SC when nothing can be detected)."""
    if sys.platform.startswith("win"):
        return "Microsoft YaHei"
    if sys.platform == "darwin":
        return "PingFang SC"
    have = signals.cjk_fonts()
    return have[0] if have else "Noto Sans CJK SC"


def wrap(text: str, limit: int = 18) -> str:
    """At most two lines; break near the middle, preferring a punctuation mark."""
    if len(text) <= limit:
        return text
    mid = len(text) // 2
    best = min((i for i, ch in enumerate(text) if ch in "，。！？、；：,.!?;: "), key=lambda i: abs(i - mid), default=None)
    cut = best + 1 if best is not None and abs(best - mid) <= 6 else mid
    return text[:cut].rstrip() + r"\N" + text[cut:].lstrip()


def write_ass(path: Path, cues: list[dict], w: int, h: int, font: str, bilingual: bool) -> None:
    k = h / 1080.0
    zh, en = int(round(58 * k)), int(round(36 * k))
    mv_zh = int(round((96 if bilingual else 64) * k))
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Zh,{font},{zh},&H00FFFFFF,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,{max(1, round(3 * k))},{max(1, round(1 * k))},2,{int(160 * k)},{int(160 * k)},{mv_zh},1
Style: En,Arial,{en},&H00F0F0F0,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,{max(1, round(2 * k))},{max(1, round(1 * k))},2,{int(160 * k)},{int(160 * k)},{int(round(52 * k))},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rows = []
    for c in cues:
        rows.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Zh,{c.get('name', '')},0,0,0,,{wrap(c['text'])}")
        if bilingual and c.get("en"):
            rows.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},En,{c.get('name', '')},0,0,0,,{c['en']}")
    path.write_text(head + "\n".join(rows) + "\n", encoding="utf-8-sig")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--out", required=True, help="output path prefix, e.g. subs/ep01")
    ap.add_argument("--aligner", choices=["faster-whisper", "cmd", "units"], default="faster-whisper")
    ap.add_argument("--model", default="small", help="faster-whisper model (large-v3 is clearly better when the GPU is free)")
    ap.add_argument("--device", default="cpu", help="cpu | cuda | auto (cpu by default so it never fights ComfyUI for VRAM)")
    ap.add_argument("--language", default="zh")
    ap.add_argument("--aligner-cmd", help='external aligner: command template using {audio} and {text}, prints units JSON')
    ap.add_argument("--units-dir", help="folder with <segment_id>.units.json for --aligner units")
    ap.add_argument("--bilingual", action="store_true", help="add the lines' `en` text as a second ASS line")
    ap.add_argument("--font", default=default_font(),
                    help="font for the Chinese line in the .ass (default by platform: Microsoft YaHei / PingFang SC / Noto Sans CJK SC)")
    ap.add_argument("--no-refine", action="store_true",
                    help="keep the recogniser's word times as they are (default: pull each line's start and end to where the "
                         "voice actually rises and falls)")
    ap.add_argument("--no-write-back", action="store_true")
    ap.add_argument("--hint", action="store_true", help="feed the locked text to whisper as a prompt (off by default: it made "
                                                        "whisper-small hallucinate on real takes)")
    a = ap.parse_args()

    edl_path = Path(a.edl)
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    fps, plan, total_frames = edl_lib.timeline(edl)
    frame = 1.0 / fps
    cues, review = [], 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for p in plan:
            seg, t0 = p["seg"], p["start_s"]
            lines = seg.get("lines") or []
            if lines:
                pinned = [ln.get("locked") and ln.get("start") is not None and ln.get("end") is not None for ln in lines]
                mapped, env, hop = None, None, 0.01
                if not all(pinned):
                    src = edl_lib.resolve(edl_path, seg["audio"] if seg.get("audio") not in (None, "native") else seg["video"])
                    a0 = p["src_in"]
                    a1 = p["src_out"] + float(seg.get("l_cut", 0.0) or 0.0)
                    wav = tmp / f"{seg['id']}.wav"
                    if speech.extract_wav(src, wav, a0, a1):
                        units, _ = speech.get_units(a.aligner, wav, lines, model=a.model, language=a.language, device=a.device,
                                                    cmd=a.aligner_cmd, tmp=tmp, bias=a.hint,
                                                    units_file=Path(a.units_dir) / f"{seg['id']}.units.json" if a.units_dir else None)
                        mapped = speech.map_lines(lines, units)
                        if not a.no_refine:
                            try:
                                env, hop = speech.envelope(wav)
                            except ImportError:                      # numpy missing: keep the recogniser's times
                                env = None
                cursor = 0.3                                      # fallback slot start for lines that were not heard
                for i, ln in enumerate(lines):
                    m = mapped["lines"][i] if mapped else {"coverage": 0.0, "first_s": None, "last_s": None, "confidence": None}
                    chars = len(speech.norm(ln["text"]))
                    extra = {}
                    if pinned[i]:                                 # corrected by hand: keep it
                        s, e, flag = float(ln["start"]), float(ln["end"]), None
                        m = {"coverage": ln.get("coverage", 1.0)}
                        extra["locked"] = True
                    elif m["first_s"] is not None:
                        first, last, shift = m["first_s"], m["last_s"], 0.0
                        if env is not None:
                            first, last, shift = speech.refine_span(env, hop, first, last)
                        s = max(0.0, first - LEAD)
                        e = max(last + TAIL, s + MIN_DUR, s + chars / MAX_CPS)
                        e = min(e, p["dur_s"] + float(seg.get("l_cut", 0.0) or 0.0))      # a cue does not outlive its picture
                        flag = None if m["coverage"] >= 0.6 else "low_coverage"
                        conf = m.get("confidence")
                        if flag is None and conf is not None and conf < 0.65:
                            flag = "low_confidence"               # the recogniser was not sure these words were said here
                        if flag is None and chars >= 2 and (last - first) > 0 and chars / (last - first) < 1.2:
                            flag = "timing_suspect"               # far too slow for speech: the span includes something else
                        if flag is None and last > p["dur_s"] - 0.10:
                            flag = "ends_at_cut"                  # the last word touches the out point: listen to it
                        before = ln.get("start")                  # where the last run put this line, from the same in-point
                        if (flag is None and before is not None and seg.get("subtitles_in_frame") == seg.get("in_frame")
                                and abs(s - float(before)) > 0.3):
                            flag = "moved"                        # same in-point, different answer: the recogniser is not sure
                            extra["previous_start"] = float(before)
                        if shift > 0.3:
                            extra["adjusted_s"] = shift           # how far the recogniser's times were pulled to the voice
                        if conf is not None:
                            extra["confidence"] = conf
                    else:
                        s = cursor
                        e = s + max(MIN_DUR, chars / 5.0)
                        flag = "not_heard"
                    cursor = e + 2 * frame
                    review += flag is not None
                    cues.append({"segment": seg["id"], "line": i, "speaker": ln.get("speaker"), "name": ln.get("name", ""),
                                 "text": ln["text"], **({"en": ln["en"]} if ln.get("en") else {}),
                                 "local_start": s, "local_end": e, "start": t0 + s, "end": t0 + e,
                                 "coverage": m["coverage"], **extra, **({"needs_review": flag} if flag else {})})
    total = total_frames / fps
    cues.sort(key=lambda c: c["start"])
    for x, y in zip(cues, cues[1:]):                              # keep >= 2 frames between consecutive cues
        if x["end"] > y["start"] - 2 * frame:
            x["end"] = max(x["start"] + 0.3, y["start"] - 2 * frame)
    for c in cues:                                               # snap to frames, clamp to the programme
        c["start"] = min(max(0.0, round(c["start"] * fps) / fps), max(0.0, total - 0.3))
        c["end"] = min(max(c["start"] + frame, round(c["end"] * fps) / fps), total)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    srt = [f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}" + (f"\n{c['en']}" if a.bilingual and c.get("en") else "") + "\n"
           for i, c in enumerate(cues, 1)]
    Path(str(out) + ".srt").write_text("\n".join(srt), encoding="utf-8")
    write_ass(Path(str(out) + ".ass"), cues, int(edl.get("width", 1920)), int(edl.get("height", 1080)), a.font, a.bilingual)
    Path(str(out) + ".cues.json").write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding="utf-8")
    if not a.no_write_back:
        seg_start = {p["id"]: p["start_s"] for p in plan}
        by = {(c["segment"], c["line"]): c for c in cues}
        for seg in edl["segments"]:
            for i, ln in enumerate(seg.get("lines") or []):
                c = by.get((seg["id"], i))
                if c:
                    ln["start"] = round(c["start"] - seg_start[seg["id"]], 3)
                    ln["end"] = round(c["end"] - seg_start[seg["id"]], 3)
                    ln["coverage"] = c["coverage"]
                    for key in ("needs_review", "confidence", "adjusted_s", "previous_start"):
                        if c.get(key) is not None:
                            ln[key] = c[key]
                        else:
                            ln.pop(key, None)
        for seg in edl["segments"]:
            if seg.get("lines"):
                seg["subtitles_in_frame"] = seg.get("in_frame")          # so the next run can tell "moved" from "re-cut"
        edl["subtitles"] = {"cut_signature": edl_lib.cut_signature(edl), "files": [str(out) + ".srt", str(out) + ".ass"],
                            "aligner": a.aligner if a.aligner != "faster-whisper" else f"faster-whisper {a.model}"}
        edl_path.write_text(json.dumps(edl, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in cues:
        mark = f"  <-- {c['needs_review']}" if c.get("needs_review") else ""
        mark += "  (locked)" if c.get("locked") else ""
        mark += f"  (start / end pulled {c['adjusted_s']:.2f}s to the voice)" if c.get("adjusted_s") else ""
        mark += f"  (the last run started this line at {c['previous_start']:.2f}s of its segment)" if c.get("previous_start") is not None else ""
        print(f"{srt_time(c['start'])} --> {srt_time(c['end'])}  [{c['segment']}] {c['text']}  (coverage {c['coverage']}){mark}")
    note = signals.subtitle_font_note(a.font, any("\u4e00" <= ch <= "\u9fff" for c in cues for ch in c["text"]))
    if note:
        print("WARN ", note)
    print(f"{len(cues)} cue(s), {review} need review -> {out}.srt / .ass / .cues.json"
          f"{'' if a.no_write_back else ' ; times written back to ' + str(edl_path)}"
          f"  [matching: {'pinyin' if speech.PHONETIC else 'exact characters - pip install pypinyin for homophone-proof matching'}]")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "h3lib"))
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
