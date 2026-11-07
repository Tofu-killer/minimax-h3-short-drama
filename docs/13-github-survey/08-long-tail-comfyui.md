# 08 · 长尾扫描：ComfyUI 相关、8 ≤ ★ < 40 的 219 个仓库

> 调研日期 2026-11-07。范围：`relevant.json` 中 `comfy=true`、`8 ≤ stars < 40`、非 fork、且未在 01–07 精读过的 219 个仓库。方法：全部拉取 README（≤150 行）做三分类；对「可能有新东西」的 39 个仓库浅克隆（`--filter=blob:limit=150k`）读节点源码确认机制与默认值；其余 180 个只给一行定位。所有速度/画质数字均为作者自报，并注明作者硬件。目标环境仍是 Win11 + RTX 4090 24 GB + ComfyUI 0.37.2 + int8_convrot + nvfp4 CLIP + lightx2v Turbo + SageAttention。

## 结论：长尾里值得补进 skill 的 ≤10 个仓库

1. **hako-mikan/comfyui-minimax-h3-negpip（AGPL-3.0）**：H3 唯一可用的「负面提示词」实现——`(phrase:-1…-5)` 翻转该词 V 向量符号，支持 `@start-end` 时段、`@v`/`@a` 单模态；填补 04/07 簇「H3 没有负向通道」的空白。采用（AGPL 只引用用法不打包代码）。
2. **pepikir/minimax-h3-speedup（MIT）+ Mu5hr00moO/CLIPCached（MIT）**：「条件编码落盘、按种子复用」族——32 GB 内存机器上 80% 墙钟时间不在采样；缓存条件后每多一个 seed 950→352 s（3090）；附 EasyCache `end_percent` 0.70 的实测修正与 `--cache-none` 语义澄清。采用规则。
3. **matsuo-koya/minimax-h3-notes（MIT）**：一个月 5090+4090 实测笔记：comfy-kitchen INT8 attention 采样 ~2×、**4090 上 345 帧悬崖（328 帧稳定）**、宽 1280→1216 解码省 15%、VAE tile >256 直接破图、FastH3 4 步 LoRA 转换（fc1 半区顺序）、TaoMate 3 步。采用结论。
4. **shootthesound/ComfyUI-Fizgig-H3-Tweaks（MIT）**：训练无关模型补丁：Detail&Contrast（latent 残差高频带，默认 0.15、跨帧稳定）、Scene Variation（子种子）、Prompt Strength（放大文本行 V 当 CFG 替代）。对 Turbo 无 CFG 链路是真正的新旋钮。采用（6 步 Turbo 验证）。
5. **cicalooo/ComfyUI-H3-PowerLoraStack（Apache-2.0）**：量化底模上的 LoRA 用运行时低秩分支而非反量化合并（合并引入 ~1.5% 权重噪声，w4a8 上只还原 <1/3 的 LoRA）、dense↔curve AdaLN 换基、按模态缩放、按 sigma 调度。修正 03 规则 18 的「合并 vs bypass」争论。采用。
6. **wjc573/ComfyUI-H3LatentUpscale-jingchen573（无 license）+ rockerBOO/h3-latent-upscaler（GPL-3.0）**：二采两条硬规则——latent 宽高必须为偶数（像素 32 倍数）否则核心 circular padding 出边缘色条；stock `AddNoise` 对 CONST 流模型会被采样器二次缩放成花屏，音频分支还要按 shift 3 单独算 sigma。采用规则（自己写节点或用 ResCascade 等已处理的包）。
7. **stuubszzz/Stubelius-Ultimate-H3（NOASSERTION）**：5090 上 PDMD / FastH3 Omni / Pika H3 Flex 三家 75 段同 seed 对照（速度、台词逐字率、跨段音色匹配、定格帧数、光流幅度），以及分段衔接四种模式的结论。只借数据与规则，不装（33 个 py 文件 + NOASSERTION）。
8. **BennyDaBall930/ComfyUI-Open-H3-FaceRegion（Apache-2.0）**：Open-H3-Regenerate-2K 的脸部保护——人脸区域从 σ0.50 起而非 0.909（`face_strength 0.55`），ArcFace 0.52→0.91、口型保留。06 簇说「Regenerate 会改脸」的直接解法。试用。
9. **mark9009/ComfyUI-H3-LongTake（MIT）**：V2V 风格迁移（NRDX StyleTransfer LoRA r64 + `source_role=guide`）、I2V 链 `anchor_mode=inpaint` 比 keyframe 接缝跳变 5.4–6.8× → 1.5–1.7×、脸部相似度逐项实测（加脸部特写 `<Picture 2>` +0.12，8 步 v1.0 闪烁 −18%）。试用 + 借数据。
10. **beijinren/ComfyUI-H3-Context-Noise（MIT）+ ethanfel/Timed-References（GPL-3.0）**：换人续接链的「锥形加噪」配方（22/0.45/0.10/3）消色彩残留；Qwen-only 时间戳参考不占 9/3/3 名额。借规则。

**不要碰**：biyuhe NB-HyperStep（跳过 50 块中的 34–38 块）、Icyoung TeaCache（未校准多项式、作者自测 3× 但 synctile 实测构图漂移 SSIM 0.58）；supElement AutoContext 功能最全但仍 monkey-patch `PackedLayout.__init__`/`extra_conds`（新版自动跳过）且带 11 MB 语义桥与 SeC-4B 追踪，与 01/02 互斥名单同列。

---

## 一、有新信息的仓库（源码级确认）

### hako-mikan/comfyui-minimax-h3-negpip（★19，AGPL-3.0，最后推送 2026-09-08）
- **定位**：A1111 Regional Prompter 作者把 NegPiP 搬到 H3：`(word:-1.0)` 把该词从提示词中**摘出单独编码**（权重 1.0，不缩放 Qwen 隐状态）、追加成条件行，再在 50 个 DiT block 的自注意力里**只翻转该行的 V**（`minimax_h3_negpip.py` 950 行：`calc_cond_batch` wrapper 传权重 → `diffusion_model` wrapper 临时替换 `optimized_attention`，调用结束即还原，不脏模型）。
- **关键参数**：`value_strength 1.0`（−1 = 精确符号翻转，可用到约 −5）、`block_start/end/stride 0/999/1`、`protect_text_rows`（负权重反而增强时打开）、`measure_attention_mass` 诊断。时段语法 `(neon signs:-1.5@2.5-4.0)`、`@v2.5-4.0` 只视频、`@a` 只音频、`@2.5-`/`@-2.0`；**带时段的组即使正权重也会被摘出**，窗口外乘 0。
- **用法要点**：MODEL 与 CLIP 都必须经过本节点；装了它括号就变成权重语法，字面括号要 `\(`；短语优于单词（`(red fruit:-3)` 好于 `(red:-3)`），2–4 个实词最佳；作者坦言时段「碰巧对上就好」。
- **与已覆盖项目关系**：04 簇共识「否定句不进正文」与 07 簇 ComfyUI-Dials 之外，第一个真正的负向通道；与 Fizgig Tweaks 的 Prompt Strength 同属「改文本行 V」的手法，可共存（后者乘倍、前者翻号）。
- **坑**：AGPL-3.0；`embedding:` 不支持负权重；int8 attention 后端下时段分割会多几次 attention 调用。
- **评级**：采用（抽卡阶段去除顽固元素）。

### shootthesound/ComfyUI-Fizgig-H3-Tweaks（★32，MIT，最后推送 2026-09-25）
- **机制（h3tweaks.py 325 行）**：`set_model_patch_replace` 每 block 一个 dispatcher；对视频行的 block 残差 `d = out − in` 按 2×2 token 网格做高斯分带：`detail = d − blur(σ1)`（「stable across frames」模式取跨帧均值再广播，避免闪烁）、`contrast = blur(σ1) − blur(σ3)`、`composition = blur(σ3)`；Prompt Strength 用同数学的替代 Attention，把文本行 V 乘 `(1+strength)`。
- **默认/窗口**：Detail&Contrast 默认 0.15，只作用于后半步数；Scene Variation 作用于前 1/3 步（±0.1–0.3 当子种子）；Prompt Strength 从 0.2 起步（Turbo 无 CFG 时的「提示词跟随」旋钮）。6 步 Turbo 验证；两节点串联相加。
- **兼容**：与 Block Skip/Token Route 等「替换 block」节点抢同一 patch 位，二选一；与 LoRA、任何采样器共存。
- **评级**：采用（短剧「皮肤更脆/更柔」与抽卡微调）。

### cicalooo/ComfyUI-H3-PowerLoraStack（★19，Apache-2.0，最后推送 2026-10-11）
- **核心结论（README 实测）**：ComfyUI 原生对量化层的 LoRA 路径是 反量化→加 delta→`requantize(scale=recalculate)`，往返**不幂等**，注入 ~1.5% 相对权重噪声，而 H3 LoRA delta 只有 0.01–0.08%；w4a8 上合并只还原 <1/3 LoRA 幅度（cos 0.12–0.14）且耗时 128 s vs 6.5 s。本包改为运行时低秩分支 `y = W_q(x) + B@A@x`（rank 64 约 +1.5% FLOPs），`quantized_layers=auto`。
- **AdaLN 换基**：dense（2688 宽 `silu(time_embedder)`）↔ curve（pruned `adaln_t_table [grid,8]`）LoRA 互转，`A' = A@V` + `.diff_b` 偏置，cos 0.999998；解决 `adaln_proj ... shape '[96768, 8]' is invalid` 跳层（06 规则 12 说可忽略——对 Turbo 蒸馏 LoRA 常数项≈100%，**不能**忽略）。两份 curve bake 可能同宽但不同基（cos −0.375），优先用「训在你跑的那份权重上」的 LoRA。
- **其它节点**：`adaLN Modality`（video/text/audio 三段各自缩放）、`LoRA Schedule`（按步或 sigma 的 linear/cosine/step 曲线）、`Inspector`；alibaba-pai Acc/PDD 32 区间输出头银行按步混合而不崩。
- **数据**：同为强度 1.0 的 H3 LoRA 扰动幅度跨 **65×**（0.054%–5.24%），rank/文件大小无关；auto-balance 只削不增。
- **评级**：采用（多 LoRA 叠加与 Turbo+风格 LoRA 组合时）。配套 **Dantemss/ComfyUI-H3-Modality-Lora-Loader（★8，MIT）**：按 packed 行掩码把 LoRA 限定到 video/audio/text（含 AdaLN 时间步掩码），每节点每步 +2 次矩阵乘。

### pepikir/minimax-h3-speedup（★12，MIT，最后推送 2026-08-10）
- **数据（3090 24 GB + 32 GB RAM，864×480×124f×20 步）**：TE 加载 121 s + 编码 206 s + DiT 加载 226 s + 采样 199 s + VAE 解码 123 s；采样只占 21%。15.7 GB 编码器与 21 GB DiT 塞不进 32 GB 内存 ⇒ 必须 `--cache-none` ⇒ 每次都全量重载。
- **机制**：四个节点 `H3SaveConditioning/LoadConditioning/SaveLatentAV/LoadLatentAV`（pickle，整个条件对象含 `minimax_keyframes` 一起存——LTXVideo 的通用条件保存节点会悄悄丢 keyframes 把 i2v 变 t2v）。分三相图：编码相（只 CLIP）→ 采样相（无 CLIPLoader，可去掉 `--cache-none` 与 `--disable-smart-memory`）→ 解码相。每多一个 seed：950→352 s（缓存条件）→204 s（模型常驻）→155 s（Sage）。
- **EasyCache 修正**：`subsample_factor=8` 写死，1280×736 下只看 5×10 网格，后期高频精修步被误判跳过（默认跳 9/11/13/15/16/18/19 步）→ 纹理织纹 + 色块；**`end_percent` 0.95→0.70** 去掉全部可测颗粒（码率 1.80→1.387 Mbps ≈ 无缓存 1.391），只保留约 31% 提速；`reuse_threshold` 0.05 等于全不跳（PSNR ∞），不是质量旋钮。
- **其它**：Sage 在 Ampere ≤56k token 干净，185k token（1920×1088×362f）出噪声未定论；Turbo LoRA 装上必须看到 `208 patches attached`；10 步 Turbo 是地板（6 步音频削波 −0.0 dB，4 步 Spectrum 零预测）；NVMe 让编码 90→25 s；「480p 渲染 + RealESRGAN ×4」比直出 720p 慢 13%。
- **评级**：采用规则。同族：**Mu5hr00moO/CLIPCached（★18，MIT）** 以 safetensors 落盘、`refresh` 强制重编、表格列出什么会/不会失效（seed/采样器/LoRA 不会）；**HEEEeeeeN（★22，MIT）** 把条件固化成 `.pt` 批量多 seed/云算力，附分镜导演 skill 与 Excel 审阅表。

