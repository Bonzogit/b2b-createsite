# Agent 读取入口

当前规范版本见 [VERSION](VERSION)。本仓库是建站规范、参考数据和离线工具，不是已经接通的后台服务。

## 按任务读取

1. 阅读 [Skill 主入口](unified-site-builder/SKILL.md)。
2. 首次接收阅读 [跨平台交接](unified-site-builder/references/portable-handoff.md)；只要求学习时止于读取和状态说明。
3. 新建网站先阅读 [通用基础框架](unified-site-builder/references/site-foundation.md)，规划网站目标、页面职责、内容、后台管理项和询盘路径。
4. 实际实现时阅读 [业务接口](unified-site-builder/references/business-contract.md)、[后台界面](unified-site-builder/references/admin-ui.md)、[邮件](unified-site-builder/references/resend-email.md)、[翻译](unified-site-builder/references/translation.md)。
5. 阅读 [设计](unified-site-builder/references/design.md)、[参考选择](unified-site-builder/references/style-selection.md) 和 [参考库](site-reference-library/design-library.json)。
6. 按目标读取 [Node](unified-site-builder/references/node-workbench.md) 或 [Cloudflare](unified-site-builder/references/cloudflare.md)，再按 [验收](unified-site-builder/references/acceptance.md) 实现和交付。

明确任务优先，不因读取仓库自动部署、发信或创建网站。旧工程仅修改本次范围，并保留数据。

## 参考库与证据

真实参考库是根目录 `site-reference-library/design-library.json`。Skill 的 `assets/design-library.json` 仅是空白模板。附带记录为公开介绍与分析推断，采用前实看对应演示页面和手机端；无法访问就标明未核验。

可以使用整站参考或模块组合，最终保持品牌协调。标准化的是后台、接口与行为，前台可以不同。

## 接收与交付

首次接收只需简短报告实际读到的版本、参考数量、文件/执行/预览能力以及遗漏项。实际建站时记录 `docs/SITE-BRIEF.md`、`docs/design-record.json`、`docs/API.md`、测试与交接文档。功能实现、服务接通、目标部署和视觉测试分开报告，未验证不得写成通过。

如果只拿到本页，继续读取链接中的配套资源；无法读取就如实说明。

