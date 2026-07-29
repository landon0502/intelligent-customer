// apps/web/config/menu.ts
import type { LucideIcon } from "lucide-react"
import { MessageSquare, BookOpen, Users, Settings, Wrench } from "lucide-react"

export type MenuRole = "admin" | "user"

export interface MenuItemConfig {
  type?: "item"
  key: string
  labelKey: string
  href: string
  icon: LucideIcon
  roles?: MenuRole[]
}
export interface MenuGroupConfig {
  type: "group"
  key: string
  labelKey: string
  children?: MenuItemConfig[]
}
export type MenuEntry = MenuGroupConfig | MenuItemConfig

export const menuConfig: MenuEntry[] = [
  { key: "chat", labelKey: "layout.menuChat", href: "/", icon: MessageSquare },
  {
    type: "group",
    key: "management",
    labelKey: "layout.menuGroupManagement",
    children: [
      {
        key: "knowledge",
        labelKey: "layout.menuKnowledge",
        href: "/knowledge",
        icon: BookOpen,
        roles: ["admin"],
      },
      {
        key: "users",
        labelKey: "layout.menuUsers",
        href: "/users",
        icon: Users,
        roles: ["admin"],
      },
      {
        key: "config",
        labelKey: "layout.menuConfig",
        href: "/config",
        icon: Settings,
        roles: ["admin"],
      },
      {
        key: "tools",
        labelKey: "layout.menuTools",
        href: "/tools",
        icon: Wrench,
        roles: ["admin"],
      },
    ],
  },
]

export function filterMenuByRole(
  entries: MenuEntry[],
  role: MenuRole | undefined
): MenuEntry[] {
  if (!role) return []

  const result: MenuEntry[] = []

  for (const entry of entries) {
    if (entry.type === "group") {
      // Filter children within the group by role
      const filteredChildren = entry.children?.filter(
        (child) => !child.roles || child.roles.includes(role)
      )
      // Skip group if no visible children
      if (filteredChildren && filteredChildren.length > 0) {
        result.push({ ...entry, children: filteredChildren })
      }
    } else {
      // Top-level item: filter by role
      if (!entry.roles || entry.roles.includes(role)) {
        result.push(entry)
      }
    }
  }

  return result
}

export const titleKeyMap: Record<string, string> = {
  "/": "layout.menuChat",
  "/knowledge": "layout.menuKnowledge",
  "/users": "layout.menuUsers",
  "/config": "layout.menuConfig",
  "/tools": "layout.menuTools",
}
