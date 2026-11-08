# 类型包 · 都市情感对白（真人向）

> 本 skill 的主场：两人对手戏、正反打、台词驱动。风格句沿用 `../style-cinematic.md`，本页只补类型差异。

## 适用与 H3 强弱项

- **强**：原生对白 + 口型 + 环境声一次出；Ref2VA 同时锁两张脸、两种音色；静态小景别的细微面部表演稳定（社区对照称 H3「细微面部锁定更强」，SkyNotSilent `x-2087507568046514509`）。
- **弱**：中文真人对白**直出**盲评 0:4 输 Seedance，**垫首帧后 4:0 赢**（garycaogan，`09-long-tail` §garycaogan）；多人同框同时说话必乱（案例 5 董事会四人四句，`04-prompting-tools` 高质量案例）；原生音色每段漂约 1.7 半音（egguy886）；同性别两人对话易串音（`storyboard-and-assets.md` §1）。
- **绕法**：先用图像模型出首帧/每镜分镜图作 `<Picture 1>` 开场锚；只用单人正反打，同框只作建立镜；音色后期 seed-vc 统一。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | Ref2VA 六段式 + 首帧锚（`<Picture 1>` = opening-frame anchor）；单人钩子镜可 I2VA |
| 段长 / 镜数 | 8–12 s；10 s ≤ 2 镜、12–15 s ≤ 3 镜，内部镜 ≥ 4 s（dramake） |
| 台词 | ≤ (段长−2)×4.5 字，目标 3.3–4 字/s；单段说话人 ≤ 2 |
| 步数 | 草稿 Turbo 8 步 v1.1 768p，shift 12/3，每段 2–3 seed（说话节奏绑 seed）；有推镜的定稿 20 步关 Turbo |
| LoRA | 默认不挂；写实人物可 A/B `fal/research-mini-max-h3-realism-people-lora`（`lora-and-style.md` §3） |

## 风格句

`Live-action, cinematic, photoreal, shot on a digital cinema camera with a 50mm spherical lens, shallow depth of field, natural skin texture with visible pores, subtle film grain, a single warm practical lamp as key light with cool window light as rim, a palette of cream, charcoal and amber, restrained acting.`

## 镜头与运镜要点

- 建立镜一颗同框中/全景交代站位，台词一律单人过肩正反打，机位在听者视线上、偏离镜头轴 25–40°（phileiny，`04` 规则 6）。
- 每镜只一个运镜：说话人慢推（`pushes in … small amplitude at slow speed`），听者反应镜 Static；首镜只锚一个具名主体（JGRFW H12）。
- 每镜重述服装关键词（open-h3-ir R15）；写空间锚点卡（门、灯、桌）每段复述（forest-laoli，`camera-and-performance.md` §4）。

## 表演与台词要点

- 先动作后台词；有台词的镜头整镜只做说话；听者写 `listens with his mouth closed` + 一个身体反应。
- 情绪落成肌肉动作（视线落地 → 抬眼 → 呼吸），四拍：trigger → reception → response → settled（T8 / phileiny）。
- 对白段**不要精简提示词**（< 400 词人声提前 1.5 s 开口，egguy886）；结尾加 `Speak only the quoted dialogue lines. Those are the only words.`（`camera-and-performance.md` §5c）。

## 声音

安静房间底噪 + 动作声 + 干净人声；`non_diegetic_music: N/A`，配乐后期全集统一铺（egguy886 QUIET_SOUND）；soundscape 不写 crowd / chatter（mathruffian，`10-unread-followup`）。

## 参考素材准备

首帧锚（图像模型出，16:9，含两人站位与关键道具）→ 每人一张 16:9 角色设定板（脸 + 正侧背）→ 每个说话人 2–8 s 干净音色。首帧里的道具（杯子、行李箱）在文本中写 `already … in <Picture 1>`。

## 示例提示词（Ref2VA，10 s，3 图 + 2 音频）

接线顺序：`<Picture 1>` 首帧锚 → `<Picture 2>` 夏 → `<Picture 3>` 陈 → `<Audio 1>` 夏音色 → `<Audio 2>` 陈音色。

