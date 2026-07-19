"""
Configuration runtime modifiable par l'Administrateur — PERSISTÉE en DB (FR-26).

Source unique de vérité pour :
- le seuil espèces Art. 72 (Trigger T2) ;
- les pondérations des 10 axes de scoring (× 0.1 – 5.0).

Architecture :
- Persistance : table `parametres_config` (clé/valeur), **propre à chaque schéma
  cabinet**. Survit aux redémarrages.
- Cache mémoire **par cabinet** : les getters sont SYNCHRONES (lus par le scoring,
  en contexte non-async) → on sert depuis un cache indexé par tenant, alimenté
  paresseusement à la première requête du cabinet (`ensure_loaded`).
- Écriture : `set_*` (async) persistent en DB ET rafraîchissent le cache du cabinet.

Le cloisonnement est ici critique : ces valeurs pilotent le scoring réglementaire.
Un cache global ferait qu'un cabinet modifiant son seuil espèces changerait la
classification de risque de tous les autres.

Tous les consommateurs DOIVENT lire via get_seuil_especes_t2() / get_ponderations() —
aucun seuil espèces ni poids codé en dur ailleurs.

Note : les codes d'axes sont dupliqués ici (et non importés de scoring_service)
pour éviter un import circulaire (scoring_service importe ce module).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.tenant_context import get_current_tenant
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


@dataclass
class _TenantConfig:
    """Paramètres de scoring en vigueur pour un cabinet."""

    seuil: float = float(settings.ESPECES_THRESHOLD_FCFA)
    poids: dict[str, float] = field(default_factory=lambda: {c: 1.0 for c in AXIS_CODES})
    loaded: bool = False


# Cache par cabinet. Un cabinet absent sert les défauts réglementaires.
_cache: dict[str, _TenantConfig] = {}


def _tenant_config() -> _TenantConfig:
    tenant_id = get_current_tenant().id
    cfg = _cache.get(tenant_id)
    if cfg is None:
        cfg = _TenantConfig()
        _cache[tenant_id] = cfg
    return cfg


def forget_tenant(tenant_id: str) -> None:
    """Purge le cache d'un cabinet (suspension, suppression, rechargement forcé)."""
    _cache.pop(tenant_id, None)


# ── Lecture (synchrone, depuis le cache du cabinet courant) ──────────────────

def get_seuil_especes_t2() -> float:
    """Seuil espèces Art. 72 (T2) en vigueur pour le cabinet courant."""
    return _tenant_config().seuil


def get_ponderations() -> dict[str, float]:
    """Pondérations des 10 axes du cabinet courant (copie défensive)."""
    return dict(_tenant_config().poids)


# ── Amorçage paresseux, par cabinet ──────────────────────────────────────────

def is_loaded(tenant_id: str) -> bool:
    cfg = _cache.get(tenant_id)
    return cfg is not None and cfg.loaded


async def load_from_db(db: AsyncSession) -> None:
    """Charge seuil + pondérations du cabinet courant depuis SON schéma.

    Si une clé est absente en DB, on conserve le défaut (cabinet fraîchement
    provisionné) — la valeur sera persistée à la 1re modification Admin.
    """
    cfg = _tenant_config()
    rows = (await db.execute(select(ParametreConfig))).scalars().all()
    by_key = {row.cle: row.valeur for row in rows if row.valeur is not None}
    if KEY_SEUIL_T2 in by_key:
        cfg.seuil = float(by_key[KEY_SEUIL_T2])
    for code in AXIS_CODES:
        k = _poids_key(code)
        if k in by_key:
            cfg.poids[code] = float(by_key[k])
    cfg.loaded = True


async def ensure_loaded(db: AsyncSession) -> None:
    """Charge la configuration du cabinet courant si ce n'est pas déjà fait.

    Appelé par le middleware tenant : une seule requête au premier appel de
    chaque cabinet, puis servi depuis le cache.
    """
    if not _tenant_config().loaded:
        await load_from_db(db)


# ── Écriture (async, persiste DB + cache du cabinet) ─────────────────────────

async def _persist(db: AsyncSession, cle: str, value: float, updated_by: str | None) -> None:
    row = await db.get(ParametreConfig, cle)
    if row is None:
        db.add(ParametreConfig(cle=cle, valeur=value, updated_by=updated_by))
    else:
        row.valeur = value
        row.updated_by = updated_by


async def set_seuil_especes_t2(db: AsyncSession, value: float, updated_by: str | None = None) -> None:
    """Met à jour le seuil Art. 72 (T2) du cabinet courant. Réservé à l'Administrateur (FR-26)."""
    await _persist(db, KEY_SEUIL_T2, float(value), updated_by)
    _tenant_config().seuil = float(value)


async def set_ponderations(db: AsyncSession, weights: dict[str, float], updated_by: str | None = None) -> None:
    """Met à jour les pondérations d'axes du cabinet courant (clés inconnues ignorées)."""
    cfg = _tenant_config()
    for code in AXIS_CODES:
        if code in weights and weights[code] is not None:
            v = float(weights[code])
            await _persist(db, _poids_key(code), v, updated_by)
            cfg.poids[code] = v
