# 10 · 补读：01–09 各簇「未覆盖 / 未读完」清单

> 补读日期 2026‑11‑07。先 grep 01–09 的 `## 未覆盖/未处理` 汇总待读清单（约 70 项），按「对 4090 短剧流水线直接有用 > 规则/配置文档 > 其它」排序逐项补读；已克隆的在 `survey/repos|lt_misc`，另外新浅克隆 24 个仓库到 `survey/followup/`（VDN‑24GB、Flow‑Aligned、HybridWindows、CLSS、hyukudan、FrameInfill、FaceRefine‑Accelerated、FastVideo‑VSA、PTD ×3、DMAD‑X2、MotionCache、Contex‑Loop、r34vtraining ×2、SolAttn_triton、FastH3Patcher、daexchef、wasserman、mathruffian、Untwisting‑RoPE、VDN‑Plus）。HF 权重用 `api/models` 逐个核实存在性与文件名。所有速度数字均为作者自报并注明硬件。

## 结论（补读后真正新增、值得进 skill 的 10 条）

1. **comfy‑kitchen ≥ 0.2.36 的 masked‑attention 回归**（infinite‑creation `lib/agent/stages.js`）：开 `--use-ck-attention` 时 Qwen‑Image 2.1 在 mask 存活 token > 64 时崩图，H3 本身不受影响（r = 0.995）且不开 CK 慢 2.7×；上游 comfy‑kitchen#226 未修。→ 出图（Qwen‑Image）与出视频（H3）用不同启动参数/实例，不要共用一个带 CK 的 ComfyUI。
2. **续接「烧焦」有了可比数字**（KadoBOT `guide/continuity/long-chains.md` + Imagineer13 Anti‑Burn 模型卡）：6 段链 clip‑6 纹理能量 REF2VA int8 + ref2v turbo 8‑step v1.1 = 1.19（几乎不烧）、FastH3 omniref = 2.04、Larry turbo v4 = +261%（最烂）；Anti‑Burn LoRA 只挂在第 2 段起的续接段、0.5 起步、合并进 int8 会减弱；`context_noise` 能把 2.04 压到 1.75。→ 续接链用 REF2VA + lightx2v 8‑step，别用 Larry v4。
3. **帧网格规则精确化**（MultiRef `KEYFRAMES_AND_INSERTS.md`、PrefixStream/Motion‑Context 测试脚本）：全片 5+17k；AV 续接上下文只能 39+51k（56 不是合法上下文）；静帧钉位 17k（0‑based）；插入偏移取 51 倍数才音频精确对齐，17 倍数要 8.33 ms 音频取整；22 帧 = 7 latent/37 tick，39 帧 = 12/65；音频 feather 默认 8 tick = 0.2 s；请求 45 帧会被吸到 39。
4. **几份「悬而未决」权重的下载源已核实**：DMAD 4‑step LoRA 在 `Kijai/MiniMax-H3-experimental/loras/minimax_h3_DMAD_4step_full_lora_avg_rank_39_bf16.safetensors`（Yzmblog 原仓 401）；同目录还有 PDD Acc‑8Step FL2VA/Ref2VA、flashgen 4‑step、open_regenerate_2k_refiner r16；X2 Detail VAE 已有官方 `_int8_convrot` 版；lightx2v Turbo‑SLA 实为 `fl2v_turbo_4step_v0.1_768p_sla_comfyui_bf16`；FastVideo/FastH3 私有（401）→ 用 `nynxz/H3_Loras` 的 149 MB adaLN 补丁贴在 fl2va pruned 上即得 FastH3 8‑step（仅 FL2VA）；NRDX StyleTransfer、madebyollin/taeh3 不可访问。
5. **mathruffian `docs/03_規則與踩坑.md`（5090 实测、每条带退件理由）是本次最密的实战规则源**：首尾帧同一张图 → 画面 100% 冻住；尾帧构图必须与首帧完全一致但「是另一张图」；多人镜只给首帧、加身份参考会多出一个人；EasyCache 定稿不开；单镜 ≤ 12 s；不说话的脸给静音引导音轨；DMAD 4 步做日常定稿（8 类镜头看不出差、快 49–58%）；Veda 开着会在第 51/119/187 帧闪（17 镜 10 镜）；台词称呼后不写逗号、开头不写「……」。
6. **否定句之争有了裁决**：TFboy1 hybrid 的 `constraints:` 负向块、h3lite「compact negatives acceptable」与 04/09 共识矛盾。更可信的是 04/09（phileiny/forest‑laoli 实测 + negpip 存在的事实），但 mathruffian 实测 `NO black letterbox bars`、`Exactly N people`、okaypic「naming a thing summons it」说明**极短、具体、单句**的排除词能用。→ 规则：负向只允许 ≤ 1 句具体失败词，先找正向替代。
7. **对白音量要逐 take 归一**（okaypic `edit-format.md`）：H3 takes 在 −26…−10 LUFS 间漂，剪前每 take 先 level 到 −16 LUFS，成片 −14 LUFS/−1.5 dBTP；chiphoton 同 seed 对照里 Turbo 比 20 步标准响 1.7–4.3 LU。字幕时间可用 ffmpeg `silencedetect` 按台词句数自动分配再人工校。
8. **二采/精修补充参数**：Goldlionren Regenerate 默认 denoise 0.30（范围 0.15–0.35 = 起始 σ）、3 步、shift 6、×2；muse Refine V2 默认 beta/8 步/首段 2 步/1.0 MP；LongMedia Refine 音频 exact passthrough（audio noise 0 + mask 0）、16 GB 卡 refine 窗 73 帧 = 22 token；T8 VDN 二采「VDN 8 → 2× → VDN 4 或原生 H3 + EMA‑B LoRA」且 VDN 分支不再叠 Turbo；HybridWindows 243 窗/39 重叠/5 钉帧、PDD 8 步拆 6 顺序 + 2 联合、shift 12/3、CFG 1。
9. **24 GB 上的新实测数字**：VDN‑H3‑24GB（3090）0.4 MP 5/10/15/20 s = 1:09/2:05/3:21/4:20，0.8 MP 10 s 5:18，但要用 bat 启动打 block‑loop 补丁；FastVideo VSA（3090 Ti，0.8 MP 5 s）4 步 topk 0.1 采样 49 s（比 20 步快 10×）、topk 1.0 2:37，Sage/CK 在 topk 0.1 下无增益，峰值 ~22 GB；chiphoton GB10 int8 对照：Larry v4 6 步 vs 20 步 res_multistep 端到端 2.2×，I2V 首帧 SSIM 0.8215 vs 0.8245（几乎无差）。
10. **驱动 ComfyUI 的工程细节**（infinite‑creation）：`POST /free {unload_models:true, free_memory:true}` 每 N 次生成一次（AMD 默认 3、NVIDIA 0）；任务丢失 = `/history` 与 `/queue` 连续 N 次都查不到；preflight 只快速失败（LLM `/models`、ComfyUI `/system_stats` 各 4–5 s 超时）；分镜硬约束 `台词字数 ≤ 时长×5`、每镜 ≤ 2 说话人、参考音只给有台词角色且 ≤ 3。

