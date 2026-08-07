# RAG 模块设计文档

> 日期：2026-07-31
> 状态：已确认

## 概述

为智能客服系统实现 RAG（检索增强生成）模块，覆盖文档摄取、向量检索、重排序和回答生成的全链路。RAG 作为独立服务层，通过清晰接口与现有 Agent 和 API 集成。

## 技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| Embedding | 智谱 Embedding-3 | 通过 langchain-openai 的 OpenAIEmbeddings 适配（智谱 API 兼容 OpenAI 接口格式） |
| Reranker | 智谱 Reranker | HTTP API 调用，暂无 LangChain 官方适配器，自行封装 |
| 向量数据库 | Chroma | Client-Server 模式，服务端口 localhost:8000 |
| 文档加载 | PyPDFLoader / Docx2txtLoader / TextLoader | LangChain 社区加载器 |
| 文本分块 | RecursiveCharacterTextSplitter | chunk_size=512, chunk_overlap=64 |
| LLM | 智谱 GLM-4.5-air | 复用现有 create_llm() |

## 模块架构

```
rag/
├── __init__.py              # 模块入口，导出 ingest_document / retrieve
├── ingestion/
│   ├── __init__.py          # 导出 ingest_document / delete_from_vectorstore
│   ├── loader.py            # 文档加载器（PDF/Word/TXT）
│   ├── splitter.py          # 文本分块器
│   └── vectorstore.py       # 向量化 + Chroma 入库
├── retrieval/
│   ├── __init__.py          # 导出 retrieve
│   ├── retriever.py         # 向量检索 + Reranker 重排序
│   └── prompts.py           # RAG Prompt 模板
├── generation/
│   ├── __init__.py          # 导出 generate_answer
│   └── chain.py             # Prompt 组装 + LLM 生成回答
└── evaluation/
    └── __init__.py          # 评估模块（暂不实现，保留骨架）
```

### 核心接口

| 接口 | 位置 | 输入 | 输出 | 调用方 |
|------|------|------|------|--------|
| `ingest_document(file_path, file_type, doc_id)` | `rag/ingestion/` | 文件路径、类型、文档ID | 处理状态（成功/失败） | `services/knowledge.py` |
| `delete_from_vectorstore(doc_id)` | `rag/ingestion/` | 文档ID | 无 | `services/knowledge.py` |
| `retrieve(query, top_k=4)` | `rag/retrieval/` | 查询文本、返回数量 | `list[RetrievalResult]` | `agent/tools/`、`api/knowledge.py` |
| `generate_answer(query, context_chunks)` | `rag/generation/` | 查询 + 检索上下文 | `GenerationResult` | `agent/tools/` |

### 数据流

```
文档上传 → services/knowledge.py → rag.ingestion.ingest_document()
                                        ↓
                                   loader → splitter → embedding → chroma

用户提问 → agent/tools/knowledge_base_query → rag.retrieval.retrieve()
                                                  ↓
                                             chroma 检索 → reranker
                                                  ↓
                                             rag.generation.generate_answer()
                                                  ↓
                                             回答 + 来源引用
```

## Ingestion 摄取模块

### 文档加载器（loader.py）

根据文件类型选择对应的 LangChain DocumentLoader：
- PDF → `PyPDFLoader`
- DOCX/DOC → `Docx2txtLoader`
- TXT → `TextLoader`

加载后统一输出 `list[Document]`，每个 Document 包含 `page_content` 和 `metadata`（来源文件名、页码等）。

### 文本分块器（splitter.py）

使用 `RecursiveCharacterTextSplitter`：
- `chunk_size=512`
- `chunk_overlap=64`
- 分隔符优先级：`["\n\n", "\n", "。", "！", "？", ".", " ", ""]`（中文友好）
- 每个 chunk 的 metadata 继承父文档 metadata，追加 `chunk_index`

### 向量化与入库（vectorstore.py）

- Embedding：智谱 `embedding-3`，通过 `OpenAIEmbeddings` 适配
- Chroma 集合名：`knowledge_base`（可配置）
- 每个 chunk 存入 Chroma 时携带 metadata：`{doc_id, filename, chunk_index, file_type}`
- Chroma Client-Server 模式，连接 `localhost:8000`

### 异步处理流程

