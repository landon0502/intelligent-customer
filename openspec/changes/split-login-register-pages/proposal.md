## Why

当前登录页 `/login` 通过 `mode` 状态在登录和注册之间切换，URL 无法区分用户当前处于哪个流程，导致无法直接分享注册链接、无法从退出登录后精确回到原流程、浏览器后退行为混乱。拆分为独立的 `/login` 和 `/register` 两个页面可让每个流程拥有独立 URL，提升可分享性和导航清晰度。

## What Changes

- 将 `/login` 页面中的注册逻辑拆分到新页面 `/register`
- `/login` 页面仅保留登录表单，底部提供跳转 `/register` 的链接
- `/register` 页面仅保留注册表单（含确认密码），底部提供跳转 `/login` 的链接
- **BREAKING**：移除登录页内的登录/注册模式切换交互，改为路由跳转
- 更新 Next.js middleware：允许未登录用户访问 `/register`；已登录用户访问 `/login` 或 `/register` 均重定向到首页
- 移除登录页中已不再需要的 `mode` 状态和 `registerForm`/`confirmPassword` 相关代码

## Capabilities

### New Capabilities
（无）

### Modified Capabilities
- `user-auth`: 用户注册和前端路由守卫的需求场景调整——注册流程独立为 `/register` 页面，路由守卫需放行 `/register` 并对已登录访问 `/register` 做重定向

## Impact

- **前端代码**：`apps/web/app/login/page.tsx`（精简为纯登录）、新增 `apps/web/app/register/page.tsx`（注册页面）、`apps/web/middleware.ts`（路由守卫放行 `/register`）
- **API**：无变更，复用现有 `/api/auth/login`、`/api/auth/register` 接口
- **依赖**：无新增依赖
- **测试**：现有前端测试不涉及页面路由，无需调整；可选新增注册页交互测试