---

## 一、05 簇：Agent Skill 与短剧流水线

### TFboy1 `references/hybrid-example.md`、`wenwu-director.md` 后半、`evals/evals.json`
- 读了：hybrid（官方六段式外壳 + WenWu 内容）完整 20 s 示例、八条生命通道/FACS/四种生镜形态/成片书写法、10 条 eval。
- 新信息：hybrid 在六段后追加第 7 段 `constraints:`（纯负向风格约束块）；20 s 拆 2×10 s **硬切 + 文字锚点交接，明令「禁止引用上一段尾帧」**；meta 带 `sound_events` 时间表与 `world_anchors`（出处标注到段）；FACS AU 强度 A–E，日常近景只用 A–C、D 只在峰值；台词三阶段（开口前/说话时/说完后）；evals 透露后端校验范围 `时长 5–15、steps 4–40`。
- 矛盾：① `constraints:` 负向块 vs 04「否定句不进正文」→ 04 更可信（实测 + 官方六段无此字段，多出的字段可能被当正文渲染）；② seg_02 的 `[Shot 1] 10.0-12.5s` 用全片绝对时间，与 01「段内局部时间、[Shot 1] 不带时间」矛盾 → 01 更可信（源自官方格式与 manju H2 校验）；③「禁止引用尾帧」与 05 结论 4（截末帧续接）矛盾 → 两者适用面不同：TFboy1 是无参考 T2V 风格 PV，短剧有角色参考时 05 的末帧路线仍成立。

### 漫剧老李 `scripts/validate_prompt.py` 本体 + `asset-spatial-ledger.md`
- 读了：5642 行校验器中的 H 系列（`validate_h3` H1–H12）与常量；资产台账的 16 项锁定、4 View 板、空间台账。
- 新信息（可直接做机检）：H1 六段缺/序错；H2 `[Shot 1]` 不得带时间戳、切点 MM:SS.mmm 严格递增、最后切点 ≤ 15 s；H4 `<d>` 必带 `[语言]`、六段正文一律英文（2026‑10‑02 官方复核）、切镜动词只认 `the camera/shot cuts|transitions|changes|switches to`，`cross-dissolve/fade/wipe/镜头切至` 会做成叠化融脸；H5 标签先定义后引用、summary 不得引入新标签、定义了不引用的 `<Subject>` 白占名额；H6 保留度只有 `fully_preserved/partially_preserved/attribute_transfer/weak_reference`（音频 `fully_copy/partially_copy/reference/weak_reference`），retention_analysis 里不得写 `(Sx)`；H7 `(Sx)` 按首现顺序从 S1 编；H9 画外音必须 `says in an off-screen voiceover … while his/her lips remain completely closed`，禁用 `{}`；H10 `non_diegetic_music` 不得复述台词；H11 说话人首现处 ±120 字内要有音色/语速词；H12 `[Shot 1]` 须含 `<Subject N>`、禁「同框/一同入画」并列句与「这只手/那张脸」悬空指代。
- 台账：角色板现行口径改为 **2×2 四格「无脸」板**（只有面部特写格有五官 + 图底声纹条），年龄/体型/职业标识三件套必写（`28~32岁男性·178cm·精瘦`），多人镜「在场声明 + 画外者明写不入画」、单实例铁律、景别‑取景半径匹配。
- 矛盾：四格无脸板 vs 05 结论 3 的「左 1/3 脸 + 右 2/3 三视图」→ 台账是 Seedance 出图侧规则（防多脸互相平均）；对 H3 Ref2VA 参考图，mathruffian 实测「本地生图参考只能单张半身照，多格板会被 Qwen 当拼贴照抄」，建议 H3 侧**每角色多张单人图**而非一张无脸板，05 结论需加此限定。

