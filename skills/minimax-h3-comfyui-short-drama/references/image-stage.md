# 生图阶段：定妆照 / 角色板 / 场景母版 + 九宫格 / 道具 / 逐镜首帧 → H3

> 依据：`docs/13-github-survey/05、06、07、09、10、11、12` + 源码精读（mathruffian-dot/shanshiba-workflow-colab `docs/07`、`docs/03`、`tools/gen_image.py`、`make_film.py`；SwotAtmk/infinite-creation `lib/core/prompts.js` 与 `comfyui_original_workflows/NVIDIA/*.json`；wbliang168/manju-studio `gen_zimage_keys.py`；okaypic `gen_sheets.py`、`cast-format.md`；anymouschina/TapCanvas `face-design.md`；manju-laoli `scene-grid-template.md`；chiphoton Codex-Drama `visual-development.md`；Fizgig-H3-Still README）+ HF 文件列表（2026-11-08 抓取）+ ComfyUI `v0.37.2` 与 master 源码对比。
> 前提：RTX 4090 24 GB、Windows、ComfyUI 0.37.2、系统内存 ≥ 32 GB（推荐 64 GB）、只从 HuggingFace / GitHub 下载。「单机实测」= 只有一台机器的数据，口径照抄原作者。

## 0. 流程总览

```
外观文字（六格 + 族裔 + 身高体型 + 标志物）
  → ① 单张半身定妆照（身份唯一来源，选定后冻结）
  → ② 16:9 角色板（从 ① 派生）→ 裁出 face.png（左 1/3）
  → ③ 场景：无人母版（2K）→ 九宫格 → 按镜裁切
  → ④ 道具：1:1 白底单品
  → ⑤ 逐镜首帧：编辑模型 + ①/face.png + ③ 裁切 → 1344×768 字面首帧
  → ⑥ 身份门禁（SFace）+ 联络表人审 → 写进 episode JSON → H3
```

## 1. 选模型（24 GB、0.37.2、HF 文件名）

ComfyUI 0.37.2 已内置 Qwen-Image 2.1（`TextEncodeQwenImage21`、`QwenImage21Cache`）、Qwen-Image-Edit Plus（`TextEncodeQwenImageEditPlus`）、Krea2、Z-Image 的模型定义（v0.37.2 `comfy_extras/nodes_qwen.py`、`comfy/supported_models.py`）；**`PH3ImageConditioning` 不在 0.37.2，只在 master**（`nodes_minimax_h3.py` v0.37.2 544 行无此类，master 646 行有）。

