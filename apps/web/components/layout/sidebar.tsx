"use client"

import { useTranslations } from "next-intl"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarTrigger,
} from "@intelligent-customer/ui/components/sidebar"
import { useAuthStore } from "@/store/auth"
import {
  menuConfig,
  filterMenuByRole,
  type MenuItemConfig,
  type MenuRole,
} from "@/config/menu"

interface SidebarProps {
  activeTab: string
  onTabChange?: (tab: string) => void
}

export function AppSidebar({
  activeTab,
  onTabChange,
}: SidebarProps) {
  const t = useTranslations("common")
  const user = useAuthStore((s) => s.user)

  const filteredMenu = filterMenuByRole(
    menuConfig,
    user?.role as MenuRole | undefined
  )

  function renderMenuItem(item: MenuItemConfig) {
    const Icon = item.icon
    return (
      <SidebarMenuItem key={item.key}>
        <SidebarMenuButton
          isActive={item.href === activeTab}
          onClick={() => onTabChange?.(item.href)}
          tooltip={t(item.labelKey.replace("layout.", "") as Parameters<typeof t>[0])}
          className="h-9"
        >
          <Icon className="size-4" />
          <span>{t(item.labelKey.replace("layout.", "") as Parameters<typeof t>[0])}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    )
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="flex h-16 flex-row items-center gap-3 border-b border-sidebar-border px-3">
        <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-5">
          <span className="text-xl">🤖</span>
          <span className="text-sm font-semibold">{t("appName")}</span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarMenu className="gap-2">
            {filteredMenu.map((entry) => {
              if (entry.type === "group") {
                return (
                  <SidebarGroup key={entry.key}>
                    <SidebarMenu className="gap-2">
                      {entry.children?.map((child) => renderMenuItem(child))}
                    </SidebarMenu>
                  </SidebarGroup>
                )
              }
              return renderMenuItem(entry)
            })}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarTrigger />
      </SidebarFooter>
    </Sidebar>
  )
}
