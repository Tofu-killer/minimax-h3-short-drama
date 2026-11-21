# 生图阶段：定妆照 / 角色板 / 场景母版 + 九宫格 / 道具 / 逐镜首帧 → H3

> 依据：`docs/13-github-survey/05、06、07、09、10、11、12` + 源码精读（mathruffian-dot/shanshiba-workflow-colab `docs/07`、`docs/03`、`tools/gen_image.py`、`make_film.py`；SwotAtmk/infinite-creation `lib/core/prompts.js` 与 `comfyui_original_workflows/NVIDIA/*.json`；wbliang168/manju-studio `gen_zimage_keys.py`；okaypic `gen_sheets.py`、`cast-format.md`；anymouschina/TapCanvas `face-design.md`；manju-laoli `scene-grid-template.md`；chiphoton Codex-Drama `visual-development.md`；Fizgig-H3-Still README）+ HF 文件列表（2026-11-08 抓取）+ ComfyUI `v0.37.2`–`v0.46.2` 各发布 tag 源码（2026-11-21 逐 tag 核对）+ `docs/14-ai-video-workflows/05`（2026-11-21：H3-Image、编辑 LoRA、资产冻结、分轨门禁；LoRA 文件名与触发句同日对照 HF 模型卡与官方模板 JSON）。
> 前提：RTX 4090 24 GB、Windows、ComfyUI 0.37.2（MiniMax-H3-Image 节点需 ≥ 0.45、P-H3-Image 节点需 ≥ 0.44，当前最新 0.46.2；其余仍按 0.37.2）、系统内存 ≥ 32 GB（推荐 64 GB）、只从 HuggingFace / GitHub 下载。「单机实测」= 只有一台机器的数据，口径照抄原作者；「待 A/B」= 机制上应如此、但没人在 4090 上验证过，先做样片再定。`docs/14` 带来的条目没有一条在 4090 上实跑过。

## 0. 流程总览

```
外观文字（六格 + 族裔 + 身高体型 + 标志物）
  → ① 锚点：单张半身定妆照（身份唯一来源）+ 由它派生一次的正面全身（待 A/B）；两张选定后冻结，记进 bible/assets.json
  → ② 派生视图：face.png（头肩特写）/ 90° 侧 / 背，每张单人单视图、只参考锚点 → 脚本拼 16:9 角色板（只给人审）
  → ③ 场景：无人母版（2K）→ 九宫格 → 按镜裁切
  → ④ 道具：1:1 白底单品
  → ⑤ 逐镜首帧：编辑模型 + ①/face.png + ③ 裁切 → 1344×768 字面首帧（同场其它机位从同一张底图转）
  → ⑥ 身份门禁（真人 `identity_gate.py`；动漫 `identity_gate_anime.py`，只判单角色画面）+ 联络表人审 → 写进 episode JSON → H3
```

## 1. 选模型（24 GB、0.37.2、HF 文件名）

ComfyUI 0.37.2 已内置 Qwen-Image 2.1（`TextEncodeQwenImage21`、`QwenImage21Cache`）、Qwen-Image-Edit Plus（`TextEncodeQwenImageEditPlus`）、Krea2、Z-Image 的模型定义（v0.37.2 `comfy_extras/nodes_qwen.py`、`comfy/supported_models.py`）；**两个 H3 出图节点都不在 0.37.2**：`PH3ImageConditioning` 自 **v0.44.0**、`MiniMaxH3ImageConditioning` 自 **v0.45.0** 进入正式版，当前最新 v0.46.2，不必跑 master（逐 tag 源码核对，2026-11-21；v0.37.2 的 `nodes_minimax_h3.py` 544 行，没有这两个类）。

| 用途 | 首选模型 | HF 仓库 / 文件（放入 `models/<子目录>`） | 文件大小 | 采样 |
|------|---------|----------------------|---------|------|
| 定妆照、场景母版、九宫格、道具（文生图） | **Qwen-Image 2.1** | `Comfy-Org/Qwen-Image-2.1`：`diffusion_models/qwen_image_2.1_int8_convrot.safetensors` + `text_encoders/qwen3vl_8b_int8_convrot.safetensors`（CLIPLoader type `qwen_image`）+ `vae/qwen_image_2.1_vae_bf16.safetensors` | 7.26 + 9.35 + 0.68 GB（HF） | 成品 euler / simple **50 步** CFG 1、原生 2K（mathruffian `gen_image.py`，A/B 2026-09-28）；官方模板起步 25 步，官方管线 40–50 步（Comfy 模板注释） |
| 同上·草稿抽构图 | Qwen-Image 2.1 Turbo | 同仓库 `diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors` | 7.26 GB | 固定 8 步 euler + ManualSigmas `1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0`、CFG 1；2K 一张 ~12 s vs 50 步 ~63 s（单机实测 RTX 5090，mathruffian）；皮肤偏光滑、表情漂向微笑、暗部压死 → 只作草稿 |
| 要商用的文生图替代 | Z-Image-Turbo（Apache-2.0） | `Comfy-Org/Z-Image-Turbo`：`split_files/diffusion_models/z_image_turbo_int8_convrot.safetensors` + `split_files/text_encoders/qwen_3_4b_fp8_mixed.safetensors`（CLIPLoader type `lumina2`，填错会报错，lifeidle 踩坑表）+ `split_files/vae/ae.safetensors` | 6.20 GB DiT（HF） | 官方模板：`ModelSamplingAuraFlow` 3 → **res_multistep** / simple 8 步 CFG 1（模板 `image_z_image_turbo_int8`）；euler / simple 是 manju-studio 的用法；img2img 锁脸 denoise 0.45–0.55 保五官构图、0.60–0.70 换景别仍同脸、> 0.8 洗掉（manju-studio，作者经验值） |
| 写实超真人定妆照 / 漫剧风格 LoRA | Krea 2 Turbo | `Comfy-Org/Krea-2`：`diffusion_models/krea2_turbo_fp8_scaled.safetensors` + `text_encoders/qwen3vl_4b_fp8_scaled.safetensors`（type `krea2`）+ `vae/qwen_image_vae.safetensors`；风格 LoRA 同仓库 `loras/krea2_retroanime.safetensors` 等（触发词见模型卡） | 13.14 GB DiT | 8 步 CFG 1 euler / simple（mathruffian；infinite-creation 三视图工作流） |
| **派生视图、逐镜首帧、换装、改已有帧（编辑）** | **Qwen-Image-Edit-2511**（Apache-2.0） | `Comfy-Org/Qwen-Image-Edit`：`split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors`（或同目录 `_int8_convrot`）+ `Comfy-Org/Qwen-Image`：`split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`、`split_files/vae/qwen_image_vae.safetensors` | 20.53 + 9.38 + 0.25 GB（HF） | `ModelSamplingAuraFlow 3.1` → `CFGNorm 1.0` → euler / simple **20 步 CFG 4**（mathruffian；Comfy 模板表「Comfy 20 / Qwen 40 步，CFG 4」）；1 张参考 ~47 s、2 张 ~85 s（单机实测 RTX 5090），16 GB + 32 GB 内存模拟 50–55 s（mathruffian） |
| 编辑·草稿 | 同上 + Lightning LoRA | `lightx2v/Qwen-Image-Edit-2511-Lightning`：`Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`（另有 8steps） | 0.85 GB | 4 步 CFG 1（infinite-creation 2511 工作流的 4 步开关）；对身份保持的影响未测 |
| 场景母版、九宫格、道具、海报（**只出不含指定人物身份的图**；要 16 MP 或强提示词遵循时用） | MiniMax-H3-Image（2026-11-03 发布，33.1B；需 ComfyUI ≥ 0.45） | `Comfy-Org/MiniMax-H3-Image`：`diffusion_models/minimax_h3_image_pruned_int8_convrot.safetensors` + `vae/minimax_h3_image_vae_fp16.safetensors` + 现有 H3 文本编码器（`qwen3vl_32b_minimax_h3_*`，CLIPLoader type `minimax`；必须是完整的 32B，讨论区 #8、#10） | 20.98 + 1.17 GB（HF；已装 H3 的机器只多下约 22 GB） | `MiniMaxH3ImageConditioning` → 6 步 CFG 1 euler / simple（官方模板 `image_minimax_h3_image_edit`）；工作区间 4–20 MP（16:9 的 16 MP = 5472×3072）；肤质 / 质感发糙换 LCM（`SamplerLCM` s_noise 1.1 → 0.9、simple、6 步；讨论区 #5、Fizgig 文档）；提示词写长的英文整图描述或接提示词扩写；2688×1536 暖机后 11–12 s / 张、16.5 MP 约 41 s、内存占用约 41 GB（单机实测 RTX 4070 SUPER 12 GB + 96 GB 内存，LIOSAM007；4090 无实测） |