| 用途 | 首选模型 | HF 仓库 / 文件（放入 `models/<子目录>`） | 文件大小 | 采样 |
|------|---------|----------------------|---------|------|
| 定妆照、角色板、场景母版、九宫格、道具（文生图） | **Qwen-Image 2.1** | `Comfy-Org/Qwen-Image-2.1`：`diffusion_models/qwen_image_2.1_int8_convrot.safetensors` + `text_encoders/qwen3vl_8b_int8_convrot.safetensors`（CLIPLoader type `qwen_image`）+ `vae/qwen_image_2.1_vae_bf16.safetensors` | 7.26 + 9.35 + 0.68 GB（HF） | 成品 euler / simple **50 步** CFG 1、原生 2K（mathruffian `gen_image.py`，A/B 2026-09-28）；官方模板起步 25 步，官方管线 40–50 步（Comfy 模板注释） |
| 同上·草稿抽构图 | Qwen-Image 2.1 Turbo | 同仓库 `diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors` | 7.26 GB | 固定 8 步 euler + ManualSigmas `1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0`、CFG 1；2K 一张 ~12 s vs 50 步 ~63 s（单机实测 RTX 5090，mathruffian）；皮肤偏光滑、表情漂向微笑、暗部压死 → 只作草稿 |
| 要商用的文生图替代 | Z-Image-Turbo（Apache-2.0） | `Comfy-Org/Z-Image-Turbo`：`split_files/diffusion_models/z_image_turbo_int8_convrot.safetensors` + `split_files/text_encoders/qwen_3_4b_fp8_mixed.safetensors` + `split_files/vae/ae.safetensors` | 6.20 GB DiT（HF） | 8 步 CFG 1 euler / simple（manju-studio）；img2img 锁脸 denoise 0.45–0.55 保五官构图、0.60–0.70 换景别仍同脸、> 0.8 洗掉（manju-studio，作者经验值） |
| 写实超真人角色板 / 漫剧风格 LoRA | Krea 2 Turbo | `Comfy-Org/Krea-2`：`diffusion_models/krea2_turbo_fp8_scaled.safetensors` + `text_encoders/qwen3vl_4b_fp8_scaled.safetensors`（type `krea2`）+ `vae/qwen_image_vae.safetensors`；风格 LoRA 同仓库 `loras/krea2_retroanime.safetensors` 等（触发词见模型卡） | 13.14 GB DiT | 8 步 CFG 1 euler / simple（mathruffian；infinite-creation 三视图工作流） |
| **逐镜首帧、换装、改已有帧（编辑）** | **Qwen-Image-Edit-2511**（Apache-2.0） | `Comfy-Org/Qwen-Image-Edit`：`split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors`（或同目录 `_int8_convrot`）+ `Comfy-Org/Qwen-Image`：`split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`、`split_files/vae/qwen_image_vae.safetensors` | 20.53 + 9.38 + 0.25 GB（HF） | `ModelSamplingAuraFlow 3.1` → `CFGNorm 1.0` → euler / simple **20 步 CFG 4**（mathruffian；Comfy 模板表「Comfy 20 / Qwen 40 步，CFG 4」）；1 张参考 ~47 s、2 张 ~85 s（单机实测 RTX 5090），16 GB + 32 GB 内存模拟 50–55 s（mathruffian） |
| 编辑·草稿 | 同上 + Lightning LoRA | `lightx2v/Qwen-Image-Edit-2511-Lightning`：`Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`（另有 8steps） | 0.85 GB | 4 步 CFG 1（infinite-creation 2511 工作流的 4 步开关）；对身份保持的影响未测 |

- 显存：表中都是 HF 文件大小，**4090 峰值显存无人实测**；Edit 2511 的 DiT 20.5 GB + 编码器 9.4 GB 靠 ComfyUI 自动卸载，mathruffian 在「16 GB 显存 + 32 GB 内存」模拟下跑通 → 24 GB + 32 GB 内存足够，int8_convrot 版在 4090 上未验证。
- 许可：**Qwen-Image 2.1 是 qwen-research（非商用）**（HF 模型卡；mathruffian `THIRD_PARTY_NOTICES`）；Edit 2511、Z-Image-Turbo、Lightning 为 Apache-2.0；Krea 2 为 krea-2-community（商用条款自查）。要营利：定妆照 / 母版改 Z-Image-Turbo 或 Edit 2511 文生图，首帧仍用 Edit 2511（mathruffian「首幀不用換」）。
- 不用：chiphoton Codex-Drama 的 `Qwen-Rapid-AIO-NSFW-v19`（28.4 GB 第三方 AIO 合并包）；它配的一致性 LoRA `lrzjason/Consistance_Edit_Lora` 有 2511 版 `qe2511_consis_alpha_patched.safetensors`，chiphoton 用 v2 版 0.8 强度，在 2511 官方权重上的效果未验证。
- **不要用 Qwen-Image 2.1 附参考图出首帧**：长相像，但每张都锁成参考图的正面居中姿势，「侧脸看窗外」也照样正面（mathruffian docs/07 实测）。它的编辑模式（最多 10 图 `<image1>`，Comfy 模板）只适合换装这类不改姿势的编辑。

### 什么时候用 H3 自己出静帧

