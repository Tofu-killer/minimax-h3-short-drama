# QC 与拼接

> 本页脚本的验证口径：`qc_probe.py`、`qc_dialogue.py`、`contact_sheet.py`、`make_edl.py`、`retime_subtitles.py`、`mix_episode.py`、两个导出脚本都在一支 38 s 的真实 H3 成片（切成 5 段）上跑通过（Linux、ffmpeg 6.1、CPU）：切点 7 / 7 检出且无误报，复读台词被拦下，成片 910 帧与计划一致、音画偏移 0 ms、−14.2 LUFS / −1.6 dBTP。**没有在用户的 Windows + 4090 上跑过**，剪映草稿也没有在剪映里打开过——第一次用先拿样片段走一遍。

## 1. QC：脚本先筛，人只看联络表

技术通过 ≠ 整体通过。按便宜到贵的顺序过，前一道不过就不做后一道：

| 顺序 | 门 | 命令 | 拦什么 |
|------|----|------|--------|
| 1 | 技术 | `scripts/qc_probe.py "takes/ep01/**/*.mp4" --episode episodes/ep01.json --freeze-tail 1.0 --out qc/probe` | FAIL：缺视频 / 音轨、尺寸或帧率不符、时长偏差 > 0.6 s、采样峰值 > −1 dB、定格尾之外冻结 > 1 s 或黑场 > 0.25 s。WARN：**镜头数与分镜不符**（少切 = 两镜糊成一镜，多切 = 自己加了镜头）、切点偏移 > 0.3 s、首尾 8 帧内的跳帧（拼接处会闪）、动作量 < 1.2（近乎静止） |
| 2 | 台词 | `scripts/qc_dialogue.py --episode episodes/ep01.json --targets "takes/ep01/**/*.mp4" --out qc/dialogue` | FAIL：整体相似度 < 0.72（`F-DIALOGUE-TEXT`）、句首 / 句尾 3 字没听到、识别字数 > 原文 × 1.15 + 2（复读 / 加词）、无台词段出现 ≥ 2 个词。WARN：首字晚于 2.5 s、末字离可用结尾 < 0.2 s |
| 3 | 身份 | `scripts/identity_gate.py --episode episodes/ep01.json --targets "takes/ep01/**/*.mp4" --out qc/identity` | 真人脸：换人、克隆脸、多出的人、缺席；先看自检（两个角色互相 ≥ 0.363 = 撞脸，回去改角色设计） |
| 4 | 联络表 + 人眼 | `scripts/contact_sheet.py "takes/ep01/s03/*.mp4" --freeze-tail 1.0` | 下面的清单 |
| 5 | VLM 评分（可选） | `assets/judge-take-prompt.md` | 事实 / 身份 / 画面三张小评分表 |

- **切点对账**用分镜里各镜的 `start`，容差 ±0.5 s；切点检测不靠 ffmpeg 的 scene 阈值（同一房间的两镜 0.19–0.28，飞舞的纸张 0.30，分不开），而是看「切点前后 4 帧均值的台阶 + 比安静一侧高 4 倍 + 之后画面不回来」（`scripts/h3lib/signals.py`）。标定素材只有一支片子：WARN 先看联络表再动手，要当硬门用 `--strict-cuts`。叠化 / 淡变不算硬切。
- **台词质检不给识别器任何提示**：把台词原文当提示喂给 whisper-small，会「听到」没说过的句子（实测出现别段的台词和乱码）。脚本用无提示转写 + 拼音比对（装 `pypinyin`，同音字误识不扣分）；GPU 空闲时 `--model large-v3 --device cuda` 更准。
- **动作量**（240 px 灰度相邻帧差的中位数）：动作镜 ≥ 2.5、特写表演 ≥ 1.8、< 1.0 接近静帧。
- **身份门禁**阈值（OpenCV SFace）：≥ 0.55 通过、0.363–0.55 警告、< 0.363 不通过；失败帧 > 20% 或第一个有脸的帧失败则整段不通过。侧脸、背影、< 40 px 的脸与动漫脸不参与；分数是警告信号，不是定论。
- **联络表**不再均匀抽 12 帧：首帧、末帧、每个切点前后各一帧、每镜中段、黑场 / 冻结起点，帧下印秒数与标签。人眼看：身份（是否换人）、服装道具（颜色 / 件数 / 是否被换成虚构物）、环境（布局 / 光向 / 色温是否接上一段）、动作（瞬移 / 多肢体 / 手崩）、镜头（是否按分镜切）、下方 15% 字幕安全区。
- **音频抽听**：语言对、没有错人开口、句尾没被截。

