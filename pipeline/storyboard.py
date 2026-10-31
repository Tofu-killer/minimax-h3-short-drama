"""Storyboard data model + validation.

One Segment == one H3 generation (4–15 s) == one API call.
Field design merges huobao-drama's storyboard-breaker skill, Hailuo-AI-Short-Drama-Studio's
director agent, and MiniMax's official six-column shot table
(Shot ID & Duration | Continuity Handoff | Reference Anchors | Hook Type | Per-Second Directives | Audio & Dialogue Track).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
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
    return cls(**d)


def _resolve(base: Path, src: Optional[str]) -> Optional[str]:
    """Local asset paths are relative to the episode JSON; URLs / mm_file:// / data: pass through."""
    if not src or src.startswith(("http://", "https://", "mm_file://", "data:")) or Path(src).is_absolute():
        return src
    return str((base / src).resolve())


def load_episode(path: str | Path) -> Episode:
    path = Path(path)
    base = path.parent
    raw = json.loads(path.read_text(encoding="utf-8"))
    characters = [Character(**c) for c in raw["characters"]]
    scenes = [Scene(**s) for s in raw["scenes"]]
    props = [Prop(**p) for p in raw.get("props", [])]
    for obj in (*characters, *scenes, *props):
        obj.reference_images = [_resolve(base, i) for i in obj.reference_images]
    for c in characters:
        c.voice_reference = _resolve(base, c.voice_reference)
    segments = []
    for s in raw["segments"]:
        s = {**s, "first_frame": _resolve(base, s.get("first_frame")), "last_frame": _resolve(base, s.get("last_frame"))}
        s.pop("first_frame_prompt", None)   # LLM-stage field, not needed at generation time
        shots = []
        for sh in s["shots"]:
            dl = [Dialogue(**d) for d in sh.get("dialogue", [])]
            shots.append(Shot(**{**sh, "dialogue": dl}))
        segments.append(Segment(**{**s, "shots": shots}))
    return Episode(title=raw["title"], ratio=raw["ratio"], style=raw.get("style", "Live-action, cinematic"),
                   characters=characters, scenes=scenes, props=props, segments=segments,
                   synopsis=raw.get("synopsis", ""))


def dump_episode(ep: Episode) -> str:
    return json.dumps(asdict(ep), ensure_ascii=False, indent=2)


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
