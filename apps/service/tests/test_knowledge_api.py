"""api/knowledge query 接口测试 —— 检索接口 admin 权限一致化（S5）。"""

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.knowledge import router as knowledge_router
from database.session import get_db
from auth.security import get_current_user
from schemas.document_schema import DocumentUploadItem
from services.knowledge import MAX_UPLOAD_FILES


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


# ========== 多文件上传 ==========

def test_upload_rejects_non_admin():
    """非管理员上传被拒（40003）。"""
    resp = _make_client("user").post(
        "/api/knowledge/upload",
        files=[("files", ("note.txt", b"hello", "text/plain"))],
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 40003


def test_upload_batch_partial_failure_end_to_end():
    """真实跑通 路由 → upload_documents → 逐文件结果 的链路（只 mock 单文件服务）。"""
    client = _make_client("admin")
    doc = MagicMock()
    doc.id = 3
    doc.status = "processing"

    async def _fake_upload(_db, filename, content, uploaded_by=None):
        if filename == "bad.txt":
            raise ValueError("文件内容为空")
        return doc

    with patch(
        "services.knowledge.upload_document", new=AsyncMock(side_effect=_fake_upload)
    ):
        resp = client.post(
            "/api/knowledge/upload",
            files=[
                ("files", ("good.txt", b"hello", "text/plain")),
                ("files", ("bad.txt", b"", "text/plain")),
            ],
        )

    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
    assert [r["filename"] for r in data["results"]] == ["good.txt", "bad.txt"]
    assert data["results"][0]["document_id"] == 3
    assert "内容为空" in data["results"][1]["message"]


def test_upload_response_shape_from_service():
    """响应体形状与批量结果模型一致。"""
    client = _make_client("admin")
    items = [
        DocumentUploadItem(
            filename="a.txt", success=True, document_id=1, status="processing"
        ),
        DocumentUploadItem(
            filename="big.txt", success=False, message="文件大小超过 20MB 上限"
        ),
    ]
    with patch("api.knowledge.upload_documents", new=AsyncMock(return_value=items)):
        resp = client.post(
            "/api/knowledge/upload",
            files=[
                ("files", ("a.txt", b"hello", "text/plain")),
                ("files", ("big.txt", b"x", "text/plain")),
            ],
        )

    data = resp.json()["data"]
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
    assert data["results"][0] == {
        "filename": "a.txt",
        "success": True,
        "document_id": 1,
        "status": "processing",
        "message": None,
    }
    assert data["results"][1]["message"] == "文件大小超过 20MB 上限"


def test_upload_rejects_too_many_files():
    """超过单批上限整批拒绝（40004），且没有任何文件被处理。"""
    client = _make_client("admin")
    upload_mock = AsyncMock()
    files = [
        ("files", (f"f{i}.txt", b"hello", "text/plain"))
        for i in range(MAX_UPLOAD_FILES + 1)
    ]

    with patch("services.knowledge.upload_document", new=upload_mock):
        resp = client.post("/api/knowledge/upload", files=files)

    assert resp.json()["code"] == 40004
    assert "最多上传" in resp.json()["message"]
    upload_mock.assert_not_called()
