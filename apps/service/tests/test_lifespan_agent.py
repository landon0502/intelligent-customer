"""lifespan 组件接线集成测试 —— agent slot 绑定 tools 分类并动态绑定工具。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from configs.registry import ComponentRegistry
from app.lifespan import _register_components

# 覆盖 6 个分类的同一份 mock 配置（各 factory 已 patch）
_MOCK_CONFIG = {
    "llm.model": "deepseek-v4-pro",
    "tools.knowledge_base_query": "enabled",
    "tools.enterprise_query": "enabled",
    "tools.ticket_submit": "disabled",
    "tools.ticket_status": "enabled",
    "tools.transfer_human": "enabled",
    "tools.clarify": "enabled",
}


@pytest.mark.anyio
async def test_lifespan_agent_slot_binds_tools_and_filters_disabled():
    mock_provider = AsyncMock()
    mock_provider.get_category = AsyncMock(return_value=dict(_MOCK_CONFIG))
    registry = ComponentRegistry(mock_provider)

    mock_llm = MagicMock(name="agent_llm")
    mock_agent = MagicMock(name="agent")

    with (
        patch("models.factory.create_agent_llm", return_value=mock_llm),
        patch("models.factory.create_rag_llm", return_value=MagicMock()),
        patch("models.embedding.create_embeddings", return_value=MagicMock()),
        patch(
            "rag.ingestion.vectorstore.create_chroma_client",
            return_value=MagicMock(),
        ),
        patch(
            "rag.ingestion.vectorstore.create_vectorstore",
            return_value=MagicMock(),
        ),
        patch(
            "agent.factory.create_customer_agent",
            return_value=mock_agent,
        ) as mock_create,
    ):
        _register_components(registry)
        agent = await registry.ensure_initialized("agent")

    assert agent is mock_agent
    # agent slot 绑定 tools 分类
    assert registry._slots["agent"]._config_category == "tools"

    # 注入 create_customer_agent 的工具集不含 ticket_submit
    call_kwargs = mock_create.call_args[1]
    enabled_names = [t.name for t in call_kwargs["tools"]]
    assert "ticket_submit" not in enabled_names
    assert len(enabled_names) == 5
    # 动态提示词不含 ticket_submit 描述
    # 注：build_system_prompt 返回纯字符串，create_customer_agent 内部才包 SystemMessage
    assert "当用户要求办理企业业务、提交申请时使用" not in call_kwargs["system_prompt"]
