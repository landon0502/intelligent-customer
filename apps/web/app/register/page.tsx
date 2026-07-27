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

const registerSchema = z
  .object({
    username: z
      .string()
      .min(1, "请输入用户名")
      .max(20, "用户名最多20位")
      .regex(/^[a-zA-Z0-9_]+$/, "仅支持字母数字下划线"),
    password: z.string().min(6, "密码至少6位"),
    confirmPassword: z.string().min(6, "确认密码至少6位"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "两次密码不一致",
    path: ["confirmPassword"],
  })

type RegisterFormData = z.infer<typeof registerSchema>

export default function RegisterPage() {
  const router = useRouter()
  const { register: registerUser } = useAuthStore()
  const [submitting, setSubmitting] = useState(false)

  const registerForm = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: "", password: "", confirmPassword: "" },
  })

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
          <CardTitle>注册</CardTitle>
          <CardDescription>创建新账户开始使用</CardDescription>
        </CardHeader>
        <form onSubmit={registerForm.handleSubmit(handleRegister)}>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
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
            <div className="grid gap-2">
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
            <div className="grid gap-2">
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
          </CardContent>
          <CardFooter className="flex flex-col gap-3">
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "注册中..." : "注册"}
            </Button>
            <p className="text-sm text-muted-foreground">
              已有账户？{" "}
              <Link
                href="/login"
                className="text-primary underline-offset-4 hover:underline"
              >
                登录
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
