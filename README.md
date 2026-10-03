# Unified Site Builder

为不同 AI Agent 提供同一套 B2B 询盘网站建设规范：**先规划基础内容，后台与接口统一，展示站按品牌设计。**

A portable specification, reference catalog, and offline package checker for AI-built B2B inquiry websites.

当前版本：**1.3.0**。完整读取入口：[AGENT_ENTRY.md](AGENT_ENTRY.md)。

## 它提供什么

- 通用建站框架：首页、产品或服务、企业能力、合作流程、文章和询盘等内容职责与内容深度。
- 按基础框架、参考设计、图片准备与生成、页面实现、实际验收的顺序完成网站。
- 中文真实后台约定、业务数据与接口协议。
- Resend 邮件通知、WhatsApp、文章发布、按需翻译与缓存规则。
- Node 工作台及 Cloudflare 的不同部署要求。
- 整站参考或多个网站模块组合的设计方法。
- 45 条 Blocksy 官方模板介绍索引，以及离线包结构检查和打包工具。

本仓库提供规范、模板和检查工具，**不包含已实现的通用 CMS、现成主题库或云端服务凭据**。生成结果需要功能、视觉和部署验收。

## 给其他 Agent 使用

把仓库链接发给 Agent，并告诉它：

> 请读取此仓库的 AGENT_ENTRY.md，按其中顺序读取 Skill、通用基础框架和参考库。先确认实际读到的版本与能力边界，再按我的具体任务执行。先按基础框架规划丰富且有依据的内容，再根据产品参考一个或多个网站，准备或生成实际图片，实现页面和统一后台，最后实际查看并验收。不能只看 README 就声称已读完规范。

如果 Agent 只能读附件，可下载仓库 ZIP 并解压。支持原生 Skill 的工具可安装 `unified-site-builder/`，同时保留同级参考库或另行指定位置。没有文件或执行能力时应说明未完成的范围。尚未在所有 Agent 平台实测导入。

开始建站只需补充产品/业务、已有资料和特殊要求；没有明确部署目标且无法从上下文判断时，使用 Skill 中的 Node 默认。延续旧工程必须先读取该项目的实际源码与交接文档。

## 目录

| 路径 | 用途 |
|---|---|
| [AGENT_ENTRY.md](AGENT_ENTRY.md) | Agent 首次读取入口 |
| [unified-site-builder/SKILL.md](unified-site-builder/SKILL.md) | Skill 主规范 |
| [基础框架](unified-site-builder/references/site-foundation.md) | 页面职责、内容、询盘方向 |
| [图片制作](unified-site-builder/references/visual-production.md) | 素材规划、实际生成与页面验证 |
| [业务接口](unified-site-builder/references/business-contract.md) | 后台、接口及数据行为 |
| [参考库](site-reference-library/design-library.json) | 45 条候选与来源链接 |
| [中文参考目录](site-reference-library/参考库总览.html) | 下载后可在浏览器打开的目录 |
| [验证范围](VALIDATION.md) | 已检查与未验证的边界 |
| [更新记录](CHANGELOG.md) | 版本变化 |

## 为什么能统一又有不同风格

基础框架说明网站应帮助客户完成什么任务。后台和业务接口说明这些功能怎样工作。参考网站帮助决定外观、信息组织与交互。

可以整站参考一个网站，也可以首屏、品牌故事、文章等模块分别参考不同网站，再统一字体、配色、间距和组件。商店模板可以用于外观及非商店页面参考；默认交付询盘站。参考不会自动授权复制对方品牌、商业事实或素材。

## 本地检查

Python 3.11+，检查器仅使用标准库，不执行目标网站代码、不联网：

```text
python -m unittest discover -s unified-site-builder/scripts -p "test_*.py" -v
python unified-site-builder/scripts/site_package.py check /path/to/website
python unified-site-builder/scripts/site_package.py pack /path/to/website --output /path/outside/website.zip
```

结构通过不能替代真实后台、询盘保存、邮件收件、翻译和上线测试。

## 版本与共享

`main` 是持续更新的内容。需要复现某次建站时，记录当时的提交 SHA、Skill 版本和参考库版本。拉取更新不自动升级已有网站；参考库的个人补充与项目历史需要合并保留。私有项目数据和凭据不要提交到公开仓库。

## 许可与来源

本项目原创代码和文档按 [MIT License](LICENSE) 提供。模板品牌、外链素材和第三方作品仍归各自权利人；详见 [第三方来源说明](THIRD_PARTY_NOTICES.md)。仓库不分发 Blocksy 的主题、图片、字体、演示站源码或付费插件。
