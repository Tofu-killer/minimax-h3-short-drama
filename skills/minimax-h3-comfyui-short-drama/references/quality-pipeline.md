# 画质流水线：768P 草稿 → 1920×1088 成片（含角色卡、人脸、音频、可控性）

> 依据 `docs/13-github-survey/06-quality-upscale-refine-control.md`（27 个画质 / 可控性仓库源码级精读），并已并入长尾补充、补读新增与新仓库实证（`11-fresh-repos.md`）。前提：RTX 4090 24 GB、int8_convrot、Turbo LoRA、Sage。目标 16:9 1920×1088。

## 0. 几条路线一览

速度一列都是原作者机器上的数字（多为 5090）。**4090 上的二采、20 步定稿、分块放大都没有实测**——第一次跑时记下耗时和显存峰值再排期，不要拿表里的数向用户承诺时间。

| 路线 | 机制 | 保不保 take | 速度（作者硬件） | 适用 |
|------|------|------------|-----------------|------|
| **ResCascade / Tr1dae 二采**（首选） | LBH 3D latent 放大 → 同条件在 1920×1088 低 σ 重采，音频钉死 | 保（σ 0.45 起） | +1 min / 5 s（5090） | 电影质感成片 |
| RelayHires | AnimeSR 像素放大 → taeh3 → 1 步 DMAD σ 0.60 | 保 | ~118 s / 5 s | 漫剧 |
| bbaudio UltimateUpscale / LBH Split | 空间分块 + 时间分块二采 | 保 | 慢但不 OOM | 10–15 s 长段、显存紧 |
| LBH 示例 0.9035 三步 / NVIDIA Open-H3-Regenerate 0.909 | 高 σ 重生成 | **改脸** | 72 GB 卡 122 s，16 GB 卡 3700 s | 接受重绘质感时才用 |
| 像素 SR（RealESRGAN x2 / RelayVSR；SeedVR2 会改脸改嘴，真人近景不用） | 不改内容只放大 | 保 | 快 | 最后一跳 |

## 1. Stage 0 · 资产（角色卡 / 剧照）

- **五视图**：`H3 Contact Sheet`（MAINodes / T8）+ matlod `minimax_h3_five_view_1024cont_s600` 0.75（或 `five_view_512_s1500` 1.0），ref2va pruned int8（LoRA 的模型卡写明是在 `ref2va_pruned` 上训练的），`res_multistep` / `simple` 28 步，一张 `<Picture 1>` 定妆图。**用完立刻卸掉该 LoRA**。
- **带表情 / 台词的角色页**：OrbitSheets，硬切 6 视图，每视图 0.75–1 s，124 帧；写 `[Shot N] At 00:MM.mmm, the shot cuts to … locked-off static camera`，转动 ≤ 40°/s。（这是出图用的特例：每视图不到 1.2 s，`lint_prompt.py` 会报「镜头短于 1.2 s」，不走机检。）
- **真单帧剧照 / 首帧**：`FizgigH3StillLatent + StillDecode`，≥ 3 MP（如 2304×1296），turbo v4_step600_ema **0.38** + er_sde simple 20 步；8 MP 海报无 Turbo 50 步。不用 `minimax_h3_t1_image_vae` 解视频。
- **姿势参考 → 角色设定单帧**：SingleFrame `Start End Frame Interpolate`（首帧姿势、末帧角色），RoPE patch 0–0.25。
- **角色设定卡防撞脸**：每人 3–5 处骨相 + 发型 / 体型 / 体态 / 主色 / 标志六格，同项目禁复用「鼻梁挺直 / 黑发束髻 / 高挑修长」；写族裔、`height_cm + build`、一个跨场景锚点；给 H3 的参考用多张单人图而非一张多格板。
- 三视图 LoRA 的选型与 RefMod 见 `lora-and-style.md`。

## 2. Stage 1 · 草稿抽卡

