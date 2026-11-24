---
name: minimax-h3-comfyui-short-drama
description: 用本地 ComfyUI 上的 MiniMax H3（海螺 3.0 / Hailuo 03，FL2VA / Ref2VA 开源权重）从剧本、生图（角色卡 / 场景 / 道具 / 逐镜首帧）做到成片的短剧 / 漫剧 / 电影质感短片生产流程，内置 13 个类型包（都市情感、悬疑、古装仙侠、动作打斗、恐怖、喜剧、科幻赛博、3D 国漫、2D 动画、MV、产品广告、口播数字人、手作定格科普）。只要用户提到 MiniMax H3、海螺、Hailuo、H3 工作流、ref2va / fl2va、Turbo LoRA、导演台、短剧分镜、角色一致性、抽卡、二采 / 超分、长视频续接、SageAttention / 稀疏注意力 / 缓存加速、ComfyUI 跑 H3 慢或爆显存，或者想让 agent 接管本地 H3 工作流批量出片——即使没说「短剧」两个字——都要先读本 skill。覆盖：环境盘点与模型文件选择、24 GB 单卡的草稿档 / 精修档加速组合、官方三段式 / 六段式提示词格式与短剧对白规则、分镜分段与角色卡 / 道具绑定、段间续接方案、768P→1080p/2K 画质流水线、QC 与拼接、GitHub 生态里每类工具该用哪个与禁忌清单。
compatibility: 本地 ComfyUI ≥ 0.37（原生 MiniMaxH3 节点；官方滑窗、原生 latent 放大、H3 出图节点与 RelayVSR 需要 ≥ 0.44 / 0.45），单卡 ≥ 16 GB（推荐 24 GB），系统内存 ≥ 32 GB（推荐 64 GB）。脚本是 Python 3.10+（Windows 可直接运行），需要 ffmpeg / ffprobe；Windows 便携版 ComfyUI 请另装 Python，不要装进 `python_embeded`（装法见 `references/local-stack-and-acceleration.md` §0b）。核心脚本只用标准库；可选依赖按用到的装：`numpy`、`faster-whisper`、`pypinyin`、`opencv-python`、`onnxruntime`、`pyJianYingDraft`、`opentimelineio`（各自用在哪，`scripts/selfcheck.py` 会列出来）。模型与 LoRA 从 HuggingFace 下载。
---

# MiniMax H3 × ComfyUI 短剧生产

## 为什么需要这个 skill

H3 是 33B 全模态 DiT：一次出 4–15 s 视频 + 原生立体声对白/音效，开源权重是 **CFG 蒸馏版**（CFG=1、无负向分支），本地 ComfyUI 生态在 2026 下半年爆发出近千个仓库（导演台、续接、加速、提示词、超分、skill）。没有地图的 agent 会：把否定句写进提示词、叠加互斥的加速节点、用 544p LoRA 跑 768p、让模型自己编道具和字幕、每段重新打光换脸。本 skill 把这些坑和已验证的参数固化下来。

## 总流程（每一步只读对应 reference）

```
0 盘点环境 ──► 1 定风格与画幅 ──► 2 系列圣经(角色/场景/道具/音色) ──► 3 分镜 JSON 并校验
      │                                                                   │
      ▼                                                                   ▼
7 QC → 拼接 → 交付 ◄── 6 精修/超分 ◄── 5 抽卡生成(草稿档) ◄── 4 生成提示词(六段式/三段式)
```

