---
change: user-management-api
design-doc: docs/superpowers/specs/2026-08-17-user-management-api-design.md
base-ref: 89e9827463d743dd65ad68a70dbd4ce623e8a1f7
---

# 用户管理真实接口（后端 users API + 前端去 mock）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现后端用户管理 API（列表/创建/删除，仅 admin）并让前端 users 页接入真实接口、去掉 mock 数据。

**Architecture:** 三层单向依赖：服务层（`services/auth.py` 扩展三个函数，接受 `db: AsyncSession` 首参，删除保护在此权威校验）→ API 层（`api/users.py` 三个端点，仅 admin，`ValueError` → 40004、非 admin → 40003、删不存在 → 40005，注册进 `api/__init__.py` + `app/main.py`）→ 前端（`services/users.ts` fetchClient 封装 + `app/users/useServices.ts` useRequest 状态 + `app/users/page.tsx` 去 mock）。测试仅后端（服务层 AsyncMock 单测 + API 权限 TestClient），前端用 `pnpm typecheck` + 端到端实测验证。详见设计文档 `docs/superpowers/specs/2026-08-17-user-management-api-design.md` 决策 D1–D4。

**Tech Stack:** Python / FastAPI / SQLAlchemy async / pytest（anyio + AsyncMock）；TypeScript / Next.js / ahooks `useRequest` / shadcn-ui 组件 / next-intl / `@intelligent-customer/fetch-client`。

## Global Constraints

- 产物语言：简体中文（本计划、commit message 均用中文；代码标识符与 i18n key 除外）。
- 服务层删除保护权威校验：`delete_user` 直接拒绝删 admin / 删自己；API 层只把 `current_user.id` 传给服务层；前端 admin 行置灰仅是 UX 防误触，防绕过依赖服务层。
- 错误码契约：非 admin → `40003`；`ValueError`（重复用户名 / 密码过短 / 非法角色 / 删除保护）→ `40004` + 具体 message；删除不存在的用户 → `40005`。
- `create_user` 独立实现但复用 `utils.password.hash_password`；**不得改动 `register_user`**（user-auth 不回归）。
- 后端测试命令：`cd apps/service && .venv/bin/python -m pytest <file> -v`（单文件）；全量 `cd apps/service && .venv/bin/python -m pytest tests/ -q`。
- 前端验证：`cd apps/web && pnpm typecheck`，本 change 文件 **0 新增错误**；`__tests__` 目录 14 个基线存量错误忽略，不得顺手修复。
- 前端不写单测（设计 D4），成功/失败提示由页面 `sonner` toast 承担；请求失败错误已由 `fetchClient` 响应拦截器统一 toast，页面 `catch` 块留空即可。
- 响应统一 `{ code, message, data }`（`utils.response.success/error`）；`fetchClient.get<T>()` 返回 `ApiResponse<T>`，前端取 payload 用 `res.data`。

## File Structure

**新建文件（5 个源码/测试 + 1 个 schema）：**

- `apps/service/api/users.py` — 用户管理 API 路由（GET/POST/DELETE，admin 校验，错误码映射）
- `apps/service/schemas/user_schema.py` — `UserItem` pydantic 响应模型（`from_attributes`，镜像 `schemas/document_schema.py` 的 `DocumentItem` 惯例）
- `apps/service/tests/test_user_management.py` — 服务层 10 用例 + API 权限 1 用例（镜像 `test_auth_service.py` 的 AsyncMock 模式）
- `apps/web/services/users.ts` — `User` 类型 + `getUsersApi` / `createUserApi` / `deleteUserApi`（fetchClient 封装，镜像 `services/tickets.ts`）
- `apps/web/app/users/useServices.ts` — `useUserServices` hook（useRequest 列表自动加载 + 新增/删除手动控制，镜像 `app/tickets/useServices.ts`）

**修改文件（6 个）：**

