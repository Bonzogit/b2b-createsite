# 模块与组件连接

前台模块必须连到统一内容模型和业务接口，不允许把业务内容写死在页面里。本文定义"模块已接通"的最低验证项；每个项目在 `docs/MODULES.md` 记录实际结论。

## 每个模块必须说清的五件事

1. 内容字段 — 数据存哪些字段，哪些可后台编辑。
2. 后台编辑位置 — 后台哪个菜单、哪个表单控件。
3. 接口 — 读取/写入走哪个 `/api/v1` 路径。
4. 前台呈现 — 哪个渲染层函数、哪个模板片段。
5. 交互状态 — 空态、加载、失败、成功、禁用、RTL。

## 优先验证的三个业务模块

### 产品列表

| 项 | 要求 |
|---|---|
| 字段 | `title`、`slug`、`summary`、`model`、`cover`、`categoryId`、`badge`、`specs[]` |
| 后台 | 产品管理 → 列表卡片；分类在分类管理 |
| 接口 | `GET /api/v1/products`（已发布）；`GET /api/v1/products?ids=a,b` 用于比较视图 |
| 前台 | 渲染层 `listing` 分支；卡片含图、型号、摘要、首条参数 |
| 交互 | 无产品时显示空态文案；图片加载失败不破坏栅格；RTL 方向正确 |

### 产品详情

| 项 | 要求 |
|---|---|
| 字段 | 上述 + `body`、`gallery[]`（url/alt/caption）、`specs[]`（group/label/value/unit）、`faqs[]`（q/a）、`highlights[]` |
| 后台 | 产品管理 → 编辑表单：图库、参数、常见问题、亮点各一个多行控件，格式见后台提示 |
| 接口 | `GET /api/v1/products/:slug`；草稿预览走 `/api/v1/admin/preview/products/:id` |
| 前台 | 渲染层 `productDetail`：按本产品信息任务组织画廊、正文、参数、FAQ 与询盘；不规定统一顺序 |
| 交互 | 画廊缩略图可键盘操作；FAQ 用 `details` 可折叠；询盘表单带型号快照 |

### 询盘

| 项 | 要求 |
|---|---|
| 字段 | `name`、`email`、`message`、`productId`、`file`、蜜罐 `website`、`submissionKey` |
| 后台 | 客户询盘 → 备注、状态、重试通知、CSV 导出 |
| 接口 | `POST /api/v1/inquiries`（JSON 或 multipart） |
| 前台 | 渲染层 `inquiryForm` + `public/contact/index.html` |
| 交互 | 提交中禁用按钮；成功显示编号；失败显示错误；重复提交幂等；同 key 不同内容拒绝 |

## 组件替换规则

替换任何组件（卡片、轮播、表单控件）时：

1. 必须接入原有数据字段，不得自建数据源。
2. 必须保留原有事件、校验和状态（提交、失败反馈、附件上传、蜜罐、submissionKey）。
3. 第三方样式必须隔离（作用域类名或影子容器），不得污染其他页面。
4. 技术栈不兼容的组件直接跳过或按现有技术实现；不为组件引入新运行时依赖。
5. 替换后重新运行 e2e 脚本与相关视觉检查，并触发 `workflow.py invalidate`。

## 渲染层边界

- `lib/app.mjs` 持有业务、鉴权、存储、翻译与接口；**不**持有品牌版式。
- `lib/render.mjs` 提供默认渲染器（与 1.6.x 输出兼容）。
- 项目可提供 `lib/theme.mjs` 导出 `createRenderer()`，运行入口自动加载；主题只拿到已解析的视图上下文（`blocks` 已含译文），接口不传入凭据、存储和私有数据；主题约定只做呈现（同进程代码不是安全沙箱）。
- 同一内容模型允许多套布局；主题不是"所有网站共用的首页拼装器"。

## 全局动效

背景、光标、模块动画必须可以独立启用与关闭；不得遮挡文字、拦截点击或破坏手机与 RTL 布局；必须尊重 `prefers-reduced-motion`。

## 向后兼容

扩展字段只增不删。旧数据没有这些字段时，`ensureExtensions()` 返回空数组；旧的后台与脚本不传这些字段时不受影响。稳定块 ID（`title`、`summary`、`bodyN`）不变，新增块 ID（`specN.label`、`faqN.q`、`highlightN`、`galleryN.alt`）只增不改。
