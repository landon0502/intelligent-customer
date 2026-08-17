# Proposal: 工具启停配置（后端配置 + Agent 动态绑定 + 接口 + tools 页对接）

## Why

Agent 当前固定绑定全部 6 个工具（`ALL_TOOLS`），前端 tools 页使用写死的 `mockTools` 模拟开关，无真实配置能力。运营侧需要能按需启停工具（如临时下线某工具、禁用知识库问答），且切换需即时生效。本次补齐工具启停配置能力：后端配置存储 + Agent 动态绑定 + 管理接口 + 前端 tools 页对接。

## What Changes

- **配置存储**：复用 `system_configs` 表，新增 `tools` 分类（key=工具名，value=`enabled`/`disabled`），与现有 `llm`/`embedding` 分类的热更新机制一致；默认全部启用。
- **Agent 动态绑定**：`agent/factory.py` 读取 `tools` 分类配置 → 过滤 `ALL_TOOLS` → 只绑定启用工具；禁用工具时 `SYSTEM_PROMPT` 同步移除对应工具描述（否则 LLM 调用未注册工具报错）。切换后复用 `registry.refresh("agent")` 热更新即时生效。
- **管理接口**（仅 admin）：
  - `GET /api/tools` — 返回 6 个工具 + 启用状态
  - `PATCH /api/tools/{name}` — 启停切换 → 写库 → `provider.invalidate("tools")` + `registry.refresh("agent")` 即时生效
- **兜底工具常开**：`transfer_human`、`clarify` 不允许禁用（后端 PATCH 硬校验拒绝 + 前端置灰），避免客服失去转人工/澄清能力。
- **前端 tools 页**：去除 `mockTools`，对接 GET/PATCH，开关切换调用接口并刷新；兜底工具开关置灰。

## Capabilities

### New Capabilities
- `tool-toggle-config`: 工具启停配置能力（tools 分类配置存储、Agent 动态绑定启用工具、GET/PATCH 管理接口、前端 tools 页对接、兜底工具不可禁用）

### Modified Capabilities
无（`agent-tools` 的工具行为在启用时不变；新增启停能力不改变现有工具 requirement）。

## Impact

- 后端：`services/config.py`（tools 默认配置 + 读写）、`agent/factory.py` + `agent/prompts.py`（动态绑定 + 动态 SYSTEM_PROMPT）、`app/lifespan.py`（agent slot 绑定 tools 分类 + LLM 变更对称刷新）、`api/tools.py`（新，GET/PATCH）、`api/__init__.py` + `app/main.py`（注册路由）
- 前端：`apps/web/services/tools.ts`（新）、`app/tools/useServices.ts`（新）、`app/tools/page.tsx`（去 mock）、i18n 消息（tools 错误提示等）
- 无 schema 变更（复用 `system_configs` 表）、无破坏性变更
