from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core import security
from app.core.redis_client import (
    revoke_token, revoke_all_user_tokens,
    is_token_revoked, is_user_globally_revoked,
    increment_login_attempts, get_login_attempts, reset_login_attempts,
)
from app.core.tenant_context import get_current_tenant
from app.models.user import User
from app.repositories import user_repo
from app.core.logging import logger

MAX_LOGIN_ATTEMPTS = 5


class AuthError(Exception):
    def __init__(self, message: str, code: str = "auth_error", remaining: int | None = None):
        self.message = message
        self.code = code
        self.remaining = remaining
        super().__init__(message)


async def authenticate(db: AsyncSession, email: str, password: str, ip: str) -> User:
    attempts = await get_login_attempts(ip, email)
    if attempts >= MAX_LOGIN_ATTEMPTS:
        raise AuthError("Trop de tentatives. Réessayez dans 15 minutes.", "rate_limited")

    user = await user_repo.get_by_email(db, email)
    if not user or not security.verify_password(password, user.hashed_password):
        new_count = await increment_login_attempts(ip, email)
        remaining = max(0, MAX_LOGIN_ATTEMPTS - new_count)
        logger.warning("login_failed", email=email, ip=ip, attempts=new_count)
        raise AuthError("Email ou mot de passe incorrect.", "invalid_credentials", remaining=remaining)

    if not user.is_active:
        raise AuthError("Compte désactivé. Contactez l'administrateur.", "account_disabled")

    await reset_login_attempts(ip, email)
    return user


def issue_tokens(user: User, totp_verified: bool = False) -> tuple[str, str]:
    """Émet le couple access/refresh du cabinet courant.

    Le claim `tid` lie le jeton à un cabinet précis. Le secret JWT étant global,
    cette liaison n'est pas cosmétique : sans elle, un jeton émis pour le cabinet
    A serait cryptographiquement valide pour le cabinet B. C'est le middleware
    qui la fait respecter en routant la session sur le schéma de `tid`.
    """
    tenant = get_current_tenant()
    needs_totp = user.requires_2fa and user.totp_enabled
    pending = needs_totp and not totp_verified
    extra = {
        "role": user.role,
        "totp_pending": pending,
        "tid": tenant.id,
    }
    access = security.create_access_token(user.id, extra=extra)
    # Le refresh porte aussi l'état 2FA → /refresh ne peut pas émettre un access « propre »
    # tant que la 2FA n'est pas validée (corrige le contournement 2FA via /refresh).
    refresh = security.create_refresh_token(
        user.id, extra={"totp_pending": pending, "tid": tenant.id}
    )
    return access, refresh


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    try:
        payload = security.decode_token(refresh_token)
    except Exception:
        raise AuthError("Token invalide ou expiré.", "invalid_token")

    if payload.get("type") != "refresh":
        raise AuthError("Token invalide.", "invalid_token")

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if jti and await is_token_revoked(jti):
        raise AuthError("Session révoquée.", "revoked")
    if user_id and await is_user_globally_revoked(user_id):
        raise AuthError("Session révoquée.", "revoked")

    user = await user_repo.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise AuthError("Utilisateur introuvable ou désactivé.", "not_found")

    if jti:
        ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_HOURS * 3600
        await revoke_token(jti, ttl)

    # Propagation de l'état 2FA : si le refresh est totp_pending (émis avant validation TOTP),
    # le nouvel access reste totp_pending → pas de contournement.
    refresh_pending = bool(payload.get("totp_pending"))
    return issue_tokens(user, totp_verified=not refresh_pending)


async def logout(refresh_token: str) -> None:
    jti = security.token_jti(refresh_token)
    if jti:
        ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_HOURS * 3600
        await revoke_token(jti, ttl)


async def logout_all_sessions(user_id: str) -> None:
    ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_HOURS * 3600
    await revoke_all_user_tokens(user_id, ttl)
