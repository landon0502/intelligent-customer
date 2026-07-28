"use client";

import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Globe, Check } from "lucide-react";
import { Button } from "@intelligent-customer/ui/components/button";
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

export function LanguageSwitcher() {
  const router = useRouter();
  const t = useTranslations("language");
  const currentLocale = useLocale();

  function handleSelect(locale: string) {
    document.cookie = `NEXT_LOCALE=${locale};path=/;max-age=31536000`;
    router.refresh();
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="icon">
            <Globe className="size-4" />
            <span className="text-xs font-medium">{localeAbbr[currentLocale] ?? currentLocale}</span>
            <span className="sr-only">{t("switch")}</span>
          </Button>
        }
      />
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
