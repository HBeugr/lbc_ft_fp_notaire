"""Détection automatique des alertes après calcul du score."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import alertes_repo
from app.services.scoring_service import ScoreResult

_TRIGGER_LABELS = {
    "T1": "T1_PPE",
    "T2": "T2_ESPECES",
    "T3": "T3_SANCTIONS",
    "T4": "T4_GAFI",
    "T5": "T5_REFUS_DOC",
    "T6": "T6_BE_NON_IDENTIFIABLE",
}


async def generate_alertes(db: AsyncSession, dossier_id: str, score_result: ScoreResult) -> None:
    for trigger_code, actif in score_result.triggers_actifs.items():
        if not actif:
            continue
        type_alerte = _TRIGGER_LABELS.get(trigger_code, "AUTRE")
        await alertes_repo.create(
            db,
            dossier_id=dossier_id,
            type_alerte=type_alerte,
            niveau="ELEVE",
            statut="ouverte",
            description=f"Trigger absolutoire {trigger_code} déclenché.",
        )

    if not score_result.triggers_actifs and score_result.score >= 8:
        niveau = "ELEVE" if score_result.score >= 14 else "MOYEN"
        axe_max = max(score_result.axes, key=lambda k: score_result.axes[k], default=None)
        if axe_max and score_result.axes[axe_max] == 2:
            await alertes_repo.create(
                db,
                dossier_id=dossier_id,
                type_alerte="AUTRE",
                niveau=niveau,
                statut="ouverte",
                description=f"Score {score_result.score}/20 — axe {axe_max} à risque élevé.",
            )
