# H3 提示词格式（官方规范压缩版 + 短剧补充规则）

> 官方原文：MiniMax-AI/MiniMax-H3 仓库 `skills/h3-prompt-writing/references/base-en.txt`（三段式）与 `ref-en.txt`（六段式）。本文件只保留写短剧必须遵守的结构与规则，并已并入 23 个提示词工具的补充规则（`docs/13-github-survey/04-prompting-tools.md`）与补读裁决（`10-unread-followup.md`）；拿不准时用 `scripts/fetch_official_guides.py` 拉官方原文对照。

## 0. 两条铁律

1. **描述段写英文，台词保持原语言。** 模型的文本编码器在英文结构化描述上训练；台词放在 `<d>[Chinese] …</d>` 里原样保留。
2. **开源权重是 CFG 蒸馏版，没有负向分支。** 任何「不要 X」「no X」都会被当成正向描述渲染出来。把否定改写成正向锁定：不写 `no jetpack`，写 `his back is bare except for the plain black jacket`。真的需要「不要 X」时用节点而不是文字：`hako-mikan/comfyui-minimax-h3-negpip`（MODEL 与 CLIP 都过它，写 `(red glow:-3)`，短语优于单词，−1 精确翻转、最多约 −5，可 `@2.5-4.0` 限时段、`@v`/`@a` 限模态；装了它字面括号要写 `\(`）。否定句唯一例外：极短、具体、单句的排除词可用（`NO black letterbox bars`、`Exactly two people`；摄影机静止只写一句 `static, on a tripod, with no camera movement whatsoever`，再写 `no push in / no zoom` 会让切点漂到 3.5 s 后），其余一律正向；六段式之外不要追加 `constraints:` 第七段。

格式卫生：只用直引号与 ASCII 括号 / 尖括号（弯引号、全角 `＜＞（）［］` 直接 ERROR）；无 Markdown 围栏、无 `<think>`、无解释前言；**提示词里的换行会被读成切镜**，一段内不要随意换行。效果 embedding 写 `embedding:minimaxh3_<name>`（ComfyUI ≥ 0.33），放开头。

## 1. 模式与首行指令

| 模式 | 输入 | 首行（必须一字不差，后空一行） |
|------|------|------|
| T2VA | 纯文字 | 无首行，直接三段 |
| I2VA | 首帧 | `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.` |
| FL2VA | 首帧+尾帧 | `How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.` |
| L2VA | 尾帧 | `How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.` |
| Ref2VA | ≤9 图 + ≤3 视频 + ≤3 音频（≤12 件） | 无首行，用六段式 |

`S.SS` = 视频实际时长，保留两位小数（10 s → `10.00`）。先把时长对齐帧格再写时码：帧数 = 17k+5，5–15 s 内只有 8.0 s 是整秒；请求 10 s 实为 243 帧 = 10.125 s，对齐行 `S.SS` 与最后切点都用**有效时长**。

## 2. 三段式（T2VA / I2VA / FL2VA / L2VA）

```
integrated_multimodal_description: [Shot 1] <风格一句> <场景/光/人物/动作/镜头> … <Subject/人物描述> (S1) says: <d>[Chinese] 台词</d> … [Shot 2] At 00:05.000, the shot cuts to …

overall_soundscape: <1–4 句，具体到物体与动作的环境音、动作音、非语言人声>

non_diegetic_music: <乐器/速度/情绪/动态，或 N/A>
```

- 第一镜不写时间码；之后每镜 `[Shot N] At MM:SS.mmm, the shot cuts to …`，时间严格递增且 < 总时长。
- 一颗生成内的切点整体后移约 1.2 s 但段内节拍准，引子多留 1.5 s；跨切点曝光会跳 ~45%，后期逐段调色，不在提示词里写「曝光一致」。
- 切镜动词只用：`the camera cuts to` / `the shot cuts to` / `the shot transitions to` / `the shot switches to`。
- 声景禁止抽象词（tense、sad）；只有用户要求静音才写 `N/A`。全集后期统一铺乐时 `non_diegetic_music: N/A`；`overall_soundscape` 不写 crowd / chatter。
- 正文长度约「时长 × 25 词」。

