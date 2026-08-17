# Design: 企业工具真实后端 + 工单落库与后台界面 + 安全默认值加固

## Context

动机见 proposal.md。当前约束：

- 三个工具（`enterprise_query`/`ticket_submit`/`ticket_status`）是同步 `@tool`，依赖写死的 `_MOCK_BUSINESS` 与模块级计数器；`transfer_human` 同步且不产生任何记录。
- Agent 是懒加载**单例**（`ComponentRegistry` 懒初始化一次），工具集是模块级 `ALL_TOOLS` —— 无法在每次请求时为工具传入会话上下文。
- `knowledge_base_query` 已是 **async `@tool`** 且内部用 `async_session_factory()` 开独立会话，是本次改造的直接先例。
- 建表统一在启动时 `Base.metadata.create_all`（lifespan），新增表自动创建，无需迁移脚本。

## Goals / Non-Goals

**Goals:**
- 工具从模拟数据切换到真实 DB，且保持异步工具模式与现有 agent 流式调用兼容。
- 工单全链路落库：对话提交/转人工 → `service_tickets` 表 → 后台管理页可见可操作。
- 安全默认值校验在不改变配置加载方式的前提下落地。

**Non-Goals:**
- 不做看板/统计、不做工单分配流转、不做邮件/短信通知。
- 不引入消息队列；工单号生成采用查库自增，不做分布式 ID。
- 不改 `DB_PASSWORD`，不跑数据库迁移（新表由 `create_all` 创建）。

## Decisions

### D1. 工具统一改 async，复用 `async_session_factory()` 独立会话
`enterprise_query`/`ticket_submit`/`ticket_status`/`transfer_human` 均改为 `async def` + `@tool`，内部用 `async_session_factory()` 开独立 DB 会话（与 `knowledge_base_query` 同模式）。`create_agent` 与 `agent.astream` 原生支持 async 工具，agent 调用链无需改动。

- 备选：保留同步工具、用 `asyncio.run()` 包一层 —— 会在已有事件循环中抛错，排除。
- 备选：请求级 `get_db` 会话 —— 工具触发于 agent 流式调用内部，生命周期不可控，排除（`knowledge_base_query` 已是独立会话先例）。

### D2. 用户/会话上下文用 ContextVar 注入
`transfer_human`（及 `ticket_submit` 落库的 `user_id` 归属）需要 `user_id`/`conversation_id`。由于 agent 是单例、工具是模块级函数，采用**模块级 `ContextVar`**：

- 在 `api/chat.py` 的 `chat_stream` 端点，调用 `agent.astream` 前 `set`，`finally` 中 `reset`。
- 工具内通过 `contextvar.get(default=None)` 读取；缺失时降级（不写 user_id 或记日志）。

- 备选：每次请求重建 agent 并闭包绑定上下文 —— 破坏懒加载单例与组件注册模型，且每次都要重建 LLM 绑定，排除。
- 备选：工具签名加 `user_id`/`conversation_id` 参数让 LLM 填 —— 不可靠且污染工具契约，排除。
- 备选：LangChain `RunnableConfig` 注入 —— 与 `create_agent` 的封装不直接兼容，需改造工厂，排除。

### D3. 工单号 `TK-YYYYMMDD-XXXX`：当日前缀查库自增
`create_ticket()` 生成工单号：前缀 `TK-{YYYYMMDD}-`，对 `service_tickets.ticket_no` 做 `LIKE 'TK-YYYYMMDD-%'` 查当日最大序号 +1 补齐 4 位。为防并发重号，`ticket_no` 列加唯一索引；冲突时重试一次。

- 备选：单独计数器表/Redis 序列 —— 对当前单实例场景过度设计，排除。

### D4. 状态字段用 `SAEnum`
`service_tickets.status` 用 `SAEnum("open","processing","closed")`（同 `documents.status`、`conversations.status` 模式）。前端筛选/更新与枚举一致。

### D5. 种子数据在 lifespan 幂等初始化
扩展 `lifespan._seed_initial_data()`：`enterprise_biz` 表为空（或缺失标准编号）时插入 3-5 条种子业务（复用 `_MOCK_BUSINESS` 文案扩展）。幂等 —— 已存在则跳过，重启不重复插入。

### D6. 路由/模型注册点补齐
新增 router 需同时注册 `api/__init__.py`（导出）与 `app/main.py`（`include_router`）；新增 ORM 需同时注册 `database/models.py` 与 `schemas/__init__.py`（两处都是 `create_all` 的模型来源）。

### D7. 前端菜单走声明式配置
工单管理页走现有模式：新增 `apps/web/services/tickets.ts` + `apps/web/app/tickets/useServices.ts` + `page.tsx`（参照 knowledge 页），菜单项加到 `config/menu.ts`（admin 角色）+ i18n（zh-CN/en-US）——侧边栏组件无需改动。

### D8. S1 校验放启动阶段
`config.py` 模块加载时 `logging` 尚未配置，直接 warning 格式不可控。方案：在 `config.py` 提供 `validate_security_defaults()` 函数，`lifespan` 启动时（`logging.basicConfig` 之后）调用，比对生效值是否等于弱默认值（`JWT_SECRET == "change-me-in-production"` / `ADMIN_PASSWORD == "admin123456"`），命中则 `logger.warning` 提示。`.env` 改为强随机 `JWT_SECRET` + 强 `ADMIN_PASSWORD`，加固后重启无告警即验证通过。

## Risks / Trade-offs

- [工具改 async 影响 agent 行为] → 全量 `pytest` + 实测对话（查业务/提交工单/转人工）回归；工具 docstring 保持稳定减少 LLM 调用偏差。
- [ContextVar 跨请求泄漏] → `finally` 中 `reset`；asyncio 任务级隔离，同任务内串行，泄漏面小。
- [工单号并发重号] → `ticket_no` 唯一索引 + 冲突重试一次；单实例部署下实际风险极低。
- [新表 `create_all` 不迁移旧库] → 本次只有新增表，无结构变更，无此风险。
- [`.env` 改动影响本机其他配置] → 仅改 `JWT_SECRET`/`ADMIN_PASSWORD` 两键，`DB_PASSWORD` 等不动；改前保留备份可回滚。

## Migration Plan

1. 部署：重启后端 → `create_all` 自动建 `enterprise_biz`/`service_tickets` → 种子初始化 → 启动无安全告警。
2. 回滚：还原代码 + 还原 `.env` 原值；新增表无副作用（后续可手动 drop）。

## Open Questions

无（设计层面的未知项均已在此解决；工单状态流转的权限细节已由 spec 约束）。
