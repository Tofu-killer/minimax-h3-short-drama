# LoRA：风格 / 角色 / 三视图 / 提示词改写（本地 24 GB）

> 依据 `docs/13-github-survey/07-lora-training-and-misc.md`（Fizgig、AcademiaSD LoRAlab、Inline-Studio、IAmIronMan42、LightX2V 训练配置、masafykun / grawwww 实验、5 张 HF 模型卡）。

## 1. 决策：参考图路线 vs 角色 LoRA 路线

| 维度 | 参考图（Ref2VA 原生 / RefMod） | 角色 LoRA |
|------|------|------|
| 成本 | 零训练；每段多付参考 token | 静帧 LoRA 40 min–2 h（24 GB）；推理零额外 |
| 脸 / 结构稳定 | **强**（三方独立实验一致） | 弱到中，易偏油 |
| 画风 / 造型语言 | 弱（会被基座拉回写实） | **强** |
| 失败模式 | 多镜头里强参考「通吃」 | 过训崩音视频、学成「类型」 |

**规则**：默认参考图；角色 LoRA 定位为「画风 + 固定造型」而非「脸」，且**与参考图同用**。只在「同一角色要在几十段里保持非写实画风」或「参考图总被拉回写实」时加风格 LoRA（强度 0.5–0.8，叠 Turbo 再 +0.1–0.25）。任何 LoRA 上线前：同提示同 seed 有/无各出 2 条盲测（看脸、看运动、听台词——LoRA 可能伤音频）。

## 2. 在 4090 上训（Fizgig，Windows 一键）

- 基座 `minimax_h3_fl2va_pruned_int8_convrot.safetensors`，Blocks Swap / Base Precision 留 Auto，训练前关掉 ComfyUI。
- 预设「MiniMax H3 Fast (LoRA 8, 50 epochs)」：dim=alpha=8、automagic3 起始 lr 1e-6、0.25 MP、Likeness and Style、EMA 0.98、caption dropout 0.05；数据集 > 40 张或要兼顾提示遵从改 rank 16（rank 8 会丢提示遵从）。
- 去蒸馏适配器：照片集 Circlestone，片段集 Ostris；训练时不开 CFG / guidance-preservation 损失。
- Training mode `Default`（块 20–49）；只有训运动才 `More Blocks`（6–49）；永不训块 0–5；不勾「Train the text token refiner」。
- 数据：静帧 15–30 张多角度 / 景别 / 服装；片段须 `.mp4`、24 fps、帧数 ∈ {22,39,56,73,90,107,124}、边长 32 倍数、音频 32 kHz 立体声或无轨（用 Gizmo 或 GK-Nodes `GK H3 Dataset Builder` 切片）。24 GB 上片段 ≤ 56 帧 0.5 MP、73–124 帧 0.25 MP，片段只学运动，脸靠静帧。
- 系统 RAM ≥ 32 GB（开预览 ≥ 48 GB），Windows 分页文件系统托管；RAM 不足表现为「CUDA out of memory」或静默退出。
- 预览钳到 22 帧；相似度以 ComfyUI 20–25 步正式出图为准。
- 纯音频 / 人声 LoRA 不要训；带声音须混 ≥ 30 段不含触发词的锚片段、rank 16、`lr×steps < 0.22`、weight decay 1e-4。
- 推理强度：画风优先 1.0–1.2，平衡 0.6–0.8；检查点取中后段（800 步取 500；40 epoch 取 20）。
- 接线 `LoraLoaderModelOnly`，`BasicGuider` 与 `BasicScheduler` 都接 LoRA 之后的 model；自训 LoRA 可与 Turbo 同载。
- 训练用 shift 12/3 口径；若推理用 Turbo 4 步，shift 改 6/3 且量化 DiT 需 `lora_dynamic_apply: true`（LightX2V）。

## 3. 现成风格 LoRA（HuggingFace）

| LoRA | 用途 | 强度 |
|------|------|------|
| `Inner-Reflections/MiniMax-H3-Looping-Sketch-Anime` | 手绘 2D 动漫（漫剧） | 0.75–1.25，提示含 `hand-drawn 2D anime art style, rough textured outlines, flat colors, white outline` |
| adf99 Anime Slider | 2D ↔ 写实连续调节（正 2D、负写实） | 小幅 |
| `fal/research-mini-max-h3-realism-people-lora` | 写实人物（电影质感） | 默认 |
| Jojocodex Camera Motion | 运镜缺失时 | 默认 |
| `TenStrip/Krea2-H3-Style-Lora` | 仅纯 T2V 有效 | r512 |

## 4. 角色三视图 / 设定图

- `matlod/minimax-h3-turnaround`（`five_view_512_s1500`）+ `H3 Contact Sheet` / `Decode` 节点：ref2va pruned int8，`res_multistep` / `simple`、28 步、denoise 1.0、强度 1.0；要白底改 `_s400_instruct` 并加 `neutral studio background`；提示里保留 `<Picture 1>`。一张照片 → 5 个一致角度。
- **turnaround LoRA 不要留在普通视频图里**（运动会变成离散姿态叠影）。
- 其它路线见 `quality-pipeline.md`（OrbitSheets、Still / SingleFrame、Image-VAE）。
- RefMod（MiniMaxH3Mod）：按目标模型分别生成（ref2va / fl2va 各一份）；视频 RefMod 慎用自带提取器（`4k+1` 裁帧与 `17n+5` 不符），静帧不受影响。

## 5. 本地提示词改写 LoRA

- `pytraveler/MiniMax-H3-Prompt-Rewriter-ComfyUI`：选 `[gguf]` 8B 条目（≈6 GB 下载、≈9 GB 显存），`keep_model_loaded=False`，`llama_backend=auto`；已有 Ollama 模型自动出现在 `writer_model`。
- 改写 LoRA 只覆盖 T2VA / I2VA / L2VA / FL2VA；**Ref2VA 六段式不要经它改写**。

## 6. 其它可控性

- 不写负面提示（无效），要「少动 / 多动」「更冷 / 更邪」用 `ComfyUI-Dials` 的 `Load Dial` + `Apply Dial`（Motion −2…+2）。
- 一镜局部出错（手、字、道具、某句台词）用 LanPaint `VideoMaskEditor → AVEncode → 采样 → AVDecode` 局部重绘，不整段重抽。
- 多 RefMod / 参考同用：视觉在前、音频在后、按模态分别计数；多镜头提示把所有角色放进第一镜；要么每个角色都给声音要么都不给。
- 单卡不装 raylight / LightX2V 多卡；X-MinimaxH3（许可证禁用、Linux only）排除；VPack 仅 ComfyUI ≥ 0.38 且带参考视频时考虑。
