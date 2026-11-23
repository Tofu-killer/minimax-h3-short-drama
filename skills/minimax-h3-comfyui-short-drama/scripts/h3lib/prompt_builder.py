"""Build official-format H3 prompts + content arrays from a Segment.

Layout and wording follow MiniMax's own guides (MiniMax-AI/MiniMax-H3 skills/h3-prompt-writing, files
base-en.txt and ref-en.txt, re-read 2026-11-21):
  * three-part  (T2VA / I2VA / FL2VA)  integrated_multimodal_description / overall_soundscape / non_diegetic_music,
                                       the style opens [Shot 1], field label and text on one line
  * six-part    (Ref2VA)               subject_definitions / summary / retention_analysis / detailed_description /
                                       overall_soundscape / non_diegetic_music, each label on its own line, one
                                       definition and one retention entry per line, every [Shot N] on its own line,
                                       ONE style sentence before [Shot 1] and everything else inside the shots
Reference labels <Picture N> / <Audio N> are numbered by position in the content array.

What the builder adds on its own, because the official examples do it and authors forget:
  * people are never called by name - a definition reads "<Subject 1> is the woman in her early thirties in
    <Picture 1>, with ..." and a prompt without labels calls her "the woman in her early thirties"
    (Character.short_phrase overrides that designation)
  * where a subject is first clearly seen, its look is repeated right after the label
    ("<Subject 2>, the man in his fifties with a lean face, ..., holds her gaze"); at later cuts the main
    subject of the shot gets a short reminder ("<Subject 2>, the man in his fifties from Shot 1")
  * after a spoken line the speaker closes the mouth (Dialogue.after_line overrides the default sentence)
  * a voice reference is cited at every line of its speaker
  * a segment with lines ends on "Speak only the quoted dialogue lines." (a community-measured guard against
    improvised extra words); a segment without lines says that every mouth stays closed

Text fields of the storyboard are inserted as written, so they have to be English sentences or phrases of the
right kind (see assets/agent-prompts/02-storyboard.md): `action`, `lighting`, `performance`, `sound_cue`,
`camera`, `after_line` are full sentences; `framing` is a noun phrase ("a close-up of {a}"); `delivery` is an
adverbial ("softly", "in a low, even voice"); `continuity` / `end_state` describe a state ("{a} stands by the
door, ..."); `identity_phrase` / `voice_phrase` are noun phrases of the form "a <who> with <features>".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from media import audio_item, image_item, text_item
from storyboard import (Dialogue, Episode, Segment, Shot, blocking_sentence, effective_continuity,
                        frames_for_seconds, reference_count, _framing_class)

ROOM_SHOTS = ("medium", "medium wide", "wide")      # framings that show the room: everyone on screen is seen properly

ALLOW_PLANNED = False       # build_prompts.py --allow-planned: "@observed" may fall back to the PLANNED end state (drafts only)
MAX_REF_IMAGES = 9
MAX_REF_AUDIO = 3
NO_SPEECH = "Nobody speaks in this video; every mouth stays closed and only the sounds of the scene are heard."


def timecode(sec: float) -> str:
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m:02d}:{s:06.3f}"


def speaker_ids(seg: Segment) -> dict[str, str]:
    """Stable (S1)/(S2) IDs per segment, in the order the voices are first heard (official rule)."""
    ids: dict[str, str] = {}
    for sh in seg.shots:
        for d in sh.dialogue:
            if d.speaker not in ids:
                ids[d.speaker] = f"S{len(ids) + 1}"
    return ids


def prompt_name(obj, kind: str) -> str:
    """The English label an asset carries inside a prompt. A Chinese display name stays out of the English text."""
    n = (getattr(obj, "name_en", "") or "").strip()
    if n:
        return n
    if obj.name and obj.name.isascii():
        return obj.name
    base = obj.id[5:] if kind == "prop" and obj.id.startswith("prop_") else obj.id
    words = [w for w in re.split(r"[_\-\s]+", base) if w]
    if kind == "character":
        return " ".join(w.capitalize() for w in words)
    return "the " + " ".join(words)


_ARTICLE = re.compile(r"^(?:an?|the)\s+", re.I)
_FEMALE = re.compile(r"\b(woman|girl|lady|mother|grandmother|aunt|sister|daughter|wife|queen|princess|actress|waitress|"
                     r"heroine|female|nun|maid|bride|empress|schoolgirl|businesswoman|policewoman)\b", re.I)
_MALE = re.compile(r"\b(man|boy|gentleman|father|grandfather|uncle|brother|son|husband|king|prince|actor|waiter|hero|"
                   r"male|monk|groom|emperor|schoolboy|businessman|policeman)\b", re.I)


def split_identity(phrase: str) -> tuple[str, str]:
    """"a woman in her early thirties with a sharp oval face, short black hair"  ->
    ("woman in her early thirties", "with a sharp oval face, short black hair").
    The head is who it is, the tail is the feature list (it keeps its own "with" when it has one)."""
    t = _ARTICLE.sub("", (phrase or "").strip().rstrip(". "))
    cuts = [c for c in (t.find(" with "), t.find(",")) if c > 0]
    if not cuts:
        return t, ""
    c = min(cuts)
    return t[:c].strip(), t[c:].lstrip(", ").strip()


def designation(c) -> str:
    """How a person is called in running text: "the woman in her early thirties" (or Character.short_phrase)."""
    s = (getattr(c, "short_phrase", "") or "").strip().rstrip(". ")
    if s:
        return "the " + _ARTICLE.sub("", s)
    return "the " + split_identity(c.identity_phrase)[0]


def full_look(c) -> str:
    """"the woman in her early thirties with a sharp oval face, ..." - the label's look, repeated once in the shots."""
    head, tail = split_identity(c.identity_phrase)
    if not tail:
        return "the " + head
    return f"the {head} {tail}" if tail.startswith("with ") else f"the {head}, {tail}"


