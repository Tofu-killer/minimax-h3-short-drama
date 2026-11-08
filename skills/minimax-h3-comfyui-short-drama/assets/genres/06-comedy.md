# 类型包 · 喜剧（情景喜剧 / 对白梗 / 轻肢体）

> 语言梗与反应镜是 H3 的舒适区；大幅 slapstick（摔、追、弹性形变）是短板。

## 适用与 H3 强弱项

- **强**：一句铺垫 + 一句反转的对白梗，口型与语气原生；正反打节奏（2D 间谍喜剧案例一镜一人一句、约 2 s 一镜，`04-prompting-tools` 案例 4）；脱口秀节奏写法可用（案例 6：铺垫后停顿、笑点后才有反应）。
- **弱**：弹性夸张表演、追逐与摔跤类 slapstick——官方 3D skill 指定这类镜头回退 Seedance 2.0（官方 `3d-animation-short-generator/references/model-selection.md`）；喜剧时点被「切点后移 1.2 s」吃掉；观众笑声写进 soundscape 会把观众画进画面（mathruffian：soundscape 不写 crowd）。
- **绕法**：笑点交给台词 + 反应镜（金句后留 0.3–0.8 s 无台词反应，JGRFW）；复杂肢体喜剧写成状态机：起始姿态 → 动作 → 结束态 = 下一动作起始态，并给手脚、道具起永久身份（LoveRain1997 案例 013 动作链喜剧）；罐头笑声后期加。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | Ref2VA（两人 + 梗道具）；单人吐槽 / 脱口秀走 `12-talking-head-digital-human.md` |
| 段长 / 镜数 | 8–12 s，3 镜：铺垫句 → 反转句 → 无台词反应镜（反应镜 ≥ 2.5 s 含 1 s 收尾） |
| 台词 | 铺垫 ≤ 12 字、反转 ≤ 12 字；反转句慢档（< 3.5 字/s） |
| 步数 | Turbo 8 步 shift 12/3 草稿，2–3 seed 选笑点节奏最好的那条；真人主角垫首帧 |
| LoRA | 无 |

## 风格句

`Live-action, bright sitcom look, photoreal, shot on a 35mm lens with a medium depth of field, soft even daylight from a large window, warm fill from the ceiling, a palette of butter yellow, white tile and navy, clean and evenly exposed, broad but grounded comic acting.`

2D 动画喜剧换 `../style-manga.md` 风格句 + 「表情符号式」夸张：`eyes widen into round white circles, sweat drop`（`storyboard-and-assets.md` §6）。

## 镜头与运镜要点

- 铺垫镜可慢推；反转句镜头 Static，给对方面无表情的近景；反应镜回切铺垫者，景别与铺垫镜一致（双人反打的「回接」）。
- 笑点期间不切镜（案例 6：Never cut during a punchline 的正向写法——反转句整镜 Static 并说完）。
- 一段 ≤ 1 次转身；不写 wink / raise eyebrow（强制切脸特写，`camera-and-performance.md` §5c）。

## 表演与台词要点

- 「表情落差」写成两拍：`his proud grin stays fixed for one beat, then sags at the corners`。
- deadpan 写身体：推眼镜、停顿一个整拍、视线下移再上抬。
- 台词不经 LLM 改写——谐音梗一改就没了；验收用 whisper 逐字比对（egguy886 qc）。

## 声音

具体小声：托盘磕台面、焦边嘶声、推眼镜轻响、泄气叹息；`non_diegetic_music: N/A`，喜剧音效（咚、滑稽木琴）与罐头笑声后期按剪辑点加。

## 参考素材准备

两人角色板（服装颜色反差大，便于辨认）、梗道具白底图（烤糊的蛋糕必须有图，否则会被画成正常蛋糕）、两人各一段音色（同性别时声学画像反着写）。

## 示例提示词（Ref2VA，10 s，3 图 + 2 音频）

接线：`<Picture 1>` 大壮 → `<Picture 2>` 小美 → `<Picture 3>` 烤糊的蛋糕 → `<Audio 1>` 大壮 → `<Audio 2>` 小美。

