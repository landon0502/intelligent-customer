"""RAG 文档摄取流水线 —— 完整摄取流程编排。"""

import logging

from rag.ingestion.loader import load_document
from rag.ingestion.splitter import split_documents
from rag.ingestion.vectorstore import add_documents_to_vectorstore

logger = logging.getLogger("intelligent-customer.rag.ingestion")


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
