# 按需翻译

默认源语言 `en`，支持 `en、zh、es、ar、ru`，用户可调整。后台维护源文，已有人工语言版本导入时保留内容关联与版本。建站时在源码中实现两种引擎、运行时注入、术语保护、持久缓存和前台触发；部署负责绑定资源和配置，不为单个项目临时改写翻译代码。

## 触发与优先级

选择语言 → 查询已发布当前版本 → 读取人工译文和缓存 → 缺失块入队 → 翻译、校验并持久化 → 后续访问复用。

- 有效人工译文 > 有效缓存 > AI。固定界面词典可保留；正文按语义块及必要语境翻译，不逐词替换拼句子。
- 部署、发布不自动全站预热。管理员可指定单篇及语言，不阻塞原文发布。访问某篇的某语言，只预热实际请求的块和语言。
- 已缓存正文尽量直接渲染到 HTML；缺失时先保留可读原文，再更新成功块。浏览器只加速与存语言偏好，换浏览器和重启仍能复用服务器译文。
- 正确设置 `lang` 和 RTL；快速切换时核对当前语言、内容版本、请求序号，丢弃迟到结果。不替换访客输入，不丢失筛选与表单。
- 默认不生成大量语言 HTML。客户端切换不等于多语言 SEO；需要独立收录时另实现稳定语言地址与实际译文 HTML，验证后才设置 `hreflang`。

## 源码内的双引擎

`initTranslationEngine(runtime)` 返回站点作用域实例，提供 `engineStatus()` 与 `callEngine(texts, options)`；等价接口记录兼容映射。参考代码 [engine.mjs](../assets/translation/engine.mjs) 只实现引擎和保护，网站仍须实现内容校验、缓存、任务和前台。

```js
// Cloudflare 引导程序注入实际绑定；与本项目存储注入和路由一起实现。
const engine = initTranslationEngine({ AI: env.AI, env, glossaryVersion: '1' });
// Node 启动，两个分支使用同一翻译模块。
const nodeEngine = initTranslationEngine({ env: process.env, glossaryVersion: '1' });
```

不能把请求 env 写入多租户共用的可变全局变量。实例复用范围与站点和账号一致。`callEngine` 内选引擎，`engineStatus` 使用相同逻辑：

1. 已注入且有可调用的 `AI.run` → `workers-ai`。
2. 未注入 AI，且 `TRANSLATION_ENDPOINT、TRANSLATION_API_KEY、TRANSLATION_MODEL` 三者齐全 → `openai-compatible`。
3. 均不可用 → `unconfigured`，不调用模型，前台保留原文。

`TRANSLATION_ENDPOINT` 是完整 HTTPS Chat Completions 地址，不猜测追加路径。外部引擎通过服务端密钥调用；批量请求返回等长、有序的 JSON 字符串数组，严格校验。已有地址语义不同则保留兼容映射。

```json
{"provider":"workers-ai","configured":true,"model":"@cf/meta/m2m100-1.2b","engineVersion":"dual-engine-v1:protected-v1","glossaryVersion":"1"}
```

provider 为 `workers-ai | openai-compatible | unconfigured`，未配置 model 为 null。configured 仅表示配置完整，不证明授权、额度或调用成功；后台另记最近调用结果。状态不含密钥和内部错误原文。已选引擎失败不静默切换供应商，尤其不能因 Cloudflare 失败调用收费外部引擎。

## Workers AI 适配

- 默认模型候选 `@cf/meta/m2m100-1.2b`，用 `WORKERS_AI_TRANSLATION_MODEL` 或等价服务端配置替换；同时核对适配器、语言及缓存版本，不能只改模型字符串。
- Wrangler 包含 `"ai":{"binding":"AI"}`，引导代码实际注入 `env.AI`。上传 Cloudflare、Node 兼容开关或协议声明不能替代绑定与真实调用。
- 默认同步调用 `env.AI.run(model, {text, source_lang, target_lang})`，读取 `translated_text`。一段一次，受限并发与预算，按原顺序返回等长结果。异步 Batch API 是另一套任务协议，不能把文本数组直接塞给同步 text 字段。
- 根据已核验的模型语言表校验方向；语言标签需要映射时明确实现。未知或不支持方向为 `unsupported_direction`，不猜测调用。增加语言须更新映射和测试。
- 此翻译模型同步输入没有 system prompt，术语保护须在代码层实现；换为生成模型时另做适配。
- 项目设置持久化站点预算、暂停开关与统计口径。账户是付费计划时，超过免费分配可能继续计费，仅捕获报错不能实现免费上限；调用次数也不等于精确 Neuron 用量。未获预算授权不购买、升级或启用超额付费，不静默转收费服务。

