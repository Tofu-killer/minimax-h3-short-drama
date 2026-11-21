#!/usr/bin/env python3
"""Download MiniMax's official prompt-writing guides (three-part and reference mode) and the official
h3-prompt-writing SKILL.md, for exact wording when something in this skill is unclear.

    python fetch_official_guides.py [dest_folder]      # default: ../references/official

Source: github.com/MiniMax-AI/MiniMax-H3, skills/h3-prompt-writing (MiniMax H3 Community License -
read-only reference, do not redistribute modified copies). Standard library only.
"""
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _utf8_console() -> None:
    """Agents read this output through a pipe; on Windows a pipe defaults to the system code page, where
    Chinese text raises UnicodeEncodeError. Always write UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_console()

BASE = "https://raw.githubusercontent.com/MiniMax-AI/MiniMax-H3/main/skills/h3-prompt-writing"
FILES = {"SKILL.md": "h3-prompt-writing.SKILL.md", "references/base-en.txt": "base-en.txt", "references/ref-en.txt": "ref-en.txt"}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dest", nargs="?", default=str(Path(__file__).resolve().parent.parent / "references" / "official"),
                    help="folder to save into (default: the skill's references/official)")
    dest = Path(ap.parse_args().dest)
    dest.mkdir(parents=True, exist_ok=True)
    failed = 0
    for remote, local in FILES.items():
        try:
            with urllib.request.urlopen(f"{BASE}/{remote}", timeout=60) as r:
                data = r.read()
            (dest / local).write_bytes(data)
            print(f"saved {dest / local} ({len(data)} bytes)")
        except (urllib.error.URLError, TimeoutError) as e:
            failed += 1
            print(f"could not fetch {remote}: {e}", file=sys.stderr)
    print("MiniMax H3 Community License - read-only reference, do not redistribute modified copies")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
