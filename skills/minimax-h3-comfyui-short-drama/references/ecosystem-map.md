# 生态地图：这件事 GitHub 上谁做得最好（2026-11）

> 1750+ 个 H3 相关仓库里精读了 ~150 个，目录在 `docs/13-github-survey/00-catalog.md`，逐仓库评级在 `01–07`。本表只列「采用 / 试用」与明确「跳过」。星数为抓取时快照。

| 需求 | 采用 | 试用 / 观望 | 跳过（原因） |
|------|------|------------|------|
| 官方权威 | MiniMax-AI/MiniMax-H3（权重、提示词指南、9 个 skill）；MiniMax-AI/awesome-minimax-h3-integration（生态索引）；Comfy-Org/workflow_templates | wildminder/awesome-minimax-H3（社区性能报告） | — |
| 单节点多模式 | nkxx188/ComfyUI-MiniMaxH3-Easy（MIT，`@`/`#`/`---`，Context Segments） | FX-FeiHou/Easy-H3（GPL，流式块不与 kitchen 同用） | yusu-02、Goldlionren JR（重） |
| 导演台 / 时间线 | seesee75-commits/ComfyUI-MiniMaxH3-Director（GPL，原生 Loop，带测量数据规则）；AIMixer Director 的二采配置 | Songssx TimelineDirector（规范好、GPL）、imbutus（linter 规则）、KadoBOT（烧焦测量表）、chanon obvpm（细但 7 个依赖） | huangserva（镜像）、j955229（停更）、karuvanan（外部程序）、rookiestar28（Windows-only 媒体）、TianyiDataScience（锁 0.34） |
| 段间续接 | 默认硬切；NikoDemon80/Motion-Context 0.7.1（不 patch）；knoic/PrefixStream（MIT，分支抽卡） | tritant Extender（改 8 步）、Herrgott v1.4（FL2VA 钉帧）、JGRFW AICG3D / WhaleTrans（先 2 段测试） | Multishot context_pin（版本冲突）、Continuum / LongMedia（过重）、T8 Long Video（EXP）、h3-relay（Linux）、Smite79（禁再分发） |
| 注意力 / 加速 | KJNodes SageAttention 两节点；lightx2v Turbo 8 步 v1.1 768p；核心 BlockSparseAttention（已合并 Sol/SLA/VSA） | Veda（≥0.38，预测器按 1344×768 训练）、Spark-H3（Windows SM89 包，≥10 s 才有收益）、Spectrum / FirstBlockCache（仅 20 步链）、PDD-Acc（写实 A/B）、HyperFlow、VDN-H3（≥10 s） | lihaoyun6 Cache、TE-Speed OSS、tl2012tl .pyd、xmarre Sol-H3、W4A4-VSA、pottokao GGUF-TE、Saganaki22 sol-attn（被核心取代） |
| latent 放大 / 精修 | LBH-123-AI latent upscaler（事实标准）+ tazmannner ResCascade（σ 0.45 二采） | Tr1dae（手搓二采）、bbaudio UltimateUpscale（长段分块）、RelayHires（漫剧）、Open-H3-Regenerate（接受重绘时） | xmarre LBH `-Plus` 分支（widget 错位） |
| 人脸 / 音频 | Carasibana FaceRefine；Adudeguyman AudioRefine；badgids ExactAudioLock | T8 audio-T8（62 节点，挑着用） | — |
| 角色卡 / 剧照 | matlod turnaround LoRA + MAINodes/T8 Contact Sheet；shootthesound Fizgig-H3-Still；lumosai8 OrbitSheets | tori29umai SingleFrame（姿势→角色）、astropuzzo Image-Studio | thaakeno H3-Studio（telemetry 目录） |
| ControlNet / 换人 | 核心 FunControl + alibaba-pai Fun-Controlnet-Union；maosika reshot | D3voz openjutsu、Saganaki22 Viggle、slmonker selflift | — |
| 提示词工具 | 官方 h3-prompt-writing skill 为基准；见 `docs/13-github-survey/04-prompting-tools.md` | pytraveler Prompt-Rewriter（本地 GGUF 8B）、ruashots open-h3-ir、ethanfel Guide、1038lab Promptor | — |
| Agent skill / 流水线 | 官方 3d-animation-short-generator 骨架；TFboy1/oh-my-minimaxh3-director（驱动 ComfyUI 的脚本层）；chiphoton Codex-Drama（references / QC） | SwotAtmk/infinite-creation、qiukaihui/comfyui-auto-drama、lixiaoxiao9888 漫剧老李 skill（段缝规程、六锁）、senmanx novel-to-manju（漫剧风格表）、suihe1、Rimagination h3lite、SlavaSexton Agent-Kit | TapCanvas / reveric / cwp / zxcHolmes / iv-studio（云 API 或重工程）、Colab skill、游戏精灵类 |
| LoRA 训练 | shootthesound/Fizgig（Windows 一键，24 GB 可训） | AcademiaSD LoRAlab、Inline-Studio、GK-Nodes Dataset Builder | IAmIronMan42（8×A800）、raylight / LightX2V 多卡、X-MinimaxH3（许可证） |
| 可控性杂项 | ComfyUI-Dials（替代负面提示）；LanPaint（局部重绘） | VPack（≥0.38 带参考视频） | — |
| 部署指南 | neng320/minimax-h3-local-deployment（4060Ti 实测）、nimblecloud13 guides | ssssssanjiu turbo 指南、alesha-pro tools（3090 基准） | 各类 OneClick（锁版本） |

## 许可证注意

GPL-3.0：seesee75 Director、Songssx、FeiHou、xmarre Sol-H3、DaSiWa、lihaoyun6 Cache。禁止再分发：Smite79。无 license：Zzz1phyrf、Shrek3、T8 部分仓库。MiniMax H3 Community License：所有官方权重与多数蒸馏 LoRA；本 skill 只引用结论，不打包这些代码。
