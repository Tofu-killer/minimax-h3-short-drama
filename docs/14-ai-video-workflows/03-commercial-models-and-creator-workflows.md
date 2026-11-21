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

