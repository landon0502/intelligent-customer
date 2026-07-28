## Context

当前 `apps/web/components/` 目录下散落着 5 个 Layout 相关组件（`app-layout.tsx`、`app-header.tsx`、`app-sidebar.tsx`、`theme-switcher.tsx`、`language-switcher.tsx`），缺乏目录组织。AppLayout 在 `app/layout.tsx` 中全局渲染，导致登录/注册等无需 Layout 的页面也被包裹。用户信息和退出登录放在 Sidebar 底部，Header 右上角只有独立的语言切换和主题切换按钮，交互模式不符合常见后台管理系统惯例。

## Goals / Non-Goals

**Goals:**
- 将 Layout 相关组件统一收纳至 `components/layout/` 子目录
- Header 右上角通过 DropdownMenu 整合用户信息、退出登录、系统设置等操作
- AppLayout 改为页面级按需引入，登录/注册页面不被 AppLayout 包裹
- 国际化切换按钮只显示 localeAbbr 文字值，不使用图标
- 菜单 MenuItem 去掉圆角

**Non-Goals:**
- 不新增系统设置页面或功能（仅预留入口）
- 不修改 Sidebar 菜单配置结构
- 不修改 UI 组件库（packages/ui）的 DropdownMenu 组件实现
- 不涉及响应式布局或移动端适配

## Decisions

1. **组件目录结构**：将 `app-layout.tsx`、`app-header.tsx`、`app-sidebar.tsx`、`theme-switcher.tsx`、`language-switcher.tsx` 移至 `components/layout/`，所有 import 路径同步更新。`theme-provider.tsx` 保留在 `components/` 根目录，因为它不属于 Layout 视觉组件。

2. **Header 用户 DropdownMenu**：使用 `@intelligent-customer/ui` 已有的 `DropdownMenu` + `Avatar` 组件。触发按钮只显示头像（圆形，显示用户名首字母），DropdownMenu 内第一项为用户信息展示项（不可点击），后续为系统设置（预留）、退出登录等操作项。语言切换和主题切换也整合进此 DropdownMenu。

3. **AppLayout 渲染策略**：从 `app/layout.tsx` 移除 AppLayout，改为在需要 Layout 的页面（如首页 `page.tsx`）中直接 import 并包裹。登录/注册页面自然不被包裹。

4. **国际化切换按钮**：LanguageSwitcher 的 DropdownMenuTrigger 只显示 `localeAbbr[currentLocale]` 的文字值（如"中"/"EN"），移除 Globe 图标。

5. **MenuItem 圆角**：Sidebar 菜单项的 `rounded-md` class 移除，改为无圆角直角样式。

## Risks / Trade-offs

- [页面级 AppLayout 引入可能导致部分页面遗漏包裹] → 通过明确列出需要 AppLayout 的页面来规避，当前只有首页 `/` 需要
- [DropdownMenu 整合后 Header 右上角操作项较多] → 使用 DropdownMenuSeparator 分组，保持视觉清晰
- [组件移动后所有 import 路径需更新] → 全局搜索替换，确保无遗漏
