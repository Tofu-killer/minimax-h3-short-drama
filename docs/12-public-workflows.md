# 12 · 公开 H3 工作流盘点：哪些真的好用

> 调研日期 2026‑10‑31。方法：克隆带工作流 JSON 的仓库，用脚本解析每个节点与参数（不是看标题）；RunningHub / RunComfy / Comfy Hub 只能读页面文字。能下载且许可允许的 JSON 已原样收进本仓库 `workflows/`（见 `workflows/NOTICE.md`）。

## 1. 结论：按用途推荐

| 用途 | 首选 | 备选 | 理由 |
|------|------|------|------|
| **短剧标准段落（多参考 + 对白）** | `official/video_minimax_h3_r2v.json` | 导演台 `director/minimax_h3_director_r2v.json` | 官方维护、节点最少（29）、带 Lightning 开关；导演台多了时间轴和段间引导，但是一个大节点，程序化改参数要走导演包 |
| **按子镜头钉关键帧（分镜图 → 视频）** | `official/video_minimax_h3_multiframe_reference.json` | — | ref2va + 3 个 `MiniMaxH3AddGuide`，把分镜图钉在第 1.5 / 3 / 5 秒；这是解决「没逻辑」最直接的工具 |
| **段落衔接（上一段尾帧 → 下一段）** | `official/video_minimax_h3_i2v_continuation.json` | Multishot `context_pin` | 官方做法就是 I2V 首帧 = 上段尾帧；Multishot 钉 22 帧 latent 更连贯但依赖第三方包 |
| **二采 / 放大成片** | 导演台 `director/minimax_h3_director_二采_加速.json` | RunComfy Dual‑Sampling（需登录下载） | 一采 ref2va 4 步 → Refine `upscale` 用 `h3_latent_upscaler_3d` 到 1920×1088 再 3 步 beta 精修 |
| **抽卡草稿（最快）** | `lightx2v/video_minimax_h3_ref2v_lightx2v_turbo.json` | 官方 r2v 开 Lightning | 4 步 Euler simple，26 节点，lightx2v 官方示例 |
| **首帧 / 首尾帧** | `official/video_minimax_h3_i2v.json`（首尾帧接 `last_frame` 口） | `director/minimax_h3_director_fl2v.json` | 官方模板默认 1:1 0.4MP，要改 ResolutionSelector |
| **长链连续多镜** | `multishot/H3_Seamless_Chain_CORE.json` | 导演台时间轴 | CORE 版不依赖第三方包；完整版 Extend_Take 需要 Motion‑Context、RES4LYF、sol‑attn |
| **姿态 / 动作控制** | `official/video_minimax_h3_fun_controlnet_union.json`（未收录，46 节点，需 RT‑DETR + SDPose） | — | 打戏或舞蹈迁移用，短剧文戏用不上 |

**不推荐**：RunningHub 上的「多模态参考生视频」应用页显示近期成功率 34%、平均 409 秒；B 站各家整合包里的工作流基本是上述几套的改皮，且只能网盘下载。

## 2. 官方模板（Comfy‑Org/workflow_templates，MIT）逐个参数

共 10 个 H3 原生模板（另有 10 个 `api_minimax_h3_*` 云端 API 节点模板，不适用本地）。

