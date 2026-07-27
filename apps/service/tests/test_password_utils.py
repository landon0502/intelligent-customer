from app.utils.password import hash_password, verify_password


def test_hash_and_verify_password():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert verify_password("mypassword", hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("mypassword")
    assert verify_password("wrongpassword", hashed) is False
