---
comet_change: web-layout-shell
role: technical-design
canonical_spec: openspec
---

# Web Layout Shell — 深度技术设计

## 1. i18n 运行时架构

### 1.1 集成路径

采用路径 A：`getRequestConfig` + cookie locale，不修改路由结构和 middleware。

### 1.2 文件结构

```
apps/web/
├── i18n/
│   ├── request.ts      # getRequestConfig，从 cookie 读取 locale，加载 messages
│   └── routing.ts      # locales 列表、defaultLocale、cookie 名
├── messages/
│   ├── zh-CN.json      # 重写，AI 客服系统翻译
│   └── en-US.json      # 重写，对应英文翻译
└── next.config.ts      # 添加 createNextIntlPlugin()
```

### 1.3 request.ts 实现

```typescript
import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";
import { routing } from "./routing";

export default getRequestConfig(async () => {
  let locale = routing.defaultLocale;

  // 从 cookie 读取用户偏好 locale
  const cookieStore = await cookies();
  const preferred = cookieStore.get(routing.cookieName)?.value;
  if (preferred && routing.locales.includes(preferred)) {
    locale = preferred;
  }

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
```

### 1.4 routing.ts 实现

```typescript
export const routing = {
  locales: ["zh-CN", "en-US"] as const,
  defaultLocale: "zh-CN" as const,
  cookieName: "NEXT_LOCALE",
};

export type Locale = (typeof routing.locales)[number];
```

### 1.5 next.config.ts 修改

```typescript
import createNextIntlPlugin from "next-intl/plugin";
const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const nextConfig: NextConfig = { /* 现有配置 */ };
export default withNextIntl(nextConfig);
```

### 1.6 语言切换实现

LanguageSwitcher 切换语言时：
1. 调用 `document.cookie = 'NEXT_LOCALE=zh-CN;path=/;max-age=31536000'` 设置 cookie
2. 调用 `router.refresh()` 触发 server component 重新渲染（重新读取 cookie → 新 locale → 新 messages）

不需要改变 URL，不需要页面跳转。

### 1.7 root layout 集成

```typescript
// app/layout.tsx (async Server Component)
import { getLocale, getMessages } from "next-intl/server";
import { NextIntlClientProvider } from "next-intl";

export default async function RootLayout({ children }) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body>
        <NextIntlClientProvider locale={locale} messages={messages}>
          <ThemeProvider>
            <AppLayout>{children}</AppLayout>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

## 2. 菜单配置系统

### 2.1 数据结构

```typescript
// apps/web/config/menu.ts
import type { LucideIcon } from "lucide-react";
import { MessageSquare, BookOpen, Users, Settings, Wrench } from "lucide-react";

export type MenuRole = "admin" | "user";

export interface MenuGroupConfig {
  type: "group";
  key: string;
  labelKey: string;
}

export interface MenuItemConfig {
  type?: "item";
  key: string;
  labelKey: string;
  href: string;
  icon: LucideIcon;
  roles?: MenuRole[];
}

export type MenuEntry = MenuGroupConfig | MenuItemConfig;
```

### 2.2 菜单配置

```typescript
export const menuConfig: MenuEntry[] = [
  { key: "chat", labelKey: "layout.menuChat", href: "/", icon: MessageSquare },
  { type: "group", key: "management", labelKey: "layout.menuGroupManagement" },
  { key: "knowledge", labelKey: "layout.menuKnowledge", href: "/knowledge", icon: BookOpen, roles: ["admin"] },
  { key: "users", labelKey: "layout.menuUsers", href: "/users", icon: Users, roles: ["admin"] },
  { key: "config", labelKey: "layout.menuConfig", href: "/config", icon: Settings, roles: ["admin"] },
  { key: "tools", labelKey: "layout.menuTools", href: "/tools", icon: Wrench, roles: ["admin"] },
];
```

### 2.3 角色过滤（纯函数，可单元测试）

```typescript
export function filterMenuByRole(
  entries: MenuEntry[],
  role: MenuRole | undefined
): MenuEntry[] {
  if (!role) return [];
  return entries.filter((entry) => {
    if (entry.type === "group") return true; // 分组始终保留，后续渲染时判断分组下是否有可见项
    return !entry.roles || entry.roles.includes(role);
  });
}
```

**注意**：分组 "management" 在过滤后如果其下所有 item 都被过滤掉，渲染时应隐藏该分组标题。在 Sidebar 渲染逻辑中处理：遍历时记录当前分组，如果分组下无可见 item 则跳过分组标题。

### 2.4 Header 标题映射

```typescript
// apps/web/config/menu.ts
export const titleKeyMap: Record<string, string> = {
  "/": "layout.menuChat",
  "/knowledge": "layout.menuKnowledge",
  "/users": "layout.menuUsers",
  "/config": "layout.menuConfig",
  "/tools": "layout.menuTools",
};
```

## 3. Layout 组件详细设计

### 3.1 AppLayout

```typescript
// apps/web/components/app-layout.tsx
"use client";

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-svh">
      <AppSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <AppHeader />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### 3.2 AppSidebar

```
┌──────────────┐
│ 🤖 AI 客服   │ ← SidebarHeader, h-14 (56px)
├──────────────┤
│ 💬 智能对话   │ ← MenuItem, active 样式
│              │
│ 管理          │ ← MenuGroup, 小字灰色
│ 📚 知识库管理 │ ← MenuItem (admin only)
│ 👥 用户管理   │
│ ⚙️ 系统配置   │
│ 🔧 工具配置   │
├──────────────┤
│ 👤 admin     │ ← SidebarFooter
│    管理员     │
│    退出登录   │
└──────────────┘
```

