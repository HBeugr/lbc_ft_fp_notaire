"""Étanchéité sous charge concurrente.

Le cloisonnement repose sur deux mécanismes qui, mal combinés, fuiraient
silencieusement : un `ContextVar` (isolé par tâche asyncio) et un pool de
connexions PostgreSQL **partagé** entre tous les cabinets. Une erreur ici ne se
verrait pas en test séquentiel — elle n'apparaîtrait qu'en production, sous
charge, et se traduirait par des données d'un cabinet servies à un autre.

Ces tests entrelacent donc délibérément les requêtes de deux cabinets.
"""
import asyncio
import uuid

import pytest

_boucle_session = pytest.mark.asyncio(loop_scope="session")

from app.core.tenant_context import get_current_tenant_or_none, tenant_scope
from tests.conftest import auth_headers, create_dossier, create_user


@_boucle_session
async def test_requetes_concurrentes_de_deux_cabinets(client, db, db_b, tenant_a, tenant_b):
    """40 requêtes entrelacées : aucune ne doit voir les dossiers de l'autre cabinet."""
    user_a = await create_user(db, role="notaire_principal")
    user_b = await create_user(db_b, role="notaire_principal")

    dossiers_a = {(await create_dossier(db, created_by=user_a.id)).id for _ in range(3)}
    dossiers_b = {(await create_dossier(db_b, created_by=user_b.id)).id for _ in range(3)}

    entetes_a = auth_headers(user_a, tenant_a)
    entetes_b = auth_headers(user_b, tenant_b)

    async def lire(entetes):
        reponse = await client.get("/api/dossiers", headers=entetes)
        assert reponse.status_code == 200, reponse.text
        return {d["id"] for d in reponse.json()["items"]}

    # Entrelacement volontaire : les tâches se disputent le même pool.
    resultats = await asyncio.gather(*[
        lire(entetes_a if i % 2 == 0 else entetes_b) for i in range(40)
    ])

    for index, vus in enumerate(resultats):
        if index % 2 == 0:
            assert dossiers_a <= vus, "le cabinet A ne voit plus ses propres dossiers"
            assert not (vus & dossiers_b), "FUITE : le cabinet A voit des dossiers du cabinet B"
        else:
            assert dossiers_b <= vus, "le cabinet B ne voit plus ses propres dossiers"
            assert not (vus & dossiers_a), "FUITE : le cabinet B voit des dossiers du cabinet A"


@_boucle_session
async def test_contexte_tenant_isole_entre_taches(tenant_a, tenant_b):
    """Le `ContextVar` ne doit pas déborder d'une tâche asyncio à l'autre."""
    observations: list[tuple[str, str]] = []

    async def travail(cabinet, etiquette):
        with tenant_scope(cabinet):
            # Cède la main : si le contexte était partagé, l'autre tâche
            # l'écraserait pendant cette suspension.
            await asyncio.sleep(0)
            courant = get_current_tenant_or_none()
            observations.append((etiquette, courant.id if courant else "aucun"))

    await asyncio.gather(*[
        travail(tenant_a if i % 2 == 0 else tenant_b, "a" if i % 2 == 0 else "b")
        for i in range(20)
    ])

    for etiquette, vu in observations:
        attendu = tenant_a.id if etiquette == "a" else tenant_b.id
        assert vu == attendu, "le contexte cabinet a débordé d'une tâche à l'autre"


@_boucle_session
async def test_chiffrement_concurrent_avec_deux_cles(client, db, db_b, tenant_a, tenant_b):
    """Écritures chiffrées simultanées : chaque cabinet doit relire SES valeurs.

    Le type `EncryptedString` choisit sa clé via le `ContextVar` au moment du
    binding. Une fuite de contexte se traduirait ici par un échec de
    déchiffrement — donc par une erreur bruyante, jamais par une donnée fausse.
    """
    from sqlalchemy import select

    from app.core.database import tenant_session
    from app.models.dossier import KycPP

    user_a = await create_user(db, role="notaire_principal")
    user_b = await create_user(db_b, role="notaire_principal")

    async def ecrire_puis_relire(cabinet, user, telephone):
        dossier_id = None
        with tenant_scope(cabinet):
            async with tenant_session(cabinet) as session:
                from app.models.dossier import Dossier

                dossier = Dossier(
                    id=str(uuid.uuid4()),
                    reference=f"KYC-{uuid.uuid4().hex[:8].upper()}",
                    type_client="PP", type_operation="vente_immobiliere",
                    statut="en_analyse", created_by=user.id,
                )
                session.add(dossier)
                await session.commit()
                dossier_id = dossier.id

                session.add(KycPP(
                    id=str(uuid.uuid4()), dossier_id=dossier_id,
                    nom="Test", prenoms="Concurrent", telephone=telephone,
                ))
                await session.commit()
                await asyncio.sleep(0)

                relu = (await session.execute(
                    select(KycPP).where(KycPP.dossier_id == dossier_id)
                )).scalar_one()
                return relu.telephone

    resultats = await asyncio.gather(*[
        ecrire_puis_relire(tenant_a, user_a, f"+225070000{i:04d}") if i % 2 == 0
        else ecrire_puis_relire(tenant_b, user_b, f"+225050000{i:04d}")
        for i in range(10)
    ])

    for i, telephone in enumerate(resultats):
        attendu = f"+225070000{i:04d}" if i % 2 == 0 else f"+225050000{i:04d}"
        assert telephone == attendu, "déchiffrement croisé entre cabinets"
