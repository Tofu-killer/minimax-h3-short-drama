# 03 · 加速 / 显存 / 量化 / 注意力 / 缓存 / 蒸馏 LoRA（GitHub 精读）

> 精读日期 2026‑11‑07。覆盖 29 个仓库（源码级），与 docs/11-acceleration.md 互补：那里已写 SageAttention、核心 BlockSparseAttention、comfy kitchen、TE‑Speed 实测、DaSiWa Cache、lightx2v Turbo、4090 实测，本文只补新项目与纠错。星数/许可证/推送日期取自 relevant.json（2026‑11‑07 抓取）。所有速度数字都注明作者硬件与 分辨率×时长×步数，均为作者自报，未独立复现。

## 本簇结论（4090 24GB · Windows · ComfyUI 0.37.2）

1. **立刻采用**：维持「int8_convrot + lightx2v Turbo 8 步 + KJ SageAttention」基线；加速叠加只在同 seed A/B 后启用。新增两条可直接用的规则：Sage 与 KJ LowVRAM 不同开（本地已证）、任何蒸馏（Turbo/PDD/HyperFlow/VDN）互不叠加（PDD‑Acc、VDN‑H3、HyperFlow 三家作者一致声明）。
2. **最值得试用（需先把 ComfyUI 升到 0.38.x）**：**Veda**（学习型稀疏注意力，预测器正好按 1344×768 / 5–10–14 s / 8 步 Turbo 训练，5070 上比 Sage 再快 1.78×，可叠在 KJ Sage 之上；但 sm89 当时仅静态审查未上机）与 **Spark‑H3**（有 Windows SM89 安装包，20 步下 5 s 1.41× → 14.4 s 1.84×，5 s 短片不比 Sol 快）。两者只选一个。
3. **精修档（20 步无 Turbo）可试**：Spectrum（11 实际 + 9 预测，作者明言 Turbo 叠加画质变化更大）或 FirstBlockCache `H3 Fast`（5090 上 −30%，专为 ~20 步调参）；二者互斥，且都不要与 EasyCache/LazyCache/T8 BlockCache 同链。
4. **Ref2VA 抽卡的激进选项**：Kablex Ref2VA‑VSA（4090 上 1344×768×5 s 4 步 72 s、13.5 GB），但它**拒绝与 SageAttention 共存**，只配 4 步 v0.1 预览 LoRA，画质需自测。
5. **观望**：VDN‑H3（换架构，作者自己说显存紧的卡不推荐；收益随时长增长，≥10 s 再评估）、HyperFlow（另一条 8 步蒸馏线，需完整底模，pruned 只能半套）、PDD‑Acc（官方 8 步 LoRA，写实向可 A/B，4 步会压平插画质感）、H3VAE_TRT（VAE 1.7×，但 VAE 只占流水线一小段，Windows 装 TensorRT 麻烦）、ClipProj（TE 15.7 GB → 4.6 GB，主要省内存，不省采样时间）、HybridLoader（fl2va 底 + ref2va AdaLN，画质向不是速度向）。
6. **别碰**：lihaoyun6 Cache（启动时替换核心 `_forward`，已停更）、TE‑Speed OSS（patch 核心 model.py，8 步 Turbo 下失真已证）、tl2012tl TE‑Speed 3.5（闭源 .pyd 无法审计）、W4A4‑VSA（12 GB 卡方案，作者自测核心 SLA 5% 同样快）、xmarre Sol‑H3（仅 SM120 Linux/WSL2，Windows 空转）、RH MultiGPU（8 卡 SGLang、权重未公开）、pottokao GGUF‑Qwen3VL‑TE（Qwen‑Image 用，README 明说 H3 编码器不受影响）。
7. **纠错 docs/11**：① 官方索引与 T8 BlockCache 源码都确认「核心 BlockSparseAttention 节点已合并 Sol/SLA/VSA」，第三方 Sol 节点（Saganaki22/kijai）基本被核心取代；② alesha‑pro 在 3090 上实测 Turbo `low_vram=on`（合并）反而比 bypass 快 25% 且近景皮肤更干净，与 Larryvrh「bypass 最锐」相反——4090 上应自测而非照抄；③ Spectrum 的 −29% 来自 20 步，8 步 Turbo 下最多 3 次预测且作者不建议。

---

## 逐仓库精读

### xmarre/ComfyUI-Spectrum-MiniMax-H3（★715，GPL‑3.0，最后推送 2026‑10‑31）

- **定位**：训练无关的「特征预测跳步」，把 Spectrum 论文（Chebyshev 多项式 + 岭回归外推去噪特征）移植到 ComfyUI 原生 `comfy.ldm.minimax.model.MiniMaxH3Model`。
- **机制（源码）**：`SpectrumApplyMiniMaxH3`（`sampling/spectrum`）克隆 MODEL，在实际步记录最后一个 transformer block 之后的 packed 目标隐状态（只存 target 音频+视频行，不存文本/参考行），预测步跳过全部 50 个 block、用历史锚点外推隐状态后仍走原生 final layer。默认 `blend_weight 0.5 / audio_blend_weight 0.0 / degree 1 / ridge_lambda 0.10 / window_size 2.0 / flex_window 0.75 / warmup_steps 1 / tail_actual_steps 1 / max_history 8 / history_storage system_ram / offline_smoothing_replay true`。`offline_smoothing_replay` 是两遍采样（捕获 + 无 transformer 回放），不增加 NFE，但预览回调只在回放时触发。
- **数字**：20 步 Euler/ER‑SDE 典型调度 `A F A F … A A` = 11 实际 + 9 预测（≈−45% NFE）；Multishot 实测 −29% 端到端（见 docs/11）。
- **兼容**：不替换 attention backend，Sage/CK 都可（Issue #41 CK+Spectrum 二次生成卡死，需 ComfyUI 新于 H3 CK 峰值显存修复）；**EasyCache/LazyCache 同链时 Spectrum 自动失效**；T8 BlockCache 会直接拒绝 Spectrum；支持 Euler、ER‑SDE、RES multistep、SEEDS‑2/3、SA‑Solver、Larryvrh `_turbo_sampler`、RefDelta。最低 ComfyUI 提交 `e377e263`。
- **对 4090 的价值**：只在 20 步精修路线有意义。8 步 Turbo 下 warmup 1 + tail 1 最多 3 次预测，作者明言「Turbo 叠加后构图/运动/细节变化明显大于 20 步路径，当作独立取舍而非免费加速」。
- **坑**：高分辨率长片历史可达数 GiB（放 system_ram）；GPL‑3.0。
- **评级**：精修档（20 步）试用｜8 步 Turbo 跳过。

### Kablex/ComfyUI-Ref2VA-VSA（★895，Apache‑2.0（relevant.json 记为 NOASSERTION，LICENSE 文件为 Apache），最后推送 2026‑10‑17）

