# 随 skill 附带的工作流（API 格式，直接交给 `comfy_submit.py`）

> **怎么来的**：用 ComfyUI 0.37.2 自带的官方模板（模板包 0.11.69，就是你模板面板里的那几份），在真实的 0.37.2 前端里执行「导出（API）」，再按下表改成本流程的设置。
> **验证到哪一步**（2026-11-23）：每个文件、每种用法都提交给了一台真实的 ComfyUI 0.37.2（装了当天的 KJNodes、ResCascade、LBH 放大节点，模型文件用空的占位文件），**服务器自己的校验器全部接受**——节点存在、输入名和类型对得上、参考图 / 音色 / 首尾帧 / 关键帧的接法合法。
> **执行到哪一步**：那台机器没有显卡，装不下真模型。后来造了一套结构相同、宽度很小的**随机权重** H3（文件格式和发布的一致，VAE 与 LBH 放大器用真实权重），把这些工作流不改一个字地从文本编码执行到了存片——草稿、关 Turbo 的 20 步、`--anchor`、精修、分块精修、`--keep-latent` / `--from-latent`、首帧 / 首尾帧 / 纯文字、首帧段的精修（细目见「已知的边界」；完整记录在 GitHub 仓库的 `skills/minimax-h3-comfyui-short-drama/evals/results/iteration-13-miniature-model-and-retest-4.md`，安装包里不带 `evals/`）。随机权重出的画面是噪声：这证明的是**接线在运行时成立**。
> **没有验证的**：真模型下的画面、口型、耗时、显存，以及 Sage 的两个节点（那台机器没有 `sageattention` 包）。这些要在你的机器上第一次跑时确认（`../first-run-checklist.md`）。

## 文件

| 文件 | 用途 | 改自 | 需要的自定义节点 |
|------|------|------|------------------|
| `smoke_test_prompt.txt` | **H3 冒烟测试用的提示词**（5 s、纯文字、一句中文台词）：配 `h3_ref2va.api.json` 在没有任何素材时确认 H3 能出片——命令见下面第 0b 条 | 用本 skill 的生成器出的 | — |
| `selftest_no_model.api.json` | **连通测试**：不用任何模型，几秒出一个 2 s 的小视频，确认脚本能连上 ComfyUI、上传文件、取回结果（脚本默认每 20 s 查一次进度，测试时加 `--poll 2`） | 手写 | 无 |
| `h3_ref2va.api.json` | Ref2VA 草稿 / 定稿：1344×768，Turbo 8 步（`euler` / `simple`）；关掉开关就是 20 步不挂 LoRA | `video_minimax_h3_r2v` | 无 |
| `h3_ref2va_sage.api.json` | 同上，模型链上多 KJNodes 的两个 Sage 节点 | 同上 | KJNodes（+ `sageattention` 包） |
| `h3_ref2va_refine.api.json` | 精修：接 `H3 Hires Fix` 二采到 1920×1088。默认加 `--from-latent` 从草稿存下的一采 latent 开始；没存 latent 时改给 `--seed`，文件里带着的一采按同 seed 原样重跑 | 同上 | ResCascade、LBH 放大节点 |
| `h3_ref2va_sage_refine.api.json` | 草稿用的是 `_sage` 版时的精修（一采要和草稿走同一条注意力路径才是同一条片段） | 同上 | 以上三个 |
| `h3_ref2va_refine_split.api.json` / `h3_ref2va_sage_refine_split.api.json` | **精修的备用方案**——上面两份在二采时显存不够才用：先用 LBH 放大 latent，再用 LBH 节点包的 `MMH3 Split Upscale` 把二采按时间切成 73 帧一块（重叠 22 帧）分块做，音频同样钉死；二采的 sigma 是 `0.45, 0.225, 0`，和 `H3 Hires Fix` 的 `steps_override 2` 相同 | 同上 | ResCascade、LBH 放大节点（带 Sage 的再加 KJNodes） |
| `h3_fl2va.api.json` | `i2va` / `fl2va` / `t2va` 段：FL2VA 权重，1344×768，Turbo 8 步（v1.0 的 768p 版 LoRA + shift 6 / 3；shift 节点只在 LoRA 那条分支上，关掉 Turbo 就回到模型默认的 12 / 3） | `video_minimax_h3_i2v` | 无 |
| `h3_fl2va_sage.api.json` | 同上 + Sage | 同上 | KJNodes |
| `h3_fl2va_refine.api.json` / `h3_fl2va_sage_refine.api.json` | `i2va` / `fl2va` / `t2va` 段的精修：同样的 `H3 Hires Fix` 二采到 1920×1088，用法和 Ref2VA 的精修一样（`--from-latent` 或 `--seed`）。首帧、尾帧是按一采的尺寸编码的，节点在二采时把它们从条件里去掉（放大的 latent 里已经有了），所以不用另建一个大尺寸的条件节点 | 同上 | ResCascade、LBH 放大节点（带 Sage 的再加 KJNodes） |
| `h3_fl2va_refine_split.api.json` / `h3_fl2va_sage_refine_split.api.json` | 上一行在二采时显存不够才用的分块版，和 Ref2VA 的分块版同一种接法 | 同上 | 同上 |
| `qwen21_t2i.api.json` | 文生图（定妆照、场景母版、道具）：Qwen-Image 2.1，25 步 CFG 1。**许可是研究用途，不能用在营利的项目里** | `image_qwen_image_2_1_t2i` | 无 |
| `zimage_turbo_t2i.api.json` | 同样三类图的**可商用**替代：Z-Image-Turbo（Apache-2.0），`ModelSamplingAuraFlow` 3、`res_multistep` / `simple`、8 步、CFG 1——官方模板原样，只把提示词清空、种子固定。`plan_stills.py --t2i zimage` 出的命令用它。只通过了服务器校验，没有出过图；模板的尺寸是 1024×1024，清单里母版排 2048×1152、道具 1024×1024，更大的尺寸没试过 | `image_z_image_turbo_int8` | 无 |
| `qwen_edit2511_1ref / 2ref / 3ref.api.json` | 编辑出图（派生视图、逐镜首帧）：Qwen-Image-Edit-2511 int8，40 步 CFG 4，**输出尺寸固定为 1344×768**（不跟着第一张图走），1 / 2 / 3 张输入图 | `image_qwen_image_edit_2511_int8` | 无 |

