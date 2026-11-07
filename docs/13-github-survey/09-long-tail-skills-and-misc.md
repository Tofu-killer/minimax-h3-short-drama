# 09 · 长尾扫描（非 ComfyUI 侧）：skill / 提示词库 / 流水线 / 部署与 API

> 范围：relevant.json 中 `comfy=false`、15 ≤ ★ < 60、非 fork、非 spam-gateway 的 77 个仓库 + 8 个 ★≥60 但簇 01–07 未覆盖的 skill / awesome 仓库，共 85 个；全部读 README（前 150 行），其中 11 个浅克隆精读 SKILL.md / references / 源码。扫描日期 2026-11-07。
> 注意：不少 `comfy=false` 的仓库实际是 ComfyUI 节点（muse-collective、kitsune、SatoDive），元数据漏标，这里一并处理。

## 本簇结论（长尾里值得补进 skill 的 ≤10 个）

1. **swan7-py/MiniMax-H3-Skills-Local**（★71）：`h3-camera-motion-lib` 是全调研里唯一「46 镜 × 约 130 条实跑 + 逐镜 ✅/🟡/❌ + LoRA 台账 + 可测/不可测指标」的运镜句库；`negation-guard.md` 的 L1 词表 + 白名单是最可落地的否定式闸门。**整包借规则，直接改写进 references/camera.md。**
2. **loopforge0/minimaxh3-shots-skills**（★17）：英文侧的对照组——29 个命名镜头由官方 12 原语组成；最硬的发现是「4 步 Turbo 几乎抹掉运镜」「背景参考板让运镜减半」「开场景别要放在主体最大的一端」。**运镜章节必须同时引用它与 swan7。**
3. **lixiaoxiao9888-create/forest-laoli-h3**（★54）：manju-laoli 的 H3 专用精简版（20 份规则 + `h3_lint.py` H1–H36），新增了门窗状态锁、分身复制、穿门融化、物理死锁、氛围层六件套、台词「连续铺轨」实测，比 05 簇里的 manju 更贴 H3。**借 H13–H36 与 `h3_lint.py` 做我们的机检。**
4. **garycaogan/h3-ref-video**（★29）：唯一做了 Seedance 2.0 mini vs H3 盲评的仓库：动漫/cos H3 直出 4:0 赢；中文真人对白戏 H3 直出 0:4 输、垫首帧后哭戏 4:0 赢；「每镜一张分镜图当参考」能追平。**直接决定我们短剧的「漫剧直出、真人先出分镜图」策略。**
5. **3ALLBUY14/h3-prompt-builder**（★19）：`lipsync-guide.md` 的「台词归属三选一防火星语」「短音频（≤8 s）音色参考优先」「吞字/句末余量 ≥0.2 s」是口播/对白最细的实战清单；`official-updates.md` 收录官方飞书手册 + H3 Max / Context-IR / 768P→2K 再生成口径。
6. **LoveRain1997/video-to-h3-prompt**（★44）：视频反推提示词的「取证 → 交叉验证 → 因果链 → 状态机」SOP，六条铁律里「静态与爆发写成互斥两态」「横置先怀疑相机 Roll」对复刻参考片有用。
7. **MacroSony/minimax-h3-chained-character-swap**（★32）：Motion Context 22 帧 + 彩噪渐弱注入（19f@0.45 → 3f→0.10）的换人续接配方，含「源片必须 24 fps、否则慢放 fps/24」「Video 1 被节点 adapt_canvas 到 1344×768」两条工程坑。
8. **RK-BoilingPoint/H3-Visual-Marker-Control**（★21）：零改动的「参考图手绘色框 + 文字解释」空间控制法，双人三色框 10 s 成功；代价是色框偶有残留。适合短剧里「谁走到哪」的站位控制实验。
9. **muse-collective-26/MiniMaxH3-Director 系列**（★57/29/26）：源码级揭示官方 `MiniMaxH3ReferenceToVideo` 把参考视频按「已是 24 fps」处理且不重采样 → 30 fps 源片会被截短并慢放；其 VAE Re-encode Carry 把段缝灰度差从 ~44–48 压到 ~3–5（与片内正常 4–16 同级）。
10. **kitsune123150/minimax-h3-hybrid-cond**（★53）：49 行 monkey-patch `MiniMaxH3.extra_conds`，把 `minimax_keyframes` 与 `minimax_refs` 的 latent 合并进同一 `cond_video_latents` → 首帧锁定 + `<Picture N>` 身份参考可同用于 FL2VA 或 Ref2VA 权重。续接场景值得试。

观望：acheng-director（★57，工程浩大但 H3 相关只是薄薄一层编译器）、animede/lipsync-mv（Vocal Lock 数据好但绑 diffusers-server）。别碰：6 个 ArgoLink SEO 仓库（API 报价页，内容互相复制）、Badim41/network_tools、dsh-client-ui-pet。

---

## 有新信息的仓库