## 3. 六段式（Ref2VA，短剧主路线）

版式照官方完整示例（`ref-en.txt` §7）：**每个字段名单独一行，定义和保留关系一条一行，每个 `[Shot N]` 另起一行，`[Shot 1]` 之前只有一句风格**。`scripts/build_prompts.py` 出的就是这个版式——下面是它对 `assets/episode.example.json` 第二段的原样输出（这一段从第一段已采纳片段的实拍末态开场）。

```
subject_definitions:
<Subject 1> is the woman in her early thirties whose face and hairstyle come from <Picture 1> and whose build and outfit come from <Picture 2>, with short black hair tucked behind her ears, a fitted black suit jacket over a white shirt, and a thin silver watch.
<Subject 2> is the man in his fifties in <Picture 3>, with grey-streaked short hair, thin gold-rimmed glasses, a white doctor's coat over a pale blue shirt, and a stethoscope around his neck.
<Subject 3> is the environment in <Picture 4>, a long hospital corridor at night: pale green walls, a row of closed ward doors on the left, a dark nurses' station with a single warm desk lamp on the right, polished floor reflecting the overhead fluorescent tubes, an exit sign glowing green at the far end.
<Subject 4> is the worn brown kraft-paper medical records envelope with a red hospital stamp in the corner, the exact item shown in <Picture 5>.
<Audio 1> is the voice-timbre reference for <Subject 2> (S1).

summary:
[reference generation + audio reference] <Subject 2> takes out <Subject 4> and admits how long he has kept the truth from <Subject 1>. The three-shot video uses <Audio 1> as the voice-timbre reference for <Subject 2>.

retention_analysis:
<Subject 1> (appears in [Shot 1], [Shot 2], [Shot 3]): fully_preserved - the facial identity and hairstyle of the woman in the black suit jacket are retained from <Picture 1> and the build, outfit and silhouette from <Picture 2>; only the person is taken from these pictures, the setting comes from <Subject 3>.
<Subject 2> (appears in [Shot 1], [Shot 2]): fully_preserved - the facial identity, hairstyle, build and outfit of the grey-haired doctor in the white coat are retained from <Picture 3>; only the person is taken from this picture, the setting comes from <Subject 3>.
<Subject 3> (appears in [Shot 1], [Shot 2], [Shot 3]): partially_preserved - the layout, light direction and set dressing are retained while the camera position changes from shot to shot.
<Subject 4> (appears in [Shot 1], [Shot 2]): fully_preserved - the item's shape, color, markings and material are retained exactly; no other item is substituted.
<Audio 1>: reference - its vocal timbre guides the dialogue delivery of <Subject 2> without copying the original signal; the spoken words come from the quoted dialogue lines.

detailed_description:
The target video is in the following style: live-action, cinematic, shot on 35mm anamorphic, shallow depth of field, cool fluorescent corridor light with a warm practical lamp at the nurses' station, fine film grain.
[Shot 1] The video opens on a medium close-up of <Subject 2>, the man in his fifties with grey-streaked short hair, thin gold-rimmed glasses, a white doctor's coat over a pale blue shirt, and a stethoscope around his neck, from over the shoulder of <Subject 1>, the woman in the black suit jacket, 50mm, shallow depth of field. The setting is <Subject 3>, the long hospital corridor at night. As the video opens, <Subject 1> stands in the middle of the corridor beside the nurses' station, one metre in front of <Subject 2> and facing him, her arms at her sides; <Subject 2> stands facing her with his hands hanging at his sides; every ward door is closed. Both outfits are unchanged. <Subject 2> holds her gaze for a long beat, lowers his eyes to the floor and draws a slow breath. With his right hand he pulls <Subject 4>, the worn brown kraft-paper medical records envelope with a red hospital stamp in the corner, out from inside his white coat and holds it flat against his chest with both hands, the red hospital stamp facing the camera. His lips stay closed and his glasses catch a thin line of fluorescent light. The kraft paper rustles against the cotton of his coat. His shoulders sink as he breathes out, and his fingers tighten on the edge of the envelope. The camera holds a static shot.
[Shot 2] At 00:03.500, the shot cuts to a close-up of the face of <Subject 2> (S1), the grey-haired doctor in the white coat from Shot 1, 85mm, very shallow depth of field. <Subject 2> raises his eyes to <Subject 1>, his hands still pressing <Subject 4> to his chest, while she listens at the right edge of the frame with her mouth closed, only her chest rising with a slow breath. The fluorescent tube above flares briefly across his gold-rimmed glasses. The camera pushes in with small amplitude at slow speed. <Subject 2> (S1), using the voice timbre referenced from <Audio 1>, with a tired, gravelly voice and slow, measured delivery, says slowly and heavily, almost as a confession, <d>[Chinese] 从你母亲住院的第一天起。</d> He closes his lips and lowers his eyes to <Subject 4>.
[Shot 3] At 00:08.000, the shot cuts to a close-up of the face of <Subject 1>, the woman in her early thirties with short black hair tucked behind her ears, a fitted black suit jacket over a white shirt, and a thin silver watch, 85mm, very shallow depth of field. <Subject 1> hears the words and her composure cracks: her eyes widen slightly, she presses her lips together and swallows once, and her gaze drops to the envelope before it lifts back to his face. She stays where she stands, breathing visibly. Warm lamp light falls on the left side of her face and cool fluorescent light on the right. The camera holds a static shot. In the final second every character settles and holds the pose, breathing, while the framing stays put. Speak only the quoted dialogue line. After that nobody says anything else.

overall_soundscape:
A quiet indoor room tone. Kraft paper rustles against cotton.

non_diegetic_music:
N/A
```

