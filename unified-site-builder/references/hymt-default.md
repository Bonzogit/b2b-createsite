# Hy-MT2 默认翻译基站

新建 Node 工程默认 TRANSLATION_PROVIDER=hymt；Worker 工程 vars 同样指定 hymt，不再默认创建 AI 绑定。用户明确指定其他服务时尊重其选择。引擎选择规则与 translation.md 保持一致。

服务端配置：
- TRANSLATION_PROVIDER=hymt
- TRANSLATION_ENDPOINT=https://43.162.83.155/translation/translate（内置默认，可覆盖）
- TRANSLATION_MODEL=Hy-MT2-1.8B-Q4_K_M（默认）
- TRANSLATION_API_KEY 仅通过工作台环境变量或 Worker Secret 注入。

密钥缺失时状态为 unconfigured，仍读取人工译文、初始中文和本站缓存；部署前复用当前会话安全可用凭据，禁止把密钥、服务器口令或私人连接文件放进 Skill、源码、前端、ZIP 或 GitHub。不同服务器可覆盖 endpoint/model。默认 URL 是可替换的服务配置，不是永久可用承诺。

原生 POST /translate 使用 from/to/text；不依赖模型生成 JSON 数组。品牌、型号、数字、网址和术语在代码中转换为简短保护标记，再严格检查出现次数和恢复值；缺失或重复标记拒绝缓存。默认单并发，每块超时60秒。429 最多重试两次，等待2秒、4秒；不转付费服务。超时后不无界重试。当前引擎的推理锁跨网站限流；客户端退避不等于持久全局队列，大规模同时发布需独立任务队列及容量测试。

保留顺序：当前人工/初始译文 → 有效本站缓存 → 翻译基站 → 检查并持久化。保持源文摘要、术语版本和引擎版本失效规则；不覆盖人工编辑，不改变数据库或附件结构。其他六种语言仍按需生成，不能默认全站预热。按项目需要可在后台预生成指定内容；文章自动翻译及访客异步补译通过 translation-admin.md 的持久队列执行，发布原文不等待译文。

基础检查包含保护标记、重复输出、整段未翻译，以及英译中无汉字或明显残留多个源文单词。这些检查不证明语义准确；材料、否定、金额和专业术语仍需抽查。其它语言需实际验收后再报告质量。qualityVerified 默认仍为 false。

选择 Workers AI：TRANSLATION_PROVIDER=workers-ai，并显式配置 AI 绑定。选择其他标准接口：TRANSLATION_PROVIDER=openai-compatible，配置完整 endpoint/key/model。没有明确 provider 时，完整外部配置优先，之后才尝试已有 AI 绑定；服务失败不自动跨引擎切换。

本版未建立共享翻译记忆库，也不会自动训练模型或抓取最新译法。未来共享库只能收录经人工确认且语言、行业、上下文匹配的译文。

更新 Skill 不自动修改旧网站。旧站按原项目更新流程安装公共核心、接线、注入凭据、验证后切换；保留数据库、术语和人工译文。跨 Agent 分发完整新包。
