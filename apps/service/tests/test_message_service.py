"""消息服务测试 —— create_message 创建消息并 touch 会话 updated_at。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from schemas.conversation import Conversation
from services.message import create_message


@pytest.mark.anyio
async def test_create_message_touches_conversation_updated_at():
    """创建消息后，会话 updated_at 更新语句被执行（支撑会话列表按更新时间倒序）。"""
    db = AsyncMock()

    with patch("services.message.update") as mock_update:
        stmt_mock = MagicMock()
        mock_update.return_value = stmt_mock
        stmt_mock.where.return_value.values.return_value = "update_stmt"

        msg = await create_message(db, 7, "user", "你好，请帮我查询企业开户")

    # 更新目标是 conversations 表
    mock_update.assert_called_once_with(Conversation)
    # where 限定会话 id=7
    stmt_mock.where.assert_called_once()
    # 更新语句与消息插入同一事务提交
    db.execute.assert_awaited_once()
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    assert msg.role == "user"
    assert msg.content == "你好，请帮我查询企业开户"
