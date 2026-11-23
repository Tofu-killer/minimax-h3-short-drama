# H3 之外：什么镜头该换模型，别的工作流里哪些做法能搬进来

> 依据 `docs/14-ai-video-workflows/`（2026-11 对整个 AI 视频领域现有工作流的调研）：`01` 开源模型的 ComfyUI 工作流、`03` 商业模型与创作者实战、`04` 声音与后期、`05` 一致性与分镜生图。节点是否存在已用 ComfyUI v0.37.2 与 v0.46.2 源码逐个核对；**耗时、画质与价格结论全部来自他人机器或官方标价，没有在本机 4090 上实测，也没有实跑任何云端模型**，换模型前先做同分镜单段样片 A/B。

## 0. 先判断要不要离开 H3

有中文对白的剧情段是 H3 的主场：音画同生、`<d>` 对白、9 图 + 音色参考、单次多镜头，本地开源模型里没有整体替代品（唯一同类 LTX-2.5 的中文对白未验证、24 GB 余量紧）。只有下面这些情况才换：同一问题在 H3 上按 `pitfalls.md` 改过提示词 / 参考 / 步数后仍连续两批不过，且属于 §1 表里的镜头类型。

## 0b. 换模型之前：H3 自己还有几种修法（社区节点；读文档和源码整理，**都没有在这套流程里执行过**）

下面几样都留在 H3 里，用的是同一份权重、同一条 take 的 latent，所以不用去适配另一个模型的画风和声音。前四样来自 `WASasquatch/was-node-suite-comfyui`（装机量很大的节点包，2026-11-19 的版本里有三十多个 H3 节点；它自己没有必装依赖，README 写的要求是 ComfyUI ≥ 0.14），第五样是论文项目 `code-video-model/CodeVideoModel` 的做法。

| 问题 | 留在 H3 里的做法 | 节点与关键参数 | 备注 |
|------|------------------|----------------|------|
| 一段里只坏一两秒（一个多出来的道具、一次穿帮、一句念错的词） | 只把那个时间窗重画，再接回原片 | `H3 Repair Window` → 采样器（denoise 1.0）→ `H3 Repair Splice`。`start_seconds` / `end_seconds` 会对齐到 17 帧一块；`picture_strength` 1.0 = 从噪声重画、0.6 = 在原画面上翻新、0 = 画面不动；`sound_strength` 0 = 声音不动（画面在原声下面重画，口型仍跟原声）、1.0 = 声音也重来；`context_frames` 34 = 两侧各带两块上下文给采样器看；`feather` 0.35 软化接缝 | 输入是一条 H3 音画 latent——草稿带 `--keep-latent` 存下的两个 `.latent` 文件（`LoadLatent` ×2 → `LTXVConcatAVLatent`）就是；`positive` 接这一段原来的条件。跨切点的时间窗会被拒绝。这就是此前标着「没有工具」的局部重拍 |
| 口型要跟一条现成的音轨（重录的台词、外语配音、歌） | 把音轨钉在音频流上，让画面在它下面生成 | `H3 Soundtrack`：`audio` 接整条音轨，`strength 1.0` = 原样保持、0.5 = 只作引导；`offset_seconds` 定它从成片的哪一秒开始；`past_end` 定音轨放完之后怎么办 | 单个镜头也能用（`window` 接 `EmptyMiniMaxH3LatentAV`）。配音先做人声分离；和 §1 的 InfiniteTalk 比，它不换模型、画面仍是 H3 的 |
| 快动作糊成一片 | 把快的部分放慢 → 重画 → 恢复原来的时序 | `H3 De-RoPE Stretch`（`strength 0.5`，采样步数 = 一采步数 × 这个值：8 步的片子用 4 步）→ 采样 → `H3 De-RoPE Refine` → `H3 De-RoPE Recover` | 只动运动最快的那部分帧，平静的片段原样通过 |
| 长段或二采显存不够 | 注意力按头、按 token 分块算 | `H3 Low VRAM`：`head_chunks 4`（56 个头每次算 14 个）、`query_chunks 4`、`token_slice 8192`；作者写明结果相同、只是更省 | 和 KJNodes 的 `MiniMax H3 Low VRAM Attention` / `Chunk FeedForward` 是同一类做法，二选一 |
| 运镜和走位要照预演来 | 一段布局视频（白模、Three.js、手机拍的走位）只在**前 1/4 的步数**里当参考，之后去掉 | 两个 `MiniMaxH3ReferenceToVideo`：A 接外观参考图 + `ref_videos.ref_video_0`（`LoadVideo` → `GetVideoComponents` 的帧，24 fps、2–15 s），B 只接外观参考图；`ConditioningSetTimestepRange` 把 A 限在 0–0.25、B 限在 0.25–1，`ConditioningCombine` 合起来接引导器 | 原项目是 20 步里前 5 步带布局视频（960×544、5 s、shift 12 / 3），提示词用自然语言；早期的步数定构图和运动，后面的步数定质感，所以白模的灰色外观不会带进成片。这种接法在真实的 0.37.2 上通过了服务器校验；`--media` 不认两个条件节点，要手工搭 |