### infinite‑creation `docs/agent-architecture.md`、`lib/agent/stages.js`、`lib/core/comfyui.js`、`comfyui_original_workflows`
- 读了：架构文、CK 版本门禁、`/free`、任务丢失逻辑、两份 H3 Easy 工作流（analyze.py）。
- 新信息：见结论 1/10；四阶段拆批 llm/image/tts/video，`video` 必须接开 CK 的实例、`image` 必须不开；队列等待上限 120 min；工作流用 `minimax_h3_hybrid_fl2va_ref2va_b25-49-int8` + Larry v4 pruned LoRA 1.0（二采 0.75）+ `MysticXXX_MMH3-V4` 0.5 + KJ Sage patch，二采链 `Easy → LatentUpscaler3D ×2 → SecondPassConditioning → H3SigmaRefiner(simple 8)`、shift 12/3。
- 与 02/03 一致（混合底模 + 二采），无矛盾；但其 Turbo 选 Larry v4，与结论 2 的烧焦数据相悖——单段抽卡可用，续接链不用。

### h3lite `references/component-sets.md / cinematic-prompting.md / prompt-assist.md / video-upscale.md`
- 新信息：W4A8 路线上 Larry `turbo_v4_step600_ema` 与 Sage/Sol/Chunk/T8 叠加出现严重重影拖尾（h3lite 直接拒载）；W4A8 下别写 `natural skin texture/freckles/stubble`（量化成砂纸）——int8 用户可忽略；FlashVSR 2× 的正确参数 `--tile_size 256 --tile_overlap 64 --frame_chunk_size 50 --keep_models_on_cpu`（128/24 必出 128 px 网格），输出**无音轨**要 `-map 0:v -map 1:a:0` 回灌，必须 `ffprobe nb_frames` 核对是否被截断；Topaz Astra Fast 4060 Ti 209 帧 1.125× 4.5 min、2× ≈ 20 min；默认画布 640×352/5 s 只是 8 GB 路线的规划默认。
- 矛盾：「compact negatives acceptable」见结论 6；与 06「FlashVSR 真人用」无冲突。

### chiphoton Codex‑Drama `minimax-h3-comfyui/references/runtime.md`、三个子 skill、`docs/turbo-vs-standard.md`、profile‑distiller `analyze_video.py`；DeepSeek‑Harness `node-protocol-v1.md`
- 新信息：runtime 固定「Turbo 只允许 `MiniMaxH3TurboSampler` + `simple` + 4–8 步、默认 6 步、LoRA 1.0、low_vram off」，监控用 `/internal/logs/raw` + `PATCH /internal/logs/subscribe` 解析 tqdm `3/6 [09:59<09:59, 199.80s/it]`，ETA 只覆盖采样不含 VAE；R2V 上限 9 图/3 视频/3 音频；GB10 对照见结论 9；video‑editor 要求每个修改写「Change/Preserve 配对 + 全局不变量」；profile‑distiller 用 ffmpeg `select=gt(scene,0.30)` 估镜数与 ASL、`loudnorm I=-14:TP=-1.5:LRA=11` 量响度；node‑protocol 把 API 工作流转「字段绑定」，只把标量当字段、数组链接不动。
- 矛盾：默认 Larry v4 + low_vram off 与 03（alesha 3090 实测 low_vram on 反而快 25%）及结论 2 冲突 → 4090 自测，续接链不用 v4。

