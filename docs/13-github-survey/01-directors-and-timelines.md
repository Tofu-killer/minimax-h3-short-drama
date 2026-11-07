# 01 · 导演台 / 时间线 / 分镜编排类节点精读

调研日期 2026‑11‑07。方法：浅克隆 23 个仓库，逐个打开节点 Python 源码（INPUT_TYPES、常量、patch 方式）、示例工作流（`analyze.py`）与作者文档；AIMixer 导演台与 WhaleTrans 已在 `docs/12-public-workflows.md` 写过，这里只补新信息。用户环境：Win11 + RTX 4090 24GB + ComfyUI 0.37.2 + int8_convrot FL2VA/Ref2VA + nvfp4 CLIP + lightx2v Turbo LoRA + SageAttention。

## 本簇结论（10 行）

1. **立即采用 seesee75-commits/ComfyUI-MiniMaxH3-Director（GPL‑3.0）**：唯一一个把「任意时长 = 约 10 s 的 render part 串联」做成原生 Loop、不 patch ComfyUI 核心、要求恰好 ComfyUI ≥ 0.37.0、在 16 GB 卡上实测跑通 1280×704 的导演台；它的 `docs/paper` 给出了一整套**有测量数据的分段规则**（22 帧画面钉 + 24 帧音频钉、接缝后 2.4 s 内别换动作、part 末 2 s 内别切镜、>4 个接缝声音发闷要锁音轨、单段 ≤30 s 且帧数×面积 ≤ 360×1280×704），这些规则比任何节点都值钱，可直接写进 skill。
2. **立即采用 nkxx188/ComfyUI-MiniMaxH3-Easy（MIT）作为「单节点抽卡 + Context Segments 长视频」的日常工具**：官方索引把它列为 24 GB 首跑推荐；`@Image1 / @Video1 / @Audio1` 引用 + `#` 对白块 + `---` 分段，四种衔接模式（Motion Context / RGB Guide / Soft AV / Hard AV），全部走核心 `minimax_keyframes`，不打猴补丁。
3. **提示词规则采用 Songssx TimelineDirector 的《循环分段提示词 Agent 规范》**（即使不用它的节点）：`--- SEGMENT ---` 分段、六字段固定顺序、第二段起 `[Shot 1] During 00:00.000‑00:00.917` 逐项复现上一段末尾 Guide、人物「首次建立、后续继承」、重叠帧向下对齐到 17k+5 网格（48→39、24→22）。
4. **采用 imbutus/ComfyUI-MiniMaxDirector（MIT）的 linter 规则**（描述 350–500 词、参考 ≤9 图/3 视频/3 音频/总 12 文件/视频音频各 2–15 s 且总 ≤15 s、图片 256–5760 px、宽高比 0.4–2.5、参考视频会压倒人物参考、相邻两镜只换景别不该切）——节点本身是单段 ≤15 s 的编译器，适合单镜头抽卡。
5. **观望**：AIMixer 导演台 v1.0 新增的「段间引导」要 patch `PackedLayout.__init__`、与 Motion‑Context 互斥；KadoBOT Continuity Studio（MIT，依赖核心 Context Windows 节点、需 LLM 端点）值得抄它的「长链烧焦」测量表；chanon obvpm‑timeline（延长/前插/桥接做得最细，但要装 7 个节点包、作者推 Patreon）；Goldlionren JR（38 节点、Hard AV Prefix 分块采样器，重）；LeonQ8 ALLinONE（锁定 ComfyUI 0.39.2 + 10 个外部包）。
6. **跳过**：huangserva（AIMixer 工作流镜像，"4090 48GB" 为魔改卡）、j955229 Motion Director（AIMixer 血统的 GPL 分支，8 月后停更）、karuvanan Director Cut Studio（PySide6 外部程序，runtime 走 Google Drive，TTS/歌声克隆全家桶）、rookiestar28 Studio（67 万行、媒体功能仅 Windows、长视频只支持 T2V、测试基线 0.42）、TianyiDataScience OneClick（面向 8 GB 新手，锁 ComfyUI 0.34 portable）。
7. **4090 24 GB 上最实用的导演台**：seesee75 Director（30–60 s 对白短剧，References 模式 + 角色卡 + 声音卡 + 锁歌）> nkxx188 Easy Context Segments（快速抽卡、按段 refine）> Songssx 有限分段采样（想一次跑完 60 s、接受 GPL 与 10 节点的简洁图）。AIMixer 二采配置（`h3_latent` 放大 → beta 3 步 denoise 0.2）仍然是最省时的精修，可搭配任何一家。
8. **时间码写法全簇一致**：`[Shot 1]` 不带时间，`[Shot N] At MM:SS.mmm,`（两位分、两位秒、三位毫秒），段内局部时间；对白 `<d>[Chinese] 原文</d>`、说话人 `(S1)` 放在 `<d>` 外、只能出现在 `detailed_description`/`integrated_multimodal_description` 里，最后一个字段永远是 `non_diegetic_music`。
9. **参考编号规则**：图/视频/音频各自独立从 1 连续编号，按接线顺序；上一段传入的 latent guide 不占号；视频自带音轨先占 `<Audio N>`，独立音频随后（r34vtraining/goohai）；RefMod 参考包在普通素材之前编号（FeiHou）。
10. **当前 ComfyUI 核心已原生支持内部帧关键帧**（`minimax_keyframes` 的 `resolved_frame_index` 可取 0..T 任意合法偏移）：seesee75、Easy、KadoBOT、chanon 都直接用核心接口；凡是仍替换 `PackedLayout.__init__` / `MiniMaxH3.extra_conds` 的包（AIMixer 段间引导、kat3ri Extend、LeonQ8 兜底 wrapper）都会与别的包互斥，装了一个就别装第二个。

---

### AIMixer/ComfyUI_MiniMaxH3_Director（★2722，Apache‑2.0，最后推送 2026‑10‑13）

**只补 docs/12 未写的部分。** pyproject 版本 1.0.0，源码 29k 行（`director/` 下 executor_core 1949 行、segment_continuity 1798、segment_cache 1837）。

