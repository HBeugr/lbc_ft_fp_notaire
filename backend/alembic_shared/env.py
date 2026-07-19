"""Environnement Alembic de l'ANNUAIRE (schéma `shared`).

Cet environnement ne gère que les tables de routage et d'exploitation : cabinets,
aiguillage email → cabinet, comptes Super-Admin, journal d'exploitation. Aucune
donnée métier LBC/FT n'y figure.

Il est joué **une seule fois** par déploiement :

    alembic -c alembic_shared.ini upgrade head

alors que `alembic/` est rejoué une fois par cabinet. Séparer les deux évite
qu'une migration de l'annuaire ne soit répétée N fois, et qu'une migration
métier ne touche l'annuaire.
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
from app.core.database import SharedBase  # noqa: E402

import app.models.shared  # noqa: F401,E402  — peuple SharedBase.metadata

config = context.config
config.set_main_option("sqlalchemy.url", settings.DB_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SharedBase.metadata
SCHEMA = settings.SHARED_SCHEMA


def _include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Ne considère que l'annuaire : les schémas cabinet ne regardent pas ici."""
    if type_ == "table":
        return getattr(obj, "schema", None) == SCHEMA
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_object=_include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
    connection.commit()

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
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
