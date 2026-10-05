# 可运行后台与两种部署路径

1.6.0 提供 assets/runtime 的可运行基础后台。它实现中文登录与管理界面、产品/分类/页面/文章编辑和发布、联系方式、询盘去重及跟进、公开媒体和私密附件、邮件设置、初始中文/人工译文及按需翻译。复用后按客户业务补齐内容模型、界面和验收；不是已经完成所有客户页面与集成的网站。

## 新建工程

默认服务器：`python <skill>/scripts/create_site.py <空目录> --runtime node --brand <品牌>`。
明确指定 Cloudflare：`python <skill>/scripts/create_site.py <空目录> --runtime cloudflare-workers --brand <品牌>`。

生成器拒绝覆盖非空项目。已有站点先读取实际工程并沿用原项目更新，不重新生成初始数据。示例产品和页面用于部署验收，必须替换成客户的内容、词汇库、完整中文、真实素材及独立设计。默认不为客户同时建立两份独立网站。

两种目标复用 lib/app.mjs、公开接口和翻译核心，仅入口和存储适配不同。修改站点后重新执行结构与真实功能检查。不要绕过核心指纹校验；如需更改公共翻译核心，先升级协议登记。

## 受支持的工作台 profile

本次目标工作台控制端为 1.13.0，已经安装 profile 检查、服务器初始账号与后台入口、原生 Worker 上传及更新适配。仅升级 Skill 不会自动升级其他工作台；其他服务器先核对其适配能力，再上传。Node 项目卡显示“管理后台”和“初始账号”。Cloudflare 必须生成相应 Worker 包，不直接把 Node 包上传为 Worker。

|profile|入口|持久存储|工作台处理|
|---|---|---|---|
|unified-node-v1|server.mjs|DATA_DIR 的原子 JSON 文档；UPLOADS_DIR 文件|容器监听 0.0.0.0，挂载 /data 与 /uploads，首次生成私密后台密码|
|unified-worker-do-v1|worker.mjs|SQLite Durable Object；附件分块存储|SITE/ASSETS/AI 绑定，首次 SITE_ADMIN_PASSWORD Secret|

当前基础实现适合单站、小型内容库及每个5 MB以内的附件。Node 单进程串行写入；Worker 数据与文件使用 SQLite 同步事务。不要把它作为已验证的大规模数据库或多进程共享文件方案。

Cloudflare 资源目录允许 public 或 ./public，工作台归一化为 ./public。普通 vars 保留；密钥/密码放 Secret。WorkBench 管理 Worker 名称、账户和域名，不从包中接收账号凭据。D1/R2/KV/Queues 等属于其他 profile，使用前另行适配；不能按泛泛的 Cloudflare 建站建议生成这些绑定后直接上传。

参考后台没有第三方运行依赖，解决自动安装和构建差异。自选框架的 npm 依赖与构建在受信任的开发环境完成，上传自包含 Worker 和 public 成品；不上传 node_modules，不声明上传时执行 build/安装脚本。服务器包仍可按服务器工作台的既有依赖安装规则处理。包检查通过不代表所有框架已兼容。

## 数据与账号

初始内容和中文只首次导入；升级不覆盖数据库、账号、人工译文、询盘、媒体和附件。首次没有密码时后台锁定，部署过程中补入 Secret 后只初始化缺失账号。已存在账号不会被首次密码变量重置。

Cloudflare 更新保留对象类 UnifiedSite、对象绑定 SITE、对象名 main 和既有迁移。需要更改存储或迁移时先制定迁移和恢复流程，不把拒绝变化的保护去掉。Node 更新保留原项目 /data、/uploads 与账号。

Node 使用外部翻译引擎配置；Cloudflare 使用 AI 绑定。无引擎时当前中文及人工译文可读，缺失内容准确返回 unconfigured。AI/机器词汇未经语言审核不能声称高质量翻译。邮件默认关闭，询盘照常保存；外部发件域名、送达回调及邮件质量仍需实际配置和单独验收。

## 功能与升级验收

先运行 site_package.py check，再通过正常工作台上传。用独立验收项目执行 e2e_site.mjs；要求 SITE_TEST_ORIGIN、私密 SITE_TEST_PASSWORD 和 SITE_E2E_ALLOW_WRITE=1。脚本会写测试内容，只能用于明确的隔离项目。

检查公网首页/后台、权限与来源/CSRF、草稿隔离、发布/更新/下架、询盘去重、附件鉴权、公开媒体、联系方式同步、初始中文、人工优先和过期原文拒绝。随后在原项目升级并重启，核对原账号、测试内容、私密附件、媒体和翻译缓存仍可读。真实 Workers AI 与服务器外部引擎状态、邮件发送、语义质量及浏览器画面分别记录，不把模拟检查当线上验收。
