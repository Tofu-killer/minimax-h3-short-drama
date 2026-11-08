# 类型包 · 恐怖

> 氛围与「门后有什么」比怪物本身好做。H3 没有负向分支，恐怖元素必须正向写出来，不能靠「不要露脸」暗示。

## 适用与 H3 强弱项

- **强**：单光源（手电、走廊绿光）+ 浓重阴影 + 颗粒的视觉；拾得式手持（found-footage）质感（SkyNotSilent `x-2084842607411335284` 渔船拾得式恐怖）；环境声细节（铰链、滴水、呼吸）原生同步。
- **弱**：jump scare 的精确时点（切点后移约 1.2 s，phileiny）；暗部噪点与跨切点曝光跳变；暗场景切点检测不可信（egguy886 qc）；怪物/鬼魂只靠文字每次都不一样；血腥内容受平台限制。
- **绕法**：惊吓事件绑在「动作完成的那一刻」并写 `exactly once`；首帧（I2VA）锁定光位与构图；怪物做参考图；揭示用「部分可见」（头发垂下、手扶门框）而不是全身；可选 80 年代恐怖风格 LoRA。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | I2VA 三段式（首帧锁暗场构图）；有固定怪物/鬼角色时 Ref2VA + 怪物参考图 |
| 段长 / 镜数 | 8–12 s，3 镜：缓慢接近 → 脸部反应 → 揭示（POV）；揭示后留 ≥ 1 s |
| 步数 | FL2V 768p Turbo 8 步 shift 6/3 草稿；定稿 20 步；暗部噪点用二采 σ 0.45 精修，不用重生成式高 σ |
| LoRA | `wassermanproductions/wasserman-80s-horror-lora`：触发词 `80s_horror_wk` 放提示词开头，再接 `shot on VHS.` 或 `shot on 16mm film.`；官方说明标准文本编码器可用、保留对白与音频；**LoRA 触发词不进有台词的段**（`camera-and-performance.md` §5c），I2VA 首行对齐指令仍在最前 |

## 风格句

`Live-action, horror film, photoreal, shot on a 24mm lens, the only light is a handheld flashlight beam plus a dim green exit glow, deep shadows filling the frame edges, thin dust floating in the beam as the air layer, a palette of sickly green, flashlight white and black, heavy film grain.`

## 镜头与运镜要点

- 接近段：主体背后手持跟拍 `shaking slightly`；反应段：正面低位光源近景 Static；揭示段：POV。
- 门、窗的开闭态写进首帧描述并在揭示时写 `swings fully open exactly once`（forest-laoli 空间层）。
- 人物不穿门洞（alpha 融化，forest-laoli）；揭示物停在门框处。

## 表演与台词要点

- 恐惧写生理：屏息、汗珠、嘴唇抿紧、手指贴墙；不写 `terrified`。
- 尖叫慎用：一镜一声且绑在揭示后；多数段 `Nobody speaks.`，喘息进 soundscape。

## 声音

底噪 + 小声源（鞋底、墙纸摩擦、铰链长音、滴水）；配乐写低音提琴长音、弓擦镲片渐强、在铰链声处切静音；不写 eerie / creepy（lint A8）。声音词会把镜头拉向声源（fuzzballb），画外声源只放 soundscape。

## 参考素材准备

首帧（暗场，但主体轮廓与光斑清晰；太黑的首帧会整段发灰）；固定怪物做三视图；场景母版写清门窗状态。合规：血 → 黑色水渍 / 红痕；肢体伤害改结果暗示。

## 示例提示词（I2VA，10 s，1 图首帧，0 音频）

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, horror film, photoreal, shot on a 24mm lens, the only light is a handheld flashlight beam plus a dim green exit glow at the far end, deep shadows filling the frame edges, thin dust floating in the beam as the air layer, a palette of sickly green, flashlight white and black, heavy film grain. The opening frame shown in <Picture 1> is preserved: a narrow apartment hallway at night, peeling beige wallpaper, a woman in a grey hoodie with a messy dark ponytail seen from behind, holding the flashlight in her right hand; the white bathroom door at the end of the hallway stands open a hand's width. Exactly one person is visible. She walks slowly down the hallway, the beam trembling across the wallpaper, her free left hand trailing along the wall. The camera tracks behind her at her pace in handheld, shaking slightly. [Shot 2] At 00:04.000, the shot cuts to a close-up on her face from the front, lit from below by the flashlight, the dark ponytail and grey hood framing it; she stops, holds her breath, her eyes fixed past the camera on the bathroom door, a bead of sweat running from her temple, her lips pressed tight. The camera holds a static shot. [Shot 3] At 00:07.000, the shot cuts to her point of view down the hallway, the flashlight beam resting on the bathroom door: the door swings fully open exactly once, the instant her held breath escapes, revealing a dark bathroom where long wet black hair hangs over the top edge of the open door from the other side, dripping water onto the tiles. The camera holds the point of view, shaking slightly with her hand. In the final second the beam and the door hold their positions while the framing stays put. Nobody speaks.

overall_soundscape: A low building hum, soft sneaker steps on old carpet, fingertips brushing dry wallpaper, a held breath and then a shaky exhale, a long rusty hinge creak as the door swings, slow water drops hitting bathroom tiles.

non_diegetic_music: A low sustained contrabass note at very soft volume, a high bowed-cymbal tone rising slowly through the close-up, cut to silence on the door creak.
```

lint：`--seconds 10 --images 1 --audios 0 --mode i2va` → PASS，0 error / 0 warning；正文 305 词（三段式约 时长 × 25–30 词）。

## 该类型禁忌

- `no face visible`、`nobody is there` 之类否定（会画出脸 / 人）；要排除光晕用 NegPiP `(red glow:-3)`。
- 一个时间戳上同时安排灯灭 + 巨响 + 人影；一段里多次 jump scare。
- 「啪 / 砰」拟音；血浆、断肢特写；`8K ultra-realistic` 空形容词。
