# Tasks: 修复异步文档处理的独立会话

## Task 1: 后端独立会话修复

- [x] 修改 `apps/service/services/knowledge.py`：`_process_document` 改用 `async_session_factory()` 独立会话，移除请求级 `db` 参数
- [x] `upload_document` 触发任务时不传 `db`，并用模块级集合保存 task 引用防 GC
- [x] 运行 `pytest` 确认全量通过（97 passed）
- [x] 端到端验证：上传 PDF 文档确认 `processing → ready` 状态流转正常（23 chunks，无 session closed）
