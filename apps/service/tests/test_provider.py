"""AsyncConfigProvider 单元测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from configs.provider import AsyncConfigProvider


def _make_mock_rows(data: dict[str, str]):
    """构造模拟 DB 行列表。"""
    rows = []
    for key, value in data.items():
        row = MagicMock()
        row.key = key
        row.value = value
        rows.append(row)
    return rows


@pytest.mark.anyio
async def test_get_category_reads_from_db_on_cache_miss():
    """缓存未命中时从 DB 读取配置。"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _make_mock_rows({
        "llm.model": "deepseek-v4-pro",
        "llm.temperature": "0.7",
    })
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    provider = AsyncConfigProvider(mock_factory)
    result = await provider.get_category("llm")

    assert result == {"llm.model": "deepseek-v4-pro", "llm.temperature": "0.7"}
    mock_session.execute.assert_called_once()


@pytest.mark.anyio
async def test_get_category_returns_cached_on_cache_hit():
    """缓存命中时直接返回，不读 DB。"""
    mock_factory = MagicMock()
    provider = AsyncConfigProvider(mock_factory)
    # 手动填充缓存
    provider._cache["llm"] = {"llm.model": "deepseek-v4-pro"}

    result = await provider.get_category("llm")
    assert result == {"llm.model": "deepseek-v4-pro"}
    # mock_factory 不应被调用
    mock_factory.assert_not_called()


@pytest.mark.anyio
async def test_get_value_extracts_single_value():
    """get_value 从缓存中提取单个值。"""
    mock_factory = MagicMock()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _make_mock_rows({
        "llm.model": "deepseek-v4-pro",
    })
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    provider = AsyncConfigProvider(mock_factory)
    value = await provider.get_value("llm.model", "default-model")
    assert value == "deepseek-v4-pro"


@pytest.mark.anyio
async def test_get_value_returns_default_on_missing_key():
    """get_value 在 key 不存在时返回默认值。"""
    mock_factory = MagicMock()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _make_mock_rows({
        "llm.temperature": "0.7",
    })
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    provider = AsyncConfigProvider(mock_factory)
    value = await provider.get_value("llm.model", "default-model")
    assert value == "default-model"


@pytest.mark.anyio
async def test_invalidate_removes_category_from_cache():
    """invalidate 移除指定分类的缓存。"""
    mock_factory = MagicMock()
    provider = AsyncConfigProvider(mock_factory)
    provider._cache["llm"] = {"llm.model": "deepseek-v4-pro"}
    provider._cache["embedding"] = {"embedding.model": "bge-base-zh"}

    provider.invalidate("llm")
    assert "llm" not in provider._cache
    assert "embedding" in provider._cache


@pytest.mark.anyio
async def test_invalidate_all_clears_entire_cache():
    """invalidate_all 清空所有缓存。"""
    mock_factory = MagicMock()
    provider = AsyncConfigProvider(mock_factory)
    provider._cache["llm"] = {"llm.model": "deepseek-v4-pro"}
    provider._cache["embedding"] = {"embedding.model": "bge-base-zh"}

    provider.invalidate_all()
    assert provider._cache == {}


@pytest.mark.anyio
async def test_invalidate_then_get_re_reads_from_db():
    """失效后再次获取会重新从 DB 读取。"""
    mock_session = AsyncMock()
    mock_result_old = MagicMock()
    mock_result_old.scalars.return_value.all.return_value = _make_mock_rows({
        "llm.model": "old-model",
    })
    mock_result_new = MagicMock()
    mock_result_new.scalars.return_value.all.return_value = _make_mock_rows({
        "llm.model": "new-model",
    })
    mock_session.execute = AsyncMock(
        side_effect=[mock_result_old, mock_result_new]
    )
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    provider = AsyncConfigProvider(mock_factory)

    # 首次读取
    result1 = await provider.get_category("llm")
    assert result1 == {"llm.model": "old-model"}

    # 失效后重新读取
    provider.invalidate("llm")
    result2 = await provider.get_category("llm")
    assert result2 == {"llm.model": "new-model"}

    assert mock_session.execute.call_count == 2
