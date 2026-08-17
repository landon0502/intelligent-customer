## 组 1：会话排序与检索权限（S4、S5）

### Task 1: 会话 updated_at 随消息更新
- [x] `services/message.py` `create_message` 内 touch 会话：`UPDATE conversation SET updated_at = NOW()`（复用 `Conversation` ORM，新增会话服务辅助函数或内联）
- [x] 单测：创建消息后会话 `updated_at` 更新且等于最新时间

### Task 2: 检索接口 admin 权限
- [x] `api/knowledge.py` `POST /api/knowledge/query` 增加 admin 校验：非 admin → `error(40003, "仅管理员可检索知识库")`
- [x] 单测：非 admin 请求 query 返回 40003；admin 正常检索

## 组 2：上传安全强化（S7）

### Task 3: 上传大小与内容校验
- [x] `services/knowledge.py` `upload_document`：增加 20MB 大小上限校验（超限拒绝）
- [x] 增加内容校验：`pypdf` 解析失败或页数为空 → 拒绝（内容无效提示）
- [x] 单测：超 20MB 拒绝、损坏 PDF 拒绝、正常 PDF 通过

## 组 3：依赖清理（O1）

### Task 4: pyproject.toml 依赖清理
- [x] `apps/service/pyproject.toml` 注释 `streamlit`/`redis`/`flagembedding` 三项并加说明（源码零引用）
- [x] 验证：依赖解析/安装不受影响（`pip install -e .` 或 `uv pip install` 模拟通过）

## 组 4：评估脚本（P4）

### Task 5: benchmark 题目集
- [x] 基于 20 份企业 PDF 内容生成 `rag/evaluation/questions.json`：20–30 道问答（问题/参考答案/来源文档）

### Task 6: benchmark.py 评估脚本
- [x] 新增 `rag/evaluation/benchmark.py`：加载题目集 → `--mode pure`（LLM 直答）与 `--mode rag`（检索注入后回答）→ 参考答案比对判定 → 输出准确率对比表并保存报告
- [x] 复用 `models.factory` LLM 工厂与 `rag.retrieval.retrieve`；支持 `--limit N` 小批量
- [x] 运行验证：`--limit 3` 纯 LLM 与 RAG 各跑一次，输出对比表

## 组 5：文档入库（P3）

### Task 7: 20 份企业 PDF 入库
- [ ] 启动后端（admin 登录）→ 上传 `~/Desktop/bg/rag-test-docs-enterprise/` 下 20 份 PDF
- [ ] 确认 20 份文档全部入库、状态可检索（`ready`），无失败残留

## 组 6：全量验证

### Task 8: 全量测试与回归
- [ ] `cd apps/service && .venv/bin/python -m pytest tests/ -q` 全量通过（含新增用例）
- [ ] 确认既有会话/知识库/上传相关测试无回归
