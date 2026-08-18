"""RAG 检索模块 —— 向量搜索 + 相似度过滤。"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

from configs.config import settings

logger = logging.getLogger("intelligent-customer.rag.retrieval")


@dataclass
class RetrievalResult:
    """单条检索结果。"""

    content: str
    score: float
    metadata: dict = field(default_factory=dict)


async def retrieve(
    query: str, top_k: int | None = None
) -> list[RetrievalResult]:
    """检索与查询最相关的文档块。

    流程：问题向量化 → Chroma 相似度检索 → 过滤低分 →（可选）Reranker 重排 → 取 Top-K

    reranker 启用时：向量召回更宽的候选集（rerank.candidates），用宽松阈值过滤后
    交给交叉编码器精排，再取 Top-K；关闭时保持原有"向量检索 + 阈值过滤"行为。

    Args:
        query: 用户查询文本
        top_k: 返回结果数量，默认使用配置值

    Returns:
        检索结果列表，按相关性排序
    """
    k = top_k or settings.RAG_TOP_K
    t0 = time.time()

    # Chroma 相似度检索（同步阻塞操作，放入线程池避免卡住事件循环）
    from app.main import app
    registry = app.state.registry
    vectorstore = await registry.ensure_initialized("vectorstore")
    reranker = await registry.ensure_initialized("reranker")

    # 向量召回宽度：reranker 开启时召回更宽候选集，交由精排收敛
    recall_k = reranker.candidates if reranker.enabled else k
    raw_results = await asyncio.to_thread(
        vectorstore.similarity_search_with_relevance_scores, query, k=recall_k
    )
    logger.info("Chroma 检索耗时: %.2fs", time.time() - t0)

    if not raw_results:
        logger.info("检索无结果: query=%s", query[:50])
        return []

    # 过滤低分结果（reranker 开启时用宽松阈值保留候选，交给精排判断）
    threshold = reranker.recall_threshold if reranker.enabled else settings.RAG_SCORE_THRESHOLD
    filtered = [
        (doc, score)
        for doc, score in raw_results
        if score >= threshold
    ]

    if not filtered:
        logger.info(
            "检索结果全低于阈值 %.2f: query=%s",
            threshold,
            query[:50],
        )
        return []

    logger.info(
        "Chroma 检索: %d 条原始结果, %d 条过滤后, 耗时: %.2fs",
        len(raw_results), len(filtered), time.time() - t0,
    )

    # 组装结果
    results = [
        RetrievalResult(
            content=doc.page_content,
            score=score,
            metadata=doc.metadata,
        )
        for doc, score in filtered
    ]

    # Reranker 精排（阻塞 torch 推理，放入线程池）
    if reranker.enabled and len(results) > k:
        results = await asyncio.to_thread(reranker.rerank, query, results, k)
        logger.info("Reranker 重排: %d 条候选 → %d 条, 耗时: %.2fs",
                    len(filtered), len(results), time.time() - t0)

    return results
