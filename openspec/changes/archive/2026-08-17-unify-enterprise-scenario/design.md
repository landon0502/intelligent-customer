# Design: 业务场景统一为企业客户服务（P1 内容一致性）

## 实现说明

### A. 提示词（`apps/service/agent/prompts.py`）
- A1：角色 "服务于一家电商平台的客户" → "服务于企业客户的智能客服"
- A2：知识工具描述 "业务规则、产品信息、退货政策、配送说明、会员权益" → "业务流程、办理条件、服务规范、常见问题"
- A3：工具列表 `order_query`/`business_action` → `enterprise_query`/`ticket_submit`/`ticket_status`
- A4：决策规则 "订单操作…order_query/business_action" → "企业业务…企业业务查询/工单工具"
- A5：回答示例 `商品/价格/手机/3999` → 企业业务示例（业务编号/业务名称/办理说明）

### B. 工具模块（`apps/service/agent/tools/`）
- B1：删除 `order.py`（含 `_MOCK_ORDERS`/`_RETURN_COUNTER`）
- B3：新增 `enterprise.py`，三个企业工具：
  - `enterprise_query(service_code)`：按业务编号/名称查询企业业务流程与办理说明
  - `ticket_submit(...)`：提交业务办理工单
  - `ticket_status(ticket_id)`：查询工单办理进度
- B2：`__init__.py` 更新注释与 `ALL_TOOLS`（移除 order_query/business_action，加入企业三工具）
- B4：`knowledge.py` docstring 知识库触发场景企业化
- B5：`chat.py` clarify 触发条件与示例企业化（工单/业务办理而非订单/退货）

### C. 前端 i18n（`apps/web/messages/zh-CN.json`、`en-US.json`）
- C1：检索占位 "退货需要多长时间？" → 企业问题示例
- C2：工具触发/输入/输出文案（order/return 相关键）→ 企业工具描述

### E. 单测 fixture（可选）
- `tests/test_message_converter.py`、`tests/test_ui_message_stream.py` 示例文本企业化（不改断言逻辑）

### D. rag 测试文档
- 本次不执行（P3 补足 20 份时替换为企业场景文档），proposal 已标注

## 验证
- `pytest` 全量通过（含 fixture 修改后）
- 后端 import 正常、前端 typecheck 无新错误
- Agent 工具注册正确（enterprise 三工具可用）
