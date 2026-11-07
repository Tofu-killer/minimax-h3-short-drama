# 06 · 画质与可控性：latent 超分 / 精修 / 人脸修复 / 音频 / 单帧出图与角色设定图 / ControlNet / 换人换物

> 调研日期 2026-11-07。27 个仓库全部浅克隆到本地并打开节点源码（INPUT_TYPES、默认值、sigma 表、noise_mask 处理）与示例工作流 JSON 逐一核对；所有耗时/显存数字均注明作者硬件。星数/推送日期来自 relevant.json（ResCascade 不在索引中）。

## 本簇结论

1. **立刻采用**：`LBH-123-AI` 3D latent 放大器（事实标准，ResCascade/Open-H3-Regenerate/T8/CGlide/bbaudio 全部复用它）+ `tazmannner/ComfyUI-H3-ResCascade` 的 **σ 0.45 起点、DMAD 0.8 二步精修、音频钉死** 配方：1 MP 草稿 → 1920×1088，成片是同一个 take，代价约 +1 分钟（5090）。这是 4090 上最稳的「草稿→成片」路线。
2. **立刻采用**：`Carasibana/ComfyUI-H3-FaceRefine`（远景小脸修复，denoise 0.40 + 逐帧衰减 0.35，配 NativeAudioLock 保口型）；`badgids/ComfyUI-H3-ExactAudioLock`（TTS 对白逐帧精确锁定、与 AddGuide 同帧）；`shootthesound/ComfyUI-Fizgig-H3-Still`（真单帧剧照 ≥3 MP）；`matlowai/ComfyUI-MAINodes` 的 **Contact-Sheet 五视图**（一张参考 → 角色三视图，28 步）。
3. **试用**：`bbaudio-2025/Comfyui-MMH3-UltimateUpscale`（24 GB 显存下 10–15 s 长片的分块二采，音频不重采）；`Adudeguyman/ComfyUI-H3-AudioRefine`（4 步 Turbo 画面 + 6 步纯音频精修）；`tazmannner/ComfyUI-H3-RelayHires`（二维动画专用，0.5 MP→1920 仅 ~118 s/5 s，真人改接 RealESRGAN_x2plus）；`lumosai8/ComfyUI-OrbitSheets`（硬切五视图 + 配音样本）；`wyzborrero/ComfyUI-H3-FunControl` 的实测结论（核心已内置节点，用其参数）。
4. **观望**：`rdh9616/ComfyUI-Open-H3-Regenerate`（NVIDIA 三步 2K 重生成：12.4 GB LoRA + 6.5 GB 快速 VAE，σ 0.909 会改脸，16 GB 卡 5 s 片要 1 小时；4090 可跑 1080P 但不如 ResCascade 保真）；`hashu786/ComfyUI-Tessera`（4785 行单文件、依赖 SAM3/Qwen-Image，适合 4K 交付而非短剧日常）；`T8mars` 全家桶（只挑 Still/Five-View/Speech/Audio 节点用，别整包依赖）；`slmonker/selflift-Avatar`、`Luisacaotica/MiniMaxH3Mod`、`thaakeno/H3-Studio`（alpha，自带 GoatCounter 遥测）。
5. **别碰 / 低价值**：`lihaoyun6/Ref-Patch`（用户已有 int8 Ref2VA，148 MB 差分补丁打在量化 FL2VA 上收益不明）；`Tr1dae` 的学习型路径（依赖另一个 Mamad8 节点包提供网络代码、硬锁 2×、无 license）；`NyckM` 相机重控（需 bf16 FL2VA 全量或 Meridian INT8 全套）；`D3voz/openjutsu`（换人是 Web 应用 + 12 个节点包，短剧用不上整套）；`maosika-ai/reshot` 只是 pip 预处理器，可按需用。
6. 共识性禁忌：**不要在 Turbo 一采后从 σ≈0.9 重采**（重新决定整条片子，LBH 示例的 0.9035 仅适合「抽卡→换尺寸再抽」）；**二采音频一律钉死**（noise_mask 音频 0）；**LoRA 文件必须是带 alpha 处理的 `comfyui_alpha8`/官方 `_comfyui_bf16`**（T8 实测缺 alpha 的版本把 LoRA 放大 16 倍整幅融化）；Sol-Attn 的 `morton` 必须关；3D 放大器处理 >32 latent 帧会走时间分块，首帧可能出字形伪影（selflift 用 reflect padding 修复）。

---

## 一、768P 草稿 → 1080p/2K 精修的几条路线

| 路线 | 核心机制 | 二采起点 / 步数 | 音频 | 作者硬件耗时 | 4090 评价 |
|---|---|---|---|---|---|
| **A. LBH 学习型 latent 放大 + 重采**（LBH 示例） | 0.2 MP 4 步 → 3D 放大到 1.0 MP → 3 步 euler | ManualSigmas `0.9035, 0.6316, 0.3158, 0`（近乎重生成） | 分离后原样拼回，二采时音频也被重噪（示例未锁） | 未给 | 只适合「低清抽构图、高清再抽一次」，成片会变 |
| **B. ResCascade H3 Hires Fix** | 1 MP 原生 20 步 → LBH 3D 放大 → beta57 尾段 | σ 0.45 起，原生 4 步或 DMAD 0.8 ×2 步 | **钉死一采音频**（sample for sample） | 5090：1 MP 178–194 s，+59–69 s 到 1920×1088；1440p 337 s（32 GB） | **首选**，同 take，+29% 细节 |
| **C. RelayHires**（2D 动画） | 0.5 MP 20 步 → AnimeSR 像素放大 → taeh3 编码 → 1 步 DMAD | σ 0.60，1 步，窗口注意力 4/锚 8 | 钉死 | 5090：5 s 片 ~118 s（原生 1920 ~500 s，路线 A ~240 s） | 动画短剧次选；真人换 RealESRGAN_x2plus |
| **D. Tr1dae 2× 重噪二采** | 硬锁 2× 学习型/插值 → CONST 重噪 → DisableNoise 二采 | σ 0.25–0.45 起（作者强调不要从 ~1 起），4 步 karras rho 7 | `audio_denoise` 0 或 1，不取中间值 | 未给 | 思路正确但依赖 Mamad8 包，建议用 B 代替 |
| **E. bbaudio UltimateUpscale / LBH Split Upscale** | 时间分块 + 3D 放大 + 空间分块逐 tile 重采 | 示例 `simple 1 步 denoise 0.2`（sa_solver）；chunk 85/17 帧，tile 512/128 | **永不重采音频** | 24 GB 建议 tile 576–768、chunk 136–170 帧 | 10–15 s 长片 OOM 时的保底 |
| **F. Tessera 分块精修** | 逐 tile 独立条件 + 时间分块 + 流式 VAE | sigmas `1.0, 0.7, 0.4, 0`（1 步 turbo 头 + 2 步 euler 尾），二跳 `1.0, 0.923, 0.55, 0` | 未精修 | 544p→1080p 124 帧 4 tiles 7m04s（GPU 未注明） | 4K/8K 交付才用 |
| **G. Open-H3-Regenerate 三步 2K**（NVIDIA） | LBH 放大到目标网格 → 重噪 σ 0.909375 → 3 步 euler + 合并 LoRA + 50 条 Sharp 曲线分支 → 快速 VAE | `0.909375, 0.857, 0.667, 0`；保守 `start_sigma 0.8` | 模型内音频=静音，成片外挂一采原声 | RTX PRO 5000 72 GB：5 s 768P→2K 精修 122 s（Sol-Attn）/474 s（dense），快速解码 24 s 峰值 21 GB；T8 在 4060Ti 16 GB 上 3700 s | 画面「重生成」而非保真，小脸会漂；4090 做 1080P 可试，2K 慢 |
| **H. 像素级 SR**（RelayVSR via MAINodes；RealESRGAN；SeedVR2 见其它簇） | 解码后像素超分 | — | 不动 | RelayVSR 需独立 LightX2V venv，X4 模型优于 X2 | 不增加 H3 细节，只放大；作为最后一跳 |

---

## 二、逐仓库

### LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler（★824，MIT，最后推送 2026-09-17）
- 定位：H3 24 通道 latent 的**学习型**空间放大器（2D ResBlock+时间卷积 / 纯 3D 卷积两种），绕开 5B 参数 VAE 的解码-重编码；~8 万对训练样本，2× 占 40%，支持 1.0–4.0× 任意倍率。被 ResCascade、Open-H3-Regenerate、bbaudio、T8、CGlide、WhaleTrans 全部复用，是事实标准。
- 源码：`nodes/minimax_h3_latent_upscaler_3d.py`，默认架构 in_blocks=12/out_blocks=12/base 512/temporal_kernel 5，attn 关闭；`enable_temporal_chunking` 时 chunk=32 latent 帧、overlap=时间核（replicate padding，加权融合）；宽高独立对齐 `align`（默认 32）；`force_unload` 推理后卸到 CPU 给二采腾显存。权重 `minimax_h3_latent_upscaler_3d_{fp16,bf16}.safetensors`（691 MB）/ `fp32.pth`（1.38 GB）放 `models/latent_upscale_models/`。
- **3D 节点必须配 `LTXVSeparateAVLatent` → 只喂 video_latent → `LTXVConcatAVLatent` 把音频原样拼回**（README 中文版红字强调，否则破坏音频）。
- 示例工作流（i2v）：一采 ResolutionSelector 0.2 MP（608×352）、`SplitSigmas 4` 取 simple 8 步前 4 步、turbo 4-step v0.1、shift 12/3；放大 `target dimensions` 到 1.0 MP；二采 **重新在高分辨率构建 MiniMaxH3ImageToVideo 条件**，ManualSigmas `0.9035, 0.6316, 0.3158, 0` 3 步 euler、同 seed 42。README 明说「省时间不省显存」。
- 附带 **MMH3 Split Upscale** 三节点组合（从 bbaudio 拆解优化）：Temporal 默认 chunk 73 帧/overlap 22/anchor 0.999/motion anchor 22/identity anchor 24；Spatial tile 512、overlap_ratio 0.25、fade 0.5、`seam_denoise` 1.0（建议 0.5–0.8 防快动作断肢）；主节点 `seam_polish` off/auto/all、`color_match` 两级颜色匹配；只接外部预放大 latent。
- 价值：4090 上所有 latent 路线的底座。坑：Pass-2 从 0.9 起会换 take（ResCascade 实测）；>32 latent 帧的分块路径在 selflift-Avatar issue #5 被发现会在首帧生成字形伪影（原因 replicate padding 把因果首帧复制 6 次）。
- 评级：**采用**（节点 + fp16 权重）；示例工作流的 sigma 仅作参考。

### Tr1dae/ComfyUI-MiniMaxH3_LatentUpscaler（★282，无 license，最后推送 2026-08-17）
- 定位：固定 2× 的 latent 放大 + NestedTensor 感知的 CONST 重噪，一个 `Latent Upscale Combined` 节点同时输出放大后的 latent 与**同步放大了 `minimax_refs`/`minimax_keyframes` 的 conditioning**（Ref2VA 必须重建 Guider，否则身份 warp）。
- 机制：video 流按 `sigmas[0]` 做 `noise_scaling + inverse_noise_scaling`，二采用 DisableNoise + 相同低 sigmas；`audio_denoise=0` 时音频零噪声且 noise_mask 0（一采音频锁死），=1 全重混，**不要用中间值**。学习型模型 `h3_clean_latent_upscaler_film_epoch200.safetensors`（Tridae/H3LatentUpscaler，自动下载到 `models/h3_latent_upscalers/`）**但网络代码从兄弟包 `ComfyUI-H3-Latent-Upscaler-Mamad8` 动态 import**，且用 legacy ModelPatcher 绕开 DynamicVRAM。
- 作者实测结论（值得记）：bilinear/bicubic/普通 blur 会让 24 维 token 范数坍缩（边缘处 19–99% token 低于均值 70%），二采在那里「发明」细丝/乱发；要用 `nearest-exact`/`bislerp` 或学习型；**二采起点 σ 0.25–0.45**，别用整条从 ~1 起的表；不要缩放噪声张量来「少去噪」；karras/exponential 在同 denoise 下 `sigmas[0]` 远低于 normal 会悄悄欠去噪——`Pass-2 Staggered Scheduler` 用 normal/8/0.45 找 sigmas[0]，再 karras rho 7 走 4 步。
- 附赠：`MiniMax H3 VAE Decode (fast)`（原生 decode 固定 256px tile 且每个时间块写回 CPU，这里可选 GPU 输出、更大 tile）、Save/Load Package 日/夜分离（白天低清抽卡存 latent+cond，晚上批量高清）、Latent Blur/Sharpen/Contrast（范数保持）。Chunked pass-2 因跨块不一致**未注册**。
- 坑：无 license；硬锁 2×；依赖第三方包；更新停在 8 月。
- 评级：**观望**（读其结论，节点用 ResCascade 代替）。

### bbaudio-2025/Comfyui-MMH3-UltimateUpscale（★254，MIT + tiled_diffusion GPLv3，最后推送 2026-10-07）
- 定位：一个节点跑完「时间分块 → latent 放大 → 空间分块 → 逐 tile 采样 → 空间拼接 → 时间拼接」，**峰值显存≈单 tile**，音频流全程不重采。
- 机制：首帧锚（`anchor_strength` 0.999，前块重采后的边界帧替换本块 keyframe）、重叠交叉淡化、tile 重叠区预填已拼接结果并 noise_mask 冻结、`overlap_blend` linear/smoothstep/overwrite/midpoint、`brightness_match`、`dynamic_fade` narrowing/widening（0831 新增）。3D 放大器与扩散模型互斥驻留（放大时卸载 H3）。`MMH3 Tiled Diffusion`（0923）在每步内分 tile 共享 sigma，用全局 RoPE 位置（v1.1 修复各 tile 自成一帧），overlap ≥25% tile；`Fun ControlNet Inpaint` 需合并 kijai PR #15860。
- 示例 `basic.json`：一采 ref2va pruned int8 + fl2v turbo 4step v1.1 768p、864×480（0.4 MP）、euler_ancestral simple 4 步；二采 **BasicScheduler simple 1 步 denoise 0.2、sa_solver**，放大到 1280×704；Temporal 85/17/0.999；Spatial tile 512×512 overlap 128 fade 64，或 `specific_size 864×480 2×2`。`upscale_an_existing_video.json` 用 VideoTemporalCrop + VAEEncodeAudio 把现成 mp4 编回 AV latent。
- 显存表（量化底模）：8 GB tile 320–384/chunk 34–68；16 GB 512–576/102–153；**24 GB tile 576–768、chunk 136–170 帧**；冗余系数 (tile+overlap)/tile² ≈1.56，时间 ≈1.13。只接受 `.safetensors` 放大权重（CVE-2025-32434）。
- 坑：denoise 0.2 单步只「增强」不重绘；高 denoise 需 dynamic_fade/brightness_match；作者自述 vibe-coded。
- 评级：**试用**（10–15 s 长片在 4090 上做 1080p 的保底方案）。

### hashu786/ComfyUI-Tessera（★99，MIT，最后推送 2026-11-06）
- 定位：面向 2K/4K/8K 交付的分块精修器：每个 tile 用**自己裁剪的视频参考 + 图像参考 + 重新编码的文本**做条件（不是邻 tile 冻边），流式 VAE 编解码让全分辨率像素序列不落显存。9 个节点，`tessera/nodes.py` 4785 行。
- 验证配方 v3（docs/LAWS.md）：`border_mode overlap`、`seam_regen 32`、`seed_mode global`、`context_border 64`、`guide_release 0.8`、`fine_below_sigma 0.75`、尾段 euler（LMS 等多步法会把每帧新纹理外推成颗粒：换 euler +56% 细节、闪烁 −1/3）、**sigmas `1.0, 0.7, 0.4, 0`（1 步 turbo 头 + 2 步尾，2 步尾比 1 步 +67% 细节，3 步过硬）**；两次 turbo 头步在 fp16 下出过 NaN。二跳 `1.0, 0.923, 0.55, 0`。`flat_skip 4.0` 跳过无纹理 tile 防幻觉；`frame_match dc` 去时间均值后再做逐帧 DC 对齐（否则 latent 偏离流形 319→87 细节坍缩）。
- 示例：ref2va pruned int8 + `taomate_3step_lora_avg_rank_19` 1.0 + `lms_v1.0_r64` 0.75/1.0（Alissonerdx 细节 LoRA）、qwen3vl int8、Sol-Attn 1.5；可选 Qwen Image 2.1 首帧锚、SAM3 主体 mask、Dilate/Decimate 快动作变速。
- 耗时：544p→1080p 124 帧 4 tiles 1024×640 共 7m04s（纯步 64%、模型换入 12%），GPU 未注明；r80 相位批处理减少换模。
- 坑：节点多、依赖重（SAM3、Qwen Image、KJNodes、rgthree），第一帧锚仅 2× 有效，源片闪烁会被放大到 0.75 上限。
- 评级：**观望**（4K 交付或大客户需求再用；其「2 步 euler 尾、全局 seed、flat_skip」结论可借鉴）。

