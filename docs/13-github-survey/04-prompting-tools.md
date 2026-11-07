# 13-04 · 提示词工具 / 本地 Context-IR 复刻 / 提示词规则与案例库

> 范围：23 个仓库（提示词改写节点、本地 Context-IR 编译器、Agent Skill、案例库），以官方 `skills/h3-prompt-writing`（SKILL.md + base-en.txt + ref-en.txt）为基准。官方三段式 / 六段式格式本身见 `docs/04-prompt-engineering.md`，本文只记录各工具**额外**总结的规则、系统提示词、linter 检查项、反例与案例。
> 元数据取自 `survey/relevant.json`（2026-11-07 抓取）。源码级结论均来自浅克隆目录 `survey/repos/<owner>__<repo>/`。

## 本簇结论（先看这 10 行）

1. **立刻采用（读规则）**：`phileiny/h3-storyboard-skill`（实拍归纳的表演/对白/切镜纪律，含 PSNR 与 whisper 数据）、`ruashots/open-h3-ir` 的 122 KB 验证器（100+ 条命名规则，含帧格、1.2 s 镜头下限、台词零改写）、`JGRFW/comfyui-AICG3D-SKILLS` 的 h3-adapter（语速 3.5–5 字/s、否定句不进正文、9 图取材优先级）。
2. **立刻采用（本地工具）**：`pytraveler/MiniMax-H3-Prompt-Rewriter-ComfyUI` 的 Writer + Prompt Check + Reducer 节点（任意 GGUF，直接读 Ollama 模型库，~5–8 GB VRAM），以及 `duckyshell/ComfyUI-MiniMaxH3-Prompt-Writer`（Ollama 前端，Sequence 模式天然对应 30/60 s 多段）。
3. **本地 Context-IR 首选方案**：`open-h3-ir` 编译器 + Ollama（OpenAI 兼容端点）→ 输出经 100+ 规则校验的六段式；写作模型建议 `qwen3-vl:8b` 起步，`qwen3-vl:4b` 只够做参考图 caption / Reducer。
4. **案例库**：`SkyNotSilent/awesome-MiniMax-H3-cases`（781 条逐字公开 Prompt，`data/cases.json` 可按 `电影叙事`/`角色对白`/`动漫` 过滤）> `yangzhou-chaofan`（ostris 1K 数据集，官方三字段格式）> `BeatAPI`/`ai-boost`（自然语言风格为主）。
5. **观望**：`ethanfel/ComfyUI-MiniMax-H3-Guide`（Plan v2 编译器扎实，但 Qwen 增强要借 H3 自己的 32B 文本编码器 + 50–63 层 tail，<32 GB 显存“可能很慢”，GPL-3.0，8 月后未更新）、`1038lab Promptor`（两段式导演流程有价值，但系统提示词偏离官方格式：`[emotion]` 槽、台词带引号）、`T8mars enhancer`（Performance Director 概念好，但 27B Q4 本地 + 商业云为主，license NOASSERTION）。
6. **别碰 / 跳过**：`T8mars/minimax-h3-prompt-skill-T8` 不要 git clone（即便 `--filter=blob:limit=150k` 也会拉 3 GB pack，用网页/Electron 看）；`sengseng123` 标准化 skill 只有 5 KB 且鼓励“负面约束”段，与所有实测结论相反。
7. **六条跨仓库共识**：① 对白文字永远不经 LLM 改写；② 一镜一人开口、多人只在同框交代关系；③ 否定句不进正文（H3 无负向通道，词根会被渲染），唯一例外是一句“static, on a tripod, with no camera movement whatsoever”；④ VO 必须紧跟 lips-closed 子句；⑤ 切镜要带新信息、用五个官方切镜短语；⑥ 本地 LLM 用完立即卸载再跑 H3。
8. **帧格与时码**：H3 只生成 17k+5 帧，5.167–15.083 s 内只有 8.0 s 是整秒；10 s 请求实际 10.125 s；切点必须落在有效时长内且每镜 ≥1.2 s（open-h3-ir 从 ComfyUI `nodes_minimax_h3.py` 核对）。
9. **对白预算**：中文 3.5–5 字/s（JGRFW；phileiny 实测配音员 4.30 字/s）；单句 >24 字拆镜；有台词的镜头“整镜都在说话”，说完后的节拍放下一镜；台词节奏绑 seed 而不绑提示词。
10. **显存排程**：4090 上任何 ≥9B 的写作模型都要与 H3（int8 + qwen3vl_32b nvfp4 CLIP）串行；所有工具都提供“跑完卸载”（1038lab 自动释放、duckyshell Keep-loaded 关、chflame163 force unload、pytraveler keep_model_loaded、Ollama `keep_alive=0`）。

---

## 基准：官方 h3-prompt-writing skill 要点（供对照）

- SKILL.md 2.6 KB：按模式读 `base-en.txt`（15.8 KB）或 `ref-en.txt`（23.6 KB），“Preserve the exact field names, section order, labels, and timing notation”；4–15 s；标签一致；具体胜于抽象。
- base-en.txt：对齐行三种固定句式（I2VA `fully referenced` / FL2VA、L2VA `aligns with the S.SS-second mark`，S.SS=有效时长两位小数）；`[Shot 1]` 无时间戳；切镜短语五选一；运镜 = 类型 + 幅度 + 速度写成动作句；`(S1)`/`(S1,S2)`；VO 固定短语 `says in an off-screen voiceover` + 紧跟 lips closed；`<scenetrans>`/`<cutoff>`；soundscape 1–4 句、仅全程静音写 N/A；music 1–3 句只写乐器/速度/节奏/动态、禁情绪词。
- ref-en.txt：六段顺序；`<Subject N>` 可复用内容、`<Picture N>` 仅具体帧锚/分镜锚、`<Video N>` 整段结构、`<Audio N>` 独立编号；summary 以 `[task type + task type]` 开头（六种）；retention 标记四个视觉 + 四个音频固定值；detailed_description 350–500 词，对白密集以说完为准。
- 下文所有“额外规则”都以此为基线，只记录官方没写或与官方不同之处。

---

## 逐仓库精读

### pytraveler/MiniMax-H3-Prompt-Rewriter-ComfyUI（★420，MIT，最后推送 2026-11-04）

- **定位**：围绕 LightX2V 官方 Prompt-Rewriter LoRA 的 ComfyUI 节点包，同时提供“把官方 guide 塞进 system prompt 的任意 GGUF 写手”、参考图/音/视频 caption、linter、Reducer、效果 embedding、1000 条预设。README 212 KB，节点源码 `minimax_h3_rewriter/`（nodes.py 106 KB）。
- **三条 LoRA 路线（源码 `prompt_template*.py`，与训练模板字节一致，作者强调改一个字都会退化）**：
  - 27B：Qwen3.6-27B + LoRA，仅 T2VA；系统提示词只有 7 行（“You are a professional prompt rewriter for joint audio-video generation… Return only these three fields…”），用户消息固定 `resolution: 16:9 / duration: 10s / original_prompt: …`。VRAM nf4 ≈16 GB、GGUF 13–19 GB。
  - 8B：Qwen3-VL-8B-Instruct + LoRA（HF `lightx2v/MiniMax-H3-Prompt-Rewriter-LoRA-8B`，GGUF Q8_0 仅 0.69 GB），**能看首/尾帧**，覆盖 T2VA/I2VA/FL2VA/L2VA；系统提示词约 60 行，是官方 base 指南的压缩版，额外要求“Never invent dialogue, lyrics, visible text, speakers, or additional reference pictures”“Add a cut only when it introduces meaningful new … information. Otherwise prefer continuous camera motion”。nf4 ≈8 GB VRAM。
  - Omni：Qwen2.5-Omni-7B + LoRA，能看能听，唯一支持 Ref2VA 六段式的 LoRA；无 GGUF。
