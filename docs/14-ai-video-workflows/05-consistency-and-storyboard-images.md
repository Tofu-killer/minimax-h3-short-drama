# 05 · 角色 / 场景 / 风格一致性与分镜生图工作流（整个 AI 影像生态，不限 H3）

> 调研日期 **2026-11-21**。方法：GitHub 搜索 API（按星排序，关键词见各节）+ HuggingFace API（作者 / base_model 适配器 / 模型卡 / 讨论区）+ `Comfy-Org/workflow_templates` 的 `templates/index.json`（HEAD，776 个模板，其中 49 个晚于本地 10-31 克隆）+ ComfyUI 源码（`v0.37.2 … v0.46.2` 各 tag 的 `comfy_extras/nodes_qwen.py`、`nodes_minimax_h3.py`、`comfy_api_nodes/*.py`）+ 36 个仓库 README / 文档 + 2 个仓库浅克隆（VNCCS）。
> 工作流 JSON 用 `wf/analyze.py` 拆节点，共 **58 个**（Comfy 官方模板 42 + 社区 16：HF 模型仓库自带工作流 11、VNCCS 5），其中有代表性的 24 个写进 §2；`analyze.py` 的关注节点表偏 H3，提示词与接线另用自写的 `dump.py` / `brief.py` 补读。
> 口径：「源码」= 我直接读到的节点源码 / 模板 JSON；「模型卡」= 作者自述；「单机实测」= 只有一位作者一台机器的数字，硬件照抄；「未验证」= 没有任何人在 4090 上跑过或我只看到机制没看到结果。**本簇没有在 4090 上实跑任何模型。**
> 与已有资料的关系：`skills/…/references/image-stage.md`（下称「现方案」）已覆盖 Qwen-Image 2.1 / Edit-2511 / Z-Image / Krea 2 的选型、版式与提示词，本文不重复，只补缺、纠错（§6 逐条）。

## 本簇结论（12 行）

1. **主流做法已从「身份适配器」换成「一张锚点图 + 编辑 / 多参考模型逐张派生」**。PuLID / InstantID / InfiniteYou / UNO / USO / EasyControl / ACE++ 的官方仓库最后推送全部停在 2024-07 – 2025-09（GitHub API），新基座上只有零星移植（PuLID-Flux2 ★128）；2026 年的增量几乎都是编辑模型 + 编辑 LoRA。
2. **2026-11 实际可用（已核实）**：Qwen-Image-Edit-2511（Apache-2.0，仍是可商用里身份保持 + LoRA 生态最全的）、Qwen-Image 2.1（10 图、研究许可、LoRA 增长最快）、FLUX.2 Klein 9B/4B、**FLUX 3 Image Klein（10-13）**、Krea 2 + Identity Edit V2、**MiniMax-H3-Image（11-03，33B、16 图、16 MP）**、P-H3-Image、Anima、MOSS-Image 等 20 余个；**Z-Image-Edit / Omni 仍未发布**（模型卡写 To be released，Tongyi-MAI 组织下只有 Z-Image 与 Turbo）。
3. **MiniMax-H3-Image 文生图强、带身份的编辑弱**：发布一周内 4 位独立用户报告「编辑后不像参考人」「两人合成有一张脸变样」，H3 视频底模取单帧反而更像（HF 讨论区 11-10/11）。它适合场景 / 道具 / 分镜板，不适合替代 Edit-2511 出人物首帧。
4. **谁做得最好**：一致性流水线 = VNCCS（★1780，角色 → 姿势 → 服装 → 表情全链，3D 假人驱动姿势）；资产纪律 = shuohao-skills（★6899，单根锚点 + 冻结 + 过期标记 + 代码门禁）；训练 = Fizgig（★785，Windows 一键，十余个基座，AdaFace 实时相似度）。
5. **云端**：Seedream 5.5 / Nano Banana 2.1·Pro / GPT Image 2.6 / Kling 4.0 Image 都是 10–16 张参考、$0.03–0.16 / 张；值得花钱的只有三种情况（§5.4）。
6. 对我们最有用的 5 件事：① 锚点单根、派生图只参考锚点、冻结三样 + 过期标记（shuohao）；② 同场多机位用 Multiple-Angles LoRA 从同一底图转机位，而不是重新生成；③ 改姿势靠 3D 假人 / 深度参考图，不靠文字；④ 身份门禁按「真人 / 动漫」分轨（SFace·AdaFace / DINOv2·CCIP）并用每套数据自己的围栏；⑤ 脸漂了用 head-swap LoRA 修，不重抽。

## 0. 2026-11 实际可用的模型与版本（先确认，不假设）

### 0.1 本地开放权重：编辑 / 多参考 / 文生图

发布日取 HF `createdAt`；采样取 Comfy 官方模板；许可取 HF `cardData`（2026-11-21 抓取）。

| 模型 | 发布 | 规模 | 参考图上限（来源） | 官方模板采样 | 24 GB 用的文件（HF 大小） | 许可 | 身份保持的证据 |
|------|------|------|------------------|-------------|--------------------------|------|----------------|
| **Qwen-Image-Edit-2511** | 2025-12-17 | 20B | **3**（`TextEncodeQwenImageEditPlus` 只有 image1–3；视觉编码器看 384² 面积、VAE 参考 1 MP，源码 v0.46.2） | AuraFlow 3.1 → CFGNorm 1 → euler/simple，Comfy 20 步 / Qwen 40 步、CFG 4；Lightning 4 步 CFG 1 | `qwen_image_edit_2511_fp8mixed` 20.53 GB 或 `_int8_convrot` 20.50 GB | Apache-2.0 | 模型卡称改进多人一致；mathruffian 2 人实测可行（现方案） |
| **Qwen-Image 2.1** / Turbo | 2026-09-14 / 10-09 | 7B DiT | **10**（模型卡；节点留了 16 槽）；**image_1 是被编辑的图，其余是参考**，画布跟随 image_1 | 25 步 CFG 1（官方管线 40–50）；Turbo 8 步 ManualSigmas | `qwen_image_2.1_int8_convrot` 7.26 + `qwen3vl_8b_int8_convrot` 9.35 GB | qwen-research（非商用） | 不给姿势参考时锁成参考姿势（现方案）；改画风时整图漂移中位 24 px（ausboss 实测） |
| **MiniMax-H3-Image** | 2026-11-03（Comfy 模板 11-10） | 33.1B，H3 去音频层 | **16**（模型卡；节点上限 100）；`<Picture N>`，image_1 是被编辑图 | 6 步 CFG 1 euler/simple，默认 2048²，工作区间 4–20 MP | `minimax_h3_image_pruned_int8_convrot` 20.98 GB + **H3 同一个文本编码器** + `minimax_h3_image_vae_fp16` 1.17 GB | H3-Image 社区许可（年收入 ≤ 100 万美元；排除欧盟 / 英 / 韩 / 美） | **弱**：4 位用户独立报告（§3.3） |
| P-H3-Image（Pruna） | 2026-10-28 | H3 fl2va + 2 GB LoRA | 节点 image_1–9（模型卡写 8） | **er_sde** + 8 步 ManualSigmas，`MiniMaxH3SigmaShift` 1/1 | fl2va int8 + `p-h3-image_lora_bf16` | H3 社区许可 | 讨论区称编辑比 H3-Image 稳（1 人，未量化） |
| FLUX.2 Klein 9B / 4B | 2026-01-14 | 9B / 4B | `ReferenceLatent` 链（官方模板接 2–4 张） | 蒸馏版 4 步 CFG 1；base 20 步 CFG 5 | `flux-2-klein-9b-fp8` ≈ 9 GB + `qwen_3_8b_fp8mixed` | 9B 非商用 / **4B Apache-2.0** | dx8152 Consistency LoRA（508 赞）专修它的一致性 |
| **FLUX 3 Image Klein** | 2026-10-13 | 5.6B | `ReferenceMultiLatent`，`<ref_image_N>` + 框选 `<obj_N>` | 蒸馏 16 步 CFG 1；base 50 步 | `flux3-image-klein-int8-convrot`（全套 10.7 GB，lifeidle） | FLUX Kommunity（年收入 < 500 万美元可商用，VentureBeat 二手） | 无人测身份；1024² 15 步 6.8 s（24 GB 笔记本 5090，单机） |
| Krea 2 + **Identity Edit V2** | 2026-06-18 / V2 | 12.9B | 2（场景 + 人物） | Turbo 8 步 CFG 1，`ref_boost` 2、`grounding_px` 768 | `krea2_turbo_int8_convrot` 13.49 GB + `krea2_identity_edit_v2_r128` 0.91 GB | Krea 社区（公司收入 < 100 万美元）+ Identity Edit 自己的非商用许可 | 作者：照片可重摆；saya：二次元立绘「只会复制源图」（16 GB 实测） |
| Z-Image / Z-Image-Turbo | 2026-01-23 / 2025-11-25 | 6B | 无参考输入；Fun ControlNet Union 2.1 | Turbo：**res_multistep**/simple 8 步 CFG 1，AuraFlow 3 | `z_image_turbo_int8_convrot` 6.20 GB | Apache-2.0 | **Edit / Omni 未发布** |
| Anima（2D 动漫） | 2026-01-29（Base v1.0 05-20） | 2B | 无；LLLite 控制、社区 IP-Adapter | 30 步 CFG 4 euler/simple；Turbo LoRA 8–12 步 CFG 1 | `anima-base-v1.0` 4.2 GB | 模型非商用，**输出可商用**（LICENSE §2e） | — |
| HiDream-O1 / OmniGen2 / MOSS-Image | 2026-05 / 2025-06 / 2026-10 | 8B / — / 5B | 多参考主体驱动 / in-context / 编辑 LoRA + 框布局 + 颜色深度控制 | 40 步 / 20 步双 CFG 5·2 / 25–50 步 | 见模板 | MIT / Apache / Apache | 无身份实测，本轮未深读 |
| 其余编辑模型 | 2026-02 – 10 | — | Mage-Flow ≤ 3，其余单图 | — | — | Fibo 2.0 CC-BY-NC；Boogu / JoyAI / FireRed 1.1 Apache；Mage-Flow MIT | 仅确认存在与许可 |

- 版本线索：ComfyUI 当前最新 tag **v0.46.2**；`TextEncodeQwenImage21` 自 v0.37.2 起就有；**`PH3ImageConditioning` 自 v0.44.0、`MiniMaxH3ImageConditioning` 自 v0.45.0**（逐 tag 取源码核对）。
- 文本编码器复用：H3-Image 用 `Comfy-Org/MiniMax-H3` 里的 `qwen3vl_32b_minimax_h3_*`（模板注释），已经装了 H3 的机器只多下 22 GB。
- 量化：Kijai 在讨论区给的口径是 int8_convrot 权重误差 < 1%、w4a8 约 7%，「ComfyUI 有异步卸载，小权重不省时间，只有内存不够才用 w4a8」。

### 0.2 云端（Comfy partner 节点价签，v0.46.2 源码；含 Comfy 的加价）

| 模型 | 模板日期 | 参考上限 | 价格 / 张 | 备注 |
|------|---------|---------|-----------|------|
| Seedream 5.5 | 2026-11-09 | 10（生成数 + 参考数 ≤ 15） | $0.029（≤ 2.6 MP）/ $0.050，另加 $0.011 × 参考图数 | 输出跟随源图分辨率 |
| Seedream 5.0 Pro | 2026-07-08 | 10 | $0.045（1K）/ $0.09（2K） | img.ly 纯文字一致性榜第 1（4.86 / 5，26 个模型各 9 次，无参考图，日期未标） |
| Nano Banana 2.1 | 2026-10-06 | 14 | $0.048 / $0.072 / $0.162（1K / 2K / 4K），thinking 另加 ≤ $0.018 | Comfy 模板描述「多轮修图保持主体与文字」 |
| Nano Banana Pro（Gemini 3 Pro Image） | 2025-11-21 | 14 | $0.161（1K、2K）/ $0.288（4K） | Comfy「Character & Fashion」分类 28 个模板里 13 个用它（Nano Banana / Gemini 系合计 16 个，Qwen-Image-Edit 5 个） |
| GPT Image 2.6 Flare / Sunburst | 2026-11-05 | 16 | 2048×1152：low $0.028 / medium $0.052 / high $0.061，另加 $0.012–0.018 × 参考图 | 最高 3840×2160 |
| Kling 4.0 Image | 2026-11-17 | 10（`@Image1`） | 未取到 | 最高 8K，「一致的系列图」 |
| FLUX 3 Image（API）/ Qwen Image 3.0 Pro / MiniMax-H3-Image API | 10-01 / 08-06 / 11-10 | 10 / 多图 / 16 | 未取到 | Qwen 3.0 Pro 只有 API |
| Midjourney | — | V7 Omni Reference 1 张、2× GPU 时间（官方文档）；V8.2 Edit Model ≤ 4 张（二手） | 订阅制 | **无官方 API**，流水线里跳过 |

## 1. 工作流图谱（7 条有代表性的完整链路）

