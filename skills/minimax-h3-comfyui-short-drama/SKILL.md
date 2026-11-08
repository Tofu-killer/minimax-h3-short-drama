---
name: minimax-h3-comfyui-short-drama
description: 用本地 ComfyUI 上的 MiniMax H3（海螺 3.0 / Hailuo 03，FL2VA / Ref2VA 开源权重）从剧本做到成片的短剧 / 漫剧 / 电影质感短片生产流程。只要用户提到 MiniMax H3、海螺、Hailuo、H3 工作流、ref2va / fl2va、Turbo LoRA、导演台、短剧分镜、角色一致性、抽卡、二采 / 超分、长视频续接、SageAttention / 稀疏注意力 / 缓存加速、ComfyUI 跑 H3 慢或爆显存，或者想让 agent 接管本地 H3 工作流批量出片——即使没说「短剧」两个字——都要先读本 skill。覆盖：环境盘点与模型文件选择、24 GB 单卡的草稿档 / 精修档加速组合、官方三段式 / 六段式提示词格式与短剧对白规则、分镜分段与角色卡 / 道具绑定、段间续接方案、768P→1080p/2K 画质流水线、QC 与拼接、GitHub 生态里每类工具该用哪个与禁忌清单。
compatibility: 本地 ComfyUI ≥ 0.37（原生 MiniMaxH3 节点），单卡 ≥ 16 GB（推荐 24 GB），系统内存 ≥ 32 GB（推荐 64 GB）。脚本仅依赖 Python 3.10+ 标准库与 ffmpeg / ffprobe。模型与 LoRA 从 HuggingFace 下载。
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
| 0 | 列出 GPU / ComfyUI 版本 / 已有模型与 LoRA / 自定义节点 / 现有工作流；用 `assets/local-inventory-checklist.md` 的清单 | `references/local-stack-and-acceleration.md` |
| 1 | 确认风格（电影质感 / 漫剧）、画幅（16:9：训练格点 1344×768 其实是 7:4，真 16:9 用 1536×864 或生成后 lanczos 到 1920×1080）、单集时长、每段时长 | `assets/style-*.md`、`references/model-and-modes.md` 分辨率格点 |
| 2 | 建角色卡（脸 / 服装 / 全身 3 图）、场景空景、道具白底图、2–15 s 干净音色；写识别短语 + 声音短语 | `references/storyboard-and-assets.md` §3 |
| 3 | 用 `assets/agent-prompts/01-outline.md` → `02-storyboard.md` 让 LLM 把剧本切成 4–15 s 段（对白段 8–12 s，动作 / 硬切镜头 5–8 s），每段 2–4 子镜头，每镜写景别 / 焦段 / 运镜 / 动作 / 表演 / 光线 / 台词 / 声音；跑 `scripts/validate_episode.py`，再用 `scripts/render_storyboard.py` 出分镜表给用户审，`03-rhythm-audit.md` 做节奏审计 | `references/storyboard-and-assets.md` §1–2 |
| 4 | `scripts/build_prompts.py` 生成每段提示词与媒体顺序；`scripts/lint_prompt.py` 机检，FAIL 不提交；本地 Ollama 改写只用于三段式，六段式手写 | `references/prompt-format.md` |
| 5 | 草稿档（Turbo 8 步 + Sage + 768P）每段 2–4 个 seed；`scripts/comfy_submit.py --batch` | `references/local-stack-and-acceleration.md`、`references/comfyui-nodes.md` |
| 6 | 中选段**同 seed** 精修：LBH latent 放大 + σ 0.45 二采（音频钉死）→ 1920×1088；小脸先修再放大；只有单镜 > 15 s 才续接 | `references/quality-pipeline.md`、`references/continuity-long-video.md` |
| 7 | `scripts/qc_probe.py` + `scripts/contact_sheet.sh` + 人眼复核；剪掉段尾 1 s 定格、裁起始音节；字幕后期烧；统一响度与铺乐；concat | `references/qc-and-assembly.md` |

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
11. **每段写 `end_state` 与 `continuity`**，下一段从上一段终态开场；跨段衔接优先「尾帧→首帧」或 latent 续接节点，不写「continue the previous video」。
12. **可复现**：任何一段都能从 `prompts/ + bible/ + project.yaml` 重生成；参数写进 `logs/takes.csv`。
13. **短剧默认硬切，不续接**：每段 5–12 s 独立 Ref2VA + 同一组参考图 + 音色锚；一条续接链 ≤ 4 段，链上关 Spectrum、不改分辨率 / LoRA / shift。
14. **段尾写 0.5 s 收束 + 1 s 定格，拼接时剪掉**；下一段同时投喂母版（角色板 / 场景母版）与截取的末帧，首镜同档景别起手。
15. **有台词的镜头整镜只做说话**；单段说话人 ≤ 2；台词文字永不经 LLM 改写；说话重讲 / 含糊先换 seed。
16. **有运镜的镜头精修用 20 步、关 Turbo**（4 步 Turbo 几乎抹掉运镜；8 步可做草稿）；Ref2VA 只挂身份参考，背景板会让运镜减半，只在必须锁环境时挂。
17. **真人对白段先出首帧再生成**（盲评：直出 0:4 输，垫首帧 4:0 赢）；漫剧可直出。参考视频先重采到 24 fps（节点不重采样）。
18. **每步落盘 + 选择卡**：会花 GPU 时间的步骤前给用户一张选择卡（推荐项放第一），产物带 seed / 参数 / 哈希，重跑幂等跳过已完成段。

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
| `scripts/validate_episode.py <ep.json> [--catalog props.json]` | 分镜校验：时长、台词预算、一镜一说话人、未知资产、道具无图、空终态 |
| `scripts/render_storyboard.py <ep.json> --out ep01_storyboard.md` | 把分镜 JSON 渲染成人能审的分镜表（每镜时间、景别 / 焦段、运镜、动作、表演、光线、台词与语速、声音） |
| `scripts/build_prompts.py <ep.json> --out prompts/ep01` | 生成每段最终提示词 `.txt` + 媒体顺序 `.media.json` + `cues.srt` |
| `scripts/comfy_submit.py <wf.api.json> --set … --batch N --poll 20 --free-every 3 --out takes/…` | 向本地 ComfyUI 提交 API 格式工作流、上传媒体、按 seed 抽卡、下载产物、写 `run.json`；轮询 ≥ 20 s，可定期 `/free` 释放显存 |
| `scripts/qc_probe.py <mp4…> --expect-seconds 10 --expect-size 1344x768 --freeze-tail 1.0` | ffprobe 技术 QC：分辨率/时长/帧率/音轨/峰值 > −1 dB/冻结 > 1 s/黑场 > 0.25 s（排除声明的 1 s 定格尾） |
| `scripts/contact_sheet.sh <mp4…>` | 4×3 联络表，供视觉 QC |
| `scripts/extract_tail_frame.py <mp4> --out tail.png --trim-freeze 1.0` | 截末帧（duration−0.2 s）作下一段首帧/参考，并剪掉声明的 1 s 定格 |
| `scripts/lint_prompt.py <prompt.txt> --seconds 10 --images 4 --audios 1` | 提示词机检：字段顺序、时码递增与 1.2 s 下限、17k+5 有效时长、`<d>` 配对、标签先定义后引用、retention 关键词、否定句、静止句、全角符号、字数 |
| `scripts/fetch_official_guides.sh` | 拉取 MiniMax 官方提示词指南原文作对照 |
| `scripts/h3lib/catalog.py build <dir> --kind prop --out props.json` | 把道具图目录化（稀有度从路径解析），供 `validate_episode.py --catalog props.json` 检查 |