| 方案 | 配方 | 用在 |
|------|------|------|
| Fizgig H3 Still（custom node，≥ 0.37 可用） | fl2va pruned int8 + `larryvrh/MiniMax-H3-Turbo-Lora` 的 `minimax_h3_turbo_v4_step600_ema.safetensors` **0.38** + er_sde / simple **20 步**，≥ 3 MP（如 2304×1296）；8 MP 无 Turbo 50 步；编辑走 `MiniMaxH3ReferenceToVideo` `<Picture 1>` 在 2.5 MP（Fizgig README） | 不想再下 30 GB 图像模型时出剧照、海报、关键帧；小于 3 MP 明显变弱 |
| Contact Sheet 五视图（MAINodes） | `matlod/minimax-h3-turnaround`：`minimax_h3_five_view_512_s1500.safetensors` 1.0（转角好）或 `_1024cont_s600` 0.75，res_multistep / simple 28 步 denoise 1.0，一张 `<Picture 1>`；消费卡靠内存卸载，需 ~50 GB 内存镜像（07 survey）；**用完立刻卸 LoRA**（T8：留着会毁运动） | 已有一张定妆照，要同一次生成里出 5 个角度（借时间一致性保身份） |
| OrbitSheets | 硬切 6 视图、每视图 0.75 s、124 帧，`[Shot N] At 00:MM.mmm, the shot cuts to … locked-off static camera`（lumosai8） | 要带表情 + 顺带一段音色样本的角色页 |
| P-H3-Image（`PH3ImageConditioning`） | `PrunaAI/P-H3-Image-Comfy`：在 fl2va 上挂 `loras/p-h3-image_lora_bf16.safetensors`（2 GB，Load LoRA Bypass 1.0）+ `ModelSamplingMiniMaxH3` 1.0 / 1.0，8 步 ManualSigmas euler 无 CFG；文生图 8 MP（16:9 = 3872×2176），编辑 4 MP（2720×1536），最多 8 张图；最小整套峰值 21 GB @ 8 MP（模型卡） | **需把 ComfyUI 升到 master**（0.37.2 无此节点）；MiniMax H3 社区许可排除欧盟 / 英国 / 韩国 / 美国（澳洲不在排除列表） |

## 2. 版式与分辨率

- **全部宽高为 32 的倍数**（Qwen 2.1 模板「Prefer multiples of 32」、Fizgig、`PH3ImageConditioning` 的 `CANVAS_MULTIPLE`）。1080 不是 32 倍数：infinite-creation 的 Krea2 工作流写 1920×1080，改 1920×1088。
- **脸部光**：哑光、均匀主光。H3 片中脸部油光取决于参考图的肤质而不是量化（animede，09 survey）；电影质感首帧写「单一真实光源 + 一致的阴影方向」（mathruffian docs/07 §3b，仅在云端 Image 2.5 上 A/B 过）。

| 资产 | 画布 | 版式规则 |
|------|------|---------|
| ① 定妆照 | 1024×1024 | 单人、一格、正面半身、浅灰无缝背景、柔和均匀光（mathruffian）；外观写到下装与鞋，否则全身镜随机配裙或长裤（mathruffian）；多 seed 挑一张后**冻结** |
| ② 角色板 | 2688×1536（Qwen 2.1 2K 默认，mathruffian；7:4）或 2560×1440（真 16:9，按 32 格点推算） | 左 1/3 头肩特写（全图唯一清晰脸），右 2/3 正 / 纯 90° 侧 / 背全身同比例、头顶到鞋底留白边，双臂自然下垂、手里空、中性表情闭嘴、纯白无缝背景、无文字（infinite-creation `CHARACTER_T2I_LAYOUT_CONSTRAINT`；okaypic；manju-laoli「立绘纯净：不手持道具」）；写头身比（manju-laoli） |
| face.png | 从 ② 裁左 1/3，短边缩到 1024 | 给编辑模型当参考、也作 H3 `reference_images[0]`；参考图短边 1024 比 2048 快约 15%、同 seed 画质相当（animede，单机） |
| ③ 场景母版 | 2688×1536（mathruffian） | 无人；人眼高主机位轴；门窗家具主道具位置写清；写一个主光源和方向；默认晴朗白昼（manju-laoli）；背景一句话带过、写 uncluttered，逐项列物件会杂乱（mathruffian） |
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

