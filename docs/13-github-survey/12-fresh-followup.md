# 13‑12 · 11‑fresh‑repos 未读条目补读（源码级）

> 调研日期 2026‑11‑07。只补 `11-fresh-repos.md` 末尾「未覆盖 / 未读完」列出的文件；仓库在 `scratchpad/survey/fresh/<owner>__<repo>/`。本文只写相对 01–11 与 `skills/minimax-h3-comfyui-short-drama/references/` **新增或矛盾**的内容；重复结论不再写。所有耗时/显存均为作者自报并注明硬件。「裁决」= 与已有结论冲突时的判定与理由。

## 结论（10 行）

1. **面部重绘起始 σ 三方独立收敛到 0.80–0.89**：xentome 面部预设 denoise 0.30（simple 8 步 shift 12 → σ 0.84）、Carasibana FaceRefine denoise 0.40（→ σ 0.89）、fuzzballb ManualSigmas 0.8——skill 的「小脸 σ 0.8 起」可升级为硬规则。
2. **「56 不是合法上下文」只对遮罩前缀（B 系）成立**：Filmworkbench 全部 11 条续接图用 Motion‑Context 钉头 `context_length 56 / audio 18`（5+17k 网格），与 10 簇「AV 前缀只能 39+51k」不冲突——两条规则按机制分开写。
3. **同场景跨段不只是「换景别」，而是「跳两级、禁全景开」**：egguy886 总导演手册把「下一段首镜开全景或 lock1 锁位」列为 `shot_lint` 硬门禁，首镜必须 CU/ECU/MCU 或动作冲击 MS（Cut on Action / Gaze / Barrier Match / Impact Smash 四式）。
4. **自动重出要分类**：egguy886 量产数据——切点类问题重出改善率只有 29%，片尾抖动重出 4 次 0 次变好；只对「技术参数 / 首帧接不上 / 自带字幕」自动换种子重出，其余只标记。fuzzballb 的硬切检测阈值 30（64×36 灰度帧差）与 Whisper 匹配 0.8 可直接复用。
5. **H3 会照抄干净音色样本的「录音棚声」**：fuzzballb 用后期 150–6500 Hz 带限 + 23/41/67 ms 早反射 + 棕噪 −18 LUFS 把对白拉回「现场」；写规则「音色样本干净，但成片对白必须后期加房间声」。
6. **manju‑studio「FL2VA 通道不出音频」是误判**：`MiniMaxH3ImageToVideo` 输出的是 AV 嵌套 latent（pongjoo 正是用它建「目标音视频潜空间」），作者只接了 `VAEDecode→SaveImage`；与其 BUGS #16/#20 同根——FL2VA 链必须接 `VAEDecodeAudio`。
7. **稀疏注意力的两份相反证词可以调和**：Filmworkbench（5090）两采都开核心 `BlockSparseAttention sla keep 10% start_percent 0.2 min_tokens 12288 sink exact_kv_and_rows`，fuzzballb（3090）`H3SLAAttention 0.7 稀疏、dense_steps 1、int8 QK` 让窗框倾斜——差别在前 20% 步是否稠密与 QK 精度。4090 维持「精修不开稀疏」，若必须开，照 FWB 参数且同 seed A/B。
8. **空间局部重绘三家实现一致**：遮罩必须在像素域做 expand 6 + feather 6 后贴回，latent 侧只能是 32 px 方块（2×2 patch 最大池化，无 0.5 阈值，Code2Collapse 核心源码佐证）；LanPaint 去除物用硬 0/1 像素遮罩交给 LanPaint 自己映射，`NumSteps 2 / Lambda 5 / StepSize 0.2 / Image First / blend_overlap 11`。
9. **像素域超分与 TikTok 发布实测**：6 s 片 RTX VSR Ultra 14 s、FlashVSR tiny 220 s / full 335 s，三者比 Lanczos 只「略清楚」，压到 2.5 Mbps 后差别更小——egguy886 结论「默认 Lanczos 不超分」；TikTok 黑边判定「边缘连续近黑 >20 px 且 >5 s」，电影暗调镜头会误判，修法把黑位抬到 TV 36。
10. 仍是空白：没有人实测 4090 上 Filmworkbench 的 56 帧 Motion‑Context + DMAD 两采链；Koongrizzly 的 39 帧遮罩续接**只锁视频、音频独立重生**，与 PrefixStream 的 AV 同锁相反，谁更好无对照。

---

## 一、fuzzballb/comfyui-h3-long-video · `story_kit/run_story.py` + `check_cuts.py`

