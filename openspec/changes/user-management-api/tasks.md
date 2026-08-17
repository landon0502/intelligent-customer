# Tasks: 用户管理真实接口（后端 users API + 前端去 mock）

## 1. 后端用户管理 API

- [x] 1.1 `services/auth.py` 新增 `list_users(db)` / `create_user(db, username, password, role)` / `delete_user(db, user_id, current_user_id)`（含删除保护：不能删自己/不能删 admin）
- [x] 1.2 新增 `api/users.py`：`GET /api/users`（admin）、`POST /api/users`（admin，username/password/role）、`DELETE /api/users/{id}`（admin），注册 `api/__init__.py` + `app/main.py`
- [x] 1.3 新增 `tests/test_user_management.py`（列表/创建成功/重复用户名/密码过短/非法角色/删除成功/删自己被拒/删 admin 被拒/删不存在/非 admin 403）

## 2. 前端 users 页接入

- [x] 2.1 新增 `apps/web/services/users.ts`（`User` 类型 + `getUsersApi` / `createUserApi` / `deleteUserApi`）
- [x] 2.2 新增 `apps/web/app/users/useServices.ts`（useRequest 列表加载 + 新增/删除控制）
- [ ] 2.3 改 `apps/web/app/users/page.tsx`：去除 `mockUsers`，真实列表渲染 + 搜索本地过滤 + 新增对话框（受控表单）+ 删除（admin 行按钮置灰）

## 3. 验证

- [ ] 3.1 全量 `pytest` 通过（`cd apps/service && .venv/bin/python -m pytest tests/ -q`）
- [ ] 3.2 `pnpm typecheck` 本 change 文件 0 新增错误 + 端到端实测（admin 登录 users 页真实列表 / 新增 / 删除 / 保护规则）
