"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuthGuard } from "@/hooks/useAuthGuard"
import { useAuthStore } from "@/store/auth"
import fetchClient, { FetchError } from "@/lib/fetch"
import { setupErrorToast } from "@/lib/fetch/error-toast"

interface AuthGuardProps {
  children: React.ReactNode
  /** token 无效时的回调，默认跳 /login */
  onUnauthorized?: () => void
}

/** 注册全局 401 回调 + token 校验守卫 */
export function AuthGuard({ children, onUnauthorized }: AuthGuardProps) {
  const router = useRouter()
  const { isValidating, hasToken } = useAuthGuard()

  // 注册全局错误 toast 提示
  useEffect(() => {
    const unregister = setupErrorToast(fetchClient)
    return unregister
  }, [])

  // 注册全局 401 处理：通过响应错误拦截器捕获 401 并触发登出
  useEffect(() => {
    const handleUnauthorized = () => {
      useAuthStore.getState().logout()
      if (onUnauthorized) {
        onUnauthorized()
      } else {
        router.replace("/login")
      }
    }

    const unregister = fetchClient.useResponseErrorInterceptor((error) => {
      if (error instanceof FetchError && error.status === 401) {
        handleUnauthorized()
      }
      return error
    })

    return unregister
  }, [router, onUnauthorized])

  // 没有 token（middleware 已兜底，这里是二次保障）
  useEffect(() => {
    if (!isValidating && !hasToken) {
      router.replace("/login")
    }
  }, [isValidating, hasToken, router])

  return <>{children}</>
}
