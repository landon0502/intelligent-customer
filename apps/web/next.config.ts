import type { NextConfig } from "next"
import createNextIntlPlugin from "next-intl/plugin"

const withNextIntl = createNextIntlPlugin("./i18n/request.ts")

const nextConfig: NextConfig = {
  transpilePackages: ["@intelligent-customer/ui"],
  /* config options here */
  async rewrites() {
    // 仅在开发环境（development）开启本地代理，解决跨域问题
    if (process.env.NODE_ENV === "development") {
      return [
        {
          // 匹配前端所有以 /api 开头的请求
          source: "/api/:path*",
          // 隐式代理转发到你本地启动的后端真实服务（如 Go/Gin 的 8080 端口）
          destination: process.env.NEXT_PUBLIC_API_URL + "/api/:path*",
        },
      ]
    }
    // 生产环境通常由 Nginx 或 负载均衡 统一处理跨域，Next.js 保持默认即可
    return []
  },
}

export default withNextIntl(nextConfig)
