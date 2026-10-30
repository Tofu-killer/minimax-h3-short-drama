# 04 · H3 提示词工程：短剧向完整方法论

> 依据：MiniMax 官方 `skills/h3-prompt-writing`（`references/base-en.txt`、`ref-en.txt`）、H3‑Context‑IR 输出样例、ComfyUI 官方文档、HackerNoon / APIDot / Krea / Kapwing / RunDiffusion / HelloGen / minimax‑h3.com 等指南。官方语法优先；社区简写标注为「社区」。

## 1. 两种官方输出结构

H3 内部（Context‑IR）把任何输入重写成下面两种格式之一。**直接按这个格式写提示词，效果最稳**；不按格式写也能用，但模型会先猜你的意图再改写。

### 1.1 三段式（T2VA / I2VA / FL2VA / L2VA）

```
<可选的首尾帧对齐声明行>

integrated_multimodal_description: [Shot 1] <风格词>, <景别> … <动作> … <运镜> … <说话人>(S1) says: <d>[Language] 台词</d> [Shot 2] At 00:04.500, the camera cuts to …

overall_soundscape: <1–4 句环境音与物理音效，一个自然段>

non_diegetic_music: <1–3 句配乐：乐器、速度、节奏、动态变化；无配乐写 N/A>
```

首尾帧声明行（逐字格式）：

| 模式 | 声明行 |
|------|--------|
| I2VA（首帧） | `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.` |
| FL2VA（首尾帧） | `How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.` |
| L2VA（尾帧） | `How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.` |

官方对 FL2VA 的提醒：**首尾帧通常用单镜头**，让模型连续插值；只有显式指定时才切镜。

### 1.2 六段式（Ref2VA 全能参考）

```
subject_definitions: <Subject 1> is the young woman in <Picture 1>, with shoulder-length black hair and a green field jacket. <Subject 2> is … <Audio 1> is the voice-timbre reference for <Subject 1> (S1).

summary: [reference generation + audio reference] <一两句话说明目标视频内容与镜头数>

retention_analysis: <Subject 1> (appears in [Shot 1], [Shot 3]): fully_preserved - face, hair and jacket are retained. <Subject 3>: weak_reference - only the lighting mood. Do not reuse either reference's background.

detailed_description: <风格一两句> [Shot 1] … [Shot 2] At 00:05.000, the shot cuts to … （生成任务通常 350–500 英文词）

overall_soundscape: …

non_diegetic_music: N/A
```

标签体系：

| 标签 | 含义 |
|------|------|
| `<Picture N>` | 第 N 张参考图（按 `content` 数组顺序） |
| `<Video N>` / `<Audio N>` | 第 N 段参考视频 / 音频，各自独立编号 |
| `<Subject N>` | 从参考素材抽象出来的可复用实体（人、服装、地点、道具） |
| `(S1)` `(S2)` `(S1,S2)` | 说话人 ID，一个片段内稳定；不说话的角色不给 ID |

保留强度词：视觉 `fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`；音频 `fully_copy` / `partially_copy` / `reference` / `weak_reference`。

summary 任务前缀（按实际用途组合）：`keyframe completion`、`reference generation`、`video editing`、`video continuation`、`audio reuse`、`audio reference`。

> 社区简写：ComfyUI 文档与多数博客用 `Image 1 / Video 1 / Audio 1` 或 `@Image1`。API 直连时建议用官方 `<Picture N>`；两种写法都被模型理解，但不要混用。

## 2. 镜头与时间码

- 第一镜 **不写** 时间码；之后每镜以 `[Shot N] At MM:SS.mmm, the camera cuts to …` 开头，时间严格递增且不超过 `duration`。
- 切镜动词：`the camera cuts to` / `the shot cuts to` / `the shot transitions to` / `the shot changes to` / `the shot switches to`。
- **切镜必须带来新信息**（新角度、新人物、反应）；只是拉近一点就用运镜而不是切镜。
- 15 秒约承载 3 个镜头、2–4 句短台词；5 秒一镜一句。
- 社区节拍写法 `0–5s: … 5–10s: …` 或 `[0-3s] …` 同样可用，但官方 IR 会把它们改写成 `At 00:05.000` 形式。

## 3. 运镜词表（官方）

Zoom In / Zoom Out · Push In / Pull Out · Pan Left / Pan Right · Truck Left / Truck Right · Tilt Up / Tilt Down · Pedestal Up / Pedestal Down · Arc Shot · Tracking Shot · Static Shot · Shake Slightly / Shake Strongly · POV · Roll Clockwise / Roll Counterclockwise

修饰：幅度 `with small amplitude` / `with large amplitude`；速度 `at slow speed` / `at fast speed`。中等幅度与正常速度省略不写。

示例：`The camera pushes in with small amplitude at slow speed toward the folded letter in her hands.`

