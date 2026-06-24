import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from app.core.password_policy import validate_password_strength
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core import security
from app.core.deps import require_user_manager
from app.core.redis_client import revoke_all_user_tokens
from app.models.user import User
from app.repositories import user_repo, audit_repo

router = APIRouter(prefix="/admin", tags=["admin"])

_REVOKE_TTL = settings.JWT_REFRESH_TOKEN_EXPIRE_HOURS * 3600


def _generate_temp_password() -> str:
    """Mot de passe temporaire fort : 16 caractères, 4 classes garanties (politique ≥12)."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(16))
        if (any(c.isupper() for c in pwd) and any(c.islower() for c in pwd)
                and any(c.isdigit() for c in pwd) and any(not c.isalnum() for c in pwd)):
            return pwd


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=12)
    must_change_password: bool = True

    @field_validator("new_password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return validate_password_strength(v)


class TempPasswordResponse(BaseModel):
    temporary_password: str


@router.post("/users/{user_id}/revoke-sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_user_sessions(
    user_id: str,
    request: Request,
    admin: User = Depends(require_user_manager),
    db: AsyncSession = Depends(get_db),
) -> None:
    target = await user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if admin.role != "admin" and target.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul un administrateur peut gérer un compte administrateur.")
    await revoke_all_user_tokens(user_id, ttl_seconds=_REVOKE_TTL)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="admin.sessions_revoked",
        user_id=admin.id,
        user_role=admin.role,
        entity_type="user",
        entity_id=user_id,
        ip=ip,
    )


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_password(
    user_id: str,
    body: ResetPasswordRequest,
    request: Request,
    admin: User = Depends(require_user_manager),
    db: AsyncSession = Depends(get_db),
) -> None:
    target = await user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if admin.role != "admin" and target.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul un administrateur peut gérer un compte administrateur.")
    hashed = security.hash_password(body.new_password)
    await user_repo.update(db, target, hashed_password=hashed, must_change_password=body.must_change_password)
    await revoke_all_user_tokens(user_id, ttl_seconds=_REVOKE_TTL)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="admin.password_reset",
        user_id=admin.id,
        user_role=admin.role,
        entity_type="user",
        entity_id=user_id,
        ip=ip,
    )


@router.post("/users/{user_id}/reset-password/temporary", response_model=TempPasswordResponse)
async def reset_user_password_temporary(
    user_id: str,
    request: Request,
    admin: User = Depends(require_user_manager),
    db: AsyncSession = Depends(get_db),
) -> TempPasswordResponse:
    """Génère un mot de passe temporaire fort, force le changement à la prochaine connexion,
    révoque les sessions, et retourne le mot de passe en clair (affiché une seule fois)."""
    target = await user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if admin.role != "admin" and target.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul un administrateur peut gérer un compte administrateur.")
    temp = _generate_temp_password()
    hashed = security.hash_password(temp)
    await user_repo.update(db, target, hashed_password=hashed, must_change_password=True)
    await revoke_all_user_tokens(user_id, ttl_seconds=_REVOKE_TTL)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="admin.password_reset_temporary",
        user_id=admin.id,
        user_role=admin.role,
        entity_type="user",
        entity_id=user_id,
        ip=ip,
    )
    return TempPasswordResponse(temporary_password=temp)


@router.delete("/users/{user_id}/totp", status_code=status.HTTP_204_NO_CONTENT)
async def disable_user_totp(
    user_id: str,
    request: Request,
    admin: User = Depends(require_user_manager),
    db: AsyncSession = Depends(get_db),
) -> None:
    target = await user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if admin.role != "admin" and target.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul un administrateur peut gérer un compte administrateur.")
    if not target.totp_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="2FA non activé pour cet utilisateur.")
    await user_repo.update(db, target, totp_secret=None, totp_enabled=False, totp_backup_codes=None)
    await revoke_all_user_tokens(user_id, ttl_seconds=_REVOKE_TTL)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="admin.totp_disabled",
        user_id=admin.id,
        user_role=admin.role,
        entity_type="user",
        entity_id=user_id,
        ip=ip,
    )
