import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { FetchError, ErrorType } from "@intelligent-customer/fetch-client";

vi.mock("@/lib/fetch/token-manager", () => ({
  tokenManager: {
    getToken: vi.fn(),
    setToken: vi.fn(),
    clearToken: vi.fn(),
    isAuthenticated: vi.fn(),
  },
}));

describe("401 interceptor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    delete (window as Record<string, unknown>).location;
    (window as Record<string, unknown>).location = { href: "", pathname: "/dashboard" };
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("AuthError 类型错误清除 token 并跳转 /login", async () => {
    const { handleAuthError, resetAuthRedirect } = await import("@/lib/fetch/index");
    resetAuthRedirect();
    const authError = new FetchError("未授权", ErrorType.AuthError, { status: 401 });
    handleAuthError(authError);
    const { tokenManager } = await import("@/lib/fetch/token-manager");
    const mockedClearToken = vi.mocked(tokenManager.clearToken);
    expect(mockedClearToken).toHaveBeenCalled();
    expect(window.location.href).toBe("/login");
  });

  it("TokenExpired 类型错误清除 token 并跳转 /login", async () => {
    const { handleAuthError, resetAuthRedirect } = await import("@/lib/fetch/index");
    resetAuthRedirect();
    const expiredError = new FetchError("Token 过期", ErrorType.TokenExpired, { status: 401 });
    handleAuthError(expiredError);
    const { tokenManager } = await import("@/lib/fetch/token-manager");
    const mockedClearToken = vi.mocked(tokenManager.clearToken);
    expect(mockedClearToken).toHaveBeenCalled();
    expect(window.location.href).toBe("/login");
  });

  it("非 AuthError 不触发跳转", async () => {
    const { handleAuthError, resetAuthRedirect } = await import("@/lib/fetch/index");
    resetAuthRedirect();
    const otherError = new FetchError("服务器错误", ErrorType.ServerError, { status: 500 });
    handleAuthError(otherError);
    const { tokenManager } = await import("@/lib/fetch/token-manager");
    const mockedClearToken = vi.mocked(tokenManager.clearToken);
    expect(mockedClearToken).not.toHaveBeenCalled();
  });
});
