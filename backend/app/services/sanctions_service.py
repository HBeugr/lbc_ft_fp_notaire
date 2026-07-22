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



# Séparateurs d'alias rencontrés dans les listes officielles. La liste nationale
# 1373 consigne les pseudonymes DANS le champ nom : « SIDAT MOUCTARR FAAL ALIAS
# « DADDYFALL » ». Comparer le nom recherché à cette chaîne entière fait chuter
# le score de correspondance (66 au lieu de 100 sur l'exemple ci-dessus, pour un
# seuil applicatif de 85) : la personne, pourtant listée, n'est PAS détectée si
# l'on saisit son vrai nom — ce que fait naturellement un notaire.
#
# On compare donc le nom recherché à chaque SEGMENT de l'entrée : la chaîne
# complète, la partie avant l'alias, et l'alias lui-même. Un match sur l'un
# quelconque des segments suffit. C'est un défaut de détection T3 (Art. 89), pas
# une question de confort.
_SEPARATEURS_ALIAS = (" ALIAS ", " ALIAS:", " AKA ", " DIT ", " DITE ")


# Guillemets et apostrophes encadrant les pseudonymes : sans portée sémantique.
_ORNEMENTS = "«»\"'“” "


def _nettoyer_segment(texte: str) -> str:
    return texte.strip().strip(_ORNEMENTS).strip()


def variantes_nom(nom: str) -> list[str]:
    """Segments comparables d'une entrée de liste : nom réel et alias éventuels."""
    if not nom:
        return []
    variantes = [nom]
    reste = nom.upper()
    for sep in _SEPARATEURS_ALIAS:
        if sep in reste:
            avant, apres = reste.split(sep, 1)
            variantes += [_nettoyer_segment(avant), _nettoyer_segment(apres)]
            reste = avant
    return [v for v in dict.fromkeys(variantes) if len(v) >= 3]


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
        # Un segment par variante de nom, en gardant le lien vers l'entrée d'origine.
        segments: list[str] = []
        origine: list[int] = []
        for position, e in enumerate(entrees):
            for variante in variantes_nom(e.nom):
                segments.append(variante)
                origine.append(position)
        if not segments:
            continue

        match = process.extractOne(norm_nom, segments, scorer=fuzz.token_sort_ratio)
        if match is None:
            continue

        matched_name, score, idx = match
        score = int(round(score))
        entry = entrees[origine[idx]]
        entry_dob = entry.date_naissance or ""
        entry_lieu = entry.lieu_naissance or ""

        niveau = "no_match"
        ddn_detail = None
        if score >= seuil:
            if norm_dob and entry_dob:
                if _dob_exact_match(norm_dob, entry_dob):
                    # DDN exacte MAIS lieu de naissance différent → homonyme possible :
                    # on rétrograde le match confirmé en "warning" (vérification RC) plutôt
                    # qu'un blocage T3 automatique (parité immo).
                    if norm_lieu and entry_lieu and not _lieu_match(norm_lieu, entry_lieu):
                        niveau, ddn_detail = "warning", "ddn_ok_lieu_mismatch"
                    else:
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


def pre_check(
    *,
    nom: str,
    date_naissance: str | None = None,
    lieu_naissance: str | None = None,
    nationalite: str | None = None,
    seuil: float = CRIBLAGE_SEUIL_DEFAULT,
    listes: list,
) -> dict:
    """Pré-vérification d'un nom (feedback UI, sans audit ni T3) — logique assujetti.

    Niveaux (du plus certain au moins certain) :
      blocked  : nom ≥ seuil + DDN complète identique
      clear    : nom ≥ seuil + nationalité différente | DDN complète différente
                 | lieu différent (DDN absente)
      warning  : nom ≥ seuil + année seule | lieu identique (DDN absente)
                 | aucun facteur de désambiguïsation
      no_lists : aucune liste active chargée
      clear    : aucun match
    """
    from rapidfuzz import process, fuzz

    norm_nom = normalize_name(nom)
    norm_dob = normalize_dob(date_naissance)
    norm_nat = normalize_name(nationalite) if nationalite else None
    norm_lieu = normalize_name(lieu_naissance) if lieu_naissance else None

    listes_avec_entrees = False
    for liste in listes:
        entrees = liste.entrees
        # Mêmes segments que `screen()` : sans cela l'écran de saisie KYC — le
        # chemin réellement emprunté par l'utilisateur — resterait aveugle aux
        # entrées portant un alias en ligne.
        segments: list[str] = []
        origine: list[int] = []
        for position, e in enumerate(entrees):
            for variante in variantes_nom(e.nom):
                segments.append(variante)
                origine.append(position)
        if not segments:
            continue
        listes_avec_entrees = True
        match = process.extractOne(norm_nom, segments, scorer=fuzz.token_sort_ratio)
        if not match or match[1] < seuil:
            continue

        matched_name, score, idx = match
        score = int(round(score))
        entry = entrees[origine[idx]]
        entry_dob = entry.date_naissance or ""
        entry_nat = normalize_name(entry.nationalite) if entry.nationalite else None
        entry_lieu = entry.lieu_naissance or ""

        # 1. Nationalité différente → homonyme confirmé
        if norm_nat and entry_nat and norm_nat != entry_nat:
            return {"level": "clear", "score": score, "liste": liste.nom,
                    "nom_correspondant": matched_name, "reason": "nationality_mismatch"}
        # 2. DDN (prioritaire)
        if norm_dob and entry_dob:
            if _dob_exact_match(norm_dob, entry_dob):
                # DDN exacte MAIS lieu de naissance différent → homonyme possible :
                # warning (vérification RC) plutôt que blocage T3 automatique (parité immo).
                if norm_lieu and entry_lieu and not _lieu_match(norm_lieu, entry_lieu):
                    return {"level": "warning", "score": score, "liste": liste.nom,
                            "type_liste": liste.type_liste,
                            "nom_correspondant": matched_name, "reason": "dob_match_lieu_mismatch"}
                return {"level": "blocked", "score": score, "liste": liste.nom,
                        "type_liste": liste.type_liste,
                        "nom_correspondant": matched_name, "reason": "name_and_dob_match"}
            if _dob_year_only_match(norm_dob, entry_dob):
                return {"level": "warning", "score": score, "liste": liste.nom,
                        "type_liste": liste.type_liste,
                        "nom_correspondant": matched_name, "reason": "year_only_match"}
            return {"level": "clear", "score": score, "liste": liste.nom,
                    "nom_correspondant": matched_name, "reason": "dob_mismatch"}
        # 3. Lieu (secondaire si DDN absente)
        if norm_lieu and entry_lieu:
            if _lieu_match(norm_lieu, entry_lieu):
                return {"level": "warning", "score": score, "liste": liste.nom,
                        "type_liste": liste.type_liste,
                        "nom_correspondant": matched_name, "reason": "lieu_match"}
            return {"level": "clear", "score": score, "liste": liste.nom,
                    "nom_correspondant": matched_name, "reason": "lieu_mismatch"}
        # 4. Aucun facteur → alerte, RC décide
        return {"level": "warning", "score": score, "liste": liste.nom,
                "type_liste": liste.type_liste,
                "nom_correspondant": matched_name, "reason": "name_only"}

    if not listes_avec_entrees:
        return {"level": "no_lists", "score": 0, "liste": None, "nom_correspondant": None, "reason": None}
    return {"level": "clear", "score": 0, "liste": None, "nom_correspondant": None, "reason": None}
