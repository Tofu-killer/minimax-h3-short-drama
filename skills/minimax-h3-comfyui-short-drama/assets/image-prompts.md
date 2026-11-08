# 生图提示词模板（复制即用）

> 说明、来源与参数见 `../references/image-stage.md`。`{}` 是占位符；LOOK = 系列圣经里冻结的外观文字（族裔 + 年龄 + 3–5 处骨相 + 发型 + 上装/下装/鞋 + 标志物），每次逐字粘贴。
> 填写前过一遍防撞脸：两人骨相 ≥ 3 处不同、其余五格（发型/体型/体态/主色/标志）≥ 2 格不同；写 `about {HEIGHT_CM} cm tall with a {BUILD} build`；主角只加一句颜值定位；不写 photorealistic / 8K / masterpiece / flawless / perfect / beautiful；正向写法，排除词只放 Edit 2511 的负向框。

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

## 2. 16:9 角色板（左 1/3 特写 + 右 2/3 正/侧/背）

_Edit 2511 以 bust 为 <image1>，或 Qwen-Image 2.1 文生图，2688×1536 / 2560×1440；成图后裁左 1/3 得 face.png_

**电影质感**

```text
A character reference sheet, 16:9 landscape, seamless pure white background, soft even studio lighting with a matte skin finish. Left third: one front-facing head-and-shoulders close-up at eye level, calm neutral expression, lips closed, looking into the camera. Right two thirds: three full-body views standing side by side, front, strict 90-degree side and back, each from the top of the head to the soles of the shoes with a little white margin above and below, all at the same scale, same height, same camera distance and same light, arms relaxed at the sides, hands empty. The person: {LOOK as in 定妆照}. About {HEIGHT_CM} cm tall with a {BUILD} build, true body proportions of {7} heads tall, scaled uniformly in every view. Identical outfit, hairstyle, accessories and marks in every view; one single person shown from several angles, the only subject in the image. Live-action photograph, 85mm lens look, natural skin texture, true-to-life colors. Clean frame containing only the depicted subject.
```

**漫剧**

```text
An anime character model sheet, 16:9 landscape, seamless pure white background, even flat lighting. Left third: one front-facing head-and-shoulders close-up, calm expression, mouth closed. Right two thirds: front, strict 90-degree side and back full-body views side by side at the same scale and the same ground line, arms relaxed, hands empty, head to shoes fully inside each panel. The character: {LOOK}. About {HEIGHT_CM} cm tall with a {BUILD} build, consistent proportions of {6} heads tall. {STYLE LOCK}. Identical line weight, colors, outfit and hairstyle in every view; one single character, the only subject in the image. Clean frame containing only the depicted subject.
```

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

_1344×768（竖屏 768×1344）；参考顺序 = 入画角色 bust/face.png（≤3）→ 最后一张场景裁切；20 步 CFG 4，AuraFlow 3.1，CFGNorm 1.0_

**电影质感**

```text
Keep exactly the same person as <image1>: same face, hairstyle and clothes ({LOOK, verbatim}). {Keep exactly the same person as <image2>: … ({LOOK})}. The room is the one in <image{N}>: same walls, furniture and light direction. New photo: A cinematic film still from a {GENRE} drama, shot on Kodak Vision3 500T film with an anamorphic 50mm lens at f/2. {FRAMING}, {WHO stands WHERE doing WHAT at the first instant, EXPRESSION}. Exactly {N} people in the frame. {ONE LIGHT SOURCE, direction, color}.
```

**漫剧**

```text
Keep exactly the same character as <image1>: same face, hairstyle, outfit, line weight and colors ({LOOK}). The place is the one in <image{N}>. New frame: a frame from a 2D anime episode, {STYLE LOCK}. {FRAMING}, {WHO WHERE DOING WHAT, EXPRESSION}. Exactly {N} characters in the frame.
```

**负向框（只在 CFG 4 时填，正向里不写排除词）**

```text
text, watermark, caption, collage, split panels, extra person, extra fingers, waxy skin
```

## 7. 换装 / 年龄子资产（编辑已有角色板）

_Qwen-Image-Edit-2511，<image1> = 已定稿角色板_

**两种风格共用**

```text
Keep exactly the same person as <image1>: same face, skin, hairstyle, body proportions and height. Change only the clothing to {NEW OUTFIT}. Same sheet layout, same pure white background, same lighting.
```
