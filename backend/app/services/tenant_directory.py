"""Tenue de l'annuaire `shared.tenant_users`.

L'annuaire est ce qui permet à `/auth/login` de router un email vers le bon
cabinet **avant** d'ouvrir la moindre session métier. Il doit donc rester
strictement synchronisé avec la table `users` de chaque schéma : un utilisateur
créé dans un cabinet mais absent de l'annuaire ne pourrait jamais se connecter,
et un email resté dans l'annuaire après suppression du compte router
indéfiniment vers un cabinet où il n'existe plus.

Toute création, modification d'email ou désactivation d'utilisateur passe par
ici.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.core import tenant_resolver
from app.core.database import shared_session
from app.core.tenant_context import get_current_tenant
from app.models.shared import Tenant, TenantUser


class DirectoryError(Exception):
    """Conflit d'annuaire — typiquement un email déjà rattaché à un cabinet."""


class QuotaExceededError(Exception):
    """Le cabinet a atteint son quota de sièges."""


async def is_email_available(email: str) -> bool:
    """L'email est-il libre au niveau plateforme ?

    L'unicité est volontairement globale et non par cabinet : c'est ce qui permet
    un login par simple email/mot de passe, sans demander à l'utilisateur de
    désigner son cabinet.
    """
    async with shared_session() as db:
        row = (
            await db.execute(select(TenantUser).where(TenantUser.email == email.strip().lower()))
        ).scalar_one_or_none()
        return row is None


async def assert_quota_available(current_active_users: int) -> None:
    """Vérifie le quota de sièges du cabinet avant d'en consommer un.

    `max_users = 0` signifie « illimité » — le cas par défaut tant qu'aucun plan
    tarifaire n'est en place.
    """
    tenant_id = get_current_tenant().id
    async with shared_session() as db:
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None or tenant.max_users == 0:
            return
        if current_active_users >= tenant.max_users:
            raise QuotaExceededError(
                f"Quota atteint : votre formule autorise {tenant.max_users} utilisateurs actifs."
            )


async def register(email: str, user_id: str, *, is_active: bool = True) -> None:
    """Rattache un email au cabinet courant."""
    email = email.strip().lower()
    tenant_id = get_current_tenant().id
    async with shared_session() as db:
        existing = (
            await db.execute(select(TenantUser).where(TenantUser.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            if existing.tenant_id != tenant_id:
                raise DirectoryError(f"L'adresse « {email} » est déjà rattachée à un autre cabinet.")
            existing.user_id = user_id
            existing.is_active = is_active
        else:
            db.add(TenantUser(
                email=email, tenant_id=tenant_id, user_id=user_id, is_active=is_active
            ))
        await db.commit()
    tenant_resolver.invalidate(tenant_id)


async def set_active(user_id: str, is_active: bool) -> None:
    """Répercute une (dés)activation de compte sur l'annuaire.

    Un compte désactivé doit cesser d'être routable : sans cela, `/auth/login`
    continuerait d'ouvrir une session sur le cabinet pour se voir refuser plus
    loin, ce qui divulguerait l'existence du rattachement.
    """
    tenant_id = get_current_tenant().id
    async with shared_session() as db:
        row = (
            await db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == tenant_id, TenantUser.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            row.is_active = is_active
            await db.commit()
    tenant_resolver.invalidate(tenant_id)


async def rename(user_id: str, new_email: str) -> None:
    """Change l'email d'aiguillage d'un utilisateur (l'email est la clé de routage)."""
    new_email = new_email.strip().lower()
    tenant_id = get_current_tenant().id
    async with shared_session() as db:
        conflict = (
            await db.execute(select(TenantUser).where(TenantUser.email == new_email))
        ).scalar_one_or_none()
        if conflict is not None and conflict.user_id != user_id:
            raise DirectoryError(f"L'adresse « {new_email} » est déjà utilisée.")

        row = (
            await db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == tenant_id, TenantUser.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            # L'email est la clé primaire : on remplace la ligne plutôt que de la modifier.
            is_active = row.is_active
            await db.delete(row)
            await db.flush()
            db.add(TenantUser(
                email=new_email, tenant_id=tenant_id, user_id=user_id, is_active=is_active
            ))
        else:
            db.add(TenantUser(email=new_email, tenant_id=tenant_id, user_id=user_id))
        await db.commit()
    tenant_resolver.invalidate(tenant_id)


async def count_registered() -> int:
    """Nombre d'emails actifs rattachés au cabinet courant."""
    tenant_id = get_current_tenant().id
    async with shared_session() as db:
        return (
            await db.execute(
                select(func.count()).select_from(TenantUser).where(
                    TenantUser.tenant_id == tenant_id, TenantUser.is_active.is_(True)
                )
            )
        ).scalar_one()
