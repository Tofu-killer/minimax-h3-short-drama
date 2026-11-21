---
name: minimax-h3-comfyui-short-drama
description: 用本地 ComfyUI 上的 MiniMax H3（海螺 3.0 / Hailuo 03，FL2VA / Ref2VA 开源权重）从剧本、生图（角色卡 / 场景 / 道具 / 逐镜首帧）做到成片的短剧 / 漫剧 / 电影质感短片生产流程，内置 13 个类型包（都市情感、悬疑、古装仙侠、动作打斗、恐怖、喜剧、科幻赛博、3D 国漫、2D 动画、MV、产品广告、口播数字人、手作定格科普）。只要用户提到 MiniMax H3、海螺、Hailuo、H3 工作流、ref2va / fl2va、Turbo LoRA、导演台、短剧分镜、角色一致性、抽卡、二采 / 超分、长视频续接、SageAttention / 稀疏注意力 / 缓存加速、ComfyUI 跑 H3 慢或爆显存，或者想让 agent 接管本地 H3 工作流批量出片——即使没说「短剧」两个字——都要先读本 skill。覆盖：环境盘点与模型文件选择、24 GB 单卡的草稿档 / 精修档加速组合、官方三段式 / 六段式提示词格式与短剧对白规则、分镜分段与角色卡 / 道具绑定、段间续接方案、768P→1080p/2K 画质流水线、QC 与拼接、GitHub 生态里每类工具该用哪个与禁忌清单。
compatibility: 本地 ComfyUI ≥ 0.37（原生 MiniMaxH3 节点；官方滑窗、原生 latent 放大、H3 出图节点与 RelayVSR 需要 ≥ 0.44 / 0.45，当前最新 0.46.2），单卡 ≥ 16 GB（推荐 24 GB），系统内存 ≥ 32 GB（推荐 64 GB）。脚本需要 Python 3.10+ 与 ffmpeg / ffprobe，核心脚本只用标准库；可选依赖按用到的装：台词质检与字幕对时 `faster-whisper`（建议加 `pypinyin`）、身份门禁 `opencv-python`、导出剪映草稿 `pyJianYingDraft`、导出 OTIO `opentimelineio`。模型与 LoRA 从 HuggingFace 下载。
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
| 0 | 列出 GPU / ComfyUI 版本 / 已有模型与 LoRA / 自定义节点 / 现有工作流；用 `assets/local-inventory-checklist.md` 的清单；跑一次 `scripts/selfcheck.py` 确认 ffmpeg 与后期脚本在这台机器上能用 | `references/local-stack-and-acceleration.md` |
| 1 | 确认类型（`assets/genres/README.md` 选一个类型包，看 H3 适配度与绕法）与风格（电影质感 / 漫剧）、画幅（16:9：训练格点 1344×768 其实是 7:4，真 16:9 用 1536×864 或生成后 lanczos 到 1920×1080）、单集时长、每段时长 | `assets/genres/`、`assets/style-*.md`、`references/model-and-modes.md` 分辨率格点 |
| 2 | 生图：定妆照（锚点，选定后冻结）→ 正面全身 + `face.png` 等单人单视图（拼成的 16:9 角色板只给人审）→ 场景无人母版 + 九宫格 → 道具白底图；再备 2–15 s 干净音色；写识别短语 + 声音短语 | `references/image-stage.md`、`assets/image-prompts.md`、`references/storyboard-and-assets.md` §3 |
| 3 | 用 `assets/agent-prompts/01-outline.md` → `02-storyboard.md` 让 LLM 把剧本切成 4–15 s 段（对白段 8–12 s，动作 / 硬切镜头 5–8 s），每段 2–4 子镜头，每镜写景别 / 焦段 / 运镜 / 动作 / 表演 / 光线 / 台词 / 声音；跑 `scripts/validate_episode.py --rhythm`，再用 `scripts/render_storyboard.py` 出分镜表给用户审，`03-rhythm-audit.md` 做节奏审计 | `references/storyboard-and-assets.md` §1–2 |
| 4 | 需要首帧的段（中文真人对白、关键道具特写）用编辑模型 + face.png + 场景裁切出字面首帧（`image-stage.md` §⑤）；`scripts/build_prompts.py` 生成每段提示词与媒体顺序；`scripts/lint_prompt.py` 机检，FAIL 不提交；本地 Ollama 改写只用于三段式，六段式手写 | `references/prompt-format.md` |
| 5 | 草稿档（Turbo 8 步 + Sage + 768P）每段 2–4 个 seed；先 `scripts/comfy_submit.py … --dry-run` 出批次预览给用户确认，再带 `--confirm <批次号>` 提交；中断了原样重跑即可续取 | `references/local-stack-and-acceleration.md`、`references/comfyui-nodes.md` |
| 6 | 中选段**同 seed** 精修：LBH latent 放大 + σ 0.45 二采（音频钉死）→ 1920×1088；小脸先修再放大；只有单镜 > 15 s 才续接 | `references/quality-pipeline.md`、`references/continuity-long-video.md` |
| 7 | QC：`qc_probe.py`（含镜头数对账）→ `qc_dialogue.py` → `identity_gate.py` → `contact_sheet.py` + 人眼；后期：`make_edl.py` → `retime_subtitles.py` → `mix_episode.py`（帧精确拼接、逐段电平、配乐压低、成片响度、验收）→ 需要人工精修时 `export_capcut_draft.py` / `export_otio.py` | `references/qc-and-assembly.md`、`references/audio-and-post.md` |

