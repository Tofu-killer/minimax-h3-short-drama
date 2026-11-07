# 05 · 让本地 agent 安装并使用 skill（发给 Claude Code / Codex 的提示词）

把下面整段发给本地 agent：

```
请先安装并阅读这个 skill，然后再接管我的 H3 工作流：

1. 安装：
   npx skills add https://github.com/Tofu-killer/minimax-h3-short-drama --skill minimax-h3-comfyui-short-drama
   （或 git clone 后把 skills/minimax-h3-comfyui-short-drama 拷到你的 skills 目录）
2. 完整读 SKILL.md，按它的「总流程」第 0 步先盘点我的环境（用 assets/local-inventory-checklist.md），把结果写成 logs/environment-report.md 给我看。
3. 之后每一步都按 skill 的 references 执行：选加速档位（references/local-stack-and-acceleration.md）、写分镜 JSON 并用 scripts/validate_episode.py 校验、用 scripts/build_prompts.py 生成提示词、scripts/lint_prompt.py 机检、scripts/comfy_submit.py 提交抽卡、scripts/qc_probe.py 与 contact_sheet.sh 做 QC。
4. 会花 GPU 时间的步骤前先给我一张选择卡（推荐项放第一）；我说「继续」就选推荐。
5. 第一步只做 1 段 10 秒样片（主角正脸 + 一句中文对白 + 一次有动机运镜 + 手部道具），通过 QC 后再扩到 30 秒、60 秒。
6. 遇到 skill 里没写的情况，先查 references/ecosystem-map.md 和 docs/13-github-survey/，再决定装什么节点；不要装 references/pitfalls.md 禁忌清单里的东西。
```
