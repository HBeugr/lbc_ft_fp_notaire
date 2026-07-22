"""Tests de non-régression — audit de sécurité (volet isolation / auth / autorisations).

Chaque test correspond à une vulnérabilité RÉELLE constatée et corrigée lors de
l'audit, ou à une barrière d'isolation dont la rupture serait une violation du
secret professionnel (Art. 63). Ils exercent la vraie pile ASGI (middleware de
résolution de cabinet compris), sur PostgreSQL/Redis réels.

Constats couverts :
  SEC-1  Énumération de comptes/cabinets au login — la réponse « identifiants
         invalides » doit être STRICTEMENT indiscernable entre un email inconnu
         et un email connu avec mot de passe erroné (même forme, même compteur).
  SEC-2  Portail 2FA incomplet — le flux SSE `/api/alertes/stream`, qui lit son
         jeton en paramètre de requête, doit refuser un jeton `totp_pending`
         (second facteur non validé) au même titre que les endpoints métier.
  SEC-3  Étanchéité inter-cabinets — un jeton du cabinet A ne lit aucune donnée
         du cabinet B (schéma), et un `tid` falsifié sans re-signature est rejeté.
"""
import base64
import json
import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

from app.core import security
from app.core.redis_client import reset_login_attempts
from tests.conftest import auth_headers, create_dossier, create_user


# ── SEC-1 — Énumération de comptes/cabinets au login ──────────────────────────

async def test_login_email_inconnu_indiscernable_de_mdp_errone(client, tenant_a, db):
    """SEC-1 : email inconnu vs email connu + mauvais mot de passe → réponses
    identiques en STATUT et en FORME.

    Avant correctif : l'email inconnu renvoyait `detail` = chaîne, tandis que
    l'email connu renvoyait `detail` = objet portant `remaining_attempts`. La
    présence de ce champ constituait un oracle d'énumération exploitable en une
    seule requête — un attaquant listait ainsi les emails clients de la
    plateforme (information sensible : quels cabinets sont assujettis à l'outil).
    """
    user = await create_user(db, role="responsable_conformite")

    email_inconnu = f"inconnu_{uuid.uuid4().hex}@nulle-part.ci"
    # IP par défaut du client de test ; on repart d'un compteur propre pour que
    # les deux sondes tombent sur la même valeur `remaining_attempts`.
    await reset_login_attempts("testclient", email_inconnu)
    await reset_login_attempts("testclient", user.email)

    r_inconnu = await client.post("/api/auth/login", json={"email": email_inconnu, "password": "peu-importe"})
    r_connu = await client.post("/api/auth/login", json={"email": user.email, "password": "mauvais-mot-de-passe"})

    assert r_inconnu.status_code == 401
    assert r_connu.status_code == 401

    d_inconnu = r_inconnu.json()["detail"]
    d_connu = r_connu.json()["detail"]

    # Même TYPE de charge utile (les deux sont des objets, jamais l'un chaîne et
    # l'autre objet) et mêmes CLÉS : c'est la propriété anti-énumération.
    assert isinstance(d_inconnu, dict) and isinstance(d_connu, dict), (
        "les deux réponses doivent avoir la même forme (objet), sinon oracle d'énumération"
    )
    assert set(d_inconnu.keys()) == set(d_connu.keys())
    assert "remaining_attempts" in d_inconnu
    assert d_inconnu["message"] == d_connu["message"]


async def test_login_email_inconnu_rate_limite_comme_un_compte_reel(client):
    """SEC-1 (suite) : le basculement en 429 ne doit pas non plus distinguer un
    email inconnu d'un compte réel — sinon l'absence de blocage serait un second
    oracle. Un email inconnu martelé finit lui aussi en 429."""
    email = f"inconnu_{uuid.uuid4().hex}@nulle-part.ci"
    await reset_login_attempts("testclient", email)

    statuts = []
    for _ in range(6):
        r = await client.post("/api/auth/login", json={"email": email, "password": "x"})
        statuts.append(r.status_code)

    assert statuts[0] == 401
    assert 429 in statuts, "un email inconnu doit aussi être rate-limité (pas d'oracle 429)"
    await reset_login_attempts("testclient", email)


# ── SEC-2 — Portail 2FA sur le flux SSE ───────────────────────────────────────

def _token_totp_pending(user, tenant) -> str:
    """Jeton d'accès émis AVANT validation du second facteur (login 2FA en cours)."""
    return security.create_access_token(
        user.id, extra={"role": user.role, "totp_pending": True, "tid": tenant.id}
    )


async def test_sse_alertes_refuse_jeton_totp_pending(client, tenant_a, db):
    """SEC-2 : `/api/alertes/stream` doit refuser (403) un jeton `totp_pending`.

    Ce flux lit son jeton en paramètre de requête (EventSource ne porte pas
    d'en-tête Authorization) et court-circuitait donc `get_current_user`, seul
    endroit où le portail 2FA est habituellement appliqué. Un utilisateur
    disposant du seul mot de passe pouvait ainsi suivre en direct le compteur
    d'alertes — un signal LBC/FT sensible — sans avoir passé le second facteur.
    """
    user = await create_user(db, role="notaire_principal")
    token = _token_totp_pending(user, tenant_a)

    r = await client.get(f"/api/alertes/stream?token={token}")
    assert r.status_code == 403, (
        "un jeton totp_pending ne doit jamais ouvrir le flux SSE (contournement 2FA)"
    )


# NB : le contrôle « happy path » (un jeton valide ouvre bien le flux) n'est pas
# rejouable via le client ASGI en processus — `ASGITransport` bufferise le corps,
# si bien qu'un flux SSE infini ne rend jamais la main à l'ouverture. Ce chemin a
# été vérifié en direct contre l'API réelle (HTTP 200). Ici on ne garde que
# l'assertion de sécurité, dont la garde s'exécute AVANT tout streaming.


# ── SEC-3 — Étanchéité inter-cabinets ─────────────────────────────────────────

async def test_dossier_d_un_cabinet_invisible_de_l_autre(client, tenant_a, tenant_b, db, db_b):
    """SEC-3 : un jeton du cabinet B ne peut pas lire un dossier du cabinet A,
    même en connaissant son identifiant (pas d'IDOR cross-cabinet)."""
    owner = await create_user(db, role="notaire_principal")
    dossier = await create_dossier(db, created_by=owner.id, assigned_to=owner.id)

    intrus = await create_user(db_b, role="admin")
    r = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(intrus, tenant_b))
    assert r.status_code == 404, "le dossier de A ne doit pas exister dans le schéma de B"


async def test_tid_falsifie_sans_resignature_est_rejete(client, tenant_a, tenant_b, db):
    """SEC-3 : réécrire le claim `tid` d'un jeton valide (sans re-signer) pour
    pointer un autre cabinet doit échouer — l'intégrité de la signature protège
    le routage de schéma."""
    user = await create_user(db, role="admin")
    token = auth_headers(user, tenant_a)["Authorization"].split(" ", 1)[1]

    header_b64, payload_b64, sig = token.split(".")

    def _decode(seg: str) -> dict:
        return json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4)))

    def _encode(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    payload = _decode(payload_b64)
    payload["tid"] = tenant_b.id  # on tente de se faire passer pour le cabinet B
    falsifie = f"{header_b64}.{_encode(payload)}.{sig}"  # signature d'origine, désormais invalide

    r = await client.get("/api/users", headers={"Authorization": f"Bearer {falsifie}"})
    assert r.status_code == 401
