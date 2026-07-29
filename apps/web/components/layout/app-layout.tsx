"use client";

import { usePathname, useRouter } from "next/navigation";
import { SidebarProvider } from "@intelligent-customer/ui/components/sidebar";
import { AppSidebar } from "@/components/layout/sidebar";
import { AppHeader } from "@/components/layout/app-header";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <SidebarProvider>
      <AppSidebar
        activeTab={pathname}
        onTabChange={(tab) => router.push(tab)}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        <AppHeader />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </SidebarProvider>
  );
}