### dramake（xixihhhh）`format-routing / directing-camera-and-pacing / physics-and-failure-modes`
- 新信息：内部切镜预算（保守起点）「单内部镜 ≥ 4–6 s；10 s 段 2 镜；12–15 s 段 2–3 镜；20–30 s 段 2–5 镜」，超预算模型会压缩/跳过/乱切，减镜不加形容词；连续输出链深默认 2；约 30 s 连续配音场景要 4–7 个可见动作；物理事件合同六字段（`physical_start_state … physical_end_state`，必须同时写世界方向与屏幕方向）；每段只承担一个高风险物理事件；失败分级 P0（因果/换人/穿模/错说话人）/P1（服装漂移/道具瞬移/越轴/接缝）/P2（首尾坏帧/轻微色差）且 P0/P1 不得用字幕音乐掩盖。
- 与 01（≥1.2 s/镜）不矛盾，是更保守的上界。

### senmanx `docs/`（制作流程、生成视频提示词格式和示例、三视图、镜头提示词+10 秒）
- 新信息：全套中文六段式短剧模板：每段 5–15 s、2–4 镜、**段尾保持 0.8–1.2 s 便于截尾帧**；转场段用黑场/淡化**不接人物尾帧**；站位固定 A 左 B 右；BGM 全部 N/A；音色 `<Audio 1>` 标 `reference`（不复制信号）；文案按 35–50 字拆一镜；三视图提示词（左全身三视图 + 右上六头像 + 右下六细节格）。
- 矛盾：六段正文用中文，与 manju H4「正文一律英文（官方复核）」矛盾 → manju 更可信（引用官方 base‑en/ref‑en 原文），senmanx 可作中文草稿再译。

### okaypic `cast-format.md / edit-format.md`
- 新信息：见结论 7；cast 板是「左列正面特写 + 90° 侧脸，右列正侧背全身同比例」白底 16:9；`height_cm + build` 写进提示词否则人人中等身材；每角色一个跨场景锚点（红领带/发绳）；两个同年龄段角色必须在秃/胡/眼镜/体型上拉开；「写明族裔，名字不传递外观」。与 05 一致。

### TapCanvas `authoring-contract-v1.json`、`clip-design-and-packet.md`、`face-design.md`
- 新信息：合同明文禁止「固定镜头配额、固定时长范围、固定负面词堆、关键词/正则路由」，优先级 P0 事实 > P1 剧情可读 > P2 状态连续 > P3 执行 > P4 类型 > P5 润色；尾帧续写只在宿主判定「同场景无转场」时允许（`referenceAssetIndices=-1`），尾帧永远占第一张参考图槽位，大多数 clip 不该续写；face‑design：用 3–5 处骨相（脸型→颧骨→下颌→眉眼→鼻→嘴）定脸，同项目禁「鼻梁挺直/黑发束髻/高挑挺拔」等高频词（十余张卡里「鼻梁挺直」出现 7 次），六格（脸/发/体型/体态/主色/标志）组合防撞脸，主角一档允许唯一一句颜值定位句。
- 与 05 一致，补了防撞脸方法。

### 其它 05 项
- **KadoBOT** `story_prompts.py`（在 `h3_continuity/`）：`BOX_PLANNING_RULES` 建议 15 s 长镜拆 2+3+4+4+2 s 的可独立重试 box；每 box 自含、禁「continue/as before」等相对措辞；`long-chains.md` 见结论 2，另：`continuation_guide:false` 可去掉接缝处 3 帧定格但移动镜更跳；FastH3 v2 第 2 段必切到更近景别（第 1 段总比提示词写的更宽）。
- **chanon `nodes_joint.py`**：`H3ContextWindows` 默认窗 5 s / 重叠 1.25 s、pyramid 融合；tooltip 给出 1920×1088 下 5 s ≈ 7 GB 激活、13 s > 17 GB。
- **Goldlionren** `h3_regenerate.py` 见结论 8；`h3_sequential_audio.py` 默认 Hard Latent Prefix 模式、按 chunk 推导 seed。
- **ethanfel `H3-Prompt-IDE`**：VS Code 式六段编辑器 + `TextEncodeH3Edit` 联动；`AV_LATENTS.md`：音频长度 = `round(frames/24×40)`，Tv = 5k+2 ↔ 17k+5 帧，静音补尾 mask 置 1；`FOLEY.md`：视频 mask 0 / 音频 mask 1 做 V2A 拟音。
- **Work‑Fisher 动效库**：M01–M10 全是产品/录屏类运动模式，与短剧无关；**ancient‑rap‑battle `seedance_align.py`**：whisper 词对齐 + ffmpeg trim 拼段，与 H3 无关；**dseditor troubleshooting**：Colab 计费/下载 50–60 GB 等，无 H3 规则；**gary149/joeVenner/killkli** 未再读。

## 二、02 簇：长视频续接

### MultiRef `KEYFRAMES_AND_INSERTS.md`
- 见结论 3；另：`Custom Keyframes (Masked)` 保护一帧会保护整个 4 帧 latent step，两钉位落同一 step 直接报错；`Existing Video Masked Context` 默认 39 帧/65 tick、8 tick feather（前 57 tick 全保护）；中段插入必须用 `Assemble Interior Insert` 硬拼（非 crossfade）；`H3 Audio VAE Compatibility` 修 PR #15972 的音频中心裁剪、masked 节点懒检 PR #15988 速度转换。

