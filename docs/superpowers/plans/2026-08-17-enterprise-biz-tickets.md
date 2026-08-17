---
change: enterprise-biz-tickets
design-doc: docs/superpowers/specs/2026-08-17-enterprise-biz-tickets-design.md
base-ref: 1baf075b1595b446eb2cca83a91c6f43ddc72879
---

# 企业工具真实后端 + 工单落库与后台界面 + 安全默认值加固 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把企业业务查询/工单工具从模拟数据改为真实数据库落库，新增工单管理后台页面，并加固安全默认值。

**Architecture:** 后端 `apps/service` 沿 FastAPI + SQLAlchemy async + LangChain 现有分层：新增 `enterprise_biz` 与 `service_tickets` 两张表（ORM 注册 `database/models.py` + `schemas/__init__.py`），服务层函数统一接收 `db: AsyncSession` 参数（单测用 `AsyncMock` 注入），工具改为 `async def` + `@tool`，在函数内用 `async_session_factory()` 自开独立会话并惰性 import 服务函数，用户/会话上下文通过 ContextVar 注入。前端 `apps/web` 新增 `/tickets` 工单管理页（next-intl 双语）。`.env` 强随机 `JWT_SECRET` 与强 `ADMIN_PASSWORD`，启动时校验弱默认值并告警。

**Tech Stack:** Python 3.14 / FastAPI / SQLAlchemy 2 async / LangChain `@tool` / ContextVar / pydantic v2；Next.js 16 / next-intl / ahooks / shadcn/ui（`@intelligent-customer/ui`）/ sonner。

## Global Constraints

- **语言**：本计划所有产物（代码注释、i18n 文案、git message）使用简体中文，与仓库现有风格一致。
- **Python 版本**：`apps/service` 要求 `requires-python = ">=3.14"`；测试统一 `cd apps/service && .venv/bin/python -m pytest <file> -v`（模块为顶层 import，须以 `apps/service` 为工作目录）。
- **服务函数签名**：一律接受 `db: AsyncSession` 作为首个参数（对齐 `services/knowledge.py`、`services/auth.py`），不在函数内部自建 DB 依赖。
- **工具 async 模式**：`@tool async def ...`；函数内 `async with async_session_factory() as session:` 自开独立会话；服务函数在工具函数体内部惰性 `from services.xxx import ...`（避免模块级循环 import，对齐 `agent/tools/knowledge.py`）；`create_agent`/`agent.astream` 原生支持 async 工具，无需改 agent 调用链。
- **工具 docstring 尽量保持不变**（LLM 依赖其触发说明）。
- **ORM 注册两处**：`apps/service/database/models.py` 与 `apps/service/schemas/__init__.py`（`Base.metadata.create_all` 的模型来源），两处都要加，否则新建表不会建表。
- **统一响应**：接口返回一律走 `utils/response.success()/error()`（`{code, message, data}`）；错误码沿用现有约定：`40003` 仅管理员、`40004` 非法值、`40005` 不存在、`40006` 业务编号未找到。
- **权限**：enterprise 两个 GET 仅需登录（`get_current_user`）；tickets 的 list/detail/status 接口校验 `current_user.role == "admin"`（对齐 `api/knowledge.py`）。
- **工单号**：`TK-YYYYMMDD-XXXX`，日期用 UTC；`service_tickets.ticket_no` 加唯一索引；`IntegrityError` 冲突重试一次。
- **ContextVar**：工具只读 ContextVar；缺失时降级为 `None`（写库 user_id 为 NULL），不阻断流程；`api/chat.py` 必须在 `finally` 中 reset 防跨请求泄漏。
- **前端**：新增菜单必须同时改 `apps/web/config/menu.ts`（含 `titleKeyMap`）；新增文案必须同时改 `messages/zh-CN.json` 与 `messages/en-US.json`。
- **测试**：后端单测用 `@pytest.mark.anyio` + `AsyncMock` db session（参考 `tests/test_auth_service.py`）；工具层用 `patch("services.xxx.<函数>")` 拦截服务函数（工具惰性 import 服务函数，故 patch 服务模块属性即生效，且不触发真实 DB 查询）。前端不写单测，用 `pnpm typecheck` + 手工验证。
- **测试文件归属映射**（对齐 tasks.md 第 6 组）：`tests/test_enterprise_biz.py`、`tests/test_ticket_service.py` 在对应功能任务（TDD 位置）创建/追加，第 6 组任务负责完整回归验证与补漏。

**建议执行顺序**：Task 1.1 → 1.4 → 2.1 → 2.3 → 3.3 → 3.1 → 3.2 → 4.1 → 4.3 → 5.1 → 5.2 → 6.1 → 6.3 → 7.1 → 7.2。第 3 组内部必须先做 3.3（ContextVar 基础设施），工具 3.1/3.2 依赖其函数。

---

## 文件结构（File Structure）

后端 `apps/service`：
- 新建 `schemas/enterprise_biz.py` — `EnterpriseBiz` ORM（enterprise_biz 表）
- 新建 `schemas/ticket.py` — `ServiceTicket` ORM（service_tickets 表）
- 修改 `schemas/__init__.py`、`database/models.py` — 注册两个模型
- 新建 `services/enterprise.py` — `list_businesses` / `get_business_by_code` / `seed_enterprise_businesses`
- 新建 `services/ticket.py` — `create_ticket` / `list_tickets` / `get_ticket_by_no` / `update_status`
- 新建 `api/enterprise.py` — 2 个 GET（登录即可）
- 新建 `api/tickets.py` — POST/GET 列表/GET 详情/PATCH 状态（admin）
- 修改 `api/__init__.py`、`app/main.py` — 注册两个 router
- 修改 `app/lifespan.py` — 种子初始化追加 + 安全校验调用
- 修改 `configs/config.py` — 新增 `validate_security_defaults()`
- 修改 `apps/service/.env` — 强 `JWT_SECRET` / `ADMIN_PASSWORD`
- 新建 `agent/tools/context.py` — ContextVar set/reset/get
- 修改 `agent/tools/enterprise.py` — `enterprise_query`/`ticket_submit`/`ticket_status` async 化（删除 `_MOCK_BUSINESS`/`_TICKET_COUNTER`）
- 修改 `agent/tools/chat.py` — `transfer_human` async 化（HUMAN 哨兵工单）
- 修改 `api/chat.py` — `chat_stream` 的 event_generator 内 set/reset ContextVar
- 新建 `tests/test_enterprise_biz.py`、`tests/test_ticket_service.py`

前端 `apps/web`：
- 新建 `services/tickets.ts` — fetchClient 封装
- 新建 `app/tickets/useServices.ts`、`app/tickets/page.tsx`、`app/tickets/layout.tsx`
- 修改 `config/menu.ts`、`messages/zh-CN.json`、`messages/en-US.json`

---

### Task 1.1: EnterpriseBiz ORM 模型 + 注册

**Files:**
- Create: `apps/service/schemas/enterprise_biz.py`
- Modify: `apps/service/schemas/__init__.py`
- Modify: `apps/service/database/models.py`
- Test: `apps/service/tests/test_enterprise_biz.py`（新建，含模型默认值冒烟测试）

**Interfaces:**
- Produces: `EnterpriseBiz`（`__tablename__ = "enterprise_biz"`，字段 `id/code/name/description/requirements/process/status/created_at`），供 Task 1.2 服务层使用。

- [x] **Step 1: 创建 ORM 模型文件**

`apps/service/schemas/enterprise_biz.py`：

```python
"""企业业务 ORM 模型 —— 对应 enterprise_biz 表。"""

from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.mysql import Base


class EnterpriseBiz(Base):
    __tablename__ = "enterprise_biz"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    requirements: Mapped[str] = mapped_column(Text, nullable=False)
    process: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum("active", "inactive", name="biz_status"),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
```

- [x] **Step 2: 注册到两处模型来源**

`apps/service/schemas/__init__.py` 末尾追加：

```python
from schemas.enterprise_biz import EnterpriseBiz
```

`apps/service/database/models.py` 末尾追加：

```python
from schemas.enterprise_biz import EnterpriseBiz  # noqa: F401
```

- [x] **Step 3: 写模型冒烟测试**

`apps/service/tests/test_enterprise_biz.py`（新建）：

```python
"""企业业务服务与工具层测试 —— AsyncMock db session / patch 服务函数。"""

import pytest

from schemas.enterprise_biz import EnterpriseBiz


# ========== 模型 ==========

def test_enterprise_biz_defaults():
    biz = EnterpriseBiz(
        code="B-001",
        name="企业开户",
        description="企业客户办理开户业务",
        requirements="需提供营业执照",
        process="提交申请 → 完成开户",
    )
    assert biz.status == "active"
    assert biz.id is None
```

