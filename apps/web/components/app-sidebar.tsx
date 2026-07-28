"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuthStore } from "@/store/auth";
import {
  menuConfig,
  filterMenuByRole,
  type MenuEntry,
  type MenuItemConfig,
  type MenuGroupConfig,
  type MenuRole,
} from "@/config/menu";

export function AppSidebar() {
  const pathname = usePathname();
  const t = useTranslations("layout");
  const tCommon = useTranslations("common");
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const filteredMenu = filterMenuByRole(
    menuConfig,
    user?.role as MenuRole | undefined
  );

  // Pre-scan: identify which groups have at least one visible item after them
  const groupHasItems = new Set<string>();
  let pendingGroup: string | null = null;
  for (const entry of filteredMenu) {
    if (entry.type === "group") {
      pendingGroup = entry.key;
    } else {
      if (pendingGroup) {
        groupHasItems.add(pendingGroup);
        pendingGroup = null;
      }
    }
  }

  function isGroup(entry: MenuEntry): entry is MenuGroupConfig {
    return entry.type === "group";
  }

  function isItem(entry: MenuEntry): entry is MenuItemConfig {
    return entry.type !== "group";
  }

  function getRoleLabel(role: string): string {
    if (role === "admin") return tCommon("roleAdmin");
    if (role === "user") return tCommon("roleUser");
    return role;
  }

  return (
    <aside className="w-[220px] bg-sidebar text-sidebar-foreground flex flex-col shrink-0">
      {/* Top Logo area */}
      <div className="h-14 flex items-center gap-2 px-5 border-b border-sidebar-border">
        <span className="text-xl">🤖</span>
        <span className="font-semibold text-sm">{tCommon("appName")}</span>
      </div>

      {/* Menu area */}
      <nav className="flex-1 overflow-y-auto py-2">
        {filteredMenu.map((entry) => {
          if (isGroup(entry)) {
            // Skip group title if no visible items under it
            if (!groupHasItems.has(entry.key)) return null;
            return (
              <div
                key={entry.key}
                className="px-5 pt-4 pb-1 text-xs text-muted-foreground uppercase tracking-wider"
              >
                {t(entry.labelKey.replace("layout.", "") as Parameters<typeof t>[0])}
              </div>
            );
          }

          if (isItem(entry)) {
            const Icon = entry.icon;
            const isActive = pathname === entry.href;
            return (
              <Link
                key={entry.key}
                href={entry.href}
                className={`flex items-center gap-3 px-5 py-2.5 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-sidebar-primary text-sidebar-primary-foreground"
                    : "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                }`}
              >
                {Icon && <Icon className="h-4 w-4 shrink-0" />}
                <span>{t(entry.labelKey.replace("layout.", "") as Parameters<typeof t>[0])}</span>
              </Link>
            );
          }

          return null;
        })}
      </nav>

      {/* Bottom user area */}
      {user && (
        <div className="border-t border-sidebar-border px-5 py-3">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-sidebar-accent flex items-center justify-center text-xs font-medium text-sidebar-accent-foreground shrink-0">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{user.username}</div>
              <div className="text-xs text-muted-foreground">{getRoleLabel(user.role)}</div>
            </div>
          </div>
          <button
            onClick={logout}
            className="mt-2 text-xs text-muted-foreground hover:text-sidebar-foreground transition-colors"
          >
            {tCommon("logout")}
          </button>
        </div>
      )}
    </aside>
  );
}
