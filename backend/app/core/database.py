"""Couche de persistance PostgreSQL multi-tenant (isolation par schéma).

Topologie :

    Instance PostgreSQL (1 conteneur)
    ├── schéma  shared          ← annuaire de routage, NON métier
    │     ├── tenants           (cabinet, statut, schéma, sel de chiffrement)
    │     ├── tenant_users      (email → cabinet, pour le routage au login)
    │     ├── super_admins      (exploitants plateforme, aveugles au métier)
    │     └── emergency_access_log
    ├── schéma  tenant_<uuid>   ← TOUTES les tables métier du cabinet A
    └── schéma  tenant_<uuid>   ← cabinet B …

Un **seul** engine et un **seul** pool de connexions desservent tous les
cabinets : l'isolation est obtenue en positionnant le `search_path` de chaque
transaction sur le schéma du tenant courant. Le code métier (repositories,
routers, requêtes SQL brutes) reste donc totalement agnostique du multi-tenant
— c'est l'objectif d'architecture central.

Garde-fou : `SET LOCAL` limite la portée du `search_path` à la transaction. Une
connexion rendue au pool ne peut pas emporter le schéma d'un cabinet vers la
requête suivante, qui pourrait appartenir à un autre cabinet.

Note sur les DOS (Art. 63) : le rôle PostgreSQL `dos_user`, à privilèges
restreints (aucun DELETE sur les déclarations de soupçon), est bien créé et
doté de ses droits dans chaque schéma cabinet par `core/dos_privileges.py`. En
revanche l'application ne s'y connecte pas : la session à privilèges réduits qui
existait ici n'était injectée par aucun endpoint. Elle a été retirée plutôt que
laissée en place sans usage. L'append-only reste donc garanti au niveau du SGBD
pour quiconque emprunte ce rôle, mais n'est pas exercé par le code applicatif —
cf. `docs/MIGRATION-SAAS-BILAN.md` §3.1 pour la marche à suivre si l'on veut
l'exercer réellement.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy import MetaData, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.tenant_context import TenantContext, get_current_tenant


class Base(DeclarativeBase):
    """Métier — matérialisé dans chaque schéma `tenant_<id>`.

    Aucun `schema=` n'est déclaré : les tables sont résolues via le `search_path`,
    ce qui permet au même modèle de servir tous les cabinets.
    """


class SharedBase(DeclarativeBase):
    """Annuaire de routage — matérialisé une seule fois dans le schéma `shared`."""

    metadata = MetaData(schema=settings.SHARED_SCHEMA)


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


# Sans cette désactivation, le schéma-par-tenant est tout simplement cassé.
#
# asyncpg met en cache les requêtes préparées côté serveur, avec les OID des
# types résolus au moment de la préparation. Or chaque schéma cabinet possède
# ses PROPRES types ENUM (`user_role_enum`, `statut_dossier_enum`…), et les
# requêtes émises par SQLAlchemy les désignent sans qualification — elles sont
# résolues par le `search_path`.
#
# Une connexion rendue au pool puis réutilisée par un autre cabinet rejouerait
# donc un plan préparé pointant les types du cabinet précédent :
#
#     cannot cast type tenant_a.user_role_enum to user_role_enum
#
# Au mieux une erreur, au pire une lecture erronée. Les deux caches sont donc
# désactivés : celui d'asyncpg (`statement_cache_size`) et celui de l'adaptateur
# SQLAlchemy (`prepared_statement_cache_size`). C'est aussi la configuration
# exigée derrière un pooler transactionnel type PgBouncer.
_NO_STATEMENT_CACHE = {"statement_cache_size": 0, "prepared_statement_cache_size": 0}


@lru_cache(maxsize=1)
def _get_engine():
    url = settings.DB_URL
    kwargs = {"echo": settings.APP_ENV == "development", "pool_pre_ping": not _is_sqlite(url)}
    if not _is_sqlite(url):
        # Dimensionné pour ~100 cabinets actifs : le pool est mutualisé, ce qui
        # est précisément l'avantage du schéma-par-tenant sur la base-par-tenant.
        kwargs.update({"pool_size": 20, "max_overflow": 30, "connect_args": _NO_STATEMENT_CACHE})
    return create_async_engine(url, **kwargs)


def _get_session_factory():
    return async_sessionmaker(_get_engine(), expire_on_commit=False)


def _validate_schema_name(schema: str) -> str:
    """Défense contre l'injection d'identifiant dans le `SET search_path`.

    Le nom vient de la base (`shared.tenants.schema_name`), donc théoriquement sûr,
    mais le `search_path` est le pivot de toute l'isolation : on ne lui fait pas
    confiance sur parole.
    """
    if not schema or not schema.replace("_", "").isalnum():
        raise ValueError(f"Nom de schéma tenant invalide : {schema!r}")
    return schema


def _bind_search_path(session: AsyncSession, schema: str) -> None:
    """Positionne le `search_path` à l'ouverture de CHAQUE transaction de la session.

    On s'accroche à `after_begin` plutôt que d'exécuter un `SET` une seule fois :
    une session peut ouvrir plusieurs transactions successives (commit puis
    nouvelle requête), et `SET LOCAL` est annulé à chaque commit.
    """
    if _is_sqlite(settings.DB_URL):  # tests unitaires — pas de notion de schéma
        return

    @event.listens_for(session.sync_session, "after_begin")
    def _set_search_path(_sess, _transaction, connection):  # pragma: no cover - hook
        connection.exec_driver_sql(
            f'SET LOCAL search_path TO "{schema}", "{settings.SHARED_SCHEMA}"'
        )


async def get_db() -> AsyncSession:
    """Session métier du cabinet courant.

    Signature volontairement inchangée : les `Depends(get_db)` existants basculent
    en multi-tenant sans être touchés. Le tenant provient du `ContextVar` posé par
    `TenantMiddleware` à partir du JWT.
    """
    tenant = get_current_tenant()
    schema = _validate_schema_name(tenant.schema)
    async with _get_session_factory()() as session:
        _bind_search_path(session, schema)
        # Les seuils et pondérations de scoring sont propres au cabinet et lus
        # par du code synchrone : ils doivent être en cache avant que l'endpoint
        # ne s'exécute. Une seule requête, à la première session du cabinet.
        # Import local : `runtime_config` dépend des modèles, qui dépendent de ce
        # module — l'importer au sommet créerait un cycle.
        from app.core import runtime_config

        await runtime_config.ensure_loaded(session)
        yield session


async def get_shared_db() -> AsyncSession:
    """Session sur l'annuaire `shared` — routage au login, console Super-Admin.

    N'expose aucune donnée métier : le `search_path` est restreint à `shared`.
    """
    async with _get_session_factory()() as session:
        _bind_search_path(session, settings.SHARED_SCHEMA)
        yield session


@asynccontextmanager
async def tenant_session(tenant: TenantContext):
    """Session métier d'un cabinet donné, hors requête HTTP.

    Réservé aux traitements qui ne passent pas par le middleware : provisioning,
    scheduler multi-tenant, scripts de migration de données.
    """
    schema = _validate_schema_name(tenant.schema)
    async with _get_session_factory()() as session:
        _bind_search_path(session, schema)
        yield session


@asynccontextmanager
async def shared_session():
    """Session sur l'annuaire, hors requête HTTP."""
    async with _get_session_factory()() as session:
        _bind_search_path(session, settings.SHARED_SCHEMA)
        yield session