- **硬切检测**（`check_cuts.py`）：`scale=64:36,format=gray,tblend=difference,signalstats` 取 YAVG，**> 30 判切**（`--cut`）；作者注明快 POV / 跟拍的运动值 12–25 不是切。联络表 `fps=1,scale=400,tile=5x2`。
- **gen 闭环**：每段渲染后 ① 无硬切 ② 有台词段 Whisper（small，`--language en`）转写与剧本 `difflib` 词级比 ≥ **0.8**（0–20 数字转英文词）③ 无台词段若 Whisper `no_speech_prob < 0.5` 且 ≥ 2 词则判「擅自说话」（过滤 "thanks for watching / subscribe / music / applause" 幻觉）；失败换 seed 最多 **3 次**，全败保留末次并**跳过依赖它的后续续接段直到下一个 new_shot**。
- **lint 规则（实跑踩坑）**：静止句与运镜句同在 → 招致切镜；一段 >1 次 `turn/spin/pivot` → H3 重画背景并跳回场景参考图构图；续接段 ≥ 2 个 `then` → 多切；`wink / blow a kiss / raise an eyebrow / stick out tongue / lick` → 切到脸特写；无台词段出现 says/counts/shouts 等说话动词 → 编乱码词；无台词段必须写 "Nobody speaks, there are no words at all" 否则填充咕哝；续接只能描述**上段末帧画面内**的东西，点名画外（"toward the staircase"）会切过去。
- **参考图**：续接段把 Picture 1 从脸部紧裁换成人物板（`FACE_CONT`）——紧裁脸图让 H3 切脸特写；道具表只在提示词含该 token 的段挂入。LoRA 触发词（"DY" / "camera motion," / "bullet-time"）在有台词段会被念出（"D.Y."）→ 删词保留 LoRA。
- **对白两种模式**：`h3` 模式台词写成 `Sam says in the voice from <Audio 1>, friendly, his lips moving clearly: "…"` 多人加 "They speak naturally… Those are the only words."，单人加 "After that nobody says anything else."（不写则后半段乱说）；`H3LongVideoReferenceAudios max_seconds 10`。`tts` 模式 ChatterBox 出轨后用 `MiniMaxH3SongMaskedAVContext` 冻结（LEAD 0.5 s，句间 GAP 0.35 s，续接段音轨前缀 = 上段最后 39 帧 + 0.3 s）——词准但表演平、无其它声音。
- **音色样本副作用**：H3 复制样本的干近录音棚声 → `location_sound.py` 后期：`highpass 150 / lowpass 6500 / −2 dB@2.5 kHz`，`aecho 23|41|67 ms`（0.22），棕噪 0.02（60–900 Hz），`loudnorm I=-18`。
- **模板实参**（`generate_api.json`）：hybrid b25‑49 int8 + `qwen3vl_32b int8_convrot` CLIP + PlagueKind `PK_MiniMaxH3Combined 1152×864 match vlm_resolution 384`；`fl2v_turbo_8step_v1.0`（非 768p 版）**0.95 + shift 12/3**、res_multistep/simple，非 Turbo 13 步；`MiniMaxLowVRAMAttention head_chunks 4` + `MiniMaxChunkFeedForward 2/4096` + `H3AdaLNLoRAFix port`；SLA 节点默认关。帧数公式 `max(5,round(s*24))` 吸附 17k+5。超分模板：`MMH3TemporalSplit 102/17/anchor 0.999`、`SpatialSplit tile 736 overlap 128 fade 32 grid 3×1 token_budget 70000`、LBH 3D bf16、FILM ×2、RCAS 0.3、CRF 14。
- **裁决**：v1.0 非 768p LoRA 配 12/3 与 skill 一致；但他在 ~1 MP 用 544p 期 LoRA 且无 A/B，skill「768p 用 `_768p_` 版」不变。道具表提示词写 "in BOTH views" 否则第二视角丢部件；道具文字（"URGENT"）可读。

## 二、pongjoo/ComfyUI-PJ-SegmentSampler · `pj_h3_context.py` + `pj_h3_edit_prepare.py` + `DEV_LOG`

