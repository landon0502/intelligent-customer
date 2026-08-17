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
