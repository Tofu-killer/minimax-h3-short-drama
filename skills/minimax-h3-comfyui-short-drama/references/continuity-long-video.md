# 段间衔接与长视频（> 15 s）

> 依据 `docs/13-github-survey/01-directors-and-timelines.md`（23 个导演台）与 `02-long-video-continuation.md`（19 个续接包）的源码级精读。所有作者都承认：**链越长越漂**（亮度每段 ×1.02–1.055、纹理每接 +13%、音频高频逐段衰减、>4 接缝声音发闷）。

## 1. 默认策略：硬切，不续接

短剧 80% 的镜头应是**独立生成 + 硬切**：
- 每镜 5–8 s（124 / 158 / 192 帧）独立 Ref2VA，共用同一组角色/场景参考图 + `<Audio 1>` 音色锚，每镜换 seed；
- 段间靠 `end_state → 下一段开场` 的文字承接 + 相同参考图保持一致；
- 接缝 FFmpeg 直拼或 4 帧叠化；音频接点放在新段前 0.75 s 内最安静处，40 ms 等功率交叉；**台词不要写在段首/段尾 0.75 s 内**；
- H3 输出音频是 32 kHz，concat 脚本从文件读采样率，不要写死 48000。

只有「单个镜头必须 > 15 s」（长走位、长独白、歌唱）才启用续接，且**一条链 ≤ 4 段**，更长就在自然转场处重启链并换新的参考锚。即使用户要求「中间不切镜」，也先用一句话说明硬切 / 插入反应镜的代价与收益，再按用户决定走续接。

## 2. 两种底层机制

| 机制 | 做法 | 代表 | 重叠帧 |
|------|------|------|--------|
| A 钉头（Motion-Context 系） | 上段 latent 尾部切下来，作为 `minimax_keyframes` 钉在新段开头，采样后裁掉 | NikoDemon80/Motion-Context 0.7.1、tritant Extender、Continuum、LongMedia、seesee75 Director | 视频 **22** 帧（0.917 s）、音频 18–24 帧；网格 5/22/39/56 |
| B 遮罩前缀（Prefix 系） | 尾部 latent 直接复制进目标开头 + 原生 `noise_mask` 冻结 | knoic/PrefixStream、Herrgott v1.4、MultiRef masked、T8 Plan B、AICG3D hard_av、WhaleTrans 软遮罩 | **39** 帧（视频 17k+5 与音频 40 Hz 同时整除）；网格 39/90/141/192 |

保守无插件法：上段尾帧 → 下段 I2VA 首帧（从末 6 帧里挑最清晰的一帧，上段裁到该帧）；或上段尾帧 + 下段首帧用 FL2VA 生成 2–4 s 转场。首帧锚会引起曝光漂移（实测均值 35→50），需要稳定曝光的连续镜头优先 Ref2VA + 参考图。

## 3. 推荐（RTX 4090，16:9，30–60 s 短剧）

1. **硬切 + Ref2VA 独立成镜**（见 §1）。
2. **必须续接（Ref2VA）：NikoDemon80/ComfyUI-H3-Motion-Context 0.7.1** —— 不 patch 核心、启动自检。`MiniMaxH3MotionContext context_length=22, audio_context_length=18`；`context_latent` 走 `SaveLatent/LoadLatent`（Load 0 / Save 1 起步）；`Trim match_tail=True`；Load Latent 不接解码器。配 8 步 euler/simple + `ref2v_turbo_8step_v1.1_768p`（有对白 ≥ 12 步），1280×704 或 1280×768，**每段 124–192 帧**（更长的段接缝更漂、显存更紧；4090 绝对上限 328 帧），一条链 ≤ 4 段。**Spectrum 必须 bypass**。
3. **要抽卡 / 分支 / 从任意历史镜头接力：knoic/ComfyUI-MiniMaxH3-PrefixStream（MIT）** —— `Continuation Config = Native Masked AV, continuation_frames 39`，`Applier.context_latent` 接上段完整采样 latent，`Trim Prefix` 接解码后的 IMAGE/AUDIO，`Long Video Stitcher crossfade_frames 4 / luminance_match on / luminance_fade_frames 16 / crossfade_ms 15`，`video_context_denoise` 保持 0。
4. **分镜图钉关键帧的长镜头（FL2VA）：Herrgott v1.4** —— `masked_context_frames 39`、`duration_mode = Net New Content`、`audio_tail_carryover = Full Previous Tail`、每段带新的 Last Frame 作画质重置。它会装 PackedLayout wrapper，不与 tritant / LongMedia 同装。
5. **一体化导演台：seesee75-commits/ComfyUI-MiniMaxH3-Director（GPL-3.0，ComfyUI ≥ 0.37）** —— 原生 Loop 把任意时长切成 ~10 s render part，22 帧画面钉 + 24 帧音频钉，16 GB 卡实测 1280×704。附带测量规则见 §4。
6. **单节点日常：nkxx188/ComfyUI-MiniMaxH3-Easy（MIT）** —— `@Image1/@Video1/@Audio1` 引用、`#` 对白块、`---` 分段，Context Segments 四种模式（Motion Context / RGB Guide / Soft AV / Hard AV）全走核心 `minimax_keyframes`。
7. 不建议：Multishot `context_pin`（要求 MC 0.3.1，与 0.37 不兼容）、Continuum / LongMedia（过重、全局 patch）、T8 Long Video（EXP）、h3-relay（仅 Linux）、tritant 默认 4 步（改 8 步 v1.1 再用）。

