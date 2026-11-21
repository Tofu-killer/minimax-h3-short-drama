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
    identity_phrase: str            # reused verbatim in every segment
    voice_phrase: str = ""          # e.g. "a woman in her late twenties with a low, slightly husky voice"
    reference_images: list[str] = field(default_factory=list)   # face / outfit / full-body
    voice_reference: Optional[str] = None                        # 2–15 s clean speech


@dataclass
class Scene:
    id: str
    name: str
    description: str                # written once, pasted unchanged
    reference_images: list[str] = field(default_factory=list)


@dataclass
class Prop:
    id: str
    name: str
    description: str
    reference_images: list[str] = field(default_factory=list)
    rarity: Optional[str] = None     # 三角洲 loot tier: red/gold/purple/blue/green/white; overlaid in post, not rendered


@dataclass
class Dialogue:
    speaker: str                    # character id, or "narrator"
    language: str                   # "Chinese" / "English" ...
    text: str
    delivery: str = ""              # "softly", "calm and quiet", ...
    offscreen: bool = False         # voice-over -> lips closed


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
    hook_type: str = ""             # hook / setup / turn / cliffhanger
    negatives: str = ""             # "no other people, no signage"
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
    """Local asset paths are relative to the episode JSON; URLs / mm_file:// / data: pass through."""
    if not src or src.startswith(("http://", "https://", "mm_file://", "data:")) or Path(src).is_absolute():
        return src
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
        raise ValueError(f"segment {seg.id} opens from the observed end of {prev.id}, which has no accepted take with an "
                         f"observed_end_state yet - accept a take of {prev.id} and run observe_take.py "
                         f"(or build with --allow-planned for drafts)")
    text = f"The clip opens from this state: {base.rstrip('.')}."
    return (text + " " + extra).strip(), src


SIDES = {"left": "on the left side of the frame", "centre": "at the centre of the frame", "center": "at the centre of the frame",
         "right": "on the right side of the frame"}
NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six"]


def staging_for(ep: "Episode", seg: "Segment") -> Optional[dict]:
    return next((st for st in ep.stagings if st.get("segment") == seg.id), None)


def blocking_sentence(ep: "Episode", seg: "Segment") -> str:
    """One sentence, generated from data, that pins who is where when a scene opens. Written by code so that the
    same positions are stated the same way every time: "{a} sits at the left end of the sofa on the left side of
    the frame, facing frame right; {b} stands by the door on the right side of the frame, facing {a}. Exactly two
    people are in the scene; the other seats stay empty." Returns "" when the segment has no staging entry."""
    st = staging_for(ep, seg)
    if not st or not st.get("places"):
        return ""
    parts = []
    for pl in st["places"]:
        bits = [f"{{{pl['character']}}} {pl.get('posture', 'stands')} {pl['at'].strip()}"]
        if pl.get("side"):
            bits.append(SIDES.get(pl["side"].lower(), pl["side"]))
        text = " ".join(bits)
        if pl.get("facing"):
            text += f", facing {pl['facing'].strip()}"
        parts.append(text)
    n = len(st["places"])
    count = NUMBER_WORDS[n] if n < len(NUMBER_WORDS) else str(n)
    tail = f" Exactly {count} {'person is' if n == 1 else 'people are'} in the scene"
    tail += f"; {st['others'].strip().rstrip('.')}." if st.get("others") else "."
    return "; ".join(parts) + "." + tail


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
        if not places:
            out.append(f"{tag}: no places")
        seen = set()
        for pl in places:
            cid = pl.get("character")
            if cid not in seg.character_ids:
                out.append(f"{tag}: {cid} is placed but is not in segment {seg.id}'s character_ids "
                           f"(someone who enters later is not part of the opening positions)")
            if not (pl.get("at") or "").strip():
                out.append(f"{tag}: {cid} has no 'at' (what they stand / sit next to)")
            if pl.get("side") and pl["side"].lower() not in SIDES:
                out.append(f"{tag}: side {pl['side']!r} for {cid} - use left / centre / right")
            key = ((pl.get("at") or "").strip().lower(), (pl.get("side") or "").lower())
            if key in seen:
                out.append(f"{tag}: two characters share {pl.get('at')!r} on the {pl.get('side')} - give each their own spot")
            seen.add(key)
            try:
                desc = ep.scene(seg.scene_id).description.lower()
                words = [w for w in re.findall(r"[a-z]{4,}", (pl.get("at") or "").lower()) if w not in
                         ("the", "left", "right", "side", "near", "next", "from", "with", "behind", "front", "centre", "center", "edge", "end")]
                if words and not any(w in desc for w in words):
                    out.append(f"{tag}: WARN {pl.get('at')!r} is not mentioned in the scene description - anchor positions to "
                               f"things the scene master actually shows")
            except StopIteration:
                pass
        missing = [c for c in seg.character_ids if c not in {pl.get("character") for pl in places}]
        if missing:
            out.append(f"{tag}: WARN {', '.join(missing)} appear in segment {seg.id} but have no opening position")
    # a scene with two or more people that opens without positions is where left/right mix-ups start
    opened = set()
    for seg in ep.segments:
        first_visit = seg.scene_id not in opened
        opened = {seg.scene_id}
        if first_visit and len(seg.character_ids) >= 2 and not staging_for(ep, seg) and ep.stagings:
            out.append(f"segment {seg.id}: WARN opens scene {seg.scene_id} with {len(seg.character_ids)} people but has no staging entry")
    return out


