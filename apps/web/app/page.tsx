"use client";

import { useEffect } from "react";
import { Button } from "@intelligent-customer/ui/components/button";
import { useAuthStore } from "@/store/auth";

export default function Page() {
  const { user, initAuth, logout, loading } = useAuthStore();

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  if (loading) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <p className="text-muted-foreground">加载中...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-svh p-6">
      <div className="flex max-w-md min-w-0 flex-col gap-4 text-sm leading-loose">
        <div>
          <h1 className="font-medium">欢迎使用 AI 客服系统</h1>
          {user && (
            <p className="mt-2 text-muted-foreground">
              你好，{user.username}（{user.role}）
            </p>
          )}
          <Button className="mt-4" variant="outline" onClick={logout}>
            退出登录
          </Button>
        </div>
        <div className="text-muted-foreground font-mono text-xs">
          (Press <kbd>d</kbd> to toggle dark mode)
        </div>
      </div>
    </div>
  );
}