同一个节点包里还有：一个节点管多段的导演台（`MiniMax H3 Conditioning` + 时间线窗口，九种段间接法，其中有「硬切但声音延续」和「硬切、从上一段抽几帧当演员参考」）、把编码好的参考存成文件反复用（RefMod）、从第 N 段重跑（`H3 Save Clip` / `H3 Load Clip`）、分瓦片精修任意长度的片子（`H3 Tiles`、`H3 Upscale Video`）、只给声音挂 LoRA（`H3 Sound LoRA`）。本流程的脚本不依赖它们；用了其中哪一样，先在一段 5 s 的片子上验证再用到正片。

## 1. 本地替补表（ComfyUI 0.37.2 核心已内置这些节点；RelayVSR 需 ≥ 0.45）

| 镜头类型 | 首选 | 备选 | 做法要点 | 代价 |
|---|---|---|---|---|
| 快速动作 / 打斗 / 舞蹈 | **Wan-Animate-2**（驱动视频决定动作；`WanAnimate2ToVideo`，模板 `video_wan_animate2`） | SCAIL-2（`WanSCAILToVideo`，动画 / 换人）；无驱动视频时 Wan 2.2 I2V 20 步 | 角色参考用同一张角色卡；驱动视频自拍或取素材并重采到 16–24 fps、景别与参考图一致；`wan_animate_2_int8_convrot`，832×480，81 帧一段，lcm 6 步，CFG 1，shift 5；text_1 只写「人物外观 + 背景」，动作写 text_2；续接接 `continue_motion` 与 `video_frame_offset` | 480p–720p 要超分；无声、无对白，音效后配 |
| 明确运镜（推拉摇、环绕） | **Wan 2.2 Fun Camera**：H3 首帧 + `WanCameraEmbedding` 预设（Static / Pan 四向 / Zoom In·Out / 顺逆时针 + speed）→ `WanCameraImageToVideo`，`wan2.2_fun_camera_{high,low}_noise_14B_fp8_scaled` | ATI / WanMove 画轨迹；LTX-2 19B 运镜 LoRA | 一镜一个预设；4 步蒸馏会损失动态，运镜镜头优先 20 步档 | 16 fps、5 s、无声 |
| 特效（能量、粒子、变身） | **Wan-Alpha**（模板 `video_wan2.1_alpha_t2v_14B`，RGBA 透明层）后期叠到 H3 画面 | VACE 遮罩重绘；Bernini-R 带参考编辑 | 特效与表演分层：H3 管人物与声音，特效层单独生成 | 多一步合成 |
| 长镜头 > 15 s | 有对白：核心 `MiniMaxH3ContextWindows`（≥ 0.44；124 / 39 / pyramid）与现有 Motion-Context 路线 A/B；再测 LTX-2.5（单次到 20 s） | 无对白：Wan 2.2 + SVI 2.0 Pro（每段 81 帧、换种子、锚点固定为首帧） | 分块估时：块数 = ⌈(总帧 − 重叠) / (窗口 − 重叠)⌉，重叠区算两遍；带参考 / 引导的窗口几乎不漂，纯 I2V 分块会漂 | LTX 中文对白未验证；SVI 易慢动作 |
| 精确口型 / 现成配音 | **InfiniteTalk**（`WanInfiniteTalkToVideo`：length 81、motion_frame_count 9、6 步、CFG 1、25 fps、`wav2vec2-chinese-base_fp16`；配音先做人声分离）；对已出的 H3 片段补口型用 kijai 的 V2V 版（4 步、shift 11、start_step 2） | LTX-2.5 A2V（冻结音频 latent、成片直接封装原波形）；Wan 2.2 S2V；H3 自己的音频锁节点（见 `quality-pipeline.md`） | 双人镜画遮罩各接一路音频；每多 3.24 s 接一个 Extend 组 | 480p 起步需超分；V2V 的运镜与原片不完全一致 |
| 换装 / 换道具 / 去穿帮 | **Bernini-R** rv2v（`BerniniConditioning`，关 Turbo 跑 40 步） | VACE 遮罩重绘；LanPaint（H3 自身局部重绘） | 只改问题区域，不重抽整段 | 81 帧一段 |
| 段缝跳变、不想重生成 | **VACE Joiner**（`stuttlepress/ComfyUI-Wan-VACE-Video-Joiner`，MIT）：在任意来源的两段之间重生成过渡帧 | 硬切 + 剪辑单里的 `l_cut`（现方案，`mix_episode.py`） | 片段先降到 16 fps、分辨率取 16 的倍数，过渡帧生成后插帧回 24 fps，接 KJNodes `ColorMatch` | 过渡段无原生音频，音频照旧交叉淡化 |

