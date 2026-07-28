"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { useAuthStore } from "@/store/auth";
import { AppLayout } from "@/components/layout/app-layout";

export default function Page() {
  const { user, initAuth, loading } = useAuthStore();
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
      <div className="flex flex-col items-center justify-center gap-2">
        <h1 className="text-2xl font-medium">{t("appName")}</h1>
        <p className="text-muted-foreground">{t("tagline")}</p>
        {user && (
          <p className="text-muted-foreground text-sm">
            {user.username}（{user.role === "admin" ? t("roleAdmin") : t("roleUser")}）
          </p>
        )}
      </div>
    </AppLayout>
  );
}
