---
change: web-layout-shell
design-doc: docs/superpowers/specs/2026-07-28-web-layout-shell-design.md
base-ref: cc86e0767b410e282b0f2d8b0485bd75f5384851
archived-with: 2026-07-28-web-layout-shell
---

# Web Layout Shell 实施计划

设计文档：`docs/superpowers/specs/2026-07-28-web-layout-shell-design.md`

技术栈：Next.js 16.2.6（App Router）+ React 19 + Tailwind CSS v4 + shadcn（base-nova 风格，@base-ui/react）+ next-themes + zustand

OpenSpec 任务映射：`openspec/changes/web-layout-shell/tasks.md`

## Global Constraints

- Next.js 16 是新版本，写代码前查 `node_modules/next/dist/docs/` 和 `node_modules/next-intl` 相关文档
- 只做 Layout，不实现业务页面内容
- 菜单声明式配置，角色过滤
- i18n 使用路径 A（getRequestConfig + cookie locale，无 locale 路由前缀）
- Sidebar 宽度固定 220px，Header 高度固定 56px，不做折叠
- CSS 变量使用 shadcn 已定义的 sidebar-* 系列（globals.css 已包含）
- 组件路径：`@/*` 映射到 `apps/web/*`，UI 组件从 `@intelligent-customer/ui/components/*` 导入
- 每个任务完成后必须提交 git commit

---

## 阶段 1：i18n 基础配置

### Task 1

安装 next-intl 依赖并验证兼容性。

- 运行 `pnpm add next-intl`（在 apps/web 目录或 monorepo 根目录）
- 查看 `node_modules/next-intl/package.json` 的 peerDependencies，确认与 Next.js 16 兼容
- 验收：依赖安装成功，无 peer 譆告冲突

OpenSpec 映射：tasks.md `1.1 安装 next-intl 依赖`

### Task 2

创建 i18n 基础配置文件（routing.ts + request.ts）并更新 next.config.ts。

- 创建 `apps/web/i18n/routing.ts`：
  - 导出 `locales = ['zh-CN', 'en-US'] as const`
  - 导出 `defaultLocale = 'zh-CN' as const`
  - 导出 `cookieName = 'NEXT_LOCALE'`
  - 导出 `Locale` 类型
- 创建 `apps/web/i18n/request.ts`：
  - 实现 `getRequestConfig`（从 next-intl/server 导入）
  - 使用 `cookies()` 从 `next/headers` 读取 `NEXT_LOCALE` cookie
  - 校验 locale 是否在 `routing.locales` 内，非法则回退 `defaultLocale`
  - 动态 import `../messages/${locale}.json`
- 更新 `apps/web/next.config.ts`：
  - 引入 `createNextIntlPlugin('./i18n/request.ts')`
  - 用 `withNextIntl` 包裹现有 `nextConfig`
  - 保留现有 rewrites 配置
- 验收：文件创建完成，TypeScript 编译无错

OpenSpec 映射：tasks.md `1.2 创建 i18n/routing.ts` + `1.3 创建 i18n/request.ts` + `1.4 更新 next.config.ts`

### Task 3

重写翻译消息文件（zh-CN.json + en-US.json）。

- 重写 `apps/web/messages/zh-CN.json`，移除 LingDiary 遗留内容，按 Design Doc 第 4.1 节结构：
  - `common`：appName("AI 客服系统")、tagline、loading、logout、roleAdmin、roleUser
  - `layout`：menuChat、menuGroupManagement、menuKnowledge、menuUsers、menuConfig、menuTools
  - `theme`：toggle、light、dark、system
  - `language`：zhCN、enUS
- 重写 `apps/web/messages/en-US.json`，与 zh-CN 键一一对应，英文翻译
- 验收：两个 JSON 文件合法，键完全对应，无 LingDiary 内容

OpenSpec 映射：tasks.md `1.5 重写 zh-CN.json` + `1.6 重写 en-US.json`

## 阶段 2：shadcn 组件补充

### Task 4

添加 shadcn 组件（dropdown-menu、avatar、separator）。

- 运行 `pnpm dlx shadcn@latest add dropdown-menu -c apps/web`，确认落入 `packages/ui/src/components/dropdown-menu.tsx`
- 运行 `pnpm dlx shadcn@latest add avatar -c apps/web`
- 运行 `pnpm dlx shadcn@latest add separator -c apps/web`
- 若任一 `shadcn add` 失败（base-nova 风格未适配），手动基于 `@base-ui/react` 实现，参照现有 button.tsx 模式
- 验收：三个组件均可从 `@intelligent-customer/ui/components/*` 导入，TypeScript 编译无错

