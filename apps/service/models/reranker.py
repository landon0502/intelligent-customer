"""Reranker 模型 —— 使用 BAAI/bge-reranker-v2-m3 本地重排序。

基于 sentence-transformers 的 CrossEncoder 实现，兼容新版 transformers。
单例模式避免重复加载模型。
"""

import logging

from sentence_transformers import CrossEncoder

logger = logging.getLogger("intelligent-customer.reranker")


class BGEReranker:
    """BGE Reranker 客户端，基于 bge-reranker-v2-m3 本地推理。"""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", top_n: int = 4):
        self.model_name = model_name
        self.top_n = top_n
        self._model: CrossEncoder | None = None

    def _get_model(self) -> CrossEncoder:
        """延迟加载模型，避免启动时占用内存。"""
        if self._model is None:
            logger.info("加载 Reranker 模型: %s", self.model_name)
            self._model = CrossEncoder(self.model_name)
            logger.info("Reranker 模型加载完成")
        return self._model

    async def rerank(
        self, query: str, documents: list[str], top_n: int | None = None
    ) -> list[dict]:
        """对文档列表进行重排序。"""
        if not documents:
            return []

        n = top_n or self.top_n

        model = self._get_model()

        # 构造 (query, document) 对
        pairs = [[query, doc] for doc in documents]
        scores = model.predict(pairs, normalize_scores=True)

        # 按 score 降序排序，取 top_n
        scored_docs = [
            {"index": i, "relevance_score": float(scores[i]), "text": documents[i]}
            for i in range(len(documents))
        ]
        scored_docs.sort(key=lambda x: x["relevance_score"], reverse=True)

        logger.info(
            "Reranker 完成: %d 条输入, %d 条输出",
            len(documents), min(n, len(scored_docs)),
        )
        return scored_docs[:n]


_reranker: BGEReranker | None = None


def create_reranker(top_n: int = 4) -> BGEReranker:
    """创建 BGE Reranker 实例（单例）。

    首次调用时初始化，后续调用直接复用。
    top_n 仅首次调用时生效。
    """
    global _reranker
    if _reranker is None:
        _reranker = BGEReranker(top_n=top_n)
    return _reranker
