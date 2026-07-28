"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { titleKeyMap } from "@/config/menu";

export function AppHeader() {
  const pathname = usePathname();
  const t = useTranslations("layout");
  const tCommon = useTranslations("common");

  const titleKey = titleKeyMap[pathname];
  const pageTitle = titleKey
    ? t(titleKey.replace("layout.", "") as Parameters<typeof t>[0])
    : tCommon("appName");

  return (
    <header className="h-14 bg-background border-b flex items-center justify-between px-6 shrink-0">
      <h1 className="text-base font-semibold">{pageTitle}</h1>
      <div className="flex items-center gap-2">
        {/* ThemeSwitcher and LanguageSwitcher will go here */}
      </div>
    </header>
  );
}
