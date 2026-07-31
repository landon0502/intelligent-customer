"""RAG 文档摄取模块 —— 负责文档加载、清洗、切片和向量化。"""

from rag.ingestion.pipeline import ingest_document
from rag.ingestion.vectorstore import (
    add_documents_to_vectorstore,
    create_chroma_client,
    create_vectorstore,
    delete_from_vectorstore,
)

__all__ = [
    "add_documents_to_vectorstore",
    "create_chroma_client",
    "create_vectorstore",
    "delete_from_vectorstore",
    "ingest_document",
]
