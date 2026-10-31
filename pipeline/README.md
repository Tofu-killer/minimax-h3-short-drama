# pipeline/ · 参考实现

一套最小但完整的「分镜 JSON → H3 生成 → 质检 → 拼接」流水线，严格按 `docs/02-api-reference.md` 的官方契约实现。它不是产品，而是把 `docs/03` 的工作流落成可运行代码，方便验证与二次开发。

```
pipeline/
├── h3_client.py        # 官方 v2 API 异步客户端：创建 / Context-IR / 查询 / 2K 重生成 / 下载 / 回调；请求前本地校验组合规则
├── storyboard.py       # 分镜数据模型（Episode→Segment→Shot→Dialogue）与校验（时长、台词密度、一镜一人、运镜等）
├── prompt_builder.py   # 把 Segment 渲染成官方三段式 / 六段式提示词，并按顺序生成 content 数组与 <Picture N> 标签
├── run_episode.py      # 批量生成：并发、幂等 manifest、草稿/成片/2K 重生成三种模式、可选 IR 改写、成本预估
├── stitch.py           # ffprobe 技术 QC → 统一转码 → concat → 从分镜生成 SRT 并烧录 → 可选配乐 ducking
├── prompts/            # LLM Agent system prompt：大纲、分镜拆解、节奏审计
└── examples/episode01.json   # 3 段 30 秒示例集（Ref2VA ×2 + I2VA ×1）
```

## 使用

```bash
git clone https://github.com/Tofu-killer/minimax-h3-short-drama.git && cd minimax-h3-short-drama/pipeline
pip install -r requirements.txt
export MINIMAX_API_KEY=sk-...
# 国内站：export MINIMAX_API_BASE=https://api.minimaxi.com

# 0. 只生成提示词与请求体，不花钱
python run_episode.py examples/episode01.json --dry-run

# 1. 768P 草稿，每段 2 个候选，4 并发
python run_episode.py examples/episode01.json --mode draft --candidates 2 -c 4

# 2. 看 out/<ep>/clips/，挑选每段最佳 take，写 picks.json: {"s01": "<clip url>", ...}
#    然后 2K 重生成（$0.05/s）；或直接 --mode final 全 2K 生成
python run_episode.py examples/episode01.json --mode upscale --pick picks.json

# 3. 技术 QC + 拼接 + 字幕
python stitch.py examples/episode01.json --clips out/末班车_EP01/clips --out ep01.mp4 --music bgm.mp3
```

可选参数：`--use-ir` 先走 H3‑Context‑IR 改写（推荐在换新题材时打开，看看官方会怎么写）；`--callback-url` 用回调代替轮询；`--only s02 s03` 只重跑部分段。

## 分镜 JSON 要点

- 一个 `segment` = 一次生成（4–15 s），`shots` 为其内部子镜头，第一镜 `start` 必须为 0。
- `mode`: `ref2va`（默认，多参考图）| `i2va`（首帧）| `fl2va`（首尾帧）| `t2va`。
- 角色在 `action` 里用 `<Subject N>` 占位（N 为该段 `character_ids` 顺序）；`i2va/t2va` 模式下自动替换为「姓名 + 识别短语」。
- `identity_phrase` / `voice_phrase` 整季逐字复用。
- 校验器会拦住：时长越界、台词密度超标（字数 ÷ 4.5 + 2 s）、一镜多人开口、未知资产 ID、连续三段静态对话。

## 生成 JSON 的方式

把 `prompts/01_outline_system.md` 与 `02_storyboard_system.md` 作为任意 LLM（DeepSeek / GPT / Claude / 本地模型）的 system prompt，输入剧本即可得到符合 schema 的 `characters/scenes/segments`，再补上定妆图路径即可运行。

## 已知限制

- `video_regeneration` 的 `base_video` 角色在抓取到的 ContentItem 枚举中尚未出现，调用前请核对最新文档。
- 字幕时间码按子镜头跨度均分估算，精确对齐需用 ASR（如 whisper）对成片重新打轴。
- 未实现「取上一段尾帧作下一段首帧」的自动化，需手动用 `ffmpeg -sseof -0.1 -i clip.mp4 -frames:v 1 last.png` 抽帧后填入 `first_frame`。
