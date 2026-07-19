"""Conséquences automatiques d'un calcul de score — CDC Module 3.

Le CDC (Module 3, « Détection automatique ») impose qu'un trigger absolutoire ne
se contente pas de reclasser le dossier : il doit **produire une alerte**, faute
de quoi la détection reste invisible du Responsable conformité, du registre des
alertes (CDC §5.1) et d'un éventuel contrôle CENTIF. Le T3 va plus loin et
emporte le blocage immédiat du dossier (Art. 89 — gel des avoirs).

Ces conséquences sont regroupées ici pour être appliquées de façon identique par
tous les chemins qui recalculent un score (écran de scoring, enregistrement du
KYC, réévaluation périodique) : c'est ce qui garantit qu'aucune porte d'entrée
ne produit un score sans ses effets réglementaires.
"""
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dossier import Dossier
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

_TRIGGER_MOTIFS = {
    "T1": "Statut PPE identifié — vigilance renforcée obligatoire (Art. 29).",
    "T2": "Transaction en espèces au-delà du seuil légal — déclaration CENTIF possible (Art. 72).",
    "T3": "Client figurant sur une liste de sanctions — blocage immédiat (Art. 89).",
    "T4": "Pays en liste noire ou grise GAFI — vigilance renforcée (Art. 30).",
    "T5": "Refus ou impossibilité de fournir les documents obligatoires — DOS possible (Art. 25).",
    "T6": "Bénéficiaire effectif non identifiable — relation d'affaires non autorisée (Art. 17).",
}


async def generate_alertes(db: AsyncSession, dossier_id: str, score_result: ScoreResult) -> None:
    """Crée les alertes correspondant aux triggers actifs et au score.

    Anti-doublon : le scoring est rejoué à chaque enregistrement du KYC. Sans
    garde-fou, un même dossier accumulerait une alerte identique par
    sauvegarde et le registre des alertes deviendrait inexploitable.
    """
    for trigger_code, actif in score_result.triggers_actifs.items():
        if not actif:
            continue
        type_alerte = _TRIGGER_LABELS.get(trigger_code, "AUTRE")
        if await alertes_repo.exists_active(db, dossier_id=dossier_id, type_alerte=type_alerte):
            continue
        await alertes_repo.create(
            db,
            dossier_id=dossier_id,
            type_alerte=type_alerte,
            niveau="ELEVE",
            statut="ouverte",
            description=(
                f"Trigger absolutoire {trigger_code} déclenché. "
                f"{_TRIGGER_MOTIFS.get(trigger_code, '')}"
            ).strip(),
        )

    # Hors trigger, le CDC (Module 3) n'alerte qu'à partir du niveau MOYEN :
    # un dossier FAIBLE relève de la « validation simple — aucune alerte générée ».
    if not score_result.triggers_actifs and score_result.score >= 8:
        niveau = "ELEVE" if score_result.score >= 14 else "MOYEN"
        axe_max = max(score_result.axes, key=lambda k: score_result.axes[k], default=None)
        if axe_max and score_result.axes[axe_max] == 2:
            if await alertes_repo.exists_active(db, dossier_id=dossier_id, type_alerte="AUTRE"):
                return
            await alertes_repo.create(
                db,
                dossier_id=dossier_id,
                type_alerte="AUTRE",
                niveau=niveau,
                statut="ouverte",
                description=f"Score {score_result.score}/20 — axe {axe_max} à risque élevé.",
            )


async def appliquer_consequences(
    db: AsyncSession, dossier: Dossier, score_result: ScoreResult
) -> None:
    """Applique les effets réglementaires d'un score : alertes puis blocage T3.

    Séparer le calcul (`scoring_service`) de ses conséquences permet de tester
    le barème sans effets de bord, tout en garantissant qu'en production un
    score n'est jamais produit sans les mesures que le CDC y attache.
    """
    await generate_alertes(db, dossier.id, score_result)

    # T3 — « Classification forcée ÉLEVÉ — Blocage immédiat » (CDC §2.3, Art. 89).
    # Classer ÉLEVÉ sans suspendre l'opération laisserait le cabinet instrumenter
    # un acte au profit d'une personne sous sanctions financières ciblées.
    if score_result.triggers_actifs.get("T3") and dossier.statut != "bloque":
        await db.execute(
            sa_update(Dossier).where(Dossier.id == dossier.id).values(
                statut="bloque", is_bloque=True
            )
        )
        dossier.statut, dossier.is_bloque = "bloque", True
        await db.commit()
