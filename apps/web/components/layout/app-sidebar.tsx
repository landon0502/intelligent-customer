"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import { ChevronRight } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
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
  const tCommon = useTranslations("common")
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
    const label = t(
      item.labelKey.replace("layout.", "") as Parameters<typeof t>[0]
    )

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
    const label = t(
      group.labelKey.replace("layout.", "") as Parameters<typeof t>[0]
    )

    return (
      <SidebarGroup key={group.key}>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={() => toggleGroup(group.key)}
                tooltip={label}
              >
                <ChevronRight
                  className={`size-4 transition-transform duration-200 ${
                    isExpanded ? "rotate-90" : ""
                  }`}
                />
                <span>{label}</span>
              </SidebarMenuButton>
              {isExpanded && (
                <SidebarMenuSub>
                  {group.children?.map((child) => {
                    const Icon = child.icon
                    const isActive = child.href === activeTab
                    const childLabel = t(
                      child.labelKey.replace("layout.", "") as Parameters<
                        typeof t
                      >[0]
                    )

                    return (
                      <SidebarMenuSubItem key={child.key}>
                        <SidebarMenuSubButton
                          isActive={isActive}
                          onClick={() => onTabChange?.(child.href)}
                        >
                          <Icon className="size-4" />
                          <span>{childLabel}</span>
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    )
                  })}
                </SidebarMenuSub>
              )}
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    )
  }

  return (
    <Sidebar collapsible={collapsible}>
      <SidebarHeader className="flex h-14 flex-row items-center justify-center gap-2 border-b border-sidebar-border px-4">
        <span className="text-xl">🤖</span>
        <span className="truncate text-sm font-semibold group-data-[collapsible=icon]:hidden">
          {tCommon("appName")}
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