和官方模板不一样的地方：尺寸、帧数写成了数字（模板用选择器和公式算）；模板自带的示例图、示例提示词去掉了；H3 的 LoRA 换成 8 步 768p 版、开关默认打开、采样器换成 `euler`；编辑模板的 Lightning 4 步分支去掉了（所以不用下那个 LoRA），latent 从「取第一张图的尺寸」换成固定的 `EmptySD3LatentImage`。

## 要下载的文件（HuggingFace；括号里是放进 `ComfyUI/models/` 的哪个子目录）

先看全局：ComfyUI 开着时跑 `python <skill>/scripts/check_setup.py`，它问服务器本身，逐个工作流标出 READY 还是缺什么（节点包、模型文件）。再看文件：不用照着表手抄，`python <skill>/scripts/fetch_models.py --comfyui <ComfyUI 目录>` 会逐个告诉你哪个在、哪个缺、哪个没下全、哪个放错了目录（只检查，不改东西）；加 `--download` 就把缺的下到正确的目录里，断了重跑会接着下，下完校验 SHA-256。默认查 `ref2va`、`stills`、`refine` 三组，要 FL2VA 加 `--sets ref2va stills refine fl2va`；`stills` 是 `t2i`（Qwen-Image 2.1，研究许可）加 `edit`（Edit-2511，Apache-2.0）两组的合称；做营利项目的把 `t2i` 换成 `zimage`：`--sets ref2va edit zimage refine`，这样不会把用不了的 Qwen-Image 2.1（17.3 GB）也下下来。清单本身是同目录的 `models.json`。

