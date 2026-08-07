"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/store/auth"
import { tokenManager } from "@/lib/fetch"

type GuardState = "idle" | "loading" | "done"

/**
 * 客户端鉴权守卫。
 * proxy 已向 Redis 校验 token，这里只需拉取用户信息。
 */
export function useAuthGuard() {
  const router = useRouter()
  const { isAuthenticated, logout, initAuth } = useAuthStore()
  const [state, setState] = useState<GuardState>("idle")
  const ranRef = useRef(false)

  useEffect(() => {
    if (ranRef.current) return
    ranRef.current = true

    const run = async () => {
      if (!tokenManager.isAuthenticated()) {
        router.replace("/login")
        return
      }

      // store 已缓存用户信息 → 直接放行
      if (isAuthenticated) {
        setState("done")
        return
      }

      // 拉取用户信息
      setState("loading")
      try {
        await initAuth()
        setState("done")
      } catch {
        await logout()
        router.replace("/login")
      }
    }

    run()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return {
    isValidating: state !== "done",
    isAuthenticated,
    hasToken: tokenManager.isAuthenticated(),
  }
}