### matsuo-koya/minimax-h3-notes（★33，MIT，最后推送 2026-09-14）
- **定位**：5090（WSL2、ComfyUI 0.33）+ 4090 worker 一个月口播 MV 产线的实测日志（日文全文 `H3_SPEEDUPS.md`）。
- **速度**：1280×704×5 s：20 步 ~270 s → Turbo 8 步 125 s → **+comfy-kitchen INT8 attention（核心 `ModelAttentionBackend`）79 s**（采样 ~2×；4090 Q4_K_M GGUF 1.34–1.79×）；TaoMate-H3 3 步 LoRA 再 1.4–2×（euler+simple 3 步 + shift 12/3 即复现其 0/16/33/49 调度）；FastH3 4 步 LoRA 比 Turbo 8 步快 1.87×、口型相关 +0.36–0.53 vs +0.21–0.28。
- **4090 专属坑**：**345 帧悬崖**——7 跑 6 跑慢 3–17×（491→8626 s），原因是个别 step 停滞 2.5–4.8×；328 帧 11 跑全部 882–897 s（1.7%）→ 单段上限取 328 帧（19×17+5）。宽 1280→1216 让 VAE 解码 tile 28→24、总时长 −15%；tile 512/768/不分块不更快且 PSNR 40→21 dB 出 16×16 格子（解码器是 256 px ViT）。
- **运维**：采样中轮询 ComfyUI HTTP 会停 18–43 s；ComfyUI 在 CUDA 崩溃前先「劣化」（单段慢 1.8×）→ 见信号即重启；杀毒实时扫描拖慢加载。LoRA 转换：diffusers `[value;gate]` vs ComfyUI `[gate;value]`，fc1 半区不交换则「风格能迁移、身份不行」，fused qkv 需块对角 lora_B（工具 `tools/h3_lora_convert.py`）。
- **负结果**：ToneCompensate 偏差 <1/255 且方向不一致；H3-Optimizations `H3MemoryOptimization` 1.27× 但输出不再同 seed 一致；FastH3 adaln 载回 pruned 基座数学可行但身份 0.669→0.613。
- **方法论**：小测试只能证明「没坏」，采纳/拒绝必须在生产分辨率、时长、素材上做（TaoMate 在 832×480 口播上口型相关 −0.10，在 1280×704 唱歌上身份反升）。
- **评级**：采用结论。

### sepiablue-ai/ComfyUI-H3-X2-Stream（★38，GPL-3.0）+ sepiablue-ai/minimax_h3_workflows（★28，MIT，均 2026-10-15）
- **机制**：把「X2 Detail VAE v1」（5.25 GB，544×960 latent 直接解码到 1088×1920 的 2× 细节解码器）在 ComfyUI 内一次转成 INT8（2.83 GB）；`H3 X2 Decode + Stream Save` 边解码下一 chunk 边用 NVENC 编码（`cq 18`，`fp16_accumulation`）；附 `H3 Chunk FeedForward` 2048 token 分块（默认阈值 4096）。
- **数据（4070 12 GB，FL2VA 544×960 采样 → 1088×1920）**：FP16 X2 86.7 s → INT8 X2 + NVENC 59.7 s（−31%）；Ref2VA 91.6→68.9 s。workflows 仓库：`fused4_sla5_x2.json`（MATLOW 融合 Turbo 4 步 + 核心 SLA 5% + X2 VAE）**62.6 s** 出 5 s 1088×1920；`fl2va_turbo8_veda90_x2` 134 s；FastH3 VSA 5% FHD 3m55s；PR #16072 top-k 10% 1024×1792 4m19s（需 `--disable-comfy-compiler` 否则末步 CUDA graph 卡 90 s）。
- **对 4090 的价值**：16:9 对应 960×544 → 1920×1088 的「半分辨率采样 + 2× 细节解码」路线，比 06 簇的 latent 放大二采更便宜（无第二次采样），但 X2 VAE 不是 ComfyUI 官方件，画质需与 ResCascade A/B。注意「Sayaka Benchmark」网站是作者自建基准。
- **坑**：GPL-3.0（节点）；要求 ComfyUI 0.37.0+、PyAV NVENC、comfy-kitchen 0.2.35；作者另有 LBH-X2-Stream（3 低清步 + 1 高清步，14 s 片 −25%）与 AudioFirst-X2-Stream（先出音频再锁，减金属声）。
- **评级**：试用（抽卡 1080p 直出路线）。

### wjc573/ComfyUI-H3LatentUpscale-jingchen573（★25，无 license，2026-08-17）+ rockerBOO/h3-latent-upscaler（★13，GPL-3.0，2026-08-05）
- **对齐规则（`__init__.py`）**：H3 视频 VAE 空间压缩 16×、DiT patch 2×2 ⇒ 二采 latent 宽高必须为偶数（像素被 32 整除）；奇数轴会触发核心 circular padding 再裁回，右/下边缘出接缝、色条。节点读入一采 latent，短边先向下对齐，长边取最接近短边倍率且 ≤ `scale_by` 的偶数；输出 width/height/effective_scale/alignment_info。
- **rockerBOO 的三个坑**：① stock `AddNoise` 对 NestedTensor 直接 `count_nonzero` 崩 → 先 `LTXVSeparateAVLatent` 分开加噪再合；② 对 CONST 流模型，`SamplerCustomAdvanced + DisableNoise` 内部会再做一次 `noise_scaling` ⇒ stock `AddNoise` 结果被二次缩放成花屏，需 `MiniMaxH3AddNoise` 多做一次 `inverse_noise_scaling`；③ 音频分支的 sigma 必须按 shift 12→3 换算（`MiniMaxH3ShiftSigmas`，denoise 0.4 时视频 σ0.4 对应音频 σ≈0.14），否则音频失真；`MiniMaxH3ConditioningUpscale` 同步缩放 `minimax_refs/minimax_keyframes`。起点 `scale_by 1.5 / bilinear / simple 15 步 denoise 0.4`（未调优）。
- **与已覆盖项目关系**：06 簇路线 B（ResCascade）、D（Tr1dae）内部已处理这些，但手搭二采图或用 LBH 原版示例时必须自己满足；BSAI Sol-H3、TaoMateHD README 也独立强调 32 px 对齐。
- **评级**：规则采用；节点可选。

### beijinren/ComfyUI-H3-Context-Noise（★23，MIT，2026-08-18）
- **机制**：给 Motion-Context 的 `context_latent`（潜变量步，音频不动）或 `context_frames`（像素，6 色调色板块噪）尾部注入锥形噪声：窗口内平坦 `alpha 0.45`，末 `ramp 3` 帧线性降到 `alpha_end 0.10`（配方 22/0.45/0.10/3 来自 MacroSony/minimax-h3-chained-character-swap）。目的：上下文「太干净」时模型照抄上一镜纹理色彩，换人链在 trim 边界后立刻露出色彩残留。
- **参数**：`tail_frames` = MC 的 `context_length`（22）；latent 节点只接受 5/22/39/56 的整步数（2/7/12/17 步）、`ramp_steps 2`、`noise_scale match_latent_std`；一次性使用，不要把加噪结果再喂回下一环。
- **评级**：试用（仅换人/换装续接链）。

### rkfg/ComfyUI-MiniMaxH3-ToneCompensate（★23，MIT，2026-08-24）
- **机制**：H3 续接段相对钉入关键帧偏暗，节点在重叠区（source 末 `overlap` 帧 vs target 首 `overlap` 帧，默认 48）估计偏差并整段撤销；`frame_shift`（逐帧逐通道加性平移，最后一帧的平移量延伸到后续）> `gain_bias` > `lut`。
- **反证**：matsuo-koya 在三类场景实测偏差 <1/255 且符号不一致（夜景 +2.8%，白天 −0.5%），判定「不需要」。02 簇规则 27 的全局拉平仍是首选。
- **评级**：观望（只在肉眼可见的接缝变暗时试 `frame_shift`）。

### mark9009/ComfyUI-H3-LongTake（★37，MIT，2026-10-21）
- **定位**：逐 clip 渲染的长视频三件套（运动/身份迁移、风格迁移/换材质、I2V 长片 + Refine），只依赖核心 ≥0.34，16 GB 卡验证；每 clip 落盘可续跑/单段重做；`longtake_nodes.py` 2703 行。
- **风格迁移**：`source_role=guide` + NRDX **StyleTransfer LoRA v1.0 r64**（Civitai 2932297）1.0，提示 `style_transfer: … the style of <Picture 1>: …` 或纯文本（Van Gogh/Ghibli/Simpsons 实例）；换人用 `reference` 不挂该 LoRA，可配 akatz-ai Character Swap LoRA。
- **衔接实测**：I2V 链 `anchor_mode=inpaint`（上段末帧复制进 latent 并用 mask 保护）vs `keyframe`（作为 guide 让模型重画）：接缝处帧间变化 5.4×/6.8× → 1.5×/1.7×；`context_frames=22` 反而恶化到 19×，默认 **5**。`seam_match=color`。
- **脸部实测（13.7 s 换人，ArcFace 均值/最差秒）**：0.5 MP 只 `<Picture 1>` 0.60/0.51 → 加脸部特写 `<Picture 2>` 并在提示词点名 **0.72/0.52** → 同图再接第三次 +0.01 → 换 **Turbo 8 步 v1.0 768p**（代替 4 步 v0.1）闪烁 −18%、最差秒 +0.11（0.74/0.63）→ Refine 1.0 MP denoise 0.25 带 `face_image` 0.79/0.68。int8 与 NVFP4 文本编码器输出一致，64 GB RAM 选 NVFP4。
- **耗时**：16 GB 卡 544×960×124f Turbo 4 步 ≈4:40/clip（Qwen 58 s、采样 2:35、解码 40 s）；60 s ≈ 12 clip ≈ 1 h。段间卸载模型（否则 Qwen 编码 1→10 min）。
- **评级**：试用（风格化短剧与换人链），数据采用。

### ethanfel/ComfyUI-MiniMax-H3-Edit（★38，MIT，2026-09-10）+ ethanfel/ComfyUI-MiniMaxH3-Timed-References（★11，GPL-3.0，2026-08-31）
- **H3-Edit 机制**：六节点静帧/编辑包；每个参考可选 **semantic（只进 Qwen，不占 `minimax_refs`）** 或 native（Qwen + VAE ref）传输；「加这副眼镜」用 semantic。角色表模式在**一次连续采样**内出所有视角：4 面板 73 帧取 `2,24,45,68`、6 面板 124 帧取 `2,21,42,63,84,113`、8 面板 171 帧 `2,21,42,63,84,108,131,160`；`clothing 6 views` 固定长焦等距 0/60/…/300°；示例 768×1344、Euler + linear-quadratic 25 步、REF2VA。Directed 预设（重摆姿势/换人/新机位）= FL2VA 首帧强锚 + 39 帧「稳定」后抽 1 帧。Scene coverage 把同法推广到整间屋：124 帧 6–8 视角、362 帧 12–16 视角，可 360° 回环（首末帧同一 latent）。
- **Timed-References**：挂在 CLIP 线上，`#tag` 在 tokenize 时替换为下一个空闲 `<Picture N>`，图片以 Qwen 视觉 token 形式在指定秒数「出现」，**不 VAE 编码、不占 9/3/3 名额**；尺寸 64–1280（建议 256–512）；实验性视频版接核心 Load Video 保留真实时间戳。
- **与已覆盖项目关系**：06 簇 Contact-Sheet/OrbitSheets 是五视图 LoRA 路线，这里是无 LoRA 的「轨道相机 + 抽帧」路线，可互为备选；Timed-References 与 04 簇「`<Picture N>` 只给具体帧锚」互补——属性/道具类用 semantic。
- **评级**：试用（角色设定图、道具语义参考）。

### BennyDaBall930/ComfyUI-Open-H3-FaceRegion（★11，Apache-2.0，2026-10-30）
- **问题**：Open-H3-Regenerate-2K 从 σ0.909 重画 2560×1440，脸与草稿 ArcFace 只剩 0.52。
- **机制**：YuNet（CPU，230 KB）逐帧找脸 + 手动框 → 映射到 2K latent 的逐 token 图 m；`Region Noise`：每 token 起点 `(1−m·s)·draft + m·s·noise`；`Region Strength`：把 m 作为 H3 逐 token 视频 denoise mask，每步按 `m·sigma` 走各自调度。整帧仍同步去噪（不是 inpaint），光线运动一致。
- **参数**：σ 表 `0.909375, 0.857143, 0.666667, 0`（3 步），`face_strength 0.55`（脸从 0.50 起；0.60–0.70 更多新纹理少身份；≤0.40 脸不再提升）、只挂 Kijai Open-H3-Regenerate-2K refiner（r384 或 155 MB r16）1.0、不叠 Turbo/Sharp、音频用草稿原音。结果：脸匹配 0.91、口型保留、细节 10.8× 于普通放大。
- **依赖**：rdh9616/ComfyUI-Open-H3-Regenerate + LBH 3D 放大器 + OpenCV/SciPy。
- **评级**：试用（当 06 簇 ResCascade 保真路线细节不够、又不想重画脸时）。

### alaintural/synctile-h3（★13，MIT，2026-10-06）
- **定位**：驱动 ComfyUI HTTP API 的脚本（非节点），**4090 实测**：fast 档 = 8 步 LoRA + 核心 INT8 attention，1344×768×141 帧 562 s → 114–117 s（4.9×）；4K 档 = LBH latent 放大到 3840×2160 → 共享噪声 σ0.878 → 9 个 1472×896 tile **每步同步**（每步后按重叠权重混合再进下一步）跑最后 3/8 步 → 整幅一次解码（±可选 5×5 unsharp 1.0）。
- **数据**：4 块独立完成 430 s 眼睛不一致，SyncTile 243–272 s 无缝；4K 路线 vs MMH3 Split Upscale vs SeedVR2 7B：542 / 605 / 2097 s，闪烁指标 1.62 / 1.68 / 3.00（SeedVR2 单帧最锐但播放「沸腾」）；精修最后 4 步而非 3 步多花 2–4 min 无增益；TeaCache 0.25 虽 2.9× 但构图漂移（SSIM 0.58）；SageAttention 2.2 在该机 0.5×（位级一致）。
- **限制**：只测 5 s；快速物体会相对底片移动几像素；24 GB 峰值 = 一块 tile。
- **评级**：试用（4K 交付；比 06 簇 Tessera/bbaudio 分块路线多了「每步同步」）。

