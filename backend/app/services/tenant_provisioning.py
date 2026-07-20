"""Provisioning d'un cabinet — « préparer le bureau avant l'emménagement ».

Enchaîne, à partir d'un simple formulaire, les étapes qui étaient jusqu'ici
faites à la main par un développeur :

    1. Créer le bureau      → CREATE SCHEMA tenant_<uuid>
    2. Installer les meubles→ jouer les migrations Alembic dans ce schéma
    3. Ouvrir le coffre     → sel de chiffrement + bucket de stockage dédiés
    4. Remettre les clés    → créer le compte Admin du cabinet + l'inscrire à l'annuaire

Le cabinet naît en statut « configuration » : il n'est utilisable qu'une fois
activé, ce qui laisse à l'exploitant le temps de vérifier le dossier
d'agrément avant toute saisie de données de conformité.

Point d'attention : les étapes touchent trois systèmes (PostgreSQL, MinIO,
annuaire). En cas d'échec en cours de route, `_rollback` défait ce qui a été
créé — un schéma orphelin bloquerait un futur provisioning sous le même nom.
"""
from __future__ import annotations

import asyncio
import re
import secrets
import sys
import unicodedata
import uuid
from pathlib import Path
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core import dos_privileges, security, tenant_resolver
from app.core.config import settings
from app.core.database import shared_session, tenant_session
from app.core.logging import logger
from app.core.storage import bucket_for_slug, ensure_tenant_bucket
from app.core.tenant_context import TenantContext, tenant_scope
from app.models.shared import Tenant, TenantAuditLog, TenantUser
from app.models.user import User


# Racine du backend : `alembic.ini` y est résolu quel que soit le répertoire
# courant du processus (API lancée depuis /app, tests depuis backend/…).
_BACKEND_ROOT = Path(__file__).resolve().parents[2]


class ProvisioningError(Exception):
    """Échec de création d'un cabinet — l'appelant doit renvoyer une 4xx/5xx explicite."""


@dataclass
class ProvisionedTenant:
    tenant: Tenant
    admin_email: str
    # Mot de passe temporaire : affiché UNE fois à l'exploitant, jamais stocké en clair.
    admin_temp_password: str


def slugify(value: str) -> str:
    """Slug de cabinet : identifiant lisible, utilisable en nom de bucket."""
    normalised = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalised.lower()).strip("-")
    return slug[:48] or "cabinet"


