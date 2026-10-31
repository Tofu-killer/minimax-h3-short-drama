# 09 · Toonflow 项目剖析：能不能当我们的前端？

> 阅读对象：HBAI‑Ltd/Toonflow‑app（master @ d7366e3，2026‑10‑31，v2.0.9）。读了 README、AGENTS.md、docs/development.md、`packages/providers`（接口定义 + 三个媒体供应商源码）、`packages/skills`（v118workflow 全部 reference 与 knowledge、workflow、canvas、mcp）、`packages/teams/storyboardTeam`、`packages/nodes/videoGenerationNode`、`packages/mcp`。飞书上的使用教程与开发者文档需要登录，未读。

## 1. 一句话定位

Toonflow 是一个 **MIT 开源的 AI 短剧 / 漫剧创作桌面平台**：无限画布（Vue Flow 节点图）上放剧本、角色、场景、分镜图、视频片段；内置 Agent（Pi Agent SDK）按 Markdown skill 执行制作流程；模型通过「供应商 .ts 插件」接入；对外提供 MCP 服务让外部 Agent 操控画布。20k star、3.6k fork，每周发版，社区活跃度在同类里最高（火宝短剧 16.8k）。

| 维度 | 事实 |
|------|------|
| 技术栈 | Bun 1.4.3 monorepo；前端 Vue 3 + Vite + Pinia + Element Plus + Vue Flow + Three.js；后端 Express 5 + Zod；桌面 Electrobun（Windows WebView2 / macOS）；Android 内置 Bun 后端；Docker |
| 持久化 | 无数据库。项目 = 工作区目录，画布 = JSON 文件，设置 = `data/settings.json` |
| 节点 | 文本、图片生成、视频生成、音频生成、帧分析、3D 导演台（Three.js 人偶走位预演）、媒体/图片/MD 等扩展节点 |
| 扩展 | 节点 `.umd.js`、工具 `.tool.js`、技能 `SKILL.md`、供应商 `.ts`；插件市场 + `toonflow://install` 协议 |
| Agent | 内置 Agent + 技能 + 记忆；团队（A2A，示例 storyboardTeam：director / writer / reviewer） |
| MCP | `http://127.0.0.1:10588/mcp`，Streamable HTTP 或 stdio；工具：`getAppState` `getCanvas` `findCanvasNodes` `getCanvasNodes` `getCanvasEdges` `addNode` `connectNodes` `getNodeTools` `nodeTools` `workspaceFiles` `getDocument/writeDocument` `runAgent` `listAppOperations/appOperation` |
| 许可 | MIT（v2.0.0 起；旧版 AGPL / Apache 不追溯） |
| 安全 | 端口固定 3000，Web 与 API **无登录鉴权**，只适合本机或内网 |

## 2. 它的短剧工作流（和本仓库 docs/03 对照）

Toonflow 把方法论写在 skill 里而不是代码里。`packages/skills/v118workflow`（13 步、3 张画布）是最完整的一套；`packages/skills/workflow` v2.7.0 是当前主推版本，但**被硬编码为 Seedance 2.0 / 2.5 路由**（"SEEDANCE EPISODE DIRECTOR · PART A"，A0–A12），全文没有出现 MiniMax / H3。

### 2.1 v118workflow 的 13 步

| 步骤 | 落点 | 与本仓库对应 |
|------|------|-------------|
| 0 项目初始化 | 剧本画布 | ① |
| 1 来源与章节事件 / 2 故事骨架 / 3 改编策略 / 4 逐集剧本 | 剧本画布 | ① 剧本改写（更细：有 12 类叙事技法知识文件） |
| 5 基础资产提取 / 6 资产图片 | 资产画布 | ②③ 资产提取 + 定妆图（有 11 种美术风格知识文件） |
| 7 导演规划 | 分集画布 | 本仓库没有的中间层：**分场 + 逐场台词条数/字数 + 情绪浓度 0–10 + 场间过渡表** |
| 8 衍生资产分析 / 9 衍生图片 | 资产画布 | 本仓库 05 的「状态属于场景」原则，Toonflow 把"湿发/破袖"做成父子资产 |
| 10 分镜表 | 分集画布 | ④ 分镜段落 |
| 11 分镜面板落点 | 分集画布 | 把分镜表变成画布节点（路线 A 文本多参：一片段一视频；路线 B 首帧：一镜头一视频） |
| 12 分镜图片 | 分集画布 | ⑤ 首帧图（可跳过） |
| 13 视频准备 → 生成 → 验收 | 分集画布 | ⑥⑦⑧，**三个独立停点 A/B/C** |

