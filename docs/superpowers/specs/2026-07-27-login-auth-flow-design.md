---
comet_change: login-auth-flow
role: technical-design
canonical_spec: openspec
archived-with: 2026-07-27-login-auth-flow
status: final
---

# 登录认证流程 — 技术设计文档

## 概述

为 AI 客服机器人系统实现完整的用户认证流程：后端 JWT 认证接口 + 前端登录/注册页面 + 路由守卫。采用轻量分层架构，复用已有的 FetchClient 请求封装和 token-manager Cookie 管理层。

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                  │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ Login    │  │ Auth     │  │ lib/fetch/            │  │
│  │ Page     │─▶│ Store    │  │ ├─ index.ts           │  │
│  │ (shadcn) │  │ (Zustand)│  │ ├─ token-manager.ts   │  │
│  └──────────┘  └────┬─────┘  │ └─ types.ts           │  │
│                      │        └──────────┬───────────┘  │
│                      │                   │              │
│  ┌──────────┐       │  ┌────────────────┐│              │
│  │Middleware│       │  │ Auth Service   ││              │
│  │(route    │       └──│ (API calls)    ││              │
│  │ guard)   │          └───────┬────────┘│              │
│  └──────────┘                  │         │              │
└────────────────────────────────┼─────────┼──────────────┘
                                 │ HTTP    │ Bearer Token