### swan7-py/MiniMax-H3-Skills-Local（★71，无 license，2026-11-04）
- **定位**：WorkBuddy skill 包，主线两个：`h3-video-prompt-cn`（六段结构 + 实跑判据，18 份 references，已归档官方 `base-en.txt/ref-en.txt`）与 `h3-camera-motion-lib`（7 个运镜族的中文镜头句库）。`old/` 10 个官方风格 skill 的本地化版已停更。
- **实测规模**：A–G 七组 46 镜，约 100 条 480P（864×480，同种子 20261005）+ 29 条 1080P 4:3 双采，Ref2VA、中文提示词；每格单样本单种子，作者自标「初级结论」。
- **运镜状态表**（节选）：推/拉/摇/变焦/横移/摇臂/过肩/双人同框/双人横移/斯坦尼康/跟拍/航拍/穿越/POV/顶拍 ✅；整圈环绕原生不闭环（首末灰度相关 0.647）**必须挂 pablodawson `minimax_h3_flf2v_lora_v1`**（0.931）；子弹时间同理；希区柯克变焦三版全部退化成普通推镜 🟡；甩镜「主体→太阳」❌ 但「花丛→主体」✅；荷兰角只有 `H3_Dutch_Angle_Slider_v1` 才有倾角（**权重即倾角，1≈20°，常用 2.0**）；Jojocodex `camera_motion_h3_lora` 18 对对照峰值位移输 15/18，默认不挂。
- **核心纪律**（`00-core-discipline.md`）：变量纪律（摇镜不写焦距；推拉必写「焦距全程锁定」；横移写「镜头朝向锁定」，不写「视线锁定主体」否则退化成环绕；升降写「姿态保持水平」）；书写顺序「画面里先出现的东西写最前」（遮挡/揭示先写前景遮挡物）；配速用 `At MM:SS.mmm` 起止两个时刻给出，禁「在 3 秒内」类自造时长；时刻会漂移 ±1 s（写 5 s 硬切实测 3.54 s），动作先后要用文字兜底；整圈必须同时给圈数 + 起止时刻 + 收束句「末了回到正面」，速度词会让圈数失效。
- **否定式闸门**（`negation-guard.md`）：效力排序「不提名字 ＞ 替换式否定（不保留 X，改为 Y）＞ 裸否定（禁）」；L1 词表（不移动/不晃动/不转身/无视差/保持不变…）必改写，白名单（不同/不仅/不断…）放行；12 条正向替换表（`机位保持不动` → `机位位置全程固定在同一点`）。官方 MT 原话 `naming them makes them come back`。
- **Ref2VA 现实边界**（`09-reality-and-pitfalls.md`）：起手景别不受控（官方矩阵「中景及更近」0/51，偏差 40/40 全偏宽），裁参考图/构图锚/crop 句三招全无效，唯一正解是 I2VA 真实首帧；环境写「描述式」不写「清单式」只能把主体放大 2.4–3×；双主体复制是「提示词×画幅×种子」联合结果（4:3 出双脸，16:9 不出），防复制句 `画面中自始至终只有 <Subject 1> 这一位人物`；挂首帧图会起手跳帧但不压运镜幅度；换种子优先于改词。
- **音频参考**（`audio-reference.md`）：`fully_copy` 音乐 r≥0.99 零位移，**语音带 ~0.45 s 系统位移**；`partially_copy` 区间声明不被遵循；`reference` 音色迁移被角色表观性别强拉（女角色 + 男声 F0 142→220 Hz），**角色形象先验 > 音色参考**，F0 落区正确 ≠ 音色复刻，只能试听判定；`Subject N = S N = Audio N` 三线同号且接线顺序一致。
- **构图可执行性**：比喻动词按字面执行（`hovering` 真悬空），要写接触 + 影子落点；微距必锁 `The frame contains only X and Y.`；含人镜必写景别锁（只写「略前倾」被放大成深鞠躬，相似度 0.549 → 加景别锁 0.9986）；提示词正文禁 markdown 符号。
- **坑**：无 license；中文提示词 + 480P 口径与官方英文 + 竖屏不同 profile；大量结论标「初级」。
- **评级**：**采用（借规则）**——运镜句库 + 否定闸门 + 音频判据直接进 skill references。

### loopforge0/minimaxh3-shots-skills（★17，MIT，2026-10-27）
- **定位**：Claude Code skill 对（`h3-camera-shots` 写镜头句、`h3-shot-iteration` 诊断），29 个命名镜头（dolly zoom / crash zoom / whip pan / snorricam / 360 orbit / crane / aerial pullback / handheld / yo-yo zoom / dutch / eyes-in / rack focus / split screen / POV / time-lapse / fisheye / FPV…）全部由官方 `base-en.txt` §4.3 的 **12 个运镜原语 + 幅度/速度两修饰词**组成；33 条逐字节原始提示词 + `build_prompt.py` 按 scene.json 换主体。约 80 次生成（RTX 3060 864×480 迭代，RTX 5090 1344×768 定稿），Ref2VA 单张身份图。
- **载荷级设置**（`settings.md`）：**20 步、Turbo LoRA 关**（4 步 Turbo 几乎抹掉运镜）；`res_multistep/simple`；**只给身份参考板，不给背景板**（背景板让运镜减半：0.81× vs 0.47×，换来场景漂移 0.08→0.02）；`ref_image_size=max`（`match` 会把参考板渲染成第 0 帧，主体缺席约 16 帧）；参考视频两次测试都不传递运镜；**帧数 ≥124**（训练范围 124–362，`%17==5`：124/192/243/362），三段式动作（yo-yo zoom、分屏）要 192 帧。
- **四条规则**：运镜 = 类型 + 幅度 + 速度写进句子；**开场景别放在主体最大的一端**（要收紧就从大全景开，要放宽就从近景开；dolly zoom / snorricam 例外）；写可观测结果不写风格标签，但原语动词优先级高于结果句；别要求不可能的事（`holds one single pose completely rigid` 让运镜幅度从 98–108% 掉到 22%）。
- **修饰词实测**（单推镜，主体放大倍数）：无修饰 1.53×；`small amplitude` 1.47×（惰性，不是刹车）；`large` 3.18×、`fast` 2.90×、两者叠加 2.83×（饱和，不叠加）→ 默认不写修饰词，只在 crash zoom / whip pan / 360 orbit 等身份靠幅度的镜头写。甩镜命名落点使速度 23→218 px/step，「要求运动模糊」无效。
- **不是杠杆**：镜头/机身型号纯装饰（8 mm 与 50 mm 像素级一致，75 mm 略紧）；事件计时不可控（要求 3.0 s/4.0 s 揭示都落在 2.46 s；「所有事都发生在前 2.5 s」是 H3 自身调度）；bullet time 做不出。
- **表演**：「still」不能写成「frozen」（全镜 `standing completely still` 让人停止眨眼呼吸）；表情要写成「变化 + 时序」而不是状态（`runs open-faced` 被定格成 8 s 张嘴）；音频槽里绝不提相机/镜头/机位（`an array of still cameras` 让运镜从 108% 掉到 22%）；不命名贴身装置（`Snorricam body rig` 被画进画面）。
- **工程坑**：ComfyUI `COMFY_AUTOGROW_V3` 输入必须用扁平键 `ref_images.ref_image_0`，嵌套写法验证通过但**静默丢弃参考图**（`verify_refs.mjs` 检测）；某图像 checkpoint 会输出纯黑 PNG 且报成功（疑 fp8 溢出），用 `ffmpeg … -pix_fmt gray | od` 查均值。
- **坑**：作者只测人类主体、单方向；int8 + NVFP4 开发、高精度定稿，量化对运镜幅度的影响未表征。
- **评级**：**采用（借规则）**，与 swan7 互为中英对照。

