# 辅助能力接入（aux-capabilities）

辅助能力只负责设计建议、评审与素材，**不负责**需求、内容、真实资料边界、后台维护、接口、多语言、部署与整体调度 —— 这些始终由主 Skill 负责。任何能力不可用时如实记录，不虚构调用成功。

判定接入是否完成的标准是**能否重复调用并留下输出文件**，而不是克隆成功或读过文档。

## 使用边界

辅助能力按需使用，不是每次建站的必经清单。通过适配脚本的 --source 等参数指定已安装来源，不能假定某台电脑目录存在；缺失如实记录，可继续不依赖它的工作。来源提交号是本次合并所依据的历史记录，未来实际使用需记录实际版本，不代表当前最新或已在目标宿主接通。

## 四个能力的接入方式

| 能力 | 角色 | 接入形态 | 接入命令 | 状态判定 |
|---|---|---|---|---|
| UI/UX Pro Max | 设计检索 → 规格 | 脚本（调其真实 `cip/search.py`） | `python <skill>/scripts/aux-adapters/pro_max_search.py --query "<行业词>" --domain industry --out <项目>/docs/aux-calls/pro-max-industry.json` | 退出码 0 且有可审查结果（0条结果不代表设计建议有效） |
| Impeccable | 页面评审 | CLI 二进制（`detect`，60 条确定性规则，无需 API key） | `python <skill>/scripts/aux-adapters/impeccable_detect.py <页面或目录> --out <项目>/docs/aux-calls/impeccable-detect.json` | 退出码 0/3 且 JSON 有 `findings` |
| GSAP Skills | 动效指导 | 运行时（把 `gsap.min.js` 装进项目） | `python <skill>/scripts/aux-adapters/gsap_setup.py --project <项目> --out <项目>/docs/aux-calls/gsap-runtime.json` | 退出码 0 且 `public/assets/vendor/gsap.min.js` 存在 |
| Galaxy | 组件素材库 | 资源库（取具体组件文件） | `python <skill>/scripts/aux-adapters/galaxy_pick.py --category Cards --list 20` 或 `--name <文件>` 复制进项目 | 退出码 0 且组件文件已落到项目 |

退出码 **2 一律表示能力未接通**（源缺失 / 二进制缺失 / 运行时缺失）。此时必须在 `workflow.json` 记 `available: false`，仅在它是本任务必要条件且无可行替代时在 `blocks` 登记，**不得记作调用成功**。

## 版本与许可证（实际核对）

| 能力 | 来源 | Commit | 许可证 |
|---|---|---|---|
| UI/UX Pro Max | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill | `477bcb28c9812b385cb51a4605ddf30d7b2266e2` | MIT |
| Impeccable | https://github.com/pbakaus/impeccable | `cf3d2fa07d3ad1814ac5fbbbb5b2043b795eaef1` | Apache-2.0 |
| GSAP Skills | https://github.com/greensock/gsap-skills | `aed9cfd3277740755f6bfc1155c7aa645403b760` | MIT |
| Galaxy | https://github.com/uiverse-io/galaxy | `adbd2adde0a299a3956ea288fb444ec01891ca41` | MIT |

Impeccable CLI 自身版本 `4.0.0`（`impeccable --version`），引擎 `0.1.11`，指令 `4.5.0`。

## 各能力的实际边界

### UI/UX Pro Max

- **真正调用的是** `.claude/skills/design/scripts/cip/search.py`（纯 Python 标准库），四个检索域：`industry` / `style` / `deliverable` / `mockup`。
- 返回结构化数值：主色、辅色、字体取向、交付物、mood、最佳实践、避免项。这些数值需按当前产品审查后才进入 `docs/design-spec.json`。
- 仓库里的 `cli/` 是 TypeScript，需要 bun 且依赖 playwright，**未接入**；本工作流不依赖它。
- 行业库是固定分类（Technology / Hospitality / Fashion / Retail / Manufacturing / Sports Fitness 等）。**没有的分类会返回 0 结果**，此时必须如实记录"该行业无匹配"，改取相邻分类或写明原创依据，不得凭印象编造检索结果。

### Impeccable

- CLI 的 `detect` 可离线运行，扫描 HTML/CSS/JS 的 UI 反模式（实测可检出 `low-contrast` 等）。这是**工具实际执行**的部分。
- 24 条指令（`critique` / `audit` / `polish` / `harden` / `animate` …）是**指令文档**，由 Agent 阅读后执行；执行了哪些、改了哪些必须写进 `docs/REVIEW.md`，并区分"检测器发现"与"Agent 按指令判断"。
- 二进制来自 npm 包 `@impeccable/cli-windows-x64`；缺平台包时脚本返回退出码 2。
- Live Mode / 浏览器扩展**不依赖**，本轮未使用。

### GSAP Skills

- 它是指令集（44 个文件），**不含运行时**。需要动效时用 `gsap_setup.py` 把真实运行时装进项目。
- 接入后必须满足：动效可独立开关、尊重 `prefers-reduced-motion`、手机与 RTL 下不遮挡文字不拦截点击。这四条由主 Skill 检查（阶段 `full-site-motion` 的 checker 记为 `aux:gsapSkills`，但验收仍由主 Skill 执行）。
- 不需要动效的项目把该阶段记为 `not-applicable` 并写明原因。

### Galaxy

- 是组件资源库（约 3800 个独立 HTML 文件，Buttons / Cards / Forms / Inputs / …）。**不是可调用的 Skill**。
- 文件名形如 `作者_形容词动物-序号.html`，**没有语义关键词**，所以 `galaxy_pick.py` 提供 `--list` 列举 + `--name` 精确取用；语义挑选仍需打开源码确认。
- 取来的组件必须**适配设计规格并接入真实功能**（数据、事件、校验、状态），样式需隔离，不允许只做装饰。

## 冲突规则

`docs/DESIGN.md` 是项目唯一设计依据，`docs/design-spec.json` 是它的数值化版本。Pro Max 的检索结果写进 `docs/aux-calls/`，只作为 `design-spec` 的输入之一；Impeccable 的评审**依据** `design-spec` 提出修改，不得另立一套风格。出现冲突时以 `DESIGN.md` 为准，或在 `DESIGN.md` 中明确修订并记录原因。

## 记录要求

每次调用都要记入 `workflow.json` 的 `auxCapabilities.<capability>`：

- `source` / `commit` / `license`
- `available`（true / false）
- `integration`（script / cli / runtime / library）
- `command`（实际执行的命令）
- `usedIn`（用于哪些阶段）
- `invocations[]`：每次调用的 `action`、`result`（success / partial / failed / not-run）、`input`、`output`、`appliedTo`（应用到哪个文件）、`recheckedBy`（谁复核）

输出文件一律落在 `<项目>/docs/aux-calls/`，用**项目相对路径**记录，且必须随交付一起打包。
