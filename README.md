# MiniMax H3 高清短剧制作 · 深度研究

> 系统整理「别人是如何用 MiniMax H3（海螺 3.0 / Hailuo 03）做竖屏短剧的」：模型能力、官方 API、端到端工作流、提示词方法论、一致性技术、开源项目剖析、社区经验，并附一套可运行的参考实现。
>
> 调研时间 2026‑10‑30。来源覆盖 MiniMax 官方文档与开源仓库、GitHub 上 10+ 个相关项目、X / B 站 / 公众号创作者经验、十余篇评测与提示词指南，全部列于 [`docs/08-sources.md`](docs/08-sources.md)。

## 结论先行

1. **H3 把短剧的生产单位从「镜头」变成了「段落」。** 一次生成 4–15 秒、内部可切 2–4 个镜头、原生对白 + 音效 + 立体声，正反打在同一上下文里完成。外挂 TTS 和对口型工具的旧流程可以去掉。
2. **一致性 = 定妆图库 + 职责分配 + 固定识别短语。** 模型不记得上一集；每段都要带同一组参考图（≤ 9 图 + 3 视频 + 3 音频），`<Picture 1>` 只管脸、`<Picture 2>` 只管服装、`<Picture 3>` 只管环境，角色描述一字不改地逐段复用。
3. **提示词按官方结构写最稳。** 三段式 `integrated_multimodal_description / overall_soundscape / non_diegetic_music`，参考模式用六段式；台词写 `角色 (S1) says: <d>[Chinese] 台词</d>`；镜头写 `[Shot 2] At 00:05.000, the shot cuts to …`；一镜一个运镜、一镜一人开口。
4. **成本结构：768P 草稿多候选 → 选片 → 2K 重生成。** 官方 2K $0.13/秒、768P $0.08/秒、重生成 $0.05/秒、音频免费。60 秒竖屏一集约 $8–13。
5. **弱项要在分镜阶段绕开**：动作偏慢、大幅运镜与特效镜头弱、精确文字不可靠（字幕后期烧）、视频续写空间连续性一般（用尾帧→首帧衔接代替）。

## 文档

| 文档 | 内容 |
|------|------|
| [01 模型总览](docs/01-model-overview.md) | 规格、变体（H3 / Highspeed / Lite / Max）、架构、定价、与 Seedance / Kling / Veo 的位置、各来源分歧 |
| [02 API 速查](docs/02-api-reference.md) | 官方 v2 接口完整字段、四种模式组合规则、媒体限制、示例、错误码、回调、Context‑IR、2K 重生成 |
| [03 端到端工作流](docs/03-production-workflow.md) | **核心**：剧本 → 资产 → 定妆图 → 分镜段落 → 首帧 → 提示词 → 批量生成 → QC → 拼接 → 交付，三条路线对比，失败对策 |
| [04 提示词工程](docs/04-prompt-engineering.md) | 官方三段式/六段式、标签体系、时间码、运镜词表、对白/旁白/跨镜头台词语法、短剧完整示例 |
| [05 一致性技术](docs/05-consistency.md) | 片段内 / 片段间 / 集间三层一致性，参考图规范，文字锁定，职责分配，衔接技术，声音一致性 |
| [06 开源项目剖析](docs/06-case-studies.md) | 火宝短剧、Hailuo‑AI‑Short‑Drama‑Studio、MiniMax‑H3‑Codex‑Drama、官方 skills、ComfyUI 生态、提示词生成器 |
| [07 社区经验](docs/07-community-insights.md) | X、B 站四个教程、公众号、英文评测的共识与弱点清单、平台差异 |
| [08 来源清单](docs/08-sources.md) | 全部阅读过的 URL |
| [10 B 站课程与「秋叶教程」笔记](docs/10-bilibili-h3-course-notes.md) | 辨析「秋叶」H3 课程的来源，提炼课程大纲，梳理导演台 / Multishot / 双采 / 去油 / 乱念台词等本地短剧生态的关键技术点 |
| [09 Toonflow 剖析](docs/09-toonflow-analysis.md) | 20k star 开源短剧平台的架构、13 步 skill、H3 供应商协议、ComfyUI 接入方式、MCP 接管路线，以及与本仓库的组合建议 |

## 参考实现与模板

```bash
git clone https://github.com/Tofu-killer/minimax-h3-short-drama.git
cd minimax-h3-short-drama
```

- [`pipeline/`](pipeline/README.md)：官方 API 异步客户端、分镜 JSON schema 与校验器、三段式/六段式提示词构建器、并发批量生成（草稿 / 成片 / 2K 重生成）、ffprobe QC + FFmpeg 拼接 + 自动字幕，附 LLM 编剧/分镜/节奏审计 Agent 的 system prompt 与 30 秒示例集。
  ```bash
  cd pipeline && pip install -r requirements.txt
  python run_episode.py examples/episode01.json --dry-run     # 不花钱，先看生成的提示词与请求体
  ```
- [`templates/`](templates/README.md)：可直接粘贴到海螺 App / ComfyUI / API 的提示词模板（T2VA、I2VA、FL2VA、Ref2VA、对白写法、制片人简报）。

## 工作流一览

```
剧本 ──► 分集剧本(LLM) ──► 资产提取 ──► 定妆图(正面/全身/场景/道具, 整季复用)
                                            │
分镜段落(8–15s, 2–4 子镜头, 台词≤字数/4.5+2s) ◄─┘
      │
      ▼
官方提示词(六段式 Ref2VA / 三段式 I2VA) ──► [可选] H3-Context-IR 改写
      │
      ▼
批量生成 768P ×2 候选 ──► 选片 ──► 2K 重生成 ──► 技术 QC(ffprobe) + 视觉 QC(联络表)
      │
      ▼
FFmpeg 统一转码 → concat → 烧字幕 → 配乐 → 1080×1920 成片
```

## 许可

本仓库内容采用 [MIT License](LICENSE)。文档中引用的开源项目各有其许可证（火宝短剧为 CC BY‑NC‑SA 4.0 禁止商用，其余多为 MIT），复用其代码或提示词前请核对。
