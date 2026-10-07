# 按需翻译

默认服务及引擎选择以 [Hy-MT2 接入](hymt-default.md) 为准；Workers AI 仅在明确选择时启用。


默认源语言 `en`；默认8种语言为英文 `en`、中文 `zh`、西班牙语 `es`、阿拉伯语 `ar`、俄语 `ru`、法语 `fr`、德语 `de`、葡萄牙语 `pt`，用户可调整。英文是内容原文，中文是建站时预先提供的目标译文；中文后台不改变源语言。后台维护源文，已有人工语言版本导入时保留内容关联与版本。

建站时复用支持 Hy-MT2、Workers AI 与 OpenAI 兼容接口的公共核心，实现运行时注入、术语保护、初始中文导入、持久缓存和前台触发；部署负责绑定资源和配置，不为单个项目临时改写翻译代码。

## 初始中文与8种语言选项

- 建站交付完整的英文内容及对应中文译文，覆盖初始首页、业务页面、产品/服务、初始文章、表单/弹窗、可翻译的标题、元信息与图片说明。中文不能只覆盖导航或标题；品牌、型号、邮箱、数字规格等按保护规则保留。以真实初始内容块清单逐项核验，缺项不可声称完整。
- 其余6种语言只提供语言名称与切换入口，不打包整站并行全文字典，不生成成套语言页面。接通实际翻译引擎后，访问内容并切换语言时补译。切换入口存在不等于服务已接通。
- 未接翻译服务时，英文与有效初始中文直接可读。其他语言或缺失中文保留源文，提示本次翻译暂不可用；不能把英文回显保存为成功译文。前台用简短可理解的状态，接入详情留在后台。
- 新增文章按后台设置自动准备目标译文；产品或页面缺失译文时仍可按需翻译或由管理员一键生成；有对应人工译文则优先使用。只修改一段英文时，原中文中该段失效，其他匹配块继续复用。部署、升级不自动翻译全站。文章保存、更新及发布可按后台配置自动创建持久任务，见 [后台翻译任务](translation-admin.md)。
- 初始中文是 `origin=seed` 的内容级译文，不是通用逐词词典。共用经过审核的行业术语表；各网站正文及中文数据按站点隔离。

### 初始译文数据与导入

推荐放在项目 `seed/translations.zh.json`，每条记录关联 siteId、contentId、blockId、sourceLanguage、targetLanguage、sourceHash、translation 和 origin。sourceHash 对确切原文字串和公开语境用版本化算法计算，例如 SHA-256(JSON.stringify(["source-v1", text, context]))，不得只按标题、slug 或文章版本认定有效。服务端先提取源块，再从同一块生成记录，不由浏览器提供或信任摘要。示意：

```json
{"siteId":"example-site","contentId":"page:home","blockId":"page:home:hero:title","sourceLanguage":"en","targetLanguage":"zh","sourceHash":"<生成的SHA-256十六进制摘要>","translation":"您信赖的供应伙伴","origin":"seed"}
```

将 seed 作为首次内容初始化的一部分，持久化到本站译文存储；译文存储以站点/内容/块/语言/源摘要/来源为唯一身份；导入检测同一源身份的已有记录，人工内容优先，幂等且与初始内容发布一致。代码升级不重新覆盖线上原文、人工译文或缓存，不因为包内 seed 较新就覆盖管理员内容；已有网站如需导入新 seed，应单独做匹配与迁移。种子和人工译文校验源摘要、语言及块归属，不依赖 AI 模型版本；术语规则变化单独审核这类已编写译文，不能因更换 AI 模型把完整中文全部作废。

[seed.mjs](../assets/translation/seed.mjs) 是生成记录、查找当前有效人工/种子译文和筛选导入候选的参考辅助模块；调用前网站必须核验已发布内容及站点归属。它不实现数据库、事务、缓存、解析接口或AI回退。按 [专项验收](acceptance.md) 完成真实持久化与端到端测试。

## 页面源块与入口一致性

页面适配器先从当前已发布源内容提取块，再应用人工译文、初始译文与缓存。块编号和 sourceHash 始终基于源内容；不能在已翻译 HTML、替换后的 DOM 或按目标语言选择的模板正文上重新生成。前台提交的编号必须与服务端加载同一路径源内容得到的编号一致；语言选择、lang/RTL 和本地日期格式单独处理，不改变源块身份。列表筛选或内容参数影响块集合时，接口应验证并使用相同的公开内容范围。

