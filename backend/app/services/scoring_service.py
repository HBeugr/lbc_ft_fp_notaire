"""
Service de scoring LBC/FT/FP — Notaire (CDC v4, Module 2).

Matrice hybride :
  - 10 axes canoniques × {0, 1, 2} → score /20.
  - 6 triggers absolutoires (T1–T6) forcent ELEVE indépendamment du score.
  - Certains axes sont pré-dérivés des données KYC/dossier (`prefill`), les autres
    sont saisis par l'agent ; toute baisse d'un axe auto exige une justification (audit).

Seuils VERROUILLÉS dans le code (non modifiables par aucun rôle) :
  0-7  → FAIBLE | 8-13 → MOYEN | 14-20 → ELEVE

T2 espèces : 15 000 000 FCFA (Art. 72, Ordonnance 2023-875).
"""
from __future__ import annotations
from dataclasses import dataclass, field

from app.core.config import settings


# Seuils verrouillés — NE PAS RENDRE PARAMÉTRABLES
_SEUILS = {"FAIBLE": (0, 7), "MOYEN": (8, 13), "ELEVE": (14, 20)}

# 10 axes canoniques (ordre CDC v4 §Module 2). code → libellé + auto-dérivable
AXES: list[dict] = [
    {"code": "type_client",     "label": "Type de client",          "auto": True},
    {"code": "pays_geographie", "label": "Pays / Géographie",       "auto": True},
    {"code": "type_operation",  "label": "Nature de l'opération",    "auto": True},
    {"code": "montant",         "label": "Montant de la transaction", "auto": True},
    {"code": "mode_paiement",   "label": "Mode de paiement",         "auto": True},
    {"code": "complexite",      "label": "Complexité juridique",     "auto": True},
    {"code": "ppe",             "label": "Personne Politiquement Exposée", "auto": True},
    {"code": "coherence_doc",   "label": "Cohérence documentaire",   "auto": False},
    {"code": "secteur",         "label": "Secteur d'activité",       "auto": True},
    {"code": "intermediaires",  "label": "Intermédiaires",           "auto": True},
]
AXIS_CODES = [a["code"] for a in AXES]
AXIS_LABELS = {a["code"]: a["label"] for a in AXES}


def _classify(score: int) -> str:
    for label, (lo, hi) in _SEUILS.items():
        if lo <= score <= hi:
            return label
    return "ELEVE"


@dataclass
class ScoreResult:
    score: int
    classification: str
    axes: dict[str, int] = field(default_factory=dict)
    triggers_actifs: dict[str, bool] = field(default_factory=dict)
    force_par_trigger: bool = False
    trigger_principal: str | None = None


# ── Calcul ──────────────────────────────────────────────────────────────────────

def calculate(
    axes: dict[str, int],
    *,
    montant_transaction: float = 0,
    mode_paiement: str = "",
    est_ppe: bool = False,
    sur_liste_sanctions: bool = False,
    pays_liste_noire_gafi: bool = False,
    pays_liste_grise_gafi: bool = False,
    refus_documents: bool = False,
    be_non_identifiable: bool = False,
    ponderations: dict[str, float] | None = None,
) -> ScoreResult:
    """Calcule le score à partir des valeurs d'axes (déjà résolues) et des triggers.

    `axes` : {code: 0|1|2} pour les 10 codes de AXIS_CODES (valeurs manquantes = 0).
    """
    w = ponderations or {code: 1.0 for code in AXIS_CODES}
    clean = {code: max(0, min(2, int(axes.get(code, 0) or 0))) for code in AXIS_CODES}
    score = sum(clean[code] * float(w.get(code, 1.0)) for code in AXIS_CODES)
    score = max(0, min(20, int(round(score))))

    triggers = {
        "T1": bool(est_ppe),
        "T2": (mode_paiement == "especes" and float(montant_transaction or 0) > settings.ESPECES_THRESHOLD_FCFA),
        "T3": bool(sur_liste_sanctions),
        "T4": bool(pays_liste_noire_gafi or pays_liste_grise_gafi),
        "T5": bool(refus_documents),
        "T6": bool(be_non_identifiable),
    }
    actifs = {k: v for k, v in triggers.items() if v}

    if actifs:
        return ScoreResult(
            score=score,
            classification="ELEVE",
            axes=clean,
            triggers_actifs=actifs,
            force_par_trigger=True,
            trigger_principal=next(iter(actifs)),
        )
    return ScoreResult(
        score=score,
        classification=_classify(score),
        axes=clean,
        triggers_actifs={},
        force_par_trigger=False,
        trigger_principal=None,
    )