### stuubszzz/Stubelius-Ultimate-H3（★39，NOASSERTION，2026-11-04）
- **定位**：四窗口单工作流（Setup/Director/Seeds/Output），模式 Speed/Hybrid/Quality/PDMD/FastH3 Omni/Pika Flex；每 chunk 1.6 s 音画续接；1–4 个 seed 并排听看再 Finish；RIFE 任意帧率、DLSS 5 / RTX VSR 到 4K。只借其 **5090 同 seed 对照**。
- **三家对照（Reference 模式，1344×768，3 seed）**：15 s 单段 Pika Flex 238–252 s / PDMD 167–172 s / FastH3 Omni 149–157 s；24 s 两段 428–437 / 289–297 / 319–324 s；第二段音色与参考匹配 **0.89–0.91 / 0.72–0.75 / 0.90–0.96**（PDMD 后续段走 FL2VA 模型不吃音色参考）；12 段 15 s 的定格帧 233（6 段）/ 91 / **1**；跑跳光流幅度 5.1 / 8.2 / 8.2；台词逐字 32/33、30/30。PDMD 脸略更像（0.74 vs 0.71）。FastH3 Omni 不开 VSA 时慢 1.8×；需 ComfyUI 0.42。
- **分段衔接四模式结论**：「Picture + sound」最顺；后段声音发闷时改「Picture, fresh sound」（续接声会丢人声与呼吸）；「Last frame only」在 PDMD 下把后段变暗变饱和的漂移减半但运动不顺；「New shot」= 硬切并在前 0.5 s 放中间帧，否则 H3 会提前跳到那张图再定格。无台词的续接段要显式告诉模型「没人说话」。
- **De-stutter**：Speed 档 15 s 段测得 95 个保持帧（每 3 帧一个），RIFE 提帧率只会把跳变切半；它用 RIFE 重绘被保持的那一帧（roughness 0.83→0.23）。Flow shift：LightX2V 768p turbo 训在 6/3，544p turbo、PDMD、FastH3 Omni、Pika 在 12/3。
- **评级**：不装（NOASSERTION、33 个 py、PySide 风格大包），数据与四条衔接规则写进 skill。

### NikoDemon80/ComfyUI-FastH3-Lora-Converter（★11，NOASSERTION，2026-08-30）+ Adudeguyman/ComfyUI-HyperFlow-H3（★17，Apache-2.0，2026-10-01）
- **FastH3 转换**：只取 `FastVideo-FastH3-4-step-Preview-v1-LoRA/dense-datafree/adapter_model.safetensors`（1.4 GB，`vsa-*` 三个为 VSA 后端专用，ComfyUI 不能用），脚本 `lora_convert_h3.py` 做 `transformer_blocks.N→blocks.N`、`to_q/k/v→qkv_proj` 融合、`ff.net→mlp.fc1/fc2`、`norm_out.linear→final_layer.adaln_proj.linear` 等映射；未转换文件加载**不报错只是无效**；建议 **6 步**。与 matsuo-koya 的转换器互为参照（后者指出 fc1 半区顺序与 qkv 块对角 lora_B 的坑，并有 `--compare` 位级校验）。
- **HyperFlow-H3**：Saganaki22/ComfyUI-Hyperflow（03 簇已评）**仓库已消失**，本包是 Apache 延续：`ApplyHyperFlowH3` 输出 9 点 SIGMAS 接采样器，Euler；权重从 drbaph/Hyperflow-Comfyui 下载（full 3.67 GiB / pruned 3.64 GiB，也有可用 stock `Load LoRA` 的独立 LoRA 版）；pruned 底模开 `experimental_curve_refit`（FL2VA 视频 cos 0.81→0.88、REF2VA 音频 0.93→0.99）；Sol-Attn 配方 = 核心 Model Sparse Attention `start_percent 0.16 / dense_blocks "0,1" / tau 1.0 / sink off`；bypass QKV 省 1092 MiB。
- **评级**：FastH3 LoRA 转换——试用（用户 int8_convrot 完整底模可用；6 步）；HyperFlow-H3——替换 03 簇中已失效的 Saganaki22 链接，评级不变（观望）。

### filliptm/ComfyUI-FL-MiniMaxH3（★22，Apache-2.0，2026-09-14）
- **新机制**：`LoRA Block Loader` 按 `blocks.0-9=0.5 / blocks.25=0 / refiner.0-1=0.8` 逐块覆盖 LoRA 强度（负值反向），作者提醒「块没有固定的运动/风格角色，削弱蒸馏 LoRA 的某些块会破坏少步行为」；`Temporal reshots` 在源视频时间线上移动/缩放一个帧精确区间并只重生成该段；`Shot Motion Context` 把上一段可配置尾巴作为隐藏条件、可见边界仍是硬切（02 簇「硬切为主」路线的工具化）；`VDN` 节点只装 Stage-DMD-250 分支 + Stage-B 适配器、**不带 turbo adapter**（4.3 GiB）。`Motion Refine` 依赖 MAINodes `H3TimeSmear.plan` 与本地流式 VAE 方法（`strength 0.50` = 25 步表尾 12 步）。
- **评级**：观望（严格时间线 + beat 规划对 MV 更有用；LoRA 分块调节可借来做 Turbo×风格 LoRA 的冲突排查）。

### fengyungithub/dsh-short-video-studio（★38，Apache-2.0，2026-11-07）
- **定位**：DeepSeek Harness 插件 + 本地 ComfyUI 的短剧画布（35 MB，Agent 编排、飞书远控），模型无关 manifest 注册表；只借其 2026-11 **同 prompt/seed 1344×768×124 帧单卡实测**。
- **加速**：Pika H3 Flex 6 步 ref2v 178.8→135.9 s、i2v 173.6→132.2 s（1.30×），叠核心块稀疏 84.4 s；PDD 8 步 ref2v 184.7 s（锐度 +10.3%），叠 Sol 137.3 s；**Sol-Attn（SolAttn-Ampere flex_attention）成片档 1.27×、balanced 1.23×，fast/480p 只有 1.03× 且高频 −13.8% ⇒ 低档不要开**；RIFE 4.25 48 fps 124 帧 10.5 s（逐镜补、成片不补）。
- **放大/重建**：RealESRGAN ×2 68.1 s → 2688×1536；SeedVR2 3B 2K 187.2 s；**RelayVSR ×2 25.3 s**（×4 83.4 s → 5376×3072，每 15 帧一次 Wan2.2 5B 参考分支）；Open-H3 Regenerate 2K 557 s；生成内 3D latent ×2 二遍 620–2700 s。结论：保内容选超分（默认像素、要快选 RelayVSR、要纹理选 SeedVR2），接受重画才选 regenerate；「超分按分镜做，不要对成片做」；2K 交付有效细节约 1.9K。
- **评级**：不装，数据采用。

### biyuhe3442-cmd/ComfyUI-NB-H3-HyperStep（★33，MIT，2026-08-04）与 Icyoung/ComfyUI-MiniMaxH3-TeaCache（★19，MIT，2026-08-04）
- **HyperStep**：中段残差复用——Fast 跳 block `[8,42)`、Turbo（默认）`[7,43)`、Extreme `[6,44)`，`full_refresh_interval 4`，有稳定性 guard 回退；不减步数；EasyCache 实验兼容、LazyCache 拒绝；检测到模型 hook 变化清缓存。beta，无质量数据。
- **TeaCache**：`set_model_unet_function_wrapper` 包整个 `apply_model`，按输入 rel-L1 累积阈值复用上一步输出（`rel_l1_thresh 0.15`，start 2 / end −2），**无多项式校准**（Phase 2 未做）；作者 CMP 170HX 20 步 306→102 s（3×）。synctile 在 4090 实测 TeaCache 0.25：195 s 但构图漂移 SSIM 0.58/0.75。
- **评级**：跳过（03 簇「一链只允许一个跳步/缓存节点」且首选 FirstBlockCache/Spectrum；这两个都没有画质护栏数据）。

### wjc573/ComfyUI-MiniMax-H3-Audio-Guide-Feather（★8，无 license，2026-09-04）
- **机制**：放在一个或多个官方 `MiniMaxH3AddGuide` 之后，找出所有带 `audio_latent` 的 keyframe，为每个音频 guide 末尾 `audio_feather_ticks`（默认 8 tick ≈ 0.2 s @40 Hz）生成逐 token 独立 timestep（半余弦释放），而非官方对整个 `cond_audio` 段统一 timestep。只改 CONDITIONING，不动目标 latent 的 noise_mask。要求 ComfyUI ≥0.34，首次执行装运行时 hook。
- **与已覆盖项目关系**：06 簇 ExactAudioLock 是「钉死」，这是钉死后的「软放开」，解决 TTS 对白段尾硬切。
- **评级**：试用（对白 guide 末尾有咔哒/硬断时）。

### simsim9-stack/ComfyUI-MiniMaxH3-PreviewOverride（★11，MIT，2026-08-05）
- **机制**：`OUTER_SAMPLE` wrapper 每步把当前 x0 视频 latent 用自训的 24 通道 **Tiny AutoEncoder 解码器 `taeh3_decoder.safetensors`**（~9.9M 参数、40 MB，放 `models/vae_approx/`）解成真 RGB，DOM 小部件内播放，附 σ/Δ 曲线、每步耗时与 ETA；全分辨率（`max_resolution` 封顶），不会加载全量 VAE。
- **价值**：抽卡时前 2–3 步就能看出构图/人数错误并中断，省掉整段采样；06 簇 RelayHires 用的 taeh3 同源思路。
- **评级**：采用（低成本）。

### BigStationW/ComfyUi-MiniMax-H3-Image-And-Reference-To-Video（★15，无 license，2026-09-02）与 entropicnoise/MiniMax-H3-Combined-Image-And-Reference-to-Video（★10，GPL-3.0，2026-09-08）
- **机制**：一个节点同时做首/尾帧关键帧 + Ref2VA 参考（entropicnoise 另支持 `middle_frame`、`length=1` 的 T2I/I2I/Ref2I）。需要 **FL2VA/Ref2VA 混合权重**（smhfacct/Minimax-H3-fl2va-ref2va-hybrid-models，作者用 b20-49；03 簇 scottmudge HybridLoader 也可现做）。
- **论点**：`AddGuide + ReferenceToVideo` 只让 DiT 看到帧 latent、Qwen 文本编码器从未见过该图，文本与 latent「拔河」导致偏色/翘曲/闪烁；本节点把首尾帧同时送进 Qwen 与 DiT。附对比视频，无数值。
- **评级**：观望（与 01 簇 Easy/seesee75 的「首尾帧 + 参考」做法比较后再定；用户已有 int8 双模型，可用 HybridLoader 试 b20-49）。

### ZenHG/ComfyUI-H3-Latent-Relay（★39，MIT，2026-10-26）
- **机制**：02 簇路线 A（上段 AV latent 尾部按真实位置钉进 `minimax_keyframes`，零重编码），`context_frames 22`（只认 5/22/…/124），「裁重叠一次裁两边」保证音画长度守恒；`/h3relay/health` 一行诊断。新点是 **`voice_anchor`**（`LoadAudio → VAEEncodeAudio` 的 latent）：`stage_index ≥1` 时恒占 1 个音频参考名额，把尾窗 0.925 s 的音频替换成指定说话人（锚 ≥0.9 s，建议 1–4 s，尾部不能静音，有垫乐要混进去），解决跨段换说话人时「翻唱成上一人音色」；缝区只锚第一个说话人，之后靠 `<Subject N>`；不接声锚则逐位等于旧版。
- **坑**：追加的那个音频参考**没有文本标签**（DiT 侧追加，tokenize 已过），提示词引用不到它；不要把 `context_latent` 接到 `voice_anchor`。
- **评级**：观望（MC 0.7 仍是首选；跨段换说话人场景可试 voice_anchor）。

### L-Trunks/ai-film-skills（★30，NOASSERTION，2026-09-15）
- **定位**：4070 Ti 12 GB 上六个 Claude skill 的「决策型」知识库（1600 行踩坑），`docs/gallery.md` 的实拍结论比代码值钱。
- **推翻自己的两条**：① 「提示词太长→削短」在剧情片上错：1300→250 字指令 0/4→4/4 但背景层次崩、模型往空处填东西；真变量是「指令句 vs 描述句权重」，解法是加长到 811–869 token 并用夹句（核心指令首尾各一遍）+ 画幅裁切写法；判据「这张图的背景要不要看？要→别削」。② `BGM 通铺` 实测覆盖 94% 等于没响，改判据：**对白交锋段一律不给音乐**（降到 19–34%）。
- **判停清单（做不到→换写法而非重抽）**：机械开合→关/开空镜硬切；群体反应→单人 + 画外声；走位→直接画「已到位」（位移不行，原地起立/转身可以）；画内文字→只留大号阿拉伯数字；多人互动→拆单人用视线缝；手部纹理→姿势级特征。⛔ 砍掉的画面必须留在音轨里。
- **其它**：0.31 MP 上中景脸 40–90 px ⇒ 76% 角色镜被迫特写、一段 30 s 可零远景（信息用台词补）；自动审片器上岗前先拿 59 张历史合格帧跑误杀回归（查出 3 类假阳性、4 处真缺陷）；原创角色每人锚三样：发型形状 + 高饱和虹膜 + 不可能漂的硬记号；「治不过的先验就顺着它写」。
- **评级**：规则采用（NOASSERTION，只引用）。