```
A 单根锚点 → 派生视图 → 代码拼板（shuohao character-refs；VNCCS 同构）
  角色描述（拆成 身份 / 脸 / 发 / 体型 / 肤 / 上装 / 下装 / 细节，标来源：明说 / 推断 / 默认）
   → ① 文生图：正面全身锚点（唯一一次文生图；Qwen 2.1 25–50 s / 张）→ 人确认 → 冻结（sha256）
   → ② 编辑模型「锚点 + 一句改图指令」：正脸大头照 / 90° 侧面 / 背面（默认档）
   → ③ 按需：细节特写 ≤ 8 张（发饰 / 领口 / 袖口 / 鞋，额外挂大头照）、45° 大头照
   → ④ 门禁（边长 300–5760、宽高比 0.4–2.5、≤ 20 MB、四边白底、是否过期）→ asset.json + PNG 元数据
   → ⑤ 报告页用代码排成设定板（左大头 + 右正 / 侧 / 背 + 细节条）—— 板不是生成出来的
  输出：每视图一张单人图；给视频模型时挂「全身 + 大头照」

B 同一底图多机位 → 逐镜首帧（Comfy 官方「1 Click Multiple Character / Scene Angles」）
  一张定稿首帧或场景母版
   → Qwen-Image-Edit-2511 + Multiple-Angles LoRA（1.0；fal 版建议 0.9）
   → 8 个子图各一条机位指令（Rotate the camera 45 degrees to the left. / Turn the camera to a close-up. …）
     或 fal 96 机位语法 `<sks> front-right quarter view eye-level shot medium shot`
   → 4 步 Lightning CFG 1（抽）或 40 步 CFG 4（定）→ 身份门禁 → 该镜首帧 → I2V / FL2V

C 3D 预演 → 转绘（VNCCS Pose Studio；AnyAngle；PoseAtlas）
  3D 假人（年龄 / 体型 / 身高滑杆，Mixamo FBX 可导入）摆姿势 + 取景 + 打光 → 渲染图
   → Qwen-Image 2.1：image 1 = 姿势渲染、image 2 = 角色，
     提示词 `replace the pose of <image 2> with the pose of <image 1>. keep the character of <image 2>`
     + `VNCCS_QI2_PoseStudio` LoRA 1.0，25 步 CFG 1 euler/simple
  场景同理：锚点图 → TripoSplat / TRELLIS.2 → Blender 摆机位渲粗图
   → Qwen 2.1 + `QI2.1_AnyAngle` LoRA 1.0，`Change the camera angle from <image2> to <image1>.`，CFG 3、≥ 20 步

D 九宫格 → 选格 → 单格重绘 → 首尾帧视频（Comfy「3x3 Contact Sheet」「Contact Sheet Step 1–3」）
  参考图 + 一句主题 → Nano Banana 2 出 3×3 无边框 16:9 宫格（系统提示词规定 9 格各写机位）
   → 选一格 → 第二次调用「Focus ONLY on the {{VIEW}} tile. Recreate that exact image as a standalone full 16:9 …」
   → 8 张关键帧 → VLM（Gemini Flash Lite）逐对分析写运镜 → 7 段 Kling 3.0 首尾帧视频

E Next-Scene 链式分镜（lovis93 2509 版 → akhaliq Qwen 2.1 版）
  起始帧 → Qwen 2.1 + Next-Scene LoRA 0.7–0.9，28–40 步
   → `Next Scene: The camera pulls back to a wide shot, revealing …`（先写运镜，再写主体 / 光线变化）
   → 输出再喂回去 → 一串「同一世界、同一人」的分镜帧（链式输入先加轻微模糊去颗粒）

F 一张图自举角色 LoRA（lora-dataset-studio；dataset-deviser；Fizgig）
  1 张参考 → 编辑模型按变化目录出 ~24 张（角度 / 姿势 / 表情 / 光线 / 景别 / 服装 / 背景）
   → Look Consistency Filter（AdaFace / DINOv2 对 3 张基准打分，剔离群）→ 人脸特写 + 全身配对 → 字幕（Qwen3-VL / JoyCaption / WD 标签）
   → Fizgig 预设（rank 8–16、0.25–0.5 MP、30 epoch、训练适配器开）→ 每 epoch 同 seed 出图 + 相似度曲线 → 挑中段检查点

G 脸漂了就换头，不重抽（BFS head swap）
  已出好的首帧（构图 / 光线 / 姿势都对，脸不像）+ 角色大头照
   → Qwen 2.1 + `bfs_head_v1.1_qwen_2.1` 1.0 + 8 步（或 2511 + `bfs_head_v5_2511…rank_16` 20 步 CFG 2.5）
   → `head_swap: start with <image1> as the base image, keeping its lighting, environment, and background. remove the head … replace it with the head from <image2> …`
   → 多人镜：SAM3 把要换的人涂成品红 → `bfs_body_swap_selective_magenta` 只换那一个人
```

## 2. 拆解的工作流 JSON（节点链与参数）

来源缩写：T = `Comfy-Org/workflow_templates/templates/`（本地克隆 10-31 + HEAD 11-21）；HF = 模型仓库自带；V = VNCCS 仓库。全部经 `analyze.py`。

| # | 工作流（来源） | 节点链 | 关键参数 |
|---|---------------|--------|---------|
| 1 | `image_qwen_image_edit_2511`（T） | UNETLoader → [Lightning LoRA 开关] → ModelSamplingAuraFlow → CFGNorm → KSampler；`TextEncodeQwenImageEditPlus`×2（正 / 负）→ `FluxKontextMultiReferenceLatentMethod`；`FluxKontextImageScale` → VAEEncode | shift 3.1、CFGNorm 1、`index_timestep_zero`；40 步 CFG 4（开 LoRA：4 步 CFG 1）；提示词用「image 1 / image 2」 |
| 2 | `templates-1_click_multiple_character_angles-v1.0`（T） | 同 #1 的子图 ×8，各挂 Multiple-Angles LoRA | LoRA 1.0；8 条机位句；默认开 4 步 LoRA |
| 3 | `template_rob_split_stack_qwen_multi_wan22`（T，313 节点） | `QwenMultiangleCameraNode`（方位 / 俯仰 / 距离）×5 → 2511 + 多角度 LoRA → 5 张起始帧 → Wan 2.2 I2V ×5 → RIFE → 竖排拼接 | 相机参数 (0,0,0)(90,0,5)(0,0,10)(0,−30,10)(0,50,5)；Wan 4 步 lightx2v |
| 4 | `image_qwen_image_2_1_image_edit`（T） | UNETLoader → `QwenImage21Cache` → KSampler；`TextEncodeQwenImage21`（prompt、resolution、image_1…）输出 conditioning + latent；可选 `TextGenerate` 提示词增强 | 25 步 CFG 1 euler/simple；`resolution`（参考图总像素预算）节点默认 1024，0 = 各参考保持原尺寸；`<image1>…<image10>` |
| 5 | `VNCCS_Utils PoseStudio QI2.1`（V） | `VNCCS_PoseStudio`（3D 假人 → IMAGE）+ LoadImage（角色）→ `TextEncodeQwenImage21` → KSampler | `VNCCS_QI2_PoseStudioV2` 1.0；Cache `gpu / int8`；25 步 CFG 1 |
| 6 | `VNCCS_Utils Pose Studio Klein9b`（V） | `VNCCS_PoseStudio` → `ReferenceLatent`×4 → CFGGuider → SamplerCustomAdvanced | `flux-2-klein-9b-fp8` + `VNCCS_PoseStudioKlein9b` 1.0；Flux2Scheduler 4 步、CFG 1 |
| 7 | `VNCCS_3.2_Step1_CharacterCloner` / `Step2_Clothes` / `Step3_Emotions`（V） | `VNCCS_ControlCenter`（下模型）→ `CharacterCloner` / `ClothesDesigner` / `EmotionGeneratorV2` → `VNCCS_PoseStudio` → 生成器节点 | 全部逻辑在自定义节点里；产物写 `output/VNCCS/Characters/<名>/{Sprites,Faces,Sheets}/<服装>/<表情>/` |
| 8 | `Head Swap V1 Qwen 2.1`（HF: BFS） | 身体图 + 头图 → `ImageResizeKJv2` → `TextEncodeQwenImage21` → KSampler | `bfs_head_v1.1_qwen_2.1` 1.0 + `p_qwen_image_2.1_8step` 1.0；8 步 CFG 1 **deis_2m**/simple |
| 9 | `Head Swap 2511 - V5`（HF: BFS） | BiRefNet → `InpaintCropImproved`（裁头部）→ 2511 + LoRA → `InpaintStitchImproved` 贴回 | `bfs_head_v5_2511_merged_version_rank_16_fp16` 1.0；20 步 CFG 2.5；提示词用「Picture 1 / Picture 2」 |
| 10 | `Body Swap Selective Qwen 2.1`（HF: BFS） | `BFSSegmentPicker`（SAM 3.1，把目标人涂 #FF00FF）→ `TextEncodeQwenImage21`（场景、涂色图、角色）→ 8 步 | `bfs_body_swap_selective_magenta_v1.0` 1.0；提示词要求「No magenta in the result」 |
| 11 | `qwen-image-2.1-edit-consistency` / `-realign`（HF: ausboss） | 2.1 编辑 + Consistency LoRA；或关 LoRA 后接 `RealignToSource` 把结果对回原图 | LoRA 1.0、`resolution` 0；25 步 CFG 1 |
| 12 | `Single image` / `Double Image`（HF: dx8152 Klein Consistency） | Klein 9B + LoRA → `ReferenceLatent` 链 → 4 步 | 单图流：一致性 LoRA 0.8；双图流里挂的是作者另一个 LoRA 0.4；中文指令「将蓝色区域替换为图2的瓶子」 |
| 13 | `krea2_reid_comfyui` / `krea2_controlnet_pose`（HF） | `Krea2OstrisEditModelPatch` + `TextEncodeKrea2OstrisEdit`；姿势版前置 `DWPreprocessor` | reid：`krea2_reid_rank32` 1.0、8 步；姿势：`krea2_turbo_openpose_controlnet` 1.0、10 步；CFG 1 |
| 14 | `Head Swap Krea 2`（HF: BFS） | `Krea2EditModelPatch` + `Krea2EditGroundedEncode` | `bfs_head_swap_v1.1_krea2` 1.0；8 步 CFG 1 |
| 15 | `workflow-comfyui-basic-next-scene-v2`（HF: lovis93） | FLUX.1 Krea 出首帧（30 步）→ Qwen-Edit-2509 + next-scene LoRA 链式出下一镜；提示词从文本文件逐行读 | `next-scene_lora-v2-3000` 1.0 + Lightning 4 步；8 步 CFG 1 |
| 16 | `image_flux3_klein_distilled_image_edit`（T） | `CreateBoundingBoxes` → `Flux3LayoutPrompt`（`In <ref_image_0>, replace the earring <obj_1> with …`）→ `ReferenceMultiLatent` → KSampler | 16 步 CFG 1；CLIPLoader type `flux3`；参考缩到 ~1 MP |
| 17 | `image_minimax_h3_image_edit`（T，HEAD） | LoadImage → 缩到 4 MP、32 倍数 → `TextGenerateV2`（Qwen3.5-9B 提示词扩写，37 KB 系统提示）→ `MiniMaxH3ImageConditioning` → KSampler | 6 步 CFG 1 euler/simple；负向 = `ConditioningZeroOut` |
| 18 | `image_p_h3_image_edit`（T，HEAD） | fl2va + `p-h3-image_lora` → `MiniMaxH3SigmaShift` → `PH3ImageConditioning` → SamplerCustomAdvanced | er_sde；sigmas `1.0, 0.984753, 0.967905, 0.951688, 0.925372, 0.881923, 0.810083, 0.528718, 0.0`；专用文本编码器与 VAE |
| 19 | `image_krea2_turbo_int8_image_style_reference`（T） | Krea 2 Turbo + `krea2_style_reference` LoRA → `TextEncodeQwenImageEditPlus`（1–2 张风格图）→ `FluxKontextMultiReferenceLatentMethod` | LoRA 1.0；8 步 CFG 1；ModelSamplingFlux 1.15 / 0.5 |
| 20 | `templates-portrait_light_migration`（T） | 2509 + Light-Migration LoRA + Lightning；图 1 = 人物、图 2 = 光照参考 | 4 步 CFG 1；提示词「参考色调，移除图1原有的光照并参考图2的光照和色调对图1重新照明」 |
| 21 | `image_moss_image_color_depth_control`（T） | 参考照 → MoGe 3 估几何 → `MOSSImageControl` → 采样 | 控制 LoRA 1.0；er_sde 25 步 CFG 3；保姿势 / 取景 / 轮廓，换人换装 |
| 22 | `templates-multiple_consistent_shots-nb_pro`（T） | Gemini 3 Pro 写 6 条提示词（每条 50–80 词，只变机位景别）→ 正则拆 → 6 个 Nano Banana Pro 并行（同一参考图） | 16:9、2K |
| 23 | `template_seedance2_storyboard_to_video`（T） | Gemini 写分镜提示词 → GPT Image 2 画 8 格火柴人预演分镜 → 分镜图 + 角色图拼接给 Gemini 写视频提示词（带「分镜机位解读」规则）→ 两张图同时作 Seedance 2.0 的参考图 | 分镜 1536×1024；规则含「不得复现分镜的边框、箭头、标注」 |
| 24 | `3d_triposplat_image_to_gaussian_splat` / `3d_pixal3d_trellis2_image_to_model`（T） | BiRefNet 去背 → DINOv3 → 采样 → 高斯泼溅 → `CreateCameraInfo`（orbit）→ `RenderSplat`；TRELLIS.2 出带贴图网格 | TripoSplat 20 步 CFG 3 dpmpp_2m；TRELLIS.2 12 步 CFG 7.5 |

## 3. 逐项目 / 逐工具

### 3.1 Qwen-Image-Edit-2511 与它的 LoRA 生态（HF，Apache-2.0，2025-12-17；LoRA 截至 2026-11-21）

- **定位**：可商用里身份保持最稳、LoRA 最全的本地编辑模型；Comfy 官方的多机位、Wan 起始帧模板建在 2511 上，重打光 / 光照迁移模板还停在 2509。
- **机制（源码 v0.46.2）**：`TextEncodeQwenImageEditPlus` 只有 image1–3；每张图给 Qwen2.5-VL 的是 **384×384 面积**的缩略图，给 DiT 的参考潜变量是 **1 MP**；提示词前自动拼 `Picture 1: … Picture 2: …`。→ 身份细节走的是那 1 MP 的潜变量，所以**参考图里脸占画面越大越像**，多格板缩到 1 MP 后脸只剩一两百像素。
- **提示词里怎么指图**：官方模板写 `image 1`，BFS 写 `Picture 1`；`<image1>` 是 Qwen-Image 2.1 节点的语法。现方案在 2511 首帧模板里写 `<image1>`，建议改掉并 A/B（未验证）。
- **关键 LoRA**（base_model 适配器按赞数）：`fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA`（1633 赞；`<sks> [方位] [俯仰] [距离]`，8×4×3 = 96 机位，强度 0.9，3000+ 对高斯泼溅渲染训练）；`lilylilith/AnyPose`（521；base + helper 各 0.7 + Lightning 4 步，一张姿势图当参考，无需 ControlNet；**平涂 / 像素风失效、多人失效**，作者自述）；`Alissonerdx/BFS-Best-Face-Swap`（1603；2511 用 `bfs_head_v5_2511_merged_version_rank_16_fp16`）；`lilylilith/QIE-2511-MP-AnyLight`、`zooeyy/…LightingRemap`（打光）；`ovi054/QIE-2511-Color-Grade-Transfer-LoRA`（调色迁移）；`prithivMLmods/QIE-2511-Extract-Outfit`（抽服装）；`tarn59/character_turnaround_sheet_qwen_edit_2511`（触发词 `Character turnaround sheet`）；`systms/SYSTMS-ACTION-LoRA`（Comfy 模板，提示词 `action the scene`）。
- **2509 的 LoRA**（Relight / Light-Migration / Fusion / White_to_Scene，`Comfy-Org/Qwen-Image-Edit` 的 `split_files/loras/`）在 2511 上是否等效未验证；2511 模型卡称已把打光与新视角 LoRA 的能力并进底模。
- **硬件与速度**：DiT 20.5 GB + 编码器 9.4 GB，靠 ComfyUI 卸载；1 张参考 47 s、2 张 85 s（RTX 5090，mathruffian，现方案已收）。4090 无实测。
- **限制**：≥ 3 个入画角色 + 1 张场景就超过 3 个槽，只能先拼图（`ImageStitch`）或换 10 图的模型。
- **评级：采用**（维持现方案的首选地位，补上多机位 / 姿势 / 换头三个 LoRA）。

