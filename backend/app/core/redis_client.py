from redis.asyncio import Redis, from_url
from app.core.config import settings

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = await from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


REVOKED_PREFIX = "revoked_token:"
RATE_LIMIT_PREFIX = "rate_login:"


async def revoke_token(jti: str, ttl_seconds: int) -> None:
    r = await get_redis()
    await r.setex(f"{REVOKED_PREFIX}{jti}", ttl_seconds, "1")


async def is_token_revoked(jti: str) -> bool:
    r = await get_redis()
    return await r.exists(f"{REVOKED_PREFIX}{jti}") == 1


async def revoke_all_user_tokens(user_id: str, ttl_seconds: int) -> None:
    r = await get_redis()
    await r.setex(f"{REVOKED_PREFIX}user:{user_id}", ttl_seconds, "1")


async def is_user_globally_revoked(user_id: str) -> bool:
    r = await get_redis()
    return await r.exists(f"{REVOKED_PREFIX}user:{user_id}") == 1


async def increment_login_attempts(ip: str) -> int:
    r = await get_redis()
    key = f"{RATE_LIMIT_PREFIX}{ip}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, 900)
    return count


async def get_login_attempts(ip: str) -> int:
    r = await get_redis()
    val = await r.get(f"{RATE_LIMIT_PREFIX}{ip}")
    return int(val) if val else 0


async def reset_login_attempts(ip: str) -> None:
    r = await get_redis()
    await r.delete(f"{RATE_LIMIT_PREFIX}{ip}")
