#!/usr/bin/env python3
"""Generate every segment of an episode with MiniMax H3.

  python run_episode.py examples/episode01.json --dry-run            # just write prompts + payloads
  python run_episode.py examples/episode01.json --mode draft -c 4    # 768P, 2 candidates per segment
  python run_episode.py examples/episode01.json --mode final         # 2K directly
  python run_episode.py examples/episode01.json --mode upscale --pick picks.json   # 768P -> 2K regeneration
  python run_episode.py examples/episode01.json --use-ir             # route prompts through H3-Context-IR first

Output tree:  out/<episode>/{prompts,payloads,clips,ir}/ + manifest.json (idempotent by segment+prompt hash)
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

from h3_client import H3Client, text_item
from prompt_builder import build
from storyboard import load_episode, validate_episode

PRICE_PER_SEC = {"2K": 0.13, "768P": 0.08}
REGEN_PER_SEC = 0.05


def slug(s: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in s)[:40]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--out", default="out")
    ap.add_argument("--mode", choices=["draft", "final", "upscale"], default="draft")
    ap.add_argument("--candidates", type=int, default=2, help="takes per segment in draft mode")
    ap.add_argument("-c", "--concurrency", type=int, default=4)
    ap.add_argument("--model", default="MiniMax-H3")
    ap.add_argument("--use-ir", action="store_true", help="rewrite each prompt with H3-Context-IR first")
    ap.add_argument("--pick", help="JSON {segment_id: clip_url} of chosen 768P takes (upscale mode)")
    ap.add_argument("--callback-url")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*", help="segment ids to (re)run")
    args = ap.parse_args()

    ep = load_episode(args.episode)
    problems = validate_episode(ep)
    for p in problems:
        print("  ! " + p, file=sys.stderr)
    if problems and not args.dry_run:
        print("storyboard has problems; fix them or run with --dry-run", file=sys.stderr)
        sys.exit(2)

    root = Path(args.out) / slug(ep.title)
    for d in ("prompts", "payloads", "clips", "ir"):
        (root / d).mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    resolution = "2K" if args.mode == "final" else "768P"
    takes = 1 if args.mode != "draft" else args.candidates
    est = 0.0
    jobs = []
    for seg in ep.segments:
        if args.only and seg.id not in args.only:
            continue
        built = build(ep, seg)
        (root / "prompts" / f"{seg.id}.txt").write_text(built.text, encoding="utf-8")
        key = hashlib.sha1((seg.id + built.text + resolution).encode()).hexdigest()[:12]
        est += seg.duration * (REGEN_PER_SEC if args.mode == "upscale" else PRICE_PER_SEC[resolution]) * takes
        for t in range(takes):
            tag = f"{seg.id}_{resolution}_t{t + 1}"
            if manifest.get(tag, {}).get("status") == "succeeded" and manifest[tag].get("key") == key:
                continue
            jobs.append((seg, built, tag, key, t))

    print(f"{ep.title}: {len(ep.segments)} segments, {ep.total_duration()} s total, "
          f"{len(jobs)} tasks to run at {resolution}, est. ${est:.2f} (+IR ≈ $0.02/segment)")

    if args.dry_run:
        for seg, built, tag, key, _ in jobs:
            payload = H3Client.__new__(H3Client)  # payload building needs no key
            payload.api_key = "dry"
            pl = H3Client.build_payload(payload, model=args.model, content=built.content,
                                        resolution=resolution, duration=seg.duration, ratio=ep.ratio)
            # strip base64 for readability
            pl_dump = json.loads(json.dumps(pl))
            for c in pl_dump["content"]:
                for k in ("image_url", "video_url", "audio_url"):
                    if k in c and c[k]["url"].startswith("data:"):
                        c[k]["url"] = c[k]["url"][:40] + "…(base64)"
            (root / "payloads" / f"{tag}.json").write_text(json.dumps(pl_dump, ensure_ascii=False, indent=2),
                                                           encoding="utf-8")
        print(f"dry-run complete → {root}")
        return

    asyncio.run(run_jobs(args, ep, root, manifest, manifest_path, jobs, resolution))


async def run_jobs(args, ep, root, manifest, manifest_path, jobs, resolution):
    client = H3Client()
    sem = asyncio.Semaphore(args.concurrency)
    picks = json.loads(Path(args.pick).read_text()) if args.pick else {}

    def save():
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    async def one(seg, built, tag, key, take):
        async with sem:
            content = built.content
            try:
                if args.use_ir:
                    ir_id = await client.create_context_ir(content=content, duration=seg.duration, ratio=ep.ratio)
                    ir = await client.wait(ir_id)
                    if ir["status"] == "succeeded":
                        rewritten = ir["content"]["prompt"]
                        (root / "ir" / f"{seg.id}.txt").write_text(rewritten, encoding="utf-8")
                        content = [text_item(rewritten)] + [c for c in content if c["type"] != "text"]
                if args.mode == "upscale":
                    base = picks.get(seg.id)
                    if not base:
                        raise RuntimeError(f"no picked clip for {seg.id}")
                    task_id = await client.create_regeneration_2k(original_content=content, base_video_url=base,
                                                                  duration=seg.duration, ratio=ep.ratio)
                else:
                    task_id = await client.create_video(model=args.model, content=content, resolution=resolution,
                                                        duration=seg.duration, ratio=ep.ratio,
                                                        callback_url=args.callback_url)
                manifest[tag] = {"task_id": task_id, "status": "queued", "key": key}
                save()
                task = await client.wait(task_id, on_update=lambda t: print(f"  {tag}: {t['status']}"))
                manifest[tag].update(status=task["status"], usage=task.get("usage"), error=task.get("error"))
                if task["status"] == "succeeded":
                    url = task["content"]["url"]
                    dest = root / "clips" / f"{tag}.mp4"
                    await client.download(url, dest)
                    manifest[tag].update(url=url, file=str(dest))
                    print(f"  ✓ {tag} → {dest}")
                else:
                    print(f"  ✗ {tag}: {task.get('error')}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                manifest[tag] = {"status": "error", "key": key, "error": str(e)}
                print(f"  ✗ {tag}: {e}", file=sys.stderr)
            finally:
                save()

    try:
        await asyncio.gather(*(one(*j) for j in jobs))
    finally:
        await client.aclose()
    ok = sum(1 for v in manifest.values() if v.get("status") == "succeeded")
    print(f"done: {ok}/{len(manifest)} succeeded. manifest → {manifest_path}")


if __name__ == "__main__":
    main()
