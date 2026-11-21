# 04 · 声音、口型与后期自动化工作流（audio-post 簇）

> 调研日期 2026-11-21。方法：GitHub 搜索 API（约 100 次查询）+ `raw.githubusercontent.com` 读 README / 源码 + HuggingFace API 读模型卡与文件清单 + 浅克隆 2 个 H3 音频仓库读节点源码与工作流 JSON + 官方 `Comfy-Org/workflow_templates`（2026-10-31 版）拆节点 + 本机 ffmpeg 6.1.1 实跑滤镜链。
> 口径：星数 / 最后推送为 2026-11-21 快照；速度与显存**全部是作者自报**并标注硬件，本簇没有在 4090 上跑任何模型（标「未验证」）；ffmpeg 命令、剪映草稿 / OTIO 导出、字幕重定时、F0 / 偏移检测原型为本次**实跑通过**（合成素材，见 §7）。
> 用户约束：Windows 11 + RTX 4090 24 GB + 本地 ComfyUI；只能用 HuggingFace / GitHub（ModelScope-only 的权重视为不可用）。

## 0. 本簇结论

1. **主流做法不是「把成片压一遍滤镜」，而是分层 stem**：对白 / 非人声原声 / 环境声底 / 拟音 / 配乐各走各的轨，台词文本锁定、时间由强制对齐给出，最后时间线混音 + sidechain ducking + 两遍 `loudnorm`，同时导出**可编辑工程**（剪映草稿 / OTIO / FCP XML）。VideoLingo、TTS-Audio-Suite、OpenMontage、h3-drama-kit 都是这个骨架。
2. **中文 TTS 第一梯队（本地、能商用）**：IndexTTS-2.5（2026-08，音色-情感解耦 + `duration_factor`）、Fun-CosyVoice3、VoxCPM2（48 kHz）、Qwen3-TTS（VoiceDesign→Clone）、OmniVoice（`duration=` 定长）、GPT-SoVITS V5（1 分钟微调固定声线）。Fish Audio Drama 3 表演最强但 35B（int4 22 GB）且商用限年收入 < 50 万美元；腾讯 AuK 是「改词 / 变调 / 增强 / 定长」的瑞士军刀（需 `--cpu_offload`）。
3. **音色统一**：零样本仍是 seed-vc（已 19 个月未更新，默认 22.05 kHz）；量产更稳的是每角色训 RVC / GPT-SoVITS。**漂移先量化再处理**（中位 F0 差 > 0.5 半音才转），不要全量过 VC。
4. **口型**：只改嘴 = LatentSync 1.6（512 px，≥18 GB）/ MuseTalk 1.5（256 px，实时），都按 25 fps 训练；整段重生成 = InfiniteTalk、LongCat-Video-Avatar 1.6、LTX-2 DubIt。对 H3 而言，「同提示 + 音频锁重拍」比事后改嘴更稳。
5. **音频驱动的统一原理**：把目标音频编进音频 latent 并令其 `noise_mask=0`，只去噪视频（H3 ExactAudioLock、H3 数字人工作流、LTX-2 A2Vid 完全同构）。
6. **对我们最有用的 5 件事**：① `Qwen3-ForcedAligner-0.6B` 做「原文锁定、只借时间」的字幕（VideoLingo 默认已从 WhisperX 换成它）；② `MiniMaxH3DialogueAudioLock` + `Finalize` 让 TTS 对白逐采样精确、环境声仍由 H3 生成；③ 定长 TTS（OmniVoice `duration` / AuK `gen_seconds` / IndexTTS `duration_factor`）；④ 时间线混音滤镜图（`adelay+afade+amix+sidechaincompress` + 两遍 `loudnorm`，实跑 −14.0 LUFS、音画同长）；⑤ `pyJianYingDraft` / OpenTimelineIO 导出可编辑工程（原型实跑）。
7. **许可陷阱**：MMAudio 权重 CC-BY-NC、F5-TTS 权重 CC-BY-NC、Fish S2-Pro Research License、AuK 依赖的 Qwen2.5-Omni-3B 为 qwen-research、Echo-TTS / Sonic 非商用；ComplexSync 权重只在 ModelScope。
8. **显存纪律**：音频模型（5–17 GB）不能与 H3（占满 24 GB）同驻；音频批处理必须排在 ComfyUI `/free` 之后的独立阶段。

## 1. 工作流图谱

### 1.0 总图：声音后期的层与总线

```
            ┌─ 对白 stem（H3 原声 → 分离 → [VC 统一] 或 TTS 重配）──┐
H3 take ────┤                                                      ├─► 对白总线 −16 LUFS ─┐
(24 fps,    └─ 非人声 stem（动作声 / 原生环境）─────────────────────┘                       │ sidechain key
 32 kHz)                                                                                    ▼
 环境声底（每场景一条 room tone，−32…−48 dB，只填缺口）──────────────────────────────► 混音总线 ─► 两遍 loudnorm
 拟音补洞（V2A：HunyuanVideo-Foley / PrismAudio；T2A：Stable Audio 3 sfx）────────────►   │        −14 LUFS / −1.5 dBTP / LRA 11
 配乐（ACE-Step 1.5，时长 = 成片，BPM 写进 tags）──► sidechaincompress（对白处 −8…−12 dB）─┘        48 kHz AAC 320k
 字幕：锁定原文 + 强制对齐时间 → ASS（中 58 px / 英 36 px @1080p）→ 烧录 或 剪映草稿文本轨
 工程：edl.json → 剪映草稿 / .otio / FCP7 XML / CMX3600 EDL
```

三条链路的差别只在「对白 stem 从哪来、画面要不要动」：A 不动画面只修声音；B 换声音并改画面的嘴；C 先定声音再生成画面。

### 1.1 链路 A：保留 H3 原生对白，只做音色统一 + 响度 + 环境声 + 配乐 + 字幕

| 步 | 输入 → 输出 | 工具 / 命令 / 参数 |
|----|------------|-------------------|
| A0 | `selects/ep01/segNN.mp4`、`episodes/ep01.json`、`bible/voices/<角色>.wav`（用户认可的 H3 原声 ≥ 6 s） | 现有 `qc_probe.py` 通过后才进本链路 |
| A1 | mp4 → `segNN.wav`（48 kHz 24-bit） | `ffmpeg -i segNN.mp4 -vn -af aresample=48000 -c:a pcm_s24le segNN.wav`（H3 原生 32 kHz，统一升到 48 k 再做任何处理） |
| A2 | `segNN.wav` → `(Vocals)` + `(Instrumental)` | `audio-separator segNN.wav --model_filename model_bs_roformer_ep_317_sdr_12.9755.ckpt --output_dir stems/`；ComfyUI 内：`MelBandRoFormerModelLoader(MelBandRoformer_fp16.safetensors)` → `MelBandRoFormerSampler`，或核心 `AudioStemSeparate(htdemucs)` |
| A3 | Vocals + 锁定台词 → 每句时间 | `Qwen3ForcedAligner.from_pretrained("Qwen/Qwen3-ForcedAligner-0.6B").align(audio, text, language="Chinese")`；按 `[首字 −0.08 s, 末字 +0.18 s]` 切句，说话人取自分镜 JSON（一镜一人开口） |
| A4 | 每句 → 漂移表 | 中位 F0（自相关，70–400 Hz）与锚点比：`12·log2(f/f_ref)`；\|Δ\| ≤ 0.5 半音且听感一致 → 跳过 A5 |
| A5 | 漂移句 → 统一音色句 | `python inference.py --source line.wav --target bible/voices/xia.wav --output vc/ --diffusion-steps 30 --length-adjust 1.0 --inference-cfg-rate 0.7 --f0-condition True --auto-f0-adjust True --semi-tone-shift 0 --fp16 True`（seed-vc 44.1 kHz F0 条件模型：语调跟原表演走、音域平移到锚点；首选项，未在 H3 素材实测，需与默认 22.05 kHz 模型 A/B） |
| A6 | 回填 + 守时 | 时长差 ≤ 1 帧（41.7 ms）；5 ms 包络互相关偏移 ≤ 20 ms，否则整句平移；句首尾 10 ms 淡变贴回原位置 |
| A7 | （可选）对白清理 | NVIDIA RE-USE（9.6 M，去噪/去混响/修削波）或 DeepFilterNet；`highpass=f=80` |
| A8 | 逐 take 响度 | 对白 stem 两遍 `loudnorm` 到 −16 LUFS（`linear=true`，输出补 `aresample=48000`）；非人声 stem 用同一线性增益 |
| A9 | 环境 / 拟音 | 每场景一条 room tone（Stable Audio 3 small-sfx 或 MOSS-SoundEffect v2，≤ 30 s 循环）；无声动作镜用 HunyuanVideo-Foley XL（offload 8 GB）/ PrismAudio |
| A10 | 配乐 | ACE-Step 1.5 XL turbo（ComfyUI 原生）：`TextEncodeAceStepAudio1.5(tags, lyrics, bpm=90, duration=成片秒数, timesignature='4', keyscale='A minor', generate_audio_codes=True)` + `EmptyAceStep1.5LatentAudio(seconds=成片秒数)`，KSampler 8 步 cfg 1 euler/simple，`ModelSamplingAuraFlow 3`；纯器乐在 tags 写乐器、歌词框写 `[instrumental]`（v1 官方器乐模板写法，1.5 未验证） |
| A11 | 时间线混音 | `mix_episode.py`（§4.1）：L-cut 0.25 s、淡出 120 ms、环境底 −34 dB、`sidechaincompress=threshold=0.05:ratio=4:attack=20:release=400:knee=4`（合成信号实测压 8.4 dB；`0.03/8` 压 13.7 dB）、成片两遍 `loudnorm I=-14:TP=-1.5:LRA=11` |
| A12 | 字幕 | `retime_subtitles.py`（§4.3）→ `ep01.srt` / `ep01.ass` → `-vf subtitles=ep01.ass` 烧录或进剪映文本轨 |
| A13 | 交付 | 视频 lanczos 到 1920×1080、bt709、GOP = fps/2、2 个 B 帧、faststart；`export_capcut_draft.py` / `export_otio.py` 同时出工程 |

要点：A 链路**不改画面**，所以任何改变时长的处理（VC 的 `length-adjust`、变速、去静音）都禁止；每一步之后都要保证「帧数不变、对白起点不变」。

### 1.2 链路 B：TTS / 克隆重配对白，并对已有 H3 视频改口型

| 步 | 输入 → 输出 | 工具 / 命令 / 参数 |
|----|------------|-------------------|
| B1 | 角色声线资产（一次性） | 有认可原声 ≥ 6 s → 直接当克隆参考；没有 → Qwen3-TTS `generate_voice_design(text, language, instruct)` 出参考再 `create_voice_clone_prompt`；长连载 → GPT-SoVITS V5 每角色 1 分钟微调 |
| B2 | 原 take 对白 → 每句时间窗 `D_i` | A2 + A3（分离 + 强制对齐）；无声样片可用 TTS-Audio-Suite `Silent Speech Analyzer`（MediaPipe 看嘴动出 SRT） |
| B3 | 文本 + 声线 + `D_i` → 定长配音 | **IndexTTS-2.5**：先自然合成量时长 `n_i`，再 `duration_factor = clamp(D_i / n_i, 0.85, 1.15)`；`emo_audio_prompt = 原句 vocals`、`emo_alpha 0.6–0.8`（借原表演的情绪，音色用锚点）。**OmniVoice**：`model.generate(text, ref_audio, ref_text, duration=D_i, num_step=32)`。**AuK**：`auk-infer --audio ref.wav --instruction "Say the following with the same voice: '…'" --gen_seconds D_i --cpu_offload`。ComfyUI：`Unified 📺 TTS SRT`（timing mode `smart_natural`，`max_stretch_ratio` 调到 1.5） |
| B4 | 每句 2–3 seed → 选 take | ASR 回读（Qwen3-ASR 1.7B / faster-whisper large-v3）与锁定原文字符相似度 ≥ 0.90；`H3ExactAudioLockAudioReviewGate` 或人工审听 |
| B5 | 新对白 stem + 原非人声 stem | 按原句起点贴回（`adelay`），保留 A2 的 (Instrumental) |
| B6 | 画面改嘴（四选一，见下） | LatentSync / MuseTalk / H3 重拍 / 整段 V2V |
| B7 | 口型 QC | 帧数相等；`syncnet_python` 置信度或「嘴开合–音频包络」相关；人眼看牙齿与糊边 |
| B8 | 混音 → 字幕 → 交付 | 同 A8–A13（TTS 已干净，A7 可省） |

B6 的四个选项：

1. **LatentSync 1.6 只改嘴（真人中近景首选）**：先把 24 fps 素材**逐帧重打时间戳成 25 fps**（不重编码、帧一一对应），音频同比例加速：
   `ffmpeg -itsscale 0.96 -i seg.mp4 -an -c:v copy -video_track_timescale 25000 seg25.mp4`；
   `ffmpeg -i new_dialogue.wav -af atempo=1.0416667 -ar 16000 -ac 1 a25.wav`；
   `python -m scripts.inference --unet_config_path configs/unet/stage2_512.yaml --inference_ckpt_path checkpoints/latentsync_unet.pt --inference_steps 20 --guidance_scale 1.5 --enable_deepcache --video_path seg25.mp4 --audio_path a25.wav --video_out_path out25.mp4`；
   `ffmpeg -itsscale 1.0416667 -i out25.mp4 -an -c:v copy -video_track_timescale 24000 out24.mp4`，最后混回**原速**音频。（重打时间戳往返已实跑：144 帧 → 144 帧，6.000 s。）
2. **MuseTalk 1.5**（MIT、实时级、脸区 256 px）：中远景、批量、预览用；特写会糊。
3. **H3 重拍（最稳）**：原首帧作 `first_frame` 锚 + 同提示词 + `MiniMaxH3TimedAudio → MiniMaxH3DialogueAudioLock`（即链路 C 的做法）。画面是新 take，但开场帧、人物、台词时间全部受控。
4. **整段 V2V**：InfiniteTalk V2V（Wan2.1 14B，连头和身体一起重生成，镜头只是「模仿」原片）、LTX-2.3 `DubItPipeline`、Chanjing-Avatar V2V 5B（只重生成脸区，Linux）。24 GB 上都要 offload / GGUF，速度未验证。

### 1.3 链路 C：先做整条音轨（对白 + 节拍），再让视频按音轨生成

