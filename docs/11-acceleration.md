# 11 · 加速方案：Turbo LoRA 与其他手段

> 调研日期 2026‑10‑31。来源：Larryvrh/ComfyUI‑MiniMax‑H3‑Turbo 与 larryvrh/MiniMax‑H3‑Turbo‑Lora 模型卡、lightx2v/Minimax‑h3‑Turbo 讨论区、Comfy‑Org/MiniMax‑H3 文件列表、B 站实测（小黄瓜、知乎对比文）、ComfyUI‑H3‑Multishot SETTINGS.md。

## 1. 结论

- 步数蒸馏 LoRA 是本地 H3 量产的前提：20 步 → 4–8 步，实测端到端 2.2–2.8 倍（含 VAE 与文本编码），纯采样约 5 倍。
- **8 步是质量与速度的平衡点**；4 步用于抽卡草稿；超过 8 步开始过锐。
- 画质代价集中在大动态（颗粒、拖影）与人脸皮肤（塑料感），静态对话戏几乎无损。

## 2. 原理层

官方开源权重本身已是 **CFG 蒸馏**（README："The released checkpoints are CFG-distilled Omni Transformer model weights"），因此 CFG 固定 1.0、无负向分支。Turbo LoRA 在其上再做步数蒸馏。两者叠加 = 4–8 步、CFG 1.0。

## 3. 可选 LoRA 一览

| 来源 | 文件 | 步数 | 备注 |
|------|------|------|------|
| Comfy‑Org/MiniMax‑H3 `loras/` | `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16` / `fl2v_turbo_8step_v1.0` / `ref2v_turbo_4step_v0.1`（各 1.96 GB） | 4 / 8 / 4 | ComfyUI 重打包，另有 `pika_h3_flex_{fl2va,ref2va}_v1` |
| lightx2v/Minimax‑h3‑Turbo（最新） | FL2V 4 步 **v1.3**、FL2V 8 步 **v1.1**、REF2V 4 步 **v1.0**、REF2V 8 步 **v1.1** | 4 / 8 | 官方推荐：8 步、Euler、simple、**视频 shift 6（仅 FL2V）**、音频 shift 3。社区有人反馈 FL2V v1.3 不如 v1.2，建议 A/B |
| larryvrh/MiniMax‑H3‑Turbo‑Lora | `minimax_h3_turbo_v4_step600_ema`（推荐）、`v4_step150_ema`、`4step_ema_ckpt850`（v1，适合 4 步 + 大动态） | 4–8 | bf16 约 744 MB；一个文件覆盖所有底模（bf16 / int8_convrot / pruned）；强度 1.0，scheduler simple |
| drozbay FastH3、Beidouqixing FlashGen、silveroxide dareties | 第三方 4 步实验版 | 4 | 社区评价不一 |

## 4. 参数建议

| 项目 | 推荐 | 说明 |
|------|------|------|
| 步数 | 草稿 4，成片 6–8 | >8 过锐 |
| 采样器 / 调度器 | Euler 或 res_multistep + `simple` | 02 工作流的 er_sde + ManualSigmas `1, .9375, .8333, .625, 0` 也是 4 步方案 |
| Sigma shift | FL2V：视频 6 / 音频 3；原版底模为 12 / 3 | Turbo 配 12 会偏糊 |
| LoRA 强度 | 1.0 | 拖影发糊 → 1.05–1.2；过锐颗粒 → 0.8–0.95 |
| CFG | 1.0 | 固定 |
| 帧数 | 17k+5 网格，124–362 | 5–15 s |
| low_vram | 关（bypass，最锐） | 开 = 合并进权重，省峰值显存但量化底模上偏软 |

## 5. 质量代价与规避

| 现象 | 条件 | 规避 |
|------|------|------|
| 颗粒、运动拖影 | 4 步 + 大动态 | 改 8 步；或 v1 ckpt850；强度 ↑ |
| 皮肤塑料感、过锐 | 4 步、步数 >8、强度过高 | 强度 ↓；二采「去油」；美学参考图 |
| 远景人脸糊 | 底模 + 768P | 分镜避免远景正脸；二采放大 |
| 音频质量下降 | Turbo 预览版 | 用 8 步 v1.x；必要时 TTS 重配 |

## 6. 其他加速手段（叠加需谨慎）

| 手段 | 实测 | 来源 |
|------|------|------|
| Spectrum | 约 −29% | Multishot SETTINGS |
| TeaCache 0.15 | 约 −14% | 同上 |
| BlockCache（T8） | 14 步时「几乎无效」，默认关 | 同上 |
| TE‑speed 插件 | 宣称 +45% | TETAE（B 站） |
| 双时钟采样器、光流跳步、EasyCache、超级缓存 | 宣称 70%–600% | 各 UP 自述，未验证 |
| int8_convrot 量化 + AdaLN 不加载 | 显存从约 66 GB 降到 24 GB 可跑 | 官方 README / Comfy‑Org |
| ActivationChunkStar7 / SageAttention patch | 省显存 | 本地已装 |

Multishot 的建议：**先把所有加速开关关掉、reserve 设 0 跑一次基线**，再逐个开，避免叠加出不可解释的画质问题。

## 7. 对本地流水线的落地

1. 补下 `ref2v_turbo_8step_v1.1`（短剧主路线是 ref2va，本地现有 ref2v 为 v0.1 预览 4 步）。
2. `run_episode_local` 草稿模式用 4 步出 2 候选，中选段 8 步重跑或直接作二采输入。
3. FL2V 工作流把 SigmaShift 从 12 改 6 做 A/B。
4. 在 test‑log 里记录每段「步数 / 版本 / 耗时 / 显存 / 主观质量」，一周后用数据定默认值。