### 3.2 Qwen-Image 2.1 的编辑模式与 LoRA 生态（HF，qwen-research，2026-09-14）

- **定位**：7B、文生图与编辑同一个权重、10 图、原生 2K、可出透明底；发布两个月已有 28 个以上过 25 赞的适配器（viggle-turbo 821、Anime-Fusal 222、AnyAngle 200、Consistency 138、Multiple-Angles 113、Next-Scene 75，另有 BFS 的 2.1 版）。
- **机制**：`TextEncodeQwenImage21` 的 `image_1` 是被编辑的图、其余是参考，输出的 latent 取 image_1 的尺寸，「换别的尺寸编辑会漂」（节点 tooltip）；`resolution` 是总像素预算，0 = 不缩放。**这解释了现方案记录的「附参考图出首帧会锁成正面」：把定妆照放在 image_1 等于让模型编辑这张定妆照。**
- **三种解法（社区工作流里的实际用法，均未在 4090 验证）**：① 姿势参考图：PoseAtlas 把人像 → image_1、衣装 → image_2、姿势 → image_3，线稿假人容易把留白当身体，**转成深度图更稳**；② 姿势 LoRA：VNCCS 把 3D 假人渲染放 image 1、角色放 image 2，加 `VNCCS_QI2_PoseStudio` LoRA；③ 场景 / 构图图放 image_1，再用 BFS 换头。
- **已知缺陷与补丁**：改画风时画面整体漂移（36 个 held-out 风格编辑，最差角点偏移中位 24.3 px → 加 `ausboss/Qwen-Image-2.1-Consistency-LoRA` 1500 步版后 1.6 px；局部编辑外的像素改动 12.8% → 7.5%）；但该 LoRA **会压制动作变化**（作者 09-28 更新），需要挪东西时改用「不挂 LoRA + Realign to Source 节点」。
- **加速**：官方 Turbo 权重 8 步；`p_qwen_image_2.1_8step`（Pruna，Comfy-Org 仓库 `loras/p_q_image_2.1_8_steps_v0.1_comfyui_bf16`）；`Viggle/…viggle-turbo` 6 步；`lightx2v/Qwen-Image-2.1-Lightning`。
- **控制**：`alibaba-pai/Qwen-Image-2.1-Fun-Controlnet-Union`（Canny / Depth / 灰度 / HED / Lineart / MLSD / Pose / Scribble + 局部重绘，约 7 GB，`control_context_scale` 1.0；Comfy-Org 仓库 `model_patches/qwen_image_2.1_fun_controlnet_union_int8_convrot` 3.78 GB）。官方模板库里还没有它的模板。
- **速度**：int8 1328² 25 步 72.7 s（24 GB 笔记本 5090，lifeidle 10-05）；shuohao 报 25–50 s / 张。
- **评级：试用**（非商用项目的派生视图、换装、换头首选；商用项目只能当草稿）。

### 3.3 MiniMax-H3-Image（HF，2026-11-03；Comfy 模板 11-10）

- **定位**：H3 家族的图像模型，33.1B 单流 DiT（H3 去掉音频层），文生图 + 编辑同一权重，蒸馏到 6 步无 CFG，直出 16 MP（4096²、5472×3072），最多 16 张参考（模型卡）。
- **机制**：文本编码器就是 H3 的 Qwen3-VL-32B（不变）；VAE 是 H3 视频 VAE 的编码器 + 专门的图像解码器（16× 下采样、24 通道，H3 视频 VAE 解不了它的图）；6 个固定噪声级各有一个输出头。`MiniMaxH3ImageConditioning`（v0.45.0 起）：参考图给 Qwen 看 1024 短边、给 VAE 1024–2048 短边，默认画布 2048²（源码）。
- **关键参数**：6 步 CFG 1 euler/simple；肤质发糙时换 **LCM**（`SamplerLCM` s_noise 1.1 → 0.9、simple、6 步；HF 讨论区 #5 与 Fizgig 文档一致）；提示词要长的英文整图描述，官方用 `MiniMax-H3-Image-PE`（Qwen3.8-27B）扩写，Comfy 模板用 Qwen3.5-9B；**必须用完整的 32B 编码器**（讨论区 #8、#10）。
- **硬件与速度**：RTX 4070 SUPER 12 GB + 96 GB 内存，int8 DiT + int8 编码器：2688×1536 暖机后 11–12 s / 张，16.5 MP 约 41 s，带一张参考 44 s，内存占用约 41 GB（LIOSAM007，11-11，单机实测）。4090 无实测，推断更快。
- **质量证据**：同 8 场景 × 2 seed 对比 Qwen 2.1：提示词遵循与小细节更好，光更平更亮、肤质更简单、画风偏「干净插画」（同一来源）。
- **身份保持（关键）**：「编辑后不像参考人」（povgeek37）、「两张参考合成两人，其中一张脸变样」（user0199939）、「视频模型取首帧做角色表几乎完美，图像模型多数时候脸不像」（VainGuard）、「角色相似度比 H3 视频稍差」（Pvok）—— 4 条独立反馈，11-10 / 11-11。另有编辑模式 5 步以上出现整图底纹的报告（MavenDE，未定位原因）。
- **训练**：Fizgig 9.6+ 支持 LoRA / LoKR / 编辑 LoRA，int8 训练 21.0–21.7 GB、带 2048 预览峰值 22.7 GB（RTX 5090 实测）→ 24 GB 刚好；Fizgig 文档称 ComfyUI 默认动态显存下 LoRA 约弱 15%（issue #17690，`--disable-dynamic-vram` 可避免）。
- **许可**：年收入 ≤ 100 万美元且不做托管服务可商用；产品界面须显示模型名；**输出也不得在排除地区（欧盟 / 英 / 韩 / 美）使用**（LICENSE §V.4，面向这些地区发行前自查）。
- **评级：试用**（场景母版、九宫格、道具、海报级剧照；人物首帧**不用它**）。
- **2026-11-24 补**：带身份的编辑现在有一枚专用 LoRA——Akatz 的 Character Swap V1（`akatz-ai/MiniMax-H3-Image-Character-Swap-LoRA`，155 MB，rank 16，1.0），11-23 进了官方模板库（`image_minimax_h3_image_character_swap`）：`<Picture 1>` 里的一个人换成 `<Picture 2>` 的角色，姿势、景别、光照跟源图；作者只在 1 MP、int8_convrot、RTX 4090 上测过，对比图是挑过的例子，没有量化。上面的评级不变，多一个「构图已定、只换人」的用法；细节和许可全文的要点见 `../13-github-survey/14-index-triage-2026-11-23.md` 的「2026-11-24 上游复查」。

### 3.4 把 H3 视频底模当图像编辑器（P-H3-Image / Fizgig Still / H3 Image Studio / musubi 单帧）

- **定位**：身份保持反而是 H3 视频权重的强项，多家都把它降成「单帧」来出静帧与角色视图。现方案已收 Fizgig Still 与 P-H3-Image，这里只补差异。
- **P-H3-Image 官方模板（11-03）**：采样器是 **er_sde**（不是 euler），8 步 sigmas 见 §2 #18；用自己的 `p-h3-image_text_encoder_int8_convrot` 与 `p-h3-image_vae_int8_convrot`；节点 image_1–9；编辑指令自动加前缀 `Edit <Picture 1>. `；默认画布 2912²（源码）。最小整套 20 GB 下载、8 MP 峰值 21 GB（模型卡）。
- **astropuzzo/ComfyUI-MiniMax-H3-Image-Studio**（★231，Unlicense，09-30）：把 Fizgig 的「单 latent 帧 + 解码时复制」封成两个工作流（Generate / Edit），只要 fl2va int8 + nvfp4 编码器 + 视频 VAE；起步 3 MP、无 LoRA 50 步。
- **musubi-tuner 单帧文档**（kohya，10 月）：Ref2VA 单帧 + 一张参考「可按文字出正 / 侧 / 背新视角，适合合成角色 LoRA 训练集」；FL2VA 单帧的先验是「同一时间戳的锚点几乎原样复制」，编辑要把目标放在 `target_index=24`、控制图放 `control_index=0`（隔 1 秒）。
- **BExplains/ComfyUI-MiniMaxH3-Image-RefMods**（11-18）：把 ≤ 15 张图打成一个 H3-Image RefMod 文件复用；效果无第三方数据。
- **评级**：H3 单帧路线 **采用**（已在 skill）；P-H3-Image **试用**（ComfyUI ≥ 0.44 即可，不必上 master）。

### 3.5 FLUX.2 Klein 与 FLUX 3 Image Klein（BFL）

- **定位**：小模型快编辑。Klein 9B 蒸馏版 4 步；FLUX 3 Klein 5.6B，把「框选对象」做进了提示词语法。
- **机制**：Klein 用 `ReferenceLatent` 链逐张追加参考；`flux-2-klein-9b-kv` 变体配 `FluxKVCache` 缓存参考图以便多次编辑。FLUX 3 用 `ReferenceMultiLatent` + `Flux3LayoutPrompt`：`In <ref_image_0>, change the dress color <obj_1> to red`，`<obj_N>` 对应 `CreateBoundingBoxes` 画的框；参考默认缩到 1 MP，BFL 管线可保持原尺寸（≤ 16 MP）。
- **一致性 LoRA**：`dx8152/Flux2-Klein-9B-Consistency`（508 赞，无触发词，V2 修了偏色 / 过饱和）；`NO8D/ExpressionControl·FaceControl·BodyControl·LightControl`；`thedeoxen/refcontrol-FLUX.2-klein-9B-reference-pose|depth|canny|lineart|normal-lora`（参考 + 结构双输入）；`nhathoangfoto/Flux.2-Klein-9B-MatchingPose`；`eric-venti-seeds/Sun-Direction-Lora`（太阳方向）。FLUX 3 Klein 的适配器只有 9 个且多为训练实验（HF，11-21）。
- **速度**：Klein 9B fp8 编辑 18.9 s、Klein 4B 42.3 s（官方 fp8 单文件 4.07 GB）、FLUX 3 Klein 蒸馏 1024² 6.8 s（24 GB 笔记本 5090，lifeidle，单机）。
- **许可**：Klein 9B / KV / FLUX.2 dev 非商用；**Klein 4B Apache-2.0**；FLUX 3 Klein 为 Kommunity 许可（年收入 < 500 万美元免费商用，二手来源，原文在 HF 上需登录）。lifeidle 把 FLUX 3 Klein 记成 Apache-2.0，与 HF 标签不符。
- **评级**：Klein 9B **试用**（非商用、要快时）；FLUX 3 Klein **观望**（无身份实测、生态未起）；Klein 4B **试用**（唯一 Apache 的小编辑模型）。

### 3.6 Krea 2 + Identity Edit V2（conradlocke，969 赞 / 27 万下载）

- **定位**：给写实向的 Krea 2（12.9B）加「一张照片 → 任意场景 / 姿势 / 服装 / 光线」与指令编辑。
- **机制**：双重条件 —— 源图的 VAE token 进上下文 + 带图的 Qwen3-VL 编码；必须装 `comfyui-krea2edit`（`Krea2EditModelPatch` + `Krea2EditGroundedEncode`）。V2 新增参考位置：`aligned`（钉在输出版式上）/ `beside`（放在画布旁，身份仍传递、版式不锁）。
- **关键参数**：Turbo 8 步 CFG 1；重摆单人 `ref_boost` 2、`grounding_px` 768；把人放进场景 = 场景 `aligned` + 人物 `beside`、人物 `ref_boost` 2–3；两个 LoRA 同时 1.0 会出纯噪声，要合用各 0.6。提示词写清「露出多少身体」「衣服换成什么、去掉什么」。
- **反面证据**：saya-imagegen 在 16 GB 上用二次元立绘测 V2 —— 「只会复制源图，不会演绎新姿势；换背景时人像贴上去」。作者的正面例子全是照片。两者不矛盾：写实可试，动漫不要用。
- **周边**：`yijunwang2/krea2-reid`、`krea2-anygles`；`thedeoxen/Krea-2-pose-controlnet`（OpenPose LoRA，10 步）；`ostris/krea2_turbo_style_reference`（已进官方模板）；`januspluto/ComfyUI-Krea2-Regional`（§3.11）。
- **许可**：Krea 2 公司收入 ≥ 100 万美元需企业授权；Identity Edit V2 免费仅限非商用，商用逐案找作者。
- **评级：试用**（写实、非商用）；动漫 **跳过**。

### 3.7 Anima 与 SDXL 二次元底模（2D 动漫线）

- **定位**：Anima（CircleStone Labs × Comfy Org，2B，212 万下载）是 2026 年的新二次元基座；Illustrious / NoobAI / WAI 这条 SDXL 线仍是「平涂二次元的标准答案、角色 LoRA 生态最大」（saya-imagegen）。
- **机制 / 参数**：Anima 读 Danbooru 标签或自然语言，512²–1536²，30–50 步 CFG 4–5，er_sde 线条利落；Turbo LoRA 8–12 步 CFG 1；质量前缀 `masterpiece, best quality, score_7, safe,`；LoRA 在 Base v1.0 上训。SDXL 线：832×1216、28 步 dpmpp_2m / karras、CFG 6.5，12–18 s / 张（16 GB，saya）。
- **控制与一致性**：`Comfy-Org/Anima-LLLite`（任意控制 / 深度 / 局部重绘，官方模板）；`Wenaka2004/comfyui-anima-ipadapter`（★60）；`An1X3R/ComfyUI-Anima-Regional`（角色级区域提示）；VNCCS 的表情步骤在 Illustrious / Anima 上用 Face Detailer 重绘（denoise 越高表情越强、越不像）。
- **许可**：Anima 模型与 LoRA 非商用，**输出可商用**；Illustrious-XL v2.0 为 OpenRAIL-M；NoobAI-XL 为 fair-ai-public-license。
- **评级：试用**（漫剧的角色锚点与风格探索）；首帧仍交给编辑模型。

### 3.8 云端图像模型（何时用见 §5.4）

- **共同点**：10–16 张参考、自然语言指图（`image 1` / `@Image1`）、单张 $0.03–0.16；Comfy 的「角色与时尚」模板（转身表、4 宫格场景探索、8 机位联络表、试衣）几乎全建在 Nano Banana Pro 上。
- **转身表模板**（`templates-character_sheet`）：两次调用 —— 「A 360 turnaround full body view of the subject … Front view, half turn, side profile, back view … all white background」16:9 2K + 四个角度的大头照 9:16 2K，再横向拼接。
- **证据强度**：只有 img.ly 的纯文字一致性榜（Seedream 5.0 Pro 4.86、GPT Image 2.5 Sunburst / Qwen Image 3.0 4.72、Nano Banana 系 3.89、FLUX 3 Klein 3.75；「一致性是所有能力里天花板最低的一项，每个模型都会漂」），没有带参考图的公开横评；Seedream 5.5 / GPT Image 2.6 / Kling 4.0 太新，无第三方数据。
- **评级**：Nano Banana 2.1 / Seedream 5.5 **试用**（按张付费兜底）；Midjourney **跳过**（无 API）。

