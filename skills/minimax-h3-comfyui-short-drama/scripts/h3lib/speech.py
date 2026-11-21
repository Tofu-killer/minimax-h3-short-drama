"""Shared speech helpers: get word/char timings for a clip and map them onto the locked dialogue text.

Rule used everywhere in this skill: subtitle and QC text ALWAYS comes from the storyboard (locked lines);
ASR / forced alignment is only trusted for timing and for "was this line actually spoken".

Timing back-ends (all return units = [{"text", "start", "end"}], seconds relative to the given wav):
  * faster-whisper word timestamps (default; `pip install faster-whisper`), biased with the locked text
  * any external aligner via a command template that prints the units as JSON on stdout
    (e.g. a Qwen3-ForcedAligner wrapper living in its own venv)
  * a pre-computed units JSON file
"""
from __future__ import annotations

import difflib
import json
import re
import shlex
import subprocess
import sys
import wave
from pathlib import Path

PUNCT = re.compile(r"[\s，。！？、；：“”‘’…—·,.!?;:\"'()（）《》〈〉<>\[\]【】~～\-]+")


def norm(s: str) -> str:
    return PUNCT.sub("", s or "").lower()


def extract_wav(src: Path, dest: Path, start: float | None = None, end: float | None = None, sr: int = 16000) -> bool:
    """Decode [start, end) of src's first audio stream to mono PCM wav. False when src has no audio."""
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name",
                            "-of", "csv=p=0", str(src)], capture_output=True, text=True)
    if not probe.stdout.strip():
        return False
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if start is not None and start > 0:
        cmd += ["-ss", f"{start:.4f}"]
    cmd += ["-i", str(src)]
    if end is not None:
        cmd += ["-t", f"{end - (start or 0):.4f}"]
    cmd += ["-vn", "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", str(dest)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and dest.exists() and dest.stat().st_size > 1000


def _load_wav(path: Path):
    import numpy as np
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
        arr = np.frombuffer(data, dtype="<i2").astype("float32") / 32768.0
        if w.getnchannels() > 1:
            arr = arr.reshape(-1, w.getnchannels()).mean(axis=1)
    return arr


_MODEL_CACHE: dict = {}


def units_faster_whisper(wav: Path, model: str = "small", language: str = "zh", prompt: str = "", device: str = "auto"):
    """-> (units, info) where info has no_speech / language probabilities per segment."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed: pip install faster-whisper   (or use --aligner cmd / units)")
    key = (model, device)
    if key not in _MODEL_CACHE:
        if device == "auto":
            try:
                import ctranslate2
                device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except Exception:  # noqa: BLE001
                device = "cpu"
        _MODEL_CACHE[key] = WhisperModel(model, device=device, compute_type="float16" if device == "cuda" else "int8")
    segs, _info = _MODEL_CACHE[key].transcribe(_load_wav(wav), language=language, word_timestamps=True, vad_filter=False,
                                               initial_prompt=prompt or None, condition_on_previous_text=False,
                                               beam_size=5, temperature=0.0)
    units, seg_info = [], []
    for s in segs:
        seg_info.append({"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(),
                         "no_speech_prob": round(float(s.no_speech_prob), 3)})
        for w in (s.words or []):
            if w.word.strip():
                units.append({"text": w.word.strip(), "start": float(w.start), "end": float(w.end),
                              "prob": round(float(getattr(w, "probability", 1.0) or 0.0), 3)})
    return units, seg_info


def units_from_cmd(template: str, wav: Path, text_file: Path):
    """Run an external aligner. The template may use {audio} and {text}; stdout must be a JSON list of units."""
    cmd = [part.format(audio=str(wav), text=str(text_file)) for part in shlex.split(template, posix=False)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"aligner command failed ({r.returncode}): {r.stderr.strip()[:300]}")
    out = r.stdout[r.stdout.find("["):]
    return json.loads(out), []


try:                                    # optional: compare Chinese by sound, so ASR homophone slips (跑刀 / 跑道) still match
    from pypinyin import lazy_pinyin as _lazy_pinyin
    PHONETIC = True
except ImportError:                     # falls back to exact character matching
    _lazy_pinyin = None
    PHONETIC = False


def keys(text: str) -> list[str]:
    """One comparison key per character of the normalised text (toneless pinyin for CJK when available)."""
    if not PHONETIC:
        return list(text)
    out = []
    for ch in text:
        out.append(_lazy_pinyin(ch)[0] if "\u4e00" <= ch <= "\u9fff" else ch)
    return out


def flatten_chars(units: list[dict]) -> list[tuple[str, float, float, float]]:
    chars = []
    for u in units:
        t = norm(u["text"])
        d = (u["end"] - u["start"]) / max(len(t), 1)
        chars += [(ch, u["start"] + k * d, u["start"] + (k + 1) * d, float(u.get("prob", 1.0))) for k, ch in enumerate(t)]
    return chars


def envelope(wav: Path, hop: float = 0.01):
    """Loudness curve of the speech band in dB, one value per `hop` seconds (numpy). Pre-emphasis removes the
    rumble and room tone that would otherwise hide where a voice starts."""
    import numpy as np
    x = _load_wav(wav)
    if len(x) < 400:
        return np.zeros(0), hop
    x = np.append(x[0], x[1:] - 0.97 * x[:-1])
    with wave.open(str(wav), "rb") as w:
        sr = w.getframerate()
    n = int(sr * hop)
    k = len(x) // n
    rms = np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(axis=1) + 1e-12)
    rms = np.convolve(rms, np.ones(3) / 3, mode="same")
    return 20 * np.log10(rms + 1e-9), hop


def refine_span(env, hop: float, first_s: float, last_s: float) -> tuple[float, float, float]:
    """Word times from a recogniser drift: the first word is often placed in the silence before the voice
    (measured on real takes: cues 0.4-1.2 s early). Pull the start forward to where the speech band actually
    rises, and the end back to where it falls. Returns (start, end, largest shift in seconds).
    Only moves inwards: speech that begins before the recognised start is left alone."""
    import numpy as np
    if len(env) == 0 or last_s <= first_s:
        return first_s, last_s, 0.0
    a, b = int(first_s / hop), min(len(env), int(last_s / hop) + 1)
    if b - a < 5:
        return first_s, last_s, 0.0
    floor = float(np.percentile(env, 10))
    peak = float(env[a:b].max())
    thr = max(floor + 8.0, peak - 22.0)
    if peak - floor < 10.0:                              # no clear voice above the bed: nothing to snap to
        return first_s, last_s, 0.0
    loud = env[a:b] >= thr
    run = 0
    on = None
    for i, v in enumerate(loud):                         # first stretch of >= 50 ms above the threshold
        run = run + 1 if v else 0
        if run >= 5:
            on = i - 4
            break
    if on is None:
        return first_s, last_s, 0.0
    idx = np.where(loud)[0]
    off = int(idx[-1]) + 1
    start = (a + on) * hop
    end = (a + off) * hop
    start = start if start - first_s > 0.10 else first_s
    end = end if last_s - end > 0.15 else last_s
    if end - start < 0.15:
        return first_s, last_s, 0.0
    return round(start, 3), round(end, 3), round(max(start - first_s, last_s - end), 3)


def map_lines(lines: list[dict], units: list[dict]) -> dict:
    """Align the locked lines (each has "text") to the timed units.

    Returns {"lines": [{..., first_s, last_s, coverage, head_missing, tail_missing}], "similarity",
             "ref_chars", "hyp_chars", "inserted_chars", "hyp_text"}.
    first_s / last_s are raw speech bounds (None when nothing of the line was heard).
    """
    chars = flatten_chars(units)
    hyp = "".join(c[0] for c in chars)
    spans, ref = [], ""
    for ln in lines:
        t = norm(ln["text"])
        spans.append((len(ref), len(ref) + len(t)))
        ref += t
    sm = difflib.SequenceMatcher(None, keys(ref), keys(hyp), autojunk=False)
    r2h, matched_h = {}, set()
    for tag, i1, i2, j1, _j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                r2h[i1 + k] = j1 + k
                matched_h.add(j1 + k)
    out = []
    for ln, (a, b) in zip(lines, spans):
        hit = [r2h[i] for i in range(a, b) if i in r2h]
        n = max(b - a, 1)
        edge = min(3, n)
        row = dict(ln)
        row.update({"coverage": round(len(hit) / n, 3),
                    "head_missing": not any(i in r2h for i in range(a, a + edge)),
                    "tail_missing": not any(i in r2h for i in range(b - edge, b)),
                    "first_s": round(chars[hit[0]][1], 3) if hit else None,
                    "last_s": round(chars[hit[-1]][2], 3) if hit else None,
                    "confidence": round(sum(chars[i][3] for i in hit) / len(hit), 3) if hit else None})
        out.append(row)
    return {"lines": out, "similarity": round(sm.ratio(), 3) if (ref or hyp) else 1.0, "ref_chars": len(ref),
            "hyp_chars": len(hyp), "inserted_chars": len(hyp) - len(matched_h), "hyp_text": hyp,
            "matching": "pinyin" if PHONETIC else "exact-characters"}


def get_units(aligner: str, wav: Path, lines: list[dict], *, model: str, language: str, device: str,
              cmd: str | None, units_file: Path | None, tmp: Path, bias: bool = False):
    """bias=True feeds the locked text to the recogniser as a hint. Leave it off: on real H3 takes a hinted
    whisper-small degenerated into repeated junk tokens and "heard" lines from other segments, while the
    unhinted pass plus sound-based matching was accurate (tested 2026-11). Never use it for QC."""
    if aligner == "units":
        if not units_file or not units_file.exists():
            sys.exit(f"units file missing: {units_file}")
        return json.loads(units_file.read_text(encoding="utf-8")), []
    if aligner == "cmd":
        if not cmd:
            sys.exit("--aligner cmd needs --aligner-cmd \"... {audio} ... {text} ...\"")
        tf = tmp / (wav.stem + ".txt")
        tf.write_text("\n".join(ln["text"] for ln in lines), encoding="utf-8")
        return units_from_cmd(cmd, wav, tf)
    prompt = "".join(ln["text"] for ln in lines)[:200] if bias else ""
    return units_faster_whisper(wav, model=model, language=language, prompt=prompt, device=device)
