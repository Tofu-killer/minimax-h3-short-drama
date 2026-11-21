# 14‑03 · 商业 / 云端 AI 视频模型与创作者实战工作流

> 调研日期 2026‑11‑21。方法：先用 Artificial Analysis 视频榜核对「2026‑11 实际在用的版本」，再逐家读官方提示词指南 / API 文档 / 价目页（WebFetch），最后读创作者教程、行业报道与 GitHub 上的提示词库 / skill（搜索 API + raw README + 只取文本的稀疏克隆 12 个仓库，共 ≈12 MB）。Reddit 被搜索工具拒绝访问，X 只读到被 GitHub 仓库收录的帖子摘要，B 站只读到标题与简介。
> 来源缩写：〔AA〕= Artificial Analysis AA‑Video‑T2V / I2V v2.1 榜（2026‑11‑21 抓取，价格列是「官方 API 生成 1 分钟的美元价」）；〔RW〕= Runway 开发者价目页 `docs.dev.runwayml.com/guides/pricing`（$0.01 / credit，含它代理的第三方模型）；〔CF〕= ComfyUI Partner Nodes 价目页 `docs.comfy.org/tutorials/partner-nodes/pricing`；〔SD‑G〕= 字节官方 Seedance 2.5 提示词指南（飞书 `bytedance.larkoffice.com/docx/A88jd0B47oAd8zxWp5ycZFMfnxh`，经 Higgsfield 帮助中心镜像读取）；〔SD‑U〕=【Dreamina】Seedance 2.5 User Guide rev 419 的快照（`liyue-aigc/seedance-2-5-video-director`，2026‑08‑16）；〔SD‑36〕= 官方 36 个发布案例（`Evolink-AI/awesome-seedance-2.5-guides`）；〔KL‑G〕= `kling.ai/quickstart/kling-4-model-user-guide`；〔WAN‑G〕= 阿里云百炼《万相3.0视频生成Prompt指南》与生成指南；〔OMNI〕= Gemini API omni 文档 + DeepMind prompt guide；〔VEO‑G〕= Google Cloud《The ultimate prompting guide for Veo 3.1》；〔LP〕= `LearnPrompt/awesome-seedance`；〔OS〕= `A-cat-with-carrots/OnlyShot`；〔WS〕= WaveSpeed 博客（2026‑10‑24 / 25）；〔AIReel〕= AIReel 三模型横评（2026‑10‑20 更新）；〔毒眸〕= 新浪转载《实测可灵4.0》（2026‑10‑27）；〔Atlas〕= Atlas Cloud 10 组实测（2026‑08‑21）。
> 口径提醒：价格全部是 **2026‑11‑21 当天能查到的标价**，各家促销频繁（Kling 4.0 八折到 11‑30、HeyGen Video 1 半价到 12‑01、即梦双十一年包 4.5 折）；厂商自报与平台营销文的数字都标了出处，没有独立验证的写「未验证」。

## 本簇结论

1. **闭源第一梯队已经换代，而且全部变成「30 秒 + 全能参考 + 可编辑」**：Seedance 2.5（4–30 s，另有 30–180 s Long Video；30 图 + 10 视频 + 10 音频）、Kling 4.0（3–30 s；15 件参考或 10 张关键帧）、Wan 3.0（闭源 API，2–30 s，30 fps，能吃 PPT / PDF / 网页）、Gemini Omni Flash 1.2（3–15 s，对话式编辑）。Sora 2 的 App 与 API 已在 2026‑09‑24 停服；Veo 3.1 仍限 8 s，〔AA〕已掉到第 26–28 位。
2. **我们本地跑的 H3 本身就在榜单前列**（〔AA〕T2V 第 3、I2V 第 5），fal H3 Max、Pika H3 Flex、Creatify Boreal‑H3 以及（据第三方）HeyGen Video 1 都是它的后训练衍生。所以云端不是「换更好的模型」，而是只买 H3 的结构性短板：> 15 s 的单镜、打戏与大幅运镜、给定音频的精确口型、指定机位轨迹、成片局部编辑。
3. **主流做法高度一致**：资产先行（角色 / 场景 / 道具图）→ 用静帧当控制层（分镜图首帧、宫格故事板、白模 / 深度图）→ 参考生视频 → **局部编辑替代整段重抽** → 剪映 / DaVinci。〔OS〕的实测单价是改一张分镜图 3 积分、改一段视频 55 积分，所以成熟流水线都把决策前移到静帧。
4. **谁做得最好**：提示词规范看字节官方〔SD‑G〕（素材职责行 + 排除项、阶段三要素、音频四种括号）；实证看〔LP〕（1070 条逐条回溯原帖、494 次跨模型复跑，Seedance 提示词搬到 H3 Max 768p 的复现率 73%）；工程化看〔OS〕（即梦官方 CLI、17 种失败模式、上线合规）与即梦短剧工作室（DreamScript → Anycook → DreamShot → 3D 导演台 → Seedance 2.5 → 截帧注释）；多模型分工看〔WS〕（Wan 3.0 拍空镜与草稿、Seedance 2.5 拍对白、Kling 4.0 拍长动作）。
5. **对我们最有用的 5 件事**：
   - 一张「镜头类型 → 本地 H3 / 云端模型」路由表和每类镜头的每秒价（§五.4）；
   - 一层与模型无关的分镜数据（时间段、每段一个主动作、起止状态、参考职责），再按模型编译成各自语法（§五.3 的对照表）；
   - 三条接入路径：ComfyUI Partner Nodes（Kling 4.0 / Seedance 2.5 / Wan 3.0 / H3 Max 全家都有节点）、官方 agent 工具（即梦 `dreamina` CLI、可灵 MCP）、直连异步 API；
   - 抽卡与成本的行业基准：每个可用镜头按 3 次生成、约 25% 成片率做预算，漫剧承制价已压到 400–1000 元 / 分钟；
   - 合规硬约束：即梦 / 火山不收真人脸参考，国内上线每集全程 AI 标识 + 元数据 `AIGC` 字段。

## 一、2026‑11 版本核对与全景

### 1.1 主力模型规格（官方文档为准，价格为官方或一级代理标价）