- **Writer 节点（无 LoRA）**：官方 guide 原文作为 system prompt（~4 000 token），`n_ctx` 自动抬到 ≥9 200（base）/ ≥12 300（ref），否则 llama.cpp 从**前面**截断把输出契约截掉。推荐写手表：Qwen3.5-4B Q4_K_M 2.6 GB/~5 GB VRAM，Qwen3.5-9B 5.3 GB/~8 GB（“best writing per gigabyte”），Gemma-3-12B，Mistral-Small-24B。`system_prompt` 可整体替换 → 同一节点可改写成 LTX/Wan 写手。
- **直接读 Ollama 模型库**（`ollama_store.py`）：扫 `$OLLAMA_MODELS`、`~/.ollama/models`，按 manifest 配对 mmproj，以 `ollama: qwen3:8b [qwen3, 4.7 GB]` 出现在下拉框；是读 GGUF 文件而非调 API，Ollama 服务可不运行。
- **Prompt Check / self-check（`checks.py`，纯正则，无模型）**：缺字段（→“lower the temperature, or try a larger writer model”）、对齐行缺失（I2VA 找 `fully referenced`，FL2VA/L2VA 找 `aligns with`）、`[Shot 1]` 带时间戳、编号跳号、切点不递增/≥时长、缺 `At MM:SS.mmm`、`<d>` 不配对、`<d>` 无 `[Language]`、标签超任务容量（CAPACITY：t2va 0 图；i2va/l2va 1 图；fl2va 2 图；ref2va 9 图 3 视频 3 音频）、已接入却未引用、每个 `<Subject N>` 必须有 retention 行、ref 正文 350–500 词、输出循环检测（同一块重复 ≥4 次且 ≥240 字符）、`embedding:` 大小写/粘连/句点。另记录 LightX2V runner 拒绝 **纵横比超 1:4** 的参考图与 **纯音频参考**，ComfyUI 原生节点则不检查。
- **fix_once**：默认关；开启后先机械补回对齐行，再把 findings 当规则**单次**重跑，只在更好时采纳。
- **Prompt Reducer**：先用规则剥掉全部脚手架（字段名、对齐行、`[Shot N] At`、标签、`<d>`），只把一段散文交给小模型压成一句——“这就是 4B 能做好的原因”。用途：改一个词再喂写手、把 H3 提示词喂给 Wan/Kling、给库条目起名。
- **Effect Embeddings**：10 个官方概念 embedding（Comfy-Org/MiniMax-H3 `embeddings/`），`[N,5120]` 已编码张量，花的是**长度**不是形容词（Art is explosion 50 位 … Four seasons 142 位）；需 ComfyUI ≥0.33.0；写法 `embedding:minimaxh3_bullet_time`，必须小写、前有空格、名末无句点。
- **Prompt Presets**：内置 ostris 1 000 条 T2VA 提示词 + 缩略图（6 MB），每条对应 ~5 s 片。
- **对 4090 短剧流水线的价值**：Writer(9B) + Check + Reducer 是最轻量、可脚本化的本地改写链；8B LoRA 是唯一能“看着首帧写对齐行”的轻模型（~9 GB）。27B LoRA 仅 T2VA，不值得为短剧占 16 GB。
- **坑**：Writer 只读文字，参考图要先经 Reference Caption（Qwen2.5-Omni-3B，3 s/帧）；H3 自带的 Qwen3-VL-32B 文本编码器**不能**复用为 LLM（无 lm_head、仅 50 层、词表不同）。
- **评级：采用**（Writer/Check/Reducer）；8B LoRA 试用。

### ruashots/open-h3-ir（★132，Apache-2.0，最后推送 2026-08-23）

- **定位**：“开源本地 Context-IR 编译器”。pip 包 `open-h3-ir`，CLI `h3ir compile/serve/doctor/budget/controls/directors`，HTTP `/v1/briefs`；ComfyUI 四节点在姊妹仓库 `ruashots/ComfyUI-OpenH3-IR`（★44，本簇未克隆）。后端任意 OpenAI 兼容端点（Ollama / llama.cpp server / LM Studio / vLLM）；参考图经该模型读取，所以需要视觉模型；作者全部用 Qwen3.6-27B 4-bit（vLLM，262K ctx，双 3090）验证。
- **核心机制（源码）**：
  - `grid.py` 对照 ComfyUI `nodes_minimax_h3.py` 固化帧格：`align_frame_count` 向上取到 `n % 17 == 5`；`video_latent_t = (n-5)//17*5+2`；音频 latent `round(n/24*40)`；训练带 124–362 帧（5.167–15.083 s），**只有 192 帧 = 8.0 s 是整秒**；10 s → 243 帧 = 10.125 s；S.SS 用**有效**时长；画布 32 倍数、短边 768、上限 768×1344；参考上限 9 图 / 3 视频 / 3 视频音轨 / 3 音频，参考视频 <5 帧报错。
  - `validate.py`（122 KB，100+ 命名规则，MUST PASS 官方样例 + 16 个单缺陷突变 MUST FAIL）。关键规则：`T12-cut-inside-the-floor` 每镜 ≥**1.2 s**（含片头到首切、末切到片尾）；`T7` 时长不在 17k+5 格；`P2/P3` 正文 <350（官方样例 336）/ >700 词；`P5/P5b` 运镜缺类型/缺幅度速度；`P7` 切镜短语不在官方五个之内；`R15-wardrobe-not-restated` 后续镜头提到主体却不提服装词；`R17-cut-states-nothing-new`；`R18-camera-as-label-stack`（`Camera: Push In, slow` 这种标签栈 → ERROR）；`R19` 裸写 `Subject 1` 无尖括号；`R12-pose-as-identity`（把参考图里的姿势当身份）；`R13-sheet-artefact`（把角色表的 FRONT/LEFT 标签、网格写进正文）；`D4/D5` 台词必须逐字节、`D7` `<d>` 内禁 `~ … !!` 与 emoji；`D8` S 编号断号；`D9` VO 后 400 字符内必须有 `lips … closed/shut`；`A8-music-mood-word`（melancholy/tense/eerie… 及 “creating a … mood” 句式）；`H1-unicode-hazard`（弯引号、全角括号、全角尖括号 → ERROR）；`H3-token-band`（已发表托管 IR 为 537–919 token）；`G1/G2` 推理泄漏与自我叙述；`S4` 代码围栏。
  - **台词不经模型**：`--say "…"` / ComfyUI `@speaks("…")`，模型只决定谁说、配什么嗓音、放哪里，渲染时字节级回填；跨切台词两半各带 `<scenetrans>`。
  - `creativity.py` 四档 restrained/balanced/bold/extreme（“explicit no dialogue at extreme still means no dialogue”）；`director.py` 七位导演只传“习惯段落”不传名字（“Type Wes Anderson at a model and it copies famous scenes”）。
  - `compose.v3.txt` 在官方 ref-en 全文后追加的自家规则（节选）：“Every shot states its camera — Static Shot is in the vocabulary, so ‘the camera does not move’ is a thing you SAY”；“Never write the camera as a header or a label stack”；“Never contradict your own camera. A push in moves closer…”；“overall_soundscape … is never empty and never N/A: a scene that exists makes sound”；“The score is the one section the request governs … otherwise it is exactly N/A”；“Straight quotes and plain apostrophes only”。
  - `docs/design.md` 成本实测（Qwen3.6-27B/vLLM）：ref-en 作 system 5 456 token、冷预填 3.25 s；1344×768 参考图 1 024 token，768×768 592 token，1536×1536 2 320 token——“一张满尺寸参考图 ≈ 整份 brief 的十倍成本，写长、附少”。
- **价值**：唯一把“帧格 + 规则 + 台词锁定 + 回退草稿”做成可测试编译器的项目，990 个单测无需模型；用 Ollama 当后端即是本地 Context-IR。
- **坑**：8 月后未更新（作者自称“young project, pin a commit”）；需 `ffmpeg` 读参考视频；`H3IR_LLM_MODEL` 多模型端点必须显式指定；验证器对自然语言风格提示词会大量报错（它只认官方六段式）。
- **评级：采用**（编译器 + 验证器，pin commit）。

### ethanfel/ComfyUI-MiniMax-H3-Guide（★343，GPL-3.0，最后推送 2026-08-11）

- **定位**：零依赖 ComfyUI 节点包，“Plan v2”类型化工作流：Project Setup → Image/Video/Audio Reference（声明角色）→ 每个真实切镜一个 Shot 节点 → Prompt Merge（确定性编译 + 校验）→ Apply Reference Plan（路由到原生 H3 节点）。`plan_v2.py` 215 KB。
- **额外规则/机制**：角色按意图选（身份/关键帧/动作迁移/编辑源/续接源/音色/配乐）；限制表“12 个混合参考文件、每段 2–15 s、视频累计 15 s、音频累计 15 s”；VO 编译固定附加 “The on-screen character's lips remain completely closed.”；`plan_enhancer.py` 要求 Qwen 每镜扩到 **80–140 个有效词**；`enhancer.py` DEFAULT_SYSTEM_PROMPT 强调“`subject_definitions` is the required section title, not a requirement to invent a `<Subject N>`”“Never add a generic main `<Subject 1>` merely because Ref2VA is selected”“If an `<Audio N>` row uses fully_copy … do not add, replace, remix … any audible event must already exist in that copied track”。
- **Qwen 增强**：CLIP 口接完整 Qwen3-VL/Qwen3.5，或接 H3 自己的 50 层编码器 + `qwen3vl_32b_minimax_h3_generation_tail_50_63_int8_convrot.safetensors`（ethanfel HF）补 50–63 层 + norm + lm_head 临时生成；“sub-32-GB operation is hardware-dependent and may be slow”。增强分 intent-locked / creative，输出 JSON 再由 Python 重建，任何触碰标签、时间、台词、路由的改动被忽略并回退确定性草稿。Prompt Review Gate 暂停队列让人改散文。
- **REFERENCE_MEDIA_PRACTICAL_GUIDE.md**（值得改写进 skill）：构图参考用 `Storyboard or shot planning` 角色 + `weak_reference`；草图能控“广义构图”不能控身份/解剖；准备图：目标画幅、短边 ~768、剪影分明、**不要画箭头/标签/网格**，映射说明写进 role notes 而不是画进图；位置词表 `screen-left / left third / 25% of frame width / foreground / eye-level`；动作参考用“带朝向线的圆”区分平移与转头。
- **价值**：读它的编译规则与参考媒体指南；节点本身对“先抽卡再精修”的短剧流程偏重。
- **坑**：GPL-3.0；tail 方案在 24 GB 上不可靠；多数示例工作流标 WIP。
- **评级：观望**（规则采用，节点不装）。

### 1038lab/ComfyUI-MiniMax-H3-Promptor（★264，GPL-3.0，最后推送 2026-09-12）