- 864×480–1344×768，Turbo 8 步（只看构图、没有运镜的镜头可 4 步），CFG 1，见 `local-stack-and-acceleration.md`。
- **保存一采 latent**（SaveLatent / Tr1dae Save Package / CGlide `.h3latent`），音频一并保留；后续精修与续接都从 latent 走，不要解码再编码（6 段后饱和 −14%、边缘脆化 +55%）。
  - **推荐做法（存下一采的 latent）**：草稿提交时加 `--keep-latent`——脚本在工作流里加上拆分和两个 `SaveLatent`，每条 take 多出两个 `.latent` 文件（视频、音频各一个；1344×768 × 10 s 约 28 MB），和 mp4 一起取回 take 的文件夹。精修时用精修工作流加 `--from-latent <中选那条 take 的文件夹>`：脚本把这两个文件传回 ComfyUI、接到 `H3 Hires Fix` 的 `latent` 上，一采不再重跑——省下一次一采的时间，而且精修的就是那一条，不依赖「同 seed 重跑能不能复现」。提示词和参考照旧用 `--media` 给（二采的条件要用），预览会把这次的任务和那条 take 的记录对一遍：提示词与参考（不一致 = 二采被另一份文字或图片牵着走）、H3 节点上的画布（参考图和钉住的帧是按节点上的尺寸准备的，画布不同就和一采看到的不一样大——预览里给出要补的 `--set <节点>.width / height`）、帧数（latent 的长度是它自己的，条件却按节点上的帧数建）。Sage 和 Turbo 开关不比：一采不重跑，它们只影响二采（关了 Turbo 做二采时另有一条 `steps_override` 的 advice）。二采放大超过 1.75 倍（比如 864×480 的预览直接放到 1920×1088）也有一条 advice——本流程的一步是 1.43 倍，更大的没试过。
  - **备用做法（没存 latent 时）**：精修工作流 = 草稿工作流原样 + 后面接放大二采。提交时用 `comfy_submit.py --seed <中选那条的 seed>`，一采按同 seed、同设置重跑一遍，得到的就是中选的那一条，再往下精修。带二采节点的工作流不给 `--tag` 时自动用 `<段号>_refine`，结果落在 `<段号>_refine_<seed>`，不会压到草稿的目录；要并排留几版（不同的二采尺寸之类）再各给一个 `--tag`——落进一个已有别的结果的目录时，旧的会被挪进 `_prev_…`，批次预览里会提醒。多花一次一采的时间，但不用搬文件，`--media` 的接线也不用改。
  - **每条 take 记着自己是拿什么做的**：`run.json`（seed、提示词与参考的指纹、每个上传文件的 sha256、一采的设置）之外，文件夹里还有 `prompt.txt`（当时发给模型的提示词，一字不差）和 `media.json`（当时的参考清单，提示词指向旁边的 `prompt.txt`）。`prompts/<集>/<段>.txt` 会随分镜重写，这两份不会。用处：一条按旧提示词抽的片段被 `--stale-ok` 采纳之后，精修用 `--media <那条 take 的文件夹>/media.json`（`--out` 不用给，脚本认得这是 take 自己的副本，结果放在它旁边）——参考图本身没有复制，图后来换过内容的话预览照样会警告，这时到 ComfyUI 的 `input/` 里按 `run.json` 记的上传名能找到当时那张。`lint_prompt.py <take 文件夹>/prompt.txt` 也能直接查。
  - **`--keep-latent` / `--from-latent` 背后是什么**：ComfyUI 自带的 `SaveLatent` 直接接 H3 的输出会报错——H3 的 latent 是视频 + 音频两个张量合在一起的，`SaveLatent` 只会存单个张量（实测报 `'NestedTensor' object has no attribute 'contiguous'`）。所以先接自带的 `LTXVSeparateAVLatent` 拆成 video / audio 两路，各接一个 `SaveLatent`（落在 ComfyUI 的 `output/latents/`，脚本取回）；读回时两个文件要在 ComfyUI 的 `input/` 里（`LoadLatent` 只列那里的文件，脚本负责上传），两个 `LoadLatent` → `LTXVConcatAVLatent` 拼回去。社区的 Tr1dae Save Package / CGlide `.h3latent` 是把这几步包起来的节点。
  - **验证到哪一步**（2026-11-23，真实的 ComfyUI 0.37.2 + 真实的 H3 视频 / 音频 VAE 和 LBH 放大权重，CPU 上小尺寸）：拆分、存、取回、传回、读入、拼回、解码成带声音的视频，以及 LBH 放大（448×256 的 latent 放大到 640×352，音频 latent 原样带着）都实际跑通了；`H3 Hires Fix` 的二采要底模：真实的 33B 权重没有跑过；后来用一套结构相同、宽度很小的随机权重模型把两种做法都执行到了出片（`--from-latent` 和 `--seed` 重跑，含分块版和首帧段；验证的是接线和节点的运行时行为，画面是噪声）——真模型下二采的画质、耗时、显存仍然要在你的机器上确认。
