# RAG 模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的 RAG 模块，覆盖文档摄取、向量检索、重排序和回答生成，替换现有的 Mock 实现。

**Architecture:** RAG 作为独立服务层，位于 `apps/service/rag/`，对外暴露 `ingest_document()`、`delete_from_vectorstore()`、`retrieve()`、`generate_answer()` 四个核心接口。通过 Chroma Client-Server 存储向量，智谱 Embedding-3 做向量化，智谱 Reranker 做重排序（可降级跳过）。

**Tech Stack:** LangChain 1.x, langchain-openai (OpenAIEmbeddings 适配智谱), ChromaDB, httpx (Reranker HTTP 调用), PyPDFLoader, Docx2txtLoader, TextLoader

## Global Constraints

- Embedding 模型名: `embedding-3`，通过 `langchain_openai.OpenAIEmbeddings` + 智谱 base_url 适配
- Chroma Client-Server 模式，默认 `localhost:8000`
- 文本分块: chunk_size=512, chunk_overlap=64, 中文友好分隔符
- 检索: 初始 top_k*3 候选 → Reranker 重排序 → 取 Top-K(默认4)
- 智谱 Reranker API 端点: `POST {ZAI_BASE_URL}rerank`，模型名待确认（当前账户暂不可用），设计为可降级
- 异步文档处理: `asyncio.create_task()` 触发，完成后更新数据库状态
- 所有配置项通过 `configs/config.py` + `.env` 管理

---

## File Structure

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| Modify | `apps/service/configs/config.py` | 新增 Chroma 和 RAG 配置项 |
| Modify | `apps/service/.env` | 新增 Chroma 和 RAG 环境变量 |
| Modify | `apps/service/pyproject.toml` | 新增 chromadb、langchain-community、pypdf、docx2txt 依赖 |
| Create | `apps/service/rag/ingestion/loader.py` | 文档加载器（PDF/Word/TXT） |
| Create | `apps/service/rag/ingestion/splitter.py` | 文本分块器 |
| Create | `apps/service/rag/ingestion/vectorstore.py` | 向量化 + Chroma 入库 + 删除 |
| Modify | `apps/service/rag/ingestion/__init__.py` | 导出 ingest_document / delete_from_vectorstore |
| Create | `apps/service/rag/retrieval/retriever.py` | 向量检索 + Reranker 重排序 |
| Create | `apps/service/rag/retrieval/prompts.py` | RAG Prompt 模板 |
| Modify | `apps/service/rag/retrieval/__init__.py` | 导出 retrieve |
| Create | `apps/service/rag/generation/chain.py` | Prompt 组装 + LLM 生成回答 |
| Modify | `apps/service/rag/generation/__init__.py` | 导出 generate_answer |
| Modify | `apps/service/rag/__init__.py` | 模块入口导出 |
| Modify | `apps/service/rag/evaluation/__init__.py` | 保留空骨架 |
| Modify | `apps/service/models/embedding.py` | 实现 create_embeddings() |
| Modify | `apps/service/services/knowledge.py` | 接入 RAG 摄取/检索/生成 |
| Modify | `apps/service/agent/tools/__init__.py` | knowledge_base_query 从 Mock 改为调用 RAG |
| Modify | `apps/service/app/lifespan.py` | 启动时初始化 Chroma 连接 |
| Modify | `apps/service/app/dependencies.py` | 新增 get_chroma_client 依赖 |

---

### Task 1: 配置与依赖

**Files:**
- Modify: `apps/service/configs/config.py`
- Modify: `apps/service/.env`
- Modify: `apps/service/pyproject.toml`

**Interfaces:**
- Consumes: 无
- Produces: `settings.CHROMA_HOST`, `settings.CHROMA_PORT`, `settings.CHROMA_COLLECTION`, `settings.RAG_TOP_K`, `settings.RAG_CHUNK_SIZE`, `settings.RAG_CHUNK_OVERLAP`, `settings.RAG_SCORE_THRESHOLD`

- [ ] **Step 1: 在 config.py 中新增 Chroma 和 RAG 配置项**

在 `configs/config.py` 的 `Settings` 类中，`# ========== Admin ==========` 之前追加：

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

- [ ] **Step 2: 在 .env 中新增对应环境变量**

在 `.env` 文件末尾追加：

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

- [ ] **Step 3: 在 pyproject.toml 中新增依赖**

在 `dependencies` 列表中追加：

```toml
    "chromadb>=0.4.0",
    "langchain-chroma>=0.2.0",
    "langchain-community>=0.1.0",
    "langchain-text-splitters>=0.3.0",
    "pypdf>=4.0.0",
    "docx2txt>=0.8",
```

- [ ] **Step 4: 安装新依赖**

