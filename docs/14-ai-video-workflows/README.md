# 14 · 现有 AI 视频工作流深度调研（走出 H3）

调研日期 2026-11-21。`docs/13-github-survey/` 只覆盖 MiniMax H3 相关仓库；本目录研究整个 AI 视频制作领域现有的工作流，提炼通用方法论、可移植到 H3 流水线的做法，以及 H3 做不好时该换什么工具。

| 文件 | 方向 | 状态 |
|------|------|------|
| [01-open-model-comfyui-workflows.md](01-open-model-comfyui-workflows.md) | 开源视频模型（Wan / LTX / HunyuanVideo 等）在 ComfyUI 里的标准工作流与通用模式 | 完成（2026-11-21） |
| [02-end-to-end-pipelines-and-agents.md](02-end-to-end-pipelines-and-agents.md) | 端到端 AI 短剧 / 影片自动化流水线与 agent 框架 | 完成（2026-11-21） |
| [03-commercial-models-and-creator-workflows.md](03-commercial-models-and-creator-workflows.md) | 商业 / 云端模型的提示词规范、能力边界与创作者实战工作流 | 完成（2026-11-21） |
| [04-audio-lipsync-and-post.md](04-audio-lipsync-and-post.md) | 配音、音色统一、口型、音效、配乐、字幕、剪辑自动化 | 完成（2026-11-21） |
| [05-consistency-and-storyboard-images.md](05-consistency-and-storyboard-images.md) | 角色 / 场景 / 风格一致性与分镜生图工作流 | 完成（2026-11-21） |
| [00-synthesis.md](00-synthesis.md) | 跨方向综合：通用方法论、模型分工表、对 skill 的改动清单、未做与待验证项 | 完成（2026-11-21）；**先读这一篇** |

五份报告都是文献与源码调研：没有在 RTX 4090 上实跑任何模型，也没有调用云端模型；实测过的只有据此新增的 skill 脚本（见综合篇 §4）。
