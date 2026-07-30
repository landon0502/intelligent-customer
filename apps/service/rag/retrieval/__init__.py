"""RAG 检索模块 —— 负责向量搜索、混合检索和重排序。"""

# 流程：问题 → Retriever → Top-K Documents → Reranker