- **定位**：`H3_Vision`（多模态分析）+ `H3_Promptor`（文本结构化）解耦；云端 API（OpenAI/Gemini/Claude/DeepSeek）或本地（Ollama、LM Studio、llama.cpp、ComfyUI-QwenVL GGUF）；v1.5.1 本地模型推理后自动释放显存且不驱逐 ComfyUI 模型。
- **系统提示词（`templates/system_base.txt`）关键段**：“Treat all provided references … as your production ensemble”；“NEVER create an isolated slideshow (PPT)”；“**STRICT SHOT BUDGET BY DURATION (MANDATORY TO AVOID VIDEO FLICKER)**: 2.5s–4.0s per shot: 4–6s → 1 or 2 shots; 7–10s → 2 or 3; 11–15s → 3 to 5. NEVER create 1-second fragmented cuts”；“Action in [Shot 1] must trigger the reaction or consequence in [Shot 2]”；“NEVER invent custom tags like `<Environment 1>`”；输出只写 `[Shot N]` 段落 + `Audio:`/`Music:` 两行，六段式标题由 `post_processor.py` 机械补全。
- **两段式导演**：Stage 1 Blueprint（Global Vibe / Ensemble Roles / 均匀节拍，“15s = 4 shots, 5s = 2 shots”）→ Stage 2 Storyboard（必须“物理地编织”所有可用标签）。
- **偏离官方之处（反例）**：台词格式写成 `<Subject N> (SN) [emotion/action] says: <d>[Language] "…"</d>`——`<d>` 内带引号、示例中文叙述且出现 `<d>…<d>` 闭合错误；“Hollywood Film Director”式角色扮演会推高形容词密度。
- **评级：试用**（借鉴镜头预算与两段式流程；用它生成后务必过 linter）。

### duckyshell/ComfyUI-MiniMaxH3-Prompt-Writer（★302，MIT，最后推送 2026-10-28）

- **定位**：ComfyUI **UI 扩展**（不是节点）：Creative Brief → 官方 guide 作契约 → 可编辑提示词；Media Editor（裁剪/抽帧/提音频）、Media Composer（拼接参考图）、浮动 Media 面板拖进工作流；另有 Windows Standalone。Provider：Ollama（推荐）、Direct GGUF、外部 llama.cpp、API。
- **Ollama 实测表（5090 测得，“起点非下限”）**：<8 GB `gemma4:e2b`、8 GB `gemma4:e4b`、12–16 GB `gemma4:12b`、**24 GB `gemma4:26b`**、32 GB `gemma4:31b`；Qwen 3.6 五模式全过。`num_ctx` 自动在 8K/16K/24K 中取最小够用值；Thinking 仅模型支持时开放；Keep model loaded 关则请求后卸载。
- **系统提示词（`backend/system_prompts.py`）额外规则**：优先级“explicit user instruction → assigned reference roles → defaults”；“Do not introduce cuts or camera movement solely for cinematic embellishment … otherwise retain a continuous-shot structure”；“never infer music from mood, style, or cinematic language”；Ref 模式“target 450–500 English words”；“a motion-only video must not contribute its performer identity, clothing, location, background, lighting, or audio”；“Never mention a contact sheet, cells, sampled frames … never create one target shot per cell”；“Audio files are not heard by the local model: infer fully_copy/partially_copy/reference/weak_reference only from the user's stated intent”。
- **Sequence 模式**：一份 brief 拆成多段独立提示词（共享媒体、逐段编辑），Official（官方六段）或 Compact（散文 + 两个声音字段）契约；`validate_compact` 校验：无 Markdown 围栏、无官方段名、标签必须存在于本段媒体、时间戳 <本段时长、本段 Shot 从 1 编号、`<d>` 配对。“A chunk boundary is not a cut.”
- **Brief 写法指南**：说清发生什么 / 哪张参考供哪一项 / 什么必须不变 / 精确台词与可见文字 / 哪些细节不许迁移；角色词可以很短（`use for appearance` `clothes only` `movement only`）。
- **价值**：最省事的 Ollama 前端；Sequence + 16:9 直接对应“30 s = 2–3 段”。
- **坑**：不入图、不排队；本地模型看的是视频接触表而非原视频。
- **评级：采用**。

### T8mars/comfyui-minimax-h3-prompt-enhancer-T8（★392，NOASSERTION，最后推送 2026-11-02）

- **定位**：一体化增强器（H3 + Seedance 2.0 + MiniMax Music 3 + Qwen Image），云提供商（ZhenZhen 等）或本地 GGUF（扫描 `ComfyUI/models/LLM/`；安装器拉 `Qwen3.8-27B-Q4_K_M.gguf` 15.9 GiB + `mmproj-F16.gguf` 0.86 GiB，或 9B heretic Q6_K 6.85 GiB 无 mmproj；“24 GB 以上推荐”）。首次 clone 目录为空，二次 clone 正常。
- **额外规则**：rewrite 温度档 strict 0.2 / balanced 0.7 / creative 1.2；H3 时长字段“任意正整数秒、不设上限”；**Performance Director Config**：AUTO 仅在有人物/情绪/对白时注入，Strong 把表演组织为 **trigger → reception → one primary response → settled/end state**，把抽象情绪转成 gaze/eyelid/breath/shoulder/hand/posture 可观察线索，每拍每角色 ≤3 个高信号通道，先定机位侧 + 具体视线目标再写面部；锁定用户点名的身体部位/颜色/左右关系/引号文字（“the pupil turns gold 不得改成 iris”）。作者注明该功能受 `phileiny/h3-storyboard-skill` 启发并 pin 了 commit。
- **测试即规范（`tests/test_h3_quality.py`）**：对齐行必须精确且 FL2VA/L2VA 校验真实末镜号；两人不能共用一个 S 号、同一人不能被重编号；跨切台词三段仍是一句原话；`soundscape/music` 不得复述台词；角色可听见的音乐不能进 non_diegetic；VO 用闭唇且不改字；“visible sign says” 不是说话人；修复只做局部、幂等、不改时间戳；接受更正仅当问题减少且不丢任何原有台词。
- **坑**：license 文件非标准（NOASSERTION）；节点 165 KB 巨石；仓库含 2.7 MB case_templates/catalog.json。
- **评级：试用**（借 Performance Director 四拍法与测试清单）。

### BMB12d3/minimax-h3-prompt-composer（★309，无 license，最后推送 2026-08-28）

- **定位**：单文件 `Prompt_Composer.html`（1.3 MB）离线可视化编排器 v5.43：Shots/时间/运镜/对白/连续性/声音控件 → 组装六段式并 **Prompt Check**（结构、时间、参考、对白、音频、运镜、连续性、输入映射）；Camera Builder + 可视化机位规划；引导式插入/替换/重打光/表演迁移/续接流程；本地抓帧；AI Project Setup 可导出上下文给外部 LLM 再导回 JSON。附 PDF 手册两份（0.9/1.4 MB）。
- **价值**：手写 Ref2VA 时的“表单 + 检查器”，无需任何模型；Camera Planner 把路径转成一句自然运镜。
- **坑**：无 license；不读像素；更新到 8 月末。
- **评级：试用**。

### chflame163/ComfyUI_Qwen_H3_Prompt（★145，MIT，最后推送 2026-10-28）

- **定位**：在 ComfyUI 内拉起独立 `llama-server`（跨平台安装器固定 llama.cpp b11115，自动选 CUDA/Vulkan/Metal），用 **Qwen3.8-27B GGUF + mmproj** 执行**官方 skills 原文**（内置 9 个官方 skill，可加 `custom_skills/`）。20 GB+ 显存推荐 Q4_K_M；16 GB 用 12 GB abliterated 版。`force unload model` 默认开，每次跑完杀进程。
- **路由规则**：0 图 → T2VA；1 图 → Qwen 依据提示词选 I2VA/L2VA/Ref2VA；2 图 → FL2VA/Ref2VA；3–9 图或任何视频 → Ref2VA。**1–2 张图必须在提示词里写明时间角色**（“将 Picture 1 作为目标视频的首帧…”），否则不猜。参考视频 ≤3 路、每路 ≤15 s、总 ≤15 s、按 24 fps 计、默认 2 fps 抽帧成接触表。
- **边界声明**：Qwen 不能分析音频（无法提 BPM/歌词/音色）；“只执行一次本地推理，不额外包装、改写或按 H3 结构修复”——需要外接 linter。
- **价值**：最接近“官方 skill + 本地 27B”的复刻；think_mode 切换 Qwen 官方 instruct/thinking 采样参数。
- **坑**：27B Q4 ≈16 GB，与 H3 必须串行；安装器要先跑；节点不校验输出。
- **评级：试用**（4090 够跑，但速度/显存权衡不如 9B + open-h3-ir 校验）。

### benjiyaya/ComfyUI-H3-VisionPromptor（★119，MIT，最后推送 2026-08-09）

- **定位**：把 ComfyUI `CLIPLoader` 加载的 **Qwen3-VL-4B/8B-Instruct 或 Gemma-3/4 文本编码器 repack** 当生成式 VLM 用（零 pip 依赖、不走 API）；Qwen2.5-VL repack 在当前 master 只有 vision tower，会报 `not generatable`。
- **系统提示词 `prompts/h3_system_base.txt`（23 KB）**：官方 base + ref 两份指南的忠实压缩，外加：模式由图片数量与角色推断（用户显式说明优先）；“Respect the word budget … never with filler, repetition, or abstract mood words”；“Use ONE primary camera move per shot”；QUALITY BAR：具体名词动词 / **一镜一主动作** / 身份锚点（发型、年龄、性别、带颜色的服装、标志配饰）每镜自然重复 / “EVERY NOISY ACTION GETS A SOUND” / 薄创意要扩到词预算。
- **词预算（`prompt_builder.py`）**：base 模式 = 时长×25 词；Ref2VA = 时长×35、封顶 500。`post_processor.py` 去 `<think>`/围栏、补对齐行、校验时间戳递增与 ≤时长。
- **评级：试用**（系统提示词可直接拿来当“单文件版官方 skill”喂 Ollama；节点依赖 ComfyUI repack 格式，8 月后未更新）。

