## ADDED Requirements

### Requirement: AsyncConfigProvider 统一配置读取
系统 SHALL 提供 `AsyncConfigProvider` 类，封装从数据库异步读取配置的逻辑，替代各模块中分散的同步 DB 读取 hack。

#### Scenario: 按分类获取配置
- **WHEN** 调用 `config_provider.get_category("llm")`
- **THEN** 返回该分类下所有配置项的 `{key: value}` 字典，结果被缓存

#### Scenario: 缓存命中
- **WHEN** 连续两次调用 `get_category("llm")` 且中间未调用 `invalidate`
- **THEN** 第二次调用直接返回缓存结果，不查询数据库

#### Scenario: 缓存失效后重新读取
- **WHEN** 调用 `invalidate("llm")` 后再调用 `get_category("llm")`
- **THEN** 重新从数据库读取该分类配置并更新缓存

#### Scenario: 获取单个配置值
- **WHEN** 调用 `config_provider.get_value("llm.model", "deepseek-v4-pro")`
- **THEN** 返回该 key 对应的值，若不存在则返回默认值

### Requirement: AsyncConfigProvider 生命周期管理
系统 SHALL 在应用启动时创建 `AsyncConfigProvider` 实例，并通过 FastAPI 的 `app.state` 或依赖注入使其全局可用。

#### Scenario: 启动时初始化
- **WHEN** 应用启动（lifespan 开始）
- **THEN** 创建 `AsyncConfigProvider` 实例并存储在 `app.state.config_provider`

#### Scenario: 关闭时清理
- **WHEN** 应用关闭（lifespan 结束）
- **THEN** 清理 `AsyncConfigProvider` 的缓存资源

### Requirement: 消除同步 DB 读取 hack
系统 SHALL 移除 `_get_llm_params()`、`_get_embedding_params()`、`_get_vectorstore_params()` 中的 `asyncio.run()` + `ThreadPoolExecutor` 同步读取模式，改用 `AsyncConfigProvider` 的异步接口。

#### Scenario: LLM 配置读取
- **WHEN** 创建 LLM 实例需要读取配置
- **THEN** 通过 `AsyncConfigProvider.get_category("llm")` 异步获取，不使用 `asyncio.run()`

#### Scenario: Embedding 配置读取
- **WHEN** 创建 Embedding 实例需要读取配置
- **THEN** 通过 `AsyncConfigProvider.get_category("embedding")` 异步获取

#### Scenario: VectorStore 配置读取
- **WHEN** 创建 VectorStore 实例需要读取配置
- **THEN** 通过 `AsyncConfigProvider.get_category("vectorstore")` 异步获取
