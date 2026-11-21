#!/usr/bin/env python3
"""Assemble and master an episode from the EDL: frame-accurate cuts, timeline mix, loudness, optional burned subtitles.

    python3 mix_episode.py edit/ep01.edl.json --out final/ep01.mp4
    python3 mix_episode.py edit/ep01.edl.json --out final/ep01.mp4 --ass subs/ep01.ass --stems-out audio/ep01/stems

Stages (each writes a file; --keep-temp DIR keeps them, so a failure is easy to locate):
  1. picture   every segment is cut on exact clip frames [in_frame, out_frame), conformed to the timeline fps and
               delivery size (lanczos; --fit cover crops, contain pads), subtitles burned in the same pass when
               --ass is given, encoded ONCE, then concatenated without re-encoding. Positions come from summed
               frame counts (h3lib/edl.py), never from summed seconds.
  2. dialogue  each segment's sound (the take's own audio = "native", or a dialogue stem named in the EDL) is
               trimmed, level-matched, given 10 ms / 120 ms fades and placed at its timecode; an L-cut lets it
               outlast its picture. Level matching uses the loudness of the SPOKEN parts (line times written by
               retime_subtitles.py) - a take with one short line and a lot of room tone is not turned up just
               because it is quiet on average. Gain is capped so loud non-dialogue peaks are limited by <= 4 dB.
  3. effects   optional non-dialogue stems and one looping ambience bed per scene (band-limited, low level).
  4. music     optional score, faded, ducked under the dialogue with a sidechain compressor.
  5. master    sum -> gain to the programme target (default -14 LUFS); a limiter is added only when the gain
               would push the true peak above the ceiling (default -1.5 dBTP). No dynamic loudnorm, no pumping.
  6. mux + verify  picture and sound must have the same length (+-2 frames), measured loudness within +-1 LU of
               target, true peak <= -1.0 dBTP. A JSON report is written next to the output.

EDL fields used: fps, width, height, segments[{id, video, src_fps, in_frame, out_frame, audio ("native" | path |
null), nondialogue, l_cut, j_cut, scene, lines[{start, end}]}], ambience{scene: {file, gain_db}},
music{file, gain_db, fade_in, fade_out, loop, duck{threshold, ratio, attack, release}},
loudness{dialogue_lufs, program_lufs, true_peak}.
Build the EDL with make_edl.py, run retime_subtitles.py (fills line times), then mix.

Exit codes: 0 ok, 1 acceptance failed, 2 bad or missing input, 3 ffmpeg/ffprobe missing. Standard library + ffmpeg.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
import edl as edl_lib  # noqa: E402

AR = 48000
STEREO = f"aresample={AR},aformat=sample_fmts=fltp:channel_layouts=stereo"


def run(cmd: list[str], what: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    if r.returncode != 0:
        tail = "\n".join(r.stderr.strip().splitlines()[-12:])
        sys.exit(f"ffmpeg failed while {what}:\n{tail}\n(command: {' '.join(cmd[:14])} ...)")
    return r


def has_audio(path: Path) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def stream_duration(path: Path, kind: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", f"{kind}:0", "-show_entries", "stream=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except ValueError:
            return 0.0


def measure(path: Path, pre: str = "") -> tuple[float, float] | None:
    """(integrated LUFS, true peak dBTP) of path after the optional `pre` filter chain; None when (near) silent."""
    af = (pre + "," if pre else "") + "loudnorm=print_format=json"
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", af, "-f", "null", "-"], "measuring loudness")
    m = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if not m:
        return None
    try:
        d = json.loads(m[-1])
        i, tp = float(d["input_i"]), float(d["input_tp"])
    except (ValueError, KeyError):
        return None
    if math.isinf(i) or math.isnan(i) or i < -60:
        return None
    return i, (tp if not (math.isinf(tp) or math.isnan(tp)) else -99.0)


def window_lufs(path: Path, t0: float, t1: float) -> float | None:
    """Integrated loudness of [t0, t1). Windows under 3 s are looped to 6 s first: the meter needs a few
    seconds of signal, and repeating the same material does not change its loudness."""
    d = t1 - t0
    af = f"atrim=start={t0:.6f}:end={t1:.6f},asetpts=PTS-STARTPTS,aresample={AR}"
    if d < 3.0:
        af += f",aloop=loop=-1:size={max(1, int(d * AR))},atrim=end=6"
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", af + ",ebur128", "-f", "null", "-"],
            "measuring a line's loudness")
    m = re.search(r"I:\s*(-?[\d.]+) LUFS", r.stderr[r.stderr.rfind("Summary:"):])
    if not m or float(m.group(1)) < -60:
        return None
    return float(m.group(1))


def ebur128(path: Path) -> tuple[float | None, float | None]:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
            "verifying loudness")
    summ = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s*(-?[\d.]+) LUFS", summ)
    p = re.search(r"Peak:\s*(-?[\d.]+) dBFS", summ)
    return (float(i.group(1)) if i else None, float(p.group(1)) if p else None)


_LATENCY_OPT: bool | None = None


def limiter(limit_db: float) -> str:
    """Brick-wall limiter without the 5 ms look-ahead delay (it would otherwise shift the sound against the picture)."""
    global _LATENCY_OPT
    if _LATENCY_OPT is None:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-h", "filter=alimiter"], capture_output=True, text=True)
        _LATENCY_OPT = "latency" in r.stdout
    lim = 10 ** (limit_db / 20.0)
    if _LATENCY_OPT:
        return f"alimiter=limit={lim:.4f}:attack=5:release=50:level=false:latency=1"
    return f"alimiter=limit={lim:.4f}:attack=5:release=50:level=false,atrim=start=0.005,asetpts=PTS-STARTPTS"


def fit(n: int) -> str:
    """Force a stream to exactly n samples (timestamps rebuilt from the sample count, then pad / cut)."""
    return f"asetpts=N/SR/TB,apad=whole_len={n},atrim=end_sample={n}"


def wav_out(dest: Path) -> list[str]:
    return ["-c:a", "pcm_s24le", "-ar", str(AR), str(dest)]


def silence(dest: Path, n: int) -> None:
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r={AR}:cl=stereo", "-af", f"atrim=end_sample={n}",
         *wav_out(dest)], "writing silence")


def energy_mean(pairs: list[tuple[float, float]]) -> float:
    """Duration-weighted mean of loudness values (in the power domain)."""
    w = sum(d for _l, d in pairs)
    return 10 * math.log10(sum(d * 10 ** (l / 10) for l, d in pairs) / w)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ass", help="burn this ASS/SRT subtitle file into the picture (same encode, no extra generation loss)")
    ap.add_argument("--fit", choices=["cover", "contain"], default="cover", help="how clips of another aspect meet the delivery size")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--no-take-normalize", action="store_true", help="keep every take's own level")
    ap.add_argument("--stems-out", help="also write dialogue / effects / music stems (pre-master, time-aligned) to this folder")
    ap.add_argument("--keep-temp", help="keep intermediate files in this folder")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and stop")
    a = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            print(f"{tool} not found on PATH", file=sys.stderr)
            sys.exit(3)
    edl_path = Path(a.edl)
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    W, H = int(edl.get("width", 1920)), int(edl.get("height", 1080))
    loud = {"dialogue_lufs": -16, "program_lufs": -14, "true_peak": -1.5, **(edl.get("loudness") or {})}
    if not edl.get("segments"):
        sys.exit("EDL has no segments")
    try:
        fps, plan, total_frames = edl_lib.timeline(edl)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
    total = total_frames / fps
    N = int(round(total * AR))

    def resolve(p) -> Path:
        return edl_lib.resolve(edl_path, p)

    problems = []
    for p in plan:
        s = p["seg"]
        if not resolve(s["video"]).exists():
            problems.append(f"missing clip: {s['video']}")
        elif s.get("frames_total") and int(s["out_frame"]) > int(s["frames_total"]):
            problems.append(f"{s['id']}: out_frame {s['out_frame']} is beyond the clip's {s['frames_total']} frames")
        for key in ("audio", "nondialogue"):
            v = s.get(key)
            if v and v != "native" and not resolve(v).exists():
                problems.append(f"missing {key} file: {v}")
    music = None if a.no_music else edl.get("music")
    if music and not resolve(music["file"]).exists():
        problems.append(f"missing music file: {music['file']}")
    amb_cfg = edl.get("ambience") or {}
    for sc, cfg in amb_cfg.items():
        if not resolve(cfg["file"]).exists():
            problems.append(f"missing ambience file for scene {sc}: {cfg['file']}")
    if a.ass and not Path(a.ass).exists():
        problems.append(f"missing subtitle file: {a.ass}")
    if problems:
        print("cannot mix:\n  " + "\n  ".join(problems), file=sys.stderr)
        sys.exit(2)

    print(f"{len(plan)} segment(s), {total_frames} frames = {total:.3f}s @ {fps:g} fps -> {W}x{H}")
    for p in plan:
        s = p["seg"]
        conform = "" if abs(p["src_fps"] - fps) < 1e-3 else f"  ({p['src_fps']:g} fps clip conformed)"
        print(f"  {p['id']:>6}  t={p['start_s']:8.3f}s  {p['frames']:4d}f  clip[{s['in_frame']},{s['out_frame']})  "
              f"audio={s.get('audio') or '-'}  l_cut={s.get('l_cut', 0) or 0}  scene={s.get('scene') or '-'}{conform}")
    if a.dry_run:
        return

    keep = Path(a.keep_temp) if a.keep_temp else None
    if keep:
        keep.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = (keep or Path(td)).resolve()
        warnings: list[str] = []

        # ---- 1. picture ---------------------------------------------------------------------------
        if a.fit == "cover":
            geo = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
        else:
            geo = f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2"
        subs_name = None
        if a.ass:                                # copied next to the work files so the filter needs no path escaping
            subs_name = "burn" + Path(a.ass).suffix.lower()
            shutil.copyfile(a.ass, tmp / subs_name)
        gop = str(max(1, int(round(fps / 2))))
        names = []
        for i, p in enumerate(plan):
            s = p["seg"]
            name = f"v_{i:03d}.mp4"
            vf = (f"trim=start_frame={s['in_frame']}:end_frame={s['out_frame']},setpts=PTS-STARTPTS,fps={fps:g},"
                  f"tpad=stop_mode=clone:stop_duration=1,{geo},setsar=1")
            if subs_name:
                vf += f",setpts=PTS+{p['start_s']:.6f}/TB,subtitles={subs_name},setpts=PTS-STARTPTS"
            vf += ",format=yuv420p"
            run(["ffmpeg", "-v", "error", "-y", "-i", str(resolve(s["video"]).resolve()), "-an", "-vf", vf,
                 "-frames:v", str(p["frames"]), "-c:v", "libx264", "-crf", str(a.crf), "-preset", a.preset,
                 "-g", gop, "-bf", "2", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                 "-video_track_timescale", "24000", name], f"cutting picture of {p['id']}", cwd=tmp)
            names.append(name)
        (tmp / "concat.txt").write_text("".join(f"file '{n}'\n" for n in names), encoding="utf-8")
        video_only = tmp / "video_only.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "video_only.mp4"],
            "concatenating picture", cwd=tmp)

        # ---- 2. dialogue bus ------------------------------------------------------------------------
        take_gain: dict[str, float] = {}
        inputs, chains, labels = [], [], []
        seg_report = []
        for idx, p in enumerate(plan):
            s = p["seg"]
            src = s.get("audio")
            entry = {"id": p["id"], "start_s": round(p["start_s"], 4), "frames": p["frames"], "audio": src or None}
            seg_report.append(entry)
            if not src:
                continue
            path = resolve(s["video"]) if src == "native" else resolve(src)
            if not has_audio(path):
                warnings.append(f"{p['id']}: no audio stream in {path.name}")
                entry["audio"] = None
                continue
            lead = min(float(s.get("j_cut", 0) or 0), p["src_in"], p["start_s"])       # sound may start before its picture
            a0 = p["src_in"] - lead
            l_cut = 0.0 if idx == len(plan) - 1 else float(s.get("l_cut", 0) or 0)   # nothing to overlap after the last cut
            a1 = p["src_out"] + l_cut
            adur = stream_duration(path, "a")
            if adur > 0:
                a1 = min(a1, adur)
            if a1 - a0 < 0.05:
                warnings.append(f"{p['id']}: the clip has no sound inside the used range")
                entry["audio"] = None
                continue
            gain = 0.0
            if not a.no_take_normalize:
                whole = measure(path, f"atrim=start={a0:.6f}:end={a1:.6f},asetpts=PTS-STARTPTS")
                if whole is None:
                    warnings.append(f"{p['id']}: take is silent or too quiet to measure, level left unchanged")
                else:
                    whole_i, tp = whole
                    lines = s.get("lines") or []
                    timed = [(ln, p["src_in"] + float(ln["start"]), p["src_in"] + float(ln["end"])) for ln in lines
                             if ln.get("start") is not None and ln.get("end") is not None
                             and float(ln["end"]) - float(ln["start"]) >= 0.3 and ln.get("needs_review") != "not_heard"]
                    per = []
                    for ln, w0, w1 in timed:
                        w0, w1 = max(a0, w0), min(a1, w1)
                        l = window_lufs(path, w0, w1) if w1 - w0 >= 0.3 else None
                        if l is not None:
                            per.append((ln, l, w1 - w0))
                    if per:
                        top = max(l for _ln, l, _d in per)
                        kept = [(l, d) for _ln, l, d in per if l >= top - 6.0]
                        ref = energy_mean(kept)
                        basis = "speech"
                        for ln, l, _d in per:
                            if l < top - 6.0:
                                warnings.append(f"{p['id']}: line '{ln['text'][:10]}' is {top - l:.0f} LU quieter than the rest of "
                                                f"the take - hard to hear; re-roll the take or lift that line in an editor")
                        raw = loud["dialogue_lufs"] - ref
                    elif lines:
                        ref, basis = whole_i, "whole take"
                        warnings.append(f"{p['id']}: no line times in the EDL, level matched on the whole take (sound effects "
                                        f"count as much as speech) - run retime_subtitles.py before mixing")
                        raw = max(-6.0, min(6.0, loud["dialogue_lufs"] - ref))
                    else:                                               # no dialogue: leave it, unless it would bury the speech
                        ref, basis = whole_i, "no dialogue"
                        raw = min(0.0, (loud["dialogue_lufs"] + 2.0) - whole_i)
                    cap = max(0.0, (-1.0 - tp) + 4.0)                    # at most ~4 dB of peak limiting
                    gain = max(-12.0, min(raw, cap, 12.0))
                    entry.update({"basis": basis, "measured_lufs": round(ref, 1), "true_peak": round(tp, 1)})
                    if gain < raw - 0.5:
                        warnings.append(f"{p['id']}: speech wants {raw:+.1f} dB but loud non-dialogue peaks cap it at {gain:+.1f} dB "
                                        f"- dialogue will sit about {raw - gain:.0f} dB low here; use a separated dialogue stem "
                                        f"or a quieter take for this segment")
            take_gain[p["id"]] = gain
            entry["gain_db"] = round(gain, 2)
            k = len(labels)
            inputs += ["-i", str(path)]
            dur = a1 - a0
            delay_ms = max(0.0, (p["start_s"] - lead) * 1000.0)
            chains.append(f"[{k}:a]atrim=start={a0:.6f}:end={a1:.6f},asetpts=PTS-STARTPTS,{STEREO},volume={gain:.3f}dB,"
                          f"afade=t=in:d=0.01,afade=t=out:st={max(0.0, dur - 0.12):.6f}:d=0.12,"
                          f"adelay={delay_ms:.3f}:all=1[d{k}]")
            labels.append(f"[d{k}]")
        dlg_bus = tmp / "bus_dialogue.wav"
        if labels:
            graph = ";".join(chains) + ";" + "".join(labels) + \
                f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,{limiter(-1.0)},{fit(N)}[out]"
            run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", *wav_out(dlg_bus)],
                "building the dialogue bus")
        else:
            silence(dlg_bus, N)
            warnings.append("no segment carries sound: the dialogue bus is silent")

        # ---- 3. effects bus (non-dialogue stems + ambience beds) --------------------------------------
        inputs, chains, labels = [], [], []
        for p in plan:
            s = p["seg"]
            if not s.get("nondialogue"):
                continue
            k = len(labels)
            d = p["src_out"] - p["src_in"]
            inputs += ["-i", str(resolve(s["nondialogue"]))]
            chains.append(f"[{k}:a]atrim=start={p['src_in']:.6f}:end={p['src_out']:.6f},asetpts=PTS-STARTPTS,{STEREO},"
                          f"volume={take_gain.get(p['id'], 0.0):.3f}dB,afade=t=in:d=0.01,"
                          f"afade=t=out:st={max(0.0, d - 0.03):.6f}:d=0.03,adelay={p['start_s'] * 1000.0:.3f}:all=1[e{k}]")
            labels.append(f"[e{k}]")
        beds = []                                                  # consecutive segments of one scene share one bed
        for p in plan:
            sc = p["seg"].get("scene")
            if sc in amb_cfg:
                if beds and beds[-1]["scene"] == sc and abs(beds[-1]["end"] - p["start_s"]) < 1e-6:
                    beds[-1]["end"] = p["start_s"] + p["dur_s"]
                else:
                    beds.append({"scene": sc, "start": p["start_s"], "end": p["start_s"] + p["dur_s"]})
        for b in beds:
            cfg = amb_cfg[b["scene"]]
            k = len(labels)
            d = b["end"] - b["start"]
            fade = min(0.3, d / 4)
            inputs += ["-stream_loop", "-1", "-i", str(resolve(cfg["file"]))]
            chains.append(f"[{k}:a]atrim=end={d:.6f},asetpts=PTS-STARTPTS,{STEREO},highpass=f=150,lowpass=f=6500,"
                          f"volume={float(cfg.get('gain_db', -34)):.2f}dB,afade=t=in:d={fade:.3f},"
                          f"afade=t=out:st={d - fade:.6f}:d={fade:.3f},adelay={b['start'] * 1000.0:.3f}:all=1[e{k}]")
            labels.append(f"[e{k}]")
        fx_bus = tmp / "bus_effects.wav"
        if labels:
            graph = ";".join(chains) + ";" + "".join(labels) + \
                f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,{limiter(-1.0)},{fit(N)}[out]"
            run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", *wav_out(fx_bus)],
                "building the effects bus")
        else:
            silence(fx_bus, N)

        # ---- 4. music bus (ducked under dialogue) -----------------------------------------------------
        music_bus = tmp / "bus_music.wav"
        duck_db = None
        if music:
            dk = {"threshold": 0.05, "ratio": 4, "attack": 20, "release": 400, **(music.get("duck") or {})}
            fi, fo = float(music.get("fade_in", 0.5)), float(music.get("fade_out", 1.0))
            pre = (f"atrim=end={total:.6f},asetpts=PTS-STARTPTS,{STEREO},volume={float(music.get('gain_db', -6)):.2f}dB,"
                   f"afade=t=in:d={fi:.3f},afade=t=out:st={max(0.0, total - fo):.6f}:d={fo:.3f},{fit(N)}")
            loop = ["-stream_loop", "-1"] if music.get("loop") else []
            plain = tmp / "bus_music_unducked.wav"
            run(["ffmpeg", "-v", "error", "-y", *loop, "-i", str(resolve(music["file"])), "-vn", "-af", pre, *wav_out(plain)],
                "preparing the music")
            run(["ffmpeg", "-v", "error", "-y", "-i", str(plain), "-i", str(dlg_bus), "-filter_complex",
                 f"[0:a][1:a]sidechaincompress=threshold={dk['threshold']}:ratio={dk['ratio']}:attack={dk['attack']}:"
                 f"release={dk['release']}:knee=4:makeup=1,{fit(N)}[out]", "-map", "[out]", *wav_out(music_bus)],
                "ducking the music")

            def mean_db(path: Path, t0: float, t1: float) -> float | None:
                r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                         f"atrim=start={t0:.3f}:end={t1:.3f},volumedetect", "-f", "null", "-"], "measuring ducking")
                m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
                return float(m.group(1)) if m else None
            spans = []
            for p in plan:                                           # measured where lines are known to be spoken
                for ln in p["seg"].get("lines") or []:
                    if ln.get("start") is not None and ln.get("end") is not None and ln["end"] - ln["start"] >= 0.5:
                        spans.append((p["start_s"] + ln["start"], p["start_s"] + ln["end"]))
            diffs = []
            for t0, t1 in spans[:6]:
                x, y = mean_db(plain, t0, t1), mean_db(music_bus, t0, t1)
                if x is not None and y is not None and x > -80:
                    diffs.append(x - y)
            if diffs:
                duck_db = round(sum(diffs) / len(diffs), 1)
                if not 3.0 <= duck_db <= 16.0:
                    warnings.append(f"music is ducked by {duck_db} dB under dialogue (useful range is roughly 6-14 dB): "
                                    f"adjust music.duck.threshold / ratio or music.gain_db")
        else:
            silence(music_bus, N)

        # ---- 5. master ----------------------------------------------------------------------------------
        mix_pre = tmp / "mix_pre.wav"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(dlg_bus), "-i", str(fx_bus), "-i", str(music_bus), "-filter_complex",
             f"[0:a][1:a][2:a]amix=inputs=3:normalize=0:dropout_transition=0,{limiter(-1.0)},{fit(N)}[out]",
             "-map", "[out]", *wav_out(mix_pre)], "summing the buses")
        tgt_i, tgt_tp = float(loud["program_lufs"]), float(loud["true_peak"])
        mix = tmp / "mix.wav"
        pre_meas = measure(mix_pre)
        if pre_meas is None:
            shutil.copyfile(mix_pre, mix)
            norm = "none (programme is silent)"
            warnings.append("programme is silent or too quiet to measure: loudness normalisation skipped")
        else:
            in_i, in_tp = pre_meas
            gain = tgt_i - in_i
            if in_tp + gain <= tgt_tp:
                run(["ffmpeg", "-v", "error", "-y", "-i", str(mix_pre), "-af", f"volume={gain:.3f}dB,{fit(N)}", *wav_out(mix)],
                    "applying programme gain")
                norm = f"linear gain {gain:+.2f} dB"
            else:
                for _ in range(3):                                   # the limiter costs a little loudness: compensate
                    run(["ffmpeg", "-v", "error", "-y", "-i", str(mix_pre), "-af",
                         f"volume={gain:.3f}dB,{limiter(tgt_tp - 0.3)},{fit(N)}", *wav_out(mix)], "applying programme gain + limiter")
                    got, _pk = ebur128(mix)
                    if got is None or abs(got - tgt_i) <= 0.2:
                        break
                    gain += tgt_i - got
                shaved = in_tp + gain - (tgt_tp - 0.3)
                norm = f"gain {gain:+.2f} dB + limiter (loudest peaks reduced by about {shaved:.1f} dB)"
                if shaved > 4.0:
                    warnings.append(f"reaching {tgt_i:g} LUFS takes {shaved:.1f} dB of limiting on the loudest peaks - audible "
                                    f"pumping is likely; lower the effects / music, or set loudness.program_lufs to -16")

        # ---- 6. mux + verify ----------------------------------------------------------------------------
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-i", str(video_only), "-i", str(mix), "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", str(AR), "-movflags", "+faststart", str(out)], "muxing")
        shutil.copyfile(mix, out.with_suffix(".mix.wav"))
        if a.stems_out:
            sd = Path(a.stems_out)
            sd.mkdir(parents=True, exist_ok=True)
            for name, f in (("dialogue", dlg_bus), ("effects", fx_bus), ("music", music_bus)):
                shutil.copyfile(f, sd / f"{out.stem}.{name}.wav")
        vdur, adur = stream_duration(out, "v"), stream_duration(out, "a")
        integ, peak = ebur128(out)
        checks = {"picture_sound_same_length": abs(vdur - adur) <= 2.0 / fps + 0.03,
                  "frame_count_matches_plan": abs(vdur - total) <= 1.0 / fps}
        if pre_meas is not None and integ is not None:
            checks["loudness_within_1LU"] = abs(integ - tgt_i) <= 1.0
            checks["true_peak_at_most_-1dBTP"] = peak is not None and peak <= -1.0 + 0.05
        report = {"output": str(out), "fps": fps, "size": [W, H], "total_frames": total_frames, "duration_s": round(total, 4),
                  "video_s": round(vdur, 4), "audio_s": round(adur, 4), "segments": seg_report,
                  "loudness": {"dialogue_target_lufs": loud["dialogue_lufs"], "target_lufs": tgt_i, "measured_lufs": integ,
                               "true_peak_dbfs": peak, "pre_master_lufs": pre_meas[0] if pre_meas else None,
                               "normalization": norm},
                  "music_duck_db": duck_db, "subtitles_burned": bool(a.ass), "checks": checks, "warnings": warnings}
        out.with_suffix(".mix.report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        for e in seg_report:
            if e.get("gain_db") is not None:
                print(f"  {e['id']:>6}  {e.get('basis', '-'):11s} {e.get('measured_lufs', '-')} LUFS -> {e['gain_db']:+.2f} dB")
        for w_ in warnings:
            print("WARN ", w_)
        print(f"picture {vdur:.3f}s / sound {adur:.3f}s / plan {total:.3f}s ; loudness {integ} LUFS (target {tgt_i:g}), "
              f"peak {peak} dBTP ; {norm}" + (f" ; music ducked {duck_db} dB" if duck_db is not None else ""))
        ok = all(checks.values())
        print(("OK  " if ok else "FAIL ") + f"{out}  " + " ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in checks.items()))
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