### 2.2 和本仓库高度一致的规则（可互相印证）

- 「一个片段 = 一次生成，上限 15 秒与模型上限取小」= 本仓库「段落」。
- 台词计时：默认 **4 字/秒 + 标点停顿 0.3–0.5 s + 首尾余量 1 s**；慢速表演 3 或 2 字/秒；超过 20 字在语义停顿处拆镜并换景别或切听者反应。本仓库用火宝的 4.5 字/秒 + 2 s，口径接近。
- OS/VO 不让画面人物张嘴；听者反应镜不转移说话人；台词原语言原字句。
- 动作密度：2–3 s 一拍、4–6 s 两拍、7 s 以上三拍。
- 无新信息的静态镜头约 6 s 要检查是否拖沓。
- 段间衔接写明结束状态 → 开始状态；不为连续性补动作。
- 默认不配乐，声音写具体声源；字幕后期做（"画面文字与画外字幕分开"）。
- 分镜图可选；多参路线不强制分镜图。

### 2.3 它比本仓库多的东西

- **导演规划层**（分场、台词统计、情绪曲线）和 **衍生资产**（父子态）两个显式阶段。
- 七大知识文件：编剧方法、12 类叙事类型、资产设计、11 种美术风格、镜头设计、图像提示词、视频提示词（含 Seedance 三段式、Wan 单首帧、通用首尾帧五段式 `[Visual][Motion][Camera][Audio][Narrative]`、通用多参 `[References][Instruction]`）。
- 审阅分级（严重 / 中等 / 轻微 + A/B/C/D）和「剧情保真锁」（五类绝对禁止改动）。
- 3D 导演台：用人偶和场景预演站位、视轴、运镜。

### 2.4 它比本仓库少的东西

- **没有 H3 专属提示词方法**。它用宿主占位符 `{{ref N}}`，由供应商翻译成 `图片1 / Image 1`；没有官方三段式 / 六段式、`<d>[Language]</d>`、`(S1)`、`[Shot N] At MM:SS.mmm` 这套语法。
- **没有合成 / 拼接 / 字幕导出**。videoProduction.md 原话：交付默认是「按确认顺序排列的片段及清单」，"旧版 README 提及拼接导出，但该 tag 未提供可据此复用的制作导出路由"。FFmpeg 只给供应商做音频转码。
- 没有 QC 自动化（ffprobe 校验、联络表）。

## 3. MiniMax H3 在 Toonflow 里是怎么接的

没有 MiniMax 官方供应商，只有两家赞助商的转售接口，但**协议就是 MiniMax 官方 v2**：

| 供应商文件 | 接口 | 参数 | 轮询 | 备注 |
|-----------|------|------|------|------|
| `metaso.ts`（秘塔，162 行） | `POST {baseUrl}/v2/video_generation`、`GET {baseUrl}/v2/query/video_generation/{id}`，默认 `https://metaso.cn/api/minimax` | `model` `duration` `resolution`(768P/2K) `ratio` `content[]`（text + reference_image/video/audio 或 first_frame/last_frame） | 5 s，上限 10 min | 模式：`text` / `startFrameOptional` / `[imageReference:9, videoReference:3, audioReference:3]`；时长枚举 4–**30** 秒（平台侧延长，官方 API 为 4–15） |
| `compshare.ts`（优云智算） | `https://cp.compshare.cn/minimax/v2/...` | 同上 + 扩展参数 `use_context_ir`、`skill_id`、`mute_audio`、`aigc_watermark` | 3 s，上限 30 min | 声称 480P–4K、4–30 秒；多出 `singleImage`、`endFrameOptional` 模式 |

