## Why

论文 5.x 章节收尾存在若干一致性、安全与评估支撑缺口：会话列表按"更新时间倒序"但发消息不更新会话 `updated_at`（排序失真）；知识库检索测试接口 `/api/knowledge/query` 仅需登录、与 upload/list/delete 的 admin 限制不一致；上传仅扩展名白名单、缺大小上限与内容校验；`pyproject.toml` 残留未用依赖；缺少支撑"RAG 较纯 LLM 提升 35 个百分点"结论的评估脚本；论文 5.2"20 份测试文档"尚未入库。

## What Changes

- **S4 会话排序**：发消息后 touch 会话 `updated_at`，保证会话列表"按更新时间倒序"与论文一致（`services/message.py` + 会话服务）。
- **S5 检索接口权限**：`POST /api/knowledge/query` 增加 admin 校验，与 upload/list/delete 的权限一致（`api/knowledge.py`）。
- **S7 上传安全强化**：知识库上传增加 20MB 大小上限 + 内容校验（PDF 可解析性/非空），不仅依赖扩展名白名单（`services/knowledge.py`）。
- **O1 依赖清理**：`pyproject.toml` 移除或注释未使用的 `streamlit`/`redis`/`flagembedding`（源码零引用，已核实）。
- **P4 评估脚本**：新增 `rag/evaluation/benchmark.py`——同一组 20–30 道企业问答（答案源自 20 份企业文档），纯 LLM 与 RAG 各跑一遍，输出准确率对比表，支撑论文"35 个百分点"结论。
- **P3 文档入库**：将 20 份企业测试 PDF（`~/Desktop/bg/rag-test-docs-enterprise/`）经 admin 上传接口入库，状态 `ready`，作为论文 5.2 测试集。

## Capabilities

### New Capabilities
- `knowledge-base`: 知识库文档管理与检索的行为规范——上传大小上限与内容校验、检索接口 admin 权限（强化现有 upload/query 行为）
- `rag-evaluation`: 论文评估支撑——benchmark 脚本对同一组题目执行纯 LLM 与 RAG 对比，输出准确率对比

### Modified Capabilities
- `chat-conversation`: 会话 `updated_at` 随消息更新（发消息 touch 会话），保证会话列表按更新时间倒序

## Impact

- 后端：`services/message.py`（S4）、会话服务（S4 touch）、`api/knowledge.py`（S5）、`services/knowledge.py`（S7）、`pyproject.toml`（O1）、`rag/evaluation/benchmark.py`（P4，新）
- 数据：知识库新增 20 份企业测试文档（P3）
- 无 schema 变更、无破坏性接口变更（S5 收紧检索接口权限为 admin 属既有 upload/list/delete 一致化）
