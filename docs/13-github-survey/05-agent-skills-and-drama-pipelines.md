# 05 · Agent Skill 套件与短剧/漫剧全自动生产流水线

> 调研日期 2026‑11‑07。读法：对 26 个仓库全部浅克隆后读源码（SKILL.md、references、scripts、驱动 ComfyUI 的客户端代码、工作流 JSON 用 analyze.py 拆解），同时精读官方 MiniMax‑AI/MiniMax‑H3 的 9 个 skill（`h3-prompt-writing` + 8 个风格 skill，以 `3d-animation-short-generator` 为写法基准）。docs/09（Toonflow）与 docs/12 §9（OpenMontage）已写过，本文不重复。元数据取自 `data/relevant.json`。

## 本簇结论（10 行）

1. **立刻采用的「骨架」**：官方 `3d-animation-short-generator` 的写法（frontmatter + 全局风格锁 + STEP 0~8 每步一张「选择卡」+ `references/` 里放 shot-table-spec / qc-checklist / fallback-policy / model-selection）是目前最成熟的 skill 结构，我们的 skill 直接照它分文件。
2. **立刻采用的「驱动 ComfyUI」做法**：TFboy1 的 `scan → build(按 class_type 覆盖，不写死节点 id) → 参数表确认 → submit(/upload/image 再 /prompt) → monitor(/history 轮询 + 重试 + 断点)`，配 infinite‑creation 的 `/history + /queue 双查、连续 3 次都查不到即判丢失`。
3. **立刻采用的「一致性」做法**：每角色一张 16:9 设定板（左 1/3 脸部特写 + 右 2/3 正侧背三视图，白底，无文字）作为唯一 canonical 参考；场景出「无人母版 + 九宫格多机位」各 1 张；参考图总数守 9/3/3/12。
4. **立刻采用的「段缝」做法**：漫剧老李的「末镜 0.5 s 收束窗 + 末 1 s 整秒硬定格 → 剪掉定格秒 → 截末帧当下一段首帧/参考 → 下一段首镜 0 级同档景别起手」，加 dramake 的「尾帧只传短期状态，长期母版每段必带」。
5. **立刻采用的「QC」做法**：chiphoton 的 `qc_media.py`（ffprobe + 全解码 + blackdetect 0.25 s + freezedetect 1 s + loudnorm I=-14/TP=-1.5 + 4×3 联络表）+ qiukaihui 的失败码表（F‑COUNT / F‑ID‑DRIFT / F‑LIPSYNC…每轮只改一个变量）。
6. **试用**：infinite‑creation（本地 ComfyUI 全自动「小说→成片」，Node 22，工作流规格 roles/media/prune 的注册方式值得借鉴但工程重）；comfyui‑auto‑drama（零依赖 Python 控制台 + 链式续接守护进程 + 「起始音节」自动裁剪）；h3lite（W4A8 低显存路线与 4090 不对口，但 anchor sheet、face‑quality 路由、WDDM 显存假空闲诊断可用）。
7. **只借规则不装**：漫剧老李（187 KB 主 SKILL、Seedance 优先、H3 只是「格式支线」，但 h3‑adapter / segment‑splicing / 取材策略写得最细）；dramake（CSV 台账与四道门）；senmanx（漫剧风格总表、敏感词替换、台词字数/秒）；suihe1（production.json 哈希审批、ffmpeg 粗剪 QC）。
8. **观望**：TapCanvas / reveric / cwp‑cwp ai‑video / zxcHolmes studio / iv‑studio / Codex‑Drama 的 MCP 路线——都是「平台 + agent」重工程，TapCanvas、reveric 走云 API（Seedance/鲁班），不是本地 ComfyUI；iv‑studio 源码不在仓库里。
9. **别碰**：killkli / dseditor（Colab 路线）、joeVenner（官方云 API）、okaypic（第三方付费 API）、gary149（游戏精灵）——与「本地 4090 短剧」无关，只抽 1–2 条写法。
10. 全簇**没有一个**项目把「抽卡→VLM 评分择优」在本地 ComfyUI 上完整跑通并开源评分器：video‑agent 的 QualityJudge 需要外接 VLM，iv‑studio 的 ranking（听清台词 × 相似度 × 不冻结 × 相对清晰度）源码未开源，qiukaihui 只对图片资产做 VLM 质检。这是我们 skill 可以补的空白。

---

## 一、官方基准：MiniMax‑AI/MiniMax‑H3 的 skill 写法

读了 `skills/README.md`、`h3-prompt-writing/SKILL.md`（40 行）、`3d-animation-short-generator/SKILL.md`（249 行）+ `meta.yaml` + 5 个 references（shot‑table‑spec 75 行、storyboard‑guidelines 185 行、qc‑checklist 99 行、fallback‑policy 52 行、model‑selection 49 行）。

**目录结构**
```
<skill>/
  SKILL.md            # frontmatter: name / description(含 Use when… Not for…) / compatibility
  SKILL.cn.md         # 中文镜像（8 个风格 skill 都有）
  meta.yaml           # display-name-zh / version / tag / summary-en|cn / desc-en|cn / author / source
  agents/openai.yaml  # 仅 h3-prompt-writing：interface.display_name / short_description / default_prompt
  references/*.md|txt # 规格书，SKILL.md 正文只写「最小运行契约」+ "Required reference: read X"
```
`compatibility` 字段明确声明「需要 MiniMax Hub agent（canvas、choice card、hub_generate_*）」或「可移植到任何能读本地文件的 agent」——我们应照抄这个字段写「需要本地 ComfyUI 0.37+、MiniMaxH3 核心节点、ffmpeg」。

**阶段划分（3d‑animation）**：STEP 0 intake（立刻弹两张卡：画幅、总时长）→ 1 项目简报 → 2 故事大纲（6 条 gate check）→ 3 角色卡（16:9 设定板，带标签）→ 4 场景卡（只许环境，禁任何人）→ 5 六列标准镜头表 → 5.5 自检门（6 项硬检）→ 6 文本分镜文档（默认）/铅笔分镜（可选）→ 7 选模型 + 选分辨率卡 → 单镜生成 → 8 拼接 + BGM → 9 终审。**每个停点都是一张选择卡，推荐项放第一，用户说「继续」= 选推荐项。**

**六列镜头表**（可直接作为我们 shot‑table schema）：`Shot ID & Duration` / `Continuity Handoff`（上接下传）/ `Reference Anchors`（Fixed Landmarks 带屏幕位置、Character Positions 带朝向、Exited Character Status、Lighting Baseline + 绑定的角色卡/场景卡名）/ `Hook Type`（受控词表）/ `Shot Description (Per‑Second Directives)`（每秒 5 要素：动作表情、运镜、空间、音频、交接）/ `Audio & Dialogue Track`（Narration / Dialogue / SFX / Performance Note，旁白时 `narrator-mouth-closed: true`）。

**5.5 自检六项**：钩子密度（每 3 镜至少 1 个 reveal/reversal/callback，首尾镜强钩子）；单镜 ≤15 s；单镜重要角色 ≤3；室内多镜地标与光照继承或写明变化；每秒指令无空洞；连读 Continuity Handoff 成链，翻转要标 `HARD CUT — time skip`。

**fallback 阶梯（H3）**：① 引用镜头表 Reference Anchors 原文重试 → ② 镜头缩到 ≤6 s 并拆行、重跑自检 → ③ 换模型（我们对应：换 FL2VA/Ref2VA 路线或换 seed/步数档）→ ④ 三次失败弹卡问用户（放宽/跳过占位/手工给参考视频）。

**资产纪律**：任何重生成后，下游一律指向最新版本，画布上多版本要点名；禁止静默混用新旧；存储板上的 `[char:…] [scene:…]` 双绑定标签在出片前必须剥离。

**h3‑prompt‑writing**：只有 40 行，核心是「读 base‑en.txt / ref‑en.txt，保留字段名、顺序、标签与时间记法；正文英文，台词/歌词/画内文字保原文；总时长 4–15 s 与描述匹配」。所有社区项目都在这两份 txt 之上叠规则。

---

## 二、逐仓库

### lixiaoxiao9888-create/manju-laoli-skill（★1952，MIT，2026‑10‑21）
- **定位**：「漫剧老李」V7.4.26，1 总控 + 12 子技能（sd‑script/asset/storyboard/combat/xuanhuan/real/jieshuo/overseas/recon/decision/feed/qc‑engine），164 个文件、50 份规则库。面向 OpenClaw/Coze/Dify/WorkBuddy，**Seedance 2.5/2.0 优先，H3 是「A 锁」下的格式转换支线**（七段式 → H3 三字段/六段式）。本包**不持有图、不调用任何生成工具**，只产提示词 + 接线单（M0/M1/M2 素材形态）。
- **结构**：总控 SKILL.md 187 KB（超长，靠「唯一权威归属表」把 50 份 reference 分权），每个子技能 `SKILL.md + references/ + scripts/`；scripts 全是**校验器**：`validate_prompt.py`（Seedance 侧 C1~C32，H3 侧 H1~H12）、`gate_check.py`（投喂六道闸门：含语速、图数上限按模型分档 H3≤9/2.5≤30）、`check_p45.py`（预演故事板）、`validate_seedance_segment_map.py`。
- **六道前置锁**：赛道 / 素材来源 / 模型版本 / 画幅 / 交付形态 / 段缝衔接方式（① 末帧定格承接 ② 换机位硬切 ③ 空镜过渡 ④ 技巧转场）+ I 画风锁（推 4 张候选卡，含「按你的推荐走」，选定即冻结）。**任何一道未选都停下问，禁止默认**。
- **h3‑adapter.md（24 KB，2026‑10‑02 对照官方 live 文件逐字复核）**关键条：六段正文一律英文，`<d>[Chinese] …</d>` 保台词；切镜只用官方短语 `the camera cuts to / the shot cuts to / transitions to / changes to / switches to`（中文「镜头切至」会被做成叠化融脸）；画外声固定公式 `<Subject N> (Sx) says in an off-screen voiceover: <d>…</d> while his lips remain completely closed.`；**同性别多说话人必崩（官方 issue #17）**→ 声学画像反着写、一段一开口者、清理 chuckle 类非对白人声、声音只前进不回头；否定句不进正文（词根会被渲染）；`[Shot 1]` 单一具名主体，禁「X 与 Y 同框」句式；`retention_analysis` 内不写 `(Sx)`；`summary` 段首任务前缀 `keyframe completion / reference generation / video continuation / audio reuse`。
- **9 张取材策略**：① 首/尾帧锚图 → ② 主角 4 View 板（1 板=1 槽）→ ③ 场景母版 + **九宫格（1 张=9 机位=1 槽）** → ④ 配角 → ⑤ 道具拼板 → ⑥ 动作参考视频 ≤3 → ⑦ 音色音频 ≤3（必须伴图/视频）；超限的降级为文字写进 `<Subject N>` 定义行；定义了不引用 = 白占槽（H5 告警）。
- **segment‑splicing.md（57 KB）**：模型每段零记忆；不变数据（角色/场景图）每段重投，可变数据（站位/姿态）段缝换挡；**尾帧锚定法三步**：末镜「0.5 s 收束窗 + 末 1 s 整秒硬定格（剪辑时整秒剪除）」→ 直接截上一段真实末帧作下一段首帧/参考（取消「重画段缝图」）→ 下一段首镜 0 级同档景别起手；末镜以中全景/中景为主、禁大远景（脸太小做不了参考）；末帧可截四要件（人在场/朝向可用/锚点可见/无压屏）；**背景锚点锁**（锁的是人与背后参照物的相对关系，不是坐标）；末帧不可用时首选「反向重设计上一段末镜」。
- **价值**：H3 提示词硬规则与段缝规程是全簇最细；台词语速表（耳语 2.5–3.5 字/s、标准 3.5–6、争吵 5–6，标点停顿 ，0.2 。0.4 …0.8）可直接入 skill。
- **坑**：总控太长不可能全装进上下文；Seedance 体系术语（七段式、@CHR 锚点、C 系机检）对 H3 项目是噪音；赞助位/招商文案多。
- **评级**：只借规则（h3‑adapter、segment‑splicing、gate_check 语速逻辑、九宫格），不装包。

