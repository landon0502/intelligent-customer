# Tasks: 业务场景统一为企业客户服务

## Task 1: 提示词企业化

- [x] 修改 `apps/service/agent/prompts.py`（A1-A5）：角色、工具描述、决策规则、回答示例改为企业场景

## Task 2: 工具模块重构

- [x] 删除 `apps/service/agent/tools/order.py`（B1）
- [x] 新增 `apps/service/agent/tools/enterprise.py`：enterprise_query / ticket_submit / ticket_status 三工具（B3）
- [x] 更新 `apps/service/agent/tools/__init__.py`：注释与 ALL_TOOLS 注册（B2）

## Task 3: 工具文案企业化

- [x] 修改 `apps/service/agent/tools/knowledge.py` docstring（B4）
- [x] 修改 `apps/service/agent/tools/chat.py` clarify 示例（B5）

## Task 4: 前端 i18n 文案

- [x] 修改 `apps/web/messages/zh-CN.json` 检索占位与工具文案（C1/C2）
- [x] 修改 `apps/web/messages/en-US.json` 对应文案（C1/C2）

## Task 5: 单测 fixture（可选）

- [x] 修改 `apps/service/tests/test_message_converter.py`、`apps/service/tests/test_ui_message_stream.py` 示例文本企业化（E1）

## Task 6: 全量验证

- [x] 运行 `pytest` 全量通过
- [x] 后端 import 与工具注册正常、前端 typecheck 无新错误