## 4. 续接链的硬规则（有测量数据）

- 链内禁止改分辨率、模型、LoRA、shift、采样器；latent 不能缩放。
- 接缝后 **2.4–2.5 s 内不安排新动作**；render part **最后 2 s 内不切镜**；需要时把段边界整 17 帧挪开。
- 台词归属镜头开始所在的段；镜头若开始于段末 2 s 内，台词放到下一段。
- 单段上限：帧数 × 宽 × 高 ≤ 360 × 1280 × 704，且 ≤ 719 帧；1280×704 维持 ≤ 360 帧；640×352 可一段 30 s 不漂移，45–60 s 会重复台词和动作。
- 音频链 > 4 个接缝明显发闷（>4 kHz 能量降至 1/11）：60 s 短剧要么锁外部配音/歌曲（`noise_mask=0`），要么对白段 ≤ 5 段。
- 8 步 Turbo 时人声是最弱环节：有对白的续接段至少 12 步，或改 Hard AV / 锁音轨。
- 保证 int8 DiT 权重 **100% 驻留 GPU**：差几百 MB 未全载会让步时从 ~19 s/it 跌到 ~283 s/it；OOM 时降分辨率或减参考图，不要加 reserve。
- 续接时参考视频/音频的时间窗同步后移（124 帧段 + 22 重叠 → 下一段参考从第 102 帧开始）。
- 像素尾帧交接若还要二采放大：钉帧按二采分辨率重新 `vae.encode`，跨分辨率插值 latent 会整段发糊；段首留 22+12 帧「跑道」不进成片。
- 链 > 5 镜时做成片外全局拉平（luma + contrast 归一化或 LUT 匹配到第 1 镜），不要逐镜校正（修不到回传的 latent）。
- 皮肤斑点/纯色背景斑纹：单变量排查 → 基线硬遮罩 → 22 vs 39 → `video_context_denoise 0/0.03/0.06` → 只在续接段挂 `Imagineer13/H3-Anti-Burn-LoRA` → 再组合。
- 遮罩硬边界造成前 2–3 帧暗亮震荡：锁前 7 个 latent 单元，其后 3 个单元遮罩 0.25→0.50→0.75（gradient mask）。
- 同一 ComfyUI 里只装一个会替换 `PackedLayout.__init__` / `MiniMaxH3.extra_conds` 的包（AIMixer 段间引导、tritant、Herrgott、LongMedia、旧 MC、kat3ri Extend 互斥；kat3ri 会让整个会话接缝偏色）。
- 续接链上不同时开 Spectrum、Turbo LoRA、稀疏注意力；先全关跑基线再逐个开。

## 5. 续接段提示词写法

