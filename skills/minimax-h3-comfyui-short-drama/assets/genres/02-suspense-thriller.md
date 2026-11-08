# 类型包 · 悬疑惊悚

> 信息控制型类型：观众比角色知道得多或少。H3 擅长「状态」与氛围光，不擅长「过程」与精确时点，分镜按此设计。

## 适用与 H3 强弱项

- **强**：低调光 + 实用光源 + 空气介质（雾、灰尘、百叶光）的氛围层；插入镜（手、道具）给信息（egguy886 插入镜头规则）；「状态先行」写法稳定——`the key already rests in her palm`（egguy886「H3 擅长状态，不擅长过程」）。
- **弱**：揭示时点不准——一颗生成内切点整体后移约 1.2 s、跨切点曝光跳约 45%（phileiny，`prompt-format.md` §2）；推断词 `realizes / seems / as if` 画不出（egguy886 lint）；暗场景切点检测不可信（egguy886 qc）；关键证物没参考图一定被编（skill 铁律 6）。
- **绕法**：揭示用「扫过 → 切 → 结果」；瞬时效果绑在动作完成那一刻；证物单独白底图并 `the exact item shown in <Picture N>`；离开再返回的状态变化用「实际末帧 + 显式状态图」（Filmworkbench K3，`11-fresh-repos`）。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | Ref2VA 六段式（角色 + 场景 + 证物）；钩子特写走 I2VA |
| 段长 / 镜数 | 8–12 s，2–3 镜：环境/动作 → 证物插入 → 脸部反应 |
| 步数 | 草稿 Turbo 8 步 shift 12/3；推镜段定稿 20 步关 Turbo；暗部噪点重的段走二采 σ 0.45（`quality-pipeline.md`） |
| 首帧 | 真人主角对白镜建议垫首帧（同都市对白包）；纯氛围段可直出 |
| LoRA | 无；要「更冷」用 ComfyUI-Dials 而不是文字（`lora-and-style.md` §6） |

## 风格句

`Live-action, cinematic, photoreal, low-key lighting, shot on a 35mm spherical lens, shallow depth of field, a single practical lamp as the hard key light, thin moonlight through blinds in parallel stripes, a faint haze of dust in the beam, a palette of bottle green, walnut brown and cold blue, subtle film grain, restrained acting.`

色板可换 egguy886 预设 B `baroque_urban_revenge`（酒红/橄榄绿/胡桃木，光比 3:1，暴力瞬间 8:1）用于豪门悬疑复仇（`14_导演风格统一与视觉宪法`）。

## 镜头与运镜要点

- 开场全景必须动（固定全景首秒动作量 2.9 vs 推/跟 19.6，egguy886），慢推从前景遮挡物后进入。
- 证物插入镜 Static、俯拍或微距，道具状态单独成句写在镜头第一句。
- 反应镜四分之三正面近景，侧脸近景 ≤ 2 s（`camera-and-performance.md` §5c）。

## 表演与台词要点

- 「强者静、弱者忙」：越近景动作越少，只留眼睛与下颌（egguy886 表演规则）。
- 台词短、气声：`hushed, breathy voice`；内心独白用画外音 + `while her lips remain completely closed`，VO 每 15 s ≤ 20 字、不复述画面。
- 没说出口写抿唇、吞咽、视线落到物件上，不写 `as if about to speak`。

## 声音

具体声源链：抽屉滑轨、灯丝嘶声、金属轻响；配乐只写乐器（低音大提琴长音、预制钢琴单音落在插入镜），不写 tense / eerie（lint A8）。画外敲门 / 脚步只进 soundscape——声音词会把镜头拉过去（fuzzballb，`11-fresh-repos`）。

## 参考素材准备

角色板 1 张、无人场景母版 1 张（门窗开闭态写清）、每件证物白底图 1 张；证物「被发现前 / 后」不同状态各做一张，只接给对应镜头（phileiny 道具规则）。

## 示例提示词（Ref2VA，10 s，3 图 + 1 音频）

接线：`<Picture 1>` 苏婉 → `<Picture 2>` 书房 → `<Picture 3>` 铜钥匙 → `<Audio 1>` 苏婉音色。

