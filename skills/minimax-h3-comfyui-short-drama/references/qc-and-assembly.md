# QC 与拼接

> 验证口径：本页脚本都在一支 38 s 的真实 H3 成片（切成 5 段）上跑通过（Linux、ffmpeg 6.1、CPU）——7 个切点全部检出且无误报，复读台词、画面里已有的字幕、段尾混入的一帧都被查出；成片帧数与剪辑单一致（默认每段裁 2 帧起始音节时 900 帧）、音画偏移 0 ms、−14.2 LUFS、烧录字幕逐帧对上。之后又请一个只读文档的 agent 独立走了一遍，它指出的问题已修进脚本与本页。**没有在用户的 Windows + 4090 上跑过**，剪映草稿也没有在剪映里打开过——装好后先跑 `scripts/selfcheck.py`，再拿样片段走一遍。
> 命令约定：都在**项目根目录**下运行（剪辑单里存的是相对它的路径），写作 `python <skill 目录>/scripts/xxx.py …`；下面为了简短只写 `scripts/xxx.py`。通配符放在引号里，由脚本自己展开。

## 0. 只做质检和后期（片段已经有了）

不需要完整的分镜：`episodes/ep01.json` 里只要有 `characters[].id / name`、`segments[].id / duration / scene_id`、每段 `shots[].index / start`（镜头起点，用来对账切点）和 `shots[].dialogue[].speaker / text`（锁定台词）；末镜要裁定格尾就写 `"end_hold": true`。`validate_episode.py` 是给生成用的，后期不要求它通过。然后按 §1 的 1→4 过质检，把选中的片段放进 `selects/ep01/`，走 §3。

给已有片段补分镜时几件事要知道：
- **片段放哪**：照 `comfy_submit.py` 的布局放，每条一个文件夹——`takes/ep01/s01/s01_100/<文件>.mp4`（段 id 在路径里，质检脚本靠它认段）。同名文件没关系，联络表会按文件夹命名（`qc/sheets/s01_100_<文件>_sheet.png`）；`_prev_*` 文件夹里的旧片段会被跳过。
- **`end_hold` 按片子的实际情况写**：片段末尾没有那 1 s 定格就不要标（否则剪辑单会多裁 1 s）。这样写出来的分镜出的提示词只能当对照——要拿它重新生成，先把 `end_hold` 补回去。
- **一张参考图都没有**也能走完：校验器只警告；`build_prompts.py` 会把这些段按纯文字（三段式，`t2va`）出提示词，身份门禁那一步跳过。
- **画面里没出现、只听得见的人**（画外的一句催促）：台词标 `"offscreen": true`，说话人不必绑进这一段的 `character_ids`。
- **一段只有一个 `scene_id`**：片子里一段跨了两个地方，就按主要的那个填，次要地点写进对应镜头的 `framing`。
- 剪辑时把某段的出点提前了、而下一段要从这一段的末态接戏：按新的出点重新观测（`observe_take.py --freeze-tail <裁掉的秒数>`）。

## 1. QC：脚本先筛，人只看联络表

技术通过 ≠ 整体通过。下表按成本从低到高排；1–3 是脚本，便宜，直接对所有候选片段跑；第 4、5 步和精修只花在前面没被硬门拦下的片段上。

