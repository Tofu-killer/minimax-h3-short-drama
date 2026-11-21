# 声音后期：对白从哪来、怎么统一、怎么混

> 依据：仓库里的调研报告 `docs/14-ai-video-workflows/04-audio-lipsync-and-post.md`（不随 skill 安装，见 <https://github.com/Tofu-killer/minimax-h3-short-drama/blob/main/docs/14-ai-video-workflows/04-audio-lipsync-and-post.md>；2026-11-21 快照，许可与文件名来自各仓库 README / 模型卡）。本页的 ffmpeg 混音、字幕对时、工程导出已由 skill 脚本实现并在真实 H3 成片上跑通（见 `qc-and-assembly.md` 页首）；**所有模型（TTS / 变声 / 改嘴 / 拟音 / 配乐）都没有在 4090 上实跑过**，速度与显存是作者自报，标「待 A/B」的先做样片。
> 下载只走 HuggingFace / GitHub；只在 ModelScope 的权重（如 ComplexSync）视为不可用。

## 1. 三条链路，先选再做

差别只在「对白 stem 从哪来、画面要不要动」。

| | A 保留 H3 原声 | B 重配 + 改嘴 | C 先音后画 |
|---|---|---|---|
| 对白 | H3 原生表演，最自然 | TTS / 克隆重配 | TTS / 克隆，生成前就定稿 |
| 画面 | 不动 | 改嘴或重拍 | H3 听着锁定的音频生成 |
| 台词可控 | 只能抽卡（`qc_dialogue.py` 把关） | 文本 100% 可控 | 文本 100% 可控 |
| 最大风险 | 段间音色、响度不齐 | 改嘴糊 / 侧脸与动漫脸失败；两次生成误差叠加 | 音频锁下画面运动变少（待 A/B）；多人时张嘴的人不对 |
| 用在 | **真人向对白短剧默认** | 画面不能重拍、但台词必须改 / 译制 | 漫剧、MV、口播、广告、多语言版本、台词密要卡点的集 |

**能 A 不 B；确定要换声音就在生成前决定（走 C），不要先生成再走 B。**

## 2. 链路 A：skill 现在能直接跑的部分

```
qc_dialogue.py（逐 take 台词把关）→ 精修 → make_edl.py → retime_subtitles.py → mix_episode.py → 导出
```
片段自带的声音（`"audio": "native"`）直接进混音：按台词区间对齐到 −16 LUFS、L-cut 0.25 s、成片 −14 LUFS。命令与字段见 `qc-and-assembly.md` §3。按收益从高到低的加法：

