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
  collapsible?: "icon" | "offcanvas";
}

export function AppLayout({
  children,
  collapsible = "icon",
}: AppLayoutProps) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <SidebarProvider>
      <AppSidebar
        activeTab={pathname}
        onTabChange={(tab) => router.push(tab)}
        collapsible={collapsible}
      />
      <SidebarInset>
        <AppHeader />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