硬门 = 文件不可解码、缺镜 / 缺节拍、尺寸帧率时长违约、身份 / 服装 / 道具 / 轴线显著错、音频削波、意外黑帧、冻结；软警 = 轻微拖影、背景小漂移、音量不均。硬门不过只允许原样重试一次。

### 失败码 → 责任层 → 处置

修复从上游开始：资产 → 剧本 / 导演 → 分镜 / 提示词 → 重生成 → 后期。

| 码 | 现象 | 责任层 / 最小修复 | 处置 |
|----|------|------|------|
| F-COUNT | 人数不对、多出一人 | 提示词：精确人数正向锁；群像先写人数 | 必须重生成 |
| F-ID-DRIFT | 换脸 / 换装 / 发型变 | 资产：角色参考（face.png + 全身）是否在参考包；提示词只写不变量 | 必须重生成；只是脸不像且构图都对 → 首帧换头后重出 |
| F-STATE-DRIFT | 位置 / 持物 / 光线与上段不接 | 分镜：`end_state` / `continuity`；同时投喂母版 + 末帧 | 能用切点藏就留用，否则重生成 |
| F-REF-SCOPE | 照抄参考图背景 / 姿势 | 提示词：「参考图只继承身份发型服装」 | 建议重抽，可豁免 |
| F-PROP | 道具虚构 / 替换 | 资产：道具图进参考包 + `the exact item shown in <Picture N>` | 关键道具必须重生成；一闪而过的裁切避让 |
| F-LIPSYNC | 错人张嘴 / 口型不对 | 分镜：一镜一人开口；听者闭嘴；音色只给说话者 | 必须重生成 |
| F-DIALOGUE-TEXT | 台词复读 / 漏句 / 含糊 | 提示词：台词只写一次、预算；步数 ≥ 8 或 12 | 换新 seed（说话节奏跟 seed 走）≤ 3 次 |
| F-SHOTS | 镜头数与分镜不符 | 分镜 / 提示词：`[Shot N] At …` 时码、每镜 ≥ 1.2 s；一段 ≤ 4 镜 | 换 seed 很少有用：先改分镜（拆段或并镜） |
| F-BURN-TEXT | 画面烧出字幕 | 提示词：正文太短（< 350 词）或要求了字幕 | 一闪而过裁掉，否则重生成 |
| F-SEAM | 接缝闪帧 / 曝光跳 | 后期：首尾跳帧裁掉、统一转码；续接见 continuity | 后期修 |

- **先分流再动手**：区间外的毛病裁掉，能后期修的后期修；只有漏关键动作 / 台词、换脸、轴线全反、关键文字乱码才必须重生成。先判是「参考图的毛病」还是「生成的毛病」——参考图错了重抽多少次都错。
- 原因不明时一次只改一个变量；**一眼看清的多处错漏同一轮改完**。原样重抽 1–2 次仍是同一硬伤 → 改词或拆镜，不再抽。
- 仍不行给用户三条出路：留用并靠切点藏住 / 把这条信息挪到相邻段 / 删段（先把剧情信息转移走）。
- 每条问题记：集‑时间码‑镜头‑类型‑证据‑根因‑修复层级‑复验状态；每集出一份 `qc/review.md`，结论取 PASS / PROVISIONAL / REVISE / REJECT。冷观众四问（想要什么 / 什么阻止 / 什么变了 / 为何结局）任一答错即 REVISE。

### 自动闭环的边界

