"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Check } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@intelligent-customer/ui/components/dropdown-menu";
import { routing } from "@/i18n/routing";

const localeOptions = routing.locales;

const localeAbbr: Record<string, string> = {
  "zh-CN": "中",
  "en-US": "EN",
};

function setLocaleCookie(locale: string) {
  document.cookie = `NEXT_LOCALE=${locale};path=/;max-age=31536000`;
}

export function LanguageSwitcher() {
  const router = useRouter();
  const t = useTranslations("language");
  const currentLocale = useLocale();

  const handleSelect = useCallback(
    (locale: string) => {
      setLocaleCookie(locale);
      router.refresh();
    },
    [router],
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="inline-flex items-center justify-center h-8 w-8 text-xs font-medium rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
      >
        {localeAbbr[currentLocale] ?? currentLocale}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {localeOptions.map((locale) => (
          <DropdownMenuItem key={locale} onClick={() => handleSelect(locale)}>
            {t(locale === "zh-CN" ? "zhCN" : "enUS")}
            {currentLocale === locale && <Check className="size-4 ml-auto" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