| 步 | 输入 → 输出 | 工具 / 命令 / 参数 |
|----|------------|-------------------|
| C1 | 剧本台词 → 全部对白 wav | B1 的声线 + 任一 TTS（此时不必定长，取最自然的 take）；逐句 ASR 回读 + 审听门 |
| C2 | 对白 wav 时长 → 分段表 | `audio_lock_plan.py`（§4.8）：每句 `start_frame ≥ 18`（0.75 s 预卷，skill 既有规则）、句尾留 ≥ 0.2 s + 1 s 定格；段长吸附 `17k+5`（124 / 141 / 158 … ≤ 328 帧） |
| C3 | 配乐与节拍 | ACE-Step 1.5 先出整集配乐（tags 写 BPM）；`beat_grid.py` 给出拍点；硬切点落在 1/4 或 1/8 拍 ±2 帧 |
| C4 | 对白段生成（要环境声） | `MiniMaxH3TimedAudio(start_frame, gain_db 0)` → `MiniMaxH3DialogueAudioLock(mix_policy=prevent_clipping, overflow_policy=error, protect_before_ms=200, protect_after_ms=250, feather_ms=100)`；同一 `start_frame` 接 `MiniMaxH3AddGuide.frame_idx` 并喂同一段 audio；提示词里照常写同一句 `<d>…</d>` 和说话人归属；采样后 `VAEDecodeAudio + dialogue_reference_audio + dialogue_lock_manifest → MiniMaxH3DialogueAudioFinalize → final_audio` |
| C5 | 歌曲 / MV / 纯口播段（整条锁） | `MiniMaxH3ExactAudioLock(mix_policy=sum, overflow_policy=error)`；成片音轨接 `exact_audio`（不是 `VAEDecodeAudio`）；长口播用 `caitongbo/ComfyUI-MiniMaxH3-LongVideo-DigitalHuman`（960×544×362 帧 ≈ 15.08 s / 段，39 帧画面前缀，≤ 20 段） |
| C6 | 不装节点的退路 | 六段式里 `<Audio 1>: fully_copy`（语音有约 0.45 s 系统位移，须在排期里预补）；只要音色用 `<Audio 1>: attribute_transfer (voice timbre only)` |
| C7 | H3 做不好时 | 口播 / 唱歌：LongCat-Video-Avatar 1.6（MIT，int8 15.97 GB，ComfyUI 原生）；多人对话：InfiniteTalk / MultiTalk；音频反应式：LTX-2 `A2VidPipelineTwoStage`、HuMo |
| C8 | 拼接混音 | 对白已是干净 TTS：跳过 A2–A7，直接 A8–A13；`Finalize` 之外的 H3 环境声作为非人声 stem |

### 1.4 三条链路比较

| 维度 | A 保留原声 | B 重配 + 改嘴 | C 先音后画 |
|------|-----------|--------------|-----------|
| 对白表演 | H3 原生表演，最自然；音色靠 VC 拉齐 | TTS 表演受模型上限（IndexTTS 情感参考可部分继承原表演） | TTS 表演；但画面表演是「听着这段声音」生成的，声画情绪一致 |
| 口型 | H3 原生，不动 | 最大风险点：改嘴糊 / 牙齿 / 侧脸失败 / 动漫脸检测失败 | H3 按锁定音频生成，时间逐采样精确；谁张嘴靠提示词 |
| 音色一致 | 取决于 VC；极端情绪句可能转坏 | 全集同一把嗓子 | 全集同一把嗓子 |
| 台词可控 | 只能抽卡（现有 Whisper 门禁） | 文本 100% 可控，可改词、可换语言 | 文本 100% 可控 |
| GPU 遍数 / 段 | 分离 1 + VC ≤ 1（都远小于一次 H3 采样） | TTS 1 + 改嘴 1（或重拍 1 次 H3） | TTS 1 + H3 1（本来就要生成） |
| 人工环节 | 听 VC 结果 | 听 TTS + 逐镜看嘴 | 听 TTS（在花 GPU 之前） |
| 主要风险 | VC 引入金属声 / 损高频（22 kHz 模型）；分离残留 | 两次生成误差叠加；24↔25 fps 处理出错即音画漂移 | 音频锁 + 8 步 Turbo 时画面运动变少（未验证）；多说话人归属错人 |
| 适用类型 | **对白短剧（真人向）首选**；已出片只想救声音 | 已有满意画面但台词必须改 / 译制 / 换语言；真人口播补救 | **漫剧、MV、口播、广告、多语言版本**；台词密、要卡点的集 |

选择规则：能 A 不 B；确定要换声音就**在生成前**决定（走 C），不要先生成再走 B；B 只用于「画面不可重拍」的补救。

### 1.5 业界参照链（别人怎么做）

- **VideoLingo 译配**（★19339，Apache-2.0）：Qwen3-ASR + Qwen3-ForcedAligner（逐词）→ NLP / LLM 断句 → 翻译 → TTS（GPT-SoVITS / F5 / CosyVoice2 / Fish）→ 变速对齐 → 混回背景声。README 自己写明「变速不保证自然与完全同步」「不自动分配多说话人音色」。
- **TTS-Audio-Suite SRT 流**（ComfyUI）：`✏️ ASR Transcribe`（Qwen3-ASR / Granite）→ `Text to SRT Builder` → `Unified 📺 TTS SRT`（`stretch_to_fit` / `pad_with_silence` / `smart_natural`，相位声码器拉伸，默认 0.5–2.0×）→ `Adjusted_SRT` 回写。
- **LTX-2 一体化**：`A2VidPipelineTwoStage`（冻结音频出画面）、`DubItPipeline`（IC-LoRA，改台词同时保身份与口型）、`RetakePipeline`（只重生成一个时间窗，音 / 画可独立）——「用联合音画模型自己修自己」是 2026 年的新范式，H3 生态的 ExactAudioLock / AudioRefine / FaceRefine 是同一思路。
- **官方 ComfyUI 模板（2026-10-31）**：`templates-wan2_1_infinitetalk_music.json`（`AudioSeparation` → `MultiTalkWav2VecEmbeds` 25 fps → `WanVideoImageToVideoMultiTalk` 832×480×81 帧、motion 9 帧 → `WanVideoSampler` 7 步 cfg 1 shift 11 dpm++_sde + lightx2v LoRA）、`video_humo.json`（`humo_17B_fp8` + `whisper_large_v3_fp16`，640×640×97，6 步 uni_pc）、`video_ltx_2_audio_to_video.json`。驱动前先做人声分离是通行做法。

## 2. 逐项目 / 逐工具

评级：**采用** = 写进默认链路；**试用** = 值得做一次 A/B；**观望** = 有前景但当前不可落地；**跳过** = 许可 / 停更 / 被取代。

### 2.1 TTS / 声音克隆 / 情感控制

| 项目（快照） | 最新版 | 许可（商用） | 权重 | 显存 / 速度（作者口径） | 中文 | 时长控制 | 情感控制 | ComfyUI | 评级 |
|---|---|---|---|---|---|---|---|---|---|
| IndexTTS（★25220） | 2.5，2026-08-10 | bilibili Model License：可商用，MAU > 1 亿或年收入 > 10 亿元需另授权 | 5.49 GB | RTF 0.21（4090，bf16） | 一等，拼音纠音 | `duration_factor` 0.5–2.0 | 情感参考音频 / 8 维向量 / 文本 | TTS-Audio-Suite；chenpipi0807/ComfyUI-Index-TTS | 采用 |
| Fun-CosyVoice3（★24468） | 0.5B-2512，2025-12 | Apache-2.0 | 9.75 GB（实际用 ~5 GB） | 流式首包 150 ms；4090 RTF 未见 | 一等，+18 方言 | 仅 instruct 语速 | instruct + `[breath]` `[laughter]` | TTS-Audio-Suite | 采用 |
| VoxCPM2（★42841） | 2026-04 | Apache-2.0 | 4.96 GB | ~8 GB；RTF ~0.30（4090） | 好，+9 方言，48 kHz | 无（括号风格词） | `(cheerful tone)` 前缀 | wildminder/ComfyUI-VoxCPM | 采用 |
| Qwen3-TTS（★14560） | 1.7B / 0.6B，2026-01-22 | Apache-2.0 | 4.5 GB / 个 | 流式 97 ms；4090 RTF 未见 | 好，北京 / 四川音色 | instruct | instruct；VoiceDesign | flybirdxx/ComfyUI-Qwen-TTS（★1981） | 采用（造声线） |
| OmniVoice（★16741） | 2026-03 起，push 2026-11-20 | Apache-2.0 | 3.27 GB | RTF 低至 0.025（H100 批量口径） | 好，方言，拼音纠音 | **`duration=` 秒** / `speed=` | 标签 + instruct | Saganaki22/ComfyUI-OmniVoice-TTS | 采用（定长） |
| GPT-SoVITS（★64157） | V5，push 2026-11-11 | MIT | — | RTF 0.014（4090，v2 ProPlus） | 一等 | 语速 | 由参考音频决定 | 无主流节点（API） | 采用（长连载） |
| AuK / AuK-Flash（★1614） | 2026-09-09 | 权重 MIT；编码器 Qwen2.5-Omni-3B = qwen-research | 6.76 + 11.99 GB | 16.98 GiB（`cpu_offload`，A800） | 支持（中英模板） | **`gen_seconds`** | 8 类情感**编辑** | 自带 `ComfyUI-AuK` | 试用 |
| Fish Audio Drama 3（★33817） | 2026-10-13 | Fish Community：年收入 < 50 万美元可商用，禁托管服务 | 41.5 GB；int4 22.1；GGUF Q4 20.6 | RTF 0.131（H200）；4090 未验证 | 一等，83 语，16 角色 | — | 内联标签 + 多轮导演改稿 + infill | 官方 API 模板 `api_fishaudio_drama3_*` | 观望 |
| MOSS-TTS（★4355） | v1.5，2026-05-26 | Apache-2.0 | 17 GB（8B）；GGUF | llama.cpp 下 8 GB 卡可跑 | 好，31 语 | **`tokens=`**；`[pause 3.2s]` | 标点驱动 | TTS-Audio-Suite | 试用 |
| FireRedTTS3（★1724） | 2026-08-13 | Apache-2.0 | 20.8 GB（Base + Instruct） | 未见 | 好，+21 方言 | 编辑 speed 0.5–2.0 | voice design + 编辑 | Saganaki22/FireRedTTS3-ComfyUI | 观望 |
| Chatterbox（★28013） | Multilingual V3 | MIT（仓库已声明归档无支持） | 2.14 GB / T3 | 未见 | 一般（有 zh-cmn 专包） | — | exaggeration / cfg | 官方模板 `audio-chatterbox_*`（FL 节点，含 VC） | 试用（VC） |
| F5-TTS（★15633） | v1，2025-03 | 代码 MIT，**权重 CC-BY-NC** | ~1.2 GB | 快 | 好 | `fix_duration` | — | niknah/ComfyUI-F5-TTS | 跳过 |
| Fish S2-Pro | 2026-03 | **Research License** | 11 GB | RTF 0.195（H200） | 一等 | — | 标签 | TTS-Audio-Suite | 跳过 |
| Spark-TTS / MegaTTS3 / VibeVoice-TTS | 2025 | Apache / MIT | — | — | 中英 | — | — | 旧节点 | 跳过 |

基准参照（都是各家 README 的自测表，口径不同不可横比）：Seed-TTS-eval test-zh CER / SIM —— CosyVoice3-2512 RL 0.81 / 77.4、VoxCPM2 0.97 / 79.5、Index-TTS2 1.03 / 76.5、Fish S2 0.54 / —、MiniMax-Speech（闭源）0.83 / 78.3；CV3-Eval zh WER / SS（IndexTTS 表）—— IndexTTS2.5-RL 3.93 / 77.92、CosyVoice3-0.5B 3.84 / 80.01、Qwen3-TTS 3.27 / 73.02、Fish S2 Pro 3.62 / 67.79。结论只取定性的：**相似度看 CosyVoice3 / IndexTTS，可懂度看 Fish / Qwen3，都已到「听不出明显错」的区间，选型看控制能力与许可。**

#### IndexTTS-2.5（index-tts/index-tts）
- **定位**：B 站出品的工业级零样本 TTS，短剧配音社区事实标准（B 站 H3 课程里「IndexTTS 单句配音」就是它）。
- **机制**：自回归 GPT 出语义 token → s2mel → BigVGAN；音色提示与情感提示解耦；2.5 用 Qwen 0.6B 做文本→情感（`qwen0.6bemo4-merge`）。
- **关键参数**：`IndexTTS2(cfg_path, model_dir, use_bf16=True[, use_qwen_emo=True])`；`infer(spk_audio_prompt, text, lang="ZH", output_path, emo_audio_prompt=None, emo_alpha=1.0, emo_vector=[喜,怒,哀,惧,厌,郁,惊,静], use_emo_text=False, emo_text=None, duration_factor=1.0, use_random=False)`；纠音 `银<行|HANG2>`。
- **硬件 / 速度**：权重 5.49 GB；4090 `kv_cache` RTF 0.2065（7 字短句 0.287）；2.0 fp16 为 0.3257（作者自报）。
- **许可**：bilibili Model Use License——普通工作室可商用；不得拿输出去改进其他商用模型。
- **价值**：`emo_audio_prompt` 可以直接喂 H3 原句（借表演）、`spk_audio_prompt` 喂角色锚点（定音色）；`duration_factor` 做 ±15% 的贴窗。注意 2.0 README 里的「精确时长控制」至今写着 not yet enabled，2.5 只有倍率。`use_random=True` 会降相似度，别开。
- **评级**：**采用**（链路 B / C 的默认中文 TTS）。

#### Fun-CosyVoice 3.0（QwenAudio/CosyVoice，原 FunAudioLLM）
- **定位**：阿里的 LLM-TTS，方言 / 跨语种最全，Apache-2.0 最干净。
- **机制**：文本 LLM 出 25 Hz 监督语义 token → flow matching → HiFT；RL 版 `llm.rl.pt` 降错字率。
- **关键参数**：`AutoModel(model_dir='pretrained_models/Fun-CosyVoice3-0.5B')`；`inference_zero_shot(text, 'You are a helpful assistant.<|endofprompt|>参考音频的文本', prompt_wav)`；`inference_instruct2(text, 'You are a helpful assistant. 请用广东话表达。<|endofprompt|>', prompt_wav)`；`[breath]`、`[laughter]`；拼音热修 `[j][ǐ]`；日语须先转片假名。
- **硬件 / 速度**：0.5B；仓库 9.75 GB（含 ONNX 双份）；官方只给流式延迟 150 ms，4090 RTF 未见。最后推送 2026-05-25，3.0 之后无新模型。
- **价值**：方言角色（四川 / 东北 / 粤语）首选；`CosyVoice-300M` 的 `inference_vc(source, prompt)` 可当备用 VC。
- **评级**：**采用**（方言与许可敏感项目）。

