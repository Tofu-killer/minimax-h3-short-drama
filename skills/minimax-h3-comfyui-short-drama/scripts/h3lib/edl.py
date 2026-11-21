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


def mix_is_stale(edl: dict, report_path=None, mix_path=None) -> str | None:
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
        if not made and rep.get("total_frames") not in (None, total_frames):
            return f"{report_path} describes a {rep.get('total_frames')}-frame programme, this edit list has {total_frames} frames: mix again"
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


def subtitles_stale(edl: dict) -> bool:
    """True when retime_subtitles.py recorded a cut signature and the cuts no longer match it."""
    made = (edl.get("subtitles") or {}).get("cut_signature")
    return bool(made) and made != cut_signature(edl)
