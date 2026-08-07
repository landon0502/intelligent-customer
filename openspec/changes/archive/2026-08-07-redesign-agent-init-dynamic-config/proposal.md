## Why

当前 service 端 Agent 初始化和 LLM 配置管理存在严重架构缺陷：模型工厂使用同步 DB 读取 hack（`asyncio.run` + `ThreadPoolExecutor`）在 async 上下文中读取配置，极易出错；全局单例 + 手动 `reset_*()` 函数线程不安全；Agent 重建直接替换 `app.state.agent`，进行中的 SSE 流可能行为不一致；启动时 eager 初始化包含调试代码（`print(_llm.invoke("你好"))`）；配置读取逻辑分散在多个模块中重复实现；Agent 和 RAG 共享同一个 LLM 单例无法独立配置。这些问题导致配置动态生效不可靠、不安全，需要重新设计整个组件生命周期管理机制。

## What Changes

- **引入配置提供者（ConfigProvider）**：统一从数据库异步读取配置，消除分散的同步 DB 读取 hack，支持配置缓存和失效
- **引入组件注册表（ComponentRegistry）**：管理 LLM、Embedding、VectorStore、Agent 等组件的生命周期，替代全局单例 + 手动 reset
- **请求级配置生效**：配置更新后新请求自动使用新配置，进行中的 SSE 流优雅完成（继续用旧组件直到流结束）
- **Agent/RAG LLM 独立配置**：Agent 和 RAG 生成链可使用不同的 LLM 模型和参数
- **懒加载初始化**：启动时只验证配置可读，首次请求时才创建组件实例
- **全配置动态生效**：LLM、Embedding、VectorStore、RAG 参数、Agent Prompt 等所有 Web 配置页面中的配置都支持动态生效
- **移除调试代码**：清理 `create_llm()` 中的 `print` 和 `invoke` 调试语句

## Capabilities

### New Capabilities
- `config-provider`: 统一配置提供者，异步从数据库读取配置，支持缓存、分类查询和失效通知
- `component-registry`: 组件注册表，管理 LLM/Embedding/VectorStore/Agent 等组件的懒加载创建、请求级版本化和优雅替换
- `request-scoped-components`: 请求级组件获取机制，确保配置更新时进行中的请求不受影响，新请求使用新配置

### Modified Capabilities
<!-- 无已有 spec 需要修改 -->

## Impact

- **核心模块重构**：`models/factory.py`、`models/embedding.py`、`rag/ingestion/vectorstore.py`、`agent/factory.py` — 移除全局单例，改用注册表
- **依赖注入变更**：`app/dependencies.py` — 从 `app.state.agent` 改为从注册表获取请求级组件
- **配置服务增强**：`services/config.py` — 配置更新时通知注册表而非手动 reset
- **启动流程简化**：`app/lifespan.py` — 移除 eager 初始化，改为懒加载
- **RAG 生成链**：`rag/generation/chain.py` — 使用独立 LLM 配置而非共享 `create_llm()`
- **API 层**：`api/config.py` — 可能需要增加配置校验和生效状态反馈
- **配置 schema**：`schemas/system_config_schema.py` — 可能需要增加 Agent LLM 和 RAG LLM 的独立配置项
