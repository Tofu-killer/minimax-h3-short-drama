# 类型包 · 3D 国漫 / 三渲二 / 皮克斯式 3D 卡通

> 漫剧主力画风之一。官方 `3d-animation-short-generator` 以 H3 为默认模型，本包把它的规则压缩成 ComfyUI 本地可用的写法。

## 适用与 H3 强弱项

- **强**：官方评价 H3 在「视觉包装、设计语言、动态图形、多模态上下文理解」上强，适合有强设计语言的风格化 3D 短片与对白节拍（官方 `model-selection.md`）；动漫 / 风格化题材 H3 直出盲评胜（garycaogan）；3D 卡通材质掩盖写实皮肤问题。
- **弱**：弹性 squash-and-stretch 夸张表演、追逐与高潮动作——官方把这类镜头标为 Seedance 2.0 回退项（官方 `model-selection.md`、`fallback-policy.md`）；参考图混入真人照片会被拉回写实（senmanx：参考图全 3D 不出真人版）；风格中途漂移（三渲二 ↔ 全 3D）。
- **绕法**：失败重试阶梯照官方：① 重写时原样引用参考锚点块；② 镜头缩到 ≤ 6 s 拆行；③ 该镜换模型或改参考视频驱动；需要长期锁画风时上风格 LoRA（`lora-and-style.md` §1）。

## 推荐模式与参数

| 项 | 建议 |
|----|------|
| 模式 | Ref2VA（每个角色一张 3D 设定板 + 场景板）；关键镜头可先出 3D 首帧再 I2VA |
| 段长 / 镜数 | 6–12 s，2–3 镜；官方单镜 ≤ 15 s、单镜重要角色 ≤ 3 |
| 步数 | Turbo 8 步 shift 12/3；漫剧 / 插画风保持 Turbo（PDD 4 NFE 会压平纹理，`local-stack-and-acceleration.md`） |
| LoRA | 自训风格 LoRA「画风 + 固定造型」与参考图同用，强度 0.6–0.8（平衡）/ 1.0–1.2（画风优先）；Inner-Reflections 等 2D LoRA 不用于 3D |

## 风格句

- 3D 国漫：`3D Chinese donghua render, stylized toon materials, clean dark outlines, cel-shaded two-tone lighting with soft gradient shadows, high-detail 3D models with hand-painted texture strokes, strong cool rim light, consistent character proportions in every frame.`
- 三渲二变体：在上句加 `3D model precision combined with 2D hand-drawn brush strokes, strong backlit rim outline`（senmanx「3D 模型精度 + 2D 手绘笔触、强逆光轮廓光」）。
- 皮克斯式：`Pixar-inspired 3D cartoon rendering, C4D and Octane look, stylized Q-version proportions, warm subsurface-scattering skin, sculpted hair clumps with fine flyaway strands, clean motion`（官方 H3 前缀）。

## 镜头与运镜要点

- 官方镜头表六列（时长 / 衔接 / 参考锚点 / 钩子类型 / 逐秒指令 / 声音）先写好，再压缩成 `[Shot N]`；每镜写固定地标的屏幕位置与光向基线，跨镜不翻转（官方 `shot-table-spec.md`）。
- 弧形运镜适合 3D 角色登场；特写与其它景别交替，不重复同景别。
- 渲染前去掉所有分镜标签、箭头、编号（官方：成片不得残留分镜痕迹）。

## 表演与台词要点

- 夸张但可读：眉、眼角、瞳孔、脸颊形状的变化写成具体动作；高强度情绪可用「表情符号式」描述。
- 一镜一人开口；没说话的角色写 `stays out of frame` 或 `listens with mouth closed`。

## 声音

竹叶风声、布料、灯笼晃动；配乐写琵琶轮指 + 低鼓 + 笛长音，中速弱奏；全片 BGM 后期一条连续轨并在对白下压低（官方 `qc-checklist.md`）。

## 参考素材准备

每角色一张 16:9 3D 设定板（正 / 侧 / 背 + 表情 + 道具；官方角色卡带名字标签用于绑定，**送进 H3 的版本按本 skill 规则去掉文字**，`prompt-format.md` §3）；无人场景板（固定地标标清）；所有图同一渲染器风格、同一光照。

## 示例提示词（Ref2VA，10 s，3 图 + 1 音频）

接线：`<Picture 1>` 白璃（狐妖，说话人 = S1 = Audio 1）→ `<Picture 2>` 云澈 → `<Picture 3>` 竹林古祠 → `<Audio 1>` 白璃音色。

