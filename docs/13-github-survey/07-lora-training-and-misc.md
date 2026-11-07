# 07 · LoRA 训练 / 角色与风格 LoRA / 推理期可控性杂项 / 多 GPU 与服务化

> 调研日期 2026-11-07。读法：README + 训练器源码（预设、INPUT_TYPES、损失约定）+ HF 模型卡；数字一律注明作者硬件。与 docs/11（Turbo LoRA）、docs/12（公开工作流）不重复。

## 本簇结论（10 行）

1. **角色一致性首选仍是「参考图路线」（Ref2VA 原生参考 / RefMod），角色 LoRA 是补丁不是主干。** 三方对照实验（grawwww-studio、masafykun、AcademiaSD）一致：LoRA 擅长固定「画风/造型语言」，脸的结构稳定性靠参考图；一次 LoRA 训练 40 min–3 h，RefMod 3 s。
2. **4090 24 GB 本地训 H3 LoRA 可行**，三个 Windows 训练器都能跑：Fizgig（int8 基座 + 单向块流，0.25 MP 静帧，rank 8–16）、AcademiaSD LoRAlab（NF4 基座，24 GB 不需块交换，576² 600 步 ≈ 40 min 级）、ai-toolkit（社区 12 GB 配方）。系统 RAM 比显存更常成为瓶颈：至少 32 GB，开预览 48 GB，masafykun 在 50 GB RAM 的 48 GB 显存机器上 3 次 OOM。
3. **视频片段训练在 24 GB 上只能低分辨率**（Fizgig：≤56 帧 0.5 MP / 73–124 帧 0.25 MP；AcademiaSD：192×192×124 帧），只适合学「运动/特效」，不适合学脸；脸用静帧 + 每段的最清晰脸帧。
4. **风格 LoRA 可用且便宜**：Fizgig「Style (LoRA 8)」预设、AcademiaSD 同一流程；现成的 Inner-Reflections 手绘动漫 LoRA 强度 0.75–1.25（叠 Turbo 时再加）；adf99 Anime Slider（2D 动漫 ↔ 写实双向滑杆）、Jojocodex Camera Motion 等见 Imagination Studio 的 LoRA Hub 清单。
5. **角色三视图**：matlod/minimax-h3-turnaround + `H3 Contact Sheet`/`H3 Contact Sheet Decode` 节点（现并入 ComfyUI-MAINodes），ref2va_pruned_int8 可用、28 步 res_multistep、强度 1.0（0.7 保真），一张参考图出 5 视图；不要把这个 LoRA 叠到普通视频生成上。
6. **提示词改写 LoRA 本地部署**：pytraveler/MiniMax-H3-Prompt-Rewriter-ComfyUI（ComfyUI Registry 可装，Windows portable 有命令），GGUF 路线 8B 版 ~6 GB 下载 / ~9 GB 显存、27B 版 ~10 GB / ~13 GB，能直接复用 Ollama 已拉的 GGUF；改写器只覆盖 T2VA/I2VA/L2VA/FL2VA，**不支持 Ref2VA**。
7. **训练必须配「去蒸馏训练适配器」**：Circlestone（图片优先，Fizgig 默认）或 Ostris（视频优先），否则 LoRA 先学「拆掉引导蒸馏」。所有训练器都遵守 H3 的反向约定：`t = 1 − σ`、速度目标 `x₀ − ε`、视频/音频双 shift；自己写训练脚本极易写反（IAmIronMan42 的 9 个坑）。
8. **训练-free 可控性**：ComfyUI-Dials 的 14 KB「拨盘」（运动量 −2…+2、情绪）可替代 H3 上无效的负面提示词，与 LoRA 叠加；LanPaint 的 H3 视频+音频局部重绘可修一镜里的一块区域而不重跑整段。
9. **多 GPU / 服务化对单卡 4090 用户基本无用**：raylight（USP+FSDP）Windows 要自编 NCCL、作者建议 WSL；LightX2V 面向 Linux 多卡服务；X-MinimaxH3 虽针对 4090 优化但许可证禁止使用/修改且仅 Linux/WSL2；Sac-Y 云插件绑定国内算力平台。
10. **别碰**：IAmIronMan42/MiniMax-H3-FineTuning（8×A800 专用、无 license、参考行未实现）；TenStrip Krea2 风格 LoRA（attn 嫁接实验品，仅 T2V）；fal realism LoRA（私有仓库读不到）；Mac 专用的 ltx-video-mac / Phosphene（不走 ComfyUI、不训 H3 LoRA）。

---

## 一、训练器

### shootthesound/Fizgig（★685，Apache-2.0，最后推送 2026-11-07）

