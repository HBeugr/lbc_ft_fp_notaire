"""
KYC Screening — pré-vérification sanctions en temps réel (logique assujetti).

Accessible à tout utilisateur authentifié. Retourne un feedback UI sans audit ni
activation T3 : le criblage formel (T3 + audit) est déclenché au save réel du KYC.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories import sanctions_repo
from app.services import sanctions_service

router = APIRouter(prefix="/kyc/screening", tags=["kyc-screening"])


@router.post("/pre-check")
async def pre_check_sanctions(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Body: { nom, prenoms, date_naissance?, lieu_naissance?, nationalite? }

    Response: { level: "blocked"|"warning"|"clear"|"no_lists", score, liste, reason }
    Le nom exact de la personne sanctionnée n'est pas exposé (anti-scan des listes).
    """
    nom = f"{body.get('nom', '')} {body.get('prenoms', '')}".strip()
    if len(nom) < 3:
        return {"level": "clear", "score": 0, "liste": None, "reason": None}

    listes = await sanctions_repo.get_active_with_entries(db)
    result = sanctions_service.pre_check(
        nom=nom,
        date_naissance=body.get("date_naissance") or None,
        lieu_naissance=body.get("lieu_naissance") or None,
        nationalite=body.get("nationalite") or None,
        listes=listes,
    )
    return {
        "level": result["level"],
        "score": result["score"],
        "liste": result["liste"],
        "reason": result["reason"],
    }
