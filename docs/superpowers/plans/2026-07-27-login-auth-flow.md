---
change: login-auth-flow
design-doc: docs/superpowers/specs/2026-07-27-login-auth-flow-design.md
base-ref: e6b1542cdd7c0a5700513127ae2499a6009c6723
---

# 登录认证流程 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 AI 客服系统实现完整的用户认证流程：后端 JWT 认证接口 + 前端登录/注册页面 + 路由守卫。

**Architecture:** 后端 FastAPI 提供 REST 认证接口（login/register/me），使用 PyJWT 签发 HS256 token，passlib/bcrypt 哈希密码，SQLAlchemy async 操作 MySQL。前端 Zustand 管理认证状态，Cookie 存储 token，Next.js Middleware 实现路由守卫，FetchClient 拦截器处理 401 自动跳转。

**Tech Stack:** FastAPI, PyJWT, passlib[bcrypt], SQLAlchemy (async), asyncmy, Next.js 16, Zustand, shadcn/ui, zod, sonner, js-cookie

## Global Constraints

- 后端 Python >=3.14，使用 uv 管理依赖
- 前端 Next.js 16.2.6，React 19.2.4，pnpm monorepo
- 后端响应格式 `{ code, message, data }`，成功 code=0（对齐前端 FetchClient SUCCESS_CODE=0）
- 前端 token 存储在 Cookie `auth_token` 中，由 `tokenManager` 管理
- 数据库驱动使用 `mysql+asyncmy`（已在 config.py 中配置）
- 现有 `success()` 返回 code=200，需改为 code=0 以兼容前端 FetchClient
- 前端 FetchClient 已有 request 拦截器注入 Bearer token，已有 responseError 拦截器做业务码映射和 toast

---

## 兼容性修复（前置）

> **关键问题：** 现有 `app/utils/response.py` 的 `success()` 返回 `code: 200`，但前端 `FetchClient` 的 `SUCCESS_CODE = 0`。所有成功响应都会被前端当作业务错误处理。必须在认证功能之前修复此不兼容问题。

### Task 1: 修复后端响应 code 与前端 SUCCESS_CODE 的兼容性

**Files:**
- Modify: `apps/service/app/utils/response.py`
- Test: `apps/service/tests/test_response_utils.py`

**Interfaces:**
- Consumes: 无外部依赖
- Produces: `success()` 返回 `{"code": 0, "message": ..., "data": ...}`，`error()` 签名不变

- [x] **Step 1: 编写失败测试**

```python
# apps/service/tests/test_response_utils.py
from app.utils.response import success, error

def test_success_returns_code_zero():
    result = success(data={"key": "value"})
    assert result["code"] == 0
    assert result["message"] == "success"
    assert result["data"] == {"key": "value"}

def test_success_with_custom_message():
    result = success(data=None, message="created")
    assert result["code"] == 0
    assert result["message"] == "created"

def test_error_returns_given_code():
    result = error(code=40000, message="参数错误")
    assert result["code"] == 40000
    assert result["message"] == "参数错误"
    assert result["data"] is None
```

- [x] **Step 2: 运行测试确认失败**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_response_utils.py -v`
Expected: `test_success_returns_code_zero` FAIL（当前 success 返回 code=200）

- [x] **Step 3: 修改 success() 使其返回 code=0**

```python
# apps/service/app/utils/response.py
def success(data: Any = None, message: str = "success") -> dict:
    """成功响应快捷函数"""
    return {"code": 0, "message": message, "data": data}
```

- [x] **Step 4: 运行测试确认通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_response_utils.py -v`
Expected: ALL PASS

- [x] **Step 5: Commit**

```bash
git add apps/service/app/utils/response.py apps/service/tests/test_response_utils.py
git commit -m "fix: align backend success code to 0 for frontend FetchClient compatibility"
```

---

## 后端基础设施

### Task 2: 添加后端认证相关依赖

**Files:**
- Modify: `apps/service/pyproject.toml`
- Modify: `apps/service/.env`
- Modify: `apps/service/app/core/config.py`

**Interfaces:**
- Consumes: 无
- Produces: `settings.JWT_SECRET`, `settings.JWT_EXPIRE_MINUTES`, `settings.ADMIN_PASSWORD` 可供后续 task 使用

- [x] **Step 1: 在 pyproject.toml 添加依赖**

在 `dependencies` 列表中添加以下包（保留已有依赖不变）：

```toml
dependencies = [
    "fastapi>=0.139.2",
    "langchain>=1.3.14",
    "langchain-core>=1.5.1",
    "langgraph>=1.2.9",
    "pydantic>=2.13.4",
    "pymysql>=1.2.0",
    "python-dotenv>=1.2.2",
    "redis>=8.0.1",
    "rich>=15.0.0",
    "streamlit>=1.60.0",
    "uvicorn>=0.51.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncmy>=0.2.9",
    "pyjwt>=2.8.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.6",
]
```

