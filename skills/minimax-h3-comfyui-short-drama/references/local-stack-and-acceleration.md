# 本地栈与加速：24 GB 单卡的草稿档 / 精修档

> 数据来源：用户 RTX 4090 实测（`docs/11-acceleration.md` §11）、neng320 4060Ti 基准、wildminder 社区性能报告、MiniMax 官方生态索引 Speed 一节、以及 29 个加速仓库的源码级精读（`docs/13-github-survey/03-acceleration.md`），并已并入长尾实测补充（`docs/13-github-survey/08-long-tail-comfyui.md`）、补读新增与新仓库实证（`11-fresh-repos.md`）。所有「作者自报」数字都注明硬件与口径。

## 0. 先盘点（agent 第一步）

按 `assets/local-inventory-checklist.md` 产出：GPU / 驱动 / CUDA / PyTorch 版本、ComfyUI 版本与启动参数（带了哪个注意力开关：`--use-ck-attention` / `--use-sage-attention` / `--use-flash-attention`，三者互斥）、`models/` 下的 H3 文件名与大小、custom_nodes 列表（重点：KJNodes、sageattention 包版本、comfy-kitchen、任何 cache / TE-Speed / Spark / Sol / Veda / Spectrum 节点）、现有工作流的注意力 / LoRA / 步数 / shift / 分辨率、ffmpeg 是否在 PATH、Windows 的 CUDA「系统内存回退」是否关闭、系统内存大小。

## 0b. 装机补充（Windows 便携版；仓库与文件名 2026-11-21 逐个核对过）

- **要下的模型、放哪个目录、多大**：`assets/workflows/README.md` 的表（只做 Ref2VA 视频约 42 GB；加两套出图模型约 89 GB；加精修约 90 GB；再加 FL2VA 约 113 GB）。LoRA 放 `ComfyUI/models/loras/`，底模放 `diffusion_models/`，文本编码器放 `text_encoders/`，VAE 放 `vae/`，LBH 放大权重放 `latent_upscale_models/`。
- **工作流**：不用自己搭，用 `assets/workflows/` 里附带的；装完东西后先照 `assets/first-run-checklist.md` 的第 2–4 项做连通测试和预检。

- **跑本 skill 脚本用哪个 Python**：另装一个 Python 3.10+（或建一个 venv），不要往 ComfyUI 便携版的 `python_embeded` 里装东西——脚本只通过 HTTP 找 ComfyUI，不需要和它共用环境。可选依赖按用到的装进这个 Python：`pip install numpy faster-whisper pypinyin opencv-python onnxruntime pyJianYingDraft opentimelineio`。`faster-whisper` 第一次运行会从 HuggingFace 下载模型（`Systran/faster-whisper-small`，约 500 MB）。
- **ffmpeg / ffprobe**：`winget install Gyan.FFmpeg`，或从 GitHub `BtbN/FFmpeg-Builds` 的 Releases 下载 win64 包、把 `bin` 目录加进 PATH。装完跑 `scripts/selfcheck.py`。
- **KJNodes**（两个 Sage 节点都在里面）：GitHub `kijai/ComfyUI-KJNodes`。三种装法任选：ComfyUI-Manager；`git clone` 到 `ComfyUI/custom_nodes/`；或者没有 git 也没有 Manager 时，在仓库页点 Code → Download ZIP，解压成 `ComfyUI/custom_nodes/ComfyUI-KJNodes/`（这个文件夹里直接就是 `__init__.py`，别多套一层）。后两种装完用便携版自带的解释器装依赖：`python_embeded\python.exe -m pip install -r ComfyUI\custom_nodes\ComfyUI-KJNodes\requirements.txt`，然后重启 ComfyUI。
- **精修要的两个节点包**：GitHub `tazmannner/ComfyUI-H3-ResCascade`（节点 `H3 Hires Fix`）和 `LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler`，装法同上；两个都没有额外的 Python 依赖。2026-11-23 把这三个包当天的版本装进一台真实的 ComfyUI 0.37.2，都能正常加载。
- **SageAttention 在 Windows 上有两条路**（二选一，别叠）：
  - 走 KJ 节点：需要 ComfyUI 的 Python 环境里有 `sageattention` 包。Windows 预编译包在 GitHub `woct0rdho/SageAttention` 的 Releases：两样都装进 **ComfyUI 自己的** Python（便携版就是 `python_embeded`，这是唯一要往里装东西的地方）：① `python_embeded\python.exe -m pip install triton-windows`；② 看 PyTorch 版本：`python_embeded\python.exe -c "import torch; print(torch.__version__)"`，输出形如 `2.10.0+cu128`——前半是 torch 版本、后半是 CUDA 版本；③ 在 Releases 页按这两样挑 wheel（torch ≥ 2.10 用文件名带 `torch2.10.0andhigher` 的；`cp310-abi3` 的包对 Python ≥ 3.10 通用；CUDA 12 与 13 的包不通用，选和 `cu12x` / `cu13x` 对应的）；④ `python_embeded\python.exe -m pip install <下载的 .whl 的路径>`。不需要装 Visual Studio 或 CUDA toolkit。装完后 `MiniMaxH3MemoryEfficientSageAttentionPatch` 如果报 `sageattention is not new enough version or could not determine CUDA architecture`，是包太旧或装的不是对应 CUDA 版本的那个；报 `This ComfyUI version does not support MiniMax H3`，是 ComfyUI 自带的 comfy-kitchen 太旧（两句都出自 KJNodes main 分支源码，2026-11-21）。
  - 走启动参数：该仓库 README 写明，用 ComfyUI 的话可以不装它的 wheel，改用 comfy-kitchen 自带的 SageAttention——启动时加 `--use-ck-attention`（不是 `--use-sage-attention`）。0.37.2 有这个参数（`comfy/cli_args.py`：`--use-ck-attention`、`--use-sage-attention`、`--use-flash-attention` 三个互斥的注意力开关都在；文中提到的 `--cache-none`、`--disable-pinned-memory` 也在，2026-11-23 核对源码）。
  - 两条路谁快没有定论：各跑一次同一段、seed+1，以日志和计时为准，然后固定用一种。
