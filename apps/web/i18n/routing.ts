export const routing = {
  locales: ["zh-CN", "en-US"] as const,
  defaultLocale: "zh-CN" as const,
  cookieName: "NEXT_LOCALE",
}

export type Locale = (typeof routing.locales)[number]
