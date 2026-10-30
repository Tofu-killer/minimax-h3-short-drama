# 06 · 开源项目剖析：别人是怎么用 H3 做短剧的

> 阅读了 GitHub 上以 MiniMax 视频模型为核心的短剧/视频生产项目的 README 与关键源码。每个项目记录：目标、技术栈、流水线、提示词模板、H3 调用方式、值得借鉴与需要避开的点。

## 1. chatfire-AI/huobao-drama（火宝短剧）

- **规模**：16.8k star，v4.0.0（2026‑08），CC BY‑NC‑SA 4.0（**禁止商用**）。
- **定位**：「一句话生成完整短剧」—— 实际从小说文本开始，到整集成片。TypeScript 全栈：Nuxt 3 + Vue 3 前端、Hono + Drizzle + SQLite 后端、**Mastra AI Agents**、fluent‑ffmpeg、Electron 桌面版。
- **四个 Agent**：`script_rewriter`（小说→分集剧本）、`extractor`（角色/场景/道具提取去重）、`storyboard_breaker`（剧本→分镜段落）、`prompt_generator`（资产图提示词 + 分镜视频提示词）。Agent 的行为由 `backend/workspace/skills/*/SKILL.md` 定义，可在 UI 内编辑。
- **流水线**：建项目（选 16:9 / 9:16 + 视觉风格，风格注入所有图像提示词）→ 配置模型（文本/图像/视频三类 OpenAI‑compatible 供应商）→ AI 改写剧本 → 提取资产并批量生成形象 → 拆分分镜 + 生成提示词 → 选视频模型（Seedance 2.0 / **MiniMax H3** / Wan 3.0，分辩率档位随模型：MiniMax 为 768P / 2K）→ 批量生成（确认镜头数、总时长、模型、分辩率）→ 失败重试 → FFmpeg 拼接导出。
- **一致性**：角色形象图作为参考注入视频生成；提示词里 `@角色名` 自动映射到参考图；道具用白底单品图作参考；`scene_id` 段落级绑定。
- **`storyboard-breaker` SKILL 关键规则（原文）**：
  - "一个分镜 = 一个 **分镜段落**（segment）= 一个视频生成任务"，段落 8–15 s、含 2–4 子镜头，子镜头 2–6 s。
  - "目标总时长 = 剧本字数 ÷ 500字/分钟；段落数 ≈ 目标总时长 ÷ 12秒，允许 ±20% 浮动"。
  - 时长档：过渡段 8–10 s、叙事段 10–15 s、爆点段 12–15 s。
  - "段落时长 ≥ 段内台词与旁白总字数 ÷ 4.5字/秒 + 2秒表演余量"。
  - 台词写法 `【镜头N】… 角色名说：「台词」`，旁白 `旁白：内容`；`bgm_prompt` / `sound_effect` 不能空泛到只有「紧张」「悲伤」。
  - 字段：`description` `result` `atmosphere` `duration` `scene_id` `character_ids` `prop_ids` `image_prompt` `bgm_prompt` `sound_effect`。
- **借鉴**：段落化分镜规范、Agent 可编辑 skill、按供应商显示原生分辩率档位、内容审核失败引导换模型。
- **注意**：没有 TTS / 口型方案（依赖视频模型原生音频）；MiniMax 适配器参数未在文档公开；Docker 部署说明与 changelog 自相矛盾；许可不可商用。

## 2. Marshmallowc/Hailuo-AI-Short-Drama-Studio

- **定位**：FastAPI + React 的「LLM 导演 Agent + MiniMax API」短剧工作台，MIT。默认 `MINIMAX_MODEL=MiniMax-Hailuo-2.3`，有角色图时切到 `S2V-01`（旧版主体参考）。**尚未升级到 H3**，但它的导演提示词是目前最完整的中文短剧分镜 system prompt。
- **流程**：`generate_outline`（创意→大纲 + 角色，temperature 0.8）→ `generate_episode_detail_stream`（每集 30 个分镜，流式解析 JSON，强制 duration 6/10、resolution 1080P/768P）→ 可选 `analyze_script_rhythm`（「节奏审计师」打 0–100 分，标 hook 与「尿点」，检查黄金 3 秒）→ `submit_project_shots` 提交 → webhook 回调或本地 30 s 轮询 → 文件下载 → 导出。
- **大纲 system prompt 的短剧黄金准则（原文）**：
  > **前3秒生死线**：剧本开头必须有强力的动作或悬念直接切入。
  > **高密冲突**：每集必须包含至少 2 个小反转或 1 个重大冲突升级。
  > **强钩子结尾**：每集结尾必须留下诱导用户点击下一集的强悬念。