临时入口、平台默认域名和正式域名须分别核对实际请求来源。SITE_ORIGIN 等配置应匹配正式入口；经反向代理访问时，由受信代理验证浏览器 Host/Origin 并映射到后端预期来源，或由应用校验明确配置的精确公开来源列表。拒绝外站、伪造转发头和缺少必要来源的写请求，不能关闭来源校验、使用通配允许列表或把任意转发头当成授权。绑定正式域名后重验，不用换域名替代页面编号修复。

出现 origin_rejected 或 invalid_block_ids 时，先修入口/源块接线并核对前台实际请求；这类失败不算引擎故障或额度不足。前台保持可读原文和简短提示，后台仅记录安全的原因码，不将配置错误详情展示给访客。

## 公共执行模块

使用 [resolver.mjs](../assets/translation/resolver.mjs) 统一人工/初始译文、块缓存、词汇库传参和写入前版本核验；存储与持久任务由项目注入。使用 [v2 工作台协议](translation-workbench-v2.md) 安装、接线并检查指纹。quality.mjs 仅拦明显重复和残留，无法认证语义准确。

## 首屏与异步补译

公开页面返回前只查询当前有效译文，不等待模型。默认参考实现通过 resolver 的 cacheOnly 模式读取人工、初始及缓存结果，将缺失的源块编号和版本标记到 HTML；浏览器调用解析接口将块纳入与后台共用的持久队列，再查询并更新对应位置。无配置或终止失败保留原文、显示简短状态并提供明确重试，不显示内部原因或清空页面。实际可见块、屏外块、后台任务依次优先，块锁及站点任务租约共同防止重复和并行失控。固定界面预写译文与动态正文分开管理，但使用相同语言选择和源摘要规则；合法同形界面词不能仅因与英文相同而重复交给模型。输入内容不进入任何块或请求。

后续 HTML 直接包含已保存译文；服务器持久记录供不同访客复用，浏览器可作额外加速层，不能以浏览器缓存代替本站持久记录。首屏翻译完成前可能显示源文，不承诺零等待或完整多语言 SEO。安装公共模块后还须接入页面、前台状态与持久调度器。

## 触发与优先级

选择语言 → 查询已发布当前版本 → 读取人工译文、初始中文和缓存 → 缺失块入队 → 翻译、校验并持久化 → 后续访问复用。

- 当前有效人工译文 > 当前有效初始中文 > 当前有效AI缓存 > AI。有效是指站点、内容/块、源/目标语言和当前源摘要匹配；过期记录不参与优先级。正文按语义块及必要语境翻译，不逐词替换拼句子。固定界面中文可保留，但缺键/过期必须进入统一解析流程，不能提前返回英文而阻止动态文章补译。
- 必须先查有效译文，再查引擎配置。AI未配置不能阻止读取初始中文或既有缓存；本次所需块全有中文可返回 ready，同时 engine.configured=false。部分有效时返回 partial 与缺失原因，全部缺失且无引擎才为 unconfigured；语言菜单、译文覆盖和引擎状态分别计算。
- 部署不自动全站预热。文章保存/更新/发布按配置排队；管理员可指定内容及语言，不阻塞原文保存和发布。访问某篇的某语言，只预热实际请求的块和语言。
- 已缓存正文尽量直接渲染到 HTML；缺失时先保留可读原文，再更新成功块。浏览器只加速与存语言偏好，换浏览器和重启仍能复用服务器译文。
- 正确设置 `lang` 和 RTL；快速切换时核对当前语言、内容版本、请求序号，丢弃迟到结果。不替换访客输入，不丢失筛选与表单。
- 默认不生成大量语言 HTML。客户端切换不等于多语言 SEO；需要独立收录时另实现稳定语言地址与实际译文 HTML，验证后才设置 `hreflang`。

## 公共引擎与运行时选择

`initTranslationEngine(runtime)` 返回站点作用域实例，提供 `engineStatus()` 与 `callEngine(texts, options)`；等价接口记录兼容映射。参考代码 [engine.mjs](../assets/translation/engine.mjs) 只实现引擎和保护，网站仍须实现内容校验、缓存、任务和前台。