| 顺序 | 门 | 命令 | 拦什么 |
|------|----|------|--------|
| 1 | 技术 | `scripts/qc_probe.py "takes/ep01/**/*.mp4" --episode episodes/ep01.json --freeze-tail 1.0 --out qc/probe` | FAIL（退出码 1）：缺视频 / 音轨、帧率不符、时长与「请求秒数对齐到 17k+5 帧格后的长度」偏差 > 0.6 s（13 s 的段实际是 13.67 s）、**音频削波**（采样卡在满幅）、定格尾之外冻结 > 1 s 或黑场 > 0.25 s；给了 `--expect-size` 时尺寸不符也算。WARN：**镜头数与分镜不符**（少切 = 两镜糊成一镜，多切 = 自己加了镜头）、切点偏移 > 0.3 s、首尾 8 帧内的跳帧（拼接处会闪）、**画面下三分之一烧着字**、动作量 < 1.2、峰值高于 −1 dB 但没削波、画幅与分镜的 `ratio` 不符 |
| 2 | 台词 | `scripts/qc_dialogue.py --episode episodes/ep01.json --targets "takes/ep01/**/*.mp4" --out qc/dialogue` | FAIL（默认只报告，`--strict` 才退出 1）：整体相似度 < 0.72（`F-DIALOGUE-TEXT`）、句首 / 句尾 3 字没听到、识别字数 > 原文 × 1.15 + 2（复读 / 加词）、无台词段出现 ≥ 2 个词。WARN：首字晚于 2.5 s、末字离可用结尾 < 0.2 s、识别把握低（词概率均值 < 0.65）、只有一两个字的短句 |
| 3 | 身份 | 真人：`scripts/identity_gate.py --episode episodes/ep01.json --targets "takes/ep01/**/*.mp4" --out qc/identity`；漫剧：`scripts/identity_gate_anime.py`（同样的参数） | 真人脸：换人、克隆脸、多出的人、缺席；先看自检（两个角色互相 ≥ 0.363 = 撞脸，回去改角色设计）。漫剧：整张图与角色参考的差异（CCIP），只判单角色画面。没有角色参考图就跳过这一步 |
| 4 | 联络表 + 人眼 | `scripts/contact_sheet.py "takes/ep01/s03/**/*.mp4" --episode episodes/ep01.json [--out-dir qc/sheets]` | 下面的清单 |
| 5 | VLM 评分（可选） | `assets/judge-take-prompt.md` | 事实 / 身份 / 画面三张小评分表 |

- **`--freeze-tail` 的口径（三个脚本一致，也与 `make_edl.py` 一致）**：它是「声明的定格尾有多长」。给了 `--episode` 时，只有末镜写了 `"end_hold": true` 的段才把最后这一秒排除在检查之外——因为只有这些段在拼接时会裁掉它；其它段的最后一秒要进成片，照查不误。不给分镜时对每个片段都排除。输出里会注明「last 1s = declared freeze, not checked」。
- **切点对账**用分镜里各镜的 `start`，容差 ±0.5 s；切点检测不靠 ffmpeg 的 scene 阈值（同一房间的两镜 0.19–0.28，飞舞的纸张 0.30，分不开），而是看「切点前后 4 帧均值的台阶 + 比安静一侧高 4 倍 + 之后画面不回来」（`scripts/h3lib/signals.py`）。标定素材只有一支片子：WARN 先看联络表再动手，要当硬门用 `--strict-cuts`。叠化 / 淡变不算硬切。
- **画面烧字**是启发式（需要 `numpy`）：找下三分之一里带深色描边的亮色笔画、沿一行有很多独立笔画、连续半秒以上亮在同一位置。在测试片上 5 处字幕全部找到、误差 0.2 s 内；没有描边的深色字检不到，纹理很细的静止画面可能误报——它只负责提醒你去看那一帧。`mix_episode.py --ass` 也会做同样的检查并警告「会叠字」。
- **台词质检不给识别器任何提示**：把台词原文当提示喂给 whisper-small，会「听到」没说过的句子（实测出现别段的台词和乱码）。脚本用无提示转写 + 拼音比对（装 `pypinyin`，同音字误识不扣分）；GPU 空闲时 `--model large-v3 --device cuda` 更准。识别器给的词时间偏早（实测首字比人声早 0.3–1.2 s），脚本会按语音频段的能量把起止点收回到人声上，报告里的首字 / 末字时间是收回后的值。只有一两个字的台词（「啊？！」）即使相似度 1.0 也只是弱证据，会标 `short_line` 或 `low_confidence`——去听。
- **首字晚**（`late_start`，从这句台词所在镜头的计划起点算起超过 2.5 s）怎么办：开口前是有效表演就留着；是空等就在剪辑单里把该段 `in_frame` 往后挪。**末字贴着结尾**：把 `out_frame` 往后挪（没标 `end_hold` 的段）或靠 L-cut，并抽听。
- **动作量**（240 px 灰度相邻帧差的中位数）：脚本只在 < 1.2（近乎静止）时警告；动作镜 ≥ 2.5、特写表演 ≥ 1.8 是给人对照的参考值，分镜没有标镜头类型，脚本不按它判。
- **身份门禁**阈值（OpenCV SFace）：≥ 0.55 通过、0.363–0.55 警告、< 0.363 不通过；失败帧 > 20% 或第一个有脸的帧失败则整段不通过。侧脸、背影、< 40 px 的脸与动漫脸不参与；分数是警告信号，不是定论。
- **动漫轨**（`identity_gate_anime.py`）：差异值越小越像，≤ 0.178 通过（模型自带阈值，F1 0.917）、0.178–0.30 警告、> 0.30 不通过；失败帧 > 20% 或第一帧失败则整段不通过。0.30 这条线只来自 12 张图的小样本（同角色最大 0.28、异角色最小 0.34），是暂定值。比的是整张画面，所以只判本段只有一个角色的图 / 片段，远景里人很小也会落进警告带；最适合用在生图阶段——派生视图和单人首帧对着冻结的定妆照过一遍。模型许可 OpenRAIL，商用前读条款。
- **联络表**不再均匀抽 12 帧：首帧、末尾可用帧（标签 `end`：给了 `--episode` 时，标了 `end_hold` 的段取定格前的最后一个运动帧）、**最后一帧**（只在没有裁定格尾的片段上有——定格尾剪辑时会裁掉，所以 `end_hold` 段的表上是 start / mid / end 三类帧）、`qc_probe` 报跳变的那一帧、每个切点前后各一帧、每镜中段、黑场 / 冻结起点，帧下印秒数与标签。人眼看：身份（是否换人）、服装道具（颜色 / 件数 / 是否被换成虚构物）、环境（布局 / 光向 / 色温是否接上一段）、动作（瞬移 / 多肢体 / 手崩）、镜头（是否按分镜切）、**画面里有没有自带的字**、下方 15% 字幕安全区。
- **音频抽听**：语言对、没有错人开口、句尾没被截。