- **分镜 system prompt 的要点（原文摘录）**：极致超写实（模拟 Arri Alexa / RED 质感）；"禁止连续两个分镜都是静态对话。每隔 3 个分镜必须有一个中景/全景的大幅调度，或动作节拍的急剧转场"；每个分镜写 `first_frame` / `last_frame` / `action_beats`（`[0.0s - 1.5s]: 动作 A; [1.5s - 4.2s]: 动作 B`）/ `camera_meta`（焦段、光圈、Dolly/Pan/Rack Focus）/ `env_meta`；"严禁包含角色的 ID 或 UUID 字符串"。
- **借鉴**：大纲→分镜→节奏审计三级 Agent；action_beats 精确到 0.1 s 与 H3 的 `At 00:01.500` 时间码天然对应；回调 + 轮询双保险。
- **坑**：README 说 30 镜并行，代码却是顺序 `await`；分镜生成的 first_frame / last_frame / action_beats 字段**没有发给 MiniMax**，只发了 `prompt + camera_instruction`，等于白写；非流式接口 `.format()` 缺 `total_seconds` 会抛 KeyError；大纲里的"每集 N 分钟"被"30 × 6 s"覆盖。本项目的参考实现修正了这些问题。

## 3. chiphoton/MiniMax-H3-Codex-Drama

- **定位**：Codex 插件 + skills，把「故事/简报/参考包 → 成片」做成 Agent 工作流，本地 ComfyUI 跑开源 H3（Turbo LoRA 6 步）。61 star，MIT。
- **11 阶段流程**：① 故事/简报 → ② 解析 profile（`tiktok-short-drama`：9:16、15–90 s、目标 45 s、单镜 3–7 s、必须字幕；`commercial-ad`）→ ③ 角色与产品圣经 → ④ 场景母图 → ⑤ 分镜与关键帧 → ⑥ 为每镜路由到 T2V / I2V / R2V / Audio 工作流 → ⑦ H3 + ComfyUI 生成 → ⑧ 选 take（普通镜 1 个、关键镜最多 2 个）→ ⑨ 剪辑、配音、字幕、声音 → ⑩ 技术 QC + 视觉 QC → ⑪ 母版 + 可复现项目。引导模式在计划后与视觉事实源完成后各暂停一次。
- **视觉事实源依赖顺序**：重复出现实体的母图 → 场景母图 → 完整分镜 → 每个需要帧控制的镜头一张精确关键帧（GPT‑Image 生成）。
- **QC 策略**：`qc_media.py` 技术检查 + 联络表人工视觉检查（身份/产品/环境/连续性/字幕安全区/叙事）；"Technical pass with visual review still pending is not an overall pass"；硬门禁失败只重试一次。交付最小集：`final/master.mp4`、`media-info.json`、`qc-report.md/json`、`final-contact-sheet.png`、`edit/timeline.yaml`。
- **参数**：`width/height` 32 的倍数；`duration_seconds ≤ 15` 换算到 `17k+5` 帧网格 @24fps；Turbo `steps` 4–8 默认 6；R2V ≤ 9 图 + 3 视频 + 3 音频；FL2VA 与 REF2VA 权重不可互换。
- **示例制片人提示词（原文）**：
  > Turn this script and cast reference pack into a 60-second vertical short drama. Keep the plot and dialogue unchanged. Design missing locations and shot coverage, lock character continuity, then finish picture, dialogue, subtitles, music, and QC.
- **借鉴**：profile 概念（把平台规范固化）、QC 双层、可复现产物目录、"精确文字后期叠加"原则。
- **限制**：仅 768P（开源权重）；FFmpeg 为唯一剪辑后端；不下载远程 URL 参考；Turbo 需要额外节点包与 LoRA。

## 4. MiniMax-AI/MiniMax-H3 官方仓库与 skills

