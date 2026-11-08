# 类型包 · 科幻 / 赛博朋克

> 霓虹、湿地反光、机械义体是 H3 的强项；全息 UI、精确屏幕文字、大规模舰队战是弱项。

## 适用与 H3 强弱项

- **强**：霓虹双色光 + 雨夜湿面反光 + 蒸汽的氛围层（open-h3-ir README 编译样例：雨夜金属栈桥、冷蓝反光，`04-prompting-tools` 案例 3）；硬表面道具（义肢、数据卡）在有参考图时稳定；氛围合成器乐原生生成。
- **弱**：游戏 / 全息 UI「能出字但不稳定」（SkyNotSilent `x-hyperboleon-2086457102474887641`）；大特效与大幅运镜（`model-and-modes.md` 已知弱项）；跨镜舰船位置连续性（`x-ai_emeraldapple-2086542941112487981` 太空战对照的观察点）。
- **绕法**：UI、屏幕字、霓虹招牌文字一律后期叠（dramake 铁律），画面里只写抽象霓虹灯管；太空 / 舰队用单一主体 + 结果镜；赛博与蒸汽朋克等相邻类型元素写进「本剧不是什么」清单后只保留一种（egguy886 `what_this_is_not`）。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | Ref2VA（角色 + 场景 + 科技道具）；纯环境 / 飞船外景先 T2VA 试风格再 I2VA |
| 段长 / 镜数 | 8–12 s，2–3 镜：运动开场 → 道具插入 → 对白近景 |
| 步数 | Turbo 8 步 shift 12/3；有升降 / 跟拍的定稿 20 步关 Turbo；Ref2VA 只在必须锁小巷布局时挂场景板（场景板让运镜减半，loopforge0） |
| LoRA | 无专用；运镜不足可试 Jojocodex Camera Motion（默认不挂） |

## 风格句

`Live-action, cyberpunk science fiction, photoreal, shot on a 35mm anamorphic lens, shallow depth of field, pink neon key light from frame left and cyan neon rim from frame right, wet asphalt mirroring both colors, steady rain and drifting steam as the air layer, a palette of magenta, cyan and wet black, fine film grain, cool and controlled acting.`

冷硬变体：egguy886 预设 C `neon_ritual_thriller`（crimson red vs cold steel blue 硬边二分，光比 8:1–12:1，大面积死黑）。senmanx 风格总表：科幻 → 赛博 2077。

## 镜头与运镜要点

- 开场用 `pedestals down` 或 `tracks` 从霓虹 / 线缆下降到人物，人物已在行走中（开场全景要动）。
- 义肢 / 道具插入镜 Static，写机械动作的具体次数（`rotates it once end over end`）。
- 镜头 / 机身型号是装饰；要宽就写宽景别（swan7）。

## 表演与台词要点

- 冷峻角色少动作：一个转头、一次握拳；台词短、平、沙哑。
- 对画外人说话写 `looks off toward frame right at someone out of frame`，不额外生成第二个人物。

## 声音

雨打金属雨棚、霓虹灯管电流声、伺服电机轻响、蒸汽嘶声；配乐写模拟合成器低音脉冲 + 琶音，不写 futuristic / cinematic。

## 参考素材准备

角色板（义体结构画清楚，左右手别画反）、无人小巷母版（霓虹只用抽象灯管形状，不带文字）、科技道具白底图（哑光材质，零自发光）；所有参考图同为写实或同为 3D，不混用。

## 示例提示词（Ref2VA，10 s，3 图 + 1 音频）

接线：`<Picture 1>` Kite → `<Picture 2>` 小巷 → `<Picture 3>` 数据卡 → `<Audio 1>` Kite 音色。