**脚本替你做的事**（前四件来自官方完整示例；分镜里不要自己再写一遍）：

1. **人不写名字。** 定义行是 `the <who> in <Picture N>, with <features>`（官方 §2.1）；一个人有多张图就写明每张图提供什么（`whose face and hairstyle come from … and whose build and outfit come from …`，官方「state what each asset provides」）。没有标签的地方（三段式、没参考图的人、状态里提到的不在本段的人）用短称 `the woman in the black suit jacket`（`short_phrase`，不填就取 `identity_phrase` 的开头：`the woman in her early thirties`）。
2. **首次清楚出场处把外貌再说一遍**（官方 §5.3：at the first clear appearance describe its referenced characteristics）：紧跟在这一镜里第一次提到它的标签后面，作同位语。「清楚出场」= 人在画面里、不是只露肩膀 / 手 / 背影，并且这一镜是中景或更宽（在场的人都看得清），或者景别写的就是他，或者景别没写任何人（建立镜头）；别人的特写镜头不算。在那之前的一瞥只给短称；之后每次切镜、该镜的主体会带一句 `…, the <短称> from Shot k`。道具同理，首次出现处带一遍描述。
3. **台词后闭嘴。** 官方示例每句台词后面都跟一句 `She closes her lips and …`。`dialogue[].after_line` 写这句（说完之后这个人做什么）；不写则补 `<Subject N> closes his / her lips.`
4. **音色参考每句都引用，并带上嗓音的文字描述**（官方 §5.3：在音频关系起作用的地方引用 `<Audio N>`；官方示例写的是 `using the clear youthful voice timbre referenced from <Audio 1>`）：首句 `using the voice timbre referenced from <Audio 1>, with a tired, gravelly voice and slow, measured delivery,`（后半句取自 `voice_phrase`），之后 `in the same voice referenced from <Audio 1>`。没有音色参考的人，首次开口处只写嗓音。该镜的景别里点到说话人时，`(S1)` 也跟在那里的标签后面。
5. **只说引号里的词。** 有台词的段在末尾加 `Speak only the quoted dialogue lines.`（单人再加 `After that nobody says anything else.`，多人加 `Those are the only words in the video.`）——这句不是官方写法，是社区实测的防多说词手段（多说词 9.3% → 1.3%，`camera-and-performance.md` §5b）；没有台词的段在 `[Shot 1]` 里写 `Nobody speaks in this video; every mouth stays closed …`。
6. **`appears in` 和 `the setting comes from` 自动对账**：保留行里的出场镜头是从写好的镜头正文里读出来的；人物行末尾的「场景取自」写的是场景的标签。

