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

    流程：问题向量化 → Chroma 相似度检索 → 过滤低分 → 取 Top-K

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
    vectorstore = app.state.registry.get("vectorstore")
    raw_results = await asyncio.to_thread(
        vectorstore.similarity_search_with_relevance_scores, query, k=k
    )
    logger.info("Chroma 检索耗时: %.2fs", time.time() - t0)

    if not raw_results:
        logger.info("检索无结果: query=%s", query[:50])
        return []

    # 过滤低分结果
    filtered = [
        (doc, score)
        for doc, score in raw_results
        if score >= settings.RAG_SCORE_THRESHOLD
    ]

    if not filtered:
        logger.info(
            "检索结果全低于阈值 %.2f: query=%s",
            settings.RAG_SCORE_THRESHOLD,
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

    return results