- **定位**：Windows/Linux 一键桌面训练器（`install_fizgig.bat` / `Launch Fizgig.bat`），H3 是一等公民：静帧 + 短视频 + 声音同一文件夹混训，输出直接进 ComfyUI；附 Gizmo（切片/裁剪/人声切段/Whisper 转写）、Repair Studio（逐块 LoRA 手术）、RefMod 生成器、Helpers（第二台机器/第二块卡跑预览或分摊训练，实验性）。
- **核心机制（源码 `src/fizgig/families/minimax.py`、`docs/MINIMAX_H3.md`）**：训练基座就是 ComfyUI 的 `minimax_h3_fl2va_pruned_int8_convrot.safetensors`（pruned 把 AdaLN MLP 换成曲线表，LoRA 不碰它，所以「训在什么权重上就部署在什么权重上」）；int8 基座 + 单向块流（只 H2D，不回传，比往返交换快 6.4×）+ rintic-13 融合前向 / mabseyuk 融合反向 Triton 核。按空闲显存自动分级：~30 GB int8 不流；~22 GB int8 流 ~14 块；~15 GB 流 ~36 块；≤12 GB 用 4-bit。
- **预设（源码常量）**：`MiniMax H3 Fast (LoRA 8, 50 epochs)`：dim=alpha=8，automagic3 从 1e-6 起，0.25 MP，Training Structure=Likeness and Style，EMA 0.98，caption dropout 0.05；`rank 16, 60 epochs` 给大数据集；`Style (LoRA 8)` 去掉片段的清晰脸帧。adamw（全精度）被测为「单项最大相似度增益」，风格集优先试 adamw。
- **训练模式 = 块范围**：Default 训 20–49 块（相似度最快、保先验）；More Blocks 训 6–49（学运动概念用，更慢、伤运动先验）；**0–5 块任何模式都不训（会扭曲解剖、把数据集色调带进去）**；人声核心 38–48。`Train the text token refiner` 默认关（开了会软化输出）。
- **训练适配器**：Circlestone（默认，照片更清晰、更听提示；一个文件兼容 fl2va/ref2va）；Ostris（视频集学风格快 3×；fl2va/ref2va 两个文件）。只在训练时全强度挂载，预览和保存都不含。
- **片段规格**：`.mp4`、严格 24 fps、帧数 ∈ {5,22,39,56,73,90,107,124}、边长 32 倍数、音频 32 kHz 立体声或无轨；人声样本时长 ∈ {0.917,1.625,2.333,3.042,3.750,4.458,5.167 s}±25 ms。成本：22 帧 ≈ 7× 静帧/步，124 帧 ≈ 37×。**24 GB 卡可训：≤56 帧 0.5 MP；73–90 帧 0.25 MP；107–124 帧 0.25 MP**。
- **速度/资源（作者硬件）**：RTX 5090 int8 0.25 MP 静帧 ≈ 0.9–1.0 s/步（限 12 GB 时 9.9 GB 峰）；预览在 24 GB 卡自动钳到 22 帧（计划只留 ~4 GB）。系统 RAM 32 GB 起、开预览 48 GB；Windows 12 GB 卡必须让分页文件系统托管（否则错误 1455）。模型文件：pruned int8 DiT ~21 GB、qwen3vl_32b nvfp4 ~15.7 GB、视频 VAE 4.9 GB、音频 VAE 605 MB、`minimax_h3_turbo_v4_step600.safetensors` 780 MB（6 步预览用，强度 0.75）。
- **RefMod 生成**：Community recipe = 8 张 1 MP 纯编码（等同 MiniMaxH3Mod 自带提取器）；Fizgig lite = 16 张 0.5 MP + 200 步「冻结 H3 反向优化文件」，未见过的造型下明显占优；**RefMod 要按目标模型做（ref2va 做的在 fl2va 上掉分：60 vs 65）**；RefMod Studio 可在 ComfyUI 之前同种子 A/B 并复制节点参数。
- **对 4090 短剧流水线的价值**：目前唯一同时满足「Windows 一键、24 GB、照片+片段+人声、输出即 ComfyUI 格式、附带 RefMod 与逐块修复」的训练器。角色画风 LoRA、剧中反复出现的服装/道具 LoRA、以及「风格 LoRA」都能在 1–2 h 内出结果。
- **坑**：预览吃 RAM（先关 ComfyUI 再训）；多主体隔离在 H3 上只用照片；文档未给 4090 的 s/步，按 5090 ×1.5–2 估；Turbo 预览只在 6 步，判断相似度以 20 步预览或 ComfyUI 为准；ROCm 路线实验性。
- **评级：采用**。

### AcademiaSD/AcademiaSD_LoRAlab-TrainerStudio（★139，MIT，最后推送 2026-11-04）