```text
subject_definitions: <Subject 1> is Su Wan, a woman in her mid-thirties with a long angular face, dark hair pulled into a low bun, thin dark eyebrows, a fitted dark green turtleneck sweater and a slim gold chain bracelet on her right wrist, defined by <Picture 1>. <Picture 2> is the study environment: a narrow home study at night with a dark walnut desk against the left wall, one green-shaded brass desk lamp as the only practical light, tall bookshelves behind, and a window with half-closed blinds on the right. <Subject 2> is the brass key, the exact item shown in <Picture 3>: a small worn brass key with a frayed red string tag. <Audio 1> is the voice-timbre reference for <Subject 1> (S1).

summary: [reference generation + audio reference] Late at night Su Wan opens the bottom drawer of her desk, finds a brass key that went missing years ago, and whispers to herself; three shots, 10 seconds, 16:9.

retention_analysis: <Picture 1>: fully_preserved - facial identity, hairstyle, turtleneck color and bracelet; no other garment is substituted; its background is ignored. <Picture 2>: partially_preserved - desk position, lamp, shelves, blinds and light direction; the camera may move; never transfer facial traits from <Picture 2>. <Picture 3>: fully_preserved - shape, color, wear and the red string tag of the key; no other item is substituted. <Audio 1>: attribute_transfer - voice timbre only; every spoken word comes solely from the quoted dialogue line.

detailed_description: Live-action, cinematic, photoreal, low-key lighting, shot on a 35mm spherical lens, shallow depth of field, a single green-shaded desk lamp as the hard key light from frame left, thin blue moonlight cutting through the blinds in parallel stripes, a faint haze of dust in the lamp beam, a palette of bottle green, walnut brown and cold blue, subtle film grain, restrained acting. The setting is the study in <Picture 2>; the window blinds stay half closed throughout. Exactly one person is present. [Shot 1] A medium wide shot from behind the bookshelf corner, a dark shelf edge soft in the right foreground: <Subject 1>, the woman with the low dark bun and the dark green turtleneck, is already crouched beside the walnut desk with her right hand gripping the handle of the bottom drawer; she pulls the drawer open in one steady motion, the lamp light spilling into it, and her hand stops as her eyes fix on something inside. The camera pushes in toward her from the shelf corner with small amplitude at slow speed. Nobody else moves in the room. [Shot 2] At 00:03.400, the shot cuts to an overhead close-up insert of the open drawer: <Subject 2>, the small worn brass key with its frayed red string tag, the exact item shown in <Picture 3>, already rests in the open palm of her right hand, the gold chain bracelet visible at her wrist; her thumb slides once across the worn teeth of the key, and the stripes of moonlight lie across her fingers. The camera holds a static shot directly above her hand. [Shot 3] At 00:06.000, the shot cuts to a close-up on the face of <Subject 1> at a three-quarter angle, the lamp lighting the left half of her face and the moonlight stripes falling across the right half, her dark green collar at the bottom of the frame; she keeps her gaze lowered to the key below the frame, her jaw tightening, and with a hushed, breathy voice and a slow, uneven pace, (S1) says: <d>[Chinese] 这把钥匙，三年前就丢了。</d> The camera holds a static shot at eye level. In the final second she settles and holds the pose, breathing, while the framing stays put. The segment ends with <Subject 1> in close-up at frame center, eyes lowered toward the key, lips pressed together, the lamp glow steady on her face. Speak only the quoted dialogue line. After that nobody says anything else.

overall_soundscape: A quiet room tone, the wooden drawer sliding on dry runners, a faint metallic tick as the key shifts in her palm, the soft hiss of the desk lamp bulb, a slow inhale through the nose before the whisper, wind pressing faintly against the window glass.

non_diegetic_music: A single low cello note sustained under the whole clip at very soft volume, with a sparse prepared-piano pluck landing on the cut to the key insert, then fading out before the whisper.
```

lint：`--seconds 10 --images 3 --audios 1` → PASS，0 error / 0 warning；406 词；台词 10 字。

## 该类型禁忌

- 让模型画手机屏幕上的线索文字 / 照片上的字（后期叠，dramake 铁律）。
- 用跳吓式「同一时刻灯灭 + 巨响」堆在一个时间戳上；写「啪 / 砰」拟音（会触发爆炸视觉）。
- 写 `nothing happens` / `completely still` 营造静默（冻结整镜），改写呼吸与灯丝声。
