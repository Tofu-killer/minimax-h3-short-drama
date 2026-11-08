# 类型包 · 古装仙侠（真人古装 / 写实仙侠）

> 服化道是卖点，法术与御剑是风险点。3D 国漫路线另见 `08-3d-guoman-toon.md`。

## 适用与 H3 强弱项

- **强**：宽袖、发带、流苏随风等布料次级运动；云海、亭台、暖逆光的东方美术；古装情绪表演（社区「花园噩耗」古装表演对照，SkyNotSilent `x-2086121943615541389`；竹林武侠谜案 `x-2083132770650571041`）。
- **弱**：大特效镜头与大幅运镜（`model-and-modes.md` 已知弱项）；剑光/法阵易变成全屏光污染；跨镜服饰层数与发饰漂移；群战千军；御剑飞行这类大位移（capruokz：H3 画不出抱起/举起整个人类动作）。
- **绕法**：特效只绑在武器或接触点、写「动作到位那一刻 + 一次」（irenerachel `diagnostics.md`「特效没有来源 → 绑定到武器」）；剑、法器各自白底参考图；每镜重述服装层次（R15）；飞行写结果镜而不是过程。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | Ref2VA（角色 + 场景 + 法器）；仙门全景开场可 T2VA 试风格后 I2VA |
| 段长 / 镜数 | 文戏 8–12 s 2–3 镜；武戏转 `04-action-fight.md` |
| 步数 | 草稿 Turbo 8 步 shift 12/3；有环绕/跟拍的定稿 20 步关 Turbo；整圈环绕挂 pablodawson flf2v LoRA（`camera-and-performance.md` §2） |
| LoRA | 武术动作 LoRA（Jojocodex Wushu Action / JOKER141 Weapon Combat，`07-lora-training` 清单）**未经本 skill 实测**，同 seed 有/无盲测后再用，额外 LoRA 强度和 ≤ 1.3 |

## 风格句

`Live-action, Chinese xianxia period film, photoreal, shot on a 40mm spherical lens, warm low morning sunlight as key, cool sky bounce as fill, thin drifting cloud vapor as the air layer, a palette of jade white, pale blue and vermilion, fine film grain, wide sleeves and hair ribbons moving in a steady mountain wind, poised and restrained acting.`

（senmanx 风格总表：修仙 → 国风写实；暗黑修真 → 青蓝墨黑 + 血红高光；选定后全片不混用，`05-agent-skills` §senmanx。）

## 镜头与运镜要点

- 开场全景用侧向跟拍或弧形运镜，人物已在行进中；第二镜在动作到位的瞬间给特效；第三镜四分之三近景说话。
- 法器「入鞘 / 出鞘」是两种状态，两张图，只接给对应镜（phileiny）；手在第一格就握住法器。
- 反光金属只写材质本色；剑气写成一条细雾带 `curls once along its edge`，不写 glow / energy burst。

## 表演与台词要点

- 古风台词短而有韵：8–12 字一句；称呼不加逗号（「师父，」会停 1 s）——改写成「这一剑，我替师父还。」。
- 仪态写身体：肩沉、下颌微收、袖口滑落，不写「仙气飘飘」。

## 声音

山风、丝袖、玉石脚步、剑身轻鸣；配乐写古琴拨弦 + 箫长音、慢速弱奏；不要写 epic / dramatic（lint A8）。

## 参考素材准备

角色板（服装层次、发饰画清楚）、无人场景母版（亭台方位、日光方向）、法器白底图；合规替换提前做：血 → 金色血液 / 衣领红痕；暴力 → 格挡弹开、光点消散（senmanx，`storyboard-and-assets.md` §6）。

## 示例提示词（Ref2VA，10 s，3 图 + 1 音频）

接线：`<Picture 1>` 凌霜 → `<Picture 2>` 玉台 → `<Picture 3>` 出鞘长剑 → `<Audio 1>` 凌霜音色。