- `apps/service/services/auth.py` — 末尾追加 `list_users` / `create_user` / `delete_user`
- `apps/service/api/__init__.py` — 追加 `from .users import router as users_router`
- `apps/service/app/main.py` — import 与 `include_router` 各追加 `users_router`
- `apps/web/app/users/page.tsx` — 去 `mockUsers`、真实列表渲染、搜索本地过滤、受控新增表单、admin 行删除置灰、created_at 本地化显示
- `apps/web/messages/zh-CN.json` — `users` 命名空间追加 `addUserSuccess` / `deleteUserSuccess`
- `apps/web/messages/en-US.json` — `users` 命名空间追加对应英文键

**任务边界对齐 tasks.md（3 组 8 任务）：** Task 1–3 = 后端（1.1/1.2/1.3）；Task 4–6 = 前端（2.1/2.2/2.3）；Task 7–8 = 验证（3.1/3.2）。

---

### Task 1: 服务层函数（tasks 1.1）

**Files:**
- Modify: `apps/service/services/auth.py`（在 `seed_admin_user` 之后追加三个函数）
- Test: `apps/service/tests/test_user_management.py`（新建，本次仅含服务层 10 个用例）

**Interfaces:**
- Consumes: 既有 `AsyncSession` / `User` ORM（`schemas/user.py`）/ `hash_password`（`utils/password.py`）/ `get_user_by_username`（本模块）
- Produces（供 Task 2/3 使用，精确签名）：
  - `async def list_users(db: AsyncSession) -> list[User]`
  - `async def create_user(db: AsyncSession, username: str, password: str, role: str = "user") -> User` —— 重复用户名抛 `ValueError("用户名已存在")`；密码不足 6 位抛 `ValueError("密码至少 6 位")`；role 不在 `{"user","admin"}` 抛 `ValueError("非法角色")`；成功则 commit + refresh 后返回
  - `async def delete_user(db: AsyncSession, user_id: int, current_user_id: int) -> bool | None` —— 目标不存在返回 `None`；目标 role == "admin" 抛 `ValueError("不能删除管理员用户")`；目标 id == current_user_id 抛 `ValueError("不能删除当前登录用户")`；否则删除 + commit，返回 `True`

- [x] **Step 1: 写失败的测试（服务层 10 用例）**

新建 `apps/service/tests/test_user_management.py`（注意：`db.add`、`db.delete` 是同步方法用 `MagicMock`；`db.commit`/`db.refresh`/`db.get`/`db.execute` 是异步用 `AsyncMock`；`list_users` 走 `result.scalars().all()`，`create_user` 先经 `get_user_by_username` 走 `result.scalar_one_or_none()`）：

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.auth import list_users, create_user, delete_user