共同约束：换模型出的片段必须回到同一条后期链——统一 24 fps（Wan 14B 是 16 fps，InfiniteTalk 25 fps，Animate / SCAIL 模板 30 fps）、同一个超分、`ColorMatch` 对齐相邻 H3 段；对白与音色仍由 H3（或配音 + 口型模型）负责。

## 2. 换模型时的硬规则

- 参数一律从官方模板读，不凭记忆写：`Comfy-Org/workflow_templates/templates/<模板名>.json`（子图在 `definitions.subgraphs`）。LTX 参数不合法不报错而是静默改值。
- 帧数网格：Wan 4n+1（81）、LTX 8n+1（121 / 241）、H3 17k+5；宽高 Wan 取 16 的倍数、LTX 取 32 的倍数。
- Wan 2.2 14B 用 `wan_2.1_vae`，5B 用 `wan2.2_vae`，不可互换。草稿档：`wan2.2_i2v_lightx2v_4steps_lora_v1_{high,low}_noise` 1.0，4 步（高噪 2 + 低噪 2），CFG 1，shift 5；定稿档关 LoRA、20 步、CFG 3.5、第 10 步交接。蒸馏件与「T2V / I2V × high / low」逐一对应，不叠两个。
- 24 GB 跑 LTX-2.5：`ltx-2.5-22b-distilled-transformer-comfy-int8-convrot`（21.5 GB），文本编码后先卸载 Gemma 4 再采样，`VAEDecodeTiled` 解码；蒸馏档固定用模板 sigma 与 CFG 1，不改步数。
- 这里说的 Wan / LTX 等替补模型：RTX 4090 不下它们的 NVFP4 扩散权重（只有 50 系有原生加速）；H3 的文本编码器照常用 `nvfp4_awq` 版；GGUF 只在装不下时用，它不提速。
- 许可：Wan 系 Apache-2.0；LTX-2.x 要求年营收 < 1000 万美元；HunyuanVideo 不适用于欧盟 / 英国 / 韩国；MoCha（AGPL）、SkyReels（skywork-license）、依赖 InsightFace buffalo 的模型（非商用）进商用管线前先读原文。
- 报耗时带齐口径：分辨率 × 帧数 × 步数 × 权重精度 × 硬件 × 首跑还是热跑；计时取 ComfyUI 服务端 `execution_start → execution_success`，复测换 seed。

## 3. 从别的工作流搬进 H3 流水线的做法

- **切点四要素**（LTX 多镜头规范）：每个 `[Shot N]` 切点写清转场方式、重建景别与机位、用同一组外观标识复述人物、交代声音是否跨切点延续。
- **拼表式参考的版式**（LTX Ingredients）：黑底或白底、一个元素一个面板、不放文字、重要元素面板更大。
- **终处理链用核心节点**：插帧 `FrameInterpolationModelLoader` + `FrameInterpolate`（`film_net_fp16` 或 `rife_v4.26`，放 `models/frame_interpolation/`，HF `Comfy-Org/Frame-Interpolation`（旧名 `frame_interpolation` 会跳转过来））；像素超分 RelayVSR ×2（`relayvsr_x2_lightx2v_int8_convrot` + `relayvsr_flash_vae_x2_fp32`，1 步、CFG 1，需 ComfyUI ≥ 0.45，×2 与 ×4 权重不混用）；无对白的漫剧 / 远景镜头可用 Wan 2.2 低噪 4 步 denoise 0.25 精修。
- **识别短语的生成模板**（Animate-2 官方）：让 LLM 只写「人物外观描述 + 背景描述」，不写动作。
- **排错**：文本编码后卸载编码器再采样；最后一步 OOM 先换分块解码；`POST /free` 返回空 body 属正常；`torch.compile` 首跑显存暴涨时清 `C:\Users\<用户>\.triton` 与 `AppData\Local\Temp\torchinductor_<用户>`。

## 4. 云端模型何时值得花钱

本地 H3 本身就在公开榜单前列（Artificial Analysis 2026-11：文生视频第 3、图生视频第 5），H3 Max、Pika H3 Flex 等都是它的后训练衍生。所以云端不是「换更好的模型」，而是只买 H3 的结构性短板。**以下强弱判断来自 4 个第三方横评与官方文档，口型与中文台词没有任何独立横评；价格为 2026-11 官方或一级代理标价，全部未在本项目实跑。**