### lixiaoxiao9888-create/forest-laoli-h3（★54，MIT，2026-11-02）
- **定位**：「漫剧老李」H3 专用包 v2.1.1（相对 05 簇 manju-laoli 去掉了 Seedance 体系）：G0 六项锁 → 剧本 → 资产 → 分镜 → H3 编译 → 清洗机检 → 交付，20 份 references + `scripts/h3_lint.py`（H1–H36，29 用例，退出码 0/1/2 可接 CI）。推荐 9:16，16:9 实测可用，禁 `auto`。
- **新于 manju 的 H3 实证**（2026-10-21《门后》4 段真机）：H29 人穿过门洞/窗洞触发 alpha 半透明融化；H30 同框第二人写 `watches him go` 诱发分身复制、一镜最多两个 `<Subject>` 且只给一人写动作；H31 门外 `knocks` 写进正文 → 门内主角自己转身敲门，画外声源动作只进 `overall_soundscape`，未开门段每镜末尾写 `the closed door stays shut`，开门段场景标 `partially_preserved` 不死锁门；H32 段内依托物跳变 → 左右两个分身；H33 全蹲 + 低机位 / 薄物穿窄缝 → 卡 76% 或冻帧 1.7 s；H34/H36 全片 9 图槽固定、省图即整体错位；H28 禁 `wall of / rows of` 等扩建词（房间翻倍）。
- **词数预算**：单镜 45–70 词健康，<35 WARN，>75 WARN，**>100 FAIL（先丢机位再丢后半动作）**。
- **台词密度实测**（`dialogue-density.md`，ASR 回读）：H3 从不漏念台词，「对话太少」99% 是稿子只写了一句；台词按文本顺序**连续铺轨**，`[Shot N]` 只决定画面切点不决定发声时刻，发声时刻 = 前面台词时长之和（偏差 ±0.4 s 自动追平）→ 用「字数 ÷ 3.3 字/秒 ≈ 镜头时长」排播；前两句最要紧。
- **运镜物理事实**（`camera-movement.md`）：H3 不知道「慢」是多慢 → 推拉必带「距离 + 时长」双锚（`slides forward 12 cm over three seconds`）；不做升格/Hit-Stop/变速，要「顿」写受力结果；不认 `follow her`（`her` 可能解析成额外主体）→ 写相对位移；单镜只做一次运镜，分阶段运镜要拆成两个 `[Shot N]`；三要素（景别/角度/运镜）一次给齐，缺景别默认全景、缺角度默认正面平视。
- **氛围层六件套**（`atmosphere-and-light.md`）：参考图能覆盖的（外形/空间）一个字别写，覆盖不了的（光位/光质/空气介质/三色色板/前景遮挡景深/材质高光）写到死；至少写光位 + 介质 + 前景三件；位置在 `detailed_description` 的 `[Shot 1]` 之前，镜行里只许挂一个光/空气短语；空词 `cinematic/atmospheric` 回落平均先验；国漫 3D 塑料感四因：空词、继承平光资产图、高频增强、无介质。
- **坑**：竖屏优先；人格化文案；`SKILL.md` 仍偏长。
- **评级**：**采用（借机检 + 规则）**；`h3_lint.py` 可直接作为我们 skill 的 `scripts/lint.py` 起点。

### garycaogan/h3-ref-video（★29，MIT，2026-11-06）＋ garycaogan/mv-swap（★33，MIT）
- **定位**：RunningHub 上用 H3 Ref2VA 出片的 CLI/skill（用户不能用 RH，但**实验结论平台无关**）：中文分镜 + 「参考图片 N 是谁」→ 自动改写成官方六段式（Claude Code 作改写器，现取官方 `ref-en.txt`）→ 每镜一张分镜图（GPT Image，第一张作后续参考）→ 生成 → **查烧字幕** → 拼片。三种分镜图模式：`shot`（每镜一图，人多戏）/ `first`（每段只给首镜，后段接前段末帧，对白戏）/ `none`（只给角色图，动漫/cos）。
- **盲评结论**（同脚本同参考图，对 Seedance 2.0 mini）：动漫与 coser 片 H3 直出 4:0、4:0 赢，成本约 1/10；**中文真人对白戏 H3 直出 0:4 输**，垫一张首帧后哭戏 4:0 赢，带货戏仍输；每镜分镜图能让 H3 稳稳追平（15 条真人 cos 短片 8 Seedance / 7 H3）。
- **格式关键**：Seedance 写法直接喂 H3，7 段 7 段被垫 BGM、中文对白烧字幕、表演收着；工作流没有负面提示词，**「不要背景音乐、不要字幕」反而把音乐和字幕招进来**；改官方六段、去掉所有否定句、`non_diegetic_music: N/A` 后消失。
- **其它实测**：中文对白会烧字幕且会写错（「三千八」烧成 3000）→ 有台词段必查；垫分镜图的镜头开头 1–2 s 偏静「像照片动起来」；大情绪反应（惊吓/疼）偏小，要写具体脸部与身体动作；Ultra 机型 736×1312 30 步慢 8 倍贵 17 倍只换锐度，不值；参考图上传前缩到 1024 px。
- **mv-swap**：换人翻拍要求源片 ≥720p（360p 源换出来头发皮肤糊成一片），角色图穿成片服装、干净背景、全身；按镜头切、认人、审片全自动，`state.json` 断点续跑。
- **坑**：RunningHub + APIMart 付费路线；分镜图依赖 GPT Image（我们应换本地 Qwen-Image/Krea）。
- **评级**：**采用结论**（漫剧直出 / 真人先出分镜图 / 台词段必跑 OCR 查字幕），代码不装。

### 3ALLBUY14/h3-prompt-builder（★19，MIT，2026-10-30）
- **定位**：纯文档 skill（WorkBuddy / Claude Code）：5 模式格式、10 风格模板、六大压缩原则、`lipsync-guide.md`、`official-updates.md`（官方飞书手册 2026-09 + 开放平台 2026-10 复查）。
- **防火星语**（奥义护肤礼盒四版 Ref2VA 实战）：音频策略 `fully_copy`（低风险）> `reference` + **短音频 ≤8 s**（只提取音色，`<d>` 时间线唯一主导，首选）> `reference` + 长音频（时间线映射冲突、吞字、句边界双重起音）；**台词归属三选一**：口型同步（露脸、嘴清晰 `speaks to the camera… <d>`）/ 显式画外音（`says in an off-screen voiceover… while her lips remain completely closed`）/ 无台词（纯 B-roll 不放 `<d>`）——唯一触发火星语的形态是「有角色、有 `<d>`、没说谁怎么说」；`<d>` 要覆盖全程，空档会被火星语填充；音频 >15 s 中段加速口胡，重录到 14–15 s；「限时抢购」连读口胡 → 短促 CTA。
- **吞字**：句末随机吞字 = `<d>` 字数超过参考音频节奏容量；弱读虚词（都/也/就/了）固定被吞 → 换双字实义词；末句切点余量 ≥0.2 s。
- **文字渲染**：长串英文拆分弹出；`<d>` 台词与叠加字幕内容重复会被渲染两行 → 格式区分；特效字低饱和莫兰迪色 + medium-weight，不用 bold；颈部极简描述。
- **官方增量**：首/尾帧图片宽高 [256, 5760]、宽高比 5:2–2:5；视频 ≤50 MB、图 ≤30 MB、音频 ≤15 MB；参考视频输入帧率 23.976–60 fps；环绕不写「环绕」写 `truck left + pan right`；文字乱码官方解法是把文字做成图片当参考并声明「按图片理解」；远景不露脸只拍背影/空镜（国风 3D 示例）；**H3 Max**：480P/768P、5–15 s、无 2K、仅标准端点，5 s 768p <3 s 出片；**H3-Context-IR** `POST /v2/h3_context_ir` 返回三段结构化提示词不生成视频；**768P→2K 再生成**：重提原 `content` + `role=base_video`、`task_type=regeneration`。
- **评级**：**采用（借 lipsync 与官方增量两份 references）**。