### 3.9 身份适配器现状：IP-Adapter / PuLID / InstantID / InfiniteYou / UNO / USO / EasyControl / ACE++ / Redux

- **定位**：2024–2025 年的主流 —— 不训练，把人脸 / 主体特征注入生成模型。
- **现状（GitHub API，2026-11-21）**：`ToTheBeginning/PuLID` ★3554 末次推送 2025-07-31；`instantX-research/InstantID` ★11994，2024-07-18；`bytedance/InfiniteYou` ★2690，2025-08-22（权重 CC-BY-NC）；`bytedance/UNO` ★1363、`bytedance/USO` ★1241，均 2025-09-12；`Xiaojiu-z/EasyControl` ★1739，2025-07-25；`ali-vilab/ACE_plus` ★1364，2025-04-21；`cubiq/ComfyUI_IPAdapter_plus` ★6187，2025-04-14。用「pushed > 2026-03」过滤后，InstantID / InfiniteYou 相关仓库最高只有个位数星。
- **机制**：PuLID = InsightFace 人脸嵌入 + EVA-CLIP 视觉特征 → 身份 token 注入；InstantID = 人脸嵌入 + 关键点 ControlNet（SDXL）；InfiniteYou / UNO / USO / Redux / EasyControl / ACE++ 全部绑定 **FLUX.1 dev**（非商用，24 GB 上已被更小更新的编辑模型取代）。
- **还活着的**：`iFayens/ComfyUI-PuLID-Flux2`（★128，MIT，2026-05-21；Klein 4B / 9B / Dev，`strength` 1.0–1.4）；Anima 的社区 IP-Adapter；Comfy 官方模板里还留着 `flux1_dev_uso_reference_image_gen`（USO：内容参考走 `ReferenceLatent`、风格参考走 SigCLIP + projector，20 步 guidance 3.5）与 `flux_redux_model_example`（只迁移整体观感，不保脸）。
- **许可坑**：这些方案几乎都依赖 InsightFace 的 `antelopev2` / `buffalo_l` 权重 —— 代码 MIT，**模型仅限非商用研究**（InsightFace README）。
- **对 4090 短剧的价值**：低。编辑模型把「看参考图 + 理解指令」做进了底模，身份适配器只在「必须文生图、且要锁脸」时才有意义；SDXL 二次元线上 InstantID / IP-Adapter 仍可用，但我们的首帧不走这条路。
- **评级：跳过**（PuLID-Flux2 仅在用 Klein 文生图锁脸时 **观望**）。

### 3.10 结构控制：ControlNet Union 与「参考 + 结构」LoRA

- **定位**：控制姿势 / 构图 / 景深，与身份参考解耦。
- **可用清单**：Z-Image-Turbo Fun ControlNet Union 2.1（Canny / HED / Depth / Pose / MLSD；官方模板用 `ModelPatchLoader` + `QwenImageDiffsynthControlnet`，8 步 res_multistep）；Qwen-Image 2512 Fun Union 2602（`ControlNetApplyAdvanced` 强度 1.0）；**Qwen-Image 2.1 Fun Union**（8 种条件 + 重绘，§3.2）；MOSS-Image 颜色 + 深度（MoGe 3 估几何，「保姿势、取景、轮廓，提示词决定人物和服装」）；Anima LLLite；Krea 2 OpenPose LoRA；Klein 9B 的 refcontrol 系列。H3 自己有 `MiniMaxH3FunControlNetApply`（已在 skill）。
- **姿势来源**：`utility_sdpose_multi_person`（SDPose-OOD，多人）；`utility_sam3d_body`；DWPose；VNCCS Pose Studio / `ComfyUI-3D-OpenPose-Editor2026`（★76）/ `comfyui-vrm-pose-editor` / `ComfyUI-Character3D` 手摆 3D 假人；`ComfyUI-RuiC-PoseAtlas`（姿势素材库，线稿可一键转深度图）。
- **经验**：编辑模型吃「渲染出来的假人 / 深度图」比吃 OpenPose 骨架稳（AnyPose 作者：「即使底模内置了 openpose，深度和比例还是会不对」；PoseAtlas：线稿留白会被当成身体）。
- **对 4090 短剧的价值**：中高 —— 我们现在只能靠文字写姿势和站位，这是最大的可控性缺口。
- **评级**：深度 / 假人参考图 **采用**；Qwen 2.1 Fun Union **试用**；其余 **观望**。

### 3.11 区域提示与多人同框不串脸

- **问题**：两个角色 LoRA 或两张身份参考同框时互相渗透；普通角色 LoRA 会把陌生人也画成主角。
- **做法 1 · 训练期隔离**：Fizgig LoRA Isolation = DOP（去掉触发词的那一遍对齐底模输出）+ 多主体同训 + 把触发词和类别词并成一个 token（`gwelt, a man` → `gweltman`）等 6 层；Krea 2 上 25 提示 × 2 seed：普通 LoRA 50 张里 48 张陌生人像主角，隔离后 0 张，主体相似度 0.77 → 0.78（真实照片互比 0.81）；「即使只训一个人，也建议同训第二个人」。
- **做法 2 · 推理期分区**：`januspluto/ComfyUI-Krea2-Regional`（★17，MIT，11-05）：单流 MMDiT 上用联合注意力掩码让每个区域只看自己的提示词，LoRA 增量按 token 门控，一次前向；边界有少量风格渗透。`ComfyUI_LC123_nodes`（★68）、`comfyui-lucid-vrp`（Anima 区域 + MOSS 布局）。
- **做法 3 · 布局进提示词**：FLUX 3 的 `<obj_N>` 框、MOSS-Image 的 `CreateBoundingBoxes` + `MOSSImageLayoutPrompt`（每个框一段描述，文字框直接渲染文字）。
- **做法 4 · 事后只换一个人**：BFS Selective Body Swap（SAM3 涂品红 → 只替换被涂的人，保留其姿势 / 头部角度 / 表情）。
- **做法 5 · 编辑模型原生**：2511 模型卡把「两张单人照合成合影」列为改进项；现方案实测 2 人可行。
- **对 4090 短剧的价值**：做法 4、5 立刻可用；做法 1 只有在走双角色 LoRA 时才需要。
- **评级**：选择性换人 **试用**；LoRA Isolation **试用**（训双人 LoRA 时默认开）；Krea2-Regional **观望**。

### 3.12 Fizgig（shootthesound，★785，Apache-2.0，v9.8.2，2026-11-21）

- **定位**：Windows 一键的 LoRA / 微调工作台，覆盖 Klein 9B、FLUX 3 Klein、Fibo 2.0、Krea 2、MiniMax H3、**H3 Image**、Qwen Image 2.1、MOSS-Image、Z-Image Turbo / Base、SDXL、Anima。现方案只收了它的 H3 视频部分。
- **各基座的角色预设**（文档原文）：Qwen 2.1 Fast = rank 8、自适应 LR 2e-4–4e-4、**0.5 MP**、30 epoch、Muon、EMA 0.98（「0.5 MP 是甜点，rank 16 用 Fast 的学习率会过训」）；Z-Image Turbo Fast = rank 8、同 LR、0.25 MP、30 epoch；Krea 2 Ultra Fast = rank 8 自适应 LR（在 RAW 上训、Turbo LoRA 只用于预览）；H3 Image Standard = 0.25 MP、Automagic v4 起始 2.5e-4；Anima = 1 MP、Base v1.0。每个基座都有自己的「训练适配器」（训练时冻结挂上、预览与成品不带），不用它 Qwen 2.1 会塌成纹理、H3 Image 会变成漫画脸。
- **显存（作者实测）**：Qwen 2.1 24 GB 走 bf16；Z-Image Turbo 1 MP 峰值 bf16 17.2 / INT8 12.3 GB；Krea 2 8 GB 起；H3 Image int8 21.0–21.7 GB、带 2048 预览 22.7 GB；系统内存 32 GB 起、开预览 48 GB。Windows 上要关「CUDA Sysmem Fallback」，否则溢到共享显存慢几倍。
- **耗时**：没有 4090 数字。可参照：MOSS-Image LoRA 20 分钟（RTX 5090，v9.2）；Qwen 2.1 编辑 LoRA 40 对图 6 epoch 约 8 分钟（RTX 5090）。
- **数据侧**：AI 字幕（Qwen3-VL-4B / JoyCaption / Florence-2 / WD EVA02 标签）；人脸特写 + 全身配对「对角色数据集帮助很大」；Look Consistency Filter；遮罩训练（只学人不学房间，「显著提高最佳相似度与到达速度」）；Element boost（前 12 epoch 脸和头发权重更高）；编辑 LoRA（约 40 对原图 / 改后图，可带 ≤ 9 张额外参考）。
- **挑检查点**：LoRA Royale 每个 epoch 同 seed 出图 + 相似度分；技巧：样张提示词里放一个数据集没有的姿势，「最后一个还听话的 epoch」就是该留的。
- **评级：采用**（图像侧也用它；训练前关 ComfyUI）。

### 3.13 其它训练器：ai-toolkit / musubi-tuner / OneTrainer / SimpleTuner / diffusion-pipe / sd-scripts

- **ostris/ai-toolkit**（★12679，MIT，11-18）：支持清单最全 —— FLUX.1 / FLUX.2 dev / Klein base 4B·9B / **FLUX 3 Image Klein**、Qwen-Image / 2512 / **2.1** / 2.1 Turbo、Z-Image / Turbo / De-Turbo、HiDream I1 / O1、OmniGen2、Anima、Krea 2；编辑类 Kontext、Qwen-Image-Edit / 2509 / **2511**、HiDream E1、Boogu Edit（「Qwen 2.1 数据集带控制图就按编辑训」）。多数社区 LoRA（Next-Scene、Consistency、Krea2 Identity Edit）都是它训的；lora-dataset-studio 把它当后端。
- **kohya-ss/musubi-tuner**（★2145，10-31）：HunyuanVideo、Wan、FramePack、Kontext、FLUX.2 dev / klein、Qwen-Image、Z-Image、Krea 2（ConvRot int8 底模）、**MiniMax-H3（含单帧图像 LoRA、Ref2VA 成对训练）**；图像训练建议 ≥ 12 GB。命令行，Windows 可用。
- **Nerogar/OneTrainer**（★3266，AGPL，11-21）、**bghira/SimpleTuner**（★2961，AGPL，11-20；FLUX 3 Klein 与 H3-Image 发布当周就有实验 LoRA 挂在 HF 的 `SimpleTuner/*`）、**tdrussell/diffusion-pipe**（★2037，GPL，11-19，Linux / WSL）、**kohya-ss/sd-scripts**（★7270，SDXL / Anima 线）。本轮只确认活跃度与支持面，未读配方。
- **选型**：Windows + 4090 + 少量图 → Fizgig；要训编辑 LoRA 或冷门基座 → ai-toolkit；要 H3 单帧 / Ref2VA 成对 → musubi-tuner。
- **评级**：ai-toolkit **试用**；musubi-tuner **观望**（H3 单帧标注为实验性）；其余 **跳过**（对我们无独占能力）。

### 3.14 数据集自举：一张图 → 训练集

- **perfectgf/lora-dataset-studio**（★359，11-16）：给一张参考照，按「变化目录」（表情 / 角度 / 光线 / 景别 / 服装 / 背景）补齐缺的镜头，生成引擎可选 Nano Banana Pro、gpt-image-2、OpenRouter、本地 Klein、Krea 2 Edit；InsightFace 相似度自动分拣；ai-toolkit 训练；同 seed 渲染各检查点并按人脸相似度 + 投票排序。显存表（ai-toolkit 后端口径）：自动字幕 ~8 GB、本地出图 ~16 GB、Z-Image / SDXL 训练 16 GB、**Krea 2 1024 px 需 24 GB**、Klein 9B 32–48 GB（Fizgig 用 fp8 底模称 14 GB 可训 Klein 9B，两家口径不同）。
- **EnragedAntelope/dataset-deviser**（★9，MIT，10-26）：角色 = 1 张参考 → 约 24 张（机位 / 姿势 / 情绪 / 场景），概念 = 18 张；本地用 Qwen-Image 2.1，云端用 Gemini；保留参考图原画风；字幕 Qwen3-VL-8B / JoyCaption / WD。
- **musubi 的提示**：H3 Ref2VA 单帧可出正 / 侧 / 背新视角，「适合合成角色 LoRA 训练集」；密集 2D 插画会被重画而非逐像素保留。
- **风险**：自举 = 用编辑模型的输出当真值，编辑模型的漂移会被 LoRA 固化。先过 Look Filter（基准 3 张、中位数 − 1.5 × IQR 以下剔除），再训。
- **评级：试用**（角色要跨 ≥ 30 段复用且参考图路线总漂时）。

### 3.15 图像 LoRA 与视频 LoRA 的关系

- **同一权重才通用**：给 H3 视频 DiT 训的静帧 LoRA 直接用于 H3 视频（现方案 `lora-and-style.md`）；给 Qwen / Z-Image / Krea 训的图像 LoRA 只作用于首帧模型，身份要靠首帧 + 参考图传进 H3。
- **H3 与 H3-Image 不通用**：Fizgig：「层是 H3 的，但权重在训练中移动了四分之一到一半，H3 的 LoRA 与训练适配器不能带过来」；讨论区有 1 人说「试了几个视频 LoRA 在图像模型上能用」—— 两说并存，未验证。
- **单帧训练能否迁移到视频**：kohya 明说「图像训练的 LoRA 用于视频生成是未验证领域」，建议字幕里写明静音以便迁移。
- **结论**：短剧里角色 LoRA 的收益顺序 = H3 视频静帧 LoRA（一次训练、全片受益）＞ 首帧模型的图像 LoRA（只稳首帧）。两者都训是最稳但最贵的做法。

### 3.16 VNCCS（AHEKOT，主仓库 ★1780 + Utils ★1234，MIT，2026-11-12 / 11-18，v3.3.4）