- [x] **Step 4: 运行测试确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_enterprise_biz.py -v`
Expected: 1 passed（`test_enterprise_biz_defaults`）

- [x] **Step 5: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/schemas/enterprise_biz.py apps/service/schemas/__init__.py apps/service/database/models.py apps/service/tests/test_enterprise_biz.py
git commit -m "feat: 新增 enterprise_biz ORM 模型并注册"
```

---

### Task 1.2: 企业业务服务层（list / get / seed）

**Files:**
- Create: `apps/service/services/enterprise.py`
- Test: `apps/service/tests/test_enterprise_biz.py`（追加服务层用例）

**Interfaces:**
- Consumes: `EnterpriseBiz`（Task 1.1）
- Produces:
  - `SEED_BUSINESSES: list[dict]`（3 条种子数据）
  - `async def list_businesses(db: AsyncSession) -> list[EnterpriseBiz]`
  - `async def get_business_by_code(db: AsyncSession, code: str) -> EnterpriseBiz | None`
  - `async def seed_enterprise_businesses(db: AsyncSession) -> None`
  - 供 Task 1.3 API、Task 3.1 `enterprise_query` 使用。

- [x] **Step 1: 写失败测试**

`apps/service/tests/test_enterprise_biz.py` 追加（保持 `import pytest`、新增 `from unittest.mock import AsyncMock, MagicMock`）：

```python
from unittest.mock import AsyncMock, MagicMock

from services.enterprise import (
    list_businesses,
    get_business_by_code,
    seed_enterprise_businesses,
)


def _make_biz(code: str = "B-001"):
    return EnterpriseBiz(
        code=code,
        name="企业开户",
        description="企业客户办理开户业务",
        requirements="需提供营业执照",
        process="提交申请 → 完成开户",
        status="active",
    )


# ========== 服务层 ==========

@pytest.mark.anyio
async def test_list_businesses_returns_all():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [_make_biz("B-001"), _make_biz("B-002")]
    db.execute = AsyncMock(return_value=result)
    businesses = await list_businesses(db)
    assert len(businesses) == 2
    assert businesses[0].code == "B-001"


@pytest.mark.anyio
async def test_get_business_by_code_hit():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=_make_biz("B-001")))
    )
    biz = await get_business_by_code(db, "B-001")
    assert biz is not None
    assert biz.code == "B-001"


@pytest.mark.anyio
async def test_get_business_by_code_miss():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    biz = await get_business_by_code(db, "B-999")
    assert biz is None


@pytest.mark.anyio
async def test_seed_enterprise_businesses_inserts_when_missing():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    await seed_enterprise_businesses(db)
    assert db.add.call_count == 3


@pytest.mark.anyio
async def test_seed_enterprise_businesses_skips_when_exists():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=_make_biz("B-001")))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    await seed_enterprise_businesses(db)
    assert db.add.call_count == 0
    db.commit.assert_not_awaited()
```

- [x] **Step 2: 运行测试确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_enterprise_biz.py -v`
Expected: 失败，`ModuleNotFoundError: No module named 'services.enterprise'`

- [x] **Step 3: 实现服务层**

`apps/service/services/enterprise.py`：

```python
"""企业业务服务 —— 业务查询与幂等种子初始化。"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.enterprise_biz import EnterpriseBiz

logger = logging.getLogger("intelligent-customer.enterprise")

# 幂等种子数据：表内无对应 code 时插入
SEED_BUSINESSES: list[dict] = [
    {
        "code": "B-001",
        "name": "企业开户",
        "description": "企业客户办理开户业务",
        "requirements": "需提供营业执照、法人身份证件、公章",
        "process": "提交申请 → 资质审核 → 完成开户（3 个工作日）",
    },
    {
        "code": "B-002",
        "name": "对公转账",
        "description": "企业对公账户转账业务",
        "requirements": "需开通对公转账权限",
        "process": "填写收款方信息 → 确认金额 → 完成转账",
    },
    {
        "code": "B-003",
        "name": "电子发票申领",
        "description": "企业电子发票申领业务",
        "requirements": "已完成企业实名认证",
        "process": "提交开票信息 → 审核 → 开具电子发票（1 个工作日）",
    },
]


async def list_businesses(db: AsyncSession) -> list[EnterpriseBiz]:
    """获取全部企业业务，按 code 排序。"""
    result = await db.execute(select(EnterpriseBiz).order_by(EnterpriseBiz.code))
    return list(result.scalars().all())


async def get_business_by_code(db: AsyncSession, code: str) -> EnterpriseBiz | None:
    """按业务编号查询单条业务。"""
    result = await db.execute(select(EnterpriseBiz).where(EnterpriseBiz.code == code))
    return result.scalar_one_or_none()


async def seed_enterprise_businesses(db: AsyncSession) -> None:
    """幂等初始化企业业务种子数据；已存在的 code 跳过。"""
    inserted = 0
    for item in SEED_BUSINESSES:
        existing = await get_business_by_code(db, item["code"])
        if not existing:
            db.add(EnterpriseBiz(**item))
            inserted += 1
    if inserted:
        await db.commit()
        logger.info("企业业务种子初始化: 插入 %d 条", inserted)
```

- [x] **Step 4: 运行测试确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_enterprise_biz.py -v`
Expected: 6 passed（模型 1 + 服务层 5）

- [x] **Step 5: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/services/enterprise.py apps/service/tests/test_enterprise_biz.py
git commit -m "feat: 企业业务服务层（list/get/幂等种子初始化）"
```

---

### Task 1.3: 企业业务接口 + 路由注册

**Files:**
- Create: `apps/service/api/enterprise.py`
- Modify: `apps/service/api/__init__.py`
- Modify: `apps/service/app/main.py`

**Interfaces:**
- Consumes: `list_businesses` / `get_business_by_code`（Task 1.2）
- Produces: `GET /api/enterprise/businesses`、`GET /api/enterprise/businesses/{code}`（登录即可）。前端与 `enterprise_query` 工具（走服务层）消费。
- 说明：API 层为薄封装，按设计文档不写单测；功能验证在 Task 7.1/7.2 端到端完成。本任务以「导入成功 + 既有测试不回归」为验收。

- [x] **Step 1: 实现接口**

`apps/service/api/enterprise.py`：

```python
"""企业业务接口 —— 业务列表与单业务查询（登录即可访问）。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from auth.security import get_current_user
from services.enterprise import list_businesses, get_business_by_code
from utils.response import success, error

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])


class EnterpriseBizItem(BaseModel):
    """企业业务响应模型"""
    id: int
    code: str
    name: str
    description: str
    requirements: str
    process: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/businesses")