Run: `cd apps/service && uv sync`

- [ ] **Step 5: 验证安装成功**

Run: `cd apps/service && .venv/bin/python -c "import chromadb; import pypdf; import docx2txt; import langchain_chroma; import langchain_text_splitters; print('OK')"`

Expected: 输出 `OK`

- [ ] **Step 6: Commit**

```bash
git add apps/service/configs/config.py apps/service/.env apps/service/pyproject.toml apps/service/uv.lock
git commit -m "feat: add Chroma and RAG config items and dependencies"
```

---

### Task 2: Embedding 模型封装

**Files:**
- Modify: `apps/service/models/embedding.py`
- Modify: `apps/service/models/reranker.py`

**Interfaces:**
- Consumes: `settings.ZAI_API_KEY`, `settings.ZAI_BASE_URL`
- Produces: `create_embeddings()` → `OpenAIEmbeddings` 实例, `create_reranker()` → `ZhipuReranker` 实例

- [ ] **Step 1: 实现 create_embeddings()**

将 `apps/service/models/embedding.py` 替换为：

```python
"""Embedding 模型 —— 通过 langchain-openai 适配智谱 Embedding-3。"""

from langchain_openai import OpenAIEmbeddings

from configs.config import settings


def create_embeddings() -> OpenAIEmbeddings:
    """创建智谱 Embedding-3 实例。

    智谱 API 兼容 OpenAI 接口格式，可通过 OpenAIEmbeddings 适配。
    """
    return OpenAIEmbeddings(
        model="embedding-3",
        api_key=settings.ZAI_API_KEY,
        base_url=settings.ZAI_BASE_URL,
    )
```

- [ ] **Step 2: 实现 ZhipuReranker 封装**

将 `apps/service/models/reranker.py` 替换为：

```python
"""Reranker 模型 —— 封装智谱 Reranker API。

智谱 Reranker 暂无 LangChain 官方适配器，通过 HTTP 请求直接调用。
当 API 不可用时自动降级，跳过重排序步骤。
"""

import logging

import httpx

from configs.config import settings

logger = logging.getLogger("ai-service.reranker")


class ZhipuReranker:
    """智谱 Reranker 客户端，支持降级。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "reranker",
        top_n: int = 4,
    ):
        self.api_key = api_key or settings.ZAI_API_KEY
        self.base_url = base_url or settings.ZAI_BASE_URL
        self.model = model
        self.top_n = top_n
        self._available: bool | None = None

    async def rerank(
        self, query: str, documents: list[str], top_n: int | None = None
    ) -> list[dict]:
        """对文档列表进行重排序。

        Args:
            query: 查询文本
            documents: 候选文档内容列表
            top_n: 返回前 N 个结果，默认使用构造参数

        Returns:
            重排序结果列表，每项包含 index、relevance_score、text。
            如果 API 不可用，返回原始顺序（降级）。
        """
        if not documents:
            return []

        n = top_n or self.top_n

        # 如果已知不可用，直接降级
        if self._available is False:
            logger.debug("Reranker 不可用，跳过重排序")
            return [
                {"index": i, "relevance_score": 1.0 - i * 0.01, "text": doc}
                for i, doc in enumerate(documents[:n])
            ]

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}rerank",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "query": query,
                        "documents": documents,
                        "top_n": n,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                self._available = True
                return data.get("results", [])
        except Exception as e:
            if self._available is None:
                logger.warning(
                    "Reranker API 调用失败，后续将跳过重排序: %s", e
                )
                self._available = False
            else:
                logger.debug("Reranker 调用失败: %s", e)
            # 降级：返回原始顺序
            return [
                {"index": i, "relevance_score": 1.0 - i * 0.01, "text": doc}
                for i, doc in enumerate(documents[:n])
            ]


def create_reranker(top_n: int = 4) -> ZhipuReranker:
    """创建智谱 Reranker 实例。"""
    return ZhipuReranker(top_n=top_n)
```

- [ ] **Step 3: 验证模块可导入**

Run: `cd apps/service && .venv/bin/python -c "from models.embedding import create_embeddings; from models.reranker import create_reranker; print('OK')"`

Expected: 输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add apps/service/models/embedding.py apps/service/models/reranker.py
git commit -m "feat: implement embedding and reranker model wrappers"
```

---

### Task 3: Ingestion 摄取模块

**Files:**
- Create: `apps/service/rag/ingestion/loader.py`
- Create: `apps/service/rag/ingestion/splitter.py`
- Create: `apps/service/rag/ingestion/vectorstore.py`
- Modify: `apps/service/rag/ingestion/__init__.py`

**Interfaces:**
- Consumes: `create_embeddings()` from Task 2, `settings.CHROMA_HOST/PORT/COLLECTION/RAG_CHUNK_SIZE/RAG_CHUNK_OVERLAP`
- Produces: `ingest_document(file_path, file_type, doc_id, filename)`, `delete_from_vectorstore(doc_id)`, `get_vectorstore()`

- [ ] **Step 1: 实现 loader.py**

创建 `apps/service/rag/ingestion/loader.py`：

```python
"""文档加载器 —— 根据文件类型选择对应的 LangChain DocumentLoader。"""