```text
subject_definitions: <Subject 1> is Da Zhuang, a chubby man in his early thirties with a round face, short spiky black hair, thick eyebrows, wearing a yellow apron with a cartoon chicken print over a navy T-shirt, defined by <Picture 1>. <Subject 2> is Mei, a woman in her early thirties with a sharp heart-shaped face, a short black bob, rectangular black glasses, wearing a grey office blazer over a white blouse, defined by <Picture 2>. <Subject 3> is the burnt cake, the exact item shown in <Picture 3>: a round two-layer cake with charred black edges and lopsided white frosting on a silver tray. <Audio 1> is the voice-timbre reference for <Subject 1> (S1). <Audio 2> is the voice-timbre reference for <Subject 2> (S2).

summary: [reference generation + audio reference] In a bright home kitchen, Da Zhuang proudly presents a burnt birthday cake and Mei answers with one deadpan line, followed by his reaction; three shots, 10 seconds, 16:9.

retention_analysis: <Picture 1>: fully_preserved - facial identity, spiky hair, apron print and T-shirt color; no other garment is substituted; its background is ignored. <Picture 2>: fully_preserved - facial identity, bob haircut, glasses, blazer and blouse; no other garment is substituted; never transfer facial traits from <Picture 2> onto <Subject 1>. <Picture 3>: fully_preserved - the charred edges, lopsided frosting and silver tray; no other item is substituted. <Audio 1>: attribute_transfer - voice timbre only for <Subject 1>. <Audio 2>: attribute_transfer - voice timbre only for <Subject 2>.

detailed_description: Live-action, bright sitcom look, photoreal, shot on a 35mm lens with a medium depth of field, soft even daylight from a large window on the left, warm fill from the ceiling, a palette of butter yellow, white tile and navy, clean and evenly exposed, broad but grounded comic acting. A small home kitchen with white tiles, a window on the left and a fridge on the right. Exactly two people are present: <Subject 1> stands behind the kitchen island at frame center; <Subject 2> stands at frame right near the fridge, facing him. [Shot 1] A medium shot of <Subject 1>, the chubby man with spiky black hair in the yellow chicken-print apron, already holding <Subject 3>, the burnt cake on its silver tray, with both hands at chest height; a thin curl of grey smoke rises from its charred edge. He lifts the tray a little higher, beaming with his chin up, and with a loud, bright voice and a quick, eager pace, (S1) says: <d>[Chinese] 生日快乐，我亲手烤的！</d> The camera pushes in toward him with small amplitude at slow speed. <Subject 2> listens with her mouth closed, out of focus at the right edge of the frame. [Shot 2] At 00:04.000, the shot cuts to a medium close-up on <Subject 2>, the woman with the short black bob, rectangular glasses and grey blazer, her face flat and calm; she looks down at the cake for a full beat, pushes her glasses up her nose with one finger, looks back up at him, and with a dry, low voice and a slow, level pace, (S2) says: <d>[Chinese] 所以消防车也是你叫的？</d> The camera holds a static shot at eye level. [Shot 3] At 00:07.600, the shot cuts back to a medium close-up on <Subject 1>: his proud grin stays fixed for one beat, then sags at the corners, his eyes slide down to the smoking cake, and his shoulders drop as he lowers the tray to the island. The camera holds a static shot. In the final second he settles and holds the pose, breathing, while the framing stays put. The segment ends with <Subject 1> in medium close-up behind the island, tray lowered, eyes on the cake; <Subject 2> out of frame at the right. They speak naturally. Those are the only words.

overall_soundscape: A quiet kitchen room tone, the silver tray clinking against the island tiles, a faint sizzle from the hot charred edge, a soft click as glasses slide up a nose, one small deflated sigh from Da Zhuang at the end.

non_diegetic_music: N/A
```

lint：`--seconds 10 --images 3 --audios 2` → PASS，0 error / 0 warning；380 词；台词 19 字。

## 该类型禁忌

- 在 soundscape 写 `audience laughter / crowd`（会长出观众）；在提示词里写「搞笑地」「滑稽地」。
- 一镜两人抢话；三人以上轮流抖包袱（单段说话人 ≤ 2）。
- 追逐 / 摔倒 / 拉伸变形的 slapstick 长镜直接交给 H3。
