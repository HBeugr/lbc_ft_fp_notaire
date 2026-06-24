from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.database import get_db
from app.core.redis_client import is_token_revoked, is_user_globally_revoked
from app.models.user import User
from app.repositories import user_repo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def _resolve_user(token: str, db: AsyncSession) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalide ou expirée.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = security.decode_token(token)
    except Exception:
        raise credentials_exc

    if payload.get("type") != "access":
        raise credentials_exc

    if payload.get("totp_pending"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vérification 2FA requise.",
        )

    jti = payload.get("jti")
    user_id: str | None = payload.get("sub")

    if not user_id:
        raise credentials_exc

    if jti and await is_token_revoked(jti):
        raise credentials_exc

    if await is_user_globally_revoked(user_id):
        raise credentials_exc

    user = await user_repo.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise credentials_exc

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _resolve_user(token, db)
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "must_change_password", "message": "Vous devez changer votre mot de passe avant de continuer."},
        )
    return user


async def get_current_user_for_password_change(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _resolve_user(token, db)


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs.")
    return user


async def require_user_manager(user: User = Depends(get_current_user)) -> User:
    """Gestion des utilisateurs : Admin et Notaire Principal (parité immo dirigeant)."""
    if user.role not in ("admin", "notaire_principal"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gestion des utilisateurs réservée à l'Admin et au Notaire Principal.")
    return user


async def require_supervisor(user: User = Depends(get_current_user)) -> User:
    if not user.is_supervisor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès insuffisant.")
    return user


async def require_rc(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "notaire_principal", "responsable_conformite"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé au Responsable Conformité.")
    return user