- **定位**：多模型 Windows 训练器（Python 3.13 单 venv、`.bat` 启动、浏览器 GUI），H3 用作者自制 `AcademiaSD/MiniMax-H3-NF4`（41 GB，**generic 分区**，非 FL2VA/Ref2VA）训练，8–32 GB 显存档位。
- **核心机制（`docs/README_MiniMaxH3.md`、`scripts/2_train_lora_MiniMaxH3.py`）**：NF4 backbone + fp32 保留 `proj_in/audio_proj_in/time_embedder/proj_out/audio_proj_out/rope` 与调制路径；块交换带硬上限 `set_per_process_memory_fraction`，可「模拟」更小显存；冻结权重不回传（`nf4_cpu_home`）；训练时不加载文本编码器和 VAE（全离线缓存）；**LoRA 与优化器 fp32**（AdamW8bit 会抹掉面部细节的低幅分量）；sigma 用 logit-normal + 分辨率相关 `mu`，作者明确说「推理的 shift 12 用于训练会毁掉相似度」（与 IAmIronMan42 用 shift 12/3 训练相反，需自行 A/B）；导出做 diffusers→ComfyUI 键名翻译（含 `mlp.fc1` SwiGLU 半块交换、QKV 融合），与多个 Turbo LoRA 同载无键冲突。
- **验证配方（作者 RTX 5080 16 GB）**：图像 8 张 576²、600 步、lr 2e-4、rank/alpha 16、constant_with_warmup → 相似度好且听提示，3.7 s/it ≈ 37 min；**rank 8 相似度一样但开始无视提示（要海滩给卧室）**。视频 9 段 5.2 s、192×192、124 帧、600 步、lr 2e-4、rank/alpha 8 → 特效 LoRA 在 FL2VA 强度 1.0 复现，1 h 10 min。24 GB 卡：图像不需交换；视频 46 块常驻、~3.9 s/it。
- **音频训练结论**：LoRA 416 个张量全在共享块，纯音频训练在 `lr×steps ≈ 0.22–0.26` 处跨过阈值（700 步后音色完美但视频崩、提示失效）；要配 **30 段多样的锚片段（不含触发词，rank 16）**，锚必须是片段不能是静帧；weight decay 1e-4、caption dropout 0.05 能推后阈值。
- **RefMod 章节（约 20 次生成实测）**：参考按**模态分别计数、按位置匹配**（第 N 个视觉 mod = `<Subject N>`，第 N 个音频 mod = 其声音）；RefMod 与工作流原生参考共用一个编号；全部视觉在前、音频在后；多镜头提示里把所有角色放进第一镜，否则「强者通吃」；要么每个角色都有声音要么都没有；需要时间定位只能用 `MiniMaxH3AddGuide`（走 `minimax_keyframes`，不扰动编号）。另指出 MiniMaxH3Mod 提取器对视频用 `4k+1` 裁帧是错的（应 `17n+5`），视频 RefMod 可能被错裁，静帧不受影响。
- **价值**：8–16 GB 友好、文档数据最硬；对 4090 用户主要价值是「576² 图像 LoRA 40 min 基线」和音频/RefMod 实验记录。
- **坑**：预览质量极差（作者自己说只当进度条）；generic 分区训练的 LoRA 作用于标准 T2V 路径，Ref2VA 上未验证；需 CUDA 13.0 PyTorch + ffmpeg；Linux 无显存→内存溢出，要重校档位。
- **评级：试用**（作为 Fizgig 的对照/低显存备选）。

### inlineresearch/Inline-Studio（★未取得（API 受限），MIT，推送 2026-11）

- **定位**：Electron 节点式创作台（本地 + fal API），自带训练节点；H3 **只在静帧（可加短片段）上训**，不训音频。
- **机制（`core/src/inline_core/training/h3.py`、`TRAINING.md`）**：必须用 `minimax_h3_fl2va_bf16.safetensors`（62 GB）——pruned 版无时间步路径无法派生 AdaLN 因子化；基座恒为 4-bit（40 GB → 11.7 GB）；潜变量与标题分两趟缓存（fp32 视频 VAE 与 32B 条件器不能同驻）。24 GB 卡峰 20.6 GB；16 GB 卡条件器落 CPU、峰 12.7 GB 但每步 0.6 s → 16 s。L40S 512² 0.63 s/步、1500 步 ≈ 16–19 min + 7 min 启动。**Windows 把 62 GB 整体 mmap，64 GB 内存机器两块盘各 64 GB 页文件仍崩，各 128 GB 才行。**
- **价值**：有 24 GB 实测数字；但要下 139 GB、Windows 页文件要求苛刻，比 Fizgig 多付出很多。
- **评级：观望**。

### IAmIronMan42/MiniMax-H3-FineTuning（★106，无 license，最后推送 2026-08-10）

- **定位**：基于官方 Diffusers 集成的最小训练脚本（`prepare_cache.py` + `train.py`），生产规模：2000 段 ~30 s 片段、448×768、8×A800、LoRA + ZeRO-3。
- **可借鉴的硬知识（FIXES.md）**：① 时间步 `t = 1 − σ`（1 = 干净）；② 速度目标是 `x₀ − ε`（与 SD3/Wan 相反，写反则 loss 上升 7.2→9.5）；③ 零占位音频的 loss 乘 0 而不是跳过；④ 视频/音频按同一 `u` 过两条 shift 曲线（12 / 3）；⑧ `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` 必须在 import torch 前；全注意力 LoRA 的 8×80 GB 上限 ≈ 70k token/样本（448×768@27 s ≈ 65k）；LoRA r=16 作用于 `to_qkv/to_out.0/linear_1/linear_2`（10.7M 参数），lr 1e-5，7.5–8 min/步。
- **限制**：参考媒体尚未编码进条件序列（Ref2VA 微调不忠实）；无 shuffle；无 license。
- **评级：跳过**（仅作训练约定参考）。

### alisson-anjos/ai-toolkit · `research/tara-h3`（★9 fork，MIT，推送 2026-11-05）

- **定位**：TARA-H3 技术报告 v0.1.2（2026-10-23）：把参考视频的时间 RoPE 对齐到目标时钟、对目标→运动参考注意力加有界时间惩罚，实现「跟源表演走时序、身份/服装/风格换掉」的运动迁移，不走 AddGuide 路径。
- **与本簇关系**：不是角色 LoRA 方法；给出 `config/examples/train_h3_native_temporal.yaml` 训练路径与 FlexAttention/Flash 分区内核；作者自述 1000 步 TARA LoRA 设置有误已退役。另：**上游 ostris/ai-toolkit 原生支持 `MiniMaxAI/MiniMax-H3` 与 Ref2V 训练**，社区在其上有两个可复现配方（见补充）。
- **评级：观望**（运动迁移方向有价值，角色一致性无关）。

### 补充：社区 ai-toolkit / musubi-tuner 配方（GitHub 搜索补充）

