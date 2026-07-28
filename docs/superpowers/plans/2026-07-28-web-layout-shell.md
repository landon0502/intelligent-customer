---
change: web-layout-shell
design-doc: docs/superpowers/specs/2026-07-28-web-layout-shell-design.md
base-ref: cc86e0767b410e282b0f2d8b0485bd75f5384851
---

# Web Layout Shell 实施计划

本计划基于 Design Doc `docs/superpowers/specs/2026-07-28-web-layout-shell-design.md`，拆分为可执行任务。

技术栈：Next.js 16.2.6（App Router）+ React 19 + Tailwind CSS v4 + shadcn（base-nova 风格，@base-ui/react）+ next-themes + zustand。

关键约束：
- Next.js 16 是新版本，写代码前查 `node_modules/next/dist/docs/` 和 `node_modules/next-intl`
- 菜单声明式配置，角色过滤
- 主题切换 + 国际化
- 只做 Layout，不实现业务页面

## 阶段 1：i18n 基础配置

### 任务 1.1：安装 next-intl 依赖
- 运行 `pnpm add next-intl`，确认安装成功
- 验证 next-intl 与 Next.js 16 兼容（查看 `node_modules/next-intl/package.json` 的 peerDependencies）
- 验收：依赖安装成功，无 peer 警告冲突

### 任务 1.2：创建 i18n/routing.ts
- 定义 `locales = ['zh-CN', 'en-US']`、`defaultLocale = 'zh-CN'`、`cookieName = 'NEXT_LOCALE'`
- 导出 `Locale` 类型
- 验收：文件创建，类型可被其他模块导入

### 任务 1.3：创建 i18n/request.ts
- 实现 `getRequestConfig`，从 `cookies()` 读取 `NEXT_LOCALE` cookie
- 校验 locale 是否在 `routing.locales` 内，非法则回退 `defaultLocale`
- 动态 import 对应 messages 文件
- 验收：导出 default getRequestConfig

### 任务 1.4：更新 next.config.ts
- 引入 `createNextIntlPlugin('./i18n/request.ts')`
- 用 `withNextIntl` 包裹现有 `nextConfig`
- 保留现有 rewrites 配置
- 验收：`pnpm --filter web build` 不报错

### 任务 1.5：重写 messages/zh-CN.json
- 移除 LingDiary 遗留内容
- 按 Design Doc 第 4.1 节结构组织：common、layout、theme、language
- 验收：JSON 合法，包含所有 Design Doc 列出的键

### 任务 1.6：重写 messages/en-US.json
- 与 zh-CN 键一一对应，英文翻译
- 验收：JSON 合法，键与 zh-CN 完全对应

## 阶段 2：shadcn 组件补充

### 任务 2.1：添加 dropdown-menu 组件
- 运行 `pnpm dlx shadcn@latest add dropdown-menu -c apps/web`
- 确认组件落入 `packages/ui/src/components/dropdown-menu.tsx`
- 若失败：手动基于 `@base-ui/react/menu` 实现
- 验收：组件可从 `@intelligent-customer/ui/components/dropdown-menu` 导入

### 任务 2.2：添加 avatar 组件
- 运行 `pnpm dlx shadcn@latest add avatar -c apps/web`
- fallback：简单 div 圆形
- 验收：组件可导入

### 任务 2.3：添加 separator 组件
- 运行 `pnpm dlx shadcn@latest add separator -c apps/web`
- fallback：`<hr>` 或 border div
- 验收：组件可导入

## 阶段 3：菜单配置与 Layout 组件

### 任务 3.1：创建 config/menu.ts
- 定义 `MenuRole`、`MenuGroupConfig`、`MenuItemConfig`、`MenuEntry` 类型
- 导出 `menuConfig` 数组
- 导出 `filterMenuByRole` 纯函数
- 导出 `titleKeyMap`
- 验收：类型导出，filterMenuByRole 可被单元测试

### 任务 3.2：创建 components/app-sidebar.tsx
- `"use client"`，读 useAuthStore + usePathname + useTranslations
- Logo 区域 + 菜单渲染（角色过滤 + 激活高亮）+ 底部用户信息 + 退出登录
- 验收：admin/user 菜单项数量正确，退出登录可调用

### 任务 3.3：创建 components/app-header.tsx
- `"use client"`，左侧标题 + 右侧 switcher 占位
- 验收：Header 渲染标题

### 任务 3.4：创建 components/app-layout.tsx
- `"use client"`，三栏 flex 容器
- 验收：三栏布局渲染

## 阶段 4：主题切换 UI

### 任务 4.1：创建 components/theme-switcher.tsx
- DropdownMenu + useTheme，图标 Sun/Moon，i18n 标签
- 验收：切换三选项，html class 变化

### 任务 4.2：在 AppHeader 集成 ThemeSwitcher
- 验收：Header 右侧显示主题切换按钮

## 阶段 5：语言切换 UI

### 任务 5.1：创建 components/language-switcher.tsx
- DropdownMenu，cookie + router.refresh()
- 验收：切换语言后文本更新，URL 不变

### 任务 5.2：在 AppHeader 集成 LanguageSwitcher
- 验收：Header 右侧显示语言切换按钮

## 阶段 6：Layout 接入与首页更新

### 任务 6.1：更新 app/layout.tsx
- async Server Component + NextIntlClientProvider + AppLayout
- 验收：页面加载无 hydration error

### 任务 6.2：更新 app/page.tsx
- 占位内容，i18n 欢迎信息
- 验收：首页展示完整 Layout

### 任务 6.3：验证完整流程
- `pnpm --filter web build` 通过
- `pnpm --filter web typecheck` 通过
- 手动验证完整流程

## 阶段 7：测试

### 任务 7.1：filterMenuByRole 单元测试
- 验收：测试通过

### 任务 7.2：LanguageSwitcher 行为测试（可选）
- 验收：测试通过

## 验收检查清单

- [ ] Sidebar + Header + Content 三栏布局
- [ ] Sidebar 含 Logo、菜单、用户信息、退出登录
- [ ] 菜单声明式配置，角色过滤正确
- [ ] Header 含页面标题、主题切换、语言切换
- [ ] 主题切换：亮/暗/系统，图标切换
- [ ] 语言切换：中/英，文本更新，URL 不变
- [ ] Layout 组件从 components 目录抽离
- [ ] `pnpm --filter web build` 通过
- [ ] `pnpm --filter web typecheck` 通过
