# 14‑01 · 开源视频模型在 ComfyUI 里的工作流（H3 之外）

> 调研日期 2026‑11‑21。方法：GitHub 搜索 API 确认现存模型与版本；稀疏克隆 `Comfy-Org/workflow_templates`（f77d47c，v0.11.114，2026‑11‑21）并用脚本拆出 156 个本地视频 / 视频工具 / 创作者模板的模型文件、采样器、步数、分辨率、帧数与便签；稀疏克隆 ComfyUI 核心（f99de88，**v0.46.0**，2026‑11‑21）读 `comfy_extras/nodes_wan.py / nodes_lt*.py / nodes_context_windows.py` 等节点签名；克隆 `kijai/ComfyUI-WanVideoWrapper`（a7439db，2026‑11‑13，44 个示例工作流）、`Lightricks/ComfyUI-LTXVideo`（ced6bad，2026‑11‑12，37 个示例工作流）、`ModelTC/LightX2V`（c840dad，2026‑11‑20）、`city96/ComfyUI-GGUF`；读 60 余份官方 README / LICENSE / 文档与 HuggingFace 模型卡、文件清单（HF API，2026‑11‑21）。
> 下文来源缩写：〔T〕= workflow_templates 的 `templates/<名字>.json`（含模板便签）；〔C〕= ComfyUI 核心源码；〔KJ〕= WanVideoWrapper `example_workflows/`；〔LTX〕= Lightricks 的 ComfyUI‑LTXVideo / LTX‑2 仓库与 docs.ltx.io；〔LD〕= `Lightricks/LTX-Desktop` 的 `docs/hardware-compatibility.md`；〔LX〕= LightX2V 仓库与 `lightx2v/*` HF 仓库；〔5090L〕= `lifeidle/comfyui-5090-laptop-24gb-minimax-h3-qwen-image-wan2.2`（RTX 5090 **笔记本** 24 GB / 64 GB RAM / ComfyUI 0.43，服务端 `execution_start→success` 计时，2026‑11‑02 快照，作者自报）；〔4090D〕= 官方模板便签里的 RTX 4090D 24 GB 实测。**没有任何一条数字是本机实跑**；用户环境 Win11 + RTX 4090 24 GB，只能走 HuggingFace / GitHub。

## 本簇结论

1. **2026‑11 本地开源视频是「三主一辅」**：Wan 2.2 家族（Apache‑2.0，无声，衍生模型最多）、LTX‑2.3 / 2.5（22B，原生音画 + 原生多镜头 + IC‑LoRA 生态，社区许可）、MiniMax H3（本项目主线），辅以 HunyuanVideo 1.5（8.3B，轻但 24 GB 上 720p+SR 不可用〔5090L〕）。**Wan 开源线停在 2.2**：HF `Wan-AI` 在 2.2 之后只发了 Animate‑2（2026‑08）和 Dancer（2026‑07），2.5 / 2.6 / 2.7 / 3.0 都只有 API。
2. **ComfyUI 0.46 核心已原生支持几乎全部主流模型**（Wan 全家、LTX‑2.x、HunyuanVideo 1.5、Kandinsky 5、SCAIL‑2、Bernini‑R、InfiniteTalk、HuMo、WanMove / ATI、Causal Forcing、RelayVSR、SeedVR2、VOID、FILM / RIFE 插帧、Context Windows、Loop）。kijai 自己写的定位是「原生没有的才用 wrapper」〔KJ readme〕。
3. **主流做法高度收敛成 6 个模式**：① 蒸馏 4–8 步 + CFG 1 当默认档，原版 20–40 步当精修档；② Wan 2.2 用 high‑noise / low‑noise 双模型两段 `KSamplerAdvanced` 接力；③ LTX 用「半分辨率 8 步 → latent ×2 → 3 步」两段式；④ 长视频 = 定长窗口 + 重叠帧接力（Wan 81 帧 / LTX 97–145 帧 / H3 124 帧），不是一次生成；⑤ 参考 / 控制 / 编辑全部走 in‑context（VACE、IC‑LoRA、Animate、SCAIL‑2、Bernini‑R）；⑥ 口型 = 冻结音频条件（InfiniteTalk、LTX A2V、S2V）。
4. **谁做得最好**：参数基线看 Comfy‑Org 官方模板（带 4090D 实测便签）；新模型首发与长视频技巧看 kijai（WanVideoWrapper + KJNodes）；蒸馏 / 量化看 lightx2v；LTX 的两段式、DFR、分块续写和 24 GB 能跑什么，看 Lightricks 自己的工作流与 LTX‑Desktop 硬件文档；无限长看 SVI 2.0 Pro。
5. **对我们最有用的 5 件事**：
   - **H3 弱项替补表**（§7.3）：动作 / 换人 → Wan Animate 2、SCAIL‑2（驱动视频决定动作）；精确口型 → InfiniteTalk（I2V 或对现成片段 V2V 重配）与 LTX‑2.5 A2V；运镜 → Wan 2.2 Fun Camera 预设；>15 s 长镜头 → LTX‑2.5（单次 20 s）或 SVI 2.0 Pro；特效 → Wan‑Alpha 透明素材、VACE / Bernini‑R 局部编辑。
   - **段缝修复可以独立于生成模型**：`ComfyUI-Wan-VACE-Video-Joiner` 用 VACE 在任意来源片段之间重生成过渡帧，H3 段也能用。
   - **终处理链现成**：RelayVSR ×2（模板便签写明这对权重是 LightX2V 为「H3 生成之后那一步」重训的）+ 核心 `FrameInterpolate`（FILM / RIFE）。
   - **核心 `MiniMaxH3ContextWindows`（124 帧 / 重叠 39 / static_standard / pyramid）+ `split_conds_to_windows`** 是官方的 H3 超长方案，可与现有 Motion‑Context 路线对照测试。
   - **LTX 的工程约定可直接抄**：A2V「音频 latent 冻结 + 原波形直接封装」、多镜头提示词「每个切点写清转场、重建景别、复述身份、交代声音是否延续」、解码分块表。

## 一、模型全景（按「2026‑11 实际存在」核对）

> 核对口径：GitHub 组织仓库列表（搜索 API `org:`）、HF `author=` 列表、官方模板 `index.json` 的 `date / models / minComfyUIVersion / usage`。「24 GB 档文件」指官方模板默认引用的权重。

| 模型（发布） | 规模 / 24 GB 档文件 | 原生一次生成 | ComfyUI 支持 | 许可 | 备注 |
|---|---|---|---|---|---|
| **Wan 2.2 T2V / I2V A14B**（2025‑07） | MoE：high + low 两个 14B，各 14.29 GB fp8_scaled；`umt5_xxl_fp8_e4m3fn_scaled` 6.74 GB；`wan_2.1_vae` 0.25 GB | 81 帧 @16 fps ≈ 5 s，480p / 720p | 原生 `WanImageToVideo` / `WanFirstLastFrameToVideo`；模板 `video_wan2_2_14B_{t2v,i2v,flf2v}` | Apache‑2.0 | 官方默认：T2V shift 12 / 40 步 / 边界 0.875 / CFG (低 3.0, 高 4.0)；I2V shift 5 / 40 步 / 边界 0.900 / CFG 3.5（`wan/configs`） |
| Wan 2.2 TI2V‑5B | 10.00 GB fp16 + `wan2.2_vae` 1.41 GB（16×16×4 压缩） | 121 帧 @24 fps，1280×704 | 原生 `Wan22ImageToVideoLatent`；`video_wan2_2_5B_ti2v` | Apache‑2.0 | 与 14B **不共用 VAE**（48 通道 vs 16 通道，换错直接报错〔5090L〕） |
| Wan 2.2 S2V‑14B（2025‑08） | 16.39 GB fp8 | 77 帧 / 块，可无限接 | 原生 `WanSoundImageToVideo(+Extend)`；`video_wan2_2_14B_s2v` | Apache‑2.0 | 音频驱动；wav2vec2_large_english |
| Wan 2.2 Animate‑14B（2025‑09） | 18.41 GB int8_convrot / KJ fp8 | 77 帧 / 段 | 原生 `WanAnimateToVideo`；`video_wan2_2_14B_animate` | Apache‑2.0 | Move（动作迁移）/ Mix（换人，需姿态 + 人脸 + 遮罩） |
| **Wan‑Animate‑2**（2026‑08‑07） | `wan_animate_2_int8_convrot` 15.51 GB；另有蒸馏版 | 81 帧 / 段 | 原生 `WanAnimate2ToVideo` / `WanAnimate2Cache`；`video_wan_animate2(_distilled)`（需 ≥0.36 / 0.31） | Apache‑2.0 | 端到端：**不再抽姿态骨架**，直接吃驱动视频；背景与机位由文字控制 |
| Wan‑Dancer（2026‑07） | global + local 两个 14B fp8 | 149 帧一次采样 | 原生 `WanDancer*`；`video_wan_dancer` | Apache‑2.0 | 音乐→舞蹈；显存吃紧 |
| Wan 2.1（2025‑02）+ VACE / FLF2V / Fun | T2V / I2V 14B、1.3B；VACE 14B 32.29 GB fp16 | 81 帧 @16 fps | 原生 `WanVaceToVideo` 等 | Apache‑2.0 | 仍是大量衍生模型的底座（InfiniteTalk、SCAIL、ATI、WanMove、HuMo、Phantom…） |
| Wan 2.2 Fun Control / Inpaint / Camera / VACE（alibaba‑pai） | 各 high + low，14.3–17.35 GB ×2 | 81 帧 | 原生 `Wan22FunControlToVideo` / `WanFunInpaintToVideo` / `WanCameraImageToVideo` | Apache‑2.0 | 姿态 / 深度 / 边缘、首尾帧、9 种运镜预设 |
| Wan 2.5 / 2.6 / 2.7 / 3.0 | — | — | 仅 Partner（API）节点 | 闭源 | GitHub 上只有 API / 提示词仓库；HF `Wan-AI` 无权重 |
| **LTX‑2.5**（2026‑08‑12） | 22B；`ltx-2.5-22b-distilled-transformer-comfy-int8-convrot` 21.5 GB；Gemma 4 12B 文本编码器（社区报约占 14.6 GB 显存）；视频 VAE 有扩散解码器与卷积解码器两种 | 8n+1 帧；官方应用可选到 **20 s**；24 / 25 / 48 / 50 fps；原生到 4K（分块）；**同步音频 + 原生多镜头** | 原生 `LTXV*`；`video_ltx2_5_{t2v,i2v,flf2v,dfr_i2v}`（需 ≥0.32 / 0.37.2） | LTX‑2.x Community License（年营收 < 1000 万美元免费商用）；HF 仓库 gated | 只发蒸馏工作流为主；dev 版用于带 CFG / STG 的两段式 |
| LTX‑2.3（2026‑03） | 22B；dev fp8 29.1 GB；`gemma_3_12B_it_fp4_mixed` | 同上，模板默认 5 s，ia2v 9 s，ID‑LoRA 10 s | `video_ltx2_3_*`（最热：i2v 使用量 17173） | LTX‑2 Community License（同门槛） | IC‑LoRA 最全：Union Control、Motion Track、Dub‑It、Ingredients、In/Outpaint、HDR、Relight… |
| LTX‑2（2026‑01） | 19B | 同上 | `video_ltx2_*` | 同上 | 运镜 LoRA（dolly / jib / static）只有 19B 版 |
| **HunyuanVideo 1.5**（2025‑11） | 8.3B；480p / 720p 的 T2V / I2V 各一个 16.65 GB fp16；SR 蒸馏 720→1080 | 121 帧 @24 fps | 原生 `HunyuanVideo15*`；`video_hunyuan_video_1.5_720p_{t2v,i2v}` | Tencent Hunyuan Community（**不适用于欧盟 / 英国 / 韩国**；> 1 亿月活需另申请） | 480p I2V 有官方 8 / 12 步蒸馏；lightx2v 4 步 LoRA |
| HunyuanVideo‑Avatar / Custom / Foley（2025） | Avatar 最低 24 GB「很慢」；Foley XXL 20 GB（offload 12 GB） | — | Avatar / Custom 无原生；Foley 有社区节点 | 同上 | Foley：视频→48 kHz 音效 |
| SkyReels V2（2025‑04）/ **V3**（2026‑01） | V2 DF 1.3B / 14B；V3：R2V‑14B（1–4 张参考）、V2V 续写‑14B、A2V‑19B | V2 DF 自回归无限长；V3 续写 5–30 s 或「切镜续写」5 s | 仅 kijai wrapper（V2 DF 续写、V3 A2V 数字人） | skywork‑license（other） | V4 只有 API |
| Kandinsky 5（Lite 2B / Pro 19B） | Lite 4.57 GB | 121 帧 @24 fps，768×512 | 原生 `Kandinsky5ImageToVideo`；`video_kandinsky5_{t2v,i2v}` | MIT | 50 步 CFG 5，慢 |
| LongCat‑Video 13.6B（2025‑10）+ **Avatar 1.5 / 1.6**（2026‑05 / 2026‑11‑15） | TI2V 有 KJ fp8_scaled；Avatar‑1.5 bf16 31.7 GB + DMD 蒸馏 LoRA（Kijai HF） | 原生「视频续写」任务，分钟级 | 仅 kijai wrapper（TI2V 与 Avatar 示例） | MIT | Avatar 1.6 自称 > 10 分钟口播；1.6 的 ComfyUI 支持未验证 |
| SCAIL（2025‑12）/ **SCAIL‑2**（2026‑06） | SCAIL‑2 fp16 30.54 GB / int8 | 81 帧 / 段，重叠 5 | SCAIL‑2 原生 `WanSCAILToVideo` + SAM3.1；SCAIL 走 kijai | 代码 Apache‑2.0，权重 MIT | 动画 / 换人二合一 |
| **Bernini‑R**（ByteDance，2026‑06） | high + low 各 14.51 GB fp8 | 81 帧 @16 fps | 原生 `BerniniConditioning`；`video_bernini_r_{video,image}_editing` | Apache‑2.0 | Wan 2.2 底座的「渲染器」：v2v / 带参考编辑 / r2v / 广告植入 |
| InfiniteTalk（2025‑08）/ MultiTalk | 补丁 5.1 GB + Wan2.1 I2V 480p | 81 帧窗口，9 帧接力，无限长 | 原生 `WanInfiniteTalkToVideo`（I2V）；V2V 走 kijai | Apache‑2.0 | 稀疏帧视频配音，单人 / 双人 |
| HuMo（2025‑09） | 17B fp8 / 1.7B | 97 帧 @25 fps | 原生 `WanHuMoImageToVideo`；`video_humo` | Apache‑2.0 | 文 + 图 + 音三条件 |
| Ovi 1.1（2025‑11） | 视频 11.1 GB + 音频 12.2 GB（bf16） | 5 s / 10 s @24 fps，960² 面积 | 仅 kijai | Apache‑2.0 | Wan 2.2 5B + 5B 音频支路；H3 / LTX 已覆盖其用途 |
| MAGI‑1 4.5B / **MAGI‑1.1 24B**（2026‑06） | 4.5B 24 GB 可跑 | 自回归分块 | 仅官方自定义节点（2025‑05） | Apache‑2.0 | 未见核心支持 |
| FramePack（2025‑04，F1 2025‑05） | HunyuanVideo 1.0 13B 底座 | 最长 60 s @30 fps，6 GB 起 | kijai FramePackWrapper | Apache‑2.0 | 2025‑10 后无更新 |
| CogVideoX / Mochi | — | — | 核心仍留节点；VOID 抠除模型用 CogVideoX VAE | Apache‑2.0 | 官方模板库已没有它们的生成模板，跳过 |
| Causal Forcing / Capybara v0.1 / Helios / WanMove / ATI | — | Causal Forcing 4 步、模板上限 81 帧 | 原生（Helios 仅 diffusers） | 各自仓库 | 小众或研究性质 |

