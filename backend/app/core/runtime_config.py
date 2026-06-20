"""
Configuration runtime modifiable par l'Administrateur — PERSISTÉE en DB (FR-26).

Source unique de vérité pour :
- le seuil espèces Art. 72 (Trigger T2) ;
- les pondérations des 10 axes de scoring (× 0.1 – 5.0).

Architecture :
- Persistance : table `parametres_config` (clé/valeur). Survit aux redémarrages.
- Cache mémoire : les getters sont SYNCHRONES (lus par le scoring, en contexte
  non-async) → on sert depuis un cache module-level, amorcé au démarrage par
  `load_from_db()`.
- Écriture : `set_*` (async) persistent en DB ET rafraîchissent le cache.

Tous les consommateurs DOIVENT lire via get_seuil_especes_t2() / get_ponderations() —
aucun seuil espèces ni poids codé en dur ailleurs.

Note : les codes d'axes sont dupliqués ici (et non importés de scoring_service)
pour éviter un import circulaire (scoring_service importe ce module).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.parametre_config import ParametreConfig

# Clé de persistance du seuil espèces (colonne `cle`).
KEY_SEUIL_T2 = "seuil_especes_t2_fcfa"

# Codes des 10 axes (alignés sur scoring_service.AXIS_CODES — gardés synchronisés).
AXIS_CODES = [
    "type_client", "pays_geographie", "type_operation", "montant", "mode_paiement",
    "complexite", "ppe", "coherence_doc", "secteur", "intermediaires",
]


def _poids_key(code: str) -> str:
    return f"poids_{code}"


# Cache mémoire, amorcé depuis les défauts puis écrasé par load_from_db().
_cache_seuil: float = float(settings.ESPECES_THRESHOLD_FCFA)
_cache_poids: dict[str, float] = {code: 1.0 for code in AXIS_CODES}


# ── Lecture (synchrone, depuis le cache) ─────────────────────────────────────

def get_seuil_especes_t2() -> float:
    """Seuil espèces Art. 72 (T2) en vigueur."""
    return _cache_seuil


def get_ponderations() -> dict[str, float]:
    """Pondérations des 10 axes en vigueur (copie défensive)."""
    return dict(_cache_poids)


# ── Amorçage au démarrage ────────────────────────────────────────────────────

async def load_from_db(db: AsyncSession) -> None:
    """Charge seuil + pondérations persistés en cache. Appelé au startup (lifespan).

    Si une clé est absente en DB, on conserve le défaut déjà en cache (premier
    démarrage / DB vide) — la valeur sera persistée à la 1re modification Admin.
    """
    global _cache_seuil
    rows = (await db.execute(select(ParametreConfig))).scalars().all()
    by_key = {row.cle: row.valeur for row in rows if row.valeur is not None}
    if KEY_SEUIL_T2 in by_key:
        _cache_seuil = float(by_key[KEY_SEUIL_T2])
    for code in AXIS_CODES:
        k = _poids_key(code)
        if k in by_key:
            _cache_poids[code] = float(by_key[k])


# ── Écriture (async, persiste DB + cache) ────────────────────────────────────

async def _persist(db: AsyncSession, cle: str, value: float, updated_by: str | None) -> None:
    row = await db.get(ParametreConfig, cle)
    if row is None:
        db.add(ParametreConfig(cle=cle, valeur=value, updated_by=updated_by))
    else:
        row.valeur = value
        row.updated_by = updated_by


async def set_seuil_especes_t2(db: AsyncSession, value: float, updated_by: str | None = None) -> None:
    """Met à jour le seuil Art. 72 (T2). Réservé à l'Administrateur (FR-26)."""
    global _cache_seuil
    await _persist(db, KEY_SEUIL_T2, float(value), updated_by)
    _cache_seuil = float(value)


async def set_ponderations(db: AsyncSession, weights: dict[str, float], updated_by: str | None = None) -> None:
    """Met à jour les pondérations d'axes (clés inconnues ignorées). Admin uniquement."""
    for code in AXIS_CODES:
        if code in weights and weights[code] is not None:
            v = float(weights[code])
            await _persist(db, _poids_key(code), v, updated_by)
            _cache_poids[code] = v