生态里每类任务该选哪个仓库、为什么，见 `references/ecosystem-map.md`；所有已知禁忌集中在 `references/pitfalls.md`。

## 必须遵守的铁律

1. **描述英文、台词原语言**，台词只放在 `<d>[Chinese] …</d>` 里。
2. **没有自由否定句**。开源权重无负向分支，`no X` 会被画出来；写正向锁定。仅允许：官方保留句式（`no other item is substituted`、`never transfer facial traits from <Picture N>`）、`Exactly N people` 式正向计数、至多一句具体失败词（`NO black letterbox bars`）。真要排除某物用 NegPiP 节点（`(red glow:-3)`）而不是文字。
3. **一镜一人开口、一镜一个运镜**；听者写 `listens with mouth closed`。
4. **台词预算**：硬上限 ≤ (段长−2 s)×4.5 字（校验器口径），目标语速 3.3–4 字/s，快档 ≤ 5 字/s 且连续不超 3 s；超了拆段，不要让角色说快。
5. **参考媒体一职责一张图**：脸 / 服装 / 环境 / 道具 / 音色分开；编号用脚本替换，不手写 `<Picture N>`。
6. **剧情里出现的道具必须有参考图并声明 `the exact item shown in <Picture N>`**，否则模型一定会编；等级框、UI、字幕一律后期叠。
7. **CFG 固定 1.0**；Turbo LoRA 用与分辨率匹配的版本（1344×768 用 `_768p_` 版）；SigmaShift：FL2V 768p 版视频 6 / 音频 3，Ref2V 与 544p 版 12 / 3（lightx2v 官方只对 FL2V 推荐 6）。
8. **加速只叠「无损 + 一个蒸馏」**：SageAttention（或 Sol-Attn 稠密核）+ 一个 Turbo/PDD LoRA；不叠加两个蒸馏 LoRA，不把 SageAttention 与 `MiniMaxLowVRAMAttention` 同开，不在精修档开 Spectrum / BlockSparse 等有损方案。
9. **先关掉所有加速跑一次基线**，再逐个打开，记录每段「步数 / LoRA / 分辨率 / 耗时 / 显存 / 评分」。
10. **抽卡有上限**：同一提示词 3 次同样问题 = 改提示词或分镜，不是换 seed。
11. **每段写 `end_state` 与 `continuity`**，下一段从上一段终态开场——同场景接续的段从**已采纳片段的实拍末态**开场（`observe_take.py` 写回，`continuity` 写 `"@observed"`），不是从计划的 `end_state`；跨段衔接优先「尾帧→首帧」或 latent 续接节点，不写「continue the previous video」。
12. **可复现**：任何一段都能从 `prompts/ + bible/ + project.yaml` 重生成；参数写进 `logs/takes.csv`。
13. **短剧默认硬切，不续接**：每段 5–12 s 独立 Ref2VA + 同一组参考图 + 音色锚；一条续接链 ≤ 4 段，链上关 Spectrum、不改分辨率 / LoRA / shift。
14. **段尾写 0.5 s 收束 + 1 s 定格，拼接时剪掉**；下一段同时投喂母版（角色参考 / 场景母版）与截取的末帧，首镜同档景别起手。
15. **有台词的镜头整镜只做说话**；单段说话人 ≤ 2；台词文字永不经 LLM 改写；说话重讲 / 含糊先换 seed。
16. **有运镜的镜头精修用 20 步、关 Turbo**（4 步 Turbo 几乎抹掉运镜；8 步可做草稿）；Ref2VA 只挂身份参考，背景板会让运镜减半，只在必须锁环境时挂。
17. **真人对白段先出首帧再生成**（盲评：直出 0:4 输，垫首帧 4:0 赢）；漫剧可直出。参考视频先重采到 24 fps（节点不重采样）。
18. **默认留在本地 H3，换模型要有触发条件**：同一问题按 `pitfalls.md` 改过仍连续不过，且属于 `beyond-h3.md` 路由表里的镜头类型，才换本地替补（Wan-Animate-2、Fun Camera、InfiniteTalk、Bernini-R）或云端；草稿永远先在本地确认，换出去的片段回到同一条后期链（24 fps、同一超分、ColorMatch）。
19. **后期只认一份剪辑单**：字幕文字永远取自分镜的锁定台词，识别 / 对齐只提供时间；台词质检不给识别器任何文字提示；切点、电平、配乐都改 `edit/<集>.edl.json` 后重跑，不手工拼 ffmpeg 命令；成片以 `mix_episode.py` 的验收（音画等长、帧数、响度、真峰）为准。
20. **每步落盘 + 选择卡**：会花 GPU 时间的步骤前给用户一张选择卡（推荐项放第一）——卡上的内容来自 `comfy_submit.py --dry-run` 的批次预览（哪些要跑、哪些已完成、预计多久、批次号），用户确认后带 `--confirm <批次号>` 提交，输入变了批次号就变、确认随之失效；「继续」不等于确认了一个改过的批次。产物带 seed / 参数 / 指纹，重跑幂等跳过已完成段；一集的段全部过 QC 再开下一集。