| 步 | 做什么 | 读 |
|----|--------|----|
| 0 | 列出 GPU / ComfyUI 版本 / 已有模型与 LoRA / 自定义节点 / 现有工作流；用 `assets/local-inventory-checklist.md` 的清单；跑一次 `scripts/selfcheck.py` 确认 ffmpeg 与后期脚本在这台机器上能用；ComfyUI 开着的时候跑 `scripts/check_setup.py`——它直接问服务器，一次报出版本、PyTorch 是不是 CUDA 13 的构建、启动参数、显存，以及附带的每个工作流缺哪个节点包、哪个模型文件（清单里前四部分的大半由它代劳）；再用 `assets/workflows/selftest_no_model.api.json` 提交一次（不用任何模型，几秒钟），确认脚本连得上 ComfyUI、能上传和取回文件；模型用 `scripts/fetch_models.py --comfyui <ComfyUI 目录>` 核对（缺哪个、哪个没下全、哪个放错了目录，加 `--download` 直接下），齐了之后用 `h3_ref2va.api.json` 配 `smoke_test_prompt.txt` 跑一条 5 s 的冒烟测试（不用任何素材，命令在 `assets/first-run-checklist.md` 第 3 项；它只验证模型齐全、这台机器出得了片，所以借 Ref2VA 工作流直接跑一段纯文字——正式的纯文字段按第 4 步用 FL2VA 的工作流） | `references/local-stack-and-acceleration.md` |
| 1 | 确认类型（`assets/genres/README.md` 选一个类型包，看 H3 适配度与绕法）与风格（电影质感 / 漫剧）、画幅（16:9：训练格点 1344×768 其实是 7:4。默认就用 1344×768 生成——Turbo LoRA 有对应的 768p 版；这个尺寸在 4090 上的耗时是外推的 5–10 min / 10 s，实测数字只有 864×480 的 134 s——交付时上下各裁 6 px 再缩放到 1920×1080；只有画面里有不能裁、不能拉伸的东西（贴边的圆形、文字）才改用真 16:9 的 1536×864，像素多三成、没有配套的 LoRA 档位，先单独试一段）、单集时长、每段时长 | `assets/genres/`、`assets/style-*.md`、`references/model-and-modes.md` 分辨率格点 |
| 2 | 先用 `assets/agent-prompts/01-outline.md` 出大纲和资产表（每个角色的 `sheet_phrase` 是生图的依据；要不要商用现在就问清，它决定出图模型）。再生图：定妆照（锚点，选定后冻结）→ 正面全身 + `face.png` 等单人单视图（拼成的 16:9 角色板只给人审）→ 场景无人母版 + 九宫格 → 道具白底图——出图提示词和命令不用手写：`scripts/plan_stills.py <ep.json>`（要营利就加 `--t2i zimage`，文生图换成可商用的 Z-Image-Turbo）按模板把每张图的提示词写进 `bible/prompts/`，并在 `bible/stills_plan.md` 里逐张列出提交命令（哪个工作流、接哪几张图、尺寸、几个候选、选中后存成什么文件名）和总张数；分镜定了之后再跑一次，逐段首帧和关键帧也排进去（已经有的图标成已完成；之后分镜里的出图提示词改了，再跑一次它会重写对应的提示词文件，并把按旧提示词出的那张图标成 `MAKE AGAIN`）；音色样本（2–15 s 干净人声，6–8 s 最稳）：用户能录就录；录不了就先只抽每个主角**第一次开口的那一段**，选定并采纳（`observe_take.py`）之后从里面截一段该角色的干净人声存成 `bible/voices/<id>.wav`，后面的段都挂它——所以没有录音时，这几段要排在批量抽卡之前做（第 5 步）（截多长、从哪截，见 `references/audio-and-post.md` §2 第 4 点；所以每个主角第一次开口的那一段里要有一句 ≥ 12 字的台词，校验器会提醒（镜头太短放不下 12 字时，它改为提醒把两句接成样本）；加了音色之后重新出提示词，已采纳的段不会被改写——`build_prompts.py` 会保留它们，精修才能按同 seed 复现）。图定下来之后**看着图**给每个角色写三样：进视频提示词的短外貌 `identity_phrase`（发型、主服装、一个标志物，约 12–25 词，有几样写几样；超过 30 词校验器会提醒）、短称 `short_phrase`、声音短语 `voice_phrase`（完整外貌 `sheet_phrase` 只给生图用） | `references/image-stage.md`、`assets/image-prompts.md`、`references/storyboard-and-assets.md` §3 |
| 3 | 用 `assets/agent-prompts/02-storyboard.md` 让 LLM 把剧本切成 5–13 s 的段（对白段 8–12 s，动作 / 硬切镜头 5–8 s；模型支持 4–15 s，但 4 s 低于训练帧数、14–15 s 在 24 GB 上明显变慢），每段 1–4 个子镜头（按段长分档），每镜写景别 / 焦段 / 运镜 / 动作 / 表演 / 台词 / 声音；多人场景的第一段在 `stagings` 里登记开场站位（脚本据此生成固定的走位句）；跑 `scripts/validate_episode.py --rhythm`（分镜点了名、还没做出来的首帧 / 关键帧 / 音色以 `+` 列在后面，不算错误——那些图第 4 步才做），再用 `scripts/render_storyboard.py` 出分镜表给用户审，`03-rhythm-audit.md` 做节奏审计 | `references/storyboard-and-assets.md` §1–2 |
| 4 | 真人中文对白段和关键道具特写先做首帧（编辑模型 + face.png + 场景裁切，`image-stage.md` §4 第 4 步「逐镜首帧」；首帧的宽高比要和生成画布一致，`i2va` 会把首帧直接拉伸到画布）。首帧里只有一张清楚的脸（单人、过肩）→ `ref2va` + `first_frame`，参考图和音色照带（首帧作为 `<Picture 1>` 进去，提示词声明它是第一镜的首帧；构图必须按设计来的后续镜头可以再各配一张关键帧 `shots[].keyframe`，见 `image-stage.md` §5）；首帧里有两张以上清楚的正脸 → 只给首帧，用 `i2va`（再挂身份参考会多出一个人；`i2va` 接不了音色参考——这一段的嗓音不受锚点约束，台词留短，装配后用 `voice_check.py` 量，偏了再变声统一；所以要锁音色的两人对白，首帧尽量设计成过肩：一张清楚的脸，走 `ref2va`）；首帧里没有脸的道具特写 / 空镜 → `ref2va` 挂道具参考图（有首帧就一起给）；首帧先按分镜里**计划的**末态一次全部做完（出图模型只装一次）；上一段选好片后如果实拍和计划对不上，再单独重做下一段的首帧；做不出首帧就 `ref2va` 直出并告诉用户命中率会低。**一张参考图、一段音色都没有**时不用自己改模式：脚本会把该段按纯文字（三段式 `t2va`，要用 FL2VA 权重的工作流）出提示词并提醒——跨段的脸、场景、嗓音都没有东西锁，只适合一次性的镜头，做剧情先去生图。`scripts/build_prompts.py` 生成每段提示词与 `.media.json`（帧数 + 参考的接线顺序）——版式照官方完整示例，人物首次出场的外貌、切镜后的短提醒、台词后的闭嘴、音色引用都由脚本写入，分镜里不要重复；`scripts/lint_prompt.py <提示词>` 机检，FAIL 不提交；本流程的提示词一律由脚本生成；本地 LLM 改写器（`prompt-format.md` §9）是不走分镜 JSON 时的另一条路，其中改写 LoRA 只覆盖三段式 | `references/prompt-format.md` |
| 5 | 草稿档（Turbo 8 步 + Sage）每段 2–3 个 seed（有台词的段 3 个）。**工作流用附带的**：`assets/workflows/h3_ref2va_sage.api.json`（没装 Sage 用 `h3_ref2va.api.json`；`i2va` / `fl2va` / `t2va` 段用 `h3_fl2va*.api.json`）——它们从 0.37.2 自带的官方模板导出再改成本流程的设置，在一台真实的 ComfyUI 0.37.2 上通过了校验，并用一套微型的随机权重模型实际执行到出片（验证的是接线；真模型下的画面、耗时、显存没有测过，Sage 版没有执行过）；每个文件要哪些模型、怎么用 `--set` 调，见 `assets/workflows/README.md`；想用自己导出的模板也行（`comfyui-nodes.md` §3）。默认直接在 1344×768 出（配 `_768p_` 版 LoRA）——选中的那条就是「采纳的片段」，之后只做 latent 二采；想快速看个大概用 `--set 136.width=864 --set 136.height=480`，那样出来的只是预览，不能当采纳的片段（`observe_take.py` 不收比草稿画布小的片段；确实就按这个尺寸做才加 `--small-ok`；Ref2V 没有 8 步的 544p 版 LoRA，预览就用同一个 LoRA 直接跑低分辨率，见 local-stack §2）。`scripts/comfy_submit.py <工作流> --media prompts/ep01/s03.media.json --batch 3 --keep-latent --dry-run` 出批次预览（`--keep-latent` 把一采的 latent 一起存下来，每条多两个小文件，精修时直接从它开始）（接了哪些参考、分辨率、步数、输出目录，这一集里已有同一工作流的成片就据此给预计时长，另有几条「advice」提示工作流里常见的漏接和错配）给用户确认，再带 `--confirm <批次号>` 提交；中断了原样重跑即可续取。**默认先批量、后对账**（出图和出视频各只装一次模型）：`build_prompts.py --allow-planned` 一次出全部段的提示词（接续的段先按计划的末态开场），各段草稿一次抽完——**例外是音色**：角色没有录音样本时，先抽他第一次开口的那一段、选定、**用 `observe_take.py` 采纳**，然后才截样本、写进 `voice_reference`，再批量抽其余的段（顺序不能反：样本一挂上，这个角色开口的、还没采纳的 `ref2va` 段提示词都变，包括样本出处的那一段自己——没采纳就挂，刚抽的草稿就成了按旧提示词抽的（`i2va` / `fl2va` / `t2va` 段接不了音色参考，它们的提示词不受影响）；`build_prompts.py` 会打印一行 `ORDER` 提醒是哪几段）；然后按顺序选片，每选定一条就写回分镜——结尾和计划一样：`scripts/observe_take.py <片段> --episode … --segment s01 --as-planned`；不一样：`--write "实际的末态" --confidence … --deviation "差在哪"`。写完再跑一次 `build_prompts.py`（不带 `--allow-planned`）：下一段标 `[unchanged]` 的，已有的草稿照用；标 `[CHANGED …]` 的，按实拍重做它的首帧和草稿，并重读它第一镜的动作（那是按计划的状态写的）。按旧提示词抽出来的草稿，`build_prompts.py` 每次都会列出来（不只是变的那一次），`observe_take.py` 也不收，并说明变的是什么（提示词、哪张图、后挂的音色）——看过确实接得上再加 `--stale-ok`。每条片段的文件夹里留着它当时用的提示词和参考清单（`prompt.txt`、`media.json`），这样采纳的旧片段精修时用 `--media <那条片段的文件夹>/media.json`。只有要求严格接续的戏（同一机位的连续动作、尾帧接首帧）才一段一段地做 | `assets/workflows/README.md`、`references/local-stack-and-acceleration.md`、`references/comfyui-nodes.md` |
| 6 | 精修中选的那一条：LBH latent 放大 + σ 0.45 二采（音频钉死）→ 1920×1088（比 1344×768 略扁 0.8%，交付时上下各裁 4 px 到 1920×1080）。二采要用一采的 latent：草稿时带了 `--keep-latent` 的，精修直接从存下来的 latent 开始，一采不重跑——`comfy_submit.py assets/workflows/h3_ref2va_sage_refine.api.json --media <同一个 .media.json> --from-latent <中选那条 take 的文件夹> --tag <段号>_refine`（草稿用的是不带 Sage 的版本就用 `h3_ref2va_refine.api.json`；`i2va` / `fl2va` / `t2va` 段用 `h3_fl2va_sage_refine.api.json` / `h3_fl2va_refine.api.json`）；没存 latent 的，去掉 `--from-latent`、改给 `--seed <中选那条的 seed>`，一采按同 seed、同设置原样重跑一遍再接放大。精修工作流的片段不给 `--tag` 时放进 `<段号>_refine_<seed>`，不会和草稿挤在同一个目录；从 latent 精修时节点上的画布和帧数由脚本按那条草稿的记录自动设好，预览会说明这次的提示词、参考、画布和帧数是否和那条草稿一致（不一致的带 `WARNING`，并在确认行之前再提醒一次）；细节见 `quality-pipeline.md` §2。10 s 以上的段直接二采在 24 GB 上可能爆显存（没有 4090 实测）；二采显存不够时换 `h3_ref2va*_refine_split.api.json` / `h3_fl2va*_refine_split.api.json`（同样的二采，按时间分块做；命令不变，只换工作流文件）；还不行就先用草稿装配——`mix_episode.py` 会把 1344×768 的片段缩放到 1920×1080，成片照样能交。小脸先修再放大；只有单镜 > 15 s 才续接 | `references/quality-pipeline.md`、`references/continuity-long-video.md` |
| 7 | QC：`qc_probe.py`（含镜头数对账）→ `qc_dialogue.py` → `identity_gate.py`（真人）/ `identity_gate_anime.py`（漫剧）→ `contact_sheet.py` + 人眼；后期：`make_edl.py`（逐段核对进剪辑单的是不是采纳的那条或它的精修，不是就 WARN，混音验收时再提醒一次）→ `retime_subtitles.py` → `mix_episode.py`（帧精确拼接、逐段电平、配乐压低、成片响度、验收；段间音色不齐先用 `voice_check.py` 量出是哪几句）→ 需要人工精修时 `export_capcut_draft.py` / `export_otio.py` | `references/qc-and-assembly.md`、`references/audio-and-post.md` |