- 电影质感且时间允许：中选镜头改用 **1 MP 原生 20 步 beta57** 重跑一采（或 Fast Tail：前 12 步 euler + 4 步 dpmpp_2m，−20%）；ResCascade 实测 Turbo 一采会丢细节 / 换 take，而精修阶段用 Turbo 无损。重跑出来的是另一条片段，要重新选片和观测。
- 音频差但画面好：`H3 Audio Refine Sampler` 冻结视频、6 步 `audio_denoise 0.5`，精修分支从 Turbo LoRA **之前**的 MODEL 分出。TTS 对白的锁音频接法以 `audio-and-post.md` 链路 B 为准（逐句用 `MiniMaxH3DialogueAudioLock`，整条歌 / 口播用 `MiniMaxH3ExactAudioLock`）：`MiniMax H3 Timed Audio(start_frame)` → 锁音频节点，同一 `start_frame` 接 `MiniMaxH3AddGuide.frame_idx`，成片混 `exact_audio`。

## 3. Stage 2 · 1 MP 阶段修补（放大前做）

- **远景小脸**：Carasibana FaceRefine：Track + Crop（768 画布，`largest_face` / identity_reference）→ Ref2VA 768×768 + 角色图 → Inject Video Latent → `MiniMaxH3NativeAudioLock`（原声保口型）→ Per-Frame Denoise 小脸 1.0 / 大脸 0.35（30 px / 120 px，smooth 9）→ simple 8 步 **denoise 0.40** + 8 步 Turbo → Stitch `face_only` dilation 24 feather 24。动漫换 deepghs 检测器 + clip_vision。
- **远景小脸（σ 重绘路线）**：只处理 **30–140 px** 的匹配脸，裁 2.6× 方框到 512²，σ 0.8 起重绘（0.6 更锐但保留错脸型），椭圆 0.75 羽化 0.35 贴回并颜色匹配。
- **人脸身份门禁**：YuNet 0.6 + SFace，同人阈值 0.363，锁脸交付 keep 0.55（严格 0.65）；只信 ≥ 40 px 正脸、逐帧独立匹配不链式；分数是警告，真实感优先。
- **快动作糊**：MAINodes Motion Lab de-rope（inject 0.5 / 0.7）或 RelayHires 的「4 步 DMAD 从 0.8」。
- denoise 换算（shift 12）：`BasicScheduler denoise` 0.25 = σ 0.80，0.05 = σ 0.39；不要套 SDXL 经验，不要用 SplitSigmas 做低去噪。

## 4. Stage 3 · 放大精修到 1920×1088

**首选 ResCascade 的 `H3 Hires Fix`**——放大和二采在一个节点里做完。**工作流用附带的** `assets/workflows/h3_ref2va_refine.api.json`（草稿用的是带 Sage 的版本就用 `h3_ref2va_sage_refine.api.json`）：它就是草稿工作流加上这个节点，`comfy_submit.py <它> --media <同一个 .media.json> --seed <中选那条的 seed> --tag <段>_refine`。下面的接法是 2026-11-21 读它 main 分支源码（`hires.py`）和 README 得到的；2026-11-23 把当天的版本装进一台真实的 ComfyUI 0.37.2，节点能加载、附带的精修工作流通过了服务器校验；同一天稍后用微型的随机权重模型把它们实际执行到了出片（控制台打印 `[H3HiresFix] (16, 28) -> (22, 40), sigmas [0.45, 0.225, 0.0]`）。**真实权重下的二采没有跑过**：画质、耗时、显存要第一次用时确认。

- **节点的名字和输入**（真实 `/object_info`）：类名 `H3HiresFix`，界面里搜「H3 Hires Fix (1 MP -> bigger, audio pinned)」。必填 `model`、`positive`、`latent`、`width`（1920）、`height`（1088）、`sigma_start`（0.45）、`seed`、`lbh_model`（下拉里是 `models/latent_upscale_models/` 下的文件，没放权重时只有 `(none)`）；可选 `images`、`vae`、`schedule_steps`（20）、`steps_override`（0）、`face_atlas`、`face_margin`（2.0）。输出 `latent`、`sigmas`。

