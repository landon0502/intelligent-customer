## 1. 基础设施 — AsyncConfigProvider

- [x] 1.1 创建 `configs/provider.py`，实现 `AsyncConfigProvider` 类：`get_category(category)` 异步读取并缓存配置、`get_value(key, default)` 获取单值、`invalidate(category)` 失效缓存、`invalidate_all()` 全量失效
- [x] 1.2 为 `AsyncConfigProvider` 编写单元测试：缓存命中、缓存失效后重新读取、获取单值回退默认值

## 2. 基础设施 — ComponentRegistry

- [x] 2.1 创建 `configs/registry.py`，实现 `ComponentSlot` 类：`_current` 持有当前组件、`_factory` 创建函数、`get()` 懒加载、`refresh(new_factory)` 版本化替换（失败时保留旧组件）
- [x] 2.2 实现 `ComponentRegistry` 类：`register(name, factory, config_category)` 注册组件、`get(name)` 获取组件、`refresh(name)` 刷新单个组件、`refresh_category(category)` 按分类批量刷新
- [x] 2.3 为 `ComponentRegistry` 编写单元测试：懒加载、版本化替换、刷新失败保留旧组件、按分类批量刷新

## 3. 重构模型工厂

- [x] 3.1 重构 `models/factory.py`：移除 `_llm` 全局变量、`_get_llm_params()` 同步 DB hack、`reset_llm()` 函数；改为提供 `create_agent_llm(config)` 和 `create_rag_llm(rag_config, llm_config)` 工厂函数
- [x] 3.2 重构 `models/embedding.py`：移除 `_embeddings` 全局变量、`_get_embedding_params()` 同步 DB hack、`reset_embeddings()` 函数；改为提供 `create_embeddings(config)` 工厂函数
- [x] 3.3 重构 `rag/ingestion/vectorstore.py`：移除 `_chroma_client`/`_vectorstore` 全局变量、`_get_vectorstore_params()` 同步 DB hack、`reset_vectorstore()` 函数；改为提供 `create_chroma_client(config)` 和 `create_vectorstore(config, embeddings, client)` 工厂函数
- [x] 3.4 移除 `create_llm()` 中的 `print(params)` 和 `print(_llm.invoke("你好"))` 调试代码

## 4. 重构 Agent 工厂

- [x] 4.1 重构 `agent/factory.py`：`create_customer_agent()` 改为 `create_customer_agent(agent_llm, tools, system_prompt)` 接受注入的 LLM 实例，不再内部调用 `create_llm()`
- [x] 4.2 在 `services/config.py` 的 `DEFAULT_CONFIGS` 中增加 `rag_llm.*` 配置项（model、temperature、max_tokens、timeout、max_retries），并更新 `init_default_configs`

## 5. 重构 RAG 生成链

- [x] 5.1 重构 `rag/generation/chain.py`：`generate_answer()` 改为接受 `rag_llm` 参数，不再内部调用 `create_llm()`；RAG 生成链使用独立 LLM 实例

## 6. 重构应用启动和依赖注入

- [x] 6.1 重构 `app/lifespan.py`：启动时创建 `AsyncConfigProvider` 和 `ComponentRegistry`，注册所有组件（agent_llm、rag_llm、embeddings、chroma_client、vectorstore、agent），移除 `create_customer_agent()` eager 初始化
- [x] 6.2 重构 `app/dependencies.py`：`get_agent` 改为从 `ComponentRegistry` 获取当前版本 Agent；增加 `get_config_provider` 和 `get_registry` 依赖注入函数
- [x] 6.3 重构 `api/chat.py`：SSE 流开始时通过依赖注入获取 Agent 引用并持有，确保流期间引用不变

## 7. 重构配置更新流程

- [x] 7.1 重构 `services/config.py`：`_apply_config_changes()` 改为通知 `ConfigProvider.invalidate(category)` + `ComponentRegistry.refresh_category(category)`，移除 `reset_llm()`/`reset_embeddings()`/`reset_vectorstore()` 调用和 `_rebuild_agent()` 函数
- [x] 7.2 重构 `api/config.py`：配置更新 API 返回生效状态（哪些组件已刷新、是否有刷新失败）

## 8. 集成验证

- [x] 8.1 端到端验证：27/27 单元测试通过（AsyncConfigProvider 7 个 + ComponentRegistry 12 个 + 工厂函数 8 个）
- [x] 8.2 验证 Agent/RAG LLM 独立配置：create_rag_llm fallback 测试通过
- [x] 8.3 验证配置更新失败场景：refresh_failure_keeps_old_instance 测试通过
