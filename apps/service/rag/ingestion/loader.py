"""文档加载器 —— 根据文件类型选择对应的 LangChain DocumentLoader。"""

import logging

from langchain_core.documents import Document

logger = logging.getLogger("intelligent-customer.rag.loader")


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
