from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.dossier import Dossier, KycBE, KycPPE, KycActionnaire
from app.repositories import dossier_repo, audit_repo
from app.schemas.kyc import (
    KycPPUpsert, KycPPOut,
    KycPMUpsert, KycPMOut,
    KycBECreate, KycBEOut,
    KycActCreate, KycActOut,
    KycPPECreate, KycPPEOut,
    ScoreOut,
)
from app.services import scoring_service

router = APIRouter(prefix="/dossiers", tags=["kyc"])


def _can_access(user: User, dossier: Dossier) -> bool:
    if user.is_supervisor:
        return True
    return dossier.assigned_to == user.id


async def _get_dossier_or_404(db: AsyncSession, dossier_id: str, user: User) -> Dossier:
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not _can_access(user, dossier):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    return dossier


# ── KYC PP ────────────────────────────────────────────────────────────────────

@router.get("/{dossier_id}/kyc/pp", response_model=KycPPOut)
async def get_kyc_pp(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPPOut:
    dossier = await _get_dossier_or_404(db, dossier_id, current_user)
    kyc = await dossier_repo.get_kyc_pp(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC PP non trouvé.")
    be_result = await db.execute(select(KycBE).where(KycBE.kyc_pp_id == kyc.id))
    ppe_result = await db.execute(select(KycPPE).where(KycPPE.kyc_pp_id == kyc.id))
    out = KycPPOut.model_validate(kyc)
    out.beneficiaires_effectifs = [KycBEOut.model_validate(b) for b in be_result.scalars().all()]
    out.ppe_declarations = [KycPPEOut.model_validate(p) for p in ppe_result.scalars().all()]
    return out


@router.put("/{dossier_id}/kyc/pp", response_model=KycPPOut)
async def upsert_kyc_pp(
    dossier_id: str,
    body: KycPPUpsert,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPPOut:
    dossier = await _get_dossier_or_404(db, dossier_id, current_user)
    data = body.model_dump()
    # Sérialise les sous-objets Pydantic en dict
    for field in ("mandataire", "operations_cochees", "origine_fonds"):
        if data.get(field) is not None and not isinstance(data[field], dict):
            data[field] = data[field].model_dump() if hasattr(data[field], "model_dump") else dict(data[field])
    kyc = await dossier_repo.upsert_kyc_pp(db, dossier_id, **data)
    # Trigger scoring
    score_data = _build_score_data(dossier, data)
    result = scoring_service.calculate(score_data)
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(Dossier).where(Dossier.id == dossier_id).values(
            score_base=result.score,
            classification=result.classification,
            trigger_actif=result.trigger_principal,
            force_par_trigger=result.force_par_trigger,
        )
    )
    await db.commit()
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="kyc_pp.upserted",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dossier",
        entity_id=dossier_id,
        ip=ip,
        detail={"classification": result.classification, "score": result.score},
    )
    be_result = await db.execute(select(KycBE).where(KycBE.kyc_pp_id == kyc.id))
    ppe_result = await db.execute(select(KycPPE).where(KycPPE.kyc_pp_id == kyc.id))
    out = KycPPOut.model_validate(kyc)
    out.beneficiaires_effectifs = [KycBEOut.model_validate(b) for b in be_result.scalars().all()]
    out.ppe_declarations = [KycPPEOut.model_validate(p) for p in ppe_result.scalars().all()]
    return out


@router.get("/{dossier_id}/kyc/pp/score", response_model=ScoreOut)
async def recalculate_score_pp(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoreOut:
    dossier = await _get_dossier_or_404(db, dossier_id, current_user)
    kyc = await dossier_repo.get_kyc_pp(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC PP non trouvé.")
    score_data = _build_score_data(dossier, kyc.__dict__)
    result = scoring_service.calculate(score_data)
    return ScoreOut(
        score=result.score,
        classification=result.classification,
        triggers_actifs=result.triggers_actifs,
        force_par_trigger=result.force_par_trigger,
        trigger_principal=result.trigger_principal,
        axes=result.axes,
    )


# ── Bénéficiaires effectifs PP ─────────────────────────────────────────────────

@router.post("/{dossier_id}/kyc/pp/be", response_model=KycBEOut, status_code=status.HTTP_201_CREATED)
async def add_be_pp(
    dossier_id: str,
    body: KycBECreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycBEOut:
    await _get_dossier_or_404(db, dossier_id, current_user)
    kyc = await dossier_repo.get_kyc_pp(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Créer le KYC PP d'abord.")
    be = KycBE(kyc_pp_id=kyc.id, **body.model_dump())
    db.add(be)
    await db.commit()
    await db.refresh(be)
    return KycBEOut.model_validate(be)


@router.delete("/{dossier_id}/kyc/pp/be/{be_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_be_pp(
    dossier_id: str,
    be_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_dossier_or_404(db, dossier_id, current_user)
    await db.execute(sa_delete(KycBE).where(KycBE.id == be_id))
    await db.commit()


# ── PPE PP ────────────────────────────────────────────────────────────────────

@router.post("/{dossier_id}/kyc/pp/ppe", response_model=KycPPEOut, status_code=status.HTTP_201_CREATED)
async def add_ppe_pp(
    dossier_id: str,
    body: KycPPECreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPPEOut:
    await _get_dossier_or_404(db, dossier_id, current_user)
    kyc = await dossier_repo.get_kyc_pp(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Créer le KYC PP d'abord.")
    ppe = KycPPE(kyc_pp_id=kyc.id, **body.model_dump())
    db.add(ppe)
    await db.commit()
    await db.refresh(ppe)
    return KycPPEOut.model_validate(ppe)


# ── KYC PM ────────────────────────────────────────────────────────────────────

@router.get("/{dossier_id}/kyc/pm", response_model=KycPMOut)
async def get_kyc_pm(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPMOut:
    await _get_dossier_or_404(db, dossier_id, current_user)
    kyc = await dossier_repo.get_kyc_pm(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC PM non trouvé.")
    be_result = await db.execute(select(KycBE).where(KycBE.kyc_pm_id == kyc.id))
    act_result = await db.execute(select(KycActionnaire).where(KycActionnaire.kyc_pm_id == kyc.id).order_by(KycActionnaire.ordre))
    ppe_result = await db.execute(select(KycPPE).where(KycPPE.kyc_pm_id == kyc.id))
    out = KycPMOut.model_validate(kyc)
    out.beneficiaires_effectifs = [KycBEOut.model_validate(b) for b in be_result.scalars().all()]
    out.actionnaires = [KycActOut.model_validate(a) for a in act_result.scalars().all()]
    out.ppe_declarations = [KycPPEOut.model_validate(p) for p in ppe_result.scalars().all()]
    return out


@router.put("/{dossier_id}/kyc/pm", response_model=KycPMOut)
async def upsert_kyc_pm(
    dossier_id: str,
    body: KycPMUpsert,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPMOut:
    dossier = await _get_dossier_or_404(db, dossier_id, current_user)
    data = body.model_dump()
    for field in ("mandataire", "operations_cochees", "origine_fonds", "infos_pm"):
        if data.get(field) is not None and not isinstance(data[field], dict):
            data[field] = data[field].model_dump() if hasattr(data[field], "model_dump") else dict(data[field])
    kyc = await dossier_repo.upsert_kyc_pm(db, dossier_id, **data)
    score_data = _build_score_data(dossier, data)
    result = scoring_service.calculate(score_data)
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(Dossier).where(Dossier.id == dossier_id).values(
            score_base=result.score,
            classification=result.classification,
            trigger_actif=result.trigger_principal,
            force_par_trigger=result.force_par_trigger,
        )
    )
    await db.commit()
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="kyc_pm.upserted",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dossier",
        entity_id=dossier_id,
        ip=ip,
        detail={"classification": result.classification, "score": result.score},
    )
    be_result = await db.execute(select(KycBE).where(KycBE.kyc_pm_id == kyc.id))
    act_result = await db.execute(select(KycActionnaire).where(KycActionnaire.kyc_pm_id == kyc.id).order_by(KycActionnaire.ordre))
    ppe_result = await db.execute(select(KycPPE).where(KycPPE.kyc_pm_id == kyc.id))
    out = KycPMOut.model_validate(kyc)
    out.beneficiaires_effectifs = [KycBEOut.model_validate(b) for b in be_result.scalars().all()]
    out.actionnaires = [KycActOut.model_validate(a) for a in act_result.scalars().all()]
    out.ppe_declarations = [KycPPEOut.model_validate(p) for p in ppe_result.scalars().all()]
    return out


@router.post("/{dossier_id}/kyc/pm/be", response_model=KycBEOut, status_code=status.HTTP_201_CREATED)
async def add_be_pm(
    dossier_id: str,
    body: KycBECreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycBEOut:
    await _get_dossier_or_404(db, dossier_id, current_user)
    kyc = await dossier_repo.get_kyc_pm(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Créer le KYC PM d'abord.")
    be = KycBE(kyc_pm_id=kyc.id, **body.model_dump())
    db.add(be)
    await db.commit()
    await db.refresh(be)
    return KycBEOut.model_validate(be)


@router.delete("/{dossier_id}/kyc/pm/be/{be_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_be_pm(
    dossier_id: str,
    be_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_dossier_or_404(db, dossier_id, current_user)
    await db.execute(sa_delete(KycBE).where(KycBE.id == be_id))
    await db.commit()


@router.post("/{dossier_id}/kyc/pm/actionnaires", response_model=KycActOut, status_code=status.HTTP_201_CREATED)
async def add_actionnaire(
    dossier_id: str,
    body: KycActCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycActOut:
    await _get_dossier_or_404(db, dossier_id, current_user)
    kyc = await dossier_repo.get_kyc_pm(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Créer le KYC PM d'abord.")
    act = KycActionnaire(kyc_pm_id=kyc.id, **body.model_dump())
    db.add(act)
    await db.commit()
    await db.refresh(act)
    return KycActOut.model_validate(act)


@router.delete("/{dossier_id}/kyc/pm/actionnaires/{act_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_actionnaire(
    dossier_id: str,
    act_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_dossier_or_404(db, dossier_id, current_user)
    await db.execute(sa_delete(KycActionnaire).where(KycActionnaire.id == act_id))
    await db.commit()


@router.post("/{dossier_id}/kyc/pm/ppe", response_model=KycPPEOut, status_code=status.HTTP_201_CREATED)
async def add_ppe_pm(
    dossier_id: str,
    body: KycPPECreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPPEOut:
    await _get_dossier_or_404(db, dossier_id, current_user)
    kyc = await dossier_repo.get_kyc_pm(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Créer le KYC PM d'abord.")
    ppe = KycPPE(kyc_pm_id=kyc.id, **body.model_dump())
    db.add(ppe)
    await db.commit()
    await db.refresh(ppe)
    return KycPPEOut.model_validate(ppe)


# ── Helper scoring ─────────────────────────────────────────────────────────────

def _build_score_data(dossier: Dossier, kyc_data: dict) -> dict:
    return {
        **kyc_data,
        "type_operation": dossier.type_operation,
        "type_client": dossier.type_client,
    }