**状态怎么进提示词**：

- 场景、开场站位、承接状态都在 `[Shot 1]` 里（官方 §5.2：`[Shot 1]` 之前只用一两句交代风格）。`[Shot 1]` 写成一句话：`The video opens on <景别>, <镜头>.`
- 承接状态写成描述句 `As the video opens, <状态>.`，放在景别和场景之后。状态说的是人在**房间里**的位置（靠着什么、在谁的左右、面朝谁、拿着什么），不是在画面里的位置——下一段是另一个机位。
- 结束状态 `At the end of the video, <状态>.` 只在末镜是中景或更宽时写进提示词；末镜是特写 / 插入镜头时不写（镜头里拍不到全屋，写了反而和景别打架），它仍然留在分镜 JSON 里给下一段和 `observe_take.py` 对照。
- 场景的保留级别写 `partially_preserved` 是有意的：写 `fully_preserved` 会把参考图的机位也一起锁住，运镜出不来；保留的是布局、光向和陈设。

- `summary` 以方括号里的任务类型开头：参考图 / 音频只作引导 = `reference generation`；有图当首帧 = 加 `keyframe completion`；音色参考 = 加 `audio reference`；整段复用原声 = `audio reuse`。后面用一两句说谁在哪做什么，只用已定义的标签。
- 画面的保留级别四个词：`fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`。**音频另有四个**：`fully_copy`（整段复用为成片音轨）/ `partially_copy` / `reference`（只借音色、节奏，不复制信号——音色参考用这个）/ `weak_reference`。`<Subject N>` 的保留行写 `(appears in [Shot …])`，首帧锚图写 `<Picture 1> ([Shot 1] first frame): fully_preserved - …`；保留行里不写 `(Sx)`。
- 标签编号 = 媒体在 ComfyUI/API 里的实际顺序。**先角色、再场景、再道具、最后音频**，六段里编号必须一致。用占位符（如 `{fengyi}`）写分镜，最后一步才替换成 `<Subject N>` / `<Picture N>`，避免手工编号错位。
- 每个参考文件一个职责：脸、服装、环境、道具分开给图。进提示词的 `identity_phrase` 只写一眼能把这个人和别人分开的不变量——年龄段、发型发色、主服装与颜色、一个标志物，12–25 词（官方示例的量级：`with long blonde hair and a light-pink button-down shirt with rolled-up sleeves`）；骨相、族裔、身高这类只对生图有用的细节放 `sheet_phrase`（不进视频提示词）。状态（湿头发、撕破的袖子）写在镜头描述里。
- 每个镜头里第一次提到某人用 `<Subject N>`；同一镜头内紧接着的句子可以用代词（官方示例就是这样写的：`<Subject 3> (S1) … She closes her lips …`）；换了镜头重新用标签，同框有两个同性别的人时不用代词。
- `<Subject N>` 只给可复用内容，`<Picture N>` 只给具体帧锚；不发明 `<Image N>` / `<Environment N>`；定义过的标签必须在正文引用且有 retention 行；接了图不提等于白占配额。
- 参考图：目标画幅、短边 ~768、剪影分明，不画箭头 / 标签 / 网格。
- 多人镜只给首帧，不加 `<Picture>` 身份参考（会多出一人）；单人镜加身份参考时写明「仅外观参考，不是要切过去的画面」；写 `Exactly N people`。
- 长度：官方说生成任务的 `detailed_description` 通常 350–500 词，对白密的段以装下完整的说话时间线为先。脚本带上站位、外貌、收尾状态之后一般落在 450–600 词。`lint_prompt.py` 只警告：< 350 词（模型会自由发挥甚至烧字幕）、> 700 词、单镜 > 240 词（首镜带着开场交代、末镜带着结束状态，放宽到 300）。写分镜时每镜的 action + performance 合计 50–100 词比较合适；灯光只在这一镜的光和风格行不一样时才写。
- 7000 字符是 MiniMax **云端 API** 的文本上限；本地 ComfyUI 节点没有长度限制（文本编码器是 Qwen3-VL-32B，直接读原文、不套对话模板，`comfy/text_encoders/minimax.py`）。`<d>` 与 `</d>` 在分词器里各是一个专用 token：必须原样写，中间不加空格、不换括号。
- 多段（30 / 60 s）：每段自包含，把全局规则拼进每一段；上一段末帧 = 本段首态；BGM / 环境音「不重启」写进两段；相邻段最后 ~1.4 s 与开头 ~0.9 s 当一次呼吸设计。

