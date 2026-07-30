"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  SidebarProvider,
  SidebarInset,
} from "@intelligent-customer/ui/components/sidebar";
import { AppSidebar } from "@/components/layout/sidebar";
import { AppHeader } from "@/components/layout/app-header";

interface AppLayoutProps {
  children: React.ReactNode;
  activeTab?: string;
  onTabChange?: (tab: string) => void;
  collapsible?: "icon" | "offcanvas";
}

export function AppLayout({
  children,
  activeTab: activeTabProp,
  onTabChange: onTabChangeProp,
  collapsible = "icon",
}: AppLayoutProps) {
  const pathname = usePathname();
  const router = useRouter();

  const activeTab = activeTabProp ?? pathname;
  const onTabChange = onTabChangeProp ?? ((tab: string) => router.push(tab));

  return (
    <SidebarProvider>
      <AppSidebar
        activeTab={activeTab}
        onTabChange={onTabChange}
        collapsible={collapsible}
      />
      <SidebarInset>
        <AppHeader />
        <div className="flex-1 overflow-y-auto p-6">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