### tazmannner/ComfyUI-H3-RelayHires（★57，MIT，最后推送 2026-11-03）
- 定位：二维动画「小渲染、1920 收尾」：0.5 MP（960×544）20 步决定构图/表演/音频 → **AnimeSR**（1.3 M 参数，专门把 H3 恒定 ~2 px 墨线变细）像素放大 → taeh3 编码 → **1 步 DMAD 从 σ 0.60** 重绘细节 → 解码；音频钉死。
- 实测（RTX 5090，124 帧 1920×1088 端到端）：原生 1920 492–508 s；1 MP+LBH 放大+精修 239–245 s；**Relay 116–121 s**；+Fast Tail 105–109 s。σ 0.45 偏软、0.75 开始重画快帧；1 步与 2 步看起来一样、省 21 s；窗口注意力 `window 4 / anchor_stride 8` 在 10–15 s 片上把 1920 步减半且锐度不变（节点默认 window 0=dense）。
- 其它结论：Pika H3 Flex 6 步一采最快（60→22 s）但是「另一条 take」，音乐可能丢，LoRA 在 SigmaShift 前、ManualSigmas `1.0, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0`、lcm；Fast De-rope 二采改为 **4 步 DMAD 从 0.8**（旧 8 步 inject 0.5 会重新走位）；taeh3 编码每 4 帧亮度脉冲 ±1.5–3 → 换 `minimax_h3_sol_vae_int8_convrot` 编解码；非动画用 `upscale_model` 接 RealESRGAN_x2plus（细节 9.8–10.6 vs AnimeSR 6.4–7.0，42 s）。`H3 Fast Tail Sampler`：`decide_above 0.79`、`tail_steps 4`、dpmpp_2m_flow，一采 −20% 且逐帧同 take（stock 等价：beta57 20 → SplitSigmas 12 + ManualSigmas `0.7903, 0.65766, 0.44654, 0.17186, 0` + DPMPP_2M_SDE eta 0）。
- 依赖：FastDerope（taeh3 loader）、MAINodes、FaceDetail、ResCascade、AnimeCadence；DMAD LoRA `minimax_h3_DMAD_4step_full_lora_avg_rank_39_bf16`。
- 评级：**试用**（漫剧风格短剧首选；电影质感用 ResCascade）。

### tazmannner/ComfyUI-H3-ResCascade（★—，MIT，最后推送 2026-11 月）
- 定位：**「1 MP 渲染、1080p/1440p 收尾、同 take 同音频」**的一体节点 `H3 Hires Fix`，建立在 LBH 3D 放大器上；作者在 5090 上系统 A/B 过每个参数。
- 配方：一采必须是**完整原生 1 MP 20 步 beta57**（低清/turbo 一采在每次测试中都丢细节或换 take）；`sigma_start 0.45`（0.31 软、0.56 开始重画五官、~0.9 重新决定整条片）；`steps_override 2` + DMAD 0.8（与 4 步原生无差、快 2.5×；turbo 只放在精修）；一采音频钉死；`images`+`vae` 可接 De-rope/FaceDetail 处理过的帧（taeh3 编码即可）；`face_atlas` 保护小脸（σ 0.45 会把 ~2 token 的小脸重画坏）。
- 实测（5090，124 帧）：1 MP 178–194 s → +59–69 s 到 1920×1088（原生 1920 492–511 s，2× 快）；1440p ~337 s（32 GB）；全动画管线（De-rope+FaceDetail+Cadence）+hires 309–451 s，15 s 片 1703 s。细节 +29%（vs Lanczos）无逐帧沸腾。
- 为什么不「低清→放大→精修」：shift 12 下 20 步里 12 步在 σ>0.8，低清一采把这些步花在 4× 少的 token 上；中途换分辨率省 35% 但丢一半细节。训练无关的注意力捷径（pooled/windowed KV）会破坏 H3。
- 其它节点：`H3 Hold Transfer`（把 1 MP 的 2s/3s 定格逐像素搬到高清）、`H3 Face Atlas Rescale/Stitch (chunked)`（15 s 1920 需分块省内存）、`H3 Front-Loaded Sigmas`（保留 σ≥0.79 原生步，其余 4 大步，−24%，音频相关 0.98）、`H3 Resolution Switch`（研究用）。
- 坑：小全身人物可能偏移几像素；长片需系统内存；只在 5090 32 GB 测过——4090 上 1920×1088×124 帧全帧二采需实测，不行退到 bbaudio 分块。
- 评级：**采用**。

### rdh9616/ComfyUI-Open-H3-Regenerate（★44，Apache-2.0，最后推送 2026-11-02）
- 定位：NVIDIA Open-H3-Regenerate-2K 的 ComfyUI 实现：768P 草稿 → LBH 3D 放大到目标网格 → 重噪 **σ 0.909375 → 0.857 → 0.667 → 0**（3 步 euler，CFG 1）→ FL2VA + 合并 LoRA（Refiner rank 576 + LightX2V FL2VA Turbo v1.2 + LMS Sharp，12.4 GB fp32）+ 50 条 AdaLN Sharp 曲线分支（1.2 GB）→ StreamRender-H3 快速 VAE（24 层蒸馏，6.5 GB）。`regen_core.py`：2 步表 `shifted_grid(0.7, 2)`=`0.7, 0.494, 0`；自定义 `start_sigma` 用 shift 6 网格。
- 节点：LoRA（Diffusers→Comfy 键映射，q/k/v 拼成 qkv_proj、SwiGLU 两半交换，位精确验证；曲线 t 从 ref2va pruned 的 32 KB `adaln_t_table` 读）、Sigmas、Prepare Draft（24 fps、1344×768 或 1024×576 居中裁、17k+5 补尾帧）、Latent Upscale（1080P=1920×1088，4K 经 2K 两跳）、Refine Latent（**音频=编码静音并 mask**，或草稿原声）、Fast VAE Decode（6.5 GB + 26 KB/token，不够回退原生 tiled）、Finish Frames（1088→1080 裁剪、音轨对齐）、Save/Load Refined Latent、Video to H3 Prompt（OpenAI 兼容 VLM 服务器写提示词）。
- 实测（RTX PRO 5000 72 GB，Win，ComfyUI 0.42，int8 FL2VA pruned，5 s 768P→2560×1440）：精修 122 s（Sol-Attn，默认开）/474 s dense；快速解码 24 s（2K 5 s 峰值 21 GB，15 s 45 GB）；全程 ≈3 min；NVFP4 底模只省 9% 且丢皮肤/苔藓细节。T8 在 4060Ti 16 GB 上同配方 3700 s。
- 质量注意：σ 0.909 重画很多——小狐狸脸漂成狼；**首尾帧钉住的草稿用 `start_sigma 0.8`**。替代：Kijai `minimax_h3_open_regenerate_2k_refiner_rank_384_bf16`（纯 refiner）+ LightX2V v1.2 + LMS Sharp 曲线。
- 4090 判断：12.4 GB fp32 LoRA 加载时转 bf16 + int8 FL2VA + 2K 激活，24 GB 会靠 DynamicVRAM 换页，预计 15–60 分钟/5 s；1080P 目标更现实。成片是「重生成」，短剧需要保角色一致时不如 B 路线。
- 评级：**观望**（想要「2K 质感重绘」且接受细节变化时再用）。