1. **环境声底**：每个场景一条 30–60 s 的 room tone 循环铺满，填掉段与段之间环境声的断层，比逐段拼 H3 自己的环境声干净。写进 EDL：`"ambience": {"office": {"file": "audio/ep01/office_tone.wav", "gain_db": -34}}`（键 = 分镜的 `scene_id`；脚本带限 150–6500 Hz）。来源：Stable Audio 3 small-sfx（`Comfy-Org/stable-audio-3`，ComfyUI 模板，8 步 CFG 1），或任何干净的现成素材。
2. **配乐**：H3 侧 `music: N/A`，剪辑阶段统一铺。写进 EDL：`"music": {"file": "audio/ep01/score.wav", "gain_db": -6, "fade_in": 0.5, "fade_out": 1.0, "loop": false}`。对白处自动压低：脚本按 EDL 里每句台词的起止时间画一条增益包络（默认压 9 dB，句前 0.15 s 开始下压、句后 0.3 s 回升，相隔 < 0.8 s 的句子连成一段），相当于剪辑师手打关键帧；深度改 `"duck": {"depth_db": 12}`。没有台词时间（没跑 `retime_subtitles.py`）时退回 sidechain 压缩，实测在真实对白上只压得动约 3–6 dB，而且片段里的音效也会把配乐压下去——所以先对时再混音。本地生成配乐：ACE-Step 1.5 XL turbo（ComfyUI 原生节点 `TextEncodeAceStepAudio1.5`，`bpm`、`duration` = 成片秒数、`keyscale` 填实数，8 步 CFG 1）。分镜阶段就定 BPM，硬切点落在 1/4 或 1/8 拍、移动 ≤ 3 帧。
3. **对白 / 非人声分轨**（某段 `mix_episode.py` 报「对白会偏低」时做）：`pip install "audio-separator[gpu]"`，`audio-separator seg.wav --model_filename model_bs_roformer_ep_317_sdr_12.9755.ckpt --output_dir stems/ --output_format WAV`（先 `ffmpeg -i seg.mp4 -vn -af aresample=48000 -c:a pcm_s24le seg.wav`；H3 原生是 32 kHz），或 ComfyUI 核心 `AudioStemSeparate`。把该段 EDL 的 `"audio"` 指向人声 stem、`"nondialogue"` 指向伴奏 stem，对白就能单独加到位。
4. **音色统一**（先量化再处理）：每个主角存一条用户认可的 H3 原声 ≥ 6 s 作锚点（`bible/voices/<角色>.wav`，也用作 H3 的 `<Audio N>`）。`scripts/voice_check.py edit/ep01.edl.json --episode episodes/ep01.json --out qc/voice` 逐句测中位基频并列出与锚点的半音差，> 0.5 半音的句子才考虑转换；零样本用 seed-vc（`Plachtaa/seed-vc`，`--length-adjust 1.0 --f0-condition True --auto-f0-adjust True --diffusion-steps 30`），转换后时长差 ≤ 1 帧、包络偏移 ≤ 20 ms 才贴回，否则保留原声。连载第 3 集起每个主角攒 5–10 分钟认可对白训 RVC 或 GPT-SoVITS V5（`lj1995/GPT-SoVITS`），替换逐句零样本。**不要全量过变声**——极端情绪句会被转坏。量化这一步有脚本（合成嗓音上误差 < 1.5%；在一支台词下面压着音效的真实 H3 成片上 5 句里只有 1 句读得出基频，其余如实标为 `unreadable`——混音复杂时先做上一步的分轨，在人声 stem 上测）；变声本身 skill 没有脚本，待 A/B。喊叫和耳语本来就高或低，表格只用来决定**先听哪几句**。

链路 A 不改画面，所以任何改变时长的处理（变速、去静音、`length-adjust ≠ 1`）都禁止：每一步之后帧数不变、对白起点不变。

## 3. 链路 C：先定声音，再生成画面

1. 每句台词用 TTS 出 2–3 个 seed，**ASR 回读与锁定原文相似度 ≥ 0.90 才入选**，再人工听一遍——在花 GPU 之前把「台词念错」消掉。
2. 按音频时长排段：每句起点 ≥ 第 18 帧（0.75 s 预卷），句尾留 ≥ 0.2 s + 1 s 定格，段长取 17k+5 帧。
3. 接线（custom node `badgids/ComfyUI-H3-ExactAudioLock`）：`MiniMaxH3TimedAudio(start_frame)` → `MiniMaxH3DialogueAudioLock(protect_before_ms 200, protect_after_ms 250, feather_ms 100, mix_policy prevent_clipping, overflow_policy error)` → 采样 → `VAEDecodeAudio` → `MiniMaxH3DialogueAudioFinalize`；同一个 `start_frame` 同时接 `MiniMaxH3AddGuide.frame_idx` 并喂同一段音频。提示词照常写同一句 `<d>[Chinese] …</d>` 并点名说话人，TTS 文本与 `<d>` 逐字一致。环境声仍由 H3 生成。
4. 歌曲 / 口播整条锁用 `MiniMaxH3ExactAudioLock`，成片音轨接它的 `exact_audio` 输出而不是 `VAEDecodeAudio`。
5. 不装节点的退路：六段式里 `<Audio 1>: fully_copy`（语音有约 0.45 s 的系统位移，排期里预补）；只借音色写 `<Audio 1>: reference - …`（官方的音频标记是 `fully_copy / partially_copy / reference / weak_reference`，`attribute_transfer` 只用于画面）。

长旁白和画外音直接 TTS 进混音，不经 H3；H3 的画外音只用于 15 s 内 ≤ 20 字的贴画面短句。

## 4. 链路 B：只在画面不能重拍时用