import logging

from langchain_core.documents import Document

logger = logging.getLogger("ai-service.rag.loader")


def load_document(file_path: str, file_type: str) -> list[Document]:
    """加载文档，返回 LangChain Document 列表。

    Args:
        file_path: 文件绝对路径
        file_type: 文件类型（pdf/docx/doc/txt）

    Returns:
        Document 列表，每个包含 page_content 和 metadata

    Raises:
        ValueError: 不支持的文件类型
        FileNotFoundError: 文件不存在
    """
    if file_type == "pdf":
        from langchain_community.document_loaders import PyPDFLoader

        loader = PyPDFLoader(file_path)
        docs = loader.load()
        for doc in docs:
            doc.metadata.setdefault("file_type", "pdf")
        return docs

    elif file_type in ("docx", "doc"):
        from langchain_community.document_loaders import Docx2txtLoader

        loader = Docx2txtLoader(file_path)
        docs = loader.load()
        for doc in docs:
            doc.metadata.setdefault("file_type", file_type)
        return docs

    elif file_type == "txt":
        from langchain_community.document_loaders import TextLoader

        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
        for doc in docs:
            doc.metadata.setdefault("file_type", "txt")
        return docs

    else:
        raise ValueError(
            f"不支持的文件类型: {file_type}，仅支持 pdf/docx/doc/txt"
        )
```

- [ ] **Step 2: 实现 splitter.py**

创建 `apps/service/rag/ingestion/splitter.py`：

```python
"""文本分块器 —— 使用 RecursiveCharacterTextSplitter 切分文档。"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from configs.config import settings


def split_documents(
    documents: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """将文档列表切分为更小的块。

    Args:
        documents: 原始文档列表
        chunk_size: 块大小，默认使用配置值
        chunk_overlap: 重叠大小，默认使用配置值

    Returns:
        切分后的文档块列表，每个块附带 chunk_index metadata
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.RAG_CHUNK_SIZE,
        chunk_overlap=chunk_overlap or settings.RAG_CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", ".", " ", ""],
        length_function=len,
    )

    chunks = splitter.split_documents(documents)

    # 为每个块追加 chunk_index
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i

    return chunks
```

- [ ] **Step 3: 实现 vectorstore.py**

创建 `apps/service/rag/ingestion/vectorstore.py`：

```python
"""向量化与 Chroma 入库 —— 文档块 Embedding + Chroma 存储/删除。"""

import logging

import chromadb
from langchain_core.documents import Document
from langchain_chroma import Chroma

from configs.config import settings
from models.embedding import create_embeddings

logger = logging.getLogger("ai-service.rag.vectorstore")


def get_chroma_client() -> chromadb.HttpClient:
    """获取 Chroma HTTP Client 实例。"""
    return chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
    )


def get_vectorstore() -> Chroma:
    """获取 Chroma VectorStore 实例（LangChain 封装）。"""
    embeddings = create_embeddings()
    client = get_chroma_client()
    return Chroma(
        client=client,
        collection_name=settings.CHROMA_COLLECTION,
        embedding_function=embeddings,
    )


async def add_documents_to_vectorstore(
    documents: list[Document], doc_id: int, filename: str
) -> int:
    """将文档块向量化并存入 Chroma。

    Args:
        documents: 切分后的文档块列表
        doc_id: 文档数据库 ID
        filename: 原始文件名

    Returns:
        入库的块数量
    """
    if not documents:
        return 0

    # 为每个块追加 doc_id 和 filename metadata
    for doc in documents:
        doc.metadata["doc_id"] = doc_id
        doc.metadata["filename"] = filename

    vectorstore = get_vectorstore()
    vectorstore.add_documents(documents)
    logger.info(
        "文档 %s (id=%d) 共 %d 个块已入库",
        filename, doc_id, len(documents),
    )
    return len(documents)


async def delete_from_vectorstore(doc_id: int) -> None:
    """从 Chroma 中删除指定文档的所有向量。

    Args:
        doc_id: 文档数据库 ID
    """
    try:
        client = get_chroma_client()
        collection = client.get_collection(settings.CHROMA_COLLECTION)
        # 通过 metadata 过滤删除指定文档的向量
        collection.delete(
            where={"doc_id": doc_id},
        )
        logger.info("文档 id=%d 的向量已从 Chroma 删除", doc_id)
    except Exception as e:
        logger.warning("从 Chroma 删除文档 id=%d 向量失败: %s", doc_id, e)
