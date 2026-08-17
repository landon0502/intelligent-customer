"""企业业务服务与工具层测试 —— AsyncMock db session / patch 服务函数。"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from schemas.enterprise_biz import EnterpriseBiz
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