- **段间引导（默认关）**：`director/h3_motion_context.py` 把上一段末尾 N 帧 latent 作为 never‑denoised keyframe 钉进下一段再裁掉，`CONTEXT_FRAME_CHOICES = (5, 22, 39, 56)`、默认 22，`DEFAULT_AUDIO_CONTEXT_FRAMES = 24`（抄 NikoDemon80 的实测值）；pipeline id `minimax_h3_motion_context_v9`。实现方式是 `director/h3_context_patches.py` **替换 `comfy.ldm.minimax.model.PackedLayout.__init__` 与 `MiniMaxH3.extra_conds`**，启动自检；检测到 ComfyUI‑H3‑Motion‑Context 或其它包已 patch 时直接 `RuntimeError` 拒跑（「both packs cannot own PackedLayout.__init__」），只与 SolAttn 的 layout observer 共存。→ 与 Motion‑Context / Extender 类包互斥。
- **公共提示词拼接**：`plan.concat_common_segment_prompt()` = 公共提示词 + 空行 + 本组提示词；`reinforce_r2v_prompt()` 在提示词里没写 `<Picture`/`<Video`/`<Audio` 时自动在开头补 `<Picture 1> <Picture 2> … ` 标签。
- **语义桥 Semantic Bridge**（外接节点，`models/semantic_bridge/`）：student MLP 改写 cond token（RMS‑norm → 残差混合），原版偏构图/空间/计数，BUNNY 偏多人动作归属；蒸馏自 FL2VA，r2v 系「强制兼容」。属实验性。
- **SelfLift 渐进一采**：`split_mode=highres_steps`，8 步默认「低清 6 + 高清 2」，建议高清约占 25%。**Face Refine**：ultralytics `face_yolov8m.pt`、confidence 0.35、crop_factor 2.5、裁剪画布 768×768 用 H3 重生成后回贴。
- **提示词增强模板**：`lib/official_pe_templates.py` 注释写明是「Verbatim Bernini official templates（bytedance/Bernini）」——即**借用字节 Bernini 的电影美学扩写模板，不是 H3 官方 skill**；LLM 支持 Ollama（默认 `qwen3.5`）/ OpenAI 兼容 / 智谱。
- **外部多组**：`Director Group (Image to Video)` / `(Reference to Video)` + `Groups Combine` 喂 `i2v_groups`/`r2v_groups`，便于程序化；但 i2v/r2v 两口不能同时接。
- 坑：单节点 UI 极重；缓存目录 `output/minimax_seg_cache/<cache_name>_<node_id>/`；fl2v 默认跳过二采（`skip_fl2v`）。
- **评级：试用**（二采/外部组/导演包继续用；段间引导与 Motion‑Context 二选一，SelfLift/语义桥观望）。

### huangserva/ComfyUI_MiniMaxH3_Director（★1429，Apache‑2.0，最后推送 2026‑08‑04）

- 仅 5 个 JSON + README，自述「工作流来自 AIMixer」，无任何 Python；官方索引误把它列为「五个模板的提供者」。
- 自称验证环境「RTX 4090 48GB、ComfyUI 0.30.0、PyTorch 2.11 + CUDA 12.8、仅 Ref2VA int8」，即改装 48G 显存卡，对 24 GB 无参考意义。
- 有用的一句经验：RV2V 换人「先生成 5 秒检查脸/服装/动作/镜头边界再延长」；「段间引导不能替代人物一致性检查」。
- **评级：跳过**（直接用 AIMixer 原仓库 `example_workflows/`）。

### Songssx/ComfyUI-MiniMaxH3-TimelineDirector（★753，GPL‑3.0，最后推送 2026‑10‑21）

