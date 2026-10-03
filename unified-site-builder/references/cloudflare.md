# Cloudflare 目标

业务接口和数据模型保持一致，运行与存储使用 Cloudflare 适配。新工程默认 Workers；已有 Pages 可保留，不为检查脚本重写可用网站。
现有工作台 Cloudflare 流程只有部分静态/SUMMIT/豆包模板适配。site.contract.json 不会自动让任意后端获得数据库/邮件/AI。分别报告 Cloudflare 工程验证与工作台适配验证，不承诺通用包一键部署。

Workers 工程：
- 完整代码、素材、wrangler.json、依赖锁、迁移和测试；runtime=cloudflare-workers。main 与 assets.directory 必须实际存在，compatibility_date 明确。
- 用合适的 D1 或 SQLite Durable Object 保存内容/询盘，媒体/附件使用适当持久存储并隔离访问；列明资源绑定与迁移，不硬编码真实凭据。
- AI 服务端绑定，邮件 Secret。Node 兼容开关不等于普通服务器运行环境，不能把本地 SQLite、child_process 构建、长期进程或本地文件写入当持久化。
- 文章返回带正文的 HTML 或采用经验证的原子发布任务，不能指向不存在的构建钩子。
- 后台任务使用平台支持的持久机制，不假设响应结束后定时器继续。
- /healthz、/admin/ 与统一接口一致；敏感响应不进共享缓存。

执行前查当前官方文档、Wrangler 版本、权限、配额和费用。生成包不自动授权发布、付费或DNS变更；无账户可完成本地与模拟测试，但不伪造线上通过。
保留已有 Pages _worker.js/functions 及依赖；不能过滤后端后冒充完整静态成功。本包脚本结构检查 Workers JSON 配置，Pages/JSONC 项目另行验收并写明范围。
默认托管地址、真实域名、trycloudflare 通道分别说明；通道依赖实际运行连接器，不能当成永久域名。
官方核对：https://developers.cloudflare.com/workers/ 、https://developers.cloudflare.com/d1/ 、https://developers.cloudflare.com/r2/ 、https://developers.cloudflare.com/workers-ai/
