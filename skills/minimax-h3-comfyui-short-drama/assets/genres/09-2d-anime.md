# 类型包 · 2D 日系动画

> H3 胜率最高的类型（直出盲评胜）。风格基础见 `../style-manga.md`，本包侧重日系 TV 动画与校园 / 恋爱向。

## 适用与 H3 强弱项

- **强**：动漫与 coser 片 H3 直出对 Seedance 2.0 mini 盲评 4:0、4:0，成本约 1/10（garycaogan，`09-long-tail`）；2D 对拖影不敏感，4 步草稿可用（`style-manga.md`）；限定动画（held poses）本身就适合 H3 的「状态」优势。
- **弱**：线宽与比例跨镜漂移；参考图画风不统一时漂向写实或西式草图（Inner-Reflections 模型卡：去掉 anime 一词会变西式草图）；画面里的日文 / 中文字不可靠；脸红写法在写实里会画成皮炎（egguy886），动画里要换成符号。
- **绕法**：所有参考图同一画风；正向锁「线宽、比例、配色每帧一致」；需要手绘线质感时挂 2D 风格 LoRA；夸张表情用漫符（汗滴、斜线腮红、圆眼）。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | Ref2VA 直出（2D 不需要先出首帧）；子镜头钉帧用官方 multiframe_reference 工作流 |
| 段长 / 镜数 | 8–12 s，对白 2 镜；动作 / 日常 2–3 镜 |
| 步数 | Turbo 4 步抽卡、8 步成片，shift 12/3；二采按需 |
| LoRA | `Inner-Reflections/MiniMax-H3-Looping-Sketch-Anime` 0.75–1.25（叠 Turbo 再加），提示含 `hand-drawn 2D anime art style, rough textured outlines, flat colors, white outline`；adf99 Anime Slider 正值更 2D（小幅）（`lora-and-style.md` §3） |

## 风格句

`2D-animated, hand-drawn Japanese TV anime style with clean dark line art, flat cel shading with two-tone shadows, soft painted gradient sky, limited animation with held poses and snappy key movements, consistent character proportions and line weight in every frame.`

可换配色尾句：`warm pastel palette` / `90s retro anime cel look` / `high-contrast noir ink`（`style-manga.md` 变体）。

## 镜头与运镜要点

- 以静帧 + 慢推为主，每镜一个大动作；复杂跟拍少用；转场硬切，不让模型做溶解（`style-manga.md`）。
- 校园 / 恋爱对白：女主中近景慢推 → 男主近景 Static，夕阳轮廓光两镜一致。
- 发丝、领巾、裙摆的风动是动画感来源，写进每镜。

## 表演与台词要点

- 漫符化：`a faint blush appears as three thin diagonal pink lines across his cheeks`、`eyes widen into round white circles, sweat drop`。
- 口型宽容度高，但一镜一人开口仍要守；日语台词写 `<d>[Japanese] …</d>`（H3 支持 11 种对白语言，`model-and-modes.md`）。

## 声音

风声、铁丝网轻响、远处蝉鸣与电车；配乐写钢琴琶音 + 轻弦乐，或 `N/A` 后期铺乐。

## 参考素材准备

角色设定板（正面 + 3/4，干净线稿 + 平涂，白底）；背景用动画背景画风格出（`anime background painting, … no characters`）——注意这是**图像模型**提示词，视频提示词里只写正向；参考图全部同一画风。

## 示例提示词（Ref2VA，10 s，3 图 + 2 音频）

接线：`<Picture 1>` 阳菜 → `<Picture 2>` 空 → `<Picture 3>` 天台 → `<Audio 1>` 阳菜 → `<Audio 2>` 空。