- **定位**：把 FastVideo 的 VSA（4×4×4 token tile、学习型 `to_gate_compress` 粗门控 top‑k）移植到 **Ref2VA**，解决参考前缀与视频 tile 混叠的问题。
- **机制（源码 `nodes.py`）**：`Ref2VAVSAGatePatch(model, gate_file, sparsity=0.70)`（README 工作流用 0.75，类别 `FastH3/VSA`）：从 `fasth3_vsa_gate.safetensors`（HF barelymining/ComfyUI-MiniMax-H3-FastVideo，或用 `tools/extract_vsa_gate.py` 从 FastH3 VSA 权重抽取）加载 50 个门控矩阵挂到 ref2va 的 50 个 block；几何映射把文本/参考图/参考音频/目标音频行放进「段纯净」tile 并全部 dense（`sink_blocks`/`sink_q`），只对生成视频 key tile 做 top‑k；内核调用 `comfy_kitchen.sol_attn(..., topk_ratio=1-sparsity)`。安装时检查 `transformer_options["optimized_attention_override"]`，**已有 SageAttention/Sol 等 attention 补丁则抛错**；已有其它 `dit` patch_replace 也抛错；要求 comfy‑kitchen CUDA 后端暴露 `sol_attn`。
- **数字（作者 4090，1344×768×124f，同 seed）**：VSA 4 步 euler/simple ≈ 72 s 热 / 95 s 冷，峰值 13.5 GB；VDN‑H3 8 步 135 s / 18.5 GB；Turbo 4 步 dense 190 s / 21 GB；原生 50 步 650 s。
- **工作流**：`ref2va_pruned_int8_convrot` → `LoraLoaderModelOnly(ref2v_turbo_4step_v0.1_comfyui_bf16, 1.0)` → `Ref2VAVSAGatePatch` → `MiniMaxH3SigmaShift(12, 3)` → BasicScheduler simple 4 步 → euler。
- **对 4090 的价值**：Ref2VA 768P 抽卡最快路径之一；代价是放弃 Sage、只能用 544p 训练的 4 步 v0.1 预览 LoRA（docs/11 已指出其音频/大动态较差）。dense 基线 190 s 疑未开 Sage，实际相对 Sage 基线的提速应小于 2.6×。
- **坑**：README 称 FastVideo 「datafree 1300step」门控是 T2V 训练，移植到 Ref2VA 为实验性；无 Windows 说明（纯 Python + kitchen，应可跑）。
- **评级**：草稿档（Ref2VA 抽卡）试用，必须与 Sage 基线同 seed 对比参考保持与口型。

### Saganaki22/ComfyUI-VDN-H3（★244，Apache‑2.0，最后推送 2026‑09‑12）

- **定位**：OpenVDN 混合注意力（近帧滑窗 softmax + 远帧线性 delta 分支）的 ComfyUI 纯 PyTorch 移植，「是 port 不是 fork」，不改核心文件、零新依赖。
- **机制**：`ApplyVDNH3` / `ApplyVDNH3Advanced`：`vdn_checkpoint`（`models/vdn/<stage目录>`）、`apply_turbo_adapter`（ON = 8 步 DMD 模型，OFF = 50 步）、`strength 1.0`、`lora_mode merge`（**DMD 阶段必须 merge**，bypass 的 bf16 舍入在 34+ 层放大到 ~10% 导致颗粒）、`branch_weights auto`（空闲显存 ≥1.5×stage+4 GiB 才驻留 GPU，否则按块流式）、`attention_backend grouped`。滑窗 softmax 只走精确 SDPA（flash/cuDNN），**不走 Sage/kitchen int8**；Sage 补丁只作用于 token refiner 与短序列 dense 回退。
- **数字**：5090 Windows，int8_convrot 底模 + bf16 分支，1280×736×145f×8 步 er_sde/beta：17 s/it → 优化后 13.9 s/it（≈2 分钟采样）；int8 分支（drbaph 2.2 GB）同 seed 比特一致，1280×736×61f 111 s → 95 s。4090 第三方（Kablex）：1344×768×124f×8 步 135 s 热、18.5 GB。
- **叠加**：8 步 `turbo` adapter **取代**社区 Turbo LoRA，不可同开；**不可与 Sol 调度补丁同链**（都替换 `attn.forward`）；Sol 的 FFN 分块与通用 attention override 可共存。Comfy Compiler（2026‑09‑04 后）与 VDN 冲突，节点运行时自动关闭。
- **对 4090 的价值**：作者原话「显存/内存有限不推荐」；5 s 片在 4090 上与 Turbo+Sage 基线相当，优势在 ≥10 s（注意力线性增长）。VAE 解码用 `VAEDecodeTiled`。
- **坑**：需额外 2.2–5.1 GB 分支权重（HF `OpenVDN/vdn-minimax-h3` 的 `stage-dmd-step-250/` 或 `drbaph/vdn-minimax-h3-int8-convrot-comfyui`）；`fast_kernels` 在 DMD 阶段有漂移，别开；训练只覆盖 t2va 布局，ref2va 可跑但未训练。
- **评级**：观望（做 15 s 单段时再测）。

### Saganaki22/ComfyUI-sol-attn（★159，Apache‑2.0，最后推送 2026‑08‑13）

- **定位**：NVIDIA Sol‑Attn Triton 内核 + 四个 H3 专用节点，面向 Windows 原生 SM120；v0.6.2 加入 SM86，SM89 由 4080 SUPER 社区烟测。
- **节点**：`SolAttentionPatch`（通用，`tau 1.3 / min_tokens 4096 / int8_qk / int8_pv / thresh_type diag`）；`MiniMax H3 Memory Efficient Sol Attention Patch`（零拷贝读 fused qkv，`sink_conditioning exact_kv`、`dense_blocks "0-2,-1"`）；`MiniMax H3 Scheduled Sol Attention Patch`（`tau_start 1.3 → tau_end 0.8`，`dense_percent 0.2` 为论文配方，输出 tau 曲线图）；`MiniMax H3 Fused Modulation`（AdaLN/门控融合，比特一致）；`MiniMax H3 Chunk FeedForward`（`chunks 2 / min_tokens 8192`，int8 底模上 65K token 省 1.9 GiB）。
- **顺序（强制）**：KJ `Patch Sage Attention` → KJ `MiniMax H3 Memory Efficient Sage Attention Patch` → 本包 Sol 节点；反过来 Sage 会完全遮蔽 Sol。KJ `MiniMax H3 Low VRAM Attention` 不能与 `Fused Modulation` 同用。
- **数字**：内核 bf16 为 Sage 的 1.38–1.65×（8K–65K token），int8_qk 1.73–1.97×；整模一例 480×864×15 s×20 步 res_multistep：Sage 9.91 s/it → Sol 8.92 s/it（−10%）。<4K token 时 Sage 更快。每个新 token 数首跑有 Triton 自动调优。
- **对 4090 的价值**：ComfyUI 核心已把 Sol/SLA/VSA 合进 `Block Sparse Attention` 节点（T8 BlockCache 与官方索引都注明 commit `e308cc73b`），用户 docs/11 已测核心 BSA；本包的独立价值只剩 `Chunk FeedForward`/`Fused Modulation`，而 KJNodes 也有 `MiniMaxChunkFeedForward`。
- **坑**：需 triton‑windows；最后更新 8 月，ComfyUI 0.30 时代开发。
- **评级**：跳过（用核心 BlockSparseAttention）。

