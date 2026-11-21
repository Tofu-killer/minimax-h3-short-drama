"""Storyboard data model + validation.

One Segment == one H3 generation (4–15 s) == one API call.
Field design merges huobao-drama's storyboard-breaker skill, Hailuo-AI-Short-Drama-Studio's
director agent, and MiniMax's official six-column shot table
(Shot ID & Duration | Continuity Handoff | Reference Anchors | Hook Type | Per-Second Directives | Audio & Dialogue Track).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path
from typing import Optional

CHARS_PER_SECOND = 4.5      # huobao rule: dialogue chars / 4.5 + 2 s acting margin
ACTING_MARGIN = 2.0


@dataclass
class Character:
    id: str
    name: str
    identity_phrase: str            # what tells this person apart at a glance, as "a <who> with <features>": hair, main
                                    # garment and colour, one marker (about 12-25 words). Goes into every prompt.
    voice_phrase: str = ""          # e.g. "a woman in her late twenties with a low, slightly husky voice"
    reference_images: list[str] = field(default_factory=list)   # face / outfit / full-body
    voice_reference: Optional[str] = None                        # 2–15 s clean speech
    name_en: str = ""               # English name for people reading the files (prompts never use a person's name)
    sheet_phrase: str = ""          # the long look used only to GENERATE the reference pictures (face structure, build,
                                    # height ...). Never written into a video prompt.
    pronoun: str = ""               # "he" | "she" | "they": for the builder's own sentences ("closes his lips"); default: read
                                    # from the head of identity_phrase (man / woman ...), else "they"
    short_phrase: str = ""          # how prompts call this person after the first mention, e.g. "the grey-haired doctor in the
                                    # white coat"; default: "the" + the head of identity_phrase ("the man in his fifties")


@dataclass
class Scene:
    id: str
    name: str
    description: str                # written once, pasted unchanged
    reference_images: list[str] = field(default_factory=list)
    name_en: str = ""               # English label used inside prompts; default: `name` if ASCII, else derived from the id


@dataclass
class Prop:
    id: str
    name: str
    description: str
    reference_images: list[str] = field(default_factory=list)
    rarity: Optional[str] = None     # 三角洲 loot tier: red/gold/purple/blue/green/white; overlaid in post, not rendered
    name_en: str = ""               # English label used inside prompts; default: `name` if ASCII, else derived from the id


@dataclass
class Dialogue:
    speaker: str                    # character id, or "narrator"
    language: str                   # "Chinese" / "English" ...
    text: str
    delivery: str = ""              # "softly", "calm and quiet", ...
    offscreen: bool = False         # voice-over -> lips closed
    en: str = ""                    # optional English subtitle for this line (--bilingual); never spoken, never in the prompt
    after_line: str = ""            # optional sentence: what the speaker does right after the words end
                                    # ("He closes his lips and looks down at {prop_folder}."); default: closes the lips


@dataclass
class Shot:
    index: int
    start: float                    # seconds; shot 1 must be 0 (no timecode is written for it)
    framing: str                    # "medium shot", "over-the-shoulder close-up" ...
    camera: str                     # one dominant move, official vocabulary
    action: str                     # starting state -> movement -> ending state
    dialogue: list[Dialogue] = field(default_factory=list)
    on_screen_characters: list[str] = field(default_factory=list)
    lens: str = ""                  # optional: "35mm, shallow depth of field" / "wide 24mm, deep focus"
    lighting: str = ""              # optional: key/fill direction, practicals, colour temperature for THIS shot
    performance: str = ""           # optional: trigger -> reception -> one response -> settled state (observable cues)
    sound_cue: str = ""             # optional: one diegetic sound tied to an action in this shot
    end_hold: bool = False          # optional: last shot settles 0.5 s then holds 1 s (trimmed at assembly)


@dataclass
class Segment:
    id: str
    duration: int                   # 4..15
    scene_id: str
    character_ids: list[str]
    shots: list[Shot]
    soundscape: str                 # 1–4 concrete sentences
    music: str = "N/A"              # "N/A" when scoring in post
    prop_ids: list[str] = field(default_factory=list)
    mode: str = "ref2va"            # ref2va | i2va | fl2va | t2va
    first_frame: Optional[str] = None
    last_frame: Optional[str] = None
    style: str = "Live-action, cinematic"
    continuity: str = ""            # inherited state from previous segment
    end_state: str = ""             # named end state for the next segment
    hook_type: str = ""             # hook / setup / turn / cliffhanger (planning label, never written into the prompt)
    summary: str = ""               # optional: one English sentence saying what happens, {asset_id} placeholders allowed
    use_scene_reference: bool = True   # False: do not attach the scene picture (it halves camera movement); the description carries the place
    character_refs: dict = field(default_factory=dict)   # {character_id: how many of its reference pictures to attach HERE};
                                    # default all (at most 3). 1 = the face only, 0 = none (the person is written in words)
    negatives: str = ""             # one positive lock ("The corridor behind them stays empty."), never a bare "no X"
    # -- written back after generation (observe_take.py); optional ------------------------------------
    status: str = "planned"         # planned | generated | accepted | accepted_with_deviation | rejected
    observed_end_state: str = ""    # where the ACCEPTED take really ends, read from its frames - never copied from the plan
    observation_confidence: str = ""   # low | medium | high
    accepted_take: Optional[dict] = None   # {"path", "sha256"}
    accepted_deviations: list[str] = field(default_factory=list)   # what differs from the plan and was accepted anyway


@dataclass
class Episode:
    title: str
    ratio: str                      # "9:16"
    style: str
    characters: list[Character]
    scenes: list[Scene]
    segments: list[Segment]
    props: list[Prop] = field(default_factory=list)
    synopsis: str = ""
    stagings: list[dict] = field(default_factory=list)   # opening positions per scene visit, see blocking_sentence()

    # -- helpers ------------------------------------------------------------
    def char(self, cid: str) -> Character:
        return next(c for c in self.characters if c.id == cid)

    def scene(self, sid: str) -> Scene:
        return next(s for s in self.scenes if s.id == sid)

    def prop(self, pid: str) -> Prop:
        return next(p for p in self.props if p.id == pid)

    def total_duration(self) -> int:
        return sum(s.duration for s in self.segments)


# ---------------------------------------------------------------- (de)serialisation

def _from_dict(cls, d):
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in names})


def _resolve(base: Path, src: Optional[str]) -> Optional[str]:
    """Local asset paths are relative to the episode JSON's folder. A path that only exists relative to the
    folder the script is run from (the project root, e.g. "bible/chars/a.png" with the JSON in episodes/) is
    accepted as well. URLs / mm_file:// / data: pass through."""
    if not src or src.startswith(("http://", "https://", "mm_file://", "data:")) or Path(src).is_absolute():
        return src
    if not (base / src).exists() and Path(src).exists():
        return str(Path(src).resolve())
    return str((base / src).resolve())


