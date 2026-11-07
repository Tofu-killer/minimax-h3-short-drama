# 13‑02 · 长视频 / 片段续接 / 多段无缝衔接类 ComfyUI 节点（源码级精读）

> 调研日期 2026‑11‑07。方法：浅克隆 19 个仓库，逐个打开 nodes 源码看 INPUT_TYPES、常量、latent 拼接方式、是否 monkey‑patch ComfyUI 核心；示例工作流用 `analyze.py` 解析参数。本文只补 docs/12 §5/§8 未写的内容。用户环境：Win11 + RTX 4090 24 GB + ComfyUI 0.37.2（已含 PR #15375 原生 AV 去噪遮罩与 PR #15439 任意位置 AddGuide）。

## 本簇结论（10 行）

1. **H3 续接只有两种底层机制**：A「latent 尾部作关键帧条件」（Motion‑Context 系：MC / tritant / Continuum / LongMedia / Multishot context_pin / WhaleTrans direct guide）和 B「latent 尾部直接复制进目标开头 + 原生 noise_mask 冻结」（Herrgott v1.4 / PrefixStream / MultiRef masked / T8 Plan B / AICG3D hard_av）。两者都要求相邻段同分辨率、同模型、同 shift，且都把重叠帧算进本段渲染预算。
2. **立即采用**：`NikoDemon80/ComfyUI-H3-Motion-Context` 0.7.1（不改核心、启动自检、context 22 / audio 18、附 Join Match / Refine Blend 抗漂移）作为 Ref2VA 连续镜头的续接主方案；`knoic/ComfyUI-MiniMaxH3-PrefixStream`（MIT、2026‑11‑07 仍在更新、纯原生遮罩、像素空间裁切、素材箱分支抽卡）作为 B 路线备选。
3. **试用**：`tritant/ComfyUI_MiniMax_H3_Extender`（UI 最省事，但会 monkey‑patch `MiniMaxH3.extra_conds`，默认 4 步）、`HerrgottMargott`（FL2VA + Last Frame「画质重置」路线最完整，但 8 月后停更且装 PackedLayout wrapper）、`JGRFW/comfyui-AICG3D`（中文短剧工作台，默认 context 5 帧 + 曝光锁 ±0.04）。
4. **观望**：Continuum（92k 行、流程极重、Issue #13 锐化漂移未解）、LongMedia（50k 行、全局 monkey‑patch、面向 16 GB 卡）、MultiRef（先驱但 9 月停更、依赖 SolAttn_triton/MAINodes）、h3‑relay（只验 Linux、要 comfy‑kitchen 0.2.33 + 非主线 VSA 提交）、Multishot（context_pin 只兼容 Motion‑Context ≤0.3.1）、T8 Long Video（全部 EXP、文档满是「未验收」）、Smite79（禁止再分发许可、单节点黑盒）、Zzz1phyrf（口播/MV 向，无 latent 连续）。
5. **别碰**：bt420000 MultiGPU（双卡引擎，与单 4090 无关，且用跨卡预测器换速度）、ptmaster ConcatAVLatent（62 行，被 LTX ConcatAVLatent / T8 Source AV Prepare 取代）、Shrek3 MusicVideo（依赖 Multishot 旧链）。pxl‑pshr Loop 做循环不做续接，但其 4090 实测时间和「首帧锚点让曝光漂移 35→50」的结论值得记。
6. **短剧实际上大多是硬切**：所有作者都承认链越长越漂（亮度 ~1.02–1.055/段、纹理 +13%/接、音频高频每段衰减）。30–60 s 短剧应先用「每镜独立 Ref2VA + 同一组参考图 + 音色锚」硬切，只在单镜头必须 >15 s 时才上续接，且**一条连续链不超过 4 段**（Multishot 实测阈值）。
7. 每段推荐长度：5 s（124 帧）起步，8 s（192 帧）上限；重叠 22 帧（0.92 s，视频 7 latent / 音频 37 tick）是 MC 系共识，39 帧（1.625 s，12/65，视频与音频网格同时整除）是遮罩系共识。
8. Turbo 兼容：所有包都能跑 8 步 Turbo，但 MC 作者明确「Turbo 和 Spectrum 都吃掉音频高频、Spectrum 会错估冻结行」——**续接链上关 Spectrum**，用 8 步 v1.1 LoRA，不要给 4 步 LoRA 加步数当等价（PrefixStream 退化分析）。
9. 显存：续接本身只多占 22–39 帧的 cond 行；真正的坑是 Multishot 实测的「激活预留挤掉权重 → DiT 差 399 MB 没全载 → 18.8 s/it 变 283 s/it」，4090 上务必让 int8 权重全驻留。
10. 4090 速度参考：pxl‑pshr 实测 1280×704×107 帧 Ref2VA，25 步约 21 min、8 步 Turbo 约 7 min（含 1.8× 的双视图开销，单程约 4 min）；MC 作者 5070 Ti 16 段 736×576 共 4:34 用时约 2 h（≈7.5 min/段，含一步 refine）。

---

## 各仓库精读