#### VoxCPM2（OpenBMB/VoxCPM）
- **定位**：无 tokenizer 的扩散自回归 TTS，直接出 **48 kHz**，README 明写「free for commercial use」。
- **机制**：LocEnc → TSLM → RALM → LocDiT，在 AudioVAE V2 连续 latent 上自回归；参考只要 16 kHz。
- **关键参数**：`VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)`；`generate(text, reference_wav_path=None, prompt_wav_path=None, prompt_text=None, cfg_value=2.0, inference_timesteps=10, seed=42)`；声音设计 / 风格写在文本开头的括号里 `(A young woman, gentle and sweet voice)…`；CLI `voxcpm clone --text … --reference-audio … --output …`，`--timestamps --timestamp-level char --timestamp-language zh`（内部调 stable-ts）。
- **硬件 / 速度**：2B，权重 4.96 GB，~8 GB 显存，RTF ~0.30（4090）/ ~0.13（Nano-vLLM）。支持 LoRA 微调。
- **价值**：音质上限最高、不用再做超分；没有显式时长控制，适合链路 C（先音后画）。
- **评级**：**采用**（链路 C 的高保真选项）。

#### Qwen3-TTS（QwenLM/Qwen3-TTS）
- **定位**：三件套——`VoiceDesign`（一句描述造音色）、`CustomVoice`（9 个预置音色 + 情感指令）、`Base`（3 秒克隆）。
- **关键参数**：`Qwen3TTSModel.from_pretrained(id, device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="flash_attention_2")`；`generate_voice_design(text, language="Chinese", instruct="…")`；`generate_voice_clone(text, language, ref_audio, ref_text)`；`create_voice_clone_prompt(ref_audio, ref_text, x_vector_only_mode=False)` 复用。
- **价值**：官方文档化的 **「Voice Design then Clone」**：先用 VoiceDesign 生成一段目标音色，再作 Base 的克隆提示批量出句——没有真人样本也能给每个角色定一把固定嗓子，且全程 Apache-2.0。ExactAudioLock 仓库的三份 Qwen3-TTS 示例工作流就是这个用法（`FB_Qwen3TTSVoiceDesign` 两个 seed → 审听门 → 锁）。
- **硬件**：1.7B 每个模型 ~4.5 GB；仓库最后推送 2026-03-17。
- **评级**：**采用**（系列圣经「音色」一栏的生成器）。

#### OmniVoice（k2-fsa/OmniVoice）
- **定位**：k2 团队的 600+ 语零样本 TTS，离散扩散语言模型式的**非自回归**结构。
- **关键参数**：`model.generate(text, ref_audio, ref_text, instruct="female, low pitch, 四川话", num_step=32, speed=1.0, duration=10.0)`——`duration`（秒）直接固定输出长度并覆盖 `speed`；非语言标签 `[laughter] [sigh] [surprise-ah]…`；中文可用带调号拼音纠音。
- **硬件 / 速度**：权重 3.27 GB；README 自报 RTF 低至 0.025（批量、H100、fp16 口径）。
- **价值**：链路 B 的「把这句话塞进 2.4 秒」只需一个参数；非自回归模型给太短的时长会吞字，建议 `D_i ≥ 字数 / 6.5 s`，超出就改词而不是硬压（未验证阈值）。
- **评级**：**采用**（定长配音首选），与 IndexTTS-2.5 做同句 A/B。

#### GPT-SoVITS V5（RVC-Boss/GPT-SoVITS）
- **定位**：5 秒零样本 / **1 分钟少样本微调**；中文社区保有量最大（★64157，MIT）。
- **要点**：v2Pro 系对一般音质训练集鲁棒，v3 / v4 更贴参考音频；V5「不微调 SoVITS 也显著提升相似度」并换了声码器，分支 `cuda_graph_accel_v5`，权重 `lj1995/GPT-SoVITS/gsv-v5-pretrained`。自报 RTF 0.014（4090）/ 0.028（4060Ti）。自带 UVR 分离、切分、ASR 打标的数据准备 WebUI。
- **价值**：每个主角用 1 分钟认可素材微调，得到**全季固定声线**，比零样本克隆逐句漂移小；训练素材可以就是链路 A 里筛出的好句。
- **评级**：**采用**（≥ 10 集的连载）。

#### AuK / AuK-Flash（Tencent-Hunyuan/AuK）
- **定位**：1.5B「语音生成 + 编辑」统一模型，全部任务走一句自然语言指令。
- **机制**：DiT + layer fusion，Qwen2.5-Omni-3B 当多模态编码器，独立 VAE；Flash 版 4 步、CFG 0。
- **关键参数**：`auk-infer --audio X --instruction "…" --output Y [--gen_seconds S] [--cpu_offload] [--ckpt ckpts/AuK-Flash/auk_flash.safetensors]`。模板：零样本 TTS `Say the following with the same voice: "…"`；改词 `把‘原文’改成‘新文’`；`将音调升高 2 个半音`；`将语速调整为 1.25 倍`；`将情感转变为愤怒`；`请保留所有说话人，去除噪声和混响，输出等长的纯净语音`；`只保留第 2 个开始说话的人`。
- **硬件**：不开 offload 峰值 24.8–25.0 GiB，`--cpu_offload` 16.75–16.98 GiB（A800，bf16）；ComfyUI 节点 `AuK Model Loader` / `AuK Generate / Edit`，**源 + 目标合计 ≤ 30 s**，输入被平均成单声道。
- **许可**：AuK 权重 MIT，但运行必须加载的 Qwen2.5-Omni-3B 在 HF 上标 `qwen-research`——商用前先核实。
- **价值**：三个别处没有的能力——① H3 原声**改一个词**不重抽（`gen_seconds` 设成原句长度以保口型大体不动）；② 半音级变调直接修「每段漂 1.7 半音」；③ 一条指令去混响 / 修削波。
- **评级**：**试用**（先在非商用样片验证改词与变调质量）。

#### Fish Audio Drama 3 / S2-Pro（fishaudio/fish-speech）
- **定位**：Drama 3 是目前唯一明确以「戏剧表演」为目标的开源 TTS：一段文本 16 个 `<|speaker:N|>`，`[whisper] [angry] [laughing]` 内联标签，`previous_takes` 多轮导演改稿（「再温柔一点、带点难过」），单词级 infill。
- **现实约束**：35B-A3B MoE，原权重 41.5 GB；`fishaudio/drama-3-int4` 22.1 GB（卡片自述为非官方量化，需 SGLang-Omni、sm80+，Linux）；GGUF Q4_K_M 20.56 GB / Q2_K 17 GB。所有速度数字来自 H200。24 GB 卡上无法与任何东西同驻，Windows 路径未验证。
- **许可**：Fish Audio Community License v1.0——年总收入 < 50 万美元可商用、禁做托管服务、分发需标 "Built with Fish Audio"；S2-Pro 权重仍是 Research License。
- **评级**：Drama 3 **观望**（先用 ComfyUI API 模板 `api_fishaudio_drama3_directed` 试表演上限）；S2-Pro **跳过**。

#### MOSS-TTS 家族 / FireRedTTS3 / Chatterbox / Step-Audio-EditX（合并）
- **MOSS-TTS v1.5**（Apache-2.0）：`processor.build_user_message(text=…, reference=[wav], tokens=325)` 的 `tokens` 是 token 级时长控制，`[pause 3.2s]` 显式停顿；同家族 MOSS-TTSD（多说话人对话）、MOSS-VoiceGenerator（造音色）、**MOSS-SoundEffect v2.0**（48 kHz 音效 ≤ 30 s）。8B 模型靠 llama.cpp + ONNX 在 8 GB 卡跑。**试用**（需要逐 token 定长时）。
- **FireRedTTS3**（Apache-2.0）：24 语 + 21 种中文方言克隆；Instruct 版的声学编辑模板固定（`adjust the speed to X` / `shift the pitch by N step(s)` / `adjust the volume to X`）。**观望**。
- **Chatterbox**（MIT，README 声明仓库归档）：官方 ComfyUI 模板带 `FL_ChatterboxVC(input_audio, target_voice)`——在 ComfyUI 里做参考式 VC 最省事的入口。**试用**（只为 VC）。
- **Step-Audio-EditX**（Apache-2.0，8.3 GB）：对已生成的语音做二次情感 / 风格编辑（14 情感、32 风格），TTS-Audio-Suite 里是独立的 Second Pass 节点。**试用**（TTS 太平时补情绪）。

#### 商业对照（未实测，仅作质量参照）
- **MiniMax Speech**：官方 MCP（MiniMax-AI/MiniMax-MCP）暴露 `text_to_audio` / `voice_clone` / `voice_design`；开源论文表里它的 Seed-TTS zh CER 0.83、SIM 78.3，与 CosyVoice3-RL 同档。
- **ElevenLabs / Fish Audio / HeyGen / VEED / sync.so**：ComfyUI 官方模板已有 API 节点（`api_elevenlabs_v4_text_to_dialogue`、`api_elevenlabs_speech_to_speech`、`api_elevenlabs_voice_isolation`、`api_veed_lipsync_2_0`、`api_veed_dubbing`、`api_sync_so_talking_image`）。本地链路某一环卡住时可单点替换；价格与条款未核实。

#### ComfyUI 集成：diodiogod/TTS-Audio-Suite v5.11.0
- **定位**：20 个引擎的统一 TTS / VC / ASR / 字幕节点包（★1270，代码 MIT，各引擎各自许可），2026-11-19 仍在更新。
- **覆盖**：IndexTTS 2 / 2.5、CosyVoice3、Qwen3-TTS、OmniVoice、MOSS-TTS、MOSS-SoundEffect v2、Fish S2 Pro、Higgs v3、VibeVoice、F5、Chatterbox（V1–V3）、Step-Audio-EditX、RVC（含训练）、Qwen3-ASR、Granite ASR。模型自动下到 `ComfyUI/models/TTS/…`。
- **关键节点**：`Unified 📺 TTS SRT`（按 SRT 生成，`stretch_to_fit` / `pad_with_silence` / `smart_natural`，`max_stretch_ratio` 默认 2.0、`min_stretch_ratio` 0.5，输出 `Adjusted_SRT`，段级缓存只重算改动句）；`Unified 🔄 Voice Changer`（RVC / ChatterBox VC / CosyVoice VC，迭代 1–30 遍，建议 1–5）；`✏️ ASR Transcribe` + `Text to SRT Builder`；`Silent Speech Analyzer`；角色切换语法 `[Alice] 台词`。
- **注意**：主环境要求 Transformers 5，老引擎走隔离运行时——装进跑 H3 的同一个 ComfyUI 前先在副本环境验证依赖；`stretch_to_fit` 是 CPU 相位声码器，拉伸超过 ±15% 明显劣化。
- **评级**：**采用**（作为 ComfyUI 内的 TTS / VC 统一入口；批量仍建议走独立 venv 脚本）。

### 2.2 变声 / 音色统一

| 项目 | 状态 | 许可 | 需要训练 | 输出采样率 | ComfyUI | 评级 |
|---|---|---|---|---|---|---|
| seed-vc（Plachtaa，★3906） | 最后推送 2025-04-20 | GPL-3.0（代码与 HF 权重） | 否（可 100 步微调） | 22.05 kHz（VC）/ 44.1 kHz（F0 条件） | billwuhao/ComfyUI_Seed-VC（★68） | 采用（零样本） |
| RVC（★39231）/ Applio（★4048，push 2026-11-19） | 活跃 | MIT | 是（每角色 ≤ 10 分钟数据） | 40 / 48 kHz | TTS-Audio-Suite 内置推理 + 训练 | 采用（量产） |
| ChatterboxVC | 归档 | MIT | 否 | 24 kHz 级（未核对） | 官方模板 `FL_ChatterboxVC` | 试用 |
| CosyVoice `inference_vc` | 稳定 | Apache-2.0 | 否 | 22–24 kHz | TTS-Audio-Suite（10 遍迭代） | 试用 |
| AuK 变调 / 音色编辑 | 新 | MIT + qwen-research 编码器 | 否 | — | ComfyUI-AuK | 试用 |
| OpenVoice V2（★38297） | 2025-04 停更 | MIT | 否 | 22 kHz | 旧 | 跳过 |
| MeanVC2 / X-VC | 2026 论文代码 | 未标 / MIT | 否 | — | 无 | 观望 |

#### seed-vc（Plachtaa/seed-vc）
- **定位**：零样本语音 / 歌声转换，参考 1–30 s；我们 skill 现有规则「原生对白每段漂 1.7 半音，用 seed-vc 统一」指的就是它。
- **机制**：内容编码器（Whisper-small / XLSR / ASTRAL 量化）+ U-ViT 扩散 + BigVGAN / HIFT 声码器；V2 额外有 AR 模型转口音与情绪。四个模型：`xlsr-tiny`（25 M，实时）、`whisper-small-wavenet`（98 M，22.05 kHz，离线默认）、`whisper-base-f0-44k`（200 M，44.1 kHz，带 F0 条件）、V2 `hubert-bsqvae-small`（67 M + 90 M AR，最能压住源说话人特征）。
- **关键参数**：`--diffusion-steps 25`（30–50 最好，4–10 最快）、`--length-adjust 1.0`（**链路 A 必须 1.0**）、`--inference-cfg-rate 0.7`、`--f0-condition True/False`、`--auto-f0-adjust`、`--semi-tone-shift`、`--fp16 True`；V2：`--intelligibility-cfg-rate 0.7 --similarity-cfg-rate 0.7 --convert-style false`（只转音色）。
- **硬件 / 速度**：权重合计 3.94 GB；作者只给了 3060 笔记本实时模式数字（xlsr-tiny 10 步，每 180 ms 块推理 150 ms），4090 离线速度未验证；Windows 上 `--compile` 需 `triton-windows==3.2.0.post13`。
- **坑**：默认离线模型输出 22.05 kHz，H3 原生 32 kHz——直接替换会丢 11–16 kHz 的空气感；用 44 k F0 模型或转换后只取 < 10 kHz 与原声高频带混合（未验证）。仓库已 19 个月未更新，GPL-3.0 仅影响再分发代码，不影响输出。
- **对 4090 短剧的价值**：链路 A 的核心；每句对白几秒，时间成本可忽略。
- **评级**：**采用**，但作为「有漂移才用」的修复工具。

#### RVC / Applio
- **定位**：检索式 VC，需为每个角色训练 `.pth`（+ index）；推理快、稳定、不幻觉内容。
- **用法**：用 A 链路里筛出的认可句（合计 5–10 分钟）训练角色模型；之后所有 take 的该角色对白过一遍。TTS-Audio-Suite 的 `Unified 🔄 Voice Changer` 可加载 `.pth` 并做 1–5 遍迭代精炼，也自带训练节点。
- **价值**：连载到第 3 集以后，角色素材够了就从 seed-vc 切到 RVC——一致性比逐句零样本好，且采样率 40 / 48 kHz。
- **评级**：**采用**（≥ 3 集后的默认）。

### 2.3 口型与音频驱动