| 文件 | 任务 | UNET | 采样 | 步数 | LoRA | 分辨率 / 帧 | 备注 |
|------|------|------|------|------|------|-------------|------|
| `video_minimax_h3_t2v` | T2V | fl2va int8_convrot | res_multistep + simple | 20（Lightning 开 → 6/8） | fl2v_turbo_8step_v1.0 | 1344×768，`max(5,round(s*24))+(5-…%17)%17` 帧网格 | 子图封装，`Boolean (Enable Lightning LoRA)` 切换 |
| `video_minimax_h3_i2v` | I2V / FL2V | fl2va | 同上 | 20 / 8 | 同上 | 默认 1:1 0.4MP（要改） | `last_frame` 口接图即首尾帧；首帧会被拉伸到画幅、尾帧中心裁 |
| `video_minimax_h3_i2v_continuation` | 续写 | fl2va | 同上 | 20 / 6 | 同上 | 同上 | 与 i2v 同图，只是把上一段尾帧当首帧，官方认可的衔接法 |
| `video_minimax_h3_r2v` | Ref2VA | ref2va int8_convrot | res_multistep + simple | 20（Lightning 开 → 4） | ref2v_turbo_4step_v0.1 | 1344×768 / 124 帧，`ref_image_size=match` | 提示词用 `subject_definitions:` 六段式 |
| `video_minimax_h3_multiframe_reference` | Ref2VA + 关键帧 | ref2va | 同上 | 20 / 4 | 同上 | 同上 | 3 个 `MiniMaxH3AddGuide(frame_idx=round(sec*24))` 钉第 1.5 / 3 / 5 秒的图，「Follow the same pattern to add more」 |
| `video_minimax_h3_fun_controlnet_union` | Ref2VA + ControlNet | ref2va + `MiniMaxH3FunControlNetApply` | 同上 | 20 / 4 | 同上 | 同上 | 需 RT‑DETR 检测 + SDPose 关键点，46 节点 |
| `video_fasth3_ominiref_r2v` | Ref2VA（FastVideo 蒸馏整模） | `fasth3_omniref_8step_pruned_int8_convrot` | Euler + simple | 8 | 无（整模已蒸馏） | 1344×768 / 124，shift 12/3 | 需 `BlockSparseAttention` 后端；另有 fasth3 t2v / i2v |
| `video_pika_h3_flex_ref2va` | Ref2VA（Pika Flex LoRA） | ref2va | lcm + ManualSigmas `1,.973,.923,.8,.571,.333,0`（6 步） | 6 | `pika_h3_flex_ref2va_v1` | 1344×768 / 124 | 2 天前新增，另有 fl2va / t2v 版 |
| `image_minimax_h3_t2i` | 文生图 | — | — | — | — | — | 用 H3 出单帧，可当分镜图 |

官方模板没有写 `MiniMaxH3SigmaShift` 节点，shift 走节点默认；教程建议「参考必须保持时 20–25 步」，风格 LoRA 约 0.5。模型文件：UNET `*_pruned_int8_convrot`、CLIP `qwen3vl_32b_minimax_h3_nvfp4_awq`（type 必须 `minimax`）、video VAE **int8_convrot**（导演台与 lightx2v 用 fp16）、audio VAE fp32。

## 3. 导演台（AIMixer，Apache‑2.0）

| 文件 | 内容 |
|------|------|
| `minimax_h3_director_r2v.json` | 11 节点：UNET ref2va int8 + CLIP + 2 VAE → `MiniMaxH3Director`（内置时间轴、素材组、采样）→ CreateVideo/SaveVideo。默认 864×480、124 帧、seed randomize |
| `minimax_h3_director_加速版.json` | 同上 + `MiniMaxH3MemoryEfficientSageAttentionPatch`，243 帧（10 s），高级采样 20 步 res_multistep simple shift 12 |
| `minimax_h3_director_二采_加速.json` | **一采**：ref2va `pruned_w4a8_mixed` + fl2v_turbo_4step_v1.0_768p LoRA，864×480，367 帧（15 s），seed fixed 666；**二采**：`MiniMaxH3DirectorRefine` mode=`upscale`、`h3_latent` 用 `minimax_h3_latent_upscaler_3d_bf16`、Euler、目标 1920×1088、refine 模型 fl2va int8 + fl2v_turbo_8step_v1.0 LoRA、`BasicScheduler beta 3 步 denoise 0.2`；两路都接 SageAttention |
| `minimax_h3_director_fl2v.json` / `t2v` / `v2v` / `rv2v` / `external_groups_*` | 其余任务型；`external_groups` 用外部 `Director Group` 节点喂素材，便于程序化 |

