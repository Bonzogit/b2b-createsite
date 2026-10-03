# Agent 读取入口

当前规范版本见 [VERSION](VERSION)。本仓库是建站规范、参考数据和离线工具，不是已经接通的后台服务。

## 按任务读取

完整建站顺序：**基础框架 → 参考设计 → 图片准备与生成 → 页面和功能实现 → 实际验收 → 打包交付**。基础框架先确定各页面内容深度；正常资料与工具条件下完成这些步骤，不把读过规范视为已完成实施。

1. 阅读 [Skill 主入口](unified-site-builder/SKILL.md)。
2. 首次接收阅读 [跨平台交接](unified-site-builder/references/portable-handoff.md)；只要求学习时止于读取和状态说明。
3. 新建网站先阅读 [通用基础框架](unified-site-builder/references/site-foundation.md)，规划网站目标、页面职责、内容、后台管理项和询盘路径。
4. 确定运行目标，读取 [Node](unified-site-builder/references/node-workbench.md) 或 [Cloudflare](unified-site-builder/references/cloudflare.md)，以及 [业务接口](unified-site-builder/references/business-contract.md)、[后台界面](unified-site-builder/references/admin-ui.md)、[邮件](unified-site-builder/references/resend-email.md)、[翻译](unified-site-builder/references/translation.md)。
5. 阅读 [设计](unified-site-builder/references/design.md)、[参考选择](unified-site-builder/references/style-selection.md)、[Blocksy 参考库](site-reference-library/design-library.json) 和 [CKCC 企业站候选](site-reference-library/ckcc-b2b-candidates.json)。
6. 按 [图片制作](unified-site-builder/references/visual-production.md) 准备或生成实际素材，先实现并查看带素材的首页与详情样板，再扩展全站。
7. 按 [验收](unified-site-builder/references/acceptance.md) 完成实际检查、修正和交付。

明确任务优先，不因读取仓库自动部署、发信或创建网站。旧工程仅修改本次范围，并保留数据。

## 参考库与证据

根目录 `site-reference-library/design-library.json` 保存 45 条 Blocksy 来源记录；`site-reference-library/ckcc-b2b-candidates.json` 保存 37 条企业站候选与预览链接。Skill 的 `assets/design-library.json` 仅是空白模板。CKCC 目录和部分演示站 HTML 已核对，实际视觉尚未核验；采用前查看对应演示页面和手机端，确认内容与目录标签一致。无法访问就标明未核验。

可以使用整站参考或模块组合，最终保持品牌协调。标准化的是后台、接口与行为，前台可以不同。

## 接收与交付

首次接收只需简短报告实际读到的版本、参考数量、文件/执行/预览能力以及遗漏项。实际建站时记录 `docs/SITE-BRIEF.md`、`docs/design-record.json`、`docs/API.md`、测试与交接文档。功能实现、服务接通、目标部署、内容与素材完成度和视觉测试分开报告，未验证不得写成通过。

如果只拿到本页，继续读取链接中的配套资源；无法读取就如实说明。