`{{ref N}}` 的翻译规则（metaso.ts）：按媒体类型分别编号 → `图片1`、`视频1`、`音频1`；首尾帧 → `首帧` / `尾帧`。这意味着在 Toonflow 里写 H3 提示词时，参考引用必须用 `{{ref 1}}` 这类占位符，再由供应商转成文字标签，**不能直接写 `<Picture 1>`**（除非自己写供应商把它透传）。

赞助商报价（README 原文，未验证）：秘塔 768P 0.09 元/秒、2K 0.15 元/秒；优云 768P 0.08 元/秒。对比官方 $0.13/秒（约 0.93 元）便宜数倍，但是转售方自报。

**接官方 API 只需改一行**：把 `metaso.ts` 复制一份，`baseUrl` 默认值改为 `https://api.minimax.io`（国内 `https://api.minimaxi.com`），时长枚举改回 4–15，即可用官方 key。

## 4. 本地 ComfyUI 怎么接：供应商 .ts 插件

Toonflow **没有内置 ComfyUI 供应商**，但接入机制是明确的：

1. 供应商 = 一个独立 `.ts` 文件，`export default { id, label, version, rules, models, generateVideo(request) }` 字面量；在 Bun 服务端执行；**禁止 import**，只能用宿主注入的 `this.tool.fetch`、`this.tool.media`、`this.tool.audio`、`this.tool.ffmpeg()`；文件 ≤ 2 MB。
2. 导入路径：设置 → 媒体模型 → 添加自定义供应商 → 文件导入 / 粘贴代码；落在 `data/providers/`。
3. `generateVideo` 收到 `VideoRequest`：`prompt`（含 `{{ref N}}`）、`images[] / videos[] / audios[]`（url / base64 / binary）、`firstFrame / lastFrame`、`duration`、`ratio`、`resolution`、`mode`、`other`（模型专属表单）。必须返回最终 `MediaAsset[]`，不能返回任务 id。
4. 内置「媒体模型接入助手」提示词（`apps/web/.../providerPrompt.ts`，约 180 行）专门有 **ComfyUI 分支**：要求用户提供 API 格式工作流 JSON，由 LLM 建立「Toonflow 字段 → 节点 id/输入名」映射，用 `/prompt` 提交、`/history/{prompt_id}` 轮询、`/view` 取回；上传素材走 `/upload/image`；无鉴权本地服务 `rules: []`；每次调用深拷贝 JSON 模板避免并发互相覆盖；不要用 `/interrupt` 误停别人的任务。

### 4.1 针对本地 H3 工作流的供应商骨架