规则：**一镜一个主运镜**；多个运镜叠加几乎必然漂移。Kapwing 提醒：旧版 Director 模式的 `[推进] [左移]` 方括号指令不再是 H3 的主语法，用自然电影语言写。

## 4. 对白与声音（短剧最关键的部分）

### 4.1 台词格式

```
The young woman with a quiet, breathy voice (S1) says: <d>[Chinese] 你到底瞒了我多久？</d>
The two children (S1,S2) shout together, <d>[English] Wait for us!</d>
```

- `<d>` 内只放 **语言标签 + 原话**，不翻译、不改写；描述段用英文，台词保持目标语言。
- 声音特征（低沉/沙哑/语速）写在 `(S1)` 之前的人物描述里，并在**每个片段原样复用**（HelloGen："paste it word for word into every clip"）。
- 情绪与停顿写在 `says:` 之前：`She sets the cup down, then (S1) says softly: <d>…</d>`。

### 4.2 画外音 / 旁白

```
The man (S1) says in an off-screen voiceover: <d>[Chinese] 我至今记得那条路。</d> while his lips remain completely closed.
```

不加「嘴唇闭合」声明，模型会让画面里的人对口型。

### 4.3 跨镜头台词与截断

- 一句台词横跨剪切点：两端都加 `<scenetrans>`，并写 `continues seamlessly across the cut`。
- 片尾被打断的话：用 `<cutoff>`。

### 4.4 对话戏规则（综合）

1. **一镜一人开口**；对手戏写明听者 `listens with his mouth closed` 并给出反应，否则会出现「错人张嘴」。
2. 先动作再说话（`She sets the cup down, then says…`），模型需要动作锚点来排时间。
3. 每 3–4 秒一句台词，或明确写出哪几秒是沉默。
4. 单镜头内最多 3 个有动作/台词的人物（官方 3d‑animation skill）。
5. 双人同框写相对位置和身高：`<Subject 2> stands at frame right, a head taller`。
6. 正反打：Shot 1 过肩 A 看 B，Shot 2 `At 00:05.000, the shot cuts to` 反向过肩；两镜都写明视线方向（eyeline）与各自服装锁定。
7. 台词太长就换下一段，不要要求「说快点」。

### 4.5 声景与配乐

- `overall_soundscape`：1–4 句，具体到物体与动作（"The entrance bell rings once, followed by wet footsteps and the soft scrape of a chair"），禁止「紧张」「悲伤」这类抽象词；只有用户要求完全静音才写 `N/A`。
- `non_diegetic_music`：乐器、速度、节奏、动态；无配乐写 `N/A`。短剧全集统一后期铺乐时，各段都写 `N/A`。
- 不写声音 ≠ 没声音，模型会自行补环境音；想要后期全控就明确写 `no music`。

### 4.6 音色参考

- `<Audio 1>` 2–15 秒干净人声（无 BGM、无混响、不削波），且必须伴随至少一张图或一段视频。
- 参考只决定音色，口音/情绪/语速仍需文字描述：`using the clear youthful voice timbre referenced from <Audio 1>, exclaims with light annoyance`。
- 只借音色不借内容时，不要把参考音频里的原话带进来；想完整复用原音轨则标 `fully_copy`。

## 5. 风格与视觉描述

- 开头一两句定风格：`Live-action, cinematic` / `2D-animated` / `3D CG` / `claymation` / `watercolor` / `vintage film`。
- 具体胜于抽象：禁用 `4K, masterpiece, ultra-realistic, cinematic, beautiful` 之类无信息词；写光源、焦段、材质。
- 形容词超过 3 个开始失效（Morphed 实测）。
- 画面文字：英文双引号 + 原语言 `A red neon sign reading "营业中"`；但精确文字不可靠，字幕一律后期。
- 画幅用 `ratio` 参数，不要写进提示词。

## 6. 一致性相关写法

见 `docs/05-consistency.md`。核心三条：
1. **每个参考文件一个职责**：`<Picture 1>` 只管脸，`<Picture 2>` 只管服装，`<Picture 3>` 只管环境与光；`Never transfer facial traits from Image 3`。
2. **固定识别短语**：角色描述一字不改地复用；用 `<Subject 1>` 而不是 `she`。
3. **写不变量，不写状态**：年龄/骨相/发型属于参考图，湿头发/撕破的袖子属于场景描述；不要在片段中途改变人物。

## 7. 短剧完整示例

### 7.1 Ref2VA 六段式，三镜头正反打（15 s，9:16）

