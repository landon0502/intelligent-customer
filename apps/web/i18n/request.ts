import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";
import { routing, type Locale } from "./routing";

export default getRequestConfig(async () => {
  let locale: Locale = routing.defaultLocale;

  const cookieStore = await cookies();
  const preferred = cookieStore.get(routing.cookieName)?.value;
  if (preferred && (routing.locales as readonly string[]).includes(preferred)) {
    locale = preferred as Locale;
  }

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
