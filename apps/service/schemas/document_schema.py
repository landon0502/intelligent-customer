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


class DocumentUploadResult(BaseModel):
    """上传文档响应"""
    document_id: int
    status: str


class KnowledgeQueryRequest(BaseModel):
    """知识库检索测试请求"""
    question: str


class KnowledgeQueryResult(BaseModel):
    """知识库检索测试响应"""
    chunks: list[dict]
    answer: str | None = None
    sources: list[dict] | None = None