- **sepiablue-ai/ai-toolkit-low-vram-lora-recipes**（MIT）：**Windows + RTX 4070 12 GB + 48 GB RAM**，Ref2VA pruned int8 ConvRot + qwen3vl nvfp4，Target 100 张 + 固定 Reference 3 张（脸 / 全身 / 中景换装，顺序固定），512 基准，rank/alpha 16，1000 步 **2 h 51 min，显存 ~7.4 GB，RAM 峰 30 GB**。分三进程缓存（Qwen-only → VAE-only → DiT-only）。标题用官方三字段格式（`integrated_multimodal_description: [Shot 1] …` / `overall_soundscape: N/A` / `non_diegetic_music: N/A`），**不写触发词、不写固定外貌**（身份交给参考图），不在正文写 `Picture 1`。
- **masafykun/minimax-h3-masafy-lora**（MIT，附论文）：原创动漫角色 12 张图，ai-toolkit，pruned int8 Ref2VA；**显存峰仅 3.96 GB，瓶颈是系统 RAM：50 GB 环境 3 次 OOM，188 GB 才完成**；800 步过头，**推荐 500 步、强度 0.6（平衡）/1.0–1.2（画风优先）**；训在 int8 的 LoRA 在 GGUF Q3_K_M 上 208 模块全部匹配；ComfyUI 接法 `UnetLoaderGGUF → LoraLoaderModelOnly → BasicGuider 与 BasicScheduler 都要接 LoRA 节点`；结论「参考图给结构，LoRA 给画风」。
- **grawwww-studio/refmod-vs-lora-consistent-character**（MIT）：同一角色三路对照——RefMod 3 s（4090）vs LoRA 46 min vs 参考图。第一版 musubi-tuner（19 张、500 步、lr 3e-4、rank 16、subject_ref teacher）几乎没改变脸；第二版 50 张 3000 步学成「类型」；第三版 Fizgig（24 张 + 18 段 H3 片段、rank 16、Automagic、40 epoch 取第 20、Circlestone 适配器、H100 43 min）最像但「油光」，用中期检查点 + 提示词「matte skin, plain window light」压回。规则：**永远先同提示同种子有/无 LoRA 对比再往下建**。
- **kohya-ss/musubi-tuner `docs/minimax_h3.md`**（Apache-2.0）：三种损失任选其一——训练适配器（最便宜）/ guidance loss（1.5× 成本、无需外部文件、可用 int8 基座）/ teacher matching（身份专用，`--h3_teacher_conditions subject_ref`）；默认 `--network_dim 16 --network_alpha 16 --blocks_to_swap 48 --block_swap_h2d_only --optimizer_type adamw8bit --learning_rate 1e-4`，目标模块 `attn.qkv_proj/out_proj/mlp.fc1/fc2`；文本编码器可 `--text_encoder_blocks_to_swap 50`；不支持 FP8/NVFP4 DiT；无 CFG。静帧 one-frame 模式标注「实验性」。
- **killkli/minimax-h3-lora-colab-skill**（Ref2VA on Colab A100 高内存，1000 步、rank 16、alpha 16、lr 1e-4）、**LoboForge/LoboRA**（DiffSynth 路线，2×H100 rank 32 1500–2500 步；概念 LoRA 建议 60–150 段 + 100–300 张；仅云端）、**chengyansen-ai/h3-multimodal-lora-training**（SimpleTuner 包装 + 审计脚本，README 工程）、**Kurumella/ComfyUI-GK-Nodes**（ComfyUI 内把长视频切成 17n+5 片段 + T2VA 标题的数据集构建节点，可配 Fizgig/AcademiaSD）、**veda-sparse/Miowtion**（2×4090 FSDP2 稀疏注意力预测器研究，非角色 LoRA）。

---

## 二、推理期可控性与杂项

### matlowai/ComfyUI-Dials（★42，AGPL-3.0，最后推送 2026-11-07）→ 后继 matlowai/ComfyUI-MAINodes（★240）

- **机制（`nodes.py`）**：对提示词对 (A,B) 各做一次文本编码、按 token 平均后取 B−A 再跨对平均；`inject=post_refiner` 时通过 ModelPatcher 对 `token_refiner.forward` 打补丁加向量（不改权重，与 LoRA/其它拨盘可叠）；`pre_refiner` 则写进 `condition_proj` 偏置的 `diff_b` LoRA 键，**stock `Load LoRA (model only)` 也能加载**。默认 Debias（去模板方向）+ Calibrate。
- **节点**：`Make Dial`（`A ||| B` 每行一对、`{subject}` 模板 4–8 个主体）、`Apply Dial`（强度 −∞…+∞，常用 −2…+2）、`Load Dial`（`models/loras/dials/`）、`Combine Dials`、`Save Dial`。发布的 Motion 拨盘：−2 ≈ 0.05× 运动（电影感静帧），+2 ≈ 2.5–3× 运动；另有 8 种「反派气质」。
- **价值**：H3 是引导蒸馏模型、**负面提示词无效**，拨盘补回这层控制；短剧里「这镜头少动/多动」「更阴冷」不用改 LoRA。MAINodes 增加 Dial Rack、从图片组做拨盘、随时间画强度曲线、`audio: protect`（保护台词）、Contact-Sheet 节点。
- **坑**：alpha 阶段，强度是在 Pika H3 Flex 6 步上测的；图片拨盘弱于文字拨盘；可能串味（psychedelic 带来锐舞服装）。
- **评级：试用**。

### zechengtang/VPack（★3，Apache-2.0，最后推送 2026-10-20）

