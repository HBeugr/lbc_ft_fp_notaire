from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core import security
from app.core.deps import require_admin
from app.core.redis_client import revoke_all_user_tokens
from app.models.user import User
from app.repositories import user_repo, audit_repo

router = APIRouter(prefix="/admin", tags=["admin"])

_REVOKE_TTL = settings.JWT_REFRESH_TOKEN_EXPIRE_HOURS * 3600


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8)
    must_change_password: bool = True


@router.post("/users/{user_id}/revoke-sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_user_sessions(
    user_id: str,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    target = await user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
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
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    target = await user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
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


@router.delete("/users/{user_id}/totp", status_code=status.HTTP_204_NO_CONTENT)
async def disable_user_totp(
    user_id: str,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    target = await user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if not target.totp_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="2FA non activé pour cet utilisateur.")
    await user_repo.update(db, target, totp_secret=None, totp_enabled=False)
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