### NikoDemon80/ComfyUI-H3-Motion-Context（★1356，GPL‑3.0，最后推送 2026‑10‑18）
- **定位**：官方 awesome 索引里的「多镜/长视频」首选；v0.7.1，要求 ComfyUI ≥0.34（0.33.4 以下用 0.3.1）。
- **核心机制（nodes.py）**：从上一段 AV latent（不经 VAE 往返）切出最后 N 帧的视频 latent，每个 latent step 变成一个 `minimax_keyframes` 条目（`resolved_frame_index` = 像素帧偏移），钉在新段**开头**（`ANCHOR_MODE="head"`），采样后由 Trim 节点去掉这 N 帧。音频取最后 `audio_context_length` 帧对应的 40 Hz tick，作为一个 **负数、分数索引** 的 audio keyframe（`index = end_frame − ref_audio_t·3/5`）放在新段自身时间线上、**向后对齐到接点**——这是「继续同一段音频」而不是「翻唱」的关键。四个曾经是开关的选项（`ENCODE_MODE=video / ANCHOR_MODE=head / AUDIO_MODE=timeline / CROP=disabled`）已固化为常量。
- **不 patch**：`layout_contract.py` 在首次运行时用假 latent 构造 `PackedLayout`，验证负数/分数索引仍按 `cursor + 5/3·index` 落位，不通过就拒跑；若发现别的包包了 `PackedLayout.__init__` 会报出是谁。
- **关键参数**：`context_length` ∈ {22(默认),5,39,56}（`VIDEO_RUN_GRID` 17k+5，离网格值向下吸附）；`audio_context_length` 默认 18（3 的倍数正好落在 40 Hz 网格，24 会逐段闷）；Trim `match_tail=True` 修正每段 ±8 ms 的音频网格舍入；Save/Load Latent 走文件（`output/h3_context/clip_0000N.safetensors`），Chain 节点按钮 Run/Approve/Chain(segments)/Reset，三者需在同一画布组。
- **抗漂移（0.7.0 实验）**：`MiniMaxH3RefineBlend`（第二个采样器用 SplitSigmas step 7 做 1 步 refine，保留钉住的 22 帧、其余混入，`blend_frames` 22）、`MiniMaxH3JoinMatch`（匹配接点两侧均值/方差/细节，`tuning=auto` 区分固定机位与运动镜头）、`MiniMaxH3SigmasTail`（最后 3 个 sigma ×0.5 降锐化）。
- **示例工作流**：Ref2VA、`fastvideo_fasth3_8step_v2_pruned_int8_convrot` + qwen3vl nvfp4 + video VAE int8，1280×768×124 帧，euler/simple 8 步，`VedaSparseAttention`（r2va_veda_preview_fp8，32/32）。
- **作者实测**：16 段 4:34 多机位情景剧，736×576，5070 Ti 约 2 h；接缝电平阶跃 median 0.905 → 带音频续接 0.16。
- **坑**：分辨率中途不能变（latent 不能缩放，直接报错）；Spectrum 必须关；Turbo 让音频变厚、画面变软；提示词要「气闸」——新段开头 2 s 保持上段构图（给演员呼吸/重心变化，否则渲染成定格），再切新调度；时间码要减去 0.92 s 的钉头。旧版本（≤0.3.1）会 patch 核心，别同时装两份。
- **评级：采用**。

### tritant/ComfyUI_MiniMax_H3_Extender（★371，Apache‑2.0，最后推送 2026‑10‑27）
- **定位**：把 Ref2VA + Motion Context + 磁盘缓存 + 多段卡片 + 参考管理 + 最终合成塞进一个 `MiniMaxH3Extender` 大节点（extender.py 7.5k 行），作者声明 v3.0.14 为「最终功能版」。
- **机制**：motion_context_ram.py 照搬 MC 算法但在同一 DAG 内传 latent（无 Save/Load）；`context_length` 默认 22，`audio_context_length` 默认 0（跟随 22）。FL2VA 模式用像素交接：从上段**最后 6 帧挑最清晰稳定的一帧**作下一段 First 图并把上段裁到该帧。接缝修正：亮度增益按 gamma 均值匹配并钳在 0.88–1.12；音频走 PCM 单次编码 + 入场渐变（`pcm_single_aac_gain_chain_v3_entry_ramp`）。v3.0.5 加「Latent Refine/Upscale」：LBH `minimax_h3_latent_upscaler_3d_conv_v1_bf16` 自动从 HF 下载，默认 ×1.5、4 步、denoise 0.30。
- **patch 情况（重要）**：`patch_motion_payload.ensure_patch()` 在每次执行前**无条件重装** `MiniMaxH3.extra_conds` 包装（即使 ComfyUI ≥0.34 原生支持）；`PackedLayout.__init__` 仅在旧核心上 patch；检测到「foreign」patch 时拒跑。和 Herrgott / LongMedia 不能共存。THIRD_PARTY_NOTICE 承认源自 GPL 代码却以 Apache 发布——许可有瑕疵。
- **默认值**：896×576、0.40 MP auto、steps 4、euler/simple、denoise 1.0、每段 10 s、最多 512 段；示例用 `minimax_h3_ref2va_pruned_int8_convrot` + `ref2v_turbo_4step_v0.1` 强度 1、qwen int4、video VAE fp16；参考最多 9 图 + 3 视频 + 3 音频，视频参考自动重采样到 24 fps 并吸附 17k+5。
- **价值**：逐段「生成→预览→重试→Validate」、每段独立 LoRA/种子/色彩校正、可中断续跑、`.ext` 工程包含参考图，是最像剪辑软件的体验；`subject_definitions` 每段开头重复的提示词模板可直接借用。
- **坑**：默认 4 步 + v0.1 LoRA 已过时（改 8 步 v1.1 768p）；Motion OFF 模式各段完全独立、无连续性；Windows 下验证充分（作者截图均为 Win）。
- **评级：试用**（图省事时用；要和 MC 二选一装）。

### ukr8b3g-cmyk/ComfyUI-H3-Continuum（★302，MIT，最后推送 2026‑11‑04）
- **定位**：日本作者的「生产采样器」：分 chunk 生成、逐 chunk Review/重试、Take 存档、Project/Take Manager 面板、Second Pass；3.10.2，Python 92k 行，CPU 测试 2248 个。声明 ComfyUI ≥0.32。
- **机制（continuation.py / layout_adapter.py / model_patch.py）**：上段尾部作为一个 `kind=video|video_audio` 的**参考块**挂进 `minimax_refs`，再由一个 **按 MODEL 克隆安装的 APPLY_MODEL wrapper** 在 forward 时把带 `_h3cj_*` 标记的参考行原地改写 `PackedLayout.position_ids`，移到目标时间线上——不全局 monkey‑patch，Sol‑Attn 按 position_ids 身份注册的 span 仍有效。
- **context 选择**：`CONTINUITY_FRAMES` = Balanced 22 / Fast 5 / Strong 39(实验)；`Auto — conservative` 按 latent 运动分数自动选（≤0.035→5，≥0.12 且容量≥39→39，否则 22）。最后两个逻辑 chunk 可「terminal merge」成一个物理单元，重叠 22 帧。解码延迟到全部采样后，逐 chunk 解码并去重叠，音频按累计样本边界放置避免 119 帧段的逐段舍入漂移。
- **参数/工作流**：V3.9 模板 `minimax_h3_fl2va_pruned_int8_convrot` + nvfp4 + video VAE int8，Draft 0.30 MP，Chunks 2 × 5 s，Review Each Chunk；Turbo Sample 用 DasiwaHybridV4 int8 + `fl2v_turbo_4step_v1.2_768p` 却跑 6 步（作者自己注明不是验证配置）。Spectrum、KJ SageAttention、rgthree 为模板依赖且默认关闭。
- **实测范围**：512×512、2×5 s、8 步 Turbo、RTX 5060 Ti 16 GB；16 GB 复杂场景峰值 15.5–15.6 GiB。Issue #13（反复续接后对比度/边缘能量上升）**未解决**，实验性前缀幅值归一化默认关。
- **坑**：Review/Take/Run Storage/Sampling v6 签名机制极重，改任何模型/LoRA/attention 都会让旧 Take 变只读；第一次上手成本高。
- **评级：观望**（机制干净，但对「单人 4090 抽卡」过重）。