```text
subject_definitions:
<Subject 1> is the 2D anime high-school girl in <Picture 1>, with large teal eyes and long chestnut hair with a side braid and a yellow hair clip, wearing a navy sailor uniform with a red neckerchief.
<Subject 2> is the 2D anime high-school boy in <Picture 2>, with messy black hair and grey eyes, wearing a white short-sleeved shirt with a loose dark green tie.
<Subject 3> is the environment in <Picture 3>, a school rooftop at sunset with a green chain-link fence, a water tower on the right and the town skyline far below.
<Audio 1> is the voice-timbre reference for <Subject 1> (S1).
<Audio 2> is the voice-timbre reference for <Subject 2> (S2).

summary:
[reference generation + audio reference] On <Subject 3>, the school rooftop at sunset, <Subject 1> asks <Subject 2> whether he will come again tomorrow and he answers, across two shots. <Audio 1> is the voice-timbre reference for <Subject 1> and <Audio 2> is the voice-timbre reference for <Subject 2>.

retention_analysis:
<Subject 1> (appears in [Shot 1], [Shot 2]): fully_preserved - the anime face design, eye color, side braid, hair clip and sailor uniform are retained from <Picture 1>; no other garment is substituted; only the person is taken from this picture, the setting comes from the scene.
<Subject 2> (appears in [Shot 1], [Shot 2]): fully_preserved - the anime face design, messy hair, shirt and tie are retained from <Picture 2>; no other garment is substituted; never transfer facial traits from <Picture 2> onto <Subject 1>; only the person is taken from this picture, the setting comes from the scene.
<Subject 3> (appears in [Shot 1], [Shot 2]): partially_preserved - the fence, water tower, skyline and sunset direction are retained from <Picture 3>; the camera may move.
<Audio 1>: reference - its vocal timbre guides the dialogue delivery of <Subject 1> without copying the original signal; the spoken words come from the quoted dialogue lines.
<Audio 2>: reference - its vocal timbre guides the dialogue delivery of <Subject 2> without copying the original signal; the spoken words come from the quoted dialogue lines.

detailed_description:
The target video is in the following style: 2D-animated, hand-drawn Japanese TV anime style with clean dark line art, flat cel shading with two-tone shadows, soft painted gradient sky, warm orange sunset light from frame right with long violet shadows, small glowing dust motes in the air, limited animation with held poses and snappy key movements, consistent character proportions and line weight in every frame, a palette of sunset orange, navy and soft pink.
[Shot 1] The video opens on a medium close-up of <Subject 1>, the girl with the chestnut side braid, yellow hair clip and navy sailor uniform, her red neckerchief and braid lifting in the evening wind. The setting is <Subject 3>, the school rooftop at sunset. Exactly two characters are present, each appearing once. <Subject 1> stands at frame left by the chain-link fence; <Subject 2> stands at frame right near the water tower, facing her. She holds the strap of her school bag with both hands, glances down, then lifts her teal eyes to him, the sunset catching a bright highlight in each eye. <Subject 1> (S1), using the voice timbre referenced from <Audio 1>, says with a soft, small voice and a slow, hesitant pace, <d>[Chinese] 明天，你还会来吗？</d> She closes her lips. The camera pushes in toward her face with small amplitude at slow speed. <Subject 2> listens with his mouth closed, out of focus at the right edge of the frame.
[Shot 2] At 00:04.800, the shot cuts to a close-up of <Subject 2>, the boy with messy black hair and the loose dark green tie, the sunset rimming his hair; his grey eyes widen for a beat, a faint blush appears as three thin diagonal pink lines across his cheeks, he scratches the back of his head with one hand and looks straight at <Subject 1>. <Subject 2> (S2), using the voice timbre referenced from <Audio 2>, says with a warm, slightly husky voice and a quick, firm pace, <d>[Chinese] 会，每天都来。</d> He closes his lips. The camera holds a static shot at eye level. <Subject 1> listens with her mouth closed at the left edge of the frame, her hands tightening on the bag strap. In the final second both characters settle and hold their poses, breathing, hair moving gently in the wind, while the framing stays put. The video ends with <Subject 2> in close-up just right of center, hand lowered, a small smile; <Subject 1> at the left edge of the frame by the fence. Speak only the quoted dialogue lines. Those are the only words.

overall_soundscape:
Evening wind across the rooftop, the chain-link fence rattling softly, a school bag strap creaking in tight hands, distant cicadas, a faraway train passing below the town.

non_diegetic_music:
A soft solo piano plays a slow arpeggio in a major key, joined by light strings on the second line, gentle dynamics throughout.
```

lint：`--seconds 10 --images 3 --audios 2` → PASS，0 error / 0 warning；425 词；台词 12 字。

## 该类型禁忌

- 真人照片与动画图混作参考；同一集一会儿赛璐璐一会儿厚涂。
- 让模型画招牌、黑板上的字（后期叠）。
- LoRA 的独立触发 token 写进有台词的段（`camera-and-performance.md` §5c；描述性风格句不受此限）；把 4 步 Turbo 结果当有运镜镜头的定稿。