### LoveRain1997/video-to-h3-prompt（★44，MIT，2026-09-20）
- **定位**：视频 → H3 提示词的取证式 skill（`SKILL.md` 10 步 SOP + 7 份 references + `onset_probe.py`/`audio_probe.py`/`forensic_probe.*`），姊妹仓 h3-prompt-journal 已在 04 簇。
- **方法**：稀疏网格建骨架 → 转折区 4–8 fps 密帧 → 音频两级取证（0.5 s RMS 包络 + onset 音头）→ 因果链（触发→动作→反应）→ 道具/身体状态表 → 现场/运镜/后期特效/声音四层分离；任何断言至少两通道支持，否则标「推测」。
- **六条铁律**：先判连续运镜 vs 离散快切；每个切换/定格是否挂在 onset 上；有参考图不写外貌；静态与爆发写成互斥两态并在时间轴/相机段/收束句三处重复；横置画面先怀疑相机 Roll；冲击可数不可糊。
- **片型分流**：A 一镜到底 / B 编辑式快照 `HARD LOCK ↔ INSTANT BURST` / C 多镜头快剪（命名机位语法 GUNNER/BUTT/PRONE…，切镜挂 onset，不可套 LOCK/BURST）。
- **硬规则**：`[Shot 1]` 无时间戳、后续严格递增、多段每段从 00:00 重计；自由散板禁写 BPM 改 `on the strong accent of <Audio 1>`；有目的运动的非身体物体必有画外控制者；原片无 BGM 写 `N/A` 禁脑补配乐。
- **评级**：**试用**（复刻参考片 / 换 coser 场景直接套 SOP）。

### MacroSony/minimax-h3-chained-character-swap（★32，MIT，2026-08-15）
- **定位**：Ref2VA 换人 + Motion Context 续接的 Agent Skill（Pi/Codex/Claude），含 `inject_tail_taper.py`、`audit_stitch.py`、`run_chain.py`（接缝审计不过则退出码 2 停链）。POC 576×1024、beta 20 步、124 帧、context 22 帧 video/head、每段交付 102 帧。
- **配方**：取上一段**干净**交付的末 22 帧 → 临时副本注入紫绿彩噪 19f@0.45、末 3f 渐弱到 0.10 → 喂 `MiniMaxH3ChainExternalVideo` → 生成 124 帧 → `MiniMaxH3LoopTrim` 裁 22 → 下一段 context 只从干净交付取（禁递归注入）。机制：`MiniMaxH3ChainContext` 把 22 帧 VAE latent 钉在目标时间轴头部 7 个 cond token（位置 0,1,5,9,13,17,18），context 区≈像素级复刻（diff 0.0035）后被裁掉；恒定 0.45 注入提升锐度但接缝残彩噪，0.20 无锐度收益。
- **工程坑**：**源片必须 24 fps**，30 fps 源不重采样会慢放 `fps/24`；`Video 1` 被 `MiniMaxH3ReferenceToVideo` 的 `adapt_canvas` 重设到 768 短边 / 768×1344 面积上限（16:9 → 1344×768）；新 `[Shot N]` 必须插在 `detailed_description` 内、`overall_soundscape` 之前（`prompt + shot2` 直接拼到末尾会被当成 `non_diegetic_music` 的一部分）；源片硬切要先用 64×36 帧差扫出切点再分段。
- **评级**：**试用**（仅慢/中速动作；与 02 簇 Motion Context 方案互补）。

### RK-BoilingPoint/H3-Visual-Marker-Control（★21，MIT，2026-09-25）
- **定位**：实验记录仓（不是节点）：在参考图上**手绘色框**（蓝框 = 主角、红框 = 配角、黄框 = 远处目标区域），提示词用纯英文解释框的含义并声明 `The colored boxes are non-diegetic visual control references only… Do not preserve, redraw, animate, or attach the colored boxes`。Ref2VA + Qwen3-VL-32B，RunningHub 工作流（三层楼的小肥猴 Remix / WorkFisher Easy），另用 dasiwa 非加速版交叉验证。
- **结果**：单人单框 10 s ✅（识别目标 → 走到区域 → 完成动作），叠加跟拍/推近/对话仍成立；双人三色框 10 s ✅ 两角色各自到达各自区域；失败/半成功：色框残留（02 案例）、提示词剪短后不稳定（04）、提示词与参考图矛盾时明显拉扯（12）。远处目标框按透视画小且在提示词里说明「小是因为远」。
- **价值**：短剧里「A 走到门口、B 坐到沙发」的站位调度多了一个零成本手段；与 forest-laoli 的空间锚点卡互补。
- **坑**：n 小、单作者；色框残留需多抽；提示词里仍大量 `must not`（与否定式禁令冲突，但在「框是非叙事参考」声明下可用）。
- **评级**：**试用**。

### muse-collective-26/MiniMaxH3-Director-V1.2（★57）/ -Seed-Hunt（★29）/ MiniMaxH3-Director（★26）（NOASSERTION，最后推送 2026-10-13）
- **定位**：ComfyUI 时间线导演节点（元数据漏标 comfy），单脚本按 CUT 切分、自动分块、Reference / First-Last-Frame 双模式、Hybrid Continuation（段缝经 FL2VA 权重硬锁）、Two-Stage Sampling（低清起步 latent 直升）、Seed Hunt（4 候选低清探种）+ Refine V2（沿同一 sigma 调度续采）。依赖 `ComfyUI-H3-Multishot` / `H3-Motion-Context-MultiRef`。
- **源码级发现**（`muse_minimax_director.py:713–760`）：旧版参考视频被**无条件截到 200 帧（≈6.67 s）**，导致「参考动作只跟前几秒」的长期误判；更关键——**官方 `MiniMaxH3ReferenceToVideo` 把传入帧当作已是 24 fps 序列，直接按目标 `frame_count` 截断后 VAE 编码，不做时间重采样** → 30 fps 源既被截短又慢放。修复是按每帧真实时间戳重采到 24 fps 网格。
- **VAE Re-encode Carry 实测**：段缝灰度帧差从 ~44–48（纯 anchor）降到 3.21（单段）/ 4.61（两段），落入片内正常波动 4–16 范围内。
- **其它**：参考视频 `retention` 文案曾与所选等级无关（已修）；多说话人 `(Sx)` 按块内首现自动编号；Refine 曾因用自己的 `steps` 重建 sigma 导致段缝音频乱码。
- **坑**：license 不明；节点体量大（4000+ 行）、依赖多；与 01 簇诸多 director 功能重叠。
- **评级**：**观望**（借两条事实：参考视频 24 fps 重采样、VAE 再编码硬锁段缝）。