生态里每类任务该选哪个仓库、为什么，见 `references/ecosystem-map.md`；所有已知禁忌集中在 `references/pitfalls.md`。

**接着做一个已经开工的项目**（换了对话、重启过、隔了几天）：先在项目根目录跑 `scripts/project_status.py episodes/ep01.json`——它只读，一屏列出每一段的提示词出没出、有几条草稿（几条是按旧提示词抽的）、采纳的是哪条、有没有它的精修、剪辑单里用的是哪个片段，以及每段的下一步命令；段落之后是剪辑单、字幕对时、混音各自还对不对得上当前的剪辑。照它说的下一步接着做，不用自己翻文件夹推断。

**只做质检和后期**（片段已经生成好了）：直接看 `references/qc-and-assembly.md` §0——只需要一份带段 id、镜头起点和锁定台词的精简分镜，不必先让 `validate_episode.py` 通过。

**命令约定**：所有脚本都在项目根目录下运行，写作 `python <本 skill 目录>/scripts/xxx.py …`（下文与各 reference 里简写成 `scripts/xxx.py`）；通配符放进引号由脚本自己展开；每个脚本都有 `--help`。references 里引用的 `docs/…`、`workflows/…`、`templates/…`，以及只写了文件名的 `NN-xxx.md`（如 `04-prompting-tools.md`、`12-fresh-followup.md`），都在仓库里、不随 skill 安装：<https://github.com/Tofu-killer/minimax-h3-short-drama/tree/main/docs>。

