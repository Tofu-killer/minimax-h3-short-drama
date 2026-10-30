# 05 · 角色 / 场景 / 声音一致性技术

短剧的生死线是一致性：观众接受 AI 画面，但不接受主角换脸。H3 相比前代多了全能参考，但**模型不记得上一集**（HelloGen："H3 does not remember episode one when it draws episode two"）。一致性只能来自三样东西：参考文件、绑定标签、文字描述。

## 1. 分层一致性模型

| 层级 | 控什么 | H3 手段 | 失败表现 |
|------|--------|---------|----------|
| 片段内（4–15 s） | 多镜头切换时同一人 | 单次生成的共享上下文；`retention_analysis: fully_preserved`；`Preserve both faces, outfits, seats, and eyelines` | 反打镜头换脸 |
| 片段间（同集） | 服装、道具、光线、方位 | 同一组参考图；首尾帧衔接；`continuity` 字段；固定识别短语 | 外套颜色变、道具消失 |
| 集间（系列） | 角色、世界观、风格 | 系列圣经 + 定妆图库 + 风格锁 + 音色参考 | 人物"长大/变老" |

## 2. 参考图规范（定妆图库）

综合 HelloGen、RunDiffusion、CSDN 工程实践、MiniMax 官方 skill：

1. **一人一图**：腰部以上、正对镜头、素底、均匀光；**脸要大**（参考图会被缩放到画布尺寸，小脸只剩几个像素）。
2. **角色包 = 3 张**：正面身份图、3/4 侧或全身图、可选细节图（纹身、首饰）。各图年龄/脸型/发长/服装/风格必须一致，否则要写明「从哪张取哪个特征」。
3. **服装进图不进文**：把戏服画进参考图，文字只写不会变的东西（骨相、发型、体型、固定饰物）。
4. **环境光接近成片**：定妆图的光线方向与色温尽量贴近该场戏，减少模型"重新打光"时的漂移。
5. **场景图无人**；**道具白底单品图**。
6. **同一文件复用整季**，不要每集重生成。
7. 数量：官方上限 9 图，但多篇指南实测 **≤ 6 个参考最稳**；前 5 张免费。

## 3. 文字锁定

```
Preserve her oval face, shoulder-length copper curls, dark brown eyes, small mole below the left eye, athletic build, and forest-green jacket with brass buttons.
```

- 每个角色写一句「识别短语」，放进系列圣经，**每个片段逐字复用**；再写一句「声音短语」（`a woman in her late twenties with a low, slightly husky voice and an unhurried pace`）同样逐字复用。
- 用 `<Subject N>` 代替人称代词。
- 负向约束锁外形（国内漫剧教程的龙案例：`保持东方龙的主体特征不变，没有龙爪，没有翅膀`）。
- 一次只改一个变量：`do not change pose, outfit, and camera angle in the same generation`（APIDot）。
- 中途不许变身：`Never script a change to the person mid-clip`。

## 4. 参考职责分配（Omni Reference）

```
Image 1 controls Character A's identity.
Image 2 controls Character A's outfit and silhouette.
Image 3 controls the environment and lighting only.
Video 1 controls body movement and timing only.
Audio 1 controls rhythm and effects only.
Never transfer facial traits from Image 3 or visual styling from Audio/Video 1.
```

- **职责不重叠**（Krea："Overlapping roles create an undefined contest between inputs"）。
- 加 `Do not copy the drink, pose, or background from @Image1` 之类的「不要搬运」语句。
- 参考视频只借运镜/节奏；参考音频只借音色。

## 5. 片段间衔接

| 技术 | 做法 | 来源 |
|------|------|------|
| 命名终态 | 每段结尾写明确状态（`End with Character A centered in a stable medium shot`），下一段从该状态开场 | APIDot、HelloGen |
| 尾帧→首帧 | 抽上一段最后一帧作为下一段 `first_frame`（I2VA） | 国内漫剧教程、Kapwing |
| 首尾帧转场段 | 上段尾帧 + 下段首帧，FL2VA 生成 2–4 s 过渡 | 人人都是产品经理教程 |
| 视频续写 | 上一段作 `<Video 1>`，summary 标 `[video continuation]`，`Continue directly from Video 1 without a visible reset` | APIDot；MindStudio 实测空间连续性不完美，背景人物会移位 |
| 一次性事件计数 | `the door opens exactly once, in [Shot 2], and stays open` | HelloGen |
| 场景只描述一次 | 地点描述写一遍，之后原样粘贴；写明不存在的东西 `no other people, no signage` | HelloGen |

## 6. 声音一致性

- 文字声音短语逐字复用，但官方与第三方都承认**仅靠描述不能保证两次生成音色完全一致**。
- 稳定方案：为每个主角录/生成一段 2–15 s 干净人声作 `<Audio N>`，每段都带（音频输入免费）。
- 旁白用固定 TTS 在后期铺整条，不交给 H3。
- 多语言：对白写什么语言就标什么语言；MindStudio 实测用英文提示要求日语台词会带口音。

## 7. 镜头设计规避一致性风险

- 需要看清脸就用中近景/特写，远景用背影、3/4 背面或空镜（forgewebO1 收录的仙侠分镜提示词："never show a distant frontal face"）。
- 群像先写明人数。
- 关键脸部镜头走 I2VA 首帧而非纯 Ref2VA。
- 2 个节拍以内的片段最容易保持主体一致（Kapwing）。

## 8. 本地 ComfyUI 路线的额外手段

- Codex‑Drama 附带 **Qwen Image Edit 一致性工作流**：用 1–2 张参考把分镜静帧改成同一人，再送 I2VA。
- RunningHub 上的「ki_MiniMax H3_多参分镜硬控流」「AITUDOU 全能参考 数字人 人物音频一致性」工作流，本质都是：多角度角色图 + 场景图 + 音频参考 一次性喂给 Ref2VA 节点。
- `ComfyUI-JZL-MiniMax-H3` 节点包声称 V1 支持 24 图 + 8 视频 + 8 音频（远超官方 API 上限，应为本地推理放宽），并自动按剧情为每段调度参考槽位，无需每段手工配图。