硬门 = 文件不可解码、缺节拍、缺镜（镜头数对账默认只警告，要人看联络表确认；加 `--strict-cuts` 才直接判 FAIL）、帧率时长违约、身份 / 服装 / 道具 / 轴线显著错、音频削波、意外黑帧、冻结；软警 = 轻微拖影、背景小漂移、音量不均、峰值偏高。硬门不过时怎么重抽，口径见 SKILL.md 铁律 10（偶发的技术故障原样重试一次；同一个问题连续两批都在就改提示词或分镜）。用户明确要先用现有片段出一版时可以带着问题装配，结论记为 PROVISIONAL 并逐条写明（模板见 `assets/review-template.md`）。

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
| F-DIALOGUE-TEXT | 台词复读 / 漏句 / 含糊 | 提示词：台词只写一次、预算；步数 ≥ 8 或 12 | 换新 seed（说话节奏跟 seed 走）；连续两批都这样就改台词分镜 |
| F-SHOTS | 镜头数与分镜不符 | 分镜 / 提示词：`[Shot N] At …` 时码、每镜 ≥ 1.2 s；一段 ≤ 4 镜 | 换 seed 很少有用：先改分镜（拆段或并镜） |
| F-BURN-TEXT | 画面烧出字幕 | 提示词：正文太短（< 350 词）或要求了字幕 | 一闪而过裁掉，否则重生成 |
| F-SEAM | 接缝闪帧 / 曝光跳 | 后期：首尾跳帧裁掉、统一转码；续接见 continuity | 后期修 |

- **先分流再动手**：区间外的毛病裁掉，能后期修的后期修；只有漏关键动作 / 台词、换脸、轴线全反、关键文字乱码才必须重生成。先判是「参考图的毛病」还是「生成的毛病」——参考图错了重抽多少次都错。
- 原因不明时一次只改一个变量；**一眼看清的多处错漏同一轮改完**。同一硬伤连续两批都在 → 改词或拆镜，不再抽（铁律 10）。
- 仍不行给用户三条出路：留用并靠切点藏住 / 把这条信息挪到相邻段 / 删段（先把剧情信息转移走）。
- 每集出一份 `qc/review.md`（模板 `assets/review-template.md`）：每条问题记 集‑时间码‑门‑现象‑失败码‑证据‑根因层‑处置‑复验状态。结论四选一——PASS：所有门都过；PROVISIONAL：可交付但带着列明的已知问题（WARN，或被豁免的 FAIL，写明理由）；REVISE：交付前必须重抽或改分镜；REJECT：从分镜 / 资产层重来。冷观众四问（想要什么 / 什么阻止 / 什么变了 / 为何结局）任一答错即 REVISE。

### 自动闭环的边界