**关键实现**：
- 宽度 `w-[220px]`，背景色 `bg-sidebar`，文字 `text-sidebar-foreground`
- Logo 区域：`h-14`（56px，与 Header 同高），底部 border
- 菜单项：`px-5 py-2.5 rounded-md`，hover 时 `bg-sidebar-accent text-sidebar-accent-foreground`，active 时 `bg-sidebar-primary text-sidebar-primary-foreground`
- 菜单分组：`px-5 pt-4 pb-1 text-xs text-muted-foreground uppercase tracking-wider`
- 底部用户信息：Avatar 占位圆形 + username + role 标签 + 退出登录
- 使用 `usePathname()` 判断当前路由高亮
- 使用 `useAuthStore()` 读取 user 和 logout
- 使用 `useTranslations('layout')` 获取菜单翻译

### 3.3 AppHeader

```
┌──────────────────────────────────────────────────────────────┐
│  智能对话                              🌙  🌐  │ ← h-14
└──────────────────────────────────────────────────────────────┘
```

- 左侧：页面标题（从 titleKeyMap + pathname 获取 i18n key，useTranslations 翻译）
- 右侧：ThemeSwitcher + LanguageSwitcher
- 高度 `h-14`，背景 `bg-background`，底部 `border-b`

### 3.4 ThemeSwitcher

- 使用 DropdownMenu，触发按钮为图标按钮
- 图标：resolvedTheme === "dark" ? `<Sun />` : `<Moon />`
- 三个选项：Light / Dark / System，每项使用 i18n 翻译（`theme.light`、`theme.dark`、`theme.system`）
- 当前 theme 对应项显示 check 标记
- 点击调用 `setTheme(value)`

### 3.5 LanguageSwitcher

- 使用 DropdownMenu，触发按钮为 🌐 图标 + 当前语言缩写
- 两个选项：简体中文 / English
- 切换时：
  1. `document.cookie = 'NEXT_LOCALE=zh-CN;path=/;max-age=31536000'`
  2. `router.refresh()`

## 4. 翻译文件结构

### 4.1 zh-CN.json

```json
{
  "common": {
    "appName": "AI 客服系统",
    "tagline": "智能客服，贴心服务",
    "loading": "加载中...",
    "logout": "退出登录",
    "roleAdmin": "管理员",
    "roleUser": "普通用户"
  },
  "layout": {
    "menuChat": "智能对话",
    "menuGroupManagement": "管理",
    "menuKnowledge": "知识库管理",
    "menuUsers": "用户管理",
    "menuConfig": "系统配置",
    "menuTools": "工具配置"
  },
  "theme": {
    "toggle": "切换主题",
    "light": "浅色",
    "dark": "深色",
    "system": "跟随系统"
  },
  "language": {
    "zhCN": "简体中文",
    "enUS": "English"
  }
}
```

### 4.2 en-US.json

```json
{
  "common": {
    "appName": "AI Customer Service",
    "tagline": "Smart Service, Thoughtful Care",
    "loading": "Loading...",
    "logout": "Log Out",
    "roleAdmin": "Admin",
    "roleUser": "User"
  },
  "layout": {
    "menuChat": "Smart Chat",
    "menuGroupManagement": "Management",
    "menuKnowledge": "Knowledge Base",
    "menuUsers": "User Management",
    "menuConfig": "System Config",
    "menuTools": "Tool Config"
  },
  "theme": {
    "toggle": "Toggle Theme",
    "light": "Light",
    "dark": "Dark",
    "system": "System"
  },
  "language": {
    "zhCN": "简体中文",
    "enUS": "English"
  }
}
```

## 5. shadcn 组件补充

通过 `pnpm dlx shadcn@latest add <component> -c apps/web` 添加，组件落入 `packages/ui/src/components/`：

| 组件 | 用途 | fallback |
|------|------|----------|
| dropdown-menu | ThemeSwitcher / LanguageSwitcher 下拉 | 手动基于 `@base-ui/react/menu` |
| avatar | Sidebar 用户头像 | 简单 div 圆形 |
| separator | Sidebar 分隔线 | `<hr>` 或 border |

## 6. 测试策略

| 测试目标 | 类型 | 具体内容 |
|---------|------|---------|
| `filterMenuByRole` | 单元 | admin 看全部、user 只看 chat、undefined 返回空 |
| `filterMenuByRole` 分组处理 | 单元 | 分组下无可见 item 时不输出分组 |
| LanguageSwitcher cookie | 单元 | mock document.cookie + router.refresh，验证调用 |
| AppSidebar 渲染 | 集成 | 不同 role 下菜单项数量和内容 |
| 主题切换 | 手动 | 切换 light/dark/system 验证样式 |
| 完整流程 | 手动 | 登录 → Layout → 主题切换 → 语言切换 → 退出 |

## 7. 边界条件

- **未登录态**：middleware 拦截，Layout 不会渲染。但组件内 `useAuthStore` 防御性检查 `if (!user)` 兜底
- **cookie 中 locale 值非法**：`request.ts` 校验 `routing.locales.includes(preferred)`，不匹配则回退 `defaultLocale`
- **菜单分组下所有 item 被角色过滤**：渲染时检测分组下无可见 item，跳过分组标题输出
- **非菜单路由页面**（如 `/login`）：不使用 AppLayout，单独 layout 或条件渲染
- **移动端**：本次不实现响应式折叠，Sidebar 固定 220px；后续 change 可扩展