| 模型（厂商 · 上线） | 单次时长 | 分辨率 · 帧率 | 原生音频 / 对白 | 参考上限 | 帧控制 | 编辑 / 延长 | API 标价（每秒） | 〔AA〕Elo T2V / I2V |
|---|---|---|---|---|---|---|---|---|
| **Seedance 2.5**（字节；即梦 + 豆包专业版 2026‑07‑31，火山方舟 / BytePlus API 8 月） | 4–30 s（97–721 帧）；Long Video 30–180 s | 480p / 720p / 1080p / 4K · 24 fps | 有；多语种对白、音频驱动口型、口型翻译 | 30 图 + 10 视频（合计 ≤ 30 s）+ 10 音频（合计 ≤ 30 s），共 50 | 首帧 / 首尾帧 / 多关键帧 / 宫格 ≤ 15 格 / 白模（Clay Renderer） | 时间戳局部编辑、换主体 / 背景 / 音频；向前向后延长（源 < 30 s） | BytePlus $10.70 / M token ≈ **$0.10（480p）/ $0.23（720p）/ $0.57（1080p）/ $0.92（4K）**；有视频输入时 $6.40 / M | 1157 / **1161（第 1）** |
| Seedance 2.0（2026‑02 国内，3 月经 CapCut 恢复全球） | 4–15 s | 480p–4K（即梦 CLI 为 720p） | 有 | 9 图 + 3 视频 + 3 音频，共 12 | 首尾帧 / 智能多帧（2–20 帧） | 延长、编辑 | 1080p ≈ $0.37；另有 Fast / Mini 档 | 1134 / 1142 |
| **Kling 4.0**（快手；Flash 抢先 09‑28，正式 10‑15） | 3–30 s（Flash 3–20 s） | 720p / 1080p / 4K；10‑bit HDR 标注 coming soon | 双声道立体声；9 语种 + 川 / 粤方言 + 京 / 东北 / 台湾口音 | 10 图 + 5 视频（合计 ≤ 30 s）+ 3 音色 + 7 主体（Element），合计 ≤ 15 | 首 / 尾 / 中间关键帧 ≤ 10（**与 Omni 参考不能同任务**） | `Edit @Video1`（≤ 5 段、合计 ≤ 30 s）；2 分钟延长 coming soon | **720p $0.157 / 1080p $0.235 / Flash 720p $0.094**〔RW / CF / WS〕 | 未上榜（3.0 Omni 1016 / 1004） |
| **Wan 3.0**（阿里；公测 08‑06，GA 08‑24；**不开源**） | 2–30 s 或 `-1` 智能时长 | 480P / 720P / 1080P · **30 fps** | 有；`audio=false` 可关；多语种、口型同步 | 10 图 + 5 视频（≤ 15 s）+ 5 音频（≤ 15 s），共 20；另可 1 个文档或 1 个公开网页 | 首帧 / 首尾帧（**与参考互斥**）；宫格 / 关键帧 / 白模参考 | 指令编辑、音频编辑、前 / 后 / 双向延长（入 + 出 ≤ 30 s） | **$0.05 / 0.10 / 0.20**；Prime $0.068 / 0.14 / 0.28 | **1176（第 1）** / 1108 |
| MiniMax H3 托管（2026‑07‑31） | 4–15 s | 768P / 2K · 24 fps | 立体声；11 语种 | 9 图 + 3 视频 + 3 音频，≤ 12 | 首尾帧 | Ref2VA 续写；Regenerate‑2K | $0.08 / 0.13 | 1161 / 1134 |
| H3 Max（fal 后训练，08‑26） | 5–15 s | 480P / 768P（Extend、Lip Sync 到 2K） | 同 H3 | 同 H3 | Camera Controls 2–12 个机位关键帧 | Recast / Insert / Extend / Reframe / Lip Sync | $0.05 / 0.08 | 1145 / 1118 |
| **Gemini Omni Flash 1.2**（Google；11‑05 GA） | 3–15 s；API 延长每轮 3–10 s、总 30 s | 360p / 720p 原生，1080p / 4K 为上采样；16:9、9:16 | 有；**英语完整支持，其它语言「variable」** | 6 图（每角色 ≤ 3 张、≤ 2 个角色）；参考视频 ≤ 3 段 × 3 s；**不收音频** | 首帧（到 15 s）；首尾帧仅 3–10 s | 多轮对话式编辑（`previous_interaction_id`）；只能向后延长 | $12 / M 视频 token ≈ $0.023（360p）/ **$0.07（720p）** / $0.104（1080p）/ $0.209（4K） | 1154 / 1086 |
| Veo 3.1（2025‑10；Lite 2026‑04） | 4 / 6 / 8 s | 720p / 1080p / 4K | 有 | Ingredients（Flow 里 3 张） | 首尾帧 | Flow 的 Insert / Extend | $0.40（4K $0.60）；Fast $0.10–0.30；Lite $0.05–0.08 | 962 / 955 |
| Vidu Q4 Preview（生数；2026‑10） | 3–16 s | 540p–4K | 有；3 段音色参考（各 3–12 s） | 15 图 + 3 音频 | 首帧 | — | 1080p ≈ $0.084；首发促销 0.09 元 / s 起 | — / 1032 |
| Runway Gen‑4.5 · Aleph 2.0 · Act‑Two | 2–10 s | 720p · 24 / 25 fps | Gen‑4.5 未见音频说明 | 图像参考 | 首帧 | Aleph 2.0 视频编辑；Act‑Two 表演迁移 | $0.12 · $0.28 · $0.05〔RW〕 | 未进前 30 |
| Luma Ray3.2（2026‑06‑09） | ≤ 20 s | ≤ 1080p；HDR 16‑bit EXR | 未见 | 参考图 | ≤ 16 关键帧 | Modify / Reframe | 按次计（〔CF〕徽标） | 未进前 30 |
| Sora 2 | — | — | — | — | — | — | **App + API 已停服**（2026‑03‑24 宣布，API 2026‑09‑24 下线，ComfyUI 节点已移除） | — |

出处：Seedance 2.5 规格〔SD‑U〕〔SD‑G〕与官方发布文（`seed.bytedance.com/zh/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5`，2026‑07‑31）；Seedance 的每秒价由〔CF〕给出的 token 公式 `floor((宽×高÷1024)×(24×时长+1))` 乘 BytePlus 单价算得，1080p 结果与〔AA〕的 $34.12 / 分钟一致。Kling 4.0〔KL‑G〕+ kling.ai 发布博客（2026‑09‑30）+ Bernama 新闻稿（2026‑10‑19）。Wan 3.0〔WAN‑G〕+ 阿里云国际站博客（2026‑08‑27）。Omni〔OMNI〕+ `aistudio.google.com/docs/pricing`。Veo〔VEO‑G〕+ invideo 价目汇总（2026‑08）。Vidu〔CF〕+ Comfy 教程页。Sora：Axios / Neowin（2026‑03‑24）、`cclank/lanshu-awesome-ai-video-kit` README、〔CF〕。

### 1.2 榜单上值得知道的其它名字

〔AA〕T2V 前 15 依次是 Wan 3.0、Utopai X（无 API）、MiniMax H3 768p、Seedance 2.5、Hyperflow H3（Video Rebirth）、Gemini Omni Flash 1.2、FLUX 3 Max、HeyGen Video 1、H3 Max、FLUX 3、Seedance 2.0、SkyReels V4、P‑Video‑2‑Pro（Pruna）、Pika H3 Flex、Omni Flash 1.1；Kling 3.0 Omni 排 22、Veo 3.1 排 26。I2V 前 6 是 Seedance 2.5、Utopai X、Boreal‑H3（Creatify）、Seedance 2.0、MiniMax H3 768p、HeyGen Video 1。无声榜（T2V‑Silent）第一是 HeyGen Video 1（1146）。

**H3 衍生家族**是 2026 下半年的新现象：fal H3 Max（「post‑trained version of MiniMax H3 developed by fal Research」，768p 5 s 约 2.5 s 出片，自称吞吐为官方端点的 35 倍）、Pika H3 Flex（2026‑10‑29，两个 LoRA、6 步，权重在 HF 开放）、Creatify Boreal‑H3（2026‑09‑30，广告向后训练，768p 首发 $0.04 / s）、Video Rebirth HyperFlow；HeyGen Video 1（2026‑09‑30；5–15 s；480p–2K；9 图 + 3 视频 + 3 音频 = 12，与 H3 规格一致）被 Pixazo 称为 H3 后训练，**HeyGen 官方页没有说明底模，未验证**。

### 1.3 同一个模型在不同入口的价格差

| 入口 | Seedance 2.5 @720p | 说明 |
|---|---|---|
| BytePlus ModelArk（官方国际 API） | ≈ $0.23 / s | $10.70 / M token，无视频输入 |
| 火山方舟（官方国内 API，第三方转述） | ≈ 1.5 元 / s | 70 元 / M token（含视频输入 42 元 / M）；5 s 720p ≈ 10.8 万 token ≈ 7.56 元 |
| Runway API | $0.30 / s | 30 credits / s，最低 80 credits / 次；参考图与音频不另收 |
| WaveSpeed | $0.36 / s | 480p $0.18、1080p $0.90、4K $1.80 |
| Dreamina 订阅（海外消费端） | 37 积分 / s | US Basic 续费 $15 / 月含 1575 积分 → ≈ $0.35 / s；首月 $0.29 促销 |
| 即梦短剧工作室（国内消费端） | **≈ 0.19 元 / s** | 爱范儿 2026‑10‑29：720P 带参考视频，叠加超级会员年包、赠分和消耗折扣后的最低价；CLI ≈ 0.18 元 / s |

国内创作者普遍用即梦会员而不是 API，原因就在最后一行：消费端叠满折扣后只有 API 标价的八分之一左右。同样的差距也出现在 Wan 3.0 上：官方 1080P 约 1.2–1.4 元 / s，RunningHub / 天工工作台的 480p 约 0.05 元 / s（什么值得买，2026‑09‑01）。

## 二、工作流图谱

七条有代表性的链路，A–D 是我们能直接借鉴的，E–G 用来对照。每条后面标了主要出处，细节在 §四 的案例里。

**链路 A：资产先行 + 分镜图当首帧（国内漫剧 / 短剧的事实标准）**〔OS〕+ 人人都是产品经理（2026‑09‑10）

