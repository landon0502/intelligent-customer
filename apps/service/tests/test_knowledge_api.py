"""api/knowledge query 接口测试 —— 检索接口 admin 权限一致化（S5）。"""

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.knowledge import router as knowledge_router
from database.session import get_db
from auth.security import get_current_user


def _make_client(role="admin"):
    """构造仅挂载 knowledge 路由的测试应用，override 鉴权/DB。"""
    app = FastAPI()
    app.include_router(knowledge_router)

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.role = role
    mock_db = AsyncMock()

    def _override_user():
        return mock_user

    def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db

    return TestClient(app)


def test_query_rejects_non_admin():
    """非管理员检索被拒（40003），与 upload/list/delete 权限一致。"""
    resp = _make_client("user").post(
        "/api/knowledge/query", json={"question": "企业开户需要什么材料？"}
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 40003


def test_query_success_for_admin():
    """管理员正常检索，返回命中结果。"""
    client = _make_client("admin")
    with patch(
        "api.knowledge.query_knowledge",
        new=AsyncMock(
            return_value={"chunks": [], "answer": "需提供营业执照", "sources": []}
        ),
    ):
        resp = client.post(
            "/api/knowledge/query", json={"question": "企业开户需要什么材料？"}
        )
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["answer"] == "需提供营业执照"
