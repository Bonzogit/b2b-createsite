# 业务与接口

## 后台、接口和展示站的分工

- 管理后台统一：中文界面、菜单命名、字段含义及发布/跟进/配置流程保持一致，按业务启用模块。已有用户认可且验证过的后台组件应复用，不随前台风格重新设计一套管理习惯。
- 业务接口统一：新工程遵循下方 /api/v1 的路径、请求字段、返回结构与状态定义；邮件、WhatsApp、文章和翻译沿用同一业务规则。各项目在 docs/API.md 记录实际实现和接口版本，不能只有规范没有实现。
- 展示站独立：首页构图、导航、内容顺序、列表与详情版式、字体、颜色、图片及交互可以不同。前台呈现层负责把标准内容变为品牌页面，不直接持有 Resend 等服务凭据，也不另实现与后台冲突的业务状态。
- 运行环境适配：Node 与 Cloudflare 可以用不同存储和发送适配器，对前台保持相同接口语义。翻译复用公共核心的 Hy-MT2、Workers AI 和 OpenAI 兼容适配，通过显式配置及兼容规则选择，见 [按需翻译](translation.md)；部署配置绑定与变量，不为单个项目改写翻译逻辑。用到兼容接口时记录映射；增加字段优先向后兼容，破坏性变化另起版本并说明迁移方式。
- 每站配置独立：发件身份、收件邮箱、WhatsApp、语言与品牌资料由对应站点后台配置。统一接口不等于全部网站共用账号、数据库、密钥或客户询盘；未经明确要求不改成多站集中后台。

验收时至少覆盖：修改联系方式后前台入口同步；文章发布后列表与详情更新；询盘先保存再处理邮件；语言切换按统一规则读取或生成译文。换前台主题不得破坏这些行为。优先验证实际结果，不以接口名称一致代替功能验收。

## 内容与管理

后台 /admin/，界面中文。默认英文源内容、完整初始中文译文和 en/zh/es/ar/ru/fr/de/pt 8种语言选项；其余6种语言按需生成。用户可以指定其他源语言。初始中文按稳定块及源摘要关联；新增/改文缺失中文也调用统一翻译接口并缓存，见 translation.md。产品/服务、分类、页面、文章、媒体、询盘、联系设置、翻译状态与账户按业务启用。不为服务网站硬套工厂或库存字段。

文章字段：id、slug、title、summary、body、cover、categoryId、tags、author、sortOrder、pinned、status、sourceLanguage、revision、createdAt、updatedAt、publishedAt。富文本用结构化块或经服务端白名单清洗的 HTML，不执行存储脚本。支持草稿、鉴权预览、发布、修改、下架、排序与删除确认。

公开内容有稳定 ID 和版本。发布成功表示列表与详情已读取新版本；可服务端渲染或生成 HTML。需要构建时先生成并验证候选版本再切换，不能清空正在服务的目录。下架使列表、详情、搜索、sitemap 与公开缓存同步失效。
页面地址、导航和站点地图来自同一个内容/路由模型。新工程默认 /products/、/products/<slug>/、/articles/、/articles/<slug>/；旧工程保留稳定路径或提供重定向。

## 联系方式

统一 settings.contact：displayEmail、notificationRecipients、whatsappNumber、address、businessHours；发信身份和密钥单独放服务端集成配置。修改一次所有入口同步。
WhatsApp 使用经校验的国际号码生成 wa.me，预填产品名称、型号、页面链接并 URL 编码，不带访客隐私和附件。号码为空隐藏按钮，保留站内询盘。打开 WhatsApp 或 mailto 不代表已发送，也不代表站内收到询盘。

## 询盘和邮件

默认邮件提供商为 Resend。必须提供“后台 → 设置 → 邮件通知”，配置字段、密钥保存、域名验证和测试流程见 resend-email.md；不能只给环境变量说明而省略后台设置。

