"""Étanchéité entre cabinets — le test le plus important de la plateforme.

Pour un outil LBC/FT, une fuite inter-cabinets n'est pas un bug fonctionnel :
c'est une violation du secret professionnel et de la confidentialité CENTIF
(Art. 63). Ces tests éprouvent chaque barrière séparément, de sorte qu'une
régression sur l'une d'elles soit visible même si les autres tiennent encore.

Barrières couvertes :
  1. Schéma PostgreSQL     — les données d'un cabinet sont invisibles de l'autre
  2. Jeton                 — `tid` obligatoire, non falsifiable en pratique
  3. Chiffrement           — clé dérivée par cabinet
  4. Redis                 — espaces de noms disjoints
  5. Configuration métier  — seuils de scoring propres à chaque cabinet
  6. Annuaire              — unicité des emails, routage au login
  7. Portier               — cabinet suspendu refoulé
  8. Exploitation          — le Super-Admin n'atteint aucune donnée métier
"""
import pytest

# Les cabinets de test sont provisionnés une seule fois (création de schéma +
# migrations Alembic). Leurs connexions appartiennent donc à la boucle de
# session : les tests doivent s'y rattacher, sinon asyncpg refuse les futures
# « attached to a different loop ».
pytestmark = pytest.mark.asyncio(loop_scope="session")

import uuid

from sqlalchemy import select, text

from app.core import security
from app.core.crypto import TenantKeyError, derive_tenant_fernet
from app.core.database import shared_session, tenant_session
from app.core.tenant_context import tenant_scope
from app.models.dossier import Dossier
from app.models.shared import Tenant
from app.services import tenant_provisioning
from tests.conftest import auth_headers, create_alerte, create_dossier, create_user


# ── 1. Isolation par schéma ──────────────────────────────────────────────────

async def test_dossiers_invisibles_entre_cabinets(client, db, db_b, tenant_a, tenant_b):
    """Un dossier du cabinet A n'apparaît jamais dans la liste du cabinet B."""
    user_a = await create_user(db, role="notaire_principal")
    user_b = await create_user(db_b, role="notaire_principal")
    dossier_a = await create_dossier(db, created_by=user_a.id)

    reponse_a = await client.get("/api/dossiers", headers=auth_headers(user_a, tenant_a))
    reponse_b = await client.get("/api/dossiers", headers=auth_headers(user_b, tenant_b))

    assert reponse_a.status_code == 200, reponse_a.text
    assert reponse_b.status_code == 200, reponse_b.text

    ids_a = {d["id"] for d in reponse_a.json()["items"]}
    ids_b = {d["id"] for d in reponse_b.json()["items"]}
    assert dossier_a.id in ids_a
    assert dossier_a.id not in ids_b
    assert ids_a.isdisjoint(ids_b)


async def test_acces_direct_par_id_cross_cabinet_refuse(client, db, db_b, tenant_a, tenant_b):
    """Connaître l'identifiant d'un dossier d'un autre cabinet ne suffit pas."""
    user_a = await create_user(db, role="notaire_principal")
    user_b = await create_user(db_b, role="notaire_principal")
    dossier_a = await create_dossier(db, created_by=user_a.id)

    reponse = await client.get(
        f"/api/dossiers/{dossier_a.id}", headers=auth_headers(user_b, tenant_b)
    )
    assert reponse.status_code == 404, reponse.text


async def test_utilisateurs_disjoints(client, db, db_b, tenant_a, tenant_b):
    """Les annuaires d'utilisateurs des deux cabinets ne se recoupent pas.

    `limit` est explicite : la pagination par défaut plafonne à 50 lignes, et les
    cabinets de session sont partagés par tous les fichiers de recette. Sans cela,
    l'admin créé ici sort de la première page dès que la suite grossit, et le test
    échoue pour une raison qui n'a rien à voir avec le cloisonnement qu'il éprouve.
    """
    admin_a = await create_user(db, role="admin")
    admin_b = await create_user(db_b, role="admin")

    liste_a = await client.get("/api/users?limit=200", headers=auth_headers(admin_a, tenant_a))
    liste_b = await client.get("/api/users?limit=200", headers=auth_headers(admin_b, tenant_b))

    emails_a = {u["email"] for u in liste_a.json()["items"]}
    emails_b = {u["email"] for u in liste_b.json()["items"]}
    assert admin_a.email in emails_a and admin_a.email not in emails_b
    assert admin_b.email in emails_b and admin_b.email not in emails_a