```text
subject_definitions: <Picture 1> is the opening-frame anchor: the exact composition, positions and lighting at 00:00.000 of this segment, a small apartment kitchen at night with a white ceramic mug on the counter and a black suitcase by the doorway. <Subject 1> is Xia, a woman in her late twenties with a soft oval face, shoulder-length dark brown hair with straight bangs, light brown eyes, an oversized cream knit cardigan over a pale blue T-shirt, defined by <Picture 2>. <Subject 2> is Chen, a man in his early thirties with a narrow face, short black hair swept back, light stubble, a charcoal wool overcoat over a white open-collar shirt, defined by <Picture 3>. <Audio 1> is the voice-timbre reference for <Subject 1> (S1). <Audio 2> is the voice-timbre reference for <Subject 2> (S2).

summary: [reference generation + audio reference] In a small apartment kitchen at night, Xia asks Chen why she was the last to know he is leaving, and he answers; two shots, 10 seconds, 16:9.

retention_analysis: <Picture 1>: fully_preserved - composition, positions, set dressing and lighting at 00:00.000; the framing continues from it. <Picture 2>: fully_preserved - facial identity, hairstyle, cardigan and T-shirt colors; no other garment is substituted; its background is ignored. <Picture 3>: fully_preserved - facial identity, hairstyle, stubble, overcoat and shirt; no other garment is substituted; never transfer facial traits from <Picture 3> onto <Subject 1>. <Audio 1>: attribute_transfer - voice timbre only for <Subject 1>. <Audio 2>: attribute_transfer - voice timbre only for <Subject 2>.

detailed_description: Live-action, cinematic, photoreal, shot on a digital cinema camera with a 50mm spherical lens, shallow depth of field, natural skin texture with visible pores, subtle film grain, a single warm pendant lamp above the counter as key light, cool blue city light through the window behind the doorway as rim, a palette of cream, charcoal and amber, restrained acting. The opening frame shown in <Picture 1> is preserved: appearance, clothing, positions and set. Exactly two people are present. <Subject 1> stands at frame left beside the counter, facing right toward the doorway, her right hand resting on the white mug already on the counter in <Picture 1>; <Subject 2> stands in the doorway at frame right, his right hand on the handle of the black suitcase from <Picture 1>, facing her. [Shot 1] An over-the-shoulder medium close-up on <Subject 1>, taken from behind the right shoulder of <Subject 2>, his charcoal overcoat soft and out of focus at the right edge of the frame. <Subject 1>, the woman with shoulder-length dark brown hair, straight bangs and the cream knit cardigan, slides the mug two centimetres away from her, keeps her fingers curled on the counter, lifts her eyes to his face, and then, with a low, slightly trembling voice and a slow, deliberate pace, (S1) says: <d>[Chinese] 你要走，为什么最后一个告诉我？</d> The camera pushes in toward her face with small amplitude at slow speed, the focal length locked throughout. <Subject 2> listens with his mouth closed, his shoulder rising with one slow breath. [Shot 2] At 00:05.000, the shot cuts to a reverse medium close-up on <Subject 2> over the left shoulder of <Subject 1>, her cream cardigan and dark brown hair blurred at the left edge of the frame, the cool window light rimming his swept-back black hair and light stubble. <Subject 2>, the man in the charcoal wool overcoat and white open-collar shirt, loosens his grip on the suitcase handle, lowers his eyes to the floor for a beat, raises them back to her, and with a quiet, husky voice and a slow, hesitant pace, (S2) says: <d>[Chinese] 因为我怕你开口留我。</d> The camera holds a static shot at eye level. <Subject 1> listens with her mouth closed at the left edge of the frame, her fingers pressing flat against the counter. In the final second both people settle and hold their positions, breathing, while the framing stays put. The segment ends with <Subject 2> in medium close-up just right of center, eyes on her, his right hand still on the suitcase handle; <Subject 1> at the left edge of the frame beside the mug; the same warm pendant light and cool window light. Speak only the quoted dialogue lines. Those are the only words.

overall_soundscape: A low refrigerator hum, the soft scrape of the ceramic mug sliding on a laminate counter, the creak of the suitcase handle as his grip loosens, a single slow exhale from Chen, faint rain ticking on the window glass.

non_diegetic_music: N/A
```

lint：`--seconds 10 --images 3 --audios 2` → PASS，0 error / 0 warning；detailed_description 451 词；台词 22 字（上限 36）。

## 该类型禁忌

- 四人同框轮流说话、一镜两人开口、同框并列句「X 与 Y 站在…」作首镜。
- 用 LLM 润色台词；台词里写 `...`；称呼后加逗号（会停 1 s）。
- 为赶字数让角色说快；台词外写 say / word / lips parted。
