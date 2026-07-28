"use client";

import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import { Sun, Moon, Monitor } from "lucide-react";
import { Button } from "@intelligent-customer/ui/components/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@intelligent-customer/ui/components/dropdown-menu";

const themeOptions = ["light", "dark", "system"] as const;

const emptySubscribe = () => () => {};

export function ThemeSwitcher() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const t = useTranslations("theme");
  const mounted = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" disabled>
        <Sun className="size-4" />
        <span className="sr-only">{t("toggle")}</span>
      </Button>
    );
  }

  const triggerIcon =
    resolvedTheme === "dark" ? (
      <Sun className="size-4" />
    ) : (
      <Moon className="size-4" />
    );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="icon">
            {triggerIcon}
            <span className="sr-only">{t("toggle")}</span>
          </Button>
        }
      />
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup
          value={theme}
          onValueChange={(value) => setTheme(value)}
        >
          {themeOptions.map((value) => {
            const icon =
              value === "light" ? (
                <Sun className="size-4" />
              ) : value === "dark" ? (
                <Moon className="size-4" />
              ) : (
                <Monitor className="size-4" />
              );

            return (
              <DropdownMenuRadioItem key={value} value={value}>
                {icon}
                {t(value)}
              </DropdownMenuRadioItem>
            );
          })}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