| 项目（快照） | 类型 | 许可 | 脸区 / 分辨率 | 帧率 | 显存 / 速度（作者口径） | 中文音频 | ComfyUI | 评级 |
|---|---|---|---|---|---|---|---|---|
| LatentSync 1.6（★6311，2025-06） | V2V 只改嘴 | 代码 Apache-2.0，HF 权重标 openrail++ | 512×512 | 25 | 1.6 ≥ 18 GB；1.5 ≥ 8 GB；速度未见 | 1.5 起专门改善 | ShmuelRonen/ComfyUI-LatentSyncWrapper（★966）；GuardSkill Enhanced | 采用（真人中近景） |
| MuseTalk 1.5（★7002，push 2026-11-19） | V2V 只改嘴，单步 | MIT，模型可商用 | 256×256 | 25 | V100 30 fps+；4 GB 可跑 | 支持中 / 英 / 日 | 旧节点（kijai 2024） | 试用（中远景 / 批量） |
| ComplexSync（★488，2026-11-02） | V2V 只改嘴，1 步 / 12 步 | Apache-2.0 | 未见 | 25 | 未见 | 未见 | 无 | 观望（权重仅 ModelScope） |
| InfiniteTalk（★8445）/ MultiTalk（★3038） | I2V / V2V 整段重生成 | Apache-2.0 | 480P / 720P（Wan2.1 14B） | 25 | fp8 19.5 GB；社区中文工作流 Q8 GGUF 需 32 GB | chinese-wav2vec2-base，好 | kijai/ComfyUI-WanVideoWrapper；官方模板 | 试用（口播 / MV） |
| LongCat-Video-Avatar 1.6（HF 2026-11-13） | I2V 整段生成 | MIT | 768×512 等 | 25 | int8 14.9 GiB；4090 10.1 s 片约 162 s（第三方节点作者） | Whisper large-v3 特征 | Comfy-Org 重打包（原生）；PedroMarinhoDev 节点 | 试用（口播首选替代） |
| LTX-2.3 DubIt / LTX-2.5 A2Vid（★10338） | 联合音画：改台词 + 口型 / 音频出画面 | 代码 Apache-2.0，权重 LTX Community | 模型原生 | 24–25 | 22B，24 GB 需 FP8 + offload（未验证） | 未验证 | 官方模板 `video_ltx_2_audio_to_video` | 观望 |
| Chanjing-Avatar V2V 5B（2026-08） | V2V 只重生成脸区 | Apache-2.0 | Wan2.2-TI2V-5B | — | 未见；Linux | wav2vec2-base-960h（英文预训练） | 无 | 观望 |
| HuMo / Wan2.2-S2V / EchoMimic v3 / FantasyTalking / Sonic / OmniAvatar | I2V 数字人 | Apache-2.0（Sonic 非商用） | 480–720P | 25 | 14–17B 级 | 各异 | 官方模板 `video_humo` 等 | 观望 |
| LivePortrait（★19541） | 表情 / 头动迁移（非音频） | GitHub 标 NOASSERTION（依赖 insightface，商用前核对） | 512 | — | 实时级 | — | kijai/ComfyUI-LivePortraitKJ（2024 停更） | 试用（修表情） |
| H3 ExactAudioLock（★16） | H3 自身音频驱动 | MIT | H3 原生 | 24 | = 一次 H3 采样 | 取决于 H3 | 自身 | **采用**（链路 C） |

#### LatentSync 1.5 / 1.6（bytedance/LatentSync）
- **定位**：端到端音频条件 latent 扩散改嘴，不经中间运动表示；目前开源「只改嘴」里清晰度最高。
- **机制**：Whisper-tiny 音频嵌入经 cross-attention 进 SD U-Net；参考帧 + 遮住下半脸的帧与噪声 latent 通道拼接；SyncNet / TREPA / LPIPS 监督；1.5 加时间层并改善中文，1.6 改 512×512 训练缓解糊嘴。InsightFace 检测 + 仿射对齐，处理后贴回。
- **关键参数**：`--inference_steps 20`（20–50）、`--guidance_scale 1.5`（1.0–3.0，越高越同步但可能抖动 / 畸变）、`--enable_deepcache`；ComfyUI 包装里叫 `lips_expression`（默认 1.5，演讲类 2.0–2.5）与 `inference_steps`。
- **硬件 / 速度**：1.6 最少 18 GB、1.5 最少 8 GB（官方）；`latentsync_unet.pt` 5.07 GB；4090 速度未见任何官方数字。
- **帧率**：训练与数据管线固定 25 fps。H3 是 24 fps——用 §1.2 的「重打时间戳」往返，不要让工具自己插帧 / 丢帧。
- **适用边界**：正脸到 3/4 侧脸的中近景（脸宽建议 ≥ 150 px，经验估计、未实测）；大侧脸、遮挡（手 / 麦克风 / 杯子）、快速转头失败率高；示例里有动漫片段，但人脸检测对二维画风不可靠（动漫脸未实测）。
- **许可**：GitHub Apache-2.0，HF 模型卡标 openrail++；商用按后者的使用限制执行。2025-06 后无更新。
- **评级**：**采用**（链路 B 真人镜头的默认；先 1.5 试通再上 1.6）。

#### MuseTalk 1.5（TMElyralab/MuseTalk）
- **定位**：腾讯音乐的实时改嘴，**不是扩散**——在 ft-mse-vae latent 里单步 inpainting。
- **关键参数**：`python -m scripts.inference --inference_config configs\inference\test.yaml --result_dir results\test --unet_model_path models\musetalkV15\unet.pth --unet_config models\musetalkV15\musetalk.json --version v15 --ffmpeg_path <ffmpeg\bin>`（README 给了 Windows 命令）；1.0 用 `--bbox_shift`（正值张嘴更大）；`--use_float16` 省显存。
- **硬件 / 速度**：V100 30 fps+；3050Ti 4 GB fp16 出 8 s 约 5 分钟（作者自报）。
- **局限**：脸区 256×256，1080p 特写会软；建议 25 fps 输入。代码 MIT、模型「可用于任何用途含商用」，是许可最干净的改嘴方案。
- **评级**：**试用**（中远景、批量预览、对许可敏感的商单）。

#### InfiniteTalk / MultiTalk（MeiGen-AI）与 LongCat-Video-Avatar 1.6（美团）
- **定位**：都不是「改嘴」，而是**音频条件的整段视频生成**：嘴、头、身体、表情一起动。InfiniteTalk 的 V2V 叫「sparse-frame video dubbing」，官方自己写明「镜头运动只是模仿原片、不完全一致」，用 SDEdit 更贴但有色偏、只适合短片段。
- **关键参数（InfiniteTalk）**：音频 CFG 3–5；不挂加速 LoRA `text 5 / audio 4`，挂 lightx2v / FusionX `1 / 2`；`--motion_frame 9`；官方 ComfyUI 模板 832×480×81 帧、7 步 cfg 1 shift 11 dpm++_sde、输出 25 fps；I2V 超过 1 分钟色偏明显。
- **关键参数（LongCat 1.6）**：起始图 + 提示词 + 语音；93 帧一段、接上段末 13 帧；8 步 DMD + OPSD LoRA（cfg 1）或 base 50 步；文本编码器与 VAE 与 Wan 2.1 字节相同（可复用）。
- **硬件**：InfiniteTalk fp8 单文件 19.5 GB + Wan2.1 14B，24 GB 需 block swap；LongCat int8 14.9–16 GiB，第三方节点作者报 4090 上 768×512、253 帧约 162 s。
- **价值**：H3 类型包里标「弱」的真人口播 / 数字人、唱歌 MV 的替代生成器；不适合「保留原画面只改嘴」。
- **评级**：**试用**（口播 / MV 类型的 B 计划），LongCat 许可（MIT）与 4090 适配更好，优先。

#### H3 自身：ExactAudioLock / DialogueAudioLock / NativeAudioLock / 数字人工作流
- **定位**：让 H3 的画面响应**用户给定的精确音频**，而不是它自己生成的音频。
- **机制（源码级）**：把目标波形重采到音频 VAE 采样率、按 `start_frame`（24 fps → 整数采样点）放到全长静音里、编码成音频 latent 替换目标，并给音频流 `noise_mask=0`（`caitongbo` 的实现是 `audio_mask = torch.zeros(…)`，视频 mask 为 1）；采样时模型只能改视频去「配合」这段音频。
- **节点与默认值**：`MiniMaxH3TimedAudio[start_frame 24, gain_db 0.0, label]`；`MiniMaxH3ExactAudioLock[mix_policy sum, overflow_policy error]`；`MiniMaxH3DialogueAudioLock[prevent_clipping, error, protect_before_ms 200, protect_after_ms 250, feather_ms 100]` + `MiniMaxH3DialogueAudioFinalize`；示例工作流用 `res_multistep / simple / 20 步`，`CreateVideo(24)`。
- **规则**：同一 `start_frame` 同时接 `MiniMaxH3AddGuide.frame_idx`；全锁时成片混 `exact_audio`；单声道会被复制成立体声；只有一条目标音轨，多说话人归属靠提示词；不要与 Context Loop 的 `lock_source_audio` 同时拥有音频 latent。
- **评级**：**采用**（链路 C 的基础设施；也是链路 B 里「重拍」选项的实现）。

### 2.4 音效与拟音

| 项目（快照） | 类型 | 许可 | 权重 / 显存（作者口径） | 输出 | ComfyUI | 评级 |
|---|---|---|---|---|---|---|
| HunyuanVideo-Foley（★1102，XL 2025-09-29） | 视频 + 文本 → 音效 | tencent-hunyuan-community | XXL 10.3 GB：20 GB / offload 12 GB；XL 5.85 GB：16 GB / offload 8 GB | 48 kHz | if-ai/ComfyUI_HunyuanVideoFoley（★183） | 采用（V2A） |
| PrismAudio（ThinkSound 后继，2026-03-24） | 视频 → 音效，四维 CoT + RL | MIT（HF 卡） | 6.17 GB | 未见 | 仅 ThinkSound 旧节点 | 试用 |
| MMAudio（★2324） | 视频 / 文本 → 音效 | 代码 MIT，**权重 CC-BY-NC 4.0** | `large_44k_v2` 4.12 GB；约 6 GB 显存 | 44.1 kHz，8 s | kijai/ComfyUI-MMAudio（★580） | 试用（仅非商用） |
| Stable Audio 3（HF 2026-10-06） | 文本 → 音效 / 音乐 / 单发 | stable-audio-community | medium 9.22 GB；small-sfx 2.27 GB | 未核对 | **ComfyUI 原生**（Comfy-Org/stable-audio-3） | 采用（T2A） |
| MOSS-SoundEffect v2.0（2026-05-26） | 文本 → 音效 | Apache-2.0 | 1.3B DiT；套件内约 11.2 GB | 48 kHz，≤ 30 s | TTS-Audio-Suite | 试用 |
| AudioX / AudioX-Turbo | 任意 → 音频 | NOASSERTION | — | — | 第三方 | 观望 |
| Foley-Omni（2026-06） | 视频 → 人声 + 音效 + 音乐整轨 | MIT | — | — | 无 | 观望 |
| LTX-2.3 Foley V2A LoRA（2026-10-22） | 用联合音画模型给无声视频配音效 | LTX Community（gated） | LoRA | — | LTX 管线 | 观望 |

#### HunyuanVideo-Foley（Tencent-Hunyuan）
- **定位**：视频 + 文本条件的 48 kHz 拟音模型，画面同步是卖点。
- **关键参数**：`--model_size xxl|xl`、`--enable_offload`；Gradio `MODEL_SIZE=xl ENABLE_OFFLOAD=true python3 gradio_app.py`；ComfyUI 节点支持 cpu offload + FP8。
- **硬件**：XL + offload 8 GB——可以在 H3 卸载后的同一台 4090 上顺手跑；速度未见官方数字。
- **许可**：腾讯混元社区许可（商用条款按其 LICENSE，未逐条核对）。
- **价值**：H3 的无台词动作镜若原生音效不理想，用它重出动作声，再与 H3 原声二选一。
- **评级**：**采用**（V2A 首选，等用户侧 A/B）。

#### Stable Audio 3（stabilityai，ComfyUI 原生）
- **定位**：文本 → 音频家族：`medium`（9.22 GB）、`small-sfx` / `small-music`（各 2.27 GB），文本编码器 `t5gemma_b_b_ul2`（1.19 GB）。
- **官方模板参数**：`CheckpointLoaderSimple(stable_audio_3_medium.safetensors)` + `CLIPLoader(t5gemma_b_b_ul2.safetensors, type stable_audio)` + `EmptyLatentAudio(60)`，KSampler 8 步 cfg 1 `lcm` / `simple`；模板内置 Music / Instrument / SFX / One-shot 四类提示词改写。
- **许可**：stable-audio-community（Stability 社区许可；官方模型卡 gated，本次未读到正文）。
- **价值**：每场景一条 room tone、风声、雨声、转场 whoosh、切黑低频重音——都是「文本就能说清」的声音，不需要看画面。
- **评级**：**采用**（环境声底与转场音效的默认生成器）。

#### MMAudio / PrismAudio（合并）
- **MMAudio**：CLIP 8 fps + Synchformer 25 fps 的同步模块，默认 8 s（偏离训练时长降质）；只看画面中心 224 px 方块；已知会偶发「含糊人声」和「背景音乐」。质量与同步口碑最好，但权重 CC-BY-NC——**商单不能用**。
- **PrismAudio**：ThinkSound 的后继（同仓库 `prismaudio` 分支），把推理拆成语义 / 时间 / 美学 / 空间四个 CoT 模块并用 RL 优化；HF 权重 MIT。ComfyUI 生态还没跟上，需独立环境。
- **评级**：MMAudio **试用（非商用）**；PrismAudio **试用**。

### 2.5 配乐

| 项目（快照） | 许可 | 时长 / 控制 | 24 GB 适配 | ComfyUI | 评级 |
|---|---|---|---|---|---|
| ACE-Step 1.5（★15046，XL 2026-04-02） | MIT | 10 s–10 min；BPM / 调 / 拍号 / 时长；cover / repaint / 分轨 / 理解 | XL turbo（~9 GB 权重）不需 offload | **原生**（`TextEncodeAceStepAudio1.5` 等） | 采用 |
| YuE2（★13644，2026-09-14） | Apache-2.0 | 先出可编辑 ABC 谱再渲染；翻唱；对话式改谱；48 kHz | 官方要求 24 GB + Linux；ComfyUI 模板用 `yue2_3b_int8_convrot` | **原生**（`YuE2GenerateABC` / `YuE2GenerateMusic`） | 试用（主题曲） |
| Stable Audio 3 small-music / medium | stable-audio-community | 文本 → 器乐 | 2.27 / 9.22 GB | 原生 | 试用（短 sting） |
| HeartMuLa oss-3B（★3810） | Apache-2.0 | 歌曲；RTF ≈ 1.0 | 可 | 第三方节点 | 观望 |
| DiffRhythm 2 / SongGeneration | Apache-2.0 / 自定义 | 整曲 | 可 | 第三方 | 观望 |

