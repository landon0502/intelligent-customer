"""知识库管理接口 —— 文档上传、列表、删除、检索测试。"""

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from schemas.document_schema import (
    DocumentItem,
    DocumentUploadResult,
    KnowledgeQueryRequest,
    KnowledgeQueryResult,
)
from auth.security import get_current_user
from services.knowledge import (
    upload_document,
    get_documents,
    delete_document,
    query_knowledge,
)
from utils.response import success, error

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/upload")
async def upload_knowledge_document(
    file: UploadFile = File(..., description="上传的文档文件（PDF/Word/TXT）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到知识库（管理员权限）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可上传文档")

    content = await file.read()
    try:
        doc = await upload_document(db, file.filename, content, uploaded_by=current_user.id)
    except ValueError as e:
        return error(code=40004, message=str(e))

    return success(data=DocumentUploadResult(
        document_id=doc.id,
        status=doc.status,
    ).model_dump())


@router.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库文档列表"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看文档列表")

    docs = await get_documents(db)
    items = [DocumentItem.model_validate(d) for d in docs]
    return success(data=items)


@router.delete("/documents/{document_id}")
async def delete_knowledge_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除知识库文档（管理员权限）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可删除文档")

    deleted = await delete_document(db, document_id)
    if not deleted:
        return error(code=40005, message="文档不存在")
    return success(data={"success": True})


@router.post("/query")
async def query_knowledge_base(
    req: KnowledgeQueryRequest,
    current_user: User = Depends(get_current_user),
):
    """知识库检索测试"""
    result = await query_knowledge(req.question)
    return success(data=KnowledgeQueryResult(**result).model_dump())