| 用途 | 文件 | 大小 |
|------|------|------|
| H3 共用 | `Comfy-Org/MiniMax-H3`：`text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`（`text_encoders/`） | 15.7 GB |
| | `vae/minimax_h3_video_vae_int8_convrot.safetensors`、`vae/minimax_h3_audio_vae_fp32.safetensors`（`vae/`） | 2.8 + 0.6 GB |
| Ref2VA | `diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors`（`diffusion_models/`） | 21.0 GB |
| | `lightx2v/Minimax-h3-Turbo`：`minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors`（`loras/`） | 2.0 GB |
| FL2VA（用到 `i2va` / `fl2va` / `t2va` 段才下） | `Comfy-Org/MiniMax-H3`：`diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors`（`diffusion_models/`） | 21.0 GB |
| | `lightx2v/Minimax-h3-Turbo`：`minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors`（`loras/`） | 2.0 GB |
| 精修 | `LBH-123-AI/Minimax_h3_latent_Upscaler`：`minimax_h3_latent_upscaler_3d_conv_v1/minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors`（直接放 `latent_upscale_models/`，不带那层子文件夹） | 0.7 GB |
| 文生图 | `Comfy-Org/Qwen-Image-2.1`：`diffusion_models/qwen_image_2.1_int8_convrot.safetensors`（`diffusion_models/`）、`text_encoders/qwen3vl_8b_int8_convrot.safetensors`（`text_encoders/`）、`vae/qwen_image_2.1_vae_bf16.safetensors`（`vae/`） | 7.3 + 9.4 + 0.7 GB |
| 文生图（可商用的替代） | `Comfy-Org/Z-Image-Turbo`：`split_files/diffusion_models/z_image_turbo_int8_convrot.safetensors`（`diffusion_models/`）、`split_files/text_encoders/qwen_3_4b_fp8_mixed.safetensors`（`text_encoders/`）、`split_files/vae/ae.safetensors`（`vae/`） | 6.2 + 5.6 + 0.3 GB |
| 编辑出图 | `Comfy-Org/Qwen-Image-Edit`：`split_files/diffusion_models/qwen_image_edit_2511_int8_convrot.safetensors`（`diffusion_models/`） | 20.5 GB |
| | `Comfy-Org/Qwen-Image`：`split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`（`text_encoders/`）、`split_files/vae/qwen_image_vae.safetensors`（`vae/`） | 9.4 + 0.3 GB |

合计：只做 Ref2VA 视频约 **42 GB**；加两套出图模型约 **89 GB**；再加精修约 **90 GB**；还要 FL2VA 的话约 **113 GB**。模型之外再留 20 GB 以上：语音识别模型约 0.5 GB，身份门禁的模型几十 MB，每条 10 s 的草稿连同存下的 latent 约 40–60 MB，ComfyUI 的 `output/` 里还会各留一份。文件名和大小取自 HuggingFace 的文件清单（2026-11-23）。下载页上文件在子目录里，放进 ComfyUI 时只放文件本身；放错目录或带着子目录，预检会报「not offered by the server」并给出最接近的名字。

## 怎么用

所有命令在项目根目录下跑；`<skill>` 是本 skill 的目录，`W=<skill>/assets/workflows`。先 `--dry-run` 看预览，再带 `--confirm <批次号>` 提交。

`$W` 只是为了少打字：bash 里先 `W=<skill>/assets/workflows`；PowerShell 里先 `$W = "<skill>\assets\workflows"`，后面同样写 `$W\h3_ref2va.api.json`；cmd 没有这种写法，直接写全路径。Windows 上解释器叫 `python`（不是 `python3`）。

```
# 0. 连通测试（不用模型）
python <skill>/scripts/comfy_submit.py $W/selftest_no_model.api.json --set 1.image=@任意一张图.png --out takes/selftest --poll 2

# 0b. H3 冒烟测试（不用素材；864×480 × 5 s × 8 步，画面好坏不算数，只看能不能出片、多久）
python <skill>/scripts/comfy_submit.py $W/h3_ref2va.api.json --set 136.prompt=@$W/smoke_test_prompt.txt --set 136.length=124 --set 136.width=864 --set 136.height=480 --out takes/smoke --tag smoke

# 1. 一段 ref2va 草稿，3 个 seed
python <skill>/scripts/comfy_submit.py $W/h3_ref2va_sage.api.json --media prompts/ep01/s01.media.json --batch 3 --seed 1001 --keep-latent --log logs/takes.csv --dry-run

# 2. 同一段，20 步、不挂 Turbo（运镜是主体的镜头，铁律 16）
python <skill>/scripts/comfy_submit.py $W/h3_ref2va_sage.api.json --media prompts/ep01/s01.media.json --seed 1001 --tag s01_full --set 146.value=false --set 123.sampler_name=res_multistep --dry-run

# 3. 精修中选的那条（草稿是 _sage 版就用 _sage_refine）：从草稿存下的 latent 开始，一采不重跑
python <skill>/scripts/comfy_submit.py $W/h3_ref2va_sage_refine.api.json --media prompts/ep01/s01.media.json --from-latent takes/ep01/s01/s01_1002 --dry-run
#    结果放进 takes/ep01/s01/s01_refine_1002（带二采节点的工作流默认 tag 是 <段>_refine，不和草稿挤一个目录）
#    那条草稿是 --stale-ok 采纳的（它之后提示词改过）：把 --media 换成它自己留的那份 takes/ep01/s01/s01_1002/media.json
#    草稿当时没加 --keep-latent：去掉 --from-latent，改给 --seed 1002（一采按同 seed 重跑一遍）
#    i2va / fl2va / t2va 段同理：草稿 h3_fl2va_sage.api.json，精修 h3_fl2va_sage_refine.api.json

# 4. 定妆照：6 个 seed，1024×1024（改尺寸：--set 459:456.width=1024 --set 459:456.height=1536）
python <skill>/scripts/comfy_submit.py $W/qwen21_t2i.api.json --set 459:452.prompt=@bible/prompts/lin_lan_bust.txt --batch 6 --seed 1 --out bible/candidates/lin_lan --tag bust --dry-run

# 5. 首帧：image1 = 这个人的 face.png，image2 = 场景裁切；输出 1344×768
python <skill>/scripts/comfy_submit.py $W/qwen_edit2511_2ref.api.json --set 41.image=@bible/chars/lin_lan_face.png --set 42.image=@bible/scenes/corridor_s01_crop.png --set 170:151.prompt=@bible/prompts/first_s01.txt --batch 3 --seed 1 --out first/candidates/s01 --tag first --dry-run
```

