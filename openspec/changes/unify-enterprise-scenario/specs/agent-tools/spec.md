# agent-tools Specification

## Purpose
Agent 可用的企业业务工具能力，覆盖企业业务查询与工单办理场景。

## ADDED Requirements

### Requirement: 企业业务查询工具
Agent SHALL 提供 `enterprise_query` 工具，用于查询企业业务流程、办理条件、服务规范、常见问题。

#### Scenario: 企业业务查询
- **WHEN** 用户询问企业业务规则、办理条件或服务规范
- **THEN** Agent 调用 `enterprise_query` 返回对应业务说明

### Requirement: 工单工具
Agent SHALL 提供 `ticket_submit` 和 `ticket_status` 工具，用于提交业务办理工单及查询办理进度。

#### Scenario: 提交办理工单
- **WHEN** 用户要求办理企业业务或提交申请
- **THEN** Agent 调用 `ticket_submit` 提交工单并返回受理结果

#### Scenario: 查询工单进度
- **WHEN** 用户询问办理进度或工单状态
- **THEN** Agent 调用 `ticket_status` 返回工单当前状态

### Requirement: 移除电商工具
Agent SHALL NOT 再提供电商场景的 `order_query`、`business_action` 工具。

#### Scenario: 不再触发电商工具
- **WHEN** Agent 识别到企业业务相关诉求
- **THEN** 不得调用已移除的 `order_query`/`business_action`