async def test_alertes_isolees(client, db, db_b, tenant_a, tenant_b):
    rc_a = await create_user(db, role="responsable_conformite")
    rc_b = await create_user(db_b, role="responsable_conformite")
    alerte_a = await create_alerte(db, statut="ouverte")

    vue_b = await client.get("/api/alertes", headers=auth_headers(rc_b, tenant_b))
    assert alerte_a.id not in {a["id"] for a in vue_b.json()["items"]}

    # …et l'action directe est refusée, pas seulement masquée en lecture.
    prise = await client.post(
        f"/api/alertes/{alerte_a.id}/prendre", headers=auth_headers(rc_b, tenant_b)
    )
    assert prise.status_code == 404, prise.text

    ok = await client.post(
        f"/api/alertes/{alerte_a.id}/prendre", headers=auth_headers(rc_a, tenant_a)
    )
    assert ok.status_code == 200, ok.text


async def test_schemas_physiquement_distincts(tenant_a, tenant_b):
    """Les deux cabinets vivent bien dans deux schémas PostgreSQL différents."""
    assert tenant_a.schema != tenant_b.schema
    async with shared_session() as db:
        rows = (await db.execute(text(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN (:a, :b)"
        ), {"a": tenant_a.schema, "b": tenant_b.schema})).scalars().all()
    assert set(rows) == {tenant_a.schema, tenant_b.schema}


# ── 2. Jeton ─────────────────────────────────────────────────────────────────

async def test_jeton_sans_tid_rejete(client, db):
    """Un jeton hérité du mono-tenant (sans cabinet) ne doit plus rien ouvrir."""
    user = await create_user(db, role="admin")
    token = security.create_access_token(user.id, extra={"role": user.role, "totp_pending": False})
    reponse = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 401, reponse.text


async def test_jeton_pointant_un_autre_cabinet_rejete(client, db, tenant_b):
    """Forger `tid` vers un autre cabinet ne donne accès à rien.

    L'utilisateur du cabinet A n'existe pas dans le schéma de B : la session est
    bien routée vers B, et la résolution de l'utilisateur y échoue.
    """
    user_a = await create_user(db, role="admin")
    token = security.create_access_token(
        user_a.id, extra={"role": user_a.role, "totp_pending": False, "tid": tenant_b.id}
    )
    reponse = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 401, reponse.text


async def test_cabinet_inconnu_rejete(client, db):
    user = await create_user(db, role="admin")
    token = security.create_access_token(
        user.id, extra={"role": user.role, "totp_pending": False, "tid": str(uuid.uuid4())}
    )
    reponse = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 401, reponse.text


# ── 3. Chiffrement ───────────────────────────────────────────────────────────

def test_cles_de_chiffrement_distinctes(tenant_a, tenant_b):
    """Chaque cabinet dérive une clé différente du même secret maître."""
    assert tenant_a.key_salt != tenant_b.key_salt
    chiffre = derive_tenant_fernet(tenant_a.key_salt).encrypt(b"donnee sensible")
    with pytest.raises(Exception):
        derive_tenant_fernet(tenant_b.key_salt).decrypt(chiffre)


async def test_donnee_chiffree_illisible_avec_la_cle_dun_autre_cabinet(db, tenant_a, tenant_b):
    """Une PII écrite dans A ne se déchiffre pas sous le contexte de B.

    C'est la garantie de dernier recours : même si une erreur de routage
    exposait des octets d'un autre cabinet, ils resteraient inexploitables — et
    l'échec est bruyant, jamais silencieux.
    """
    from app.models.dossier import KycPP

    user_a = await create_user(db, role="notaire_principal")
    dossier_a = await create_dossier(db, created_by=user_a.id)

    with tenant_scope(tenant_a):
        async with tenant_session(tenant_a) as session:
            session.add(KycPP(
                id=str(uuid.uuid4()), dossier_id=dossier_a.id,
                nom="Kouassi", prenoms="Awa", telephone="+2250700000000",
            ))
            await session.commit()

    # Le stockage est bien chiffré (préfixe applicatif visible en base brute).
    async with shared_session() as raw:
        brut = (await raw.execute(
            text(f'SELECT telephone FROM "{tenant_a.schema}".kyc_pp WHERE dossier_id = :d'),
            {"d": dossier_a.id},
        )).scalar_one()
    assert brut.startswith("enc::"), "la colonne doit être chiffrée au repos"

    # Lu sous le contexte du cabinet B, le déchiffrement échoue explicitement.
    with tenant_scope(tenant_b):
        with pytest.raises(TenantKeyError):
            from app.core.crypto import EncryptedString

            EncryptedString().process_result_value(brut, None)


# ── 4. Redis ─────────────────────────────────────────────────────────────────

async def test_revocation_de_session_cloisonnee(tenant_a, tenant_b):
    """Révoquer un jeton dans A ne révoque rien dans B."""
    from app.core.redis_client import is_token_revoked, revoke_token

    jti = f"jti-test-{uuid.uuid4().hex}"
    with tenant_scope(tenant_a):
        await revoke_token(jti, 60)
        assert await is_token_revoked(jti) is True
    with tenant_scope(tenant_b):
        assert await is_token_revoked(jti) is False


