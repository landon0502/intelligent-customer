---
comet_change: enterprise-biz-tickets
role: technical-design
canonical_spec: openspec
archived-with: 2026-08-17-enterprise-biz-tickets
status: final
---

# Design: 企业工具真实后端 + 工单落库与后台界面 + 安全默认值加固

## 1. 目标与范围

承接 OpenSpec change `enterprise-biz-tickets`（proposal/design/specs 为上游事实源）。本文档细化实现设计：架构分层、工具 async 化与上下文注入、工单号生成、接口契约、前端页面、安全加固、测试策略。

**范围**：P5 企业业务真实后端、P6 工单落库与后台界面、S1 安全默认值加固。
**非范围**：论文、`DB_PASSWORD`、看板/统计、工单分配流转、消息通知、分页。

## 2. 架构分层

复用现有服务模式，新增两个能力域：

```
API 层 (api/enterprise.py, api/tickets.py)
  → 服务层 (services/enterprise.py, services/ticket.py)  接受 db: AsyncSession 参数
  → ORM   (schemas/enterprise_biz.py, schemas/ticket.py)

工具层 (agent/tools/enterprise.py, chat.py)
  → async 工具内部 async_session_factory() 开独立会话 → 调用服务层
```

- **服务函数接受 `db` 参数**（对齐 `services/knowledge.py`），使单测可用 `AsyncMock` 注入，不依赖真实数据库。
- **工具独立会话**（对齐 `knowledge_base_query` 先例）：工具在 agent 流式调用内部触发，请求级 `get_db` 会话生命周期不可控，故工具用 `async_session_factory()` 自开会话，结束后关闭。

## 3. 关键决策

### D1. 工具统一 async（对齐 `knowledge_base_query`）

`enterprise_query` / `ticket_submit` / `ticket_status` / `transfer_human` 均改为 `async def` + `@tool`。`create_agent` 与 `agent.astream` 原生支持 async 工具，无需改动 agent 调用链。同步工具 + `asyncio.run()` 会在已有事件循环中抛错，排除。

### D2. 用户/会话上下文用 ContextVar 注入

**问题**：agent 是懒加载单例（`ComponentRegistry` 懒初始化一次），工具是模块级 `ALL_TOOLS`，无法为每次请求传入会话上下文。

**方案**：模块级 `ContextVar`。

- 新增 `agent/tools/context.py`：
  ```python
  _current_user_id: ContextVar[int | None] = ContextVar("user_id", default=None)
  _current_conversation_id: ContextVar[int | None] = ContextVar("conversation_id", default=None)
  # 提供 set/reset/get 辅助函数
  ```
- `api/chat.py` 的 `chat_stream`：调用 `agent.astream` 前 set（`current_user.id`、`req.conversation_id`），`finally` 中 reset。
- 工具内 `context.get("user_id")` 读取，缺失降级（写库时 user_id 为 NULL 或记日志，不阻断流程）。

**备选已排除**：每请求重建 agent（破坏懒加载单例与组件模型）；工具签名加参让 LLM 填（不可靠、污染契约）；LangChain `RunnableConfig`（与 `create_agent` 封装不直接兼容）。

### D3. 工单号 `TK-YYYYMMDD-XXXX`

`create_ticket()` 内生成：前缀 `TK-{YYYYMMDD}-`，`SELECT MAX(ticket_no) WHERE ticket_no LIKE 'TK-YYYYMMDD-%'` 得当日最大序号，+1 补齐 4 位（无则 0001）。`ticket_no` 列加唯一索引；插入冲突（IntegrityError）时重试一次。单实例部署下并发风险极低。

### D4. 状态枚举

`service_tickets.status` 用 `SAEnum("open","processing","closed")`，与 `documents.status`/`conversations.status` 模式一致。工具返回与 API 返回均用此枚举。

### D5. 转人工工单归属（哨兵编码）

`transfer_human` 创建的工单 `business_code = "HUMAN"`（哨兵编码），管理页可按「转人工」筛选；`content` 存转人工说明文本。备选（空值/复用业务编号）不如哨兵编码清晰可筛，排除。

### D6. 种子数据幂等初始化

`services/enterprise.py` 提供 `seed_enterprise_businesses()`：表内无记录（或缺失标准编号）时插入 3-5 条种子业务（企业开户/对公转账/电子发票申领等），已存在则跳过。`lifespan._seed_initial_data()` 中追加调用。

### D7. 注册点

- ORM：`database/models.py` + `schemas/__init__.py`（两处均为 `create_all` 模型来源）
- 路由：`api/__init__.py`（导出）+ `app/main.py`（`include_router`）

### D8. S1 安全默认值校验

`configs/config.py` 提供 `validate_security_defaults()`：比对生效值（`settings.JWT_SECRET == "change-me-in-production"` / `settings.ADMIN_PASSWORD == "admin123456"`），命中 `logger.warning`。`lifespan` 启动时（`logging.basicConfig` 之后）调用。不阻塞启动，仅告警。`.env` 改强随机 `JWT_SECRET` + 强 `ADMIN_PASSWORD`（`DB_PASSWORD` 不动）。