## 4. 台词与声音

```
六段式：<Subject 1> (S1), with a low, hoarse voice, says quietly, <d>[Chinese] 你到底瞒了我多久？</d> She closes her lips.
三段式：The woman in the black suit jacket with a low, hoarse voice (S1) says quietly: <d>[Chinese] 你到底瞒了我多久？</d> She closes her lips.
听者：  <Subject 2> listens with his mouth closed, jaw tightening.
```

- 一镜只能一人开口；听者必须写 `listens with mouth closed` + 反应，否则错人张嘴。
- **有台词的镜头从头到尾只做「说话」这一件事**（H3 倾向于把整镜当成该人在讲）；讲完后的眨眼 / 吞咽放下一镜。台词后面那句闭嘴动作（官方示例的写法，脚本会补）只负责把嘴收住，不要在它后面再排一串动作。
- 先动作后台词：动作放在**前一个镜头**或台词之前的那半句（`She sets the cup down. … (S1) says, <d>…</d>`），动作是模型排时间的锚点；开口的那一镜里只做说话这一件事。
- 台词预算（权威口径在 `storyboard-and-assets.md` §1）：一段的总字数 ≤ (时长 − 2 s) × 4.5；一个镜头里的台词 ≤ 镜头秒数 × 3；说话时的语速目标 3.3–4 字/s（金句慢档 < 3.5，快档 ≤ 5 且连续不超 3 s）。逗号约 +0.1–0.3 s、句号 +0.3–0.6 s；单句 > 24 字拆 2–3 镜、每镜 ≤ 18 字；金句后留 0.3–0.8 s 无台词反应镜。超了就拆段，不要要求说快。
- 每 3–4 s 一句，或明确写出哪几秒沉默。
- 有 `<d>` 的镜头，台词之外不出现 say / sentence / word / line，不写 `lips parted as if about to speak`（会真开口 2 s）；「没说出口」写抿唇、吞咽、视线落桌面。
- 台词文字永远不经 LLM 改写，验收逐字比对；summary 不写 `continuing / says the rest`；台词不用 `And` 开头；称呼后面不写逗号、句首不写「……」（会停 1 s / 念乱语）。
- 说话节奏绑 seed 不绑提示词：重讲 / 含糊先换 seed，有台词的镜头一次 2–3 个 seed；用 whisper `--word-timestamps` 验收。
- 画外音：`(S1) says in an off-screen voiceover: <d>…</d> while his lips remain completely closed.` 不加闭唇声明会被对口型；闭唇子句必须在 `</d>` 后 400 字符内；VO + OS 每 15 s 段 ≤ 20 字；VO 不复述画面。
- 跨切点台词两端加 `<scenetrans>` 并写 `continues seamlessly across the cut`；片尾被打断用 `<cutoff>`。
- 音色参考 `<Audio 1>`：2–15 s 干净人声，必须伴随至少一张图/一段视频；只定音色，口音/情绪/语速仍要写字；不说话的人脸镜头给一段静音引导音轨（防乱念）。
- 音色描述（低沉 / 沙哑 / 语速）写进角色的 `voice_phrase`（`a man in his fifties with a tired, gravelly voice and slow, measured delivery`），每段一字不改复用；三段式里它在 `(S1)` 前（官方：`the middle-aged baker with a calm, slightly raspy voice (S1) … says:`），六段式里 `(S1)` 紧跟标签、音色随后；说话人首现 ±120 字内要有音色词，`(Sx)` 按**在成片里开口的先后**从 S1 编（官方规则），不必与 `<Subject N>` 的编号相同；绑定了说话人的 `<Audio N>` 复用同一个 `(Sx)`。

