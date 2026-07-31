"""向量化与 Chroma 入库 — 文档块 Embedding + Chroma 存储/删除。

工厂函数由 ComponentRegistry 调用。
运行时函数（add_documents_to_vectorstore, delete_from_vectorstore）
通过 Registry 获取当前组件实例。
"""

import asyncio
import logging

import chromadb
from langchain_core.documents import Document
from langchain_chroma import Chroma

logger = logging.getLogger("intelligent-customer.rag.vectorstore")


# ========== 工厂函数（由 ComponentRegistry 调用） ==========

def create_chroma_client(config: dict) -> chromadb.HttpClient:
    """创建 Chroma HTTP Client 实例。

    Args:
        config: "vectorstore" 分类的配置字典

    Returns:
        chromadb.HttpClient 实例
    """
    from configs.config import settings
    host = config.get("vectorstore.host", settings.CHROMA_HOST)
    port = config.get("vectorstore.port", str(settings.CHROMA_PORT))

    return chromadb.HttpClient(
        host=host,
        port=int(port),
    )


def create_vectorstore(config: dict, embeddings, client) -> Chroma:
    """创建 Chroma VectorStore 实例。

    Args:
        config: "vectorstore" 分类的配置字典
        embeddings: HuggingFaceEmbeddings 实例（由 Registry 提供）
        client: chromadb.HttpClient 实例（由 Registry 提供）

    Returns:
        Chroma VectorStore 实例
    """
    from configs.config import settings
    collection = config.get("vectorstore.collection", settings.CHROMA_COLLECTION)

    return Chroma(
        client=client,
        collection_name=collection,
        embedding_function=embeddings,
    )


# ========== 运行时函数（通过 Registry 获取组件） ==========

def _get_registry():
    """获取 ComponentRegistry 实例。"""
    from app.main import app
    return app.state.registry


async def add_documents_to_vectorstore(
    documents: list[Document], doc_id: int, filename: str
) -> int:
    """将文档块向量化并存入 Chroma。"""
    if not documents:
        return 0

    for doc in documents:
        doc.metadata["doc_id"] = doc_id
        doc.metadata["filename"] = filename

    registry = _get_registry()
    vectorstore = await registry.ensure_initialized("vectorstore")
    await asyncio.to_thread(vectorstore.add_documents, documents)
    logger.info(
        "文档 %s (id=%d) 共 %d 个块已入库",
        filename, doc_id, len(documents),
    )
    return len(documents)


async def delete_from_vectorstore(doc_id: int) -> None:
    """从 Chroma 中删除指定文档的所有向量。"""
    try:
        registry = _get_registry()
        client = await registry.ensure_initialized("chroma_client")
        from configs.config import settings
        collection_name = settings.CHROMA_COLLECTION
        collection = client.get_collection(collection_name)
        collection.delete(
            where={"doc_id": doc_id},
        )
        logger.info("文档 id=%d 的向量已从 Chroma 删除", doc_id)
    except Exception as e:
        logger.warning("从 Chroma 删除文档 id=%d 向量失败: %s", doc_id, e)
