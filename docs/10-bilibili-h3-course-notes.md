# 10 · 「秋叶教程」与 B 站 H3 本地短剧课程体系学习笔记

> 调研日期 2026‑10‑31。视频正片无法观看，本文依据 B 站页面文字（标题、简介、分 P / 合集目录、UP 主信息）、相关 GitHub 仓库 README 与源码、第三方文章。凡只读到标题的条目都注明「仅标题」。

## 1. 先把「秋叶」是谁说清楚

| 身份 | 事实 | 与 H3 的关系 |
|------|------|-------------|
| **真·秋葉aaaki**（B 站空间 12566101） | ComfyUI / SD‑WebUI 整合包与「绘世启动器」作者 | 第三方文章（阿里云开发者社区，2026‑09‑22）称其 **2026 年 8 月 ComfyUI 整合包 v3.2**（Python 3.13.11 + PyTorch 2.13.0+cu130 + ComfyUI v0.30.2）"原生支持 MiniMax H3、Wan 2.2、Qwen‑Image‑2.1，解压即用"。所谓原生支持，最可能指 ComfyUI v0.30 核心自带的 `MiniMaxH3*` 节点，而非额外插件或工作流。**没有找到他本人发布的 H3 短剧教程**；他的空间视频列表被 B 站风控拦截（API 返回 -352 / 412），无法核实。 |
| **「秋叶ComfyUI」系列 H3 短剧课程** | 来自一组借用「秋叶」品牌的营销矩阵账号：`MiniMaxh3工作流`（3546856300743410，4.3 万粉）、`minimaxh3工作流搭建`（1906105684）、`comfyui整合包`（3546759114525530，10 万粉）、`-ComfyUI整合包`（22539614）、`Comfyui全新整合包`（20208496）等；资料区统一写「咨询 AI 技能学习 + 微信 huahuawu01」，简介统一是「一键三连 / 关注私信自动获取整合包」 | 内容是把 **MiniMax 官方 skills、Comfy 官方工作流和公开插件**重新录一遍；多条视频已「仅自见」或下架（BV1KLYq6eEDh、BV1gkxc69ERv、BV1oYu36QEva）。**可以当学习路线图看，不要当作秋葉aaaki出品，也不必为此加微信或付费。** |

结论：用户所说的「秋叶教程」在 H3 语境下几乎都是第二类。下面先提炼这些课程的大纲（有价值），再把 B 站上真正有技术含量的 H3 短剧生态梳理出来（更有价值）。

## 2. 「秋叶ComfyUI」H3 课程大纲（可作本地学习路线）

### 2.1 《8G 显存流畅跑 AI 漫剧》17 课（BV15Hap6uEvY，39.8 万播放，2026‑10‑04）

```
01 8G 显存本地部署 ComfyUI 整合包
02 界面初识与 Z-Image-Turbo
03 Krea2 单/双采文生图
04 Krea2 角色资产图生图          ← 定妆图
05 Krea2 图片编辑
06 Qwen-Image-2.1 生图工作流
07 MiniMaxH3 文生及首尾帧生视频
08 MiniMaxH3 双采多参生视频      ← 核心：Ref2VA + 二采
09 剧本创作
10 资产建立
11 视频生成
巩固篇 12 ComfyUI 基础视频生成流程
巩固篇 13 用 ComfyUI 做出你的第一部 AI 漫剧
巩固篇 14 MiniMaxH3 使用教程
巩固篇 15 HellGrind 式提示词 × MiniMaxH3
巩固篇 16 MiniMaxH3 影视创作
巩固篇 17 MiniMaxH3 AI 漫剧创作：解决油腻、美学参考全都要
```

这条路线和本仓库 docs/03 的顺序一致：先图像模型做资产，再 H3 做段落，最后「解决油腻」（去塑料感）与美学参考。

### 2.2 《MiniMaxH3 本地部署》17 课（BV1pHH965EaQ，9.9 万播放，2026‑10‑09）

```
02 本地部署 / 03 云端部署 / 04–05 基础工作流介绍
06–07 模型工作流使用 1、2
08–09 加速方法的认识以及讲解 1、2
10 插件加速方法 + 舞蹈迁移用法
11 一些实际例子
12–13 3D 动画短片生成 1、2
14 品牌宣传片生成 ｜ 双人游戏开场视频生成
15 手绘实拍融合视频生成 ｜ 极简产品广告生成
16 音乐 MV 动态字幕生成
17 纸艺定格科普视频生成
```

