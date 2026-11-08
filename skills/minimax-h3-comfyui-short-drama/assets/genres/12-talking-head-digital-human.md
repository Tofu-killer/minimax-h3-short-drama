# 类型包 · 口播 / 数字人

> 一个人对镜头说话。两条路线：H3 按 `<d>` 自己说（音色参考）；或已有配音要逐字对口型（音频锁定节点）。

## 适用与 H3 强弱项

- **强**：一张定稿脸 + 一段音色即可出带口型的胸像口播；原生音频与口型同步出；可做 1 分钟片的分段拼接（mcoblackmore `digital-human-16gb`，`11-fresh-repos`）。
- **弱**：嘴动幅度偏小；镜头会自己轻微漂移 / 呼吸（实测中心抖动约 11 px）；胸像下缘凭空长出手指，提示词压不住；把配音塞进 `ref_audios` 只影响音色，模型会自编语音与时序（嘴型与配音相关性 0.04）；16 GB 卡单段约 192 帧（8 s）见顶（以上均 mcoblackmore 实测）；原生音色每段漂约 1.7 半音（egguy886）。
- **绕法**：要逐字对现成配音走 `PixaromaH3AudioSync`（ComfyUI-Pixaroma）而不是 `ref_audios`；写 `clear, pronounced lip movements … on every syllable` 加大嘴型；拼接前裁掉底部 12%、按最大脸对齐只放不缩（≤ 1.35×）、按语音边界裁段头（mcoblackmore `join_clips.py`）。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 路线 A（H3 自己说） | Ref2VA：`<Picture 1>` 定稿胸像（含背景）+ `<Audio 1>` 2–8 s 干净音色（`attribute_transfer`）；台词写 `<d>` |
| 路线 B（现成配音） | Ref2VA + `PixaromaH3AudioSync` 锁音频（说的是克隆音色，波形与原录音不同）；要原录音逐字一致只能换 Wan + InfiniteTalk 路线（mcoblackmore 3B） |
| 段长 / 镜数 | 16 GB：≤ 8 s/段；24 GB 可 10 s；1–2 镜，第二镜只做「跳切到更紧景别」 |
| 台词 | ≤ (段长−2)×4.5 字；每 3–4 s 一句；句末留 ≥ 0.2 s（3ALLBUY14 `lipsync-guide`） |
| 步数 | Turbo 8 步 shift 12/3；高分辨率走「8plus2」：草稿 896×512 8 步 → latent 1.8× → 只跑最后 2 步（`SplitSigmas` 取输出槽 1）+ 2K refiner LoRA + 音频遮罩（mcoblackmore 3A-2）；SeedVR2 会让嘴部发飘 |

## 风格句

`Live-action talking-head video, photoreal, natural creator-studio look, shot on a 35mm lens at chest height, shallow depth of field, a large soft key light from frame right, a warm desk lamp as a practical, matte and evenly lit skin with natural texture, relaxed and friendly delivery.`

## 镜头与运镜要点

- 只写一句静止：`The camera is static, on a tripod, with no camera movement whatsoever.`（`prompt-format.md` §0 唯一例外句式；再叠 no pan / no zoom 会让切点漂移）。不要事后整帧防抖（会放大成呼吸式推拉，mcoblackmore）。
- 胸像构图、脸占画宽约两成（mcoblackmore 构图步骤）；双手写在画框下缘之外的位置，成片仍裁底 12%。
- 包装字卡（标题、要点）后期加：三档文字预算以「≤ 2 组、18 字」为推荐（guangjun5952 B-roll skill）。

## 表演与台词要点

- 台词归属三选一：对镜口型 `speaking to the camera` / 画外音 / 无台词，不留空档（3ALLBUY14）。
- 同一说话人两镜都写同一句音色描述（一字不改）；口型镜头用裁出的半身图而非全身三视图，四分之三或正面、无麦克风挡嘴（`storyboard-and-assets.md` §5）。

## 声音

安静处理过的房间底噪 + 干净近讲人声 + 衣物轻响；`non_diegetic_music: N/A`，BGM 与音效后期；拼接时段头 10 ms 淡入去爆音（mcoblackmore：段首爆音峰值 863 → 34）。