```
一句话题材 ─► LLM 写剧本与节奏地图（秒级；3 分钟 ≈ 36 段 × 4–10 s）
          ─► 设定圣经 + ref 图库（角色 5–8 张 / 场景 3–5 张 / 道具若干；即梦图片 5.0，2K）
          ─► 分镜.json（每段：时长、video_mode、首帧 / 尾帧路径、300–1500 字符提示词）
          ─► 分镜图：每段 1–4 张候选静帧（3 积分 / 张）→ 人工选图（脸对 / 场景对 / 构图对）
          ─► 视频：image2video 80% │ frames2video 10%（爆点锁首尾）│ multiframe2video 5%（一镜到底）
                    │ multimodal2video 5%（9 图 + 3 视频 + 3 音频兜底）   55 积分 / 段
          ─► ffmpeg 自动初剪（字幕 + 全程「AI生成」角标 + 元数据 AIGC）─► 剪映精修 ─► 上线前合规清单
```

**链路 B：宫格故事板直出（一次生成 15–30 s 多镜头）**〔LP〕`storyboard-grid-to-video` + `10291124jcjc-dotcom/ai-anime-series`

```
角色设定图（三视图 + 表情 + 动作 + 剪影，每角色 1 张）
  ─► 图像模型出「单页编号分镜板」：15 s = 6 格、30 s = 9 格（每格 1.5–3.3 s），黑白素描即可，格内不写时间码
  ─► Seedance 2.5 全能参考：Image1 = 角色（只管身份）、Image2 = 分镜板（管顺序 / 构图 / 动作）
     + 规则清单「按 1→N 顺序，每格一个镜头，约 X 秒，不跳步不加步」+ 按秒写的镜头与音效
  ─► 先 480p 出片 ─► 抽帧检查 ─► 只补拍坏的那几格（patch）─► 两段各 9 格拼成 1 分钟
```

**链路 C：多模型分工的一集短剧（60–90 s，8–14 个镜头）**〔WS〕2026‑10‑25

```
剧本（一场一地、每句台词归到具名角色、结尾留反转）
  ─► 每角色 1 张正面均匀光白底图 + 每场景 1 张图 + 一段每条提示词都复用的身份文字
  ─► 镜头表（编号 / 时长 4–10 s / 景别 / 一个动作 / 台词 / 声音）
  ─► 按镜头类型选模型：空镜、插入镜头、草稿 → Wan 3.0（$0.10 / s @720p）
                        对白（带两张角色图、开音频）→ Seedance 2.5（$0.36 / s @720p，WaveSpeed 价）
                        追逐 / 打斗长镜头 → Kling 4.0（$0.157 / s @720p）
  ─► 全部先 480p / 720p 草稿 → 粗剪 → 只把活下来的镜头用同一提示词重渲 720p / 1080p
  ─► 段间：上一镜末帧 = 下一镜首帧；台词不准就重做特写 ─► 安全区检查 ─► 导出
```

**链路 D：3D 白模 / 深度图做运镜与走位迁移**（`Evolink-AI/Awesome-Blender-Seedance-Workflow-Usecases` 的 39 个 X 案例 + Curious Refuge 2026‑07‑17）

```
Blender 灰盒（手工 / Blender MCP 让 Claude、Codex 搭）或手机实拍 / 玩具摆拍
  ─► 导出 5–15 s viewport 预演视频（代理块 + 相机关键帧）──可选──► Depth Anything 转成灰度深度图
  ─► 起始帧：抽预演第一帧转写实图，或图像模型单独出
  ─► Seedance：@Video1 只继承相机路径与节奏、@Image1 = 首帧 / 角色；文字只写主体、场景、风格
  ─► 可选 Topaz 超分
```

**链路 E：MV / 口型（给定音频）**（`10291124jcjc-dotcom/ancient-rap-battle`）

```
歌词 ─► Suno 出歌 ─► demucs 分离人声 + faster‑whisper 逐句时间戳
     ─► Midjourney 定妆 9 张（三视图 / 表情 / 半身 / 场景）
     ─► 每段一个素材包：干净人声 + 参考图 + 「几秒到几秒唱哪半句」（一句一个镜头）
     ─► 即梦 Seedance 2.5 网页生成（音频参考驱动口型）─► 逐镜头互相关对齐 ─► 拼接、调色、字幕
```

**链路 F：一体化短剧工作室**（即梦短剧工作室，爱范儿 2026‑10‑29）

```
DreamScript（选题标签 → 三套方案 → 设定 / 分集大纲 / 剧本）
  ─► Anycook 出角色与场景并沉淀为项目资产 ─► DreamShot 拆分镜（画布 + 故事板）
  ─► 3D 导演台摆站位 / 机位 / 轨迹 + 智能预演（不耗视频算力）
  ─► Seedance 2.5 生成 ─► 片段重拍 / 分离音频重配 / 智能切分 / 截帧注释（圈画 + 一句话改）/ 重制转绘
```

**链路 G：Google 路线（英语内容、对话式修改）**〔VEO‑G〕〔OMNI〕

```
Nano Banana 出角色 / 场景 ingredients 与首尾帧
  ─► Veo 3.1：Ingredients 逐镜出对白（"…says in a weary voice, "…""）│ 首尾帧做 180° 弧线运镜
               │ 时间戳提示词 [00:00‑00:02]…[00:06‑00:08] 一次出 4 个镜头
  ─► Flow / Omni Flash 1.2：360p 草稿 → 对话式改背景 / 机位 / 道具 → 延长 → 上采样到 1080p / 4K
```

## 三、逐模型 / 逐工具

每节的字段按商业模型改写为：定位 / 机制与规格 / 官方提示词规范 / 价格与接入 / 审核 / 弱项 / 对 4090 短剧的价值 / 评级。

### 3.1 Seedance 2.5 / 2.0（字节；即梦、豆包专业版、Dreamina、火山方舟、BytePlus）

- **定位**：2026‑11 参考能力最强、I2V 榜第一的闭源模型，国内漫剧 / 短剧的默认出片引擎（`UnderleveledBuilder/awesome-short-drama-skills` 收录的 117 个短剧 skill 里 47 个适配它）。
- **规格**：见 §1.1。入口分「首尾帧」与「全能参考」；2.5 另有 Long Video（30–180 s）、Smart Edit / 标记区域编辑、两段视频间无缝转场、Clay Renderer（粗 / 精白模，粗白模更稳）〔SD‑U〕。
- **官方提示词规范**〔SD‑G〕：
  - 基本公式 = 主体 + 动作 / 事件，再按需加场景、风格、运镜或切镜、音频；时长与画幅填界面或 API，不写进提示词。
  - 素材写作 `@Image 1 / @Video 1 / @Audio 1`（API 清单里是 `<<<image_1_1>>>`）。**每个素材一行职责 + 一行排除**（不要用它的背景 / 人物 / 构图）；映射必须写在提示词里，不靠图内文字标签；多视角图要声明「这几张是同一个物体，成片只出现一个」。
  - 参考视频已经定义了动作和运镜时，只写「继承哪些属性」，复述动作会和参考打架。
  - 音频与文字用四种括号：音乐 `()`、音效 `<>`、台词 `{}`、字幕 `【】`；非中文台词按「语言 → 口音 → 演绎方式 → 说话人 → `{台词}`」的顺序写。
  - 长视频拆阶段，每阶段 = 初始状态 + **一个**主事件 + 可见的结束状态；末尾加一致性段（身份、人数、服装、道具归属、空间方向、声音关系）。
  - 时间戳是「时间预算」，不是帧级精度；精确时间点只留给一个关键事件。
  - 情绪 = 情绪词 + 2–4 个可观察线索（眼、眉、嘴、呼吸、视线、手）。
  - 延长先写边界状态（姿态、道具、背景、机位、光、运动方向）再写新动作；编辑按「目标 → 源视频是唯一母版 → 目标素材职责 → 范围 → 保留项」写。
  - 宫格分镜 ≤ 15 格、少文字、声明阅读顺序；白模要把每个几何体映射到最终主体，导出前去掉路径线、坐标轴、控制器、相机视锥。