### Saganaki22/ComfyUI-Hyperflow（★59，Apache‑2.0，2026‑10‑14）与 Video-Rebirth/hyperflow（★162，Apache 代码 / MiniMax 社区许可权重，2026‑09‑18）

- **定位**：Video Rebirth 的 8 步自蒸馏 LoRA（rank 256，2.8 GB；ComfyUI 转换版 3.67 GB）+ **双时间 (t, r) 条件**（每步额外输入积分区间端点 `r = 1 − sigma_next`，AnyFlow 流图思路）。
- **机制**：`ApplyHyperFlow(model, hyperflow_file, strength 1.0, lora_mode bypass, variant auto, download_if_missing false, experimental_curve_refit false)` 输出 MODEL + **SIGMAS**（固定 9 点网格，必须接 `SamplerCustomAdvanced` 取代 BasicScheduler），Euler。完整底模（有 `time_embedder`）才有双时间路径；**pruned 底模只能 backbone‑only 单时间（脱离配方）**，`experimental_curve_refit` 用 34 KB 拟合补回大部分（FL2VA 视频余弦 0.81→0.88，REF2VA 音频 0.93→0.99）。int8 融合层自动走 merge。
- **数字（上游，H200）**：1344×768×124f，49 NFE 395 s → 8 NFE 130 s（3.0×）；Sol‑Attn 叠加（dense_steps 2、dense_layers (0,1)、tau 1.0）相对 dense PSNR≈23 dB，作者要求先看效果。画质声明「更好的镜头控制/一致性/材质」为自评。
- **叠加**：是蒸馏，**不与 Turbo/PDD/VDN 叠加**；核心 `Model Sparse Attention` 可接在后面（`start_percent 0.16` 对应前两步 dense）。
- **对 4090 的价值**：lightx2v 8 步出现塑料感/拖影时的替代候选；用户的 int8_convrot 完整底模（非 pruned）满足双时间条件。drbaph 提供可用 stock `Load LoRA` 的单文件版但缺双时间条件，不推荐。
- **坑**：ComfyUI 0.37 「Model Initializing」卡住报告，诊断 `--disable-fast-disk`；首块 bypass 多占显存（merge 可省）。
- **评级**：观望（A/B 候选）。

### Jalen-Brunson/ComfyUI-MiniMax-H3-PDD-Acc（★136，Apache‑2.0，2026‑08‑30）

- **定位**：加载阿里 PAI 官方 8 步 PDD LoRA（`alibaba-pai/MiniMax-H3-Acc-LoRAs`：`MiniMax-H3-FL2VA-Acc-8Step` / `Ref2VA-Acc-8Step`，rank 64），含普通加载器会丢掉的 **32 个 final‑layer 输出头**。
- **机制**：`MiniMaxH3PDDAccApply(model, pdd_file, nfe 8|4|6, lora_strength 1.0, head_strength 1.0, on_off_grid error, partition "", partition_check error)` 输出 MODEL + SIGMAS（`12t/(1+11t)` 网格）；按 sigma 装配头，只允许块大小 4/8；trunk 指纹防止 FL2VA/Ref2VA 错配（否则静默出错）；pruned 底模把 AdaLN LoRA 重投影到 8 维曲线基。**必须 Euler、CFG 1.0、SigmaShift 恰好 12/3**；er_sde/res_multistep 会越网格。
- **叠加**：「移除 lightx2v 等其它蒸馏 LoRA，蒸馏不叠加」；「不要叠 blockcache/EasyCache，final‑layer 补丁会 fail‑closed」。
- **官方索引补充**：ComfyUI ≥0.33 已原生支持 LoRA‑bank，本节点在新版上「冗余」；2080Ti/4090 线程的现场笔记：PDD 4 NFE 会压平插画纹理，Turbo v4‑600 保留更好，8 步差距基本消失。
- **对 4090 的价值**：写实短剧的 8 步 A/B 候选（官方训练、FL2VA/Ref2VA 各一）。漫剧风格优先 Turbo。
- **评级**：试用（仅作为 lightx2v 8 步的对照）。

### duckyshell/ComfyUI-MiniMaxH3-FirstBlockCache（★113，MIT，2026‑10‑12）

- **机制（源码）**：每步算 block 0，比较 block 0 残差与上一步的平均绝对差，≤阈值则复用上一步 block 1–49 的残差（`first_output + cached_tail_residual`），否则全算；预设 `H3 Safe 0.08 / H3 Fast 0.10（默认）/ H3 Aggressive 0.12`，窗口 10%–95%，连续命中上限 2，可选 `temporal_guard`（按最大变化帧判定）。用 `DIFFUSION_MODEL` wrapper + `dit/double_block` replace，不改核心。
- **数字**：5090、int8_convrot、0.5 MP×5 s×20 步 res_multistep：Sage 57.96 s → 40.26 s（−30.5%）；原生 attention 90.64 → 60.82 s。
- **叠加**：Sage 可；**不可与 EasyCache/LazyCache/CacheDiT/T8 Block Cache 或其它 double_block 替换同用**。预设「为 ~20 步调参」；8 步 sigma 间隔大，几乎无命中（看控制台 hit 数）。
- **评级**：精修档 20 步试用（与 Spectrum 二选一）；8 步跳过。

### T8mars/comfyui-minimax-h3-blockcache-T8（★146，Apache‑2.0，2026‑09‑07）

- **机制**：同为 F1B0，但音频与视频残差分别判定、任一超阈值就全算；`residual_diff_threshold 0.12 / start 0.08 / end 0.95 / max_consecutive_hits 2 / cache_device cpu / metric_stride 8`。明确拒绝 EasyCache、LazyCache、Spectrum、核心 Block Sparse Attention 与其它 double_block 替换；Sage 可用。对新版 ComfyUI（FLOW_AV、PDD final layer、prefetch、Comfy Compiler）做了大量兼容分支。
- **数字**：作者仅 4060Ti 256×160×5f×20 步烟测 1.09–1.20×；docs/11 已记 Multishot「14 步几乎无效」。
- **评级**：跳过（FirstBlockCache 数据更全、维护更新）。