### benjiyaya/Minimax-H3-Prompt-AgentSkill（★160，无 license，最后推送 2026-08-06）

- **定位**：Hermes Agent skill（SKILL.md 15 KB + base/ref 格式参考 + 68 KB creative-showcase）。流程：Step 0 判模式 → Step 1 参数（默认 8 s、16:9；镜头预算 4–6s 1–2、7–10s 2–3、11–15s 3–5）→ Step 2 七维增强（Camera Identity / Visual Texture / Pacing Arc / Character Detail / Spatial Geography / Continuity Progression / Sound Design）→ Step 3 格式化 → Step 4 呈现与假设声明。
- **可借的规则**：每角色一个“visual signature”颜色锁；连续性递进（损伤累积、头发变乱、道具位移）；屏幕方向向量（Left→Right, Deep→Front）；“Avoid named third-party IP, real celebrities”；Pitfalls 10 条（角色表不是 `<Picture>`、一镜多动作、忘写运镜、身份不重复、镜头数超预算、diegetic/non-diegetic 混放、发明标签、改写台词、缺风格开场、平坦时间戳）；校验清单 13 项。
- **评级：采用（作为规则文本）**，不装运行时。

### Adudeguyman/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder（★319，MIT，最后推送 2026-10-17）

- **定位**：节点内可视化手填编辑器（按模式给模板，右侧实时组装）+ Media Loader（图/视频/音频，拖排序决定标签号）+ 提示词库 + RefMods（预编码参考包）+ 遮罩编辑。
- **实时检查项**：镜号顺序、切点递增且 <时长、`[Shot 1]` 无时间戳、`<d>` 配对且有语言、接入却未提及的参考、Ref 模式每个 subject 有 retention 行；琥珀=建议、红=必修。
- **额外写法**：给 subject 起名 → 定义行追加 “Their name is Bob.”，正文可用 `!Bob` → 渲染为 `<Subject 1> Bob`，在 `<d>` 内只渲染 `Bob`（“nobody says a label out loud”）；音色框 → “It is Ann's voice: low, husky …”，说话按钮生成 `!Ann (S1), in the low, husky voice … referenced from <Audio 1>, says: <d>[English] </d>`；**短语库插入时压平换行，“因为模型把换行读成切镜”**；每行可开关以应对临时拔掉参考。
- **评级：试用**（手工精修场景）。

### T8mars/minimax-h3-prompt-skill-T8（★325，MIT + CC BY 4.0，最后推送 2026-11-01）

- **定位**：Creative DNA 案例库（README 320 KB）+ 可安装 Skills + Electron 桌面查看器；索引 9 个官方 skill（只存 commit/SHA 不复制正文）；2 个非官方 skill（街拍采访、惊吓到和解）。案例入库原则：可追溯原帖、机制拆解、H3 与 Seedance 两份校验过的提示词、anti-copy 说明；明确“技术教程/Benchmark/工作流不收”。
- **坑**：`git clone --depth 1 --filter=blob:limit=150k` 仍会下载 3 GB pack（含媒体），本次已中止并删除；只能 curl README 或用 Electron。
- **评级：观望**（当灵感库用，不要当规则源）。

### LoveRain1997/h3-prompt-journal（★259，MIT，最后推送 2026-11-06）

- **定位**：26 篇实测日记（多为舞蹈/MV，6–18 段 90–230 s 长片），每篇 README + 可粘贴 prompt.md；另含《凡人修仙传》拉片 558 条 IF-THEN 规则。
- **核心纪律（README 原话）**：“音乐时间轴驱动一切 · 每段自包含 · 图 1 零外貌 · 全局规则拼进每一段（禁止规则段压底） · 卡点=onset · 分段间局部特写+动作续接 · 转场写成‘动作钩子+切点原因+下段续动’”。
- **007 两段式 30 s 电影感角色揭示**（最贴近短剧）：两段独立生成，用“接缝契约”六条镜像写进两段（同角色/服装/场景、末帧=下段首态、“Do NOT restart the music”、环境音不换、**点名禁止重复的六种镜头机制**、姿态库纪律）；“Part 1 的最后 1.4 s 与 Part 2 的前 0.9 s 作为一次呼吸设计”；像素优先级 脸 > 眼 > 手 > 环境。
- **摄影机纪律库（System B）**：“动作负责舞蹈，摄影机负责观看”——每段一个主运镜行为，只为重大空间变化而动；十条物理法则（POSITION/NO DEGREE/OPTICAL-AXIS/…/HERO LOCK）；13 词物理词库（PUSH-IN/TRACK/WRAP/RISE/DROP/OCCLUSION/REVEAL/WHIP PAN/RECOIL/HERO LOCK…每个词 = 起点 + 触发 + 终点）；反目录（不要每拍都动、不要随脚步 bob、无指定不 orbit/whip）；五件套块 POSITION/GEOMETRY/MOVEMENT/TRIGGER/END POSITION，静止段也要写 `MOVEMENT: none`。
- **反例警示**：其提示词是大段自然语言 + 大量 “Do not …”“No cartoon …”——与 phileiny/JGRFW/alesha 的“否定不进正文”结论相反；作者产出靠多段抽卡与后期，不能当格式范本。
- **评级：采用**（30/60 s 分段与接缝契约的方法论；格式不照搬）。

### SkyNotSilent/awesome-MiniMax-H3-cases（★218，MIT，最后推送 2026-11-07）

- **定位**：3 145 条可播放案例、781 条逐字公开 Prompt、26 篇教程；`data/cases.json`（10.5 MB）字段：`prompt / mode / duration / aspectRatio / tags / category / styles / promptProvenance(creator-verbatim) / verified / featured`；`CATALOG.md` 按 T2VA 等分组；三个 agent skill（prompt-library / tutorial-guide / submission-helper）；网站带 `llms-full.txt`（6.6 MB）。
- **用法**：`python3 -I` 读 cases.json，过滤 `prompt` 非空且 tags 含 `电影叙事`/`角色对白`/`动漫`，本次命中 141 条，可直接作为短剧提示词库（见下文案例）。
- **评级：采用**（数据源）。

### BeatAPI/awesome-minimax-h3-prompts（★209，NOASSERTION，最后推送 2026-10-07）

- **定位**：550 条带 webm 预览的提示词，`prompts/catalog.json`（2.9 MB，字段 slug/title/category/mode/duration/aspectRatio/ingredients/source/prompt）；按 use-case 分 Stories & Films / Action & Fantasy / Ads / Music 等。
- **观察**：含 `<d>` 或 `[Shot 2]` 的官方格式提示词仅 2 条，其余是 `Scene 1 (0–3s)` 自然语言 + “8K photorealistic, blockbuster” 式堆词；商业导流（BeatAPI 代理）。
- **评级：观望**（找镜头创意可以，格式别学）。

### gnipbao/minimax-h3-video-reverse-skill（★305，MIT，最后推送 2026-10-02）

- **定位**：Claude/Codex skill（SKILL.md 20 KB + 8 份 references + 校验脚本）：**先复述视频内容与叙事逻辑并等用户确认，再反推**；五遍读片（全局 → 真实切镜 → 连续覆盖 → 关键动作加密 → 首尾倒查）；事实状态 `observed/uncertain/user_requested`；输出 AUTO/T2VA/I2V/DUAL；I2V 每个真实 Shot 独立 Job（I2V-A 单图 / I2V-B 首尾帧仅平台确认支持时）。
- **可借规则**：“被遮挡不等于消失，出画不等于落地”；“镜头约束针对实际风险，没有风险填 N/A，不要全片复制‘无运动、无变形、无文字’”；“必要的稳定要求合入主描述，不额外发明 negative_prompt 字段”；时间码补零只是序列化不代表精度；`scripts/validate_prompt.py --mode I2VA --duration 4` 做格式门槛。
- **评级：试用**（把参考电影/漫剧片段反推成分镜时用）。

### phileiny/h3-storyboard-skill（★191，MIT，最后推送 2026-10-03）