- **接线**：一采采样器输出的 latent 直接接它的 `latent`（音画合并的那个，不用先拆）；一采的 `positive` 接 `positive`；`model` 接一采用的模型；`width 1920 / height 1088`、**`sigma_start 0.45`**、`lbh_model` 选 LBH 的 fp16 权重。采样在节点内部完成（euler），输出就是 1920×1088 的成品 latent，后面直接接 `VAEDecode` + `VAEDecodeAudio`，不用再接采样器；音频是钉死的一采原声。
- **参考条件不用重建**：Ref2VA 的参考原样沿用（它们有自己的网格）；按一采尺寸编码的关键帧节点会自动丢掉（放大的画面里已经有了）——`i2va` / `fl2va` 的首帧、尾帧是这样，`ref2va` 段用 `--anchor` 钉上去的首帧和各镜关键帧也是这样（控制台会打印 `dropped N pass-1 keyframe(s)`）。所以精修工作流里仍然只有一个 H3 条件节点，`comfy_submit.py --media` 照常接线。`i2va` / `fl2va` / `t2va` 段有自己的一组文件：`assets/workflows/h3_fl2va_refine.api.json`、`h3_fl2va_sage_refine.api.json`（用法相同）。用微型随机权重模型实际执行时，节点对一段带首帧和尾帧的任务打印的是 `[H3HiresFix] dropped 2 pass-1 keyframe(s) (start/end image) sized for pass 1`。
- **`model` 和步数有三种配法**：① 一采的模型原样接进来（同样的 LoRA 和 shift），`steps_override` 填 2——节点自己的说明是「turbo LoRA 配 `steps_override` 可用」；② 作者实测过的配方：挂 DMAD LoRA 0.8 的模型 + `steps_override 2`（DMAD 要挂在没有 Turbo 的底模上，两个蒸馏 LoRA 不叠，铁律 8）；③ 不挂任何蒸馏 LoRA 的底模 + `steps_override 0`（原生调度的最后 4 步，最慢）。本流程的一采是 lightx2v Turbo 8 步，先试 ①——附带的精修工作流就是 ①（`steps_override 2`）。关了 Turbo（`--set 146.value=false`）出的 20 步片段要精修时，同时 `--set 300.steps_override=0`，就是 ③；两样配错了预览的 advice 会提醒。三种在 4090 上都没有实跑过，定下来之前各出一条对比。
- **作者的主张和本流程的差别**：作者建议一采用原生 20 步（他的测试里 Turbo 一采细节少，而且 Turbo 和原生出的是两条不同的片段）。本流程默认一采就是 Turbo 8 步的草稿，精修保住的是这条草稿；想要原生一采的细节，就得 20 步重出——那是一条新片段，要重新选片和观测（铁律 16）。
- 有 FaceRefine 结果接 `face_atlas`（σ 0.45 会把只占一两个 token 的小脸重画坏）。作者的耗时是 5090 上 5 s 片段多花约 1 分钟；24 GB 上 10 s 以上的段没有数字。
- 来源：ResCascade = GitHub `tazmannner/ComfyUI-H3-ResCascade`；它要求先装 LBH 放大器（GitHub `LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler`，`git clone` 进 `custom_nodes` 即可，不用另装依赖），权重在 HF `LBH-123-AI/Minimax_h3_latent_Upscaler`：`H3 Hires Fix` 用的是 **3D 版**，下 `minimax_h3_latent_upscaler_3d_conv_v1/minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors`（约 0.7 GB），放 `ComfyUI/models/latent_upscale_models/`；同仓库 2026-11-10 新出的 2D 版权重（`…_2d_conv_v1_…`）只能配 LBH 自己的 2D 节点，和 `H3 Hires Fix` 不通用（HF 文件清单与两个仓库的 README，2026-11-21 核对）；DMAD LoRA 在 HF `Kijai/MiniMax-H3-experimental` 的 `loras/`。
- 1344×768 是 7:4（1.750），1920×1088 是 1.765，差 0.8%：二采是在新尺寸上重新采样，不是把画面拉过去，这点差别看不出来；交付时上下各裁 4 px 到 1920×1080。