- **官方模板的名字**（ComfyUI「模板」面板里搜。0.37.2 自带的模板包是 0.11.69，下面这些都在里面，用到的节点 0.37.2 全有——2026-11-23 在真实的 0.37.2 上逐个导出验证过；GitHub `Comfy-Org/workflow_templates` 上的版本更新，个别模板和自带的不一样，没必要去下）：视频 `video_minimax_h3_r2v` / `video_minimax_h3_i2v` / `video_minimax_h3_t2v`；出图 `image_qwen_image_2_1_t2i`、`image_qwen_image_edit_2511_int8`、`image_z_image_turbo_int8`。怎么把视频模板改成脚本能用的草稿档工作流，见 `comfyui-nodes.md` §3。

## 1. 三个杠杆与叠加原则

| 杠杆 | 代表 | 有损？ | 规则 |
|------|------|--------|------|
| 少步（蒸馏） | lightx2v Turbo 4/8 步、alibaba-pai PDD 8 步、HyperFlow 8 步、FastH3 整模、Pika Flex 6 步、DMAD、VDN turbo adapter | 4 步明显、8 步轻微 | **只选一个**；VDN / PDD / SVDQuant 量化权重已折叠蒸馏，不再叠 LoRA |
| 便宜的步 | 注意力核：SageAttention（无损）、Sol-Attn 稠密核（近无损）、核心 `BlockSparseAttention`（已合并 Sol/SLA/VSA，稀疏=有损）、Veda / Spark-H3 / Kablex VSA（有损稀疏）；跳步缓存：Spectrum、FirstBlockCache、T8 BlockCache、EasyCache（有损） | 核无损；稀疏与缓存有损 | 同一模型分支只能有一个「跳步/缓存」、只能有一个 attention 补丁；精修档只留 Sage |
| 便宜的模型 | pruned（AdaLN 剪枝）int8、nvfp4、GGUF、VDN 架构替换、ClipProj 小文本编码器 | 剪枝略损细节 | 24 GB 用 int8_convrot（pruned 更省显存，不剪枝画质更稳） |

**基线链**（「先跑一次基线」指的就是它：int8 底模 + Turbo 8 步 + Sage，别的加速全关，用一段固定的 10 s 提示词记下耗时；之后每开一个加速项都和它比）：
`UNETLoader(int8_convrot)` → `LoraLoaderModelOnly(lightx2v *_turbo_8step_v1.1*_comfyui_bf16, 1.0)` → KJ `PathchSageAttentionKJ(auto)`（KJNodes 里这个节点名本身就拼成 Pathch，搜节点时照这个拼） → KJ `MiniMaxH3MemoryEfficientSageAttentionPatch` → `MiniMaxH3SigmaShift` → Guider。先全关跑一次基线，再逐个开，一次只改一个变量。同 seed 同参数重跑会命中 ComfyUI 结果缓存秒出，计时与对比用 seed+1。