常用的 `--set`（节点 id 就是官方模板里的 id；带冒号的是模板子图里的节点，照写即可）：

| 工作流 | 要改什么 | 写法 |
|--------|----------|------|
| `h3_ref2va*` | 关 Turbo（20 步） | `--set 146.value=false`（预览会显示实际步数、LoRA 是否还在链上） |
| | 采样器 | `--set 123.sampler_name=res_multistep` |
| | 画布（快速预览） | `--set 136.width=864 --set 136.height=480` |
| | LoRA 强度 | `--set 145.strength_model=0.75` |
| | 参考图按原图大小进模型（20 步定稿时） | `--set 136.ref_image_size=max`（默认 `match`：每张参考图合计约 2,000 token；`max` 多几倍、更慢） |
| `h3_ref2va*_refine`、`h3_fl2va*_refine` | 二采强度 / 尺寸 | `--set 300.sigma_start=0.31`、`--set 300.width=… --set 300.height=…` |
| | 关了 Turbo 之后 | 同时 `--set 300.steps_override=0`（不关时保持 2；预览的 advice 会提醒配错的情况） |
| `h3_ref2va*_refine_split`、`h3_fl2va*_refine_split` | 每块多少帧 / 重叠 | `--set 312.chunk_frames=73 --set 312.temporal_overlap_frames=22`（显存还不够就把每块改小，如 56）；放大后的尺寸在 `--set 310.width=… --set 310.height=…` |
| | 关了 Turbo 之后的二采 sigma | `--set 311.sigmas="0.45, 0.3095, 0.1719, 0.0569, 0.0"`（`H3 Hires Fix` 不挂 Turbo 时用的那 4 步，由 0.37.2 的调度器算出） |
| `h3_fl2va*` | 关 Turbo / 采样器 / 画布 / shift | `--set 105:126.value=false`、`--set 105:17.sampler_name=…`、`--set 105:104.width=…`、`--set 105:200.shift_video=…` |
| `qwen21_t2i` | 提示词 / 尺寸 / 步数 | `--set 459:452.prompt=@文件`、`--set 459:456.width=… .height=…`、`--set 459:458.steps=50` |
| `zimage_turbo_t2i` | 提示词 / 尺寸 / 步数 | `--set 57:27.text=@文件`（这个节点的输入叫 `text`，不是 `prompt`）、`--set 57:13.width=… --set 57:13.height=…`、`--set 57:3.steps=8` |
| `qwen_edit2511_*` | 输入图 | `--set 41.image=@…`（`image1`）、`--set 42.image=@…`（`image2`）、`--set 43.image=@…`（`image3`）；也可以按标题：`--set-title image1.image=@…` |
| | 提示词 / 输出尺寸 / 步数 | `--set 170:151.prompt=@文件`、`--set 170:300.width=… --set 170:300.height=…`、`--set 170:169.steps=20` |