def _execute_result(scalar_one_or_none_value=None):
    """构造 db.execute 返回的 result（scalar_one_or_none 模式，供 get_user_by_username 使用）"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none_value
    return result


def _make_user(id, username, role):
    u = MagicMock()
    u.id = id
    u.username = username
    u.role = role
    return u


# ---------- list_users ----------

@pytest.mark.anyio
async def test_list_users_returns_all():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _make_user(1, "admin", "admin"),
        _make_user(2, "zhang_san", "user"),
    ]
    db.execute = AsyncMock(return_value=result)

    users = await list_users(db)

    assert len(users) == 2
    assert users[0].username == "admin"
    assert users[1].role == "user"


# ---------- create_user ----------

@pytest.mark.anyio
async def test_create_user_uses_default_role():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock(return_value=_execute_result(None))  # 用户名不重复

    user = await create_user(db, username="newuser", password="password123")

    assert user.username == "newuser"
    assert user.role == "user"
    assert user.password_hash != "password123"
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_create_user_with_admin_role():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock(return_value=_execute_result(None))

    user = await create_user(db, username="newadmin", password="password123", role="admin")

    assert user.role == "admin"


@pytest.mark.anyio
async def test_create_user_duplicate_username_raises():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=_execute_result(_make_user(1, "newuser", "user"))
    )

    with pytest.raises(ValueError, match="用户名已存在"):
        await create_user(db, username="newuser", password="password123")


@pytest.mark.anyio
async def test_create_user_short_password_raises():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_execute_result(None))

    with pytest.raises(ValueError, match="密码至少 6 位"):
        await create_user(db, username="newuser", password="123")


@pytest.mark.anyio
async def test_create_user_invalid_role_raises():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_execute_result(None))

    with pytest.raises(ValueError, match="非法角色"):
        await create_user(db, username="newuser", password="password123", role="super")


# ---------- delete_user ----------

@pytest.mark.anyio
async def test_delete_user_success():
    db = AsyncMock()
    db.get = AsyncMock(return_value=_make_user(3, "zhang_san", "user"))
    db.delete = MagicMock()
    db.commit = AsyncMock()

    result = await delete_user(db, user_id=3, current_user_id=1)

    assert result is True
    db.delete.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_delete_user_not_found_returns_none():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    result = await delete_user(db, user_id=99, current_user_id=1)

    assert result is None


@pytest.mark.anyio
async def test_delete_user_admin_raises():
    db = AsyncMock()
    db.get = AsyncMock(return_value=_make_user(1, "admin", "admin"))

    with pytest.raises(ValueError, match="不能删除管理员用户"):
        await delete_user(db, user_id=1, current_user_id=2)


@pytest.mark.anyio
async def test_delete_user_self_raises():
    db = AsyncMock()
    db.get = AsyncMock(return_value=_make_user(1, "zhang_san", "user"))

    with pytest.raises(ValueError, match="不能删除当前登录用户"):
        await delete_user(db, user_id=1, current_user_id=1)
```

- [x] **Step 2: 运行测试确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_user_management.py -v`
Expected: 每个用例 FAIL，报 `ImportError: cannot import name 'list_users' from 'services.auth'`（三函数尚未定义）。

- [x] **Step 3: 实现服务层三个函数**

在 `apps/service/services/auth.py` 末尾（`seed_admin_user` 之后）追加：

```python
async def list_users(db: AsyncSession) -> list[User]:
    """获取全部用户（按 id 升序，管理员使用）"""
    result = await db.execute(select(User).order_by(User.id))
    return list(result.scalars().all())


async def create_user(
    db: AsyncSession, username: str, password: str, role: str = "user"
) -> User:
    """创建用户（管理员专用）——重复用户名/密码过短/非法角色抛 ValueError"""
    existing = await get_user_by_username(db, username)
    if existing:
        raise ValueError("用户名已存在")
    if len(password) < 6:
        raise ValueError("密码至少 6 位")
    if role not in {"user", "admin"}:
        raise ValueError("非法角色")
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(
    db: AsyncSession, user_id: int, current_user_id: int
) -> bool | None:
    """删除用户（管理员专用）——目标不存在返回 None；删除保护抛 ValueError"""
    user = await db.get(User, user_id)
    if not user:
        return None
    if user.role == "admin":
        raise ValueError("不能删除管理员用户")
    if user.id == current_user_id:
        raise ValueError("不能删除当前登录用户")
    await db.delete(user)
    await db.commit()
    return True
```

- [x] **Step 4: 运行测试确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_user_management.py -v`
Expected: 10 个用例全部 PASS。

- [x] **Step 5: Commit**

```bash
git add apps/service/services/auth.py apps/service/tests/test_user_management.py
git commit -m "feat(service): 用户管理服务层 list_users/create_user/delete_user（删除保护权威校验）"
```

---

### Task 2: 用户管理 API 与路由注册（tasks 1.2）

**Files:**
- Create: `apps/service/api/users.py`
- Create: `apps/service/schemas/user_schema.py`
- Modify: `apps/service/api/__init__.py`
- Modify: `apps/service/app/main.py`
- Test: `apps/service/tests/test_user_management.py`（追加 API 权限用例）

**Interfaces:**
- Consumes: Task 1 的 `list_users` / `create_user` / `delete_user`；既有 `get_current_user`（`auth/security.py`）、`get_db`（`database/session.py`）、`success` / `error`（`utils/response.py`）
- Produces（供 Task 3 校验与前端 Task 4 使用）：
  - `GET /api/users` → `{ code: 0, data: UserItem[] }`（`id/username/role/created_at`），非 admin → `{ code: 40003 }`
  - `POST /api/users`，body `{ username, password, role? }` → 成功 `{ code: 0, data: UserItem }`；`ValueError` → `{ code: 40004, message: str(e) }`；非 admin → 40003
  - `DELETE /api/users/{id}` → 成功 `{ code: 0, data: { success: true } }`；目标不存在 → `{ code: 40005 }`；`ValueError` → `{ code: 40004 }`；非 admin → 40003
  - `apps/service/schemas/user_schema.py` 导出 `UserItem`（pydantic，`model_config = {"from_attributes": True}`）

- [x] **Step 1: 写失败的 API 权限测试**

在 `apps/service/tests/test_user_management.py` 末尾追加（**API 相关 import 必须放在测试函数内部**，这样 Task 2 中 `api/users.py` 尚未创建时只让本用例失败、不影响其余 10 个服务层用例；这是同步 TestClient 用例，不加 `@pytest.mark.anyio`）：

```python
def test_users_api_rejects_non_admin():
    from unittest.mock import AsyncMock, MagicMock
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.users import router as users_router
    from database.session import get_db
    from auth.security import get_current_user

    app = FastAPI()
    app.include_router(users_router)

    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.role = "user"  # 非 admin
    mock_db = AsyncMock()

    def _override_user():
        return mock_user

    def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db

    client = TestClient(app)
    resp = client.get("/api/users")

    assert resp.status_code == 200
    assert resp.json()["code"] == 40003
```

- [x] **Step 2: 运行测试确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_user_management.py -v`
Expected: 新增用例 FAIL，报 `ModuleNotFoundError: No module named 'api.users'`；其余 10 个服务层用例仍 PASS。

- [x] **Step 3: 实现 schema 与 API**

新建 `apps/service/schemas/user_schema.py`（镜像 `schemas/document_schema.py` 的 `DocumentItem` 惯例）：

```python
"""用户管理相关 Pydantic 模型 —— 响应体定义。"""

from datetime import datetime

from pydantic import BaseModel


class UserItem(BaseModel):
    """用户列表/创建响应项（仅暴露 id/username/role/created_at，不含 password_hash）"""
    id: int
    username: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

新建 `apps/service/api/users.py`：

```python
"""用户管理接口 —— 列表、创建、删除（仅管理员）。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from schemas.user_schema import UserItem
from auth.security import get_current_user
from services.auth import list_users, create_user, delete_user
from utils.response import success, error

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