- **int8_convrot 底模上挂 LoRA**：官方模板用 ComfyUI 自带的 `LoraLoaderModelOnly`，第一次照它来就行。「合并进权重，还是运行时另挂一条分支（bypass）」是社区节点才有的选项：Larryvrh `ComfyUI-MiniMax-H3-Turbo` 的 `low_vram` 开关（开 = 合并）、cicalooo `ComfyUI-H3-PowerLoraStack` 的 `quantized_layers=auto`（运行时低秩分支；多 LoRA 时视频风格 LoRA 的 audio 模态缩到 0–0.25）。两边的说法相反——一说合并往返会注入约 1.5% 的权重噪声、而 H3 LoRA 的改动量只有 0.01–0.08%，所以运行时分支更锐；另一位在 3090 上测到合并快 25%、近景皮肤更干净。装了这类节点就两种各跑一次、seed+1 对比，以自己机器的结果为准；没装就不用管。装 LoRA 后日志里要能看到 `… 208 patches attached.`（看不到、或者数字不是 208，说明 LoRA 没挂全；这一行只在默认的 DynamicVRAM 加载路径下打印，条件见 `comfyui-nodes.md` §1「LoRA 和底模对不对得上」）。
- 8 步 Turbo 上叠风格 / 运镜 LoRA，**额外 LoRA 强度之和 ≤ 1.3**（0.6+0.3+0.4 实心；0.8+0.5+0.6 小物件透明重影）。

## 2. 推荐组合（RTX 4090 24 GB，Ref2VA 短剧）

### 草稿档（两档：快速预览 ≤ 2–3 min / 条；同构图草稿预计 5–10 min / 条，没有实测）
- 权重：`ref2va_pruned_int8_convrot`（或 fl2va）+ `qwen3vl_32b_minimax_h3_nvfp4_awq` + int8 视频 VAE + fp32 音频 VAE
- LoRA：`minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16` 强度 1.0（抽卡可降 `ref2v_turbo_4step_v1.0_768p`；声音不稳降 0.75）
- 采样：8 步，`euler` + `simple`（Turbo LoRA 作者 lightx2v 的示例工作流和说明用的就是它；Comfy 官方模板的 `res_multistep` + `simple` 也能跑，想换就拿同一段、seed+1 比一次），CFG 1.0（用 `BasicGuider`，本来就没有 CFG 分支）；shift：12 / 3 是模型默认值，Ref2V 的 LoRA 用它，接不接 `MiniMaxH3SigmaShift` 一样；FL2V 的 v1.0 768p 版（本流程 FL2V 的默认）要用这个节点改成 6 / 3，那时**调度器的 `model` 也要接它的输出**（各版本的值见 `comfyui-nodes.md` §1）
- 注意力：KJ Sage 两节点；**不接** `MiniMaxLowVRAMAttention`（与 Sage 同开实测第一步 693 s——这是用户机器上当时那版 KJNodes 的结果；2026-11-23 的 KJNodes 源码里它的说明是「不改变计算、输出与不加时一致」，并且写明遇到 mem-eff Sage 的补丁会与之配合；更新 KJNodes 之后想用它省显存，先单独拿同一段比一次再决定）；工作流里只留这一个注意力补丁，不再接 kitchen / BlockSparse 的注意力节点（启动参数 `--use-ck-attention` 是另一回事，见文末「出图与出视频分实例」；它和 KJ Sage 同开时谁生效以日志为准，配好后用同 seed 各跑一次计时）；省显存改 KJ `MiniMaxChunkFeedForward` 或 star7 分块（`chunk_tokens 8192 / mlp 4096 / qkv 4096`）
- 分辨率与 LoRA，两档各有用途：
  - **快速预览档** 864×480 或 960×544：只用来看构图和调度对不对，选中后要在 1344×768 重跑（那是一条新片段，要重新选片）。Ref2V 没有 8 步的 544p 版 LoRA（仓库里不带 `768p` 的 Ref2V 文件只有 4 步的 `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16`，官方 r2v 模板默认挂的就是它）；下面那条 134 s 的实测用的是 8 步 LoRA 直接跑 864×480。FL2V 有 8 步的 544p 版：`minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16`。
  - **同构图草稿档** 1344×768 + `…_768p_…` 版 LoRA：出来的片段可以直接采纳、之后走 latent 二采——**默认用这一档**，除非只是想快速看个大概。544p 版 LoRA 不要用在 768p 上（又慢又糊）。
