import base64
import pyotp
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.redis_client import get_redis

_PENDING_PREFIX = "totp_pending:"
_PENDING_TTL = 300


def _fernet() -> Fernet:
    key_bytes = base64.urlsafe_b64decode(settings.AES_KEY.encode())
    if len(key_bytes) != 32:
        raise ValueError("AES_KEY must decode to exactly 32 bytes")
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.TOTP_ISSUER)


def verify_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


async def store_pending_secret(user_id: str, secret: str) -> None:
    redis = await get_redis()
    encrypted = encrypt_secret(secret)
    await redis.setex(f"{_PENDING_PREFIX}{user_id}", _PENDING_TTL, encrypted)


async def pop_pending_secret(user_id: str) -> str | None:
    redis = await get_redis()
    key = f"{_PENDING_PREFIX}{user_id}"
    encrypted = await redis.get(key)
    if not encrypted:
        return None
    await redis.delete(key)
    return decrypt_secret(encrypted)
