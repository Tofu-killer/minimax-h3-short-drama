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

用 `image-prompts.md` §1–§5 的模板（定妆照 → 单人单视图 → 场景无人母版 → 道具白底图），规则见 `../references/image-stage.md`：参考图是单人单视图、不是多视图设定板；模板里不写 photorealistic / 4K / masterpiece 这类词，也不写 no people / no text（CFG 1 的模型会把名词召唤出来，要用正向写法）。**所有参考图必须是同一画风**，真人照片和动画图混用会漂。

## 衔接与口型
- 漫剧对白口型宽容度高，一镜一人开口仍要守；台词写在 `<d>[Chinese] …</d>`。
- 漫剧多用静帧 + 推拉（限定动画），每镜「一个大动作」即可，运镜以 `slow push in` / `static` 为主，避免复杂跟拍。
- 转场多用硬切，不要让模型做溶解。

## 可用的公开工作流
- ComfyUI 自带模板里的 MiniMax H3 Reference to Video（`comfyui-nodes.md` §2；参考图全部用动画风）；仓库 `workflows/official/` 里也有一份，不随 skill 安装；
- 子镜头分镜图钉帧：给该镜写 `keyframe`，提交时加 `--anchor`（脚本按 ComfyUI 多帧模板的方式串 `MiniMaxH3AddGuide`，`comfyui-nodes.md` §3）；
- 分镜图生成：Qwen‑Image‑Edit「人物多视角」「换装」工作流；
- 动画示例写法见 `genres/09-2d-anime.md`。

## H3 配置
ref2va，768P；草稿 Turbo 8 步（2D 风格对拖影不敏感，没有运镜的镜头可以用 4 步）；有运镜的镜头精修同样 20 步、关 Turbo；二采按需。
