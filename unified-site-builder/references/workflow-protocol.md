# 工作流事实记录

workflow.json 是进度与证据记录，不是自动调度器，也不能证明画面质量。完整新建或整体改版使用；小范围修复只记录受影响阶段，不要求重走全程。

真实阶段 ID：environment、requirements-content、reference-selection、design-spec、module-components、real-sample、design-review、full-site-motion、acceptance、packaging。每阶段状态 pass / fail / unverified / blocked / not-applicable。pass 需要产物或证据；not-applicable 要写 skipReason。阶段不适用与尚未执行不能混用。

运行 scripts/workflow.py init <project> --skill-version <version> 初始化；set 记录实际结果；invalidate --topic visual|content|runtime|admin 使相关检查失效；check 核对记录结构。确切参数以 --help 为准。修改视觉、内容或运行代码后重新核对受影响样板、评审与验收，保留历史证据。

更换执行者先读取真实代码、HANDOFF 和证据，不能把旧 pass 当成本次已验证。没有独立评审者时如实记录单一执行者。
