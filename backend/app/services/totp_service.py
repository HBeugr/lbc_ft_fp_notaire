import json
import secrets

import pyotp
from cryptography.fernet import Fernet

from app.core import security as sec
from app.core.crypto import derive_tenant_fernet
from app.core.redis_client import get_redis
from app.core.tenant_context import get_current_tenant

_PENDING_PREFIX = "totp_pending:"
_PENDING_TTL = 300


def _pending_key(user_id: str) -> str:
    """Clé Redis du secret 2FA en attente — cloisonnée par cabinet.

    Sans le préfixe cabinet, deux enrôlements simultanés dans deux cabinets
    différents pourraient se recouvrir si les identifiants utilisateur venaient
    à ne plus être uniques au niveau plateforme.
    """
    return f"t:{get_current_tenant().id}:{_PENDING_PREFIX}{user_id}"

# Codes de secours 2FA
_BACKUP_CODE_COUNT = 10
_BACKUP_CODE_BYTES = 5  # → 10 caractères hex par code


def _fernet() -> Fernet:
    """Clé de chiffrement des secrets TOTP — propre au cabinet.

    Auparavant dérivée directement de `AES_KEY` par décodage base64, alors que
    `crypto.py` en faisait un SHA-256 : deux dérivations divergentes de la même
    variable. On s'aligne désormais sur l'unique dérivation HKDF par cabinet,
    de sorte qu'un secret 2FA reste illisible hors de son cabinet d'origine.
    """
    return derive_tenant_fernet(get_current_tenant().key_salt)


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    """URI d'enrôlement 2FA.

    L'émetteur porte le nom du cabinet : sans cela, tous les cabinets
    apparaîtraient sous une même entrée dans l'application d'authentification
    de l'utilisateur, qui ne pourrait plus les distinguer.
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=get_current_tenant().nom)


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
    await redis.setex(_pending_key(user_id), _PENDING_TTL, encrypted)


async def pop_pending_secret(user_id: str) -> str | None:
    redis = await get_redis()
    key = _pending_key(user_id)
    encrypted = await redis.get(key)
    if not encrypted:
        return None
    await redis.delete(key)
    return decrypt_secret(encrypted)

