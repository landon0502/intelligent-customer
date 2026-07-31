## Context

当前 intelligent-customer service 端的组件初始化和配置管理存在以下问题：

1. **同步 DB 读取 hack**：`_get_llm_params()`、`_get_embedding_params()`、`_get_vectorstore_params()` 都在同步函数中用 `asyncio.run()` + `ThreadPoolExecutor` 读取数据库，在 FastAPI 的 async 上下文中极易出错
2. **全局单例不安全**：`_llm`、`_embeddings`、`_vectorstore`、`_chroma_client` 都是模块级全局变量，靠 `reset_*()` 置 None 来"动态生效"，无线程安全保证
3. **Agent 重建不安全**：`_rebuild_agent()` 直接替换 `app.state.agent`，进行中的 SSE 流仍持有旧引用；重建失败时 fallback 逻辑混乱
4. **Eager 初始化**：启动时 `create_customer_agent()` 触发 LLM 实例化，含调试代码 `print(_llm.invoke("你好"))`
5. **配置读取分散**：每个模型模块各自实现 DB 读取逻辑，代码重复
6. **LLM 共享单例**：Agent 和 RAG 共享 `create_llm()` 单例，无法独立配置

约束：只调整 service 端，不涉及前端和数据库表结构变更。

## Goals / Non-Goals

**Goals:**
- 统一配置读取：消除分散的同步 DB 读取 hack，提供异步配置提供者
- 请求级配置生效：配置更新后新请求用新配置，进行中 SSE 流优雅完成
- Agent/RAG LLM 独立配置：各自可设不同模型和参数
- 懒加载初始化：启动时不创建组件实例，首次请求时才创建
- 全配置动态生效：Web 配置页面中所有配置都支持动态生效
- 组件生命周期管理：统一管理 LLM/Embedding/VectorStore/Agent 的创建、缓存和替换

**Non-Goals:**
- 前端改动
- 数据库 schema 变更（SystemConfig 表结构保持不变）
- 多租户/多模型实例池
- 配置版本回滚机制
- 配置值合法性校验（后续迭代）

## Decisions

### D1: 配置提供者模式 — AsyncConfigProvider

**选择**：引入 `AsyncConfigProvider` 类，封装异步 DB 读取 + 内存缓存 + 失效通知

**替代方案**：
- A) 继续现状（各模块自行读取）— 代码重复，无法统一缓存/失效
- B) Redis 缓存层 — 引入新依赖，增加复杂度，当前规模不需要
- C) FastAPI Depends 注入 — 每次请求都查 DB，无缓存，性能差

**理由**：AsyncConfigProvider 在内存中缓存配置，配置更新时通过 `invalidate(category)` 方法失效缓存，下次获取时重新从 DB 读取。简单、无新依赖、性能好。

```
┌─────────────────────────────────────────────┐
│           AsyncConfigProvider                │
│                                             │
│  _cache: dict[str, dict]  # category → {k:v}│
│  _db: AsyncSession                          │
│                                             │
│  + get_category(category) → dict            │
│  + get_value(key, default) → str            │
│  + invalidate(category) → None              │
│  + invalidate_all() → None                  │
└─────────────────────────────────────────────┘
```

### D2: 组件注册表 — ComponentRegistry

**选择**：引入 `ComponentRegistry`，管理组件的懒加载创建和版本化替换

**替代方案**：
- A) 继续全局单例 + reset — 线程不安全，无法请求级生效
- B) 每次请求创建新实例 — 性能差，LLM 初始化开销大
- C) 依赖注入框架（如 dependency-injector）— 过重，学习成本高

**理由**：ComponentRegistry 持有组件的"当前版本"引用，配置更新时创建新版本并替换指针，旧版本在所有引用释放后自然回收。Python 的引用计数 + GIL 保证了线程安全。

```
┌──────────────────────────────────────────────────────┐
│              ComponentRegistry                        │
│                                                      │
│  _components: dict[str, ComponentSlot]               │
│                                                      │
│  + register(name, factory, config_category)           │
│  + get(name) → component       # 获取当前版本        │
│  + refresh(name) → component   # 用新配置重建并替换   │
│  + refresh_category(category)  # 刷新该分类下所有组件 │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│              ComponentSlot                            │
│                                                      │
│  _current: component | None    # 当前版本（懒加载）   │
│  _factory: callable            # 创建函数             │
│  _config_category: str         # 依赖的配置分类       │
│                                                      │
│  + get() → component           # 懒加载获取          │
│  + refresh(new_factory) → component                  │
│     # 创建新实例，替换 _current 指针                  │
│     # 旧实例的已有引用继续有效，直到引用释放          │
└──────────────────────────────────────────────────────┘
```

**请求级生效原理**：
- SSE 流开始时通过 `registry.get("agent")` 获取 agent 引用并持有
- 配置更新时 `registry.refresh("agent")` 创建新 agent 并替换 `_current`
- 进行中的 SSE 流仍持有旧 agent 引用，流结束后旧 agent 自然回收
- 新请求调用 `registry.get("agent")` 获取新 agent

### D3: Agent/RAG LLM 独立配置

**选择**：在 SystemConfig 中增加 `rag_llm.*` 配置分类，RAG 生成链使用独立 LLM 实例

**实现**：
- 注册两个 LLM 组件：`"agent_llm"`（依赖 `llm` 分类）和 `"rag_llm"`（依赖 `rag_llm` 分类）
- `rag_llm` 分类配置项：`rag_llm.model`、`rag_llm.temperature`、`rag_llm.max_tokens` 等
- RAG 生成链从注册表获取 `"rag_llm"` 而非调用 `create_llm()`
- 如果 `rag_llm` 分类未配置，回退到 `llm` 分类配置

### D4: 懒加载初始化

**选择**：启动时只初始化 ConfigProvider 和 ComponentRegistry，不创建任何组件实例

**实现**：
- `lifespan.py` 中移除 `create_customer_agent()` 调用
- 注册组件到 Registry（只注册 factory 和 config_category，不触发创建）
- 首次请求时 `registry.get("agent")` 触发懒加载创建
- 移除 `create_llm()` 中的 `print` 和 `invoke` 调试代码

### D5: 配置更新流程

**选择**：配置更新 → 通知 ConfigProvider 失效缓存 → 通知 ComponentRegistry 刷新组件

```
PUT /api/config
    │
    ▼
update_configs(db, configs)
    │
    ├─ 写入 DB
    │
    └─ _apply_config_changes(categories)
         │
         ├─ config_provider.invalidate(category)  # 失效缓存
         │
         └─ registry.refresh_category(category)   # 重建组件
              │
              ├─ 用新配置创建新 factory
              ├─ 替换 ComponentSlot._current
              └─ 旧实例的已有引用继续有效
```

## Risks / Trade-offs

- **[风险] 首次请求延迟** → 懒加载导致首次请求需要创建 LLM 实例（可能数秒）。缓解：可在启动后异步预热，但不阻塞启动
- **[风险] 内存占用** → 配置更新时新旧组件可能短暂共存。缓解：Python 引用计数确保旧组件在流结束后立即回收
- **[风险] 配置更新失败** → 新组件创建失败时旧组件继续服务。缓解：`refresh()` 捕获异常，记录日志，保留旧组件不替换
- **[权衡] 不引入 Redis 缓存** → 配置缓存纯内存，重启后丢失。可接受：配置本就存在 DB 中，启动时重新加载
- **[权衡] 不做配置值校验** → 非法配置可能导致组件创建失败。可接受：创建失败时保留旧组件，管理员可通过日志发现问题