@router.get("")
async def list_users_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表（管理员权限）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看用户列表")
    users = await list_users(db)
    items = [UserItem.model_validate(u) for u in users]
    return success(data=items)


@router.post("")
async def create_user_endpoint(
    req: CreateUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建用户（管理员权限）——业务校验错误统一 40004"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可创建用户")
    try:
        user = await create_user(db, req.username, req.password, req.role)
    except ValueError as e:
        return error(code=40004, message=str(e))
    return success(data=UserItem.model_validate(user))


@router.delete("/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除用户（管理员权限）——目标不存在 40005，删除保护 ValueError 40004"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可删除用户")
    try:
        deleted = await delete_user(db, user_id, current_user.id)
    except ValueError as e:
        return error(code=40004, message=str(e))
    if deleted is None:
        return error(code=40005, message="用户不存在")
    return success(data={"success": True})
```

注册路由。`apps/service/api/__init__.py` 在 `from .tickets import router as tickets_router` 后追加：

```python
from .users import router as users_router
```

`apps/service/app/main.py` 两处修改：
1. import 行追加 `users_router`：

```python
from api import health_router, auth_router, chat_router, conversations_router, knowledge_router, config_router, enterprise_router, tickets_router, users_router
```

2. 在 `app.include_router(tickets_router)` 后追加：

```python
app.include_router(users_router)
```

- [x] **Step 4: 运行测试确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_user_management.py -v`
Expected: 11 个用例全部 PASS（含新增 API 权限 40003 用例）。

- [x] **Step 5: 快速验证路由已挂载（可选但推荐）**

Run: `cd apps/service && .venv/bin/python -c "from app.main import app; print([r.path for r in app.routes if 'users' in r.path])"`
Expected: 输出包含 `/api/users`、`/api/users/{user_id}`。

- [x] **Step 6: Commit**

```bash
git add apps/service/api/users.py apps/service/schemas/user_schema.py apps/service/api/__init__.py apps/service/app/main.py apps/service/tests/test_user_management.py
git commit -m "feat(service): 用户管理 API /api/users（GET/POST/DELETE，仅 admin）与路由注册"
```

---

### Task 3: 测试文件完整性校验（tasks 1.3）

**Files:**
- Test: `apps/service/tests/test_user_management.py`（只读校验，缺用例时补齐）

**Interfaces:**
- Consumes: Task 1 的服务层三函数 + Task 2 的 `api/users.py`；tasks.md 1.3 的 10 用例清单
- Produces: 通过本任务的完整测试文件（作为 tasks 1.3 的交付物），供 Task 7 全量回归

- [x] **Step 1: 对照 tasks.md 1.3 清单核对用例覆盖**

逐一确认下列 10 项在 `tests/test_user_management.py` 中均有对应测试函数（Task 1/2 已写，仅核对；若有缺失则补齐并复用相同 mock 模式）：

| tasks.md 1.3 要求 | 测试函数 |
|---|---|
| 列表 | `test_list_users_returns_all` |
| 创建成功 | `test_create_user_uses_default_role`（+ 变体 `test_create_user_with_admin_role`） |
| 重复用户名 | `test_create_user_duplicate_username_raises` |
| 密码过短 | `test_create_user_short_password_raises` |
| 非法角色 | `test_create_user_invalid_role_raises` |
| 删除成功 | `test_delete_user_success` |
| 删自己被拒 | `test_delete_user_self_raises` |
| 删 admin 被拒 | `test_delete_user_admin_raises` |
| 删不存在 | `test_delete_user_not_found_returns_none` |
| 非 admin 403 | `test_users_api_rejects_non_admin`（断言 `code == 40003`） |

- [x] **Step 2: 运行该文件全量确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_user_management.py -v`
Expected: 11 个用例全部 PASS（10 项要求全覆盖 + 1 个 admin 角色变体）。

- [x] **Step 3: Commit（仅当 Step 1 补齐了用例）**

```bash
git add apps/service/tests/test_user_management.py
git commit -m "test(service): 用户管理测试文件补全 tasks 1.3 全部 10 用例"
```

若 Step 1 未做任何改动，跳过本步（Step 2 通过即完成任务）。

---

### Task 4: 前端服务封装 services/users.ts（tasks 2.1）

**Files:**
- Create: `apps/web/services/users.ts`

**Interfaces:**
- Consumes: `fetchClient`（`@/lib/fetch`）；后端 `GET /api/users` / `POST /api/users` / `DELETE /api/users/{id}` 契约（Task 2）
- Produces（供 Task 5 使用）：
  - `export interface User { id: number; username: string; role: "user" | "admin"; created_at: string }`
  - `export async function getUsersApi(): Promise<ApiResponse<User[]>>`
  - `export async function createUserApi(username: string, password: string, role: string): Promise<ApiResponse<User>>`
  - `export async function deleteUserApi(id: number): Promise<ApiResponse<{ success: boolean }>>`

- [x] **Step 1: 写文件**

新建 `apps/web/services/users.ts`（镜像 `apps/web/services/tickets.ts` 的封装风格；`fetchClient` 的 `baseURL` 已含 `/api`，故路径写 `/users` 与后端 `prefix="/api/users"` 对应）：

```ts
import { fetchClient } from "@/lib/fetch"

// ========== 类型定义 ==========

export interface User {
  id: number
  username: string
  role: "user" | "admin"
  created_at: string
}

// ========== 用户管理接口 ==========

export async function getUsersApi() {
  return fetchClient.get<User[]>("/users")
}

export async function createUserApi(
  username: string,
  password: string,
  role: string
) {
  return fetchClient.post<User>("/users", { username, password, role })
}

export async function deleteUserApi(id: number) {
  return fetchClient.delete<{ success: boolean }>(`/users/${id}`)
}
```

- [x] **Step 2: typecheck 验证**

Run: `cd apps/web && pnpm typecheck`
Expected: 本文件 0 新增错误（`__tests__` 14 个基线存量错误忽略）。

- [x] **Step 3: Commit**

```bash
git add apps/web/services/users.ts
git commit -m "feat(web): 用户管理服务封装 services/users.ts（getUsersApi/createUserApi/deleteUserApi）"
```

---

### Task 5: useUserServices 状态 Hook（tasks 2.2）

**Files:**
- Create: `apps/web/app/users/useServices.ts`

**Interfaces:**
- Consumes: Task 4 的 `User` / `getUsersApi` / `createUserApi` / `deleteUserApi`
- Produces（供 Task 6 使用）：
  - `export default function useUserServices(): { listControl, users: User[], createControl, createUser(username, password, role), deleteControl, removeUser(id) }`
  - `createUser` / `removeUser` 内部执行对应请求后调用 `listControl.run()` 刷新列表；请求失败时向调用方抛错（错误 toast 由 fetchClient 拦截器负责）

- [x] **Step 1: 写文件**

新建 `apps/web/app/users/useServices.ts`（镜像 `apps/web/app/tickets/useServices.ts`：列表自动模式；create/delete 用 `manual` 控制）：

```ts
import { useRequest } from "ahooks";
import { useMemo } from "react";
import {
  getUsersApi,
  createUserApi,
  deleteUserApi,
  type User,
} from "@/services/users";

export default function useUserServices() {
  // 用户列表（自动模式：挂载首拉；create/delete 后手动重拉）
  const listControl = useRequest(getUsersApi, {});
  const { data: listData } = listControl;
  const users = useMemo(() => listData?.data ?? [], [listData]);

  // 创建用户
  const createControl = useRequest(
    async (username: string, password: string, role: string) =>
      createUserApi(username, password, role),
    { manual: true },
  );

  async function createUser(username: string, password: string, role: string) {
    await createControl.runAsync(username, password, role);
    await listControl.run();
  }

  // 删除用户
  const deleteControl = useRequest(deleteUserApi, { manual: true });

  async function removeUser(id: number) {
    await deleteControl.runAsync(id);
    await listControl.run();
  }

  return {
    listControl,
    users,
    createControl,
    createUser,
    deleteControl,
    removeUser,
  };
}
```

- [x] **Step 2: typecheck 验证**

Run: `cd apps/web && pnpm typecheck`
Expected: 本文件 0 新增错误。

- [x] **Step 3: Commit**

```bash
git add apps/web/app/users/useServices.ts
git commit -m "feat(web): users 页 useUserServices 状态 Hook（useRequest 列表/新增/删除）"
```

---

### Task 6: 页面去 mock 接入真实接口（tasks 2.3）

**Files:**
- Modify: `apps/web/app/users/page.tsx`（整文件替换）
- Modify: `apps/web/messages/zh-CN.json`、`apps/web/messages/en-US.json`（`users` 命名空间追加 2 个 key）

**Interfaces:**
- Consumes: Task 5 的 `useUserServices`（`users` / `createControl` / `createUser` / `removeUser`）；既有 `useTranslations("users")` / `useTranslations("common")` key；`tickets` 页的 `formatCreatedAt` 本地化格式惯例
- Produces: 本 change 的最终页面交付（真实列表 + 本地搜索过滤 + 受控新增表单 + admin 行删除置灰 + toast）

- [ ] **Step 1: 追加 i18n key（zh-CN）**

在 `apps/web/messages/zh-CN.json` 的 `users` 命名空间内，`"rolePlaceholder": "请选择角色"` 之后追加：

```json
  "addUserSuccess": "用户创建成功",
  "deleteUserSuccess": "用户已删除"
```

- [ ] **Step 2: 追加 i18n key（en-US）**

在 `apps/web/messages/en-US.json` 的 `users` 命名空间内追加对应英文键（先查看该文件 `users` 块结构，在 `rolePlaceholder` 之后插入，保持 JSON 合法）：

```json
  "addUserSuccess": "User created successfully",
  "deleteUserSuccess": "User deleted"
```

- [ ] **Step 3: 替换 page.tsx**

整文件替换 `apps/web/app/users/page.tsx` 为（核心改动：删除 `mockUsers`、接入 `useUserServices`、搜索过滤 `users`、新增受控表单、删除按钮 `user.role === "admin"` 置灰、`formatCreatedAt` 本地化、成功 toast 后刷新由 hook 内部 `listControl.run()` 完成）：

```tsx
"use client"

import { useCallback, useState } from "react"
import { useTranslations } from "next-intl"
import { Search, UserPlus, Trash2, Shield, User } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@intelligent-customer/ui/components/button"
import { Input } from "@intelligent-customer/ui/components/input"
import { Badge } from "@intelligent-customer/ui/components/badge"
import { Card, CardContent } from "@intelligent-customer/ui/components/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@intelligent-customer/ui/components/table"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@intelligent-customer/ui/components/dialog"
import { Label } from "@intelligent-customer/ui/components/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@intelligent-customer/ui/components/select"
import useUserServices from "./useServices"

function formatCreatedAt(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return dateStr
  }
}

