# 设计与建站的共同接口

机器入口为 `assets/interface-contract.json`。builderVersion 是生成工具版本；项目发布版本独立填写在设计记录、验收报告和部署环境 SITE_RELEASE 中，不能用工具版本冒充网站版本。接口有破坏变化时更换对应接口版本，不能只提升 Skill 补丁号。旧项目不因安装新 Skill 自动迁移。

| 边界 | 维护方与实际约定 |
|---|---|
| 策划与布局 | 设计 Skill 写 SITE-BRIEF、DESIGN、design-spec、MODULES；建站承接关键路径与样板范围，技术约束发生变化时回写决定 |
| 可编辑内容 | 建站内容模型为准。title/summary/body/highlights/specs/faqs/gallery/options 必须接后台及保存接口；新增字段先扩展模型、校验、后台和翻译块，再画控件。组件自己的 state 不当成业务数据库 |
| 主题 unified-theme-v1 | lib/theme.mjs 导出 createRenderer()，返回 null 或 {render(ctx)}；render 返回完整 HTML，可使用 ctx.document({...ctx,main}) 保留壳层。ctx 有 lang/dir/query/selected/items/products/articles/categories/escape/renderBlock，不暴露 db/env/storage/询盘/会话。没有全站 pages 数组；跨页内容先核对解析覆盖，不能假设 ctx.blocks 含所有内容 |
| 翻译 | 内容通过 ctx.renderBlock('product:ID','ID#title') 等稳定块呈现，属性值使用 ctx.escape；保留 /assets/site.js、语言选择 #language、翻译状态和重试。当前参考核心的源语言基线为 en，初始中文使用 authored seed；不能只把 settings.sourceLanguage 改为 zh 就宣称中文源语言全链路可用。新源语言须另行验证散列、手动译文、队列和前台 |
| 询盘 unified-inquiry-v1 | POST /api/v1/inquiries，JSON 或 multipart；name/email/message 必填，productId/file/website 可选，submissionKey 必须稳定。同 key 不同核心内容返回冲突。额外预算、用途等字段先有保存模型，或在前台明确组合进 message，不能假设后台自动保存未知字段 |
| 表单回调 | import {createInquirySubmit} from '/assets/inquiry-adapter.js'；submit 接收普通 values 对象及 {signal,key}，返回 {id,status:'saved',emailStatus}。API 原始返回 {ok:true,data:{inquiryId,emailStatus}}；入库成功与邮件成功分别判断。重试沿用 key，编辑核心内容换 key；文件只接 file 字段，限 PDF/JPEG/PNG、5MB，并校验文件头；修改附件也须换 key，不能用 JSON.stringify(File) 判定附件变化，现有幂等指纹不包含附件。不要给同一 form 同时挂核心 #inquiry 处理器和第三方处理器 |
| 数据与部署 | 后台带会话、CSRF、revision 检查；主题与外部组件不持有密钥。沿用原数据库/附件/账号及部署目标，不能为了新布局换成实验室后端或新数据库 |

## 设计记录 2.0

`references[].observations` 是非空字符串，不能填数组；已观察来源需 observedAt、viewport、非空本地 evidence。researchStatus=pass 需四个 designQuestions 字符串。decisions 与 journeys 的 verification.status 为 pass/fail/unverified；通过需当前 projectVersion、页面、视口、日期和实际证据。路径相对工程根，用正斜杠，不允许绝对路径或 `..`。

策划完成时 verification=unverified、implementation=[] 可以合法存在；不伪造截图占位。使用 scripts/design_check.py 检查结构；实现后按当前版本补证据。验收报告仍使用独立 schema：它的 not-applicable 需理由，不直接搬进设计 verification；设计 checkedAt 对应验收 observedAt，项目版本和证据可引用同一实际检查。任一工具结构通过不代表视觉质量通过。
