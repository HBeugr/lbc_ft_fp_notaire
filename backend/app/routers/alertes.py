from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_rc
from app.models.alerte import Alerte
from app.models.user import User
from app.repositories import alertes_repo, audit_repo, dossier_repo
from app.schemas.alertes import AlerteCreate, AlerteOut, AlerteTraiter, AlerteListResponse, SignalementInterneRequest

router = APIRouter(prefix="/alertes", tags=["alertes"])


@router.get("", response_model=AlerteListResponse)
async def list_alertes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    statut: str | None = Query(None),
    niveau: str | None = Query(None),
    type_alerte: str | None = Query(None),
    dossier_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> AlerteListResponse:
    items, total = await alertes_repo.list_alertes(
        db,
        statut=statut,
        niveau=niveau,
        type_alerte=type_alerte,
        dossier_id=dossier_id,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return AlerteListResponse(
        items=[AlerteOut.from_orm_safe(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


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


# ── Signalement interne (clercs) — doit précéder /{alerte_id} ─────────────────
_SIGNALEUR_ROLES = ("clercs", "admin")


@router.post("/signaler", response_model=AlerteOut, status_code=status.HTTP_201_CREATED)
async def signaler_alerte_interne(
    body: SignalementInterneRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlerteOut:
    """Un clerc signale une suspicion au Responsable Conformité (CDC — Art. 29)."""
    if current_user.role not in _SIGNALEUR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux clercs et à l'administrateur.",
        )
    dossier_id: str | None = None
    if body.dossier_reference:
        dossier = await dossier_repo.get_by_reference(db, body.dossier_reference)
        if dossier is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dossier introuvable : {body.dossier_reference}",
            )
        dossier_id = dossier.id
    alerte = await alertes_repo.create(
        db,
        dossier_id=dossier_id,
        type_alerte="SIGNALEMENT_INTERNE",
        niveau="MOYEN",
        description=f"[Signalement {current_user.first_name} {current_user.last_name}] {body.description}",
        signaleur_id=current_user.id,
    )
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="alerte.signalement_interne",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="alerte",
        entity_id=alerte.id,
        ip=ip,
        detail={"dossier_reference": body.dossier_reference},
    )
    return AlerteOut.from_orm_safe(alerte)


@router.get("/mes-signalements", response_model=list[AlerteOut])
async def mes_signalements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AlerteOut]:
    """Retourne les signalements internes émis par l'utilisateur courant."""
    if current_user.role not in _SIGNALEUR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux clercs.")
    items = await alertes_repo.list_by_signaleur(db, signaleur_id=current_user.id)
    return [AlerteOut.from_orm_safe(a) for a in items]


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
