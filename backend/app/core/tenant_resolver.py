"""Résolution du cabinet : email → cabinet, id → cabinet.

C'est la « réception de l'immeuble » de l'analyse SaaS : le seul composant
capable de dire à quel cabinet appartient une connexion **avant** de savoir dans
quel schéma chercher.

Un cache mémoire à TTL court évite une requête sur l'annuaire à chaque appel HTTP
(le middleware résout le tenant sur toutes les requêtes authentifiées) tout en
propageant les changements de statut — suspension notamment — en moins d'une
minute sans redémarrage.
"""
from __future__ import annotations

import time

from sqlalchemy import select

from app.core.config import settings
from app.core.database import shared_session
from app.core.tenant_context import TenantContext
from app.models.shared import Tenant, TenantUser

# Un TTL court est volontaire : suspendre un cabinet doit couper l'accès vite.
_CACHE_TTL_SECONDS = 30

_by_id: dict[str, tuple[float, TenantContext]] = {}
_email_to_id: dict[str, tuple[float, str | None]] = {}


def _to_context(tenant: Tenant) -> TenantContext:
    return TenantContext(
        id=tenant.id,
        schema=tenant.schema_name,
        slug=tenant.slug,
        nom=tenant.nom_cabinet,
        statut=tenant.statut,
        key_salt=tenant.key_salt,
        totp_required=tenant.totp_required,
        storage_bucket=tenant.storage_bucket,
    )


def _fresh(entry: tuple[float, object] | None) -> bool:
    return entry is not None and (time.monotonic() - entry[0]) < _CACHE_TTL_SECONDS


def invalidate(tenant_id: str | None = None) -> None:
    """Purge le cache — après provisioning, suspension ou réactivation."""
    if tenant_id is None:
        _by_id.clear()
        _email_to_id.clear()
        return
    _by_id.pop(tenant_id, None)
    for email, (_, tid) in list(_email_to_id.items()):
        if tid == tenant_id:
            _email_to_id.pop(email, None)


async def get_by_id(tenant_id: str) -> TenantContext | None:
    cached = _by_id.get(tenant_id)
    if _fresh(cached):
        return cached[1]

    async with shared_session() as db:
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            return None
        ctx = _to_context(tenant)

    _by_id[tenant_id] = (time.monotonic(), ctx)
    return ctx


async def get_by_email(email: str) -> TenantContext | None:
    """Aiguillage au login. L'email identifie le cabinet de façon unique."""
    key = email.strip().lower()
    cached = _email_to_id.get(key)
    if _fresh(cached):
        tenant_id = cached[1]
        return await get_by_id(tenant_id) if tenant_id else None

    async with shared_session() as db:
        row = (
            await db.execute(
                select(TenantUser).where(TenantUser.email == key, TenantUser.is_active.is_(True))
            )
        ).scalar_one_or_none()
        tenant_id = row.tenant_id if row else None

    _email_to_id[key] = (time.monotonic(), tenant_id)
    return await get_by_id(tenant_id) if tenant_id else None


async def get_by_slug(slug: str) -> TenantContext | None:
    async with shared_session() as db:
        tenant = (
            await db.execute(select(Tenant).where(Tenant.slug == slug))
        ).scalar_one_or_none()
        return _to_context(tenant) if tenant else None


async def list_active_tenants() -> list[TenantContext]:
    """Cabinets en production — utilisé par les migrations et le scheduler."""
    async with shared_session() as db:
        rows = (
            await db.execute(select(Tenant).where(Tenant.statut == "production"))
        ).scalars().all()
        return [_to_context(t) for t in rows]


async def list_all_tenants() -> list[TenantContext]:
    """Tous les cabinets, y compris en configuration — les migrations doivent
    aussi atteindre un schéma pas encore mis en production."""
    async with shared_session() as db:
        rows = (await db.execute(select(Tenant))).scalars().all()
        return [_to_context(t) for t in rows]


def schema_for(tenant_id: str) -> str:
    return settings.tenant_schema(tenant_id)