### kitsune123150/minimax-h3-hybrid-cond（★53，无 license，2026-08-03）
- **定位**：ComfyUI 节点 `MiniMax H3 Hybrid Cond (R2V + I2V)`，一个 conditioning 同时接 `first_frame/last_frame`（fl2va keyframe）与 `ref_image_1/2`、`ref_video_1`、`ref_audio_1`（`<Picture N>/<Video N>/<Audio N>`）；`also_ref_first_frame` 可把首帧同时作为下一个 Picture。
- **机制**（`model_base_patch.py` 49 行）：monkey-patch `MiniMaxH3.extra_conds`，把 `minimax_keyframes` 与 `minimax_refs` 的 latent 顺序拼进 `holder.cond["cond_video_latents"]`，音频 latent 进 `cond_audio_latents`。可配 FL2VA 权重（首帧锁优先）或 Ref2VA 权重（身份优先）。
- **价值**：续接场景「上一段末帧作首帧 + 角色四视图作 Picture」一次完成；与 02 簇 Zzz1phyrf 等方案不同之处是不改 sampler。
- **坑**：无 license；2026-08-03 后未更新，未验证 ComfyUI 0.37.2；拼接后 `<Picture N>` 编号是否仍从 1 起要实测。
- **评级**：**试用**。

### animede/Minimax-H3-lipsync-mv（★20，Apache-2.0，2026-10-24）＋ animede/Diffusers_minimax-h3（★20）
- **定位**：日文本地 Web 应用（diffusers-movie-server 网关），一张角色图 + 歌曲/TXT → Ref2VA 口型同步 MV / 读稿视频。固定规格：Turbo ON、Vocal Lock ON、同参考图 prefix cache、Demucs 分离人声作 `<Audio 1>: fully_copy` 关联到 `<Subject 1> (S1)`，**歌词不写进 `<d>`**（直接对 `<Audio 1>` 口型），最终音轨用原曲；歌唱段强制正面或 3/4 中近景露嘴；每场 5–10 s 按无音/音量谷/换气/小节用 DP 切分。
- **可借数字**：参考图短边缩到 1024 px 比 2048 快约 15%、同种子画质相当（`H3_REF_SHORT_EDGE=1024`）；**脸部油光取决于参考图肤质而非量化**→ 用哑光、均匀照明的参考图；竖屏/方形自动加「主体居中」构图句；背景文字三档（只允许 1–3 词大字 / 不出字）；双卡时第二卡专做解码（1024×768 10 s 解码用 7.9 GB），场景间隔 131 s → 89 s。
- **Diffusers 版**：ck-w4a8（comfy-kitchen 0.2.37 的 W4A8 int8 kernel）在 4090 级 24 GB 上 320×448 141 帧 7.1 s（1.21× 实时，峰值 20.4 GB），5090 级 0.95× 实时；FirstBlockCache/Sage/Turbo/量化可热切换。
- **评级**：**观望**（结论可借，工程不装）。

### guangjun5952/minimax-h3-broll-generator（★48，MIT，2026-08-14）
- **定位**：Codex skill，口播逐字稿/视频 → 语义切段 → T01–T21 包装模板路由 → 每镜 H3 提示词 → `broll-plan.json` 审片后才付费生成 → 按时间戳回填口播。三档文字预算：v1 1 组 ≤12 字、v2 ≤3 组 28 字、v3 ≤2 组 18 字（推荐）。
- **可借规则**：H3 中文生成排版仍会错字，品牌名/法律文字/引用用确定性工具合成；每镜一个核心语义，3–4 阶段、4–7 有效元素、同屏 ≤2 组辅助信息；文字正对镜头高对比稳定 ≥1.5 s、最多两层低速运动；一个主运镜 + 一次回稳、一种强调色；B-roll 禁 BGM 只留同步拟音与环境音。
- **评级**：**借规则**（短剧字卡/片头字适用），skill 本身面向知识口播。

### AharaOoO/acheng-director-skill（★57，Apache-2.0 / 文档 CC BY-NC-ND，2026-10-01）
- **定位**：924 文件的「工业级导演引擎」v4.3.9：七模块（story/shots/performance/effects/assets/model/continuity）、132 段 1080p24 运镜白模视频（`data/camera-moves.json` 可检索）、36 决策卡、89 项门禁、2900 词红线、`compile_h3.py` 编译器、连续性账本（伤势/弹药/道具归属）。H3 侧直接内嵌官方 `h3-prompt-writing`（`base-en.txt/ref-en.txt`）。
- **可借思路**：文戏「五轨表演」（gaze/breath/shoulder/body_hands/dialogue）把情绪拆成可见肌肉动作；打戏「施力源→轨迹→接触→阻力停顿→传递→后坐」因果链 + `speed_profile`；慢动作只在接触 0.1–0.3 s 窗口（但 forest-laoli 实测 H3 根本做不了升格，需改写为受力结果）；反省略门禁（禁「同上」）；STYLE_MOTHER 风格母图锚定全部资产图。
- **坑**：首次响应强制输出 B 站广告横幅与版权声明；上下文极重；H3 特有判据远少于 swan7/forest-laoli；对 Seedance 一视同仁。
- **评级**：**观望**（只借表演/打戏分解模板）。

### AcademiaSD/AcademiaSD_LoRAlab-MiniMax-H3（★17，无 license，2026-10-01）
- 已并入 07 簇覆盖的 TrainerStudio，但 README 的「技术深潜」有 07 未记的训练约定：H3 条件是 Qwen3-VL-32B **第 50 层未归一化 hidden state**；VAE 用 ImageNet 归一化 over [0,1]；flow-matching `t = 1−σ` 且 t=1 为干净、速度目标 `x0 − noise`（符号与常规相反）；sigma 用 logit-normal + 分辨率 shift `mu = 0.5 + (tokens−256)·0.65/6144`，**采样用的 shift=12 对训练是错的**；导出要做 `mlp.fc1` 的 SwiGLU 半块交换；LoRA/优化器保持 fp32（AdamW8bit 会抹掉面部细节）。验证配方 8 图 576² 600 步 lr 2e-4 rank/alpha 16 ≈ 40 min（16 GB）。
- **评级**：**借约定**（写自训脚本时查）。