- **逐段重建条件**（`_encode_segment_conditions`）：每窗口按 `17n+5` 对齐（`bounds[0] % 5 == 0`，窗口 token ≡ 2 mod 5），调用原生 `MiniMaxH3ReferenceToVideo.execute` 重编码：图片逐张按 `match/max` 编码；参考视频在「原视频编辑」模式按**本窗口时间段切片** `[frame_start:end]`，配套音轨按自身采样率同步切片；「素材参考」模式整段向下对齐；原生参考节点会把参考截到目标长度，所以 `length = max(窗口帧数, 各参考视频帧数)`。
- **运动引导**：上段尾部 latent 必须是 **2+5k token（5/22/39 帧）且相位对齐**，逐 token 转成 `minimax_keyframes`（`resolved_frame_index = frames_for_tokens(i)`）；上游首尾/引导 latent 分辨率与当前窗口不一致直接报错（跨分辨率二采必须重建引导）。
- **条件集中准备**：`unload_all_models → 逐窗编码存 CPU .pt → 再卸载 → 连续采样`；只编码「失效后缀」窗口。
- **空间遮罩**（`PJ_H3EditPrepare`）：遮罩尺寸 = latent×16 像素、`[帧数,H,W]` 或单帧；**32×32 最大池化 → 每个原生时间跨度取并集 → 2×2 复制回 latent 网格**；与已有 noise_mask 相乘；音频遮罩原样（或全 1）；原视频 VAE 编码结果替换目标视频 latent。
- **DEV_LOG 新数字**：规划器 6 s 段 = 42 token/141 帧；目标重叠 0 或 0.5 s → 5 帧、1.5 s → 39 帧；秒数只作参考、后端取最近合法值；322 帧向下对齐 311、原声同步裁到 311/24 s；SAM 3.1 换鞋流一采 0.4 MP → 二采 ~1 MP 3 步 denoise 0.3 起试；v1.0 前 BF16 余弦权重可舍入为 0 导致融合退回原输入（已改 FP32 分块，只对真实交集加权）；「潜空间固定 ≠ 解码像素固定」反复强调。
- **价值**：这是唯一把「参考视频按窗口切片」写进源码的实现——视频编辑式 Ref2VA 分段时，参考视频必须与目标窗口同时间段，否则条件错位。

## 三、egguy886/h3-drama-kit · playbook 06 / 08 / 14 / 15×2 + `comfy_run.py` + `axis_lint.py`

- **06 AutoDL 量产数字**：768p 竖 15 s 单段中位 13 min、最长 18；并发 4 一晚 ≈85 段；重出率 7%；每段下载后自动质检只对**技术参数 / 首帧接不上 / 自带字幕**重出，**切点类重出改善率 29%、片尾抖动重出 4 次 0 次变好 → 只标记不重出**；先锋 2 段合格才放量；HARD_CUT 段可并行、TAIL_RELAY 必须等上段 accept。RunningHub 只认 6 张参考图，5 图 + 2 音频时音频被丢。
- **08 拼接常数**（`assemble_episode.py`）：段首裁 0.08 s；对白段尾只留到末词 +1.0 s、末镜 ≥2.2 s；出点 ≥ 末词 +0.18 s，下一段入点前有词用 J‑cut；集尾切黑 ≥ 末词 +0.6 s（此前全剧 16 处剪掉半句）；L‑cut 上段声音多留 0.25 s，段间音频 120 ms 交叉淡化；分场景环境声底 −32～−48 dB 只填静默缺口（13 处→1 处）；同场接色向组内中位数拉 70%。
- **08 声线/交付**：seed‑vc 基准取**用户确认的 H3 原声 ≥6 s**而非 TTS 样音，校验静音污染（−60 dB）、电平差 ≤1.5 dB；字幕文字取锁定原文、只借 Whisper 词级时间，极短单句并入下一条；两遍 loudnorm −14 LUFS / LRA 11 / ≤−1 dBTP。**超分裁决：默认不做，用 Lanczos**（6 s 片 RTX VSR Ultra 14 s、FlashVSR tiny ≈220 s / full ≈335 s，放大裁切看略清楚、2.5 Mbps 后差别更小；FlashVSR 60 集 ¥240–360 > 出片费）。
- **TikTok**：黑边判定「边缘连续黑像素 >20 px 且 >5 s」，暗调镜头误判（55/60 集）→ `tiktok_edge.py fix` 把 Y' 抬到 **TV 36**、切黑前 0.4 s 淡出、片尾保持纯黑；代理指标 ≥4 s 危险；受限集 >10% 影响整部发布；血腥用 `blood_mosaic.py` 去色压暗（红光场景要手工框）。
- **14 视觉宪法**：`style_lock.json` 锁 7 维——全剧 ≤3 支定焦（24/40/85 等）、光比（6:1 强逆光）、分区色盘「1 主色相 75% + 1 重点色 15–25%」、天气必须作用于身体、机位权力、表演寄存器、反例白名单；地平线 1/8 或 7/8 禁五五分；前景失焦遮挡 10–15%；形容词替换表（`cinematic lighting` → `6:1 hard amber rim light from upper-left…`）。**裁决**：其「反例」是否定句列表，只作作者侧 lint 白名单，不进 H3 提示词。
- **15 总导演手册**：首集 12–15 段 / 3:00–3:45，常规集 9–14 段；**一段一主空间**，跨空间必拍 Arrival Bridge 过渡段；同场景下一段**首镜禁全景 / lock1 锁位**，必须跳两级景别开 CU/ECU/MCU/MS，四式桥接：Cut on Action+ECU、Cut on Gaze+MCU、Barrier Match Cut（可用 `edit.json trim_in` 裁掉废头）、Impact Smash Cut；状态单步递进台账（不许跳过物理过程写结果态）；在场人物守恒；命名运镜句式（Crane Down / Tilt Up Reveal / Low Angle Hero / Rack Focus ≥2.4 s / Eyes‑In / Aerial Pullback）；配乐 ducking −8 dB、转场叠低频重音桥。
- **15b 多种子经验**：3 seed + 每候选 8 帧候选图人选；3 seed 同一错才改分镜；**长独白用四分之三正面，侧脸只给 ≤2 s**（侧脸近景说到后半变成另一个人）；空间写成几何事实句并每镜重复；状态变体（戴/不戴眼镜）独立参考 ID、吊坠道具图每段都带、不必要的小物件直接从剧本取消；**Dolly Zoom 单独出 6–7 s 单镜再裁 3.2 s 替入**（15 s 多镜内做必败，尺寸变 2.0–2.8×），脸高比最稳 1.11，背景需灯串/人群纹理；Codex 出参考图串行（并行串脸）、`--ref` 会抄衣服。
- **comfy_run.py**：U24 一采 **0.4 MP 上限**（更高失败）× 二采 1.5；提交前先等队列空再 `/free`（别的任务在跑时清显存会打断）；参考图按 sha256 缓存只传一次；重出必须换 seed；轮询 3 s——**裁决**：那是 zealman 面板的 `/api/workflow/result` 代理，不是 ComfyUI `/history`，直连 ComfyUI 仍按 skill ≥20 s。`axis_lint.py`：正反打里两人 `off-camera at frame-left/right` 同向 = 越轴；跑步镜必须写方向（全剧约定画左→画右）。

