from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码"""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与哈希是否匹配"""
    return _pwd_context.verify(plain, hashed)