**第 12–17 课的名字就是 MiniMax 官方仓库 `skills/` 里 9 个 skill 的名字**（3d‑animation‑short、brand‑promo、co‑op‑game‑intro、handdrawn‑live、minimalist‑product‑ad、music‑video‑subtitle、papercraft‑stop‑motion……）。也就是说这套课的后半段是在演示官方 skills，想学直接读 `github.com/MiniMax-AI/MiniMax-H3/skills`（本仓库 docs/04、06 已覆盖）。

### 2.3 《56 集》（BV1aJgN6cEeb，14.7 万播放，6 人创作团队，UP「PR教程-」）

H3 7 课（云服务器 / 工作流 ×2 / 加速 ×2 / 插件加速 + 舞蹈迁移 / 实例）+ ComfyUI 26 课 + AI 漫剧 16 课 + **漫剧工作流 7 课**：

```
1 视频字幕、水印去除与视频高清/超清
2 视频自动匹配音效、文本生成音效
3 LTX2.3 导演工作流
4 AI 解说短剧神器：旁白解说克隆
5 视频高清放大
6 视频人物/物体去除
7 短剧画面自动匹配 BGM
```

这 7 个后期工作流正好补上 H3 本体不管的事（字幕去除、音效、BGM、旁白），可以对照本仓库 `pipeline/stitch.py` 的后期阶段。

### 2.4 《一键懒人整合包》12 分 P（BV1rnun6QENd，12.7 万播放）

界面 → 基础生图 → 图生图/局部重绘 → ControlNet → 洗图 → 文生视频 → 图生视频 → 首尾帧 → 动作迁移（上/下）→ 多图参考生视频。属于 ComfyUI 通识课，H3 只占首尾两节。

## 3. B 站 H3 短剧生态里真正有技术含量的东西

### 3.1 导演台插件（AIMixer/ComfyUI_MiniMaxH3_Director，2.6k star，Apache‑2.0）— 你本地已安装

| 项目 | 内容 |
|------|------|
| 节点 | `MiniMax H3 Director`（必填 model / video_vae / audio_vae / clip；可选 `i2v_groups` `r2v_groups` `semantic_bridge` `selflift` `refine`；输出 images / audio / fps / frame_count / source_images / report / images_pre_refine）、`Director Group (Image to Video)`、`Director Group (Reference to Video)`（图 ≤9 / 视频 ≤3 / 音频 ≤3 自动增长口）、`Director Groups Combine`、`Director Refine`、`Director SelfLift`、`Director Semantic Bridge` |
| 底层 | 官方 `MiniMaxH3ImageToVideo` / `MiniMaxH3ReferenceToVideo` + `MiniMaxH3SigmaShift` + KSampler |
| 任务类型 | `t2v` `i2v` `fl2v`（fl2va 权重）；`r2v` `v2v` `rv2v`（ref2va 权重）；CLIP Loader type 必须设 `minimax` |
| 多段 | 节点内时间轴：切分 / 均分 / 智能分镜（PySceneDetect）/ 追加；**段间引导**默认关，开启后"将上一段生成结果的末尾运动（及生成音频）钉入下一段采样再裁掉前缀"，上下文帧数 5 / **22（推荐）** / 39 / 56 |
| 参考引用语法 | **`<Picture N>` / `<Video K>` / `<Audio J>`**，或 `@`——与官方六段式一致，可直接用本仓库 docs/04 的写法 |
| 二采（Refine） | 三种模式：`refine` 同分辨率精修；`upscale` 先放大到目标画布再二采（像素插值 / RTX VSR / H3 latent）；`latent_upscale` 只放大 H3 latent 不二采。`sigmas` 接 BasicScheduler 或 ManualSigmas，可选 `refine_model` 二采 UNET，`skip_fl2v` 默认开 |
| SelfLift | 渐进一采：低清前缀 + 3D lift + 高清收尾，Euler |
| 默认参数 | 0.4MP 16:9（864×480）、5 s / 124 帧 @24fps（17k+5 网格）、25 steps、`res_multistep` + `simple`、CFG 1.0、sigma shift 视频 12 / 音频 3 |
| **导演包 `*.mmxpack.zip`** | `pack.json` + `shared_params/shared_params.json` + `asset_groups/01/group.json` + `timeline.json` + `Picture1.png…Picture9.webp` / `Video1.mp4` / `Audio1.wav` / `start.jpg` `end.jpg` / `source_video/`。README："转换工具可以只写 pack.json + shared_params/ + asset_groups/，不必手写 timeline.json" —— **这是程序化驱动导演台的正规入口**，比改 Workbench 的 JSON 字串稳 |
| 示例工作流 | `minimax_h3_director_{t2v,fl2v,r2v,v2v,rv2v,external_groups_i2v,external_groups_r2v,二采_加速}.json` |
| 依赖 | ComfyUI ≥ 0.30.0；可选 scenedetect、opencv‑python‑headless、imageio‑ffmpeg；RTX VSR 需 nvidia‑vfx |
| 配套 | 作者 AI搅拌手（空间 1997403556）的「MiniMaxH3导演台插件」合集 54 集；「提示词大师」桌面软件（一键扩写 H3 连续剧情提示词，支持 Qwen3.8） |

