# 02 · MiniMax H3 官方 API 速查（视频生成 v2）

> 来源：platform.minimax.io 的 Video Generation 指南、`video-generation-v2-create` / `-query` / `h3-context-ir` API 参考与 Pricing 页。本文只记录官方文档明确写出的字段；文档未出现的字段（如旧版的 `prompt_optimizer`、`aigc_watermark`、`subject_reference`）**不要**再往 H3 请求里塞。

## 1. 基础信息

| 项目 | 值 |
|------|----|
| Base URL | `https://api.minimax.io`（国内站为 `https://api.minimaxi.com`，路径相同） |
| 认证 | `Authorization: Bearer <API_KEY>`，`Content-Type: application/json` |
| 创建任务 | `POST /v2/video_generation` |
| 提示词增强（只返回改写文本） | `POST /v2/h3_context_ir` |
| 查询任务 | `GET /v2/query/video_generation/{task_id}` |
| 2K 重生成 | `POST /v2/video_regeneration`（指南提及，详细页未抓取） |
| 列表 / 取消 / 删除 | 指南中有链接，本项目未用 |
| 结果获取 | 成功后 `task.content.url` 直接给出**限时**下载链接，无需 file_id 换取；过期后重新查询可拿新链接 |
| 可查询窗口 | 任务创建后 7 天内 |
| 推荐轮询间隔 | 10 秒 |

## 2. 创建任务请求体

```jsonc
{
  "model": "MiniMax-H3",            // 必填: MiniMax-H3 | MiniMax-H3-Highspeed | MiniMax-H3-Lite | MiniMax-H3-Max
  "content": [ /* ContentItem[] 必填，至少 1 个非空 text */ ],
  "resolution": "2K",               // 必填: 480P | 768P | 2K（H3 本体只接受 768P / 2K）
  "duration": 8,                    // 必填: 整数 4..15（Max 为 5..15）
  "ratio": "9:16",                  // 可选，默认 adaptive: adaptive | 21:9 | 16:9 | 4:3 | 1:1 | 3:4 | 9:16
  "callback_url": "https://…",      // 可选，状态变化时 POST 回调
  "extra": { "prompt_expansion_mode": "balanced" }   // 可选，仅 H3-Max: disabled | balanced | quality
}
```

`ratio` 规则：
- 文生视频：**必填且不能是 `adaptive`**。
- 首尾帧（image-to-video）：**始终 `adaptive`**，画幅随输入图；传其他值会被忽略。
- 参考生视频：可选，默认 `adaptive`；`MiniMax-H3-Lite` 暂不支持 `adaptive`。

### 2.1 ContentItem

```jsonc
{ "type": "text",      "text": "…≤7000 字符…" }
{ "type": "image_url", "image_url": { "url": "…" }, "role": "first_frame" | "last_frame" | "reference_image" }
{ "type": "video_url", "video_url": { "url": "…" }, "role": "reference_video" }
{ "type": "audio_url", "audio_url": { "url": "…" }, "role": "reference_audio" }
```

`url` 可以是公网 URL、`mm_file://{file_id}`，或 data URI（`data:image/png;base64,…`、`data:video/mp4;base64,…`、`data:audio/mp3;base64,…`，格式名小写）。整个请求体 ≤ 64 MB，Base64 会膨胀约 33%，大视频请用 URL。

### 2.2 四种合法组合

| 模式 | content 组成 | 备注 |
|------|--------------|------|
| 文生视频 T2VA | 1 个 `text` | `ratio` 必填 |
| 图生视频（首帧）I2VA | `text` + 1 个 `image_url`（`role=first_frame` 或省略） | `ratio` 强制 adaptive |
| 尾帧 L2VA | `text` + 1 个 `image_url`（`role=last_frame`） | |
| 首尾帧 FL2VA | `text` + 2 个 `image_url`（`first_frame` + `last_frame`） | |
| 参考生视频 Ref2VA | `text` + 任意 `reference_image`（≤9）/ `reference_video`（≤3）/ `reference_audio`（≤3） | 音频不能单独出现，必须伴随图或视频 |

**首尾帧与参考模式互斥**：出现任一 `reference_*` 角色后不得再出现 `first_frame` / `last_frame`，反之亦然。

### 2.3 输入媒体限制

| 类型 | 格式 | 单文件 | 数量 | 其他 |
|------|------|--------|------|------|
| 图片 | JPG/JPEG/PNG/WEBP/HEIC/HEIF | ≤ 30 MB | 首帧 ≤1，尾帧 ≤1，参考图 ≤9 | 宽高 256–5760 px，宽高比 0.4–2.5 |
| 视频 | MP4/MOV，H.264/H.265 + AAC/MP3 | ≤ 50 MB | ≤ 3 | 每段 2–15 s，总计 ≤ 15 s，23.976–60 fps |
| 音频 | WAV/MP3 | ≤ 15 MB | ≤ 3 | 每段 2–15 s，总计 ≤ 15 s |

## 3. 官方示例

文生视频：
```json
{"model":"MiniMax-H3","content":[{"type":"text","text":"Epic space-opera theatrical teaser: a female captain stands alone before a massive observation window as the last fleet gathers and jumps away in a blinding flash, the bridge shaking, leaving her behind."}],"resolution":"2K","duration":5,"ratio":"16:9"}
```