请求含 submissionKey；服务端唯一约束去重。先验证并持久化询盘和有效附件，再返回 inquiryId。相同 key 重试返回已有结果，不同内容使用同 key 则拒绝。任务唯一键防止重复通知。
记录客户联系方式、需求、产品 ID/型号快照、必要来源、createdAt、inquiryStatus、emailStatus。按实际隐私配置收集来源，不自动采集无关个人信息。
邮件状态独立：unconfigured、queued、sending、submitted、failed；submitted 只表示服务商接受。送达回调必须验签后另记 delivered/bounced。失败不能丢询盘，支持有限重试及管理员重试。客户确认邮件单独配置，默认不发敏感附件。
无邮件也可收单。基础防滥用含校验、长度限制、蜜罐、限速、去重；强制验证码仅在明确启用并配置后使用，验证失败不绕过。
默认附件 PDF/JPG/PNG，单个 5 MB、一次一个，可按需求调整。校验实际类型/路径/大小，后台鉴权下载；随机文件名不是鉴权。公开媒体与私密附件分开。询盘支持跨设备查看、备注、跟进、过滤和导出，CSV 防公式注入。
成功页仅在保存后进入；可选统计按询盘编号去重，不传个人信息。

## 新工程接口 v1

这些是网站应实现的接口，不是工作台已有服务。旧工程可加兼容层，不删在用接口。
前缀 /api/v1；返回 {ok:true,data:...} 或 {ok:false,error:{code,message}}，HTTP 状态与结果一致。管理写操作必须鉴权、CSRF 与来源检查；不泄漏内部配置。

| 路径 | 行为 |
|---|---|
| POST/GET/DELETE /session | 登录、查询和退出 |
| POST /admin/password | 核验旧密码、修改、撤销旧会话 |
| GET/PUT /admin/settings | 集中配置，不返回已有密钥明文 |
| GET/POST /admin/articles | 列表、创建草稿 |
| GET/PATCH/DELETE /admin/articles/:id | 管理文章，版本冲突保护 |
| POST /admin/articles/:id/publish | 发布并返回真实版本/任务状态 |
| POST /admin/articles/:id/unpublish | 下架及失效缓存 |
| GET /articles、/articles/:slug | 只读已发布内容 |
| POST /inquiries | JSON/multipart，返回询盘编号 |
| GET /admin/inquiries、/admin/inquiries/:id | 查询询盘 |
| PATCH /admin/inquiries/:id | 跟进和备注 |
| POST /admin/inquiries/:id/retry-email | 有限重试通知 |
| POST /admin/media | 管理员上传公开媒体 |
| GET /admin/attachments/:id | 鉴权下载 |
| POST /translations/resolve | 查询/请求已发布版本的翻译 |

产品/分类按相同资源风格实现；公开页面可以服务端渲染，不强制通过浏览器 API 才阅读。

翻译接口沿用请求 `{contentId,revision,targetLanguage,blockIds?}` 和返回 `{ok:true,data:{status,sourceLanguage,targetLanguage,revision,blocks,retryAfterMs}}`。兼容新增可选 `reasonCode` 和脱敏 `engine:{provider,configured,model,engineVersion,glossaryVersion}`；provider 为 hymt/workers-ai/openai-compatible/unconfigured，不返回凭据。状态仍为 ready/partial/pending/unconfigured/failed，准确语义、稳定块 ID 与术语结构见 translation.md。配置完整不等于真实引擎验收；翻译服务端只读取本站已发布内容，来源与权限错误使用相应 HTTP 状态。

## 账号与数据

标准密码哈希、限速、过期与可注销 HttpOnly 会话；HTTPS 使用 Secure，本机 HTTP 开发明确区分。无初始密码时后台锁定，禁止抢注。升级时不重置密码。
数据事务或等价原子操作防并发丢失；迁移有版本且可恢复。草稿、账户、询盘、附件不进公开缓存或翻译。导出内容不等于完整备份，备份含一致数据与文件并在隔离环境恢复验证。