## 单段样片先行

先做 1 段「最能暴露问题」的样片（主角正脸 + 一句中文对白 + 一次有动机运镜 + 手部道具）走完 0–7，再扩到 30 s（约 3 段），再 60 s。每次重抽只改一个变量；同一错误连续两批无改善就回上层（资产 / 分镜），不再抽卡。

## 和用户沟通时

- 用户常把「画质差」归因于步数：先查是否 4 步、是否 544p LoRA 跑 768p、FL2V 768p 版是否还用 shift 12、是否没带参考图。见 `references/pitfalls.md` 的「症状→原因」表。
- 用户问「别人 5070 为什么比我 4090 快」：对比分辨率（544p vs 768p）、步数、是否 Turbo、是否 Windows CUDA 系统内存回退、是否 Sage。给出同口径基准再比。
- 给出耗时估算时注明口径：分辨率 × 时长 × 步数 × 硬件，并引用 `local-stack-and-acceleration.md` 的基准表。
- 用户在海外（无 ModelScope / 网盘）时，只给 HuggingFace / GitHub 链接；文件名以 Comfy-Org / lightx2v 的 HF 仓库为准。
- **只回答问到的范围**：问加速就给两档配置与下载清单，不要把画质流水线、生态黑名单整段搬进来；基准数字一律标注「单机实测，口径 分辨率×时长×步数」。
- **写提示词时只写参考图里真实存在的锚点**（门、灯、标志）；看不到参考图就用泛指或先问用户，不要凭想象给场景加元素。
- 不确定 ComfyUI 节点的输入口名称时，以 `references/comfyui-nodes.md`（来自核心源码）为准，不要发明 `duration` / `aspect_ratio` / `prompt_optimizer` 之类的参数。

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/validate_episode.py <ep.json> [--rhythm] [--catalog props.json]` | 分镜校验：时长、台词预算、一镜一说话人、未知资产、道具无图、空终态、已采纳但没观测末态的段；`--rhythm` 加纯算术的节奏审计（超载、各镜等长、连续三镜同景别、台词塞不进镜头、开场偏慢）。警告以 `~` 打印，不影响退出码 |
| `scripts/render_storyboard.py <ep.json> --out ep01_storyboard.md` | 把分镜 JSON 渲染成人能审的分镜表（每镜时间、景别 / 焦段、运镜、动作、表演、光线、台词与语速、声音） |
| `scripts/build_prompts.py <ep.json> --out prompts/ep01 [--only s03] [--allow-planned]` | 生成每段最终提示词 `.txt` + 媒体顺序 `.media.json` + `cues.srt`；`continuity` 为 `"@observed"` 的段从上一段实拍末态开场，尚未观测时不出这一段 |
| `scripts/observe_take.py <take.mp4> --episode ep.json --segment s02 [--write "…" --confidence high --deviation "…"]` | 出已采纳片段的观测表（首帧 / 中段 / 末帧），再把实拍末态、置信度、与计划的偏差写回分镜 |
| `scripts/comfy_submit.py <wf.api.json> --set … --batch N --out takes/ep01/s03 --tag s03 [--dry-run \| --confirm <批次号>] [--free-every 3] [--log logs/takes.csv]` | 向本地 ComfyUI 提交 API 格式工作流、上传媒体、按 seed 抽卡、下载产物。提交前**预检**（节点是否安装、模型 / LoRA 文件名是否在服务器列表里并给出最接近的名字、必填输入、H3 帧数 17k+5、宽高 32 倍数、参考图接线格式）；每个 take 按「最终工作流 + 上传文件内容」算指纹，**相同的已完成 take 自动跳过**；任务被受理就把 `prompt_id` 落盘，脚本中断后原样重跑会**接回原任务**而不是重复提交；同一目录里旧结果移到 `_prev_*` 不覆盖。轮询 ≥ 20 s |
| `scripts/qc_probe.py "takes/ep01/**/*.mp4" --episode ep.json --freeze-tail 1.0 --out qc/probe` | 技术 QC：分辨率 / 时长 / 帧率 / 音轨 / 峰值 > −1 dB / 冻结 > 1 s / 黑场 > 0.25 s（排除声明的定格尾）；**镜头数与分镜对账**（少切、多切、切点偏移）、首尾跳帧、动作量。没有分镜时用 `--expect-seconds / --expect-size / --shots 0,3.5` |
| `scripts/qc_dialogue.py --episode ep.json --targets "takes/ep01/**/*.mp4" --out qc/dialogue` | 台词质检：每句是否说了、说全、只说一次、何时说；无台词段是否擅自说话；输出首 / 末字时间与语速（需 `faster-whisper`） |
| `scripts/contact_sheet.py "takes/ep01/s03/*.mp4" --freeze-tail 1.0` | 联络表：首末帧、每个切点前后各一帧、每镜中段，帧下印秒数；Windows 直接可用 |
| `scripts/identity_gate.py --episode ep.json --targets "takes/**/*.mp4" --out qc/identity` | 真人脸身份门禁（YuNet + SFace，CPU 可跑，首次自动从 HuggingFace 下模型）：逐帧把脸指派给本段应出现的角色，报换人 / 克隆脸 / 多出的人，并先自检角色之间是否撞脸；默认只警告，`--strict` 才拦截。动漫脸检测不到，改用 `assets/judge-take-prompt.md` |
| `scripts/extract_tail_frame.py <mp4> --out tail.png --trim-freeze 1.0 [--after-cut N]` | 截末帧（duration−0.2 s）作下一段首帧 / 参考，并剪掉声明的 1 s 定格；`--after-cut N` 取第 N 个硬切后的第一帧（给反打 / 特写出同一空间的首帧） |
| `scripts/make_edl.py ep.json --selects selects/ep01 --out edit/ep01.edl.json` | 从分镜 + 中选片段生成剪辑单：每段入出帧（裁起始音节与定格尾）、锁定台词、L-cut；之后所有后期脚本都读它 |
| `scripts/retime_subtitles.py edit/ep01.edl.json --out subs/ep01 [--bilingual]` | 字幕：文字 = 锁定台词，时间 = 音频；出 `.srt` / `.ass`，并把每句起止时间写回剪辑单（需 `faster-whisper`） |
| `scripts/mix_episode.py edit/ep01.edl.json --out final/ep01.mp4 [--ass subs/ep01.ass] [--stems-out audio/ep01]` | 装配与母带：帧精确拼接、按台词区间对齐各段电平、环境声底、配乐在台词处自动压低、成片 −14 LUFS / −1.5 dBTP、可烧字幕；自动验收并写报告 |
| `scripts/export_capcut_draft.py edit/ep01.edl.json --drafts "<剪映草稿目录>" [--report … --mix …]` | 导出可在剪映 / CapCut 里继续精修的草稿（切点与自动成片逐帧一致；需 `pyJianYingDraft`） |
| `scripts/export_otio.py edit/ep01.edl.json --out edit/ep01` | 导出 `.otio` + FCP7 XML + CMX3600，给 Resolve / Premiere（需 `opentimelineio`） |
| `scripts/lint_prompt.py <prompt.txt> --seconds 10 --images 4 --audios 1` | 提示词机检：字段顺序、时码递增与 1.2 s 下限、17k+5 有效时长、`<d>` 配对、标签先定义后引用、retention 关键词、否定句、静止句、全角符号、字数 |
| `scripts/selfcheck.py [--keep work]` | 装完 skill 先跑一次（约 1 分钟、不用 GPU）：用合成素材把校验 → 提示词 → 技术 QC（切点对账）→ 联络表 → 剪辑单 → 混音母带 → 工程导出整条链走一遍，逐步报 PASS / FAIL / SKIP，并列出缺哪些可选依赖 |
| `scripts/fetch_official_guides.sh` | 拉取 MiniMax 官方提示词指南原文作对照 |
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
| `assets/genres/README.md` | 按类型选参数、风格句、镜头 / 表演 / 声音要点与示例提示词；H3 弱的类型（打斗、slapstick、大特效、真人口播）怎么绕 |
| `references/beyond-h3.md` | H3 连续不过或分镜阶段就知道做不了的镜头（打戏、指定运镜、> 15 s 长镜头、给定音频口型、局部修补、特效层）该换哪个本地模型或云端模型、怎么接回来；别的工作流里能搬进来的做法 |
| `references/ecosystem-map.md` | 「这件事 GitHub 上谁做得最好」 |
| `references/pitfalls.md` | 症状→原因→修法 |
