#!/usr/bin/env python3
"""EDL -> an editable 剪映 (JianYing) / CapCut draft: same cuts as the automatic mix, ready for manual polish.

    python export_capcut_draft.py edit/ep01.edl.json --drafts "D:/JianyingPro Drafts"
    python export_capcut_draft.py edit/ep01.edl.json --drafts "D:/JianyingPro Drafts" ^
        --report final/ep01.mix.report.json --mix final/ep01.mix.wav

The drafts folder is the one shown in 剪映 under 全局设置 -> 草稿位置. After the script ran, leave and re-enter
the draft list (or restart 剪映) to see the new draft. Media is referenced by absolute path, not copied:
run this on the machine that holds the clips, and do not move them afterwards.

Tracks written:
  picture      one segment per EDL segment, cut on the same frames mix_episode.py uses. A clip that plays its
               own sound keeps it ATTACHED (it follows the clip when you trim or reorder), at the per-take gain
               mix_episode.py chose when --report is given.
  dialogue_a/b separate dialogue stems named in the EDL, alternating over two tracks so L-cut tails can overlap;
               the picture's own sound is muted for those segments.
  effects      non-dialogue stems named in the EDL.
  music        the EDL score, 8 dB under its mix level: 剪映 has no sidechain ducking, so this static level
               stands in for it - ride it by hand where there is no speech.
  subtitle     one text segment per timed line; the text is the locked line, the times come from
               retime_subtitles.py.
  master_mix   (--mix) the mastered mix from mix_episode.py as a MUTED reference track. If you did not move
               any cut, un-mute it and mute everything else to get exactly the automatic master.

Needs: pip install pyJianYingDraft   (or pycapcut for the international CapCut with --international).
Generating drafts works with current 剪映 versions; this script was verified by inspecting the draft JSON it
writes - opening it in your 剪映 version is the first thing to check.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import edl as edl_lib  # noqa: E402

STATIC_DUCK_DB = -8.0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--drafts", required=True, help="剪映 / CapCut drafts folder (must exist)")
    ap.add_argument("--name", help="draft name (default: EDL name)")
    ap.add_argument("--report", help="mix_episode.py report (*.mix.report.json): use its per-take gains")
    ap.add_argument("--mix", help="mastered mix wav to add as a muted reference track")
    ap.add_argument("--no-subtitles", action="store_true")
    ap.add_argument("--bilingual", action="store_true", help="append each line's `en` text as a second row")
    ap.add_argument("--international", action="store_true", help="write a CapCut (international) draft with pycapcut")
    ap.add_argument("--overwrite", action="store_true", help="replace an existing draft of the same name")
    a = ap.parse_args()

    mod = "pycapcut" if a.international else "pyJianYingDraft"
    try:
        lib = importlib.import_module(mod)
    except ImportError:
        sys.exit(f"{mod} is not installed: pip install {mod}")
    edl_path = Path(a.edl)
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    fps, plan, total_frames = edl_lib.timeline(edl)
    if abs(fps - round(fps)) > 1e-6:
        print(f"NOTE: timeline is {fps:g} fps; the draft is created at {round(fps)} fps (剪映 drafts take whole numbers)")
    drafts = Path(a.drafts)
    if not drafts.is_dir():
        sys.exit(f"drafts folder not found: {drafts}\n(in 剪映: 全局设置 -> 草稿位置)")
    name = a.name or edl.get("name") or edl_path.stem
    gains = {}
    if a.report:
        rep = json.loads(Path(a.report).read_text(encoding="utf-8"))
        gains = {s["id"]: float(s.get("gain_db") or 0.0) for s in rep.get("segments", [])}

    SEC = lib.SEC

    def us(frames: int) -> int:                       # timeline frames -> microseconds, from the frame count
        return int(round(frames * SEC / fps))

    def absolute(p) -> str:
        return str(edl_lib.resolve(edl_path, p).resolve())

    def lin(db: float) -> float:
        return round(10 ** (db / 20.0), 4)

    script = lib.DraftFolder(str(drafts)).create_draft(name, int(edl.get("width", 1920)), int(edl.get("height", 1080)),
                                                      fps=int(round(fps)), allow_replace=a.overwrite)

    def add_track(kind: str, track: str, mute: bool = False) -> None:
        ttype = getattr(lib.TrackType, kind)
        if hasattr(script, "append_track"):           # pyJianYingDraft >= 0.3
            script.append_track(lib.TrackSpec(ttype, track, mute=mute))
        else:                                         # pycapcut / older pyJianYingDraft
            script.add_track(ttype, track, mute=mute)

    has_stem = any(p["seg"].get("audio") not in (None, "native") for p in plan)
    has_fx = any(p["seg"].get("nondialogue") for p in plan)
    music = edl.get("music")
    add_track("video", "picture")
    if has_stem:
        add_track("audio", "dialogue_a")
        add_track("audio", "dialogue_b")
    if has_fx:
        add_track("audio", "effects")
    if music:
        add_track("audio", "music")
    if a.mix:
        add_track("audio", "master_mix", mute=True)
    if not a.no_subtitles:
        add_track("text", "subtitle")

    stem_i = 0
    for i, p in enumerate(plan):
        s = p["seg"]
        t0 = us(p["start_frame"])
        dur = us(p["start_frame"] + p["frames"]) - t0             # contiguous by construction: no 1-microsecond gaps
        src0 = int(round(p["src_in"] * SEC))
        src_dur = dur if abs(p["src_fps"] - fps) < 1e-3 else int(round((p["src_out"] - p["src_in"]) * SEC))
        own_sound = s.get("audio") == "native"
        vol = lin(gains.get(p["id"], 0.0)) if own_sound else 0.0
        script.add_segment(lib.VideoSegment(absolute(s["video"]), lib.trange(t0, dur),
                                            source_timerange=lib.trange(src0, src_dur), volume=vol), "picture")
        if s.get("audio") not in (None, "native"):
            last = i == len(plan) - 1
            tail = 0 if last else int(round(float(s.get("l_cut", 0) or 0) * SEC))
            seg = lib.AudioSegment(absolute(s["audio"]), lib.trange(t0, dur + tail),
                                   source_timerange=lib.trange(src0, dur + tail), volume=lin(gains.get(p["id"], 0.0)))
            seg.add_fade("0.01s", "0.12s")
            script.add_segment(seg, "dialogue_a" if stem_i % 2 == 0 else "dialogue_b")
            stem_i += 1
        if s.get("nondialogue"):
            script.add_segment(lib.AudioSegment(absolute(s["nondialogue"]), lib.trange(t0, dur),
                                                source_timerange=lib.trange(src0, dur),
                                                volume=lin(gains.get(p["id"], 0.0))), "effects")
    total_us = us(total_frames)
    if music:
        seg = lib.AudioSegment(absolute(music["file"]), lib.trange(0, total_us),
                               volume=lin(float(music.get("gain_db", -6)) + STATIC_DUCK_DB))
        seg.add_fade(f"{float(music.get('fade_in', 0.5))}s", f"{float(music.get('fade_out', 1.0))}s")
        script.add_segment(seg, "music")
    if a.mix:
        script.add_segment(lib.AudioSegment(str(Path(a.mix).resolve()), lib.trange(0, total_us)), "master_mix")

    cues, untimed = 0, 0
    if not a.no_subtitles:
        style = lib.TextStyle(size=7.0, color=(1.0, 1.0, 1.0), align=1, auto_wrapping=True)
        place = lib.ClipSettings(transform_y=-0.78)
        border = lib.TextBorder(color=(0.06, 0.06, 0.06), width=40.0)
        rows = []
        for p in plan:
            for ln in p["seg"].get("lines") or []:
                if ln.get("start") is None or ln.get("end") is None:
                    untimed += 1
                    continue
                text = ln["text"] + (f"\n{ln['en']}" if a.bilingual and ln.get("en") else "")
                rows.append([int(round((p["start_s"] + float(ln["start"])) * SEC)),
                             int(round((p["start_s"] + float(ln["end"])) * SEC)), text])
        rows.sort()
        for x, y in zip(rows, rows[1:]):                           # segments on one track may not overlap
            x[1] = min(x[1], y[0])
        for st, en, text in rows:
            en = min(en, total_us)
            if en - st < 100_000:
                continue
            script.add_segment(lib.TextSegment(text, lib.trange(st, en - st), style=style, clip_settings=place,
                                               border=border), "subtitle")
            cues += 1
    script.save()

    out_dir = drafts / name
    content = json.loads((out_dir / "draft_content.json").read_text(encoding="utf-8"))
    tracks = [(t.get("name") or t["type"], len(t["segments"])) for t in content["tracks"]]
    print(f"draft written: {out_dir}")
    print(f"  duration {content['duration'] / SEC:.3f}s ({total_frames} frames @ {fps:g} fps), tracks: "
          + ", ".join(f"{n}={c}" for n, c in tracks))
    if gains:
        print("  per-take gains from the mix report applied: " + ", ".join(f"{k} {v:+.1f} dB" for k, v in gains.items()))
    else:
        print("  no --report: every take plays at its own level (pass the mix report to carry the level matching over)")
    if untimed:
        print(f"  {untimed} line(s) have no times and were left out of the subtitle track - run retime_subtitles.py first")
    if music:
        print(f"  music placed {STATIC_DUCK_DB:g} dB under its mix level (no ducking in 剪映) - ride it by hand")
    if a.mix:
        print("  master_mix is muted: un-mute it and mute the rest only if no cut was moved")
    print("  open 剪映 and re-enter the draft list to see it; missing fonts / effects load on the second open")


if __name__ == "__main__":
    main()