模板（`{}` 为占位；电影质感 = A，漫剧 = B）：

```text
[定妆照 A] Studio character reference photo, a single person in one image, medium close-up bust portrait facing the camera at eye level, plain light grey seamless background, soft even studio light with a matte skin finish, sharp focus, realistic photograph. {ETHNICITY} {GENDER} of {AGE}, {3-5 BONE TRAITS}, {HAIR}, {SKIN}, wearing {TOP}, {BOTTOM}, {SHOES}, {SIGNATURE ITEM}. {APPEAL LINE (leads only)} Gentle natural expression, lips closed. Clean frame containing only the depicted subject.
[定妆照 B] Anime character bust portrait, a single character in one image, facing the viewer at eye level, plain white background, even flat lighting, {STYLE LOCK: clean dark line art, flat cel shading with two-tone shadows, warm pastel palette}. {ETHNICITY} {GENDER} of {AGE}, {3-5 BONE TRAITS}, {HAIR}, {EYE COLOR}, wearing {TOP}, {BOTTOM}, {SIGNATURE ITEM}. Calm expression, mouth closed. Clean frame containing only the depicted subject.
[角色板 A] A character reference sheet, 16:9 landscape, seamless pure white background, soft even studio lighting with a matte skin finish. Left third: one front-facing head-and-shoulders close-up at eye level, calm neutral expression, lips closed, looking into the camera. Right two thirds: three full-body views standing side by side, front, strict 90-degree side and back, each from the top of the head to the soles of the shoes with a little white margin above and below, all at the same scale, same height, same camera distance and same light, arms relaxed at the sides, hands empty. The person: {LOOK as in 定妆照}. About {HEIGHT_CM} cm tall with a {BUILD} build, true body proportions of {7} heads tall, scaled uniformly in every view. Identical outfit, hairstyle, accessories and marks in every view; one single person shown from several angles, the only subject in the image. Live-action photograph, 85mm lens look, natural skin texture, true-to-life colors. Clean frame containing only the depicted subject.
[角色板 B] An anime character model sheet, 16:9 landscape, seamless pure white background, even flat lighting. Left third: one front-facing head-and-shoulders close-up, calm expression, mouth closed. Right two thirds: front, strict 90-degree side and back full-body views side by side at the same scale and the same ground line, arms relaxed, hands empty, head to shoes fully inside each panel. The character: {LOOK}. About {HEIGHT_CM} cm tall with a {BUILD} build, consistent proportions of {6} heads tall. {STYLE LOCK}. Identical line weight, colors, outfit and hairstyle in every view; one single character, the only subject in the image. Clean frame containing only the depicted subject.
[场景母版 A] A cinematic film still of an empty {PLACE}, wide establishing view at eye level from {CAMERA SPOT} looking {DIRECTION} along the main axis, 16:9. {LAYOUT: the door on the left wall, a tall window on the right wall, a desk at the centre}. {TIME OF DAY}: one key light, {SOURCE} from {DIRECTION}, shadows falling toward {DIRECTION} with soft falloff and detail kept in the shadows. Shot on a 35mm lens at f/4, deep focus, true-to-life colors, uncluttered. The space holds only its architecture and furniture, deserted and still.
[场景母版 B] An anime background painting of an empty {PLACE}, wide establishing view at eye level from {CAMERA SPOT}, 16:9, painted style matching the character sheets, {STYLE LOCK}. {LAYOUT}. {TIME OF DAY} light from {DIRECTION} in flat cel-shaded blocks. The space holds only its architecture and furniture, deserted and still.
[九宫格 A/B] One 16:9 location board divided into exactly nine equal panels in a 3x3 grid with thin white gutters. All nine panels show the same empty {PLACE} with identical architecture, furniture positions, materials, colors, time of day and light direction; only the camera position changes. 1 view from the doorway into the room; 2 wide view of the main activity area; 3 the window side with the light falling in; 4 reverse view from inside toward the door; 5 high overhead view of the floor layout; 6 long-lens diagonal view from one corner to the opposite corner; 7 close view of {SIGNATURE FURNITURE}; 8 close view of {WALL DETAIL}; 9 the view out of the window. A small numeral 1-9 in each panel's top-left corner. Uniform 50mm lens, bright even exposure, one white balance. The place: {SCENE DESCRIPTION, verbatim from the bible}. {STYLE LINE of A or B}. Every panel is a deserted space.
[道具 A] Product reference photo of {ITEM}, one object centered on a seamless pure white background, 1:1, three-quarter front view at eye level, soft even studio light with a soft contact shadow beneath it, {MATERIAL}, {COLOR}, {WEAR MARKS}, {REAL TEXT: the label reads "{TEXT}" in {COLOR} block letters at the upper left}, about {SIZE} cm long. Sharp focus across the whole object, true-to-life colors. The frame contains only this one object.
[道具 B] Anime prop illustration of {ITEM}, one object centered on a pure white background, 1:1, three-quarter front view, {STYLE LOCK}, {MATERIAL AND COLOR}, {REAL TEXT}, about {SIZE} cm long. The frame contains only this one object.
[首帧·Edit 2511 A] Keep exactly the same person as <image1>: same face, hairstyle and clothes ({LOOK, verbatim}). {Keep exactly the same person as <image2>: … ({LOOK})}. The room is the one in <image{N}>: same walls, furniture and light direction. New photo: A cinematic film still from a {GENRE} drama, shot on Kodak Vision3 500T film with an anamorphic 50mm lens at f/2. {FRAMING}, {WHO stands WHERE doing WHAT at the first instant, EXPRESSION}. Exactly {N} people in the frame. {ONE LIGHT SOURCE, direction, color}.
[首帧·Edit 2511 B] Keep exactly the same character as <image1>: same face, hairstyle, outfit, line weight and colors ({LOOK}). The place is the one in <image{N}>. New frame: a frame from a 2D anime episode, {STYLE LOCK}. {FRAMING}, {WHO WHERE DOING WHAT, EXPRESSION}. Exactly {N} characters in the frame.
[换装子资产·Edit 2511] Keep exactly the same person as <image1>: same face, skin, hairstyle, body proportions and height. Change only the clothing to {NEW OUTFIT}. Same sheet layout, same pure white background, same lighting.
[Edit 2511 负向框，仅 CFG 4 时] text, watermark, caption, collage, split panels, extra person, extra fingers, waxy skin
```

