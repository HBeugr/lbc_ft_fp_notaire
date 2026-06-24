"""WRK-09 — Autorisations du Notaire Principal sur les dossiers Trigger T1 (PPE).

Réservé exclusivement au notaire_principal (non délégable, Art. 29 + séparation des
fonctions). Une décision AUTORISE/REFUSE par dossier ; REFUSE → blocage du dossier.
Registre confidentiel et immuable (table autorisations_dirigeant).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.alerte import Alerte
from app.models.user import User
from app.repositories import alertes_repo, audit_repo, dossier_repo

router = APIRouter(tags=["autorisations"])


class PendingWrk09Item(BaseModel):
    dossier_id: str
    dossier_reference: str
    type_dossier: str
    niveau_risque: str | None
    created_at: str
    alerte_id: str | None


class AutorisationCreate(BaseModel):
    decision: str  # "AUTORISE" | "REFUSE"
    justification: str | None = None


class AutorisationOut(BaseModel):
    id: str
    dossier_id: str
    dirigeant_id: str
    decision: str
    justification: str | None
    created_at: str


def _require_notaire_principal(user: User) -> None:
    if user.role != "notaire_principal":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="WRK-09 est réservé exclusivement au Notaire Principal (non délégable).",
        )


@router.get("/autorisations/wrk09/pending", response_model=list[PendingWrk09Item])
async def pending_wrk09(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PendingWrk09Item]:
    """Dossiers PPE (Trigger T1) en attente d'autorisation du Notaire Principal.

    Visible par les superviseurs ; seul le Notaire Principal peut décider."""
    if not current_user.is_supervisor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux superviseurs.")
    dossiers = await alertes_repo.get_pending_wrk09(db)
    items: list[PendingWrk09Item] = []
    for d in dossiers:
        alerte = (await db.execute(
            select(Alerte.id).where(Alerte.dossier_id == d.id, Alerte.type_alerte == "T1_PPE").limit(1)
        )).scalar_one_or_none()
        items.append(PendingWrk09Item(
            dossier_id=d.id,
            dossier_reference=d.reference,
            type_dossier=d.type_client,
            niveau_risque=d.classification,
            created_at=d.created_at.isoformat() if d.created_at else "",
            alerte_id=alerte,
        ))
    return items


@router.post("/dossiers/{dossier_id}/autorisation", response_model=AutorisationOut, status_code=status.HTTP_201_CREATED)
async def create_autorisation(
    dossier_id: str,
    body: AutorisationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutorisationOut:
    """Enregistre la décision WRK-09 (AUTORISE/REFUSE) — Notaire Principal uniquement."""
    _require_notaire_principal(current_user)
    if body.decision not in ("AUTORISE", "REFUSE"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Décision invalide (AUTORISE|REFUSE).")
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if dossier.trigger_actif != "T1":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce dossier n'a pas de Trigger T1 actif — WRK-09 non applicable.")
    if await alertes_repo.has_autorisation(db, dossier_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une autorisation a déjà été enregistrée pour ce dossier.")

    autorisation = await alertes_repo.create_autorisation(
        db, dossier_id=dossier_id, dirigeant_id=current_user.id,
        decision=body.decision, justification=body.justification,
    )
    if body.decision == "REFUSE":
        dossier.statut, dossier.is_bloque = "bloque", True
        db.add(dossier)
        await db.commit()

    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db, action=f"wrk09.{body.decision.lower()}", user_id=current_user.id, user_role=current_user.role,
        entity_type="dossier", entity_id=dossier_id, ip=ip,
        detail={"decision": body.decision, "justification": body.justification, "autorisation_id": autorisation.id},
    )
    return AutorisationOut(
        id=autorisation.id, dossier_id=autorisation.dossier_id, dirigeant_id=autorisation.dirigeant_id,
        decision=autorisation.decision, justification=autorisation.justification,
        created_at=autorisation.created_at.isoformat() if autorisation.created_at else datetime.utcnow().isoformat(),
    )