- 显存：表中都是 HF 文件大小，**4090 峰值显存无人实测**；Edit 2511 的 DiT 20.5 GB + 编码器 9.4 GB 靠 ComfyUI 自动卸载，mathruffian 在「16 GB 显存 + 32 GB 内存」模拟下跑通 → 24 GB + 32 GB 内存足够，int8_convrot 版在 4090 上未验证。
- 许可：**Qwen-Image 2.1 是 qwen-research（非商用）**（HF 模型卡；mathruffian `THIRD_PARTY_NOTICES`）；Edit 2511、Z-Image-Turbo、Lightning 为 Apache-2.0；Krea 2 为 krea-2-community，公司收入 ≥ 100 万美元需企业授权（经 Identity Edit 许可转述，许可原文未读）；**MiniMax-H3-Image**：年收入 ≤ 100 万美元且不做托管服务可商用、产品界面须显示模型名，**排除地区（欧盟 / 英 / 韩 / 美）连输出也不能用**（LICENSE §V.4）；FLUX.2 Klein 9B 非商用、**4B 为 Apache-2.0**；FLUX 3 Image Klein 为 FLUX Kommunity（年收入 < 500 万美元可商用，二手来源，原文未读）；Anima 模型与 LoRA 非商用、**输出可商用**（LICENSE §2e）；**InsightFace `buffalo_l` / `antelopev2` 权重仅限非商用研究**（InsightFace README）。要营利：定妆照 / 母版改 Z-Image-Turbo 或 Edit 2511 文生图，首帧仍用 Edit 2511（mathruffian「首幀不用換」）。
- **Edit-2511 怎么吃参考图**（v0.46.2 `comfy_extras/nodes_qwen.py`）：`TextEncodeQwenImageEditPlus` 只有 `image1`–`image3` 三个图像输入，并在提示词前自动拼 `Picture 1: `、`Picture 2: `、`Picture 3: ` 标签；每张参考给 Qwen2.5-VL 看的是 384×384 面积的缩略图、给 DiT 的参考潜变量缩到 1 MP → **参考图里脸占画面越大越像**，多格板缩到 1 MP 后每张脸只剩一两百像素。所以参考合计 ≤ 3 张，身份参考用单人图，脸部参考用脸占满画面的头肩特写。
- 不用：chiphoton Codex-Drama 的 `Qwen-Rapid-AIO-NSFW-v19`（28.4 GB 第三方 AIO 合并包）；它配的一致性 LoRA `lrzjason/Consistance_Edit_Lora` 有 2511 版 `qe2511_consis_alpha_patched.safetensors`，chiphoton 用 v2 版 0.8 强度，在 2511 官方权重上的效果未验证。
- **推荐挂的 2511 LoRA**（分别解决机位、姿势、修脸；触发原句见 §3 与 `../assets/image-prompts.md` §8–§10；都没有在 4090 上实跑过，上线前各做一次同提示同 seed 的有 / 无对比并记进 `logs/takes.csv`）：

| LoRA | HF 仓库 / 文件（放入 `models/loras`） | 强度与采样 | 限制 |
|------|------|------|------|
| Multiple-Angles（转机位） | `fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA`：`qwen-image-edit-2511-multiple-angles-lora.safetensors`（Apache-2.0） | **0.9**（模型卡 0.8–1.0；官方模板 1.0）；`<sks> [方位] [俯仰] [距离]`，8 × 4 × 3 = 96 机位，3000+ 对高斯泼溅渲染训练；4 步 Lightning CFG 1 抽、40 步 CFG 4 定（官方模板） | 无带人脸相似度的评测；大角度（背面、俯 60°）会补画看不见的部分，需人审 |
| AnyPose（姿势迁移，**仅写实单人**） | `lilylilith/AnyPose`：`2511-AnyPose-base-000006250.safetensors` + `2511-AnyPose-helper-00006000.safetensors`（Apache-2.0） | base 0.7 + helper 0.7 + Lightning 4 步 CFG 1；一张姿势图当参考，无需 ControlNet；被摆姿势的人全身（连地面）入画最稳（模型卡） | 平涂 / 像素风失效、多人失效（作者自述）→ 漫剧不用 |
| BFS head v5（脸漂了换头） | `Alissonerdx/BFS-Best-Face-Swap`：`bfs_head_v5_2511_merged_version_rank_16_fp16.safetensors`（MIT） | **1.0**；euler / simple 20 步 CFG 2.5，`ModelSamplingAuraFlow` 1.0、CFGNorm 1.0（BFS V5 工作流）；Picture 1 = 身体底图、Picture 2 = 头部参考，顺序不能反 | 2511 + v5 的换头相似度无量化（已有数字是 Qwen 2.1 版的）；修完必须重新过门禁；只换本项目自己生成的角色（作者：不用于公众人物或未经同意的真人） |

