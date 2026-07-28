## 1. 组件目录重组

- [x] 1.1 创建 `components/layout/` 目录，将 `app-layout.tsx`、`app-header.tsx`、`app-sidebar.tsx`、`theme-switcher.tsx`、`language-switcher.tsx` 移入该目录
- [x] 1.2 更新所有 import 路径（`app-layout.tsx` 内部引用、`app/layout.tsx`、`app/page.tsx` 等）

## 2. AppLayout 渲染策略变更

- [x] 2.1 从 `app/layout.tsx` 移除 AppLayout 引入和渲染，仅保留 ThemeProvider 和 NextIntlClientProvider
- [x] 2.2 在 `app/page.tsx` 中引入 AppLayout 并包裹页面内容

## 3. Header 用户 DropdownMenu

- [x] 3.1 重写 `app-header.tsx`：右侧新增用户头像 DropdownMenu，整合用户信息（首项不可点击）、语言切换、主题切换、退出登录
- [x] 3.2 从 `app-sidebar.tsx` 移除底部用户信息和退出登录区域

## 4. 国际化切换按钮样式

- [x] 4.1 修改 `language-switcher.tsx`：DropdownMenuTrigger 只显示 `localeAbbr[currentLocale]` 文字值，移除 Globe 图标

## 5. 菜单项圆角移除

- [x] 5.1 修改 `app-sidebar.tsx`：菜单项 Link 的 `rounded-md` class 移除

## 6. i18n 翻译键补充

- [x] 6.1 检查并补充 Header 用户菜单相关翻译键（如"系统设置"等）