async def list_businesses_api(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取企业业务列表（登录即可）"""
    businesses = await list_businesses(db)
    items = [EnterpriseBizItem.model_validate(b).model_dump() for b in businesses]
    return success(data=items)


@router.get("/businesses/{code}")
async def get_business_api(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按业务编号查询单条业务（登录即可）"""
    biz = await get_business_by_code(db, code.upper())
    if not biz:
        return error(code=40006, message=f"未找到业务编号 {code}")
    return success(data=EnterpriseBizItem.model_validate(biz).model_dump())
```

- [x] **Step 2: 注册路由**

`apps/service/api/__init__.py` 末尾追加：

```python
from .enterprise import router as enterprise_router
```

`apps/service/app/main.py` 修改 import 行与注册：

```python
from api import health_router, auth_router, chat_router, conversations_router, knowledge_router, config_router, enterprise_router
```

```python
app.include_router(enterprise_router)
```

（在 `app.include_router(config_router)` 之后追加 `app.include_router(enterprise_router)`。）

- [x] **Step 3: 验证导入 + 既有测试不回归**

Run: `cd apps/service && .venv/bin/python -c "from api.enterprise import router; print(len(router.routes))"`
Expected: 输出 `2`

Run: `cd apps/service && .venv/bin/python -m pytest tests/ -q`
Expected: 全部通过（原有用例 + 新增企业用例不回归）

- [x] **Step 4: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/api/enterprise.py apps/service/api/__init__.py apps/service/app/main.py
git commit -m "feat: 企业业务查询接口（GET /api/enterprise/businesses）"
```

---

### Task 1.4: lifespan 种子初始化扩展

**Files:**
- Modify: `apps/service/app/lifespan.py`

**Interfaces:**
- Consumes: `seed_enterprise_businesses`（Task 1.2）
- Produces: 服务启动时幂等初始化 3 条企业业务种子数据（验证在 Task 7.1 日志确认）。

- [ ] **Step 1: 修改 `_seed_initial_data`**

`apps/service/app/lifespan.py` 中 `_seed_initial_data` 改为：

```python
async def _seed_initial_data() -> None:
    """初始化种子数据：创建管理员用户 + 企业业务"""
    from services.auth import seed_admin_user
    from services.enterprise import seed_enterprise_businesses

    async for db in get_db():
        await seed_admin_user(db)
        await seed_enterprise_businesses(db)
```

- [ ] **Step 2: 验证既有测试不回归**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_enterprise_biz.py -q`
Expected: 6 passed

- [ ] **Step 3: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/app/lifespan.py
git commit -m "feat: 启动时幂等初始化企业业务种子数据"
```

---

### Task 2.1: ServiceTicket ORM 模型 + 注册

**Files:**
- Create: `apps/service/schemas/ticket.py`
- Modify: `apps/service/schemas/__init__.py`
- Modify: `apps/service/database/models.py`

**Interfaces:**
- Produces: `ServiceTicket`（`__tablename__ = "service_tickets"`，字段 `id/ticket_no/user_id/conversation_id/business_code/content/status/created_at/updated_at`），供 Task 2.2 服务层使用。

- [x] **Step 1: 创建 ORM 模型文件**

`apps/service/schemas/ticket.py`：

```python
"""工单 ORM 模型 —— 对应 service_tickets 表。"""

from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.mysql import Base


class ServiceTicket(Base):
    __tablename__ = "service_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_no: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    conversation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    business_code: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum("open", "processing", "closed", name="ticket_status"),
        nullable=False,
        default="open",
        server_default="open",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

- [x] **Step 2: 注册到两处模型来源**

`apps/service/schemas/__init__.py` 末尾追加：

```python
from schemas.ticket import ServiceTicket
```

`apps/service/database/models.py` 末尾追加：

```python
from schemas.ticket import ServiceTicket  # noqa: F401
```

- [x] **Step 3: 验证导入 + 既有测试不回归**

Run: `cd apps/service && .venv/bin/python -c "from schemas.ticket import ServiceTicket; print(ServiceTicket.__tablename__)"`
Expected: 输出 `service_tickets`

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_enterprise_biz.py -q`
Expected: 6 passed

- [x] **Step 4: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/schemas/ticket.py apps/service/schemas/__init__.py apps/service/database/models.py
git commit -m "feat: 新增 service_tickets ORM 模型并注册"
```

---

### Task 2.2: 工单服务层（工单号生成 + 列表/详情/状态）

**Files:**
- Create: `apps/service/services/ticket.py`
- Test: `apps/service/tests/test_ticket_service.py`（新建，服务层用例）

**Interfaces:**
- Consumes: `ServiceTicket`（Task 2.1）
- Produces:
  - 常量 `TICKET_STATUS_OPEN = "open"`、`TICKET_STATUS_PROCESSING = "processing"`、`TICKET_STATUS_CLOSED = "closed"`、`TICKET_STATUS_VALUES`
  - `async def create_ticket(db, business_code: str, content: str, user_id: int | None = None, conversation_id: int | None = None) -> ServiceTicket`
  - `async def list_tickets(db, status: str | None = None) -> list[ServiceTicket]`
  - `async def get_ticket_by_no(db, ticket_no: str) -> ServiceTicket | None`
  - `async def update_status(db, ticket_no: str, status: str) -> ServiceTicket | None`（非法值抛 `ValueError`）
  - 供 Task 2.3 API、Task 3.1/3.2 工具使用。

- [x] **Step 1: 写失败测试**

`apps/service/tests/test_ticket_service.py`（新建）：

```python
"""工单服务与工具层测试 —— AsyncMock db session / patch 服务函数。"""

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from schemas.ticket import ServiceTicket
from services.ticket import (
    create_ticket,
    list_tickets,
    get_ticket_by_no,
    update_status,
    TICKET_STATUS_OPEN,
    TICKET_STATUS_PROCESSING,
    TICKET_STATUS_CLOSED,
)


def _today_prefix() -> str:
    return datetime.now(timezone.utc).strftime("TK-%Y%m%d-")


def _make_ticket(ticket_no: str = "TK-20260817-0001", status: str = "open"):
    return ServiceTicket(
        ticket_no=ticket_no,
        user_id=1,
        conversation_id=None,
        business_code="B-001",
        content="办理企业开户",
        status=status,
    )


# ========== 服务层 ==========

@pytest.mark.anyio
async def test_create_ticket_generates_valid_ticket_no():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    ticket = await create_ticket(db, "B-001", "办理企业开户", user_id=1)
    assert re.match(r"^TK-\d{8}-\d{4}$", ticket.ticket_no)
    assert ticket.status == TICKET_STATUS_OPEN
    assert ticket.user_id == 1
    assert ticket.business_code == "B-001"


@pytest.mark.anyio
async def test_create_ticket_sequence_increments():
    prefix = _today_prefix()
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=f"{prefix}0003"))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    ticket = await create_ticket(db, "B-001", "test")
    assert ticket.ticket_no == f"{prefix}0004"


@pytest.mark.anyio
async def test_create_ticket_retries_on_integrity_error():
    prefix = _today_prefix()
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=f"{prefix}0001"))
    )
    db.add = MagicMock()
    db.commit = AsyncMock(
        side_effect=[IntegrityError("INSERT", {}, Exception("dup")), None]
    )
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    ticket = await create_ticket(db, "B-001", "test")
    assert ticket.ticket_no == f"{prefix}0002"
    assert db.commit.await_count == 2
    db.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_list_tickets_no_filter():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _make_ticket("TK-20260817-0002"),
        _make_ticket("TK-20260817-0001"),
    ]
    db.execute = AsyncMock(return_value=result)
    tickets = await list_tickets(db)
    assert len(tickets) == 2
    assert tickets[0].ticket_no == "TK-20260817-0002"


@pytest.mark.anyio
async def test_list_tickets_with_status_filter():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _make_ticket("TK-20260817-0001", status="processing")
    ]
    db.execute = AsyncMock(return_value=result)
    tickets = await list_tickets(db, TICKET_STATUS_PROCESSING)
    assert len(tickets) == 1
    assert tickets[0].status == TICKET_STATUS_PROCESSING


@pytest.mark.anyio
async def test_get_ticket_by_no_hit():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=_make_ticket("TK-20260817-0001")))
    )
    ticket = await get_ticket_by_no(db, "TK-20260817-0001")
    assert ticket is not None
    assert ticket.ticket_no == "TK-20260817-0001"


@pytest.mark.anyio
async def test_get_ticket_by_no_miss():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    ticket = await get_ticket_by_no(db, "TK-99999999-9999")
    assert ticket is None


@pytest.mark.anyio
async def test_update_status_valid_transition():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=_make_ticket("TK-20260817-0001", status="open")))
    )
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    ticket = await update_status(db, "TK-20260817-0001", TICKET_STATUS_PROCESSING)
    assert ticket is not None
    assert ticket.status == TICKET_STATUS_PROCESSING


@pytest.mark.anyio
async def test_update_status_invalid_value_raises():
    db = AsyncMock()
    with pytest.raises(ValueError):
        await update_status(db, "TK-20260817-0001", "invalid-status")


@pytest.mark.anyio
async def test_update_status_not_found_returns_none():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    ticket = await update_status(db, "TK-99999999-9999", TICKET_STATUS_CLOSED)
    assert ticket is None
```

- [x] **Step 2: 运行测试确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_ticket_service.py -v`
Expected: 失败，`ModuleNotFoundError: No module named 'services.ticket'`

- [x] **Step 3: 实现服务层**

`apps/service/services/ticket.py`：

```python
"""工单服务 —— 工单号生成、列表/详情查询与状态流转。"""

import logging

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.ticket import ServiceTicket

logger = logging.getLogger("intelligent-customer.ticket")

TICKET_STATUS_OPEN = "open"
TICKET_STATUS_PROCESSING = "processing"
TICKET_STATUS_CLOSED = "closed"
TICKET_STATUS_VALUES = (
    TICKET_STATUS_OPEN,
    TICKET_STATUS_PROCESSING,
    TICKET_STATUS_CLOSED,
)


def _today_prefix() -> str:
    """生成工单号当日前缀 TK-YYYYMMDD-（UTC 日期）"""
    return datetime.now(timezone.utc).strftime("TK-%Y%m%d-")


async def _next_ticket_no(db: AsyncSession, prefix: str) -> str:
    """基于当日最大工单号生成下一个工单号。"""
    result = await db.execute(
        select(func.max(ServiceTicket.ticket_no)).where(
            ServiceTicket.ticket_no.like(f"{prefix}%")
        )
    )
    max_no = result.scalar_one_or_none()
    seq = int(max_no[len(prefix):]) if max_no else 0
    return f"{prefix}{seq + 1:04d}"


async def create_ticket(
    db: AsyncSession,
    business_code: str,
    content: str,
    user_id: int | None = None,
    conversation_id: int | None = None,
) -> ServiceTicket:
    """创建工单并生成 TK-YYYYMMDD-XXXX 工单号；唯一冲突时重试一次。"""
    prefix = _today_prefix()
    for attempt in range(2):
        ticket_no = await _next_ticket_no(db, prefix)
        ticket = ServiceTicket(
            ticket_no=ticket_no,
            user_id=user_id,
            conversation_id=conversation_id,
            business_code=business_code,
            content=content,
            status=TICKET_STATUS_OPEN,
        )
        db.add(ticket)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            logger.warning("工单号冲突重试: %s (attempt=%d)", ticket_no, attempt + 1)
            continue
        await db.refresh(ticket)
        return ticket
    raise RuntimeError("工单号生成冲突，请重试")


async def list_tickets(
    db: AsyncSession, status: str | None = None
) -> list[ServiceTicket]:
    """获取工单列表；status 可选过滤，按创建时间倒序。"""
    stmt = select(ServiceTicket).order_by(ServiceTicket.created_at.desc())
    if status:
        stmt = stmt.where(ServiceTicket.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_ticket_by_no(
    db: AsyncSession, ticket_no: str
) -> ServiceTicket | None:
    """按工单号查询工单。"""
    result = await db.execute(
        select(ServiceTicket).where(ServiceTicket.ticket_no == ticket_no)
    )
    return result.scalar_one_or_none()


async def update_status(
    db: AsyncSession, ticket_no: str, status: str
) -> ServiceTicket | None:
    """更新工单状态；非法状态抛 ValueError，工单不存在返回 None。"""
    if status not in TICKET_STATUS_VALUES:
        raise ValueError(f"非法工单状态: {status}")
    ticket = await get_ticket_by_no(db, ticket_no)
    if not ticket:
        return None
    ticket.status = status
    await db.commit()
    await db.refresh(ticket)
    return ticket
```