- **定位**：105 KB 繁中 SKILL，“教你怎么想”，每条标验证状态（Ref2VA 243 帧实拍、固定 seed、PSNR/whisper 逐字计量）。T8 enhancer 的 Performance Director 即源于此。
- **第一定律**：一镜装不下多个表情节拍——7 s 特写塞 9 拍 PSNR 37–42 dB（≈冻结帧），拆成三颗 2–3 s 各一拍降到 22–23 dB，加 `<d>` 再到 19 dB；**大肢体武打例外**（3 s 塞 8–9 招可行，拆镜理由改为换角度）。
- **`<d>` 偷时间**：有台词的镜头被重新分配到更多帧（74→84），代价是其他镜头被压缩、背景元素消失；要背景延续的镜头不要与台词同片。
- **台词长度硬约束**：外挂真人配音时 `字数 ÷ 语速（实测 4.30 字/s）= 需要秒数` 与该镜长度比；VO 不受限；**“H3 把整个镜头都当成那个人在讲话，不会在下一拍收嘴”**——讲完后的拍子放下一镜。
- **不要写“什么都不变”**：会外溢整镜冻结；停顿交给剪接。三种“不动”：物件静止写正面状态（“笔与资料夹距离第一格到最后一格一样”）；人的静止写小事（呼吸/眨眼/重心）；摄影机静止只写一句，**多写 `no push in / no zoom / no dissolve` 反而让切点漂到 3.5 s 后**。
- **多人场**：同框只交代关系，“台词一律单人正反打”，机位放在听者视线上；对象偏离轴线 25–40° 为自然四分之三，<15° 像看观众；单人镜前景不放路人。
- **禁用字对照表**（§五之三，节选）：`nothing about her changes` → 写小动作；分数/厘米尺寸被忽略 → 用画内物体当尺；`lips parted as if about to speak` → 真开口讲 2 s；`continuing / says the rest / And 开头` → 假起头重讲；旁白里 `say/sentence/word/line` → 被念出来；共用段写“落地灯暖光”→ 每镜长出那盏灯；`she holds the camera` → 相机被画成道具；`motion blur/particle trails` → 写因果（袖子甩直）。
- **台词重讲三成因 + seed**：接续暗示、语速两处矛盾、未写“只讲一次”；**说话节奏绑 seed**（两份不同提示词同 seed，whisper 逐字时间到小数点后两位一致）→ 声音坏先换 seed，有台词镜头一次跑 2–3 seed。
- **切点漂移**：一颗生成内的切点整体后移 ~1.2 s（规格 2.0 → 实测 3.21），但段内相对节拍准 → 瞬时效果绑事件不绑时间戳；引子多写 1.5 s 余裕；跨切点曝光跳 ~45%，提示词写“曝光一致”无效，后期逐段套曲线。
- **验收**：`mlx_whisper --word-timestamps` 逐字对照（重讲、假起头、晚开口、提示词被念出）；一张脸被读懂只需 1.5–2 s。
- **评级：采用**（短剧 skill 的表演/对白章节主干）。

### sengseng123/minimax-h3-prompt-standardizer（★94，无 license，最后推送 2026-08-24）

- **定位**：5 KB Codex skill，中文输出模板（【任务设定】【图片上传顺序】【MiniMax H3 主提示词】【防错约束】），把“震撼/高级/电影感”替换成具体构图光色；“Never split the same unfinished composition, pose, action phase, or emotional state across independent generations”。
- **问题**：输出不是官方三/六段式；写作顺序第 7 步“Stability and negative constraints”与多方实测相悖；无 license。
- **评级：跳过**。

### unknowlei/minimax-h3-opencode-skills（★131，MIT，最后推送 2026-08-09）

- **定位**：7 个 OpenCode skill 的路由系统：creative-director 总入口 → multishot-planner（逐镜询问确认）→ text/reference/keyframe 三个写手 → prompt-reviewer。核心路由：**普通图片默认 Ref2VA**，只有用户明确“纯首帧/尾帧且不承担参考”才走 I2VA/FL2VA/L2VA；≥10 s 未说明镜头数先问是否多镜。
- **可借**：`prompt-reviewer/references/validation-checklist.md`（9 组检查：模式结构、时间线、运镜语义 Zoom≠Push/Pan≠Truck/Tilt≠Pedestal、语音文字、声音分层、全参标签、全参内关键帧需 `keyframe completion`、双语输出、交互提问）；`shot-choice-library.md` 景别/运镜/转场/开场选项库（J-cut/L-cut、match cut、fade in）。
- **评级：试用**（检查表并入 skill）。

### JGRFW/comfyui-AICG3D-SKILLS（★135，GPL-3.0，最后推送 2026-10-28）

- **定位**：独立 ComfyUI 提示词插件：模型设置（OpenAI 兼容/Gemini/RunningHub/本地 Transformers 与 GGUF）→ 参考素材整理 → `H3 提示词推理` → `H3 提示词检查`（H1–H12）；内置 `minimax-h3-short-drama-director`（由 Seedance 版短剧导演 skill 适配，含 40 份 references）+ 打包 T8 的 284 个 Skill；数字人模式用 whisper 识歌词与时间码、wav2vec2 判男女声、“当前演唱者保留完整嘴部，另一位完全在画外”。注意仓库名在 relevant.json 中为 `comfyui-AICG3D-SKILLS`，本地另有 `JGRFW__comfyui-AICG3D`（主工作流插件，属其它簇）。
- **H1–H12 检查（`scripts/validate_prompt.py --model h3`）**：H1 字段集；H2 Shot 1 无时间戳 / 切点递增；H3 时长 4–15 s；H4 `<d>` 语言标签；H5 标签先定义后引用、summary 不引新标签、定义 >9 告警、定义未引用告警；H6 retention 合法值且不写 (Sx)；H7 S 编号按首现递增；**H8 泄漏：七段式栏名/`@` 锚点 FAIL，工作流术语/否定式 WARN**；H9 画外声紧跟闭口证据、禁 `{}`；H10 soundscape/music 不含 `<d>`、BGM 不复述台词；H11 发言人首现缺语气/音色/语速 WARN；H12 首镜无具名主体 / 并列主体句式 / 悬空指示代词 WARN。
- **h3-adapter.md 额外规则**：“正文只写‘有什么’——否定式一律不进 H3 正文，被禁概念的词根（不发光里的‘发光’）照旧被渲染”；反光道具零光效只写材质本色；**9 图取材优先级**：具体帧锚图 > 主角（4 View 板算 1 张）> 核心场景拼接图 > 配角 > 道具拼板 > 动作/运镜视频 ≤3 段 > 音色/BGM ≤3 段且必须挂图或视频；超限的降级为文字写进 `<Subject N>` 定义行；“给了图却一次没提到 = 白占一个位”。首镜锚定句只许一个具名主体（实测并列句出“两张脸”）。
- **dialogue-speed-check.md**：标准 3.5–5 字/s、慢速 <3.5（金句/遗言）、快速 >5（连续不超 3 s）；口播时长 = 可发音字符 ÷ 语速 + 标点停顿（逗号 0.1–0.3 s、句号 0.3–0.6 s）+ 情绪停顿；单句 >24 字强制拆 2–3 镜（每镜 ≤18 字）；金句后留 0.3–0.8 s 无对白反应镜；语气词决定语速档（气音/一字一顿 → 慢档）。
- **vo-os-weaving.md**：VO+OS 每分钟 ≤60–80 字（15 s 段 ≤20 字）；OS 发声时画面角色绝不张嘴，写“嘴唇紧闭”的闭口神态；VO 不翻译画面——“把旁白删掉，画面信息量不得减少”。
- **坑**：导演 skill 是 Seedance 七段式体系移植，大量 `【站位声明】` 等栏名若泄漏进 H3 正文会被 H8 判 FAIL；GPL-3.0；节点依赖多（whisper、可选 wav2vec2）。
- **评级：试用**（规则与 H 系列检查采用；插件按需）。

### wildminder/awesome-minimax-H3（★600，无 license，最后推送 2026-11-06）

- **定位**：生态索引（blocks/ 按模型/编码器/组件/LoRA/节点/指南/工作流分块）。本簇相关：`blocks/50_guides.md` 的 Prompting & Prompt Datasets（yangzhou 1K 整理、neta.art 1 000 片交互图集、JiaYang-BUAA Codex 自动成片 skill）；`blocks/40_nodes.md` 列出全部 Prompt 类节点（含本文未读的 ethanfel/ComfyUI-H3-Prompt-IDE、Hearmeman24/MiniMaxRefPack、gabxav/Vision-Prompt-Composer、NyckM/H3-Relight、matlowai/ComfyUI-Dials 提示词对转向滑块）以及 **LightX2V 全部改写模型**：LoRA-8B（Qwen3-VL-8B，GGUF Q8_0 0.69 GB ★推荐，不支持 Ref2VA）、Qwen3.5-9B-Ref2VA / -FL2VA 全量 SFT（vLLM，18 GiB，32K ctx，Apache-2.0）、Qwen3.8-27B-Ref2VA / -FL2VA（51 GiB，无 LICENSE 文件）、LoRA-Omni（Qwen2.5-Omni-7B，无 GGUF）；10 个概念 embedding 名单。
- **评级：采用（索引）**。

### ai-boost/awesome-image-video-prompts（★3452，GPL-3.0，最后推送 2026-11-07）

- **定位**：跨模型提示词画廊（README_zh 中 MiniMax H3 条目 12 条，`pages/zh/video-dialogue.md` 57 条）；每条带出处、赞数、标签与一句点评。H3 条目多为自然语言：角色参考蒙太奇（20 镜硬切、脸始终出画）、玛雅剧片头字幕（逐 3 s 节拍 + 精确字幕文本）、Rem 桌面动画（首帧锁定、0–2s/2–3s 时间段）、Friends 沙发对白（角色名逐行 + 动作停顿 + STYLE 段 + “Hold on Chandler's face … for a full beat before cut”）。
- **评级：观望**（创意取材；格式需改写为官方三段式）。

### yangzhou-chaofan/minimax-h3-1000-prompts（★14，无 license，最后推送 2026-08-21）

- **定位**：对 HF `ostris/minimax_h3_1k`（1 000 条三字段提示词 + 768p 片，`minimax_h3_fl2va_pruned_int8_convrot` 30 步生成）的索引与 10 条精选；neta.art 交互图集。强提示词的五个共性：**开头定媒介与调色**（“Live-action, modern cinematic film with anamorphic flares…” / “Shot on 35mm black-and-white film, dense grain…”）、**点名运镜**、`<d>[English] …</d>` 行内台词、**soundscape 是具体声源逗号链**、**music 刻意 N/A**。
- **评级：采用（数据）**；pytraveler 的 Presets 节点已内置同一数据。

---