## 5. 镜头、运镜与表演

- 官方运镜词：Zoom In/Out · Push In / Pull Out · Pan Left/Right · Truck Left/Right · Tilt Up/Down · Pedestal Up/Down · Arc Shot · Tracking Shot · Static Shot · Shake Slightly/Strongly · POV · Roll Clockwise/Counterclockwise；修饰 `with small/large amplitude`、`at slow/fast speed`。
- **一镜一个主运镜**。叠加 push in + handheld + orbit 必漂移。运镜写成带后果的动作句，静止也写 `Static Shot`；绝不写 `Camera: Push In, slow` 标签栈或角度数值。
- 切镜必须带来新信息（主体 / 空间 / 状态 / 视点 / 时间之一：新角度、新人物、反应）；只想拉近用运镜。一镜一个主节拍（表情）或一个主动作。
- 镜头数与时长以 `storyboard-and-assets.md` §1 为准：每镜 ≥ 1.2 s（含片头到第一刀、最后一刀到片尾），常规 2.5–6 s，有台词的镜 ≥ 3 s；≤ 6 s 1–2 镜，7–10 s 2–3 镜，11–13 s 3–4 镜；对白段 10 s 内 ≤ 2 镜、12–13 s ≤ 3 镜，禁 1 s 碎切（打斗每击一镜例外）。dramake 对对白段更保守（每内部镜 ≥ 4 s），片子节奏慢时可以照它来。超预算先减镜不加形容词；每段只放一个高风险物理事件并写 起始态 → 控制输入 → 方向 → 阶段 → 终态。
- 正反打两镜都写视线方向与各自服装锁定；多人场只用一两颗同框中景交代站位，台词一律单人正反打，机位在听者视线上，说话对象偏离镜头轴 25–40°。
- 单镜头内有动作/台词的人物 ≤ 3；双人同框写相对位置与身高。首镜只锚定一个具名主体，禁「X 与 Y 同框」并列句（实测出两张脸）。
- 每个后续镜头重述主体服装关键词与身份锚点（发型、年龄、带颜色的服装、标志配饰）。
- 表演四拍：trigger → reception → one primary response → settled end state；每拍每角色 ≤ 3 个可观察线索；情绪词落成肌肉动作。
- 不写 `completely still / his face is doing nothing`（会冻结整镜）；人的静止写呼吸、眨眼、重心微沉；物件静止写正面状态。
- 瞬时效果（闪光、巨响）绑在「某动作完成的那一刻」而不是时间戳。
- 一张脸被读懂只需 1.5–2 s，不要为旁白拉长特写。
- 运镜与表演细则（含 46 镜实跑数据）见 `camera-and-performance.md`：4 步 Turbo 抹掉运镜、背景板让运镜减半、台词按文本顺序连续铺轨、参考视频须 24 fps 等。

