"""Contexte tenant courant — socle de l'isolation multi-cabinet.

Le tenant actif est porté par un `ContextVar`, posé une seule fois par requête
(dépendance `get_db` / middleware) et lu par tout ce qui doit être cloisonné :
routage du `search_path`, clé de chiffrement, préfixes Redis, bucket MinIO,
cache de configuration métier.

Pourquoi un ContextVar plutôt qu'un paramètre propagé partout : plusieurs points
de cloisonnement sont **synchrones et sans accès à la session** — notamment
`EncryptedString.process_bind_param` (SQLAlchemy `TypeDecorator`) et les getters
de `runtime_config` appelés depuis le scoring. Un ContextVar est le seul canal
qui les atteint sans réécrire les 113 points d'injection de session.

`ContextVar` est nativement isolé par tâche asyncio : deux requêtes concurrentes
de deux cabinets différents ne peuvent pas se marcher dessus.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    """Identité du cabinet servant la requête courante."""

    id: str
    schema: str
    slug: str
    nom: str
    statut: str
    # Sel propre au tenant : la clé AES du cabinet en est dérivée (HKDF).
    key_salt: str
    # Politique 2FA du cabinet — surcharge le défaut global de la plateforme.
    totp_required: bool = True
    # Bucket documentaire dédié, figé à la création du cabinet.
    storage_bucket: str = ""

    @property
    def is_active(self) -> bool:
        return self.statut == "production"


_current_tenant: ContextVar[TenantContext | None] = ContextVar(
    "current_tenant", default=None
)


class NoTenantContextError(RuntimeError):
    """Levée quand du code métier s'exécute hors de tout cabinet.

    C'est volontairement une erreur dure : un chiffrement ou une requête métier
    sans tenant identifié est un défaut d'isolation, jamais un cas nominal.
    """


def get_current_tenant() -> TenantContext:
    tenant = _current_tenant.get()
    if tenant is None:
        raise NoTenantContextError(
            "Aucun cabinet actif dans le contexte : opération métier interdite hors tenant."
        )
    return tenant


def get_current_tenant_or_none() -> TenantContext | None:
    return _current_tenant.get()


def set_current_tenant(tenant: TenantContext | None):
    """Pose le tenant courant. Retourne le token de restauration."""
    return _current_tenant.set(tenant)


def reset_current_tenant(token) -> None:
    _current_tenant.reset(token)


@contextmanager
def tenant_scope(tenant: TenantContext | None):
    """Exécute un bloc dans le contexte d'un cabinet donné.

    Utilisé par les tâches hors requête HTTP (provisioning, scheduler, scripts
    de migration) qui doivent se placer explicitement dans un tenant.
    """
    token = set_current_tenant(tenant)
    try:
        yield tenant
    finally:
        reset_current_tenant(token)