- **定位**：视觉小说立绘全流程 —— 建角 → 摆姿势 → 换装 → 表情，四个工作流各只有 2–5 个大节点，一切参数在节点内的面板里。
- **机制**：Step 1 Creator（Illustrious / Anima / Qwen 2.1 文生角色，种族、体型、脸、发等预设 + 风格库）或 Cloner（克隆现成图）；**Pose Studio**（节点内 3D 视口：年龄 / 性别 / 体重 / 肌肉 / 身高滑杆、可拖关节、多姿势页签、Mixamo FBX、灯光、参考图描摹）出姿势渲染；生成器用 Qwen 2.1 / Klein 9B（4 步）/ **MiniMax H3**（`h3_still.py`）+ 作者自训 LoRA（`MIUProject/VNCCS_v3.0`：`VNCCS_QI2_PoseStudio`、`VNCCS_QI2_ClothesCore`、`VNCCS_PoseStudioKlein9b`、`VNCCS_PoseStudioH3`、`VNCCS_ClothesCoreMiniMaxH3`）；色键 + SAM3 去背；Step 3 表情在 Qwen 2.1 上「只改脸再贴回」，在 Illustrious / Anima 上走 Face Detailer。
- **Utils**：3D Factory（TripoSplat 把参考图变成高斯物体，多物体摆成场景，**最多 32 个命名机位，一次输出全部机位的 IMAGE 列表**）；UniCanvas（无限画布，Qwen Edit 2.1 / Krea2 Identity Edit，≤ 4 张参考 `Picture 2…`，360° 全景内编辑）；Prompt Designer。
- **存储**：`output/VNCCS/Characters/<名>/{Sprites,Faces,Sheets}/<服装>/<表情>/` + `<名>_config.json`（`character_info`、`costumes`）；`Naked` / `Original` 两套受保护；写入加锁 + 原子写 + 旧批次归档；API 用 ETag 做乐观锁（过期 409、缺版本 428）。
- **许可**：代码 MIT；自带 LoRA 跟随各底模许可（Qwen 2.1 研究许可、Klein 9B 非商用）。
- **对 4090 短剧的价值**：高 —— 它已经把「H3 当立绘生成器 + 3D 假人摆姿势」做成了现成节点；漫剧的角色 × 服装 × 表情矩阵可以直接照它的目录结构建。
- **评级：试用**（先单独装在一份干净 ComfyUI 里，只拿 Pose Studio 与目录规范）。

### 3.17 shuohao-skills（eternityspring，★6899，Apache-2.0，2026-11-09）

- **定位**：7 个与 agent 无关的短剧技能（大纲 / 角色 / 角色出图 / 美术 / 剧本 / 走位 / 分镜），每个都带脚本门禁与自测；短剧技能 / 流水线类里星数最高。
- **character-refs（真出图）**：见图谱 A。实测依据：「只挂正面全身，H3 的服装和背影都对，但脸会走样；加一张大头照，脸最接近」；「一致性来自同一张锚点，不来自同一个模型」（Qwen 锚点 + GPT 派生、反之、混用都接得上）；设定板「由代码排版而不是生成一张合成图 —— 合成图当参考会让模型把人画小」。标签 `角色/服装/视图/版本` 同时写进文件名、asset.json、PNG 元数据；旧版本永不覆盖。
- **novel-art**：场景写 3–5 个一致性锚点（观众靠它认地方，QC 逐镜核对）；**换时段 = 重新生成，不是重打光**；变体用 `variantOf` + `changes` 对着父图生成；道具只给叙事道具建资产（每部 3–8 个），必须有状态变体（箱子合 / 开是两张）、尺度短语（「AI 爱把手持道具画成家具大小」）、白底无手。
- **novel-staging**：每场开场的站位 / 朝向 / 坐立，输出俯视图报告与一句开场走位句，抄进该场第一段分镜。
- **novel-storyboard**：段（一次生成 ≤ 15 s）→ 镜（2–5 s，硬门禁）→ **每镜一张关键帧，主帧钉在 0.00 s、子帧钉在各自切点**；H3 提示词里的对齐句（`Picture 2 aligns with the 3.00-second mark…`）与 `[Shot k] At 00:0X.XXX` 由镜长推导并逐字审计；18 条门禁全是代码。
- **评级：采用**（资产纪律与「每镜关键帧钉切点」两点搬进 skill；它的 H3 提示词部分与我们现有规则重叠）。

### 3.18 多角度 LoRA 与相机节点

- **fal Multiple-Angles（2511）**：见 §3.1；`jtydhr88/ComfyUI-qwenmultiangle`（★1465，MIT）用 Three.js 视口拖相机，输出该 LoRA 的提示词（方位 0–360°、俯仰 −30–60°、距离 0–10）；`NickPittas/ComfyUI_CameraAngleSelector`（★129）可一次多选机位输出提示词列表。
- **Qwen 2.1 版**：`akhaliq/Qwen-Image-2.1-Multiple-Angles-LoRA`（113 赞）、`gribbliest/qwen-image-2.1-qma-camera-angles`、`lilylilith/QI_2.1_AnyAngle`（任意角度：先 TripoSplat / TRELLIS.2 重建 → Blender 摆机位渲粗图 → LoRA 1.0、CFG 3、≥ 20 步转绘；训练集一半来自 Blender 实渲、一半来自 **H3 图生视频的环绕镜头**；重建太粗时桌子、马尾会错位）。
- **Klein / Krea**：`lovis93/Flux-2-Multi-Angles-LoRA-v2`（72 机位）、`yijunwang2/krea2-anygles`。
- **用途**：正反打、过肩、俯拍 —— 从同一张底图转出来，背景结构不跑；比现方案「同一张底图编辑出不同机位」多了可控的角度语法。
- **限制**：未见到带人脸相似度的评测；大角度（背面、俯 60°）会补画看不见的部分，需人审。
- **评级：采用**（2511 + fal LoRA，Apache-2.0）。

### 3.19 3D 辅助：图 → 3D → 取景 → 转绘

- **本地可用（Comfy 官方模板）**：TripoSplat（单图 → 高斯泼溅，可按 orbit 渲染转台视频）、Idol（Comfy-Org 微调版，11-03）、TRELLIS.2（`trellis_2_int8_convrot`，带贴图网格）、Pixal3D、Hunyuan3D 2.1（单文件 7.37 GB，54.7 s 出 52 万面 GLB，24 GB 笔记本 5090，lifeidle）、MoGe 全景 → 网格、`qwen-360-diffusion` LoRA（2512 上出等距柱状全景）。腾讯开放权重最新仍是 Hunyuan3D 2.1（2025-06）与 Hunyuan3D-Omni（2025-09）。
- **三种用法**：① 角色粗模当**姿势与机位参考**（VNCCS Pose Studio 更省事，不必重建角色）；② **场景**重建后在 3D 里摆机位出多角度粗图再转绘（AnyAngle、VNCCS 3D Factory 32 机位）；③ 全景母版：先出 360° 图，在全景里取景再转绘（VNCCS UniCanvas、`ComfyUI-6DOF-Camera`、`comfyui-pano2room`、`ComfyUI-HYPano2`）。
- **平台侧**：`pyoonpyoon/open-higgsfield`（★5）：拖 3D 相机 → 编译成 2511 + 多角度 LoRA 的工作流；`Heroesjouney/AIMovieStudiov2`（★208）：3D 里摆机位、180° 轴线警告、参考图按固定顺序注入（建立镜头 → 地点 → 角色 / 道具）。
- **代价**：多装 3–10 GB 模型、多一个 Blender 环节；重建质量决定上限。
- **评级**：Pose Studio 式假人 **试用**；场景高斯重建 **观望**（只在一个场景要出 ≥ 6 个机位时才值得）。

### 3.20 Comfy 官方的分镜 / 角色类模板（Nano Banana 系）

- **3×3 联络表**（05-21）：系统提示词规定「3 列 × 3 行、每格 16:9、无边框、每格强烈透视、逐格写机位」并要求先写成 JSON 再出图；选格后第二次调用把该格重绘为独立 16:9 高清图。
- **Contact Sheet 三步**（03-30）：① 角色 + 场景 + 产品 → 一张 4K 主视觉；② 两次调用各出一张 2×2 宫格 → 裁成 8 张不同机位；③ 8 张当关键帧，相邻两张交给 VLM 分析「机位距离 / 角度 / 景别 / 光线差异」写运镜提示词 → 7 段首尾帧视频。
- **Single Image to Multiple Consistent Shots**（01-26）：LLM 先写 6 条只变机位与景别的提示词，再并行出图。
- **6 Key Frames**（2025-12）：6 张关键帧 → Wan 2.2 首尾帧 ×5 → 拼接。
- **Storyboard to Video**（06-15）：火柴人预演分镜只表达动作与机位，交给视频模型当「镜头计划」。
- **可借鉴的是结构而不是模型**：宫格 → 选格 → 单格重绘；相邻关键帧 → VLM 写运镜。本地可用 Qwen 2.1 / H3-Image 出宫格（现方案已有九宫格），单格重绘用 2511。
- **评级**：结构 **采用**；火柴人分镜喂 H3 **观望**（H3 把带文字 / 分格的图当弱参考，未验证）。

### 3.21 Next-Scene LoRA

- **来源**：`lovis93/next-scene-qwen-image-lora-2509`（MIT，666 赞，v2）；`akhaliq/Qwen-Image-2.1-Next-Scene-LoRA`（移植到 2.1，step 2500）。
- **机制**：用电影连续镜头对训练，让编辑模型学会「下一镜」—— 运镜、揭示、光线变化，同时保持世界、角色、画风。
- **参数**：提示词以 `Next Scene:` 开头、先写运镜；强度 0.7–0.9（越低越不照抄输入）；2.1 版 28–40 步 CFG 1；2509 版配 Lightning 8 步。链式生成时每跳先对输入加轻微模糊去颗粒。
- **限制**：链越长漂移越大（作者示例 4 跳）；无身份量化；2511 上是否可用未验证。
- **对 4090 短剧的价值**：用来**快速出一场戏的分镜草图序列**给用户审，定稿首帧仍从母版 + 角色参考重出，不直接用链尾。
- **评级：试用**。

### 3.22 开源短剧平台的一致性做法（只看方法）

- **BigBanana-AI-Director**（★2473）：「剧本 → 资产 → 关键帧」；定妆照 + 衣橱系统（同一身份多套造型）+ 上下文感知；全自动前先出计划，**逐镜选「九宫格分镜」还是「首尾帧」链路**。
- **wind-comic**（★722，MIT）：导演台在俯视舞台上摆演员和相机 → 一句精确走位指令 + 一张布局草图（只给会按草图构图的引擎）；走位改了，旧镜头标记过期；Vision 审核 < 70 分自动重生成；发布门禁四维（画面对剧本 / 一致性 / 口型可对齐 / 实测口型）。
- **aid-studio**（★1476，MIT）：参考图占位协议 + 每个模型的能力表（参考图数量、分辨率、时长）+ 项目风格快照。
- **AIMovieStudiov2**（★208，AGPL）：参考图数超过工作流槽位时**报错而不是静默丢图**。
- **共同点**：都在做「先资产后镜头 + 过期传播 + 机器审核」；没有一家公布带参考图的一致性量化数据。
- **评级**：方法 **采用**（过期传播、超槽报错、逐镜选链路）；平台本身 **跳过**。

### 3.23 风格一致：风格参考、风格 LoRA、3D 国漫

- **风格参考**：Krea 2 `krea2_style_reference` LoRA（1–2 张风格图，只迁移画风不保身份）；USO（FLUX.1）；云端 Recraft / Magnific 的 style reference。
- **不要做的**：把成片画面当风格参考（人和物会被画进来，现方案已记）；在提示词里堆「最高优先级风格段」（saya 实测画风不变）；负向里写目标风格词（等于推远）；`semi-realistic` 会把脸推向真人、`illustration / painterly` 会拉满手绘感。
- **风格 LoRA**：Fizgig 的 Style 预设（Qwen 2.1：rank 16、平 LR 1.5e-4；「风格数据集上自适应 LR 会爬升导致过烤」）；Detail crops（把每张图再裁成原尺度方块训练笔触）；字幕写「除画风以外的一切」，让触发词绑定画风。Klein 的风格集中在双流块 0–7 与晚时间步（Fizgig 块图）。
- **2D**：Anima 风格库（VNCCS 内置，可两种风格混合）、`MicksHF/Qwen-Image-2.1-Anime-Fusal`、`VNCCS_QI2_AnimeOverhaul`。
- **3D 国漫 / 三渲二**：HF 上没有成气候的现成 LoRA（搜索 donghua / guoman 均为个位数下载）；可行路线是「提示词锁（现 skill 的 3D 国漫类型包）+ 用 20–40 张目标画面自训风格 LoRA」，或 3D 管线：`chfr19820610-cell/AIComics`（ComfyUI + Blender + Remotion，三档渲染 2D / 2.5D Blender 赛璐珞 / 3D，四视图参考约束分镜，未读源码）。
- **评级**：Krea 2 风格参考 **试用**；自训风格 LoRA **试用**；AIComics **观望**。

### 3.24 光线与色调统一

- **重打光 LoRA**：2509 的 Relight / Light-Migration（官方模板：图 1 人物 + 图 2 光照参考，4 步）；2511 的 `QIE-2511-MP-AnyLight`、`LightingRemap`、`QIE-2511-Studio-DeLight`（去光）、`QIE-2511-Cinematic-FlatLog-Control`（出平的 Log 画面便于后期统一调色）；Klein 的 `Sun-Direction`、`LightControl`、`Flux2-Klein-Delight-LoRA`。
- **调色迁移**：`ovi054/QIE-2511-Color-Grade-Transfer-LoRA`；Fizgig 的编辑 LoRA 示例就是「40 对图学一个调色」。
- **原则（shuohao novel-art）**：同一场景换时段是**重新生成**一张母版，不是对旧母版重打光；每个场景只有有限几个「光照状态」，各有一张母版。
- **对我们**：现方案用提示词写「单一光源 + 阴影方向」；补充手段是「同场所有首帧生成完后，用同一张光照参考做一次 Light-Migration」（未验证是否伤身份，做完必须再过门禁）。
- **评级：观望**（先靠母版 + 提示词；后期统一调色更便宜）。

### 3.25 检测与门禁

- **真人脸**：现方案用 YuNet + SFace（OpenCV Zoo，Apache-2.0）—— 保留，它是**唯一许可干净**的一套。Fizgig 在 2026-11-12 把相似度后端从 ArcFace 换成 **AdaFace ViT-Base**（`minchul/cvlface_adaface_vit_base_webface4m`）：逐 epoch 对比 ArcFace / AdaFace IR-101 / AdaFace ViT，「ViT 选出的最佳 epoch 每次都与人眼一致，ArcFace 经常不一致」；阈值 match 0.42 / borderline 0.36 / floor 0.30；6 人数据集同人 p10 / p25 / 中位 = 0.46 / 0.56 / 0.63，1700 对异人中位 0.05、最高 0.31。ArcFace 旧档 0.45 / 0.30 / 0.25。
- **动漫 / 兽设 / 手绘**：InsightFace 在这类图上基本检不出脸（Fizgig 测试集 0 / 19）。检测换 YOLO 头部模型（deepghs anime head，MIT），嵌入换 **DINOv2-base**（对头部裁剪）：match 0.62 / borderline 0.48 / floor 0.40；同角色中位 0.69–0.75，异角色 p95 0.57–0.60；**CLIP 被测后弃用**（异角色常 > 0.8）。另一套：deepghs `imgutils` 的 **CCIP**（专门的动漫角色相似度，差异值 ≤ 0.178 判同人，F1 0.917，仅限单人图）。
- **每套数据自己的围栏**：阈值是小样本标定的起点，更可信的是「对 3 张基准打分后，中位数 − 1.5 × IQR」（Fizgig Look Filter）。
- **漂移曲线**：`DevvGwardo/soulfoundry` 的 `ConsistencyAudit` 输出逐镜相似度、漂移曲线、第一处失败的镜头；其默认地板 0.75 过严（同一人 1860 与 1862 年照片只有 0.505）。
- **换脸效果参照**：同一身体图 + 同一脸源，InsightFace 余弦：原图 0.129、ReActor 0.216、Qwen 2.1 + BFS 0.735、先放大到 1536×2048 再换 0.783（同人上限约 0.94；moss-qwen-faceswap，单机）。
- **服装 / 道具**：没有成熟的专用度量。可行组合：人物裁剪（遮掉脸）的 DINOv2 相似度 + 主色 ΔE + VLM 是非题清单（wind-comic 的 Vision 审核、Comfy 11-21 新上的 HeyGen Decision 节点都是这个思路）。
- **许可**：InsightFace `buffalo_l` / `antelopev2` 权重仅限非商用研究；AdaFace 权重训练集 WebFace4M 的商用条款自查。
- **评级**：分轨门禁 **采用**（规格见 §7）。

