# 翻译核心与工作台协议 v2

默认服务及引擎选择以 [Hy-MT2 接入](hymt-default.md) 为准；Workers AI 仅在明确选择时启用。


本版本将服务器已验证的型号修复合入公共引擎，新增 resolver、明显重复输出检查和包检查。当前 skillVersion=1.6.5、translationContract.version=2；具体文件指纹见 assets/translation/core-manifest.json。

## 各 Agent 的执行入口

分发完整 skill 文件夹，保留 references、assets、scripts 相对路径。豆包、WorkBuddy、Claude Code 等从 SKILL.md 读取；平台专用元数据不是必需入口。记录宿主能否写文件、执行检查和预览。没有运行证据时不能报告通过。

在已有项目中运行 `python <skill-dir>/scripts/install_translation.py <project>` 安装公共模块、写入文件指纹，保留已有词汇库与中文数据。安装完成不等于接通；必须继续接线及验收。旧站改动前保留数据与恢复路径。

## 接线

复制的 lib/translation/resolver.mjs 导出 createTranslationService。每站独立创建实例，传 siteId、统一 languages、sourceLanguage、runtime、repository、glossary、结构化品牌/型号清单。源码、菜单、后台设置、接口都使用这份 languages；不维护额外硬编码列表。

runtime：Worker 传 env 与所选引擎需要的绑定，Node 传服务端 env；Hy-MT2 在两种平台均使用服务端密钥，Workers AI 仅在明确选择时传 AI:env.AI；必须提供持久预算 reserveUsage。示例限制不是免费额度保证。不得在供应商失败后静默转付费接口。

repository 必须实现 getContent、getAuthored、getCached、putCached、withLock、getEngineIdentity、putEngineIdentity。getContent 只返回本站已发布内容，含 status/revision/kind/context/blocks；每块含稳定 id/text/context。withLock 使用持久任务协调、租约与恢复，同一站点跨实例去重；回调完成后释放，任务正在执行可返回 undefined。数据库和附件由本站存储实现，resolver 不冒充数据库。

getAuthored 返回本站初始/人工译文。初始中文按实际全部初始块生成 seed/translations.zh.json，使用 seed.mjs 的源摘要规则。重启/升级不覆盖管理员内容。词汇库 config/translation-glossary.json 使用 translation.md 的条目格式，传 glossary.entries，不能只传 glossaryVersion 或 protectedTerms。

正文、导航、按钮、表单、标题、图片说明都应有可翻译的块或有效人工译文。前台捕获过期请求；失败保留原文并显示简短状态。明显重复输出被拒绝，不缓存为成功；qualityVerified=false 是默认，不能据 ready 宣称译文合格。每个启用语言抽查首页、代表产品、文章、询盘及术语，记录审核语言/块/当前源摘要。机器词汇和模型输出未经审核时明确标记。

## 工作台支持边界

Ubuntu 默认走原 Node 工作台路径，外部翻译服务需实际配置；Node 无法直接读取 Worker 的 env.AI。指定 Cloudflare 时生成原生 Worker 包：根目录 site.contract.json、wrangler.json、完整源码/公共模块、public/、锁文件、词汇库和初始中文。

工作台新增 v2 原生路径当前接受 SQLite Durable Object 包，按所选引擎注入 Secret 或 AI 绑定；1.6 的可运行 profile 见 runtime-profiles.md，保留声明的对象类与迁移。统一入口 /healthz、/admin/、匿名 /api/v1/admin/overview 返回401；后台首次账号读取 SITE_ADMIN_PASSWORD。需要 D1/R2、其他资源或额外绑定时先明确适配，不转为静态发布。不要把普通 Node 工程改个 runtime 字段就当 Worker。

旧包仍走已核对的旧模板兼容路径；旧包部署成功不等于通过 v2。原项目更新使用工作台待验证版本→检查→正式切换→失败回滚流程。存储或迁移声明变化时停止更新，要求明确迁移；不重新创建项目。

## 必跑检查

- `python <skill-dir>/scripts/site_package.py check <project>` 检查词汇/中文文件、语言配置与公共模块指纹；结构通过仍不证明运行接线。
- `node --test <skill-dir>/assets/translation/test_engine.mjs <skill-dir>/assets/translation/test_seed.mjs <skill-dir>/assets/translation/test_resolver.mjs` 验证公共代码。
- 项目端到端验证真实语言切换、行业术语、重复型号、源文修改、人工译文优先、换浏览器及重启缓存；调用计数证明缓存命中。真实译文质量独立报告。

交接中记录 skill/core/glossary/协议版本和部署目标。当前安装 skill 不会改变旧网站或其他 Agent 已下载的包；跨平台重新分发完整新包。

Workers AI 分支将品牌、型号、数字和指定词汇保留在代码中，只把其余文本片段交给模型，随后按原顺序拼接。片段翻译仍可能影响语句流畅度，需进行目标语言人工复核。
