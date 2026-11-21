#!/usr/bin/env python3
"""Lint a MiniMax H3 prompt (three-part or six-part) before submitting it.

    python3 lint_prompt.py prompts/ep01/s03.txt --seconds 10 [--images 4 --videos 0 --audios 1] [--mode ref2va|i2va|fl2va|l2va|t2va]

Checks the machine-checkable rules collected from 23 prompt tools and the
official guides (see references/prompt-format.md §0–§5 and §8):
field names + order, [Shot 1] without timecode, strictly increasing MM:SS.mmm
below the effective duration (17k+5 frame grid), >=1.2 s per shot, <d> tags
paired and starting with [Language], (S1..) numbering, labels defined before
use / no phantom media / no unused media, retention keywords (audio lines must use the audio
markers), unresolved {placeholders}, negation words, "completely still", curly quotes / full-width
brackets, markdown fences, and length - all warnings: under 350 words the model improvises; over 700 words, or
240 words in one shot (300 in the first and the last shot, which carry the set-up and the end state), it follows
less closely; over 7000 characters
the cloud API refuses the text (the local ComfyUI node has no limit).
ERRORs exit 1.

    python3 lint_prompt.py prompts/ep01/s03.txt            # reads prompts/ep01/s03.media.json written by build_prompts.py
"""
import argparse, re, sys
from pathlib import Path


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()

SIX = ["subject_definitions", "summary", "retention_analysis", "detailed_description", "overall_soundscape", "non_diegetic_music"]
THREE = ["integrated_multimodal_description", "overall_soundscape", "non_diegetic_music"]
RETENTION = {"fully_preserved", "partially_preserved", "attribute_transfer", "weak_reference", "fully_copy", "partially_copy", "reference"}
AUDIO_MARKERS = ("fully_copy", "partially_copy", "reference", "weak_reference")      # official markers for <Audio N> lines
NEG = re.compile(r"\b(no|not|never|without|don't|doesn't|do not|does not|avoid|nothing)\b", re.I)
NEG_OK = re.compile(r"with no camera movement whatsoever|no other (item|garment|person|people)|is not transferred|never transfer facial traits"
                    r"|no black letterbox bars"
                    r"|without copying the original signal", re.I)
STILL = re.compile(r"completely still|doing nothing|does not move at all|remains? (perfectly )?motionless", re.I)
CUT = re.compile(r"\[Shot (\d+)\]\s*(?:At (\d{2}):(\d{2})\.(\d{3}),)?")
LABEL = re.compile(r"<(Picture|Video|Audio|Subject) (\d+)>")
BARE_PICTURE = re.compile(r"(?<![<\w])Picture (\d+)\b")      # the official FL2VA wording writes Picture 1 / Picture 2 without brackets
UNFILLED = re.compile(r"\{[A-Za-z0-9_\u4e00-\u9fff-]+\}")
BAD_LABEL = re.compile(r"<(Image|Environment|Ref|Reference) \d+>")


