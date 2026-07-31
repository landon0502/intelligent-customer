"""工厂函数单元测试 — 验证纯工厂函数正确创建组件。"""

import pytest
from unittest.mock import MagicMock, patch


def test_create_agent_llm_creates_chat_model():
    """create_agent_llm 用配置创建 BaseChatModel。"""
    from models.factory import create_agent_llm

    config = {
        "llm.model": "deepseek-v4-pro",
        "llm.api_key": "test-key",
        "llm.base_url": "https://api.test.com",
        "llm.temperature": "0.5",
        "llm.max_tokens": "1024",
        "llm.timeout": "30",
        "llm.max_retries": "2",
    }

    with patch("models.factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock(name="BaseChatModel")
        result = create_agent_llm(config)

        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args[1]
        assert call_kwargs["model"] == "deepseek-v4-pro"
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["timeout"] == 30
        assert call_kwargs["max_retries"] == 2


def test_create_agent_llm_uses_defaults_on_missing_keys():
    """create_agent_llm 在配置缺失时使用默认值。"""
    from models.factory import create_agent_llm

    config = {}  # 空配置

    with patch("models.factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock(name="BaseChatModel")
        create_agent_llm(config)

        call_kwargs = mock_init.call_args[1]
        assert call_kwargs["model"] == "deepseek-v4-pro"  # 默认值
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 512


def test_create_rag_llm_with_rag_config():
    """create_rag_llm 使用 rag_llm 分类配置。"""
    from models.factory import create_rag_llm

    rag_config = {
        "rag_llm.model": "glm-4-flash",
        "rag_llm.api_key": "rag-key",
        "rag_llm.base_url": "https://rag.test.com",
        "rag_llm.temperature": "0.3",
        "rag_llm.max_tokens": "256",
        "rag_llm.timeout": "10",
        "rag_llm.max_retries": "1",
    }
    llm_config = {
        "llm.model": "deepseek-v4-pro",
        "llm.api_key": "llm-key",
    }

    with patch("models.factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock(name="BaseChatModel")
        result = create_rag_llm(rag_config, llm_config)

        call_kwargs = mock_init.call_args[1]
        assert call_kwargs["model"] == "glm-4-flash"
        assert call_kwargs["temperature"] == 0.3


def test_create_rag_llm_falls_back_to_llm_config():
    """create_rag_llm 在 rag_llm 配置为空时回退到 llm 配置。"""
    from models.factory import create_rag_llm

    rag_config = {}  # 空 rag_llm 配置
    llm_config = {
        "llm.model": "deepseek-v4-pro",
        "llm.api_key": "llm-key",
        "llm.base_url": "https://api.test.com",
        "llm.temperature": "0.7",
        "llm.max_tokens": "512",
        "llm.timeout": "15",
        "llm.max_retries": "1",
    }

    with patch("models.factory.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock(name="BaseChatModel")
        result = create_rag_llm(rag_config, llm_config)

        call_kwargs = mock_init.call_args[1]
        assert call_kwargs["model"] == "deepseek-v4-pro"
        assert call_kwargs["api_key"] == "llm-key"


def test_create_embeddings_creates_hf_instance():
    """create_embeddings 用配置创建 HuggingFaceEmbeddings。"""
    from models.embedding import create_embeddings

    config = {
        "embedding.model": "BAAI/bge-large-zh",
    }

    with patch("models.embedding.HuggingFaceEmbeddings") as mock_hf:
        mock_hf.return_value = MagicMock(name="HuggingFaceEmbeddings")
        result = create_embeddings(config)

        mock_hf.assert_called_once()
        call_kwargs = mock_hf.call_args[1]
        assert call_kwargs["model_name"] == "BAAI/bge-large-zh"


def test_create_embeddings_uses_default_model():
    """create_embeddings 在配置缺失时使用默认模型。"""
    from models.embedding import create_embeddings

    config = {}

    with patch("models.embedding.HuggingFaceEmbeddings") as mock_hf:
        mock_hf.return_value = MagicMock(name="HuggingFaceEmbeddings")
        create_embeddings(config)

        call_kwargs = mock_hf.call_args[1]
        assert call_kwargs["model_name"] == "BAAI/bge-base-zh-v1.5"


def test_create_chroma_client_creates_http_client():
    """create_chroma_client 用配置创建 chromadb.HttpClient。"""
    from rag.ingestion.vectorstore import create_chroma_client

    config = {
        "vectorstore.host": "192.168.1.100",
        "vectorstore.port": "9000",
    }

    with patch("rag.ingestion.vectorstore.chromadb") as mock_chroma:
        mock_chroma.HttpClient.return_value = MagicMock(name="HttpClient")
        result = create_chroma_client(config)

        mock_chroma.HttpClient.assert_called_once_with(
            host="192.168.1.100", port=9000
        )


def test_create_vectorstore_creates_chroma_instance():
    """create_vectorstore 用配置和 embeddings 创建 Chroma。"""
    from rag.ingestion.vectorstore import create_vectorstore

    config = {
        "vectorstore.host": "localhost",
        "vectorstore.port": "8000",
        "vectorstore.collection": "test_collection",
    }
    mock_embeddings = MagicMock(name="HuggingFaceEmbeddings")
    mock_client = MagicMock(name="HttpClient")

    with patch("rag.ingestion.vectorstore.Chroma") as mock_chroma_cls:
        mock_chroma_cls.return_value = MagicMock(name="Chroma")
        result = create_vectorstore(config, mock_embeddings, mock_client)

        mock_chroma_cls.assert_called_once_with(
            client=mock_client,
            collection_name="test_collection",
            embedding_function=mock_embeddings,
        )
