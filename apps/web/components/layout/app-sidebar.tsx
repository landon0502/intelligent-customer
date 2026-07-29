"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuthStore } from "@/store/auth";
import {
  menuConfig,
  filterMenuByRole,
  type MenuItemConfig,
  type MenuRole,
} from "@/config/menu";

export function AppSidebar() {
  const pathname = usePathname();
  const t = useTranslations("layout");
  const tCommon = useTranslations("common");
  const user = useAuthStore((s) => s.user);

  const filteredMenu = filterMenuByRole(
    menuConfig,
    user?.role as MenuRole | undefined
  );

  function renderMenuItem(item: MenuItemConfig) {
    const Icon = item.icon;
    const isActive = pathname === item.href;
    return (
      <Link
        key={item.key}
        href={item.href}
        className={`flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${
          isActive
            ? "bg-sidebar-primary text-sidebar-primary-foreground"
            : "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        }`}
      >
        {Icon && <Icon className="h-4 w-4 shrink-0" />}
        <span>{t(item.labelKey.replace("layout.", "") as Parameters<typeof t>[0])}</span>
      </Link>
    );
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
          if (entry.type === "group") {
            return (
              <div key={entry.key}>
                <div className="px-5 pt-4 pb-1 text-xs text-muted-foreground uppercase tracking-wider">
                  {t(entry.labelKey.replace("layout.", "") as Parameters<typeof t>[0])}
                </div>
                {entry.children?.map((child) => renderMenuItem(child))}
              </div>
            );
          }

          return renderMenuItem(entry);
        })}
      </nav>
    </aside>
  );
}