- 另两枚只在特定场合用（文件与原句见 `../assets/image-prompts.md` §11–§12）：**Next-Scene**——要快速出一场戏的分镜草图给用户审时用，只作审稿，定稿首帧仍从母版 + 角色参考重出，不直接用链尾（链越长漂移越大，无身份量化；2511 上是否可用未验证）。**Light-Migration**——同场首帧光线不齐先查母版与提示词里的光源句，后期统一调色更便宜；这枚 LoRA 观望（待 A/B：是否伤身份未验证，做完必须再过门禁），换时段是重新生成母版而不是重打光（shuohao novel-art）。
- **Qwen-Image 2.1 附参考图出首帧会锁姿势，原因在接线**：`TextEncodeQwenImage21` 的 `image_1` 是**被编辑的图**（画布与姿势跟随它，其余才是参考；节点 tooltip，Comfy 模板注释「image_1 is the edit target」），定妆照放 `image_1` 时长相像，但每张都锁成它的正面居中姿势，「侧脸看窗外」也照样正面（mathruffian docs/07 实测）。接法：要保留构图的那张放 `image_1`，身份与服装从 image 2 起。要改姿势有三条路（社区工作流的实际用法，**均未在 4090 验证，待 A/B**）：① 多接一张姿势参考（3D 假人渲染或深度图；线稿假人的留白会被当成身体，转成深度图更稳，PoseAtlas）并在提示词里点名；② 挂姿势 LoRA：`MIUProject/VNCCS_v3.0` 的 `VNCCS_QI2_PoseStudio` 系列（HF 文件列表有 V1–V3；1.0，25 步 CFG 1），假人渲染放 image 1、角色放 image 2，提示词 `replace the pose of <image 2> with the pose of <image 1>. keep the character of <image 2>`（VNCCS 工作流）；③ 构图图放 `image_1`，事后换头（§3【换头】）。验证前首帧仍默认 Edit-2511；Qwen 2.1 的编辑模式（最多 10 图 `<image1>`，Comfy 模板）先只用于换装这类不改姿势的编辑。

### 什么时候用 H3 自己出静帧

身份保持是 H3 视频权重的强项：多位用户称用视频底模取单帧做角色表「几乎完美」、比 H3-Image 更像（HF 讨论区 2026-11-10/11，未量化）→ 带身份的角色视图 / 剧照走下表的单帧路线，不走 H3-Image。

| 方案 | 配方 | 用在 |
|------|------|------|
| Fizgig H3 Still（custom node，≥ 0.37 可用） | fl2va pruned int8 + `larryvrh/MiniMax-H3-Turbo-Lora` 的 `minimax_h3_turbo_v4_step600_ema.safetensors` **0.38** + er_sde / simple **20 步**，≥ 3 MP（如 2304×1296）；8 MP 无 Turbo 50 步；编辑走 `MiniMaxH3ReferenceToVideo` `<Picture 1>` 在 2.5 MP（Fizgig README） | 不想再下 30 GB 图像模型时出剧照、海报、关键帧；小于 3 MP 明显变弱 |
| Contact Sheet 五视图（MAINodes） | `matlod/minimax-h3-turnaround`：`minimax_h3_five_view_512_s1500.safetensors` 1.0（转角好）或 `_1024cont_s600` 0.75，res_multistep / simple 28 步 denoise 1.0，一张 `<Picture 1>`；消费卡靠内存卸载，需 ~50 GB 内存镜像（07 survey）；**用完立刻卸 LoRA**（T8：留着会毁运动） | 已有一张定妆照，要同一次生成里出 5 个角度（借时间一致性保身份） |
| OrbitSheets | 硬切 6 视图、每视图 0.75 s、124 帧，`[Shot N] At 00:MM.mmm, the shot cuts to … locked-off static camera`（lumosai8） | 要带表情 + 顺带一段音色样本的角色页 |
| P-H3-Image（`PH3ImageConditioning`，ComfyUI ≥ 0.44） | `PrunaAI/P-H3-Image-Comfy`（HF 上该仓库现重定向到 `PrunaAI/P-Image-OSS-Comfy`，`p-h3-image_*` 文件仍在，2026-11-21）：在 fl2va 上挂 `loras/p-h3-image_lora_bf16.safetensors`（2 GB，Load LoRA Bypass 1.0）+ 专用的 `text_encoders/p-h3-image_text_encoder_int8_convrot.safetensors` 与 `vae/p-h3-image_vae_int8_convrot.safetensors` + `ModelSamplingMiniMaxH3` 1.0 / 1.0；8 步 **er_sde** + ManualSigmas `1.0, 0.984753, 0.967905, 0.951688, 0.925372, 0.881923, 0.810083, 0.528718, 0.0`、无 CFG（官方模板 `image_p_h3_image_edit`、`image_p_h3_t2i`，2026-11-03；不是 euler）；文生图 8 MP（16:9 = 3872×2176），编辑 4 MP（2720×1536）；节点 `image_1`–`image_9`（模型卡写最多 8 张）；最小整套峰值 21 GB @ 8 MP（模型卡） | **需 ComfyUI ≥ 0.44**（0.37.2 无此节点，不必上 master）；MiniMax H3 社区许可排除欧盟 / 英国 / 韩国 / 美国（澳洲不在排除列表） |

## 2. 版式与分辨率

- **全部宽高为 32 的倍数**（Qwen 2.1 模板「Prefer multiples of 32」、Fizgig、`PH3ImageConditioning` 的 `CANVAS_MULTIPLE`）。1080 不是 32 倍数：infinite-creation 的 Krea2 工作流写 1920×1080，改 1920×1088。
- **脸部光**：哑光、均匀主光。H3 片中脸部油光取决于参考图的肤质而不是量化（animede，09 survey）；电影质感首帧写「单一真实光源 + 一致的阴影方向」（mathruffian docs/07 §3b，仅在云端 Image 2.5 上 A/B 过）。

