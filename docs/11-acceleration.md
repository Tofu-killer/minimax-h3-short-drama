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

## 8. lightx2v/Minimax‑h3‑Turbo 文件清单（魔搭镜像，2026‑10‑20 更新）

24 个权重文件，命名规则 `minimax_h3_{fl2v|ref2v}_turbo_{4|8}step_v{版本}[_768p]{_bf16|_comfyui_bf16}`。**没有 `768p` 后缀的是 544p 训练版**（训练 shift 12/3）；`768p` 版按 1344×768 训练，shift 6/3。ComfyUI 用 `_comfyui_bf16`（约 1.96 GB），其余 bf16 约 1.38 GB，`fl2v_4step_v1.1_768p_fp8` 为 34 GB 整合版不要下。

| 变体 | 可用版本 | 4090 @768p 推荐 |
|------|----------|-----------------|
| FL2V 4 步 | v0.1(544p)、v1.0/1.1/1.2/1.3 (768p) | v1.3 与 v1.2 A/B |
| FL2V 8 步 | v1.0(544p)、v1.0/1.1 (768p) | **v1.1_768p** |
| REF2V 4 步 | v0.1(544p)、v1.0 (768p) | v1.0_768p |
| REF2V 8 步 | v1.0/1.1 (768p) | **v1.1_768p** |

官方规格表只覆盖到 v1.0；在线 Studio 当前用 FL2V 8 步 v1.0 768p，8 NFE、视频 shift 6、音频 shift 3。参考图 resize 选 `match`。

## 9. 「为什么我 4090 比别人 5070 还慢」排查清单

| 可能原因 | 判断方法 | 处理 |
|----------|----------|------|
| 分辨率：别人跑 544p（960×544 / 864×480），你跑 1344×768，像素 2.3 倍 | 同工作流改 864×480 对比 | 草稿用 544p，成片再 768p 或二采放大 |
| 工作流走了非 Turbo 分支：20 步 + CFG 6（CFG>1 每步两遍） | 看采样节点实际 steps / cfg | 确认 Turbo 开关为 True，CFG 1.0，4–8 步 |
| 双采 / SelfLift 多步 | 04 工作流 10 步 + refine | 只对中选段落跑 |
| LoRA 为 544p 版却在 768p 用、shift 12 | 文件名无 `768p` | 换 768p 版，shift 6/3 |
| 显存溢出回落到系统内存（Windows 默认允许，不报错只变慢） | 1344×768 比 864×480 慢 >5 倍；任务管理器「共享 GPU 内存」上涨 | NVIDIA 控制面板 → CUDA 系统内存回退策略 → 首选无回退；开 ActivationChunkStar7 / 分块 FFN |
| 未用 Sage Attention | 启动日志 `Using pytorch attention` | 安装 sageattention，接 KJNodes `MiniMaxH3MemoryEfficientSageAttentionPatch`，约 1.5–2× |
| 驱动显存降级导致随机慢渲染 | 同参数偶发慢 3 倍 | Multishot 的 driver headroom 规则：留显存余量，重启 ComfyUI |

基准参考：3090，736×1280，192 帧，Turbo 每步 67–98 s（Multishot 实测）；4090 约快 1.7 倍，1344×768 / 10 s / 4 步不溢出应在 5 分钟上下。

## 10. DaSiWa 节点包与「2 分钟出 10 秒」的真相（2026‑11‑02 补充）

**DaSiWa**（`darksidewalker/ComfyUI-DaSiWa-Nodes`，GPL‑3.0，173★ / 571 commits）是画质与长视频取向的节点包：Director 时间轴 + RefMod 参考库 + Prompt Forge、Continuity Segment Prepare/Decode/Publish + Join Clips（长视频分段续接）、Tiled/Enhanced Upscale、RTX 帧生成与超分、LLM 写提示词，以及 `MiniMaxH3Cache`。其最新工作流 C‑MMH3‑33：fl2va + ref2va 剪枝 int8，**25 步** res_multistep simple，shift 11/4，**无 Turbo LoRA，Cache 节点默认旁路**。

