from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core import security
from app.core.deps import get_current_user, require_admin, require_user_manager
from app.models.user import User
from app.repositories import user_repo, audit_repo
from app.schemas.users import UserCreate, UserListOut, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.get("", response_model=UserListOut)
async def list_users(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> UserListOut:
    all_users = await user_repo.get_all(db)
    paginated = all_users[offset : offset + limit]
    return UserListOut(items=[UserOut.model_validate(u) for u in paginated], total=len(all_users))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    request: Request,
    admin: User = Depends(require_user_manager),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    existing = await user_repo.get_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé.")
    # Anti-escalade : seul un admin peut créer un compte admin.
    if body.role == "admin" and admin.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul un administrateur peut créer un compte administrateur.")
    hashed = security.hash_password(body.password)
    new_user = await user_repo.create(
        db,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        role=body.role,
        hashed_password=hashed,
        must_change_password=body.must_change_password,
    )
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="user.created",
        user_id=admin.id,
        user_role=admin.role,
        entity_type="user",
        entity_id=new_user.id,
        ip=ip,
        detail={"email": new_user.email, "role": new_user.role},
    )
    return UserOut.model_validate(new_user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    target = await user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    return UserOut.model_validate(target)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserUpdate,
    request: Request,
    admin: User = Depends(require_user_manager),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    target = await user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    # Anti-escalade : seul un admin peut gérer un compte admin ou promouvoir au rôle admin.
    if admin.role != "admin" and (target.role == "admin" or body.role == "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul un administrateur peut gérer un compte administrateur.")
    if user_id == admin.id and body.role is not None and body.role != "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de changer son propre rôle.")
    if user_id == admin.id and body.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de se désactiver soi-même.")
    updates = body.model_dump(exclude_none=True)
    updated = await user_repo.update(db, target, **updates)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="user.updated",
        user_id=admin.id,
        user_role=admin.role,
        entity_type="user",
        entity_id=user_id,
        ip=ip,
        detail=updates,
    )
    return UserOut.model_validate(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: str,
    request: Request,
    admin: User = Depends(require_user_manager),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de se désactiver soi-même.")
    target = await user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    await user_repo.update(db, target, is_active=False)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="user.deactivated",
        user_id=admin.id,
        user_role=admin.role,
        entity_type="user",
        entity_id=user_id,
        ip=ip,
    )