### suihe1/short-drama-production（★194，Apache‑2.0，2026‑09‑16）
- **定位**：AI 短剧「生产总控」skill（Codex 优先，有 `agents/openai.yaml`），默认 16:9；下挂 novel‑outline / novel‑characters / novel‑art / novel‑script / novel‑storyboard / short‑drama‑director 六个专业 skill + 官方 h3‑prompt‑writing 快照。**生成走 MiniMax 官方 API 或 CompShare**，不驱动 ComfyUI；但其状态机、schema、粗剪 QC 与本地路线无关，可直接复用。
- **结构**：根 SKILL.md 8 KB 只做路由（「按需读取」表 → 14 份 references）；`scripts/*.mjs` 是 Node 工具：`production-kit.mjs init/status/validate/register/refresh/approve/render`、`post-kit.mjs plan/preflight/assemble/qc`、`storyboard-bridge.mjs`、`reality-audit.mjs`、`doctor.mjs`、`offline-demo.mjs`；有 `.github/workflows/offline-tests.yml`。
- **production.json 合同**：`project.format{aspectRatio,deliveryWidth/Height,fps,generationResolution 768P|2K,targetModel}`；`policies{batchEpisodes:3, pilotJobs:1, contextIrPolicy off|pilot|selective|on, paidGenerationRequiresApproval}`；`artifacts[]{id,kind(source|outline|cast|art|script|director|storyboard|frames|video|audio|edit|qc|delivery),dependsOn,status(planned|working|review|approved|stale|missing|blocked|failed|skipped),sha256,approvedSha256,approvedDependencyHashes}`；`voiceAssets[]{sampleType,rights,licenseScope evaluation-only|commercial,provider}`；`jobs[]{mode h3-ref2va…,duration(4–15 整数),sourceDurationSeconds,durationAdjustmentSeconds,ratio(Ref2VA 继承画幅，I2VA/FL2VA 必须 adaptive),references[{role reference_image|reference_audio}],speakers[{characterId,speakerId S1,voiceAssetId}],dialogueRoute h3-native-reference|h3-native-free|tts-guided-h3|tts-post|silent,experiment{changedVariables}}`。**上游哈希变了下游自动 stale，必须重新审批。**
- **storyboard.json**：集 → 段（一次生成，≤15 s，不跨场次）→ 分镜 cut（2–5 s，`beats` 唯一认领剧本节拍，`camera` 直接用 H3 官方词表字符串，`size` 五档，`information.displayStrategy contextual|insert|full-frame-content|post-composite`，`exactText:true` 必走后期合成）；段 id `E01-01` 即素材文件名。
- **导演包→技术分镜**的偏差记录 schema（`deviationId/sourceShotId/fields/reason/original/change/dramaticImpact/approvedBy`）与「必须记录偏差」清单（景别变、越轴、台词转画外、时长变 >15%…）。
- **post‑and‑qc.md**：样片要选「最能暴露问题」的片段（主角正脸 + 一句中文对白 + 一次有动机运镜 + 手部道具 + 可判光照）；技术/视觉/声音三类验收项；问题等级 critical/high/medium/low，每条关联集‑时间码‑任务 ID‑根因‑修复层级（资产→剧本→分镜/提示词→重生成→后期）；post‑kit 只收 `status=succeeded`，多候选必须 `--select-file takes.json` 不自动选最新，contain‑pad 统一到交付尺寸 24 fps 48 kHz，执行前核 SHA‑256。
- **价值**：状态机 + 哈希审批 + 声音资产版权字段是全簇最严谨的「工程合同」。
- **坑**：Node 脚本、API 路线；无 ComfyUI 适配；`reality-audit` 面向现实题材偏重。
- **评级**：借 schema 与 QC 清单（试用其 post‑kit 思路，自写 Python 版）。

### TFboy1/oh-my-minimaxh3-director（★163，MIT，2026‑08‑16）
- **定位**：Codex skill，**真正驱动本地/远程 ComfyUI** 的全自动流水线：剧本→分镜（WenWu 导演引擎）→人物四视图→H3 提示词（official/wenwu/hybrid 三模式）→工作流构建→参数确认→批量提交/监控→剪映拼合。中文为主，另有 EN/JA/FR/DE README。
- **结构**：`SKILL.md`（阶段 0–5 + 失败恢复 + 脚本速查）、`references/`（setup‑guide / storyboard‑schema / workflow‑routing / wenwu‑director / hybrid‑example / cloudflared / autodl / resource‑monitoring / api‑and‑mcp）、`assets/templates/{ref2va,t2v,i2v}.json`（API 格式）、`scripts/` 10 个 Python（probe_comfy / ensure_cloudflared / scan_workflows / convert_ui_workflow / build_workflows / submit_jobs / monitor_jobs / generate_assembly / check_hardware / monitor_resources）、`evals/evals.json`。
- **项目目录**：`storyboard.md + storyboard.json + prompts/seg_XX.txt + workflows/seg_XX_api.json + jobs/params.json + jobs/seg_XX_job.json + clips/raw/<batch>/ + edit/`。`storyboard.json`：`meta{aspect:"16:9 (Widescreen)",megapixels:0.4,duration_default:10,default_steps:8,default_seed,prompt_mode,prompt_mode_reason,workflow_map}`、`characters[]{refs{front,side,back,face}}`、`segments[]{id,duration 5–15,mode,template,refs[],first_frame,last_frame,dialogue[],prompt_file}`。
- **驱动 ComfyUI（源码级）**：铁律「优先复用用户已有工作流，禁止自创」→ `scan_workflows.py` 扫描并标注 API/UI 格式、模式、参考槽位、Turbo 标记；`build_workflows.py` **按 class_type 覆盖**（`PrimitiveStringMultiline.value`/H3 节点 `prompt`、`LoadImage.image`、`ComfyMathExpression→PrimitiveFloat` 时长、`BasicScheduler.steps/scheduler`、`RandomNoise.noise_seed`、`ResolutionSelector.aspect_ratio/megapixels`、`SaveVideo.filename_prefix=<项目>/<模式>/seg_XX`），后端校验 duration 5–15 / steps 4–40 / seed / 参考图存在 / 六段齐全；UI 格式工作流拒绝并要求 `convert_ui_workflow.py --object-info-url` 转换，**绝不改写用户文件**；`submit_jobs.py` 先 `POST /upload/image`（multipart，`type=input`，`subfolder=<项目>/refs`，同批缓存去重，重试 `overwrite=true`）再 `POST /prompt`，`node_errors` 非空即中止；`monitor_jobs.py` 轮询 `/history/{prompt_id}`（默认 30 s），`status_str=error` 提取 `execution_error` 的 node_id/node_type/exception_message，重试上限 2，完成后从 `/view` 分块下载到 `.part` 再改名；状态落盘可续跑。
- **模板参数**（analyze.py）：ref2va 用 `minimax_h3_ref2va_pruned_int8_convrot` + `qwen3vl_32b_int8_convrot` + `res_multistep/simple` **4 步** + `LoraLoaderBypassModelOnly` + `PathchSageAttentionKJ` + `TESpeedMiniMaxH3`；t2v 用 `MiniMaxH3TurboLoRA(minimax_h3_turbo_4step_ema_ckpt500)` + `MiniMaxH3TurboSampler` 6 步。与我们 4090 环境同一套组件。
- **其它亮点**：阶段 3.5「无人值守确认」（约定关机时间，`monitor_resources.py` 显存 90% 警告/95% 停）；分镜汇报必须「几秒到几秒→什么画面→什么对白」；每段默认 10 s 内含 2–3 镜，镜间至少传一个锚点（动作方向/视线/光/道具/轮廓/声桥/受力）；hybrid 模式 = 官方六段外壳 + WenWu 逐秒镜头脉冲 + 结尾 `constraints:` 块。
- **坑**：模型下载指向 ModelScope（用户不能用，换 HF）；剪映拼合依赖 `jianying-editor` 第三方 skill 与 Windows 剪映 ≤5.9；hybrid 正文含中文时与官方「全英文」口径冲突（它自己也说 detailed_description 用英文）。
- **评级**：**采用**（脚本层直接改造：换 HF 链接、去掉剪映改 ffmpeg、模板换成我们的 int8+Turbo+Sage 工作流）。