- Turbo 的代价（ComfyUI 官方 H3 教程）：8 步「faster, slightly softer motion/audio」，Ref2VA 的 Turbo「weaker reference/audio」，参考必须守住时官方建议 20–25 步——所以草稿里脸或嗓音不稳，不一定是提示词的问题，见 `pitfalls.md`
- 5–10 s；`ref_image_size = match`（参考 token 预算，1344×768 画布上实测：`match` 每张图在 DiT 参考块里约 1,000 token、文本编码器一侧再约 1,000，合计约 2,000，和原图大小无关；`max` 按原图算、短边封顶 2048，一张 2048×2048 是 4,096；124 帧参考视频 14k–27k token——**重者胜**，否定句与「视频里的人就是 Subject 1」都压不过它）；每段 2–3 个 seed
- 耗时：864×480 × 10 s × 8 步 ≈ 134 s（用户的 4090 实测）；1344×768 × 10 s × 8 步没有实测，两种外推：按上面这条实测乘 2.5–3.5 倍像素是 5–8 min；按别人 4090 上 1280×704 × 107 帧 ≈ 4 min 的自报（§4 表）折算约 10 min——所以按 **5–10 min** 做计划，11–12 s 的段再加一成多；每次开机第一条另加 8–14 min 冷启动。20 步定稿、latent 二采、出图在 4090 上都没有实测数字——第一次跑的时候记下来（`comfy_submit.py --log` 会记耗时）
- 同一提示词多 seed 抽卡时把条件编码落盘复用（pepikir `H3SaveConditioning/LoadConditioning` 或 CLIPCached），采样图里不放 CLIPLoader；多段接力先编码所有段的条件再连续采样（E/E/E/S/S/S），避免 TE / VAE / DiT 往返加载，−25~45%；32 GB 内存机器单图 `--cache-none`；TE 与 DiT 放 NVMe（编码 90→25 s）
- 可选（ComfyUI ≥ 0.38 后）：Veda `VedaSparseAttention` 放在 LoRA 与 Sage 补丁之后、Guider 之前，预测器只保证 1344×768 / 768×1344 / 768×768 / 1024×768 × 5/10/14 s × 8 步 Turbo；首次 Ctrl+B 旁路同 seed 对比再默认开；5090 实测（mathruffian）Veda 开着会在第 51/119/187 帧闪帧
- 激进替代（仅 Ref2VA、放弃 Sage）：Kablex `Ref2VAVSAGatePatch(sparsity 0.5–0.75)` + ref2v 4 步 v0.1 + shift 12/3，1344×768 × 5 s ≈ 72 s（作者自报），模型分支上不得有任何 Sage/Sol 节点

### 精修档（中选段，1344×768）
- **路线 A（默认的草稿档，中选后走 latent 二采；有运镜的镜头另按铁律 16 用 20 步关 Turbo 重出）**：Turbo 8 步 v1.1 + Sage，其余加速全关；`low_vram`（合并）与 bypass 各跑一次同 seed 定默认（3090 实测合并反而快 25% 且皮肤更干净，勿照抄「bypass 最锐」）
- Turbo 无 CFG 链路的微调旋钮：Fizgig H3 Tweaks（LoRA 之后、采样器之前）`Detail & Contrast 0.15`、`Prompt Strength 0.2`、`Scene Variation ±0.1–0.3`；不与块跳过类节点同挂
- **路线 B（画质优先 / 有运镜的镜头）**：无 Turbo 20 步 `res_multistep` + `simple` + Sage，**不叠任何缓存或稀疏注意力**（精修档铁律）。Spectrum（默认参数，SigmaShift 之后 Guider 之前，`history_storage=system_ram`）或 FirstBlockCache `H3 Fast`（5090 实测 −30%；hit 数为 0 就移除）只允许在「20 步草稿探索」时二选一试用；8 步链两者都不挂；若用核心 EasyCache：`end_percent` 封顶 0.70（默认 0.95 后期跳步造成织纹与色块），且定稿不开（5090 实测，mathruffian）
- **草稿档 ≥ 10 s 长段可选（ComfyUI 0.38.x 后）**：Spark-H3（Windows SM89 CUDA-13 包，`fidelity`、`topk_ratio 0.2`，Ref2VA 带参考视频时 `sparse_scope joint-video`、`dense_backend sage`）或 Veda，二选一，不与核心 `Block Sparse Attention` 同链；稀疏注意力有损，**只用于抽卡，不进精修档**；Sol / 块稀疏只在 ≥ 768p 才有收益（1.23–1.27×），480p 档 1.03× 且高频 −13.8%；5 s 短片不值得折腾（3090 实测 Spark 与核心 Sol 同速 158 vs 152 s）
- **二采精修（保 take）**：一采 latent → LBH 放大 → 1920×1088 从 **σ 0.45** 重采、音频钉死，见 `quality-pipeline.md` §4（权威）。Spark-H3 / FreeVideo 示例的「0.2–0.33 MP 4–8 步 → 放大 → 3 步 sigmas `0.9035, 0.6316, 0.3158, 0`」是**重生成式**二采（高 σ 会改脸），只在接受重绘时用
- **写实 A/B**：alibaba-pai PDD Ref2VA 8 步替换 Turbo（`MiniMaxH3PDDAccApply nfe=8`，SIGMAS 接 `SamplerCustomAdvanced`，Euler、CFG 1、shift 恰好 12/3，不接任何缓存，不用 er_sde / res_multistep）；漫剧 / 插画风格保持 Turbo（PDD 4 NFE 会压平纹理）
- **DMAD 4 步可做日常定稿**（5090 实测，mathruffian；指没有运镜的镜头，有运镜的仍按 SKILL.md 铁律 16 用 20 步）：8 类镜头看不出差、快 49–58%；单镜 ≤ 12 s
- 预计：1344×768 × 10 s × 8 步 ≈ 5–10 min（4090，含 VAE；外推，见上）

