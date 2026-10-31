# Agent 提示词 · 从零开一个电影质感 / 漫剧项目

> 给本地 agent 的开项目指令。先在「项目设定」里填空，其余照抄。它假设 agent 已完成 `prompts/02-local-takeover.md` 的接管（本地 ComfyUI、H3 权重、工作流可用）。

```
我要用本地 MiniMax H3 做一部新短剧，不用之前的三角洲素材。按下面的设定从零建项目，走仓库 https://github.com/Tofu-killer/minimax-h3-short-drama 的流程，每个阶段完成后给我看结果再往下。

## 项目设定
- 题材与一句话故事：[例：都市悬疑，女法医在旧案卷宗里发现自己父亲的名字]
- 风格：[二选一：电影质感 → 用 templates/style-cinematic.md；漫剧 → 用 templates/style-manga.md，并指定变体如 国漫 / 日系 / 韩漫]
- 画幅：[9:16 竖屏 / 16:9 横屏]
- 单集长度：[60 秒]，集数：[先做第 1 集]
- 台词语言：中文
- 已有素材：[无 / 有剧本 / 有角色设定图，路径…]

## 第一阶段：风格圣经（不生成视频）
1. 读对应的风格档案，产出《风格圣经》一页：全局风格锁句（逐字固定）、调色、镜头习惯、灯光习惯、正向约束句。写进 project/style.md。
2. 用 prompts/01_outline_system.md 从一句话故事生成分集大纲、角色表（identity_phrase 要写进风格锁的画风，例如 anime 角色不要写 "photoreal"）、场景表。给我确认。

## 第二阶段：资产库（图像模型，不用 H3）
3. 每个角色用风格档案里的定妆图模板出 3 张（正面半身、3/4 侧、全身），同一画风、同一光线、同一服装；用 Qwen‑Image‑2.1 或 Krea2 文生图，多视角用 Qwen‑Image‑Edit「人物多视角」工作流。每个角色出 2 轮候选，我挑。
4. 每个场景 1 张无人场景图，画风与角色一致；关键道具 1 张白底图。
5. 全部跑 pipeline/catalog.py build 建目录；把路径填进分镜 JSON 的 characters / scenes / props。
6. 做一张联络表（所有定妆图拼在一起）给我看画风是否统一。画风不统一就重做，不进下一步。

## 第三阶段：分镜
7. 用 prompts/02_storyboard_system.md 生成分镜 JSON：段落 6–12 秒、一镜一人开口、每段 continuity / end_state 必填、人物用 {资产id} 占位、风格字段填风格锁句。
8. 跑 run_episode.py --dry-run 和 catalog.py check，把 s01 和最关键的一段提示词全文给我看。
9. 为每段的每个子镜头出一张分镜图（I2VA 首帧或 multiframe 钉帧用）：用角色定妆图 + 场景图做参考，Qwen‑Image‑Edit 出图，画风锁定。

## 第四阶段：生成
10. 抽卡：workflows/official/video_minimax_h3_r2v.json 开 Lightning（4 步）或 lightx2v ref2v，768p 版 LoRA，shift 6/3，每段 3 候选，seed 随机。关键逻辑段用 workflows/official/video_minimax_h3_multiframe_reference.json，把分镜图按子镜头起始秒钉进去。
11. 我挑选后，固定 seed 换 8 步重跑；电影质感的脸部特写段过一遍导演台二采（workflows/director/minimax_h3_director_二采_加速.json 的 Refine 配置）；漫剧按需。
12. 段落衔接用 workflows/official/video_minimax_h3_i2v_continuation.json（上一段尾帧作首帧）。

## 第五阶段：成片与验收
13. pipeline/stitch.py 拼接、烧字幕、导出 CRF 16；按 docs/reviews 的方法做抽帧联络表、whisper 转写、分段清晰度，连同 test-log 一起交给我。

## 规则
- 风格锁句和角色 identity_phrase 一旦确认，整部剧逐字复用，不得改写。
- 所有参考图必须同一画风，不混真人照片与动画图。
- 否定句改正向约束（"恰好两个人在场" 而不是 "没有其他人"）。
- 每个阶段先给我看，确认后再花显卡时间；抽卡阶段每段不超过 3 次。
- 不下载大于 5GB 的文件，不用云端 API。
```
