"""系统配置 Pydantic 模型 —— 请求体与响应体定义。"""

from datetime import datetime

from pydantic import BaseModel


class ConfigItem(BaseModel):
    """单条配置项"""
    key: str
    value: str
    category: str = "general"
    description: str | None = None

    model_config = {"from_attributes": True}


class ConfigUpdateRequest(BaseModel):
    """批量更新配置请求"""
    configs: list[ConfigItem]


class LlmConfigResponse(BaseModel):
    """LLM 配置响应"""
    provider: str
    model: str
    api_key_set: bool = False  # 是否已设置 API Key（不返回实际值）
    base_url: str = ""
    temperature: str
    max_tokens: str
    timeout: str
    max_retries: str


class EmbeddingConfigResponse(BaseModel):
    """Embedding 配置响应"""
    provider: str
    model: str
    dimensions: str


class VectorStoreConfigResponse(BaseModel):
    """向量数据库配置响应"""
    provider: str
    host: str
    port: str
    collection: str
