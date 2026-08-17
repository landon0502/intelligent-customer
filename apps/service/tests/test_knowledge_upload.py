"""知识库上传校验测试 —— 大小上限与内容有效性（S7）。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.knowledge import MAX_UPLOAD_SIZE, upload_document


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
