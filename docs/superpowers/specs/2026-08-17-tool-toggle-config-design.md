---
comet_change: tool-toggle-config
role: technical-design
canonical_spec: openspec
archived-with: 2026-08-17-tool-toggle-config
status: final
---

# Design: 工具启停配置（后端配置 + Agent 动态绑定 + 接口 + tools 页对接）

## 1. 目标与范围

承接 OpenSpec change `tool-toggle-config`。本文档细化实现设计：tools 分类配置存储、Agent 动态绑定与动态提示词、热更新时序、GET/PATCH 接口契约、前端 tools 页去 mock、测试策略。

**范围**：后端 `system_configs` 表 `tools` 分类配置（默认全启用）+ Agent 动态绑定启用工具 + 禁用工具提示词同步 + GET/PATCH 管理接口（仅 admin）+ 前端 tools 页对接真实接口。
**非范围**：不改工具实现、不改 LLM/embedding 配置机制、不做按会话/用户粒度的工具权限、不做工具级参数配置（仅启停）、不做工具排序/分组。

## 2. 架构分层

```
数据层   system_configs 表（SystemConfig ORM，key 唯一 + category 分类）
  ↕ 读写
服务层   services/config.py（init_default_configs/update_configs）
         services/tools.py（list_tool_states / update_tool_state，新增）
  ↕ 读取
配置层   AsyncConfigProvider（Cache-Aside 按分类缓存 get_category/invalidate）
  ↕ 组件重建
注册表   ComponentRegistry（refresh/refresh_category，事务性替换，失败保留旧实例）
  ↕
Agent    agent/factory.py（filter_tools + create_customer_agent 注入）
         agent/prompts.py（TOOL_DESCRIPTIONS + build_system_prompt 动态提示词）
         app/lifespan.py（agent slot 绑定 tools 分类）
  ↕
接口层   api/tools.py（GET /api/tools + PATCH /api/tools/{name}，仅 admin）
  ↕
前端     services/tools.ts + app/tools/useServices.ts + app/tools/page.tsx（去 mock）
```

## 3. 关键决策

### D1. 配置存储：`system_configs` 表 `tools` 分类

- `services/config.py` 的 `DEFAULT_CONFIGS` 新增 6 项，key 格式 `tools.<工具名>`，value 固定 `enabled`，category 固定 `tools`，description 为中文说明：

| key | value | description |
|-----|-------|-------------|
| `tools.knowledge_base_query` | `enabled` | 知识库问答工具是否启用 |
| `tools.enterprise_query` | `enabled` | 企业业务查询工具是否启用 |
| `tools.ticket_submit` | `enabled` | 工单提交工具是否启用 |
| `tools.ticket_status` | `enabled` | 工单状态查询工具是否启用 |
| `tools.transfer_human` | `enabled` | 转人工工具是否启用（兜底，不可禁用） |
| `tools.clarify` | `enabled` | 追问澄清工具是否启用（兜底，不可禁用） |

- `init_default_configs` 已是"仅插入缺失键、不覆盖已有值"的幂等实现，无需改动。
- 读取经 `AsyncConfigProvider.get_category("tools")`，返回 `{key: value}`（key 含 `tools.` 前缀）；写入经 `services/config.py` 通用逻辑或 `services/tools.py` 内联写库。

**注意（key 前缀归一化）**：`get_category("tools")` 返回的 key 是 `tools.<name>`，而 Agent/接口层按工具名 `<name>` 引用。所有消费点必须统一归一化：`{k.split(".", 1)[-1]: v for k, v in category.items()}`。

### D2. Agent 动态绑定：过滤工具集 + 动态系统提示词

**`agent/prompts.py` 拆解**（单一来源原则）：

- 新增 `TOOL_DESCRIPTIONS: dict[str, str]`——name → 描述文本，**沿用现有 `SYSTEM_PROMPT` 中 1-6 工具的原文**：
  - `knowledge_base_query` → "当用户询问业务流程、办理条件、服务规范、常见问题等知识性问题时使用"
  - `enterprise_query` → "当用户提供业务编号或询问企业业务流程、办理条件时使用"
  - `ticket_submit` → "当用户要求办理企业业务、提交申请时使用"
  - `ticket_status` → "当用户询问办理进度、工单状态时使用"
  - `transfer_human` → "当你判断无法处理或需要人工介入时使用"
  - `clarify` → "当用户意图不明确，需要追问澄清时使用"
- 抽取固定提示词段 `PROMPT_FIXED`（`## 决策规则` / `## 回答规范` / `## 回答格式要求` 原文不动）。
- 新增 `build_system_prompt(enabled_names: list[str]) -> str`：动态生成 `## 可用工具及适用场景`（按启用工具**重新编号**） + `PROMPT_FIXED`。
- 保留 `SYSTEM_PROMPT = build_system_prompt(ALL_TOOL_NAMES)` 作为兼容默认（现有调用方不传 system_prompt 时行为不变）。