官方模板的「使用量」字段（`index.json` 的 `usage`，2026‑11‑21）给出了一个粗略的热度排序：H3 I2V 19766 > **LTX‑2.3 I2V 17173** > **Wan 2.2 14B I2V 8895** > H3 R2V 6582 > LTX‑2.5 I2V 4738 > H3 T2V 4089 > Pika H3 Flex Ref2VA 2717 > FastH3 I2V 2284 > Wan Animate 2 1603 > LTX‑2.5 T2V 1209 > LTX‑2.3 图 + 音→视频 1111 > LTX‑2.5 FLF2V 911 > SCAIL‑2 换人 872（+ int8 版 576）（此处略去了 Pika H3 Flex T2V 1342、FastH3 OmniRef 1296 两个 H3 变体；`usage` 字段含义官方未说明，只当相对热度看）。也就是说：**图生视频是绝对主流入口，Wan 2.2 I2V 与 LTX‑2.3 I2V 是 H3 之外真正被大量使用的两条线，换人 / 动作迁移是第二大需求。**

## 二、工作流图谱（5 条代表链路）

### 链路 A · Wan 2.2 14B 图生视频（无声 5 s 镜头，双采样器 + 4 步蒸馏）〔T `video_wan2_2_14B_i2v`〕

```
首帧图（生图 / 编辑模型出，16 的倍数）
  └─ LoadImage ─► WanImageToVideo(width, height, length=81, start_image)          # 4n+1 帧，16 fps
UNETLoader wan2.2_i2v_high_noise_14B_fp8_scaled ─► LoraLoaderModelOnly wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise (1.0) ─► ModelSamplingSD3 shift 5
UNETLoader wan2.2_i2v_low_noise_14B_fp8_scaled  ─► LoraLoaderModelOnly …_low_noise (1.0)                                   ─► ModelSamplingSD3 shift 5
CLIPLoader umt5_xxl_fp8_e4m3fn_scaled (type wan) ─► 正向 / 负向（官方中文负面词）
  ├─ KSamplerAdvanced #1（high）：add_noise=enable，steps 4，cfg 1，euler / simple，start 0 → end 2，return_with_leftover_noise=enable
  └─ KSamplerAdvanced #2（low） ：add_noise=disable，同 steps / cfg，start 2 → end 4
VAEDecode(wan_2.1_vae) ─► CreateVideo 16 fps ─► [FrameInterpolate ×2] ─► [RelayVSR ×2] ─► SaveVideo
```
- 方括号里的插帧与超分是本文建议的可选后处理，不在原模板里。精修档：同图关掉 LoRA，20 步、CFG 3.5、第 10 步交接（模板里用一个布尔开关切 5 个 `ComfySwitchNode`）。
- 〔4090D〕640×640×81 帧：fp8 20 步 ≈ 513–536 s；+ 4 步 LoRA 首跑 ≈ 97–108 s、二跑 ≈ 71 s；显存占用 83–89%。
- kijai 版〔KJ `wanvideo_2_2_I2V_A14B_example_WIP`〕：6 步、第 3 步交接、shift 8、`dpm++_sde`、BlockSwap 20、`lightx2v_I2V_14B_480p_cfg_step_distill_rank64` **高噪端强度 3 / 低噪端 1**，并用 `CreateCFGScheduleFloatList`（CFG 2，`start_percent 0 → end_percent 0.01`）只在采样最开头给 CFG——这是社区对付「蒸馏后动作变慢」的常见手法之一。

### 链路 B · LTX‑2.5 两段式音画同出（T2V / I2V，台词写进提示词）〔T `video_ltx2_5_i2v`；LTX `LTX-2.5_T2V_I2V_Two_Stage_Distilled`〕

```
提示词（一段话 150–220 词：景别 + 机位 + 运镜必写，台词放引号并注明语言 / 口音，声音写进同一段）
  └─ CLIPLoader gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot (type ltxv) ─► CLIPTextEncode ─► LTXVConditioning(frame_rate 24)
      [可选 TextGenerateLTX2Prompt + gemma4_e2b 做提示词增强，+1–2 min]
EmptyLTXVLatentVideo(半分辨率, 8n+1 帧) + LTXVEmptyLatentAudio ─► LTXVConcatAVLatent
  [I2V：LTXVPreprocess(18) ─► LTXVImgToVideoInplace(strength 0.7)]
阶段 1：UNETLoader ltx-2.5-22b-distilled-transformer-comfy-int8-convrot
        ManualSigmas "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"（8 步）+ euler_ancestral + LTXVDualCFGGuider(1, 1)
阶段 2：LTXVSeparateAVLatent ─► LTXVLatentUpsampler(ltx-2.5-latent-spatial-upscaler-x2) ─► [I2V 再贴一次首帧 strength 1.0]
        ManualSigmas "0.85, 0.7250, 0.4219, 0.0"（3 步）
VAEDecodeTiled(ltx-2.5-video-vae) + LTXVAudioVAEDecode ─► CreateVideo 24 fps ─► SaveVideo
```
- **DFR（Diffusion Fidelity Rendering）档**〔T `video_ltx2_5_dfr_i2v`〕：阶段 1 额外每秒放一个「生成关键帧」槽（121 帧 @24 fps → 24,48,72,96,120）与视频一起去噪；阶段 2 把半分辨率 latent 作为 IC‑LoRA 参考（`LTXVAddLatentGuide`）+ `ltx-2.5-22b-ic-lora-pixel-spatial-upscaler-x2` 跑 3 步；可选阶段 3 时间 ×2（121→241 帧、24→48 fps，4 步，关键帧以 0.95 强度作引导，音频只参与交叉注意力后丢弃）。便签自述「重复高频纹理和平滑渐变在运镜时会沸腾 / 分层，四种开关组合都一样，属于模型本身；宽银幕 + 缓运镜最稳，bf16 比 int8 干净」。
- 24 GB 关键坑：Gemma 4 12B 编码器约 14.6 GB，和 20–21.5 GB 的 DiT 同驻会触发动态换入（作者报 16 s / 步）；编码后先卸载编码器再采样（guillaume127/LTX‑2.5‑FP8 模型卡，4090 自报整条 ≈ 99 s，未给分辨率 / 时长）。

### 链路 C · 动作迁移 / 换人（Wan Animate 2，分段续接）〔T `video_wan_animate2`〕

```
角色参考图（背景无所谓）＋ 驱动视频（先重采样到 16–24 fps；景别要与参考图一致）
  └─ WanAnimate2ToVideo(832×480, length 81, pose_strength 1, reference_image_strength 1, continue_motion?, video_frame_offset)
提示词 text_1：「人物外观描述：…  背景描述：…」（只写长相与背景，不写动作）；text_2：一句动作描述（a person dancing）
UNETLoader wan_animate_2_int8_convrot ─► LoraLoaderModelOnly lightx2v_I2V_14B_480p_cfg_step_distill_rank64 (1.0) ─► ModelSamplingSD3 shift 5
  ─► ContextWindowsManual(context_length 21 latent, overlap 8, standard_static, pyramid)
SamplerCustom：lcm + BasicScheduler(simple, 6 步)，CFG 1 ─► TrimVideoLatent ─► VAEDecode ─► CreateVideo（模板按 30 fps 封装；帧与驱动视频 1:1 对应，不重采样）
续接：复制子图，上一段 IMAGE → 下一段 continue_motion，上一段 video_frame_offset → 下一段；相邻段重叠 1 帧，接缝卡一下就丢掉新段第一帧
```
- 蒸馏版模板：`wan_animate_2_distill_int8_convrot`，10 步、lcm、CFG 1。便签提示把 `WanAnimate2Cache` 设到 cpu 以免显存尖峰；「景别不匹配是坏结果的头号原因」。
- 同类：SCAIL‑2〔T `video_wan21_scail2_character_replacement`〕= SAM3.1 分别抠驱动视频与参考图里的人 → 彩色遮罩绑定身体部位 → `WanSCAILToVideo`（`replace_mode` true 换人 / false 动画），每段 81 帧、重叠 5、分段偏移 76×(index−1)，6 步（蒸馏 LoRA 0.8 + DPO LoRA 1.0，CFG 1）或 40 步 CFG 5；**不会自动循环，每段手动排队**。

### 链路 D · 音频驱动口型（InfiniteTalk；可对现成片段重配音）〔T `video_wan2_1_infinitetalk`；KJ `…InfiniteTalk_example_03` / `…V2V_InfiniteTalk_example_02`〕

```
配音 wav ─► [MelBandRoFormer 人声分离] ─► AudioEncoderLoader wav2vec2-chinese-base_fp16 ─► AudioEncoderEncode
定妆图（或已有视频） ─► WanInfiniteTalkToVideo(mode single / two_speakers, 832×480, length 81, motion_frame_count 9, audio_scale 1, [mask_1 / mask_2], [previous_frames])
UNETLoader Wan2_1-I2V-14B-480p_fp8_e4m3fn_scaled_KJ ＋ ModelPatchLoader wan2.1_infiniteTalk_{single,multi}_fp16 ＋ LoRA lightx2v_I2V_14B_480p_cfg_step_distill_rank64 (1.0)
SamplerCustomAdvanced：euler，BasicScheduler(normal, 6 步)，CFGGuider 1 ─► VAEDecode ─► CreateVideo 25 fps（原音轨直接封装）
加长：每复制一个 Video Extend 组 +81 帧（3.24 s），上一段 IMAGE → previous_frames
```
- 双人：对首帧在 MaskEditor 里分别给角色 1 / 2 画遮罩，各接一路音频。
- **V2V 重配音**（kijai）：`VHS_LoadVideo` 载入已有片段 → `WanVideoEncode` → `WanVideoImageToVideoMultiTalk(mode infinitetalk, 81 帧窗口, 9 帧接力)`，采样 4 步、shift 11、`dpm++_sde`、`start_step 2`（等于部分重绘）；便签：「音频比视频长时，从最后一帧继续延伸」。官方 README：音频 CFG 3–5 口型最准（挂加速 LoRA 后建议 2）；FusionX LoRA 超过 1 分钟会加剧偏色并降低身份保持；V2V 会模仿原片运镜但不完全一致。

### 链路 E · 长镜头接力（SVI 2.0 Pro on Wan 2.2 I2V）〔KJ `WanVideoSVIProEmbeds` / KJNodes `WanImageToVideoSVIPro`；vita‑epfl/Stable‑Video‑Infinity；Well‑Made/ComfyUI‑Wan‑SVI2Pro‑FLF〕

```
锚点图（首帧）─► VAE 编码 = anchor_samples（每一段都喂同一个）
第 k 段：WanVideoSVIProEmbeds(anchor_samples, prev_samples = 上一段 latent, motion_latent_count 1, num_frames 81)
        Wan 2.2 I2V high / low ＋ SVI_v2_PRO_Wan2.2-I2V-A14B_{HIGH,LOW}_lora_rank_128 ＋ 少量 lightx2v ─► 双采样器
        每段独立提示词、**每段换种子** ─► 解码 ─► ImageBatchExtendWithOverlap（对齐不准时调 overlap ±1–2）
```
- 源码层面：条件 latent = [锚点 latent, 上一段末尾 N 个 latent, 零填充]，遮罩只标第一帧——即「固定锚点保身份 + latent 尾巴续动作」。
- 官方置顶提示：不同段用不同种子；减少 lightx2v 用量、写足提示词、用 480p 可缓解慢动作。SVI2Pro‑FLF 再加「末帧硬锁」，可做首尾帧串联（附带工作流预置 7 段，不是上限）；续不上提示词时把段长加到 81–101 帧，或把 “starting to do X” 改成 “doing X”。

## 三、14 个通用工作流模式（各模型怎么实现 / 关键参数 / 坑）

### 3.1 文生视频（T2V）
- **Wan 2.2 14B**：`EmptyHunyuanLatentVideo(w, h, 81)` + T2V high / low；模板 shift 5、20 步 / CFG 3.5 / 第 10 步交接，或 `wan2.2_t2v_lightx2v_4steps_lora_v1.1_{high,low}_noise` 4 步 / CFG 1 / 第 2 步交接〔T〕。官方原始默认是 shift 12、40 步、CFG 高噪 4.0 / 低噪 3.0。
- **Wan 2.2 5B**：`Wan22ImageToVideoLatent` 不接 `start_image` 即 T2V；1280×704×121 帧 @24 fps，20 步 CFG 5 `uni_pc / simple` shift 8〔T〕。
- **LTX‑2.5 / 2.3**：同 I2V 图，开关切 T2V；模板带可选的提示词增强（`TextGenerateLTX2Prompt`，系统提示词写在核心 `nodes_textgen.py`）。
- **HunyuanVideo 1.5**：`DualCLIPLoader(qwen_2.5_vl_7b_fp8_scaled + byt5_small_glyphxl_fp16, type hunyuan_video_15)` → `EmptyHunyuanVideo15Latent(1280, 720, 121)` → 20 步 CFG 6 shift 7 euler〔T〕。**Kandinsky 5 Lite**：768×512×121，50 步 CFG 5 `euler_ancestral / beta`。
- 坑：CFG 1（蒸馏）时负面提示词不起作用，要排除东西用 NAG（核心 `nodes_nag.py`、kijai `WanVideoApplyNAG`、KJNodes `LTX2_NAG`）；T2V 只适合试风格——使用量数据里 T2V 比 I2V 低一个量级。

