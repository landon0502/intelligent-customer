# Tasks: 企业工具真实后端 + 工单落库与后台界面 + 安全默认值加固

## 1. P5 企业业务真实后端

- [x] 1.1 新增 `apps/service/schemas/enterprise_biz.py`（`enterprise_biz` 表：id/code/name/description/requirements/process/status/created_at），注册到 `database/models.py` 与 `schemas/__init__.py`
- [x] 1.2 新增 `apps/service/services/enterprise.py`：`list_businesses()` / `get_business_by_code()` + 幂等种子数据函数
- [x] 1.3 新增 `apps/service/api/enterprise.py`：`GET /api/enterprise/businesses`、`GET /api/enterprise/businesses/{code}`（登录即可访问），注册 `api/__init__.py` + `app/main.py`
- [x] 1.4 扩展 `lifespan._seed_initial_data()`：启动时幂等初始化企业业务种子数据（3-5 条）

## 2. P6 工单落库与 API

- [x] 2.1 新增 `apps/service/schemas/ticket.py`（`service_tickets` 表：id/ticket_no(唯一)/user_id/conversation_id/business_code/content/status(open·processing·closed)/created_at/updated_at），注册 `database/models.py` 与 `schemas/__init__.py`
- [x] 2.2 新增 `apps/service/services/ticket.py`：`create_ticket()`（生成 `TK-YYYYMMDD-XXXX`）/ `list_tickets(status?)` / `get_ticket_by_no()` / `update_status()`
- [x] 2.3 新增 `apps/service/api/tickets.py`：`POST /api/tickets`（创建，登录）、`GET /api/tickets`（列表 + 状态筛选，admin）、`GET /api/tickets/{no}`（admin）、状态更新接口，注册 `api/__init__.py` + `app/main.py`

## 3. P5/P6 工具 async 化

- [x] 3.1 `apps/service/agent/tools/enterprise.py`：`enterprise_query` 改 async 查 `enterprise_biz` 表（删除 `_MOCK_BUSINESS`）；`ticket_submit`/`ticket_status` 改 async 落库/查库
- [x] 3.2 `apps/service/agent/tools/chat.py`：`transfer_human` 改 async 生成转人工工单
- [x] 3.3 新增 ContextVar（`user_id`/`conversation_id`）：`api/chat.py` 的 `chat_stream` 中 set/reset；工具内读取（缺失降级）

## 4. P6 前端工单管理页

- [x] 4.1 新增 `apps/web/services/tickets.ts`（fetchClient 封装类型 + 接口）
- [x] 4.2 新增 `apps/web/app/tickets/useServices.ts` + `page.tsx`（工单列表 + 状态筛选/更新）
- [x] 4.3 `apps/web/config/menu.ts` 加"工单管理"菜单项（admin）与 `titleKeyMap`；i18n `messages/zh-CN.json`、`en-US.json` 补 `layout.menuTickets` 与 tickets 页文案

## 5. S1 安全默认值加固

- [x] 5.1 `configs/config.py` 提供 `validate_security_defaults()`，`lifespan` 启动时校验弱默认值并 `logger.warning`
- [ ] 5.2 `.env`：`JWT_SECRET` 改强随机、`ADMIN_PASSWORD` 改强密码（`DB_PASSWORD` 不动）

## 6. 测试

- [ ] 6.1 新增 `apps/service/tests/test_enterprise_biz.py`（业务查询命中/未命中）
- [ ] 6.2 新增 `apps/service/tests/test_ticket_service.py`（创建/查询/状态流转）
- [ ] 6.3 全量 `pytest` 通过（原有用例 + 新增）

## 7. 端到端验证

- [ ] 7.1 重启后端：自动建表（enterprise_biz / service_tickets）+ 种子初始化 + 无安全告警
- [ ] 7.2 实测对话：查 B-001 → 查库返回；提交工单 → 落库返回工单号；转人工 → 生成工单；后台工单页可见、可筛选/更新状态