- 定位：WhaleTrans 的上游。0.8.0 起**不再依赖 Loop PR #15923**，用 `MiniMaxH3FiniteSegmentSampler` 一节点在普通无环图里展开 N 段；也提供原生 `Start Loop / End Loop` 节点组与「低内存版」（每段解码后立即写临时 MP4、编码层合并，不保留整条 RGB）。
- 续接机制（源码）：`experimental_latent_guide._valid_guide_frames()` 把重叠帧向下对齐到 `n % 17 == 5`（<5 → 1）；上一段 sampled AV latent 尾部直接放到下一段开头（不经 RGB 往返）；`drift_control_av.py` 用 `DRIFT_CONTROL_VIDEO_STEPS=12 / MATCHED=8 / TAPER=4` 的动态前缀噪声掩码匹配外部 sigma（支持 4/8/20 步）；音频重叠前部全保护、**最后 8 个音频 latent tick 半余弦 Soft AV 释放**，合并时用后一段的 Soft AV 重叠音频替换前一段末尾。全段同一 seed。
- `_inject_continuity_instruction()`：第二段起在 `detailed_description:`/`integrated_multimodal_description:` 的 `[Shot 1]` 后自动插入「The opening 00:00.000‑00:00.917 is a carried latent continuation …」（docs/12 已引用原文）。分段提示词用 `--- SEGMENT ---` 独占行或 JSON 数组。
- SelfLift 二采内置（不再需要 comfyui‑SelfLift）：勾「开启二采」+ 选 `models/latent_upscale_models/` 的 H3 Latent Upscaler + 高清步数≈总步 25%（8 步 → 2）。作者实测 **1536×832 / 29 s 约 10 分钟直出**（未写显卡）。
- 示例工作流只有 10 节点：`MiniMaxH3TimelinePlanner`(960×544, 7.3 s/段) → `FiniteSegmentSampler`(seed 42 fixed) ；采样 Euler + simple 8 步，UNET 是作者自融合的 `minimax_h3_fused_refdelta_r1024_turbo8_mystic07_int8_convrot`（非官方权重，需自行换成 ref2va int8 + Turbo LoRA）。CLIP 路径带 `minimax_h3\` 子目录。
- 文档：`docs/MiniMax_H3_循环分段提示词_Agent规范.md`（553 行）是全簇最完整的分段提示词写法；`docs/MEDIA_CHECKLIST.md`、`AGENT_LONG_VIDEO_GUIDE_CN.md`。
- 坑：GPL‑3.0；视频用途三选一（固定 Guide / 可编辑参考 / 仅固定边界）容易选错；不声明 pip 依赖，低清代理要 `imageio-ffmpeg`。
- **评级：试用**（节点）/ **采用**（Agent 规范）。

### seesee75-commits/ComfyUI-MiniMaxH3-Director（★343，GPL‑3.0，最后推送 2026‑11‑03）

- 定位：v1.0.1（2026‑11‑03）。「任意时长」导演台：planner 把视频切成约 10 s 的 render part，在 ComfyUI **原生 Loop** 里逐段采样（`H3 Render Sequence` 展开为 `StartLoop → cond → pin → SamplerCustomAdvanced → EndLoop`），latent 空间拼接后分窗解码。**要求 ComfyUI ≥ 0.37.0**（测试到 0.42），唯一依赖 OpenCV；SKILL.md 明言「Never patch ComfyUI itself」，`ng/adapters/conditioning.py` 只往 `minimax_keyframes` 追加 `{resolved_frame_index, latent}` / `{resolved_frame_index, audio_latent}`。
- `ng/core/limits.py` 常量：`GRID 17k+5`、`SAMPLED 96–360`、`PIN_VIDEO_WINDOWS (5,22,39,56)` 默认 22、`PIN_AUDIO_DEFAULT 24`（=40 音频 tick）、`CONTINUE_VIDEO_FRAMES 39`、`LATE_CHANGE_FRAMES 60`、`AUDIO_DULLING_JOINS 4`、`DEFAULT_CHUNK_SECONDS 10`、`FRAME_BUDGET = 360×1280×704`、`LONG_PART_FRAMES 719`（29.96 s）。
- 实测（技术报告 §8，RTX 5060 Ti 16 GB）：只钉画面 → 音频相关 0.18；钉画面+声音 → 0.92；头窗 5/22/39 帧相关 0.88/0.92/0.94；48 帧音频窗比 24 无提升；六段链接缝相关不衰减但 >4 kHz 能量降到 1/11（声音发闷）；接缝后新动作延迟 **2.4 s**；part 末 2 s 内切镜会被切两次；640×352 单段 30 s 不漂移、45–60 s 开始重复台词。速度：Turbo 8 步 vs 20 步 5 s 1280×704 = 285 s vs 526 s；15 s 1280×704 Turbo 约 15–20 分钟（16 GB）。
- `turbo_profiles.json`（实测）：`ref2v_turbo_4step_v0.1` → **6 步**（4 步有白雾，黑电平 0.024）；`fl2v_turbo_8step_v1.0` → 8 步（4 步出笔触且第二段静音 −97 dB）；`fl2v_turbo_4step_v1.2_768p` → 4 步；`turbo_4step_ckpt500` → 8 步 euler+beta（4 步绿脸）；均 res_multistep+simple。
- 编译器规则（`part_prompt.py` / 论文 §7）：镜头切换 `[Shot N] At MM:SS.mmm,`、首镜 `[Shot 1]` 无时间；跨 part 的长镜头按 `0–5s:` 节拍分配；**镜头运动句只写在镜头开始的 part，续接 part 改写成 "The camera holds a static shot, keeping the framing of the preceding video"**；台词归属镜头开始的 part，除非开始于末 2 s；首尾帧模式续接 part 把开场图当 reference 以防换衣；禁写 flawless/glowing/shimmering/wet 皮肤词。
- 其他：角色卡（Belongs to 合并多视图为一个 Subject）、声音卡（Lock 锁歌/对白 → `noise_mask=0`）、Storyboard、ControlNet 车道、Ollama/LM Studio 写词（qwen3.5:9b 测试）、`taeh3.safetensors` 实时预览、断点续跑 `output/h3-director-resume`、BT.709 标签。OOM 对策：Render part 5 s / int8 video VAE / Resolution Fast(480)。
- 坑：GPL；UI 卡片在 Vue 新前端曾错位（1.0.1 修）；大部分实测单 seed；无法精确控制切点（±0.5 s）。
- **评级：采用**。

### imbutus/ComfyUI-MiniMaxDirector（★73，MIT，最后推送 2026‑09‑16）

- 定位：「编译器而非 latent 引导」——时间轴上的 Shot/运镜/音频 cue 编译成**一条**官方结构提示词，调核心 `MiniMaxH3ImageToVideo`/`ReferenceToVideo`（introspection 解析签名），无外部依赖，纯 Python 核心 0.2 s。单段 ≤ 15 s。要求 ComfyUI ≥ 0.31（Turbo 开关需 `ModelSamplingAV`）。
- 编译输出：Ref2VA 六字段、FL2VA 三字段（`integrated_multimodal_description / overall_soundscape / non_diegetic_music`，无则 `N/A`）；`<Picture 1> (from [Shot 1]) is fully referenced.` / `aligns with the N‑second mark`；运镜写成「motion type × amplitude × speed」；对白跨切 `carries over`、被剪断 `<cutoff>`、听不清 `[unclear]`；画面文字逐字引用。WHO & WHAT 卡片 → `<Subject n>`，可绑脸/声/保留度/换脸目标。
- `lint.py` 规则（可直接抄）：描述 350–500 词；相邻两镜内容相同只换景别 → 建议并为一镜加运镜；音轨空 → `overall_soundscape: N/A` 等于告诉模型全片静音；声音参考 keep 必须 `reference`（不是 copy）；**参考视频里的人脸 8 次测试全部压倒人物卡**，要换人就把视频撤掉；参考视频自带音轨压倒声音参考；视频 2–15 s；图 ≤9、视频 ≤3、音频 ≤3、总 ≤12；参考视频总 ≤15 s；图片 256–5760 px、宽高比 0.4–2.5；台词说话人与所在镜头主体不符会误导。
- 示例工作流：ref2va int8 + `ref2v_turbo_4step_v0.1`、res_multistep/simple 20 步（Turbo 时 euler 8 步）、可选 `MinimaxH3LatentUpscaler3D` 二采（8 步 simple）。
- **评级：采用（规则）/ 试用（节点，单镜抽卡）**。

### j955229/ComfyUI-MiniMax-H3-Motion-Director（★141，GPL‑3.0，最后推送 2026‑08‑20）

- 定位：自称 "Independent"，但文件结构（`web/js/minimax_prompt_mentions.js`、`lib/prompt_enhancer.py`、`director/external_groups.py`）与 AIMixer 同源，README 致谢 AIMixer；v1.2.0 后两个半月无提交。
- 机制：`motion_context.py` `VIDEO_CONTEXT_GRID = (39, 22, 5, 1)`，pipeline `pin_renorm_selected_context_v2`，带 **Color Re‑anchor**（像素域回拉颜色）和 Latent Scale Lock；注释写「guarded layout patch」→ 同样 patch 核心。Mixed Mode 每段自选 T2V/I2V/FL2V/R2V/Source Video，边界按钮逐个开关画面/音频连续性；Segment Result 把前段某帧当后段 I2V/FL2V 输入。
- 推荐流程原文：低分辨率一遍 → 检查 → 重抽失败段 → 固定 → Global Refine/Upscale → Face Refine。
- 坑：GPL；停更；与 AIMixer 节点同名 JS 可能冲突。
- **评级：跳过**（功能已被 AIMixer v1.0 覆盖）。

### KadoBOT/ComfyUI-H3-Continuity-Studio（★153，MIT，最后推送 2026‑11‑07）

- 定位：Timeline + Story（LLM 写分镜/Story bible）+ Continuity check（Vision 模型 + CIELAB 漂移/纹理「烧焦」测量）。依赖 `jsonschema`；**>362 帧要用核心 `MiniMaxH3ContextWindowsNode`**（`comfy_extras/nodes_context_windows`，需较新 ComfyUI）；官方 prompt guide `base-en.txt/ref-en.txt` 不随包分发。
- 常量（`timeline.py`/`timing.py`）：`MAX_FRAMES 362`、`LONG_MAX_FRAMES 991`、`MIN_FRESH 22`、`MIN_CONTINUING 17`、`CONTEXT_OPTIONS ("22","39","90","141")`、`BRIDGE_FRAMES (12, 29, 46)`（桥 = 17j−5，使两端 17k+5 保持网格）；`@image1/@audio1/@video1/@video_audio1` 引用；视觉记忆模式 `off/scene/selected/cast`（把早先镜头的帧作为 keyframe 带入后续镜头，换机位也能保人/景）。
- 续接：Continue = 上一段最后 `context_frames` 帧（+音频）冻结为 native context，并把上一段末帧图作为首个新帧的 guide；Cut/New scene 不带帧；Bridge 在两段已渲染片之间插 12/29/46 新帧（39 帧 context 时整段 90/107/124 帧），**桥不带任何图/参考**。
- `guide/continuity/long-chains.md` 实测（FastH3 omniref 8 步 int8，960×544，6 段）：默认纹理烧焦到 2.04×；`context_noise` → 1.75；加 H3 Sigmas Tail 3 步 0.5 → 1.67；**REF2VA int8 本身只 1.19**（模型比任何设置更重要）；FastH3 v2 第 2 段必跳近景。
- 坑：Story/Check 需 OpenAI 兼容端点；文档极厚（guide/ + docs/ 20 篇）；示例工作流录的是作者本机模型名。
- **评级：观望**（抄测量结论；节点等 ComfyUI 核心 Context Windows 稳定后再试）。

### chanon/comfyui-obvpm-timeline（★266，GPL‑3.0，最后推送 2026‑10‑23）

- 定位：「迷你剪辑器」时间轴 + **Extend / Prepend / Bridge / Loop** + 整段联合 latent 放大。每个生成片旁存 `.mctx.safetensors` sidecar（latent + header），延长从原 latent 而非重编码像素出发；pin 窗口 5/22/39/56（22 日常），latent 切点必须落 17 帧组网格；钉入帧是「脚手架」，交付时裁掉。
- 依赖重：ComfyUI ≥ 0.35（核心 `Model Sparse Attention`）、comfyui‑obvpm ≥ 0.2.16、KJNodes、LBH‑123‑AI latent upscaler（**不能装 xmarre 的 Plus 分支**，同名节点少两个 widget 会错位且没有 temporal chunking）、Larryvrh Turbo、xmarre Spectrum、rgthree。示例工作流 140 节点：ref2va int8、`er_sde` + simple 4 步、`fl2v_turbo_4step_v1.0_768p` 强度 0.7 + `turbo_v4_step600_ema` 叠加、SigmaShift 12/3、`MiniMaxH3MemoryEfficientSageAttentionPatch`、`BlockSparseAttention`、`H3ContextWindows`。
- 独有发现：**kat3ri/ComfyUI-MiniMax-H3-Extend（Backported）在 import 时替换 `extra_conds` 与 `PackedLayout.__init__`，会让全会话所有 H3 采样的接缝偏色**；pmhaidn Extender 是 wrap 不是替换，但会 patch Turbo loader。`H3 VRAM Headroom` 节点：核心动态加载只留 256 MB，Windows 开浏览器/录屏时会把 VRAM 页到 PCIe 卡在 "Model Initializing"，建议预留 1 GB（裸机）/3 GB（开浏览器）/5–6 GB（录屏）。新 take 在接缝前 1 个 latent step（4 帧）接管，接缝细节变化降约 1/3。H3 每片多出约 8 ms 音频，trim 节点截到 `frames/fps`。
- **评级：观望**（想做「拍完再补一段/补中间」时最强，但包链太长、GPL）。

### karuvanan/MiniMax-H3-Director-Cut-Studio（★153，MIT，最后推送 2026‑10‑19）

- 定位：**ComfyUI 之外**的 PySide6 桌面程序（`director_cut_studio.py` 3.5 万行），Premiere 式多轨时间轴，把 Shot/Dialogue/Marker 编译成 Ref2VA 提示词后 POST 给 ComfyUI；捆绑 Z‑Image 概念图、BLIP/Whisper、LM Studio、ACE‑Step 音乐、SoulX 歌声克隆、Qwen3‑TTS、VoxCPM2、Character‑Swap LoRA + SAM3.1 换人合成。完整 Windows runtime 走 Google Drive。
- Smart Long Render：>15 s 自动按 Shot 边界切成 3–6 s Render Unit（无 Shot 结构时 `0–15 / 14–29 / 28–43…`），**非首段把上一段最后 24 帧（1 s）抽成无音频的隐藏 `<Video N>` 参考**（占一个视频槽），提示词明令禁止重播上一段动作，FFmpeg 裁重叠拼 master；段内时间换算为 `0–15s` 局部时间。
- 对白行格式：`[Track Layer 1.000-3.500s] (role; S1; Chinese; voice_gender=female; delivery; overlap=policy) <d>[Chinese] 台词</d>` + "VOICE GENDER LOCK" 句；齐声用 "SYNCHRONIZED UNISON LOCK"。
- 坑：依赖清单 170 行、多机主从部署（ACE‑Step 默认连 `192.168.0.185:8001`）、仅 Windows；与本仓库「ComfyUI 内完成」目标不符。
- **评级：跳过**（可借鉴「上一段末 24 帧当 Video 参考」这一不依赖 patch 的衔接法与 `skill special/short-drama-h3-director`）。

### rookiestar28/MiniMaxH3-Studio（★158，Apache‑2.0，最后推送 2026‑10‑27）

- 定位：ComfyUI 侧边栏 Studio（28 个 canvas 节点、`comfyui_h3_context` 包 67 万行含 governance 合约）；五种任务模式、App Mode 把官方 `video_minimax_h3_*` 模板写进当前 tab、Production 工作台、内置 8 轨剪辑器。
- 长视频：4–60 s，storyboard 脚本 `[Shot 2] At 00:08.000, …` 自动切 4–15 s 段（示例 60 s → 8/12/13/14/13 s 五段），**当前只接受 T2V 计划**，段间无 latent 衔接，拼接后只标 smooth/visible change。
- 对白走 `H3 Hard Constraint Producer` 节点（`dialogue / visible_text / required_content / forbidden_content`，`dialogue_delivery on_screen|voiceover`）；「Guide readiness」按官方 prompt guide 检查完整性；辅助写词支持 Ollama/Gemini/OpenAI/Anthropic。
- 坑：媒体功能（剪辑器、拼接）**仅 Windows x64**；测试组合 ComfyUI 0.42 + 前端 1.55/1.57，0.37.2 未验证；不生成 Ref2VA 长视频。
- **评级：跳过**（对短剧流水线无增量）。

### nkxx188/ComfyUI-MiniMaxH3-Easy（★889，MIT，最后推送 2026‑10‑26）

- 定位：官方索引「24 GB 首跑」推荐。`nodes.py` 7846 行单文件；`MiniMaxH3Easy` 主节点一个 `Media` 口收图/视频/音频，模式 `I2V or First/Last Frame`（0 图=T2V、1 图=I2V、2 图=FL2V，居中裁剪不拉伸）/ `Reference-to-video` / `Digital Human`（单条音频锁为驱动音轨）。采样、LoRA、解码留在节点外。示例 1：fl2va int8 + `fl2v_turbo_8step_v1.0` + euler/simple 8 步 + `ModelAttentionBackend` + RAMCleanup。
- 提示词：`@` 弹菜单选 `@Image1/@Video1/@Audio1`（运行时转 `<Picture N>` 等并重编号）；`#` 建对白块 → `<d>…</d>`；`~` 插 `---` 分段；可切「raw 视图」或外接 STRING。
- **Context Segments**：`Segment seconds` 如 `5,5,5`；**每段只使用其提示词里 `@` 到的素材**（不继承）；共享库上限 27 图/9 视频/9 音频，单段仍 9/3/3。衔接模式与网格（源码常量）：`Motion Context` / `RGB Guide` 用 `(5,22,39,56,73)`，`Soft AV` / `Hard AV` 用 `(39,90,141)`；默认 context 5 帧（`SEGMENT_DEFAULT_CONTEXT_FRAMES = 5`，建议改 22）；实现全部写 `minimax_keyframes`（`resolved_frame_index` 按 `(1,4,4,4,4)` 累加），**无核心 patch**。`Segment Refine` 逐段放大重采并把精修结果传给下一段（Pixel Resize / Latent Upscale / Low VRAM Tile），`Segment Decode` 逐段写临时 MP4。工作流 5 用 `Segment Step` 链实现按段换 seed/重跑。
- 提示词优化：OpenAI 兼容 / Responses / Gemini / Ollama，按 `Segment seconds` 一次生成 N 段独立提示词（Whole sequence / Per segment），刻意避免 "Segment 2 / continue from previous" 这类规划语；API key 明文存 `prompt_optimizer.json`。
- 坑：Segment Sample/Refine 每次 Queue 都重跑（无缓存）；Segment Decode 需 ffmpeg；参考视频缓存吃系统内存。
- **评级：采用**。

