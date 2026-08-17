# Proposal: 企业工具对接真实后端 + 工单落库与后台界面 + 安全默认值加固（D1 剩余 P5/P6/S1）

## Why

企业客户服务场景（D1）目前仍运行在模拟数据上：`enterprise_query` 依赖写死的 `_MOCK_BUSINESS`（仅 3 条业务），`ticket_submit`/`ticket_status` 不落库、状态固定返回"审核中"，`transfer_human` 不生成任何工单记录。后端没有企业业务与工单的真实接口，前端也没有工单管理界面；同时安全默认值（`JWT_SECRET`/`ADMIN_PASSWORD`）过弱。本次补齐 D1 剩余任务：对接真实后端（P5）、工单落库 + 后台界面（P6）、安全默认值加固（S1）。

## What Changes

- **P5 企业业务真实后端**：
  - 新增 `enterprise_biz` 表（ORM：`schemas/enterprise_biz.py`），注册到 `database/models.py` 与 `schemas/__init__.py`
  - 新增 `services/enterprise.py`：`list_businesses()` / `get_business_by_code()`，启动时种子初始化 3-5 条企业业务
  - 新增 `api/enterprise.py`：`GET /api/enterprise/businesses`、`GET /api/enterprise/businesses/{code}`（登录即可访问），注册到 `api/__init__.py` + `app/main.py`
  - `enterprise_query` 工具改 **async**，内部用 `async_session_factory()` 查 `enterprise_biz` 表，删除 `_MOCK_BUSINESS`
- **P6 工单落库 + 后台界面**：
  - 新增 `service_tickets` 表（ORM：`schemas/ticket.py`），注册 `database/models.py` 与 `schemas/__init__.py`
  - 新增 `services/ticket.py`：`create_ticket()`（生成 `TK-YYYYMMDD-XXXX` 工单号）/ `list_tickets()` / `get_ticket_by_no()` / `update_status()`
  - 新增 `api/tickets.py`：`POST /api/tickets`（创建，登录）、`GET /api/tickets`（列表，admin）、`GET /api/tickets/{no}`（查询，admin），注册 `api/__init__.py` + `app/main.py`
  - `ticket_submit`/`ticket_status` 改 **async** 落库查库；`transfer_human` 改 **async** 生成转人工工单（`user_id`/`conversation_id` 经 ContextVar 注入）
  - 新增 `apps/web/app/tickets/page.tsx` 工单管理页（列表 + 状态筛选/更新）；`config/menu.ts` 加"工单管理"菜单项（admin）+ i18n（zh-CN/en-US）
- **S1 安全默认值加固**：
  - `configs/config.py` 启动时校验弱默认值（`JWT_SECRET == "change-me-in-production"` / `ADMIN_PASSWORD == "admin123456"`）并 `logger.warning`
  - `.env` 的 `JWT_SECRET` 改强随机、`ADMIN_PASSWORD` 改强密码（`DB_PASSWORD` **不动**）
- **测试**：新增 `apps/service/tests/test_enterprise_biz.py`、`apps/service/tests/test_ticket_service.py`

## Capabilities

### New Capabilities
- `enterprise-biz`: 企业业务目录后端能力（`enterprise_biz` 表 + 业务查询 API + 启动种子数据）
- `ticket-service`: 工单生命周期后端与前端能力（`service_tickets` 表 + 工单 API + 工单管理页）

### Modified Capabilities
- `agent-tools`: 企业业务查询工具从模拟数据改为查库；工单工具落库并返回真实状态；转人工生成工单

## Impact

- 后端：`apps/service/schemas/`（新增 enterprise_biz.py、ticket.py）、`services/`（新增 enterprise.py、ticket.py）、`api/`（新增 enterprise.py、tickets.py，注册 `api/__init__.py` + `app/main.py`）、`agent/tools/`（enterprise.py、chat.py 改 async）、`database/models.py`、`schemas/__init__.py`、`app/lifespan.py`（企业业务种子初始化）、`configs/config.py`（弱默认值校验）
- 前端：`apps/web/app/tickets/page.tsx`（新增）、`apps/web/config/menu.ts`、`apps/web/messages/`（zh-CN.json、en-US.json）
- 配置：`apps/service/.env`
- 测试：`apps/service/tests/`（新增 2 个测试文件）
- 数据库：新增 `enterprise_biz`、`service_tickets` 两张表（启动 `create_all` 自动创建）
- 无破坏性变更