### lihaoyun6/ComfyUI-MiniMaxH3-Cache（★77，GPL‑3.0，2026‑08‑03）

- **机制**：`__init__.py` 在导入时把 `comfy.ldm.minimax.model.MiniMaxH3Model._forward` 整个替换成自带版本以注入 `("dit","block_loop",0)` 钩子，再用 `set_model_patch_replace` 接管块循环；参数 `resuse_threshold 0.10 / start 0.15 / end 0.90 / max_steps 2 / device auto`。README 自己警告「patch 核心文件，出问题请删」。
- **评级**：跳过（8 月停更，0.37 的 H3 forward 已大改；DaSiWa 的 `MiniMaxH3Cache` 是其后继，见 docs/11）。

### lihaoyun6/ComfyUI-H3VAE_TRT（★254，Apache‑2.0，2026‑09‑06）

- **机制**：H3 视频 VAE 导出 ONNX（HF `lihaoyun6/MiniMax-H3-VAE-ONNX`，另有 `w4a16_awq` 解码器给 <12 GB），`MiniMax-H3 TRT VAE Compiler` 节点按本机 GPU 编译 engine，`MiniMax-H3 TRT VAE Loader` 加载；时序分块 + 256 空间 tile（重叠 64）；`requirements.txt` 仅 `tensorrt`。宣称最高 1.7×。
- **对 4090 的价值**：VAE 解码在 10 s 768P 流水线里约占 30–60 s，1.7× 只省 ~15–25 s；Windows 装 TensorRT 与 cu130 匹配麻烦。预览需求用 Kijai `taeh3` 更划算。
- **评级**：观望。

### HELPMEEADICE/TE-Speed-MiniMaxH3-OSS（★344，LGPL‑3.0，2026‑08‑03）

- **机制**：TE‑Speed 1.x 的开源重实现。`patch_model.py` 修改核心 `comfy/ldm/minimax/model.py`（加 `_run_blocks(start,end)` 与 `("block_loop",0)` 钩子，备份 `.te_speed.bak`）。节点 `TESpeedMiniMaxH3`：`processing_control_value 0.12`（相邻步 sigma 差阈值）、窗口 `0.1–0.9`、`mcs 2`、`cache_depth 0.75`（缓存步只重算前 25% 块，加上一步保存的尾部残差）。作者：30 步 8 s 片 ≈ −45%。
- **评级**：跳过（docs/11 已证 8 步 Turbo + int8 下文字乱码/手嘴变形；且 patch 核心文件在 0.37 上大概率失配）。

### tl2012tl/TE-Speed-MiniMaxH3（★114，无许可证，2026‑09‑06）

- **机制**：闭源 `nodes.pyd`（Cython 编译、链接 `python3.dll` 稳定 ABI，Windows 专用，396 KB）。README：3.0 加「4‑step LoRA」模式按实际步数自动选策略（1–10 步短轨迹专用），3.2 加 >10 s 长视频缓存策略、CPU 残差分块传输、附带「可与 TE‑Speed 同开」的 KJ Sol 改版，3.5 适配 Comfy Compiler/核心 BSA/PDD。
- **评级**：跳过（无法审计源码、无许可证、无 A/B 数据；官方索引也标 ⚠️）。

### sepiablue-ai/ComfyUI-MiniMax-H3-W4A4-VSA（★124，GPL‑3.0，2026‑10‑15）

- **机制**：FC1 权重/激活 4 bit（ConvRot W4A4，一次性预转换 5.8 GB 缓存）+ Streaming VSA（INT8 门控放 CPU，按层送 GPU，`keep_percent 5`），节点 `H3V2PreconvertedLoader` + `H3V2StreamingVSAPatch(keep_percent 5, min_tokens 12288)`；依赖 KJNodes `MiniMaxChunkFeedForward`、Mozer `MiniMaxH3FastVAEDecode`、MATLOWAI 融合模型 `minimax_h3_fused_refdelta_r1024_turbo8_mystic07_int8_convrot`；`setup.bat` 一键；验证 ComfyUI 0.36.0、kitchen 0.2.34；推荐 `--disable-comfy-compiler`。
- **数字（4070 12GB，1024×1792×124f×4 步）**：dense 672 s → 197 s；**但 ComfyUI 核心 Block Sparse Attention SLA 5% 为 189 s**，作者承认核心方案同样快甚至略快。
- **评级**：跳过（24 GB 卡无需 W4A4）；保留其结论：核心 SLA 5% ≈ 3.4× dense。

### star7code/minimax-h3-chunk-star7（★98，MIT，2026‑10‑24）

- **定位**：原「ActivationChunkStar7」已膨胀为全家桶：核心 `MiniMax H3 显存分块加速 - Star7`（QKV/RoPE/MLP 沿 token 分块 + OOM 自动减半 + attention 后端选择 `existing / comfy_kitchen_int8 / sla_sm80+ / sol_sm80+_bf16_official / vsa_sm80+ / hybrid_sm80+_ck_*`），另有 VDN 节点、VEDA 节点、Spark/VPack 节点、TAEH3 实时预览、人脸修复、latent 放大、分块解码、W4A8 载入。
- **参数建议（作者表）**：20–24 GB：`chunk_tokens(RoPE) 8192 / mlp_chunk_tokens 4096 / qkv_chunk_tokens 4096`。作者强调「分块只降峰值不降 FLOPs，原本能驻留显存时不会更快」。Hybrid = 按步切换：4 步工作流第 1、4 步 CK、第 2、3 步稀疏。SLA 建议配 `lightx2v/Minimax-h3-Turbo-SLA` LoRA。
- **数字**：仅 2080Ti 22GB（SM75）：1.0 MP×10 s×4 步 Turbo，KJ SM75 Sage 190 s/step → CK int8 119.5 → SLA 96.7 → SLA All‑INT8 60.8 s/step；对 4090 无直接数据。SM80+ 稀疏走 Triton/CK。
- **对 4090 的价值**：用户已装；只在 1344×768×15 s 爆显存时开分块，日常关闭；别用它的 `existing` 以外后端与 Sage 叠。
- **评级**：观望（保留作 OOM 保险）。

### zechengtang/Spark-H3（★162，Apache‑2.0，2026‑11‑07）

