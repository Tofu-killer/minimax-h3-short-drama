#!/usr/bin/env python3
"""Lint a MiniMax H3 prompt (three-part or six-part) before submitting it.

    python3 lint_prompt.py prompts/ep01/s03.txt --seconds 10 [--images 4 --videos 0 --audios 1] [--mode ref2va|i2va|fl2va|l2va|t2va]

Checks the machine-checkable rules collected from 23 prompt tools and the
official guides (see references/prompt-format.md §7b/§8):
field names + order, [Shot 1] without timecode, strictly increasing MM:SS.mmm
below the effective duration (17k+5 frame grid), >=1.2 s per shot, <d> tags
paired and starting with [Language], (S1..) numbering, labels defined before
use / no phantom media / no unused media, retention keywords, negation words,
"completely still", curly quotes / full-width brackets, markdown fences, and
word budget (350-500 for ref2va detailed_description).  ERRORs exit 1.
"""
import argparse, re, sys
from pathlib import Path

SIX = ["subject_definitions", "summary", "retention_analysis", "detailed_description", "overall_soundscape", "non_diegetic_music"]
THREE = ["integrated_multimodal_description", "overall_soundscape", "non_diegetic_music"]
RETENTION = {"fully_preserved", "partially_preserved", "attribute_transfer", "weak_reference", "fully_copy"}
NEG = re.compile(r"\b(no|not|never|without|don't|doesn't|avoid|nothing)\b", re.I)
NEG_OK = re.compile(r"with no camera movement whatsoever|no other (item|garment|person|people)|is not transferred|not reuse", re.I)
STILL = re.compile(r"completely still|doing nothing|does not move at all|remains? (perfectly )?motionless", re.I)
CUT = re.compile(r"\[Shot (\d+)\]\s*(?:At (\d{2}):(\d{2})\.(\d{3}),)?")
LABEL = re.compile(r"<(Picture|Video|Audio|Subject) (\d+)>")
BAD_LABEL = re.compile(r"<(Image|Environment|Ref|Reference) \d+>")


