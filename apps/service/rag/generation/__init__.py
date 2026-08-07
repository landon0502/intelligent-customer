"""RAG 生成模块 —— 负责 Prompt 组装、上下文构建和 LLM 回答。"""

from rag.generation.chain import GenerationResult, generate_answer

__all__ = ["generate_answer", "GenerationResult"]
