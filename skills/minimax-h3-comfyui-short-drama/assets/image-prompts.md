# 生图提示词模板（复制即用）

> 说明、来源与参数见 `../references/image-stage.md`。`{}` 是占位符；LOOK = 系列圣经里冻结的外观文字，也就是分镜 JSON 里角色的 `sheet_phrase`——只给生图用，不进视频提示词（视频提示词用短的 `identity_phrase`）（族裔 + 年龄 + 3–5 处骨相 + 发型 + 上装/下装/鞋 + 标志物），每次逐字粘贴。
> 填写前过一遍防撞脸：两人骨相 ≥ 3 处不同、其余五格（发型/体型/体态/主色/标志）≥ 2 格不同；写 `about {HEIGHT_CM} cm tall with a {BUILD} build`；主角只加一句颜值定位；不写 photorealistic / 8K / masterpiece / flawless / perfect / beautiful；正向写法，排除词只放 Edit 2511 的负向框。
> 指图写法：Qwen-Image-Edit-2511 的节点只有 `image1`–`image3` 三个图像输入，并在提示词前自动加 `Picture 1: `、`Picture 2: `、`Picture 3: ` 标签（ComfyUI v0.46.2 源码）→ 2511 的模板一律写 `Picture 1` / `Picture 2` / `Picture 3`（与 `<image1>` 的效果差别待 A/B）；`<image1>` 只用于 Qwen-Image 2.1。§8–§12 是 LoRA 模板：触发句逐字照抄作者 / 官方模板原句，原句里自带的 `don't`、`remove`、「移除」是作者的触发写法，自己追加的内容仍只写正向；这五条都没有在 4090 上实跑过。

## 1. 定妆照（单张半身，身份唯一来源）

_Qwen-Image 2.1 50 步 / Z-Image-Turbo 8 步，1024×1024_

**电影质感**

```text
Studio character reference photo, a single person in one image, medium close-up bust portrait facing the camera at eye level, plain light grey seamless background, soft even studio light with a matte skin finish, sharp focus, realistic photograph. {ETHNICITY} {GENDER} of {AGE}, {3-5 BONE TRAITS}, {HAIR}, {SKIN}, wearing {TOP}, {BOTTOM}, {SHOES}, {SIGNATURE ITEM}. {APPEAL LINE (leads only)} Gentle natural expression, lips closed. Clean frame containing only the depicted subject.
```

**漫剧**

```text
Anime character bust portrait, a single character in one image, facing the viewer at eye level, plain white background, even flat lighting, {STYLE LOCK: clean dark line art, flat cel shading with two-tone shadows, warm pastel palette}. {ETHNICITY} {GENDER} of {AGE}, {3-5 BONE TRAITS}, {HAIR}, {EYE COLOR}, wearing {TOP}, {BOTTOM}, {SIGNATURE ITEM}. Calm expression, mouth closed. Clean frame containing only the depicted subject.
```

## 2. 派生视图（每视图一张单人图，只参考锚点）→ 脚本拼 16:9 角色板

_Qwen-Image-Edit-2511，20 步 CFG 4；Picture 1 = 锚点（见下表），每次只出一个视图，哪张坏了单独重出；全身视图竖幅 1024×1536，face.png 1024×1024；16:9 角色板（左 1/3 face.png + 右 2/3 正 / 侧 / 背同比例，2688×1536 / 2560×1440）用脚本拼出来只给人审，不喂给任何模型；本节模板由原 16:9 角色板模板改写成单视图，未实跑_

**电影质感**

```text
Keep exactly the same person as Picture 1: same face, hairstyle, outfit, accessories and marks ({LOOK, verbatim}). New photo: a character reference view of this one person alone on a seamless pure white background, soft even studio lighting with a matte skin finish. {VIEW} About {HEIGHT_CM} cm tall with a {BUILD} build, true body proportions of {7} heads tall. One single person, the only subject in the image. Live-action photograph, 85mm lens look, natural skin texture, true-to-life colors. Clean frame containing only the depicted subject.
```

**漫剧**

```text
Keep exactly the same character as Picture 1: same face, hairstyle, outfit, line weight and colors ({LOOK, verbatim}). New frame: an anime character model view of this one character alone on a seamless pure white background, even flat lighting, {STYLE LOCK}. {VIEW} About {HEIGHT_CM} cm tall with a {BUILD} build, consistent proportions of {6} heads tall. One single character, the only subject in the image. Clean frame containing only the depicted subject.
```

**`{VIEW}` 取值（两种风格共用）**