async def test_rate_limit_login_cloisonne(tenant_a, tenant_b):
    """Le blocage anti-brute-force d'un cabinet n'affecte pas l'autre.

    Auparavant compté par seule IP : derrière un NAT partagé, un cabinet pouvait
    verrouiller les utilisateurs de tous les autres.
    """
    from app.core.redis_client import get_login_attempts, increment_login_attempts, reset_login_attempts

    ip, email = "203.0.113.7", f"user-{uuid.uuid4().hex[:6]}@test.ci"
    with tenant_scope(tenant_a):
        await reset_login_attempts(ip, email)
        await increment_login_attempts(ip, email)
        assert await get_login_attempts(ip, email) == 1
    with tenant_scope(tenant_b):
        assert await get_login_attempts(ip, email) == 0


# ── 5. Configuration métier ──────────────────────────────────────────────────

async def test_seuil_especes_par_cabinet(db, db_b, tenant_a, tenant_b):
    """Le seuil T2 (Art. 72) d'un cabinet ne déborde pas sur le scoring de l'autre.

    Un cache global rendrait la classification de risque d'un cabinet dépendante
    des réglages d'un autre — inacceptable pour une décision réglementaire.
    """
    from app.core import runtime_config

    with tenant_scope(tenant_a):
        await runtime_config.load_from_db(db)
        await runtime_config.set_seuil_especes_t2(db, 25_000_000)
        await db.commit()
        assert runtime_config.get_seuil_especes_t2() == 25_000_000

    with tenant_scope(tenant_b):
        await runtime_config.load_from_db(db_b)
        assert runtime_config.get_seuil_especes_t2() != 25_000_000


# ── 6. Annuaire et routage au login ──────────────────────────────────────────

async def test_login_route_vers_le_bon_cabinet(client, db, db_b, tenant_a, tenant_b):
    """L'email seul suffit à router vers le bon cabinet, sans le désigner."""
    user_a = await create_user(db, role="admin")
    user_b = await create_user(db_b, role="admin")

    for user, tenant in ((user_a, tenant_a), (user_b, tenant_b)):
        reponse = await client.post(
            "/api/auth/login", json={"email": user.email, "password": "TestPass123!"}
        )
        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert corps["tenant"]["id"] == tenant.id
        assert corps["user"]["email"] == user.email


async def test_email_unique_sur_la_plateforme(db, db_b, tenant_b):
    """Un email déjà rattaché à un cabinet ne peut pas l'être à un second.

    Sans cette contrainte, le routage au login serait ambigu.
    """
    from app.services.tenant_directory import DirectoryError, register

    user_a = await create_user(db, role="clercs")
    with tenant_scope(tenant_b):
        with pytest.raises(DirectoryError):
            await register(user_a.email, str(uuid.uuid4()))


async def test_login_email_inconnu(client):
    reponse = await client.post(
        "/api/auth/login", json={"email": "inconnu@nulle-part.ci", "password": "x"}
    )
    assert reponse.status_code == 401


# ── 7. Portier ───────────────────────────────────────────────────────────────

async def test_cabinet_suspendu_refoule(client, db, db_b, tenant_b):
    """Un cabinet suspendu perd l'accès, données intégralement conservées."""
    user_b = await create_user(db_b, role="admin")
    jeton = auth_headers(user_b, tenant_b)

    avant = await client.get("/api/dossiers", headers=jeton)
    assert avant.status_code == 200

    await tenant_provisioning.set_tenant_statut(tenant_b.id, "suspendu", motif="Test")
    try:
        pendant = await client.get("/api/dossiers", headers=jeton)
        assert pendant.status_code == 402, pendant.text
        assert pendant.json()["code"] == "tenant_suspended"

        connexion = await client.post(
            "/api/auth/login", json={"email": user_b.email, "password": "TestPass123!"}
        )
        assert connexion.status_code == 402, connexion.text
    finally:
        await tenant_provisioning.set_tenant_statut(tenant_b.id, "production")

    apres = await client.get("/api/dossiers", headers=jeton)
    assert apres.status_code == 200, "la réactivation doit rendre l'accès sans perte de données"


# ── 8. Étanchéité de l'exploitation ──────────────────────────────────────────

async def test_super_admin_ne_peut_pas_lire_le_metier(client, db):
    """Un jeton d'exploitation n'ouvre aucun endpoint métier.

    Il ne porte pas de `tid` — et le compte n'existe dans aucun schéma cabinet,
    donc même un `tid` ajouté ne résoudrait aucun utilisateur.
    """
    jeton = security.create_access_token(str(uuid.uuid4()), extra={"scope": "platform"})
    reponse = await client.get("/api/dossiers", headers={"Authorization": f"Bearer {jeton}"})
    assert reponse.status_code == 401, reponse.text