```

- [ ] **Step 4: 更新 ingestion/__init__.py**

将 `apps/service/rag/ingestion/__init__.py` 替换为：

```python
"""RAG 文档摄取模块 —— 负责文档加载、清洗、切片和向量化。"""

import logging

from rag.ingestion.loader import load_document
from rag.ingestion.splitter import split_documents
from rag.ingestion.vectorstore import (
    add_documents_to_vectorstore,
    delete_from_vectorstore,
    get_vectorstore,
)

logger = logging.getLogger("ai-service.rag.ingestion")


async def ingest_document(
    file_path: str, file_type: str, doc_id: int, filename: str
) -> int:
    """完整摄取流程：加载 → 分块 → 向量化 → 入库。

    Args:
        file_path: 文件绝对路径
        file_type: 文件类型（pdf/docx/doc/txt）
        doc_id: 文档数据库 ID
        filename: 原始文件名

    Returns:
        入库的块数量

    Raises:
        ValueError: 不支持的文件类型
        FileNotFoundError: 文件不存在
    """
    # 1. 加载文档
    logger.info("开始加载文档: %s (type=%s)", filename, file_type)
    documents = load_document(file_path, file_type)
    logger.info("文档加载完成，共 %d 页/段", len(documents))

    # 2. 文本分块
    chunks = split_documents(documents)
    logger.info("文本分块完成，共 %d 个块", len(chunks))

    # 3. 向量化 + 入库
    chunk_count = await add_documents_to_vectorstore(chunks, doc_id, filename)
    logger.info("文档摄取完成: %s, %d 个块已入库", filename, chunk_count)

    return chunk_count


__all__ = [
    "ingest_document",
    "delete_from_vectorstore",
    "get_vectorstore",
]
```

- [ ] **Step 5: 验证模块可导入**

Run: `cd apps/service && .venv/bin/python -c "from rag.ingestion import ingest_document, delete_from_vectorstore, get_vectorstore; print('OK')"`

Expected: 输出 `OK`

- [ ] **Step 6: Commit**

```bash
git add apps/service/rag/ingestion/
git commit -m "feat: implement RAG ingestion module (loader, splitter, vectorstore)"
```

---

### Task 4: Retrieval 检索模块

**Files:**
- Create: `apps/service/rag/retrieval/retriever.py`
- Create: `apps/service/rag/retrieval/prompts.py`
- Modify: `apps/service/rag/retrieval/__init__.py`

**Interfaces:**
- Consumes: `get_vectorstore()` from Task 3, `create_reranker()` from Task 2, `settings.RAG_TOP_K/RAG_SCORE_THRESHOLD`
- Produces: `retrieve(query, top_k)` → `list[RetrievalResult]`, `RAG_PROMPT_TEMPLATE` from prompts.py

- [ ] **Step 1: 实现 prompts.py**

创建 `apps/service/rag/retrieval/prompts.py`：

```python
"""RAG 检索相关 Prompt 模板。"""

RAG_PROMPT_TEMPLATE = """\
你是一个专业的客服助手。请根据以下参考资料回答用户的问题。
如果参考资料中没有相关信息，请诚实说明你无法回答，不要编造内容。
回答时请在末尾标注信息来源。

参考资料：
{context}

用户问题：{question}
"""
```

- [ ] **Step 2: 实现 retriever.py**

创建 `apps/service/rag/retrieval/retriever.py`：

```python
"""RAG 检索模块 —— 向量搜索 + Reranker 重排序。"""

import logging
from dataclasses import dataclass, field

from configs.config import settings
from models.reranker import create_reranker
from rag.ingestion.vectorstore import get_vectorstore

logger = logging.getLogger("ai-service.rag.retrieval")


@dataclass
class RetrievalResult:
    """单条检索结果。"""

    content: str
    score: float
    metadata: dict = field(default_factory=dict)