### PrefixStream / Motion‑Context 测试脚本
- Motion‑Context `_node_smoke_test.py`：22 帧上下文 = 7 个 cond block 取 latent 索引 `[0,1,5,9,13,17,18]`，音频 keyframe 永远最后一个、`ref_audio_t 37`，`_steps_for_frames` 22→7、39→12、5→2、3→None（不是整 step 边界就拒绝）；且断言 `PackedLayout.__init__` 未被替换（证实 02「不改核心」）。`_probe_node_test.py` 是音频续接探针：相关系数 > 0.95 且 lag < 1 ms 判「clean continuation」，< 阈值判「imitating」。
- PrefixStream：`snap_to_run_grid(45)=39`；frame_choices 5..192 步长 17；软 mask 0.06/0.03 可选；`test_context_noise` 的噪声曲线 0.4→0 余弦衰减、最后一帧必为 0；39 帧保存 latent 带 `minimax_video_start_step 12 / audio_start_tick 65`。

### Continuum `SECOND_PASS_GUIDE.md`、`REGENERATE_INTENT_V396.md`；LongMedia `TWO_PASS…EN.md`、`DIRECTOR_REGENERATION_GUIDE_EN.md`
- Continuum：Second Pass 没有任何官方推荐 sigma/步数（只接外部 SIGMAS），音频原样透传；latent 插值放大会出双轮廓（Issue #27）；验证 GPU 是 5060 Ti、512×512、8 步 Turbo、Spectrum OFF。LongMedia：见结论 8；lipsync `audio_strength=1.0`；选择性重生成「只采一个目标、两侧缝合同有效才不扩范围」；MEDIA 块永不重采。
- 与 02「观望」评级一致。

### T8 `HYPERFLOW_LONG_VIDEO_EXP.md`、`PROGRESSIVE_LONG_VIDEO_EXP.md`、`VDN_TWO_PASS.md`
- 8 s 长片 = 124+68 帧、接缝 ≈ 5.17 s，续段 LOW 从**已接受 MP4 最后 39 帧**重编码；HIGH 1024×576 / LOW 512×288；隔离 Core 需 `--disable-comfy-compiler`；全部自述「未完成真人验收」。VDN 二采见结论 8。维持 02「全部 EXP」判断。

### ethanfel Contex‑Loop（新克隆，h3‑relay/WhaleTrans/LongMedia 的上游）
- `H3_CHAIN_FORMAT_GUIDE.md`：raw vs delivered（124→后续段交付 102、243→221、362→340，30 s = 736 帧）；派生 seed = `base_seed + 场景序号 + 场景 id`；续接模式 `guide(22) / latent_guide / masked_av(39) / tapered_av / drift_control_av(39, 8+4 taper)`；`audio_mode`：有完整配音用 `source_track`，只有音色参考用 `generated_audio`。与 02 机制 A/B 分类一致。
- Imagineer13 Anti‑Burn 模型卡见结论 2（10 段×4 场景均值：unseen model +61%→+4%@0.6，lightx2v 8‑step +44%→0%@0.5，Larry v4 +261%→+57%@0.8 仍不够）。

## 三、03 簇：加速

### 新克隆：VDN‑H3‑24GB、VDN‑H3‑Plus、Flow‑Aligned‑Regenerate、Untwisting‑RoPE、SolAttn_triton、FastVideo‑VSA、FastH3Patcher、PTD ×3、DMAD‑X2、MotionCache‑FastVAE；已克隆 VPack、X2‑Stream
- VDN‑24GB：见结论 9；权重 `speach1sdef178/VDN-H3-INT8-ConvRot-ComfyUI`（完整 stage 目录含 `model_spec.json` + default/turbo adapters）或 `drbaph/vdn-minimax-h3-int8-convrot-comfyui`；推荐 preset `lora_mode=merge, branch_weights=stream, attention_backend=grouped`，`auto_memory_latent` 必接采样器同一 latent。VDN‑Plus：5090 1280×736×145 帧 8 步 ~2:15（16.9 s/it），pruned 底模需 ~97 KB AdaLN affine（Comfy‑Org pruned 不含，用 `xmarre/MiniMax-H3-Pruned-Ref-Delta-Fused-r1024-ComfyUI`）。仍属「观望」：换架构 + 启动补丁。
- Flow‑Aligned‑Regenerate v0.3.14 与 Sol‑H3/VDN‑Plus/Continuum‑Plus 捆绑发版，无 4090 数据；SolAttn_triton README 首行 **DEPRECATED**（核心已内置 sol‑attn）→ 03 判断证实。
- FastVideo‑VSA（3090 Ti）见结论 9，需 Triton、FastVideo 4 步 LoRA；FastH3Patcher 证明 FastH3 = fl2va + adaLN 重参数化（149 MB）+ `to_gate_compress`（3.85 GB，只有 VSA 读）→ 不用 VSA 时 149 MB 即可；但 FastH3 为 FL2VA 谱系，Ref2VA 用户无益。
- PTD：taobao `MiniMax-H3-Ref2VA-PTD-{4,8}Step`（5.58/11.1 GB，per‑hop LoRA 不可合并）、EPFL fl2va 4/6 步、Nynxz int8 压缩版；Jalen 自述「unrendered，质量未知」→ 跳过。DMAD‑X2：本地把 DMAD r39 融进 FL2VA int8，4070 12 GB 544×960→1088×1920 124 帧 ~60 s，与 MATLOW 融合模型同速。
- VPack 默认 `2/5`，1344×768/4 s/4 步 Ref2VA 在 SM120 上 DiT 段 −24%（仅一次测试），要求 ComfyUI ≥ 0.38 → 升级后可试。X2‑Stream：4070 12 GB 60 s 出 1088×1920 5 s；精确绑定 ComfyUI 0.37.0 commit `1568e6c…`、comfy‑kitchen 0.2.35、需 `h264_nvenc`；X2 VAE 5.25 GB + int8 2.83 GB。MotionCache 默认 `reuse_threshold 0.15 / warmup 4 / max_skips 2 / 0.15–0.95`，与其它 cache 互斥。
- 矛盾：无；补充 03 结论 2——VPack 与 Veda/Spark 同样要求 0.38。

