"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import Link from "next/link"
import { useAuthStore } from "@/store/auth"
import { Button } from "@intelligent-customer/ui/components/button"
import { Input } from "@intelligent-customer/ui/components/input"
import { Label } from "@intelligent-customer/ui/components/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@intelligent-customer/ui/components/card"

const loginSchema = z.object({
  username: z
    .string()
    .min(1, "请输入用户名")
    .max(20, "用户名最多20位")
    .regex(/^[a-zA-Z0-9_]+$/, "仅支持字母数字下划线"),
  password: z.string().min(6, "密码至少6位"),
})

type LoginFormData = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const { login } = useAuthStore()
  const [submitting, setSubmitting] = useState(false)

  const loginForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  })

  const handleLogin = async (data: LoginFormData) => {
    setSubmitting(true)
    try {
      await login(data.username, data.password)
      router.push("/")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "登录失败")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>登录</CardTitle>
          <CardDescription>输入用户名和密码登录系统</CardDescription>
        </CardHeader>
        <form onSubmit={loginForm.handleSubmit(handleLogin)}>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="login-username">用户名</Label>
              <Input
                id="login-username"
                placeholder="请输入用户名"
                {...loginForm.register("username")}
              />
              {loginForm.formState.errors.username && (
                <p className="text-sm text-destructive">
                  {loginForm.formState.errors.username.message}
                </p>
              )}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="login-password">密码</Label>
              <Input
                id="login-password"
                type="password"
                placeholder="请输入密码"
                {...loginForm.register("password")}
              />
              {loginForm.formState.errors.password && (
                <p className="text-sm text-destructive">
                  {loginForm.formState.errors.password.message}
                </p>
              )}
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-3">
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "登录中..." : "登录"}
            </Button>
            <p className="text-sm text-muted-foreground">
              没有账户？{" "}
              <Link
                href="/register"
                className="text-primary underline-offset-4 hover:underline"
              >
                注册
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