### FL2VA（I2VA 首帧 / 尾帧衔接）
`fl2va_pruned_int8_convrot` + `minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16`，8 步 euler，shift 6 / 3（作者公布的值）：要加 `MiniMaxH3SigmaShift`，并且 `BasicGuider` 和 `BasicScheduler` 都接它的输出——附带的 `assets/workflows/h3_fl2va*.api.json` 就是这样接的。更新的 8 步 v1.2（作者在模型卡里拿 v1.1 出问题的例子重测，更贴提示词、更清晰，按 12 / 3 跑）**在 24 GB 上用不了完整的**：它比别的版本多改 51 个时间调制层，这些层只在不带 `pruned` 的底模（34 GB）上对得上，挂在 `pruned` 底模上会被跳过（文件头部逐层核对的结果，见 `comfyui-nodes.md` §1「LoRA 和底模对不对得上」）。v1.1 的 shift 作者没有公布；其余同上。

- **可选：FastH3（下面这个 V2 只支持 `t2va` / `i2va` / `fl2va`；参考生视频的 FastH3 Omni 是另一个整模，要 ComfyUI ≥ 0.42，0.37.2 上加载不了——原因见 `comfyui-nodes.md` §1）**——FastVideo 团队的蒸馏整模，固定 8 步，改步数会掉质量。ComfyUI ≥ 0.36 自带模板 `video_fastvideo_fasth3_t2v` / `video_fastvideo_fasth3_i2v`；权重是 HF `FastVideo/FastVideo-FastH3-Comfy` 的 `diffusion_models/fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors`，文本编码器和两个 VAE 与 H3 共用。模板里的设置：`MiniMaxH3SigmaShift` 10 / 3、`res_multistep` + `simple` 8 步、`BlockSparseAttention`（VSA，`keep_percent` 10，从调度的 20% 处开始）。官方的定位是牺牲一些动作和音频保真换速度，用于草稿和迭代；它本身就是蒸馏模型，不再挂 Turbo LoRA（铁律 8）。4090 上没有实测，想用就拿同一张首帧、同一段提示词和 Turbo 那一档各出一条，比时间、口型和音质再决定（ComfyUI 官方 FastH3 教程，2026-11-21 读）。

### 更快的视频解码（三个轻量解码器，都要比 0.37.2 新的 ComfyUI）

官方视频 VAE 的解码器是 36 层的 ViT，按瓦片和时间块解码，是每条 take 里一段固定的开销（Sol 的模型卡：RTX 5090 上 768p × 5 s，官方解码器 12.5 s）。下面三个替代品的 latent 空间和官方 VAE 完全相同（同样的通道、归一化、时空压缩），所以**同一个 latent 可以先用轻量解码器看草稿，定稿再用官方 VAE 解码**。