## 高质量案例原文（电影质感 / 漫剧风格，注明来源）

> 均为公开逐字提示词（节选到约 1 500 字符）。★ 为官方格式，可直接喂 ComfyUI；其余是自然语言风格，需改写成三/六段式再用。

**案例 1 ★ Rooftop heist（ostris/minimax_h3_1k #000，经 yangzhou-chaofan 整理）**
```
integrated_multimodal_description: [Shot 1] Live-action, modern cinematic film with anamorphic flares and rain-slick night textures, a handheld tracking shot follows two thieves sprinting across a wet rooftop, satchels of stolen bearer bonds bouncing on their backs. The wiry East Asian woman in a black windbreaker (S1), her voice sharp, breathless, and quick-paced, vaults an air duct and shouts: <d>[English] Don't slow down — jump!</d> Her partner, a stocky bearded Black man in his forties, hurdles a vent pipe and clips a stack of paint cans that clatter away behind them. [Shot 2] …
overall_soundscape: Pounding footsteps on wet tar, steady rain patter, distant police sirens, paint cans clattering, ragged breathing, two heavy landing grunts, gravel scattering, a burst of pigeon wingbeats.
non_diegetic_music: Staccato string ostinato over taiko-style drums at fast tempo, rising dynamics with a crescendo hit on the landing.
```

**案例 2 ★ Film-noir office break-in（ostris #120）**
```
integrated_multimodal_description: [Shot 1] Shot on 35mm black-and-white film, dense grain, hard scratches raking the frame, deep shadow crush, and an occasional exposure flicker typical of a dupe print, in a cramped office lit only by the amber glow of a desk lamp. A middle-aged white woman in a belted trench coat and slouch hat bursts through a frosted-glass office door, snatches a manila dossier off the desk, and shoves a tall filing cabinet crashing over to block the doorway behind her. Venetian-blind shadows rake across her face as she wrenches open the sash window, swings her legs over the sill, and drops onto the iron fire escape. The camera trucks right…
overall_soundscape: Door glass rattling, papers sliding across a desk, a filing cabinet slamming to the floorboards, a window sash screeching, iron fire-escape steps clanging, street steam hissing, a distant foghorn.
non_diegetic_music: Solo muted trumpet, slow tempo, a single sustained low note under the voiceover, a soft cymbal roll.
```

**案例 3 ★ open-h3-ir 编译输出（ruashots/open-h3-ir README，Ref2VA，10.125 s，Qwen3.6-27B 写成）**
```
subject_definitions:
<Subject 1> is the woman in <Picture 1>, with short dark hair with shaved sides and a small top knot, dark complexion, black tactical jacket with shoulder straps and buckles, black t-shirt, black cargo trousers, black lace-up combat boots, slender build.
[…]
detailed_description:
The target video is in a cinematic, high-contrast style with realistic 3D character design, featuring cool blue tones and wet, reflective surfaces.
[Shot 1] A medium-long tracking shot follows <Subject 1> from behind as she walks out onto a wet, metallic gantry in the rain. The camera tracks slowly with small amplitude, keeping her centered in the frame as she moves away from the viewer. […]
[Shot 2] At 00:05.000, the shot cuts to a close-up of <Subject 1> from a slightly low angle as she stops at the edge of the gantry. The camera is static, focusing on her face and upper body. She looks down, her expression shifting to one of quiet contemplation as she sees the city below. […]
```
（验证器报两条 WARN：P2 正文 265 词 <350；R15 Shot 2 未重述服装。）

**案例 4 ★（混合）2D 漫剧式双人对白（SkyNotSilent `x-2086063980234035362`，@Cardoso，T2VA 15 s 横屏）**
```
Style: Adult animated television comedy in the distinctive flat-vector / limited-animation style of a suave-spy cartoon. Bold inked outlines, flat cel-shaded colors, slightly stiff comedic timing, hard graphic shadows, subtle film-grain texture. 2K, cinematic but comedic.
Setting: A bright sunny beach. Clear blue sky, soft sand, ocean waves in the background.
Characters: … a handsome secret agent with jet-black slicked-back hair … / a tall, striking brown-skinned female agent …
Shot 1 (0:00–0:03): Medium shot of the two standing on the beach. He cups his hands around his mouth and calls out: <d>[English] Lana? Lana? LANA!!!!</d>
Shot 2 (0:03–0:05): Cut to her turning sharply toward him, annoyed: <d>[English] What?!</d>
Shot 3 (0:05–0:07): He leans in with a smug grin: <d>[English] …</d>
… Shot 9 (0:13–0:15): He raises both hands defensively, looking genuine: <d>[English] That's not me!</d>
overall_soundscape: …
```
（要点：一镜一人一句、`<d>[English]` 标签、2 s 一镜的正反打节奏；缺点是用了 `Shot N (0:00–0:03)` 社区时码与角色真名。）

**案例 5 董事会谈判（SkyNotSilent `x-2086698076325253323`，@adithatipalli，T2VA 15 s）**
```
cinematic 15-second ultra-realistic sequence inside a luxurious modern boardroom during daytime. Soft natural light enters through large glass windows. Four powerful industrialists in expensive tailored suits sit around a long polished dark wooden table. The atmosphere is tense and high-stakes.
The senior industrialist at the head of the table leans forward slightly and says firmly: "This acquisition will change the entire market. Either we move now, or someone else will."
Another industrialist across the table adjusts his cufflinks and replies calmly: "Moving now is risky. The numbers still don't support a full takeover."
A third industrialist places both hands on the table and speaks with intensity: "Risk is the price of control. The investors are already waiting for our decision."
The camera slowly pushes in as the most powerful industrialist leans back, looks at everyone, and delivers the final line with quiet authority: "Then we take it. No more delays."
Cinematic lighting, sharp details on suits and the wooden table, subtle tension in their faces, realistic skin textures, high-end corporate atmosphere, shallow depth of field, filmic look.
```
（反例价值：4 人 4 句 15 s、无 S 号、无切镜 → 正是 phileiny “多人同框台词必乱”的场景；改写时应拆成同框建立镜 + 单人正反打。）

**案例 6 脱口秀节奏（SkyNotSilent `x-2087208466264076759`，@azed_ai，15 s 5 cuts）**
```
Style: Live stand-up comedy special, intimate comedy club, professional multi-camera production, warm stage lighting … 15-second video, 5 cinematic cuts
0–3s: [Wide Establishing → Medium Push-In] A comedian stands center stage holding a microphone as the audience settles. The comedian smiles and says: "I asked AI to organize my life yesterday" — Brief beat
3–6s: [Medium Close-Up] The comedian maintains a completely serious expression … Audience immediately laughs
6–9s: [Side Angle + Audience Reaction] The comedian waits for the laughter, then slowly nods … Quick cut to the front row laughing and clapping
9–12s: [Tight Close-Up] …
12–15s: [Medium → Wide Ending] … the camera pulls out to reveal the applauding club
Production details: Keep the same comedian, outfit, microphone, stage and audience throughout. Prioritize precise comedic timing, short pauses before punchlines … Never cut during a punchline. Audience laughter starts only after the punchline …
```

**案例 7 1935 柏林双参考短剧（BeatAPI catalog，@Cardoso，12 s）**
```
Use the <picture 1> as the exact first frame.
The video opens on the exact first frame from <picture 1>. Centered in the lower third of the frame, a clean elegant legend appears in classic yellow Fraktur typeface reading "Berlim, 1935". After a brief hold, the legend fades out.
[Shot 1] Bright sunny summer day in a tree-lined park. The blonde woman in the red-and-black geometric dress, black cardigan, wide-brimmed burgundy hat, black over-the-knee boots and yellow handbag stands on the path, then begins walking forward at a steady, unhurried pace. … Wide tracking shot follows her as she walks.
[Shot 2] At 00:04.000, hard cut to a wooden park bench to the side of the path. The man from <picture 2> sits on the bench casually scrolling on a modern smartphone … The man from <picture 2> says: <d>[German]Fräulein?</d>
[Shot 3] At 00:06.200, hard cut back to a medium side-tracking shot of the woman. Without breaking stride … she reaches into her yellow handbag with one hand …
```
（要点：每镜重述服装 = R15 正解；`[Shot N] At` 官方时码；缺点 `<picture 1>` 小写、“hard cut” 不在五个切镜短语内。）

**案例 8 试镜独白（BeatAPI catalog，@EndFolding79421，20 s）**
```
integrated_multimodal_description:
cinematic acting-audition performance. One woman, Chris, remains the only visible person throughout the entire video. Maintain the same face, hair, clothing, age, and identity for the full shot.
[0-4s] Medium close-up framing from the chest up. Chris stands tall facing directly toward the camera, holding a script page naturally in one hand. … She looks directly into the camera and introduces herself in her normal speaking voice.
(S1, Chris): <d>[English] My name is Chris, and I am reading for the part of Lady Ash.</d>
[4-6s] After finishing the introduction, Chris naturally lowers her eyes from the camera to the script page … she takes a small breath as she emotionally enters the character.
[6-18s] Keep the camera in a close medium-close-up emphasizing her face and eyes. Chris reads from the page in a soft, sorrowful, extremely sad voice … Her voice becomes increasingly fragile as the line continues.
(S1, Chris): <d>[English] Please, Peter... please don't let this be our last night together. …</d>
```