| 资产 | 画布 | 版式规则 |
|------|------|---------|
| ① 定妆照（锚点） | 1024×1024 | 单人、一格、正面半身、浅灰无缝背景、柔和均匀光（mathruffian）；外观写到下装与鞋，否则全身镜随机配裙或长裤（mathruffian）；多 seed 挑一张后**冻结** |
| ① 正面全身（锚点，待 A/B） | 竖幅 1024×1536（2:3，按 32 格点推算） | 由 ① 半身 + 外观文字用编辑模型**派生一次**，人确认后同样冻结、不再变：半身看不到下装和鞋，每次由文字补会不一样；侧 / 背视图从它派生（shuohao character-refs）。给 H3 时两张都要：只挂全身脸会走样，加大头照脸最接近（shuohao 的 H3 实测，本 skill 待 A/B） |
| ② 派生视图 → 角色板 | 每个视图一张单人图（全身视图同上竖幅）；拼好的板 2688×1536（Qwen 2.1 2K 默认，mathruffian；7:4）或 2560×1440（真 16:9，按 32 格点推算） | **每个视图单独生成一张单人图**（face.png、纯 90° 侧、背），都只参考锚点、互不引用，哪张坏了单独重出；16:9 角色板用**脚本拼**出来只给人审（`scripts/make_character_board.py`），不当参考——合成板当参考会把人画小（shuohao character-refs；2511 把每张参考缩到 1 MP）。板的版式：左 1/3 头肩特写（全图唯一清晰脸），右 2/3 正 / 纯 90° 侧 / 背全身同比例；每个全身视图头顶到鞋底留白边，双臂自然下垂、手里空、中性表情闭嘴、纯白无缝背景、无文字（infinite-creation `CHARACTER_T2I_LAYOUT_CONSTRAINT`；okaypic；manju-laoli「立绘纯净：不手持道具」）；写头身比（manju-laoli） |
| face.png | 1024×1024（短边 1024） | 由 ① 半身单独出的正脸头肩特写，脸占满画面（2511 把参考缩到 1 MP，脸越大越像）；给编辑模型当参考、也作 H3 `reference_images[0]`；参考图短边 1024 比 2048 快约 15%、同 seed 画质相当（animede，单机） |
| ③ 场景母版 | 2688×1536（mathruffian）；用 MiniMax-H3-Image 可到 5472×3072（16 MP，官方模板） | 无人；人眼高主机位轴；门窗家具主道具位置写清；写一个主光源和方向；默认晴朗白昼（manju-laoli）；背景一句话带过、写 uncluttered，逐项列物件会杂乱（mathruffian） |
| ③ 九宫格 | 整板 16:9，2688×1536 | 恰好 9 格、同一空间仅机位变化（模式 A）；室内机位表：进门视角 / 主活动区全景 / 窗侧光位 / 门框反打 / 俯视平面 / 对角长焦压缩 / 陈设特写 / 墙侧细节 / 窗外空镜；统一 50 mm、统一曝光白平衡；格内标签糊了就降级为数字 1–9 + 图外对照表，重试 ≤ 2 次（manju-laoli）；1 张 = 9 视角 = 1 个参考槽（05 survey） |
| ③ 按镜裁切 | 裁到该镜景别，长边 ≤ 1344 | 附整张母版会被照抄成大全景（mathruffian `masters()`） |
| ④ 道具 | 1:1，2048×2048（Qwen 2.1 原生 2K） | 纯白背景、只有该物件、真实文字写清内容和位置（infinite-creation 道具规则）；要透明底：`This is an RGBA format image with transparency. … The image has an alpha channel and a transparent background.` 存 PNG（Comfy 模板注释） |
| ⑤ 首帧 | **等于 H3 生成画布**：1344×768（竖屏 768×1344） | 字面首帧，不是拼贴设定板、无标签无 UI（05 survey #30；chiphoton）；动作镜画「动作开始前」的姿势，跳跃留头顶空间（mathruffian docs/03）；场景里的实物文字（屏幕、招牌）画进首帧，UI / 字幕 / 等级框仍后期叠（mathruffian checklists；本 skill 铁律 6） |

## 3. 提示词模板（英文，正向写法；全文另存 `../assets/image-prompts.md`）

防撞脸（每个角色都要过）：
- 脸用 **3–5 处骨相**，按「脸型 → 颧骨 → 下颌下巴 → 眉骨眼窝 → 眼 → 鼻 → 嘴」取前几处；同项目任意两人骨相 ≥ 3 处不同、发型 / 体型 / 体态 / 主色 / 标志五格 ≥ 2 格不同；`straight high nose bridge`、`black hair in a bun`、`tall and slender` 这类高频词同项目只许出现一次（TapCanvas：十余张卡里「鼻梁挺直」出现 7 次）。
- 写**族裔**（名字不传递外观，「Nadia Volkov」没写 Eastern European 出成东亚脸）、`about {height_cm} cm tall with a {build} build`（不写人人中等身材）、**一个跨场景标志物**（okaypic）。
- 主角在骨相后加一句颜值定位（`a striking, cool-toned beauty`），只此一句评价词（TapCanvas）；未满 18 岁只写骨相与年龄感，不写唇形、身材曲线（TapCanvas：整张被拒的案例）。
- 不写 `photorealistic, 8K, masterpiece, flawless, perfect, beautiful`：出广告脸 + 金黄 HDR，4 张有 3 张自己加标语（mathruffian，仅在 Image 2.5 上测）。
- 以 `Clean frame containing only the depicted subject.` 收尾代替「no text」（okaypic）。Qwen 2.1 / Z-Image / Krea2 都是 CFG 1，负向框无效（Comfy 模板注释）；只有 Edit 2511（CFG 4）负向框生效，排除词只放那里。

指图与 LoRA 原句：
- **Edit-2511 的模板用 `Picture 1` / `Picture 2` / `Picture 3` 指图**：节点自动拼在提示词前的标签就是 `Picture N: `（v0.46.2 源码；官方模板写 `image 1`，BFS 写 `Picture 1`）；`<image1>` 是 Qwen-Image 2.1 节点的语法，只留给 Qwen 2.1。两种写法在 2511 上的效果差别待 A/B。模板里的 `Picture {K}` = 场景裁切的图号（最后一张，K ≤ 3）。
- **LoRA 触发句逐字照抄作者原句**：AnyPose 原句用 `image 1` / `image 2` 且自带 `…is undesirable, so don't do it`，BFS 原句自带 `remove the head…`，光照迁移原句自带「移除…」——这些是作者 / 官方模板的触发写法，不算自由否定句；自己追加的内容仍只写正向。

模板（`{}` 为占位；电影质感 = A，漫剧 = B）：