## 四、06 / 07 / 08 / 09 簇

### 06：Luisacaotica `PLAN_0.3.0.md / BUNDLE_FORMAT.md`、T8 `speech.py`、NyckM `camera.py`、openjutsu 工作流、Viggle 长视频工作流（PNG 内嵌）
- MiniMaxH3Mod 0.3.0 方向改为「库/QoL」，明文**不采纳**「RefMod 解决角色串味」「16384 token 硬上限」等研究断言 → 06 观望判断不变；bundle v5 为多参考容器（image `[1,24,1,H,W]`、audio `[1,32,2,T]`）。T8 `speech.py` 是 TTS 式 speech plan（分句、语音 profile、能量裁剪）无新参数。NyckM camera.py 是轨迹→提示词编译器。openjutsu face 工作流 = `ref2va_pruned_int8` + DMAD 4‑step r39 LoRA + 6 步 simple + int4 CLIP + int8 video VAE + SAM 遮罩。Viggle 长视频：`BlockSparseAttention sol-attn 1.3/0.2`、`SigmaShift 3/3`、窗 124/上下文 22、`bong_tangent` 8 步 + 分块 CustomSigmas（7/5/3 步）、DMD LoRA。
- SatoDive IMG Gen：默认 2.5 MP（tooltip「H3 剧照 ≥ 3 MP 最好」）、Fast 2‑pass 预设 `er_sde + lora 0.38 + refine ×1.5/10 步`，与 06 Fizgig‑Still 结论一致。

### 07：Fizgig `FINETUNE*.md / TRAINING_SHARE.md / MASKED_TRAINING.md`、AcademiaSD Settings reference
- 24 GB 全量微调 H3 可行：用 **pruned int8 底模**（bf16 66 GB 只能 LoRA），24 GB 走 5 窗循环（fc1 切两片）峰值 19.1–21.5 GB，视频片段只到 2.3 s（56 帧，5.2 s 需 >32 GB），每次保存 ~21 GB，系统 RAM 23–38 GB；rank 64 回提 LoRA 与全量「感知无差」。MASKED_TRAINING 用 MediaPipe/SAM 3.1 自动做人像 mask。TRAINING_SHARE 为双机分摊（家用 5090 + pod，epoch 75–80 s → 50 s）。
- AcademiaSD：`lora_dtype fp32`（勿降）、`adamw`（8bit 脸发软）、`constant_with_warmup`、`caption_dropout 0.05`、`num_frames` 必为 17n+5、**`use_sage_attention` 训练时无效（无 backward，q/k/v LoRA 收到零梯度）**、`sigma_shift` 勿填 12、音频单独训练尚坏、训练的是通用分区而非 Ref2VA。与 07 一致。