注意：README 中**没有** Ollama / 智谱提示词扩写的配置说明，也没有文本分镜格式；本地清单里看到的 `Refine 可接 Ollama` 要以你安装的版本源码为准。

### 3.2 多镜头采样器（jlucasmcrell/ComfyUI‑H3‑Multishot，v2.7.2）— 你本地已安装，但节点名需核对

README 实际节点：`H3MultishotSampler`、`H3MultishotMemorySampler`、`H3StudioControls`、`H3StudioSwitches`、`H3AutoRefs`、`H3ReferenceVideo`、`H3ExtendTake`、`H3Retake`、`H3ChainNormalize`、`RiftPromptSource`、`RiftScriptPicker`、`JoyEcho_LLMEnhance`（Ollama，默认 `qwen3:14b`）。你清单里的 `H3RefBatch / H3ReferenceAudio / H3ConcatAV / H3EpisodeSplit / H3LastFrame` 在 README 中不存在，可能是旧版或静态扫描误判，**用 `/object_info` 核实**。

它的 `PROMPTING.md` 是目前最具体的「多段连续生成」写作规则：

- **气闸（airlock）**：非首镜开头保持上一镜收尾姿态，静止约 2 秒再开口；**落定收尾**：台词讲完留约 2 秒回到稳定姿态。
- **台词预算 = 自然语速念完 + 4 秒安静**，必须落在镜头长度内：362 帧（≈15.1 s）约 27 个英文词；243 帧（≈10.1 s）约 15 词；**124 帧（≈5.2 s）"does not work"**，接缝处会截断。
- **角色外貌与房间/光线描述每镜逐字相同**（与 HelloGen "paste it word for word" 一致）。
- **每镜必须改变物理状态**："if you can swap two shots' action lines and the script still reads correctly, the model cannot tell them apart either."
- 24 fps 不要改；**CFG 1.0 没有负分支，否定句会被渲染出来**，静止短语会冻住整帧 —— 这解释了为什么 H3 提示词里"不要出现 X"要慎用。
- 衔接模式 `continuity`：`context_pin`（默认，钉上一镜最后 22 帧原始 latent，需 ComfyUI‑H3‑Motion‑Context 包）、`first_frame`、`cut`、`seamless`、`seamless_tail`、`flf_chain`、`latent_handoff`。接缝音频在下一镜前 0.75 s 内最安静处切，40 ms 等功率焊接。
- **extend take**：一个 premise + `take_seconds`，写作器写一段连续台词在句/从句边界切窗口；建议 ≤ 4 个窗口。
- 长链每跳漂移约 1.02、纹理每接缝 ×1.3，超过约 5 镜建议 `chain_gain_control = flatten`；**场景切换处重开链**。
- 显存实测：3090 24GB，736×1280，192 帧，首镜约 67 s/step，后续约 98 s/step，约 23 分钟/镜。GGUF 建议 Q8_0（32GB）/ Q5_1（24–32GB）/ Q4_0（16GB）。
- 参考图能恢复外观但**不能恢复体型尺度**。

### 3.3 其他值得看的创作者与主题

