# 本地栈与加速：24 GB 单卡的草稿档 / 精修档

> 数据来源：用户 RTX 4090 实测（`docs/11-acceleration.md` §11）、neng320 4060Ti 基准、wildminder 社区性能报告、MiniMax 官方生态索引 Speed 一节、以及 29 个加速仓库的源码级精读（`docs/13-github-survey/03-acceleration.md`）。所有「作者自报」数字都注明硬件与口径。

## 0. 先盘点（agent 第一步）

按 `assets/local-inventory-checklist.md` 产出：GPU / 驱动 / CUDA / PyTorch 版本、ComfyUI 版本与启动参数（是否带 `--use-sage-attention`）、`models/` 下的 H3 文件名与大小、custom_nodes 列表（重点：KJNodes、sageattention 包版本、comfy-kitchen、任何 cache / TE-Speed / Spark / Sol / Veda / Spectrum 节点）、现有工作流的注意力 / LoRA / 步数 / shift / 分辨率、ffmpeg 是否在 PATH、Windows 的 CUDA「系统内存回退」是否关闭、系统内存大小。

## 1. 三个杠杆与叠加原则

| 杠杆 | 代表 | 有损？ | 规则 |
|------|------|--------|------|
| 少步（蒸馏） | lightx2v Turbo 4/8 步、alibaba-pai PDD 8 步、HyperFlow 8 步、FastH3 整模、Pika Flex 6 步、DMAD、VDN turbo adapter | 4 步明显、8 步轻微 | **只选一个**；VDN / PDD / SVDQuant 量化权重已折叠蒸馏，不再叠 LoRA |
| 便宜的步 | 注意力核：SageAttention（无损）、核心 `BlockSparseAttention`（已合并 Sol/SLA/VSA，稀疏=有损）、Veda / Spark-H3 / Kablex VSA（有损稀疏）；跳步缓存：Spectrum、FirstBlockCache、T8 BlockCache、EasyCache（有损） | 核无损；稀疏与缓存有损 | 同一模型分支只能有一个「跳步/缓存」、只能有一个 attention 补丁；精修档只留 Sage |
| 便宜的模型 | pruned（AdaLN 剪枝）int8、nvfp4、GGUF、VDN 架构替换、ClipProj 小文本编码器 | 剪枝略损细节 | 24 GB 用 int8_convrot（pruned 更省显存，不剪枝画质更稳） |

**基线链**（所有加速都在它之上同 seed A/B）：
`UNETLoader(int8_convrot)` → `LoraLoaderModelOnly(lightx2v *_turbo_8step_v1.1*_comfyui_bf16, 1.0)` → KJ `PatchSageAttentionKJ(auto)` → KJ `MiniMaxH3MemoryEfficientSageAttentionPatch` → `MiniMaxH3SigmaShift` → Guider。先全关跑一次基线，再逐个开，一次只改一个变量。同 seed 同参数重跑会命中 ComfyUI 结果缓存秒出，计时与对比用 seed+1。

## 2. 推荐组合（RTX 4090 24 GB，Ref2VA 短剧）

### 草稿档（抽卡，目标 ≤ 2–3 min / 条）
- 权重：`ref2va_pruned_int8_convrot`（或 fl2va）+ `qwen3vl_32b_minimax_h3_nvfp4_awq` + int8 视频 VAE + fp32 音频 VAE
- LoRA：`minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16` 强度 1.0（抽卡可降 `ref2v_turbo_4step_v1.0_768p`；声音不稳降 0.75）
- 采样：8 步 Euler + `simple`（或 `res_multistep`），CFG 1.0；`MiniMaxH3SigmaShift`：Ref2V 12 / 3，FL2V 768p 版 6 / 3
- 注意力：KJ Sage 两节点；**不接** `MiniMaxLowVRAMAttention`（与 Sage 同开实测第一步 693 s）；旁路 kitchen / BlockSparse；省显存改 KJ `MiniMaxChunkFeedForward` 或 star7 分块（`chunk_tokens 8192 / mlp 4096 / qkv 4096`）
- 分辨率：864×480 或 960×544，5–10 s；`ref_image_size = match`；每段 2–4 个 seed
- 实测：864×480 × 10 s × 8 步 ≈ 134 s（4090）
- 可选（ComfyUI ≥ 0.38 后）：Veda `VedaSparseAttention` 放在 LoRA 与 Sage 补丁之后、Guider 之前，预测器只保证 1344×768 / 768×1344 / 768×768 / 1024×768 × 5/10/14 s × 8 步 Turbo；首次 Ctrl+B 旁路同 seed 对比再默认开
- 激进替代（仅 Ref2VA、放弃 Sage）：Kablex `Ref2VAVSAGatePatch(sparsity 0.5–0.75)` + ref2v 4 步 v0.1 + shift 12/3，1344×768 × 5 s ≈ 72 s（作者自报），模型分支上不得有任何 Sage/Sol 节点

