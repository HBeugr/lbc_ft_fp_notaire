"""Endpoints matrice de risque — CDC Module 2.

  GET  /api/dossiers/{id}/scoring/prefill   → valeurs d'axes pré-dérivées (auto)
  POST /api/dossiers/{id}/scoring/calculate → calcule, persiste l'évaluation + cache + audit
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.dossier import Dossier, KycActionnaire, EvaluationRisque
from app.models.user import User
from app.repositories import dossier_repo, audit_repo
from app.schemas.kyc import (
    ScoringPrefillOut, ScoringAxisPrefill,
    ScoreCalcIn, ScoreResultOut, ScoreAxisOut,
    SimulateurIn, SimResultOut,
)
from app.services import scoring_service

router = APIRouter(prefix="/dossiers", tags=["scoring"])

# Routeur stateless du simulateur (hors contexte dossier) — monté sur /api/scoring
sim_router = APIRouter(prefix="/scoring", tags=["scoring"])


@sim_router.post("/simuler", response_model=SimResultOut)
async def simuler_scoring(
    body: SimulateurIn,
    current_user: User = Depends(get_current_user),
) -> SimResultOut:
    """Simule un scoring complet à partir des codes du formulaire (aucun dossier).

    Outil pédagogique de l'onglet « Simulateur de Risque » : réutilise la logique
    de `scoring_service.calculate()` (seuils verrouillés + triggers absolutoires).
    """
    res = scoring_service.simulate(**body.model_dump())
    return SimResultOut(**res)


def _can_access(user: User, dossier: Dossier) -> bool:
    return user.is_supervisor or dossier.assigned_to == user.id


async def _get_dossier_or_404(db: AsyncSession, dossier_id: str, user: User) -> Dossier:
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not _can_access(user, dossier):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    return dossier


async def _load_kyc(db: AsyncSession, dossier: Dossier):
    """Retourne (kyc_pp, kyc_pm, actionnaires_count)."""
    kyc_pp = kyc_pm = None
    actionnaires_count = 0
    if dossier.type_client == "PP":
        kyc_pp = await dossier_repo.get_kyc_pp(db, dossier.id)
    else:
        kyc_pm = await dossier_repo.get_kyc_pm(db, dossier.id)
        if kyc_pm:
            res = await db.execute(
                select(func.count(KycActionnaire.id)).where(KycActionnaire.kyc_pm_id == kyc_pm.id)
            )
            actionnaires_count = res.scalar_one()
    return kyc_pp, kyc_pm, actionnaires_count


@router.get("/{dossier_id}/scoring/prefill", response_model=ScoringPrefillOut)
async def get_scoring_prefill(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoringPrefillOut:
    dossier = await _get_dossier_or_404(db, dossier_id, current_user)
    kyc_pp, kyc_pm, count = await _load_kyc(db, dossier)
    pf = scoring_service.prefill(dossier, kyc_pp, kyc_pm, actionnaires_count=count)
    return ScoringPrefillOut(axes={k: ScoringAxisPrefill(**v) for k, v in pf.items()})


@router.post("/{dossier_id}/scoring/calculate", response_model=ScoreResultOut)
async def calculate_scoring(
    dossier_id: str,
    body: ScoreCalcIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoreResultOut:
    dossier = await _get_dossier_or_404(db, dossier_id, current_user)
    kyc_pp, kyc_pm, _ = await _load_kyc(db, dossier)
    kyc = kyc_pp or kyc_pm

    # Persiste les données opération si fournies (alimentent axes 4/5 et T2)
    op_updates = {}
    if body.montant_transaction is not None:
        op_updates["montant_transaction"] = body.montant_transaction
    if body.mode_paiement is not None:
        op_updates["mode_paiement"] = body.mode_paiement
    if body.nb_parties is not None:
        op_updates["nb_parties"] = body.nb_parties
    if op_updates:
        await db.execute(sa_update(Dossier).where(Dossier.id == dossier_id).values(**op_updates))
        for k, v in op_updates.items():
            setattr(dossier, k, v)

    est_ppe = bool(getattr(kyc, "est_ppe", False) or getattr(kyc, "ppe_detectee", False))
    result = scoring_service.calculate(
        body.axes,
        montant_transaction=float(dossier.montant_transaction or 0),
        mode_paiement=dossier.mode_paiement or "",
        est_ppe=est_ppe,
        sur_liste_sanctions=body.sur_liste_sanctions,
        pays_liste_noire_gafi=body.pays_liste_noire_gafi,
        pays_liste_grise_gafi=body.pays_liste_grise_gafi,
        refus_documents=body.refus_documents,
        be_non_identifiable=body.be_non_identifiable,
    )

    overrides_payload = [
        {**o.model_dump(), "user_id": current_user.id} for o in body.overrides
    ]
    flags = dict(
        sur_liste_sanctions=body.sur_liste_sanctions,
        pays_liste_noire_gafi=body.pays_liste_noire_gafi,
        pays_liste_grise_gafi=body.pays_liste_grise_gafi,
        refus_documents=body.refus_documents,
        be_non_identifiable=body.be_non_identifiable,
    )
    await _persist_evaluation(db, dossier, result, flags, overrides_payload, current_user.id)

    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="scoring.calculated",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dossier",
        entity_id=dossier_id,
        ip=ip,
        detail={
            "score": result.score,
            "classification": result.classification,
            "trigger": result.trigger_principal,
            "overrides": [o["axe"] for o in overrides_payload],
        },
    )

    return ScoreResultOut(
        total=result.score,
        niveau=result.classification,
        axes=[
            ScoreAxisOut(code=c, label=scoring_service.AXIS_LABELS[c], score=result.axes.get(c, 0))
            for c in scoring_service.AXIS_CODES
        ],
        triggers_actifs=list(result.triggers_actifs.keys()),
        force_par_trigger=result.force_par_trigger,
        trigger_principal=result.trigger_principal,
    )


async def _persist_evaluation(db, dossier, result, flags: dict, overrides_payload, user_id) -> None:
    """Upsert evaluations_risque + met à jour le cache dénormalisé du dossier."""
    existing = await db.execute(
        select(EvaluationRisque).where(EvaluationRisque.dossier_id == dossier.id)
    )
    ev = existing.scalar_one_or_none()
    axes = result.axes
    values = dict(
        axe_type_client=axes.get("type_client", 0),
        axe_pays_geographie=axes.get("pays_geographie", 0),
        axe_type_operation=axes.get("type_operation", 0),
        axe_montant=axes.get("montant", 0),
        axe_mode_paiement=axes.get("mode_paiement", 0),
        axe_complexite=axes.get("complexite", 0),
        axe_ppe=axes.get("ppe", 0),
        axe_coherence_doc=axes.get("coherence_doc", 0),
        axe_secteur=axes.get("secteur", 0),
        axe_intermediaires=axes.get("intermediaires", 0),
        score_total=result.score,
        classification=result.classification,
        trigger_principal=result.trigger_principal,
        triggers_actifs=result.triggers_actifs,
        force_par_trigger=result.force_par_trigger,
        sur_liste_sanctions=flags["sur_liste_sanctions"],
        pays_liste_noire_gafi=flags["pays_liste_noire_gafi"],
        pays_liste_grise_gafi=flags["pays_liste_grise_gafi"],
        refus_documents=flags["refus_documents"],
        be_non_identifiable=flags["be_non_identifiable"],
        overrides=overrides_payload,
        evaluated_by=user_id,
    )
    if ev:
        for k, v in values.items():
            setattr(ev, k, v)
    else:
        db.add(EvaluationRisque(dossier_id=dossier.id, **values))

    await db.execute(
        sa_update(Dossier).where(Dossier.id == dossier.id).values(
            score_base=result.score,
            classification=result.classification,
            trigger_actif=result.trigger_principal,
            force_par_trigger=result.force_par_trigger,
        )
    )
    await db.commit()


async def recompute_cache(db: AsyncSession, dossier: Dossier, user_id: str):
    """Recalcule un score provisoire depuis le prefill au moment d'un upsert KYC.

    Rafraîchit les axes auto ; préserve l'axe manuel (cohérence doc) et les flags
    triggers d'une évaluation existante. Persiste évaluation + cache dossier.
    Retourne le ScoreResult.
    """
    kyc_pp, kyc_pm, count = await _load_kyc(db, dossier)
    kyc = kyc_pp or kyc_pm
    pf = scoring_service.prefill(dossier, kyc_pp, kyc_pm, actionnaires_count=count)
    axes = scoring_service.axes_from_prefill(pf)

    existing = (
        await db.execute(select(EvaluationRisque).where(EvaluationRisque.dossier_id == dossier.id))
    ).scalar_one_or_none()
    flags = dict(
        sur_liste_sanctions=False, pays_liste_noire_gafi=False, pays_liste_grise_gafi=False,
        refus_documents=False, be_non_identifiable=False,
    )
    overrides_payload = []
    if existing:
        axes["coherence_doc"] = existing.axe_coherence_doc  # axe manuel préservé
        flags = dict(
            sur_liste_sanctions=existing.sur_liste_sanctions,
            pays_liste_noire_gafi=existing.pays_liste_noire_gafi,
            pays_liste_grise_gafi=existing.pays_liste_grise_gafi,
            refus_documents=existing.refus_documents,
            be_non_identifiable=existing.be_non_identifiable,
        )
        overrides_payload = existing.overrides or []

    est_ppe = bool(getattr(kyc, "est_ppe", False) or getattr(kyc, "ppe_detectee", False))
    result = scoring_service.calculate(
        axes,
        montant_transaction=float(dossier.montant_transaction or 0),
        mode_paiement=dossier.mode_paiement or "",
        est_ppe=est_ppe,
        **flags,
    )
    await _persist_evaluation(db, dossier, result, flags, overrides_payload, user_id)
    return result
