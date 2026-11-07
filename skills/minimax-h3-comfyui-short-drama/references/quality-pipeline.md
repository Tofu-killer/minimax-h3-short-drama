# 画质流水线：768P 草稿 → 1920×1088 成片（含角色卡、人脸、音频、可控性）

> 依据 `docs/13-github-survey/06-quality-upscale-refine-control.md`（27 个画质 / 可控性仓库源码级精读）。前提：RTX 4090 24 GB、int8_convrot、Turbo LoRA、Sage。目标 16:9 1920×1088。

## 0. 几条路线一览

| 路线 | 机制 | 保不保 take | 速度（作者硬件） | 适用 |
|------|------|------------|-----------------|------|
| **ResCascade / Tr1dae 二采**（首选） | LBH 3D latent 放大 → 同条件在 1920×1088 低 σ 重采，音频钉死 | 保（σ 0.45 起） | +1 min / 5 s（5090） | 电影质感成片 |
| RelayHires | AnimeSR 像素放大 → taeh3 → 1 步 DMAD σ 0.60 | 保 | ~118 s / 5 s | 漫剧 |
| bbaudio UltimateUpscale / LBH Split | 空间分块 + 时间分块二采 | 保 | 慢但不 OOM | 10–15 s 长段、显存紧 |
| LBH 示例 0.9035 三步 / NVIDIA Open-H3-Regenerate 0.909 | 高 σ 重生成 | **改脸** | 72 GB 卡 122 s，16 GB 卡 3700 s | 接受重绘质感时才用 |
| 像素 SR（RealESRGAN x2 / RelayVSR / SeedVR2） | 不改内容只放大 | 保 | 快 | 最后一跳 |

## 1. Stage 0 · 资产（角色卡 / 剧照）

- **五视图**：`H3 Contact Sheet`（MAINodes / T8）+ matlod `minimax_h3_five_view_1024cont_s600` 0.75（或 `five_view_512_s1500` 1.0），fl2va pruned int8，`res_multistep` / `simple` 28 步，一张 `<Picture 1>` 定妆图。**用完立刻卸掉该 LoRA**。
- **带表情 / 台词的角色页**：OrbitSheets，硬切 6 视图，每视图 0.75–1 s，124 帧；写 `[Shot N] At 00:MM.mmm, the shot cuts to … locked-off static camera`，转动 ≤ 40°/s。
- **真单帧剧照 / 首帧**：`FizgigH3StillLatent + StillDecode`，≥ 3 MP（如 2304×1296），turbo v4_step600_ema **0.38** + er_sde simple 20 步；8 MP 海报无 Turbo 50 步。不用 `minimax_h3_t1_image_vae` 解视频。
- **姿势参考 → 角色设定单帧**：SingleFrame `Start End Frame Interpolate`（首帧姿势、末帧角色），RoPE patch 0–0.25。
- 三视图 LoRA 的选型与 RefMod 见 `lora-and-style.md`。

## 2. Stage 1 · 草稿抽卡

- 864×480–1344×768，Turbo 8 步（抽卡可 4 步），CFG 1，见 `local-stack-and-acceleration.md`。
- **保存一采 latent**（SaveLatent / Tr1dae Save Package / CGlide `.h3latent`），音频一并保留；后续精修与续接都从 latent 走，不要解码再编码（6 段后饱和 −14%、边缘脆化 +55%）。
- 电影质感且时间允许：中选镜头改用 **1 MP 原生 20 步 beta57** 重跑一采（或 Fast Tail：前 12 步 euler + 4 步 dpmpp_2m，−20%）；ResCascade 实测 Turbo 一采会丢细节 / 换 take，而精修阶段用 Turbo 无损。
- 音频差但画面好：`H3 Audio Refine Sampler` 冻结视频、6 步 `audio_denoise 0.5`，精修分支从 Turbo LoRA **之前**的 MODEL 分出。TTS 对白则 `MiniMax H3 Timed Audio(start_frame)` → `Exact Audio Lock`，同一 `start_frame` 接 `MiniMaxH3AddGuide.frame_idx`，成片混 `exact_audio`。

## 3. Stage 2 · 1 MP 阶段修补（放大前做）

- **远景小脸**：Carasibana FaceRefine：Track + Crop（768 画布，`largest_face` / identity_reference）→ Ref2VA 768×768 + 角色图 → Inject Video Latent → `MiniMaxH3NativeAudioLock`（原声保口型）→ Per-Frame Denoise 小脸 1.0 / 大脸 0.35（30 px / 120 px，smooth 9）→ simple 8 步 **denoise 0.40** + 8 步 Turbo → Stitch `face_only` dilation 24 feather 24。动漫换 deepghs 检测器 + clip_vision。
- **快动作糊**：MAINodes Motion Lab de-rope（inject 0.5 / 0.7）或 RelayHires 的「4 步 DMAD 从 0.8」。
- denoise 换算（shift 12）：`BasicScheduler denoise` 0.25 = σ 0.80，0.05 = σ 0.39；不要套 SDXL 经验，不要用 SplitSigmas 做低去噪。

## 4. Stage 3 · 放大精修到 1920×1088

**首选 ResCascade**：`LTXVSeparateAVLatent` → `H3 Hires Fix`（内置 LBH 3D，`lbh_model` fp16，`width 1920 / height 1088`，**`sigma_start 0.45`**，DMAD 4step LoRA 0.8 + `steps_override 2`；无 DMAD 时 `steps_override 0` 走原生 4 步；有 FaceRefine 结果接 `face_atlas`）→ `SamplerCustomAdvanced` euler + 节点输出 sigmas → 解码；音频自动钉死为一采原声。

