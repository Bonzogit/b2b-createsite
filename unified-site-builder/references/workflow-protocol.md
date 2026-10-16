# 工作流事实记录

workflow.json 是执行者填写的事实与证据记录，不是调度器。完整新建或整体改版可使用十阶段记录；局部修改仅记录受影响阶段，不重走整站流程。

阶段为 environment、requirements-content、reference-selection、design-spec、module-components、real-sample、design-review、full-site-motion、acceptance、packaging。执行者与检查者写实际身份；没有独立评审就注明单一执行者，不预设外部工具或虚构协作。

运行 scripts/workflow.py init <project> --skill-version <version> 初始化，set 登记结果，invalidate --topic visual|content|runtime|admin 使受影响结果失效。pass 需非空本地产物或证据；not-applicable 需 skipReason，不能冒充未执行。路径相对 workflow.json，不能越过项目目录；已存在的旧记录不自动重写。

`check` 检查记录结构和 pass 引用的文件存在性，输出明确标注 recordStructurePassed 与 allStagesComplete；默认成功仅代表结构有效。`check --require-complete` 在任一阶段未完成时返回失败，不能用默认退出码宣称全流程通过。文件存在仍不证明内容有效、画面好看或操作成功。

设计研究与核对见 style-selection.md：四个问题足够支撑样板就停止研究；决定与关键用户路径记录在 design-record.json。用 design_check.py 分别检查结构、引用、证据及当前版本记录，不替代浏览器验证。set 的版本号不能证明证据已更新。

修改后仅重验受影响实现及路径，记录新版本、日期、页面、视口、工具和证据。复用未受影响的有效记录；工具失败或看不到画面时保持 unverified，不反复扩大测试。