## 四、Filmworkbench-Starter · K2/K4/K6–K9/MARKET + `AUTONOMOUS_FILM.md` + 图参数

- **图参数全集**（44 图）：首段 S1 `AddGuide frame_idx 0` + DMAD 1.0 + 8 步 er_sde/beta 864×480，帧数 192/240/277/345；续接段 S1 `MiniMaxH3MotionContext context_length **56** / audio 18` + `ref2v_turbo_8step_v1.0_768p`（不是 DMAD）396 帧（56 重叠 + 340 新）；S2 一律 `MinimaxH3LatentUpscaler3D mode megapixels 2.0 align 32 temporal_chunking on force_unload` → DMAD 2 步 er_sde/**linear_quadratic denoise 0.4** 1952×1088；两采都挂 `ModelAttentionBackend comfy kitchen` + `BlockSparseAttention selection sla keep_percent 10 start_percent 0.2 end 1.0 min_tokens 12288 extra_tokens 256 sink_conditioning exact_kv_and_rows`。
- **End guide**：K6 锁定外景、K7 入画、K9 穿门用 `AddGuide frame_idx -1` 钉**终态图**（「已知角色进空镜」= 空景首帧 + 终态尾帧 + 身份图）。
- **裁决 ①（56 vs 39+51k）**：10 簇「AV 续接上下文只能 39+51k」是遮罩前缀（B 系）的音频对齐约束；Motion‑Context 钉头（A 系）走 5+17k 网格且音频单独 `audio_context_length`，56 合法。skill 两条按机制分写。**裁决 ②（BlockSparse）**：见结论 7。**裁决 ③（否定句）**：FWB 提示词大量用 "no pan, no tilt, no dolly, no zoom" / "No new cups or other objects appear" / "he does not enter again"，但这是人工审片后的「被接受 take」集，无 A/B，不构成推翻 skill 铁律的证据；可借其正向写法 "the blue porthole and door remain at their exact original pixel positions"。
- **配方要点**：K2 反打要给「对面房间视图」参考并**显式交换两人画面左右**再回全景；K4 对白先入（prelap）——**音频参考会导致重复词**，要听完整段；K6 舱内外——舱内用连续全景避免内部切镜「发明多出的行星」，外景窗保持远/反光；K7 空镜入画——"At 00:01.000, immediately after the initial empty one-second view the man walks into the shot from offscreen beyond the near LEFT edge"；K8 湖怪——先空湖 + 生物比例参考，露头颈背后从「已出水状态」续；K9 外开门——拉、退、让、跟四步，从门几何正确的 take 续。
- **MARKET（47.67 s 四段）**：场景参考用**罗盘命名的四向空景**（north/south/east/west）+ 一张有人的航拍开场引导；`retention_analysis` 写**物权台账**（"After the handover the red apple is held by Lena's RIGHT hand and the ivory cloth is empty"）；续接段 summary 以 `[reference generation + temporal continuation] Continue the supplied AV motion context` 开头并写 "During the first two seconds everything continues exactly as in the preceding frames"；`<Audio N> supplies only the voice timbre of <Subject N>, not its recorded words`；已知缺陷：背景路人/篮子变、脚步声比动作长。
- **AUTONOMOUS 审片循环**：每 take 的 `assessment.json` 绑定 take 指纹 + 视频哈希，缺核心观察（动作/身份/连续性/运动/音频/故事）不能 accept；**静帧不能证明运动与台词正确**，必须看完整视频听音频；预算 3 take/阶段、16 次渲染，到顶报告而不是加预算；无 `--auto-accept`。

## 五、Code2Collapse/ComfyUI-MiniMax-H3-Suite · `WORKLOG` + `sampling_guard.py`

- **WORKLOG（2026‑08‑28 生成）**：247 测试通过但 **0 个节点在真实 ComfyUI 注册**——包目录叫 `utils/`、`nodes/`，与 ComfyUI 顶层 `utils` 包 / `nodes.py` 同名，`sys.modules` 已被占用 → 所有 import 静默失败；前端 4 个 widget 读 `onExecuted` 却从未发 `ui=` payload（只有 `NodeOutput.ui` 到浏览器）。**诊断规则**：自定义节点包启动后看日志的注册数，不信其测试套件。
- **核心源码佐证**（作者引用 `model_base.py` / `model.py`）：软遮罩量化 `ceil(m·256)/256` 后**最大池化到 2×2 patch，无 0.5 阈值**，粒度 32 px，细羽化只能在像素域；核心按 token 行独立 timestep，**软 noise_mask 等价于逐 token 去噪曲线**（支撑 gradient mask 规则）；音频 VAE 直接作用于 32 kHz 波形而非 mel；`video_latent_t(22) == 7`。
- **守卫矩阵**（`sampling_guard.py`）：Spectrum × BlockCacheT8、EasyCache × T8、EasyCache × LazyCache、FirstBlockCache × {T8, EasyCache, LazyCache, Spectrum} 互斥；两个块级缓存不报错但**悄悄出错图**；保护块 = {0, 最后一块, **10/20/30/40（Fun‑ControlNet‑Union 注入块）**} 与 `final_layer / norm_out / proj_out / audio_proj_out`。→ 新规则：挂 FunControl 时不要开任何跳块/缓存。
- **过时**：「Union 无 ComfyUI 加载路径」写于 8 月，核心 `MiniMaxH3FunControlNetApply` 已于 10 月合入；DriftQC（RAFT‑small）对 1 px 位移低报 0.18 px，阈值 ≥0.25 px——仅供自建漂移门参考。评级维持观望。

## 六、nvmax/VideoBuilderH3 · `minimax_keyframes.mjs` / `refmod_quick_add.mjs`（+ `minimax_h3.mjs` 常量）

- 两个 .mjs 是纯 UI（每场景 first/last 帧卡片、FLF 过渡风格、RefMod 库按 folder→card 类型映射：identity→character、clothing_men/women→outfit、background→location 卡、其余→subject 卡），无 H3 参数。
- **有用常量**在 `minimax_h3.mjs`：2‑Pass 默认 pass1 0.4 MP 20 步 euler/beta → pass2 **2 MP 1 步 `sa_solver`/simple denoise 0.2**；3‑Pass 再加 5 步 euler/beta denoise 0.2；TE‑Speed 只允许 pass1。**按显存的瓦片预设**：8 GB tile 0.2 MP / chunk 51 帧 / overlap 128；12 GB 0.3/85/128；16 GB 0.43/119/128；**24 GB 0.65 MP / 153 帧 / 160 px**（32 GB 归并到 24 GB）；瓦片网格按「面积超目标罚 2×」自动选。
- 续接只剩 `latent_continuation_masked`（standard / exact‑last‑frame 模式已退役），上下文只能 39/90/141/192；首帧角色影响分 "face+hair only" / "full character"；场景图三档：精确首帧 / 仅环境灵感（只给 LLM）/ 环境+构图灵感。分辨率预设按长边：1K 1024×576、2K 1920×1088、1440p 2560×1440、4K 3840×2176。
- 评级维持观望；瓦片预设可作 4090 UltimateUpscale 起点（与 06 簇 tile 576–768 / overlap 128 / chunk 136–170 同量级）。

## 七、Koongrizzly/MiniMax_H3_Standalone_app · Timeline Director

- `runtime/timeline_masked_context.py`：把上段 `.h3latent.pt` sidecar 的最后 **12 个视频 token（39 帧）**复制进新 latent 开头并把视频 noise_mask 置 0；**音频不锁、独立重生**（与 PrefixStream/fuzzballb 的 AV 同锁相反）；`overlap != 39` 直接拒绝；分辨率不一致拒绝；输出必须精确裁掉 39 帧。sidecar 缺失时回退「解码帧重编码」记忆，可选「帧记忆 + latent 记忆合并」。
- 时间线块默认 **243 帧**（吸附到允许帧值）；四种编辑模式：`bridge_both`（续上段 + 以下一块首帧为终帧）、`continue_previous`、`anchor_next`（不续上段、只钉下一块首帧——FL2VA 式补桥）、`standalone`；**带参考图时禁用 bridge/continue**（续接与 Ref 互斥）；「Carry audio memory」独立开关。
- 调度器：检测到 EMA 加速 LoRA 自动选 **beta**；Spectrum 在 4 步 Turbo 只预测一个中间步，README 要求 ≥6 步。
- 评级维持观望（独立 app，不进 ComfyUI）；可借「anchor_next = 用下一段首帧补桥」思路。

## 八、ArcSeekerX/Xpark-Media-Foundry-Agent · `app/qc.py`

- 抽 **3 帧（5% / 50% / 95%）**缩到 512 宽 JPEG q4，经 OpenAI 兼容端点喂 `gemma3`（temperature 0.2，max_tokens 400），要求 JSON `{verdict: pass|warn|fail, issues[], note}`；检查项只有「清晰/畸变/肢体、乱码文字/水印/logo、可用否」；解析失败重试一次否则判 `warn`。
- **局限**：3 帧判不了运动、口型、台词；与 skill 四维评分（ASR 对照 × 相似度 × 冻结 × 清晰度）相比只覆盖第 4 维。→ 规则：VLM 抽帧只作「崩坏/水印/乱码」门，动作与台词走 ffmpeg 帧差 + Whisper。

## 九、wbliang168/manju-studio · `gen_fl2v.py` + `gen_zimage_keys.py` + `manju_skills/drama_video.py`

- **gen_fl2v.py**：打斗/动作镜走 FL2VA（`fl2va_pruned-Q4_K.gguf` + `fl2v_turbo_4step_v1.0_768p` + `MiniMaxH3TurboLoRA low_vram` + `MiniMaxH3TurboSampler` 4 步 simple，576×1024），理由「单图只有起点，模型自由演化成慢动作/动作做不完；给终点位移才有保证」。提示词：官方对齐行 + "Between these two frames the motion is continuous and physically connected, not a cut" + "Camera, framing, clothing and background stay identical between the two frames; only the body pose and the weapon position change"。
- **裁决（误判）**：作者称该通道「不生成音频」因节点无 `audio_vae` 入口——实际 `MiniMaxH3ImageToVideo` 输出 AV 嵌套 latent（pongjoo 用它建目标 AV latent），工作流只接 `VAEDecode→SaveImage` 没解音频；FL2VA 有音频，接 `VAEDecodeAudio` 即可。
- **gen_zimage_keys.py**：Z‑Image‑Turbo int8 8 步 cfg 1 euler/simple 出关键帧，尺寸比 H3 渲染大约 1/3（576×1024 → 768×1360）留细节；img2img 用定妆照锁脸：**denoise 0.45–0.55 保五官构图、0.60–0.70 换场景/景别仍同脸、>0.8 洗掉**；`ImageScale crop` 只能 `disabled|center`（写 `crop` → /prompt 400 整批挂）。
- **drama_video.py**：与 H3 无关——PIL 对漫画面板做 pan_zoom / breathe / shake / fade 的 Ken Burns 帧序列（1080 宽，24 fps，ffmpeg crf 18），可作漫剧「静态格子」兜底。

## 十、xentome/EDITS-WITH-AI · `app/retocar.py`

- **三模式**：`cambiar` 重绘（fuerza 0.40–1.0 = denoise，默认 MP **0.18**，范围 0.05–1.0）、`detallar` 视频到视频精修（denoise 0.10–0.80，方形画布 384–1024）、`quitar` LanPaint 去除（1–4 轮）；全部跑 **Pika H3 Flex 6 步 lcm**，部分去噪用 `sigmas_pika(d)`：先算 simple‑8 步 shift 12 下该 denoise 的起始 σ（`t = 8/int(8/d)`，`σ = 12t/(1+11t)`），再接 Pika 节点中低于它的 sigma。
- **面部预设**：遮罩 `face` + 脸照 + **denoise 0.30（→ σ 0.84）/ 768 画布**，裁切 ×2.5 方形 `padding flexible`，无 latent 遮罩（整裁切视频到视频，表情/视线来自原片），`ColorMatch` 回配，贴回 feather 24、expand 8；「固定裁切」模式 ×1.6 单一静止框避免头部与身体节奏不一致。
- **遮罩工艺**：贴回用 `NKDMaskOps`（无 VAE）expand 6 + feather 6（±6 px 盒模糊，先扩再糊以免糊出未盖区）；latent 侧遮罩 32 px 方块不可避免；LanPaint 用 `ThresholdMask 0.5` 硬像素遮罩交给 `LanPaint_SamplerCustomAdvanced`（`NumSteps 2`（作者 5，12 GB 太慢）、`Lambda 5.0`、`StepSize 0.2`、`PromptMode Image First`）自己映射，贴回 `LanPaint_MaskBlend blend_overlap 11`——1 轮硬遮罩留菱形边框，像素硬遮罩 + 软贴回才干净。
- **实跑教训**：段内部按 17k+5 向上取整，**遮罩提前结束会让原画面在末帧重现**；SAM `face` 漏护目镜、抓屏幕里的脸；**对重绘结果再重绘会累积损伤，回原片重做**；LLM 写 inpaint 句：一句 ≤30 词、写「这一帧里有什么 + 这一帧的光向色温」、不提相机/姿势/运动、无否定；3060 12 GB 上 5 s 去除 ≈10 min。
- **Extend 页**：重叠 39 帧「唯一在音频网格上精确的值」，末帧总被加为参考；从保存 latent 续无损、从 mp4 续接缝轻微色损；末尾冻结则续接继续冻结；链式延长漂色漂身份，加项目参考图能减缓。

---

## 可写进 skill 的规则（只写新的）

1. 小脸 / 面部重绘起始 σ 固定 **0.80–0.89**（BasicScheduler simple 8 步 shift 12 的 denoise 0.30–0.40 即此区间）；低于 0.6 保留错脸型（xentome / Carasibana / fuzzballb 三方一致）。
2. 续接上下文长度按机制分写：**Motion‑Context 钉头取 5+17k（22/39/56），音频单独 `audio_context_length 18`**；**遮罩 AV 前缀取 39+51k（39/90/141/192）**——56 只对前者合法（Filmworkbench 图参数 vs 10 簇）。
3. 同场景下一段**首镜禁全景、禁 lock1 锁位**，跳两级景别开 CU/ECU/MCU 或动作冲击 MS，并写明桥接类型（Cut on Action / Gaze / Barrier Match / Impact Smash）；跨空间必加一段「物理到达」过渡（egguy886 15）。
4. 自动质检只对「技术参数 / 首帧接不上 / 画面自带字幕」换 seed 重出；切点偏移、片尾抖动只标记不重出（重出改善率 29%、0/4）（egguy886 06）。
5. 硬切检测：64×36 灰度 `tblend=difference` 的 YAVG **> 30** 判切，12–25 是运动不是切；无台词段 Whisper `no_speech_prob < 0.5` 且 ≥ 2 词判「擅自说话」并换 seed（fuzzballb）。
6. 续接链某段 N 次全败时**保留末次并跳过依赖它的后续段直到下一个硬切**，不要在坏段上继续续（fuzzballb run_story）。
7. 提示词 lint 追加：一段 ≤1 次 `turn/spin`；续接段 ≤1 个 `then`；禁 wink / blow a kiss / raise eyebrow / lick（会切脸特写）；无台词段必须写 "Nobody speaks, there are no words at all"；LoRA 触发词不进有台词段；续接只描述上段末帧画面内之物（fuzzballb）。
8. 多人对白段末尾加 "They speak naturally… **Those are the only words.**"，单人加 "After that nobody says anything else."；音色样本干净但成片对白要后期加房间声（150–6500 Hz 带限、23/41/67 ms 早反射、−18 LUFS）（fuzzballb）。
9. 长独白镜用**四分之三正面**，侧脸近景 ≤2 s；Dolly Zoom 单独出 6–7 s 单镜再裁 3.2 s 替入，不在 15 s 多镜段内做（egguy886 15b）。
10. 拼接常数：段首裁 0.08 s；出点 ≥ 末词 +0.18 s（入点前有词用 J‑cut）；集尾切黑 ≥ 末词 +0.6 s；L‑cut 0.25 s；段间音频 120 ms 交叉；环境声底 −32～−48 dB 只填缺口；同场接色向组内中位数拉 70%（egguy886 08）。
11. 声线统一基准取**用户确认的 H3 原声 ≥6 s**，不用 TTS 样音；校验静音污染 −60 dB、电平差 ≤1.5 dB（egguy886 08）。
12. 像素超分默认不做、用 Lanczos 到交付尺寸；真要做选 RTX VSR（6 s 片 14 s）而非 FlashVSR（220–335 s），2.5 Mbps 平台压缩后差别可忽略（egguy886 08）。
13. 竖屏 TikTok 交付前把黑位抬到 **TV 36**（切黑前 0.4 s 淡出、片尾保持纯黑），边缘连续近黑 ≥4 s 即危险（平台判定 >20 px 且 >5 s）（egguy886 tiktok_edge）。
14. 视频编辑式分段 Ref2VA 时，参考视频与配套音轨必须**按本窗口时间段切片**后再编码；运动引导 latent 必须是 2+5k token 且与当前分辨率一致，否则重建引导（pongjoo pj_h3_context）。
15. 空间局部重绘：latent 遮罩只能是 32 px 方块（2×2 patch 最大池化、无 0.5 阈值），羽化只在像素域做（expand 6 → feather 6 贴回；面部 feather 24）；LanPaint 去除给硬 0/1 像素遮罩 + `NumSteps 2 / Lambda 5 / StepSize 0.2 / Image First / blend_overlap 11`；遮罩要覆盖到段末，不要对重绘结果再重绘（xentome / pongjoo / Code2Collapse）。
16. 挂 Fun‑ControlNet 时不开任何跳块 / 缓存加速：Union 注入块 0/10/20/30/40 与 FinalLayer 必须原生；两个块级缓存同挂不报错但静默出错图（Code2Collapse sampling_guard）。
17. 「已知角色进空镜 / 回到已改变状态」用 `AddGuide frame_idx 0` 钉空景首帧 + `AddGuide frame_idx -1` 钉终态图 + 身份参考；写 "At 00:01.000, immediately after the initial empty one-second view … walks into the shot from offscreen beyond the near LEFT edge"；`retention_analysis` 写物权台账（谁的哪只手拿着、原位已空）（Filmworkbench K7/K3/MARKET）。
18. 对白先入（prelap）段的音频参考会导致**重复词**，验收必须听完整段；场景参考用罗盘命名的四向空景（north/south/east/west）而不是一张母版（Filmworkbench K4/MARKET）。
19. FL2VA 链必须接 `VAEDecodeAudio`——`MiniMaxH3ImageToVideo` 输出 AV latent，只接 `VAEDecode` 会「以为没有音频」；动作镜用首尾帧时写 "Between these two frames the motion is continuous and physically connected, not a cut"（manju‑studio，裁决为误判后的正确写法）。
20. VLM 抽帧（3 帧 5%/50%/95%）只作「崩坏 / 水印 / 乱码」门，不替代帧差动作量与 Whisper 台词检查；agent 自动审片时每个 take 的评估要绑定视频哈希，静帧不足以 accept 有运动或台词的镜头（ArcSeekerX / Filmworkbench AUTONOMOUS）。

---

## 仍未读

- Filmworkbench `film.py` 的阶段/预算实现与 `graphs/inventory.json` 依赖图；EDIT_NOTES 之外的「Studio Memory」实验变体。
- Koongrizzly `helpers/minimax_h3_gui.py`（7k+ 行）中「解码帧重编码记忆」的帧窗与 Spectrum 绑定细节；BeatSyncFX 与 H3 无关未读。
- nvmax Rust 侧 `crates/h3-core/src/timeline.rs` 的 17k+5 吸附与 `minimax/tile_plan.py`（仓库未含 Python 侧）。
- egguy886 playbook 07 / 11 / 12 / 13 与 `qc_lib.py`、`seg_qc.py`、`motion_check.py` 源码阈值（11 簇已据 README 摘录，未逐行核）。
- xentome `app/generar.py` 全文（只读了 `sigmas_pika` / `poner_pika`）与 `plantillas/retocar.api.json` 节点图。
- Code2Collapse 其余 400 文件（director / drift_qc / color_qc）。
