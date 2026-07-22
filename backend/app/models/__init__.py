"""Chargement de tous les modèles.

Importer ce paquet garantit que `Base.metadata` (métier, un schéma par cabinet)
et `SharedBase.metadata` (annuaire) sont complets. C'est indispensable partout
où l'on part des métadonnées plutôt que des migrations : autogenerate Alembic,
provisioning d'un nouveau cabinet, fixtures de test.

Auparavant, `alembic/env.py` et `tests/conftest.py` importaient chacun leur
sous-ensemble de modèles, tous deux incomplets (sanctions, documents et
paramètres manquaient) — un autogenerate aurait proposé de supprimer ces tables.
Ce point d'entrée unique supprime la divergence.
"""

from app.models import (  # noqa: F401
    alerte,
    audit,
    bien_immobilier,
    document,
    dos,
    dossier,
    parametre_config,
    procedure,
    revision,
    sanction,
    shared,
    user,
)

__all__ = [
    "alerte",
    "audit",
    "bien_immobilier",
    "document",
    "dos",
    "dossier",
    "parametre_config",
    "procedure",
    "revision",
    "sanction",
    "shared",
    "user",
]
