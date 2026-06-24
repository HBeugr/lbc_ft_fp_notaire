from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security as sec
from app.core.database import get_db
from app.core.redis_client import (
    is_token_revoked,
    is_user_globally_revoked,
    increment_totp_attempts,
    get_totp_attempts,
    reset_totp_attempts,
    TOTP_MAX_ATTEMPTS,
)
from app.models.user import User
from app.repositories import user_repo
from app.schemas.totp import (
    TotpActivateRequest,
    TotpActivateResponse,
    TotpBackupCodesResponse,
    TotpBackupVerifyRequest,
    TotpSetupResponse,
    TotpVerifyRequest,
    TotpVerifyResponse,
)
from app.services import totp_service
from app.services.auth_service import issue_tokens

router = APIRouter(prefix="/auth/totp", tags=["totp"])
_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def _get_user_from_token(token: str, db: AsyncSession, allow_pending: bool = False) -> User:
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide.")
    try:
        payload = sec.decode_token(token)
    except Exception:
        raise exc
    if payload.get("type") != "access":
        raise exc
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise exc
    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise exc
    if await is_user_globally_revoked(user_id):
        raise exc
    if not allow_pending and payload.get("totp_pending"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vérification 2FA requise.")
    user = await user_repo.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise exc
    return user


@router.post("/setup", response_model=TotpSetupResponse)
async def setup(token: str = Depends(_oauth2), db: AsyncSession = Depends(get_db)) -> TotpSetupResponse:
    user = await _get_user_from_token(token, db, allow_pending=False)
    if not user.requires_2fa:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="2FA non requis pour ce rôle.")
    if user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="2FA déjà activé.")
    secret = totp_service.generate_secret()
    await totp_service.store_pending_secret(user.id, secret)
    uri = totp_service.provisioning_uri(secret, user.email)
    return TotpSetupResponse(provisioning_uri=uri, qr_data=uri)


@router.post("/activate", response_model=TotpActivateResponse)
async def activate(body: TotpActivateRequest, token: str = Depends(_oauth2), db: AsyncSession = Depends(get_db)) -> TotpActivateResponse:
    user = await _get_user_from_token(token, db, allow_pending=False)
    if not user.requires_2fa:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="2FA non requis pour ce rôle.")
    if user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="2FA déjà activé.")
    secret = await totp_service.pop_pending_secret(user.id)
    if not secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session d'activation expirée.")
    if not totp_service.verify_code(secret, body.code):
        await totp_service.store_pending_secret(user.id, secret)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Code invalide.")
    encrypted = totp_service.encrypt_secret(secret)
    plain_codes, hashed_json = totp_service.generate_backup_codes()
    await user_repo.update(db, user, totp_secret=encrypted, totp_enabled=True, totp_backup_codes=hashed_json)
    # Affichés une seule fois — l'utilisateur doit les conserver
    return TotpActivateResponse(backup_codes=plain_codes)


@router.post("/backup-codes/regenerate", response_model=TotpBackupCodesResponse)
async def regenerate_backup_codes(token: str = Depends(_oauth2), db: AsyncSession = Depends(get_db)) -> TotpBackupCodesResponse:
    """Régénère les codes de secours (session pleinement authentifiée, 2FA déjà actif)."""
    user = await _get_user_from_token(token, db, allow_pending=False)
    if not user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA non activé.")
    plain_codes, hashed_json = totp_service.generate_backup_codes()
    await user_repo.update(db, user, totp_backup_codes=hashed_json)
    return TotpBackupCodesResponse(backup_codes=plain_codes)


@router.post("/verify", response_model=TotpVerifyResponse)
async def verify(body: TotpVerifyRequest, token: str = Depends(_oauth2), db: AsyncSession = Depends(get_db)) -> TotpVerifyResponse:
    user = await _get_user_from_token(token, db, allow_pending=True)
    payload = sec.decode_token(token)
    if not payload.get("totp_pending"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP non requis pour cette session.")
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA non configuré.")
    if await get_totp_attempts(user.id) >= TOTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Trop de tentatives. Réessayez plus tard.")
    secret = totp_service.decrypt_secret(user.totp_secret)
    if not totp_service.verify_code(secret, body.code):
        await increment_totp_attempts(user.id)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Code invalide.")
    await reset_totp_attempts(user.id)
    new_access, _ = issue_tokens(user, totp_verified=True)
    return TotpVerifyResponse(access_token=new_access)


@router.post("/verify-backup", response_model=TotpVerifyResponse)
async def verify_backup(body: TotpBackupVerifyRequest, token: str = Depends(_oauth2), db: AsyncSession = Depends(get_db)) -> TotpVerifyResponse:
    """Récupération 2FA : vérifie un code de secours (à usage unique) en lieu et place du TOTP."""
    user = await _get_user_from_token(token, db, allow_pending=True)
    payload = sec.decode_token(token)
    if not payload.get("totp_pending"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP non requis pour cette session.")
    if not user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA non configuré.")
    if await get_totp_attempts(user.id) >= TOTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Trop de tentatives. Réessayez plus tard.")
    ok, remaining_json = totp_service.consume_backup_code(user.totp_backup_codes, body.code)
    if not ok:
        await increment_totp_attempts(user.id)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Code de secours invalide.")
    await reset_totp_attempts(user.id)
    await user_repo.update(db, user, totp_backup_codes=remaining_json)
    new_access, _ = issue_tokens(user, totp_verified=True)
    return TotpVerifyResponse(access_token=new_access)