```text
[定妆照 A] Studio character reference photo, a single person in one image, medium close-up bust portrait facing the camera at eye level, plain light grey seamless background, soft even studio light with a matte skin finish, sharp focus, realistic photograph. {ETHNICITY} {GENDER} of {AGE}, {3-5 BONE TRAITS}, {HAIR}, {SKIN}, wearing {TOP}, {BOTTOM}, {SHOES}, {SIGNATURE ITEM}. {APPEAL LINE (leads only)} Gentle natural expression, lips closed. Clean frame containing only the depicted subject.
[定妆照 B] Anime character bust portrait, a single character in one image, facing the viewer at eye level, plain white background, even flat lighting, {STYLE LOCK: clean dark line art, flat cel shading with two-tone shadows, warm pastel palette}. {ETHNICITY} {GENDER} of {AGE}, {3-5 BONE TRAITS}, {HAIR}, {EYE COLOR}, wearing {TOP}, {BOTTOM}, {SIGNATURE ITEM}. Calm expression, mouth closed. Clean frame containing only the depicted subject.
[派生视图 A·Edit 2511] Keep exactly the same person as Picture 1: same face, hairstyle, outfit, accessories and marks ({LOOK, verbatim}). New photo: a character reference view of this one person alone on a seamless pure white background, soft even studio lighting with a matte skin finish. {VIEW} About {HEIGHT_CM} cm tall with a {BUILD} build, true body proportions of {7} heads tall. One single person, the only subject in the image. Live-action photograph, 85mm lens look, natural skin texture, true-to-life colors. Clean frame containing only the depicted subject.
[派生视图 B·Edit 2511] Keep exactly the same character as Picture 1: same face, hairstyle, outfit, line weight and colors ({LOOK, verbatim}). New frame: an anime character model view of this one character alone on a seamless pure white background, even flat lighting, {STYLE LOCK}. {VIEW} About {HEIGHT_CM} cm tall with a {BUILD} build, consistent proportions of {6} heads tall. One single character, the only subject in the image. Clean frame containing only the depicted subject.
[{VIEW} 取值] 正面全身（Picture 1 = bust；出一次、确认后冻结）: Full-body front view standing upright, from the top of the head to the soles of the shoes with a little white margin above and below, arms relaxed at the sides, hands empty, calm neutral expression, lips closed. ｜ face.png（Picture 1 = bust）: Front-facing head-and-shoulders close-up at eye level with the face filling the frame, calm neutral expression, lips closed, looking into the camera. ｜ 90° 侧（Picture 1 = 正面全身）: Full-body strict 90-degree side view standing upright, from the top of the head to the soles of the shoes with a little white margin above and below, same scale and camera distance as Picture 1, arms relaxed at the sides, hands empty. ｜ 背（Picture 1 = 正面全身）: Full-body back view standing upright, from the top of the head to the soles of the shoes with a little white margin above and below, same scale and camera distance as Picture 1, arms relaxed at the sides, hands empty.
[场景母版 A] A cinematic film still of an empty {PLACE}, wide establishing view at eye level from {CAMERA SPOT} looking {DIRECTION} along the main axis, 16:9. {LAYOUT: the door on the left wall, a tall window on the right wall, a desk at the centre}. {TIME OF DAY}: one key light, {SOURCE} from {DIRECTION}, shadows falling toward {DIRECTION} with soft falloff and detail kept in the shadows. Shot on a 35mm lens at f/4, deep focus, true-to-life colors, uncluttered. The space holds only its architecture and furniture, deserted and still.
[场景母版 B] An anime background painting of an empty {PLACE}, wide establishing view at eye level from {CAMERA SPOT}, 16:9, painted style matching the character sheets, {STYLE LOCK}. {LAYOUT}. {TIME OF DAY} light from {DIRECTION} in flat cel-shaded blocks. The space holds only its architecture and furniture, deserted and still.
[九宫格 A/B] One 16:9 location board divided into exactly nine equal panels in a 3x3 grid with thin white gutters. All nine panels show the same empty {PLACE} with identical architecture, furniture positions, materials, colors, time of day and light direction; only the camera position changes. 1 view from the doorway into the room; 2 wide view of the main activity area; 3 the window side with the light falling in; 4 reverse view from inside toward the door; 5 high overhead view of the floor layout; 6 long-lens diagonal view from one corner to the opposite corner; 7 close view of {SIGNATURE FURNITURE}; 8 close view of {WALL DETAIL}; 9 the view out of the window. A small numeral 1-9 in each panel's top-left corner. Uniform 50mm lens, bright even exposure, one white balance. The place: {SCENE DESCRIPTION, verbatim from the bible}. {STYLE LINE of A or B}. Every panel is a deserted space.
[道具 A] Product reference photo of {ITEM}, one object centered on a seamless pure white background, 1:1, three-quarter front view at eye level, soft even studio light with a soft contact shadow beneath it, {MATERIAL}, {COLOR}, {WEAR MARKS}, {REAL TEXT: the label reads "{TEXT}" in {COLOR} block letters at the upper left}, about {SIZE} cm long. Sharp focus across the whole object, true-to-life colors. The frame contains only this one object.
[道具 B] Anime prop illustration of {ITEM}, one object centered on a pure white background, 1:1, three-quarter front view, {STYLE LOCK}, {MATERIAL AND COLOR}, {REAL TEXT}, about {SIZE} cm long. The frame contains only this one object.
[首帧·Edit 2511 A] Keep exactly the same person as Picture 1: same face, hairstyle and clothes ({LOOK, verbatim}). {Keep exactly the same person as Picture 2: … ({LOOK})}. The room is the one in Picture {K}: same walls, furniture and light direction. New photo: A cinematic film still from a {GENRE} drama, shot on Kodak Vision3 500T film with an anamorphic 50mm lens at f/2. {FRAMING}, {WHO stands WHERE doing WHAT at the first instant, EXPRESSION}. Exactly {N} people in the frame. {ONE LIGHT SOURCE, direction, color}.
[首帧·Edit 2511 B] Keep exactly the same character as Picture 1: same face, hairstyle, outfit, line weight and colors ({LOOK}). The place is the one in Picture {K}. New frame: a frame from a 2D anime episode, {STYLE LOCK}. {FRAMING}, {WHO WHERE DOING WHAT, EXPRESSION}. Exactly {N} characters in the frame.
[换装子资产·Edit 2511] Keep exactly the same person as Picture 1: same face, skin, hairstyle, body proportions and height. Change only the clothing to {NEW OUTFIT}. Same view, same pose, same pure white background, same lighting.
[Edit 2511 负向框，仅 CFG 4 时] text, watermark, caption, collage, split panels, extra person, extra fingers, waxy skin
[多机位·Edit 2511 + Multiple-Angles LoRA 0.9] <sks> {AZIMUTH} {ELEVATION} {DISTANCE}
[多机位·取值] AZIMUTH: front view / front-right quarter view / right side view / back-right quarter view / back view / back-left quarter view / left side view / front-left quarter view. ELEVATION: low-angle shot / eye-level shot / elevated shot / high-angle shot. DISTANCE: close-up / medium shot / wide shot. 例: <sks> front-right quarter view eye-level shot medium shot
[姿势迁移·Edit 2511 + AnyPose base 0.7 + helper 0.7，作者原句] Make the person in image 1 do the exact same pose of the person in image 2. Changing the style and background of the image of the person in image 1 is undesirable, so don't do it. The new pose should be pixel accurate to the pose we are trying to copy. The position of the arms and head and legs should be the same as the pose we are trying to copy. Change the field of view and angle to match exactly image 2. Head tilt and eye gaze pose should match the person in image 2.
[换头·Edit 2511 + BFS head v5 1.0，作者原句] head_swap: start with Picture 1 as the base image, keeping its lighting, environment, and background. remove the head from Picture 1 completely and replace it with the head from Picture 2, strictly preserving the hair, eye color, and nose structure of Picture 2. copy the eye direction, head rotation, and micro-expressions from Picture 1.
[分镜草图链·Next-Scene LoRA 0.7–0.9] Next Scene: {CAMERA MOVE}, {WHAT IS REVEALED OR HOW THE SUBJECT / LIGHT CHANGES}.
[光照迁移·Edit 2509 + Light-Migration LoRA 1.0，官方模板原句] 参考色调，移除图1原有的光照并参考图2的光照和色调对图1重新照明
```