def unpictured_look(c) -> dict:
    """What follows the first mention of a person who has no reference picture: the feature list when the
    designation is the head of the identity phrase, the whole phrase when a short_phrase replaced it (and nothing
    when the identity says no more than the designation does)."""
    head, tail = split_identity(c.identity_phrase)
    if (getattr(c, "short_phrase", "") or "").strip():
        whole = c.identity_phrase.strip().rstrip(". ")
        if _ARTICLE.sub("", whole).lower() == _ARTICLE.sub("", designation(c)).lower():
            return {}
        return {"look": whole, "sep": ", "}
    if not tail:
        return {}
    return {"look": tail, "sep": " " if tail.startswith("with ") else ", "}


def possessive(c) -> str:
    stated = {"he": "his", "she": "her", "they": "their"}.get((getattr(c, "pronoun", "") or "").strip().lower())
    if stated:
        return stated
    head = split_identity(c.identity_phrase)[0]
    if _FEMALE.search(head):
        return "her"
    if _MALE.search(head):
        return "his"
    return "their"


def voice_tail(c) -> str:
    """"a man in his fifties with a tired, gravelly voice" -> "with a tired, gravelly voice" (official wording:
    "the middle-aged baker with a calm, slightly raspy voice (S1) ... says")."""
    v = (c.voice_phrase or "").strip().rstrip(". ")
    if not v:
        return ""
    k = v.find(" with ")
    if k >= 0:
        return v[k + 1:]
    v = _ARTICLE.sub("", v)
    return f"speaking in a {v}" if "voice" in v.lower() else f"speaking in a {v} voice"


def definite(text: str) -> str:
    return "the " + _ARTICLE.sub("", (text or "").strip().rstrip(". "))


def scene_brief(description: str, limit: int = 30) -> str:
    """A scene picture carries the layout, so the shot only names the place: the whole description when it is
    short, otherwise its opening clause ("the long hospital corridor at night")."""
    d = (description or "").strip().rstrip(". ")
    if len(d.split()) <= limit:
        return definite(d)
    cuts = [c for c in (d.find(":"), d.find(","), d.find(" with ")) if c > 0]
    return definite(d[:min(cuts)] if cuts else d)


_ADVERBIAL = {"in", "with", "at", "under", "through", "like", "as", "between", "while"}


def delivery_phrase(d: Dialogue) -> str:
    t = (d.delivery or "").strip().rstrip(".,;:")
    if not t:
        return ""
    first = re.sub(r"[^a-z]", "", t.split()[0].lower())
    if first.endswith("ly") or first in _ADVERBIAL:
        return " " + t
    return f" in a voice that is {t}"            # an adjective list still reads as a sentence


PLACEHOLDER = re.compile(r"\{([A-Za-z0-9_一-鿿-]+)\}")


def fill(text: str, labels: dict[str, str]) -> str:
    """Replace {asset_id} tokens with the label assigned for this segment (<Subject N> or a name).
    Writing asset ids instead of hand-numbered <Subject N> keeps the storyboard valid when the
    builder changes the numbering (characters first, then scene, then props)."""
    def sub(m):
        key = m.group(1)
        if key not in labels:
            raise KeyError(key)
        return labels[key]
    return PLACEHOLDER.sub(sub, text or "")


def room_labels(ep: Episode, labels: dict[str, str]) -> dict[str, str]:
    """Labels for a STATE text (continuity / end_state / observed_end_state): it describes the whole room, so it may
    name people and things that are not bound to this segment. Those are written in words."""
    out = {c.id: designation(c) for c in ep.characters}
    out.update({x.id: prompt_name(x, "prop") for x in ep.props})
    out.update({x.id: prompt_name(x, "scene") for x in ep.scenes})
    out.update(labels)
    return out


def style_sentence(style: str) -> str:
    """One sentence before [Shot 1] (ref guide 5.2). A style written as a full sentence is used as it is; a
    comma list ("Live-action, cinematic, shot on 35mm ...") is introduced, not forced into a clause."""
    st = style.strip().rstrip(".")
    if st.lower().startswith("the target video"):
        return st + "."
    st = style_list(st)
    return f"The target video is in the following style: {st[0].lower() + st[1:]}."


NUMBER = ["zero", "one", "two", "three", "four", "five", "six"]


def _sentence(text: str, labels: dict[str, str]) -> str:
    t = fill((text or "").strip(), labels)
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    t = re.sub(r"(?<=[.!?] )([a-z])", lambda m: m.group(1).upper(), t)      # "... flame. the masked man pulls" -> "The masked man"
    return t if t[-1] in ".!?" else t + "."


