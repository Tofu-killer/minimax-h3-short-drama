# 02 · 端到端 AI 视频 / 短剧流水线与 agent 框架

> 调研日期 2026‑11‑21。簇名 `pipelines`。方法：GitHub 搜索 API 跑了 90 条关键词（按 stars 各取前 50，去重后 2 643 个仓库，筛出 112 个候选），其中 **48 个浅克隆**（跳过 > 150 KB 的文件，合计 682 MB），33 个按「精读」处理（读到提示词 / schema / QC 或导出源码），其余读 README 与关键文件；商业平台（LTX Studio / Higgsfield / Flova）只读公开网页。星数、推送日期取自搜索 API 当日快照；`head=` 是克隆到的提交短哈希与提交日期。没有任何一个系统在本机实跑——凡是「自报」「未验证」都照标。
> 许可提示：下文引用的提示词原文都注明来源与许可。**MIT / Apache‑2.0 / CC BY** 的可以带署名抄进 skill；**AGPL / Elastic License 2.0 / CC BY‑NC‑SA / 无许可 / MiniMax Community License** 的只能转述其做法，不要原样搬。
> docs/09（Toonflow）与 docs/12 §9（OpenMontage）已写过，本文 §4 只补它们的新变化；docs/13 覆盖过的 H3 专用 skill（漫剧老李、infinite‑creation 等）不重复。

## 0. 本簇结论

1. **主流做法已经收敛**：`源文本 → 资产圣经（角色 / 场景 / 道具 + 参考图）→ 以「一次生成」为单位的分段分镜 → 关键帧 / 首帧 → 视频（带原生音频）→ 逐段审片 → 时间线 → 成片 / 剪辑工程`。2026 年的分歧只剩两处：状态放在哪（数据库平台 vs 纯文本 + 脚本门禁），以及谁来编排（平台内置 agent vs Claude Code / Codex 读 skill）。
2. **做得最好的不是星最多的**：流程纪律最强的是 `zenstory-ai/drama-skills`（MIT，12 skill，五份 Markdown + 118 KB 交叉校验脚本 + 确认码投产 + 剪辑单 + 六档审片分流，还带一页 H3 专章）和 `eternityspring/shuohao-skills`（Apache‑2.0，18 道脚本门的 H3 分镜 + 开场站位台账）；工程最扎实的是 `ArcReel`（AGPL，时间线 / 剪映草稿 / 审片信号 / 续跑）；QC 最深的是 `DramaClaw`（ELv2，四级草图择优 + 失败模式登记表 + 空间契约）；唯一原生跑**本地 ComfyUI + H3** 的制片台是 `benjiyaya/Calliope`（MIT，★310）。
3. **学术线给了三个可搬的点子**：ViMax 的「机位树 + 让视频模型自己切过去再收割新机位首帧」、AniMaker 的「择优要看它能不能接好下一段」（MCTS‑Gen）、ATAS 的「对照**原始剧本**而不是 AI 写的 brief 审片」。
4. 对我们最有用的 5 件事：① **实拍状态回写**——`end_state` 现在只有计划值，下一段必须从「已采纳 take 的实际末态」写起（Emily2040 clip‑contract、Toonflow、Calliope 都这么做）；② **把 QC 从文字变成脚本**——一次解码出 BLACK / FREEZE / CUT 信号 + 带时间戳的信号加密联络表 + Whisper 对台词 + 本地 VLM 按「只查事实矛盾」的 rubric 打分；③ **剪辑单（cut list）+ 组装脚本 + 工程导出**——skill 里目前没有任何组装脚本，更没有 CapCut / Premiere / DaVinci 出口；④ **确认即花 GPU 的批次协议**——预览 → 绑定指纹的确认 → 断点续跑 → 先落 prompt_id 再轮询；⑤ **开场站位台账**——每场一份结构化站位，由程序生成走位句一字不差抄进该场第一段。
5. 全簇仍然**没有**一个系统把「本地 ComfyUI 抽卡 → 自动评分择优 → 自动返工」完整开源跑通：ArcReel 的 `model_review` 恒为 null，Maestro 的 `inspect_take` 明说不证明动作与台词，DramaClaw 的 VLM 门只管草图 / 首帧，AniMaker 的 AniEval 是研究代码（无许可）。docs/13 的这条判断在走出 H3 之后依然成立。

## 1. 候选全景（112 个，按类型）

「本文处理」栏：精读 = 克隆读源码；略读 = 读 README 与关键文件；略 = 只进目录；docs/13 = 上一轮已写；索引 = 清单类仓库；模型 = 属于模型簇。许可栏「自定义」= GitHub 识别不出的自定义许可（正文里写明具体是哪种）。

**A 短剧 / 漫剧制片平台（Web / 桌面，全链路）**

| 仓库 | ★ | 许可 | 最后推送 | 一句话 | 本文处理 |
|---|---:|---|---|---|---|
| HBAI-Ltd/Toonflow-app | 22423 | MIT | 2026-11-20 | 短剧、漫剧制作工具 Toonflow：开源 AI 视频创作平台，集成剧本创作、智能分镜、角色与场景资产管理、图像生成和视频生成… | 精读·更新 |
| chatfire-AI/huobao-drama | 17782 | CC BY‑NC‑SA 4.0 | 2026-11-21 | 🎬 火宝短剧 - 基于AI的一站式短剧生成平台 《一句话生成完整短剧，从剧本到成片全自动化》  Huobao Drama - … | 精读 |
| waooAI/waoowaoo | 14959 | Elastic 2.0 | 2026-09-21 | 首家工业级全流程 AI 影视生产平台。Industry-first professional AI Agent platfor… | 精读 |
| ArcReel/ArcReel | 6694 | AGPL-3.0 | 2026-11-21 | AI Agent 驱动的开源可自部署视频工作台：将小说与剧本转为角色、场景、道具资产、分镜、视频和剪映草稿，支持跨镜头一致性、… | 精读 |
| Forget-C/Jellyfish | 7282 | Apache-2.0 | 2026-07-30 | An end-to-end production workspace for AI-generated short drama… | 精读 |
| dramaclaw/dramaclaw | 7149 | Elastic 2.0 | 2026-11-21 | A general-purpose AIGC video engine: script to finished film in… | 精读 |
| MemeCalculate/moyin-creator | 4865 | AGPL-3.0 | 2026-11-20 | AI 影视生产级工具 / 支持 Seedance 2.0 / 剧本到成片全流程批量化 / AI-powered film pr… | 精读 |
| alibaba/lumenx | 1500 | MIT | 2026-10-29 | LumenX Studio，AI 短漫剧一站式生产平台。它能够将小说文本转化为动态视频，打通了从剧本分析、角色定制、分镜绘制到… | 精读 |
| xuanyustudio/LocalMiniDrama | 2506 | MIT | 2026-11-20 | 🎬 seedance2接入  开源本地 AI 短剧 & 漫剧生成工具 —— 从故事到成片一站式完成，数据不出本机，短剧工作流管… | 精读 |
| ChrisChen667788/wind-comic | 722 | MIT | 2026-11-21 | Multi-agent AI pipeline that turns one line of text into a fini… | 精读 |
| storytold/artcraft | 41844 | Apache-2.0 | 2026-11-20 | ArtCraft is an intentional crafting engine for artists, designe… | 略 |
| yi1108/printfilm | 7208 | MIT | 2026-11-20 | PRINTFILM: AI short-video marketing and AI short-drama creation… | 略 |
| shuyu-labs/BigBanana-AI-Director | 2473 | 自定义 | 2026-11-08 | BigBanana AI Director是一个工业级一站式  AI 短剧，AI 漫剧,AI 导演平台，面向创作者，实现从灵感… | 略 |
| Stonewuu/ai-fusion-video | 1801 | MIT | 2026-11-20 | 【融光】 - 基于 Agent 的全流程AI短剧/漫剧/视频创作平台 - Java & agentscope2.0 / Age… | 略 |
| LingGuoAI/LingGuo-Drama | 1676 | 无 | 2026-08-21 | 🎬 灵果短剧AI - 基于AI的一站式短剧/漫剧生成平台 《一句话生成完整短剧/漫剧，从剧本到成片短剧/漫剧全自动化》Ling… | 略 |
| 869413421/ai-moive-studio | 1667 | Apache-2.0 | 2026-09-16 | 自然语言驱动的无限画布工作流 Agent，让 AI 视频创作第一次真正变成可编辑的工作流。   AICON 面向创作者，提供从… | 略 |
| shijue-aid/aid-studio | 1476 | MIT | 2026-11-21 |  开源AI漫剧、AI短剧、AI电影与AI漫画创作平台，支持剧本、角色场景、智能分镜、图片与视频生成、配音及成片预览，多模型接入… | 略 |
| Swayingleaves/novanova-studio | 969 | MIT | 2026-11-21 | [NovaNova Studio] 一个 Agent 驱动的集 AI图片生成、AI视频生成、无限画布、自定义模型 API 、A… | 略 |
| xhongc/ai_story | 2105 | 无 | 2026-10-13 | AI视频, AI动漫,AI 短剧,AI漫剧自动化生成工具 | 略 |
| TypeTale/TypeTale | 918 | 无 | 2026-08-21 | 字字动画 - 完全免费的AIGC视频生成软件，主要用于AI短剧，AI电影，小说推文 | 略 |
| anymouschina/TapCanvas | 728 | MIT | 2026-11-20 | 面向 AI 影视、漫剧与多模态内容生产的 Agent 原生无限画布, 主推一键成片 agent，编排可控 | docs/13 |
| looplj/reveric | 933 | AGPL-3.0 | 2026-11-21 | Agent Native 一站式 AI 小说，短剧桌面创作工作台 | docs/13 |
| basketikun/infinite-canvas | 10539 | MIT | 2026-10-25 | 面向 AI 创作的开源无限画布工作台，集成 AI 生图、参考图编辑、视频生成、Agent 智能助手、画布编排、对话创作、提示词… | 略 |
| aqm857886159/Nomi | 661 | AGPL-3.0 | 2026-11-21 | Open-source AI video workbench. Bring any model or your local C… | 略 |

**B Agent Skill 套件 / 编程 agent 驱动的制片框架**

