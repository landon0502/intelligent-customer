"""文档相关 Pydantic 模型 —— 请求体与响应体定义。"""

from datetime import datetime

from pydantic import BaseModel


# ========== 响应模型 ==========

class DocumentItem(BaseModel):
    """文档列表项"""
    id: int
    filename: str
    file_type: str
    chunk_count: int
    status: str
    uploaded_by: int | None = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadItem(BaseModel):
    """批量上传中单个文件的结果"""
    filename: str
    success: bool
    document_id: int | None = None
    status: str | None = None
    message: str | None = None


class DocumentUploadResult(BaseModel):
    """批量上传文档响应"""
    results: list[DocumentUploadItem]
    success_count: int
    failed_count: int


class KnowledgeQueryRequest(BaseModel):
    """知识库检索测试请求"""
    question: str


class KnowledgeQueryResult(BaseModel):
    """知识库检索测试响应"""
    chunks: list[dict]
    answer: str | None = None
    sources: list[dict] | None = None
