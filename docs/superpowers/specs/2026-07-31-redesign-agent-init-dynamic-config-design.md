---
comet_change: redesign-agent-init-dynamic-config
role: technical-design
canonical_spec: openspec
---

# Agent 初始化重构与 LLM 配置动态生效 — 技术设计

## 1. 概述

本设计重构 service 端的 Agent 初始化和 LLM 配置管理，解决同步 DB 读取 hack、全局单例不安全、Agent 重建不安全、eager 初始化等问题。引入 AsyncConfigProvider + ComponentRegistry + ComponentSlot 三层架构，实现请求级配置生效、Agent/RAG LLM 独立配置、懒加载初始化。

## 2. 核心架构

```
┌──────────────────────────────────────────────────────────────┐
│                       FastAPI App                            │
│                                                              │
│  app.state.config_provider = AsyncConfigProvider             │
│  app.state.registry = ComponentRegistry                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │              AsyncConfigProvider                      │     │
│  │                                                       │     │
│  │  _session_factory: async_session_factory              │     │
│  │  _cache: dict[str, dict]  # category → {key: value}  │     │
│  │                                                       │     │
│  │  + get_category(category) → dict                      │     │
│  │  + get_value(key, default) → str                      │     │
│  │  + invalidate(category) → None                        │     │
│  │  + invalidate_all() → None                            │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │              ComponentRegistry                        │     │
│  │                                                       │     │
│  │  _slots: dict[str, ComponentSlot]                     │     │
│  │  _provider: AsyncConfigProvider                       │     │
│  │  _order: list[str]  # 注册顺序，保证刷新顺序         │     │
│  │                                                       │     │
│  │  + register(name, factory, config_category)           │     │
│  │  + get(name) → component                              │     │
│  │  + refresh(name) → component                          │     │
│  │  + refresh_category(category) → None                  │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │              ComponentSlot                            │     │
│  │                                                       │     │
│  │  _current: component | None                          │     │
│  │  _factory: (config: dict) → component  # sync!       │     │
│  │  _config_category: str                                │     │
│  │                                                       │     │
│  │  + get() → component                                  │     │
│  │  + replace(new_instance) → None                       │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

## 3. AsyncConfigProvider 详细设计

### 3.1 类定义

```python
class AsyncConfigProvider:
    """统一配置提供者 — 异步读取 DB 配置，内存缓存，支持失效。"""

    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._cache: dict[str, dict[str, str]] = {}

    async def get_category(self, category: str) -> dict[str, str]:
        """获取某分类下所有配置，优先返回缓存。"""
        if category in self._cache:
            return self._cache[category]
        async with self._session_factory() as db:
            result = await db.execute(
                select(SystemConfig).where(SystemConfig.category == category)
            )
            rows = result.scalars().all()
            config = {row.key: row.value for row in rows}
            self._cache[category] = config
            return config

    async def get_value(self, key: str, default: str = "") -> str:
        """获取单个配置值，从缓存中提取。"""
        category = key.split(".")[0]
        config = await self.get_category(category)
        return config.get(key, default)

    def invalidate(self, category: str) -> None:
        """失效某分类的缓存。"""
        self._cache.pop(category, None)

    def invalidate_all(self) -> None:
        """失效所有缓存。"""
        self._cache.clear()
```

### 3.2 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| DB 会话管理 | Provider 持有 session_factory | 调用方无需传递 DB session，接口简洁 |
| 缓存粒度 | 按分类缓存 | 与配置更新 API 的分类粒度一致 |
| 读取策略 | Cache-Aside（先查缓存，miss 时读 DB） | 简单可靠，无并发一致性问题（Python GIL） |

## 4. ComponentRegistry 详细设计

### 4.1 ComponentSlot

```python
class ComponentSlot:
    """组件槽位 — 懒加载、原子替换、失败保留旧实例。"""

    def __init__(self, name: str, factory: Callable[[dict], Any], config_category: str):
        self.name = name
        self._factory = factory
        self._config_category = config_category
        self._current: Any = None
        self._initialized = False

    def get(self) -> Any:
        """获取当前组件实例（懒加载）。"""
        if not self._initialized:
            raise RuntimeError(f"Component '{self.name}' not initialized. Call create first.")
        return self._current

    def create(self, config: dict) -> Any:
        """用给定配置创建组件实例（首次创建）。"""
        instance = self._factory(config)
        self._current = instance
        self._initialized = True
        return instance

    def replace(self, new_instance: Any) -> None:
        """原子替换当前实例。旧引用继续有效直到释放。"""
        self._current = new_instance