```text
subject_definitions: <Subject 1> is Kite, a courier woman in her late twenties with a sharp narrow face, an asymmetric silver-dyed undercut, dark eyes, a matte black cybernetic left arm with visible steel joints, wearing a cropped olive bomber jacket over a black high-neck top and black cargo trousers, defined by <Picture 1>. <Picture 2> is the environment: a narrow rain-soaked back alley at night lined with stacked air-conditioning units, tangled cables overhead, pink and cyan neon tubes in abstract shapes on both walls, and steam rising from a floor grate. <Subject 2> is the data cartridge, the exact item shown in <Picture 3>: a palm-sized matte black rectangular cartridge with a single cyan painted stripe. <Audio 1> is the voice-timbre reference for <Subject 1> (S1).

summary: [reference generation + audio reference] In a neon back alley in the rain, the courier Kite walks in, turns a data cartridge in her cybernetic hand and demands payment from someone off-screen; three shots, 10 seconds, 16:9.

retention_analysis: <Picture 1>: fully_preserved - facial identity, silver undercut, cybernetic left arm, bomber jacket and trousers; no other garment is substituted; its background is ignored. <Picture 2>: partially_preserved - alley layout, cables, neon colors and steam grate; the camera may move; never transfer facial traits from <Picture 2>. <Picture 3>: fully_preserved - shape, matte black finish and the cyan stripe; no other item is substituted. <Audio 1>: attribute_transfer - voice timbre only; every spoken word comes solely from the quoted dialogue line.

detailed_description: Live-action, cyberpunk science fiction, photoreal, shot on a 35mm anamorphic lens, shallow depth of field, pink neon key light from frame left and cyan neon rim from frame right, wet asphalt mirroring both colors, steady rain and drifting grate steam as the air layer, a palette of magenta, cyan and wet black, fine film grain, cool and controlled acting. The setting is the alley in <Picture 2>. Exactly one person is visible. [Shot 1] A high wide shot looking down the alley past the hanging cables: <Subject 1>, the courier with the silver undercut and the cropped olive bomber jacket, walks toward the camera through the steam at a steady pace, rain beading on her matte black cybernetic left arm, her boots splashing through shallow puddles, the collar of the olive jacket turned up against the rain and her right hand tucked into its pocket, neon reflections sliding across the wet ground at her feet. The camera pedestals down from the cables to her eye level as she approaches, with the horizon kept level. [Shot 2] At 00:04.000, the shot cuts to a close-up insert at chest height: the steel fingers of her cybernetic left hand already hold <Subject 2>, the matte black cartridge with the single cyan stripe, the exact item shown in <Picture 3>; the fingers rotate it once end over end with precise mechanical clicks, then close around it. The camera holds a static shot. [Shot 3] At 00:06.400, the shot cuts to a medium close-up on <Subject 1> at a three-quarter angle, pink light on the left side of her face and cyan rim on her silver hair, the olive collar of the bomber jacket at the bottom of the frame; she looks off toward frame right at someone out of frame and, with a flat, husky voice and a clipped, unhurried pace, (S1) says: <d>[Chinese] 货送到了，钱呢？</d> The camera holds a static shot at eye level. In the final second she settles and holds the pose, breathing, rain still falling, while the framing stays put. The segment ends with <Subject 1> in medium close-up at frame center, eyes toward frame right, the cartridge closed inside her mechanical fist at the lower edge of the frame. Speak only the quoted dialogue line. After that nobody says anything else.

overall_soundscape: Dense rain on metal awnings, the hum and buzz of neon tubes, boots splashing in shallow puddles, steam hissing from the floor grate, small precise servo clicks from the mechanical fingers, distant air-conditioner fans rattling.

non_diegetic_music: A slow analog synth bass pulse at a low tempo with a soft arpeggiated synth line, swelling slightly on the cartridge insert and dropping to the bass alone under the line.
```

lint：`--seconds 10 --images 3 --audios 1` → PASS，0 error / 0 warning；381 词；台词 6 字。

## 该类型禁忌

- `holographic interface displaying "ACCESS GRANTED"` 等让模型写字的界面；一段里叠全息 + 激光 + 爆炸。
- 道具写 glowing / emits light（反光道具只写材质本色）。
- 赛博霓虹与蒸汽朋克黄铜、废土锈蚀混搭在同一集。