## 必须遵守的铁律

1. **描述英文、台词原语言**，台词只放在 `<d>[Chinese] …</d>` 里。
2. **没有自由否定句**。开源权重无负向分支，`no X` 会被画出来；写正向锁定。仅允许：本流程固定使用、lint 放行的两句保留说明（`no other item is substituted`、`never transfer facial traits from <Picture N>`——由脚本写进 retention 一栏，不是官方指南的原文）、`Exactly N people` 式正向计数、摄影机静止那一句（`with no camera movement whatsoever`）、至多一句具体失败词（`NO black letterbox bars`）。真要排除某物用带负权重的节点而不是文字：NegPiP（`(red glow:-3)`），或 KJNodes 的实验节点 `MiniMax H3 Prompt Weight`（`(word:-1)` 去掉一个概念；它替换 H3 的条件节点，`--media` 不会自动接它，要在界面里手接）。校验器和 lint 对否定句只给警告（它们分不清官方保留句式和自由否定），**看到警告要自己改成正向写法**，不是放着不管。
3. **一镜一人开口、一镜一个运镜**；听者写 `listens with mouth closed`。
4. **台词预算**：硬上限 ≤ (段长−2 s)×4.5 字（校验器口径），目标语速 3.3–4 字/s，快档 ≤ 5 字/s 且连续不超 3 s；超了拆段，不要让角色说快。
5. **参考媒体一职责一张图**：脸 / 服装 / 环境 / 道具 / 音色分开；编号用脚本替换，不手写 `<Picture N>`。
6. **剧情里出现的关键道具要有参考图**（脚本会声明 `the exact item shown in <Picture N>`），否则模型一定会编，而且每段编得不一样——没图时校验器只警告、提示词里用文字描述它，结果要如实告诉用户；等级框、UI、字幕一律后期叠。
7. **CFG 固定 1.0**；Turbo LoRA 用与分辨率匹配的版本（1344×768 用 `_768p_` 版）；shift：默认的 12 / 3 就是模型自带的值，Ref2V 的 LoRA（8 步 v1.1）用它，不用接 shift 节点；FL2V 用 8 步 **v1.0 的 768p 版**，它要 6 / 3（调度器和引导器的 `model` 都要接 shift 节点的输出——附带的 `h3_fl2va*.api.json` 已经接好）。FL2V 8 步 v1.2 不要配 `pruned` 底模：它多改 51 个时间调制层，`pruned` 底模里这些层是另一种存法，挂不上（`comfyui-nodes.md` §1「LoRA 和底模对不对得上」）。各版本的值见 `references/comfyui-nodes.md` §1。
8. **加速只叠「无损 + 一个蒸馏」**：SageAttention（或 Sol-Attn 稠密核）+ 一个 Turbo/PDD LoRA；不叠加两个蒸馏 LoRA，不把 SageAttention 与 `MiniMaxLowVRAMAttention` 同开（二选一：这台机器上实测同开第一步 693 s；新版 KJNodes 说两者可以配合，没有在这里重新测过之前仍按互斥处理），不在精修档开 Spectrum / BlockSparse 等有损方案。
9. **先跑一次基线再加东西**：基线 = int8 底模 + Turbo 8 步 + Sage（就是附带的 `h3_ref2va_sage.api.json`）、别的加速全关，用一段固定的提示词记下耗时——固定的那一段取样片的第一段：把它的 `.txt` 和 `.media.json` 复制到 `logs/baseline/`，以后每次都提交这份副本（`comfy_submit.py <工作流> --media logs/baseline/s01.media.json --tag baseline --out takes/baseline --batch 2`，两个 seed，计时看第二条——第一条含冷启动；以后重测换一个 `--seed`，同样的输入会被当成已完成跳过）；之后逐个打开别的加速项，一次只改一个变量。`comfy_submit.py --log logs/takes.csv` 会记下每个 take 的耗时、seed、帧数和设置摘要（分辨率 / 步数 / 模型 / LoRA）；评分自己填在 `score` 列，显存峰值看 ComfyUI 控制台。
10. **抽卡有上限**：一批 2–3 个 seed；同一个问题连续两批都在 = 改提示词或分镜，不是继续换 seed。偶发的技术故障（黑场、无声、任务报错）原样重试一次。
11. **每段写 `end_state` 与 `continuity`**，下一段从上一段终态开场——同场景接续的段从**已采纳片段的实拍末态**开场（`observe_take.py` 写回，`continuity` 写 `"@observed"`；实拍和计划一致时用 `--as-planned` 原样确认），不是从没核对过的计划 `end_state`；不写「continue the previous video」。段与段的三种接法按这个顺序选：① 硬切，状态靠文字 + 同一组参考图带过去（默认）；② 同一机位的连续动作，把上一段尾帧（`extract_tail_frame.py --size <生成画布>`）当下一段的 `first_frame`；③ 单个镜头超过 15 s 才用 latent 续接。
12. **可复现**：任何一段都能从 `prompts/ + bible/ + project.yaml` 重生成（`project.yaml` 是给人看的项目记录，模板与目录布局见 `qc-and-assembly.md` §4）；参数写进 `logs/takes.csv`。
13. **短剧默认硬切，不续接**：每段 5–13 s 独立 Ref2VA + 同一组参考图 + 音色锚；一条续接链 ≤ 4 段，链上关 Spectrum、不改分辨率 / LoRA / shift。
14. **段尾写 0.5 s 收束 + 1 s 定格，拼接时剪掉**（末镜标 `"end_hold": true`——提示词、质检和剪辑单都靠这个字段知道这一秒是定格）。硬切的下一段首镜换景别或角度；只有用尾帧接（上条 ②）时才同档景别起手，并同时带角色参考——此时参考图容易超过 6 张，去掉场景图或一张细节图。
15. **有台词的镜头整镜只做说话**（动作放前一个镜头）；单段说话人 ≤ 2；台词在定稿前可以和用户商量着改顺口，**锁定后永不改写**（LLM、ASR 都不许动它）；说话重讲 / 含糊先换 seed。
16. **运镜是主体的镜头定稿用 20 步、关 Turbo 重出**（4 步 Turbo 几乎抹掉运镜；8 步可做草稿）——跟拍、环绕、大幅推拉属于这一类，重出的是一条新片段，要重新选片和观测；对白镜头里那种小幅慢推先看 8 步草稿里推镜出没出来，出来了就照常走 latent 二采，没出来再按本条重出；场景参考图会让运镜减半——运镜是主体的段在分镜里写 `"use_scene_reference": false`，只挂身份参考，地点靠文字描述；需要锁环境的段照常挂。
17. **真人对白段先出首帧再生成**（盲评：直出 0:4 输，垫首帧 4:0 赢）；漫剧可直出；没有生图条件时直出并如实告知。首帧尺寸 = 生成画布，画面里不能有字幕或 UI。参考视频先重采到 24 fps（节点不重采样）。
18. **默认留在本地 H3，换模型要有触发条件**：同一问题按 `pitfalls.md` 改过仍连续不过，且属于 `beyond-h3.md` 路由表里的镜头类型，才换本地替补（Wan-Animate-2、Fun Camera、InfiniteTalk、Bernini-R）或云端；草稿永远先在本地确认，换出去的片段回到同一条后期链（24 fps、同一超分、ColorMatch）。
19. **后期只认一份剪辑单**：字幕文字永远取自分镜的锁定台词，识别 / 对齐只提供时间；台词质检不给识别器任何文字提示；切点、电平、配乐都改 `edit/<集>.edl.json` 后重跑，不手工拼 ffmpeg 命令；成片以 `mix_episode.py` 的验收（音画等长、帧数、响度、真峰）为准。
20. **每步落盘 + 选择卡**：会花 GPU 时间的步骤前给用户一张选择卡（推荐项放第一）——卡上的内容来自 `comfy_submit.py --dry-run` 的批次预览（哪些要跑、哪些已完成、预计多久、批次号），用户确认后带 `--confirm <批次号>` 提交，输入变了批次号就变、确认随之失效；「继续」不等于确认了一个改过的批次。产物带 seed / 参数 / 指纹，重跑幂等跳过已完成段；一集的段全部过 QC 再开下一集。

