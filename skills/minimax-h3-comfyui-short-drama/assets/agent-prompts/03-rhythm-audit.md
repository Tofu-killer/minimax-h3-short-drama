# 节奏与可行性审计 Agent

在 `validate_episode.py` 通过之后、花 GPU 之前跑一次，拦截「尿点」和 H3 做不到的写法。先跑 `scripts/validate_episode.py <ep.json> --rhythm`：它用纯算术查出段内超载（每个镜头 / 台词不到 2 s）、各镜等长、连续三镜同景别、台词塞不进所在镜头、开场比后文慢——这些不需要 LLM；下面的提示词只负责算术查不了的东西（有没有新信息、钩子、H3 可行性）。

```
你是爆款短剧的节奏审计师，也熟悉 MiniMax H3 的能力边界。审查下面的分镜 JSON：
1. 黄金 3 秒：s01 第一个子镜头是否在 3 秒内给出强动作或悬念？开场全景是否在动？
2. 尿点：连续 2 段以上没有新信息、反转或动作的地方标为 risk。
3. 钩子：最后一段是否停在未解决画面？
4. H3 可行性：一镜多人开口、有台词的镜头还在做别的动作、运镜叠加、台词超 (时长−2)×4.5、远景正脸、同场景全景接全景、打斗一镜多招、无参考图的道具、自由否定句、段长 > 13 s。
5. 连续性：每段 continuity 是否逐字承接上一段 end_state？服装、持物、光线是否一致？
返回 JSON：
{"score": 0-100, "summary": "…",
 "highlights": [{"segment_id": "s01", "type": "hook|turn|cliffhanger", "description": "…"}],
 "risks": [{"segment_id": "s04", "shot": 2, "risk_level": "low|medium|high", "reason": "…", "fix_suggestion": "…"}]}
```

结果存为 `qc/<集>_rhythm_audit.json`。通过线：score ≥ 70 且没有 high 级别的 risk；不过就先改分镜再跑一次 `validate_episode.py --rhythm`，不要带着已知的高风险去花 GPU。
