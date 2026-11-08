# 类型包 · MV 音乐视频（演唱对口型 / 卡点 / 歌词排版）

> 音乐时间轴驱动一切：先锁母带与歌词，再切镜。官方 `music-video-subtitle-generator` + 社区 lipsync 实测整理。

## 适用与 H3 强弱项

- **强**：对象分层与提示词遵循（SkyNotSilent `x-tapehead-composition-mv`）；带 MG 动态排版的动画场景同输入对照胜 Seedance 2.5（`x-2087563166654067099`）；Ref2VA 可把分离人声作 `<Audio 1>: fully_copy` 让角色对口型（animede `Minimax-H3-lipsync-mv`，`09-long-tail`）。
- **弱**：单次 ≤ 15 s，整首歌必须多段拼接；`fully_copy` 约 0.45 s 系统位移（`camera-and-performance.md` §5）；中文歌词在画面里会错字（guangjun5952：中文排版仍会错字）；歌唱侧脸口型差。
- **绕法**：官方多镜拼接协议：一条母带、4–8 个 2–5 s 镜头、切点落在 1/4 或 1/8 拍且避开元音中间、只用硬切、全片统一 LUT 与颗粒（官方 MV skill STEP 6）；歌唱镜强制正面或 3/4 中近景露嘴（animede）；中文歌词排版后期做，画面内只允许 1–3 个英文大字。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | 演唱段：Ref2VA（角色板 + 场景板 + `<Audio 1>` Demucs 分离的人声 stem，`fully_copy`），**歌词不写进 `<d>`**（animede）；纯画面段：T2VA / I2VA + 乐器描述 |
| 段长 / 镜数 | 按小节切 5–10 s（animede DP 切分：无音 / 音量谷 / 换气 / 小节）；每段 2–3 镜，切点 = onset（LoveRain1997） |
| 步数 | Turbo 8 步 shift 12/3；跟拍镜定稿 20 步；同参考图多段可落盘条件编码复用 |
| 成片音轨 | 用原曲替换生成音轨，按时间码对齐；接缝落在换气 / 军鼓 |

## 风格句

`Live-action music video, photoreal, shot on a 35mm lens, cold fluorescent top light with a single magenta practical glow as rim, a faint haze as the air layer, a palette of tile white, cold green and magenta, heavy 35mm film grain with slight halation, performance-driven acting.`

官方预设语法（Dark-pop / Cyber-grunge / Trap）：杂志胶片质感、半调网点、扫描错位，**只用硬切**，图像对 hi-hat / snare / 808 起反应。

## 镜头与运镜要点

- 每个切点写「为什么在这里切」：`cuts on the snare hit` / `on the next downbeat`（LoveRain1997：转场 = 动作钩子 + 切点原因 + 下段续动）。
- 快节奏 MV 在同一情绪下快速切换多个近景空间（隧道、墙面、灯带），场景切换由音乐冲击触发（官方 STEP 3.1）。
- 段间衔接：同场景用上段尾帧作下段首帧；硬切换景用同向运动或遮挡匹配（官方 STEP 6.2）。

## 表演与台词要点

- 写口型与呼吸：`lip shapes, jaw motion and breaths follow the phrasing of <Audio 1>`；点头、手部重音落拍。
- 歌词是锁定文本，不改写、不翻译；排版文字必须与正在唱的词逐字一致，且不遮眼睛与嘴（官方 STEP 4）。

## 声音

`overall_soundscape` 只写现场小声（脚步、隧道风、换气）；`non_diegetic_music` 写伴奏乐器与速度并声明与 `<Audio 1>` 同速，便于模型卡点；没有现成歌时先写一段详细 BGM 提示词（曲风 / BPM / 乐器 / 段落 / 重音位置）并声明动作由它驱动（LoveRain1997）。

## 参考素材准备

角色板、场景板、（可选）排版风格卡三者职责隔离——排版卡只管字体质感与动效语言，不贡献人和场景（官方 STEP 3）；人声 stem 用 Demucs 分离、每段截取对应窗口；参考图短边 1024、哑光均匀光（animede）。

## 示例提示词（Ref2VA，10 s，2 图 + 1 音频）

接线：`<Picture 1>` 歌手 → `<Picture 2>` 地铁站台 → `<Audio 1>` 本窗口人声 stem（fully_copy）。

