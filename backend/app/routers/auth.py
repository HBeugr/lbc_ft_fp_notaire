from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.core.database import get_db
from app.core.config import settings
from app.core import security
from app.core.deps import get_current_user_for_password_change
from app.models.user import User
from app.services.auth_service import authenticate, issue_tokens, refresh_access_token, logout, AuthError
from app.schemas.auth import LoginRequest, LoginResponse, TokenResponse, UserOut, PasswordChangeRequest

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


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    ip = request.client.host if request.client else "unknown"
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
    _set_refresh_cookie(response, refresh_token)
    return LoginResponse(access_token=access_token, user=UserOut.model_validate(user), totp_pending=user.requires_2fa and user.totp_enabled)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    token = request.cookies.get(_REFRESH_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expirée.")
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
