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

export const menuConfig: MenuEntry[] = [
  { key: "chat", labelKey: "layout.menuChat", href: "/", icon: MessageSquare },
  { type: "group", key: "management", labelKey: "layout.menuGroupManagement" },
  { key: "knowledge", labelKey: "layout.menuKnowledge", href: "/knowledge", icon: BookOpen, roles: ["admin"] },
  { key: "users", labelKey: "layout.menuUsers", href: "/users", icon: Users, roles: ["admin"] },
  { key: "config", labelKey: "layout.menuConfig", href: "/config", icon: Settings, roles: ["admin"] },
  { key: "tools", labelKey: "layout.menuTools", href: "/tools", icon: Wrench, roles: ["admin"] },
];

export function filterMenuByRole(
  entries: MenuEntry[],
  role: MenuRole | undefined
): MenuEntry[] {
  if (!role) return [];
  return entries.filter((entry) => {
    if (entry.type === "group") return true;
    return !entry.roles || entry.roles.includes(role);
  });
}

export const titleKeyMap: Record<string, string> = {
  "/": "layout.menuChat",
  "/knowledge": "layout.menuKnowledge",
  "/users": "layout.menuUsers",
  "/config": "layout.menuConfig",
  "/tools": "layout.menuTools",
};
