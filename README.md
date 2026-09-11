# 智能客服系统（Intelligent Customer）

基于 RAG 的企业级智能客服系统。Turborepo 管理的 pnpm monorepo：前端 Next.js，后端 FastAPI + LangGraph，向量检索走 Chroma。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端框架 | Next.js 16（App Router）+ React 19 |
| UI | Tailwind CSS v4 + shadcn/ui（`packages/ui` 共享组件） |
| 前端状态 | Zustand |
| 国际化 | next-intl（`zh-CN` / `en-US`） |
| LLM 交互 | Vercel AI SDK（`ai` v7 + `@ai-sdk/react` v4，UIMessageStream 协议） |
| Markdown 流式渲染 | Streamdown |
| 后端框架 | FastAPI + Uvicorn |
| AI 框架 | LangChain + LangGraph |
| 数据库 | MySQL（SQLAlchemy 异步 + AsyncMy） |
| 向量数据库 | Chroma |
| Embedding / Reranker | sentence-transformers（本地推理，CPU 可跑） |
| 认证 | JWT + OAuth2（PyJWT + passlib/bcrypt） |
| 包管理 | pnpm 10（Node ≥ 20）/ uv（Python ≥ 3.14） |
| 构建编排 | Turborepo |

## 目录结构

```text
intelligent-customer/
├── apps/
│   ├── web/                    # Next.js 前端
│   │   ├── app/                # 路由：/chat /knowledge /users /config /tools /tickets /login /register
│   │   ├── components/         # 页面组件（chat/ 为聊天模块，layout/ 为外壳）
│   │   ├── services/           # 后端 API 调用封装
│   │   ├── store/              # Zustand store
│   │   ├── messages/           # next-intl 语言包
│   │   ├── config/             # 菜单配置、权限过滤
│   │   └── __tests__/          # Vitest 单测
│   └── service/                # FastAPI 后端
│       ├── app/                # 应用入口、中间件、路由挂载、依赖注入
│       ├── api/                # 接口层（auth/chat/conversations/knowledge/...）
│       ├── agent/              # Agent 工厂、Prompt、工具（knowledge/enterprise/chat）
│       ├── rag/                # RAG 摄取 / 检索 / 生成 / 评估
│       ├── models/             # LLM / Embedding / Reranker 模型封装
│       ├── database/           # MySQL 异步引擎、ORM 模型
│       ├── services/           # 业务服务层
│       ├── configs/            # 配置类 + LLM/Embedding/向量库 yaml
│       └── tests/              # Pytest 单测
├── packages/
│   ├── ui/                     # 共享 shadcn/ui 组件 + 全局样式
│   ├── fetch-client/           # 统一请求客户端（拦截器、错误类型）
│   ├── eslint-config/          # 共享 ESLint 配置
│   └── typescript-config/      # 共享 tsconfig
├── docs/                       # 项目设计方案、架构文档
├── openspec/                   # OpenSpec 规格与变更记录
├── docker-compose.yml          # mysql / redis / chroma / service / web
└── Makefile                    # 常用命令入口
```

## 快速开始

### 1. 环境要求

