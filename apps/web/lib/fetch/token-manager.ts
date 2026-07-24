import Cookies from "js-cookie";
import { TOKEN_KEY, REFRESH_TOKEN_KEY } from "./config";

const BASE_COOKIE_OPTIONS = {
  path: "/",
  sameSite: "strict" as const,
  secure: process.env.NODE_ENV === "production",
};

function getCookieOptions(remember: boolean) {
  return {
    ...BASE_COOKIE_OPTIONS,
    expires: remember ? 30 : undefined, // 记住我: 30天, 否则会话级
  };
}

export const tokenManager = {
  getToken(): string | null {
    if (typeof window === "undefined") return null;
    return Cookies.get(TOKEN_KEY) ?? null;
  },

  setToken(token: string, remember = false): void {
    if (typeof window === "undefined") return;
    Cookies.set(TOKEN_KEY, token, getCookieOptions(remember));
  },

  getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return Cookies.get(REFRESH_TOKEN_KEY) ?? null;
  },

  setRefreshToken(token: string, remember = false): void {
    if (typeof window === "undefined") return;
    Cookies.set(REFRESH_TOKEN_KEY, token, getCookieOptions(remember));
  },

  clearToken(): void {
    if (typeof window === "undefined") return;
    Cookies.remove(TOKEN_KEY, { path: "/" });
    Cookies.remove(REFRESH_TOKEN_KEY, { path: "/" });
  },

  isAuthenticated(): boolean {
    return !!this.getToken();
  },
};
