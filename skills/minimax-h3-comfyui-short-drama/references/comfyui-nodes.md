# ComfyUI 节点速查：原生 MiniMax H3 节点 + 社区节点怎么接

> 原生部分依据 ComfyUI `comfy_extras/` 各发布版源码逐 tag 比对（v0.37.2 → v0.46.2，2026-11-21 核对）；0.37.2 的输入名、必填 / 可选、默认值另和一台真实 0.37.2 的 `/object_info` 逐项对过（2026-11-23）。表里带 `?` 的输入是可选的；括号里的「界面名」是在节点搜索框里要搜的名字。社区节点的精读见 `docs/13-github-survey/01–07`。

## 1. 原生节点（`model/conditioning/minimax`）

| 节点 | 输入 | 要点 |
|------|------|------|
| `UNETLoader` | `minimax_h3_{fl2va,ref2va}[_pruned]_int8_convrot.safetensors`, weight_dtype `default` | int8 已进主线；旧 I8Fast 命名的量化文件要先转换 |
| `CLIPLoader` | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`, type **`minimax`** | 32B 视觉语言编码器；编码完会被卸载 |
| `VAELoader` ×2 | `minimax_h3_video_vae_int8_convrot.safetensors`（或 fp16）+ `minimax_h3_audio_vae_fp32.safetensors` | 视频 / 音频两个 VAE 都要接 |
| `EmptyMiniMaxH3LatentAV`（界面名 Empty MiniMax H3 AV Latent） | width 1344, height 768, length 124（步进 17，自动吸到 17k+5） | 纯文生用 |
| `MiniMaxH3ImageToVideo`（界面名 MiniMax H3 Image to Video） | clip, vae, prompt, width, height, length, `first_frame?`, `last_frame?` → positive + latent | FL2VA 权重；0/1/2 张图 = T2VA / I2VA（或 L2VA）/ FL2VA。`first_frame` 被直接拉伸到画布（不裁切），`last_frame` 居中裁切（0.37.2 源码；2026-11-23 用真实节点实测：一张上三分之一是白的正方形图，当首帧进去白的部分仍占画面高度的 1/3——整张被压扁；当尾帧进去只剩 0.208——被居中裁掉了上下）→ 首帧要按画布比例出图。节点自己的默认值是 1344×768 × 124 帧；官方模板的默认设置见 §2 |
| `MiniMaxH3AddGuide`（界面名 Add Guide for MiniMax H3） | positive, latent, `frame_idx`（负数从尾部数）, `vae?`（接了 `image` 才需要）, `audio_vae?`（接了 `audio` 才需要）, `image?`（单帧或 5/22/39…帧的片段）, `audio?` → positive | **多关键帧 / 片段锚定**：把一张图或一小段视频（含音轨）钉在任意帧；可链式多个。续接类节点大多基于它：上一段最后 22 帧锚在 frame 0。ComfyUI 官方多帧教程的三点：钉进去的图会居中裁切到画布；**只接在这个节点上的图，文本编码器看不到**——要让它被当成 `<Picture N>` 看见，就得同时接进 `ref_images`；它是条件不是视频转视频，采样仍从空 latent 开始。官方多帧模板的实际接线（2026-11-23 读模板 JSON）：第一张图**只接 `ref_images`**，靠提示词里「`<Picture 1>` is the first frame of [Shot 1]」和保留关系当首帧兼身份参考；后面三个镜头的关键帧**只接这个节点**，各钉在 `round(秒 × 24)` 帧，提示词里照样写「`<Picture 2>` is the keyframe of [Shot 2], showing …」并逐张描述。`comfy_submit.py --media` 对带首帧的 `ref2va` 段默认也是只接成 `<Picture 1>`，加 `--anchor` 才再钉一次 |
| `MiniMaxH3ReferenceToVideo`（界面名 MiniMax H3 Reference to Video） | clip, prompt, width, height, length, `ref_image_size`（`match`/`max`）, `vae?`, `audio_vae?`（两个都标着可选，但不接的话参考图 / 音色只进文本编码器）, 参考图 / 视频 / 视频音轨 / 独立音频（界面上是可增长的插槽；API 键名见下「Autogrow 键名」）→ positive + latent | Ref2VA 权重。**编号顺序 = 先图（Picture 1..i）、再视频（每个视频的音轨 Audio j 紧跟在 Video k 前）、最后独立音频**。`match`（默认）把每张参考**等比缩到生成画布的像素面积**（只缩不放、不裁切，宽高吸附到 32；1344×768 画布 ≈ 1 MP），`max` 只把短边限制到 2048（身份更准；参考 token 每一步都要带着走，可能慢几倍）。竖幅全身图不会被裁成横幅；多视图拼板在 `match` 下和单人图占同样的像素面积，所以板上每个人更小。不接 vae 时参考只进文本编码器 |
| `MiniMaxH3SigmaShift`（界面名 **ModelSamplingMiniMaxH3**——搜 SigmaShift 搜不到） | model, shift_video 12, shift_audio 3 | 模型自带的默认值就是 12 / 3（0.37.2 `supported_models.py`），用默认值的时候不接这个节点结果一样。shift 按 LoRA 的版本来（作者公布的值，2026-11-22 读 ModelTC/Minimax-H3-Turbo 的规格表和 ModelTC/LightX2V 的配置文件）：FL2V 的 **v1.0** 768p 版（4 步、8 步）是 6 / 3；FL2V 8 步 **v1.2** 768p 版是 12 / 3（但它配不了 `pruned` 底模，见表后「LoRA 和底模对不对得上」）；544p 档和 Ref2V 4 步 v0.1 是 12 / 3。其余文件（FL2V v1.1 / v1.3、Ref2V 的 768p 版）作者没有公布，本流程按模型默认的 12 / 3 用。**改了 shift 时 `BasicGuider` 和 `BasicScheduler` 的 `model` 都要接它的输出**：步数表是按调度器拿到的那个模型算的，而官方模板里调度器直接接 `UNETLoader`——只改引导器那一路，调度表仍按 12 算，模型却按 6 换算，会错位。`comfy_submit.py` 的预览会检查这一点 |
| `MiniMaxH3FunControlNetApply`（界面名 Apply MiniMax H3 Fun ControlNet） | model, model_patch（`ModelPatchLoader` 读出的权重）, vae, strength 1.0, start/end_percent, `control_video?`, `mask?`, `source_video?` | alibaba-pai Fun-Controlnet-Union（Canny/Depth/HED/MLSD/Pose + 修补），单文件 ~6.8 GiB，CFG 保持 1 |
| `MiniMaxH3LatentUpscaleWithModel` | latent upscale model（LBH 系列权重）, samples, width 2560, height 1440 | 只放大视频 latent，音频原样透传；做「草稿→精修二采」的第一步 |
| `PH3ImageConditioning`（≥ 0.44）/ `MiniMaxH3ImageConditioning`（≥ 0.45） | prompt, width/height(0=自动), image_1..9 | 单帧出图分支：P-H3-Image（在 fl2va 上挂 LoRA）与 MiniMax-H3-Image（独立 33B 图像模型）。0.37.2 没有这两个节点，用 Fizgig Still / Contact Sheet，或升级 ComfyUI；见 `image-stage.md` |
| 采样 | `KSamplerSelect` → `BasicScheduler(simple, steps, denoise)` → `SamplerCustomAdvanced` | 挂 Turbo 用 `euler`（LoRA 作者 lightx2v 的示例工作流和说明用的是它），不挂 LoRA 的 20 步用 Comfy 官方模板的 `res_multistep`；`cfg` 固定 1.0 |
| 输出 | `VAEDecode` + `VAEDecodeAudio` → `CreateVideo(fps 24)` → `SaveVideo` | `CreateVideo` 的 `fps` **默认值是 30**，自己搭的图要填 24（官方模板里已经是 24）；API 里 `SaveVideo` 的输入写作 `"format": "auto", "format.codec": "auto", "codec": "auto"` |

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

**权重文件从哪个版本开始能加载**（同样是逐 tag 对着 `comfy/sd.py`、`comfy/quant_ops.py`、`comfy/model_detection.py` 查的，2026-11-23；这类文件在旧版本上不是「缺节点」，而是加载时报错或者悄悄出坏图）：

| ComfyUI 版本 | 新认得的文件 | 在 0.37.2 上会怎样 |
|------|------|------|
| **0.38.0** | `…_pruned_w6a8.safetensors`（6 bit 底模，格式 `w6a8_int8`，16.0 GB） | 加载报 `KeyError: 'w6a8_int8'`（0.37.2–0.37.4 的格式表里没有它） |
| **0.39.0** | 层数比官方少的视频 VAE（按文件里的层数建解码器）：LynnReal light VAE（26 层） | **不报错**地加载成 36 层，控制台 `Missing weight for layer decoder.transformer_blocks.26…35` + `Missing VAE keys`，画面是坏的（实际在 0.37.2 的加载代码上试过） |
| **0.41.0** | 编码器也剪过的视频 VAE：LightVAE Lite（12 层） | `WARNING: No VAE weights detected, VAE not initalized.`（实际试过：0.37.2 靠编码器里的一个键认这种 VAE，剪过的编码器没有它） |
| **0.42.0** | FastH3 Omni（末层叠着 PDD 头的蒸馏整模） | 识别出错的潜空间维数，见下面「FastH3 Omni」 |
| **0.44.0** | Sol-H3-VAE（`minimax_h3_sol_vae_*`，24 层整段解码器） | `WARNING: No VAE weights detected, VAE not initalized.`（实际试过） |

- 0.37.2 上没有 `MiniMaxH3LatentUpscaleWithModel` 时用社区节点 `LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler`；FunControl 在 0.37.2 已是原生，不必装社区版。
- **要不要升级**：升到 ≥ 0.45 能拿到官方滑窗、原生 latent 放大、两个出图节点和 RelayVSR，以及上表那几种更小、更快的权重（6 bit 底模省 5 GB 显存，Sol 解码器省解码时间——各自的数字见 `local-stack-and-acceleration.md` §2 与 `model-and-modes.md`）；升级前逐个核对已装节点的版本窗口（Spark-H3 跳过 0.41、只支持 0.38.x–0.40.x 与 0.42.x–0.44.x；Motion-Context 启动时会自检并拒绝不匹配的核心；FeiHou 流式块不与 kitchen 同用），并先整目录备份或另装一份便携版做 A/B，不要在唯一能出片的环境上直接升。

**latent 的实际形状**（2026-11-23，在真实的 0.37.2 上用真实的 H3 视频 / 音频 VAE 实测）：

- 视频 latent 是 `[1, 24, T, 高/16, 宽/16]`：24 个通道，空间 16 倍压缩；时间上每 17 帧对 5 个 latent 帧，所以帧数 `17k + 5` 对应 `T = 5k + 2`——124 帧 → 37，243 帧 → 72，22 帧 → 7。模型再按 2×2 打包：每个 latent 帧的 token 数 = (宽/32) × (高/32)。
- 所以一条片段的视频 token 数 = (宽/32) × (高/32) × (5k + 2)：1344×768 × 10 s = 42 × 24 × 72 = **72,576**；864×480 × 10 s = 27 × 15 × 72 = 29,160（前者的 0.40）；二采的 1920×1088 × 10 s = 60 × 34 × 72 = 146,880（一采的 2.02 倍）。耗时和显存跟着这个数走，比单看像素更准。
- 音频 latent 是 `[1, 32, 2, 40 × 秒数]`：32 个通道、双声道、每秒 40 步；解码出来是 32 kHz 立体声，时长和视频一致。
- **一条任务的完整序列**（用 KJNodes 的 `MiniMax H3 Token Counter` 在真实节点上数的——它用的是 ComfyUI 自己的排布代码，不采样就能数；接 H3 节点的 `latent` 和最后那个 `positive`）：一段 9 s、1344×768、6 张参考图、一条 6 s 音色、两个 `--anchor` 关键帧的任务是 **76,888 + 文本**，其中视频 67,536、参考图 6,086、关键帧 2,016（每个 1,008）、片段自己的音频 754（每秒 80）、音色样本 480。这次数的时候文本编码器是替身，所以上面的总数**不含文本侧**；文本侧另算——用 0.37.2 自己的分词器实测：这一段的提示词（491 个英文词）是 751 个 token，一条 950 词的六段式是 1,365 个（约 1.4–1.5 token / 词）；而且节点把每张参考图也交给文本编码器（`<Picture i>: ` + 图像块，按 32 px 一个 token 进条件序列，0.37.2 `text_encoders/minimax.py`），6 张图在文本侧又是约 6,100 个。加起来这一段的完整序列约 **83,800**。文本侧这个数后来实测到了（把文本编码器换成同一套代码、宽度缩小的微型版本，分词和视觉塔照常走）：一段 10 s、1344×768、5 张参考图（1024² 的脸两张、1024×1536 的全身、2688×1536 的场景、2048² 的道具）配 951 词的提示词，文本编码器输出 **6,504 个 token**——提示词 1,365，其余每张图约 1,030；同一次里 DiT 侧的 5 张参考图是 1,024 / 1,014 / 1,024 / 1,008 / 1,024。所以每张参考图的真实代价是 **约 2,000 个 token**（DiT 参考块 1,000 + 文本侧 1,000），6 张图合计占 15% 左右；提示词本身只占 1–2%，写长写短不影响耗时；音频和音色可以忽略。想知道自己某一段的准确数字，就在工作流里接这个节点（接真的文本编码器时它数的就是全部）。
- `VAEDecode` 和 `VAEDecodeAudio` 都直接吃采样器输出的那个音画合并 latent，各取自己那一路；`CreateVideo(fps 24)` 合成后帧数就是 H3 节点上的 `length`。
- **参考图进节点之后的实际大小**（`ref_image_size = match`，画布 1344×768；真实节点 + 真实 VAE 实测）：1024×1024 的脸保持 1024×1024，1024×1536 的全身缩成 832×1248，2688×1536 的场景和 1920×1080 的图都成了 1344×768，2048×2048 的道具成了 1024×1024——都被等比缩到画布的像素面积、再吸附到 32 的倍数，所以**每张参考图在 DiT 的参考块里大约 1,000 个 token，和原图多大无关**（6 张图 6,086 个；文本编码器一侧还要再算一份，见上一条）。一段 6 s 的音色样本是 240 步的音频 latent。改成 `max` 才按原图大小算（短边封顶 2048：2048×2048 的图是 4,096 个 token）。
- **`--anchor` 的接法实际跑过**：脚本接出来的两个 `MiniMaxH3AddGuide`（首帧钉第 0 帧、第二镜关键帧钉第 96 帧）在真实节点上执行通过，条件里得到两条关键帧，各是一帧 1344×768 的 latent；参考的顺序和提示词里的 `<Picture 1…6>`、`<Audio 1>` 一一对应。这次用的是替身文本编码器——H3 的条件节点、VAE 编码、关键帧都是真的，文本编码和采样没有跑。

**LoRA 和底模对不对得上**（2026-11-23：不下载整个文件，只读 HuggingFace 上各文件头部的张量名和形状，再对照 0.37.2 的加载代码）：

- 文件名里的 `pruned` 指去掉了时间嵌入器、把每层的时间调制（AdaLN）改存成 8 维曲线基的版本：`blocks.N.adaln_proj.linear.weight` 在 `pruned` 底模里是 `[96768, 8]`，在不带 `pruned` 的底模里是 `[96768, 2688]`。Ref2VA 和 FL2VA 的结构完全一样（各 932 个张量）。
- lightx2v 的 Turbo LoRA 除一个之外都是 **208 个模块**（50 层 × 注意力的 qkv / out、MLP 的 fc1 / fc2，加文本精炼器的 8 个），在 `pruned` 和不带 `pruned` 的底模上都能全部对上——Ref2V 的 4 步 v0.1、4 步 / 8 步 v1.0、8 步 v1.1，FL2V 的 8 步 v1.0（544p 与 768p）、v1.1、4 步 v1.3 都是这样。加载后控制台那行 `Model MiniMaxH3 prepared for dynamic VRAM loading. … 208 patches attached.` 就是这个数（0.37.2 `model_patcher.py`）。这一行只在 DynamicVRAM 开着时才有——N 卡上默认开；带 `--disable-dynamic-vram`、`--highvram`、`--gpu-only`、`--novram` 或 `--cpu` 启动时走旧的加载路径，只打印 `loaded completely …`，不报补丁数，那时看有没有 `ERROR lora` 就行。两条路径对 int8 底模挂 LoRA 的做法不同（源码）：DynamicVRAM 下 LoRA 以补丁的形式挂在各层上、随权重一起装载（`LowVramPatch`）；旧路径在装载时把这一层反量化、加上 LoRA、再量化回去。用自带的 `LoraLoaderModelOnly` 时这由 ComfyUI 决定，不用选；旧路径在一台没有显卡的 0.37.2 上用同样格式的微型 int8 模型实际走通过（记录在 GitHub 仓库的 `evals/results/iteration-13-miniature-model-and-retest-4.md`，安装包里不带 `evals/`）。
- **例外是 FL2V 8 步 v1.2**（2.1 GB，比别的大一点）：259 个模块，多出来的 51 个改的正是 AdaLN 层，按不带 `pruned` 的底模训练（形状 `[16, 2688]` / `[96768, 16]`）。挂在 `pruned` 底模上，ComfyUI 对这 51 个逐个报 `ERROR lora diffusion_model.blocks.N.adaln_proj.linear.weight shape … is invalid` 然后跳过（0.37.2 `weight_adapter/lora.py`），只有另外 208 个生效——少了时间调制那部分，效果没有保证。要完整用它得换不带 `pruned` 的 `minimax_h3_fl2va_int8_convrot`（34.0 GB，24 GB 显存装不下，要靠系统内存分担，慢）。所以本流程的 FL2V 默认是 **8 步 v1.0 的 768p 版 + shift 6 / 3**；`comfy_submit.py` 的预览见到 v1.2 配 `pruned` 会提醒。
- **FastH3 Omni（参考生视频的蒸馏整模）在 0.37.2 上加载不了**：HF `FastVideo/FastH3-Omni-Comfy`（旧名 `FastH3-OmniRef-Comfy`）的 `fasth3_omniref_8step_pruned_int8_convrot.safetensors`（22.2 GB）把 32 个 PDD 输出头叠在最后一层里。0.37.2 的识别代码会把叠起来的头数算进潜空间维数（读出 768 / 1024，正确值是 24 / 32），建出来的模型和文件对不上；从 **0.42.0** 起识别代码才按 `pdd_steps` 去除（逐个 tag 比对 `comfy/model_detection.py`）。它的官方模板 `video_fasth3_ominiref_r2v` 也不在 0.37.2 自带的模板包里。想用它（8 步、不挂 LoRA、shift 12 / 3、必须配 `Model Sparse Attention` 的 `vsa` 10%）得先把 ComfyUI 升到 ≥ 0.42。

## 2. 官方模板默认值（0.37.2 自带的模板包 0.11.69；2026-11-23 在真实的 0.37.2 前端里导出 API 后读出的实际值）

0.37.2 自带这些 H3 模板：`video_minimax_h3_t2v / _i2v / _r2v / _multiframe_reference / _i2v_continuation / _fun_controlnet_union`、`video_fastvideo_fasth3_t2v / _i2v`；出图有 `image_qwen_image_2_1_t2i`、`image_qwen_image_2_1_image_edit`、`image_qwen_image_edit_2511(_int8)`、`image_z_image_turbo(_int8)`。它们用到的节点 0.37.2 全都有。GitHub 上更新的模板（例如带提示词扩写分支的 Qwen 2.1 文生图、`image_minimax_h3_t2i`）和自带的不完全一样，以模板面板里的为准。

| 模板（面板里的名字 / 文件名） | 权重 | 开关里的 LoRA | 默认设置（开关关着） | 采样链 |
|------|------|------|------|-----------|
| MiniMax H3: Text / Image to Video（`video_minimax_h3_t2v` / `video_minimax_h3_i2v`） | `fl2va_pruned_int8_convrot` | `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16`（544p 档） | **20 步、不挂 LoRA**；画布 0.4 MP（t2v 864×480，i2v 640×640）；5 s。打开「Enable Lightning LoRA」= 8 步 + 左边的 LoRA | 同下 |
| MiniMax H3: Reference to Video（`video_minimax_h3_r2v`；`video_minimax_h3_multiframe_reference` 类似） | `ref2va_pruned_int8_convrot` | `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16`（544p 档、4 步） | **20 步、不挂 LoRA**；画布 864×480（16:9、0.4 MP）；5 s。打开开关 = 4 步 + 左边的 LoRA。多帧模板里三个 `MiniMaxH3AddGuide` 的 `vae`、`audio_vae`、`image` 都接着，帧号 = 秒 × 24 | `RandomNoise` → `KSamplerSelect(res_multistep)` → `BasicScheduler(simple)` → `BasicGuider` → `SamplerCustomAdvanced` → `VAEDecode` + `VAEDecodeAudio` → `CreateVideo` → `SaveVideo` |
| MiniMax H3 Fun ControlNet Union（`video_minimax_h3_fun_controlnet_union`；ComfyUI ≥ 0.35，Union 2.0 要 ≥ 0.38） | 模板用 `ref2va_pruned_int8_convrot`（官方教程：`fl2va` 也能配）+ `model_patches/minimax_h3_fun_controlnet_union_pruned_int8_convrot`（HF `Comfy-Org/MiniMax-H3`，放 `models/model_patches/`） | 同 r2v 模板 | 同 r2v 模板 | 模板里的姿态提取子图另要 HF `Comfy-Org/SDPose` 的 `sdpose_wholebody_fp16` 和 `rt_detr_v4-x-hgnet_fp16`；控制视频比目标长会被截断、短了停在最后一帧 |

模板里的文本编码器是 `qwen3vl_32b_minimax_h3_nvfp4_awq`（CLIPLoader type `minimax`），VAE 是 `minimax_h3_video_vae_int8_convrot` + `minimax_h3_audio_vae_fp32`。提示词、帧数、分辨率、是否用 Turbo 都接在模板自带的原始值 / 开关节点上（`PrimitiveStringMultiline`、`PrimitiveInt`、`ResolutionSelector`、`ComfySwitchNode`），所以**步数和 LoRA 不要只看控件上的数**：`comfy_submit.py` 的预览会顺着开关和选择器把实际生效的值读出来。模板开关里的两个 LoRA 都是 544p 档，跑 1344×768 要换成 `_768p_` 版，步数改成 LoRA 的训练步数——附带的工作流（`assets/workflows/`）已经这样改好了。

## 3. 把现成的工作流改成脚本能用的草稿档工作流

**先用附带的**：`assets/workflows/` 里有从上面这些模板导出、改成本流程设置的 API 版工作流（Ref2VA / FL2VA，各有带 Sage 和不带的；精修；文生图；编辑出图；一个不用模型的连通测试），每个都提交给真实的 ComfyUI 0.37.2 通过了校验，清单、要下的模型和常用的 `--set` 见 `assets/workflows/README.md`。下面的内容在两种情况下才需要：想知道这些工作流是怎么来的，或者要自己改一份。

**自己导出也可以不改图**：模板原样「导出（API）」的文件脚本就能读——开关选出的步数 / LoRA、`ResolutionSelector` 算出的宽高会在预览里显示实际值，要改的用 `--set`（例：`--set 146.value=true --set 144.value=8 --set 145.lora_name=minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors --set 136.width=1344 --set 136.height=768 --set 123.sampler_name=euler`，节点 id 以你导出的文件为准，预览里每行方括号中的就是）。

`comfy_submit.py` 往 API 版工作流里写提示词、帧数和参考接线。要在界面里改图再导出的话，起点有两个，推荐 A：

**A. 从 Turbo LoRA 作者的示例工作流开始（改得最少）**——GitHub `ModelTC/Minimax-H3-Turbo` 的 `example_workflows/`（2026-11-21 读过这三个 JSON；只用 ComfyUI 自带节点，作者写明要求 ComfyUI ≥ 0.31）：

- `video_minimax_h3_ref2v_lightx2v_turbo.json`：平铺的图，LoRA → `MiniMaxH3SigmaShift(12, 3)` → 引导器、`euler` + `simple`、`RandomNoise`、H3 参考节点的 `vae` 和 `audio_vae` 都已接好。要改的只有：底模 `minimax_h3_ref2va_bf16` 换成 `…ref2va_pruned_int8_convrot`（24 GB 装不下 bf16）；LoRA 从 4 步 544p 档换成 `minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16`，`BasicScheduler` 的步数 4 → 8；视频 VAE 可换成 int8 版省显存；宽高直接填 1344×768（它默认接的 `ResolutionSelector` 在 1 MP 档给的是 1376×768，不是训练格点）；再按下面第 3 步接两个 Sage 节点。
- `video_minimax_h3_i2v_lightx2v_turbo.json`（`i2va` / `fl2va` / `t2va` 共用）：包在一个子图里，外面能直接改 `lora_name`、`steps`、`shift_video`、`shift_audio`、`sampler_name`，调度器已经接在 shift 节点后面。LoRA 换成 `minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16`，步数 8，`shift_video` 改成 6、`shift_audio` 保持 3（v1.0 的 768p 版作者公布的值），宽高 1344×768。
- 导出前把宽高、步数这些由选择器 / 公式给出的值改成直接填数字，`comfy_submit.py` 的预览才读得到。

**B. 从 Comfy 官方模板开始**（模板面板里就有，但 LoRA、步数藏在开关后面，也没有 shift 节点）：

1. 打开模板 `video_minimax_h3_r2v`，先原样跑通一次。
2. LoRA 换成 `minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors`，强度 1.0；步数设 8（模板用开关控制步数时，把开关拨到 Turbo 那一档并确认 `BasicScheduler` 实际拿到的是 8）。
3. 在 LoRA 之后、采样之前依次接 KJNodes 的 `PathchSageAttentionKJ(auto)` → `MiniMaxH3MemoryEfficientSageAttentionPatch`（界面里搜到的名字是 `Patch Sage Attention KJ` 和 `MiniMax H3 Mem Eff Sage Attention Patch`；第一个的 `sage_attention` 选 `auto`），再接 `MiniMaxH3SigmaShift`（Ref2V：12 / 3）。
4. 分辨率 1344×768；`MiniMaxH3ReferenceToVideo` 的 `vae` 和 `audio_vae` 两个输入都要接上（不接的话参考图只进文本编码器、音色参考完全不起作用），`ref_image_size` 用 `match`。
5. 输出保持 `VAEDecode` + `VAEDecodeAudio` → `CreateVideo(24)` → `SaveVideo`。精修默认从草稿存下的一采 latent 开始：草稿提交时加 `--keep-latent`，精修时加 `--from-latent`，都不用改图（脚本自己加拆分、保存、读回的节点，见 `quality-pipeline.md` §2）；草稿当时没存 latent 的，精修工作流改给 `--seed`，按同 seed 把一采原样重跑一遍再接放大。草稿工作流不用为这两种做法改什么。
6. 菜单「工作流 → 导出（API）」存到项目的 `workflows/` 下，例如 `workflows/draft_ref2va.api.json`（自己导出的放项目里，和 skill 附带的 `assets/workflows/h3_ref2va*.api.json` 分开；旧界面要先在设置里打开开发者模式才有这一项）。
7. 需要 `i2va` / `fl2va` / `t2va` 的段再用模板 `video_minimax_h3_i2v` 同样改一份（FL2VA 权重、`minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16`，在 LoRA 后面加 `MiniMaxH3SigmaShift(6, 3)`，并把 `BasicScheduler` 的 `model` 从 `UNETLoader` 改接到它的输出，见 §1 表里那一行），导出成 `workflows/draft_fl2va.api.json`。`--media` 按段的模式找节点：`ref2va` 找 `MiniMaxH3ReferenceToVideo`，其余找 `MiniMaxH3ImageToVideo`，所以**每种权重各要一份工作流**。

脚本怎么认这份工作流：
- **种子**：任何带字面值 `seed` 或 `noise_seed` 的节点（模板里是 `RandomNoise`），`--batch N` 依次加一；种子接在 `Primitive*` 原始值节点上时改那个节点的值。工作流里有几处种子就一起设成同一个数（精修工作流里一采和 `H3 Hires Fix` 用同一个）。种子由别的节点算出来时 `--batch` / `--seed` 会拒绝并说明要改哪里。
- **提示词 / 帧数 / 参考**：`--media` 直接写在 H3 节点上（原来连着的原始值节点会被字面值替换），参考图和音色按 `.media.json` 的顺序新建 `LoadImage` / `LoadAudio` 接上，模板里原有的参考输入会被清掉。文件传到 ComfyUI 的 `input/` 时改名为「原名里的英文数字部分 + 内容指纹前 8 位」（如 `face_3eb734e6.png`）：两个角色的图都叫 `face.png` 也不会互相覆盖，中文文件名也不会出问题。
- **首帧和各镜关键帧（`ref2va` 段）**：`--media` 把首帧接成 `<Picture 1>`、把写了 `keyframe` 的镜头的图依次接成后面的 `<Picture N>`，提示词里已经声明它们各是哪一镜的首帧 / 关键帧并要求完整保留——官方多帧模板对第一张图就是这么处理的。加 `--anchor`：脚本再给每张图加一个 `MiniMaxH3AddGuide`，首帧钉在第 0 帧、关键帧钉在该镜切点那一帧，串在 H3 参考节点和引导器之间（官方多帧模板对后几个镜头的关键帧是这么钉的；需要参考节点接了 `vae`；图会被居中裁切到画布）。想让画面**严格**从某一帧起（比如拿上一段的尾帧接着演）时用它。两种做法哪个更稳没有在真机上比过。导出草稿工作流时不要自带 AddGuide 节点——脚本不会动它们，里面的图会被钉进每一段。`i2va` / `fl2va` 段不走这条路，首尾帧直接接 `MiniMaxH3ImageToVideo`。
- **想看脚本到底接成了什么**：加 `--write-workflow <路径>`，把最终要提交的工作流写成文件。
- **预览里的设置**：字面值、原始值节点、`If/Else Switch` 开关（条件读得出来时）和 `ResolutionSelector`（和节点同一套算法）都能读出实际生效的值，并且只列真正会跑到的那条分支——开关关着时那条 LoRA 不会出现在预览和 advice 里；预览第一行会写明每个开关现在是开是关、翻它该 `--set` 哪个节点。数学表达式和自定义节点算出来的值读不到，预览会写明「在工作流里计算」，那种情况在 ComfyUI 窗口里确认一次。
- **预检和 ComfyUI 的规则一致**：每个节点的类都要装了；输入只检查连着输出节点的那部分（`--media` 接线后不再连着输出的模板示例图、帧数公式不会被检查，ComfyUI 也不管它们）；但开关的两条分支 ComfyUI 都会校验——关着的分支里的 LoRA 文件也得在。
- **任务失败时**脚本把 ComfyUI 返回的整段堆栈压成一行（哪个节点、什么错），显存不足和模型文件不完整会直接点明，同一行也记进该 take 的 `run.json`。

```
UNETLoader(ref2va_pruned_int8) → LoraLoaderModelOnly(ref2v_turbo_8step_v1.1_768p, 1.0)
  → PathchSageAttentionKJ(auto) → MiniMaxH3MemoryEfficientSageAttentionPatch [两个都是 KJNodes] → model   [用默认 shift 12 / 3 时到此为止；FL2V v1.0 的 768p 版再接 MiniMaxH3SigmaShift(6, 3)]