### Amduraznak/minimax-h3-fp16-fix（★58，MIT，2026-08-08）
- V100 专用（4090 原生 bf16 不需要），但解释了 H3 数值结构：`condition_proj` 首层输出 ~96k；残差流 attention-sink 行从 ~81k 增长到 ~4.3M（50 块内 ~50×），无固定 rescale 可救；`out_proj`/`fc2` 某些 sigma 下超 fp16 上限（fc2 >2M）。修法：残差流 fp32、分支 fp16、`out = f(x/K)·K`（K=64/256）位精确；V100 32 GB 1120×768 124 帧 30 s/step vs fp32 330–370 s/step。
- **价值**：解释为什么 H3 的 fp8/int8 量化要把 `proj_in/out`、AdaLN、残差加法留在高精度——评估第三方量化权重时的检查项。**跳过（仅作背景）**。

---

## 其余仓库一览

| 仓库 | ★ | 一句话定位 | 归类 |
|---|---|---|---|
| unslothai/unsloth | 79153 | 桌面端跑/训 LLM 与扩散模型，支持 GGUF，与 H3 关系只是 HyperFlow GGUF 可在其 Studio 加载 | 通用工具 |
| zhongkaifu/TensorSharp | 665 | .NET GGUF 推理引擎 + Video Studio，支持 H3 GGUF（HyperFlow）生成 | 通用工具 |
| MiniMax-AI/awesome-minimax-h3-integration | 549 | 官方生态索引（VRAM 表 / 节点 / 加速 / 训练），已作本调研总索引 | 官方索引 |
| MirroS-Lab/HarnessEval-W | 311 | 世界模型 agent 化评测框架，100 例公开集；与短剧无关 | 学术 |
| AIVFI/Video-Depth…Rankings | 264 | 深度估计/立体转换排行榜，仅一句「期待 H3 基础的新模型」 | 无关 |
| AtlasCloudAI/awesome-minimax-h3-prompts | 71 | 官方 showcase 案例库（2872 行 README，带 Atlas 推广链接） | 提示词库 / API 报价页 |
| xianyu110/awesome-minimax-h3-prompts | 64 | 274 条 X 平台提示词（202 作者原文 + 72 反推，已标注），最长 6602 字符 | 提示词库 |
| Anil-matcha/MiniMax-H3-API / awesome-minimax-h3-prompts | 56/27 | MuAPI 推广 SDK 与 30 例提示词 | API 报价页 |
| veda-sparse/Miowtion | 56 | Veda 稀疏注意力训练与 LoRA 微调（2×4090 FSDP2），已由 07 簇 Veda-on-ComfyUI 覆盖；附 1003 条 MovieGen 结构化 T2VA 提示词 | 训练 / 数据 |
| PotionUI/PotionUI | 55 | 自托管多用户生成工作室（Krea2/Flux/Wan/LTX/MiniMax），MCP 驱动，Video Director 分段 | 应用壳 |
| Video-Rebirth/hyperflow-h3-flash | 52 | 13.7B 蒸馏 H3（4–8 步无 CFG，Q4_K_M 9.1 GB），03 簇已覆盖 | 已覆盖 |
| SatoDive/Minimax-H3-Latent-Continuation | 51 | 基于 nkxx188 Easy 的 latent 存取 + Seed Video/Seed Ref Video 双参考续接节点（Patreon 工作流） | ComfyUI 节点（漏标） |
| SatoDive/Minimax-H3-Transparent-Video | 39 | 平底色生成后抠像出 ProRes 4444/RGBA PNG；工作流 `ModelSamplingMiniMaxH3 (6/3)` + Turbo 0.8 | ComfyUI 节点（漏标） |
| Argus-AiTeam/minimax-h3-mac | 50 | M4 Pro 24 GB MLX 流式跑满血 H3 + Turbo，1344×768 5 s 耗时 48 min | Mac 部署 |
| spacesimeco-hue/Chain-Motion-AI-Video-Editor | 50 | Frameforge：ComfyUI 后端的场景式桌面剪辑/生成器（takes 对比、运动衔接、Speech Studio） | 应用壳 |
| drowzeys/keys-heretic…Single-DGX-Spark | 49 | DGX Spark 配方：Sol-Attn + FBC 1.55×，Heretic NVFP4 TE，Spectrum，0.5 MP + RealESRGAN x2 | 非 4090 硬件 |
| mathruffian-dot/shanshiba-workflow-colab | 45 | 台湾校园奇幻喜剧频道的 Colab G4 全流程（YuE2 歌 + Qwen-Image + Ming TTS + H3），一场 1.5–2 h / 15–18 单元 | 云端流水线 |
| lpalbou/mlx-gen | 42 | mflux 分支的 Apple Silicon 图/视频运行时 | Mac 部署 |
| daexchef/Minimax_Grok | 41 | HTML 生成器输出长视频 ComfyUI JSON + Grok CLI/MCP skills.zip，RTX PRO 6000 30 s 规划 | 工具 / 过时 |
| aa335615543-ux/BUNNY_H3_Conditioning_Bridge | 41 | 语义桥 MLP 改写 cond token，01 簇已覆盖 | 已覆盖 |
| sjh00/minimax-h3-storyboard-prompt-skills | 41 | 官方 8 个风格 skill + h3-prompt-writing 的中文化移植 | 官方 skill 复制 |
| Yuliya1310/minimax-h3-workspace | 38 | Windows 安装包，内嵌 ComfyUI，本地 Gemma 4 写提示词，SeedVR2 超分；提到社区权重「Singularity v1.3/v2」「Pika H3 Flex」 | 应用壳 |
| ZeroLu/awesome-minimax-h3 | 37 | X 平台社区提示词按题材分类（教育/纪实/动作/情景喜剧/卡点） | 提示词库 |
| seraphinawolfe / barnabywren3 / ferguslindholm / harlowprewitt7 / oberonlindquist / duncangrimsby | 37/34/32/30/30/39 | 同一天（10-19）推送、互相引用的 ArgoLink SEO 仓库：skill/CLI/36 卡片/短剧管线，内容均为官方限制复述 + 报价表（$0.039/s） | API 报价页 |
| appautomaton/mlx-h3 | 36 | 纯 MLX H3 推理（pre-alpha），20 步 res_multistep | Mac 部署 |
| Tele-AI/TeleFuser | 36 | 流式多模态推理框架，H3 4×H100 服务 | 数据中心部署 |
| tonyd2wild/DS4-H3-Video-Gen-Factory | 35 | 两台 DGX Spark 同时跑 DeepSeek-V4 1M ctx + 两路 H3 480p | 非 4090 硬件 |
| dg1kjd/sglang-sxm2 | 35 | 4×V100 32 GB 跑 H3 的 SGLang 配方 | 非 4090 硬件 |
| qianye-wuyu/dual-model-video-prompt | 34 | Seedance 2.5 + H3 双模型 Brief→编译 skill（U1–U9 框架，image-first 资产管线） | 单文件 skill |
| fadeaway20242024/H3-comic-pv | 33 | 动漫角色 PV 包装 skill：三固定风格（高饱和 / 冰蓝版式 / 红白漫画）+ 时间块分镜确认制 | 单文件 skill（漫剧片头可参考） |
| hui-tony-zk/h3zero | 31 | Modal 无服务器部署 Turbo H3（RTX PRO 6000 480p 15 s ≈ 50 s） | 云部署 |
| gulucaptain/MiniMax-H3-Reason | 31 | 物理推理评测 517 例：H3 人工成功率 41.97%（ADR 音频消歧 27.4%，VDR 56%，MSR 多视角 43.5%） | 学术（结论可引） |
| Huage001/Ascend-H3 | 31 | 昇腾 910B 上 Full/VSA/Veda/VDN/Spark 五种注意力 INT8 对照 | 非 NVIDIA |
| drowzeys/keys-Mac-TensorFold-MiniMax-H3-MLX | 30 | M5 Ultra TensorFold：Turbo 5 passes + 基座 20 步「重配音」修复 Turbo 音频发糙 | Mac 部署（音频观点可参考） |
| wobushannes/Drehbuch--Referenzanker-Generator | 29 | 德/英剧本工作室 + 单行提示词压缩器 + 胶片模拟，多模型 | 工具 |
| Badim41/network_tools | 29 | 俄语多模型中转 API | API 报价页 |
| lololerigolo60/Minimax-H3-prompt-studio | 28 | CustomTkinter 桌面提示词构建器（Ollama/LM Studio/llama.cpp），Story→Sequences 自动分段 | 工具 |
| penposs/mvmaker-h3-skills | 28 | Codex MV skills：导演/分镜与官方 h3-prompt-writing 分层，整数秒 PCM 切片 + 四宫格故事板，RunningHub 队列 | skill（结构可参考） |
| VulcanEon/awesome-minimax-h3-max-prompts | 28 | h3max.io 维护的 48 例 H3/H3 Max 案例 | 提示词库 / API 报价页 |
| ZzzAloong/fight-scene-director | 28 | Codex 打戏设计 skill（站位图/轨迹图/双轨迹图提示词，15/30 s） | 单文件 skill |
| hoodtronik/minimax-h3-style-atlas | 27 | ostris/minimax_h3_1k 数据集 941 种风格索引，暴露官方 caption 三字段 `integrated_multimodal_description / overall_soundscape / non_diegetic_music` 原文 | 风格词表（可当风格句库） |
| killkli/minimax-h3-lora-colab-skill | 27 | Colab A100 训 Ref2VA LoRA 的 Codex skill，07 簇已覆盖 | 已覆盖 |
| HeyZhey/RunH3onMac | 27 | M3 Ultra 512 GB 用官方 144 GB 权重 + MPS 跑 FL2VA，附 `ForAgent.md` | Mac 部署 |
| KunLabAI/KunFlix | 27 | 影视广告 Agent 平台（无限画布、多 Agent、积分计费） | 平台壳 |
| xituisuany-max/dsh-client-ui-pet | 25 | DSH Web GUI 桌宠插件 | 无关 |
| RobZombAI/H3MLX | 24 | antirez h3.c 的 Metal 4 扩展，5 步 S-FMC 求解器 | Mac 部署 |
| wassermanproductions/wasserman-spark-director-h3-speed-recipe | 24 | 两台 Spark：H3 4 步 FP8 → latent 升采 + 适配器 → LTX-2.5 3 步精修 + 16-NFE 人声修复，8 s 片 2m54s | 非 4090 硬件（H3→LTX 精修思路） |
| EVZheng-Lab/h3-seedance-prompt | 23 | 一个创意同时出 H3 与 Seedance 2.5 两版提示词（固化官方飞书/火山手册） | 单文件 skill |
| turanszkij/mini-ai | 23 | C++/WinAPI 零依赖本地生成小程序，支持 H3 | 工具 |
| niw/mmh3 | 20 | Rust + CUDA/Metal 的 H3 专用推理引擎，可多机 RDMA 分布；03/11 已提及 | 已覆盖 |
| yeahdongcn/nautilus-studio | 20 | vLLM-Omni 后端的长片工作室（边界→锚帧续接） | 平台壳 |
| flaqai/awesome-minimax-h3-video-prompts | 19 | 84 条自写商用配方（参考图角色映射 + 时间线 + 一致性锁），多语种 SEO | 提示词库 |
| yume-arasaki/ezlaunch-minimax-h3 | 19 | 双击安装器（8 GB+ NVIDIA / Spark），自动映射 Turbo 工作流 | 安装器 |
| xxx-888/super_gen | 19 | SceneGen 商业短剧平台（剧本解析 → 分镜 → @引用 → r2va → 三轨剪辑） | 平台壳 |
| janishar/h3c-studio | 18 | h3.c 的 Go Web 前端（helmstudio） | Mac 部署 |
| MARK42IRPC/MinimaxH3-ONNX | 17 | H3 分片 ONNX 导出与 4 GB 显存边缘实验，03/06 已提及 | 已覆盖 |
| wodeshijie1234/faithful-h3-web | 16 | 本地 Qwen3.5 4B/9B GGUF 的「忠实转换」FL2VA/Ref2VA 提示词 Web 工具 + 漫画分格分析 | 工具 |
| juemin4-source/minimax-h3-guide | 15 | 4070 Ti 12 GB：cu130 升级 480 s → 47–74 s（6–8×），03 簇已覆盖 cu130 结论；附 9 图参考链插件 | 已覆盖 |
| pythonic2439/infinite-canvas-01 | 15 | infinite-canvas 二开，接豆包/dola 等付费 API | 应用壳 |

