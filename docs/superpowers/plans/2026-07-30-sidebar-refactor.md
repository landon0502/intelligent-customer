# 侧边栏重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有手写 aside 侧边栏重构为基于 shadcn Sidebar 组件的实现，支持侧边栏折叠（icon/offcanvas）和分组子菜单收放。

**Architecture:** 在 AppLayout 中用 SidebarProvider 包裹 Sidebar + SidebarInset，替换旧版 flex 布局。AppSidebar 基于 shadcn Sidebar 组件体系，支持 collapsible prop 切换折叠模式，分组菜单使用 SidebarMenuSub 实现收放。SidebarTrigger 移至 AppHeader 左侧。

**Tech Stack:** React 19, Next.js, shadcn Sidebar (基于 @base-ui/react), next-intl, zustand (auth store), lucide-react

## Global Constraints

- UI 组件从 `@intelligent-customer/ui/components/*` 导入，不使用 Radix UI（项目使用 @base-ui/react）
- 国际化使用 `next-intl`，菜单翻译 key 在 `layout` 命名空间下
- 菜单配置和角色过滤逻辑不变（`@/config/menu`）
- 导航方式为 `onTabChange` 回调，不使用 Link 路由跳转
- 侧边栏状态通过 cookie 持久化（shadcn Sidebar 内置）

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `apps/web/components/layout/app-sidebar.tsx` | 删除 | 旧版手写 aside，被新 AppSidebar 替代 |
| `apps/web/components/layout/sidebar.tsx` | 重写 | 新 AppSidebar：shadcn Sidebar + 可配置折叠 + 分组子菜单收放 |
| `apps/web/components/layout/app-layout.tsx` | 改造 | SidebarProvider + SidebarInset 包裹 |
| `apps/web/components/layout/app-header.tsx` | 改造 | 加入 SidebarTrigger |
| `apps/web/app/page.tsx` | 改造 | 传递 activeTab/onTabChange/collapsible 给 AppLayout |

---

### Task 1: 重写 AppSidebar 组件

**Files:**
- Rewrite: `apps/web/components/layout/sidebar.tsx`
- Delete: `apps/web/components/layout/app-sidebar.tsx`

**Interfaces:**
- Consumes: `menuConfig`, `filterMenuByRole`, `MenuItemConfig`, `MenuGroupConfig`, `MenuEntry`, `MenuRole` from `@/config/menu`; `useAuthStore` from `@/store/auth`; shadcn Sidebar components from `@intelligent-customer/ui/components/sidebar`
- Produces: `AppSidebar` component with props `{ activeTab: string; onTabChange?: (tab: string) => void; collapsible?: "icon" | "offcanvas" }`

- [ ] **Step 1: 重写 sidebar.tsx 为新 AppSidebar**

将 `apps/web/components/layout/sidebar.tsx` 完整替换为以下内容：

```tsx
"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import { ChevronRight } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@intelligent-customer/ui/components/sidebar"
import { useAuthStore } from "@/store/auth"
import {
  menuConfig,
  filterMenuByRole,
  type MenuItemConfig,
  type MenuGroupConfig,
  type MenuRole,
} from "@/config/menu"

interface AppSidebarProps {
  activeTab: string
  onTabChange?: (tab: string) => void
  collapsible?: "icon" | "offcanvas"
}

export function AppSidebar({
  activeTab,
  onTabChange,
  collapsible = "icon",
}: AppSidebarProps) {
  const t = useTranslations("layout")
  const user = useAuthStore((s) => s.user)

  const filteredMenu = filterMenuByRole(
    menuConfig,
    user?.role as MenuRole | undefined
  )

  // 追踪每个分组的展开/收起状态
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(
    () => {
      const initial: Record<string, boolean> = {}
      for (const entry of filteredMenu) {
        if (entry.type === "group") {
          initial[entry.key] = true // 默认展开
        }
      }
      return initial
    }
  )

  function toggleGroup(key: string) {
    setExpandedGroups((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  function renderMenuItem(item: MenuItemConfig) {
    const Icon = item.icon
    const isActive = item.href === activeTab
    const label = t(item.labelKey.replace("layout.", "") as Parameters<typeof t>[0])

    return (
      <SidebarMenuItem key={item.key}>
        <SidebarMenuButton
          isActive={isActive}
          onClick={() => onTabChange?.(item.href)}
          tooltip={label}
        >
          <Icon className="size-4" />
          <span>{label}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    )
  }

  function renderGroup(group: MenuGroupConfig) {
    const isExpanded = expandedGroups[group.key] ?? true
    const label = t(group.labelKey.replace("layout.", "") as Parameters<typeof t>[0])

    return (
      <SidebarGroup key={group.key}>
        <SidebarGroupLabel
          className="cursor-pointer select-none hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          onClick={() => toggleGroup(group.key)}
        >
          <ChevronRight
            className={`size-4 transition-transform duration-200 ${
              isExpanded ? "rotate-90" : ""
            }`}
          />
          <span>{label}</span>
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {isExpanded &&
              group.children?.map((child) => {
                const Icon = child.icon
                const isActive = child.href === activeTab
                const childLabel = t(
                  child.labelKey.replace("layout.", "") as Parameters<typeof t>[0]
                )

                return (
                  <SidebarMenuItem key={child.key}>
                    <SidebarMenuButton
                      isActive={isActive}
                      onClick={() => onTabChange?.(child.href)}
                      tooltip={childLabel}
                    >
                      <Icon className="size-4" />
                      <span>{childLabel}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    )
  }

  return (
    <Sidebar collapsible={collapsible}>
      <SidebarHeader className="h-16 flex items-center gap-2 border-b border-sidebar-border px-4">
        <span className="text-xl">🤖</span>
        <span className="text-sm font-semibold truncate group-data-[collapsible=icon]:hidden">
          AI 客服系统
        </span>
      </SidebarHeader>

      <SidebarContent>
        {filteredMenu.map((entry) => {
          if (entry.type === "group") {
            return renderGroup(entry)
          }
          // 顶级菜单项放在一个 SidebarGroup 中
          return (
            <SidebarGroup key={entry.key}>
              <SidebarGroupContent>
                <SidebarMenu>{renderMenuItem(entry)}</SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )
        })}
      </SidebarContent>
    </Sidebar>
  )
}
```