- **机制**：Spark‑Attn = Reblock（相似 token 重分块后 top‑k）+ Reweight（尾块 K/V 摘要加权并修正注意力质量）。ComfyUI 节点 `MiniMax H3 Spark Attention (SM89)`：预设 `fidelity`（默认，20% 模型评估为 dense 预热）/ `speed` / `custom` / `dense`；`topk_mode topk_ratio`，示例 `topk_ratio 0.2`（LBH 二采第二段 0.1）；`sparse_scope target-video`（Ref2VA 有参考视频时切 `joint-video`）；`dense_backend inherit|kitchen|sage|sdpa`；`producer_chunk 16384`。v0.2.0 用独立 `spark-h3-kitchen 0.2.37`，不再覆盖官方 comfy‑kitchen；**Windows SM89 ZIP（CUDA 13.0 wheel）**；支持 ComfyUI **0.38.x–0.40.x、0.42.x–0.44.x**（用户 0.37.2 不在列）。可接在 KJ `Low VRAM Attention` → `Chunk FeedForward` 之后；「一个模型只挂一个 attention 补丁」。附 Larryvrh LoRA 转 ComfyUI 格式脚本、LBH 两段式工作流（0.2 MP 4 评估 → latent 放大 → 0.98 MP 3 评估，sigmas `0.9035, 0.6316, 0.3158, 0`，第二段 `speed` + 10%）。
- **数字**：内核矩阵（A800 / RTX PRO 6000，20 步 dense SDPA 基线，1344×768）：5 s 1.41×、10 s 1.70×、14.4 s 1.84×。3090（改 48 GB）Turbo 8 步 1344×768×124f：spark 158 s vs `sol_attn_chunked` 152 s 采样——**5 s 短片不比核心 Sol 快**。10‑25 公告：新 comfy‑kitchen 有回归，推荐验证过的 0.38.x。
- **评级**：试用（升级到 ComfyUI 0.38.x 后，≥10 s 精修档；与 Veda 二选一）。

### veda-sparse/Veda-on-ComfyUI（★223，MIT，2026‑10‑11）

- **机制**：学习型稀疏注意力：275 MB fp8 预测器提前选出 ~10% 注意力 tile，Triton INT8 内核（算术源自 SageAttention v1）。节点 `VedaSparseAttention(model, predictor)`，高级项 `generated_sparsity trained(90%/R2VA 32 tiles)`、`reference_sparsity`、`full_attention_layers`、`full_attention_steps`。作为 `optimized_attention` override：**可叠在 KJ `Patch Sage Attention` 之上**（Veda 接稀疏层、其余给 Sage），KJ `Low VRAM Attention` 可共存，KJ `MiniMax H3 Mem Eff Sage Attention Patch` 必须放在 Veda **之前**；**不可与核心 `Model Sparse Attention` 同链**。内核自检失败会报错而非静默回退。要求 **ComfyUI ≥0.38.0**，pip 自动装 `triton-windows`。
- **训练覆盖**：预测器按 **1344×768 / 768×1344 / 768×768 / 1024×768 × 5/10/14 s × 8 步 Turbo LoRA** 训练（T2VA/FL2VA 共用 `minimax_h3_t2va_veda_8nfe_600step_preview_fp8`，R2VA 另有 `minimax_h3_r2va_veda_preview_fp8`），其他尺寸退回最近 tile 计划。
- **数字（5070 12GB，Windows，T2VA 1344×768×124f×8 步 Turbo）**：默认 attention 342 s → `--use-sage-attention` 231 s → Veda 130 s（每步 14.0 s，注意力 4.41 s）。
- **坑**：`docs/hardware.md`：sm86/sm89「只做了静态审查，没有上机」（2026‑10‑03）；portable Python 缺头文件时 Triton 首编译失败（报错会误导成「此卡无内核」）；二采工作流曾周期性闪烁，已改固定 32 tile 预算；ComfyUI 0.38 aimdo malloc graph 需 `pause_malloc_graph`（已处理）。
- **评级**：试用（用户场景与训练集完全重合；升级 ComfyUI 后第一个该测的稀疏方案，Ctrl+B 旁路同 seed 对比）。

### xmarre/ComfyUI-Sol-H3（★53，GPL‑3.0，2026‑11‑06）

- **机制**：打包 Sana `sol-engine` 的 CuTe `cute_sm120` 内核 + Exact Runtime，仅 **SM120/SM121 Linux/WSL2**；README 明说「原生 Windows 两条自定义内核路径都 fail‑closed，节点留在图里但不执行任何加速」。默认 `tau 1.0 / dense_evaluations 1 / dense_layers 2`。
- **评级**：跳过（4090 + Windows 双重不符）。

### scottmudge/ComfyUI_MinimaxH3HybridLoader（★184，MIT，2026‑08‑11）

- **机制**：`MiniMaxH3HybridLoader(base, overlay, overlay_preset block_range_adaln, block_range_start 25, block_range_end 49, final_adaln_from_overlay false, weight_dtype)`：mmap 逐 tensor 流式合并，int8 `.comfy_quant` 随权重同行；输出与 stock 加载器一致。作者张量对比：fl2va 与 ref2va >97% 权重几乎相同，差异集中在每块 `adaln_proj`、`final_layer.adaln_proj` 与输出头；推荐 fl2va 为底 + ref2va 25–49 块 AdaLN，主观「参考能力与画质最佳折中」。
- **对 4090 的价值**：画质向（ref2va 底模训练质量问题的绕法），不省时间，多一次加载；与 Turbo ref2v LoRA 的匹配未验证（PDD‑Acc 的指纹检查会对 hybrid 报 trunk 警告）。
- **评级**：试用（精修 Ref2VA 画质 A/B）。

### nicolab28/ComfyUI-ClipProj（★184，MIT，2026‑08‑17）

- **机制**：用 Qwen3‑VL‑4B/8B + 岭回归线性投影（`cond = ((h-μ)/σ)·W·σ_out+μ_out`）替代 32B 文本编码器；矩阵在 HF `NicoLab28/ClipProj-MiniMax-H3`（v3.1：`mmh3-4b-ClipProj-v3.1` 26 MB / `-mlp` 481 MB）。单卡推荐 stock `Load CLIP`（type `krea2`=4B / `boogu`=8B）→ `ClipProjApply`；`ClipProj Loader (all-in-one)` 仅多卡用（单卡会把 4–9 GB 钉在显存里反而更慢）。15.7 GB → 4.6 GB。
- **质量**：测试余弦 0.71（线性上限），作者称 DiT 容忍度高，多镜头结构化提示词 ✅；语音音素错误与「换 seed」同量级；v3.1 主要改进非英语发音。int8 编码器只能 resident 模式。
- **对 4090 的价值**：TE 每次改提示词才跑一次并会卸载，省的是内存与首次编码时间，不省采样；短剧对提示词遵从要求高，精修不用。
- **评级**：观望（内存 <48 GB 或抽卡快速迭代提示词时可试）。

### Larryvrh/ComfyUI-MiniMax-H3-Turbo（★625，Apache‑2.0，2026‑08‑14）

- docs/11 已覆盖。补充：节点包含自定义 `MiniMaxH3TurboSampler`（Spectrum 识别其 `_turbo_sampler` 为确定性单调用合同）；`low_vram` 合并 vs bypass 的取舍**在 alesha‑pro 的 3090 上反转**：合并 2:42 采样 / 3:45 全程，bypass 3:37 / 7:07，且作者称合并版近景皮肤更干净——4090 应自测两档而非默认 bypass。
- **评级**：采用（已在用）。