### 3.2 图生视频（I2V）
- **Wan 2.2**：`WanImageToVideo(start_image)`，2.2 的 I2V 模板不再加载 CLIP‑Vision；宽高 16 的倍数、帧数 4n+1。
- **LTX**：`LTXVPreprocess(img_compression 18)`（LTX‑2 模板用 33，2.3 FLF 用 25）→ `LTXVImgToVideoInplace`，阶段 1 strength 0.7、阶段 2 再贴一次 1.0〔T〕；官方工作流便签：首帧约束的强弱就靠 img_strength 与 img_compression 这两个值调。宽高 32 的倍数（LTX‑2 是 64）、帧数 8n+1；**参数不合法不会报错，而是静默取最近合法值**（模板便签）。
- **HunyuanVideo 1.5**：`HunyuanVideo15ImageToVideo` + `sigclip_vision_patch14_384`。
- **蒸馏后动作变慢 / 运镜变弱**（官方 FLF 模板便签原话：Lightning LoRA 会损失动态）的四种社区解法：① 高噪端 LoRA 强度 3（用的是 Wan 2.1 的 lightx2v I2V 480p LoRA）+ 采样开头 CFG 2〔KJ〕；② `princepainter/ComfyUI-PainterI2V`（★636，无许可证声明）用 `PainterI2V` 替换 `WanImageToVideo`，`motion_amplitude` 1.15 起；③ `VraethrDalkr/ComfyUI-TripleKSampler`（★107）三段：无 LoRA 的基础高噪（CFG 3.5）→ lightning 高噪 → lightning 低噪；④ `stduhpf/ComfyUI-WanMoeKSampler`（★249，GPL‑3.0）按信噪比 1:1 的时间步自动切模型，`boundary` T2V 0.875 / I2V 0.900。
- 坑：Wan 5B 与 14B 的 VAE 不通用；H3 是 17k+5 帧、24 fps，Wan 14B 是 16 fps——混剪前要统一帧率（§3.14）。

### 3.3 首尾帧（FLF2V）
- **Wan 2.2**：没有专用模型，直接用 I2V high / low + `WanFirstLastFrameToVideo(start_image, end_image)`；模板 640×640×81、shift 8、20 步 CFG 4 第 10 步交接，或 4 步 LoRA（shift 5）〔T `video_wan2_2_14B_flf2v`〕。Wan 2.1 另有专用 FLF2V‑14B‑720P；Fun Inpaint 版用 `WanFunInpaintToVideo`。
- **VACE 首尾帧**：把首 / 尾真帧放进控制序列、中间用占位帧并配遮罩（模板子图 `Wan VACE FLF2V Image Batch`）→ `WanVaceToVideo`；模板 20 步 CFG 6 `uni_pc`，或 lightx2v LoRA 0.8 + 6 步〔T `video_wan_vace_flf2v`〕。
- **LTX**：两个 `LTXVAddGuide`（frame_idx 0 与 −1，strength 0.7）→ 采样 → `LTXVCropGuides`〔T `video_ltx2_5_flf2v`〕。
- H3 对应 FL2VA，原生已解决；这里唯一值得搬的是「末帧硬锁 + 动作 latent 续接」的组合（SVI2Pro‑FLF）。

### 3.4 多关键帧
- **官方 `templates-6-key-frames`**：6 张图 → 5 个 FLF2V 子图（每段 720×720×25 帧、4 步 LoRA）→ `BatchImagesNode` 拼成一条。
- `wallen0322/ComfyUI-Wan22FMLF`（★576）：Wan 2.2 I2V 的首 / 中 / 尾三帧参考，`structural_repulsion_boost` 1.2–1.5 只作用于高噪阶段以增强运动而不偏色，并内置 SVI 模式。
- **LTX**：`LTXVAddGuide` 可在任意帧位多次添加（KJNodes 有 `LTXVAddGuideMulti`）；DFR 的「生成关键帧」是与视频同步去噪出来的细节关键帧，后续阶段拿它们当引导。
- **VACE**：任意位置真帧 + 遮罩（`stuttlepress/ComfyUI-Wan-VACE-Prep` 负责拼控制视频）。
- 坑：关键帧之间时长太短或光照 / 身份不一致会变成「溶解变形」；每段至少留 25 帧（Wan 16 fps 下约 1.5 s）。

### 3.5 视频续写与无限长
| 机制 | 代表实现 | 关键参数 | 代价 / 坑 |
|---|---|---|---|
| 采样内滑窗（Context Windows） | 核心 `WanContextWindowsManual`（81 帧 / 重叠 30 / uniform_standard / pyramid / freenoise）、`LTXVContextWindows`（145 / 40）、`MiniMaxH3ContextWindows`（124 / 39 / static_standard）；kijai `WanVideoContextOptions`（81 / stride 4 / overlap 16） | `retain_first_frame`（I2V 首帧在每个窗口保留）、`split_conds_to_windows`（`ConditioningCombine` 的多条提示词按窗口分配） | kijai 自测 1.3B T2V 1025 帧 < 5 GB、5090 上 10 min；I2V 首帧只锚第一个窗口，后段漂 |
| 多帧接力（motion frames） | InfiniteTalk 9 帧；Wan Animate `continue_motion_max_frames` 5；SCAIL‑2 重叠 5；Animate 2 重叠 1；LongCat 13；SkyReels DF 17；LTX 官方 CLI 分块 `--chunk-pixel-frames 97` / `--chunk-carry-frames 25`（LTX‑Desktop 里 T2V / I2V 的 carry 是 17、IC‑LoRA 是 25）；`LTXVLoopingSampler` tile 80 / overlap 24 + `MultiPromptProvider` | 像素拼接用 KJNodes `ImageBatchExtendWithOverlap(overlap, crossfade)` | 重叠区要算两遍：41 帧窗口 + 17 帧 carry 时每窗只新增 24 帧，20 s 要 20 个窗口〔LD〕 |
| latent 续接 + 固定锚点 | SVI 2.0 Pro（锚点 latent + 上段尾 latent；原生图用 KJNodes `WanImageToVideoSVIPro`，wrapper 用 `WanVideoSVIProEmbeds`）；Pusa（逐帧噪声 `flowmatch_pusa`）；FramePack；SkyReels V2 Diffusion Forcing | 每段换种子；锚点始终是首帧 | 慢动作、提示词要「正在做」而不是「开始做」 |
| 模型原生续写 | LongCat‑Video（预训练任务就是续写）、SkyReels V3 V2V（单镜续 5–30 s / 切镜续 5 s）、LTX Retake / Extend | — | LTX 官方：4090 上一次 1080p 续写上限约 5–6 s〔LD〕 |
| 段间过渡重生成 | `ComfyUI-Wan-VACE-Video-Joiner`（Wan 2.1 VACE 或 Wan 2.2 Fun VACE） | 每个接缝排队一次；素材降到 16 fps 处理 | VACE 会带亮度 / 饱和偏移；作者的缓解办法是处理后插帧到 30 / 60 fps |
- 共性坑：亮度 / 颜色逐段漂移（VACE、InfiniteTalk + FusionX 超 1 分钟、MultiTalk 建议音频 CFG 3 + APG）；LTX 官方原话——纯 T2V / I2V 分块「像传话游戏」会漂，**带 IC‑LoRA 引导视频时几乎无损，因为引导视频锚住了每个窗口**〔LD〕。这与我们对 H3「续接链 ≤ 4 段」的结论同向。

### 3.6 参考主体一致
- **Wan 系**：VACE 参考图（`WanVaceToVideo.reference_image`，参考帧由 `TrimVideoLatent` 裁掉）；Phantom（核心 `WanPhantomSubjectToVideo(images)`；kijai 示例 8 步、shift 5、lightx2v T2V 0.8，「480p 训练也能 720p，24 fps」）；MAGREF（I2V 式任意参考）；Stand‑In（人脸 ID 的特殊 LoRA，**必须直连模型加载器**，脸抠到白底 512²，已有 Wan 2.2 T2V high / low 版）；Lynx（人脸 IP 适配器，kijai 建议用 lite ip 层并降低 ref 层强度；裁脸用的 InsightFace buffalo 模型是非商用）；Bernini‑R 的 r2v / rv2v（训练时约 5 路参考可靠，节点留 8 槽，提示词里按 image0、image1… 指代）；SkyReels V3 R2V（1–4 张）。
- **LTX 系**：官方 **Ingredients IC‑LoRA**（一张「参考表」：每个角色脸特写 + 全身转面、每个道具产品图、一个场景面板，**黑底无文字**；循环成 ≥121 帧静态视频作引导；提示词分两段 `Reference sheet: … / Generated video: …`；2.3 版模型卡推荐强度 1.4、30 步、CFG 4、768×448×121 @24；面板越大迁移越准）；社区 `liconstudio/ComfyUI-LTX2.5-MSR`（≤5 路：pic1–pic4 + background，新版可配两路参考音频）；ID‑LoRA（脸 + 声音，`LTXVReferenceAudio`）。
- 对照：H3 Ref2VA 原生 9 图 + 3 视频 + 3 音频，是这一项里能力最强的；别家基本是「1–5 张图」或「一张拼表」。**Ingredients 的参考表版式（黑底、一元素一面板、无文字）与我们「一职责一张图」的规则互证。**

### 3.7 姿态 / 深度 / 边缘控制与运镜控制
- **Wan 2.2 Fun Control**：`Wan22FunControlToVideo(ref_image, control_video)`；预处理用官方工具模板 `utility-openpose-video`（DWPose）、`utility_sdpose_*`、`utility_depth_anything3_video_depth_estimation`、`utility-lineart-video`、`utility-normal_crafter-video`。
- **LTX IC‑LoRA Union Control**：一个 LoRA 同时吃深度 / 姿态 / 边缘，在下采样 latent 上工作（`ref0.5`）；`LTXICLoRALoaderModelOnly` + `LTXAddVideoICLoRAGuide`，阶段 1 后 `LTXVCropGuides` 去掉引导帧〔LTX `LTX-2.5_ICLoRA_Union_Control_Distilled`，该示例加载的仍是 2.3 的 union LoRA 文件〕。另有 Motion‑Track、Layout‑To‑Render（2.5）。
- **运镜**：`WanCameraEmbedding`（Static / Pan Up·Down·Left·Right / Zoom In·Out / 顺逆时针，带 speed）→ `WanCameraImageToVideo` + Fun Camera high / low〔T `video_wan2_2_14B_fun_camera`〕；轨迹控制 ATI（`WanTrackToVideo`）、WanMove；kijai wrapper 里的 Uni3C / ReCamMaster（对已有视频改机位）；LTX‑2 19B 有 dolly in / out / left / right、jib up / down、static 七个运镜 LoRA。
- 坑：控制视频要先对齐到模型帧率（Wan 16 fps）与 16 / 32 倍数分辨率；姿态类对景别极敏感。

### 3.8 视频转绘与换人
- **换人 / 动作迁移**：Wan 2.2 Animate（姿态 ViTPose + 人脸 + SAM2 遮罩 + `WanAnimate_relight_lora`，6 步 CFG 1 shift 8）；Wan‑Animate‑2（免预处理）；SCAIL‑2（SAM3.1 彩色遮罩）；MoCha（无结构引导，首帧 SAM2 遮罩 + 1–2 张参考；kijai 便签：输入尺寸等于翻倍，要 BlockSwap 40；**权重 AGPL‑3.0**）。
- **编辑**：Bernini‑R（v2v / 带参考换装 rv2v / 广告植入 ads2v；Turbo 档 6 步 = 高噪 LoRA 3.0 + 低噪 1.5、3 / 3 交接、CFG 1；原始档 40 步 CFG 5，官方 Python 里还有 APG）；VACE 遮罩重绘 / 外扩 / 转绘；LTX 的 V2V IC‑LoRA 族（去字幕、去水印、去物体、修复老片、外扩、日转夜、Alpha‑Gen 抠像、Clean‑Plate）；VOID 物体移除（两遍各 30 步 CFG 6，连物理影响一起抹）。
- 共性：全部按 81 帧（或 8n+1）分段，长片靠手动复制子图或核心 Loop 节点。

### 3.9 口型与数字人（音频驱动）
| 方案 | 输入 | 关键参数 | 备注 |
|---|---|---|---|
| InfiniteTalk（原生 + kijai） | 图或视频 + 音频（单 / 双人） | 81 帧窗口、9 帧接力、25 fps、6 步 CFG 1；`wav2vec2-chinese-base` | 嘴、头、身体、表情一起对；可 V2V 重配现成片段 |
| MultiTalk | 图 + 多路音频 | 81 帧 @25 fps 训练，最多 201 帧；10 步也不伤口型 | 被 InfiniteTalk 取代，口型精度官方称后者更高 |
| Wan 2.2 S2V | 图 + 音频（+ 可选姿态视频） | 每块 77 帧（至少 73），批数 = Extend 子图数 + 1；4 步 CFG 1（T2V lightning LoRA）或 20 步 CFG 6 `uni_pc` | 模板自带「首帧过曝」补丁：首帧加倍、解码后删 |
| LTX‑2.5 A2V / 2.3 ia2v | 图 + 音频 | 音频经 `LTXVAudioVAEEncode` 后**冻结**（noise mask 0），两阶段都不加噪；**输出封装原始波形，不从 latent 解码** | 与 H3 的音频锁定同理 |
| LTX‑2.3 Dub‑It IC‑LoRA | 现成视频 + 新台词文字 | 两阶段，阶段 2 冻结音频；提示词模板 `[Speaker] is speaking [Language], saying: "…"` | 官方只验证了英 / 法 / 西 / 德 / 俄；单说话人；台词要用目标语言文字写全 |
| HuMo | 文 + 图 + 音 | 97 帧 @25 fps；6 步 CFG 1 `uni_pc` + lightx2v I2V LoRA | 超 97 帧质量下降 |
| SkyReels V3 A2V（kijai） | 图 + 音频（≤200 s） | `flowmatch_distill` 4 步 shift 5；先跑一段普通 I2V 当参考帧 | 19B，BlockSwap 30 |
| LongCat‑Avatar 1.5 / 1.6 | 图 / 文 + 单 / 多路音频 | 1.5 起用 Whisper‑large，8 步蒸馏 | 1.6（2026‑11‑15）自称 > 10 分钟；ComfyUI 侧未验证 |

### 3.10 原生音频与配音
- **音画同生**只有三家可本地跑：H3、LTX‑2.x（台词放引号、注明语言 / 口音；2.3 模型卡承认「无语音时音频质量偏低」）、Ovi（台词 `<S>…<E>`，音效 `Audio: …` 放在提示词末尾）。Wan / HunyuanVideo 全系无声。
- **纯音频 / 后配**：LTX 的 `LTXVAudioOnlyModel` 可单独文生音频；`LTX-2.3-22b-LoRA-Foley-V2A` 给视频配音效；HunyuanVideo‑Foley（48 kHz，XXL 20 GB / XL 16 GB，offload 后 12 / 8 GB）；kijai/ComfyUI‑MMAudio（★580）。官方音频模板还有 Chatterbox（克隆 / 多说话人对话）、ACE‑Step 1.5、Stable Audio 3、MiniMax Music 3、MelBandRoFormer 人声分离——细节归 04 簇。