### SwotAtmk/infinite-creation（★266，MIT，2026‑11‑06）
- **定位**：Next.js 15 + 自研 ReAct Agent 的本地工作台，「上传小说/剧本 → 本地 ComfyUI（H3 Ref2VA + Qwen‑Image 2.1 + Krea2 + Qwen3‑TTS）→ 不限时长成片」，无人值守、断点续跑、分镜级重做；`skills/` 内置 50+ SKILL.md（含官方 8 个、漫剧老李 13 个、自家 novel‑to‑video / story‑pipeline‑cn / image‑prompt‑writing / tts‑voice‑design / h3‑prompt‑writing 改版）。Node ≥22、pnpm、Bun、ffmpeg。
- **四阶段调度**：`llm`（圣经/风格/资产提示词/分镜/视频提示词）→ `image`（人物三视图/场景/道具/服装与年龄变体）→ `tts`（每角色 voice_ref）→ `video`（逐镜 r2v + ffmpeg 合并）。`novel-to-video/SKILL.md` 硬性约定：全程不问用户；幂等（有 video_path 且 done 则跳过）；每角色**一张 canonical 参考图**跨镜复用；**只给「有台词」角色传音色，单镜音频 ≤3**；分镜按「长镜头聚合」（同场景连续动作 + 多句对白合一镜 2–15 s，`sub_shots` 时间轴承载节拍，禁一句一镜）；画面禁任何文字字幕水印；换装/年龄走子资产（`category=costume|age`，`parent_id` 指向角色，优先级 服装 > 年龄 > 原图）。
- **驱动 ComfyUI（`lib/core/comfyui.js`）**：`uploadToInput → /upload/image`；`queuePrompt → /prompt {prompt, client_id}`；`generate()` 开 WebSocket `/ws?clientId=` 只用于 progress/execution_error 显示，**完成判定靠每 1.5 s 并行查 `/history/{id}` + `/queue`**：history 有记录即完成（`status_str=error` 且 messages 含 `execution_interrupted` 单独标「被中断」），既不在 queue_running/pending 又无 history **连续 3 次**才判「任务丢失」（防 ComfyUI 重启后傻等），超时临界再复查一次；取消时本地后端直接 `/interrupt` + `DELETE /queue {delete:[id]}`，云端并发 >1 只删排队项；所有 fetch 挂 `AbortSignal.timeout`（poll 15 s、queue 30 s）；提交失败必须关 WS 防连接泄漏。
- **工作流规格（`workflow-specs.js`）**：每个工作流一份 spec：`roles{positive_prompt,seconds,resolution(map '16:9'→'16:9 (Widescreen)'),seed,filename_prefix…→{node,field}}`、`media{targetNode, loaders{image:LoadImage.image, audio:LoadAudio.audio, video:LoadVideo.file}, reusePool, maxImages:9, maxAudioVideo:3}`、`outputs`、`prune`（删模板里硬编码的占位参考/LLM 改写链）。r2v 模板是 `MiniMaxH3Easy` 节点（mode=reference，`reference_mention_mode=index`，提示词用平铺 `__MINIMAX_H3_REF_N__` 标签，不认 `<Picture N>`）；>768P 走「768P 首遍 + `MiniMaxH3EasyLatentUpscaler3D` 线性超分」二采 spec。
- **参考装配（`refs.js assembleShotReferences`）**顺序：人物图（服装/年龄变体优先）→ 场景图 → 道具图 → 说话角色音色（名字规范化精确匹配，一行多说话人会匹配失败并告警）→ 显式绑定音频；音频不存在直接跳过（避免 LoadAudio Invalid audio file 整图被拒）。`MAX_SPEAKERS_PER_SHOT = 2`（≥3 人对话必须拆镜）。
- **调度**：本地 ComfyUI 整批串行（`render-gate.js` 两级闸门：任务级独占 + 渲染槽位），纯 LLM 阶段也过闸门（27B 常驻显存会和渲染抢卡）；`scheduler.js` 可重试错误按 15 s×2^n 退避（上限 10 min）；阶段前查 `/system_stats` 空闲显存不足即抛错。
- **价值**：ComfyUI 客户端的健壮性细节（丢失检测、中断区分、WS 泄漏、取消策略）是全簇最好；工作流 spec 抽象可作我们 `references/workflow-spec.md`。
- **坑**：工程重（5800 文件）、Next.js/Bun；用 MiniMaxH3Easy 第三方节点而非核心节点；默认 Qwen‑Image 三视图布局「左 1/3 脸部特写 + 右 2/3 正侧背」是它的 `CHARACTER_T2I_LAYOUT_CONSTRAINT` 常量。
- **评级**：试用（跑一次看全自动质量）；客户端逻辑与 spec 设计直接吸收。

### qiukaihui/comfyui-auto-drama（★73，MIT，2026‑10‑22）
- **定位**：Python 标准库零依赖的 Web 控制台（`console/batch_console.py` 4757 行）+ 链式守护进程（`chain_daemon.py`，20 s 一轮），远程 ComfyUI 跑 H3 T2V/I2V/R2V，LLM（LM Studio/云）写剧本与提示词，Boogu/云生图出资产，VLM 质检资产图，8 步流程：建项目→脚本→改写→规范提示词→参考资产→预览确认→提交→记录导出/合成。规则文件 `console/rules/*.md` 可热改。
- **驱动 ComfyUI**：`build_api_graphs.py` 从 `r2v_api_template.json / i2v_api_template.json` 构图；**steps ≤8 自动插入 `MiniMaxH3TurboLoRA` → `MiniMaxH3MemoryEfficientSageAttentionPatch`**（UNET→LoRA→Sage→Guider/Scheduler）；提交 R2V 前检测服务器是否加载 Ref2VA 权重，缺失回退 FL2VA 并提示「身份锁定弱」；任务 id 版本化（v2/v3 自动接序）；`F-DUP-SUBMIT` 拦截同任务重提。
- **链式衔接（`advance_chain`）**：上一段完成并下载后 `ffmpeg -sseof -0.1 -frames:v 1` 抽末帧，上传为 `chain_<id>.png`，下一段改成 I2V 提交；**上一段失败则回溯找更早成功段末帧续接，再不行降级 T2V**，链不断。R2V 六段式包装（`to_ref2va_six_section`）把链帧写成 `<Picture N> 是上一段末帧，作为第 0.00 秒首帧（keyframe completion）`，分镜图写成 `storyboard: weak_reference 仅参考构图机位站位`。
- **h3_expand.md 规则（中文正文三段式，R2V 提交时自动转六段）**：画面描述七层——「画面中恰好 N 名角色各出现一次」精确人数正向锁 → 身份/发型/服装与资产状态表**一字不差** + 「参考图只继承身份发型服装，排除姿势构图背景光线」(inherit/exclude) → 空间与数量（屏幕左右、唯一道具、无倒影无重复角色）→ 动作因果（触发→准备→发力→接触→反作用→落定）→ **摄影机三件套（起点构图 + 一个主运动 + 终点构图）**，承接段开头写「承接上段末帧：位置/手部/视线/服装」、结尾写「尾帧：…」→ 光色材质 → 连续性三栏 must_hold / changes_here / must_not_appear；对白 `(S1)(S2)` 按剧本角色表固定全片不换号，`<d>` 内只放纯台词；拟音禁「啪/砰/轰/炸/爆」（会触发爆炸视觉）；`non_diegetic_music: N/A`。
- **资产 VLM 质检**：角色锚点图/侧面/背面/脸部特写/场景/分镜图各一套 JSON 提问（性别、发型服装与设定一字不差、无多余肢体/重复人物/文字乱码/现代物品；场景必须无人；分镜图「严格只有 N 个人」），服务不可用则保守放行并标注。资产状态机：有质检通过记录才进位。
- **「起始音节」裁剪**：H3 输出开头常有 0.02–0.15 s 短促人声，`detect_lead_syllable` 用 16 kHz 单声道 RMS（20 ms 窗）：前 0.6 s 内有 >1500 的高能段且 <0.3 s，之后连续 0.2 s <800，再有真语音 → 在低能间隙起点裁掉（0.02–0.8 s），音画同步 trim。
- **失败码表**（`failure_codes.md`）：F‑SUBMIT‑API/RESP、F‑DUP‑SUBMIT、F‑LOST、F‑TIMEOUT、F‑ASSET‑QA、F‑ID‑DRIFT、F‑STATE‑DRIFT、F‑REF‑SCOPE、F‑COUNT、F‑DUP‑SUBJECT、F‑PROP‑DUP、F‑ACTION‑OVERLOAD、F‑CAMERA‑CONFLICT、F‑CAMERA‑PATH、F‑DIALOGUE‑TEXT/TIME、F‑LIPSYNC、F‑DIALOGUE‑VISUALIZED、F‑AUDIO‑MIX/POLLUTION，每条给责任层与最小修复；**每轮只改一个变量，同一错误连续两批无改善就回上层不再抽卡**。
- **坑**：CLIP 默认 nvfp4_awq（我们已有），生图走 Apple Silicon Boogu 或云端；中文正文与官方英文口径相悖（作者说「用户需要看懂」）；单文件 4700 行难维护。
- **评级**：试用（链式守护 + 失败码 + 起始音节裁剪三个点直接搬）。

### JGRFW/comfyui-AICG3D（★478，GPL‑3.0，2026‑11‑04）——只看 agent/skill 编排
- **定位**：ComfyUI 插件「短剧工作台」，无限分段生成（续接机制由另一人负责）。本簇只看 `aicg3d/skills.py`、`prompt_split.py`、`prompt_guides/`。
- **skill 机制**：`prompt_guides/` 一个子目录 = 一个「提示词方案」（`guide.md`/`guide-zh.md`/`SKILL.cn.md` + `references/` + 可选 `meta.json{id,name,name_zh,languages}`），`manifest.json` 固定官方 8 个方案 id 与「H3 通用 / base / ref 参考」三份公共规则；`skills.py discover()` 扫目录读 frontmatter，`skill_id` 给多轮对话节点、`guide_id` 给 H3 主节点；**运行时 = H3 General + 模式参考（base/ref）+ 至多一个场景方案**。`ADAPTATION_NOTES.md`：把官方 skill 改成节点可用时「只删 Agent 运行时动作（工具调用、画布、审批等待、拼接交付），一字不缩写提示词知识」。
- **分段解析节点（`prompt_split.py`）**：把整篇分段剧本按「第N段（5秒）/ 镜头N / Shot N / 分隔线 / 空行」切成 ≤64 段，秒数「跟随文本标注/固定/不改」，一键填入各段落节点并可顺序写 seed。
- **自带社区 skill**：`H3高密度打斗/high-density-fight-prompt`（15 s 一镜到底打戏模版 v1.4‑MM：19 个变量槽、八拍节奏、只输出提示词本体）、`phone-vlog`、`light-fresh-short-film`、`eastern-megastructure-director`、`digital_human_audio_performance`。
- **价值**：「skill 知识 vs agent 动作」的拆分原则，以及把 skill 文件夹直接当 ComfyUI 节点下拉选项的发现机制。
- **坑**：GPL‑3.0；提示词优化在节点内调 LLM，和我们 agent 侧写提示词重叠。
- **评级**：观望（续接部分另文评估）；借 ADAPTATION_NOTES 原则。

### Rimagination/h3lite（★473，MIT，2026‑08‑23）
- **定位**：Codex skill，「硬件感知」的 Windows+NVIDIA 本地 H3 工作站：doctor → planner → preflight → fastpath 一键生成；主验证路线是 **W4A8 低显存**（4060 Ti 16 GB），组件集 A/B 必须原子选择；Linux/macOS 标为未验证。`references/` 11 份、`scripts/` 11 个 Python、`tests/` 6 个。
- **可用部分**：`agent-workflow.md` 的生产契约 `intent route → anchor sheet → 5 遍提示词增强 → execute → verify`；**anchor sheet**（每个参考记录 Role / Retention / Allowed change / Forbidden drift，`h3_anchor.py` 只记元数据不改提示词）；`face-quality.md` 路由（物体/风景 T2VA；单镜可辨认人物 I2VA 清晰首帧单人正脸或 3/4；跨镜同一人 Ref2VA；首镜一个人、眼鼻嘴发际可见、先验无对白人脸稳定再加口型；**零推理开销约束**：人脸模式不许加步数/第二模型）；`director-sequences.md`（单次 H3 = 一个连续镜头，shot/reverse‑shot 必须拆段分别 I2VA 再 ffmpeg 拼；OTS 遮挡镜头首帧必须带参考图生成否则 H3 会发明新身份；角色描述逐字一致 `Man A / Man B` 不改名；W4A8 下「真实毛孔」变砂纸，改写 `smooth refined skin, fine pores, not plastic`）；`gpu-contention.md`（WDDM 下 `nvidia-smi` 进程显存 N/A、PyTorch free 虚高，`h3_vram.py` 读 `\GPU Process Memory(*)\Dedicated Usage` 计数器做门禁）。
- **脚本**：`h3_generate.py` 组件完整性校验、模型名解析、LoRA/加速节点配对校验、参考图绑定/占位校验、音频策略、run manifest + 提交占位锁（防重复提交）、`bypass_block_cache`。
- **坑**：组件集是 W4A8 + Qwen3‑VL 4B，不是我们的 int8 + 32B；百度网盘分发；`32 像素对齐`、`640×352` 等参数不适用 4090。
- **评级**：观望；借 anchor sheet / face routing / 显存诊断。