async def retrieve(
    query: str, top_k: int | None = None
) -> list[RetrievalResult]:
    """检索与查询最相关的文档块。

    流程：问题向量化 → Chroma 相似度检索(top_k*3) → 过滤低分 → Reranker 重排序 → 取 Top-K

    Args:
        query: 用户查询文本
        top_k: 返回结果数量，默认使用配置值

    Returns:
        检索结果列表，按相关性排序
    """
    k = top_k or settings.RAG_TOP_K

    # 1. Chroma 相似度检索，扩大候选集
    vectorstore = get_vectorstore()
    candidate_count = k * 3
    raw_results = vectorstore.similarity_search_with_relevance_scores(
        query, k=candidate_count
    )

    if not raw_results:
        logger.info("检索无结果: query=%s", query[:50])
        return []

    # 2. 过滤低分结果
    filtered = [
        (doc, score)
        for doc, score in raw_results
        if score >= settings.RAG_SCORE_THRESHOLD
    ]

    if not filtered:
        logger.info(
            "检索结果全低于阈值 %.2f: query=%s",
            settings.RAG_SCORE_THRESHOLD,
            query[:50],
        )
        return []

    logger.info(
        "Chroma 检索: %d 条原始结果, %d 条过滤后",
        len(raw_results), len(filtered),
    )

    # 3. Reranker 重排序
    candidate_texts = [doc.page_content for doc, _ in filtered]
    candidate_meta = [doc.metadata for doc, _ in filtered]

    reranker = create_reranker(top_n=k)
    rerank_results = await reranker.rerank(query, candidate_texts, top_n=k)

    # 4. 组装最终结果
    results: list[RetrievalResult] = []
    for item in rerank_results:
        idx = item["index"]
        results.append(
            RetrievalResult(
                content=item.get("text", candidate_texts[idx]),
                score=item["relevance_score"],
                metadata=candidate_meta[idx],
            )
        )

    logger.info("检索完成: %d 条最终结果", len(results))
    return results
```

- [ ] **Step 3: 更新 retrieval/__init__.py**

将 `apps/service/rag/retrieval/__init__.py` 替换为：

```python
"""RAG 检索模块 —— 负责向量搜索、混合检索和重排序。"""

from rag.retrieval.retriever import RetrievalResult, retrieve

__all__ = ["retrieve", "RetrievalResult"]
```

- [ ] **Step 4: 验证模块可导入**

Run: `cd apps/service && .venv/bin/python -c "from rag.retrieval import retrieve, RetrievalResult; print('OK')"`

Expected: 输出 `OK`

- [ ] **Step 5: Commit**

```bash
git add apps/service/rag/retrieval/
git commit -m "feat: implement RAG retrieval module with reranker support"
```

---

### Task 5: Generation 生成模块

**Files:**
- Create: `apps/service/rag/generation/chain.py`
- Modify: `apps/service/rag/generation/__init__.py`

**Interfaces:**
- Consumes: `retrieve()` → `list[RetrievalResult]` from Task 4, `RAG_PROMPT_TEMPLATE` from Task 4, `create_llm()` from `models/factory.py`
- Produces: `generate_answer(query, context_chunks)` → `GenerationResult`

- [ ] **Step 1: 实现 chain.py**

创建 `apps/service/rag/generation/chain.py`：

```python
"""RAG 生成模块 —— Prompt 组装 + LLM 回答生成。"""

import logging
from dataclasses import dataclass, field

from langchain_core.output_parsers import StrOutputParser

from models.factory import create_llm
from rag.retrieval.prompts import RAG_PROMPT_TEMPLATE
from rag.retrieval.retriever import RetrievalResult

logger = logging.getLogger("ai-service.rag.generation")


@dataclass
class GenerationResult:
    """生成结果。"""

    answer: str
    sources: list[dict] = field(default_factory=list)