- **稳定性建议**〔SD‑U〕：音视频驱动的主体 1–5 个最稳，静图主体 1–8 个最稳；**超过 5 个主体时「一视角一张图」优于「一张图多视角」**；编辑源视频 ≤ 20 s。
- **官方案例的写法**〔SD‑36〕：一段总述（风格、主线、「全片仅使用两种运镜」）→ `0-5秒，…` 首尾相接的时间段，段内直接引用素材 → 引号台词加 `口播：/ 旁白：` → 一句整体质感。FPV 案例直接写速度（3–5 m/s 加速到 14–16 m/s）与 pitch / yaw / roll 角度。
- **价格与接入**：见 §1.3。即梦有官方面向 agent 的 `dreamina` CLI（`jimeng.jianying.com/cli`；`text2image / image2video / frames2video / multiframe2video / multimodal2video`），但 2026‑11 的 CLI 仍只到 Seedance 2.0（4–15 s、720p）〔OS〕；API 走火山方舟 / BytePlus 异步任务，支持 `return_last_frame`〔LP〕。
- **审核**：即梦 2026‑02‑09 起停用真人图片 / 视频作主体参考；ModelArk 文档只接受三类人脸来源——预置虚拟人像、同账号 30 天内由 Seedream / Seedance 生成的原图、经本人实名认证授权的肖像（apidog 转述，未读到原文）；Adobe 社区有「AI 生成的脸被判成真人而拦截」的报告；海外版带人脸过滤、C2PA 水印、版权角色检测（TNW 2026‑03‑31）。即梦文本审核的实测敏感词见 §五.2。
- **弱项**：官方发布文自己承认「复杂运动的物理合理性、多主体交互稳定性仍有提升空间」；单次超过 30 s 身份漂移明显上升〔LP〕；价格是同档最高；多素材合成的结尾音效会乱〔毒眸〕。
- **对 4090 短剧的价值**：H3 最弱的打戏、大幅运镜、30 s 一镜到底、白模运镜迁移，以及「改一处不重抽」的局部编辑。**评级：采用**（云端回退首选；写实真人角色先做一次人脸审核小样）。

### 3.2 Kling 4.0 / 3.0 / O3（快手可灵）

- **定位**：文戏写实度与静态细节第一梯队，强在关键帧控制、方言对白和主体库（Element）。
- **规格**〔KL‑G〕：两个入口——Omni Reference（图、视频、Element、音色，也含文生与关键帧生）与 Keyframes（纯图片：首帧 / 首尾帧 / 中间帧），**同一任务不能混用**。提示词上限 8000 token；多镜头默认开启并自动拆分（Smart Storyboard）；只能上传音色，音乐与音效由画面生成。
- **官方提示词规范**〔KL‑G〕：
  - 用描述性语言，少抽象词，少否定：原文说否定提示「can increase the likelihood of errors」，只有 `no subtitles` 和 `no background music` 两条被认为必要；「打电话时不要露脸」应改写成「侧脸」。
  - 四段模板：`[Asset Roles]`（每个素材定义什么、保留什么）→ `[Overall Settings]`（场景与质感、风格、镜头基调）→ `[Sequence of Events]`（`0–X s / X–Y s / Y s–end`，每段写画面、动作、运镜、落幅）→ `[Audio]`（对白或旁白、环境声、音乐、音效）。
  - 素材按上传顺序自动编号 `@Image1 / @Video1 / @Element1`；不写职责，结果不可预测。
  - 关键帧句式：`Use @Image1 as the first frame and @Image2 as the last frame.`；中间帧可放任意时间点。
  - 编辑必须写 `Edit @Video1` + 改什么 + `Keep everything else unchanged`；写成 `Reference @Video1` 会被当成参考生成。
  - 台词放引号并声明语言；指定声线时写年龄、音色、语速、情绪。字幕也可以用提示词指定字号、位置、出现时间。
  - 分镜板可以当「镜头顺序参考」上传：要求模型重现分镜描述的成片画面，而不是分镜板本身。
- **Kling 3.0 / O3 的遗留经验**（fal 官方指南，经 `smixs/visual-skills` 整理；3.0 单次最多 6 镜 15 s）：五层 `Scene → Characters → Action → Camera → Audio`；`[Character A: …]` 标签开头定义一次；台词先绑一个独特动作再开口；声线写进标签 `[Character A, raspy deep voice]:`；连续两句之间加 `Immediately,`；相邻两镜景别和机位都相同会被合并成一镜；写 `no music` 不可靠，要干净音轨就关音频。
- **价格与接入**：720p $0.157、1080p $0.235、Flash 720p $0.094；参考视频另计，编辑约为参考价的 2 倍〔CF〕〔RW〕；官方站 10 积分 / s〔AIReel，未验证〕。官方提供远程 MCP（国内 `https://klingai.com/mcp`，海外 kling.ai）、CLI 和 Claude 插件 `klingai-tech/claude-plugin(-cn)`（三个 skill，提交前必须让用户确认参数，每个意图只提交一次）；Runway API、ComfyUI Partner Nodes、WaveSpeed、Atlas Cloud 都已上架 4.0。
- **弱项**〔毒眸〕：指令遵循、多素材图层融合、复杂物理落后 Seedance 2.5（一拳打空仍有击打音效、扫腿的执行者混淆、龙舟桨板方向错、复杂场景出现油蜡感）；光影偏平；音色参考自由度低；HDR 与 2 分钟延长仍未上线。
- **对 4090 短剧的价值**：需要 10 张关键帧锁节奏的长镜头、方言对白、跨集复用的主体库、动作库（Motion Control）。**评级：试用**。

### 3.3 Wan 3.0 托管版（阿里通义万相）

- **定位**：〔AA〕T2V 第一、每秒最便宜的 30 s 模型；**闭源，只有 API**（开源线停在 Wan 2.2，见本目录 01）。写实真人、广告、口播口碑好（什么值得买 2026‑09‑01）。
- **规格**〔WAN‑G〕：模型 `wan3.0-video` / `wan3.0-video-prime`；任务类型由 `input.media` 的类型和提示词自动路由；默认输出 1080P、30 fps、带声音；有视频输入时「输入 + 输出 ≤ 30 s」；`reference_*` 与首尾帧互斥；`file` 支持 docx / xlsx / pptx / pdf / txt / md，`link` 仅限无需登录的公开网页。
- **官方提示词公式**〔WAN‑G〕：`[总体描述] + [参考素材引用：图N / 视频N / 音频N] + [分镜N（起‑止秒）：主体 + 场景 + 运动 + 美学控制] + [台词：xx 说："……"] + [音效 / BGM] + [风格 / 情绪] + [负向清单]`，写不到的板块跳过。
  - 素材按上传顺序**分类型**编号（图 1 和视频 1 可以同时存在）；用途分开引用：「图1的儿童站在图2的现代公寓玄关内」「音色参考音频1」「仅参考图2的色调与光影，不参考人物」。
  - 多镜头：`第1个镜头[0-3秒]` 或 `分镜1（00:00-00:03）`，格式全篇统一，首尾相接不重叠，每段 2–5 s，段末可写「硬切转场 / 叠化转场」。
  - 台词 = 角色 + 说话动词 + 冒号 + 引号；多人逐句标说话人；要口型就追加「口型同步」；不要台词写「无台词」；BGM 三档：不写 / 明确指定 / 「无 bgm」。
  - 负向清单只写不希望出现的，不重复正向内容；故事板开头声明「仅作分镜指导」；编辑与白模场景列出「绝对保持不变」的项。
  - 官方还发了一个提示词优化 skill `wan3-pe`（`/wan3-pe` 调用）。
- **价格与接入**：$0.05 / 0.10 / 0.20 每秒；百炼 DashScope 异步任务（请求头 `X-DashScope-Async: enable`，轮询 `GET /api/v1/tasks/{task_id}`），视频 URL 24 小时失效，模型与 Key 必须同地域；fal、OpenRouter、Runway、ComfyUI 均有。
- **弱项**：阿里云自己的 GA 博客说音频质感和画面内文字「still maturing」；I2V 榜只排第 12；B 站评论「第一眼好看、动起来有问题」（什么值得买转述）；文档转视频时产品外观跨镜头会漂；**30 fps，与 H3 的 24 fps 混剪要重采**。
- **对 4090 短剧的价值**：最便宜的云端草稿、空镜、30 s 长简报〔Atlas〕。**评级：试用**。

### 3.4 MiniMax H3 托管版与 H3 衍生家族

- **定位**：与我们本地同一个底模。官方托管版多出 2K、Context‑IR 改写、Regenerate‑2K（规格与价格见 `docs/01-model-overview.md`）；衍生家族提供本地没有的任务端点。
- **fal H3 Max 家族**（fal 文档与〔CF〕节点名）：
  - `text-to-video / image-to-video / first-last-frame / reference`：480P $0.05、768P $0.08；另有 Max Turbo。
  - **Camera Controls**：单张图 + 2–12 个机位关键帧（环绕角、仰俯、距离）；提示词留空 = 场景冻结只动机位。
  - **Lip Sync**：图 + 给定音频 → 对口型视频，可带转写文本辅助，480P–2K。
  - **Recast**：把源视频里的主要人物换成参考照片里的人，保留原动作、机位、剪辑与音频（768P / 1080P）。
  - **Extend / Insert / Reframe**：文字引导续写、在两个时间点之间插入新段、改画幅。
