# ComfyUI 节点速查：原生 MiniMax H3 节点 + 社区节点怎么接

> 原生部分依据 ComfyUI `comfy_extras/` 各发布版源码逐 tag 比对（v0.37.2 → v0.46.2，2026-11-21 核对）。社区节点的精读见 `docs/13-github-survey/01–07`。

## 1. 原生节点（`model/conditioning/minimax`）

| 节点 | 输入 | 要点 |
|------|------|------|
| `UNETLoader` | `minimax_h3_{fl2va,ref2va}[_pruned]_int8_convrot.safetensors`, weight_dtype `default` | int8 已进主线；旧 I8Fast 命名的量化文件要先转换 |
| `CLIPLoader` | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`, type **`minimax`** | 32B 视觉语言编码器；编码完会被卸载 |
| `VAELoader` ×2 | `minimax_h3_video_vae_int8_convrot.safetensors`（或 fp16）+ `minimax_h3_audio_vae_fp32.safetensors` | 视频 / 音频两个 VAE 都要接 |
| `EmptyMiniMaxH3LatentAV` | width 1344, height 768, length 124（步进 17，自动吸到 17k+5） | 纯文生用 |
| `MiniMaxH3ImageToVideo` | prompt, width, height, length, `first_frame?`, `last_frame?` → positive + latent | FL2VA 权重；0/1/2 张图 = T2VA / I2VA（或 L2VA）/ FL2VA。官方模板默认 1344×768、`res_multistep` + `simple`、Turbo 8 步 LoRA 强度 1 |
| `MiniMaxH3AddGuide` | positive, vae, audio_vae, latent, `image?`（单帧或 5/22/39…帧的片段）, `audio?`, `frame_idx`（负数从尾部数） → positive | **多关键帧 / 片段锚定**：把一张图或一小段视频（含音轨）钉在任意帧；可链式多个。续接类节点大多基于它：上一段最后 22 帧锚在 frame 0 |
| `MiniMaxH3ReferenceToVideo` | prompt, vae, audio_vae, width, height, length, `ref_image_size`（`match`/`max`）, 参考图 / 视频 / 视频音轨 / 独立音频（界面上是可增长的插槽；API 键名见下「Autogrow 键名」）→ positive + latent | Ref2VA 权重。**编号顺序 = 先图（Picture 1..i）、再视频（每个视频的音轨 Audio j 紧跟在 Video k 前）、最后独立音频**。`match`（默认）把每张参考**等比缩到生成画布的像素面积**（只缩不放、不裁切，宽高吸附到 32；1344×768 画布 ≈ 1 MP），`max` 只把短边限制到 2048（身份更准；参考 token 每一步都要带着走，可能慢几倍）。竖幅全身图不会被裁成横幅；多视图拼板在 `match` 下和单人图占同样的像素面积，所以板上每个人更小。不接 vae 时参考只进文本编码器 |
| `MiniMaxH3SigmaShift`（显示名 ModelSamplingMiniMaxH3） | model, shift_video 12, shift_audio 3 | FL2V 768p Turbo LoRA 改 6 / 3；Ref2V 与 544p 版保持 12 / 3 |
| `MiniMaxH3FunControlNetApply` | model, controlnet 权重, strength 1.0, start/end_percent, `control_video?`, `mask?`, `source_video?` | alibaba-pai Fun-Controlnet-Union（Canny/Depth/HED/MLSD/Pose + 修补），单文件 ~6.8 GiB，CFG 保持 1 |
| `MiniMaxH3LatentUpscaleWithModel` | latent upscale model（LBH 系列权重）, samples, width 2560, height 1440 | 只放大视频 latent，音频原样透传；做「草稿→精修二采」的第一步 |
| `PH3ImageConditioning`（≥ 0.44）/ `MiniMaxH3ImageConditioning`（≥ 0.45） | prompt, width/height(0=自动), image_1..9 | 单帧出图分支：P-H3-Image（在 fl2va 上挂 LoRA）与 MiniMax-H3-Image（独立 33B 图像模型）。0.37.2 没有这两个节点，用 Fizgig Still / Contact Sheet，或升级 ComfyUI；见 `image-stage.md` |
| 采样 | `KSamplerSelect(res_multistep)` → `BasicScheduler(simple, steps, denoise)` → `SamplerCustomAdvanced` | 官方模板的采样器组合；`cfg` 固定 1.0 |
| 输出 | `CreateVideo(24 fps)` → `SaveVideo` | 24 fps 不要改 |

**提示词在节点里怎么被读**（`comfy/text_encoders/minimax.py`，v0.37.2 与 v0.46.2 一致）：文本编码器是 Qwen3-VL-32B（取第 50 层隐状态），**不套对话模板**，直接读原文。Ref2VA 的呈现顺序是：按接线顺序每张参考图前自动加一段 `<Picture i>: ` + 图像 token，每段参考音频加 `<Audio j>: `（音频本身不进编码器），参考视频加 `<Video k>: ` 和按 2 帧一组的 `<T.T seconds>` + 图像 token，**最后才是你的提示词**；FL2VA 是 `<Picture 1>: ` 首帧、`<Picture 2>: ` 尾帧、再接提示词。所以提示词里的 `<Picture N>` / `<Audio N>` 必须和接线顺序一一对应（`comfy_submit.py --media` 按 `.media.json` 的顺序接线并在预览里列出）。`<d>` 与 `</d>` 在分词器里各是一个专用 token（另有 `<|cutoff|>`、`<|lyrics_start|>` / `<|lyrics_end|>`、`<|caption_start|>` / `<|caption_end|>`）——台词标签必须原样写。本地节点对提示词**没有长度上限**（超出分词器单批才会报 `exceeds the supported prompt length`，实际碰不到）；7000 字符是云端 API 的限制。

**API 格式里的 Autogrow 键名**（ComfyUI `comfy_api/latest/_io.py` 与 `execution.py`，v0.37.2 与 v0.46.2 源码一致）：参考输入在提交的工作流里是**带点的扁平键**，从 0 编号——`"ref_images.ref_image_0": ["<LoadImage id>", 0]`、`"ref_images.ref_image_1": …`、`"ref_audios.ref_audio_0": ["<LoadAudio id>", 0]`、`"ref_videos.ref_video_0"`、`"ref_video_audios.ref_video_audio_0"`；服务器收到后自己还原成嵌套结构。`ref_image_0` 就是 `<Picture 1>`。写成列表或嵌套对象（`"ref_images": {…}`）不会被读到——不报错、参考被静默丢掉、出图像没给参考一样（两个独立项目踩到的是列表写法）。不用手写这些键：`scripts/comfy_submit.py --media prompts/ep01/s03.media.json` 会按提示词里的编号顺序建 LoadImage / LoadAudio 节点并接好，它的预检也会拦下错误写法和「提示词提到 `<Picture 5>` 但只接了 0 张图」这种情况。（此前本页写的是嵌套对象，那是错的，以这里为准。）

**FL2VA 链必须接 `VAEDecodeAudio`**：`MiniMaxH3ImageToVideo` 输出的是 AV latent，只接 `VAEDecode` 会误以为「FL2VA 没有音频」。

**Ref2VA 不要照 FL2VA 经验把 `shift_video` 改 6**：整条全黑（manju-studio 实测）；Ref2VA 用 12 / 3 或按 LoRA 说明。

### 原生节点从哪个版本开始有（逐 tag 源码核对，2026-11-21；当前最新 v0.46.2）

| ComfyUI 版本 | 新增的 H3 相关原生节点 |
|------|------|
| **0.37.2**（本 skill 的基线） | `EmptyMiniMaxH3LatentAV`、`MiniMaxH3ImageToVideo`、`MiniMaxH3ReferenceToVideo`、`MiniMaxH3AddGuide`、`MiniMaxH3SigmaShift`、`MiniMaxH3FunControlNetApply`；通用：`FrameInterpolationModelLoader` / `FrameInterpolate`（FILM / RIFE 插帧）、SeedVR2 全套、`ContextWindowsManual` |
| **0.44.0** | `MiniMaxH3ContextWindows`（官方滑窗长视频：context_length 124、context_overlap 39、fuse pyramid、freenoise 开、`split_conds_to_windows` 每窗一条提示词）、`MiniMaxH3LatentUpscaleWithModel`、`PH3ImageConditioning` |
| **0.45.0** | `MiniMaxH3ImageConditioning`、`RelayVSRConditioning`（像素超分 ×2 / ×4） |

- 0.37.2 上没有 `MiniMaxH3LatentUpscaleWithModel` 时用社区节点 `LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler`；FunControl 在 0.37.2 已是原生，不必装社区版。
- **要不要升级**：升到 ≥ 0.45 能拿到官方滑窗、原生 latent 放大、两个出图节点和 RelayVSR；升级前逐个核对已装节点的版本窗口（Spark-H3 跳过 0.41、只支持 0.38.x–0.40.x 与 0.42.x–0.44.x；Motion-Context 启动时会自检并拒绝不匹配的核心；FeiHou 流式块不与 kitchen 同用），并先整目录备份或另装一份便携版做 A/B，不要在唯一能出片的环境上直接升。

## 2. 官方模板默认值（Comfy-Org/workflow_templates）

| 模板 | 权重 | LoRA | 步数 | 分辨率/帧 |
|------|------|------|------|-----------|
| t2v / i2v / i2v_continuation | fl2va_pruned_int8 | fl2v_turbo_8step_v1.0 | 4（模板值，建议 8） | 1344×768 / 73 |
| r2v / multiframe_reference | ref2va_pruned_int8 | ref2v_turbo_4step_v0.1 | 20（模板值；用 Turbo 时改 4–8） | 1344×768 / 124，`match` |
| fun_controlnet_union | fl2va + Fun-Controlnet-Union | — | — | — |

模板里 LoRA 与步数不完全匹配（8 步 LoRA 配 4 步），自己用时把步数改成 LoRA 的训练步数。

## 3. 接线骨架（Ref2VA 草稿档）

```
UNETLoader(ref2va_pruned_int8) → LoraLoaderModelOnly(ref2v_turbo_8step_v1.1_768p, 1.0)
  → PathchSageAttentionKJ(auto) [KJNodes] → MiniMaxH3SigmaShift(12, 3)（FL2V 768p 用 6, 3）→ model