**手搓等价**：`MinimaxH3LatentUpscaler3D`（`minimax_h3_latent_upscaler_3d_fp16.safetensors`，放 `models/latent_upscale_models/`；或原生 `MiniMaxH3LatentUpscaleWithModel`）只放大 video latent → `LTXVConcatAVLatent` 拼回原音频 → 在 1920×1088 **重建**同 prompt / 参考的 conditioning（Ref2VA 必须重建 Guider）→ `ManualSigmas 1.0, 0.7, 0.4, 0`（1 步 turbo 头 + 2 步 euler 尾；3 步尾 +17% 闪烁）→ euler + DisableNoise。
- σ 起点含义：0.31 软、**0.45 保 take**、0.56 重画五官、0.9 换片。
- 二采永远钉死一采音频（Tr1dae `audio_denoise=0`、bbaudio / T8 `preserve_first_pass`）。
- 二采用 euler / res_multistep 非祖先采样器；LMS 类多步法会把逐帧纹理外推成颗粒。

**漫剧**：RelayHires：AnimeSR 放大 → taeh3 编码 → 1 步 DMAD 0.8 从 σ 0.60，`window 4 / anchor_stride 8`；真人改 `RealESRGAN_x2plus`。

**10–15 s 或 OOM**：bbaudio `MMH3 Ultimate Upscale`（tile 576–768（32 倍数）、overlap 128、chunk 136–170 帧（17 倍数）/ overlap 17、anchor 0.999，二采 1–2 步 denoise 0.2–0.3，音频不重采）或 LBH `MMH3 Split Upscale`（`seam_denoise 0.5–0.8`）。多段续接的精修用 CGlide `Upscale Hold` 钉上一段精修尾。
- LBH 3D 对 > 32 latent 帧（> ~110 帧）走时间分块，检查首帧网格状字形伪影；短片关 `enable_temporal_chunking`。

## 5. Stage 4 · 可选最后一跳

- 想要 2K 重绘质感且接受细节变化：Open-H3-Regenerate 3 步（σ `0.909375, 0.857, 0.667, 0`；首尾帧钉住的草稿改 `start_sigma 0.8` 保脸），需 FL2VA + 12.4 GB 合并 LoRA + 6.5 GB 快速 VAE；4090 预计慢数倍，先只做 1080P。
- 只要更大尺寸：像素 SR（RelayVSR X4 / RealESRGAN_x2plus / SeedVR2）。

## 6. 可控性

- **FunControl**（核心已内置 `MiniMaxH3FunControlNetApply`）：多个 ControlNet 的强度是共享预算，depth 0.3 + pose 0.7，总和 ≤ 1.0；锁人用 pose 不用 depth；`end_percent 0.6`；strength > 1 无效；小人物先放大取景；稀疏注意力的 `morton` 必须 false 并接在 ControlNet 之前。
- **复刻参考片走位**：`reshot ref.mp4 --target h3 --control pose`（武打 / 舞蹈）或 depth，提示词写明 `<Video 1>` 里发生了什么并声明 `its grey depth look is not transferred`。
- **Ref-Patch**（FL2VA 仿 Ref2VA，112 键差分）：已有 int8 Ref2VA 时跳过。
- **局部重绘**：LanPaint（见 `lora-and-style.md`）。

## 6b. 长尾补充

- 二采 / 放大前 latent 宽高必须为偶数（像素被 32 整除），否则核心 circular padding 在右 / 下边缘出色条（`H3 Latent Upscale By -jingchen573` 或自算）。
- 手工重噪二采不用 stock `AddNoise`（CONST 流模型会被 `SamplerCustomAdvanced` 二次缩放成花屏），用 rockerBOO `MiniMaxH3AddNoise`，音频分支 sigma 按 shift 3 单独换算。
- Ref2VA 换人保脸：脸部特写单独作 `<Picture 2>` 并在提示词点名（ArcFace +0.12），同图重复第三次无效。
- Open-H3-Regenerate-2K 重画时保护人脸：YuNet 脸区图 + `face_strength 0.55`（脸从 σ 0.50 起），只挂 refiner LoRA、不叠 Turbo / Sharp，音频用草稿原音（ArcFace 0.52→0.91）。
- 道具 / 属性 / 材质类参考可用 Qwen-only 语义参考（`#tag`，不占 9/3/3 名额，256–512 px）；身份与具体帧锚才用原生 VAE 参考。
- 超分逐镜做，不对成片做；像素超分优先级：RelayVSR ×2（25 s）> RealESRGAN ×2（68 s）> SeedVR2（要纹理时）。

## 7. 禁忌

- LoRA 文件必须是带 alpha 的 `*_comfyui_alpha8` 或官方 `*_comfyui_bf16`；缺 PEFT alpha 的会把更新放大 ~16 倍整幅融化。
- 剪枝底模加载全量 LoRA 时的 51 行 `ERROR lora … adaln_proj` 可忽略（贡献 0.02%）。
- 不要同时装 CGlide 的 `cglide` 与 `ComfyUI-CGlide` 两份；不装 xmarre LBH `-Plus` 分支。
- 原生 VAE 解码固定 256 px tile 且每时间块写回 CPU；长片可用 Tr1dae `VAE Decode (fast)` 或 int8_convrot 视频 VAE（快 1.5×）。
- Pika H3 Flex 6 步是另一条 take 路线（LoRA 在 SigmaShift 前，ManualSigmas `1.0, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0`，lcm，CFG 1），不与 Turbo 叠。
