# H3 提示词格式（官方规范压缩版 + 短剧补充规则）

> 官方原文：MiniMax-AI/MiniMax-H3 仓库 `skills/h3-prompt-writing/references/base-en.txt`（三段式）与 `ref-en.txt`（六段式）。本文件只保留写短剧必须遵守的结构与规则；拿不准时用 `scripts/fetch_official_guides.sh` 拉官方原文对照。

## 0. 两条铁律

1. **描述段写英文，台词保持原语言。** 模型的文本编码器在英文结构化描述上训练；台词放在 `<d>[Chinese] …</d>` 里原样保留。
2. **开源权重是 CFG 蒸馏版，没有负向分支。** 任何「不要 X」「no X」都会被当成正向描述渲染出来。把否定改写成正向锁定：不写 `no jetpack`，写 `his back is bare except for the plain black jacket`。

## 1. 模式与首行指令

| 模式 | 输入 | 首行（必须一字不差，后空一行） |
|------|------|------|
| T2VA | 纯文字 | 无首行，直接三段 |
| I2VA | 首帧 | `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.` |
| FL2VA | 首帧+尾帧 | `How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.` |
| L2VA | 尾帧 | `How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.` |
| Ref2VA | ≤9 图 + ≤3 视频 + ≤3 音频（≤12 件） | 无首行，用六段式 |

`S.SS` = 视频实际时长，保留两位小数（10 s → `10.00`）。

## 2. 三段式（T2VA / I2VA / FL2VA / L2VA）

```
integrated_multimodal_description: [Shot 1] <风格一句> <场景/光/人物/动作/镜头> … <Subject/人物描述> (S1) says: <d>[Chinese] 台词</d> … [Shot 2] At 00:05.000, the shot cuts to …

overall_soundscape: <1–4 句，具体到物体与动作的环境音、动作音、非语言人声>

non_diegetic_music: <乐器/速度/情绪/动态，或 N/A>
```

- 第一镜不写时间码；之后每镜 `[Shot N] At MM:SS.mmm, the shot cuts to …`，时间严格递增且 < 总时长。
- 切镜动词只用：`the camera cuts to` / `the shot cuts to` / `the shot transitions to` / `the shot switches to`。
- 声景禁止抽象词（tense、sad）；只有用户要求静音才写 `N/A`。全集后期统一铺乐时 `non_diegetic_music: N/A`。

## 3. 六段式（Ref2VA，短剧主路线）

```
subject_definitions: <Subject 1> is <身份+外观不变量>, defined by <Picture 1> (face) and <Picture 2> (outfit). <Subject 2> is … <Picture 3> is the <场景> environment. <Subject 3> is <道具名>, the exact item shown in <Picture 4>.

summary: <一两句：谁在哪做什么，总时长>

retention_analysis: <Picture 1>: fully_preserved (facial identity, hairstyle). <Picture 2>: fully_preserved (outfit, colors), no other garment is substituted. <Picture 3>: partially_preserved (layout, lighting), camera may move. <Picture 4>: fully_preserved, no other item is substituted. <Audio 1>: attribute_transfer (voice timbre only).

detailed_description: [Shot 1] … [Shot 2] At 00:06.500, the shot cuts to …

overall_soundscape: …

non_diegetic_music: …
```

- 保留级别只用四个词：`fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`；参考音频若要整段复用原声写 `fully_copy`。
- 标签编号 = 媒体在 ComfyUI/API 里的实际顺序。**先角色、再场景、再道具、最后音频**，六段里编号必须一致。用占位符（如 `{fengyi}`）写分镜，最后一步才替换成 `<Subject N>` / `<Picture N>`，避免手工编号错位。
- 每个参考文件一个职责：脸、服装、环境、道具分开给图；文字只写不变量（年龄、骨相、发型、服装颜色），状态（湿头发、撕破的袖子）写在镜头描述里。
- 始终用 `<Subject 1>` 指代，不用 `she/he`。

## 4. 台词与声音

```
<Subject 1>, with a low, hoarse voice, (S1) says: <d>[Chinese] 你到底瞒了我多久？</d>
<Subject 2> listens with his mouth closed, jaw tightening.
```

- 一镜只能一人开口；听者必须写 `listens with mouth closed` + 反应，否则错人张嘴。
- 先动作后台词（`She sets the cup down, then (S1) says:`），动作是模型排时间的锚点。
- 台词预算：中文约 **4 字/秒**；一段的台词总字数 ≤ (时长 − 2 s) × 4.5。超了就拆段，不要要求说快。
- 每 3–4 s 一句，或明确写出哪几秒沉默。
- 画外音：`(S1) says in an off-screen voiceover: <d>…</d> while his lips remain completely closed.` 不加闭唇声明会被对口型。
- 跨切点台词两端加 `<scenetrans>` 并写 `continues seamlessly across the cut`；片尾被打断用 `<cutoff>`。
- 音色参考 `<Audio 1>`：2–15 s 干净人声，必须伴随至少一张图/一段视频；只定音色，口音/情绪/语速仍要写字。
- 音色描述（低沉/沙哑/语速）写在 `(S1)` 前，并在每段一字不改复用。

