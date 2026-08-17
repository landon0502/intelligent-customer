# Tasks: 修复上传状态不同步与测试 import 路径

## Task 1: 前端知识库上传状态轮询

- [x] 修改 `apps/web/app/knowledge/page.tsx`，新增文档状态轮询 effect：当文档列表存在 `processing` 状态时每 2s 刷新，全部完成或 60s 超时停止
- [x] 运行前端相关测试/类型检查确认无回归

## Task 2: 修正测试文件 import 路径

- [ ] 修改 `apps/service/tests/test_auth_service.py`：`from app.services.auth` → `from services.auth`
- [ ] 修改 `apps/service/tests/test_jwt_utils.py`：`from app.utils.jwt` → `from utils.jwt`
- [ ] 修改 `apps/service/tests/test_password_utils.py`：`from app.utils.password` → `from utils.password`
- [ ] 修改 `apps/service/tests/test_response_utils.py`：`from app.utils.response` → `from utils.response`
- [ ] 修改 `apps/service/tests/test_user_model.py`：`from app.models.user` → `from schemas.user`
- [ ] 运行 `pytest --collect-only` 确认无收集错误，`pytest` 全量通过