**二采显存不够时按这个顺序试**：① 换下面的分块工作流（不用动别的）；② 改用**不带 Sage** 的那一份（`h3_ref2va_refine*.api.json`），在界面里给它的模型链加 KJNodes 的两个省显存节点——`MiniMax H3 Chunk FeedForward`（把前馈层按 token 分块）和 `MiniMax H3 Low VRAM Attention`（把注意力按头分组），两个节点的说明都写着输出与不加时完全一致、只多一点开销；把 `.api.json` 拖进 ComfyUI，接在 LoRA 开关之后，再导出一份。Low VRAM Attention 和 Sage 仍然按二选一处理（铁律 8）：这台机器上早先那版 KJNodes 两者同开第一步要 693 s；现在的源码写明它遇到 mem-eff Sage 的补丁会配合，但没有实测——想同开，先拿 5 s 的段单独计一次时，结果记进 `logs/machine-notes.md` 再决定；③ 都不行就先用草稿装配。KJNodes 的 `MiniMax H3 Token Counter` 还会提醒一个上限：sageattention 的核在 H3 上超过约 30 万 token 可能溢出——1920×1088 的 15 s 段是 21.8 万，没事；2560×1440 的 15 s 段是 38.5 万，超了。

**分块二采**——`assets/workflows/h3_ref2va_refine_split.api.json`（带 Sage 的是 `h3_ref2va_sage_refine_split.api.json`），用法和上面的精修工作流完全一样（`--from-latent` 或 `--seed`）。它把一个节点拆成三步：ResCascade 的 `H3 Latent Upscale (LBH 3D net)` 放大 latent → `ManualSigmas`（`0.45, 0.225, 0`，即 `H3 Hires Fix` 配 Turbo 时的那两步）→ LBH 节点包的 `MMH3 Split Upscale` 按 `MMH3 Temporal Split Params`（每块 73 帧、重叠 22 帧）分块重采样。每块的 token 数只有整段的三分之一左右，所以能跑下 `H3 Hires Fix` 跑不下的长度；代价是块与块之间靠锚帧衔接，可能有接缝，出来先看接缝处。它的音频同样不重采（节点源码里音频的降噪掩码是全零）；LBH 作者自己的 Ref2VA 示例工作流在二采时也是直接复用一采的条件，不重建。两个文件通过了真实服务器的校验，并用微型随机权重模型实际执行过（124 帧分成两块、各 2 步，出 640×352；真模型下的接缝和画质没有看过）。首帧段也有分块版（`h3_fl2va*_refine_split.api.json`）：这个节点不丢一采的首帧 / 尾帧，而是把它们的 latent 双线性放大到新尺寸继续当锚（节点源码 `reanchor_conditioning`）；LBH 作者自己的首帧示例是在目标尺寸另建一个条件节点重新编码首帧，更准——分块版出来首帧处发软时再手工改成那样。空间上再切瓦片（`MMH3 Spatial Split Params`）没有接进去——整帧一块接缝最少，时间分块还不够时再加。

