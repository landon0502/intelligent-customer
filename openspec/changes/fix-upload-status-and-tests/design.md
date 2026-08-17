# Design: 修复上传状态不同步与测试 import 路径

## P1 前端上传状态轮询

**现状**：`apps/web/app/knowledge/page.tsx` 的 `handleUpload` 上传成功后只调一次 `documentsControl.run()`。后端异步任务（`upload_document` → `asyncio.create_task`）在接口返回时通常仍处于 `processing`，之后状态变化不再刷新。

**方案**：利用 ahooks `useRequest` 的轮询能力。将 `useKnowledgeServices` 中的文档列表请求改为支持按需轮询：当 `documents` 中存在 `status === "processing"` 的文档时，每 2s 自动刷新一次；全部不再 `processing` 或超过 60s 超时后停止。

- 修改 `apps/web/app/knowledge/page.tsx`：新增一个基于 `documents` 状态的 effect，检测到 `processing` 时用 `setInterval` 每 2s 调 `documentsControl.run()`，无 `processing` 时清理定时器。
- 不做接口/后端改动（后端链路已验证正常）。

## P2 测试 import 路径修复

**现状**：5 个测试文件 import 使用 `app.*` 前缀，但重构后代码在顶层模块。

**方案**：逐文件修正 import：

| 文件 | 错误 import | 正确 import |
|---|---|---|
| `tests/test_auth_service.py` | `from app.services.auth import ...` | `from services.auth import ...` |
| `tests/test_jwt_utils.py` | `from app.utils.jwt import ...` | `from utils.jwt import ...` |
| `tests/test_password_utils.py` | `from app.utils.password import ...` | `from utils.password import ...` |
| `tests/test_response_utils.py` | `from app.utils.response import ...` | `from utils.response import ...` |
| `tests/test_user_model.py` | `from app.models.user import User` | `from schemas.user import User` |

不改测试断言逻辑，仅改 import。运行 `pytest --collect-only` 确认收集通过、`pytest` 全量通过。