CLIPLoader(qwen3vl nvfp4, minimax) → clip；VAELoader ×2 → vae / audio_vae
LoadImage ×N（按 media.json 顺序）→ MiniMaxH3ReferenceToVideo(clip, vae, audio_vae, prompt, 1344×768, 243, match) → positive, latent
RandomNoise(noise_seed) + KSamplerSelect(euler) + BasicScheduler(model, simple, 8) + BasicGuider(model, positive) → SamplerCustomAdvanced → latent   [两处 model 都接上一行的输出]
VAEDecode(video vae) + VAEDecodeAudio(audio vae) → CreateVideo(24) → SaveVideo
```

出图也用同一个脚本排队，工作流用附带的 `qwen21_t2i.api.json`（营利项目换 `zimage_turbo_t2i.api.json`，提示词节点是 `57:27.text`、尺寸节点 `57:13`）和 `qwen_edit2511_{1,2,3}ref.api.json`：`comfy_submit.py <skill>/assets/workflows/qwen21_t2i.api.json --set 459:452.prompt=@bible/prompts/lin_lan_bust.txt --batch 6 --seed 1 --out bible/candidates/lin_lan --tag bust --dry-run`，预览确认后带 `--confirm` 提交——这样出图也有批次预览、不会重复提交（每类图的命令见 `image-stage.md` §4 和 `assets/workflows/README.md`）。

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