- 只对「技术参数 / 首帧接不上 / 画面自带字幕 / 台词不过」类失败自动换 seed；切点偏移、片尾抖动只标记不重出（重出改善率 29%、0 / 4）。
- 无台词段「擅自说话」的判据：`no_speech_prob < 0.5` 且 ≥ 2 词（`qc_dialogue.py` 的 `unexpected_speech`）。
- VLM 抽帧只作「崩坏 / 水印 / 乱码」与事实核对，不替代动作量与台词检查；每个 take 的评估绑定视频哈希，静帧不足以放行有运动或台词的镜头。

## 2. 抽卡策略

- 草稿档每段 2 个 seed（关键镜 3），**看联络表挑**而不是看视频：先身份一致，再能量 / 表演。
- 中选后**同 seed 精修 / 二采**，不换表演。
- 记录每段「seed / 步数 / LoRA 版本 / 分辨率 / 耗时 / 显存 / 主观评分」到 `logs/takes.csv`，一周后用数据定默认值。
- 同一提示词连抽 3 次都出同一问题 = 提示词问题，不是运气。
- 仅对续接链（可选）：本段评分前二的 take 各出一条下一段草稿，按「本段分 + 下一段分」选——只在链首和情绪高点用。

## 3. 后期：一份剪辑单（EDL）走到底

```
selects/ep01/<段>.mp4（精修后的中选片段，一段一个）
 → scripts/make_edl.py episodes/ep01.json --selects selects/ep01 --out edit/ep01.edl.json
 → scripts/retime_subtitles.py edit/ep01.edl.json --out subs/ep01          # 出 .srt / .ass，并把每句起止时间写回 EDL
 → scripts/mix_episode.py edit/ep01.edl.json --out final/ep01.mp4 [--ass subs/ep01.ass] [--stems-out audio/ep01]
 → scripts/export_capcut_draft.py edit/ep01.edl.json --drafts "<剪映草稿目录>" --report final/ep01.mix.report.json --mix final/ep01.mix.wav
   scripts/export_otio.py edit/ep01.edl.json --out edit/ep01 --mix final/ep01.mix.wav   # 要人工精修时二选一
```

**EDL 是唯一事实源**：字幕、混音、剪映草稿、OTIO 都从它算时间线（`scripts/h3lib/edl.py`，位置 = 帧数累加，不是秒数累加），所以四者的切点逐帧一致。手改都改这一个文件，重跑 `make_edl.py` 不会覆盖已有的段（`--overwrite` 才重建）。

| EDL 字段 | 含义 | 默认 |
|----------|------|------|
| `segments[].in_frame / out_frame` | 用素材的哪几帧（素材自己的帧号，出点不含） | 入点裁 2 帧（H3 开头常带一个起始音节）；末镜标了 `end_hold` 的段裁掉 1 s 定格尾 |
| `segments[].audio` | `"native"` = 用片段自带的声音；路径 = 单独的对白 stem；`null` = 静音 | 有音轨即 `native` |
| `segments[].l_cut / j_cut` | 声音比画面晚收 / 早进的秒数 | 有台词的段 L-cut 0.25 s |
| `segments[].lines[]` | 锁定的台词原文（字幕文字只从这里来）；`start / end` 由 `retime_subtitles.py` 填 | 取自分镜 `dialogue[]` |
| `ambience{场景: {file, gain_db}}` | 每个场景一条循环环境声底，带限 150–6500 Hz | 空；`gain_db` 默认 −34 |
| `music{file, gain_db, fade_in, fade_out, loop, duck{depth_db, …}}` | 全集配乐；按每句台词的起止时间自动压低（增益包络，不受片段里音效影响） | 空；默认压 9 dB。EDL 里没有台词时间时退回 sidechain（真实对白上只有约 3–6 dB） |
| `loudness{dialogue_lufs, program_lufs, true_peak}` | 响度目标 | −16 / −14 LUFS / −1.5 dBTP |

