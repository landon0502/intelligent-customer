## ADDED Requirements

### Requirement: 请求级组件获取
系统 SHALL 通过 FastAPI 依赖注入提供请求级组件获取，确保每个请求获取当前版本的组件。

#### Scenario: Chat 请求获取 Agent
- **WHEN** Chat 请求通过 `Depends(get_agent)` 获取 Agent
- **THEN** 返回 ComponentRegistry 中当前版本的 Agent 实例

#### Scenario: RAG 请求获取 LLM
- **WHEN** RAG 生成链需要 LLM 实例
- **THEN** 通过 `registry.get("rag_llm")` 获取独立于 Agent LLM 的实例

#### Scenario: SSE 流持有组件引用
- **WHEN** SSE 流开始时获取 Agent 引用
- **THEN** 整个流期间持有同一引用，即使配置更新导致 registry 中 Agent 被替换

### Requirement: Agent/RAG LLM 独立配置
系统 SHALL 支持 Agent 和 RAG 使用不同的 LLM 模型和参数。

#### Scenario: Agent 使用独立 LLM 配置
- **WHEN** 管理员配置 `llm.model=deepseek-v4-pro`
- **THEN** Agent 使用 deepseek-v4-pro 模型

#### Scenario: RAG 使用独立 LLM 配置
- **WHEN** 管理员配置 `rag_llm.model=deepseek-v3` 且 `rag_llm.temperature=0.3`
- **THEN** RAG 生成链使用 deepseek-v3 模型，temperature=0.3

#### Scenario: RAG LLM 配置回退
- **WHEN** `rag_llm` 分类未配置任何值
- **THEN** RAG 生成链回退使用 `llm` 分类的配置

### Requirement: 懒加载初始化
系统 SHALL 在启动时不创建任何组件实例，首次请求时才触发创建。

#### Scenario: 启动不创建组件
- **WHEN** 应用启动完成
- **THEN** ComponentRegistry 中所有组件均为 None（未创建），ConfigProvider 已初始化

#### Scenario: 首次请求触发创建
- **WHEN** 首次 Chat 请求到达
- **THEN** `registry.get("agent")` 触发 Agent 及其依赖组件的懒加载创建

#### Scenario: 移除启动时 eager 初始化
- **WHEN** 应用启动
- **THEN** 不调用 `create_customer_agent()`，不调用 `create_llm()`，不执行 `print(_llm.invoke("你好"))`

### Requirement: 配置更新动态生效
系统 SHALL 在配置更新时自动使新配置生效，无需重启服务。

#### Scenario: LLM 配置更新生效
- **WHEN** 管理员通过 PUT /api/config 更新 `llm.model`
- **THEN** ConfigProvider 失效 llm 分类缓存，ComponentRegistry 刷新 agent_llm 和 agent 组件，新请求使用新模型

#### Scenario: Embedding 配置更新生效
- **WHEN** 管理员更新 `embedding.model`
- **THEN** ConfigProvider 失效 embedding 分类缓存，ComponentRegistry 刷新 embeddings 和 vectorstore 组件

#### Scenario: 全配置动态生效
- **WHEN** 管理员更新任意分类的配置
- **THEN** 对应分类的缓存失效，对应组件刷新，新请求使用新配置

### Requirement: 优雅的旧请求处理
系统 SHALL 确保配置更新时不中断进行中的 SSE 流。

#### Scenario: 进行中 SSE 流继续完成
- **WHEN** SSE 流正在输出，同时配置更新触发组件刷新
- **THEN** SSE 流继续使用旧组件完成当前对话，不受影响

#### Scenario: 新请求使用新配置
- **WHEN** 配置更新完成后新请求到达
- **THEN** 新请求获取刷新后的组件实例，使用新配置