### 3.11 步数蒸馏与双采样器
| 模型 | 蒸馏件 | 步数 / CFG / 其它 | 来源 |
|---|---|---|---|
| Wan 2.2 I2V / T2V 14B | `wan2.2_{i2v,t2v}_lightx2v_4steps_lora_v1(.1)_{high,low}_noise`（Comfy 重打包）；lightx2v 官方 `…_lora_rank64_lightx2v_4step_1022`（I2V）/ `_1217`（T2V）；720p 版 `…_4step_720p_260412`（原件 57 GB，Kijai 抽成 rank64 / 256 LoRA） | 4 步 = 高 2 + 低 2，shift 5，CFG 关；`denoising_step_list [1000, 750, 500, 250]` | 〔T〕〔LX `configs/distill/wan22`〕 |
| 沿用 Wan 2.1 蒸馏 LoRA 的模型（VACE、Animate、Animate 2、InfiniteTalk、SCAIL‑2、HuMo、WanMove，以及 Wan 2.2 底座的 Bernini‑R / Dancer） | `lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16` / `lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16` | 4–8 步、CFG 1、强度 0.8–1.0（Bernini / Dancer 高噪端用到 3.0） | 〔T〕〔KJ〕 |
| 旧件 | CausVid LoRA（强度 0.3–0.4、3–4 步 `uni_pc`）；FusionX、rCM、FastWan | CausVid 只在 2025 年的 VACE 模板里还在用；其余见 Kijai HF 与各项目 README | 〔T `video_wan_vace_*`〕 |
| LTX‑2.5 / 2.3 | 蒸馏 transformer，或 dev + `distilled-lora`（2.3 模板强度 0.5） | 固定 sigma 表 8 步 + 放大后 3 步，CFG 1；「步数和 sigma 是配方的一部分，改了画风就变」 | 〔T〕 |
| LTX‑2 dev | — | `LTXVScheduler(20, 2.05, 0.95)` CFG 4 + 阶段 2 蒸馏 LoRA 3 步 | 〔T `video_ltx2_i2v`〕 |
| HunyuanVideo 1.5 | 480p I2V 官方步数蒸馏；lightx2v 4 步 LoRA；SR 蒸馏 | 8 / 12 步 shift 7 CFG 1；SR 720→1080 8 步 shift 2 | 官方 README |
| Wan‑Animate‑2 | 官方蒸馏权重 | 10 步 CFG 1 lcm | 〔T〕 |
- 通用规律：蒸馏件必须与「模型（T2V / I2V）× 噪声段（high / low）× 分辨率档」逐一对应；不叠两个蒸馏；CFG 固定 1；代价是动作幅度与运镜（Wan）、提示词遵循（〔5090L〕老 LTX‑Video 2B 蒸馏在 CFG 1 / 8 步下完全不跟随提示词）。这与 H3「4 步 Turbo 抹掉运镜」同构。

### 3.12 低显存（24 GB 视角）
- **量化格式四分法**〔5090L §2.2〕：GGUF / NF4 只压权重（省内存、不提速甚至更慢）；INT8 + ConvRot 是 Comfy‑Org 新模型默认（Animate 2、SCAIL‑2、LTX‑2.5、H3）；fp8_scaled 是 Wan 2.2 默认；NVFP4 只有 RTX 50 系（Blackwell）有原生加速——**4090 上选 int8_convrot 或 fp8，不选 nvfp4**。
- **Wan 2.2 14B 能在 24 GB 跑的原因**：双专家合计 28.6 GB，但每步只驻留一个（各 14.3 GB）。
- **GGUF**（`city96/ComfyUI-GGUF`，★4283）：`Unet Loader (GGUF)` 替换 `Load Diffusion Model`；Wan 2.2 I2V Q4_K_M 9.65 GB×2、Q8_0 15.41 GB×2（QuantStack）；LTX‑2.5 蒸馏版 Unsloth `UD-Q4_K_XL` 14 GB（awesome‑ltx2 推荐）、Q8_0 22.78 GB。4090 上只有「DiT + 文本编码器 + 参考编码放不下」时才值得换。
- **kijai wrapper**：`WanVideoBlockSwap`（40 块里换出 20–40 块；未合并的 LoRA 会跟块走，1 GB LoRA 约需多换 2 块）、`WanVideoVRAMManagement`、`fp16_fast`（约 +20%）、SageAttention（便签称「接近翻倍」）、`WanVideoTorchCompileSettings`（Triton 约 +30%；**Windows 上更新后首跑显存暴涨时清 `C:\Users\<用户>\.triton` 与 `AppData\Local\Temp\torchinductor_<用户>`**）；便签警告 `fp8_fast` 画质明显变差。
- **LTX**：先编码文本再卸载编码器；`low_vram_loaders.py`；`--reserve-vram 5`；`VAEDecodeTiled`（官方给了 512/64/128/32 到 1536/384/192/48 的分块表）；KJNodes `LTXVChunkFeedForward`。
- **通用**：每次提交前 `POST /free {"unload_models": true, "free_memory": true}`（返回空 body）；VAE 解码是最后一步的瞬时峰值，用分块解码〔5090L §7.2〕。

### 3.13 两段式放大精修
- **latent 放大 + 少步重采样**：LTX（`LTXVLatentUpsampler` ×2 或 ×1.5 → 3 步）；HunyuanVideo 1.5（`HunyuanVideo15LatentUpscaleWithModel` → 1080p SR 蒸馏 8 步、`HunyuanVideo15SuperResolution` 噪声增强 0.7；〔5090L〕24 GB 上跑满 70 分钟未完成）；H3 的 LBH 二采属于同一类。
- **低噪专家当精修器**：官方 `utility_video_upscale` = lanczos 放大 → 分块编码 → `Wan2_2-T2V-A14B-LOW` + lightx2v T2V LoRA 0.7 → **4 步、denoise 0.25、shift 5**、提示词只写 `high resolution, sharp, detailed` → 分块解码；单次最多 121 帧。任何模型的成片都能过这一遍。
- **IC‑LoRA 生成式放大**：LTX `pixel-spatial-upscaler` ×2 / ×4（先 ~280p 定构图与运动再放大）；4K / 8K 用 `LTXVTiledFusionSampler`（**提示词只写质感与调色，不写具体物体，否则每个 tile 都会长出来**）。
- **像素超分**：RelayVSR ×2 / ×4（1 步；大模型每 15 帧写一个关键帧参考、Flash 解码器铺到每帧；帧率与音轨原样带出；需 ComfyUI ≥ 0.45）；SeedVR2 3B int8（核心原生，1 步）/ 7B（numz 节点 ★3004）；FlashVSR（kijai 版自述「未实现稀疏注意力与流式，结果与原版不一致」）；RTX Video（超分 + 插帧 + SDR→HDR 一条链，需 ≥ 0.40）。

### 3.14 插帧
- **核心原生**：`FrameInterpolationModelLoader` + `FrameInterpolate(multiplier)`，权重放 `models/frame_interpolation/`：`film_net_fp16`（65.7 MB）或 `rife_v4.25 / v4.26(_heavy / _lite)`，来自 HF `Comfy-Org/frame_interpolation`〔T `utility_video_frame_interpolation`〕。
- GIMM‑VFI（kijai，`gimmvfi_r_arb_lpips_fp32`，模板插 3 倍）；`Fannovel16/ComfyUI-Frame-Interpolation`（★1095，MIT；RIFE 4.0–4.9、FILM、GMFSS、AMT 等，`clear_cache_after_n_frames` 防 OOM）；LTX 的 latent 时间放大器（24→48 fps）。
- 帧率换算：Wan 14B 出 16 fps，要并进 24 fps 时间线可 ×3 到 48 fps 再隔帧取（算术推导，未实测画面）；Animate / SCAIL / InfiniteTalk 模板直接按 30 / 25 fps 封装，混剪前用 `VHS_LoadVideo.force_rate` 或 ffmpeg 统一。

## 四、逐项目 / 逐工具

### 4.1 Comfy‑Org/workflow_templates（官方模板库，MIT，v0.11.114，2026‑11‑21）
- **定位**：ComfyUI「模板」面板的数据源，也是每个模型的**官方参数基线**。777 个工作流 JSON；`index.json` 的 Video 分类 229 个（139 个是 API / 闭源，**90 个本地开源**）、Video Tools 59 个（26 个本地）；以 `video_` 命名的本地模板 71 个（其中 12 个是 H3 系：H3 6、Pika H3 Flex 3、FastH3 3）。
- **机制**：新模板大多用**子图**封装「加载 → 条件 → 采样 → 解码」，外层只露提示词 / 尺寸 / 时长 / 蒸馏开关；节点参数在 `definitions.subgraphs[].nodes[].widgets_values` 里，解析时必须下钻一层。便签里通常有模型链接（HF + ModelScope 镜像）与存放目录树；最低 ComfyUI 版本写在 `index.json`。
- **关键信息**：`index.json` 每条带 `date / models / minComfyUIVersion / size / usage`——可直接当「这个模型何时进核心、要多大盘、有多少人用」的事实表。Wan 2.2 系模板带 4090D 实测便签。
- **坑**：〔5090L §9.4〕把模板转 API 格式时，种子后面的 `control_after_generate` 伪 widget 要占一个槽位，否则参数整体错位（`steps` 变成 `"randomize"`）；子图边界连线要按 `linkIds` 接回内层。
- **对 4090 短剧的价值**：换任何新模型先抄模板参数，再做自己的 A/B；RelayVSR、插帧、SeedVR2、深度 / 姿态预处理这些工具模板可直接接在 H3 成片后面。
- **硬件与速度**：模板本身不保证能在 24 GB 上跑——`index.json` 的 `size` 是全部模型文件之和（Wan 2.2 14B I2V 38 GB、LTX‑2.5 I2V 56.9 GB、H3 I2V 44.5 GB），不是显存；带实测便签的只有 Wan 2.2 14B 系、ATI、VACE。
- **许可**：仓库 MIT；模板引用的每个模型另有各自许可（见 §6）。
- **评级：采用**（作为参数与文件名的唯一基准）。

### 4.2 Wan‑Video/Wan2.2（★18807，Apache‑2.0，最后推送 2026‑09‑21）与 Wan2.1（★17470）
- **定位**：开源视频生态的事实底座。2.2 的新东西是 MoE（高噪 / 低噪两个 14B 专家）与 5B 高压缩 TI2V；此后官方只开源了 S2V、Animate、Animate‑2、Dancer。
- **机制与官方参数**：按时间步边界切换专家（T2V 0.875、I2V 0.900）；官方默认 40 步、无蒸馏；负面提示词是一段固定中文。ComfyUI 模板把它简化成「20 步、第 10 步交接」。
- **硬件与速度**：官方脚本 14B 720p 标称「至少 80 GB」（OOM 时再加 `--offload_model / --convert_model_dtype / --t5_cpu`）；5B 标称 24 GB 4090 可跑。ComfyUI 里靠 fp8_scaled + 每步只驻留一个专家：〔4090D〕640×640×81 帧 20 步 513–536 s，4 步 LoRA 71–108 s；〔5090L〕832×480×81 帧 4 步 93.8 s；5B 1280×704×121 帧 20 步 355 s。
- **ComfyUI 模板参数**：I2V / T2V shift 5，FLF2V / Fun 系 shift 8；20 步 CFG 3.5（FLF2V 为 4）第 10 步交接，或 4 步 CFG 1 第 2 步交接；euler / simple；默认 640×640×81 帧「给低显存用户」，可自行加到 832×480 / 1280×720。
- **短板**：16 fps、单次约 5 s、无声、无原生多镜头；4 步蒸馏损失动态（官方模板便签自认）。
- **对 4090 短剧的价值**：H3 做不好的**无对白镜头**的第一替补——动作、特效元素、首尾帧过渡、可控运镜；全系 Apache‑2.0，商用最干净。
- **许可**：权重与代码 Apache‑2.0，官方声明不对生成内容主张权利。
- **评级：采用**（14B I2V / FLF2V + lightx2v 4 步作草稿，20 步或三段采样作定稿）；5B **观望**（最慢的一档，除非需要原生 24 fps 720p）。

### 4.3 Wan‑Animate‑2（★387）/ Wan 2.2 Animate / zai‑org SCAIL‑2（★1336）—— 动作迁移与换人
- **定位**：「参考图里的人 × 驱动视频里的动作」。Animate‑2（2026‑08）去掉了姿态 / 人脸预处理，背景与机位改由文字决定；Wan 官方模型里只有 Animate v1 带「保留原视频背景的换人（Mix）」；SCAIL‑2 用彩色遮罩把参考图与驱动视频的身体部位对应起来（`SCAIL2ColoredMask` 按 left_to_right 排序，多人场景未实测）。
- **机制**：Animate‑2 的驱动视频经 VAE 成 pose latent，逐帧给 DiT 提供 K / V；参考图 latent 负责身份〔T 便签〕。官方推理要求先用 LLM 把参考图写成「人物外观描述 + 背景描述」的固定句式（README 给了中文模板）。
- **关键参数**：见链路 C。官方仓库默认配置按 8×A800 跑 720p；ComfyUI 模板默认 832×480、81 帧一段。
- **硬件与速度**：Animate‑2 的 DiT 是 15.5 GB 的 int8_convrot 单文件。〔5090L〕自报 Animate 线 Move 105 s（832×480 / 77 帧 / 4 步）、Mix 155 s（640×640 / 77 帧 / 6 步）——该文所用 18.41 GB 权重对应的是 Animate v1 的 int8，口径存疑。
- **许可**：Animate / Animate‑2 Apache‑2.0；SCAIL‑2 权重 MIT。
- **对 4090 短剧的价值**：**打斗、舞蹈、复杂肢体动作**——自己拍一段（或找一段）驱动视频，就能绕开 H3「动作偏慢」；换人可把实拍 / 素材片里的演员换成角色卡。
- **坑**：景别不匹配是头号失败原因；驱动视频按帧 1:1 读取、不重采样；`WanAnimate2Cache` 放 cpu 防显存尖峰；SCAIL‑2 模板依赖 ComfyUI PR #14373 之后的核心，且不会自动循环分段；社区 `wuwukaka/ComfyUI-WanAnimatePlus`（★427）给 Animate / SCAIL‑2 / Animate‑2 加了多参考图（`prefix_frames` 1–5 张）与取上一段末 21 帧的无缝续接。
- **评级：试用**（Animate‑2 优先；要保留原背景用 Animate v1 或 SCAIL‑2 替换模式）。

