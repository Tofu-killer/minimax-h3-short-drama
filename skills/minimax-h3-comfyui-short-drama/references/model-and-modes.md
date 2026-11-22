# MiniMax H3 模型与模式速查

| 项 | 值 |
|----|----|
| 架构 | 33B 全模态 DiT，视频 + 立体声音频联合去噪；文本/视觉编码器 Qwen3-VL-32B；视频 VAE ≈5B |
| 输出 | 4–15 s，24 fps，帧数网格 `17k+5`（124 / 243 / 362 ≈ 5 / 10 / 15 s）；768P 或 2K；32 kHz 立体声；11 种对白语言 |
| 开源变体 | `FL2VA`（0/1/2 张关键帧：T2VA / I2VA / L2VA / FL2VA）与 `Ref2VA`（≤9 图 + ≤3 视频 + ≤3 音频，≤12 件）。两者同尺寸。FL2VA 原生画质更高；Ref2VA 参考能力强、基础画质略低（lihaoyun6 Ref-Patch 是另一条路：让 FL2VA 权重获得参考能力；已经有 Ref2VA int8 时不必装） |
| 权重性质 | **CFG 蒸馏**：CFG 固定 1.0，没有负向分支 → 否定句会被渲染 |
| 默认采样 | 20 步（基线最高质量），Euler/`simple` 或 `res_multistep`，SigmaShift 视频 12 / 音频 3 |
| 托管专属 | Context-IR 提示词改写、Regenerate-2K、H3 Max / Max Director / Max Turbo（fal 后训练，闭源） |
| 官方 API | `POST /v2/video_generation`，`GET /v2/query/video_generation/{id}`，`POST /v2/h3_context_ir`；2K $0.13/s、768P $0.08/s |

## 24 GB 单卡的标准文件组合（Comfy-Org 重打包，HuggingFace）

| 组件 | 文件 | 大小 |
|------|------|------|
| DiT | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` / `minimax_h3_ref2va_pruned_int8_convrot.safetensors`（pruned = AdaLN 剪枝，只能在 ComfyUI 用） | 19.5 GiB |
| DiT（不剪枝，画质更稳） | `minimax_h3_{fl2va,ref2va}_int8_convrot.safetensors` | 31.7 GiB（靠 offload，慢） |
| 文本编码器 | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`（type=`minimax`） | 14.6 GiB |
| VAE | `minimax_h3_video_vae_int8_convrot.safetensors`（官方模板默认；另有 `…_fp16`）+ `minimax_h3_audio_vae_fp32.safetensors`（HF `Comfy-Org/MiniMax-H3` 的 `vae/`） | 4.9 GiB + 0.6 GiB（此前记录的数，未重新核对是哪一档的大小） |
| 加速 LoRA | HF `lightx2v/Minimax-h3-Turbo`（2026-11-21 核对文件列表）：768p 训练版文件名带 `_768p_`——Ref2V `minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16`、FL2V `minimax_h3_fl2v_turbo_8step_v1.2_768p_comfyui_bf16`（v1.1 是上一版）；不带 `768p` 的是 544p 档——Ref2V 只有 4 步的 `…ref2v_turbo_4step_v0.1_comfyui_bf16`，FL2V 有 `…fl2v_turbo_8step_v1.0_comfyui_bf16` 与 `…fl2v_turbo_4step_v0.1`。shift：模型默认 12/3；作者公布的例外只有 FL2V **v1.0** 的 768p 版 = 6/3（FL2V 8 步 v1.2 是 12/3），各版本见 `comfyui-nodes.md` §1 | 1.8–2.0 GiB |

来源：MiniMax-AI/awesome-minimax-h3-integration（官方维护的生态索引，2026-11）。

**许可（条款摘录，不是法律意见；原文是 HF `MiniMaxAI/MiniMax-H3` 的 `LICENSE`，2026-11-21 读）**：权重按 MiniMax H3 Community License 发布。① 适用地区是全球但**排除美国、欧盟、英国、韩国**（澳大利亚、中国大陆等在适用范围内）；条款 V.4 写的是不得在适用地区以外使用、分发、展示模型**及其输出**。② 社区许可一般允许商用：商业产品和服务年收入超过 2000 万美元要另取书面授权，使用 H3 的商业产品要在界面上显示「MiniMax H3」。③ 鼓励给生成的文件加 AI 生成标识。④ 要在那四个被排除的地区使用，需要另购商用许可（Comfy 的许可页写明它是官方转售方，Professional 档每月 5000 美元起）。片子打算发到哪里、给谁用，开工前和用户确认一次；拿不准就让用户自己读原文。

## 分辨率格点（容易踩的坑）

- 宽高必须是 **32 的倍数**，否则核心 `pad_to_patch_size` 做 circular padding，底 / 右 16 px 出条纹：1280×**704**（不是 720）、576×**1024**（不是 720×1280）。
- **1344×768 其实是 7:4，不是 16:9**。真 16:9 且 32 对齐的格点只有 1024×576 / **1536×864** / 2048×1152。交付 1080p 时：默认仍在 1344×768 生成，由 `mix_episode.py` 在装配时裁切（上下各约 6 px）并缩放到 1920×1080——不要在 ComfyUI 里先把它拉伸成 1920×1080（约 1.6% 横向变形）。画面里有不能裁的东西才改用真 16:9 的 1536×864。
- 内置分辨率选择器按 mebipixel（1024²）算，官方「0.98 MP」= 1.03 真 MP；建分辨率表按真 MP（×10⁶）。
- 单镜帧数取 **124–362**（5–15 s）：< 124 帧跑出训练分布（动作做不完、音频发虚、中途变形）。

## 模式选择（短剧）

| 需求 | 模式 | 原因 |
|------|------|------|
| 多角色对手戏、需要脸/服装/场景/道具全部锁定 | Ref2VA 六段式 | 唯一能同时带 9 图 + 音色参考的模式 |
| 单角色钩子镜头、已有高质量首帧 | I2VA 三段式（FL2VA 权重） | 画质最高，首帧即定妆 |
| 段与段衔接 | 默认硬切，状态靠文字和同一组参考图带过去；例外：上一段尾帧作本段 `first_frame`（`ref2va`，同时带角色参考；提交脚本会把它钉在第 0 帧，画面从这一帧接着走）；单镜 > 15 s 才用 Motion-Context 类续接节点 | 见 `continuity-long-video.md` |
| 纯文字试风格 | T2VA | 便宜快速，只做风格探索 |

## 已知弱项（分镜阶段绕开）

动作偏慢；大幅运镜、特效镜头弱；精确文字不可靠；远景正脸糊；跨段空间连续性一般；Ref2VA 多参考时「油腻感」略重。
