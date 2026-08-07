# AI 客服系统 — Service 后端

基于 FastAPI + LangGraph + RAG 的智能客服后端服务。

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| AI 框架 | LangGraph + LangChain |
| 数据库 | MySQL (AsyncMy) + Redis |
| 向量数据库 | Milvus / Chroma (待实现) |
| LLM | 智谱 GLM / DeepSeek / OpenAI |
| 认证 | JWT + OAuth2 |

## 项目结构

```
service/
├── main.py                          # 启动入口
├── pyproject.toml                   # 依赖管理
├── .env                             # 环境变量
├── Makefile                         # 构建/运行命令
│
├── app/                             # 应用入口
│   ├── main.py                      # FastAPI 实例、中间件、路由挂载
│   ├── lifespan.py                  # 生命周期管理（启动/关闭）
│   └── dependencies.py              # 依赖注入
│
├── api/                             # API 接口层
│   ├── health.py                    # 健康检查
│   ├── auth.py                      # 认证接口（登录/注册/用户信息）
│   ├── agent.py                     # Agent 聊天接口（同步/流式）
│   └── knowledge.py                 # 知识库接口（待实现）
│
├── agent/                           # Agent 核心
│   ├── factory.py                   # Agent 工厂
│   ├── prompts.py                   # Prompt 模板
│   ├── memory.py                    # Agent 记忆
│   └── tools/                       # Agent 工具
│
├── rag/                             # RAG 核心
│   ├── ingestion/                   # 文档摄取（加载/清洗/切片/向量化）
│   ├── retrieval/                   # 检索（向量搜索/混合检索/重排序）
│   ├── generation/                  # 生成（Prompt 组装/上下文构建/LLM 回答）
│   └── evaluation/                  # 评估（检索质量/回答质量）
│
├── models/                          # 模型层
│   ├── factory.py                   # LLM 工厂
│   ├── embedding.py                 # Embedding 模型
│   └── reranker.py                  # Reranker 模型
│
├── vectorstore/                     # 向量数据库（待实现）
│
├── memory/                          # 记忆模块
│   ├── checkpointer.py              # LangGraph 状态持久化
│   └── history.py                   # 对话历史管理
│
├── database/                        # 数据库层
│   ├── mysql.py                     # MySQL 异步引擎
│   ├── redis.py                     # Redis 客户端
│   ├── session.py                   # 数据库会话依赖注入
│   └── models.py                    # ORM 模型
│
├── schemas/                         # Pydantic Schema
│   └── user.py                      # 用户 Schema
│
├── auth/                            # 认证安全
│   └── security.py                  # JWT 验证 + get_current_user
│
├── services/                        # 业务服务层
│   └── auth.py                      # 用户认证/注册/seed
│
├── configs/                         # 配置中心
│   ├── config.py                    # 全局配置类
│   ├── llm.yaml                     # LLM 模型配置
│   ├── embedding.yaml               # Embedding 模型配置
│   └── vector_store.yaml            # 向量数据库配置
│
├── utils/                           # 工具层
│   ├── response.py                  # 统一响应格式
│   ├── jwt.py                       # JWT 生成/验证
│   └── password.py                  # 密码哈希
│
├── data/                            # 数据目录（运行时）
├── scripts/                         # 脚本目录
├── docs/                            # 文档
│   └── python-rag-agent-project-structure.md  # 项目架构设计文档
│
└── tests/                           # 测试
    ├── test_auth_service.py
    ├── test_jwt_utils.py
    ├── test_password_utils.py
    ├── test_response_utils.py
    └── test_user_model.py
```

## API 接口

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |

### 认证

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/login` | 用户登录 | 否 |
| POST | `/api/auth/register` | 用户注册 | 否 |
| GET | `/api/auth/me` | 获取当前用户信息 | 是 |

### Agent 聊天

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/agent/chat` | 同步聊天 | 否 |
| POST | `/api/agent/chat-stream` | SSE 流式聊天 | 否 |

### 知识库（待实现）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/knowledge/upload` | 上传文档 | 是 |
| GET | `/api/knowledge/list` | 知识库列表 | 是 |
| GET | `/api/knowledge/{id}` | 知识库详情 | 是 |
| DELETE | `/api/knowledge/{id}` | 删除知识库 | 是 |

## 快速开始

### 1. 安装依赖

```bash
cd apps/service
uv sync
```

### 2. 配置环境变量

复制 `.env` 文件，填入实际配置：

```bash
# 必填项
ZAI_API_KEY=your_zhipu_api_key
ZAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
JWT_SECRET=your_jwt_secret
```

### 3. 启动服务

```bash
# 开发模式
make dev

# 或直接运行
uvicorn app.main:app --host 0.0.0.0 --port 8009 --reload
```

### 4. 验证

```bash
curl http://localhost:8009/health
```

## RAG 流程

```
用户问题 → FastAPI → Agent → RAG Pipeline
                                    ↓
                              Retriever → Vector DB
                                    ↓
                              Reranker → Top-K Documents
                                    ↓
                              Prompt Assembly + LLM
                                    ↓
                              回答
```

## 实现状态

| 模块 | 状态 | 说明 |
|------|------|------|
| FastAPI 框架 | ✅ 已完成 | CORS、生命周期、路由挂载 |
| 用户认证 | ✅ 已完成 | 注册/登录/JWT/密码哈希 |
| Agent 聊天 | ✅ 已完成 | 同步 + SSE 流式 |
| LLM 接入 | ✅ 已完成 | 智谱 GLM-4.5-Air |
| 统一响应格式 | ✅ 已完成 | { code, message, data } |
| Agent 记忆 | 🔄 待实现 | 多轮对话、会话上下文 |
| Agent 工具 | 🔄 待实现 | 知识库检索、对话历史 |
| RAG 摄取 | 🔄 待实现 | 文档加载/清洗/切片/向量化 |
| RAG 检索 | 🔄 待实现 | 向量搜索/混合检索/重排序 |
| RAG 生成 | 🔄 待实现 | Prompt 组装/上下文构建 |
| RAG 评估 | 🔄 待实现 | 检索质量/回答质量评估 |
| 知识库 API | 🔄 待实现 | 文档上传/查询/删除 |
| Redis 客户端 | 🔄 待实现 | 会话缓存/速率限制 |
| 向量数据库 | 🔄 待实现 | Milvus/Chroma 接入 |
