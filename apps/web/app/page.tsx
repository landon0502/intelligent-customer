"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { useAuthStore } from "@/store/auth";
import { AppLayout } from "@/components/layout/app-layout";
import { ChatPage } from "@/components/chat/chat-page";

export default function Page() {
  const { initAuth, loading } = useAuthStore();
  const t = useTranslations("common");

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">{t("loading")}</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <ChatPage />
    </AppLayout>
  );
}
