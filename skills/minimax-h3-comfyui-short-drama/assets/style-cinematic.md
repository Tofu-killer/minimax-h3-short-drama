# 风格档案 · 电影质感（真人向）

## 全局风格锁（每段提示词开头逐字复用）
```
Live-action, cinematic, photoreal. Shot on a digital cinema camera with a 35mm spherical lens, shallow depth of field, natural skin texture with visible pores, subtle film grain, soft motivated lighting from practical sources, muted desaturated palette with warm highlights and cool shadows, restrained acting.
```

## 正向约束（代替否定句）
```
Skin keeps natural texture and matte finish. Faces stay calm with small expressions. The camera makes exactly one movement per shot. Exactly {N} people are present.
```

## 资产（定妆图）提示词模板

用 `image-prompts.md` §1–§5 的模板（定妆照 → 单人单视图 → 场景无人母版 → 道具白底图），规则见 `../references/image-stage.md`：参考图是单人单视图、不是多视图设定板；模板里不写 photorealistic / 4K / masterpiece 这类词，也不写 no people / no text（CFG 1 的模型会把名词召唤出来，要用正向写法）。真人参考图一律实拍质感，不要把插画当参考。

## 美学参考（可选）
挑 1 张你想要的电影截图或调色样片作 `<Picture N>`，retention 写 `weak_reference - only the film texture, color grade and lighting mood; never transfer faces, wardrobe or objects`。

## 运镜与灯光词
`slow push in` / `static locked-off` / `handheld with slight tremor` / `slow lateral track`；`window light` / `single practical lamp` / `overcast soft light` / `sodium streetlight`。

## H3 配置
ref2va，768P（1344×768 或 768×1344），草稿 Turbo 8 步（4 步只用来看构图，会抹掉运镜）；中选后同 seed 精修，有运镜的镜头 20 步、关 Turbo（SKILL.md 铁律 16）；shift 12/3（Ref2V）；脸部特写段过一遍二采（去油）。