### seitanism/ComfyUI-H3-Motion-Context-MultiRef（★287，GPL‑3.0，最后推送 2026‑09‑05）
- **定位**：MC 的早期分支，Update 1–9（2026‑08‑10 → 09‑05）；作者把「按 token 的视频/音频 noise_mask」贡献进 ComfyUI 核心（PR #15375），又修了音频 VAE 包装裁切（#15972）与遮罩速度转换（#15988）。
- **两条续接家族**：① 原生 guide（`H3 Motion Context`，旧 OLD‑* 工作流）；② **latent 遮罩**：`H3 Generated AV Masked Context`（默认 [39 帧, 音频末 8 tick 可重生]）、`H3 Existing Video Masked Context`、`H3 Masked AV Bridge`（两个已知端点之间补过渡，context 必须 39+51k，目标 5+17k 且 > 两端 context 之和，建议 192/39）、`H3 Song Audio + Masked Video Context`（整首母带歌曲按 40 Hz 网格精确切进音频 latent，音频遮罩 0、视频 1）。
- **为什么 39**：39 帧 = 1.625 s = 65 tick，是视频 17k+5 与音频 40 Hz 同时整除的最小值（其后 90/141/192）；非整除会出现 73 帧→121.67 tick 的分数端点。
- **AV Extension 示例**：Ref2VA int8 + qwen int8 + video VAE int8，960×544、**362 帧**/段，res_multistep/simple 20 步 + `fl2v_turbo_8step_v1.0` 0.95（步数与 LoRA 不匹配，疑为旧配置），shift 12/3；6 个 Extension 分组用 `MiniMaxH3StreamLiveExtensionAVToVHS` 流式写 VHS；Keep source audio 时仅末 0.2 s 音频重生。2MP De‑Rope 示例依赖 MAINodes `Jerk Oracle/Time Smear/Exact Recover` + SolAttn_triton + LBH 放大器。
- **坑**：示例要求恒定 24 fps 源；不提供跨重启的磁盘断点；依赖包多；9 月后无更新，PR 已入核心后其独特价值在下降。
- **评级：观望**（想做 MV 母带对拍或两端桥接时再翻它）。

### vizart-vj/ComfyUI-MiniMax-H3-LongMedia（★316，Apache‑2.0，最后推送 2026‑09‑29）
- **定位**：俄语作者的「Director」整合包 0.6.63（nodes.py 30k 行）：Setup/Planner/Director/Cameras/Sampler/Decode/Reconstructor，含 Sol‑H3 AdaLN 缓存、Sol 稀疏注意力、MLP 分块、Latent Hi‑Res 二阶段、lip‑sync/redub、运动修复。
- **机制**：`ContinuationContext`（video_latent_tail + audio_latent_tail + overlap_frames）；GENERATED→GENERATED 复用保存的 TAKE latent，MEDIA→GENERATED 只编码外部视频尾窗并钉为 frame‑0 keyframe。`transition_frames` 默认 22（5–3600，步长 17），`segment_seconds` 默认 5；Sampler 有 `video_context_denoise`/`audio_context_denoise`（0 = 完全保留继承重叠，即 noise_mask 路线）。
- **patch**：`motion_context_layout_patch.py` 全局替换 `PackedLayout.__init__`，`hybrid_payload_patch.py` 包装 `MiniMaxH3.extra_conds`，marker‑gated（只改带 `motion_context_index` 的 keyframe），ABI 刻意与 MC/Context Loop 旧版一致以便「复用已装的 owner」。
- **显存策略**：`memory_mode=auto` 按量化物理大小而非 BF16 逻辑大小选档（防 16 GB 卡被误降到 ultra_low_vram）；Windows 走 `ModelMMAP/TensorFileSlice` 文件映射；文档全部围绕 16 GB 卡。
- **坑**：全局 patch + 自带注意力/缓存层，与 SageAttention/Veda 等外部 patch 叠加风险高；更新停在 9 月底；没有 4090 数据。
- **评级：观望**。

### knoic/ComfyUI-MiniMaxH3-PrefixStream（★215，MIT，最后推送 2026‑11‑07）
- **定位**：中文文档，「低侵入」：不改核心、不 patch DiT，只在续接处插 `Continuation Config/Applier` + `Trim Prefix` + `Long Video Stitcher` + `Save/Load AV Latent` + Clip Bin 素材箱（画廊/血缘树选任意历史片段接力）+ `Disk Video Stream` 低内存落盘 + `Video Chunk Slicer/Patch Reassembler`（长片局部重绘）。
- **机制（pipeline/native_masked_av.py）**：`cache_mode` 默认 `Native Masked AV`：按 17k+5 网格选上段相位对齐的尾部（结束 step ≡2 mod 5、起始 ≡0 mod 5），复制进目标开头，`noise_mask = NestedTensor((video_mask, audio_mask))`，前缀 0、其余 1；音频 tick 数先算时长再舍入一次、末端对齐。`continuation_frames` 默认 **39**（5…192 可选；22 = 官方 LatentCut/LatentConcat 组合的 7 latent/37 tick）。`audio_tail_carryover` 默认 Match Video Handover；`audio_feather_ticks` 0；`video_context_denoise` 0（实验 0/0.03/0.06，遮罩按 1/256 取整）；`reference_noise`（0.4→0 余弦注噪，配对编码 Δz 作用于原 latent）；`audio_continuation_mode` 可切 `Native Audio Guide`。源/目标过短自动回退 `Safe Native`。
- **接缝处理**：`Trim Prefix` 在**像素与波形空间**裁切（避免再解码闪烁/偏色），记录裁切后相位；`Stitcher` 默认 `crossfade_frames 4`、`luminance_match True`、`luminance_fade_frames 16`、音频 `crossfade_ms 15`，重叠区不增益。
- **退化分析（docs/DEGRADATION_ANALYSIS_CN.md）**：皮肤斑点/纯色背景斑纹归因于「历史纹理误差被再次当条件」；给出对照顺序（基线→22 vs 39→软遮罩→纠偏 LoRA→组合），并接入 `continuation_model` 插槽以便只在续接段用 **Imagineer13/H3‑Anti‑Burn‑LoRA**；明确不做 latent 均值匹配、不做模糊重编码。
- **示例**：fl2va bf16、768×768×124、er_sde/beta 20 步，turbo v4 旁路，Sage patch 旁路。
- **坑**：Clip Bin 元数据很多；作者自己承认实际画质改善未做多段对照。
- **评级：采用（B 路线首选）**。