- **字幕**：文字 = 锁定台词，时间 = 音频（无提示识别 + 拼音对齐）。入点 = 首字 − 0.08 s，出点 = 末字 + 0.25 s，≥ 0.8 s，≤ 9 字 / s，相邻 ≥ 2 帧，全部吸附到帧。没听到的句子不丢，标 `needs_review: not_heard` 并给占位时间；末字贴着出点的标 `ends_at_cut`（把 `out_frame` 往后挪，或靠 L-cut 并抽听）。ASS 样式：中文 58 px、英文 36 px（按 1080p 等比），`--bilingual` 出双语；Windows 默认字体 Microsoft YaHei。不让模型画字幕。
- **逐段电平**按「有台词的那几秒」对齐到 −16 LUFS，不按整段平均：一段里只有一句短台词时整段平均会偏低，按它放大会把环境声和音效一起抬 8–9 dB（实测）。自带声音的片段对白和音效在同一条轨上，音效峰值会限制能加多少——脚本最多让峰值被限幅 4 dB，超出就报「对白会偏低约 N dB」，这时该段改用分离出的对白 stem 或换一个 take。某一句比同段其他句低 6 LU 以上也会单独报。
- **成片响度**：能用纯增益到 −14 LUFS 就只加增益；增益会顶破 −1.5 dBTP 时才加限幅并补偿。不用 `loudnorm` 的动态模式（会抽吸）。限幅超过 4 dB 会警告：压低音效 / 配乐，或把目标改成 −16。
- **验收**（`mix_episode.py` 自动做，不过则退出码 1）：音画等长（±2 帧）、帧数 = 计划、响度在目标 ±1 LU、真峰 ≤ −1 dBTP；报告写在 `final/ep01.mix.report.json`。
- 其余常数：边界淡变 10 ms 入 / 120 ms 出；集尾切黑 ≥ 末词 + 0.6 s；胸像 / 口播拼接前裁底部 12%（H3 在下缘凭空长手指）；脸只放不缩 ≤ 1.35×；同场接色向组内中位数拉 70%；配乐硬切点对齐 1/4 或 1/8 拍；开头 3 s 剪到最紧。竖屏 TikTok 把黑位抬到 TV 36（边缘连续近黑 ≥ 4 s 会被平台判定）。
- 交付 16:9：1920×1080、24 fps（或转 30）、bt709、AAC 48 kHz 立体声 320 k、`faststart`；不是 16:9 的片段 `--fit cover` 裁满 / `contain` 加边。

**出口怎么选**

| 要什么 | 用哪个 | 注意 |
|--------|--------|------|
| 直接发布 | `mix_episode.py` 的 mp4（`--ass` 烧字幕，或平台另传 `.srt`） | 改任何东西都回 EDL 重跑 |
| 在剪映里加花字 / 转场 / 调色 | `export_capcut_draft.py`（`pip install pyJianYingDraft`；国际版 CapCut 加 `--international`） | 片段自带的声音留在片段上（挪切点时跟着走），电平取混音报告；配乐按 −8 dB 静态垫着（草稿里不带自动压低）；成片混音作为**静音**参考轨——没动过切点时，解除它的静音并静音其余轨即得自动母带。素材按绝对路径引用，别移动 |
| 交给 Resolve / Premiere 或外部剪辑师 | `export_otio.py`（`.otio` + FCP7 XML + CMX3600，`pip install opentimelineio otio-fcp-adapter otio-cmx3600-adapter`） | 不带电平；每句台词是片段上的一个标记；字幕另导 `.srt` |

生成成功 ≠ 在目标软件里打开播放过：第一次导出后先打开看一眼时间线。

## 4. 产物目录（可复现）

```
project/
├── project.yaml           # 风格、画幅、模型组合、LoRA 版本
├── bible/                 # 角色 / 场景 / 道具图 + 识别短语 + 音色样本
├── episodes/ep01.json     # 分镜
├── prompts/               # 每段最终提示词（含替换后的标签）
├── takes/ep01/s03/        # 每个候选 mp4 + 参数 json
├── selects/ep01/          # 精修 / 超分后的中选片段，文件名带段 id
├── edit/ep01.edl.json     # 剪辑单（+ 导出的 .otio / .xml）
├── subs/ep01.srt|.ass     # 字幕
├── audio/ep01/            # 配乐、环境声、导出的 stem
├── final/ep01.mp4         # 成片 + .mix.wav + .mix.report.json
├── qc/                    # probe / dialogue / identity 报告、联络表、review.md
└── logs/takes.csv
```
任何一段都能从 `prompts/ + bible/ + project.yaml` 重新生成；成片能从 `selects/ + edit/` 重新装配。