### SlavaSexton/ComfyUI-Agent-Kit（★118，Apache‑2.0，2026‑11‑02）——只看 H3 skill 与驱动方式
- **定位**：给 Claude Code / Codex / Gemini CLI / Qwen Code 的通用 ComfyUI skill 包（`claude-code/skills/comfyui` 大手册 + `minimax-h3` + `krea` + `seedance` 子 skill），`.mcp.json`，安装脚本。
- **minimax-h3/SKILL.md**：区分「托管 API 节点 `MinimaxHailuo03*`」与「本地核心节点 `MiniMaxH3ImageToVideo / ReferenceToVideo`（`comfy_extras/nodes_minimax_h3.py`）」；强调本地没有 Context‑IR，必须自己写成改写器输出形；基础三字段 vs Ref2VA **六段**（字段名是 `retention_analysis` 不是 `retention`，核心节点不校验格式）；本地 `MiniMaxH3ReferenceToVideo` 有**四组 Autogrow**：`ref_images`(9)/`ref_videos`(3)/`ref_video_audios`(3，参考视频自带音轨)/`ref_audios`(3)；**`length` 必须落在 17k+5 帧网格**（73≈3 s、124≈5 s、362≈15 s）；原生约 1 MP，模板 1344×768；症状表：胡言乱语=台词没进 `<d>[lang]`，脸漂=没 `<Subject N>` 绑身份源或超分后参考尺度错，超分后音频糊=`audio_denoise` 留 1.0，人群里动错脸=`ref_image_size` 用了 match 而该用 max。
- **驱动方式**：`comfy_client.py` 极简：`POST /prompt` → `GET /history/{id}` 每 2 s 轮询 → `/view` 下载；`apply_overrides` 按节点 id 覆盖。另有 `tools/fetch_workflow.py`、`node_inventory.py`、`workflow_layout.py`。
- **价值**：症状→原因表和 17k+5 网格、四组 Autogrow 这几条硬事实写法精炼，可直接入我们的 troubleshooting reference。
- **评级**：借条目；不装（大手册面向全模型）。

### agent-next/video-agent（★116，Apache‑2.0，2026‑10‑10）
- **定位**：「OpenVideo = Ollama for video」，CLI `open-video pull/status/run` 驱动 ComfyUI（Linux/WSL2，RTX 5090 开发），`skill/h3-video`（默认）与 `skill/open-video`（实验的导演路径 plan→judge→stitch）。
- **源码级**：`core/validator.py` 模式感知硬校验（三字段必在；4–15 s；I2V/FL2V/L2VA 缺对齐行告警；R2V 9/3/3/12 且音频不能唯一；`At MM:SS.mmm` 严格递增且 ≤时长；`<d>` 必带 `[lang]` 且闭合），`--strict` 时告警也失败；`core/judge.py QualityJudge`：ffprobe 数帧 → 抽 5 帧 → 外接 VLM 回 `{score,missing_elements,artifacts,motion_quality,incoherence}` → PASS(≥0.7 且无 issue)/REFINE/FAIL，无 VLM 诚实 SKIPPED(0.0) 不假 PASS；`pipeline.py` 每镜 `OPEN_VIDEO_JUDGE_RETRIES`（默认 1）次 REFINE 重生成换 seed 保留最高分 take，FL2VA 链用 `Stitcher.extract_last_frame`；`backends/h3/PROMPT_GRAMMAR.md`。
- **BEST_PRACTICES（5090 32 GB）**：1344×768 多倍 32、20 步（15 下限、25 边际）、`res_multistep + simple`（R2V 用 beta/normal）、shift 12/3（标 ⚠️ 社区继承未官方证实）、CFG 蒸馏无负面词、`ref_image_size match` 快 / `max` 身份强、**5090 避开 nvfp4 文本编码器**（ComfyUI #14157，或 `EXTRA_RESERVED_VRAM` 加到 +4 GB）、Sage ≈2×。
- **设计原则**（抄自 Seedance 生态）：skill 模块不做单体；先路由模式再验约束；硬校验器就是自我修正循环；参考包 > 模型选择；成本 = 像素 × 重生成次数。
- **坑**：Linux 优先、Windows 只 WSL2；judge 需 `OPEN_VIDEO_VLM_URL/MODEL/KEY`。
- **评级**：借 validator 与 judge 结构（我们本地用 Qwen3‑VL 做 vision_fn 即可补齐）。

### chiphoton/MiniMax-H3-Codex-Drama（★60，MIT，2026‑09‑28）
- **定位**：Codex 插件市场（4 个插件：制作插件 10 个 skill + `h3style` 官方 skill 伴侣 + `privacy` 本地媒体工具 + `canvas` 网页工作流引擎），通过 `.mcp.json` 启动 `comfyui-mcp@0.49.3 --comfyui-url http://localhost:8188`。skill：adviser / audio / comfyui / drama‑producer / frame‑to‑video / profile‑distiller / reference‑to‑video / text‑to‑video / video‑editor / qwen‑image‑edit。
- **drama‑producer**：`guided`（每次一问，**production‑plan 批准 → visual‑lock 批准**两道门）/`fast`（记录假设不问）；Profile 体系（`base-video` + 一个 primary，如 `tiktok-short-drama` JSON：9:16、15–90 s、required_beats hook 0–8% / setup / escalation / payoff / value‑tag 90–100%，shot 3–7 s，key_shot_classes，takes ordinary 1 / key 2 / max 2 / technical_retries 1，captions 安全区 top 12% bottom 18%，-14 LUFS/-1.5 dBTP，transition ≤0.25 s；`profile_tool.py` 解析继承）；11 个 stage（preflight / init / ingest / plan / approval / visual dev / visual‑lock / shot gen / post / QC / delivery）；项目目录合同 `outputs/<project>/{project.yaml, inputs/, planning/{brief,story,entities,asset-ledger.yaml,continuity.yaml,shot-list.yaml}, prompts/, images/{entity-sheets,scenes,storyboards,keyframes}, workflows/, clips/{raw,selected}, audio/, subtitles/, edit/timeline.yaml, qc/, final/master.mp4, logs/}`；`project.yaml` 单一状态账本，attempts 只增不覆盖。
- **visual‑development.md**：角色板 = 正/3‑4/侧/背全身同比例 + 头肩正/3‑4 特写 + 中性表情 + 服装层/鞋/配饰/持物 + 色板；**场景母版** = 宽景 + 主机位轴 + 门窗家具主道具位置 + 深度分区 + 光向 + 合法站位与屏幕方向；关键帧按交付画幅从母版派生，**首帧必须是可直接用的字面首帧不是拼贴板**；visual‑lock 时跨板比对冲突即拒绝，「不要指望 H3 修复不一致的源」。
- **comfyui skill**：控制标志 `[turbo=bool]`（默认 true：插 `MiniMaxH3TurboLoRA` + `MiniMaxH3TurboSampler` + simple 6 步，步数只许 4–8，拒绝改采样器）`[return=]` `[pe=]` `[preview=]` `[load_workflow=]`；只用随包 pinned 模板，拒绝任意自定义工作流；`prepare_workflow.py` 只 patch manifest 声明字段；**awaited 运行优先读 ComfyUI 日志流里的采样 ETA，不用固定间隔轮询**；音频‑only 模式把视觉 latent 钉在 32×32。
- **qc_media.py**：ffprobe + 全解码 + `blackdetect=d=0.25:pix_th=0.05` + `freezedetect=n=-60dB:d=1.0` + `loudnorm=I=-14:TP=-1.5:LRA=11` + `fps=…,scale,tile=4x3` 联络表 → JSON+MD 报告；`record_visual_qc.py --check/--hard-failure/--warning` 把人眼复核写回；技术 PASS + 视觉待审 ≠ 通过。硬门：缺镜/缺节拍、尺寸帧率时长编码违约、身份/服装/道具/轴线显著错、字幕越安全区、音频削波/超 TP、意外黑帧 >0.25 s / 冻结 >1 s。
- **turbo‑vs‑standard 报告**（GB10 128 GB、ComfyUI 0.30、768×448、124 帧、seed 固定）：Turbo 6 步 vs 标准 20 步 `res_multistep`，端到端 **2.20×**（T2V 253→114 s，I2V 260→119 s，R2V 261→119 s），I2V 首帧 SSIM 0.8245 vs 0.8215 基本持平，Turbo 更锐利高对比、标准更稳。
- **坑**：Codex 插件体系；GPT‑Image 做资产（我们用本地 Qwen‑Image/Krea2 替）；MCP 依赖 npm。
- **评级**：**采用其 references 结构与 QC 脚本**（profile.yaml、visual‑development、qc‑policy、project‑contract 四份文件思路直接移植）。

### chiphoton/DeepSeek-Harness-Video-Director（★69，MIT，2026‑09‑28）
- **定位**：DeepSeek Harness 的节点画布插件（vd‑node / vd‑workflow），内置 ComfyUI + Ollama + Codex Plan Provider，自带 H3 t2v/r2v turbo、音频、Qwen 编辑、Z‑Image 等 `custom_nodes/*.node.json`，`schemas/video-director-node-v1.schema.json`。
- **skill `comfyui-workflow-to-node`**：把可信 ComfyUI 工作流 JSON 转成声明式 vd‑node pack；明确区分 API 图（`class_type+inputs`）与 UI 模板（`nodes+links`，必须借 `/object_info` 的 `input_order` 把 `widgets_values` 映射成 API 输入名才能发 `/prompt`）；「转换不授权执行/安装」。
- **价值**：UI→API 转换规则与「节点包 = 代码，必须用户信任」的安全口径；术语表（comfyui‑node vs vd‑node）。
- **坑**：绑定 DSH 平台、DGX Spark 推荐；与我们路线无直接交集。
- **评级**：跳过（只记 UI→API 转换要点）。

### killkli/minimax-h3-colab-skill（★129，无 license，2026‑10‑17）
- **定位**：Codex skill，经 Google Colab CLI 跑 Ref2VA/FL2VA 批处理（notebook + `runner.py`）；manifest `{jobs:[{inference_mode reference|first_frame, reference_images 1–9 → <Picture N>, prompt_file, width/height 默认 1344×768 且多倍 32 面积 ≤1344×768, duration 4–15}]}`；`compose_ref2va_prompt()` 辅助写六段并校验 shot 起点 <时长。
- **价值**：manifest 字段设计简洁；「一批复用同一 session、失败保留已完成」。
- **评级**：跳过（Colab，无 license）。

### dseditor/h3-colab-skill（★74，NOASSERTION，2026‑11‑06）
- **定位**：繁中 skill，Colab 或本地 ComfyUI Desktop（`h3local.py check/setup/run`，默认 480P）跑 H3 生图（P‑H3‑Image LoRA）/视频/延伸（Motion Context）/TTS（32×32 只解码声音）；manifest 用 `@圖片1/@音訊1` 由程序换成 `<Picture N>/<Audio N>`。
- **prompt‑guide 要点**：**detailed_description 写 350–500 英文词，写太短 H3 会在画面上烧字幕**；台词 `<d>[Mandarin] …。</d>` 句尾要有标点；人物必须照参考图描述（对不上时 H3 会无视参考图）；动作戏先定进场/轴线/离场；`extend` 自动把上一段最后一格当参考。
- **评级**：跳过；借「写满 350–500 词防烧字幕」与「描述必须与参考图一致」两条。