### Zzz1phyrf/ComfyUI-H3-LongVideo（★181，无 license，最后推送 2026‑11‑07）
- **定位**：「MV 数字人」与「口播数字人」两个控制节点，支持本地或 RunningHub 执行、分段审核、单段重做、合并；附两份示例工作流（依赖 SelfLift‑Avatar、KJNodes、YCNodes）。
- **机制**：按整条音频在人声低能量/分句间隙自动切点（core.py `word_overlap`/`phrase_gap`，置信度 0.92/0.65），单段 ≤15 s；口播各段用**同一张参考图作首尾锚定**，MV 每段独立 Ref2VA，靠「镜头方案 + 出口运动状态」的中文导演简报（expansion.py）把下一段开场接上一段结尾——**没有 latent 级连续**，成片用完整原声 24 fps 合成。
- **价值**：切点算法与「素材说明→六段式 Ref2VA 提示词」的格式化规则（`ref2va_performance_rule.txt`）可借鉴；RH 依赖对本项目无用。
- **坑**：无 license；需自配扩写 API、人声分离模型；美观但黑盒。
- **评级：观望**。

### HerrgottMargott/Herrgotts-H3-Infinite-Continuation-Suite（★90，GPL‑3.0，最后推送 2026‑08‑22）
- **定位**：FL2VA 路线的续接：每段可带 Last Frame 作「画质重置」，v1.4 改为 **Native Masked AV**（需 PR #15375，节点探测 forward 是否有 `denoise_mask/audio_denoise_mask` 参数，不信版本号）。
- **机制**：`H3ContinuousAnalyzeHandoverV14` 先在上段找「安全视频终点」（检测 FL2VA 落地的冻结/亮度跳变尾巴：硬冻结→检测端点；软终态→提前裁 + 安全边距；都没有→保守回退 11 帧），再**向前吸附**到最近的 39/90/141/192 网格；Stitch Ready 把上段裁到该点，下一段把该点前 39 帧 AV latent 复制进开头并遮罩冻结。`duration_mode` 默认 `Net New Content`（5 s → 总 158 帧 = 39 钉头 + 119 新帧，而 Total Generation 只剩 85 新帧）；`audio_tail_carryover` 默认 `Full Previous Tail`（允许音频比画面多保护，例：画面保护 68..106 帧、音频保护 113..206 tick，多出 0.725 s 把半个词说完）；`audio_feather_ticks` 0；拼接 `video crossfade 4 帧`、`audio de-click 15 ms`、亮度匹配默认关。
- **patch**：runtime_patches 在 0.33+ 仍安装 marker‑gated 的 `PackedLayout.__init__` 音频坐标 wrapper，并**拒绝**与其他拥有该构造函数的包共存（tritant/LongMedia）；与 MC 0.7（不 patch）可共存。
- **示例**：fl2va int8 + nvfp4 + video VAE fp16，res_multistep/simple **15 步无 Turbo**，shift 12/3，Patch Sage Attention KJ 可选；11 段示例片与 7 段 61 s 旧片。
- **坑**：8 月后停更；90/141/192 标注实验；无 HQ 音频重置手段，长链音频仍漂；Qwen Reference 只是文本侧图片，不是 Ref2VA 参考。
- **评级：试用**（分镜图钉关键帧 + 续接二合一的最佳参考实现）。

### akatz-ai/h3-relay（★51，GPL‑3.0，最后推送 2026‑10‑22）
- **定位**：「可导演、可续跑、显存有界」的分段流水线：Sequence Start → Generate Shot ×N → (H3 Ultimate 2×/LTX 2.5 增强) → RIFE 插帧 → Assemble，`Run staged · bounded RAM` 把每一阶段拆成独立队列任务并在任务间卸载模型。要求 **ComfyUI ≥0.37.0**，验证环境 Linux + RTX 4090 + comfy‑kitchen 0.2.33。
- **机制**：vendored ethanfel/Context‑Loop 的 `sliding_history`（WanGP 风格）：`h3_overlap_frames` ∈ {18(默认),35,52,69}（**17k+1 网格**）= 17 帧历史 + 1 帧边界锚，历史放在目标时间线**之前**而不进入采样 latent，解码后只重复 1 帧边界再裁掉；`history_layout.ensure_history_keyframe_support` 在旧核心上内存 patch。默认采样 Euler + `beta57`（16 步精确手工曲线）+ Spectrum 开；FastH3 VSA 档锁 4 forward、shift 12/3、Spectrum 关。
- **4090 数据**：仅功能验证（一次 1664×960 15 s 增强链 260 s、显存峰值 23 GB），无可比生成速度。
- **坑**：Windows 未验证；FastH3 需非主线 VSA 提交；vendored Spectrum/Context‑Loop 整包；Ultimate 需 bbaudio MMH3 UltimateUpscale。
- **评级：观望**。

### pxl-pshr/ComfyUI-MiniMaxH3-Loop（★55，GPL‑3.0，最后推送 2026‑10‑29）
- **定位**：无缝循环（不是续接）：`MiniMax H3 Loop` 模型补丁把 latent 首尾环绕，每次模型调用两侧各多看 `pad_clips`（默认 1）个 17 帧片段再丢弃；`views 2` 再采一个半旋转视图取其接点音频（+1.8× 时间）。要求 **ComfyUI ≥0.42**。
- **对本项目有用的数据**：RTX 4090、1280×704×107 帧 Ref2VA：25 步 ≈21 min，8 步 Turbo v1.0/v1.1/FastH3‑Omni ≈7 min，Turbo + Fun ControlNet（views 1）≈4 min；默认 1344×768×158。Turbo v1.0 快动作会「隔帧停顿」，**v1.1 消除**；FastH3‑Omni 接近 25 步观感。
- **洞察**：H3 把钉住的首帧当「镜头开始」，首帧锚点会让曝光从 35 漂到 50（纯 I2V 也漂到 39），参考图路线曝光稳定——这解释了为何长链用 Ref2VA 比 FL2VA 稳；重复 latent 配同一噪声会让蒸馏模型画出白色噪点。
- **评级：跳过**（短剧不需要循环；记下速度与曝光结论）。