- 只对「技术参数 / 首帧接不上 / 画面自带字幕 / 台词不过」类失败自动换 seed（画面自带字幕由 `qc_probe.py` 的启发式提醒，以联络表上看到的为准）；切点偏移、片尾抖动只标记不重出（重出改善率 29%、0 / 4）。
- 无台词段「擅自说话」的判据：`no_speech_prob < 0.5` 且 ≥ 2 词（`qc_dialogue.py` 的 `unexpected_speech`）。
- VLM 抽帧只作「崩坏 / 水印 / 乱码」与事实核对，不替代动作量与台词检查；每个 take 的评估绑定视频哈希，静帧不足以放行有运动或台词的镜头。

## 2. 抽卡策略

- 草稿档每段 2–3 个 seed（有台词的段 3 个），**看联络表挑**而不是看视频：先身份一致，再能量 / 表演。
- 中选后只对**那一条**做精修 / 二采（从它存下的 latent 开始，或同 seed 重跑），不换表演。
- `comfy_submit.py --log logs/takes.csv` 会记下每个 take 的 seed、耗时、帧数和设置摘要（分辨率 / 步数 / 模型 / LoRA），主观评分自己填 `score` 列；一周后用数据定默认值。
- 同一个问题连续两批都在 = 提示词或分镜的问题，不是运气（铁律 10）。
- 仅对续接链（可选）：本段评分前二的 take 各出一条下一段草稿，按「本段分 + 下一段分」选——只在链首和情绪高点用。

## 3. 后期：一份剪辑单（EDL）走到底

**先选片**：把每段选中的（精修后的）片段复制到 `selects/ep01/`，文件名以段 id 开头（`s03.mp4`、`s03_seed103.mp4` 都行），一段一个；或者不复制，用 `make_edl.py --pick s03=<片段路径>` 逐段指定。`make_edl.py` 会把每段选进来的片段和分镜里记的采纳片段对一遍：是采纳的那个文件本身、是它的精修（旁边 `run.json` 里的提示词与参考指纹、seed 都相同），或者是这两者复制到 `selects/` 里的副本（按内容在该段的 `takes/` 文件夹里找回出处），都不出声；seed 不同、按别的提示词抽的、或者这一段根本没采纳过，打印 `WARN <段>: …` 并在末尾汇总一行 `CHECK:`。剪辑单照样写出来（警告随条目存着，`mix_episode.py` 验收时再报一次）；在别的软件里超分 / 补帧过的文件对不上任何记录，只给一行 `note`。已有的剪辑单重跑时，保留下来的条目也会重新对一遍——采纳的片段后来换了，这里能看出来。**换片段时的顺序**：把新片段用同一个文件名覆盖进 `selects/` 之后，文件名和帧号都没变，但入出帧、台词时间、混音都是按旧片段量的——剪辑单的每个条目记着片段内容的指纹，`make_edl.py` 会指出「这一条的内容换了」并给出重建它的 `--pick`；`mix_episode.py`（含 `--dry-run`）和两个导出脚本也会提醒字幕时间、混音属于旧的那一版。重建条目 → 重跑 `retime_subtitles.py` → 重新混音，三步都做完提醒才消失。

```
 → scripts/make_edl.py episodes/ep01.json --selects selects/ep01 --out edit/ep01.edl.json
 → scripts/retime_subtitles.py edit/ep01.edl.json --out subs/ep01          # 出 .srt / .ass，并把每句起止时间写回 EDL
 → scripts/mix_episode.py edit/ep01.edl.json --out final/ep01.mp4 [--ass subs/ep01.ass] [--stems-out audio/ep01/stems]
 → scripts/export_otio.py edit/ep01.edl.json --out edit/ep01 --mix final/ep01.mix.wav        # 给 Resolve / Premiere
   scripts/export_capcut_draft.py edit/ep01.edl.json --drafts "<剪映草稿目录>" --report final/ep01.mix.report.json --mix final/ep01.mix.wav
```

完整示例见 `assets/edl.example.json`（一段用片段自带声音，一段用分离出的对白 / 非人声 stem，带环境声与配乐）。

**EDL 是唯一事实源**：字幕、混音、剪映草稿、OTIO 都从它算时间线（`scripts/h3lib/edl.py`，位置 = 帧数累加，不是秒数累加），所以四者的切点逐帧一致。手改都改这一个文件，重跑 `make_edl.py` 不会覆盖已有的段（`--overwrite` 才重建，`--pick` 只换指定的段）。

**改完之后重跑什么**：