| 主题 | UP / 项目 | 要点 |
|------|-----------|------|
| 全自动漫剧流水线 | 机智罗_LX `wjluoxiao/ComfyUI-JZL-MiniMax-H3`（BV1gPb963EJb、短剧导演台 V6 BV15yt66kEMN） | 故事 → 自动分段 → 每段官方六段式 Ref2VA 提示词 + SCENE/VIDEO/AUDIO 槽位调度 → 「动作导演级」润色（攻防同步、拒绝回合制）→ 校验兜底；V6 降低配置门槛 |
| 多宫格导演台 | Ai_随风 + 尺素呵插件（BV1s2Mk6nEg4 整合包 V3；BV12Zuw6CE42 导演台 3.0） | 多参 + 多宫格 + 提示词模板 + 使用手册（飞书，需登录）；另有「全自动一分钟动漫短剧工作流（多参 + 自动循环 + 上下文潜空间衔接参考）」、「一人剧组 9 skills + RHTV 无限画布」 |
| 文戏与打戏 | WorkFisher《MINIMAX 系列》11 集（BV1T68c6ZEDm 短剧全流程 + 全套提示词模板；"全网最强文戏教学？H3 终于会演戏不油腻"；"高动态打斗动画精讲 附模板"；"提速 530% 12G 10 秒只需 300 秒"） | 本地整合包 + 工作流在夸克网盘；插件 `ptmaster/ComfyUI-PT_H3ConcatAVLatent`（注意：它只是把视频 latent 与音频 latent 打包成 H3 采样器需要的嵌套 latent，用于 **v2v 重绘**，不是跨段续接） |
| 低显存加速 + 四视图 | 黑鹤001（BV14Zu16YERZ，38.3 万播放） | 全功能低显加速流 + 角色四视图生成 + 提示词技巧 + 4 步 LoRA 精简流；网盘：pan.quark.cn/s/710a55193ab5 |
| 实测与提示词最佳实践 | 天选嘉鲤敦赵图图（BV1x8Mo6tESD，200 条实测）；小黄瓜（BV1xHMX67EAA 合集 5 集：能否跑 / 全模式实测 / **Turbo LoRA 20 分钟→8 分钟画质对比** / 高清放大修脸） | 提示词建议均来自官方 `VIDEO_PROMPT_WRITING_GUIDE_base_en.md` |
| 乱念台词 / 抢台词 / 乱出字幕 | 楚辰_Amos「提示词约束 + IndexTTS 单句配音实操」；汉江小白条「乱念台词的坑我填上了（附 SKILL）」；在下鱼酥「乱出字幕、抢台词 附提示词模板」；无用の阿杰「JSON 写法更可控」；AIX爱客「99% 听话 Prompt Skill，官方规范 + A/B 实测」；Ai_随风「提示词优化器 skills：告别台词乱说、英文看不懂」 | 社区共识方向：严格官方 `<d>[Chinese] …</d>` + `(S1)` + 听者闭嘴；一镜一人；台词短；必要时 H3 出画面、TTS 单句重配 |
| 去油（去塑料感） | AI代码侠土豆「电影短剧 Skill：去油单采 / 去油双采」（BV1VztP6gELV，基础模板来自 发福的卡皮巴拉）；「解决油腻、美学参考」 | 二采 + 美学参考图是主流解法 |
| 双采 | 劇毒Shoujo「zib+zit 最大程度保持原样双采」「15s 768P 旧 4 步加速多参 + 音色参考」（BV16tgK6yE1e 踩坑分享）；YZ_金鱼「新二采、新加速」；BCE‑I_曲率炸鸡「8G+16G 15 秒 720p 低配二采」 | 一采低清出动作，二采高清修质感 |
| 加速方案 | T8star‑Aix（4 步 LoRA 移植、BlockCache、双时钟采样器）、TETAE TE‑speed（+45%）、lightx2v 4/8 步 LoRA、Larryvrh 4 步、阿硕「多重加速快 70%」、机智罗「光流跳步 vs EasyCache vs 超级缓存」 | 你本地已有 Turbo 4/8 步 LoRA、Star7 chunk、SelfLift；缺 Motion‑Context、RES4LYF（beta57）、blockcache‑T8 |
| 官方 skills 使用 | AIwood「官方提示词 skill 安装与使用心得」（仅标题）；学AI的曹同学「官方 SKILL 安装调用 + 两类工作流实操」；宏雷HyLan「未开源的官方 Skill + Prompt 网站爆火玩法」；AI代码侠土豆「官方 Skills 提示词生成器使用教程」 | 对应 `MiniMax-AI/MiniMax-H3/skills/h3-prompt-writing` |
| 数字人 | AIwood「真音频驱动数字人，绝非音频参考」（仅标题）；像素幻想Lab「无限时长数字人工作流，口播/唱歌」 | H3 的 `reference_audio` 是音色参考，不是驱动；真驱动走 InfiniteTalk 之类 |
| 其他整合包 | Ai_随风 V3、笨笨聊AI 小白整合包、WorkFisher 纯净包、AI代码侠土豆 tudouV4.1 + NB 启动器、万能君「文字图片生成带音频视频工具 V1.0」 | 均为第三方打包，下载前核验 |