### 4.4 kijai/ComfyUI‑WanVideoWrapper（★6823，Apache‑2.0，最后推送 2026‑11‑13）
- **定位**：Wan 系新模型的「首发试验田」。作者明说：原生有的就别用 wrapper；它的价值是原生还没有的模型与技巧。
- **覆盖**（README + 44 个示例）：SkyReels V2 DF / V3 A2V、Fun、ReCamMaster、VACE、Phantom、ATI、Uni3C、MiniMaxRemover、MAGREF、FantasyTalking / FantasyPortrait、MultiTalk / InfiniteTalk（含 V2V）、EchoShot（多镜头，1.3B）、Stand‑In、HuMo、WanAnimate、Lynx、MoCha、UniLumos、Bindweave、TimeToMove、SteadyDancer、One‑to‑All、SCAIL、LongCat‑Video / Avatar、Ovi、FlashVSR、Pusa、SVI Pro、StoryMem、LucyEdit。
- **机制**：自带加载器 / 采样器（`WanVideoModelLoader → WanVideoSampler`，调度器含 `dpm++_sde / unipc / lcm / flowmatch_distill / flowmatch_pusa / longcat_distill_euler`），与原生 MODEL 类型不互通（文本编码可借原生）；显存靠 `WanVideoBlockSwap` + torch.compile + SageAttention。
- **示例里的通用配方**：蒸馏 LoRA + 4–8 步 + CFG 1 + shift 5–11；长视频要么 `WanVideoContextOptions`，要么模型自带的窗口循环（「窗口间要重新编码，所以结果已解码、不存 latent」）。
- **坑**：新账号被禁止提 issue；每次更新后 Windows 上 torch.compile 可能首跑显存暴涨（清 Triton 缓存）；GGUF 的 MultiTalk 不能与非 GGUF 主模型混用。
- **硬件与速度**：作者早期自测 512×512×81 帧约 16 GB（40 块里 offload 20 块）；滑窗 1025 帧的 1.3B T2V 不到 5 GB、5090 上 10 分钟；其余示例不带耗时。
- **许可**：Apache‑2.0（所封装的各模型许可各异，见 §6）。
- **对 4090 短剧的价值**：InfiniteTalk V2V、SVI Pro、MoCha 等「原生没有」的能力只能从这里拿；示例工作流的便签是这些模型最可靠的参数出处。
- **评级：采用**（限定用途：InfiniteTalk V2V、SVI Pro、MoCha / Stand‑In / Lynx、SkyReels、LongCat、Ovi）。

### 4.5 kijai/ComfyUI‑KJNodes（★3482，GPL‑3.0，最后推送 2026‑11‑18）
- **定位**：视频工作流的通用工具箱；官方模板自己也在用（`ImageResizeKJv2`、`VAELoaderKJ`、`ImageBatchExtendWithOverlap`），H3 流水线里的 SageAttention 补丁也出自它。文档基本只在节点描述与 tooltip 里。
- **与本簇相关的节点**（节点名用 2026‑10‑31 的克隆核对）：
  - `ImageBatchExtendWithOverlap(source_images, overlap=13, overlap_side source / new_images, overlap_mode cut / linear_blend / ease_in_out / filmic_crossfade / perceptual_crossfade, new_images)`——先用一份取出续写起始帧，再用另一份把新段按重叠拼回去；LongCat、LTX‑2 A2V、SVI 工作流都靠它拼段。
  - `WanImageToVideoSVIPro(length 81, anchor_samples, prev_samples, motion_latent_count 1)`——原生图里的 SVI 续接条件节点。
  - `GetImageRangeFromBatch`（取尾帧 / 尾段）、`ColorMatch`（段间校色）、`ImageResizeKJv2`（`divisible_by` 16 / 32 对齐网格）。
  - LTX 系：`LTX2_NAG`、`LTXVAddGuideMulti`、`LTXVChunkFeedForward`、`LTXVAudioVideoMask`、`LTXVImgToVideoInplaceKJ`、`VAELoaderKJ`。
- **硬件与速度**：纯工具节点，不单独占显存；`LTXVChunkFeedForward(chunks, dim_threshold 4096)` 把前馈激活分块以压低峰值显存（节点自述「实验性，可能改变输出」）；`LTX2_NAG` 默认 `nag_scale 11 / alpha 0.25 / tau 2.5`，可分别给视频和音频接负向条件。
- **许可**：GPL‑3.0（只调用不分发则无碍）。
- **对 4090 短剧的价值**：分段拼接、尾帧提取、网格对齐、校色这几件事不必再写脚本；2026‑03‑19 起 Set / Get 节点重写，旧工作流可能要重连。
- **评级：采用**（已在用；新增关注 `ImageBatchExtendWithOverlap` 与 `ColorMatch`）。

### 4.6 ModelTC/LightX2V（★3015，Apache‑2.0，最后推送 2026‑11‑20）与 `lightx2v/*` HF 仓库
- **定位**：推理框架 + 蒸馏 / 量化权重的最大来源（H3 Turbo LoRA 也是它出的）。支持 Wan 2.1 / 2.2（含 VACE、S2V、Animate、Animate‑2 蒸馏、Dancer）、LTX‑2 / 2.3 / 2.5、HunyuanVideo 1.5、InfiniteTalk、Self‑Forcing、SeedVR2、RelayVSR 等。
- **机制（框架侧）**：少步推理（DMD2、MeanFlow）；W8A8（INT8 / FP8）与 W4A4（NVFP4）量化；磁盘‑CPU‑GPU 分层 offload（可到 block 级）；TeaCache / MagCache / TaylorSeer 缓存；TP / SP / CFG 并行；变分辨率推理。ComfyUI 侧是「服务模式」节点（`lightx2v_comfyui/`：`LightX2V Service → Generate Video / Regenerate Video / Upscale Video`），模型常驻在独立进程里。
- **关键参数**（`configs/distill/wan22/`）：`infer_steps 4`、`distill_method dmd2`、`sample_shift 5.0`、`enable_cfg false`、`boundary_step_index 2`、`denoising_step_list [1000, 750, 500, 250]`；4090 预设 `wan_moe_i2v_distill_4090.json` = DiT 与 T5 都用 fp8、block 级 CPU offload、sage_attn2、默认 720×1280×81 帧。
- **对我们有用的是权重而不是框架**：`lightx2v/Wan2.2-Distill-Loras`（I2V `…_1022`、T2V `…_1217`，各 0.6–0.7 GB）、`Wan2.2-Distill-Models`（整模型 fp8 / int8 各约 15 GB，另有 ComfyUI 版；2026‑04‑12 的 720p 版只有 57 GB 原件，Kijai HF 有抽出的 rank64 / 256 LoRA）、`Wan2.2-Lightning`（Seko 系列）、`Hy1.5-Distill-Models`。
- **硬件与速度**：模型卡称用自家框架「约比 ComfyUI 快 2 倍」；`LightWan2.2-A14B`（NVFP4 + 稀疏注意力）在 **RTX 5090** 上 720p I2V 4 步端到端 26.7 s、480p 10.7 s（基线 40 步 2685 s / 787 s）——**要求 RTX 50 系，4090 用不了**。
- **许可**：框架与 Wan / HunyuanVideo 蒸馏权重 Apache‑2.0（HF 元数据）；H3 Turbo LoRA 的许可按 skill 既有记录随 H3 社区许可。
- **对 4090 短剧的价值**：Wan 替补路线的蒸馏件全部来自这里；它证明了「4 步 + 关 CFG + 第 2 步交接 + shift 5」是官方配方而不是社区偏方。
- **评级：采用其 LoRA / 观望其框架**（服务模式 + Docker 优先，Windows 单卡收益未验证）。

### 4.7 Lightricks/LTX‑2（★10338）+ ComfyUI‑LTXVideo（★4272，最后推送 2026‑11‑12）—— LTX‑2.3 / 2.5
- **定位**：H3 之外唯一成体系的「音画同生」开源线。2.5（2026‑08）相对 2.3：Gemma 4 12B 文本编码器、扩散式视频解码器、**原生多镜头**、时长预测头、DFR 生产档；核心已原生支持，官方节点包只补高级功能（IC‑LoRA 引导、Looping / Tiled Fusion 采样器、HDR、低显存加载器、纯音频模式）。
- **机制**：视频与音频 latent 拼成一个序列联合去噪（`LTXVConcatAVLatent / SeparateAVLatent`）；图像 / 关键帧 / 参考视频都以「引导帧」形式写入 latent（`LTXVImgToVideoInplace`、`LTXVAddGuide`、`LTXAddVideoICLoRAGuide`）；IC‑LoRA = 把参考视频 token 拼进上下文再用 LoRA 教模型读它。
- **关键参数**：见链路 B。提示词规范（docs.ltx.io）：单段落、现在时、情绪写成可见动作、台词加引号并注明语言；**多镜头**写法——每个切点用自然语言点名转场（hard cut / match cut / dissolve）、重建新镜头的景别与机位、用同一组外观标识复述人物、交代声音跨切点是否延续，**一次 2–4 个镜头**；I2V 从首帧开始时建议保持单镜头。「别把 Kling / Seedance 的标签式提示词原样贴进来」。
- **硬件与速度**：仓库 README 写 32 GB+；LTX‑Desktop 要求 24 GB 起（建议 32 GB）+ 64 GB 内存。〔LD〕（由 5090 实跑推算）24 GB 卡在「流式加载」下可单次跑 720p ≤ 20 s、1080p ≤ 10 s；1080p 20 s 要分 3 块，1440p / 4K 全靠分块（5090 上 3 s 的 4K 约 7 分钟、10 s 约 26 分钟）；流式比全驻慢 10–25%。4090 的 720p 实际秒数**没有可靠公开口径**（仅一条社区自报 ≈ 99 s，未注明规格）。
- **许可**：代码 Apache‑2.0；权重 LTX‑2.x Community License——年营收 ≥ 1000 万美元的实体需付费授权；2.5 仓库 gated（HF 上点同意即可）。
- **对 4090 短剧的价值**：① 单次 20 s + 原生多镜头，是 H3（15 s）之外的长对白段候选；② A2V 与 Dub‑It 给「锁原配音」和「改台词」两条路；③ IC‑LoRA 工具族（去字幕 / 水印、抠像、修复、外扩、参考表一致性）可当后期工具。风险：中文对白质量未见验证（Dub‑It 官方只验证英法西德俄）；24 GB 很紧；官方承认高频纹理在运镜时沸腾。
- **坑**：HF 仓库 gated，未登录下载直接 401；编码器与 DiT 不能同驻 24 GB；画面内文字仍不可靠（官方建议短、显眼、关键字幕后期加）；复杂物理易出伪影；LoRA 与模型版本要对应（官方 README：LoRA 只对训练它的模型有效）。
- **评级：试用**（先做一次「同分镜 H3 vs LTX‑2.5」的 10 s 中文对白对照，再决定是否进流水线）。

### 4.8 wildminder/awesome‑ltx2（★604，最后推送 2026‑11‑13）与 RuneXX 工作流集
- **定位**：LTX‑2 / 2.3 / 2.5 的全量索引（README 432 KB）。作者同时维护 awesome‑minimax‑H3，是我们已经在用的那类「社区事实表」。
- **内容**：各家量化表（官方 int8‑convrot 21.5 GB、nvfp4 18.7 GB；社区 w4a8 12.5–15.4 GB、fp8 19–23.5 GB；QuantStack / Unsloth / Vantage GGUF）、文本编码器（Comfy‑Org 优化版、Gemma 3 / 4 各量化、abliterated 版）、分离组件（transformer / VAE / connector）、LoRA 分类（风格、IC‑LoRA 的 Control / Restore / Outpaint / Relight / Edit / Effect、Camera、Audio‑Foley、Character‑FaceSwap、Motion、Distill、ID‑LoRA）、训练工具与工作流合集。
- **关键参数（表里能直接抄的）**：LTX‑2.5 蒸馏 GGUF 推荐 `UD-Q4_K_XL`（14 GB，「明显好于 Q4_K_M，接近 Q5_K_M」）；训练数据切成 121 帧（8n+1）；量化训练 24 GB 是实际下限。
- **`RuneXX/LTX-2.3-2.5-Workflows`（HF）**是其中最完整的社区工作流集：基础 I2V / T2V（含 GGUF 版、单段版、dev 全步数版）、**Movie‑Maker 系列**（Prompt‑Relay 时间线：多图多段短故事、自带配音版、dev 版）、多主体参考（Licon‑MSR V1 / V2、与 Ingredients 组合、Best‑Face‑ID LoRA、脸 + 声音参考）、角色表辅助工作流（Flux Klein / Krea 2 / Qwen‑Image 出参考表）、口播（Qwen‑TTS 克隆）。作者注明多数 2.3 工作流换上 2.5 模型即可用。
- **Prompt‑Relay**（GordonChen19，训练‑free）：给每条提示词指定时间区间，在交叉注意力里对区间外的 token 加距离惩罚，让多事件按时间顺序发生；论文自报在 Wan 2.2 上的时间对齐评分优于基线。
- **硬件与速度**：索引本身无数据；README 里 4090 一行只写「24 GB，需 offloading」。
- **许可**：列表无许可证声明；收录的模型以 LTX 社区许可为主，另有大量未审查微调，商用前逐个核对。
- **对 4090 短剧的价值**：选 LTX 量化档与找 IC‑LoRA 的入口；Movie‑Maker 的「时间线 + 逐段提示词路由」可与我们的分镜 JSON 对照。
- **评级：采用为索引**（工作流本身按需试用）。

### 4.9 Tencent HunyuanVideo 1.5（★4609，最后推送 2026‑04）及 Avatar / Custom / Foley
- **定位**：8.3B 轻量模型，官方称 14 GB（开 offload）可跑；自带 720→1080p 超分蒸馏模型。
- **机制**：8.3B DiT + 3D 因果 VAE（空间 16×、时间 4× 压缩）；文本侧是 Qwen2.5‑VL 7B + byT5（字形）双编码器，I2V 另加 SigLIP 视觉编码；720p 模型带稀疏注意力（SSTA）版本。
- **参数**：官方表——480p shift 5、720p T2V shift 9 / I2V shift 7、CFG 6、50 步；CFG 蒸馏版**必须 50 步**；480p I2V 步数蒸馏 8 / 12 步 shift 7（官方称 4090 端到端 75 s 内）。ComfyUI 模板用 20 步 CFG 6 shift 7，SR 分支默认旁路。
- **实测**〔5090L〕：480p / 121 帧 / 4 步（lightx2v LoRA）117 s；**720p → 1080p SR 流水线跑满 70 分钟未完成**；「480p / 720p / i2v / SR 是四个不同的基座模型」。
- **许可**：Tencent Hunyuan Community License——不适用于欧盟、英国、韩国（澳洲在许可地域内）；月活 > 1 亿需另行申请；不得用输出训练其它模型。
- **周边**：Avatar 官方最低 24 GB「但很慢」，无原生节点；Custom 走 kijai 的 HunyuanVideoWrapper（2025‑05）；Foley 有两个社区节点，XL 版 offload 后 8 GB。
- **对 4090 短剧的价值**：480p 4 步档（约 2 分钟 / 5 s）可当无声草稿；官方演示强调画面内文字渲染与运镜提示词，但 24 GB 上拿不到它的 1080p。
- **评级：观望**（没有 H3 / Wan / LTX 给不了的能力）；Foley **试用**归 04 簇。

