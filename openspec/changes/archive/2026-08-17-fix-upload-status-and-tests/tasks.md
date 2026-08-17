# Tasks: 修复上传状态不同步与测试 import 路径

## Task 1: 前端知识库上传状态轮询

- [x] 修改 `apps/web/app/knowledge/page.tsx`，新增文档状态轮询 effect：当文档列表存在 `processing` 状态时每 2s 刷新，全部完成或 60s 超时停止
- [x] 运行前端相关测试/类型检查确认无回归

## Task 2: 修正测试文件 import 路径

- [x] 修改 `apps/service/tests/test_auth_service.py`：`from app.services.auth` → `from services.auth`
- [x] 修改 `apps/service/tests/test_jwt_utils.py`：`from app.utils.jwt` → `from utils.jwt`
- [x] 修改 `apps/service/tests/test_password_utils.py`：`from app.utils.password` → `from utils.password`
- [x] 修改 `apps/service/tests/test_response_utils.py`：`from app.utils.response` → `from utils.response`
- [x] 修改 `apps/service/tests/test_user_model.py`：`from app.models.user` → `from schemas.user`
- [x] 修复 import 修正后暴露的循环导入：`configs/__init__.py` 包初始化时不再导入 provider/registry（无人使用其重导出，打破 provider → system_config → database.mysql 循环）
- [x] 运行 `pytest --collect-only` 确认无收集错误（97 collected），`pytest` 全量通过（97 passed）