#### ACE-Step 1.5（ace-step/ACE-Step-1.5）
- **定位**：LM 规划 + DiT 的音乐基础模型，自评「介于 Suno v4.5 与 v5 之间」；MIT。
- **ComfyUI 原生接线（官方模板 `audio_ace_step1_5_xl_turbo.json`）**：`UNETLoader(acestep_v1.5_xl_turbo_bf16.safetensors)` → `ModelSamplingAuraFlow(3)`；`DualCLIPLoader(qwen_0.6b_ace15.safetensors, qwen_4b_ace15.safetensors, type ace)`；`VAELoader(ace_1.5_vae.safetensors)`；`TextEncodeAceStepAudio1.5(tags, lyrics, seed, bpm 10–300, duration 0–2000 s, timesignature 2/3/4/6, language, keyscale, generate_audio_codes, cfg_scale 2.0, temperature 0.85, top_p 0.9)`；`EmptyAceStep1.5LatentAudio(seconds)`；KSampler 8 步 cfg 1 euler / simple。
- **硬件 / 速度**：自报 A100 < 2 s、RTX 3090 < 10 s 一首；24 GB 推荐 XL turbo / sft + `acestep-5Hz-lm-1.7B`；2B turbo 权重 4.79 GB。
- **与短剧相关的能力**：`bpm` 与 `duration` 是节点入参——先定 BPM 再生成，切点表才能预先对拍；`repaint` 可只重画某一小节（转场处加重音）；「音频理解」可从现成参考曲提 BPM / 调。
- **评级**：**采用**（全集配乐默认生成器）。

#### YuE2（multimodal-art-projection/YuE）
- **定位**：歌词 + 风格 → **先写旋律与和弦谱（ABC）再渲染成带人声的歌**；谱可读、可改、可交给 agent 改。
- **ComfyUI 原生（官方模板）**：`CheckpointLoaderSimple(yue2_3b_int8_convrot.safetensors)` → `YuE2GenerateABC`（`cot="full"`）→ `YuE2GenerateMusic` → KSampler 32 步 cfg 1 `dpm_2` / `sgm_uniform`，`EmptyYuE2LatentAudio(120)`。
- **价值**：MV 类型包与片头 / 片尾主题曲；因为谱是显式的，同一主题可以出「完整版 / 纯器乐版 / 悲伤变奏」并保持旋律一致——这是给短剧做**主题动机**的正确工具。
- **评级**：**试用**。

### 2.6 人声分离与对白清理

| 项目（快照） | 用途 | 许可 | 用法 | 评级 |
|---|---|---|---|---|
| python-audio-separator（★1503，push 2026-10-29） | 人声 / 伴奏 / 去混响 / 去噪（UVR 全模型库） | MIT | `pip install "audio-separator[gpu]"`；`audio-separator in.wav --model_filename model_bs_roformer_ep_317_sdr_12.9755.ckpt` | 采用 |
| ComfyUI 核心 `AudioStemSeparate(htdemucs)`；kijai MelBandRoFormer 节点 | 工作流内分离 | — | 官方模板 `utility-audioseparation` / `audio_melbandroformer_audio_separation` | 采用 |
| SAM-Audio（Meta，★3759） | 文本 / 画面 / 时间段提示分离任意声音 | 自定义（gated） | `model.separate(batch, predict_spans=True, reranking_candidates=8)` → target + residual；提示用小写名词短语 | 试用 |
| TIGER-DnR（JusperLee） | 影视声轨三分：对白 / 音乐 / 音效 | Apache-2.0 | HF `JusperLee/TIGER-DnR` | 试用 |
| NVIDIA RE-USE（2026-10-22） | 通用语音增强（噪声 / 混响 / 削波 / 带宽 / 编码失真） | openmdw-1.1，卡片写明可商用 | 9.6 M 参数，输入 8–48 kHz | 采用（清理） |
| DeepFilterNet（★5069，push 2026-11-06） | 实时降噪 48 kHz | MIT / Apache 双许可（GitHub 标 NOASSERTION） | CLI / LADSPA | 试用 |
| Resemble Enhance（★2504，2024-12 停更） | 去噪 + 44.1 kHz 增强 | MIT | — | 观望 |
| AudioSR（★1998） | 任意 → 48 kHz 扩散超分 | MIT | Saganaki22/ComfyUI-AudioSR | 试用（22 kHz VC 之后） |
| ClearerVoice-Studio（★4637，2025-08） | SE / SR / 说话人分离 | Apache-2.0 | 下载源未核对 | 观望 |

要点：① H3 的一条音轨里对白、动作声、环境声已经混在一起，**任何 VC / TTS 替换之前必须先分离**，否则会把动作声一起转成人声质感；这也是 skill 现有规则「生成时声音行统一写安静房间底噪 + 动作声 + 干净人声」的价值——底噪越干净分离越彻底。② 音乐向的人声模型（BS / MelBand RoFormer）对「对白 vs. 非音乐音效」不是专门训练的，脚步、关门等瞬态可能漏进人声 stem；SAM-Audio（文本提示 `speech`）与 TIGER-DnR 是对口方案，均未在 H3 素材实测。③ 增强模型会改变音色，放在 VC 之前、且只对确实脏的句子用。

### 2.7 ASR、强制对齐与字幕

| 项目（快照） | 用途 | 许可 | 中文 | 关键用法 | 评级 |
|---|---|---|---|---|---|
| Qwen3-ASR + Qwen3-ForcedAligner-0.6B（★3932，2026-01-29） | ASR；**已知文本强制对齐** | Apache-2.0 | 30 语 + 22 种中文方言；对齐 11 语含中 / 粤 | `Qwen3ForcedAligner…align(audio, text, language="Chinese")` → 每字 `start_time / end_time`，单段 ≤ 5 分钟；ASR 4.70 GB、对齐器 1.84 GB | 采用 |
| faster-whisper（★26922，push 2026-11-12） | ASR + 词级时间 | MIT | 好 | `WhisperModel("large-v3", device="cuda", compute_type="float16").transcribe(a, word_timestamps=True, vad_filter=True)`；`BatchedInferencePipeline` | 采用（质检） |
| WhisperX 3.8（★25555） | ASR + wav2vec2 对齐 + 说话人 | BSD-2 | 对齐模型 `jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn`，逐字 | `whisperx a.wav --model large-v3 --language zh --highlight_words True` | 试用 |
| stable-ts（★2285） | Whisper 系强制对齐 + 断句 | MIT | 可 | `model.align(audio, text, language='zh')`；`to_srt_vtt(word_level=True)` / `to_ass()` | 试用 |
| FunASR / SenseVoice / FunClip | 中文 ASR + 情感 / 事件；按文本剪辑 | MIT | 一等 | 默认 hub 是 ModelScope，HF 需显式指定（未在本次核对） | 观望（下载源） |
| VibeVoice-ASR 7B | 60 分钟长音频、说话人 + 时间戳、热词 | MIT | 50+ 语 | 长节目 | 观望 |

#### 字幕规范（落到 ASS 样式，1920×1080）
- **文本永远取锁定原文**，ASR / 对齐只提供时间（h3-drama-kit playbook 08 的规则，VideoLingo 也这么做）。
- **时间**：入点 = 首字 −0.08 s，出点 = 末字 +0.25 s；最短 0.8 s；阅读速度上限 9 字 / s；相邻字幕留 ≥ 2 帧；全部吸附到帧。极短单句（< 0.8 s）并入下一条。
- **版式**：中文 58 px、英文 36 px（双语时中文在上）；`Outline 3 / Shadow 1`，`BorderStyle 1`；`Alignment 2`（底部居中）；`MarginV` 中文 96、英文 52；左右 `MarginL/R 160`；单行 ≤ 18 个汉字，最多两行；`WrapStyle 2`；`YCbCr Matrix: TV.709`。
- **安全区**：16:9 交付保留底部 ≥ 5% 净空（`MarginV ≥ 52`）；若同一成片要裁成 9:16 发抖音 / TikTok，字幕改放画面高度 62–72% 处并避开右侧 15%（平台 UI 遮挡，经验值未核对官方模板）。
- **两种交付**：软字幕（`.srt` + 剪映草稿文本轨，可再编辑）与烧录（`-vf subtitles=ep01.ass`）。H3 画面自带文字的镜头先 OCR 复查（skill 既有规则）。

### 2.8 剪辑自动化

#### ffmpeg 滤镜链模板（全部在 ffmpeg 6.1.1 上实跑通过）
```bash
# ① 逐 take：帧精确裁切（丢前 2 帧起始音节、丢尾部 1 s 定格）+ 7:4→16:9 + bt709 标记
ffmpeg -i seg.mp4 -an -vf "trim=start_frame=2:end_frame=120,setpts=PTS-STARTPTS,scale=1920:-2:flags=lanczos,crop=1920:1080,setsar=1,format=yuv420p" \
  -r 24 -c:v libx264 -crf 16 -g 12 -bf 2 -color_primaries bt709 -color_trc bt709 -colorspace bt709 seg.cut.mp4
# ② 无损拼接（各段编码参数一致）
ffmpeg -f concat -safe 0 -i list.txt -c copy video_only.mp4
# ③ 两遍 loudnorm（先测后调，线性增益；动态模式内部升到 192 kHz，必须补 aresample）
ffmpeg -i in.wav -af "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" -f null -      # 读 input_i/tp/lra/thresh/target_offset
ffmpeg -i in.wav -af "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=…:measured_TP=…:measured_LRA=…:measured_thresh=…:offset=…:linear=true,aresample=48000" -c:a pcm_s24le out.wav
# ④ 时间线混音：每段对白 atrim → afade → adelay 到自己的时间码，amix 不归一；L-cut = 音频比画面多留 0.25 s
[0:a]atrim=start=0.0833:end=5.25,asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st=5.0467:d=0.12,adelay=0:all=1[d0];
[1:a]atrim=…,afade=…,adelay=4916.667:all=1[d1]; …
[d0][d1][d2]amix=inputs=3:normalize=0:dropout_transition=0,apad=whole_dur=14.75,atrim=end=14.75,asplit=2[dlg][key];
# ⑤ 环境声底 + 配乐 ducking + 限幅
[amb_in]highpass=f=150,lowpass=f=6500,volume=-34dB[amb];
[bgm_in]volume=-6dB,afade=t=in:d=0.5,afade=t=out:st=13.75:d=1.0[bgm0];
[bgm0][key]sidechaincompress=threshold=0.05:ratio=4:attack=20:release=400:knee=4:makeup=1[bgmd];
[dlg][amb][bgmd]amix=inputs=3:normalize=0:dropout_transition=0,alimiter=limit=0.89:level=false[mix]
# ⑥ 成片：再跑一次 ③（I=-14），然后封装
ffmpeg -i video_only.mp4 -i final_audio.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -ar 48000 -movflags +faststart ep01.mp4
# ⑦ 其它：4 帧叠化 / LUT / 黑位 / 字幕 / 验收
[0:v][1:v]xfade=transition=fade:duration=0.166667:offset=4.75[v]
-vf "lut3d=grade.cube:interp=tetrahedral"          -vf "lutyuv=y='max(val\,36)'"          -vf "subtitles=ep01.ass"
ffmpeg -i ep01.mp4 -vn -af ebur128=peak=true -f null -      # 读 I / LRA / Peak
```
实跑结果（3 段合成素材）：视频 354 帧 = 14.750 s，音频 14.750 s，成片 I = −14.0 LUFS、`Normalization Type: Linear`；`sidechaincompress` 在对白 RMS −20 dBFS 时 `0.05 / 4` 压 8.4 dB、`0.03 / 8` 压 13.7 dB、`0.02 / 20` 压 18.3 dB。

注意：① `acrossfade` 会让总时长缩短一个交叉长度，**硬切短剧不要用它拼对白**，用上面的 `adelay` 定位 + 各自淡变；② `loudnorm` 给不出线性增益时（目标会顶到 TP）自动退回动态模式并改变动态——脚本要检查 `Normalization Type`，退回时改用「固定增益 + `alimiter`」；③ 少于约 3 s 的片段积分响度不可靠，逐句归一用整段对白的测量值；④ H3 段间响度可差 9 LU（skill 既有数据），所以必须**逐 take 先归一再混**。

#### 剪映 / CapCut 草稿导出
- **pyJianYingDraft**（GuanYixuan，★4958，Apache-2.0，pip 0.3.1，push 2026-10-14）：生成草稿在剪映 5.9 与新版（README 标 10.8）都可用；**读加密模板**需自备 `fallback_loader`；自动导出仅剪映 ≤ 6；草稿需在 Windows 剪映里导出。API：`DraftFolder(root).create_draft(name, 1920, 1080, fps=24, allow_replace=True)` → `append_tracks([TrackSpec(TrackType.audio, "music"), …])` → `VideoSegment(path, trange(start_us, dur_us), source_timerange=…, volume=0.0)` / `AudioSegment(path, target, source_timerange=…, volume=…)` + `add_fade("0.01s", "0.12s")` → `script.import_srt(srt, track_name="subtitle", text_style=TextStyle(size=7.0, auto_wrapping=True), clip_settings=ClipSettings(transform_y=-0.78))` → `script.save()`。本次原型实跑：3 段画面 + 2 条交错对白轨 + 配乐 + SRT，`draft_content.json` 时长 14.75 s、fps 24。
- **pyCapCut**（同作者，★779）：国际版 CapCut 草稿，README 标验证版本 8.2.0，不支持自动导出。
- **capcut-mate**（Hommy-master，★2191，Apache-2.0）：FastAPI 服务（`uv run main.py` → `http://localhost:30000/docs`）+ Coze 插件 + 云渲染，适合 n8n / agent 调用。
- **capcut-cli**（renezander030，★1247，MIT，Node ≥ 18）：`capcut quickstart my-first --video clip.mp4 --srt captions.srt`，直接读写本地草稿库；旧版本（≤ 0.17.2）有安全公告，须升级。
- **评级**：pyJianYingDraft **采用**（用户在 Windows 上，剪映是最顺手的精修入口）；其余**试用**。

#### OpenTimelineIO / FCP XML / EDL / DaVinci Resolve / Premiere
- **OpenTimelineIO**（ASWF，★2106，Apache-2.0，0.18.1）：0.16 之后核心包只含 `.otio / .otioz / .otiod`，FCP7 XML、CMX3600 EDL、AAF 适配器要另装（`pip install otio-fcp-adapter otio-cmx3600-adapter` 或 `OpenTimelineIO-Plugins`）。本次原型实跑：`otio.adapters.write_to_file(tl, "ep01.otio")`、`adapter_name="fcp_xml"`、`"cmx_3600"` 三种都写出，354 帧。
- **去向**（通行做法，版本细节未在本次核对）：Resolve 可直接导入 `.otio` / FCP7 XML / EDL；Premiere 导入 FCP7 XML；EDL 只带单轨切点，适合给调色。Resolve 的 Python 外部脚本 API 只有 Studio 版开放（免费版需走内置控制台或社区 MCP，如 `emircbngl/davinci-resolve-mcp-free`，未验证）。
- **评级**：**采用** `.otio + FCP7 XML` 作为剪映之外的第二工程出口。