```
subject_definitions: <Subject 1> is the young woman in <Picture 1>, shoulder-length black hair, green field jacket. <Subject 2> is the man in <Picture 2>, short grey beard, navy wool coat. <Subject 3> is a small station café at night: one counter, three stools, rain on the front window.

summary: [reference generation] <Subject 1> has been waiting in <Subject 3>; <Subject 2> arrives late, and she decides to let him stay. Three shots, 15 seconds.

retention_analysis: <Subject 1> (appears in [Shot 1], [Shot 3]): fully_preserved - face, shoulder-length black hair and green field jacket are retained. <Subject 2> (appears in [Shot 2], [Shot 3]): fully_preserved - face, short grey beard and navy wool coat are retained. Do not reuse either reference's background.

detailed_description: Live-action, naturalistic drama, cool fluorescent light inside, warm street light through the rain-streaked window. [Shot 1] A medium shot from across the counter: <Subject 1> sits on the middle stool facing the camera, both hands around a paper cup. The camera pushes in slowly. She looks up toward the door, and <Subject 1>, a woman in her late twenties with a low, slightly husky voice and an unhurried pace (S1), says: <d>[Chinese] 你迟到了四十分钟。</d> [Shot 2] At 00:05.000, the shot cuts to the doorway: <Subject 2> steps in from frame right with rain on his shoulders and stops, facing the camera. <Subject 2>, a man in his fifties with a deep, quiet voice (S2), says: <d>[Chinese] 末班车停了，我走过来的。</d> [Shot 3] At 00:10.000, an over-the-shoulder shot from behind <Subject 2>, who stands at frame right, a head taller; <Subject 1> faces the camera from her stool at frame left. She studies him, sets the cup down and slides it toward him, then <Subject 1> (S1) says: <d>[Chinese] 坐吧，还热着。</d>

overall_soundscape: Rain on the window, the low hum of a drinks fridge, the door's bell once at 00:05, wet footsteps, a paper cup sliding on laminate.

non_diegetic_music: N/A
```

（改编自 HelloGen 示例，台词改为中文。）

### 7.2 I2VA 三段式，单人钩子镜头（6 s）

```
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, the young woman shown in <Picture 1> remains beside the rain-covered train window, preserving her appearance, clothing, seat position, and the carriage layout. The camera pushes in with small amplitude at slow speed as she folds the letter and turns toward the passing lights. The woman with a quiet, breathy voice (S1) says: <d>[Chinese] 下一站，我就下车。</d>

overall_soundscape: Train wheels create a metallic rhythm beneath a low ventilation hum. Rain ticks against the glass while paper moves in her hands.

non_diegetic_music: Sustained cello notes at a slow tempo with widely spaced piano tones.
```

### 7.3 自然语言写法（社区，适合海螺 App 直接输入）

```
Two characters sit opposite each other in a quiet train compartment.
Static medium two-shot. Preserve both faces, outfits, seats, and eyelines.
0–5s: Character A looks out the window.
5–10s: Character A turns and says, "We missed the last stop."
10–15s: Character B reacts silently, then looks toward the door.
Natural carriage ambience; accurate lip synchronization for Character A only.
No camera movement and no shot change.
```

### 7.4 官方级短剧 teaser（forgewebO1 收录，源自 MiniMax 官方指南）

```
Create a 15-second, 9:16 live-action vampire-romance teaser for an international short-drama audience. Use Image 1 for the leads' appearance and Image 2 for the setting. Preserve both identities throughout and maintain premium live-action production value.

Story: an innocent human woman strays into a forbidden wing of an old castle and awakens a sleeping vampire noble. He senses that she carries a trace of an ancient war, which sparks dangerous fascination and a possessive need for control. She fears him but refuses to submit completely and pushes back against his dominance.

Style: ReelShort / DramaBox vampire romance—darkly romantic, fate-bound, oppressive, and charged with dangerous attraction, with a strong hook and a high-impact turn. Keep it polished, restrained, and tightly paced like the opening 15 seconds of a breakout series. No gore, cheap horror, Halloween styling, or modern street aesthetic.

Compose for TikTok / ReelShort / DramaBox. Favor medium-close shots, close-ups, and extreme close-ups that emphasize faces, eye contact, pressure, and relationship tension.
```

这条说明了：**给 Context‑IR 一段"制片人简报"也能出片**，IR 会自己补成结构化描述。工业化流水线更推荐自己写六段式以便复现。

## 8. 常见错误速查

| 写法 | 问题 | 改为 |
|------|------|------|
| `cinematic, 4K, masterpiece` | 不指向任何镜头或光 | 写光源、焦段、运镜 |
| `she says "…"` 没有 (S1) 和语言 | 错人开口、含糊音 | `<Subject 1> (S1) says: <d>[Chinese] …</d>` |
| 同镜头 `push in` + `handheld` + `orbit` | 运镜漂移 | 一镜一运镜 |
| 每镜重复描述发型服装 | 与参考图冲突产生漂移 | 服装进参考图，文字只写不变量 |
| 提示词里要求字幕 | 字幕重复/乱码 | 后期烧录 |
| 用 `she` 指代 | 多人物时指代错乱 | 始终 `<Subject 1>` |
| 15 s 塞 6 句台词 | 语速失真、口型崩 | 拆段 |
| 把 16:9 画幅写在文字里 | 无效 | 用 `ratio` 参数 |