### FX-FeiHou/ComfyUI-FeiHou-Easy-H3（★78，GPL‑3.0，最后推送 2026‑11‑06）

- 定位：Easy 的 GPL 分支：9 图九宫格 + 3 视频 + 3 音频**内嵌槽位**（拖放上传、随工作流保存），默认 24 fps / 10 s，参考图短边 480–1088 可选；FeiHou LoRA Stack；多家 LLM/本地 GGUF 扩写；`提示词预览` 节点输出最终扩写词。
- 新增 `refmods` 口接 Luisacaotica/ComfyUI‑MiniMaxH3Mod 的 `Load H3 RefMods`：RefMod 不占 9/3/3 槽位但增加 token/显存；**编号 RefMod 在前、普通素材在后**（8 个 image RefMod → `<Picture 1–8>`，普通图从 `<Picture 9>` 起）。
- 「完整低显存分块（实验）」来自 matlowai MAINodes 的 `H3 Streamed Blocks`（QKV/attention/MLP/输出头全分块），**开启后不能再串 `ModelAttentionBackend / comfy kitchen attention`**，与用户的 SageAttention 路线冲突。
- 坑：GPL；与上游 Easy 同名节点不能并装；1.1 万行以上改动难跟上游。
- **评级：观望**（只有要用 RefMod 参考包时才换它）。

