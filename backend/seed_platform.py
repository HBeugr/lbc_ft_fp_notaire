"""Amorçage de la plateforme SaaS.

Crée le compte Super-Admin d'exploitation, puis — optionnellement — un cabinet
de démonstration entièrement provisionné avec ses comptes par rôle.

    python seed_platform.py                  # Super-Admin seul
    python seed_platform.py --demo           # + cabinet de démonstration

Prérequis : les migrations de l'annuaire doivent être jouées
(`alembic -c alembic_shared.ini upgrade head`). Les migrations du cabinet de
démonstration, elles, sont déclenchées automatiquement par le provisioning.

Remplace l'ancien `seed_admin.py`, qui insérait quatre utilisateurs dans une
base unique — notion qui n'existe plus : un utilisateur appartient toujours à
un cabinet.
"""
import argparse
import asyncio
import os
import sys

from sqlalchemy import select

from app.core import security
from app.core.database import shared_session, tenant_session
from app.core.tenant_context import TenantContext, tenant_scope
from app.models.shared import SuperAdmin
from app.models.user import User
from app.services import tenant_directory, tenant_provisioning

# Comptes de démonstration du cabinet — mots de passe à changer immédiatement.
DEMO_USERS = [
    ("notaire@notaire.local", "Maître", "Dupont", "notaire_principal", "Notaire2026!"),
    ("conformite@notaire.local", "Marie", "Martin", "responsable_conformite", "Conformite2026!"),
    ("clerc@notaire.local", "Jean", "Clerc", "clercs", "Clerc2026!"),
]


async def seed_super_admin() -> tuple[str, str | None]:
    """Crée le compte d'exploitation s'il n'existe pas encore."""
    # Défauts alignés sur le back-office CCI immobilier, à la demande de
    # l'exploitant : un seul couple d'identifiants à retenir pour ses projets.
    # Ce sont des valeurs de développement — `must_change_password` ci-dessous
    # impose leur remplacement à la première connexion, et la console reste
    # verrouillée sur la page de compte tant que ce n'est pas fait.
    email = os.environ.get("SUPER_ADMIN_EMAIL", "admin@cci.ci").strip().lower()
    password = os.environ.get("SUPER_ADMIN_PASSWORD", "ChangeMoi2026!")

    async with shared_session() as db:
        existing = (
            await db.execute(select(SuperAdmin).where(SuperAdmin.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            return email, None

        db.add(SuperAdmin(
            email=email,
            hashed_password=security.hash_password(password),
            first_name=os.environ.get("SUPER_ADMIN_FIRST_NAME", "Super"),
            last_name=os.environ.get("SUPER_ADMIN_LAST_NAME", "Admin"),
            is_active=True,
            must_change_password=True,
        ))
        await db.commit()
    return email, password


async def seed_demo_tenant() -> None:
    """Provisionne un cabinet de démonstration et ses comptes par rôle."""
    result = await tenant_provisioning.provision_tenant(
        nom_cabinet="Étude Notariale de Démonstration",
        slug="demo",
        contact_email="contact@notaire.local",
        admin_email="admin@notaire.local",
        admin_first_name="Admin",
        admin_last_name="Système",
        numero_agrement="CNCI-DEMO-001",
        # La 2FA est désactivée sur le cabinet de démonstration pour ne pas
        # bloquer une prise en main ; elle reste obligatoire en production.
        totp_required=False,
    )
    tenant = result.tenant

    # Mise en production immédiate : un cabinet en « configuration » refuse les
    # connexions, ce qui rendrait la démonstration inutilisable.
    await tenant_provisioning.set_tenant_statut(tenant.id, "production")

    context = TenantContext(
        id=tenant.id, schema=tenant.schema_name, slug=tenant.slug, nom=tenant.nom_cabinet,
        statut="production", key_salt=tenant.key_salt, totp_required=tenant.totp_required,
        storage_bucket=tenant.storage_bucket,
    )
    with tenant_scope(context):
        async with tenant_session(context) as db:
            for email, first, last, role, password in DEMO_USERS:
                user = User(
                    email=email,
                    hashed_password=security.hash_password(password),
                    first_name=first,
                    last_name=last,
                    role=role,
                    is_active=True,
                    must_change_password=False,
                )
                db.add(user)
                await db.flush()
                await tenant_directory.register(email, user.id)
            await db.commit()

    print("\n" + "=" * 72)
    print("CABINET DE DÉMONSTRATION PROVISIONNÉ")
    print("=" * 72)
    print(f"  Cabinet : {tenant.nom_cabinet}  (slug : {tenant.slug})")
    print(f"  Schéma  : {tenant.schema_name}")
    print(f"  Bucket  : {tenant.storage_bucket}")
    print("-" * 72)
    print(f"  {'Email':<32} {'Mot de passe':<22} Rôle")
    print("-" * 72)
    print(f"  {result.admin_email:<32} {result.admin_temp_password:<22} admin (à changer)")
    for email, _f, _l, role, password in DEMO_USERS:
        print(f"  {email:<32} {password:<22} {role}")
    print("=" * 72)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Amorçage de la plateforme SaaS notariale.")
    parser.add_argument("--demo", action="store_true", help="Provisionner un cabinet de démonstration.")
    args = parser.parse_args()

    try:
        email, password = await seed_super_admin()
    except Exception as exc:
        print(f"Annuaire inaccessible — jouez d'abord : alembic -c alembic_shared.ini upgrade head\n{exc}")
        sys.exit(1)

    print("\n" + "=" * 72)
    print("COMPTE SUPER-ADMIN (exploitation de la plateforme)")
    print("=" * 72)
    if password is None:
        print(f"  {email} — déjà existant, inchangé.")
    else:
        print(f"  {email} / {password}")
        print("  Changement de mot de passe imposé à la première connexion.")
    print("=" * 72)

    if args.demo:
        try:
            await seed_demo_tenant()
        except tenant_provisioning.ProvisioningError as exc:
            print(f"\nCabinet de démonstration non créé : {exc}")


if __name__ == "__main__":
    asyncio.run(main())