- Node.js ≥ 20、pnpm 10
- Python ≥ 3.14、[uv](https://docs.astral.sh/uv/)
- Docker（跑 MySQL / Redis / Chroma）

### 2. 安装依赖

```bash
make bootstrap        # 等价于 pnpm install && cd apps/service && uv sync
```

### 3. 配置环境变量

`.env*` 已被 gitignore，需要手动创建两份：

**`apps/service/.env`**（后端）

```bash
APP_HOST=0.0.0.0
APP_PORT=8009
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000

DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=00000000
DB_NAME=intellgent-customer-db

# 预留：后端目前不读这些变量（database/redis.py 是空实现，compose 中 redis 也已注释）
REDIS_HOST=localhost
REDIS_PORT=6379

JWT_SECRET=<随机字符串>
JWT_EXPIRE_MINUTES=10080
ADMIN_PASSWORD=<初始化管理员密码>

CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_COLLECTION=knowledge_base

RAG_TOP_K=4
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=64
RAG_SCORE_THRESHOLD=0.3

# 本地跑 Embedding/Reranker 用 cpu，Mac 可用 mps，有 NVIDIA 显卡可改 cuda
EMBEDDING_DEVICE=cpu

# 可选：LangSmith 追踪（由 LangChain SDK 直接读取）
LANGSMITH_TRACING=false
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=intelligent-customer
```

> 以上是运行必需的核心变量，完整列表（连接池、日志、Redis 超时等）见 [apps/service/configs/config.py](apps/service/configs/config.py)。

**`apps/web/.env.development`**（前端）

```bash
NEXT_PUBLIC_API_URL=http://localhost:8009
NEXT_PUBLIC_API_BASE_URL=/api
# 后端静态挂载的上传目录，用于 PDF 预览直链
NEXT_PUBLIC_FILE_BASE_URL=http://localhost:8009/data/uploads
```

> `NEXT_PUBLIC_` 前缀的变量会被编译期注入浏览器，其余变量仅服务端可读，不要把密钥放进 `NEXT_PUBLIC_*`。

### 4. 启动基础设施

```bash
docker compose up -d mysql chroma
```

数据卷都是项目内命名卷（`intelligent-customer_*`），clone 后可直接创建，无需手工建卷。

> **从旧配置迁移**：如果本机已有旧数据，旧配置用的是 external 卷 `ling-diary_mysql_data` 和宿主机目录 `/Users/superhuan/chroma_data`，换卷后不会被自动继承。首次 `up` 之前执行 [docker-compose.yml](docker-compose.yml) 底部注释里的两条 `docker run ... cp -a` 迁移命令，否则 MySQL 会重新走种子数据初始化、Chroma 的向量需要重新摄取文档。

### 5. 启动应用

```bash
# 本地开发（turbo 并行拉起 web + service）
pnpm dev          # web: http://localhost:3000   service: http://localhost:8009

# 或整栈容器化
docker compose up -d
```

验证：

```bash
curl http://localhost:8009/health
```

部署到非本机时，需要通过环境变量覆盖 `NEXT_PUBLIC_API_URL` 和 `NEXT_PUBLIC_FILE_BASE_URL`（compose 里已留 `${...:-默认值}` 占位），后端 `CORS_ORIGINS` 也要同步改。

## 常用命令

| 命令 | 说明 |
| --- | --- |
| `make bootstrap` | 安装前端 + 后端依赖 |
| `pnpm dev` | 并行启动所有应用的开发模式 |
| `pnpm build` | 构建全部应用 |
| `pnpm lint` | ESLint 检查 |
| `pnpm format` | Prettier 格式化 |
| `pnpm typecheck` | 全量类型检查 |
| `pnpm --filter web test` | 前端单元测试（Vitest） |
| `cd apps/service && uv run --no-sync python -m pytest tests/ -v` | 后端单元测试（Pytest）。注意必须是 `python -m pytest`：项目无 `[build-system]`，裸 `pytest` 不会把项目根加进 `sys.path`，会报 `No module named 'rag'` |
| `docker compose logs -f service` | 查看后端日志 |

## 服务与端口

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| web | 3000 | Next.js 前端，`/` 自动跳转 `/chat` |
| service | 8009 | FastAPI 后端，健康检查 `/health` |
| mysql | 3306 | 业务数据 |
| redis | 6379 | 预留组件，compose 中已注释；后端 `database/redis.py` 尚未实现，依赖也注释在 pyproject 里 |
| chroma | 8000 | 向量库 |

## 后端 API 概览

所有业务接口挂在 `/api` 前缀下，除认证外均需 `Authorization: Bearer <token>`。

| 模块 | 前缀 | 说明 |
| --- | --- | --- |
| 健康检查 | `/health` | 服务健康状态 |
| 认证 | `/api/auth` | 登录、注册、当前用户信息 |
| 聊天 | `/api/chat` | 发送消息（SSE 流式，UIMessageStream 协议） |
| 会话 | `/api/conversations` | 会话增删查、历史消息 |
| 知识库 | `/api/knowledge` | 文档上传、列表、删除、检索测试 |
| 企业业务 | `/api/enterprise` | 企业信息查询 |
| 工单 | `/api/tickets` | 工单创建、查询、状态更新 |
| 用户管理 | `/api/users` | 用户列表、创建、删除 |
| 工具配置 | `/api/tools` | Agent 工具开关（查询 / 按名切换） |
| 系统配置 | `/api/config` | 运行时配置读取与更新 |

## 开发工作流

本项目用 **OpenSpec** 管理功能规格、用 **Comet** 管理工作流阶段（open → design → build → verify → archive）。

- `openspec/specs/` — 已归档的能力规格（chat-conversation、knowledge-base、user-auth 等）
- `openspec/changes/` — 进行中的变更提案
- 阶段规则见 [CLAUDE.md](CLAUDE.md) 和 `.claude/rules/comet-phase-guard.md`

## UI 组件（shadcn/ui）

组件统一存放在 `packages/ui/src/components`，新增组件在 `web` 应用目录执行：

```bash
pnpm dlx shadcn@latest add button -c apps/web
```

业务代码中从 `ui` 包引入：

```tsx
import { Button } from "@intelligent-customer/ui/components/button";
```

## 相关文档

- [docs/项目设计方案.md](docs/项目设计方案.md) — 整体设计方案
- [apps/service/README.md](apps/service/README.md) — 后端详细说明（部分章节待更新）
- [apps/service/docs/python-rag-agent-project-structure.md](apps/service/docs/python-rag-agent-project-structure.md) — 后端架构设计
- [AGENTS.md](AGENTS.md) — 仓库约定与 Agent 规则