```js
// Cloudflare 引导程序注入实际绑定；与本项目存储注入和路由一起实现。
const engine = initTranslationEngine({ AI: env.AI, env, glossaryVersion: '1' });
// Node 与 Worker 复用同一模块；新工程 env.TRANSLATION_PROVIDER 为 hymt。
const nodeEngine = initTranslationEngine({ env: process.env, glossaryVersion: '1' });
```

不能把请求 env 写入多租户共用的可变全局变量。实例复用范围与站点和账号一致。`callEngine` 内选引擎，`engineStatus` 使用相同逻辑：

1. 新工程显式设置 `TRANSLATION_PROVIDER=hymt`，使用 Hy-MT2 原生接口、默认地址/模型及服务端密钥；缺密钥为 `unconfigured`。详见 hymt-default.md。
2. 明确设置 `workers-ai` 时仅使用可调用的 `AI.run`；明确设置 `openai-compatible` 时要求 endpoint/key/model 完整。指定引擎配置缺失不回退到其他引擎。
3. 兼容旧工程未指定 provider 的情况：完整外部配置优先选择 `openai-compatible`，否则采用已有可调用 AI 绑定，均缺失为 `unconfigured`。未知 provider 为配置错误。
4. 引擎失败保留原文及有效缓存，不跨供应商切换；引擎选择不改变人工/初始译文优先级。

在 `openai-compatible` 模式，`TRANSLATION_ENDPOINT` 是完整 HTTPS Chat Completions 地址，不猜测追加路径。外部引擎通过服务端密钥调用；批量请求返回等长、有序的 JSON 字符串数组，严格校验。已有地址语义不同则保留兼容映射。

```json
{"provider":"workers-ai","configured":true,"model":"@cf/meta/m2m100-1.2b","engineVersion":"unified-translation-v2:hymt-v1","glossaryVersion":"1"}
```

provider 为 `hymt | workers-ai | openai-compatible | unconfigured`，未配置 model 为 null。configured 仅表示配置完整，不证明授权、额度或调用成功；后台另记最近调用结果。状态不含密钥和内部错误原文。已选引擎失败不静默切换供应商，尤其不能因 Cloudflare 失败调用收费外部引擎。

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

三种适配共用品牌、型号、数字与术语识别，分别处理模型调用：

1. 扫描品牌、型号、数字及单位、邮箱、网址、preserve 和 translate 术语，生成不重叠片段，避免重复替换。
2. Workers AI 翻译模型只接收其余文字片段；受保护值与指定术语译文始终留在代码中，翻译后按原顺序拼接。每个片段会消耗一次调用额度，短片段可能影响语句流畅度，需实际语言复核。
3. 外部生成模型使用占位符及 prompt，恢复时校验唯一对应关系；无法可靠恢复则 placeholder_mismatch，保留原文和有效缓存，不展示标识。
4. Hy-MT2 使用原生 from/to/text 逐块调用及简短保护标记，严格还原；细节见 hymt-default.md。各适配均检查非空结果和明显重复输出。保护与结构检查通过不代表语义质量通过，不得据此把 qualityVerified 设置为 true。

参考实现覆盖常见数字/单位、邮箱、URL和带字母数字的型号；项目须补行业单位、品牌与型号并测试。保护成功不代表译文自然或规格含义正确，仍须抽查。

## 接口与状态

`POST /api/v1/translations/resolve`：

```json
{"contentId":"article:care","revision":3,"targetLanguage":"es","blockIds":["article:care:paragraph:intro"]}
```

服务端核验已发布内容、当前版本、语言与块归属。禁止接收任意文本消耗公共额度；旧 DOM 接入须核对文字来自本站公开内容。过期请求报告 `stale_revision`，不翻译或缓存旧正文。

保留原有返回字段，兼容增加可选 reasonCode 与脱敏 engine：