def style_list(style: str) -> str:
    """A style written as several sentences becomes one comma list, so that it can open [Shot 1] or follow a colon."""
    parts = [x.strip() for x in re.split(r"\.\s+", style.strip().rstrip(".")) if x.strip()]
    return ", ".join([parts[0]] + [x[0].lower() + x[1:] for x in parts[1:]]) if parts else ""


def _state(text: str, labels: dict[str, str]) -> str:
    return fill((text or "").strip(), labels).rstrip(". ")


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


@dataclass
class BuiltPrompt:
    text: str
    content: list[dict]
    labels: dict[str, str]          # e.g. {"char_a": "<Subject 1>", "scene_cafe": "<Subject 3>"}
    mode: str = ""                  # the layout really built: a ref2va segment without any reference media becomes "t2va"
    # shot index -> {"own": words that come from that shot's own storyboard fields (framing, action, performance,
    # camera, lines), "all": words of the whole shot block with the set-up, the looks and the end state the builder adds}
    own_words: dict = field(default_factory=dict)


# ---------------------------------------------------------------- shared shot body

def _shot_parts(seg: Segment, sh: Shot, is_first: bool, labels: dict[str, str], speak, closure, lead: str = "",
                speakers: dict[str, str] | None = None) -> tuple[str, list[str]]:
    """-> (framing sentence, the sentences that follow it). `speak(dialogue)` returns the sentence for one line,
    `closure(dialogue)` the sentence that closes the speaker's mouth afterwards."""
    framing = fill(sh.framing.strip().rstrip("."), labels)
    for d in sh.dialogue:                                   # official: "a close-up of <Subject 4> (S2), the young man ..."
        tag = labels.get(d.speaker, "")
        if speakers and not d.offscreen and tag.startswith("<") and tag in framing and f"{tag} (" not in framing:
            framing = framing.replace(tag, f"{tag} ({speakers[d.speaker]})", 1)
    lens = (sh.lens or "").strip().rstrip(".")
    shot_open = framing + (f", {lens}" if lens else "")
    if is_first and lead:                                   # three-part: the style opens [Shot 1]
        head = f"[Shot {sh.index}] {lead}{shot_open}."
    elif is_first:
        head = f"[Shot {sh.index}] The video opens on {shot_open}."
    else:
        head = f"[Shot {sh.index}] At {timecode(sh.start)}, the shot cuts to {shot_open}."
    body = [_sentence(sh.action, labels), _sentence(sh.sound_cue, labels), _sentence(sh.performance, labels),
            _sentence(sh.lighting, labels), _sentence(sh.camera, labels)]
    for j, d in enumerate(sh.dialogue):
        body.append(speak(d))
        nxt = sh.dialogue[j + 1] if j + 1 < len(sh.dialogue) else None
        if (d.after_line or "").strip():
            body.append(_sentence(d.after_line, labels))
        elif d.speaker != "narrator" and not d.offscreen and (nxt is None or nxt.speaker != d.speaker):
            body.append(closure(d))                        # official examples close the mouth after every line
    if sh.end_hold:
        if sh.on_screen_characters or _framing_class(sh.framing) not in ("insert", "extreme close-up"):
            body.append("In the final second every character settles and holds the pose, breathing, while the framing stays put.")
        else:
            body.append("In the final second the picture settles and holds while the framing stays put.")
    return head, [x for x in body if x]


def only_these_words(seg: Segment) -> str:
    """Closing sentence of a segment with lines. Measured by a community test (egguy886, see
    references/camera-and-performance.md sections 5 and 5c): "Speak only the quoted dialogue lines" cut improvised extra
    words from 9.3% of takes to 1.3%."""
    lines = [d for sh in seg.shots for d in sh.dialogue]
    if not lines:
        return ""
    first = "Speak only the quoted dialogue line." if len(lines) == 1 else "Speak only the quoted dialogue lines."
    if len({d.speaker for d in lines}) > 1:
        return first + " Those are the only words in the video."
    return first + " After that nobody says anything else."


def _closing(ep: Episode, seg: Segment, labels: dict[str, str]) -> str:
    """The room-wide end state is written out only when the last shot shows the room (medium or wider, or a framing
    the classifier does not know). Inside a close-up it would describe things the shot cannot show."""
    out = []
    last = seg.shots[-1]
    if seg.end_state.strip() and _framing_class(last.framing) in ROOM_SHOTS + ("other",):
        out.append(f"At the end of the video, {_state(seg.end_state, room_labels(ep, labels))}.")
    if seg.negatives.strip():
        out.append(_sentence(seg.negatives, labels))
    out.append(only_these_words(seg))
    return " ".join(x for x in out if x)


