"""Embedding 模型工厂函数 — 创建 HuggingFaceEmbeddings 实例。

纯函数，无全局状态。由 ComponentRegistry 调用。
"""

from langchain_huggingface import HuggingFaceEmbeddings


def create_embeddings(config: dict) -> HuggingFaceEmbeddings:
    """创建 Embedding 实例。

    Args:
        config: "embedding" 分类的配置字典

    Returns:
        HuggingFaceEmbeddings 实例
    """
    model_name = config.get("embedding.model", "BAAI/bge-base-zh-v1.5")

    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "mps"},
        encode_kwargs={"normalize_embeddings": True},
    )