- **其它衍生**：Pika H3 Flex（6 步，〔CF〕768p ≈ $0.02 / s，权重开放，本仓库已评测）；Creatify Boreal‑H3（广告向，I2V 榜第 3）；HeyGen Video 1（$0.02–0.04 / s 促销价，底模未验证）。
- **提示词**：与 H3 官方三段式 / 六段式通用（H3 Max 另有 `prompt_expansion_mode`）；〔LP〕把 243 条 Seedance 提示词原样搬到 H3 Max 768p，73% 判为复现。
- **弱项**：15 s 上限；横评里动作戏只动手、机位静止〔AIReel〕，会自己加没要求的元素（产品标签）；知乎实测称人脸偏油腻。
- **对 4090 短剧的价值**：Lip Sync、Camera Controls、Recast 正好补本地 H3 的三个短板，而且角色资产与提示词不用改。**评级：试用优先**（三个端点我们都还没实跑）。

### 3.5 Gemini Omni Flash 1.2 / Veo 3.1 / Flow（Google）

- **定位**：Omni 是 2026‑05‑19 I/O 发布的「任意输入 → 视频 + 对话式编辑」模型，1.2（11‑05）把单段从 10 s 提到 15 s、价格降 30%；Veo 3.1 是上一代的 8 s 模型，仍在 API 上。
- **Omni 的官方约束**〔OMNI〕：默认会自己切镜，要一镜到底必须写 `In a single continuous shot` / `No scene cuts`；没有独立的负面字段，直接在提示词里写 `Do not do X`；API 最多 6 张参考图，不收音频输入，不支持多段视频推理；延长只看输入的最后 10 s，更早出现的元素要重新描述或作为参考图再传一次；带人声的上传视频不能再加台词；所有输出带 SynthID。
- **Omni 的提示词维度**（DeepMind prompt guide）：景别与运动、风格、光、地点、动作五维；修改用一句话（`Change the camera angle to be over the violinist's shoulder.`）；故事板输入用 `Follow the story exactly in order starting top left. Entire story in 10 seconds.`。官方原话：Omni 不需要过度解释，「with Veo, by contrast, precise instructions are needed」。
- **Veo 3.1 的官方公式**〔VEO‑G〕：`[Cinematography] + [Subject] + [Action] + [Context] + [Style & Ambiance]`；台词 `A woman says, "We have to leave now."`；音效 `SFX: thunder cracks in the distance`；环境 `Ambient noise: …`；否定改写成正向（`a desolate landscape with no buildings or roads`）；时间戳 `[00:00-00:02] …`，一次 8 s 排 4 个镜头。
- **价格与接入**：Omni 1.2 $0.07 / s（720p），Gemini API、Vertex、Flow、OpenRouter、ComfyUI（`GeminiVideoOmniV2`）；Veo 3.1 $0.40 / s。
- **弱项**：Omni 官方只承诺英语，中文对白不可依赖；Google 自己说快速体育动作、快速文字变化、复杂物理仍在改进；Veo 8 s 上限且贵。
- **对 4090 短剧的价值**：对已有成片做便宜的对话式局部修改（换背景、改机位、去道具），以及画面内文字。**评级：Omni 试用（只用于编辑与英文内容）；Veo 3.1 观望**。

### 3.6 OpenAI Sora 2

2026‑03‑24 宣布关停 App、sora.com 与 API（Axios、Neowin），API 于 2026‑09‑24 下线，Azure Foundry 最后一个部署 2026‑10‑15 退役（`cclank/lanshu-awesome-ai-video-kit`），ComfyUI 的 Sora 节点已移除〔CF〕。它留下的写法（`Style: / Cinematography: / Actions:` 逐拍列表 `/ Dialogue:`）仍被各种提示词转换 skill 当作中间格式。**评级：跳过**。

### 3.7 Runway（Gen‑4.5 / Aleph 2.0 / Act‑Two）

- **定位**：自研生成模型已不在榜单前列，但 **视频编辑（Aleph 2.0）和表演迁移（Act‑Two）仍是专长**，API 同时代理了 Kling、Seedance、Wan、H3、Omni（Model Router）并提供 Product Ad / UGC / Multi‑Shot 这类成品 Recipe。
- **官方提示词规范**（`academy.runwayml.com/prompt-guide`）：文生 `[Camera] shot of [subject] [action] in [environment]. [Supporting]`；图生几乎只写运动 `The camera [motion] as the subject [action].`；只用正向表述；避免多段落的过度描述；时间戳 `[00:01] X occurs. [00:03] Y occurs.`；防乱切写 `continuous, seamless shot`；要机位不动写 `The locked-off camera remains perfectly still.`；首帧图里的运动模糊会和「静止」指令打架；长序列用末帧接下一段。
- **Aleph 2.0 的写法**：只命名变化，其余声明保持（`Replace the gray sky with a blue sky with clouds`；品牌替换时用参考首帧定义精确外观）。
- **价格**〔RW〕：Gen‑4.5 12 credits / s（2026‑06 从 25 降下来）、Aleph 2.0 28 / s（最低 56）、Act‑Two 5 / s、gen4_turbo 5 / s，$0.01 / credit；Gen‑4.5 为 2–10 s、720p。
- **对 4090 短剧的价值**：成片改一处（换天、换道具、换服装）与把真人表演迁到角色上。**评级：Aleph 2.0 / Act‑Two 试用，Gen‑4.5 观望**。

### 3.8 Luma Ray3.2

2026‑06‑09 发布：最长 20 s、1080p，最多 16 个关键帧，Modify Video（保留原片动作节奏只换服装与场景）、Reframe，原生 HDR 与 16‑bit EXR（ACES2065‑1）。官方 shot‑direction 写法 = 机位 + 主体 + 单一动作 + 场景 + 光影 + 风格 + 一致性约束。没有查到音频能力；Luma Agents（2026‑03）会在 Ray3.14、Veo 3.1、Kling 3.0 之间路由。HDR / EXR 是它独有的专业交付能力，对短剧无用。**评级：观望**。

### 3.9 Vidu Q4 Preview（生数科技）

2026‑10 初发布的预览版：参考生视频最多 15 张图 + 3 段音色（MP3，各 3–12 s，只取音色不复制词句），3–16 s，540p–4K，对白与音效同出。提示词用 `image 1 / audio 1` 按顺序引用，官方示例 `image 1 says "Welcome back!" in the voice from audio 1`；上限 5000 字符；seed 不能锁结果〔Comfy 教程页〕。〔CF〕1080p ≈ $0.084 / s，国内首发促销 0.09 元 / s 起；〔AA〕I2V 1032。多参考 + 音色参考的定位与 H3 Ref2VA 高度重叠，时长多 1 s、分辨率到 4K。**评级：观望**（等正式版；漫剧多角色镜头可以小额对比）。

### 3.10 其它生成模型（只列事实）

| 模型 | 状态与规格 | 价格（每秒） | 对我们 |
|---|---|---|---|
| PixVerse V6 / V6 Max / C1 | V6 与 C1 2026‑03 / 04 发布，≤ 15 s，同出音频；C1 面向分镜与动作 | V6 1080p 带音频 ≈ $0.115〔AA〕；Atlas 转售 $0.025–0.03 | 跳过 |
| Grok Imagine Video 1.5（xAI，2026‑05） | 480p–1080p，参考 / 编辑 / 延长 | 720p $0.14、1080p $0.25〔CF〕 | 跳过；〔LP〕用它做复跑，复现率 74% |
| FLUX 3 / FLUX 3 Max 视频（BFL，2026‑07 / 10） | 720p–2160p，另有 Video Continuation / Edit / Upscale | FLUX 3 ≈ $0.24、Max ≈ $0.145〔AA〕 | 观望 |
| HappyHorse 1.0 / 1.1（阿里 ATH，2026‑04 / 06） | 5–15 s 紧凑短片，原生环境音，提示词要短（30–55 词） | 720p ¥0.9、1080p ¥1.6 | 跳过 |
| LTX‑2.5 托管（Lightricks，2026‑08） | 权重开放；API 分 Fast / Pro，原生多镜头 | Fast 720p $0.09 起 | 本地路线见本目录 01 |
| Midjourney Video | 仍是 2025‑06 的 Video V1：图生视频，一次 4 条 5 s，可延长到约 21 s；图像模型已到 V8.2（2026‑07‑24） | 订阅制；约为出图的 8 倍 GPU 时间 | 只把 Midjourney 当定妆 / 首帧来源 |
| Utopai X、SkyReels V4、Hyperflow H3、MAGI‑2 | 〔AA〕前 20 常客；Utopai X 无 API | — | 未研究 |

