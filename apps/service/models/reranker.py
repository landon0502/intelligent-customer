"""Reranker 重排序模块 —— Qwen3-Reranker 交叉编码器重排检索候选。

检索-重排序（retrieve-then-rerank）：向量召回宽集 → 交叉编码器精排 → 取 Top-K。
Qwen3-Reranker-0.6B 通过 transformers 直接加载（FlagEmbedding 映射表不含 Qwen3 系列）。

模型懒加载：enabled=false 时不加载、零成本；首次启用时从 HuggingFace 下载并载入。
rerank() 为同步阻塞方法（torch 推理），调用方应通过 asyncio.to_thread 放入线程池。

批处理设计：并发请求的 (query, doc) 对在 BATCH_MAX_WAIT 窗口内合并为单个 batch，
由唯一后台工作线程统一 predict。收益：
  1. 单个 predict 处理多个请求的候选对，MPS 利用率显著提升（压测显示并发下
     逐请求 predict 排队是主要瓶颈，均值 12-32s/次）；
  2. 推理收敛到单线程，天然避免并发推理破坏 MPS 模型状态（无需信号量）；
  3. 并发首次加载仍由 _load_lock 保护。
"""

import logging
import threading
import time
from collections import deque

logger = logging.getLogger("intelligent-customer.rag.reranker")

DEFAULT_RERANKER_MODEL = "Qwen/Qwen3-Reranker-0.6B"
# 每批最多合并的请求数（infer_concurrency 语义：控制批大小而非并发线程数）
DEFAULT_INFER_CONCURRENCY = 20
# 批收集窗口（秒）：首请求到达后再等一小段时间，让更多并发请求加入同批
BATCH_MAX_WAIT = 0.05
# CrossEncoder.predict 内部 batch_size（过大在内存紧张时可能 OOM）
BATCH_PREDICT_BATCH_SIZE = 32
# 单次批处理等待结果的上限（秒）
BATCH_RESULT_TIMEOUT = 90


class _BatchRequest:
    """一次待批处理的打分请求。"""

    __slots__ = ("pairs", "result", "error", "done")

    def __init__(self, pairs: list[tuple[str, str]]):
        self.pairs = pairs
        self.result: list[float] | None = None
        self.error: Exception | None = None
        self.done = threading.Event()


class Reranker:
    """Qwen3-Reranker 交叉编码器重排序器（批处理）。"""

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER_MODEL,
        device: str = "cpu",
        candidates: int = 20,
        recall_threshold: float = 0.1,
        enabled: bool = False,
        infer_concurrency: int = DEFAULT_INFER_CONCURRENCY,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.candidates = candidates
        self.recall_threshold = recall_threshold
        self.enabled = enabled
        self._model = None
        self._tokenizer = None
        # 加载锁：仅防止并发首次加载；推理由单 worker 线程串行执行
        self._load_lock = threading.Lock()
        # 批处理队列与工作线程
        self._queue: deque[_BatchRequest] = deque()
        self._cond = threading.Condition()
        self._worker: threading.Thread | None = None
        self._batch_size = max(1, int(infer_concurrency))

    # ---------- 内部：懒加载 + 批处理 ----------

    def _ensure_loaded(self) -> None:
        """加载模型（仅首次调用；下载 + 载入耗时较长）。

        Qwen3-Reranker 仓库为标准 cross-encoder 结构（config_sentence_transformers.json
        + 1_LogitScore/），用 sentence-transformers CrossEncoder 加载；根 config.json 是
        纯 Qwen3 因果 LM 配置，不能直接用 AutoModelForSequenceClassification 加载。
        """
        if self._model is not None:
            return
        with self._load_lock:
            # double-checked locking：避免并发首次调用重复加载
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

    def _ensure_worker(self) -> None:
        """懒启动批处理工作线程（daemon，随进程退出）。"""
        if self._worker is None:
            self._worker = threading.Thread(
                target=self._worker_loop,
                name="reranker-batch",
                daemon=True,
            )
            self._worker.start()

    def _worker_loop(self) -> None:
        """后台工作线程：收集一批请求 → 合并 predict → 按请求分发结果。"""
        self._ensure_loaded()
        while True:
            batch = self._collect_batch()
            if not batch:
                continue
            # 合并所有请求的 (query, doc) 对为单个 batch
            all_pairs: list[tuple[str, str]] = []
            for req in batch:
                all_pairs.extend(req.pairs)

            t0 = time.monotonic()
            try:
                scores = self._model.predict(
                    all_pairs,
                    batch_size=BATCH_PREDICT_BATCH_SIZE,
                    convert_to_numpy=True,
                )
                import numpy as np

                if isinstance(scores, np.ndarray):
                    flat = scores.tolist()
                else:
                    flat = [float(s) for s in scores]
            except Exception as e:  # noqa: BLE001 —— 批内任一失败，整批标记错误
                logger.error("reranker 批处理预测失败（%d 个请求，%d 对）: %s",
                             len(batch), len(all_pairs), e)
                for req in batch:
                    req.error = e
                    req.done.set()
                continue

            # 按请求切分结果
            idx = 0
            for req in batch:
                n = len(req.pairs)
                req.result = flat[idx: idx + n]
                idx += n
                req.done.set()
            logger.debug("reranker 批处理: %d 个请求 / %d 对, 耗时 %.2fs",
                         len(batch), len(all_pairs), time.monotonic() - t0)

    def _collect_batch(self) -> list[_BatchRequest]:
        """等待并收集一批请求（受 _batch_size 上限与收集窗口约束）。"""
        with self._cond:
            # 等第一个请求；超时且队列空则返回空（循环继续）
            self._cond.wait_for(lambda: bool(self._queue), timeout=BATCH_MAX_WAIT)
            if not self._queue:
                return []

            # 收集窗口：首请求到达后再等 BATCH_MAX_WAIT，让更多并发请求加入同批
            deadline = time.monotonic() + BATCH_MAX_WAIT
            while time.monotonic() < deadline and len(self._queue) < self._batch_size:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._cond.wait(timeout=min(remaining, 0.005))

            batch: list[_BatchRequest] = []
            while self._queue and len(batch) < self._batch_size:
                batch.append(self._queue.popleft())
            return batch

    def _score_pairs(self, pairs: list[tuple[str, str]]) -> list[float]:
        """对 (query, document) 对打分：提交批处理队列并等待结果。

        注意：阻塞调用方所在线程（asyncio.to_thread），不占用事件循环。
        """
        self._ensure_loaded()
        req = _BatchRequest(pairs)
        with self._cond:
            self._queue.append(req)
            self._cond.notify()
        self._ensure_worker()

        if not req.done.wait(timeout=BATCH_RESULT_TIMEOUT):
            raise TimeoutError(f"reranker 批处理等待超时（>{BATCH_RESULT_TIMEOUT}s）")
        if req.error is not None:
            raise req.error
        return req.result

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
        device=config.get("rerank.device", "cpu"),
        candidates=int(config.get("rerank.candidates", "20")),
        recall_threshold=float(config.get("rerank.recall_threshold", "0.1")),
        enabled=enabled,
        infer_concurrency=int(config.get("rerank.infer_concurrency", DEFAULT_INFER_CONCURRENCY)),
    )