## 4. 一致性工作流

1. **定妆照**（Qwen 2.1 50 步，或 Z-Image-Turbo）：同一外观文字跑 4–8 个 seed，人挑一张，存 `bible/chars/<id>_bust.png`，之后不再换（mathruffian）；「冻结」要落成机器可读，记进 `bible/assets.json`（布局见本节「冻结与过期记录」）。外观文字（LOOK）存进系列圣经，**每一镜首帧原样照抄**，少写一次就掉眼镜换发型（mathruffian `frames()`）。
2. **正面全身 + 派生视图**：Edit 2511 以 bust 为 Picture 1 套【派生视图】模板出一张**正面全身**（`<id>_full.png`），人确认后与 bust 一起冻结（待 A/B）；再逐张出 face.png（参考 bust）、纯 90° 侧与背（参考正面全身），每张单人单视图、只参考锚点、互不引用（编辑模型保脸，mathruffian「長相像」；shuohao character-refs）。16:9 角色板用脚本把这几张拼起来（`<id>_sheet.png`）只给人审。备选：Contact Sheet 从 bust 出五视图，逐视图存成单人图再拼板。infinite-creation 的做法是把一张现成三视图板当第 1 张参考让 2511 照「排版格式」出新人物（它的 2511 工作流示例提示）；这条路把版式当参考，身份另靠文字，出的是合成板，只作备选且只给人审。
3. **变体**：换装 / 年龄变体用【换装子资产】从冻结的正面全身编辑（侧 / 背再从变体全身派生），每套变体也是一组单人单视图，优先级 `costume > age > 原图`（本 skill §3 资产表）。
4. **逐镜首帧**：Edit 2511，参考合计 ≤ 3 张（节点只有 `image1`–`image3`），顺序 = 每个入画角色的 bust / face.png（2 人实测可行）→ 最后一张场景裁切（mathruffian）；超槽（≥ 3 个具名角色 + 场景）就停下来，不静默丢图（AIMovieStudiov2）——非商用可换 10 图的 Qwen-Image 2.1，或按本节「什么时候花钱用云端出关键帧」的条件走云端；把几张身份图 `ImageStitch` 拼成一张等于多格板（§6 第 1 条），不用。1344×768 直接出。
   - **同场多机位**：同一场的不同机位从**同一张底图**编辑，首尾帧也从同一张图改（mathruffian docs/03：换机位背景会跑）；转机位用 Multiple-Angles LoRA 的 96 机位语法（§3【多机位】），正反打两张都从同一张双人底图转（官方模板 `templates-1_click_multiple_character_angles-v1.0`、`template_rob_split_stack_qwen_multi_wan22` 都是一张输入图出多个机位）。转完人审 + 过门禁。
   - **姿势**：靠文字写不稳时，接一张 3D 假人渲染或深度图当姿势参考并在提示词里点名（占一个槽；编辑模型吃假人 / 深度图比吃 OpenPose 骨架稳，AnyPose 作者、PoseAtlas 的经验，未在 4090 验证）；写实单人可用【姿势迁移】，漫剧不用。
   - **不过怎么办**：每镜最多 2 个 seed，仍不对就改提示词或换参考裁切（本 skill 铁律 10 的同一逻辑）；第三条出路——构图 / 光线 / 姿势都对、只有脸不像 → 用【换头】修复，不重抽，修完重新过门禁。换头的量化只有一组单机实测，且测的是 Qwen 2.1 + BFS：InsightFace 余弦原图 0.129、ReActor 0.216、换头 0.735、先放大到 1536×2048 再换 0.783，同人上限约 0.94（moss-qwen-faceswap）；2511 + v5 无量化。多人镜只有一个人不对：SAM3 把他涂成 `#FF00FF`，用 `bfs_body_swap_selective_magenta_v1.0_qwen_2.1` 只换这一个人（BFS 工作流；Qwen 2.1，非商用）。
5. **身份门禁**（分轨，阈值见本节「门禁分轨与阈值」）：**真人轨默认** YuNet 检测置信 0.6 + SFace 余弦（OpenCV Zoo，Apache-2.0，真人轨里唯一许可干净的一套），对比 bust（这一轨对应 SKILL.md 脚本表里的 `scripts/identity_gate.py`，基准取 episode JSON 的 `reference_images` 或 `--ref`）：≥ 0.363 = 同人（SFace 官方阈值），交付 keep ≥ 0.55、严格 0.65；只信 ≥ 40 px 正脸、逐张独立比（Zowwan `facematch.py`；fuzzballb 实测本人 0.35–0.59、旁人 −0.01–0.13）。**漫剧 / 手绘 / 兽设走动漫轨**：`scripts/identity_gate_anime.py`（CCIP，整张图比对，已实现；只判单角色画面，多人画面仍用 `assets/judge-take-prompt.md` 的 VLM 评审 + 人审；头部检测 + DINOv2 的逐人轨仍在规划中）；3D 国漫先试 SFace，检不出脸再切动漫轨。多人镜做匈牙利匹配查串脸。分数是警告不是门禁，与真实感冲突时真实感优先（Zowwan）。
6. **人审联络表**（每格 ≥ 720 px）：脸、服装、手指数、背景有没有字、窗户 / 光向对不对；背对镜头查左右手（mathruffian review-checklist / checklists）。审过才写 `frames_ok`、才进 H3（mathruffian docs/02）。

**冻结与过期记录 `bible/assets.json`**（shuohao character-refs、wind-comic 的做法；布局是本 skill 的约定，**现有脚本都不读写它**，先手工或自写脚本维护；`scripts/identity_gate.py` 读取它属于 `docs/14-ai-video-workflows/05` §7 规格里的规划中部分）：

```json
{"style_line": "<画风句>", "characters": {"lin_lan": {"look": "<LOOK 全文>"}}, "files": {
  "bible/chars/lin_lan_bust.png": {"sha256": "…", "derived_from": [], "model": "z_image_turbo_int8_convrot", "params": {"seed": 41, "steps": 8, "cfg": 1}, "frozen": true, "stale": false},
  "bible/chars/lin_lan_full.png": {"sha256": "…", "derived_from": ["bible/chars/lin_lan_bust.png"], "model": "qwen_image_edit_2511_fp8mixed", "params": {"seed": 7, "steps": 20, "cfg": 4}, "frozen": true, "stale": false},
  "first/s03.png": {"sha256": "…", "derived_from": ["bible/chars/lin_lan_face.png", "bible/scenes/corridor_s03_crop.png"], "model": "qwen_image_edit_2511_fp8mixed", "params": {"seed": 12, "steps": 20, "cfg": 4}, "frozen": false, "stale": false}}}
```

