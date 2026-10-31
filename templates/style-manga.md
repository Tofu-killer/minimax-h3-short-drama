# 风格档案 · 漫剧（2D 动画向）

## 全局风格锁（每段提示词开头逐字复用）
```
2D-animated, hand-drawn anime style with clean dark line art, flat cel shading with two-tone shadows, soft gradient backgrounds, limited animation with held poses and snappy key movements, consistent character proportions, {色彩基调: e.g. warm pastel palette / high-contrast noir ink}.
```
可选变体：`Chinese guoman style (国漫)`, `webtoon manhwa style`, `90s retro anime cel look`, `ink-wash wuxia`.

## 正向约束
```
Line quality, proportions and character colors stay identical in every frame. Mouth shapes follow the dialogue in simple anime lip flaps. Backgrounds stay painted and static unless the camera moves. Exactly {N} characters are present.
```

## 资产（定妆图）提示词模板
```
Anime character reference sheet, {角色描述}, front view and three-quarter view side by side, neutral expression, clean line art, flat cel colors, white background, consistent proportions, full outfit visible, high resolution.
```
场景图：`anime background painting, {场景}, no characters, painted style matching the character sheet, {时间与光线}`。
**所有参考图必须是同一画风**，真人照片和动画图混用会漂。

## 衔接与口型
- 漫剧对白口型宽容度高，一镜一人开口仍要守；台词写在 `<d>[Chinese] …</d>`。
- 漫剧多用静帧 + 推拉（限定动画），每镜「一个大动作」即可，运镜以 `slow push in` / `static` 为主，避免复杂跟拍。
- 转场多用硬切，不要让模型做溶解。

## 可用的公开工作流
- 官方 `workflows/official/video_minimax_h3_r2v.json`（参考图全部用动画风）；
- 子镜头分镜图钉帧：`workflows/official/video_minimax_h3_multiframe_reference.json`；
- 分镜图生成：Qwen‑Image‑Edit「人物多视角」「换装」工作流；
- 参考 APIDot 的动画示例写法（docs/04 §8 示例 4）。

## H3 配置
ref2va，768P；4 步抽卡 / 8 步成片；2D 风格对拖影不敏感，可多用 4 步；二采按需。
