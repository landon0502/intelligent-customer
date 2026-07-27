"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
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

const registerSchema = loginSchema
  .extend({
    confirmPassword: z.string().min(6, "确认密码至少6位"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "两次密码不一致",
    path: ["confirmPassword"],
  })

type LoginFormData = z.infer<typeof loginSchema>
type RegisterFormData = z.infer<typeof registerSchema>

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login")
  const router = useRouter()
  const { login, register: registerUser } = useAuthStore()
  const [submitting, setSubmitting] = useState(false)

  const loginForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  })

  const registerForm = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: "", password: "", confirmPassword: "" },
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

  const handleRegister = async (data: RegisterFormData) => {
    setSubmitting(true)
    try {
      await registerUser(data.username, data.password)
      router.push("/")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "注册失败")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{mode === "login" ? "登录" : "注册"}</CardTitle>
          <CardDescription>
            {mode === "login"
              ? "输入用户名和密码登录系统"
              : "创建新账户开始使用"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {mode === "login" ? (
            <form onSubmit={loginForm.handleSubmit(handleLogin)}>
              <div className="flex flex-col gap-6">
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
              </div>
            </form>
          ) : (
            <form onSubmit={registerForm.handleSubmit(handleRegister)}>
              <div className="space-y-2">
                <Label htmlFor="reg-username">用户名</Label>
                <Input
                  id="reg-username"
                  placeholder="请输入用户名"
                  {...registerForm.register("username")}
                />
                {registerForm.formState.errors.username && (
                  <p className="text-sm text-destructive">
                    {registerForm.formState.errors.username.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="reg-password">密码</Label>
                <Input
                  id="reg-password"
                  type="password"
                  placeholder="请输入密码"
                  {...registerForm.register("password")}
                />
                {registerForm.formState.errors.password && (
                  <p className="text-sm text-destructive">
                    {registerForm.formState.errors.password.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="reg-confirm">确认密码</Label>
                <Input
                  id="reg-confirm"
                  type="password"
                  placeholder="请再次输入密码"
                  {...registerForm.register("confirmPassword")}
                />
                {registerForm.formState.errors.confirmPassword && (
                  <p className="text-sm text-destructive">
                    {registerForm.formState.errors.confirmPassword.message}
                  </p>
                )}
              </div>
            </form>
          )}
        </CardContent>
        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" className="w-full" disabled={submitting}>
            {mode === "login"
              ? submitting
                ? "登录中..."
                : "登录"
              : submitting
                ? "注册中..."
                : "注册"}
          </Button>
          <p className="text-sm text-muted-foreground">
            {mode === "login" ? "没有账户？" : "已有账户？"}
            <button
              type="button"
              className="text-primary underline-offset-4 hover:underline"
              onClick={() => setMode("register")}
            >
              {{ login: "登录", register: "注册" }[mode]}
            </button>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
