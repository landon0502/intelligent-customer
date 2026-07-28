## 1. 依赖安装与 i18n 基础配置

- [x] 1.1 安装 next-intl 依赖（`pnpm add next-intl`），验证与 Next.js 16 兼容性
- [x] 1.2 创建 `apps/web/i18n/request.ts`，实现 `getRequestConfig` 从 cookie 读取 locale 并加载对应 message 文件
- [x] 1.3 创建 `apps/web/i18n/routing.ts`，定义支持的语言列表（zh-CN、en-US）和默认语言
- [x] 1.4 更新 `apps/web/next.config.ts`，添加 `createNextIntlPlugin()` 集成
- [x] 1.5 重写 `apps/web/messages/zh-CN.json`，按 AI 客服系统组织翻译内容（common、layout、theme、language 命名空间）
- [x] 1.6 重写 `apps/web/messages/en-US.json`，与 zh-CN 对应的英文翻译

## 2. shadcn 组件补充

- [x] 2.1 通过 `pnpm dlx shadcn@latest add dropdown-menu -c apps/web` 添加 DropdownMenu 组件
- [x] 2.2 通过 `pnpm dlx shadcn@latest add avatar -c apps/web` 添加 Avatar 组件
- [x] 2.3 通过 `pnpm dlx shadcn@latest add separator -c apps/web` 添加 Separator 组件
- [ ] 2.4 通过 `pnpm dlx shadcn@latest add tooltip -c apps/web` 添加 Tooltip 组件（如 shadcn add 不可用，手动基于 @base-ui/react 实现）

## 3. 菜单配置与 Layout 组件实现

- [x] 3.1 创建 `apps/web/config/menu.ts`，导出菜单配置数组（含 key、labelKey、href、icon、roles、分组声明）
- [x] 3.2 创建 `apps/web/components/app-sidebar.tsx`，实现 Sidebar 组件（Logo 区域、菜单列表渲染、角色过滤、底部用户信息、退出登录）
- [x] 3.3 创建 `apps/web/components/app-header.tsx`，实现 Header 组件（页面标题、右侧操作区域占位）
- [ ] 3.4 创建 `apps/web/components/app-layout.tsx`，组合 Sidebar + Header + Content 三栏布局

## 4. 主题切换 UI

- [ ] 4.1 创建 `apps/web/components/theme-switcher.tsx`，实现主题切换 DropdownMenu（亮色/暗色/跟随系统），集成 next-themes 的 useTheme
- [ ] 4.2 在 AppHeader 右侧集成 ThemeSwitcher 组件，根据当前主题显示太阳/月亮图标

## 5. 语言切换 UI

- [ ] 5.1 创建 `apps/web/components/language-switcher.tsx`，实现语言切换 DropdownMenu，切换时更新 cookie 并刷新 locale
- [ ] 5.2 在 AppHeader 右侧集成 LanguageSwitcher 组件（ThemeSwitcher 旁边）

## 6. Layout 接入与首页更新

- [ ] 6.1 更新 `apps/web/app/layout.tsx`，集成 NextIntlClientProvider 和 AppLayout
- [ ] 6.2 更新 `apps/web/app/page.tsx`，替换为使用新 Layout 的首页占位内容
- [ ] 6.3 验证完整流程：登录 → 首页展示 Layout → 主题切换 → 语言切换 → 退出登录