# ── Pré-remplissage (dérivation auto depuis dossier + KYC) ───────────────────────

def prefill(dossier, kyc_pp=None, kyc_pm=None, actionnaires_count: int = 0) -> dict[str, dict]:
    """Retourne {code: {valeur, auto, source}} pour pré-remplir le formulaire.

    Les axes `auto` sont verrouillés côté UI (override justifié) ; les axes non-auto
    valent 0 par défaut et sont laissés à la saisie de l'agent.
    `actionnaires_count` est passé explicitement (évite un lazy-load async).
    """
    kyc = kyc_pp or kyc_pm
    result: dict[str, dict] = {}

    # Axe 1 — Type de client
    v, src = _derive_type_client(dossier, actionnaires_count)
    result["type_client"] = {"valeur": v, "auto": True, "source": src}

    # Axe 2 — Pays / Géographie
    v, src = _derive_pays(kyc)
    result["pays_geographie"] = {"valeur": v, "auto": True, "source": src}

    # Axe 3 — Nature de l'opération
    v, src = _derive_type_operation(dossier)
    result["type_operation"] = {"valeur": v, "auto": True, "source": src}

    # Axe 4 — Montant
    v, src = _derive_montant(dossier)
    result["montant"] = {"valeur": v, "auto": dossier.montant_transaction is not None, "source": src}

    # Axe 5 — Mode de paiement
    v, src = _derive_mode_paiement(dossier)
    result["mode_paiement"] = {"valeur": v, "auto": bool(dossier.mode_paiement), "source": src}

    # Axe 6 — Complexité juridique (défaut depuis nb parties)
    v, src = _derive_complexite(dossier)
    result["complexite"] = {"valeur": v, "auto": True, "source": src}

    # Axe 7 — PPE
    is_ppe = bool(getattr(kyc, "est_ppe", False) or getattr(kyc, "ppe_detectee", False))
    result["ppe"] = {
        "valeur": 2 if is_ppe else 0,
        "auto": True,
        "source": "PPE déclarée" if is_ppe else "Non PPE",
    }

    # Axe 8 — Cohérence documentaire (saisie)
    result["coherence_doc"] = {"valeur": 0, "auto": False, "source": ""}

    # Axe 9 — Secteur d'activité
    v, src = _derive_secteur(kyc)
    result["secteur"] = {"valeur": v, "auto": True, "source": src}

    # Axe 10 — Intermédiaires (présence d'un mandataire)
    v, src = _derive_intermediaires(kyc)
    result["intermediaires"] = {"valeur": v, "auto": True, "source": src}

    return result


_UEMOA = {"CI", "BJ", "BF", "ML", "NE", "SN", "TG", "GW", "COTE D'IVOIRE", "CÔTE D'IVOIRE"}
_EUROPE_REGULE = {"FR", "BE", "CH", "DE", "US", "GB", "FRANCE", "BELGIQUE", "SUISSE", "ALLEMAGNE"}


def _derive_type_client(dossier, actionnaires_count: int = 0) -> tuple[int, str]:
    tc = dossier.type_client
    if tc == "PP":
        return 0, "Personne physique"
    if tc == "Indivision":
        return 1, "Indivision"
    if tc == "Association":
        return 1, "Association"
    # PM : 1 par défaut ; 2 si actionnariat complexe
    if actionnaires_count >= 4:
        return 2, f"PM — actionnariat complexe ({actionnaires_count} associés)"
    return 1, "Personne morale"


def _derive_pays(kyc) -> tuple[int, str]:
    pays = (getattr(kyc, "pays_residence", None) or "").strip().upper()
    if not pays:
        return 0, "Côte d'Ivoire (par défaut)"
    if pays in _UEMOA:
        return 0, f"UEMOA ({pays})"
    if pays in _EUROPE_REGULE:
        return 1, f"Pays régulé ({pays})"
    return 1, f"Pays tiers ({pays})"


def _derive_type_operation(dossier) -> tuple[int, str]:
    op = dossier.type_operation
    mapping = {
        "vente_immobiliere": (0, "Vente immobilière simple"),
        "donation": (1, "Donation"),
        "succession": (1, "Succession"),
        "constitution_societe": (1, "Constitution de société"),
        "manipulation_fonds": (2, "Manipulation de fonds / actifs"),
        "fiducicommis": (2, "Fidéicommis / structure analogue"),
        "autre": (1, "Autre opération"),
    }
    return mapping.get(op, (1, op or "—"))