### 3.11 数字人与口型

| 工具 | 输入 → 输出 | 价格（每秒，〔CF〕折算，口径见下注） | 备注 |
|---|---|---|---|
| H3 Max Lip Sync（fal） | 图 + 音频 → 视频，480P–2K | $0.05 / 0.08 / 0.16 / 0.32（480P / 768P / 1080P / 2K） | 与本地 H3 同族；超过 15 s ×1.2 |
| Kling Lip Sync / Kling Avatar 2.0 | 视频 + 音频；图 + 音频 | ≈ $0.07 每次；≈ $0.06–0.11 | 可灵站内对口型是国内对白戏的常用补救 |
| Seedance 2.5（音频参考 / Talking Avatar） | 参考图 + 音频 → 口型跟随上传音频 | 按 token，同 §1.1 | 〔LP〕建议只让一个角色对口型，间奏写闭嘴 |
| HeyGen Avatar IV / V、Video Translate | 照片或数字分身 + 文本 / 音频 | ≈ $0.04–0.08 / $0.12 / $0.025 | 口播数字人主力；API 2026 年改为按量付费 |
| VEED Lipsync 2.0、sync.so | 现成视频 + 新音频 → 重对口型 | 21.12、≈ 40.13 积分（折算口径不明） | Curious Refuge 2026‑07：VEED 2.0 在多镜头素材上「pretty good so far」 |

注：〔CF〕的积分有两种口径并存。2026‑05 之后上架的节点（Wan 3.0、Kling 4.0、H3 / H3 Max、Omni、Grok 1.5、HeyGen）按「301.73 积分 = 官方标价 $1」折算能和〔AA〕〔RW〕对上；更早的节点（Veo 3.1、Kling 3.0、PixVerse V6、HappyHorse 1.0）按 211 积分 = $1 才对得上。Comfy 支持文档写的是「$1 = 211 credits」，照此算新节点经 Comfy 购买会比官方标价贵约 43%——**这是推算，未验证**，以节点徽标和账单为准。

Hedra 这次没有查到 2026 年的可靠资料（见「未覆盖」）。本地等价物（InfiniteTalk、LTX A2V）在本目录 01 / 04。

### 3.12 增强与终处理

- **Topaz**：Starlight Precise 2.5（2026‑03，专门针对 AI 生成视频，云端）、Astra 2（2026‑04，可写提示词的超分，带 Creativity / Sharpness 滑杆）、Starlight Fast；〔CF〕按源帧计价，1080p 每帧 0.43（Fast）/ 0.70（Precise 2.5）/ 1.72（Astra 2）积分，10 s 24 fps 的片段用 Precise 2.5 约 168 积分（约 $0.6–0.8）。桌面版 Topaz Video 约 $299 / 年。
- **Magnific 视频超分**：Runway API 里 `magnific_video_upscaler_creative` 每帧 $0.007（1K）/ $0.009（2K）/ $0.012（4K），10 s @30 fps = $2.1 / 2.7 / 3.6〔RW〕。
- **其它**：字节 vCube Video Enhance（720p–8K）、Runway `enhance_frame_rate`（每 2 s 输入 1 credit）与 `ruby`（SDR → HDR）、LTX Upscale。
- **对我们**：本地已有 LBH latent 放大 + 二采与 RelayVSR，云端超分只在交付 4K 或救低清云端片段时才值。创作者经验：AI 视频色彩比特率低，后期调色空间小，色调要在场景图阶段定（Mx‑Shell）。**评级：观望**。

### 3.13 聚合平台与工作台

| 平台 | 是什么 | 值得知道的点 |
|---|---|---|
| 即梦短剧工作室（字节，随 Seedance 2.5 推出） | 剧本 → 资产 → 分镜 → 3D 导演台 → 生成 → 后期的一体化项目空间 | 国内同类产品里最完整；截帧注释式局部修改；≈ 0.19 元 / s |
| ComfyUI Partner Nodes | 在本地工作流里直接调云端模型的付费节点 | Kling 4.0、Seedance 2.5、Wan 3.0、H3 / H3 Max 全家、Vidu Q4、Omni、Runway、Luma、Pika Flex、HeyGen、Topaz 都有；`--disable-api-nodes` 可整体关闭 |
| Runway API / Model Router | 自研模型 + 第三方模型同一套 credits | 价目页是目前最全的「各家每秒价」对照 |
| Higgsfield | 多模型订阅 + Soul ID（从参考照片训练持久身份）+ Cinema Studio 4.0（机位 / 镜头参数） | Seedance 2.5 720p 订阅折算 ≈ $0.047 / s（Dreamina 页引用，未验证）；最多的 Claude 提示词 skill 生态 |
| Google Flow | Veo / Omni 的官方创作台 | 360p 草稿省积分、首尾帧、视频参考、延长时分析最后 10 s（2026‑08‑27 更新） |
| LTX Studio | 分镜工作台 + Elements（一致性资产） | 商用需 Standard（$35 / 月）以上 |
| fal、WaveSpeed、Atlas Cloud、Evolink、OpenRouter、Vercel AI Gateway | 按秒计费的 API 代理 | 2026 年 OpenRouter 与 Vercel 也开始列视频模型；同模型价格差可达 2 倍 |
| LibTV、小云雀、Seko、纳米漫剧流水线（360） | 国内「自动分镜 + 多模型」平台 | 只在教程标题与行业报道里见到，未研究 |

### 3.14 GitHub 上的提示词库与 skill（星数取自 2026‑11‑21 搜索 API）

| 仓库 | 星 · 更新 | 内容 | 对我们 |
|---|---|---|---|
| `LearnPrompt/awesome-seedance` | 2610 · 11‑21 | 1070 例（2.5 占 765）逐条回溯原帖；27 个模板写明「语料里多少例这样写」；494 次跨模型复跑（H3 Max 243 次 73%、Grok 240 次 74%、H3 768p 10 次 80%）；`seedance-production-workflow` skill 带 `validate_plan.py` 与 7 维 QA 表 | **采用其模板规则与 QA 表**（MIT 代码 / CC BY 4.0 内容） |
| `Evolink-AI/awesome-seedance-2.5-guides` | 419 · 11‑19 | 官方 36 个发布案例的完整提示词 + 保留的 Seedance 2.0 官方手册 | 采用（当官方写法的原文库） |
| `Evolink-AI/Awesome-Blender-Seedance-Workflow-Usecases` | 355 · 07‑20 | 39 个 Blender / Blender MCP 预演 → Seedance 的 X 案例，含限制测试 | 采用其结论（§四 案例 8） |
| `A-cat-with-carrots/OnlyShot` | 414 · 11‑10 | 即梦 CLI 短剧流水线、17 种失败模式、`compliance-2026.md` | **采用其失败模式表与合规清单**（MIT） |
| `10291124jcjc-dotcom/ai-anime-series` | 392 · 11 月 | 宫格故事板 → Seedance 2.5 一次出 30 s 的完整例子与脚本 | 试用（宫格法搬到 H3） |
| `liyue-aigc/seedance-2-5-video-director` | — | 把官方 User Guide 固化成能力快照 + 提示词蓝图 + 冲突诊断 | 借快照 |
| `cclank/lanshu-awesome-ai-video-kit` | 465 · 10‑07 | 604 条提示词、110 条「10 场景 × 11 模型」对照矩阵、`prompt-translator` / `model-selector` skill、每周巡检 32 个官方端点 | 借「按目标模型标签重写」的转换表；模型矩阵部分已过时 |
| `smixs/visual-skills` | 726 · 11‑06 | `dramaturgy.md` + 14 条通用规则（U1–U14）+ Seedance / Kling / Veo 语法 | 借通用规则（CC BY 4.0） |
| `klingai-tech/claude-plugin(-cn)` | 官方 | 可灵 MCP + 3 个 skill | 接入可灵时直接用 |
| `jnMetaCode/ai-shortfilm-prompts` | 557 · 11‑16 | Mx‑Shell《丧尸清道夫》等的原始提示词、5 段式方法论、制作 FAQ | 借案例数据（§四 案例 7） |
| `dexhunter/seedance2-skill`、`songguoxs/seedance-prompt-skill` | 4556、3023 | Seedance 2.0 时代的提示词 skill | 已被 2.5 的官方指南覆盖，跳过 |
| `UnderleveledBuilder/awesome-short-drama-skills` | 2672 · 11‑19 | 117 个短剧 skill 的索引（Seedance 47、H3 22、可灵 14、Wan 5、Veo 5）+ 三轮编剧 skill 盲评 | 当索引用；编剧 skill 的实测结论见本目录 02 |

