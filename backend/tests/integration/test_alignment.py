"""Tests fonctionnels — alignement notaire ← immo (2FA, alertes, users/admin).

Couvre les endpoints ajoutés/modifiés lors de l'alignement :
- Alertes : prise en charge, traitement + action, contrat AlerteOut, timeline, export
- Users/Admin : require_user_manager, mot de passe temporaire
- 2FA : codes de secours (logique service)
"""
import pytest

# Les cabinets de test sont provisionnés une seule fois (création de schéma +
# migrations Alembic). Leurs connexions appartiennent donc à la boucle de
# session : les tests doivent s'y rattacher, sinon asyncpg refuse les futures
# « attached to a different loop ».
pytestmark = pytest.mark.asyncio(loop_scope="session")

import json
import uuid

from app.services import totp_service
from app.routers.admin import _generate_temp_password
from app.core.password_policy import validate_password_strength
from tests.conftest import create_user, create_alerte, create_dossier, auth_headers


# ── Alertes — prise en charge ───────────────────────────────────────────────────

async def test_prendre_alerte(client, db):
    rc = await create_user(db, role="responsable_conformite")
    a = await create_alerte(db, statut="ouverte")
    r = await client.post(f"/api/alertes/{a.id}/prendre", headers=auth_headers(rc))
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "EN_COURS"
    assert r.json()["prise_en_charge_par"] == rc.id
    # 2e prise en charge impossible (plus 'ouverte')
    r2 = await client.post(f"/api/alertes/{a.id}/prendre", headers=auth_headers(rc))
    assert r2.status_code == 409


# ── Alertes — contrat AlerteOut (statut MAJUSCULES + champs frontend) ───────────

async def test_alerte_list_contract(client, db):
    rc = await create_user(db, role="responsable_conformite")
    a = await create_alerte(db, statut="ouverte", niveau="ELEVE")
    r = await client.get("/api/alertes", headers=auth_headers(rc))
    assert r.status_code == 200
    items = r.json()["items"]
    it = next((x for x in items if x["id"] == a.id), None)
    assert it is not None, "l'alerte créée doit figurer dans la liste"
    assert it["statut"] == "OUVERTE"          # mappé en MAJUSCULES (DB minuscules)
    assert "justification_traitement" in it    # nommage aligné frontend
    assert "prise_en_charge_par" in it


# ── Alertes — traitement avec action sur le dossier ─────────────────────────────

