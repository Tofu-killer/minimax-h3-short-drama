# Agent 提示词 · 映射并接管本地 H3 短剧流程

> 用途：在 `01-local-inventory.md` 产出清单之后使用。本提示词已针对一台具体机器（RTX 4090 24GB、ComfyUI 0.37.2、H3 int8 开源权重、闲兔导演台等）定制；换环境时请按自己的清单改写「已知事实」一节。

```
目标：接管我本地的 MiniMax H3 短剧制作流程。最终状态是：我给你一段剧本和角色资产，你能在不问我的情况下产出带对白音轨、分镜连贯、角色一致的成片。参考资料仓库：https://github.com/Tofu-killer/minimax-h3-short-drama （先 clone 到本地）。

## 已知事实（来自我昨天的环境清单，不要重复盘点，直接用）
硬件：Windows 11，RTX 4090 24GB，64GB 内存，E 盘 618GB 空闲。
ComfyUI：E:\AI\ComfyUI_seller_test\comfyui，0.37.2，闲兔启动器起在 8188；另有 Start-Seller-Test.ps1 起在 8190 并加载 E:\AI\ComfyUI_seller_test\shared-models.yaml。两套不要同时跑。
H3 权重：fl2va 与 ref2va 均为 int8 convrot（各 19.5GB），文本编码器 qwen3vl_32b nvfp4_awq（14.6GB），video_vae int8、audio_vae fp32，LoRA：fl2v_turbo_8step、ref2v_turbo_4step，latent 超分 h3_upscaler_lms_v0.1，预览 taeh3。打戏/速度类 LoRA 全部缺失，忽略它们。
H3 节点：核心 nodes_minimax_h3.py（EmptyMiniMaxH3LatentAV、MiniMaxH3ImageToVideo、MiniMaxH3ReferenceToVideo 9图/3视频/3音频、MiniMaxH3AddGuide、MiniMaxH3SigmaShift）；ComfyUI-H3-Multishot（H3RefBatch、H3AutoRefs、H3ReferenceAudio、H3ConcatAV、H3EpisodeSplit、H3LastFrame、JoyEcho LLMEnhance）；ComfyUI_MiniMaxH3_Director（提示词增强可接 Ollama）；minimax-h3-chunk-star7（ActivationChunkStar7 省显存）；comfyui-SelfLift（双采）；ComfyUI-Xiantu-QwenImage21-Workbench 的 XiantuVideoEditorWorkbench 导演台（多分镜、续接重叠 22 帧、自动合并）；KJNodes 的 MiniMaxH3MemoryEfficientSageAttentionPatch、MiniMaxH3TokenCounter；VHS；SeedVR2；XB_ToolBox（CosyVoice3、XB_llamaMiniMaxRef2va、StoryboardEnhancer 本地 GGUF LLM）；ComfyUI-GGUF-Qwen3VL-TE。
已验证工作流（全部 UI 格式，位于 comfyui\user\default\workflows）：
- 视频/01-图片生成视频-H3.json：I2V，fl2va + turbo 8step，4 步 res_multistep，默认 0.3MP 2 秒
- 视频/首尾帧生视频-H3-FL2VA-短样例.json：FL2V
- 视频/02-H3多分镜导演台-干净示例.json：ref2va + 导演台，448×672，每镜 5 秒，ManualSigmas 1,0.9375,0.8333,0.625,0 + er_sde，ref2v_turbo_4step，ActivationChunkStar7；此前已通过 /prompt 接口提交成功
- 视频/04-H3双采-短片适配版.json：SelfLiftH3Sampler + SigmaShift 视频 12 / 音频 3，euler beta 10 步
- 视频/03-视频高清放大-SeedVR2-已验证.json：SeedVR2 3B fp8，目标短边 704
- 图片：人物多视角参考-Qwen、自动换装-Qwen参考图、02-人物姿势参考、三图参考编辑-Klein4B、文生图-QwenImage2.1-NoctQ
- 工具：五路视频对照拼接、本地提示词/01 扩写与翻译、02 视频提示词扩写
实测上限：单镜 1344×768 或 1376×768（约 1MP）、最长 10 秒、24fps、带 AAC 音轨；导演台 3 镜 × 5 秒合并 15 秒已验证。核心节点训练范围 124–362 帧（约 5–15 秒）。
已有项目：三角洲漫剧《第1集-蜂医的复仇》粗剪 68.5 秒（横屏 1344×768）。资产在 E:\AI\素材\三角洲素材\三角洲素材————\：干员图 48 张、场景图 2069 张、物品 1683 张、按干员分目录的语音 wav 2116 条、音效 754 条。
LLM：Ollama 便携版（E:\AI\Ollama_seller，qwen3-vl:4b）、XB_llama 可加载 qwen3vl_8b_heretic Q4_K_M GGUF、models\prompt_generator 下 Qwen3-VL-8B-Instruct BF16。没有任何在线 API key，也没有 MiniMax 云端 key。
工具：ffmpeg 7.1 在 imageio_ffmpeg 包内，没有 ffprobe；没有插帧模型；没有字幕节点。
已知失败：双人对口型（InfiniteTalk Multi）多轮失败；参考音频 / 参考视频从未测过。

## 总体策略（已替你决定，照做）
1. 主生产路线：ref2va 多参考 + 官方六段式提示词，一个「分镜段落」= 一次生成（5–15 秒，内含 1–3 个子镜头），这是仓库 docs/03 的核心做法，也正好对应你本地 02 工作流的能力。关键脸部镜头用 fl2va 首帧路线（01 工作流）。
2. 提示词不依赖 LLM 改写：云端有 Context-IR，本地没有。仓库的 pipeline/prompt_builder.py 能从分镜 JSON 直接确定性地生成官方三段式/六段式提示词（格式来自 MiniMax 官方 skills/h3-prompt-writing/references/ref-en.txt 与 base-en.txt），这正是开源权重 README 要求自建的那一层。LLM 只用在「剧本 → 分镜 JSON」这一步，而且在视频生成之前单独跑完，避免和 H3 抢显存。
3. 分辨率：原生 768 短边出片（横屏 1344×768 沿用现有项目；竖屏则 768×1344 或 768×1376，宽高需为 16 的倍数），成片再用 SeedVR2 放大到 1080p。不追求 2K，本地没有 2K 重生成。
4. 一致性：角色用 2–3 张干员图（正面 + 全身）作 reference_image，场景图 1 张，道具白底图按需；每段复用同一组参考与同一句英文识别短语；段落间用 H3LastFrame 抽尾帧作下一段首帧，或用导演台的续接重叠。
5. 对白：全部交给 H3 原生音频，严格一镜一人开口；音色用干员语音 wav 作 reference_audio（需要先测）。不再碰 InfiniteTalk 多人。
6. 编排：Python 脚本通过 ComfyUI HTTP API（POST /prompt、GET /history/{id}、GET /view）驱动 API 格式工作流；并发固定为 1。

## 第一阶段：读仓库并产出映射表（约 1 小时，只读）
读 README.md、docs/03-production-workflow.md、docs/04-prompt-engineering.md、docs/05-consistency.md、docs/06-case-studies.md（重点「ComfyUI 生态」与 MiniMax-H3-Codex-Drama）、pipeline/ 全部代码、pipeline/prompts/、templates/。
输出《映射表》：仓库每个阶段 → 我的哪个工作流 / 节点 → 缺口 → 补齐方案。至少覆盖：剧本改写、资产提取、定妆图（→ Qwen 多视角 / 换装 / Klein 三图）、分镜拆解（→ 本地 LLM + 仓库 02_storyboard_system.md）、首帧图、提示词（→ prompt_builder，无 LLM）、生成（→ 02 导演台 或 自建核心节点工作流）、音色参考（→ H3ReferenceAudio，未验证）、超分（→ SeedVR2 / h3 latent 超分）、拼接（→ H3ConcatAV / VHS / ffmpeg）、字幕（→ 仓库 stitch.py 的 SRT + ffmpeg subtitles 滤镜）、QC（→ 仓库 stitch.py 的 ffprobe 检查，需先补 ffprobe）。

## 第二阶段：准备 ComfyUI 与 API 格式工作流
0. 启动 ComfyUI：优先用闲兔启动器的 8188 实例（如果它不加载 shared-models.yaml 导致模型找不到，改用 Start-Seller-Test.ps1 的 8190 实例，二选一）。GET /system_stats 与 /object_info 确认上节列出的 H3 节点全部存在，把 /object_info 保存到 pipeline/local/object_info.json 备查。
1. 导出 API 格式：在前端分别打开 02 导演台、01 图生视频、首尾帧样例、03 SeedVR2，用「导出（API）」另存为 pipeline/local/workflows/*.api.json。不要自己写脚本转换 UI 格式（子图、SetNode/GetNode、旁路节点会出错）。如果前端操作必须由我来做，把精确步骤写给我，我来导出。
2. 原样回放：把导出的 02 API JSON 不改任何参数 POST 到 /prompt，确认能出片。读懂 XiantuVideoEditorWorkbench 节点 widgets_values 里那段 JSON 的结构（分镜数组、每镜素材、提示词、模式、时长、续接重叠），写一个 patch 函数能替换分镜列表。
2b. 导演台的程序化入口：ComfyUI_MiniMaxH3_Director 支持「导演包」`*.mmxpack.zip`（pack.json + shared_params/shared_params.json + asset_groups/NN/group.json + Picture1..9 / Audio1..3 / start.jpg / end.jpg；timeline.json 可省略）。读该插件 README 的导演包一节，写一个 storyboard JSON → mmxpack 的转换函数；这比修改 Xiantu Workbench 的 JSON 字串稳得多，优先评估它能否作为主路线。段间引导上下文帧数用 22。
3. 自建最小工作流（备选，比导演台的 JSON 字符串更稳）：用核心节点搭 h3_segment_ref2va.api.json：UNETLoader(ref2va int8) → LoraLoaderModelOnly(ref2v_turbo_4step, 1.0) → MiniMaxH3MemoryEfficientSageAttentionPatch 或 ActivationChunkStar7 → CLIPLoader(qwen3vl nvfp4) → CLIPTextEncode → H3RefBatch(≤9 图) + H3ReferenceAudio(≤3) → MiniMaxH3ReferenceToVideo → EmptyMiniMaxH3LatentAV(宽/高/帧数) → SamplerCustomAdvanced(er_sde + ManualSigmas 1,0.9375,0.8333,0.625,0，照搬 02) → VAEDecode 视频 + 音频 → CreateVideo/SaveVideo 带音轨。再搭 h3_segment_i2va.api.json（fl2va + fl2v_turbo_8step，照搬 01 的 4 步 res_multistep）。帧数按 17k+5 网格、24fps 换算。每个工作流在 pipeline/local/workflows/README.md 里记录每个可改输入的节点 id 与字段名。
4. 补工具：安装带 ffprobe 的 ffmpeg（winget install Gyan.FFmpeg 或下载 gyan full build，<1GB），确认 ffmpeg 含 libass（字幕烧录需要）。

## 第三阶段：逐项实测，每项通过才进下一项（每次只跑一个任务）
测试用提示词全部用仓库 templates/six-part-ref2va.md 的格式，参考图用三角洲干员图。每次记录：分辨率、时长、步数、生成耗时、显存峰值（nvidia-smi 轮询）、输出路径、通过/失败与原因，写进 pipeline/local/test-log.md。
T1 基线：ref2va，1344×768（或竖屏 768×1344），5 秒，1 个角色 2 张参考图，1 句中文台词。看画面、听台词是否为中文且口型同步。
T2 时长：同设置拉到 10 秒，再 15 秒（362 帧）。记录 24GB 能到多少；爆显存就加 ActivationChunkStar7 或降到 10 秒作为上限。
T3 多镜头：一段 12 秒内写 3 个 [Shot N] At MM:SS.mmm 切镜，两个角色分别在不同镜头开口。检查切镜是否发生、是否错人开口。这就是官方的「多说话人」做法。
T4 音色参考：加 1 段 5–10 秒的干员语音 wav 作 reference_audio，提示词写「<Audio 1> is the voice-timbre reference for <Subject 1> (S1)」，对比 T1 音色是否迁移。失败则记录为缺口，回退纯文字描述声音。
T5 首帧路线：fl2va，用 Qwen 多视角工作流生成的角色静帧作首帧，6 秒，1 句台词。检查首帧保真。
T6 段落衔接：T3 结果用 H3LastFrame 抽尾帧 → 作 T5 路线的首帧生成下一段；另试导演台续接重叠 22 帧；比较哪种衔接更自然，选一种作默认。
T7 放大：T1 结果分别过 SeedVR2（目标短边改 1080）和 h3_upscaler_lms latent 超分，比较耗时与清晰度，选一种。
T8 拼接字幕：T3 + T6 两段用仓库 stitch.py 拼接并烧 SRT（需改造 stitch.py 以适配 Windows 路径与 ffmpeg 位置）。

## 第四阶段：编排层（代码放在仓库 clone 的 pipeline/local/，不要改动云端版本）
1. comfy_client.py：submit(api_json, patches) → prompt_id；wait(prompt_id) 轮询 /history；fetch 输出文件到本地目录；支持按节点 id 或节点标题设置输入；失败时抓 /history 里的 error 并存日志。
2. local_backend.py：把 storyboard.py 的 Segment + prompt_builder.py 的产物映射到工作流输入：text → CLIPTextEncode；reference_images → LoadImage ×N 接 H3RefBatch（图先复制到 comfyui\input\h3_pipeline\）；voice_reference → LoadAudio 接 H3ReferenceAudio；first_frame → LoadImage 接 MiniMaxH3ImageToVideo；duration → 帧数；ratio → 宽高（768 短边）。
3. run_episode_local.py：复制 run_episode.py 的结构（校验、幂等 manifest、--dry-run、--only、多候选），后端换成 local_backend，并发固定 1，追加 --upscale 开关调用 SeedVR2 工作流。
4. storyboard_from_script.py：调用本地 LLM（优先 XB_llama 的 qwen3vl_8b GGUF 或 Ollama qwen3-vl:4b；先测哪个能稳定输出合法 JSON）跑仓库 pipeline/prompts/01_outline_system.md 与 02_storyboard_system.md，产出 episode JSON；LLM 跑完必须卸载再开始生成视频。
5. stitch.py 本地化：ffmpeg/ffprobe 路径可配置；SRT 字体用系统中文字体（如 Microsoft YaHei）。
6. pipeline/local/README.md：一条命令从剧本到成片的用法、所有可调参数、显存与时长上限、已知缺口。

## 第五阶段：用真实项目验收
用《蜂医的复仇》第 1 集的前 30–45 秒剧情（从粗剪或我提供的剧本里取），沿用横屏 1344×768，角色与场景用三角洲素材：
1. storyboard_from_script.py 生成分镜 JSON，人工检查后（给我看一眼）；
2. run_episode_local.py --dry-run 看提示词与节点参数；
3. 实际生成每段 1 个候选 → 失败段重试 1 次 → SeedVR2 放大 → stitch 拼接烧字幕；
4. 产出 ep01_test.mp4 与 .srt，连同 test-log.md、映射表、《接管报告》交给我。《接管报告》要包含：最终采用的工作流与参数、每段耗时与显存、与云端 API 路线相比缺的能力（Context-IR、2K、15 秒以上）及影响、我今后只需要做的事（提供剧本、挑候选）、以及必须由我决定的事项。

## 写提示词时的额外纪律（来自 ComfyUI-H3-Multishot 的 PROMPTING.md 实测）
- H3 以 CFG 1.0 运行、没有负分支，否定句会被渲染出来：用正向锁定（"只有两个人在场"）代替 "no other people"。
- 5 秒镜头放不下一句完整台词加收尾；台词预算 = 自然语速念完 + 约 4 秒安静，10 秒约 15 个英文词 / 约 30 个汉字。
- 非首镜开头保持上一镜收尾姿态静止约 2 秒再开口；每镜结束留 2 秒落定。
- 角色外貌与场景光线描述每段逐字相同；每镜必须有可区分的物理状态变化。
- 场景切换处不要续接，直接硬切重开链。

## 规则
- 不删除、不覆盖我现有的任何工作流、模型、输出文件；要改的工作流先复制到 pipeline/local/workflows/ 再改。
- 显存只给一个任务；LLM 与 H3 不同时驻留显存。
- 不下载缺失的卖家 LoRA；需要下载任何大于 5GB 的文件先问我。
- 不要尝试云端 API（没有 key）。
- 每个测试先 5 秒小样，再放大时长或分辨率。
- 所有结论写明依据（日志、文件路径、ffprobe 输出），没验证的写「未验证」。
```
