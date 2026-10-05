# Cloudflare 目标

业务接口和数据模型保持一致，运行与存储使用 Cloudflare 适配。新工程默认 Workers；经用户工作台部署时优先使用 runtime-profiles.md 的 unified-worker-do-v1；已有 Pages 可保留，不为检查脚本重写可用网站。
工作台新增翻译协议 v2 原生 Worker 路径，当前支持 AI + SQLite Durable Object；旧站仍有部分静态/SUMMIT/豆包/已核对 Node 模板适配，具体边界见 translation-workbench-v2.md。site.contract.json 不会自动让任意后端获得数据库/邮件/AI。分别报告 Cloudflare 工程验证与工作台适配验证，不承诺通用包一键部署。

Workers 工程：
- 完整代码、素材、wrangler.json、依赖锁、迁移和测试；runtime=cloudflare-workers。main 与 assets.directory 必须实际存在，compatibility_date 明确。
- 当前工作台已验证 profile 使用 SQLite Durable Object 保存内容/询盘及分块附件，私密下载需鉴权。D1/R2 等是其他适配路径，不能在未适配时默认生成；直接走 Cloudflare 工具时按相应资源单独验收。列明绑定与迁移，不硬编码真实凭据。
- AI 服务端绑定，邮件 Secret。源码的翻译模块已具备两种引擎，Worker 引导代码注入 env.AI，Wrangler 声明 ai.binding；按 [翻译规范](translation.md) 实现保护、额度与持久缓存，不依赖部署适配器临时改写。Node 兼容开关不等于普通服务器运行环境，不能把本地 SQLite、child_process 构建、长期进程或本地文件写入当持久化。
- 文章返回带正文的 HTML 或采用经验证的原子发布任务，不能指向不存在的构建钩子。
- 后台任务使用平台支持的持久机制，不假设响应结束后定时器继续。
- /healthz、/admin/ 与统一接口一致；敏感响应不进共享缓存。

执行前查当前官方文档、Wrangler 版本、权限、配额和费用。生成包不自动授权发布、付费或DNS变更；无账户可完成本地与模拟测试，但不伪造线上通过。
保留已有 Pages _worker.js/functions 及依赖；不能过滤后端后冒充完整静态成功。本包脚本结构检查 Workers JSON 配置，Pages/JSONC 项目另行验收并写明范围。
默认托管地址、真实域名、trycloudflare 通道分别说明；通道依赖实际运行连接器，不能当成永久域名。
官方核对：https://developers.cloudflare.com/workers/ 、https://developers.cloudflare.com/d1/ 、https://developers.cloudflare.com/r2/ 、https://developers.cloudflare.com/workers-ai/
