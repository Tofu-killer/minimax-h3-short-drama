"""Local-ComfyUI flavour of the content items used by prompt_builder.

The hosted API wants data URIs; a local ComfyUI graph just needs the file path
and the role so the agent can wire it into LoadImage / LoadAudio nodes in the
right order.  Keep the shape close to the API so the two builders stay in sync.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

TEXT_LIMIT = 7000


def text_item(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("text item must be non-empty")
    if len(text) > TEXT_LIMIT:
        raise ValueError(f"text exceeds {TEXT_LIMIT} chars ({len(text)})")
    return {"type": "text", "text": text}


def image_item(src: str, role: Optional[str] = None) -> dict:
    p = Path(src)
    if not p.exists():
        raise FileNotFoundError(f"reference image missing: {src}")
    return {"type": "image", "path": str(p), "role": role}


def audio_item(src: str, role: str = "reference_audio") -> dict:
    p = Path(src)
    if not p.exists():
        raise FileNotFoundError(f"reference audio missing: {src}")
    return {"type": "audio", "path": str(p), "role": role}
