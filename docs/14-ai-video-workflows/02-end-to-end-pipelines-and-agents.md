# 02 · 端到端 AI 视频 / 短剧流水线与 agent 框架

> 调研日期 2026‑11‑21。簇名 `pipelines`。方法：GitHub 搜索 API 跑了 90 条关键词（按 stars 各取前 50，去重后 2 000+ 仓库，筛出 112 个候选），其中 **46 个浅克隆读源码 / 提示词 / schema**（克隆时跳过 > 150 KB 的二进制），其余读 README；商业平台（LTX Studio / Higgsfield / Flova）只读公开网页。星数、推送日期取自搜索 API 当日快照；`head=` 是克隆到的提交短哈希与提交日期。没有任何一个系统在本机实跑——凡是「自报」「未验证」都照标。
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
| HKUDS/VideoAgent | 2059 | MIT | 2026-07-22 | [EMNLP2026] "VideoAgent: All-in-One Agentic Framework for Video… | 精读 |
| HITsz-TMG/VideoClaw | 1915 | MIT | 2026-08-26 | 🚀 AI 全自动化视频生成员工 / Your First AIGC Coworker. Chat an Idea. Get a… | 精读 |
| HITsz-TMG/Anim-Director | 267 | 无 | 2026-01-07 | Controllable Animation Video Generation with Large Models-based… | 精读 |
| showlab/MovieAgent | 380 | 无 | 2025-03-26 | MovieAgent: Automated Movie Generation via Multi-Agent CoT Plan… | 精读 |
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
| hypit-ai/hypit | 30919 | 改版 Apache‑2.0 | 2026-11-20 | Clone any viral video with AI agents. Not just a script, the wh… | 精读 |
| edenfunf/reelmimic | 2091 | MIT | 2026-11-20 | Open-source AI video style cloning for 2D animation. Give it a … | 略 |
| bkingfilm/lapian-notes | 814 | MIT | 2026-10-26 | AI 辅助的电影拉片工具：AI 拆出剧情泳道时间轴、结构树、情绪曲线，边播边写拉片笔记，免费开源全本地 / AI-assist… | 略 |
| JuneYaooo/rea-toon | 292 | 自定义 | 2026-11-18 | AI 拆解学习短剧：为什么火、剧本怎么写、每一镜怎么拍 / Break down any short drama with A… | 略 |

**F 剪辑 agent / 时间线 / 工程导出**

| 仓库 | ★ | 许可 | 最后推送 | 一句话 | 本文处理 |
|---|---:|---|---|---|---|
| browser-use/video-use | 31387 | MIT | 2026-10-08 | Edit videos with coding agents | 精读 |
| kajisho5/ffmpeg-skill | 9073 | MIT | 2026-11-21 | Local video editor for coding agents: 42 FFmpeg tools with a ma… | 精读 |
| GuanYixuan/pyJianYingDraft | 4958 | Apache-2.0 | 2026-10-14 | 轻量、灵活、易上手的Python剪映草稿生成及导出工具，构建全自动化视频剪辑/混剪流水线。本项目的CapCut版本正于 htt… | 精读 |
| GuanYixuan/pyCapCut | 779 | 无 | 2026-10-16 | A lightweight, flexible, and easy-to-use Python tool for genera… | 精读 |
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
| Huanshere/VideoLingo | 19339 | Apache-2.0 | 2026-11-13 | Netflix-level subtitle cutting, translation, alignment, and eve… | 精读 |
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
