# 类型包 · 手作定格科普（纸艺立体 / 纸拼贴 / 手绘实拍融合）

> 官方 8 个风格 skill 里有 3 个属于这一类且都以 H3 为默认模型；适合科普、观点、品牌 B-roll，不适合对白剧情。

## 适用与 H3 强弱项

- **强**：官方 `papercraft-stop-motion-explainer`、`paper-collage-explainer-generator`、`handdrawn-live-video-generator` 均默认 MiniMax-H3；分层纸张、纤维与撕边、纸片间的物理阴影可直接从首帧继承；纸艺题材中文直写也能出片（SkyNotSilent `x-2085649264185913721` 纸艺奇幻大战）。
- **弱**：H3 天生是 24 fps 平滑运动，容易变成「数字图层平移 / 慢推漂移」而丢掉定格感（官方 paper-collage：画面像平滑数字图层时要按定格节拍重写）；画面字与 UI 会乱码；大幅旋转、翻飞、物件乱飞会崩（官方 paper-collage 禁止项的正向改写）。
- **绕法**：运动写成定格节拍「出现 → 轻弹 → 压平 → 停顿 → 锁定」（官方 paper-collage STEP 5）与「小步进、微停顿、轻回弹」（官方 papercraft）；先出静帧获批再 I2VA；后期可抽帧做「一拍二」（`fps=12` 再回 24 fps）加强定格感（本包建议，未实测）。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | I2VA 三段式：先出获批静帧作首帧（官方 paper-collage：先出静帧再动）；手绘实拍融合用单场景 15 s 16:9 |
| 段长 / 镜数 | 纸拼贴：单镜组装、机位不动；纸艺立体：8–12 s，1–2 镜；手绘实拍：单场景、0–3 s 内必须出现手绘与实物的**接触**（官方 handdrawn） |
| 步数 | FL2V 768p Turbo 8 步 shift 6/3；定格风对拖影不敏感，4 步可抽卡 |
| 声音策略 | 官方 paper-collage 默认只保留拼贴拟音，不加 BGM / 旁白 / 字幕，除非用户要 |

## 风格句

- 纸艺立体：`Handmade papercraft stop-motion, layered cut-paper diorama, visible paper fibers and torn edges, soft physical shadows between paper layers, warm top light like a desk lamp, shallow miniature depth of field, every moving piece advancing in small stepped increments with tiny pauses and slight rebounds.`
- 纸拼贴：`Editorial paper-collage stop-motion, flat bold color fields, black-and-white halftone photo cut-outs, colored cardstock accents, warm cream keylines, soft paper shadows, pieces popping in, bouncing lightly, pressing flat, pausing and locking into place.`（官方 paper-collage 视觉语言）
- 手绘实拍：`Rough glowing hand-drawn chalk-and-crayon line animation living inside a real live-action room, filmed one-handed on a phone that follows slightly late.`（官方 handdrawn）

## 镜头与运镜要点

- 纸拼贴：一镜组装到底、机位不动，结尾停在与获批静帧一致的构图（官方 paper-collage STEP 5）。
- 纸艺立体：大全景小推 → 局部特写 Static；层次纵深（前中后景纸层）每镜都写（官方 papercraft 强调分层深度）。
- 手绘实拍：一个连续变形的单体、逃逸路线、手持镜头延迟跟随；保持非恐怖调性（官方 handdrawn）。

## 表演与台词要点

- 纸角色动作写铰链关节、推拉片、转盘、翻卡表情（官方 papercraft）；不做大幅人物表演。
- 旁白后期配；若必须生成旁白，用画外音并写 `while … lips remain completely closed`，每 15 s ≤ 20 字。

## 声音

纸张滑动、轻「啵」声、压平轻叩、纸屑沙沙、细小折痕声，与纸片动作同步；`non_diegetic_music: N/A`。拟音不写「啪 / 砰」。

## 参考素材准备

获批的首帧静图（与成片同画幅，纸层、色板、底色定死——官方：开场底色与静帧不一致要重出）；每个纸角色一张正面设定；避免牛皮纸底色 / 发黄底，除非批准。

## 示例提示词（I2VA，10 s，1 图首帧，0 音频）

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Handmade papercraft stop-motion, layered cut-paper diorama, visible paper fibers and torn edges, soft physical shadows between paper layers, warm top light like a desk lamp from frame left, shallow miniature depth of field, a palette of ocean teal, cloud white, sun yellow and kraft brown, every moving piece advancing in small stepped increments with tiny pauses and slight rebounds. The opening frame shown in <Picture 1> is preserved: a pop-up paper diorama of the water cycle, a teal cut-paper sea with three layered wave strips at the bottom, a yellow paper sun disc on a pin at the upper left, a brown cardboard mountain on the right, and an empty pale blue paper sky. The yellow sun disc rotates on its pin in stepped quarter turns; with each step, a small white paper curl peels upward from the top wave strip and slides up into the sky on a thin visible wire, and the three curls press together into one puffy white paper cloud above the mountain. The camera pushes in toward the cloud with small amplitude at slow speed. [Shot 2] At 00:05.500, the shot cuts to a close-up of the paper cloud above the cardboard mountain: the cloud darkens as a grey paper layer slides over it from behind, then thin blue paper raindrop strips drop from its underside one row at a time in stepped jumps, bounce once on the mountain slope and settle, and a narrow blue paper river unfolds down the mountain toward the sea. The camera holds a static shot. In the final second every paper piece settles and holds its position while the framing stays put. Nobody speaks.

overall_soundscape: Soft paper sliding against paper, a tiny pin squeak as the sun disc turns, crisp light paper pops as the curls lift, gentle taps as raindrop strips land on cardboard, a soft fold-and-crease sound as the river unfolds.

non_diegetic_music: N/A
```

lint：`--seconds 10 --images 1 --audios 0 --mode i2va` → PASS，0 error / 0 warning；正文 277 词。

## 该类型禁忌

- 平滑慢推、慢变焦、数字图层漂移、快速旋转、物件乱飞（官方 paper-collage 列为失败模式）。
- 让模型生成科普标签文字、箭头说明（后期叠）。
- 手绘实拍做成恐怖跳吓或毛绒玩偶（官方 handdrawn 边界）。
