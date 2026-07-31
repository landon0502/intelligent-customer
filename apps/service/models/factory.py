"""LLM 工厂函数 — 创建 Agent LLM 和 RAG LLM 实例。

纯函数，无全局状态。由 ComponentRegistry 调用。
"""

import httpx
from langchain.chat_models import init_chat_model


def _build_llm_params(config: dict, prefix: str = "llm") -> dict:
    """从配置字典构建 LLM 参数。

    Args:
        config: 配置字典（key 格式为 "prefix.xxx"）
        prefix: 配置键前缀（"llm" 或 "rag_llm"）

    Returns:
        init_chat_model 所需的参数字典
    """
    model = config.get(f"{prefix}.model", "deepseek-v4-pro")
    temperature = float(config.get(f"{prefix}.temperature", "0.7"))
    max_tokens = int(config.get(f"{prefix}.max_tokens", "512"))
    timeout = int(config.get(f"{prefix}.timeout", "15"))
    max_retries = int(config.get(f"{prefix}.max_retries", "1"))
    api_key = config.get(f"{prefix}.api_key", "")
    base_url = config.get(f"{prefix}.base_url", "")

    return {
        "model": model,
        "model_provider": "openai",
        "api_key": api_key,
        "base_url": base_url,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "max_retries": max_retries,
        # "http_async_client": httpx.AsyncClient(
        #     timeout=httpx.Timeout(timeout, connect=10)
        # ),
    }


def create_agent_llm(config: dict):
    """创建 Agent 使用的 LLM 实例。

    Args:
        config: "llm" 分类的配置字典

    Returns:
        BaseChatModel 实例
    """
    params = _build_llm_params(config, prefix="llm")
    return init_chat_model(**params)


def create_rag_llm(rag_config: dict, llm_config: dict):
    """创建 RAG 生成链使用的 LLM 实例。

    当 rag_llm 分类无配置时，回退到 llm 分类配置。

    Args:
        rag_config: "rag_llm" 分类的配置字典
        llm_config: "llm" 分类的配置字典（fallback）

    Returns:
        BaseChatModel 实例
    """
    if (
        not rag_config
        or rag_config.get("rag_llm.model") == ""
        or rag_config.get("rag_llm.api_key") == ""
    ):
        # rag_llm 分类无配置，回退到 llm 分类
        params = _build_llm_params(llm_config, prefix="llm")
    else:
        params = _build_llm_params(rag_config, prefix="rag_llm")
    return init_chat_model(**params)
