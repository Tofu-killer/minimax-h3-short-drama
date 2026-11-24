# 14 · 官方生态索引的收尾：110 个没提过的仓库逐个过一遍（2026-11-23）

上一篇（`13-followup-2026-11-23.md`）留了一句「索引里其余一百来个仓库没有逐个确认」。这一篇把它做完：`MiniMax-AI/awesome-minimax-h3-integration` 里 293 个 GitHub 仓库中，本目录和 skill 都没提到过的 110 个，逐个取了仓库根目录（README 等顶层文件；`henjicc/Henji-AI` 克隆失败，没取到），按 README 分了类；和本地 ComfyUI + H3 视频有关的那一类读了全文，个别进了子目录。

**怎么读这张表**：「是什么」一栏里，写成中文整句的是读过之后的判断；只有一句英文或原文的，是 README 的第一句原话（没有往下读）。分类看的是 README 自己怎么说，没有运行任何一个仓库的代码。

## 结论

- 110 个里和「本地 ComfyUI 上用 H3 做剧」直接相关的只有 21 个，其中 7 个上一轮已读；这一轮新读的 14 个里，没有一个给出需要改动本流程默认做法的东西。
- 18 个是 H3-Image（出图模型）的周边——节点、提示词库、加速、Mac 端口。原生节点要 ComfyUI ≥ 0.45，用户的 0.37.2 用不上；升级之后再看。
- 其余 71 个是把 H3 当作一个云端供应商的应用、演示，或者只是「支持调用 H3」的网关与框架，和本地流程无关。

## 这一轮带回来的事实

| 事实 | 依据 | 去向 |
|------|------|------|
| NVFP4 的文本编码器在 4090 上是「模拟」运行：原生的 NVFP4 运算要显卡计算能力版本 ≥ 10（RTX 50 系），不够时 ComfyUI 仍按 NVFP4 存权重、用到时逐层解回计算精度。日志里 `emulated ops: nvfp4, mxfp8` 是正常的 | `neuregex/freefield` 的清单里写「NVFP4 的那个要 Blackwell」→ 去 0.37.2 源码核对：`comfy/model_management.py` 的 `supports_nvfp4_compute`（`props.major < 10` 返回 False）、`comfy/ops.py` 的 `get_disabled_quant_formats` 与加载时的 `_full_precision_mm = True`；`yilives/minimax-h3-v100-guide` 在 V100 上用这个文件实跑通过 | skill 的 `local-stack-and-acceleration.md` §5 第 9 条 |
| CUDA 低于 13 的 PyTorch 上，comfy-kitchen 禁用 cuda 后端，int8 / nvfp4 只省空间不提速 | `yilives/minimax-h3-v100-guide`（实跑记录）——和上一篇从 comfy-kitchen 源码读到的一致 | 已在 skill 里 |
| 不要给 ComfyUI 加 `--lowvram` / `--novram` / `--disable-dynamic-vram`；启动日志应有 `DynamicVRAM support detected and enabled` | 同上 | 与 skill 现有说法一致（`… patches attached.` 只在 DynamicVRAM 路径下出现） |
| H3 视频和 H3-Image 用的是同一种 `pruned` 剪法（`adaln_proj.linear` 的输入从 2688 剪到 8） | `iamwavecut/MiniMax-H3-Image-Pruned` 的说明；本项目在视频权重的文件头部见过同样的形状 | 只记在这里 |
| 同一张图同时当首帧和尾帧，可以把一个不动的场景稳住 | `gokayfem/H3-Max-Blender` | 与 skill「同图首尾 = 整镜静止」是同一件事；不新增规则 |
| 非人形主体不挂 LoRA 时 5 条里 2 条肢体颜色互换，自训 LoRA 后 0 条 | `patch-gg/anymove`（云端 H3 Max，作者自述） | 只记在这里：样本小，且不是本地权重 |

## 分类表

### 本地 ComfyUI / 权重 / 训练里和 H3 视频直接相关的（21 个）

