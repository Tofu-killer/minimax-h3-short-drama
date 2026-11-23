# 第一次在这台机器上跑：按顺序验证的 10 件事

> 这个 skill 里有不少做法是读源码、官方模板和别人机器上的数据得出来的，标着「没有在 4090 上实跑」。第一次开工时照这张表从便宜到贵各验一次，把结果记进项目里的 `logs/machine-notes.md`（模板在文末），以后就用自己机器的数，不用再猜。每一项只改一个变量；要对比的两条用同一段、同一个 seed（计时用 seed+1，避免命中 ComfyUI 的结果缓存）。

| # | 做什么 | 看什么 | 结果决定什么 |
|---|--------|--------|--------------|
| 1 | `scripts/selfcheck.py`；照 `local-inventory-checklist.md` 盘点环境 | 自检全过；ffmpeg、可选依赖、中文字体都在 | 后期链路能不能用；缺什么先装（`local-stack-and-acceleration.md` §0b） |
| 2 | 按 `comfyui-nodes.md` §3 做出 Ref2VA 草稿工作流，`comfy_submit.py … --dry-run` | 预览里参考的接线顺序、分辨率、步数都读得出来；没有 advice 报漏接（`vae` / `audio_vae`、LoRA 档位、shift） | 工作流改对了没有——这一步不花 GPU |
| 3 | **基线计时**：同一段 10 s 提示词连出两条（第一条含冷启动，不算数） | 第二条的耗时；ComfyUI 控制台里的显存峰值 | 一条草稿到底要几分钟 → 每段抽几个 seed、一晚上能出多少 |
| 4 | Sage 的两条路各出一条：KJNodes 两个节点 / 启动参数 `--use-ck-attention` | 耗时；画面有没有差别 | 固定用哪一条（别叠） |
| 5 | 采样器：`euler` 对 `res_multistep`，都是 8 步 Turbo | 口型、细节、有没有拖影 | 草稿档的采样器 |
| 6 | 参考守不守得住：同一段出 3 个 seed | 脸、服装、道具是不是同一个；嗓音像不像样本 | 守不住时先按 `pitfalls.md` 查接线，再试这一段 20–25 步不挂 Turbo |
| 7 | 首帧：只当 `<Picture 1>`（默认）对加 `--anchor` 钉在第 0 帧 | 开场构图贴不贴首帧；脸有没有多出一个人；口型 | 带首帧的段默认加不加 `--anchor`；接上一段尾帧的段同样比一次 |
| 8 | 出图：官方 Qwen-Image 2.1 模板出一张定妆照；Edit 2511 模板换成 1344×768 空 latent 出一张首帧（`image-stage.md` §1） | 出得来、尺寸对；每张耗时 | 生图阶段的时间；首帧工作流定稿 |
| 9 | 精修：选中的那条按同 seed 重跑接 `H3 Hires Fix`（`quality-pipeline.md` §4），先 5 s 段、再 10 s 段 | 是不是同一条片段；显存够不够；多花多久 | 10 s 以上的段能不能整段二采，还是要走分块 |
| 10 | 后期：对真实片段跑 `qc_probe.py` → `qc_dialogue.py` → `make_edl.py` → `retime_subtitles.py` → `mix_episode.py`，导出剪映草稿并打开 | 验收行 OK；字幕时间对；剪映里能打开 | 交付链路可用；切点对账在真实 H3 片段上准不准 |

用到 `i2va` / `fl2va` 的项目再加两项：FL2V 的 v1.2 LoRA 按默认 shift 12 / 3 出一条（`comfy_submit.py` 的预览不应报 shift）；首帧比例故意差 5% 出一条，确认预览会提醒、画面确实被拉伸。

## `logs/machine-notes.md` 模板

```markdown
# 这台机器上的实测（日期、ComfyUI 版本、驱动、KJNodes / sageattention 版本）

| 项 | 条件 | 结果 | 结论 |
|----|------|------|------|
| 草稿耗时 | Ref2VA int8 + Turbo 8 步 v1.1 768p + Sage，1344×768 × 243 帧 | 第 2 条 ___ s，显存峰值 ___ GB | 每段抽 ___ 个 seed |
| Sage 路线 | KJ 节点 / --use-ck-attention | ___ s / ___ s | 用 ___ |
| 采样器 | euler / res_multistep | … | 用 ___ |
| 参考保持 | 3 个 seed | 脸 _/3、服装 _/3、嗓音 _/3 | … |
| 首帧 | 只当参考 / --anchor | … | 默认 ___ |
| 出图 | Qwen 2.1 定妆照 / Edit 2511 首帧 | ___ s / ___ s | … |
| 精修 | 5 s / 10 s，同 seed + H3 Hires Fix | 同一条？显存 ___ GB，+___ s | 10 s 以上：整段 / 分块 |
| 后期 | 真实片段全链路 | 验收 ___；剪映打开 ___ | … |
```

记下来之后，把和文档不一样的地方告诉用户，并在后续的批次预览、耗时估算里用这张表的数。
