from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.dossier import Dossier
from app.models.user import User
from app.schemas.kyc import ScoreOut
from app.services.scoring_service import calculate

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.get("/dossiers/{dossier_id}", response_model=ScoreOut)
async def recalculate_score(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoreOut:
    result = await db.execute(
        select(Dossier)
        .options(selectinload(Dossier.kyc_pp), selectinload(Dossier.kyc_pm))
        .where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not current_user.is_supervisor and dossier.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")

    # Build minimal score_data from dossier fields
    score_data: dict = {
        "est_ppe": False,
        "type_transaction": dossier.type_operation or "",
        "pays_residence": "",
        "montant_especes": 0,
        "a_refuse_documents": False,
        "beneficiaire_non_identifiable": False,
        "sur_liste_sanctions": False,
        "pays_gafi_risque": False,
    }

    if dossier.kyc_pp:
        kyc = dossier.kyc_pp
        score_data["est_ppe"] = kyc.est_ppe or False
        score_data["pays_residence"] = kyc.pays_residence or ""
        score_data["a_refuse_documents"] = kyc.a_refuse_documents or False
        score_data["montant_operation"] = kyc.montant_operation or 0
    elif dossier.kyc_pm:
        kyc = dossier.kyc_pm
        score_data["pays_siege"] = kyc.pays_siege or ""

    result = calculate(score_data)
    return ScoreOut(
        score=result.score,
        classification=result.classification,
        trigger_actif=result.trigger_actif,
        force_par_trigger=result.force_par_trigger,
        details=result.details,
    )