- [x] **Step 4: 运行测试确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_ticket_service.py -v`
Expected: 10 passed（全部服务层用例）

- [x] **Step 5: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/services/ticket.py apps/service/tests/test_ticket_service.py
git commit -m "feat: 工单服务层（TK-YYYYMMDD-XXXX 生成 + 列表/详情/状态流转）"
```

---

### Task 2.3: 工单接口 + 路由注册

**Files:**
- Create: `apps/service/api/tickets.py`
- Modify: `apps/service/api/__init__.py`
- Modify: `apps/service/app/main.py`

**Interfaces:**
- Consumes: `create_ticket`/`list_tickets`/`get_ticket_by_no`/`update_status`（Task 2.2）、`ServiceTicket`（Task 2.1）
- Produces: `POST /api/tickets`（登录）、`GET /api/tickets?status=`（admin）、`GET /api/tickets/{no}`（admin）、`PATCH /api/tickets/{no}/status`（admin）。响应 `TicketItem` 含 `username`（提交用户，前端展示用）。
- 说明：API 层薄封装不写单测，功能验证在 Task 7.1/7.2 端到端完成。本任务以「导入成功 + 既有测试不回归」为验收。

- [x] **Step 1: 实现接口**

`apps/service/api/tickets.py`：

```python
"""工单接口 —— 创建（登录）、列表/详情/状态更新（admin）。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.user import User
from schemas.ticket import ServiceTicket
from auth.security import get_current_user
from services.ticket import (
    create_ticket,
    list_tickets,
    get_ticket_by_no,
    update_status,
)
from utils.response import success, error

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


class TicketCreateRequest(BaseModel):
    """创建工单请求体"""
    business_code: str
    content: str
    conversation_id: int | None = None


class TicketStatusUpdateRequest(BaseModel):
    """更新工单状态请求体"""
    status: str


class TicketItem(BaseModel):
    """工单响应模型"""
    id: int
    ticket_no: str
    user_id: int | None = None
    username: str | None = None
    conversation_id: int | None = None
    business_code: str
    content: str
    status: str
    created_at: datetime
    updated_at: datetime


async def _build_username_map(
    db: AsyncSession, tickets: list[ServiceTicket]
) -> dict[int, str]:
    """按 user_id 批量查询用户名。"""
    user_ids = {t.user_id for t in tickets if t.user_id is not None}
    if not user_ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u.username for u in result.scalars().all()}


def _ticket_to_item(t: ServiceTicket, usernames: dict[int, str]) -> dict:
    return TicketItem(
        id=t.id,
        ticket_no=t.ticket_no,
        user_id=t.user_id,
        username=usernames.get(t.user_id),
        conversation_id=t.conversation_id,
        business_code=t.business_code,
        content=t.content,
        status=t.status,
        created_at=t.created_at,
        updated_at=t.updated_at,
    ).model_dump()


@router.post("")
async def create_ticket_api(
    req: TicketCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交工单（登录即可）"""
    ticket = await create_ticket(
        db,
        req.business_code,
        req.content,
        user_id=current_user.id,
        conversation_id=req.conversation_id,
    )
    return success(data=_ticket_to_item(ticket, {current_user.id: current_user.username}))


@router.get("")
async def list_tickets_api(
    status: str | None = Query(
        default=None, description="按状态筛选 open/processing/closed"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """工单列表 + 状态筛选（admin）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看工单")
    tickets = await list_tickets(db, status)
    usernames = await _build_username_map(db, tickets)
    items = [_ticket_to_item(t, usernames) for t in tickets]
    return success(data=items)


@router.get("/{no}")
async def get_ticket_api(
    no: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """工单详情（admin）"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可查看工单")
    ticket = await get_ticket_by_no(db, no)
    if not ticket:
        return error(code=40005, message="工单不存在")
    usernames = await _build_username_map(db, [ticket])
    return success(data=_ticket_to_item(ticket, usernames))


@router.patch("/{no}/status")
async def update_ticket_status_api(
    no: str,
    req: TicketStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新工单状态（admin），body {"status": "processing"|"closed"}"""
    if current_user.role != "admin":
        return error(code=40003, message="仅管理员可操作工单")
    try:
        ticket = await update_status(db, no, req.status)
    except ValueError as e:
        return error(code=40004, message=str(e))
    if not ticket:
        return error(code=40005, message="工单不存在")
    usernames = await _build_username_map(db, [ticket])
    return success(data=_ticket_to_item(ticket, usernames))
```

- [x] **Step 2: 注册路由**

`apps/service/api/__init__.py` 末尾追加：

```python
from .tickets import router as tickets_router
```

`apps/service/app/main.py` 修改 import 行与注册：

```python
from api import health_router, auth_router, chat_router, conversations_router, knowledge_router, config_router, enterprise_router, tickets_router
```

```python
app.include_router(tickets_router)
```

（在 `app.include_router(enterprise_router)` 之后追加 `app.include_router(tickets_router)`。）

- [x] **Step 3: 验证导入 + 既有测试不回归**

Run: `cd apps/service && .venv/bin/python -c "from api.tickets import router; print(len(router.routes))"`
Expected: 输出 `4`

Run: `cd apps/service && .venv/bin/python -m pytest tests/ -q`
Expected: 全部通过（不回归）

- [x] **Step 4: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/api/tickets.py apps/service/api/__init__.py apps/service/app/main.py
git commit -m "feat: 工单接口（创建/列表/详情/状态更新，admin 校验）"
```

---

### Task 3.3: ContextVar 上下文注入

> **执行顺序说明**：第 3 组内部必须先做本任务（ContextVar 基础设施），Task 3.1/3.2 的工具依赖 `agent/tools/context.py` 的函数。

**Files:**
- Create: `apps/service/agent/tools/context.py`
- Modify: `apps/service/api/chat.py`
- Test: `apps/service/tests/test_ticket_service.py`（追加 ContextVar 用例）

**Interfaces:**
- Produces:
  - `def set_user_context(user_id: int | None, conversation_id: int | None) -> None`
  - `def reset_user_context() -> None`
  - `def get_current_user_id() -> int | None`
  - `def get_current_conversation_id() -> int | None`
  - 供 Task 3.1/3.2 工具读取；`api/chat.py` 在 `agent.astream` 前后 set/reset。

- [x] **Step 1: 写失败测试**

`apps/service/tests/test_ticket_service.py` 追加：

```python
from agent.tools.context import (
    set_user_context,
    reset_user_context,
    get_current_user_id,
    get_current_conversation_id,
)


# ========== 上下文 ==========

def test_context_var_set_get_reset():
    reset_user_context()
    assert get_current_user_id() is None
    assert get_current_conversation_id() is None

    set_user_context(user_id=7, conversation_id=9)
    assert get_current_user_id() == 7
    assert get_current_conversation_id() == 9

    reset_user_context()
    assert get_current_user_id() is None
    assert get_current_conversation_id() is None
```

- [x] **Step 2: 运行测试确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_ticket_service.py -v`
Expected: 失败，`ModuleNotFoundError: No module named 'agent.tools.context'`

- [x] **Step 3: 实现 ContextVar 模块**

`apps/service/agent/tools/context.py`：

