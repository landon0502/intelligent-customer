# enterprise-biz Specification

## Purpose
企业业务目录的后端能力：维护企业可办理业务清单，提供面向登录用户的业务列表与单业务查询接口，供 Agent 工具与前端使用。
## Requirements
### Requirement: 企业业务数据模型
系统 SHALL 维护 `enterprise_biz` 数据表，每条业务包含业务编号（如 B-001）、名称、说明、办理条件、办理流程与状态，并在服务启动时初始化种子数据。

#### Scenario: 启动种子初始化
- **WHEN** 后端服务启动
- **THEN** 系统创建 `enterprise_biz` 表并初始化 3-5 条企业业务数据（如企业开户、对公转账、电子发票申领）

### Requirement: 业务列表接口
系统 SHALL 提供 `GET /api/enterprise/businesses` 接口，返回全部企业业务列表；仅需登录即可访问。

#### Scenario: 登录用户获取业务列表
- **WHEN** 已登录用户请求 `GET /api/enterprise/businesses`
- **THEN** 系统返回企业业务列表（含编号、名称、说明、办理条件、办理流程）

### Requirement: 单业务查询接口
系统 SHALL 提供 `GET /api/enterprise/businesses/{code}` 接口，按业务编号返回单条业务详情；仅需登录即可访问。

#### Scenario: 查询存在的业务
- **WHEN** 已登录用户请求 `GET /api/enterprise/businesses/B-001`
- **THEN** 系统返回 B-001 的业务详情

#### Scenario: 查询不存在的业务
- **WHEN** 已登录用户请求 `GET /api/enterprise/businesses/B-999`
- **THEN** 系统返回未找到该业务编号的错误

