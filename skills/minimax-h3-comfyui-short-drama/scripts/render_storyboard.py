#!/usr/bin/env python3
"""Render an episode JSON as a human-readable shot table (Markdown) for director review.

    python3 render_storyboard.py episodes/ep01.json --out ep01_storyboard.md

One table per segment: shot, time range, framing/lens, camera, action, performance,
lighting, dialogue (speaker + text + chars/s), sound cue; plus segment header with
mode, effective frames (17k+5), references bound, continuity and end_state.
Review this BEFORE spending GPU time.
"""
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "h3lib"))
from storyboard import load_episode  # noqa: E402


def frames_for(sec: float) -> int:
    f = 24 * sec
    k = max(0, -(-(int(round(f)) - 5) // 17))
    return 17 * k + 5


NAMES: dict[str, str] = {}


def esc(t: str) -> str:
    t = re.sub(r"\{([a-z0-9_]+)\}", lambda m: NAMES.get(m.group(1), m.group(0)), t or "")
    return t.replace("|", "\\|").replace("\n", " ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ep = load_episode(a.episode)
    NAMES.update({c.id: c.name for c in ep.characters})
    NAMES.update({x.id: x.name for x in ep.scenes})
    NAMES.update({x.id: x.name for x in ep.props})
    out = [f"# {ep.title}", "", f"画幅 {ep.ratio} · 风格：{ep.style}", "",
           f"共 {len(ep.segments)} 段，请求总时长 {sum(s.duration for s in ep.segments)} s，"
           f"有效总时长 {sum(frames_for(s.duration) for s in ep.segments) / 24:.2f} s（17k+5 帧网格）", ""]
    if ep.synopsis:
        out += [f"> {ep.synopsis}", ""]
    for seg in ep.segments:
        fr = frames_for(seg.duration)
        refs = [ep.char(c).name for c in seg.character_ids] + [ep.scene(seg.scene_id).name] + \
               [next(p.name for p in ep.props if p.id == pid) for pid in seg.prop_ids]
        chars = sum(len(d.text) for sh in seg.shots for d in sh.dialogue)
        out += [f"## {seg.id} · {seg.mode} · {seg.duration} s（{fr} 帧 = {fr / 24:.3f} s）{' · ' + seg.hook_type if seg.hook_type else ''}", "",
                f"- 参考：{'、'.join(refs)}" + (f"；首帧：{Path(seg.first_frame).name}" if seg.first_frame else ""),
                f"- 台词 {chars} 字 / 上限 {int((seg.duration - 2) * 4.5)} 字",
                f"- 承接：{esc(seg.continuity) or '（首段）'}",
                f"- 结束状态：{esc(seg.end_state)}", "",
                "| 镜 | 时间 | 景别 / 镜头 | 运镜 | 动作 | 表演 | 光线 | 台词 | 声音 |",
                "|---|---|---|---|---|---|---|---|---|"]
        bounds = [sh.start for sh in seg.shots] + [fr / 24]
        for i, sh in enumerate(seg.shots):
            span = bounds[i + 1] - bounds[i]
            lines = []
            for d in sh.dialogue:
                who = "旁白" if d.speaker == "narrator" else ep.char(d.speaker).name
                rate = len(d.text) / span if span else 0
                lines.append(f"{who}{'（画外）' if d.offscreen else ''}：{d.text}（{rate:.1f} 字/s）")
            out.append("| " + " | ".join([
                str(sh.index), f"{bounds[i]:.1f}–{bounds[i + 1]:.1f}",
                esc(sh.framing + (f"，{sh.lens}" if getattr(sh, "lens", "") else "")),
                esc(sh.camera), esc(sh.action), esc(getattr(sh, "performance", "")),
                esc(getattr(sh, "lighting", "")), esc("<br>".join(lines)),
                esc(getattr(sh, "sound_cue", ""))]) + " |")
        out += ["", f"环境声：{esc(seg.soundscape)}　配乐：{esc(seg.music)}", ""]
    Path(a.out).write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
