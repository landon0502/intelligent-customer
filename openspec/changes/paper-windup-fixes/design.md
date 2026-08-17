# Design: 论文收尾修正（会话排序/检索权限/上传强化/依赖清理/评估脚本/文档入库）

## Context

论文 5.x 收尾需补齐 6 项：会话 `updated_at` 随消息更新（S4）、检索接口 admin 权限一致化（S5）、上传大小+内容校验（S7）、依赖清理（O1）、benchmark 评估脚本（P4）、20 份企业文档入库（P3）。均为小范围后端改动，无 schema 变更。

现状：
- `services/message.py` `create_message` 只创建消息，不 touch 会话 `updated_at`（`Conversation` 已有该字段）。
- `api/knowledge.py` `POST /query` 仅 `get_current_user`，upload/list/delete 均限 admin。
- `services/knowledge.py` `upload_document` 仅扩展名白名单。
- `pyproject.toml` 含 `streamlit`/`redis`/`flagembedding`（源码零引用，已核实）。
- `rag/evaluation/` 为空；RAG 检索可复用 `rag.retrieval.retrieve`。
- 20 份企业 PDF 已就绪于 `~/Desktop/bg/rag-test-docs-enterprise/`。

## Decisions

### D1. S4 会话 updated_at 随消息更新
在 `create_message`（`services/message.py`）内同步 `UPDATE conversation SET updated_at = NOW() WHERE id = conversation_id`（或复用 ORM 会话对象 touch）。保证会话列表按 `updated_at` 倒序与论文一致。不新增字段（`Conversation.updated_at` 已存在）。

### D2. S5 检索接口 admin 权限
`api/knowledge.py` 的 `POST /api/knowledge/query` 增加 `current_user.role != "admin"` → `error(40003, ...)`，与 upload/list/delete 一致。

### D3. S7 上传大小 + 内容校验
`services/knowledge.py` `upload_document`：
- 大小：`len(content) > 20 * 1024 * 1024` → 拒绝（40004 或复用既有错误码，返回大小超限提示）。
- 内容：用 `pypdf` 尝试解析，页数为 0 或文本为空 → 拒绝（内容无效提示）。
- 保留现有扩展名白名单，新增两层校验。

### D4. O1 依赖清理
`pyproject.toml` 移除或注释 `streamlit`/`redis`/`flagembedding` 三项（源码零引用）。优先注释 + 说明（避免破坏本地 venv 安装），并确认 `pip install -e .` 或依赖解析不受影响。

### D5. P4 评估脚本 `rag/evaluation/benchmark.py`
- 题目集：`rag/evaluation/questions.json`（20–30 道企业问答，答案源自 20 份文档，含参考答案）。
- 两种模式：
  - `--mode pure`：仅 LLM（deepseek，`llm.model` 配置）直接回答。
  - `--mode rag`：检索 `rag.retrieval.retrieve` 注入上下文后由 LLM 回答。
- 判定：参考答案与 LLM 输出做关键词/语义比对（或 LLM 判分），统计答对数与准确率。
- 输出：对比表（题目数/答对数/准确率，纯 LLM vs RAG），保存报告文件。
- 复用现有 LLM 工厂（`models.factory.create_agent_llm` / `create_rag_llm`）与配置。

### D6. P3 文档入库
change 验证环节：启动后端（admin 登录）→ 逐个上传 20 份 PDF（`~/Desktop/bg/rag-test-docs-enterprise/*.pdf`）→ 确认全部入库、状态可检索（`ready`）。

## Risks / Trade-offs

- [benchmark 真实 LLM 调用消耗 API 费用] → 用户已确认真实调用；脚本支持小批量（`--limit N`）先验证。
- [S5 收紧权限影响既有检索调用方] → 检索测试接口本身为 admin 测试用途，收紧符合既有 upload/list/delete 模式。
- [S7 内容校验误拒合法文档] → 校验仅"可解析 + 非空"，不限制文本长度。
- [O1 移除依赖破坏安装] → 优先注释保留，验证安装后再决定是否彻底移除。

## Migration Plan

无 schema/数据迁移（S4 用既有 `updated_at` 字段；P3 为数据入库）。