---

## 可写进 skill 的规则（只列本簇新增，≤15 条）

1. **运镜载荷**：做有运镜的镜头时用 20 步、Turbo LoRA 关、`res_multistep/simple`、帧数 ≥124（三段式动作用 192），`ref_image_size=max`；4 步 Turbo 几乎抹掉运镜，只能用于抽卡构图。（loopforge0）
2. **参考板取舍**：Ref2VA 只挂身份参考，不挂背景/场景参考板；背景板让运镜幅度减半（0.81× vs 0.47×）换来场景漂移降 4×，需要锁环境的产品/匹配剪辑镜头才挂。（loopforge0）
3. **开场景别**：运镜要收紧就从大全景开、要放宽就从近景开；dolly zoom / snorricam 例外，开在结束处。镜头/机身型号是装饰，要宽就写宽景别。（loopforge0）
4. **运镜句写法**：类型 + 幅度 + 速度写进动词句（`the camera pushes in … toward X`），默认不写修饰词（`large/fast` 过驱且不叠加，`small` 惰性）；甩镜必须命名落点；推拉写「焦距全程锁定」；摇镜不写焦距；横移不写「视线锁定主体」；升降写「姿态保持水平」。（loopforge0 + swan7）
5. **整圈环绕/子弹时间**：必须挂 pablodawson `minimax_h3_flf2v_lora_v1`（整段 caption 触发），同时写圈数 + `At` 起止时刻 + 「末了回到正面」收束句，不写速度词；荷兰角用 `H3_Dutch_Angle_Slider_v1`，权重即倾角（1≈20°，常用 2.0）；Jojocodex camera_motion LoRA 默认不挂。（swan7）
6. **否定式闸门**：效力排序「不提名字 ＞ 替换式否定（不保留 X，改为 Y）＞ 裸否定（禁）」；交付前用 L1 词表（不移动/不晃动/不转身/保持不变…）+ 白名单（不同/不仅/不断…）两级判定，命中 L1 必须正向化；「不要 BGM/不要字幕」会把 BGM 与字幕招进来，改写 `non_diegetic_music: N/A`。（swan7 + garycaogan）
7. **漫剧直出、真人先出图**：动漫/cos 题材 H3 直出可胜 Seedance；中文真人对白戏必须先出首帧或每镜一张分镜图（第一张作后续参考）再 I2VA/Ref2VA；有台词的段落成片必跑 OCR 查烧字幕与错字。（garycaogan）
8. **台词归属三选一**：每个 `<d>` 必须显式归属——口型同步（露脸嘴清晰 `speaks to the camera`）/ 画外音（`says in an off-screen voiceover … while her lips remain completely closed`）/ 无台词；`<d>` 覆盖全程不留空档；音色参考用 ≤8 s 短音频；末句与切点留 ≥0.2 s；弱读虚词（都/也/就/了）换双字实义词。（3ALLBUY14）
9. **台词排播**：H3 把全部 `<d>` 按文本顺序连续铺轨，`[Shot N]` 不决定发声时刻；用「字数 ÷ 3.3 字/秒 ≈ 镜头时长」配字数，前两句定基准；单镜正文 45–70 词，>100 词 FAIL。（forest-laoli）
10. **空间层防崩**：全片一张空间锚点卡（单数家具 + 站位 + 门窗初始开闭态）每段复述；每镜末尾一句正向维持句；未开门段写 `the … door stays shut`，开门段场景标 `partially_preserved`；画外敲门只进 `overall_soundscape`；人物不穿门洞/窗洞（alpha 融化）；一镜 ≤2 人且只给一人写动作、第二人禁 `watches him go`；禁 `wall of / rows of`；禁全蹲 + 低机位、薄物穿窄缝。（forest-laoli）
11. **氛围层**：参考图能覆盖的（外形/家具）一句带过，覆盖不了的（光源方向、光质、空气介质、三色色板、前景遮挡景深、材质高光）写到死，放在 `[Shot 1]` 之前；至少写光位 + 介质 + 前景；禁 `cinematic/atmospheric` 空词。（forest-laoli）
12. **运镜物理量**：推拉写「距离 + 时长」双锚（`slides forward 12 cm over three seconds`）；不写升格/Hit-Stop/变速，要「顿」写受力结果（`his head snaps back; the camera holds still`）；跟拍写相对位移不写 `follow her`；单镜只一次运镜，分阶段拆成两个 `[Shot N]`；景别/角度/运镜三要素每镜给齐。（forest-laoli）
13. **表演写法**：静止写「站在原地、呼吸、眨眼、衣发微动」不写 `completely still`；表情写「变化 + 时序」不写状态；禁「刚性单一姿势」类不可能指令（运镜幅度掉 80%）；音频槽不提相机/机位/镜头；不命名贴身装置（Snorricam rig 会被画出）。（loopforge0）
14. **参考视频 24 fps**：喂给 `MiniMaxH3ReferenceToVideo` / Motion Context 的参考视频必须先按真实时间戳重采到 24 fps（节点把输入当 24 fps 序列直接按帧数截断，30 fps 源被截短且慢放 fps/24）；16:9 源会被 `adapt_canvas` 到 1344×768。（muse-collective + MacroSony）
15. **参考图预处理与音频判据**：参考图短边缩到 1024 px（快 15%、画质同）；用哑光均匀照明的角色图（脸部油光来自参考图肤质）；`fully_copy` 语音有 ~0.45 s 系统位移；`reference` 音色迁移受角色表观性别强拉——先让 `<Subject>` 描述与音色性别一致，成立与否只能试听判定；`Subject N = S N = Audio N` 三线同号并与接线顺序一致。（animede + swan7）