### Carasibana/ComfyUI-H3-FaceRefine（★571，MIT，最后推送 2026-09-13）
- 定位：视频版 FaceDetailer：逐帧检测/跟踪脸 → 裁成填满画布（默认 768×768，`auto_capped_768`）→ H3 Ref2VA 低去噪重绘 → 只贴回脸区。H3 小脸画差是「头占画面比例」问题，720p+ 也存在。
- 节点链（示例 Auto Select）：`H3 Face Track + Crop`（face_yolov8m 0.35，smooth_window 21，size per_frame，`select largest_face`，fallback person_yolov8m-seg，identity insightface；输出 frame_count 接 H3 节点 length）→ `MiniMaxH3ReferenceToVideo` 768×768 + 角色参考图 → `H3 Inject Video Latent`（img2img，强度由 BasicScheduler denoise 控制，**不要用 SplitSigmas**）→ `MiniMaxH3NativeAudioLock`（把原音编进音频流、音频 noise_mask 0 → 口型跟原声）→ `H3 Per-Frame Denoise`（接 MODEL：小脸 ×1.0、大脸 ×0.35，30 px/120 px 阈值，smooth 9）→ BasicScheduler **simple 8 步 denoise 0.40** + 8-step turbo v1.0 LoRA 1.0 + er_sde → `H3 Face Stitch Back`（face_only，dilation 24，feather 24，color match，fade_out）。
- 关键表：shift 12 下 denoise→有效 σ：0.02→0.197、0.05→0.387、0.15→0.68、**0.25→0.80**（SDXL 习惯值会整帧重画）。旁路 Per-Frame Denoise 时基准 denoise 要大幅下调。
- 1.1.x：`H3 Load Video + Face Select`（PySceneDetect 切镜头，逐镜头选脸，交互式 Pick faces）、丢失主体不再跳到别人脸上、动漫用 deepghs 检测器 + `clip_vision`/`ccip` 身份模型。
- 依赖：ultralytics、scipy、insightface（onnxruntime 与 -gpu 不能并存）、scenedetect；示例还需 VHS、Impact Pack、NativeAudioLock（在 Shrek3OnVH5/MiniMax-H3-NativeAudio-MusicVideo-Workflow 仓库里）。成本 = 画布²×帧数；帧数补到 17k+5。
- 评级：**采用**（短剧中远景对话必备；配合 ResCascade 的 face_atlas 在高清化前做）。

### Adudeguyman/ComfyUI-H3-AudioRefine（★164，MIT，最后推送 2026-09-08）
- 定位：Turbo 4 步画面可接受、音频不行时，**冻结视频流只对音频再去噪**：noise_mask video=0/audio=1，每步把冻结视频以 0.999 视觉条件时间步注入，音频走 ModelSamplingAV 自己的时钟，无自定义采样器。
- 节点：`H3 Audio Refine Sampler`（默认 steps 6、`audio_denoise 0.5`、`video_denoise 0`、euler/simple、cfg 1）+ `H3 Frozen Video Cache`（冻结行 K/V 缓存，`hidden`/`int4` 最小，~10 GB 内存；磁盘后端默认关——每次写 10 GB）。**精修分支从 Turbo LoRA 之前的底模分出**，用未蒸馏权重补回音质。
- 实测（RTX 5090 32 GB，1376×768 10 s）：4 步 Turbo 137 s；+6 步音频精修：有缓存 44.6 s（26.5 s 建缓存 + 3.6 s/步）、无缓存 124 s（20.7 s/步≈一整步）；端到端 263→185 s。无缓存时精修步≈全价，因为 H3 单流全双向注意力。
- 示例：fl2va pruned int8 + turbo 4step v1.0 768p 0.8、sa_solver beta 4 步、1344×768 73 帧。
- 坑：缓存是近似（冻结行不再响应音频演化，`refresh_interval` 重建）；显存紧就旁路缓存。
- 评级：**试用**（草稿阶段用 4 步 + 音频精修替代整段 8 步；成片仍建议 8 步 LoRA 或 TTS 锁定）。

### T8mars/comfyui-minimax-h3-audio-T8（★1262，NOASSERTION，最后推送 2026-10-31）
- 定位：62+ 节点、95 组工作流、上百页验证记录的全家桶；本簇只看 Still / Conditioning / Speech / Audio / Quality / Upscale 菜单。文档是「验证日志」风格（SHA、prompt ID、CPU 测试数），可执行结论要自己挖。
- Still：`MiniMax H3 Reference Image Edit (EXP/T8)`（Ref2VA 单/多图语义编辑，`direct_1_frame`，音频 `generate_and_discard`/`lock_silence`，不是 mask 像素编辑）；**`Five-View Character Sheet (EXP/T8)`**：一张 `<Picture 1>` → 5 个独立解码的图像槽（video latent `[1,24,5,S/16,S/16]`），Ref2VA pruned 底模 + matlod `minimax_h3_five_view_512_s1500.safetensors`（63 MB，放 loras）强度 1.0、res_multistep/simple 28 步；专用 Decode 把每槽复制成 2 token 合法 clip 解码取首帧；**切回视频生成必须卸掉这个 LoRA（作者记录会毁运动）**。
- Speech：Voice Profile / Speech Plan / Speech Conditioning（描述音色走 T2VA，参考音色走 Ref2VA + 黑图，参考音 2–15 s，渲染 124–362 帧）/ Speech Decode / Assemble / Verify & Align（ASR 裁切）/ Dialogue Script / Turn Select；11 种语言。NATIVE_VOICE_EMOTION：台词只在 Local 段出现一次、0–2 s 说完、其余时间写明确的无声动作，否则尾部乱说；情绪要写「直接狂怒」而非「克制」。
- Audio/Quality：Audio Refine Plan/Audit（对应 AudioRefine 思路）、Scheduled Drive Audio Injection（双时钟反复锚定 drive audio）、Audio Integrity Audit（只报告不修）、Face Refine Parity（对齐 Carasibana@79a97ce5，推荐 `manual_512`、crop_factor 2.5、逐帧 0.8/0.35、21/51 平滑，SSIM 0.967）。
- Upscale：`Learned Latent Upscale (Advanced)` + `Chunked Two-Pass Plan`：标准 I2VA **4+4**（低清 simple 8 前 4 步 → LBH 3D → 高清 `0.9035, 0.8, 0.6316, 0.3158, 0`），并修复「高分段 video σ 0.9035 对应 audio σ≈0.701，通用采样器先按 video σ 初始化整个 AV latent」的双时钟问题；`H16-3 Chunked PASS2` 默认 `preserve_first_pass` 音频。**警告：缺 PEFT alpha 处理的普通 `_comfyui` LoRA 会把更新放大 ~16 倍整幅融化，要用 `comfyui_alpha8`**。4060Ti 16 GB 上 4+4 1472×832 124 帧 1572 s（DynamicVRAM 换页）。
- 坑：依赖链重、README 导流网盘/RunningHub、许可证 NOASSERTION、节点 ID 经常变；OPEN_REGENERATE_2K 在 16 GB 上 3700 s。
- 评级：**观望**（只摘 Five-View / Speech 规则与 alpha8 警告；节点包本身不建议整装）。

### Luisacaotica/ComfyUI-MiniMaxH3Mod（★616，MIT，最后推送 2026-10-15）
- 定位：「RefMod」——把图像/视频/音频参考用对应 VAE 编码后存成可复用 `.safetensors`（`encode` 保细节 / `training` 压缩 latent 再精炼，不是 LoRA 训练），`Apply H3 RefMod` 注入原生 conditioning，可设 token 预算、强度、按去噪步的强度曲线、A/B 概念轴、Bridge 用公开 `OUTER_SAMPLE` wrapper（无 monkeypatch）。
- 现状：README 顶部「🚧 Under construction」+ 指向 discussions/36 的更新通知（未能读取）；**语音身份迁移在作者测试中失败**（音乐参考有效）。
- 对短剧：角色参考库「一次编码多次复用」有吸引力，但 H3 原生多参考已能做；压缩会丢身份细节。
- 评级：**观望**。

