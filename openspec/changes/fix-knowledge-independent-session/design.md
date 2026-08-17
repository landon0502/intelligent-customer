# Design: 修复异步文档处理的独立会话

## 方案

修改 `apps/service/services/knowledge.py`：

1. **`_process_document` 使用独立会话**：
   - 移除 `db: AsyncSession` 参数
   - 内部 `async with async_session_factory() as session:` 创建独立会话
   - 成功/失败两个分支的 `execute/commit` 均用独立 session

2. **`upload_document` 触发任务**：
   - `asyncio.create_task(_process_document(doc.id, file_path, ext, filename))` 不再传请求级 db
   - 用模块级 `_pending_tasks: set[asyncio.Task]` 保存任务引用，`add_done_callback(_pending_tasks.discard)` 自动清理，防止任务被 GC 回收

3. 导入 `from database.session import async_session_factory`。

## 验证

- 单元/集成：`pytest` 全量通过
- 端到端：上传文档确认 `processing → ready`（独立会话下状态更新成功）
- 代码审查确认：`_process_document` 不再引用任何请求级对象
