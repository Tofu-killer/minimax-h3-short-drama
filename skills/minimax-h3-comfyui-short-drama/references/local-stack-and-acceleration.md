# 本地栈与加速：24 GB 单卡的草稿档 / 精修档

> 数据来源：用户 RTX 4090 实测（`docs/11-acceleration.md` §11）、neng320 4060Ti 基准、wildminder 社区性能报告（17 个 Reddit 线程）、MiniMax 官方生态索引 Speed 一节、各加速仓库 README。GitHub 精读见 `docs/13-github-survey/03-acceleration.md`。

## 0. 先盘点（agent 第一步）

按 `assets/local-inventory-checklist.md` 产出：GPU / 驱动 / CUDA / PyTorch 版本、ComfyUI 版本与启动参数、`models/diffusion_models|text_encoders|vae|loras` 下的 H3 文件名与大小、custom_nodes 列表（重点：KJNodes、sageattention 包、comfy-kitchen、任何 cache/TE-Speed/Spark/Sol 节点）、现有工作流 JSON 与它们的注意力/LoRA/步数/分辨率设置、ffmpeg/ffprobe 是否在 PATH、Windows 的 CUDA「系统内存回退」是否关闭。

## 1. 三个杠杆与叠加原则

| 杠杆 | 代表 | 有损？ | 规则 |
|------|------|--------|------|
| 少步（蒸馏 LoRA） | lightx2v Turbo 4/8 步、alibaba-pai PDD 8 步、Hyperflow 8 步、FastH3、Pika Flex 6 步、DMAD | 轻微（4 步明显） | **只选一个**；VDN/PDD/SVDQuant 量化权重已折叠蒸馏，不再叠 LoRA |
| 便宜的步（注意力/缓存） | SageAttention（无损）、Sol-Attn Triton（无损，SM89+）、BlockSparse / Spark-H3 / VSA（有损稀疏）、Spectrum / FirstBlockCache / TE-Speed / EasyCache（有损跳步） | 注意力核无损；稀疏与缓存有损 | 草稿档可开一个有损项；精修档只留 Sage/Sol |
| 便宜的模型 | pruned（AdaLN 剪枝）int8、nvfp4、GGUF、VDN 架构替换 | 剪枝略损细节 | 24 GB 用 pruned_int8；不剪枝 int8 画质更稳但靠 offload 慢 |

先全部关掉跑一次基线（reserve 0），再逐个打开，每次只改一个变量。同 seed 同参数重跑会命中 ComfyUI 结果缓存秒出，计时与对比用 seed+1。

## 2. 推荐组合（RTX 4090 24 GB，Ref2VA 短剧）

### 草稿档（抽卡）
- 权重：`ref2va_pruned_int8_convrot` + `qwen3vl_32b_minimax_h3_nvfp4_awq` + int8 视频 VAE + fp32 音频 VAE
- LoRA：`minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16`，强度 1.0（声音不稳降 0.75）
- 采样：8 步，`res_multistep` 或 Euler + `simple`，CFG 1.0；`MiniMaxH3SigmaShift` 6 / 3
- 注意力：KJNodes `PathchSageAttentionKJ(auto)`（配 `MiniMaxH3MemoryEfficientSageAttentionPatch`）；旁路 `ModelAttentionBackend(kitchen)`、`BlockSparseAttention`、`MiniMaxLowVRAMAttention`
- 分辨率：864×480 或 1056×608，10 s（243 帧）；`ref_image_size = match`
- 每段 2–4 个 seed；实测 864×480 / 10 s ≈ 134–138 s / 条（4090）

### 精修档（中选段）
- 同权重、同 LoRA；1344×768（或先 latent 二采到 1344×768，见 `quality-pipeline.md`）
- 8 步（不要超过 8，过锐）；Sage 保留；所有有损加速关闭
- 预计 1344×768 / 10 s ≈ 5–8 min / 条（4090，含 VAE）；1344×768 token 数更高时才值得测试稀疏注意力是否拉开差距
- 需要 1080p+ 成片：精修后像素级超分（SeedVR2 / Tessera）或 LBH latent 二采到 1920×1088