## 4. 一致性工作流

1. **定妆照**（Qwen 2.1 50 步，或 Z-Image-Turbo）：同一外观文字跑 4–8 个 seed，人挑一张，存 `bible/chars/<id>_bust.png`，之后不再换（mathruffian）。外观文字（LOOK）存进系列圣经，**每一镜首帧原样照抄**，少写一次就掉眼镜换发型（mathruffian `frames()`）。
2. **角色板**：Edit 2511 以 bust 为 `<image1>` 套【角色板】模板（编辑模型保脸，mathruffian「長相像」），或 Contact Sheet 从 bust 出五视图再人工排版。infinite-creation 的做法是把一张现成三视图板当 `<image1>` 让 2511 照「排版格式」出新人物（它的 2511 工作流示例提示）；这条路把版式当参考，身份另靠文字，只作备选。
3. **派生图**：从板裁 face.png；换装 / 年龄变体用【换装子资产】从板编辑，优先级 `costume > age > 原图`（本 skill §3 资产表）。
4. **逐镜首帧**：Edit 2511，参考顺序 = 每个入画角色的 bust / face.png（≤ 3 张，2 人实测可行）→ 最后一张场景裁切（mathruffian）；同一场的不同机位从**同一张底图**编辑，首尾帧也从同一张图改（mathruffian docs/03：换机位背景会跑）。1344×768 直接出。每镜最多 2 个 seed，仍不对就改提示词或换参考裁切（本 skill 铁律 10 的同一逻辑）。
5. **身份门禁**：YuNet 检测置信 0.6 + SFace 余弦，对比 bust：≥ 0.363 = 同人（SFace 官方阈值），交付 keep ≥ 0.55、严格 0.65；只信 ≥ 40 px 正脸、逐张独立比（Zowwan `facematch.py`；fuzzballb 实测本人 0.35–0.59、旁人 −0.01–0.13）。分数是警告不是门禁，与真实感冲突时真实感优先（Zowwan）。
6. **人审联络表**（每格 ≥ 720 px）：脸、服装、手指数、背景有没有字、窗户 / 光向对不对；背对镜头查左右手（mathruffian review-checklist / checklists）。审过才写 `frames_ok`、才进 H3（mathruffian docs/02）。