#### auto-editor / MoviePy / Remotion
- **auto-editor**（★6038，Unlicense，Nim 重写）：按响度 / 运动自动剪「死气」，`auto-editor in.mp4 --margin 0.2sec --edit audio:-19dB`，可导出到 Premiere / Resolve / Final Cut 时间线。对 H3 短剧的用途是**口播类**（数字人口播去停顿），剧情片不要用。**试用**。
- **MoviePy v2**（★15186，MIT）：v2 有大量破坏性改动，逐帧过 numpy，比直接 ffmpeg 慢；我们的脚本保持「标准库 + ffmpeg」即可，不引入。**跳过**。
- **Remotion**（★74668）：React 写视频，字幕动效 / 片头片尾 / 等级框这类**图形包装**的最佳工具，但许可特殊（公司使用可能需付费授权）。**观望**（另一簇覆盖）。

### 2.9 插帧与输出规格

- **24 → 30 / 60 fps 的取舍**：H3 原生 24 fps。YouTube 官方建议「按拍摄帧率上传」，24 fps 直接交付即可；国内平台与电视端常见 25 / 30 fps，直接 `fps=30` 是复制帧（每 4 帧重复 1 帧，平移镜头可见顿挫）。要 30 / 60 就用光流插帧，且**只对无硬切的单镜头片段做**（跨切点插帧会生成融帧）。
- **工具**：Practical-RIFE（★1050，MIT，README 建议默认 4.25，并称 4.24+ 适合扩散生成视频的后处理）；Fannovel16/ComfyUI-Frame-Interpolation（★1095，MIT：RIFE 4.0–4.9、FILM、AMT、IFRNet…）；kijai/ComfyUI-GIMM-VFI（★487，需 `cupy-cuda12==13.3.0`）；yuvraj108c/ComfyUI-Rife-Tensorrt（最快）。ffmpeg `minterpolate=fps=60:mi_mode=mci` 只作无 GPU 的兜底（慢且有拖影）。
- **24 ↔ 25 fps**（给 25 fps 的口型模型）：用时间戳重解释（`-itsscale 0.96` / `1.0416667` + `-c:v copy`），不是插帧。
- **各平台规格**：

| 平台 | 已核实来源 | 视频 | 音频 | 响度 |
|---|---|---|---|---|
| YouTube | 官方帮助页（2026-11-21 读取） | MP4、moov 前置；H.264 High、逐行、2 个连续 B 帧、闭合 GOP = 帧率一半、CABAC、4:2:0、BT.709；1080p SDR 8 Mbps（24–30 fps）/ 12 Mbps（48–60 fps），2160p 35–45 / 53–68 Mbps | AAC-LC 或 Opus，48 kHz，立体声 384 kbps | 官方未公布数值；社区共识约 −14 LUFS、只压不抬 |
| B 站 | 仅社区专栏（非官方，2018–2026） | 1080p 平均码率 ≤ 6000 kbps、峰值 ≤ 24000 kbps 时不二压的说法流传最广 | AAC ≤ 320 kbps、双声道 | 未见官方数值 |
| 抖音 / 快手 / TikTok | 未找到官方规格 | 16:9 横屏按 1920×1080、H.264、24–30 fps、8–12 Mbps 上传并接受二压 | AAC 48 kHz | 未见官方数值；沿用 −14 LUFS / −1.5 dBTP |
| 广播 / 流媒体参照 | EBU R128 | — | — | −23 LUFS、真峰值 ≤ −1 dBTP（电视）；本项目线上交付用 −14 |

- **统一母版建议**：`ep01_master.mp4` = 1920×1080、24 fps、H.264 High、CRF 16（或 2-pass 12 Mbps）、GOP 12、`-bf 2`、yuv420p、bt709 三标记、AAC 320 kbps 48 kHz、`+faststart`；各平台从母版转，不从平台回传文件再加工。TikTok 黑边 / 黑位规避沿用 skill 既有规则（Y′ ≥ 36、切黑前 0.4 s 淡出）。

## 3. 与 H3 流水线对照

### 3.1 H3 已经原生解决的（不要再外挂）
| 外部世界的做法 | H3 里的等价物 | 结论 |
|---|---|---|
| TTS → 改嘴（Wav2Lip / LatentSync 流水线） | 联合音画生成：对白、口型、动作声一次出 | 绝大多数对白镜头**不需要** TTS + lipsync；这是 H3 相对 Wan / Hunyuan 流水线最大的省事点 |
| 音频驱动数字人（InfiniteTalk、LTX A2Vid） | `MiniMaxH3ExactAudioLock`（音频 latent `noise_mask=0`）；`<Audio N>: fully_copy` | 同一原理，H3 内可做；长口播 > 15 s 才考虑换模型 |
| 「只重做音频」（LTX `RetakePipeline regenerate_audio`） | Adudeguyman `H3 Audio Refine Sampler`（冻结视频、`audio_denoise 0.5`、6 步） | 画面好、声音坏时先试它，再考虑 TTS |
| 小脸 / 远景口型修复 | Carasibana FaceRefine + `MiniMaxH3NativeAudioLock`（denoise 0.40） | 已在 skill；把喂给它的音频换成新对白即是 H3 版「V2V 改嘴」（未验证） |
| 音色克隆 | `<Audio 1>` 2–15 s 参考（`attribute_transfer`） | 只定大致音色，每段漂约 1.7 半音 → 仍需后期统一或改用音频锁 |
| 画外音、旁白 | `says in an off-screen voiceover … lips remain completely closed` | 每 15 s ≤ 20 字的限制很紧；**长旁白直接 TTS 进混音，不经 H3** |

### 3.2 可以直接搬进 skill 的做法（标明落点）
| 做法 | 来源 | 搬到哪 |
|---|---|---|
| 声线资产：Qwen3-TTS VoiceDesign → 6–10 s 参考 → 既作 H3 `<Audio N>` 又作 TTS 克隆提示 | Qwen3-TTS README「Voice Design then Clone」 | 步骤 2 系列圣经；`storyboard-and-assets.md` §3 音色一栏 |
| 分镜 JSON 增加 `audio_plan: native \| dialogue_lock \| full_lock` 与 `bpm` | 链路 A / C 的分流 | 步骤 3；`episode.schema.json`、`validate_episode.py` |
| TTS 对白 → `TimedAudio → DialogueAudioLock → Finalize`，同帧 `AddGuide` | ExactAudioLock 源码 + 示例工作流 05 / 10 | 步骤 5；`comfyui-nodes.md` 新增「音频锁」小节；`comfy_submit.py` 的 API 模板 |
| 先分离再处理：`(Vocals)` / `(Instrumental)` 两条 stem 贯穿后期 | VideoLingo、官方 InfiniteTalk / LTX A2V 模板里的 `AudioSeparation` | 步骤 7；`qc-and-assembly.md` §3 之前新增「stem 化」 |
| 漂移先量化（中位 F0）再决定是否 VC；VC 守时（`length-adjust 1.0`、帧数与包络偏移校验） | seed-vc README + 本次原型 | 步骤 7；`unify_voice.py` |
| 字幕时间改用强制对齐（替换 `silencedetect` 按句数分配） | Qwen3-ForcedAligner；VideoLingo 默认 | `qc-and-assembly.md` §3-2；`retime_subtitles.py`；`build_prompts.py` 产出的 `cues.srt` 只作初稿 |
| 台词质检 ASR 升级到 large-v3 / Qwen3-ASR（中文），阈值沿用 0.72 / 0.88 | faster-whisper、Qwen3-ASR | `qc-and-assembly.md` §1；`judge-take-prompt.md` |
| 时间线混音模板 + 校准过的 ducking 参数 + `loudnorm` 退回检查 | 本次 ffmpeg 实跑 | `mix_episode.py`；`qc-and-assembly.md` §3 |
| 配乐带 BPM 生成 + 切点吸附 1/4、1/8 拍 ±2–3 帧 | ACE-Step 1.5 节点入参；本次 beat_grid 原型 | 步骤 3（定 BPM）与步骤 7（吸附） |
| 可编辑工程双出口：剪映草稿 + `.otio / FCP7 XML` | pyJianYingDraft、OpenTimelineIO 原型 | 步骤 7；产物目录新增 `edit/` |
| 25 fps 工具的帧率往返用时间戳重解释 | 本次 ffmpeg 实跑 | `pitfalls.md` 新增一行；`lipsync_v2v.py` |

### 3.3 这些场景应该换别的模型
| 场景 | H3 的问题 | 换什么 |
|---|---|---|
| 真人口播 / 数字人连续说话 > 15 s | 段间续接后声音发闷、身份漂移；类型包已标「弱」 | LongCat-Video-Avatar 1.6（MIT，int8 ~16 GB，ComfyUI 原生）；或 InfiniteTalk I2V |
| 画面不可重拍但必须改台词 / 出外语版 | H3 没有「保画面只改嘴」的官方模式 | LatentSync 1.6（真人）/ MuseTalk 1.5（许可敏感）；LTX-2.3 DubIt 观望 |
| 全集配乐、主题曲 | `non_diegetic_music` 逐段生成互不连贯 | ACE-Step 1.5（器乐）/ YuE2（带人声主题曲）；H3 侧一律 `N/A` |
| 连续环境声（同一场景跨多段） | 每段环境声重新生成、底噪跳变 | Stable Audio 3 small-sfx 出一条 room tone 贯穿全场 |
| 方言 / 指定艺人式声线 / 强情绪独白 | 音色参考被角色表观性别强拉；情绪不可控 | IndexTTS-2.5 / CosyVoice3 出对白，再走链路 C 音频锁 |
| 需要逐字精确的台词（法律 / 品牌 / 产品名） | 抽卡门禁成本高 | TTS + ASR 回读 100% 通过后再锁音频生成 |
| 歌声对口型（MV） | 可用 `fully_copy` + 分离人声（animede 做法），多段后发闷 | InfiniteTalk（官方模板即 music）或 LongCat；歌曲本身用 YuE2 / ACE-Step |

## 4. 可直接加进 skill 的脚本清单与规格

**约定**：① 与现有脚本一致——Python 3.10+ 标准库 + `ffmpeg / ffprobe`；凡是要调模型的脚本都通过 `audio_tools.toml` 里的**命令模板**调用独立 venv（不 import torch），模型缺失时给出可执行的安装提示并以退出码 3 结束。② 中间交换格式统一为 `edit/ep01.edl.json`（下例）；所有脚本幂等（输出旁写 `*.meta.json`：输入哈希、参数、工具版本），重跑跳过未变项。③ 每个会占 GPU 的批次开始前调用 ComfyUI `/free`。④ 标 ★ 的核心逻辑已有实跑原型。

```json
{"name": "ep01", "fps": 24, "width": 1920, "height": 1080, "bpm": 90,
 "segments": [
   {"id": "seg01", "video": "final/ep01/seg01.mp4", "in_frame": 2, "out_frame": 220,
    "dialogue": "audio/ep01/seg01.dlg.wav", "nondialogue": "audio/ep01/seg01.fx.wav",
    "l_cut": 0.25, "j_cut": 0.0, "scene": "kitchen_night",
    "lines": [{"speaker": "xia", "text": "为什么我是最后一个知道的？", "en": "Why was I the last to know?"}]}],
 "ambience": {"kitchen_night": {"file": "audio/amb/kitchen_night.wav", "gain_db": -34}},
 "music": {"file": "audio/music/ep01_90bpm.wav", "gain_db": -6, "fade_in": 0.5, "fade_out": 1.0,
           "duck": {"threshold": 0.05, "ratio": 4, "attack": 20, "release": 400}},
 "loudness": {"dialogue_lufs": -16, "program_lufs": -14, "true_peak": -1.5, "lra": 11}}
```

### 4.1 `mix_episode.py` ★
- **用途**：链路 A / B / C 的最终混音与封装。
- **CLI**：`mix_episode.py edit/ep01.edl.json --out final/ep01.mp4 [--stems-out audio/ep01/stems/] [--no-music] [--dry-run]`
- **输入**：EDL；每段的对白 stem、非人声 stem、环境声、配乐。**输出**：`ep01.mp4`（视频流拷贝 + AAC 320k 48 kHz）、`ep01.mix.wav`、三条 stem（`dialogue / effects / music`，便于平台二次混）、`ep01.mix.report.json`。
- **关键逻辑**：① 逐段帧精确裁切并统一转码（§2.8 ①），`concat -c copy` 得到 `video_only.mp4`；段起点 `T_i = Σ(out−in)/fps`，全部用**帧数累加再换算**，不要累加浮点秒。② 对白：`atrim(start=in/fps − j_cut, end=out/fps + l_cut)` → `afade in 10 ms / out 120 ms` → `adelay=(T_i − j_cut)·1000:all=1` → `amix normalize=0`；非人声 stem 同样定位但不做 L-cut。③ 环境声按 `scene` 连续铺、`highpass 150 / lowpass 6500`、默认 −34 dB。④ 配乐 `sidechaincompress`（key = 对白总线），默认 `0.05 / 4 / 20 ms / 400 ms`。⑤ `alimiter limit=0.89`。⑥ 两遍 `loudnorm` 到 `program_lufs`；检查 `Normalization Type`，若为 Dynamic 则改「线性增益 = target − input_i，再 `alimiter`」并在报告里记警告。⑦ `ebur128=peak=true` 复测，写报告。
- **验收（硬门）**：`|视频时长 − 音频时长| ≤ 1 帧`；I 在目标 ±0.5 LU；真峰值 ≤ −1.0 dBTP；对白段内配乐压低量在 6–14 dB 之间（用 stem 测）。
- **退出码**：0 通过；1 验收失败；2 输入缺失；3 工具缺失。

### 4.2 `split_stems.py`
- **用途**：H3 take → 对白 stem + 非人声 stem（链路 A / B 的前置）。
- **CLI**：`split_stems.py selects/ep01/*.mp4 --out audio/ep01/ --engine audio-separator --model model_bs_roformer_ep_317_sdr_12.9755.ckpt`
- **逻辑**：`ffmpeg -vn -af aresample=48000 pcm_s24le` → 调分离器 → 重命名为 `segNN.dlg.wav` / `segNN.fx.wav` → **重构校验**：`dlg + fx` 与原音轨相减的残差 RMS ≤ −40 dBFS（`amix` 反相求差）；台词区间外 `dlg` 的能量应 < −50 dBFS，否则标记「动作声漏进人声」供人工看。`--engine sam-audio` 时提示词固定 `speech`。
- **输出**：两条 stem + `segNN.stems.json`（残差、泄漏指标）。