### 3.26 资产管理：各家怎么存

| 项目 | 目录 / 文件 | 版本与冻结 | 过期传播 |
|------|------------|-----------|---------|
| shuohao character-refs | `<角色>/asset.json` + PNG；标签 `角色/服装/视图/版本` 写进文件名、JSON、PNG 元数据 | 旧版本永不覆盖；只冻结三样：锚点文件 sha256、画风快照、文字描述指纹 | 锚点变 → 其余全过期；大头照变 → 发 / 领口细节过期；描述变 → 全过期；只标记不删除 |
| VNCCS | `Characters/<名>/{Sprites,Faces,Sheets}/<服装>/<表情>/` + `<名>_config.json` | 新批次落盘前把旧批次移入归档目录；`Naked` / `Original` 受保护 | 服装保存带 revision，冲突返回 409 并保留本地草稿 |
| wind-comic / AIMovieStudio | 数据库 + 资产库（TEXT → JSON → PNG → MP4 每级落库） | 每级可单独重跑 | 走位或上游变更 → 下游镜头标过期 |
| aid-studio | 资产库 + 官方资产包（`manifest.json` + sha256 清单） | 风格快照随项目 | — |
| 我们（现 skill） | `bible/chars/<id>_bust.png`、`_sheet.png`、`_face.png`、`bible/scenes/…`、`bible/props/…` | 「选定后冻结」只是文字约定 | 无 |

缺口：我们没有机器可读的冻结与过期记录（§6 第 14 条）。

## 4. 交付 (1)：一致性技术路线对照表

「身份保持」只写有出处的判断；显存按 24 GB 卡 + ComfyUI 自动卸载是否可行。

| # | 路线 | 身份保持（证据） | 灵活度（姿势 / 机位 / 服装） | 成本 | 24 GB | 许可 | 适用场景 |
|---|------|-----------------|---------------------------|------|-------|------|---------|
| 1 | 纯文字：外观文字逐字复用 | 弱；纯文字跨场景一致性是所有能力里天花板最低的（img.ly，最高 4.86 / 5） | 最高 | 零 | 任意 | 随模型 | 只用来生成锚点；群演、路人 |
| 2 | 编辑模型 + 单张锚点（Edit-2511） | 中上；「换场景 / 姿势仍认得出」（saya）；官方称多人一致改进 | 高（姿势靠文字时不稳） | 20 步约 47–85 s / 张（5090） | 可（卸载） | Apache-2.0 | **逐镜首帧、派生视图、换装** |
| 3 | 编辑模型 + 多参考（Qwen 2.1 10 图 / H3-Image 16 图） | Qwen 2.1：中上但默认锁 image_1 的姿势；H3-Image：弱（4 条反馈） | 高 | 25 步约 25–73 s；H3-Image 4 MP 约 11 s（12 GB 卡） | 可 | 研究许可 / H3-Image 社区许可 | 多资产合成（人 + 衣 + 姿势 + 景）；H3-Image 只做无人物的 |
| 4 | 编辑 LoRA：多角度 / 姿势 / Next-Scene | 继承底模；无量化 | **机位 96 档可控**；姿势可由参考图给定 | +0.2–0.3 GB LoRA，耗时不变 | 可 | 多为 Apache / MIT | 同场正反打、过肩、俯拍；分镜草图链 |
| 5 | 换头 / 选择性换人 LoRA（BFS） | 高：InsightFace 0.735–0.783 对 ReActor 0.216（单机） | 只改脸 / 人，构图光线不动 | 8–20 步 | 可 | LoRA MIT；底模许可照旧 | **修脸不重抽**；多人镜只换一个人 |
| 6 | H3 视频底模取单帧（Ref2VA 单帧 / Still / P-H3 / Contact Sheet） | 高：多人称「几乎完美」「比 H3-Image 更像」 | 中（≥ 3 MP 才好；五视图一次出） | 20–50 步，慢于图像模型 | 可（已在 skill） | H3 社区许可 | 角色视图、训练集自举、剧照 |
| 7 | 身份适配器（PuLID / InstantID / IP-Adapter…） | 中（脸像、发型服装不管） | 高（文生图） | 低 | 可，但绑定 FLUX.1 / SDXL | 权重多依赖 InsightFace（非商用） | SDXL 二次元线；其余已被编辑模型取代 |
| 8 | 角色 LoRA（首帧模型） | **最高**（「要一模一样只能上 LoRA」，saya；Fizgig 0.78 对真实照片互比 0.81） | 高；过训后不听提示词 | 15–40 张图，分钟到 1–2 小时；每角色一次 | Qwen 2.1 / Z-Image / Krea 2 / Anima 均可 | 随底模 | 长期主角、非写实造型、参考图总漂 |
| 9 | 角色 LoRA（H3 视频 DiT） | 脸弱到中、造型画风强（现 skill 结论） | 高 | 40 min – 2 h（24 GB） | 可 | H3 社区许可 | 几十段复用的固定造型；与参考图同用 |
| 10 | 双角色 LoRA + 隔离 / 区域提示 | 隔离后陌生人被同化 48 / 50 → 0 / 50（Krea 2，Fizgig） | 高 | 训练翻倍 | 可 | 随底模 | 两个 LoRA 角色同框 |
| 11 | 3D 预演转绘（假人 / 高斯场景 + 机位） | 继承转绘模型 | **姿势与机位精确**；场景结构稳定 | 多一步摆位；重建 1–2 分钟 | 可 | 工具 MIT；LoRA 随底模 | 复杂姿势、同场 ≥ 6 机位、动作镜 |
| 12 | 九宫格 / 联络表一图多镜 | 格间一致（同一次生成），单格分辨率低 | 中（选格后需单格重绘） | 1–2 次生成出 9 格 | 可（Qwen 2.1 / H3-Image） | 随底模 | 场景多机位母版、分镜选型 |
| 13 | 云端多参考（Seedream / Nano Banana / GPT Image / Kling） | 中上到高，无带参考图的公开横评 | 高；10–16 张参考 | $0.03–0.16 / 张 | 不占 | 各家条款 | ≥ 3 人同框、密集文字、本地两次不过 |
| 14 | 结构控制（ControlNet Union / 深度 / 姿势 LoRA） | 不负责身份 | 构图、姿势锁定 | +3–7 GB | 可 | 随底模 | 与 2、3、8 搭配 |

读法：**2 + 4 + 5 是默认组合**（可商用、零训练）；主角跨 ≥ 30 段再加 8 或 9；姿势与机位要求高时加 11；13 是兜底。

## 5. 交付 (2)：24 GB 本地推荐组合

文件名均为 HuggingFace 上的实际文件名；放置目录沿用现方案。**三套都没有在 4090 上实跑过，参数来自官方模板与作者文档。**

### 5.1 写实（电影质感短剧）· 可商用优先

| 环节 | 模型 / 文件 | 参数 | 来源 |
|------|------------|------|------|
| 锚点（定妆照、正面全身） | Z-Image-Turbo：`z_image_turbo_int8_convrot` + `qwen_3_4b_fp8_mixed`（CLIPLoader type `lumina2`）+ `ae` | `ModelSamplingAuraFlow` 3 → res_multistep / simple 8 步 CFG 1；多 seed 人挑 | 官方模板 `image_z_image_turbo_int8` |
| 派生视图、逐镜首帧 | Qwen-Image-Edit-2511：`qwen_image_edit_2511_fp8mixed` + `qwen_2.5_vl_7b_fp8_scaled` + `qwen_image_vae` | AuraFlow 3.1 → CFGNorm 1 → euler / simple 20 步 CFG 4；草稿挂 `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16` 4 步 CFG 1 | 官方模板；现方案 |
| 同场多机位 | + `fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA` | 强度 0.9–1.0；`<sks> back-left quarter view eye-level shot medium shot` | 模型卡；模板 #2 |
| 指定姿势 | 3D 假人或深度图作第 2 张参考；或 + `lilylilith/AnyPose`（`2511-AnyPose-base-000006250` + `2511-AnyPose-helper-00006000`） | 各 0.7 + Lightning 4 步；参考人物须全身入画 | 模型卡 |
| 脸漂修复 | + `bfs_head_v5_2511_merged_version_rank_16_fp16` | 1.0；20 步 CFG 2.5；裁头部 → 换 → 贴回 | BFS 工作流 #9 |
| 场景母版、九宫格、道具 | Z-Image-Turbo；要 16 MP 或强提示词遵循用 MiniMax-H3-Image（`minimax_h3_image_pruned_int8_convrot` + 现有 H3 编码器 + `minimax_h3_image_vae_fp16`） | 6 步 CFG 1；2688×1536 或 5472×3072；肤质 / 质感发糙换 LCM | 官方模板；讨论区 |
| 主角长期复用 | Fizgig：H3 视频静帧 LoRA（现 skill）；首帧侧可加 Z-Image Turbo LoRA | rank 8、自适应 LR 2e-4–4e-4、0.25 MP、30 epoch、训练适配器开 | Fizgig 文档 |
| 门禁 | YuNet + SFace（现方案）；非商用可换 AdaFace ViT | §7 | — |

非商用项目可升级：锚点换 Qwen-Image 2.1（50 步，现方案）；换头换 `bfs_head_v1.1_qwen_2.1`（8 步，相似度更高的那组数据就是它）；Klein 9B + `Flux2-Klein-9B-consistency-V2` 做 4 步快编辑。

### 5.2 2D 动漫（漫剧）

| 环节 | 模型 / 文件 | 参数 | 来源 |
|------|------------|------|------|
| 锚点与风格探索 | Anima：`anima-base-v1.0` + `qwen_3_06b_base`（CLIPLoader type `stable_diffusion`）+ `qwen_image_vae`；可挂 `anima-turbo-lora-v0.2` | 30 步 CFG 4 euler / simple（或 er_sde）；正向以 `masterpiece, best quality, score_7, safe,` 开头；负向 `worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, sepia`；Turbo 8–12 步 CFG 1 | 官方模板；模型卡 |
| 角色 × 服装 × 表情矩阵 | VNCCS 3.3：Qwen-Image 2.1 int8 + `VNCCS_QI2_PoseStudioV1.1` + `VNCCS_QI2_ClothesCoreV2.6`（`MIUProject/VNCCS_v3.0`） | Pose Studio 出姿势 → 25 步 CFG 1；表情「只改脸再贴回」 | VNCCS 工作流 #5、#7 |
| 逐镜首帧 | Qwen-Image-Edit-2511（同 5.1），提示词带 STYLE LOCK；姿势用假人 / 深度参考，**不要用 AnyPose**（平涂画风失效） | 20 步 CFG 4 | 现方案；AnyPose 模型卡 |
| 全片画风 | 一枚风格 LoRA：Fizgig Qwen 2.1 Style 预设（rank 16、平 LR 1.5e-4、0.5 MP）或 Anima 风格 LoRA；H3 侧用现 skill 的漫剧风格 LoRA | 字幕写「除画风以外的一切」 | Fizgig 文档 |
| 门禁 | deepghs 头部检测 + DINOv2-base（0.62 / 0.48 / 0.40）或 CCIP（差异 ≤ 0.178） | §7 | Fizgig 文档；imgutils |
| 进 H3 | 漫剧可 Ref2VA 直出（现 skill 铁律 17）；首帧只给关键镜 | — | 现 skill |

许可：Anima 输出可商用；Qwen 2.1 及其 LoRA 非商用 → 商用漫剧把矩阵步骤换成 2511（放弃 VNCCS 的 QI2 LoRA，改用 Pose Studio 假人 + 2511）。

### 5.3 3D 国漫 / 三渲二

| 环节 | 模型 / 文件 | 参数 | 来源 |
|------|------------|------|------|
| 锚点 | MiniMax-H3-Image 文生图（3D 渲染风是它的强项之一，官方样张含 3D 角色）或 Krea 2 Turbo `krea2_turbo_int8_convrot`；风格句沿用现 skill 的 3D 国漫类型包 | H3-Image 6 步 CFG 1；Krea 2 8 步 CFG 1 | 模型卡；现 skill |
| 派生视图 | H3 视频底模单帧（Contact Sheet 五视图 / Still，现 skill）—— 3D 质感下它比图像编辑模型更稳的说法来自 H3-Image 讨论区，未量化 | 现 skill 参数 | §3.4 |
| 姿势与机位 | VNCCS Pose Studio 假人；场景复杂时 TripoSplat（`triposplat_fp16`，20 步 CFG 3 dpmpp_2m）→ Blender 机位 → 转绘 | 转绘用 2511；非商用可用 Qwen 2.1 + `QI2.1_AnyAngle` 1.0、CFG 3、≥ 20 步 | 官方模板 #24；AnyAngle 模型卡 |
| 逐镜首帧 | Qwen-Image-Edit-2511；提示词锁「3D 模型精度 + 卡通材质 + 描边」并写「角色参考图全 3D、不出真人版」 | 20 步 CFG 4 | 现 skill 风格包 |
| 全片画风 | 自训风格 LoRA（HF 上没有可用的现成 3D 国漫 LoRA）：20–40 张目标画面，H3 视频侧用 Fizgig | 强度 0.6–0.8 | §3.23 |
| 门禁 | 先试 SFace；检不出脸就切动漫轨（DINOv2） | §7 | — |

### 5.4 什么时候值得花钱用云端出关键帧