- [x] **Step 2: 安装依赖**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv sync`

- [x] **Step 3: 在 .env 添加 JWT 和 admin 配置**

在 `.env` 文件末尾追加：

```
JWT_SECRET=intelligent-customer-jwt-secret-2026
JWT_EXPIRE_MINUTES=10080
ADMIN_PASSWORD=admin123456
```

- [x] **Step 4: 在 config.py 添加对应字段**

在 `Settings` 类中，`LOG_LEVEL` 字段之后添加：

```python
    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

    # Admin
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123456")
```

- [x] **Step 5: 验证配置可读取**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -c "from app.core.config import settings; print(f'JWT_SECRET={settings.JWT_SECRET}, JWT_EXPIRE={settings.JWT_EXPIRE_MINUTES}, ADMIN_PW={settings.ADMIN_PASSWORD}')"`
Expected: 输出配置的值，无报错

- [x] **Step 6: Commit**

```bash
git add apps/service/pyproject.toml apps/service/uv.lock apps/service/.env apps/service/app/core/config.py
git commit -m "feat: add JWT, SQLAlchemy, and bcrypt dependencies with config"
```

---

### Task 3: 创建数据库会话和用户模型

**Files:**
- Create: `apps/service/app/db/__init__.py`
- Create: `apps/service/app/db/session.py`
- Create: `apps/service/app/models/__init__.py`
- Create: `apps/service/app/models/user.py`
- Test: `apps/service/tests/test_user_model.py`

**Interfaces:**
- Consumes: `settings.database_url`（来自 Task 2）
- Produces: `get_db()` 依赖注入函数，`User` ORM 模型（含 `id`, `username`, `password_hash`, `role`, `created_at` 字段），`Base` 声明基类

- [x] **Step 1: 创建 db 包**

```python
# apps/service/app/db/__init__.py
from app.db.session import get_db, async_session_factory, engine
```

```python
# apps/service/app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.DB_ECHO)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

- [x] **Step 2: 创建 models 包和 User 模型**

```python
# apps/service/app/models/__init__.py
from app.models.user import User
```

```python
# apps/service/app/models/user.py
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
```

- [x] **Step 3: 编写 User 模型测试**

```python
# apps/service/tests/test_user_model.py
from app.models.user import User


def test_user_model_fields():
    user = User(username="testuser", password_hash="hashed", role="user")
    assert user.username == "testuser"
    assert user.password_hash == "hashed"
    assert user.role == "user"


def test_user_model_default_role():
    user = User(username="testuser", password_hash="hashed")
    assert user.role == "user"
```

- [x] **Step 4: 运行模型测试**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_user_model.py -v`
Expected: ALL PASS

- [x] **Step 5: Commit**

```bash
git add apps/service/app/db/ apps/service/app/models/ apps/service/tests/test_user_model.py
git commit -m "feat: add async database session and User ORM model"
```

---

### Task 4: 创建 JWT 和密码工具模块

**Files:**
- Create: `apps/service/app/utils/jwt.py`
- Create: `apps/service/app/utils/password.py`
- Test: `apps/service/tests/test_jwt_utils.py`
- Test: `apps/service/tests/test_password_utils.py`

**Interfaces:**
- Consumes: `settings.JWT_SECRET`, `settings.JWT_EXPIRE_MINUTES`（来自 Task 2）
- Produces: `create_token(user_id, username, role) -> str`，`verify_token(token) -> dict`，`hash_password(password) -> str`，`verify_password(plain, hashed) -> bool`

- [x] **Step 1: 编写 JWT 工具失败测试**

```python
# apps/service/tests/test_jwt_utils.py
import pytest
from app.utils.jwt import create_token, verify_token


def test_create_and_verify_token():
    token = create_token(user_id=1, username="admin", role="admin")
    payload = verify_token(token)
    assert payload["sub"] == 1
    assert payload["username"] == "admin"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_verify_invalid_token_raises():
    with pytest.raises(ValueError, match="无效的 Token"):
        verify_token("invalid.token.here")
```

- [x] **Step 2: 运行 JWT 测试确认失败**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_jwt_utils.py -v`
Expected: FAIL — module not found

- [x] **Step 3: 实现 JWT 工具**

```python
# apps/service/app/utils/jwt.py
from datetime import datetime, timezone, timedelta

import jwt

from app.core.config import settings