def _opening(ep: Episode, seg: Segment, labels: dict[str, str]) -> dict[str, str]:
    """{"blocking": positions written by code from `stagings`, "state": the inherited / observed state,
    "nospeech": the closed-mouths sentence of a segment without lines} - empty strings where there is nothing."""
    out = {"blocking": fill(blocking_sentence(ep, seg), labels), "state": "", "nospeech": ""}
    is_first = ep.segments[0] is seg
    text, source = effective_continuity(ep, seg, ALLOW_PLANNED)
    if source != "authored":
        out["state"] = fill(text, room_labels(ep, labels))
    elif text and not is_first:                           # the first segment inherits nothing: its note stays a note
        out["state"] = f"As the video opens, {_state(text, room_labels(ep, labels))}."
    if not any(sh.dialogue for sh in seg.shots):
        out["nospeech"] = NO_SPEECH
    return out


ORDER = ("anchor", "setting", "blocking", "state", "nospeech", "body", "closing")   # how a shot's parts follow its framing sentence


def _join_shot(head: str, parts: dict[str, str]) -> str:
    return " ".join(x for x in [head] + [parts.get(k, "") for k in ORDER] if x)


# ---------------------------------------------------------------- the look of a subject where it is first seen

_PARTIAL = (r"(?:over the (?:left |right )?shoulder of|from behind|behind|past|the back of|the (?:left |right )?shoulders? of|"
            r"the (?:left |right )?hands? of|the (?:left |right )?arms? of|the fingers of|the feet of|the silhouette of|"
            r"the shadow of|the reflection of)\s+")


def _label_re(label: str) -> re.Pattern:
    """The label plus a speaker id that may follow it. Plain-word labels also match at a sentence start."""
    if label.startswith("<"):
        return re.compile(re.escape(label) + r"(?: \(S\d+(?:,S\d+)*\))?")
    return re.compile(r"(?<![\w-])" + re.escape(label) + r"(?![\w-])(?: \(S\d+(?:,S\d+)*\))?", re.I)   # whole words only


def _splice(text: str, label: str, addition: str, sep: str = ", ") -> tuple[str, bool]:
    """Insert `addition` after the first mention of `label` that is not a possessive.
    "<Subject 2> holds her gaze"  ->  "<Subject 2>, the man in his fifties with ..., holds her gaze"."""
    for m in _label_re(label).finditer(text):
        rest = text[m.end():]
        if rest.startswith(("'s", "’s")):
            continue
        tail = "" if (not rest or rest[0] in ",.;:!?)") else ","
        return text[:m.end()] + sep + addition + tail + rest, True
    return text, False


_ABSENT = re.compile(r"\b(outside the frame|out of (?:the )?frame|off[- ]?screen|off frame|has left|have left|is gone|are gone|"
                     r"absent|no longer|not in the)\b", re.I)


def _present(text: str, pat: re.Pattern) -> bool:
    """True when `text` mentions the label in a clause that does not say it is away."""
    return any(pat.search(clause) and not _ABSENT.search(clause) for clause in re.split(r"[;.]", text or ""))


def _introduce(heads: list[str], parts: list[dict[str, str]], subjects: list[dict], classes: list[str]) -> None:
    """Official rule (ref guide 5.3): at the first clear appearance of a subject, describe its referenced
    characteristics; later shots keep the label. `subjects`: {"label", "look", "sep", "short", "person", "visible"}.
      * look    - spliced in once, after the first mention in the first shot that really shows the subject: it is
                  on screen, it is more than a shoulder or a pair of hands in the framing, and either the shot
                  shows the room (medium or wider), or its framing names the subject, or it names nobody.
                  Somebody else's close-up does not count.
      * short   - said at a first glimpse that comes before that shot, and as a reminder at each later cut whose
                  framing leads with this subject ("<Subject 2>, the man in his fifties from Shot 1")
      * visible - shot indexes where the person is on screen (None: not declared, any mention counts)
    `classes` is the shot size of each shot (storyboard._framing_class). Text is searched in reading order -
    framing, opening positions, inherited state, the shot's own sentences - and an end state is never touched."""
    first_label = re.compile(r"<Subject \d+>")
    people = [_label_re(x["label"]) for x in subjects if x.get("person")]

    def put(i: int, s: dict, addition: str, sep: str = ", ") -> bool:
        pat = _label_re(s["label"])
        for key in ("head", "blocking", "state", "body"):
            text = heads[i] if key == "head" else parts[i].get(key, "")
            if key == "state" and not _present(text, pat):
                continue
            new, ok = _splice(text, s["label"], addition, sep)
            if ok:
                if key == "head":
                    heads[i] = new
                else:
                    parts[i][key] = new
                return True
        return False

    for s in subjects:
        pat = _label_re(s["label"])
        mention = [i for i in range(len(heads))
                   if pat.search(heads[i]) or pat.search(parts[i].get("blocking", "")) or pat.search(parts[i].get("body", ""))
                   or _present(parts[i].get("state", ""), pat)]
        if not mention:
            continue
        partial = set()
        if s.get("person"):
            glimpse = re.compile(_PARTIAL + re.escape(s["label"]), re.I)
            partial = {i for i in mention if glimpse.search(heads[i])}
        clear = [i for i in mention
                 if (s.get("visible") is None or i in s["visible"]) and i not in partial
                 and (not s.get("person") or classes[i] in ROOM_SHOTS or pat.search(heads[i])
                      or not any(q.search(heads[i]) for q in people))]
        shown = None
        if clear and s.get("look") and put(clear[0], s, s["look"], s.get("sep", ", ")):
            shown = clear[0]
        short = s.get("short")
        if not short:
            continue
        if shown is None or mention[0] < shown:              # a first glimpse still says who it is
            put(mention[0], s, short)
        if shown is None:
            continue
        for i in mention:
            if i <= shown:
                continue
            lead = first_label.search(heads[i])
            if lead and lead.group(0) == s["label"]:
                heads[i], _ = _splice(heads[i], s["label"], f"{short} from Shot {shown + 1}")


