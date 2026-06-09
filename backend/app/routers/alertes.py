from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_rc
from app.models.alerte import Alerte
from app.models.user import User
from app.repositories import alertes_repo, audit_repo
from app.schemas.alertes import AlerteCreate, AlerteOut, AlerteTraiter

router = APIRouter(prefix="/alertes", tags=["alertes"])


@router.get("", response_model=list[AlerteOut])
async def list_alertes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    statut: str | None = Query(None),
    niveau: str | None = Query(None),
    dossier_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[AlerteOut]:
    q = select(Alerte).order_by(Alerte.created_at.desc())
    if statut:
        q = q.where(Alerte.statut == statut)
    if niveau:
        q = q.where(Alerte.niveau == niveau)
    if dossier_id:
        q = q.where(Alerte.dossier_id == dossier_id)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return [AlerteOut.from_orm_safe(a) for a in result.scalars().all()]


@router.post("", response_model=AlerteOut, status_code=status.HTTP_201_CREATED)
async def create_alerte(
    body: AlerteCreate,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> AlerteOut:
    alerte = await alertes_repo.create(
        db,
        dossier_id=body.dossier_id,
        type_alerte=body.type_alerte,
        niveau=body.niveau,
        description=body.description,
    )
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="alerte.created",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="alerte",
        entity_id=alerte.id,
        ip=ip,
        detail={"type_alerte": body.type_alerte, "niveau": body.niveau, "dossier_id": body.dossier_id},
    )
    return AlerteOut.from_orm_safe(alerte)


@router.get("/{alerte_id}", response_model=AlerteOut)
async def get_alerte(
    alerte_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlerteOut:
    result = await db.execute(select(Alerte).where(Alerte.id == alerte_id))
    alerte = result.scalar_one_or_none()
    if not alerte:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte introuvable.")
    return AlerteOut.from_orm_safe(alerte)


@router.patch("/{alerte_id}/traiter", response_model=AlerteOut)
async def traiter_alerte(
    alerte_id: str,
    body: AlerteTraiter,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> AlerteOut:
    result = await db.execute(select(Alerte).where(Alerte.id == alerte_id))
    alerte = result.scalar_one_or_none()
    if not alerte:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte introuvable.")
    alerte = await alertes_repo.update_statut(db, alerte, body.statut, current_user.id, body.resolution_note)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="alerte.traitee",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="alerte",
        entity_id=alerte_id,
        ip=ip,
        detail={"statut": body.statut, "note": body.resolution_note},
    )
    return AlerteOut.from_orm_safe(alerte)