def create_token(user_id: int, username: str, role: str) -> str:
    """生成 HS256 JWT，payload 包含 sub(user_id)、username、role、exp"""
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> dict:
    """验证 JWT 签名和有效期，返回 payload 或抛出异常"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token 已过期")
    except jwt.InvalidTokenError:
        raise ValueError("无效的 Token")
```

- [x] **Step 4: 运行 JWT 测试确认通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_jwt_utils.py -v`
Expected: ALL PASS

- [x] **Step 5: 编写密码工具失败测试**

```python
# apps/service/tests/test_password_utils.py
from app.utils.password import hash_password, verify_password


def test_hash_and_verify_password():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert verify_password("mypassword", hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("mypassword")
    assert verify_password("wrongpassword", hashed) is False
```

- [x] **Step 6: 运行密码测试确认失败**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_password_utils.py -v`
Expected: FAIL — module not found

- [x] **Step 7: 实现密码工具**

```python
# apps/service/app/utils/password.py
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码"""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与哈希是否匹配"""
    return _pwd_context.verify(plain, hashed)
```

- [x] **Step 8: 运行密码测试确认通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_password_utils.py -v`
Expected: ALL PASS

- [x] **Step 9: Commit**

```bash
git add apps/service/app/utils/jwt.py apps/service/app/utils/password.py apps/service/tests/test_jwt_utils.py apps/service/tests/test_password_utils.py
git commit -m "feat: add JWT and password utility modules"
```

---

## 后端认证逻辑

### Task 5: 创建认证服务和安全依赖

**Files:**
- Create: `apps/service/app/services/__init__.py`
- Create: `apps/service/app/services/auth.py`
- Create: `apps/service/app/core/security.py`
- Test: `apps/service/tests/test_auth_service.py`

**Interfaces:**
- Consumes: `User` 模型（来自 Task 3），`verify_password`/`hash_password`（来自 Task 4），`create_token`（来自 Task 4），`get_db`（来自 Task 3），`settings.ADMIN_PASSWORD`（来自 Task 2）
- Produces: `authenticate_user(db, username, password) -> User`，`register_user(db, username, password) -> User`，`get_user_by_username(db, username) -> User | None`，`seed_admin_user(db)`，`get_current_user(token, db) -> User`

- [x] **Step 1: 编写认证服务失败测试**

```python
# apps/service/tests/test_auth_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.auth import authenticate_user, register_user, get_user_by_username


@pytest.mark.asyncio
async def test_register_user_creates_new_user():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    user = await register_user(db, username="newuser", password="password123")
    assert user.username == "newuser"
    assert user.role == "user"
    assert user.password_hash != "password123"
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_authenticate_user_with_correct_password():
    db = AsyncMock()
    from app.utils.password import hash_password
    mock_user = MagicMock()
    mock_user.username = "testuser"
    mock_user.password_hash = hash_password("password123")
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user)))
    user = await authenticate_user(db, username="testuser", password="password123")
    assert user is not None
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_authenticate_user_with_wrong_password_returns_none():
    db = AsyncMock()
    from app.utils.password import hash_password
    mock_user = MagicMock()
    mock_user.password_hash = hash_password("password123")
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user)))
    user = await authenticate_user(db, username="testuser", password="wrongpassword")
    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_not_found_returns_none():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    user = await authenticate_user(db, username="nonexistent", password="password123")
    assert user is None
```

- [x] **Step 2: 运行测试确认失败**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_auth_service.py -v`
Expected: FAIL — module not found

- [x] **Step 3: 创建 services 包和认证服务**

```python
# apps/service/app/services/__init__.py
from app.services.auth import authenticate_user, register_user, get_user_by_username, seed_admin_user
```

```python
# apps/service/app/services/auth.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.utils.password import hash_password, verify_password
from app.core.config import settings


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """根据用户名查询用户"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """验证用户名密码，成功返回 User，失败返回 None"""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def register_user(db: AsyncSession, username: str, password: str) -> User:
    """创建新用户（默认 role='user'）"""
    user = User(
        username=username,
        password_hash=hash_password(password),
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def seed_admin_user(db: AsyncSession) -> None:
    """启动时检查 admin 用户是否存在，不存在则创建"""
    existing = await get_user_by_username(db, "admin")
    if not existing:
        admin = User(
            username="admin",
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role="admin",
        )
        db.add(admin)
        await db.commit()
```

- [x] **Step 4: 创建 JWT 认证依赖**

```python
# apps/service/app/core/security.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.utils.jwt import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从请求头提取并验证 Bearer token，返回当前用户"""
    try:
        payload = verify_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的认证凭据")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="无效的认证凭据")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user
```

- [x] **Step 5: 运行认证服务测试确认通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_auth_service.py -v`
Expected: ALL PASS

- [x] **Step 6: Commit**

```bash
git add apps/service/app/services/ apps/service/app/core/security.py apps/service/tests/test_auth_service.py
git commit -m "feat: add auth service and JWT security dependency"
```

---

### Task 6: 创建认证路由并集成到主应用

**Files:**
- Create: `apps/service/app/routers/auth.py`
- Modify: `apps/service/app/routers/__init__.py`
- Modify: `apps/service/app/main.py`
- Test: `apps/service/tests/test_auth_routes.py`

**Interfaces:**
- Consumes: `authenticate_user`, `register_user`, `seed_admin_user`（来自 Task 5），`create_token`（来自 Task 4），`get_current_user`（来自 Task 5），`get_db`（来自 Task 3），`success`/`error`（来自 Task 1），`Base`（来自 Task 3）
- Produces: `POST /api/auth/login`，`POST /api/auth/register`，`GET /api/auth/me` 端点

- [x] **Step 1: 编写认证路由测试**