首帧图生视频：
```json
{"model":"MiniMax-H3","content":[{"type":"text","text":"Pull focus to the people in the background and add more steam to the ramen bowl."},{"type":"image_url","image_url":{"url":"https://…/input.png"},"role":"first_frame"}],"resolution":"2K","duration":5,"ratio":"adaptive"}
```

首尾帧：
```json
{"model":"MiniMax-H3","content":[{"type":"text","text":"A little girl grows up."},{"type":"image_url","image_url":{"url":"https://…/first.jpeg"},"role":"first_frame"},{"type":"image_url","image_url":{"url":"https://…/last.jpeg"},"role":"last_frame"}],"resolution":"2K","duration":5}
```

参考生视频（图 + 视频 + 音频）：
```json
{"model":"MiniMax-H3","content":[
  {"type":"text","text":"The character performs street dance, following the motion in reference video 1; the character's appearance follows reference images 1 and 2."},
  {"type":"image_url","image_url":{"url":"https://…/ref1.png"},"role":"reference_image"},
  {"type":"image_url","image_url":{"url":"https://…/ref2.png"},"role":"reference_image"},
  {"type":"video_url","video_url":{"url":"https://…/motion.mp4"},"role":"reference_video"}
],"resolution":"2K","duration":5}
```

音色参考（官方原文提示词）：`"Character speaks: Follow the wind, live free. Leave worries behind, enjoy the moment. Voice timbre follows reference audio 1."`

## 4. 响应与任务对象

创建成功：`{"task_id": "424010985738629"}`

查询：
```json
{
  "task": {
    "id": "424010985738629",
    "model": "MiniMax-H3",
    "status": "succeeded",              // queued | running | succeeded | failed | cancelled
    "created_at": 1785125529, "updated_at": 1785125946,
    "content": { "url": "https://…/final.mp4" },     // IR 任务则为 content.prompt
    "resolution": "2K", "duration": 5, "ratio": "16:9",
    "usage": { "total_seconds": 5, "input_seconds": 0, "output_seconds": 5,
               "input_image_count": 1, "input_audio_seconds": 6,
               "total_tokens": 273890, "prompt_tokens": 13500, "completion_tokens": 260390 },
    "task_type": "generation",          // generation | h3_context_ir | regeneration
    "modality": "video"                 // video | text
  }
}
```

失败时多一个 `error`：`{"code":"1026","message":"video description contains sensitive content"}`。

### 4.1 错误码

| HTTP | type | 典型 message (code) |
|------|------|---------------------|
| 400 | bad_request_error | `content must include a non-empty text item (2013)` |
| 401 | authorized_error | `login fail … (1004)` |
| 402 | insufficient_balance_error | `insufficient balance (1008)` |
| 422 | unprocessable_entity_error | `video description contains sensitive content (1026)` |
| 429 | rate_limit_error | `rate limit, please retry later (1002)` |
| 500 / 529 | server_error / overloaded_error | `internal error (1000)` |

短剧生产中 **1026 内容审核** 是最常见失败：真人明星名、血腥、亲密戏描述都可能触发。处理策略见 `docs/03-production-workflow.md` §7。

## 5. 回调（callback_url）

1. 创建任务时 MiniMax 先向回调地址发送一条含 `challenge` 字段的验证请求，服务端须在 **3 秒内原样返回 `challenge`**。
2. 之后每次状态变化推送与「查询任务」结构一致的 JSON（`queued → running → succeeded/failed/cancelled`）。
3. 本地开发没有公网地址时用轮询；参考实现 `pipeline/h3_client.py` 两种都支持。

## 6. H3-Context-IR（提示词增强）

```json
POST /v2/h3_context_ir
{"model":"MiniMax-H3","content":[{"type":"text","text":"两姐妹深夜在医院走廊沉默相对……"}],"duration":10,"ratio":"9:16"}
```

- 不生成视频，只返回 `task_id`；查询后 `task.content.prompt` 即改写结果，`modality=text`。
- 改写结果就是官方三段式结构（`integrated_multimodal_description` / `overall_soundscape` / `non_diegetic_music`），带 `[Shot N] At 00:02.800, the camera cuts to …` 时间码。可直接作为正式生成的 `text`，也可以让 LLM 在此基础上微调台词。
- 计费 $0.90 / M 输入 token、$3.60 / M 输出 token，一条约 ¢1–3。
- 开源权重**不含** IR，自部署时需用 `templates/` 中的提示词模板让 LLM 自行完成这一层改写。

## 7. 2K 重生成

- 请求需**重放原 768P 任务的全部 `content`**，再追加一个 `type=video_url, role=base_video` 的源视频项（注意：`base_video` 在抓取到的 ContentItem 枚举里尚未列出，调用前先查最新文档）。
- 结果用同一个查询接口拿，`task_type=regeneration`。
- 原任务的输入素材按规则重新计费（前 5 张图免费，视频按时长），重生成费用与原任务分开结算。

## 8. 定价摘要（USD / 秒）

| 模型 | 2K | 768P | 480P |
|------|----|------|------|
| MiniMax-H3 | 0.13 | 0.08 | — |
| MiniMax-H3-Highspeed | — | 0.06 | 0.04 |
| MiniMax-H3-Lite | — | 0.04 | 0.025 |
| MiniMax-H3-Max | — | 0.08 | 0.05 |
| Regeneration 768P→2K | 0.05 | | |

输入视频按输出分辩率同价计费；前 5 张图免费（Max 前 2 张），之后 $0.04/张（Lite $0.02）；音频免费。视频套餐暂不覆盖 H3，只能按量付费。
