"""Recette de sécurité — surface d'entrée : téléversement, restitution, injections.

Ces tests fixent le comportement attendu face à un utilisateur hostile mais
authentifié (un clerc, un compte compromis) :

  * un fichier **déguisé** (HTML/script renommé en .pdf, ou content-type forgé)
    est refusé — la signature réelle du contenu fait foi, pas l'extension ni le
    type déclaré (défense en profondeur qui ne « fail open » pas si `libmagic`
    manque) ;
  * la **restitution** ne renvoie jamais le content-type déclaré à l'upload
    (un `text/html` stocké deviendrait un XSS stocké dès qu'un rendu en ligne a
    lieu) : le type servi est dérivé de l'extension validée et inerte ;
  * l'accès aux pièces d'une fiche est **contrôlé par l'appartenance** ;
  * la recherche de procédures — bâtie sur du SQL brut — est **imperméable à
    l'injection** (paramètres liés) ;
  * un nom de fichier avec « ../ » ne peut pas **échapper** au préfixe de stockage ;
  * le **schéma OpenAPI** n'est pas servi hors développement.
"""
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

import io

from app.main import app
from tests.conftest import auth_headers, create_dossier, create_user

_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
_HTML_XSS = b"<html><body><script>alert(document.domain)</script></body></html>"


async def _dossier(db, role="responsable_conformite"):
    user = await create_user(db, role=role)
    dossier = await create_dossier(db, created_by=user.id, assigned_to=user.id)
    return user, dossier


# ── 1. Téléversement : fichier déguisé refusé ─────────────────────────────────

@pytest.mark.parametrize(
    "filename, content_type",
    [
        ("evil.pdf", "application/pdf"),   # extension autorisée mais contenu HTML
        ("evil.txt", "application/pdf"),   # content-type forgé
        ("evil.png", "text/html"),         # extension autorisée, contenu HTML
    ],
)
async def test_upload_document_deguise_refuse(client, db, filename, content_type):
    """Un contenu HTML/script maquillé en pièce autorisée est refusé (400).

    C'est le cœur de la régression : avant correctif, `ext OU type` suffisait et
    la couche magic-bytes était morte (python-magic absent du conteneur), si bien
    qu'un fichier déguisé était accepté puis stocké dans le coffre du cabinet.
    """
    user, dossier = await _dossier(db)
    r = await client.post(
        f"/api/dossiers/{dossier.id}/documents",
        files={"file": (filename, io.BytesIO(_HTML_XSS), content_type)},
        data={"type_document": "piece_identite"},
        headers=auth_headers(user),
    )
    assert r.status_code == 400, (
        f"Fichier déguisé accepté ({filename}, {content_type}) — {r.status_code} : {r.text[:200]}"
    )


async def test_upload_document_pdf_legitime_accepte(client, db):
    """Le durcissement ne doit pas refuser une vraie pièce : un PDF signé passe."""
    user, dossier = await _dossier(db)
    r = await client.post(
        f"/api/dossiers/{dossier.id}/documents",
        files={"file": ("cni.pdf", io.BytesIO(_PDF), "application/pdf")},
        data={"type_document": "piece_identite"},
        headers=auth_headers(user),
    )
    assert r.status_code == 201, r.text


# ── 2. Restitution : content-type neutralisé ──────────────────────────────────

async def test_download_document_content_type_est_neutralise(client, db):
    """Le content-type servi est dérivé de l'extension, jamais celui déclaré.

    On téléverse un PDF **réel** mais en déclarant `content_type=text/html`. Sans
    correctif, la restitution renverrait `text/html` (le type stocké) — vecteur
    de XSS stocké dès qu'un consommateur rend la ressource en ligne.
    """
    user, dossier = await _dossier(db)
    up = await client.post(
        f"/api/dossiers/{dossier.id}/documents",
        files={"file": ("piege.pdf", io.BytesIO(_PDF), "text/html")},
        data={"type_document": "autre"},
        headers=auth_headers(user),
    )
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]

    dl = await client.get(f"/api/documents/{doc_id}/download", headers=auth_headers(user))
    assert dl.status_code == 200, dl.text
    ct = dl.headers.get("content-type", "")
    assert ct.startswith("application/pdf"), f"content-type non neutralisé : {ct!r}"
    assert "text/html" not in ct
    assert dl.headers.get("content-disposition", "").startswith("attachment")
    assert dl.headers.get("x-content-type-options") == "nosniff"
    assert dl.content == _PDF  # l'octet restitué reste fidèle


# ── 3. Restitution : contrôle d'appartenance ──────────────────────────────────

