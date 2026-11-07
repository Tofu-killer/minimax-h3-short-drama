# 抽卡择优：本地 VLM 评分提示词（Qwen3-VL / Ollama）

输入：候选片段的 5 帧联络表（`scripts/contact_sheet.sh` 可改 `tile=5x1`）、角色设定板、本段提示词中的 `<d>` 台词、ASR 转写（可选 faster-whisper）。

```
You are grading one candidate take of a MiniMax H3 short-drama segment.
Inputs: (1) a contact sheet of 5 evenly spaced frames, (2) the character sheet(s), (3) the expected dialogue lines, (4) the ASR transcript of the take.
Score each criterion 0-5 and return strict JSON only:
{
 "identity": <0-5, face/hair/outfit match to the character sheets across all 5 frames; 0 if any frame shows a different person or outfit>,
 "count": <0-5, exactly the expected number of characters, no extra people/limbs>,
 "props": <0-5, every expected prop present and matching its sheet; invented items = 0>,
 "continuity": <0-5, positions/lighting consistent across frames, no teleport>,
 "dialogue": <0-5, fraction of expected lines heard in the ASR, right language, no repeats>,
 "sharpness": <0-5, relative to the other takes of this segment>,
 "freeze_or_black": <true|false>,
 "hard_fail": <true|false, true if identity<=1 or count<=1 or props<=1 or freeze_or_black>,
 "notes": "<one sentence>"
}
```

排序：先淘汰 `hard_fail`，再按 identity → dialogue → continuity → sharpness 排；分数相同取能量 / 表演更强的那条。结果写入 `qc/scorecard.csv`（segment, seed, identity, count, props, continuity, dialogue, sharpness, hard_fail, chosen）。
