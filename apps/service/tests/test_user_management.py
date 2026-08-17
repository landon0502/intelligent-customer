import pytest
from unittest.mock import AsyncMock, MagicMock
from services.auth import list_users, create_user, delete_user


def _execute_result(scalar_one_or_none_value=None):
    """构造 db.execute 返回的 result（scalar_one_or_none 模式，供 get_user_by_username 使用）"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none_value
    return result


def _make_user(id, username, role):
    u = MagicMock()
    u.id = id
    u.username = username
    u.role = role
    return u


# ---------- list_users ----------

@pytest.mark.anyio
async def test_list_users_returns_all():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _make_user(1, "admin", "admin"),
        _make_user(2, "zhang_san", "user"),
    ]
    db.execute = AsyncMock(return_value=result)

    users = await list_users(db)

    assert len(users) == 2
    assert users[0].username == "admin"
    assert users[1].role == "user"


# ---------- create_user ----------

@pytest.mark.anyio
async def test_create_user_uses_default_role():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock(return_value=_execute_result(None))  # 用户名不重复

    user = await create_user(db, username="newuser", password="password123")

    assert user.username == "newuser"
    assert user.role == "user"
    assert user.password_hash != "password123"
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_create_user_with_admin_role():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock(return_value=_execute_result(None))

    user = await create_user(db, username="newadmin", password="password123", role="admin")

    assert user.role == "admin"


@pytest.mark.anyio
async def test_create_user_duplicate_username_raises():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=_execute_result(_make_user(1, "newuser", "user"))
    )

    with pytest.raises(ValueError, match="用户名已存在"):
        await create_user(db, username="newuser", password="password123")


@pytest.mark.anyio
async def test_create_user_short_password_raises():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_execute_result(None))

    with pytest.raises(ValueError, match="密码至少 6 位"):
        await create_user(db, username="newuser", password="123")


@pytest.mark.anyio
async def test_create_user_invalid_role_raises():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_execute_result(None))

    with pytest.raises(ValueError, match="非法角色"):
        await create_user(db, username="newuser", password="password123", role="super")


# ---------- delete_user ----------

@pytest.mark.anyio
async def test_delete_user_success():
    db = AsyncMock()
    db.get = AsyncMock(return_value=_make_user(3, "zhang_san", "user"))
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    result = await delete_user(db, user_id=3, current_user_id=1)

    assert result is True
    db.delete.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_delete_user_not_found_returns_none():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    result = await delete_user(db, user_id=99, current_user_id=1)

    assert result is None


@pytest.mark.anyio
async def test_delete_user_admin_raises():
    db = AsyncMock()
    db.get = AsyncMock(return_value=_make_user(1, "admin", "admin"))

    with pytest.raises(ValueError, match="不能删除管理员用户"):
        await delete_user(db, user_id=1, current_user_id=2)


@pytest.mark.anyio
async def test_delete_user_self_raises():
    db = AsyncMock()
    db.get = AsyncMock(return_value=_make_user(1, "zhang_san", "user"))

    with pytest.raises(ValueError, match="不能删除当前登录用户"):
        await delete_user(db, user_id=1, current_user_id=1)
