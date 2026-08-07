# 侧边栏重构设计：使用 shadcn Sidebar 组件

## 概述

将现有手写 `<aside>` 侧边栏重构为基于 shadcn Sidebar 组件体系的实现，支持侧边栏折叠（icon 模式和 offcanvas 模式）以及分组子菜单的收放功能。

## 现状分析

- `app-sidebar.tsx`：旧版，纯 `<aside>` 实现，固定 220px 宽度，无折叠功能，当前在用
- `sidebar.tsx`：新版，已使用 shadcn Sidebar 组件（`collapsible="icon"`），但未接入 `SidebarProvider`，无子菜单折叠
- `AppLayout`：使用旧版 `AppSidebar`，无 `SidebarProvider` 包裹
- shadcn Sidebar 组件已安装在 `packages/ui/src/components/sidebar.tsx`，功能完整

## 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 折叠模式 | 同时支持 icon 和 offcanvas | 用户需求，通过 `collapsible` prop 配置 |
| 子菜单收放 | 点击分组标题展开/收起 | 用户需求，使用 SidebarMenuSub 组件 |
| 导航方式 | onTabChange 回调 | 用户需求，与现有 sidebar.tsx 一致 |
| SidebarTrigger 位置 | AppHeader 左侧 | 更符合常见 UI 模式（VS Code、Notion 等） |

## 架构

### 布局结构

改造后布局链：

```
layout.tsx (全局) → page.tsx → AppLayout
  └─ SidebarProvider
       ├─ Sidebar (侧边栏主体)
       │    ├─ SidebarHeader (Logo + 应用名)
       │    ├─ SidebarContent (菜单区域)
       │    └─ SidebarFooter (折叠按钮，备用)
       └─ SidebarInset
            ├─ AppHeader (含 SidebarTrigger)
            └─ main (内容区)
```

`SidebarProvider` 包裹 `Sidebar` 和 `SidebarInset`，提供折叠状态上下文。`SidebarInset` 替代原来的 `flex-1` div，自动响应侧边栏折叠时的宽度变化。

### 侧边栏菜单结构

```
🤖 AI 客服系统          ← SidebarHeader
─────────────
💬 智能对话              ← 顶级菜单项（无折叠）
📁 管理 ▾               ← 分组标题，点击可收放
   📚 知识库管理         ← SidebarMenuSubItem
   👥 用户管理           ← SidebarMenuSubItem
   ⚙️ 系统配置           ← SidebarMenuSubItem
   🔧 工具配置           ← SidebarMenuSubItem
─────────────
[折叠按钮]              ← SidebarFooter (备用)
```

### AppHeader 布局

```
[≡] 页面标题                    [语言] [主题] [用户头像]
 ↑
 SidebarTrigger
```

## 组件设计

### AppSidebar (sidebar.tsx 改造)

Props：

```typescript
interface AppSidebarProps {
  activeTab: string
  onTabChange?: (tab: string) => void
  collapsible?: "icon" | "offcanvas"  // 默认 "icon"
}
```

实现要点：
- 使用 `Sidebar` 组件，`collapsible` 由 prop 传入
- 顶级菜单项：`SidebarMenuItem` + `SidebarMenuButton`（带 tooltip，折叠时显示）
- 分组菜单：`SidebarMenuItem` + `SidebarMenuButton`（带 ChevronRight 图标）+ `SidebarMenuSub` + `SidebarMenuSubItem` + `SidebarMenuSubButton`
- 分组标题点击通过 React state 控制展开/收起
- 折叠为 icon 模式时，子菜单自动隐藏（shadcn 内置 `group-data-[collapsible=icon]:hidden`）
- 使用 `useTranslations("layout")` 命名空间
- 修复 SidebarHeader 中重复嵌套的 div

### AppLayout (app-layout.tsx 改造)

```tsx
<SidebarProvider>
  <AppSidebar activeTab={activeTab} onTabChange={onTabChange} collapsible={collapsible} />
  <SidebarInset>
    <AppHeader />
    <main className="flex-1 overflow-y-auto p-6">{children}</main>
  </SidebarInset>
</SidebarProvider>
```

需要从 `@intelligent-customer/ui/components/sidebar` 导入 `SidebarProvider` 和 `SidebarInset`。

### AppHeader (app-header.tsx 改造)

在页面标题左侧添加 `SidebarTrigger`：

```tsx
<header>
  <SidebarTrigger />
  <Separator orientation="vertical" className="mx-2 h-4" />
  <h1>{pageTitle}</h1>
  {/* 现有功能不变 */}
</header>
```

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/web/components/layout/app-sidebar.tsx` | 删除 | 旧版手写 aside 实现 |
| `apps/web/components/layout/sidebar.tsx` | 重写 | 新 AppSidebar，支持可配置折叠模式 + 分组子菜单收放 |
| `apps/web/components/layout/app-layout.tsx` | 改造 | 加入 SidebarProvider + SidebarInset |
| `apps/web/components/layout/app-header.tsx` | 改造 | 加入 SidebarTrigger |
| `apps/web/config/menu.ts` | 不变 | — |
| `apps/web/messages/zh-CN.json` | 不变 | — |
| `apps/web/messages/en-US.json` | 不变 | — |

## 不涉及

- 菜单配置结构不变
- 翻译文件不变
- 认证/角色过滤逻辑不变
- packages/ui 中的 shadcn Sidebar 组件不变