- **机制**：对 Ref2VA 条件里的参考视频 latent 在时间轴按 chunk 相位丢 token（`COMPRESSION_PROFILES`：0/5 全留、2/5 留相位 (0,2)、3/5 只留 2），并在模型包装器里恢复保留帧的原始时间 RoPE；不改空间尺寸与生成 latent。节点 `VPack`（`model`+`positive`→`model`+`positive`，默认 `2/5`）。
- **数据**：1344×768、~4 s、4 步 Ref2VA（SM120）DiT 段提速 ~24%；仅一次测试。
- **坑**：**要求 ComfyUI ≥ 0.38.0（用户在 0.37.2）**；只对带参考视频的 Ref2VA 有用。
- **评级：观望**。

### scraed/LanPaint（★1483，GPL-3.0，最后推送 2026-09-28）

- **机制（`src/LanPaint/nodes.py`）**：检测 H3 的嵌套 (video, audio) latent 与 `minimax_h3_sigma_shift_video/audio`，音频行走自己的 shift 日程；对 ComfyUI ≥0.34 的逐 token denoise-mask 契约做了隐藏/兼容。节点：`LanPaint_VideoMaskEditor`（关键帧画遮罩、SDF 插值、音频区间、把遮罩写进 mp4 元数据）、`LanPaint_AVEncode`、`LanPaint_AVDecode`（边界混合 + 音频交叉淡入）。示例 864×480×124 帧，工作流 `example_workflows/MiniMax_H3_AV_EncodeDecode_Inpaint.json`。
- **价值**：一镜里只有一块坏（手、字、道具、某段台词）时局部重绘，保住其余画面与声音；比重抽整段便宜。
- **坑**：GPL-3.0；对长序列耗时显著增长；与 Turbo LoRA 的配合未在 README 给数字。
- **评级：试用**。

### komikndr/raylight（★477，Apache-2.0，最后推送 2026-11-04）

- **机制**：Ray worker 管多卡，USP（Ulysses+Ring）切序列、FSDP 切权重、CFG 并行；H3 注入 `usp_dit_forward/usp_block_forward`，并有 FP16 attention/MLP + FP32 残差、token 分块、时间 VAE 分卡解码。H3 专属节点：`RayMiniMaxH3SigmaShift`（12/3）、`RayMiniMaxH3SLA`（稀疏注意力，`sparsity_ratio` 0.90、`block_size` 64、`min_seq_len` 8192、`dense_last_steps` 1、`protect_audio` 默认开）、`RayMiniMaxH3FunControlNetApply`。
- **坑**：Windows 需自己编译 NCCL，作者建议「直接用 WSL 并软链模型目录」；要 `nvidia-nccl-cu12==2.28.9`；单卡无意义。
- **评级：跳过**（除非未来加第二块卡）。

### ModelTC/LightX2V（★2994，Apache-2.0，最后推送 2026-11-06；只读 `configs/minimax_h3`、`scripts/minimax_h3`）

- **机制**：Diffusers 权重 + AdaLN 缓存（改 `infer_steps/video_flow_shift/audio_flow_shift` 要重建）；配置族：单卡 BF16/FP8/INT8、`minimax_h3_block_offload.json`、`minimax_h3_sp.json`（4 卡 Ulysses）、`minimax_h3_tp.json`（TP2）、`fp8/minimax_h3_sp_5090.json`（**8×5090 SP8 FP8 768×1344×362 帧**）、DMD 4/8 步、decache、shared_offload；服务端 `start_server(_parallel).sh` + `post_*.py`。LoRA：量化 DiT 必须 `lora_dynamic_apply: true`；Turbo 4 步示例 `infer_steps 4, video_flow_shift 6.0, audio_flow_shift 3.0, h3_step_update training_euler, alpha 128`。帧数对齐 `17n+5`、124–362。
- **价值**：数字和 shift 约定可反查（4 步 Turbo 用 shift 6/3 而非 12/3）；Prompt Rewriter LoRA 出处。
- **坑**：Linux/多卡取向，Windows 文档为 `requirements_win.txt` 级别；与 ComfyUI 不是一套。
- **评级：观望**（只取参数，不部署）。

### PullMyBoots/X-MinimaxH3（★130，NOASSERTION，最后推送 2026-09-12）

- **定位**：专为单张 4090（SM89）优化的本地 H3 服务（Web 控制台 + REST）：W4A8/INT8、FL2VA/Ref2VA、SelfLift（小画布首段 → 学习型 3D 潜变量放大 → 最高 1440p 收尾）、1–300 s 长视频、自动人脸修复、LightX2V Turbo LoRA（4 步 v1.1 / 8 步 v1.0 shift 6/3，Ref2VA 4 步 shift 12/3）；作者机器 i9 + 128 GB RAM + 4090。
- **坑**：**LICENSE 明文「源码可见，但未经书面许可不得使用/复制/修改/分发」**；仅 Linux x86-64 / WSL2，CUDA 13.0 PyTorch + CUDA 13.3 工具链；非 ComfyUI（仅可选 HTTP 连接器）。
- **评级：跳过**（许可证与平台双重不合）。

### Sac-Y/MiniMax-H3-Cloud（★243，MIT，最后推送 2026-09-22）

- Codex 插件：在优云智算（CompShare）租 GPU、起 ComfyUI Runtime、提交 T2V/首尾帧/参考图工作流、下载 MP4、任务结束关机（30 min 兜底）。依赖 Node 20、ssh、ffprobe、CompShare CLI。
- **坑**：绑定中国算力平台与账号；用户在澳洲且不能用国内服务。**评级：跳过**。

### MiniMaxH3ComfyUI/MiniMax-H3-ComfyUI

- 本会话 GitHub API 与 raw 均 404/受限，无法读取。**未读**（见文末）。

