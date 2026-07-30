# Python RAG Agent 项目目录结构

一个工程化的 Python RAG Agent 项目建议按照：

> 应用层 → Agent层 → RAG层 → 模型层 → 基础设施层

进行模块拆分。

适用于：

-   智能客服机器人
-   企业知识库问答
-   AI Agent 应用
-   RAG + LLM 应用

------------------------------------------------------------------------

# 一、项目整体结构

``` text
rag-agent/

├── README.md
├── pyproject.toml
├── .env
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── Makefile
│
├── configs/
├── app/
├── api/
├── agent/
├── rag/
├── models/
├── vectorstore/
├── memory/
├── database/
├── services/
├── schemas/
├── utils/
├── prompts/
├── data/
├── tests/
└── scripts/
```

------------------------------------------------------------------------

# 二、核心模块说明

## configs 配置中心

负责：

-   全局配置
-   LLM配置
-   Embedding配置
-   向量数据库配置

------------------------------------------------------------------------

## app 应用入口

负责：

-   FastAPI启动
-   生命周期管理
-   依赖注入

------------------------------------------------------------------------

## api 接口层

包含：

-   chat.py：聊天接口
-   knowledge.py：知识库接口
-   agent.py：Agent接口
-   auth.py：认证接口

------------------------------------------------------------------------

## agent Agent核心

负责：

-   Agent执行
-   任务规划
-   工具调用
-   工作流编排

结构：

``` text
User
 |
Agent Executor
 |
Planner
 |
Tools
 |
Result
```

------------------------------------------------------------------------

## rag RAG核心

目录：

``` text
rag/

├── ingestion/
├── retrieval/
├── generation/
└── evaluation/
```

### ingestion 文档处理

负责：

-   文档加载
-   文档清洗
-   文档切片
-   Embedding生成

流程：

``` text
PDF
 |
Loader
 |
Cleaner
 |
Splitter
 |
Embedding
 |
Vector DB
```

### retrieval 检索

负责：

-   向量搜索
-   混合检索
-   重排序

流程：

``` text
Question
 |
Retriever
 |
Top-K Documents
 |
Reranker
```

### generation 生成

负责：

-   Prompt组装
-   上下文构建
-   LLM回答

------------------------------------------------------------------------

# 三、模型与数据层

## models

统一封装：

-   LLM
-   Embedding
-   Reranker

支持：

-   OpenAI
-   DeepSeek
-   Claude
-   GLM
-   本地模型

------------------------------------------------------------------------

## vectorstore

支持：

-   Milvus
-   Chroma
-   PostgreSQL pgvector

------------------------------------------------------------------------

## memory

实现：

-   短期会话记忆
-   长期用户记忆
-   历史摘要

------------------------------------------------------------------------

## database

负责：

-   用户数据
-   会话数据
-   业务数据

------------------------------------------------------------------------

# 四、完整RAG流程

``` text
用户问题

    |

 FastAPI

    |

 Agent

    |

 RAG Pipeline

    |

 Retriever

    |

 Vector Database

    |

 Prompt Assembly

    |

 LLM

    |

 Answer
```

------------------------------------------------------------------------

# 五、LangChain对应关系

  目录             LangChain组件
  ---------------- -----------------
  agent            AgentExecutor
  agent/tools      Tools
  rag/ingestion    Document Loader
  rag/retrieval    Retriever
  rag/generation   Chain
  memory           Memory
  prompts          PromptTemplate
  models           ChatModel

------------------------------------------------------------------------

# 六、LlamaIndex对应关系

``` text
rag/

├── ingestion
├── index
├── query
└── agent
```

对应：

  模块        LlamaIndex
  ----------- ------------------
  index       VectorStoreIndex
  query       QueryEngine
  agent       ReAct Agent
  retrieval   Retriever

------------------------------------------------------------------------

# 七、智能客服项目推荐架构

``` text
customer-service-ai/

├── backend/

├── ai-core/
│   ├── rag/
│   ├── agent/
│   ├── memory/
│   └── prompt/

├── knowledge-base/

├── admin-web/

├── user-web/

└── deploy/
```

技术路线：

``` text
React/Vue

    |

FastAPI

    |

Agent

    |

RAG

    |

Embedding

    |

Vector Database

    |

LLM
```

------------------------------------------------------------------------

# 八、推荐技术栈

## 后端

-   Python
-   FastAPI
-   Pydantic

## AI框架

-   LangGraph
-   LangChain
-   LlamaIndex

## 模型

-   DeepSeek
-   OpenAI
-   GLM
-   Claude

## 数据库

-   PostgreSQL
-   Redis
-   Milvus

## 前端

-   React / Next.js
-   Vue3

------------------------------------------------------------------------

# 总结

核心职责划分：

``` text
API负责通信

Service负责业务

Agent负责决策

RAG负责知识

LLM负责生成
```

该结构适合：

-   企业级RAG系统
-   AI客服机器人
-   Agent应用
-   毕业论文项目实现