### 精修档（中选段，1344×768）
- **路线 A（默认）**：Turbo 8 步 v1.1 + Sage，其余加速全关；`low_vram`（合并）与 bypass 各跑一次同 seed 定默认（3090 实测合并反而快 25% 且皮肤更干净，勿照抄「bypass 最锐」）
- **路线 B（画质优先）**：无 Turbo 20 步 `res_multistep` + `simple` + Sage，再**二选一**叠加 Spectrum（默认参数，SigmaShift 之后 Guider 之前，`history_storage=system_ram`）或 FirstBlockCache `H3 Fast`（5090 实测 −30%；控制台 hit 数为 0 就移除）；8 步链两者都不挂
- **路线 C（≥ 10 s 长段，ComfyUI 0.38.x 后）**：Spark-H3（Windows SM89 CUDA-13 包，`fidelity`、`topk_ratio 0.2`，Ref2VA 带参考视频时 `sparse_scope joint-video`、`dense_backend sage`）或 Veda，二选一，不与核心 `Block Sparse Attention` 同链；5 s 短片不值得折腾（3090 实测 Spark 与核心 Sol 同速 158 vs 152 s）
- **二采精修**：第一段 0.2–0.33 MP 4–8 步 → `MiniMaxH3LatentUpscaleWithModel`（LBH 权重）放大 → 第二段 0.98 MP **3 步**，sigmas `0.9035, 0.6316, 0.3158, 0`，稀疏注意力只开在第二段；详见 `quality-pipeline.md`
- **写实 A/B**：alibaba-pai PDD Ref2VA 8 步替换 Turbo（`MiniMaxH3PDDAccApply nfe=8`，SIGMAS 接 `SamplerCustomAdvanced`，Euler、CFG 1、shift 恰好 12/3，不接任何缓存，不用 er_sde / res_multistep）；漫剧 / 插画风格保持 Turbo（PDD 4 NFE 会压平纹理）
- 预计：1344×768 × 10 s × 8 步 ≈ 5–8 min（4090，含 VAE）

### FL2VA（I2VA 首帧 / 尾帧衔接）
`fl2va_pruned_int8_convrot` + `minimax_h3_fl2v_turbo_8step_v1.1_768p_comfyui_bf16`，shift 6 / 3；其余同上。

## 3. 明确不要叠加

- 任何两种蒸馏：lightx2v Turbo × PDD × HyperFlow × VDN turbo adapter × larryvrh。
- Spectrum × EasyCache / LazyCache / T8 BlockCache / FirstBlockCache；任何 BlockCache × 核心 Block Sparse Attention；FirstBlockCache × 其它 double_block 替换。
- Kablex Ref2VA-VSA × Sage / Sol / 任何 attention override（抛错）。
- Veda × 核心 Model Sparse Attention；Veda 放在 KJ MemEff Sage 之前（收不到调用）。
- Spark-H3 × 第二个 attention 补丁；Spark-H3 × ComfyUI 0.37 / 0.41。
- VDN-H3 × Sol 调度补丁 / 社区 Turbo LoRA / `fast_kernels`。
- KJ `MiniMaxLowVRAMAttention` × Sage；KJ LowVRAM × sol-attn `Fused Modulation`。
- `--use-sage-attention` 启动参数 × KJ `Patch Sage Attention` 节点（重复 patch）。
- PDD × er_sde / res_multistep / 任何缓存 / shift ≠ 12/3。
- 8 步 Turbo × Spectrum / 任何 BlockCache（无命中）/ TE-Speed（失真）。
- 不安装：lihaoyun6 Cache（替换核心 `_forward`）、TE-Speed OSS（patch 核心 `model.py`，已装先 `python patch_model.py --revert`）、tl2012tl TE-Speed（闭源 .pyd）、xmarre Sol-H3（Windows 空转）、W4A4-VSA（24 GB 无需）、pottokao GGUF-TE（对 H3 无效）。

## 4. 基准表（口径各异）

