## Why

两个已确认真实存在的 bug 影响系统可用性：

1. **P1 上传卡"处理中"**：知识库上传文档后，前端 [apps/web/app/knowledge/page.tsx](../../apps/web/app/knowledge/page.tsx) 上传成功只调用一次 `documentsControl.run()` 刷新列表，而此刻后端异步任务刚启动（`status=processing`）。页面无轮询，后端处理完成（`processing→ready`）后 UI 不会自动更新，用户一直看到"处理中"直到手动刷新。后端实测处理正常（txt 15s / PDF 5s 内 ready）。
2. **P2 pytest 收集报错**：后端 5 个测试文件 import 路径使用 `app.*` 前缀（`app.utils.*`、`app.services.auth`、`app.models.user`），但重构后实际代码是顶层模块（`utils/`、`services/`、`schemas/user.py`），导致 `pytest --collect-only` 5 个文件收集失败（`ModuleNotFoundError`）。

## What Changes

- **P1**：知识库页面在上传后对文档状态轮询，直至所有文档不再处于 `processing`（或超时），使 `ready`/`failed` 状态自动反映到 UI。
- **P2**：修正 5 个测试文件的 import 路径，与现有目录结构对齐。

## Capabilities

### New Capabilities

无（行为 bug 修复，不引入新 capability）。

### Modified Capabilities

无。两个修复均不改 spec 级行为契约（前端轮询是 UI 状态刷新机制，测试 import 是工具类修复），已在 `.openspec.yaml` 设置 `skip_specs: true`。

## Impact

- 前端：`apps/web/app/knowledge/page.tsx`（状态轮询）及可能的 `useServices.ts`
- 后端测试：`apps/service/tests/` 下 5 个文件（import 路径）
- 无接口变更、无 schema 变更、无架构调整
