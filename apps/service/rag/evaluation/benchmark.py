"""论文评估脚本 —— 同一组企业问答下纯 LLM 与 RAG 的准确率对比。

用法：
    cd apps/service
    .venv/bin/python -m rag.evaluation.benchmark --mode pure          # 纯 LLM
    .venv/bin/python -m rag.evaluation.benchmark --mode rag           # RAG（需知识库已入库 + Chroma）
    .venv/bin/python -m rag.evaluation.benchmark --mode both --limit 5  # 两者各跑前 5 题

输出：控制台准确率对比表 + report.json（题目数/答对数/准确率）。
支撑论文"RAG 较纯 LLM 提升 35 个百分点"结论。
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# 评估环境：禁用 LangSmith 追踪（避免 DNS 噪音与无关请求）
os.environ.setdefault("LANGSMITH_TRACING", "false")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
REPORT_FILE = Path(__file__).parent / "report.json"

# 每次 LLM 调用的重试次数（网络波动/长响应超时容错）
MAX_RETRIES = 3


def _content(resp) -> str:
    """兼容不同响应的文本提取。"""
    if hasattr(resp, "content"):
        return str(resp.content)
    return str(resp)


async def _load_provider():
    """构建 AsyncConfigProvider（读 DB 配置）。"""
    from configs.provider import AsyncConfigProvider
    from database.session import async_session_factory

    return AsyncConfigProvider(async_session_factory)


async def _init_rag_env(provider):
    """模拟 lifespan 初始化 registry（供 retrieve/generate 使用 app.state.registry）。"""
    from app.lifespan import _register_components
    from app.main import app
    from configs.registry import ComponentRegistry

    registry = ComponentRegistry(provider)
    _register_components(registry)
    app.state.config_provider = provider
    app.state.registry = registry
    return registry


async def _call_with_retry(coro_factory, desc: str) -> str:
    """调用 LLM 并重试（网络波动/长响应超时容错）。"""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await coro_factory()
        except Exception as e:  # noqa: BLE001 — 评估脚本需容忍任何网络/API 错误
            last_exc = e
            print(f"    [重试 {attempt}/{MAX_RETRIES}] {desc}: {type(e).__name__}", flush=True)
            await asyncio.sleep(1)
    raise last_exc


async def answer_pure(llm, question: str) -> str:
    """纯 LLM 直答。"""
    resp = await _call_with_retry(lambda: llm.ainvoke(question), f"answer[{question[:20]}]")
    return _content(resp)


async def answer_rag(question: str) -> str:
    """RAG 检索 + 生成。"""
    from configs.config import settings
    from rag.generation import generate_answer
    from rag.retrieval import retrieve

    chunks = await retrieve(question, top_k=settings.RAG_TOP_K)
    result = await generate_answer(question, chunks, rag_llm=None)
    return result.answer


async def judge(llm, reference: str, answer: str) -> bool:
    """LLM 判分：模型回答是否与参考答案要点一致（输出 1/0）。"""
    prompt = (
        "你是严谨的评判者。判断下面的模型回答是否准确回答了问题"
        "（与参考答案的要点一致，允许措辞不同）。\n\n"
        f"参考答案：{reference}\n\n模型回答：{answer[:800]}\n\n"
        "只输出一个数字：1（准确/要点一致）或 0（不准确或答非所问）。"
    )
    resp = await _call_with_retry(lambda: llm.ainvoke(prompt), "judge")
    return _content(resp).strip().startswith("1")


async def run_mode(mode: str, questions: list[dict], llm, limit: int | None) -> list[dict]:
    """运行一种模式，返回每题的作答与判定结果。"""
    results = []
    subset = questions if limit is None else questions[:limit]
    for i, q in enumerate(subset, 1):
        print(f"  [{i}/{len(subset)}] 题：{q['question'][:50]}...", flush=True)
        answer = await (
            answer_pure(llm, q["question"]) if mode == "pure" else answer_rag(q["question"])
        )
        correct = await judge(llm, q["answer"], answer)
        results.append(
            {
                "question": q["question"],
                "reference": q["answer"],
                "answer": answer[:500],
                "correct": correct,
            }
        )
    return results


def _summarize(mode: str, results: list[dict]) -> dict:
    n = len(results)
    correct = sum(1 for r in results if r["correct"])
    return {
        "mode": mode,
        "total": n,
        "correct": correct,
        "accuracy": round(correct / n, 4) if n else 0,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="纯 LLM vs RAG 准确率对比")
    parser.add_argument("--mode", choices=["pure", "rag", "both"], default="both")
    parser.add_argument("--limit", type=int, default=None, help="限制题数（小批量验证）")
    args = parser.parse_args()

    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    if not questions:
        sys.exit("questions.json 为空，请先生成题目集")

    from models.factory import create_agent_llm

    provider = await _load_provider()
    llm_config = await provider.get_category("llm")

    # 评估脚本需要更长生成时间（产品配置 llm.timeout 较短，如 15s）；
    # 深拷贝覆盖为 120s + 重试，容忍长问题回答与网络波动。
    bench_config = dict(llm_config)
    bench_config["llm.timeout"] = "120"
    bench_config["llm.max_retries"] = str(MAX_RETRIES)

    # 纯 LLM 模式直接创建；RAG 模式还需初始化 registry
    llm = create_agent_llm(bench_config)
    if args.mode in ("rag", "both"):
        await _init_rag_env(provider)

    summaries = []
    details = {"pure": [], "rag": []}

    if args.mode in ("pure", "both"):
        print(f"=== 纯 LLM 模式（{args.limit or len(questions)} 题）===")
        details["pure"] = await run_mode("pure", questions, llm, args.limit)
        summaries.append(_summarize("pure", details["pure"]))

    if args.mode in ("rag", "both"):
        print(f"=== RAG 模式（{args.limit or len(questions)} 题）===")
        details["rag"] = await run_mode("rag", questions, llm, args.limit)
        summaries.append(_summarize("rag", details["rag"]))

    # 输出对比表
    print("\n===== 准确率对比 =====")
    print(f"{'模式':<8}{'题目数':<8}{'答对数':<8}{'准确率':<10}")
    for s in summaries:
        print(f"{s['mode']:<8}{s['total']:<8}{s['correct']:<8}{s['accuracy']:.1%}")
    if len(summaries) == 2:
        delta = summaries[1]["accuracy"] - summaries[0]["accuracy"]
        print(f"\nRAG 较纯 LLM 提升：{delta:+.1%}")

    # 保存报告
    REPORT_FILE.write_text(
        json.dumps({"summaries": summaries, "details": details}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n报告已保存：{REPORT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