CLIPLoader(qwen3vl nvfp4, minimax) → clip
LoadImage ×N（按 media.json 顺序）→ MiniMaxH3ReferenceToVideo(prompt, 1344×768, 243, match) → positive, latent
SamplerCustomAdvanced(noise seed, model, positive, res_multistep, simple 8, latent) → latent
VAEDecode(video vae) + 音频解码(audio vae) → CreateVideo(24) → SaveVideo
```
草稿档把分辨率降到 864×480 或 960×544 抽卡（Turbo LoRA 换成 544p 训练版，即文件名里**不带** `768p` 的那个），中选后用同 seed 在 1344×768 重跑或走 latent 二采（见 `quality-pipeline.md`）。

## 4. 社区节点分类（详见各精读文件）

| 需求 | 首选 | 备选 |
|------|------|------|
| 单节点多模式（T2V/I2V/FL/Ref 一个口） | `nkxx188/ComfyUI-MiniMaxH3-Easy` | `FX-FeiHou/ComfyUI-FeiHou-Easy-H3`（GPL） |
| 时间线式多镜头编排 | 见 `01-directors-and-timelines.md` 结论 | — |
| 段间续接 | 见 `02-long-video-continuation.md` 结论 | 原生 `MiniMaxH3AddGuide` 手搭 |
| 加速 | SageAttention（KJNodes patch）+ Turbo 8 步 | Sol-Attn（Blackwell） |
| 超分 / 精修 | 原生 LatentUpscaleWithModel + LBH 权重二采 | Tr1dae 重加噪、SeedVR2 像素级 |
| 提示词改写 | 本地 Qwen + 官方 skill 规则 | 见 `04-prompting-tools.md` |
