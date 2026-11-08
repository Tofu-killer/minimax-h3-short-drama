# 类型包 · 产品广告 / 品牌宣传

> 纯产品片是 H3 官方默认场景；真人带货口播戏是弱项（转 `12-talking-head-digital-human.md` 并先出首帧）。

## 适用与 H3 强弱项

- **强**：官方极简产品广告 skill 默认 H3——「更干净的 Apple 式产品特写、留白与高级产品片运镜」（官方 `minimalist-product-ad-generator`）；同提示词商业广告对比，H3 更自然精致、Seedance 更强调视觉冲击（SkyNotSilent `x-pollo-commercial-comparison`）；原生音频可直接出品牌向器乐与 UI 音效（官方 `brand-promo-video-generator` STEP 8）。
- **弱**：真人带货戏垫首帧后仍输 Seedance（garycaogan）；Logo、包装字、中文文案会被近似重绘（官方 brand-promo：不得重绘 logo / 包装；guangjun5952：中文排版错字）；拼贴成一张的锚点板会被模型照搬版式（官方 minimalist：不再默认 4 宫格锚点板）。
- **绕法**：三张**独立**锚点照（主视角 / 材质细节 / 终帧构图）作参考；画面内只出一行 3–5 个英文词的文案，失败就减少文案次数或改后期叠；Logo / 中文 / 法律文字 / 价格用确定性工具后期合成。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | Ref2VA（产品锚点 3 张，产品是 `<Subject 1>`）；产品镜头可以挂背景 / 终帧构图板（锁环境的产品镜头才挂，loopforge0） |
| 段长 / 节拍 | 官方：5 s 3–4 拍、10 s 5–7 拍、15 s 6–9 拍；节拍 ≠ 切镜，10 s 内 3 镜、每镜 2–3 拍；15 s 品牌片模式「钩子 → 需求 → 机制 → 场景 → 证明 → 回报 → logo + CTA」（官方 brand-promo STEP 5） |
| 步数 | Turbo 8 步 shift 12/3 草稿；微距跟拍、升降镜定稿 20 步；写实材质 A/B 可试 PDD 8 步替换 Turbo |
| 音频 | 默认 H3 原生音频写品牌安全器乐；不满意再单独配乐替换（官方 minimalist STEP 8–10） |

## 风格句

`Minimalist premium product film, photoreal, clean studio look, shot on a 100mm macro lens and an 85mm lens, one large soft key light from frame left, a thin hard rim light from behind tracing the product edge, a seamless warm-white background, restrained elegant motion, crisp focus on product surfaces.`

暗调变体：`dark rim-light style, deep charcoal background, a single hard rim tracing the silhouette`（官方白色科技 / 暗调轮廓光 / 品牌色场三模板）。

## 镜头与运镜要点

- 开场不留空镜：第一秒就给产品真实结构动作（开盖、旋转、滑出），动作从产品形态推断（官方 minimalist）。
- 每拍一个主动作，次要元素晚半拍；转场靠产品边缘高光、开合动作、同向运动，不靠白闪与随机粒子（官方 STEP 4）。
- 终镜：整帧单一产品 + 一行文案稳定停留；不要以分屏 / 网格 / 锚点板收尾。

## 表演与台词要点

- 无人产品片写 `Nobody speaks.`；需要旁白时用画外音 + 后期 TTS，不让产品片里出现嘴。
- 有人出镜的生活方式片：一镜一个使用动作，手在第一格已接触产品；人物脸用首帧锁。

## 声音

具体产品声：金属旋盖滑动、开盖气声、蒸汽嘶声、放置轻叩；配乐写慢速极简电子 + 毛毡钢琴 + 文案出现时一声轻铃。

## 参考素材准备

用户授权的产品原图 → 三张独立锚点照（与成片同画幅同分辨率、统一光与背景，**不拼成一张**）；产品颜色永不改色，Apple 式只改背景与光（官方 minimalist）；记录素材来源清单（官方 brand-promo provenance manifest）。

## 示例提示词（Ref2VA，10 s，3 图，0 音频）