### 1113800942/comfy-h3md-director（★16，AGPL-3.0，2026-11-06）
- **定位**：2–3 分钟 1080p 一次跑完的多镜导演台（自动按显存切段、磁盘缓存续跑、`rerun_segments` 只重渲坏段并两端锁邻段、运动复制 = 深度 + SAM3 + Fun ControlNet、4B + ClipProj 编码器省 10 GB）。
- **漂移处理**：长单镜颜色漂移「生在低清阶段」（饱和度 0.32→0.46、锐度递增）；`lowres_anchor=1` 锚住低清通道；v0.2.0 `drift_correct=auto` 在保存节点只对「清晰稳定趋势」的饱和/锐度做校正、场景明暗切换自动重置参考、1–2 段的短程不动、所有决定写 `<video>_drift.json`；`tools/drift_correct.py` 可处理任何成片。
- **评级**：观望（AGPL、35 MB；漂移校正脚本思路可借到 02 簇规则 27）。

### Speach1sdef178/MiniMax-H3-Semantic-Bridge（★26，NOASSERTION，2026-09-09）
- **机制**：~11 MB 适配器（SenseNova U1.5 作教师蒸馏）把 H3 条件变换后以 `alpha 0.10`（A/B 示例 0.15）、`magnitude_match per_token` 混回条件，不改 DiT 权重；只支持 FL2VA/T2V/首尾帧，**明确不支持 Ref2VA，口播/唱歌会变差**。supElement AutoContext 与 flywhale upgrade-kit 都内置了它（含 BUNNY V2 变体）。docs/10 曾提到 AIMixer 的 `semantic_bridge` 入口即此物。
- **评级**：观望（短剧主干是 Ref2VA，几乎用不上）。

### slmonker/ComfyUI-TaoMateHD（★19，NOASSERTION，2026-11-07）与 ANe5s/ComfyUI-Sol-Sampler（★10，Apache-2.0，2026-11-07）
- **TaoMateHD**：三阶段渐进采样（低清 σ1→state16、低清 16→33、耦合提升到高清、高清 33→0；默认 3 步 = 2 低清 + 1 高清），需转换版 `TaoMate-HD-preview-comfy.safetensors`（2.48 GB fp32），支持 AV noise mask（数字人口播锁音频）、32 px 对齐；Ref2VA 为实验。示例 1920×1088 5.17 s 数字人。
- **Sol-Sampler**：一个 SAMPLER：前 `lowres_steps 6` 步在 0.5× 分辨率跑（Sol-Attn 的 dense 预热在小 latent 上完成），`Minimax H3 3D` 放大后继续；关键是**噪声耦合**——低清噪声由同一高清噪声派生（2D 正交 Haar LL 或 bilinear），作者观察非耦合噪声会出明显异常、bilinear 无方差补偿反而最稳。
- **评级**：观望（与 docs/10 SelfLift、06 簇 ResCascade 同属渐进路线；Sol-Sampler 的「噪声耦合」是渐进二采的共性要点）。

### TwoAbove/ComfyUI-H3VideoOutpaint（★21，MIT，2026-09-08）
- **机制**：无提示词滑窗外绘：每个时间窗把源视频作为硬保留 target latent + 空间 guide，向 9:12 竖版扩边；需核心 PR #16184（可定位 FL2VA 关键帧）；`temporal_window_frames auto`（≤107 帧）、`source_pixels exact`（原像素回贴 + 16 px 渐变 + 逐帧色匹配）；推荐 `generation_megapixels 1.0 / minimum_source 0.7 / max_upscale 1.5 / 20 步 res_multistep simple`，**不要用随机采样器（er_sde/euler_ancestral 会把噪声留给下一窗）**。
- **评级**：观望（用户做 16:9，仅在需要把竖版素材改横版时反向使用）。

### klfzqxs/ref2va-h3-video-optimizer（★36，MIT，2026-10-27）
- **机制**：Web 控制台，把提示词当唯一变量：LLM 写剧本 → ComfyUI 渲染 → ffmpeg 抽帧（均匀覆盖且**强制含末帧**，修正了 `t=dur/n*i` 永远采不到最后 1/n 的 bug）→ 多模态 LLM 评分 → 爬山式只采纳更好者；v2.0 对 >15 s 注入「运动铺满、新内容均摊每拍、光色连续演变、声音连续」规则，声称 60 s 单次可用（未给数据）；`core/video_metrics.py` 纯标准库算尾部运动/复读相关/音频电平（复读指标基线高只作辅助）。
- **与已覆盖项目关系**：05 簇结论 10 说「没人在本地 ComfyUI 跑通抽卡→VLM 评分择优」——这里跑通的是「提示词迭代」而非「同提示词多 seed 择优」，但评分器与抽帧脚本可直接借。
- **评级**：试用（借抽帧 + 评分回路）。

### supElement/ComfyUI_MinimaxH3_AutoContext（★39，Apache-2.0，2026-11-06）
- **定位**：22.5k 行一体化长视频包：分段推理 + 段间锚定 + 提示词时间轴切片（`Clip_Tag`/`timeline`/`sequential`/`global`）+ 二采 + 接缝修正 + 面部修复（`Face_Cut` YOLO + 可选 SeC-4B 追踪 → `Face_Resample` 块级 img2img → `Face_Blend`）+ 语义桥 + latent 磁盘缓存（32 GB 上限、按节点 ID 目录、v0.9.1 起能识别 LoRA/加速节点变化）。
- **新机制 TST（`h3_tst_patch.py`）**：对每个 head 计算帧级传输算子的「谱张力」（行熵 − 特征值熵），用 `gamma = exp(T·tau·层权重·步权重)` 做自适应 query 温度，`tau 0.2`（建议 0.2–0.3，深层更强、早期步更强）抑制时序闪烁与小脸崩坏；必须放在其它赋值型 attention override 的下游，与 Kijai Sage 补丁链式共存，官方 ModelAttentionBackend 不冲突。BSAI Film-Factory 的「selflift TST」与此同源。
- **默认**：960×544、`chunk_frames 90`、`context_frames 22`、`lock_audio true`、`video_context_denoise 0`（二采接 SplitSigmas 时建议 1）。
- **坑**：`h3_patches.py` 仍替换 `PackedLayout.__init__` 与 `MiniMaxH3.extra_conds`（检测到新版签名无 `frame_count` 时跳过）——落入 01/02 簇互斥名单；仓库内捆绑 sec_engine（phi3/internlm2/sam2 代码）体量大。
- **评级**：观望（TST 单独值得抽出来 A/B；整包不装）。

---

## 二、其余仓库一览（180 个）

