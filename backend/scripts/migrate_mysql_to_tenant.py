"""Reprise des données MySQL mono-tenant → schéma d'un cabinet PostgreSQL.

L'ancienne base MySQL contenait les données d'une seule étude. Elles deviennent
le premier cabinet de la plateforme SaaS : ce script les recopie dans son schéma
`tenant_<uuid>`, en convertissant ce que les deux moteurs ne représentent pas de
la même façon.

    # 1. l'annuaire doit exister
    alembic -c alembic_shared.ini upgrade head

    # 2. reprise (crée le cabinet et son schéma au passage)
    python scripts/migrate_mysql_to_tenant.py \\
        --nom-cabinet "Étude Kouassi & Associés" \\
        --slug kouassi \\
        --contact-email contact@etude-kouassi.ci \\
        --admin-email admin@etude-kouassi.ci

    # à blanc, pour vérifier les volumes avant de s'engager
    python scripts/migrate_mysql_to_tenant.py ... --dry-run

Quatre conversions ne vont PAS de soi et sont la raison d'être de ce script :

1. **Colonnes chiffrées** — elles sont chiffrées dans MySQL avec l'ancienne clé
   globale (SHA-256 de `AES_KEY`), et doivent l'être dans PostgreSQL avec la clé
   propre au cabinet (HKDF). On déchiffre donc à la lecture et on laisse le type
   `EncryptedString` rechiffrer à l'écriture. Sans cette étape, les données
   seraient illisibles après bascule.
2. **Booléens** — `TINYINT(1)` (0/1) → `BOOLEAN` : PostgreSQL refuse l'entier.
3. **Horodatages** — MySQL renvoie des datetimes naïfs ; les colonnes cibles sont
   `TIMESTAMPTZ`. On les qualifie en UTC, ce que l'application supposait déjà.
4. **JSON** — le pilote MySQL renvoie une chaîne là où `JSONB` attend une
   structure.

Le script est **idempotent au niveau du cabinet** : il refuse de s'exécuter si
le schéma cible contient déjà des données, plutôt que de créer des doublons.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Boolean, DateTime, Numeric, func, insert, select
from sqlalchemy.dialects.postgresql import JSONB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.models  # noqa: F401  — peuple Base.metadata
from app.core.crypto import _PREFIX
from app.core.database import Base, shared_session, tenant_session
from app.core.tenant_context import TenantContext, tenant_scope
from app.models.shared import Tenant
from app.services import tenant_provisioning

# Tables volontairement exclues : elles sont reconstruites par le provisioning
# ou n'existaient pas dans le schéma MySQL.
_SKIP_TABLES = {"alembic_version"}


# ── Source MySQL ─────────────────────────────────────────────────────────────

def _mysql_connection():
    """Connexion à l'ancienne base. `pymysql` n'est requis que par ce script.

    Le pilote MySQL a été retiré des dépendances de l'application : la reprise
    est une opération ponctuelle, pas une capacité permanente du produit.
    """
    try:
        import pymysql
    except ImportError:
        print(
            "pymysql absent. Installez les dépendances de reprise :\n"
            "    pip install -r requirements-migration.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    return pymysql.connect(
        host=os.environ.get("LEGACY_MYSQL_HOST", "localhost"),
        port=int(os.environ.get("LEGACY_MYSQL_PORT", "3306")),
        user=os.environ["LEGACY_MYSQL_USER"],
        password=os.environ["LEGACY_MYSQL_PASSWORD"],
        database=os.environ.get("LEGACY_MYSQL_DATABASE", "notaire_lbcft"),
        charset="utf8mb4",
        cursorclass=__import__("pymysql").cursors.DictCursor,
    )


def _legacy_fernet() -> Fernet:
    """Clé de déchiffrement de l'ancienne base : SHA-256 de `AES_KEY`.

    C'est exactement la dérivation qu'appliquait `crypto.py` avant la migration.
    Elle est reproduite ici, et nulle part ailleurs, pour que le code applicatif
    n'ait plus à connaître l'ancien schéma de clés.
    """
    legacy_key = os.environ.get("LEGACY_AES_KEY") or os.environ.get("AES_KEY")
    if not legacy_key:
        print("LEGACY_AES_KEY (ou AES_KEY) requis pour déchiffrer l'ancienne base.", file=sys.stderr)
        sys.exit(1)
    digest = hashlib.sha256(legacy_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


# ── Conversions de valeurs ───────────────────────────────────────────────────

def _decrypt_legacy(value, fernet: Fernet, table: str, column: str):
    """Ramène une colonne chiffrée en clair, pour permettre son rechiffrement."""
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    if not text.startswith(_PREFIX):
        return text  # donnée historique restée en clair
    try:
        return fernet.decrypt(text[len(_PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        print(
            f"  ⚠️  {table}.{column} : déchiffrement impossible avec LEGACY_AES_KEY — "
            "valeur conservée telle quelle, à vérifier manuellement.",
            file=sys.stderr,
        )
        return text


def _convert(value, column, fernet: Fernet, table_name: str):
    """Adapte une valeur MySQL au type PostgreSQL cible."""
    if value is None:
        return None

    type_ = column.type

    # Colonnes chiffrées : déchiffrées ici, rechiffrées par le type à l'insertion.
    if type_.__class__.__name__ == "EncryptedString":
        return _decrypt_legacy(value, fernet, table_name, column.name)

    if isinstance(type_, Boolean):
        # MySQL stocke les booléens en TINYINT(1) : PostgreSQL exige un vrai bool.
        return bool(value)

    if isinstance(type_, DateTime) and isinstance(value, datetime) and value.tzinfo is None:
        # MySQL ignorait `timezone=True` et renvoyait des datetimes naïfs ;
        # l'application les a toujours écrits en UTC.
        return value.replace(tzinfo=timezone.utc)

    if isinstance(type_, JSONB) and isinstance(value, (str, bytes)):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None

    if isinstance(type_, Numeric) and isinstance(value, float):
        return Decimal(str(value))

    return value


# ── Reprise ──────────────────────────────────────────────────────────────────

async def verifier_collisions_emails() -> list[tuple[str, str]]:
    """Détecte, AVANT toute écriture, les emails déjà rattachés à un autre cabinet.

    L'email est unique au niveau plateforme — c'est ce qui permet de router une
    connexion sans demander son cabinet à l'utilisateur. Une collision est donc
    bloquante : l'utilisateur repris ne pourrait pas se connecter.

    Ce contrôle est en tête de course parce que la découvrir en fin de reprise
    laisse un cabinet à moitié peuplé : données présentes, annuaire incomplet,
    personne ne peut entrer. Mieux vaut ne rien avoir écrit.
    """
    connection = _mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT email FROM `users`")
            emails = [r["email"].strip().lower() for r in cursor.fetchall() if r.get("email")]
    finally:
        connection.close()

    if not emails:
        return []

    from app.models.shared import Tenant, TenantUser

    collisions: list[tuple[str, str]] = []
    async with shared_session() as db:
        rows = (await db.execute(
            select(TenantUser, Tenant.slug)
            .join(Tenant, Tenant.id == TenantUser.tenant_id)
            .where(TenantUser.email.in_(emails))
        )).all()
        collisions = [(r[0].email, r[1]) for r in rows]
    return collisions


def inventorier_source() -> dict[str, int]:
    """Compte les lignes de l'ancienne base, table par table.

    Sert au `--dry-run` : l'exploitant relève ces volumes AVANT la bascule et les
    repasse ensuite à `verifier_reprise.py --attendu`, ce qui rend le contrôle
    d'après-reprise réellement opposable au lieu d'être auto-référentiel.
    """
    connection = _mysql_connection()
    inventaire: dict[str, int] = {}
    try:
        for table in Base.metadata.sorted_tables:
            if table.name in _SKIP_TABLES:
                continue
            with connection.cursor() as cursor:
                try:
                    cursor.execute(f"SELECT COUNT(*) AS n FROM `{table.name}`")
                    inventaire[table.name] = cursor.fetchone()["n"]
                except Exception:
                    # Table absente de l'ancienne base (ajoutée depuis).
                    inventaire[table.name] = 0
    finally:
        connection.close()
    return inventaire


async def _assert_target_empty(context: TenantContext) -> None:
    """Refuse d'écrire dans un schéma déjà peuplé — mieux vaut échouer que doublonner."""
    from app.models.user import User

    async with tenant_session(context) as db:
        count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    if count > 1:  # 1 = le compte admin créé par le provisioning
        raise SystemExit(
            f"Le schéma {context.schema} contient déjà {count} utilisateurs. "
            "Reprise annulée pour ne pas créer de doublons."
        )


