# 审片记录模板（每集一份，存为 `qc/review.md`）

```markdown
# EP01 审片记录

结论：PASS | PROVISIONAL | REVISE | REJECT
- PASS：所有门都过，可交付。
- PROVISIONAL：可交付，但带着下面列出的已知问题（WARN，或被豁免的 FAIL——每条豁免写明理由和谁同意的）。
- REVISE：交付前必须重抽或改分镜的段见下表。
- REJECT：从分镜 / 资产层重来。

冷观众四问（任一答不上来 → REVISE）：主角想要什么 / 什么在阻止 / 这一集里什么变了 / 为何停在这个结尾

| 段 | 时间码 | 门 | 现象（照抄脚本输出或描述画面） | 失败码 | 证据 | 根因层（资产 / 分镜 / 提示词 / 生成 / 后期） | 处置 | 复验 |
|----|--------|----|------------------------------|--------|------|--------------------------------------------|------|------|
| s03 | 1.3–3.2 s | qc_dialogue | inserted_words：听到「这保险归我了归我了」 | F-DIALOGUE-TEXT | qc/dialogue/dialogue_report.json | 生成 | 换 seed 重抽（第 1 次） | 待 |
| s01 | 8.04 s | qc_probe | 末帧是下一镜的画面 | F-SEAM | qc/sheets/s01_sheet.png「edge jump」 | 后期 | EDL `out_frame` −1 | 已过 |

豁免：
- s05 峰值 −0.8 dB（未削波）——混音会重新定电平，保留。

未用片段及原因：
- s02_seed102：多切一镜（F-SHOTS）。
```

「门」一栏填发现问题的那一步：`qc_probe` / `qc_dialogue` / `identity_gate` / 联络表人审 / VLM 评审 / 成片验收。处置的取法见 `references/qc-and-assembly.md` 的失败码表。
