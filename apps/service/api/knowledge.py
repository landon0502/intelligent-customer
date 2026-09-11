"""知识库管理接口 —— 文档上传、列表、删除、检索测试。"""

from fastapi import APIRouter, Depends, UploadFile, File, Query
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
    upload_documents,
    get_documents,
    delete_document,
    query_knowledge,
)
from utils.response import success, error

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/upload")
async def upload_knowledge_document(
    files: list[UploadFile] = File(..., description="上传的文档文件（PDF/Word/TXT），支持多选"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量上传文档到知识库（管理员权限）

    逐文件独立处理：单个文件校验失败只体现在 results 里，不影响其余文件，
    整体仍返回成功，由前端按 success_count / failed_count 提示。
    """
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可上传文档")

    payload = [(f.filename or "", await f.read()) for f in files]
    try:
        results = await upload_documents(db, payload, uploaded_by=current_user.id)
    except ValueError as e:
        return error(code=40004, message=str(e))

    return success(data=DocumentUploadResult(
        results=results,
        success_count=sum(1 for r in results if r.success),
        failed_count=sum(1 for r in results if not r.success),
    ).model_dump())

@router.get("/documents")
async def list_documents(
    keyword: str = '',
    page: int = 1,
    page_size: int = Query(10, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库文档列表"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看文档列表")

    docs = await get_documents(db, keyword=keyword, page=page, page_size=page_size)
    return success(data=docs)


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
    """知识库检索测试（管理员权限）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可检索知识库")
    result = await query_knowledge(req.question)
    return success(data=KnowledgeQueryResult(**result).model_dump())
