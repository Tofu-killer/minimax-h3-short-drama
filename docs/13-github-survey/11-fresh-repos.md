# 13‑11 · 枚举之后新出现 / 最近一周活跃的 36 个仓库（精读）

> 调研日期 2026‑11‑07。来源清单 `data/new_since_2026-11-01.json`（创建或推送在 2026‑11‑01 之后、星数 0–14）。全部 36 个浅克隆到本地，重点 15 个打开节点源码 / SKILL.md / playbook / 工作流 JSON（`analyze.py`），其余略读 README 归类。判断标准：相对 01–10 与 `skills/minimax-h3-comfyui-short-drama/references/` 已有结论，是否带来**新机制、新参数、新实测数字或矛盾**。所有耗时/显存都注明作者硬件，均为作者自报。

## 本簇结论（10 行）

1. **立刻采用（源码级新机制）**：`fuzzballb/comfyui-h3-long-video`——「39 帧 latent 冻结续接 + 每段存 latent/cond 到磁盘 + 单独一条超分工作流只重采已批准段（σ 0.6316 起、2 步）+ 续接处 78 帧交叉淡化 + SFace 身份匹配的小脸重绘（σ 0.8）」是迄今最完整、最可复制的「一人 24 GB 卡做 1–2 分钟连续剧」方案；三条新实证：`H3MiniMaxCache` 会毁掉续接（接缝帧差 28 vs 9）、SLA 稀疏让背景直线扭曲（同 seed 关掉即稳，代价 2.8×）、Turbo 上叠加 LoRA 总强度 >1.3 会让小物件透明重影。
2. **立刻采用（二采新参数）**：`pongjoo/ComfyUI-PJ-SegmentSampler`——二采**分段精修**在段间留 **5 帧正重叠**（承接已精修前段，单份交付、不加权混合）让接缝 MAE 降 62–72%、亮度跳变降 ~5×；局部回修默认 denoise 0.4、边界锁 2 个视频潜步；一采 22 帧接力「先集中编码全部段条件再连续采样（E/E/E/S/S/S）」省 25–45% 节点耗时（5090D 实测）。
3. **立刻采用（分辨率纠错）**：`dreevelle/ComfyUI-ResolutionTools`——核心 `ResolutionSelector` 的 MP 是 **mebipixel（×1024²）**，官方教程的 0.98 MP 实为 1.03 真 MP；**1344×768 是 7:4 而非 16:9**，H3（对齐 32）真 16:9 格点只有 512n×288n：1024×576 / 1536×864 / 2048×1152；交付 1920×1080 应在格点上生成后 **lanczos 缩放**而不是 1920×1088 裁 8 px。
4. **立刻采用（短剧写法实证）**：`egguy886/h3-drama-kit`——60 集 480 段量产 + 150 次 RunningHub 对照得出的证据表：固定全景开场首秒动作量 2.9 vs 推/跟 19.6；打斗每击单独一镜 0.8–1.4 s；对白段**不能**精简提示词（人声提前 1.5 s）；省略号 "..." 会被塞乱码插词（换逗号）；总述里的台词转述会被念出；氛围句/声线开头会被念出；同场景跨段**硬切换景别**而不是尾帧接力；生成时统一安静底噪、环境声全部后期铺。
5. **试用**：`martinsommer3-oss/Filmworkbench-Starter`（Hybrid b25‑49 INT8 + DMAD rank‑39 LoRA 一采 864×480 8 步 er_sde/beta → LBH 放大 → 二采 2 步 er_sde/**linear_quadratic** denoise 0.4 到 1952×1088，5090 实测 S1 73 s / S2 184 s 做 14.4 s；8 个「场景配方」K1–K9 按 Motion‑Context 续接，用「实际接受的末帧 + 显式状态图」解决离开再返回的道具状态）；`wbliang168/manju-studio`（12 GB 路线 Q4 GGUF + 4B TE + ClipProj；QC 阈值：动作镜帧差 ≥2.5、特写 ≥1.8、任何镜 <1.0 判冻结、亮度 <8 判黑屏；一镜必须 ≥124 帧因为训练分布是 124–362）；`mcoblackmore/digital-human-16gb`（4060Ti 16 GB 实测：草稿 896×512 → 1.8× latent → 2 步 refiner LoRA「8plus2」；**瓦片对 ≤7 s 片是净负收益**；拼接前裁底部 12% 去 H3 幻手、裁每段头 0.1 s 去爆音）。
6. **借规则不装**：`Zowwan/studio-grade-ai-video`（SFace 同人阈值 0.363、商用锁脸 keep 0.55–0.65，「真实感优先于技术分」）；`richiepic/ComfyUI-RICHIEPIC-H3`（RefMod 构建：Full Reference 每图 ≈330 token@512、首图定画布；头替换用 `head_swap_v1.0_r32` 而不是 character swap；一采 8 步 DMD + 二采 `lms_v1.0_r64` 0.7 + `h3_upscaler_lms_v0.1`）；`capruokz/h3-comfy`（**参考 token 竞争实测**：2 张角色图 match 1,550 token vs 124 帧参考视频 14k–27k，重者胜，否定句与「角色扮演句」都压不过；续接链在静态戏要始终引用第 1 段尾帧、运动戏引用上一段，否则色偏累积 L 107→86→74）；`yuyuki`（LM Studio 本地 LLM 把小说章节转六段式 + 每镜 ≥2.5 s 校验器）。
7. **观望**：`Code2Collapse/ComfyUI-MiniMax-H3-Suite`（GPL‑3，411 文件的「几何脊柱 + 采样守卫」大包，`H3 Legal Scheduler` 拒绝 SplitSigmas、`Protected Layer Guard` 拦 FinalLayer/首末 block 补丁、SigmaShift 比值锁 12/3——理念好但工程极重且与 SplitSigmas 二采路线冲突）；`nvmax/VideoBuilderH3`（VRGDG 音乐视频台 Rust 移植，社区许可、自带 MCP）；`Koongrizzly`（独立 PySide6 app，INT4/W4A8，Beta 调度配 EMA 4 步 LoRA）；`shawnie117 / CortexIL / keboqi / jdelahayes / nightclaw555`（云端 A40 / RunPod / Colab 部署壳，与 4090 本地无关）。
8. **别碰**：`gjnave/GGF-Recast`（Viggle Remake 换人，内部预览许可、73 GB 权重、4090 上 6 s 两段 15.5 min）、`jameswright1562/openjutsu`（D3voz 同名 fork，无改动）、`knapcio` / `Yuuki-git` / `drimeF0` / `OwenLittleWhite` / `commitname`（双 DGX Spark、海光 8 卡、TPU、昇腾 NPU、精度对齐——与消费卡无关，仅 knapcio 的数字可作 20 步基线参考）、`cheems12` / `pixelaigc/pixelaigc` / `shihoos` / `MindrLabs`（空壳或个人主页）。
9. **矛盾与裁决**：① fuzzballb 认为超分二采从 σ 0.9035 起「接近重生成、道具会变」而 0.6316 保道具、0.45 偏软——与 06 簇 ResCascade 的 0.45 结论并列：**保道具/文字选 0.63，保纹理一致选 0.45，都不要 0.90**；② egguy886 的「数量锁无效」（C 段）与「道具数量写死有效」（C2 段）不冲突：前者给本不会重复的东西加锁反而漂服装，后者只对真会多出来的道具；③ capruokz 的 action 模式「不写时间戳」与官方 `[Shot N] At MM:SS` 相反，仅限纯动作无台词段且他自己承认 0.3 s 切被拉成 42 帧的根因是时间块，短剧对白段仍走六段式；④ manju‑studio 说 Ref2VA 加 `SigmaShift 6` 会全黑——这与 skill 已有「Ref2V 用 12/3、FL2V 768p 才用 6/3」一致，是对 **不要把 FL2VA 的 shift 搬到 Ref2VA** 的再次实证。
10. 这批仓库共同指向一个空白：**没有人把「latent 冻结续接」与「段内分段二采」合成一条管线**——fuzzballb 在像素域交叉淡化超分段，pongjoo 在 latent 域承接二采边界但只验到 1 MP 73 帧。4090 上可先用 pongjoo 的 5 帧正重叠做 768P→1080P 分段二采，再按 fuzzballb 的规则（关 Cache、关 SLA、LoRA 总强度 ≤1.3）跑续接。

---

## 一、有新信息的仓库

### fuzzballb/comfyui-h3-long-video（★0，无 LICENSE 文件，最后推送 2026‑11‑05）
- **定位**：`h3_output_video` 节点包 + 4 条工作流 + story_kit 脚本，配 PlagueKind V11 模型栈与 seitanism MultiRef 的 `MiniMaxH3GeneratedAVMaskedContext`；RTX 3090 24 GB / 62 GB RAM 上做出 95 s 10 段与 2:35 16 段连续剧（1920×1056@48 fps）。
- **机制（long_video.py 549 行）**：`H3LongVideoContinue` 读上一段 `part_NNN.safetensors`（MC 格式 `{video,audio}`），把最后 `context_length=39` 帧（12 视频步 / 65 音频 tick）复制进新空 latent 开头，noise_mask 0 冻结，音频最后 `audio_feather_ticks=8`（0.2 s）余弦释放；采样后 `H3LongVideoAppend` 裁掉 39 帧，把音频 conform 到 frames/24 s 存 FLAC（10 段漂移 0.01 ms/段）。`new_shot=True` 则硬切、不复制。重跑第 N 段自动把依赖它的后续段移到 `_superseded/`，直到下一个 new_shot。每段另存 `part_NNN.cond.pt`（5120 维 Qwen 嵌入 + `minimax_token_tags` + `minimax_refs`），超分时不再跑 26 GB 文本编码器。
- **超分工作流**：LBH 3D 放大 1.5× → `MMH3UltimateUpscale` 102 帧时间块、`res_multistep`、ManualSigmas `0.6316, 0.3158, 0` → FILM ×2 到 48 fps → RCAS 0.3；续接接缝在像素域对 78 帧（1.625 s）线性交叉淡化，用改动前的 `part_NNN.tail.mkv` 防止二次混合。作者对照：σ 0.9035 让纸箱贴纸变成粉色 "URGENT" 再变透明白盒；0.6316 道具不变；0.45 偏软、标签漂。
- **人脸工作流（face_detail.py）**：YuNet 置信 0.6 检测 + SFace 余弦匹配 `match` 0.35（工作流用 0.3），只认 ≥40 px 正脸（眼距 ≥0.33 脸宽）、每帧独立匹配不链式跟踪、24 帧内孤立命中丢弃、≤12 帧空隙插值；`box_scale 2.6` 裁 512² 稳定方框 → ManualSigmas `0.8, 0.6, 0.4, 0.2, 0` 重绘 → 椭圆 0.75 羽化 0.35 颜色匹配贴回；只处理 30–140 px 的脸。实测本人 0.35–0.59、旁人 −0.01–0.13。
- **三条硬实证（同 seed 对照）**：① `H3MiniMaxCache` 在冻结前缀下忽略上下文，接缝帧差 28 vs 无缓存 9——续接链**禁用任何步间缓存**；② `H3SLAAttention`（70% 稀疏 int8 QK）每步 30 s vs 86 s，但窗框倾斜、阳台时隐时现，默认关；③ Turbo 0.95 + shift 12/3 8 步接缝帧差 3.6（段内 2.5），可用；叠 camera 0.8 + human‑motion 0.5 + texture 0.6 → 小物件透明重影，降到 0.6/0.3/0.4 即实心——**额外 LoRA 总强度控制在 1.2–1.3**。
- **提示词实证**（README「Prompting tips」18 条）：每段重复完整角色描述；续接段以 "Continue the same shot without a cut. One continuous take, static locked-off camera." 开头；一段只一个动作；不要从动作中途续接（改 new shot）；声音词会把镜头拉过去（写 "rushing water" 就切到水）；无声倒数会被念成乱码，所有要说的话都写成引号台词；道具做白底产品图当额外参考比文字稳；"没有桥" 要写成 "只有断桩露出水面"。
- **4090 价值**：3090 数字可直接上调：Turbo 8 步 1152×864×10 s ≈12 min、超分 ≈13 min、人脸 4–5 min/段；一分钟片 ≈7 段 ≈1.5 h。1280×720 会在底部出 16 px 条纹带（720 非 32 倍数），用 1280×704。
- **坑**：依赖 PlagueKind + MultiRef 两个包（后者 9 月停更）；无 LICENSE；Linux 验证为主（journalctl）；超分期间 TE 26 GB + 模型 20 GB 常驻需 ≥62 GB 内存。
- **评级：采用**（机制与规则）；节点本身在 4090/Windows 需自测。

### pongjoo/ComfyUI-PJ-SegmentSampler（★0，MIT，最后推送 2026‑11‑07）
- **定位**：5 个节点（Planner / H3EditPrepare / H3SegmentContext / FirstPass / SegmentSampler）做「一采分段接力 → latent 放大 → 二采分段精修 → 看高清后回修一采并只更新对应高清区」，保留标准 LATENT 接口，不改核心。3,124 行 Python + 181 项回归测试 + 真机验证报告（5090D 24 GB）。
- **一采接力（segment_relay.py）**：后段继承前段最后 **7 视频潜步 = 22 帧**，用原生 `denoise_mask` 固定（`constrain_boundaries`），接 `PJ_H3SegmentContext` 时再把前段尾部转成关键帧运动引导；拼接时「前段拥有重叠，后段只复制新增后缀」，音频按 40 Hz 时钟去重；每段 seed = 基础 seed + 段偏移；磁盘缓存按签名失效整条后缀。
- **条件集中准备**（v1.4.1）：接力时先编码所有段条件写盘，卸载编码器后连续采样（E/E/E/S/S/S 取代 E/S/E/S/E/S）；3 窗 73 帧节点耗时 48.8–69.4 s → 35.4–37.2 s，CUDA 峰值不变 ≈21.3 GB。作者坦承量化 + LoRA 在不同加载状态下不保证同 seed 逐值复现。
- **二采分段（pj_segment_sampler.py）**：输入放大后 AV latent、SIGMAS「通常 2–3 步」、`run_mode` 智能缓存/全部/仅第 N 段/按秒定位，每段 `segN_lock`；Planner 默认段长 6.0 s、重叠 1.5 s、`0-6, 4.5-10.5, 9-15` 自定义区间。**关键实测**：同基准同 seed，零重叠 vs 5 帧正重叠（0.208 s），切点 16→17 帧差 0.0737→0.0209（−71.6%）、50→51 0.0650→0.0242（−62.7%），亮度跳变 0.0255→0.0043；正重叠承接已精修前段边界、**单份交付不做两份加权混合**。
- **局部回修（segment_local_repair.py）**：以上次成功结果初始化，默认 denoise 0.4（0/0.2/0.4/0.6 × 2 seed 矩阵都只改目标潜步 `[7,13)`，音频逐值不变），目标两端各锁 `boundary_tokens=2` 个视频潜步；注意潜步只改 [7,13) 但 VAE 解码后像素影响帧 18–55——**时间保护 ≠ 像素逐值保护**。
- **真机配置**：hybrid fl2va_ref2va b25‑49 int8 + qwen3vl_32b nvfp4 + video VAE int8 + `ref2v_turbo_4step_v0.1`；`er_sde` + `beta`，一采/回修 6 步、二采 3 步；1 MP（768×1376）73 帧「放大 → 三段二采 → 回修中段 → 更新高清」耗时 284.8 s，CUDA 峰值 22.84 GB。855 帧（35.6 s）7 窗接力 97.9 s / 21.42 GB（320×192 小样）。
- **坑**：第一版只保证**当前后端会话内**回修（节点实例丢失要重载基准）；放大器全量执行、未做增量放大；右端仅 latent 锁定无反向运动引导；Autogrow 接口键名 `ref_images.ref_image_0`；零重叠不等于无跳变。中文 UI。
- **评级：采用**（二采 5 帧正重叠 + 局部回修思路可直接搬到 ResCascade/手搓二采）。

### egguy886/h3-drama-kit（★0，MIT，最后推送 2026‑11‑07）
- **定位**：《越线》60 集 480 段（AutoDL `minimax_h3_zm_u24` 工作流）+《I Texted the Wrong Billionaire》《错撩》《Tangled in His Bed》自有 ComfyUI（zealman 面板 U24，0.4 MP 一采 ×1.5 二采 → 736×1312，15.08 s，约 6 min/段）的流水线：16 份 playbook + 48 个脚本（lint / preflight / 自动质检 / 换种子重出 / Demucs 人声 / seed‑vc 统一声线 / 字幕 / 响度 / TikTok 黑边）。竖屏 9:16 为主，规则对横屏同样成立。
- **结构规则（量产级证据）**：每段 15.0 s ≤6 镜（7 镜切点命中率 91–97%→89%）；最后一句台词 ≤13.5 s，末 1–1.5 s 有内容停留；英文六段式切点误差 ≤0.3 s、中文晚 1.6–2 s；同场景跨段**硬切 + 换景别 + seam_motive（action/gaze/sound）**，禁全景接全景，尾帧接力只作例外（接力缝重复一秒、首帧僵、运镜减半）；每段写**首帧站位**（0 s 时谁在哪、朝向、手持物、车内/电梯写机位）并注明 "positions and postures only"，45 处接缝 44 处接上。
- **动作量实证（175 段 E41–E60 + RH 对照）**：固定全景开场首秒动作量 2.9 vs 推/跟 19.6；删 "holds a static shot" 后 5 秒 4→8；"in slow motion" 删掉 14.7→22.2；打斗每击单独一镜 0.8–1.4 s 前 5 秒 28–30（长镜 3–4）；**精简提示词（<400 词）动作段动作量 +60%，但对白段人声提前 1.5 s 开口**；人物写 "frozen/completely still" 拖掉 ~80% 运镜；场景参考图让运镜减半但去掉就丢地点一致性（保留）。
- **台词实证**：说话句外的 say/speak/lips part 会被念出或开口；总述里的台词转述被先含糊念一遍（12/90 段）→ 总述只写动作；英文氛围句被念出（E05 Seg7 4/4）→ 删掉 + 加 "Speak only the quoted dialogue lines"（多说词 9.3%→1.3%）；"..." 处被塞乱码插词（换逗号）；声线开头 "Name, a man of N:" 个别段被念（85 段中 2 段，换种子无用）；原生对白音色每段漂 1.7 半音 → 后期 seed‑vc 统一，TTS 整句重配判无效。
- **自动质检（qc_lib）**：Whisper 逐词模式；整句相似度 <0.72 FAIL、0.72–0.88 WARN；开头/结尾 3 词覆盖不足 2 且 <0.95 FAIL；转写词数 > 台词 ×1.15+2 判「插词」；FAIL 自动换新种子重出最多 3 次（同种子出同一结果）；时长 14.3–15.8 s、有音轨。切点检测阈值 0.18、暗场景不可信只标记不重出。
- **资产规则**：角色三栏表（脸特写 / 正面全身**去头** / 背面）或 3×2 六格；场景 3/4 高机位空镜、可变物体画「动作之前」状态、每个状态单独 ID；带可读文字的道具先做 `image_text` 参考图而不是后期叠字；被否决的图搬出 assets/；皮肤写 "clean, smooth and evenly toned" 压雀斑放大；脸红不写（画成皮炎）；痣写 "one single rice-grain-sized flat mole"。
- **声音策略**：提示词声音行全集统一 `QUIET_SOUND`（安静房间底噪 + 动作声 + 干净人声），Demucs 只留人声，按场景铺连续环境底、音效后期——否则段缝处背景声跳。设备声（电话/广播）不进 H3。
- **显存**：U24 工作流 0.6 MP 一采爆显存，保持 0.4 MP × 1.5 二采；单卡同一时间只留一个出片进程。
- **评级：采用**（规则与 lint 思路；AutoDL/zealman 部分不适用）。

### wbliang168/manju-studio（★0，MIT，最后推送 2026‑11‑06）
- **定位**：Windows Tk 桌面「剧本 → 分镜 → 定妆照 → 逐镜 H3 → QC → ffmpeg 拼接」漫剧工作台，12 GB 显存路线：`minimax_h3_ref2va_pruned-Q4_K.gguf` + `qwen3vl_4b_int8_convrot` + `mmh3-4b-ClipProj-v3.1-mlp`（4B 编码器 2560 维必须挂 ClipProj 投影到 5120 维，否则 "mat1 and mat2 shapes cannot be multiplied"）+ `ref2v_turbo_4step_v0.1`；可选 TESpeed + KJ Sage + ChunkFeedForward + SelfLift 低清→全清两段采样（H3SigmaRefiner start 0.7 cosine）。
- **BUGS.md 实跑教训（23 条）**：#16/#20 流水线只接 VAEDecode 丢掉了模型原生音轨再贴 edge‑tts → 口型物理上不可能同步；修法是 `VAEDecodeAudio` + 每镜音轨对齐拼接 + loudnorm，**不再叠合成底噪**。#18 720×1280 直接崩（720/16=45 奇数，报在采样器里的 shape 错）→ 宽高强制 32 倍数，成片 720×1280 用 576×1024 生成再 lanczos 放大。#19 帧数不在 17k+5 崩 → `align_len` 向上吸附。#13 `-shortest` 咬掉末句 → 画面 tpad 补到语音长。#15 22 帧只有 0.9 s 真实动作。
- **训练分布规则**：一镜帧数取 **[124, 362]**，短于 124 帧「动作做不完、音频发虚、人物中途变形」；按中文 4.3 字/秒 + 标点 0.4 字 + 0.25 s 起 + 0.55 s 收估时长，收尾镜建议 +15%（最少 +22 帧）。
- **Ref2VA 不接 SigmaShift**：照 FL2VA 经验加 `shift_video=6` 整条片全黑（latent 被压平）；官方 R2V 模板无 SigmaShift，模型从 LoRA 直连调度器。
- **API 坑**：Autogrow 在 API JSON 里键名是 `ref_images.ref_image_0`，写成列表不报错但参考图被**完全忽略**（出图全黑、无日志）；`BasicGuider` 多传 `cfg` 靠容错才没炸。
- **QC 阈值（实测标定）**：相邻帧灰度差（240 px 宽）动作镜 ≥2.5（1.85 判「该动没动」）、特写/近景动作 ≥1.8、未识别 ≥1.8、任何镜 <1.0 冻结、<1.2 才值得重跑；全片跑完后再用「低于本片中位数 45%」做相对判定（打斗片普遍 5–10、情感片 1.5–3）；亮度 <8 黑屏、std <3 纯色、帧差 <0.4 占 90% 判冻帧；动作不达标默认重跑 2 次。`MOTION_SUFFIX` 写死「微风拂动枝叶」在室内镜凭空长叶子 → 改中性句。
- **评级：试用**（QC 阈值与坑单直接借用；12 GB 路线对 4090 不必要）。

### martinsommer3-oss/Filmworkbench-Starter（★0，MIT，最后推送 2026‑11‑07）
- **定位**：「用聊天 agent 做短片」的配方包：8 个场景配方（K1 对白特写、K2 反打、K3 离开再回到已改变状态、K4 定场 + 音频先入、K6 飞船舱内外、K7 已知角色入空镜、K8 湖怪、K9 穿门）+ MARKET 组合案例，`film.py init/check/next` 逐阶段审批，44 个 API 图 + bindings 全部附带，Win11 + 5090 32 GB + 128 GB RAM 验证。
- **精确栈（docs/STACK.md + graphs）**：`minimax_h3_hybrid_fl2va_ref2va_b25-49-int8` + `qwen3vl_32b int8_convrot` + video VAE int8 + audio VAE fp32 + `minimax_h3_DMAD_4step_full_lora_avg_rank_39_bf16`（强度 1.0，**两采都挂**）+ LBH `latent_upscaler_3d_conv_v1_fp16`；续接配方才用 `ref2v_turbo_8step_v1.0_768p`。S1：`MiniMaxH3ReferenceToVideo` + `AddGuide frame_idx 0`、**8 步 er_sde/beta denoise 1.0、864×480**；S2：`MotionContextLoadLatent` → LBH 3D → `LTXVSeparateAVLatent`/`LTXVConcatAVLatent` → **2 步 er_sde/linear_quadratic denoise 0.4、1952×1088**；注意力 `ModelAttentionBackend = comfy kitchen attention` + `BlockSparseAttention`；成片用 S1 音频。续接用 NikoDemon80 Motion Context `audio_context_length 18`、`MotionContextTrim match_tail true`。
- **实测（5090）**：首段 14.375 s（345 帧）S1 72.5 s / S2 184 s；K1 两段 685 帧 S1 178 s / S2 438 s；23 个 S1 阶段 + 11 个 S2 阶段全部通过完整解码；作者明说「Wall 含轮询、非基准」。
- **K3 配方机制**：道具移动 → 切到别处 → 返回时用**实际接受的末帧 + 一张明确「已改变状态」的参考图**（`<Picture 1> is the actual current living room state after the teapot was moved…`）作起点；「状态由人显式提供，不是模型记忆」。
- **EDIT_NOTES 有用结论**：裁剪/重构图保表演与声音；替换短镜用成片一帧 + 角色参考重生成、按帧边界插回并匹配下一镜状态；H3 视频条件编辑在「换物件动作」案例可行；**未解决**：保留原声同时改说话镜、接缝处编辑不失效后段。
- **坑**：52.6 GB 权重、128 GB RAM 环境、未在 24 GB 卡验证；参考图用 GPT Image 生成（Krea 2 为本地备选）；德语对白英字幕。
- **评级：试用**（DMAD 两采参数与 K3 状态图法可直接 A/B；别照搬 1952×1088 到 4090 前先测显存）。

### dreevelle/ComfyUI-ResolutionTools（★6，MIT，最后推送 2026‑11‑07）
- **定位**：3 个无依赖节点（Resolution Preset / Resolution Selector (Real MP) / Align Resolution to Grid），README 是一篇分辨率数学论证。
- **纠错 ①**：ComfyUI 内置 `ResolutionSelector` 用 `megapixels × 1024 × 1024`（mebipixel），所有数值面积虚高 4.86%；官方 H3 教程的 0.98 MP = 1.03 真 MP；16:9 对齐 32 时输入 1.03 得 1344×768，输入 0.98 得 1312×736。
- **纠错 ②**：**1344×768 是 7:4（1.750）不是 16:9（1.778）**，两轴各自取整才碰巧落到 H3 原生画布；对齐 32 的精确 16:9 格点是 `512n×288n`：512×288 / 1024×576 / **1536×864（1.33 MP，比原生 1.03 MP 多 29%，作者认为是值得默认跑的最高一档）** / 2048×1152 / 2560×1440——「流传的 H3 分辨率表没有一张是真 16:9」。低于 0.6 MP 时独立取整的比例漂移可达 6.9%，用格点。
- **交付 1920×1080**：在格点生成后用核心 `Upscale Image`（**不是 `Upscale Image By`**，step 0.01 取整会出 1917×1079）缩放到 1920×1080，滤镜 **lanczos**（zone‑plate RMSE 0.00298；`area` 在接近 1 的非整数倍率下比 bicubic 差 10×；lanczos 经 PIL 量化到 8‑bit，16‑bit 母版先存再缩）；1920×1088 是表里唯一要裁 8 px 的（1.7647 非 16:9）。
- **对齐机制**：H3 = VAE 16× × patch 2 ⇒ 32；差一格核心 `pad_to_patch_size` 用**circular padding** 把顶部包到底部，底/右出 16 px 色带（与 08 簇 wjc573 结论一致，这里给出了成因）。
- **评级：采用**（规则）；节点可装可不装。

### Zowwan/studio-grade-ai-video（★0，MIT，最后推送 2026‑11‑07）
- **定位**：沙特小工作室的面部身份门禁脚本 `facematch.py`（YuNet + SFace，CPU）+ QA 清单 + 运动提示词手册；H3 部分在 WanGP 内运行（变体 H3 Singularity / Pika H3 Flex 6 步）。
- **阈值**：SFace 官方同人阈值 **0.363**，商用锁脸 keep 默认 **0.55**、严格 0.65；`--det-conf 0.6`；抽帧 `fps=2`（快动作 4）。「分数是警告不是门禁：有纹理的真实帧可能比更假更光滑的帧分低，矛盾时真实感赢」。
- **QA 顺序**：先问「普通观众会不会信这是实拍」——CG 感/塑料皮肤/过净光线即 FAIL；手指数、几何（logo/雕花）跨帧不变、布料物理；9:16 安全区 x 86–994 / y 230–1536；响度约 −16 LUFS；FAIL 先剪裁/修帧再重生成。
- **第一次试拍失败复盘**：7 张静帧各 1 s = 「照片在呼吸」；正文写否定（no blinking…）命名了 blink；取 4–5 s 长条再截 1.5–3 s（掐头去尾 0.5 s）；手势类要首尾帧而不是只靠文字。H3 侧：FL2VA 静音脸相似度 0.886 vs Ref2VA 带音频 0.09（单一测试者，未验证）；guidance 1、17n+5、全 20 步 shift 12、人脸重要时 turbo 6–8 步。
- **评级：借规则**（0.363/0.55 两档阈值 + 「真实感优先」写进 QC）。

### richiepic/ComfyUI-RICHIEPIC-H3（★0，MIT，最后推送 2026‑11‑05）
- **定位**：一个 `RICHIEPIC_H3ReferenceGallery` 节点（缩略图画廊 + 外部 IMAGE/VIDEO 合成一个有序 `H3_REF_LIST`）+ 2 条工作流：RefMod Builder、用 RefMod 代替参考图的 **Head Swap**；上游是 Luisacaotica MiniMaxH3Mod 0.2.7 的 `RefModMasterExtract / RefModsLoader / RefModTextEncode`。ComfyUI 0.42.0 + 5090 验证。
- **RefMod 构建实测**：Full Reference 每图约 **330 token@ref_resolution 512**；`budget_policy=error` 看真实计数以免静默丢参考；**特写肖像放第一张定画布**，其余 cover‑crop；文件存 `models/refmods/`。
- **Head Swap 工作流（analyze.py）**：`ref2va_pruned_int8_convrot` + nvfp4 TE + SigmaShift 12/3 + `EmptyMiniMaxH3LatentAV 1344×768×124` + `AddGuide frame_idx 0`（引导视频）；一采 `minimax_h3_head_swap_v1.0_r32` 1.0 + `minimax_h3_dmd_ref2va_8step_turbo_pruned` 1.0、euler/simple 8 步、ManualSigmas `1.0, 0.970874, 0.907249, 0.64, 0`；二采 `MinimaxH3LatentUpscaler3D` + `minimax_h3_lms_v1.0_r64` 0.7 + ManualSigmas `0.9035, 0.6316, 0.3158, 0`；`ColorMatchV2 hm-mkl-hm` 回配引导色；提示词为空，全靠 LoRA + RefMod。引导视频按 24 fps 载入并裁到 17k+5（5.875 s=141 帧、8.708 s=209 帧）。**用 head swap LoRA 而不是 character swap**（后者换整个人）。
- **评级：借规则**（RefMod token 预算 + 头替换参数；短剧换头场景少）。

### mcoblackmore/digital-human-16gb（★0，MIT，最后推送 2026‑11‑07）
- **定位**：4060 Ti 16 GB / 32 GB RAM / ComfyUI 0.43 上复刻 builder2 数字人 skill：Qwen‑Image‑Edit GGUF 做脸 → Qwen3‑TTS 克隆 → H3 ref2va + `PixaromaH3AudioSync`（把音频塞 `ref_audios` 只影响音色，模型会自编语音）→ 拼接。
- **「8plus2」两段式实测**：草稿 896×512×124 帧 8 步（DenoMix ref2va int8 v3 + Acc‑8Step + dmd 8step 双 LoRA）330 s / ~13 GB → 1.8× latent → **只跑 2 步**（`BasicScheduler(8)` → `SplitSigmas(6)` 取**输出槽 1**；槽 0 是从头重画出纯噪声）+ `minimax_h3_open_regenerate_2k_refiner_rank_16` + 音频 `SolidMask(0)` + `SetLatentNoiseMask` 屏蔽 → 1600×928 531 s / 12 GB；锐度（Laplacian 方差）160 过 150 门槛。
- **否决实验**：删 refiner LoRA 1 步 91.9 / 2 步 98.8 锐度（加步数救不回）；**瓦片二采对 6.5 s 片是净负收益**（891 s > 721 s 且更糊、构图变宽）——瓦片只在 15 s 长段塞显存时才用；Pika 6 步 LoRA 快 3 倍但锐度 417→154、构图变宽，「不是加速，是另一个模型」；纯 latent 放大到 1920×1088 眼睛糊；SeedVR2 1.2× 嘴部轻飘。SageAttention（KJ `MiniMaxH3MemoryEfficientSageAttentionPatch`，LoRA 后采样器前）草稿 −22%、精修 −32%，锐度不变。
- **拼接规则（join_clips.py，实测数字）**：裁底部 **12%**（H3 在胸像下缘凭空长手指，提示词压不住）；对齐到最大的脸只放不缩（≤1.35×）；裁每段头 0.1 s + 音频 10 ms 淡入（段首爆音峰值 863→34）；人脸尺寸跳变 −29.1%→+0.9%。QC：底部 25% 带 Laplacian 方差 <150 判糊（干净片 170–370、糊片 50–65）。
- **Motion Context 计划**（lab/04）：目标切点帧差 <2.0（现方案像素域 6 帧溶解 6.59），记录了官方推荐 22/18/match_tail。
- **评级：试用**（SplitSigmas 槽位、裁底 12%、瓦片否决结论直接可用；16 GB 模型选型对 4090 不必要）。

### capruokz/h3-comfy（★0，Apache‑2.0，最后推送 2026‑11‑05）
- **定位**：泰语三件套 skill（h3‑setup / h3‑run / h3‑prompt）+ `find_ceiling.py`（用 nvidia‑smi 功耗判断显存是否溢出到 RAM：util 100% 但功耗只有 48/180 W 即在搬数据；16 GB 卡约 294 帧见顶、362 帧慢 2.6×）；用 H3 Singularity 单程 0.6 MP 工作流。
- **参考 token 竞争（实测）**：2 张角色图 `ref_image_size=match` = **1,550 token**（`max` = 12,320）；124 帧 360×640 参考视频 = **14,000–27,000**；39 帧 176×304 = 2,090。重者胜：同 seed 两次，结果都是参考视频里的演员穿他的衣服坐他的沙发，**"do NOT take the faces" 与 "the man in <Video 1> is <Subject 1>" 都无效**；只想借「风格」就量化写数字（L/饱和度/b），视频参考两次失败且贵 1.7×。不要接来路不明的 `ref_video_audios`。
- **续接链选择**：静态戏（坐着对话）`<Picture N>` 始终引用第 1 段尾帧（链式引用色偏累积 L 107→86→74、sat 66→104→135）；运动戏引用上一段（引用第 1 段会每段回到起点）。第 2 段起**禁止 "The video opens on"**（会先铺全景）；尾帧参考要写「这里有谁已经在哪」+「不重复画背景里的人」+「不回到开头」。
- **五种模式**：dialogue / montage / footage / action / product；action 模式单段落无 `[Shot N]` 无时间戳（时间块会把 0.3 s 切拉成 42 帧）；H3 画不出「抱起/举起整个人」类动作，切到结果。无台词片不要接音频参考、不要声明 `<Audio N>`——那是 H3 自编台词的来源。
- **评级：借规则**（token 数字与链式引用规则新；泰语文档）。

### yuyuki/ComfyUI-Minimax_H3_Novel_Pipeline（★4，GPL‑3.0，最后推送 2026‑11‑06）
- **定位**：17 个 ComfyUI 节点，用 LM Studio（Qwen/Gemma/Mistral/GPT‑OSS）或 OpenAI 把小说章节 → 角色证据 → 视觉档案 → 空间连续性 → 六段式 H3 提示词（8,849 行 Python），不生成图像/视频。
- **校验器（pipeline_step3_generate.py）**：六段顺序严格；summary 以 `[reference generation + audio reference]` 任务前缀开头且不重复；`[Shot 1]` 无时间戳、后续 `At MM:SS.mmm` 严格递增且 ≤ 时长；**每镜 ≥2.5 s**（含末尾停留），`max_shots = min(设定, floor(duration/2.5))`；detailed_description 350–500 词（</> 报错）；台词 `<d>[Language] …</d>`；retention 标记只认 fully_preserved / partially_preserved / attribute_transfer / weak_reference，音频 fully_copy / partially_copy / reference / weak_reference；连续性监督二次审稿、修复预算 2 次；temperature 0.38。参考图只定义 Subject，不单独写 Picture 行。
- **评级：借规则**（2.5 s/镜与一镜一动的校验写法；本地 LLM 依赖重）。

### Code2Collapse/ComfyUI-MiniMax-H3-Suite（★0，GPL‑3.0，最后推送 2026‑11‑07）
- **定位**：411 文件 V3 `io.ComfyNode` 大包：换人「几何脊柱」（裁切规划 → 遮罩 → 注入 → 贴回 → 细节回注）、长视频惰性读帧/分段写盘、HDR/OCIO、以及一组**采样守卫**。
- **守卫思路（sampling_guard.py）**：`Protected Layer Guard` 若首/末 DiT block 或 FinalLayer / proj_out / audio_proj_out 被 `patches_replace`/object_patch 就报错；`Accelerator Conflict` 拒绝不兼容缓存叠加；`Legal Scheduler` 校验 sigma 表并**拒绝 SplitSigmas**；`Sigma Shift (Ratio Locked)` 默认视频/音频比 4（12/3）；音频质量门 RMS 比 <0.55 或低频能量比 <0.45 判「电平/低音塌陷」。
- **评级：观望**（守卫理念可作 skill 检查项；拒绝 SplitSigmas 与 06/本簇二采路线冲突，且包体过重）。

---

## 二、其余仓库归类

| 仓库 | ★ / 推送 | 一句话 | 对 4090 短剧 | 评级 |
|---|---|---|---|---|
| kkone1238899/awesome-seedance-h3-prompts | 0 / 11‑07 | Seedance 2.x + H3 双模型提示词对照 + GitHub 每日归集（Actions） | H3 部分是「万能填空模板」级别，低于 04 簇；对照表确认两边都「正说不否定、一镜一运镜、喂上一镜实际视频」 | 跳过 |
| zhangyanyans-oss/AI-anime-studio | 0 / 11‑07 | FastAPI 单页：DeepSeek 剧本 + 豆包分镜图 + AutoDL `minimax_h3_lightx2v` 云端 | 云 API 路线；仅「分镜图比例必须与视频一致否则裁切变形」可记 | 跳过 |
| nvmax/VideoBuilderH3 | 5 / 11‑05 | VRGDG Video Builder 的 Rust/Tauri 移植，歌→MV，自带 MCP/Agent API | 社区‑商业许可，MV 向；RefMod quick add、minimax keyframes UI 可看 | 观望 |
| Koongrizzly/MiniMax_H3_Standalone_app | 4 / 11‑07 | 不装 ComfyUI 的 PySide6 app，INT4/W4A8/INT8，最长 30–100 s，Spectrum/Sage/SOL/SLA 开关 | 「EMA 4 步 LoRA 配 Beta 而非 simple」「Spectrum 至少 6 步」两条与 03 簇一致 | 观望 |
| knapcio/MiniMax-H3-2x-DGX-Spark-TP2 | 14 / 11‑07 | 双 DGX Spark vLLM‑Omni TP2+SP2，FP8 DiT 20 步 | 20 步基线：5 s 1344×768 单 Spark 1399 s、双 643 s；10 s 80 s/步、15 s 147 s/步；TP 改变浮点归约顺序，同 seed SSIM 0.93–0.96 | 跳过 |
| keboqi/minimax-h3 | 7 / 11‑07 | Prism Studio：Gradio 多引擎工作台 + Modal 部署，Blackwell 向 | 不适用 | 跳过 |
| CortexIL/h3-studio | 0 / 11‑07 | 多人共享 RunPod 排队 Web（FastAPI+Postgres+S3） | 不适用 | 跳过 |
| shawnie117/minimax-h3-studio | 0 / 11‑07 | erdinoral Studio 私有派生：A40 48 GB Jupyter 部署 + 远程 API | 提到 Director 按章节跑 Continuum 序列、可暂停续采 | 跳过 |
| jdelahayes/runpod-comfy-blackwell | 0 / 11‑06 | RunPod RTX PRO 6000 ComfyUI 0.44.1 镜像 + profiles.json | 不适用 | 跳过 |
| nightclaw555/Comfy-colab | 0 / 11‑07 | Colab A100 两阶段省额度 + Next.js UI（泰语） | 不适用 | 跳过 |
| xentome/EDITS-WITH-AI | 1 / 11‑06 | MAX EDITOR：12 GB 3060 上做音乐剪辑，Pika H3 Flex 6 步 + Singularity v2，SAM 3.1 局部重绘 | 3060：22 帧 544×960 ≈3 min、5 s 1 MP ≈17 min；「每个 H3 任务跑 6 步 Flex」是 12 GB 的取舍 | 跳过 |
| congw729/InferRSI-MiniMax-H3 | 0 / 11‑07 | RTX 5070 12 GB 跑 FastH3 Trim 8 步 384×256×73 帧 + vLLM‑Omni 适配器实验 | 启动参数 `--disable-smart-memory --cache-none --reserve-vram 3.0` 是 12 GB 保命招 | 跳过 |
| ArcSeekerX/Xpark-Media-Foundry-Agent | 0 / 11‑06 | 飞书接入的对话式资产流水线，gemma3:4b 抽帧质检 | 「本地小 VLM 抽帧判通过/瑕疵」是 05 簇空白的一个雏形，但源码在 app/qc.py 未深读 | 观望 |
| OwenLittleWhite/cannlab-h3-ascend | 0 / 11‑06 | 昇腾 NPU 部署适配 + 持久条件缓存 | 不适用 | 跳过 |
| commitname/minimax-h3-accuracy-agent | 0 / 11‑07 | GPU↔NPU 训练精度对齐 agent（skill） | 不适用 | 跳过 |
| Yuuki-git/minimax-h3-8gpu | 0 / 11‑07 | 海光 8 卡 InfiniLM FL2VA，SSIM 93.5% | 不适用 | 跳过 |
| drimeF0/minimax-h3-jax-tpu | 0 / 11‑07 | TPU v5e JAX LoRA 微调移植 | 不适用 | 跳过 |
| MindrLabs/text-to-video-minimax-h3 | 0 / 11‑07 | model‑compose 一键服务；H200/RTX PRO 6000/Spark RTF 75–373 | 不适用 | 跳过 |
| jameswright1562/openjutsu | 0 / 11‑05 | D3voz/openjutsu 的无改动 fork（文件树一致） | 见 06 簇 | 跳过 |
| gjnave/GGF-Recast | 0 / 11‑07 | Viggle Remake（H3 衍生）多角色换人 app，内部预览许可，73 GB 权重 | 4090 实测 6 s 两段 736p 15.5 min；模型许可排除美欧英韩 | 别碰 |
| CodeAlexx/mm-AIR | 0 / 11‑07 | 私有 AIR 语言桌面 app 源码快照，不可构建 | 不适用 | 跳过 |
| pixelaigc/pixelaigc | 0 / 11‑07 | 个人主页 README | 见 01/08 簇其它 pixelaigc 仓库 | 跳过 |
| shihoos / cheems12 | 0 | 空壳（一行 README） | — | 跳过 |

---

## 可写进 skill 的规则（只写本簇新增）

1. 续接链上**禁用一切步间缓存**（`H3MiniMaxCache` / EasyCache / BlockCache）：冻结前缀下缓存忽略上下文，接缝帧差 28 vs 9（fuzzballb，同 seed）。
2. 续接/长镜头**关 SLA 稀疏注意力**：70% 稀疏让窗框倾斜、阳台闪现，同 seed 关掉即稳；只在抽卡阶段开（fuzzballb，3090 86 vs 30 s/步）。
3. 8 步 Turbo 上叠加风格/运镜 LoRA，**额外 LoRA 强度之和 ≤1.3**（0.6+0.3+0.4 实心；0.8+0.5+0.6 小物件透明重影）（fuzzballb）。
4. 超分二采 sigma 三档：**保道具/文字 `0.6316, 0.3158, 0`**；保纹理一致 σ 0.45 起；`0.9035` 起只用于「换尺寸再抽」——它会把纸箱标签改色变透明（fuzzballb vs 06 簇 ResCascade）。
5. 分段二采在段间留 **5 帧正重叠**（0.208 s，整数潜步），后段承接已精修前段边界、**单份交付不混合**；零重叠切点 MAE 0.074→0.021（pongjoo，5090D）。
6. 高清后局部回修：以上次成功结果初始化、denoise **0.4**、两端各锁 **2 个视频潜步**、音频 noise_mask 0；记住潜步 [7,13) 的改动会经 VAE 影响像素帧 18–55（pongjoo）。
7. 多段接力时**先编码所有段的条件再连续采样**（E/E/E/S/S/S），避免 TE/VAE/DiT 往返加载，节点耗时 −25~45%（pongjoo）。
8. 建分辨率表时按 **真 MP（×10⁶）** 换算：内置选择器是 mebipixel，官方 0.98 = 1.03 真 MP；1344×768 是 7:4，真 16:9 且 32 对齐只有 1024×576 / **1536×864** / 2048×1152；交付 1080p 在格点生成后用 `Upscale Image` 固定 1920×1080 + **lanczos**，不用 `Upscale Image By`、不用 `area`（dreevelle）。
9. 宽高不是 32 倍数时核心 `pad_to_patch_size` 做 circular padding，底/右 16 px 出条纹——1280×**704** 不是 1280×720，576×1024 不是 720×1280（dreevelle、fuzzballb、manju‑studio 三方独立撞到）。
10. 单镜帧数取 **124–362**（5–15 s）：<124 帧跑出训练分布（动作做不完、音频发虚、中途变形）；按台词估时：中文 4.3 字/s + 标点 0.4 字 + 0.25 s 起 + 0.55 s 收，收尾镜 +15%（manju‑studio）。
11. Ref2VA 链**不要接 SigmaShift 6**：照 FL2VA 经验加 `shift_video=6` 整条全黑（manju‑studio）；Ref2VA 用 12/3 或按 LoRA 说明。
12. API JSON 里 Autogrow 参考键必须写 **`ref_images.ref_image_0`**（`ref_videos.ref_video_0` / `ref_audios.ref_audio_0`）；写成列表不报错但参考被静默忽略、出图全黑（manju‑studio、pongjoo）。
13. 每段**同场景跨段用硬切 + 换景别 + 写明切点动机（action/gaze/sound）**，禁全景接全景；尾帧接力只作例外（重复一秒、首帧僵、运镜减半）（egguy886，E41–E60 量产）。
14. 开场全景必须**动**（运镜 + 持续动作）：固定全景开场首秒动作量 2.9 vs 推/跟 19.6；删 "holds a static shot"；全片 "slow motion" 最多一次（egguy886）。
15. 打斗**每一击单独一镜 0.8–1.4 s、一镜一动作**，写 "All action plays at full real-time speed" 一次（egguy886 RH 前 5 秒动作量 28–30 vs 长镜 3–4）。
16. **对白段不要精简提示词**（人声提前 1.5 s 开口）；动作段可用 <400 词精简版（动作量 +60%）（egguy886）。
17. 台词里的 "..." 换成逗号（否则停顿处塞乱码插词、换种子无用）；总述只写动作不转述台词；英文氛围句删掉并加 "Speak only the quoted dialogue lines"（多说词 9.3%→1.3%）；个别段被念出声线开头时只对该段去掉 "Name, a man of N:"（egguy886）。
18. 每段写**首帧站位**（0 s 时位置、画面侧、姿势、朝向、手持物，车内/电梯写机位）并注明 "positions and postures only; framing follows each shot"（45 处接缝 44 处接上）（egguy886）。
19. 生成时声音行全集统一「安静房间底噪 + 动作声 + 干净人声」，环境声/音效/配乐后期按场景连续铺；原生对白音色每段漂 1.7 半音，用 seed‑vc 统一而不是 TTS 重配（egguy886）。
20. 自动台词质检用 Whisper **逐词模式**：整句相似度 <0.72 FAIL、开头/结尾 3 词丢失 FAIL、转写词数 > 台词 ×1.15+2 判插词；FAIL 自动**换新种子**重出 ≤3 次，同类问题连续 2 次回去改分镜（egguy886）。
21. 动作量 QC 阈值（相邻帧灰度差，240 px 宽）：动作镜 ≥2.5、特写动作 ≥1.8、任何镜 <1.0 冻结、<1.2 才重跑；全片跑完后再按「低于本片中位数 45%」相对判定；亮度 <8 黑屏、std <3 纯色（manju‑studio）。
22. 人脸身份门禁用 YuNet 0.6 + SFace：同人阈值 **0.363**，锁脸交付 keep **0.55**（严格 0.65）；只信 ≥40 px 正脸、逐帧独立匹配不链式；分数是警告，真实感优先（Zowwan、fuzzballb）。
23. 远景小脸修复只处理 **30–140 px** 的匹配脸，裁 2.6× 方框到 512²，σ **0.8** 起重绘（0.6 更锐但保留错脸型），椭圆 0.75 羽化 0.35 贴回并颜色匹配（fuzzballb）。
24. 参考 token 预算：2 张角色图 `match` ≈1,550 token、`max` ≈12,320；124 帧参考视频 14k–27k token——**重者胜**，否定句与「视频里的人就是 Subject 1」都压不过；无台词片不接音频参考、不声明 `<Audio N>`（capruokz）。
25. 像素尾帧续接链：静态戏始终引用**第 1 段**尾帧（链式引用 L 107→86→74 色偏累积），运动戏引用**上一段**；第 2 段起禁 "The video opens on"（capruokz）。
26. 两段式精修「8plus2」：草稿 8 步 → 1.8× latent → `BasicScheduler(8)`→`SplitSigmas(6)` 取**输出槽 1** 跑 2 步 + refiner LoRA；≤7 s 片**不要瓦片二采**（更慢更糊构图变宽）；删 refiner LoRA 加步数救不回锐度（mcoblackmore，4060Ti）。
27. 胸像/口播拼接前裁底部 **12%**（H3 在下缘凭空长手指）、裁每段头 0.1 s + 音频 10 ms 淡入（段首爆音 863→34）、脸只放不缩 ≤1.35×（mcoblackmore）。
28. DMAD rank‑39 LoRA 两采方案可 A/B：S1 864×480 8 步 er_sde/beta → LBH 放大 → S2 2 步 er_sde/**linear_quadratic** denoise 0.4；「离开再返回」用实际接受末帧 + 显式「已改变状态」参考图（Filmworkbench，5090）。
29. RefMod 构建：Full Reference ≈330 token/图@512，`budget_policy=error` 看真实计数；特写肖像放第一张定画布；头替换用 `head_swap_v1.0_r32` 不是 character swap（richiepic）。
30. 每镜 **≥2.5 s**（含末尾停留），`max_shots = floor(duration / 2.5)`；detailed_description 350–500 词自动校验（yuyuki；与 egguy886 的 15 s ≤6 镜相容）。
31. 显存溢出到 RAM 不报错只变慢：看 nvidia‑smi **功耗**（util 100% 但功耗只有峰值 1/4 即在搬数据），不信 `/system_stats`（capruokz）。

---

## 未覆盖 / 未读完

- `fuzzballb` 的 `story_kit/run_story.py`（整本故事排队 + Whisper 校验台词 + ChatterBox TTS 对白模式）与 `check_cuts.py` 切点检测阈值未逐行读。
- `pongjoo` 的 `pj_h3_context.py`（逐段重建 Ref 条件与关键帧引导的实现）与 `pj_h3_edit_prepare.py`（SAM 空间遮罩）未读；DEV_LOG 未读。
- `egguy886` playbook 06（AutoDL）、08（后期交付、TikTok 规则）、14（导演风格宪法）、15 总导演手册未读；`comfy_run.py`（zealman 面板驱动、U24 参数）未读；`axis_lint.py`（轴线检查）未读。
- `Filmworkbench` 的 K2/K4/K6–K9/MARKET 配方正文与 `AUTONOMOUS_FILM.md` 审片循环未读；S2 图中 `BlockSparseAttention` 参数未展开。
- `Code2Collapse` 411 文件只读 README 与 sampling_guard.py；`WORKLOG` 未读。
- `nvmax/VideoBuilderH3` 的 `minimax_keyframes.mjs` / `refmod_quick_add.mjs`、`Koongrizzly` 的 Timeline Director、`ArcSeekerX` 的 `app/qc.py`（gemma3 抽帧质检）未读。
- `manju-studio` 的 `manju_skills/drama_video.py`、`gen_zimage_keys.py`（关键帧生图）与 `gen_fl2v.py` 未读。
- `xentome` 的 `app/retocar.py`（SAM 3.1 局部重绘 + LanPaint）未读。
