# 随 skill 附带的工作流（API 格式，直接交给 `comfy_submit.py`）

> **怎么来的**：用 ComfyUI 0.37.2 自带的官方模板（模板包 0.11.69，就是你模板面板里的那几份），在真实的 0.37.2 前端里执行「导出（API）」，再按下表改成本流程的设置。
> **验证到哪一步**（2026-11-23）：每个文件、每种用法都提交给了一台真实的 ComfyUI 0.37.2（装了当天的 KJNodes、ResCascade、LBH 放大节点，模型文件用空的占位文件），**服务器自己的校验器全部接受**——节点存在、输入名和类型对得上、参考图 / 音色 / 首尾帧 / 关键帧的接法合法。
> **没有验证的**：那台机器没有显卡也没有真模型，**没有采样过一帧**。画面、耗时、显存要在你的机器上第一次跑时确认（`../first-run-checklist.md`）。

## 文件

| 文件 | 用途 | 改自 | 需要的自定义节点 |
|------|------|------|------------------|
| `selftest_no_model.api.json` | **连通测试**：不用任何模型，几秒出一个 2 s 的小视频，确认脚本能连上 ComfyUI、上传文件、取回结果（脚本默认每 20 s 查一次进度，测试时加 `--poll 2`） | 手写 | 无 |
| `h3_ref2va.api.json` | Ref2VA 草稿 / 定稿：1344×768，Turbo 8 步（`euler` / `simple`）；关掉开关就是 20 步不挂 LoRA | `video_minimax_h3_r2v` | 无 |
| `h3_ref2va_sage.api.json` | 同上，模型链上多 KJNodes 的两个 Sage 节点 | 同上 | KJNodes（+ `sageattention` 包） |
| `h3_ref2va_refine.api.json` | 精修：一采按同 seed 原样重跑，再接 `H3 Hires Fix` 到 1920×1088 | 同上 | ResCascade、LBH 放大节点 |
| `h3_ref2va_sage_refine.api.json` | 草稿用的是 `_sage` 版时的精修（一采要和草稿走同一条注意力路径才是同一条片段） | 同上 | 以上三个 |
| `h3_fl2va.api.json` | `i2va` / `fl2va` / `t2va` 段：FL2VA 权重，1344×768，Turbo 8 步 | `video_minimax_h3_i2v` | 无 |
| `h3_fl2va_sage.api.json` | 同上 + Sage | 同上 | KJNodes |
| `qwen21_t2i.api.json` | 文生图（定妆照、场景母版、道具）：Qwen-Image 2.1，25 步 CFG 1 | `image_qwen_image_2_1_t2i` | 无 |
| `qwen_edit2511_1ref / 2ref / 3ref.api.json` | 编辑出图（派生视图、逐镜首帧）：Qwen-Image-Edit-2511 int8，40 步 CFG 4，**输出尺寸固定为 1344×768**（不跟着第一张图走），1 / 2 / 3 张输入图 | `image_qwen_image_edit_2511_int8` | 无 |

和官方模板不一样的地方：尺寸、帧数写成了数字（模板用选择器和公式算）；模板自带的示例图、示例提示词去掉了；H3 的 LoRA 换成 8 步 768p 版、开关默认打开、采样器换成 `euler`；编辑模板的 Lightning 4 步分支去掉了（所以不用下那个 LoRA），latent 从「取第一张图的尺寸」换成固定的 `EmptySD3LatentImage`。

## 要下载的文件（HuggingFace；括号里是放进 `ComfyUI/models/` 的哪个子目录）

| 用途 | 文件 | 大小 |
|------|------|------|
| H3 共用 | `Comfy-Org/MiniMax-H3`：`text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`（`text_encoders/`） | 15.7 GB |
| | `vae/minimax_h3_video_vae_int8_convrot.safetensors`、`vae/minimax_h3_audio_vae_fp32.safetensors`（`vae/`） | 2.8 + 0.6 GB |
| Ref2VA | `diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors`（`diffusion_models/`） | 21.0 GB |
| | `lightx2v/Minimax-h3-Turbo`：`minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors`（`loras/`） | 2.0 GB |
| FL2VA（用到 `i2va` / `fl2va` / `t2va` 段才下） | `Comfy-Org/MiniMax-H3`：`diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors`（`diffusion_models/`） | 21.0 GB |
| | `lightx2v/Minimax-h3-Turbo`：`minimax_h3_fl2v_turbo_8step_v1.2_768p_comfyui_bf16.safetensors`（`loras/`） | 2.1 GB |
| 精修 | `LBH-123-AI/Minimax_h3_latent_Upscaler`：`minimax_h3_latent_upscaler_3d_conv_v1/minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors`（直接放 `latent_upscale_models/`，不带那层子文件夹） | 0.7 GB |
| 文生图 | `Comfy-Org/Qwen-Image-2.1`：`diffusion_models/qwen_image_2.1_int8_convrot.safetensors`（`diffusion_models/`）、`text_encoders/qwen3vl_8b_int8_convrot.safetensors`（`text_encoders/`）、`vae/qwen_image_2.1_vae_bf16.safetensors`（`vae/`） | 7.3 + 9.4 + 0.7 GB |
| 编辑出图 | `Comfy-Org/Qwen-Image-Edit`：`split_files/diffusion_models/qwen_image_edit_2511_int8_convrot.safetensors`（`diffusion_models/`） | 20.5 GB |
| | `Comfy-Org/Qwen-Image`：`split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`（`text_encoders/`）、`split_files/vae/qwen_image_vae.safetensors`（`vae/`） | 9.4 + 0.3 GB |