### shootthesound/ComfyUI-Fizgig-H3-Still（★177，MIT，最后推送 2026-09-26）
- 定位：两节点让 H3 出**真单帧**：`Fizgig H3 Still Latent`（1 帧 latent，stock 最少 5 帧）+ `Fizgig H3 Still Decode`（把 token 复制成 GROUP 帧解码取第 3 帧，30 dB vs 单 token 17 dB，去条带）。比专用单帧 VAE `minimax_h3_t1_image_vae` 更快更锐。
- 配方：fl2va pruned int8 + qwen nvfp4 + video VAE int8，`MiniMaxH3ImageToVideo` 只取 conditioning（LATENT 不接），**turbo `minimax_h3_turbo_v4_step600_ema` 强度 0.38 + 20 步 er_sde simple**；最高质量 8 MP 无 Turbo 50 步；**≥3 MP 才好**，小图明显弱；编辑用 `MiniMaxH3ReferenceToVideo` `<Picture 1>` 在 2.5 MP 做。宽高 32 倍数，解码分 tile。
- 对短剧：剧照、海报、关键帧、角色定妆照；配合 ResolutionSelector。
- 评级：**采用**。

### tori29umai0123/ComfyUI-MiniMaxH3-SingleFrame（★82，无 license，最后推送 2026-09-18）
- 定位：`MiniMax H3 Single Frame Edit`（输入图钉在第 0 帧，`frame_count=1` 直接出单帧 latent，`keyframe`/`reference` 两种用法）、`Start End Frame Interpolate`（首尾帧固定，取中间帧——「姿势参考图 → 角色设定」转换）、`Temporal RoPE Patch`（把目标 token 的时间 RoPE 拉向指定帧：静态编辑 strength 1.0，首尾插值 0–0.25）、`Empty Single Frame Latent`。不 patch 核心模型代码。
- 帧数规则 `frame_count % 17 == 5`；2–4 帧按 5 帧网格。
- 对短剧：把「动作参考 + 角色设计图」合成同一角色摆同一姿势的单帧，是角色卡的实用技巧；但无 license。
- 评级：**试用**。

### astropuzzo/ComfyUI-MiniMax-H3-Image-Studio（★218，Unlicense，最后推送 2026-09-30）
- 定位：H3 文生图/图编辑的两套模板（Generate / Edit），内置 Fizgig 单帧解码技术，`Image Edit` 最多 9 张 `<Picture n>`，各图独立编码（没有隐藏的第 0 帧锚/假 denoise 滑块）。需 ComfyUI ≥0.37。
- 默认：3 MP（预览 1 MP，4–8 MP 大图）、无 LoRA 50 步 ER-SDE/simple；快配方 turbo v4 step600 0.38 + 20 步；LoRA 节点默认 bypass，可串任意多个。旧版 Qwen 细节精修已废弃。
- 评级：**试用**（比 Fizgig 多一个多图编辑模板）。

### thaakeno/ComfyUI-MiniMax-H3-Studio（★139，MIT，最后推送 2026-09-21）
- 定位：图像向「导演面板」：T2I（FL2VA）/ I2I（FL2VA）/ 参考编辑（REF2VA，最多 9 张 `@Image1..9` 各司其职）、LightX v1.0 8 步主路径、PDD 4 步 REF2VA、小脸 Face Refine（YOLOv8-Face + 可选 SAM）、Qwen3-VL 4B/8B 提示词准备、Benchmark Lab。Alpha；不支持 Nodes 2.0。
- 注意：**自带 GoatCounter 生成计数遥测**，删 `telemetry/` 目录可关。
- 评级：**观望**。

### lumosai8/ComfyUI-OrbitSheets（★85，MIT，最后推送 2026-08-14）
- 定位：用一次 H3 I2VA 渲染出角色转身/场景参考页：因为「每个角度都是同一镜头」所以不漂。**结论：硬切优于连续环绕**——`[Shot N] At 00:MM.mmm, the shot cuts to...` 锁定三脚架静态镜头；角色 6 个视图（全身→脸特写→左侧→右侧→背面→受惊表情 `scared_shot`），场景 4–6 个（前→右→后→左 +wide +detail），`shot_seconds` 0.75，124 帧；连续转动限 ≤40°/s（360° 需 ≥216 帧），超了会自动钳制并打日志。
- 其它规则：约束写正面陈述（「地平线保持水平、墙的竖线保持竖直」）而非否定句；宽体角色用 `full body, generous margin`，锚图也要留边；角色页顺带出一段台词 → 音色样本。`Frame Select (vision-judged)` 用视觉模型（llm_url）在锐度门控后挑帧，`Contact Sheet` 拼图，`Attention Backend` 可选 sage/flash。
- 示例：Krea2 画锚图 → H3 fl2va pruned int8 + turbo 4-step v0.1 1.0 + `minimax_h3_ref_lora_rank_256` 1.0、1216×672、simple 8 步、shift 12/3。
- 评级：**试用**（与 Contact-Sheet 互补：Contact-Sheet 出干净五视图，OrbitSheets 出带表情/声音的参考）。

### matlowai/ComfyUI-MAINodes（★240，NOASSERTION，最后推送 2026-11-07）
- 定位：三合一——**Contact-Sheet 五视图**、Motion Lab「去绳」（de-rope：快动作糊是 1 token 装 4 帧的 4 个姿势装不下，先读 latent 找过热段、定格放慢、v2v 部分去噪重绘、再精确抽帧恢复帧率）、Dials 无训练转向滑块；外加 RelayVSR 像素超分、16 GB 低显存节点、视频对比器。
- Contact-Sheet：`H3 Contact Sheet` + `H3 Contact Sheet Decode`，fl2va pruned int8 + `minimax_h3_five_view_1024cont_s600.safetensors` **0.75**、res_multistep/simple **28 步 denoise 1.0**，`ref_image` 可空（纯文本五视图）。LoRA 来自 matlod/minimax-h3-turnaround。
- Motion Lab：一采 12 步底模 → turbo 6 步去绳，`inject` 0.50 更锐/0.70 更稳；192 帧 1 MP 约 12 min（RTX PRO 6000）；先试 2–3 s 片。Pika Flex + de-rope 是作者推荐起点。
- LOWVRAM：`--fast-disk --fp16-intermediates --disable-pinned-memory`（RSS 41.9→14.6 GB），`H3 Streamed Blocks` 16k token 分块、kv int8；w4a8 底模。RelayVSR 需独立 LightX2V venv，X4 模型即使出 2× 也优于 X2（+3.3 dB，少闪）。
- 坑：许可证 NOASSERTION；大多数图需 KJNodes；alpha 功能多。
- 评级：**采用**（Contact-Sheet）/ **试用**（de-rope 用于打斗镜头）。

### wyzborrero/ComfyUI-H3-FunControl（★51，Apache-2.0，最后推送 2026-09-15）
- 定位：第一个能加载 alibaba-pai `MiniMax-H3-Fun-Controlnet-Union` 的 ComfyUI 节点（depth/canny/pose/HED/MLSD 逐帧驱动）；**ComfyUI 0.35 起核心已有 `MiniMaxH3FunControlNetApply`**，作者明说「只要 ControlNet 就用核心的」。权重必须是 Kijai 曲线形 `minimax_h3_fun_controlnet_union_pruned_bf16`（adaln `[96768, 8]`），原版 `[96768, 2688]` 只配 34 GB 全量底模。
- 实测结论（5090，90 帧 1280×704，28 步）：**链式 ControlNet 的 skip 相加**——depth 1.0 + pose 1.0 ≈ 单塔 2.0 饱和，建议 depth 0.3 + pose 0.7；**pose 锁人、depth 不锁**（1280×704 的 token 网格只有 40×22，100 px 的人只占 3 个竖 token，深度渐变近乎平坦）；strength >1.0 无效且劣化；`end_percent 0.6` 提前释放让后期长纹理；风格细节用 CFG 4.0 + CFGGuider 更听话（1.9× 成本）；Sol-Attn `morton` 必须 false（220 s vs dense 332 s，morton 开则控制消失无报错）；核心 `BlockSparseAttention` 在 PR #16344 合并前必须放在 ControlNet **之前**。
- 评级：**试用**（用核心节点 + 这里的参数；短剧用处：复刻参考片走位/运镜时用 pose，配 reshot 生成控制视频）。