export default function UsersPage() {
  const t = useTranslations("users")
  const tCommon = useTranslations("common")
  const { users, createControl, createUser, removeUser } = useUserServices()

  const [searchQuery, setSearchQuery] = useState("")
  const [addOpen, setAddOpen] = useState(false)
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState("user")

  const filteredUsers = users.filter(
    (user) =>
      !searchQuery ||
      user.username.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleAddUser = useCallback(async () => {
    try {
      await createUser(username, password, role)
      toast.success(t("addUserSuccess"))
      setAddOpen(false)
      setUsername("")
      setPassword("")
      setRole("user")
    } catch {
      // 错误已由 fetchClient 拦截器统一处理
    }
  }, [createUser, username, password, role, t])

  const handleDeleteUser = useCallback(
    async (id: number) => {
      try {
        await removeUser(id)
        toast.success(t("deleteUserSuccess"))
      } catch {
        // 错误已由 fetchClient 拦截器统一处理
      }
    },
    [removeUser, t]
  )

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("userCount", { count: users.length })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder={t("searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-60 pl-9"
            />
          </div>
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger
              render={
                <Button>
                  <UserPlus className="mr-2 size-4" />
                  {t("addUser")}
                </Button>
              }
            ></DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t("addUserTitle")}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>{t("colUsername")}</Label>
                  <Input
                    placeholder={t("usernamePlaceholder")}
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("colPassword")}</Label>
                  <Input
                    type="password"
                    placeholder={t("passwordPlaceholder")}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("colRole")}</Label>
                  <Select value={role} onValueChange={setRole}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="user">
                        {tCommon("roleUser")}
                      </SelectItem>
                      <SelectItem value="admin">
                        {tCommon("roleAdmin")}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  className="w-full"
                  disabled={createControl.loading}
                  onClick={handleAddUser}
                >
                  {t("addUserConfirm")}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* 用户表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>{t("colUsername")}</TableHead>
                <TableHead>{t("colRole")}</TableHead>
                <TableHead>{t("colCreatedAt")}</TableHead>
                <TableHead className="text-right">{t("colActions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="text-muted-foreground">
                    {user.id}
                  </TableCell>
                  <TableCell className="font-medium">{user.username}</TableCell>
                  <TableCell>
                    <Badge
                      variant={user.role === "admin" ? "default" : "secondary"}
                      className={
                        user.role === "admin"
                          ? "bg-primary/10 text-primary hover:bg-primary/10"
                          : ""
                      }
                    >
                      {user.role === "admin" ? (
                        <>
                          <Shield className="mr-1 size-3" />
                          {tCommon("roleAdmin")}
                        </>
                      ) : (
                        <>
                          <User className="mr-1 size-3" />
                          {tCommon("roleUser")}
                        </>
                      )}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatCreatedAt(user.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="text-destructive hover:text-destructive"
                      disabled={user.role === "admin"}
                      onClick={() => handleDeleteUser(user.id)}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: typecheck 验证**

Run: `cd apps/web && pnpm typecheck`
Expected: 本 change 涉及文件（`services/users.ts`、`app/users/useServices.ts`、`app/users/page.tsx`、`messages/*.json`）0 新增错误。

- [ ] **Step 5: Commit**

```bash
git add apps/web/app/users/page.tsx apps/web/messages/zh-CN.json apps/web/messages/en-US.json
git commit -m "feat(web): users 页接入真实接口去 mock（列表/搜索/受控新增表单/删除置灰/toast）"
```

---

### Task 7: 全量后端回归（tasks 3.1）

**Files:**
- 无源码改动（仅验证；如发现回归按 systematic-debugging 流程处理）

**Interfaces:**
- Consumes: Task 1–3 后端全部改动；既有测试基线（约 124 个既有用例）
- Produces: 全量 `pytest` 通过证据

- [ ] **Step 1: 运行全量 pytest**

Run: `cd apps/service && .venv/bin/python -m pytest tests/ -q`
Expected: 全部通过，总数 = 既有（约 124）+ 新增（test_user_management.py 11 个）；0 failed。特别确认 `test_auth_service.py`（user-auth）未回归。

- [ ] **Step 2: 若失败，进入 systematic-debugging 流程**

加载 systematic-debugging 技能定位根因，修复后重跑直至全绿；修复涉及源码时按当前 Comet 阶段完成确认与 commit（`git add` 相关文件 + `git commit -m "fix(service): ..."`）。

- [ ] **Step 3: Commit（仅当修复了回归）**

```bash
git add <修复涉及的文件>
git commit -m "fix(service): 修复全量回归问题"
```

若全绿无改动，跳过本步。

---

### Task 8: 前端 typecheck + 端到端实测（tasks 3.2）

**Files:**
- 无源码改动（仅验证）

**Interfaces:**
- Consumes: Task 4–6 前端全部改动 + 后端 Task 1–2 已启动的 API
- Produces: typecheck 证据 + 端到端实测证据（admin 真实列表 / 新增 / 删除 / 保护规则）

- [ ] **Step 1: 前端 typecheck**

Run: `cd apps/web && pnpm typecheck`
Expected: 本 change 涉及文件 0 新增错误（`__tests__` 14 个基线存量错误忽略）。

- [ ] **Step 2: 启动后端与前端**

Run:
```bash
cd apps/service && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
# 另一终端：
cd apps/web && pnpm dev
```

- [ ] **Step 3: 端到端实测清单（admin 登录）**

逐项实测并确认：
1. 打开 users 页 → 表格渲染**真实**用户列表（含 `admin`、既有 seed/注册用户），非 mock 数据；`created_at` 显示为本地时间格式。
2. 搜索框输入 → 本地过滤（按 `username.toLowerCase().includes(query)`），结果即时更新。
3. 新增用户：打开对话框，填写用户名/密码、角色选 `user` → 确认 → 成功 toast「用户创建成功」→ 对话框关闭 → 列表自动刷新出现新用户。
4. 新增重复用户名 → 收到 `40004` 错误 toast（fetchClient 拦截器统一提示），不崩溃。
5. 删除普通用户 → 成功 toast「用户已删除」→ 列表刷新移除该行。
6. 删除保护：**admin 行的删除按钮置灰 disabled**，无法点击；即便绕过前端调用 `DELETE /api/users/{admin_id}`，后端返回 `40004`（"不能删除管理员用户"）；调用 `DELETE /api/users/{自己的id}` 返回 `40004`（"不能删除当前登录用户"）；调用 `DELETE /api/users/{不存在的id}` 返回 `40005`。
7. 用非 admin 账号直接请求 `GET /api/users` → 返回 `{ code: 40003 }`。

- [ ] **Step 4: 无代码改动即完成**

端到端实测通过即本任务（以及 tasks.md 3.2）完成，无需 commit。若实测发现缺陷，按 systematic-debugging 定位并修复后重测，修复按当前 Comet 阶段完成确认与 commit。