def _format_context(chunks: list[RetrievalResult]) -> str:
    """将检索结果格式化为上下文字符串。

    格式：
    [来源1] 文件：退货政策.pdf | 内容：退货政策：...
    [来源2] 文件：配送说明.pdf | 内容：配送说明：...
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        filename = chunk.metadata.get("filename", "未知文档")
        content = chunk.content.strip()
        parts.append(f"[来源{i}] 文件：{filename} | 内容：{content}")
    return "\n".join(parts)


def _extract_sources(chunks: list[RetrievalResult]) -> list[dict]:
    """从检索结果中提取来源信息。"""
    return [
        {
            "filename": chunk.metadata.get("filename", "未知文档"),
            "chunk_index": chunk.metadata.get("chunk_index", 0),
            "score": round(chunk.score, 4),
        }
        for chunk in chunks
    ]


async def generate_answer(
    query: str, context_chunks: list[RetrievalResult]
) -> GenerationResult:
    """基于检索结果生成回答。

    Args:
        query: 用户问题
        context_chunks: 检索结果列表

    Returns:
        GenerationResult 包含回答文本和来源引用
    """
    if not context_chunks:
        return GenerationResult(
            answer="抱歉，我在知识库中没有找到相关信息，无法回答您的问题。",
            sources=[],
        )

    # 组装上下文
    context = _format_context(context_chunks)

    # 填充 Prompt
    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=query)

    # 调用 LLM
    llm = create_llm()
    chain = llm | StrOutputParser()
    answer = await chain.ainvoke(prompt)

    # 提取来源
    sources = _extract_sources(context_chunks)

    logger.info("RAG 回答生成完成, 来源数: %d", len(sources))
    return GenerationResult(answer=answer, sources=sources)
```

- [ ] **Step 2: 更新 generation/__init__.py**

将 `apps/service/rag/generation/__init__.py` 替换为：

```python
"""RAG 生成模块 —— 负责 Prompt 组装、上下文构建和 LLM 回答。"""

from rag.generation.chain import GenerationResult, generate_answer

__all__ = ["generate_answer", "GenerationResult"]
```

- [ ] **Step 3: 验证模块可导入**

Run: `cd apps/service && .venv/bin/python -c "from rag.generation import generate_answer, GenerationResult; print('OK')"`

Expected: 输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add apps/service/rag/generation/
git commit -m "feat: implement RAG generation module"
```

---

### Task 6: RAG 模块入口

**Files:**
- Modify: `apps/service/rag/__init__.py`
- Modify: `apps/service/rag/evaluation/__init__.py`

**Interfaces:**
- Consumes: Task 3/4/5 的导出
- Produces: `rag.ingest_document()`, `rag.delete_from_vectorstore()`, `rag.retrieve()`, `rag.generate_answer()`

- [ ] **Step 1: 更新 rag/__init__.py**

将 `apps/service/rag/__init__.py` 替换为：

```python
"""RAG 模块 —— 检索增强生成，覆盖文档摄取、检索、生成全链路。"""

from rag.ingestion import ingest_document, delete_from_vectorstore
from rag.retrieval import retrieve, RetrievalResult
from rag.generation import generate_answer, GenerationResult

__all__ = [
    "ingest_document",
    "delete_from_vectorstore",
    "retrieve",
    "RetrievalResult",
    "generate_answer",
    "GenerationResult",
]
```

- [ ] **Step 2: 更新 evaluation/__init__.py**

将 `apps/service/rag/evaluation/__init__.py` 替换为：

```python
"""RAG 评估模块 —— 负责检索质量和回答质量的评估。

暂不实现，保留骨架供后续扩展。
"""
```

- [ ] **Step 3: 验证模块整体可导入**

Run: `cd apps/service && .venv/bin/python -c "from rag import ingest_document, delete_from_vectorstore, retrieve, generate_answer, RetrievalResult, GenerationResult; print('OK')"`

Expected: 输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add apps/service/rag/__init__.py apps/service/rag/evaluation/__init__.py
git commit -m "feat: add RAG module entry point exports"
```

---

### Task 7: 集成 — services/knowledge.py 接入 RAG

**Files:**
- Modify: `apps/service/services/knowledge.py`

**Interfaces:**
- Consumes: `ingest_document()` from Task 3, `delete_from_vectorstore()` from Task 3, `retrieve()` from Task 4, `generate_answer()` from Task 5, `settings.RAG_TOP_K`

- [ ] **Step 1: 重写 services/knowledge.py**

将 `apps/service/services/knowledge.py` 替换为：

```python
"""知识库业务逻辑 —— 文档上传、查询、删除、检索测试。"""

import asyncio
import logging
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.document import Document
from configs.config import settings
from rag.ingestion import ingest_document, delete_from_vectorstore
from rag.retrieval import retrieve
from rag.generation import generate_answer

logger = logging.getLogger("ai-service.knowledge")

# 文件上传存储目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的文件类型
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}


def _get_file_extension(filename: str) -> str:
    """获取文件扩展名（小写）"""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def _process_document(
    db: AsyncSession, doc_id: int, file_path: str, file_type: str, filename: str
) -> None:
    """异步处理文档：解析 → 分块 → 向量化 → 入库。更新文档状态。"""
    try:
        chunk_count = await ingest_document(file_path, file_type, doc_id, filename)
        # 更新文档状态和块数量
        result = await db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if doc:
            doc.chunk_count = chunk_count
            doc.status = "ready"
            await db.commit()
            logger.info("文档处理完成: id=%d, chunks=%d", doc_id, chunk_count)
    except Exception as e:
        logger.error("文档处理失败: id=%d, error=%s", doc_id, e)
        result = await db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = "failed"
            await db.commit()


async def upload_document(
    db: AsyncSession,
    filename: str,
    file_content: bytes,
    uploaded_by: int | None = None,
) -> Document:
    """保存上传文件并创建文档记录，触发异步处理。"""
    ext = _get_file_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}")

    # 生成唯一文件名避免冲突
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    # 写入文件
    with open(file_path, "wb") as f:
        f.write(file_content)

    # 创建数据库记录
    doc = Document(
        filename=filename,
        file_path=file_path,
        file_type=ext,
        chunk_count=0,
        status="processing",
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 触发异步文档处理
    asyncio.create_task(
        _process_document(db, doc.id, file_path, ext, filename)
    )

    return doc


async def get_documents(db: AsyncSession) -> list[Document]:
    """获取所有文档列表，按上传时间倒序"""
    result = await db.execute(
        select(Document).order_by(Document.uploaded_at.desc())
    )
    return list(result.scalars().all())


async def get_document_by_id(db: AsyncSession, document_id: int) -> Document | None:
    """根据 ID 获取文档"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    return result.scalar_one_or_none()


