"""Build official-format H3 prompts + content arrays from a Segment.

Two structures, straight from MiniMax-AI/MiniMax-H3 skills/h3-prompt-writing:
  * three-part  (T2VA / I2VA / FL2VA)  integrated_multimodal_description / overall_soundscape / non_diegetic_music
  * six-part    (Ref2VA)               subject_definitions / summary / retention_analysis / detailed_description /
                                       overall_soundscape / non_diegetic_music
Reference labels <Picture N> / <Audio N> are numbered by position in the content array.
"""
from __future__ import annotations

from dataclasses import dataclass

from h3_client import audio_item, image_item, text_item
from storyboard import Dialogue, Episode, Segment, Shot

MAX_REF_IMAGES = 9
MAX_REF_AUDIO = 3


def timecode(sec: float) -> str:
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m:02d}:{s:06.3f}"


def speaker_ids(seg: Segment) -> dict[str, str]:
    """Stable (S1)/(S2) IDs per segment, only for characters who vocalise."""
    ids: dict[str, str] = {}
    for sh in seg.shots:
        for d in sh.dialogue:
            if d.speaker not in ids:
                ids[d.speaker] = f"S{len(ids) + 1}"
    return ids


def render_dialogue(d: Dialogue, who: str, sid: str) -> str:
    delivery = f" {d.delivery}" if d.delivery else ""
    line = f"<d>[{d.language}] {d.text}</d>"
    if d.offscreen:
        return (f"{who} ({sid}) says in an off-screen voiceover{delivery}: {line} "
                f"while the on-screen character's lips remain completely closed.")
    return f"{who} ({sid}) says{delivery}: {line}"


@dataclass
class BuiltPrompt:
    text: str
    content: list[dict]
    labels: dict[str, str]          # e.g. {"char_a": "<Picture 1>", "scene_cafe": "<Picture 3>"}


# ---------------------------------------------------------------- shared body

def _shot_sentences(ep: Episode, seg: Segment, sh: Shot, is_first: bool, subj_label) -> str:
    parts = []
    head = f"[Shot {sh.index}]"
    if not is_first:
        head += f" At {timecode(sh.start)}, the shot cuts to"
    action = sh.action.strip()
    if action and action[-1] not in ".!?。！？":
        action += "."
    parts.append(f"{head} {sh.framing}: {action}")
    if sh.camera:
        parts.append(sh.camera.rstrip(".") + ".")
    sids = speaker_ids(seg)
    for d in sh.dialogue:
        if d.speaker == "narrator":
            who = "The narrator"
        else:
            c = ep.char(d.speaker)
            who = f"{subj_label(d.speaker)}, {c.voice_phrase}" if c.voice_phrase else subj_label(d.speaker)
        parts.append(render_dialogue(d, who, sids[d.speaker]))
    return " ".join(parts)


# ---------------------------------------------------------------- six-part (Ref2VA)