| 改了什么 | 重跑 |
|----------|------|
| 切点（`in_frame` / `out_frame`）、换片段、调整段的顺序 | `retime_subtitles.py` → `mix_episode.py` → 导出（台词时间是相对各段入点存的，切点一动就过期；没重跑时 `mix_episode.py`（含 `--dry-run`）和两个导出脚本都会警告「字幕是按另一版切点对的时」；导出时带的 `--mix` / `--report` 若来自另一版切点也会警告，要先重新混音） |
| 某句字幕的时间或逐句增益、配乐、环境声、响度目标 | `mix_episode.py` → 导出（改了字幕时间先重跑 `retime_subtitles.py` 重写 .srt / .ass） |
| 只想换字幕样式 / 字体 | `retime_subtitles.py`（时间不变）→ 带 `--ass` 的 `mix_episode.py` |

| EDL 字段 | 含义 | 默认 |
|----------|------|------|
| `segments[].in_frame / out_frame` | 用素材的哪几帧（素材自己的帧号，出点不含） | 入点裁 2 帧（H3 开头常带一个起始音节）；末镜标了 `end_hold` 的段裁掉 1 s 定格尾（`--freeze-tail-all` 对所有段都裁） |
| `segments[].audio` | `"native"` = 用片段自带的声音；路径 = 单独的对白 stem；`null` = 静音 | 有音轨即 `native` |
| `segments[].l_cut / j_cut` | 声音比画面晚收 / 早进的秒数 | 有台词的段 L-cut 0.25 s |
| `segments[].lines[]` | 锁定的台词原文（字幕文字只从这里来）。`start / end` = **从该段入点算起的秒数**，由 `retime_subtitles.py` 填；手改某句时间后加 `"locked": true`，之后重跑不再覆盖它；`"gain_db": 6` 单独抬高（或压低）这一句 | 取自分镜 `dialogue[]` |
| `segments[].lines[].en` | 可选的英文字幕文字，来自分镜台词的 `en` 字段；只有 `--bilingual` 时才用，不进提示词 | 空 |
| `ambience{场景: {file, gain_db}}` | 每个场景一条循环环境声底，带限 150–6500 Hz | 空；`gain_db` 默认 −34 |
| `music{file, gain_db, fade_in, fade_out, loop, duck{depth_db, …}}` | 全集配乐；按每句台词的起止时间自动压低（增益包络，不受片段里音效影响） | 空；默认压 9 dB。EDL 里没有台词时间时退回 sidechain（真实对白上只有约 3–6 dB） |
| `loudness{dialogue_lufs, program_lufs, true_peak}` | 响度目标 | −16 / −14 LUFS / −1.5 dBTP |