**案例 9 纸艺奇幻大战（SkyNotSilent `x-2085649264185913721`，@xianshi666123，12 s 16:9，中文书写）**
```
【核心创意】12 秒，16:9 横屏视频。手工纸艺立体拼贴与奇幻故事书风格的二维动画。…
0–2 秒｜大全景：镜头从山谷战场大全景缓慢向前 Push In。…
2–4 秒｜中景切换：镜头切到左侧女弓箭手。她迅速拉满弓弦，瞄准右侧骷髅士兵并射出一支箭。…
4–6 秒｜仰拍跟随：镜头快速 Tilt Up 跟随棕红色飞龙。…
声音：风吹旗帜声、弓弦拉动声、箭矢破空声、飞龙翅膀声、火焰喷射声、魔法护盾低沉嗡鸣、剑盾碰撞声、哥布林脚步声和紧张的奇幻战斗配乐。无对白、无旁白。
不想要：写实摄影、普通3D游戏CG、塑料材质 … 字幕、Logo、乱码文字、镜头剧烈抖动、黑屏转场。
必须保持：全片为手工纸艺立体拼贴与二维定格动画风格；… 英雄阵营位于左侧，敌方阵营位于右侧 …
```
（中文直写可出片的例子；“不想要”段是典型否定清单，按 phileiny/JGRFW 应改写为“必须保持”正面句。）

**案例 10 漫剧风格角色登场 MV（SkyNotSilent `x-2094305294117429711`，@Just_sharon7，15.168 s 16:9，Ref2VA）**
```
15s / 16:9 / high-energy 2D anime pop-punk MV — character-locked
CHARACTER LOCK (absolute authority = the reference still) Twin high black space-buns with messy volume and warm brown inner strands. Green jade disc clusters pinned into both buns. Straight blunt bangs with a small center split. Huge sharp green eyes, thick black outlines … Sleeveless lime-to-jade floral qipao with black piping … Bold black outlines, flat saturated colors, minimal cel shading, early-2000s TV-anime / handmade cartoon finish.
GRAPHIC LANGUAGE (from the still) Primary palette: lemon yellow, jade / lime green, ink black, paper white. Motifs: spinning jade discs, qipao lotus line-art, frog-button glyphs … torn yellow paper, black brush X's, photocopy grain, tape strips …
```
（漫剧向可借：把参考图的“图形语言”显式枚举成调色板 + 母题清单，再让每镜转场用这些母题。）

---

## 「本地 Ollama/Qwen 做提示词改写」可行方案排序（用户：Windows 11 + 4090 24 GB + Ollama `qwen3-vl:4b`）

| 排序 | 方案 | 模型/显存 | 为什么 | 注意 |
|---|---|---|---|---|
| **1** | `open-h3-ir` 编译器（`pip install open-h3-ir`）+ Ollama 作 OpenAI 兼容端点（`H3IR_LLM_URL=http://127.0.0.1:11434/v1`，`H3IR_LLM_MODEL=qwen3-vl:8b`），ComfyUI 侧装 `ruashots/ComfyUI-OpenH3-IR` 四节点 | `qwen3-vl:8b`（~6 GB）起步；想接近作者质量用 `qwen3.6:27b`/`qwen3.8:27b` Q4（~16–17 GB，须与 H3 串行） | 唯一带帧格对齐、1.2 s 镜头下限、台词零改写（`@speaks`）、100+ 规则校验与确定性回退的本地 Context-IR；`h3ir doctor` 会直接告诉你 Ollama 模型能否看图 | 项目 8 月后未更新，pin commit；验证器只认官方六段式；参考图按 1344×768≈1 024 token 计费，`num_ctx` 要 ≥16K |
| **2** | `duckyshell/ComfyUI-MiniMaxH3-Prompt-Writer`（Ollama provider） | 24 GB 档实测 `gemma4:26b`；或 `qwen3-vl:8b`；Qwen 3.6 五模式全过 | 最低学习成本的 UI；Sequence 模式一份 brief 出 30/60 s 多段提示词（Official 或 Compact）；自动选 8K/16K/24K `num_ctx`；跑完卸载 | 不自带规则级 linter（只有格式校验与修复），输出再过 pytraveler Prompt Check 或 open-h3-ir `validate` |
| **3** | `pytraveler` Writer(T2VA…/Ref2VA) + Reference Caption + Prompt Check + Reducer 节点，模型选 `ollama: …` 条目直读 GGUF | Qwen3.5-9B Q4 ≈8 GB；caption 用 Qwen2.5-Omni-3B 3.4 GB；8B LoRA Rewriter（Qwen3-VL-8B + 0.69 GB 适配器）≈9 GB 可“看首帧写对齐行” | 全在 ComfyUI 图内，可批量抽卡；self-check 每次运行自动跑；Reducer 让你改一个词再重写 | Writer 需要 ≥9.2K/12.3K ctx（自动）；`qwen3-vl:4b` 在 Writer 下 Ref2VA 常缺字段（作者建议“lower temperature or larger model”），但够做 caption 与 Reducer |
| **4** | `chflame163/ComfyUI_Qwen_H3_Prompt`（内置 llama-server + 官方 9 个 skill 原文） | Qwen3.8-27B Q4_K_M ≈16 GB + mmproj 0.86 GB | 最忠于“官方 skill + 本地大模型”；路由逻辑清晰 | 不校验、不修复；27B 与 H3 必须串行（force unload 默认开）；每次冷启动 llama-server |
| **5** | `1038lab Promptor`（Ollama provider）/ `T8mars enhancer`（本地 GGUF）/ `JGRFW AICG3D-SKILLS`（本地 GGUF） | 27B Q4 或云 API | 自带导演流程与检查节点（JGRFW H1–H12） | 系统提示词偏离官方格式（1038lab）、依赖重、GPL/NOASSERTION |
| 不推荐 | `ethanfel` 的 32B tail 增强 | 需 ≥32 GB 顺畅 | — | 24 GB 上“可能很慢”，且需其 int8 convrot 重打包的 CLIP，与用户现有 nvfp4 CLIP 不同文件 |

**关于 `qwen3-vl:4b` 的定位**：三家实测（pytraveler 4B 写手表、benjiyaya VisionPromptor 推荐 Qwen3-VL-4B/8B、duckyshell <8 GB 档）都把 4B 级放在“T2VA 三字段可用、Ref2VA 六段式吃力”。建议：4B 负责 **参考图 caption（一行 `Picture 1: …` 描述）与 Reducer**；写作交给 8B–9B（`ollama pull qwen3-vl:8b`），终稿校验用 open-h3-ir 验证器（无需 GPU）。所有方案都把 LLM 放在 H3 采样之前并卸载（Ollama：请求体 `keep_alive: 0` 或环境变量 `OLLAMA_KEEP_ALIVE=0`），避免与 int8 H3 + nvfp4 CLIP 抢 24 GB。

---

## 可写进 skill 的规则

