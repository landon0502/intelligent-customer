"""RAG 生成模块 —— Prompt 组装 + LLM 回答生成。"""

import logging
import time
from dataclasses import dataclass, field

from langchain_core.output_parsers import StrOutputParser

from rag.retrieval.prompts import RAG_PROMPT_TEMPLATE
from rag.retrieval.retriever import RetrievalResult

logger = logging.getLogger("intelligent-customer.rag.generation")


@dataclass
class GenerationResult:
    """生成结果。"""

    answer: str
    sources: list[dict] = field(default_factory=list)


def _format_context(chunks: list[RetrievalResult]) -> str:
    """将检索结果格式化为上下文字符串。"""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        filename = chunk.metadata.get("filename", "未知文档")
        content = chunk.content.strip()
        parts.append(f"[来源{i}] 文件：{filename} | 内容：{content}")
    return "\n".join(parts)


def _extract_sources(chunks: list[RetrievalResult]) -> list[dict]:
    """从检索结果中提取来源信息。"""
    return [
        {
            "filename": chunk.metadata.get("filename", "未知文档"),
            "chunk_index": chunk.metadata.get("chunk_index", 0),
            "score": round(chunk.score, 4),
        }
        for chunk in chunks
    ]


async def generate_answer(
    query: str, context_chunks: list[RetrievalResult]
) -> GenerationResult:
    """基于检索结果生成回答。"""
    if not context_chunks:
        return GenerationResult(
            answer="抱歉，我在知识库中没有找到相关信息，无法回答您的问题。",
            sources=[],
        )

    # 组装上下文
    context = _format_context(context_chunks)
    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=query)

    # 调用 LLM
    t0 = time.time()
    from app.main import app
    llm = app.state.registry.get("rag_llm")
    chain = llm | StrOutputParser()
    answer = await chain.ainvoke(prompt)
    logger.info("LLM 生成耗时: %.2fs", time.time() - t0)

    # 提取来源
    sources = _extract_sources(context_chunks)

    logger.info("RAG 回答生成完成, 来源数: %d", len(sources))
    return GenerationResult(answer=answer, sources=sources)