---

## 未处理清单

- **xingheFF/minimax-h3-NSFW-skill**（★17）：README 404（HEAD/main/master 均失败），未读。
- 仅读 README、未浅克隆验证的 skill：fadeaway20242024/H3-comic-pv、ZzzAloong/fight-scene-director、penposs/mvmaker-h3-skills、qianye-wuyu/dual-model-video-prompt、EVZheng-Lab/h3-seedance-prompt、sjh00（官方中文化，未逐一比对差异）。
- 未读源码的 ComfyUI 漏标节点：SatoDive 两仓（latent 存取格式、Seed Ref Video 的 retention 处理）、kitsune `nodes.py` 的 INPUT_TYPES 默认值、muse Refine V2 sigma 续采细节。
- 未读的文档：daexchef `MASTER_BOT_BRIEFING`（30 s 规划）、wassermanproductions `REPRODUCE.md`（H3→LTX-2.5 适配器）、drowzeys Spark `RESULTS.md`、mathruffian `agent/skills/`、Yuliya1310 所提「Singularity v1.3/v2」「Pika H3 Flex」社区权重来源未核实。
- AtlasCloud / xianyu110 / ZeroLu / flaqai / VulcanEon 五个提示词库只看了结构，未抽样比对提示词质量（04 簇已覆盖同类）。
- 工程备注：本次与 ComfyUI 侧长尾子任务共用过 `scratchpad/survey/longtail/` 目录并被覆盖，已改用 `scratchpad/survey/lt_misc/`（README 快照在 `lt_misc/readme/`，浅克隆在 `lt_misc/repos/`）。
