# H3 之外：什么镜头该换模型，别的工作流里哪些做法能搬进来

> 依据 `docs/14-ai-video-workflows/`（2026-11 对整个 AI 视频领域现有工作流的调研）：`01` 开源模型的 ComfyUI 工作流、`03` 商业模型与创作者实战、`04` 声音与后期、`05` 一致性与分镜生图。节点是否存在已用 ComfyUI v0.37.2 与 v0.46.2 源码逐个核对；**耗时与画质结论全部来自他人机器，没有在本机 4090 上实测**，换模型前先做同分镜单段样片 A/B。

## 0. 先判断要不要离开 H3

有中文对白的剧情段是 H3 的主场：音画同生、`<d>` 对白、9 图 + 音色参考、单次多镜头，本地开源模型里没有整体替代品（唯一同类 LTX-2.5 的中文对白未验证、24 GB 余量紧）。只有下面这些情况才换：同一问题在 H3 上按 `pitfalls.md` 改过提示词 / 参考 / 步数后仍连续两批不过，且属于 §1 表里的镜头类型。

## 1. 本地替补表（ComfyUI 0.37.2 核心已内置这些节点；RelayVSR 需 ≥ 0.45）

| 镜头类型 | 首选 | 备选 | 做法要点 | 代价 |
|---|---|---|---|---|
| 快速动作 / 打斗 / 舞蹈 | **Wan-Animate-2**（驱动视频决定动作；`WanAnimate2ToVideo`，模板 `video_wan_animate2`） | SCAIL-2（`WanSCAILToVideo`，动画 / 换人）；无驱动视频时 Wan 2.2 I2V 20 步 | 角色参考用同一张角色卡；驱动视频自拍或取素材并重采到 16–24 fps、景别与参考图一致；`wan_animate_2_int8_convrot`，832×480，81 帧一段，lcm 6 步，CFG 1，shift 5；text_1 只写「人物外观 + 背景」，动作写 text_2；续接接 `continue_motion` 与 `video_frame_offset` | 480p–720p 要超分；无声、无对白，音效后配 |
| 明确运镜（推拉摇、环绕） | **Wan 2.2 Fun Camera**：H3 首帧 + `WanCameraEmbedding` 预设（Static / Pan 四向 / Zoom In·Out / 顺逆时针 + speed）→ `WanCameraImageToVideo`，`wan2.2_fun_camera_{high,low}_noise_14B_fp8_scaled` | ATI / WanMove 画轨迹；LTX-2 19B 运镜 LoRA | 一镜一个预设；4 步蒸馏会损失动态，运镜镜头优先 20 步档 | 16 fps、5 s、无声 |
| 特效（能量、粒子、变身） | **Wan-Alpha**（模板 `video_wan2.1_alpha_t2v_14B`，RGBA 透明层）后期叠到 H3 画面 | VACE 遮罩重绘；Bernini-R 带参考编辑 | 特效与表演分层：H3 管人物与声音，特效层单独生成 | 多一步合成 |
| 长镜头 > 15 s | 有对白：核心 `MiniMaxH3ContextWindows`（≥ 0.44；124 / 39 / pyramid）与现有 Motion-Context 路线 A/B；再测 LTX-2.5（单次到 20 s） | 无对白：Wan 2.2 + SVI 2.0 Pro（每段 81 帧、换种子、锚点固定为首帧） | 分块估时：块数 = ⌈(总帧 − 重叠) / (窗口 − 重叠)⌉，重叠区算两遍；带参考 / 引导的窗口几乎不漂，纯 I2V 分块会漂 | LTX 中文对白未验证；SVI 易慢动作 |
| 精确口型 / 现成配音 | **InfiniteTalk**（`WanInfiniteTalkToVideo`：length 81、motion_frame_count 9、6 步、CFG 1、25 fps、`wav2vec2-chinese-base_fp16`；配音先做人声分离）；对已出的 H3 片段补口型用 kijai 的 V2V 版（4 步、shift 11、start_step 2） | LTX-2.5 A2V（冻结音频 latent、成片直接封装原波形）；Wan 2.2 S2V；H3 自己的音频锁节点（见 `quality-pipeline.md`） | 双人镜画遮罩各接一路音频；每多 3.24 s 接一个 Extend 组 | 480p 起步需超分；V2V 的运镜与原片不完全一致 |
| 换装 / 换道具 / 去穿帮 | **Bernini-R** rv2v（`BerniniConditioning`，关 Turbo 跑 40 步） | VACE 遮罩重绘；LanPaint（H3 自身局部重绘） | 只改问题区域，不重抽整段 | 81 帧一段 |
| 段缝跳变、不想重生成 | **VACE Joiner**（`stuttlepress/ComfyUI-Wan-VACE-Video-Joiner`，MIT）：在任意来源的两段之间重生成过渡帧 | 4 帧叠化（现方案） | 片段先降到 16 fps、分辨率取 16 的倍数，过渡帧生成后插帧回 24 fps，接 KJNodes `ColorMatch` | 过渡段无原生音频，音频照旧交叉淡化 |