### ModelTC/Minimax-H3-Turbo（★411，Apache‑2.0，2026‑08‑27）

- docs/11 已覆盖规格表。补充源码级细节：`NFE=N` 时评估点 `q_i=(N-i)/N`，shift 12/3 的 4 步视频 sigma `[1, .973, .923, .80]→0`、音频 `[1, .9, .75, .5]→0`；参考图 `ref_image_size=match` 为蒸馏训练设置（永不放大小图）；配套 `example_workflows/*_lightx2v_turbo.json` 三份（t2v/i2v/ref2v）。
- **评级**：采用（LoRA 来源）。

### ssssssanjiu/minimax-h3-turbo（★97，MIT，2026‑08‑27）

- **定位**：零自定义节点的 `fl2v-8step.json` / `ref2v-4step.json`（+KJNodes 版），附本地/云部署指南。要点与本簇一致：cu130 是最大头（int8 convrot 硬件反量化，3–5×）；Sage 必须 2.x wheel；`--use-sage-attention` 与 KJ patch 节点二选一（重复 patch）；TE‑Speed 不开；RAM ≥32 GB 硬门槛（实测 44 GB）；pruned vs 完整 int8：真人/文字选完整；nvfp4 TE 在非 Blackwell 上是模拟运算但只跑一次可忽略。
- **评级**：采用（作为规则来源，工作流本身低于用户现有）。

### RH-RunningHub/MiniMax-H3-MultiGPU-Lightning（★123，Apache‑2.0，2026‑09‑26）

- 8× RTX 6000D + SGLang `multimodal_gen`，4 步私有蒸馏 + SageAttention2 + Cache‑DiT + torch.compile：5 s 1344×768 348.8 s → 28.7 s。RH 加速权重**未公开**，仓库内嵌 sglang 快照（676 KB 文件树）。
- **评级**：跳过（单卡无关）。

### alesha-pro/tools（★697，MIT，2026‑09‑28）— 只读 H3 基准

- 4×3090（220–320 W，PCIe 3.0，Ubuntu）。单卡等效工作流 1344×768×124f：Turbo 4 步 `low_vram on` 采样 2:42 / 全程 3:45；`low_vram off` 3:37 / 7:07；base 20 步 10:14 / 11:08；pruned int8 87.4 s/步（320 W）。多卡 Raylight 3.12×（15 s 片 19 min → 6:41）。实用贴士：功耗墙 220→320 W 同任务 220 s → 170 s；32 GB RAM 需 `--disable-pinned-memory`；TE 放 CPU 约 27 s/次。
- **评级**：参考（规则来源）。

### OpenVDN/vdn-minimax-h3（★672，Apache 代码 / MiniMax 社区许可权重，2026‑10‑05）— 只读 README

- 机制：滑窗 softmax（chunk 5、radius 1、锚帧）+ 帧级线性 delta 分支 + 两个 LoRA，冻结底模上训练；DMD 阶段对齐 larryvrh Turbo。单 H200 768p×14.4 s：dense 32.7 s/NFE → VDN fp8 11.2 s/NFE（2.9×），8 NFE 90.5 s；24 GB 卡用 diffusers 块级 offload 345 帧峰值 22 GB（fp8 20 GB）。权重仓 82 GB，只需 `stage-dmd-step-250/`（5.1 GB）。
- **评级**：经 ComfyUI 节点间接评估（见 VDN‑H3）。

### FlashML-org/FreeVideo（★2834，Apache‑2.0，2026‑11‑07）— 只读 8 GB 路径与 VDN 用法

- 基于 VDN‑H3 8 步模型的自适应执行引擎（ComfyUI 插件 + 启动器）：按实时显存/内存决定 50 块驻留数、pinned 预取、磁盘流式、int8（GeForce）或 FP8、attention 探测顺序 **SageAttention2 → flash → cuDNN → FA2 → FA4**、头分组 16/8/4、TE 独立进程。质量档（`web/sampling_effort.js`）：**Light/Medium = 两段式 8 步 + 3 步精修**（学习型 latent 放大 2× / 1.5×），**High 16 步、Max 20 步 + `easycache-av`**。
- **数字（Windows，1344×768×10 s 两段式）**：5090 32 GB 122 s；5060Ti 16 GB 486 s；4060Ti 16 GB 558 s；社区 3090 24 GB Light 704 s。
- **对 4090 的价值**：不能直接套进用户的 ref2va int8_convrot + Turbo 链（底模换成 VDN）；但其「半分辨率 8 步 → latent 放大 → 全分辨率 3 步」配方与 Spark‑H3 的 LBH 两段式一致，是精修档二采的现成参数。
- **评级**：观望（参考两段式配方）。

### neng320/minimax-h3-local-deployment（★95，无许可证，2026‑08‑12）

- 自 docs/11 引用的 2026‑08‑08 数据后无新内容（README/qa‑benchmarks 日期未变）。
- **评级**：已采用，无需补充。

### pottokao/ComfyUI-GGUF-Qwen3VL-TE（不在 relevant.json；实际仓库 pottokao-dotcom/ComfyUI-GGUF-Qwen3VL-TE，★22，2026‑10‑17）

- 是 city96/ComfyUI‑GGUF 的补丁，修 Qwen‑Image‑2.1 / Ideogram 4 / FLUX.3 的 Qwen3‑VL GGUF 文本编码器 12288 形状错误；README 原文：「其它用 Qwen3‑VL GGUF 的模型（如 MiniMax‑H3 文本编码器）加载行为与没装一样」。wildminder 索引里另有 `pottokao/H3-RotNVFP4-ComfyUI-Loader`（旋转 NVFP4 FastH3 12.5 GB），现已 404，且 NVFP4 在 4090 上为模拟运算。
- **评级**：跳过（与 H3 无关）。

---

## 4090 24GB 推荐组合

### 草稿档（768P/544p 抽卡，5–10 s，目标 ≤2–3 分钟）
1. 底模 `minimax_h3_ref2va_int8_convrot`（或 fl2va），`LoraLoaderModelOnly` lightx2v Turbo：Ref2V **8 步 v1.1_768p**（抽卡可降 4 步 v1.0_768p），强度 1.0，CFG 1.0，Euler + simple，SigmaShift 按 docs/11（FL2V 768p 版 6/3，Ref2V 12/3）。
2. 注意力：KJ `Patch Sage Attention`(auto) → KJ `MiniMaxH3MemoryEfficientSageAttentionPatch`；**不接** KJ `MiniMaxLowVRAMAttention`。
3. 分辨率 864×480 或 960×544 先抽卡；换 seed 抽卡（同 seed 会命中 ComfyUI 结果缓存）。
4. 升级 ComfyUI ≥0.38 后，可选加 **Veda**（R2VA 预测器）放在 LoRA/Sage 之后、Guider 之前，用于 1344×768×10 s 的抽卡；同 seed Ctrl+B 旁路对比后再默认开。
5. 激进替代（仅 Ref2VA、愿放弃 Sage）：Kablex `Ref2VAVSAGatePatch`(sparsity 0.7) + ref2v 4 步 v0.1，1344×768×5 s ≈ 72 s。