### 4.3 `retime_subtitles.py` ★
- **用途**：锁定原文 + 对齐器时间 → `ep01.srt`、`ep01.ass`（可双语），并回写每句时间到 EDL。
- **CLI**：`retime_subtitles.py edit/ep01.edl.json --aligner qwen3 --fps 24 --out subs/ep01 [--bilingual en] [--style assets/subtitle-style.json]`
- **逻辑**：① 每段对白 stem 调对齐器（模板：Qwen3-ForcedAligner `align(audio, text, language)`；备选 `whisperx`、`stable-ts align`、faster-whisper `word_timestamps`），统一成 `[{text, start, end}]`。② 把对齐单元摊成逐字时间，与**去标点的锁定原文**做 `difflib.SequenceMatcher`，只取 `equal` 块建立「原文字 → 时间」映射（ASR 错字不影响文本）。③ 每句：`start = 首个命中字 − 0.08`，`end = 末个命中字 + 0.25`，再套最短 0.8 s、≤ 9 字 / s、相邻留 ≥ 2 帧、吸附帧；覆盖率 < 0.6 的句子标 `needs_review`。④ 加上段起点 `T_i` 得到全片时间；写 SRT 与 ASS（§2.7 样式）。
- **核心函数（已实跑）**：
```python
chars = [(ch, u_start + k*d, u_start + (k+1)*d) for u in units for k, ch in enumerate(norm(u["text"]))]  # d = 单元时长/字数
sm = difflib.SequenceMatcher(None, ref, "".join(c[0] for c in chars), autojunk=False)
r2h = {i1 + k: j1 + k for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag == "equal" for k in range(i2 - i1)}
hit = [r2h[i] for i in range(a, b) if i in r2h]                 # a:b = 该句在 ref 中的字区间
start, end = chars[hit[0]][1] - 0.08, max(chars[hit[-1]][2] + 0.25, start + 0.8, start + (b - a) / 9.0)
```
  样例：ASR 把「知道的」识别成「知到的」时覆盖率 0.917，字幕仍输出锁定原文，时间 0.542 → 2.250 s。

### 4.4 `unify_voice.py` ★
- **用途**：链路 A 的音色统一（零样本 seed-vc 或每角色 RVC）。
- **CLI**：`unify_voice.py edit/ep01.edl.json --anchors bible/voices/ --engine seed-vc --drift-semitones 0.5 [--probe-only]`
- **逻辑**：① 锚点体检：时长 ≥ 6 s、−60 dB 以下静音占比 < 30%、与本集对白电平差 ≤ 1.5 dB（skill 既有规则）。② 按 `retime_subtitles` 写回的句时间切 `dlg` stem，逐句测中位 F0（16 kHz、1024 窗、自相关 70–400 Hz、峰值 > 0.3·R0 才计）并与该角色锚点比较，输出 `voice_drift.csv`；`--probe-only` 到此为止。③ 只对 `|Δ| > 阈值` 或人工点名的句子调用引擎：seed-vc 模板 `python inference.py --source {src} --target {anchor} --output {out} --diffusion-steps 30 --length-adjust 1.0 --inference-cfg-rate 0.7 --f0-condition True --auto-f0-adjust True --fp16 True`。④ **守时**：输出时长与源差 ≤ 1 帧；5 ms RMS 包络互相关求偏移（±300 ms 搜索），|偏移| > 20 ms 则整句平移；输出重采到 48 kHz。⑤ 10 ms 淡变贴回，写 `segNN.dlg.unified.wav`，EDL 的 `dialogue` 指向新文件。
- **验收**：转换后该句与锚点的 F0 差 ≤ 0.5 半音；ASR 回读与原文相似度不下降；失败句保留原声并记入报告（宁可不转）。
- **原型实测**：人为延迟 40 ms + 升调 1.65 半音的合成样本，检出偏移 30 ms（5 ms 分辨率）、音高差 1.75 半音。

### 4.5 `tts_lines.py`
- **用途**：链路 B / C 批量出对白（多引擎、可定长、带回读门禁）。
- **CLI**：`tts_lines.py edit/ep01.edl.json --engine indextts25|omnivoice|cosyvoice3|voxcpm2|auk --anchors bible/voices/ --seeds 3 [--fit-window] [--emo-from-original]`
- **逻辑**：每句构造引擎命令（`audio_tools.toml` 模板）；`--fit-window` 时读取该句窗口 `D_i`：OmniVoice 传 `duration=D_i`，AuK 传 `--gen_seconds D_i`，IndexTTS 先自然合成再以 `duration_factor = clamp(D_i/n_i, 0.85, 1.15)` 重出；`--emo-from-original` 把原句 vocals 作为 `emo_audio_prompt`（`emo_alpha 0.7`）。每个 seed 生成后：`ffprobe` 时长检查（\|时长 − D_i\| ≤ 3 帧）、ASR 回读相似度 ≥ 0.90、首尾静音裁到 20 ms、逐句 `loudnorm` 不做（留给 take 级）。全部候选写入 `audio/ep01/tts/segNN_lineMM_seedK.wav` 与 `tts_candidates.csv`，默认选相似度最高者，可被人工 `--pick` 覆盖。
- **输出**：每段一条按句定位好的 `segNN.dlg.tts.wav` + 候选清单。

### 4.6 `lipsync_v2v.py`
- **用途**：链路 B 的改嘴（LatentSync / MuseTalk），封装 24 ↔ 25 fps 往返与校验。
- **CLI**：`lipsync_v2v.py final/ep01/seg03.mp4 --audio audio/ep01/seg03.dlg.tts.wav --engine latentsync16 --steps 20 --guidance 1.5 --out final/ep01/seg03.ls.mp4`
- **逻辑**：`-itsscale 0.96 … -c:v copy -video_track_timescale 25000` 得 25 fps 副本；音频 `atempo=1.0416667`、16 kHz 单声道；调引擎模板；`-itsscale 1.0416667 … -video_track_timescale 24000` 还原；**硬门**：输出帧数 == 输入帧数、分辨率一致；软门：嘴部区域与原片的逐帧差在无台词区间应接近 0（确认只改了说话段）。失败自动回退到「原片 + 标记 needs_reshoot」。
- **备注**：不处理音频封装——成片音轨永远由 `mix_episode.py` 用原速音频合成。

### 4.7 `audio_lock_plan.py`
- **用途**：链路 C：把对白 wav 排到 H3 时间轴并改写 API 工作流。
- **CLI**：`audio_lock_plan.py edit/ep01.edl.json --workflow workflows/h3_ref2va_dialogue_lock.api.json --out prompts/ep01/`
- **逻辑**：每句 `start_frame = max(18, round(start_s·24))`；相邻句间隔 ≥ 6 帧；段长 = `ceil((末句结束 + 0.2 s + 1.0 s 定格)·24)` 向上吸附到 `17k+5` 且 ≤ 328；溢出则拆段。为每段复制 API 模板并写入：`LoadAudio.audio`、`MiniMaxH3TimedAudio.start_frame / gain_db / label`、`MiniMaxH3ReferenceToVideo.length`；`DialogueAudioLock` 保持 `200 / 250 / 100 / prevent_clipping / error`；同时调用现有 `lint_prompt.py` 确认提示词里 `<d>` 文本与 TTS 文本逐字一致。Autogrow 输入按 skill 既有规则写成嵌套对象（`"timed_audios": {"timed_audio_0": [id, 0]}`）。
- **输出**：`segNN.api.json` + `lock_plan.csv`（每句帧位、每段帧数）。

### 4.8 `beat_grid.py` ★
- **用途**：配乐节拍网格与切点吸附建议。
- **CLI**：`beat_grid.py audio/music/ep01_90bpm.wav --bpm 90 --edl edit/ep01.edl.json --division 2 --max-shift 3`
- **逻辑**：ffmpeg 解码 11 kHz 单声道 → 10 ms 能量差分得 onset 包络 → 已知 BPM 时只搜相位（梳状求和最大），未知时在 60–180 BPM 以 0.5 步长联合搜索 → 对每个切点求最近的 1/`division` 拍格点，偏移 ≤ `max-shift` 帧则建议移动（通过增减该段 `in_frame / out_frame` 的余量实现，绝不变速画面）。
- **原型实测**：96 BPM、相位 0.2 s 的合成节拍，检出 96.0 BPM、相位 0.21 s。真实音乐上的稳健性未验证（有 librosa 时可替换检测器）。

### 4.9 `export_capcut_draft.py` ★
- **用途**：EDL → 剪映草稿（Windows 版剪映里可继续精修、调色、换字体、导出）。
- **CLI**：`export_capcut_draft.py edit/ep01.edl.json --drafts "D:/JianyingPro Drafts" [--srt subs/ep01.srt] [--international]`
- **依赖**：`pip install pyJianYingDraft`（0.3.1 实跑；`--international` 用 `pyCapCut`）。
- **骨架（已实跑）**：
```python
import pyJianYingDraft as draft
from pyJianYingDraft import trange, SEC, TrackSpec, TrackType, TextStyle, ClipSettings
us = lambda frames: round(frames * SEC / fps)                    # 帧 → 微秒，累计用帧数算
script = draft.DraftFolder(root).create_draft(name, 1920, 1080, fps=24, allow_replace=True)
script.append_tracks([TrackSpec(TrackType.audio, "music"), TrackSpec(TrackType.audio, "dialogue_a"),
                      TrackSpec(TrackType.audio, "dialogue_b"), TrackSpec(TrackType.video, "picture"),
                      TrackSpec(TrackType.text, "subtitle")])
v = draft.VideoSegment(path, trange(t, us(n)), source_timerange=trange(us(in_f), us(n)), volume=0.0)
a = draft.AudioSegment(dlg, trange(t, us(n) + lcut), source_timerange=trange(us(in_f), us(n) + lcut)); a.add_fade("0.01s", "0.12s")
script.add_segment(v, "picture").add_segment(a, "dialogue_a" if i % 2 == 0 else "dialogue_b")   # 交错两轨容纳 L-cut 重叠
script.import_srt(srt, track_name="subtitle", text_style=TextStyle(size=7.0, auto_wrapping=True),
                  clip_settings=ClipSettings(transform_y=-0.78)); script.save()
```
- **注意**：画面片段 `volume=0.0`（声音全部走独立音轨，避免与 stem 重复）；素材用绝对路径；新版剪映读不了的是「加密模板」，**生成**草稿不受影响；需要进再退出一个草稿或重启剪映才刷新列表。ducking 与总线响度剪映里没有等价物——草稿用于画面与字幕精修，最终音频仍以 `mix_episode.py` 的 `ep01.mix.wav` 为准（作为一条独立音轨放进草稿并静音其余音轨即可）。

### 4.10 `export_otio.py` ★
- **用途**：EDL → `.otio` + FCP7 XML + CMX3600 EDL（Resolve / Premiere）。
- **依赖**：`pip install opentimelineio otio-fcp-adapter otio-cmx3600-adapter`（0.18.1 实跑）。
- **骨架**：`Timeline` → `Track(kind=Video|Audio)` → `Clip(media_reference=ExternalReference(target_url="file://…", available_range=…), source_range=TimeRange(RationalTime(in_f, 24), RationalTime(n, 24)))` → `otio.adapters.write_to_file(tl, "ep01.otio")`；`adapter_name="fcp_xml"` / `"cmx_3600"`。L-cut 用第二条音轨 + `Gap` 表达。
- **注意**：EDL 的 reel 名被截成 8 字符（`OTIO TRUNCATED REEL NAME`），文件名请保持 `segNN` 前缀唯一。

### 4.11 `deliver.py`
- **用途**：母版 → 各平台版本 + 字幕烧录 + 验收报告。
- **CLI**：`deliver.py final/ep01.mp4 --preset youtube_1080p24|bilibili_1080p|douyin_h|tiktok_h --ass subs/ep01.ass --out deliver/`
- **预设**：`youtube_1080p24` = H.264 High、`-g 12 -bf 2`、8 Mbps（2-pass 或 `-crf 16 -maxrate 12M -bufsize 24M`）、AAC 384k 48 kHz；`bilibili_1080p` = 平均 ≤ 6000 kbps、峰值 ≤ 24000 kbps、AAC 320k（社区口径，可在预设文件里改）；`douyin_h / tiktok_h` = 1080p、10 Mbps、30 fps 可选（`--interp rife` 时先按镜头分段插帧）、`lutyuv=y='max(val\,36)'` 黑位保护可选。
- **验收**：`ffprobe` 编码参数、`ebur128` 响度、`blackdetect` / `freezedetect`（复用 `qc_probe.py`）、字幕末帧不越过片尾。

### 4.12 `qc_audio.py`（对现有 `qc_probe.py` 的补充）
- **逐 take 指标**：积分响度 / 真峰值 / 采样率（应为 32 kHz 原生）、对白占比（VAD 或 stem 能量）、各说话人中位 F0 与锚点差、ASR 回读相似度（large-v3 或 Qwen3-ASR）、起始音节检测（前 0.6 s 内 < 0.3 s 的高能段）、句尾与切点间距 ≥ 0.2 s。
- **输出**：`qc/ep01_audio.csv` + 失败码（沿用 `F-DIALOGUE-TEXT / F-LIPSYNC`，新增 `F-VOICE-DRIFT`、`F-AUDIO-LEAK`、`F-LOUDNESS`）。

## 可写进 skill 的规则