1. **一帧里 ≥ 3 个有名有姓的角色 + 指定场景**：2511 原生节点只有 3 个参考槽；本地 10 图的 Qwen 2.1 非商用。用 Nano Banana 2.1（14 张，2K $0.072）或 Seedream 5.5（10 张，$0.029–0.050 + $0.011 × 参考数）。
2. **画面里有必须读得清的多行文字 / 界面**（海报、手机屏、证件）且本地两次不过：GPT Image 2.6（2048×1152 medium $0.052）或 Nano Banana Pro（$0.161）。
3. **同一镜首帧本地 2 个 seed + 1 次换头仍不过门禁**：按现 skill「抽卡有上限」的逻辑，此时换模型比继续抽便宜。
- 量级：一集 60 s ≈ 6–8 张首帧 + 约 10 张资产，全部走云端 2K 也只有 $1–3；所以**本地优先的理由是可复现、可批量、许可与隐私，不是钱**。
- 不值得：场景、道具、草稿、九宫格（本地够用）；任何需要反复迭代同一张图的环节（云端每次整图重画、不可锁 seed 复现）。
- 云端出的图照样过 §7 门禁，并把模型名、日期、提示词写进资产记录；注意各家对未成年人外观、真实人物相似的拒绝策略（现方案已有被拒案例）。

## 6. 交付 (3)：对 `references/image-stage.md` 的修订建议（逐条）

格式：位置｜现文 → 建议｜为什么｜来源。标「待 A/B」的是机制上应改但没人在 4090 上验证过的。

| # | 位置 | 现文（摘） | 建议改为 | 为什么 | 来源 |
|---|------|-----------|---------|--------|------|
| 1 | §1 首段 | 「`PH3ImageConditioning` 不在 0.37.2，只在 master」 | 「`PH3ImageConditioning` 自 **v0.44.0**、`MiniMaxH3ImageConditioning` 自 **v0.45.0** 进入正式版（当前最新 v0.46.2）」；§1 表与 §6 第 15 条里的「升到 master」同步改成「升到 ≥ 0.44 / 0.45」 | 已不需要跑 master | ComfyUI 各 tag 源码，2026-11-21 |
| 2 | §1「H3 自己出静帧」表 P-H3-Image 行 | 「8 步 ManualSigmas euler 无 CFG…最多 8 张图」 | 「**er_sde** + ManualSigmas `1.0, 0.984753, 0.967905, 0.951688, 0.925372, 0.881923, 0.810083, 0.528718, 0.0`；另需 `p-h3-image_text_encoder_int8_convrot` 与 `p-h3-image_vae_int8_convrot`；节点 image_1–9（模型卡写 8）」 | 官方模板的采样器不是 euler，且有专用编码器 / VAE | 模板 `image_p_h3_image_edit`、`image_p_h3_t2i`（11-03）；源码 |
| 3 | §1 选模型表 | （无） | 新增一行 **MiniMax-H3-Image**：`Comfy-Org/MiniMax-H3-Image` 的 `diffusion_models/minimax_h3_image_pruned_int8_convrot`（20.98 GB）+ 现有 H3 文本编码器 + `vae/minimax_h3_image_vae_fp16`；`MiniMaxH3ImageConditioning` → 6 步 CFG 1 euler/simple；用途限定「场景母版 / 九宫格 / 道具 / 海报」 | 11-03 新发布、与 H3 共用编码器、16 MP；但带身份编辑弱 | 模型卡；模板；HF 讨论区 4 条 |
| 4 | §1 表 Z-Image-Turbo 行 | 「8 步 CFG 1 euler / simple（manju-studio）」 | 「官方模板：`ModelSamplingAuraFlow` 3 → **res_multistep** / simple 8 步 CFG 1，CLIPLoader type `lumina2`；euler / simple 为 manju-studio 的用法」 | 以官方模板为基线，避免 type 填错报错 | 模板 `image_z_image_turbo_int8`；lifeidle 踩坑表 |
| 5 | §1 末条 | 「**不要用 Qwen-Image 2.1 附参考图出首帧**：…每张都锁成参考图的正面居中姿势」 | 「Qwen 2.1 的 `image_1` 是**被编辑的图**（画布与姿势跟随它），定妆照放 image_1 就会锁姿势。要改姿势：① 加一张姿势参考（3D 假人渲染或深度图）并在提示词里点名；② 挂姿势 LoRA（如 `VNCCS_QI2_PoseStudio`）；③ 构图图放 image_1、事后换头。未验证前，首帧仍默认 Edit-2511」 | 给出原因与可试的解法，而不是只下禁令（待 A/B） | 节点 tooltip；模板注释；VNCCS / PoseAtlas / BFS 工作流 |
| 6 | §1 许可条 | 只列了 Qwen 2.1 / Edit 2511 / Z-Image / Krea 2 | 补：H3-Image（≤ 100 万美元、排除地区连输出也不能用）；FLUX 3 Klein（Kommunity，< 500 万美元，二手）；Klein 9B 非商用、4B Apache；Anima 模型非商用但输出可商用；Krea 2 的线是公司收入 100 万美元；**InsightFace 权重仅限非商用** | 选型时一次看全 | HF cardData 与 LICENSE 文本 |
| 7 | §1「不用」条 | 只提了 Consistance_Edit_Lora | 新增「推荐挂的 2511 LoRA」：Multiple-Angles（fal，0.9）、AnyPose（0.7 + 0.7，仅写实）、BFS head v5（1.0） | 这三个分别解决机位、姿势、修脸 | §3.1 |
| 8 | §2 表 ② 角色板 | 「左 1/3 头肩特写…右 2/3 正 / 侧 / 背」作为一张生成图 | 「每个视图**单独生成一张单人图**（都只参考锚点），设定板用脚本拼出来给人审；给模型的身份参考永远是单人图」 | 生成的合成板当参考会把人画小；单视图坏了可单独重出 | shuohao character-refs；2511 节点把参考缩到 1 MP |
| 9 | §2 表 ① 定妆照 | 「单人、一格、正面半身」为唯一来源 | 增加「同时冻结一张**正面全身**（由半身 + 外观文字派生一次后不再变），侧 / 背视图从全身图派生」 | 半身看不到下装和鞋，每次由文字补会不一样；H3 实测「只挂全身脸会走样、加大头照最接近」→ 两张都要 | shuohao（H3 实测）；待 A/B |
| 10 | §3 首帧模板 + `assets/image-prompts.md` §6、§7 | `Keep exactly the same person as <image1>` | Edit-2511 的模板改写成 `Picture 1` / `Picture 2`（或 `image 1`）；`<image1>` 只留给 Qwen 2.1 | ComfyUI 给 2511 拼的标签是 `Picture N:`；官方模板写 image 1，BFS 写 Picture 1 | 源码；模板 #1；工作流 #9（待 A/B） |
| 11 | §3 模板清单 | （无） | 新增 5 条：多机位 `<sks> …`；姿势迁移（AnyPose 原句）；换头（BFS 原句）；`Next Scene: …`；光照迁移 | 对应新增的 LoRA | §2 表 |
| 12 | §4 第 4 步 | 「同一场的不同机位从同一张底图编辑」 | 追加「用 Multiple-Angles LoRA 的 96 机位语法转机位；正反打两张都从同一张双人底图转」 | 可控且背景结构不跑 | 模板 #2、#3 |
| 13 | §4 第 4 步 | 「每镜最多 2 个 seed，仍不对就改提示词或换参考裁切」 | 追加第三条出路「构图对、只有脸不像 → 换头修复，不重抽」 | 换头后相似度 0.73–0.78（单机） | §3.25 |
| 14 | §4 第 1 步 | 「之后不再换」 | 落成机器可读：`bible/assets.json` 记每个文件的 sha256、`derived_from`、模型与参数、`frozen`、`stale`；锚点或外观文字变了就把下游标 `stale`（只标不删） | 现在的冻结只是口头约定 | shuohao；wind-comic |
| 15 | §4 第 5 步 | 只有 YuNet + SFace | 保留为默认（许可干净），增加：动漫轨（头部检测 + DINOv2 0.62 / 0.48 / 0.40 或 CCIP ≤ 0.178）；可选 AdaFace ViT（0.42 / 0.36 / 0.30）；每套数据自己的围栏（中位数 − 1.5 × IQR）；多人镜做匈牙利匹配查串脸 | 漫剧现在没有可用门禁 | Fizgig FACE_BACKENDS；imgutils |
| 16 | §5 episode JSON | `first_frame` 每段一张 | 允许 `keyframes: [{t, image}]`：每个子镜头一张关键帧，用 `MiniMaxH3AddGuide.frame_idx` 钉在切点 | 段内每镜构图可控；**开放权重 FL2VA 官方只支持 ≤ 2 张图，≥ 3 张为实验性** | shuohao novel-storyboard；musubi 单帧文档（待 A/B） |
| 17 | §6 禁忌 | 17 条 | 新增：用 H3-Image 出带身份的编辑首帧；给 2511 接第 4 张参考（节点只有 3 槽）；在平涂画风或多人图上用 AnyPose；要改姿势时挂 Consistency LoRA；商用项目用 InsightFace 权重做门禁；用 CLIP 相似度判断动漫角色是否同一人；把成组生成的设定板当身份参考 | 均有出处 | §3 各节 |
| 18 | 文件头「前提」 | 「ComfyUI 0.37.2」 | 注明：H3-Image / P-H3-Image 节点需 ≥ 0.45 / 0.44；其余仍按 0.37.2 | 避免误判「没有节点」 | 同 #1 |

## 7. 交付 (4)：角色一致性自动门禁脚本规格（`scripts/identity_gate.py`，建议）

**目的**：输入角色板 + 一批图或视频帧，输出每张 / 每段的相似度与通过 / 警告 / 不通过；默认只警告（现 skill 口径「分数是警告不是门禁，真实感优先」），`--strict` 才以非零退出码拦截。

**输入**
- `--bible bible/`：读 `assets.json`（或按约定找 `chars/<id>_bust.png`、`_face.png`、`_full.png`、人工认可的额外参考）。每角色 3–5 张基准。
- `--targets`：图片 glob 或 mp4；`--episode ep.json` 时按段读 `character_ids`（期望出现谁）与子镜头切点。
- `--track real|anime|auto`；`--embedder sface|adaface|arcface|dinov2|ccip`；`--strict`；`--out report.json`。

**流程**
1. **取帧**（视频）：首帧、末帧（去掉声明的 1 s 定格）、每个切点后 0.3 s、其余按 2 fps；逐帧独立，不做跟踪链。
2. **检测**：真人轨 YuNet（置信 ≥ 0.6）；动漫轨 deepghs 头部 YOLO（置信 ≥ 0.35）；`auto` = 抽 ≤ 24 张，≥ 50% 检到真人脸且纯动漫脸 < 25% 用真人轨，否则动漫轨（Fizgig 的判定规则）。丢弃短边 < 40 px 的脸并计数。
3. **嵌入**：真人 SFace（默认）/ AdaFace ViT（脸 + 镜像取平均）/ ArcFace；动漫 DINOv2-base（头部裁剪）或 CCIP。同一次运行只用一种嵌入，报告里写明。
4. **自标定**：每个角色的基准图两两互比，得到同人分布；角色之间互比，得到异人分布。若「同人最低 ≤ 异人最高」→ 报 `bible_ambiguous`（撞脸，回去改角色设计，而不是调阈值）。
5. **匹配**：每帧建「检到的脸 × 期望角色」相似度矩阵，匈牙利算法指派。输出：未匹配的脸（多出来的人）、缺席的角色、**串脸**（A 位置的脸更像 B 且反之）。
6. **判定**（每张脸）：`pass` ≥ match；`warn` 在 borderline 与 match 之间；`fail` < borderline 或 < 该角色围栏（基准互比的中位数 − 1.5 × IQR，且不低于 floor）。

| 嵌入 | match | borderline | floor | 出处 |
|------|-------|-----------|-------|------|
| SFace 余弦 | 0.55（严格 0.65） | 0.363 | 0.363 | OpenCV 官方阈值；Zowwan（现方案） |
| AdaFace ViT-Base | 0.42 | 0.36 | 0.30 | Fizgig 2026-11-12 标定 |
| ArcFace（buffalo_l） | 0.45 | 0.30 | 0.25 | Fizgig 旧档；非商用权重 |
| DINOv2-base（头部） | 0.62 | 0.48 | 0.40 | Fizgig 小样本标定 |
| CCIP（差异，越小越像） | ≤ 0.178 | — | — | imgutils 默认，F1 0.917 |

7. **段级汇总**（视频）：每角色的最小值、p10、中位数、低于 borderline 的帧占比、第一处失败的时间码（漂移曲线）；段判定 = 失败帧占比 > 20% 或首帧失败 → `fail`（20%、2 fps、切点后 0.3 s 均为建议默认值，未标定）。
8. **非脸检查（可选，`--costume`）**：人物框遮掉头部后的 DINOv2 相似度对比全身基准；主色 LAB ΔE；`--vlm ollama:<model>` 时用外观文字自动生成 ≤ 8 条是非题（「戴圆框眼镜吗」「外套是深蓝色吗」「手里是那只红色文件夹吗」），逐条返回 yes / no / 看不清。只出警告。
9. **输出**：`report.json`（每文件：期望、检到的脸 [框、置信、像素、指派角色、分数、判定]、多余 / 缺席 / 串脸、服装分、VLM 标记、总判定）+ `summary.csv` + 带框联络表 PNG。写明嵌入名、阈值、被丢弃的小脸数。

**约束**：仅 CPU 可跑（onnxruntime + opencv + numpy；检测 + 嵌入约 0.2–0.4 s / 张，Fizgig 口径）；DINOv2 / CCIP 为可选依赖；不联网下载非商用权重，除非显式 `--allow-nc`。
**验收用例**：① 基准图自己对自己全部 pass；② 两个不同角色互换文件名 → 全部 fail 且报串脸；③ 侧脸 / 背影帧不产生 fail（被计为「无可用脸」）；④ 动漫板在真人轨下报「检测为 0，建议切换动漫轨」。

## 8. 与 H3 流水线对照

**H3 已经原生解决的**
- 片内多参考一致：Ref2VA 一次吃 9 图 / 3 视频 / 3 音频（源码），人物、场景、道具各占槽位 —— 别的生态要靠编辑模型逐帧保证的事，H3 在一次生成里完成。
- 身份保持的单帧生成：H3 视频底模取单帧（Still / Contact Sheet / 单帧 Ref2VA）的相似度被多方认为高于它自己的图像版；五视图一次出，借时间一致性保身份。
- 口型、音色与画面的同次一致：不属于本簇，但意味着「首帧 + H3」比「逐镜出图 + 另配口型」少一个漂移环节。

**可以直接搬进 skill 的（搬到哪）**
| 做法 | 搬到 | 备注 |
|------|------|------|
| 单视图逐张派生、代码拼板、冻结三样 + 过期标记 | `image-stage.md` §2、§4；新增 `bible/assets.json` | §6 #8、#9、#14 |
| 多机位 LoRA 转正反打 | `image-stage.md` §4 第 4 步；`image-prompts.md` 新模板 | §6 #11、#12 |
| 假人 / 深度图给姿势 | `image-stage.md` §4；`storyboard-and-assets.md` §5（动作镜） | 新增可选步骤 |
| 换头修脸 | `image-stage.md` §4；`pitfalls.md`「脸不像」一行 | §6 #13 |
| 分轨门禁脚本 | `scripts/identity_gate.py`；`qc-and-assembly.md` | §7 |
| 每镜关键帧钉切点 | `episode.schema.json`（`keyframes`）；`prompt-format.md` 对齐句 | ≤ 2 张稳，≥ 3 张先做样片 |
| 场景锚点 3–5 个、换时段重出母版、道具状态变体 + 尺度短语 | `storyboard-and-assets.md` §3 | shuohao novel-art |
| 开场走位句（俯视图 → 一句话） | `agent-prompts/02-storyboard.md` | shuohao novel-staging；wind-comic |
| H3-Image 出场景 / 道具 / 九宫格 | `image-stage.md` §1 表 | §6 #3 |
| 超过参考槽位就报错 | `build_prompts.py`（已有上限检查则核对）；首帧脚本对 2511 限 3 张 | AIMovieStudio |