### drowzeys/Imagination-Studio-by-keys-Wasserman（★615，Apache-2.0，最后推送 2026-11-07，略读）

- Mac/DGX Spark 影视工作台（TensorFold 引擎，非 ComfyUI）。**有价值的是 `docs/lora-guide.md` 的公开 H3 LoRA 清单**：Jojocodex Camera Motion / Spatial Physics / Wushu Action（Apache-2.0）、adf99 Anime Slider（+2D 动漫 / −写实）、DiffSynth Lineart Anime（线稿上色）、JOKER141 Motion Continuity Repair / Combat Base V2 / Weapon Combat、vpakarinen Natural Face Speech（Apache-2.0）、KennethFal VH5 Tape、matlod Turnaround、akatz Character Swap / Person Remover、dntpi Video Upscaler LoRA。LoRA 训练只在 DGX Spark 上（musubi-tuner f8a1b03 + Ostris 适配器 v2，928×512×124 帧 **110 s/步，1000 步 ≈ 30 h**）。**评级：观望**（只抄清单）。

### james-see/ltx-video-mac（★451，MIT）与 mrbizarro/Phosphene（★310，MIT）（略读）

- 前者 SwiftUI Mac 应用，H3 走 `antirez/h3.c` Metal 实现（含 int8 与折叠 Turbo 6 步），与 ComfyUI 无关；后者 Pinokio Mac 应用，H3 仅推理，「角色 LoRA 训练」是 **LTX-2 的**，不是 H3。**评级：跳过**。

---

## 三、HuggingFace 模型卡

### matlod/minimax-h3-turnaround（Contact-Sheet 三视图 LoRA）

- 把 5 个独立图像 latent 塞进 5 位视频 latent 的位置、拉伸时间坐标让模型以为是一镜，借「时间一致性」做跨视图身份一致。三个文件：`five_view_512_s1500`（默认，转角最好）、`512_s400_instruct`（更听「neutral studio background」等指令，转角浅）、`1024cont_s600`。**rank 16、仅注意力（qkv/out，50 块 100 模块，63 MB）、`ref2va_pruned` 分区**；强度 1.0 转角 / 0.7 保真；训练：90 段自生成环绕片段（30 主体×3 种子）、lr 5e-5、adamw8bit、Ostris 适配器、512² 1500 步 ≈ 2.8 h。
- **ComfyUI 用法**（`ComfyUI-H3-ContactSheet`，已并入 MAINodes）：`UNETLoader(ref2va pruned int8) → LoraLoaderModelOnly → BasicGuider`；`H3 Contact Sheet`（prompt + 参考图 + 每视图尺寸 → cond + 五槽 AV latent，参考图在提示里写 `<Picture 1>`）→ `SamplerCustomAdvanced`（`res_multistep`/`simple`、28 步、denoise 1.0）→ `H3 Contact Sheet Decode`（五槽独立解码 + 拼条）。RTX PRO 6000 上 512 ≈ 25 s、2048 ≈ 175 s；**消费卡靠 ComfyUI 的 RAM 卸载可跑（计算量 ≈ 17 帧片段），RAM 需 ~50 GB 镜像**。
- **禁忌**：不要把它叠在普通视频生成上（风车叶片会变离散叠影）；旋转轴跟随主体朝向，提示里写明起始视角；2048 时转角后置。
- 替代：`lumosai8/ComfyUI-OrbitSheets`（不用 LoRA，靠「5 个硬切锁定机位」的多镜头提示 + 视觉模型选帧，顺带给人声样本）、`muse-collective-26/Muse-CharacterSheet-H3`（Ref2VA 六段式提示 + 8 参考图，Windows 安装器，可接 RefMod）。

### fal/research-mini-max-h3-realism-people-lora

- 私有/受限仓库（`Invalid username or password`），**未读**。

### Inner-Reflections/MiniMax-H3-Looping-Sketch-Anime

- 循环动漫手绘风格 LoRA；**强度 0.75–1.25，叠 Turbo 时再加**；推荐提示："A hand-drawn 2D anime art style characterized by rough, textured outlines, coloring technique is minimalist, utilizing flat colors and white outline"（去掉 anime 变西式草图）。无训练参数。

### TenStrip/Krea2-H3-Style-Lora

- Krea2 attn K/V 嫁接的提取结果，rank 512 只捕获 52% 的 delta，**仅对纯 T2V 有效**，作者自称全实验性。**跳过**。

### lightx2v/MiniMax-H3-Prompt-Rewriter-LoRA-8B（及 27B 版）

- 8B：Qwen3-VL-8B-Instruct 上的 PEFT LoRA，支持 **T2VA / I2VA / L2VA / FL2VA**（可看首尾帧），**不支持 Ref2VA**；`infer.py --greedy` 决定性改写，输出三段式（时间线镜头 + 同步音景 + 非叙事音乐）。27B 版基于 Qwen3.6-27B，仅文本 T2VA。
- **本地部署路径**（pytraveler/MiniMax-H3-Prompt-Rewriter-ComfyUI，★420，MIT，ComfyUI Registry `darkil/minimax-h3-prompt-rewriter`）：节点 `MiniMax-H3 Prompt Rewriter`（27B）/ `Rewriter 8B (sees frames)` / `Universal Rewriter`；Transformers 路线 nf4 ≈ 16 GB 显存、int8 28 GB；**GGUF 路线无需 pip**：8B GGUF ~6.1 GB 下载 / ~9 GB 显存，27B GGUF ~10 GB / ~13 GB；自动拉 llama.cpp 官方二进制（Windows CUDA 511 MB，SM 8.6/8.9/12.x 原生）；`keep_model_loaded=False` 默认用完即释放显存给视频生成；**自动识别 `~/.ollama/models` 里已有的 GGUF（直接读文件，不需 Ollama 服务运行）**。还有 2.6 GB 的「Writer」节点走系统提示而非 LoRA，8 GB 卡用这个。