```

### 4.2 ComponentRegistry

```python
class ComponentRegistry:
    """组件注册表 — 管理组件的懒加载创建和事务性版本化替换。"""

    def __init__(self, provider: AsyncConfigProvider):
        self._provider = provider
        self._slots: dict[str, ComponentSlot] = {}
        self._order: list[str] = []  # 注册顺序

    def register(self, name: str, factory: Callable[[dict], Any],
                 config_category: str) -> None:
        """注册组件（不触发创建）。"""
        slot = ComponentSlot(name, factory, config_category)
        self._slots[name] = slot
        self._order.append(name)

    def get(self, name: str) -> Any:
        """获取组件（懒加载：首次获取时触发创建）。"""
        slot = self._slots.get(name)
        if slot is None:
            raise KeyError(f"Component '{name}' not registered")
        if not slot._initialized:
            # 懒加载：首次获取时创建
            config = await self._provider.get_category(slot._config_category)
            slot.create(config)
        return slot.get()

    async def refresh(self, name: str) -> bool:
        """刷新单个组件。返回是否成功。"""
        slot = self._slots.get(name)
        if slot is None:
            return False
        try:
            config = await self._provider.get_category(slot._config_category)
            new_instance = slot._factory(config)
            slot.replace(new_instance)
            return True
        except Exception as e:
            logger.error("刷新组件 %s 失败: %s", name, e)
            return False

    async def refresh_category(self, category: str) -> dict[str, bool]:
        """事务性刷新某分类下所有组件。

        先创建所有新实例，全部成功后统一替换；
        任一失败则全部回退，保留旧实例。
        """
        # 1. 收集该分类下的 slot（按注册顺序）
        affected = [s for s in self._slots.values()
                     if s._config_category == category]

        # 2. 先失效缓存，确保读取最新配置
        self._provider.invalidate(category)

        # 3. 为每个 slot 创建新实例
        new_instances: dict[str, tuple[ComponentSlot, Any]] = {}
        for slot in affected:
            try:
                config = await self._provider.get_category(slot._config_category)
                new_instance = slot._factory(config)
                new_instances[slot.name] = (slot, new_instance)
            except Exception as e:
                logger.error("事务性刷新失败: 创建 %s 时出错: %s", slot.name, e)
                # 全部回退：不替换任何实例
                return {name: False for name in self._slots
                        if self._slots[name]._config_category == category}

        # 4. 全部成功，统一替换
        for slot, new_instance in new_instances.values():
            slot.replace(new_instance)

        return {name: True for name in new_instances}
```

### 4.3 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Factory 签名 | sync `(config: dict) → component` | 与 LangChain sync API 兼容 |
| 依赖管理 | Registry 不感知依赖 | 依赖少，通过注册顺序保证 |
| 刷新原子性 | 事务性（先创建再替换，失败全部回退） | 避免中间状态 |
| 懒加载 | `get()` 首次调用时创建 | 启动快，首次请求触发 |

### 4.4 注意：`get()` 的异步问题

`get()` 方法内部需要调用 `await self._provider.get_category()`，但 `get()` 本身不应该是 async 的（FastAPI `Depends` 需要同步函数）。

解决方案：`ComponentSlot.create()` 在 lifespan 阶段通过异步初始化完成，`get()` 只是返回已创建的实例。懒加载触发点改为 `registry.ensure_initialized(name)` 异步方法，在请求前的中间件或依赖中调用。

```python
async def ensure_initialized(self, name: str) -> Any:
    """确保组件已初始化（懒加载）。"""
    slot = self._slots.get(name)
    if slot is None:
        raise KeyError(f"Component '{name}' not registered")
    if not slot._initialized:
        config = await self._provider.get_category(slot._config_category)
        slot.create(config)
    return slot.get()