```python
# apps/service/tests/test_auth_routes.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_register_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/auth/register", json={
            "username": "testuser1",
            "password": "password123",
        })
        body = resp.json()
        assert body["code"] == 0
        assert "token" in body["data"]
        assert body["data"]["user"]["username"] == "testuser1"
        assert body["data"]["user"]["role"] == "user"


@pytest.mark.anyio
async def test_register_duplicate_username():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/auth/register", json={
            "username": "testuser2",
            "password": "password123",
        })
        resp = await client.post("/api/auth/register", json={
            "username": "testuser2",
            "password": "password123",
        })
        body = resp.json()
        assert body["code"] == 30002
        assert "已存在" in body["message"]


@pytest.mark.anyio
async def test_login_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/auth/register", json={
            "username": "loginuser",
            "password": "password123",
        })
        resp = await client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "password123",
        })
        body = resp.json()
        assert body["code"] == 0
        assert "token" in body["data"]


@pytest.mark.anyio
async def test_login_wrong_password():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/auth/register", json={
            "username": "wrongpwuser",
            "password": "password123",
        })
        resp = await client.post("/api/auth/login", json={
            "username": "wrongpwuser",
            "password": "wrongpassword",
        })
        body = resp.json()
        assert body["code"] == 30001


@pytest.mark.anyio
async def test_me_with_valid_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/auth/register", json={
            "username": "meuser",
            "password": "password123",
        })
        token = reg.json()["data"]["token"]
        resp = await client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["username"] == "meuser"


@pytest.mark.anyio
async def test_me_without_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401
```

- [x] **Step 2: 运行测试确认失败**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_auth_routes.py -v`
Expected: FAIL — router not found

- [x] **Step 3: 创建认证路由**

```python
# apps/service/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth import authenticate_user, register_user, get_user_by_username
from app.utils.jwt import create_token
from app.utils.response import success, error
from app.core.security import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or len(v) < 1:
            raise ValueError("用户名不能为空")
        if len(v) > 20:
            raise ValueError("用户名最多20位")
        if not v.replace("_", "").isalnum():
            raise ValueError("用户名仅支持字母数字下划线")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少6位")
        return v


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, req.username, req.password)
    if not user:
        return error(code=30001, message="用户名或密码错误")
    token = create_token(user_id=user.id, username=user.username, role=user.role)
    return success(data={
        "token": token,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    })


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_username(db, req.username)
    if existing:
        return error(code=30002, message="用户名已存在")
    user = await register_user(db, req.username, req.password)
    token = create_token(user_id=user.id, username=user.username, role=user.role)
    return success(data={
        "token": token,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    })


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return success(data={
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
    })
