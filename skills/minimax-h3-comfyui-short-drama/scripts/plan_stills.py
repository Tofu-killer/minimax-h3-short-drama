#!/usr/bin/env python3
"""Plan the still pictures of an episode: write every image prompt and list, picture by picture, the command that makes it.

    python plan_stills.py episodes/ep01.json                 # writes bible/prompts/*.txt and bible/stills_plan.md
    python plan_stills.py episodes/ep01.json --back dr_zhou  # also a back view of that character (over-the-shoulder shots)

Reads the storyboard and nothing else. For every picture the storyboard names it works out
  * the prompt, from the templates in assets/image-prompts.md:
      bust / full body / face (and side / back on request)  <- the character's sheet_phrase
      scene master, nine-grid                                <- the scene's description
      prop                                                   <- the prop's description
      first frame, shot keyframe                             <- the segment's first_frame_prompt, the shot's keyframe_prompt
                                                                (written at the storyboard stage; a list = two editing steps)
  * the workflow file, the pictures that go into image1..image3 (read from the "Picture N" sentences of the prompt),
    the size, how many candidates, the folder and the tag
  * the file the chosen candidate is copied to - the path the storyboard already uses.
Pictures that are on disk already are listed as done and left out of the count. A prompt file follows the storyboard: when the text the
storyboard gives changes (a first_frame_prompt rewritten after a take ended differently), the file is written again and
the picture made from the earlier text is listed as MAKE AGAIN. A prompt file you edited by hand is kept as it is;
--rewrite replaces it. (What was written, and which prompt each picture belongs to, is remembered in
<prompts>/.stills_plan.json.)

The commands are printed for comfy_submit.py: run each one with --dry-run first, look at the preview, then run it
again with --confirm <batch id>. Nothing is submitted by this script and no GPU is used.

Order: everything the text-to-picture model makes (busts, scene masters, props) first, then - after you chose the
busts - everything Qwen-Image-Edit-2511 makes (views, first frames, keyframes): each model is loaded once.

The text-to-picture model is Qwen-Image 2.1 by default. Its licence is for research: a project that earns money
uses --t2i zimage instead (Z-Image-Turbo, Apache-2.0; workflow zimage_turbo_t2i.api.json, files: fetch_models.py
--sets zimage). The edit model, Qwen-Image-Edit-2511, is Apache-2.0 either way.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "h3lib"))
W = HERE.parent / "assets" / "workflows"
NEGATIVE = "text, watermark, caption, collage, split panels, extra person, extra fingers, waxy skin"

VIEWS = {
    "full": ("bust", "Full-body front view standing upright, from the top of the head to the soles of the shoes with a little white "
                     "margin above and below, arms relaxed at the sides, hands empty, calm neutral expression, lips closed."),
    "face": ("bust", "Front-facing head-and-shoulders close-up at eye level with the face filling the frame, calm neutral expression, "
                     "lips closed, looking into the camera."),
    "side": ("full", "Full-body strict 90-degree side view standing upright, from the top of the head to the soles of the shoes with a "
                     "little white margin above and below, same scale and camera distance as Picture 1, arms relaxed at the sides, hands empty."),
    "back": ("full", "Full-body back view standing upright, from the top of the head to the soles of the shoes with a little white "
                     "margin above and below, same scale and camera distance as Picture 1, arms relaxed at the sides, hands empty."),
}


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def sentence(text: str) -> str:
    text = " ".join(str(text).split()).rstrip(". ")
    return (text[0].upper() + text[1:] + ".") if text else ""


def is_anime(style: str) -> bool:
    return bool(re.search(r"anime|cel[- ]shad|2d animation|animated|donghua|manga|cartoon|3d animation|漫|动画", style or "", re.I))


def body(look: str) -> str:
    """'About 165 cm tall with a slim build, ' when the look says so in the usual words, else ''."""
    m = re.search(r"about (\d{2,3}) ?cm(?: tall)?(?:,? and| with an?) ([a-z-]+)", look, re.I)
    return f"About {m.group(1)} cm tall with a {m.group(2)} build, " if m else ""


def bust_prompt(look: str, style: str) -> str:
    if is_anime(style):
        return (f"Anime character bust portrait, a single character in one image, facing the viewer at eye level, plain white background, "
                f"even flat lighting, {style.rstrip('. ')}. {sentence(look)} Calm expression, mouth closed. "
                f"Clean frame containing only the depicted subject.")
    return (f"Studio character reference photo, a single person in one image, medium close-up bust portrait facing the camera at eye level, "
            f"plain light grey seamless background, soft even studio light with a matte skin finish, sharp focus, realistic photograph. "
            f"{sentence(look)} Gentle natural expression, lips closed. Clean frame containing only the depicted subject.")


def view_prompt(look: str, style: str, view: str) -> str:
    if is_anime(style):
        return (f"Keep exactly the same character as Picture 1: same face, hairstyle, outfit, line weight and colors ({look.rstrip('. ')}). "
                f"New frame: an anime character model view of this one character alone on a seamless pure white background, even flat "
                f"lighting, {style.rstrip('. ')}. {VIEWS[view][1]} {body(look)}consistent proportions of 6 heads tall. "
                f"One single character, the only subject in the image. Clean frame containing only the depicted subject.")
    return (f"Keep exactly the same person as Picture 1: same face, hairstyle, outfit, accessories and marks ({look.rstrip('. ')}). "
            f"New photo: a character reference view of this one person alone on a seamless pure white background, soft even studio "
            f"lighting with a matte skin finish. {VIEWS[view][1]} {body(look)}true body proportions of 7 heads tall. "
            f"One single person, the only subject in the image. Live-action photograph, 85mm lens look, natural skin texture, "
            f"true-to-life colors. Clean frame containing only the depicted subject.")


def master_prompt(desc: str, style: str, ratio: str) -> str:
    place = desc.rstrip(". ")
    if is_anime(style):
        return (f"An anime background painting of {place}, with nobody in it. Wide establishing view at eye level along the main axis, "
                f"{ratio}, painted style matching the character sheets, {style.rstrip('. ')}. "
                f"The space holds only its architecture and furniture, deserted and still.")
    return (f"A cinematic film still of {place}, with nobody in it. Wide establishing view at eye level along the main axis, {ratio}. "
            f"Soft falloff with detail kept in the shadows. Shot on a 35mm lens at f/4, deep focus, true-to-life colors, uncluttered. "
            f"The space holds only its architecture and furniture, deserted and still.")


def grid_prompt(desc: str, style: str, ratio: str) -> str:
    # the episode's style line describes people and acting; a board of empty rooms only takes the medium from it
    look = style.rstrip(". ") if is_anime(style) else "Live-action photograph, true-to-life colors"
    return (f"One {ratio} location board divided into exactly nine equal panels in a 3x3 grid with thin white gutters. All nine panels show "
            f"the same place, empty of people, with identical architecture, furniture positions, materials, colors, time of day and light "
            f"direction; only the camera position changes. 1 view from the doorway into the room; 2 wide view of the main activity area; "
            f"3 the window side with the light falling in; 4 reverse view from inside toward the door; 5 high overhead view of the floor "
            f"layout; 6 long-lens diagonal view from one corner to the opposite corner; 7 close view of the most distinctive piece of "
            f"furniture; 8 close view of a wall detail; 9 the view out of the window. A small numeral 1-9 in each panel's top-left corner. "
            f"Uniform 50mm lens, bright even exposure, one white balance. The place: {desc.rstrip('. ')}. {look}. "
            f"Every panel is a deserted space.")


def prop_prompt(desc: str, style: str) -> str:
    if is_anime(style):
        return (f"Anime prop illustration of {desc.rstrip('. ')}, one object centered on a pure white background, 1:1, three-quarter front "
                f"view, {style.rstrip('. ')}. The frame contains only this one object.")
    return (f"Product reference photo of {desc.rstrip('. ')}, one object centered on a seamless pure white background, 1:1, three-quarter "
            f"front view at eye level, soft even studio light with a soft contact shadow beneath it. Sharp focus across the whole object, "
            f"true-to-life colors. The frame contains only this one object.")


def quoted(path) -> str:
    """A path as it has to stand on a command line: in double quotes when it holds a space (cmd, PowerShell and sh agree on that)."""
    text = Path(path).as_posix() if not isinstance(path, str) else path
    return f'"{text}"' if re.search(r"\s", text) else text


def sha(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def pick(refs: list, word: str):
    return next((r for r in refs if word in Path(r).stem.lower()), None)


# The text-to-picture model (busts, scene masters, props). qwen21 = Qwen-Image 2.1, the default: research licence, not
# for projects that earn money. zimage = Z-Image-Turbo, Apache-2.0: its official template runs at 1024x1024, so its
# masters are planned at about 2.4 megapixels and its props at 1024 - larger sizes have not been tried with it here.
T2I = {"qwen21": {"file": "qwen21_t2i.api.json", "prompt": "459:452.prompt", "size": "459:456", "label": "Qwen-Image 2.1",
                  "master": {"16:9": (2688, 1536), "9:16": (1536, 2688)}, "prop": (2048, 2048)},
       "zimage": {"file": "zimage_turbo_t2i.api.json", "prompt": "57:27.text", "size": "57:13", "label": "Z-Image-Turbo",
                  "master": {"16:9": (2048, 1152), "9:16": (1152, 2048)}, "prop": (1024, 1024)}}


class Plan:
    def __init__(self, raw: dict, prompts: Path, rewrite: bool, script: str, t2i: str = "qwen21"):
        self.raw, self.prompts, self.rewrite, self.script = raw, prompts, rewrite, script
        self.t2i = T2I[t2i]
        self.style = raw.get("style", "Live-action, cinematic")
        self.ratio = raw.get("ratio", "16:9")
        self.canvas = {"16:9": (1344, 768), "9:16": (768, 1344)}.get(self.ratio)
        self.master = self.t2i["master"].get(self.ratio, self.t2i["master"]["16:9"])
        self.items: list[dict] = []           # one per picture
        self.notes: list[str] = []
        self.written: list[str] = []
        self.updated: list[str] = []
        self.kept: list[str] = []
        self.record_file = prompts / ".stills_plan.json"      # what this script wrote, and which prompt each picture was made from
        try:
            self.record = json.loads(self.record_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.record = {}
        self.record.setdefault("prompts", {})
        self.record.setdefault("pictures", {})

    # -- prompt files ------------------------------------------------------------------------------------
    def prompt_file(self, name: str, text: str) -> Path:
        """Write <name>.txt. A file this script wrote follows the storyboard (it is written again when the text the
        storyboard gives has changed); a file that was edited by hand is kept unless --rewrite."""
        path = self.prompts / f"{name}.txt"
        text = text.strip() + "\n"
        new, was = sha(text), self.record["prompts"].get(path.name)
        now = sha(path.read_text(encoding="utf-8")) if path.exists() else None
        if now is None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            self.written.append(path.name)
        elif now == new:
            self.kept.append(path.name)
        elif self.rewrite or (was is not None and now == was):
            path.write_text(text, encoding="utf-8")
            self.updated.append(path.name)
        else:                                   # edited by hand (or written by an earlier version): the user's text stands
            self.kept.append(path.name)
            if was is None or was != new:
                self.notes.append(f"{path} differs from what the storyboard gives now and was kept as it is (edited by hand?) - "
                                  f"--rewrite replaces it with the storyboard's text")
            self.record["prompts"][path.name] = was if was is not None else new
            return path
        self.record["prompts"][path.name] = new
        return path

    def picture_state(self, dest: str, prompt: Path | None) -> str:
        """'missing' | 'have' | 'stale' (on disk, but made before its prompt last changed)."""
        if not dest or not Path(dest).exists():
            self.record["pictures"].pop(dest, None)
            return "missing"
        if prompt is None or not prompt.exists():
            return "have"
        now, mtime = sha(prompt.read_text(encoding="utf-8")), round(Path(dest).stat().st_mtime, 2)
        rec = self.record["pictures"].get(dest)
        if rec is None or rec.get("mtime") != mtime:          # first seen, or made again since: it belongs to the prompt of now
            self.record["pictures"][dest] = {"prompt": now, "mtime": mtime}
            return "have"
        return "have" if rec.get("prompt") == now else "stale"

    # -- one picture -------------------------------------------------------------------------------------
    def add(self, phase: str, what: str, dest: str, workflow: str, prompt: Path | None, n: int, out: str, tag: str,
            images: list | None = None, size: tuple | None = None, negative: bool = False, problems: list | None = None,
            needs: list | None = None):
        sets = []
        for k, img in enumerate(images or []):
            sets.append("--set " + quoted(f"{41 + k}.image=@{img}"))
        text_model = workflow == self.t2i["file"]
        key = self.t2i["prompt"] if text_model else "170:151.prompt"
        if prompt is not None:
            sets.append("--set " + quoted(f"{key}=@{prompt.as_posix()}"))
        if negative:
            sets.append("--set " + quoted(f"170:149.prompt={NEGATIVE}"))
        if size:
            holder = self.t2i["size"] if text_model else "170:300"
            default = (1024, 1024) if text_model else (1344, 768)
            if tuple(size) != default:
                sets.append(f"--set {holder}.width={size[0]} --set {holder}.height={size[1]}")
        cmd = f"{self.script} {quoted(W / workflow)} {' '.join(sets)} --batch {n} --seed 1 --out {quoted(out)} --tag {tag}"
        state = self.picture_state(dest, prompt)
        self.items.append({"phase": phase, "what": what, "dest": dest, "have": state == "have", "stale": state == "stale", "n": n,
                           "cmd": cmd, "size": size, "problems": problems or [], "needs": needs or [], "out": out, "tag": tag})

    # -- characters, scenes, props -----------------------------------------------------------------------
    def characters(self, extra_views: dict):
        for c in self.raw.get("characters", []):
            refs = c.get("reference_images") or []
            look = (c.get("sheet_phrase") or "").strip()
            base = Path(refs[0]).parent if refs else Path("bible/chars")
            cid = c["id"]
            paths = {"bust": (base / f"{cid}_bust.png").as_posix(),
                     "face": pick(refs, "face") or (base / f"{cid}_face.png").as_posix(),
                     "full": pick(refs, "full") or (base / f"{cid}_full.png").as_posix()}
            c["_face"] = paths["face"]
            cand = f"bible/candidates/{cid}"
            if not look:
                self.notes.append(f"character {cid} has no sheet_phrase: its bust and views cannot be written - add the full look "
                                  f"(assets/agent-prompts/01-outline.md) and run this again")
                continue
            self.add("A", f"{cid}: bust (the anchor - choose one and freeze it)", paths["bust"], self.t2i["file"],
                     self.prompt_file(f"{cid}_bust", bust_prompt(look, self.style)), 6, cand, "bust", size=(1024, 1024))
            views = ["full", "face"] + [v for v in ("side", "back") if v in extra_views.get(cid, set()) or pick(refs, v)]
            for v in views:
                src = VIEWS[v][0]
                dest = paths.get(v) or pick(refs, v) or (base / f"{cid}_{v}.png").as_posix()
                paths[v] = dest
                self.add("B1" if src == "bust" else "B2", f"{cid}: {v} view (from the {src})", dest, "qwen_edit2511_1ref.api.json",
                         self.prompt_file(f"{cid}_{v}", view_prompt(look, self.style, v)), 3, cand, v, images=[paths[src]],
                         size=(1024, 1024) if v == "face" else (1024, 1536), needs=[paths[src]])
            c["_back"] = paths.get("back")

    def scenes(self):
        for s in self.raw.get("scenes", []):
            refs = s.get("reference_images") or []
            sid = s["id"]
            base = Path(refs[0]).parent if refs else Path("bible/scenes")
            master = refs[0] if refs else (base / f"{sid}_master.png").as_posix()
            s["_master"], s["_dir"] = master, base
            self.add("A", f"scene {sid}: master, no people", master, self.t2i["file"],
                     self.prompt_file(f"{sid}_master", master_prompt(s.get("description", ""), self.style, self.ratio)), 3,
                     f"bible/candidates/{sid}", "master", size=self.master)
            grid = pick(refs[1:], "grid")
            if grid:
                self.add("A", f"scene {sid}: nine-grid (for people to look at and to cut single views from - never a reference)", grid,
                         self.t2i["file"], self.prompt_file(f"{sid}_grid9", grid_prompt(s.get("description", ""), self.style, self.ratio)),
                         2, f"bible/candidates/{sid}", "grid", size=self.master)

    def props(self):
        for p in self.raw.get("props", []):
            refs = p.get("reference_images") or []
            pid = p["id"]
            dest = refs[0] if refs else f"bible/props/{pid}.png"
            p["_pic"] = dest
            self.add("A", f"prop {pid}: one object on white", dest, self.t2i["file"],
                     self.prompt_file(pid, prop_prompt(p.get("description", p.get("name", pid)), self.style)), 3,
                     f"bible/candidates/{pid}", "prop", size=self.t2i["prop"])

    # -- first frames and keyframes ----------------------------------------------------------------------
    def frame_inputs(self, text: str, seg: dict, shot: dict, carried: str | None) -> tuple[list, list]:
        """Which file each "Picture N" of a frame prompt is, read from its own sentences."""
        chars = {c["id"]: c for c in self.raw.get("characters", [])}
        props = {p["id"]: p for p in self.raw.get("props", [])}
        scene = next((s for s in self.raw.get("scenes", []) if s["id"] == seg.get("scene_id")), None)
        got: dict[int, str] = {}
        problems: list[str] = []
        m = re.search(r"Keep everything in Picture (\d)", text)
        if m:
            got[int(m.group(1))] = carried or "<the picture chosen in the step before>"
        on_screen = [c for c in (shot.get("on_screen_characters") or seg.get("character_ids") or []) if c in chars]
        used: set[str] = set()
        for m in re.finditer(r"same (?:person|character) as Picture (\d)(?:[^().]*\(([^)]*)\))?", text):
            n, look = int(m.group(1)), norm(m.group(2) or "")
            hit = next((cid for cid, c in chars.items() if look and norm(c.get("sheet_phrase", "")) and
                        (look == norm(c["sheet_phrase"]) or look in norm(c["sheet_phrase"]) or norm(c["sheet_phrase"]) in look)), None)
            if hit is not None and look != norm(chars[hit]["sheet_phrase"]):
                problems.append(f"Picture {n}: the look quoted in brackets is not {hit}'s sheet_phrase as it is now (the look was "
                                f"changed after this prompt was written?) - copy the current sheet_phrase into the prompt")
            if hit is None:
                hit = next((cid for cid in on_screen if cid not in used), None)
                if hit:
                    problems.append(f"Picture {n}: the look in brackets is not a character's sheet_phrase word for word - taken as "
                                    f"{hit} from the order of on_screen_characters; check it")
            if hit is None:
                problems.append(f"Picture {n}: cannot tell which character it is - set image{n} by hand")
                continue
            used.add(hit)
            got[n] = chars[hit].get("_face") or f"<{hit} face>"
        for m in re.finditer(r"(?:exact item|exact object|same object|item) shown in Picture (\d)", text):
            n = int(m.group(1))
            if n in got:
                continue
            ids = [p for p in seg.get("prop_ids", []) if p in props]
            near = text[max(0, m.start() - 160): m.end() + 40].lower()
            best = next((p for p in ids if any(w in near for w in norm(props[p].get("name_en", "") or p).split() if len(w) > 3)), None)
            if best is None and ids:
                best = ids[0]
                if len(ids) > 1:
                    problems.append(f"Picture {n}: this segment has {len(ids)} props - taken as {best}; check it")
            if best is None:
                problems.append(f"Picture {n}: the prompt points at an item but the segment binds no prop - set image{n} by hand")
            else:
                got[n] = props[best].get("_pic") or f"<{best}>"
        m = re.search(r"(?:room|place|space|location|setting|street|scene|interior|exterior) is the one in Picture (\d)", text)
        if m and scene is not None:
            got[int(m.group(1))] = (Path(scene["_dir"]) / f"{scene['id']}_{seg['id']}_crop.png").as_posix()
        nums = sorted({int(x) for x in re.findall(r"Picture (\d)", text)})
        for n in nums:
            if n not in got:
                problems.append(f"Picture {n} is named in the prompt but none of its sentences says what it is "
                                f"(same person as / exact item shown in / the room is the one in Picture {n}) - set image{n} by hand")
        if nums and nums != list(range(1, len(nums) + 1)):
            problems.append(f"the prompt numbers its pictures {nums}: they have to run 1, 2, 3 without a gap")
        if len(nums) > 3:
            problems.append("more than 3 pictures: the edit model takes three - split it into two steps (assets/image-prompts.md, "
                            "section 6: two people + room first, then the prop into the result); write the two prompts as a list")
        return [got.get(n, f"<image{n}>") for n in nums[:3]], problems

    def frame(self, seg: dict, shot: dict, dest: str, prompt, name: str, what: str):
        if not self.canvas:
            self.notes.append(f"ratio {self.ratio}: this script knows the canvas of 16:9 and 9:16 only - set the size of {dest} by hand")
        if not prompt:
            field = "first_frame_prompt" if name.startswith("first_") else "keyframe_prompt"
            self.notes.append(f"{seg['id']}: {dest} is named in the storyboard but there is no {field} to make it from - write it "
                              f"(assets/agent-prompts/02-storyboard.md; template: assets/image-prompts.md section 6) and run this again")
            return
        steps = prompt if isinstance(prompt, list) else [prompt]
        carried = None
        for k, text in enumerate(steps, 1):
            last = k == len(steps)
            images, problems = self.frame_inputs(text, seg, shot, carried)
            if not images:
                problems.append("the prompt names no Picture: a frame is made by the edit model from the character / prop / room "
                                "pictures - start it with the Keep ... as Picture N sentences of the template")
            out = f"first/candidates/{seg['id']}"
            tag = name if last else f"{name}_step{k}"
            target = dest if last else str(Path(dest).with_name(Path(dest).stem + f"_step{k}" + Path(dest).suffix).as_posix())
            pf = self.prompt_file(name if len(steps) == 1 else f"{name}_step{k}", text)
            self.add("C", what + ("" if len(steps) == 1 else f" - step {k} of {len(steps)}"), target,
                     f"qwen_edit2511_{max(1, min(3, len(images)))}ref.api.json", pf, 3, out, tag, images=images, size=self.canvas,
                     negative=True, problems=problems, needs=[i for i in images if not i.startswith("<")])
            carried = target

    def frames(self):
        ots = []
        for seg in self.raw.get("segments", []):
            shots = seg.get("shots") or [{}]
            if seg.get("first_frame"):
                self.frame(seg, shots[0], seg["first_frame"], seg.get("first_frame_prompt"), f"first_{seg['id']}",
                           f"{seg['id']}: first frame")
            for sh in shots[1:]:
                if sh.get("keyframe"):
                    self.frame(seg, sh, sh["keyframe"], sh.get("keyframe_prompt"), f"key_{seg['id']}_{sh.get('index', '?')}",
                               f"{seg['id']}: keyframe of shot {sh.get('index', '?')}")
            for sh in shots:
                framed = sh is shots[0] and seg.get("first_frame") or sh.get("keyframe")
                for who in re.findall(r"shoulder of \{([A-Za-z0-9_-]+)\}", sh.get("framing", "")):
                    if framed:
                        ots.append((seg["id"], sh.get("index", "?"), who))
        chars = {c["id"]: c for c in self.raw.get("characters", [])}
        for sid, idx, who in ots:
            if who in chars and not (chars[who].get("_back") and Path(chars[who]["_back"]).exists()):
                self.notes.append(f"{sid} shot {idx} is framed over the shoulder of {who}, and it gets a frame picture: a face picture of "
                                  f"the person whose back is to the camera tends to be painted onto the back of the head. Give that "
                                  f"frame {who}'s back view instead (run this again with --back {who}), or no picture of {who} at all")

    def crops(self) -> list[str]:
        out = []
        for it in self.items:
            for need in it["needs"]:
                if need.endswith("_crop.png") and not Path(need).exists() and need not in out:
                    out.append(need)
        return out


def render(plan: Plan, episode: str) -> tuple[str, int, int]:
    titles = {"A": f"A. {plan.t2i['label']} (text to picture): busts, scene masters, props",
              "B1": "B. Qwen-Image-Edit-2511: views made from the chosen bust",
              "B2": "B. Qwen-Image-Edit-2511: views made from the chosen full-body picture",
              "C": "C. Qwen-Image-Edit-2511: first frames and keyframes (after the faces, props and scene crops exist)"}
    todo = sum(i["n"] for i in plan.items if not i["have"])
    done = sum(1 for i in plan.items if i["have"])
    lines = [f"# Still pictures for {plan.raw.get('title', episode)}", "",
             f"Made by plan_stills.py from {episode}. {len(plan.items)} picture(s) in the storyboard: {done} on disk, "
             f"{len(plan.items) - done} to make = **{todo} candidates** to generate.", "",
             "Each command: run it with `--dry-run` added, read the preview, then run it again with `--confirm <batch id>`. "
             "Look at the candidates, copy the one you choose to the file named after `->`, and go on. A bust that is chosen is "
             "frozen: everything else of that person is made from it.", ""]
    crops = plan.crops()
    for phase in ("A", "B1", "B2", "C"):
        part = [i for i in plan.items if i["phase"] == phase]
        if not part:
            continue
        lines += [f"## {titles[phase]}", ""]
        if phase == "C" and crops:
            w, h = plan.canvas or (1344, 768)
            lines += ["Scene crops first (ffmpeg, no GPU): one single-camera view per frame picture, cut from the scene master at the "
                      f"canvas ratio and scaled to {w}x{h}. Choose the window by looking at the master - `crop=width:height:x:y`, "
                      f"width:height = {w * 3 // 2}:{h * 3 // 2} or {w * 5 // 4}:{h * 5 // 4}:", ""]
            for c in crops:
                scene = next((s for s in plan.raw.get("scenes", []) if Path(c).name.startswith(s["id"] + "_")), None)
                master = scene["_master"] if scene else "<scene master>"
                lines.append(f'    ffmpeg -i {master} -vf "crop={w * 3 // 2}:{h * 3 // 2}:X:Y,scale={w}:{h}:flags=lanczos" {c}')
            lines.append("")
        for i in part:
            state = "have it" if i["have"] else f"{i['n']} candidates"
            lines.append(f"- **{i['what']}** -> `{i['dest']}`  ({state})")
            if i["have"]:
                continue
            if i.get("stale"):
                lines.append("  - MAKE AGAIN: the file on disk was made from an earlier version of this prompt")
            for p in i["problems"]:
                lines.append(f"  - CHECK: {p}")
            missing = [n for n in i["needs"] if not Path(n).exists()]
            if missing:
                lines.append(f"  - needs first: {', '.join(missing)}")
            lines += ["", f"      {i['cmd']}", ""]
    if plan.notes:
        lines += ["## Open points", ""] + [f"- {n}" for n in plan.notes] + [""]
    return "\n".join(lines), todo, done


def main():
    _utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__[__doc__.index("Reads the storyboard"):])
    ap.add_argument("episode")
    ap.add_argument("--prompts", default="bible/prompts", help="folder for the prompt files (default bible/prompts)")
    ap.add_argument("--out", default="bible/stills_plan.md", help="the plan (default bible/stills_plan.md)")
    ap.add_argument("--back", nargs="*", default=[], metavar="CHARACTER", help="also plan a back view of these characters")
    ap.add_argument("--side", nargs="*", default=[], metavar="CHARACTER", help="also plan a 90-degree side view of these characters")
    ap.add_argument("--rewrite", action="store_true", help="write prompt files again even when they exist (hand edits are lost)")
    ap.add_argument("--t2i", choices=sorted(T2I), default="qwen21",
                    help="the text-to-picture model for busts, masters and props: qwen21 (default; research licence, not for projects "
                         "that earn money) or zimage (Z-Image-Turbo, Apache-2.0)")
    a = ap.parse_args()
    raw = json.loads(Path(a.episode).read_text(encoding="utf-8"))
    ids = {c["id"] for c in raw.get("characters", [])}
    for who in a.back + a.side:
        if who not in ids:
            sys.exit(f"{who} is not a character of {a.episode} (characters: {', '.join(sorted(ids))})")
    extra: dict[str, set] = {}
    for who in a.back:
        extra.setdefault(who, set()).add("back")
    for who in a.side:
        extra.setdefault(who, set()).add("side")
    script = f"python {quoted(HERE / 'comfy_submit.py')}"
    plan = Plan(raw, Path(a.prompts), a.rewrite, script, a.t2i)
    plan.characters(extra)
    plan.scenes()
    plan.props()
    plan.frames()
    text, todo, done = render(plan, a.episode)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"{len(plan.items)} picture(s) in the storyboard: {done} on disk, {len(plan.items) - done} to make = {todo} candidates to generate")
    for phase, label in (("A", plan.t2i["label"]), ("B1", "Edit-2511, from the bust"), ("B2", "Edit-2511, from the full body"), ("C", "Edit-2511, frames")):
        part = [i for i in plan.items if i["phase"] == phase and not i["have"]]
        if part:
            print(f"  {label}: {len(part)} picture(s), {sum(i['n'] for i in part)} candidates")
    plan.record_file.parent.mkdir(parents=True, exist_ok=True)
    plan.record_file.write_text(json.dumps(plan.record, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"prompt files in {a.prompts}: {len(plan.written)} written"
          + (f", {len(plan.updated)} updated from the storyboard ({', '.join(plan.updated)})" if plan.updated else "")
          + (f", {len(plan.kept)} kept as they were" if plan.kept else ""))
    again = [i["dest"] for i in plan.items if i.get("stale")]
    if again:
        print(f"MAKE AGAIN ({len(again)}): {', '.join(again)} - on disk, but made before the prompt changed; counted above as still to make")
    # a picture that exists needs no command - but one whose prompt quotes an outdated look was made from that look
    checks = [(i["what"], p) for i in plan.items for p in i["problems"] if not i["have"] or "sheet_phrase as it is now" in p]
    for what, p in checks:
        print(f"CHECK {what}: {p}")
    for n in plan.notes:
        print(f"NOTE {n}")
    print(f"plan with every command: {out}")


if __name__ == "__main__":
    from guard import run as _guarded   # a wrong path or a broken JSON file ends in one line, not in a traceback
    _guarded(main)