### slmonker/selflift-Avatar（★155，无 license，最后推送 2026-11-02）
- 定位：SelfLift（arXiv 2609.02036）渐进分辨率采样的 H3 分支：前 `transition_step`（默认 6）步在 `lowres_scale` 0.5 上跑，用无训练「Artifact-Aware Consistency Lift」抬到目标分辨率、在过渡 σ 重噪、补完；`low_res_model`/`high_res_model` 双模型；音频流全程保留（mask）；高分辨率阶段 `highres_tiling` 四种省显存模式（`spatial` 最省但背景会膨胀/错位；`global_stream` token chunk 4096 + 权重缓存 4 GiB 推荐）。
- 重要副产物：发现并修复 LBH 3D 放大器 >32 latent 帧时间分块的**首帧字形伪影**（replicate→reflect padding），只影响首尾窗口。
- 现状：94 个 CPU 测试 + 前端桩测试，真实画质/显存未系统验证；打包版 v0.1.4 不含修复。
- 评级：**观望**（关注其对 LBH 分块伪影的修复是否被上游吸收）。

### Saganaki22/ComfyUI-Viggle-Animate-H3（★137，Apache-2.0，最后推送 2026-09-11）
- 定位：Viggle-Animate（ref2va 的 33.1 B 全量微调）视频换人：驱动视频 + 角色图 → 片中表演者换成角色，运动/机位/背景/音轨不变；无文本编码器，固定 362 token 条件 `fixed_embed_fwd_anyframe`。
- 配方：`minimax_h3_ref2va_viggle_pruned_int8_convrot`（21 GB）+ `viggle_animate_dmd_lora_r64`（0.94 GB）、ModelSamplingMiniMaxH3 shift **3/3**、euler、CFG 1、**ManualSigmas `1.0, 0.857142857, 0.6, 0`（3 次前向）**，6 点=5 步均衡、8 点=7 步可能过锐（KJ CustomSigmas `interpolate_to_steps` 必须=点数−1，否则 log(0) 出 NaN）；长片 `Windowed Conditioning` + `Chunked Sampler` 124 帧窗/22 帧重叠、`five_frame_anchor` 续接、磁盘 checkpoint 循环。
- 对短剧：把真人表演/替身视频换成自己的角色，是「表演可控」的另一条路；21 GB 底模在 4090 上只能换页运行。
- 评级：**观望**（有真人表演素材时再试）。

### D3voz/openjutsu（★1898，MIT，最后推送 2026-10-30）
- 定位：Genjutsu 风格「一键换人/换物」Next.js 应用，壳在 ComfyUI 工作流外（comfy-api-proxy 8189）：简单/高级（1–4 人按角色匹配）/物体替换（SAM 3.1 跟踪区域重绘、Add 物体、换背景）/From picture（FLUX+SolarRenderer 先摆姿势）/后处理 Fix faces（调用 Carasibana FaceRefine）与 Fix colours。模型：ref2va pruned int8 + **DMAD 4step LoRA 6 步** + qwen int4 + SAM 3.1。
- 实测（4060Ti 16 GB + 64 GB 内存，权重从内存流式）：6 s 480p 片 6–13 min；默认 736p；1080p 慢 2.5×。镜子/反射不行；「替换谁」按角色写不要写衣着（会漏进结果）；`No lip-sync` 选项给静音防止新人物对口型。
- 依赖 12 个节点包（SolarRenderer、Context-Loop、PromptBuilder、KJNodes、controlnet_aux、VHS、oneclick-swap、FaceRefine、Impact、detail-contrast、FXMax、websocket-fix）。
- 评级：**跳过整套**（想借鉴的只是「SAM 跟踪区域 + 灰色人偶运动参考 + 局部重绘」思路和 `comfyui-h3-oneclick-swap` 节点）。

### maosika-ai/reshot（★57，Apache-2.0，最后推送 2026-09-28）
- 定位：pip 命令行/网页工具：参考视频 → 深度图（Video Depth Anything，全片一次归一化）/ DWPose 骨架（带身份跟踪、One-Euro 平滑）/ Canny，`--target h3` 输出 32 倍数、24 fps；4090 上 12 s 片深度 ~20 s。另有 ComfyUI-ReShot 节点。
- H3 用法：`depth.mp4` 作 `<Video 1>` + 角色设定页 `<Picture 1>`；提示词要**用文字描述灰片里发生了什么**，并写明 `attribute_transfer - every action, position, timing and camera move of <Video 1> is transferred onto <Subject 1>...; its grey depth look is not transferred`，否则可能出灰片。骨架可直接进 Fun ControlNet 的 pose 输入。Depth 传整体构图/机位，Pose 传四肢手指；武打舞蹈用 pose。
- 评级：**试用**（复刻参考片走位的预处理器）。

### CGlide/ComfyUI-CGlide（★172，GPL-3.0，最后推送 2026-11-07）
- 定位：短片作者自用的「H3 Studio」一体节点（9 图/3 视频/3 音频槽、项目时间线、🔗 续接、Song mode、一键渲染整项目）+ Glide Preview/Video/Join/Audio Lock/Upscale Hold/Cast + Diffusers LoRA 加载器。
- 画质相关：**Latent hold**——续接改用上一段采样器输出的 `.h3latent`（~30 MB）而非解码再编码，6 段链路后饱和度 −14%/边缘 +55% 的「越接越糊越脆」消失；**必须取第一采样器的 latent**（放大精修后的尺寸不同不被使用）。`Glide Upscale Hold` 在放大精修时把本段头部钉到上一段**精修后**的尾部，避免各段各自发明纹理导致接缝跳变。`Glide Audio Lock`：歌曲编进音频半区、nested noise_mask 钉死，ComfyUI 在 AUDIO_COND_TIMESTEP 每步重注入；输出原始音频段 bit-exact 供混流。`Glide H3 LoRA (Diffusers)`：加载 Open-H3 合并 LoRA，refiner/turbo/sharp 三个强度可分开调（默认 1.0）。
- 2K 示例：`minimax_h3_hybrid_fl2va_ref2va_b25-49-int8` + LBH 3D（Separate/Concat）+ `CSGlideUpscaleHoldCS` + ManualSigmas `0.909375, 0.857143, 0.666667, 0` 或 BasicScheduler simple 3 步 denoise 0.3 + Sol-Attn。
- 坑：GPL-3.0；Manager 注册版装进 `cglide` 目录与 git clone 重复加载；w4a8 底模在旧 ComfyUI 下出「黑画面有声音」无报错；低显存路径需 ≥0.31。
- 评级：**试用**（Latent hold / Upscale Hold 的做法值得写进长片拼接规则）。

### PlagueKind/ComfyUI-PlagueKind-Nodes（★213，MIT，最后推送 2026-09-21）
- 只看 H3 部分：`H3 SLA Attention`（块稀疏注意力，5090 768p/15 s + SLA turbo LoRA：44 s/it dense → 31 s/it @0.85、25 s/it @0.90，无额外显存，需 Triton）；`H3 AdaLN LoRA Fix`（让全量 LoRA 在剪枝曲线形底模上不再被跳过——实测恢复的贡献仅 0.02%，**只是让日志干净**）；`ComfyUI-H3-UltimateUpscale-LD`（bbaudio 单节点的自包含复制，无外部依赖）；`H3 UpscaleSize`（按 MP/倍率/长边算 32 对齐尺寸，默认 1440/2.0）；`H3 MiniMax Cache`；10 槽 LoRA 堆叠器 minimax 模式 + `h3_refmod_loader`。
- 评级：**观望**（SLA 在 docs/11 已有同类结论；AdaLN fix 说明那 51 行 `ERROR lora ... adaln_proj` 可以忽略）。

### badgids/ComfyUI-H3-ExactAudioLock（★16，MIT，最后推送 2026-09-28）
- 定位：确定性、采样级精确的目标音频构建 + 全锁/对白局部锁 + 人工审听门。`Timed Audio`（`start_frame` 按 24 fps→40 Hz 音频 latent 整数换算、`gain_db`）→ `Exact Audio Lock`（整条音频 noise_mask 0，视频可去噪；`mix_policy` sum/prevent_clipping/reject_overlap，`overflow_policy` error/crop）或 `Dialogue Audio Lock`（只保护对白区间 + 边距，空隙让模型生成环境音）→ `Dialogue Audio Finalize`（采样后把精确波形回填核心区间）；`Audio Review / Accept Gate` 选一条通过的 take；Scene 版用于递归长视频；附 Qwen3-TTS 工作流。
- 规则：**同一 `start_frame` 同时接原生 `Add Guide for MiniMax H3.frame_idx` 并喂同一段音频**（锁保证波形时间，Guide 告诉模型此刻发生什么）；全锁时成片音轨用 `exact_audio` 混流，**不要用采样器的 VAEDecodeAudio**；多说话人只有一个目标音频流，说话人归属靠提示词；单声道复制为立体声。
- 评级：**采用**（TTS 对白短剧的口型/时序基础设施，比 NativeAudioLock 多了逐句时间轴与局部锁）。

