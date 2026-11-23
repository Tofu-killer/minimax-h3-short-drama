# MiniMax H3 高清短剧制作 · 深度研究

> 系统整理「别人是如何用 MiniMax H3（海螺 3.0 / Hailuo 03）做竖屏短剧的」：模型能力、官方 API、端到端工作流、提示词方法论、一致性技术、开源项目剖析、社区经验，并附一套可运行的参考实现。
>
> 调研时间 2026‑10‑30。来源覆盖 MiniMax 官方文档与开源仓库、GitHub 上 10+ 个相关项目、X / B 站 / 公众号创作者经验、十余篇评测与提示词指南，全部列于 [`docs/08-sources.md`](docs/08-sources.md)。

## 结论先行

1. **H3 把短剧的生产单位从「镜头」变成了「段落」。** 一次生成 4–15 秒、内部可切 2–4 个镜头、原生对白 + 音效 + 立体声，正反打在同一上下文里完成。外挂 TTS 和对口型工具的旧流程可以去掉。
2. **一致性 = 定妆图库 + 职责分配 + 固定识别短语。** 模型不记得上一集；每段都要带同一组参考图（≤ 9 图 + 3 视频 + 3 音频），`<Picture 1>` 只管脸、`<Picture 2>` 只管服装、`<Picture 3>` 只管环境，角色描述一字不改地逐段复用。
3. **提示词按官方结构写最稳。** 三段式 `integrated_multimodal_description / overall_soundscape / non_diegetic_music`，参考模式用六段式；台词写 `角色 (S1) says: <d>[Chinese] 台词</d>`；镜头写 `[Shot 2] At 00:05.000, the shot cuts to …`；一镜一个运镜、一镜一人开口。
4. **成本结构：768P 草稿多候选 → 选片 → 2K 重生成。** 官方 2K $0.13/秒、768P $0.08/秒、重生成 $0.05/秒、音频免费。60 秒竖屏一集约 $8–13。
5. **弱项要在分镜阶段绕开**：动作偏慢、大幅运镜与特效镜头弱、精确文字不可靠（字幕后期烧）、视频续写空间连续性一般（用尾帧→首帧衔接代替）。

## 文档

| 文档 | 内容 |
|------|------|
| [01 模型总览](docs/01-model-overview.md) | 规格、变体（H3 / Highspeed / Lite / Max）、架构、定价、与 Seedance / Kling / Veo 的位置、各来源分歧 |
| [02 API 速查](docs/02-api-reference.md) | 官方 v2 接口完整字段、四种模式组合规则、媒体限制、示例、错误码、回调、Context‑IR、2K 重生成 |
| [03 端到端工作流](docs/03-production-workflow.md) | **核心**：剧本 → 资产 → 定妆图 → 分镜段落 → 首帧 → 提示词 → 批量生成 → QC → 拼接 → 交付，三条路线对比，失败对策 |
| [04 提示词工程](docs/04-prompt-engineering.md) | 官方三段式/六段式、标签体系、时间码、运镜词表、对白/旁白/跨镜头台词语法、短剧完整示例 |
| [05 一致性技术](docs/05-consistency.md) | 片段内 / 片段间 / 集间三层一致性，参考图规范，文字锁定，职责分配，衔接技术，声音一致性 |
| [06 开源项目剖析](docs/06-case-studies.md) | 火宝短剧、Hailuo‑AI‑Short‑Drama‑Studio、MiniMax‑H3‑Codex‑Drama、官方 skills、ComfyUI 生态、提示词生成器 |
| [07 社区经验](docs/07-community-insights.md) | X、B 站四个教程、公众号、英文评测的共识与弱点清单、平台差异 |
| [08 来源清单](docs/08-sources.md) | 全部阅读过的 URL |
| [10 B 站课程与「秋叶教程」笔记](docs/10-bilibili-h3-course-notes.md) | 辨析「秋叶」H3 课程的来源，提炼课程大纲，梳理导演台 / Multishot / 双采 / 去油 / 乱念台词等本地短剧生态的关键技术点 |
| [12 公开工作流盘点](docs/12-public-workflows.md) | 官方 10 个原生模板、导演台、lightx2v、Multishot 逐节点参数；按用途推荐；JSON 已收进 `workflows/` |
| [11 加速方案](docs/11-acceleration.md) | Turbo LoRA 版本、步数、shift、强度建议，画质代价与规避，其他加速手段叠加原则 |
| [09 Toonflow 剖析](docs/09-toonflow-analysis.md) | 20k star 开源短剧平台的架构、13 步 skill、H3 供应商协议、ComfyUI 接入方式、MCP 接管路线，以及与本仓库的组合建议 |
| [13 GitHub 全量调研](docs/13-github-survey/00-catalog.md) | 1750+ 个 H3 相关仓库目录 + 7 簇源码级精读（导演台、续接、加速、提示词工具、agent skill、画质、LoRA），每簇附可写进 skill 的规则 |
| [14 现有 AI 视频工作流调研](docs/14-ai-video-workflows/00-synthesis.md) | 走出 H3：开源视频模型的 ComfyUI 工作流、端到端流水线与 agent、商业模型与创作者做法、配音 / 口型 / 后期、一致性与分镜生图五份报告 + 综合篇（通用方法论、各模型分工表、对 skill 的改动与未做项） |

