# ComfyUI 节点速查：原生 MiniMax H3 节点 + 社区节点怎么接

> 原生部分依据 ComfyUI `comfy_extras/` 各发布版源码逐 tag 比对（v0.37.2 → v0.46.2，2026-11-21 核对）。社区节点的精读见 `docs/13-github-survey/01–07`。

## 1. 原生节点（`model/conditioning/minimax`）

| 节点 | 输入 | 要点 |
|------|------|------|
| `UNETLoader` | `minimax_h3_{fl2va,ref2va}[_pruned]_int8_convrot.safetensors`, weight_dtype `default` | int8 已进主线；旧 I8Fast 命名的量化文件要先转换 |
| `CLIPLoader` | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`, type **`minimax`** | 32B 视觉语言编码器；编码完会被卸载 |
| `VAELoader` ×2 | `minimax_h3_video_vae_int8_convrot.safetensors`（或 fp16）+ `minimax_h3_audio_vae_fp32.safetensors` | 视频 / 音频两个 VAE 都要接 |
| `EmptyMiniMaxH3LatentAV` | width 1344, height 768, length 124（步进 17，自动吸到 17k+5） | 纯文生用 |
| `MiniMaxH3ImageToVideo` | prompt, width, height, length, `first_frame?`, `last_frame?` → positive + latent | FL2VA 权重；0/1/2 张图 = T2VA / I2VA（或 L2VA）/ FL2VA。`first_frame` 被直接拉伸到画布（不裁切），`last_frame` 居中裁切（0.37.2 源码）→ 首帧要按画布比例出图。官方模板默认 1344×768、`res_multistep` + `simple`、Turbo 8 步 LoRA 强度 1 |
| `MiniMaxH3AddGuide` | positive, vae, audio_vae, latent, `image?`（单帧或 5/22/39…帧的片段）, `audio?`, `frame_idx`（负数从尾部数） → positive | **多关键帧 / 片段锚定**：把一张图或一小段视频（含音轨）钉在任意帧；可链式多个。续接类节点大多基于它：上一段最后 22 帧锚在 frame 0。ComfyUI 官方多帧教程的三点：钉进去的图会居中裁切到画布；**只接在这个节点上的图，文本编码器看不到**——提示词要引用它（`<Picture N>`）就得同时接进 `ref_images`，官方多帧模板里 `<Picture 1>` 既是身份参考又是视频的首帧；它是条件不是视频转视频，采样仍从空 latent 开始。`comfy_submit.py --media` 对带首帧的 `ref2va` 段就是这么接的 |
| `MiniMaxH3ReferenceToVideo` | prompt, vae, audio_vae, width, height, length, `ref_image_size`（`match`/`max`）, 参考图 / 视频 / 视频音轨 / 独立音频（界面上是可增长的插槽；API 键名见下「Autogrow 键名」）→ positive + latent | Ref2VA 权重。**编号顺序 = 先图（Picture 1..i）、再视频（每个视频的音轨 Audio j 紧跟在 Video k 前）、最后独立音频**。`match`（默认）把每张参考**等比缩到生成画布的像素面积**（只缩不放、不裁切，宽高吸附到 32；1344×768 画布 ≈ 1 MP），`max` 只把短边限制到 2048（身份更准；参考 token 每一步都要带着走，可能慢几倍）。竖幅全身图不会被裁成横幅；多视图拼板在 `match` 下和单人图占同样的像素面积，所以板上每个人更小。不接 vae 时参考只进文本编码器 |
| `MiniMaxH3SigmaShift`（显示名 ModelSamplingMiniMaxH3） | model, shift_video 12, shift_audio 3 | 模型自带的默认值就是 12 / 3（0.37.2 `supported_models.py`），用默认值的时候不接这个节点结果一样。shift 按 LoRA 的版本来（作者公布的值，2026-11-22 读 ModelTC/Minimax-H3-Turbo 的规格表和 ModelTC/LightX2V 的配置文件）：FL2V 的 **v1.0** 768p 版（4 步、8 步）是 6 / 3；FL2V 8 步 **v1.2** 768p 版是 12 / 3；544p 档和 Ref2V 4 步 v0.1 是 12 / 3。其余文件（FL2V v1.1 / v1.3、Ref2V 的 768p 版）作者没有公布，本流程按模型默认的 12 / 3 用。**改了 shift 时 `BasicGuider` 和 `BasicScheduler` 的 `model` 都要接它的输出**：步数表是按调度器拿到的那个模型算的，而官方模板里调度器直接接 `UNETLoader`——只改引导器那一路，调度表仍按 12 算，模型却按 6 换算，会错位。`comfy_submit.py` 的预览会检查这一点 |
| `MiniMaxH3FunControlNetApply` | model, controlnet 权重, strength 1.0, start/end_percent, `control_video?`, `mask?`, `source_video?` | alibaba-pai Fun-Controlnet-Union（Canny/Depth/HED/MLSD/Pose + 修补），单文件 ~6.8 GiB，CFG 保持 1 |
| `MiniMaxH3LatentUpscaleWithModel` | latent upscale model（LBH 系列权重）, samples, width 2560, height 1440 | 只放大视频 latent，音频原样透传；做「草稿→精修二采」的第一步 |
| `PH3ImageConditioning`（≥ 0.44）/ `MiniMaxH3ImageConditioning`（≥ 0.45） | prompt, width/height(0=自动), image_1..9 | 单帧出图分支：P-H3-Image（在 fl2va 上挂 LoRA）与 MiniMax-H3-Image（独立 33B 图像模型）。0.37.2 没有这两个节点，用 Fizgig Still / Contact Sheet，或升级 ComfyUI；见 `image-stage.md` |
| 采样 | `KSamplerSelect` → `BasicScheduler(simple, steps, denoise)` → `SamplerCustomAdvanced` | 挂 Turbo 用 `euler`（LoRA 作者 lightx2v 的示例工作流和说明用的是它），不挂 LoRA 的 20 步用 Comfy 官方模板的 `res_multistep`；`cfg` 固定 1.0 |
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

## 2. 官方模板默认值（Comfy-Org/workflow_templates，模板 JSON 2026-11-21 核对）

| 模板（面板里的名字 / 文件名） | 权重 | 模板默认的 LoRA | 步数 | 采样链 |
|------|------|------|------|-----------|
| MiniMax H3: Text / Image to Video（`video_minimax_h3_t2v` / `video_minimax_h3_i2v`） | `fl2va_pruned_int8_convrot` | `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16`（544p 档） | 调度器控件值 4（步数由模板里的开关驱动） | 同下 |
| MiniMax H3: Reference to Video（`video_minimax_h3_r2v`；`video_minimax_h3_multiframe_reference` 类似） | `ref2va_pruned_int8_convrot` | `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16`（544p 档、4 步） | 调度器控件值 20（同样由开关驱动） | `RandomNoise` → `KSamplerSelect(res_multistep)` → `BasicScheduler(simple)` → `BasicGuider` → `SamplerCustomAdvanced` → `VAEDecode` + `VAEDecodeAudio` → `CreateVideo` → `SaveVideo` |
| MiniMax H3 Fun ControlNet Union（`video_minimax_h3_fun_controlnet_union`） | fl2va + Fun-Controlnet-Union | — | — | — |

模板里的文本编码器是 `qwen3vl_32b_minimax_h3_nvfp4_awq`（CLIPLoader type `minimax`），VAE 是 `minimax_h3_video_vae_int8_convrot` + `minimax_h3_audio_vae_fp32`。提示词、帧数、分辨率、是否用 Turbo 都接在模板自带的原始值 / 开关节点上（`PrimitiveStringMultiline`、`PrimitiveInt`、`ResolutionSelector`、`ComfySwitchNode`），所以**步数和 LoRA 不要只看控件上的数**：模板默认的两个 LoRA 都是 544p 档，跑 1344×768 要换成 `_768p_` 版，步数改成 LoRA 的训练步数。

## 3. 把现成的工作流改成脚本能用的草稿档工作流

`comfy_submit.py` 不带工作流，它往**你导出的 API 版工作流**里写提示词、帧数和参考接线。改一次、导出两份就够用。起点有两个，推荐 A：

**A. 从 Turbo LoRA 作者的示例工作流开始（改得最少）**——GitHub `ModelTC/Minimax-H3-Turbo` 的 `example_workflows/`（2026-11-21 读过这三个 JSON；只用 ComfyUI 自带节点，作者写明要求 ComfyUI ≥ 0.31）：

- `video_minimax_h3_ref2v_lightx2v_turbo.json`：平铺的图，LoRA → `MiniMaxH3SigmaShift(12, 3)` → 引导器、`euler` + `simple`、`RandomNoise`、H3 参考节点的 `vae` 和 `audio_vae` 都已接好。要改的只有：底模 `minimax_h3_ref2va_bf16` 换成 `…ref2va_pruned_int8_convrot`（24 GB 装不下 bf16）；LoRA 从 4 步 544p 档换成 `minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16`，`BasicScheduler` 的步数 4 → 8；视频 VAE 可换成 int8 版省显存；宽高直接填 1344×768（它默认接的 `ResolutionSelector` 在 1 MP 档给的是 1376×768，不是训练格点）；再按下面第 3 步接两个 Sage 节点。
- `video_minimax_h3_i2v_lightx2v_turbo.json`（`i2va` / `fl2va` / `t2va` 共用）：包在一个子图里，外面能直接改 `lora_name`、`steps`、`shift_video`、`shift_audio`、`sampler_name`，调度器已经接在 shift 节点后面。LoRA 换成 `minimax_h3_fl2v_turbo_8step_v1.2_768p_comfyui_bf16`，步数 8，shift 保持它默认的 12 / 3（v1.2 就是按 12 / 3 跑的；换回 v1.0 的 768p 版才改成 6 / 3），宽高 1344×768。
- 导出前把宽高、步数这些由选择器 / 公式给出的值改成直接填数字，`comfy_submit.py` 的预览才读得到。

**B. 从 Comfy 官方模板开始**（模板面板里就有，但 LoRA、步数藏在开关后面，也没有 shift 节点）：

1. 打开模板 `video_minimax_h3_r2v`，先原样跑通一次。
2. LoRA 换成 `minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors`，强度 1.0；步数设 8（模板用开关控制步数时，把开关拨到 Turbo 那一档并确认 `BasicScheduler` 实际拿到的是 8）。
3. 在 LoRA 之后、采样之前依次接 KJNodes 的 `PathchSageAttentionKJ(auto)` → `MiniMaxH3MemoryEfficientSageAttentionPatch`（界面里搜到的名字是 `Patch Sage Attention KJ` 和 `MiniMax H3 Mem Eff Sage Attention Patch`；第一个的 `sage_attention` 选 `auto`），再接 `MiniMaxH3SigmaShift`（Ref2V：12 / 3）。
4. 分辨率 1344×768；`MiniMaxH3ReferenceToVideo` 的 `vae` 和 `audio_vae` 两个输入都要接上（不接的话参考图只进文本编码器、音色参考完全不起作用），`ref_image_size` 用 `match`。
5. 输出保持 `VAEDecode` + `VAEDecodeAudio` → `CreateVideo(24)` → `SaveVideo`。精修默认是在精修工作流里按同 seed 把一采重跑一遍再接放大，草稿工作流不用为它改什么；想把一采的 latent 存下来省掉重跑，要先用 `LTXVSeparateAVLatent` 拆开再各接一个 `SaveLatent`（自带的 `SaveLatent` 直接接 H3 的合并 latent 会报错，做法见 `quality-pipeline.md` §2；`comfy_submit.py` 只下载图片 / 视频 / 音频，latent 留在 ComfyUI 的 `output/latents/` 里）。
6. 菜单「工作流 → 导出（API）」存成 `workflows/draft_ref2va.api.json`（旧界面要先在设置里打开开发者模式才有这一项）。
7. 需要 `i2va` / `fl2va` / `t2va` 的段再用模板 `video_minimax_h3_i2v` 同样改一份（FL2VA 权重、`minimax_h3_fl2v_turbo_8step_v1.2_768p_comfyui_bf16`，shift 用默认的 12 / 3，不用加 shift 节点；如果用的是 v1.0 的 768p 版，才要加 `MiniMaxH3SigmaShift(6, 3)`，并把 `BasicScheduler` 的 `model` 从 `UNETLoader` 改接到它的输出，见 §1 表里那一行），导出成 `workflows/draft_fl2va.api.json`。`--media` 按段的模式找节点：`ref2va` 找 `MiniMaxH3ReferenceToVideo`，其余找 `MiniMaxH3ImageToVideo`，所以**每种权重各要一份工作流**。

脚本怎么认这份工作流：
- **种子**：任何带字面值 `seed` 或 `noise_seed` 的节点（模板里是 `RandomNoise`），`--batch N` 依次加一。
- **提示词 / 帧数 / 参考**：`--media` 直接写在 H3 节点上（原来连着的原始值节点会被字面值替换），参考图和音色按 `.media.json` 的顺序新建 `LoadImage` / `LoadAudio` 接上，模板里原有的参考输入会被清掉。
- **首帧（`ref2va` 段）**：`--media` 把首帧接成 `<Picture 1>`，同时自动加一个 `MiniMaxH3AddGuide`、把它钉在第 0 帧（插在 H3 参考节点和引导器之间，即官方多帧模板的接法；需要 H3 参考节点接了 `vae`）。只想让它当参考、不钉帧就加 `--no-anchor`。导出草稿工作流时不要自带 AddGuide 节点——脚本不会动它们，里面的图会被钉进每一段。`i2va` / `fl2va` 段不走这条路，首尾帧直接接 `MiniMaxH3ImageToVideo`。
- **想看脚本到底接成了什么**：加 `--write-workflow <路径>`，把最终要提交的工作流写成文件。
- **预览里的设置**：接在原始值节点上的数能读出来；由开关或公式算出来的（模板的步数、`ResolutionSelector` 的宽高）读不到，预览会写明「在工作流里计算」——这种情况要在 ComfyUI 窗口里确认一次，或者把它们改成直接填数字再导出，预览和 advice 才能替你把关。

```
UNETLoader(ref2va_pruned_int8) → LoraLoaderModelOnly(ref2v_turbo_8step_v1.1_768p, 1.0)
  → PathchSageAttentionKJ(auto) → MiniMaxH3MemoryEfficientSageAttentionPatch [两个都是 KJNodes] → model   [用默认 shift 12 / 3 时到此为止；FL2V v1.0 的 768p 版再接 MiniMaxH3SigmaShift(6, 3)]
