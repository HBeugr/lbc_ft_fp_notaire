import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, _get_session_factory
from app.core.deps import get_current_user, require_rc
from app.core import security
from app.models.alerte import Alerte
from app.models.user import User
from app.repositories import alertes_repo, audit_repo, dossier_repo, user_repo
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


# ── Temps réel : compteur d'alertes (badge SSE) — doit précéder /{alerte_id} ──

@router.get("/mon-compteur")
async def mon_compteur(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Compteur d'alertes non traitées pour l'utilisateur (badge — fallback du SSE)."""
    count = await alertes_repo.count_open_for_user(db, current_user.id, current_user.is_supervisor)
    return {"count": count}


@router.get("/stream")
async def alertes_stream(token: str = Query(...)):
    """Flux SSE temps réel du compteur d'alertes (badge).
    Auth par query param car EventSource ne supporte pas l'en-tête Authorization."""
    try:
        payload = security.decode_token(token)
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide.")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide.")

    async def event_gen():
        factory = _get_session_factory()
        # Charge le rôle une fois (is_supervisor) pour le périmètre du compteur
        async with factory() as s:
            user = await user_repo.get_by_id(s, user_id)
        if user is None:
            yield ": error\n\n"
            return
        is_sup = user.is_supervisor
        last = None
        while True:
            try:
                async with factory() as s:
                    count = await alertes_repo.count_open_for_user(s, user_id, is_sup)
                if count != last:
                    last = count
                    yield f"event: count\ndata: {count}\n\n"
                else:
                    yield ": keepalive\n\n"
            except Exception:
                yield ": error\n\n"
            await asyncio.sleep(3)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{alerte_id}/timeline")
async def alerte_timeline(
    alerte_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Parcours chronologique d'une alerte (créée → traitée + note)."""
    result = await db.execute(select(Alerte).where(Alerte.id == alerte_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte introuvable.")
    events = [{"label": "Alerte créée", "at": a.created_at.isoformat() if a.created_at else None, "par": None}]
    if a.traite_at:
        events.append({
            "label": "Traitée",
            "at": a.traite_at.isoformat(),
            "par": a.traite_par,
            "note": a.resolution_note,
        })
    return {"alerte_id": alerte_id, "statut": a.statut, "type_alerte": a.type_alerte, "events": events}


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
