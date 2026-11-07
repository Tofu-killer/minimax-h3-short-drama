# 症状 → 原因 → 修法（禁忌清单）

> 综合：本仓库 `docs/reviews/ep01_test`（真实成片评审）、`docs/11-acceleration.md`（4090 / 4060Ti 实测）、MiniMax 官方生态索引、GitHub 各节点 README 的 Known issues。精读报告见 `docs/13-github-survey/`。

## A. 画质 / 速度

| 症状 | 最常见原因 | 修法 |
|------|-----------|------|
| 背景横向拖影、颗粒 | 4 步 Turbo + 大动态；544p LoRA 跑 768p；FL2V 768p 版 shift 仍是 12 | 改 8 步 `_768p_` 版 LoRA（FL2V 配 SigmaShift 6/3，Ref2V 12/3）；大动态镜头拆短 |
| 皮肤塑料/油腻、笑容夸张 | 步数 > 8 或 LoRA 强度 > 1；Ref2VA 多参考；表情词抽象 | 强度 0.8–0.95；表情写具体（`confident half-smile, lips closed`）；二采去油或 Ref-Patch |
| 双眼发光、面部变形 | 多参考图职责冲突；参考图小脸；长段 15 s | 一职责一图；脸占画面 ≥ 1/3 的正面图；段压到 ≤ 10 s |
| 文字乱码、手嘴变形 | 开了 TE-Speed / 缓存类加速 + 8 步 Turbo + int8 | 关掉缓存类；只保留 Sage + 一个蒸馏 LoRA |
| 4090 比别人 5070 慢 | 对方 544p/480p + 4 步；你 1344×768 + 20 步 CFG 分支；Windows CUDA 系统内存回退；没开 Sage | 同口径比较；关掉 CUDA sysmem fallback；Sage；草稿档降到 864×480 |
| 第一步极慢（>10 分钟） | SageAttention 与 `MiniMaxLowVRAMAttention` 同开 | 二选一，旁路（Ctrl+B）另一个，不要删节点 |
| 第二次同参数秒出 | ComfyUI 结果缓存命中 | 抽卡必须换 seed；计时用 seed+1 |
| 冷启动 8–14 分钟 | JIT 编译 + 34 GB 载入 | 第 2 条起才算速度；保持 ComfyUI 常驻 |
| OOM / 系统内存爆 | 不剪枝 int8 + 32B nvfp4 TE 同驻；`MAX_PINNED_MEMORY` 吃掉 40% RAM | 用 pruned_int8；`--disable-pinned-memory`；TE 用后卸载 |
| 音频破损、对白含糊 | 4 步 Turbo 预览版 LoRA；台词超预算 | 8 步 v1.x；台词预算 (段长−2)×4.5 |

## B. 内容 / 逻辑

| 症状 | 原因 | 修法 |
|------|------|------|
| 道具是虚构的（例：保险柜里的红色物品） | 请求里没有道具参考图，只有人物与场景 | 道具目录化、绑定进 `prop_ids`、`the exact item shown in <Picture N>` + `no other item is substituted` |
| 角色换装、长出喷气背包 | 该段没带该角色的服装参考；否定句被渲染 | 每段都带角色 2 图；正向锁定（`his back is bare except…`） |
| 角色瞬移 / 消失 / 多出一个人 | 多人镜头未写明每人位置与动作；`continuity` 为空 | 每人每镜都写位置/姿态；`end_state`→下一段开场；群像先写人数 |
| 台词复读两遍 | 台词写了两处（动作句 + 对白句）；无 (S1) | 只写一次 `<Subject 1> (S1) says: <d>…</d>` |
| 错人张嘴 | 一镜两人开口；听者没写闭嘴 | 一镜一人；`listens with mouth closed` |
| 字幕重复/乱码 | 让模型画字幕 | 后期烧录 |
| 画幅不对 | 把 16:9 写进文字 | 用节点/参数设定宽高 |
| 跨段空间不连续、背景人物移位 | 用「continue the previous video」做续写 | 尾帧→首帧 I2VA，或 latent 续接节点（Motion-Context 类），或 FL2VA 2–4 s 转场段 |
| 拼接处闪帧 | 边界帧重复 / 不同编码参数 concat | 统一转码后 concat；检查首尾重复帧 |

## C. 组合禁忌（不要同时做）

- 两个蒸馏 LoRA（Turbo + PDD / FastH3 / Hyperflow / DMAD）叠加 → 过蒸馏。
- VDN / PDD 的量化权重 + 另一个加速 LoRA → 这些权重已折叠蒸馏。
- SageAttention + `MiniMaxLowVRAMAttention`。
- 原生 `ModelAttentionBackend(comfy kitchen)` + FeiHou 流式块模式。
- 精修档开 Spectrum / BlockSparse / FirstBlockCache / TE-Speed 等有损加速。
- 一个镜头内多个运镜；一个镜头内两人说话；一段内给角色换装。
- Image-VAE（单帧图专用）用于视频解码。
- 删除节点来「关掉」功能（后面想用找不回）→ 用旁路 / Fast Groups Bypasser。
