## Context

当前 `apps/web` 首页（`app/page.tsx`）只是一个简单的欢迎占位页，无应用外壳。原型 `/docs/原型.html` 展示了一个标准的 Sidebar（220px）+ Header（56px）+ Content 三栏布局。技术栈已确定：Next.js 16.2.6（App Router）+ React 19 + Tailwind CSS v4 + shadcn（base-nova 风格，基于 @base-ui/react）+ next-themes。

国际化方面，项目已有 `apps/web/messages/zh-CN.json` 和 `en-US.json`，但内容是上一个项目（LingDiary）遗留，且未接入任何 i18n 运行时。所有页面文本目前硬编码中文。主题切换已有 ThemeProvider（`attribute="class"`，支持 system），但只有键盘快捷键 `d` 切换，无 UI 入口。

约束：
- 不实现其他业务页面内容，只搭 Layout
- 菜单声明式配置
- 主题切换和国际化必须可用

## Goals / Non-Goals

**Goals:**
- 建立 Sidebar + Header + Content 三栏 App Shell，组件从 `apps/web/components/` 抽离
- 菜单以配置数组声明，支持角色过滤
- 接入 next-intl 运行时，文本可切换语言
- Header 暴露主题切换（亮/暗/系统）和语言切换 UI 入口
- 首页套用新 Layout 展示占位内容

**Non-Goals:**
- 不实现聊天、知识库、用户管理等业务页面的具体内容
- 不修改后端 API 和 auth 逻辑
- 不实现 Sidebar 折叠动画（保持固定宽度，后续可扩展）
- 不做 SSR 渲染优化之外的服务端 i18n 路由（保持单一路由，不做 `/[locale]` 前缀路由，降低改动面）

## Decisions

### Decision 1: i18n 库选用 next-intl
**选择**：next-intl
**理由**：Next.js App Router 生态最主流的 i18n 方案，原生支持 RSC、Server Components 和消息文件加载。与项目已有的 `messages/*.json` 结构契合。项目已有 message 文件，迁移成本低。
**替代方案**：react-i18next（需额外配置 SSR，生态偏 CSR）、i18next（更底层）。next-intl 对 App Router 一等支持，优先选它。

### Decision 2: i18n 路由策略采用"无 locale 前缀"模式
**选择**：不引入 `/[locale]` 路由段，使用 next-intl 的 `getNow()` / 客户端 locale 持久化（cookie/localStorage），语言切换不改变 URL。
**理由**：当前项目路由已存在 `/login`、`/register`、`/`，引入 locale 前缀会牵连 middleware、auth 重定向逻辑，与本次"只做 Layout"目标不符。无前缀模式下，locale 通过 cookie 持久化，`NextIntlClientProvider` 在 root layout 注入。
**替代方案**：`/[locale]` 前缀路由（标准但改动大）。本次范围外。

### Decision 3: 菜单配置声明式 + 角色过滤
**选择**：在 `apps/web/config/menu.ts` 导出菜单配置数组，每项含 `key`、`labelKey`（i18n key）、`href`、`icon`、`roles`（可选）。渲染时根据当前 `user.role` 过滤。
**理由**：原型中 admin 看到"管理"分组（知识库、用户、系统配置、工具配置），普通 user 只看到"智能对话"。声明式配置便于后续扩展，符合"菜单以配置形式声明"要求。

### Decision 4: Layout 组件分层
**选择**：
- `AppLayout`（Server 或 Client 顶层容器，组合 Sidebar + Header + Content）
- `AppSidebar`（Client，读 auth store + 渲染菜单 + 用户信息）
- `AppHeader`（Client，页面标题 + 主题切换 + 语言切换）
- `ThemeSwitcher`（Client，封装主题切换 dropdown）
- `LanguageSwitcher`（Client，封装语言切换 dropdown）
**理由**：单一职责，便于复用和测试。Sidebar/Header 需读 client state（auth、theme），用 `"use client"`。

### Decision 5: shadcn 组件补充
**选择**：通过 `pnpm dlx shadcn@latest add <component> -c apps/web` 添加 `sidebar`（或手动用现有基础组件拼装）、`dropdown-menu`、`avatar`、`separator`、`tooltip`。组件落入 `packages/ui/src/components/`。
**理由**：项目已有 button/card/input/label/drawer，Layout 需要的菜单交互依赖 dropdown-menu 等。遵循项目既有 shadcn 工作流。
**替代方案**：纯手写 Tailwind。但项目已标准化 shadcn，应保持一致。

### Decision 6: 翻译文件重构
**选择**：重写 `messages/zh-CN.json` 和 `en-US.json`，移除 LingDiary 遗留内容，按 AI 客服系统组织：`common`、`layout`（menu/header）、`theme`、`language`。
**理由**：现有文件内容与项目不符，直接复用会产生误导。

## Risks / Trade-offs

- **[Next.js 16 新版本差异]** → 严格按照 `AGENTS.md` 提示，写代码前查 `node_modules/next/dist/docs/`，留意 App Router 与 next-intl 集成的 API 变化
- **[next-intl 与 Next 16 兼容性]** → 先验证 next-intl 最新版支持 Next 16，若不支持则回退评估；安装后跑 `next build` 验证
- **[无 locale 前缀模式下 SSR 一致性]** → locale 通过 cookie 读取，首屏可能闪现默认语言；接受此 trade-off，或用 `suppressHydrationWarning` 处理
- **[shadcn base-nova 风格组件可用性]** → 部分 shadcn 组件在 base-nova 风格下可能未适配；若 `shadcn add` 失败则手动基于 @base-ui/react 实现
- **[菜单角色过滤依赖 auth store]** → Sidebar 需 client 渲染读 user.role；未登录态（理论上 middleware 已拦截）兜底显示空菜单