- 第二段起 `[Shot 1]` 逐项复现上段最后 overlap 秒的画面与声音（人物位置、动作相位、镜头、灯光、环境声），不加台词、不换调度，写一个微动作（呼吸 / 重心 / 视线）防定格；时间码整体减去钉头 0.917 s。
- 可直接插入 WhaleTrans 原句：`The opening 00:00.000-00:00.917 is a fixed latent continuation from the preceding segment. Describe this opening as the preceding segment's final shot, preserving character positions, environment, motion, camera path, lighting, color, and sound before introducing new action.`
- 重叠结束后不切镜写 `From 00:00.917, without a cut, …`；切镜则 `[Shot 2] At 00:00.917, the shot cuts to …`。
- 不重复运镜句（每段会再推一次）：写 `The camera holds a static shot, keeping the framing of the preceding video`；运镜必须在本段内起止。
- 人物只在首次出场完整定义，后续段写 `<Subject 1> is the girl already visible in the opening Latent Guide; <Picture 1> calibrates her identity`；上一段传入的 latent guide **不占** `<Picture/Video/Audio N>` 编号。
- 上段最后一个 Shot 的起点 = 段长 − 重叠秒；内容选低速、轮廓清晰、少遮挡的可承接状态，不塞新剧情。
- 两端钉死的桥接镜头至少 5 s，并把到达状态写进文本（`…ends with her at the doorway`）。
- 描述正文 350–500 词；参考 ≤ 9 图 / 3 视频 / 3 音频 / 总 12 件，参考视频/音频各 2–15 s；**要保人物卡时不要同时挂参考视频**（视频里的人脸和音轨会压倒 `<Picture>`/`<Audio>`）。

## 5b. 长尾补充

- I2V 尾帧接力链用 `anchor_mode=inpaint`（复制 + 遮罩保护）而不是 keyframe（接缝帧间跳变 5.4–6.8× → 1.5–1.7×），上下文 5 帧而不是 22；换人 / 换装续接对上下文做锥形加噪 22/0.45/0.10/3 消色彩残留，加噪结果不回喂。
- 要跨段保持音色选 FastH3 Omni 或 Pika Flex（全程 Ref2VA，第二段音色匹配 0.89–0.96 vs PDMD 0.72–0.75）；Pika Flex 每 12 段 15 s 有 233 个定格帧需 de-stutter；后段声音发闷改「只续画面、声音重生」；后段变暗变饱和改「只用末帧」。

## 5c. 补读新增（`docs/13-github-survey/10-unread-followup.md`）

- **烧焦有数字**（6 段链第 6 段纹理能量）：REF2VA int8 + lightx2v ref2v 8-step v1.1 = 1.19（几乎不烧）；FastH3 omniref = 2.04；**Larry turbo v4 = +261%（最烂，禁用于续接）**。`Imagineer13/H3-Anti-Burn-LoRA` 只挂第 2 段起，`LoraLoaderModelOnly` 0.5 起步，不合并进 int8；`context_noise` 可把 2.04 压到 1.75。
- **帧网格精确规则**：全片 5+17k；AV 续接上下文只能 **39+51k**（39/90/141/192；56 不是合法上下文）；静帧钉位 17k（0-based）；中段插入偏移取 51 倍数才音频精确对齐（17 倍数要 8.33 ms 取整）；22 帧 = 7 latent/37 tick，39 帧 = 12/65；音频 feather 默认 8 tick = 0.2 s；请求非法值被静默向下吸附（45 → 39），先自己算好。
- **截尾帧续接**：段尾写 0.8–1.2 s 收束保持；尾帧占第一张参考图槽位，只在「同场景无转场且动作未完成」时续写；转场段用黑场 / 淡化而非人物尾帧。
- FL2VA 首尾帧：尾帧与首帧同机位同构图但**必须是不同图**（动作完成后的姿势）；同一张图做首尾 → 100% 静止。没锁尾帧时加 `LOCKED-OFF STATIC CAMERA on a tripod`。
- 24 GB 实测：VDN-H3-24GB（3090）0.4 MP 5/10/15/20 s = 1:09/2:05/3:21/4:20，0.8 MP 10 s 5:18（需 bat 启动打 block-loop 补丁）。

## 6. 每段结束的检查

- 钉头是否被渲染成定格：Motion-Context `tests/freeze_detect.py`，或本 skill 的 `scripts/qc_probe.py`（freezedetect）。
- 接缝音频：MC `tests/seam_probe.py A.flac B_untrimmed.flac`。
- 亮度/纹理漂移：联络表对比第 1 段与第 N 段的同构图帧。