## 6. 风格句（三段式放在 [Shot 1] 开头；六段式是 [Shot 1] 之前的那一句）

- 电影质感：`Live-action, cinematic, shot on 35mm anamorphic, shallow depth of field, warm tungsten key light with cool window fill, fine film grain.`
- 漫剧（2D）：`2D anime, clean cel shading, bold ink outlines, flat colors with soft gradient shadows, limited animation timing, speed lines on fast motion.`
- 禁词：`4K, masterpiece, ultra-realistic, beautiful, cinematic`（单独出现无信息）。形容词 > 3 个开始失效。写光源、焦段、材质。
- 画面文字：`a red neon sign reading "营业中"`；精确文字不可靠，字幕一律后期烧。画幅用参数，不写进文字。

## 7. 道具

- 剧情里出现的任何关键物品必须有参考图并在 `subject_definitions` 里声明 `the exact item shown in <Picture N>`，`retention_analysis` 写 `fully_preserved, no other item is substituted`。没有参考图的物品模型一定会编。
- 手在镜头第一格就已接触道具，不从画外伸进来；同一道具不同状态（刀在鞘 / 出鞘）做成不同参考图只接给该状态镜头；反光道具只写材质本色、零光效。
- 物品等级/稀有度颜色框、UI、字幕都后期叠加，不交给模型。

## 8. 自检清单（生成前跑一遍，`scripts/lint_prompt.py` 自动化了可机检的部分）

- [ ] 首行指令与模式匹配，S.SS 等于实际时长
- [ ] 所有 `<Picture/Video/Audio N>` 都有对应媒体且编号顺序一致
- [ ] 每镜一个说话人、一个运镜；时间码递增且小于总时长
- [ ] 没有否定句（§0 允许的极短排除词除外）；没有 `she/he` 指代多人
- [ ] 台词字数 ≤ (时长−2)×4.5
- [ ] 声景具体、配乐字段存在（或 N/A）
- [ ] 描述英文、台词原语言、`<d>` 内只有语言标签+原话

## 9. 本地提示词改写（Ollama / Qwen）

| 排序 | 方案 | 模型 |
|------|------|------|
| 1 | `pip install open-h3-ir` + Ollama 作 OpenAI 兼容端点（`H3IR_LLM_URL=http://127.0.0.1:11434/v1`），ComfyUI 侧 `ruashots/ComfyUI-OpenH3-IR`；自带 122 KB 验证器（帧格、1.2 s 下限、台词零改写、R15 服装重述、A8 配乐禁情绪词） | `qwen3-vl:8b` 起步；27B Q4 须与 H3 串行 |
| 2 | `duckyshell/ComfyUI-MiniMaxH3-Prompt-Writer`（Ollama 前端，Sequence 模式出 30/60 s 多段） | `qwen3-vl:8b` / `gemma4:26b` |
| 3 | `pytraveler` Writer + Reference Caption + Prompt Check + Reducer（直读 Ollama GGUF） | Qwen3.5-9B Q4 ≈ 8 GB |
| 4 | `chflame163/ComfyUI_Qwen_H3_Prompt`（内置 llama-server + 官方 9 个 skill 原文） | Qwen3.8-27B Q4 ≈ 16 GB |

`qwen3-vl:4b` 只够做参考图 caption 与 Reducer；写作交给 8–9B；终稿过 open-h3-ir 验证或本 skill 的 `scripts/lint_prompt.py`。写手模型用完立即卸载（`keep_alive: 0`）再跑 H3；上下文 ≥ 9.2K（base）/ ≥ 12.3K（ref）。案例库：SkyNotSilent/awesome-MiniMax-H3-cases `cases.json`（781 条逐字 Prompt，可按电影叙事 / 角色对白 / 动漫过滤）。