**`agent/factory.py`**：

- 新增 `filter_tools(tool_states: dict[str, str]) -> list`：`[t for t in ALL_TOOLS if tool_states.get(t.name, "enabled") == "enabled"]`（`t.name` 为 StructuredTool 的工具名）。
- `create_customer_agent(agent_llm, tools=None, system_prompt=None)` 保持不变——调用方注入过滤后的 `tools` 与动态 `system_prompt`。

**`agent/tools/__init__.py`**：

- 新增 `ALL_TOOL_NAMES = [t.name for t in ALL_TOOLS]`（供接口/服务层校验工具存在性）。

### D3. lifespan 接线：agent slot 绑定 tools 分类

`app/lifespan.py` 的 `_agent_factory` 改为闭包：

```python
def _agent_factory(config: dict):
    agent_llm = registry.get("agent_llm")
    # config 是 tools 分类配置（key 含 "tools." 前缀）
    states = {k.split(".", 1)[-1]: v for k, v in config.items()}
    enabled = filter_tools(states)
    system_prompt = build_system_prompt([t.name for t in enabled])
    return create_customer_agent(agent_llm, tools=enabled, system_prompt=system_prompt)

registry.register("agent", _agent_factory, "tools")  # config_category: "llm" → "tools"
```

**LLM 变更对称刷新**：`_apply_config_changes` 增加 `llm` 分类变更时额外 `refresh("agent")`（对齐现有 `embedding` → 额外 refresh `vectorstore` 的先例，`services/config.py:238`）。因为 agent 内部持有 agent_llm 引用，llm 配置变更后 agent 必须重建才能拿到新 LLM；而 agent slot 的 `config_category` 已改为 `tools`，单纯 `refresh_category("llm")` 不再覆盖 agent。

### D4. 热更新时序：写库 → invalidate → refresh("agent")

```
PATCH /api/tools/{name}  {enabled: true|false}
  → admin 校验（非 admin → 40003）
  → update_tool_state(db, name, enabled, provider, registry)
      → name ∉ ALL_TOOL_NAMES           → ValueError → 40005
      → name ∈ GUARDED_TOOLS 且 disabled → ValueError → 40004
      → upsert system_configs 键 tools.<name>（category=tools）
      → provider.invalidate("tools")          # 缓存失效
      → await registry.refresh("agent")       # 读库最新 → 重建 Agent（失败保留旧实例）
  → 返回 {name, enabled, refresh_ok}
```

`registry.refresh("agent")` 内部 `get_category("tools")` 缓存 miss 后读库，factory 闭包用最新工具状态重建 Agent，即时生效。热更新失败时旧实例继续服务（registry 内置语义）。

### D5. 服务层 `services/tools.py`（新增）

- `GUARDED_TOOLS = {"transfer_human", "clarify"}`（兜底常开，后端硬校验防绕过）。
- `async def list_tool_states(db) -> dict[str, str]`：读 `tools` 分类 → 归一化 key → `{工具名: enabled/disabled}`；**缺失项按默认 `enabled`**（与 `DEFAULT_CONFIGS` 对齐，容忍脏数据）。
- `async def update_tool_state(db, name, enabled, provider, registry)`：
  - `name not in ALL_TOOL_NAMES` → `ValueError`（接口映射 40005）
  - `name in GUARDED_TOOLS and not enabled` → `ValueError`（接口映射 40004）
  - 写库（存在则更新 value，不存在则插入）→ `invalidate` → `refresh("agent")` → 返回 `(name, enabled, refresh_ok)`。

### D6. 接口 `api/tools.py`（新增，仅 admin）

- `GET /api/tools`：非 admin → `error(40003, "仅管理员可查看工具")`；返回 `{name, description, enabled}` 列表。description 来源 `TOOL_DESCRIPTIONS[name]`（与提示词一致），enabled 来源 `list_tool_states`。
- `PATCH /api/tools/{name}`：body `{enabled: bool}`；非 admin → 40003；`ValueError` 区分——兜底禁用 → `error(40004, "兜底工具不可禁用")`、未知工具 → `error(40005, "工具不存在")`；成功返回 `{name, enabled, refresh_ok}`。
- 注册：`api/__init__.py` 导出 `tools_router`，`app/main.py` `include_router(tools_router)`。

### D7. 前端 tools 页对接（沿用 users/knowledge 模式）