### senmanx/novel-to-manju（★74，NOASSERTION，2026‑08‑17）
- **定位**：自包含的「小说 → 抖音竖屏漫剧」提示词 skill（粘给豆包/DeepSeek 即可），10 步：爆款改文（保人称）→ 转漫剧剧本（第一人称）→ 角色卡+音色 → 人物/道具提示词（全 3D）→ 场景清单 → 场景提示词 → 三视图 → 分镜 → 打斗特效 → H3 六段式；`docs/` 是作者原始提示词 txt 合集；`commands/manju.md` 一键触发。
- **漫剧专属规则**：**5.1 风格总表**按题材定美术风格/主色/光影/渲染后缀（修仙→国风写实 UE5 8K PBR；都市→现代写实 ELLE/VOGUE；科幻→赛博 2077；西幻→指环王；民国→伪装者；中式克苏鲁→褪色朱红锈蚀青绿；暗黑修真→青蓝墨黑+血红高光），3D 国漫加「3D国漫渲染、卡通材质、描边、赛璐璐」，三渲二加「3D 模型精度+2D 手绘笔触、强逆光轮廓光」，**选定后全片统一禁混用**；五官差异化词表（脸型/眉/眼/鼻/唇各 5–7 型）拒绝脸盲；瞳色规则（人类只用自然色）；参考图**全 3D 渲染不出真人版**（避免 H3 生成真人质感）；场景提示词固定开头「不能出现其他人,无人纯场景,」且禁人名/衣物暗示，视角三选一（鸟瞰/低仰/平视深远）；三视图版式 = 左全身正侧背 + 右上 6 头部角度 + 右下 6 局部细节，白底横版无文字。
- **时长与台词**：单段 4–15 s（默认 6–15），段内 2–4 镜用「切」；≤15 s 单段一次生成，>15 s 才拆段「上一段尾帧=下一段首帧」；**每段结尾留 0.8–1.2 s 静止供截尾帧**；台词每 5–6 字≈1 s，2 s 镜≤6 字/独白≤8，3 s≤9/12，4 s≤12/16，单镜 >30 字必拆；非说话者嘴唇紧闭不写喉部动作；内心独白标「（无口型，画外音）」。
- **合规两层**：平台红线（血腥/裸露/校园暴力/自残/邪教）绝对禁；题材中性化（血→金色血液/红痕/符文，暴力→格挡弹开光点消散，裸露→高领一字肩）。
- **评级**：借漫剧风格总表、三视图版式、台词字数表、合规替换表；不装（无 license、Seedance/即梦时代痕迹、第一人称强制对横屏短剧不适用）。

### xixihhhh/ai-short-drama-skill（Dramake，★91，MIT，2026‑08‑29）
- **定位**：面向 Codex/Claude Code/WorkBuddy 的短剧 skill v0.6.0，多模型选路（Wan 3 / Seedance / H3 / Kling），不绑定平台；`skills/dramake/SKILL.md` + 24 份 references + 20 个 CSV/MD 模板（production‑brief、character‑bible、prop‑bible、voice‑bible、shot‑plan、block‑manifest、continuity‑ledger、candidate‑scorecard、generation‑jobs、cost‑plan、spend‑ledger、qa‑report…）+ `scripts/{validate_plan.py,estimate_cost.py,extract_tail_frame.sh,make_contact_sheet.sh,check_bilingual.py}` + `evals/`。
- **十条铁律**摘要：主角必须因果改变结果；静音可懂；更少更长的段但限事件负载；未验收上游素材不生成下游；锁身份/材质/服装结构/轴线/道具/天气/湿度/光/声音边界；接触要有接近‑接触‑施力‑响应‑稳定；**视频里默认不生成手机 UI/信件/价签/关键文字，后期叠加**；原生对白每句锁唯一说话者与非说话者闭嘴；技术干净≠能发，60–120 s 要冷观众检查；没真看过不许说通过。
- **两种时间尺度**：生成段（一次请求，8–30 s，含 entry_state/exit_state、3–6 个内部节拍、事件负载预算：一个主道具系统 + 一条高风险物理链 + 一个主回报）与剪辑节拍（2–8 s 一项新信息）；`generated_duration ≠ accepted_ranges ≠ edit_duration` 分别记录；精确对白/手物接触/高运动/变形/多人/换地点时缩到 4–15 s。
- **一致性两层**：长期母版（脸、比例、服装结构、道具几何、场景布局、声音）vs 短期状态（姿势、位置、湿度伤势、道具朝向、情绪）；「每段都用母版 + 当前已验收状态；**只用尾帧会传播漂移**」；参考权威矩阵每维度唯一胜出素材；重复/带字道具建 `prop_id + state_id + text_plate_id`，文字做透明 PNG 后期跟踪。
- **QC 四道门 + 五种决定**：剧情（冷观众四问）/身份画风/物理连续性/声音；保留、后期修、编辑而非重生、换种子重试（最多 2–3 次）、重写；每次只改一个变量；预算用到一半无进展就换模式/拆镜。`extract_tail_frame.sh` = `ffprobe duration − 0.20 s` 处抽一帧。
- **实测记录**（2026‑08）：36 个 5 s 碎片 55.6% 严重/阻断；20 个原生音频段响度 −25.8～−16.9 LUFS 相差 8.9 LU，边界 RMS 跳 30–40 dB → 必须后期重建环境与响度；尾帧串联改善连续性但同段后半仍漂移。
- **坑**：Seedance/Wan 为主，H3 只在路由表一行；CSV 字段极多（shot‑plan 50+ 列）。
- **评级**：借台账字段与 QC 门禁；不装。

### anymouschina/TapCanvas（★712，MIT，2026‑11‑03）——只看 H3/漫剧编排与一键成片
- **定位**：Agent 原生无限画布（pnpm monorepo，hono‑api + new‑api 鲁班网关），**视频走云 API 渠道**（HeyRoute 31 模型含 MiniMax H3、Seedance），不驱动本地 ComfyUI。`apps/agents-cli/skills/` 70+ 个 skill，其中 tapcanvas‑video‑workflow（一键成片唯一主路径）、tapcanvas‑video‑authoring‑stages、tapcanvas‑continuity、tapcanvas‑video‑reviewer、tapcanvas‑workflow‑orchestrator、tapcanvas‑character‑card/scene‑card/prop‑card、wardrobe‑continuity‑director 等。
- **编排结构**：frontmatter 极重（`knowledge-role`、`knowledge-domains`、`metadata.contracts`、`consumes/produces/required-evidence/side-effects/self-check/requires-skills`、`artifact-preload`）；一键成片 = 「冻结来源分段 → 章级共享资产注册表 → 全章连续性/对白规划 → 逐 Clip packet 作者 → 节点投影 → 媒体执行」，每 Clip 一个视频节点，跨章资产按稳定身份在项目记忆查真实 URL；`tapcanvas-continuity` 要求续写边界来自显式 checkpoint（`storyboardChunks`、`tailFrameUrl`），缺证据直接失败，禁止用 history 猜；reviewer 是**可选**诊断，不固定打分、不逐条流程，「有依据的静止与静默不是缺陷」。
- **价值**：skill 之间的「合同/证据/副作用」声明方式；「主代理决定 source of truth，子代理只做局部」的边界条款。
- **坑**：云 API、重工程、与本地 H3 参数无关。
- **评级**：观望；借 frontmatter 字段与 continuity 协议写法。

### looplj/reveric（★714，AGPL‑3.0，2026‑11‑07）——只看 H3/漫剧编排
- **定位**：Flutter 桌面「小说→成片」工作台，模型走 API（赞助商秘塔 H3 API 0.09 元/秒 768P），`assets/official_skills/screenplay-production/`（剧本制片 skill：SKILL.md + 14 份 references：production / storyboard / character‑design / image‑references / image‑recipes / shot‑recipes / video‑prompts / seedance‑/veo‑/kling‑/wan‑prompts / model‑capabilities / troubleshooting）。
- **编排规则**：「分镜」= 场次下一条制作内容 = 一次生成，可含多个 Shot，**换景别不等于新建生成任务**；拆分镜六步：读正文与已有片段核对素材 → 列必须保留的动作/逐字对白/揭示 → 先按连续性选生成边界再按模型时长与动作负载定段长（接触、交接、受力、精确姿态放同一次生成）→ 明确每段开场/结束状态与所需参考 → 写入 `/clips` → 回读核对；缺素材只许标「参考待绑定」不许自动改纯文本生成；`photos.name` 必须说明用途/视角/状态。
- **坑**：AGPL；源码为 Flutter 设计稿与 skill 文本，H3 细节少。
- **评级**：观望；借「生成边界先于时长」与「参考待绑定」措辞。

### cwp-cwp/ai-video（★81，无 license，2026‑11‑07）
- **定位**：Spring Boot 3 + LangChain4j + Vue 3 的本地平台（小说→剧本→分镜→视频，ComfyUI 本地 H3/LTX，VoxCPM2 配音，ACE‑Step 音乐），B 站有 6 分钟/11 分钟全自动短片；`skills/SKILL.md`（`ai-drama-director`）是**外部导演 skill**：把平台当渲染后端 + 资产库，用法 A 全流程、B 质量增强（台词长度 vs 分镜时长、可拍性、景别/运镜/时长/声音字段）、C 精品线（增量改系统生成的剧本/分镜基线）；`scripts/drama.py` 提供 `audit_storyboard / coverage_check / preflight_check / promptcheck`（对白与分镜文本差异、台词时长审计）。
- **自带工作流（analyze.py）**：`video_minimax_h3_r2v_导演台多段衔接.json` = AIMixer `MiniMaxH3Director` + `DirectorGroupReferenceToVideo` ×3 段（12/7/9 s）+ `GroupsCombine`，`minimax_h3_ref2va_pruned_int8_convrot` + `qwen3vl_32b_int8_convrot` + `minimax_h3_fl2v_turbo_8step_v1.0 LoRA 0.75` + `res_multistep` 8 步 + `TESpeedMiniMaxH3`；`minimax-h3-二采工作流.json` = Ref2VA 一采 1344×768 124 帧 12 步 `TaoMate-H3-3step` LoRA + `MiniMaxH3SigmaShift(12,3)` + `MinimaxH3LatentUpscaler3D` + `MMH3UltimateUpscale` 二采；`Minima-H3-武戏工作流.json` = T8 系列双时钟采样 + 学习式 latent 超分 1.5× + 语义桥 LoRA，先出 736×416 预览「看动作对不对，不对就取消」。
- **cinematic-rules.md**：每场必须改变一件事；对白在做事不在说明；每镜「起点→唯一动作→终点」，终点要能成下一镜起点；相邻两镜同景别同角度同关系 = 切镜无职责并回一镜。
- **坑**：Java 栈、无 license、依赖本平台 API 登录。
- **评级**：观望平台；**借三份工作流的参数组合**（与 docs/12 互补）与 cinematic‑rules。

