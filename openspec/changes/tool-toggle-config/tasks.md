## 组 1：后端配置与 Agent 动态绑定

### Task 1: tools 分类默认配置
- [x] `services/config.py` 的 `DEFAULT_CONFIGS` 添加 `tools` 分类 6 项默认配置（key=`tools.<工具名>`，value=`enabled`，category=`tools`，description 中文说明），覆盖 `knowledge_base_query`/`enterprise_query`/`ticket_submit`/`ticket_status`/`transfer_human`/`clarify`
- [x] 确认 `init_default_configs` 幂等插入（仅缺失键，不覆盖已有值）
- [x] 单测：`init_default_configs` 后 `tools` 分类 6 项全部为 `enabled`

### Task 2: 工具启停服务层
- [x] 新增 `services/tools.py`：`list_tool_states(db)` 读取 `tools` 分类返回 `{工具名: enabled/disabled}`，缺失项按默认 `enabled`
- [x] `update_tool_state(db, name, enabled, provider, registry)`：校验工具存在于 `ALL_TOOLS`（不存在抛 `ValueError`）→ 校验 `transfer_human`/`clarify` 不允许禁用（抛 `ValueError`）→ 写 `system_configs` → `provider.invalidate("tools")` → `registry.refresh("agent")` → 返回新状态
- [x] 单测：禁用兜底工具拒绝、未知工具拒绝、正常启停写库 + 热更新被调用

### Task 3: Agent 动态绑定与动态提示词
- [x] `agent/prompts.py`：拆出静态工具描述表 `TOOL_DESCRIPTIONS`（name → 描述文本，沿用现有 SYSTEM_PROMPT 中 1-6 工具描述）与固定提示词段（决策规则/回答规范/格式要求）；新增 `build_system_prompt(enabled_names)` 按启用工具生成动态 SYSTEM_PROMPT（禁用工具的描述与调用引导同步移除）
- [x] `agent/factory.py`：新增 `filter_tools(tool_states)` 从 `ALL_TOOLS` 过滤出启用工具；`create_customer_agent(agent_llm, tools, system_prompt)` 接收注入的过滤工具集与动态提示词
- [x] 单测：禁用某工具后 `filter_tools` 结果不含该工具；`build_system_prompt` 结果不含该工具描述

### Task 4: lifespan 接线与 llm 变更对称刷新
- [x] `app/lifespan.py` `_agent_factory` 改为闭包捕获 provider，读取 `tools` 分类配置 → `filter_tools` + `build_system_prompt` → 注入 `create_customer_agent`
- [x] `services/config.py` `_apply_config_changes` 增加：`llm` 分类变更时额外 `refresh("agent")`（对齐 embedding→vectorstore 既有模式，保证 Agent 持有的 LLM 引用同步）
- [x] 验证：启动后 `registry.get("agent")` 绑定的工具与 `tools` 分类配置一致

## 组 2：接口与前端

### Task 5: api/tools.py 接口与路由注册
- [x] 新增 `api/tools.py`：`GET /api/tools`（admin 校验，返回全部工具 name/description/enabled）+ `PATCH /api/tools/{name}`（admin 校验，body `{enabled: bool}`，调用 `update_tool_state`；`ValueError` → 40004，未知工具 → 40005，非 admin → 40003）
- [x] 注册 `api/__init__.py` + `app/main.py` 两处路由
- [x] 单测：GET 非 admin 40003、PATCH 成功/兜底禁用 40004/未知工具 40005

### Task 6: 前端 services 与 useServices
- [ ] 新增 `apps/web/services/tools.ts`：`ToolItem` 类型（name/description/enabled）+ `getToolsApi()` + `updateToolApi(name, enabled)`（fetchClient 封装）
- [ ] 新增 `app/tools/useServices.ts`：`useRequest` 加载工具列表 + toggle 切换控制（成功后刷新）
- [ ] `pnpm typecheck` 无本文件新增错误

### Task 7: page.tsx 去 mock 与 i18n
- [ ] `page.tsx` 去除 `mockTools`：保留前端静态展示元数据映射（name → triggerKey/inputKey/outputKey/i18n、implemented 标记），与后端返回的 name/enabled 合并渲染
- [ ] 开关切换调用 PATCH 接口 → 成功后刷新列表；`transfer_human`/`clarify` 行开关置灰不可操作
- [ ] i18n `zh-CN.json`/`en-US.json` 补充 tools 相关提示（如兜底工具不可禁用、操作失败）
- [ ] `pnpm typecheck` + 本地验证页面真实渲染

## 组 3：全量验证

### Task 8: 全量测试与端到端验证
- [ ] `cd apps/service && .venv/bin/python -m pytest tests/ -q` 全量通过（含新增用例）
- [ ] `npm run build` 构建成功（含 `/tools` 路由）
- [ ] 端到端（admin 登录）：GET /api/tools 返回 6 工具全 enabled → PATCH 禁用 `knowledge_base_query` → 状态持久化 + 热更新生效（agent SYSTEM_PROMPT 不含该工具描述、不再调用该工具）→ PATCH 禁用 `transfer_human` 返回 40004 → 恢复 `knowledge_base_query` 为 enabled → 前端 tools 页真实列表渲染 + 开关切换刷新 + 兜底工具置灰
- [ ] 测试数据清理，无脏数据残留