def _derive_montant(dossier) -> tuple[int, str]:
    m = float(dossier.montant_transaction or 0)
    if dossier.montant_transaction is None:
        return 0, "Montant non renseigné"
    if m > 15_000_000:
        return 2, f"{m:,.0f} FCFA (> 15M)"
    if m >= 5_000_000:
        return 1, f"{m:,.0f} FCFA (5–15M)"
    return 0, f"{m:,.0f} FCFA (< 5M)"


def _derive_mode_paiement(dossier) -> tuple[int, str]:
    mode = dossier.mode_paiement or ""
    mapping = {
        "virement": (0, "Virement bancaire"),
        "cheque": (1, "Chèque"),
        "mix": (1, "Paiement mixte"),
        "especes": (2, "Espèces"),
        "paiement_tiers": (2, "Paiement via tiers"),
    }
    return mapping.get(mode, (0, "Non renseigné"))


def _derive_complexite(dossier) -> tuple[int, str]:
    n = int(dossier.nb_parties or 1)
    if n > 3:
        return 2, f"{n} parties — montage complexe"
    if n >= 2:
        return 1, f"{n} parties"
    return 0, "Acte simple (1 partie)"


_SECTEUR_ELEVE = ("crypto", "jeux", "pari", "casino", "btc", "bitcoin")
_SECTEUR_MOYEN = ("commerce", "cash", "import", "export", "immobilier", "change", "or ", "négoce")


def _derive_secteur(kyc) -> tuple[int, str]:
    sec = (getattr(kyc, "secteur_activite", None) or getattr(kyc, "libelle_activite", None) or "").lower()
    if not sec:
        return 0, "Secteur non renseigné"
    if any(k in sec for k in _SECTEUR_ELEVE):
        return 2, "Secteur sensible (cash/crypto/jeux)"
    if any(k in sec for k in _SECTEUR_MOYEN):
        return 1, "Secteur commerce/immobilier"
    return 0, "Secteur classique"


def _derive_intermediaires(kyc) -> tuple[int, str]:
    mand = getattr(kyc, "mandataire", None)
    if mand and isinstance(mand, dict) and (mand.get("prenom_nom") or mand.get("nom")):
        return 1, "Mandataire identifié"
    return 0, "Aucun intermédiaire"


def axes_from_prefill(pf: dict[str, dict]) -> dict[str, int]:
    """Extrait {code: valeur} d'un résultat de `prefill`."""
    return {code: int(pf[code]["valeur"]) for code in AXIS_CODES if code in pf}


# ── Simulateur stateless (onglet « Simulateur de Risque ») ───────────────────────
# Traduit les codes du formulaire UI → (score, justification) par axe canonique.
# Aucun dossier requis : sert d'outil pédagogique de test de combinaisons.

_SIM_PROFIL = {
    "particulier_salarie": (0, "Particulier salarié"),
    "profession_liberale": (1, "Profession libérale / entrepreneur"),
    "societe_sarl":        (1, "Société (SARL, SA)"),
    "societe_complexe":    (2, "Société à actionnariat complexe"),
    "structure_atypique":  (2, "Structure atypique (holding, offshore)"),
}
_SIM_ZONE = {
    "cote_ivoire":   (0, "Côte d'Ivoire"),
    "uemoa":         (1, "Zone UEMOA (hors CI)"),
    "europe_regule": (1, "Europe / pays régulé"),
    "gafi":          (2, "Pays liste grise/noire GAFI (T4)"),
}
# Catégories à plat du CDC v4 (Module 2, Règles métiers)
_SIM_TYPE_OP = {
    "vente_immobiliere_simple": (0, "Vente immobilière simple"),
    "donation_succession":      (1, "Donation / succession"),
    "creation_societe":         (1, "Création société"),
    "montage_complexe":         (2, "Montage complexe (SCI, multi-actes)"),
    "transaction_atypique":     (2, "Transaction atypique"),
}
_SIM_MODE_PAIEMENT = {
    "virement": (0, "Virement bancaire"),
    "cheque":   (1, "Chèque"),
    "mix":      (1, "Mix paiements"),
    "especes":  (2, "Espèces"),
    "tiers":    (2, "Paiement via tiers"),
}
_SIM_QUALITE = {
    "complet":         (0, "Dossier complet et cohérent"),
    "doute":           (1, "Léger doute documentaire"),
    "incoherence":     (2, "Incohérences / refus documentaire (T5)"),
    "presse_negative": (2, "Presse négative avérée"),
}
_SIM_RESEAU = {
    "aucun":     (0, "Aucun intermédiaire"),
    "identifie": (1, "Intermédiaire identifié"),
    "non_clair": (2, "Intermédiaire non clair"),
    "multiples": (2, "Montage avec plusieurs intermédiaires"),
}
_SIM_MONTANT = {0: "< 5M FCFA", 1: "5 – 15M FCFA", 2: "> 15M FCFA"}
_SIM_MONTAGE = {0: "Acte simple", 1: "Montage standard (2–3 parties)", 2: "Montage complexe / offshore"}
_SIM_SECTEUR = {0: "Secteur classique", 1: "Commerce / cash / import-export", 2: "Secteur sensible (crypto, jeux)"}