```python
"""工具上下文 —— 通过 ContextVar 注入当前请求的用户/会话，供 async 工具读取。

Agent 为懒加载单例，工具无法接收请求级参数；
由 api/chat.py 的 chat_stream 在 astream 前后 set/reset。
"""

from contextvars import ContextVar

_current_user_id: ContextVar[int | None] = ContextVar("user_id", default=None)
_current_conversation_id: ContextVar[int | None] = ContextVar(
    "conversation_id", default=None
)


def set_user_context(user_id: int | None, conversation_id: int | None) -> None:
    """设置当前请求的用户与会话上下文。"""
    _current_user_id.set(user_id)
    _current_conversation_id.set(conversation_id)


def reset_user_context() -> None:
    """清空当前请求的用户与会话上下文（防跨请求泄漏）。"""
    _current_user_id.set(None)
    _current_conversation_id.set(None)


def get_current_user_id() -> int | None:
    """读取当前用户 ID；ContextVar 未注入时返回 None。"""
    return _current_user_id.get()


def get_current_conversation_id() -> int | None:
    """读取当前会话 ID；ContextVar 未注入时返回 None。"""
    return _current_conversation_id.get()
```

- [x] **Step 4: 在 `chat_stream` 中 set/reset**

`apps/service/api/chat.py` 的 `event_generator` 开头与 `finally` 修改：

```python
    async def event_generator():
        from agent.tools.context import set_user_context, reset_user_context
        try:
            set_user_context(current_user.id, req.conversation_id)
            async for chunk, metadata in agent.astream(
                {"messages": history_messages},
                stream_mode="messages",
            ):
                # ... 原有循环体不变 ...
        except Exception as e:
            # ... 原有异常处理不变 ...
        finally:
            reset_user_context()
            # ... 原有持久化逻辑不变 ...
```

（即：`agent.astream` 迭代前 `set_user_context(current_user.id, req.conversation_id)`，`finally` 中第一句 `reset_user_context()`。工具执行发生在 `astream` 迭代期间，因此能读到当前请求上下文；请求结束无论成功失败均重置，防止跨请求泄漏。）

- [x] **Step 5: 运行测试确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_ticket_service.py -v`
Expected: 11 passed（原 10 + ContextVar 1）

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_chat_endpoint.py -q`
Expected: 通过（chat 端点既有用例不回归）

- [x] **Step 6: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/agent/tools/context.py apps/service/api/chat.py apps/service/tests/test_ticket_service.py
git commit -m "feat: ContextVar 注入用户/会话上下文（chat_stream set/reset）"
```

---

### Task 3.1: 企业/工单工具 async 化

**Files:**
- Modify: `apps/service/agent/tools/enterprise.py`
- Test: `apps/service/tests/test_enterprise_biz.py`（追加工具层用例）、`apps/service/tests/test_ticket_service.py`（追加工具层用例）

**Interfaces:**
- Consumes: `async_session_factory`（`database/session.py`）、`agent/tools/context.py` 的 `get_current_user_id`/`get_current_conversation_id`（Task 3.3）、`services/enterprise.py`、`services/ticket.py`（Task 1.2/2.2）
- Produces: 三个 async 工具 `enterprise_query` / `ticket_submit` / `ticket_status`（函数名、docstring 与 `agent/tools/__init__.py` 的 `ALL_TOOLS` 引用保持不变）。

- [x] **Step 1: 写失败测试**

`apps/service/tests/test_enterprise_biz.py` 追加（模块顶部新增两个 import；`patch` 为本文件首次使用，须补上）：

```python
from unittest.mock import patch

from agent.tools.enterprise import enterprise_query


# ========== 工具层 ==========

@pytest.mark.anyio
async def test_enterprise_query_hit():
    biz = _make_biz("B-001")
    with patch("services.enterprise.get_business_by_code", new_callable=AsyncMock, return_value=biz):
        result = await enterprise_query("B-001")
    assert "企业开户" in result
    assert "办理条件" in result


@pytest.mark.anyio
async def test_enterprise_query_miss_lists_available():
    with patch("services.enterprise.get_business_by_code", new_callable=AsyncMock, return_value=None), patch(
        "services.enterprise.list_businesses",
        new_callable=AsyncMock,
        return_value=[_make_biz("B-001"), _make_biz("B-002")],
    ):
        result = await enterprise_query("B-999")
    assert "未找到业务编号 B-999" in result
    assert "企业开户" in result
```

`apps/service/tests/test_ticket_service.py` 追加（模块顶部新增 import）：

```python
from agent.tools.enterprise import ticket_submit, ticket_status


@pytest.mark.anyio
async def test_ticket_submit_returns_ticket_no():
    create_mock = AsyncMock(return_value=_make_ticket("TK-20260817-0001", status="open"))
    with patch("services.ticket.create_ticket", create_mock):
        result = await ticket_submit("B-001", "张三", "办理企业开户")
    assert "TK-20260817-0001" in result
    _, kwargs = create_mock.call_args
    assert kwargs["business_code"] == "B-001"
    assert kwargs["content"] == "办理企业开户"
    assert kwargs["user_id"] is None  # 未注入 ContextVar 时降级


@pytest.mark.anyio
async def test_ticket_status_returns_real_status():
    with patch(
        "services.ticket.get_ticket_by_no",
        new_callable=AsyncMock,
        return_value=_make_ticket("TK-20260817-0001", status="processing"),
    ):
        result = await ticket_status("TK-20260817-0001")
    assert "processing" in result


@pytest.mark.anyio
async def test_ticket_status_not_found():
    with patch("services.ticket.get_ticket_by_no", new_callable=AsyncMock, return_value=None):
        result = await ticket_status("TK-00000000-0000")
    assert "未找到工单" in result
```

> 注：工具函数在函数体内惰性 `from services.xxx import ...`，因此 `patch("services.xxx.<函数>")` 在调用时生效；`async with async_session_factory() as session:` 只创建会话不发起连接，服务函数被 patch 后不会产生真实 DB 查询，测试无需数据库。

- [x] **Step 2: 运行测试确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_enterprise_biz.py tests/test_ticket_service.py -v`
Expected: 新增用例失败（`TypeError: 'coroutine' object is not iterable` 或工具仍为同步返回 str 无法 await）

- [x] **Step 3: 实现 async 工具**

`apps/service/agent/tools/enterprise.py` 整体替换为（删除 `_MOCK_BUSINESS` 与 `_TICKET_COUNTER`）：

```python
"""企业业务工具 —— 查询 enterprise_biz 表，提交/查询工单（service_tickets 表）。"""

import logging

from langchain_core.tools import tool

from database.session import async_session_factory

logger = logging.getLogger("intelligent-customer.agent.tools.enterprise")


@tool
async def enterprise_query(service_code: str) -> str:
    """当用户提供业务编号或询问企业业务流程、办理条件时使用此工具。
    输入为业务编号，格式如 B-001。工具会返回该业务的办理说明。"""
    from services.enterprise import get_business_by_code, list_businesses

    async with async_session_factory() as session:
        biz = await get_business_by_code(session, service_code.upper())
        if not biz:
            businesses = await list_businesses(session)
            available = "、".join(b.name for b in businesses)
            return f"未找到业务编号 {service_code} 对应的业务。当前可办理业务：{available}。"
        return (
            f"【{biz.name}】\n"
            f"业务说明：{biz.description}\n"
            f"办理条件：{biz.requirements}\n"
            f"办理流程：{biz.process}"
        )


@tool
async def ticket_submit(business_code: str, customer_name: str, description: str) -> str:
    """当用户要求办理企业业务、提交申请时使用此工具。
    输入业务编号、客户名称和办理说明，工具会创建一张办理工单。"""
    from services.ticket import create_ticket
    from agent.tools.context import get_current_user_id, get_current_conversation_id

    async with async_session_factory() as session:
        ticket = await create_ticket(
            session,
            business_code=business_code,
            content=description,
            user_id=get_current_user_id(),
            conversation_id=get_current_conversation_id(),
        )
    logger.info(
        "创建工单: %s, 业务=%s, 客户=%s", ticket.ticket_no, business_code, customer_name
    )
    return (
        f"您的办理工单已创建，工单号 {ticket.ticket_no}，业务 {business_code}。"
        f"请留意后续办理进度通知。"
    )


@tool
async def ticket_status(ticket_id: str) -> str:
    """当用户询问办理进度、工单状态时使用此工具。
    输入工单号，格式如 TK-20260817-0001，工具会返回该工单的真实状态。"""
    from services.ticket import get_ticket_by_no

    async with async_session_factory() as session:
        ticket = await get_ticket_by_no(session, ticket_id)
    if not ticket:
        return f"未找到工单 {ticket_id}，请核对工单号。"
    return (
        f"工单 {ticket.ticket_no} 当前状态：{ticket.status}。"
        f"如需进一步处理请联系人工客服。"
    )
```

- [x] **Step 4: 运行测试确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_enterprise_biz.py tests/test_ticket_service.py -v`
Expected: `test_enterprise_biz.py` 8 passed（模型 1 + 服务 5 + 工具 2）、`test_ticket_service.py` 14 passed（服务 10 + 上下文 1 + 工具 3）

- [x] **Step 5: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/agent/tools/enterprise.py apps/service/tests/test_enterprise_biz.py apps/service/tests/test_ticket_service.py
git commit -m "feat: 企业/工单工具 async 化（真实落库 service_tickets / 查询 enterprise_biz）"
```