# ---------------------------------------------------------------- six-part (Ref2VA)

def build_ref2va(ep: Episode, seg: Segment) -> BuiltPrompt:
    content: list[dict] = []
    labels: dict[str, str] = {}
    pic = aud = nsubj = 0           # <Subject N> counter (audio definitions must not consume numbers)
    defs: list[str] = []
    retention: list[str] = []
    subjects: list[dict] = []       # what _introduce() repeats inside the shots
    speakers = speaker_ids(seg)     # only characters who speak in THIS segment get a voice reference
    audio_content: list[dict] = []  # audio is wired after all images: characters, scene, props, then audio
    audio_defs: list[str] = []
    audio_ret: list[str] = []
    audio_of: dict[str, int] = {}
    all_shots = ", ".join(f"[Shot {sh.index}]" for sh in seg.shots)
    on_screen: dict[str, set[int]] = {}     # label -> shot indexes the storyboard declares the person visible in
    sc = ep.scene(seg.scene_id)
    scene_name = prompt_name(sc, "scene")

    # optional opening-frame anchor (a generated first frame, or the previous segment's tail frame) takes <Picture 1>
    if seg.first_frame:
        pic += 1
        content.append({**image_item(seg.first_frame, "reference_image"), "anchor": "first_frame"})   # comfy_submit.py --anchor can also pin it at frame 0
        defs.append(f"<Picture {pic}> is the first frame of [Shot 1], showing the opening composition, positions and lighting.")
        retention.append(f"<Picture {pic}> ([Shot 1] first frame): fully_preserved - the composition, character positions "
                         f"and lighting of the opening frame are retained and the action develops from it.")
    # optional keyframes of later shots (official ref guide 5.3 and ComfyUI's multiframe template): one picture per shot
    frame_pics: dict[int, int] = {1: 1} if seg.first_frame else {}     # shot index -> <Picture N> the shot starts on
    key_notes: dict[int, str] = {}
    for sh in seg.shots:
        if not sh.keyframe or sh.index == 1:
            continue
        if pic >= MAX_REF_IMAGES:
            import sys
            print(f"WARN {seg.id}: keyframe of shot {sh.index} dropped (9-slot limit): {sh.keyframe}", file=sys.stderr)
            continue
        pic += 1
        content.append({**image_item(sh.keyframe, "reference_image"), "anchor": {"shot": sh.index, "frame": int(round(sh.start * 24))}})
        frame_pics[sh.index] = pic
        key_notes[pic] = (sh.keyframe_note or "").strip().rstrip(".")
        retention.append(f"<Picture {pic}> ([Shot {sh.index}] keyframe): fully_preserved - the composition, character positions "
                         f"and lighting of this keyframe are established as the shot starts.")

    # characters first (identity), then scene, then props
    for cid in seg.character_ids:
        c = ep.char(cid)
        imgs = c.reference_images[:min(3, int((seg.character_refs or {}).get(cid, 3)))]      # per-segment budget
        if not imgs:
            continue
        pics = []
        for src in imgs:
            if pic >= MAX_REF_IMAGES:
                import sys
                print(f"WARN {seg.id}: reference image dropped (9-slot limit): {src}", file=sys.stderr)
                break
            pic += 1
            content.append(image_item(src, "reference_image"))
            pics.append(f"<Picture {pic}>")
        if not pics:
            continue
        nsubj += 1
        subj = f"<Subject {nsubj}>"
        labels[cid] = subj
        on_screen[subj] = {i for i, sh in enumerate(seg.shots) if cid in sh.on_screen_characters}
        head, tail = split_identity(c.identity_phrase)
        who = designation(c)
        tail = f", {tail}" if tail else ""
        if len(pics) == 1:                                   # official: "<Subject 1> is the young woman in <Picture 1>, with ..."
            defs.append(f"{subj} is the {head} in {pics[0]}{tail}.")
            kept = f"the facial identity, hairstyle, build and outfit of {who} are retained from {pics[0]}"
        else:                                                # official: "state what each asset provides"
            extra = f", with further detail in {pics[2]}" if len(pics) > 2 else ""
            defs.append(f"{subj} is the {head} whose face and hairstyle come from {pics[0]} and whose build and outfit "
                        f"come from {pics[1]}{extra}{tail}.")
            kept = (f"the facial identity and hairstyle of {who} are retained from {pics[0]} and the build, outfit and "
                    f"silhouette from {pics[1]}" + (f"; {pics[2]} adds detail" if len(pics) > 2 else ""))
        retention.append(f"{subj} (appears in @@SHOTS:{subj}@@): fully_preserved - {kept}; only the person is taken from "
                         f"{'this picture' if len(pics) == 1 else 'these pictures'}, the setting comes from @@SETTING@@.")
        declared = any(sh.on_screen_characters for sh in seg.shots)
        subjects.append({"label": subj, "look": full_look(c), "short": who, "person": True,
                         "visible": {i for i, sh in enumerate(seg.shots) if cid in sh.on_screen_characters} if declared else None})
        if c.voice_reference and cid in speakers and aud < MAX_REF_AUDIO:
            aud += 1
            audio_of[cid] = aud
            audio_content.append(audio_item(c.voice_reference, "reference_audio"))
            audio_defs.append(f"<Audio {aud}> is the voice-timbre reference for {subj} ({speakers[cid]}).")
            audio_ret.append(f"<Audio {aud}>: reference - its vocal timbre guides the dialogue delivery of {subj} without "
                             f"copying the original signal; the spoken words come from the quoted dialogue lines.")

    if sc.reference_images and seg.use_scene_reference and pic < MAX_REF_IMAGES:
        pic += 1
        content.append(image_item(sc.reference_images[0], "reference_image"))
        nsubj += 1
        subj = f"<Subject {nsubj}>"
        labels[sc.id] = subj
        defs.append(f"{subj} is the environment in <Picture {pic}>, {sc.description.strip().rstrip('.')}.")
        # partially_preserved on purpose: "fully" also keeps the picture's viewpoint, which freezes the camera
        retention.append(f"{subj} (appears in {all_shots}): partially_preserved - the layout, light direction and set "
                         f"dressing are retained while the camera position changes from shot to shot.")
        setting = f"The setting is {subj}, {scene_brief(sc.description)}."
        setting_ref = subj
    else:
        labels[sc.id] = scene_name                          # no picture: the words have to carry the place
        setting = f"The setting is {scene_name}, {sc.description.strip().rstrip('.')}."
        setting_ref = "the described setting"

    for pid in seg.prop_ids:
        p = ep.prop(pid)
        if p.reference_images and pic < MAX_REF_IMAGES:
            pic += 1
            content.append(image_item(p.reference_images[0], "reference_image"))
            nsubj += 1
            subj = f"<Subject {nsubj}>"
            labels[pid] = subj
            defs.append(f"{subj} is {definite(p.description)}, the exact item shown in <Picture {pic}>.")
            retention.append(f"{subj} (appears in @@SHOTS:{subj}@@): fully_preserved - the item's shape, color, "
                             f"markings and material are retained exactly; no other item is substituted.")
            subjects.append({"label": subj, "look": definite(p.description)})

    content.extend(audio_content)
    defs.extend(audio_defs)
    retention.extend(audio_ret)

    # an asset without a reference picture has no label: a person is called by a designation, an item by its name,
    # and the words that would have been the definition follow the first mention
    for cid in seg.character_ids:
        if cid not in labels:
            c = ep.char(cid)
            labels[cid] = designation(c)
            subjects.append({"label": labels[cid], "person": True, **unpictured_look(c)})
    for pid in seg.prop_ids:
        if pid not in labels:
            p = ep.prop(pid)
            labels[pid] = prompt_name(p, "prop")
            subjects.append({"label": labels[pid], "look": p.description.strip().rstrip(". ")})

    voiced: set[str] = set()

    def speak(d: Dialogue) -> str:
        line = f"<d>[{d.language}] {d.text}</d>"
        sid = speakers[d.speaker]
        if d.speaker == "narrator":
            return (f"The narrator ({sid}) says in an off-screen voiceover{delivery_phrase(d)}: {line} "
                    f"while the lips of everyone on screen remain completely closed.")
        c = ep.char(d.speaker)
        first = d.speaker not in voiced
        voiced.add(d.speaker)
        voice = ""
        tag = labels.get(d.speaker) or designation(c)         # heard but not bound to this segment: called in words
        if d.speaker in audio_of:                           # cited wherever the audio relationship is active (ref guide 5.3)
            described = f" {voice_tail(c)}," if voice_tail(c).startswith("with ") else ""
            voice = (f", using the voice timbre referenced from <Audio {audio_of[d.speaker]}>,{described}" if first else
                     f", in the same voice referenced from <Audio {audio_of[d.speaker]}>,")
        elif first and voice_tail(c):                       # no reference: the voice is described where it is first heard
            voice = f", {voice_tail(c)},"
        who = f"{tag[0].upper() + tag[1:]} ({sid}){voice}"
        if d.offscreen:
            return (f"{who} says in an off-screen voiceover{delivery_phrase(d)}: {line} "
                    f"while the lips of everyone on screen remain completely closed.")
        return f"{who} says{delivery_phrase(d)}, {line}"

    def closure(d: Dialogue) -> str:
        return f"{labels[d.speaker][0].upper() + labels[d.speaker][1:]} closes {possessive(ep.char(d.speaker))} lips."

    lead_line = style_sentence(seg.style)                   # official: only the style comes before [Shot 1]
    heads, parts, own = [], [], {}
    for i, sh in enumerate(seg.shots):
        h, b = _shot_parts(seg, sh, i == 0, labels, speak, closure, speakers=speakers)
        heads.append(h)
        parts.append({"body": " ".join(b)})
        own[sh.index] = len(f"{h} {parts[-1]['body']}".split()) - 2  # before the set-up, the looks and the end state are added
        if sh.index in frame_pics:                          # official wording for frame anchors inside a shot (ref guide 5.3)
            parts[-1]["anchor"] = (f"The shot begins from <Picture {frame_pics[sh.index]}>." if sh.index == 1
                                   else f"The shot's keyframe corresponds to <Picture {frame_pics[sh.index]}>.")
    key_defs = [f"<Picture {n}> is the keyframe of [Shot {idx}], showing "
                + (fill(key_notes[n], labels) if key_notes.get(n) else "the composition the shot starts on") + "."
                for idx, n in sorted(frame_pics.items()) if idx > 1]
    defs[1 if seg.first_frame else 0:1 if seg.first_frame else 0] = key_defs      # right after the first-frame line
    parts[0].update(setting=setting, **_opening(ep, seg, labels))            # the set-up sits inside [Shot 1]
    parts[-1]["closing"] = _closing(ep, seg, labels)
    _introduce(heads, parts, subjects, [_framing_class(sh.framing) for sh in seg.shots])
    shot_lines = [_join_shot(h, p) for h, p in zip(heads, parts)]
    words = {sh.index: {"own": own[sh.index], "all": len(line.split()) - 2} for sh, line in zip(seg.shots, shot_lines)}

    # "appears in" lists the shots that name the subject or declare it on screen - read off the finished text
    def appears(label: str) -> str:
        pat = _label_re(label)
        hit = [i for i, line in enumerate(shot_lines) if pat.search(line) or i in on_screen.get(label, ())]
        return ", ".join(f"[Shot {seg.shots[i].index}]" for i in hit) or all_shots
    retention = [re.sub(r"@@SHOTS:(<Subject \d+>)@@", lambda m: appears(m.group(1)), r).replace("@@SETTING@@", setting_ref)
                 for r in retention]

    types = (["keyframe completion"] if frame_pics else []) + ["reference generation"] + (["audio reference"] if aud else [])
    people = [labels[c] for c in seg.character_ids]
    n = len(seg.shots)
    if seg.summary.strip():
        gist = _sentence(seg.summary, room_labels(ep, labels))
    else:
        gist = (f"The target video shows {_join(people)} in {labels[sc.id]}" if people else f"The target video shows {labels[sc.id]}") \
            + f" across {n} shot{'s' if n > 1 else ''}."
    if seg.first_frame:
        gist += " It opens on <Picture 1>."
    if audio_of:                                            # official: "The three-shot exchange uses <Audio 1> as the ..."
        uses = _join([f"<Audio {j}> as the voice-timbre reference for {labels[cid]}" for cid, j in audio_of.items()])
        count = f"{NUMBER[n]}-shot " if 1 < n < len(NUMBER) else ""
        gist += f" The {count}video uses {uses}."
    summary = f"[{' + '.join(types)}] {gist}"

    text = (
        "subject_definitions:\n" + "\n".join(defs) + "\n\n"
        "summary:\n" + summary + "\n\n"
        "retention_analysis:\n" + "\n".join(retention) + "\n\n"
        "detailed_description:\n" + lead_line + "\n" + "\n".join(shot_lines) + "\n\n"
        "overall_soundscape:\n" + fill(seg.soundscape.strip(), labels) + "\n\n"
        "non_diegetic_music:\n" + (seg.music.strip() or "N/A")
    )
    content.insert(0, text_item(text))
    return BuiltPrompt(text=text, content=content, labels=labels, mode="ref2va", own_words=words)


