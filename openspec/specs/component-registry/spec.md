# component-registry Specification

## Purpose
TBD - created by archiving change redesign-agent-init-dynamic-config. Update Purpose after archive.
## Requirements
### Requirement: ComponentRegistry 组件注册
系统 SHALL 提供 `ComponentRegistry` 类，管理 LLM、Embedding、VectorStore、Agent 等组件的注册、创建和生命周期。

#### Scenario: 注册组件
- **WHEN** 调用 `registry.register("agent_llm", factory=create_agent_llm, config_category="llm")`
- **THEN** 组件被注册但未创建实例，factory 和 config_category 被记录

#### Scenario: 懒加载获取组件
- **WHEN** 首次调用 `registry.get("agent_llm")`
- **THEN** 调用 factory 创建组件实例，缓存并返回；后续调用直接返回缓存实例

#### Scenario: 组件不存在
- **WHEN** 调用 `registry.get("nonexistent")`
- **THEN** 抛出 KeyError 或返回 None

### Requirement: ComponentSlot 版本化替换
系统 SHALL 通过 `ComponentSlot` 实现组件的版本化替换，确保配置更新时进行中的请求不受影响。

#### Scenario: 刷新组件
- **WHEN** 调用 `registry.refresh("agent_llm")`
- **THEN** 用新配置创建新组件实例，替换 `_current` 指针；旧实例的已有引用继续有效

#### Scenario: 进行中请求不受影响
- **WHEN** SSE 流持有旧 agent 引用，同时配置更新触发 `refresh("agent")`
- **THEN** 旧 SSE 流继续使用旧 agent 完成当前对话，新请求获取新 agent

#### Scenario: 刷新失败保留旧组件
- **WHEN** `refresh("agent_llm")` 创建新实例失败（如 API Key 无效）
- **THEN** 保留旧组件实例不替换，记录错误日志，进行中请求和新请求都使用旧组件

### Requirement: 按配置分类批量刷新
系统 SHALL 支持按配置分类批量刷新相关组件。

#### Scenario: LLM 配置变更刷新
- **WHEN** 调用 `registry.refresh_category("llm")`
- **THEN** 刷新所有 `config_category="llm"` 的组件（agent_llm、agent）

#### Scenario: Embedding 配置变更刷新
- **WHEN** 调用 `registry.refresh_category("embedding")`
- **THEN** 刷新所有 `config_category="embedding"` 的组件（embeddings、vectorstore）

### Requirement: 移除全局单例和手动 reset
系统 SHALL 移除 `_llm`、`_embeddings`、`_vectorstore`、`_chroma_client` 全局变量和对应的 `reset_*()` 函数，由 ComponentRegistry 统一管理。

#### Scenario: 不再使用全局变量
- **WHEN** 代码需要获取 LLM 实例
- **THEN** 通过 `registry.get("agent_llm")` 获取，不使用 `create_llm()` 全局单例

#### Scenario: 不再使用 reset 函数
- **WHEN** 配置更新需要重建组件
- **THEN** 通过 `registry.refresh()` 刷新，不调用 `reset_llm()` 等函数