### LeonQ8/ComfyUI-ALLinONE-MinimaxH3（★366，GPL‑3.0，最后推送 2026‑10‑22）

- 定位：单节点 11 种模式（Image/T2V/I2V/R2V/Character Sheet/Audio Drive/Keyframes/Extend/Chain/Mask/Upscale）+ Compare & Stitch 对比。`nodes.py` 3078 行。
- 机制：Chain/Keyframes/Extend 接线抄 seitanism/ComfyUI‑H3‑Motion‑Context‑MultiRef，`nodes.py:29` 为 ComfyUI 0.32/0.33 的「keyframes + refs 同时存在崩溃」bug 内置 `MiniMaxH3.extra_conds` 替换兜底（优先加载 MultiRef 的 `patch_payload.py`）。Keyframes 写 `{"resolved_frame_index": idx, "latent": z}`。
- COMPATIBILITY.md 锁死栈：**ComfyUI 0.39.2**、PyTorch 2.9.1+cu130、MultiRef Update 9、vrgamedevgirl 9.2.0（Audio Drive）、VHS、SeedVR2、RTX VSR、Larryvrh Turbo、KJNodes、thaakeno Studio、PlagueKind（SLA Draft：er_sde+beta 6 步 + 8 步 Turbo）。
- 坑：GPL；0.37.2 不在测试栈；extra_conds 兜底与其它 patch 包互斥。
- **评级：观望**。

### yusu-02/ComfyUI-Yusu-MiniMaxH3-Unified（★100，无 license，最后推送 2026‑10‑09）

- 定位：一个节点三模式（`text_to_video / first_last_frame / omni_reference`），节点内上传/粘贴/裁剪媒体，只封装官方两个 conditioning 节点，**不改推理核心**；9 图/3 视频/3 视频配对音频/3 独立音频；`duration` 秒数自动对齐网格；可按参考音频自动算时长；单段参考音频 ≥2 s，上限已取消。
- B 站 UP「在下鱼酥」配套，工作流 `H3全能工作流.json` 同时发 RunningHub。源码 530 行，有前后端测试。
- 坑：**无 LICENSE 文件**；与 Easy 功能重叠且少了分段。
- **评级：跳过**。