### zxcHolmes/minimax-h3-studio（★187，Apache‑2.0，2026‑11‑06）
- **定位**：Linux 单 GPU 自托管 Web 工作室，**把 ComfyUI 当 Python 库直接调节点**（无 UI、无工作流 JSON，输出与官方工作流像素一致 PSNR inf），常驻 job 服务 + sqlite 队列；T2V/I2V/FL2V/Ref2VA（≤6 图 + 3 视频）、larryvrh 4 步 / Pika H3 Flex 6 步 / FastH3 8 步可选、MOSS‑Image/Klein/Qwen 生图、Pixal3D、audio.cpp TTS/ASR、Music 3、RelayVSR/FlashVSR/SeedVR2 超分、guide audio。**RTX 4090 实测：5 s 带声 544p 约 30–45 s，768p 约 65–70 s。**
- **doc/directing-workflow.md**（agent 导演流程）：先确认画幅/分辨率（默认 768p）/视频模式（默认 Ref2VA 固定角色与场景图）/口语/视觉处理/字幕语言；项目目录 `00_project.md / 01_bible.md / 02_storyboard.md / 03_reference_manifest.json / 04_generation_log.md / PROGRESS.md / refs/{characters,locations,shots,candidates} / prompts/{images,video} / clips(+rejected) / qc / subs / jobs.json`；交付物 = 含两条字幕轨的成片，「一堆片段不算成片」。
- **坑**：Linux + systemd + ComfyUI 特定 commit（2f894332，comfy‑kitchen 0.2.41），不适合 Windows 11 用户；绕过工作流 JSON 的做法与我们「ComfyUI 0.37.2 现成节点」路线不同。
- **评级**：观望；借项目目录与 4090 时间基线。

### hollisorg/iv-studio（★57，MIT，2026‑11‑07）
- **定位**：Electron 桌面应用（Win/mac/Linux 发行版），驱动本机 ComfyUI 跑 H3，六步向导（idea→script→cast→storyboard→filming→film），**抽卡机制**：`generate_previews` 1–3 个低分辨率候选（seed, +1000, +2000）→ 看帧 → `finish_candidate` 复用预览 latent 做 2 MP + DLSS/RTX 2× 或 SeedVR2 精修（「picked performance stays the same」）；**take ranking** = 每句台词听回比例（`heardScore`，ASR 对照 `<d>` 内文本，数字读法归一，重复说一遍扣分）× 与角色相似度 × 不冻结 × 相对清晰度（`relativeSharpness`，差距小视为同样清晰），权重随用户挑选漂移；`check_prompt` 渲染前查 H3 易误读点并给 fix；`review_take` 让写手看帧逐条列问题 + 秒数 + 一个修法（改词 / 换参考 / 拆动作 / 取干净段 / 剪辑解决），复发问题标 `again` 自动升级修法；staging board（俯视米制站位 → 屏幕左右站位词 + `lineWarnings` 越轴警告）；previs 灰模视频只对 arc 运镜有效，推拉跟摇用文字更好且快 1.6–3.5×。MCP server `iv-studio` 暴露同一套工具。
- **源码**：仓库只含 `resources/`、`docs/`、`test/`，**`src/` 不在仓库**（ranking.js 只能从 test 推断）。
- **坑**：源码不开放、角色靠训练 LoRA（Modal）、DLSS 依赖 NVIDIA。
- **评级**：观望；**抽卡→排序→精修的三段式与排序四维**是我们 skill「择优」规则的最佳参照。

### 10291124jcjc-dotcom/ancient-rap-battle（★233，MIT，2026‑10‑17）
- **定位**：Claude Code skill，一句话做「古人说唱 Battle」90 s 16:9 2K：歌词（每句史料注释）→ Suno → Midjourney 定妆 → 即梦 Seedance 2.5 网页分段生成（或 MiniMax API H3 路线 `h3run.py`）→ 自动逐镜对齐 → 拼接字幕封面。`scripts/` 15 个 Python（analyze_song / clean_vocal / seedance_packs / seedance_align / h3run / qa / lipcheck / assemble / package…）。
- **可迁移经验（pitfalls.md H3 路线）**：参考图用全身三视图 → H3 拍成全身远景脸小看不清口型，**近景用裁出的半身图，提示词第一句写景别**；**一条只给一句歌词**（第 2 秒后 H3 自己重唱）；H3 把歌晚放 0.1–0.3 s → `qa.py` 用 10 ms 对数能量包络互相关整句搜偏移（corr≈0.98 同步、下降=重唱只前半可用），自动存 `shifts.json`；纯侧脸/麦克风挡嘴看不出口型 → 3/4 侧脸；固定站位 A 永远左 B 永远右；`lipcheck.py`（MediaPipe 嘴开合 vs 人声响度）只作提示，**以用户眼睛为准**（曾测出 0.58 s 偏移反而更糟）。
- **评级**：跳过主体（音乐类 + 云端）；借口型/对齐 QA 思路。

### Work-Fisher/reference-first-motion-director（★86，MIT，2026‑08‑27）
- **定位**：Codex skill，口播/动效包装的「参考先行」视觉导演：整片视觉总表（A 人物/E 原生证据/R 录屏/M 动态包装/G 生成镜头五职责，优先级 E/R/A > M > G）→ 动效制作清单 → 每单元一张严格 2048×1152 参考图（`ensure_2k.py`）→ H3 提示词（`h3-compile.md`）；四层参考库（starter / creator / 主知识库 / 新入库）带 `reference_library.py`。
- **h3‑compile.md**：模式职责表——I2VA 图=精确首帧、L2VA=精确终帧、FL2VA 双锁、**Ref2VA 图只做构图/主体/材质/风格参考（含文字/UI 的完成图默认走此模式）**；时长路由三步（用户/模型约束 → 主运动要完成几个因果事件 → 参考案例节奏校准），常用 3–5 s 标题冲击 / 6–9 s 2–4 强事件 / 10–15 s 连续操作；「原本写 15 s 但只有 2–4 个强事件的短包装优先压到约 8 s」并给 8 s 骨架（0–0.8 建立 / 0.8–2.6 事件 1 / 2.6–4.6 事件 2 / 4.6–6.6 事件 3 …）。
- **评级**：跳过（口播包装题材）；借「含文字的参考图只能走 Ref2VA 弱参考」与时长路由。

### lshhhhhhh/ai-school-op（★83，NOASSERTION，2026‑09‑25）
- **定位**：实战复盘：用本地 H3 Ref2VA **视频编辑模式**把 91 s 动画 OP 的 18 个角色逐镜换成 AI 娘，81 镜/73 单元，RTX 5090，1024×576，`res_multistep/simple` 20 步，56 帧约 2.5 分钟；公开分镜计划、118 个版本的最终通过提示词（`prompts/index.csv` 含版本/种子/参考图顺序）、工作流模板、验收页代码。
- **经验**：**随手写的短提示词 → 模型几乎原样照抄原片**，换成官方 Ref2VA 六段（`summary` 以 `[video editing + reference generation] The target video is an edited version of <Video 1>.` 开头）一次换对；修改时**一次只加一句**；外观相近/人物小/快速推拉时写「对比句」（原片是 X，换成 Y）；多镜头单元 H3 的剪辑点会漂几帧，用场景变化分数找真实剪辑点再对齐；不要为凑长度把无关镜头拼进参考视频（会串画面）；换不掉时改首帧 I2V + 后期溶解；静态字卡/道具直接生图按帧数静止输出；GPU 温度守护、夜间队列；拼接前核片段哈希与帧数，超分母带只做 lanczos 不叠 AI 处理。
- **评级**：借经验条目（视频编辑模式、对比句、一次只改一句）。

### gary149/h3-game-sprites（★147，MIT，2026‑08‑17）——略读
- H3 当「演员」生成 5 s 动作视频 → 抽 8–16 极端姿态帧 → 品红 `#FF00FF` 抠像 → 数值 QC → 精灵图集。依赖 OpenRouter API。唯一可借的是「idle‑pin」思路（每个动作以同一待机姿态起止保证可循环）与「用数字而非感觉验收」。跳过。

### joeVenner/awesome-minimax-h3（★9，MIT，2026‑08‑16）
- 三个 skill（`minimax-video` / `minimax-speech` / `minimax-music`）全部走 **MiniMax 云 API**（`api.minimax.io/v2/video_generation`，`allowed-tools: Bash(curl:*) …`，frontmatter 有 `metadata.verified` 日期）。写法规范（description 带关键词列表、`compatibility` 声明依赖、references 分 api‑reference / prompt‑engineering / technical‑reference），但与本地无关。跳过；借 frontmatter 的 `metadata.verified`、`allowed-tools` 字段。

### okaypic/okaypic-video-skill（★0，MIT，2026‑10‑26）
- 第三方付费 API（0.10 美元/10 s 768p），但 SKILL.md 是**真正交付过剧集**的写法：项目 `ep01/{cast.json, shots.json, edit.json}`；`shots.json{style 一句全集共用, seeds:[1,2] 两个 take 是甜点, duration, shots[{id,refs→<Picture N>,prompt,first_frame}]}`；流程：先给成本估算并拿到 OK → 每镜 5–10 s、对白 ≤12 词、钩子在第 1 镜前 3 秒、不要画内文字 → 角色**16:9 设定板（特写 + 正侧背全身）而非单张肖像**（「一张板能撑 50 个片段，单张 3/4 肖像会漂」），明写人种/年龄/体型/身高，一个保留视觉锚（领带/疤/帽），变形角色每形态一张板，**只写正面描述绝不写 "no text/no watermark"（点名即召唤）** → **用 5 帧联络表而非视频挑 take，先看角色一致再看能量** → 失败镜只重跑对应 id（`client_request_id` 幂等不重复计费）→ `edit.py --autotime` 从音频对字幕时间。`prompting-h3.md`：`effort 1.5x/2x` 多镜头时才值（1x 偶尔忽略 `[Shot 3] at 00:11.000` 的切镜）；相同 seed 不可复现；避免 >3 说话人、两个长得像的角色。
- **评级**：跳过 API；**借其 shots.json 与「联络表挑 take」规则**。

---

## 三、我们自己的 skill：建议目录结构与阶段划分

> 综合官方 3d‑animation 骨架、TFboy1 的脚本层、chiphoton 的 references/QC、suihe1 的状态合同、漫剧老李的段缝规程。目标宿主：Claude Code / Codex / OpenCode；执行后端：本机 ComfyUI 0.37.2 + 核心 MiniMaxH3 节点。

