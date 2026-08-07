"""知识库检索工具 —— 通过 RAG 检索知识库并生成回答。"""

import logging

from langchain_core.tools import tool

from configs.config import settings

logger = logging.getLogger("intelligent-customer.agent.tools.knowledge")


@tool
async def knowledge_base_query(query: str) -> str:
    """当用户询问业务规则、产品信息、退货政策、配送说明、会员权益等知识性问题时使用此工具。
    输入为用户的完整问题，工具会检索知识库中与问题最相关的文档片段并返回。

    触发条件示例：
    - "退货政策是什么？"
    - "配送需要多长时间？"
    - "你们有什么产品？"
    - "会员有什么权益？"
    """
    from rag.retrieval import retrieve
    from rag.generation import generate_answer

    # 在同步工具中运行异步检索
    try:
        chunks = await retrieve(query, top_k=settings.RAG_TOP_K)
        result = await generate_answer(query, chunks)
    except Exception as e:
        logger.error("RAG 检索失败: %s", e)
        return "知识库检索暂时不可用，请稍后重试。"

    if not result.sources:
        return "在知识库中未找到相关信息。"

    # 组装来源信息
    sources_text = "、".join(s["filename"] for s in result.sources)
    return f"{result.answer}\n\n[来源：{sources_text}]"
