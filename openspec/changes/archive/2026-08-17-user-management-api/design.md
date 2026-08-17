# Design: 用户管理真实接口（后端 users API + 前端去 mock）

## Context

动机见 proposal.md。当前约束：

- 后端无用户管理 API；`services/auth.py` 已有 `get_user_by_username`/`register_user`（接受 `db: AsyncSession` 首参，模式沿用）。
- 前端 users 页为纯 mock（`mockUsers` 写死，新增/删除无逻辑）；页面功能：列表、搜索（本地过滤）、新增（用户名/密码/角色）、删除（admin 行置灰）。
- `User` 模型：id/username/password_hash/role/created_at；`hash_password` 已在 `utils/password.py`。
- 权限模式：admin 校验沿用 `api/knowledge.py`（handler 内 `current_user.role != "admin"` → 40003）。
- 统一响应：`utils/response.success()/error()`，错误码 40003（仅管理员）/40004（非法值）/40005（不存在）。

## Goals / Non-Goals

**Goals:**
- 后端提供用户管理 API（列表/创建/删除），仅 admin 可用。
- 删除保护：不能删当前登录用户自己、不能删 admin 角色用户。
- 前端 users 页去 mock，接入真实接口。

**Non-Goals:**
- 不做角色编辑、不改注册/登录、不做密码重置、不做分页（数据量小）。

## Decisions

### D1. 服务层扩展 `services/auth.py`（接受 `db: AsyncSession` 首参）
新增 `list_users(db)` / `create_user(db, username, password, role)` / `delete_user(db, user_id, current_user_id)`。沿用 `register_user` 模式（hash_password + commit + refresh）。删除保护在服务层校验（`delete_user` 接收 `current_user_id` 与 `current_user.role`），API 层从 `current_user` 传入，保证规则单一来源。

- `list_users`：`select(User).order_by(User.id)`。
- `create_user`：用户名重复抛 `ValueError`；密码 <6 位抛 `ValueError`；role 仅 `user`/`admin` 合法（默认 user）。复用 `register_user` 的创建逻辑但支持指定 role。
- `delete_user`：目标不存在返回 `None`；目标 role == "admin" 抛 `ValueError("不能删除管理员用户")`；目标 id == current_user_id 抛 `ValueError("不能删除当前登录用户")`；否则删除并 commit，返回 `True`。

### D2. API 层 `api/users.py`（仅 admin）
- `GET /api/users`：admin 校验 → `list_users(db)` → 返回列表（id/username/role/created_at）。
- `POST /api/users`：admin 校验 → body `{username, password, role?}` → `create_user` → 成功返回用户信息；`ValueError` → 40004。
- `DELETE /api/users/{id}`：admin 校验 → `delete_user` → 返回 `None` 则 40005，`ValueError` 则 40004，成功返回 success。
- 注册 `api/__init__.py` + `app/main.py`（两处）。

### D3. 前端接入（沿用 knowledge/tickets 模式）
- 新增 `apps/web/services/users.ts`：`User` 类型 + `getUsersApi()` / `createUserApi(username, password, role)` / `deleteUserApi(id)`（fetchClient 封装）。
- 新增 `app/users/useServices.ts`：`useRequest` 自动模式加载列表 + create/delete 控制（沿用 tickets 的 refreshDeps/run 模式）。
- `page.tsx`：去 `mockUsers`，改真实列表 + 搜索本地过滤 + 新增对话框（受控表单）+ 删除（admin 行 `role === "admin"` 置灰）。
- 前端不写单测，`pnpm typecheck` 验证（本文件 0 新增错误；`__tests__` 存量错误与本 change 无关）。

### D4. 错误码映射
- 非 admin → 40003（对齐 knowledge）
- 创建非法值（重复用户名/密码过短/非法角色）→ 40004
- 删除保护（删自己/删 admin）→ 40004（业务规则拒绝，非"不存在"）
- 删除不存在 → 40005

## Risks / Trade-offs

- [删除保护规则实现位置双处（前端置灰 + 后端校验）] → 前端置灰仅 UX，后端服务层是权威校验（防绕过）；测试覆盖后端保护规则。
- [创建用户复用 register 逻辑 vs 独立 create_user] → 独立 create_user 支持指定 role，register 保持只建 user 不变（不破坏 user-auth 行为）。
- [`ValueError` 语义混杂（重复/密码/删除保护）] → API 层统一映射 40004 + 具体 message，前端 toast 展示。

## Migration Plan

无（复用既有 `users` 表，无 schema/数据迁移）。