```ts
// comfyH3.ts —— 本地 ComfyUI 上的 MiniMax H3 Ref2VA（示意，节点 id 需按你导出的 API JSON 填写）
const rules = [{ type: "input", field: "baseUrl" as const, title: "ComfyUI 地址", value: "http://127.0.0.1:8188" }] as const;
const workflow = { /* 导出的 API 格式 JSON，节点 id → {class_type, inputs} */ };
const slots = { prompt: ["12", "text"], refImages: ["20", "images"], refAudio: ["21", "audio"], width: ["5", "width"], height: ["5", "height"], frames: ["5", "length"], save: "40" };

export default {
  id: "comfyH3", label: "本地 ComfyUI · MiniMax H3", version: "2.0.0", rules,
  models: [{ id: "h3-ref2va-local", label: "H3 Ref2VA（本地 768P）", type: "video", audio: true,
    mode: [["imageReference:9", "audioReference:3"]],
    imageRatios: ["16:9", "9:16"],
    durationResolutionMap: [{ duration: [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], resolution: ["768P"] }] }],
  async generateVideo(request) {
    const base = this.config.baseUrl.replace(/\/$/, "");
    const g = JSON.parse(JSON.stringify(workflow));          // 每次独立副本
    // 1. 上传参考图 → POST /upload/image (multipart)，拿到 name 填进 LoadImage 节点
    // 2. 提示词：把 {{ref N}} 翻成 <Picture N>（保持官方六段式语法），写入 CLIPTextEncode
    g[slots.prompt[0]].inputs[slots.prompt[1]] = request.prompt.replace(/\{\{ref (\d+)\}\}/g, (_, n) => `<Picture ${n}>`);
    // 3. 时长 → 帧数（17k+5 网格 @24fps），画幅 → 768 短边宽高
    const frames = Math.round((request.duration ?? 5) * 24 / 17) * 17 + 5;
    g[slots.frames[0]].inputs[slots.frames[1]] = frames;
    // 4. POST /prompt → prompt_id；轮询 GET /history/{prompt_id} 直到 outputs 出现；
    // 5. GET /view?filename=…&subfolder=…&type=output 下载 mp4，返回 binary
    const { prompt_id } = await (await this.tool.fetch(`${base}/prompt`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt: g }), signal: this.signal })).json();
    for (;;) {
      const h = await (await this.tool.fetch(`${base}/history/${prompt_id}`, { signal: this.signal })).json();
      const out = h[prompt_id]?.outputs?.[slots.save];
      if (out) { const f = (out.videos ?? out.gifs ?? out.images)[0];
        const bytes = new Uint8Array(await (await this.tool.fetch(`${base}/view?filename=${encodeURIComponent(f.filename)}&subfolder=${encodeURIComponent(f.subfolder ?? "")}&type=${f.type}`)).arrayBuffer());
        return [{ mediaType: "video", type: "binary", data: bytes, mimeType: "video/mp4" }]; }
      if (h[prompt_id]?.status?.status_str === "error") throw Object.assign(new Error("ComfyUI 执行失败"), { code: "MEDIA_TASK_FAILED" });
      await new Promise(r => setTimeout(r, 3000));
    }
  },
} satisfies ProviderDefinition<typeof rules>;
```

要点：`{{ref N}}` → `<Picture N>` 的翻译放在供应商里做，这样在 Toonflow 里可以直接用本仓库 `docs/04` 的官方六段式写提示词；输出节点字段名（`videos` / `gifs` / `images`）取决于你用的保存节点（VHS_VideoCombine 返回 `gifs`，核心 SaveVideo 返回 `videos`）。

## 5. 外部 Agent 接管：MCP 路线

Toonflow 的 MCP 让 Claude Code / Codex 这类外部 Agent 直接操作运行中的 Toonflow：

```
getAppState → getCanvas({include:["nodeTypes"]}) → addNode({type,position,label})
→ nodeTools({nodeId, name:"node:setPrompt", args:{prompt}})
→ nodeTools(… "node:setConfig", {providerId, modelId, mode, duration, resolution})
→ connectNodes({connections:[{source, sourceHandle, target, targetHandle}]})   // 参考图连线决定 {{ref N}} 顺序
→ nodeTools(… "node:generateVideo") → nodeTools(… "node:getGenerationStatus")  // idle/running/succeeded/failed
```

约束：画布操作需要 Toonflow 窗口打开；单次工具调用 30 分钟超时；读取 64 KiB/次；不允许直接改带 `toonflowCanvas` 标记的 JSON 文件。`runAgent` 可把任务委托给 Toonflow 内置 Agent（按 skill 跑 13 步流程）。

## 6. 对本项目的结论

### 6.1 值得借的

1. **导演规划层**：在分镜拆解前先做「分场 + 台词统计 + 情绪浓度 + 过渡表」，本仓库 `pipeline/prompts/02_storyboard_system.md` 可以加这一段中间输出。
2. **台词计时口径**：4 字/秒 + 标点停顿 + 1 s 余量，比 4.5 字/秒 + 2 s 更细；`storyboard.py` 的校验器可改为按语速档位（4 / 3 / 2 字/秒）计算。
3. **三个独立停点**（准备确认 / 生成结果确认 / 选用交付确认）和「任务已启动 ≠ 媒体成功」的纪律，适合写进 Agent 接管提示词。
4. **衍生资产父子态**：角色基础态 + 本集衍生态（湿发、受伤、换装）在资产库里显式建模。
5. **供应商 .ts 单文件插件**的设计：无 import、宿主注入 fetch/ffmpeg、`{{ref N}}` 由供应商翻译。本仓库 `pipeline/h3_client.py` 可按同样契约封一层，方便将来挂到任何前端。

