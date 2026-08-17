"""知识库检索工具 —— 通过 RAG 检索知识库并生成回答。"""

import logging

from langchain_core.tools import tool

from configs.config import settings

logger = logging.getLogger("intelligent-customer.agent.tools.knowledge")


@tool
async def knowledge_base_query(query: str) -> str:
    """当用户询问业务流程、办理条件、服务规范、常见问题等知识性问题时使用此工具。
    输入为用户的完整问题，工具会检索知识库中与问题最相关的文档片段并返回。

    触发条件示例：
    - "企业开户需要什么材料？"
    - "对公转账的办理流程是什么？"
    - "电子发票怎么申领？"
    - "服务规范有哪些要求？"
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