| 解码器 | 文件（HuggingFace） | 大小 | ComfyUI 最低版本 | 它是什么、自述的效果 |
|--------|--------------------|------|------------------|----------------------|
| Sol-H3-VAE | `Comfy-Org/MiniMax-H3` 的 `vae/minimax_h3_sol_vae_int8_convrot.safetensors`（原版 `Efficient-Large-Model/Sol-H3-VAE`） | 1.99 GB | **0.44.0** | 24 层，蒸馏成整段一次解码（不分瓦片、不做时间重叠重算）。模型卡：5090 上 768p × 5 s 从 12.5 s 降到 5.0 s；和官方解码器比 PSNR 45.4 dB（留出的 latent）/ 38.2 dB（一条生成的 768p 片段）；占用随片段长度增长 |
| LynnReal light VAE | `Kijai/MiniMax-H3-experimental` 的 `minimax_h3_lynnreal_light_vae_int8_convrot.safetensors`（原版 `stdstu123/LynnReal-Onmi-light-vae`） | 2.14 GB | **0.39.0** | 26 层的蒸馏解码器，编码器不变。Kijai 的说明：解码约快 1.3 倍 |
| LightVAE Lite | 同仓库 `minimax_h3_lightvae_lite_vae_int8_convrot.safetensors` | 1.04 GB | **0.41.0** | 12 层解码器，编码器也剪过 |

- **0.37.2 上三个都不能用。** 版本是逐个 tag 对着 `comfy/sd.py` 查的：0.37.2–0.38.2 把解码器写死成 36 层，0.39.0 起才按文件里的层数建；剪过的编码器 0.41.0 起；Sol 的键名 0.44.0 起才认。在 0.37.2 的加载代码上实际试过（只用文件头部的形状）：LynnReal 的 26 层文件**不报错地加载成 36 层**，控制台刷 `Missing weight for layer decoder.transformer_blocks.26…35` 和一行 `Missing VAE keys`，缺的 10 层是未初始化的值，解出来的画面是坏的；Sol 和 LightVAE Lite 的文件是 `WARNING: No VAE weights detected, VAE not initalized.`。要用就先升级 ComfyUI（§6 的检查照做）；不升级就继续用 `minimax_h3_video_vae_int8_convrot`——它已经是量化过的版本（Kijai：比 fp16 解码快约 2 倍）。
- 用法（升级之后）：`VAELoader` 换个文件名就行，附带的工作流里是节点 119（`--set 119.vae_name=minimax_h3_sol_vae_int8_convrot.safetensors`；FL2VA 那几份是 `105:11`）。蒸馏的解码器和官方的不逐像素相同，建议只在草稿档用：草稿带 `--keep-latent`，选中的那条精修时仍由官方 VAE 解码。
- 三个都没有在这套流程里实跑过，速度是各自作者的数字、口径不同（Sol 的是它自己的引擎，不是 ComfyUI 里的耗时）。升级后第一次用，先拿同一条存下的 latent 用两种解码器各出一遍对比画面和耗时。

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
- 不安装：lihaoyun6 Cache（替换核心 `_forward`）、TE-Speed OSS（patch 核心 `model.py`，已装先 `python patch_model.py --revert`）、tl2012tl TE-Speed（闭源 .pyd）、xmarre Sol-H3（Windows 空转）、W4A4-VSA（24 GB 无需）、pottokao GGUF-TE（对 H3 无效）、HyperStep / TeaCache（无画质护栏）、AutoContext 整包（patch PackedLayout）。

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
| 3090 Ti | FastVideo VSA topk 0.1 + 4 步 | 0.8 MP × 5 s × 4 | 采样 49 s（比 20 步快 10×）；Sage/CK 在 topk 0.1 下无增益，峰值 ~22 GB |
| GB10 int8（chiphoton） | Larry v4 6 步 vs 20 步 res_multistep | — | 端到端 2.2×，I2V 首帧 SSIM 0.8215 vs 0.8245（几乎无差） |
| L4 24 GB（kuhung 的 Colab 记录，2026-11-12） | int8_convrot（cu130）+ Turbo 8 步，`BasicGuider` | 960×544 × 5 s × 8 | 稳态 165 s（第一条含加载 244 s）；同一张卡上 I2V 首条 258 s、首尾帧 273 s |
| L4 24 GB（同上，旧版流程：CFG 3、20 步） | — | 960×544 × 5 s → 1344×768 × 5 s | 316 s → 875 s（**像素 ×1.98，时间 ×2.77**）；960×544 时去噪阶段显存 21.8 GB、峰值 21.9 GB（可用 22.0 GB） |
| 8×B300（NVIDIA Sol-H3） | 4 步蒸馏 + Ulysses | 1344×768 × 10 s | 3.7 s（数据中心，不可比） |