- [ ] **Step 2: 删除旧版 app-sidebar.tsx**

```bash
rm apps/web/components/layout/app-sidebar.tsx
```

- [ ] **Step 3: 提交**

```bash
git add apps/web/components/layout/sidebar.tsx apps/web/components/layout/app-sidebar.tsx
git commit -m "feat: rewrite AppSidebar with shadcn Sidebar — collapsible + group expand/collapse"
```

---

### Task 2: 改造 AppLayout — 加入 SidebarProvider + SidebarInset

**Files:**
- Modify: `apps/web/components/layout/app-layout.tsx`

**Interfaces:**
- Consumes: `AppSidebar` from `@/components/layout/sidebar` (Task 1); `SidebarProvider`, `SidebarInset` from `@intelligent-customer/ui/components/sidebar`
- Produces: `AppLayout` component with props `{ children: React.ReactNode; activeTab: string; onTabChange?: (tab: string) => void; collapsible?: "icon" | "offcanvas" }`

- [ ] **Step 1: 重写 app-layout.tsx**

将 `apps/web/components/layout/app-layout.tsx` 完整替换为：

```tsx
"use client"

import { AppSidebar } from "@/components/layout/sidebar"
import { AppHeader } from "@/components/layout/app-header"
import {
  SidebarProvider,
  SidebarInset,
} from "@intelligent-customer/ui/components/sidebar"

interface AppLayoutProps {
  children: React.ReactNode
  activeTab: string
  onTabChange?: (tab: string) => void
  collapsible?: "icon" | "offcanvas"
}

export function AppLayout({
  children,
  activeTab,
  onTabChange,
  collapsible = "icon",
}: AppLayoutProps) {
  return (
    <SidebarProvider>
      <AppSidebar
        activeTab={activeTab}
        onTabChange={onTabChange}
        collapsible={collapsible}
      />
      <SidebarInset>
        <AppHeader />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  )
}
```

- [ ] **Step 2: 提交**

```bash
git add apps/web/components/layout/app-layout.tsx
git commit -m "feat: wrap AppLayout with SidebarProvider + SidebarInset"
```

---

### Task 3: 改造 AppHeader — 加入 SidebarTrigger

**Files:**
- Modify: `apps/web/components/layout/app-header.tsx`

**Interfaces:**
- Consumes: `SidebarTrigger`, `SidebarSeparator` from `@intelligent-customer/ui/components/sidebar`; `useSidebar` from `@intelligent-customer/ui/components/sidebar`

- [ ] **Step 1: 在 app-header.tsx 中添加 SidebarTrigger**

在文件顶部导入区域添加：

```tsx
import {
  SidebarTrigger,
  SidebarSeparator,
} from "@intelligent-customer/ui/components/sidebar"
```

将未登录状态的 header 替换为：

```tsx
if (!user) {
  return (
    <header className="flex h-14 shrink-0 items-center border-b bg-background px-4 gap-2">
      <SidebarTrigger className="-ml-1" />
      <SidebarSeparator className="mr-2 h-4" />
      <h1 className="text-base font-semibold">{pageTitle}</h1>
    </header>
  )
}
```

将已登录状态的 header 替换为：