```

- [x] **Step 4: 更新 routers/__init__.py 导出 auth_router**

```python
# apps/service/app/routers/__init__.py
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
```

- [x] **Step 5: 更新 main.py 注册路由、CORS、lifespan 初始化**

```python
# apps/service/app/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import health_router, auth_router
from app.core.config import settings
from app.db.session import engine, Base
from app.services.auth import seed_admin_user
from app.db.session import async_session_factory

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
logger = logging.getLogger("ai-service")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("启动中...  创建数据库表")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("启动中...  初始化 admin 用户")
    async with async_session_factory() as session:
        await seed_admin_user(session)
    logger.info("启动完成  %s:%s", settings.APP_HOST, settings.APP_PORT)
    yield
    logger.info("关闭中...")
    await engine.dispose()
    logger.info("已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
```

- [x] **Step 6: 运行所有后端测试确认通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/ -v`

注意：路由集成测试需要数据库连接。如果本地无 MySQL，可以单独运行单元测试：

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python -m pytest tests/test_response_utils.py tests/test_user_model.py tests/test_jwt_utils.py tests/test_password_utils.py tests/test_auth_service.py -v`
Expected: ALL PASS

- [x] **Step 7: Commit**

```bash
git add apps/service/app/routers/auth.py apps/service/app/routers/__init__.py apps/service/app/main.py apps/service/tests/test_auth_routes.py
git commit -m "feat: add auth routes and integrate with main app (CORS, lifespan, admin seed)"
```

---

## 前端认证服务层

### Task 7: 创建前端 auth service 和 auth store

**Files:**
- Create: `apps/web/services/auth.ts`
- Create: `apps/web/store/auth.ts`
- Test: `apps/web/__tests__/auth-store.test.ts`

**Interfaces:**
- Consumes: `fetchClient`（来自 `apps/web/lib/fetch/index.ts`），`tokenManager`（来自 `apps/web/lib/fetch/token-manager.ts`）
- Produces: `loginApi(username, password)`，`registerApi(username, password)`，`getMeApi()`，`useAuthStore()` Zustand store（含 `user`, `isAuthenticated`, `loading`, `login`, `register`, `fetchUser`, `logout`, `initAuth`）

- [x] **Step 1: 创建 auth service**

```typescript
// apps/web/services/auth.ts
import { fetchClient } from "@/lib/fetch";
import type { ApiResponse } from "@intelligent-customer/fetch-client";

export interface User {
  id: number;
  username: string;
  role: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export async function loginApi(username: string, password: string) {
  return fetchClient.post<AuthResponse>("/api/auth/login", {
    username,
    password,
  });
}

export async function registerApi(username: string, password: string) {
  return fetchClient.post<AuthResponse>("/api/auth/register", {
    username,
    password,
  });
}

export async function getMeApi() {
  return fetchClient.get<User>("/api/auth/me");
}
```

- [x] **Step 2: 编写 auth store 测试**

```typescript
// apps/web/__tests__/auth-store.test.ts
import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("@/lib/fetch/token-manager", () => ({
  tokenManager: {
    getToken: vi.fn(),
    setToken: vi.fn(),
    clearToken: vi.fn(),
    isAuthenticated: vi.fn(),
  },
}));

vi.mock("@/services/auth", () => ({
  loginApi: vi.fn(),
  registerApi: vi.fn(),
  getMeApi: vi.fn(),
}));

import { useAuthStore } from "@/store/auth";
import { tokenManager } from "@/lib/fetch/token-manager";
import { loginApi, registerApi } from "@/services/auth";

const mockedLoginApi = vi.mocked(loginApi);
const mockedRegisterApi = vi.mocked(registerApi);
const mockedSetToken = vi.mocked(tokenManager.setToken);
const mockedClearToken = vi.mocked(tokenManager.clearToken);

describe("authStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const store = useAuthStore.getState();
    store.logout();
  });

  it("login 成功后设置 token 和用户状态", async () => {
    mockedLoginApi.mockResolvedValueOnce({
      code: 0,
      message: "success",
      data: {
        token: "test-jwt-token",
        user: { id: 1, username: "admin", role: "admin" },
      },
    });

    await useAuthStore.getState().login("admin", "password123");

    expect(mockedSetToken).toHaveBeenCalledWith("test-jwt-token");
    const state = useAuthStore.getState();
    expect(state.user?.username).toBe("admin");
    expect(state.isAuthenticated).toBe(true);
  });

  it("logout 清除 token 和用户状态", () => {
    useAuthStore.setState({
      user: { id: 1, username: "admin", role: "admin" },
      isAuthenticated: true,
    });

    useAuthStore.getState().logout();

    expect(mockedClearToken).toHaveBeenCalled();
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it("register 成功后设置 token 和用户状态", async () => {
    mockedRegisterApi.mockResolvedValueOnce({
      code: 0,
      message: "success",
      data: {
        token: "new-jwt-token",
        user: { id: 2, username: "newuser", role: "user" },
      },
    });

    await useAuthStore.getState().register("newuser", "password123");

    expect(mockedSetToken).toHaveBeenCalledWith("new-jwt-token");
    const state = useAuthStore.getState();
    expect(state.user?.username).toBe("newuser");
    expect(state.isAuthenticated).toBe(true);
  });
});
```

- [x] **Step 3: 运行 store 测试确认失败**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm test -- --run __tests__/auth-store.test.ts`
Expected: FAIL — module not found

- [x] **Step 4: 创建 auth store**

```typescript
// apps/web/store/auth.ts
import { create } from "zustand";
import { tokenManager } from "@/lib/fetch/token-manager";
import { loginApi, registerApi, getMeApi, type User } from "@/services/auth";

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

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  loading: false,

  login: async (username, password) => {
    const res = await loginApi(username, password);
    tokenManager.setToken(res.data.token);
    set({ user: res.data.user, isAuthenticated: true });
  },

  register: async (username, password) => {
    const res = await registerApi(username, password);
    tokenManager.setToken(res.data.token);
    set({ user: res.data.user, isAuthenticated: true });
  },

  fetchUser: async () => {
    try {
      const res = await getMeApi();
      set({ user: res.data, isAuthenticated: true, loading: false });
    } catch {
      tokenManager.clearToken();
      set({ user: null, isAuthenticated: false, loading: false });
    }
  },

  logout: () => {
    tokenManager.clearToken();
    set({ user: null, isAuthenticated: false });
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  },

  initAuth: async () => {
    if (tokenManager.isAuthenticated()) {
      set({ loading: true });
      try {
        const res = await getMeApi();
        set({ user: res.data, isAuthenticated: true, loading: false });
      } catch {
        tokenManager.clearToken();
        set({ user: null, isAuthenticated: false, loading: false });
      }
    } else {
      set({ user: null, isAuthenticated: false, loading: false });
    }
  },
}));
```

- [x] **Step 5: 运行 store 测试确认通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm test -- --run __tests__/auth-store.test.ts`
Expected: ALL PASS

- [x] **Step 6: Commit**

```bash
git add apps/web/services/auth.ts apps/web/store/auth.ts apps/web/__tests__/auth-store.test.ts
git commit -m "feat: add frontend auth service and Zustand auth store"
```

---

### Task 8: 添加 401 响应拦截器

**Files:**
- Modify: `apps/web/lib/fetch/index.ts`
- Test: `apps/web/__tests__/interceptor-401.test.ts`

**Interfaces:**
- Consumes: `tokenManager`（来自 `apps/web/lib/fetch/token-manager.ts`），`FetchError`/`ErrorType`（来自 `@intelligent-customer/fetch-client`），现有 `fetchClient` 实例
- Produces: 401 拦截器注册到 `fetchClient`，AuthError/TokenExpired 时自动清除 token 并跳转 `/login`

- [x] **Step 1: 编写 401 拦截器测试**

```typescript
// apps/web/__tests__/interceptor-401.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { FetchError, ErrorType } from "@intelligent-customer/fetch-client";

vi.mock("@/lib/fetch/token-manager", () => ({
  tokenManager: {
    getToken: vi.fn(),
    setToken: vi.fn(),
    clearToken: vi.fn(),
    isAuthenticated: vi.fn(),
  },
}));

describe("401 interceptor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete (window as Record<string, unknown>).location;
    (window as Record<string, unknown>).location = { href: "", pathname: "/dashboard" };
  });

  it("AuthError 类型错误清除 token 并跳转 /login", async () => {
    const { handleAuthError } = await import("@/lib/fetch/index");
    const authError = new FetchError("未授权", ErrorType.AuthError, { status: 401 });
    handleAuthError(authError);
    const { tokenManager } = await import("@/lib/fetch/token-manager");
    const mockedClearToken = vi.mocked(tokenManager.clearToken);
    expect(mockedClearToken).toHaveBeenCalled();
    expect(window.location.href).toBe("/login");
  });

  it("TokenExpired 类型错误清除 token 并跳转 /login", async () => {
    const { handleAuthError } = await import("@/lib/fetch/index");
    const expiredError = new FetchError("Token 过期", ErrorType.TokenExpired, { status: 401 });
    handleAuthError(expiredError);
    const { tokenManager } = await import("@/lib/fetch/token-manager");
    const mockedClearToken = vi.mocked(tokenManager.clearToken);
    expect(mockedClearToken).toHaveBeenCalled();
    expect(window.location.href).toBe("/login");
  });

  it("非 AuthError 不触发跳转", async () => {
    const { handleAuthError } = await import("@/lib/fetch/index");
    const otherError = new FetchError("服务器错误", ErrorType.ServerError, { status: 500 });
    handleAuthError(otherError);
    const { tokenManager } = await import("@/lib/fetch/token-manager");
    const mockedClearToken = vi.mocked(tokenManager.clearToken);
    expect(mockedClearToken).not.toHaveBeenCalled();
  });
});
```

- [x] **Step 2: 运行测试确认失败**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm test -- --run __tests__/interceptor-401.test.ts`
Expected: FAIL — handleAuthError not exported