def _clamp02(v) -> int:
    return max(0, min(2, int(v or 0)))


def simulate(
    *,
    profil_code: str,
    zone_geo: str,
    type_operation: str,
    montant: int,
    mode_paiement_code: str,
    montage_juridique: int,
    is_ppe: bool,
    qualite_code: str,
    secteur_activite: int,
    reseau_code: str,
) -> dict:
    """Simule un scoring complet à partir des codes UI (stateless).

    Retourne {score_total, niveau, axes: [{code, label, score, justification}]}.
    Réutilise `calculate()` pour garantir l'identité de logique avec le scoring réel
    (mêmes seuils verrouillés, mêmes triggers absolutoires).
    """
    s_profil, j_profil = _SIM_PROFIL.get(profil_code, (0, "Non renseigné"))
    s_zone, j_zone     = _SIM_ZONE.get(zone_geo, (0, "Non renseigné"))
    s_op, j_op         = _SIM_TYPE_OP.get(type_operation, (0, "Non renseigné"))
    s_mont = _clamp02(montant)
    s_mode, j_mode     = _SIM_MODE_PAIEMENT.get(mode_paiement_code, (0, "Non renseigné"))
    s_montage = _clamp02(montage_juridique)
    s_qualite, j_qualite = _SIM_QUALITE.get(qualite_code, (0, "Non renseigné"))
    s_secteur = _clamp02(secteur_activite)
    s_reseau, j_reseau = _SIM_RESEAU.get(reseau_code, (0, "Non renseigné"))

    axes = {
        "type_client":     s_profil,
        "pays_geographie": s_zone,
        "type_operation":  s_op,
        "montant":         s_mont,
        "mode_paiement":   s_mode,
        "complexite":      s_montage,
        "ppe":             2 if is_ppe else 0,
        "coherence_doc":   s_qualite,
        "secteur":         s_secteur,
        "intermediaires":  s_reseau,
    }
    justifs = {
        "type_client":     j_profil,
        "pays_geographie": j_zone,
        "type_operation":  j_op,
        "montant":         _SIM_MONTANT[s_mont],
        "mode_paiement":   j_mode,
        "complexite":      _SIM_MONTAGE[s_montage],
        "ppe":             "PPE déclarée (T1)" if is_ppe else "Non-PPE",
        "coherence_doc":   j_qualite,
        "secteur":         _SIM_SECTEUR[s_secteur],
        "intermediaires":  j_reseau,
    }

    # Triggers absolutoires dérivés des codes UI.
    # T2 = espèces ET montant > 15M (Axe 4 = 2) — règle critique CDC v4.
    especes_t2 = (mode_paiement_code == "especes" and s_mont >= 2)
    result = calculate(
        axes,
        montant_transaction=(settings.ESPECES_THRESHOLD_FCFA + 1) if especes_t2 else 0,
        mode_paiement="especes" if especes_t2 else "",
        est_ppe=bool(is_ppe),
        pays_liste_grise_gafi=(zone_geo == "gafi"),
        refus_documents=(qualite_code == "incoherence"),
    )

    return {
        "score_total": result.score,
        "niveau": result.classification,
        "axes": [
            {
                "code": code,
                "label": AXIS_LABELS[code],
                "score": result.axes.get(code, 0),
                "justification": justifs.get(code, ""),
            }
            for code in AXIS_CODES
        ],
    }
