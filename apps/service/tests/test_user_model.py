from schemas.user import User


def test_user_model_fields():
    user = User(username="testuser", password_hash="hashed", role="user")
    assert user.username == "testuser"
    assert user.password_hash == "hashed"
    assert user.role == "user"


def test_user_model_default_role():
    user = User(username="testuser", password_hash="hashed")
    assert user.role == "user"