合计：只做 Ref2VA 视频约 **42 GB**；加两套出图模型约 **89 GB**；再加精修约 **90 GB**；还要 FL2VA 的话约 **113 GB**。文件名和大小取自 HuggingFace 的文件清单（2026-11-23）。下载页上文件在子目录里，放进 ComfyUI 时只放文件本身；放错目录或带着子目录，预检会报「not offered by the server」并给出最接近的名字。

## 怎么用

所有命令在项目根目录下跑；`<skill>` 是本 skill 的目录，`W=<skill>/assets/workflows`。先 `--dry-run` 看预览，再带 `--confirm <批次号>` 提交。

`$W` 只是为了少打字：bash 里先 `W=<skill>/assets/workflows`；PowerShell 里先 `$W = "<skill>\assets\workflows"`，后面同样写 `$W\h3_ref2va.api.json`；cmd 没有这种写法，直接写全路径。Windows 上解释器叫 `python`（不是 `python3`）。

```
# 0. 连通测试（不用模型）
python <skill>/scripts/comfy_submit.py $W/selftest_no_model.api.json --set 1.image=@任意一张图.png --out takes/selftest --poll 2

# 1. 一段 ref2va 草稿，3 个 seed
python <skill>/scripts/comfy_submit.py $W/h3_ref2va_sage.api.json --media prompts/ep01/s01.media.json --batch 3 --seed 1001 --log logs/takes.csv --dry-run

# 2. 同一段，20 步、不挂 Turbo（运镜是主体的镜头，铁律 16）
python <skill>/scripts/comfy_submit.py $W/h3_ref2va_sage.api.json --media prompts/ep01/s01.media.json --seed 1001 --tag s01_full --set 146.value=false --set 123.sampler_name=res_multistep --dry-run

# 3. 精修中选的那条（seed 用中选那条的；草稿是 _sage 版就用 _sage_refine）
python <skill>/scripts/comfy_submit.py $W/h3_ref2va_sage_refine.api.json --media prompts/ep01/s01.media.json --seed 1002 --tag s01_refine --dry-run

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
| `h3_ref2va*_refine` | 二采强度 / 尺寸 | `--set 300.sigma_start=0.31`、`--set 300.width=… --set 300.height=…` |
| | 关了 Turbo 之后 | 同时 `--set 300.steps_override=0`（不关时保持 2；预览的 advice 会提醒配错的情况） |
| `h3_fl2va*` | 关 Turbo / 采样器 / 画布 | `--set 105:126.value=false`、`--set 105:17.sampler_name=…`、`--set 105:104.width=…` |
| `qwen21_t2i` | 提示词 / 尺寸 / 步数 | `--set 459:452.prompt=@文件`、`--set 459:456.width=… .height=…`、`--set 459:458.steps=50` |
| `qwen_edit2511_*` | 输入图 | `--set 41.image=@…`（`image1`）、`--set 42.image=@…`（`image2`）、`--set 43.image=@…`（`image3`）；也可以按标题：`--set-title image1.image=@…` |
| | 提示词 / 输出尺寸 / 步数 | `--set 170:151.prompt=@文件`、`--set 170:300.width=… --set 170:300.height=…`、`--set 170:169.steps=20` |

种子不用 `--set`：`--seed N --batch K` 会把工作流里所有种子一起设成 N、N+1…（精修工作流里一采和 `H3 Hires Fix` 的种子是同一个数）。提示词、帧数、参考图、音色、首尾帧由 `--media` 接，不用手改。

## 不想用附带的，自己从模板导出也行

打开模板 → 菜单「工作流 → 导出（API）」，原样导出的文件脚本就能读：模板里用开关选步数和 LoRA、用选择器算分辨率，预览会把开关和选择器算出来的实际值显示出来，并告诉你翻开关该 `--set` 哪个节点（例如 `--set 146.value=true --set 144.value=8 --set 145.lora_name=minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors --set 136.width=1344 --set 136.height=768`）。模板自带的示例图、算帧数的公式在 `--media` 接线之后不再连着输出，ComfyUI 不会管它们。

## 已知的边界

- `H3 Hires Fix` 的二采、`MiniMaxH3AddGuide`（`--anchor`）、Sage 两个节点在这些工作流里的接法都只通过了校验，没有出过片；第一次用时照 `../first-run-checklist.md` 各验一次。
- Sage 版需要 `sageattention` 包装在 ComfyUI 自己的 Python 里（`references/local-stack-and-acceleration.md` §0b）；没装时节点能加载、运行时才报错——先用不带 `_sage` 的版本确认其余都通。
- 这些文件对应 ComfyUI 0.37.2 的节点定义。升级 ComfyUI 之后如果预检报输入缺失或多余，按上一节从新模板重新导出一份。