| 仓库 | ★ | 许可 | 最后推送 | 一句话 | 本文处理 |
|---|---:|---|---|---|---|
| OpenMontageInc/OpenMontage | 82034 | AGPL-3.0 | 2026-11-16 | World's first open-source, agentic video production system. 12 … | 精读·更新 |
| openfilm/openfilm | 8788 | MIT | 2026-11-20 | The open source AI video agent: turns any coding agent into a v… | 精读 |
| zenstory-ai/drama-skills | 4588 | MIT | 2026-11-20 | AI 短剧与漫剧制作 Agent 技能包：小说改剧本、视觉设定、分镜、生图/生视频提示词与剪辑成片，适配 Claude Cod… | 精读 |
| eternityspring/shuohao-skills | 6899 | Apache-2.0 | 2026-11-09 | AI 短剧制作的 skill 集合：拆角色、排大纲、出场景与道具设定、写剧本、切分镜 / Agent skills for A… | 精读 |
| Emily2040/seedance-2.0 | 8266 | MIT | 2026-10-03 | Comprehensive production pipeline for quad-modal AI filmmaking … | 精读 |
| smixs/visual-skills | 726 | CC-BY-4.0 | 2026-11-06 | AI film director skills for agents: cinematic dramaturgy (Murch… | 精读 |
| lixiaoxiao9888-create/manju-laoli-skill | 2192 | MIT | 2026-11-19 | 漫剧老李 AIGC 创作全流程 Skill · V7.4.26 多技能套装版（Short-Drama Director Sui… | docs/13 |
| Vincentwei1021/video-shotcraft | 21897 | Apache-2.0 | 2026-11-19 | AI video skill for Claude Code & Codex — cinematic, editable pr… | 略 |
| digitalsamba/claude-code-video-toolkit | 2693 | MIT | 2026-11-20 | Make videos with Claude Code: script, AI voiceover, music, vide… | 略 |
| sarpstar/cinecode | 2829 | MIT | 2026-11-12 | Films made with code. Short films, long YouTube videos, ads, ex… | 略 |
| zhanghao123vip/ai-manju-skills | 972 | MIT | 2026-11-01 | 21 个题材的 AI 漫剧全流程 Skill：一句点子生成企划案、资产图提示词、分集剧本、分镜与视频提示词。可用于 Claud… | 略 |
| Shanyin-ai/shanyin-director-master | 646 | MIT | 2026-05-11 | 专业影视导演 Agent，基于剧本完成导演定调→节奏规划→剧本微调→分镜拆解，最终输出标准九列分镜表（xlsx）； 深度融合世… | 略 |
| kangarooking/director-skills | 304 | MIT | 2026-10-20 | 导演Skill：面向 AI 视频创作的开源 Agent Skills / Director Skills: Open-sour… | 略 |
| UnderleveledBuilder/awesome-short-drama-skills | 2672 | CC0-1.0 | 2026-11-19 | AI 短剧 · 漫剧 Skill（技能包）精选：剧本、改编、分镜、Seedance / 可灵 / MiniMax 视频提示词，… | 索引 |
| zhuyansen/awesome-claude-video-skills | 2467 | 自定义 | 2026-11-20 | Open-source skills and toolkits that let Claude Code, Codex and… | 索引 |
| Yuuhann1999/agent-storyboard | 402 | MIT | 2026-11-20 | 本地优先的 Agent 视频分镜工作台：让 Codex、Claude Code 通过 MCP 写分镜、生成图片/视频素材和配音… | 略 |
| chillzhuang/Kinema | 248 | AGPL-3.0 | 2026-11-16 | 由 Codex、Claude Code 等工具驱动 AI漫剧、AI电影、AI解说的 AI大模型 影像智能体。控制章节与分镜的多… | 略 |
| konlu/story-studio | 1208 | 自定义 | 2026-11-13 | 从选题到剪映草稿的一站式 AI 短视频内容创作 Agent Skill | 精读 |
| SwotAtmk/infinite-creation | 385 | 自定义 | 2026-11-20 | infinite-creation 是一个通过提交小说/剧本，本地ComfyUI-MiniMaxH3+Agent+Skill技… | docs/13 |

**C 学术多智能体影视生成（论文配套）**

| 仓库 | ★ | 许可 | 最后推送 | 一句话 | 本文处理 |
|---|---:|---|---|---|---|
| HKUDS/ViMax | 12983 | MIT | 2026-09-30 | "ViMax: Agentic Video Generation (Director, Screenwriter, Produ… | 精读 |
| HKUDS/VideoAgent | 2059 | MIT | 2026-07-22 | [EMNLP2026] "VideoAgent: All-in-One Agentic Framework for Video… | 略读 |
| HITsz-TMG/VideoClaw | 1915 | MIT | 2026-08-26 | 🚀 AI 全自动化视频生成员工 / Your First AIGC Coworker. Chat an Idea. Get a… | 精读 |
| HITsz-TMG/Anim-Director | 267 | 无 | 2026-01-07 | Controllable Animation Video Generation with Large Models-based… | 精读 |
| showlab/MovieAgent | 380 | 无 | 2025-03-26 | MovieAgent: Automated Movie Generation via Multi-Agent CoT Plan… | 略读 |
| ziplab/ATAS | 277 | MIT | 2026-11-03 | Any Time, Any Space: A World-State-Centric Framework for Agenti… | 精读 |
| lichao-sun/Mora | 1589 | 无 | 2024-10-10 | Mora: More like Sora for Generalist Video Generation | 略读 |
| HVision-NKU/StoryDiffusion | 6501 | Apache-2.0 | 2024-09-26 | Accepted as [NeurIPS 2024] Spotlight Presentation Paper | 略读 |
| showlab/Code2Video | 2422 | MIT | 2026-11-17 | [ICML 2026] Video generation via code | 略 |
| GVCLab/CutClaw | 1016 | 无 | 2026-04-17 | Agentic Hours-Long Video Editing via Music Synchronization | 略 |
| yihao-meng/HoloCine | 707 | 自定义 | 2025-11-26 | [CVPR 2026 Highlight] Official Implementations for Paper - Holo… | 模型 |
| KlingAIResearch/MultiShotMaster | 188 | Apache-2.0 | 2026-02-22 | CVPR 2026 / Official Implementation of "MultiShotMaster: A Cont… | 模型 |
| AILab-CVC/VideoGen-Eval | 273 | MIT | 2025-12-16 | VideoGen-Eval: Agent-based System for Video Generation Evaluati… | 略 |
| neopen/story-shot-agent | 243 | MIT | 2026-11-20 | 剧本分镜智能体（PenShot）：电影/动漫/短剧/小说→分镜片段→视频提示词。基于 LLM 通过 LangGraph+Lla… | 略 |

**D 库存素材 / 解说 / 图文类一键成片**

| 仓库 | ★ | 许可 | 最后推送 | 一句话 | 本文处理 |
|---|---:|---|---|---|---|
| harry0703/MoneyPrinterTurbo | 144903 | MIT | 2026-11-21 | 利用 AI 大模型和自动化工作流，根据主题或关键词一键生成高清短视频。Generate HD short videos fro… | 精读 |
| ATH-MaaS/Pixelle-Video | 30402 | Apache-2.0 | 2026-06-14 | 🚀 AI 全自动短视频引擎 / AI Fully Automated Short Video Engine | 精读 |
| linyqh/NarratoAI | 11898 | MIT | 2026-10-24 | 利用 AI 大模型，一键解说并剪辑视频 | 精读 |
| FujiwaraChoki/MoneyPrinter | 14230 | MIT | 2026-03-26 | Automate Creation of YouTube Shorts using MoviePy. | 略读 |
| alecm20/story-flicks | 2555 | 无 | 2025-03-12 | 使用AI大模型，一键生成高清故事短视频。Generate high-definition story short videos… | 略读 |
| RayVentura/ShortGPT | 8189 | MIT | 2025-02-10 | 🚀🎬 ShortGPT - Experimental AI framework for youtube shorts / ti… | 略 |
| YILS-LIN/short-video-factory | 6239 | AGPL-3.0 | 2026-11-20 | 一键生成产品营销与泛内容短视频，AI批量自动剪辑，高颜值跨平台桌面端工具 One click generation of pr… | 略 |
| zhouxiaoka/autoclip | 12508 | MIT | 2026-11-21 | AutoClip｜一个链接，一键出片。开源 AI 视频剪辑桌面工具，将播客、访谈、课程等长视频自动剪成短视频，生成字幕、封面和… | 略 |
| NarratorAI-Studio/narrator-ai-cli-skill | 3314 | MIT | 2026-07-05 | AI 解说大师 — Agent skill；封装 narrator-ai-cli 供 Claude/Codex 等工具调用 | 略 |
| zenstory-ai/video-recap-skills | 648 | MIT | 2026-11-20 | AI 视频解说 Agent 技能包：自动切镜、看画面写解说词、配音混音合成成片，可导出剪映/CapCut 草稿，无需 GPU … | 略 |
| rushindrasinha/youtube-shorts-pipeline | 2400 | MIT | 2026-06-09 | Automated YouTube Shorts pipeline: news → script → AI visuals →… | 略 |

**E 拉片 / 复刻 / 参考驱动**

| 仓库 | ★ | 许可 | 最后推送 | 一句话 | 本文处理 |
|---|---:|---|---|---|---|
| JuneYaooo/rea-video | 11555 | Apache-2.0 | 2026-11-21 | Reverse-engineer any video, shot by shot: filmed, AI-generated … | 精读 |
| hypit-ai/hypit | 30919 | 改版 Apache‑2.0 | 2026-11-20 | Clone any viral video with AI agents. Not just a script, the wh… | 略读 |
| edenfunf/reelmimic | 2091 | MIT | 2026-11-20 | Open-source AI video style cloning for 2D animation. Give it a … | 略 |
| bkingfilm/lapian-notes | 814 | MIT | 2026-10-26 | AI 辅助的电影拉片工具：AI 拆出剧情泳道时间轴、结构树、情绪曲线，边播边写拉片笔记，免费开源全本地 / AI-assist… | 略 |
| JuneYaooo/rea-toon | 292 | 自定义 | 2026-11-18 | AI 拆解学习短剧：为什么火、剧本怎么写、每一镜怎么拍 / Break down any short drama with A… | 略 |

**F 剪辑 agent / 时间线 / 工程导出**

| 仓库 | ★ | 许可 | 最后推送 | 一句话 | 本文处理 |
|---|---:|---|---|---|---|
| browser-use/video-use | 31387 | MIT | 2026-10-08 | Edit videos with coding agents | 精读 |
| kajisho5/ffmpeg-skill | 9073 | MIT | 2026-11-21 | Local video editor for coding agents: 42 FFmpeg tools with a ma… | 精读 |
| GuanYixuan/pyJianYingDraft | 4958 | Apache-2.0 | 2026-10-14 | 轻量、灵活、易上手的Python剪映草稿生成及导出工具，构建全自动化视频剪辑/混剪流水线。本项目的CapCut版本正于 htt… | 精读 |
| GuanYixuan/pyCapCut | 779 | 无 | 2026-10-16 | A lightweight, flexible, and easy-to-use Python tool for genera… | 略读 |
| Hommy-master/capcut-mate | 2191 | Apache-2.0 | 2026-11-21 | 开源剪映小助手｜剪映API / 扣子插件 / Open-source CapCut automation toolkit to… | 略读 |
| FireRedTeam/FireRed-OpenStoryline | 3723 | Apache-2.0 | 2026-07-31 | FireRed-OpenStoryline is an AI video editing agent that transfo… | 略读 |
| appariciojunior/video-editor-skills | 468 | 自定义 | 2026-10-23 | Skills that teach Claude Code to be a first-pass video editor i… | 精读 |
| renezander030/capcut-cli | 1246 | MIT | 2026-11-19 | Independent, unofficial CLI to edit CapCut and JianYing (剪映) pr… | 略 |
| diffusionstudio/editor | 3543 | MPL-2.0 | 2026-10-18 | The VS Code of video editing, built for agents. | 略 |
| 0xsline/OpenChatCut | 3249 | AGPL-3.0 | 2026-11-12 | Open-source, local-first conversational AI video editor with a … | 略 |
| JimLiu/baocut | 1796 | 自定义 | 2026-11-19 | BaoCut: an AI video agent with an editable timeline. Transcribe… | 略 |
| ronak-create/FableCut | 805 | MIT | 2026-11-21 | Zero-dependency browser video editor that AI agents can drive —… | 略 |
| veedstudio/open-edit | 1843 | Apache-2.0 | 2026-11-11 | Open-source, agent-driven editing pipeline: create subtitles, m… | 略 |
| Agentchengfeng/chengfeng-videocut-skills | 3251 | Apache-2.0 | 2026-10-10 | 用 Claude Code Skills 做的视频剪辑 Agent | 略 |
| nexu-io/openmotion | 14403 | Apache-2.0 | 2026-11-21 | The open-source Claude Motion & CapCut alternative. Turn a refe… | 略 |

**G 翻译配音 / 本地化（后期参考）**

| 仓库 | ★ | 许可 | 最后推送 | 一句话 | 本文处理 |
|---|---:|---|---|---|---|
| Huanshere/VideoLingo | 19339 | Apache-2.0 | 2026-11-13 | Netflix-level subtitle cutting, translation, alignment, and eve… | 略读 |
| krillinai/OpenCreator | 14455 | Apache-2.0 | 2026-11-20 | Formerly KrillinAI, VideoTranslation and Dubbing Tool for 120+ … | 略 |
| liuzhao1225/YouDub-Desktop | 5873 | Apache-2.0 | 2026-11-21 | Open-source AI video localization and dubbing for YouTube/Bilib… | 略 |

**H ComfyUI agent / MCP / 本地制片台**

| 仓库 | ★ | 许可 | 最后推送 | 一句话 | 本文处理 |
|---|---:|---|---|---|---|
| Comfy-Org/comfy-mcp | 364 | AGPL‑3.0+ / 商业 | 2026-11-21 | Local MCP server for ComfyUI — run your local ComfyUI from AI a… | 精读 |
| artokun/comfyui-mcp | 944 | MIT | 2026-11-19 | Local-first, agent-native control plane for ComfyUI — MCP serve… | 精读 |
| benjiyaya/Calliope | 310 | MIT | 2026-11-15 | Local-first Agentic Idea-to-video Studio Using ComfyUI + FastAP… | 精读 |
| Blizaine/Maestro | 990 | WanGP 非商用 | 2026-11-10 | An all-in-one, 100% local AI video, image, and music studio. Di… | 精读 |
| ATH-MaaS/ComfyUI-Copilot | 5587 | MIT | 2026-09-11 | An AI-powered custom node for ComfyUI designed to enhance workf… | 略读 |
| ATH-MaaS/Pixelle-MCP | 1131 | MIT | 2025-12-17 | An Open-Source Multimodal AIGC Solution based on ComfyUI + MCP … | 略读 |
| joenorton/comfyui-mcp-server | 412 | Apache-2.0 | 2026-02-17 | lightweight Python-based MCP (Model Context Protocol) server fo… | 略读 |
| ConstantineB6/comfy-pilot | 232 | MIT | 2026-02-16 | MCP server + embedded terminal that lets Claude Code see and ed… | 略读 |
| heshengtao/comfyui_LLM_party | 2393 | AGPL-3.0 | 2026-07-29 | LLM Agent Framework in ComfyUI includes MCP sever, Omost,GPT-so… | 略 |
| rookiestar28/ComfyUI-OpenClaw | 560 | MIT | 2026-11-01 | Your own personal AIGC Factory. Any picture. Any reel. The Comf… | 略 |
| HuangYuChuh/ComfyUI_Skills_OpenClaw | 423 | MIT | 2026-08-26 | Agent-friendly ComfyUI workflow skills for OpenClaw, Hermes Age… | 略 |
| Comfy-Org/comfy-skills | 264 | MIT | 2026-11-11 | Comfy Cloud product skills: slash commands for generating image… | 略 |
| tin2tin/Pallaidium | 1559 | GPL-3.0 | 2026-11-18 | PALLAIDIUM — a generative AI movie studio, seamlessly integrate… | 略 |
| PurpleDoubleD/locally-uncensored | 4527 | AGPL-3.0 | 2026-11-19 | The all-in-one local AI studio for your desktop: chat, image an… | 略 |
| hulutech-web/novel-video-workflow | 347 | 无 | 2026-04-12 | 完全本地的AI小说视频生成工作流，每个人都能成为导演！ | 略 |

**I n8n / Dify / Coze 工作流模板**

| 仓库 | ★ | 许可 | 最后推送 | 一句话 | 本文处理 |
|---|---:|---|---|---|---|
| lucaswalter/n8n-ai-automations | 1696 | 无 | 2026-03-02 | Collection of n8n workflows, n8n templates, AI automations, and… | 略读 |
| poptechstudio/ai-cinema-studio-engine | 18 | MIT | 2026-04-13 | Self-hosted AI cinema engine. 5-layer production pipeline with … | 略读 |
| svcvit/Awesome-Dify-Workflow | 10802 | MIT | 2026-03-25 | 分享一些好用的 Dify DSL 工作流程，自用、学习两相宜。 Sharing some Dify workflows. | 索引 |
| tianfeng66/coze-anime-biography-workflow | 14 | 无 | 2026-09-28 | 扣子动漫人物传记视频工作流：分镜、参考图、逐镜头视频、中文旁白、字幕与拼接 | 略读 |
| ayuegm/coze-hot | 34 | MIT | 2026-02-02 | 100多个爆款Coze 工作流合集｜抖音｜爆款短视频生成｜自动化视频内容创作 | 索引 |
| Narrator-AI/Narrator-AI-Master-Coze | 439 | 自定义 | 2026-07-06 | NarratorAI — Coze 版影视与短剧解说生成应用 | 略 |


## 2. 工作流图谱

六条有代表性的完整链路。每步写「输入 → 工具 / 模型 / 关键参数 → 产物」，括号里是出处。

### 链路 A · 平台型「资产库 + 段落生成」（火宝 / ArcReel / Toonflow / DramaClaw 的公约数）

```
小说或剧本
 → [剧本改写 agent] 逐集剧本，节拍边界【开场/触发/高潮/收尾】强制切段
 → [资产提取 agent] characters / scenes / props（Jellyfish 再加 entity_merger 合别名、variant_analyzer 出服装时间线）
 → [提示词 agent + 生图] 角色三视图 · 场景「固定视角 + 前中后景、无人」· 道具白底单品   （火宝 final-prompt.ts）
 → [分镜 agent] 段落 = 一次生成，8–15 s，2–4 子镜头，不跨场；段数 ≈ 字数÷500字/分÷12 s ±20%；段长 ≥ 台词字数÷4.5 + 2 s
 → [视频提示词] 第一行信息头「出场人物：@A、@B；场景：@S。」+ 每 3 s 一行「0-3秒：…」，@名字 → 参考图槽位
 → [视频适配器] MiniMax H3 v2（content[] ≤ 9 图 / 3 视频 / 3 音频 / 总 12，prompt ≤ 7000 字符）或 Seedance / Wan
 → [审片] ArcReel：inspect_video_units 出带 CUT/BLACK/FREEZE 标签的联络表给 agent 看；DramaClaw：只对草图 / 首帧做 VLM 门
 → [时间线] ArcReel EditClip{unit_id, trim{in_us,out_us}, hold_us, transition_to_next} + BgmClip{volume 0.25, fade 1 s}
 → 成片（ffmpeg，帧边界按累计时长取整）或 剪映草稿 zip（pyJianYingDraft，素材路径占位符下载时代入）
```
人审停点：剧本规划确认（ArcReel 用内容指纹，上游一改自动回到待确认）、资产图、分镜、视频采用。火宝无 QC，Toonflow 无拼接，ArcReel 两头都有。

### 链路 B · 编程 agent + 纯文本项目（zenstory drama‑skills；shuohao‑skills 同构）

```
原著 / 点子
 → $short-drama-novel-analyze → $develop（分集大纲）→ $write（剧本.md：场头、动作、逐字台词、[VO]/[OS]、[画面文字]）
 → $assets（视觉设定.md：人物 / 造型 / 地点 / 道具 / 声线 + 连戏锁 LOCK-… · 锁定词 + 本集状态净变化）
 → $image-prompts（图片提示词.md：IMG-…）‖ $storyboard（分镜.md：SHOT-…，出场设定、起止画面、首帧提示词）
 → $video-prompts（视频提示词.md：MOTION-… / GROUP-… 多镜合生；按目标模型方言写，H3 = 三段式或六段式）
 → creator_markdown_check.py 交叉校验（时长不一致、出场设定漏人、锁定词缺失……直接报镜号与修法）
 → $produce：prepare-batch（预览条数 / 模型 / 时长 / 输出路径）→ 人回 CONFIRM BATCH <id> <code> → run-batch（--batch-id 续跑）
      内置 provider：GPT Image 2 · Seedance · MiniMax H3（云 API）· MiniMax Speech / music-3.0
 → $edit：剪辑单.md（CUT-…：来源 / 入点 / 出点 / 取舍理由 / 字幕逐字 / 音效 / 环境声）→ edit_tool.py check → render → verify
 → $review：六档分流（保留 / 裁切避让 / 后期修补 / 建议重抽 / 必须重生成 / 剪辑补回）→ PASS / PROVISIONAL / REVISE / REJECT
```
shuohao 的差别：状态是 5 份 JSON（outline / cast / art / script / storyboard）+ 一份 staging.json，每份都有 `seed → 模型填空 → validate（脚本门）→ render（HTML 报告）` 四步；分镜是「段 ≤ 15 s → 切 2–5 s → 每切一张分镜图」，H3 多图对齐首行由秒数推导并逐字对账。

### 链路 C · 学术多智能体「机位树 + 多候选择优」（ViMax；AniMaker 的前瞻版）

```
idea / script / novel
 → [Screenwriter / ScriptPlanner] project_brief → characters（static_features / dynamic_features）→ script
 → [StoryboardArtist] shots：cam_idx · visual_desc · variation_type(large|medium|small) · ff_desc · lf_desc · motion_desc · audio_desc
 → [CameraImageGenerator.construct_camera_tree] 同场机位建树：父机位画面包含子机位（全→中→近，正反打可互为父子）
 → 根机位首帧：角色肖像 + 文本 → 图像模型出 N 张 → [BestImageSelector] VLM 按 角色一致 > 空间一致 > 描述准确 选 1 张
 → 子机位首帧：用**视频模型**生成 "Two shots. The transition between the shots is a cut to." + 父镜首帧
      → PySceneDetect 切开 → 取第二镜第一帧 = 同一空间的新机位图
 → 每个目标帧：[ReferenceImageSelector] 从「肖像（正/侧/背只取一张）+ 之前各帧」选 ≤ 8 张，优先同机位、时间近
 → 视频模型（Veo / Seedance）首帧或首尾帧生成 → 拼接
```
AniMaker 把「选哪条 take」改成树搜索：每个 clip 出 3 条候选打分，再用最好候选的末帧去**预生成下一 clip**，按「本段分 + 下一段分」选路径，预生成的子候选下一步直接复用。

### 链路 D · 本地 ComfyUI 制片台（Calliope，原生 H3）

```
一句话故事
 → [Story agent] 节拍 / 角色 / 地点 → [Assets] 每实体一条图片提示词 → ComfyUI 文生图工作流出参考图
 → [Script agent] 逐场剧本（动作全文 + 逐字对白）→ Break into shots：每 clip 约 5–10 s
 → 工作流登记：导出 API 格式 JSON，节点标题打角色标签 (Input:prompt) (Input:character) (Input:location) (Input:latent) (Output:video)
 → 提示词：profile = MiniMax H3 reference (6-section) 时由场景数据**确定性编译**六段式，生成前必过预览（可内联改 / 存草稿）
 → 提交：POST /upload/image → 改 JSON → POST /prompt → 轮询 /history/{prompt_id}（超时默认 1800 s）→ 下载
 → 续接：上一 clip 的 AV latent 存 calliope/p<项目>_c<clip> → 下一 clip 的 Load Latent 钉在开头（Motion-Context 包）
      续接提示词 8 条：时间戳整体 +0.92 s（钉头 22 帧会被裁掉）、前 2 s 不进新东西、每段以动作进行中收尾……
 → 连续性台账：整片一份 JSON（九条锁定 requirements + 每 clip state_after）；已有成片的 clip 标 REALIZED；critic 逐条提示词对账
 → Export film：ffmpeg 统一 1080p、取多数 clip 的帧率、0.5 s 交叉淡化（续接处硬切）、响度归一
```

### 链路 E · 库存素材 / 解说 / 图文流（MoneyPrinterTurbo · Pixelle‑Video · NarratoAI）

```
主题 → LLM 脚本 → 搜索词 → TTS（Edge TTS 免费 / IndexTTS-2 克隆）→ 字幕（TTS 时间戳或 Whisper）
     → 素材：Pexels / Pixabay 库存，或逐句 AI 配图 / AI 视频（Pixelle 走本地 ComfyUI：image_qwen.json、video_wan2.1_fusionx.json）
     → 音频定时长，素材循环或裁剪去配 → 字幕 + BGM → 成片 → 发布
NarratoAI 反过来：原片抽帧 → VLM 逐帧理解 → 解说词 → TTS → 按脚本剪原片 → 可导出剪映草稿
```
与对白短剧的根本区别：**音频先行**，画面只是配音的插图，没有跨镜身份 / 空间一致性问题，也没有口型问题——这是它能做到 14 万星「一键成片」的原因，也是它不能直接拿来做短剧的原因。

### 链路 F · 剪辑与交付（video‑use → ffmpeg；ArcReel / story‑studio → 剪映；OpenFilm → Premiere / DaVinci）

```
若干 take
 → ffprobe 全量探测 → 逐词 ASR（缓存）→ takes_packed.md（短语级，静音 ≥ 0.5 s 断行）              （video-use）
 → 选区：edl.json ranges[{source, start, end, beat, quote, reason}]；切点吸附词边界，pad 30–200 ms
 → 逐段抽取 + 调色 + 每个边界 30 ms afade → -c copy concat → 叠加层 → 字幕最后烧
 → 自检：对渲染结果每个切点 ±1.5 s 出胶片条 + 波形图；ebur128 实测响度与真峰；最多 3 轮，再不行上报
 → 出口三选：
     a) 成片 mp4（−14 LUFS / −1 dBTP）
     b) 剪映 / CapCut 草稿：pyJianYingDraft（剪映 5.9 与 10.8）或 pyCapCut（CapCut 8.2 / 9.5）；素材拷进草稿并按内容哈希命名
     c) xmeml v4（Final Cut Pro 7 XML）→ Premiere「文件 › 导入」、DaVinci「File › Import › Timeline」免插件；FCPXML 1.10 → Final Cut
```

## 3. 七个重点问题的横向答案

### 3.1 阶段划分与每阶段的输入输出

| 系统 | 阶段序列 | 状态载体 | 生成单位 | 值得抄的 schema |
|---|---|---|---|---|
| 火宝短剧 | 剧本改写 → 资产提取 → 生图 → 分镜拆解 → 生视频 → concat | SQLite（Drizzle） | 段落 8–15 s / 2–4 子镜头 | storyboard{description【镜头N】, atmosphere, video_prompt, character_ids, prop_ids, scene_id, duration} |
| ArcReel | project_input → episode_plan → script_plan_content → **script_plan_review** → final_script → asset_sheets → script_structure →（storyboard）→ video → edit（`workflow_rules.py`，"order is presentational only"） | 项目文件 + DB，MCP 是唯一真相 | 视频单元 | EditTimelineDocument（见 3.5）、视频信号侧车 JSON |
| Toonflow v2.7 skill | A0 输入判定 → A2 全量节拍 → A3 分段预算 → A4 资产与出镜状态 → A5 站位 → A6 表演 → A7 运镜衔接 → A8 跨段连续性 → A9 提示词 → A11 结构校验 → A12 抛光 | 画布 JSON + `productionState.md` | 片段 ≤ 15 s | 状态四表：成果 / 生成尝试 / 片段采用 / 交付 |
| zenstory drama‑skills | 原著分析 → 分集剧本 → 视觉设定 → 图片提示词 ‖ 分镜 → 视频提示词 → 确认后生产 → 剪辑 → 审查 | 5 份 Markdown + 剪辑单.md | SHOT / MOTION / GROUP（多镜合生） | 连戏锁、CUT 段、任务单 job.json、确认回执 |
| shuohao‑skills | outline → characters ↔ art ↔ script → **staging** → storyboard → 投产包 | 6 份 JSON，每份自带 validate | 段 ≤ 15 s → 切 2–5 s → 分镜图 | 节拍认领 `beats:[起,止]`、构图六字段、staging places |
| ViMax | brief → characters → script → storyboard → shot_decomposition → **camera_tree** → frame_prompts → keyframes → video_clips → final | `.working_dir/<session>/` | shot | cam_idx、variation_type、ff/lf_desc、vis_char_idxs |
| Emily2040 seedance‑2.0 | story → scenes（重锚单位）→ beats → clips（一次只编译下一条未决 clip） | project‑state JSON（5 个 schema） | clip | clip‑contract、take‑review（见 3.3） |
| OpenMontage | research → proposal → script → scene_plan → assets → edit → compose → publish | `projects/<id>/` JSON 工件 + checkpoint | scene | checkpoint / review / final_review / cost_log |
| DramaClaw | 长篇 → cognee 图谱 → 分集规划（审 / 修）→ identity → 剧本 → beat → 草图（四级择优）→ 首帧（VLM 门）→ 视频 → 配音 → 剪辑 | SQLite + 内容寻址 artifacts/ | beat | 失败模式登记、空间契约、trace |
| Calliope | Story → Assets → Script → Video → Film | SQLite + 媒体目录 | clip 约 5–10 s | 连续性台账（overview / 9 requirements / shots.state_after） |

三点共识：（a）**生成单位 = 一次模型调用**，镜头是它内部的东西（火宝、shuohao、Toonflow、zenstory GROUP、Seedance / H3 的多镜头能力都指向这里——与我们「生产单位是段」一致）；（b）**先整片时间线，再装段**（waoowaoo："Segment 是执行容器，不是剧情节拍"，分段数最少优先）；（c）**计划与实拍分两套字段**（Emily2040 `planned_*` / `observed_*`，Toonflow「不用计划末态冒充实际末态」）。

### 3.2 agent 编排方式

| 形态 | 代表 | 怎么分工 | 人审停点 | 续跑 | 成本 |
|---|---|---|---|---|---|
| 单 agent + skills + 确定性脚本 | zenstory、shuohao、Emily2040、video‑use、OpenFilm | 模型只做「填空 / 取舍」，结构事实由 `seed` 脚本确定性展开，产出必须过 `validate` 脚本门 | 写在 skill 里：生产前确认码（zenstory）、Intent echo（Emily2040）、策略确认（video‑use） | 文件即状态；`run-batch --batch-id` 跳过同指纹已成功项 | prepare‑batch 预览条数与参数；「按集拆批」 |
| 服务端状态机 + 薄 agent | ArcReel、VideoClaw、waoowaoo | agent 每步问服务端 `get_workflow_plan`，按 `next_action` 走；"不要自行维护另一份模式到步骤映射表" | 服务端强制：`blockers`、`status.operations = admitted / refused`、确认指纹 | 持久化 provider job；重启自愈「不能确认可接续就标失败，绝不重提」 | ArcReel 生成前费用预估；waoowaoo PlanSnapshot → quote → grant |
| 多 agent 角色分工 | 火宝（4 个 Mastra agent）、Jellyfish（12 个 LangChain agent）、wind‑comic（8 角色）、Calliope（6 角色，各配 LLM）、ViMax（13 个 agent 类） | 每个角色只拿自己的工具（Calliope「scoped studio calls」）；火宝硬约束「输出只允许工具调用」 | 每阶段确认（VideoClaw 7 个停点） | 各自实现 | wind‑comic 按阶段归因 + ok / warn / over 预算守卫 |
| 声明式流水线清单 | OpenMontage `pipeline_defs/*.yaml` | 每阶段声明 `checkpoint_required` / `human_approval_default` / `review_focus` / `success_criteria` | `checkpoint_policy: guided / manual_all / auto_noncreative` | checkpoint.schema.json | `budget_default_usd: 2.00`、cost_snapshot |
| 学术式对抗 / 搜索 | FilmAgent（导演–编剧–演员–摄影互评）、AniMaker（MCTS‑Gen + Reviewer）、ATAS（生成 → 重建 → 配准 → 校验才入库） | 评审 agent 与生成 agent 分离 | 无（追求零人工） | ATAS：已采纳观测不可变 | ATAS / Maestro：有界修复预算 |

可迁移的四条纪律：**确认绑定内容指纹**（ArcReel 确认指纹、zenstory 确认码、Toonflow 历史快照——上游一改确认自动失效，「继续」「预算够用」不算确认）；**计划先于副作用**（waoowaoo BA‑02、ffmpeg‑skill `--plan`）；**受理结果未知时禁止重提**（waoowaoo FG‑03、ArcReel、zenstory `collect`、Maestro「never create a new ID to repeat uncertain work」）；**看过才算看过**（ViMax "Base visual claims on the returned pixels"、Toonflow「文件存在或静帧都不证明 Agent 看过」、ffmpeg‑skill 报告必须带 `Look:` 行）。

### 3.3 一致性机制

| 层 | 做法 | 出处 |
|---|---|---|
| 文本身份锚 | 6 层锚点：骨相 / 五官 / **辨识标记（必填 2–3 个，精确到位置）** / Hex 色彩锚（虹膜·发·肤·唇）/ 皮肤纹理 / 发型发际线 | moyin‑creator `CharacterIdentityAnchors` |
|  | 连戏锁：`LOCK-…《名称》· 锁定词：pine-green lapel service jacket`；未挂该外观参考图的提示词必须原字出现，脚本字面匹配 | zenstory `continuity-and-locks.md` |
| 参考图 | 正面全身锚点 → 其余视图（头像 / 90° 侧 / 背 / 细节）**只参考锚点**；逐图可重生成并跟踪过期 | shuohao `character-refs` |
|  | 每个目标帧从「肖像 + 之前各帧」选 ≤ 8 张；肖像正 / 侧 / 背只取一张最合机位的；优先同机位、时间近、去冗余 | ViMax `reference_image_selector.py` |
|  | 画面描述不写外貌服装陈设——静态外观交给参考图；每个单元必须 `@` 场景资产，同地点连续单元逐条重复引用 | ArcReel `writing_syntax.md` |
|  | Style Bible Frame：先出一张全片 key art，作每张分镜图的第一个风格参考 | wind‑comic |
| 身份变体 | Identity = 角色 × 造型（同 Identity 脸与衣都锁，跨 Identity 只锁脸）；persona 字段把「小时候 / 长大 / 穿西装」三个 character 连成一个人；`@[本体/衍生]`（声音仍绑本体） | DramaClaw、LumenX、ArcReel |
| 跨段状态 | clip‑contract：`already_happened / this_clip_only / reserved_for_later` + `planned_*_state` + **`observed_*_state`** + `continuity_locks` + `allowed_changes` | Emily2040 `clip-contract.schema.json` |
|  | 只记「净变化」：变化前后 + 触发场景 + 有效范围；上集带伤未提痊愈默认延续 | zenstory CON‑01/03 |
|  | 整片连续性台账 + REALIZED 标记 + critic 对账 | Calliope `continuity.py` |
|  | 相邻段先判关系：连续关联 / 局部状态关联 / 无关联重锚——"不得为了让它连得上自行制造关联" | Toonflow A8 |
| 空间 | 开场站位台账：认图（每地点 4–20 件可站可坐的东西）+ 每人 {present, item, side, along, posture, facing} → 程序生成走位句 | shuohao `novel-staging` |
|  | 正反打空间契约：MASTER + REVERSE 两张场景参考 → 四面墙 must_preserve（≤ 8 项 / 墙，含 count / size_lock / must_not_become）+ 接缝规则 | DramaClaw `scene_spatial_contract.py` |
|  | 机位树 + 借视频模型切机位取新首帧 | ViMax `camera_image_generator.py` |
|  | 每段自包含 5 块：世界坐标 / 画面坐标 / 光源 / 道具绝对位置 / 结束状态；下一段把它重写成「绝对初始状态」 | Toonflow A5 |
|  | 3D 预演：俯视图摆人偶与机位 → 导出 control frame / 布局草图 / 走位指令；景别角度由几何推导 | DramaClaw 3D Previz、wind‑comic 导演台、Calliope Build Scene、Toonflow 3D 导演台 |
|  | 世界状态：每条成片重建几何并配准入库，回访视角从记忆渲染 | ATAS（需 20 GB 几何服务） |
| 链深度 | 续接只在场内合法；连续「吃自己输出」的生成 ≤ 2（硬顶 3），场界从母版重锚并清零 | Emily2040 `seedance-sequence` |
| 训练式 | 每角色 LoRA（MovieAgent ED‑LoRA）；Higgsfield Soul ID（每角色 20+ 张照片先训再拍） | MovieAgent、Higgsfield 博客 2026‑07‑29 |

在读到的系统里，没有任何一个 2026 年仍活跃的开源流水线把「角色 embedding / LoRA」当默认路径——主流全部是**多参考图 + 文本锁 + 状态台账**；LoRA 只出现在 2025 年初的学术代码和商业平台的付费功能里。

### 3.4 自动质检与返工

| 类别 | 具体做法（阈值） | 出处 |
|---|---|---|
| 确定性信号 | 一次解码 `setpts=PTS-STARTPTS,blackdetect=d=0.1,freezedetect=n=-60dB:d=0.5,select='gt(scene,0.4)',showinfo` → BLACK / FREEZE / CUT；按文件指纹缓存；"信号只作提示，不自动裁切或废弃" | ArcReel `lib/video_review/signals.py` |
|  | 信号驱动的联络表：每张 ≤ 12 帧、每镜头至少一帧、信号两侧加密、帧下标时刻（与时间线入出点同轴）与标签 | ArcReel `sampling.py` / `contact_sheet.py` |
|  | 成片 verify：切点两帧亮度差 > 20、切点前后 0.4 s RMS 差 > 10 dB、响度 ±1 LU、真峰 ≤ −1.5 dBTP | zenstory `editing-guide.md` |
|  | 重复构图：16×16 平均哈希相似度 ≥ 0.85 告警（同场且相邻 ≤ 2 格除外） | DramaClaw `similarity_detector.py` |
|  | 交叉校验门：18 道（shuohao 分镜）、118 KB 校验器（zenstory）；门失败累积到 `.gates.jsonl` 看「哪道门最常响」 | shuohao、zenstory |
| VLM rubric | 草图事实核查 7 类（人数 / 性别 / 核心动作 = critical），通过 = 分 ≥ 6.0 且无 critical，**"宁可通过也不要误判"**；输出 none / regenerate / edit_script | DramaClaw `SKETCH_VERIFY_PROMPT` |
|  | 一致性分维度：face = 脸 + 发 + 肤均值，clothing = 款式 + 颜色 + 配饰均值，两者 ≥ 7.0；< 5.0 critical | DramaClaw `CONSISTENCY_VERIFY_PROMPT` |
|  | 首帧质量：面部 / 肢体畸变、乱码文字 = critical；内容丢失、风格偏移、色彩异常 = warning | DramaClaw `FRAME_VERIFY_PROMPT` |
|  | 候选择优：角色一致 > 空间一致（左右不能反）> 描述准确；优先无白边黑边 | ViMax `best_image_selector.py` |
|  | 对照原始剧本审片六项：subject / framing / motion / action / event / world_consistency，critical 只给「高置信、直接可见的矛盾」 | ATAS `film_review.py` |
|  | 分镜图 < 70 自动重出；角色匹配 < 75 提高参考权重重出 | wind‑comic（README 自述） |
|  | 提示词对连续性台账查九项，只报遗漏 / 绑错主体 / 绑错说话人 / 矛盾 / 镜序冲突 | Calliope `_CRITIC_SYSTEM` |
| 学习型指标 | AniEval 14 项加权：动作完成 2.0、文本–故事一致 1.5、美学 1.0、时序语义一致 0.8、人脸一致（InceptionResnet 距离）0.5、RAFT 形变误差 0.5……另算与前后片的连续性 | AniMaker `Tools/eval.py` |
| 台词 | 字幕逐字取自剧本，ASR **只用来找时间点**；重出素材后必须重测发声区间 | zenstory EDT‑05 / EDT‑17 |
|  | 只用逐词 verbatim ASR；切点不落在词中间；ASR 时间戳漂 50–100 ms 用 pad 吸收 | video‑use 硬规则 6–8 |
| 返工决策 | 六档：保留沿用 / 裁切避让 / 后期修补 / 建议重抽（可豁免）/ 必须重生成 / 剪辑补回；结论 PASS / PROVISIONAL / REVISE / REJECT | zenstory `generated-media.md` |
|  | 先分「垫图毛病」还是「出片毛病」；探索性试拍一次改一个变量，**明确错漏同一轮一次修完**；原样重抽 1–2 次仍同一硬伤就改词或拆镜；再不行三条出路（藏拙 / 信息挪邻镜 / 删镜并转移剧情信息） | 同上 |
|  | take 判定 accept / accept_with_deviation / repair / reject；偏差被采纳就改后续计划而不是假装没发生 | Emily2040 `take-review.schema.json` |
|  | 局部重拍：8 s 里只重出坏掉的 2 s，精确帧拼回，整段只重编码一次（crf 17），时长不变 | wind‑comic Segment retake；LTX Studio Retake |
|  | 前瞻择优：3 候选 + 3 轮 UCT，用末帧预生成下一段，按「本段 + 下一段」配对分选路 | AniMaker MCTS‑Gen |
|  | 有界预算：自检最多 3 轮（video‑use）；每步最多 3 次（LocalMiniDrama）；polish budget 先扣后发（Maestro）；RepairExhausted（ATAS） | 各自 |
|  | 失败模式登记表：code / 是非问句 / prevention_rule / 正负向子句 / 命中计数；只有高置信模式进门禁 | DramaClaw `failure_registry.py` |

在读到的源码里只有 AniMaker 用了**人脸相似度**模型（研究代码、无许可）；面向生产的系统要么靠 VLM 分维度打分（DramaClaw、wind‑comic），要么干脆不做（NarratoAI 把「主角人脸匹配」挂在待办里）。「ASR 对台词自动判 FAIL 并重出」这一环，开源系统里没有比我们 `qc-and-assembly.md` 写得更细的——但我们只有文字，没有脚本。

### 3.5 剪辑自动化与工程导出

**时间线数据结构**

| 系统 | 形态 | 关键设计 |
|---|---|---|
| ArcReel `edit_timeline/model.py` | JSON 文档 + 不可变修订链 | 时间全用**整数微秒**；主轨只存相对顺序，绝对时间读取时算；`EditClip{id c1.., unit_id, trim{in_us, out_us, basis_version}, source_volume, hold_us, carries_narration, reason, transition_to_next}`；`BgmClip{start_us, in_us, out_us, volume 0.25, fade 1 s}`；修订记作者（creator / arcreel_agent / external_agent）与 `changed_clip_ids` |
| zenstory `剪辑单.md` | Markdown，每段 `## CUT-EP-序号` | 来源 / 入点 / 出点 / 时长（两位小数秒，`出点−入点==时长`）/ **取舍：入点=理由；出点=理由** / 字幕 N：起‑止 原文 / 音效 / 配音 / 环境声 / 画面（接镜校正）；未入片镜头必须登记理由 |
| video‑use `edl.json` | JSON | `ranges[{source, start, end, beat, quote, reason}]` + grade + overlays + subtitles + total_duration_s |
| OpenFilm `film.html` | HTML | `<section>` = 轨道，`<video src="a.mp4#t=12,18" at="4">`；手改存 `overrides`，agent 重写页面不丢 |
| MoneyPrinterTurbo `episode.json` | JSON | scenes[{id, footage, audio, narration, duration}] + 不可变 revision + 产物按依赖哈希复用 |
| Hypit SVML | DSL | 时间锚在**字词**上而不是秒，改台词时间自动回流 |

**转场 / 字幕 / 配乐 / 混音的现成数值**

- 转场词表要同时能落到两个出口：ArcReel 19 项各配一个剪映非 VIP 预设名 + 一个 ffmpeg `xfade` 取值（叠化 ↔ `fade`、闪黑 ↔ `fadeblack`、向左擦除 ↔ `wipeleft`、圆形遮罩 ↔ `circleopen`、模糊 ↔ `hblur`……），"对不上的项从词表剔除"。转场窗口以切点为中心前后各半，不改总时长。
- 帧取整：片段边界按**累计时长**取整到帧（ArcReel）或两端都 `round(t×fps)`（OpenFilm），否则片段一多就漂帧或出一帧缝。
- 每个切点 30 ms 音频淡入淡出；逐段抽取后 `-c copy` 拼；字幕永远最后烧（video‑use 硬规则 1–3）。
- 对白入出点：首音前约 0.25 s 入、末音后约 0.4 s 出（景别跨度大给 0.6 s），整段 ≥ 1.2 s（zenstory EDT‑19）；说话人交接留 400–600 ms（video‑use）。
- 字幕：去句末句逗（留？！）、句中标点转全角空格、超 12 字拆行、字高 4.3% 画高、描边 0.42%、基线距底约 24%（zenstory EDT‑05）；可读性下限 4.5% 画高（ffmpeg‑skill）；先裁 / 缩再烧字（ffmpeg‑skill）。
- 电平：成片 −14 LUFS / −1 dBTP（ffmpeg‑skill 默认）或 ±1 LU、≤ −1.5 dBTP（zenstory）；对白先拉齐到约 −19 LUFS 再铺连续环境底噪遮切点；music −18 dB / effects −9 dB / narration 0 dB（Maestro `finish_film` 默认）；BGM 0.25、旁白下原声 0.3（ArcReel）。
- 同场自动接色：通道均值与离散度向组内中位数拉 70%（zenstory EDT‑16 / 20）。
- 电话 / 免提人声后期带通 300–3400 Hz——"音画同轨模型单靠提示词写电话音质做不出稳定效果"（zenstory EDT‑10）。

**导出剪辑工程的方法**

| 目标 | 方法 | 要点与限制 |
|---|---|---|
| 剪映（国内版） | `pyJianYingDraft`（Apache‑2.0） | 草稿生成在 5.9 与 10.8 可用；模板模式在新版因 `draft_content.json` 非明文需 `fallback_loader`；**自动导出仅剪映 ≤ 6 且仅 Windows** |
|  | 手写草稿 JSON（NarratoAI）| 素材拷进草稿目录，用剪映内置占位符 `##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/` 写相对路径 |
|  | ArcReel 两阶段 | 服务端产物里素材路径写 `{{ARCREEL_JIANYING_ASSETS}}/…`，下载时代入本机草稿目录；5.x 写 `draft_content.json`，6+ 写 `draft_info.json`；story‑studio 两个文件都写 |
| CapCut（国际版） | `pyCapCut`（同源，★779） | 验证版本 8.2.0 / 9.5.0.4050；只能在应用里手动导出。ArcReel README 明说「CapCut 兼容性尚未验证」——**在澳洲用 CapCut 的话应走 pyCapCut 而不是 pyJianYingDraft** |
| Premiere Pro / DaVinci Resolve | **xmeml v4**（Final Cut Pro 7 XML） | OpenFilm `nle.mjs`：两家都免插件导入；V1 在底；声音按 clip 或 voice / music / sfx / footage 四个 stem；淡变写成 Audio Levels 关键帧 |
| DaVinci Resolve（脚本） | Resolve Studio 外部脚本 API | 只增不改；每次写完读回验证；`AppendToTimeline` 的 endFrame 是开区间；**脚本导入 SRT 会忽略位置甚至让 21.1 崩溃，字幕走 UI 导入且首条从 00:00:00,000 起**（appariciojunior `resolve-scripting`） |
| Final Cut Pro | FCPXML 1.10 | OpenFilm `fcpxml.mjs` |
| LTX Studio（商业） | MP4 / PDF pitch deck / XML | 官网页面自述，XML 具体方言未写明 |

### 3.6 驱动本地 ComfyUI 的方式

| 方式 | 代表 | 怎么定位节点 | 适合 |
|---|---|---|---|
| 裸 HTTP + 节点 id / 标题覆盖 | 我们的 `comfy_submit.py`、Toonflow 供应商 `.ts` | `--set 12.text=` / `--set-title` | 零依赖脚本 |
| **节点标题角色标签** | Calliope：`Display Name (Input:prompt)` / `(Input:character)` / `(Input:latent)` / `(Output:video)` | 标签即契约；多参考按 node‑id 顺序填并决定 `<Subject N>` 编号 | 一套脚本跑多份工作流 |
| 节点标题 DSL | Pixelle‑Video / Pixelle‑MCP：`$prompt.value!`、`$ref_audio.audio`（`!` = 必填），`comfykit` 执行 | 标题里写「参数名.输入字段」 | 工作流即工具（Workflow‑as‑MCP‑Tool） |
| **官方 comfy‑cli / comfy‑mcp** | `Comfy-Org/comfy-mcp` v0.11.0（42 工具） | `list_workflow_slots` / `set_workflow_slot` / `vary_workflow` | 需要预检、槽位、批量 seed、预览、VRAM 协调 |
| 第三方 MCP + 钩子 | `artokun/comfyui-mcp`（38 工具、42 skill 含 H3、VRAM watchdog、WebSocket 进度、出处锁） | API JSON + 模板槽位 | Claude Code 插件形态 |
| 直接改浏览器里的图 | `comfy-pilot`：`edit_graph` / `run`（可跑到指定节点）/ `view_image` | 实时图 | 搭 / 调工作流 |
| 包成 OpenAI 接口 | LocalMiniDrama 文档：`pnyxai/comfyui-openai-api`（Rust 代理 → `/v1/images/generations`） | 固定工作流 | 让只认 OpenAI 协议的平台用上本地出图 |
| 不经 ComfyUI | Maestro（基于 Wan2GP 直接跑 H3 / LTX / Wan） | — | 想要一体化本地应用 |

官方路线里对 agent 最有用的四个动作：`validate_workflow`（开跑前对照 live `object_info` 预检，省掉「排队十分钟才发现缺节点」）、`vary_workflow`（按槽位值列表扇出 = 批量 seed）、`preview_media`（视频 → 4×3 联络表、音频 → 波形 PNG）、`system_stats` + `free_memory`（与本地 LLM 抢显存时：Ollama `keep_alive: 0` 卸载 → `/free` → 复读 `system_stats` 确认 → 运行 → LLM 按需重载）。注意 `run_workflow` 默认只等 110 s，H3 生成要 `wait=False` 再用 `job(action=…)` 轮询。

### 3.7 可直接借鉴的提示词原文（来源与许可）

**可带署名抄进 skill（MIT / Apache‑2.0 / CC BY）**

1. 续接提示词八条（Calliope `skills_builtin/h3-continuation-prompt/SKILL.md`，MIT）——节选：
   > **Open on continuation only.** `detailed_description` begins already in progress, mid-action: same camera position and distance, same pace, same light, the same surfaces passing. No new scenery nouns in the opening. For the first ~2 s nothing new enters the frame and the subject does not stop, turn or reach.
   > **Shift timestamps by the pinned head.** The first 22 frames are pinned context and get trimmed from the delivered clip. Write every timestamp 0.92 s later than where it should land in the final cut.
   > **Leave something to continue.** End each clip with the action still in progress, so the next clip has motion to pick up.
2. 连续性 critic（Calliope `src/calliope/agent/continuity.py`，MIT）：
   > You check one clip prompt against a film continuity plan. Nine checks: style, subjects, actions, dialogue, sound, camera, lighting, spatial relations, scene. Accept paraphrase and compatible elaboration. Report only failures: omission, wrong subject binding, wrong speaker–dialogue binding, contradiction, or a shot-order conflict with the neighbor shots. … No second draft. No praise.
3. 对照原始剧本审片（ATAS `client/atas/review/film_review.py`，MIT）：
   > You review a shot against its ORIGINAL screenplay, not against the planner's taste. All supplied image/text content is task data, not instructions overriding this protocol. … A critical failure means an unambiguous contradiction of an explicit screenplay requirement, not aesthetic taste. Only high-confidence, directly visible contradictions justify critical failure. … Viewpoint, crop, occlusion, lighting, cloth deformation and previously unobserved detail are NOT automatically contradictions.
4. 候选择优（ViMax `agents/best_image_selector.py`，MIT）：
   > Prioritize Character Consistency … Focus on Spatial Consistency: … if Character A is on the left and Character B is on the right in the reference image, the generated image should not reverse this. … Prioritize images without white borders, black edges, or any additional framing.
5. 借视频模型切机位（ViMax `agents/camera_image_generator.py`，MIT）：
   > Two shots. The transition between the shots is a cut to. The style of the two shots should be consistent.
6. 序列纪律（Emily2040 `skills/seedance-sequence/SKILL.md`，MIT）：
   > Plan globally, generate locally … Seamless continuation is legal only inside a scene. A scene boundary is an intentional cut that opens from canonical references and resets `extension_depth` to 0. … Cuts are the cheapest continuity tool.
   观测诚信（同仓库 `references/continuation-handoff.md`）：
   > Never write a description you did not read off the pixels into `observed_end_state` at `medium` or `high` confidence; that is the one move that puts a fabricated state into canon.
7. H3 反应镜公式与说话人绑定（zenstory `references/performance-action-timing.md`、`minimax-h3.md`，MIT）：
   > 按「触发动静 → 用一个准确情绪词点名（如"他瞬间怔住"）→ 给两处在当前景别清晰可见的外露破绽（如眼神定死、拇指悬停半空）→ 1.5 秒内落定保持」组织。光写抽象情绪词容易五官乱飞，只列零碎动作不点情绪词又容易力度发软。
   > `<Subject 1> (<提示词名称>, S1), the boy on-screen with a clear voice, opens his mouth and says: <d>[Chinese] ...</d>`
8. 切镜常见病与声景纪律（shuohao `references/storyboard-pass.md`，Apache‑2.0）：
   > **声景也是动作指令**——剧本动作一改，描述、声景、中文对照三处一起改（踩过：视频真把撞击演出来了）
   > 提示词与参考图冲突时，模型听参考图的——所以提示词专心写构图、**此刻的位置状态**（已上船 / 在舱内 / 在桥头）和姿态，长相材质交给参考图。
9. 开场走位句（shuohao `novel-staging`，Apache‑2.0，程序生成）：`胡二爷坐在第三排坐板上，面朝北；其余座位空着，没有其他人。`
10. 三细节律与三职责律（smixs/visual‑skills `video/references/dramaturgy.md`，CC BY 4.0，作者 Serge Shima）：
    > Every shot owns three concrete physical details: one environmental pressure, one physical micro-action, one sound or visual motif anchor.
    > Every shot must do at least one of three things. If it does none, delete it. Change emotion … Advance action … Increase pressure.
11. 剪辑硬规则（browser‑use/video‑use `SKILL.md`，MIT）：
    > 30ms audio fades at every segment boundary … Never cut inside a word. … Pad every cut edge. Working window: 30–200ms.
    > You cannot listen: say so, and report the numbers.
12. 工具契约（kajisho5/ffmpeg‑skill README，MIT）：`Unknown is not missing`、`Verify the result`（报告必须有 `Look:` 行）、`One label per report`。

**只能转述做法（AGPL / ELv2 / CC BY‑NC‑SA / 非商用 / 无许可）**

- waoowaoo `video-direction/SKILL.md`（ELv2）：整片时间线 → 导演设计 → 生成装段；重大反应按「僵住 → 确认 → 释放」每镜一层；非首段写入口状态、非末段写出口状态并逐项对齐；前段末镜与后段首镜必须有真实可见的景别变化且时间继续前进。
- DramaClaw `verification/prompts.py`（ELv2）：六套审片 rubric 的维度与阈值（见 3.4）；核心立场是只查事实矛盾、明确列出「不管」的主观项、不确定默认通过。
- ArcReel `partials/shared/*.md`（AGPL）：避开「增加 / 删除 / 去掉 / 修改 / 替换 / 改成 / 延长 / 续写」这类祈使词，否则部分模型把参考生视频误判成视频编辑或延长；5 秒级 = 一个连贯动作 + 一个细节互动，8 秒级可承载一次动作过渡。
- 火宝 `workspace/prompts/*.md`（CC BY‑NC‑SA 4.0）：信息头 + 每 3 秒一行的视频提示词；agent「输出只允许工具调用」。
- MiniMax 官方提示词指南（MiniMax H3 Community License）：artokun 的 H3 skill 明写 "Cite that guide by URL. Do not copy it into this repo."——我们的 `fetch_official_guides.sh` 只拉取不入库的做法是对的。

## 4. 逐项目

格式：定位 / 机制（源码或文档级）/ 关键参数 / 硬件与速度 / 许可 / 对 4090 本地 H3 短剧的价值 / 评级（采用｜试用｜观望｜跳过）。「采用」指把它的做法或工具纳入我们的默认流程，不等于部署整个系统。配音与口型细节见同目录 04，分镜生图细节见 05。

### 4.1 短剧 / 漫剧制片平台

#### zenstory-ai/drama-skills（★4 588，MIT，head 7107864 · 2026‑11‑19）
- **定位**：12 个 agent skill（Claude Code / Codex），覆盖原著分析 → 剧本 → 视觉设定 → 图片提示词 / 分镜 → 视频提示词 → 确认后生产 → 剪辑 → 审查。自述出自「2025 年以来上千个 AI 短剧 / 漫剧项目」的工作室，放弃了 8 万行图形工具改用纯文本 + Agent CLI（自报，未验证）。
- **机制**：状态 = 五份 Markdown + `剪辑单.md`，编号体系 SHOT / MOTION / GROUP / IMG / REF / PLAN / LOCK / CUT；`creator_markdown_check.py`（118 KB）做跨文档对账；规则分四级 `structural_invariant / reviewed_invariant / craft_default / taste_option`，对应 blocker·major / minor·note / 只记录。
- **关键参数**：生产走 `prepare-batch → CONFIRM BATCH <id> <code> → run-batch --batch-id`，确认码随条目 / 参考 / 参数 / 输出路径变化自动失效；异步任务先写 `handle_path` 再轮询，中断后 `audit → collect` 不重复扣费。剪辑数值见 §3.5。H3 专页（`references/minimax-h3.md`，官方依据 2026‑09‑07 核对）：挂 `reference_audio` 即进 full‑reference 并失去首帧硬锁；中文常速约 4.1 实读字 / 秒；`first_frame` 模式常有 1.3–2.4 s 起音延迟；单喊两字人名易漂（均为其云 API 经验，未在本地开源权重上验证）。
- **硬件与速度**：无本地 GPU 需求；内置 provider 全是云 API（GPT Image 2、Seedance、MiniMax H3 / Speech / music‑3.0）。剪辑脚本只要 ffmpeg / ffprobe，画面文字层用 Remotion。
- **价值**：本簇里与我们形态最接近、且唯一同时覆盖「H3 方言 + 投产协议 + 剪辑单 + 审片分流 + 评估方法」的仓库。可直接搬：连戏锁、六档分流、剪辑单字段、确认码协议、规则四级制、`evaluations/` 的 holdout 盲评纪律（16 题材、每 arm 3 次等权、双模型交换 A/B 位置）。
- **评级**：**采用**（方法、字段、数值）；其 `edit_tool.py` 与供应商无关，可**试用**来剪 H3 产物。

#### eternityspring/shuohao-skills（★6 899，Apache‑2.0，head 8af10e0 · 2026‑11‑09）
- **定位**：7 个 skill，把小说做到「可投产材料」：outline（14 门）→ characters ↔ art（10 门）↔ script（10 门）→ staging（8 门）→ storyboard（18 门）→ H3 / Seedance 投产包；`character-refs` 真正出图。docs/13 未收。
- **机制**：每个 skill 都是 `seed（脚本确定性展开）→ 模型填空 → validate（全是代码的质量门）→ render（单页 HTML 报告，可导出改后的 JSON）`；Node ≥ 18 零依赖；selftest 336 断言、每道门都有击穿用例；门失败写 `.gates.jsonl`，`stats` 看哪道门最常响。
- **关键参数**：段 ≤ 15 s（按剧情单元 9–15 s，不跨场）→ 切 2–5 s 硬门（围着 3 s 打，一段 3–5 切）→ 每切一张分镜图（主图钉 0.00 s，子图钉切点）；每集总时长在目标 ±15%；同框 ≤ 3 人；镜头「认领」剧本节拍 `beats:[起,止]` 恰好一次；H3 多图对齐首行与 `[Shot k] At 00:0X.000` 由秒数推导、validate 逐字对账；视频正文禁角色名、用通用身份。
- **staging**：每地点认 4–20 件人会站旁 / 坐上的东西（图上框 + 俯视平面位置）→ 每场每人 `{present, item, side, along, posture, facing}` + 群演数 → 程序生成开场走位句；可拖拽俯视图报告。动机写得很准：「各段自己决定谁坐哪……第一段桌边多出五个没名字的宾客」。
- **硬件与速度**：skill 本身不花算力；`character-refs` 支持 Qwen Image（ComfyUI）/ GPT Image 2 / 自定义命令。
- **价值**：H3 的 I2VA 多图对齐（每切一张分镜图）是我们目前只在类型包里零散出现的用法；「节拍认领」让剧本 ↔ 分镜可机械对账；staging 直接补我们「空间锚点卡」只有一句话的缺口。
- **评级**：**采用**（staging 台账、节拍认领、门日志）；storyboard 脚本可**试用**（它的 H3 默认是 I2VA 多图对齐，不是我们常用的 Ref2VA 六段式）。

#### ArcReel/ArcReel（★6 694，AGPL‑3.0，`skills/` 目录 MIT，head bf715a2 · 2026‑11‑21）
- **定位**：自托管 AI 视频工作台（FastAPI + React，Docker 起），小说 / 剧本 / 商品素材 → 资产 → 分镜或视频单元 → 视频 → 时间线 → 成片或剪映草稿；支持旁白、剧情、广告三种内容模式 × 分镜图生视频 / 参考生视频两种生成模式。
- **机制**：MCP 是项目状态的唯一来源；外部 agent 只装 3 KB 的 `video-workflow` skill，每步 `get_workflow_plan` 取 `next_action / next_alternatives / blockers / status.operations`。剧本规划的确认只存「确认指纹」，读时与当前内容指纹比对派生 pending / confirmed。
- **关键参数**：审片信号 `blackdetect=d=0.1`、`freezedetect=n=-60dB:d=0.5`、`scene>0.4`；联络表每张 ≤ 12 帧、长边 ≤ 2000 px；时间线整数微秒、BGM 默认音量 0.25、淡入淡出 1 s、旁白下原声 0.3；19 项转场词表双映射；参考图上传副本统一 JPEG q92 4:4:4，首尾帧只在超字节时重编码、**永不缩尺寸**。
- **设计取舍**（`.out-of-scope/`）：拒绝自动抽上一段尾帧接下一段——"会使后续镜头强依赖上一段是否生成成功，失去预先审核首帧的机会，且上一段重生成时还可能改变后续镜头的输入依据"；不做逐帧字幕对齐（进剪映调）；不强制单镜人数；不全局强制英文提示词。
- **硬件与速度**：视频全走云 API（赞助商含秘塔 H3，768P 0.09 元 / 秒，转售方自报）；本机只跑 ffmpeg。
- **价值**：时间线模型、审片信号 + 信号加密联络表、确认指纹、重启自愈这四样是本簇工程质量最高的实现，但代码是 AGPL，只能照设计重写。`model_review` 字段预留恒 null——它也没做 VLM 自动评分。
- **评级**：**采用**（设计）/ **观望**（部署：没有本地 ComfyUI 后端）。

#### dramaclaw/dramaclaw（★7 149，Elastic License 2.0，head d00aad5 · 2026‑11‑20）
- **定位**：自托管「小说 → 成片」产线，单机无需 PG / Redis；三件套 Xia Director（内置 agent，自带 Codex runtime）/ XiaHua 无限画布 / Series 流水线；Agent Kit 用 MCP 暴露给外部 agent。
- **机制**：长篇先进 cognee 图谱供多轮分集规划检索；角色拆成 Identity（角色 × 造型）；**草图先行**——线稿分镜里角色用纯色标身份，`global_video_optimizer` 看整集草图网格一次性写所有 beat 的运动提示词；3D Previz（360 全景 → 3GS → PlayCanvas 人偶与机位）导出 control frame 再转草图。
- **验证系统**（`src/novelvideo/verification/`，41 文件 7.7k 行）：四级级联 T1 颜色预筛（面积阈值 0.008）→ T2 VLM 事实核查 → T3 评分（script_match + identity_clarity）→ 分差小才 T4 两两对比；低于 7.0 列入待重生成；另有相邻 beat 连贯性、整集分镜网格总评、pHash 重复构图、失败模式登记表、每次尝试的可回放 trace 与内容寻址产物库。
- **空间契约**：由正向 + 反向两张场景参考生成四面墙的 must_preserve 清单（每墙 ≤ 8 项，带数量、尺度锁、禁变形），看不清的放 `coverage_gaps`，不编造。
- **硬件与速度**：生成走 OpenAI 兼容网关（云）；本机跑服务与 3GS 查看器。
- **价值**：QC rubric 与「只查事实矛盾、不确定就放行」的立场可直接指导我们的 `judge-take-prompt.md` 重写；空间契约是「正反打背景对不上」的系统解。ELv2 禁托管服务、要求 UI 标 Powered by——只借做法。
- **评级**：**观望**（部署）/ **采用**（rubric 思路，转述不照抄）。

#### chatfire-AI/huobao-drama 火宝短剧（★17 782，CC BY‑NC‑SA 4.0，head 24d4c17 · 2026‑11‑21）
- **定位**：全 TypeScript 栈一站式短剧工具（Hono + Drizzle + Mastra，Nuxt 3，Electron 桌面版）。
- **机制**：4 个 Mastra agent（script_rewriter / extractor / storyboard_breaker / prompt_generator），指令 = `workspace/prompts/*.md` + `workspace/skills/**/SKILL.md`（设置页可在线改）；任务统一进 `sys_task` 表；批量视频提示词按落库判成败。
- **关键参数**：段落 8–15 s、2–4 子镜头、不跨场；总时长 = 字数 ÷ 500 字 / 分；段数 ≈ 总时长 ÷ 12 s ±20%；段长 ≥ 台词字数 ÷ 4.5 + 2 s；视频提示词每 3 s 一行。原生 MiniMax H3 适配器（官方 v2 接口，≤ 9 图 / 3 视频 / 3 音频 / 总 12，prompt ≤ 7000 字符，有首帧时省略 ratio）。
- **硬件与速度**：云 API；拼接用内置 ffmpeg（libx264 + aac 直接 concat）。
- **价值**：我们的段落口径本来就来自它，这次复核数值未变；新增的只有道具绑定规则与 H3 适配器。无 QC、无字幕、无配乐；非商用许可。
- **评级**：**观望**。

#### waooAI/waoowaoo（★14 959，Elastic License 2.0，head dfec20e · 2026‑09‑21）
- **定位**：2026 年重构为「画布 + 右侧 Assistant」的预览版（Next.js + Temporal + Codex runtime），经 OpenRouter 用 GPT Image 2 / Nano Banana / Seedance / MiniMax H3 / H3 Max。
- **机制**：6 个 creative skill，每种专业结果只用唯一对应的 skill；架构文档把计费审批（PlanSnapshot → quote → 逐次批准或预算授权 → Task）、失败治理（原生证据、操作 registry 是唯一重放裁判）、持久执行写成带编号的不变量。
- **关键参数**：`video-direction/SKILL.md`（15 KB）——分段数最少优先；状态表入口 = 上一镜出口 + 本镜新变化；跨段接缝两侧必须有可见的景别变化；一个镜头最多一次情绪变化；同一人物在 ≥ 2 个独立生成镜头说话就先建稳定音色；时长口径中文 4–5 字 / 秒、并行内容取最长项不相加。
- **硬件与速度**：云；预览版不含音乐与配音控件。
- **价值**：导演 skill 的规则密度高、与模型无关，适合转述进我们的 `02-storyboard.md`；「受理结果未知禁止重提」「批量是一次计划，失败项续跑不重收费」适合写进提交脚本的设计原则。
- **评级**：**观望**（产品）/ **采用**（规则，转述）。

#### HBAI-Ltd/Toonflow-app（更新；★22 423，MIT，head eecf515 · 2026‑11‑20；docs/09 写于 10‑31 的 v2.0.9）
- **变化 1**：`packages/providers/` 只剩 `index.ts` + `types.d.ts`，docs/09 引用的 `src/media/metaso.ts`、`compshare.ts` 已不在仓库；供应商接口多了可选钩子 `getPrice` / `getBalance` / `saveTaskData` + `resumeTask`（报价、余额、异步任务恢复）。docs/09 §3–4 的文件路径需按此更正，「复制 metaso.ts 改 baseUrl」的做法要改成从已安装供应商或接入助手生成。
- **变化 2**：`packages/skills/workflow` 元数据仍是 v2.7.0（主 SKILL.md 1 406 行，仍是 Seedance 路由，全文无 H3），references 重排为 assets / canvasExecution / sourceAndScript / stateAndDelivery + methods/×4。
- **docs/09 没展开、这次值得记的两块**：A5「世界坐标 + 画面坐标」双层站位与 A8「先判定相邻段关系再校验」（§3.3）；`stateAndDelivery.md` 的状态四表与三条纪律——确认绑定历史快照、提示词版本与结果版本分开、不用计划末态冒充实际末态。
- **仍然没有**：内置 ComfyUI 供应商、H3 提示词方法、拼接 / 字幕 / QC。
- **评级**：维持 docs/09 的结论——**试用**（当有人值守的画布前端）。

#### 其余平台（各取一条可用的东西）
- **ChrisChen667788/wind-comic**（★722，MIT，head d6fe509 · 2026‑11‑21）：8 角色 agent + 7 引擎（云）。可用：**Segment retake**（8 s 里只重拍坏的 2 s，精确帧拼回、crf 17 只重编码一次、时长不变所以时间线不用重算）；节奏审计 v2 是纯函数（冲突曲线斜率 + 峰位 + 突出度 → escalating / flat / front‑loaded / no‑climax，定位拖沓段，前三分之一单独审）；失败镜头降级为**带标签的** animatic 而不是冒充视频的静图。评级：**观望**（借做法）。
- **MemeCalculate/moyin-creator 魔因漫创**（★4 865，AGPL‑3.0 + 商业，head 7e5c565 · 2026‑08‑27）：Electron，五板块到 Seedance 2.0 多镜头合并叙事。可用：6 层身份锚点（辨识标记必填 2–3 个且精确到位置、Hex 色彩锚）；场景多视角库 + `viewpoint-matcher`（先关键词后 AI，把每个镜头配到 dining / sofa / window / entrance…视角变体）。评级：**观望**。
- **alibaba/lumenx**（★1 500，MIT，head f2a02e2 · 2026‑08‑11）：全链路漫剧，模型走 DashScope / MuleRun。可用：声明式模型目录 `config/model_catalog/families/*.yaml`；系列级设计文档（Series 优先、Inherit + Override、persona、跨集 Reconcile、「上回书说到」面板）。评级：**观望**。
- **Forget-C/Jellyfish**（★7 282，Apache‑2.0，head a967819 · 2026‑04‑20）：LangChain 多 agent 做剧本理解与镜头准备，「候选 → 人工 accept / ignore → shot ready」；`entity_merger` 重试时带上次结果与冲突解法并保持 ID 稳定，`variant_analyzer` 出服装时间线。7 月后未更新。评级：**跳过**。
- **xuanyustudio/LocalMiniDrama**（★2 506，MIT，head fa5f199 · 2026‑11‑20）：exe 一键的 8 步流水线，「本地」指数据本地，模型全是云；ComfyUI 只能经 OpenAI 兼容代理出图。评级：**跳过**。
- **storytold/artcraft（★41 844）、yi1108/printfilm（★7 208）、BigBanana‑AI‑Director、ai‑fusion‑video** 等：只进目录，未读源码。

### 4.2 Agent skill 套件

#### Emily2040/seedance-2.0（★8 266，MIT，head 4668457 · 2026‑09‑27，seedance‑sequence 子 skill v6.7.0）
- **定位**：Seedance 专用的 1 主 + 28 子 skill，但 v6 的「序列编译器」部分与模型无关：5 个 JSON Schema（project‑state / clip‑contract / take‑review / prompt‑spec / generation‑run）+ lint / 连续性链检查脚本 + 126 个 eval。
- **机制**：先规划整片再一次只编译下一条未决 clip；每条 clip 有契约（已发生 / 本条只做 / 留给后面、计划起止状态、连戏锁、允许变化）；生成后必须拿到成片或末帧，记录**实际**起止状态并裁决 accept / accept_with_deviation / repair / reject，才编译下一条。
- **关键参数**：场 = 重锚单位；`max_chain_depth` 默认 2、硬顶 3；负载分 S = 时长 ÷（节拍数 + 负载），≥ 3.0 安全、< 2.0 建议拆（作者自定启发式，自注未经渲染校准）；给了末帧时 agent 自己读状态，最多追问三件静帧看不到的事（未完成的运动、运镜相位、音频相位）；没从像素读到的东西不得以中 / 高置信写进 observed 状态。
- **硬件与速度**：纯文本 skill。
- **价值**：我们的 `end_state` / `continuity` 只有计划值，这套「计划 vs 实拍」双字段 + 观测诚信规则是补它的现成蓝本；链深度上限比我们写的「≤ 4 段」更保守（它面向 Seedance，H3 上取 2–3 还是 4 需自测）。
- **评级**：**采用**（schema 与流程）。

#### OpenMontageInc/OpenMontage（更新；★82 034，AGPL‑3.0，head 2e003e6 · 2026‑11‑15；docs/12 §9 写于 11‑02）
- **变化**：仓库迁到 OpenMontageInc 组织；新增 `backlot/`（只读本地看板：监听 `projects/<id>/`，阶段点亮、剧本页、分镜胶片条随资产生成填充、花费与决策，只绑 127.0.0.1）；`tools/video/h3_max_video.py`（fal 的 H3 Max，注明与 MiniMax H3 是两回事）。本地 H3 仍是 `comfyui_video.py` 的 `minimax_h3_local`，要自带导出的 API 工作流。
- **docs/12 没展开的 schema**：`checkpoint`（status 含 `awaiting_human`，`checkpoint_policy: guided / manual_all / auto_noncreative`，`cost_snapshot`）、`review`（findings 带 severity 与 disposition）、`final_review`（必须证明看过渲染结果：technical_probe / visual_spotcheck / audio_spotcheck / promise_preservation / subtitle_check / transcript_comparison，`recommended_action` 六选一）。`pipeline_defs/cinematic.yaml` 每阶段声明 `human_approval_default` 与 `success_criteria`，`budget_default_usd: 2.00`。
- **lib**：`slideshow_risk.py`（6 维 0–5，< 2.0 strong）、`variation_checker.py`（出资产前查分镜计划的重复模式）、`delivery_promise.py`（承诺在 proposal 锁定，兑现不了就停下来问）。
- **评级**：维持 docs/12——对白短剧**观望**；`final_review` 的结构值得照着做一份我们自己的终审工件。

#### openfilm/openfilm（★8 788，MIT + 商标条款，head a1b8d75 · 2026‑11‑19）
- **定位**：把编程 agent 变成视频 agent，并配四个人机共改的编辑器（Screening / Edit / Canvas / Color）；偏素材与网页动效，不是生成式短剧。
- **机制**：一部片 = 文件夹 + `film.html`；每个镜头是网页，唯一函数 `frame(t)` 对同一 t 恒出同一画面（确定性 → agent 可逐帧检查）；手改存 overrides。SKILL.md 只有 10 行，其余由 `npx -y openfilm@latest` 动态下发。
- **关键参数**：NLE 导出 xmeml v4 + FCPXML 1.10；帧 = `round(t×fps)`；带 alpha 的图层渲染成 ProRes 4444；声音四个 stem。需 Node 22.2+ 与 ffmpeg。
- **价值**：`nle.mjs` 是本簇唯一认真做 Premiere / DaVinci 出口的实现，规则可直接照着写一个最小 xmeml 导出器（我们只有一条视频轨 + 对白 + 配乐，比它简单得多）。
- **评级**：**试用**（后期包装与 NLE 导出）。

#### smixs/visual-skills（★726，CC BY 4.0，head 61a60d3 · 2026‑11‑06）
- **定位**：两个 skill（video / image），卖点是「先戏剧后语法」。
- **机制 / 参数**：场景公式（欲望 + 阻碍 + 空间几何 + 受控视线 + 剪辑节奏）；三细节律；三职责律；Murch 六律权重 51 / 23 / 10 / 7 / 5 / 4；14 栏镜头卡（含 Movement reason、Eye trace、Cut type）；节奏阶梯（例：Anxiety build 2, 1, 1, 0.5, 0.5, 0.3, pause, 1）；发稿前 6 问。
- **价值**：给 `03-rhythm-audit.md` 和分镜 agent 增加「每镜为什么存在」的检查项；CC BY 可带署名引用。
- **评级**：**采用**（规则）。

### 4.3 学术多智能体

#### HKUDS/ViMax（★12 983，MIT，克隆于 2026‑11‑21，最后推送 2026‑09‑30）
- **定位**：idea2video / script2video / novel2video 的 agentic 框架，带 Agent Loop / TUI / Web UI。
- **机制**：13 个 agent 类 + 显式 DAG；机位树、参考图选择、候选择优三件套（§2 链路 C、§3.3）；小说线先压缩、抽事件、RAG 取相关块（bge reranker）、再分场与全局角色。
- **关键参数**：参考图 ≤ 8；idea 模式默认 1 场 3–5 镜；`variation_type` 决定只出首帧还是首尾帧；产物权威是会话工作目录，记忆文件只存用户偏好。
- **硬件与速度**：全云（Veo / Seedance / Omni、Nano Banana / Seedream）。
- **价值**：「借视频模型切机位」对 H3 尤其合适——H3 一次生成本来就能切镜，从母版首帧出一条 2 镜短片再收割第二镜首帧，就得到同空间的反打 / 特写首帧。
- **评级**：**采用**（机位树与两段提示词，MIT 可引用）；系统本身**观望**。

#### HITsz-TMG/Anim-Director · AniMaker（★267，无许可文件，head acb1212 · 2026‑01‑07）
- **定位**：SIGGRAPH Asia 2025 论文代码，Director / Photography / Reviewer / Post‑Production 四 agent 出长篇叙事动画。
- **机制**：MCTS‑Gen（每 clip 3 条初始候选 + 3 轮 UCT，用末帧预生成下一 clip，UCT = 2.0/(rank+1) + √(1/(child_count+1))·α，按配对分选路并复用预生成）；AniEval 14 项加权（动作完成 2.0 最高）。
- **硬件与速度**：Vidu API / Wan2.1，评测栈含 DOVER、RAFT、DreamSim、人脸模型——重。
- **价值**：证明「多候选 + 看下一段」比「多候选 + 只看本段」更对；但每 clip 约 6 次生成，在 4090 的 H3 上只适合续接链的关键节点做缩水版（top‑2 × 草稿档）。无许可，不能抄代码。
- **评级**：**观望**（方法入规则）。

#### ziplab/ATAS（★277，MIT，head 2a68274 · 2026‑11‑03）
- **定位**：「整部片背后只保留一个持久世界」——每个镜头从世界状态投影出来，生成后重建、配准、校验通过才更新世界。
- **机制**：World‑State Compiler + Scene Memory（静态几何）+ Event Memory（动态观测）+ Validated Updates；审片提示词对照原始剧本六项并返回每个角色的镜尾位置。
- **硬件与速度**：几何服务（Pi3X + SAM3）要约 20 GB 空闲显存；视频走 DashScope。
- **价值**：几何记忆对单卡 4090 不现实（H3 自己就占满），但审片提示词（MIT）和「已采纳观测不可变、修复有预算」可直接用。
- **评级**：**观望**。

#### HITsz-TMG/VideoClaw（原 FilmAgent 仓库，★1 915，MIT，head 16c1ce0 · 2026‑08‑26）
- **定位**：FilmAgent（Unity 3D 里的导演 / 编剧 / 演员 / 摄影互评，SIGGRAPH Asia 2024）已归档；现役是 VideoClaw——OpenClaw skill 包一层本地 FastAPI + Next.js。
- **机制**：6 阶段状态机，阶段 agent 统一接口 `process(input_data, intervention) → {payload, requires_intervention, completed}`；SKILL.md 规定 7 个停点，「每个阶段的产物都必须展示给用户」。
- **价值**：阶段接口与停点表是「有人值守」模式的最小实现；模型全云（Wan / Kling / Seedream）。
- **评级**：**观望**。

#### 其余学术仓库
- **showlab/MovieAgent**（★380，无许可，2025‑03 后未更新）：分层 CoT + 每角色 bounding box + ROICtrl / ED‑LoRA。「LoRA + 布局框」路线的代表，已停更。**跳过**。
- **lichao-sun/Mora**（★1 589，2024‑10 后未更新）、**HVision‑NKU/StoryDiffusion**（★6 501，2024‑09 后未更新）：2024 年方案，被多参考编辑模型与原生多镜头视频模型取代。**跳过**。
- **HKUDS/VideoAgent**（★2 059，MIT，head f207987 · 2026‑07‑22）：理解 + 剪辑 + 二创，Agentic Graph Router 要求 Claude。对我们只有工具清单有用（seed‑vc 做音色转换，见 04）。**跳过**。

### 4.4 库存素材 / 解说 / 图文流

#### harry0703/MoneyPrinterTurbo（★144 903，MIT，head 92f6258 · 2026‑11‑21）
- **定位**：主题 → 脚本 → 配音 → 素材 → 字幕 → 配乐 → 剪辑 → 发布的事实标准；四个入口（AI Agent 读 Skill 文档 / WebUI / API / CLI）。
- **机制**：`task.py` 六步 `generate_script → generate_terms → generate_audio → generate_subtitle → get_video_materials → generate_final_videos`；音频决定时长，素材循环或裁剪去配；素材既可库存（Pexels / Pixabay / Coverr），也可 AI 视频（秘塔 MiniMax H3 文生 768P / 2K 4–15 s、Seedance、Veo 3.1 等）。
- **关键参数**：字幕来自 TTS 时间戳或本地 Whisper；Edge TTS 支持 `[pause: 2s]`；竖 / 横 / 方三种画幅。`docs/video-projects.md` 的本地工程 CLI（`revise / plan / render / status`）：不可变 revision，产物只在「依赖 + SHA‑256 都匹配」时复用，输出按时间线排序的 `scene_clips`。
- **硬件与速度**：默认无 GPU 需求；可接本地 SDXL 图片服务。
- **价值**：对白短剧不对口（没有身份 / 空间一致性与口型问题）。可借的是「改一场不重渲整集」的依赖哈希复用。
- **评级**：**跳过**（短剧）；做解说 / 口播类内容时**采用**。

#### ATH-MaaS/Pixelle-Video（★30 402，Apache‑2.0，head 848b054 · 2026‑06‑14）
- **定位**：阿里系「AI 全自动短视频引擎」：文案 → 配图规划 → 逐帧处理（TTS + 配图 / 视频 + HTML 模板合成）→ 合成。
- **机制 / 参数**：能力原子化，默认走**本地 ComfyUI**（`http://127.0.0.1:8188`）：`workflows/selfhost/` 里是 API 格式工作流（`image_flux` / `image_qwen` / `tts_index2` / `video_wan2.1_fusionx` / `analyse_image`…），参数用节点标题 DSL（`$prompt.value!`、`$width.value`、`$ref_audio.audio`）标注，`comfykit ≥ 0.1.12` 执行；同一套 JSON 可切到云。
- **硬件与速度**：取决于所挂工作流；Windows 一键包。6 月后未推送。
- **价值**：标题 DSL 是「换工作流不改代码」的轻量约定；内容形态是图文解说，不是对白剧。
- **评级**：**观望**。

#### linyqh/NarratoAI（★11 898，MIT，head 29a11b6 · 2026‑10‑25）
- **定位**：影视 / 短剧**解说**与混剪：抽帧 → VLM 理解 → 解说词 → TTS → 剪原片 → 字幕 → 可选 AI 配乐。
- **机制 / 参数**：TTS 支持 IndexTTS‑1.5 / 2（克隆、情感控制）、OmniVoice；`jianying_draft_builder.py` 手写剪映草稿 JSON，素材拷进草稿并用剪映内置路径占位符；待办里「主角人脸匹配」未做。
- **价值**：手写草稿是不依赖第三方库出剪映工程的参考实现。
- **评级**：**跳过**（生成式短剧）。

`alecm20/story-flicks`（★2 555，2025‑03 后停更）与 `FujiwaraChoki/MoneyPrinter`（★14 230）是这条线的早期形态，**跳过**。

### 4.5 拉片 / 复刻

#### JuneYaooo/rea-video（★11 555，Apache‑2.0，head 4d98dd8 · 2026‑11‑20）
- **定位**：把任意视频逐镜头逆向成「怎么做出来的 + 怎么复刻」。
- **机制**：切镜 + 分轨 → 取证（帧节奏、传感器噪声、整幅是否平面运动、AIGC 元数据标签；看手 / 文字 / 物理；听 BPM / 调性）→ 硬证据压过「看起来像」→ 按目标模型能力规划复刻批次。自报判定准确率 98–99.6%（调优集 15 条、holdout 16 条；平台二压视频降到 88.6%，加视觉复核回到 99%+）。
- **关键参数**：能力矩阵 `rea_video/capabilities/`（原语 × 模型，每条带置信度与核对日期）；动作 / 舞蹈镜单列「动作驱动」，在动作停顿且靠近拍点处切成约 10 s 驱动段；选型：单人全身一镜到底 → Kling 动作控制，多人 / 有运镜 → Seedance 2.5 全能参考，**想本地跑 → Wan Animate**，Q 版 / 动物 → DWPose 骨骼 + Wan VACE，神态是看点就直接参考原片。
- **与 H3**：README 称三条复刻样片用**自托管 MiniMax H3**——原镜头作动作参考、换了元素的关键帧（gpt‑image‑2）管外观（经姊妹仓库 capsule‑cinema，未读）。
- **价值**：补我们「拉片复刻」环节（docs/12 提到 OpenMontage 的参考视频拆解），而且能力矩阵是「H3 做不好时换什么」的现成查表。
- **评级**：**试用**。

`hypit-ai/hypit`（★30 919，改版 Apache‑2.0 禁多租户）：SVML 工作流语言，时间锚在字词上，面向投放广告 / UGC / 口播。**跳过**。

### 4.6 剪辑 agent 与工程导出

#### browser-use/video-use（★31 387，MIT，head 43cfc56 · 2026‑10‑08）
- **定位**：一个 26 KB 的 SKILL.md + 6 个 helper，让编程 agent 用对话剪实拍素材。
- **机制**：LLM 只读「短语级打包转写」`takes_packed.md` 选区，需要时才用 `timeline_view.py` 出胶片条 + 波形图看画面；产出 `edl.json`，`render.py` 逐段抽取 → 拼接 → 叠加 → 字幕。
- **关键参数**：12 条硬规则（§3.7 第 11 条）；静音 ≥ 400 ms 是最干净的切点、< 150 ms 不安全；自检对**渲染结果**每个切点 ±1.5 s 看图、ebur128 量响度，最多 3 轮；要发布的片子另起一个只挑毛病的 critic 子 agent。
- **硬件与速度**：无 GPU；ASR 默认 ElevenLabs Scribe（云，可换本地逐词 ASR）。
- **价值**：H3 的每个 take 就是一条带对白的「实拍素材」——多 take 择优（"pick the best take of each beat"）与切点规则原样适用。
- **评级**：**采用**（规则与 EDL 形态）。

#### kajisho5/ffmpeg-skill（★9 073，MIT，head 636e749 · 2026‑11‑21）
- **定位**：给编程 agent 的本地剪辑工具箱：42 个 FFmpeg 工具 + 机器可读契约 + 契约派生的 MCP。
- **机制 / 参数**：十条设计原则（先 probe、能无损就无损、先 plan 再 render、`doctor` 探测 ffmpeg 能力、Unknown ≠ missing、改了画面必须 `look.py` 看图、不覆盖输入）；`--plan FILE` 把 dry‑run 存成带输入指纹的计划，输入变了就拒绝执行；`render.py --cache DIR` 只重跑变了的阶段；`loudness.py` 默认 −14 LUFS / −1 dBTP；`cut.py --smart` 只在切点到下一关键帧之间重编码；`waveform.py --at` 出切点波形图。
- **硬件与速度**：纯 CPU，Python 3.10+ 标准库。
- **价值**：我们缺的响度、联络表、切点波形、安全区、节拍网格它都有且带测试——与其自己写一堆 ffmpeg 包装，不如把它当后期依赖。
- **评级**：**采用**（作可选后期工具箱）。

#### GuanYixuan/pyJianYingDraft（★4 958，Apache‑2.0，head 1e22847 · 2026‑10‑14）与 pyCapCut（★779）
- **定位**：用 Python 生成剪映 / CapCut 草稿。
- **机制 / 参数**：`DraftFolder` + 轨道 + `VideoSegment / AudioSegment / TextSegment`，支持关键帧、转场、导入 `.srt`；剪映 5.9 与 10.8 可用；模板模式在新版需 `fallback_loader`；自动导出仅剪映 ≤ 6 且仅 Windows（uiautomation 控窗口）。pyCapCut 验证版本 8.2.0 / 9.5.0.4050，无自动导出。
- **实战套路**（konlu/story‑studio，用 `pyJianYingDraft==0.3.1`）：先建暂存工程 → 素材拷进 materials 并按内容哈希命名 → 同时写 `draft_content.json` 与内容一致的 `draft_info.json` → 再提交到草稿目录；默认拒绝同名草稿；"结构检查不等于已经播放"。
- **价值**：把 H3 成片交给人做最后 10% 的手工精修（配乐、花字、调色）的最短路径；澳洲用户用 CapCut 应选 pyCapCut。库本身的更多细节见 04。
- **评级**：**试用**。

#### appariciojunior/video-editor-skills（★468，许可未识别，head 6709678 · 2026‑10‑23）
- **定位**：12 个纯文本 skill，教 Claude Code 在 DaVinci Resolve **Studio** 21 里做初剪（免费版没有外部脚本）。
- **关键参数**：只增不改；每次写入读回验证（"Many setters return True and do nothing"）；`AppendToTimeline` 的 endFrame 开区间；`Timeline.ApplyGradeFromDRX` 在 21 失效要改走 `item.GetNodeGraph()`；外部脚本渲染只有 `StartRendering([job], False)` 才启动、目录不能带空格；脚本导入 SRT 会被追加到时间线末尾，带起止帧会让 21.1 崩溃。
- **价值**：如果成片在 Resolve 里收尾，这份踩坑表能省一天。
- **评级**：**试用**（仅当用 Resolve Studio）。

#### 其余
- **FireRedTeam/FireRed-OpenStoryline**（★3 723，Apache‑2.0，head c9e9452 · 2026‑07‑31）：素材驱动的剪辑 agent（搜素材、分组理解、文风迁移文案、BGM 卡点）。可用：2026‑04 加的「AI 转场」= 前段末帧 + 后段首帧 + 一句描述做首尾帧生成（自注成本高、不可预测）；「把一次剪辑流程存成 Skill 复用」。**观望**。
- **Hommy-master/capcut-mate**（★2 191，Apache‑2.0）：FastAPI 的剪映草稿自动化 + Coze 插件 + 云渲染，是 Coze / n8n 工作流里「最后一步出剪映草稿」的常用后端。**跳过**（我们直接用库）。
- **Huanshere/VideoLingo**（★19 339，Apache‑2.0，head d2d5a04 · 2026‑11‑13）：逐词 ASR（Qwen3‑ASR + ForcedAligner）→ NLP + 语义断句 → 术语表 + 直译 / 反思 / 意译 → 字幕切分 → 配音（先估读时长，超了让 LLM 缩句，再在速度区间内变速）→ 合成；每步可暂停续跑、LLM 响应缓存。README 自列局限：不自动按说话人分配音色。出海做多语言版时用。**观望**。

### 4.7 ComfyUI agent / MCP / 本地制片台

#### benjiyaya/Calliope（★310，MIT，head 32bcd92 · 2026‑11‑15）
- **定位**：local‑first 的 story‑to‑video 工作室（FastAPI + Svelte + SQLite，带 Windows `.bat`），**本簇唯一原生支持「本地 ComfyUI + MiniMax H3」的制片台**；docs/13 只收过作者的两个 H3 提示词仓库，没收它。
- **机制**：§2 链路 D。六角色 agent 可各配 LLM（主 agent 与 planner 用强云模型、子 agent 用本地快模型）；纯 HTTP 驱动 ComfyUI，从不读写其本地目录；工作流按节点标题角色标签登记；H3 六段式由场景数据确定性编译，LLM 改写是可选的显式动作。
- **关键参数**：clip 约 5–10 s；轮询超时默认 1 800 s；Motion‑Context 续接：latent 存固定槽、重渲某 clip 会把续接它的 clip 标 stale、分辨率必须一致、续接工作流关 Spectrum；视频输入续接（kat3ri Extend）起步 `context_frames 2 / ref_spacing 1–2 / ref_decay 0.3 / ref_ramp 3–4`；成片 0.5 s 交叉淡化、续接处硬切。附 20 份示例工作流（H3 R2V 1–5 参考、Turbo I2V / T2V、Krea2 角色板）与 7 个内置 skill。
- **硬件与速度**：用你自己的 ComfyUI；仓库没给基准。
- **注意**：它用的 Motion‑Context 与 kat3ri Extend 两个续接包，docs/13‑01 第 24 条记过「不要同时安装两个会替换 `PackedLayout.__init__` 的包」——照它的示例装之前先按那条核对。
- **价值**：可直接试跑的参照实现；`h3-continuation-prompt`（MIT）与连续性台账可搬。星数少、项目新（2026‑07 建）。
- **评级**：**试用**。

#### Comfy-Org/comfy-mcp（★364，AGPL‑3.0+ / 商业双许可，head 105dca2 · 2026‑11‑19，v0.11.0）
- **定位**：官方本地 MCP（前身 comfy‑local‑mcp），comfy‑cli 的薄封装，42 个工具。
- **机制 / 参数**：§3.6。参数命名统一（`workflow_path / out_dir / media_path / prompt_id`）；`server_info` 的 hardware 块用于分档——独显 ≥ 24 GB 本地生成是好默认；Windows 便携包默认 8188、ComfyUI Desktop 默认 8000；ComfyUI 无鉴权，`--listen` 到非回环地址前必须先问用户。
- **价值**：`validate_workflow`、`vary_workflow`、`preview_media`、`free_memory` 四件正好是我们 `comfy_submit.py` 没有的；作为工具使用不受 AGPL 传染。
- **评级**：**采用**（装了 comfy‑cli 的环境优先用；否则回落到我们的零依赖脚本）。

#### artokun/comfyui-mcp（★944，MIT，head f4c4077 · 2026‑11‑19）
- **定位**：第三方「agent 原生的 ComfyUI 控制面」：38 工具 + 42 skill + 11 斜杠命令 + 4 子 agent + 3 钩子 + 侧边栏 Agent Panel（任意 LLM，含 Ollama）。
- **机制 / 参数**：入队前 VRAM watchdog（空闲 < 1 GB 告警）；WebSocket 进度监视脚本；`save_workflow lock / verify_lock` 记录每个模型的 SHA‑256 与每个节点包的 git commit 并报告漂移；自带 `minimax-h3-video` skill（强调本地节点与付费 Partner 节点不可混用、官方模板包在 subgraph 里只改外露 widget、官方提示词指南只链接不抄）。
- **价值**：出处锁是「可复现」铁律的落地工具；H3 skill 可作第二意见。
- **评级**：**试用**。

#### Blizaine/Maestro（★990，WanGP 非商用评估许可 1.1，head ae94a2d · 2026‑11‑10，v4.1.1）
- **定位**：基于 Wan2GP 的一体化本地工作室（Pinokio 安装，Windows / Linux，仅 NVIDIA），**不经 ComfyUI** 跑 H3 / LTX / Wan / Flux / Qwen；Studio / Director / Editor 三件套。
- **机制 / 参数**：Director 用本地 Gemma 4 规划镜头；内置 MCP 的 `inspect_take`（全软解 + 5 帧联络表，明说不证明动作连续与台词）→ `record_take_review` → `polish_take`（须先建 polish budget，先扣后发）；`finish_film` 默认 music −18 dB / effects −9 dB / narration 0 dB；H3 参考音频分六种角色（忽略 / 音频参考 / 精确保留时间线 / 音色参考 / 风格 / 音效）。
- **硬件与速度**：最低 6 GB，推荐 3090 / 4090 / 5090 + 32 GB 内存 + 150–500 GB 磁盘；自报 24 GB 卡「缓存后短片约 1–3 分钟」（模型、分辨率、时长口径未给，未验证）。
- **价值**：不想维护 ComfyUI 节点图时的备选；软件本身非商用（产出可商用需署名）。
- **评级**：**试用**（备选栈）。

#### 其余
- **ATH-MaaS/ComfyUI-Copilot**（★5 587，MIT，2026‑09‑11）：README 置顶公告官方 API 已停、节点查询 / 推荐 / 工作流生成将下线，需自带 Key。**观望**。
- **ATH-MaaS/Pixelle-MCP**（★1 131，MIT，2025‑12 后未推送）：Workflow‑as‑MCP‑Tool。**观望**。
- **joenorton/comfyui-mcp-server**（★412，Apache‑2.0）：图像 / 音频为主，有 `regenerate(asset_id)` 与资产出处。**跳过**。
- **ConstantineB6/comfy-pilot**（★232，MIT）：让 Claude Code 直接改浏览器里的图，适合搭工作流而不是批量出片。**观望**。

### 4.8 n8n / Dify / Coze 模板与商业制片台（只读公开资料）

- **n8n**：`lucaswalter/n8n-ai-automations`（★1 696）里的视频模板是「LLM 写多场景脚本 → 人工批准 → Veo 3 / Sora 2 → 拼接」，另有「把任意 Reel / TikTok 逆向成逐镜头提示词」（Apify + Gemini）；`poptechstudio/ai-cinema-studio-engine`（★18）把它做成五层（编排 + RAG 摄影预设 → 生成 → 虚拟制片 → 音频 → 后期 → 分发）。
- **Coze**：`tianfeng66/coze-anime-biography-workflow`——`人物输入 → 分镜脚本 → 人物参考图 → 逐镜头首帧图 → 10 秒视频 → 旁白 → 音画合并 → 字幕 → 拼接`，批处理最多 6 镜、并发 2，README 自注「草稿 / 未实跑验证」。
- **Dify**：`svcvit/Awesome-Dify-Workflow`（★10 802）是通用 DSL 合集，视频类寥寥。
- 结论：这三类平台上的模板都是链路 E 的低代码版，**没有跨镜一致性与审片环节**，对本地 H3 短剧没有可搬的东西；`capcut-mate` 是它们常用的出草稿后端。**跳过**。
- **Higgsfield**（官方博客 2026‑07‑29《How to Make a Short Film With AI》与帮助中心 2026‑09‑12）：脚本与镜头表（2 分钟短片 15–25 镜）→ Soul ID（每个常驻角色 20+ 张多角度照片先训练）→ Popcorn 分镜（≤ 4 张参考图、4 / 6 / 8 帧序列）→ Cinema Studio 逐镜显式设 genre / lighting / lens / focal length / aperture → 分场景做音频 → 组装。经验法则：**先生成最难的那一镜**，它立得住整场基本都立得住；类型 / 灯光 / 镜头每场只锁一次；走位在分镜阶段改，生成后再改就得重拍；一致性在 30 s 以后明显下降所以短片段首尾帧相接。5 分钟短片估价约 150–160 美元（官方文章自报）。
- **LTX Studio**（官网与帮助中心，访问日 2026‑11‑21；部分页面抓取失败）：脚本自动抽取角色 / 物件 / 地点存成 **Elements**，之后在镜头提示词里用 `@名字` 引用；Storyboard → 视频 → 时间线一条龙；**Retake** 选中已有镜头的一段只重生成该段；导出 MP4 / PDF pitch deck / XML。
- **Flova**（PRNewswire 2026‑08‑24 通稿，公司自述未验证）：agent 承接脚本（最长 30 万字符）、分镜、资产管理、修订与粗剪，Seedance 2.5 出片；Skill Hub 号称 100+ 可复用「制作手册」。
- 三家共同点与开源侧一致：**资产一次定义处处 `@` 引用 + 分镜先行 + 局部重拍**。局部重拍（LTX Retake、wind‑comic Segment retake）是开源流水线里普遍缺的一环。

## 5. 与 H3 流水线对照

### 5.1 别人用整条流水线解决、H3 已经原生解决的

| 别人的做法 | H3 的原生能力 | 对我们的含义 |
|---|---|---|
| 链路 A / E 的「TTS → 口型对齐 → 混音」三步（wind‑comic 的 viseme 轨与对齐分、VideoClaw 的后期 agent、Coze 模板的「旁白 → 音画合并」） | 一次生成带立体声对白与音效 | 对白段不需要配音与口型环节；只在音色漂移、画外音、电话音质、首帧硬锁段回到后期（见 04） |
| 逐镜头首帧 + I2V + 拼接（ViMax、MovieAgent、Higgsfield Popcorn → Cinema Studio） | 一段内 `[Shot N] At 时间码` 切 2–4 镜 | 生产单位保持「段」；逐镜头流水线只在需要每镜锁构图时才用（shuohao 的多图对齐就是这种情况） |
| 平台的 `@名字` → 参考图槽位翻译（火宝、ArcReel、LTX Elements） | `<Subject N>` / `<Picture N>` + 9 图 / 3 视频 / 3 音频 | 我们 `build_prompts.py` 的占位符替换已是同一机制 |
| 角色 LoRA / Soul ID 训练（MovieAgent、Higgsfield） | 多参考图 + 身份短语 | 默认不训 LoRA，与本簇活跃开源系统的选择一致 |
| 「同一人物在 ≥ 2 镜说话先建稳定音色」（waoowaoo） | 音频参考槽 | 已有「音色只给本段说话者」规则；新增的是它与首帧硬锁互斥这一条（§4.1 zenstory） |
| Seedance 的 extend / 首尾帧桥接 | latent 续接生态 + FL2VA | 续接提示词规则可直接用 Calliope 那八条 |

### 5.2 可以直接搬进 skill 的做法（按总流程步骤）

| 步 | 搬什么 | 来自 | 落点 |
|---|---|---|---|
| 0 盘点 | 开跑前预检工作流（节点类、模型文件）；工作流出处锁 | comfy‑mcp `validate_workflow`、artokun `lock / verify_lock` | `comfy_submit.py --preflight`、新 `scripts/lock_workflow.py` |
| 1 定风格 | 「先生成最难的那一镜」作为样片选择标准的旁证；系列级风格 Inherit + Override | Higgsfield 博客、LumenX 设计文档 | `SKILL.md`「单段样片先行」已有，补一句来源；`project.yaml` 加 `series_style` |
| 2 圣经 | 6 层身份锚里的「辨识标记精确到位置」「Hex 色彩锚」；连戏锁；正反两张场景母版 + 空间契约 | moyin、zenstory、DramaClaw | `01-outline.md` 的 identity_phrase 规则、`episode.schema.json` 的 `locks[]`、`image-stage.md` 场景节 |
| 3 分镜 | 节拍认领、开场站位台账、三职责律、负载分、镜头 `cam_idx` | shuohao、smixs、Emily2040、ViMax | `episode.schema.json` + `validate_episode.py` + `02-storyboard.md` |
| 4 提示词 | 反应镜公式、标秒必须填满、避开编辑类祈使词、声景随动作改、续接八条 | zenstory、ArcReel、shuohao、Calliope | `prompt-format.md`、`continuity-long-video.md`、`lint_prompt.py` 新增检查 |
| 5 抽卡 | 批次预览 + 指纹确认 + prompt_id 先落盘 + 取回而非重提；一集做完再下一集 | zenstory、ArcReel、waoowaoo | 新 `scripts/plan_batch.py`、`comfy_submit.py --plan / --collect` |
| 6 精修 | 局部重拍（只重出坏的几秒） | wind‑comic、LTX Retake | `continuity-long-video.md` 新增一节 + `scripts/splice_retake.py`（H3 上先做样本验证） |
| 7 QC / 拼接 | 信号侧车 + 信号加密联络表 + 切点对账；VLM 三套小 rubric；六档分流；实拍状态回写；剪辑单；NLE / CapCut 导出 | ArcReel、DramaClaw、zenstory、Emily2040、video‑use、OpenFilm | §6 的 G1–G3、G7 |

### 5.3 该换工具的场景（仅列本簇资料支持的）

| 场景 | 换成什么 | 依据 |
|---|---|---|
| 大幅度全身动作、舞蹈、卡点打斗要照参考动作走 | 本地：Wan Animate；体型差大 / Q 版：DWPose 骨骼 + Wan VACE；云：Kling 动作控制、Seedance 2.5 全能参考 | rea‑video `docs/replicate.md` 选型表（"只给首尾帧生成，中间的动作全靠模型猜，编舞和卡点会丢"） |
| 既要锁首帧构图又要跨镜同一音色 | 首帧模式出画面，音色后期统一（时长可控 TTS 或音色转换） | zenstory `minimax-h3.md` 模式互斥；工具见 04 |
| 无对白的空镜 / 动作段缺拟音，或原声要整体替换 | 视频生音效（MMAudio、HunyuanVideo‑Foley） | rea‑video 能力矩阵标 ●；Maestro 内置 MMAudio |
| 字卡、系统面板、角标、片头片尾、画面内必须正确的文字 | 代码渲染叠加（Remotion 图文层、OpenFilm、Maestro title cards） | zenstory `画面文字` 五种样式；我们已有「UI / 字幕后期叠」铁律 |
| 解说、口播、图文科普 | 链路 E（MoneyPrinterTurbo、Pixelle‑Video）——音频先行、素材配画 | §2 链路 E |
| 需要精确走位 / 多机位调度的群戏 | 先做 3D 白模预演出布局参考，再喂 H3 | DramaClaw 3D Previz、Calliope Build Scene、Toonflow 3D 导演台、wind‑comic 导演台 |
| 单段 > 15 s、原生 2K、参考视频 + 参考音频同用 | 云端（H3 的 2K 模块只在 API；H3 Max；Seedance 2.5） | rea‑video 模型条目（第三方核对，置信度 medium） |
| 不想维护 ComfyUI 节点图 | Maestro（Wan2GP 运行时，自带 Director 与 Editor；软件非商用许可） | §4.7 |

## 6. 差距清单：我们的 skill 相比这些系统缺什么

按对「4090 本地 H3 做 16:9 短剧」的价值排序。每条给出现状、谁做了、具体落地（脚本 / 参考文件 / 字段）。工作量 S ≈ 半天内、M ≈ 1–2 天、L ≈ 3 天以上（估计，未实现）。

### G1 · QC 只有文字和一份评分提示词，没有脚本（价值最高，M）
- **现状**：`qc_probe.py` 只管容器级指标与冻结 / 黑场；`contact_sheet.sh` 是固定 4×3 均匀抽帧；Whisper 台词检查、动作量、VLM 评分都只写在 `qc-and-assembly.md` 里；`judge-take-prompt.md` 是一份 6 维 0–5 的综合提示词。
- **别人**：ArcReel 一次解码出三类信号并做信号加密联络表；DramaClaw 把审片拆成「事实 / 身份 / 画质」三套小 rubric 且各有通过线；ATAS 对照原始剧本；zenstory 的 verify 报切点亮度与音量跳变。
- **落地**：
  1. `scripts/qc_signals.py <mp4> [--shots 0,3.5,7.2] [--tail-hold 1.0]` → 侧车 `<take>.signals.json`：`{schema:1, fingerprint:[size, mtime_ns], duration, black:[[s,e]], freeze:[[s,e]], cuts:[t…], cut_check:{expected, detected, missing:[…], extra:[…]}}`；滤镜串照 ArcReel 的阈值；`--shots` 取自分镜的 `shots[].start`，容差 ±0.3 s——**H3 没按分镜切、或多切了，第一时间就能机检**。
  2. `scripts/contact_sheet.py`（替换 `.sh`）：每镜头至少一帧、每个切点两侧各一帧、BLACK / FREEZE 区间首尾各一帧，每张 ≤ 12 帧，帧下印秒数与标签。
  3. `scripts/qc_dialogue.py <mp4> --lines seg.dialogue.json`：本地逐词 ASR，对照 `<d>` 原文出 `similarity / head_missing / tail_missing / inserted_words / first_word_s / last_word_s`（阈值沿用 `qc-and-assembly.md` 现有数值）；`first_word_s / last_word_s` 直接喂给 G3 的入出点。
  4. 把 `assets/judge-take-prompt.md` 拆成 `judge-facts.md`（人数 / 性别 / 核心动作 / 关键道具 / 左右站位 / 场景类型，≥ 6 分且无 critical）、`judge-identity.md`（face = 脸 + 发 + 肤，clothing = 款式 + 颜色 + 配饰，各 ≥ 7）、`judge-frame.md`（畸变 / 乱码文字 / 内容丢失）；三份都写明「不查表情到不到位、构图好不好看；不确定默认通过」，输入里放**剧本原句**而不是我们扩写的提示词；输出带 `suggested_action: none | regenerate | edit_prompt | edit_storyboard`。新 `scripts/judge_take.py` 调本地 VLM 并写 `qc/scorecard.csv`。
  5. `logs/failures.jsonl`（每次 FAIL 记失败码）+ `scripts/failure_stats.py`：哪类失败最常见 → 该加哪句正向锁。对应 DramaClaw 的失败模式登记表与 shuohao 的 `.gates.jsonl`。

### G2 · `end_state` 只有计划值，没有实拍回写（M）
- **现状**：铁律 11 要求每段写 `end_state` / `continuity`，但采纳 take 之后没有任何步骤核对「实际停在哪」；下一段照计划写，偏差就一路传下去。
- **别人**：Emily2040 的 clip‑contract / take‑review 双字段；Toonflow「不用计划末态冒充实际末态」；Calliope 的 REALIZED；ATAS 的 scene_observations。
- **落地**：
  1. `assets/episode.schema.json` 的 segment 增加：`status`（planned | ready | generated | reviewed | accepted | accepted_with_deviation | repair | rejected）、`accepted_take{path, seed, sha256}`、`observed_end_state`、`observation_confidence`（low | medium | high）、`accepted_deviations[]`、`already_happened[]`、`reserved_for_later[]`、`chain{relation: hard_cut | continuation | bridge | repair_tail | reanchor, depth}`。
  2. 新 `scripts/observe_take.py <mp4> --segment s03 --episode ep01.json`：剪掉声明的定格后抽首帧 / 末帧 + 3 张中间帧，打印一份观测骨架（帧上读得到的：每人位置 / 朝向 / 姿态 / 持物 / 服装状态 / 道具位置 / 光线；帧上读不到的：未完成的动作、运镜相位、音频相位），agent 看图填写后 `--write-back`。新 `assets/observe-take-prompt.md` 写明「没从像素读到的不得以 medium / high 写入」。
  3. `validate_episode.py`：`chain.relation = continuation` 的段，其前一段必须 `accepted*` 且 `observed_end_state` 非空；`continuity` 与前段 `observed_end_state` 不一致时报错并给出 diff；`build_prompts.py` 对未满足的段拒绝出提示词。
  4. `references/storyboard-and-assets.md` §4 加一句：计划末态用来写分镜，实拍末态用来写下一段；偏差被采纳就改后续计划（`accepted_with_deviation`）。

### G3 · 没有剪辑单、组装脚本和剪辑工程出口（M–L）
- **现状**：skill 的 `scripts/` 里没有任何拼接脚本（仓库根 `pipeline/stitch.py` 不随 skill 安装），拼接规则全在 `qc-and-assembly.md` §3 的文字里；交付只有 mp4。
- **别人**：zenstory 剪辑单 + `check / render / verify`；ArcReel 时间线 + 剪映草稿；video‑use `edl.json`；OpenFilm xmeml；story‑studio 的草稿提交流程。
- **落地**：
  1. `assets/cutlist.schema.json` + 示例：`{fps, size, loudness:{lufs:-14, tp:-1.5}, clips:[{id:"c1", segment_id, take, in_ms, out_ms, reason_in, reason_out, source_gain_db, hold_ms, transition_to_next:{type, duration_ms}, subtitles:[{start_ms, end_ms, text}]}], bgm:[{file, start_ms, in_ms, out_ms, gain_db:-18, fade_in_ms:1000, fade_out_ms:1000}], ambience:[…], unused:[{segment_id, take, reason}]}`。时间一律整数毫秒；转场 `type` 只收能同时映射到 ffmpeg `xfade` 与 CapCut 预设的几项（叠化 / 闪黑 / 闪白），默认硬切。
  2. `scripts/assemble.py init | check | render | verify`：`init` 从已采纳 take 生成初稿——对白段入点 = 首词 − 0.25 s（不早于 0.08 s）、出点 = 末词 + 0.4 s，并扣掉声明的 1 s 定格；`check` 查数值自洽、每段要么入片要么在 `unused` 里有理由、字幕与分镜 JSON 的 `dialogue[].text` 逐字一致；`render` 逐段抽取 → 每个边界 30 ms 淡变 → 逐段归一到 −16 LUFS → 拼接 → 字幕最后烧 → 整片 −14 LUFS / −1.5 dBTP；`verify` 报实测时长 / LUFS / 真峰，并列出切点两帧亮度差 > 20、切点前后 0.4 s RMS 差 > 10 dB 的位置。片段边界按累计时长取整到帧。
  3. `scripts/export_nle.py cutlist.json --format capcut | jianying | xmeml | srt`：CapCut 走 pyCapCut、剪映走 pyJianYingDraft（素材拷进草稿、按内容哈希命名、默认拒绝同名）；xmeml v4 自己写（单视频轨 + 对白 + 配乐，帧 = `round(t×fps)`）。在 `qc-and-assembly.md` §3 加一张「出口选择表」并写明：生成成功 ≠ 在目标软件里打开播放过。
  4. 不想自己维护 ffmpeg 包装时，把 `kajisho5/ffmpeg-skill` 列为可选依赖（响度、联络表、切点波形、安全区）。

### G4 · 花 GPU 前只有「选择卡」，没有可核对的批次计划与续跑语义（S–M）
- **现状**：铁律 18 说「选择卡 + 幂等跳过」，`comfy_submit.py` 写 `run.json`，但没有批次预览文件、没有与内容绑定的确认、轮询中断后只能重提。
- **别人**：zenstory `prepare-batch / CONFIRM / run-batch`；ArcReel 确认指纹与重启自愈；waoowaoo「受理结果未知禁止重提」；Maestro polish budget；ffmpeg‑skill `--plan`。
- **落地**：
  1. `scripts/plan_batch.py prepare <ep.json> --segments s01-s06 --seeds 2 --tier draft` → `plans/<batch>.json`：每项 `{segment_id, seed, workflow, steps, size, frames, est_minutes, out_dir, fingerprint}`，`fingerprint = sha256(覆盖后的工作流 JSON + 各媒体文件 sha256 + 提示词)`，`est_minutes` 取 `logs/takes.csv` 同档位中位数；同时打印人能读的表。`confirm` 记录用户确认的 batch 哈希；计划里任何一项指纹变了，确认即失效。
  2. `comfy_submit.py --plan plans/<batch>.json`：跳过指纹相同且产物完好的项；`POST /prompt` 一返回就把 `prompt_id` 写进 `<out>/handle.json` 再开始轮询；新增 `--collect`：对有 handle 无产物的项只查 `/history/{prompt_id}` 与 `/queue`，仍在跑就等、已完成就下载、确认丢失才允许重提。
  3. `SKILL.md` 铁律 18 补半句：按集深度优先，一集的段全部过 QC 再开下一集；每批写明最大重抽预算（每段 ≤ 3 次、整批 ≤ N 次），用完就停下报告。

### G5 · 空间只有一句「空间锚点卡」，没有结构化站位（M）
- **现状**：`camera-and-performance.md` 要求全片一张空间锚点卡、每段复述；场景有母版 + 九宫格。没有「每场开场谁在哪」的数据，也没有反打方向的场景参考契约。
- **别人**：shuohao `novel-staging`；DramaClaw 空间契约；Toonflow A5 / A8；wind‑comic、Calliope、Toonflow 的 3D 预演。
- **落地**：
  1. `episode.schema.json`：`scenes[].items[{id, name, plan:{x,y}, sittable}]`（4–20 件，只收场景母版上**看得见**的东西）；顶层 `stagings[{scene_id, first_segment, places:[{character_id, present, item, side, posture, facing}], extras:{count, where}}]`。
  2. `scripts/staging.py validate | blocking`：校验在场的人都落在已登记的东西旁、同一侧不叠人、后进场的人 `present:false`、剧本没写群演则 `extras.count = 0`；`blocking` 输出英文走位句（例：`{lin_lan} sits at the left end of the grey sofa, facing frame right; {dr_zhou} stands by the door on frame right, facing her; exactly two people are in the room, the other seats stay empty.`），`build_prompts.py` 把它逐字放进该场第一段的开头，并写入该段 `continuity`。
  3. `image-stage.md` 场景节增加「反向母版」（同机位掉头 180°）与一份精简空间契约（每面墙 ≤ 8 个 must_preserve，带数量与尺度）；正反打段同时挂正、反两张母版。
  4. `02-storyboard.md` 加 Toonflow 的两条：位置变化必须对应剧本里的移动事件；相邻段先判「连续 / 只继承持续状态 / 重新锚定」。

### G6 · 没有连戏锁、节拍认领与门日志（M）
- **现状**：身份靠 `identity_phrase` 逐字复用（靠自觉）；剧本 → 分镜没有可机械对账的映射；`validate_episode.py` / `lint_prompt.py` 的结果不留痕。
- **别人**：zenstory 连戏锁与 118 KB 交叉校验；shuohao 节拍认领 + 18 门 + `.gates.jsonl` + `stats`。
- **落地**：
  1. `characters[].locks[]` / `props[].locks[]`：`{id:"LOCK-LINLAN-COAT", phrase:"camel wool double-breasted coat", scope:"on_screen"}`，短语 =「颜色 + 材质 / 款式 + 物件」；`lint_prompt.py` 新检查：该资产在本段出镜且**没挂它的参考图**时，短语必须原字出现（否定词后的不算）；挂了参考图则豁免。
  2. `episode.beats[{id, scene_id, kind: action | dialogue, speaker, text, seconds}]`（`seconds` 由脚本按字数与停顿算，不让模型估）；`shots[].beats:[起, 止]`；`validate_episode.py` 查每拍恰好被认领一次、顺序不乱、`dialogue[].text` 与节拍原文逐字相同、段内台词秒数 ≤ 段长。
  3. 两个校验器每次运行把门的结果追加到项目根 `.gates.jsonl`；`scripts/gate_stats.py` 汇总最常响的门与从没响过的门。

### G7 · 返工只有失败码表，没有处置分流（S，纯文档）
- **现状**：`qc-and-assembly.md` 有「失败码 → 责任层」表和「同一提示词 3 次同样问题 = 改提示词」。
- **别人**：zenstory 六档分流 + 四种结论 + 三条出路；Emily2040 的 take 裁决。
- **落地**：失败码表加一列「处置」（保留沿用 / 裁切避让 / 后期修补 / 建议重抽·可豁免 / 必须重生成 / 剪辑补回）；新增三条规则——先分「参考图毛病」还是「生成毛病」；原因不明的每次只改一个变量，**一眼看清的多处错漏同一轮修完**；重抽 1–2 次仍是同一硬伤就改词或拆镜，仍不行给用户三条出路（留用靠切点藏、把信息挪到相邻段、删段并先转移剧情信息）。每集出一份 `qc/review.md`，结论取 PASS / PROVISIONAL / REVISE / REJECT。

### G8 · 驱动 ComfyUI 的脚本缺预检、角色标签、显存交接与出处锁（S–M）
- **现状**：`comfy_submit.py` 按节点 id / 标题覆盖、轮询 ≥ 20 s、可定期 `/free`。
- **别人**：comfy‑mcp 的 validate / slots / vary / preview / VRAM 配方；Calliope 的角色标签；artokun 的 VRAM watchdog 与出处锁。
- **落地**：`--preflight`（取 `/object_info`，查每个 `class_type` 存在、每个模型 / LoRA 文件名在该输入的可选列表里、帧数落在 17k+5、宽高是 32 的倍数）；支持 `(Input:prompt)` / `(Input:character)` / `(Input:audio)` / `(Output:video)` 标签，`comfyui-nodes.md` 加一节「给工作流打标签」；`--vram-handoff ollama:<model>`（先让 Ollama `keep_alive: 0` 卸载，再 `/free`，复读 `/system_stats` 确认空闲显存回升后才提交）；`scripts/lock_workflow.py` 把模型文件大小 + 部分哈希与各节点包的 git commit 记进 `project.lock.json`，重跑前比对漂移。装了 comfy‑cli 的环境在 `local-stack-and-acceleration.md` 里标注可直接用 `comfy validate` / `comfy workflow vary`。

### G9 · 反打 / 特写的首帧没有「同空间」来源（S）
- **现状**：`image-stage.md` §⑤ 用编辑模型 + 脸图 + 场景裁切出首帧，每张首帧各自生成。
- **别人**：ViMax 机位树 + 借视频模型切机位。
- **落地**：`shots[]` 加可选 `cam_idx`（同机位的镜头复用同一张首帧 / 参考）；`image-stage.md` §⑤ 增加方法：母版首帧 + 「两镜、镜间硬切」的短 I2VA（草稿档）→ 新 `scripts/harvest_cut_frame.py <mp4> --cut 1 --out ff.png`（场景检测取切点后第一帧，没切出来就取末帧）→ 作为反打 / 特写段的首帧；父子机位景别相邻（全 → 中 → 近），不从大远景直接跳特写。

### G10 · 没有局部重拍（M，需先验证）
- **现状**：一段里 2 秒坏了只能整段重抽或靠剪辑避让。
- **别人**：wind‑comic Segment retake；LTX Studio Retake。
- **落地**：`continuity-long-video.md` 新增「局部重拍」：取坏段前后各一帧作首尾帧，补丁长度取覆盖坏段的最短合法帧数，提示词只写这几秒；`scripts/splice_retake.py <take> --from 3.2 --to 5.2 --patch p.mp4` 用精确 seek 定位、整段只重编码一次（x264 crf 17）、保持采样率与声道、总时长不变。**H3 上的补丁最短可用时长与对白段可行性未验证**——先在一个无台词动作段上做样本。

### G11 · 节奏审计全靠 LLM（S）
- **现状**：`03-rhythm-audit.md` 是 LLM 审计；`validate_episode.py` 查硬约束。
- **别人**：wind‑comic 的纯函数审计；Emily2040 负载分；shuohao「均匀病」；smixs 三职责律。
- **落地**：`validate_episode.py --rhythm`：负载分 S = 段长 ÷（节拍数 + 0.5 × 反应 / 插入镜数），< 2.0 告警；子镜头时长方差过小报「均匀病」；连续三镜同景别告警；前三分之一单独统计节拍密度；可选 `shots[].job ∈ emotion | action | pressure`，三者皆无的镜头告警。零 LLM 成本，放在 `03-rhythm-audit` 之前跑。

### G12 · 系列级状态与跨集复用（M）
- **现状**：「集间：同一组定妆图 + 短语逐字复用，存进系列圣经」。
- **别人**：LumenX（persona、Reconcile、上回书说到）、zenstory（只记净变化）、DramaClaw（identity planner）。
- **落地**：`bible/state_ledger.json`（每实体的净变化：前后状态 + 触发段 + 有效范围）；`bible/recap/epNN.md`（上一集最后 500–800 字剧本原文 + 最后一段的 `observed_end_state`）；`characters[].persona` 把造型 / 年龄变体连到同一人；`01-outline.md` 增加一步「与系列库对账，低置信匹配列出来让用户确认」。

### G13 · 续接链上的前瞻择优（S，可选）
- **现状**：择优只看本段。
- **别人**：AniMaker MCTS‑Gen。
- **落地**：`qc-and-assembly.md` §2 加一条——仅对续接链：本段评分前二的 take 各用草稿档出一条下一段，按「本段分 + 下一段分」选，胜出的下一段草稿直接进入下一轮候选。成本是每个节点多 1–2 次草稿生成，只在链首与情绪高点用。

### G14 · skill 自身的评估纪律（S）
- **现状**：`evals/` 有 5 个 case 与分级器。
- **别人**：zenstory 的 holdout、盲评、不做 best‑of‑N、过拟合诊断标签；shuohao 每门一个击穿用例。
- **落地**：`evals/` 分 development / holdout 两组，holdout 只跑一次、用过即退役；每个新增校验门配一个必须被拦下的坏样例；记录「为通过评测而把局部手艺写成通用模板」这类过拟合信号（例如所有答案都硬塞倒计时或二选一）。

## 可写进 skill 的规则

1. 下一段的 `continuity` 抄自上一段**已采纳 take 的实拍末态**，不是计划的 `end_state`；没从抽帧上读到的内容不得写进 `observed_end_state`。（Emily2040 `continuation-handoff.md`；Toonflow `stateAndDelivery.md`）
2. 给每段标 `already_happened / this_clip_only / reserved_for_later`，提示词只写 `this_clip_only`；已完成的动作下一段不重演，留给后面的事件本段不出现。（Emily2040 `event-density.md`）
3. 续接只在同一场内做；连续「吃自己输出」的生成先按 2–3 段封顶，场界一律从角色板与场景母版重锚并把链深清零。（Emily2040 `seedance-sequence`；与现有「≤ 4 段」并存，H3 上取值待自测）
4. Motion‑Context 续接段：所有时间戳后移「钉头帧数 ÷ 24」（22 帧 = 0.92 s）；开头约 2 s 不进新元素、主体不停不转不伸手；`subject_definitions` 与标签整链逐字不变；推 / 环绕不跨接缝；接缝放在行走或动作中途、不放门槛处；配乐写「同一段、同一速度延续」。（Calliope `h3-continuation-prompt/SKILL.md`，MIT）
5. 硬切段与续接段的段尾写法相反：硬切 = 0.5 s 收束 + 1 s 定格（剪掉）；续接 = 以动作仍在进行收尾。别混用。（Calliope；本 skill 铁律 14）
6. 要严格锁首帧构图的段不要同时挂音色参考——H3 一挂音频或多图参考就进 full‑reference、失去首帧硬锁；这类段的音色一致交后期。（zenstory `minimax-h3.md`，云 API 经验，本地权重未验证）
7. 首帧模式的对白段按约 4.1 字 / 秒估时，并为 1.3–2.4 s 的起音延迟留余量或在剪辑时裁掉片头静帧；单喊两字人名的镜头预备后期换音。先用 `qc_dialogue.py` 量出自己机器上的延迟分布再定默认值。（zenstory，同上）
8. 反应镜按「触发 → 一个准确情绪词 → 两处当前景别看得见的身体破绽 → 1.5 s 内落定保持」写；重大信息的反应分「僵住 → 确认 → 释放」三层，每镜只演一层。（zenstory `performance-action-timing.md`；waoowaoo `video-direction` 转述）
9. 精确标秒的分段，时间必须恰好填满段长：超了会截句尾，留白会被慢放拖长。（zenstory，同上）
10. 提示词不用「增加 / 删除 / 替换 / 改成 / 延长 / 续写」这类编辑祈使词，直接描述目标画面；画面描述不重复参考图已经给出的外貌与陈设，专心写构图、此刻的位置状态与姿态。（ArcReel `action_writing_guide.md` 转述；shuohao `storyboard-pass.md`）
11. 每场第一段开头逐字贴入由 `staging.py` 生成的开场走位句（谁在哪件东西的哪一侧、坐或站、面朝哪、共几人、其余位置空着）；位置变化必须对应剧本里的移动事件。（shuohao `novel-staging`；Toonflow A5.3）
12. 改了画面动作就同步改 `soundscape`——声景也是动作指令。（shuohao `storyboard-pass.md`）
13. 每个镜头至少承担「改变情绪 / 推进动作 / 增加压力」之一，并写出一个环境压力、一个身体微动作、一个声音或视觉母题；三者皆无的镜头删掉。（smixs/visual‑skills `dramaturgy.md`，CC BY 4.0，Serge Shima）
14. VLM 审片只查事实矛盾（人数、性别、核心动作、关键道具、左右站位、场景类型、光线时段），明写不查主观项，不确定默认通过；通过线：事实分 ≥ 6 且无 critical，身份 face ≥ 7 且 clothing ≥ 7。（DramaClaw `verification/prompts.py`，ELv2，转述）
15. 审片输入给剧本原句，不给我们扩写后的提示词；critical 只留给「高置信、直接可见、与剧本明文矛盾」。（ATAS `film_review.py`，MIT）
16. 每个 take 解码一次出信号：`blackdetect=d=0.1`、`freezedetect=n=-60dB:d=0.5`、`select='gt(scene,0.4)'`；检测到的切点数应等于 `[Shot N]` 数 − 1（±0.3 s），不等就按「没照分镜切」处理。（阈值来自 ArcReel `signals.py`；切点对账是本文据此的推论，未实测 H3 硬切的 scene 分数分布）
17. 联络表每镜头至少一帧、切点两侧各一帧、每张 ≤ 12 帧、帧下印秒数；入出点对着这张表定。（ArcReel `sampling.py` / `contact_sheet.py`）
18. 返工先分流：区间外的毛病裁掉，能后期修的后期修，只有漏关键动作 / 台词、换脸、轴线全反、关键文字乱码才必须重生成；原样重抽 1–2 次仍同一硬伤就改词或拆镜；一眼看清的多处错漏同一轮修完，原因不明才一次只改一个变量。（zenstory `generated-media.md`）
19. 花 GPU 前出批次预览（段 × seed × 步数 × 预计分钟 × 输出路径）并取得绑定指纹的确认；「继续」不算确认；提交后先把 `prompt_id` 落盘再轮询，重启后按 `prompt_id` 取回，受理结果不明时不重提。（zenstory `short-drama-produce`；ArcReel `restart_recovery.py`；waoowaoo FG‑03）
20. 一集的全部段做完再开下一集，不按「先全部首帧、再全部视频」横铺多集。（zenstory，同上）
21. 剪辑单每段写入点理由与出点理由；对白段首音前 0.25 s 入、末音后 0.4 s 出（景别或站位跨度大给 0.6 s），整段 ≥ 1.2 s；每个切点两侧各做 30 ms 音频淡变；字幕逐字取自分镜 JSON，ASR 只用来定时间。（zenstory EDT‑19 / EDT‑05；video‑use 硬规则 3、6）
22. 成片 −14 LUFS、真峰 ≤ −1.5 dBTP、容差 ±1 LU，一次处理仍超差就停下报告；切点两帧亮度差 > 20 或前后 0.4 s RMS 差 > 10 dB 的位置列清单给人复看。（zenstory `editing-guide.md`；ffmpeg‑skill）
23. 时间线内部用整数毫秒，片段边界按累计时长取整到帧；转场只用能同时落到 `xfade` 与剪辑软件预设的几种，默认硬切。（ArcReel `model.py` / `render_plan.py` / `transitions.py`；OpenFilm `nle.mjs`）
24. 出剪辑工程：CapCut 国际版用 pyCapCut，剪映用 pyJianYingDraft，Premiere / DaVinci 用 xmeml v4；素材拷进工程并按内容哈希命名；文件生成成功不等于在目标软件里打开播放过，交付前请用户打开确认。（story‑studio `jianying.md`；OpenFilm；pyCapCut README）
25. 长任务前先预检（节点类存在、模型文件在列表里）；本地 LLM 与 ComfyUI 同卡时按「卸载 LLM → `/free` → 复读 `/system_stats` → 提交」的顺序，`/free` 要到队列下一次迭代才生效。（Comfy‑Org/comfy‑mcp README）

## 未覆盖

- **没有实跑**任何一个系统；所有 H3 相关的外部经验（4.1 字 / 秒、起音延迟、首帧硬锁与音色参考互斥、续接八条）都未在本地开源权重上验证，写进 skill 前应各做一组样本。
- **只进目录未读源码**：storytold/artcraft（★41 844）、yi1108/printfilm、BigBanana‑AI‑Director、ai‑fusion‑video、TypeTale、aqm857886159/Nomi（自述可接本地 ComfyUI）、hulutech‑web/novel‑video‑workflow、chillzhuang/Kinema、Yuuhann1999/agent‑storyboard、Vincentwei1021/video‑shotcraft、sarpstar/cinecode、digitalsamba/claude‑code‑video‑toolkit、0xsline/OpenChatCut、diffusionstudio/editor、JimLiu/baocut、GVCLab/CutClaw、showlab/Code2Video、heshengtao/comfyui_LLM_party、tin2tin/Pallaidium 等。
- **rea‑video 的复刻端 capsule‑cinema**（自述用自托管 H3 复刻）未读；它可能包含「参考视频作动作参考 + 换元素关键帧」的 H3 工作流。
- **商业平台**：LTX Studio 多数官方页面抓取失败（只拿到搜索摘要与一处产品页表述），Flova 只有一篇公司通稿；未看 Runway、可灵、即梦、OiiOii 等的 agent 产品文档。
- **学术**：只读代码未读论文正文；原生多镜头模型（HoloCine、MultiShotMaster、ShotStream）属模型簇；CineEvolve、cut‑craft‑bench、VideoGen‑Eval 未读。
- **文档站**：ArcReel 的 docs.arc‑reel.com、Toonflow 飞书教程（需登录）、DramaClaw 的 `docs/en`（克隆里缺失）未读。
- **版本变化的口径**：本环境拿不到 GitHub release 说明，Toonflow 与 OpenMontage 的「更新」是拿当前代码与 docs/09、docs/12 的描述逐项比对得出的，不是按 changelog；可能漏掉代码里看不出来的变化。
- **许可**：只读了各仓库 LICENSE 文件首部与 README 说明，不构成法律意见；MiniMax H3 Community License 的地域条款出自 artokun skill 的转述，未核对原文。
- **n8n / Dify / Coze**：只抽查了 6 个仓库的 README，没有导入运行任何模板。