| 仓库 | 是什么 |
|------|--------|
| `BobJohnson24/ComfyUI-INT8-Fast` | int8 加速节点的前身；作者说明 ComfyUI 已原生支持 int8，旧格式的量化文件用它的脚本转换。H3 不在它支持的模型里 |
| `ByteDance-Seed/VeOmni` | 分布式训练框架，列了 H3 |
| `DeepNeuralNerd/H3-Video-LoRA-Loader-for-Image` | 把 H3 视频 LoRA 过滤后挂到 H3-Image 上（去掉音频分支和输出层的条目）；给出两个模型输出层的形状差异（视频 `[96, 5376]`、出图 `[576, 5376]`）。结构对得上不等于效果能迁移 |
| `Klimentios/talemondo-studio` | Mac 上的制片工作室 + 远端 96 GB 显卡跑 ComfyUI 的 H3（BF16、24 步）；镜头预设编译成提示词、带 MCP 服务。PolyForm 非商用许可；硬件档位和本流程差得远 |
| `LIUFelix2004/God-minmax-H3` | 云端 API 的提示词库 + skill（5 条模板、分段与拼接流程）：接缝放在换气 / 转开视线处、每一段（含第一段）都给定妆图、上一段的音轨当音色参考——和本 skill 的规则一致；它用中文自然语言提示词加「不要出现…」，面向云端的改写器，不适用于本地权重 |
| `NVlabs/FastGen` | NVIDIA 的蒸馏框架，FastH3 / FastH3 Omni 的训练出处之一；带 ComfyUI 节点做师生对比推理 |
| `NVlabs/LongLive` | 上一轮已读：LongLive-Plug few-step / CFG 两个 LoRA，和 Turbo 二选一 |
| `Tencent-Hunyuan/UniRL` | 强化学习训练框架，列了 H3 |
| `WASasquatch/was-node-suite-comfyui` | 上一轮已读：36 个 H3 节点（局部重画、分段导演台、配乐、低显存、分块放大）。只读了文档和节点定义，没有执行 |
| `X-GenGroup/Flow-Factory` | 强化学习 / 离线微调框架，支持 H3 的 T2VA、FL2VA、Ref2VA LoRA（批大小 1、无 CFG）——训练侧，本流程用不到 |
| `aigc-apps/VideoX-Fun` | Fun ControlNet 的出处（姿态 / 深度 / 边缘驱动 H3）；ComfyUI 0.37.2 自带对应模板，skill 的节点表和生态地图里已有这条路 |
| `code-video-model/CodeVideoModel` | 上一轮已读：布局视频只在前 5/20 步当视频参考；这种接法在微型模型上执行过 |
| `hao-ai-lab/uniserve` | FastVideo 团队的推理服务；和本地 ComfyUI 无关 |
| `iamwavecut/ComfyUI-OrbitQuant` | WaveCut 的 OrbitQuant 量化模型（H3 是 W4A4）的 ComfyUI 节点：H3 要单独的 Python 环境和钉死的 Diffusers 版本，Ref2VA 只接一张参考图——不是原生节点那条路，和本流程（多参考 + 音色）不相干 |
| `jtydhr88/ComfyTV` | 上一轮已读：自带 h3-cinematic-director skill；它在提示词末尾加排除语，不照搬 |
| `kuhung/minimax-h3-colab-workflow` | 上一轮已读：L4（24 GB）上的实测耗时与显存，写进了基准表 |
| `neuregex/freefield` | 把一批创作应用做成「一个文件夹 = 清单 + API 工作流」，H3 用官方模板的 20 步、int8 文本编码器（它说 NVFP4 要 Blackwell——据 0.37.2 源码，那指的是原生运算，老显卡走模拟），在 H100 上峰值 48–50 GB；CI 用一台 CPU 的 ComfyUI 校验每个工作流，和本项目的做法一样 |
| `omnichar/OmniChar` | 上一轮只读了 README：角色打包成 .char 文件 + 连续性打分 |
| `radixark/miles_diffusion` | 训练 / 采样框架，列了 H3 |
| `thu-ml/TurboDiffusion` | 上一轮只读了 README：自带运行时，不走 ComfyUI 原生节点，只有首帧 / 首尾帧模式 |
| `yilives/minimax-h3-v100-guide` | Tesla V100 16 GB + 32 GB 内存的实跑记录：视频用 0.38.2、出图用 0.45.2 两套工作树；印证了「CUDA 低于 13 时 comfy-kitchen 禁用 cuda 后端，int8 / nvfp4 只省空间不提速」，并在 V100 上用 NVFP4 文本编码器跑通；提醒不要加 `--lowvram` / `--novram` / `--disable-dynamic-vram`，启动日志应有 `DynamicVRAM support detected and enabled` |

### H3-Image（出图模型；ComfyUI 原生节点要 ≥ 0.45，本流程的 0.37.2 用不上）（18 个）