- [x] **Step 3: 在 lib/fetch/index.ts 中添加 401 拦截器**

在现有的 `fetchClient` 定义和拦截器之后，添加 401 认证拦截器。完整的修改后文件：

```typescript
// apps/web/lib/fetch/index.ts
import { FetchClient, FetchError, ErrorType } from "@intelligent-customer/fetch-client";
import { tokenManager } from "./token-manager";
import { TOKEN_KEY, APP_CONFIG } from "./config";
import { getBusinessErrorType } from "./types";
import { toast } from "sonner";

const fetchClient = new FetchClient({ baseURL: APP_CONFIG.baseURL });

// Request interceptor: inject Bearer token
fetchClient.useRequestInterceptor((ctx) => {
  const token = tokenManager.getToken();
  if (token) {
    ctx.config.headers = { ...ctx.config.headers, Authorization: `Bearer ${token}` };
  }
  return ctx;
});

// Response error interceptor: map business error codes to ErrorType
fetchClient.useResponseErrorInterceptor((error) => {
  if (error instanceof FetchError && error.code) {
    error.type = getBusinessErrorType(error.code);
  }
  return error;
});

// 401 认证拦截器：token 过期或无效时清除状态并跳转登录页
let _isRedirecting = false;

export function handleAuthError(error: Error): Error {
  if (
    error instanceof FetchError &&
    (error.type === ErrorType.AuthError || error.type === ErrorType.TokenExpired)
  ) {
    tokenManager.clearToken();
    if (typeof window !== "undefined" && !_isRedirecting && !window.location.pathname.startsWith("/login")) {
      _isRedirecting = true;
      window.location.href = "/login";
      setTimeout(() => { _isRedirecting = false; }, 1000);
    }
  }
  return error;
}

fetchClient.useResponseErrorInterceptor(handleAuthError);

// Response error interceptor: toast all errors (skip 401 since already redirected)
fetchClient.useResponseErrorInterceptor((err) => {
  if (err instanceof FetchError && (err.type === ErrorType.AuthError || err.type === ErrorType.TokenExpired)) {
    return err;
  }
  toast.error(err.toString(), { position: "top-center" });
  return err;
});

// Server-side client factory
export async function createServerClient(): Promise<FetchClient> {
  const { cookies } = await import("next/headers");
  const cookieStore = await cookies();
  const token = cookieStore.get(TOKEN_KEY)?.value ?? null;
  const client = new FetchClient({ baseURL: APP_CONFIG.baseURL });
  if (token) client.setDefaultHeader("Authorization", `Bearer ${token}`);
  return client;
}

export { fetchClient };
```