| 硬件 | 配置 | 分辨率 × 时长 × 步 | 耗时 |
|------|------|-------------------|------|
| 4090（用户） | ref2va pruned int8 + Turbo 8 步 + Sage | 864×480 × 10 s × 8 | 134 s |
| 4090（用户） | 同上，BlockSparse + kitchen + LowVRAM 代替 Sage | 同上 | 138 s（清晰度低 9%） |
| 4090（用户） | Sage + LowVRAM 同开 | 同上 | 第一步 693 s，不可用 |
| 4090（Kablex 自报） | Ref2VA-VSA 稀疏 + 4 步 | 1344×768 × 5 s × 4 | ≈72 s，13.5 GiB |
| 4090（VDN 第三方） | VDN-H3 8 步 | 1344×768 × 5 s × 8 | 135 s 热，18.5 GB |
| 4090（pxl-pshr Loop） | Ref2VA 8 步 Turbo / 25 步 | 1280×704 × 107 帧 | ≈4 min / ≈12 min |
| 3090（Spark 文档） | Turbo 8 步 + Spark vs 核心 Sol | 1344×768 × 5 s × 8 | 158 s vs 152 s |
| 4060Ti 16G（neng320） | 完整 int8 + Turbo 8 步 | 640×640 × 5 s × 8 | 391 s 基线 / 300 s +Sage / 195 s +TE-Speed（失真） |
| 4060Ti 16G（neng320） | pruned int8 + Sage | 1344×768 × 5 s × 20 | 360 s |
| 5090（duckyshell） | 20 步 res_multistep Sage → +FirstBlockCache Fast | 0.5 MP × 5 s × 20 | 58 s → 40 s |
| 5090（Saganaki22） | VDN-H3 | 1280×736 × 145 帧 | 17 → 13.9 s/it |
| 8×B300（NVIDIA Sol-H3） | 4 步蒸馏 + Ulysses | 1344×768 × 10 s | 3.7 s（数据中心，不可比） |

估算：同配置下耗时随 token 数（宽×高×帧）近似线性偏超线性；1344×768 ≈ 864×480 的 2.5 倍像素 → 2.5–3.5 倍时间。稀疏注意力的收益随时长增长，5 s 以内几乎无差。

## 5. 「为什么比别人慢」排查顺序

1. 分辨率与时长同口径？（多数「2 分钟 10 秒」是 480p–544p）
2. 还在跑 20 步 + CFG 分支？→ Turbo 8 步，CFG 1
3. LoRA 版本与分辨率匹配？（544p 版跑 768p 既慢又糊）
4. Windows：NVIDIA 控制面板关闭「CUDA 系统内存回退」；看「共享 GPU 内存」是否被占用
5. int8 DiT 权重是否 **100% 驻留 GPU**：差几百 MB 未全载，步时从 ~19 s/it 跌到 ~283 s/it；OOM 时降分辨率或减参考图，不要加 reserve
6. Sage 已生效？（控制台 patch 日志）是否与 LowVRAM 同开？是否启动参数和节点重复 patch？
7. 冷启动：第一条含 JIT 编译（Triton / Sage）与 34 GB 载入，8–14 min 属正常；任何稀疏 / Sol 节点换分辨率或时长都会重新 JIT
8. 系统内存 ≥ 64 GB？32 GB 时加 `--disable-pinned-memory`，TE 可放 CPU（约 +27 s/次）
9. PyTorch / CUDA 过旧 → 升到 cu128+ 后 int8 / nvfp4 核才快；显卡功耗墙拉满

## 5b. 长尾实测补充（`docs/13-github-survey/08-long-tail-comfyui.md`）

- **4090 单段帧数上限 328 帧**（19×17+5）：345 帧有 6/7 概率个别 step 停滞 2.5–4.8×、整段慢 3–17×；1280 宽改 **1216** 让 VAE 解码 tile 28→24、总时长 −15%；VAE tile 保持 256（512+ 不更快且 PSNR 40→21 dB 出格子）。
- 采样期间不要轮询 ComfyUI HTTP（每次停 18–43 s，`comfy_submit.py --poll` 设 ≥ 20 s）；同配置耗时涨到 1.8× 立即重启 ComfyUI（CUDA 崩溃前兆）；渲染时关杀毒实时扫描。
- **int8_convrot 底模上挂 LoRA 用运行时分支 / bypass，不反量化合并**：合并往返注入 ~1.5% 权重噪声而 H3 LoRA delta 只有 0.01–0.08%；多 LoRA 用 PowerLoraStack `quantized_layers=auto`，视频风格 LoRA 的 audio 模态缩到 0–0.25。装 LoRA 后日志必须出现 `208 patches attached`。
- 同一提示词多 seed 抽卡时把条件编码落盘复用（pepikir `H3SaveConditioning/LoadConditioning` 或 CLIPCached），采样图里不放 CLIPLoader；32 GB 内存机器单图 `--cache-none`；TE 与 DiT 放 NVMe（编码 90→25 s）。
- 若用核心 EasyCache：`end_percent` 封顶 0.70（默认 0.95 后期跳步造成织纹与色块）。
- Turbo 无 CFG 链路的微调旋钮：Fizgig H3 Tweaks（LoRA 之后、采样器之前）`Detail & Contrast 0.15`、`Prompt Strength 0.2`、`Scene Variation ±0.1–0.3`；不与块跳过类节点同挂。
- Sol / 块稀疏注意力只在 ≥ 768p 成片档开（1.23–1.27×）；480p 档 1.03× 且高频 −13.8%。
- 明确别碰：HyperStep / TeaCache（无画质护栏）、AutoContext 整包（patch PackedLayout）。

