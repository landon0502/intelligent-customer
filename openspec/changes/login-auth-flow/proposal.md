## Why

系统当前没有用户认证机制，任何人都可以直接访问所有功能页面。作为 AI 客服机器人系统的第一步，需要建立用户登录/注册流程和 JWT 认证体系，确保只有经过身份验证的用户才能访问系统功能，同时区分普通用户和管理员角色权限。

## What Changes

- 新增前端登录/注册页面，使用 shadcn UI 组件构建，支持用户名+密码登录和注册
- 新增后端认证接口（`/api/auth/login`、`/api/auth/register`、`/api/auth/me`），基于 JWT token 校验
- 新增后端用户数据模型和数据库连接（SQLAlchemy async + MySQL）
- 对接已有的前端请求封装层（`lib/fetch`）和 token 管理器（`token-manager`）
- 新增 Next.js middleware 路由守卫，未登录用户重定向到 `/login`
- 新增前端 auth service 层，封装认证相关的 API 调用和状态管理

## Capabilities

### New Capabilities
- `user-auth`: 用户认证能力，覆盖登录、注册、token 校验、路由守卫的完整认证流程

### Modified Capabilities
（无已有 capability 需修改）

## Impact

- **前端代码**：`apps/web/app/login/`（登录/注册页面）、`apps/web/services/`（auth service）、`apps/web/store/`（auth 状态）、`apps/web/middleware.ts`（路由守卫）
- **后端代码**：`apps/service/app/routers/auth.py`（认证路由）、`apps/service/app/models/user.py`（用户模型）、`apps/service/app/db/`（数据库连接）、`apps/service/app/utils/jwt.py`（JWT 工具）、`apps/service/app/services/auth.py`（认证服务）
- **依赖变更**：后端需新增 `PyJWT`（或 `python-jose`）和 `passlib[bcrypt]`、`asyncmy`、`sqlalchemy` 依赖
- **数据库**：需创建 `users` 表
- **API**：新增 3 个认证接口
- **配置**：后端 `.env` 需新增 `JWT_SECRET`、`JWT_EXPIRE_MINUTES`；前端需配置 `NEXT_PUBLIC_API_URL` 和 `NEXT_PUBLIC_API_BASE_URL`
