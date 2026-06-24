import base64
import json
import secrets

import pyotp
from cryptography.fernet import Fernet

from app.core import security as sec
from app.core.config import settings
from app.core.redis_client import get_redis

_PENDING_PREFIX = "totp_pending:"
_PENDING_TTL = 300

# Codes de secours 2FA
_BACKUP_CODE_COUNT = 10
_BACKUP_CODE_BYTES = 5  # → 10 caractères hex par code


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


# ── Codes de secours 2FA ────────────────────────────────────────────────────

def generate_backup_codes() -> tuple[list[str], str]:
    """Génère des codes de secours en clair + leur représentation hachée (JSON bcrypt).

    Le clair n'est retourné qu'une seule fois (à l'activation / régénération).
    Les hachages sont stockés en base ; chaque code est à usage unique.
    """
    plain = [secrets.token_hex(_BACKUP_CODE_BYTES) for _ in range(_BACKUP_CODE_COUNT)]
    hashed = [sec.hash_password(code) for code in plain]
    return plain, json.dumps(hashed)


def consume_backup_code(stored_json: str | None, code: str) -> tuple[bool, str | None]:
    """Vérifie un code de secours. Si valide, le retire et renvoie (True, nouveau_json).

    Retourne (False, None) si invalide. Le code saisi est normalisé (minuscules, sans espaces/tirets).
    """
    if not stored_json:
        return False, None
    try:
        hashes: list[str] = json.loads(stored_json)
    except (ValueError, TypeError):
        return False, None
    candidate = code.strip().lower().replace("-", "").replace(" ", "")
    for h in hashes:
        if sec.verify_password(candidate, h):
            remaining = [x for x in hashes if x != h]
            return True, json.dumps(remaining)
    return False, None


def count_backup_codes(stored_json: str | None) -> int:
    if not stored_json:
        return 0
    try:
        return len(json.loads(stored_json))
    except (ValueError, TypeError):
        return 0


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
