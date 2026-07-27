# Task 3-6 实施报告

## 状态: DONE

## Task 3: 创建数据库会话和用户模型

**提交哈希:** 3d900c0

**变更文件:**
- Create: `apps/service/app/db/__init__.py`
- Create: `apps/service/app/db/session.py`
- Create: `apps/service/app/models/__init__.py`
- Create: `apps/service/app/models/user.py`
- Create: `apps/service/tests/test_user_model.py`

**测试结果:** 2 passed

**偏差说明:** 计划中 `User` 模型的 `role` 字段使用 `mapped_column(default="user")`，但 SQLAlchemy 2.0 的 `mapped_column` 的 `default` 参数不会在 Python 对象实例化时生效（仅作为数据库端 server_default）。添加了 `__init__` 方法通过 `kwargs.setdefault("role", "user")` 实现 Python 端默认值，同时保留 `server_default="user"` 确保数据库端也有默认值。

---

## Task 4: 创建 JWT 和密码工具模块

**提交哈希:** 6ce28cb

**变更文件:**
- Create: `apps/service/app/utils/jwt.py`
- Create: `apps/service/app/utils/password.py`
- Create: `apps/service/tests/test_jwt_utils.py`
- Create: `apps/service/tests/test_password_utils.py`
- Modify: `apps/service/pyproject.toml` (添加 `bcrypt<4.1` 约束)
- Modify: `apps/service/uv.lock`

**测试结果:** 4 passed

**偏差说明:**
1. PyJWT 2.8+ 要求 JWT `sub` claim 必须为字符串类型，但计划中 `create_token` 传入整数 `user_id`。在 `verify_token` 的 `jwt.decode` 调用中添加 `options={"verify_sub": False}` 跳过 sub 类型校验，保持 `sub` 为整数以兼容 `security.py` 中 `db.get(User, user_id)` 的用法。
2. passlib 1.7.4 与 bcrypt 5.x 不兼容（bcrypt 移除了 `__about__` 模块且不再自动截断 72 字节密码）。在 pyproject.toml 中添加 `bcrypt<4.1` 约束，降级到 bcrypt 4.0.1。

---

## Task 5: 创建认证服务和安全依赖

**提交哈希:** ec9e2de

**变更文件:**
- Create: `apps/service/app/services/__init__.py`
- Create: `apps/service/app/services/auth.py`
- Create: `apps/service/app/core/security.py`
- Create: `apps/service/tests/test_auth_service.py`

**测试结果:** 4 passed

**偏差说明:** 计划中使用 `@pytest.mark.asyncio`，但项目未安装 pytest-asyncio。改用已安装的 anyio 插件的 `@pytest.mark.anyio`。同时将 `db.add` mock 从 AsyncMock 改为 MagicMock（SQLAlchemy `Session.add()` 是同步方法）。

---

## Task 6: 创建认证路由并集成到主应用

**提交哈希:** 9b99fd6

**变更文件:**
- Create: `apps/service/app/routers/auth.py`
- Modify: `apps/service/app/routers/__init__.py`
- Modify: `apps/service/app/main.py`

**测试结果:** 路由集成测试需要数据库连接，未单独运行。全部后端单元测试 13 passed。

---

## 全部后端单元测试结果

```
tests/test_response_utils.py::test_success_returns_code_zero PASSED
tests/test_response_utils.py::test_success_with_custom_message PASSED
tests/test_response_utils.py::test_error_returns_given_code PASSED
tests/test_user_model.py::test_user_model_fields PASSED
tests/test_user_model.py::test_user_model_default_role PASSED
tests/test_jwt_utils.py::test_create_and_verify_token PASSED
tests/test_jwt_utils.py::test_verify_invalid_token_raises PASSED
tests/test_password_utils.py::test_hash_and_verify_password PASSED
tests/test_password_utils.py::test_verify_wrong_password PASSED
tests/test_auth_service.py::test_register_user_creates_new_user[asyncio] PASSED
tests/test_auth_service.py::test_authenticate_user_with_correct_password[asyncio] PASSED
tests/test_auth_service.py::test_authenticate_user_with_wrong_password_returns_none[asyncio] PASSED
tests/test_auth_service.py::test_authenticate_user_not_found_returns_none[asyncio] PASSED

13 passed in 2.44s
```

## 风险信号

无阻塞性风险。以下为已解决的技术偏差：
- SQLAlchemy `mapped_column(default=...)` Python 端默认值问题：已通过 `__init__` 修复
- PyJWT `sub` 类型校验：已通过 `options={"verify_sub": False}` 修复
- passlib/bcrypt 版本兼容性：已通过 `bcrypt<4.1` 约束修复
- pytest-asyncio 未安装：已改用 anyio
