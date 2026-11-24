"""Shared EDL arithmetic. Every script that reads an EDL gets its timeline from here, so that cuts,
subtitles, the mix and the exported editor projects can never disagree about where a segment starts.

EDL frame numbers (in_frame / out_frame, out exclusive) count frames of the SOURCE clip.
`src_fps` (written by make_edl.py) is the clip's own frame rate; when it differs from the timeline
`fps` the clip is conformed, and its length on the timeline is round(source_frames * fps / src_fps).
Timeline positions are sums of whole timeline frames - never sums of rounded seconds.
"""
from __future__ import annotations

from pathlib import Path


def seg_times(seg: dict, fps: float) -> dict:
    sf = float(seg.get("src_fps") or fps)
    n_src = int(seg["out_frame"]) - int(seg["in_frame"])
    if n_src <= 0:
        raise ValueError(f"segment {seg.get('id')}: out_frame must be greater than in_frame")
    frames = n_src if abs(sf - fps) < 1e-3 else max(1, int(round(n_src * fps / sf)))
    return {"src_fps": sf, "frames": frames, "src_in": int(seg["in_frame"]) / sf, "src_out": int(seg["out_frame"]) / sf}


def timeline(edl: dict) -> tuple[float, list[dict], int]:
    """-> (fps, [{id, start_frame, frames, start_s, dur_s, src_fps, src_in, src_out, seg}], total_frames)"""
    fps = float(edl.get("fps", 24))
    out, acc = [], 0
    for s in edl["segments"]:
        t = seg_times(s, fps)
        out.append({"id": s["id"], "start_frame": acc, "start_s": acc / fps, "dur_s": t["frames"] / fps, "seg": s, **t})
        acc += t["frames"]
    return fps, out, acc


def resolve(edl_path: Path, p: str | Path) -> Path:
    """Paths in an EDL are used as written when they exist (absolute, or relative to the working
    directory - that is how make_edl.py writes them); otherwise they are tried relative to the EDL file."""
    q = Path(p)
    if q.is_absolute() or q.exists():
        return q
    alt = Path(edl_path).parent / q
    return alt if alt.exists() else q