async def copy_tables(context: TenantContext, *, dry_run: bool, batch_size: int = 500) -> dict[str, int]:
    """Recopie toutes les tables métier, dans l'ordre des dépendances de clés étrangères."""
    fernet = _legacy_fernet()
    connection = _mysql_connection()
    counts: dict[str, int] = {}

    try:
        with tenant_scope(context):
            for table in Base.metadata.sorted_tables:
                if table.name in _SKIP_TABLES:
                    continue

                with connection.cursor() as cursor:
                    try:
                        cursor.execute(f"SELECT * FROM `{table.name}`")
                    except Exception as exc:
                        # Table absente de l'ancienne base (ajoutée depuis) : rien à reprendre.
                        print(f"  · {table.name:<28} ignorée ({exc.__class__.__name__})")
                        counts[table.name] = 0
                        continue
                    rows = cursor.fetchall()

                if not rows:
                    counts[table.name] = 0
                    continue

                known = {c.name for c in table.columns}
                payload = [
                    {
                        name: _convert(value, table.columns[name], fernet, table.name)
                        for name, value in row.items()
                        if name in known
                    }
                    for row in rows
                ]

                counts[table.name] = len(payload)
                if dry_run:
                    print(f"  · {table.name:<28} {len(payload):>6} lignes (simulation)")
                    continue

                async with tenant_session(context) as db:
                    for start in range(0, len(payload), batch_size):
                        await db.execute(insert(table), payload[start : start + batch_size])
                    await db.commit()
                print(f"  · {table.name:<28} {len(payload):>6} lignes reprises")
    finally:
        connection.close()

    return counts