## 四、创作者工作流案例（12 条）

每条写清：来源与日期、逐步工具与提示词写法、抽卡与成本、踩过的坑。作者自报的数字保持原口径。

### 案例 1 · OnlyShot：即梦 CLI 竖屏短剧流水线（一集 193 s ≈ 160 元）

- **来源**：〔OS〕v0.7.0（2026‑11‑10），作者在两个项目上实跑后沉淀；成本是作者 2026‑05 的即梦积分单价。
- **步骤**：① 联网扫近 30 天热点 → IP 简报 → 节奏地图（每段精确到秒，标 cold_open / twist / cliffhanger）→ 角色 / 场景 / 道具圣经；② 用即梦图片 5.0 出 ref 图库 80–150 张（每角色 5–8 张含动作与表情、每场景 3–5 张多角度、关键道具全角度）；③ 写 `分镜.json`：一集 36 段，时长按 4×11 + 5×14 + 6×5 + 7×3 + 8–10×3 变奏；④ **分镜图**：每段 1 张候选（爆点段 4 张），人工选定后改名为 `gridNN.png`，它就是视频首帧；⑤ 视频四种模式按文件是否存在自动选：`image2video` 80%、`frames2video` 10%、`multiframe2video` 5%、`multimodal2video` 5%；⑥ `拼接初剪.py` 拼成 1080×1920 初剪，自动加对白字幕、全程「AI生成」角标与元数据；⑦ 剪映精修，过上线清单。
- **提示词写法**：分镜图用 8 段 SOP（CHARACTER / BACKGROUND / ACTION / SCENE / CAMERA / LIGHT / TEXT / STYLE），1200–1400 字符；ref 图用 6 段身份块；`(@角色_ref.png)` 引用；风格指纹只在 ref 阶段追加，出分镜图时要关掉（否则 `neutral / flat` 会冲掉戏剧光）。
- **成本**：分镜图 3 积分 / 张，视频 55 积分 / 段 → 一集 ≈ 2230 积分（分镜图 108 + 视频 2120）≈ 160 元；先 `--dry-run` 看预估。
- **坑**：提示词超过约 1500 字符直接 `ret=1046 InvalidNode`（作者 N=8 的实测：< 1300 全过，> 1700 全挂，不是官方常数）；`sinister / menacingly / cold smirk` 这类反派词与「极近特写 + 面部细节」会触发内容审核；用 bash 拼中文提示词会被服务端静默丢弃，要用 Python `subprocess` 参数列表；并发从 8 降到 4；全能参考的任务在网页端「视频生成 → 全能参考 → 历史」里才看得到。

### 案例 2 · 巴中夫妻的日更漫剧（534 集、抖音 41 亿播放）

- **来源**：人人都是产品经理，子文《AI漫剧从0到1》（2026‑09‑10）；案例是《发配边关，罪妻开荒养出战神》，2026‑06 上线，冲到红果爆剧榜第一。播放数据为文章转述。
- **步骤**：① 豆包 / DeepSeek 写分镜脚本：3 分钟 60–80 个镜头，每镜 3–5 s，六要素 = 镜号、画面、动作、台词、时长、运镜；② 即梦出角色基准图并存成「角色模板」，开人物参考，权重 0.7–0.8（太高僵硬，太低锁不住脸）；③ 逐镜出分镜图，一次 4 张选优，合格标准是「脸对、场景对、构图对」，缺一即重出；④ Seedance 2.0 图生视频，3–5 s，人物幅度选轻微或中等、镜头缓慢推拉；对白多的戏换可灵对口型，远景和侧面回避口型；⑤ 剪映：内置 TTS（200–220 字 / 分钟）、字幕逐帧校对、转场 0.2 s、BGM 为人声的 20–30%；1080P 30 fps。
- **产能与收入**：熟练后一集 3–5 分钟只要 1–3 小时；抖音中视频约 60 元 / 万播放；作者同时给出万播收益从 2025 年约 100 元跌到 2026 年中 5–10 元；代工价资深组 2000–5000 元 / 分钟、量产组 500–1000 元 / 分钟。
- **坑**：镜号必须是阿拉伯数字，否则即梦批量导入失败；Seed 只稳画风不稳角色；运动幅度一大就崩脸、六指；古风字幕识别错字（「妾身」识别成「切身」）；服装变化必须写进剧本。

### 案例 3 · 三模型分工的一集短剧（Seedance 2.5 + Wan 3.0 + Kling 4.0）

- **来源**：〔WS〕2026‑10‑25（平台教程，价格是 WaveSpeed 标价）。
- **步骤与分工**：见链路 C。示例提示词的开头是 `Jun from @Image 2 steps into the flower shop from @Image 3 and speaks to Mara from @Image 1.`，结构 = 一句话总述 → 按时间拆解 → 一致性说明；Wan 的空镜写 `Static wide shot, slight drift to the right.`；Kling 的动作镜写 `Handheld tracking shot from behind`，并交代场面如何发展。
- **成本**：一分钟 720p 成片的生成费（不含重拍）= Wan $6.00、Kling $9.42、Seedance $21.60；草稿用 480p（Seedance $0.18 / s、Wan $0.05 / s）。
- **坑**：文章没给抽卡率；对白不准时不重抽整镜，而是重做特写；竖屏要留平台 UI 安全区。

### 案例 4 · 2 人 2 天的 3 分钟动画短片（164 条生成留 41 条）

- **来源**：invideo FAQ（2026‑07‑27 更新，**平台营销内容**，但给了少见的完整数字）。
- **步骤**：第 1 天 ① 锁风格：一次上传参考剧集的 64 帧，写一段带明确禁止项的风格块，之后每条提示词都以它开头；② 锁角色：11 张参考（4 个角色 + 1 个道具），Nano Banana 出设定板，每个角色约试 5 次（约 $9.78 / 角色）；③ Seedance 2.0 参考生视频，每段 15 s，角色板和风格块每次都带，逐条人工批准后才扣费。第 2 天 ④ 多生成再挑；⑤ 拼合镜头；⑥ 粗剪后让 agent 通看节奏。
- **抽卡**：每个可用镜头预算约 3 次生成；全片生成 164 条、保留 41 条（25%）；每条 15 s 平均只用 5 s；**17 个成片镜头（超过 40%）是把同一提示词的 2 条以上生成拼起来的**。
- **成本**：70 s 短片 $750、90 s $870、3 分钟 $950（约 $315 / 成片分钟），含平台订阅口径。

### 案例 5 · 宫格故事板直出 30 s 无对白动画（《汤圆和油条》）

- **来源**：`10291124jcjc-dotcom/ai-anime-series`（作者 X @DDJCXX；第 1 集 30 s 由即梦 Seedance 2.5 一次生成，480p）。
- **步骤**：① 每个角色一张设定图（三视图 + 表情 + 动作 + 剪影），要求剪影差别大、每人一个招牌能力；② 写镜头表（开场 → 冲突 → 反转 → 反击 → 结尾笑点）；③ 在即梦画布框选设定图出**黑白素描宫格故事板**，30 s 用 9 格、15 s 用 6 格、1 分钟拆成两段各 9 格；④ 全能参考 = 设定图 + 故事板 + 按秒写的镜头与音效，先出 480p；⑤ 脚本抽帧检查，只重出某一格（`panel 6`）或补拍某两格（`patch 5-6`），最后拼合集。
- **配套规则**〔LP〕模板：分镜板里不写时间码（会被画进视频）；每格必须是「正在发生的动作 + 景别」，否则成片像幻灯片；明确「角色图只管脸，故事板管地点、动作、构图与顺序」；格数按 1.5–3 s / 格倒推。
- **坑**：分镜板把人画在门的错误一侧，会压过正确的文字提示（〔LP〕production‑workflow skill）。

### 案例 6 · 古人说唱 Battle MV（Suno + Midjourney + Seedance 2.5 / H3）