- 开源 H3 Base FL2VA / Ref2VA 权重、SGLang/vLLM/diffusers/ComfyUI 推理；README 强调 Context‑IR 对质量至关重要，自部署者需自建提示词改写层。
- **`h3-prompt-writing` skill**：可移植到任何 Agent 框架（`npx skills add https://github.com/MiniMax-AI/MiniMax-H3 --skill h3-prompt-writing`），内含 `base-en.txt`（三段式）与 `ref-en.txt`（六段式）两份写作指南——本项目 `docs/04` 的语法全部来源于此。
- **`3d-animation-short-generator`**（仅 MiniMax Hub 可用）：六列分镜表 `Shot ID & Duration | Continuity Handoff | Reference Anchors (Spatial + Identity) | Hook Type | Shot Description (Per-Second Directives) | Audio & Dialogue Track`；角色卡用 16:9 制作参考表；场景卡不含人物；"Strip all storyboard-only labels before video render"。
- **`music-video-subtitle-generator`**：超 15 s 用「多镜头分镜 + 尾/首帧续接 + 节拍硬切 + 全局母带音频对齐」；切点落在 1/4 或 1/8 拍。
- **借鉴**：直接把官方六列分镜表作为本项目 storyboard JSON 的字段来源。

## 5. ComfyUI 生态

| 项目 | 内容 |
|------|------|
| Comfy 官方 Partner Node（docs.comfy.org） | T2V / I2V(FLF) / R2V 模板，H3 Max 与 Max Turbo 变体；Prompt Enhance（Context IR 节点）与 Upscale to 2K（Regenerate 节点）布尔开关；"Generate at 768P if you plan to upscale" |
| wjluoxiao/ComfyUI-JZL-MiniMax-H3 | 「本地短剧一键生成」：故事 → 自动拆段 → 每段生成官方六段式 Ref2VA 提示词 + SCENE/VIDEO/AUDIO 槽位调度 → 「动作导演级」润色（攻防同步、力量链写全）→ 本地 GGUF 或在线 LLM 双后端 → 槽位名清洗/格式校验/逐段重拍兜底 |
| Larryvrh/ComfyUI-MiniMax-H3-Turbo | 6 步 Turbo LoRA 节点包 |
| badgids/ComfyUI-H3-ExactAudioLock | 多说话人定时音频混合与目标音频潜变量锁定 |
| qihanqihan-gif/ComfyUI-MiniMaxH3-Steering | steering / cache / prompt director 节点 |
| RunningHub 工作流「ki_MiniMax H3_多参分镜硬控流」「AITUDOU 全能参考 数字人 人物音频一致性」 | B 站教程配套的在线工作流，多参考图 + 音频一致性 |

## 6. 其他工具

- **wobushannes/Drehbuch--Referenzanker-Generator**：把要点和参考图转成**严格单行、带时间码**的 H3 提示词（`window1: (00:00.000–00:14.000) …`，14 s 一窗），锚点 `@Subject1_Name`、`@Building1`、`@Floorplan1`；每个人物附「反克隆」句 `unique facial structure corresponding 100% to reference image @Subject1_…, zero feature transfer from other actors`。本地 LM Studio 视觉模型分析参考图。
- **forgewebO1/awesome-minimax-h3-prompts**：20 条「可溯源」提示词，均标注来自 MiniMax 官方指南或官方 X 帖，包含竖屏吸血鬼短剧 teaser、武侠正反打、仙侠分镜等短剧向案例（见 `docs/04` §7.4）。
- **CARRYYOOAI/AutoVideo-MiniMax-Pipeline**：面向旧 Video‑01 的批量提交/队列/导出脚本，H3 时代仅作并发管理参考。

## 7. 对本项目参考实现的启发（已落地到 `pipeline/`）

1. 段落化分镜 JSON（火宝 + 官方六列表）。
2. 分镜字段 **全部** 进入提示词（修正 Short‑Drama‑Studio 的漏发）。
3. 官方六段式 / 三段式提示词构建器，`<Picture N>` 自动按 `content` 顺序编号。
4. 真正的异步并发 + 幂等 + 回调/轮询双模式。
5. 768P 草稿 → 选片 → 2K 重生成的两档成本策略。
6. FFmpeg 统一转码后 concat + SRT 字幕从分镜 JSON 自动生成。
7. 技术 QC（ffprobe）自动化，视觉 QC 留人工清单。
