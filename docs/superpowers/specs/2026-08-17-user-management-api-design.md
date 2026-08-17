---
comet_change: user-management-api
role: technical-design
canonical_spec: openspec
archived-with: 2026-08-17-user-management-api
status: final
---

# Design: 用户管理真实接口（后端 users API + 前端去 mock）

## 1. 目标与范围

承接 OpenSpec change `user-management-api`。本文档细化实现设计：服务层函数、API 契约、删除保护规则、前端接入、测试策略。

**范围**：后端用户管理 API（列表/创建/删除）+ 前端 users 页去 mock。
**非范围**：角色编辑、注册/登录鉴权改动、密码重置、分页。

## 2. 架构分层

```
服务层 (services/auth.py 扩展，接受 db: AsyncSession 首参)
  → API 层 (api/users.py，仅 admin，校验对齐 api/knowledge.py)
  → 前端 (services/users.ts + app/users/useServices.ts + app/users/page.tsx)
```

## 3. 关键决策

### D1. 服务层函数（`services/auth.py`）

- `async def list_users(db) -> list[User]`：`select(User).order_by(User.id)`。
- `async def create_user(db, username, password, role="user") -> User`：
  - username 重复 → `ValueError("用户名已存在")`
  - 密码 <6 位 → `ValueError("密码至少 6 位")`
  - role 不在 `{"user","admin"}` → `ValueError("非法角色")`
  - `hash_password` + commit + refresh（沿用 register_user 模式）
- `async def delete_user(db, user_id, current_user_id) -> bool | None`：
  - 目标不存在 → `None`
  - 目标 role == "admin" → `ValueError("不能删除管理员用户")`
  - 目标 id == current_user_id → `ValueError("不能删除当前登录用户")`
  - 否则删除 + commit，返回 `True`

**删除保护在服务层权威校验**（API 层从 `current_user` 传 id，前端置灰仅 UX 防误触，服务层防绕过）。

### D2. API 层（`api/users.py`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/users` | 用户列表（admin），返回 id/username/role/created_at |
| POST | `/api/users` | 创建用户（admin），body `{username, password, role?}`；ValueError → 40004 |
| DELETE | `/api/users/{id}` | 删除用户（admin）；None → 40005，ValueError → 40004 |

- admin 校验：handler 内 `current_user.role != "admin"` → `error(code=40003, ...)`（对齐 api/knowledge.py）
- 注册：`api/__init__.py` 导出 + `app/main.py` `include_router`

### D3. 错误码映射

| 场景 | 错误码 |
|---|---|
| 非 admin | 40003 |
| 重复用户名 / 密码过短 / 非法角色 / 删除保护 | 40004（+ 具体 message） |
| 删除不存在的用户 | 40005 |

### D4. 前端接入

- `apps/web/services/users.ts`：`User` 类型（id/username/role/created_at）+ `getUsersApi()` / `createUserApi(username, password, role)` / `deleteUserApi(id)`（fetchClient 封装）
- `app/users/useServices.ts`：`useRequest` 自动模式加载列表（沿用 tickets 的 refreshDeps/run 模式）+ create/delete 控制
- `page.tsx`：
  - 去 `mockUsers`，真实列表渲染
  - 搜索本地过滤（`username.toLowerCase().includes(query)`）
  - 新增对话框受控表单（用户名/密码/角色 Select），成功 toast + 刷新列表
  - 删除按钮：`role === "admin"` 行置灰 disabled；删除成功 toast + 刷新
  - created_at 前端格式化显示（UTC → 本地）
- 前端不写单测，`pnpm typecheck` 验证（本文件 0 新增错误；`__tests__` 存量错误与 change 无关）

## 4. 测试策略

- `apps/service/tests/test_user_management.py`（`@pytest.mark.anyio` + AsyncMock db，对齐 test_auth_service.py）：
  - `list_users` 返回全量
  - `create_user` 成功（role 默认 user）/ 指定 admin / 重复用户名 ValueError / 密码过短 ValueError / 非法角色 ValueError
  - `delete_user` 成功 True / 目标不存在 None / 删 admin ValueError / 删自己 ValueError
  - API 权限：非 admin 访问 40003（可经 TestClient + mock 依赖，或服务层校验覆盖）
- 全量 `pytest`（既有 124 + 新增）通过；前端 typecheck 0 新增错误；端到端实测。

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 删除保护被绕过 | 服务层权威校验 + 测试覆盖四分支 |
| create_user 与 register 逻辑重复 | 独立实现但复用 hash_password；register 行为不变（user-auth 不回归） |
| ValueError 语义混杂 | API 层统一映射 40004 + message，前端 toast 区分 |
| 前端 mock 残留 | page.tsx 删除 mockUsers；E2E 实测真实列表 |
