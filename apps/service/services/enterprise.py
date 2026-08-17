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
