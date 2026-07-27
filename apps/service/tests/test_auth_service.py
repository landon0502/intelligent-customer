import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.auth import authenticate_user, register_user, get_user_by_username


@pytest.mark.anyio
async def test_register_user_creates_new_user():
    db = AsyncMock()
    db.add = MagicMock()  # Session.add is synchronous
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    user = await register_user(db, username="newuser", password="password123")
    assert user.username == "newuser"
    assert user.role == "user"
    assert user.password_hash != "password123"
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_authenticate_user_with_correct_password():
    db = AsyncMock()
    from app.utils.password import hash_password
    mock_user = MagicMock()
    mock_user.username = "testuser"
    mock_user.password_hash = hash_password("password123")
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user)))
    user = await authenticate_user(db, username="testuser", password="password123")
    assert user is not None
    assert user.username == "testuser"


@pytest.mark.anyio
async def test_authenticate_user_with_wrong_password_returns_none():
    db = AsyncMock()
    from app.utils.password import hash_password
    mock_user = MagicMock()
    mock_user.password_hash = hash_password("password123")
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user)))
    user = await authenticate_user(db, username="testuser", password="wrongpassword")
    assert user is None


@pytest.mark.anyio
async def test_authenticate_user_not_found_returns_none():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    user = await authenticate_user(db, username="nonexistent", password="password123")
    assert user is None