`ingest_document()` 被 `services/knowledge.py` 通过 `asyncio.create_task()` 调用：
1. 更新文档状态为 `processing`
2. 加载文档 → 分块 → 向量化 → 入库
3. 更新 `chunk_count` 和状态为 `ready`
4. 任何步骤失败 → 更新状态为 `failed`，记录错误日志

### 错误处理

- 不支持的文件类型 → 抛出 `ValueError`
- 文件读取失败 → 记录日志，状态设为 `failed`
- Chroma 连接失败 → 记录日志，状态设为 `failed`
- Embedding API 调用失败 → 重试 2 次后标记 `failed`

## Retrieval 检索模块

### 向量检索（retriever.py）

1. 用户问题 → 智谱 Embedding-3 向量化
2. Chroma `similarity_search_with_relevance_scores()`，初始检索 `top_k * 3` 条（扩大候选集供 Reranker 筛选）
3. 过滤相关性分数低于阈值（0.3）的结果
4. 送入 Reranker 重排序，取 Top-K（默认 4）条

### Reranker 重排序

- 使用智谱 Reranker API，通过 HTTP 请求调用（自行封装，暂无 LangChain 官方适配器）
- 输入：query + 候选文档列表
- 输出：按相关性重排序的文档列表 + 重排序分数
- 取重排序后 Top-K 条作为最终检索结果

### 检索结果格式

```python
@dataclass
class RetrievalResult:
    content: str           # 文档块内容
    score: float           # 重排序分数
    metadata: dict         # {doc_id, filename, chunk_index, file_type}
```

### RAG Prompt 模板（prompts.py）

```
你是一个专业的客服助手。请根据以下参考资料回答用户的问题。
如果参考资料中没有相关信息，请诚实说明你无法回答，不要编造内容。
回答时请在末尾标注信息来源。

参考资料：
{context}

用户问题：{question}
```

## Generation 生成模块

### 回答生成（chain.py）

1. 将检索到的 chunks 按分数排序，拼接为上下文字符串，每个 chunk 标注来源编号
2. 填充 Prompt 模板（context + question）
3. 调用 `create_llm()` 生成回答
4. 从回答中提取来源引用信息

### 上下文组装格式

```
[来源1] 文件：退货政策.pdf | 内容：退货政策：商品签收后7天内...
[来源2] 文件：配送说明.pdf | 内容：配送说明：全国大部分地区...
```

### 返回格式

```python
@dataclass
class GenerationResult:
    answer: str                    # LLM 生成的回答
    sources: list[dict]            # 引用来源列表 [{filename, chunk_index, score}]
```

## 集成改造

### services/knowledge.py

- `upload_document()`：文件保存和数据库记录创建后，调用 `asyncio.create_task(_process_document(...))` 触发异步处理
- `_process_document()`：调用 `rag.ingestion.ingest_document()`，处理完成后更新 `chunk_count` 和 `status`
- `delete_document()`：删除文件和数据库记录后，调用 `rag.ingestion.delete_from_vectorstore(doc_id)` 清除 Chroma 中对应向量
- `query_knowledge()`：调用 `rag.retrieve()` + `rag.generate_answer()` 替换空占位实现

### agent/tools/__init__.py

- `knowledge_base_query` 工具从 Mock 实现改为调用 `rag.retrieval.retrieve()` + `rag.generation.generate_answer()`
- 返回格式：回答文本 + 来源引用信息

### configs/config.py 新增

```python
# ========== Chroma ==========
CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "knowledge_base")

# ========== RAG ==========
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "4"))
RAG_CHUNK_SIZE: int = int(os.getenv("RAG_CHUNK_SIZE", "512"))
RAG_CHUNK_OVERLAP: int = int(os.getenv("RAG_CHUNK_OVERLAP", "64"))
RAG_SCORE_THRESHOLD: float = float(os.getenv("RAG_SCORE_THRESHOLD", "0.3"))
```

### .env 新增

```
# ========== Chroma ==========
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_COLLECTION=knowledge_base

# ========== RAG ==========
RAG_TOP_K=4
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=64
RAG_SCORE_THRESHOLD=0.3
```

### 依赖新增（pyproject.toml）

```
chromadb>=0.4.0
langchain-community>=0.1.0
pypdf>=4.0.0
docx2txt>=0.8
```

### app/lifespan.py

- 启动时初始化 Chroma 连接，验证连通性
- 将 Chroma client 存入 `app.state` 供后续使用

### evaluation 模块

保留空骨架，暂不实现，后续可扩展检索质量和回答质量评估。