### ptmaster/ComfyUI-PT_H3ConcatAVLatent（★72，无 license，最后推送 2026‑08‑06）
- 62 行单节点：把视频 latent 和音频 latent 合成 H3 采样器要的 NestedTensor，用于对现有视频做 V2V 重绘。作者自己注明 LTX 的 ConcatAVLatent 等价；T8 `Source AV Prepare` 更完整（分别设 video/audio denoise 与遮罩）。
- **评级：跳过**。

### jingyu000/ComfyUI-MiniMaxH3-WhaleTrans-Director（★66，GPL‑3.0，最后推送 2026‑10‑26）
- docs/12 §8 已写机制与依赖，这里只补源码级事实：
- `minimax_h3_finite_segments.py`：`overlap_frames` 默认 22（音频节点默认 39）；`_inject_continuity_instruction` 把那句「opening 00:00–00:0x.xxx is a fixed latent continuation…」插到 `integrated_multimodal_description:` 或 `detailed_description:` 字段后。
- `experimental_latent_guide._apply_linear_temporal_noise_mask`：把上段尾部 latent **复制进目标开头**并建 (1,1,T,1,1) 紧凑 noise_mask，`gradient=True` 时在 guide 区间从 0 线性升到 1（软过渡），否则保持 0（硬冻结）——所以它其实同时属于 B 路线，不只是 direct guide。
- `drift_control_av.py`：改自 ethanfel Context‑Loop 的 Drift‑Control AV v1，用 `set_model_denoise_mask_function` 做「与采样计划匹配的前缀遮罩」（12 步视频、8 步匹配、4 步渐变），只改本次采样的可丢弃前缀，不污染保存的上段 latent。
- `h3_latent_scale.py` `guide_frames` 默认 22（H3HighRefineGuide）。
- **评级：试用**（维持 docs/12 判断）。

### Smite79/MiniMax-H3-LongVideos（★26，自定义「禁止再分发」许可，最后推送 2026‑11‑07）
- **定位**：单节点 `H3-LongVideos`：整场戏按段落（beat）写，自动规划镜头（≥5.2 s，`shot_seconds` 默认 10、上限 15）、写每镜提示词、渲染、配音、拼接。标签含 `not-for-all-audiences`，提示词 tag（`hold/release/remove/wear/lift/tear`）明显面向成人内容。
- **机制（chain.py）**：上一镜**最后一帧像素**作下一镜 `minimax_keyframes[resolved_frame_index=0]`（需完整 video VAE 编码）+ 每镜带角色参考图 + 「memory」背景图；无台词镜头静音渲染再做音频 pass（`silence` latent + 按台词 span 的音频 noise_mask）；`grade()` 用 LUT 把本镜色调匹配到前镜，`hold()` 抑制亮度/色度漂移，`refresh()` 把静止背景回填；默认 8 步 res_multistep/simple，shift 12/3，自动识别 Turbo/Hyperflow/FastH3 并按其训练方式采样；推荐 smhfacct 的 fl2va/ref2va hybrid 合并权重。
- **坑**：许可禁止再分发（不能进 Manager，也不能进我们的 skill 包）；README 内含作者与他人的纠纷声明；黑盒。
- **评级：观望**（只借鉴「静音渲染 + 音频 pass」和 LUT 匹配思路）。

### jlucasmcrell/ComfyUI-H3-Multishot（★81，MIT，最后推送 2026‑08‑27）
- docs/12 §5 已写工作流，这里补续接相关源码事实（2.7.2）：
- `continuity=context_pin` 钉上一镜最后 22 帧**原始 latent**，依赖 Motion‑Context 包；`h3_multishot_utils.py` 4470 行起按名探测：MC **0.4.0 起把音频从参考块改成音频 keyframe，与本采样器行累计不一致（shape mismatch [882,32] vs [956,32]），预检直接拒绝**，要求停留在 MC 0.3.1；而 MC 0.3.1 只保证 ≤0.34。在 ComfyUI 0.37.2 上 `context_pin` 基本不可用，只能 `first_frame`（模型自带交接）或 `cut`。
- 2.7.1 移除了 Registry 禁止的 `exec` 重编 `PackedLayout.__init__` 补丁，改为探测原生/MC。
- **漂移量化（SETTINGS.md，960×544 十镜）**：亮度 1.055→1.022/段（`memory_frames=0`）、色度 1.086→1.039；`pin_renorm=on` 把钉 latent 压回第 1 镜 sigma；`master_normalize=luma+contrast` 在成片外做一次全局拉平；纹理每接 ×1.3，>5 镜开 `chain_gain_control=flatten`；extend take 实测 +13% 细纹/接，**建议 ≤4 窗口（30–40 s）**；`seed_per_shot=ON` 反而保脸；音频：纯 recency 到第 8 镜 4–10 kHz 掉 84–92%，`bank_pinned=1`（永远参考第 1 镜音频）降到 8–50%，最佳音频配方是 `continuity=cut + bank_pinned=1, memory_frames=0`（−5%）。
- **显存教训**：激活预留挤掉权重 → DiT 差 399 MB 未全载 → 18.8 s/it 变 283 s/it（15×）；现在预留钳在 `free − weights − 384 MB`。
- **评级：观望**（CORE 版硬切链仍可用；pin 模式冻结在旧 MC）。

