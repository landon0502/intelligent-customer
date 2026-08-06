import { NextRequest, NextResponse } from "next/server"

const PUBLIC_PATHS = ["/login", "/register"]

export function proxy(request: NextRequest) {
  const token = request.cookies.get("auth_token")?.value
  const { pathname } = request.nextUrl

  const isPublic = PUBLIC_PATHS.includes(pathname)

  // 已登录访问公开页面（/login、/register）→ 重定向到首页
  if (token && isPublic) {
    return NextResponse.redirect(new URL("/", request.url))
  }

  // 未登录访问非公开页面 → 重定向到登录页
  if (!token && !isPublic) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
}