- **来源**：`10291124jcjc-dotcom/ancient-rap-battle`（MIT，2026‑10）；本仓库 `docs/13-github-survey/05` 已评过它的 H3 路线。
- **步骤**：Claude 写两段各 16 句歌词 → Suno 先生成 A 段再 Extend 接 B 段（两个人声才分得开）→ demucs 分离人声、faster‑whisper 标每句时间 → Midjourney 出 9 张定妆（三视图、表情、半身、DJ、观众、场景）→ 自动生成 11 个素材包，每个含干净且切准的人声、参考图和「几秒到几秒唱哪半句」（时间写到 0.01 s，一句一个镜头）→ 即梦网页上传生成并放大到 2K → 逐镜头对齐口型 → 拼接、调色去「胶质感」、字幕。
- **成本**：H3 API 路线的成片 1 分 42 秒、34 句，视频生成约 $16（作者自报）。
- **坑**（H3 路线）：全身三视图会被拍成远景看不清口型，近景要用裁出的半身图；一条只给一句；H3 会把歌晚放 0.1–0.3 s，要按能量包络互相关校正；Suno 免费版不能商用。

### 案例 7 · Mx‑Shell《丧尸清道夫》（约 3 分钟，200+ 镜头）

- **来源**：`jnMetaCode/ai-shortfilm-prompts` 对作者直播与原始提示词的整理（方法论与 FAQ）；模型是 Seedance 2.0（非 Fast）。
- **提示词五段式**：核心主题（一行定调）→ 人物与基础设定 → 氛围与画质 → 运镜规则 → 分镜时间轴（单镜头按秒切片，多镜头按镜头切片）。每一秒交代动作、镜头、特效、声音四件事。
- **数据**：10 天；约 400 张图 + 200 多个视频镜头；单镜少则两三次、多则 20 多次才挑出能用的；95% 的提示词手写；成本对外说 3000 元，直播里改口「两万多」（含抽卡损耗）。
- **经验与坑**：低画质垫图会把参考图的画风带进成片，画质不够就纯文字；写瑕疵（磨损、掉漆、油污）比写「完美」更真；开场 15 s、一般镜头 5–10 s、短动作 4–5 s；两段之间靠**运动方向**接（从哪一侧出画，下一镜就从哪一侧进）；AI 视频色彩比特率低，色调要在场景图阶段定；IP 名会被拦截，换近义词；意外的好运镜无法复刻，「挑卡比磨提示词重要」。

### 案例 8 · 3D 白模 / 深度图迁移运镜与走位

- **来源**：`Evolink-AI/Awesome-Blender-Seedance-Workflow-Usecases`（39 个带原帖链接的 X 案例，2026‑06 至 07）；Curious Refuge《AI Film News》（2026‑07‑17）。
- **基本流程**（@reidhannaford 三步法）：Blender 摆相机与代理块 → Midjourney 出起始帧 → 两者一起送 Seedance。变体：viewport 预演导出后抽第一帧转写实图；用 iPhone 驱动 Blender 相机并按对白卡节奏（带音频的预演 + 两张静帧）；Mixamo 动作导入 Blender；让 Claude / Codex 通过 Blender MCP 在 2–3 分钟内搭出预演；不开 3D 软件时用玩具摆拍。
- **量化结果**：16 个机位快切的预演，约 73% 的计划剪辑点落在 ±0.6 s 内（@nemopi）；8 个角色的 15 s 环绕升空镜头全程保持住（@moframe2026）；没有预演时跑酷会塌成单纯奔跑。
- **坑与修法**：**简单代理块比精细 3D 好用**，精细的手和道具会把 CG 感带进成片；粗糙动画的僵硬过渡会被照抄，「关键帧 – 黑帧 – 关键帧」能保住走位又让成片更顺；完全忠实参考会让动作僵，适当降低参考对动作的约束、只保留位置关系；复杂场景试 4 次仍对不齐的情况存在；布料物理仍难。
- **深度图变体**（Curious Refuge）：把参考素材用 Depth Anything 转成灰度深度视频，连同角色与场景参考一起送 Seedance 2.0；纯黑白深度图效果最好，叠 OpenPose 骨架或彩色分割遮罩几乎没有帮助。

### 案例 9 · 即梦短剧工作室（90 s 短剧 3 小时、不到 100 元）

- **来源**：爱范儿张子豪实测（2026‑10‑29）；B 站 GenJi《我们用 Seedance 2.5 重拍了〈西游记〉》（2026‑11‑15，51.7 万播放，数字来自视频简介）。
- **步骤**：见链路 F。剧本入口三种（一句话、IP 改编、上传剧本），10–100 集；资产确认后沉淀为项目资产供续集复用；3D 导演台与智能预演不耗视频算力；生成后的修改手段是片段重拍、分离音频重新配音、智能切分（拆信息过载的镜头）、**截帧注释**（在不满意的画面上圈出位置再用一句话改，作者用它只改了人物服装）、重制转绘（换风格、画幅、地区本地化）。
- **成本**：720P 带参考视频最低约 0.19 元 / s（叠加年包与活动）；GenJi 自述 90 s 成片 3 小时、不到 100 元。
- **评价**：爱范儿认为价值在于「前面的创作被后续环节复用」和「局部修改替代整段重做」，但生成单价本身没有降低，多角色项目的抽卡成本仍会放大。

### 案例 10 · Google 官方的三个 Veo 3.1 工作流

- **来源**：〔VEO‑G〕（2025‑10‑15，官方博客）。
- **首尾帧做运镜**：用图像模型出正面起始帧和背后 POV 结束帧，Veo 提示词只写「镜头做一个平滑的 180° 弧线，从正面绕到背后」，再加一句唱词。
- **Ingredients 拍对白**：先出侦探、女人、办公室三张图，每个镜头都以 `Using the provided images for the detective, the woman, and the office setting, create a medium shot of …` 开头，台词写成 `…says in a weary voice, "Of all the offices in this town, you had to walk into mine."`，正反打各生成一条。
- **时间戳提示词**：`[00:00-00:02] Medium shot from behind … [00:02-00:04] Reverse shot … SFX: … [00:04-00:06] Tracking shot … Emotion: … [00:06-00:08] Wide, high-angle crane shot …`，一次生成四个镜头。

### 案例 11 · 工作室流水线与岗位分工（行业报道）

- **无锡起点互动**（Sixth Tone，2026‑08‑25）：自研平台按「热点选题 → 剧本 → 角色 / 场景 / 物件 / 灯光预设库 → 逐秒分镜 + 3D 摆位插件 → 视频生成 → 另一个模型按 10 多项打分（钩子、情绪节奏、场景效率、过审风险）→ 组长人工检查 → 剪辑」运转；三个小组（角色与场景、生成、剪辑），每环 1–2 人加一名组长；2026‑06 时日产 4–5 部、每部 30–44 集。视频提示词直接写机型和镜头（Arri Alexa 65、Panavision Primo、35mm）。
- **抽卡**：同报道里上海一位制作人说同一镜头要生成 3–5 次，每次几分钟，高峰排队 10–20 分钟；有专职「抽卡员」。常见缺陷是人物「油腻」、定格时细节崩、物件跨镜头变化（沙发座位数和材质）。
- **其它口径**：12 人约 30 天做出《斩仙台下，我震惊了诸神》（36 氪 2026‑02‑26）；可灵 3.0 时期有人实测 10 段只有 2 段可用、Seedance 2.0 排队 6 小时（虎嗅 2026‑03‑10，搜索摘要）；《霍去病》的「3 人 48 小时」被导演澄清为近 20 人团队、48 小时是纯工作时间、算力约 3000 元不含人力（腾讯云开发者社区 2026‑03）。

### 案例 12 · 一人 3 分钟短片的预算与工时（海外）

- **来源**：MindStudio（2026‑03‑27，Runway + Kling 时期，数字偏旧但结构可用）。
- **预算**：脚本 $5、概念图 $3–10、视频生成 $48–120、配音（ElevenLabs）$5–11、配乐（Suno Pro）$0–8、超分 $0–10、剪辑（DaVinci 免费版）$0，合计 $61–165。
- **素材比**：180 s 成片对应 80–150 条、300–500 s 原始素材（1.7–2.8 倍），每条最多重生成 3 次。
- **工时**：20–40 小时（前期 3–5、生成与改提示词 8–15、音频 2–4、剪辑 5–10）；新手 1–2 周，熟手 2–5 天。