1. 先把目标时长对齐帧格再写时码：帧数 = 17k+5（24 fps），5.167–15.083 s 内只有 8.0 s 是整秒；请求 10 s 实为 243 帧 = 10.125 s，对齐行 S.SS 与最后切点都用有效时长。（ruashots/open-h3-ir `grid.py`）
2. 每个镜头至少 1.2 s，包括片头到第一刀、最后一刀到片尾；切点落在最后 1.2 s 内判 ERROR。（open-h3-ir `T12`）
3. 镜头预算：4–6 s 1–2 镜，7–10 s 2–3 镜，11–15 s 3–5 镜，单镜 2.5–4.0 s，禁止 1 s 碎切。（1038lab `system_base.txt`、benjiyaya AgentSkill）
4. 中文台词按 3.5–5 字/s 预算（慢档 <3.5 用于金句，快档 >5 连续不超 3 s），逗号 +0.1–0.3 s、句号 +0.3–0.6 s；单句 >24 字拆成 2–3 镜、每镜 ≤18 字；金句后留 0.3–0.8 s 无台词反应镜。（JGRFW `dialogue-speed-check.md`）
5. 有台词的镜头从头到尾只做“说话”这一件事——H3 把整镜都当成该人在讲，不会在下一拍收嘴；讲完后的眨眼/吞咽放到下一镜。（phileiny §一之二）
6. 一镜只让一个人开口；多人场只用一两颗同框中景交代“谁站谁旁边”，台词一律单人正反打，机位放在听者视线上，说话对象偏离镜头轴 25–40°。（phileiny §四之二之四；JGRFW 数字人“另一位完全在画外”）
7. 画外音固定写 `says in an off-screen voiceover: <d>[Chinese] …</d> while his lips remain completely closed`，闭唇子句必须在 `</d>` 后 400 字符内；VO+OS 每 15 s 段 ≤20 字；VO 不得复述画面。（官方 base-en；open-h3-ir `D9`；JGRFW `vo-os-weaving.md`）
8. 否定句不进正文：H3 没有负向通道，被禁概念的词根会被渲染；人数、空镜、光效都用肯定句写“有什么”。唯一例外是摄影机静止只写一句 `static, on a tripod, with no camera movement whatsoever`，再多写 `no push in / no zoom / no dissolve` 会让切点漂到 3.5 s 后。（phileiny §二/§七之二③；JGRFW 法则 22 与 H8；alesha-pro “H3 has no negative prompt”）
9. 不写“什么都不变 / completely still / his face is doing nothing”，会冻结整镜；人的静止写呼吸、眨眼、重心微沉；物件静止写正面状态（“笔与资料夹的距离第一格到最后一格一样”）。（phileiny §二）
10. 有 `<d>` 的镜头，台词之外不出现 say / sentence / word / line 等词，不写 `lips parted as if about to speak`（会真的开口 2 s）；要表达“没说出口”写抿唇、吞咽、视线落到桌面。（phileiny §六之二④之二）
11. 台词文字永远不经 LLM 改写：锁定后原样回填，验收时逐字比对；summary 里不写 `continuing / says the rest`，台词不用 `And` 开头，否则出现假起头与重讲。（open-h3-ir `--say`/`D4`；duckyshell；phileiny）
12. 说话节奏绑 seed 不绑提示词：声音重讲/含糊先换 seed，有台词的镜头一次跑 2–3 个 seed；用 whisper `--word-timestamps` 逐字验收（重讲、假起头、晚开口、提示词被念出）。（phileiny §六之二④之二成因四、§八）
13. 一张脸被读懂只需 1.5–2 s，不要为了旁白长度拉长特写。（phileiny §六之二⑤）
14. 一镜一个主节拍（表情）或一个主动作；大肢体武打可 3 s 塞 8–9 招，拆镜理由改为“换角度”。（phileiny §一；benjiyaya “ONE PRIMARY ACTION PER SHOT”）
15. 切镜必须带来主体/空间/状态/视点/时间之一的新信息（否则用运镜），且开头用官方五个短语之一：`the camera cuts to / the shot cuts to / the shot transitions to / the shot changes to / the shot switches to`；dissolve/fade/wipe 仅用户要求时用。（open-h3-ir `R17`/`P7`）
16. 运镜写成带后果的动作句，每镜一个主运镜，静止也要写 `Static Shot`；绝不写 `Camera: Push In, slow` 这类标签栈，也不写角度数值；摄影机只为重大空间变化而动。（open-h3-ir `R18`/`P5`；LoveRain 摄影机纪律库 NO DEGREE / SUBJECT-TRIGGER）
17. 瞬时效果（闪光、巨响）绑在“某动作完成的那一刻”而不是时间戳；一颗生成内的切点整体后移约 1.2 s 但段内节拍准，引子多留 1.5 s 余裕；跨切点曝光会跳 ~45%，后期逐段调色而不是在提示词里写“曝光一致”。（phileiny §七之二⑦⑧⑨）
18. 每个后续镜头重述主体的服装关键词（夹克/衬衫/靴），只写一次会跨镜漂移；身份锚点（发型、年龄、带颜色的服装、标志配饰）每镜自然重复。（open-h3-ir `R15`；benjiyaya QUALITY BAR）
19. 参考标签规则：`<Subject N>` 只给可复用内容，`<Picture N>` 只给具体帧锚/分镜锚，不发明 `<Image N>`/`<Environment N>`；标签必带尖括号；定义过的每个标签必须在正文引用且有一行 retention，接了图却不提等于白占 9 个位；9 张配额按“帧锚图 > 主角板 > 场景拼接图 > 配角 > 道具拼板 > 动作视频 ≤3 > 音频 ≤3（必须挂图/视频）”取舍，超额降级为文字写进定义行。（open-h3-ir `L1–L4`；pytraveler `_tags`；JGRFW h3-adapter §四）
20. 道具绑定：手在镜头第一格就已接触道具，不要从画外伸进来；同一道具不同状态（刀在鞘/出鞘）做成不同参考图并只接给该状态的镜头；接了道具参考图就必须让它入画；反光道具只写材质本色、零光效。（phileiny §二之二/§四之一之二；JGRFW 法则 23）
21. 首镜只锚定一个具名主体，禁 “X 与 Y 同框” 并列句（实测出两张脸）；首镜无具名主体或悬空代词告警。（JGRFW `H12`）
22. 参考图准备：目标画幅、短边 ~768、剪影分明，不画箭头/标签/网格，映射说明写进文字；构图草图用 `weak_reference` 的分镜角色，身份另给图。（ethanfel REFERENCE_MEDIA_PRACTICAL_GUIDE）
23. 声音两字段：`overall_soundscape` 只在用户要全程静音时写 N/A，写成具体声源逗号链；`non_diegetic_music` 只写乐器/速度/节奏/动态与进出点，禁 melancholy/tense/eerie 等情绪词，用户没要配乐就写 N/A、不要从“cinematic”氛围推断出配乐。（open-h3-ir `A8`；duckyshell；yangzhou 模式 5）
24. 正文长度：Ref2VA `detailed_description` 350–500 词（官方样例 336，>700 告警），base 模式约“时长×25 词”，不靠形容词凑数；中文直写时每段 ≤500 字。（open-h3-ir `P2/P3`；benjiyaya `word_budget`；JGRFW 字数门禁）
25. 输出卫生：只用直引号与 ASCII 括号/尖括号（弯引号、全角 `＜＞（）［］` 直接 ERROR）；无 Markdown 围栏、无 `<think>`、无解释前言；提示词里的换行会被读成切镜，一段内不要随意换行。（open-h3-ir `H1`/`S4`/`G1`；Adudeguyman）
26. linter 最小集合（写成脚本跑在每次生成后）：Shot 1 无时间戳；Shot N 时码 `MM:SS.mmm` 严格递增且 <有效时长；编号连续；`<d>` 配对且以 `[Language]` 开头；I2VA/FL2VA/L2VA 对齐行存在且末镜号与 S.SS 正确；`(S1)` 从 1 连续；标签先定义后引用、无幻影媒体、无未引用媒体；retention 不含 `(Sx)`；soundscape/music 不含 `<d>`；无否定式；无工作流栏名泄漏。（pytraveler `checks.py`；open-h3-ir；JGRFW H1–H12；T8 tests）
27. 多段长片（30/60 s）：每段自包含，把全局规则拼进每一段而不是压底；上一段末帧 = 本段首态；BGM/环境音“不重启”写进两段；点名禁止重复的镜头机制而不是泛泛说“别重复”；相邻段最后 ~1.4 s 与开头 ~0.9 s 当一次呼吸设计。（LoveRain 007 与 README 纪律；duckyshell “A chunk boundary is not a cut”）
28. 表演四拍法：trigger → reception → one primary response → settled/end state；每拍每角色 ≤3 个可观察线索（视线/眼睑/呼吸/肩颈/手/姿态），先定机位侧与视线目标再写面部；情绪词一律落成肌肉动作。（T8 Performance Director；phileiny §零之二；JGRFW FACS 化）
29. 本地写作模型用完立即卸载再跑 H3（Ollama `keep_alive: 0`；节点侧 keep_model_loaded=false / force unload）；写手上下文 ≥9.2K（base guide）或 ≥12.3K（ref guide），否则 llama.cpp 从前面截断把输出契约截掉。（pytraveler；duckyshell `num_ctx` 8K/16K/24K）
30. 效果 embedding 写 `embedding:minimaxh3_<name>`：全小写、前有空格、名末无句点、ComfyUI ≥0.33；它占 50–142 个 token 长度而非形容词，开头放置最稳。（pytraveler Effect Embeddings）

---

## 未覆盖 / 未读完

- `ruashots/ComfyUI-OpenH3-IR`（★44，open-h3-ir 的 ComfyUI 四节点）未克隆，仅从主仓库 README 得知 `@speaks()`/`@` 命名语法。
- `T8mars/minimax-h3-prompt-skill-T8` 仅读 README（320 KB）前 60 行与质量原则段；案例画廊 600+ 行与两份非官方 skill 正文未读（仓库 pack 3 GB，不宜克隆）。
- `SkyNotSilent` 的 `data/tutorial-guides.json`（211 KB）、`public/llms-full.txt`（6.6 MB）与三个 agent skill 正文未读；`cases.json` 只做了过滤抽样。
- `LoveRain1997` 仅精读 README、007、摄影机纪律库 README；`lapian-research/01_拍摄技巧总纲.md`（371 KB、558 条 IF-THEN 规则）与 Dance MV Production Skill（88 KB）未读。
- `BeatAPI` 只读 README 与 catalog.json 抽样；`ai-boost` 只读 README_zh 的 12 条 H3 条目，`pages/zh/video-dialogue.md`（57 条）未读。
- `ethanfel` 的 `plan_v2.py`（215 KB）编译/校验细节与 `docs/PLAN_V2.md`、`FOLEY.md`、`AV_LATENTS.md` 未读；`ethanfel/ComfyUI-H3-Prompt-IDE` 未在列表、未读。
- `JGRFW/comfyui-AICG3D-SKILLS` 的 `engine/optimizer.py`（153 KB）、`DIRECTOR_SYSTEM_FULL.md`（54 KB）与 `JGRFW/comfyui-AICG3D` 主插件的 `prompt_optimizer.py` 未读。
- `T8mars enhancer` 的 `nodes.py`（165 KB）、`creative_suite.py`、`resources/visual_styles/catalog.json`（200 种视觉风格）未读，仅读 README_EN 相关段与测试名。
- `pytraveler` 的 `writer_omni.py`、`refmods.py`、`universal.py` 未逐行读；`prompt_template_omni.py` 的 REF_SYSTEM_PROMPT 未摘录。
- `chflame163` 内置官方 8 个风格 skill 正文（与官方仓库相同）未重读；`unknowlei` 的 creative-director 与三个写手 SKILL.md 只读了 reviewer 与 shot library。
- 不在本簇清单但 grep 命中、值得其它簇跟进：`SwotAtmk/infinite-creation`（short-drama-director 的 `validate_prompt.py` 含 C12 “否定式硬删除”检测与“人数用肯定句”规则）、`Astral-xm/ComfyUI-MiniMax-ContextIR`、`AI-KSK/aiksk-minimax-h3-local-prompt`、`alesha-pro/tools`（“H3 has no negative prompt; refusals are plain sentences”）。