### FL2VA（I2VA 首帧 / 尾帧衔接）
- `fl2va_pruned_int8_convrot` + `minimax_h3_fl2v_turbo_8step_v1.1_768p_comfyui_bf16`，shift 6 / 3；其余同上。

## 3. 基准表（作者自报，口径各异）

| 硬件 | 配置 | 分辨率×时长×步 | 耗时 |
|------|------|----------------|------|
| 4090（用户） | ref2va pruned int8 + Turbo 8 步 + Sage | 864×480 × 10 s × 8 | 134 s |
| 4090（用户） | 同上，BlockSparse+kitchen+LowVRAM 代替 Sage | 同上 | 138 s（清晰度低 9%） |
| 4090（用户） | Sage + LowVRAM 同开 | 同上 | 第一步 693 s，不可用 |
| 4060Ti 16G（neng320） | 完整 int8 + Turbo 8 步 | 640×640 × 5 s × 8 | 391 s 基线 / 300 s +Sage / 195 s +TE-Speed（失真） |
| 4060Ti 16G（neng320） | pruned int8 + Sage | 1344×768 × 5 s × 20 | 360 s |
| 4090（Kablex 自报） | Ref2VA-VSA 稀疏 | 5 s | ≈72 s，13.5 GiB |
| 5090（Saganaki22 自报） | VDN-H3 | 1280×736 × 145 帧 | 17 s/it |
| 8×B300（NVIDIA Sol-H3） | 4 步蒸馏 + Ulysses | 1344×768 × 10 s | 3.7 s（数据中心，不可比） |

估算经验：同一配置下耗时 ≈ 与 token 数（宽×高×帧）近似线性偏超线性；1344×768 是 864×480 的 2.5 倍像素，预计 2.5–3.5 倍时间。

## 4. 「为什么比别人慢」排查顺序

1. 分辨率与时长同口径？（多数「2 分钟 10 秒」是 480p–544p）
2. 还在跑 20 步 + CFG 分支？→ Turbo 8 步，CFG 1
3. LoRA 版本与分辨率匹配？（544p 版跑 768p 既慢又糊）
4. Windows：NVIDIA 控制面板关闭「CUDA 系统内存回退」；任务管理器看「共享 GPU 内存」是否被占用
5. 注意力：Sage 已生效？（控制台应打印 patch 日志）是否与 LowVRAM 同开？
6. 冷启动：第一条包含 JIT 编译与 34 GB 载入，第二条起才算
7. 系统内存 ≥ 64 GB？不足时 TE 与 DiT 轮换加载会拖慢
8. PyTorch/CUDA 过旧（cu118/cu121）→ 升到 cu128+ 后 int8/nvfp4 核才快

## 5. 下载清单（HuggingFace，澳洲可直连）

- Comfy-Org/MiniMax-H3：`diffusion_models/`、`text_encoders/`、`vae/`、`loras/`
- lightx2v/Minimax-h3-Turbo：`minimax_h3_{fl2v,ref2v}_turbo_{4,8}step_v1.x_768p_comfyui_bf16.safetensors`
- larryvrh/MiniMax-H3-Turbo-Lora：`minimax_h3_turbo_v4_step600_ema.safetensors`（FL2VA 4 步备选）
- alibaba-pai/MiniMax-H3-Acc-LoRAs（PDD 8 步，需 LoRA-bank 支持的新版 ComfyUI；或 aptech0081 重打包）
- LBH-123-AI/Minimax_h3_latent_Upscaler（latent 二采权重）
- lihaoyun6/MiniMax-H3-Ref-Patch（FL2VA 仿 Ref2VA）
- alibaba-pai/MiniMax-H3-Fun-Controlnet-Union（姿态/深度/边缘控制）