---

## 四、「短剧角色一致性：参考图路线 vs 角色 LoRA 路线」决策建议

| 维度 | 参考图路线（Ref2VA 原生参考 / RefMod） | 角色 LoRA 路线 |
|---|---|---|
| 成本 | RefMod 3 s（4090）；每段生成多付参考 token 的注意力成本 | 静帧 LoRA 40 min–2 h（24 GB）；推理零额外成本 |
| 脸/结构稳定 | 强（三方实验一致） | 弱到中（19–50 张图的三次尝试里只有 Fizgig+适配器那次「最像」，且偏油） |
| 画风/造型语言 | 弱（会被提示和基座拉回写实） | **强**（masafykun：LoRA 决定「平涂插画 vs 写实毛发」） |
| 多角色 | 可，但编号/模态规则复杂（AcademiaSD 实测） | 每角色一个触发词；Fizgig 双主体一文件 |
| 跨集复用 | 定妆图库即可 | 需维护 LoRA 版本与强度 |
| 失败模式 | 多镜头里强参考「通吃」；参考 token 拖慢 | 过训崩音视频、学成「类型」、油光 |

**建议**：
1. **默认：参考图 + RefMod**。每段带同一组定妆图（≤9 图）或等价 RefMod；只在「同一角色要在几十段里保持一种非写实画风」或「参考图总是被基座拉回写实」时加 **风格/画风 LoRA**（强度 0.5–0.8，叠 Turbo 再加 0.1–0.25）。
2. **角色 LoRA 定位为「画风 + 固定造型」而非「脸」**：训练集 15–30 张多角度、多景别、多服装的静帧（+ 可选 6–18 段 22–56 帧的 H3 自生成片段），Fizgig Fast 预设（rank 8，50 epoch，0.25 MP，Circlestone 适配器），取中后期检查点，推理强度 0.6–0.8，**与参考图同用**。
3. **三视图/定妆图**用 matlod turnaround + Contact-Sheet 节点或 OrbitSheets 生成，再回灌为参考图；不要指望文字分别生成 5 个角度。
4. **任何 LoRA 上线前**：同提示同种子有/无 LoRA 各出 2 条，看脸、看运动、听台词（LoRA 可能伤音频）。

---

## 可写进 skill 的规则

