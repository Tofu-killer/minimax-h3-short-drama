#!/usr/bin/env bash
# Download MiniMax's official prompt-writing guides (base + reference mode) and
# the official h3-prompt-writing SKILL.md next to this skill for exact wording.
set -euo pipefail
dest="${1:-$(dirname "$0")/../references/official}"
mkdir -p "$dest"
base=https://raw.githubusercontent.com/MiniMax-AI/MiniMax-H3/main/skills/h3-prompt-writing
curl -fsSL "$base/SKILL.md" -o "$dest/h3-prompt-writing.SKILL.md"
curl -fsSL "$base/references/base-en.txt" -o "$dest/base-en.txt"
curl -fsSL "$base/references/ref-en.txt" -o "$dest/ref-en.txt"
echo "saved to $dest (MiniMax H3 Community License — read-only reference, do not redistribute modified)"