## 参考素材准备

定稿胸像一张（哑光均匀光，脸部油光来自参考图肤质——animede）；音色 2–8 s 无 BGM 无混响；要 16:9 但不想动脸就只外扩两边（mcoblackmore `outpaint_169.py`）。

## 示例提示词（Ref2VA 路线 A，10 s，1 图 + 1 音频）

```text
subject_definitions: <Subject 1> is Lao Zhou, a presenter in his late thirties with a square face, short neat black hair, thin black-framed glasses, a clean-shaven jaw, wearing a navy crew-neck sweater over a light grey collared shirt, defined by <Picture 1>, which also shows the home studio behind him: a light wooden bookshelf, a small green plant and a warm desk lamp on the left. <Audio 1> is the voice-timbre reference for <Subject 1> (S1).

summary: [reference generation + audio reference] A talking-head clip: Lao Zhou faces the camera in his home studio and delivers two short lines about a money-saving habit, with one jump cut to a tighter framing; two shots, 10 seconds, 16:9.

retention_analysis: <Picture 1>: fully_preserved - facial identity, hairstyle, glasses, sweater and shirt, bookshelf, plant and lamp placement; no other garment is substituted. <Audio 1>: attribute_transfer - voice timbre only; every spoken word comes solely from the quoted dialogue lines.

detailed_description: Live-action talking-head video, photoreal, natural creator-studio look, shot on a 35mm lens at chest height, shallow depth of field with the bookshelf softly blurred, a large soft key light from frame right, the warm desk lamp glowing on the left as a practical, matte and evenly lit skin with natural texture, a palette of navy, light wood and warm white, relaxed and friendly delivery. The setting is the home studio shown in <Picture 1>. Exactly one person is present, framed from the mid-chest up, centered, both hands resting below the bottom edge of the frame, face toward the lens the whole time. The camera is static, on a tripod, with no camera movement whatsoever. [Shot 1] A medium close-up of <Subject 1>, the presenter with short neat black hair, thin black-framed glasses and the navy crew-neck sweater over a light grey collar, seated upright and facing the lens, shoulders relaxed and square to the camera, the desk lamp glowing softly over his left shoulder and the green plant blurred behind his right; he blinks once, draws a light breath, gives a small open smile, then, speaking to the camera with a warm, clear, mid-pitched voice and an easy, even pace, with clear, pronounced lip movements that open and close fully on every syllable, (S1) says: <d>[Chinese] 大家好，今天聊一个省钱的小习惯。</d> [Shot 2] At 00:05.200, the shot cuts to a tighter close-up of <Subject 1> from the same angle, his face filling the center third of the frame, the glasses catching a soft highlight from the key light, the navy collar at the bottom of the frame; his eyebrows lift slightly with interest, he leans in a few centimetres toward the lens, keeping his head level and his eyes locked on the lens, and, speaking to the camera with the same warm, clear, mid-pitched voice and a slightly more emphatic pace, with clear, pronounced lip movements, (S1) says: <d>[Chinese] 每天记账五分钟，月底多存三百。</d> In the final second he holds the pose, breathing, while the framing stays put. The segment ends with <Subject 1> in close-up at frame center, eyes on the lens. Speak only the quoted dialogue lines. After that nobody says anything else.

overall_soundscape: A quiet treated-room tone, a dry, close-miked male voice, a soft rustle of the sweater as he leans in, one light breath before the second line.

non_diegetic_music: N/A
```

lint：`--seconds 10 --images 1 --audios 1` → PASS，0 error / 0 warning；367 词；台词 27 字（上限 36）。

## 该类型禁忌

- 写 `hands out of frame, no fingers`（否定句压不住，反而招手）；用整帧变换「锁脸」。
- 把配音只塞 `ref_audios` 就以为会逐字对口型；两句台词塞进一镜且中间无停顿。
- 16 GB 卡直接渲 1280×736 或 latent 放大到 1280（进程级 OOM，mcoblackmore）。