### D9. 接口契约

**enterprise（登录即可）**
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/enterprise/businesses` | 业务列表（按 code 排序） |
| GET | `/api/enterprise/businesses/{code}` | 单业务详情；未命中返回错误 |

**tickets**
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/tickets` | 创建工单（登录）；body：business_code / content（conversation_id 由 query 或 body 传入？——由前端调用时传 conversation_id，工具路径由 ContextVar 注入） |
| GET | `/api/tickets?status=open` | 工单列表 + 状态筛选（admin）；created_at DESC |
| GET | `/api/tickets/{no}` | 工单详情（admin） |
| PATCH | `/api/tickets/{no}/status` | 更新状态（admin）；body `{"status":"processing"|"closed"}` |

> POST /api/tickets 的 conversation_id 设计：body 可选字段 `conversation_id`（前端管理/对话侧创建时传）；工具路径（ticket_submit/transfer_human）由 ContextVar 注入，不走此接口。

**权限校验**：复用 `get_current_user`；admin 接口校验 `current_user.role == "admin"`（对齐 `api/knowledge.py`）。

### D10. 前端工单管理页

- `apps/web/services/tickets.ts`：`fetchClient` 封装（类型 + 4 个接口）
- `apps/web/app/tickets/useServices.ts`：loading/error/params 控制（对齐 `knowledge/useServices.ts`）
- `apps/web/app/tickets/page.tsx`：工单表（工单号/业务/用户/状态/时间）+ 顶部状态筛选（全部/open/processing/closed）+ 每行状态下拉更新；空态提示；toast 反馈
- `apps/web/config/menu.ts`：management 分组加「工单管理」（admin）+ `titleKeyMap` 加 `/tickets`
- i18n：`messages/zh-CN.json`、`en-US.json` 补 `layout.menuTickets` 与 tickets 页文案
- 无分页（数据规模小，YAGNI）

## 4. 数据模型

**`enterprise_biz`**
| 列 | 类型 | 说明 |
|---|---|---|
| id | Integer PK auto | |
| code | String(16) unique | 业务编号 B-001 |
| name | String(100) | 业务名称 |
| description | String(255) | 业务说明 |
| requirements | Text | 办理条件 |
| process | Text | 办理流程 |
| status | SAEnum(active/inactive) | 默认 active |
| created_at | DateTime | 默认 now(utc) |

**`service_tickets`**
| 列 | 类型 | 说明 |
|---|---|---|
| id | Integer PK auto | |
| ticket_no | String(32) unique | TK-YYYYMMDD-XXXX |
| user_id | Integer FK users.id | 可空，ContextVar 注入；删除置 NULL |
| conversation_id | Integer FK conversations.id | 可空 |
| business_code | String(16) | 业务编号或 HUMAN |
| content | Text | 办理说明/转人工说明 |
| status | SAEnum(open/processing/closed) | 默认 open |
| created_at | DateTime | |
| updated_at | DateTime | onupdate |

## 5. 测试策略

- **服务层**（`tests/test_enterprise_biz.py`、`tests/test_ticket_service.py`）：AsyncMock db session。
  - `enterprise_biz`：list 返回全量、get 命中/未命中
  - `ticket`：create 生成正确工单号格式、list 带/不带状态筛选、get_by_no 命中/未命中、update_status 合法流转/非法值
- **工具层**：patch `async_session_factory()`（返回 AsyncMock session）或 patch 服务函数。
  - `enterprise_query` 命中/未命中、`ticket_submit` 返回工单号、`ticket_status` 返回真实状态、`transfer_human` 生成 HUMAN 工单
- **端到端**：重启后端 → 建表/种子/无告警 → 实测对话（查 B-001 / 提交工单 / 转人工）+ 后台工单页。
- 前端不写单测，手工验证。

## 6. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 工具 async 化影响 agent 行为/LLM 调用 | 全量 pytest + 实测对话回归；工具 docstring 尽量不变 |
| ContextVar 跨请求泄漏 | finally reset；asyncio 任务级隔离 |
| 工单号并发重号 | ticket_no 唯一索引 + 冲突重试 |
| 新增表 create_all 不影响旧库 | 本次只有新增表，无结构变更 |
| `.env` 改动影响本机 | 仅改 JWT_SECRET/ADMIN_PASSWORD，改前备份可回滚 |

## 7. 回写 Spec Patch

- `specs/ticket-service/spec.md`：
  - 「工单列表接口」补充状态更新用 `PATCH /api/tickets/{no}/status`、body `{"status": ...}`
  - 「转人工生成工单」（agent-tools）补充 `business_code = "HUMAN"` 归属
  - 新增「转人工工单归属」场景：WHEN 转人工工单生成 THEN business_code 为 HUMAN
