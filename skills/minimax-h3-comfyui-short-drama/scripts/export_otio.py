#!/usr/bin/env python3
"""EDL -> OpenTimelineIO (.otio) plus FCP7 XML / CMX3600 EDL for DaVinci Resolve, Premiere and other editors.

    python export_otio.py edit/ep01.edl.json --out edit/ep01
    python export_otio.py edit/ep01.edl.json --out edit/ep01 --mix final/ep01.mix.wav

Writes <out>.otio always; <out>.xml (FCP7 XML - Resolve: File > Import > Timeline; Premiere: File > Import)
and <out>.cmx3600.edl (CMX3600, picture only) when the adapter packages are installed.
Timeline: V1 picture, A1 the sound of each segment (the clip's own audio, or the dialogue stem named in the
EDL), A2 non-dialogue stems, A3 music, A4 the mastered mix (--mix). Every dialogue line with times becomes a
marker on its clip. Subtitles are not part of these formats: import the .srt from retime_subtitles.py.
Levels are NOT carried over (the formats have no portable gain); use the mastered mix track, or set clip gains
from the mix report by hand.

Needs: pip install opentimelineio otio-fcp-adapter otio-cmx3600-adapter
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import edl as edl_lib  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--out", required=True, help="output path prefix, e.g. edit/ep01")
    ap.add_argument("--mix", help="mastered mix wav to add as track A4")
    a = ap.parse_args()
    try:
        import opentimelineio as otio
    except ImportError:
        sys.exit("OpenTimelineIO is not installed: pip install opentimelineio otio-fcp-adapter otio-cmx3600-adapter")

    edl_path = Path(a.edl)
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    fps, plan, total_frames = edl_lib.timeline(edl)
    RT, TR = otio.opentime.RationalTime, otio.opentime.TimeRange

    def url(p) -> str:
        return edl_lib.resolve(edl_path, p).resolve().as_uri()

    def ref(p, frames: float, rate: float):
        return otio.schema.ExternalReference(target_url=url(p), available_range=TR(RT(0, rate), RT(frames, rate)))

    tl = otio.schema.Timeline(name=edl.get("name") or edl_path.stem)
    tl.global_start_time = RT(0, fps)
    tracks = {"V1": otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)}
    for n in ("A1", "A2", "A3", "A4"):
        tracks[n] = otio.schema.Track(name=n, kind=otio.schema.TrackKind.Audio)
    conformed = []
    for p in plan:
        s = p["seg"]
        rate = p["src_fps"]
        n_src = int(s["out_frame"]) - int(s["in_frame"])
        avail = float(s.get("frames_total") or s["out_frame"])
        if abs(rate - fps) > 1e-3:
            conformed.append(p["id"])
        src = TR(RT(int(s["in_frame"]), rate), RT(n_src, rate))
        clip = otio.schema.Clip(name=p["id"], media_reference=ref(s["video"], avail, rate), source_range=src)
        for ln in s.get("lines") or []:
            if ln.get("start") is None or ln.get("end") is None:
                continue
            at = int(s["in_frame"]) + int(round(float(ln["start"]) * rate))
            dur = max(1, int(round((float(ln["end"]) - float(ln["start"])) * rate)))
            clip.markers.append(otio.schema.Marker(name=f"{ln.get('name', '')}: {ln['text']}".strip(": "),
                                                   marked_range=TR(RT(at, rate), RT(dur, rate)),
                                                   color=otio.schema.MarkerColor.CYAN))
        tracks["V1"].append(clip)
        if s.get("audio"):
            media = s["video"] if s["audio"] == "native" else s["audio"]
            tracks["A1"].append(otio.schema.Clip(name=p["id"], media_reference=ref(media, avail, rate), source_range=src))
        else:
            tracks["A1"].append(otio.schema.Gap(source_range=TR(RT(0, fps), RT(p["frames"], fps))))
        if s.get("nondialogue"):
            tracks["A2"].append(otio.schema.Clip(name=p["id"] + " fx", media_reference=ref(s["nondialogue"], avail, rate),
                                                 source_range=src))
        else:
            tracks["A2"].append(otio.schema.Gap(source_range=TR(RT(0, fps), RT(p["frames"], fps))))
    whole = TR(RT(0, fps), RT(total_frames, fps))
    if edl.get("music"):
        tracks["A3"].append(otio.schema.Clip(name="music", media_reference=ref(edl["music"]["file"], total_frames, fps),
                                             source_range=whole))
    if a.mix:
        mix_ref = otio.schema.ExternalReference(target_url=Path(a.mix).resolve().as_uri(), available_range=whole)
        tracks["A4"].append(otio.schema.Clip(name="master mix", media_reference=mix_ref, source_range=whole))
    for n, tr in tracks.items():
        if n in ("V1", "A1") or any(isinstance(c, otio.schema.Clip) for c in tr):
            tl.tracks.append(tr)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    otio.adapters.write_to_file(tl, str(out) + ".otio")
    wrote = [str(out) + ".otio"]
    for suffix, adapter, what in ((".xml", "fcp_xml", "otio-fcp-adapter"), (".cmx3600.edl", "cmx_3600", "otio-cmx3600-adapter")):
        if adapter not in otio.adapters.available_adapter_names():
            print(f"skipped {suffix}: pip install {what}")
            continue
        try:
            if adapter == "cmx_3600":                 # the EDL format describes one picture track
                v_only = otio.schema.Timeline(name=tl.name)
                v_only.global_start_time = RT(0, fps)
                v_only.tracks.append(tracks["V1"].deepcopy())
                otio.adapters.write_to_file(v_only, str(out) + suffix, adapter_name=adapter, rate=fps)
            else:
                otio.adapters.write_to_file(tl, str(out) + suffix, adapter_name=adapter)
            wrote.append(str(out) + suffix)
        except Exception as e:  # noqa: BLE001
            print(f"could not write {suffix} ({adapter}): {type(e).__name__}: {str(e)[:200]}")
    dur = tl.duration()
    print(f"timeline {dur.value:g} frames @ {dur.rate:g} fps ({total_frames} planned), "
          f"tracks: {', '.join(t.name + '=' + str(len(t)) for t in tl.tracks)}")
    print("wrote " + ", ".join(wrote))
    if conformed:
        print(f"NOTE: {', '.join(conformed)} are not {fps:g} fps clips; the editor will conform them - check their length there")
    print("levels are not exported: use the master mix track or apply the gains from the mix report by hand")


if __name__ == "__main__":
    main()
