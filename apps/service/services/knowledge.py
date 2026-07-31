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

logger = logging.getLogger("intelligent-customer.knowledge")

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
    import time
    t0 = time.time()

    # 1. 检索
    chunks = await retrieve(question, top_k=settings.RAG_TOP_K)
    t_retrieve = time.time()

    # 2. 生成回答
    from app.main import app
    rag_llm = await app.state.registry.ensure_initialized("rag_llm")
    result = await generate_answer(question, chunks, rag_llm=rag_llm)
    t_generate = time.time()

    logger.info(
        "query_knowledge 总耗时: %.2fs (检索: %.2fs, 生成: %.2fs)",
        t_generate - t0, t_retrieve - t0, t_generate - t_retrieve,
    )

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
