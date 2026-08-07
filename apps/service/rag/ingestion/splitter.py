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