## 可安装 Skill（GitHub 全量调研的沉淀）

[`skills/minimax-h3-comfyui-short-drama/`](skills/minimax-h3-comfyui-short-drama/SKILL.md)：给 Claude Code / Codex / OpenCode 等 agent 安装后，它就知道如何在本地 ComfyUI 上用 H3 从剧本做到成片——环境盘点、24 GB 草稿档 / 精修档加速组合、官方格式提示词与短剧对白规则、分镜与角色卡、段间续接、768P→1080p 画质流水线、QC 与拼接、生态地图与禁忌清单，附校验 / 构建 / 提交 / QC 脚本与 eval 用例。2026-11 起还包括：生图阶段（定妆照 → 单视图参考 → 场景 / 道具 → 逐镜首帧）、13 个类型包、脚本化 QC（镜头数与分镜对账、逐句台词质检、真人脸身份门禁、带时间戳的联络表）、一份剪辑单走到底的后期（字幕对时、帧精确拼接与混音母带、导出剪映草稿 / OTIO），以及 H3 做不了的镜头该换哪个本地或云端模型。

```bash
npx skills add https://github.com/Tofu-killer/minimax-h3-short-drama --skill minimax-h3-comfyui-short-drama
```

调研底稿：[`docs/13-github-survey/`](docs/13-github-survey/00-catalog.md)——1924 个 GitHub 仓库枚举 → 1750+ 相关 → 7 簇 ~170 个仓库源码级精读 + 2 轮长尾扫描（~300 个）。评测：5 个用例「带 skill / 不带」对照，23/24 vs 6/24（[`skills/.../evals/results/`](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-1-benchmark.md)）。之后做过三轮独立可用性测试（一个没有上下文的 agent 只凭 skill 文档完成任务并报告每处卡点）：[后期链路](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-4-post-chain-usability.md)、[创作链路 + 对照官方原文复核](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-5-authoring-chain-usability.md)、[创作链路复测](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-6-authoring-chain-retest.md)、一次[全量一致性审计](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-7-consistency-audit.md)、一次[端到端测试](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-8-end-to-end.md)、一次[装机与生图规划测试](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-9-setup-and-planning.md)（按 Windows + 4090、只能走 HuggingFace / GitHub、从零开始的条件）和它的[复测 + 真实 ComfyUI 0.37.2 验证](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-10-setup-retest-and-real-server.md)：skill 现在附带 13 个 API 格式的工作流（`assets/workflows/`），从 0.37.2 自带的官方模板导出再改成本流程的设置，全部通过了一台真实 ComfyUI 0.37.2 的校验（没有显卡，没有采样过）。随后又[用真实权重和真实节点把不需要底模的部分实际跑了一遍](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-11-real-weights-and-headers.md)（解码、latent 存取、放大器、参考图与关键帧的条件节点），并只读 HuggingFace 上各文件的头部核对了 LoRA 和底模对不对得上。[第三次复测](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-12-setup-retest-3.md)让测试 agent 直接对着那台真实服务器走完全程：第一批草稿「接近可以」、30 秒成片「部分可以」，并据此把流程改成「先按计划批量出、再逐段对账」。[第四次复测与微型模型](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-13-miniature-model-and-retest-4.md)：造了一套结构相同、宽度很小的随机权重 H3（文件格式与发布的一致），第一次把附带的工作流在真实 ComfyUI 上从文本编码执行到存片——草稿、20 步、`--anchor`、精修、分块精修、从存下的 latent 续接都跑通（画面是噪声，验证的是运行时接线；画质、耗时、显存仍要在 4090 上确认）；复测的结论是第一批草稿「偏向可以」，据此加了出图规划脚本 `plan_stills.py`、过期草稿与错段片段的把关、首帧段的精修工作流。[第五次测试](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-14-end-to-end-on-the-miniature-rig.md)让 agent 在那台微型模型的服务器上从装机做到 1920×1080 的成片，中途故意犯七种常见的错：第一批草稿「能」、成片「部分能」；据此让剪辑单核对放进去的是不是采纳的片段、每条片段留下当时的提示词（过期后被采纳的片段可以按原样精修）、预览尺寸的片段不能被采纳、出图清单跟着分镜走，并补了营利项目用的文生图工作流（Z-Image-Turbo；现在共 18 个工作流）。[第六次测试](skills/minimax-h3-comfyui-short-drama/evals/results/iteration-15-other-branches-and-silent-paths.md)换了一条路线（首帧段、关键帧、已有录音、营利项目），结论相同，找出四条会把错图或错片段悄悄放进成片的路：两步出的首帧不会连带过期、画布不一致的精修照样能提交、剪辑单在草稿和精修之间自己挑、背面视图排了却没接上——都改掉了（图片按输入图的内容追踪依赖；从保留的 latent 精修时画布和帧数取自草稿的记录；一段两个片段不猜；过肩镜头接背面视图），另加了一个只读的环境体检脚本 `check_setup.py`。