### 4.10 MeiGen‑AI/InfiniteTalk（★8445，Apache‑2.0）· MultiTalk（★3038）· LongCat‑Video‑Avatar
- **定位**：音频驱动的「稀疏帧视频配音」——不止改嘴，头、身体、表情一起随音频动；支持图生与视频重配、单人 / 多人、无限长。
- **机制**：Wan 2.1 I2V 14B 480p + 一个 5 GB 的音频交叉注意力补丁；窗口 81 帧，取上一窗最后 9 帧作运动帧；音频特征来自 `chinese-wav2vec2-base`。核心把它做成 `ModelPatchLoader` + `WanInfiniteTalkToVideo`。
- **ComfyUI 参数**：核心模板 832×480、length 81、`motion_frame_count` 9、6 步、CFG 1、euler、25 fps，底模 `Wan2_1-I2V-14B-480p_fp8_e4m3fn_scaled_KJ` + `lightx2v_I2V_14B_480p_cfg_step_distill_rank64`；kijai 示例用 Q8 GGUF 底模 + BlockSwap 20、shift 11、`dpm++_sde`，并先用 MelBandRoFormer 分离人声。
- **官方建议**：480p / 720p 都可；音频 CFG 3–5（挂 LoRA 后 2）；默认最长 1000 帧（40 s）；内存不够用量化版；V2V 用 SDEdit 能更贴原运镜但会偏色，只适合短片段。
- **后继**：同团队的 LongCat‑Video‑Avatar 1.5（2026‑05，Whisper‑large、8 步蒸馏、单 / 多路音频、泛化到动漫与动物）与 1.6（2026‑11‑15，自称 > 10 分钟），MIT；kijai 已有 Avatar 示例（BlockSwap 25、bf16、93 帧窗口 / 13 帧重叠），1.6 的 ComfyUI 支持未验证。
- **对 4090 短剧的价值**：H3 skill 里「要原录音逐字一致只能换 Wan + InfiniteTalk」的那条路，核心模板即可跑；V2V 模式可给 H3 出的无声 / 错词镜头补口型。
- **硬件与许可**：官方称 MultiTalk 起就能在单张 4090 上跑 480p；无带口径的耗时。InfiniteTalk / MultiTalk Apache‑2.0，LongCat 系 MIT。
- **评级：采用**（精确口型的默认方案）；LongCat‑Avatar 1.6 **观望**。

### 4.11 vita‑epfl/Stable‑Video‑Infinity（★2626，MIT，ICLR 2026 Oral）及其 ComfyUI 节点
- **定位**：用「错误回收」微调出的 LoRA，让 Wan I2V 可以无限接力而不漂色。1.0（2025‑10）分 Shot / Film / Talk / Dance 等专用 LoRA；2.0（2025‑12‑04）同时支持 Wan 2.1 与 2.2；**2.0 Pro（2025‑12‑26）**是当前社区主力，对应 Wan 2.2 I2V A14B high / low。
- **机制**：见链路 E——固定锚点 latent + 上一段末尾 latent 作条件，只在遮罩里标第一帧；每段可以有独立提示词（官方工作流原生支持「逐段提示词流」）。
- **关键参数**：`SVI_v2_PRO_Wan2.2-I2V-A14B_{HIGH,LOW}_lora_rank_128_fp16`（各 1.23 GB，Kijai HF）；每段 81 帧；`motion_latent_count` 1；像素拼接重叠按需 ±1–2 帧。
- **社区节点**：KJNodes `WanImageToVideoSVIPro`、wrapper `WanVideoSVIProEmbeds`、`Well-Made/ComfyUI-Wan-SVI2Pro-FLF`（★83，GPL‑3.0，加末帧锁与「加载已有视频继续」）、`wallen0322/ComfyUI-Wan22FMLF`（SVI Pro Advanced：`overlap_frames` 4、`motion_boost`、针对 1080p 下动态减弱）。同思路已被移植到 LTX（`Z-L-D/LTX2-Infinity`，每段 10 s）。
- **硬件与速度**：与普通 Wan 2.2 I2V 相同（多挂两个 1.23 GB LoRA），总时长线性增加；README 展示了 8–14 分钟成片与社区 40 s / 1 min 无漂色测试，但没有带口径的耗时。
- **坑**：官方置顶——不同段必须换种子；蒸馏 LoRA 用多了动作变慢，480p 更稳；量化与步数蒸馏对 SVI‑Film 影响大；别用仓库里的 1.0 工作流跑 2.0；发灰时在拼接前加 1.2 左右对比度（SVI2Pro‑FLF）。
- **许可**：MIT（LoRA 与代码）。
- **对 4090 短剧的价值**：无对白的长跟拍 / 一镜到底；与 H3 的 Motion‑Context 属于同一机制（尾 latent 作条件），「每段换种子」「锚点固定」两条经验可直接借。
- **评级：试用**。

### 4.12 ali‑vilab/VACE（★4069）+ Wan 2.2 Fun VACE + stuttlepress/ComfyUI‑Wan‑VACE‑Video‑Joiner（★109，MIT）
- **定位**：VACE 是 Wan 的「全能编辑」：参考生成、遮罩重绘、外扩、控制视频、首尾帧。2.2 时代由 alibaba‑pai 的 Fun VACE（high + low，各 17.35 GB fp8）接棒；Kijai 另抽出可挂在普通 T2V 上的 VACE 模块（各 6.1 GB）。
- **机制**：`WanVaceToVideo(control_video, control_masks, reference_image, strength)`——控制视频里灰色 / 被遮罩的部分由模型生成，其余保留；参考图作为额外帧拼在序列前，采样后用 `TrimVideoLatent` 裁掉。
- **官方模板参数**〔T〕：参考生视频 / 控制视频 / 外扩用 `wan2.1_vace_14B_fp16`（32.29 GB）+ CausVid LoRA 0.3–0.4、3–4 步、CFG 1、`uni_pc`、shift 8；遮罩重绘模板已更新为子图版：「20 步 CFG 6」与「蒸馏 6 步 CFG 1」双档，并内置 SAM3.1 分割。便签：VACE 按约 81 帧 @16 fps 的短片段训练，**不能可靠地一次处理很长的视频**。
- **Joiner 的做法**：把一个目录里的片段按文件名排序，逐个接缝取两侧上下文帧，让 VACE 重新生成中间的过渡帧并顺手替换掉接缝处的坏帧；N 段排队 N−1 次；可选首尾循环。**输入可以来自任何模型或实拍**；最小片段长度 = (context_frames + replace_frames) × 2 + 1。
- **硬件与速度**：〔T 便签〕Wan 2.1 VACE 14B 720p / 81 帧在 4090 上约 40 分钟，挂 CausVid LoRA 后约 4 分钟（1.3B 约 2 分钟）；Joiner 每个接缝只生成几十帧，无公开耗时。
- **坑**：分辨率须是 16 的倍数（1080 不是）；素材高于 16 fps 时上下文 / 替换帧数要按倍数放大，作者建议先降到 16 fps 处理再插帧回去；VACE 自带亮度 / 饱和偏移，蒸馏 LoRA 会加重；Wan 2.1 VACE 偶发输出帧数少于输入导致交叉淡化重影（关掉 cross‑fade 规避）；ComfyUI 前端 1.40.x–1.42.9 的子图 bug 会让它只跑一半。
- **许可**：VACE 与 Fun VACE Apache‑2.0；Joiner MIT。
- **对 4090 短剧的价值**：H3 硬切与 latent 续接之外的第三种段间衔接——只重生成接缝的十几到几十帧；也可修掉段尾定格 / 段首坏帧。
- **评级：试用**。

### 4.13 bytedance/Bernini → Bernini‑R（★1371，Apache‑2.0，2026‑06）
- **定位**：「MLLM 语义规划 + 视频渲染」框架里开源出来的渲染器，底座 Wan 2.2（high + low 两个模型），in‑context 条件；ComfyUI 核心只有渲染器（`BerniniConditioning`），没有规划器——长提示词质量要靠官方仓库的 `--use_pe`。
- **能力**：文生、视频编辑（v2v / 遮罩 mv2v）、参考生视频（r2v）、**带参考图的视频编辑（rv2v：换装 / 换造型）**、把一段视频植入另一段（ads2v）。
- **机制**：源视频按输出尺寸缩放并截到 `length` 帧；每张参考图单独编码成一路 in‑context 流（长边限 `ref_max_size` 848，保持比例，不拉到整幅）；提示词 = 任务类型对应的系统提示词 + 英文描述，多参考按 image0、image1… 指代。
- **关键参数**：848×480 或 832×480、81 帧 @16 fps、宽高 16 的倍数；Turbo：lightx2v T2V v2 LoRA 高噪 3.0 / 低噪 1.5、6 步（3 + 3）、CFG 1、`res_multistep`；原始：40 步（20 + 20）、CFG 5（官方 Python 另有 APG，模板未完全复现）。
- **硬件与速度**：两个 14.51 GB fp8_scaled 模型轮换，结构与 Wan 2.2 I2V 相同；无公开 4090 耗时。
- **许可**：Apache‑2.0（代码与 Comfy‑Org 重打包权重）。
- **对 4090 短剧的价值**：给已生成的镜头换服装 / 换道具 / 植入屏幕内容，比整段重抽便宜；模板便签明说 Turbo 只适合试提示词与连线，换装等精细编辑要关 Turbo。
- **评级：试用**。

### 4.14 city96/ComfyUI‑GGUF（★4283，Apache‑2.0，最后推送 2026‑01）
- **定位**：GGUF 量化 DiT / 文本编码器的加载器。README 仍自称 WIP，但已是事实标准；kijai wrapper 的主加载器也能直接读 GGUF。
- **机制**：`Unet Loader (GGUF)`（bootleg 分类）替换 `Load Diffusion Model`，文件放 `models/unet`；`*CLIPLoader (gguf)` 读量化 T5；LoRA 用原生加载器，标注为实验性。
- **关键参数（档位选择）**：Wan 2.2 I2V（QuantStack）Q4_K_M 9.65 GB、Q5_K_M 10.79 GB、Q6_K 12.00 GB、Q8_0 15.41 GB，高低噪各一份；LTX‑2.5（Unsloth）`UD-Q4_K_XL` 14 GB、Q6_K 17.81 GB、Q8_0 22.78 GB。
- **硬件与速度**：GGUF 属于「只压权重」一类，省显存不提速，甚至更慢〔5090L §2.2〕；24 GB 上 Wan 2.2 的 fp8（14.3 GB / 专家）已能驻留，不需要它。
- **许可**：Apache‑2.0。
- **对 4090 短剧的价值**：只在 LTX‑2.5 这类「DiT + 编码器 + 解码器」挤不进 24 GB 时用（Q4–Q6 给解码与参考留余量），或在 16 GB 以下的机器上复现流程。
- **坑**：README 提醒单卡不要装 / 乱设「Force / Set CLIP Device」；kijai 便签：GGUF 的 MultiTalk / InfiniteTalk 补丁不能与非 GGUF 主模型混用，但不同量化档之间可以混。
- **评级：观望**（4090 默认不用）。

### 4.15 Kosinkadink/ComfyUI‑VideoHelperSuite（★1927，GPL‑3.0）/ Fannovel16/ComfyUI‑Frame‑Interpolation（★1095，MIT）/ 核心视频节点
- **定位**：视频的读、写、切、合与插帧。两年来的事实标准是 VHS + Frame‑Interpolation，2026 年核心补齐了大部分。
- **核心现状**〔C `nodes_video.py`、`nodes_frame_interpolation.py`、`nodes_loop.py`、`nodes_video_deflicker.py`〕：`LoadVideo / GetVideoComponents / CreateVideo / SaveVideo / Video Slice / VideoTrim / VideoCrop / ConcatenateVideo / VideoDeflicker / FrameInterpolate / StartLoop‑EndLoop`；新官方模板基本不再依赖 VHS。
- **VHS 仍然必要的地方**：kijai 的全部示例都用它——`VHS_LoadVideo`（`force_rate` 重采样、`frame_load_cap` 限帧、`select_every_nth` 抽帧、`custom_width / height`）、`VHS_VideoCombine`（h264‑mp4、crf 19、`trim_to_audio`、把工作流写进元数据）、Meta Batch Manager（长片分批合成，VACE Joiner 用它防内存溢出）。
- **Frame‑Interpolation**：RIFE 4.0–4.9、FILM、GMFSS Fortuna、IFRNet、AMT 等十余种；`clear_cache_after_n_frames` 防 OOM；STMFNet / FLAVR 只能 2 倍且至少 4 帧。
- **硬件与速度**：插帧与封装都是轻负载；核心 FILM 权重 65.7 MB。未见 4090 口径的插帧耗时。
- **许可**：VHS GPL‑3.0；Frame‑Interpolation MIT（各插帧模型另有许可）。
- **对 4090 短剧的价值**：`force_rate` 是把参考 / 驱动视频对齐到模型帧率的最省事办法（H3 的参考视频要求 24 fps，Wan 要 16 fps）。
- **评级**：VHS **采用**；Fannovel16 包 **观望**（核心 FILM / RIFE 已够用，除非要 GMFSS / AMT）。

### 4.16 超分与修复：RelayVSR / SeedVR2 / FlashVSR / RTX Video / VOID
- **定位**：成片之后的「最后一跳」。2026 年的变化是一步扩散超分进了核心，且有专门为 H3 后处理重训的权重。
- **RelayVSR**（kopper/RelayVSR，Apache‑2.0；核心 `RelayVSRConditioning` + `VSRDecode`；模板 2026‑11‑10 / 11‑14）：大的 Wan 系模型只给稀疏关键帧写参考 latent（每 15 帧一个），轻量 Flash 解码器把它铺到每一帧，所以长片一遍流式跑完；`relayvsr_x2_lightx2v_int8_convrot` 4.81 GB + `relayvsr_flash_vae_x2_fp32` 0.12 GB；steps 1 / cfg 1 / euler / simple；倍率由权重决定，×2 与 ×4 文件不能混；帧率与音轨原样带出；OOM 就裁段分批；需 ComfyUI ≥ 0.45。**采用**（skill 已列为最后一跳首选）。
- **SeedVR2**（ByteDance‑Seed，Apache‑2.0）：核心原生 3B int8 一步修复（模板使用量 516），7B 走 `numz/ComfyUI-SeedVR2_VideoUpscaler`（★3004）；〔5090L〕图像 768²→3072² 23.6 s。skill 既有结论「SeedVR2 会让嘴部发飘」仍适用——**只用于无对白镜头**。
- **Wan 2.2 低噪精修**（`utility_video_upscale`）：生成式，会改细节；适合漫剧 / 远景，不适合要保脸的特写；单次 ≤ 121 帧，4K 很吃显存（模板便签）。**试用**。
- **RTX Video**（`utility_nvidia_rtx_video_enhance`，需 ≥ 0.40；另有 `Deno2026/comfyui-deno-custom-nodes` ★233）：驱动级超分 + 插帧 + SDR→HDR 一条链，在本地 RTX 显卡上运行（速度与对生成瑕疵的修复能力均未验证）。**试用**。
- **FlashVSR**：kijai 版标 WIP 且自述与原版结果不一致；`lihaoyun6/ComfyUI-FlashVSR_Ultra_Fast`（★811）停在 2025‑11。**观望**。
- **VOID**（核心原生，CogVideoX 底座）：SAM3.1 选中物体 → 两遍各 30 步 CFG 6，连同其物理影响一起移除；默认 672×384、5 s。可用来抹掉 H3 自己长出来的手指 / 道具。**试用**。
- **硬件与速度**：RelayVSR ×2 在 skill 里已有「25 s」量级的记录；其余无 4090 口径。