┌────────────────────────────────┼─────────┼──────────────┐
│                     Backend (FastAPI)     │              │
│                                │         │              │
│  ┌─────────────┐  ┌───────────▼──┐  ┌───▼───────────┐  │
│  │ Auth Router  │  │ Security     │  │ JWT Utility   │  │
│  │ /api/auth/*  │  │ (Depends)    │  │ (PyJWT HS256) │  │
│  └──────┬──────┘  └──────────────┘  └───────────────┘  │
│         │                                               │
│  ┌──────▼──────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Auth Service │  │ Password     │  │ User Model    │  │
│  │ (business)   │  │ (bcrypt)     │  │ (SQLAlchemy)  │  │
│  └─────────────┘  └──────────────┘  └───────┬───────┘  │
│                                              │          │
│                                        ┌─────▼─────┐    │
│                                        │  MySQL    │    │
│                                        │  (asyncmy)│    │
│                                        └───────────┘    │
└─────────────────────────────────────────────────────────┘
```

## 后端实现设计

### 数据库层

**`app/db/session.py`** — 异步数据库会话管理

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

**`app/models/user.py`** — 用户 ORM 模型

| 字段 | 类型 | 约束 |
|------|------|------|
| id | Integer | PK, autoincrement |
| username | String(20) | UNIQUE, NOT NULL, 索引 |
| password_hash | String(128) | NOT NULL |
| role | String(10) | NOT NULL, default="user" |
| created_at | DateTime | NOT NULL, default=utcnow |

### JWT 工具

**`app/utils/jwt.py`**

- `create_token(user_id: int, username: str, role: str) -> str`：生成 HS256 JWT，payload 包含 sub(user_id)、username、role、exp（7 天）
- `verify_token(token: str) -> dict`：验证签名和有效期，返回 payload 或抛出异常
- SECRET 从 `settings.JWT_SECRET` 读取，有效期从 `settings.JWT_EXPIRE_MINUTES` 读取

### 密码工具

**`app/utils/password.py`**

- `hash_password(password: str) -> str`：使用 passlib CryptContext(bcrypt) 哈希
- `verify_password(plain: str, hashed: str) -> bool`：验证明文密码与哈希

### 认证依赖

**`app/core/security.py`**

```python
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    payload = verify_token(token)
    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(401)
    return user
```

使用 FastAPI 的 OAuth2PasswordBearer 从 Authorization 头提取 Bearer token。

### 认证服务

**`app/services/auth.py`**

- `authenticate_user(db, username, password) -> User`：验证用户名密码
- `register_user(db, username, password) -> User`：创建新用户（默认 role="user"）
- `get_user_by_username(db, username) -> User | None`
- `seed_admin_user(db)`：启动时检查 admin 用户是否存在，不存在则创建（密码从配置或默认值）

### 认证路由

**`app/routers/auth.py`**

| 端点 | 方法 | 认证 | 请求体 | 响应 |
|------|------|------|--------|------|
| `/api/auth/login` | POST | 无 | `{username, password}` | `{token, user: {id, username, role}}` |
| `/api/auth/register` | POST | 无 | `{username, password}` | `{token, user: {id, username, role}}` |
| `/api/auth/me` | GET | Bearer | — | `{id, username, role}` |

登录/注册成功后返回 JWT token + 用户信息，前端自行存入 Cookie。
密码错误和用户不存在统一返回 INVALID_CREDENTIALS（不暴露用户存在性）。

### 启动初始化

在 `main.py` 的 lifespan 中：
1. `create_all()` 建表
2. 调用 `seed_admin_user()` 创建默认 admin 用户

### CORS 配置

在 `main.py` 中添加 CORSMiddleware，允许前端域名（开发环境 `http://localhost:3000`）。

## 前端实现设计

### Auth Service 层

**`apps/web/services/auth.ts`**

```typescript
export async function loginApi(username: string, password: string) {
  return fetchClient.post<{token: string; user: User}>('/api/auth/login', {username, password});
}

export async function registerApi(username: string, password: string) {
  return fetchClient.post<{token: string; user: User}>('/api/auth/register', {username, password});
}

export async function getMeApi() {
  return fetchClient.get<User>('/api/auth/me');
}
```

薄封装，仅负责 API 调用。

### Auth Store (Zustand)

**`apps/web/store/auth.ts`**

```typescript
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  fetchUser: () => Promise<void>;
  logout: () => void;
  initAuth: () => Promise<void>;
}
```

- `login`/`register`：调用 API → `tokenManager.setToken(token)` → 设置 user 状态
- `fetchUser`：调用 `getMeApi` 恢复用户信息（应用启动时）
- `logout`：`tokenManager.clearToken()` → 清除 user 状态 → `router.push('/login')`
- `initAuth`：检查 `tokenManager.isAuthenticated()`，有 token 则 fetchUser，否则清除状态

### 401 拦截器

在 `apps/web/lib/fetch/index.ts` 中添加响应错误拦截器：

```typescript
fetchClient.useResponseErrorInterceptor((error) => {
  if (error instanceof FetchError &&
      (error.type === ErrorType.AuthError || error.type === ErrorType.TokenExpired)) {
    tokenManager.clearToken();
    if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
      window.location.href = '/login';
    }
  }
  return error;
});
```

使用 `window.location` 而非 router，因为拦截器不在 React 组件上下文内。

### 登录/注册页面

**`apps/web/app/login/page.tsx`**

- 状态：`mode = 'login' | 'register'`
- shadcn 组件：Card + CardHeader + CardContent + CardFooter，Input，Button
- 表单校验（zod schema）：
  - username: `string().min(1, '请输入用户名').max(20, '用户名最多20位').regex(/^[a-zA-Z0-9_]+$/, '仅支持字母数字下划线')`
  - password: `string().min(6, '密码至少6位')`
  - confirmPassword: `ref` 校验与 password 一致（仅注册模式）
- 提交逻辑：调用 auth store 的 login/register → 成功 `router.push('/')` → 失败 sonner toast
- 底部切换链接：登录 ↔ 注册

### Next.js Middleware

**`apps/web/middleware.ts`**

```typescript
export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token')?.value;
  const {pathname} = request.nextUrl;

  if (token && pathname === '/login') {
    return NextResponse.redirect(new URL('/', request.url));
  }
  if (!token && pathname !== '/login') {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

仅检查 Cookie 存在性，不验证 token 有效性（JWT 验证由后端负责）。

### 退出登录

在首页 `apps/web/app/page.tsx` 添加退出按钮，调用 `useAuthStore().logout()`。

## 错误处理

### 后端统一错误格式

使用已有的 `ApiResponse` 格式 `{code, message, data}`：

| HTTP 状态 | code | 场景 |
|-----------|------|------|
| 400 | 40000 | 请求参数校验失败 |
| 401 | 20001 | 无效 Token |
| 401 | 20002 | Token 过期 |
| 401 | 40100 | 缺少 Token |
| 409 | 30002 | 用户名已存在 |
| 401 | 30001 | 用户名或密码错误 |
| 500 | 50000 | 服务器内部错误 |

### 前端错误处理链

1. **FetchClient 响应拦截器**：根据 error_code 映射 ErrorType
2. **401 拦截器**（新增）：AuthError/TokenExpired → 清除 token + 跳转 /login
3. **通用错误 toast**（已有）：sonner toast 显示错误消息

### 边界条件处理

| 场景 | 处理方式 |
|------|---------|
| Token 过期但用户仍在操作 | 401 拦截器自动清除状态并跳转 |
| 并发请求同时收到 401 | 用标志位防抖，只触发一次跳转 |
| Cookie 被手动清除 | middleware 检测无 token → 重定向 /login |
| 数据库连接失败 | FastAPI 异常处理器返回 500 |
| 用户名含特殊字符 | 后端校验格式（字母数字下划线，1-20位） |
| 密码长度边界 | 前端 zod min(6)，后端同样校验 |

## 测试策略

### 后端测试

使用 FastAPI TestClient + 内存 SQLite（测试环境替换数据库 URL）：

- **`test_auth_routes.py`**：API 端点测试（登录成功/失败、注册成功/重复用户名、获取用户信息）
- **`test_jwt_utils.py`**：JWT 工具测试（生成/验证/过期 token）
- **`test_password_utils.py`**：密码工具测试（哈希/验证）

### 前端测试

使用 vitest + @testing-library/react，mock API 调用：

- **`auth-store.test.ts`**：Zustand store 测试（login/logout/fetchUser）
- **`login-page.test.tsx`**：页面交互测试（表单校验、模式切换、提交跳转）

### 联调验证

手动端到端流程：注册 → 登录 → 访问首页 → 退出 → 未登录重定向 /login

## 文件变更清单

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `apps/service/app/db/__init__.py` | db 包初始化 |
| `apps/service/app/db/session.py` | 数据库连接和会话 |
| `apps/service/app/models/__init__.py` | models 包初始化 |
| `apps/service/app/models/user.py` | 用户 ORM 模型 |
| `apps/service/app/utils/jwt.py` | JWT 工具 |
| `apps/service/app/utils/password.py` | 密码工具 |
| `apps/service/app/services/__init__.py` | services 包初始化 |
| `apps/service/app/services/auth.py` | 认证业务逻辑 |
| `apps/service/app/core/security.py` | JWT 认证依赖 |
| `apps/service/app/routers/auth.py` | 认证路由 |
| `apps/web/services/auth.ts` | 前端 auth API 封装 |
| `apps/web/store/auth.ts` | Zustand auth store |
| `apps/web/middleware.ts` | Next.js 路由守卫 |

### 修改文件

| 文件路径 | 变更内容 |
|----------|---------|
| `apps/service/pyproject.toml` | 新增 PyJWT、passlib[bcrypt]、sqlalchemy、asyncmy 依赖 |
| `apps/service/app/core/config.py` | 新增 JWT_SECRET、JWT_EXPIRE_MINUTES、ADMIN_PASSWORD 配置 |
| `apps/service/app/main.py` | 注册 auth_router、配置 CORS、lifespan 添加建表和 admin 初始化 |
| `apps/web/app/login/page.tsx` | 实现登录/注册页面（替换空壳） |
| `apps/web/app/page.tsx` | 添加退出登录按钮 |
| `apps/web/lib/fetch/index.ts` | 添加 401 响应错误拦截器 |
| `apps/web/.env.local` | 配置 NEXT_PUBLIC_API_BASE_URL |