### 精修档（1344×768，中选段重跑/二采）
1. 路线 A（默认）：Turbo **8 步 v1.1** + Sage，其余加速全关；`low_vram` 合并/bypass 两档各跑一次定默认（alesha‑pro 反例）。
2. 路线 B（画质优先）：无 Turbo 20 步 res_multistep/simple + Sage，再二选一叠加：Spectrum 默认参数（≈11 实际 + 9 预测）或 FirstBlockCache `H3 Fast`（−30%）；同 seed 与无缓存对比口型、参考保持。
3. 路线 C（≥10 s 长段）：升级 ComfyUI 0.38.x 后，Spark‑H3 `fidelity`、`topk_ratio 0.2`、Ref2VA 有参考视频时 `sparse_scope joint-video`、`dense_backend sage`；或 Veda。两者只选一个，且不与核心 `Block Sparse Attention` 同链。
4. 二采配方（来自 Spark‑H3 LBH 示例 / FreeVideo Light）：第一段 0.2–0.33 MP 4–8 步 → LBH latent 放大 → 第二段 0.98 MP 3 步，sigmas `0.9035, 0.6316, 0.3158, 0`，第二段才开稀疏注意力。
5. 写实对照：alibaba‑pai PDD Ref2VA 8 步（Euler、shift 12/3、SIGMAS 来自节点）替换 Turbo 做 A/B；漫剧风格保持 Turbo。

### 明确不要叠加
- 任何两种蒸馏：lightx2v Turbo × PDD × HyperFlow × VDN turbo adapter × Larryvrh（PDD‑Acc、VDN‑H3、HyperFlow README 一致）。
- Spectrum × EasyCache/LazyCache/T8 BlockCache/FirstBlockCache；FirstBlockCache × T8 BlockCache × EasyCache × CacheDiT；任何 BlockCache × 核心 Block Sparse Attention（T8 源码直接拒绝）。
- Kablex Ref2VA‑VSA × SageAttention/Sol/任何 `optimized_attention_override`（抛错）。
- VDN‑H3 × Sol 调度补丁；VDN‑H3 × 社区 Turbo LoRA；VDN‑H3 `fast_kernels` 开启。
- Veda × 核心 `Model Sparse Attention`；Veda 放在 KJ MemEff Sage **之前**（会收不到调用）。
- Spark‑H3 × 第二个 attention 补丁（Sol/SLA/Veda）；Spark‑H3 与 ComfyUI 0.37/0.41。
- KJ `MiniMaxLowVRAMAttention` × Sage（本地实测极慢）；KJ LowVRAM × sol‑attn `Fused Modulation`。
- `--use-sage-attention` 启动参数 × KJ `Patch Sage Attention` 节点（重复 patch）。
- PDD × er_sde/res_multistep/dpmpp（越网格报错）；PDD × 任何步缓存；PDD × shift ≠ 12/3。
- 8 步 Turbo × Spectrum（作者不建议）；8 步 Turbo × 任何 BlockCache（无命中）；8 步 Turbo + int8 × TE‑Speed（失真）。
- 同一张卡上 ClipProj all‑in‑one Loader（钉住 TE）× 大分辨率采样。

---

## 可写进 skill 的规则

