## Why

系统业务场景残留大量"电商平台"文案（Agent 提示词、工具模块、前端 i18n、测试文档、单测 fixture），与实际定位"**企业客户服务**"不一致。本次统一业务场景，消除电商残留，保证 Agent 工具、提示词、UI 文案口径一致。

## What Changes

- **A. Agent 提示词**（`apps/service/agent/prompts.py`）：角色设定、工具描述、决策规则、回答示例由电商改为企业场景。
- **B. 工具模块**（`apps/service/agent/tools/`）：
  - 删除 `order.py`（`order_query`/`business_action` 电商工具）
  - 新增 `enterprise.py`（`enterprise_query`/`ticket_submit`/`ticket_status` 企业工具）
  - 更新 `__init__.py` 工具注册
  - `knowledge.py`、`chat.py` 的 docstring 示例企业化
- **C. 前端 i18n**（`apps/web/messages/`）：检索占位、工具触发/输入/输出文案企业化。
- **E. 单测 fixture**（可选，低优先级）：`tests/test_message_converter.py`、`tests/test_ui_message_stream.py` 示例文本企业化。
- **D. rag 测试文档**（`~/Desktop/bg/rag-test-docs/`）：本次**不执行**，标注为 P3 补足 20 份时替换/补充企业场景文档。

## Capabilities

### New Capabilities
- `agent-tools`: Agent 企业工具能力（enterprise_query / ticket_submit / ticket_status），移除电商工具

### Modified Capabilities
无（现有 specs 未覆盖 Agent 工具实现细节）。

## Impact

- 后端：`apps/service/agent/`（prompts.py、tools/）
- 前端：`apps/web/messages/`（zh-CN.json、en-US.json）
- 测试：`apps/service/tests/`（fixture 文案）
- 无接口变更、无 schema 变更、无数据库变更
