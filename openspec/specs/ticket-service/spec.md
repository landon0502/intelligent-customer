# ticket-service Specification

## Purpose
工单生命周期的后端与前端能力：创建、查询、状态流转工单，并配套管理员工单管理界面，实现工单从提交到办理的闭环。
## Requirements
### Requirement: 工单数据模型
系统 SHALL 维护 `service_tickets` 数据表，每条工单包含工单号（`TK-YYYYMMDD-XXXX`）、提交用户、关联会话、业务编号、办理说明、状态（open/processing/closed）与创建/更新时间。

#### Scenario: 工单号格式
- **WHEN** 系统创建一张工单
- **THEN** 工单号遵循 `TK-YYYYMMDD-XXXX` 格式，其中 XXXX 为当日内自增序列

### Requirement: 创建工单接口
系统 SHALL 提供 `POST /api/tickets` 接口，登录用户可提交工单；工单落库后返回工单号。

#### Scenario: 登录用户提交工单
- **WHEN** 已登录用户通过 `POST /api/tickets` 提交业务办理申请
- **THEN** 系统创建工单并落库，返回 `TK-YYYYMMDD-XXXX` 工单号

### Requirement: 工单列表接口
系统 SHALL 提供 `GET /api/tickets` 接口，仅管理员可查看全部工单，支持按状态筛选与状态更新。

#### Scenario: 管理员查看工单列表
- **WHEN** 管理员请求 `GET /api/tickets`
- **THEN** 系统返回全部工单（工单号、业务、提交用户、状态、创建时间）

#### Scenario: 管理员更新工单状态
- **WHEN** 管理员通过 `PATCH /api/tickets/{no}/status` 请求体 `{"status": "processing"|"closed"}` 更新工单状态
- **THEN** 系统更新该工单状态并返回最新状态

#### Scenario: 非管理员访问列表
- **WHEN** 普通用户请求 `GET /api/tickets`
- **THEN** 系统返回无权限错误

### Requirement: 工单详情接口
系统 SHALL 提供 `GET /api/tickets/{no}` 接口，按工单号查询工单详情。

#### Scenario: 查询存在的工单
- **WHEN** 管理员请求 `GET /api/tickets/TK-…`
- **THEN** 系统返回该工单的完整详情

### Requirement: 工单管理界面
系统 SHALL 在 Web 端提供工单管理页面（`/tickets`），管理员可查看工单列表（工单号/业务/用户/状态/时间）并按状态筛选、更新状态；侧边栏"管理"分组 SHALL 包含"工单管理"菜单入口。

#### Scenario: 管理员访问工单管理页
- **WHEN** 管理员登录后进入 `/tickets`
- **THEN** 页面展示工单列表，支持按状态筛选与更新工单状态

#### Scenario: 菜单入口
- **WHEN** 管理员查看侧边栏"管理"分组
- **THEN** 分组中包含"工单管理"菜单项并可跳转至 `/tickets`

