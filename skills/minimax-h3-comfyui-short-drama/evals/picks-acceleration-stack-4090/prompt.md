---
tags: [minimax-h3]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---

RTX 4090 24G，Windows 11，ComfyUI 0.37.2，已装 KJNodes 和 sageattention，模型是 minimax_h3_ref2va_pruned_int8_convrot + qwen3vl nvfp4，LoRA 只有 minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16。现在 1344x768 跑 10 秒要 9 分多钟，而且画面有横向拖影。工作流里开着 comfy kitchen attention、BlockSparseAttention 和 MiniMaxLowVRAMAttention。我想要一个抽卡用的草稿档和一个出成片的精修档配置，告诉我具体改哪些节点和参数，要下载什么文件（我在澳洲只能用 HuggingFace）。