给本地 agent 的提示词在 [`prompts/`](prompts/)：推荐直接发 [`05-use-the-skill.md`](prompts/05-use-the-skill.md)（安装 skill 并按流程接管）；`01` 盘点环境、`02` 接管现有工作流、`03` 迭代手册、`04` 新项目简报。

## 参考实现与模板

```bash
git clone https://github.com/Tofu-killer/minimax-h3-short-drama.git
cd minimax-h3-short-drama
```

- [`pipeline/`](pipeline/README.md)：官方 API 异步客户端、分镜 JSON schema 与校验器、三段式/六段式提示词构建器、并发批量生成（草稿 / 成片 / 2K 重生成）、ffprobe QC + FFmpeg 拼接 + 自动字幕，附 LLM 编剧/分镜/节奏审计 Agent 的 system prompt 与 30 秒示例集。
  ```bash
  cd pipeline && pip install -r requirements.txt
  python run_episode.py examples/episode01.json --dry-run     # 不花钱，先看生成的提示词与请求体
  ```
- [`workflows/`](workflows/NOTICE.md)：可直接导入 ComfyUI 的 10 个公开 H3 工作流（官方模板 / 导演台 / lightx2v / Multishot），含来源与许可。
- [`templates/`](templates/README.md)：可直接粘贴到海螺 App / ComfyUI / API 的提示词模板（T2VA、I2VA、FL2VA、Ref2VA、对白写法、制片人简报）。

## 工作流一览

```
剧本 ──► 分集剧本(LLM) ──► 资产提取 ──► 定妆图(正面/全身/场景/道具, 整季复用)
                                            │
分镜段落(8–15s, 2–4 子镜头, 台词≤字数/4.5+2s) ◄─┘
      │
      ▼
官方提示词(六段式 Ref2VA / 三段式 I2VA) ──► [可选] H3-Context-IR 改写
      │
      ▼
批量生成 768P ×2 候选 ──► 选片 ──► 2K 重生成 ──► 技术 QC(ffprobe) + 视觉 QC(联络表)
      │
      ▼
FFmpeg 统一转码 → concat → 烧字幕 → 配乐 → 1080×1920 成片
```

## 许可

本仓库内容采用 [MIT License](LICENSE)。文档中引用的开源项目各有其许可证（火宝短剧为 CC BY‑NC‑SA 4.0 禁止商用，其余多为 MIT），复用其代码或提示词前请核对。