## 单段样片先行

先做 1 段「最能暴露问题」的样片（主角正脸 + 一句中文对白 + 一次有动机运镜 + 手部道具）走完 0–7，再扩到 30 s（3–4 段；第一次在这台机器上做用 4 段 9 / 9 / 8 / 8 s，见 `storyboard-and-assets.md` §1），再 60 s。第一次在一台机器上开工，样片就照 `assets/first-run-checklist.md` 的顺序做——它把文档里标着「没有实跑过」的做法逐项验一遍，结果记进 `logs/machine-notes.md`，之后用实测的数。每次重抽只改一个变量；同一错误连续两批无改善就回上层（资产 / 分镜），不再抽卡。

## 和用户沟通时

- 用户常把「画质差」归因于步数：先查是否 4 步、是否 544p LoRA 跑 768p、FL2V 768p 版是否还用 shift 12、是否没带参考图。见 `references/pitfalls.md` 的「症状→原因」表。
- 用户问「别人 5070 为什么比我 4090 快」：对比分辨率（544p vs 768p）、步数、是否 Turbo、是否 Windows CUDA 系统内存回退、是否 Sage。给出同口径基准再比。
- 给出耗时估算时注明口径：分辨率 × 时长 × 步数 × 硬件，并引用 `local-stack-and-acceleration.md` 的基准表。
- 用户在海外（无 ModelScope / 网盘）时，模型、LoRA、节点、模板只给 HuggingFace / GitHub 链接（Python 包走 PyPI 的 `pip`，ffmpeg 用 `winget` 或 GitHub 上的发布包，Python 本身从 python.org 或 `winget` 装——这三样不在 HF / GitHub 上）；文件名以 Comfy-Org / lightx2v 的 HF 仓库为准（核对过的清单在 `local-stack-and-acceleration.md` §0b 与 §7）。
- 开工前要问清的几件事：是否商用（决定出图模型，Qwen-Image 2.1 是非商用许可）、片子打算发到哪里（H3 的社区许可不含美国、欧盟、英国、韩国，条款摘录见 `references/model-and-modes.md`）、能不能自己录音色样本、先做一段样片还是直接做 30 s、要不要为了快先用 864×480 看个大概。
- **只回答问到的范围**：问加速就给两档配置与下载清单，不要把画质流水线、生态黑名单整段搬进来；基准数字一律标注「单机实测，口径 分辨率×时长×步数」。
- **写提示词时只写参考图里真实存在的锚点**（门、灯、标志）；看不到参考图就用泛指或先问用户，不要凭想象给场景加元素。
- 不确定 ComfyUI 节点的输入口名称时，以 `references/comfyui-nodes.md`（来自核心源码，并和一台真实 0.37.2 的 `/object_info` 对过）为准，不要发明 `duration` / `aspect_ratio` / `prompt_optimizer` 之类的参数。

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/validate_episode.py <ep.json> [--rhythm] [--catalog props.json]` | 分镜校验：时长、台词预算、一镜一说话人、未知资产、道具无图、空终态、已采纳但没观测末态的段、拼错的字段名（会提示最接近的正确名字）、否定句；分镜点了名但还不在盘上的图 / 音色以 `+` 列出，不算错误；已采纳的片段文件不在了、或者内容被换过（和采纳时的 sha256 不一样）会提醒；`--rhythm` 加纯算术的节奏审计（超载、各镜等长、连续三镜同景别、台词塞不进镜头、开场偏慢）。警告以 `~` 打印，不影响退出码 |
| `scripts/render_storyboard.py <ep.json> --out ep01_storyboard.md` | 把分镜 JSON 渲染成人能审的分镜表（每镜时间、景别 / 焦段、运镜、动作、表演、光线、台词与语速、声音） |
| `scripts/plan_stills.py <ep.json> [--back 角色id …] [--side 角色id …] [--t2i zimage]` | 出图阶段的清单：按 `assets/image-prompts.md` 的模板写出每张图的提示词（定妆照 / 全身 / face 来自角色的 `sheet_phrase`，母版 / 九宫格 / 道具来自描述，首帧 / 关键帧来自分镜里的 `first_frame_prompt` / `keyframe_prompt`），并在 `bible/stills_plan.md` 逐张列出提交命令：工作流、`image1`–`image3` 各接哪张图（从提示词里的 `Picture N` 句子读出来）、尺寸、候选数、选中后存成的文件名（就是分镜里已经写的路径）；已经在盘上的图标成已完成；它写的提示词文件跟着分镜走（分镜改了就重写，并把按旧提示词出的图标成 `MAKE AGAIN`），手改过的提示词文件不动（`--rewrite` 才覆盖）；营利项目加 `--t2i zimage`，定妆照 / 母版 / 道具的命令改用 Apache-2.0 的 Z-Image-Turbo（默认的 Qwen-Image 2.1 是研究许可）；不提交任何任务 |
| `scripts/build_prompts.py <ep.json> --out prompts/ep01 [--only s03] [--allow-planned]` | 生成每段最终提示词 `.txt` + 媒体顺序 `.media.json` + `planned_cues.srt`（计划的台词时间，只供预览）；分镜本身有错误（时长、台词预算、未知资产……）时一段都不出（`--force` 强行出，警告从不拦）；某一段点名的图 / 音色还不在盘上，只跳过这一段（列在 `NOT BUILT` 下，退出码 1），其余照出；`continuity` 为 `"@observed"` 的段从上一段实拍末态开场，尚未观测时不出这一段。每次都报告：各段提示词变没变、`takes/<--out 的文件夹名>/<段>` 里有几条成片是按旧提示词抽的、还缺音色样本时该先抽哪几段 |
| `scripts/observe_take.py <采纳的那条草稿 mp4> --episode ep.json --segment s01 [--as-planned \| --write "…" --confidence high --deviation "…"] [--stale-ok] [--small-ok] [--force]`（`--segment` 是这条片段所属的段，不是下一段） | 出已采纳片段的观测表（首帧 / 中段 / 末帧；末镜标了 `end_hold` 时自动跳过 1 s 定格取「最后一个运动帧」），再把实拍末态、置信度、与计划的偏差写回分镜。写回的文字会原样进下一段提示词——写人在房间里的位置，不写画面坐标；可以提到下一段不出场的人。采纳前对照片段旁边的 `run.json`：别的段的片段、长度不对的片段不收（`--force` 才收）；按旧提示词或旧参考抽的草稿不收，并说明变了什么（看过接得上再加 `--stale-ok`）；比草稿画布小的预览片段不收（`--small-ok`）；前一段后来换了结尾，`validate_episode.py` 会一直提醒去看这一刀 |
| `scripts/comfy_submit.py <wf.api.json> --media prompts/ep01/s03.media.json --batch N [--dry-run \| --confirm <批次号>] [--out takes/ep01/s03 --tag s03] [--set …] [--free-every 3] [--log logs/takes.csv] [--anchor] [--keep-latent] [--from-latent <take 文件夹>] [--write-workflow <路径>]`（`--out` / `--tag` 不给时按 `--media` 推出 `takes/<提示词文件夹名>/<段 id>`；带二采节点的工作流 tag 默认是 `<段 id>_refine`） | 向本地 ComfyUI 提交 API 格式的工作流（附带的 `assets/workflows/*.api.json`，或你自己导出的——官方模板原样导出的也能读：开关选出的步数 / LoRA、选择器算出的分辨率都会在预览里显示实际值）。`--media` 把这一段的提示词、帧数和全部参考图 / 音色**按提示词里的编号顺序自动接进工作流**（不用手改 JSON）；`--set 节点id.输入=值` 再覆盖个别参数。提交前**预检**（节点是否安装、模型 / LoRA 文件名是否在服务器列表里并给出最接近的名字、必填输入、H3 节点的帧数 17k+5 和宽高 32 倍数、参考的键名写法、提示词提到的 `<Picture N>` 是否真的接了图、提示词是不是还空着或者是一个忘了写 `@` 的文件名、图片位是不是还没给、`--set` 写的输入名这个节点有没有、有没有把数字写成了 `2688x1536` 这样的文字；出图工作流的尺寸不是本流程用的那几档、首帧图的比例和画布不一样时给 advice；和 ComfyUI 自己的规则一样，只查连着输出的那部分；连不上服务器时只做不需要服务器的那几项，并在预览里说明）；`--dry-run` 打印接线表与关键设置。每个 take 按「最终工作流 + 上传文件内容」算指纹，**相同的已完成 take 自动跳过**；每条 take 的文件夹里除了 `run.json`，还留着它当时的提示词（`prompt.txt`）和参考清单（`media.json`，可以直接当 `--media` 用）；任务被受理就把 `prompt_id` 落盘，脚本中断后原样重跑会**接回原任务**而不是重复提交；同一目录里旧结果移到 `_prev_*` 不覆盖。轮询 ≥ 20 s |
| `scripts/qc_probe.py "takes/ep01/**/*.mp4" --episode ep.json --freeze-tail 1.0 --out qc/probe` | 技术 QC。FAIL：缺音轨 / 帧率 / 时长不符、音频削波、冻结 > 1 s、黑场 > 0.25 s；WARN：**镜头数与分镜对不上**（少切、多切、切点偏移）、首尾跳帧、**画面里烧着字**、近乎静止、峰值偏高、画幅不符。定格尾只在标了 `end_hold` 的段上排除。没有分镜时用 `--expect-seconds / --expect-size / --shots 0,3.5` |
| `scripts/qc_dialogue.py --episode ep.json --targets "takes/ep01/**/*.mp4" --out qc/dialogue` | 台词质检：每句是否说了、说全、只说一次、何时说；无台词段是否擅自说话；输出首 / 末字时间与语速（需 `faster-whisper`） |
| `scripts/contact_sheet.py "takes/ep01/s03/**/*.mp4" --episode ep.json [--out-dir qc/sheets]`（每个候选在自己的子文件夹里，所以用 `**`） | 联络表：首帧、最后一个运动帧（给了 `--episode` 时，标了 `end_hold` 的段自动跳过 1 s 定格）、跳变帧、每个切点前后各一帧、每镜中段，帧下印秒数 |
| `scripts/identity_gate.py --episode ep.json --targets "takes/**/*.mp4" --out qc/identity` | 真人脸身份门禁（YuNet + SFace，CPU 可跑，首次自动从 HuggingFace 下模型）：逐帧把脸指派给本段应出现的角色，报换人 / 克隆脸 / 多出的人，并先自检角色之间是否撞脸；默认只警告，`--strict` 才拦截。动漫脸检测不到，改用下一行的动漫轨 |
| `scripts/identity_gate_anime.py --episode ep.json --targets "first/*.png" "takes/**/*.mp4" --out qc/identity_anime` | 动漫 / 手绘 / 3D 国漫的身份门禁（CCIP 动漫角色相似度模型，CPU 可跑，首次从 HuggingFace 下 150 MB）：整张图与角色参考比，差异 ≤ 0.178 同一角色、0.178–0.30 去看、> 0.30 换人；先自检角色库（两个角色差异 ≤ 0.178 = 撞脸）。**只判单角色画面**（派生视图、单人首帧、单人段），多人画面列出数值但不判，交给 `assets/judge-take-prompt.md` |
| `scripts/extract_tail_frame.py <mp4> --out tail.png --trim-freeze 1.0 [--size 1344x768] [--after-cut N]` | 截末帧（duration−0.2 s）作下一段首帧 / 参考（`--size` 缩放裁切到生成画布；带 `--trim-freeze` 时还会在片段旁写一个去掉定格尾的 `<片段>_trimmed.mp4`，`--no-trimmed-clip` 关闭）；`--after-cut N` 取第 N 个硬切后的第一帧（给反打 / 特写出同一空间的首帧） |
| `scripts/make_edl.py ep.json --selects selects/ep01 --out edit/ep01.edl.json [--pick s03=<片段>]` | 从分镜 + 选中的片段生成剪辑单（选片 = 把片段以段 id 开头的文件名放进 `selects/ep01/`，一段一个——放了两个不猜，报 `AMBIGUOUS`；或用 `--pick` 指定）：每段入出帧（裁起始音节与声明的定格尾）、锁定台词、L-cut；每段的片段都和分镜里记的采纳片段对一遍——是它本身、它的精修（同提示词、同参考、同 seed）或这两者的复制品就不出声，别的 seed、按旧提示词抽的草稿、没采纳过的段给 WARN（剪辑单照出，`mix_episode.py` 验收时再提醒）；之后所有后期脚本都读它，手改不会被覆盖 |
| `scripts/retime_subtitles.py edit/ep01.edl.json --out subs/ep01 [--bilingual] [--font …]` | 字幕：文字 = 锁定台词，时间 = 音频（识别器的词时间再按人声能量收回，避免字幕早出）；出 `.srt` / `.ass`，把每句起止时间写回剪辑单并标出要复核的句子；手改过并加 `"locked": true` 的句子不再覆盖（需 `faster-whisper`） |
| `scripts/mix_episode.py edit/ep01.edl.json --out final/ep01.mp4 [--ass subs/ep01.ass] [--stems-out audio/ep01/stems]` | 装配与母带：帧精确拼接、按台词区间对齐各段电平（单句可用 `gain_db` 微调）、环境声底、配乐在台词处自动压低、成片 −14 LUFS / −1.5 dBTP、逐帧准确地烧字幕（片段里已有字会警告）；自动验收并写报告 |
| `scripts/voice_check.py edit/ep01.edl.json --out qc/voice [--episode ep.json \| --anchor 角色=样音.wav]` | 音色漂移量化：逐句测中位基频，与角色锚点（或本集该角色的中位数）比，≤ 0.5 半音不动、0.5–2 半音去听、> 2 半音重抽或变声；台词下面压着音效 / 配乐测不准的句子标 `unreadable`（需 `numpy`） |
| `scripts/export_capcut_draft.py edit/ep01.edl.json --drafts "<剪映草稿目录>" [--report … --mix …]` | 导出可在剪映 / CapCut 里继续精修的草稿（切点与自动成片逐帧一致；需 `pyJianYingDraft`） |
| `scripts/export_otio.py edit/ep01.edl.json --out edit/ep01` | 导出 `.otio` + FCP7 XML + CMX3600，给 Resolve / Premiere（需 `opentimelineio`） |
| `scripts/lint_prompt.py prompts/ep01/s03.txt`（自动读同名 `.media.json`；手写的提示词给 `--seconds 10 --images 4 --audios 1`） | 提示词机检：字段顺序、时码递增与 1.2 s 下限、17k+5 有效时长、`<d>` 配对、标签先定义后引用、retention 关键词、否定句、静止句、全角符号、字数 |
| `scripts/make_character_board.py --face face.png --views full.png side.png back.png --out sheet.png` | 把单人单视图拼成 16:9 角色审阅板——只给人看，不当参考图 |
| `scripts/fetch_models.py --comfyui <ComfyUI 目录> [--sets ref2va stills refine fl2va zimage] [--download] [--verify-hash]`（`stills` = `t2i` + `edit`；营利项目用 `--sets ref2va edit zimage refine`） | 按清单（`assets/workflows/models.json`：HuggingFace 仓库、该放的目录、大小、SHA-256）核对附带工作流要用的模型文件：在不在、下没下全、是不是放错了目录；默认只检查、不改任何东西，加 `--download` 才下载缺的（断了重跑会接着下，边下边校验哈希；只用标准库、不需要 token） |
| `scripts/project_status.py <ep.json> [--json logs/status.json]` | 项目进度总览（只读）：逐段列出缺的图 / 音色、提示词状态（没出 / 已出 / 分镜改过之后过期）、草稿和二采、采纳的片段及它的精修、剪辑单里用的片段是什么，并给出下一步的命令；最后是剪辑单、字幕对时、混音是否仍属于当前的剪辑。文件夹按其它脚本的默认名找（`prompts/<集>`、`takes/<集>`、`selects/<集>`、`edit/<集>.edl.json`、`final/<集>.mp4`），不在默认位置用 `--prompts` / `--takes` / `--selects` / `--edl` / `--final` 指 |
| `scripts/check_setup.py [--server http://127.0.0.1:8188] [--json logs/setup.json]` | 只读地问正在运行的 ComfyUI：版本、PyTorch 构建（低于 CUDA 13 会提醒 int8 没有快速核）、启动参数（改变模型加载方式的会指出）、显存和内存、ComfyUI 要求而没装对版本的包；附带的 18 个工作流逐个标 READY / MISSING——缺节点就说装哪个节点包，缺模型文件就说放哪个目录、用 `fetch_models.py` 的哪一组，文件放深了一层也认得出。看不到的三样它会列出来：`sageattention` 包、启动日志、没下全的文件。Ref2VA 草稿工作流就绪时退出码 0 |
| `scripts/selfcheck.py [--keep work]` | 装完 skill 先跑一次（约 1 分钟、不用 GPU、不用模型）：用合成素材把校验 → 提示词 → 技术 QC → 联络表 → 剪辑单 → 字幕 → 台词质检流程 → 音色检查 → 混音母带 → 两种工程导出整条链走一遍，逐步报 PASS / FAIL / SKIP，并列出缺哪些可选依赖。它不测语音识别本身和 ComfyUI |
| `scripts/fetch_official_guides.py [目录]` | 拉取 MiniMax 官方提示词指南原文作对照 |
| `scripts/h3lib/catalog.py build <dir> --kind prop --out props.json` | 把道具图目录化（稀有度从路径解析），供 `validate_episode.py --catalog props.json` 检查 |

