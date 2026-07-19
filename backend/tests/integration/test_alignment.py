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


async def test_admin_can_still_create_admin(client, db):
    admin = await create_user(db, role="admin")
    payload = {
        "email": f"real-admin-{uuid.uuid4().hex[:8]}@test.ci", "first_name": "R", "last_name": "A",
        "role": "admin", "password": "TestPass123!",
    }
    r = await client.post("/api/users", headers=auth_headers(admin), json=payload)
    assert r.status_code == 201, r.text


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