```text
subject_definitions: <Subject 1> is the singer, a woman in her mid-twenties with a defined oval face, a wolf-cut of black hair with blue tips, dark winged eyeliner, small silver hoop earrings, wearing an oversized black leather jacket over a white tank top, defined by <Picture 1>. <Picture 2> is the environment: an empty underground subway platform at night with white tiled walls, a row of cold fluorescent strips, yellow safety lines and a dark tunnel mouth at the far end. <Audio 1> is the isolated lead-vocal stem of the song for this 10-second window, sung by <Subject 1> (S1).

summary: [reference generation + audio reference] The singer performs one chorus phrase on an empty subway platform at night, her lip movements following the vocal in <Audio 1>; three shots cut on the beat, 10 seconds, 16:9.

retention_analysis: <Picture 1>: fully_preserved - facial identity, blue-tipped wolf-cut, eyeliner, earrings, leather jacket and tank top; no other garment is substituted; its background is ignored. <Picture 2>: partially_preserved - tiled walls, fluorescent strips, safety lines and tunnel mouth; the camera may move; never transfer facial traits from <Picture 2>. <Audio 1>: fully_copy - the lead vocal is reproduced exactly as recorded, and <Subject 1> lip-syncs every syllable of it.

detailed_description: Live-action music video, photoreal, shot on a 35mm lens, cold fluorescent top light with a single magenta practical glow from the tunnel mouth as rim, a faint haze hanging over the platform as the air layer, a palette of tile white, cold green and magenta, heavy 35mm film grain with slight halation, performance-driven acting. The setting is the platform in <Picture 2>. Exactly one person is present. Her lip shapes, jaw motion and breaths follow the phrasing of <Audio 1> from the first frame to the last, mouth open on each vowel and closing on each consonant, face kept toward the camera or at three-quarter angle while she sings. [Shot 1] A frontal medium close-up of <Subject 1>, the woman with the blue-tipped black wolf-cut and the oversized black leather jacket, standing on the yellow safety line; she sings the opening of the phrase straight into the lens, her head nodding on each kick drum, one hand gripping the collar of her jacket, the fluorescent light drawing a hard highlight along her cheekbones and the worn leather. The camera pushes in toward her face with small amplitude at slow speed. [Shot 2] At 00:03.500, the shot cuts on the snare hit to a low-angle wide shot down the length of the platform: <Subject 1> walks toward the camera along the safety line, singing, the leather jacket swinging open over the white tank top, the fluorescent strips sliding overhead in perspective, her steps landing on the beat, the silver hoop earrings catching each strip of light as she passes beneath it. The camera tracks backward ahead of her at her walking pace. [Shot 3] At 00:07.000, the shot cuts on the next downbeat to a three-quarter close-up of <Subject 1>, magenta rim light on her cheek and silver hoop earring, a gust from the tunnel lifting the blue tips of her hair; she holds the last long vowel of the phrase with her eyes half closed, then lets the breath go. The camera holds a static shot. In the final second she settles and holds the pose, breathing, hair still moving, while the framing stays put. The segment ends with <Subject 1> in three-quarter close-up at frame center, eyes lifting to the lens.

overall_soundscape: A low fluorescent hum, boots stepping on tiled concrete in time with the beat, a soft rush of tunnel wind, the singer's breaths between lines.

non_diegetic_music: A mid-tempo dark-pop backing track with a punchy kick drum, a snapping snare on beats two and four, a sub bass line and a filtered synth pad, matching the tempo of <Audio 1>, steady dynamics through the window.
```

lint：`--seconds 10 --images 2 --audios 1` → PASS，0 error / **1 warning**（「段内无 `<d>`」）。**保留理由**：演唱段按 animede 做法让口型跟 `<Audio 1>` fully_copy，歌词刻意不写进 `<d>`；不要为了消警告加 `Nobody speaks`（会让歌手闭嘴）。372 词。

## 该类型禁忌

- 溶解 / 淡入淡出转场（官方：只用硬切）；在元音中间切镜。
- 每段各自生成配乐再拼（段缝音乐跳）；不锁母带就开拍。
- 让 H3 在画面里写整句中文歌词；歌手侧脸长镜演唱。