接线：`<Picture 1>` 主视角 → `<Picture 2>` 材质细节 → `<Picture 3>` 终帧构图。

```text
subject_definitions: <Subject 1> is the thermos bottle, the exact item shown in <Picture 1> and <Picture 2>: a tall matte sage-green stainless-steel vacuum bottle with a brushed silver screw cap and a thin silver ring at the shoulder. <Picture 1> is the hero product view. <Picture 2> is the material detail view of the brushed cap and the matte powder-coated body. <Picture 3> is the final composition anchor: the bottle standing on a low warm-white plinth against a seamless warm-white background, placed at the right third of the frame with open negative space on the left.

summary: [reference generation] A minimalist premium product film for a sage-green thermos bottle: macro detail of the cap opening, a slow reveal of the full bottle with rising steam, and a final hero composition with one line of copy; three shots, 10 seconds, 16:9.

retention_analysis: <Picture 1>: fully_preserved - bottle silhouette, proportions, sage-green matte color, cap and shoulder ring; no other item is substituted. <Picture 2>: fully_preserved - brushed metal grain of the cap and the matte powder-coat texture; no other item is substituted. <Picture 3>: partially_preserved - plinth, background color, product placement and negative space for the final shot; the camera may move before the final shot.

detailed_description: Minimalist premium product film, photoreal, clean studio look, shot on a 100mm macro lens and an 85mm lens, one large soft key light from frame left, a thin hard rim light from behind tracing the edge of the bottle, a seamless warm-white background, a palette of warm white, sage green and brushed silver, restrained elegant motion, crisp focus on product surfaces. Exactly one product is present, and it is always <Subject 1>, keeping the sage-green body color from <Picture 1> in every frame. [Shot 1] An extreme macro close-up on the brushed silver screw cap of <Subject 1>, matching the material detail of <Picture 2>: the cap is already lifted a few millimetres and rotates a quarter turn counterclockwise, the brushed metal grain catching a slow-moving rim highlight that slides across its edge, then the cap lifts clear out of the frame upward and a soft thread of white steam rises from the open mouth. The camera tracks slowly along the rim of the cap from left to right. [Shot 2] At 00:03.600, the shot cuts to a medium shot from a low angle: <Subject 1> stands upright on the warm-white plinth with its cap set beside it, the thread of steam curling up from the open mouth into the light, the matte sage-green body showing its fine powder-coat texture as the rim highlight travels from the base up to the silver shoulder ring. The camera pedestals up from the base to the shoulder ring at slow speed, with the horizon kept level. [Shot 3] At 00:06.800, the shot cuts to the final hero composition matching <Picture 3>: <Subject 1> stands at the right third of the frame on the plinth with the cap screwed back on, steam fading, wide warm-white negative space on the left. At 00:07.800 a single line of English copy in SF Pro Display Semibold fades in at the vertical center of the left negative space, left-aligned, reading "Warm Hours, Every Day", the words "Warm Hours," in dark grey and "Every Day" in sage green, the whole line sliding a few pixels to the right as it settles and then holding steady to the end. The camera holds a static shot. In the final second the bottle, the light and the copy hold their positions while the framing stays put. Nobody speaks.

overall_soundscape: A soft metallic glide as the screw cap turns, a light airy release as the cap lifts, a faint hiss of steam, a gentle low tap as the cap is set on the plinth, quiet studio room tone.

non_diegetic_music: A minimal electronic track at a slow tempo with soft felt-piano notes over a warm sub pulse, a light chime landing as the copy line appears, fading out with the final hold.
```

lint：`--seconds 10 --images 3 --audios 0` → PASS，0 error / 0 warning；386 词。画面文案若出现错字：同 seed 去掉文案句重出，文案后期叠。

## 该类型禁忌

- 没有授权素材就「画一个差不多的 logo / 包装」；编造功效数据、假 HUD、玻璃卡片、文字墙（官方 brand-promo STEP 6）。
- 镜面地板、玻璃台面的廉价反射棚；把产品改成白色或银色「显高级」。
- 同屏两行文案、标题 + 副标题；文案放在下方字幕位。