### 4.17 其它模型速评
- **SkyReels V3**（★603，skywork‑license）：亮点是 V2V 续写里的「切镜续写」（Cut‑In / Cut‑Out / 正反打 / 多角度 / Cut‑Away，限 5 s）与 1–4 张参考的 R2V；但 14B / 19B、ComfyUI 只有 kijai 的 A2V，24 GB 要 `--low_vram`。**观望**。V2 的 Diffusion Forcing 14B 540P 官方峰值 43–51 GB。
- **Kandinsky 5 Lite**（MIT）：权重最小（4.57 GB），但〔5090L〕768×512×121 帧 50 步要 884.5 s。**跳过**。
- **MAGI‑1.1 24B**（2026‑06，Apache‑2.0）：自回归分块，无核心支持。**观望**。
- **FramePack**（★17377）：6 GB 能出 60 s，但底座是 HunyuanVideo 1.0，4090 上 1.5–2.5 s / 帧（30 fps，即 5 s 片约 4–6 分钟）。**跳过**。
- **Ovi 1.1**：10 s 音画同生，24 GB 需 fp8 + CPU offload，50 步 CFG 4。H3 与 LTX 已覆盖。**跳过**。
- **HuMo**：文 + 图 + 音三条件、原生节点、97 帧上限。口型精度官方称 1.7B 版也基本不掉。**观望**（InfiniteTalk 更成熟）。
- **Helios**（★2271）：14B 实时长视频（H100 上 19.5 FPS），Group Offloading 后约 6 GB，仅 diffusers。**观望**。
- **Causal Forcing / Capybara / WanMove / ATI / Wan‑Dancer**：核心有节点，用途窄（实时自回归、指令编辑、轨迹控制、音乐舞蹈）。**按需**。

### 4.18 基准与索引类
- **lifeidle/comfyui‑5090‑laptop‑24gb‑minimax‑h3‑qwen‑image‑wan2.2**（★26，文档 MIT，2026‑11‑02 快照）
  - 定位：15 条模型线 / 30 组配置的 24 GB 实测手册（图像、视频、音画、动作迁移、音乐、3D），附下载器、模板→API 转换器、A/B 脚本。
  - 方法（比数字更值钱）：计时取服务端 `execution_start / execution_success`；复测换 seed，否则命中全节点缓存得到 0.0 s 假计时；量化对比必须固定编码器、用种子间差异作噪声地板；跑前 `POST /free`；产物用 ffprobe + 抽帧复核；「跑不动」要明确记录为不可行。
  - 结论里对我们有用的：Wan 14B 与 5B 的 VAE 不通用；HunyuanVideo 1.5 的 720p + SR 在 24 GB 不可行；老 LTX‑Video 2B 蒸馏在 CFG 1 下不跟随提示词（已淘汰，并自认当初因 fp8 体积否决 LTX‑2.3 是判断失误）；视频模型许可普遍是「社区许可 + 营收门槛 + 地域排除」。
  - 局限：GPU 是 Blackwell 笔记本，NVFP4 结论不适用于 4090；Animate 线的权重版本描述不清；没有 LTX‑2.3 / 2.5 的数据。
  - **评级：采用其方法，数字仅作量级参考**。
- **deepbeepmeep/Wan2GP（WanGP）**：非 ComfyUI 的低显存一体化应用（Wan / H3 / LTX‑2.x / HunyuanVideo / LongCat，自带 RIFE、FlashVSR、RelayVSR、SeedVR、MMAudio、MCP 接口）；InfiniteTalk、HunyuanVideo‑Avatar、HunyuanCustom 等官方 README 都把它列为低显存首选（Avatar 10 GB、Custom 8 GB）。与我们的 ComfyUI + agent 路线不兼容。**观望**。
- **neverbiasu/Awesome‑ComfyUI‑Video**（★28）：表格数据停在 2025‑04，**跳过**。
- **GitHub 上的工作流合集**：没有找到高星且仍在维护的 Wan / LTX 专门合集——`ZHO-ZHO-ZHO/ComfyUI-Workflows-ZHO`（★7987）停在 2024‑12；`LingyiChen-AI/comfyui-workflow-skill`（★456，2026‑04）是「自然语言 → 工作流 JSON」的 skill，内置 Wan 2.2 文生 / 图生 / 首尾帧 / Fun Control / 相机控制等 34 个模板（归 02 簇细看）；`Cordux/ComfyUI-Wan2.2-workflow`（★71）是 6 GB 卡用 Rapid AIO 合并模型 GGUF 的低显存流程。活跃的社区工作流主要在 HuggingFace（RuneXX、Kijai）与 Civitai，后者本轮未读。

## 五、24 GB 单卡的耗时与显存（全部为他人口径，逐条标注）

| 模型 · 配置 | 规格 | 耗时 | 显存 | 硬件 | 来源 |
|---|---|---|---|---|---|
| Wan 2.2 14B I2V / T2V / FLF2V，fp8_scaled，20 步 CFG 3.5 | 640×640×81 帧（5 s @16） | 513–536 s | 84% | RTX 4090D 24 GB | 〔T〕模板便签 |
| 同上 + lightx2v 4 步 LoRA | 同上 | 首跑 97–108 s / 二跑 71 s | 83–89% | 4090D | 〔T〕 |
| Wan 2.2 14B T2V，4 步 LoRA | 832×480×81 帧 | 93.8 s | 双专家 28.6 GB 轮换 | 5090 笔记本 24 GB | 〔5090L〕 |
| Wan 2.2 5B TI2V，20 步 CFG 5 | 1280×704×121 帧（5 s @24）/ 704×384×49 帧 | 355.1 s / 34.6 s | — | 同上 | 〔5090L〕 |
| Wan 2.1 VACE 14B fp16，无蒸馏 → CausVid 4 步 | 720p×81 帧 | ≈ 40 min → ≈ 4 min | — | RTX 4090 | 〔T〕便签 |
| Wan 2.1 ATI 14B，20 步 | 720×480×81 帧 | 463–500 s | 90% | 4090D | 〔T〕 |
| Wan 2.2 Animate（Move / Mix），4 / 6 步 | 832×480×77 / 640×640×77 | 105 s / 155 s | — | 5090 笔记本 | 〔5090L〕（权重版本口径存疑） |
| LTX‑2.5 蒸馏 fp8（社区转换） | **未注明分辨率与时长** | ≈ 99 s | DiT ≈ 20–21.5 GB，Gemma 4 ≈ 14.6 GB，须错峰 | RTX 4090 + 64 GB RAM | guillaume127/LTX‑2.5‑FP8 模型卡自报 |
| LTX‑2.5 能力边界 | 720p ≤ 20 s、1080p ≤ 10 s 单次（流式）；1080p 20 s 分 3 块 | 无秒数 | 24 GB | 由 5090 实跑推算 | 〔LD〕 |
| LTX‑2.5 4K | 3 s / 10 s | ≈ 7 min / ≈ 26 min | 32 GB | RTX 5090 | 〔LD〕 |
| HunyuanVideo 1.5 480p，lightx2v 4 步 | 848×480×121 帧（5 s @24） | 117 s | — | 5090 笔记本 | 〔5090L〕 |
| HunyuanVideo 1.5 480p I2V 官方步数蒸馏 8–12 步 | 480p | ≤ 75 s | — | RTX 4090 | 官方 README 自报 |
| HunyuanVideo 1.5 720p → 1080p SR | 1280×720 → 1920×1080×121 帧 | > 70 min 未完成 | — | 5090 笔记本 | 〔5090L〕 |
| Kandinsky 5 Lite T2V，50 步 | 768×512×121 帧 | 884.5 s | — | 同上 | 〔5090L〕 |
| FramePack（HunyuanVideo 1.0 底座） | 30 fps | 1.5–2.5 s / 帧（5 s ≈ 4–6 min） | 6 GB 起 | RTX 4090 台式 | 官方 README |
| LightWan2.2‑A14B（NVFP4 + 稀疏，LightX2V 框架） | 720p I2V 4 步 | 26.7 s | — | **RTX 5090** | 〔LX〕——4090 不适用 |
| 对照：H3 Ref2VA Turbo 8 步 + Sage | 864×480×10 s | 134 s | — | RTX 4090（用户实测） | 本仓库 skill |
| 对照：H3 T2VA 8 步 | 1344×768×124 帧（5 s） | 519 s | DiT 21 GB + 编码器 15.7 GB，必须 offload | 5090 笔记本 | 〔5090L〕 |

- **10 s 口径**：Wan 14B 与 HunyuanVideo 1.5 单次只有 5 s，10 s = 两段接力（SVI / Context Windows / 尾帧），耗时约为单段的 2 倍再加重叠开销（推算，未见实测）；LTX‑2.5 的 10 s 是单次 241 帧，4090 实际秒数没有可靠公开数据；H3 的 10 s 有本仓库实测（上表）。
- **换算提醒**：4090D 比 4090 略慢；5090 笔记本的 24 GB 是 Blackwell 架构，算力与 4090 台式不同档，且该文多数视频线未用 NVFP4——**量级可参考，不能当 4090 基准**。
- **Animate‑2 / SCAIL‑2 / InfiniteTalk / SVI / Bernini‑R 在 4090 上的耗时未找到带完整口径的公开数字**（见「未覆盖」）。

## 六、许可证（能否商用）

| 对象 | 许可 | 商用 | 备注 |
|---|---|---|---|
| Wan 2.1 / 2.2 全系、Animate、Animate‑2、S2V、Dancer、alibaba‑pai Fun 系、lightx2v 蒸馏件、Comfy‑Org / Kijai 重打包 | Apache‑2.0 | 可 | 最干净的一组 |
| InfiniteTalk、MultiTalk、HuMo、Phantom、Stand‑In、Lynx、Ovi、Bernini‑R、SeedVR2、RelayVSR、FlashVSR、MAGI‑1 | Apache‑2.0 | 可 | Lynx 工作流里裁脸用的 InsightFace buffalo 模型为非商用，需换裁脸方式；FramePack 代码也是 Apache‑2.0，但底座 HunyuanVideo 权重受腾讯许可约束 |
| SCAIL‑2 权重、LongCat‑Video / Avatar、SVI LoRA、Kandinsky 5 | MIT | 可 | — |
| MoCha 权重 | AGPL‑3.0（HF 标注） | 有传染性条款，商用项目回避 | GitHub 仓库未声明许可 |
| LTX‑2 / 2.3 | LTX‑2 Community License | 年营收 < 1000 万美元可免费商用 | 常被误写成 Apache‑2.0 |
| LTX‑2.5 | LTX‑2.x Community License | 同上 | HF 仓库 gated，需登录同意 |
| HunyuanVideo 1.5 / Avatar / Custom / Foley | Tencent Hunyuan Community License | 有条件 | 不适用于欧盟 / 英国 / 韩国；月活 > 1 亿另行申请；输出不得用于训练其它模型 |
| SkyReels V2 / V3 | skywork‑license | 未读全文，用前自查 | HF 标 `other` |
| H3（对照） | MiniMax Community License | 有条件 | 〔5090L 附录 F〕转述：排除 US / EU / UK / KR，营收 < 2000 万美元，界面标注「MiniMax H3」（本轮未独立核对许可原文） |
| 节点代码 | WanVideoWrapper Apache‑2.0；ComfyUI 核心 / KJNodes / VHS / WanMoeKSampler / SVI2Pro‑FLF GPL‑3.0；ComfyUI‑LTXVideo 自定义许可；PainterI2V / Wan22FMLF 未声明 | 自用无碍 | 本 skill 只引用结论，不打包这些代码 |

## 七、与 H3 流水线对照

### 7.1 能力对照表

| 维度 | MiniMax H3（开源权重） | Wan 2.2 14B | LTX‑2.5 | HunyuanVideo 1.5 |
|---|---|---|---|---|
| 单次时长 | 4–15 s（124–362 帧 @24；4090 实测单段上限 328 帧） | 81 帧 @16 fps ≈ 5 s | 8n+1 帧；官方应用到 20 s；24 GB 流式 720p ≤ 20 s〔LD〕 | 121 帧 @24 = 5 s |
| 分辨率 | 768P 格点 → latent 二采到 1920×1088 | 480p / 720p | 半分辨率出片 + latent ×2；分块可到 4K | 480p / 720p；1080p SR 在 24 GB 不可用 |
| 原生音频 | 有，32 kHz 立体声 | 无 | 有，音画联合去噪 | 无 |
| 对白 | `<d>` 标签，11 种语言，中文是主场 | 无（靠 S2V / InfiniteTalk 后驱动） | 引号台词；LTX‑2.3 模型卡语言标签含 zh（2.5 模型卡 gated 未读到）；**中文质量未验证** | 无 |
| 单次多镜头 | 2–4 子镜头，时码写法 | 无 | 原生，2–4 镜，自然语言写切点 | 无 |
| 参考能力 | Ref2VA：9 图 + 3 视频 + 3 音频 | VACE 参考、Phantom、MAGREF、Stand‑In、Lynx、Bernini‑R（约 5 路） | Ingredients 参考表、MSR ≤ 5 路、ID‑LoRA（脸 + 声） | 无（Custom 是另一个模型） |
| 控制能力 | Fun‑ControlNet‑Union | Fun Control、VACE、9 种运镜预设、轨迹（ATI / WanMove）、动作迁移（Animate / SCAIL） | IC‑LoRA Union / Motion‑Track / Layout‑To‑Render；运镜 LoRA 仅 19B | 无 |
| 锁现成配音 | 社区音频锁节点 | InfiniteTalk / S2V / HuMo | A2V 冻结音频；Dub‑It 改台词 | 无 |
| 负面提示词 | 无（CFG 蒸馏） | 非蒸馏档有效 | dev 档有效，蒸馏档无 | 有效 |
| 生态成熟度 | 发布 3 个多月约 1750 个仓库，集中在导演台 / 续接 / 加速 | 最成熟：kijai README 列了约 25 个衍生模型，蒸馏 / 续接 / 编辑齐全 | 官方 HF 上 2.3 / 2.5 的 IC‑LoRA 各十余个 + awesome‑ltx2 | 低 |
| 24 GB 可用性 | DiT 19.5–21 GB + 编码器 14.6–15.7 GB，必须 offload | 好（每步只驻留一个 14.3 GB 专家） | 紧（DiT 21.5 GB + Gemma 4 约 14.6 GB，须错峰） | 480p 好 |
| 许可 | MiniMax Community | Apache‑2.0 | LTX‑2.x Community | Tencent Community |

### 7.2 三类结论