```json
{"ok":true,"data":{"status":"pending","sourceLanguage":"en","targetLanguage":"es","revision":3,"blocks":{},"retryAfterMs":2000,"engine":{"provider":"workers-ai","configured":true,"model":"@cf/meta/m2m100-1.2b","engineVersion":"unified-translation-v2:hymt-v1","glossaryVersion":"2"}}}
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
- AI断开后，仍允许读取与当前源块及最后已知有效缓存配置匹配的持久译文；保留引擎/模型等有效版本信息，不把 provider=unconfigured 当作新缓存身份。配置新模型/规则时按版本失效AI缓存；初始/人工中文按其独立规则核验。
- 修改只重算受影响的文字、语境或术语块；未变块复用。写入前再次核验发布状态、版本与摘要，翻译期间修改或下架不得写入旧结果。缓存命中也先检查发布状态；下架停止公开复用。
- 任务身份与缓存一致，跨请求去重，多实例使用持久协调。服务端控制并发、长度、超时、有限重试与站点预算；超时不等于供应商调用已取消，不立刻重复计费调用。
- 失败不覆盖有效缓存，成功块可分别保存。参考引擎整批校验失败则拒绝整批；需要部分完成时服务层按块隔离并保留上述语义。
- Cloudflare 任务用平台支持的持久机制，不返回 pending 后只依赖普通计时器；Node 重启须恢复任务或明确重试状态。
- 可共用引擎和经过审核的通用术语表，各站完整内容及缓存隔离。相同服务名、模型或对象实例名称不自动形成跨站共享。
- 公开接口拒绝草稿；只有已鉴权管理员触发或其自动翻译设置授权的文章草稿公开字段，才可经私有服务端任务交给所选引擎预译。草稿译文不提前公开。询盘、私密附件、账号及访客输入一律不发送翻译，也不写入公开日志。见 translation-admin.md 的隔离要求。


## 中英文混排与页面识别

内容块或 DOM 文本识别不能仅因含汉字而排除整个片段。英文正文带中文括号、中文正文夹外语说明、品牌/型号和正文共处一块时，仍按目标语言处理需要翻译的自然语言；纯目标语言内容及明确保留的品牌/术语不应被强制重复翻译。不能仅凭“出现目标语言字符”判断整段已经翻译。

DOM 接入保持 HTML 结构、链接、强调样式和受保护文字，校验解码后的可见文本；品牌保护只覆盖品牌本身，不能使同段的说明文字跳过。含混排的文本块照常进入内容归属检查、人工译文/缓存查询与缺失块翻译流程。短语词典缺键应继续调用引擎，不能算已完成；确认人工译文时仍匹配当前源文摘要。

验收例（通用虚构文本）：`Acme Alliance（示例联盟） connects international visitors with local services.`，并使用带 `<strong>` 品牌强调的相同正文。切换中文后英文说明应完整变为中文，中文括号保持含义，品牌按保护表保留或使用已确认名称；不能只翻译开头词、只识别不含中文的子片段，或剩余整句英文却报告 ready。再切换一个其他目标语言核对该混排块仍被识别；实际未调用引擎或未人工复核时明确记录限制。

还要测试纯中文内容、仅品牌/型号的文本、已有人工译文和缓存命中；修改混排段落后仅该块旧译文失效。DOM 识别证据与引擎输出检查分别记录，防止把未入队误判成引擎故障。完整验收项见 [验收规范](acceptance.md)。

## 建站与交接

源码保留公共核心的三种适配并做隔离测试，不要求同时部署两套网站。跨平台部署仍要适配路由、数据库、附件和任务，共用引擎不能让任意 Node ZIP 自动成为 Worker。

复制参考模块到网站服务端，例如 lib/translation-engine.mjs；调用时传源/目标语言、服务端保护清单、`glossary.entries`、scope 和公开 context。生产环境必须在解析接口/任务层实施权限、持久预算和去重。模块提供可选 `reserveUsage({provider,blocks})` 预算钩子（返回 false 阻止调用）及 `mapWorkersError(error)` SDK 错误映射；这些钩子的模拟测试不等于已实现持久预算。Hy-MT2 默认单并发、60秒超时；其他适配默认并发3、15秒超时。最长单块3000字符、单批50块均是示例值，按目标平台限制调整并记录。

Workers 默认适配器仅处理上述翻译模型。更换模型须提供经过验证的 workersAdapter 与 supportedLanguages，未知 schema 明确失败。模型不能额外接收语境 prompt 时，选择足够完整的语义块和术语约束，并抽查上下文质量。参考模块不持久化任何正文或缓存。

交接记录8种语言及源语言、初始中文覆盖/导入状态、源摘要算法、实际 provider/model、变量与绑定名、块/术语版本、译文/缓存与任务存储、预算及未完成项。模拟、真实引擎、缓存持久化、前台显示分开报告。按 [验收](acceptance.md) 确认后才称已接通。升级 Skill 不自动升级已部署网站。