- **首选仍是 H3 重拍**：原首帧作 `first_frame` + 同提示词 + 上面的音频锁。
- 事后改嘴只救**真人中近景**：LatentSync 1.6（`ByteDance/LatentSync-1.6`，512 px，≥ 18 GB，`--inference_steps 20 --guidance_scale 1.5`）；MuseTalk 1.5（`TMElyralab/MuseTalk`，256 px，中远景 / 预览）。动漫脸、遮挡、大侧脸直接重拍。
- 这两个模型按 25 fps 训练。24 fps 素材用**时间戳重解释**往返，不重编码：`ffmpeg -itsscale 0.96 -i in.mp4 -an -c:v copy -video_track_timescale 25000 in25.mp4`，音频 `atempo=1.0416667`；改完 `-itsscale 1.0416667 … -video_track_timescale 24000` 转回，前后帧数必须相等，成片只混原速音频（ffmpeg 6.1 实跑：362 帧往返后逐帧一致）。
- 定长配音贴回原时间窗：IndexTTS-2.5 的 `duration_factor` 限制在 0.85–1.15，超出就改词；必须定长用 OmniVoice `duration=秒`。

## 5. 工具速查

| 用途 | 工具（仓库） | 许可 | 结论 |
|------|-------------|------|------|
| 字幕 / 质检的词级时间 | faster-whisper（skill 脚本默认）；`Qwen/Qwen3-ForcedAligner-0.6B`（已知文本强制对齐，更准） | MIT / Apache-2.0 | 采用。强制对齐器装在自己的环境里，包一个输出 `[{"text","start","end"}]` JSON 的小脚本，用 `--aligner cmd --aligner-cmd "python align.py {audio} {text}"` 接进 `retime_subtitles.py` / `qc_dialogue.py`（包装脚本需自写，未随 skill 提供） |
| 中文配音（默认） | IndexTTS-2.5（`IndexTeam/IndexTTS-2.5`，代码 `index-tts/index-tts`） | bilibili 模型许可：可商用，超大体量另授权 | 采用：音色与情感分开给（`spk_audio_prompt` = 锚点，`emo_audio_prompt` = 情绪样本，`emo_alpha 0.6–0.8`），多音字 `<行\|HANG2>` |
| 配音备选 / 方言 | Fun-CosyVoice3（`FunAudioLLM/Fun-CosyVoice3-0.5B-2512`）；VoxCPM2（`openbmb/VoxCPM2`，48 kHz） | Apache-2.0 | 采用 |
| 造声线 | Qwen3-TTS VoiceDesign → Clone | Apache-2.0 | 采用：出 6–8 s 单人干声（模型接受 2–15 s，短样本更稳），既作 H3 `<Audio N>` 又作克隆参考 |
| 定长配音 | OmniVoice（`k2-fsa/OmniVoice`） | 见仓库 | 试用 |
| 变声统一 | seed-vc；长连载 RVC / GPT-SoVITS V5 | 见仓库 | 采用（只转漂移句） |
| 拟音 | HunyuanVideo-Foley XL（`--enable_offload` 约 8 GB） | 见仓库 | 试用；商单别用 MMAudio（权重 CC-BY-NC） |
| 口播 / 唱歌整段重生成 | InfiniteTalk（`MeiGen-AI/InfiniteTalk`）、LongCat-Video-Avatar 1.6 | Apache-2.0 / MIT | InfiniteTalk 的用法见 `beyond-h3.md`；LongCat 只记了名字，没有评估 |

许可陷阱：MMAudio、F5-TTS 权重 CC-BY-NC；Fish S2-Pro 为 Research License；Fish Audio Drama 3 表演最强但 int4 也要 22 GB、商用限年收入 < 50 万美元——不在本机跑。

**显存纪律**：音频模型（5–17 GB）不能和 H3 同驻。TTS / 变声 / 分离 / 改嘴开始前先让 ComfyUI `/free`，整批做完再回去生成；`faster-whisper` 默认跑 CPU 就是为了不抢显存。

## 6. 没验证的（样片阶段各做一次 A/B）

seed-vc 44 kHz F0 模型在 H3 对白上的听感；音频锁 + Turbo 8 步对画面运动的影响；LatentSync 在 1344×768 H3 画面上的成功率；各 TTS 在 4090 上的速度与中文听感；TTS-Audio-Suite 与 H3 的 ComfyUI 环境是否有依赖冲突。