```
h3-drama-director/
  SKILL.md                      # ≤300 行。frontmatter: name / description(Use when… Not for…) / compatibility
                                #   ("Requires local ComfyUI ≥0.37 at 127.0.0.1:8188 with MiniMaxH3ImageToVideo /
                                #   ReferenceToVideo / AddGuide / SigmaShift, ffmpeg+ffprobe, Python 3.11; Windows+NVIDIA validated")
                                #   / license / metadata{version, verified: YYYY-MM-DD, hardware: RTX 4090 24GB}
  SKILL.cn.md                   # 中文镜像
  agents/openai.yaml            # Codex UI 元数据（display_name / short_description / default_prompt）
  references/
    00-locks.md                 # 开工六锁：画幅 16:9 / 总时长 30|60 s / 风格(电影感|漫剧 3D|三渲二) / 对白路线 / 段缝方式 / 草稿档位
    10-story-outline.md         # 大纲 gate check（主角主动、巧合不解题、结尾回收锚点…）
    20-character-sheet.md       # 角色设定板规格（16:9，左1/3脸部特写+右2/3正侧背；白底；无文字）+ 五官词表 + 瞳色规则 + 衣橱/状态子资产
    21-scene-master.md          # 场景母版（无人、16:9、主机位轴、门窗家具主道具位置、光向）+ 九宫格多机位（1 槽=9 视角）
    22-prop-sheet.md            # 道具板 1:1 白底；含文字的道具 → text_plate 后期叠加
    30-shot-table-spec.md       # 六列镜头表 + 每秒指令 + 5.5 自检六项（钩子密度/≤15 s/≤3 人/地标光照继承/每秒覆盖/Handoff 成链）
    31-segment-splicing.md      # 段 = 一次生成 4–15 s；末镜 0.5 s 收束 + 末 1 s 定格；截末帧；0 级同档景别起手；背景锚点锁；末帧不可用三级处置
    40-h3-prompt-rules.md       # 在官方 base-en/ref-en 之上的增量规则（英文正文、<d>[Chinese]、官方切镜短语、画外声公式、(Sx) 编号、
                                #   同性别多说话人对策、否定句禁用、[Shot 1] 单主体、350–500 词、retention 标记固定值、summary 任务前缀）
    41-reference-pack.md        # 9/3/3/12 取材优先级；role/retention/allowed change/forbidden drift 四栏 anchor sheet；只给说话角色传音色、音频≤3
    50-comfyui-driver.md        # /system_stats→/upload/image→/prompt→/history+/queue 轮询→/view；class_type 覆盖表；node_errors 处理；丢失判定；中断区分
    51-workflow-profiles.md     # 草稿档(768P 短边、Turbo 4–6 步、Sage)/精修档(20 步 res_multistep simple、shift 12/3)/二采超分档；17k+5 帧网格；文件命名
    60-take-selection.md        # 抽卡：每镜 2 seed（关键镜 3）；5 帧联络表先看一致性再看能量；VLM 评分 schema；四维排序；一次只改一个变量
    61-qc-policy.md             # 硬门/软警；ffprobe+全解码+blackdetect 0.25+freezedetect 1.0+loudnorm −14/−1.5；人眼复核必填；问题分级与修复层级
    62-failure-codes.md         # F-COUNT / F-ID-DRIFT / F-STATE-DRIFT / F-REF-SCOPE / F-LIPSYNC / F-DIALOGUE-TEXT … → 责任层 + 最小修复
    70-assembly.md              # 剪掉定格秒；起始音节裁剪；contain-pad 1920×1080 24 fps 48 kHz；响度统一；字幕后期；无 BGM 默认
    80-manju-style.md           # 漫剧专属：风格总表（题材→美术/主色/光影/渲染后缀）、3D 国漫/三渲二后缀、参考图全 3D、合规替换表
    90-troubleshooting.md       # 症状→原因表（胡言乱语/脸漂/超分音糊/长度不对/烧字幕/照抄参考视频/爆炸词…）
  assets/
    workflows/{t2v,i2v,fl2v,ref2va}_{draft,final,upscale}.api.json   # API 格式，字段由 workflow-manifest.json 声明
    workflow-manifest.json      # 每个工作流的 roles{prompt,seconds,width,height,seed,steps,scheduler,filename_prefix}/media{loaders,maxImages 9,maxAudioVideo 3}/outputs/prune
    templates/{project.yaml, shot-table.md, character-bible.md, continuity-ledger.csv, candidate-scorecard.csv, qa-report.md}
  scripts/
    doctor.py          # /system_stats、/object_info 查节点、模型文件、ffmpeg、显存空闲
    init_project.py    # 建 outputs/<slug>/ 目录与 project.yaml
    validate_prompt.py # H1~H12 式校验（字段/顺序/时长/<d>/切点递增/标签先定义后引用/否定句/中文泄漏/说话人编号）
    build_workflows.py # shot-table → 每段 API 图（按 class_type/manifest 覆盖，后端校验）+ params.md 确认表
    submit_jobs.py     # 上传参考 → /prompt → jobs/*.json
    monitor_jobs.py    # /history+/queue 轮询、重试、断点、下载 .part
    extract_tail_frame.py / detect_lead_syllable.py / make_contact_sheet.py
    judge_take.py      # 抽 5 帧 → 本地 Qwen3-VL 打分 → scorecard
    qc_media.py        # ffprobe/全解码/黑帧/冻结/响度/联络表 → qc-report
    assemble.py        # 剪定格秒、裁起始音节、concat、统一规格、字幕
```

**阶段划分（每个阶段 = 一张选择卡 + 一份落盘产物，推荐项放第一，用户说「继续」即选推荐）**

| # | 阶段 | 输入 | 输出（落盘） | 停点 |
|---|---|---|---|---|
| 0 | 开工六锁 + doctor | 用户一句话/剧本 | `project.yaml`（画幅、时长、风格、对白路线、段缝方式、档位）、`logs/environment-report.json` | 卡 ×6 |
| 1 | 故事与大纲 | 锁 | `planning/story.md`（8 拍、gate check） | 卡 |
| 2 | 角色/场景/道具圣经 | 大纲 | `planning/entities.md`、`character-bible.md`、衣橱与状态表 | 卡 |
| 3 | 资产生图（本地 Qwen‑Image/Krea2） | 圣经 | `images/entity-sheets/*.png`（16:9 板）、`images/scenes/*_master.png + *_grid9.png`、`images/props/` + VLM 质检记录 | **visual‑lock 卡** |
| 4 | 六列镜头表 + 5.5 自检 | 大纲 + 资产 | `planning/shot-table.md`（段/镜两级，段 ≤15 s，每秒指令，Handoff，Anchors，Hook，Audio 轨） | 卡（自检通过才放行） |
| 5 | 段缝设计 | 镜头表 | 每段 entry_state/exit_state、末镜定格写法、下一段起手景别 | 并入卡 4 |
| 6 | H3 提示词 + 参考包 | 镜头表 + 资产 | `prompts/seg_XX.txt`（官方三字段/六段，英文）、`prompts/seg_XX.refs.json`（anchor sheet）+ `validate_prompt.py` 通过 | 卡：展示逐段「几秒→画面→对白」表 |
| 7 | 工作流构建 + 参数确认 | 提示词 | `workflows/seg_XX_api.json`、`jobs/params.md`（段/时长/模式/档位/步数/seed/分辨率/参考数） | **卡（付费≈GPU 时间确认）** |
| 8 | 草稿抽卡（768P、Turbo） | 工作流 | `clips/raw/seg_XX_sNNNN.mp4` ×2–3、联络表、`qc/scorecard.csv`（VLM + 规则） | 卡：每段选 take 或重抽（只改一个变量） |
| 9 | 精修/超分 | 选中 take | `clips/selected/seg_XX.mp4`（20 步重跑同 seed 或二采超分） | 卡 |
| 10 | 拼接与声音 | selected | `edit/timeline.yaml`、`final/master.mp4`（剪定格秒、裁起始音节、统一规格、响度） | — |
| 11 | QC 与交付 | master | `qc/qc-report.{json,md}`、`qc/final-contact-sheet.png`、人眼复核记录 | 终卡 |

先做 1 段「最能暴露问题」的样片（主角正脸 + 一句中文对白 + 一次有动机运镜 + 手部道具）跑完 0–11，再扩到 30 s（约 3 段），再 60 s。

---

## 四、可写进 skill 的规则（祈使句，含来源）