### JGRFW/comfyui-AICG3D（★478，GPL‑3.0，最后推送 2026‑11‑04）
- **定位**：「短剧工作台」：13 号无限分段工作流 = `AICG3D_H3SequenceGlobal`（全局设置）→ `AICG3D_H3SequenceSegment` ×N（每段一个节点，可无限加）→ `AICG3D_H3SequenceCombine`（FFmpeg 合成）；加资源库（`@图片N/@视频N/@音频N`）、`AICG3D_H3PromptSegmentSplit` 剧本分段、六角色 Spark‑TTS 音色库（`@角色1`…）、12 号二采放大（SeedVR2/RTX VSR/VOSR2）、DMAD 四步。节点全部 `AICG3D_H3_` 前缀隔离命名空间；v1.1.26 修了 Manager 启动卡死（requirements 零安装）。
- **机制（aicg3d_h3easy/nodes.py）**：`continuity_mode` ∈ {`latent_guide`(默认), `guide`, `soft_av`, `hard_av`}；guide 网格 (5,22,39,56,73)、AV 网格 (39,90,141)；`SEGMENT_DEFAULT_CONTEXT_FRAMES = 5`（极短重叠）；guide 模式刻意让钉头大部分可重绘（避免递归退化），只把钉头**最后 2 个视频 token** 和全部音频重叠用遮罩锁死（`_segment_apply_guide_handoff`）；有视觉参考时对 context 注噪 α 0.45→0.10（2 步 ramp）。接缝后处理：匹配上段尾帧低频色光，整段亮度校正上限 ±0.04，接缝加性窗口 12 帧，同镜头一帧姿态跳变做运动桥。
- **工作流 13 参数**：`MiniMaxH3SigmaShift [12, 2]`（音频 shift 2，与官方 3 不同，作者称修正音频偏移）；DMAD Sampler + Sigmas 4 步、LoRA 1.0；FL2VA + REF2VA 双槽位混合权重。
- **坑**：15k 行单文件、参数多在面板里；5 帧 context 很弱，连贯主要靠 FL2VA 尾帧→首帧；v1.1.3 已刻意**移除**局部重抽入口（会破坏接缝），只能重做后续整段。
- **评级：试用**（中文短剧向最完整的一体机；验证 shift 2 与 5 帧 context 再决定）。

### bt420000-collab/ComfyUI-H3-MultiGPU（★63，GPL‑3.0，最后推送 2026‑09‑26）
- H3VM 0.21.1：`H3VM Core` 插在 Loader 后、`H3VM Video VAE` 双卡解码；双 5060 Ti 16 GB 实测 1.63× 端到端、步时 23.8→12.8 s/it（SPECTRAL 跨卡**预测器**，非精确计算），双卡扩容把主卡峰值压到 6.08 GiB；需 `--cuda-device all`，基线 ComfyUI 0.35.0，建议 20 步。与续接无关、与单 4090 无关。
- **评级：跳过**。

### T8mars/comfyui-minimax-h3-audio-T8（★1262，无标准 license，最后推送 2026‑10‑31）—只看 Long Video 与 Source AV 菜单
- **Long Video**（`T8/MiniMax H3/Long Video/Experimental`，全部 EXP）：`long_video.py` `CONTEXT_FRAME_STEPS = {5:2, 22:7, 39:12}`，最大 39，Segment 0 必须 context 0；Chain Orchestrator 默认总长 60 s、每段 124 帧、context 22、steps 4、shift 12/3；`Native Masked Video Context（Plan B）` 只硬锁**视频**前缀、音频与 Vocal Lock 遮罩原样；`Native Latent Timeline Concat/Continuation Concat` 在双时钟上去掉整段 5/22/39 重叠；`Prompt Relay Long Video Window` 把全片事件时间线投影到本段（frame 0 = 接受起点 − context）；`Color Match`（参考 5 帧、过渡 24 帧）；MC 同款 Refine Blend / Join Match / Sigma Tail 的 T8 变体（`keep_pin_T8_exp`）。**双模型 4+4**：LOW 4 步小图 → 学习型 3D latent 放大 → HIGH 4 步；已验收配置 `accepted_picture_low_context_v1`（LOW 参考取上段**成片**末 39 帧重编码）+ `high_native_mask_ramp_exp`（HIGH 精确锁 7 个 context latent 单元后按 0.25→0.50→0.75 渐释 3 个单元）+ `bounded_motion_color_exp`；作者承认残留「续段第 2–3 帧短促偏暗回亮」与「轻微接缝变色」。
- **Source AV**：`Source Media Window`（24 fps、17n+5 窗口、32 kHz 立体声对齐）、`Source AV Prepare`（video_mode remix denoise 0.5 / audio lock 0.35、分别建遮罩）、`AV Latent Separate`——外片 V2V 重绘/续拍的正确入口，取代 ptmaster。
- **坑**：README 明言「不保证无接缝、不保证通用 16 GB 性能」；每个节点改动都要换 `chain_id`；KJ/Sol/Sage 节点不能互换。
- **评级：观望**（思路最前沿，稳定性最差）。

### wjluoxiao/ComfyUI-JZL-MiniMax-H3（★135，MIT，最后推送 2026‑11‑07）—只看续接相关
- 续接只出现在 `JZL_MiniMaxCharacterSwap`（长视频换人）：源片自动切段（**5–8 s 最稳**，吸附 17k+5），每段 `<Video 1>`=源片段、`<Picture N>`=定妆图走 ref2va；「分段衔接」默认开：取上段**成片像素**末 `衔接 22 + 过渡 12` 帧按本次画布 `vae.encode` 重编码作 `minimax_keyframes` 钉在段首「跑道」，跑道不进成片且对齐到 17 的倍数；`二采钉帧` 默认开（二采按新分辨率重新编码钉帧，否则二采发糊）；旧「latent 尾帧」跨分辨率插值会整段发糊，仅留对比。推荐 MP 1.0（1344×768）、参考图放大 2–3×、始终开二采到 1280×704。
- **洞察**：作者指出换人比「无限时长」稳，是因为每段有源片逐帧真值可对位，不累积误差——对我们意味着：**有分镜参考视频/动捕的段落比纯文本续写稳得多**。
- **评级：试用（仅换人场景）**。

### Shrek3OnVH5/MiniMax-H3-NativeAudio-MusicVideo-Workflow（★116，无 license，最后推送 2026‑08‑05）
- 两份模板 + `ComfyUI-H3-NativeAudioLock` 节点（把给定歌曲锁进音频 latent 并原样回填），`chain/0x_*` 工作流全部基于 Multishot `H3MultishotSampler`。模板：ref2va int8、1344×768×124、res_multistep/beta 20 步；续接做法仅是「用上一段真实末帧继续场景」。
- **评级：跳过**（音频锁定可用官方 Add Guide/T8 替代）。

---

## 接缝伪影与各家解法速查

