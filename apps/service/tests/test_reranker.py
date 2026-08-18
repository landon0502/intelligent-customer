"""Reranker 重排序测试 —— 工厂默认关闭、直通行为、retrieve 集成（S-rerank）。"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from rag.retrieval.retriever import RetrievalResult, retrieve
from models.reranker import DEFAULT_RERANKER_MODEL, Reranker, create_reranker


class _FakeDoc:
    """模拟 langchain Document（仅含检索所需字段）。"""

    def __init__(self, content: str, metadata: dict | None = None):
        self.page_content = content
        self.metadata = metadata or {}


class _FakeVectorstore:
    """模拟 Chroma vectorstore 的相似度检索。"""

    def __init__(self, raw: list):
        self._raw = raw

    def similarity_search_with_relevance_scores(self, query: str, k: int):
        return self._raw[:k]


def _fake_app(registry):
    """构造假的 app.main.app，避免测试引入 FastAPI 重依赖。"""
    app = MagicMock()
    app.state.registry = registry
    return app


def _fake_registry(vectorstore, reranker):
    registry = MagicMock()

    async def _ensure(name: str):
        return {"vectorstore": vectorstore, "reranker": reranker}[name]

    registry.ensure_initialized = _ensure
    return registry


def _run_with_fake_app(registry, fn):
    fake_module = types.ModuleType("app.main")
    fake_module.app = _fake_app(registry)
    with patch.dict(sys.modules, {"app.main": fake_module}):
        return fn()


# ---------- 工厂 ----------


def test_create_reranker_defaults_disabled():
    """默认配置返回关闭状态的 Reranker（不加载模型）。"""
    r = create_reranker({})
    assert r.enabled is False
    assert r.model_name == DEFAULT_RERANKER_MODEL
    assert r.device == "cpu"
    assert r.candidates == 20
    assert r.recall_threshold == 0.1


def test_create_reranker_enabled_parses_config():
    """启用配置被正确解析。"""
    r = create_reranker(
        {
            "rerank.enabled": "true",
            "rerank.model": "local/reranker",
            "rerank.device": "mps",
            "rerank.candidates": "10",
            "rerank.recall_threshold": "0.2",
        }
    )
    assert r.enabled is True
    assert r.model_name == "local/reranker"
    assert r.device == "mps"
    assert r.candidates == 10
    assert r.recall_threshold == 0.2


# ---------- Reranker 直通（默认关闭） ----------


def test_reranker_disabled_is_passthrough_without_model():
    """关闭时不加载模型，rerank 直通且保持原顺序。"""
    r = create_reranker({})
    results = [
        RetrievalResult(content=f"候选{i}", score=0.5, metadata={}) for i in range(5)
    ]
    out = r.rerank("查询", results, 2)
    assert [x.content for x in out] == ["候选0", "候选1"]
    assert r._model is None  # 未触发模型加载


def test_reranker_enabled_empty_results():
    """启用但候选为空时直接返回空。"""
    r = Reranker(enabled=True)
    assert r.rerank("查询", [], 2) == []


# ---------- retrieve 集成 ----------


def test_retrieve_reranker_disabled_keeps_threshold_behavior():
    """关闭时保持原"向量检索 + 阈值过滤"行为，不调用 rerank。"""
    reranker = MagicMock()
    reranker.enabled = False
    reranker.candidates = 20
    reranker.recall_threshold = 0.1

    # 一条低于 0.3 阈值被过滤，一条保留
    raw = [(_FakeDoc("低分内容"), 0.1), (_FakeDoc("高分内容"), 0.6)]
    vs = _FakeVectorstore(raw)
    registry = _fake_registry(vs, reranker)

    def _call():
        import asyncio
        return asyncio.run(retrieve("测试查询"))

    results = _run_with_fake_app(registry, _call)
    assert [x.content for x in results] == ["高分内容"]
    reranker.rerank.assert_not_called()


def test_retrieve_reranker_enabled_recalls_more_and_reranks():
    """启用时召回更宽候选集，宽松阈值过滤后调用 rerank 取 Top-K。"""
    reranker = MagicMock()
    reranker.enabled = True
    reranker.candidates = 20
    reranker.recall_threshold = 0.1
    reranker.rerank.return_value = [
        RetrievalResult(content="候选3", score=0.9, metadata={}),
        RetrievalResult(content="候选1", score=0.8, metadata={}),
    ]

    # 5 条候选，全部高于宽松阈值 0.1（无 0.3 过滤）
    raw = [(_FakeDoc(f"候选{i}", {"i": i}), 0.5) for i in range(5)]
    vs = _FakeVectorstore(raw)
    registry = _fake_registry(vs, reranker)

    def _call():
        import asyncio
        return asyncio.run(retrieve("测试查询", top_k=2))

    results = _run_with_fake_app(registry, _call)
    assert [x.content for x in results] == ["候选3", "候选1"]
    reranker.rerank.assert_called_once()
    # 召回宽度使用 candidates（20），而非最终 top_k（2）
    _call_args = reranker.rerank.call_args.args
    assert len(_call_args[1]) == 5  # 全部候选传入精排