def load_episode(path: str | Path) -> Episode:
    path = Path(path)
    base = path.parent
    raw = json.loads(path.read_text(encoding="utf-8"))
    characters = [_from_dict(Character, c) for c in raw["characters"]]
    scenes = [_from_dict(Scene, s) for s in raw["scenes"]]
    props = [_from_dict(Prop, p) for p in raw.get("props", [])]
    for obj in (*characters, *scenes, *props):
        obj.reference_images = [_resolve(base, i) for i in obj.reference_images]
    for c in characters:
        c.voice_reference = _resolve(base, c.voice_reference)
    segments = []
    for s in raw["segments"]:
        s = {**s, "first_frame": _resolve(base, s.get("first_frame")), "last_frame": _resolve(base, s.get("last_frame"))}
        s.pop("first_frame_prompt", None)   # LLM-stage field, not needed at generation time
        s.setdefault("style", raw.get("style", "Live-action, cinematic"))   # episode style is the default for every segment
        shots = []
        for sh in s["shots"]:
            dl = [_from_dict(Dialogue, d) for d in sh.get("dialogue", [])]
            shots.append(_from_dict(Shot, {**sh, "dialogue": dl}))
        segments.append(_from_dict(Segment, {**s, "shots": shots}))
    return Episode(title=raw["title"], ratio=raw["ratio"], style=raw.get("style", "Live-action, cinematic"),
                   characters=characters, scenes=scenes, props=props, segments=segments,
                   synopsis=raw.get("synopsis", ""), stagings=raw.get("stagings", []) or [])