## 5c. 补读新增

- **出图与出视频分实例**：comfy-kitchen ≥ 0.2.36 的 `--use-ck-attention` 会让 Qwen-Image 2.1 在 mask 存活 token > 64 时崩图，但 H3 不受影响且不开 CK 慢 2.7× → 给 Qwen-Image 的 ComfyUI 不带该参数，给 H3 的实例保留。
- 驱动 ComfyUI：每 N 个任务 `POST /free {"unload_models":true,"free_memory":true}`（`comfy_submit.py --free-every N`）；`/history` 与 `/queue` 连续 3 次都查不到才判丢失；H3 不与其它 GPU 任务并行；计时读 `/history` 执行时间。
- 权重下载源核实：DMAD 4-step LoRA 在 `Kijai/MiniMax-H3-experimental/loras/minimax_h3_DMAD_4step_full_lora_avg_rank_39_bf16.safetensors`（同目录有 PDD Acc-8Step FL2VA/Ref2VA、flashgen 4-step、open_regenerate_2k_refiner r16）；X2 Detail VAE 有官方 `_int8_convrot` 版；lightx2v Turbo-SLA 实为 `fl2v_turbo_4step_v0.1_768p_sla_comfyui_bf16`；FastVideo/FastH3 私有（401）。
- 5090 实测规则（mathruffian）：EasyCache 定稿不开；Veda 开着会在第 51/119/187 帧闪帧；DMAD 4 步可做日常定稿（8 类镜头看不出差、快 49–58%）；单镜 ≤ 12 s。
- 3090 Ti 实测：FastVideo VSA 0.8 MP 5 s 4 步 topk 0.1 采样 49 s（比 20 步快 10×），Sage/CK 在 topk 0.1 下无增益，峰值 ~22 GB。
- GB10 int8 对照（chiphoton）：Larry v4 6 步 vs 20 步 res_multistep 端到端 2.2×，I2V 首帧 SSIM 0.8215 vs 0.8245（几乎无差）。

## 6. 升级 ComfyUI 前检查

Spark-H3 跳过 0.41（要 0.38.x–0.40.x 或 0.42.x–0.44.x）；Spectrum 需 ≥ `e377e263`；Veda ≥ 0.38；HyperFlow 在 0.37 有「Model Initializing」卡住报告（诊断 `--disable-fast-disk`）；FeiHou 流式块模式不与 kitchen 同用；核心 INT8 已进主线（旧 I8Fast 文件要转换）。

## 7. 下载清单（HuggingFace，澳洲可直连）

- Comfy-Org/MiniMax-H3：`diffusion_models/`、`text_encoders/`、`vae/`、`loras/`
- lightx2v/Minimax-h3-Turbo：`minimax_h3_{fl2v,ref2v}_turbo_{4,8}step_v1.x_768p_comfyui_bf16.safetensors`
- larryvrh/MiniMax-H3-Turbo-Lora：`minimax_h3_turbo_v4_step600_ema.safetensors`（FL2VA 4 步备选，漫剧友好）
- alibaba-pai/MiniMax-H3-Acc-LoRAs（PDD 8 步；新版 ComfyUI 原生 LoRA-bank 可直接加载，旧版用 Jalen-Brunson 节点或 aptech0081 重打包）
- LBH-123-AI/Minimax_h3_latent_Upscaler（latent 二采权重，装原版节点，不装 xmarre `-Plus` 分支）
- lihaoyun6/MiniMax-H3-Ref-Patch（FL2VA 仿 Ref2VA）
- alibaba-pai/MiniMax-H3-Fun-Controlnet-Union（姿态 / 深度 / 边缘控制）
- Imagineer13/H3-Anti-Burn-LoRA（仅续接链上的皮肤斑点修复）
