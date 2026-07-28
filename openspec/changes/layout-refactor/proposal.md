## Why

当前 Layout 组件散落在 `components/` 根目录，缺乏目录组织；Header 右上角功能入口分散（语言切换、主题切换各自独立），用户信息与退出登录放在 Sidebar 底部而非 Header，不符合常见后台管理系统的交互模式；AppLayout 在全局 `layout.tsx` 中渲染导致登录/注册等无需 Layout 的页面也被包裹；国际化切换按钮使用 Globe 图标不够直观；菜单项圆角样式与整体设计不协调。

## What Changes

- 将 `app-layout.tsx`、`app-header.tsx`、`app-sidebar.tsx`、`theme-switcher.tsx`、`language-switcher.tsx` 移至 `components/layout/` 子目录
- Header 右上角新增用户头像 DropdownMenu，整合用户信息、退出登录、系统设置等操作；触发按钮只显示头像；DropdownMenu 内第一项显示用户必要信息
- Sidebar 底部移除用户信息和退出登录区域
- **BREAKING**: AppLayout 从 `app/layout.tsx` 全局渲染改为页面级按需引入，登录/注册页面不再被 AppLayout 包裹
- 国际化切换按钮触发元素只显示 `localeAbbr` 中的 value 值（如"中"/"EN"），移除 Globe 图标
- 菜单 MenuItem 去掉圆角（`rounded-md` → 无圆角）

## Capabilities

### New Capabilities

（无新增 capability）

### Modified Capabilities

- `app-shell-layout`: Layout 组件目录结构变更、Header 交互模式变更（用户信息从 Sidebar 移至 Header DropdownMenu）、AppLayout 渲染策略变更（全局→页面级）、菜单项样式变更

## Impact

- **代码文件**：`apps/web/components/` 下 5 个组件文件移动至 `components/layout/`；`app/layout.tsx` 移除 AppLayout 引用；`app/page.tsx` 新增 AppLayout 包裹；`app-header.tsx` 重写（新增 DropdownMenu、移除独立切换按钮）；`app-sidebar.tsx` 移除底部用户区域；`language-switcher.tsx` 触发按钮样式变更
- **依赖**：`@intelligent-customer/ui` 的 `dropdown-menu` 组件（已有）、`avatar` 组件（已有）
- **路由**：登录/注册页面不再被 AppLayout 包裹，需确认页面样式不受影响
- **i18n**：可能需要新增 Header 用户菜单相关翻译键