要点：导演台提示词直接用 `<Picture N>`；程序化驱动走导演包 `*.mmxpack.zip`；二采的「3 步 beta denoise 0.2」是很省时的精修配置，值得照搬到任何一采结果上。

## 4. lightx2v 官方示例（ModelTC/Minimax‑H3‑Turbo，Apache‑2.0）

| 文件 | 参数 |
|------|------|
| `video_minimax_h3_ref2v_lightx2v_turbo.json` | ref2va **bf16 全量** + ref2v_turbo_4step_v0.1，`BasicScheduler simple 4`，Euler，`MiniMaxH3SigmaShift 12/3`，1344×768 / 124，3 张参考图，`match` |
| `video_minimax_h3_i2v_lightx2v_turbo.json` | fl2va int8 + fl2v_turbo_8step_v1.0，simple 8，Euler，shift 12/3，1344×768 / 73 帧 |
| `video_minimax_h3_t2v_lightx2v_turbo.json` | 同 i2v 去掉首帧 |

注意示例仍用 544p 版 LoRA 和 shift 12；换 768p 版时把 shift 改 6。bf16 全量 ref2va 在 24 GB 上跑不动，改 int8_convrot。

## 5. Multishot（jlucasmcrell，MIT）

`H3_Seamless_Chain_CORE.json` 13 节点，只用自带节点（`H3ModelLoaderAny` / `H3ClipLoaderAny` / `H3LoraStack` / `H3StudioControls` / `H3MultishotSampler`），`---` 分隔多镜脚本，帧接力；`H3_Extend_Take.json` 58 节点，含 LLM 写作器（JoyEcho，Ollama）、参考视频、音色锚、sol‑attn / chunk FFN（默认旁路），依赖多；`H3_Keyframes.json` 用 `H3Keyframes` 节点在 0 / 0.5 / 1 位置钉三张关键帧，20 步 res_multistep——和官方 multiframe 是同一思路的第三方实现。

## 6. 第三方平台（只读到页面）

| 平台 | 工作流 | 可得信息 |
|------|--------|----------|
| RunComfy | MiniMax H3 Dual‑Sampling R2V | `SplitSigmas` 把调度拆两段：低 sigma 一采定布局与身份，latent 轻放大，高 sigma 二采锐化；rgthree LoRA 栈 + SageAttention + UniBlockSwap；页面不给任何数值，下载需登录 |
| RunComfy | 4‑Step Reference‑to‑Video | 即 lightx2v ref2v 示例 + KJNodes/VHS |
| RunningHub | 导演台全能工作流（AI搅拌手） | 即 `director/*`，27.5K 浏览、911 收藏 |
| RunningHub | 多模态参考生视频（Little Wrangler） | 1583 次运行，成功率 34%，平均 409 s，无说明 |
| Comfy Hub | Minimax H3 Video Restyling | 未读 |

## 7. 对本项目的落地

1. **抽卡**：`official/video_minimax_h3_r2v.json` 开 Lightning（4 步）或 `lightx2v/ref2v`，换 768p LoRA + shift 6。
2. **逻辑控制**：`official/video_minimax_h3_multiframe_reference.json`，每个子镜头的分镜图按 `round(start*24)` 钉进去，再加角色参考图。这比纯文字描述位置可靠一个量级。
3. **衔接**：`official/video_minimax_h3_i2v_continuation.json`，首帧 = 上段最后一帧（`ffmpeg -sseof -0.05`）。
4. **成片**：中选段按导演台二采配置精修（latent 3D 放大 → 3 步 beta denoise 0.2）。
5. 这四个 JSON 都是 UI 格式，程序化调用前在前端「导出（API）」一次，节点 id 记进 `pipeline/local/workflows/README.md`。
