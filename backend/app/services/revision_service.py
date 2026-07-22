"""Calcul des fréquences de réévaluation KYC (Art. 19, Ordonnance 2023-875)."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


# Fréquences par classification (Art. 19)
_FREQUENCES = {
    "FAIBLE": relativedelta(years=5),
    "MOYEN": relativedelta(years=3),
    "ELEVE": relativedelta(years=2),
}

# PPE → toujours 3 ans (Art. 29, non paramétrable)
_FREQUENCE_PPE = relativedelta(years=3)

# Trigger absolutoire actif → 1 an
_FREQUENCE_TRIGGER = relativedelta(years=1)


def prochaine_echeance(
    classification: str,
    est_ppe: bool = False,
    trigger_actif: bool = False,
    depuis: date | None = None,
) -> date:
    base = depuis or date.today()
    if trigger_actif:
        return base + _FREQUENCE_TRIGGER
    if est_ppe:
        return base + _FREQUENCE_PPE
    delta = _FREQUENCES.get(classification, _FREQUENCES["MOYEN"])
    return base + delta


def jalons_relance(date_echeance: date) -> dict[str, date]:
    return {
        "alerte_j_minus_30": date_echeance - timedelta(days=30),
        "relance_1": date_echeance + timedelta(days=30),
        "relance_2": date_echeance + timedelta(days=60),
        "vigilance_renforcee": date_echeance + timedelta(days=90),
        "blocage": date_echeance + timedelta(days=120),
    }
