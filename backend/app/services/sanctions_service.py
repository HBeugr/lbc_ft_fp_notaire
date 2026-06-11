"""
Criblage de noms contre les listes de sanctions — reproduit la logique du projet
assujetti (rapidfuzz token_sort_ratio, seuil 85, désambiguïsation DDN prioritaire
puis lieu de naissance).
"""
from __future__ import annotations
import re
import unicodedata

# Seuil de fraîcheur (jours) au-delà duquel une liste est signalée périmée.
SANCTIONS_THRESHOLD_DAYS = 95
CRIBLAGE_SEUIL_DEFAULT = 85.0


def normalize_name(text: str) -> str:
    """Majuscules + suppression diacritiques — identique au parser d'ingestion."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


def normalize_dob(dob) -> str | None:
    """Normalise une DDN client au format YYYY-MM-DD. None si invalide."""
    if not dob:
        return None
    import datetime as _dt
    if isinstance(dob, (_dt.date, _dt.datetime)):
        return dob.strftime("%Y-%m-%d")
    try:
        return _dt.datetime.strptime(str(dob).strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _dob_exact_match(client_dob: str, list_dob: str) -> bool:
    """DDN complète DD/MM/YYYY dans la liste vs YYYY-MM-DD du client → confirmation forte."""
    list_dob = (list_dob or "").strip()
    if re.match(r"^\d{2}/\d{2}/\d{4}$", list_dob):
        parts = list_dob.split("/")
        return client_dob == f"{parts[2]}-{parts[1]}-{parts[0]}"
    return False


def _dob_year_only_match(client_dob: str, list_dob: str) -> bool:
    """Année seule dans la liste (ex: '1984') → signal faible."""
    list_dob = (list_dob or "").strip()
    return bool(re.match(r"^\d{4}$", list_dob)) and client_dob[:4] == list_dob


def _lieu_match(client_lieu: str, list_lieu: str) -> bool:
    """Correspondance floue du lieu de naissance (seuil 80%)."""
    from rapidfuzz import fuzz
    cl = normalize_name(client_lieu)
    ll = normalize_name(list_lieu)
    if not cl or not ll:
        return False
    return fuzz.token_sort_ratio(cl, ll) >= 80


def screen(
    *,
    nom: str,
    date_naissance: str | None,
    lieu_naissance: str | None,
    seuil: float,
    listes: list,
) -> list[dict]:
    """Crible un nom contre des listes actives (une entrée résultat par liste).

    `listes` : liste d'objets avec attributs `.nom`, `.type_liste`, `.entrees`
    (chaque entrée ayant `.nom`, `.date_naissance`, `.lieu_naissance`).
    Retourne une liste de dicts conformes au schéma CriblageResult.
    """
    from rapidfuzz import process, fuzz

    norm_nom = normalize_name(nom)
    norm_dob = normalize_dob(date_naissance)
    norm_lieu = normalize_name(lieu_naissance) if lieu_naissance else None

    results: list[dict] = []

    for liste in listes:
        entrees = liste.entrees
        if not entrees:
            continue
        noms_seuls = [e.nom for e in entrees]
        match = process.extractOne(norm_nom, noms_seuls, scorer=fuzz.token_sort_ratio)
        if match is None:
            continue

        matched_name, score, idx = match
        score = int(round(score))
        entry = entrees[idx]
        entry_dob = entry.date_naissance or ""
        entry_lieu = entry.lieu_naissance or ""

        niveau = "no_match"
        ddn_detail = None
        if score >= seuil:
            if norm_dob and entry_dob:
                if _dob_exact_match(norm_dob, entry_dob):
                    niveau, ddn_detail = "match", "ddn_confirmee"
                elif _dob_year_only_match(norm_dob, entry_dob):
                    niveau, ddn_detail = "warning", "annee_seule"
                else:
                    niveau, ddn_detail = "clear", "homonymie_confirmee"
            elif norm_lieu and entry_lieu:
                if _lieu_match(norm_lieu, entry_lieu):
                    niveau, ddn_detail = "warning", "lieu_match"
                else:
                    niveau, ddn_detail = "clear", "lieu_mismatch"
            else:
                niveau = "warning"
                ddn_detail = "ddn_absente_liste" if (norm_dob and not entry_dob) else None

        is_match = niveau in ("match", "warning")
        results.append({
            "liste": liste.nom,
            "type_liste": liste.type_liste,
            "score": score,
            "statut": "match" if is_match else "no_match",
            "niveau": niveau,
            "ddn_detail": ddn_detail,
            "nom_correspondant": matched_name if is_match else None,
        })

    return results