### yichengup/ComfyUI-YCNodes-MiniMax-H3（★265，MIT，最后推送 2026‑09‑15）

- 定位：6 个底层节点，无依赖。与「分镜编排」直接相关的是 **`H3 Prompt Relay`**：H3 是 text+cond+audio+video 打包自注意力、无 cross‑attention，该节点对 video query → text key 施加时间惩罚 mask，让不同时间段只看对应提示词；`local_prompts` 用 `|` 分段、`global_prompt` 全程可见；默认惩罚 0.001、强度 1.0。只支持 `MiniMaxH3ImageToVideo`（含 MultiParams），不支持 Ref2VA。
- 其它：`Image to Video (Tail)` 接受一采 latent 透传做二采并按帧数重算关键帧锚点（默认 1344×768/124 帧，`apply_keyframes` 可关）；`Distance Attention Patcher` 时空高斯感受野（默认 864×480、17 帧）；`Dynamic CFG`（CFG=1 时无意义）；`Sigma Refiner` 低噪区加步；`Tiled Sampler` 改自 10S LTX tiled。
- 坑：Prompt Relay 是 attention patch，与 SageAttention/Sage patch 节点叠加是否生效未验证；2 个月未更新。
- **评级：试用**（Prompt Relay 做「一段 15 s 内多镜头各看各词」的实验）。

### Goldlionren/ComfyUI_JR_MiniMaxH3Node（★64，Apache‑2.0，最后推送 2026‑10‑29）

- 定位：38 个 V1 节点的大套件（0.20.0）。导演相关：`JR_H3_DirectorDesk`（不调 LLM 的时间线编辑器，确定性编译 `director_prompt`，用自定义 `JR_H3_DIRECTOR_PIPE` 总线传给 Prompt Optimizer → Review 人工审核 → Directed Video Conditioning；优先级 `reviewed > optimized > director`）、`Director PIPE Builder/Unpack`。First Frame 固定 0.0 s 单点锚；Driving Audio 不允许重叠；时间线 >150 s 拒绝。
- 长视频：`JR_H3_TemporalChunkSampler` 默认 **Hard AV Latent Prefix**（Chunk 2+ 复制上一块 video T12 + audio T65 尾部、两流 prefix mask=0、采样后逐位校验回写，不调 AddGuide、不 decode/re‑encode）；`Legacy Independent Chunks` 用末帧 `MiniMaxH3AddGuide(frame_idx=0)`。Regenerate（Open‑H3‑Regenerate‑2K）分窗 5s/8s/10s，后续窗锁 39 帧前缀，建议 3 步 / denoise 0.30，**只兼容 BF16 底模**（不支持 pruned int8）。
- Prompt Optimizer：closed‑world 忠实改写；Base 对白只进 `integrated_multimodal_description`、Ref2VA 对白只进 `detailed_description`，不重复到 soundscape；程序逐字保护对白。
- 坑：节点多、文档 626 行；RTX 效果要 `nvidia-vfx`；Unified 加速依赖 KJNodes + SolAttn_triton。
- **评级：观望**（Hard AV Prefix 思路与 Songssx 一致；Director Desk 的「人工审核暂停」节点可借鉴）。

### princepainter/ComfyUI-PainterNodes（★203，MIT，最后推送 2026‑10‑23，只看 MiniMaxRefToVideo2）

- `PainterMiniMaxRefToVideo2.py` 384 行：Ref2VA conditioning 封装，参考图节点内上传，音/视频外接；前端 JS 提供中文速记：`@图片1/@视频1/@音频1` → `<Picture N>/<Video N>/<Audio N>`；`切镜3.5` 芯片 → `[Shot N] At 00:03.50,`（注意只两位小数，`formatShotTimestamp` 用 `toFixed(2)`，与官方三位毫秒略不同）；`【台词】` → `<d>[Chinese] 台词</d>`（已带 `[语言]` 前缀则不重复加）。
- 价值：中文用户最快的「按官方格式填词」输入法；无分段/衔接。
- **评级：跳过**（规则已被吸收；用 Easy 的 `@`/`#` 即可）。

### goohai/Goohai-MiniMax-H3_Integration（★254，GPL‑3.0‑or‑later，最后推送 2026‑09‑09）

- 定位：B 站「孤海FOTO」的一体化 conditioning 节点，**内置 T8mars audio‑T8 的条件构建实现**（因此 GPL）；按素材组合自动判 T2VA/I2VA/L2VA/FL2VA/Ref2VA/Hybrid；配套适配器、双时钟采样、AV 解码、Latent Upscaler、二采分块采样器。面向 RunningHub 在线运行。
- 标签规则（`prompt_tags.py`）：I2VA/L2VA/Hybrid/Ref2VA 用 `<Picture 1>`，**FL2VA 用不带尖括号的 `Picture 1 / Picture 2`**；单击素材插标签、双击视频插其音轨标签；「严格提示词标签」开时引用不存在编号直接报错。高级音频模式 `native / reference_only / lock_source / remix_source`。
- 限制：输出 2–30 s；参考图 ≤4 MP、参考视频 0.3–1.6 MP，只缩不放；条件编码后主动卸载文本编码器释放显存。
- 优化器系统提示（`prompt_optimizer.py` ~L850–1011）值得抄：`<d>` 只能嵌在描述字段的镜头句里、永远不出现在 `subject_definitions/summary/retention_analysis/overall_soundscape/non_diegetic_music`；中文对白必须 `<d>[Chinese]…</d>` 不能只用引号；最后一段必须是 `non_diegetic_music`；不得编造用户没给的台词。
- **评级：跳过**（规则吸收；节点面向 RunningHub）。

### nimblecloud13/ComfyUI-Guides（★68，无 license，最后推送 2026‑10‑24，只看 H3）

- 一份 HTML/PDF 新手讲解（约 2 万字），按 RTX 5060 Ti 16 GB / 32 GB RAM 写。要点：steps 20 为官方默认、12–16 快测、**8 步时人声最弱、12 步起可用**、细节到 ~50 步仍改善；Ref2VA 多参考时官方注记 beta/normal 调度常优于 simple；shift 越高越多步花在早期（构图/运动），越低越偏细节；CFG 1.0 = 关；列出官方模板模型集与 `fl2v_turbo_8step` LoRA。
- **评级：跳过**（无新机制；"8 步人声弱" 与 seesee75 实测一致，可作为规则佐证）。