### lihaoyun6/ComfyUI-MiniMaxH3_Ref-Patch（★11，Apache-2.0，最后推送 2026-08-12）
- 原理：`minimax_h3_ref_patch.safetensors`（148 MiB，官方索引：ref2va 与 fl2va **共享的 112 个键的权重差分**）放 `models/model_patches`，`MiniMax H3 Ref-Patch Loader` 用 `model.add_patches({key: (diff,)}, strength_patch=ref_strength)` 加到 FL2VA 上（键名自动加/去 `diffusion_model.` 前缀），目标是**模拟 Kijai `minimax_h3_ref_lora_rank_256` 的效果**，不是复刻 ref2va。
- 效果：README 只有一张预览图，无量化对比；70 行代码，无 license 争议。用户已有 int8 Ref2VA，且差分是 bf16 全量权重算出的，叠在 int8_convrot 量化权重上能否正确应用未验证。
- 评级：**跳过**（除非只想常驻一个 FL2VA 模型省磁盘/切换时间）。

### NyckM/3d-Camera-control-H3-Minimax（★108，Apache-2.0，最后推送 2026-09-20）
- 定位：对已有视频「重新运镜」：MoGe 估几何 → Camera H3 节点按新虚拟相机轨迹重投影生成 Meridian 深度 warp 视频 → Viggle Meridian（相机控制模型）生成；相机来自 warp 不是提示词。两条路线：Meridian INT8 剪枝全模型 + Meridian DMD LoRA + taomate 3-step LoRA（质量优），或 **bf16 全量 FL2VA** + Meridian Teacher→Turbo LoRA（Teacher 必须先于 Turbo 加载）。支持子弹时间定格、主体框。
- 依赖：MoGe 权重、Meridian 固定文本嵌入、Bruxos H3 Frames/Compare、Custom-Scripts、Pixaroma；bf16 FL2VA 路线不适合 24 GB。
- 评级：**观望**（短剧偶尔需要「换机位重拍」时再看，先看 Meridian INT8 在 4090 的可行性）。

---

## 三、4090（24 GB）「草稿 → 成片」画质流水线推荐

前提：Windows、ComfyUI 0.37.2、int8_convrot FL2VA/Ref2VA、qwen3vl_32b nvfp4、SageAttention、lightx2v Turbo LoRA。目标 16:9 1920×1088，5 s 一段起步。

**Stage 0 · 资产**
- 角色三视图：`MAINodes` `H3 Contact Sheet`（fl2va pruned int8 + matlod `five_view_1024cont_s600` 0.75，res_multistep/simple 28 步，`<Picture 1>` 一张定妆图）→ 五视图；需要表情/声音样本时再跑 `OrbitSheets` 角色页（硬切 6 视图，0.75 s/视图，124 帧，带台词）。五视图 LoRA 用完立刻卸载。
- 剧照/关键帧/首帧：`Fizgig H3 Still Latent + Still Decode`，3 MP（如 2304×1296），turbo v4 step600 **0.38** + er_sde simple 20 步；海报 8 MP 无 Turbo 50 步。姿势参考→角色：`SingleFrame` Start/End Interpolate，RoPE patch 0–0.25。

**Stage 1 · 草稿抽卡（保持现状）**
- 1344×768（或 960×544 更快），Turbo 4 步、shift 12/3（或 docs/11 的 6/3），CFG 1。
- 保存一采 **latent**（SaveLatent / Tr1dae Save Package / CGlide `.h3latent`），音频一并保留。电影质感且时间允许时，挑中的镜头改用 **1 MP 原生 20 步 beta57（或 Fast Tail：前 12 步 euler + 4 步 dpmpp_2m，−20%）**重跑一采——ResCascade 实测 turbo 一采会丢细节/换 take，而精修阶段 turbo 无损。
- 音频差但画面好：`H3 Audio Refine Sampler` 6 步 `audio_denoise 0.5`、分支从 Turbo LoRA **之前**的底模取；TTS 对白则直接用 `ExactAudioLock` 钉死（同帧接 AddGuide）。

**Stage 2 · 1 MP 阶段修补（在放大前做）**
- 远景对话脸：`FaceRefine` Track+Crop（768 画布，largest_face/identity_reference）→ Ref2VA 768×768 + 角色图 → Inject Video Latent → NativeAudioLock（原声→口型）→ Per-Frame Denoise 1.0/0.35 → simple 8 步 **denoise 0.40** + 8-step turbo → Stitch face_only dilation 24 feather 24。动漫换 deepghs 检测器 + clip_vision。
- 快动作糊：`MAINodes` Motion Lab de-rope（inject 0.5/0.7）或 RelayHires 的「4 步 DMAD 从 0.8」。

**Stage 3 · 放大精修到 1920×1088（首选 ResCascade）**
- `LTXVSeparateAVLatent` → `H3 Hires Fix`（内置 LBH 3D，`lbh_model` fp16，`width 1920 / height 1088`，**`sigma_start 0.45`**，DMAD 4step LoRA 0.8 + `steps_override 2`，或无 DMAD 时 `steps_override 0` 走原生 4 步；有 FaceRefine 结果时走 `images`+VAE 并接 `face_atlas`）→ 二采 SamplerCustomAdvanced euler + 节点输出的 sigmas → 解码；音频自动钉死为一采原声。等价手搓：3D 放大 → Concat 音频 → 在 1920×1088 重建同 prompt/参考的条件 → ManualSigmas 从 0.45 起的 beta57 尾段 → DisableNoise。**不要从 0.9 起，不要用 BasicScheduler denoise 0.25（=σ 0.80）**。
- 漫剧风格：改走 RelayHires（AnimeSR → taeh3 → 1 步 DMAD σ 0.60，window 4/anchor 8；亮度 4 帧脉冲换 Sol-H3 VAE）。
- 10–15 s 长片或 OOM：`MMH3 Ultimate Upscale`（tile 768×768、overlap 128、chunk 136 帧/overlap 17、anchor 0.999，二采 1–2 步 denoise 0.2–0.3，音频不重采）或 LBH `MMH3 Split Upscale`（seam_denoise 0.6）。多段续接时用 CGlide `Upscale Hold` 钉住上一段精修后的尾巴。
- 观察：LBH 3D 对 >32 latent 帧（>~110 帧）走时间分块，检查首帧是否有网格状字形伪影。

**Stage 4 · 可选最后一跳**
- 想要「2K 重绘质感」且接受细节变化：Open-H3-Regenerate 3 步（`start_sigma 0.8` 保脸），先只做 1080P；4090 预计慢数倍于 72 GB 卡的 122 s。
- 只想更大尺寸不改内容：像素 SR（RelayVSR X4 / RealESRGAN_x2plus / 其它簇的 SeedVR2）。

**Stage 5 · 交付**：一采原声或 ExactAudioLock 的 `exact_audio` 混流；多段用 CGlide Latent hold 续接，不要解码再编码。

---

## 可写进 skill 的规则