估算：同配置下耗时随 token 数近似线性偏超线性。视频 token 数 = (宽/32) × (高/32) × (5k + 2)，其中帧数 = 17k + 5（实测的 latent 形状，见 `comfyui-nodes.md` §1）：864×480 × 10 s 是 29,160，1344×768 × 10 s 是 72,576（2.49 倍）→ 2.5–3.5 倍时间（上表 L4 那一行是另一台 24 GB 卡上实测的同类放大：像素 ×1.98 对应时间 ×2.77，按同样的指数 2.49 倍像素约是 3.9 倍时间，即 134 s → 8–9 min，落在「5–10 min」这个外推区间的上半段）；二采的 1920×1088 × 10 s 是 146,880，又是一采的 2 倍——这就是 10 s 以上的段整段二采在 24 GB 上吃紧的原因。稀疏注意力的收益随时长增长，5 s 以内几乎无差。

## 5. 「为什么比别人慢」排查顺序

1. 分辨率与时长同口径？（多数「2 分钟 10 秒」是 480p–544p）
2. 还在跑 20 步 + CFG 分支？→ Turbo 8 步，CFG 1
3. LoRA 版本与分辨率匹配？（544p 版跑 768p 既慢又糊）
4. Windows：NVIDIA 控制面板关闭「CUDA 系统内存回退」（关闭后放不下会直接 OOM 报错而不是变慢，先确认模型 + 激活能放进 24 GB）；看「共享 GPU 内存」是否被占用
5. int8 DiT 权重是否 **100% 驻留 GPU**：差几百 MB 未全载，步时从 ~19 s/it 跌到 ~283 s/it；OOM 时降分辨率或减参考图，不要加 reserve；显存溢出到系统内存不报错只变慢：看 `nvidia-smi` **功耗**（util 100% 但功耗只有峰值 1/4 = 在搬数据），不信 `/system_stats`
6. Sage 已生效？（控制台 patch 日志）是否与 LowVRAM 同开？是否启动参数和节点重复 patch？
7. 冷启动：第一条含 JIT 编译（Triton / Sage）与 34 GB 载入，8–14 min 属正常；任何稀疏 / Sol 节点换分辨率或时长都会重新 JIT
8. 系统内存 ≥ 64 GB？32 GB 时加 `--disable-pinned-memory`，TE 可放 CPU（约 +27 s/次）
9. PyTorch 是不是 **CUDA 13（cu130）** 的构建？int8 / nvfp4 的快速核在 comfy-kitchen 的 `cuda` 后端里，这个后端加载的是 CUDA 13 的 cuBLASLt（comfy-kitchen 0.2.35 源码）；官方模型仓库的说明也是「能用 cu130 的 PyTorch 就优先 `int8_convrot`，不能用才退到 `fp8_scaled`」。看 ComfyUI 启动日志里的这一行：`Found comfy_kitchen backend cuda: {'available': True, …}`——是 `False` 的话后面写着原因，int8 权重就走慢路径。官方便携版的默认包（`ComfyUI_windows_portable_nvidia.7z`）自带的就是 cu130；带 `_cu126` 的那个包是给 10 系及更老的显卡的，4090 不要用它。另外：显卡功耗墙拉满
10. 单段超过 328 帧？**4090 单段帧数上限 328 帧**（19×17+5）：345 帧有 6/7 概率个别 step 停滞 2.5–4.8×、整段慢 3–17×；1280 宽改 **1216** 让 VAE 解码 tile 28→24、总时长 −15%；VAE tile 保持 256（512+ 不更快且 PSNR 40→21 dB 出格子）
11. 采样期间在轮询 ComfyUI HTTP？每次停 18–43 s，`comfy_submit.py --poll` 设 ≥ 20 s（脚本记的耗时取自 ComfyUI 历史记录里的起止时间戳，不含排队和轮询的等待；`run.json` 里 `seconds` 是执行时间、`wall_seconds` 是从提交到取回）；驱动 ComfyUI 时每 N 个任务 `POST /free {"unload_models":true,"free_memory":true}`（`comfy_submit.py --free-every N`）；`/history` 与 `/queue` 连续 3 次都查不到才判丢失（脚本已内置：受理后先把 `prompt_id` 写进 `<take>/handle.json`，中断后原样重跑会先查这两个接口再决定是否重提）；H3 不与其它 GPU 任务并行；计时读 `/history` 执行时间
12. 同配置耗时涨到 1.8× 立即重启 ComfyUI（CUDA 崩溃前兆）；杀毒软件只对 ComfyUI 与模型目录加排除项，不要整体关闭

## 6. 升级 ComfyUI 前检查

Spark-H3 跳过 0.41（要 0.38.x–0.40.x 或 0.42.x–0.44.x）；Spectrum 需 ≥ `e377e263`；Veda ≥ 0.38；HyperFlow 在 0.37 有「Model Initializing」卡住报告（诊断 `--disable-fast-disk`）；FeiHou 流式块模式不与 kitchen 同用；核心 INT8 已进主线（旧 I8Fast 文件要转换）。