def effective_seconds(req):
    frames = 24 * req
    k = max(0, -(-(frames - 5) // 17))
    return (17 * k + 5) / 24.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt"); ap.add_argument("--seconds", type=float, required=True)
    ap.add_argument("--images", type=int, default=None); ap.add_argument("--videos", type=int, default=0); ap.add_argument("--audios", type=int, default=0)
    ap.add_argument("--mode", default=None)
    a = ap.parse_args()
    text = Path(a.prompt).read_text(encoding="utf-8")
    errs, warns = [], []
    eff = effective_seconds(a.seconds)

    fields = SIX if "subject_definitions:" in text else THREE
    mode = a.mode or ("ref2va" if fields is SIX else "base")
    pos = [text.find(f + ":") for f in fields]
    for f, p in zip(fields, pos):
        if p < 0: errs.append(f"missing field {f}")
    if all(p >= 0 for p in pos) and pos != sorted(pos): errs.append("fields out of order: " + " → ".join(fields))
    body_field = "detailed_description" if fields is SIX else "integrated_multimodal_description"
    m = re.search(body_field + r":(.*?)(?:\n\s*\n|\Z)", text, re.S)
    body = m.group(1) if m else text

    if "```" in text or "<think>" in text: errs.append("markdown fence or <think> present")
    if re.search(r"[“”‘’＜＞（）［］]", text): errs.append("curly quotes or full-width brackets present")
    if "\n" in body.strip(): warns.append("line breaks inside the description are read as cuts")

    shots = list(CUT.finditer(body))
    if not shots: errs.append("no [Shot N] markers")
    prev_t = 0.0
    for i, s in enumerate(shots):
        n = int(s.group(1))
        if n != i + 1: errs.append(f"shot numbering jumps at [Shot {n}]")
        if i == 0 and s.group(2): errs.append("[Shot 1] must not carry a timecode")
        if i > 0:
            if not s.group(2): errs.append(f"[Shot {n}] missing 'At MM:SS.mmm,'"); continue
            t = int(s.group(2)) * 60 + int(s.group(3)) + int(s.group(4)) / 1000
            if t <= prev_t: errs.append(f"[Shot {n}] timecode {t:.3f} not increasing")
            if t - prev_t < 1.2: errs.append(f"[Shot {n}] previous shot shorter than 1.2 s")
            if t >= eff - 1.2: errs.append(f"[Shot {n}] cut at {t:.3f}s is inside the last 1.2 s of the {eff:.3f}s clip")
            prev_t = t
    nshots = len(shots)
    lo, hi = (1, 2) if a.seconds <= 6 else (2, 3) if a.seconds <= 10 else (3, 5)
    if nshots and not (lo <= nshots <= hi): warns.append(f"{nshots} shots for {a.seconds}s (suggested {lo}-{hi})")

    d_open, d_close = text.count("<d>"), text.count("</d>")
    if d_open != d_close: errs.append(f"<d> tags unbalanced ({d_open} open / {d_close} close)")
    for dm in re.finditer(r"<d>(.*?)</d>", text, re.S):
        if not re.match(r"\s*\[[A-Z][a-zA-Z]+\]", dm.group(1)): errs.append(f"<d> without [Language] tag: {dm.group(1)[:30]!r}")
        if "..." in dm.group(1) or "……" in dm.group(1): warns.append(f"ellipsis inside dialogue invites garbled filler words; use a comma or split the line: {dm.group(1)[:30]!r}")
    for f in ("subject_definitions", "summary", "retention_analysis", "overall_soundscape", "non_diegetic_music"):
        fm = re.search(f + r":(.*?)(?:\n\s*\n|\Z)", text, re.S)
        if fm and "<d>" in fm.group(1): errs.append(f"<d> inside {f}")
    if "(S?)" in text: errs.append("unresolved speaker marker (S?)")
    speakers = sorted({int(x) for x in re.findall(r"\(S(\d+)", text)})
    n_audio_defs = len(re.findall(r"<Audio \d+> is the voice", text))
    if n_audio_defs > len(speakers): warns.append(f"{n_audio_defs} voice references but only {len(speakers)} speaker(s): attach timbre only for characters who speak in this segment")
    if speakers and speakers != list(range(1, len(speakers) + 1)): errs.append(f"speaker ids not contiguous from 1: {speakers}")
    for vo in re.finditer(r"off-screen voiceover[^<]*<d>.*?</d>(.{0,400})", text, re.S):
        if "lips" not in vo.group(1): errs.append("off-screen voiceover without 'lips remain completely closed' within 400 chars")

    labels = LABEL.findall(text)
    if BAD_LABEL.search(text): errs.append("non-standard label (<Image N>/<Environment N>) used")
    counts = {k: {int(n) for t, n in labels if t == k} for k in ("Picture", "Video", "Audio", "Subject")}
    for k, n in (("Picture", a.images), ("Video", a.videos), ("Audio", a.audios)):
        if n is None: continue
        used = counts[k]
        if used and max(used) > n: errs.append(f"<{k} {max(used)}> referenced but only {n} {k.lower()}(s) wired")
        missing = set(range(1, n + 1)) - used
        if missing: warns.append(f"wired {k.lower()}(s) never referenced: {sorted(missing)}")
    if fields is SIX:
        ra = re.search(r"retention_analysis:(.*?)(?:\n\s*\n|\Z)", text, re.S)
        if ra:
            if "(S" in ra.group(1): errs.append("retention_analysis contains a speaker marker")
            if not any(w in ra.group(1) for w in RETENTION): errs.append("retention_analysis has no retention keyword")
        sd = re.search(r"subject_definitions:(.*?)(?:\n\s*\n|\Z)", text, re.S)
        if sd:
            defined = {int(n) for n in re.findall(r"<Subject (\d+)>", sd.group(1))}
            used = {int(n) for n in re.findall(r"<Subject (\d+)>", body)}
            if used - defined: errs.append(f"subjects used but not defined: {sorted(used - defined)}")
            if defined - used: warns.append(f"subjects defined but unused in description: {sorted(defined - used)}")
        words = len(body.split())
        if words < 350: warns.append(f"detailed_description {words} words (<350: model may invent or burn subtitles)")
        if words > 700: errs.append(f"detailed_description {words} words (>700)")
    else:
        if mode in ("i2va", "fl2va", "l2va") and "aligns with" not in text and "is fully referenced" not in text:
            errs.append(f"{mode} prompt missing the alignment instruction line")
        if "aligns with the" in text:
            for sm in re.finditer(r"aligns with the ([\d.]+)-second mark", text):
                v = float(sm.group(1))
                if v > 0 and abs(v - eff) > 0.02: errs.append(f"alignment says {v}s but effective duration is {eff:.2f}s")

    for nm in NEG.finditer(body):
        ctx = body[max(0, nm.start() - 40): nm.end() + 40]
        if not NEG_OK.search(ctx): warns.append(f"negation: …{ctx.strip()}…")
    if STILL.search(body): errs.append("'completely still'-type phrase freezes the whole shot")
    sound = re.search(r"overall_soundscape:(.*?)(?:\n\s*\n|\Z)", text, re.S)
    music = re.search(r"non_diegetic_music:(.*?)(?:\n\s*\n|\Z)", text, re.S)
    for name, fm in (("overall_soundscape", sound), ("non_diegetic_music", music)):
        if fm and re.search(r"\b(tense|sad|melancholy|eerie|emotional|dramatic|cinematic)\b", fm.group(1), re.I):
            warns.append(f"{name} uses a mood adjective instead of concrete sources/instruments")

    for e in errs: print("ERROR", e)
    for w in warns: print("WARN ", w)
    print(f"{'FAIL' if errs else 'PASS'}: {len(errs)} error(s), {len(warns)} warning(s); effective duration {eff:.3f}s, {nshots} shots")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