## 5. 镜头与运镜

- 官方运镜词：Zoom In/Out · Push In / Pull Out · Pan Left/Right · Truck Left/Right · Tilt Up/Down · Pedestal Up/Down · Arc Shot · Tracking Shot · Static Shot · Shake Slightly/Strongly · POV · Roll Clockwise/Counterclockwise；修饰 `with small/large amplitude`、`at slow/fast speed`。
- **一镜一个主运镜**。叠加 push in + handheld + orbit 必漂移。
- 切镜必须带来新信息（新角度、新人物、反应）；只想拉近用运镜。
- 15 s ≈ 3 镜 + 2–4 句短台词；5 s 一镜一句。正反打两镜都写视线方向与各自服装锁定。
- 单镜头内有动作/台词的人物 ≤ 3；双人同框写相对位置与身高。

## 6. 风格句（放在 [Shot 1] 开头）

- 电影质感：`Live-action, cinematic, shot on 35mm anamorphic, shallow depth of field, warm tungsten key light with cool window fill, fine film grain.`
- 漫剧（2D）：`2D anime, clean cel shading, bold ink outlines, flat colors with soft gradient shadows, limited animation timing, speed lines on fast motion.`
- 禁词：`4K, masterpiece, ultra-realistic, beautiful, cinematic`（单独出现无信息）。形容词 > 3 个开始失效。写光源、焦段、材质。
- 画面文字：`a red neon sign reading "营业中"`；精确文字不可靠，字幕一律后期烧。画幅用参数，不写进文字。

## 7. 道具

- 剧情里出现的任何关键物品必须有参考图并在 `subject_definitions` 里声明 `the exact item shown in <Picture N>`，`retention_analysis` 写 `fully_preserved, no other item is substituted`。没有参考图的物品模型一定会编。
- 物品等级/稀有度颜色框、UI、字幕都后期叠加，不交给模型。

## 7b. 来自 23 个提示词工具的补充规则（`docs/13-github-survey/04-prompting-tools.md`）

**时长与切点**
- 先把时长对齐帧格再写时码：帧数 = 17k+5，5–15 s 内只有 8.0 s 是整秒；请求 10 s 实为 243 帧 = 10.125 s，对齐行 `S.SS` 与最后切点都用**有效时长**。
- 每镜 ≥ 1.2 s（含片头到第一刀、最后一刀到片尾）；镜头预算：4–6 s 1–2 镜，7–10 s 2–3 镜，11–15 s 3–5 镜，单镜 2.5–4 s，禁 1 s 碎切。
- 一颗生成内的切点整体后移约 1.2 s 但段内节拍准，引子多留 1.5 s；跨切点曝光会跳 ~45%，后期逐段调色，不在提示词里写「曝光一致」。
- 瞬时效果（闪光、巨响）绑在「某动作完成的那一刻」而不是时间戳。

**台词**
- 中文 3.5–5 字/s（金句慢档 < 3.5；快档 > 5 连续不超 3 s），逗号 +0.1–0.3 s、句号 +0.3–0.6 s；单句 > 24 字拆 2–3 镜、每镜 ≤ 18 字；金句后留 0.3–0.8 s 无台词反应镜。
- **有台词的镜头从头到尾只做「说话」这一件事**（H3 把整镜当成该人在讲，不会在下一拍收嘴）；讲完后的眨眼 / 吞咽放下一镜。
- 多人场只用一两颗同框中景交代站位，台词一律单人正反打，机位在听者视线上，说话对象偏离镜头轴 25–40°。
- 有 `<d>` 的镜头，台词之外不出现 say / sentence / word / line，不写 `lips parted as if about to speak`（会真开口 2 s）；「没说出口」写抿唇、吞咽、视线落桌面。
- 台词文字永远不经 LLM 改写，验收逐字比对；summary 不写 `continuing / says the rest`；台词不用 `And` 开头。
- 说话节奏绑 seed 不绑提示词：重讲 / 含糊先换 seed，有台词的镜头一次 2–3 个 seed；用 whisper `--word-timestamps` 验收。
- 画外音闭唇子句必须在 `</d>` 后 400 字符内；VO + OS 每 15 s 段 ≤ 20 字；VO 不复述画面。
- 一张脸被读懂只需 1.5–2 s，不要为旁白拉长特写。

**否定与静止**
- 否定句唯一例外：摄影机静止只写一句 `static, on a tripod, with no camera movement whatsoever`；再写 `no push in / no zoom` 会让切点漂到 3.5 s 后。
- 不写 `completely still / his face is doing nothing`（会冻结整镜）；人的静止写呼吸、眨眼、重心微沉；物件静止写正面状态。