1. latent 放大一律用 `MinimaxH3LatentUpscaler3D`（`minimax_h3_latent_upscaler_3d_fp16.safetensors`，`models/latent_upscale_models/`），前接 `LTXVSeparateAVLatent` 只放大 video_latent，后用 `LTXVConcatAVLatent` 把原音频拼回。（LBH-123-AI）
2. 二采目标宽高必须与重建后 conditioning 的生成尺寸一致（重新在 1920×1088 建 MiniMaxH3ImageToVideo/ReferenceToVideo，或用 Tr1dae/ResCascade 节点自动缩放 `minimax_refs`），Ref2VA 必须重建 Guider。（Tr1dae、bbaudio）
3. 「保 take」精修从 **σ 0.45** 起（0.31 软、0.56 重画五官、0.9 换片）；Turbo/DMAD 只放在精修阶段，一采用原生 20 步 beta57。（ResCascade）
4. 二采永远钉死一采音频：Tr1dae `audio_denoise=0`、bbaudio/T8 `preserve_first_pass`、ResCascade 默认；H3 的 `BasicScheduler denoise` 在 shift 12 下 0.25=σ0.80、0.05=σ0.39，不要套 SDXL 经验，不要用 SplitSigmas 做低去噪。（Tr1dae、FaceRefine）
5. 二采用 euler（或 res_multistep）非祖先采样器 + DisableNoise；多步法（LMS）在释放尾段会把逐帧纹理外推成颗粒。（Tessera、Tr1dae）
6. 精修尾段 2 步最佳：1 步 turbo 头 + 2 步 euler 尾（`1.0, 0.7, 0.4, 0`），3 步尾过硬 +17% 闪烁。（Tessera）
7. 小脸修复：画布 768×768（`auto_capped_768`），Ref2VA + 角色图，`denoise 0.40` × 逐帧（小脸 1.0 / 大脸 0.35，30 px/120 px，smooth 9），`MiniMaxH3NativeAudioLock` 喂原声保口型，stitch `face_only` dilation 24 feather 24。（Carasibana）
8. 小脸修复放在放大之前；高清精修时用 `face_atlas` 保护或把 512 脸块重贴回 1920 帧。（ResCascade）
9. 动画短剧 1920 收尾用 RelayHires：AnimeSR 放大 → taeh3 编码 → 1 步 DMAD 0.8 从 σ 0.60，`window 4 / anchor_stride 8`；真人/绘画风改 `upscale_model=RealESRGAN_x2plus`。（RelayHires）
10. 4 步 Turbo 音频差时：冻结视频只精修音频 6 步 `audio_denoise 0.5`，精修分支从 Turbo LoRA 之前的 MODEL 分出；显存紧就不开 Frozen Video Cache。（AudioRefine）
11. LightX2V LoRA 用带 alpha 的 `*_comfyui_alpha8` / 官方 `*_comfyui_bf16` 文件；缺 PEFT alpha 的会把 LoRA 更新放大 ~16 倍整幅融化。（T8）
12. 剪枝底模加载全量 LoRA 时出现 51 行 `ERROR lora ... adaln_proj` 可忽略（恢复贡献仅 0.02%）。（PlagueKind）
13. 真单帧剧照用 `FizgigH3StillLatent + FizgigH3StillDecode`，≥3 MP，turbo v4_step600_ema 0.38 + er_sde simple 20 步；8 MP 海报无 Turbo 50 步；不要用 `minimax_h3_t1_image_vae`。（Fizgig-Still、Image-Studio）
14. 角色五视图：`H3 Contact Sheet` + matlod `minimax_h3_five_view_1024cont_s600` 0.75（或 `five_view_512_s1500` 1.0）、res_multistep simple 28 步、一张 `<Picture 1>`；生成视频前必须卸掉该 LoRA。（MAINodes、T8）
15. 用视频做参考页时写硬切而非环绕：`[Shot N] At 00:MM.mmm, the shot cuts to ... locked-off static camera ...`，每视图 0.75–1 s，124 帧；转动 ≤40°/s（360° 需 ≥216 帧）；约束写正面陈述。（OrbitSheets）
16. 姿势参考→角色设定单帧：SingleFrame `Start End Frame Interpolate`（首帧姿势、末帧角色），RoPE patch strength 0–0.25；静态编辑 strength 1.0。（SingleFrame）
17. 多个 ControlNet 的强度是共享预算：depth 0.3 + pose 0.7，总和 ≤1.0；锁人用 pose 不用 depth；`end_percent 0.6`；strength >1 无效；小人物先放大取景。（FunControl）
18. Sol-Attn/BlockSparseAttention 的 `morton` 必须 false；在 PR #16344 合并前稀疏注意力节点要接在 ControlNet 之前。（FunControl）
19. 参考片走位复刻：`reshot ref.mp4 --target h3 --control pose`（武打舞蹈）或 depth（其它），提示词写明 `<Video 1>` 里发生了什么并声明 `its grey depth look is not transferred`。（reshot）
20. TTS 对白用 `MiniMax H3 Timed Audio`（`start_frame`）→ `Exact Audio Lock`/`Dialogue Audio Lock`，同一 `start_frame` 接 `MiniMaxH3AddGuide.frame_idx` 并喂同段音频；成片混 `exact_audio`，不用 VAEDecodeAudio。（ExactAudioLock）
21. 长片续接从上一段**第一采样器的 latent**续（`.h3latent`），不要解码再编码（6 段后 −14% 饱和、+55% 边缘脆化）；放大精修的多段用 `Glide Upscale Hold` 钉上一段精修尾。（CGlide）
22. 24 GB 分块二采起点：tile 576–768（32 倍数）、overlap 128、chunk 136–170 帧（17 倍数）、anchor 0.999、`seam_denoise` 0.5–0.8，二采 1–2 步 denoise 0.2–0.3；只用 `.safetensors` 放大权重。（bbaudio、LBH）
23. LBH 3D 放大 >32 latent 帧会走时间分块，检查首帧字形伪影；短片关掉 `enable_temporal_chunking`。（LBH、selflift-Avatar）
24. Open-H3-Regenerate 只在接受「重生成」时用：σ 表 `0.909375, 0.857, 0.667, 0`，首尾帧钉住的草稿改 `start_sigma 0.8`；需 FL2VA + 12.4 GB 合并 LoRA + 6.5 GB 快速 VAE + ref2va pruned 的 adaln 表；NVFP4 底模丢细节。（Open-H3-Regenerate、CGlide）
25. 一采提速且不换 take：保留 σ≥0.79 的原生步，尾段 4 步 dpmpp_2m（Fast Tail）或 Front-Loaded Sigmas，−20~24%。（RelayHires、ResCascade）
26. Pika H3 Flex 6 步一采：LoRA 在 SigmaShift 前，ManualSigmas `1.0, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0`、lcm、CFG 1；它是另一条 take，背景音乐要写「loud, clearly audible」。（RelayHires）
27. 不要给 H3 Studio（thaakeno）保留 `telemetry/` 目录；不要同时装 CGlide 的 `cglide` 与 `ComfyUI-CGlide` 两份。（H3-Studio、CGlide）
28. 原生 VAE 解码固定 256 px tile 且每时间块写回 CPU；长片可用 Tr1dae `VAE Decode (fast)` GPU 输出或 int8_convrot 视频 VAE（解码快 1.5×，60 dB）。（Tr1dae、MAINodes）

## 未覆盖/未读完

- `Luisacaotica/ComfyUI-MiniMaxH3Mod` 的 discussions/36 更新通知与 BUNDLE_FORMAT/PLAN_0.3.0 未读（可能已改方向）。
- `T8mars` 95 组工作流只读了 13-latent-upscale、FIVE_VIEW、FACE_REFINE、PIKA_DOUBLE_SAMPLING、OPEN_REGENERATE_2K、NATIVE_VOICE_EMOTION、H16-3 文档；Speech 节点源码只看了 schema，未读 `speech.py` 全部 966 行；Director、Meridian、FreeVideo、Topaz/DLSS 未读。
- `hashu786/ComfyUI-Tessera` nodes.py 4785 行只读了 INPUT_TYPES 与 LAWS.md；Streamed Encode/Decode 实现未读。
- `D3voz/openjutsu` 的工作流 JSON（simple/advanced/object/face）未逐节点分析；其依赖 `comfyui-h3-oneclick-swap` 未克隆。
- `NyckM` 的 camera.py/meridian_convert.py 未读；Viggle Meridian 模型本身不在本簇。
- `Saganaki22/Viggle` 的 long_video_guide 未读。
- DMAD 4-step LoRA（`minimax_h3_DMAD_4step_full_lora_avg_rank_39_bf16`）的发布源在本簇仓库中只出现文件名（Yzmblog/DMAD 项目与 Kijai 转换），需另簇确认下载链接。
- ResCascade 不在 relevant.json，星数未知。
