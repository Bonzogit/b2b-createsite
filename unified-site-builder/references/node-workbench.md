# Node / 普通服务器工作台

基于用户工作台当前已验证的 Node 协议；工作台变化时核对实际约定。Skill 安装不修改工作台。
新建优先采用 runtime-profiles.md 的 unified-node-v1 基础后台，工作台首次生成后台密码，并在原项目更新时保留账号。
根目录包含 package.json、package-lock.json、deploy.json、site.contract.json、server.mjs、lib/、public/、tests/、docs/。业务模块可细分。
默认 type=module、npm start=node server.mjs，Node 22 兼容；需要更高小版本时明确并核实目标环境。交付前生成公开页面，默认部署不 build。文章发布依赖的构建工具必须实际在运行环境中，不假设 devDependencies 始终存在。
复制 assets/deploy.node.json 为 deploy.json，不发明工作台未支持的自动建库或安装模型字段。

运行变量：
- HOST 默认 0.0.0.0；PORT 默认 3000，由环境注入。
- DATA_DIR（兼容 SITE_DATA_DIR）与 UPLOADS_DIR 保存所有持久内容/媒体/附件；工作台挂载 /data、/uploads。开发目录在公开目录外。
- SITE_ORIGIN，兼容 SITE_URL / PUBLIC_SITE_URL，运行时影响 canonical、sitemap、绝对链接和来源校验，不能只在构建时写死。
- SITE_ADMIN_USER 默认 admin，SITE_ADMIN_PASSWORD 仅首次初始化，建议随机至少16位；没有密码则锁定后台。
- /healthz 无登录返回200简短 JSON，不依赖外部服务。
- 仅信任明确配置代理，例如 TRUSTED_PROXY_IP，不无条件信任转发头。

选用与实际运行环境兼容的 SQLite 或事务安全文件存储。SQLite 放 DATA_DIR；一致备份需处理 WAL/快照，不能随意复制正在写入的单个文件。
邮件与翻译放服务端配置，未配置不阻断浏览、后台和收单，状态如实显示。翻译模块复用公共核心和运行时注入。新工程默认 TRANSLATION_PROVIDER=hymt，使用默认原生地址/模型，TRANSLATION_API_KEY 由服务端注入；地址/模型可覆盖。明确选择 openai-compatible 时配置完整 HTTPS Chat Completions 地址、密钥和模型；Workers AI 仅适用于实际具备 AI 绑定的环境。缓存/任务放持久数据目录，详见 [翻译规范](translation.md)，不在浏览器中保存服务密钥。
ZIP <=120 MiB，解压 <=600 MiB / 20,000 文件；不含依赖、密钥、运行数据、数据库、私人附件和符号链接。公开初始素材可包含。
新 ZIP 上传通常创建新站，不自动等于升级原站；升级指定目标、备份并沿用持久化目录。隧道由工作台负责，网站不自行启动 tunnel。
可访问实际包检测器时实测，否则写“离线结构通过，未实际部署”，不能声称工作台已验收。

临时代理与正式域名的来源配置及页面源块一致性按 [翻译规范](translation.md#页面源块与入口一致性) 核对；GET 首页可访问不证明翻译 POST、后台保存或询盘成功。换域名后验证相关写接口，保留精确来源校验。

## 后台翻译调度

共享任务记录保存在既有 DATA_DIR，进程启动读取待办并恢复唤醒；计时器只是执行器。按 [后台翻译任务](translation-admin.md)验证重启、失败重试及改文失效，不复制另一份数据目录或将任务放在浏览器内。
