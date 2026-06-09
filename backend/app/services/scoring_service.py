"""
Service de scoring LBC/FT/FP — Notaire.

Architecture deux niveaux (CDC Module 2) :
  Niveau 1 : Score de base /20 — 10 axes × {0, 1, 2}
  Niveau 2 : 6 triggers absolutoires — forcent ELEVE indépendamment du score

Seuils VERROUILLÉS dans le code source (non modifiables par aucun rôle) :
  0-7  → FAIBLE
  8-13 → MOYEN
  14-20→ ELEVE

T2 espèces : 15 000 000 FCFA (Art. 72, Ordonnance 2023-875).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from app.core.config import settings


# Seuils verrouillés — NE PAS RENDRE PARAMÉTRABLES
_SEUILS = {"FAIBLE": (0, 7), "MOYEN": (8, 13), "ELEVE": (14, 20)}


def _classify(score: int) -> str:
    for label, (lo, hi) in _SEUILS.items():
        if lo <= score <= hi:
            return label
    return "ELEVE"


@dataclass
class ScoreResult:
    score: int
    classification: str
    triggers_actifs: dict[str, bool] = field(default_factory=dict)
    force_par_trigger: bool = False
    trigger_principal: str | None = None
    axes: dict[str, int] = field(default_factory=dict)


def calculate(kyc_data: dict, ponderations: dict | None = None) -> ScoreResult:
    """
    kyc_data : dict avec les champs KYC PP ou PM.
    ponderations : dict axe->ponderation fourni par l'admin (défaut 1.0 pour chaque axe).
    """
    w = ponderations or {str(i): 1 for i in range(1, 11)}

    axes = _score_axes(kyc_data)
    score_base = sum(int(axes.get(str(i), 0)) * float(w.get(str(i), 1)) for i in range(1, 11))
    score_base = min(20, int(score_base))

    triggers = _detect_triggers(kyc_data)
    triggers_actifs = {k: v for k, v in triggers.items() if v}
    trigger_principal = next(iter(triggers_actifs), None)

    if triggers_actifs:
        return ScoreResult(
            score=score_base,
            classification="ELEVE",
            triggers_actifs=triggers_actifs,
            force_par_trigger=True,
            trigger_principal=trigger_principal,
            axes=axes,
        )

    return ScoreResult(
        score=score_base,
        classification=_classify(score_base),
        triggers_actifs={},
        force_par_trigger=False,
        axes=axes,
    )


def _score_axes(d: dict) -> dict[str, int]:
    return {
        "1": _axe1_type_client(d),
        "2": _axe2_nationalite(d),
        "3": _axe3_type_operation(d),
        "4": _axe4_montant(d),
        "5": _axe5_mode_paiement(d),
        "6": _axe6_complexite(d),
        "7": _axe7_ppe(d),
        "8": _axe8_coherence_doc(d),
        "9": _axe9_secteur(d),
        "10": _axe10_intermediaires(d),
    }


def _detect_triggers(d: dict) -> dict[str, bool]:
    return {
        "T1": bool(d.get("est_ppe") or d.get("ppe_detectee")),
        "T2": _is_especes_sup_15m(d),
        "T3": bool(d.get("sur_liste_sanctions")),
        "T4": _is_pays_gafi(d),
        "T5": bool(d.get("refus_documents")),
        "T6": bool(d.get("be_non_identifiable")),
    }


def _is_especes_sup_15m(d: dict) -> bool:
    mode = d.get("mode_paiement", "")
    montant = float(d.get("montant_transaction", 0) or 0)
    return mode == "especes" and montant > settings.ESPECES_THRESHOLD_FCFA


def _is_pays_gafi(d: dict) -> bool:
    pays_liste_noire = d.get("pays_liste_noire_gafi", False)
    pays_liste_grise = d.get("pays_liste_grise_gafi", False)
    return bool(pays_liste_noire or pays_liste_grise)


# ── Axes ─────────────────────────────────────────────────────────────────────

def _axe1_type_client(d: dict) -> int:
    tc = d.get("type_client_scoring", "")
    if tc in ("holding_offshore", "structure_atypique"):
        return 2
    if tc in ("sarl", "sa", "societe_actionariat_complexe"):
        return 1 if tc != "societe_actionariat_complexe" else 2
    return 0


def _axe2_nationalite(d: dict) -> int:
    pays = d.get("pays_residence", "").upper()
    if d.get("pays_liste_noire_gafi") or d.get("pays_liste_grise_gafi"):
        return 2
    if pays in ("FR", "BE", "CH", "DE", "US", "GB"):
        return 1
    if pays in ("CI", "BJ", "BF", "ML", "NE", "SN", "TG", "GW"):
        return 0
    return 1


def _axe3_type_operation(d: dict) -> int:
    op = d.get("type_operation", "")
    if op in ("fiducicommis",):
        return 2
    if op in ("manipulation_fonds",):
        return 2
    if op in ("succession", "donation", "constitution_societe"):
        return 1
    return 0


def _axe4_montant(d: dict) -> int:
    montant = float(d.get("montant_transaction", 0) or 0)
    if montant > 15_000_000:
        return 2
    if montant >= 5_000_000:
        return 1
    return 0


def _axe5_mode_paiement(d: dict) -> int:
    mode = d.get("mode_paiement", "")
    if mode in ("especes", "paiement_tiers"):
        return 2
    if mode in ("cheque", "mix"):
        return 1
    return 0


def _axe6_complexite(d: dict) -> int:
    if d.get("montage_complexe"):
        return 2
    nb_parties = int(d.get("nb_parties", 1) or 1)
    if nb_parties >= 3:
        return 1
    return 0


def _axe7_ppe(d: dict) -> int:
    return 2 if (d.get("est_ppe") or d.get("ppe_detectee")) else 0


def _axe8_coherence_doc(d: dict) -> int:
    coherence = d.get("coherence_documents", "ok")
    if coherence == "incoherent":
        return 2
    if coherence == "doute":
        return 1
    return 0


def _axe9_secteur(d: dict) -> int:
    secteur = d.get("secteur_activite_scoring", "")
    if secteur in ("crypto", "jeux", "paris"):
        return 2
    if secteur in ("commerce", "cash", "immobilier_complexe"):
        return 1
    return 0


def _axe10_intermediaires(d: dict) -> int:
    intermediaires = d.get("intermediaires_scoring", "aucun")
    if intermediaires == "non_clair":
        return 2
    if intermediaires == "identifie":
        return 1
    return 0
