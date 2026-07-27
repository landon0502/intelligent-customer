import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("@/lib/fetch/token-manager", () => ({
  tokenManager: {
    getToken: vi.fn(),
    setToken: vi.fn(),
    clearToken: vi.fn(),
    isAuthenticated: vi.fn(),
  },
}));

vi.mock("@/services/auth", () => ({
  loginApi: vi.fn(),
  registerApi: vi.fn(),
  getMeApi: vi.fn(),
}));

import { useAuthStore } from "@/store/auth";
import { tokenManager } from "@/lib/fetch/token-manager";
import { loginApi, registerApi } from "@/services/auth";

const mockedLoginApi = vi.mocked(loginApi);
const mockedRegisterApi = vi.mocked(registerApi);
const mockedSetToken = vi.mocked(tokenManager.setToken);
const mockedClearToken = vi.mocked(tokenManager.clearToken);

describe("authStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const store = useAuthStore.getState();
    store.logout();
  });

  it("login 成功后设置 token 和用户状态", async () => {
    mockedLoginApi.mockResolvedValueOnce({
      code: 0,
      message: "success",
      data: {
        token: "test-jwt-token",
        user: { id: 1, username: "admin", role: "admin" },
      },
    });

    await useAuthStore.getState().login("admin", "password123");

    expect(mockedSetToken).toHaveBeenCalledWith("test-jwt-token");
    const state = useAuthStore.getState();
    expect(state.user?.username).toBe("admin");
    expect(state.isAuthenticated).toBe(true);
  });

  it("logout 清除 token 和用户状态", () => {
    useAuthStore.setState({
      user: { id: 1, username: "admin", role: "admin" },
      isAuthenticated: true,
    });

    useAuthStore.getState().logout();

    expect(mockedClearToken).toHaveBeenCalled();
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it("register 成功后设置 token 和用户状态", async () => {
    mockedRegisterApi.mockResolvedValueOnce({
      code: 0,
      message: "success",
      data: {
        token: "new-jwt-token",
        user: { id: 2, username: "newuser", role: "user" },
      },
    });

    await useAuthStore.getState().register("newuser", "password123");

    expect(mockedSetToken).toHaveBeenCalledWith("new-jwt-token");
    const state = useAuthStore.getState();
    expect(state.user?.username).toBe("newuser");
    expect(state.isAuthenticated).toBe(true);
  });
});