## 参考文件索引

| 文件 | 何时读 |
|------|--------|
| `references/model-and-modes.md` | 第一次接触 H3；选 FL2VA / Ref2VA；24 GB 标准文件组合 |
| `references/local-stack-and-acceleration.md` | 盘点环境、选草稿/精修档加速组合、排查慢与 OOM |
| `references/comfyui-nodes.md` | 原生节点与各家导演台/续接/加速节点的参数速查 |
| `references/prompt-format.md` | 写或审任何一条提示词 |
| `references/storyboard-and-assets.md` | 切分镜、建角色卡、一致性 |
| `references/continuity-long-video.md` | 超过 15 s、段间衔接、接缝伪影 |
| `references/quality-pipeline.md` | 768P→1080p/2K、人脸修复、角色三视图、ControlNet、换人 |
| `references/camera-and-performance.md` | 写运镜句、表演、空间锚点卡、台词排播、参考媒体预处理（有实跑数据） |
| `references/lora-and-style.md` | 要不要训角色 LoRA、风格 LoRA 选型与强度、三视图 LoRA、本地提示词改写 LoRA |
| `references/qc-and-assembly.md` | 抽卡策略、QC、字幕、配乐、拼接、目录规范 |
| `references/ecosystem-map.md` | 「这件事 GitHub 上谁做得最好」 |
| `references/pitfalls.md` | 症状→原因→修法 |
