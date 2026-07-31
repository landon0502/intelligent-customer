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