1. **先分 stem 再处理**：H3 音轨先 `aresample=48000` 存 24-bit WAV，再用 `audio-separator … --model_filename model_bs_roformer_ep_317_sdr_12.9755.ckpt`（或 ComfyUI `AudioStemSeparate(htdemucs)` / `MelBandRoFormerSampler`）拆成对白与非人声两条；VC、TTS 替换、降噪只作用于对白 stem。（VideoLingo；官方 InfiniteTalk / LTX A2V 模板）
2. **音色统一前先量化漂移**：逐句测中位 F0，与角色锚点差 > 0.5 半音才转换；锚点用用户认可的 H3 原声 ≥ 6 s，存 `bible/voices/<角色>.wav`。（本簇原型；h3-drama-kit playbook 08）
3. **seed-vc 守时**：一律 `--length-adjust 1.0`；首选 `--f0-condition True --auto-f0-adjust True --diffusion-steps 30`（44.1 kHz 模型）；转换后时长差 ≤ 1 帧、包络偏移 ≤ 20 ms 才贴回，否则保留原声。（seed-vc README）
4. **第 3 集起换训练式 VC**：每个主角攒 5–10 分钟认可对白训 RVC（Applio）或 GPT-SoVITS V5，替换逐句零样本转换。（RVC / GPT-SoVITS README）
5. **换台词在生成前决定**：需要改词、外语版、逐字精确台词时走音频锁，不要先生成再改嘴。接线 `MiniMaxH3TimedAudio(start_frame ≥ 18)` → `MiniMaxH3DialogueAudioLock(protect_before_ms 200, protect_after_ms 250, feather_ms 100, prevent_clipping, error)` → 采样 → `VAEDecodeAudio` → `MiniMaxH3DialogueAudioFinalize`。（badgids/ComfyUI-H3-ExactAudioLock 源码与 `05_t2v_dialogue_audio_lock.json`）
6. **锁帧与引导同源**：`TimedAudio.start_frame` 输出同时接 `MiniMaxH3AddGuide.frame_idx` 并喂同一段 audio；提示词仍写同一句 `<d>[Chinese] …</d>` 并点名说话人，TTS 文本与 `<d>` 逐字一致。（同上，示例 10）
7. **整条锁用 `exact_audio`**：歌曲 / 口播用 `MiniMaxH3ExactAudioLock(sum, error)`，成片音轨接 `exact_audio` 而不是 `VAEDecodeAudio`；不要与 Context Loop 的 `lock_source_audio` 同开。（同上 README）
8. **声线资产一物两用**：用 Qwen3-TTS `generate_voice_design` 为每个角色生成 6–10 s 单人干声，既作 H3 `<Audio N>` 又作 TTS 克隆参考（`create_voice_clone_prompt`）。（Qwen3-TTS README）
9. **中文配音默认 IndexTTS-2.5**：`spk_audio_prompt=锚点`、`emo_audio_prompt=原句或情绪样本`、`emo_alpha 0.6–0.8`、`use_random=False`、多音字用 `<行|HANG2>`；贴窗用 `duration_factor` 且限制在 0.85–1.15，超出就改词。（index-tts README）
10. **必须定长时**用 OmniVoice `duration=秒` 或 AuK `--gen_seconds 秒`；每句 2–3 个 seed，ASR 回读相似度 ≥ 0.90 才入选。（OmniVoice / AuK README）
11. **事后改嘴只救真人中近景**：LatentSync `--inference_steps 20 --guidance_scale 1.5`（糊嘴升到 2.0，抖动降到 1.2），1.6 需 ≥ 18 GB、1.5 需 ≥ 8 GB；动漫脸、遮挡、大侧脸直接重拍。（LatentSync README）
12. **25 fps 模型的帧率往返用时间戳重解释**：`ffmpeg -itsscale 0.96 -i in.mp4 -an -c:v copy -video_track_timescale 25000`，音频 `atempo=1.0416667`；回程 `-itsscale 1.0416667 … -video_track_timescale 24000`；前后帧数必须相等，成片只用原速音频。（本簇 ffmpeg 6.1.1 实跑）
13. **响度两遍走**：逐 take 对白 stem `loudnorm=I=-16:TP=-1.5:LRA=11` 先测后调（`linear=true`，滤镜后补 `aresample=48000`），成片 −14 LUFS；日志 `Normalization Type` 不是 Linear 时改固定增益 + `alimiter=limit=0.89`。（本簇实跑；skill 既有目标值）
14. **硬切拼接不用 `acrossfade`**（会缩短总长）：对白 `atrim → afade(in 10 ms / out 120 ms) → adelay → amix=normalize=0`，L-cut 0.25 s；验收音画时长差 ≤ 1 帧。（本簇实跑）
15. **配乐 ducking 参数**：`sidechaincompress=threshold=0.05:ratio=4:attack=20:release=400:knee=4`（对白 −16 LUFS 时约压 8 dB）；要 −12 dB 用 `threshold=0.03:ratio=8`。（本簇实测）
16. **配乐带 BPM 生成**：ACE-Step 1.5 XL turbo，`TextEncodeAceStepAudio1.5` 的 `bpm`、`duration`、`keyscale` 填实数，KSampler 8 步 cfg 1 euler / simple、`ModelSamplingAuraFlow 3`；分镜阶段就定 BPM，硬切点吸附 1/4 或 1/8 拍且移动 ≤ 3 帧；H3 侧 `non_diegetic_music: N/A`。（ComfyUI 核心 `nodes_ace.py`；官方模板）
17. **环境声每场景一条**：Stable Audio 3 small-sfx（`stable_audio_3_small_sfx.safetensors`，8 步 cfg 1 lcm）出 30–60 s room tone，`highpass=150,lowpass=6500`、−34 dB 起步连续铺；不要逐段拼 H3 的环境声。（Comfy-Org/stable-audio-3 模板；skill 既有 −32…−48 dB 区间）
18. **拟音许可**：商单的视频配音效用 HunyuanVideo-Foley XL（`--model_size xl --enable_offload`，8 GB）；MMAudio 权重 CC-BY-NC、F5-TTS 权重 CC-BY-NC、Fish S2-Pro Research License，只能用于非商用样片。（各仓库 License 段）
19. **字幕时间用强制对齐**：文本取分镜 JSON 锁定原文，时间取 `Qwen/Qwen3-ForcedAligner-0.6B`（备选 WhisperX 中文对齐模型 `jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn`）；入点 −0.08 s、出点 +0.25 s、最短 0.8 s、≤ 9 字 / s、相邻 ≥ 2 帧、吸附到帧。（Qwen3-ASR README；本簇原型）
20. **1080p 字幕样式**：中文 58 px / 英文 36 px，`Outline 3`、`MarginV 96 / 52`、`MarginL/R 160`、单行 ≤ 18 汉字、`YCbCr Matrix: TV.709`；烧录 `-vf subtitles=ep01.ass`，软字幕另存 `.srt`。（本簇 libass 实跑）
21. **每集双出口工程**：`export_capcut_draft.py`（pyJianYingDraft 0.3.1：画面片段 `volume=0.0`、对白交错两轨、`import_srt` 进文本轨、成品混音单独一轨）+ `export_otio.py`（`.otio` 与 FCP7 XML，需 `otio-fcp-adapter`）。（本簇原型实跑）
22. **母版编码**：1920×1080、24 fps、H.264 High、`-g 12 -bf 2`、yuv420p + bt709 三标记、AAC 48 kHz、`-movflags +faststart`；YouTube 1080p 给 8 Mbps（24–30 fps）/ 12 Mbps（48–60 fps）、立体声 384 kbps。（YouTube 官方上传编码建议）
23. **要 30 / 60 fps 就按镜头分段用 RIFE 4.25 插帧**，不跨硬切；`fps=30` 复制帧只作兜底；能按 24 fps 交付就不插。（Practical-RIFE README；YouTube 建议按原帧率上传）
24. **音频批次与 H3 不同驻**：TTS / VC / 分离 / 改嘴开始前先调 ComfyUI `/free`，整批做完再回去生成；AuK 必须 `--cpu_offload`（否则 ~25 GiB），Fish Drama 3 不在本机跑。（AuK README 显存表；Drama 3 模型卡）
25. **长旁白与画外音直接 TTS 进混音**，不经 H3；H3 的 VO 只用于 15 s 内 ≤ 20 字的贴画面短句。（skill 既有 VO 限额 + 本簇结论）

## 未覆盖

- **没有在 4090 上实跑任何模型**：所有 TTS / VC / 口型 / 拟音 / 配乐的速度、显存、中文听感、动漫脸有效性都来自作者自报或推断；seed-vc 44 k F0 模型与 V2 在 H3 素材上的 A/B、音频锁 + Turbo 8 步对画面运动的影响、LatentSync 在 1344×768 H3 画面上的成功率都需要用户侧样片验证。
- **商业服务未调研**：ElevenLabs v4、MiniMax Speech / Music、Suno / Udio、HeyGen、VEED、sync.so 只确认了 ComfyUI API 模板存在，价格、条款、质量未核实。
- **平台规范只核实了 YouTube**：B 站只有社区专栏口径，抖音 / 快手 / TikTok 未找到官方编码与响度规范；各平台 AI 生成内容标注政策、音乐版权、水印（Chatterbox Perth、LTX VideoSeal / AudioSeal、Fish 水印）未覆盖。
- **未读的模型**：Higgs Audio v3（Research License）、Ming-3.0-tts（MIT，awesome-ai-voice 称其在 Artificial Analysis 可控语音榜开源第一）、dots.tts、Confucius4-TTS、ZONOS3、SoulX-Singer / DiffSinger（歌声）、Foley-Omni、AudioX-Turbo、UniAVC、Lip Forcing / HighSync / DiFlowDubber 只看了元数据。
- **H3 生态本轮未重读**：T8 audio-T8（62 节点）、Audio-Guide-Feather、NativeAudioLock、animede lipsync-mv 沿用 `docs/13-github-survey/` 的结论；`caitongbo/…DigitalHuman`（★5，GPL-3.0）只读了核心节点源码与示例工作流，未跑。
- **未展开的环节**：多说话人自动 diarization → 分人 VC（pyannote 4）、对白去混响后的「重新加房间声」参数、5.1 / 空间音频、自动同场配色与 ACES 流程（只验证了 `lut3d` / `lutyuv` 语法）、Remotion 图形包装、DaVinci Resolve / Premiere 脚本 API 细节、SyncNet 口型评分脚本。
- **环境风险未验证**：TTS-Audio-Suite（主环境 Transformers 5）与 H3 ComfyUI 环境的依赖冲突；Windows 上 `triton-windows`、flash-attn、SGLang / vLLM（多为 Linux）的安装；pyJianYingDraft 生成的草稿在用户实际剪映版本上的打开情况。

## 附：来源与核验记录

**读过的一手来源（2026-11-21）**
- TTS：index-tts/index-tts（README、LICENSE、HF `IndexTeam/IndexTTS-2.5`）；QwenAudio/CosyVoice（README、`example.py`、HF `FunAudioLLM/Fun-CosyVoice3-0.5B-2512`）；OpenBMB/VoxCPM；QwenLM/Qwen3-TTS；k2-fsa/OmniVoice；RVC-Boss/GPT-SoVITS；Tencent-Hunyuan/AuK（README、`docs/COOKBOOK.md`、`docs/COMFYUI.md`）；fishaudio/fish-speech（README、LICENSE、HF `drama-3` / `drama-3-int4` / `s2-pro`）；OpenMOSS/MOSS-TTS；FireRedTeam/FireRedTTS3；resemble-ai/chatterbox；microsoft/VibeVoice；SWivid/F5-TTS（README、`utils_infer.py`）；diodiogod/TTS-Audio-Suite（README、`SRT_IMPLEMENTATION.md`）；wildminder/awesome-ai-voice（95 个 TTS 条目的总表）。
- VC / 口型：Plachtaa/seed-vc；bytedance/LatentSync（README、`inference.sh`）；TMElyralab/MuseTalk；MeiGen-AI/InfiniteTalk；Playmate111/ComplexSync；chanjing-ai/Chanjing-Avatar-V2V-5B；PedroMarinhoDev/ComfyUI-LongCat-Avatar；Lightricks/LTX-2（README、`packages/ltx-pipelines/docs/pipelines.md`）；justdubit/just-dub-it；Kedreamix/Awesome-Talking-Head-Synthesis。
- H3：badgids/ComfyUI-H3-ExactAudioLock（README、`docs/DIALOGUE_PARTIAL_LOCK.md`、`__init__.py`、4 份示例工作流）；caitongbo/ComfyUI-MiniMaxH3-LongVideo-DigitalHuman（`h3_digital_human_audio_context.py`、示例工作流）；本仓库 skill 与 `docs/13-github-survey/`。
- 音效 / 配乐 / 分离 / ASR：hkchengrex/MMAudio；Tencent-Hunyuan/HunyuanVideo-Foley；QwenAudio/ThinkSound（PrismAudio）；ace-step/ACE-Step-1.5；multimodal-art-projection/YuE；HeartMuLa/heartlib；nomadkaraoke/python-audio-separator；facebookresearch/sam-audio；HF `nvidia/NVIDIA-NemotronLabs-RE-USE`、`JusperLee/TIGER-DnR`；QwenLM/Qwen3-ASR；m-bain/whisperX（README、`alignment.py`、`pyproject.toml`）；SYSTRAN/faster-whisper；jianfch/stable-ts。
- 剪辑：GuanYixuan/pyJianYingDraft（README、`demo.py`、pip 0.3.1 API）；GuanYixuan/pyCapCut；Hommy-master/capcut-mate；renezander030/capcut-cli；WyattBlue/auto-editor；AcademySoftwareFoundation/OpenTimelineIO；Huanshere/VideoLingo；jianchang512/pyvideotrans；hzwer/Practical-RIFE；Fannovel16/ComfyUI-Frame-Interpolation。
- ComfyUI 核心：`comfy_extras/nodes_ace.py`、`nodes_audio.py`（master）；`Comfy-Org/workflow_templates`（2026-10-31 提交）中 `audio_*`、`audio-chatterbox_*`、`utility-audioseparation`、`templates-wan2_1_infinitetalk_music`、`video_humo`、`video_ltx_2_audio_to_video`、`audio_yue2_*`、`audio_stable_audio_3_medium`。
- 平台：YouTube 帮助「Recommended upload encoding settings」（support.google.com/youtube/answer/1722171）；B 站 / 抖音仅检索到社区文章，未采信为规范。

**本次实跑（合成素材：3 段 1344×768@24 fps + 32 kHz 立体声「说话」音频 + 48 kHz 配乐）**
- ffmpeg 6.1.1：两遍 `loudnorm`（−34.9 / −48.7 / −27.4 LUFS → −16.0 / −16.1 / −16.1，Linear）；帧精确裁切 + 7:4→16:9 + `concat -c copy`（354 帧）；时间线混音 + 环境声 + sidechain ducking + 限幅 + 成片 `loudnorm`（−14.0 LUFS，音画均 14.750 s）；ASS / SRT 烧录（文泉驿字体）；`lut3d` 恒等 LUT + `lutyuv` 黑位（YMIN = 36）；24↔25 fps 时间戳往返（144 帧不变）；`fps=30`、`minterpolate`、`xfade` 4 帧叠化（232 帧）。
- Python 原型：`retime_subtitles`（difflib 映射）、`unify_voice` 的偏移与 F0 检测、`beat_grid`（梳状搜索）、`export_capcut_draft`（pyJianYingDraft 0.3.1）、`export_otio`（OpenTimelineIO 0.18.1 + fcp / cmx3600 适配器）。原型文件暂存于 `/tmp/claude-0/-home-user/d049cf81-589a-59f7-bbcd-0b44f6d3b87d/scratchpad/wfstudy/audio-post/fftest/`（会话临时目录，可能被清理；关键逻辑已内联进 §4）。
- 研究笔记：`/tmp/claude-0/-home-user/d049cf81-589a-59f7-bbcd-0b44f6d3b87d/scratchpad/wfstudy/audio-post/notes/NOTES.md`（同为临时目录）。