**手搓等价**（不装 ResCascade 时；`LTXVSeparateAVLatent` / `LTXVConcatAVLatent` 是 ComfyUI 自带节点，0.37.2 的 `comfy_extras/nodes_lt.py`；`i2va` / `fl2va` 手搓这条路时，想让首帧按新尺寸重新编码就得在 1920×1088 另建一个 H3 条件节点，工作流里就有两个，`--media` 一次只接一个（用 `--h3-node` 指定），另一个得手工保持一致，不建议第一次就这么做——两种模式现在都有附带的精修和分块工作流可用）：LBH 的 3D 放大节点（界面里叫 `Minimax H3 Latent Upscaler (3D)`，权重 `minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors`，放 `models/latent_upscale_models/`；也可以用它的 2D 节点配 `minimax_h3_latent_upscaler_2d_conv_v1_fp16.safetensors`，更小、可调锐度，两种权重不通用；或原生 `MiniMaxH3LatentUpscaleWithModel`）只放大 video latent → `LTXVConcatAVLatent` 拼回原音频 → 二采的条件：Ref2VA 直接复用一采的条件、另接一个 `BasicGuider`（LBH 作者的 r2v 示例工作流就是这样，2026-11-23 用真实前端导出核对）；`i2va` / `fl2va` 带首尾帧关键帧，要在目标尺寸另建一个 `MiniMaxH3ImageToVideo`（作者的 i2v 示例里有两个，一采、二采各一个）→ `ManualSigmas 1.0, 0.7, 0.4, 0`（1 步 turbo 头 + 2 步 euler 尾；3 步尾 +17% 闪烁）→ euler + DisableNoise。这组数是该工作流作者配合自己的加噪方式用的，起点不是下一条说的 0.45；要严格保住中选片段就用上面的 ResCascade（`sigma_start 0.45`），手搓时用同 seed 对比确认没有换片。
- σ 起点含义：0.31 软、**0.45 保 take**、0.56 重画五官、0.9 换片。**按目的选三档**：保道具 / 文字 `0.6316, 0.3158, 0`；保纹理一致 σ 0.45 起；`0.9035` 起只用于「换尺寸再抽」（会把纸箱标签改色变透明）。
- 二采永远钉死一采音频（Tr1dae `audio_denoise=0`、bbaudio / T8 `preserve_first_pass`、LongMedia Refine 音频 exact passthrough：audio noise 0 + mask 0，16 GB 卡 refine 窗 73 帧）。
- 二采用 euler / res_multistep 非祖先采样器；LMS 类多步法会把逐帧纹理外推成颗粒。
- 二采 / 放大前 latent 宽高必须为偶数（像素被 32 整除），否则核心 circular padding 在右 / 下边缘出色条（`H3 Latent Upscale By -jingchen573` 或自算）。
- 手工重噪二采不用 stock `AddNoise`（CONST 流模型会被 `SamplerCustomAdvanced` 二次缩放成花屏），用 rockerBOO `MiniMaxH3AddNoise`，音频分支 sigma 按 shift 3 单独换算。
- 「8plus2」两段式：草稿 8 步 → 1.8× latent → `BasicScheduler(8)` → `SplitSigmas(6)` 取**输出槽 1** 跑 2 步 + refiner LoRA；≤ 7 s 片**不要瓦片二采**（更慢更糊构图变宽）；删 refiner LoRA 加步数救不回锐度。
- DMAD rank-39 两采 A/B：S1 864×480 8 步 er_sde/beta → LBH 放大 → S2 2 步 er_sde/`linear_quadratic` denoise 0.4。
- muse Refine V2：beta / 8 步 / 首段 2 步 / 1.0 MP。
- VDN 二采：VDN 8 → 2× → VDN 4 或原生 H3 + EMA-B LoRA，VDN 分支不再叠 Turbo。

**漫剧**：RelayHires：AnimeSR 放大 → taeh3 编码 → 1 步 DMAD 0.8 从 σ 0.60，`window 4 / anchor_stride 8`；真人改 `RealESRGAN_x2plus`。

**本流程的对白段是 8–13 s，按这个顺序试**：先整段直接二采（上面的首选）；LBH 的说明写得很直接——latent 放大只省时间，二采仍然在目标分辨率上跑，显存峰值接近直接生成 1920×1088。1920×1088 × 243–328 帧在 24 GB 上够不够没人测过，爆显存或者慢到不可接受，就改下面的分块方案——分块只换放大方式，中选的片段和音频不变。

**10–15 s 或 OOM**：bbaudio `MMH3 Ultimate Upscale`（tile 576–768（32 倍数）、overlap 128、chunk 136–170 帧（17 倍数）/ overlap 17、anchor 0.999，二采 1–2 步 denoise 0.2–0.3，音频不重采）或 LBH `MMH3 Split Upscale`（`seam_denoise 0.5–0.8`）。多段续接的精修用 CGlide `Upscale Hold` 钉上一段精修尾。
- LBH 3D 对 > 32 latent 帧（> ~110 帧）走时间分块，检查首帧网格状字形伪影；短片关 `enable_temporal_chunking`。

## 5. Stage 4 · 可选最后一跳

- 想要 2K 重绘质感且接受细节变化：Open-H3-Regenerate 3 步（σ `0.909375, 0.857, 0.667, 0`；首尾帧钉住的草稿改 `start_sigma 0.8` 保脸），需 FL2VA + 12.4 GB 合并 LoRA + 6.5 GB 快速 VAE；4090 预计慢数倍，先只做 1080P。Regenerate 类默认：denoise 0.30（0.15–0.35 = 起始 σ）、3 步、shift 6、×2。Open-H3-Regenerate-2K 重画时保护人脸：YuNet 脸区图 + `face_strength 0.55`（脸从 σ 0.50 起），只挂 refiner LoRA、不叠 Turbo / Sharp，音频用草稿原音（ArcFace 0.52→0.91）。
- 只要更大尺寸：像素 SR（RelayVSR X4 / RealESRGAN_x2plus / SeedVR2）。超分逐镜做，不对成片做；像素超分优先级：RelayVSR ×2（25 s）> RealESRGAN ×2（68 s）> SeedVR2（要纹理时）；**真人近景优先 RTX VSR，不用 SeedVR2 / SoL-Refiner（改脸改嘴）**。FlashVSR 2× 用 `--tile_size 256 --tile_overlap 64 --frame_chunk_size 50 --keep_models_on_cpu`（128/24 出网格），完成后 `ffprobe nb_frames` 核帧数并用 `-map 0:v -map 1:a:0` 回灌原音轨。