| 视图 | Picture 1 | `{VIEW}` |
|------|-----------|----------|
| 正面全身 `<id>_full.png`（锚点：只出一次，人确认后冻结；待 A/B） | 半身定妆照 bust | `Full-body front view standing upright, from the top of the head to the soles of the shoes with a little white margin above and below, arms relaxed at the sides, hands empty, calm neutral expression, lips closed.` |
| face.png（头肩特写，脸占满画面） | 半身定妆照 bust | `Front-facing head-and-shoulders close-up at eye level with the face filling the frame, calm neutral expression, lips closed, looking into the camera.` |
| 纯 90° 侧 | 正面全身 | `Full-body strict 90-degree side view standing upright, from the top of the head to the soles of the shoes with a little white margin above and below, same scale and camera distance as Picture 1, arms relaxed at the sides, hands empty.` |
| 背 | 正面全身 | `Full-body back view standing upright, from the top of the head to the soles of the shoes with a little white margin above and below, same scale and camera distance as Picture 1, arms relaxed at the sides, hands empty.` |

## 3. 场景母版（无人、写光向）

_Qwen-Image 2.1 50 步，2688×1536_

**电影质感**

```text
A cinematic film still of an empty {PLACE}, wide establishing view at eye level from {CAMERA SPOT} looking {DIRECTION} along the main axis, 16:9. {LAYOUT: the door on the left wall, a tall window on the right wall, a desk at the centre}. {TIME OF DAY}: one key light, {SOURCE} from {DIRECTION}, shadows falling toward {DIRECTION} with soft falloff and detail kept in the shadows. Shot on a 35mm lens at f/4, deep focus, true-to-life colors, uncluttered. The space holds only its architecture and furniture, deserted and still.
```

**漫剧**

```text
An anime background painting of an empty {PLACE}, wide establishing view at eye level from {CAMERA SPOT}, 16:9, painted style matching the character sheets, {STYLE LOCK}. {LAYOUT}. {TIME OF DAY} light from {DIRECTION} in flat cel-shaded blocks. The space holds only its architecture and furniture, deserted and still.
```

## 4. 场景 3×3 九宫格

_Qwen-Image 2.1，整板 16:9；{STYLE LINE} 填电影质感或漫剧的风格句_

**两种风格共用**

```text
One 16:9 location board divided into exactly nine equal panels in a 3x3 grid with thin white gutters. All nine panels show the same empty {PLACE} with identical architecture, furniture positions, materials, colors, time of day and light direction; only the camera position changes. 1 view from the doorway into the room; 2 wide view of the main activity area; 3 the window side with the light falling in; 4 reverse view from inside toward the door; 5 high overhead view of the floor layout; 6 long-lens diagonal view from one corner to the opposite corner; 7 close view of {SIGNATURE FURNITURE}; 8 close view of {WALL DETAIL}; 9 the view out of the window. A small numeral 1-9 in each panel's top-left corner. Uniform 50mm lens, bright even exposure, one white balance. The place: {SCENE DESCRIPTION, verbatim from the bible}. {STYLE LINE of A or B}. Every panel is a deserted space.
```

## 5. 道具（1:1 白底单品）

_Qwen-Image 2.1，2048×2048_

**电影质感**

```text
Product reference photo of {ITEM}, one object centered on a seamless pure white background, 1:1, three-quarter front view at eye level, soft even studio light with a soft contact shadow beneath it, {MATERIAL}, {COLOR}, {WEAR MARKS}, {REAL TEXT: the label reads "{TEXT}" in {COLOR} block letters at the upper left}, about {SIZE} cm long. Sharp focus across the whole object, true-to-life colors. The frame contains only this one object.
```

**漫剧**

```text
Anime prop illustration of {ITEM}, one object centered on a pure white background, 1:1, three-quarter front view, {STYLE LOCK}, {MATERIAL AND COLOR}, {REAL TEXT}, about {SIZE} cm long. The frame contains only this one object.
```

## 6. 逐镜首帧（字面首帧，Qwen-Image-Edit-2511）

_1344×768（竖屏 768×1344）；参考合计 ≤ 3 张（节点只有 `image1`–`image3`），顺序 = 入画角色 bust/face.png → 最后一张场景裁切（模板里的 `Picture {K}`）；用附带的 `workflows/qwen_edit2511_{1,2,3}ref.api.json`（输出已固定 1344×768；默认 40 步 CFG 4、AuraFlow 3.1、CFGNorm 1.0，即官方 int8 模板的默认值；模板自带的对照表里 Comfy 的 20 步也行：`--set 170:169.steps=20`）；提示词用 `--set 170:151.prompt=@文件`，负向用 `--set 170:149.prompt=…`；直接用官方模板的话，它的出图尺寸跟着第 1 张图走，做 16:9 首帧要换成 1344×768 的空潜空间（`../references/image-stage.md` §1）；模板里的胶片 / 镜头描述换成和分镜 `style` 一致的说法；`Picture N` 写法待 A/B_

**电影质感**