| 伪影 | 成因 | 解法（来源） |
|---|---|---|
| 接点亮度/对比度阶跃 | 每段重新归一化；FL2VA 落地尾巴 | Join Match auto（MC）；亮度增益钳 0.88–1.12（tritant）；lum match + 16 帧淡入（PrefixStream）；±0.04 全段校正 + 12 帧窗（AICG3D）；成片外 `master_normalize`（Multishot）；Color Match 5/24 帧（T8） |
| 纹理越接越锐/皮肤斑点 | 模型回放自身输出，纹理能量 ×1.3/接 | Refine Blend 让每段重读参考图（MC）；`chain_gain_control=flatten`（Multishot）；Anti‑Burn LoRA 只挂续接段（PrefixStream 入口）；Last Frame 画质重置（Herrgott）；链 ≤4 段 |
| 音频越来越闷/翻唱感 | 参考位置放音频 = 模仿；高频逐段丢 | 音频 keyframe 向后对齐接点（MC）；`bank_pinned=1` 永远参考第 1 镜音频 / `<Audio 1>` 音色锚（Multishot）；Full Previous Tail 保住词尾（Herrgott） |
| 接点 8 ms 音画错位累积 | 40 Hz 音频 vs 24 fps 视频 = 5/3 | 窗口取 3 的倍数、`match_tail`（MC）；39/90/141/192 双网格整除（MultiRef/Herrgott/PrefixStream） |
| 新段开头定格/停滞 | 「气闸」保持构图但没写动作 | 提示词给呼吸、重心、视线变化（MC）；`freeze_detect.py` |
| 新段把两套构图叠在一起 | 钉住的帧 + 矛盾的新构图 = 并集 | 先 2 s 气闸再切（MC） |
| FL2VA 尾部冻结/亮度跳 | 模型「落地」到 Last Frame | Auto Handover 向前裁到安全点（Herrgott）；取末 6 帧最清晰的一帧交接（tritant） |
| 续段前 2–3 帧暗‑亮震荡、第 1 个自由帧结构跳切 | 遮罩硬边界 | HIGH 7 单元硬锁后 0.25→0.5→0.75 渐释（T8）；soft gradient mask（WhaleTrans）；只锁末 2 token（AICG3D） |
| Turbo 隔帧停顿 | 4/8 步 v1.0 LoRA 快动作 | 换 v1.1 768p（Loop 实测） |
| 蒸馏模型白色噪点 | 重复 latent 配同一噪声 | 重叠区换新噪声（Loop） |

## 在 4090 上做 30–60 s 横屏短剧的最稳续接方案（排序）

1. **硬切优先 + Ref2VA 独立成镜**：每镜 5–8 s，同一组角色/场景参考图 + `<Audio 1>` 音色锚，`seed_per_shot` 随机，接缝用 FFmpeg 直拼或 4 帧叠化。零第三方续接节点、零漂移累积，占 30–60 s 短剧 80% 的镜头。
2. **单镜 >15 s 必须续接时：Motion‑Context 0.7.1**（Ref2VA，context 22 / audio 18，Save/Load Latent + Trim，match_tail 开，Spectrum 关，8 步 euler/simple + 768p 8‑step v1.1 LoRA，1280×704 或 1280×768，每段 124–192 帧，一条链 ≤4 段），可选 Join Match auto + Refine Blend；提示词按「气闸」写。
3. **想抽卡/分支时：PrefixStream Native Masked AV 39** + Trim Prefix（像素裁切）+ Stitcher（lum match、4 帧叠化、15 ms 音频）+ Clip Bin；同样 8 步，`video_context_denoise` 保持 0。
4. **分镜图钉关键帧的连续长镜：Herrgott v1.4**（FL2VA int8，每段带 Last Frame 画质重置，Net New Content 5 s，39 帧，Full Previous Tail）——注意它会装 PackedLayout wrapper，不与 tritant/LongMedia 同装。
5. **图省事：tritant Extender**（改 8 步 v1.1、Motion ON、0.4–0.6 MP 草稿），接受其 extra_conds 补丁。
6. **中文一体机：AICG3D 13 号 / WhaleTrans**——先用 2 段测试其 shift 12/2、5 帧 context、DMAD 4 步在 1280×704 下是否糊，再决定。
7. 不建议：Multishot context_pin（MC 版本冲突）、Continuum/LongMedia（过重）、T8 Long Video（EXP）、h3‑relay（Linux）。

## 可写进 skill 的规则