- [x] **Step 4: 运行拦截器测试确认通过**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm test -- --run __tests__/interceptor-401.test.ts`
Expected: ALL PASS

- [x] **Step 5: Commit**

```bash
git add apps/web/lib/fetch/index.ts apps/web/__tests__/interceptor-401.test.ts
git commit -m "feat: add 401 auth error interceptor with redirect and dedup"
```

---

## 前端登录/注册页面

### Task 9: 安装 shadcn 组件并实现登录/注册页面

**Files:**
- Modify: `apps/web/app/login/page.tsx`
- Generated by shadcn: `packages/ui/src/components/card.tsx`, `packages/ui/src/components/input.tsx`, `packages/ui/src/components/label.tsx`, `packages/ui/src/components/form.tsx`

**Interfaces:**
- Consumes: `useAuthStore`（来自 Task 7），shadcn Card/Input/Button 组件
- Produces: 登录/注册页面组件，含表单校验（zod），登录/注册模式切换

- [x] **Step 1: 安装需要的 shadcn 组件**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm dlx shadcn@latest add card input label form`

- [x] **Step 2: 安装 react-hook-form 和 zod 依赖（如果尚未安装）**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm add react-hook-form @hookform/resolvers zod`

- [x] **Step 3: 实现登录/注册页面**

```tsx
// apps/web/app/login/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth";
import { Button } from "@intelligent-customer/ui/components/button";
import { Input } from "@intelligent-customer/ui/components/input";
import { Label } from "@intelligent-customer/ui/components/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@intelligent-customer/ui/components/card";

const loginSchema = z.object({
  username: z
    .string()
    .min(1, "请输入用户名")
    .max(20, "用户名最多20位")
    .regex(/^[a-zA-Z0-9_]+$/, "仅支持字母数字下划线"),
  password: z.string().min(6, "密码至少6位"),
});

const registerSchema = loginSchema.extend({
  confirmPassword: z.string().min(6, "确认密码至少6位"),
}).refine((data) => data.password === data.confirmPassword, {
  message: "两次密码不一致",
  path: ["confirmPassword"],
});

type LoginFormData = z.infer<typeof loginSchema>;
type RegisterFormData = z.infer<typeof registerSchema>;

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const router = useRouter();
  const { login, register: registerUser } = useAuthStore();
  const [submitting, setSubmitting] = useState(false);

  const loginForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const registerForm = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: "", password: "", confirmPassword: "" },
  });

  const handleLogin = async (data: LoginFormData) => {
    setSubmitting(true);
    try {
      await login(data.username, data.password);
      router.push("/");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRegister = async (data: RegisterFormData) => {
    setSubmitting(true);
    try {
      await registerUser(data.username, data.password);
      router.push("/");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "注册失败");
    } finally {
      setSubmitting(false);
    }
  };

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

        {mode === "login" ? (
          <form onSubmit={loginForm.handleSubmit(handleLogin)}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
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
              <div className="space-y-2">
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
                <button
                  type="button"
                  className="text-primary underline-offset-4 hover:underline"
                  onClick={() => setMode("register")}
                >
                  注册
                </button>
              </p>
            </CardFooter>
          </form>
        ) : (
          <form onSubmit={registerForm.handleSubmit(handleRegister)}>
            <CardContent className="space-y-4">
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
            </CardContent>
            <CardFooter className="flex flex-col gap-3">
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "注册中..." : "注册"}
              </Button>
              <p className="text-sm text-muted-foreground">
                已有账户？{" "}
                <button
                  type="button"
                  className="text-primary underline-offset-4 hover:underline"
                  onClick={() => setMode("login")}
                >
                  登录
                </button>
              </p>
            </CardFooter>
          </form>
        )}
      </Card>
    </div>
  );
}
```

- [x] **Step 4: 验证页面可编译**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm build 2>&1 | head -50`
Expected: 无编译错误（可能有其他页面的 warning，但 login 页面不应有错误）

- [x] **Step 5: Commit**

```bash
git add apps/web/app/login/page.tsx apps/web/package.json apps/web/pnpm-lock.yaml packages/ui/src/components/
git commit -m "feat: implement login/register page with form validation and mode toggle"
```

---

## 前端路由守卫

### Task 10: 创建 Next.js Middleware 路由守卫

**Files:**
- Create: `apps/web/middleware.ts`

**Interfaces:**
- Consumes: Cookie `auth_token`（由 `tokenManager` 设置）
- Produces: 未登录访问非 /login 页面时重定向到 /login；已登录访问 /login 时重定向到 /

- [x] **Step 1: 创建 middleware**

```typescript
// apps/web/middleware.ts
import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("auth_token")?.value;
  const { pathname } = request.nextUrl;

  // 已登录访问 /login → 重定向到首页
  if (token && pathname === "/login") {
    return NextResponse.redirect(new URL("/", request.url));
  }

  // 未登录访问非 /login 页面 → 重定向到登录页
  if (!token && pathname !== "/login") {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

- [x] **Step 2: 验证 middleware 不影响构建**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm build 2>&1 | tail -20`
Expected: 构建成功

