#!/usr/bin/env bash
# Make a 4x3 contact sheet (12 evenly spaced frames) per clip for visual QC.
#   ./contact_sheet.sh takes/ep01/s03/*.mp4
set -euo pipefail
for f in "$@"; do
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  fps=$(python3 -c "print(12/float('$dur'))")
  ffmpeg -v error -y -i "$f" -vf "fps=$fps,scale=320:-1,tile=4x3" -frames:v 1 "${f%.*}_sheet.png"
  echo "${f%.*}_sheet.png"
done
