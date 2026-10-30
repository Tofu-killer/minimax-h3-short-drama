"""MiniMax H3 video-generation v2 client (async).

Implements exactly what the official docs expose:
  POST /v2/video_generation            create a video task
  POST /v2/h3_context_ir               prompt enhancement only (returns rewritten prompt)
  GET  /v2/query/video_generation/{id} poll a task
  POST /v2/video_regeneration          768P -> 2K regeneration (see docs/02 §7)

Reference: docs/02-api-reference.md
"""
from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

import httpx

Model = Literal["MiniMax-H3", "MiniMax-H3-Highspeed", "MiniMax-H3-Lite", "MiniMax-H3-Max"]
Resolution = Literal["480P", "768P", "2K"]
Ratio = Literal["adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]
Role = Literal["first_frame", "last_frame", "reference_image", "reference_video", "reference_audio", "base_video"]

TERMINAL = {"succeeded", "failed", "cancelled"}

# Hard limits from the official create-task schema.
LIMITS = {
    "text_chars": 7000,
    "reference_image": 9,
    "reference_video": 3,
    "reference_audio": 3,
    "first_frame": 1,
    "last_frame": 1,
    "duration": (4, 15),
}


class H3Error(RuntimeError):
    def __init__(self, status: int, body: Any):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {json.dumps(body, ensure_ascii=False)[:500]}")


# ---------------------------------------------------------------- content items

def text_item(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("text item must be non-empty")
    if len(text) > LIMITS["text_chars"]:
        raise ValueError(f"text exceeds {LIMITS['text_chars']} chars ({len(text)})")
    return {"type": "text", "text": text}


def _url_or_data_uri(src: str, kind: str) -> str:
    """Accept http(s) URL, mm_file:// id, or a local path (inlined as data URI)."""
    if src.startswith(("http://", "https://", "mm_file://", "data:")):
        return src
    p = Path(src)
    if not p.exists():
        raise FileNotFoundError(src)
    mime = mimetypes.guess_type(p.name)[0] or {
        "image": "image/png", "video": "video/mp4", "audio": "audio/mpeg"}[kind]
    # Official doc requires lowercase format names, e.g. data:image/png;base64,...
    return f"data:{mime.lower()};base64," + base64.b64encode(p.read_bytes()).decode()


def image_item(src: str, role: Optional[Role] = None) -> dict:
    item: dict = {"type": "image_url", "image_url": {"url": _url_or_data_uri(src, "image")}}
    if role:
        item["role"] = role
    return item


def video_item(src: str, role: Role = "reference_video") -> dict:
    return {"type": "video_url", "video_url": {"url": _url_or_data_uri(src, "video")}, "role": role}


def audio_item(src: str, role: Role = "reference_audio") -> dict:
    return {"type": "audio_url", "audio_url": {"url": _url_or_data_uri(src, "audio")}, "role": role}


def validate_content(content: list[dict]) -> None:
    """Enforce the official combination rules before spending money."""
    texts = [c for c in content if c["type"] == "text"]
    if not texts:
        raise ValueError("content must include a non-empty text item")
    roles = [c.get("role") for c in content if c["type"] != "text"]
    counts = {r: roles.count(r) for r in set(roles)}
    for role, cap in (("reference_image", 9), ("reference_video", 3), ("reference_audio", 3),
                      ("first_frame", 1), ("last_frame", 1)):
        if counts.get(role, 0) > cap:
            raise ValueError(f"too many {role}: {counts[role]} > {cap}")
    # untyped image = first_frame
    untyped_images = [c for c in content if c["type"] == "image_url" and not c.get("role")]
    if len(untyped_images) + counts.get("first_frame", 0) > 1:
        raise ValueError("only one first_frame image allowed")
    has_ref = any(r and r.startswith("reference_") for r in roles)
    has_frame = any(r in ("first_frame", "last_frame") for r in roles) or bool(untyped_images)
    if has_ref and has_frame:
        raise ValueError("image-to-video (first/last frame) and reference-to-video are mutually exclusive")
    if counts.get("reference_audio") and not (counts.get("reference_image") or counts.get("reference_video")):
        raise ValueError("reference_audio must be accompanied by at least one image or video reference")
    total_media = sum(1 for c in content if c["type"] != "text")
    if has_ref and total_media > 12:
        raise ValueError("mixed reference input is capped at 12 files")


# ---------------------------------------------------------------- client

@dataclass
class H3Client:
    api_key: str = field(default_factory=lambda: os.environ.get("MINIMAX_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.environ.get("MINIMAX_API_BASE", "https://api.minimax.io"))
    timeout: float = 60.0
    max_retries: int = 5

    def __post_init__(self):
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY is not set")
        self._http = httpx.AsyncClient(
            base_url=self.base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=self.timeout,
        )

    async def aclose(self):
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kw) -> dict:
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            r = await self._http.request(method, path, **kw)
            if r.status_code < 400:
                return r.json()
            body = r.json() if "json" in r.headers.get("content-type", "") else {"raw": r.text}
            # 429 rate limit / 529 overloaded / 5xx: retry with jittered exponential backoff
            if r.status_code in (429, 529) or r.status_code >= 500:
                if attempt < self.max_retries:
                    await asyncio.sleep(delay + random.uniform(0, 1))
                    delay = min(delay * 2, 60)
                    continue
            raise H3Error(r.status_code, body)
        raise RuntimeError("unreachable")

    # -- create -------------------------------------------------------------
    def build_payload(self, *, model: Model, content: list[dict], resolution: Resolution,
                      duration: int, ratio: Ratio = "adaptive", callback_url: str | None = None,
                      extra: dict | None = None) -> dict:
        validate_content(content)
        lo, hi = LIMITS["duration"]
        if model == "MiniMax-H3-Max":
            lo = 5
        if not (lo <= duration <= hi):
            raise ValueError(f"duration {duration} outside {lo}..{hi} for {model}")
        if model == "MiniMax-H3" and resolution not in ("768P", "2K"):
            raise ValueError("MiniMax-H3 supports only 768P / 2K")
        if model != "MiniMax-H3" and resolution == "2K":
            raise ValueError(f"{model} does not support 2K")
        is_t2v = all(c["type"] == "text" for c in content)
        has_frame = any(c.get("role") in ("first_frame", "last_frame") or
                        (c["type"] == "image_url" and not c.get("role")) for c in content)
        if is_t2v and ratio == "adaptive":
            raise ValueError("text-to-video requires an explicit ratio (not adaptive)")
        if has_frame:
            ratio = "adaptive"  # server ignores anything else for image-to-video
        payload: dict = {"model": model, "content": content, "resolution": resolution,
                         "duration": int(duration), "ratio": ratio}
        if callback_url:
            payload["callback_url"] = callback_url
        if extra:
            payload["extra"] = extra
        return payload

    async def create_video(self, **kw) -> str:
        payload = self.build_payload(**kw)
        resp = await self._request("POST", "/v2/video_generation", json=payload)
        return resp["task_id"]

    async def create_context_ir(self, *, content: list[dict], duration: int, ratio: Ratio = "adaptive",
                                callback_url: str | None = None) -> str:
        validate_content(content)
        payload: dict = {"model": "MiniMax-H3", "content": content, "duration": int(duration), "ratio": ratio}
        if callback_url:
            payload["callback_url"] = callback_url
        resp = await self._request("POST", "/v2/h3_context_ir", json=payload)
        return resp["task_id"]

    async def create_regeneration_2k(self, *, original_content: list[dict], base_video_url: str,
                                     duration: int, ratio: Ratio = "adaptive") -> str:
        """Regenerate a 768P result at 2K. Must replay the original content + one base_video item."""
        content = list(original_content) + [video_item(base_video_url, role="base_video")]
        payload = {"model": "MiniMax-H3", "content": content, "resolution": "2K",
                   "duration": int(duration), "ratio": ratio}
        resp = await self._request("POST", "/v2/video_regeneration", json=payload)
        return resp["task_id"]

    # -- query --------------------------------------------------------------
    async def query(self, task_id: str) -> dict:
        resp = await self._request("GET", f"/v2/query/video_generation/{task_id}")
        return resp["task"]

    async def wait(self, task_id: str, *, interval: float = 10.0, timeout: float = 1800.0,
                   on_update=None) -> dict:
        """Poll until terminal. Official recommended interval is 10 s."""
        start = time.monotonic()
        last = None
        while True:
            task = await self.query(task_id)
            if task.get("status") != last and on_update:
                on_update(task)
            last = task.get("status")
            if last in TERMINAL:
                return task
            if time.monotonic() - start > timeout:
                raise TimeoutError(f"task {task_id} still {last} after {timeout}s")
            await asyncio.sleep(interval)

    async def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=300) as dl:
            async with dl.stream("GET", url) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    async for chunk in r.aiter_bytes():
                        f.write(chunk)
        return dest


# ---------------------------------------------------------------- callback helper

def make_callback_app():
    """Minimal callback receiver (FastAPI optional). MiniMax first POSTs {"challenge": ...}
    and expects the same value echoed back within 3 seconds; later POSTs carry the task object."""
    try:
        from fastapi import FastAPI, Request
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("pip install fastapi uvicorn to use the callback receiver") from e

    app = FastAPI()
    app.state.events: list[dict] = []

    @app.post("/callback/minimax")
    async def cb(req: Request):
        body = await req.json()
        if "challenge" in body:
            return {"challenge": body["challenge"]}
        app.state.events.append(body)
        return {"ok": True}

    return app
