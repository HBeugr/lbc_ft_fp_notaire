"""Environnement Alembic des schémas CABINET (métier).

Ces migrations ne sont jamais jouées une seule fois : elles sont rejouées
**schéma par schéma**, une fois par cabinet. Le schéma cible est passé en
argument :

    alembic -x schema=tenant_<uuid> upgrade head

Chaque schéma porte sa propre table `alembic_version`, si bien qu'un cabinet
provisionné hier et un cabinet provisionné l'an dernier peuvent se trouver à des
révisions différentes le temps d'un déploiement progressif.

Les tables de l'annuaire (`shared`) sont gérées par un environnement distinct,
`alembic_shared/` : les deux cycles de vie sont indépendants.
"""
import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402

import app.models  # noqa: F401,E402  — peuple Base.metadata (tous les modèles)

config = context.config
config.set_main_option("sqlalchemy.url", settings.DB_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _target_schema() -> str:
    """Schéma cabinet ciblé par cette exécution.

    Défaut : un schéma gabarit, qui permet de générer les migrations
    (`--autogenerate`) sans avoir à provisionner un vrai cabinet.
    """
    return context.get_x_argument(as_dictionary=True).get("schema", "tenant_template")


def _include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Exclut l'annuaire du périmètre : il a son propre environnement."""
    if type_ == "table" and getattr(obj, "schema", None) == settings.SHARED_SCHEMA:
        return False
    return True


def run_migrations_offline() -> None:
    schema = _target_schema()
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=schema,
        include_schemas=False,
        include_object=_include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    schema = _target_schema()
    # Le schéma doit exister avant que la table de versions n'y soit créée : un
    # `alembic upgrade` sur un cabinet fraîchement créé doit être autosuffisant.
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    connection.execute(text(f'SET search_path TO "{schema}"'))
    connection.commit()

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=schema,
        include_schemas=False,
        include_object=_include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
