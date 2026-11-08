# 类型包 · 动作打斗

> H3 最弱的类型之一。本包的目标不是「一条出大片」，而是把打戏拆成 H3 能做好的短拍，配首尾帧锁定起止。

## 适用与 H3 强弱项

- **强**：单次接触的受力结果（头后仰、滑步、溅水）；手持跟拍质感；打击音效与动作同步出声（原生音频）。
- **弱**：动作偏慢、长镜像慢动作（egguy886：打斗长镜前 5 秒动作量 3–4，每击一镜 28–30）；4 步 Turbo 几乎抹掉运镜（swan7 实跑，`camera-and-performance.md` §1）；物理理解弱于 LTX 2.5（SkyNotSilent `x-2087620996970791323`）；官方 3D skill 把「追逐、slapstick、高潮动作」明确列为 Seedance 2.0 的强项、H3 失败三次即切换（官方 `3d-animation-short-generator/references/model-selection.md`、`fallback-policy.md`）；举起/抱起整个人画不出（capruokz）。
- **绕法**：首尾帧 FL2VA 锁住起点与终点位移（manju-studio `gen_fl2v.py`：「单图只有起点，模型自由演化成慢动作」）；每击一镜；`All action plays at full real-time speed.` 写一次；精简提示词（< 400 词动作量 +60%，egguy886）；连续三次不过的拍改走参考视频驱动（reshot pose / depth，`06-quality` §reshot）或换模型。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | **FL2VA 三段式**（首帧 = 对峙站位，尾帧 = 结果姿态，图像模型出）；走位复杂时 Ref2VA + pose/depth 参考视频 `<Video 1>` |
| 段长 / 镜数 | 5–10 s；纯动作段每集最多 1 段，跨段插反应镜或一句台词（egguy886） |
| 每击时长 | egguy886 实测 0.8–1.4 s/击；**生成内切点 ≥ 1.2 s**（open-h3-ir T12，lint ERROR），所以提示词里每击写 1.2–1.6 s，更碎的切点后期剪 |
| 步数 | FL2V 768p Turbo 草稿 8 步、shift 6/3；定稿 20 步关 Turbo（运镜）；帧数 ≥ 124，三段式动作建议 192 |
| LoRA | JOKER141 Combat Base V2 / Weapon Combat、Jojocodex Wushu Action 仅列入候选（AIKSK v1.8.1 给了实验起始权重），本 skill 未实测，先盲测；与 Turbo 同载时额外 LoRA 和 ≤ 1.3 |

## 风格句

`Live-action, gritty action film, photoreal, shot on a 28mm lens, hard sodium-orange streetlight from frame left, wet concrete reflecting it, light rain as the air layer, a palette of orange, steel grey and black, fine grain. All action plays at full real-time speed.`

## 镜头与运镜要点

- 一镜一动作一个职责：建立距离 → 看清接触 → 反制 → 结果（irenerachel `camera-guide.md`）；接触前用看得见双方身体的景别，接触瞬间 `shakes slightly with the impact`。
- 固定轴线：两人屏幕左右全程不换，切镜前写清谁在左谁在右（irenerachel：人物左右互换 → 固定轴线）。
- 不写升格 / Hit-Stop / 变速；要「顿」写受力结果 `his head snaps back`（forest-laoli）。只给最关键一击一次慢动作，或完全不用。

## 表演与台词要点

- 施力源 → 轨迹 → 接触 → 阻力 → 位移 → 环境反馈（acheng 打戏因果链 / irenerachel）；速度词 `explosively / in a split second`（egguy886）。
- 打斗段通常无台词，写 `Nobody speaks.`；喘息、闷哼写进 soundscape。

## 声音

具体材质：布料与骨的闷响、湿地脚步、溅水、铁栏杆回声；拟音不写「啪 / 砰 / 轰」（会触发爆炸视觉）；配乐写太鼓 + 低频合成贝斯，重音落在结果动作上。

## 参考素材准备

首帧、尾帧两张（同机位或明确的新机位、同服装同光），文本里写清两人服装颜色作区分；武器各一张白底图且只接给持械镜。双人走位精确时加灰色火柴人站位线稿（egguy886，约 1/6 概率线稿入画需重抽）。

## 示例提示词（FL2VA，10 s，2 图：首帧 + 尾帧，0 音频）

```text
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 4) aligns with the 10.13-second mark of the target video.

integrated_multimodal_description: [Shot 1] Live-action, gritty action film, photoreal, shot on a 28mm lens, hard sodium-orange streetlight from frame left, wet concrete reflecting it, light rain falling as the air layer, a palette of orange, steel grey and black, fine grain. All action plays at full real-time speed. On the rain-soaked top deck of a parking garage at night, the fighter in the red track jacket and black trousers stands at frame left and the bald fighter in the grey hoodie stands at frame right, three metres apart, both in guard, matching <Picture 1>. The red-jacket fighter explosively sprints across the wet deck toward the grey-hoodie fighter, who drops his weight and raises both forearms. The camera tracks with the runner from the side in handheld, keeping both men in frame. [Shot 2] At 00:02.400, the shot cuts to a medium shot on the line between them: the red-jacket fighter drives his right elbow into the raised forearms in a split second, and the grey-hoodie fighter's head snaps back as he slides half a step on the wet concrete. The camera shakes slightly with the impact. [Shot 3] At 00:03.800, the shot cuts to a low angle at deck level: the grey-hoodie fighter sweeps his right leg low across the puddles, spraying a fan of water, and the red-jacket fighter hops over the leg and lands square on both feet. The camera holds low and pans with the sweep. [Shot 4] At 00:05.200, the shot cuts to a medium wide shot facing the guardrail: the red-jacket fighter seizes the grey hoodie at the collar with both hands and drives him three steps back until his spine meets the steel guardrail, pinning him there, both men breathing hard, rain streaming off their faces. The camera pushes in toward the pinned fighter with small amplitude. In the final second both men hold the pin, chests heaving, while the framing stays put, ending on the composition of <Picture 2>. Between the two reference frames the motion is one continuous, physically connected sequence across the cuts. Nobody speaks.

overall_soundscape: Steady rain on concrete, quick splashing footsteps, a heavy cloth-and-bone thud on the elbow strike, a sharp exhale from the struck fighter, water spraying from the leg sweep, two feet landing in a puddle, a deep metallic clang as a back hits the guardrail, ragged breathing.

non_diegetic_music: Fast taiko-style drums with a pulsing low synth bass at a quick tempo, a single drum hit landing on the guardrail impact, then a held low drone to the end.
```

lint：`--seconds 10 --images 2 --audios 0 --mode fl2va` → PASS，0 error / **1 warning**（4 镜超出 10 s 建议的 2–3 镜）。**保留理由**：打斗按 egguy886「每击一镜」实证，4 镜均 ≥ 1.4 s，满足 1.2 s 硬下限；正文 342 词，符合动作段 < 400 词精简原则。

## 该类型禁忌

- 一镜里「出拳 + 格挡 + 回旋踢 + 摔投」堆动作名；15 s 一镜到底打戏直接交给 H3（动作会做不完）。
- `in slow motion`、`bullet time`（除非挂环绕 LoRA）；`completely still` 的对峙（拖掉约 80% 运镜）。
- 血浆、断肢；平台合规改为格挡弹开、光点消散（senmanx）。