OpenSpec 映射：tasks.md `2.1 添加 dropdown-menu` + `2.2 添加 avatar` + `2.3 添加 separator`

## 阶段 3：菜单配置与 Layout 组件

### Task 5

创建菜单配置文件（config/menu.ts）。

- 创建 `apps/web/config/menu.ts`
- 定义类型：`MenuRole`（'admin' | 'user'）、`MenuGroupConfig`（type: 'group', key, labelKey）、`MenuItemConfig`（type?: 'item', key, labelKey, href, icon: LucideIcon, roles?: MenuRole[]）、`MenuEntry`（联合类型）
- 导出 `menuConfig` 数组：
  - chat（labelKey: 'layout.menuChat', href: '/', icon: MessageSquare, 无 roles）
  - management 分组（type: 'group', key: 'management', labelKey: 'layout.menuGroupManagement'）
  - knowledge（href: '/knowledge', icon: BookOpen, roles: ['admin']）
  - users（href: '/users', icon: Users, roles: ['admin']）
  - config（href: '/config', icon: Settings, roles: ['admin']）
  - tools（href: '/tools', icon: Wrench, roles: ['admin']）
- 导出 `filterMenuByRole(entries: MenuEntry[], role: MenuRole | undefined): MenuEntry[]` 纯函数
  - role 为 undefined 时返回空数组
  - 保留 group 类型条目，但渲染时需判断分组下是否有可见 item
  - 无 roles 的 item 对所有用户可见；有 roles 的仅匹配角色可见
- 导出 `titleKeyMap: Record<string, string>`（pathname → i18n key 映射）
- 验收：文件创建，类型和函数导出正确

OpenSpec 映射：tasks.md `3.1 创建 config/menu.ts`

### Task 6

创建 AppSidebar 组件。

- 创建 `apps/web/components/app-sidebar.tsx`，标记 `"use client"`
- 使用 `useAuthStore`（user, logout）、`usePathname`、`useTranslations`
- 顶部 Logo 区域：h-14，🤖 图标 + "AI 客服"文字（使用 `useTranslations('common').appName`），底部 border-b
- 菜单区域：
  - 调用 `filterMenuByRole(menuConfig, user?.role as MenuRole | undefined)` 获取过滤后菜单
  - 遍历渲染：分组标题（小字 muted-foreground uppercase tracking-wider）、菜单项（Link + icon + label）
  - 菜单项 active 样式：当前 pathname 匹配 href 时使用 `bg-sidebar-primary text-sidebar-primary-foreground`，否则 hover 用 `hover:bg-sidebar-accent hover:text-sidebar-accent-foreground`
  - 分组下无可见 item 时跳过分组标题渲染
- 底部用户信息区域：
  - Avatar 占位圆形 + `user.username` + 角色标签（admin→管理员/user→普通用户，i18n）
  - 退出登录文字按钮，调用 `logout()`
  - 防御性检查：`if (!user)` 不渲染用户信息区域
- Sidebar 样式：`w-[220px] bg-sidebar text-sidebar-foreground flex flex-col shrink-0`，暗色主题下背景色通过 CSS 变量自动切换
- 验收：组件渲染，admin 看到6个菜单项+1分组，user 看到1个菜单项，退出登录可调用

OpenSpec 映射：tasks.md `3.2 创建 components/app-sidebar.tsx`

### Task 7

创建 AppHeader 组件。

- 创建 `apps/web/components/app-header.tsx`，标记 `"use client"`
- 使用 `usePathname`、`useTranslations`
- 左侧：页面标题
  - 从 `titleKeyMap` 获取当前 pathname 对应的 i18n key
  - 使用 `useTranslations` 翻译
  - 默认值：`common.appName`
- 右侧操作区域：ThemeSwitcher + LanguageSwitcher（这两个组件在后续任务实现，先留占位 div）
- Header 样式：`h-14 bg-background border-b flex items-center justify-between px-6 shrink-0`
- 验收：Header 渲染页面标题，右侧有操作区域

OpenSpec 映射：tasks.md `3.3 创建 components/app-header.tsx`

### Task 8

创建 AppLayout 组件。

- 创建 `apps/web/components/app-layout.tsx`，标记 `"use client"`
- 三栏布局：`<div className="flex h-svh">`
  - `<AppSidebar />`
  - `<div className="flex flex-1 flex-col overflow-hidden">`
    - `<AppHeader />`
    - `<main className="flex-1 overflow-y-auto p-6">{children}</main>`
- 接收 `children: React.ReactNode`
- 验收：三栏布局正确渲染，Sidebar 220px 固定宽度

OpenSpec 映射：tasks.md `3.4 创建 components/app-layout.tsx`

## 阶段 4：主题切换 UI

### Task 9

