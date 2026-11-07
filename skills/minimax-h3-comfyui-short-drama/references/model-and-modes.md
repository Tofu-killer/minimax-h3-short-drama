# MiniMax H3 模型与模式速查

| 项 | 值 |
|----|----|
| 架构 | 33B 全模态 DiT，视频 + 立体声音频联合去噪；文本/视觉编码器 Qwen3-VL-32B；视频 VAE ≈5B |
| 输出 | 4–15 s，24 fps，帧数网格 `17k+5`（124 / 243 / 362 ≈ 5 / 10 / 15 s）；768P 或 2K；32 kHz 立体声；11 种对白语言 |
| 开源变体 | `FL2VA`（0/1/2 张关键帧：T2VA / I2VA / L2VA / FL2VA）与 `Ref2VA`（≤9 图 + ≤3 视频 + ≤3 音频，≤12 件）。两者同尺寸。FL2VA 原生画质更高；Ref2VA 参考能力强、基础画质略低（lihaoyun6 Ref-Patch 可部分弥补） |
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
| VAE | 官方视频 VAE + 音频 VAE（fp8mix 对或 fp16/fp32） | 4.9 GiB + 0.6 GiB |
| 加速 LoRA | lightx2v `minimax_h3_{fl2v,ref2v}_turbo_{4,8}step_v1.x_768p_comfyui_bf16.safetensors`（带 `768p` 后缀的才是 1344×768 训练版；无后缀是 544p 版。SigmaShift：FL2V 768p 用 6/3，Ref2V 与 544p 版用 12/3） | 1.8–2.0 GiB |

来源：MiniMax-AI/awesome-minimax-h3-integration（官方维护的生态索引，2026-11）。

## 模式选择（短剧）

| 需求 | 模式 | 原因 |
|------|------|------|
| 多角色对手戏、需要脸/服装/场景/道具全部锁定 | Ref2VA 六段式 | 唯一能同时带 9 图 + 音色参考的模式 |
| 单角色钩子镜头、已有高质量首帧 | I2VA 三段式（FL2VA 权重） | 画质最高，首帧即定妆 |
| 段与段衔接 | FL2VA（上一段尾帧 = 本段首帧）或 Motion-Context 类续接节点 | 见 `continuity-long-video.md` |
| 纯文字试风格 | T2VA | 便宜快速，只做风格探索 |

## 已知弱项（分镜阶段绕开）

动作偏慢；大幅运镜、特效镜头弱；精确文字不可靠；远景正脸糊；跨段空间连续性一般；Ref2VA 多参考时「油腻感」略重。