---

### Task 3.2: transfer_human async 化（HUMAN 哨兵工单）

**Files:**
- Modify: `apps/service/agent/tools/chat.py`
- Test: `apps/service/tests/test_ticket_service.py`（追加工具层用例）

**Interfaces:**
- Consumes: `async_session_factory`、`agent/tools/context.py` 的 get 函数（Task 3.3）、`services.ticket.create_ticket`（Task 2.2）
- Produces: async 工具 `transfer_human`（函数名与 `ALL_TOOLS` 引用保持不变，docstring 微调补充工单说明）。

- [x] **Step 1: 写失败测试**

`apps/service/tests/test_ticket_service.py` 追加（模块顶部新增 `from agent.tools.chat import transfer_human`）：

```python
from agent.tools.chat import transfer_human


@pytest.mark.anyio
async def test_transfer_human_creates_human_ticket():
    create_mock = AsyncMock(return_value=_make_ticket("TK-20260817-0001", status="open"))
    with patch("services.ticket.create_ticket", create_mock):
        result = await transfer_human()
    assert "TK-20260817-0001" in result
    assert "人工" in result
    _, kwargs = create_mock.call_args
    assert kwargs["business_code"] == "HUMAN"
```

- [x] **Step 2: 运行测试确认失败**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_ticket_service.py -v`
Expected: 新增用例失败（transfer_human 仍为同步，无法 await）

- [x] **Step 3: 实现 async transfer_human**

`apps/service/agent/tools/chat.py` 整体替换为：

```python
"""对话辅助工具 —— 转人工和追问澄清。"""

import logging

from langchain_core.tools import tool

from database.session import async_session_factory

logger = logging.getLogger("intelligent-customer.agent.tools.chat")


@tool
async def transfer_human() -> str:
    """当你判断无法处理用户的问题，或需要人工介入时使用此工具。
    调用后会生成一条转人工工单（business_code=HUMAN）。

    触发条件：
    - 连续两次无法确定用户意图
    - 用户明确要求人工服务
    - 问题超出你的处理能力范围
    - 涉及投诉、纠纷等需要人工判断的场景
    """
    from services.ticket import create_ticket
    from agent.tools.context import get_current_user_id, get_current_conversation_id

    async with async_session_factory() as session:
        ticket = await create_ticket(
            session,
            business_code="HUMAN",
            content="用户请求转人工客服",
            user_id=get_current_user_id(),
            conversation_id=get_current_conversation_id(),
        )
    logger.info("生成转人工工单: %s", ticket.ticket_no)
    return (
        f"已为您转接人工客服，请稍候。工单号 {ticket.ticket_no}，"
        f"人工客服将在1-2分钟内为您服务，感谢您的耐心等待。"
    )


@tool
def clarify(question: str) -> str:
    """当用户意图不明确，需要追问澄清时使用此工具。
    输入为你要向用户提出的澄清问题。

    触发条件：
    - 用户的问题模糊，无法判断需要哪个工具
    - 用户提供的业务编号或工单号不完整
    - 用户的需求可以有多种理解

    使用示例：
    - clarify(question="请问您是想查询办理进度还是提交新工单？")
    - clarify(question="请提供完整的业务编号或工单号，格式如 B-001 或 TK-20260817-0001。")
    """
    return question
```

- [x] **Step 4: 运行测试确认通过**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_ticket_service.py -v`
Expected: 15 passed（含 `test_transfer_human_creates_human_ticket`）

Run: `cd apps/service && .venv/bin/python -m pytest tests/ -q`
Expected: 全量不回归（含既有 chat/tools 相关用例）

- [x] **Step 5: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/agent/tools/chat.py apps/service/tests/test_ticket_service.py
git commit -m "feat: transfer_human async 化并生成 HUMAN 哨兵工单"
```

---

### Task 4.1: 前端工单服务封装

**Files:**
- Create: `apps/web/services/tickets.ts`

**Interfaces:**
- Consumes: `fetchClient`（`apps/web/lib/fetch`，`get<T>(url, params?)` / `patch<T>(url, body?)`）
- Produces:
  - `export type TicketStatus = "open" | "processing" | "closed"`
  - `export interface Ticket { id; ticket_no; user_id; username; conversation_id; business_code; content; status; created_at; updated_at }`
  - `export async function getTicketsApi(status?: TicketStatus | "")`
  - `export async function updateTicketStatusApi(ticketNo: string, status: TicketStatus)`
  - 供 Task 4.2 `useServices.ts` 使用。

- [ ] **Step 1: 实现服务封装**

`apps/web/services/tickets.ts`：

```ts
import { fetchClient } from "@/lib/fetch"

// ========== 类型定义 ==========

export type TicketStatus = "open" | "processing" | "closed"

export interface Ticket {
  id: number
  ticket_no: string
  user_id: number | null
  username: string | null
  conversation_id: number | null
  business_code: string
  content: string
  status: TicketStatus
  created_at: string
  updated_at: string
}

// ========== 工单接口 ==========

export async function getTicketsApi(status?: TicketStatus | "") {
  return fetchClient.get<Ticket[]>(
    "/tickets",
    status ? { status } : undefined
  )
}

export async function updateTicketStatusApi(ticketNo: string, status: TicketStatus) {
  return fetchClient.patch<Ticket>(`/tickets/${ticketNo}/status`, { status })
}
```

- [ ] **Step 2: 类型检查**

Run: `cd apps/web && pnpm typecheck`
Expected: 无类型错误

- [ ] **Step 3: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/web/services/tickets.ts
git commit -m "feat(web): 工单 API 服务封装（列表/状态更新）"
```

---

### Task 4.2: 工单管理页（useServices + page + layout）

**Files:**
- Create: `apps/web/app/tickets/useServices.ts`
- Create: `apps/web/app/tickets/page.tsx`
- Create: `apps/web/app/tickets/layout.tsx`

**Interfaces:**
- Consumes: `getTicketsApi` / `updateTicketStatusApi` / `TicketStatus` / `Ticket`（Task 4.1）
- Produces: `/tickets` 页面（工单表 + 顶部状态筛选 + 每行状态更新下拉 + 空态 + toast），经 `layout.tsx` 的 `AuthGuard` + `AppLayout` 包裹。
- i18n 文案键（本任务引用的 `t("...")`，Task 4.3 补齐两份 messages）。

- [ ] **Step 1: 实现 useServices**

`apps/web/app/tickets/useServices.ts`：

```ts
import { useRequest } from "ahooks";
import { useMemo, useState } from "react";
import {
  getTicketsApi,
  updateTicketStatusApi,
  type Ticket,
  type TicketStatus,
} from "@/services/tickets";

export default function useTicketServices() {
  // 状态筛选（"" 表示全部）
  const [statusFilter, setStatusFilter] = useState<TicketStatus | "">("");

  // 工单列表（跟随状态筛选；manual 模式由页面 useEffect 触发）
  const listControl = useRequest(() => getTicketsApi(statusFilter), {
    manual: true,
  });
  const { data: listData } = listControl;
  const tickets = useMemo(() => listData?.data ?? [], [listData]);

  // 更新状态
  const updateControl = useRequest(updateTicketStatusApi, { manual: true });

  async function updateStatus(ticketNo: string, status: TicketStatus) {
    await updateControl.runAsync(ticketNo, status);
    await listControl.run();
  }

  return {
    statusFilter,
    setStatusFilter,
    listControl,
    tickets,
    updateControl,
    updateStatus,
  };
}
```

- [ ] **Step 2: 实现页面**

`apps/web/app/tickets/page.tsx`：