| ★ | 仓库 | 推送 | 一句话定位 | 归类 |
|---:|---|---|---|---|
| 39 | [JYE-HC/Director-WebUI](https://github.com/JYE-HC/Director-WebUI) | 2026-08-25 | 导演台 WebUI（DirectorDeck 前身），React 时间线 + 原生节点模板，多卡 RayLight；与 01 簇导演台重合 | 重复造轮子 |
| 39 | [Icbears/minimax-h3-v100-patch](https://github.com/Icbears/minimax-h3-v100-patch) | 2026-09-06 | V100 FP16 混合精度 patch（替换核心 model.py 路径） | 硬件不对口 |
| 39 | [mamad8c/ComfyUI-H3-Latent-Upscaler-Mamad8](https://github.com/mamad8c/ComfyUI-H3-Latent-Upscaler-Mamad8) | 2026-08-09 | clean-latent 2× 学习型放大器（Tr1dae 依赖的那个包），06 已评 | 重复造轮子 |
| 38 | [dseditor/minimax-h3-colab](https://github.com/dseditor/minimax-h3-colab) | 2026-11-05 | Colab L4 笔记本（05 已评 dseditor skill） | 过时/不对口 |
| 38 | [shuaixn/ComfyUI-MiniMaxH3DualClockSampler](https://github.com/shuaixn/ComfyUI-MiniMaxH3DualClockSampler) | 2026-08-07 | 双时钟 Euler 修 4 步爆音；ComfyUI bdcb886 起核心原生已修，自动转交官方 euler | 过时 |
| 37 | [buqi-code/buqi-minimax-h3-multigpu](https://github.com/buqi-code/buqi-minimax-h3-multigpu) | 2026-09-28 | 2–8 卡 Ulysses 序列并行，Linux/WSL2，world_size 须整除 56 头 | 硬件不对口 |
| 37 | [AI-KSK/aiksk-minimax-h3-local-prompt](https://github.com/AI-KSK/aiksk-minimax-h3-local-prompt) | 2026-10-14 | 全域提示词 Skill v1.8.1（AIMixer 导演台规则 + 武打编排）；与 04/05 共识重合 | 重复造轮子（skill） |
| 36 | [NyckM/H3-Relight-Minimax-ComfyUI](https://github.com/NyckM/H3-Relight-Minimax-ComfyUI) | 2026-09-13 | 三灯位布光参考图 + 提示词编译器（给 H3 Edit 用），非真正光照适配器 | 重复造轮子 |
| 36 | [shootthesound/ComfyUI-H3Studio](https://github.com/shootthesound/ComfyUI-H3Studio) | 2026-08-20 | 单节点时间线编辑器（docs/10、12 已写） | 重复造轮子 |
| 36 | [GStaaaaa/GS-prompt-extend](https://github.com/GStaaaaa/GS-prompt-extend) | 2026-09-07 | llama-cpp-python 0.3.40 锁版 GGUF 提示词工作台（Qwen3.5/Gemma4 mmproj） | 重复造轮子 |
| 36 | [Work-Fisher/fisher-storylens](https://github.com/Work-Fisher/fisher-storylens) | 2026-10-15 | Z-Image→Qwen-Image 2.1→H3 短剧 Skill，15 s/段 3–4 镜；工作流在夸克网盘/RunningHub | 重复造轮子（skill） |
| 35 | [AntaresAlice/h3-webui](https://github.com/AntaresAlice/h3-webui) | 2026-09-11 | aiohttp 自托管 WebUI，尾帧续写、音频用途标注（音色/原声/音乐 → 提示词加 `[audio reuse]`） | 重复造轮子（UI） |
| 34 | [JayceHuang/jayce-recast-video-dgx](https://github.com/JayceHuang/jayce-recast-video-dgx) | 2026-10-26 | 双 DGX Spark 人物替换 Codex skill，物料在夸克网盘 | 硬件不对口 |
| 34 | [drowzeys/keys-SM121-Optimized-MiniMax-H3-Nvidia-Sol-Engine-Kijai-SolAttn_Triton-Single-DGX-Spark](https://github.com/drowzeys/keys-SM121-Optimized-MiniMax-H3-Nvidia-Sol-Engine-Kijai-SolAttn_Triton-Single-DGX-Spark) | 2026-08-17 | DGX Spark sm_121 专用 Sol-Engine 移植（flex_attention 在 sm_121 静默算错） | 硬件不对口 |
| 33 | [kat3ri/ComfyUI-MiniMax-H3-Extend](https://github.com/kat3ri/ComfyUI-MiniMax-H3-Extend) | 2026-09-24 | Backported Extend（01 规则 24 已列为互斥包）；≥0.34 不再 patch | 过时 |
| 33 | [aaalll12322/ComfyUI-MiniMaxH3-SolAttn-V100](https://github.com/aaalll12322/ComfyUI-MiniMaxH3-SolAttn-V100) | 2026-08-29 | V100 Sol-Attn/SLA 节点，2026-09-01 起停止维护 | 硬件不对口/过时 |
| 33 | [charlie12345/R9700AIProComfyUIPatch](https://github.com/charlie12345/R9700AIProComfyUIPatch) | 2026-08-08 | AMD R9700 RDNA4 改核心 model.py 的补丁，ComfyUI 更新即失效 | 硬件不对口 |
| 33 | [bingling360/ComfyUI-minimaxH3-SequenceForge](https://github.com/bingling360/ComfyUI-minimaxH3-SequenceForge) | 2026-11-02 | 导演控制台：尾 latent 钉头续接 + LBH 二采 + Seam Doctor；无 license，24 MB | 重复造轮子 |
| 33 | [goodguy1963/ComfyUI-ThinkingLLM](https://github.com/goodguy1963/ComfyUI-ThinkingLLM) | 2026-11-06 | Qwen/Gemma4/Whisper 多模态 LLM 节点（GPL fork 链），含 H3 系统提示词 | 重复造轮子 |
| 32 | [underworldhistory1-ctrl/minimax-h3-interface](https://github.com/underworldhistory1-ctrl/minimax-h3-interface) | 2026-11-06 | H3 + Qwen Image 2.1 浏览器工作室 2.15（launcher 安装到 custom_nodes 外） | 重复造轮子（UI） |
| 32 | [Newaiguy/ComfyUI-h3_sage_amd](https://github.com/Newaiguy/ComfyUI-h3_sage_amd) | 2026-08-16 | AMD gfx12 head-chunking Sage（作者自述不是提速器，是 16 GB 保险丝） | 硬件不对口 |
| 31 | [rwashy/H3-V100](https://github.com/rwashy/H3-V100) | 2026-09-29 | V100 优化节点 2.0.3（Flash/SOL、EasyCache、双卡） | 硬件不对口 |
| 31 | [Speach1sdef178/ComfyUI-VDN-H3-24GB](https://github.com/Speach1sdef178/ComfyUI-VDN-H3-24GB) | 2026-09-10 | VDN-H3 的 24 GB/3090 适配版 1.1.0（AutoMemory/AutoLongCache）；VDN 本身 03 已评观望 | 重复造轮子 |
| 31 | [xm6018924/BSAI-MiniMAX-H3-Prompt](https://github.com/xm6018924/BSAI-MiniMAX-H3-Prompt) | 2026-11-04 | GGUF/API 提示词优化 + 8 PV 模板 + 15 VFX 模板，76 MB 仓库 | 重复造轮子 |
| 31 | [tlano-z/ComfyUI-MiniMax-H3-Workflows-For3060](https://github.com/tlano-z/ComfyUI-MiniMax-H3-Workflows-For3060) | 2026-08-27 | RTX 3060 12 GB 工作流集（T2V/I2V/R2V/R2I、PDD、TAE 预览） | 单工作流 JSON |
| 31 | [wwjjqq888888-pixel/nanfeng-h3-comfyui](https://github.com/wwjjqq888888-pixel/nanfeng-h3-comfyui) | 2026-09-01 | 南风 H3 V10 单节点工作台（分镜/音频驱动/连续二采/NativeAudioLock），中文 UI，无 license | 重复造轮子 |
| 30 | [ANe5s/ComfyUI-MiniMax-H3-Hybrid](https://github.com/ANe5s/ComfyUI-MiniMax-H3-Hybrid) | 2026-09-25 | FL2VA 底 + Ref2VA AdaLN 覆盖加载器（默认 block 45–49；scottmudge 用 25–49）；03 已评 HybridLoader | 重复造轮子 |
| 30 | [muse-collective-26/Muse-CharacterSheet-H3](https://github.com/muse-collective-26/Muse-CharacterSheet-H3) | 2026-10-19 | Omni 模式角色三视图 + Qwen 精修 + DLSS，Windows bat 安装；06 Contact-Sheet 已覆盖 | 重复造轮子 |
| 30 | [aroslanov/ComfyUI-VideoAnalyzer](https://github.com/aroslanov/ComfyUI-VideoAnalyzer) | 2026-09-27 | knishika62/video-analyzer 的 ComfyUI 移植：VLM 把视频反推成 H3 六段/三段提示词（内置 VLM 加载器） | 重复造轮子（04 gnipbao 已评反推） |
| 30 | [AlonAshken/ComfyUI-MiniMaxH3-FlowDirector](https://github.com/AlonAshken/ComfyUI-MiniMaxH3-FlowDirector) | 2026-08-18 | 尾帧→下一段首帧的 WYSIWYG 时间线，像素级交接 | 重复造轮子 |
| 29 | [luxu1999/ComfyUI-MiniMaxH3-ChainDirector](https://github.com/luxu1999/ComfyUI-MiniMaxH3-ChainDirector) | 2026-08-31 | 单节点：首段 r2v + 后续 i2v 首帧硬锁接力，8 GB 可跑 | 重复造轮子 |
| 29 | [EvolvingLMMs-Lab/MacOS-H3-Speedrun](https://github.com/EvolvingLMMs-Lab/MacOS-H3-Speedrun) | 2026-08-21 | Apple Silicon 工作流（Turbo/FBC/Spectrum/SolAttn） | 硬件不对口 |
| 28 | [MajoorWaldi/ComfyUI-Majoor-H3-GuideMaster](https://github.com/MajoorWaldi/ComfyUI-Majoor-H3-GuideMaster) | 2026-08-28 | 时间线 UI 放置图/音频 guide（AddGuide 的可视化壳） | 重复造轮子（UI） |
| 27 | [SonderSaid/ComfyUI-Sonder-Editor](https://github.com/SonderSaid/ComfyUI-Sonder-Editor) | 2026-11-06 | 模型无关的时间线编辑器（LTX/Wan/H3），takes 对比 | 重复造轮子（UI） |
| 26 | [siyuan-liu31/minimax-h3-video-studio](https://github.com/siyuan-liu31/minimax-h3-video-studio) | 2026-10-24 | 自托管工作室 + h3ctl CLI + Agent，含变声/改词，37 MB | 重复造轮子（UI） |
| 26 | [star7code/minimax-h3-fp16-exact-star7](https://github.com/star7code/minimax-h3-fp16-exact-star7) | 2026-09-18 | Turing FP16 原生加载 + 溢出保护（SM80+ 自动回 BF16） | 硬件不对口 |
| 26 | [a756598009-cmyk/MiniMax-H3-AMD7900XTX-Win11](https://github.com/a756598009-cmyk/MiniMax-H3-AMD7900XTX-Win11) | 2026-10-22 | AMD 7900XTX Win11 部署教程（GGUF Loader） | 硬件不对口 |
| 25 | [Eanya-Tonic/2080ti-minimax-h3](https://github.com/Eanya-Tonic/2080ti-minimax-h3) | 2026-08-12 | 4×2080Ti Raylight FSDP/USP 多卡 + 多卡 Qwen CLIP 加载 | 硬件不对口 |
| 25 | [Yuishi1/ComfyUI-MiniMaxH3-lanxi](https://github.com/Yuishi1/ComfyUI-MiniMaxH3-lanxi) | 2026-11-02 | 1–8 段长视频操作台（独立命名空间，RefMod/LoRA），无 license | 重复造轮子 |
| 24 | [hyukudan/ComfyUI-MiniMax-H3-Prompt-Enhancer](https://github.com/hyukudan/ComfyUI-MiniMax-H3-Prompt-Enhancer) | 2026-08-29 | 规范约束提示词增强/校验（17 语言 + 88 方言、`<Audio N>`→`<Subject>` 绑定、隔离 llama-server 释放显存） | 重复造轮子（04 已有同类） |
| 24 | [colorAi/ComfyUI-Minimax-H3-Prompt-Engineer](https://github.com/colorAi/ComfyUI-Minimax-H3-Prompt-Engineer) | 2026-08-06 | AGPL 提示词编排 + 条件单节点，推 RunningHub 邀请码 | 重复造轮子 |
| 24 | [harlixay7/Kinoloom](https://github.com/harlixay7/Kinoloom) | 2026-10-29 | 8 GB 卡本地电影工作室（LTX-2.5 为主，H3 支持未展示） | 重复造轮子（UI） |
| 24 | [jiel71365-commits/ComfyUI-H3-Prompt-Builder](https://github.com/jiel71365-commits/ComfyUI-H3-Prompt-Builder) | 2026-08-26 | DeepSeek 改写 + 漫剧分镜六节点（剧本→分镜 JSON→逐镜 Ref2VA 提示词 + 接线说明） | 重复造轮子 |
| 23 | [erdinoral/minimax-h3-studio](https://github.com/erdinoral/minimax-h3-studio) | 2026-11-07 | Pinokio 一键 H3 Studio（Director/Continuum/Refine/Spectrum 开关） | 重复造轮子（UI） |
| 23 | [xmarre/MiniMax-H3-Flow-Aligned-Regenerate](https://github.com/xmarre/MiniMax-H3-Flow-Aligned-Regenerate) | 2026-10-21 | xmarre 伴侣包：低清轨迹引导高清/渐进交接，依赖 VDN-Plus/Continuum-Plus/Latent-Upscaler-Plus（03 已列为跳过 xmarre 系列） | 观望（研究向） |
| 23 | [AraneaQwQ/ComfyUI-H3-ClipStream](https://github.com/AraneaQwQ/ComfyUI-H3-ClipStream) | 2026-11-07 | PrefixStream 素材箱 + Motion-Context 续接拼装，Dual 卡同存一采/二采 latent | 重复造轮子 |
| 22 | [IvenKooLab/minimax-h3-turing](https://github.com/IvenKooLab/minimax-h3-turing) | 2026-10-30 | 2080Ti 22G 手册：W4A8 唯一可行、T8 BlockCache −43%、杀毒软件拖慢加载 27 min | 硬件不对口（结论可借） |
| 22 | [FlowForgeLabAi/MiniMax-H3-8GB-Workflows](https://github.com/FlowForgeLabAi/MiniMax-H3-8GB-Workflows) | 2026-10-24 | 8 GB 笔记本三档工作流（20/8/4 步），每次运行前重启 ComfyUI | 单工作流 JSON |
| 22 | [leonardofrito/Directors-Cut](https://github.com/leonardofrito/Directors-Cut) | 2026-11-03 | Windows 桌面资产 + REF2VA 工作室（Comfy SDK），rc 版 | 重复造轮子（UI） |
| 21 | [cicalooo/ComfyUI-MM-1Frame](https://github.com/cicalooo/ComfyUI-MM-1Frame) | 2026-09-10 | 原生 5 帧 T=2 静帧 + 可选 T=1 VAE；06 Fizgig-Still 已覆盖 | 重复造轮子 |
| 21 | [AtlasCloudAI/awesome-minimax-h3](https://github.com/AtlasCloudAI/awesome-minimax-h3) | 2026-11-05 | H3 awesome 列表（带星数/日期，SFW only） | 无内容（索引） |
| 21 | [lifeidle/comfyui-5090-laptop-24gb-minimax-h3-qwen-image-wan2.2](https://github.com/lifeidle/comfyui-5090-laptop-24gb-minimax-h3-qwen-image-wan2.2) | 2026-11-02 | 5090 笔记本 21 组实测：NVFP4 比 INT8 快 2.6×（Blackwell 专属，4090 无 NVFP4 硬件） | 硬件不对口（数据） |
| 21 | [Jalen-Brunson/ComfyUI-HybridWindows](https://github.com/Jalen-Brunson/ComfyUI-HybridWindows) | 2026-10-31 | 滚动扩散混合窗：39 帧重叠内钉 5 帧、6 顺序 + 2 联合步、原生 KSampler Advanced，V2V 需 6 个节点包 | 观望（实验） |
| 20 | [ThomasEricB/minimax-h3-pinokio](https://github.com/ThomasEricB/minimax-h3-pinokio) | 2026-09-05 | Pinokio 启动器；README 解释 pruned/int8 与 cu130 要求 | 重复造轮子 |
| 20 | [Deveraux-Parker/minimax-h3-voice-api](https://github.com/Deveraux-Parker/minimax-h3-voice-api) | 2026-08-09 | 把 H3 当 TTS/音乐服务（OpenAI/ElevenLabs 兼容 API，Parakeet 验证） | 外围工具（可借：H3 自产干音） |
| 20 | [Rea1Felix/H3-colab-studio](https://github.com/Rea1Felix/H3-colab-studio) | 2026-11-06 | Colab G4 Agent Bridge skill + stitch.sh | 过时/不对口 |
| 20 | [lumosai8/MinimaxStoryBuilder](https://github.com/lumosai8/MinimaxStoryBuilder) | 2026-08-29 | 故事→镜头→Krea2 角色表→H3 Ref2VA，每镜重发角色/场景参考（lumosai8 OrbitSheets 作者） | 重复造轮子 |
| 20 | [JYE-HC/DirectorDeck](https://github.com/JYE-HC/DirectorDeck) | 2026-08-24 | Director-WebUI 的 ComfyUI 插件形态（侧栏面板，Linux 多卡） | 重复造轮子 |
| 20 | [reventadirecta/MiniMax-H3-ComfyUI-8GB-VRAM](https://github.com/reventadirecta/MiniMax-H3-ComfyUI-8GB-VRAM) | 2026-09-06 | 4060 Laptop 8 GB FL2V 工作流（480×864/158 帧/20 步，Spectrum+ClipProj） | 单工作流 JSON |
| 20 | [Kiwi-shijie/ComfyUI_MiniMaxH3_Smart_Director](https://github.com/Kiwi-shijie/ComfyUI_MiniMaxH3_Smart_Director) | 2026-08-27 | 中文一体化智能导演：内部调用 AIMixer Director，自动 t2v/i2v/fl2v/r2v | 重复造轮子 |
| 20 | [digital-garbage/FunUI](https://github.com/digital-garbage/FunUI) | 2026-11-06 | 模型无关时间线工作室 v5（FramePack 起家），评分学习 | 重复造轮子（UI） |
| 19 | [nazgut/ComfyUI-MiniMaxH3-CLSS](https://github.com/nazgut/ComfyUI-MiniMaxH3-CLSS) | 2026-10-01 | 闭环流式合成：SLB 重叠重噪 + EMA AdaIN + 锚点库 + 音频尾 ref 到接点，16 GB；无 license | 观望（机制复杂） |
| 19 | [aaalll12322/ComfyUI-MiniMaxH3-FP16Safe](https://github.com/aaalll12322/ComfyUI-MiniMaxH3-FP16Safe) | 2026-08-22 | V100 fp16 NaN 安全节点 | 硬件不对口 |
| 19 | [AesSedai/ComfyUI-MiniMaxH3-Parallel](https://github.com/AesSedai/ComfyUI-MiniMaxH3-Parallel) | 2026-08-17 | 2–4 卡注意力头分片（RTX PRO 6000 ×4） | 硬件不对口 |
| 19 | [MANFRI-DEV/sprite-sheep](https://github.com/MANFRI-DEV/sprite-sheep) | 2026-09-27 | Godot + sidecar 做精灵表（H3/Wan） | 外围工具 |
| 19 | [ttulttul/ComfyUI-Minimax-H3-Continuation](https://github.com/ttulttul/ComfyUI-Minimax-H3-Continuation) | 2026-08-18 | 滚动重叠续接三节点（尾部作 frame-0 guide，隐藏重叠丢弃），需 e01fb4c+ | 重复造轮子（02 路线 A） |
| 19 | [formulake/KreativeSuite](https://github.com/formulake/KreativeSuite) | 2026-08-14 | LTX 2.5 放大器 + H3 视频精修单节点（Turbo 0.8 × 2 步起点） | 重复造轮子 |
| 19 | [newbmechanix-ship-it/ALPHA-T1](https://github.com/newbmechanix-ship-it/ALPHA-T1) | 2026-08-27 | 4060Ti 单程 I2V（euler+bong_tangent 12 步、Turbo 4 步 ×0.5、Sol tau 1.3）；结论「二采只加像素」与 06 相左 | 单工作流 JSON |
| 18 | [GeekatplayStudio/ComfyUI-MiniMax-H3-StoryBoard](https://github.com/GeekatplayStudio/ComfyUI-MiniMax-H3-StoryBoard) | 2026-08-07 | 面板→FL2VA 相邻两两成段，自动增长插口，落盘续跑 | 重复造轮子 |
| 18 | [Mitsuasa513/ComfyUI-MiniMax-H3-V100-Workflow](https://github.com/Mitsuasa513/ComfyUI-MiniMax-H3-V100-Workflow) | 2026-10-29 | V100 16/32G 工作流（T8 加速、--disable-cuda-malloc） | 硬件不对口 |
| 18 | [minimaxh3turbo/MiniMax-H3-Turbo-LoRA-ComfyUI](https://github.com/minimaxh3turbo/MiniMax-H3-Turbo-LoRA-ComfyUI) | 2026-08-28 | SEO 式仓库，自称 H3ModelLoader/SGLang，内容空泛 | 无内容 |
| 18 | [asirusasr-maker/ComfyUI-MiniMax-H3-Keyframe-Offset](https://github.com/asirusasr-maker/ComfyUI-MiniMax-H3-Keyframe-Offset) | 2026-08-26 | 任意帧钉关键帧（patch PackedLayout，核心已原生）+ AIO 音频生成器（Ref2VA 声线克隆出纯音频） | 过时（patch）/可借 TTS 思路 |
| 18 | [pwillia7/sorant](https://github.com/pwillia7/sorant) | 2026-11-07 | Vercel 前端连本机 ComfyUI（H3/Music3/SeedVR2/Kontext） | 重复造轮子（UI） |
| 18 | [MIKA6941/Comfy-H3-Director](https://github.com/MIKA6941/Comfy-H3-Director) | 2026-08-30 | Agent skill：资产分级、网文改分镜、媒体槽位挂载清单、FFmpeg 尾帧接力 | 重复造轮子（skill，05 同类） |
| 17 | [Comfy-Org/comfystreamerh3](https://github.com/Comfy-Org/comfystreamerh3) | 2026-10-06 | ComfyStream FastH3 实时流（448×256，云部署） | 不对口 |
| 17 | [JGRFW/comfyui-AICG3D-CSR](https://github.com/JGRFW/comfyui-AICG3D-CSR) | 2026-11-06 | AICG3D 独立换人/换景/换品节点，分段落盘、曝光锁、音轨独立封装 | 重复造轮子（05/01 AICG3D 已评） |
| 16 | [Kaihui-AMD/ComfyUI-MiniMaxH3-MultiGPU](https://github.com/Kaihui-AMD/ComfyUI-MiniMaxH3-MultiGPU) | 2026-09-08 | AMD ROCm 双卡序列并行 1.76× | 硬件不对口 |
| 16 | [luqidaxia/dgxspark_comfyui_minimax_h3](https://github.com/luqidaxia/dgxspark_comfyui_minimax_h3) | 2026-10-10 | DGX Spark 一键部署 + 基准（360p→RealESRGAN 2× 比直出 720p 快 6×） | 硬件不对口 |
| 16 | [fblissjr/ComfyUI-h3-explorations](https://github.com/fblissjr/ComfyUI-h3-explorations) | 2026-11-07 | 个人研究包（vendor sapiens2/moge2），LLM wiki | 无内容（个人） |
| 16 | [ethanfel/ComfyUI-H3-Qwen3VL-TextGen](https://github.com/ethanfel/ComfyUI-H3-Qwen3VL-TextGen) | 2026-08-17 | 把 H3 的 Qwen3-VL-32B 文本编码器接回 50–63 层尾巴当本地 LLM 用（04 ethanfel Guide 已评该思路） | 重复造轮子 |
| 16 | [wuli-art/MiniMax-H3-Turbo-ComfyUI](https://github.com/wuli-art/MiniMax-H3-Turbo-ComfyUI) | 2026-10-23 | Diffusers 0.40 加载 Wuli 4/6/8 步 Turbo 整模的独立节点（不走核心） | 重复造轮子/过时 |
| 16 | [pmhaidn/ComfyUI-Minimax-H3-Extender](https://github.com/pmhaidn/ComfyUI-Minimax-H3-Extender) | 2026-09-06 | 续接 + Farneback 光流 seam_smooth + seam_fade 色匹配（24 帧余弦回落）+ 同步裁切；GPL，31 MB | 重复造轮子（02 路线 A；seam_fade 思路可借） |
| 15 | [GaryLauLGY/MinimaxH3-Dual-Dgx-Spark](https://github.com/GaryLauLGY/MinimaxH3-Dual-Dgx-Spark) | 2026-10-01 | 双 DGX Spark RoCE 推理 2.24× | 硬件不对口 |
| 15 | [loopforge0/ComfyUI-H3-Continuous](https://github.com/loopforge0/ComfyUI-H3-Continuous) | 2026-10-03 | AddGuide 钉上一段末 1.6 s 的 Ref2VA 链 + 两端钉修复节点 | 重复造轮子（02 路线 A） |
| 15 | [einhorn13/mmh3_media](https://github.com/einhorn13/mmh3_media) | 2026-11-04 | .mmh3 媒体包（AV latent + 成片 + 参考 + 元数据）+ Generate/Continue/Edit/Refine 四节点 | 重复造轮子 |
| 15 | [teskor-hub/minimax-h3-skill](https://github.com/teskor-hub/minimax-h3-skill) | 2026-09-19 | Claude Code skill + Reel Maker（Ref+ControlNet+TS smoother / Ref Only 两模板） | 重复造轮子（skill） |
| 14 | [smthemex/ComfyUI_SolarWM_H3](https://github.com/smthemex/ComfyUI_SolarWM_H3) | 2026-09-04 | SolarWM 世界模型 LoRA（orbit_turns/radius 相机轨迹），等官方代码 | 观望（niche） |
| 14 | [xm6018924/BSAI-ComfyUI-H3-Film-Factory](https://github.com/xm6018924/BSAI-ComfyUI-H3-Film-Factory) | 2026-11-07 | 30 档渲染管线工厂（Sol-H3 Self-Lift 双采、selflift TST tau 0.2、一镜到底 seamless） | 重复造轮子 |
| 14 | [supElement/ComfyUI_Element_easy](https://github.com/supElement/ComfyUI_Element_easy) | 2026-11-07 | Multi REF 素材台、视频剪辑节点、Sigma 曲线手绘、H3 LatentUpscaler 包装 | 外围工具 |
| 14 | [ZenHG/ComfyUI-MOSS-Storyboard](https://github.com/ZenHG/ComfyUI-MOSS-Storyboard) | 2026-11-07 | MOSS-Image 九宫格故事板/局部编辑/换脸 + LLM 提示词（target=minimax-h3），ComfyUI ≥0.42 | 外围工具 |
| 14 | [zhenhanchen1-cyber/minimax-h3-nvidia-uncensored](https://github.com/zhenhanchen1-cyber/minimax-h3-nvidia-uncensored) | 2026-10-13 | 8 GB 起一键脚本 + 9 工作流（GGUF Q2_K） | 重复造轮子 |
| 14 | [topmass/topnodes](https://github.com/topmass/topnodes) | 2026-09-14 | 单/双角色替换 + SAM3 遮罩修复 + 全片音频定时（Singularity ref2va、Turbo 0.6） | 重复造轮子（06 换人已评） |
| 13 | [xiaolibai-sys/ComfyUI-MiniMaxH3](https://github.com/xiaolibai-sys/ComfyUI-MiniMaxH3) | 2026-08-16 | 自带 Qwen3-VL 编码器与流式加载/BlockSwap 的独立 H3 节点包（不走核心） | 重复造轮子/过时 |
| 13 | [linjian-ufo/comfyui-speed-minimaxH3](https://github.com/linjian-ufo/comfyui-speed-minimaxH3) | 2026-11-05 | 安全残差缓存 + 文本编码 CPU 缓存（2 组）+ 内置 Sage auto | 重复造轮子（缓存族） |
| 13 | [pixelaigc/ComfyUI-MiniMax-H3-Studio](https://github.com/pixelaigc/ComfyUI-MiniMax-H3-Studio) | 2026-11-07 | 新手 Web 工作台（Turbo 6 步/标准 20 步、PIKA Flex LCM 6 步、SAPI TTS、长片拼接） | 重复造轮子（UI） |
| 13 | [BiggerFishy/comfyui-minimax-h3-studio](https://github.com/BiggerFishy/comfyui-minimax-h3-studio) | 2026-10-07 | 视频 inpaint/换人工作流 ZIP（SAM3.1，--disable-fast-disk） | 单工作流 JSON |
| 13 | [martonsagi/Comfy-H3-MultiStream](https://github.com/martonsagi/Comfy-H3-MultiStream) | 2026-10-18 | 1–8 卡 DiT/VAE 拆分 + pinned RAM 权重常驻 + TE 缓存，位级一致 | 硬件不对口 |
| 13 | [Songssx/ComfyUI-OpenH3-Regenerate2K](https://github.com/Songssx/ComfyUI-OpenH3-Regenerate2K) | 2026-10-28 | Open-H3-Regenerate-2K 早期适配（312 LoRA 键映射、50 Sharp 曲线、锁音频）；06 rdh9616 已评 | 重复造轮子 |
| 13 | [grandju51/comfyui-llm-prompt-studio](https://github.com/grandju51/comfyui-llm-prompt-studio) | 2026-11-06 | LM Studio/vLLM 提示词卡片节点（H3 每任务一卡） | 重复造轮子 |
| 13 | [maosika-ai/ComfyUI-ReShot](https://github.com/maosika-ai/ComfyUI-ReShot) | 2026-09-13 | reshot 的 ComfyUI 节点版（深度/姿态/Canny 视频）；06 已评 pip 版 | 重复造轮子 |
| 13 | [japaneserunic/blubs-pixel-nodepack](https://github.com/japaneserunic/blubs-pixel-nodepack) | 2026-08-25 | H3 输出→像素精灵表（抠像、量化、Aseprite 桥） | 外围工具 |
| 13 | [Jolanoff/goated-prompter](https://github.com/Jolanoff/goated-prompter) | 2026-10-29 | React 本地提示词工作室（H3 模式、数据集生成） | 重复造轮子 |
| 12 | [PullMyBoots/ComfyUI-H3-FaceRefine-Accelerated](https://github.com/PullMyBoots/ComfyUI-H3-FaceRefine-Accelerated) | 2026-09-07 | FaceRefine 多脸 atlas 批处理（4 脸 768² 一图、4 s 作业 + 0.2 s latent 交接）：15 s 四脸 995→202 s（4.9×）；X-MinimaxH3 作者，MIT | 可借（06 FaceRefine 的加速分支） |
| 12 | [dg1kjd/comfyui-v100-sxm2-minimax-h3](https://github.com/dg1kjd/comfyui-v100-sxm2-minimax-h3) | 2026-08-14 | 8×V100 Ulysses 19→7 min | 硬件不对口 |
| 12 | [Dantesworks/MV_Maker](https://github.com/Dantesworks/MV_Maker) | 2026-10-29 | MV 工作流 + Clip Director（依赖 MultiRef 的 SongMaskedAVContext） | 单工作流 JSON |
| 12 | [sengseng123/aix-drama-factory](https://github.com/sengseng123/aix-drama-factory) | 2026-09-15 | 盖伦TA哥短剧工厂的 AGPL 延续（Flask 工作台、断点恢复） | 重复造轮子（05 同类） |
| 12 | [xm6018924/BSAI-ComfyUI-FaceRefine](https://github.com/xm6018924/BSAI-ComfyUI-FaceRefine) | 2026-10-29 | FaceRefine 单节点封装 + person 全身兜底 + 小脸 denoise 0.4（06 规则 7 已有） | 重复造轮子 |
| 12 | [skaiy/wild-h3c-comfyui](https://github.com/skaiy/wild-h3c-comfyui) | 2026-09-24 | antirez h3.c Metal 引擎桥接（Mac） | 硬件不对口 |
| 12 | [JerryZRic/comfyui-minimax-h3-latent](https://github.com/JerryZRic/comfyui-minimax-h3-latent) | 2026-10-21 | 保存/加载 NestedTensor AV latent 为 .h3latent（核心 Save Latent 会报 contiguous 错） | 小工具（06 规则 21 已提 .h3latent） |
| 12 | [patientx/comfyui-h3-sla-attention-rocm](https://github.com/patientx/comfyui-h3-sla-attention-rocm) | 2026-09-19 | PlagueKind SLA 节点的 ROCm 分支 | 硬件不对口 |
| 12 | [entert-ai/ComfyUI-H3-RefMods-Lab](https://github.com/entert-ai/ComfyUI-H3-RefMods-Lab) | 2026-10-14 | 把参考编码成可复用 .safetensors RefMod 包，可选源/强度/合并 100 个 | 重复造轮子（06 MiniMaxH3Mod 已评 RefMod） |
| 12 | [bbaudio-2025/Comfyui-MiniMax-H3-LatentSplit](https://github.com/bbaudio-2025/Comfyui-MiniMax-H3-LatentSplit) | 2026-09-19 | AV latent 按 17 帧网格切段重采 + 交叉淡入 + 边界帧锚（UltimateUpscale 作者）；06 已评该作者 | 重复造轮子 |
| 12 | [bt420000-collab/ComfyUI-H3-Neat-ImageFusion](https://github.com/bt420000-collab/ComfyUI-H3-Neat-ImageFusion) | 2026-10-20 | H3 静帧连拍多帧共识融合（曝光匹配+光流+伪影压制），配 Neat Prime LoRA | 外围工具（静帧向） |
| 12 | [GZT2023/ComfyUI-MiniMax-H3-Fun-Controlnet](https://github.com/GZT2023/ComfyUI-MiniMax-H3-Fun-Controlnet) | 2026-08-25 | Fun-Controlnet-Union 非官方节点，权重在 ModelScope（用户不可下）；06 FunControl 已评核心内置 | 过时/不可下 |
| 12 | [madersasuke/minimax-h3-video-skill](https://github.com/madersasuke/minimax-h3-video-skill) | 2026-08-12 | 风格参考 PV/MAD Codex skill（BGM 主导节奏） | 重复造轮子（skill） |
| 12 | [inikolax/remiqora-video](https://github.com/inikolax/remiqora-video) | 2026-11-04 | Windows 本地工作室（llama.cpp 写分镜，H3/LTX/WAN 单进程），GPL | 重复造轮子（UI） |
| 12 | [rookiestar28/ComfyUI-Sigmax](https://github.com/rookiestar28/ComfyUI-Sigmax) | 2026-10-27 | 模型感知 sigma 表（含 H3 Turbo 实验配方、拒绝不匹配 shift） | 外围工具 |
| 12 | [doubletwisted/ComfyUI-Spool](https://github.com/doubletwisted/ComfyUI-Spool) | 2026-11-07 | 模型无关时间线 + takes（本机/Comfy Cloud/Deadline），ComfyUI ≥0.39 | 重复造轮子（UI） |
| 11 | [Rinne414/ComfyUI-MiniMaxH3-Tools](https://github.com/Rinne414/ComfyUI-MiniMaxH3-Tools) | 2026-08-04 | DiffSynth NF4 加载器 + 画布规划/提示词 lint/音频 reroll/AV latent 工具 | 重复造轮子 |
| 11 | [red-polo/ComfyUI-MiniMaxH3FrameInfill](https://github.com/red-polo/ComfyUI-MiniMaxH3FrameInfill) | 2026-08-09 | 任意帧区间重生成（前后视频作锚，patch 核心，版本需锁定），实验 | 观望（实验，patch 核心） |
| 11 | [mamad8c/ComfyUI-MiniMaxH3-PDD-Mamad8](https://github.com/mamad8c/ComfyUI-MiniMaxH3-PDD-Mamad8) | 2026-08-07 | Ref2VA PDD 位移头加载/调度（需配套 head 工件）；03 PDD-Acc 已评 | 重复造轮子 |
| 11 | [malcolmamal/ComfyUI-MiniMaxH3RefLoRA](https://github.com/malcolmamal/ComfyUI-MiniMaxH3RefLoRA) | 2026-09-24 | LoRA + RefMod 打包成一个 .safetensors（RefLoRA），标准加载器照常读 LoRA | 小工具 |
| 11 | [sandpies/ComfyUI-Hand-Tie-Clips](https://github.com/sandpies/ComfyUI-Hand-Tie-Clips) | 2026-11-02 | 单节点多 hop 续接工作室（shot cards、参考轨、solo 重拍） | 重复造轮子 |
| 11 | [Fish4AI/comfyui-SelfLift-Fish](https://github.com/Fish4AI/comfyui-SelfLift-Fish) | 2026-11-04 | facok SelfLift 改良：16 GB 跑 20 s 1376×768 / 15 s 1920×1088（5070Ti 14 min） | 重复造轮子（SelfLift 系） |
| 11 | [tazmannner/ComfyUI-H3-AnimeCadence](https://github.com/tazmannner/ComfyUI-H3-AnimeCadence) | 2026-10-18 | 动画 2s/3s 重定时节点（06 RelayHires 条目已提） | 已覆盖 |
| 11 | [madeye/comfyui-minimax-h3-dgx-spark](https://github.com/madeye/comfyui-minimax-h3-dgx-spark) | 2026-09-04 | DGX Spark int8 pruned 配置 + fp8 vs int8 基准 | 硬件不对口 |
| 11 | [tazmannner/ComfyUI-H3-FastDerope](https://github.com/tazmannner/ComfyUI-H3-FastDerope) | 2026-11-03 | MAINodes de-rope 的运动门控廉价版（+12 s 而非 +202 s）（06 已提） | 已覆盖 |
| 11 | [barelymining/ComfyUI-MiniMax-H3-FastVideo](https://github.com/barelymining/ComfyUI-MiniMax-H3-FastVideo) | 2026-09-06 | FastVideo VSA 路由（3090Ti：4 步 topk 0.1 49 s 草稿）；03 Kablex VSA 已评 | 重复造轮子 |
| 11 | [BMB12d3/ComfyUI-H3-Ref2VA-Accelerator](https://github.com/BMB12d3/ComfyUI-H3-Ref2VA-Accelerator) | 2026-08-13 | Ref2VA 专用块缓存（block0 每步跑、1–49 残差复用，CPU 缓存）；03 缓存族已评 | 重复造轮子 |
| 11 | [PMZFX/minimax-h3-intel-xpu](https://github.com/PMZFX/minimax-h3-intel-xpu) | 2026-08-13 | Intel Arc Pro B70 移植（464 s/5 s 8 步） | 硬件不对口 |
| 11 | [xm6018924/BSAI-H3-upscale-4K](https://github.com/xm6018924/BSAI-H3-upscale-4K) | 2026-11-06 | 像素/潜空间双通道 4K 放大路由（RealESRGAN/FlashVSR/SeedVR2/RTX VSR/DLSS5/VOSR/Topaz） | 外围工具 |
| 11 | [muse-collective-26/Muse-MiniMax-H3-Unified-Loader](https://github.com/muse-collective-26/Muse-MiniMax-H3-Unified-Loader) | 2026-10-31 | 按显存自选模型栈的统一加载器（依赖 Multishot + KJNodes；A/B 后移除 Sol-Attn 选项） | 重复造轮子 |
| 11 | [vita-epfl/PTD-inference](https://github.com/vita-epfl/PTD-inference) | 2026-10-28 | PTD 官方推理 + ComfyUI 节点（4/6 步 SDE 配方，EPFL 权重）；03 已列待评 | 观望（另一条蒸馏线） |
| 11 | [wassermanproductions/wasserman-80s-horror-lora](https://github.com/wassermanproductions/wasserman-80s-horror-lora) | 2026-10-09 | 80 年代恐怖片风格 LoRA（`80s_horror_wk` + `shot on VHS./16mm film.`），Apache 代码 | 风格 LoRA（题材不对口） |
| 11 | [ljxdn/ComfyUI-DNNodes](https://github.com/ljxdn/ComfyUI-DNNodes) | 2026-10-29 | 资产卡（图+音+描述）打包成 AIMixer `MMX_DIR_GROUP`/拆回官流 + SelfLift 一采缓存路由 | 外围工具（配 AIMixer） |
| 11 | [wandermyz/vhotseat](https://github.com/wandermyz/vhotseat) | 2026-10-21 | 本地 LLM 与 ComfyUI 轮流占 GPU（Linux，Strata/pi） | 外围工具（04 已有卸载规则） |
| 10 | [civilcoco/ComfyUI-MiniMaxH3-Myang](https://github.com/civilcoco/ComfyUI-MiniMaxH3-Myang) | 2026-09-20 | MC 衍生的长视频导演台（GPL），LLM 分镜/媒体 Agent/RTX VSR 二采 | 重复造轮子 |
| 10 | [Yamoon-jjang/comfyui-Ultra-MiniMax-H3-Prompt](https://github.com/Yamoon-jjang/comfyui-Ultra-MiniMax-H3-Prompt) | 2026-11-06 | 韩文菜单式提示词节点 v3.59（人物/机位/台词/环境音） | 重复造轮子 |
| 10 | [shiqikuangsan31/MiniMax-H3-12GB-ComfyUI-Guide](https://github.com/shiqikuangsan31/MiniMax-H3-12GB-ComfyUI-Guide) | 2026-08-11 | 12 GB 部署指南（多数加速在 offload 下无效；Turbo 4 步 + EasyCache 420 s/5 s） | 过时（8 月，ModelScope 下载） |
| 10 | [onigirikiller/minimax-h3-webui](https://github.com/onigirikiller/minimax-h3-webui) | 2026-08-04 | 小型 WebUI + 队列 + 尾帧接力；README 详述社区许可地域限制（含美英欧韩） | 重复造轮子（UI） |
| 10 | [xm6018924/BSAI-ComfyUI-Sol-H3](https://github.com/xm6018924/BSAI-ComfyUI-Sol-H3) | 2026-11-05 | 一键加载器：Sol-Attn + FastH3 4 步 + Fused Modulation + Self-Lift 二采（32px 对齐、CONST 重噪） | 重复造轮子 |
| 10 | [YourAiBuddyJie/minimax-h3-director-suite](https://github.com/YourAiBuddyJie/minimax-h3-director-suite) | 2026-09-05 | Codex 双 skill（导演 + 本地 runner：预检/低清测试/抽帧质检/选择性重试） | 重复造轮子（skill，05 TFboy1 同源） |
| 10 | [cyberworm1/refmodBuilder](https://github.com/cyberworm1/refmodBuilder) | 2026-10-08 | Linux Qt 桌面 RefMod 打包器（依赖 MiniMaxH3Mod） | 外围工具/不对口 |
| 10 | [SekiyoKana/minimax-studio-webui](https://github.com/SekiyoKana/minimax-studio-webui) | 2026-10-23 | FP8 视频服务 + API + Android 客户端（RunningHub 节点），108 MB | 重复造轮子（UI） |
| 10 | [winchao110/auto-drama-video](https://github.com/winchao110/auto-drama-video) | 2026-10-25 | 小说→H3 分段提示词→Moss/Qwen 资产图→H3 视频，纯标准库直连 ComfyUI HTTP | 重复造轮子（05 同类） |
| 10 | [The5toryofthe5ecret5tar5ystem/5tar5ystem-MMH3-Character-Sheet-Builder](https://github.com/The5toryofthe5ecret5tar5ystem/5tar5ystem-MMH3-Character-Sheet-Builder) | 2026-10-14 | 角色表构建器：参考角色（脸/身/声）、15 视图矩阵、格间 latent 续接、合成单图回喂 ref2va | 重复造轮子（06 三视图已评） |
| 10 | [YiIimini/NiliX](https://github.com/YiIimini/NiliX) | 2026-09-08 | Go 单服务漫剧工作台，已停更转 ManJuX | 过时 |
| 9 | [Speach1sdef178/ComfyUI-VELA-H3](https://github.com/Speach1sdef178/ComfyUI-VELA-H3) | 2026-10-08 | VDN-H3 的分层注意力后端策略（block 40–49 exact SDPA）；≤9 s 快 4–23%，10 s 反慢 | 观望（依赖 VDN） |
| 9 | [YanzuoLu/ComfyUI-MiniMax-H3-RAVEN-Streaming](https://github.com/YanzuoLu/ComfyUI-MiniMax-H3-RAVEN-Streaming) | 2026-08-20 | 流式 T2VA（chunk-major 采样 + 强制 RAVEN LoRA） | 观望（niche） |
| 9 | [flywhale-666/ComfyUI-H3-upgrade-kit](https://github.com/flywhale-666/ComfyUI-H3-upgrade-kit) | 2026-10-14 | MC + LBH + SelfLift 整合包（22 帧上下文、音频分段循环、BUNNY 语义桥） | 重复造轮子 |
| 9 | [cicalooo/ComfyUI-SolAttn-Ampere](https://github.com/cicalooo/ComfyUI-SolAttn-Ampere) | 2026-08-06 | flex_attention 版 Sol-Attn（3090 sm_80+） | 重复造轮子（核心已含 Sol） |
| 9 | [quzopl/ComfyUI-SolAttn-H3](https://github.com/quzopl/ComfyUI-SolAttn-H3) | 2026-09-10 | CuTe DSL Sol-Attn 节点：4070Ti 对 Sage 1.31–1.65×，dense 回退有理由；核心已含 Sol | 重复造轮子（数据可参考） |
| 9 | [alisson-anjos/ComfyUI-Molmo2-H3](https://github.com/alisson-anjos/ComfyUI-Molmo2-H3) | 2026-11-04 | Molmo2-8B 当 H3 编码器（投影器实验）+ 点追踪→SAM3.1 | 观望（实验） |
| 9 | [KursatAs/ComfyUI-H3-Multishot-Advance](https://github.com/KursatAs/ComfyUI-H3-Multishot-Advance) | 2026-08-31 | Multishot 的精简分支（shot_cache 项目层）；02 Multishot 已评 | fork 镜像 |
| 9 | [Argus-AiTeam/ComfyUI-MiniMax-H3-MLX](https://github.com/Argus-AiTeam/ComfyUI-MiniMax-H3-MLX) | 2026-08-12 | Apple MLX 节点 | 硬件不对口 |
| 9 | [Shenrui-Ma/video-regen-recipes](https://github.com/Shenrui-Ma/video-regen-recipes) | 2026-09-18 | 20 个 MEME/鬼畜二创模板 + Agent skill，115 MB | 重复造轮子（skill） |
| 9 | [jayleaton/minimax-h3-tensorfold-rtx](https://github.com/jayleaton/minimax-h3-tensorfold-rtx) | 2026-10-30 | TensorFold NVFP4 W4A4 加载器（RTX 50 专属：5070Ti 2.3×/Turbo+Sol 96 s） | 硬件不对口 |
| 9 | [Xplore-LAB/minimax-h3-dgx-spark](https://github.com/Xplore-LAB/minimax-h3-dgx-spark) | 2026-10-22 | DGX Spark 容器化部署 | 硬件不对口 |
| 9 | [Promptlab37/PocketComfy](https://github.com/Promptlab37/PocketComfy) | 2026-10-03 | Android 遥控 ComfyUI（已转闭源） | 外围工具 |
| 9 | [hany-liu/comfy-director](https://github.com/hany-liu/comfy-director) | 2026-09-02 | Node 本地长视频导演台（4070 12 GB：992×1792 上限、frame_idx=0 锚、第 119 帧续写） | 重复造轮子 |
| 9 | [pxl-pshr/LoopStudio](https://github.com/pxl-pshr/LoopStudio) | 2026-11-05 | 无缝循环 GIF 本地 app（Pika Flex + VBVR LoRA 叠加，4090 ~15 min/渲染）；02 已评 pxl-pshr Loop | 外围工具 |
| 9 | [xianjing2000/comic-drama-forge](https://github.com/xianjing2000/comic-drama-forge) | 2026-10-19 | 云 LLM 剧本→Qwen 三阶段资产→H3→FlashVSR 4×→FFmpeg，60 MB | 重复造轮子（05 同类） |
| 9 | [dougliell/Cheapsfield](https://github.com/dougliell/Cheapsfield) | 2026-10-29 | Windows 本地 Higgsfield 式工作室（产品/建筑向） | 不对口 |
| 8 | [nikaskeba/ComfyUI-Minimax-H3-Reference-Library](https://github.com/nikaskeba/ComfyUI-Minimax-H3-Reference-Library) | 2026-10-28 | 带标签的本地参考库（图/音/视频，自动编号、Qwen 视觉缓存）+ MC 节点 | 外围工具 |
| 8 | [powerhouse90/motionbridge](https://github.com/powerhouse90/motionbridge) | 2026-11-04 | H3 视频→GEM 骨骼动画→任意绑定角色（游戏向） | 不对口 |
| 8 | [ChrisJohnson89/minimax-h3-comfyui](https://github.com/ChrisJohnson89/minimax-h3-comfyui) | 2026-08-05 | 5090 10 步工作流与计时（1344×768×5 s 85 s warm） | 单工作流 JSON |
| 8 | [liaodaobin/comfyui-liao2049](https://github.com/liaodaobin/comfyui-liao2049) | 2026-10-25 | Liao-H3 一体化创作台（六模式、MV 音乐轨、Qwen/Flux3 生图台） | 重复造轮子 |
| 8 | [xmarre/ComfyUI-Untwisting-RoPE](https://github.com/xmarre/ComfyUI-Untwisting-RoPE) | 2026-09-18 | RoPE 频段缩放控制参考注意力（风格↔结构复制），H3 ref2va 原生路径；03 已列 xmarre 伴侣 | 观望（研究向） |
| 8 | [colorAi/Minimax-H3-Studio](https://github.com/colorAi/Minimax-H3-Studio) | 2026-10-29 | macOS/Win 桌面工作台（夸克网盘下载，RunningHub） | 重复造轮子（UI） |
| 8 | [Nynxz/ComfyUI-PTD-Compact](https://github.com/Nynxz/ComfyUI-PTD-Compact) | 2026-10-28 | PTD 适配器 int8/低秩紧凑加载器（EPFL fl2va 4/6 步、taobao Ref2VA 4/8 步） | 观望（PTD 线） |
| 8 | [matlowai/ComfyUI-H3-ContactSheet](https://github.com/matlowai/ComfyUI-H3-ContactSheet) | 2026-08-15 | Contact-Sheet 五视图独立包（已并入 MAINodes，06 已评） | 已覆盖 |
| 8 | [designloves2/AI-ONE-STUDIO](https://github.com/designloves2/AI-ONE-STUDIO) | 2026-11-03 | TJ_NODE_STUDIO_ONE 的独立 Web 壳（非开源许可） | 重复造轮子（UI） |
| 8 | [1038lab/ComfyUI-Open-H3-Regenerate-2K](https://github.com/1038lab/ComfyUI-Open-H3-Regenerate-2K) | 2026-10-29 | Open-H3-Regenerate-2K 单节点（自动下载 8.8 GB/1.95 GB r128 权重、Sharp 曲线、lock_audio）；06 rdh9616 已评 | 重复造轮子 |
| 8 | [MiniMax-design-H3/minimax-design](https://github.com/MiniMax-design-H3/minimax-design) | 2026-08-24 | 商业桌面平台营销页（Veo/Kling/云 API） | 无内容 |
| 8 | [star7code/star7-director](https://github.com/star7code/star7-director) | 2026-10-19 | Star7 画布导演台（自由关键帧、尾部运动引导、二采/修脸、NVENC 导出）；03 star7 chunk 作者 | 重复造轮子 |
| 8 | [Anil-matcha/uncensored-ai-video-generator-comfyui](https://github.com/Anil-matcha/uncensored-ai-video-generator-comfyui) | 2026-10-15 | Muapi 云 API 推广页 | 无内容 |
| 8 | [catiseyeqaq/ai-manju-shengcheng-xitong](https://github.com/catiseyeqaq/ai-manju-shengcheng-xitong) | 2026-09-14 | 8×PPU 集群 + BF16 全量 + SGLang Qwen3.6 润色的写实短剧工程（93 MB） | 硬件不对口 |
| 8 | [lshhhhhhh/ai-culling-game-op](https://github.com/lshhhhhhh/ai-culling-game-op) | 2026-10-03 | 《咒术回战》OP 复刻过程：70/103 单元用 H3 视频编辑，28 单元生图+代码合成；方法论可读（05 已评同作者 ai-school-op） | 案例（可借方法） |
| 8 | [whp199/GemmaPrompt](https://github.com/whp199/GemmaPrompt) | 2026-09-09 | 多模型方言提示词增强（H3 六段式），标准库 Web | 重复造轮子 |
| 8 | [synthetic-ape/comfield](https://github.com/synthetic-ape/comfield) | 2026-10-16 | Comfy Router/SDK 的 Higgsfield 式工作室（云+本地） | 不对口 |

---

## 可写进 skill 的规则（只列 01–07 没有的）

1. 需要「不要 X」时不用否定句，用 NegPiP：装 hako-mikan/comfyui-minimax-h3-negpip，MODEL 与 CLIP 都过该节点，写 `(red fruit:-3)`（短语优于单词，2–4 个实词，−1 为精确翻转、最多约 −5），时段用 `(neon signs:-1.5@2.5-4.0)`、只视频 `@v`、只音频 `@a`；装了它字面括号要写 `\(`。（negpip）
2. 二采/放大前保证 latent 宽高为偶数（像素被 32 整除），否则 H3 核心 circular padding 会在右/下边缘出色条；用 `H3 Latent Upscale By -jingchen573` 或自算；手工重噪二采不要用 stock `AddNoise`（CONST 流模型会被 `SamplerCustomAdvanced` 二次缩放成花屏），音频分支 sigma 要按 shift 3 单独换算（rockerBOO `MiniMaxH3AddNoise` + `MiniMaxH3ShiftSigmas`），`minimax_refs/keyframes` 同步缩放。（wjc573、rockerBOO）
3. 同一提示词多 seed 抽卡时把条件编码落盘复用（pepikir `H3SaveConditioning/LoadConditioning` 或 CLIPCached），采样图里不放 CLIPLoader；32 GB 内存机器单图必须 `--cache-none`（它控制节点输出缓存，`--disable-smart-memory` 控制模型驻留，二者不同），分相后两者都可去掉；文本编码器与 DiT 放 NVMe（编码 90→25 s）。（pepikir、CLIPCached）
4. 若用核心 EasyCache：`end_percent` 封顶 0.70（默认 0.95 的后期跳步造成织纹与色块），不要靠降 `reuse_threshold`（0.05 = 全不跳）；装 LoRA 后日志必须出现 `208 patches attached`，否则 LoRA 无效。（pepikir）
5. 4090 单段帧数上限取 **328 帧**（19×17+5）：345 帧有 6/7 概率个别 step 停滞 2.5–4.8×、整段慢 3–17×；1280 宽改 1216 可让 VAE 解码 tile 28→24、总时长 −15%；VAE tile 保持 256（512+ 不更快且 PSNR 40→21 dB 出格子）。（matsuo-koya）
6. 采样期间不要轮询 ComfyUI HTTP（每次停 18–43 s）；同配置单段耗时涨到 1.8× 时立即重启 ComfyUI（CUDA 崩溃前兆）；渲染时关闭杀毒实时扫描。（matsuo-koya、IvenKooLab）
7. 量化底模（int8_convrot）上挂 LoRA 优先运行时分支/bypass，不反量化合并：合并往返注入 ~1.5% 权重噪声而 H3 LoRA delta 只有 0.01–0.08%，w4a8 上只还原 <1/3；多 LoRA 用 PowerLoraStack `quantized_layers=auto`，视频风格 LoRA 把 audio 模态缩到 0–0.25；同为 1.0 的 LoRA 扰动幅度差 65×，叠加前先看 `rel dW` 报告。（PowerLoraStack、Dantemss）
8. Turbo 无 CFG 链路的微调旋钮用 Fizgig H3 Tweaks（LoRA 之后、采样器之前）：`Detail & Contrast 0.15`（stable across frames）提皮肤纹理、`Prompt Strength 0.2` 起步当提示词跟随旋钮、`Scene Variation ±0.1–0.3` 当子种子；不与块跳过类节点同挂。（Fizgig-Tweaks）
9. I2V 尾帧接力链：`anchor_mode=inpaint`（复制 + 遮罩保护）而不是 keyframe（接缝帧间跳变 5.4–6.8× → 1.5–1.7×），上下文 5 帧而不是 22（22 恶化到 19×）；换人/换装续接链对上下文做锥形加噪 22/0.45/0.10/3 消色彩残留，加噪结果不回喂。（LongTake、Context-Noise）
10. Ref2VA 换人保脸：脸部特写单独作 `<Picture 2>` 并在提示词点名（ArcFace +0.12），同图重复第三次无效；成片用 8 步 v1.0 768p 而非 4 步 v0.1（闪烁 −18%、最差秒 +0.11）；V2V 风格化用 NRDX StyleTransfer LoRA r64 + `source_role=guide`。（LongTake）
11. Open-H3-Regenerate-2K 重画时保护人脸：YuNet 脸区图 + `face_strength 0.55`（脸从 σ0.50 起，全图 0.909/0.857/0.667/0），只挂 Kijai refiner LoRA 1.0、不叠 Turbo/Sharp、音频用草稿原音（ArcFace 0.52→0.91）。（Open-H3-FaceRegion）
12. 道具/属性/材质类参考用 Qwen-only 语义参考（`#tag`，可带时间戳，不占 9/3/3 名额，256–512 px），身份与具体帧锚才用原生 VAE 参考。（Timed-References、H3-Edit）
13. 多段方案选型（5090 实测，借用）：要跨段保持音色选 FastH3 Omni 或 Pika Flex（全程 Ref2VA，第二段音色匹配 0.89–0.96 vs PDMD 0.72–0.75）；Pika Flex 声音最清但慢 1.5× 且每 12 段 15 s 有 233 个定格帧，需 de-stutter；后段声音发闷改「只续画面、声音重生」；PDMD 后段变暗变饱和时改「只用末帧」；硬切新镜头在段首 0.5 s 放中间帧。LightX2V 768p turbo 用 shift 6/3，544p turbo、PDMD、FastH3 Omni、Pika 用 12/3。（Stubelius）
14. Sol/块稀疏注意力只在 ≥768p 成片档开（1.23–1.27×）；480p/fast 档 1.03× 且高频 −13.8%。放大路线按需选：保内容像素超分（RealESRGAN ×2 68 s；RelayVSR ×2 25 s 最快；SeedVR2 要纹理）、接受重画才用 Regenerate（557 s）；超分逐镜做不对成片做。（dsh）
15. 剧情片提示词别一味削短：首帧图要当质感底子时保留/加长描述（811–869 token），用「夹句」（核心指令首尾各一遍）提高指令权重；对白交锋段不给音乐；做不到的动作换写法不重抽（机械开合→空镜硬切、走位→直接「已到位」、群体反应→单人 + 画外声、画内文字→只留大号数字）；自动审片器先拿历史合格帧跑误杀回归。（L-Trunks）

---

## 未处理清单

- 219 个仓库 README 全部读完；39 个浅克隆读源码；其余 180 个只读 README（未克隆），其中以下几个体量大、仅凭 README 判断，若后续需要可补克隆：`Jalen-Brunson/ComfyUI-HybridWindows`（55 MB）、`PullMyBoots/ComfyUI-H3-FaceRefine-Accelerated`（43 MB）、`nazgut/ComfyUI-MiniMaxH3-CLSS`、`hyukudan/ComfyUI-MiniMax-H3-Prompt-Enhancer`、`xmarre/MiniMax-H3-Flow-Aligned-Regenerate`、`red-polo/ComfyUI-MiniMaxH3FrameInfill`。
- 未下载/未验证任何模型权重或数值（X2 Detail VAE、taeh3_decoder、StyleTransfer LoRA、Semantic Bridge 适配器）；sepiablue 的「Sayaka Benchmark」为作者自建站点，数字未独立复现。
- `stars < 8` 的 ComfyUI 仓库（约 770 个）与非 ComfyUI 长尾不在本次范围。