async def delete_document(db: AsyncSession, document_id: int) -> bool:
    """删除文档记录、文件及向量，返回是否成功"""
    doc = await get_document_by_id(db, document_id)
    if not doc:
        return False

    # 删除文件
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # 从向量数据库删除对应向量
    await delete_from_vectorstore(document_id)

    await db.delete(doc)
    await db.commit()
    return True


async def query_knowledge(question: str) -> dict:
    """知识库检索测试 —— RAG 检索 + 生成回答"""
    # 1. 检索
    chunks = await retrieve(question, top_k=settings.RAG_TOP_K)

    # 2. 生成回答
    result = await generate_answer(question, chunks)

    # 3. 格式化返回
    return {
        "chunks": [
            {
                "content": chunk.content,
                "score": round(chunk.score, 4),
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ],
        "answer": result.answer,
        "sources": result.sources,
    }
```

- [ ] **Step 2: 验证模块可导入**

Run: `cd apps/service && .venv/bin/python -c "from services.knowledge import upload_document, get_documents, delete_document, query_knowledge; print('OK')"`

Expected: 输出 `OK`

- [ ] **Step 3: Commit**

```bash
git add apps/service/services/knowledge.py
git commit -m "feat: integrate RAG into knowledge service (async ingestion + retrieval + generation)"
```

---

### Task 8: 集成 — Agent 工具接入 RAG

**Files:**
- Modify: `apps/service/agent/tools/__init__.py`

**Interfaces:**
- Consumes: `retrieve()` from Task 4, `generate_answer()` from Task 5, `settings.RAG_TOP_K`

- [ ] **Step 1: 重写 knowledge_base_query 工具**

将 `apps/service/agent/tools/__init__.py` 中的 `knowledge_base_query` 函数替换为（保留其余所有工具和 Mock 数据不变）：

将原函数：
```python
@tool
def knowledge_base_query(query: str) -> str:
    """..."""
    # 当前为 Mock 实现
    query_lower = query.lower()
    matched = []
    for key, content in _MOCK_KNOWLEDGE.items():
        if key in query_lower or any(kw in query_lower for kw in content[:20].lower()):
            matched.append(content)
    if matched:
        return "\n\n---\n\n".join(matched)
    return "\n\n---\n\n".join(_MOCK_KNOWLEDGE.values())
```

替换为：
```python
@tool
def knowledge_base_query(query: str) -> str:
    """当用户询问业务规则、产品信息、退货政策、配送说明、会员权益等知识性问题时使用此工具。
    输入为用户的完整问题，工具会检索知识库中与问题最相关的文档片段并返回。

    触发条件示例：
    - "退货政策是什么？"
    - "配送需要多长时间？"
    - "你们有什么产品？"
    - "会员有什么权益？"
    """
    import asyncio
    from rag.retrieval import retrieve
    from rag.generation import generate_answer
    from configs.config import settings

    # 在同步工具中运行异步检索
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已在异步上下文中（如 LangGraph），用 asyncio.run_coroutine_threadsafe
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                chunks = pool.submit(asyncio.run, retrieve(query, top_k=settings.RAG_TOP_K)).result()
                result = pool.submit(asyncio.run, generate_answer(query, chunks)).result()
        else:
            chunks = asyncio.run(retrieve(query, top_k=settings.RAG_TOP_K))
            result = asyncio.run(generate_answer(query, chunks))
    except Exception as e:
        logger.error("RAG 检索失败: %s", e)
        return "知识库检索暂时不可用，请稍后重试。"

    if not result.sources:
        return "在知识库中未找到相关信息。"

    # 组装来源信息
    sources_text = "、".join(s["filename"] for s in result.sources)
    return f"{result.answer}\n\n[来源：{sources_text}]"
```

同时在文件顶部（`import random` 之后）追加：
```python
import logging

logger = logging.getLogger("ai-service.agent.tools")
```

- [ ] **Step 2: 验证模块可导入**

Run: `cd apps/service && .venv/bin/python -c "from agent.tools import ALL_TOOLS; print(len(ALL_TOOLS), 'tools loaded')"`

Expected: 输出 `5 tools loaded`

- [ ] **Step 3: Commit**

```bash
git add apps/service/agent/tools/__init__.py
git commit -m "feat: replace knowledge_base_query mock with RAG retrieval + generation"
```

---

### Task 9: 集成 — 应用启动初始化 Chroma

**Files:**
- Modify: `apps/service/app/lifespan.py`
- Modify: `apps/service/app/dependencies.py`

**Interfaces:**
- Consumes: `get_chroma_client()` from Task 3 的 vectorstore.py
- Produces: `app.state.chroma_client`, `get_chroma_client()` 依赖注入函数

- [ ] **Step 1: 更新 lifespan.py**

将 `apps/service/app/lifespan.py` 替换为：

```python
from fastapi import FastAPI
import logging
from contextlib import asynccontextmanager
from database import mysql
from database.session import get_db
from configs.config import settings
from agent.factory import create_customer_agent
from rag.ingestion.vectorstore import get_chroma_client

# 确保所有 ORM 模型被注册到 Base.metadata
import database.models  # noqa: F401

# 日志
logging.basicConfig(
    level=getattr(logging, "INFO"),
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
logger = logging.getLogger("ai-service")


async def _seed_initial_data() -> None:
    """初始化种子数据：创建管理员用户"""
    from services.auth import seed_admin_user
    async for db in get_db():
        await seed_admin_user(db)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时初始化连接池及 Provider 注册，关闭时释放资源"""
    logger.info("启动中...  创建数据库表")
    async with mysql.engine.begin() as conn:
        await conn.run_sync(mysql.Base.metadata.create_all)
    logger.info("初始化种子数据...")
    await _seed_initial_data()
    logger.info("初始化 Chroma 连接...")
    try:
        client = get_chroma_client()
        client.heartbeat()
        _app.state.chroma_client = client
        logger.info("Chroma 连接成功: %s:%s", settings.CHROMA_HOST, settings.CHROMA_PORT)
    except Exception as e:
        logger.warning("Chroma 连接失败: %s，RAG 功能暂不可用", e)
        _app.state.chroma_client = None
    logger.info("初始化agent...")
    _app.state.agent = create_customer_agent()
    logger.info("启动完成  %s:%s", settings.APP_HOST, settings.APP_PORT)
    yield
    logger.info("关闭中...")
    await mysql.engine.dispose()
    logger.info("已关闭")
```

- [ ] **Step 2: 更新 dependencies.py**

将 `apps/service/app/dependencies.py` 替换为：

```python
from fastapi import Request


def get_agent(request: Request):
    """获取 Agent 实例。"""
    return request.app.state.agent


def get_chroma_client(request: Request):
    """获取 Chroma Client 实例。"""
    return request.app.state.chroma_client
```

- [ ] **Step 3: 验证模块可导入**

Run: `cd apps/service && .venv/bin/python -c "from app.lifespan import lifespan; from app.dependencies import get_agent, get_chroma_client; print('OK')"`

Expected: 输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add apps/service/app/lifespan.py apps/service/app/dependencies.py
git commit -m "feat: initialize Chroma connection on app startup"
```

---

### Task 10: 端到端验证

**Files:**
- 无新文件，验证整体功能

**Interfaces:**
- Consumes: 所有前序 Task 的产出

- [ ] **Step 1: 验证所有模块可正常导入**

Run: `cd apps/service && .venv/bin/python -c "
from rag import ingest_document, delete_from_vectorstore, retrieve, generate_answer
from rag.ingestion import load_document, split_documents
from rag.retrieval import RetrievalResult
from rag.generation import GenerationResult
from models.embedding import create_embeddings
from models.reranker import create_reranker
from services.knowledge import upload_document, query_knowledge
from agent.tools import ALL_TOOLS
print('All imports OK')
print(f'Tools: {len(ALL_TOOLS)}')
"`

Expected: 输出 `All imports OK` 和 `Tools: 5`

- [ ] **Step 2: 验证应用可启动（无需 Chroma 服务）**

Run: `cd apps/service && timeout 5 .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8009 2>&1 | head -20`

Expected: 看到"启动完成"日志（Chroma 连接失败不影响启动）

- [ ] **Step 3: 如有 Chroma 服务可用，测试完整 RAG 流程**

（此步骤可选，取决于本地是否有 Chroma 服务运行）

如果 Chroma 服务在 localhost:8000 运行，可以测试：

```python
# 在 apps/service 目录下运行
import asyncio
from rag import ingest_document, retrieve, generate_answer

# 测试摄取（需要一个测试文件）
# result = asyncio.run(ingest_document("test.txt", "txt", 1, "test.txt"))

# 测试检索
# chunks = asyncio.run(retrieve("退货政策"))
# print(chunks)
```

- [ ] **Step 4: Final Commit（如有遗漏修正）**

```bash
git add -A
git commit -m "feat: complete RAG module implementation"
```