def dump_episode(ep: Episode) -> str:
    return json.dumps(asdict(ep), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- hand-off between segments

OBSERVED = "@observed"
PLACEHOLDER_RE = re.compile(r"\{([A-Za-z0-9_\u4e00-\u9fff-]+)\}")


class NotObservedYet(ValueError):
    """The segment opens from the observed end of the previous one, and that take has not been accepted and
    observed yet. A normal state of the project, not a mistake in the storyboard."""


def effective_continuity(ep: "Episode", seg: "Segment", allow_planned: bool = False) -> tuple[str, str]:
    """The text that opens a segment, and where it came from.

    A `continuity` that starts with "@observed" means: open from where the previous segment's ACCEPTED take
    really ended (its observed_end_state), not from where the plan said it would end. Anything after
    "@observed" is appended (wardrobe / light notes). Returns (text, "authored" | "observed:<id>" | "planned:<id>").
    Raises ValueError when the previous take has not been observed yet (unless allow_planned, for drafts).
    """
    raw = (seg.continuity or "").strip()
    if not raw.startswith(OBSERVED):
        return raw, "authored"
    extra = raw[len(OBSERVED):].strip()
    i = next(k for k, x in enumerate(ep.segments) if x is seg)
    if i == 0:
        raise ValueError(f"segment {seg.id}: '{OBSERVED}' needs a previous segment")
    prev = ep.segments[i - 1]
    if prev.observed_end_state.strip() and prev.status.startswith("accepted"):
        base, src = prev.observed_end_state.strip(), f"observed:{prev.id}"
    elif allow_planned and prev.end_state.strip():
        base, src = prev.end_state.strip(), f"planned:{prev.id}"
    else:
        raise NotObservedYet(f"segment {seg.id} opens from the observed end of {prev.id}, which has no accepted take with an "
                             f"observed_end_state yet - accept a take of {prev.id} and run observe_take.py "
                             f"(or build with --allow-planned for drafts)")
    text = f"As the video opens, {base.rstrip('. ')}."
    if extra:
        extra = extra[0].upper() + extra[1:]
        extra = extra if extra[-1] in ".!?" else extra + "."
    return (text + " " + extra).strip(), src


SIDES = {"left": "on the left side of the frame", "centre": "at the centre of the frame", "center": "at the centre of the frame",
         "right": "on the right side of the frame"}
NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six"]


def staging_for(ep: "Episode", seg: "Segment") -> Optional[dict]:
    return next((st for st in ep.stagings if st.get("segment") == seg.id), None)


def blocking_sentence(ep: "Episode", seg: "Segment") -> str:
    """One passage, generated from data, that pins who is where when a scene opens. Written by code so that the
    same positions are stated the same way every time:
        "At the start {a} sits at the left end of the sofa on the left side of the frame, facing frame right;
         {b} stands by the door on the right side of the frame, facing {a}. Exactly two people are in the scene
         at the start; {c} enters later; the other seats stay empty."
    `places` lists only who is present when the scene opens; `enters_later` names who walks in during the
    segment. Returns "" when the segment has no staging entry."""
    st = staging_for(ep, seg)
    if not st:
        return ""
    places = st.get("places") or []
    later = st.get("enters_later") or []
    if not places and not later:
        return ""
    parts = []
    for pl in places:
        bits = [f"{{{pl['character']}}} {pl.get('posture', 'stands')} {pl['at'].strip()}"]
        if pl.get("side"):
            bits.append(SIDES.get(pl["side"].lower(), pl["side"]))
        text = " ".join(bits)
        if pl.get("facing"):
            text += f", facing {pl['facing'].strip()}"
        parts.append(text)
    n = len(places)
    count = NUMBER_WORDS[n] if n < len(NUMBER_WORDS) else str(n)
    if n:
        out = "At the start " + "; ".join(parts) + "." + \
              f" Exactly {count} {'person is' if n == 1 else 'people are'} in the scene" + (" at the start" if later else "")
    else:
        out = "At the start nobody is in the scene"
    if later:
        names = [f"{{{c}}}" for c in later]
        who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
        out += f"; {who} {'enters' if len(names) == 1 else 'enter'} later"
    out += f"; {st['others'].strip().rstrip('.')}." if st.get("others") else "."
    return out


def staging_problems(ep: "Episode") -> list[str]:
    out = []
    seg_by_id = {s.id: s for s in ep.segments}
    for k, st in enumerate(ep.stagings):
        tag = f"staging {k + 1} ({st.get('scene_id')}/{st.get('segment')})"
        seg = seg_by_id.get(st.get("segment"))
        if seg is None:
            out.append(f"{tag}: unknown segment {st.get('segment')!r}")
            continue
        if st.get("scene_id") != seg.scene_id:
            out.append(f"{tag}: segment {seg.id} plays in {seg.scene_id}, not {st.get('scene_id')}")
        places = st.get("places") or []
        later = st.get("enters_later") or []
        if not places and not later:
            out.append(f"{tag}: neither places nor enters_later")
        placed = {pl.get("character") for pl in places}
        for c in later:
            if c not in seg.character_ids:
                out.append(f"{tag}: enters_later names {c}, who is not in segment {seg.id}'s character_ids")
            if c in placed:
                out.append(f"{tag}: {c} is both placed at the start and listed in enters_later")
        seen = set()
        for pl in places:
            cid = pl.get("character")
            if cid not in seg.character_ids:
                out.append(f"{tag}: {cid} is placed but is not in segment {seg.id}'s character_ids")
            at = (pl.get("at") or "").strip()
            if not at:
                out.append(f"{tag}: {cid} has no 'at' (what they stand / sit next to)")
            if pl.get("side") and pl["side"].lower() not in SIDES:
                out.append(f"{tag}: side {pl['side']!r} for {cid} - use left / centre / right")
            key = (at.lower(), (pl.get("side") or "").lower())
            if key in seen:
                out.append(f"{tag}: two characters share {pl.get('at')!r} on the {pl.get('side')} - give each their own spot")
            seen.add(key)
            refs = set(PLACEHOLDER_RE.findall(at + " " + (pl.get("facing") or "")))
            for r in refs:
                if r not in placed and r not in seg.prop_ids and r != seg.scene_id:
                    out.append(f"{tag}: {cid}'s position refers to {{{r}}}, who has no place at the start")
            if not refs & placed:                           # "two steps behind {a}" is anchored to a person, not to the set
                try:
                    desc = ep.scene(seg.scene_id).description.lower()
                    words = [w for w in re.findall(r"[a-z]{4,}", at.lower()) if w not in
                             ("the", "left", "right", "side", "near", "next", "from", "with", "behind", "front", "centre",
                              "center", "edge", "end", "middle", "steps", "step", "past")]
                    if words and not any(w in desc for w in words):
                        out.append(f"{tag}: WARN {pl.get('at')!r} is not mentioned in the scene description - anchor positions "
                                   f"to things the scene master actually shows")
                except StopIteration:
                    pass
        missing = [c for c in seg.character_ids if c not in placed and c not in later]
        if missing:
            out.append(f"{tag}: WARN {', '.join(missing)} {'is' if len(missing) == 1 else 'are'} in segment {seg.id} but "
                       f"{'has' if len(missing) == 1 else 'have'} neither an opening position nor an enters_later entry")
    # a scene with two or more people that opens without positions is where left / right mix-ups start
    current = None
    for seg in ep.segments:
        first_visit = seg.scene_id != current
        current = seg.scene_id
        if first_visit and len(seg.character_ids) >= 2 and not staging_for(ep, seg):
            out.append(f"segment {seg.id}: WARN opens scene {seg.scene_id} with {len(seg.character_ids)} people but has no "
                       f"`stagings` entry - add one so the opening positions are stated the same way every time")
    return out


PUNCT_RE = re.compile(r"[\s，。！？、；：“”‘’…—·,.!?;:\"'()（）《》〈〉<>\[\]【】~～\-]+")


def spoken_chars(text: str) -> int:
    """Characters that are actually spoken (punctuation and spaces do not take time)."""
    return len(PUNCT_RE.sub("", text or ""))


def placeholder_problems(ep: "Episode") -> list[str]:
    """Every {asset_id} in a shot, a summary, a soundscape or a staging must be an asset bound to that segment -
    it is replaced by that asset's label. A STATE (continuity, end_state, observed_end_state) describes the whole
    room, so it may name any asset of the episode: one that is not bound to the segment is written in words
    ("the ticket clerk") instead of a label."""
    out = []
    everything = {c.id for c in ep.characters} | {p.id for p in ep.props} | {s.id for s in ep.scenes}
    for seg in ep.segments:
        bound = set(seg.character_ids) | set(seg.prop_ids) | {seg.scene_id}
        texts = [("negatives", seg.negatives), ("soundscape", seg.soundscape)]
        for sh in seg.shots:
            for name in ("framing", "camera", "action", "lighting", "performance", "sound_cue"):
                texts.append((f"shot {sh.index} {name}", getattr(sh, name, "")))
            for d in sh.dialogue:
                texts.append((f"shot {sh.index} after_line", d.after_line))
        st = staging_for(ep, seg)
        if st:
            for pl in st.get("places") or []:
                texts.append(("staging", f"{pl.get('at', '')} {pl.get('facing', '')}"))
        for where, text in texts:
            for key in PLACEHOLDER_RE.findall(text or ""):
                if key not in bound:
                    out.append(f"segment {seg.id} {where}: {{{key}}} is not an asset bound to this segment "
                               f"(bound: {', '.join(sorted(bound))})")
        for where, text in (("continuity", seg.continuity), ("end_state", seg.end_state), ("observed_end_state", seg.observed_end_state),
                            ("summary", seg.summary)):          # a summary may name someone who is only heard
            for key in PLACEHOLDER_RE.findall(text or ""):
                if key not in everything:
                    out.append(f"segment {seg.id} {where}: {{{key}}} is not an asset of this episode")
    return out


def shot_spans(seg: "Segment") -> list[tuple["Shot", float, float]]:
    """[(shot, start, end)] with ends taken from the next shot's start / the segment duration."""
    out = []
    for i, sh in enumerate(seg.shots):
        end = seg.shots[i + 1].start if i + 1 < len(seg.shots) else float(seg.duration)
        out.append((sh, float(sh.start), float(end)))
    return out


def _framing_class(framing: str) -> str:
    """Shot size from the first matching phrase; hyphens and spaces are interchangeable ("medium-wide" = "medium wide")."""
    f = framing.lower().replace("-", " ")
    for key, cls in (("extreme close", "extreme close-up"), ("medium close", "medium close-up"), ("insert", "insert"),
                     ("close up", "close-up"), ("closeup", "close-up"),
                     ("medium wide", "medium wide"), ("medium long", "medium wide"), ("cowboy", "medium wide"),
                     ("medium", "medium"), ("mid shot", "medium"), ("two shot", "medium"),
                     ("full shot", "wide"), ("wide", "wide"), ("long shot", "wide"), ("establishing", "wide"), ("aerial", "wide")):
        if key in f:
            return cls
    return "other"


def rhythm_warnings(ep: "Episode") -> list[str]:
    """Pure arithmetic on the storyboard - no model involved. Every item is advice, not an error."""
    out: list[str] = []
    all_shots, events_by_t = [], []
    offset = 0.0
    for seg in ep.segments:
        spans = shot_spans(seg)
        durs = [e - s for _sh, s, e in spans]
        n_lines = sum(len(sh.dialogue) for sh in seg.shots)
        events = len(seg.shots) + n_lines
        load = seg.duration / events if events else seg.duration
        if load < 2.0:
            out.append(f"segment {seg.id}: {events} shots + lines in {seg.duration}s ({load:.1f}s each) - overloaded; "
                       f"split the segment or drop a beat")
        if len(durs) >= 3 and max(durs) - min(durs) <= 0.5:
            out.append(f"segment {seg.id}: all {len(durs)} shots last about {sum(durs) / len(durs):.1f}s - even pacing reads "
                       f"as mechanical; give the key shot more time and shorten a reaction")
        for sh, s0, e0 in spans:
            chars = sum(spoken_chars(d.text) for d in sh.dialogue)
            if chars and chars > 3 * (e0 - s0) + 1:
                out.append(f"segment {seg.id} shot {sh.index}: {chars} characters in a {e0 - s0:.1f}s shot "
                           f"(about {3 * (e0 - s0):.0f} fit) - the line will be rushed or cut off")
            all_shots.append((seg.id, sh.index, _framing_class(sh.framing), seg.scene_id))
            events_by_t.append(offset + s0)
            events_by_t += [offset + s0] * len(sh.dialogue)
        offset += seg.duration
    run = 1
    for (a, b) in zip(all_shots, all_shots[1:]):
        run = run + 1 if (a[2] == b[2] and a[2] != "other" and a[3] == b[3]) else 1       # a new scene starts a new run
        if run == 3:
            out.append(f"segment {b[0]} shot {b[1]}: third {b[2]} shot in a row - change the shot size")
    total = offset
    if total >= 24 and events_by_t:
        first = sum(1 for t in events_by_t if t < total / 3) / (total / 3)
        rest = sum(1 for t in events_by_t if t >= total / 3) / (total * 2 / 3)
        if rest > 0 and first < 0.8 * rest:
            out.append(f"the first third has {first * 10:.1f} shots + lines per 10s, the rest {rest * 10:.1f} - the opening is "
                       f"slower than what follows; tighten the first {total / 3:.0f}s")
    segd = [seg.duration for seg in ep.segments]
    if len(segd) >= 4 and len(set(segd)) == 1:
        out.append(f"all {len(segd)} segments are {segd[0]}s long - vary segment length with the content")
    return out


def frames_for_seconds(seconds: float) -> int:
    """Frame count on the model's 17k+5 grid at 24 fps (rounded up)."""
    n = int(round(seconds * 24))
    k = max(0, -(-(n - 5) // 17))
    return 17 * k + 5


# ---------------------------------------------------------------- hand-off states and spoken shots

_FRAME_WORDS = re.compile(r"\b(?:at |on |in )?(?:the )?frame[- ](?:left|right|centre|center)\b|\b(?:left|right|centre|center|middle) "
                          r"(?:side |edge |half |third )?of (?:the )?frame\b|\bat frame\b|\bin the (?:foreground|background)\b", re.I)
_SPEECH_VERBS = re.compile(r"\b(speaks?|says?|talks?|tells?|asks?|replies|reply|answers?|whispers?|shouts?|murmurs?)\b", re.I)


def state_problems(ep: "Episode") -> list[str]:
    """A state is handed to the NEXT segment, whose first shot has a different camera: "at frame left" would be
    read as a framing instruction there. Say where people are in the room instead."""
    out = []
    for seg in ep.segments:
        for where, text in (("continuity", seg.continuity), ("end_state", seg.end_state), ("observed_end_state", seg.observed_end_state)):
            m = _FRAME_WORDS.search(text or "")
            if m:
                out.append(f"segment {seg.id} {where}: WARN \"{m.group(0)}\" is a place in one camera's picture. A state is handed "
                           f"to the next segment, which opens on another camera: say where each person is in the room (next to "
                           f"what, to whose left or right, facing whom) and what they hold")
    return out


def speech_problems(ep: "Episode") -> list[str]:
    out = []
    for seg in ep.segments:
        for sh, s0, e0 in shot_spans(seg):
            if not sh.dialogue:
                continue
            if e0 - s0 < 3.0:
                out.append(f"segment {seg.id} shot {sh.index}: WARN a shot with a line lasts {e0 - s0:.1f}s - give a spoken shot at "
                           f"least 3 s")
            for name in ("action", "performance"):
                m = _SPEECH_VERBS.search(getattr(sh, name, "") or "")
                if m:
                    out.append(f"segment {seg.id} shot {sh.index} {name}: WARN \"{m.group(0)}\" - the line is written by the dialogue "
                               f"field; a second mention of speaking invites extra speech. Describe what the body does instead")
    return out


def reference_count(ep: "Episode", seg: "Segment") -> tuple[int, int]:
    """(pictures, audio clips) the builder will attach to this segment in ref2va mode."""
    if seg.mode != "ref2va":
        return (1 if seg.first_frame else 0) + (1 if seg.last_frame else 0), 0
    speakers = {d.speaker for sh in seg.shots for d in sh.dialogue}
    pics = 1 if seg.first_frame else 0
    audio = 0
    for cid in seg.character_ids:
        try:
            c = ep.char(cid)
        except StopIteration:
            continue
        n = min(3, len(c.reference_images), int((seg.character_refs or {}).get(cid, 3)))
        pics += n
        if c.voice_reference and n and cid in speakers:
            audio += 1
    try:
        if ep.scene(seg.scene_id).reference_images and seg.use_scene_reference:
            pics += 1
    except StopIteration:
        pass
    for pid in seg.prop_ids:
        try:
            pics += 1 if ep.prop(pid).reference_images else 0
        except StopIteration:
            pass
    return min(pics, 9), min(audio, 3)


def reference_problems(ep: "Episode") -> list[str]:
    out = []
    for seg in ep.segments:
        for cid, n in (seg.character_refs or {}).items():
            if cid not in seg.character_ids:
                out.append(f"segment {seg.id}: character_refs names {cid}, who is not in this segment's character_ids")
            elif not isinstance(n, int) or not 0 <= n <= 3:
                out.append(f"segment {seg.id}: character_refs[{cid}] must be 0, 1, 2 or 3 (how many of the reference pictures to attach)")
    bare = [seg.id for seg in ep.segments if seg.mode == "ref2va" and reference_count(ep, seg) == (0, 0)]
    if bare:
        which = "every segment" if len(bare) == len(ep.segments) else "segment " + ", ".join(bare)
        out.append(f"{which}: WARN mode is ref2va but nothing bound has a reference picture or a voice sample - the prompt is "
                   f"built as plain text-to-video (three-part layout; run it on the FL2VA weights) and nothing holds faces, "
                   f"set or voices the same from one segment to the next. Fine for a one-off shot; for a story, make the "
                   f"reference pictures first (references/image-stage.md)")
    for seg in ep.segments:
        pics, audio = reference_count(ep, seg)
        if seg.mode == "ref2va" and pics + audio > 6:
            out.append(f"segment {seg.id}: WARN {pics} picture(s) + {audio} voice reference(s) = {pics + audio} references; community "
                       f"tests found 6 or fewer the most stable. Options: fewer pictures for a secondary character in this "
                       f"segment (\"character_refs\": {{\"<id>\": 1}}), "
                       f"use_scene_reference false, or leave out a prop that is only glimpsed")
    return out


# ---------------------------------------------------------------- how people are written into prompts

_ARTICLE_RE = re.compile(r"^(?:an?|the)\s+", re.I)
IDENTITY_WORDS = 30       # the look is repeated where a person first appears; official examples use 10-20 words


def identity_head(phrase: str) -> str:
    """"a woman in her early thirties with short black hair, ..." -> "woman in her early thirties" (the part
    prompts use to call the person; prompt_builder.split_identity cuts at the same place)."""
    t = _ARTICLE_RE.sub("", (phrase or "").strip().rstrip(". "))
    cuts = [c for c in (t.find(" with "), t.find(",")) if c > 0]
    return t[:min(cuts)].strip() if cuts else t


def designation_of(c: "Character") -> str:
    s = (c.short_phrase or "").strip().rstrip(". ")
    return ("the " + _ARTICLE_RE.sub("", s if s else identity_head(c.identity_phrase))).lower()


def identity_problems(ep: "Episode") -> list[str]:
    out = []
    for c in ep.characters:
        p = (c.identity_phrase or "").strip()
        if not p:
            out.append(f"character {c.id}: identity_phrase is empty")
            continue
        if not _ARTICLE_RE.match(p):
            out.append(f"character {c.id}: WARN identity_phrase should read \"a <who> with <features>\" "
                       f"(\"a woman in her thirties with short black hair, ...\"); prompts call the person "
                       f"\"{designation_of(c)}\" - it starts with {p.split()[0]!r}")
        elif " with " not in p and "," not in p and c.reference_images:
            out.append(f"character {c.id}: WARN identity_phrase names nothing that can be seen (\"a <who> with <hair>, <main "
                       f"garment>, <one marker>\" - write what the reference picture shows; fewer items are fine)")
        n = len(p.split())
        if n > IDENTITY_WORDS:
            out.append(f"character {c.id}: WARN identity_phrase is {n} words and is repeated where the person first appears in "
                       f"every segment. With a reference picture the prompt only needs what tells this person apart at a "
                       f"glance - hair, main garment and colour, one marker (about 12-25 words). Move the fine detail to "
                       f"sheet_phrase, which only the image stage reads")
        if c.voice_phrase.strip() and " with " not in c.voice_phrase and "voice" not in c.voice_phrase.lower():
            out.append(f"character {c.id}: WARN voice_phrase should read \"a <who> with a <pitch / texture> voice and a <pace> "
                       f"pace\"")
    for seg in ep.segments:
        seen: dict[str, str] = {}
        for cid in seg.character_ids:
            try:
                d = designation_of(ep.char(cid))
            except StopIteration:
                continue
            for other, od in seen.items():
                if d == od or d.startswith(od + " ") or od.startswith(d + " "):
                    out.append(f"segment {seg.id}: WARN {other} and {cid} are both called \"{od if len(od) <= len(d) else d}\" in "
                               f"prompts - give each a short_phrase that tells them apart (\"the grey-haired doctor in the "
                               f"white coat\")")
            seen[cid] = d
    return out


_LOOK_WORD = re.compile(r"[a-z]{4,}")
_LOOK_STOP = {"with", "over", "from", "into", "that", "this", "left", "right", "hand", "hands", "side", "back", "around",
              "about", "early", "late", "years", "woman", "girl", "person", "each", "both"}
_RESTATED = re.compile(r"\{([A-Za-z0-9_\u4e00-\u9fff-]+)\}\s*,\s*([^,.;{}]{3,90})[,.;]")


def restated_look_problems(ep: "Episode") -> list[str]:
    """"{a}, short black hair and beige trench coat, sits ..." - the builder already repeats the look where a
    person first appears and adds a short reminder at later cuts; a second copy in the action doubles it."""
    out = []
    for seg in ep.segments:
        hits = []
        for sh in seg.shots:
            for name in ("framing", "action", "performance"):
                for m in _RESTATED.finditer(getattr(sh, name, "") or ""):
                    cid = m.group(1)
                    if cid not in seg.character_ids:
                        continue
                    try:
                        c = ep.char(cid)
                    except StopIteration:
                        continue
                    own = set(_LOOK_WORD.findall(f"{c.identity_phrase} {c.short_phrase}".lower())) - _LOOK_STOP
                    if len(set(_LOOK_WORD.findall(m.group(2).lower())) & own) >= 2:
                        hits.append((sh.index, f"{{{cid}}}, {m.group(2).strip()}"))
        if hits:
            shots = ", ".join(str(i) for i in sorted({i for i, _ in hits}))
            out.append(f"segment {seg.id}: WARN shot {shots} restate{'s' if len({i for i, _ in hits}) == 1 else ''} a person's look "
                       f"after the placeholder (\"{hits[0][1]}\"{f' and {len(hits) - 1} more' if len(hits) > 1 else ''}). "
                       f"build_prompts.py already repeats the look where the person first appears and adds a reminder at later "
                       f"cuts - write the placeholder and go straight on with the action")
    return out


# ---------------------------------------------------------------- validation

def validate_episode(ep: Episode) -> list[str]:
    """Return a list of human-readable problems. Empty list == OK."""
    problems: list[str] = []
    cids = {c.id for c in ep.characters}
    sids = {s.id for s in ep.scenes}
    pids = {p.id for p in ep.props}
    if ep.ratio not in ("21:9", "16:9", "4:3", "1:1", "3:4", "9:16"):
        problems.append(f"ratio {ep.ratio!r} not in official enum")

    for seg in ep.segments:
        tag = f"segment {seg.id}"
        if not 4 <= seg.duration <= 15:
            problems.append(f"{tag}: duration {seg.duration} outside 4..15")
        elif seg.duration < 5:
            problems.append(f"{tag}: WARN {seg.duration} s is {frames_for_seconds(seg.duration)} frames, below the ~124 frames the open "
                            f"weights were trained on (motion may not finish, sound may thin out) - generate 5 s and trim in the edit")
        if seg.scene_id not in sids:
            problems.append(f"{tag}: unknown scene_id {seg.scene_id}")
        for c in seg.character_ids:
            if c not in cids:
                problems.append(f"{tag}: unknown character_id {c}")
        for p in seg.prop_ids:
            if p not in pids:
                problems.append(f"{tag}: unknown prop_id {p}")
            elif not ep.prop(p).reference_images:
                problems.append(f"{tag}: WARN prop {p} has no reference picture: the prompt describes it in words and the model "
                                f"invents its look, differently in every segment - give it a white-background picture if it has "
                                f"to stay the same")
        if seg.mode not in ("ref2va", "i2va", "fl2va", "t2va"):
            problems.append(f"{tag}: unknown mode {seg.mode}")
        if seg.mode in ("i2va", "fl2va") and not seg.first_frame:
            problems.append(f"{tag}: mode {seg.mode} requires first_frame")
        if seg.mode == "fl2va" and not seg.last_frame:
            problems.append(f"{tag}: fl2va requires last_frame")
        if not seg.shots:
            problems.append(f"{tag}: no shots")
            continue
        if not 1 <= len(seg.shots) <= 4:
            problems.append(f"{tag}: {len(seg.shots)} shots (recommended 1–4 per segment)")
        if seg.shots[0].start != 0:
            problems.append(f"{tag}: first shot must start at 0")
        prev = -1.0
        total_chars = 0
        for sh in seg.shots:
            if sh.start <= prev and sh.index != seg.shots[0].index:
                problems.append(f"{tag} shot {sh.index}: start {sh.start} not strictly increasing")
            prev = sh.start
            if sh.start >= seg.duration:
                problems.append(f"{tag} shot {sh.index}: start {sh.start} >= duration {seg.duration}")
            speakers = [d.speaker for d in sh.dialogue if not d.offscreen and d.speaker != "narrator"]   # a narrator has no mouth on screen
            if len(set(speakers)) > 1:
                problems.append(f"{tag} shot {sh.index}: {len(set(speakers))} on-screen speakers in one shot "
                                f"(one speaker per shot keeps lip-sync stable)")
            if len(sh.on_screen_characters) > 3:
                problems.append(f"{tag} shot {sh.index}: >3 characters with action/lines")
            for d in sh.dialogue:
                if d.speaker != "narrator" and d.speaker not in cids:
                    problems.append(f"{tag} shot {sh.index}: unknown speaker {d.speaker}")
                elif d.speaker != "narrator" and d.speaker not in seg.character_ids and not d.offscreen:
                    problems.append(f"{tag} shot {sh.index}: speaker {d.speaker} is not in this segment's character_ids "
                                    f"(add the character to the segment; a voice from someone who is not seen takes "
                                    f"\"offscreen\": true and needs no binding)")
                total_chars += spoken_chars(d.text)
        need = total_chars / CHARS_PER_SECOND + ACTING_MARGIN if total_chars else 0
        if need > seg.duration:
            problems.append(f"{tag}: {total_chars} spoken characters need ~{need:.1f}s (characters / 4.5 + 2 s of acting) "
                            f"but the segment is {seg.duration}s")
        if any(w in seg.soundscape.lower() for w in ("tense", "sad", "紧张", "悲伤")) and len(seg.soundscape) < 40:
            problems.append(f"{tag}: soundscape is a mood word, write concrete sounds")

    # hand-off state: every segment except the first needs continuity, every segment needs an end_state
    for i, seg in enumerate(ep.segments):
        if not seg.end_state.strip():
            problems.append(f"segment {seg.id}: end_state is empty; the next segment cannot pick up positions")
        if i > 0 and not seg.continuity.strip() and not staging_for(ep, seg):
            problems.append(f"segment {seg.id}: continuity is empty; positions/wardrobe will drift from the previous segment "
                            f"(a segment that opens a new scene may give a `stagings` entry instead)")
        if seg.continuity.strip().startswith(OBSERVED):
            if i == 0:
                problems.append(f"segment {seg.id}: '{OBSERVED}' needs a previous segment")
            elif ep.segments[i - 1].scene_id != seg.scene_id:
                problems.append(f"segment {seg.id}: WARN '{OBSERVED}' points at {ep.segments[i - 1].id}, which is a different scene")
        if seg.status not in ("planned", "generated", "accepted", "accepted_with_deviation", "rejected"):
            problems.append(f"segment {seg.id}: unknown status {seg.status!r}")
        if seg.status.startswith("accepted") and not seg.observed_end_state.strip() and i + 1 < len(ep.segments) \
                and ep.segments[i + 1].scene_id == seg.scene_id:
            problems.append(f"segment {seg.id}: WARN accepted but not observed - the next segment plays in the same scene; "
                            f"run observe_take.py so it opens from where this take really ends")
        if seg.status == "accepted_with_deviation" and not seg.accepted_deviations:
            problems.append(f"segment {seg.id}: status accepted_with_deviation but accepted_deviations is empty")
        if seg.observed_end_state.strip() and seg.observation_confidence == "low":
            problems.append(f"segment {seg.id}: WARN observed_end_state has low confidence - look at the frames again before "
                            f"the next segment relies on it")
        for sh in seg.shots:
            if len(sh.action.split()) < 8:
                problems.append(f"segment {seg.id} shot {sh.index}: action is too short to be a start→change→end description")
    problems += identity_problems(ep)
    problems += state_problems(ep)
    problems += speech_problems(ep)
    problems += reference_problems(ep)
    problems += restated_look_problems(ep)
    problems += staging_problems(ep)
    problems += placeholder_problems(ep)
    # consecutive static dialogue segments (Short-Drama-Studio rule)
    static_run = 0
    for seg in ep.segments:
        is_static = all(("static" in sh.camera.lower() or "push" in sh.camera.lower()) and sh.dialogue
                        for sh in seg.shots)
        static_run = static_run + 1 if is_static else 0
        if static_run >= 3:
            problems.append(f"segment {seg.id}: third consecutive static-dialogue segment; add a wide move or action beat")
            static_run = 0
    return problems