- 每个文件一条：`sha256`、`derived_from`（直接上游）、`model` 与 `params`（模型文件名、seed、步数、CFG、提示词；云端出的图记模型名、日期、提示词）、`frozen`、`stale`。只冻结三样：锚点文件（bust、正面全身）的 sha256、外观文字（LOOK）、画风句（shuohao）。
- 锚点文件、LOOK 或画风句任何一样变了 → 沿 `derived_from` 把所有下游标 `stale: true`，**只标不删**、旧版本不覆盖；非锚点的图重出后（如 face.png），从它出的首帧同样标过期。门禁把 `stale` 当不通过（shuohao 的门禁含「是否过期」一项）。

**门禁分轨与阈值**（SKILL.md 脚本表里的 `scripts/identity_gate.py` 目前只覆盖第一行的真人默认轨：输出每张脸的指派角色、分数与 pass / warn / fail，默认只警告、`--strict` 才拦截。最后一行的 CCIP 动漫轨由 `scripts/identity_gate_anime.py` 实现（整图比对、只判单角色画面）；中间两行（AdaFace、头部检测 + DINOv2）、每角色围栏、`auto` 选轨与读取 `bible/assets.json` 是 `docs/14-ai-video-workflows/05` §7 的规格，**规划中、尚未实现**；规格的输入是 `bible/assets.json`，或按约定找 `bible/chars/<id>_bust.png`、`_face.png`、`_full.png` 与人工认可的额外参考，每角色 3–5 张基准。绝对阈值都是小样本标定，只作起点）：

| 轨 | 检测 | 嵌入 | match | borderline | floor | 出处与限制 |
|----|------|------|-------|-----------|-------|-----------|
| 真人（默认） | YuNet，置信 ≥ 0.6 | SFace 余弦 | 0.55（严格 0.65） | 0.363 | 0.363 | OpenCV Zoo（Apache-2.0）官方阈值；Zowwan |
| 真人（可选） | 同上 | AdaFace ViT-Base（`minchul/cvlface_adaface_vit_base_webface4m`） | 0.42 | 0.36 | 0.30 | Fizgig 2026-11-12 标定（6 人数据集，在 InsightFace 五点对齐上标的）；权重训练集 WebFace4M 的商用条款自查 |
| 动漫 / 手绘 / 兽设 | deepghs anime head YOLO（MIT），置信 ≥ 0.35 | DINOv2-base（头部裁剪；Apache-2.0） | 0.62 | 0.48 | 0.40 | Fizgig 小样本标定（暂定值）：同角色中位 0.69–0.75、异角色 p95 0.57–0.60 |
| 动漫（**已实现**：`identity_gate_anime.py`） | 不检测，整张图 | CCIP 差异值（越小越像） | ≤ 0.178 | ≤ 0.30（暂定） | > 0.30 不通过 | deepghs `ccip-caformer-24-randaug-pruned`，默认阈值 F1 0.917；脚本复现了官方示例数值（误差 < 0.001）；仅限单角色画面；OpenRAIL |

- **围栏优先于绝对阈值**（围栏属规划中部分）：每个角色的基准图两两互比，取「中位数 − 1.5 × IQR」且不低于 floor 作该角色的下限（Fizgig Look Filter）；判定 pass ≥ match、warn 在 borderline 与 match 之间、fail < borderline 或 < 围栏。基准里同人最低分 ≤ 异人最高分 = 撞脸（`bible_ambiguous`），回去改角色设计，不要调阈值。
- **多人镜与选轨**：多人镜把「检到的脸 × 期望角色」相似度矩阵做匈牙利匹配，报多出来的人、缺席的角色、串脸（A 位置的脸更像 B 且反之）。真人检测器在动漫 / 手绘图上基本检不出脸（InsightFace 在 Fizgig 测试集 0 / 19；YuNet 未测）→ 漫剧直接走动漫轨；规划中的 `auto` 选轨 = 抽 ≤ 24 张，≥ 50% 检到真人脸且纯动漫脸 < 25% 走真人轨，否则动漫轨（Fizgig 的判定规则）。一次运行只用一种嵌入，分数只在同一嵌入内可比；deepghs 检测模型的具体文件名未核实。

**什么时候花钱用云端出关键帧**（满足任一条；价格取 ComfyUI v0.46.2 partner 节点价签，含 Comfy 加价）：① 一帧 ≥ 3 个具名角色 + 指定场景（2511 只有 3 槽、10 图的 Qwen 2.1 非商用）→ Nano Banana 2.1（14 张参考，2K $0.072）或 Seedream 5.5（10 张，$0.029–0.050 + $0.011 × 参考数）；② 画面里有必须读得清的多行文字 / 界面且本地两次不过 → GPT Image 2.6（2048×1152 medium $0.052）或 Nano Banana Pro（$0.161）；③ 同一镜本地 2 个 seed + 1 次换头仍不过门禁。不值得：场景、道具、草稿、九宫格，以及要反复迭代同一张图的环节（云端每次整图重画、不可锁 seed 复现）；一集全走云端 2K 也只有 $1–3，本地优先是为了可复现、可批量、许可与隐私。云端出的图照样过门禁并记进 `bible/assets.json`。

## 5. 接进 episode JSON 与 H3 模式

```json
"characters": [{"id": "lin_lan", "reference_images": ["bible/chars/lin_lan_face.png", "bible/chars/lin_lan_full.png"], …}],
"scenes":     [{"id": "corridor", "reference_images": ["bible/scenes/corridor_master.png", "bible/scenes/corridor_grid9.png"], …}],
"props":      [{"id": "prop_folder", "reference_images": ["bible/props/prop_folder.png"], …}],
"segments":   [{"id": "s03", "mode": "i2va", "first_frame": "first/s03.png", "first_frame_prompt": "<§3 首帧模板填好的全文>", …}]
```

