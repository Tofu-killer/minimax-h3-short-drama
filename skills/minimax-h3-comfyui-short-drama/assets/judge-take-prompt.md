# 抽卡择优：本地 VLM 审片提示词（Qwen3-VL / Ollama）

先过脚本门（`qc_probe.py`、`qc_dialogue.py`、`identity_gate.py`），VLM 只看脚本看不了的东西。一份大而全的评分表会让模型把「表情不够到位」也算成错，所以拆成三张小表，各有通过线；三张都写明**不查主观项、不确定默认通过**。

输入（每张表都给）：
1. `scripts/contact_sheet.py` 出的联络表（帧下印着秒数与 `before cut / after cut` 标签）；
2. 角色参考图（`face.png` + 正面全身）、本段用到的道具图；
3. **剧本原句**：本段分镜里各镜的 `action` 与台词原文、计划镜头数——给原句，不给扩写后的提示词（扩写里的修饰会被当成必须兑现的事实）。

通过线与「critical」口径转述自 DramaClaw 的审片提示词与 ATAS 的 film review（见 `docs/14-ai-video-workflows/02`），**没有在本地 VLM + H3 素材上标定过**：先拿 10 个已知好坏的 take 试一遍再信它。

## A. 事实（通过：score ≥ 6 且没有 critical）

```
You are checking one take of a short-drama segment against its script. You are given a time-stamped contact sheet, the reference images, and the script lines for this segment.
Check ONLY facts that are directly visible: the number of people, each person's apparent gender and age band, the core action of each shot, whether each key prop appears and matches its reference image, who is on the left and who is on the right, the type of place, and the time of day / main light direction.
Do NOT judge acting quality, whether an expression is strong enough, beauty, or composition. When you are not sure, treat the item as correct.
Mark an issue "critical" only when it is clearly visible, you are highly confident, and it contradicts an explicit statement in the script.
Return strict JSON only:
{"score": <0-10>, "issues": [{"what": "<one sentence>", "frame": "<timestamp on the sheet>", "severity": "critical" | "minor"}],
 "suggested_action": "none" | "regenerate" | "edit_prompt" | "edit_storyboard"}
```

## B. 身份（通过：face ≥ 7 且 clothing ≥ 7）

```
Compare every person in the contact sheet with the character reference images.
face = facial structure + hairstyle + skin tone. clothing = garment type + colours + accessories.
Score each 0-10 for the WORST frame in which that person's face (or outfit) is clearly visible. Skip frames where the face is turned away, tiny or blurred - those do not count against the take.
Do NOT judge expression or pose. When you are not sure, score 7.
Return strict JSON only:
{"people": [{"character": "<id>", "face": <0-10>, "clothing": <0-10>, "worst_frame": "<timestamp>", "note": "<what differs, one sentence>"}],
 "extra_or_missing": "<people who should not be there, or who are missing; empty string if none>",
 "suggested_action": "none" | "regenerate" | "edit_prompt"}
```

## C. 画面（通过：score ≥ 6）

```
Look for generation defects only: extra or fused limbs and fingers, a face that collapses or melts, objects passing through each other, garbled or unintended on-screen text, watermarks, burned-in subtitles, frames that are black or too blurred to read.
Do NOT judge style, lighting taste or composition. When you are not sure, treat the frame as clean.
Return strict JSON only:
{"score": <0-10>, "defects": [{"what": "<one sentence>", "frame": "<timestamp>"}],
 "suggested_action": "none" | "regenerate" | "crop_or_trim"}
```

## 排序与记录

先淘汰任何一张表不过的 take；剩下的按 身份 → 事实 → 画面 排，分数相同看 `qc_dialogue.py` 的相似度，再同就取能量 / 表演更强的那条（这一步由人定）。结果写 `qc/scorecard.csv`（segment, seed, facts, face, clothing, frame, dialogue_similarity, verdict, suggested_action, chosen），评估绑定视频文件哈希。`suggested_action` 只是建议：是否重抽按 `references/qc-and-assembly.md` 的处置分流定。