```

FastAPI 依赖：
```python
def get_agent(request: Request):
    return request.app.state.registry.get("agent")  # sync，已初始化

async def get_agent_async(request: Request):
    registry = request.app.state.registry
    return await registry.ensure_initialized("agent")  # async，懒加载
```

## 5. 组件注册清单

| 注册名 | factory 签名 | config_category | 说明 |
|--------|-------------|-----------------|------|
| `agent_llm` | `create_agent_llm(config: dict) → BaseChatModel` | `llm` | Agent 使用的 LLM |
| `rag_llm` | `create_rag_llm(config: dict) → BaseChatModel` | `rag_llm` | RAG 生成链使用的 LLM，fallback 到 llm |
| `embeddings` | `create_embeddings(config: dict) → HuggingFaceEmbeddings` | `embedding` | Embedding 模型 |
| `chroma_client` | `create_chroma_client(config: dict) → HttpClient` | `vectorstore` | Chroma HTTP Client |
| `vectorstore` | `create_vectorstore(config: dict) → Chroma` | `vectorstore` | Chroma VectorStore（内部获取 embeddings） |
| `agent` | `create_customer_agent(config: dict) → Agent` | `llm` | Agent 实例（内部获取 agent_llm） |

注册顺序（保证刷新时 agent_llm 在 agent 之前、embeddings 在 vectorstore 之前）：
`agent_llm` → `rag_llm` → `embeddings` → `chroma_client` → `vectorstore` → `agent`

### 5.1 VectorStore 跨分类处理

VectorStore 依赖 `embedding` 和 `vectorstore` 两个分类的配置。处理方式：
- VectorStore 的 `config_category` 设为 `vectorstore`
- factory 内部通过 `registry.get("embeddings")` 获取已创建的 embeddings 实例
- `embedding` 分类变更时，`refresh_category("embedding")` 同时刷新 `embeddings` 和 `vectorstore`（手动追加）

### 5.2 RAG LLM fallback

`rag_llm` 的 factory 实现回退逻辑：
```python
def create_rag_llm(config: dict) -> BaseChatModel:
    if not config:
        # rag_llm 分类无配置，回退到 llm 分类
        config = registry.get_category_sync("llm")  # 或由 Registry 传入
    return init_chat_model(**_build_llm_params(config, prefix="rag_llm"))
```

实际实现中，Registry 的 `refresh_category` 在发现 `rag_llm` 分类缓存为空时，自动回退读取 `llm` 分类。

## 6. 配置更新流程

```
PUT /api/config
    │
    ▼
update_configs(db, configs)
    │
    ├─ 1. 写入 DB，收集 changed_categories
    │
    └─ 2. _apply_config_changes(changed_categories)
              │
              ├─ config_provider.invalidate(category)  # 每个 changed category
              │
              ├─ registry.refresh_category(category)   # 事务性刷新
              │     │
              │     ├─ 为该分类下所有 slot 创建新实例
              │     ├─ 任一失败 → 全部回退 → 返回失败状态
              │     └─ 全部成功 → 统一替换 → 返回成功状态
              │
              ├─ 特殊处理：embedding 变更时额外刷新 vectorstore
              │
              └─ 返回生效结果（哪些成功、哪些失败）
```

### 6.1 API 响应增强

```python
@router.put("")
async def update_config(req, ...):
    ...
    result = await _apply_config_changes(changed_categories)
    return success(data={
        "updated": len(req.configs),
        "refresh_result": result,  # {"agent_llm": True, "agent": True, ...}
    })