**应该换别的模型的场景**
- 一帧 ≥ 3 个具名角色的首帧 → 云端（§5.4）。
- 需要大量「同角色 × 多服装 × 多表情」静态立绘（漫剧角色库）→ VNCCS，而不是让 H3 逐张出。
- 画面里的可读文字 → Qwen-Image 2.1 / H3-Image / GPT Image，不要指望首帧编辑模型顺手写对。
- 画风探索与定调 → Krea 2 / Anima + 风格参考，定了再训 H3 风格 LoRA。
- 复杂机位 / 一场戏很多机位 → 3D 预演（假人或高斯场景）出构图，再转绘成首帧。

## 9. 来源索引（本轮实际读取，均为 2026-11-21 抓取）

- **ComfyUI 源码**：`Comfy-Org/ComfyUI` tag v0.37.2 / v0.38.0 / v0.40.0 – v0.46.2 的 `comfy_extras/nodes_qwen.py`、`comfy_extras/nodes_minimax_h3.py`；v0.46.2 的 `comfy_api_nodes/nodes_bytedance.py`、`nodes_gemini.py`、`nodes_openai.py`、`nodes_kling.py`（参考上限与价签）。
- **官方模板**：`Comfy-Org/workflow_templates` `templates/index.json`（HEAD）与 §2 所列 JSON。
- **HF 模型卡 / 许可 / 文件列表**：`MiniMaxAI/MiniMax-H3-Image`（含 LICENSE）、`Comfy-Org/MiniMax-H3-Image`、`PrunaAI/P-H3-Image-Comfy`、`Qwen/Qwen-Image-2.1`（含 LICENSE）、`Qwen/Qwen-Image-Edit-2511`、`Tongyi-MAI/Z-Image`、`circlestone-labs/Anima`（含 LICENSE）、`HiDream-ai/HiDream-O1-Image`、`OmniGen2/OmniGen2`、`alibaba-pai/Qwen-Image-2.1-Fun-Controlnet-Union`、`conradlocke/krea2-identity-edit`（含 LICENSE_V2）、`fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA`、`lilylilith/AnyPose`、`lilylilith/QI_2.1_AnyAngle`、`Alissonerdx/BFS-Best-Face-Swap`、`ausboss/Qwen-Image-2.1-Consistency-LoRA`、`akhaliq/Qwen-Image-2.1-Next-Scene-LoRA`、`dx8152/Flux2-Klein-9B-Consistency`、`thedeoxen/Krea-2-pose-controlnet`、`MIUProject/VNCCS_v3.0`、`deepghs/ccip_onnx`；适配器榜单取自 `api/models?filter=base_model:adapter:<基座>`。BFL 各仓库模型卡需登录，未读到。
- **HF 讨论区**：`Comfy-Org/MiniMax-H3-Image` #3 #5 #8 #11 #12 #20；`MiniMaxAI/MiniMax-H3-Image` #9 #10 #19 #23。
- **GitHub README / 文档**：`AHEKOT/ComfyUI_VNCCS`、`ComfyUI_VNCCS_Utils`（另浅克隆读 `utils.py`、`control_center.json`、工作流）；`eternityspring/shuohao-skills`（README + character-refs / novel-art / novel-storyboard 的 README 与 SKILL.md）；`shootthesound/Fizgig`（README + docs/ 的 MINIMAX_IMAGE、QWEN_IMAGE、KREA2、KLEIN、ZIMAGE、ANIMA、TRAINING、INSTALL、FACE_BACKENDS、LORA_ISOLATION）；`kohya-ss/musubi-tuner`（README + docs/minimax_h3_1f.md）；`ostris/ai-toolkit`；`perfectgf/lora-dataset-studio`；`EnragedAntelope/dataset-deviser`；`jtydhr88/ComfyUI-qwenmultiangle`；`NickPittas/ComfyUI_CameraAngleSelector`；`shutong-queyue/ComfyUI-RuiC-PoseAtlas`；`JGRFW/ComfyUI-CharacterCardStudio`；`lbouaraba/comfyui-krea2edit`；`januspluto/ComfyUI-Krea2-Regional`；`iFayens/ComfyUI-PuLID-Flux2`；`astropuzzo/ComfyUI-MiniMax-H3-Image-Studio`；`BExplains/ComfyUI-MiniMaxH3-Image-RefMods`；`sayasaikou/saya-imagegen`（含 docs/krea2-identity-edit.md）；`loyalchiiina/moss-qwen-faceswap`；`lifeidle/comfyui-5090-laptop-24gb-…`；`DevvGwardo/soulfoundry`；`shuyu-labs/BigBanana-AI-Director`；`ChrisChen667788/wind-comic`；`shijue-aid/aid-studio`；`Heroesjouney/AIMovieStudiov2`；`pyoonpyoon/open-higgsfield`；`chfr19820610-cell/AIComics`；`deepinsight/insightface`（许可段）；`deepghs/imgutils`（`metrics/ccip.py`）。星数与末次推送取自 GitHub 搜索 API。
- **网页**：img.ly GenAI Benchmarks「consistency」页（已打开）；FLUX Kommunity 许可的 500 万美元线、Midjourney Omni Reference / V8.2 只来自搜索结果摘要，未打开原文。

## 可写进 skill 的规则

1. 每个角色只生成一次锚点（定妆照 + 一张正面全身），人确认后把文件 sha256、外观文字、画风句写进 `bible/assets.json` 并冻结；其余视图只参考锚点、互不引用，任何一样变了就把下游标 `stale`（shuohao character-refs）。
2. 用脚本拼设定板给人审；给编辑模型和 H3 的身份参考一律用单人单视图，不用模型生成的合成板（shuohao；2511 节点把每张参考缩到 1 MP）。
3. 给 Qwen-Image-Edit-2511 接参考不超过 3 张（`TextEncodeQwenImageEditPlus` 只有 image1–3），脸部参考用脸占满画面的头肩特写，提示词用 `Picture 1` / `image 1` 指图（ComfyUI v0.46.2 源码；官方模板）。
4. 用 Qwen-Image 2.1 编辑时把要保留构图的那张放 `image_1`、身份与服装放 image_2 起；要换姿势就多接一张假人渲染或深度姿势图并在提示词里点名（节点 tooltip；PoseAtlas；VNCCS 工作流）。
5. 同一场戏的正反打 / 过肩 / 俯拍从同一张底图转机位：挂 `fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA` 强度 0.9，提示词写 `<sks> [方位 8 档] [low-angle|eye-level|elevated|high-angle] shot [close-up|medium shot|wide shot]`（模型卡）。
6. 姿势复杂的镜头先用 3D 假人或深度图定姿势再转绘；写实可挂 AnyPose（base 0.7 + helper 0.7 + Lightning 4 步、参考人物全身入画），平涂画风与多人图不要用（AnyPose 模型卡）。
7. 首帧构图对、只有脸不像时换头修复而不是重抽：2511 + `bfs_head_v5_2511_merged_version_rank_16_fp16` 1.0、20 步 CFG 2.5、先裁头部再贴回；修完重新过门禁（BFS 工作流；moss-qwen-faceswap 0.216 → 0.783，单机）。
8. 多人镜只有一个人不对时，用 SAM3 把他涂成 `#FF00FF`，再用 `bfs_body_swap_selective_magenta_v1.0_qwen_2.1` 只换这一个人（BFS 工作流；非商用）。
9. 把 MiniMax-H3-Image 限定在不含指定人物身份的图（场景母版、九宫格、道具、海报）：`minimax_h3_image_pruned_int8_convrot` + 完整 32B 编码器、6 步 CFG 1、≥ 4 MP；人物首帧不用它（HF 讨论区 2026-11-10/11，4 条）。
10. H3-Image 肤质或质感发糙时把采样器换成 LCM（`SamplerLCM` s_noise 1.1 → 0.9、simple、6 步），并给完整英文整图描述或接提示词扩写（讨论区 #5；Fizgig 文档）。
11. P-H3-Image 照官方模板跑：`er_sde` + 8 步 ManualSigmas、`MiniMaxH3SigmaShift` 1 / 1、专用编码器与 VAE，ComfyUI ≥ 0.44（模板 2026-11-03；源码）。
12. Z-Image-Turbo 照官方模板跑：CLIPLoader type `lumina2`、`ModelSamplingAuraFlow` 3、res_multistep / simple 8 步 CFG 1（模板 `image_z_image_turbo_int8`）。
13. 身份门禁分轨：真人用 YuNet + SFace（≥ 0.363 同人、交付 ≥ 0.55）；动漫用头部检测 + DINOv2-base（0.62 / 0.48 / 0.40）或 CCIP（差异 ≤ 0.178）；不要用 CLIP 相似度判断动漫角色同一性（Fizgig FACE_BACKENDS；imgutils）。
14. 用每个角色基准图互比的「中位数 − 1.5 × IQR」做围栏，绝对阈值只作起点；基准里同人最低分不高于异人最高分时回去改角色设计，不要调阈值（Fizgig Look Filter）。
15. 商用项目的门禁与数据清洗不要加载 InsightFace `buffalo_l` / `antelopev2` 权重（仅限非商用研究，InsightFace README）。
16. 角色跨 ≥ 30 段或参考图路线反复漂时才训 LoRA：先训 H3 视频静帧 LoRA；首帧模型的 LoRA 用 Fizgig 预设（Qwen 2.1：rank 8、自适应 LR 2e-4–4e-4、0.5 MP、30 epoch；Z-Image Turbo：rank 8、0.25 MP），训练适配器保持开启（Fizgig 文档）。
17. 自举训练集时每个角色出约 24 张（角度 / 姿势 / 表情 / 光线 / 景别 / 服装 / 背景），先用 3 张基准过相似度筛，再按「脸部特写 + 全身」成对入库（dataset-deviser；Fizgig）。
18. 在训练样张提示词里放一个数据集没有的姿势或角度，保留「最后一个还听话」的 epoch（Fizgig README）。
19. 训双角色 LoRA 时开 Fizgig LoRA Isolation；只训一个人也同训第二个人作锚（Krea 2 上陌生人被同化 48 / 50 → 0 / 50）。
20. 每个场景写 3–5 个一致性锚点并在 QC 时逐镜核对；换时段重新生成母版而不是重打光；道具每个状态一张白底无手图并在提示词里写尺度短语（shuohao novel-art）。
21. 分镜草图链用 `Next Scene: <运镜>, <主体或光线变化>`（LoRA 0.7–0.9）只作审稿，定稿首帧从母版 + 角色参考重出（Next-Scene 模型卡）。
22. 一段内每个子镜头需要独立构图时，每镜一张关键帧用 `MiniMaxH3AddGuide.frame_idx` 钉在切点；开放权重先限制在 ≤ 2 张并做样片（shuohao novel-storyboard；musubi 单帧文档）。
23. 满足任一条再用云端出关键帧：≥ 3 个具名角色同框、密集可读文字、本地 2 个 seed + 1 次换头仍不过；首选 Nano Banana 2.1（14 张参考，2K $0.072）或 Seedream 5.5（$0.029–0.050 + $0.011 × 参考数）（ComfyUI v0.46.2 价签）。
24. 参考图数量超过节点槽位时报错停下，不要静默丢图（AIMovieStudiov2）。
25. 任何新编辑 LoRA 上线前做同提示同 seed 的有 / 无对比并记入 `logs/takes.csv`；Consistency 类 LoRA 只用于「不许动构图」的编辑（ausboss 2026-09-28 更新）。

## 未覆盖

- **没有在 4090 上实跑任何模型**；所有耗时、显存、相似度都是他人的单机数字。§5 三套组合、§6 标「待 A/B」的 4 条尤其需要先做样片。
- 没有找到「带参考图、跨模型、带人脸相似度」的公开横评；ausboss 的三模型对比是视频，未读。Qwen-Image-Edit-2511 与 Qwen 2.1 在 4090 上的峰值显存仍无人实测。
- BFL 仓库在 HF 上需登录：FLUX Kommunity 许可原文、FLUX.2 dev / Klein 的多参考上限、FLUX 3 Klein 的模型卡未读到；Krea 2 社区许可 PDF 未读（只经 Identity Edit 许可转述）。
- 2509 时代的 LoRA（Relight、Light-Migration、next-scene）在 2511 上是否等效未验证；`<image1>` 与 `Picture 1` 两种写法在 2511 上未做 A/B。
- 训练器：OneTrainer / SimpleTuner / diffusion-pipe / sd-scripts 的配方、ai-toolkit 的示例配置未读；24 GB 上各图像基座的训练耗时缺 4090 数字。
- 只确认了存在、许可与模板参数、未评估身份保持的模型：HiDream-O1、OmniGen2、MOSS-Image 编辑、Fibo 2.0、Boogu、Mage-Flow、JoyAI、FireRed 1.1、LongCat、Capybara、Ming Image、ChronoEdit。
- 云端：Kling 4.0 Image、FLUX 3 API、Qwen Image 3.0 Pro、Krea 3、HY Image 3.5、Muse Image、Grok Imagine、MAI Image 的价格与一致性未取；Midjourney 只有二手信息；价签来自 Comfy partner 节点（含加价），不是各家直连价。
- Civitai / LiblibAI 上的 LoRA 与工作流未查（3D 国漫风格 LoRA 多半在那里）；B 站、知乎、Reddit 的教程文字稿未系统抓取，社区证据主要来自 HF 讨论区。
- 3D 路线只读了模板与 README：Blender 具体插件（ComfyUI-Blender）、Daz / MMD 预演、Hunyuan3D-Omni、全景 → 高斯重建（DreamScene360、Pano2Room）未读；IC-Light 系未查近况。
- 服装 / 道具一致性没有找到成熟的专用度量；§7 的 VLM 是非题与 DINOv2 服装分没有标定数据。AdaFace 权重的商用条款、deepghs 检测模型的具体文件名未核实。
- VNCCS 只读了 README、目录代码与两个 Utils 工作流，生成器节点内部的采样参数未读；wind-comic、BigBanana、aid-studio、Nomi、AI-Canvas、manga-generator、AIComics 只读 README。
- `docs/14` 其它簇（01–04）与本文同时撰写，未交叉核对；云端模型的提示词规范、端到端流水线的整体评价以它们为准。