### pixelaigc/ComfyUI-MiniMax-H3-Workflow（★404，无 license，最后推送 2026‑09‑10）

- 单个子图工作流 `video_minimax_h3_t2v_0909.json`：fl2va int8 + Larryvrh `MiniMaxH3TurboLoRA`（`turbo_4step_ema_ckpt850`）**8 步** res_multistep/simple、0.4 MP 16:9 = 864×480、目标 6 s → 158 帧（6.58 s）；首帧/尾帧接或不接切换 FL2V/I2V/T2V。
- 有用的小公式：帧数 = `max(5, round(a*24)) + (5 - (… % 17)) % 17`，向上对齐 17k+5；16:9 分辨率表 0.2→608×352、0.4→864×480、0.6→1056×608、0.8→1216×672。
- 坑：无许可证、未记录硬件/耗时、依赖 Larryvrh 包；README 自述「编写时未重新执行生成」。
- **评级：跳过**。

### TianyiDataScience/MiniMax-H3-OneClick（★130，MIT，最后推送 2026‑09‑16）

- Windows 一键安装器（PowerShell）：下载 **ComfyUI portable v0.34.0** + 44.4 GB 模型（SHA‑256 校验、断点续传），生成 8 GB 显存首跑工作流（864×480、5 s、Turbo 8 步，Stable 模式预留 1.5 GB 显存）；实测机 RTX 5050 Laptop 8 GB。官方 T2V 工作流分析：fl2va int8 + `fl2v_turbo_8step_v1.0` + res_multistep/simple **4 步**、1344×768、73 帧。
- 提质顺序（原文）：先 480p 5 s 关 Turbo 或加步 → 0.5/0.6 MP → 0.98 MP(1344×768) → 再试 Balanced 启动；一次只改一项。
- **评级：跳过**（锁 0.34，不适合 24 GB 用户；提质顺序可作规则）。

### light-and-ray/Minimalistic-Comfy-Wrapper-WebUI（★145，AGPL‑3.0，最后推送 2026‑10‑25，只看 H3）

- MCWW v2.4 加 H3 支持：用节点标题 `<Picture 1:prompt/Pictures 1-3:11>` 这种约定把 ComfyUI 图暴露成表单 UI；4 个示例（Ref / Ref Image / FL2V / T2V）。Ref 示例 115 节点：ref2va int8 + **`minimax_h3_video_vae_int8_convrot`**（int8 视频 VAE）+ `ref2v_turbo_8step_v1.0_768p`（与 4step_v0.1 二选一）、euler + **beta 6 步**、SigmaShift **6/3**、`ModelAttentionBackend`、`PCLazyLoraLoader`、1344×768×124 帧。作者提示 torch ≥ 2.13+cu130 否则慢一倍。
- 价值：非节点式推理前端；与导演台无关。
- **评级：跳过**（但「768p 8 步 LoRA + euler/beta 6 步 + shift 6/3 + int8 VAE」是一组可对照的 Ref2VA 抽卡参数）。

### r34vtraining/Longshot_Studio（★55，无 license，最后推送 2026‑10‑31）

- 定位：ComfyUI 内置网页 `/longshot`，逐 Shot 做长片；需另装同作者 `H3_Prompt_Compiler` + `H3_Longshot ≥1.7.0`（节点 `MiniMaxH3TimelineShot/Take/LongShot/Clip/UpscaleChunk/FaceRefine…`），ComfyUI ≥ 0.35，可选 Larryvrh Turbo / RTX VSR Pro / RefMods；SageAttention 用 `--use-sage-attention` 启动参数。
- 接缝类型：**Continuous**（续前镜，固定 **22 帧重叠**，`film.py`）/ **Cut** / **Context**（新机位，把上一镜末帧当参考）/ **Bridge**（两端钉死）/ Lead In / Cutaway（B‑roll，不被后镜看到）。角色用 `<hero>` 这类标签，编译时映射 `<Picture N>`；歌曲固定 `<Audio 1>`（视频音轨先占号）；说话人 `(S1)` 要自己写。
- Tips 原文：两端钉死的 Shot 至少 5 s 且要把「到达状态」写进文本；长链漂移对策「先单独渲染奇数 Shot，再 Render all 桥接偶数」；OOM 自动重试；ProRes 422 HQ 母版。
- 坑：三包联动、无 LICENSE、作者机器未写。
- **评级：观望**（接缝六分类与「奇偶渲染」策略可借鉴）。

---

## 可写进 skill 的规则

