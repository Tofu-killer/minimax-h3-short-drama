#!/usr/bin/env python3
"""Asset catalog: turn a folder of item / character / scene images into a JSON catalog,
and check that every storyboard segment binds the props it talks about.

  python catalog.py build  <folder-of-item-images> --kind prop --out props.json
  python validate_episode.py episodes/ep01.json --catalog props.json   # runs check() below

Rarity (三角洲行动 loot tiers) is parsed from the folder name or file name:
  红/red, 黄/金/gold, 紫/purple, 蓝/blue, 绿/green, 白/white.
The rarity is NOT rendered by H3; it is stored so the editing stage can overlay the game-style
coloured frame deterministically (same rule as subtitles: exact UI goes in post).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RARITY = {
    "red": ["红", "red", "legend"], "gold": ["黄", "金", "gold", "yellow"], "purple": ["紫", "purple", "epic"],
    "blue": ["蓝", "blue", "rare"], "green": ["绿", "green", "uncommon"], "white": ["白", "white", "common"],
}
IMG = {".png", ".jpg", ".jpeg", ".webp"}


def rarity_of(text: str) -> str | None:
    t = text.lower()
    for tier, keys in RARITY.items():
        if any(k in t for k in keys):
            return tier
    return None


def slug(s: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", s).strip("_")
    return s[:48] or "item"


def build(root: Path, kind: str) -> list[dict]:
    items = []
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() not in IMG:
            continue
        rel = p.relative_to(root)
        name = p.stem
        rar = rarity_of(str(rel.parent)) or rarity_of(name)
        items.append({
            "id": f"{kind}_{slug(name)}",
            "kind": kind,
            "name": name,
            "rarity": rar,
            "reference_images": [str(p)],
            "aliases": [],
        })
    # de-dup ids
    seen: dict[str, int] = {}
    for it in items:
        if it["id"] in seen:
            seen[it["id"]] += 1
            it["id"] += f"_{seen[it['id']]}"
        else:
            seen[it["id"]] = 0
    return items


def check(episode_path: Path, catalog_path: Path) -> list[str]:
    """Problems: a segment's action/dialogue mentions a catalog item but does not bind it,
    or a bound prop has no reference image."""
    sys.path.insert(0, str(Path(__file__).parent))
    from storyboard import load_episode
    ep = load_episode(episode_path)
    cat = {c["id"]: c for c in json.loads(catalog_path.read_text(encoding="utf-8"))}
    names = {c["id"]: [c["name"], *c.get("aliases", [])] for c in cat.values()}
    problems = []
    for seg in ep.segments:
        text = " ".join([sh.action for sh in seg.shots] + [d.text for sh in seg.shots for d in sh.dialogue])
        bound = set(seg.prop_ids)
        # a catalog item also counts as bound when a bound prop uses the same image file or the same name
        bound_files = {Path(f).name for pid in seg.prop_ids for x in ep.props if x.id == pid for f in x.reference_images}
        bound_names = {x.name for pid in seg.prop_ids for x in ep.props if x.id == pid}
        for pid, ns in names.items():
            item = cat[pid]
            if Path(str(item.get("path", item.get("file", "")))).name in bound_files or any(n in bound_names for n in ns if n):
                continue
            if any(n and n in text for n in ns) and pid not in bound:
                problems.append(f"segment {seg.id}: mentions catalog item {pid!r} ({ns[0]}) but prop_ids does not bind it")
        for pid in seg.prop_ids:
            p = next((x for x in ep.props if x.id == pid), None)
            if p is None:
                continue
            if not p.reference_images:
                problems.append(f"segment {seg.id}: prop {pid!r} has no reference image; H3 will invent the item")
        generic = re.findall(r"(红色|黄色|紫色|蓝色|绿色|白色)(?:的)?(物品|东西|装备|道具|item|object)", text)
        if generic and not seg.prop_ids:
            problems.append(f"segment {seg.id}: generic item wording {generic[0]} without a bound prop -> model will hallucinate")
    return problems


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("folder"); b.add_argument("--kind", default="prop"); b.add_argument("--out", required=True)
    c = sub.add_parser("check"); c.add_argument("episode"); c.add_argument("--catalog", required=True)
    a = ap.parse_args()
    if a.cmd == "build":
        items = build(Path(a.folder), a.kind)
        Path(a.out).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        tiers = {}
        for it in items:
            tiers[it["rarity"]] = tiers.get(it["rarity"], 0) + 1
        print(f"{len(items)} items -> {a.out}; rarity counts: {tiers}")
    else:
        probs = check(Path(a.episode), Path(a.catalog))
        for p in probs:
            print("  ! " + p)
        print("OK" if not probs else f"{len(probs)} problem(s)")
        sys.exit(1 if probs else 0)


if __name__ == "__main__":
    main()