```text
subject_definitions: <Subject 1> is Bai Li, a 3D-animated fox spirit girl with a small pointed face, large amber eyes, long white hair, two white fox ears, wearing a pale jade green layered dress with a red sash, defined by <Picture 1>. <Subject 2> is Yun Che, a 3D-animated young swordsman with a lean face, sharp dark eyebrows, long black hair in a high ponytail bound by a silver crown, wearing a black and crimson cross-collar robe with a dark leather belt, defined by <Picture 2>. <Picture 3> is the environment: a moonlit bamboo forest around a ruined stone shrine with moss-covered steps and a single paper lantern hanging from the eaves. <Audio 1> is the voice-timbre reference for <Subject 1> (S1).

summary: [reference generation + audio reference] In a moonlit bamboo forest, the swordsman Yun Che lands on a bamboo stalk, the fox spirit Bai Li taunts him from the shrine steps, and he reacts; three shots, 10 seconds, 16:9.

retention_analysis: <Picture 1>: fully_preserved - 3D toon facial design, white hair, fox ears, jade dress and red sash; no other garment is substituted; its background is ignored. <Picture 2>: fully_preserved - 3D toon facial design, ponytail with silver crown, robe colors and belt; no other garment is substituted; never transfer facial traits from <Picture 2> onto <Subject 1>. <Picture 3>: partially_preserved - bamboo density, shrine layout, steps and lantern; the camera may move. <Audio 1>: attribute_transfer - voice timbre only for <Subject 1>.

detailed_description: 3D Chinese donghua render, stylized toon materials, clean dark outlines, cel-shaded two-tone lighting with soft gradient shadows, high-detail 3D models with hand-painted texture strokes, strong cool blue moonlight rim from behind, warm orange glow from the paper lantern as the key on faces, thin silver mist drifting between the bamboo stalks as the air layer, a palette of ink black, jade green and crimson, consistent character proportions in every frame. The setting is the bamboo forest shrine in <Picture 3>. Exactly two characters are present, each appearing once. [Shot 1] A wide shot from a low angle among the bamboo stalks: <Subject 2>, the swordsman in the black and crimson robe with the high ponytail and silver crown, drops from above and lands on the tip of a tall bamboo stalk at frame left, the stalk bending under his weight and springing back, his ponytail and wide sleeves swinging with the rebound. The camera arcs around the stalk with small amplitude at slow speed. [Shot 2] At 00:03.800, the shot cuts to a medium close-up of <Subject 1>, the fox spirit girl with long white hair, white fox ears and the jade green dress, sitting on the moss-covered shrine steps under the lantern, chin resting on one hand, her ears tilting toward him, the lantern light warming the left side of her face and the moonlight tracing the white fur of her ears; her amber eyes narrow into a playful smile and, with a light, teasing voice and a slow, sing-song pace, (S1) says: <d>[Chinese] 你的剑，比三百年前慢了。</d> The camera holds a static shot at eye level. <Subject 2> stays out of frame. [Shot 3] At 00:07.200, the shot cuts to a close-up of <Subject 2> on the bamboo tip, moonlight rimming his crown and the strands of his ponytail: his dark eyebrows pull together, his jaw sets, and his right hand closes into a tight fist at his side. The camera pushes in toward his face with small amplitude. In the final second both characters hold their poses, breathing, robes and hair drifting slightly, while the framing stays put. The segment ends with <Subject 2> in close-up at frame center, eyes fixed down toward the shrine steps. Speak only the quoted dialogue line. After that nobody says anything else.

overall_soundscape: Wind rustling through dense bamboo leaves, a creaking bamboo stalk bending and springing back, cloth sleeves flapping, a soft wooden sway of the paper lantern, crickets in the undergrowth.

non_diegetic_music: A pipa plays a quick tremolo phrase over a low frame drum pulse, settling into a sustained dizi flute note under the line, moderate tempo and soft dynamics.
```

lint：`--seconds 10 --images 3 --audios 1` → PASS，0 error / 0 warning；378 词；台词 10 字。

## 该类型禁忌

- 同一集混用真人参考图与 3D 参考图；三渲二与全 3D 段落交替。
- 设定板上的文字标签直接喂视频（会被画进画面）。
- 用真人负面词（`ugly, deformed`）约束动画；改为锁比例 / 轮廓 / 线宽 / 色板。