创建 ThemeSwitcher 组件并集成到 AppHeader。

- 创建 `apps/web/components/theme-switcher.tsx`，标记 `"use client"`
- 使用 `useTheme`（来自 next-themes）
- 使用 `useTranslations('theme')`
- 使用 DropdownMenu 组件
- 触发按钮：icon button
  - 使用 `resolvedTheme` 判断图标：`resolvedTheme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />`
  - 注意 hydration 防护：用 `mounted` state 避免服务端渲染时 `resolvedTheme` 为 undefined
- 三个选项：
  - light（labelKey: theme.light）
  - dark（labelKey: theme.dark）
  - system（labelKey: theme.system）
  - 当前 theme 对应项显示 check 标记（使用 DropdownMenuItem 的 `disabled` + icon 或 CheckboxIndicator）
  - 点击调用 `setTheme(value)`
- 在 `app-header.tsx` 中集成：在右侧操作区域渲染 `<ThemeSwitcher />`
- 验收：点击切换三选项，html class 变化（dark/light），图标切换

OpenSpec 映射：tasks.md `4.1 创建 theme-switcher.tsx` + `4.2 在 AppHeader 集成`

## 阶段 5：语言切换 UI

### Task 10

创建 LanguageSwitcher 组件并集成到 AppHeader。

- 创建 `apps/web/components/language-switcher.tsx`，标记 `"use client"`
- 使用 `useRouter`（来自 next/navigation）、`useTranslations('language')`
- 使用 DropdownMenu 组件
- 使用 `useLocale`（来自 next-intl）获取当前 locale
- 触发按钮：🌐 Globe 图标 + 当前 locale 缩写（"中"/"EN"）
- 两个选项：
  - zh-CN（labelKey: language.zhCN）
  - en-US（labelKey: language.enUS）
  - 当前 locale 对应项显示 check 标记
- 切换逻辑：
  ```typescript
  document.cookie = `NEXT_LOCALE=${locale};path=/;max-age=31536000`;
  router.refresh();
  ```
- 在 `app-header.tsx` 中集成：在 ThemeSwitcher 旁渲染 `<LanguageSwitcher />`
- 验收：切换语言后 Layout 文本更新，URL 不变，刷新后保持

OpenSpec 映射：tasks.md `5.1 创建 language-switcher.tsx` + `5.2 在 AppHeader 集成`

## 阶段 6：Layout 接入与首页更新

### Task 11

更新 app/layout.tsx 和 app/page.tsx，集成 NextIntlClientProvider + AppLayout。

- 更新 `apps/web/app/layout.tsx`：
  - 改为 async Server Component（`export default async function RootLayout`）
  - 导入 `getLocale` 和 `getMessages`（来自 next-intl/server）
  - 调用 `const locale = await getLocale()` 和 `const messages = await getMessages()`
  - 用 `NextIntlClientProvider` 包裹（传入 `locale` 和 `messages`）
  - 保留 ThemeProvider
  - 用 AppLayout 包裹 children
  - `html` 的 `lang` 属性改为动态 `locale`
  - 保留 geist 字体配置和 `suppressHydrationWarning`
- 更新 `apps/web/app/page.tsx`：
  - 保留 `"use client"` 和 `initAuth` 调用
  - 保留 loading 状态
  - 内容区显示欢迎信息（使用 `useTranslations('common')`）
  - 移除退出登录按钮（已在 Sidebar）
  - 使用 `useTranslations` 替换硬编码中文
- 验收：页面加载无 hydration error，首页展示完整 Layout，i18n 文本正确

OpenSpec 映射：tasks.md `6.1 更新 layout.tsx` + `6.2 更新 page.tsx`

### Task 12

验证完整流程：构建、类型检查、lint 通过。

- 运行 `pnpm --filter web build`，确认构建成功
- 运行 `pnpm --filter web typecheck`，确认类型检查通过
- 运行 `pnpm --filter web lint`，确认 lint 通过
- 如有构建错误，修复后重新验证
- 验收：三个命令全部通过

OpenSpec 映射：tasks.md `6.3 验证完整流程`

## 阶段 7：测试

### Task 13

添加 filterMenuByRole 单元测试。

- 创建或更新测试文件 `apps/web/__tests__/menu-filter.test.ts`
- 测试用例：
  - admin 角色看到全部菜单项（6 item + 1 group）
  - user 角色只看到 chat 菜单项（1 item，无 group）
  - undefined role 返回空数组
  - 分组下所有 item 被过滤时，分组标题仍保留在结果中（渲染逻辑处理跳过）
- 运行 `pnpm --filter web test` 确认测试通过
- 验收：所有测试通过

OpenSpec 映射：tasks.md `7.1 filterMenuByRole 单元测试`