def _generate_temp_password() -> str:
    """Mot de passe temporaire conforme à la politique (12+, mixte)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    core = "".join(secrets.choice(alphabet) for _ in range(14))
    return f"{core}#7a"


async def _run_alembic(schema: str) -> None:
    """Joue les migrations métier dans le schéma du cabinet.

    Alembic est lancé en sous-processus plutôt qu'en API interne : il gère lui-même
    sa boucle d'événements et sa connexion, or nous sommes déjà dans une boucle
    asyncio. Le mélanger au processus applicatif est une source connue de blocages.
    """
    # `sys.executable -m alembic` plutôt que le binaire `alembic` : le
    # provisioning ne doit pas dépendre du PATH du processus. On garantit ainsi
    # l'usage du même interpréteur — et donc du même environnement virtuel — que
    # l'application, quelle que soit la façon dont elle a été lancée.
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "alembic",
        "-c", "alembic.ini", "-x", f"schema={schema}", "upgrade", "head",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=_BACKEND_ROOT,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        raise ProvisioningError(
            f"Migrations échouées sur {schema} : {stdout.decode('utf-8', 'replace')[-2000:]}"
        )


async def _rollback(schema: str, slug: str) -> None:
    """Défait un provisioning partiel — sinon le nom reste inutilisable."""
    try:
        async with shared_session() as db:
            await db.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            await db.commit()
    except Exception:  # pragma: no cover — best effort
        logger.exception("tenant.rollback_failed", schema=schema, slug=slug)


async def provision_tenant(
    *,
    nom_cabinet: str,
    contact_email: str,
    admin_email: str,
    admin_first_name: str,
    admin_last_name: str,
    slug: str | None = None,
    numero_agrement: str | None = None,
    pays: str = "CI",
    contact_telephone: str | None = None,
    adresse: str | None = None,
    totp_required: bool = True,
    max_users: int = 0,
    super_admin_id: str | None = None,
) -> ProvisionedTenant:
    """Crée un cabinet de bout en bout et retourne ses accès initiaux."""
    slug = slugify(slug or nom_cabinet)
    admin_email = admin_email.strip().lower()
    contact_email = contact_email.strip().lower()

    # ── Unicité, avant toute création ────────────────────────────────────────
    async with shared_session() as db:
        if (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none():
            raise ProvisioningError(f"Un cabinet utilise déjà l'identifiant « {slug} ».")
        if numero_agrement and (
            await db.execute(select(Tenant).where(Tenant.numero_agrement == numero_agrement))
        ).scalar_one_or_none():
            raise ProvisioningError(f"Le numéro d'agrément « {numero_agrement} » est déjà enregistré.")
        # L'email pilote le routage au login : il doit être unique sur la plateforme.
        if (
            await db.execute(select(TenantUser).where(TenantUser.email == admin_email))
        ).scalar_one_or_none():
            raise ProvisioningError(f"L'adresse « {admin_email} » est déjà rattachée à un cabinet.")

        # L'identifiant est généré ici et non laissé au défaut de colonne : le nom
        # du schéma en dérive, et il faut donc le connaître avant l'INSERT.
        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            id=tenant_id,
            slug=slug,
            nom_cabinet=nom_cabinet,
            schema_name="",  # renseigné juste après, l'id étant généré côté Python
            statut="configuration",
            key_salt=secrets.token_hex(32),
            storage_bucket="",
            numero_agrement=numero_agrement,
            pays=pays,
            contact_email=contact_email,
            contact_telephone=contact_telephone,
            adresse=adresse,
            totp_required=totp_required,
            max_users=max_users,
        )
        tenant.schema_name = settings.tenant_schema(tenant_id)
        tenant.storage_bucket = bucket_for_slug(slug)
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)

    schema = tenant.schema_name
    temp_password = _generate_temp_password()

    try:
        # ── Étapes 1 & 2 : le schéma et ses tables ──────────────────────────
        await _run_alembic(schema)

        # ── Étape 3 : stockage documentaire dédié + cloisonnement DOS ───────
        ensure_tenant_bucket(tenant.storage_bucket)
        await dos_privileges.apply_to_tenant(schema)

        # ── Étape 4 : le premier compte administrateur du cabinet ───────────
        context = TenantContext(
            id=tenant.id,
            schema=schema,
            slug=tenant.slug,
            nom=tenant.nom_cabinet,
            statut=tenant.statut,
            key_salt=tenant.key_salt,
            totp_required=tenant.totp_required,
            storage_bucket=tenant.storage_bucket,
        )
        with tenant_scope(context):
            async with tenant_session(context) as db:
                admin = User(
                    email=admin_email,
                    hashed_password=security.hash_password(temp_password),
                    first_name=admin_first_name,
                    last_name=admin_last_name,
                    role="admin",
                    is_active=True,
                    # L'exploitant connaît le mot de passe initial : il doit être
                    # changé à la première connexion.
                    must_change_password=True,
                )
                db.add(admin)
                await db.commit()
                await db.refresh(admin)
                admin_id = admin.id

        # Inscription à l'annuaire : c'est ce qui rend le login possible.
        async with shared_session() as db:
            db.add(TenantUser(email=admin_email, tenant_id=tenant.id, user_id=admin_id))
            db.add(TenantAuditLog(
                tenant_id=tenant.id,
                super_admin_id=super_admin_id,
                action="tenant.provisioned",
                detail=f"Cabinet « {nom_cabinet} » créé (schéma {schema}, admin {admin_email}).",
            ))
            await db.commit()

    except Exception as exc:
        await _rollback(schema, slug)
        async with shared_session() as db:
            obsolete = await db.get(Tenant, tenant.id)
            if obsolete is not None:
                await db.delete(obsolete)
                await db.commit()
        logger.exception("tenant.provisioning_failed", slug=slug, schema=schema)
        raise ProvisioningError(f"Provisioning du cabinet échoué : {exc}") from exc

    tenant_resolver.invalidate()
    logger.info("tenant.provisioned", tenant_id=tenant.id, slug=slug, schema=schema)
    return ProvisionedTenant(tenant=tenant, admin_email=admin_email, admin_temp_password=temp_password)


async def update_tenant(
    tenant_id: str,
    changes: dict[str, object],
    *,
    super_admin_id: str | None = None,
) -> Tenant:
    """Modifie les attributs administratifs d'un cabinet.

    L'appelant est responsable d'avoir écarté les champs figés (slug,
    schema_name, key_salt, statut) : ils ne sont pas seulement immuables par
    convention, les changer casserait respectivement le routage, la résolution
    de schéma et le déchiffrement des données existantes.
    """
    if not changes:
        raise ProvisioningError("Aucune modification demandée.")

    async with shared_session() as db:
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            raise ProvisioningError("Cabinet introuvable.")

        applied: list[str] = []
        for champ, valeur in changes.items():
            if getattr(tenant, champ) != valeur:
                setattr(tenant, champ, valeur)
                applied.append(champ)

        if not applied:
            return tenant

        db.add(TenantAuditLog(
            tenant_id=tenant_id,
            super_admin_id=super_admin_id,
            action="tenant.updated",
            detail=f"Champs modifiés : {', '.join(sorted(applied))}.",
        ))
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            # Le seul unique atteignable ici est `numero_agrement`.
            raise ProvisioningError(
                "Ce numéro d'agrément est déjà attribué à un autre cabinet."
            ) from exc
        await db.refresh(tenant)

    # `totp_required` et le nom du cabinet sont portés par le contexte de
    # routage : sans invalidation, les sessions en cours garderaient l'ancienne
    # politique 2FA jusqu'à expiration du cache.
    tenant_resolver.invalidate(tenant_id)
    logger.info("tenant.updated", tenant_id=tenant_id, champs=applied)
    return tenant


async def reset_tenant_admin_password(
    tenant_id: str,
    *,
    super_admin_id: str | None = None,
) -> tuple[str, str]:
    """Réémet un mot de passe temporaire pour l'administrateur d'un cabinet.

    Seul recours quand le mot de passe affiché à la création a été perdu : sans
    lui, le cabinet est inaccessible et personne à l'intérieur ne peut ouvrir de
    session pour réparer.

    Volontairement borné au compte de rôle `admin` : l'exploitant rétablit un
    accès, il ne prend pas la main sur des comptes métier. Un notaire ou un
    responsable conformité ne peut être réinitialisé que par l'admin du cabinet,
    de l'intérieur — l'exploitant reste aveugle aux dossiers (Art. 63).

    Retourne `(email, mot_de_passe_temporaire)`. Le mot de passe n'est stocké
    nulle part en clair : s'il est perdu à nouveau, il faut rappeler ce service.
    """
    async with shared_session() as db:
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            raise ProvisioningError("Cabinet introuvable.")

    context = TenantContext(
        id=tenant.id,
        schema=tenant.schema_name,
        slug=tenant.slug,
        nom=tenant.nom_cabinet,
        statut=tenant.statut,
        key_salt=tenant.key_salt,
        totp_required=tenant.totp_required,
        storage_bucket=tenant.storage_bucket,
    )

    temp_password = _generate_temp_password()
    with tenant_scope(context):
        async with tenant_session(context) as db:
            admin = (
                await db.execute(
                    select(User)
                    .where(User.role == "admin")
                    .order_by(User.created_at.asc())
                )
            ).scalars().first()
            if admin is None:
                raise ProvisioningError(
                    "Ce cabinet n'a aucun compte administrateur à réinitialiser."
                )

            admin.hashed_password = security.hash_password(temp_password)
            admin.must_change_password = True
            # Réactivation implicite : un admin désactivé laisserait le cabinet
            # tout aussi inaccessible qu'un mot de passe perdu.
            admin.is_active = True
            # La 2FA est remise à zéro avec le mot de passe. L'exploitant n'a
            # aucun moyen de vérifier que le porteur du téléphone est toujours
            # la même personne ; conserver le secret TOTP transformerait la
            # réinitialisation en verrou permanent.
            admin.totp_enabled = False
            admin.totp_secret = None
            admin.totp_backup_codes = None
            await db.commit()
            admin_email = admin.email

    async with shared_session() as db:
        db.add(TenantAuditLog(
            tenant_id=tenant_id,
            super_admin_id=super_admin_id,
            action="tenant.admin_password_reset",
            detail=f"Mot de passe et 2FA réinitialisés pour {admin_email}.",
        ))
        await db.commit()

    logger.info("tenant.admin_password_reset", tenant_id=tenant_id, email=admin_email)
    return admin_email, temp_password


async def set_tenant_statut(
    tenant_id: str,
    statut: str,
    *,
    motif: str | None = None,
    super_admin_id: str | None = None,
) -> Tenant:
    """Change le statut d'un cabinet (activation, suspension, archivage).

    C'est le point d'accroche prévu pour un futur portier de facturation : passer
    un cabinet en « suspendu » coupe l'accès sans toucher à ses données.
    """
    from datetime import datetime, timezone

    async with shared_session() as db:
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            raise ProvisioningError("Cabinet introuvable.")

        tenant.statut = statut
        if statut == "production" and tenant.activated_at is None:
            tenant.activated_at = datetime.now(timezone.utc)
        if statut == "suspendu":
            tenant.suspended_at = datetime.now(timezone.utc)
            tenant.motif_suspension = motif
        if statut == "production":
            tenant.motif_suspension = None

        db.add(TenantAuditLog(
            tenant_id=tenant_id,
            super_admin_id=super_admin_id,
            action=f"tenant.statut.{statut}",
            detail=motif,
        ))
        await db.commit()
        await db.refresh(tenant)

    # Le cache de routage doit refléter la coupure sans attendre son TTL.
    tenant_resolver.invalidate(tenant_id)
    return tenant


async def migrate_all_tenants() -> dict[str, str]:
    """Rejoue les migrations métier sur TOUS les cabinets.

    À lancer à chaque déploiement portant une migration : contrairement au
    mono-tenant, `alembic upgrade head` ne suffit plus — il y a une table de
    versions par schéma.
    """
    results: dict[str, str] = {}
    for tenant in await tenant_resolver.list_all_tenants():
        try:
            await _run_alembic(tenant.schema)
            results[tenant.slug] = "ok"
        except ProvisioningError as exc:
            results[tenant.slug] = f"échec : {exc}"
            logger.error("tenant.migration_failed", slug=tenant.slug, schema=tenant.schema)
    return results