### 08：HybridWindows、FaceRefine‑Accelerated、CLSS、hyukudan、FrameInfill、权重核实
- HybridWindows：243 帧窗/39 重叠/5 钉帧、PDD Acc 8 步拆 6+2、CFG 1、shift 12/3，2 分钟 2895 帧 Ref2VA 对照在 H200/H100 上做；DMD 8‑step 也能跑。FaceRefine‑Accelerated：4 脸/768² atlas、每次 ≤ 9 脸、0.2 s latent 前缀交接、检测到硬切重置链。CLSS：面向 16 GB，默认 `tau_c 0.05 / beta 0.40 / overlap 7 latent`，发现音频 ref 若把增益写回 latent 会让 RMS 0.48→0.85 五段爬升 → 增益只在导出层。hyukudan：GPL，OpenAI 兼容 + `llama-server`，17 语言/88 方言标签，宽高 16 px 对齐。FrameInfill：patch `PackedLayout.__init__`，640×640×8 s 约 24 GB，锁 ComfyUI 0.30.x → 与 01 互斥名单同列。
- 权重核实：X2 Detail VAE（int8_convrot 已有）、Semantic Bridge（`speach1sdef178/…` 69 文件）存在；StyleTransfer LoRA、taeh3（只有 `t8star/Taeh3-Comfy`、`OzzyGT/taeh3` 社区版）不可验证；Pika‑Labs/Pika‑H3‑Flex（+Turbo LoRA）与 `WarmBloodAban/Minimax-h3_Singularity`、`WAS/…_v2_pruned` 存在；mathruffian 6 镜×2 seed A/B 结论：Singularity V2 动作大 1.5–2.4× 但音色像本人程度下降、后墙乱换 → 不换。

### 09：mathruffian `docs/03`、daexchef `MASTER_BOT_BRIEFING`、wasserman、r34vtraining ×2、README‑only skill
- mathruffian 见结论 5，另：H3 不要与别的 GPU 任务同跑（慢 ~10×）；计时看 `/history` 不看墙钟；SaveVideo 只有 ~3 Mbps → 存 PNG 自编 CRF 12；小于 50 px 的脸用 H3 低强度重画（`face_refine.py`，放大器救不回）；近景背后贴墙不留空地（会走进路人）；soundscape 不写 crowd/chatter（会画进人）；舞蹈武打用白模动作参考 + 首尾帧，≤ 158 帧；Colab G4 ≈ 5090 速度（DMAD 90 帧 42 s vs 47 s）。
- daexchef（PRO 6000）：锁定看法 5 s/0.4 MP → 30 s 用 Seamless Chain 三段 10 s → 只提升 keeper（latent ×2 → RTX VSR），脸糊只重跑一段 8 步无 cache；Larry v4 0.8–1.0（脸塑料从 0.85 起）。与结论 2 冲突处（Larry v4）以 KadoBOT/Anti‑Burn 实测为准。
- wasserman：两台 DGX Spark 的 H3→LTX‑2.5 精修，8 s = 704×384/192 帧，与 4090 无关。r34vtraining：Prompt Compiler 为纯 stdlib 七节点（累计切点、`<d>` 按钮）；Longshot 1.8 的 Face Refine = MTCNN 追踪 + fl2va denoise ≈ 0.3 / shift ≈ 4 + `hold_audio`，预览开着模型放不下时慢 30–40%。README‑only skill（fadeaway/ZzzAloong/penposs/qianye/EVZheng/sjh00）无新数字，只重复 15 s/10–15 s 分段；xingheFF 仍 404。

## 可写进 skill 的规则（只列新增，含来源）

