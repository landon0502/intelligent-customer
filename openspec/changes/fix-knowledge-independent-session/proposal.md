## Why

后端知识库上传的异步文档处理存在 **session closed 风险**：[services/knowledge.py](../../apps/service/services/knowledge.py) 的 `upload_document` 用 `asyncio.create_task(_process_document(db, ...))` 把 **FastAPI 请求级 db 会话**传给后台任务。请求结束后 `get_db` 的 `async with` 退出，会话即关闭；大文档处理耗时长，后台任务再用该会话执行 `db.execute/commit` 会抛 `session closed`，导致文档状态卡在 `processing` 或报错。小文档实测能过仅因处理发生在请求生命周期内。

## What Changes

- `_process_document` 不再接收请求级 `db`，改为内部用 `async_session_factory()` 创建**独立会话**更新文档状态。
- `upload_document` 触发任务时不再传 `db`。
- 顺带修复：`asyncio.create_task` 返回的 task 若不保存引用可能被 GC 回收，改为模块级集合保存引用（done callback 自动清理）。

## Capabilities

### New Capabilities

无（行为 bug 修复，不引入新 capability）。

### Modified Capabilities

无。已在 `.openspec.yaml` 设置 `skip_specs: true`。

## Impact

- 后端：`apps/service/services/knowledge.py`（`_process_document` / `upload_document`）
- 无接口变更、无 schema 变更