## 5. 接进 episode JSON 与 H3 模式

```json
"characters": [{"id": "lin_lan", "reference_images": ["bible/chars/lin_lan_face.png", "bible/chars/lin_lan_sheet.png"], …}],
"scenes":     [{"id": "corridor", "reference_images": ["bible/scenes/corridor_master.png", "bible/scenes/corridor_grid9.png"], …}],
"props":      [{"id": "prop_folder", "reference_images": ["bible/props/prop_folder.png"], …}],
"segments":   [{"id": "s03", "mode": "i2va", "first_frame": "first/s03.png", "first_frame_prompt": "<§3 首帧模板填好的全文>", …}]
```

- 角色图顺序有语义：`build_prompts.py` 把第 1 张写成「脸、发型、体型、服装来源」、第 2 张写成「只控服装与轮廓」（`h3lib/prompt_builder.py`）→ **face.png 放第一、整板放第二**。口型近景用半身裁图而非全身三视图（ancient-rap-battle，05 survey #27）。
- 场景只接 `reference_images[0]`（同上源码）；要九宫格就把它排第一，母版 / 九宫格二选一占槽。场景参考会让运镜减半，但去掉就丢地点一致性（egguy886 h3-drama-kit 175 段实测，11 survey）。
- 道具：剧情里出现即必须有图（本 skill 铁律 6）。

| 模式 | 首帧怎么用 | 用在 |
|------|-----------|------|
| `ref2va` + `first_frame` | 首帧成为 `<Picture 1>` 开场锚，`fully_preserved`，后接角色 / 场景 / 道具参考（`prompt_builder.py`） | 需要身份参考又要钉开场构图；上一段末帧续接 |
| `i2va` | 首帧钉在第 0 帧（FL2VA 权重 `MiniMaxH3ImageToVideo.first_frame`），三段式提示词，不挂身份参考 | **真人对白段**、关键脸部 / 道具交接镜（本 skill §5）；**多人镜只给首帧**，再加身份参考会多出一个人（mathruffian docs/03） |
| `fl2va` | 首尾帧都要；两张同构图、**不同姿势**；同一张图当首尾帧整镜 100% 静止（mathruffian 三次实测） | 必须演到某个结果的动作 / 特效 |
| `ref2va` 无首帧 | — | 漫剧可直出（本 skill 铁律 17） |

**真人对白段先出首帧**：盲评直出 0:4 输、垫首帧 4:0 赢（本 skill 铁律 17）；首帧的光线、肤质、背景会保留到整支片，只在视频提示词加手持 / 眨眼描述看不出差别（mathruffian，Image 2.5 首帧 3 场景实测）。

## 6. 生图阶段禁忌

1. 给编辑模型的身份参考用多格板 → 被照抄成拼贴图；只给单格半身照 / face.png（mathruffian docs/03）。
2. Qwen-Image 2.1 附参考图出首帧 → 姿势锁死正面（mathruffian）。
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
15. Contact Sheet 五视图 LoRA 留在视频图里（T8；07 survey）；P-H3-Image 在 0.37.2 上找不到节点就去升 ComfyUI，别装来路不明的替代包（ComfyUI 源码对比）。
16. 九宫格少写「恰好 9 格」或写「主图 + 多视角」→ 出 5 格 / 10 格（manju-laoli）。
17. 商用项目用 Qwen-Image 2.1（qwen-research 非商用）出定妆照（HF 模型卡；mathruffian）。
