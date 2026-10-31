# 第二版制作手册：抽卡 → 选片 → 精修（本地 4090 + ComfyUI）

> 适用于《蜂医的复仇》EP01 重做。可直接交给本地 agent 执行；人工只做第 4 步和第 7 步的挑选。

## 0. 一次性准备（约 30 分钟）

1. 下载 lightx2v 768p 版 LoRA 到 `ComfyUI/models/loras/`：
   - `minimax_h3_ref2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors`（抽卡用）
   - `minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors`（成片用）
   - `minimax_h3_fl2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors`（首帧路线成片用）
2. NVIDIA 控制面板 → 管理 3D 设置 → CUDA 系统内存回退策略 → **首选无系统内存回退**。溢出会直接报错而不是悄悄变慢。
3. 资产目录化：
   ```
   python pipeline/catalog.py build "E:\AI\素材\三角洲素材\三角洲素材————\三角洲物品" --kind prop --out catalog_props.json
   python pipeline/catalog.py build "...\三角洲干员图" --kind character --out catalog_chars.json
   python pipeline/catalog.py build "...\三角洲场景" --kind scene --out catalog_scenes.json
   ```
4. 为蜂医、威龙各准备 2 张定妆图（正面半身 + 全身，脸要大、素底），办公室和大坝各 1 张无人场景图，红色物品 1 张白底图；全部放到 `pipeline/examples/assets/fengyi/`。

## 1. 分镜（用 `examples/fengyi_ep01.json` 为底）

1. 把占位图路径换成真实资产；`prop_red_loot` 换成目录里的真实物品 id 与名字。
2. 跑两道校验，全部通过才往下：
   ```
   python pipeline/run_episode.py examples/fengyi_ep01.json --dry-run
   python pipeline/catalog.py check examples/fengyi_ep01.json --catalog catalog_props.json
   ```
3. 打开 `out/.../prompts/s04.txt` 逐句读一遍：每个镜头是否写了「起始 → 变化 → 结束」、人物左右位置、谁开口谁闭嘴、道具是 `<Subject N>` 而不是形容词。

## 2. 基准测试（只做一次，约 20 分钟）

同一提示词、同一 seed（固定 42）、s02 段，跑四次，记录耗时与主体清晰度：

| 编号 | 分辨率 | LoRA | 步数 | shift 视频/音频 |
|------|--------|------|------|-----------------|
| T1 | 864×480 | ref2v 4step v0.1（旧） | 4 | 12 / 3 |
| T2 | 1344×768 | ref2v 4step v0.1（旧） | 4 | 12 / 3 |
| T3 | 1344×768 | ref2v 4step v1.0 768p | 4 | 6 / 3 |
| T4 | 1344×768 | ref2v 8step v1.1 768p | 8 | 6 / 3 |

判读：T2 比 T1 慢超过 5 倍 → 显存溢出，先解决再继续；T3 比 T2 清楚 → 错配是主因；T4 比 T3 清楚 → 步数有份。清晰度用 `docs/reviews` 里的拉普拉斯方差脚本算主体区域。

## 3. 抽卡（草稿）

- 配置：1344×768（或 864×480 更快）、ref2v **4 步 v1.0 768p**、shift 6/3、Euler + simple、CFG 1、LoRA 强度 1.0、seed **randomize**。
- 每段生成 **3 个候选**：`run_episode_local.py --mode draft --candidates 3`（或导演台时间轴里同段跑三次）。
- 每段耗时目标：10 秒段 ≤ 5 分钟；超过就回第 2 步查溢出。

## 4. 选片（人工，每段 1 分钟）

只看四件事，不看画质：
1. 人物位置和朝向符合 `end_state`；
2. 道具是参考图里的那个；
3. 台词只念一次、是对的人在说；
4. 没有多出来的人或装备。
选中的候选记下 **seed**，写进 `picks.json`：`{"s04": {"file": "...", "seed": 1234567}}`。三个都不合格就改提示词（通常是动作写得不够具体或 continuity 没复述上一段），不要靠继续抽。

## 5. 精修（成片）

- 用选中的 seed **固定**，同提示词，换 ref2v **8 步 v1.1 768p**，shift 6/3，重跑一次。
- 脸部特写或拖影严重的段，再过一次二采：导演台 Refine `upscale` 模式（或 SeedVR2 目标短边 1080）。
- 大动作段只保留一个运镜，其余改 `The camera holds a static shot`。

## 6. 拼接与导出

- 先统一转码再 concat，检查边界帧不重复（上一版 34.1–34.6 s 的闪帧就是这里出的）。
- 字幕从分镜 JSON 生成烧录；稀有度颜色框按 catalog `rarity` 后期叠。
- 导出：1920×1080 或 1344×768 原生，24 fps，libx264 **CRF 16**，AAC 192k；不要用「small」低码率版交付。
- 响度：峰值 −1 dB，均值约 −16 LUFS。

## 7. 验收（用同一套工具）

```
ffprobe 参数核对 → 每 1.5 s 抽帧联络表 → whisper 转写对照台词 → 拉普拉斯方差分段清晰度
```
和上一版对比：拖影段主体清晰度应 ≥ 背景的 70%；台词全部被识别；无连续多刀切点。

## 8. 时间预算（4090，42 秒五段）

抽卡 5 段 × 3 候选 × 约 3 分钟 ≈ 45 分钟；精修 5 段 × 约 6 分钟 ≈ 30 分钟；二采 2 段 × 约 8 分钟；拼接 5 分钟。一集约 1.5 小时机器时间，人工挑选约 10 分钟。