```text
subject_definitions: <Subject 1> is Ling Shuang, a young woman in her early twenties with a slender oval face, long straight black hair tied high with a white silk ribbon, dark phoenix eyes, wearing layered white and pale blue Song-style robes with wide sleeves and a silver-embroidered sash, defined by <Picture 1>. <Picture 2> is the environment: a white jade terrace on a mountain peak above a sea of clouds, a red-pillared pavilion at the far left, pine trees clinging to the cliff edge, morning sun low on the right. <Subject 2> is the jian sword, the exact item shown in <Picture 3>: a straight double-edged steel blade with a pale jade guard and a white cord tassel, drawn and bare. <Audio 1> is the voice-timbre reference for <Subject 1> (S1).

summary: [reference generation + audio reference] On a jade terrace above the clouds, Ling Shuang raises her drawn sword toward the horizon and vows to repay a debt for her master; three shots, 10 seconds, 16:9.

retention_analysis: <Picture 1>: fully_preserved - facial identity, hairstyle with white ribbon, robe layers, colors and sash; no other garment is substituted; its background is ignored. <Picture 2>: partially_preserved - terrace layout, pavilion, pines, cloud sea and sun direction; the camera may move; never transfer facial traits from <Picture 2>. <Picture 3>: fully_preserved - blade shape, jade guard and white tassel; no other item is substituted. <Audio 1>: attribute_transfer - voice timbre only; every spoken word comes solely from the quoted dialogue line.

detailed_description: Live-action, Chinese xianxia period film, photoreal, shot on a 40mm spherical lens, deep warm morning sunlight from frame right as key, cool sky bounce as fill, thin drifting cloud vapor across the terrace floor as the air layer, a palette of jade white, pale blue and vermilion, fine film grain, wide sleeves and hair ribbon moving in a steady mountain wind, poised and restrained acting. The setting is the jade terrace in <Picture 2>. Exactly one person is present. [Shot 1] A wide shot from a low angle near the terrace edge, pine needles soft in the left foreground: <Subject 1>, the young woman in layered white and pale blue robes with the high white ribbon, walks from frame left toward the cliff edge at an even pace, her right hand already holding <Subject 2>, the bare jian sword from <Picture 3>, blade angled down beside her leg, cloud vapor parting around her ankles. The camera tracks with her from the side at slow speed, keeping her at the left third of the frame. [Shot 2] At 00:03.600, the shot cuts to a medium shot from behind her left shoulder facing the sea of clouds: <Subject 1> stops at the edge and lifts the sword in one smooth arc until the blade points level at the horizon, her wide right sleeve sliding back to the elbow; the moment the blade reaches level, a thin ribbon of pale blue mist curls once along its edge and drifts off the tip into the wind. The camera arcs slowly from her shoulder to her right side with small amplitude. [Shot 3] At 00:06.400, the shot cuts to a close-up on the face of <Subject 1> at a three-quarter angle, the sun rimming her cheek and the white ribbon lifting behind her head, the jade guard of the sword visible at the lower edge of the frame; she keeps her eyes on the horizon and, with a clear, low, steady voice and a slow, measured pace, (S1) says: <d>[Chinese] 这一剑，我替师父还。</d> The camera holds a static shot at eye level. In the final second she settles and holds the pose, breathing, robes and ribbon still moving in the wind, while the framing stays put. The segment ends with <Subject 1> in close-up at frame center, sword level at the lower edge, eyes on the horizon. Speak only the quoted dialogue line. After that nobody says anything else.

overall_soundscape: Steady high-altitude wind across stone, silk sleeves snapping softly, footsteps on polished jade, a thin metallic ring as the blade lifts, distant pine branches creaking, one crane call far below the clouds.

non_diegetic_music: A solo guqin plays slow plucked phrases with long decays, joined by a low xiao flute holding one note as the blade reaches level, soft dynamics throughout.
```

lint：`--seconds 10 --images 3 --audios 1` → PASS，0 error / 0 warning；402 词；台词 8 字。

## 该类型禁忌

- 同一段里法阵 + 雷光 + 剑雨 + 御剑多重特效；`8K, epic, masterpiece` 空形容词。
- 让模型生成匾额、卷轴上的精确汉字（后期叠）。
- 写 `slow motion` 慢动作出剑（动作量 14.7 → 22.2 去掉后才正常，egguy886）。