async def test_download_document_controle_appartenance(client, db):
    """Un clerc non assigné et non superviseur ne peut pas lire la pièce (403)."""
    proprietaire, dossier = await _dossier(db, role="responsable_conformite")
    up = await client.post(
        f"/api/dossiers/{dossier.id}/documents",
        files={"file": ("cni.pdf", io.BytesIO(_PDF), "application/pdf")},
        data={"type_document": "piece_identite"},
        headers=auth_headers(proprietaire),
    )
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]

    intrus = await create_user(db, role="clercs")
    r = await client.get(f"/api/documents/{doc_id}/download", headers=auth_headers(intrus))
    assert r.status_code == 403, f"pièce lisible par un tiers non habilité : {r.status_code}"


# ── 4. Procédures : fichier déguisé refusé, PDF légitime accepté ───────────────

async def _procedure(client, user, nom="Procédure test"):
    r = await client.post("/api/procedures", json={"nom": nom}, headers=auth_headers(user))
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_upload_procedure_deguise_refuse(client, db):
    user = await create_user(db, role="clercs")
    pid = await _procedure(client, user)
    r = await client.post(
        f"/api/procedures/{pid}/files",
        files={"file": ("piece.pdf", io.BytesIO(_HTML_XSS), "application/pdf")},
        data={"slot": "1"},
        headers=auth_headers(user),
    )
    assert r.status_code == 400, f"pièce de procédure déguisée acceptée : {r.status_code} {r.text[:200]}"


async def test_upload_procedure_pdf_legitime_accepte(client, db):
    user = await create_user(db, role="clercs")
    pid = await _procedure(client, user)
    r = await client.post(
        f"/api/procedures/{pid}/files",
        files={"file": ("piece.pdf", io.BytesIO(_PDF), "application/pdf")},
        data={"slot": "1"},
        headers=auth_headers(user),
    )
    assert r.status_code == 201, r.text


# ── 5. Procédures : traversée de chemin neutralisée ───────────────────────────

async def test_upload_procedure_nom_fichier_traversal_neutralise(client, db):
    """« ../ » dans le nom de fichier ne doit pas subsister dans la clé de stockage."""
    user = await create_user(db, role="clercs")
    pid = await _procedure(client, user)
    r = await client.post(
        f"/api/procedures/{pid}/files",
        files={"file": ("../../../../etc/passwd.pdf", io.BytesIO(_PDF), "application/pdf")},
        data={"slot": "2"},
        headers=auth_headers(user),
    )
    assert r.status_code == 201, r.text
    nom = r.json()["nom_fichier"]
    assert "/" not in nom and ".." not in nom, f"nom de fichier non assaini : {nom!r}"


# ── 6. Recherche de procédures : injection SQL neutralisée ─────────────────────

async def test_recherche_procedures_injection_sql_inoffensive(client, db):
    """Le SQL brut de la recherche passe par un paramètre lié : pas d'injection.

    Une charge « ' OR '1'='1 » ne doit PAS élargir le jeu de résultats à toutes
    les procédures (ce que ferait une concaténation naïve) — elle est traitée en
    littéral et ne matche aucun nom.
    """
    user = await create_user(db, role="clercs")
    await _procedure(client, user, nom="Alpha unique 12345")
    await _procedure(client, user, nom="Beta unique 67890")

    legit = await client.get("/api/procedures", params={"search": "Alpha unique 12345"}, headers=auth_headers(user))
    assert legit.status_code == 200, legit.text
    assert legit.json()["total"] >= 1

    inj = await client.get("/api/procedures", params={"search": "' OR '1'='1"}, headers=auth_headers(user))
    assert inj.status_code == 200, inj.text
    assert inj.json()["total"] == 0, "l'injection a élargi le jeu de résultats — paramètre non lié"


async def test_creation_procedure_nom_avec_apostrophe_litteral(client, db):
    """Un nom contenant une apostrophe et « = » est stocké/restitué littéralement
    (pas de rupture SQL, et pas de neutralisation destructrice côté base)."""
    user = await create_user(db, role="clercs")
    nom = "Étude O'Brien =2+2 & Cie"
    pid = await _procedure(client, user, nom=nom)
    detail = await client.get(f"/api/procedures/{pid}", headers=auth_headers(user))
    assert detail.status_code == 200, detail.text
    assert detail.json()["nom"] == nom


# ── 7. Schéma OpenAPI non exposé hors développement ───────────────────────────

async def test_openapi_non_expose_hors_developpement(client):
    """En dehors de `development`, /openapi.json ne doit pas être servi (fuite de
    la surface d'API et des champs des modèles sensibles, DOS compris)."""
    r = await client.get("/openapi.json")
    assert r.status_code == 404, f"schéma OpenAPI exposé (env non-dev) : {r.status_code}"
    # La méthode interne reste néanmoins disponible pour les tests/outillage.
    assert app.openapi()["info"]["title"]
