"""知识库上传校验测试 —— 大小上限与内容有效性（S7）。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.knowledge import (
    MAX_UPLOAD_FILES,
    MAX_UPLOAD_SIZE,
    upload_document,
    upload_documents,
)


def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.anyio
async def test_upload_rejects_oversize():
    """超过 20MB 的上传被拒绝，不写库。"""
    db = _mock_db()
    with pytest.raises(ValueError, match="20MB"):
        await upload_document(db, "big.pdf", b"x" * (MAX_UPLOAD_SIZE + 1), uploaded_by=1)
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_upload_rejects_corrupt_pdf():
    """损坏（无法解析）PDF 被拒绝，不写库。"""
    db = _mock_db()
    with pytest.raises(ValueError, match="无法解析"):
        await upload_document(db, "corrupt.pdf", b"%PDF-1.4 not really a pdf", uploaded_by=1)
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_upload_rejects_empty_txt():
    """空文本文件被拒绝，不写库。"""
    db = _mock_db()
    with pytest.raises(ValueError, match="内容为空"):
        await upload_document(db, "empty.txt", b"", uploaded_by=1)
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_upload_accepts_valid_txt():
    """合法非空文本文件通过校验并入库。"""
    db = _mock_db()
    with (
        patch("services.knowledge._process_document"),
        patch(
            "services.knowledge.asyncio.create_task", new=lambda c: MagicMock()
        ),
    ):
        doc = await upload_document(db, "note.txt", "企业开户需要营业执照及法人身份证件".encode(), uploaded_by=1)
    assert doc.status == "processing"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


# ========== 批量上传（多文件） ==========

@pytest.mark.anyio
async def test_upload_documents_partial_failure():
    """单文件校验失败只影响该条结果，其余文件照常入库，顺序保持一致。"""
    db = _mock_db()
    ok_doc = MagicMock()
    ok_doc.id = 7
    ok_doc.status = "processing"

    async def _fake_upload(_db, filename, content, uploaded_by=None):
        if filename == "bad.pdf":
            raise ValueError("PDF 文件无法解析: broken")
        return ok_doc

    with patch(
        "services.knowledge.upload_document", new=AsyncMock(side_effect=_fake_upload)
    ):
        results = await upload_documents(
            db,
            [("note.txt", b"hello"), ("bad.pdf", b"broken")],
            uploaded_by=1,
        )

    assert [r.filename for r in results] == ["note.txt", "bad.pdf"]

    assert results[0].success is True
    assert results[0].document_id == 7
    assert results[0].status == "processing"

    assert results[1].success is False
    assert results[1].document_id is None
    assert "无法解析" in results[1].message


@pytest.mark.anyio
async def test_upload_documents_isolates_unexpected_error():
    """未预期异常被隔离：记为该文件失败并回滚会话，后续文件继续处理。"""
    db = _mock_db()
    ok_doc = MagicMock()
    ok_doc.id = 9
    ok_doc.status = "processing"

    async def _fake_upload(_db, filename, content, uploaded_by=None):
        if filename == "boom.txt":
            raise RuntimeError("disk on fire")
        return ok_doc

    with patch(
        "services.knowledge.upload_document", new=AsyncMock(side_effect=_fake_upload)
    ):
        results = await upload_documents(
            db, [("boom.txt", b"x"), ("ok.txt", b"y")], uploaded_by=1
        )

    assert results[0].success is False
    assert results[0].message == "文件处理失败，请重试"
    assert results[1].success is True
    db.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_upload_documents_rejects_too_many_files():
    """超过单批文件数上限时整批拒绝，一个文件都不处理。"""
    db = _mock_db()
    upload_mock = AsyncMock()
    files = [(f"f{i}.txt", b"x") for i in range(MAX_UPLOAD_FILES + 1)]

    with patch("services.knowledge.upload_document", new=upload_mock):
        with pytest.raises(ValueError, match="最多上传"):
            await upload_documents(db, files, uploaded_by=1)

    upload_mock.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.anyio
async def test_upload_documents_accepts_exactly_max_files():
    """正好等于上限时不被拒绝（边界）。"""
    db = _mock_db()
    ok_doc = MagicMock()
    ok_doc.id = 1
    ok_doc.status = "processing"
    files = [(f"f{i}.txt", b"x") for i in range(MAX_UPLOAD_FILES)]

    with patch(
        "services.knowledge.upload_document", new=AsyncMock(return_value=ok_doc)
    ):
        results = await upload_documents(db, files, uploaded_by=1)

    assert len(results) == MAX_UPLOAD_FILES
    assert all(r.success for r in results)