1. 角色一致性默认走 Ref2VA 原生参考或 RefMod；角色 LoRA 只用于固定画风/造型，并与参考图叠加使用。（grawwww-studio、masafykun、AcademiaSD）
2. 在 4090 上训 H3 LoRA 用 Fizgig：基座选 `minimax_h3_fl2va_pruned_int8_convrot.safetensors`，Blocks Swap 与 Base Precision 留 Auto，先关闭 ComfyUI 再启动训练。（Fizgig）
3. 角色静帧 LoRA 从预设「MiniMax H3 Fast (LoRA 8, 50 epochs)」起步：dim=alpha=8、automagic3 起始 lr 1e-6、0.25 MP、Likeness and Style、EMA 0.98、caption dropout 0.05；数据集 >40 张或要兼顾提示遵从时改 rank 16。（Fizgig；AcademiaSD 指出 rank 8 会丢提示遵从）
4. 训练适配器：照片集选 Circlestone，片段集选 Ostris；绝不在训练时同时用 CFG/guidance-preservation 损失。（Fizgig、circlestone 模型卡）
5. Training mode 用 Default（块 20–49）；只有训运动概念才用 More Blocks（6–49）；永远不训块 0–5；不要勾选「Train the text token refiner」。（Fizgig）
6. 训练片段必须 `.mp4`、24 fps、帧数 ∈ {22,39,56,73,90,107,124}、边长 32 倍数、音频 32 kHz 立体声或无轨；用 Gizmo 切片而不是手工 ffmpeg。（Fizgig）
7. 24 GB 卡上片段训练上限：≤56 帧 0.5 MP，73–124 帧 0.25 MP；片段只用来学运动/特效，脸靠静帧和「每段最清晰脸帧」。（Fizgig、AcademiaSD）
8. 系统 RAM：训练 ≥32 GB，开预览 ≥48 GB；Windows 分页文件设为系统托管；RAM 不足时表现为「CUDA out of memory」或进程无声退出，不要误判为显存不足。（Fizgig、masafykun、Inline-Studio）
9. 训练中预览在 24 GB 卡钳到 22 帧；判断相似度以 ComfyUI 内 20–25 步正式出图为准，不用 Turbo 预览定稿。（Fizgig、AcademiaSD）
10. 纯音频/人声 LoRA 不要训；若要带声音，必须混入 ≥30 段多样化、不含触发词的锚片段并用 rank 16，`lr×steps` 控制在 0.22 以下，weight decay 1e-4。（AcademiaSD）
11. 角色 LoRA 推理强度：画风优先 1.0–1.2，平衡 0.6–0.8；检查点取训练中后段（masafykun 800 步配方取 500 步；grawwww 40 epoch 取第 20）。（masafykun、grawwww-studio）
12. ComfyUI 接 LoRA 用 `LoraLoaderModelOnly`，且 `BasicGuider` 与 `BasicScheduler` 都要接 LoRA 之后的 model 输出，否则两者静默使用不同模型。（masafykun）
13. 自训 LoRA 与 Turbo LoRA 可同时加载（AcademiaSD、Fizgig 均验证无键冲突）；叠 Turbo 时风格 LoRA 强度再加 0.1–0.25。（AcademiaSD、Inner-Reflections）
14. 手绘动漫风格直接用 `Inner-Reflections/MiniMax-H3-Looping-Sketch-Anime`，强度 0.75–1.25，提示词含 "hand-drawn 2D anime art style, rough textured outlines, flat colors, white outline"。（HF 模型卡）
15. 需要「更 2D ↔ 更写实」连续调节时用 adf99 Anime Slider（正值 2D、负值写实）；运镜缺失用 Jojocodex Camera Motion（Apache-2.0）。（Imagination Studio LoRA Hub）
16. 角色三视图：ref2va pruned int8 + `matlod/minimax-h3-turnaround` 的 `five_view_512_s1500` + `H3 Contact Sheet`/`H3 Contact Sheet Decode`，`res_multistep`/`simple`、28 步、denoise 1.0、强度 1.0（要背景干净改用 `_s400_instruct` 并加 "neutral studio background"）；提示里保留 `<Picture 1>`。（matlod 模型卡、ComfyUI-H3-ContactSheet）
17. 禁止把 turnaround LoRA 留在普通视频生成图里（会把运动变成离散姿态叠影）。（matlod 模型卡）
18. 本地提示词改写：装 `pytraveler/MiniMax-H3-Prompt-Rewriter-ComfyUI`，选 `[gguf]` 的 8B 条目（~6 GB 下载、~9 GB 显存），`keep_model_loaded=False`，`llama_backend=auto`（Windows 自动取 CUDA 二进制）；已有 Ollama 模型会自动出现在 `writer_model` 下拉。（pytraveler）
19. 改写 LoRA 只用于 T2VA/I2VA/L2VA/FL2VA；Ref2VA 六段式提示不要经过它改写。（lightx2v 模型卡）
20. 想要「少动/多动」「更冷/更邪」而不改 LoRA 时，用 ComfyUI-Dials 的 `Load Dial`+`Apply Dial`（Motion 拨盘 −2…+2），不要写负面提示词（H3 无 CFG，负面提示无效）。（ComfyUI-Dials）
21. 一镜中局部出错（手、字、道具、某句台词）用 LanPaint 的 `LanPaint_VideoMaskEditor → LanPaint_AVEncode → 采样 → LanPaint_AVDecode` 局部重绘，而不是整段重抽。（LanPaint）
22. 多个 RefMod/参考同用时：视觉在前、音频在后、按模态分别计数（第 N 个视觉 = `<Subject N>`）；多镜头提示把所有角色放进第一镜；要么每个角色都给声音要么都不给。（AcademiaSD）
23. 做 RefMod 时按目标模型分别生成（ref2va 用 / fl2va 用各一份）；视频 RefMod 慎用 MiniMaxH3Mod 自带提取器（`4k+1` 裁帧与 `17n+5` 不符），静帧不受影响。（Fizgig、AcademiaSD）
24. 任何 LoRA 上线前，同提示同种子有/无 LoRA 各出 2 条做盲测，再决定强度与检查点。（grawwww-studio）
25. 不要用 shift 12/3 以外的推理 shift 训练；若用 LightX2V 4 步 Turbo 推理，shift 改 6/3 且量化 DiT 必须 `lora_dynamic_apply: true`。（LightX2V、IAmIronMan42）
26. 单卡 4090 不装 raylight / LightX2V 多卡服务；X-MinimaxH3 因许可证（禁止使用/修改）与 Linux-only 直接排除；Sac-Y 云插件绑定国内平台不适用。（raylight、X-MinimaxH3、Sac-Y）
27. VPack 仅在 ComfyUI ≥0.38 且 Ref2VA 带参考视频时考虑，压缩档 2/5。（VPack）
28. 数据集 clip 切分可用 `Kurumella/ComfyUI-GK-Nodes` 的 `GK H3 Dataset Builder`（17n+5 对齐 + T2VA 标题）在 ComfyUI 内完成。（GK-Nodes）

## 未覆盖/未读完

- `MiniMaxH3ComfyUI/MiniMax-H3-ComfyUI`：GitHub API 与 raw 均不可访问（404/会话受限），未读。
- `fal/research-mini-max-h3-realism-people-lora`：HF 私有/受限，模型卡读不到。
- `alisson-anjos/ai-toolkit` 的其它 H3 分支（`feat/h3-source-photo-conditioning`、`minimax-h3-latent-guides`、`scanpe-h3-continuity`）只看了分支名。
- `ostris/minimax_h3_training_adapter` 模型卡为空；`AkaneTendo25/musubi-tuner` H3 fork（Vast.ai 镜像 `Norian11/musubi-h3-vastai`）未能访问。
- Fizgig 的 `docs/FINETUNE.md`（全量微调，24 GB NF4 可跑）、`TRAINING_SHARE.md`（双卡分摊训练）、`MASKED_TRAINING.md` 只读了摘要；AcademiaSD `docs/README_MiniMaxH3.md` 的 Settings reference 段未逐项读。
- Imagination Studio LoRA Hub 中各 LoRA 的 HF 模型卡（adf99 Anime Slider、Jojocodex Camera Motion 等）未逐个核对训练参数与许可证。
- raylight `docs/` 下 USP/FSDP 开发文档、LightX2V `scripts/minimax_h3_roll`（低分辨率草稿→候选→高分辨率重生成）未读。
