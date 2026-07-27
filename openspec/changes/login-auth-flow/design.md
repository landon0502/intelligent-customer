## Context

本项目是一个 AI 客服机器人系统，采用前后端分离架构：前端 Next.js + shadcn UI，后端 FastAPI + MySQL。当前系统仅有健康检查接口，无任何认证机制。前端已有完整的请求封装层（`packages/fetch-client` + `apps/web/lib/fetch/`）和 token 管理器（Cookie 存储），但后端尚未实现认证接口，前端登录页仅为空壳。

现有基础设施：
- **前端**：`lib/fetch/` 已封装 FetchClient + 请求/响应拦截器 + token 注入 + 错误码映射；`token-manager.ts` 已实现 Cookie 读写；`zustand` 已安装用于状态管理
- **后端**：FastAPI 入口已搭建，统一响应格式已定义（`{code, message, data}`），MySQL/Redis 配置已就绪，但 models/db/services 目录均为空
- **UI**：shadcn UI 组件库已配置（`@intelligent-customer/ui`），已有 button/drawer 组件

## Goals / Non-Goals

**Goals:**
- 实现完整的用户登录/注册流程，前后端贯通
- 基于 JWT 的无状态认证，token 存储在 Cookie 中
- 前端路由守卫，未登录用户自动重定向到登录页
- 区分普通用户和管理员角色
- 复用已有的请求封装层和 token 管理器

**Non-Goals:**
- Refresh token 刷新机制（token 过期直接跳转登录页）
- 密码找回/重置功能
- 第三方 OAuth 登录
- 用户管理 CRUD 页面
- 多因素认证（MFA）

## Decisions

### D1: JWT 库选择 — PyJWT

**选择**：PyJWT
**替代方案**：python-jose
**理由**：PyJWT 是最轻量的 JWT 库，API 简洁，社区活跃。python-jose 功能更全但依赖更多，本项目不需要 JWE/JWK 等高级特性。PyJWT 足以满足 HS256 签名和验证需求。

### D2: 密码哈希 — passlib[bcrypt]

**选择**：passlib + bcrypt
**替代方案**：Python 内置 hashlib + salt
**理由**：bcrypt 是业界标准的密码哈希方案，自带 salt、可调 cost factor、抗 GPU 暴力破解。passlib 提供统一的哈希接口，便于未来切换算法。

### D3: Token 存储位置 — Cookie（HttpOnly）

**选择**：Cookie 存储，设置 HttpOnly + SameSite=Strict
**替代方案**：localStorage
**理由**：HttpOnly Cookie 可防止 XSS 攻击窃取 token；SameSite=Strict 防止 CSRF。前端 `token-manager.ts` 已基于 `js-cookie` 实现 Cookie 读写，但当前未设置 HttpOnly（需后端通过 Set-Cookie 响应头设置）。考虑到前端需要读取 token 注入请求头，采用非 HttpOnly 的 Cookie 方案（前端可读），但设置 SameSite=Strict 和 Secure（生产环境）。

### D4: 数据库连接 — SQLAlchemy async + asyncmy

**选择**：SQLAlchemy 2.x async engine + asyncmy driver
**替代方案**：同步 SQLAlchemy + pymysql
**理由**：FastAPI 是异步框架，使用 async ORM 可避免阻塞事件循环。asyncmy 是纯 Python 实现的 MySQL async driver，与 SQLAlchemy 2.x async session 配合良好。后端配置中 `database_url` 已使用 `mysql+asyncmy` 前缀。

### D5: 前端路由守卫 — Next.js Middleware

**选择**：Next.js middleware（`middleware.ts`）
**替代方案**：每个页面组件内检查认证状态
**理由**：middleware 在请求到达页面之前执行，可统一拦截未认证请求，避免页面闪烁。通过检查 Cookie 中的 `auth_token` 判断登录状态，无需客户端 JS 执行。

### D6: 前端认证状态管理 — Zustand store

**选择**：Zustand 创建 `useAuthStore`
**替代方案**：React Context
**理由**：项目已安装 zustand，且 zustand 比 Context 更轻量、支持持久化中间件、便于在非组件代码中使用。auth store 管理用户信息和登录状态，与 token-manager（Cookie 层）配合使用。

### D7: 登录页视觉风格 — shadcn 现代风格

**选择**：使用 shadcn UI 组件重新设计，不还原原型渐变背景
**理由**：shadcn 组件风格统一、可定制性强，与项目已有 UI 体系一致。保持居中卡片布局的功能结构，但视觉风格采用 shadcn 的 neutral 色调。

## Risks / Trade-offs

- **[Cookie 非 HttpOnly]** → 前端需要读取 token 注入 Authorization 请求头，因此不能设 HttpOnly。缓解：设置 SameSite=Strict + Secure，配合 CSP 头减少 XSS 风险
- **[无 Refresh Token]** → Token 过期后用户需重新登录，体验略差。缓解：设置较长的 token 有效期（如 24 小时），后续版本可增加 refresh token
- **[JWT 无状态无法主动失效]** → 用户退出登录后，token 在过期前仍可使用。缓解：退出时清除 Cookie，服务端可维护黑名单（Redis）作为后续增强
- **[数据库迁移]** → 首次建表需确保 MySQL 服务可用。缓解：使用 SQLAlchemy `create_all()` 自动建表，开发阶段不引入 Alembic 迁移工具
