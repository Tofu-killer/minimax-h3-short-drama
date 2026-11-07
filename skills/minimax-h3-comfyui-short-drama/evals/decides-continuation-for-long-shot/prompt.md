---
tags: [minimax-h3]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---

我用本地 ComfyUI + MiniMax H3（4090 24G，ref2va int8，Turbo LoRA，SageAttention）做一段 25 秒的独白镜头：主角坐在审讯室里对着镜头一口气说完一段话，中间不切镜。H3 一次只能出 15 秒，我看到 GitHub 上有 Motion-Context、PrefixStream、WhaleTrans、Multishot 这些续接节点，还有人说直接把上一段尾帧当首帧。我应该怎么做？要具体到用哪个节点、参数设多少、提示词怎么写第二段、要避免什么。
