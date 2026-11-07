# 风格档案 · 电影质感（真人向）

## 全局风格锁（每段提示词开头逐字复用）
```
Live-action, cinematic, photoreal. Shot on a digital cinema camera with a 35mm spherical lens, shallow depth of field, natural skin texture with visible pores, subtle film grain, soft motivated lighting from practical sources, muted desaturated palette with warm highlights and cool shadows, restrained acting.
```

## 正向约束（代替否定句）
```
Skin keeps natural texture and matte finish. Faces stay calm with small expressions. The camera makes exactly one movement per shot. Exactly {N} people are present.
```

## 资产（定妆图）提示词模板（Qwen‑Image / Krea2 / Flux，图像模型用）
```
Photorealistic portrait reference sheet, {角色描述: 年龄段、脸型、发型发色、体型、固定服装与饰物}, neutral expression, looking at camera, waist-up, plain mid-grey background, soft even key light from camera left, 85mm lens look, natural skin texture, no retouching, 4K.
```
每个角色出 3 张：正面半身、3/4 侧、全身；同一光线、同一服装。场景图：`photoreal {场景描述}, no people, {时间与光源}, 35mm lens, cinematic color grade`。

## 美学参考（可选）
挑 1 张你想要的电影截图或调色样片作 `<Picture N>`，retention 写 `weak_reference - only the film texture, color grade and lighting mood; never transfer faces, wardrobe or objects`。

## 运镜与灯光词
`slow push in` / `static locked-off` / `handheld with slight tremor` / `slow lateral track`；`window light` / `single practical lamp` / `overcast soft light` / `sodium streetlight`。

## H3 配置
ref2va，768P（1344×768 或 768×1344），8 步成片 / 4 步抽卡（仅构图），shift 12/3（Ref2V）；脸部特写段过一遍二采（去油）。
