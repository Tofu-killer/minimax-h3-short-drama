# ComfyUI 节点速查：原生 MiniMax H3 节点 + 社区节点怎么接

> 原生部分依据 ComfyUI `comfy_extras/nodes_minimax_h3.py`（master，2026-11-07 抓取）。社区节点的精读见 `docs/13-github-survey/01–07`。

## 1. 原生节点（`model/conditioning/minimax`）

| 节点 | 输入 | 要点 |
|------|------|------|
| `UNETLoader` | `minimax_h3_{fl2va,ref2va}[_pruned]_int8_convrot.safetensors`, weight_dtype `default` | int8 已进主线；旧 I8Fast 命名的量化文件要先转换 |
| `CLIPLoader` | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`, type **`minimax`** | 32B 视觉语言编码器；编码完会被卸载 |
| `VAELoader` ×2 | `minimax_h3_video_vae_int8_convrot.safetensors`（或 fp16）+ `minimax_h3_audio_vae_fp32.safetensors` | 视频 / 音频两个 VAE 都要接 |
| `EmptyMiniMaxH3LatentAV` | width 1344, height 768, length 124（步进 17，自动吸到 17k+5） | 纯文生用 |
| `MiniMaxH3ImageToVideo` | prompt, width, height, length, `first_frame?`, `last_frame?` → positive + latent | FL2VA 权重；0/1/2 张图 = T2VA / I2VA（或 L2VA）/ FL2VA。官方模板默认 1344×768、`res_multistep` + `simple`、Turbo 8 步 LoRA 强度 1 |
| `MiniMaxH3AddGuide` | positive, vae, audio_vae, latent, `image?`（单帧或 5/22/39…帧的片段）, `audio?`, `frame_idx`（负数从尾部数） → positive | **多关键帧 / 片段锚定**：把一张图或一小段视频（含音轨）钉在任意帧；可链式多个。续接类节点大多基于它：上一段最后 22 帧锚在 frame 0 |
| `MiniMaxH3ReferenceToVideo` | prompt, vae, audio_vae, width, height, length, `ref_image_size`（`match`/`max`）, `ref_image_1..9`, `ref_video_1..3`, `ref_video_audio_1..3`, `ref_audio_1..3` → positive + latent | Ref2VA 权重。**编号顺序 = 先图（Picture 1..i）、再视频（每个视频的音轨 Audio j 紧跟在 Video k 前）、最后独立音频**。`match` 把参考缩到生成画布面积（省显存），`max` 用 2048 短边（身份更准、更慢）。不接 vae 时参考只进文本编码器 |
| `MiniMaxH3SigmaShift`（显示名 ModelSamplingMiniMaxH3） | model, shift_video 12, shift_audio 3 | FL2V 768p Turbo LoRA 改 6 / 3；Ref2V 与 544p 版保持 12 / 3 |
| `MiniMaxH3FunControlNetApply` | model, controlnet 权重, strength 1.0, start/end_percent, `control_video?`, `mask?`, `source_video?` | alibaba-pai Fun-Controlnet-Union（Canny/Depth/HED/MLSD/Pose + 修补），单文件 ~6.8 GiB，CFG 保持 1 |
| `MiniMaxH3LatentUpscaleWithModel` | latent upscale model（LBH 系列权重）, samples, width 2560, height 1440 | 只放大视频 latent，音频原样透传；做「草稿→精修二采」的第一步 |
| `PH3ImageConditioning` | prompt, width/height(0=自动), image_1..9 | p-h3-image 单帧出图分支（角色卡 / 剧照） |
| 采样 | `KSamplerSelect(res_multistep)` → `BasicScheduler(simple, steps, denoise)` → `SamplerCustomAdvanced` | 官方模板的采样器组合；`cfg` 固定 1.0 |
| 输出 | `CreateVideo(24 fps)` → `SaveVideo` | 24 fps 不要改 |

**API 格式里的 Autogrow 键名**：`ref_images` / `ref_videos` / `ref_video_audios` / `ref_audios` 是嵌套对象，子键从 0 计：`"ref_images": {"ref_image_0": ["<LoadImage id>", 0], "ref_image_1": …}`。写成列表不报错但参考被**静默忽略、出图全黑**（两个独立项目踩到）。`comfy_submit.py --set` 无法直接写嵌套键，用导出的 API JSON 作模板、只替换 LoadImage 的 `image`。

**Ref2VA 不要照 FL2VA 经验把 `shift_video` 改 6**：整条全黑（manju-studio 实测）；Ref2VA 用 12 / 3 或按 LoRA 说明。

版本提示：FunControl 与 LatentUpscaleWithModel 是 2026-10 之后进主线的；ComfyUI 0.37 若没有这两个节点，先用社区节点 `wyzborrero/ComfyUI-H3-FunControl`、`LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler`，或升级 ComfyUI（升级前确认 Spark-H3 / FeiHou 等依赖 kitchen 的节点兼容）。

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
草稿档把分辨率降到 864×480 或 1056×608 抽卡，中选后用同 seed 在 1344×768 重跑或走 latent 二采（见 `quality-pipeline.md`）。

## 4. 社区节点分类（详见各精读文件）

| 需求 | 首选 | 备选 |
|------|------|------|
| 单节点多模式（T2V/I2V/FL/Ref 一个口） | `nkxx188/ComfyUI-MiniMaxH3-Easy` | `FX-FeiHou/ComfyUI-FeiHou-Easy-H3`（GPL） |
| 时间线式多镜头编排 | 见 `01-directors-and-timelines.md` 结论 | — |
| 段间续接 | 见 `02-long-video-continuation.md` 结论 | 原生 `MiniMaxH3AddGuide` 手搭 |
| 加速 | SageAttention（KJNodes patch）+ Turbo 8 步 | Sol-Attn（Blackwell） |
| 超分 / 精修 | 原生 LatentUpscaleWithModel + LBH 权重二采 | Tr1dae 重加噪、SeedVR2 像素级 |
| 提示词改写 | 本地 Qwen + 官方 skill 规则 | 见 `04-prompting-tools.md` |
