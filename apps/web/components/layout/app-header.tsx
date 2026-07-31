"use client"

import { usePathname, useRouter } from "next/navigation"
import { useLocale, useTranslations } from "next-intl"

import { useTheme } from "next-themes"
import { titleKeyMap } from "@/config/menu"
import { useAuthStore } from "@/store/auth"
import { routing } from "@/i18n/routing"
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuLabel,
  DropdownMenuGroup,
} from "@intelligent-customer/ui/components/dropdown-menu"
import { Sun, Moon, Monitor, Check, LogOut, Settings } from "lucide-react"
import {
  SidebarTrigger,
  SidebarSeparator,
} from "@intelligent-customer/ui/components/sidebar"
import { useMounted } from "@/hooks"

const localeOptions = routing.locales

const localeAbbr: Record<string, string> = {
  "zh-CN": "中",
  "en-US": "EN",
}

const themeOptions = ["light", "dark", "system"] as const

function setLocaleCookie(locale: string) {
  document.cookie = `NEXT_LOCALE=${locale};path=/;max-age=31536000`
}

function ThemeIcon({ theme }: { theme?: string }) {
  return theme === "light" ? (
    <Sun className="size-4" />
  ) : theme === "dark" ? (
    <Moon className="size-4" />
  ) : (
    <Monitor className="size-4" />
  )
}

export function AppHeader() {
  const pathname = usePathname()
  const router = useRouter()
  const currentLocale = useLocale()
  const t = useTranslations("layout")
  const tCommon = useTranslations("common")
  const tTheme = useTranslations("theme")
  const tLanguage = useTranslations("language")
  const { theme, setTheme } = useTheme()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  const mounted = useMounted()
  const titleKey = titleKeyMap[pathname]
  const pageTitle = titleKey
    ? t(titleKey.replace("layout.", "") as Parameters<typeof t>[0])
    : tCommon("appName")

  function getRoleLabel(role: string): string {
    if (role === "admin") return tCommon("roleAdmin")
    if (role === "user") return tCommon("roleUser")
    return role
  }

  const handleLocaleSelect = (locale: string) => {
    setLocaleCookie(locale)
    router.refresh()
  }

  const handleLogout = () => {
    logout()
  }

  if (!user) {
    return (
      <header className="flex h-14 shrink-0 items-center justify-between border-b bg-background px-4">
        <SidebarTrigger className="-ml-1" />
        <SidebarSeparator orientation="vertical" className="mr-2 h-8" />
        <h1 className="text-base font-semibold">{pageTitle}</h1>
      </header>
    )
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b bg-background px-4">
      <div className="flex items-center gap-2">
        <SidebarTrigger className="-ml-1" />
        <SidebarSeparator orientation="vertical" className="mr-2 h-8" />
        <h1 className="text-base font-semibold">{pageTitle}</h1>
      </div>
      <div className="flex items-center gap-2">
        {/* Language switcher - text only */}
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

        <DropdownMenu>
          <DropdownMenuTrigger className="inline-flex h-8 w-8 items-center justify-center rounded-md text-xs font-medium transition-colors hover:bg-accent hover:text-accent-foreground">
            <ThemeIcon theme={theme} />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {/* Theme switcher */}
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

        {/* User avatar dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-accent text-xs font-medium text-accent-foreground transition-colors hover:bg-accent/80 focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:outline-none">
            {user.username.charAt(0).toUpperCase()}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            {/* First item: user info (non-interactive) */}
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
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
