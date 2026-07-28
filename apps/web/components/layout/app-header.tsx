"use client";

import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import { titleKeyMap } from "@/config/menu";
import { useAuthStore } from "@/store/auth";
import { routing } from "@/i18n/routing";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuLabel,
} from "@intelligent-customer/ui/components/dropdown-menu";
import { Sun, Moon, Monitor, Check, LogOut, Settings } from "lucide-react";

const localeOptions = routing.locales;

const localeAbbr: Record<string, string> = {
  "zh-CN": "中",
  "en-US": "EN",
};

const themeOptions = ["light", "dark", "system"] as const;

const emptySubscribe = () => () => {};

function setLocaleCookie(locale: string) {
  document.cookie = `NEXT_LOCALE=${locale};path=/;max-age=31536000`;
}

export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const currentLocale = useLocale();
  const t = useTranslations("layout");
  const tCommon = useTranslations("common");
  const tTheme = useTranslations("theme");
  const tLanguage = useTranslations("language");
  const { theme, setTheme } = useTheme();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const mounted = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );

  const titleKey = titleKeyMap[pathname];
  const pageTitle = titleKey
    ? t(titleKey.replace("layout.", "") as Parameters<typeof t>[0])
    : tCommon("appName");

  function getRoleLabel(role: string): string {
    if (role === "admin") return tCommon("roleAdmin");
    if (role === "user") return tCommon("roleUser");
    return role;
  }

  const handleLocaleSelect = (locale: string) => {
    setLocaleCookie(locale);
    router.refresh();
  };

  const handleLogout = () => {
    logout();
  };

  if (!user) {
    return (
      <header className="h-14 bg-background border-b flex items-center px-6 shrink-0">
        <h1 className="text-base font-semibold">{pageTitle}</h1>
      </header>
    );
  }

  return (
    <header className="h-14 bg-background border-b flex items-center justify-between px-6 shrink-0">
      <h1 className="text-base font-semibold">{pageTitle}</h1>
      <div className="flex items-center gap-2">
        {/* Language switcher - text only */}
        <DropdownMenu>
          <DropdownMenuTrigger
            className="inline-flex items-center justify-center h-8 w-8 text-xs font-medium rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            {localeAbbr[currentLocale] ?? currentLocale}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {localeOptions.map((locale) => (
              <DropdownMenuItem key={locale} onClick={() => handleLocaleSelect(locale)}>
                {tLanguage(locale === "zh-CN" ? "zhCN" : "enUS")}
                {currentLocale === locale && <Check className="size-4 ml-auto" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User avatar dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger
            className="inline-flex items-center justify-center rounded-full h-8 w-8 bg-accent text-accent-foreground text-xs font-medium hover:bg-accent/80 transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          >
            {user.username.charAt(0).toUpperCase()}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            {/* First item: user info (non-interactive) */}
            <DropdownMenuLabel className="flex flex-col gap-0.5">
              <span className="text-sm font-medium text-foreground">{user.username}</span>
              <span className="text-xs text-muted-foreground">{getRoleLabel(user.role)}</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />

            {/* Theme switcher */}
            {mounted && (
              <>
                <DropdownMenuRadioGroup
                  value={theme}
                  onValueChange={(value) => setTheme(value)}
                >
                  {themeOptions.map((value) => {
                    const icon =
                      value === "light" ? (
                        <Sun className="size-4" />
                      ) : value === "dark" ? (
                        <Moon className="size-4" />
                      ) : (
                        <Monitor className="size-4" />
                      );
                    return (
                      <DropdownMenuRadioItem key={value} value={value}>
                        {icon}
                        {tTheme(value)}
                      </DropdownMenuRadioItem>
                    );
                  })}
                </DropdownMenuRadioGroup>
                <DropdownMenuSeparator />
              </>
            )}

            {/* System settings (placeholder) */}
            <DropdownMenuItem>
              <Settings className="size-4" />
              {tCommon("settings")}
            </DropdownMenuItem>
            <DropdownMenuSeparator />

            {/* Logout */}
            <DropdownMenuItem variant="destructive" onClick={handleLogout}>
              <LogOut className="size-4" />
              {tCommon("logout")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