**镜头与表演**
- 一镜一个主节拍（表情）或一个主动作；切镜必须带来主体 / 空间 / 状态 / 视点 / 时间之一的新信息。
- 运镜写成带后果的动作句，静止也写 `Static Shot`；绝不写 `Camera: Push In, slow` 标签栈或角度数值。
- 表演四拍：trigger → reception → one primary response → settled end state；每拍每角色 ≤ 3 个可观察线索；情绪词落成肌肉动作。
- 每个后续镜头重述主体服装关键词与身份锚点（发型、年龄、带颜色的服装、标志配饰）。
- 首镜只锚定一个具名主体，禁「X 与 Y 同框」并列句（实测出两张脸）。

**参考与道具**
- `<Subject N>` 只给可复用内容，`<Picture N>` 只给具体帧锚；不发明 `<Image N>` / `<Environment N>`；定义过的标签必须在正文引用且有 retention 行；接了图不提等于白占配额。
- 道具：手在镜头第一格就已接触道具，不从画外伸进来；同一道具不同状态（刀在鞘 / 出鞘）做成不同参考图只接给该状态镜头；反光道具只写材质本色、零光效。
- 参考图：目标画幅、短边 ~768、剪影分明，不画箭头 / 标签 / 网格。

**长度与卫生**
- Ref2VA `detailed_description` 350–500 词（> 700 告警）；base 模式约「时长 × 25 词」。
- 只用直引号与 ASCII 括号 / 尖括号（弯引号、全角 `＜＞（）［］` 直接 ERROR）；无 Markdown 围栏、无 `<think>`、无解释前言；**提示词里的换行会被读成切镜**，一段内不要随意换行。
- 效果 embedding 写 `embedding:minimaxh3_<name>`（ComfyUI ≥ 0.33），放开头。

**多段（30 / 60 s）**：每段自包含，把全局规则拼进每一段；上一段末帧 = 本段首态；BGM / 环境音「不重启」写进两段；相邻段最后 ~1.4 s 与开头 ~0.9 s 当一次呼吸设计。

**运镜与表演细则**（含 46 镜实跑数据）见 `camera-and-performance.md`：4 步 Turbo 抹掉运镜、背景板让运镜减半、台词按文本顺序连续铺轨、参考视频须 24 fps 等。

## 7c. 本地提示词改写（Ollama / Qwen）

| 排序 | 方案 | 模型 |
|------|------|------|
| 1 | `pip install open-h3-ir` + Ollama 作 OpenAI 兼容端点（`H3IR_LLM_URL=http://127.0.0.1:11434/v1`），ComfyUI 侧 `ruashots/ComfyUI-OpenH3-IR`；自带 122 KB 验证器（帧格、1.2 s 下限、台词零改写、R15 服装重述、A8 配乐禁情绪词） | `qwen3-vl:8b` 起步；27B Q4 须与 H3 串行 |
| 2 | `duckyshell/ComfyUI-MiniMaxH3-Prompt-Writer`（Ollama 前端，Sequence 模式出 30/60 s 多段） | `qwen3-vl:8b` / `gemma4:26b` |
| 3 | `pytraveler` Writer + Reference Caption + Prompt Check + Reducer（直读 Ollama GGUF） | Qwen3.5-9B Q4 ≈ 8 GB |
| 4 | `chflame163/ComfyUI_Qwen_H3_Prompt`（内置 llama-server + 官方 9 个 skill 原文） | Qwen3.8-27B Q4 ≈ 16 GB |

`qwen3-vl:4b` 只够做参考图 caption 与 Reducer；写作交给 8–9B；终稿过 open-h3-ir 验证或本 skill 的 `scripts/lint_prompt.py`。写手模型用完立即卸载（`keep_alive: 0`）再跑 H3；上下文 ≥ 9.2K（base）/ ≥ 12.3K（ref）。案例库：SkyNotSilent/awesome-MiniMax-H3-cases `cases.json`（781 条逐字 Prompt，可按电影叙事 / 角色对白 / 动漫过滤）。

## 8. 自检清单（生成前跑一遍，`scripts/lint_prompt.py` 自动化了可机检的部分）

- [ ] 首行指令与模式匹配，S.SS 等于实际时长
- [ ] 所有 `<Picture/Video/Audio N>` 都有对应媒体且编号顺序一致
- [ ] 每镜一个说话人、一个运镜；时间码递增且小于总时长
- [ ] 没有否定句；没有 `she/he` 指代多人
- [ ] 台词字数 ≤ (时长−2)×4.5
- [ ] 声景具体、配乐字段存在（或 N/A）
- [ ] 描述英文、台词原语言、`<d>` 内只有语言标签+原话
