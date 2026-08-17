# agent-tools Specification

## Purpose
Agent 可用的企业业务工具能力，覆盖企业业务查询与工单办理场景。
## Requirements
### Requirement: 企业业务查询工具
Agent SHALL 提供 `enterprise_query` 工具，用于查询企业业务流程、办理条件、服务规范、常见问题。数据来源 SHALL 为 `enterprise_biz` 数据表（启动时种子初始化），不得使用写死的模拟数据。

#### Scenario: 企业业务查询
- **WHEN** 用户询问企业业务规则、办理条件或服务规范
- **THEN** Agent 调用 `enterprise_query` 返回对应业务的说明、办理条件与办理流程（数据来自 `enterprise_biz` 表）

#### Scenario: 企业业务查询未命中
- **WHEN** 用户询问的业务编号/名称不存在于 `enterprise_biz` 表
- **THEN** Agent 返回未找到提示，并列出当前可办理业务名称

### Requirement: 工单工具
Agent SHALL 提供 `ticket_submit` 和 `ticket_status` 工具，用于提交业务办理工单及查询办理进度。工单 SHALL 持久化到 `service_tickets` 数据表，状态以库中真实数据为准。

#### Scenario: 提交办理工单
- **WHEN** 用户要求办理企业业务或提交申请
- **THEN** Agent 调用 `ticket_submit` 创建工单并持久化到 `service_tickets` 表，返回工单号（格式 `TK-YYYYMMDD-XXXX`）与受理结果

#### Scenario: 查询工单进度
- **WHEN** 用户询问办理进度或工单状态
- **THEN** Agent 调用 `ticket_status` 从 `service_tickets` 表查询并返回该工单的真实当前状态（open/processing/closed）

### Requirement: 移除电商工具
Agent SHALL NOT 再提供电商场景的 `order_query`、`business_action` 工具。

#### Scenario: 不再触发电商工具
- **WHEN** Agent 识别到企业业务相关诉求
- **THEN** 不得调用已移除的 `order_query`/`business_action`

### Requirement: 转人工生成工单
Agent SHALL 提供 `transfer_human` 工具，当无法处理用户问题或用户要求人工服务时，生成一条转人工工单并持久化到 `service_tickets` 表，业务归属 `business_code` 标记为 `HUMAN`（哨兵编码）。

#### Scenario: 转人工生成工单
- **WHEN** 用户明确要求人工服务或 Agent 判断无法处理
- **THEN** Agent 调用 `transfer_human` 创建转人工工单（`business_code = "HUMAN"`）并返回"已转接人工，工单号 TK-…"