| 镜头类型 | 触发条件 | 云端首选 | 备选 / 本地替代 | 标价（每秒） |
|---|---|---|---|---|
| 对白、正反打、情绪特写、漫剧 | ≤ 15 s、说话人 ≤ 2 | **留在本地 H3** | — | 0 |
| 打戏、追逐、摔打 | 超过 3 s 的全身接触动作 | Seedance 2.5（720p） | Kling 4.0；本地 Wan-Animate-2 | 约 $0.23；$0.157 |
| 指定轨迹的运镜（环绕、升降、穿越） | 运镜是镜头主体 | H3 Max Camera Controls（单图 + 2–12 个机位关键帧） | Seedance 2.5 + 白模 / 深度图参考视频；本地 Wan Fun Camera | $0.08；约 $0.23 |
| 不能切的长镜头 | 单镜 > 15 s | Kling 4.0（单次 30 s，10 张关键帧锁节奏）或 Seedance 2.5（单次 30 s） | Wan 3.0（最便宜，30 fps 需重采）；本地续接链 ≤ 4 段 | $0.157；约 $0.23；$0.10 |
| 给定音频的精确口型 | 歌、外语配音、重录台词，音频不能动 | H3 Max Lip Sync | 本地 InfiniteTalk、H3 音频锁节点 | $0.08（768P） |
| 成片只坏一处 | 多出的道具、服装、背景、穿帮字 | Gemini Omni Flash 1.2 对话式编辑（只可靠支持英语对白的片段） | Runway Aleph 2.0；本地 Bernini-R / VACE | $0.07（720p）；$0.28 |
| 换人 / 表演迁移 | 有可用的驱动视频 | H3 Max Recast | 本地 Wan-Animate-2 | 约 $0.30（768P） |
| 画面内必须清晰的文字、包装 | 无法后期叠加 | Seedance 2.5 | 首选仍是后期叠 | 约 $0.23 |

量级参考：60 s 一集 12 段里 3 段走云端（8 s 打戏抽 3 次 + 20 s 长镜头抽 2 次 + 10 s 对口型抽 2 次）合计约 $13（官方标价，不含代理加价）。行业抽卡基准：每个可用镜头按 3 次生成、约 25% 成片率做预算。Sora 2 已于 2026-09-24 停服；Veo 3.1 仍限 8 s。

**接入与纪律**

1. 默认所有段留在本地；只有命中上表触发条件，且同一段按 `pitfalls.md` 改过之后仍连续两批出现同样问题，才改云端（与 SKILL.md 铁律 18 同一口径）。分镜 JSON 里给该段记 `route`（`local_h3` 或 `cloud:<模型>`）与 `cloud_reason`，`logs/takes.csv` 记模型、分辨率、计费秒数、单价（这两个字段脚本会原样忽略，仅作记录）。
2. **草稿永远在本地**：云端只重拍已在本地确认过构图、台词、节奏的段，并把本地中选 take 的首帧作为云端的首帧或参考，保证接得上。
3. 三条调用路径，改动量从小到大：① ComfyUI Partner Nodes（Kling 4.0、Seedance 2.5、Wan 3.0、H3 Max 全家都有节点，继续用 `comfy_submit.py` 提交；需要 Comfy 账号积分，从脚本提交如何带鉴权未实测；计价以节点徽标的积分为准，可能比官方标价贵）；② 官方 agent 工具（可灵 MCP / CLI、即梦 `dreamina` CLI）；③ 直连异步 API（BytePlus ModelArk、DashScope、fal、Gemini API、Runway API），都是「提交 → 轮询」，与仓库 `docs/02-api-reference.md` 的写法一致。
4. 同一份分镜编译到云端时按目标模型改语法，台词文字原样透传：Seedance 用 `@Image N` + `0-5秒` + `{台词}`；Kling 4.0 用 `[Asset Roles] / [Overall Settings] / [Sequence of Events] / [Audio]`；Wan 3.0 用「图N + 第N个镜头[0-3秒] + xx 说："…"」；Omni 加 `In a single continuous shot`。只有送云端时才写 `Do not use…` 排除句，本地 H3 仍靠预处理参考图（白底、裁背景、去文字）。
5. 回收：结果 URL 会过期（Wan 3.0 为 24 小时），生成后立即下载；统一转成 24 fps、1920×1080、−14 LUFS 再进时间线；色调差异在首帧阶段对齐，不指望后期拉回来。
6. 合规：即梦 / 火山方舟不收真人脸参考，写实角色先传一张测试是否被判为真人；投国内平台要全程 AI 标识并写元数据 `AIGC` 字段（`ffprobe -show_entries format_tags=AIGC` 检查）。送 Seedance 2.5 且主体超过 5 个时把角色板拆成一视角一张图。
