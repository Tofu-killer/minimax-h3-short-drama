# 第一次在这台机器上跑：按顺序验证的 12 件事

> 这个 skill 里的做法有三种来历：读源码和官方模板得出的、在一台真实的 ComfyUI 0.37.2 上验证过接线但**没有显卡、没采样过**的（附带的工作流都属于这一类）、别人机器上的数据。第一次开工时照这张表从便宜到贵各验一次，把结果记进项目里的 `logs/machine-notes.md`（模板在文末），以后就用自己机器的数，不用再猜。每一项只改一个变量；要对比的两条用同一段、同一个 seed（计时用 seed+1，避免命中 ComfyUI 的结果缓存）。
>
> 下面 `W` = `<skill>/assets/workflows`；命令都在项目根目录下跑，先 `--dry-run` 看预览，再带 `--confirm <批次号>` 提交。

| # | 做什么 | 看什么 | 结果决定什么 |
|---|--------|--------|--------------|
| 1 | `scripts/selfcheck.py`；照 `local-inventory-checklist.md` 盘点环境 | 自检全过；ffmpeg、可选依赖、中文字体都在 | 后期链路能不能用；缺什么先装（`local-stack-and-acceleration.md` §0b） |
| 2 | **连通测试，不用模型**：`comfy_submit.py $W/selftest_no_model.api.json --set 1.image=@任意一张图.png --out takes/selftest --poll 2` | 几秒后 `takes/selftest/` 里有一个 2 s 的 mp4 | 脚本连得上 ComfyUI、能上传和取回文件；连不上先查地址 / 端口（`--server`） |
| 3 | **官方模板原样跑一次**：在 ComfyUI 界面打开模板 `video_minimax_h3_r2v`，不改任何东西直接运行（模板自带示例图和提示词；默认 864×480、5 s、20 步） | 出得来、有声音；记下这一条的耗时（含冷启动） | 模型文件都放对了；这台机器跑通 H3 的最低门槛 |
| 4 | **预检附带的草稿工作流，不花 GPU**：`build_prompts.py <skill>/assets/episode.example.json --out prompts/_example --allow-planned`，再 `comfy_submit.py $W/h3_ref2va_sage.api.json --media prompts/_example/s01.media.json --dry-run` | 第二行是 `preflight ok`；预览里 1344×768、8 步、LoRA 文件名、Sage 两个节点都在；没有 advice | 草稿档要的文件和节点齐不齐——缺哪个，预检会点名并给出最接近的文件名。没装 Sage 就换 `h3_ref2va.api.json` |
| 5 | **出图**：`qwen21_t2i.api.json` 出一张定妆照；`qwen_edit2511_2ref.api.json` 出一张 1344×768 的首帧（命令见 `workflows/README.md`） | 出得来、尺寸对；每张耗时 | 生图阶段要多久；首帧的做法定稿 |
| 6 | **基线计时**：样片第一段的提示词做好后，把它的 `.txt` 和 `.media.json` 复制到 `logs/baseline/`，用草稿工作流连出两条（`--media logs/baseline/s01.media.json --tag baseline --out takes/baseline --batch 2 --log logs/takes.csv`） | 第二条的耗时（第一条含冷启动，不算数）；ComfyUI 控制台里的显存峰值 | 一条草稿到底要几分钟 → 每段抽几个 seed、一晚上能出多少；以后每开一个加速项都拿这份副本比 |
| 7 | Sage 的两条路各出一条：`h3_ref2va_sage.api.json`（KJNodes 两个节点）对 `h3_ref2va.api.json` + 启动参数 `--use-ck-attention` | 耗时；画面有没有差别 | 固定用哪一条（别叠）；精修要跟草稿用同一条 |
| 8 | 采样器：`euler`（附带工作流的默认）对 `--set 123.sampler_name=res_multistep`，都是 8 步 Turbo | 口型、细节、有没有拖影 | 草稿档的采样器 |
| 9 | 参考守不守得住：同一段出 3 个 seed | 脸、服装、道具是不是同一个；嗓音像不像样本 | 守不住时先按 `pitfalls.md` 查，再试这一段关 Turbo 出 20 步（`--set 146.value=false`） |
| 10 | 首帧：只当 `<Picture 1>`（默认）对加 `--anchor` 钉在第 0 帧 | 开场构图贴不贴首帧；脸有没有多出一个人；口型 | 带首帧的段默认加不加 `--anchor`；接上一段尾帧的段同样比一次 |
| 11 | 精修：中选的那条用 `h3_ref2va_sage_refine.api.json`（或不带 Sage 的那份）按同 seed 重跑，先 5 s 段、再 10 s 段 | 预览写着「same prompt and references as …」；出来是不是同一条片段；显存够不够；多花多久 | 10 s 以上的段能不能整段二采，还是要走分块（`quality-pipeline.md` §4） |
| 12 | 后期：对真实片段跑 `qc_probe.py` → `qc_dialogue.py` → `make_edl.py` → `retime_subtitles.py` → `mix_episode.py`，导出剪映草稿并打开 | 验收行 OK；字幕时间对；剪映里能打开 | 交付链路可用；切点对账在真实 H3 片段上准不准 |

用到 `i2va` / `fl2va` 的项目再加两项：`h3_fl2va.api.json` 出一条（FL2V v1.0 768p LoRA + shift 6 / 3，预览里应能看到 `MiniMaxH3SigmaShift … 6.0 / 3.0`、没有 advice；控制台应有 `208 patches attached`、没有 `ERROR lora`）；首帧比例故意差 5% 出一条，确认预览会提醒、画面确实被拉伸。

## `logs/machine-notes.md` 模板

```markdown
# 这台机器上的实测（日期、ComfyUI 版本、驱动、KJNodes / sageattention 版本）

| 项 | 条件 | 结果 | 结论 |
|----|------|------|------|
| 连通 | selftest_no_model | 通 / 不通 | … |
| 官方模板 | video_minimax_h3_r2v 原样，864×480 × 5 s × 20 步 | ___ s（含冷启动） | 模型齐全 |
| 草稿耗时 | h3_ref2va_sage：Ref2VA int8 + Turbo 8 步 v1.1 768p + Sage，1344×768 × ___ 帧（logs/baseline） | 第 2 条 ___ s，显存峰值 ___ GB | 每段抽 ___ 个 seed |
| Sage 路线 | KJ 节点 / --use-ck-attention | ___ s / ___ s | 用 ___ |
| 采样器 | euler / res_multistep | … | 用 ___ |
| 参考保持 | 3 个 seed | 脸 _/3、服装 _/3、嗓音 _/3 | … |
| 首帧 | 只当参考 / --anchor | … | 默认 ___ |
| 出图 | qwen21_t2i 定妆照 / qwen_edit2511_2ref 首帧 | ___ s / ___ s | … |
| 精修 | 5 s / 10 s，同 seed + H3 Hires Fix | 同一条？显存 ___ GB，+___ s | 10 s 以上：整段 / 分块 |
| 后期 | 真实片段全链路 | 验收 ___；剪映打开 ___ | … |
```

记下来之后，把和文档不一样的地方告诉用户，并在后续的批次预览、耗时估算里用这张表的数。
