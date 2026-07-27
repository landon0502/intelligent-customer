## 1. 后端基础设施

- [x] 1.1 添加后端依赖：PyJWT、passlib[bcrypt]、sqlalchemy、asyncmy 到 pyproject.toml 并安装
- [x] 1.2 在 `.env` 中添加 JWT_SECRET 和 JWT_EXPIRE_MINUTES 配置项，在 config.py 中读取
- [x] 1.3 创建数据库连接模块 `app/db/session.py`：SQLAlchemy async engine + async session factory
- [x] 1.4 创建用户模型 `app/models/user.py`：User ORM 模型（id, username, password_hash, role, created_at）
- [x] 1.5 在 FastAPI lifespan 中添加数据库初始化（create_all 建表）

## 2. 后端认证逻辑

- [x] 2.1 创建 JWT 工具模块 `app/utils/jwt.py`：生成 token、验证 token、解析用户信息
- [x] 2.2 创建密码工具模块 `app/utils/password.py`：bcrypt 哈希、验证密码
- [x] 2.3 创建认证服务 `app/services/auth.py`：登录验证、注册创建用户、获取用户信息
- [x] 2.4 创建 JWT 认证依赖 `app/core/security.py`：FastAPI Depends，从请求头提取并验证 token
- [x] 2.5 创建认证路由 `app/routers/auth.py`：POST /api/auth/login、POST /api/auth/register、GET /api/auth/me
- [x] 2.6 在 main.py 中注册 auth_router，配置 CORS 中间件

## 3. 前端认证服务层

- [x] 3.1 创建 auth service `apps/web/services/auth.ts`：封装 login、register、getMe API 调用
- [x] 3.2 创建 auth store `apps/web/store/auth.ts`：Zustand store 管理用户信息和登录状态
- [x] 3.3 在 `lib/fetch/index.ts` 中添加 401 响应拦截器：token 过期时清除状态并跳转登录页

## 4. 前端登录/注册页面

- [x] 4.1 安装 shadcn UI 表单相关组件（card、input、label、form）
- [x] 4.2 实现登录/注册页面 `apps/web/app/login/page.tsx`：shadcn Card + Form + Input，登录/注册切换
- [x] 4.3 添加表单校验：用户名必填、密码至少 6 位、注册时确认密码一致

## 5. 前端路由守卫

- [x] 5.1 创建 Next.js middleware `apps/web/middleware.ts`：检查 Cookie auth_token，未登录重定向 /login，已登录访问 /login 重定向 /
- [x] 5.2 在首页 `apps/web/app/page.tsx` 添加退出登录按钮，调用 auth store 的 logout 方法

## 6. 联调与验证

- [x] 6.1 配置前端 `.env.local`：NEXT_PUBLIC_API_URL 和 NEXT_PUBLIC_API_BASE_URL
- [x] 6.2 端到端验证：注册 → 登录 → 访问受保护页面 → 退出登录 → 未登录重定向
