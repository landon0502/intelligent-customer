import { create } from "zustand";
import { tokenManager } from "@/lib/fetch/token-manager";
import { loginApi, registerApi, getMeApi, type User } from "@/services/auth";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  fetchUser: () => Promise<void>;
  logout: () => void;
  initAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  loading: false,

  login: async (username, password) => {
    const res = await loginApi(username, password);
    tokenManager.setToken(res.data.token);
    set({ user: res.data.user, isAuthenticated: true });
  },

  register: async (username, password) => {
    const res = await registerApi(username, password);
    tokenManager.setToken(res.data.token);
    set({ user: res.data.user, isAuthenticated: true });
  },

  fetchUser: async () => {
    try {
      const res = await getMeApi();
      set({ user: res.data, isAuthenticated: true, loading: false });
    } catch {
      tokenManager.clearToken();
      set({ user: null, isAuthenticated: false, loading: false });
    }
  },

  logout: () => {
    tokenManager.clearToken();
    set({ user: null, isAuthenticated: false });
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  },

  initAuth: async () => {
    if (tokenManager.isAuthenticated()) {
      set({ loading: true });
      try {
        const res = await getMeApi();
        set({ user: res.data, isAuthenticated: true, loading: false });
      } catch {
        tokenManager.clearToken();
        set({ user: null, isAuthenticated: false, loading: false });
      }
    } else {
      set({ user: null, isAuthenticated: false, loading: false });
    }
  },
}));