## 参考文件索引

| 文件 | 何时读 |
|------|--------|
| `references/image-stage.md` | 生图阶段：选哪个本地生图 / 编辑模型（HF 文件名、采样）、角色板 / 场景 / 道具 / 首帧版式、一致性流程、身份门禁 |
| `references/model-and-modes.md` | 第一次接触 H3；选 FL2VA / Ref2VA；24 GB 标准文件组合 |
| `references/local-stack-and-acceleration.md` | 盘点环境、选草稿/精修档加速组合、排查慢与 OOM |
| `references/comfyui-nodes.md` | 原生节点与各家导演台/续接/加速节点的参数速查 |
| `references/prompt-format.md` | 写或审任何一条提示词 |
| `references/storyboard-and-assets.md` | 切分镜、建角色卡、一致性 |
| `references/continuity-long-video.md` | 超过 15 s、段间衔接、接缝伪影 |
| `references/quality-pipeline.md` | 768P→1080p/2K、人脸修复、角色三视图、ControlNet、换人 |
| `references/camera-and-performance.md` | 写运镜句、表演、空间锚点卡、台词排播、参考媒体预处理（有实跑数据） |
| `references/lora-and-style.md` | 要不要训角色 LoRA、风格 LoRA 选型与强度、三视图 LoRA、本地提示词改写 LoRA |
| `references/qc-and-assembly.md` | QC 的顺序与阈值、失败码与返工分流、抽卡策略、剪辑单与装配、导出剪辑工程、目录规范 |
| `references/audio-and-post.md` | 声音怎么做：保留原声 / 重配改嘴 / 先音后画三条链路怎么选，环境声、配乐、分轨、音色统一，TTS / 变声 / 改嘴工具与许可 |
| `assets/workflows/README.md` | 附带的工作流：每个文件做什么、要下哪些模型（文件名、目录、大小）、常用的 `--set`、验证到了哪一步 |
| `assets/first-run-checklist.md` | 第一次在这台机器上跑：按顺序验证的事项和记录模板 |
| `assets/genres/README.md` | 按类型选参数、风格句、镜头 / 表演 / 声音要点与示例提示词；H3 弱的类型（打斗、slapstick、大特效、真人口播）怎么绕 |
| `references/beyond-h3.md` | H3 连续不过或分镜阶段就知道做不了的镜头（打戏、指定运镜、> 15 s 长镜头、给定音频口型、局部修补、特效层）该换哪个本地模型或云端模型、怎么接回来；别的工作流里能搬进来的做法 |
| `references/ecosystem-map.md` | 「这件事 GitHub 上谁做得最好」 |
| `references/pitfalls.md` | 症状→原因→修法 |