- `services/tools.ts`：`ToolItem`（`name`/`description`/`enabled`）+ `getToolsApi()`（GET）+ `updateToolApi(name, enabled)`（PATCH），fetchClient 封装。
- `app/tools/useServices.ts`：`useRequest` 加载列表（auto）+ `toggle` 手动调 PATCH，成功后刷新列表。
- `app/tools/page.tsx`：
  - **去掉 `mockTools`**。保留静态展示元数据映射 `toolMeta: Record<name, {triggerKey, inputKey, outputKey, implemented}>`（沿用原 mockTools 的 i18n 键，implemented 全部保留 `true`——用户已确认）；后端返回的 `name`/`enabled` 与之合并渲染。
  - 工具标识从 `id`（数字）改为 `name`（字符串）；`toggleTool(name)` 调 `updateToolApi` → 成功后刷新。
  - `GUARDED_TOOLS`（transfer_human、clarify）行开关置灰不可操作（`disabled` prop）。
  - 搜索过滤逻辑保留，基于 `tool.name`。
- i18n：`zh-CN.json`/`en-US.json` 补充 tools 错误提示（兜底工具不可禁用、操作失败重试）。

## 4. 数据流

**启动**：`init_default_configs` 幂等插入 tools 分类 6 项（默认 enabled）→ 首次请求 `ensure_initialized("agent")` 时 factory 读 tools 配置 → `filter_tools` + `build_system_prompt` → 创建绑定启用工具的 Agent。

**启停切换**：见 D4 时序图。前端 toggle → PATCH → 写库 + invalidate + refresh("agent") → 下一请求的 Agent 已绑定新工具集与动态提示词。

## 5. 接口契约

### `GET /api/tools`（admin）

```json
// 200
{ "code": 0, "data": [ { "name": "knowledge_base_query", "description": "当用户询问业务流程…时使用", "enabled": true }, … ] }
// 401 未认证 / 403 非 admin（40003）
```

### `PATCH /api/tools/{name}`（admin）

```json
// body
{ "enabled": true }
// 200
{ "code": 0, "data": { "name": "knowledge_base_query", "enabled": false, "refresh_ok": true } }
// 40003 非 admin | 40004 禁用兜底工具（transfer_human/clarify）| 40005 未知工具名
```

## 6. 测试策略

**单元测试**（`apps/service/tests/`，沿用 pytest + TestClient 模式）：
- `list_tool_states`：缺失工具默认 `enabled`、读取已存状态。
- `update_tool_state`：禁用兜底工具拒绝、未知工具拒绝、正常启停写库 + `invalidate`/`refresh` 被调用。
- `filter_tools`：禁用某工具后结果不含该工具。
- `build_system_prompt`：禁用某工具后提示词不含该工具描述与编号；启用子集时编号连续。
- API：GET 非 admin → 40003；PATCH 成功 / 兜底禁用 → 40004 / 未知工具 → 40005。工具为 LangChain StructuredTool，无 `__call__`，测试用 `await <tool>.ainvoke({...dict})`。

**集成**：`registry.refresh("agent")` 后 `registry.get("agent")` 绑定的工具集与 tools 分类配置一致。

**端到端**（admin 登录）：GET 返回 6 工具全 enabled → PATCH 禁用 `knowledge_base_query` → 状态持久化 + Agent 重建（SYSTEM_PROMPT 不含该工具描述）→ PATCH 禁用 `transfer_human` → 40004 → 恢复 enabled → 前端 tools 页真实渲染 + 切换刷新 + 兜底置灰。

## 7. 边界条件与风险

| 风险 | 缓解 |
|------|------|
| 禁用工具但提示词未同步 → LLM 调用未注册工具报错 | `build_system_prompt(enabled)` 单一来源，禁用即移除描述；测试断言"禁用后提示词不含该工具" |
| `get_category` 缓存读到旧启停状态 | PATCH 后先 `invalidate("tools")` 再 `refresh("agent")`，refresh 内缓存 miss 读库 |
| agent slot 解耦 llm 分类后 LLM 变更不重建 agent | `_apply_config_changes` 对 `llm` 对称额外 `refresh("agent")`（对齐 embedding→vectorstore 先例） |
| 兜底工具被禁用 → 客服失去转人工/澄清能力（事故级） | 后端 `GUARDED_TOOLS` 硬校验拒绝（防绕过）+ 前端置灰（UX）；测试覆盖 40004 |
| `get_category("tools")` key 含 `tools.` 前缀 | 统一归一化 `{k.split(".", 1)[-1]: v}`，services/agent/lifespan 三处消费点一致 |
| 热更新失败 | `registry.refresh` 失败保留旧实例继续服务（内置语义），接口返回 `refresh_ok: false` 供前端提示 |
| 禁用 `knowledge_base_query` 失效 RAG 问答 | 属预期行为（delta spec 已声明），端到端/截图注意 |

## 8. 迁移计划

无 schema/数据迁移（复用 `system_configs` 表；`init_default_configs` 幂等插入 `tools` 分类默认项）。