1. 基线链固定为 `UNETLoader(int8_convrot)` → `LoraLoaderModelOnly(lightx2v *_turbo_8step_v1.1*_comfyui_bf16, 1.0)` → `PatchSageAttentionKJ(auto)` → `MiniMaxH3MemoryEfficientSageAttentionPatch` → `MiniMaxH3SigmaShift` → Guider；加速节点一律在此基线上同 seed A/B 后才默认开启。（docs/11、ssssssanjiu）
2. 绝不同时挂两种蒸馏（Turbo / PDD‑Acc / HyperFlow / VDN turbo adapter / Larryvrh），换蒸馏时先移除旧 LoRA 节点。（Jalen‑Brunson PDD‑Acc、Saganaki22 VDN‑H3、Saganaki22 Hyperflow）
3. 不要把 KJ `MiniMaxLowVRAMAttention` 与 Sage 补丁同开；需要省显存时改用 KJ/`MiniMaxChunkFeedForward` 或 star7 分块（`chunk_tokens 8192 / mlp 4096 / qkv 4096`，attention_backend=`existing`）。（docs/11 实测、star7code）
4. 启动参数 `--use-sage-attention` 与 KJ `Patch Sage Attention` 节点只用一个；Sage 必须 2.x wheel。（ssssssanjiu）
5. 20 步精修链才允许挂 Spectrum（`SpectrumApplyMiniMaxH3` 默认参数，放在 SigmaShift 之后、Guider 之前，`history_storage=system_ram`）；8 步 Turbo 链不挂。（xmarre Spectrum）
6. Spectrum 与 EasyCache/LazyCache/任何 BlockCache 互斥；同一模型分支只能有一个「跳步/缓存」节点。（xmarre Spectrum、T8mars、duckyshell）
7. 20 步链若选 FirstBlockCache，用 `ApplyMiniMaxH3FirstBlockCache mode="H3 Fast"`（阈值 0.10、窗口 0.10–0.95、连续命中 ≤2），控制台 hit 数为 0 时直接移除；4–8 步链不挂。（duckyshell）
8. 不安装 lihaoyun6/ComfyUI-MiniMaxH3-Cache、HELPMEEADICE/TE-Speed-OSS、tl2012tl/TE-Speed（分别为替换核心 `_forward`、patch 核心 `model.py`、闭源 .pyd）；若已装 TE‑Speed OSS 先 `python patch_model.py --revert`。（三仓库源码）
9. 用 Kablex `Ref2VAVSAGatePatch` 时，模型分支上不得有任何 Sage/Sol/attention override 节点；链路为 ref2va int8 → ref2v Turbo 4 步 v0.1 → VSA(gate=`fasth3_vsa_gate.safetensors`, sparsity 0.5–0.75) → SigmaShift 12/3 → Euler simple 4 步；需 comfy‑kitchen CUDA `sol_attn`。（Kablex）
10. 装 Veda 前先把 ComfyUI 升到 ≥0.38.0；`VedaSparseAttention` 放在 LoRA 与所有 Sage 补丁之后、Guider 之前；R2VA 用 `minimax_h3_r2va_veda_preview_fp8`，FL2VA 用 `minimax_h3_t2va_veda_8nfe_600step_preview_fp8`（放 `models/veda/`）；不与核心 `Model Sparse Attention` 同链；首次用 Ctrl+B 旁路同 seed 对比。（veda‑sparse）
11. Veda 预测器只保证 1344×768 / 768×1344 / 768×768 / 1024×768 × 5/10/14 s × 8 步 Turbo；其它分辨率/步数必须 A/B。（veda‑sparse）
12. 装 Spark‑H3 只用官方 Windows SM89 CUDA‑13 ZIP（`spark-h3-kitchen 0.2.37`），ComfyUI 需在 0.38.x–0.40.x 或 0.42.x–0.44.x；节点预设 `fidelity`、`topk_ratio 0.2`，Ref2VA 带参考视频时 `sparse_scope=joint-video`，`dense_backend=sage`；一个模型只挂一个 attention 补丁。（zechengtang Spark‑H3）
13. 5 s 以内短片不要为稀疏注意力折腾：Spark 在 3090 上 Turbo 8 步 1344×768×5 s 与核心 Sol 同速（158 vs 152 s），Sol 比 Sage 整模只快 ~10%；稀疏注意力留给 ≥10 s 或 20 步。（Spark‑H3 docs、Saganaki22 sol‑attn、docs/11）
14. VDN‑H3 只在做 ≥10 s 单段且显存充足时评估；`lora_mode=merge`、`apply_turbo_adapter=ON` 配 8 步 er_sde/beta、`branch_weights=auto`、`fast_kernels=off`、移除社区 Turbo LoRA、不接 Sol 调度补丁、解码用 `VAEDecodeTiled`；分支用 drbaph int8_convrot 版（2.2 GB）。（Saganaki22 VDN‑H3）
15. PDD‑Acc 作写实 A/B 时：`MiniMaxH3PDDAccApply(nfe=8, lora 1.0, head 1.0)`，SIGMAS 输出接 `SamplerCustomAdvanced`，Euler、CFG 1.0、SigmaShift 恰好 12/3，FL2VA 文件配 fl2va 底模、Ref2VA 配 ref2va；禁止 er_sde/res_multistep 与任何缓存。（Jalen‑Brunson）
16. 漫剧/插画风格不用 PDD 4 NFE（压平纹理），用 Turbo v4‑600 或 lightx2v 8 步。（官方索引现场笔记）
17. HyperFlow 只在完整底模（含 `time_embedder`）上按配方用：`ApplyHyperFlow(bypass, strength 1.0)` 的 SIGMAS 接采样器，Euler；pruned 底模必须开 `experimental_curve_refit` 否则脱离配方；不与 Turbo 同挂。（Saganaki22 Hyperflow）
18. Turbo LoRA 的 `low_vram`（合并）与 bypass 在本机各跑一次 1344×768×124f 同 seed 记录时间与近景皮肤，再定默认；不要照抄「bypass 最锐」。（alesha‑pro vs Larryvrh）
19. 二采精修用「低分辨率 4–8 步 → LBH latent 放大 → 全分辨率 3 步，sigmas 0.9035 / 0.6316 / 0.3158 / 0」，稀疏注意力只开在第二段。（Spark‑H3 LBH 示例、FreeVideo Light 档）
20. 不为 24 GB 卡装 W4A4‑VSA；需要极稀疏时直接用核心 `Block Sparse Attention` SLA 5%（作者自测与 W4A4+VSA 同速）。（sepiablue）
21. 不装 xmarre/ComfyUI-Sol-H3（Windows 空转、仅 SM120）。（xmarre Sol‑H3 README）
22. ClipProj 只在内存紧张或提示词快速迭代时用 stock `Load CLIP(type=krea2)` → `ClipProjApply(mmh3-4b-ClipProj-v3.1)`；精修与最终渲染用 32B nvfp4；单卡绝不用 `ClipProj Loader (all-in-one)`。（nicolab28）
23. Ref2VA 精修画质 A/B 可用 `MiniMaxH3HybridLoader(base=fl2va int8, overlay=ref2va int8, block_range_adaln 25–49)`；它不省时间，且与 ref2v Turbo LoRA 的匹配需自测。（scottmudge）
24. 显卡功耗墙拉满（4090 450 W）、RAM 32 GB 时加 `--disable-pinned-memory`、TE 可放 CPU（约 +27 s/次）。（alesha‑pro）
25. 冷启动（Triton/Sage JIT + 模型载入）8–14 分钟属正常，计时从第 2 条起算；任何稀疏/Sol 节点换分辨率或时长都要重新 JIT 一次。（ssssssanjiu、Saganaki22 sol‑attn）
26. 不装 pottokao-dotcom/ComfyUI-GGUF-Qwen3VL-TE（Qwen‑Image 用，对 H3 无效）。（其 README）
27. 升级 ComfyUI 前检查：Spark‑H3 跳过 0.41；Spectrum 需 ≥`e377e263`；Veda ≥0.38；T8 BlockCache ≥0.30；HyperFlow 在 0.37 有「Model Initializing」卡住报告（诊断 `--disable-fast-disk`）。（各仓库 pyproject/README）

## 未覆盖/未读完

- `pottokao/H3-RotNVFP4-ComfyUI-Loader`（索引有、仓库 404；NVFP4 在 4090 为模拟运算，价值低）。
- `kijai/ComfyUI-SolAttn_triton`（官方索引 ★266，与 Saganaki22 sol‑attn 同类，已被核心 BSA 取代，未精读）。
- `Speach1sdef178/ComfyUI-VDN-H3-24GB`（VDN 24 GB 重卸载分支）。
- xmarre 系列伴侣：`ComfyUI-VDN-H3-Plus`、`Flow-Aligned Regenerate`、`H3 Continuum-Plus`、`Untwisting-RoPE`、`DiffAid-Patches`（Spectrum/Sol‑H3 README 反复引用，属长视频/质量簇）。
- `zechengtang/VPack`（Ref2VA 参考视频压缩，推荐档 2/5）、`sepiablue-ai/ComfyUI-H3-X2-Stream`（544×960 生成 → 1088×1920 输出 68.9 s）。
- `lightx2v/Minimax-h3-Turbo-SLA` LoRA（star7 建议配 SLA 使用）、FastVideo FastH3 8‑step V2（ComfyUI 单文件 int8 20.6 GB）、`Nynxz/ComfyUI-FastH3Patcher`、PTD（vita‑epfl）、DMAD 4/8 步 LoRA——均为「换蒸馏」候选，未逐一精读。
- `Mozer/ComfyUI-MiniMax-H3-MotionCache-FastVAE`（W4A4‑VSA 依赖的快速 VAE 解码）、`LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler`（归放大簇）。
- RH MultiGPU 仓库内嵌的 sglang 快照与 alesha‑pro 的 Raylight 多卡工作流（单卡无关，未读）。
