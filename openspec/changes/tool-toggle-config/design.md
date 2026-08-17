# Design: 工具启停配置（后端配置 + Agent 动态绑定 + 接口 + tools 页对接）

## Context

Agent 固定绑定 `ALL_TOOLS`（6 个工具），`SYSTEM_PROMPT` 为静态字符串硬编码全部工具描述；前端 tools 页使用 `mockTools` 模拟开关，无真实接口。需要运营侧可启停工具并即时生效。

现有基础设施（可直接复用）：
- `system_configs` 表（key 唯一 + category 分类）+ `AsyncConfigProvider` Cache-Aside 按分类缓存
- `ComponentRegistry` 热更新（`refresh`/`refresh_category`），`registry.refresh("agent")` 用最新配置重建 Agent
- `create_customer_agent(agent_llm, tools=None, system_prompt=None)` 已支持注入工具集与系统提示词
- 配置 API 模式（`api/config.py`）：admin 校验 40003 + 写库 + 热更新

## Goals / Non-Goals

**Goals:**
- tools 分类配置存储（默认全启用）+ Agent 动态绑定启用工具 + 禁用工具提示词同步
- GET/PATCH 管理接口（admin），切换即时生效
- 兜底工具（transfer_human、clarify）不可禁用（后端硬校验 + 前端置灰）
- 前端 tools 页去 mock 对接真实接口

**Non-Goals:**
- 不改工具实现、不改 LLM/embedding 配置机制、不做按会话/用户粒度的工具权限
- 不做工具级参数配置（仅启停）

## Decisions

### D1. 配置存储：复用 `system_configs` 表 `tools` 分类
新增 `tools` 分类配置项（key=工具名，value=`enabled`/`disabled`），默认全部 `enabled`，并入 `init_default_configs` 与既有分类一致。读写走既有 `services/config.py` 通用配置服务（`get_configs_by_category`/`update_configs`），不新增表。

### D2. Agent 动态绑定：工厂读取 tools 配置 → 过滤 + 动态提示词
- `agent/factory.py`：新增 `build_system_prompt(enabled_tools)` 从静态工具描述表筛选启用工具生成动态 SYSTEM_PROMPT；`create_customer_agent` 接收过滤后的工具列表与动态提示词。
- `app/lifespan.py`：agent slot 的工厂闭包从 provider 读取 `tools` 分类配置，过滤 `ALL_TOOLS` 后调用 `create_customer_agent(agent_llm, tools=…, system_prompt=…)`。
- **关键约束**：禁用工具必须同步从 SYSTEM_PROMPT 移除对应描述，否则 LLM 调用未绑定工具报错。

### D3. 热更新：写库 → invalidate → refresh("agent")
`PATCH /api/tools/{name}`：admin 校验 → 校验兜底工具不可禁用/工具存在 → 写库 → `provider.invalidate("tools")` → `registry.refresh("agent")` 重建 Agent 即时生效。LLM 配置变更时对称额外 `refresh("agent")`（对齐现有 embedding→vectorstore 特殊处理模式），保证 Agent 持有的 LLM 引用同步更新。

### D4. 管理接口 `api/tools.py`（仅 admin）
- `GET /api/tools`：读 `tools` 分类配置 + `ALL_TOOLS` 元数据 → 返回工具名/描述/启用状态。
- `PATCH /api/tools/{name}`：body `{enabled: bool}` → 写库 + 热更新 → 返回新状态。
- 错误码：非 admin → 40003；禁用兜底工具 → 40004（明确提示）；未知工具名 → 40005。
- 注册 `api/__init__.py` + `app/main.py`。

### D5. 前端 tools 页对接（沿用 knowledge/users 模式）
- 新增 `apps/web/services/tools.ts`（fetchClient 封装 GET/PATCH）+ `app/tools/useServices.ts`（useRequest 加载 + 切换控制）。
- `page.tsx` 去 `mockTools`：工具展示元数据（triggerKey/inputKey/outputKey 等 i18n 键、implemented 标记）保留为前端静态映射，后端返回 name + enabled 状态合并渲染；开关切换调 PATCH 后刷新；兜底工具行开关置灰。
- i18n 补充错误提示（兜底不可禁用等）。前端不写单测，`pnpm typecheck` 验证。

## Risks / Trade-offs

- [禁用工具提示词不同步 → LLM 调用未绑定工具报错] → `build_system_prompt(enabled)` 单一来源动态生成，禁用即移除描述；测试覆盖"禁用后提示词不含该工具"。
- [agent slot 与 llm 分类解耦后 LLM 变更不刷新 agent] → services/config.py `_apply_config_changes` 对称特殊处理：llm 变更时额外 `refresh("agent")`。
- [缓存读到旧启停状态] → PATCH 后先 `invalidate("tools")` 再 refresh，refresh 内缓存 miss 重新读库。
- [兜底工具禁用事故级风险] → 后端服务层硬校验（防绕过）+ 前端置灰（UX），测试覆盖禁用拒绝。

## Migration Plan

无 schema/数据迁移（复用 `system_configs` 表，`init_default_configs` 幂等插入 `tools` 分类默认项）。