async def test_traiter_avec_action(client, db):
    rc = await create_user(db, role="responsable_conformite")
    a = await create_alerte(db, statut="ouverte")
    r = await client.post(
        f"/api/alertes/{a.id}/traiter",
        headers=auth_headers(rc),
        json={"justification": "Analyse terminée", "action_dossier": "AUCUNE"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "TRAITEE"


async def test_traiter_action_invalide(client, db):
    rc = await create_user(db, role="responsable_conformite")
    a = await create_alerte(db, statut="ouverte")
    r = await client.post(
        f"/api/alertes/{a.id}/traiter",
        headers=auth_headers(rc),
        json={"justification": "x", "action_dossier": "ACTION_BIDON"},
    )
    assert r.status_code == 422


# ── Alertes — timeline ──────────────────────────────────────────────────────────

async def test_timeline(client, db):
    rc = await create_user(db, role="responsable_conformite")
    a = await create_alerte(db)
    r = await client.get(f"/api/alertes/{a.id}/timeline", headers=auth_headers(rc))
    assert r.status_code == 200
    labels = [e["label"] for e in r.json()["events"]]
    assert "Alerte créée" in labels


# ── Alertes — export (RBAC + format Excel) ──────────────────────────────────────

async def test_export_rbac_et_excel(client, db):
    rc = await create_user(db, role="responsable_conformite")
    clerc = await create_user(db, role="clercs")
    await create_alerte(db)
    # Un clerc ne peut pas exporter (réservé conformité)
    r403 = await client.get("/api/alertes/export?format=excel", headers=auth_headers(clerc))
    assert r403.status_code == 403
    # RC : export Excel OK
    r = await client.get("/api/alertes/export?format=excel", headers=auth_headers(rc))
    assert r.status_code == 200, r.text
    assert "spreadsheet" in r.headers.get("content-type", "")


# ── Users — require_user_manager ────────────────────────────────────────────────

async def test_users_require_user_manager(client, db):
    clerc = await create_user(db, role="clercs")
    admin = await create_user(db, role="admin")
    payload = {
        "email": f"nouveau-{uuid.uuid4().hex[:8]}@test.ci", "first_name": "N", "last_name": "U",
        "role": "clercs", "password": "TestPass123!",
    }
    # Clerc → interdit
    r403 = await client.post("/api/users", headers=auth_headers(clerc), json=payload)
    assert r403.status_code == 403
    # Admin → autorisé
    r = await client.post("/api/users", headers=auth_headers(admin), json=payload)
    assert r.status_code == 201, r.text


# ── Cloisonnement Art.63 — lecture des alertes (revue sécurité) ─────────────────

async def test_alertes_cloisonnement_non_superviseur(client, db):
    clerc = await create_user(db, role="clercs")
    autre = await create_user(db, role="clercs")
    d_mine = await create_dossier(db, created_by=clerc.id, assigned_to=clerc.id)
    d_autre = await create_dossier(db, created_by=autre.id, assigned_to=autre.id)
    a_mine = await create_alerte(db, dossier_id=d_mine.id)
    a_autre = await create_alerte(db, dossier_id=d_autre.id)
    r = await client.get("/api/alertes", headers=auth_headers(clerc))
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()["items"]}
    assert a_mine.id in ids            # son dossier → visible
    assert a_autre.id not in ids       # dossier d'autrui → masqué
    # Lecture directe d'une alerte non assignée → 403
    r403 = await client.get(f"/api/alertes/{a_autre.id}", headers=auth_headers(clerc))
    assert r403.status_code == 403


async def test_alertes_superviseur_voit_tout(client, db):
    rc = await create_user(db, role="responsable_conformite")
    autre = await create_user(db, role="clercs")
    d = await create_dossier(db, created_by=autre.id, assigned_to=autre.id)
    a = await create_alerte(db, dossier_id=d.id)
    r = await client.get(f"/api/alertes/{a.id}", headers=auth_headers(rc))
    assert r.status_code == 200       # le superviseur voit l'alerte d'un autre


# ── Anti-escalade de privilège (revue sécurité) ─────────────────────────────────

async def test_notaire_principal_cannot_create_admin(client, db):
    np = await create_user(db, role="notaire_principal")
    payload = {
        "email": f"evil-admin-{uuid.uuid4().hex[:8]}@test.ci", "first_name": "E", "last_name": "A",
        "role": "admin", "password": "TestPass123!",
    }
    r = await client.post("/api/users", headers=auth_headers(np), json=payload)
    assert r.status_code == 403  # seul un admin crée un admin


async def test_notaire_principal_cannot_reset_admin_password(client, db):
    np = await create_user(db, role="notaire_principal")
    admin_target = await create_user(db, role="admin")
    r = await client.post(
        f"/api/admin/users/{admin_target.id}/reset-password/temporary",
        headers=auth_headers(np),
    )
    assert r.status_code == 403  # un NP ne peut pas détourner un compte admin


async def test_admin_ne_cree_pas_de_compte_admin(client, db):
    """L'Admin de cabinet gère tous les rôles SAUF « admin ».

    Ce test affirmait l'inverse (`test_admin_can_still_create_admin`) : il
    garantissait qu'un durcissement visant le Notaire Principal n'avait pas
    débordé sur l'Admin. Le contrat a changé volontairement — le compte
    administrateur est désormais posé au seul provisionnement du cabinet, par
    la console plateforme, qui reste le point d'entrée tracé hors du cabinet.

    La couverture du cas nominal (les 5 autres rôles restent créables) vit dans
    `test_cdc_modules_7_8_9.py::test_adm01_admin_ne_fabrique_pas_de_pair_administrateur`.
    """
    admin = await create_user(db, role="admin")
    payload = {
        "email": f"real-admin-{uuid.uuid4().hex[:8]}@test.ci", "first_name": "R", "last_name": "A",
        "role": "admin", "password": "TestPass123!",
    }
    r = await client.post("/api/users", headers=auth_headers(admin), json=payload)
    assert r.status_code == 403, r.text


# ── Admin — mot de passe temporaire ─────────────────────────────────────────────

async def test_admin_mdp_temporaire(client, db):
    admin = await create_user(db, role="admin")
    target = await create_user(db, role="clercs")
    r = await client.post(
        f"/api/admin/users/{target.id}/reset-password/temporary",
        headers=auth_headers(admin),
    )
    assert r.status_code == 200, r.text
    temp = r.json()["temporary_password"]
    assert validate_password_strength(temp) == temp  # politique respectée


async def test_mdp_temporaire_parcours_complet(client, db):
    """Régression — l'utilisateur réinitialisé doit pouvoir définir son mot de passe.

    Incident production : après génération d'un mot de passe temporaire, le
    collaborateur se connectait bien (le login ne consulte pas la révocation)
    puis restait bloqué sur l'écran « Définir votre mot de passe ». La cause :
    `reset-password/temporary` posait une révocation globale du compte sous
    forme de simple drapeau, valable 8 h (durée de vie du refresh). Or
    `_resolve_user` la consulte pour TOUT appel authentifié, y compris
    `PATCH /auth/password` — le jeton pourtant émis APRÈS la réinitialisation
    partait en 401, et le compte restait inutilisable jusqu'à expiration de la
    clé, chaque nouvelle réinitialisation relançant le compteur.

    Le test suit donc le parcours de bout en bout, seul moyen d'attraper ce
    défaut : pris isolément, chaque endpoint répondait correctement.
    """
    admin = await create_user(db, role="admin")
    cible = await create_user(db, role="clercs")

    reinit = await client.post(
        f"/api/admin/users/{cible.id}/reset-password/temporary",
        headers=auth_headers(admin),
    )
    assert reinit.status_code == 200, reinit.text
    temporaire = reinit.json()["temporary_password"]

    connexion = await client.post(
        "/api/auth/login", json={"email": cible.email, "password": temporaire}
    )
    assert connexion.status_code == 200, connexion.text
    assert connexion.json()["user"]["must_change_password"] is True
    jeton = connexion.json()["access_token"]

    definitif = "MotDePasseNotaire2026!"
    changement = await client.patch(
        "/api/auth/password",
        headers={"Authorization": f"Bearer {jeton}"},
        json={"current_password": temporaire, "new_password": definitif},
    )
    assert changement.status_code == 200, changement.text
    assert changement.json()["user"]["must_change_password"] is False

    # Le mot de passe définitif ouvre une session, le temporaire ne le peut plus.
    assert (await client.post(
        "/api/auth/login", json={"email": cible.email, "password": definitif}
    )).status_code == 200
    assert (await client.post(
        "/api/auth/login", json={"email": cible.email, "password": temporaire}
    )).status_code == 401


async def test_revocation_globale_tue_les_sessions_anterieures(client, db):
    """Contrepartie du test précédent : la révocation doit rester mordante.

    Corriger le blocage en désarmant purement la révocation aurait laissé vivre
    les sessions volées que `revoke-sessions` est censé couper. Seuls les jetons
    émis AVANT la révocation doivent tomber.
    """
    admin = await create_user(db, role="admin")
    cible = await create_user(db, role="clercs")

    jeton_anterieur = auth_headers(cible)
    assert (await client.get("/api/dossiers", headers=jeton_anterieur)).status_code == 200

    revocation = await client.post(
        f"/api/admin/users/{cible.id}/revoke-sessions", headers=auth_headers(admin)
    )
    assert revocation.status_code == 204, revocation.text

    assert (await client.get("/api/dossiers", headers=jeton_anterieur)).status_code == 401
    # Un jeton émis après la révocation, lui, reste valide.
    assert (await client.get("/api/dossiers", headers=auth_headers(cible))).status_code == 200


async def test_liste_utilisateurs_signale_les_comptes_non_actives(client, db):
    """Le drapeau « mot de passe à changer » doit remonter dans la liste du cabinet.

    Un compte créé par l'admin — ou dont le mot de passe vient d'être réinitialisé —
    ne peut rien faire tant que son titulaire n'a pas défini le sien. L'écran
    Utilisateurs n'en montrait rien : l'administrateur n'avait aucun moyen de
    distinguer un collaborateur qui n'a jamais activé son accès d'un autre qui
    travaille normalement, et le cabinet remontait le blocage par message. La vue
    affiche désormais un repère, qui se lit sur ce champ — d'où ce test sur le
    contrat de l'API, seule partie vérifiable automatiquement ici.
    """
    admin = await create_user(db, role="admin")
    h = auth_headers(admin)

    creation = await client.post("/api/users", headers=h, json={
        "email": f"nouveau-{uuid.uuid4().hex[:8]}@test.ci",
        "first_name": "Nouveau", "last_name": "Collaborateur",
        "role": "clercs", "password": "ProvisoireInitial2026!",
    })
    assert creation.status_code in (200, 201), creation.text
    nouveau_id = creation.json()["id"]

    liste = await client.get("/api/users", headers=h)
    assert liste.status_code == 200, liste.text
    comptes = {u["id"]: u for u in liste.json()["items"]}
    assert comptes[nouveau_id]["must_change_password"] is True, (
        "le compte jamais activé doit être signalé dans la liste"
    )
    assert comptes[admin.id]["must_change_password"] is False, (
        "un compte déjà actif ne doit pas porter le repère"
    )


# ── 2FA — codes de secours (logique service, sans infra) ────────────────────────

def test_generate_backup_codes():
    plain, hashed_json = totp_service.generate_backup_codes()
    assert len(plain) == 10
    assert len(json.loads(hashed_json)) == 10
    # Les codes en clair ne sont pas stockés tels quels
    assert all(p not in hashed_json for p in plain)


def test_consume_backup_code():
    plain, hashed_json = totp_service.generate_backup_codes()
    ok, remaining = totp_service.consume_backup_code(hashed_json, plain[0])
    assert ok is True
    assert len(json.loads(remaining)) == 9          # code consommé (usage unique)
    bad, _ = totp_service.consume_backup_code(hashed_json, "codeinvalide")
    assert bad is False
    assert totp_service.count_backup_codes(hashed_json) == 10


def test_temp_password_policy():
    for _ in range(10):
        pw = _generate_temp_password()
        assert validate_password_strength(pw) == pw