```text
Keep exactly the same person as Picture 1: same face, hairstyle and clothes ({LOOK, verbatim}). {Keep exactly the same person as Picture 2: … ({LOOK})}. The room is the one in Picture {K}: same walls, furniture and light direction. New photo: A cinematic film still from a {GENRE} drama, shot on Kodak Vision3 500T film with an anamorphic 50mm lens at f/2. {FRAMING}, {WHO stands WHERE doing WHAT at the first instant, EXPRESSION}. Exactly {N} people in the frame. {ONE LIGHT SOURCE, direction, color}.
```

**漫剧**

```text
Keep exactly the same character as Picture 1: same face, hairstyle, outfit, line weight and colors ({LOOK}). The place is the one in Picture {K}. New frame: a frame from a 2D anime episode, {STYLE LOCK}. {FRAMING}, {WHO WHERE DOING WHAT, EXPRESSION}. Exactly {N} characters in the frame.
```

**首帧里有道具**（道具图占一个输入位：人 + 道具 + 场景裁切正好 3 张；`{P}` 是道具图的编号）——在上面的模板里、`New photo:` 之前加一句：

```text
The object in {his/her} {left/right} hand is the exact item shown in Picture {P}: same shape, color and markings, no other item is substituted.
```

**两个人 + 道具同框**（3 个输入位不够，分两步）：先用上面的模板出「两人 + 场景」；再用 `qwen_edit2511_2ref`，`image1` = 刚出的那张、`image2` = 道具图：

```text
Keep everything in Picture 1 exactly as it is: the same two people, their faces, clothes and positions, the same room and light. Change one thing only: {WHO, by clothing} now holds the exact item shown in Picture 2 in {his/her} {left/right} hand at {chest / desk} height, same shape, color and markings as in Picture 2.
```

**过肩镜头里背对镜头的人**：不要给这个人的 `face.png`——参考图里有什么就容易出现什么，一张正脸会被画到本该是后脑勺的位置。给背面视图（`<id>_back.png`）；没有背面视图就不给图，只在文字里照抄 LOOK 里的发型和上衣。正对镜头的那个人照常给 `face.png`。（这条是按上面那条规律定的，没有做过对比。）

**负向框（只在 CFG 4 时填，正向里不写排除词）**

```text
text, watermark, caption, collage, split panels, extra person, extra fingers, waxy skin
```

## 7. 换装 / 年龄子资产（编辑已冻结的单视图）

_Qwen-Image-Edit-2511，Picture 1 = 已冻结的正面全身；侧 / 背再用 §2 从变体全身派生，每套变体也是一组单人单视图_

**两种风格共用**

```text
Keep exactly the same person as Picture 1: same face, skin, hairstyle, body proportions and height. Change only the clothing to {NEW OUTFIT}. Same view, same pose, same pure white background, same lighting.
```

## 8. 同场多机位（Edit-2511 + Multiple-Angles LoRA）

_`fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA` 的 `qwen-image-edit-2511-multiple-angles-lora.safetensors`，强度 0.9（模型卡 0.8–1.0，官方模板 1.0）；Picture 1 = 同场底图（定稿首帧或场景母版）；整条提示词只有一行，`<sks>` 必写，顺序固定为方位 → 俯仰 → 距离；4 步 Lightning CFG 1 抽、40 步 CFG 4 定；大角度（背面、俯 60°）会补画看不见的部分，转完人审并过身份门禁_

**两种风格共用**

```text
<sks> {AZIMUTH} {ELEVATION} {DISTANCE}
```

| 槽 | 取值（8 × 4 × 3 = 96 机位，模型卡） |
|----|------|
| `{AZIMUTH}` | `front view`（0°）、`front-right quarter view`（45°）、`right side view`（90°）、`back-right quarter view`（135°）、`back view`（180°）、`back-left quarter view`（225°）、`left side view`（270°）、`front-left quarter view`（315°） |
| `{ELEVATION}` | `low-angle shot`（−30°）、`eye-level shot`（0°）、`elevated shot`（30°）、`high-angle shot`（60°） |
| `{DISTANCE}` | `close-up`、`medium shot`、`wide shot` |

**示例（取自模型卡的 96 条；正反打 / 过肩 / 俯拍每个机位写一行，都从同一张双人底图转）**

```text
<sks> front-right quarter view eye-level shot medium shot
<sks> back-left quarter view eye-level shot medium shot
```

## 9. 姿势迁移（Edit-2511 + AnyPose，仅写实单人）

_`lilylilith/AnyPose` 的 `2511-AnyPose-base-000006250.safetensors` 0.7 + `2511-AnyPose-helper-00006000.safetensors` 0.7，配 `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` 4 步 CFG 1；image 1 = 要摆姿势的角色（全身连地面入画最稳），image 2 = 姿势图（单人；任意照片或 3D 假人渲染）；平涂 / 像素画风与多人图失效（作者自述），漫剧不用_