```tsx
return (
  <header className="flex h-14 shrink-0 items-center justify-between border-b bg-background px-4">
    <div className="flex items-center gap-2">
      <SidebarTrigger className="-ml-1" />
      <SidebarSeparator className="mr-2 h-4" />
      <h1 className="text-base font-semibold">{pageTitle}</h1>
    </div>
    <div className="flex items-center gap-2">
      {/* 语言切换 DropdownMenu — 保持不变 */}
      <DropdownMenu>
        <DropdownMenuTrigger className="inline-flex h-8 w-8 items-center justify-center rounded-md text-xs font-medium transition-colors hover:bg-accent hover:text-accent-foreground">
          {localeAbbr[currentLocale] ?? currentLocale}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {localeOptions.map((locale) => (
            <DropdownMenuItem
              key={locale}
              onClick={() => handleLocaleSelect(locale)}
            >
              {tLanguage(locale === "zh-CN" ? "zhCN" : "enUS")}
              {currentLocale === locale && (
                <Check className="ml-auto size-4" />
              )}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* 主题切换 DropdownMenu — 保持不变 */}
      <DropdownMenu>
        <DropdownMenuTrigger className="inline-flex h-8 w-8 items-center justify-center rounded-md text-xs font-medium transition-colors hover:bg-accent hover:text-accent-foreground">
          <ThemeIcon theme={theme} />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {mounted && (
            <>
              <DropdownMenuRadioGroup
                value={theme}
                onValueChange={(value) => setTheme(value)}
              >
                {themeOptions.map((value) => {
                  const icon = <ThemeIcon theme={value} />
                  return (
                    <DropdownMenuRadioItem key={value} value={value}>
                      {icon}
                      {tTheme(value)}
                    </DropdownMenuRadioItem>
                  )
                })}
              </DropdownMenuRadioGroup>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* 用户头像 DropdownMenu — 保持不变 */}
      <DropdownMenu>
        <DropdownMenuTrigger className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-accent text-xs font-medium text-accent-foreground transition-colors hover:bg-accent/80 focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:outline-none">
          {user.username.charAt(0).toUpperCase()}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuGroup>
            <DropdownMenuLabel className="flex flex-col gap-0.5">
              <span className="text-sm font-medium text-foreground">
                {user.username}
              </span>
              <span className="text-xs text-muted-foreground">
                {getRoleLabel(user.role)}
              </span>
            </DropdownMenuLabel>

            <DropdownMenuSeparator />

            <DropdownMenuItem>
              <Settings className="size-4" />
              {tCommon("settings")}
            </DropdownMenuItem>
            <DropdownMenuSeparator />

            <DropdownMenuItem variant="destructive" onClick={handleLogout}>
              <LogOut className="size-4" />
              {tCommon("logout")}
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  </header>
)
```

- [ ] **Step 2: 提交**

```bash
git add apps/web/components/layout/app-header.tsx
git commit -m "feat: add SidebarTrigger to AppHeader"
```

---

### Task 4: 改造 page.tsx — 传递 props 给 AppLayout

**Files:**
- Modify: `apps/web/app/page.tsx`

**Interfaces:**
- Consumes: `AppLayout` from `@/components/layout/app-layout` (Task 2); `useAuthStore` from `@/store/auth`

- [ ] **Step 1: 更新 page.tsx 传递 activeTab 和 onTabChange**

将 `apps/web/app/page.tsx` 替换为：

```tsx
"use client"

import { useEffect, useState } from "react"
import { useTranslations } from "next-intl"
import { useAuthStore } from "@/store/auth"
import { AppLayout } from "@/components/layout/app-layout"
import { ChatPage } from "@/components/chat/chat-page"

export default function Page() {
  const { initAuth, loading } = useAuthStore()
  const t = useTranslations("common")
  const [activeTab, setActiveTab] = useState("/")

  useEffect(() => {
    initAuth()
  }, [initAuth])

  if (loading) {
    return (
      <AppLayout activeTab={activeTab} onTabChange={setActiveTab}>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">{t("loading")}</p>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout activeTab={activeTab} onTabChange={setActiveTab}>
      <ChatPage />
    </AppLayout>
  )
}
```

- [ ] **Step 2: 提交**

```bash
git add apps/web/app/page.tsx
git commit -m "feat: pass activeTab/onTabChange to AppLayout from page"
```

---

### Task 5: 验证构建与功能

**Files:** 无新文件

- [ ] **Step 1: 运行 TypeScript 类型检查**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && pnpm --filter web typecheck
```

Expected: 无类型错误

- [ ] **Step 2: 运行 lint**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && pnpm --filter web lint
```

Expected: 无 lint 错误

- [ ] **Step 3: 启动开发服务器验证**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && pnpm --filter web dev
```

验证以下功能：
1. 侧边栏正常显示菜单项和分组
2. 点击分组标题可展开/收起子菜单
3. 点击 SidebarTrigger 可折叠侧边栏（icon 模式：折叠后显示图标 + tooltip）
4. 菜单项点击触发 onTabChange 回调
5. 角色过滤正常（admin 看到管理组，普通用户看不到）
6. 移动端侧边栏以 Sheet 形式展示

- [ ] **Step 4: 提交最终状态（如有修复）**

```bash
git add -A
git commit -m "fix: address build/typecheck issues from sidebar refactor"
```