- **字幕**：文字 = 锁定台词，时间 = 音频（无提示识别 + 拼音对齐）。规则：入点 = 首字 − 0.08 s，出点 = 末字 + 0.25 s，≥ 0.8 s，≤ 9 字 / s，相邻 ≥ 2 帧，全部吸附到帧。「首字」不直接用识别器给的时间——它常把第一个字放进人声之前的静音里（实测早 0.3–1.2 s），脚本按语音频段能量把起止点收回到人声上；这仍是估计，成片后看一遍。需要复核的句子会标出来：`not_heard`（没听到，给占位时间）、`low_coverage`、`low_confidence`、`timing_suspect`（时长对这几个字来说太长）、`ends_at_cut`（末字贴着出点）、`moved`（入点没动，这句的起点却比上一次对时挪了 0.3 s 以上——识别器自己拿不准，去听）。字幕不会越过本段的出点（设了 `l_cut` 的段可以延到尾音结束）。看着不对就在 EDL 里改这句的 `start / end` 并加 `"locked": true`。`not_heard` 的句子写回的是占位时间，混音不拿它当人声区间（电平按整段对、配乐按侧链压），这时 `mix_episode.py` 的提示会说「对时跑过但没听到」而不是让你再跑一遍对时：去听——确实说了就手填 `start / end` 加 `"locked": true`（之后混音就按这个区间算），没说就重抽这一段。ASS 样式：中文 58 px、英文 36 px（按 1080p 等比），`--bilingual` 出双语；字体默认按系统取（Windows Microsoft YaHei、macOS PingFang SC、Linux Noto Sans CJK SC），`--font` 可改。烧录是逐帧准的（实测与字幕帧号偏差 0）。**片段画面里已经有字的不要再烧一遍。** 不让模型画字幕。
- **逐段电平**按「有台词的那几秒」对齐到 −16 LUFS，不按整段平均：一段里只有一句短台词时整段平均会偏低，按它放大会把环境声和音效一起抬 8–9 dB（实测）。自带声音的片段对白和音效在同一条轨上，音效峰值会限制能加多少——脚本最多让峰值被限幅 4 dB，超出就报「对白会偏低约 N dB」，这时该段改用分离出的对白 stem 或换一个 take。某一句比同段其他句低 6 LU 以上会单独报，并给出建议的 `gain_db`。
- **成片响度**：能用纯增益到 −14 LUFS 就只加增益；增益会顶破 −1.5 dBTP 时才加限幅并补偿。不用 `loudnorm` 的动态模式（会抽吸）。限幅超过 4 dB 会警告：压低音效 / 配乐，或把目标改成 −16。
- **验收**（`mix_episode.py` 自动做，不过则退出码 1）：音画等长（±2 帧）、帧数 = 计划、响度在目标 ±1 LU、真峰 ≤ −1 dBTP；报告写在 `final/ep01.mix.report.json`。`--stems-out` 只写有声音的总线：片段都用自带声音时是 `<集>.takes.wav`（对白和片段自带的音效在一条轨上），用了分离的对白 stem 时是 `<集>.dialogue.wav`，另有 `effects` / `music`。
- 其余常数：边界淡变 10 ms 入 / 120 ms 出；集尾切黑 ≥ 末词 + 0.6 s；胸像 / 口播拼接前裁底部 12%（H3 在下缘凭空长手指）；脸只放不缩 ≤ 1.35×；同场接色向组内中位数拉 70%；配乐硬切点对齐 1/4 或 1/8 拍；开头 3 s 剪到最紧。竖屏 TikTok 把黑位抬到 TV 36（边缘连续近黑 ≥ 4 s 会被平台判定）。
- 交付 16:9：1920×1080、24 fps（或转 30）、bt709、AAC 48 kHz 立体声 320 k、`faststart`；不是 16:9 的片段 `--fit cover` 裁满 / `contain` 加边。

**出口怎么选**

| 要什么 | 用哪个 | 注意 |
|--------|--------|------|
| 直接发布 | `mix_episode.py` 的 mp4（`--ass` 烧字幕，或平台另传 `.srt`） | 改任何东西都回 EDL 重跑 |
| 在剪映里加花字 / 转场 / 调色 | `export_capcut_draft.py`（`pip install pyJianYingDraft`；国际版 CapCut 加 `--international`，并改装 `pip install pycapcut`）。`--drafts` 是剪映「全局设置 → 草稿位置」那个文件夹，要在装着剪映、放着素材的那台机器上跑 | 片段自带的声音留在片段上（挪切点时跟着走），电平取混音报告；配乐按 −8 dB 静态垫着（草稿里不带自动压低）；成片混音作为**静音**参考轨——没动过切点时，解除它的静音并静音其余轨即得自动母带。素材按绝对路径引用，别移动 |
| 交给 Resolve / Premiere 或外部剪辑师 | `export_otio.py`（`.otio` + FCP7 XML + CMX3600，`pip install opentimelineio otio-fcp-adapter otio-cmx3600-adapter`） | 不带电平；每句台词是片段上的一个标记；字幕另导 `.srt` |

不确定用哪个剪辑软件时先出 `export_otio.py`（FCP7 XML 在免费的 DaVinci Resolve 里就能打开）。生成成功 ≠ 在目标软件里打开播放过：第一次导出后先打开看一眼时间线。

## 4. 产物目录（可复现）

```
project/
├── project.yaml           # 给人和 agent 看的项目记录（没有脚本读它），见下
├── workflows/             # 只有自己改过 / 自己导出的工作流才放这里；默认直接用 skill 附带的 assets/workflows/
├── bible/                 # 角色 / 场景 / 道具图 + 音色样本（+ 多集共用的资产表）
├── episodes/ep01.json     # 分镜：资产表（characters / scenes / props）+ stagings + segments
├── prompts/ep01/          # 每段提示词 + .media.json + planned_cues.srt（计划的台词时间，只供预览，不是字幕）
├── takes/ep01/s03/        # comfy_submit.py 的输出：每个候选一个文件夹（mp4 + run.json）
├── selects/ep01/          # 精修 / 超分后的中选片段，文件名带段 id
├── edit/ep01.edl.json     # 剪辑单（+ 导出的 .otio / .xml）
├── subs/ep01.srt|.ass     # 字幕
├── audio/ep01/            # 配乐、环境声、导出的 stem
├── final/ep01.mp4         # 成片 + .mix.wav + .mix.report.json
├── qc/                    # probe / dialogue / identity 报告、观测表、联络表、review.md
└── logs/takes.csv         # 每个 take 一行：耗时、seed、帧数、设置摘要（分辨率 / 步数 / 模型 / LoRA）、评分
```