```tsx
"use client"

import { useCallback, useEffect, useState } from "react"
import { useTranslations } from "next-intl"
import useTicketServices from "./useServices"

import { Card, CardContent } from "@intelligent-customer/ui/components/card"
import { Badge } from "@intelligent-customer/ui/components/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@intelligent-customer/ui/components/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@intelligent-customer/ui/components/select"
import { toast } from "sonner"
import type { TicketStatus } from "@/services/tickets"

const STATUS_OPTIONS: { value: string; labelKey: string }[] = [
  { value: "all", labelKey: "statusAll" },
  { value: "open", labelKey: "statusOpen" },
  { value: "processing", labelKey: "statusProcessing" },
  { value: "closed", labelKey: "statusClosed" },
]

function StatusBadge({ status }: { status: TicketStatus }) {
  const t = useTranslations("tickets")
  if (status === "open") {
    return (
      <Badge variant="secondary" className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100">
        {t("statusOpen")}
      </Badge>
    )
  }
  if (status === "processing") {
    return (
      <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
        {t("statusProcessing")}
      </Badge>
    )
  }
  return (
    <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
      {t("statusClosed")}
    </Badge>
  )
}

function formatCreatedAt(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return dateStr
  }
}

export default function TicketsPage() {
  const t = useTranslations("tickets")
  const {
    statusFilter,
    setStatusFilter,
    listControl,
    tickets,
    updateControl,
    updateStatus,
  } = useTicketServices()

  // 状态筛选变化时重新拉取
  useEffect(() => {
    listControl.run()
  }, [statusFilter, listControl])

  const handleStatusChange = useCallback(
    async (ticketNo: string, status: TicketStatus) => {
      try {
        await updateStatus(ticketNo, status)
        toast.success(t("statusUpdated"))
      } catch {
        // 错误已由 fetchClient 拦截器统一处理
      }
    },
    [updateStatus, t],
  )

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("ticketCount", { count: tickets.length })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={statusFilter || "all"}
            onValueChange={(v) => setStatusFilter(v === "all" ? "" : (v as TicketStatus))}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {t(opt.labelKey)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 工单表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("colTicketNo")}</TableHead>
                <TableHead>{t("colBusiness")}</TableHead>
                <TableHead>{t("colUser")}</TableHead>
                <TableHead>{t("colStatus")}</TableHead>
                <TableHead>{t("colCreatedAt")}</TableHead>
                <TableHead className="text-right">{t("colActions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tickets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                    {t("noTickets")}
                  </TableCell>
                </TableRow>
              ) : (
                tickets.map((ticket) => (
                  <TableRow key={ticket.id}>
                    <TableCell className="font-medium">{ticket.ticket_no}</TableCell>
                    <TableCell>{ticket.business_code}</TableCell>
                    <TableCell>{ticket.username ?? ticket.user_id ?? "—"}</TableCell>
                    <TableCell>
                      <StatusBadge status={ticket.status} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatCreatedAt(ticket.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Select
                        value={ticket.status}
                        disabled={updateControl.loading}
                        onValueChange={(v) =>
                          handleStatusChange(ticket.ticket_no, v as TicketStatus)
                        }
                      >
                        <SelectTrigger className="h-8 w-28">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="open">{t("statusOpen")}</SelectItem>
                          <SelectItem value="processing">{t("statusProcessing")}</SelectItem>
                          <SelectItem value="closed">{t("statusClosed")}</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 3: 实现 layout**

`apps/web/app/tickets/layout.tsx`：

```tsx
import { AppLayout } from "@/components/layout/app-layout"
import { AuthGuard } from "@/components/auth-guard"

export default function TicketsLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <AuthGuard>
      <AppLayout>{children}</AppLayout>
    </AuthGuard>
  )
}
```

- [ ] **Step 4: 类型检查**

Run: `cd apps/web && pnpm typecheck`
Expected: 无类型错误（i18n 文案键未定义不会导致 tsc 报错；运行时缺失会在 Task 4.3 补齐后消除）

- [ ] **Step 5: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/web/app/tickets/
git commit -m "feat(web): 工单管理页（列表/状态筛选/状态更新）"
```

---

### Task 4.3: 菜单入口 + i18n 文案

**Files:**
- Modify: `apps/web/config/menu.ts`
- Modify: `apps/web/messages/zh-CN.json`
- Modify: `apps/web/messages/en-US.json`

**Interfaces:**
- Consumes: Task 4.2 页面引用的 `t("...")` 文案键
- Produces: 侧边栏「管理」分组新增「工单管理」（admin）菜单项与 `titleKeyMap["/tickets"]`；两份 messages 补 `layout.menuTickets` 与 `tickets.*`。

- [ ] **Step 1: 修改 menu.ts**

`apps/web/config/menu.ts`：

import 行（lucide 增加 `ClipboardList`）：

```ts
import { MessageSquare, BookOpen, Users, Settings, Wrench, ClipboardList } from "lucide-react"
```

「管理」分组 children 中（`knowledge` 之后）新增：

```ts
      {
        key: "tickets",
        labelKey: "layout.menuTickets",
        href: "/tickets",
        icon: ClipboardList,
        roles: ["admin"],
      },
```

`titleKeyMap` 新增：

```ts
  "/tickets": "layout.menuTickets",
```

- [ ] **Step 2: 补齐 zh-CN 文案**

`apps/web/messages/zh-CN.json`：

`layout` 对象内新增 `"menuTickets": "工单管理"`；`tools` 对象之后新增：

```json
  "tickets": {
    "title": "🎫 工单管理",
    "ticketCount": "共 {count} 张工单",
    "statusFilter": "状态筛选",
    "statusAll": "全部",
    "statusOpen": "待处理",
    "statusProcessing": "办理中",
    "statusClosed": "已关闭",
    "colTicketNo": "工单号",
    "colBusiness": "业务",
    "colUser": "提交用户",
    "colStatus": "状态",
    "colCreatedAt": "创建时间",
    "colActions": "操作",
    "statusUpdated": "状态已更新",
    "noTickets": "暂无工单"
  }
```

- [ ] **Step 3: 补齐 en-US 文案**

`apps/web/messages/en-US.json`：

`layout` 对象内新增 `"menuTickets": "Ticket Management"`；`tools` 对象之后新增：

```json
  "tickets": {
    "title": "🎫 Ticket Management",
    "ticketCount": "{count} tickets",
    "statusFilter": "Filter by status",
    "statusAll": "All",
    "statusOpen": "Open",
    "statusProcessing": "Processing",
    "statusClosed": "Closed",
    "colTicketNo": "Ticket No.",
    "colBusiness": "Business",
    "colUser": "User",
    "colStatus": "Status",
    "colCreatedAt": "Created At",
    "colActions": "Actions",
    "statusUpdated": "Status updated",
    "noTickets": "No tickets yet"
  }
```

- [ ] **Step 4: 验证 JSON 合法 + 类型检查**

Run: `cd apps/web && node -e "JSON.parse(require('fs').readFileSync('messages/zh-CN.json','utf8')); JSON.parse(require('fs').readFileSync('messages/en-US.json','utf8')); console.log('json ok')"`
Expected: 输出 `json ok`

Run: `cd apps/web && pnpm typecheck`
Expected: 无类型错误

- [ ] **Step 5: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/web/config/menu.ts apps/web/messages/zh-CN.json apps/web/messages/en-US.json
git commit -m "feat(web): 工单管理菜单入口与双语文案"
```

---

### Task 5.1: 安全默认值校验（validate_security_defaults）

**Files:**
- Modify: `apps/service/configs/config.py`
- Modify: `apps/service/app/lifespan.py`

**Interfaces:**
- Consumes: `settings.JWT_SECRET` / `settings.ADMIN_PASSWORD`
- Produces: `def validate_security_defaults() -> None`；`lifespan` 启动时调用（`logging.basicConfig` 之后）。弱默认值命中仅 `logger.warning`，不阻塞启动。

- [ ] **Step 1: 在 config.py 增加校验函数**

`apps/service/configs/config.py` 顶部 `import os` 之后新增 `import logging`：

```python
import logging
```

文件末尾（`settings = Settings()` 之后）新增：

```python
def validate_security_defaults() -> None:
    """校验安全默认值：弱 JWT_SECRET / ADMIN_PASSWORD 命中时仅告警，不阻塞启动。"""
    logger = logging.getLogger("intelligent-customer.security")
    if settings.JWT_SECRET == "change-me-in-production":
        logger.warning(
            "安全告警: JWT_SECRET 仍为默认弱值 change-me-in-production，"
            "请在 .env 中配置强随机密钥"
        )
    if settings.ADMIN_PASSWORD == "admin123456":
        logger.warning(
            "安全告警: ADMIN_PASSWORD 仍为默认弱值 admin123456，请在 .env 中配置强密码"
        )
```

- [ ] **Step 2: 在 lifespan 启动时调用**

`apps/service/app/lifespan.py` 的 `lifespan` 异步函数开头（`logger.info("启动中... 创建数据库表")` 之前）新增：

```python
    from configs.config import validate_security_defaults
    validate_security_defaults()
```

- [ ] **Step 3: 验证告警输出（当前 .env 仍为弱值）**

Run: `cd apps/service && .venv/bin/python -c "from configs.config import validate_security_defaults; validate_security_defaults()"`
Expected: 输出两条 `安全告警`（JWT_SECRET + ADMIN_PASSWORD）

- [ ] **Step 4: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/configs/config.py apps/service/app/lifespan.py
git commit -m "feat: 启动时校验安全默认值并告警"
```

---

### Task 5.2: .env 强 JWT_SECRET 与 ADMIN_PASSWORD

**Files:**
- Modify: `apps/service/.env`

**Interfaces:**
- Produces: 强随机 `JWT_SECRET`（`secrets.token_hex(32)` 生成）、强 `ADMIN_PASSWORD`；`DB_PASSWORD` 与其余配置保持不变。