```

## 7. 启动流程重构

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 1. DB 初始化
    async with mysql.engine.begin() as conn:
        await conn.run_sync(mysql.Base.metadata.create_all)

    # 2. 种子数据
    await _seed_initial_data()
    await _init_default_configs()

    # 3. 创建 ConfigProvider + Registry
    provider = AsyncConfigProvider(async_session_factory)
    registry = ComponentRegistry(provider)

    # 4. 注册组件（不触发创建）
    registry.register("agent_llm", create_agent_llm, "llm")
    registry.register("rag_llm", create_rag_llm, "rag_llm")
    registry.register("embeddings", create_embeddings, "embedding")
    registry.register("chroma_client", create_chroma_client, "vectorstore")
    registry.register("vectorstore", create_vectorstore, "vectorstore")
    registry.register("agent", create_customer_agent, "llm")

    _app.state.config_provider = provider
    _app.state.registry = registry

    yield  # ← 首次请求时懒加载创建组件

    # 5. 清理
    await mysql.engine.dispose()
```

## 8. 测试策略

| 层级 | 测试内容 | 方式 |
|------|---------|------|
| 单元 | AsyncConfigProvider 缓存命中/失效/重新读取 | mock DB session |
| 单元 | ComponentSlot 懒加载/原子替换/未初始化异常 | mock factory |
| 单元 | ComponentRegistry 注册/获取/事务性刷新/失败回退 | mock slot + provider |
| 单元 | factory 函数（create_agent_llm 等） | mock config dict |
| 集成 | 端到端：配置更新→新请求用新配置 | TestClient + 实际 DB |
| 集成 | SSE 流中配置更新→旧流继续 | TestClient SSE |
| 集成 | 配置更新失败→旧组件继续 | 无效 API Key |
| 集成 | Agent/RAG LLM 独立配置 | 不同模型配置 |

## 9. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 首次请求延迟 | 懒加载导致首次请求需要创建组件（可能数秒） | 可选异步预热：lifespan 结束前 `asyncio.create_task(registry.ensure_initialized("agent"))` |
| 事务性刷新耗时 | 多组件创建期间旧组件继续服务 | 创建是后台操作，不影响进行中请求 |
| VectorStore 跨分类 | embedding 变更需要同时刷新 vectorstore | `refresh_category("embedding")` 手动追加 vectorstore 刷新 |
| rag_llm 分类为空 | RAG LLM 需要回退到 llm 分类 | factory 内部检测空配置并回退 |
| 旧组件资源释放 | Python 引用计数确保旧组件在流结束后回收 | 无额外处理，依赖 GC |

## 10. Implementation Divergence

### D-1: refresh_category 刷新策略变更

**Design Doc 描述**：`refresh_category()` 实现事务性刷新——先创建所有新实例，全部成功后统一替换；任一失败则全部回退，保留旧实例。

**实际实现**：`refresh_category()` 采用逐个替换策略——按注册顺序逐个创建新实例并立即替换 `_current` 指针。部分失败时，已替换的组件保留新实例，未替换的继续使用旧实例。

**变更原因**：事务性全量替换会导致后续工厂闭包通过 `registry.get()` 获取到旧的前置组件。例如，当 `agent_llm` 和 `agent` 都需要刷新时，事务性替换会先创建新 agent（此时 `registry.get("agent_llm")` 返回旧实例），再统一替换——导致新 agent 绑定的是旧 agent_llm。逐个替换确保 `agent_llm` 先替换，`agent` 工厂闭包通过 `registry.get("agent_llm")` 获取到已更新的新实例。

**测试覆盖**：`test_registry_refresh_category_partial_failure_keeps_successful` 验证了部分失败时已替换组件保留的行为。

### D-2: invalidate 调用位置内聚化

**Design Doc 描述**：`_apply_config_changes()` 先调用 `config_provider.invalidate(category)`，再调用 `registry.refresh_category(category)`。

**实际实现**：`invalidate(category)` 在 `refresh_category()` 内部调用（第 196 行），`_apply_config_changes()` 不再显式调用 invalidate。

**变更原因**：将 invalidate 封装在 refresh_category 内部更内聚，避免调用方遗漏 invalidate 步骤。效果等价——refresh_category 先 invalidate 再读取，保证读取到最新配置。
