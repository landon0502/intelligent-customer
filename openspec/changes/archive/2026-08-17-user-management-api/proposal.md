# Proposal: 用户管理真实接口（后端 users API + 前端去 mock）

## Why

前端用户管理页（`apps/web/app/users/page.tsx`）目前使用写死的 `mockUsers` 假数据（5 条），新增/删除按钮无真实逻辑；后端没有任何用户管理接口（`api/` 下仅 auth/chat/config/conversations/enterprise/health/knowledge/tickets）。本次补齐用户管理能力：后端新增用户管理 API，前端 users 页接入真实接口。

## What Changes

- **后端用户管理 API**（仅 admin）：
  - 新增 `api/users.py`：`GET /api/users`（用户列表）、`POST /api/users`（创建用户，可指定 role）、`DELETE /api/users/{id}`（删除用户）
  - `services/auth.py` 新增 `list_users()` / `create_user()` / `delete_user()`（删除规则：不能删除当前登录用户自己，不能删除 admin 角色用户）
  - 注册到 `api/__init__.py` + `app/main.py`
- **前端 users 页接入真实接口**：
  - 新增 `apps/web/services/users.ts`（fetchClient 封装）+ `app/users/useServices.ts`（数据加载控制）
  - `page.tsx` 去除 `mockUsers`，改为真实列表渲染 + 新增用户（用户名/密码/角色）+ 删除用户（admin 行删除按钮置灰）
  - 搜索仍为前端本地过滤（数据量小）

## Capabilities

### New Capabilities
- `user-management`: 用户管理能力（用户列表/创建/删除 API + 前端管理页接入，仅 admin 可用）

### Modified Capabilities
无（`user-auth` 的登录/注册/me 行为不变）。

## Impact

- 后端：`apps/service/api/users.py`（新）、`services/auth.py`（+list/create/delete）、`api/__init__.py`、`app/main.py`
- 前端：`apps/web/services/users.ts`（新）、`app/users/useServices.ts`（新）、`app/users/page.tsx`（改）
- 无 schema 变更（复用 `users` 表）、无破坏性变更