## 4. 对你本机的直接映射

你已装：`ComfyUI_MiniMaxH3_Director`、`ComfyUI-H3-Multishot`、`minimax-h3-chunk-star7`、`comfyui-SelfLift`、`Xiantu Workbench`、`XB_ToolBox`、Turbo 4/8 步 LoRA、`h3_upscaler_lms`、SeedVR2。这意味着 B 站上三条主流路线你都有基础：

| 路线 | 你本地对应 | 学习重点 |
|------|-----------|----------|
| A 导演台（AIMixer） | 已装 | 用 **导演包 mmxpack** 程序化喂分镜；段间引导 22 帧；Refine `upscale` 模式做二采放大 |
| B 多镜头采样器（Multishot） | 已装（节点名待核实） | `PROMPTING.md` 规则；`context_pin` 需补装 ComfyUI‑H3‑Motion‑Context 0.3.1；RES4LYF beta57 调度器 |
| C 闲兔导演台（Xiantu） | 已装、02 工作流已验证 | 续接重叠 22 帧（与 A/B 的 22 帧是同一思路） |

建议补装：`ComfyUI-H3-Motion-Context`（0.3.1，不要 0.4.0）、`RES4LYF`、`comfyui-minimax-h3-blockcache-T8`、lightx2v 4/8 步 LoRA。

## 5. 对本仓库方法论的修正与补充

1. **否定句慎用**：H3 以 CFG 1.0 运行、没有负分支，"no X" 这类句子可能被渲染出 X。本仓库 docs/04 与 templates 里的 `negatives` 字段应改为**正向锁定**写法（写"只有两个人在场"而不是"没有其他人"），或只在 Context‑IR 可用时使用。
2. **台词预算更严格**：Multishot 实测 5 秒镜头基本放不下一句完整台词 + 收尾；本仓库校验器的「字数 ÷ 4.5 + 2 s」应对 ≤ 6 s 段落额外警告。
3. **每镜要有可区分的物理状态变化**：加入分镜校验（相邻镜头 `action` 文本不得互换后仍成立）。
4. **场景切换处重开链**：长链漂移与变暗是实测现象，跨场景不要用续接，直接硬切。
5. **二采是本地路线的标配**：768P 一采 → Refine/SelfLift/SeedVR2 二采，替代云端的 2K 重生成。
6. **导演包 mmxpack** 作为本地编排层的输入格式，比 Workbench JSON 更稳；已写入 `prompts/02-local-takeover.md`。

## 6. 本节来源

- B 站页面：BV1rnun6QENd、BV1VNuP6ZEXh、BV1pHH965EaQ、BV15Hap6uEvY、BV1aJgN6cEeb、BV1rSYM62E2b、BV1s2Mk6nEg4、BV1T68c6ZEDm、BV1xHMX67EAA、BV14Zu16YERZ、BV1x8Mo6tESD、BV1mkM96QETu、BV1SjMX6DE8R、BV1Tquc6gERB、BV16tgK6yE1e、BV1yfua6sEC4、BV15yt66kEMN、BV1PJby6gEJ9、BV1qnuq6dET2、BV1VztP6gELV、BV1XYut6dEgL、BV1GG8F6FEwA（仅标题：BV1efMm62EeR、BV1hQuw6UEeQ；不可访问：BV1KLYq6eEDh、BV1gkxc69ERv、BV1oYu36QEva）
- https://hailuoai.com/h3-open（海螺官方 H3 开源生态页，收录 48 条社区视频）
- https://github.com/AIMixer/ComfyUI_MiniMaxH3_Director（README + nodes/ 目录）
- https://github.com/jlucasmcrell/ComfyUI-H3-Multishot（README、PROMPTING.md、SETTINGS.md、INSTALL.md）
- https://github.com/ptmaster/ComfyUI-PT_H3ConcatAVLatent（README、nodes.py）
- https://github.com/suihe1/short-drama-production（Codex skill：MiniMax 官方 API 预检/提交/轮询/下载）
- https://developer.aliyun.com/article/1765587（秋叶整合包 v3.2，第三方撰写）
- 无法访问：秋葉aaaki 空间与 B 站 API（风控）、MiniMax 官方《H3 使用手册》飞书 wiki 与各创作者飞书文档（需登录）、知乎两篇（403）、CSDN 一篇（521）