共同约束：换模型出的片段必须回到同一条后期链——统一 24 fps（Wan 14B 是 16 fps，InfiniteTalk 25 fps，Animate / SCAIL 模板 30 fps）、同一个超分、`ColorMatch` 对齐相邻 H3 段；对白与音色仍由 H3（或配音 + 口型模型）负责。

## 2. 换模型时的硬规则

- 参数一律从官方模板读，不凭记忆写：`Comfy-Org/workflow_templates/templates/<模板名>.json`（子图在 `definitions.subgraphs`）。LTX 参数不合法不报错而是静默改值。
- 帧数网格：Wan 4n+1（81）、LTX 8n+1（121 / 241）、H3 17k+5；宽高 Wan 取 16 的倍数、LTX 取 32 的倍数。
- Wan 2.2 14B 用 `wan_2.1_vae`，5B 用 `wan2.2_vae`，不可互换。草稿档：`wan2.2_i2v_lightx2v_4steps_lora_v1_{high,low}_noise` 1.0，4 步（高噪 2 + 低噪 2），CFG 1，shift 5；定稿档关 LoRA、20 步、CFG 3.5、第 10 步交接。蒸馏件与「T2V / I2V × high / low」逐一对应，不叠两个。
- 24 GB 跑 LTX-2.5：`ltx-2.5-22b-distilled-transformer-comfy-int8-convrot`（21.5 GB），文本编码后先卸载 Gemma 4 再采样，`VAEDecodeTiled` 解码；蒸馏档固定用模板 sigma 与 CFG 1，不改步数。
- RTX 4090 不下 NVFP4 权重（只有 50 系有原生加速）；GGUF 只在装不下时用，它不提速。
- 许可：Wan 系 Apache-2.0；LTX-2.x 要求年营收 < 1000 万美元；HunyuanVideo 不适用于欧盟 / 英国 / 韩国；MoCha（AGPL）、SkyReels（skywork-license）、依赖 InsightFace buffalo 的模型（非商用）进商用管线前先读原文。
- 报耗时带齐口径：分辨率 × 帧数 × 步数 × 权重精度 × 硬件 × 首跑还是热跑；计时取 ComfyUI 服务端 `execution_start → execution_success`，复测换 seed。

## 3. 从别的工作流搬进 H3 流水线的做法

- **切点四要素**（LTX 多镜头规范）：每个 `[Shot N]` 切点写清转场方式、重建景别与机位、用同一组外观标识复述人物、交代声音是否跨切点延续。
- **拼表式参考的版式**（LTX Ingredients）：黑底或白底、一个元素一个面板、不放文字、重要元素面板更大。
- **终处理链用核心节点**：插帧 `FrameInterpolationModelLoader` + `FrameInterpolate`（`film_net_fp16` 或 `rife_v4.26`，放 `models/frame_interpolation/`，HF `Comfy-Org/frame_interpolation`）；像素超分 RelayVSR ×2（`relayvsr_x2_lightx2v_int8_convrot` + `relayvsr_flash_vae_x2_fp32`，1 步、CFG 1，需 ComfyUI ≥ 0.45，×2 与 ×4 权重不混用）；无对白的漫剧 / 远景镜头可用 Wan 2.2 低噪 4 步 denoise 0.25 精修。
- **识别短语的生成模板**（Animate-2 官方）：让 LLM 只写「人物外观描述 + 背景描述」，不写动作。
- **排错**：文本编码后卸载编码器再采样；最后一步 OOM 先换分块解码；`POST /free` 返回空 body 属正常；`torch.compile` 首跑显存暴涨时清 `C:\Users\<用户>\.triton` 与 `AppData\Local\Temp\torchinductor_<用户>`。

## 4. 云端模型何时值得花钱

（待 `docs/14-ai-video-workflows/03` 完成后补全：各商业模型的强弱对照、价格与接入方式。）出关键帧的三种付费情形见 `image-stage.md`。
