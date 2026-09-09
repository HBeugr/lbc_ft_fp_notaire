"""Client Redis — cloisonné par cabinet.

Toutes les clés sont préfixées par le cabinet courant. Sans cela, Redis
constituerait un canal latéral entre tenants alors même que les données sont
isolées au niveau des schémas PostgreSQL : révoquer une session ou bloquer une
IP dans un cabinet affecterait les autres.

Les compteurs anti-brute-force sont en outre segmentés par email et non par
seule IP : derrière un NAT d'entreprise, une IP partagée bloquait auparavant
tous les utilisateurs — un déni de service inter-cabinets exploitable.
"""
from datetime import datetime, timezone

from redis.asyncio import Redis, from_url

from app.core.config import settings
from app.core.tenant_context import get_current_tenant_or_none

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = await from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


# Espace de noms hors cabinet : login avant routage, console Super-Admin.
_PLATFORM_NS = "plateforme"


def _ns() -> str:
    """Espace de noms Redis du cabinet courant."""
    tenant = get_current_tenant_or_none()
    return tenant.id if tenant is not None else _PLATFORM_NS


def _key(*parts: str) -> str:
    return ":".join(("t", _ns()) + parts)


REVOKED_PREFIX = "revoked_token"
RATE_LIMIT_PREFIX = "rate_login"


async def revoke_token(jti: str, ttl_seconds: int) -> None:
    r = await get_redis()
    await r.setex(_key(REVOKED_PREFIX, jti), ttl_seconds, "1")


async def is_token_revoked(jti: str) -> bool:
    r = await get_redis()
    return await r.exists(_key(REVOKED_PREFIX, jti)) == 1


async def revoke_all_user_tokens(user_id: str, ttl_seconds: int) -> None:
    """Invalide les sessions du compte ouvertes AVANT maintenant.

    On enregistre l'INSTANT de révocation, pas un simple drapeau. Un drapeau
    bannissait le compte pendant toute la durée de vie du refresh (8 h) — y
    compris les sessions ouvertes après coup. Effet de bord observé en
    production : après une réinitialisation de mot de passe par l'admin,
    l'utilisateur se connectait bien avec son mot de passe temporaire (le login
    ne consulte pas la révocation) mais TOUT appel authentifié repartait en 401,
    à commencer par le changement de mot de passe lui-même. Le compte était donc
    inutilisable jusqu'à expiration de la clé, et chaque nouvelle
    réinitialisation relançait le compteur.
    """
    r = await get_redis()
    # Horodatage à la microseconde (NumericDate non entier, autorisé par la
    # RFC 7519) : à la seconde près, une connexion légitime survenant dans la
    # même seconde que la révocation serait tuée à tort.
    now = datetime.now(timezone.utc).timestamp()
    await r.setex(_key(REVOKED_PREFIX, "user", user_id), ttl_seconds, repr(now))


async def is_user_globally_revoked(user_id: str, issued_at: int | float | None = None) -> bool:
    """Vrai si le jeton présenté est antérieur à la révocation globale du compte.

    `issued_at` est le claim `iat` du jeton. Absent (jeton émis par une version
    antérieure à l'horodatage), on tranche dans le sens de la sûreté : révoqué.
    """
    r = await get_redis()
    revoked_at = await r.get(_key(REVOKED_PREFIX, "user", user_id))
    if revoked_at is None:
        return False
    if issued_at is None:
        return True
    try:
        return float(issued_at) <= float(revoked_at)
    except (TypeError, ValueError):
        return True


async def increment_login_attempts(ip: str, email: str = "") -> int:
    r = await get_redis()
    key = _key(RATE_LIMIT_PREFIX, ip, email.lower())
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, 900)
    return count


async def get_login_attempts(ip: str, email: str = "") -> int:
    r = await get_redis()
    val = await r.get(_key(RATE_LIMIT_PREFIX, ip, email.lower()))
    return int(val) if val else 0


async def reset_login_attempts(ip: str, email: str = "") -> None:
    r = await get_redis()
    await r.delete(_key(RATE_LIMIT_PREFIX, ip, email.lower()))


# ── Rate-limiting 2FA (par utilisateur) — anti brute-force du 2nd facteur ───────
TOTP_RATE_PREFIX = "rate_totp"
TOTP_MAX_ATTEMPTS = 5
TOTP_LOCK_SECONDS = 900  # 15 min


async def increment_totp_attempts(user_id: str) -> int:
    r = await get_redis()
    key = _key(TOTP_RATE_PREFIX, user_id)
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, TOTP_LOCK_SECONDS)
    return count


async def get_totp_attempts(user_id: str) -> int:
    r = await get_redis()
    val = await r.get(_key(TOTP_RATE_PREFIX, user_id))
    return int(val) if val else 0


async def reset_totp_attempts(user_id: str) -> None:
    r = await get_redis()
    await r.delete(_key(TOTP_RATE_PREFIX, user_id))