async def test_jeton_cabinet_refuse_sur_la_console(client, db, tenant_a):
    """Réciproquement, un utilisateur de cabinet n'entre pas dans la console."""
    admin = await create_user(db, role="admin")
    reponse = await client.get(
        "/api/super-admin/tenants", headers=auth_headers(admin, tenant_a)
    )
    assert reponse.status_code == 401, reponse.text


async def test_metriques_super_admin_sans_contenu_metier(client, db, tenant_a):
    """Les métriques d'exploitation ne remontent que des volumes."""
    from app.models.shared import SuperAdmin

    mot_de_passe = "SuperAdminTest2026!"
    async with shared_session() as shared:
        admin = SuperAdmin(
            id=str(uuid.uuid4()), email=f"sa-{uuid.uuid4().hex[:8]}@test.ci",
            hashed_password=security.hash_password(mot_de_passe),
            first_name="Super", last_name="Admin", is_active=True,
        )
        shared.add(admin)
        await shared.commit()
        email = admin.email

    connexion = await client.post(
        "/api/super-admin/auth/login", json={"email": email, "password": mot_de_passe}
    )
    assert connexion.status_code == 200, connexion.text
    entetes = {"Authorization": f"Bearer {connexion.json()['access_token']}"}

    metriques = await client.get(f"/api/super-admin/tenants/{tenant_a.id}/metrics", headers=entetes)
    assert metriques.status_code == 200, metriques.text
    corps = metriques.json()
    assert set(corps) == {
        "tenant_id", "utilisateurs_actifs", "utilisateurs_total",
        "quota_utilisateurs", "dossiers_total",
    }
    assert isinstance(corps["dossiers_total"], int)


# ── Conservation légale (Art. 23) ────────────────────────────────────────────

async def test_suppression_dossier_archive_impossible(db, tenant_a):
    """La conservation 10 ans est garantie par la base, pas par l'applicatif.

    Le trigger MySQL `SIGNAL SQLSTATE` a été porté en plpgsql : aucun rôle ni
    chemin de code ne peut supprimer un dossier archivé (Art. 23, Art. 197).
    """
    user = await create_user(db, role="notaire_principal")
    dossier = await create_dossier(db, created_by=user.id, statut="archive")

    with tenant_scope(tenant_a):
        async with tenant_session(tenant_a) as session:
            with pytest.raises(Exception) as erreur:
                await session.execute(
                    text("DELETE FROM dossiers WHERE id = :id"), {"id": dossier.id}
                )
                await session.commit()
    assert "archive" in str(erreur.value).lower()

    # Le dossier est toujours là.
    with tenant_scope(tenant_a):
        async with tenant_session(tenant_a) as session:
            reste = (
                await session.execute(select(Dossier).where(Dossier.id == dossier.id))
            ).scalar_one_or_none()
    assert reste is not None


# ── Provisioning ─────────────────────────────────────────────────────────────

async def test_provisioning_cree_un_schema_complet(tenant_a):
    """Un cabinet fraîchement provisionné dispose de toutes les tables métier."""
    async with shared_session() as db:
        tables = (await db.execute(text(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = :s"
        ), {"s": tenant_a.schema})).scalar_one()
    # 23 tables métier + la table de versions Alembic propre au schéma.
    assert tables >= 24, f"schéma incomplet : {tables} tables"


async def test_provisioning_refuse_un_slug_deja_pris(tenant_a):
    async with shared_session() as db:
        existant = (
            await db.execute(select(Tenant).where(Tenant.id == tenant_a.id))
        ).scalar_one()

    with pytest.raises(tenant_provisioning.ProvisioningError):
        await tenant_provisioning.provision_tenant(
            nom_cabinet="Doublon",
            slug=existant.slug,
            contact_email="doublon@test.ci",
            admin_email=f"doublon-{uuid.uuid4().hex[:6]}@test.ci",
            admin_first_name="A", admin_last_name="B",
        )


# ── 9. Contexte cabinet hors du cycle requête/réponse ───────────────────────
#
# Le flux SSE `/api/alertes/stream` a constitué la régression la plus insidieuse
# de cette migration : son générateur est consommé APRÈS la sortie du middleware,
# donc hors du `ContextVar` d'isolation, et l'échec était SILENCIEUX — réponse
# 200, flux vide, badge d'alertes muet.
#
# Il n'est volontairement pas testé ici : le transport ASGI en processus
# n'expose pas de flux qui ne se termine jamais. La vérification vit dans
# `scripts/e2e_saas.sh`, contre un serveur réel, et porte sur le CONTENU du flux
# — un contrôle de code de statut n'aurait rien vu.