**作者触发原句（逐字照抄；用的是 `image 1` / `image 2`，句中的 `don't do it` 是作者写法）**

```text
Make the person in image 1 do the exact same pose of the person in image 2. Changing the style and background of the image of the person in image 1 is undesirable, so don't do it. The new pose should be pixel accurate to the pose we are trying to copy. The position of the arms and head and legs should be the same as the pose we are trying to copy. Change the field of view and angle to match exactly image 2. Head tilt and eye gaze pose should match the person in image 2.
```

**可选追加（作者原句）：出图背景被换成姿势图的背景时接在句尾；看不到的部位（如下装）另用一句正向描述补在最后**

```text
Remove the background of image 2, and replace it with the background of image 1.
```

## 10. 换头修脸（Edit-2511 + BFS head v5）

_`Alissonerdx/BFS-Best-Face-Swap` 的 `bfs_head_v5_2511_merged_version_rank_16_fp16.safetensors`，强度 1.0；euler / simple 20 步 CFG 2.5，`ModelSamplingAuraFlow` 1.0、CFGNorm 1.0（作者 V5 工作流）；Picture 1 = 已出好的首帧（构图 / 光线 / 姿势都对，只有脸不像），Picture 2 = 该角色的 face.png，顺序不能反；脸小的镜头启用工作流里的裁头部 → 换 → 贴回（`InpaintCropImproved` / `InpaintStitchImproved`，默认旁路）；修完重新过身份门禁；只换本项目自己生成的角色（作者：不用于公众人物或未经同意的真人）。非商用可换 Qwen-Image 2.1 + `bfs_head_v1.1_qwen_2.1.safetensors`（1.0，8 步 CFG 1；原句改用 `<image1>` / `<image2>`，见该仓库 `docs/qwen-image-2.1.md`）_

**作者触发原句（逐字照抄；`remove the head` 是作者写法）**

```text
head_swap: start with Picture 1 as the base image, keeping its lighting, environment, and background. remove the head from Picture 1 completely and replace it with the head from Picture 2, strictly preserving the hair, eye color, and nose structure of Picture 2. copy the eye direction, head rotation, and micro-expressions from Picture 1.
```

## 11. 分镜草图链（Next-Scene LoRA，只作审稿）

_Qwen-Image 2.1（非商用）：`akhaliq/Qwen-Image-2.1-Next-Scene-LoRA` 的 `next_scene_step2500.safetensors`，强度 0.7–0.9，28–40 步 CFG 1；Edit-2509：`lovis93/next-scene-qwen-image-lora-2509` 的 `next-scene_lora-v2-3000.safetensors`，强度 0.7–0.8（模型卡；作者工作流填 1.0），配 Lightning、8 步 CFG 1；在 2511 上是否可用未验证。输入 = 上一帧，输出再喂回去；链式每跳先给输入加约 0.5 px 高斯模糊并把强度压到 ≤ 0.7（2.1 版模型卡的链式配方），链越长漂移越大（作者示例 4 跳）。只用来快速出一场戏的草图序列给人审，定稿首帧仍从母版 + 角色参考重出_

**两种风格共用（以 `Next Scene:` 开头，先写运镜，再写主体 / 光线变化）**

```text
Next Scene: {CAMERA MOVE}, {WHAT IS REVEALED OR HOW THE SUBJECT / LIGHT CHANGES}.
```

**示例**

```text
Next Scene: The camera pulls back to a wide shot, revealing {WHAT COMES INTO VIEW}.
```

## 12. 光照迁移（Edit-2509 + Light-Migration LoRA，待 A/B）

_`Comfy-Org/Qwen-Image-Edit` 的 `split_files/loras/Qwen-Image-Edit-2509-Light-Migration.safetensors`，强度 1.0；这是 **2509** 的 LoRA：官方模板 `templates-portrait_light_migration` 用 `qwen_image_edit_2509_fp8_e4m3fn.safetensors`（19.03 GB，另下），euler / simple 两档：开 `lightx2v/Qwen-Image-Lightning` 的 `Qwen-Image-Edit-2509/Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors` 时 4 步 CFG 1，不开时 20 步 CFG 4；图 1 = 要重打光的首帧，图 2 = 光照参考。在 2511 上是否等效、是否伤身份都未验证 → 做完必须再过身份门禁。只用于「同场首帧都生成完后，用同一张光照参考统一一次」；换时段是重新生成母版，不是重打光；多数情况先靠母版 + 提示词里的单一光源句，后期统一调色更便宜_

**官方模板原句（中文原样保留、逐字照抄，「移除」是模板写法；要追加的编辑指令接在句后）**

```text
参考色调，移除图1原有的光照并参考图2的光照和色调对图1重新照明
```