**出图与出视频分实例**：comfy-kitchen ≥ 0.2.36 的 `--use-ck-attention` 会让 Qwen-Image 2.1 在 mask 存活 token > 64 时崩图（社区报告）。如果你的 H3 实例是带这个参数启动的，出图另开一个不带它的 ComfyUI；H3 这边带不带，按 §0b 的办法实测后固定。

## 7. 下载清单（HuggingFace，澳洲可直连）

- Comfy-Org/MiniMax-H3：`diffusion_models/minimax_h3_{ref2va,fl2va}_pruned_int8_convrot.safetensors`、`text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`、`vae/minimax_h3_video_vae_int8_convrot.safetensors`（或 `…_fp16`）+ `vae/minimax_h3_audio_vae_fp32.safetensors`；`loras/` 里是官方模板默认挂的三个 LoRA（`fl2v_turbo_4step_v1.0_768p`、`fl2v_turbo_8step_v1.0`、`ref2v_turbo_4step_v0.1`）
- lightx2v/Minimax-h3-Turbo（文件名都带 `_comfyui_bf16.safetensors` 的才是 ComfyUI 用的）：Ref2V `minimax_h3_ref2v_turbo_8step_v1.1_768p`（草稿档默认）、`…ref2v_turbo_4step_v1.0_768p`、`…ref2v_turbo_4step_v0.1`（544p 档）；FL2V `minimax_h3_fl2v_turbo_8step_v1.0_768p`（默认，配 shift 6 / 3；`v1.2_768p` 更新但配不了 `pruned` 底模，见 `comfyui-nodes.md` §1）、`…fl2v_turbo_4step_v1.3_768p`、`…fl2v_turbo_8step_v1.0`（544p 档）
- larryvrh/MiniMax-H3-Turbo-Lora：`minimax_h3_turbo_v4_step600_ema.safetensors`（FL2VA 4 步备选，漫剧友好）
- alibaba-pai/MiniMax-H3-Acc-LoRAs（PDD 8 步；新版 ComfyUI 原生 LoRA-bank 可直接加载，旧版用 Jalen-Brunson 节点或 aptech0081 重打包）
- LBH-123-AI/Minimax_h3_latent_Upscaler（latent 二采权重：`minimax_h3_latent_upscaler_3d_conv_v1/minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors`，约 0.7 GB，放 `models/latent_upscale_models/`；节点装 GitHub `LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler` 原版，不装 xmarre `-Plus` 分支）
- lihaoyun6/MiniMax-H3-Ref-Patch（FL2VA 仿 Ref2VA）
- alibaba-pai/MiniMax-H3-Fun-Controlnet-Union（姿态 / 深度 / 边缘控制）
- Imagineer13/H3-Anti-Burn-LoRA（仅续接链上的皮肤斑点修复）
- DMAD 4-step LoRA 在 `Kijai/MiniMax-H3-experimental/loras/minimax_h3_DMAD_4step_full_lora_avg_rank_39_bf16.safetensors`（同目录有 PDD Acc-8Step FL2VA/Ref2VA、flashgen 4-step、open_regenerate_2k_refiner r16；2026-11-23 再看时还有 PDMD 2 步 / 4 步、NVIDIA LongLive-Plug 的 4 步版 `minimax_h3_ELM_longlive_plug_4step_lora_bf16`（原版 `Efficient-Large-Model/LongLive-Plug-MiniMax-H3-few-step`，作者写明不要和它的 CFG 蒸馏版叠用）、TaoMate FL2VA 3 步——都是又一种蒸馏 LoRA，和 Turbo 二选一、不叠（铁律 8），本流程没有试过；同一个仓库里的 `…_w4a8_mixed` / `wip/…_w6a8_g32` 是更低比特的底模，`minimax_h3_lynnreal_light_vae_*` / `minimax_h3_lightvae_lite_*` 是轻量视频 VAE，都要比 0.37.2 新的 ComfyUI，见 §2「更快的视频解码」和 `comfyui-nodes.md` §1 的版本表）
- 权重下载源核实：X2 Detail VAE 有官方 `_int8_convrot` 版；lightx2v Turbo-SLA 实为 `fl2v_turbo_4step_v0.1_768p_sla_comfyui_bf16`；FastVideo FastH3 此前是私有仓库，2026-11-21 复查已公开（HF `FastVideo/FastVideo-FastH3-Comfy`，用法见上文 FL2VA 一节的可选项）
