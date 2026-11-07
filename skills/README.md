# Skills

本目录是把整个仓库的调研沉淀成的 **可安装 Agent Skill**（Claude Code / Codex / OpenCode / Cursor 等支持 `SKILL.md` 的 agent 都能用）。

| Skill | 用途 |
|-------|------|
| [`minimax-h3-comfyui-short-drama`](minimax-h3-comfyui-short-drama/SKILL.md) | 在本地 ComfyUI（单卡 24 GB 为基准）上用 MiniMax H3 从剧本做到成片：盘点环境 → 选加速组合 → 资产与角色卡 → 分镜分段 → 官方格式提示词 → 抽卡/精修/续接 → QC → 拼接。附 GitHub 生态地图与禁忌清单。 |

## 安装

```bash
# 用 vercel skills CLI（与 MiniMax 官方 skill 相同的安装方式）
npx skills add https://github.com/Tofu-killer/minimax-h3-short-drama --skill minimax-h3-comfyui-short-drama

# 或手动：把目录拷到 agent 的 skills 目录
cp -r skills/minimax-h3-comfyui-short-drama ~/.claude/skills/
```

## 结构

```
minimax-h3-comfyui-short-drama/
├── SKILL.md                 # 触发条件 + 总流程（<500 行）
├── references/              # 按需加载的深度资料
├── scripts/                 # 可直接运行的辅助脚本（校验分镜、提交 ComfyUI、QC）
├── assets/                  # 模板（分镜 JSON、提示词骨架）
└── evals/                   # 测试用例（prompt.md + case.yaml）
```

资料来源：`docs/13-github-survey/`（GitHub 全量调研）、`docs/01-12`（官方文档、API、社区经验）。