CLIPLoader(qwen3vl nvfp4, minimax) → clip；VAELoader ×2 → vae / audio_vae
LoadImage ×N（按 media.json 顺序）→ MiniMaxH3ReferenceToVideo(clip, vae, audio_vae, prompt, 1344×768, 243, match) → positive, latent
RandomNoise(noise_seed) + KSamplerSelect(euler) + BasicScheduler(model, simple, 8) + BasicGuider(model, positive) → SamplerCustomAdvanced → latent   [两处 model 都接上一行的输出]
VAEDecode(video vae) + VAEDecodeAudio(audio vae) → CreateVideo(24) → SaveVideo
```

出图也可以用同一个脚本排队：把 `image_qwen_image_2_1_t2i` 或 `image_qwen_image_edit_2511_int8` 模板导出成 API 版，`comfy_submit.py workflows/qwen_t2i.api.json --set <提示词节点id>.<输入名>=@bible/prompts/lin_lan_bust.txt --batch 6 --out bible/candidates/lin_lan --tag bust --dry-run`，预览确认后带 `--confirm` 提交——这样出图也有批次预览、不会重复提交。

草稿分两档（见 `local-stack-and-acceleration.md` §2）：默认直接在 1344×768 出，片段可以采纳并走 latent 二采；864×480 / 960×544 只作快速预览，选中后在 1344×768 重跑出来的是一条新片段，要重新选片。

## 4. 社区节点分类（详见各精读文件）

| 需求 | 首选 | 备选 |
|------|------|------|
| 单节点多模式（T2V/I2V/FL/Ref 一个口） | `nkxx188/ComfyUI-MiniMaxH3-Easy` | `FX-FeiHou/ComfyUI-FeiHou-Easy-H3`（GPL） |
| 时间线式多镜头编排 | 见 `ecosystem-map.md` 的导演台一栏（调研底稿 `01-directors-and-timelines.md` 不随 skill 安装） | — |
| 段间续接 | 默认不续接（硬切）；确实要接见 `continuity-long-video.md` | 原生 `MiniMaxH3AddGuide` 手搭 |
| 加速 | SageAttention（KJNodes patch）+ Turbo 8 步 | Sol-Attn（Blackwell） |
| 超分 / 精修 | 原生 LatentUpscaleWithModel + LBH 权重二采 | Tr1dae 重加噪、SeedVR2 像素级 |
| 提示词改写 | 本地 Qwen + 官方 skill 规则 | 见 `04-prompting-tools.md` |