- 角色图顺序有语义：`build_prompts.py` 把第 1 张写成「脸、发型、体型、服装来源」、第 2 张写成「只控服装与轮廓」（`h3lib/prompt_builder.py`）→ **face.png 放第一、正面全身 `_full.png` 放第二**，两张都是单人单视图；拼出来的角色板只给人审，不进 `reference_images`（shuohao 的 H3 实测：只挂正面全身，服装和背影都对但脸会走样，加一张大头照脸最接近；本 skill 待 A/B）。口型近景用半身裁图而非全身三视图（ancient-rap-battle，05 survey #27）。
- 场景只接 `reference_images[0]`（同上源码）；要九宫格就把它排第一，母版 / 九宫格二选一占槽。场景参考会让运镜减半，但去掉就丢地点一致性（egguy886 h3-drama-kit 175 段实测，11 survey）。
- 道具：剧情里出现即必须有图（本 skill 铁律 6）。
- **段内每镜一张关键帧（规划中的可选字段，待 A/B）**：`"keyframes": [{"t": 0.0, "image": "first/s04_k1.png"}, {"t": 3.0, "image": "first/s04_k2.png"}]`——每个子镜头一张关键帧，主帧钉在 0.00 s、子帧钉在各自切点（`t` 取该镜的 `shots[].start`），用 `MiniMaxH3AddGuide.frame_idx` 钉帧（shuohao novel-storyboard）。**脚本尚未支持，需手工在 ComfyUI 里用 MiniMaxH3AddGuide 接线**：`episode.schema.json` 没有这个字段，`load_episode()` 读入时会静默丢掉它，`validate_episode.py` / `build_prompts.py` 既不校验也不出对齐句（`Picture k … aligns with the X.XX-second mark of the target video` 要手写；`t` 到 `frame_idx` 的换算与吸附以节点 tooltip 为准）。开放权重 FL2VA 官方只支持 ≤ 2 张图，≥ 3 张为实验性（musubi 单帧文档）→ 先限制在 ≤ 2 张并做样片。

| 模式 | 首帧怎么用 | 用在 |
|------|-----------|------|
| `ref2va` + `first_frame` | 首帧成为 `<Picture 1>` 开场锚，`fully_preserved`，后接角色 / 场景 / 道具参考（`prompt_builder.py`） | 需要身份参考又要钉开场构图；上一段末帧续接 |
| `i2va` | 首帧钉在第 0 帧（FL2VA 权重 `MiniMaxH3ImageToVideo.first_frame`），三段式提示词，不挂身份参考 | **真人对白段**、关键脸部 / 道具交接镜（本 skill §5）；**多人镜只给首帧**，再加身份参考会多出一个人（mathruffian docs/03） |
| `fl2va` | 首尾帧都要；两张同构图、**不同姿势**；同一张图当首尾帧整镜 100% 静止（mathruffian 三次实测） | 必须演到某个结果的动作 / 特效 |
| `ref2va` 无首帧 | — | 漫剧可直出（本 skill 铁律 17） |

**真人对白段先出首帧**：盲评直出 0:4 输、垫首帧 4:0 赢（本 skill 铁律 17）；首帧的光线、肤质、背景会保留到整支片，只在视频提示词加手持 / 眨眼描述看不出差别（mathruffian，Image 2.5 首帧 3 场景实测）。

## 6. 生图阶段禁忌

1. 给编辑模型的身份参考用多格板 → 被照抄成拼贴图；只给单格半身照 / face.png（mathruffian docs/03）。
2. 把定妆照接在 Qwen-Image 2.1 的 `image_1` 上出首帧 → 姿势锁死正面（mathruffian；原因与三条待 A/B 的解法见 §1）。
3. 附整张场景母版当首帧参考 → 出成大全景；先裁到景别（mathruffian）。
4. 附别的成片画面当「风格参考」→ 里面的人和物被画进来（mathruffian docs/07 §4）。
5. 首帧用拼贴 / 带标签的设定板，或带 UI 文字的图当 I2VA 首帧（05 survey #30）。
6. 首帧尺寸 ≠ H3 画布、或宽高不是 32 倍数（Fizgig；本 skill 分辨率格点）；首帧底部用边缘复制补画面 → H3 长出黑条（mathruffian docs/03 #24）。
7. 首帧是动作最高点 → H3 只剩维持（mathruffian）。
8. 首尾帧用同一张图却要人动 → 整镜冻结（mathruffian）。
9. 外观文字每镜重写或漏写下装 → 掉眼镜、换发型、随机裙裤（mathruffian）。
10. 立绘手持道具、摆 pose → 道具与动作被焊进身份（manju-laoli）；道具单独出白底图。
11. 只写身份词不写骨相 / 族裔 / 身高体型 / 标志物 → 撞脸、人人中等身材、职业被画成别的行当（TapCanvas；okaypic；manju-laoli「外卖员被画成协警」）。
12. 在 CFG 1 模型的正向里写「no text / no people」→ 名词被召唤（okaypic）；排除词只进 Edit 2511 的负向框。
13. 油亮高光的参考脸 → H3 片中脸油（animede）；用哑光均匀光。
14. Turbo / Lightning 草稿直接当定妆照或成片首帧（Qwen 2.1 Turbo：皮肤光滑、表情漂、暗部压死，mathruffian）。
15. Contact Sheet 五视图 LoRA 留在视频图里（T8；07 survey）；P-H3-Image / MiniMax-H3-Image 在 0.37.2 上找不到节点就把 ComfyUI 升到 ≥ 0.44 / ≥ 0.45（不必上 master），别装来路不明的替代包（ComfyUI 逐 tag 源码核对）。
16. 九宫格少写「恰好 9 格」或写「主图 + 多视角」→ 出 5 格 / 10 格（manju-laoli）。
17. 商用项目用 Qwen-Image 2.1（qwen-research 非商用）出定妆照（HF 模型卡；mathruffian）。
18. 用 MiniMax-H3-Image 出带身份的编辑首帧 → 脸不像参考人、两人合成有一张脸变样（HF 讨论区 4 条独立反馈，2026-11-10/11）；它只出场景 / 九宫格 / 道具 / 海报，人物首帧仍用 Edit 2511。
19. 给 Edit 2511 接第 4 张参考 → 节点只有 `image1`–`image3`（v0.46.2 源码）；超槽就报错停下，不静默丢图（AIMovieStudiov2）。
20. 在平涂 / 像素画风或多人图上用 AnyPose → 失效（AnyPose 模型卡，作者自述）；漫剧的姿势用假人 / 深度参考。
21. 要改姿势时挂 Consistency 类 LoRA → 它会压制动作变化（`ausboss/Qwen-Image-2.1-Consistency-LoRA` 作者 2026-09-28 更新）；这类 LoRA 只用于「不许动构图」的编辑。
22. 商用项目用 InsightFace `buffalo_l` / `antelopev2` 权重做门禁或数据清洗 → 权重仅限非商用研究（InsightFace README）；真人轨用 YuNet + SFace。
23. 用 CLIP 相似度判断动漫角色是否同一人 → 异角色常 > 0.8（Fizgig 测后弃用）；用 DINOv2 头部裁剪或 CCIP。
24. 把成组生成或拼出来的设定板当身份参考（编辑模型与 H3 都一样）→ 人被画小（shuohao character-refs）；板只给人审，参考一律单人单视图。
