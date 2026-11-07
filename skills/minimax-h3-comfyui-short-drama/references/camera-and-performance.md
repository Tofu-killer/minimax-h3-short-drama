# 运镜、表演、空间层与台词排播（实跑数据版）

> 来源：`docs/13-github-survey/09-long-tail-skills-and-misc.md`——swan7-py `h3-camera-motion-lib`（46 镜 × 130 条实跑逐镜 ✅/🟡/❌）、loopforge0 英文对照实验、forest-laoli-h3（`h3_lint.py` H1–H36）、garycaogan 盲评、3ALLBUY14、muse-collective / MacroSony 源码级发现。

## 1. 运镜能不能出来，取决于步数

- **4 步 Turbo 几乎抹掉运镜**，只能用于抽卡构图；有运镜的镜头精修用 **20 步、关 Turbo、`res_multistep/simple`、帧数 ≥ 124（三段式动作 192）、`ref_image_size = max`**。
- Ref2VA 只挂身份参考，**不挂背景 / 场景参考板**：背景板让运镜幅度减半（0.81× → 0.47×），换来场景漂移降 4×；只有必须锁环境的镜头（产品 / 匹配剪辑）才挂。
- 开场景别决定方向：运镜要收紧就从大全景开，要放宽就从近景开（dolly zoom / snorricam 例外，开在结束处）。镜头 / 机身型号是装饰，要宽就写宽景别。

## 2. 运镜句写法

- 类型 + 幅度 + 速度写进动词句：`the camera pushes in toward X`；默认不写修饰词（`large / fast` 过驱且不叠加，`small` 惰性）。
- 推拉写「焦距全程锁定」+ 距离 / 时长双锚（`slides forward 12 cm over three seconds`）；摇镜不写焦距；横移不写「视线锁定主体」；升降写「姿态保持水平」；甩镜必须命名落点；跟拍写相对位移不写 `follow her`。
- 单镜只一次运镜，分阶段拆成两个 `[Shot N]`；景别 / 角度 / 运镜三要素每镜给齐。
- 不写升格 / Hit-Stop / 变速；要「顿」写受力结果（`his head snaps back; the camera holds still`）。
- 整圈环绕 / 子弹时间必须挂 pablodawson `minimax_h3_flf2v_lora_v1`，写圈数 + `At` 起止 + 「末了回到正面」收束句，不写速度词；荷兰角用 `H3_Dutch_Angle_Slider_v1`（权重 ≈ 倾角，1 ≈ 20°，常用 2.0）；Jojocodex camera_motion LoRA 默认不挂。
- 不命名贴身装置（写 Snorricam rig 会被画出来）；音频字段里不提相机 / 机位。

## 3. 表演与静止

- 静止写「站在原地、呼吸、眨眼、衣发微动」，不写 `completely still`；表情写「变化 + 时序」不写状态。
- 禁「刚性单一姿势」类不可能指令（运镜幅度掉 80%）。
- 一镜 ≤ 2 人且只给一人写动作；第二人禁 `watches him go` 类跟随句。

## 4. 空间层防崩（forest-laoli）

- 全片一张**空间锚点卡**（单数家具 + 站位 + 门窗初始开闭态），每段复述；每镜末尾一句正向维持句。
- 未开门段写 `the … door stays shut`；开门段场景标 `partially_preserved`；画外敲门只进 `overall_soundscape`。
- 人物不穿门洞 / 窗洞（alpha 融化）；禁 `wall of …` 类堆叠描述。
- **氛围层**：参考图能覆盖的（外形 / 家具）一句带过；覆盖不了的（光源方向、光质、空气介质、三色色板、前景遮挡景深、材质高光）写到死，放在 `[Shot 1]` 之前；至少写光位 + 介质 + 前景。

## 5. 台词排播（与 prompt-format §4 互补）

- H3 把全部 `<d>` **按文本顺序连续铺轨**，`[Shot N]` 不决定发声时刻；字数 ÷ 3.3–4 字/秒 ≈ 镜头时长，前两句定基准；单镜正文 45–70 词，> 100 词 FAIL。
- 每个 `<d>` 显式归属三选一：口型同步（露脸、`speaks to the camera`）/ 画外音（`says in an off-screen voiceover … while her lips remain completely closed`）/ 无台词；`<d>` 覆盖全程不留空档。
- 末句与切点留 ≥ 0.2 s；弱读虚词（都 / 也 / 就 / 了）换双字实义词；音色参考 ≤ 8 s 短音频。
- `fully_copy` 语音有 ~0.45 s 系统位移；`reference` 音色迁移受角色表观性别强拉——`<Subject>` 描述与音色性别要一致；`Subject N = S N = Audio N` 三线同号并与接线顺序一致。

## 5b. 60 集量产结论（egguy886 h3-drama-kit）

- 开场全景必须**动**（运镜 + 持续动作）：固定全景开场首秒动作量 2.9 vs 推 / 跟 19.6；删 `holds a static shot`；全片 `slow motion` 最多一次。
- 打斗**每一击单独一镜 0.8–1.4 s、一镜一动作**，写一次 `All action plays at full real-time speed`。
- **对白段不要精简提示词**（人声会提前 1.5 s 开口）；动作段可用 < 400 词精简版（动作量 +60%）。
- 台词里的 `...` 换成逗号（否则停顿处塞乱码插词，换 seed 无用）；总述只写动作不转述台词；英文氛围句删掉并加 `Speak only the quoted dialogue lines`（多说词 9.3% → 1.3%）；个别段被念出声线开头时只对该段去掉 `Name, a man of N:`。
- 生成时声音行全集统一「安静房间底噪 + 动作声 + 干净人声」，环境声 / 音效 / 配乐后期按场景连续铺；原生对白音色每段漂 1.7 半音，用 seed-vc 统一而不是 TTS 重配。
- 每镜 ≥ 2.5 s（含末尾停留），`max_shots = floor(duration / 2.5)`；按台词估时：中文 4.3 字/s + 标点 0.4 字 + 0.25 s 起 + 0.55 s 收，收尾镜 +15%。
- 无台词片不接音频参考、不声明 `<Audio N>`。

## 6. 题材判断（garycaogan 盲评）

- 动漫 / cos 题材 H3 直出可胜 Seedance（4:0）；**中文真人对白戏直出 0:4 输，垫首帧后 4:0 赢**——真人对白段必须先出首帧（或每镜一张分镜图，第一张作后续参考）再 I2VA / Ref2VA。
- 有台词的段落成片必跑 OCR 查烧字幕与错字；「不要 BGM / 不要字幕」会把 BGM 与字幕招进来。

## 7. 参考媒体预处理（源码级）

- `MiniMaxH3ReferenceToVideo` / Motion-Context **不重采样参考视频**：输入当 24 fps 序列按帧数截断，30 fps 源被截短且慢放（fps/24）——先按真实时间戳重采到 24 fps；16:9 源会被 `adapt_canvas` 到 1344×768。
- 参考图短边缩到 1024 px（快 15%、画质同）；用哑光均匀照明的角色图（脸部油光来自参考图肤质）。
- 否定式效力排序：不提名字 ＞ 替换式（`不保留 X，改为 Y`）＞ 裸否定（禁）；交付前过 L1 词表（不移动 / 不晃动 / 不转身 / 保持不变…）+ 白名单（不同 / 不仅 / 不断…）两级判定。