这些工作流里要你给的东西出厂时是空的：H3 和出图的提示词是空字符串，编辑工作流的图片位写着 `(not set)`。漏给任何一个，预检会直接拦下并写出该补的那条 `--set`（ComfyUI 自己不会拦——空提示词、拼错的输入名它都照收）；`--set` 写了节点没有的输入名也会被拦，并列出这个节点真正的输入名。出图的预览会列出尺寸、每张输入图和提示词的开头。

种子不用 `--set`：`--seed N --batch K` 会把工作流里所有种子一起设成 N、N+1…（精修工作流里一采和 `H3 Hires Fix` 的种子是同一个数）。提示词、帧数、参考图、音色、首尾帧由 `--media` 接，不用手改。

## 想在界面里看或改这些工作流

把 `.api.json` 文件直接拖进 ComfyUI 窗口就能打开（在真实的 0.37.2 前端里试过，节点全部认得；位置是自动排的，不好看但能用）。在界面里改过之后，用菜单「工作流 → 导出（API）」另存一份到项目的 `workflows/` 下，再把那个文件交给脚本。

## 不想用附带的，自己从模板导出也行

打开模板 → 菜单「工作流 → 导出（API）」，原样导出的文件脚本就能读：模板里用开关选步数和 LoRA、用选择器算分辨率，预览会把开关和选择器算出来的实际值显示出来，并告诉你翻开关该 `--set` 哪个节点（例如 `--set 146.value=true --set 144.value=8 --set 145.lora_name=minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors --set 136.width=1344 --set 136.height=768`）。模板自带的示例图、算帧数的公式在 `--media` 接线之后不再连着输出，ComfyUI 不会管它们。

## 已知的边界

- **用微型随机权重模型执行过的**（真实的 0.37.2、CPU、448×256 或 320×192、真实的 VAE 和 LBH 权重；控制台的原话抄在括号里）：冒烟测试命令；`--media` 接 5 张参考图加音色；关 Turbo 的 20 步；`--anchor`（首帧钉第 0 帧、第二镜关键帧钉第 96 帧，243 帧）；`h3_ref2va_refine`（`[H3HiresFix] (16, 28) -> (22, 40), sigmas [0.45, 0.225, 0.0]`）；`h3_ref2va_refine_split`（124 帧分两块）；`--keep-latent` 再 `--from-latent`；`h3_fl2va` 的首尾帧、首帧、纯文字三种；`h3_fl2va_refine`（`[H3HiresFix] dropped 2 pass-1 keyframe(s) (start/end image) sized for pass 1`）。每条都出了尺寸、帧数、帧率正确、带 32 kHz 立体声的 mp4。
- **仍然没有执行过的**：Sage 的两个节点（带 `_sage` 的六个文件只通过了服务器校验）；N 卡上默认的 DynamicVRAM 加载路径；真权重下的一切画面与耗时。第一次用时照 `../first-run-checklist.md` 各验一次。
- 用真实权重实际跑过的只有不需要 33B 底模的那几段（真实的 0.37.2，CPU，小尺寸）：H3 的音画 latent 解码成 24 fps 视频 + 32 kHz 立体声；一采 latent 的拆分、保存、取回、传回、读入、拼回（`--keep-latent` / `--from-latent`）；LBH 放大器；音色样本过音频 VAE；1344×768 的空潜空间过 Qwen-Image VAE 解码出来就是 1344×768；脚本接好的参考图、音色、首帧和关键帧过 H3 的参考节点与关键帧节点（文本编码器用替身），顺序、尺寸、帧号都对。
- Sage 版需要 `sageattention` 包装在 ComfyUI 自己的 Python 里（`references/local-stack-and-acceleration.md` §0b）；没装时节点能加载、预检也通过，运行到第一个 Sage 节点才报 `ModuleNotFoundError: No module named 'sageattention'`（实际跑出来的原话；脚本会在后面接一句怎么办），版本太旧时报 `sageattention is not new enough version …`——先用不带 `_sage` 的版本确认其余都通。两个 Sage 节点里接管 H3 自注意力的是第二个（`MiniMax H3 Mem Eff Sage Attention Patch`：替换 50 个块的注意力，自述是实验性的、用途是降低显存峰值）；第一个按文档里的基线链保留。
- 这些文件对应 ComfyUI 0.37.2 的节点定义。升级 ComfyUI 之后如果预检报输入缺失或多余，按上一节从新模板重新导出一份。