def mix_is_stale(edl: dict, report_path=None, mix_path=None, edl_path=None) -> str | None:
    """A sentence when the mix report / mix wav was made from another cut than the one in this edit list, else None.
    The report carries the cut signature; a wav on its own is judged by its length."""
    import json as _json
    import subprocess
    from pathlib import Path as _P
    fps, _plan, total_frames = timeline(edl)
    if report_path and _P(report_path).exists():
        try:
            rep = _json.loads(_P(report_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            rep = {}
        made = rep.get("cut_signature")
        if made and made != cut_signature(edl):
            return (f"{report_path} was made from another cut (in / out frames changed since): run mix_episode.py again, "
                    f"then export once more")
        clips = rep.get("clips_signature")
        if clips and edl_path is not None and clips != clips_signature(edl, edl_path):
            return (f"{report_path} was made from other clips than the edit list points at now (a clip was replaced under the "
                    f"same name): run mix_episode.py again, then export once more")
        if not made and rep.get("total_frames") not in (None, total_frames):
            return f"{report_path} describes a {rep.get('total_frames')}-frame programme, this edit list has {total_frames} frames: mix again"
        sound = rep.get("sound_signature")                      # absent in reports written by an earlier version
        if sound and edl_path is not None and sound != sound_signature(edl, edl_path):
            return (f"{report_path} was mixed before the sound in the edit list changed (the music or an ambience bed - its file or "
                    f"its settings -, a stem, a level, or the time of a line, which retime_subtitles.py or a hand edit set again): "
                    f"run mix_episode.py again, then export once more")
        burned, burned_sha = rep.get("subtitles_file"), rep.get("subtitles_sha")
        if burned and burned_sha:
            now = clip_sha(resolve(edl_path, burned) if edl_path is not None else burned)
            if now and now != burned_sha:                       # '' = the file is gone: nothing can be said
                return (f"the subtitles burned into the picture are an earlier version of {burned} (the file was written again "
                        f"after the mix): run mix_episode.py again with --ass {burned}, then export once more")
    if mix_path and _P(mix_path).exists():
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mix_path)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            dur = float(r.stdout.strip())
        except ValueError:
            return None
        if abs(dur - total_frames / fps) > 1.5 / fps:
            return (f"{mix_path} is {dur:.3f}s long, this edit list is {total_frames / fps:.3f}s: the mix was made from another "
                    f"cut - run mix_episode.py again, then export once more")
    return None


def cut_signature(edl: dict) -> str:
    """Changes whenever a cut moves: line times are stored relative to each segment's in point, so they are
    only valid for the cut they were measured on."""
    import hashlib
    key = ";".join(f"{s['id']}:{s['in_frame']}:{s['out_frame']}:{s.get('src_fps', '')}:{s.get('video')}:{s.get('audio')}"
                   for s in edl.get("segments", []))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def sound_signature(edl: dict, edl_path) -> str:
    """Changes whenever something the MIX is made from changes while the cut stays where it is: the music bed and the
    ambience beds (their files, by content, and their settings), a stem, an L-cut, the loudness targets, a line's time or
    gain. cut_signature() and clips_signature() see none of these."""
    import hashlib
    import json as _json

    def file_sig(name) -> str:
        return clip_sha(resolve(edl_path, name)) if name and name != "native" else ""

    music = edl.get("music") or None
    beds = edl.get("ambience") or {}
    key = {"size": [edl.get("width"), edl.get("height")],
           "music": dict(music, _sha=file_sig(music.get("file"))) if isinstance(music, dict) else music,
           "ambience": {k: (dict(v, _sha=file_sig(v.get("file"))) if isinstance(v, dict) else v) for k, v in sorted(beds.items())}
           if isinstance(beds, dict) else beds,
           "loudness": edl.get("loudness"),
           "segments": [{"id": s.get("id"), "audio": s.get("audio"), "audio_sha": file_sig(s.get("audio")),
                         "nondialogue": s.get("nondialogue"), "nondialogue_sha": file_sig(s.get("nondialogue")),
                         "l_cut": s.get("l_cut"), "j_cut": s.get("j_cut"), "scene": s.get("scene"),
                         "lines": [[ln.get("start"), ln.get("end"), ln.get("gain_db"), bool(ln.get("locked")), ln.get("needs_review")]
                                   for ln in s.get("lines") or []]}
                        for s in edl.get("segments", [])]}
    return hashlib.sha1(_json.dumps(key, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()[:12]


def exports_file(edl_path) -> Path:
    return Path(str(edl_path)[:-len(".edl.json")] + ".exports.json") if str(edl_path).endswith(".edl.json") \
        else Path(edl_path).with_suffix(".exports.json")


def note_export(edl: dict, edl_path, kind: str, target: str) -> None:
    """Remember that the edit list was exported (an editor project is a copy: it does not follow later changes).
    Kept beside the edit list as <name>.exports.json; project_status.py compares it with the cut of now."""
    import json as _json
    import time as _time
    f = exports_file(edl_path)
    try:
        rec = _json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rec = {}
    rec[kind] = {"path": str(target), "at": round(_time.time(), 1), "cut_signature": cut_signature(edl),
                 "clips_signature": clips_signature(edl, edl_path), "sound_signature": sound_signature(edl, edl_path)}
    try:
        f.write_text(_json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def exports_state(edl: dict, edl_path) -> list[tuple[str, str, str]]:
    """[(kind, path, '' or why it is out of date)] for the exports recorded beside the edit list."""
    import json as _json
    try:
        rec = _json.loads(exports_file(edl_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for kind, e in sorted(rec.items()):
        if not isinstance(e, dict):
            continue
        why = ""
        if e.get("cut_signature") != cut_signature(edl):
            why = "exported from another cut (a clip or an in / out frame changed since)"
        elif e.get("clips_signature") and e["clips_signature"] != clips_signature(edl, edl_path):
            why = "a clip was replaced under the same name since it was exported"
        elif e.get("sound_signature") and e["sound_signature"] != sound_signature(edl, edl_path):
            why = "the music, a level or the time of a line changed since it was exported"
        out.append((kind, str(e.get("path") or ""), why))
    return out


def clip_sha(path) -> str:
    """First 12 hex digits of a file's SHA-256, '' when it cannot be read."""
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()[:12]


def clips_signature(edl: dict, edl_path) -> str:
    """Changes whenever a clip's CONTENT changes. cut_signature() only sees names and frame numbers: a new take copied
    over selects/s03.mp4 keeps both, and the line times measured on the old take would pass as current."""
    import hashlib
    key = ";".join(f"{s['id']}:{clip_sha(resolve(edl_path, s.get('video', '')))}" for s in edl.get("segments", []))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def subtitles_stale(edl: dict, edl_path=None) -> bool:
    """True when retime_subtitles.py recorded the cut it timed and the edit list is no longer that cut: an in or
    out frame moved, a clip was exchanged, or - when `edl_path` is given, so the files can be read - a clip was
    replaced under the same name."""
    sub = edl.get("subtitles") or {}
    made = sub.get("cut_signature")
    if made and made != cut_signature(edl):
        return True
    clips = sub.get("clips_signature")                      # absent in edit lists timed by an earlier version
    return bool(clips) and edl_path is not None and clips != clips_signature(edl, edl_path)