`MiniMaxH3Cache`：缓存整个 H3 Transformer 块堆栈的残差，当采样 token 特征变化小于 `reuse_threshold`（默认 0.05）时整段跳过；作用区间 `start_percent/end_percent` 0.15–0.90，连续命中上限 `max_steps` 2。文档明言**没有实测加速与画质数据**，「显示的加速比只是理论块跳过比例」，要求同 seed A/B 检查音频连续性、运动稳定性与参考保持。源自 lihaoyun6/ComfyUI‑MiniMaxH3‑Cache。

**「2 分钟出 10 秒」**：RunningHub「Dasiwa‑MiniMax H3‑Dynamic Strongest‑Single Sample」（作者青橙Lab）页面无此声明、无显卡与分辨率；节点为 T8 `MiniMaxH3DualClockSamplerT8` + `MiniMaxH3AudioConditioningT8` + SageAttention，与 DaSiWa 节点无关（「Dasiwa」疑指 DaSiWa 融合模型，未核实）。

**有数据的基准**（`neng320/minimax-h3-local-deployment`，RTX 4060 Ti 16G，2026‑08‑08，5 秒片）：

| 配置 | 耗时 | 画质 |
|------|------|------|
| 剪枝 int8，864×480，12 步，Sage | 109 s | 剪枝细节弱 |
| 剪枝，1056×608 | 180 s | |
| 剪枝，1344×768，20 步 | 360 s | |
| 完整 int8，640×640，8 步 Turbo，无加速 | 391 s | 基线 |
| 同上 + **SageAttention** | **300 s** | 无损，推荐 |
| 同上 + TE‑Speed | 195 s | **文字乱码、手嘴变形，弃用** |
| 冷启动（JIT 编译 + 34G 载入） | 490–818 s | 第 2 条起才是真实速度 |

换算到 4090（约 2.5–3×）：480p + Turbo + Sage 的 10 秒片约 1.5–2 分钟，1344×768 约 5–8 分钟。所谓「很快」基本都是 480p 抽卡档。

结论：
1. **SageAttention 是唯一反复验证「提速且无损」的加速**（1.3–1.5×）；TE‑Speed 在 8 步 Turbo + int8 下失真，不用。
2. Cache 类（DaSiWa / lihaoyun6 / EasyCache）只能同 seed A/B 后再用，口型与参考保持最易受损。
3. 同 seed 同参数重跑会命中 ComfyUI 结果缓存秒出，抽卡务必换 seed。
4. DaSiWa 的 Continuity Segment / Join Clips 与 RefMod 库是长视频与资产管理的好思路，流程跑通后再评估。

## 11. 本机实测：稀疏注意力 vs SageAttention（RTX 4090，2026‑11‑02）

条件：YZ 双采工作流副本，864×480，10 秒，同段、同提示词、同步数与 LoRA；先预热，再用 seed+1 计时（同 seed 会命中 ComfyUI 结果缓存）。

| 组 | 配置 | 第二次耗时 | 显存峰值 | 清晰度（拉普拉斯） |
|----|------|-----------|----------|-------------------|
| A | comfy kitchen + BlockSparseAttention（tau 1.3，从 20% 步起）+ MiniMaxLowVRAMAttention 4 | 138 s | 24.0 GB* | 2026 |
| B | PathchSageAttentionKJ(auto) + MiniMaxH3MemoryEfficientSageAttentionPatch，旁路稀疏 / kitchen / LowVRAM | 134 s | 24.0 GB* | 2204（+9%） |
| C | B + MiniMaxLowVRAMAttention 4 | **不可用**：第 1 步 693 s（A 为 41 s），16 分钟后中断，无 OOM | 23.5 GB | — |

\* ComfyUI 尽量常驻模型，峰值不代表实际需求。

结论：
1. 864×480 / 10 s 约 2 分钟，与社区「2 分钟出 10 秒」一致；
2. 低分辨率下 token 少，稀疏注意力几乎不省时间；Sage 速度持平、画质不差 → 抽卡档用 Sage；
3. **Sage 与 MiniMaxLowVRAMAttention 实测不能同时开**（尽管 KJNodes 源码注释称可组合），会走极慢路径，原因未验证；
4. 待测：1344×768 一对，稀疏注意力在高 token 数下才可能拉开差距，且关闭 LowVRAM 后需确认是否爆显存。

注意：清晰度对比必须两组同 seed；计时用的 seed+1 两组也要一致。
