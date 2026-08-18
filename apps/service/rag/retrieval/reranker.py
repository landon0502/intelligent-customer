"""Reranker 重排序模块 —— Qwen3-Reranker 交叉编码器重排检索候选。

检索-重排序（retrieve-then-rerank）：向量召回宽集 → 交叉编码器精排 → 取 Top-K。
Qwen3-Reranker-0.6B 通过 transformers 直接加载（FlagEmbedding 映射表不含 Qwen3 系列）。

模型懒加载：enabled=false 时不加载、零成本；首次启用时从 HuggingFace 下载并载入。
rerank() 为同步阻塞方法（torch 推理），调用方应通过 asyncio.to_thread 放入线程池。
"""

import logging
logger = logging.getLogger("intelligent-customer.rag.reranker")

DEFAULT_RERANKER_MODEL = "Qwen/Qwen3-Reranker-0.6B"


class Reranker:
    """Qwen3-Reranker 交叉编码器重排序器。

    默认关闭（enabled=False）时 rerank 为直通，不加载模型。
    启用后懒加载模型，按"查询 × 候选内容"逐对打分并降序取 Top-K。
    """

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER_MODEL,
        device: str = "cpu",
        candidates: int = 20,
        recall_threshold: float = 0.1,
        enabled: bool = False,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.candidates = candidates
        self.recall_threshold = recall_threshold
        self.enabled = enabled
        self._model = None
        self._tokenizer = None

    # ---------- 内部：懒加载 + 打分 ----------

    def _ensure_loaded(self) -> None:
        """加载模型（仅首次调用；下载 + 载入耗时较长）。

        Qwen3-Reranker 仓库为标准 cross-encoder 结构（config_sentence_transformers.json
        + 1_LogitScore/），用 sentence-transformers CrossEncoder 加载；根 config.json 是
        纯 Qwen3 因果 LM 配置，不能直接用 AutoModelForSequenceClassification 加载。
        """
        if self._model is not None:
            return
        from sentence_transformers import CrossEncoder

        logger.info("加载 reranker 模型: %s (device=%s)", self.model_name, self.device)
        self._model = CrossEncoder(
            self.model_name,
            device=self.device,
            trust_remote_code=True,
        )
        logger.info("reranker 模型加载完成: %s", self.model_name)

    def _score_pairs(self, pairs: list[tuple[str, str]]) -> list[float]:
        """对 (query, document) 对打分，返回相关性分数列表。"""
        self._ensure_loaded()
        import numpy as np

        scores = self._model.predict(pairs, convert_to_numpy=True)
        if isinstance(scores, np.ndarray):
            return scores.tolist()
        return [float(s) for s in scores]

    # ---------- 对外接口 ----------

    def rerank(self, query: str, results: list, top_k: int) -> list:
        """按查询对候选结果重排序，返回分数最高的 top_k 条。

        Args:
            query: 用户查询
            results: 候选结果列表（元素需含 .content 字段，如 RetrievalResult）
            top_k: 返回条数

        Returns:
            重排后的 top_k 条结果（保持原对象引用）
        """
        if not self.enabled or not results:
            return list(results)[:top_k]
        contents = [r.content for r in results]
        scores = self._score_pairs([(query, c) for c in contents])
        ranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)
        return [r for r, _score in ranked[:top_k]]


def create_reranker(config: dict) -> Reranker:
    """创建 Reranker 实例（由 ComponentRegistry 调用）。

    Args:
        config: "rerank" 分类的配置字典

    Returns:
        Reranker 实例（默认关闭）
    """
    enabled = config.get("rerank.enabled", "false").strip().lower() == "true"
    return Reranker(
        model_name=config.get("rerank.model", DEFAULT_RERANKER_MODEL),
        device=config.get("rerank.device","cpu"),
        candidates=int(config.get("rerank.candidates", "20")),
        recall_threshold=float(config.get("rerank.recall_threshold", "0.1")),
        enabled=enabled,
    )