**H3 已原生解决、不必外求的**：音画同生与中文对白；多图 + 音色参考；单次多镜头；首尾帧（FL2VA）；姿态 / 深度 / 边缘控制；latent 二采（LBH）；蒸馏（Turbo）；超长段的官方滑窗（核心 `MiniMaxH3ContextWindows`）。在「有对白的短剧段」这个主战场，本簇没有任何一个模型能整体替代 H3——LTX‑2.5 是唯一同类，但中文对白与 24 GB 余量都还是问号。

**可以直接搬进 skill 的做法**（标注落点）：
1. **步骤 6 精修 / 超分**（`references/quality-pipeline.md`）：补上「无对白镜头可用 `utility_video_upscale` 的 Wan 2.2 低噪 4 步 denoise 0.25 精修」与「核心 `FrameInterpolate`（FILM / RIFE）已原生，不必装第三方包」；RelayVSR 的版本下限写成 ComfyUI ≥ 0.45。
2. **步骤 7 拼接**（`references/qc-and-assembly.md`、`continuity-long-video.md`）：新增第三种段间衔接——VACE Joiner 重生成过渡帧（16 fps、16 倍数分辨率、处理后插帧回 24、接 `ColorMatch`）；像素级重叠拼接用 `ImageBatchExtendWithOverlap`。
3. **续接**（`continuity-long-video.md`）：记录核心 `MiniMaxH3ContextWindows` 的默认值 124 / 39 / pyramid / freenoise 与 `split_conds_to_windows`（每个窗口一条提示词），列为与 Motion‑Context 的 A/B 对象；写入 LTX 官方的分块代价公式与「引导视频 / 参考锚住每个窗口则几乎不漂」这条旁证。
4. **提示词**（`references/prompt-format.md`）：把 LTX 多镜头规范的「切点四要素」（点名转场、重建景别与机位、用同一组外观标识复述人物、交代声音是否跨切点延续）做成 H3 `[Shot N]` 写法的检查清单。
5. **资产**（`references/image-stage.md`、`storyboard-and-assets.md`）：引用 Ingredients 参考表规范（黑底、一元素一面板、无文字、重要元素面板更大）作为角色板 / 道具板版式的外部佐证；借用 Animate‑2 官方的「人物外观描述 + 背景描述，不写动作」LLM 模板来生成识别短语。
6. **类型包**（`assets/genres/04-action-fight.md`、`12-talking-head-digital-human.md`、`10-music-video.md`）：把「回退路线」从笼统的「换模型」写成具体工作流名与参数（见 7.3）。
7. **环境与排错**（`references/local-stack-and-acceleration.md`、`pitfalls.md`）：文本编码后卸载编码器再采样、VAE 分块解码防最后一步 OOM、`POST /free` 返回空 body、torch.compile 首跑显存暴涨清 Triton 缓存、4090 不选 NVFP4。
8. **基准口径**：采用〔5090L〕的三条——服务端计时、复测换 seed 防缓存命中、ffprobe + 抽帧复核。

**H3 做不好、应该换模型的镜头**：见下表。

### 7.3 H3 做不好的镜头该换谁

| 镜头类型 | 首选 | 备选 | 做法要点 | 代价 |
|---|---|---|---|---|
| **快速动作 / 打斗 / 舞蹈** | Wan‑Animate‑2（驱动视频决定动作） | SCAIL‑2（遮罩绑定的动画 / 换人）；Wan 2.2 I2V 20 步或三段采样（无驱动视频时） | 角色参考图用同一张角色卡；驱动视频自拍或取素材，景别对齐；81 帧一段、lcm 6 步、CFG 1；输出 30 fps，进时间线前统一到 24 | 480p–720p 要超分；无声，音效后配；不带对白 |
| **明确运镜**（推拉摇、环绕） | Wan 2.2 Fun Camera：H3 首帧 + `WanCameraEmbedding` 预设 | ATI / WanMove 画轨迹；ReCamMaster / Uni3C 给已有片段改机位；LTX‑2 19B 运镜 LoRA | 一镜一个预设，speed 调幅度；官方便签称 4 步 LoRA 会损失动态，运镜镜头优先 20 步档 | 16 fps、5 s、无声 |
| **特效**（能量、粒子、变身、合成元素） | Wan‑Alpha（`video_wan2.1_alpha_t2v_14B`，RGBA）出透明特效层，后期叠到 H3 画面 | VACE 遮罩重绘、Bernini‑R 带参考编辑、LTX IC‑LoRA（水体、日转夜、抠像 Alpha‑Gen） | 特效与表演分层：H3 管人物与声音，特效层单独生成 | 需要合成环节；Alpha 模板只有 33 帧示例 |
| **长镜头 > 15 s** | 有对白：先测核心 `MiniMaxH3ContextWindows`；再测 LTX‑2.5 单次 20 s | 无对白：Wan 2.2 + SVI 2.0 Pro（每段 81 帧、换种子、固定锚点） | 分块时每块新增帧 = 窗口 − 重叠；纯 I2V 分块会漂，带参考 / 引导则稳 | LTX 中文对白未验证；SVI 易慢动作 |
| **精确口型 / 现成配音** | InfiniteTalk：定妆图 + 配音（I2V），或对 H3 片段 V2V 重配 | LTX‑2.5 A2V（冻结音频、输出原波形）；Wan 2.2 S2V；LongCat‑Avatar；LTX Dub‑It（仅验证英法西德俄） | 配音先人声分离；81 帧窗口、9 帧接力、25 fps；双人画遮罩各接一路音频 | 480p 起步需超分；V2V 的运镜与原片不完全一致 |
| **换装 / 换道具 / 去穿帮** | Bernini‑R rv2v（关 Turbo 跑 40 步） | VACE 遮罩重绘；VOID 去物体；LTX 去字幕 / 水印 IC‑LoRA | 只改问题区域，不重抽整段 | 81 帧一段；Turbo 档精细度不够 |

共同约束：换模型出的片段必须回到同一条后期链——统一 24 fps、同一个超分、`ColorMatch` 对齐相邻 H3 段；对白与音色仍由 H3（或配音 + 口型模型）负责。任何替补路线先做「同分镜单段样片」A/B，再进批量。

## 可写进 skill 的规则

1. 换到任何非 H3 模型前，先从 `Comfy-Org/workflow_templates/templates/<模板名>.json` 读参数（下钻 `definitions.subgraphs`），不凭记忆写 Wan / LTX 的步数、shift、文件名。
2. Wan 2.2 14B 用 `wan_2.1_vae.safetensors`，5B 用 `wan2.2_vae.safetensors`，两者不可互换（16 vs 48 通道）。
3. Wan 2.2 草稿档：`wan2.2_i2v_lightx2v_4steps_lora_v1_{high,low}_noise` 强度 1.0，4 步（高噪 2 + 低噪 2），CFG 1，shift 5，euler / simple；定稿档关 LoRA，20 步，CFG 3.5，第 10 步交接（来源：`video_wan2_2_14B_i2v`）。
4. 蒸馏 LoRA 与「T2V / I2V × high / low」逐一对应；不叠两个蒸馏件；CFG 设 1；此时负面提示词无效，要排除内容用 NAG 类节点。
5. Wan 4 步出片动作慢或运镜弱时按顺序试：kijai 示例的做法（Wan 2.1 的 `lightx2v_I2V_14B_480p_cfg_step_distill_rank64` 高噪端 3.0 / 低噪端 1.0，6 步第 3 步交接，仅采样开头给 CFG 2）→ 三段采样（TripleKSampler）→ 关 LoRA 跑 20 步；同样问题出现三次就改分镜，不换 seed 硬抽。
6. 帧数网格：Wan 4n+1（81）、LTX 8n+1（121 / 241）、H3 17k+5；宽高 Wan 取 16 的倍数、LTX 取 32 的倍数（DFR 取 64）。LTX 参数不合法不会报错而是静默改值，提交前自己算好。
7. 混剪前把所有片段统一到 24 fps：Wan 14B 是 16 fps，InfiniteTalk 25 fps，Animate / SCAIL 模板 30 fps。
8. LTX‑2.5 蒸馏档固定使用模板 sigma（阶段 1 八步 `1.0 … 0.421875, 0.0`，阶段 2 三步 `0.85, 0.725, 0.4219, 0.0`）和 CFG 1，不改步数；要更高质量走 DFR 模板而不是加步。
9. LTX 提示词写成一个 150–220 词的英文段落：景别、机位、运镜必写，台词放引号并注明语言；多镜头每个切点写清转场、重建景别、复述人物外观、声音是否延续，单次 2–4 镜；从首帧 I2V 时保持单镜头。
10. 24 GB 跑 LTX‑2.5：DiT 用 `ltx-2.5-22b-distilled-transformer-comfy-int8-convrot`（21.5 GB）或 Unsloth `UD-Q4_K_XL`（14 GB）；文本编码完成后先卸载 Gemma 4 再采样；解码用 `VAEDecodeTiled`。
11. RTX 4090 不下载 NVFP4 权重（只有 RTX 50 系有原生加速）；优先 int8_convrot / fp8_scaled；GGUF 只在装不下时用，它不提速。
12. 需要逐字对上现成配音时用 InfiniteTalk：`WanInfiniteTalkToVideo` length 81、motion_frame_count 9、6 步、CFG 1、25 fps，音频编码器 `wav2vec2-chinese-base_fp16`，配音先过 MelBandRoFormer；每多 3.24 s 复制一个 Extend 组并把上一段 IMAGE 接到 `previous_frames`。
13. 给 H3 已出的片段补口型或改配音，用 kijai 的 V2V InfiniteTalk（4 步、shift 11、start_step 2）；超过 1 分钟不挂 FusionX LoRA；音频 CFG 3–5，挂加速 LoRA 后用 2。
14. 打斗 / 舞蹈镜头改用 Wan‑Animate‑2：`wan_animate_2_int8_convrot`，832×480，81 帧一段，lcm 6 步，CFG 1，shift 5；text_1 只写「人物外观描述 + 背景描述」，动作写在 text_2；驱动视频先重采样到 16–24 fps 且景别与参考图一致；续接接 `continue_motion` 与 `video_frame_offset`。
15. 要保留原视频背景的换人用 SCAIL‑2 替换模式或 Wan 2.2 Animate（Mix）；MoCha 权重是 AGPL‑3.0，商用项目不用。
16. 需要可控运镜的无对白镜头：`WanCameraEmbedding`（Static / Pan 四向 / Zoom In·Out / 顺逆时针 + speed）接 `WanCameraImageToVideo`，模型用 `wan2.2_fun_camera_{high,low}_noise_14B_fp8_scaled`。
17. 单镜超过 15 s：有对白先对核心 `MiniMaxH3ContextWindows`（context_length 124、overlap 39，实验性节点）做同 seed A/B；无对白可用 Wan 2.2 + `SVI_v2_PRO_Wan2.2-I2V-A14B_{HIGH,LOW}_lora_rank_128`，每段换种子、锚点固定为首帧。
18. 段缝跳变但不想重生成整段时用 VACE Joiner：片段先降到 16 fps、分辨率取 16 的倍数，过渡帧生成后插帧回 24 fps，并接 `ColorMatch`。
19. 最后一跳超分：RelayVSR ×2（`relayvsr_x2_lightx2v_int8_convrot` + `relayvsr_flash_vae_x2_fp32`，1 步、CFG 1，ComfyUI ≥ 0.45，×2 与 ×4 权重不混用）；有对白的特写不用 SeedVR2；漫剧 / 远景可用 `Wan2_2-T2V-A14B-LOW` 4 步 denoise 0.25 精修。
20. 插帧用核心 `FrameInterpolationModelLoader` + `FrameInterpolate`，权重 `film_net_fp16` 或 `rife_v4.26` 放 `models/frame_interpolation/`（HF `Comfy-Org/frame_interpolation`）。
21. 分块长视频估时：窗口 W、重叠 C 时块数 = ⌈(总帧 − C) / (W − C)⌉，重叠区算两遍；LTX 官方 CLI 默认 W 97 / C 25，Wan 核心滑窗默认 W 81 / C 30，H3 核心滑窗默认 W 124 / C 39。
22. 报任何耗时都带齐口径：分辨率 × 帧数 × 步数 × 权重精度 × 硬件 × 首跑还是热跑；计时取 ComfyUI 服务端 `execution_start → execution_success`，复测必须换 seed。
23. 进商用管线前查许可：Wan 系 Apache‑2.0；LTX 需年营收 < 1000 万美元；HunyuanVideo 不适用于欧盟 / 英国 / 韩国；MoCha（AGPL）、SkyReels（skywork‑license）、Lynx 依赖的 InsightFace buffalo（非商用）先读原文。
24. 给「拼表式」参考（LTX Ingredients 或任何多元素参考图）排版：黑底、一个元素一个面板、不放文字、重要元素给更大的面板。
25. kijai WanVideoWrapper 只在原生没有对应功能时使用；启用 torch.compile 后每次更新节点，若首跑显存暴涨，先清 `C:\Users\<用户>\.triton` 与 `AppData\Local\Temp\torchinductor_<用户>`。

## 未覆盖

- **没有本机实跑**。所有耗时来自模板便签或作者自报；RTX 4090 上 LTX‑2.5（720p 5 s / 10 s）、Wan‑Animate‑2、SCAIL‑2、InfiniteTalk、SVI 2.0 Pro、Bernini‑R 的耗时与峰值显存没有找到带完整口径的公开数据。
- **质量对比空白**：H3 / LTX‑2.5 / Wan 2.2 的同分镜盲评、LTX‑2.5 中文对白与口型、Animate‑2 身份保持，都未验证；§7.3 的替补建议基于机制与官方能力描述，上线前需样片 A/B。
- 未读：Civitai / OpenArt / RunningHub 上的社区工作流，B 站 / YouTube / Reddit 实测帖；Wan 2.2 与 LTX 的风格 / 特效 LoRA 生态未盘点（「特效用 Wan + LoRA」这一条因此没有写进表里）。
- 只读了 README、未读推理源码的：SkyReels V3、MAGI‑1.1、Helios、Kandinsky 5 Pro、Capybara、Causal Forcing、WanMove / ATI、HunyuanVideo‑Avatar / Custom、Wan‑Dancer。LongCat‑Avatar 1.6（2026‑11‑15）与 Bernini 完整版（含规划器）的 ComfyUI 可用性未验证。
- KJNodes 仅用 2026‑10‑31 的旧克隆核对了节点名，未逐个读实现；VideoHelperSuite 与 Frame‑Interpolation 只读了 README。
- 一处未求证的矛盾：Lightricks 的 `LTX-2.5_ICLoRA_Union_Control_Distilled` 示例给 2.5 模型加载 2.3 的 union IC‑LoRA 文件，而 LTX‑2 README 写「LoRA 只对训练它的模型有效」。
- 云端 / 闭源模型（Wan 2.5–3.0、SkyReels V4、LTX API Fast / Pro、Seedance、Kling、Veo）归 03 簇；TTS / 音效 / 配乐 / 字幕归 04 簇；角色表与分镜生图归 05 簇；端到端 agent 流水线归 02 簇。