# ---------------------------------------------------------------- three-part (T2VA / I2VA / FL2VA)

def build_three_part(ep: Episode, seg: Segment) -> BuiltPrompt:
    content: list[dict] = []
    header = ""
    effective = frames_for_seconds(seg.duration) / 24.0        # the clip really lasts this long (17k+5 frame grid)
    if seg.mode == "i2va":
        content.append(image_item(seg.first_frame, "first_frame"))
        header = ("For the target video, at 0.00 seconds into the target video, "
                  "<Picture 1> (from [Shot 1]) is fully referenced.\n\n")
    elif seg.mode == "fl2va":
        content.append(image_item(seg.first_frame, "first_frame"))
        content.append(image_item(seg.last_frame, "last_frame"))
        last_shot = seg.shots[-1].index
        header = ("How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the "
                  f"0.00-second mark of the target video; Picture 2 (from Shot {last_shot}) aligns with the "
                  f"{effective:.2f}-second mark of the target video.\n\n")

    # no <Subject N> labels in this layout and no names either (official examples: "the young woman", "the baker")
    sc = ep.scene(seg.scene_id)
    labels = {cid: designation(ep.char(cid)) for cid in seg.character_ids}
    labels.update({pid: prompt_name(ep.prop(pid), "prop") for pid in seg.prop_ids})
    labels[sc.id] = prompt_name(sc, "scene")
    speakers = speaker_ids(seg)
    voiced: set[str] = set()

    def speak(d: Dialogue) -> str:
        line = f"<d>[{d.language}] {d.text}</d>"
        sid = speakers[d.speaker]
        if d.speaker == "narrator":
            return (f"The narrator ({sid}) says in an off-screen voiceover{delivery_phrase(d)}: {line} "
                    f"while the lips of everyone on screen remain completely closed.")
        c = ep.char(d.speaker)
        tag = labels.get(d.speaker) or designation(c)         # heard but not bound to this segment
        who = tag[0].upper() + tag[1:]
        if d.speaker not in voiced and voice_tail(c):          # official: identify the voice where it is first heard
            who += f" {voice_tail(c)}" if voice_tail(c).startswith("with ") else f", {voice_tail(c)},"
        voiced.add(d.speaker)
        if d.offscreen:
            return (f"{who} ({sid}) says in an off-screen voiceover{delivery_phrase(d)}: {line} "
                    f"while the lips of everyone on screen remain completely closed.")
        return f"{who} ({sid}) says{delivery_phrase(d)}: {line}"

    def closure(d: Dialogue) -> str:
        return f"{labels[d.speaker][0].upper() + labels[d.speaker][1:]} closes {possessive(ep.char(d.speaker))} lips."

    # with a first frame the picture carries the look; without one the words after the first mention do
    subjects: list[dict] = []
    setting = f"The setting is {sc.description.strip().rstrip('.')}."
    if seg.mode == "i2va":
        setting += (" The opening frame shown in <Picture 1> is preserved: appearance, clothing, position and set "
                    "layout stay as established.")
    elif seg.mode == "fl2va":
        setting += " The shot begins in the position and framing established by Picture 1."
    if seg.mode in ("i2va", "fl2va"):
        subjects += [{"label": labels[cid], "person": True} for cid in seg.character_ids]
    else:
        for cid in seg.character_ids:
            subjects.append({"label": labels[cid], "person": True, **unpictured_look(ep.char(cid))})
    for pid in seg.prop_ids:
        subjects.append({"label": labels[pid], "look": ep.prop(pid).description.strip().rstrip(". ")})
    style = style_list(seg.style)
    heads, parts, own = [], [], {}
    for i, sh in enumerate(seg.shots):
        h, b = _shot_parts(seg, sh, i == 0, labels, speak, closure, lead=f"{style}, " if i == 0 else "", speakers=speakers)
        heads.append(h)
        parts.append({"body": " ".join(b)})
        own[sh.index] = len(f"{h} {parts[-1]['body']}".split()) - 2 - (len(style.split()) if i == 0 else 0)   # the style is the segment's
    parts[0].update(setting=setting, **_opening(ep, seg, labels))            # the set-up sits inside [Shot 1], after the framing
    if seg.mode == "fl2va":
        parts[-1]["closing"] = " ".join(x for x in (
            "The shot settles into the pose, spacing and composition established by Picture 2 at the end.",
            _sentence(seg.negatives, labels), only_these_words(seg)) if x)
    else:
        parts[-1]["closing"] = _closing(ep, seg, labels)
    _introduce(heads, parts, subjects, [_framing_class(sh.framing) for sh in seg.shots])
    shot_lines = [_join_shot(h, p) for h, p in zip(heads, parts)]
    words = {sh.index: {"own": own[sh.index], "all": len(line.split()) - 2} for sh, line in zip(seg.shots, shot_lines)}
    body = " ".join(shot_lines)

    text = (
        header +
        "integrated_multimodal_description: " + body + "\n\n"
        "overall_soundscape: " + fill(seg.soundscape.strip(), labels) + "\n\n"
        "non_diegetic_music: " + (seg.music.strip() or "N/A")
    )
    content.insert(0, text_item(text))
    return BuiltPrompt(text=text, content=content, labels=labels, mode=seg.mode if seg.mode in ("i2va", "fl2va", "t2va") else "t2va",
                       own_words=words)