- **资产表放哪**：就是分镜 JSON 里的 `characters` / `scenes` / `props`，这是唯一被脚本读取的一份。多集共用时另存一份 `bible/series_bible.json` 当母本，新一集从它复制——目前没有脚本做合并，改了母本要自己同步到各集。
- **「采纳的片段」是哪个文件**：选片在草稿阶段做，采纳的就是 `takes/…/` 里那条草稿 mp4；`observe_take.py` 观测的也是它（记下路径和 sha256，连同它旁边 `run.json` 里的 seed、提示词与参考的指纹、它是从上一段的哪个状态开场的）。采纳之前脚本会拿这份记录对一遍，三种情况不收：① 这条片段是给别的段做的；② 帧数和这一段对不上（这两种加 `--force` 才收）；③ 它是按**旧的**提示词或参考抽的——上一段后来观测到的结尾和计划不一样、挂了音色样本、换了某张图，都会让提示词变。③ 的正路是按现在的提示词重抽；如果你把这条和上一段采纳的片段放在一起看过、确实接得上，加 `--stale-ok` 采纳它。这样采纳的片段，精修要用**它当时的**提示词和参考：`comfy_submit.py` 在每条片段的文件夹里留了 `prompt.txt` 和 `media.json`（参考清单，提示词指向旁边的 `prompt.txt`），精修时把 `--media` 换成 `<那条片段的文件夹>/media.json`，再加 `--from-latent <同一个文件夹>`（没存 latent 就 `--seed <它的 seed>`）；用现在的 `prompts/…/<段>.media.json` 的话，`--from-latent` 的预览会警告「二采会被另一份文字牵着走」，`--seed` 重跑出来的则是按新提示词的另一条。脚本不收的时候也会说变的是什么：提示词、哪张图内容变了、后来挂上的音色样本。④ 比草稿画布小的片段（快速预览用的 864×480 之类）也不收：预览不是二采要接的那一条，确实就按这个尺寸做才加 `--small-ok`。反过来，前一段后来换了采纳的片段或改了结尾，后面已经采纳的段不会被自动推翻——`observe_take.py` 当场提示 `CHECK THE CUT`，`validate_episode.py` 此后每次都提醒，直到你确认这一刀（对后一段再跑一次 `observe_take.py … --stale-ok`）或者重做后一段。之后的 latent 二采（LBH 放大 + σ 0.45）不改构图，末态不变；换步数、关 Turbo 或换分辨率重跑出来的是一条新片段，要对它重新选片、重新观测。精修 / 超分后的文件放进 `selects/`，剪辑单用的是 `selects/` 里的。
- **`project.yaml`** 记下这个项目固定不变的东西，换机器或隔了几周回来能照着重建。没有固定格式，建议至少这些：

```yaml
title: 最后一班渡船
ratio: "16:9"
canvas: 1344x768            # 生成画布；交付时裁 6 px 上下再缩放到 1920x1080
style: "Live-action, cinematic, ..."      # 与分镜 JSON 的 style 一致
comfyui: 0.37.2
models:
  unet: minimax_h3_ref2va_pruned_int8_convrot.safetensors
  text_encoder: qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors
# 工作流写 skill 附带的文件名（assets/workflows/）；自己改过的另存到项目的 workflows/ 下再写那个路径
draft:   {workflow: h3_ref2va_sage.api.json, steps: 8, lora: minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors, shift: "12 / 3"}
refine:  {workflow: h3_ref2va_sage_refine.api.json, note: "中选片段的 latent 二采：从草稿存下的 latent 开始（--from-latent；没存就同 seed 重跑一采）+ LBH 放大 + σ 0.45，音频钉死"}
camera:  {workflow: h3_ref2va_sage.api.json, set: "146.value=false 123.sampler_name=res_multistep", steps: 20, lora: none, note: "有运镜的镜头重出（铁律 16）；算新片段，要重新选片和观测"}
```

任何一段都能从 `prompts/ + bible/ + project.yaml` 重新生成；成片能从 `selects/ + edit/` 重新装配。