- [x] **Step 3: Commit**

```bash
git add apps/web/middleware.ts
git commit -m "feat: add Next.js middleware for auth route guard"
```

---

### Task 11: 在首页添加退出登录按钮

**Files:**
- Modify: `apps/web/app/page.tsx`

**Interfaces:**
- Consumes: `useAuthStore`（来自 Task 7），`Button` 组件
- Produces: 首页包含用户名显示和退出登录按钮

- [x] **Step 1: 更新首页**

```tsx
// apps/web/app/page.tsx
"use client";

import { useEffect } from "react";
import { Button } from "@intelligent-customer/ui/components/button";
import { useAuthStore } from "@/store/auth";

export default function Page() {
  const { user, initAuth, logout, loading } = useAuthStore();

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  if (loading) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <p className="text-muted-foreground">加载中...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-svh p-6">
      <div className="flex max-w-md min-w-0 flex-col gap-4 text-sm leading-loose">
        <div>
          <h1 className="font-medium">欢迎使用 AI 客服系统</h1>
          {user && (
            <p className="mt-2 text-muted-foreground">
              你好，{user.username}（{user.role}）
            </p>
          )}
          <Button className="mt-4" variant="outline" onClick={logout}>
            退出登录
          </Button>
        </div>
        <div className="text-muted-foreground font-mono text-xs">
          (Press <kbd>d</kbd> to toggle dark mode)
        </div>
      </div>
    </div>
  );
}
```

- [x] **Step 2: 验证构建**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm build 2>&1 | tail -20`
Expected: 构建成功

- [x] **Step 3: Commit**

```bash
git add apps/web/app/page.tsx
git commit -m "feat: add logout button and user info to home page"
```

---

## 联调与配置

### Task 12: 配置前端环境变量

**Files:**
- Create: `apps/web/.env.local`

**Interfaces:**
- Consumes: 后端运行在 `http://localhost:8001`
- Produces: `NEXT_PUBLIC_API_URL` 和 `NEXT_PUBLIC_API_BASE_URL` 环境变量，使 `lib/fetch/config.ts` 的 `BASE_URL` 正确指向后端

- [x] **Step 1: 创建 .env.local**

```
# apps/web/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_API_BASE_URL=
```

注意：`NEXT_PUBLIC_API_BASE_URL` 留空，因为后端路由已经包含 `/api/auth/...` 前缀，不需要额外的 base path。如果 `NEXT_PUBLIC_API_URL` 末尾不带斜杠且 `NEXT_PUBLIC_API_BASE_URL` 为空，拼接后为 `http://localhost:8001`，前端请求 `/api/auth/login` 即访问 `http://localhost:8001/api/auth/login`。

- [x] **Step 2: 验证配置生效**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm build 2>&1 | tail -10`
Expected: 构建成功，无环境变量缺失报错

- [x] **Step 3: Commit**

```bash
git add apps/web/.env.local
git commit -m "feat: add frontend env config for API base URL"
```

---

### Task 13: 端到端联调验证

**Files:**
- 无代码变更，仅手动验证

**Interfaces:**
- Consumes: 所有前序 Task 的产物
- Produces: 确认完整认证流程可工作

- [x] **Step 1: 启动后端服务**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/service && uv run python main.py`

验证：控制台输出"启动完成"，无报错

- [x] **Step 2: 启动前端开发服务器**

Run: `cd /Users/superhuan/Documents/project/intelligent-customer/apps/web && pnpm dev`

验证：控制台输出 localhost URL

- [x] **Step 3: 验证注册流程**

1. 浏览器打开 `http://localhost:3000`，应被重定向到 `/login`
2. 点击"注册"切换到注册模式
3. 输入用户名 `testuser`，密码 `password123`，确认密码 `password123`
4. 点击"注册"
5. 验证：注册成功后跳转到首页，显示"你好，testuser（user）"

- [x] **Step 4: 验证退出登录**

1. 在首页点击"退出登录"按钮
2. 验证：跳转回 `/login` 页面

- [x] **Step 5: 验证登录流程**

1. 在登录页输入 `testuser` / `password123`
2. 点击"登录"
3. 验证：登录成功后跳转到首页

- [x] **Step 6: 验证 admin 默认用户**

1. 退出登录
2. 使用 `admin` / `admin123456` 登录
3. 验证：登录成功，首页显示"你好，admin（admin）"

- [x] **Step 7: 验证表单校验**

1. 在登录页输入空用户名 → 验证显示"请输入用户名"
2. 输入密码 `123` → 验证显示"密码至少6位"
3. 切换到注册模式，两次密码不一致 → 验证显示"两次密码不一致"

- [x] **Step 8: 验证错误登录**

1. 输入正确用户名但错误密码 → 验证显示错误 toast
2. 输入不存在的用户名 → 验证显示错误 toast（不暴露用户是否存在）