async def rebuild_directory(context: TenantContext) -> int:
    """Réinscrit tous les utilisateurs repris dans l'annuaire de routage.

    Sans cette étape, les comptes existeraient dans le schéma du cabinet mais
    `/auth/login` ne saurait pas vers quel cabinet router leur email : personne
    ne pourrait se connecter.
    """
    from app.models.user import User
    from app.services import tenant_directory

    with tenant_scope(context):
        async with tenant_session(context) as db:
            users = (await db.execute(select(User))).scalars().all()
            for user in users:
                await tenant_directory.register(user.email, user.id, is_active=user.is_active)
    return len(users)


def migrate_storage(context: TenantContext, *, dry_run: bool) -> int:
    """Recopie les objets du bucket unique historique vers celui du cabinet.

    Les `minio_key` stockés en base restent identiques : seul le bucket change.
    """
    from minio.commonconfig import CopySource

    from app.core.storage import ensure_tenant_bucket, get_minio_client

    legacy_bucket = os.environ.get("LEGACY_MINIO_BUCKET", "notaire-documents")
    client = get_minio_client()

    if not client.bucket_exists(legacy_bucket):
        print(f"  · bucket historique « {legacy_bucket} » absent — rien à reprendre")
        return 0

    target = context.storage_bucket
    if not dry_run:
        ensure_tenant_bucket(target)

    copied = 0
    for obj in client.list_objects(legacy_bucket, recursive=True):
        if not dry_run:
            client.copy_object(target, obj.object_name, CopySource(legacy_bucket, obj.object_name))
        copied += 1
    print(f"  · {copied} objet(s) {'à copier' if dry_run else 'copiés'} → {target}")
    return copied


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--nom-cabinet", required=True)
    parser.add_argument("--contact-email", required=True)
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--slug", default=None)
    parser.add_argument("--admin-first-name", default="Admin")
    parser.add_argument("--admin-last-name", default="Cabinet")
    parser.add_argument("--numero-agrement", default=None)
    parser.add_argument("--existing-tenant-id", default=None,
                        help="Reprendre vers un cabinet déjà provisionné plutôt que d'en créer un.")
    parser.add_argument("--skip-storage", action="store_true", help="Ne pas recopier les documents MinIO.")
    parser.add_argument("--dry-run", action="store_true", help="Compter sans écrire.")
    args = parser.parse_args()

    # ── Contrôle préalable : aucune écriture avant d'être sûr d'aboutir ──────
    collisions = await verifier_collisions_emails()
    if collisions:
        print("\nReprise refusée — adresses déjà rattachées à un autre cabinet :", file=sys.stderr)
        for email, slug in collisions:
            print(f"  · {email}  →  cabinet « {slug} »", file=sys.stderr)
        print(
            "\nL'email identifie le cabinet au moment de la connexion : il ne peut "
            "appartenir qu'à un seul.\nSupprimez ou renommez le cabinet concerné, puis "
            "relancez. Aucune donnée n'a été écrite.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    # ── Cabinet cible ────────────────────────────────────────────────────────
    if args.existing_tenant_id:
        async with shared_session() as db:
            tenant = await db.get(Tenant, args.existing_tenant_id)
        if tenant is None:
            raise SystemExit(f"Cabinet {args.existing_tenant_id} introuvable.")
        temp_password = None
    elif args.dry_run:
        # Simulation SANS cabinet : c'est le cas d'usage réel d'un `--dry-run`,
        # celui qu'on veut avant la toute première reprise. Exiger un cabinet
        # existant rendait l'option inutilisable au moment où elle sert le plus.
        print("→ Simulation — aucun cabinet créé, aucune écriture\n")
        inventaire = inventorier_source()
        total = sum(inventaire.values())
        print("── Volumétrie de la source ──────────────────────────────────")
        for table, n in sorted(inventaire.items(), key=lambda kv: (-kv[1], kv[0])):
            if n:
                print(f"  · {table:<28} {n:>6}")
        vides = [t for t, n in inventaire.items() if not n]
        if vides:
            print(f"  ({len(vides)} table(s) vide(s))")
        print(f"\n  total : {total} lignes")
        print(
            "\n  Aucune collision d'adresses détectée : la reprise peut être lancée "
            "sans --dry-run."
        )
        return
    else:
        print("→ Provisioning du cabinet cible…")
        result = await tenant_provisioning.provision_tenant(
            nom_cabinet=args.nom_cabinet,
            slug=args.slug,
            contact_email=args.contact_email,
            admin_email=args.admin_email,
            admin_first_name=args.admin_first_name,
            admin_last_name=args.admin_last_name,
            numero_agrement=args.numero_agrement,
        )
        tenant = result.tenant
        temp_password = result.admin_temp_password

    context = TenantContext(
        id=tenant.id, schema=tenant.schema_name, slug=tenant.slug, nom=tenant.nom_cabinet,
        statut=tenant.statut, key_salt=tenant.key_salt, totp_required=tenant.totp_required,
        storage_bucket=tenant.storage_bucket,
    )

    if not args.dry_run:
        await _assert_target_empty(context)

    print(f"\n→ Reprise des données vers {context.schema}")
    counts = await copy_tables(context, dry_run=args.dry_run)

    if not args.dry_run:
        registered = await rebuild_directory(context)
        print(f"\n→ Annuaire : {registered} utilisateur(s) rattaché(s) au cabinet")

    if not args.skip_storage:
        print("\n→ Documents")
        migrate_storage(context, dry_run=args.dry_run)

    total = sum(counts.values())
    print("\n" + "=" * 72)
    print(f"{'SIMULATION' if args.dry_run else 'REPRISE TERMINÉE'} — {total} lignes, cabinet « {tenant.nom_cabinet} »")
    print(f"  schéma : {tenant.schema_name}")
    print(f"  statut : {tenant.statut}")
    if temp_password:
        print(f"  admin  : {args.admin_email} / {temp_password}")
    if tenant.statut != "production":
        print("\n  Le cabinet est en « configuration » : activez-le depuis la console")
        print("  Super-Admin pour autoriser les connexions.")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