1. 写 SKILL.md 时 frontmatter 只放 `name / description(含 Use when… Not for…) / compatibility / license / metadata{version,verified,hardware}`，正文每步只写「最小运行契约」并 `Required reference: read references/X.md`，细则全部进 references。（官方 3d‑animation；joeVenner metadata.verified）
2. 每个会花 GPU 时间或改变下游的步骤前弹选择卡，推荐项放第一，用户说「继续」即选推荐；开工先问画幅与总时长，任何锁未选时停下问，禁止替用户默认。（官方；漫剧老李六锁）
3. 角色参考只用一张 16:9 设定板：左 1/3 头肩特写，右 2/3 正/侧/背全身同比例，白底，无文字无道具；每角色一张 canonical 跨所有镜复用，服装/年龄变体做子资产（`costume > age > 原图`）。（infinite‑creation `CHARACTER_T2I_LAYOUT_CONSTRAINT`；okaypic；chiphoton visual‑development）
4. 场景出两张：无人 16:9 母版（主机位轴、门窗家具主道具位置、光向）+ 3×3 九宫格多机位（1 张=9 视角=1 参考槽）；场景提示词固定开头「无人纯场景」，禁任何人名/衣物暗示。（漫剧老李 scene‑grid‑template；senmanx 场景；chiphoton）
5. 参考包守 图≤9 / 视频≤3 / 音频≤3 / 总≤12，音频不能唯一；取材顺序 首尾帧锚图 → 主角板 → 场景母版+九宫格 → 配角 → 道具拼板 → 动作参考视频 → 音色；每个参考写 Role / Retention / Allowed change / Forbidden drift 四栏；定义了不引用的参考删掉。（漫剧老李 h3‑adapter §四；h3lite anchor sheet；Agent‑Kit）
6. 只给「有台词」角色传音色参考，单镜音频 ≤3、说话人 ≤2（≥3 人对话拆镜）；音频文件不存在就不引用（LoadAudio 会让整图被拒）。（infinite‑creation `MAX_SPEAKERS_PER_SHOT=2` / `assembleShotReferences`）
7. 同性别多说话人高危：声学画像反着写（音高/音质/语速）、优先一段一开口者、删掉 chuckle/抽气类非对白人声、声音只前进不回头；每个说话人首次出现写 age/gender/on‑screen/pitch/timbre/rate/accent。（漫剧老李 h3‑adapter 引官方 issue #17）
8. 六段/三字段正文一律英文，只有 `<d>[Chinese] 台词</d>` 与双引号内画内文字保原文；`<d>` 内只放纯台词，说话人与语气放外面；切镜只用 `the camera cuts to / the shot cuts to / transitions to / changes to / switches to`；画外声用 `… (Sx) says in an off-screen voiceover: <d>…</d> while his lips remain completely closed.`。（官方 base‑en；漫剧老李；Agent‑Kit）
9. 正文只写「有什么」，不写否定句（词根会被渲染，"no watermark" 点名即召唤）；拟音禁「啪/砰/轰/炸/爆」类词（触发爆炸视觉）。（漫剧老李法则 22；okaypic；qiukaihui h3_expand）
10. `[Shot 1]` 不带时间戳且只有一个具名主体；后续 `[Shot N] At MM:SS.mmm,` 严格递增且 ≤段时长；`detailed_description` 写满 350–500 英文词（太短 H3 会在画面上烧字幕）；`retention_analysis` 用固定值 `fully_preserved / partially_preserved / attribute_transfer / weak_reference` 且不含 `(Sx)`；`summary` 段首写任务前缀 `keyframe completion / reference generation / video continuation`。（官方 ref‑en；漫剧老李；dseditor）
11. 每镜画面描述按七层写：精确人数正向锁「恰好 N 名角色各出现一次」→ 身份/发型/服装与资产表一字不差 + 「参考图只继承身份发型服装，排除姿势构图背景光线」→ 空间与唯一道具 → 动作因果链 → 摄影机三件套（起点构图 + 一个主运动 + 终点构图）→ 光色材质 → must_hold / changes_here / must_not_appear。（qiukaihui h3_expand）
12. 段 = 一次生成，4–15 s，不跨场次；段内 2–4 镜；台词按 4–6 字/秒预算（2 s 镜≤6 字、3 s≤9、4 s≤12，单镜 >30 字必拆），标点停顿 ，0.2 s 。0.4 s …0.8 s；长镜头聚合（同场景连续动作 + 多句对白合一段，禁一句一镜）。（senmanx；漫剧老李 gate_check；infinite‑creation novel‑to‑video）
13. 末镜写「末 1 s 前 0.5 s 运动收束，末 1 s 全体人物保持姿态站位、画面定格」，拼接时整秒剪除；末镜用中全景/中景装下全部在场人物，禁大远景；用 `ffprobe duration−0.2 s` 抽末帧作下一段首帧/参考；下一段首镜以 0 级同档景别起手；每人身后写一个可辨背景锚点。（漫剧老李 segment‑splicing；dramake extract_tail_frame.sh；qiukaihui `-sseof -0.1`）
14. 下一段同时带「长期母版（角色板/场景母版）」和「短期状态（截取的末帧）」，只用末帧会传播漂移；上一段失败则回溯更早成功段的末帧续接，再不行降级 T2V，链不断。（dramake identity locks；qiukaihui advance_chain）
15. 驱动 ComfyUI 的顺序：`GET /system_stats` 探活 → `POST /upload/image`(multipart, type=input, subfolder=<项目>/refs, overwrite=true) → `POST /prompt {prompt, client_id}` → `node_errors` 非空立即中止并报缺什么 → 每 1.5–30 s 并行 `GET /history/{id}` + `GET /queue`，history 有记录即完成，既不在队列又无 history **连续 3 次**才判丢失 → `GET /view?filename&subfolder&type` 分块下载到 `.part` 再改名。（TFboy1 submit/monitor；infinite‑creation comfyui.js）
16. 改工作流只按 `class_type`/manifest 声明的字段覆盖（提示词、LoadImage.image、时长、steps、scheduler、noise_seed、ResolutionSelector、SaveVideo.filename_prefix），不写死节点 id，不改写用户工作流文件；UI 格式先借 `/object_info` 转 API 格式。（TFboy1 workflow‑routing；DeepSeek‑Harness；infinite‑creation spec）
17. `length` 必须落在 17k+5 帧网格（73≈3 s、124≈5 s、362≈15 s），分辨率多倍 32，草稿 768 短边；`status_str=error` 时区分 `execution_interrupted`（被中断）与真失败；取消时本地后端 `/interrupt` + `DELETE /queue`。（Agent‑Kit；infinite‑creation）
18. 文件命名 `E01-S01.mp4` / `seg_01_s1011.mp4`：段 id 即文件名；`SaveVideo.filename_prefix=<项目>/<模式>/seg_XX`；jobs 状态逐段落盘 `prompt_id/status/attempt/seed/refs/sha256`，重跑任意阶段幂等跳过已完成段。（suihe1；TFboy1；chiphoton project.yaml）
19. 提交前跑硬校验：字段齐全与顺序、4–15 s、模式与对齐行匹配、9/3/3/12、切点递增、`<d>[lang]` 闭合、标签先定义后引用、正文无中文泄漏、无否定句、无内部术语；FAIL 不提交。（video‑agent validator；漫剧老李 H1~H12）
20. 抽卡每镜 2 个 seed（关键镜 3），用 5 帧联络表而不是看视频挑：先角色一致性再能量；评分四维 = 台词听回比例（ASR 对照 `<d>`）× 与角色板相似度 × 无冻结 × 相对清晰度；一次重抽只改一个变量（seed / 一句提示词 / 一个参考），同一错误连续两批无改善就回上层（资产/镜头拆解）不再抽。（iv‑studio ranking；okaypic；qiukaihui failure_codes；dramake）
21. 草稿用 Turbo 4–6 步 + Sage（步数 ≤8 自动插 TurboLoRA→Sage），精修 20 步 `res_multistep/simple`（Ref2VA 可试 beta），`SigmaShift(12,3)` 标注为社区经验；Turbo 对标准约 2.2× 快、首帧 SSIM 持平、细节更锐；选中 take 后重跑同 seed 精修或走二采 latent 超分，不换表演。（chiphoton turbo‑vs‑standard；qiukaihui；video‑agent BEST_PRACTICES；cwp 二采工作流；iv‑studio finish_candidate）
22. 本地 ComfyUI 一次只跑一个渲染任务；LLM/VLM 阶段也排队（27B/32B 文本编码器常驻显存）；长批次前检查空闲显存与磁盘，Windows WDDM 下 `nvidia-smi` 进程显存不可信；无人值守前确认并开显存 90%/95% 监控。（infinite‑creation render‑gate；h3lite gpu‑contention；TFboy1 阶段 3.5）
23. QC 分硬门与软警：硬门 = 文件不可解码、缺镜/缺节拍、尺寸帧率时长违约、身份/服装/道具/轴线显著错、音频削波或超 −1 dBTP、意外黑帧 >0.25 s / 冻结 >1 s（声明的定格尾除外）；跑 `ffprobe + 全解码 + blackdetect=d=0.25:pix_th=0.05 + freezedetect=n=-60dB:d=1 + loudnorm I=-14:TP=-1.5 + tile=4x3 联络表`；技术 PASS + 人眼未审 ≠ 通过。（chiphoton qc‑policy/qc_media.py）
24. 每条 QC 问题记 集‑时间码‑镜头/任务 ID‑类型‑证据‑根因‑修复层级‑复验状态，修复从上游开始：资产 → 剧本/导演 → 分镜/提示词 → 重生成 → 后期；冷观众四问（想要什么/什么阻止/什么变了/为何结局）任一答错即 P0。（suihe1 post‑and‑qc；dramake qa‑and‑repair）
25. 拼接前：剪掉每段末 1 s 定格；检测并裁掉 H3 开头 0.02–0.15 s 的「起始音节」（前 0.6 s 内 <0.3 s 高能段后接 0.2 s 低能）；统一 contain‑pad 1920×1080 24 fps 48 kHz；原生音频段间响度可差 9 LU，必须后期统一；字幕与画内文字一律后期叠加，默认无 BGM。（qiukaihui；suihe1 post‑kit；dramake 实测；官方 qc）
26. 用 Ref2VA 视频编辑/人物替换时，随手短提示词会原样照抄参考视频；必须六段式且 `summary` 以 `[video editing + reference generation] The target video is an edited version of <Video 1>.` 开头，外观相近时写「原片是 X，换成 Y」对比句，修改时一次只加一句。（lshhhhhhh ai‑school‑op）
27. 口型镜头：近景用裁出的半身图而非全身三视图，提示词第一句写景别；一条只给一句台词；3/4 侧脸，不要麦克风挡嘴；用能量包络互相关检查 H3 是否晚放/重唱音频。（ancient‑rap‑battle pitfalls/qa.py）
28. 漫剧风格：先按题材选风格总表一行（美术风格/主色/光影/渲染后缀），3D 国漫加「3D国漫渲染、卡通材质、描边、赛璐璐」，三渲二加「3D 模型精度+2D 手绘笔触、强逆光轮廓光」，全片统一禁混用；角色参考图全 3D 不出真人版；动画目标不用真人负面词，改锁比例/轮廓/线宽/色板/变形边界；五官按词表逐人写具体，人类瞳色只用自然色。（senmanx 5.1/5.2；dramake style‑locks）
29. 合规：血→金色血液/衣领红痕/光影符文，暴力→格挡弹开光点消散，裸露→高领一字肩立体剪裁；不删剧情只换词。（senmanx 2.1）
30. 含可读文字/UI 的参考图只能走 Ref2VA 弱参考（构图/风格），不能当 I2VA 精确首帧；首帧必须是可直接用的字面首帧，不是拼贴设定板。（Work‑Fisher h3‑compile；chiphoton visual‑development；suihe1 storyboard‑view）

## 五、10 条最有价值的规则（从上面 30 条里挑）

1. 每角色一张 16:9 设定板（特写 + 正侧背）作为唯一 canonical，场景「母版 + 九宫格」，参考包守 9/3/3/12 并逐项写 Role/Retention/Allowed/Forbidden。
2. 末镜「0.5 s 收束 + 末 1 s 定格」→ 剪掉 → 截末帧 → 下一段同档景别起手，且母版与末帧同时投喂。
3. 六段/三字段全英文、`<d>[Chinese]` 保台词、官方切镜短语、画外声固定公式、只写正面描述。
4. 只给说话角色传音色、单镜说话人 ≤2、音频 ≤3，同性别多说话人反着写声学画像。
5. 驱动 ComfyUI：class_type 覆盖、/upload→/prompt→/history+/queue 双查、连续 3 次查无判丢失、node_errors 立即止、.part 下载。
6. 提交前硬校验器（字段/时长/切点/标签/中文泄漏/否定句）FAIL 即不提交。
7. 草稿 Turbo 4–6 步抽 2–3 seed，联络表先看一致性再看能量，VLM 四维评分，选中后同 seed 精修/二采，不换表演。
8. 一次只改一个变量，同一错误两批无改善回上层；失败码表定位责任层。
9. QC 硬门/软警 + ffprobe/黑帧/冻结/响度/联络表脚本 + 人眼复核必填；冷观众四问是 P0。
10. 每步一张选择卡，落盘产物 + 哈希/状态，上游变了下游自动 stale，重跑幂等。

## 未覆盖/未读完

- TFboy1 `references/hybrid-example.md`、`wenwu-director.md` 后半（八条生命通道 / 7 列镜头卡）与 `evals/evals.json`。
- 漫剧老李 `scripts/validate_prompt.py` 本体、`asset-spatial-ledger.md`（38 KB）、`style-bible/` 其余 9 份、sd‑storyboard‑engine 的 p45 预演故事板。
- infinite‑creation `lib/agent/agent-loop.js / tools.js / stages.js` 全文、`skills/tts-voice-design`、`docs/agent-architecture.md`；comfyui_original_workflows 未用 analyze.py 拆。
- JGRFW/comfyui‑AICG3D 的节点续接机制（按分工归另一人）。
- h3lite `references/component-sets.md / cinematic-prompting.md / prompt-assist.md / video-upscale.md`。
- chiphoton Codex‑Drama 的 `minimax-h3-comfyui/references/runtime.md`、`frame-to-video / video-editor / profile-distiller` 三个 skill、canvas 插件；DeepSeek‑Harness 的 `node-protocol-v1.md`。
- iv‑studio `src/`（不在仓库，排序算法只从 `test/ranking.mjs` 推断）；zxcHolmes `h3_engine.py` 具体采样参数与 `novel-adaptation-workflow.md`。
- TapCanvas `tapcanvas-video-prompt-writer/references/authoring-contract-v1.json`、`clip-design-and-packet.md`、`face-design.md`；reveric `references/video-prompts.md / model-capabilities.md` 全文。
- dramake 其余 20 份 references（format‑routing、directing‑camera、physics‑and‑failure‑modes 等）；senmanx `docs/` 其余 txt（打斗、封面、反推）。
- gary149、joeVenner `minimax-video/references/*`、okaypic `cast-format.md / edit-format.md`、killkli notebook、dseditor `troubleshooting.md`、Work‑Fisher 动效模式库、ancient‑rap‑battle `seedance_align.py`。