1. 短剧默认用硬切：每个镜头独立 Ref2VA 生成 5–8 s（124/158/192 帧），共用同一组参考图与音色参考，接缝 FFmpeg 直拼；只有单镜头必须 >15 s 时才启用续接。（Multishot SETTINGS 音频最佳配方 `continuity=cut`；MC「airlock」）
2. 一条续接链不超过 4 段（≈30–40 s）；更长就在自然转场处重启链并换新参考锚。（Multishot 2.6.0 +13%/接实测；MC Limitations）
3. 续接链内禁止改分辨率、模型、LoRA、shift、采样器；latent 不能缩放，MC/tritant/PrefixStream 遇到尺寸不一致直接报错。（MC nodes.py 分辨率检查）
4. Ref2VA 续接用 `MiniMaxH3MotionContext`：`context_length=22`、`audio_context_length=18`，`context_latent` 走 `MiniMaxH3MotionContextSaveLatent/LoadLatent`（Load 0/Save 1 起步），`MiniMaxH3MotionContextTrim.match_tail=True`，不要把 Load Latent 接解码器。（MC README）
5. 装 Motion‑Context 后 Spectrum 必须 bypass；Turbo LoRA 会让链上音频变闷，成片段优先 8 步 v1.1 768p 而非 4 步。（MC Limitations；Loop 实测 v1.1 去抖）
6. 续接段提示词：开头 2 s 保持上段结尾构图与人物位置（不加台词、不换调度），并写一个微动作（呼吸/重心/视线）防定格；时间码整体减去钉头 0.92 s（22 帧）。（MC「Writing prompts for a chain」）
7. 续接段 `[Shot 1]` 后可插入 WhaleTrans 原句：`The opening 00:00.000-00:00.917 is a fixed latent continuation from the preceding segment. Describe this opening as the preceding segment's final shot, preserving character positions, environment, motion, camera path, lighting, color, and sound before introducing new action.`（22 帧时写 00:00.917）。（WhaleTrans `_inject_continuity_instruction`）
8. 需要分支/抽卡/从任意历史镜头接力时用 PrefixStream：`MiniMax H3 Continuation Config = Native Masked AV, continuation_frames 39`，`Applier.context_latent` 接上段**完整**采样 latent，`Trim Prefix` 接解码后的 IMAGE/AUDIO（像素空间裁切），`Long Video Stitcher` 保持 `crossfade_frames 4 / luminance_match on / luminance_fade_frames 16 / crossfade_ms 15`。（PrefixStream USER_GUIDE）
9. 遮罩路线的重叠长度只取 39/90/141/192（视频 17k+5 与音频 40 Hz 同时整除）；MC 路线取 22 或 39，音频窗口取 3 的倍数。（MultiRef TECHNICAL_ARCHITECTURE；MC audio grid）
10. 用 FL2VA 钉分镜图做长镜头时用 Herrgott v1.4：`masked_context_frames 39`、`duration_mode = Net New Content`、`audio_tail_carryover = Full Previous Tail`、`audio_feather_ticks 0`，`Auto Handover = Balanced`，每段带新的 Last Frame 作画质重置。（Herrgott README baseline）
11. 同一 ComfyUI 里只装一个会包 `PackedLayout.__init__ / MiniMaxH3.extra_conds` 的续接包（tritant、Herrgott、LongMedia、旧 MC ≤0.3.1 互斥）；MC 0.7 不 patch，可与它们共存但仍建议只留一个。（各包 `_already_patched`/`refusing to stack` 逻辑）
12. Multishot `continuity=context_pin` 在 ComfyUI 0.37 上不可用（它要求 MC 0.3.1，而 MC ≥0.4 已改音频 keyframe，预检报 shape mismatch）；Multishot 只用 `first_frame` 或 `cut`。（h3_multishot_utils.py 4470–4495）
13. 链 >5 镜时开成片外的全局拉平而不是逐镜校正：Multishot `master_normalize=luma+contrast`、`chain_gain_control=flatten`；逐镜校正会修可见帧却修不到回传的 latent。（Multishot SETTINGS「per-shot correction does not fix it」）
14. 每段结束检查钉头是否被渲染成定格：跑 MC `tests/freeze_detect.py clip*.mp4`；接缝音频用 `tests/seam_probe.py A.flac B_untrimmed.flac`（需裁切前音频）。（MC Testing）
15. 续接链上的音频输出是 32 kHz，不是 48 kHz；FFmpeg concat 脚本从文件读采样率，不要写死 48000。（MC「H3 emits 32 kHz」）
16. 拼接时音频接点落在新段前 0.75 s 内最安静处并做 40 ms 等功率交叉；台词不要写在段首/段尾 0.75 s 内。（Multishot「Seam audio」）
17. 皮肤斑点/纯色背景斑纹出现时按单变量顺序排查：先基线硬遮罩 → 比较 22 vs 39 → `video_context_denoise 0/0.03/0.06` → 只在续接段挂 `Imagineer13/H3-Anti-Burn-LoRA`（HF 可下）→ 再组合；不要用模糊重编码或 latent 均值匹配。（PrefixStream DEGRADATION_ANALYSIS_CN）
18. 续接时参考视频/音频/深度的时间窗要同步后移：124 帧段 + 22 帧重叠，下一段参考从第 102 帧开始而不是 124。（PrefixStream 退化分析表）
19. 保证 int8 DiT 权重 100% 驻留 GPU 再谈激活预留：权重差几百 MB 未全载会让步时从 ~19 s/it 跌到 ~283 s/it；OOM 时降分辨率或减参考图，不要加预留。（Multishot SETTINGS 2026‑08‑12）
20. 4090 预算：1280×704×107 帧 Ref2VA 8 步 Turbo ≈4 min/段（不含双视图），25 步 ≈12 min；一条 4 段 ×5 s 链按 20–30 min 估。（pxl‑pshr Loop 实测换算）
21. 用上一段像素尾帧做交接（I2V/FL2VA 路线）时，从末 6 帧里挑最清晰、局部最稳的一帧，并把上一段裁到该帧，避免倒退跳帧。（tritant fl2va_engine `_select_best_plan_end_frame`）
22. 像素尾帧交接若还要二采放大：钉帧必须按二采分辨率重新 `vae.encode`（JZL「二采钉帧」），跨分辨率插值 latent 会整段发糊；段首留 22+12 帧「跑道」不进成片。（JZL USAGE 七）
23. 首帧锚点（I2V/FL2VA）会让 H3 把该帧当「镜头开始」并引起曝光漂移（实测均值 35→50）；需要稳定曝光的连续镜头优先 Ref2VA + 参考图而非首帧锚。（Loop README）
24. 遮罩硬边界造成续段前 2–3 帧暗‑亮震荡时，改用渐释：锁前 7 个 latent 单元，其后 3 个单元遮罩 0.25→0.50→0.75，或把 gradient mask 打开。（T8 `high_native_mask_ramp_exp`；WhaleTrans `gradient=True`）
25. 不把 Spectrum、Turbo LoRA、Sol/VSA 稀疏注意力在续接链上同时打开；先全关跑基线，再逐个开。（MC Limitations；Continuum USER_GUIDE「Do not enable Spectrum and a Turbo LoRA together」）
26. 每段 `subject_definitions` 块放在提示词最前并逐段重复，同一张参考图可同时定义人物与环境（`<Subject 3>` = `<Picture 1>` 的街道环境）。（tritant README「Keeping References Consistent」）
27. 可选的最终去闪烁：对整条成片做一次全局 luma 归一化（Multishot `master_normalize`）或 LUT 匹配到第 1 镜（Smite79 `grade()` 思路），而不是在生成环节逐段补偿。
28. 不采用 Smite79（禁止再分发）与 Zzz1phyrf/Shrek3（无 license）的代码进 skill 包；只引用其结论。

## 未覆盖/未读完

- ethanfel/ComfyUI-MiniMaxH3-Contex-Loop（h3‑relay、WhaleTrans、LongMedia 都从它借 sliding history / Drift‑Control AV，是本簇的隐藏上游，未单独克隆）。
- Imagineer13/H3-Anti-Burn-LoRA（HF 模型卡未读，只知 PrefixStream 引用）。
- LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler、bbaudio-2025/Comfyui-MMH3-UltimateUpscale（多家续接包的二采依赖，属放大簇）。
- Continuum 的 docs/SECOND_PASS_GUIDE.md、REGENERATE_INTENT；LongMedia 的 DIRECTOR_GUIDE 与 TWO_PASS 指南；T8 的 HYPERFLOW_LONG_VIDEO_EXP、PROGRESSIVE_LONG_VIDEO_EXP；AICG3D 的二采无限修复文档——均只扫了标题。
- MultiRef 的 KEYFRAMES_AND_INSERTS.md（任意位置硬遮罩插入）未精读。
