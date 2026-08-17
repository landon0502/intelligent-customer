"""api/tools 接口测试 —— admin 权限、错误码映射。"""

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.tools import router as tools_router
from database.session import get_db
from auth.security import get_current_user
from app.dependencies import get_config_provider, get_registry
from services.tools import UnknownToolError, GuardedToolError


def _make_client(role="admin"):
    """构造仅挂载 tools 路由的测试应用，override 鉴权/DB/依赖。"""
    app = FastAPI()
    app.include_router(tools_router)

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.role = role
    mock_db = AsyncMock()

    def _override_user():
        return mock_user

    def _override_db():
        yield mock_db

    def _override_provider():
        return MagicMock()

    def _override_registry():
        return MagicMock()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_config_provider] = _override_provider
    app.dependency_overrides[get_registry] = _override_registry

    return TestClient(app)


def test_get_rejects_non_admin():
    resp = _make_client("user").get("/api/tools")
    assert resp.status_code == 200
    assert resp.json()["code"] == 40003


def test_patch_rejects_non_admin():
    resp = _make_client("user").patch(
        "/api/tools/knowledge_base_query", json={"enabled": False}
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 40003


def test_get_success():
    client = _make_client("admin")
    with patch(
        "api.tools.list_tool_states",
        new=AsyncMock(
            return_value={"knowledge_base_query": "enabled", "clarify": "enabled"}
        ),
    ):
        resp = client.get("/api/tools")

    assert resp.json()["code"] == 0
    items = resp.json()["data"]
    assert items[0]["name"] == "knowledge_base_query"
    assert items[0]["enabled"] is True
    assert items[0]["description"]  # 来自 TOOL_DESCRIPTIONS


def test_patch_success():
    client = _make_client("admin")
    with patch(
        "api.tools.update_tool_state",
        new=AsyncMock(return_value=("knowledge_base_query", False, True)),
    ):
        resp = client.patch(
            "/api/tools/knowledge_base_query", json={"enabled": False}
        )

    assert resp.json()["code"] == 0
    assert resp.json()["data"] == {
        "name": "knowledge_base_query",
        "enabled": False,
        "refresh_ok": True,
    }


def test_patch_guarded_disable_returns_40004():
    client = _make_client("admin")
    with patch(
        "api.tools.update_tool_state",
        side_effect=GuardedToolError("兜底工具不可禁用"),
    ):
        resp = client.patch("/api/tools/transfer_human", json={"enabled": False})

    assert resp.status_code == 200
    assert resp.json()["code"] == 40004


def test_patch_unknown_tool_returns_40005():
    client = _make_client("admin")
    with patch(
        "api.tools.update_tool_state",
        side_effect=UnknownToolError("工具不存在: xxx"),
    ):
        resp = client.patch("/api/tools/xxx", json={"enabled": True})

    assert resp.status_code == 200
    assert resp.json()["code"] == 40005
