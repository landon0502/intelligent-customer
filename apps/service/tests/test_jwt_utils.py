import pytest
from app.utils.jwt import create_token, verify_token


def test_create_and_verify_token():
    token = create_token(user_id=1, username="admin", role="admin")
    payload = verify_token(token)
    assert payload["sub"] == 1
    assert payload["username"] == "admin"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_verify_invalid_token_raises():
    with pytest.raises(ValueError, match="无效的 Token"):
        verify_token("invalid.token.here")