def build(ep: Episode, seg: Segment) -> BuiltPrompt:
    try:
        if seg.mode == "ref2va" and reference_count(ep, seg) != (0, 0):
            return build_ref2va(ep, seg)
        return build_three_part(ep, seg)          # also a ref2va segment with nothing to reference: plain text-to-video
    except KeyError as e:
        raise ValueError(f"segment {seg.id}: placeholder {{{e.args[0]}}} is not an asset bound to this segment "
                         f"(bound: {', '.join(seg.character_ids + [seg.scene_id] + seg.prop_ids)})") from None


# ---------------------------------------------------------------- planned subtitle cues

def dialogue_cues(ep: Episode, seg: Segment, offset: float) -> list[tuple[float, float, str, str]]:
    """Rough PLANNED cues: each shot's lines are spread evenly across that shot's span.
    The real subtitles come from retime_subtitles.py after assembly."""
    cues = []
    bounds = [sh.start for sh in seg.shots] + [frames_for_seconds(seg.duration) / 24.0]
    for i, sh in enumerate(seg.shots):
        lines = sh.dialogue
        if not lines:
            continue
        span = (bounds[i + 1] - bounds[i]) / len(lines)
        for j, d in enumerate(lines):
            start = offset + bounds[i] + j * span + 0.3
            end = offset + bounds[i] + (j + 1) * span - 0.1
            name = "旁白" if d.speaker == "narrator" else ep.char(d.speaker).name
            cues.append((start, max(end, start + 0.5), name, d.text))
    return cues