## 6. 可控性

- **FunControl**（核心已内置 `MiniMaxH3FunControlNetApply`）：多个 ControlNet 的强度是共享预算，depth 0.3 + pose 0.7，总和 ≤ 1.0；锁人用 pose 不用 depth；`end_percent 0.6`；strength 的说法有出入——社区有人测到 > 1 无效，ComfyUI 官方教程写的是「输出偏离控制时才调到 1 以上」，平时保持 1；`mask` 标 1 的区域在 `source_video` 的约束下重画、其余不动（官方教程，可做局部修补）；小人物先放大取景；稀疏注意力的 `morton` 必须 false 并接在 ControlNet 之前。
- **复刻参考片走位**：`reshot ref.mp4 --target h3 --control pose`（武打 / 舞蹈）或 depth，提示词写明 `<Video 1>` 里发生了什么并声明 `its grey depth look is not transferred`。
- **Ref-Patch**（让 FL2VA 权重获得参考能力，112 键差分）：已有 int8 Ref2VA 时跳过。
- **RefMod**：Full Reference ≈ 330 token/图@512，`budget_policy=error` 看真实计数；特写肖像放第一张定画布；头替换用 `head_swap_v1.0_r32` 不是 character swap。
- Ref2VA 换人保脸：脸部特写单独作 `<Picture 2>` 并在提示词点名（ArcFace +0.12），同图重复第三次无效。
- 道具 / 属性 / 材质类参考可用 Qwen-only 语义参考（`#tag`，不占 9/3/3 名额，256–512 px）；身份与具体帧锚才用原生 VAE 参考。
- **局部重绘**：LanPaint（见 `lora-and-style.md`）。

## 6e. 源码级补充（`12-fresh-followup.md`）

- 小脸 / 面部重绘起始 σ 固定 **0.80–0.89**（BasicScheduler simple 8 步 shift 12 的 denoise 0.30–0.40 即此区间）；低于 0.6 保留错脸型（三方独立一致）。
- 像素超分**默认不做**，Lanczos 到交付尺寸；真要做选 RTX VSR（6 s 片 14 s）而非 FlashVSR（220–335 s）；2.5 Mbps 平台压缩后差别可忽略。
- 空间局部重绘：latent 遮罩只能是 32 px 方块（2×2 patch 最大池化），羽化只在像素域做（expand 6 → feather 6 贴回；面部 feather 24）；LanPaint 去除物体用硬 0/1 像素遮罩 + `NumSteps 2 / Lambda 5 / StepSize 0.2 / Image First / blend_overlap 11`；遮罩要覆盖到段末。
- 挂 Fun-ControlNet 时不开任何跳块 / 缓存加速：Union 注入块 0/10/20/30/40 与 FinalLayer 必须原生；两个块级缓存同挂不报错但静默出错图。

## 7. 禁忌

- LoRA 文件必须是带 alpha 的 `*_comfyui_alpha8` 或官方 `*_comfyui_bf16`；缺 PEFT alpha 的会把更新放大 ~16 倍整幅融化。
- 剪枝底模加载全量 LoRA（目前只有 FL2V 8 步 v1.2 是这种）时控制台的 51 行 `ERROR lora … adaln_proj`：任务不会中断，那 51 个模块被跳过、其余 208 个照常生效。社区里有「这部分贡献只有 0.02%，可以忽略」的说法，本项目没有验证；默认做法仍是不这么配——换成 v1.0 的 768p 版（`comfyui-nodes.md` §2、`pitfalls.md` 第一张表）。
- 不要同时装 CGlide 的 `cglide` 与 `ComfyUI-CGlide` 两份；不装 xmarre LBH `-Plus` 分支。
- 原生 VAE 解码固定 256 px tile 且每时间块写回 CPU；长片可用 Tr1dae `VAE Decode (fast)` 或 int8_convrot 视频 VAE（快 1.5×）。
- Pika H3 Flex 6 步是另一条 take 路线（LoRA 在 SigmaShift 前，ManualSigmas `1.0, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0`，lcm，CFG 1），不与 Turbo 叠。
