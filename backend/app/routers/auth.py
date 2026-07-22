from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.core.database import get_db, tenant_session
from app.core.config import settings
from app.core import security, tenant_resolver
from app.core.deps import get_current_user_for_password_change
from app.core.redis_client import get_login_attempts, increment_login_attempts
from app.core.tenant_context import TenantContext, tenant_scope
from app.models.user import User
from app.services.auth_service import (
    authenticate, issue_tokens, refresh_access_token, logout, AuthError, MAX_LOGIN_ATTEMPTS,
)
from app.schemas.auth import LoginRequest, LoginResponse, TenantOut, TokenResponse, UserOut, PasswordChangeRequest

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"
_COOKIE_MAX_AGE = settings.JWT_REFRESH_TOKEN_EXPIRE_HOURS * 3600


def _set_refresh_cookie(response: Response, token: str) -> None:
    is_prod = settings.APP_ENV == "production"
    response.set_cookie(
        key=_REFRESH_COOKIE, value=token, httponly=True,
        secure=is_prod, samesite="strict" if is_prod else "lax",
        max_age=_COOKIE_MAX_AGE, path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path="/api/auth")


_INVALID_CREDENTIALS = "Email ou mot de passe incorrect."

# Empreinte bcrypt « leurre », calculée une fois. Sur un email inconnu, aucun
# hash réel n'est vérifié : la réponse reviendrait bien plus vite que pour un
# compte existant (où bcrypt s'exécute), rouvrant l'oracle d'énumération par
# mesure de temps. On vérifie donc ce leurre pour aligner le coût des deux
# chemins. Le mot de passe ne correspondra jamais — seul le temps compte.
_DUMMY_HASH = security.hash_password("timing-equalizer-not-a-real-password")


def _assert_tenant_usable(tenant: TenantContext) -> None:
    """Portier : un cabinet non actif ne peut pas ouvrir de session."""
    if tenant.statut == "configuration":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "tenant_configuration",
                    "message": "Cabinet en cours de configuration. Contactez votre administrateur."},
        )
    if tenant.statut == "suspendu":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "tenant_suspended",
                    "message": "Accès suspendu. Contactez l'administrateur de la plateforme."},
        )
    if tenant.statut == "archive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "tenant_archived", "message": "Ce cabinet est archivé."},
        )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, response: Response) -> LoginResponse:
    """Connexion : l'email désigne le cabinet, qui désigne le schéma.

    Aucune session métier n'est ouverte avant d'avoir identifié le cabinet — le
    routage précède l'authentification, jamais l'inverse.
    """
    ip = request.client.host if request.client else "unknown"

    tenant = await tenant_resolver.get_by_email(body.email)
    if tenant is None:
        # Email non rattaché à un cabinet. La réponse doit être STRICTEMENT
        # indiscernable de celle d'un mot de passe erroné sur un compte existant,
        # sinon la forme du corps (présence/absence de `remaining_attempts`) et le
        # basculement en 429 deviennent un oracle d'énumération : un attaquant
        # distingue en une requête les emails clients de la plateforme des autres.
        # On applique donc ici le même rate-limit et la même charge utile, via
        # l'espace de noms Redis « plateforme » (hors cabinet, faute de tenant),
        # et l'on aligne le temps de réponse en vérifiant une empreinte leurre.
        security.verify_password(body.password, _DUMMY_HASH)
        if await get_login_attempts(ip, body.email) >= MAX_LOGIN_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives. Réessayez dans 15 minutes.",
            )
        new_count = await increment_login_attempts(ip, body.email)
        remaining = max(0, MAX_LOGIN_ATTEMPTS - new_count)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": _INVALID_CREDENTIALS, "remaining_attempts": remaining},
        )

    _assert_tenant_usable(tenant)

    with tenant_scope(tenant):
        async with tenant_session(tenant) as db:
            try:
                user = await authenticate(db, body.email, body.password, ip)
            except AuthError as exc:
                if exc.code == "rate_limited":
                    raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message)
                detail: dict | str = exc.message
                if exc.remaining is not None:
                    detail = {"message": exc.message, "remaining_attempts": exc.remaining}
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

            access_token, refresh_token = issue_tokens(user)
            payload = LoginResponse(
                access_token=access_token,
                user=UserOut.model_validate(user),
                totp_pending=user.requires_2fa and user.totp_enabled,
                tenant=TenantOut(id=tenant.id, slug=tenant.slug, nom=tenant.nom, statut=tenant.statut),
            )

    _set_refresh_cookie(response, refresh_token)
    return payload


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response) -> TokenResponse:
    """Renouvellement de session.

    Le cabinet est relu depuis le claim `tid` du refresh token : cet endpoint
    n'a pas d'en-tête Authorization, le middleware ne peut donc pas l'avoir
    résolu en amont.
    """
    token = request.cookies.get(_REFRESH_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expirée.")

    try:
        tenant_id = security.decode_token(token).get("tid")
    except Exception:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré.")

    tenant = await tenant_resolver.get_by_id(tenant_id) if tenant_id else None
    if tenant is None:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cabinet introuvable.")

    _assert_tenant_usable(tenant)

    with tenant_scope(tenant):
        async with tenant_session(tenant) as db:
            try:
                access_token, new_refresh = await refresh_access_token(db, token)
            except AuthError as exc:
                _clear_refresh_cookie(response)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)

    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(request: Request, response: Response) -> None:
    token = request.cookies.get(_REFRESH_COOKIE)
    if token:
        # La liste de révocation Redis est cloisonnée par cabinet : il faut se
        # replacer dans le bon cabinet, sinon le jeton serait révoqué dans un
        # espace de noms où personne ne le cherchera.
        tenant = None
        try:
            tenant_id = security.decode_token(token).get("tid")
            if tenant_id:
                tenant = await tenant_resolver.get_by_id(tenant_id)
        except Exception:
            tenant = None
        with tenant_scope(tenant):
            await logout(token)
    _clear_refresh_cookie(response)


@router.patch("/password", response_model=LoginResponse)
async def change_password(body: PasswordChangeRequest, response: Response, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user_for_password_change)) -> LoginResponse:
    if not security.verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mot de passe actuel incorrect.")
    new_hashed = security.hash_password(body.new_password)
    await db.execute(update(User).where(User.id == current_user.id).values(hashed_password=new_hashed, must_change_password=False))
    await db.commit()
    await db.refresh(current_user)
    access_token, refresh_token = issue_tokens(current_user)
    _set_refresh_cookie(response, refresh_token)
    return LoginResponse(access_token=access_token, user=UserOut.model_validate(current_user), totp_pending=False)