执行时核对当前官方资料。本次核对日期 2026-10-05：[模型与调用](https://developers.cloudflare.com/workers-ai/models/m2m100-1.2b/)、[绑定](https://developers.cloudflare.com/workers-ai/configuration/bindings/)、[限速](https://developers.cloudflare.com/workers-ai/platform/limits/)、[费用](https://developers.cloudflare.com/workers-ai/platform/pricing/)。这些资料不保证占位符保持不变，所选语言方向必须实际测试。

## 内容块与术语表

服务端从已发布内容提取块：

```json
{"id":"article:care:paragraph:intro","text":"Care instructions for Valenza leather.","kind":"text","context":"article body; leather care"}
```

id 在同一内容中稳定且唯一，插入段落不让全部 ID 重排。text 是可见纯文本；kind 为 `text | title | list-item | table-cell | alt`。列表逐项、表格逐单元格，保留各项稳定身份；过长段落按句子拆稳定子块，不截断保护片段。富文本保留经清洗的结构，模型输出按文本渲染。context 只用公开标题、字段用途和产品类别。

blockIds 是上述 ID 数组，用于只请求页面需要的块；浏览器不得自行提交正文。纯邮箱、URL、型号和数值字段可直接保留原文。

```json
{
  "version":"2",
  "entries":[
    {"source":"Valenza","sourceLanguage":"en","targetLanguage":"*","mode":"preserve","translation":null,"scope":"global","version":"1"},
    {"source":"full-grain leather","sourceLanguage":"en","targetLanguage":"es","mode":"translate","translation":"cuero de plena flor","scope":"product","version":"2"}
  ]
}
```

source 非空，sourceLanguage 为实际源语言。targetLanguage 为目标语言，`*` 只允许 preserve。preserve 还原原文，translate 必须有非空目标译文。scope 为 global 或项目内容类型（product/article/page 等）；条目与总表均有 version。

默认精确区分大小写，按文字系统校验边界：英文等避免匹配词内片段，中文等不要求空格。最长匹配优先，同词的具体范围优先于 global，同优先级矛盾条目拒绝配置。术语修改更新版本并失效受影响缓存。品牌、型号来自后台结构化字段和 protectedTerms 清单，正则只是辅助，不能保证识别全部名称。

## 占位符保护与校验

两种引擎共用保护流程，外部引擎的 prompt 只作辅助：

1. 扫描品牌、型号、数字及单位、邮箱、网址、preserve 和 translate 术语，生成不重叠片段。避免 URL 中数字二次替换，重复术语每次有独立占位符。
2. 生成不与原文冲突的标识，例如 `[[B2BT_<随机标识>_0]]`，替换后调用模型。任何格式都可能被修改，不能声称模型不会改动。
3. 结果须为非空字符串，块数量相同；每个预期标识恰好一次，无未知、损坏或遗留标识。校验后用原文或指定目标译文还原。
4. 缺失、重复、改写等为 `placeholder_mismatch`，该块失败，保留原文和有效缓存，不展示标识，也不取消保护后盲目重试。

参考实现覆盖常见数字/单位、邮箱、URL和带字母数字的型号；项目须补行业单位、品牌与型号并测试。保护成功不代表译文自然或规格含义正确，仍须抽查。

## 接口与状态

`POST /api/v1/translations/resolve`：

```json
{"contentId":"article:care","revision":3,"targetLanguage":"es","blockIds":["article:care:paragraph:intro"]}
```

服务端核验已发布内容、当前版本、语言与块归属。禁止接收任意文本消耗公共额度；旧 DOM 接入须核对文字来自本站公开内容。过期请求报告 `stale_revision`，不翻译或缓存旧正文。

保留原有返回字段，兼容增加可选 reasonCode 与脱敏 engine：

```json
{"ok":true,"data":{"status":"pending","sourceLanguage":"en","targetLanguage":"es","revision":3,"blocks":{},"retryAfterMs":2000,"engine":{"provider":"workers-ai","configured":true,"model":"@cf/meta/m2m100-1.2b","engineVersion":"dual-engine-v1:protected-v1","glossaryVersion":"2"}}}
```

| status | 含义 |
|---|---|
| ready | 本次所需块均可用；源语言直接返回原文，不调用 AI |
| partial | 部分有效结果，其余未完成或失败；原文不算翻译成功 |
| pending | 真实任务已排队或执行中，提供再次查询间隔 |
| unconfigured | 没有有效引擎配置，原文和已有有效译文可读 |
| failed | 没有可用译文且处理失败，返回简短原因 |

reasonCode 可为 `stale_revision、unsupported_direction、unsupported_model、unauthorized、quota_exceeded、rate_limited、timeout、placeholder_mismatch、invalid_engine_output、provider_error`。SDK 错误按实际代码映射，不靠猜错误文本判断计费。鉴权、404、非法字段、超限及限速用正确 HTTP 错误与 `{ok:false,error:{code,message}}`，不伪装成功任务。内部详情只显示于鉴权后台。

## 缓存、任务和隔离

- 缓存身份包含站点、源/目标语言、块文字及语境摘要、引擎/模型/提示词与保护算法版本、术语表版本。术语可用本块实际应用条目的版本摘要作为有效版本，完整表版本另记元数据，避免无关术语变更使全站失效。revision 用于校验请求与写入，不能仅按整篇 revision 建缓存导致全文重译。
- 修改只重算受影响的文字、语境或术语块；未变块复用。写入前再次核验发布状态、版本与摘要，翻译期间修改或下架不得写入旧结果。缓存命中也先检查发布状态；下架停止公开复用。
- 任务身份与缓存一致，跨请求去重，多实例使用持久协调。服务端控制并发、长度、超时、有限重试与站点预算；超时不等于供应商调用已取消，不立刻重复计费调用。
- 失败不覆盖有效缓存，成功块可分别保存。参考引擎整批校验失败则拒绝整批；需要部分完成时服务层按块隔离并保留上述语义。
- Cloudflare 任务用平台支持的持久机制，不返回 pending 后只依赖普通计时器；Node 重启须恢复任务或明确重试状态。
- 可共用引擎和经过审核的通用术语表，各站完整内容及缓存隔离。相同服务名、模型或对象实例名称不自动形成跨站共享。
- 草稿、询盘、私密附件、账号、访客输入一律不发送翻译，也不写入公开日志。已发布内容仅交给用户选择且授权的引擎。

## 建站与交接

源码实现两种分支并做隔离测试，不要求同时部署两套网站。跨平台部署仍要适配路由、数据库、附件和任务，双引擎不能让任意 Node ZIP 自动成为 Worker。

复制参考模块到网站服务端，例如 lib/translation-engine.mjs；调用时传源/目标语言、服务端保护清单、`glossary.entries`、scope 和公开 context。生产环境必须在解析接口/任务层实施权限、持久预算和去重。模块提供可选 `reserveUsage({provider,blocks})` 预算钩子（返回 false 阻止调用）及 `mapWorkersError(error)` SDK 错误映射；这些钩子的模拟测试不等于已实现持久预算。默认并发3、最长单块3000字符、单批50块、超时15秒均是示例值，按目标平台限制调整并记录。

Workers 默认适配器仅处理上述翻译模型。更换模型须提供经过验证的 workersAdapter 与 supportedLanguages，未知 schema 明确失败。模型不能额外接收语境 prompt 时，选择足够完整的语义块和术语约束，并抽查上下文质量。参考模块不持久化任何正文或缓存。

交接记录实际 provider/model、变量与绑定名、块/术语版本、缓存与任务存储、预算及未完成项。模拟、真实引擎、缓存持久化、前台显示分开报告。按 [验收](acceptance.md) 确认后才称已接通。升级 Skill 不自动升级已部署网站。