1. 多段提示词的镜头标记统一写 `[Shot 1]`（无时间）与 `[Shot N] At MM:SS.mmm,`（段内局部时间、两位分两位秒三位毫秒）；不要用 `[0s-1s]` 区间式写法做主格式（seesee75 `part_prompt.py`、Songssx 规范、rookiestar28）。
2. Ref2VA 提示词六字段固定顺序 `subject_definitions → summary → retention_analysis → detailed_description → overall_soundscape → non_diegetic_music`，字段名不译不删不换序；FL2VA/T2VA 用 `integrated_multimodal_description → overall_soundscape → non_diegetic_music`（imbutus compile.py、Songssx 规范）。
3. 对白只写成 `<d>[Chinese] 原文</d>`，说话人 `(S1)` 与动作放在 `<d>` 之外、同一镜头句内；`<d>` 绝不出现在 `subject_definitions/summary/retention_analysis/overall_soundscape/non_diegetic_music`（goohai prompt_optimizer、Goldlionren）。
4. 描述正文控制在 350–500 词；低于则模型自行脑补，高于则细节互相争抢（imbutus lint）。
5. 参考标签按类型各自从 1 连续编号、顺序 = 接线顺序；不得跳号/重复/引用不存在的编号；上一段传入的 latent guide 不占 `<Video/Audio/Picture N>` 编号（Songssx 规范 §4）；视频自带音轨先占 `<Audio N>`，独立音频随后（r34vtraining graph_builder、goohai）。
6. 参考上限：图 ≤9、视频 ≤3、音频 ≤3、总文件 ≤12；每段参考视频/音频 2–15 s 且同类总时长 ≤15 s；参考图 256–5760 px、宽高比 0.4–2.5（imbutus lint、seesee75 minimax_plan）。
7. 要换人/保人物卡时不要同时挂参考视频：参考视频里的人脸和音轨会压倒 `<Picture>`/`<Audio>` 参考（imbutus lint，8 次实测全部如此）。
8. 分段衔接的重叠帧只取 5 / 22 / 39 / 56（n ≡ 5 mod 17），默认 22（0.917 s）；音频钉 24 帧（1 s = 40 tick），48 帧音频窗无增益（seesee75 E4、AIMixer、Songssx `_valid_guide_frames`、chanon）。
9. 用 Soft/Hard AV 前缀同时续音画时取 39 / 90 / 141 帧网格（nkxx188 Easy `SEGMENT_CONTEXT_AV_FRAME_GRID`、KadoBOT `CONTEXT_OPTIONS`）。
10. 第二段起 `[Shot 1]` 必须逐项复现上一段最后 overlap 秒的画面与声音（人物位置、动作相位、镜头、灯光、环境声），重叠结束后不切镜写 `From 00:00.917, without a cut, …`，切镜则从 `[Shot 2] At 00:00.917` 开始；后续段只承接直接上一段（Songssx 规范 §7）。
11. 上一段最后一个 Shot 的起点严格等于 `segment_seconds − overlap_seconds`，内容选中低速、轮廓清晰、少遮挡的可承接状态，不塞新剧情（Songssx 规范 §1.2、§4.3）。
12. 接缝后 2.5 s（60 帧）内不要安排新动作，也不要在 render part 最后 2 s 内切镜；需要时把段边界整 17 帧地挪开（seesee75 `LATE_CHANGE_FRAMES`、E7、M18/M19）。
13. 续接段不要重复运镜句（每段会再推一次），改写为 "The camera holds a static shot, keeping the framing of the preceding video"；运镜必须在本段内起止（seesee75 §7.2、CRAFT）。
14. 台词归属镜头开始所在的段，除非镜头开始于该段最后 2 s（48 帧）——那就放到下一段（seesee75 `SPEAK_MIN_FRAMES`）。
15. 生成音频链超过 4 个接缝会明显发闷（>4 kHz 能量降至 1/11）；60 s 短剧要么锁定外部配音/歌曲（`noise_mask=0`），要么把对白段控制在 ≤5 段（seesee75 E6、`AUDIO_DULLING_JOINS`）。
16. 单段长度上限：帧数 × 宽 × 高 ≤ 360 × 1280 × 704，且 ≤ 719 帧（30 s）；640×352 可一段 30 s 不漂移，45–60 s 会重复台词和动作；1280×704 维持 ≤360 帧（seesee75 §5.3、M13）。
17. 每段只喂该段提示词里 `@` 到的素材，不自动继承上一段素材；同一角色在每段都要重新 `@`（nkxx188 Easy Context Segments）。
18. 人物只在首次出场或造型变化时用 `<Picture N>` 完整定义；后续段写成「`<Subject 1>` is the girl already visible in the opening Latent Guide; `<Picture 1>` calibrates her identity」；音色参考绑定到既有人物即可（Songssx 规范 §4.1）。
19. 用正向构图控制人物数量（左/中/右、景别、遮挡），不要反复写 "Do not create extra characters"（Songssx 规范 §4.2）。
20. 首尾帧模式下续接 part 没有图时，把该镜头的开场图作为 reference（不是 frame）喂进去，否则推近脸后下一段会换衣服（seesee75 §7.4）。
21. 两端钉死（Bridge）的镜头至少给 5 s，并把到达状态写进文本（"…ends with her at the doorway"）（r34vtraining Tips、seesee75 ARRIVAL 规则）。
22. Turbo LoRA 步数按实测表：`ref2v_turbo_4step_v0.1` 用 6 步（4 步白雾）；`fl2v_turbo_8step_v1.0` 用 8 步（4 步笔触且第二段静音）；`fl2v_turbo_4step_v1.2_768p` 4 步即可；`turbo_4step_ckpt500` 要 8 步 euler+beta；全部 CFG 1.0（seesee75 turbo_profiles.json）。
23. 8 步 Turbo 时人声是最弱环节，有对白的段至少 12 步或改 Hard AV/锁音轨（nimblecloud13 guide、seesee75）。
24. 不要在同一 ComfyUI 里同时安装两个会替换 `PackedLayout.__init__`/`MiniMaxH3.extra_conds` 的包（AIMixer 段间引导、ComfyUI‑H3‑Motion‑Context、kat3ri Extend、LeonQ8 兜底）；kat3ri Backported Extend 会让整个会话的接缝偏色（AIMixer h3_context_patches、chanon README）。
25. 安装 LBH‑123‑AI latent upscaler 原版，不装 xmarre `-Plus` 分支（同名节点 widget 错位且无 temporal chunking）；整段联合放大必须开 `enable_temporal_chunking`（chanon README/limits）。
26. Windows 上开着浏览器/录屏跑 H3 时给核心加载器预留 1–3 GB（录屏 5–6 GB）显存，避免 "Model Initializing" 卡死（chanon `H3 VRAM Headroom`）。
27. 长链烧焦（纹理越来越脆）主要取决于模型：ref2va int8 六段仅 1.19×，FastH3 omniref 2.04×；`context_noise` + 3 步 Sigmas Tail 0.5 可降到 1.67×；换模型优于调参（KadoBOT long-chains）。
28. 段间 OOM 对策顺序：render part 5 s → int8 video VAE → 短边 480（Fast）→ 段间清显存；提质顺序：先 480p 5 s 加步/关 Turbo → 0.5–0.6 MP → 0.98 MP，一次只改一项（seesee75 tips、TianyiDataScience）。
29. 分段提示词之间用 `--- SEGMENT ---` 独占行（或 Easy 的 `---`）分隔，块数 = 段数，不输出解释文字（Songssx 规范 §2、nkxx188）。
30. 不依赖 patch 的保守衔接法：把上一段最后 24 帧（1 s）切成无音频视频作为 `<Video N>` 参考，提示词明确「不要重播上一段动作」（karuvanan Smart Long Render）；或官方做法上段尾帧 = 下段 I2V 首帧（docs/12 已写）。

## 未覆盖/未读完

- 全部 23 个仓库均已打开源码或文档；以下只读了 README/常量未逐行读实现：karuvanan `design_engine.py`（9027 行）与 `director_cut_studio.py`（35643 行）、rookiestar28 `comfyui_h3_context/`（67 万行）、Goldlionren 38 节点中的 Regenerate/Sequential Audio 细节、KadoBOT `story_prompts.py`（LLM 提示词模板）与 `cast_memory.py`、chanon `nodes_joint.py`（联合放大 2117 行）。
- 未运行任何工作流做实际显存/耗时验证；所有数字均为作者自述或作者实测。
- r34vtraining 依赖的 `H3_Prompt_Compiler`、`H3_Longshot` 两个仓库未克隆。