def shot_spans(seg: "Segment") -> list[tuple["Shot", float, float]]:
    """[(shot, start, end)] with ends taken from the next shot's start / the segment duration."""
    out = []
    for i, sh in enumerate(seg.shots):
        end = seg.shots[i + 1].start if i + 1 < len(seg.shots) else float(seg.duration)
        out.append((sh, float(sh.start), float(end)))
    return out


def _framing_class(framing: str) -> str:
    f = framing.lower()
    for key, cls in (("extreme close", "extreme close-up"), ("medium close", "medium close-up"), ("insert", "insert"),
                     ("close-up", "close-up"), ("close up", "close-up"), ("closeup", "close-up"),
                     ("medium wide", "medium wide"), ("medium long", "medium wide"), ("cowboy", "medium wide"),
                     ("medium", "medium"), ("mid shot", "medium"), ("two-shot", "medium"),
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
            chars = sum(len(re.sub(r"\s", "", d.text)) for d in sh.dialogue)
            if chars and chars > 3 * (e0 - s0) + 1:
                out.append(f"segment {seg.id} shot {sh.index}: {chars} characters in a {e0 - s0:.1f}s shot "
                           f"(about {3 * (e0 - s0):.0f} fit) - the line will be rushed or cut off")
            all_shots.append((seg.id, sh.index, _framing_class(sh.framing)))
            events_by_t.append(offset + s0)
            events_by_t += [offset + s0] * len(sh.dialogue)
        offset += seg.duration
    run = 1
    for (a, b) in zip(all_shots, all_shots[1:]):
        run = run + 1 if (a[2] == b[2] and a[2] != "other") else 1
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
        if seg.scene_id not in sids:
            problems.append(f"{tag}: unknown scene_id {seg.scene_id}")
        for c in seg.character_ids:
            if c not in cids:
                problems.append(f"{tag}: unknown character_id {c}")
        for p in seg.prop_ids:
            if p not in pids:
                problems.append(f"{tag}: unknown prop_id {p}")
            elif not ep.prop(p).reference_images:
                problems.append(f"{tag}: prop {p} bound without a reference image; the model will invent its look")
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
            speakers = [d.speaker for d in sh.dialogue if not d.offscreen]
            if len(set(speakers)) > 1:
                problems.append(f"{tag} shot {sh.index}: {len(set(speakers))} on-screen speakers in one shot "
                                f"(one speaker per shot keeps lip-sync stable)")
            if len(sh.on_screen_characters) > 3:
                problems.append(f"{tag} shot {sh.index}: >3 characters with action/lines")
            for d in sh.dialogue:
                if d.speaker != "narrator" and d.speaker not in cids:
                    problems.append(f"{tag} shot {sh.index}: unknown speaker {d.speaker}")
                total_chars += len(re.sub(r"\s", "", d.text))
        need = total_chars / CHARS_PER_SECOND + ACTING_MARGIN if total_chars else 0
        if need > seg.duration:
            problems.append(f"{tag}: dialogue needs ~{need:.1f}s (chars/4.5 + 2) but duration is {seg.duration}s")
        if any(w in seg.soundscape.lower() for w in ("tense", "sad", "紧张", "悲伤")) and len(seg.soundscape) < 40:
            problems.append(f"{tag}: soundscape is a mood word, write concrete sounds")

    # hand-off state: every segment except the first needs continuity, every segment needs an end_state
    for i, seg in enumerate(ep.segments):
        if not seg.end_state.strip():
            problems.append(f"segment {seg.id}: end_state is empty; the next segment cannot pick up positions")
        if i > 0 and not seg.continuity.strip():
            problems.append(f"segment {seg.id}: continuity is empty; positions/wardrobe will drift from the previous segment")
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
    problems += staging_problems(ep)
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
