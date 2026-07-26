"""Cumul de rôles — chemins SUPER-ADMIN de notaire.

`test_roles_cumules.py` (unit) couvre le modèle. Ici on verrouille la **parité**
côté console d'exploitation :

  1. l'onboarding d'un cabinet peut pré-créer des utilisateurs avec cumul
     (`provision_tenant(utilisateurs=[{... roles_extra}])`) ;
  2. le super-admin peut poser/retirer le cumul via
     `PATCH /tenants/{id}/users/{uid}/role` ;
  3. la liste des utilisateurs expose les rôles effectifs (`roles`) ;
  4. un appel sans `roles_extra` reste rétro-compatible (cumul inchangé).

Et un test fonctionnel A/B : le cumul OUVRE réellement un accès (DOS) refusé au
rôle principal seul — `a_role()` étant le prédicat qu'appliquent les endpoints.
"""
import uuid

import pytest
from sqlalchemy import select

from app.core import security
from app.core.database import shared_session, tenant_session
from app.core.tenant_context import tenant_scope
from app.models.shared import SuperAdmin
from app.models.user import User
from app.services import tenant_provisioning
from tests.conftest import _context, auth_headers, create_user

# Fixtures client/db/tenant_a en loop session : les tests doivent partager la
# même boucle, sinon asyncpg lève « attached to a different loop ».
pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(autouse=True)
def _activer_gestion_users():
    """La gestion des users de cabinet depuis la console est derrière un flag
    (SUPER_ADMIN_TENANT_USERS), off par défaut. On l'active le temps du test et
    on le restaure, pour ne pas fausser les autres modules."""
    from app.core.config import settings
    ancien = settings.SUPER_ADMIN_TENANT_USERS
    settings.SUPER_ADMIN_TENANT_USERS = True
    yield
    settings.SUPER_ADMIN_TENANT_USERS = ancien


async def _super_admin_token(client) -> str:
    mdp = "SuperAdminTest2026!"
    async with shared_session() as shared:
        admin = SuperAdmin(
            id=str(uuid.uuid4()), email=f"sa-{uuid.uuid4().hex[:8]}@test.ci",
            hashed_password=security.hash_password(mdp),
            first_name="Super", last_name="Admin", is_active=True,
        )
        shared.add(admin)
        await shared.commit()
        email = admin.email
    r = await client.post("/api/super-admin/auth/login", json={"email": email, "password": mdp})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ── 1. Onboarding : utilisateur additionnel avec cumul ───────────────────────

async def test_onboarding_utilisateur_avec_cumul():
    suffix = uuid.uuid4().hex[:8]
    res = await tenant_provisioning.provision_tenant(
        nom_cabinet=f"Etude Cumul {suffix}", slug=f"cumul-{suffix}",
        contact_email=f"c-{suffix}@test.ci",
        admin_email=f"admin-{suffix}@test.ci",
        admin_first_name="Ad", admin_last_name="Min", totp_required=False,
        utilisateurs=[{
            "email": f"poly-{suffix}@test.ci", "first_name": "Poly", "last_name": "Valent",
            "role": "clercs", "roles_extra": ["responsable_conformite"],
        }],
    )
    ctx = _context(res.tenant)
    with tenant_scope(ctx):
        async with tenant_session(ctx) as tdb:
            u = (await tdb.execute(
                select(User).where(User.email == f"poly-{suffix}@test.ci"))).scalar_one()
            assert u.role == "clercs"
            assert u.a_role("responsable_conformite") and not u.a_role("admin")
            assert u.roles == ("clercs", "responsable_conformite")


# ── 2/3/4. Console super-admin : changement de rôle + cumul ───────────────────

async def test_superadmin_pose_le_cumul_via_changement_de_role(client, db, tenant_a):
    token = await _super_admin_token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    membre = await create_user(db, role="clercs")

    r = await client.patch(
        f"/api/super-admin/tenants/{tenant_a.id}/users/{membre.id}/role",
        headers=hdr, json={"role": "clercs", "roles_extra": ["responsable_conformite"]},
    )
    assert r.status_code == 200, r.text
    assert set(r.json()["roles"]) == {"clercs", "responsable_conformite"}

    # Vérité terrain : le prédicat d'autorisation reconnaît le cumul.
    with tenant_scope(tenant_a):
        async with tenant_session(tenant_a) as tdb:
            u = await tdb.get(User, membre.id)
            assert u.a_role("responsable_conformite")


async def test_superadmin_liste_expose_les_roles(client, db, tenant_a):
    token = await _super_admin_token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    membre = await create_user(db, role="clercs", roles_extra=["declarant_centif"])

    r = await client.get(f"/api/super-admin/tenants/{tenant_a.id}/users", headers=hdr)
    assert r.status_code == 200, r.text
    ligne = next(u for u in r.json() if u["id"] == membre.id)
    assert set(ligne["roles"]) == {"clercs", "declarant_centif"}


async def test_changement_de_role_sans_roles_extra_ne_touche_pas_au_cumul(client, db, tenant_a):
    """Rétro-compat : l'ancien front n'envoie que `role` → le cumul doit survivre."""
    token = await _super_admin_token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    membre = await create_user(db, role="clercs", roles_extra=["responsable_conformite"])

    r = await client.patch(
        f"/api/super-admin/tenants/{tenant_a.id}/users/{membre.id}/role",
        headers=hdr, json={"role": "declarant_centif"},  # pas de roles_extra
    )
    assert r.status_code == 200, r.text
    assert set(r.json()["roles"]) == {"declarant_centif", "responsable_conformite"}


async def test_superadmin_retire_le_cumul(client, db, tenant_a):
    token = await _super_admin_token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    membre = await create_user(db, role="clercs", roles_extra=["responsable_conformite"])

    r = await client.patch(
        f"/api/super-admin/tenants/{tenant_a.id}/users/{membre.id}/role",
        headers=hdr, json={"role": "clercs", "roles_extra": []},
    )
    assert r.status_code == 200, r.text
    assert r.json()["roles"] == ["clercs"]


# ── 5. Fonctionnel : le cumul OUVRE réellement l'accès DOS ────────────────────

async def test_cumul_ouvre_l_acces_dos(client, db, tenant_a):
    """`clercs` n'accède pas aux DOS ; avec le cumul RC, il y accède."""
    avec = await create_user(db, role="clercs", roles_extra=["responsable_conformite"])
    sans = await create_user(db, role="clercs")

    r_ok = await client.get("/api/dos", headers=auth_headers(avec))
    r_ko = await client.get("/api/dos", headers=auth_headers(sans))

    assert r_ok.status_code == 200, f"cumul RC doit ouvrir l'accès DOS : {r_ok.text}"
    assert r_ko.status_code == 403, f"clercs seul doit être refusé : {r_ko.text}"