def build_ref2va(ep: Episode, seg: Segment) -> BuiltPrompt:
    content: list[dict] = []
    labels: dict[str, str] = {}
    pic = 0
    aud = 0
    defs: list[str] = []
    retention: list[str] = []

    # characters first (identity), then scene, then props
    for cid in seg.character_ids:
        c = ep.char(cid)
        imgs = c.reference_images[:3]
        if not imgs:
            continue
        pics = []
        for src in imgs:
            if pic >= MAX_REF_IMAGES:
                break
            pic += 1
            content.append(image_item(src, "reference_image"))
            pics.append(f"<Picture {pic}>")
        subj = f"<Subject {len(defs) + 1}>"
        labels[cid] = subj
        defs.append(f"{subj} is {c.name}, the person in {' and '.join(pics)}, {c.identity_phrase}.")
        shots_in = [f"[Shot {sh.index}]" for sh in seg.shots if cid in sh.on_screen_characters]
        retention.append(f"{subj} (appears in {', '.join(shots_in) or 'all shots'}): fully_preserved - "
                         f"face, hair, build and outfit are retained from {pics[0]}"
                         + (f"; {pics[1]} controls outfit and silhouette only" if len(pics) > 1 else "")
                         + ". Do not reuse the reference's background.")
        if c.voice_reference and aud < MAX_REF_AUDIO:
            aud += 1
            content.append(audio_item(c.voice_reference, "reference_audio"))
            defs.append(f"<Audio {aud}> is the voice-timbre reference for {subj} ({speaker_ids(seg).get(cid, 'S?')}).")
            retention.append(f"<Audio {aud}>: reference - timbre only; do not carry its original words into the video.")

    sc = ep.scene(seg.scene_id)
    if sc.reference_images and pic < MAX_REF_IMAGES:
        pic += 1
        content.append(image_item(sc.reference_images[0], "reference_image"))
        subj = f"<Subject {len(defs) + 1}>"
        labels[sc.id] = subj
        defs.append(f"{subj} is {sc.name} in <Picture {pic}>: {sc.description}")
        retention.append(f"{subj}: partially_preserved - layout, lighting and set dressing are retained; "
                         f"never transfer facial traits from <Picture {pic}>.")
    else:
        labels[sc.id] = sc.name

    for pid in seg.prop_ids:
        p = ep.prop(pid)
        if p.reference_images and pic < MAX_REF_IMAGES:
            pic += 1
            content.append(image_item(p.reference_images[0], "reference_image"))
            subj = f"<Subject {len(defs) + 1}>"
            labels[pid] = subj
            defs.append(f"{subj} is {p.name}, the exact item shown in <Picture {pic}>: {p.description}")
            retention.append(f"{subj}: fully_preserved - the item's shape, colour, markings and material are retained exactly; "
                             f"no other item is substituted.")

    def subj_label(cid: str) -> str:
        return labels.get(cid, ep.char(cid).name)

    shots_txt = " ".join(_shot_sentences(ep, seg, sh, i == 0, subj_label) for i, sh in enumerate(seg.shots))
    scene_lead = f"{seg.style}. {sc.description}" if sc.id not in labels or not labels[sc.id].startswith("<") \
        else f"{seg.style}. The setting is {labels[sc.id]}."
    body = f"{scene_lead} {seg.continuity + ' ' if seg.continuity else ''}{shots_txt}"
    if seg.end_state:
        body += f" The segment ends with {seg.end_state}."
    if seg.negatives:
        body += f" {seg.negatives}."

    summary = (f"[reference generation{' + audio reference' if aud else ''}] {seg.hook_type + ': ' if seg.hook_type else ''}"
               f"{len(seg.shots)} shot{'s' if len(seg.shots) > 1 else ''}, {seg.duration} seconds, {ep.ratio}.")

    text = (
        "subject_definitions: " + " ".join(defs) + "\n\n"
        "summary: " + summary + "\n\n"
        "retention_analysis: " + " ".join(retention) + "\n\n"
        "detailed_description: " + body + "\n\n"
        "overall_soundscape: " + seg.soundscape.strip() + "\n\n"
        "non_diegetic_music: " + (seg.music.strip() or "N/A")
    )
    content.insert(0, text_item(text))
    return BuiltPrompt(text=text, content=content, labels=labels)


# ---------------------------------------------------------------- three-part (T2VA / I2VA / FL2VA)

def build_three_part(ep: Episode, seg: Segment) -> BuiltPrompt:
    content: list[dict] = []
    header = ""
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
                  f"{seg.duration:.2f}-second mark of the target video.\n\n")

    def subj_label(cid: str) -> str:
        c = ep.char(cid)
        return f"{c.name}, {c.identity_phrase}"

    sc = ep.scene(seg.scene_id)
    shots_txt = " ".join(_shot_sentences(ep, seg, sh, i == 0, subj_label) for i, sh in enumerate(seg.shots))
    anchor = ""
    if seg.mode in ("i2va", "fl2va"):
        anchor = (" The opening frame shown in <Picture 1> is preserved: appearance, clothing, position and set "
                  "layout stay as established.")
    body = f"{seg.style}, {sc.description}{anchor} {seg.continuity + ' ' if seg.continuity else ''}{shots_txt}"
    if seg.mode == "fl2va":
        body += " The shot settles into the pose, spacing and composition established by Picture 2 at the end."
    elif seg.end_state:
        body += f" The segment ends with {seg.end_state}."
    if seg.negatives:
        body += f" {seg.negatives}."

    text = (
        header +
        "integrated_multimodal_description: " + body + "\n\n"
        "overall_soundscape: " + seg.soundscape.strip() + "\n\n"
        "non_diegetic_music: " + (seg.music.strip() or "N/A")
    )
    content.insert(0, text_item(text))
    return BuiltPrompt(text=text, content=content, labels={})


def build(ep: Episode, seg: Segment) -> BuiltPrompt:
    if seg.mode == "ref2va":
        return build_ref2va(ep, seg)
    return build_three_part(ep, seg)


# ---------------------------------------------------------------- subtitles

def dialogue_cues(ep: Episode, seg: Segment, offset: float) -> list[tuple[float, float, str, str]]:
    """Rough SRT cues: each shot's lines are spread evenly across that shot's span."""
    cues = []
    bounds = [sh.start for sh in seg.shots] + [float(seg.duration)]
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
