"""Privilèges du rôle DOS — confidentialité des déclarations de soupçon (Art. 63).

Traduction PostgreSQL de l'ADR-003 : un rôle dédié `dos_user` ne dispose que de
SELECT/INSERT/UPDATE sur `declarations_suspicion` et SELECT/INSERT sur
`dos_addendums`. Aucun DELETE nulle part — le caractère append-only des
déclarations est ainsi garanti par le SGBD et non par l'applicatif, donc
insensible à un bug ou à un contournement du code.

En multi-tenant, ces privilèges doivent être posés **dans chaque schéma
cabinet** : au démarrage pour les cabinets existants, et au provisioning pour
chaque nouveau cabinet — sans quoi un cabinet créé entre deux redémarrages
resterait sans cloisonnement DOS jusqu'au redéploiement suivant.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger


_SQL_ECHO_LOGGERS = ("sqlalchemy.engine", "sqlalchemy.engine.Engine")


@contextmanager
def _muted_sql_echo():
    """Neutralise l'écho SQL le temps d'exécuter du DDL portant un secret.

    Relever le niveau des journaux ne suffit pas : sous `echo=True`, SQLAlchemy
    passe par un `InstanceLogger` qui consulte son propre drapeau `echo` et
    court-circuite le niveau effectif du logger. Il faut donc éteindre l'écho
    sur le moteur lui-même — les niveaux sont ajustés en complément, pour le cas
    où l'écho serait activé par configuration de journalisation plutôt que par
    le drapeau du moteur.
    """
    from app.core.database import _get_engine

    engine = _get_engine()
    previous_echo = engine.echo
    previous_levels = [(logging.getLogger(n), logging.getLogger(n).level) for n in _SQL_ECHO_LOGGERS]

    engine.echo = False
    for log, _ in previous_levels:
        log.setLevel(logging.WARNING)
    try:
        yield
    finally:
        engine.echo = previous_echo
        for log, level in previous_levels:
            log.setLevel(level)


def _valid_identifier(name: str) -> bool:
    return bool(name) and name.replace("_", "").isalnum()


def _quote_literal(value: str) -> str:
    """Échappe un littéral SQL.

    PostgreSQL n'admet **aucun paramètre lié dans du DDL** : `ALTER ROLE … PASSWORD $1`
    est une erreur de syntaxe. Le mot de passe doit donc être écrit en littéral,
    et échappé ici. Le doublement des apostrophes est l'échappement standard, et
    `standard_conforming_strings` (actif par défaut) garantit que les
    antislashs restent littéraux — il n'y a pas d'autre séquence d'échappement à
    neutraliser.
    """
    return "'" + value.replace("'", "''") + "'"


async def ensure_role(db: AsyncSession) -> bool:
    """Crée ou met à jour le rôle DOS. Retourne False si la configuration est invalide."""
    role = settings.DOS_DB_USER
    if not _valid_identifier(role):
        logger.warning("dos.grants_skipped", reason="nom de rôle invalide", role=role)
        return False

    # Garde-fou : si `DOS_DB_USER` vaut le rôle applicatif, deux choses graves se
    # produisent. D'abord la séparation de privilèges de l'ADR-003 est annulée —
    # le rôle « restreint » est en fait le superutilisateur, donc DELETE sur les
    # DOS redevient possible. Ensuite, l'`ALTER ROLE` ci-dessous réinitialiserait
    # le mot de passe du compte applicatif avec `DOS_DB_PASSWORD` : si les deux
    # divergent, l'application se verrouille hors de sa propre base au prochain
    # redémarrage. On refuse plutôt que de « faire au mieux ».
    if role == settings.DB_USER:
        logger.error(
            "dos.grants_skipped",
            reason="DOS_DB_USER est identique à DB_USER — séparation de privilèges "
                   "annulée (ADR-003, Art. 63). Configurez un rôle dédié.",
            role=role,
        )
        return False

    # Le DDL de rôle porte un mot de passe en clair (PostgreSQL n'admet aucun
    # paramètre lié ici). On coupe l'écho SQL le temps de ces deux instructions :
    # sous `echo=True` (APP_ENV=development), elles seraient recopiées telles
    # quelles dans les journaux, mot de passe compris.
    #
    # Les deux noms de journaux sont neutralisés : `echo=True` agit sur
    # `sqlalchemy.engine.Engine`, et régler le seul parent `sqlalchemy.engine`
    # ne suffit pas — un niveau posé explicitement sur l'enfant l'emporte.
    with _muted_sql_echo():
        # `CREATE ROLE` n'admet pas `IF NOT EXISTS` : il faut un bloc conditionnel.
        await db.execute(text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {_quote_literal(role)}) THEN
                    CREATE ROLE "{role}" LOGIN;
                END IF;
            END
            $$;
        """))
        await db.execute(text(
            f'ALTER ROLE "{role}" WITH LOGIN PASSWORD {_quote_literal(settings.DOS_DB_PASSWORD)}'
        ))
    return True


async def grant_on_schema(db: AsyncSession, schema: str) -> None:
    """Applique les privilèges DOS restreints sur un schéma cabinet."""
    role = settings.DOS_DB_USER
    if not _valid_identifier(schema) or not _valid_identifier(role):
        return
    await db.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"'))
    await db.execute(text(
        f'GRANT SELECT, INSERT, UPDATE ON "{schema}".declarations_suspicion TO "{role}"'
    ))
    await db.execute(text(
        f'GRANT SELECT, INSERT ON "{schema}".dos_addendums TO "{role}"'
    ))


async def apply_to_tenant(schema: str) -> None:
    """Pose le rôle et ses privilèges sur un cabinet — appelé au provisioning."""
    from app.core.database import shared_session

    try:
        async with shared_session() as db:
            if await ensure_role(db):
                await grant_on_schema(db, schema)
                await db.commit()
                logger.info("dos.grants_applied", schema=schema)
    except Exception as exc:
        # Non bloquant : un cabinet reste utilisable sans le rôle DOS dédié, la
        # confidentialité restant assurée par le RBAC applicatif. On trace pour
        # que l'exploitant puisse régulariser.
        logger.warning("dos.grants_failed", schema=schema, error=str(exc))


async def apply_to_all_tenants() -> None:
    """Rejoue les privilèges sur tous les cabinets — appelé au démarrage de l'API."""
    from app.core import tenant_resolver
    from app.core.database import shared_session

    try:
        async with shared_session() as db:
            if not await ensure_role(db):
                return
            for tenant in await tenant_resolver.list_all_tenants():
                await grant_on_schema(db, tenant.schema)
            await db.commit()
        logger.info("dos.grants_applied", user=settings.DOS_DB_USER)
    except Exception as exc:
        logger.warning("dos.grants_failed", error=str(exc))