| 仓库 | 是什么 |
|------|--------|
| `AI-KSK/minimax-h3-image-prompts` | H3-Image 的提示词 skill（按官方手册整理：先任务与布局、再局部；编辑时分清变与不变；多图逐张指定用途） |
| `Anionex/h3-image-mlx` | This banner was generated end to end with MiniMax H3 Image using H3 Image MLX. |
| `BeatAPI/awesome-minimax-h3-image-prompts` | Awesome MiniMax H3 Image Prompts |
| `BesianSherifaj-AI/h3-image-editor` | A local image and short-video editing workspace for ComfyUI, LM Studio and CPU tools. |
| `Hejunlong27/H3GIF` | 用 H3-Image 出分镜联络表再切成 GIF 的节点包 |
| `MrJackSpade/ImageGenerationServer` | A self-hosted, multi-user web front end for image generation, backed by a local ComfyUI |
| `SHoogstad/diffusion-for-krita` | Generative AI painting in Krita 5 and Krita 6 with diffusion models: inpaint, outpaint, refine, live painting, |
| `Timster666/comfyui-minimax-image` | ComfyUI + MiniMax-H3-Image — RunPod template |
| `animede/minimax-h3-image-server` | MiniMaxAI/MiniMax-H3-Image(33B、静止画生成 + |
| `devin-lai/MiniMax-H3-Image-Accel` | Run MiniMax-H3-Image on a single L20 or RTX 5090, or spread inference across multiple GPUs. The SGLang runtime supports native 4K generation and refer |
| `felix-ab/minimax-h3-image-mlx` | MiniMax-H3-Image for Apple Silicon. It does text-to-image and image |
| `iamwavecut/MiniMax-H3-Image-Pruned` | H3-Image 的剪枝做法说明：`adaln_proj.linear` 从 `[96768, 2688]` 剪到 `[96768, 8]`、时间嵌入压成查表——和 H3 视频的 `pruned` 文件是同一种剪法（本项目在文件头部见过同样的形状） |
| `jo-nike/h3-image-bench` | A gallery of 600 graded text-to-image prompts in two rounds (300 reused from a MOSS-Image benchmark, 300 written for this model) rendered with MiniMax |
| `pxyllvr/ComfyUI-H3Image-MediaLoader` | H3-Image 的 16 图参考加载器 |
| `ryoppippi/mmh3-studio` | A native and web studio for generating pictures with |
| `stepupgaming/styk-paint` | Film cameras and an AI set painter for Godot 4.7. |
| `tong-io/tongflow-modal-minimax-h3-image` | tongflow-modal-minimax-h3-image |
| `ukr8b3g-cmyk/H3-Character-Sheet-Designer` | H3-Image / P-H3 一张角色图出最多 13 个视图的角色板（3968×1024），含表情表；出的是合成板，按本 skill 的规则只给人审、不当参考 |

### 走云端 API 的做片、画布、分镜应用（把 H3 当一个供应商）（27 个）

| 仓库 | 是什么 |
|------|--------|
| `0xsline/StoryGen-Atelier` | AI-assisted storyboard and video generation tool. Uses Gemini for generating storyboard text and frames, Vertex AI Veo for generating transition clips |
| `ChatCut-Inc/agent-plugin` | ChatCut is an AI video editor for agents: an MCP server and plugin that lets Codex, ChatGPT, Claude Code, Cursor, Grok Bot, Gemini CLI, Google Antigra |
| `Finderchangchang/brewreel` | 给素材和简报，一条命令出宣传片 / 口播配画面 / 讲课视频；AI 画面走云端 H3，先估价、人批准才生成 |
| `HaD0Yun/CozyClay` | Make the scene first. Then make it a video. |
| `ItusiAI/Open-Magiviz` | 多模型的云端视频创作平台，H3 是可选模型之一（README 顶部是赞助商广告，不摘） |
| `Jjat00/hf-studio` | Your AI studio for video, image and audio. |
| `LudwigKienle/ai-video-production-editor` | An open-source, local-first film studio for AI video: script → director → storyboard → filming → edit → color → export, all on your own machine with y |
| `ThinkFlowLab/OpenDirector` | 本地运行、浏览器访问的做片工作台（对话生成、画布、时间线导出），生成走云端或自建的模型服务 |
| `darkzOGx/youtube-automation-agent` | The open-source AI agent that runs a YouTube channel end to end, with you approving every video before it goes out. |
| `ddcat-ai/open-ai-canvas` | 「影策」：上传小说 → 改编、拆集、建角色、出分镜、逐段生成并合成的短剧工作台（云端模型） |
| `eren23/openflipbook` | Explore illustrated worlds. Keep the places you create. Start with a map or a prompt, enter a place, and return to its saved view. Edit names and cano |
| `fancyboi999/Loomic` | Open-source alternative to Lovart / CapCut Video Studio / Canva AI |
| `ganbo-gab/open-storyboard-canvas` | 本地桌面的分镜画布：三维预演台摆人物走位 → 拍四视图 → 送回节点画布；带 ComfyUI 连接与依赖预检。三维预演这一步和上一篇记的「布局视频」思路相近 |
| `glanderness/BeefTV` | 画布式的视频创作工作台（智能体 + skills + 工作流），云端模型 |
| `gooseworks-ai/goose-skills` | Put your AI agent on the growth team. |
| `henjicc/Henji-AI` | （README 没取到） |
| `ilkerzg/storycast` | Pick a character, give it a topic, and get back a narrated animated film, made end to end on fal. |
| `makevoid/motion-graphics-music-video-skill` | Motion graphics music video plugin |
| `marketcalls/sketchmaker` | Sketchmaker: Self-Hosted, Open-Source AI Studio for Video and Images |
| `openstory-so/openstory` | An open-source AI film studio that runs on your own machine. |
| `orkunisitmak/banana-studio` | From a rough idea to images, YouTube thumbnails and video.An open source creative workspace, powered by your own API keys. |
| `saihhold-zhao/polox_ai` | PoloX AI — Agent-Powered Multimodal Creation Workbench |
| `sumarilkkxx/Mora` | （Multimodal Orchestration for Retail Automation） |
| `thezolon/tiiny-studio` | A local media studio for the Tiiny Pocket, a pocket-sized device that runs AI models on |
| `tryonlabs/opentryon` | Open-source AI toolkit for fashion technology: virtual try-on, image/video generation & editing, multimodal understanding, background removal, preproc |
| `xixihhhh/clipforge` | ClipForge — 开源 AI 带货短视频神器 ｜ 一张商品图，自动出卖货视频 |
| `zenstory-ai/oh-story-dsh` | 为 DeepSeek Harness 打造的小说、短剧、互动游戏与视频解说创作工作台 |

### 演示、游戏、3D 与其他创作实验（13 个）

| 仓库 | 是什么 |
|------|--------|
| `OpenDCAI/GameFactory-3A` | 📚 New reports coming soon — we will soon open-source several new reports. |
| `RachelForster/Shinsekai` | 面向 Galgame / 乙女 / 剧情向 RPG 的开源桌面伙伴与交互演出平台：由大语言模型驱动角色对白与剧情演出，结合 多形态形象（静态 / 动态立绘、MMD、Live2D）、服装分组与情绪联动、语音合成与口型同步、长期记忆与资料检索、实时屏幕感知、桌面智能助手 与 插件 / MCP 扩展——在 |
| `Valiera00/SPITE` | Built out of spite. Made for control. |
| `WhiteTowerAI/ohmygame` | The open-source studio for making games with AI. |
| `blendi-remade/falcraft` | 🎨 falcraft - AI-Powered 3D Generation for Minecraft |
| `blendi-remade/interdimensional-game` | A playable film. Every shot is generated as you watch, and the video |
| `blendi-remade/prompt2rig` | @patch_gg · FLUX 3 Max or H3 Max Turbo video · GVHMR body · WiLoR fingers · Apache-2.0 code. |
| `blendi-remade/unreel` | Endless television. Written and rendered while you watch. |
| `gokayfem/H3-Max-Blender` | Blender 灰模 → 云端 H3 Max 上色的演示；一个做法值得记：同一张图同时当首帧和尾帧来稳住不动的场景——和本 skill「同图首尾 = 整镜静止」的结论是一回事的两面 |
| `gokayfem/h3-max-education` | Realtime, interruptible science tutoring with continuously generated H3 Max teaching videos. |
| `lovisdotio/video-to-game` | A skill that teaches coding agents to turn a gameplay video into a real game you can play in the browser. |
| `patch-gg/anymove` | 用云端 H3 拍「正面 + 侧面同框」的生物视频再反求骨骼动画；数据点：不挂 LoRA 时 5 条里 2 条肢体颜色互换，挂了自训 LoRA（1,200 步）0 条 |
| `xflare-bot/pokemonlive` | Choose a move. Watch the battle come to life. |

### 模型网关、推理框架、通用智能体平台（只是支持调用 H3）（31 个）

| 仓库 | 是什么 |
|------|--------|
| `1CatAI/1Cat-vLLM` | Modern LLM inference for NVIDIA Tesla V100 / SM70 |
| `1Panel-dev/MaxKB` | Open-source platform for building enterprise-grade agents |
| `Agent-Field/agentfield` | Build agents like APIs. Run ten thousand of them like microservices. |
| `BerriAI/litellm` | Open Source AI Gateway for 100+ LLMs. Self-hosted. Enterprise-ready. Call any LLM in OpenAI format. |
| `Devin-AXIS/iPolloWork` | An enterprise collaboration platform for people and AI agents, built on the open-source DeepSeek Harness. |
| `Neywa-Labs/mlx-vlm` | Run and fine-tune multimodal models on Apple Silicon. Text, images, video, and audio in — any out. Built on MLX. |
| `OctaFuse/octafuse-gateway` | Octafuse Gateway 是面向 Agent 的可自托管开源 AI 网关。它将不同供应商的文本、图像、语音与工具能力汇聚到统一入口，支持 Chat Completions、OpenAI Responses API、图像生成与编辑、ASR、TTS、实时语音和智能体工具（Agent Tools） |
| `Sociaro-Research/open-media-gateway` | One API. One key. AI media across providers. |
| `THU-MAIC/OpenMAIC` | Get an immersive, multi-agent learning experience in just one click |
| `TeamWiseFlow/xiaobei` | 🎉 5.8.2 版本已发布，基于openclaw 2026.10 LTS版本并精简插件，更轻、更稳定！ |
| `ZMGID/kivio` | macOS / Windows 屏幕级 AI 助手：Agent 客户端，加上翻译、截图 OCR 与视觉问答 |
| `agentjido/req_llm` | Join the community! Come chat about building AI tools with Elixir and coding Elixir with LLMs in The Swarm: Elixir AI Collective Discord server. |
| `agentscope-ai/QwenPaw` | [Documentation] [中文] [日本語] [Русский] |
| `chaitin/MonkeyCode` | 百智办公是一款面向团队的开源 AI 办公工作台。用自然语言提出需求，让 AI 完成办公、编程与设计任务，直接交付工作成果。支持团队资源共享、统一管控与私有化部署。 |
| `corsairdev/corsair` | Corsair: Connect your users to their apps |
| `crmne/ruby_llm` | Build AI features the Ruby way: models, tools, agents, evaluations, and Rails conventions, designed together, with one consistent API. |
| `drawthingsai/draw-things-community` | This is a community repository that maintains public-facing code that runs the Draw Things app. |
| `gufo-org/gufo` | Gufo: The *Open Source* Strix Halo AI engine |
| `langgenius/dify-official-plugins` | <img src="https://img.shields.io/discord/1082486657678311454?logo=discord&labelColor=%20%235462eb&logoColor=%20%23f5f5f5&color=%20%235462eb" |
| `localai-org/vllm.cpp` | Same tokens as vLLM. Same throughput. 140x less to install. |
| `maximhq/bifrost` | <img src="https://run.pstmn.io/button.svg" alt="Run In Postman" style="width: 95px; height: 21px;" |
| `monid-ai/monid` | Tool catalog &nbsp;&middot;&nbsp; |
| `mudler/LocalAI` | LocalAI runs open models for chat, images, speech and video on your own machines. The API speaks the OpenAI and Anthropic formats. Your team gets chat |
| `openJiuwen-ai/jiuwenswarm` | Understands Your Intent, Evolves Autonomously — Swarm Collaboration for Complex Tasks |
| `pollinations/pollinations` | Open-source AI for people who make things. |
| `rikkahub/rikkahub` | A native Android LLM chat client that supports switching between different providers for |
| `s-nagaev/chibi` | Your Digital Companion. Not a Tool. A Partner. |
| `saddam213/AmuseAI` | Local AI image, video, audio and text. |
| `siddsachar/row-bot` | Row-Bot is a local-first desktop AI assistant for doing real work with models, |
| `yetone/magpie` | Every agent's model. One place. |
| `ztxz16/fastllm` | FastLLM 是用于本地运行和服务部署的大模型推理引擎，支持语言模型、图片生成和视频生成。核心运行时使用 C++，不依赖 PyTorch；支持稠密与 MoE 模型、GPU/CPU/NUMA/磁盘混合推理，以及多卡部署。 |

## 索引之外：同一轮网上检索到的

2026-11-24 另用网页检索找了一遍近期的 H3 + ComfyUI 项目，结果里只有一个仓库是本目录没提过的：

| 仓库 | 是什么 | 对本流程的意义 |
|------|--------|----------------|
| `HM-RunningHub/ComfyUI_RH_MinMaxH3` | RunningHub 维护的一整套 H3 运行时节点（`RHMiniMaxH3*`），改编自 MiniMax 发布的源码包，Apache-2.0；T2VA / FL2VA / Ref2VA 都有，自带按层卸载和 adaLN 预计算，面向 24 GB 单卡。**不走 ComfyUI 的原生节点**：权重是另一套文件名和目录（`models/MiniMax-H3/…`，INT8 版在 HF 的 `Gluttony10/MiniMax-H3-INT8-CONVROT`），工作流也是它自己的 | 和本 skill 的原生节点路线是两套东西，权重和工作流都不通用，不要混装着用。README 里有一组数据可作旁证：不挂蒸馏 LoRA 时，`res_multistep` 约 21 个 sigma 点（20 次 DiT）与 50 点 Euler 同 seed 下看不出差别，832×480 × 125 帧的采样时间 101 s 对 249 s——和本流程「关 Turbo 时 20 步 `res_multistep`」的取法一致。它重申的两条也和本 skill 的规则相同：关键帧占时间轴上的真实帧位、必须和画布同尺寸，参考图没有帧位、可以用自己的分辨率；参考上限 9 图 / 3 视频 / 3 音频、合计 12 |

检索到的其余条目（官方模板与教程、`xiaolibai-sys`、`LeonQ8` 的一体化节点、Spectrum、`BennyDaBall` / `RuneXX` 的工作流集、`pottokao` 的 RotNVFP4 加载器、长视频工作流、vLLM-Omni 集成、`open-h3-ir`）都已在本目录里。上游也核对过：`lightx2v/Minimax-h3-Turbo` 自 2026-11-16 起没有新文件，ComfyUI 最新的 tag 仍是 v0.46.2。

## 2026-11-24 上游复查

逐个看了本流程依赖的上游仓库的最新提交（浅克隆只取提交记录）。没有新提交的：两个生态索引（`MiniMax-AI/awesome-minimax-h3-integration` 停在 11-12，`wildminder/awesome-minimax-H3` 停在 11-16）、`tazmannner/ComfyUI-H3-ResCascade`（10-24）、`LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler`（11-10）、`MiniMax-AI/MiniMax-H3`（10-28）、`ModelTC/Minimax-H3-Turbo`（08-27）、`nkxx188/ComfyUI-MiniMaxH3-Easy`（11-13）、`seesee75-commits/ComfyUI-MiniMaxH3-Director`（11-03）、`HM-RunningHub/ComfyUI_RH_MinMaxH3`（08-06）、`Kosinkadink/ComfyUI-VideoHelperSuite`（09-01）；ComfyUI 最新的 tag 仍是 v0.46.2。有新内容的两处：

### 官方模板库：H3-Image「换角色」（`Comfy-Org/workflow_templates` #1451，2026-11-23）

- 新模板 `image_minimax_h3_image_character_swap`（`minComfyUIVersion` 0.45.0）：把照片里的人换成参考图里的角色，姿势、景别、光照跟源图，脸、服装、材质跟参考。18 个节点，全是原生节点：`UNETLoader`（`minimax_h3_image_pruned_int8_convrot`）→ `LoadLoraModel`（`h3_image_character_swap_v1.safetensors` 1.0）→ `KSampler` 6 步 CFG 1 euler / simple；`MiniMaxH3ImageConditioning` 的 `images.image_0` 接缩过的源图、`images.image_1` 接角色参考，宽高取自源图；负向是 `ConditioningZeroOut`。源图先 `scale total pixels` 到 1 MP，再 `scale to multiple` 32。模板默认的文本编码器是 `qwen3vl_32b_minimax_h3_int8_convrot`（27.1 GB）；作者模型卡用的是 `…_nvfp4_awq`。
- LoRA 在 `akatz-ai/MiniMax-H3-Image-Character-Swap-LoRA`（2026-11-20 建仓）：155,110,448 字节，SHA-256 `68378574bede5ca9d7d69df8bb8f8d9f7860d07ea45b26d9c67a7babf50d330f`（HF 接口与模型卡一致）；rank 16，AI Toolkit 训练，最后一阶段 140 对、18 个验证例；作者在 ComfyUI 0.45.0、RTX 4090（dynamic VRAM）上测，只评过 int8_convrot 底模、约 1 MP；「只用于人和类人角色；小的或被遮挡的人、手靠近道具、衣服和背景颜色接近时要检查；可能留下原来的衣服、改动目标周围、选错人」（模型卡原话的意思）。对比图是挑过的例子，没有量化。
- `Comfy-Org/MiniMax-H3-Image` 在 11-24 的文件：DiT `…_pruned_int8_convrot` 20.98 GB、`…_pruned_bf16` 40.23 GB、`…_pruned_w4a8` 12.55 GB；文本编码器 `qwen3vl_32b_minimax_h3_nvfp4_awq`（15.69 GB，SHA-256 与 `Comfy-Org/MiniMax-H3` 里那一个相同——已经装了 H3 的机器不用再下）、`…_int8_convrot` 27.14 GB、提示词扩写 `qwen3.8_27b_minimax_h3_image_pe_w4a8_gptq` 17.29 GB、`qwen3.5_9b_w4a8_gptq` 7.34 GB；VAE 1.17 GB。仓库说明现在列三个官方模板：Image Edit、Text to Image、Character Swap。
- **许可全文读了**（LoRA 仓库带的 LICENSE 与 `MiniMaxAI/MiniMax-H3-Image` 的逐字节相同，18,208 字节）：许可日期 2026-11-10；适用地域 = 全球，除去欧盟、英国、韩国、美国（澳洲在内）；§V.4 输出也不得在排除地区使用、展示或分发；§V.3 输出不得用来改进别的 AI 模型；§IV 年化营收超过 100 万美元或对第三方提供托管服务要另行书面授权，商用产品界面要醒目显示 “MiniMax-H3-Image”；附件 A 第 12 条：往公共环境发布要醒目标明是机器生成的；适用香港法律。不是法律意见。
- 进了 skill：`references/image-stage.md` §1 多一行和一条「什么时候用」，`assets/image-prompts.md` §13 是两句作者原句。没有在显卡上跑过。

### KJNodes（`kijai/ComfyUI-KJNodes`，1.5.5 之后到 2026-11-23）

- `MiniMax H3 Prompt Weight` 多了两个视频模式（11-18）：`edit video` 包的是 `MiniMaxH3ReferenceToVideo`（参考图最多 9、参考视频 3、参考视频的声音 3、参考音频 3，`ref_image_size` match / max，宽高填 0 时按 1344×768，帧数吸附到 17k+5），`first last frame` 包的是 `MiniMaxH3ImageToVideo`（首帧、尾帧）；两个模式都有 `start_percent` / `end_percent`，范围之外提示词不带参考重新编码。11-13 起还支持 `[cat|fox:-1]` 式的提示词混合。
- 它的 `execute` 第一行是 `from comfy_extras.nodes_minimax_h3 import MiniMaxH3ImageConditioning, MiniMaxH3ReferenceToVideo, MiniMaxH3ImageToVideo`。**在真实的 ComfyUI 0.37.2 上**：节点注册得上（`/object_info` 里有，界面里搜得到），但这条 import 报 `ImportError: cannot import name 'MiniMaxH3ImageConditioning'`——0.37.2 的 `nodes_minimax_h3.py` 只有视频那几个节点。所以用户现在的 0.37.2 用不了它，要 ≥ 0.45。SKILL.md 铁律 2 里的说法照此改了。
- `Skip DiT Blocks KJ`（11-23，实验节点）：按序号整块跳过 transformer block，靠 ComfyUI 的 DiT block replace 补丁；说明里列的支持模型是 Flux、Chroma、Wan、LTX、Qwen-Image、HunyuanVideo、SD3、Kandinsky5「等」，没有点名 H3，跳不到的块只记一条警告。没有试，不进流程。
- 其余：`Get Workflow KJ`（把工作流取成字符串）、支持 H3-Image 的 tiny VAE（11-15）、几处重采样提速——和本流程无关。

### ComfyUI 主仓库与模型仓库

- `Comfy-Org/ComfyUI` 主干最近 120 个提交（2026-11-06 起）里和 H3 有关的：11-10 支持 MiniMax-H3-Image（已知，≥ 0.45）；11-19 加了 `ModelMergeMiniMaxH3`（按块合并两份 H3 权重的节点，本流程用不到）；11-20 合作方节点加了 Creatify Boreal-H3（云端）；11-23 把模板包升到 0.11.118（带上面那个换角色模板）。`nodes_minimax_h3.py` 里视频那几个节点没有改动。
- HuggingFace 上本流程用到的仓库的最后修改时间：`lightx2v/Minimax-h3-Turbo` 11-16、`Comfy-Org/MiniMax-H3` 11-15（那次只是加 Pika 模板的链接）、`LBH-123-AI/Minimax_h3_latent_Upscaler` 11-10、`Kijai/MiniMax-H3-experimental` 11-09——`models.json` 里的文件名、大小、哈希都还对得上。

### 官方模板里的 H3 一族（35 个）和配乐模型

- `Comfy-Org/workflow_templates` 在 2026-11-24 有 35 个名字里带 minimax / h3 的模板。`api_` 开头的 16 个是合作方云端接口（H3 Max 的换演员 Recast、改画幅 Reframe、运镜、对口型，H3-Image 的云端版，Pika H3 Flex 云端版等），按量付费、不在本地跑；本地的是 `video_` 12 个（H3 6、Pika H3 Flex 3、FastH3 3）、`image_` 6 个、`audio_minimax_music_3` 1 个。本地的 19 个里，除 `image_minimax_h3_image_t2i`、Pika 的 `fl2va` / `t2v` 两个和配乐那一个之外，本目录之前都读过，这四个里只有配乐那个带来新东西；`api_` 的 16 个之前只按产品（H3 Max、Pika H3 Flex 等）写过，这次也只读了索引里的说明，没有逐个打开。
- **ComfyUI 0.37.2 就有两套本地文生音乐节点**（在真实的 0.37.2 上查的 `/object_info`，自带的模板包 0.11.69 里也有对应模板）：`TextEncodeAceStepAudio1.5`（模板 `audio_ace_step1_5_xl_turbo`）和 `MiniMaxMusic3TextEncode`（模板 `audio_minimax_music_3`）。
- **ACE-Step 1.5 XL turbo**（MIT）：`UNETLoader(acestep_v1.5_xl_turbo_bf16)` → `ModelSamplingAuraFlow(3)`，`DualCLIPLoader(qwen_0.6b_ace15, qwen_4b_ace15, type ace)`，`TextEncodeAceStepAudio1.5(tags, lyrics, seed, bpm, duration, timesignature, language, keyscale, generate_audio_codes=true, cfg_scale 2, temperature 0.85, top_p 0.9)`，`EmptyAceStep1.5LatentAudio(seconds)`，KSampler 8 步 CFG 1 euler / simple。文件在 `Comfy-Org/ACE-Step-1.5`（旧名 `ace_step_1.5_ComfyUI_files`，HuggingFace 会转）：9.97 + 1.19 + 8.38 + 0.34 = 19.9 GB，四个下载链接逐个试过，大小和 SHA-256 与接口返回一致。纯器乐的写法是歌词填 `[Instrumental]`（上游 `docs/en/INFERENCE.md`、`cli.py`）；上游文档：caption 最多 512 字符，时长 10–600 s，BPM 30–300，人声语言 `unknown` = 自动。
- **MiniMax Music 3**（2026-08-07 开放，`MiniMaxAI/MiniMax-Music3`）：8B 的全局语言模型 + 0.6B 的局部语言模型 + 2.4B flow matching，32 kHz 立体声，最长 5 分钟；输入是歌词（段落标签 `[Intro]` `[Verse]` `[Chorus]` `[Instrumental]` 等）加三段式描述（Global Metadata / Vocal Details / Arrangement）。ComfyUI 版在 `Comfy-Org/MiniMax-Music-3`：DiT fp16 4.91 GB（int8 2.50 GB）、文本编码器 pruned int8 9.20 GB、VAE 0.22 GB；模板 30 步 CFG 1.7，`max_duration` 是上限（节点说明：模型可以提前结束）。许可是 MiniMax-Music3 Community License（读了原文）：MIT 式授权加商用条款——商用产品界面显示 “MiniMax-Music3”，年收入超过 2000 万美元另行授权；没有地域条款。`Comfy-Org` 那个仓库的卡片标成 apache-2.0，以原仓库的 LICENSE 为准。
- **结论**：垫在对白下面、长度要和成片一致的器乐配乐用 ACE-Step 1.5（时长、BPM、调都是显式入参）；带歌词的主题曲才考虑 Music 3。两个都没有在显卡上跑过。
- **进了 skill**：`assets/workflows/acestep15_music.api.json`（从 0.37.2 自带的模板经真实前端导出；歌词默认 `[Instrumental]`、时长只填一处、输出 flac），`models.json` 多一组 `music`，`comfy_submit.py` 的预览列出时长 / BPM / 调 / 描述并拦下空描述，`project_status.py` 在剪辑齐了之后给出配乐命令。真实的 0.37.2 接受了这份工作流（29 种用法全过）；用同一个保存节点的无模型工作流验证了音频结果能取回到片段文件夹。
- **顺带补的一处「悄悄走错」**：混音之后再加配乐、换配乐文件（同名）、调电平，或者字幕重新对时，原来的检查都只看剪辑点和片段，成片会被当成最新的。现在混音报告记下声音部分的指纹和烧进去的字幕文件，`project_status.py` 和带混音轨的导出会指出来。

## 仍未读

表里只引了 README 第一句的仓库没有往下读。`henjicc/Henji-AI` 没克隆下来。H3-Image 那一类等用户把 ComfyUI 升到 0.45 以上、要用这个出图模型时再读。