1. 出图与出视频分实例：给 Qwen‑Image 的 ComfyUI **不要**带 `--use-ck-attention`（comfy‑kitchen ≥ 0.2.36 崩图），给 H3 的实例保留（否则慢 2.7×）。（infinite‑creation `stages.js`）
2. 续接链底模/蒸馏组合固定为 REF2VA int8 + lightx2v ref2v turbo 8‑step v1.1；禁用 Larry `turbo_v4_step600_ema` 做续接（6 段纹理 +261%）；Anti‑Burn LoRA 只挂第 2 段起、`LoraLoaderModelOnly` 0.5 起步、不合并进 int8。（KadoBOT long‑chains、Imagineer13 模型卡）
3. 续接帧数只取 39+51k（39/90/141/192），中段插入偏移取 51 的倍数；静帧钉位取 17k；请求非法值会被静默向下吸附，先自己算好。（MultiRef、PrefixStream tests）
4. 不说话的人脸镜头给静音引导音轨；台词中称呼后面不写逗号、句首不写「……」（会停 1 s / 念乱语）；soundscape 不写 crowd/chatter。（mathruffian 03）
5. FL2VA 首尾帧：尾帧与首帧**同机位同构图但必须是不同图**（动作完成后的姿势）；同一张图做首尾 → 100% 静止。没锁尾帧时加 `LOCKED-OFF STATIC CAMERA on a tripod`。（mathruffian 03）
6. 多人镜只给首帧不加 `<Picture>` 身份参考（会多一人）；单人镜加身份参考时写明「仅外观参考，不是要切过去的画面」；写 `Exactly N people`。（mathruffian 03、KadoBOT）
7. 负向词只允许一句具体失败词（如 `NO black letterbox bars`），其余一律改正向；六段式之外不要追加 `constraints:` 第七段。（04/09 共识 + mathruffian/okaypic 实测，否定 TFboy1/h3lite）
8. 提示词机检采用 manju H1–H12：`[Shot 1]` 无时间戳、切点 MM:SS.mmm 递增且 ≤ 15 s、保留度只用四个合法词、retention_analysis 不写 `(Sx)`、`(Sx)` 按首现从 S1 编、说话人首现 ±120 字内有音色词、画外音固定句 `says in an off-screen voiceover … lips remain completely closed`、切镜只用 `the camera/shot cuts to` 五短语。（manju `validate_prompt.py`）
9. 剪辑前每个 H3 take 先 `loudnorm` 到 −16 LUFS，成片 −14 LUFS / −1.5 dBTP；Turbo take 比 20 步响 1.7–4.3 LU，不要凭耳朵混。（okaypic、chiphoton）
10. 单镜内部切镜预算：10 s 段 ≤ 2 镜、12–15 s 段 ≤ 3 镜、每内部镜 ≥ 4 s；超预算先减镜不加形容词；每段只放一个高风险物理事件并写出 起始态→控制输入→世界方向+屏幕方向→阶段→终态。（dramake）
11. 驱动 ComfyUI：每 N 个任务 `POST /free {"unload_models":true,"free_memory":true}`；`/history` 与 `/queue` 连续 3 次都查不到才判丢失；预检 `/system_stats` 4–5 s 超时；H3 不与其它 GPU 任务并行；计时读 `/history` 执行时间。（infinite‑creation、mathruffian）
12. 对白分镜硬约束：中文台词字数 ≤ 时长×5，每镜 ≤ 2 说话人，参考音只给有台词角色且 ≤ 3 段；文案按 35–50 字拆一镜。（infinite‑creation `set_storyboard`、senmanx）
13. 截尾帧续接时段尾写 0.8–1.2 s 的收束保持；转场段用黑场/淡化而非人物尾帧；尾帧占第一张参考图槽位、只在「同场景无转场且动作未完成」时续写。（senmanx、TapCanvas）
14. 角色设定卡防撞脸：每人 3–5 处骨相 + 发型/体型/体态/主色/标志六格，同项目禁复用「鼻梁挺直/黑发束髻/高挑修长」；写族裔、`height_cm + build`、一个跨场景锚点；给 H3 的参考用多张单人图而非一张多格板。（TapCanvas face‑design、okaypic、mathruffian）
15. FlashVSR 2× 用 `--tile_size 256 --tile_overlap 64 --frame_chunk_size 50 --keep_models_on_cpu`（128/24 出网格），完成后 `ffprobe nb_frames` 核帧数并用 `-map 0:v -map 1:a:0` 回灌原音轨；真人近景优先 RTX VSR，不用 SeedVR2/SoL‑Refiner（改脸改嘴）。（h3lite video‑upscale、mathruffian）

## 仍未读

- LightX2V `scripts/minimax_h3_roll`（克隆被 blob 过滤，仓内无此目录）；alisson‑anjos 其它 H3 分支；ostris/Imagination Studio 各 LoRA 模型卡；raylight USP/FSDP 文档。
- T8：`speech.py` 全部 966 行逻辑、Director/Meridian/FreeVideo/Topaz 文档、OPEN_REGENERATE 以外的 90 组工作流；Tessera Streamed Encode/Decode 实现。
- JGRFW `engine/optimizer.py`（153 KB）与主插件 `prompt_optimizer.py`；ethanfel `plan_v2.py`（215 KB）、`PLAN_V2.md`、`QWEN_ENHANCER.md`、Contex‑Loop 其余 docs；LongMedia `DIRECTOR_GUIDE_EN.md` 正文；Continuum 其它 docs。
- LoveRain1997 `01_拍摄技巧总纲.md` 566 条 IF‑THEN 正文（只读了目录）；T8 enhancer 200 种视觉风格正文（只见元数据）；SkyNotSilent `llms-full.txt`、三个 agent skill 正文；unknowlei creative‑director；pytraveler `REF_SYSTEM_PROMPT`（文件名与 04 描述不符未定位）。
- 漫剧老李 style‑bible 其余 9 份、sd‑storyboard‑engine p45；senmanx `3D超燃打斗提示词.txt`（123 KB）、`S级漫剧人物7.15.txt`；dramake 其余 ~15 份 references 与 `evals.json`；TapCanvas `clip-design-and-packet.md` 主体与 `authoring-contract` 后半。
- 新克隆但只读 README/测试：VDN‑24GB 内核、Flow‑Aligned 内部 docs、CLSS 全部、HybridWindows `docs/`、hyukudan 节点源码、FaceRefine‑Accelerated 基准、PTD 质量（作者亦称无人渲染对比）、daexchef 的 HTML 生成器与 `segments.json`、wasserman recipes（DGX‑only）。
- 未验证/不可访问：FastVideo/FastH3 与 Yzmblog/DMAD 原仓（401）、NRDX StyleTransfer LoRA、madebyollin/taeh3、xingheFF NSFW skill（404）、Pika‑H3‑Flex 与 Singularity 模型卡正文、garycaogan 盲评原片。
- 未运行任何生成做实机验证；所有数字沿用作者自报。