### 6.2 不要指望它的

- 没有 H3 专属提示词方法，更没有官方三段/六段式；当前主推 workflow skill 锁死 Seedance。要在 Toonflow 里做 H3 短剧，需要**自己写一份 `h3workflow` skill**（可以直接把本仓库 docs/03–05 改写成 SKILL.md + references，格式照 v118workflow）。
- 没有拼接、字幕、QC、交付导出；成片仍要靠本仓库 `pipeline/stitch.py` 或剪映。
- 没有 ComfyUI 供应商；要自己写（上面骨架）或用它的接入助手让 LLM 生成。
- 30 秒时长、4K 分辨率等是转售平台能力，官方 API 与开源权重都没有。

### 6.3 推荐组合（针对本地 4090 + ComfyUI H3 的用户）

| 层 | 用什么 | 理由 |
|----|--------|------|
| 画布 / 资产库 / 分镜可视化 / 人工确认 | **Toonflow 桌面版** | 20k star 社区、角色/场景资产管理、3D 导演台、每步确认的 UI，比纯命令行好用 |
| 视频生成后端 | **自写 `comfyH3.ts` 供应商** → 本地 ComfyUI（Ref2VA / FL2VA API 工作流） | 一个文件接入，`{{ref N}}` → `<Picture N>` 后可用官方六段式提示词 |
| 方法论 / 提示词 | **本仓库 docs/04–05 改写成 Toonflow skill** | Toonflow 没有 H3 语法 |
| Agent 接管 | **外部 Agent 走 MCP** 操作画布 + 节点工具，或 `runAgent` 委托内置 Agent 按 skill 执行 | 保留人工停点 |
| 拼接 / 字幕 / QC / 交付 | **本仓库 `pipeline/stitch.py`** | Toonflow 不做合成 |
| 纯批量无人值守 | **本仓库 `pipeline/run_episode.py`（或 local 版）** | 上百集工业化时不需要画布 |

一句话：**Toonflow 适合做「有人看着的制片间」，本仓库的 pipeline 适合做「没人看着的流水线」；两者通过同一套分镜 JSON 与六段式提示词衔接。**

## 7. 源码位置索引（便于后续查阅）

| 内容 | 路径 |
|------|------|
| 供应商接口定义 | `packages/providers/types.d.ts` |
| 秘塔 H3 供应商（最小可读范本） | `packages/providers/src/media/metaso.ts` |
| 优云 H3 供应商（含 use_context_ir 等扩展参数） | `packages/providers/src/media/compshare.ts` L1534–1720 |
| 接入助手提示词（含 ComfyUI 分支） | `apps/web/src/components/settings/panels/mediaModel/providerPrompt.ts` |
| 13 步短剧流程 | `packages/skills/v118workflow/SKILL.md` + `references/*.md` |
| 镜头 / 台词计时 / 审阅 | `packages/skills/v118workflow/references/knowledge/shotCraft.md` |
| 视频提示词模板 | `packages/skills/v118workflow/references/knowledge/videoPromptCraft.md` |
| 画布与节点工具用法 | `packages/skills/v118workflow/references/canvasOperations.md` |
| Seedance 导演规范（A0–A12） | `packages/skills/workflow/SKILL.md` |
| MCP 工具说明 | `packages/mcp/README.md`、`packages/mcp/skills/toonflow/SKILL.md` |
| 视频节点 `{{ref N}}` 顺序逻辑 | `packages/nodes/videoGenerationNode/src/index.vue` L241–274 |
| 团队（A2A）示例 | `packages/teams/storyboardTeam/team.json` |