- [ ] **Step 1: 生成强随机 JWT_SECRET**

Run: `cd apps/service && .venv/bin/python -c "import secrets; print(secrets.token_hex(32))"`
Expected: 输出 64 位十六进制字符串（形如 `a1b2...`，记下备用）

- [ ] **Step 2: 修改 .env**

`apps/service/.env` 中：

```
JWT_SECRET=<上一步生成的 64 位随机值>
ADMIN_PASSWORD=<强密码，如 Admin#2026Secure>
```

（`DB_PASSWORD`、`APP_HOST`、`APP_PORT` 等其余行一律不动。改动前可先 `cp .env .env.bak` 以便回滚。）

> 注意：`seed_admin_user` 仅在 admin 不存在时创建。若本地库已存在 admin（旧密码哈希），改 `.env` 不会覆盖已有用户。Task 7.1 重启前，若需要让新 `ADMIN_PASSWORD` 生效，手动执行一条 SQL 删除已有 admin 行（`DELETE FROM users WHERE username='admin';`），启动时将以新密码重建。

- [ ] **Step 3: 验证弱值告警消失**

Run: `cd apps/service && .venv/bin/python -c "from configs.config import validate_security_defaults; validate_security_defaults()"`
Expected: 无 `安全告警` 输出

- [ ] **Step 4: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/.env
git commit -m "chore: .env 强化 JWT_SECRET 与 ADMIN_PASSWORD"
```

---

### Task 6.1: 验证 test_enterprise_biz.py 全通过

**Files:**
- Test: `apps/service/tests/test_enterprise_biz.py`（如发现缺漏在此补齐）

**Interfaces:**
- Consumes: Task 1.1/1.2/3.1 累计的用例（模型 + 服务层 + 工具层）

- [ ] **Step 1: 运行完整测试文件**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_enterprise_biz.py -v`
Expected: 8 passed（`test_enterprise_biz_defaults` + 服务层 5 + 工具层 2）

- [ ] **Step 2: 检查规格覆盖补漏**

对照设计文档 §5 与 OpenSpec `enterprise-biz/spec.md`：确认「业务列表/单业务查询/查询未命中」「启动种子初始化」均有对应用例；若缺失，补一条并重跑。

- [ ] **Step 3: 提交（若补了用例）**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/tests/test_enterprise_biz.py
git commit -m "test: 补全企业业务用例"
```

（未补用例时跳过本步。）

---

### Task 6.2: 验证 test_ticket_service.py 全通过

**Files:**
- Test: `apps/service/tests/test_ticket_service.py`（如发现缺漏在此补齐）

**Interfaces:**
- Consumes: Task 2.2/3.3/3.1/3.2 累计的用例（服务层 + 上下文 + 工具层）

- [ ] **Step 1: 运行完整测试文件**

Run: `cd apps/service && .venv/bin/python -m pytest tests/test_ticket_service.py -v`
Expected: 15 passed（服务层 10 + 上下文 1 + 工具层 4）

- [ ] **Step 2: 检查规格覆盖补漏**

对照设计文档 §5 与 OpenSpec `ticket-service/spec.md`：确认「工单号格式与当日内自增」「创建返回工单号」「列表 + 状态筛选」「详情」「状态更新合法流转/非法值」「转人工生成 HUMAN 工单」均有对应用例；若缺失，补一条并重跑。

- [ ] **Step 3: 提交（若补了用例）**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer
git add apps/service/tests/test_ticket_service.py
git commit -m "test: 补全工单用例"
```

（未补用例时跳过本步。）

---

### Task 6.3: 全量 pytest 通过

**Files:**
- 无新增（回归验证）

- [ ] **Step 1: 运行全量测试**

Run: `cd apps/service && .venv/bin/python -m pytest tests/ -q`
Expected: 全部通过（既有 11 个测试文件 + 新增 2 个，无失败）

- [ ] **Step 2: 确认无相关告警/报错**

若有失败：加载 systematic-debugging 定位根因后修复，禁止跳过失败直接提交。

---

### Task 7.1: 重启后端验证建表/种子/无告警

**Files:**
- 无新增（运行验证）

**Interfaces:**
- Consumes: 全部后端改动（Task 1.1–5.2）

- [ ] **Step 1: 确认 MySQL/Redis/Chroma 依赖可用**

按项目现有方式确认依赖服务已启动（本机 MySQL 或 `docker compose`）。若用 Docker：`docker compose up -d mysql redis chroma`（按 `docker-compose.yml` 实际服务名）。

- [ ] **Step 2: 启动后端并观察日志**

Run: `cd apps/service && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8009`

预期日志：
- 无「安全告警」行（Task 5.2 已强化 .env；若 admin 为旧哈希已按 Task 5.2 备注处理）
- 出现「企业业务种子初始化: 插入 3 条」（或已有数据时跳过）
- 启动完成行 `启动完成  ...:8009`

- [ ] **Step 3: 确认建表**

Run: `mysql -uroot -p00000000 ling_diary -e "SHOW TABLES;"`
Expected: 包含 `enterprise_biz`、`service_tickets`

Run: `mysql -uroot -p00000000 ling_diary -e "SELECT code,name FROM enterprise_biz ORDER BY code;"`
Expected: B-001 企业开户 / B-002 对公转账 / B-003 电子发票申领

- [ ] **Step 4: 冒烟调用接口**

用登录 token 调企业接口（先用 admin/新密码登录拿 token）：

```bash
TOKEN=$(curl -s -X POST http://localhost:8009/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin#2026Secure"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["token"])')
curl -s http://localhost:8009/api/enterprise/businesses -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8009/api/enterprise/businesses/B-001 -H "Authorization: Bearer $TOKEN"
```

Expected: 业务列表返回 3 条；B-001 返回详情；`B-999` 返回 `code=40006` 错误。

- [ ] **Step 5: 提交（无代码改动则不提交）**

本任务为运行验证，无源码改动时不产生提交。

---

### Task 7.2: 实测对话 + 后台工单页

**Files:**
- 无新增（端到端验证）

**Interfaces:**
- Consumes: 全部前后端改动（Task 1.1–6.3）

- [ ] **Step 1: 通过对话触发生成工单**

后端保持运行，向前端（`cd apps/web && pnpm dev`，端口 3000）发起对话：

1. 登录（admin/新密码）。
2. 提问「查一下企业开户的办理条件」→ Agent 调用 `enterprise_query`，回复应含「企业开户 / 办理条件」（数据来自 `enterprise_biz` 表，非模拟数据）。
3. 提问「提交企业开户的办理申请」→ Agent 调用 `ticket_submit`，回复应含 `TK-YYYYMMDD-XXXX` 工单号。
4. 提问「转人工客服」→ Agent 调用 `transfer_human`，回复应含工单号。

- [ ] **Step 2: 查库确认落库与上下文注入**

Run:

```bash
mysql -uroot -p00000000 ling_diary -e "SELECT ticket_no,user_id,conversation_id,business_code,content,status FROM service_tickets ORDER BY id DESC LIMIT 5;"
```

Expected: 提交/转人工工单均已落库；`business_code` 为对应业务编号与 `HUMAN`；`user_id`、`conversation_id` 已由 ContextVar 注入（对话路径下非空）；`status` 为 `open`。

- [ ] **Step 3: 后台工单页验证**

浏览器访问 `http://localhost:3000/tickets`（admin 登录）：
- 侧边栏「管理」分组含「工单管理」入口，可跳转 `/tickets`，页面标题正确（中/英切换验证 i18n）
- 工单表展示工单号/业务/提交用户/状态/创建时间
- 顶部状态筛选（全部/待处理/办理中/已关闭）生效
- 每行状态下拉更新后 toast「状态已更新」，列表刷新后状态变更
- 非 admin 账号访问 `/tickets`：菜单不显示该入口；直连页面接口返回 40003 错误（无权限）

- [ ] **Step 4: 提交（无代码改动则不提交）**

本任务为端到端验证，若发现缺陷回到对应任务修复后再验收；无源码改动时不产生提交。

---

## Self-Review 结果

- **Spec 覆盖**：P5（Task 1.1–1.4, 3.1）、P6（Task 2.1–2.3, 3.1–3.3, 4.1–4.3）、S1（Task 5.1–5.2）、测试（Task 6.1–6.3）、端到端（Task 7.1–7.2）全部覆盖；OpenSpec 三个 delta spec（enterprise-biz / ticket-service / agent-tools）的每条 Requirement 均有对应任务。
- **占位符扫描**：全部代码步骤给出完整内容，无 TBD/TODO/「类似 Task N」引用。
- **类型一致性**：`EnterpriseBiz`/`ServiceTicket` ORM 字段、服务函数签名（`db: AsyncSession` 首参）、工具函数名（`enterprise_query`/`ticket_submit`/`ticket_status`/`transfer_human`）、API 路径、前端 `Ticket`/`TicketStatus` 类型在后续任务中引用一致。