def effective_seconds(req):
    frames = 24 * req
    k = max(0, -(-(frames - 5) // 17))
    return (17 * k + 5) / 24.0


def main():
    ap = argparse.ArgumentParser(description="Lint a MiniMax H3 prompt before submitting it. With the .media.json that "
                                             "build_prompts.py writes next to the prompt, no other argument is needed.")
    ap.add_argument("prompt", help="prompt text file")
    ap.add_argument("--media", help="the segment's .media.json (default: <prompt>.media.json next to the prompt, when it exists); "
                                    "supplies --seconds, --images, --audios and --mode")
    ap.add_argument("--seconds", type=float, help="requested segment length in seconds")
    ap.add_argument("--images", type=int, default=None, help="number of reference / frame images wired")
    ap.add_argument("--videos", type=int, default=0, help="number of reference videos wired")
    ap.add_argument("--audios", type=int, default=None, help="number of reference audios wired")
    ap.add_argument("--mode", default=None, help="ref2va | i2va | fl2va | l2va | t2va")
    a = ap.parse_args()
    media_path = Path(a.media) if a.media else Path(a.prompt).with_suffix(".media.json")
    if a.media and not media_path.exists():
        sys.exit(f"media file not found: {media_path}")
    if media_path.exists():
        import json
        meta = json.loads(media_path.read_text(encoding="utf-8"))
        kinds = [m.get("type") for m in meta.get("media", [])]
        if a.seconds is None: a.seconds = float(meta["duration"])
        if a.images is None: a.images = kinds.count("image")
        if a.audios is None: a.audios = kinds.count("audio")
        if a.mode is None: a.mode = meta.get("mode")
    if a.seconds is None:
        sys.exit("--seconds is required when there is no <prompt>.media.json next to the prompt (or pass --media)")
    if a.audios is None: a.audios = 0
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
    for bad in re.finditer(r"[“”‘’＜＞（）［］]", text):
        errs.append(f"curly quote or full-width bracket {bad.group(0)!r} at …{text[max(0, bad.start() - 25):bad.end() + 25].strip()}… "
                    f"(often Chinese text pasted into an English field: write the field in English and refer to assets as {asset_id})")
        break
    for um in UNFILLED.finditer(text):
        errs.append(f"unresolved placeholder {um.group(0)} at …{text[max(0, um.start() - 30):um.end() + 30].strip()}…")
    if re.search(r"\n(?!\[Shot \d+\])", body.strip()):
        warns.append("a line break inside the description that does not start a new [Shot N] is read as a cut")

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
    lo, hi = (1, 2) if a.seconds <= 6 else (2, 3) if a.seconds <= 10 else (3, 4)
    if "<d>" in text: lo = max(1, lo - 1)                # dialogue segments run one step lower (storyboard-and-assets.md section 1)
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
    sd_block = re.search(r"subject_definitions:(.*?)(?:\n\s*\n|\Z)", text, re.S)
    n_audio_defs = len(re.findall(r"<Audio \d+> is the voice", sd_block.group(1) if sd_block else ""))
    if n_audio_defs > len(speakers): warns.append(f"{n_audio_defs} voice references but only {len(speakers)} speaker(s): attach timbre only for characters who speak in this segment")
    if speakers and speakers != list(range(1, len(speakers) + 1)): errs.append(f"speaker ids not contiguous from 1: {speakers}")
    for vo in re.finditer(r"off-screen voiceover[^<]*<d>.*?</d>(.{0,400})", text, re.S):
        if "lips" not in vo.group(1): errs.append("off-screen voiceover without 'lips remain completely closed' within 400 chars")

    labels = LABEL.findall(text)
    if BAD_LABEL.search(text): errs.append("non-standard label (<Image N>/<Environment N>) used")
    counts = {k: {int(n) for t, n in labels if t == k} for k in ("Picture", "Video", "Audio", "Subject")}
    counts["Picture"] |= {int(n) for n in BARE_PICTURE.findall(text)}
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
            for am in re.finditer(r"<Audio \d+>[^:\n]*:\s*([a-z_]+)", ra.group(1)):
                if am.group(1) not in AUDIO_MARKERS:
                    errs.append(f"audio retention marker {am.group(1)!r}: the official markers for audio are {', '.join(AUDIO_MARKERS)}")
        sd = re.search(r"subject_definitions:(.*?)(?:\n\s*\n|\Z)", text, re.S)
        if sd:
            defined = {int(n) for n in re.findall(r"<Subject (\d+)>", sd.group(1))}
            used = {int(n) for n in re.findall(r"<Subject (\d+)>", body)}
            if used - defined: errs.append(f"subjects used but not defined: {sorted(used - defined)}")
            if defined - used: warns.append(f"subjects defined but unused in description: {sorted(defined - used)}")
        words = len(body.split())
        if words < 350: warns.append(f"detailed_description {words} words (<350: model may invent or burn subtitles)")
    # length advice holds for both layouts (a three-part prompt without pictures carries looks and place in words, so it runs long too)
    words = len(body.split())
    if words > 700: warns.append(f"{body_field} {words} words (>700): long descriptions get followed less closely - split the segment or trim the shots")
    for sm in re.finditer(r"\[Shot (\d+)\](.*?)(?=\[Shot \d+\]|\Z)", body, re.S):
        n_words = len(sm.group(2).split())
        edge = sm.group(1) == "1" or int(sm.group(1)) == nshots     # the first shot carries the set-up, the last one the end state
        cap = 300 if edge else 240
        if fields is THREE and sm.group(1) == "1": cap = 380          # ... and, without pictures, every look and the whole place
        if n_words > cap: warns.append(f"[Shot {sm.group(1)}] runs to {n_words} words (over {cap}): one shot holds one action and one camera move")
    if len(text) > 7000: warns.append(f"prompt is {len(text)} characters: the MiniMax cloud API rejects text over 7000; the local "
                                      f"ComfyUI node has no length limit, but a prompt this long is followed less closely")
    if fields is SIX:
        pass
    else:
        if mode in ("i2va", "fl2va", "l2va") and "aligns with" not in text and "is fully referenced" not in text:
            errs.append(f"{mode} prompt missing the alignment instruction line")
        if "aligns with the" in text:
            for sm in re.finditer(r"aligns with the ([\d.]+)-second mark", text):
                v = float(sm.group(1))
                if v > 0 and abs(v - eff) > 0.02: errs.append(f"alignment says {v}s but effective duration is {eff:.2f}s")

    neg_scope = body
    for f in ("subject_definitions", "retention_analysis"):
        fm = re.search(f + r":(.*?)(?:\n\s*\n|\Z)", text, re.S)
        if fm: neg_scope += " " + fm.group(1)
    for nm in NEG.finditer(neg_scope):
        ctx = neg_scope[max(0, nm.start() - 40): nm.end() + 40]
        if not NEG_OK.search(ctx): warns.append(f"negation: …{ctx.strip()}…")
    if STILL.search(body): errs.append("'completely still'-type phrase freezes the whole shot")
    for cm in re.finditer(r"\b(?:with|at) (?:a )?(medium|moderate|normal|average) (amplitude|speed)\b", body, re.I):
        warns.append(f"camera modifier \"{cm.group(0)}\": the official modifiers are small / large amplitude and slow / fast speed; "
                     f"a medium move is written without the modifier")
    turns = len(re.findall(r"\b(turns?|spins?|turning|spinning)\b", body, re.I))
    if turns > 1: warns.append(f"{turns} turn/spin verbs in one segment (keep <= 1; extra turns drift)")
    micro = re.findall(r"\b(winks?|blows? a kiss|raises? (?:an |one |her |his )?eyebrows?|licks?)\b", body, re.I)
    if micro: warns.append(f"micro-expression verbs {sorted(set(m.lower() for m in micro))} tend to force a face close-up")
    if d_open == 0 and not re.search(r"nobody speaks|no words|no dialogue|without speaking", body, re.I):
        warns.append("no dialogue in this segment: state it ('Nobody speaks in this video; every mouth stays closed.') or the model may "
                     "improvise speech - build_prompts.py adds this sentence by itself")
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
