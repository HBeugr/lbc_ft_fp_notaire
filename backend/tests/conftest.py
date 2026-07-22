"""Fixtures pytest — suite notaire SaaS multi-tenant.

Les tests tournent désormais sur un **PostgreSQL réel**, et non plus sur SQLite
en mémoire. Ce n'est pas un luxe : l'isolation repose entièrement sur les
schémas PostgreSQL et le `search_path`, deux notions que SQLite ignore. Une
suite SQLite validerait une application qui fuit en production.

Deux cabinets sont provisionnés pour la session (`tenant_a`, `tenant_b`), ce qui
permet de vérifier qu'aucun endpoint ne laisse filtrer les données de l'un vers
l'autre.

Les requêtes passent par la vraie pile ASGI, middleware de résolution de cabinet
compris : `get_db` n'est plus surchargé, sans quoi les tests court-circuiteraient
précisément le mécanisme qu'ils doivent éprouver.

Prérequis : PostgreSQL, Redis et MinIO accessibles. Les valeurs par défaut
ci-dessous correspondent aux ports publiés par `docker-compose.dev.yml` :

    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db redis storage
    pytest

Toute variable d'environnement déjà définie l'emporte, ce qui permet de viser
une autre instance sans toucher au fichier.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Configuration de test ────────────────────────────────────────────────────
#
# Les identifiants (mots de passe, clés) proviennent du `.env` du projet : les
# recopier ici les ferait diverger silencieusement à la première rotation, et la
# suite échouerait sur une erreur d'authentification difficile à relier à sa
# cause. Seul l'ADRESSAGE est surchargé — depuis l'hôte, les services ne
# s'atteignent pas par leur nom de conteneur (`db`, `redis`, `storage`) mais par
# les ports publiés par `docker-compose.dev.yml` :
#
#     docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db redis storage
#     alembic -c alembic_shared.ini upgrade head
#     pytest
#
# Toute variable déjà présente dans l'environnement l'emporte sur tout le reste.

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def _charger_env_projet() -> None:
    """Reprend les valeurs du `.env` du projet comme base de configuration."""
    if not _ENV_FILE.exists():
        return
    for ligne in _ENV_FILE.read_text().splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


_charger_env_projet()

# Adressage depuis l'hôte — remplace les noms de conteneurs du `.env`.
os.environ["DB_HOST"] = os.environ.get("TEST_DB_HOST", "localhost")
os.environ["DB_PORT"] = os.environ.get("TEST_DB_PORT", "5434")
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://localhost:6389/0")
os.environ["MINIO_ENDPOINT"] = os.environ.get("TEST_MINIO_ENDPOINT", "localhost:9020")

# Repli si aucun `.env` n'est présent (intégration continue sur base vierge).
os.environ.setdefault("DB_NAME", "notaire_lbcft")
os.environ.setdefault("DB_USER", "notaire_user")
os.environ.setdefault("DB_PASSWORD", "notaire_dev_password")
os.environ.setdefault("DOS_DB_USER", "dos_user")
os.environ.setdefault("DOS_DB_PASSWORD", "dos_test_password")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")

# Secrets propres aux tests : jamais ceux du projet, pour qu'un jeton ou une
# donnée chiffrée de test ne soit pas exploitable ailleurs.
os.environ["JWT_SECRET"] = "test_secret_at_least_32_characters_ok!"
os.environ["AES_KEY"] = "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGU="
os.environ["TENANT_MASTER_KEY"] = "test-master-key-for-tenant-derivation"
os.environ["APP_ENV"] = "test"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Chargé en premier et sous alias : un `import app.models` en fin de bloc
# relierait le nom `app` au PAQUET et écraserait l'instance FastAPI importée
# ci-dessous — l'application deviendrait alors un module non appelable.
from app import models as _models  # noqa: F401  — peuple les métadonnées

from app.core import security, tenant_resolver
from app.core.database import shared_session, tenant_session
from app.core.tenant_context import TenantContext, set_current_tenant, tenant_scope
from app.main import app
from app.models.shared import Tenant
from app.services import tenant_provisioning


def _context(tenant: Tenant) -> TenantContext:
    return TenantContext(
        id=tenant.id, schema=tenant.schema_name, slug=tenant.slug, nom=tenant.nom_cabinet,
        statut=tenant.statut, key_salt=tenant.key_salt, totp_required=tenant.totp_required,
        storage_bucket=tenant.storage_bucket,
    )


async def _provision(label: str) -> TenantContext:
    """Provisionne un cabinet de test, immédiatement en production."""
    suffix = uuid.uuid4().hex[:8]
    result = await tenant_provisioning.provision_tenant(
        nom_cabinet=f"Cabinet Test {label} {suffix}",
        slug=f"test-{label}-{suffix}",
        contact_email=f"contact-{label}-{suffix}@test.ci",
        admin_email=f"admin-{label}-{suffix}@test.ci",
        admin_first_name="Admin",
        admin_last_name=label.upper(),
        totp_required=False,
    )
    tenant = await tenant_provisioning.set_tenant_statut(result.tenant.id, "production")
    return _context(tenant)


def _drop_bucket(context: TenantContext) -> None:
    """Supprime le bucket du cabinet de test.

    Sans cela chaque exécution laisse un bucket orphelin : le stockage local
    (et celui de l'intégration continue) se remplit de cabinets fantômes.
    """
    try:
        from app.core.storage import bucket_for, get_minio_client

        client = get_minio_client()
        bucket = bucket_for(context)
        if client.bucket_exists(bucket):
            for obj in client.list_objects(bucket, recursive=True):
                client.remove_object(bucket, obj.object_name)
            client.remove_bucket(bucket)
    except Exception:
        # Le nettoyage ne doit jamais faire échouer une suite par ailleurs verte.
        pass


async def _teardown(context: TenantContext) -> None:
    """Supprime le schéma du cabinet, son bucket et sa trace dans l'annuaire."""
    _drop_bucket(context)
    async with shared_session() as db:
        await db.execute(text(f'DROP SCHEMA IF EXISTS "{context.schema}" CASCADE'))
        await db.execute(
            text("DELETE FROM shared.tenant_users WHERE tenant_id = :tid"), {"tid": context.id}
        )
        await db.execute(
            text("DELETE FROM shared.tenant_audit_log WHERE tenant_id = :tid"), {"tid": context.id}
        )
        await db.execute(text("DELETE FROM shared.tenants WHERE id = :tid"), {"tid": context.id})
        await db.commit()
    tenant_resolver.invalidate()


# Cabinet servi par défaut quand un test ne précise rien. Évite d'imposer la
# fixture `tenant_a` aux tests fonctionnels historiques, qui ne se préoccupent
# pas du multi-tenant.
_DEFAULT_TENANT: TenantContext | None = None


# Préfixe des cabinets créés par la suite : sert aussi à repérer les résidus.
_PREFIXE_TEST = "test-"


# Un cabinet de test n'est considéré orphelin qu'au-delà de cet âge. Voir
# `_purger_cabinets_orphelins` : c'est ce délai qui distingue un résidu d'une
# exécution tuée d'un cabinet appartenant à une suite en cours d'exécution.
_AGE_ORPHELIN = timedelta(minutes=30)


async def _purger_cabinets_orphelins() -> None:
    """Supprime les cabinets de test laissés par une exécution interrompue.

    Sans ce ménage, la suite n'est pas rejouable : l'email d'un utilisateur est
    unique au niveau PLATEFORME (c'est ce qui permet le routage au login), donc
    un résidu dans `shared.tenant_users` fait échouer en 409 toute création
    d'utilisateur réutilisant la même adresse. Le teardown de session ne suffit
    pas : il ne s'exécute pas si le processus est tué (timeout, Ctrl-C).

    Le filtre d'ÂGE n'est pas une optimisation : sans lui, deux exécutions
    simultanées de la suite (plusieurs fichiers de recette lancés en parallèle,
    ou une intégration continue à plusieurs agents) se détruisent mutuellement.
    La seconde purgerait les cabinets fraîchement provisionnés par la première,
    dont les tests échoueraient alors sur des schémas disparus — un échec
    spectaculaire, massif, et sans aucun rapport avec le code testé. On ne
    supprime donc que les cabinets assez vieux pour ne pouvoir appartenir
    qu'à une exécution morte.
    """
    seuil = datetime.now(timezone.utc) - _AGE_ORPHELIN
    async with shared_session() as db:
        orphelins = (await db.execute(
            select(Tenant).where(
                Tenant.slug.like(f"{_PREFIXE_TEST}%"),
                Tenant.created_at < seuil,
            )
        )).scalars().all()
        contextes = [_context(t) for t in orphelins]

    for contexte in contextes:
        await _teardown(contexte)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def tenants() -> tuple[TenantContext, TenantContext]:
    """Deux cabinets distincts, pour éprouver l'étanchéité entre eux."""
    global _DEFAULT_TENANT
    await _purger_cabinets_orphelins()
    a = await _provision("a")
    b = await _provision("b")
    _DEFAULT_TENANT = a
    yield a, b
    _DEFAULT_TENANT = None
    await _teardown(a)
    await _teardown(b)


@pytest_asyncio.fixture(loop_scope="session")
async def tenant_a(tenants) -> TenantContext:
    return tenants[0]


@pytest_asyncio.fixture(loop_scope="session")
async def tenant_b(tenants) -> TenantContext:
    return tenants[1]


@pytest_asyncio.fixture(loop_scope="session")
async def db(tenant_a) -> AsyncSession:
    """Session métier sur le cabinet A — cabinet par défaut des tests."""
    async with tenant_session(tenant_a) as session:
        session.info["tenant"] = tenant_a
        # Le cabinet par défaut est aussi posé dans le ContextVar, pour les tests
        # qui manipulent directement des modèles à colonnes chiffrées.
        # Volontairement sans `reset` : pytest exécute setup et teardown dans
        # deux contextes distincts, et rendre le jeton depuis l'autre lèverait
        # « Token was created in a different Context ».
        set_current_tenant(tenant_a)
        yield session


@pytest_asyncio.fixture(loop_scope="session")
async def db_b(tenant_b) -> AsyncSession:
    """Session métier sur le cabinet B.

    Ne touche pas au ContextVar global : les helpers se placent eux-mêmes dans
    le bon cabinet à partir de `session.info["tenant"]`, ce qui permet à un test
    d'utiliser les deux cabinets sans que l'ordre des fixtures ne compte.
    """
    async with tenant_session(tenant_b) as session:
        session.info["tenant"] = tenant_b
        yield session


def _scope_of(db: AsyncSession):
    """Contexte du cabinet auquel appartient une session de test."""
    return tenant_scope(db.info.get("tenant") or _DEFAULT_TENANT)


@pytest_asyncio.fixture(loop_scope="session")
async def client(tenants):
    """Client HTTP sur la vraie pile ASGI.

    Aucun `dependency_overrides` : le cabinet est résolu par le middleware à
    partir du jeton, exactement comme en production.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Helpers de seed ───────────────────────────────────────────────────────────

async def create_user(db: AsyncSession, role: str = "responsable_conformite", **kwargs):
    """Crée un utilisateur dans le cabinet de la session `db` et l'inscrit à l'annuaire."""
    from app.models.user import User
    from app.services import tenant_directory

    defaults = dict(
        id=str(uuid.uuid4()),
        email=f"u_{uuid.uuid4().hex[:8]}@test.ci",
        hashed_password=security.hash_password("TestPass123!"),
        first_name="Test", last_name="User",
        role=role, is_active=True, totp_enabled=False, must_change_password=False,
    )
    user = User(**{**defaults, **kwargs})
    with _scope_of(db):
        db.add(user)
        await db.commit()
        await db.refresh(user)
        # Sans inscription à l'annuaire, l'utilisateur ne pourrait pas se
        # connecter : les tests de login seraient faussement rouges.
        await tenant_directory.register(user.email, user.id)
    return user


async def create_dossier(db: AsyncSession, created_by: str, **kwargs):
    from app.models.dossier import Dossier
    defaults = dict(
        id=str(uuid.uuid4()),
        reference=f"KYC-{uuid.uuid4().hex[:8].upper()}",
        type_client="PP", type_operation="vente_immobiliere",
        statut="en_analyse", created_by=created_by, assigned_to=None,
    )
    dossier = Dossier(**{**defaults, **kwargs})
    with _scope_of(db):
        db.add(dossier)
        await db.commit()
        await db.refresh(dossier)
    return dossier


async def create_alerte(db: AsyncSession, **kwargs):
    from app.models.alerte import Alerte
    defaults = dict(
        id=str(uuid.uuid4()), dossier_id=None,
        type_alerte="INCOHERENCE_DOC", niveau="MOYEN", statut="ouverte",
        description="Alerte de test",
    )
    alerte = Alerte(**{**defaults, **kwargs})
    with _scope_of(db):
        db.add(alerte)
        await db.commit()
        await db.refresh(alerte)
    return alerte


def auth_headers(user, tenant: TenantContext | None = None) -> dict:
    """Jeton d'un utilisateur DANS un cabinet donné (A par défaut).

    Le claim `tid` est obligatoire : c'est lui qui indique au middleware quel
    schéma servir. Un jeton sans `tid` est rejeté — comportement volontaire,
    vérifié par les tests d'isolation.
    """
    tenant = tenant or _DEFAULT_TENANT
    assert tenant is not None, "la fixture `tenants` doit être active"
    token = security.create_access_token(
        user.id, extra={"role": user.role, "totp_pending": False, "tid": tenant.id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers_a(tenant_a):
    """Fabrique de jetons pour le cabinet A."""
    return lambda user: auth_headers(user, tenant_a)


@pytest.fixture
def headers_b(tenant_b):
    """Fabrique de jetons pour le cabinet B."""
    return lambda user: auth_headers(user, tenant_b)
