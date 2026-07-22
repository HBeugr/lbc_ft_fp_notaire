#!/usr/bin/env python3
"""Couverture exhaustive de la surface d'API — détection des 5xx multi-tenant/PostgreSQL.

POURQUOI
--------
La plateforme a migré de MySQL mono-tenant vers PostgreSQL multi-tenant (isolation
par schéma). Les régressions typiques de cette migration (valeur absente d'un type
ENUM, datetime naïf vs TIMESTAMPTZ, Decimal asyncpg là où un float est attendu,
accès sans contexte de cabinet) ne se voient QUE si la route est réellement
appelée avec des identifiants existants. Or ~95 routes à paramètre de chemin
(`/{id}`) n'étaient jamais exercées : sans jeu de données réel, elles répondent
404 avant d'atteindre le code fautif.

Ce script construit donc d'abord un jeu de données réel dans le cabinet, puis
rejoue CHAQUE opération de l'OpenAPI en substituant les identifiants créés.

Ce qu'on cherche : les **5xx** uniquement. Un 422 (validation), un 403 (RBAC) ou
un 404 (règle métier) sont des résultats acceptables — le but n'est pas de tester
la logique métier mais de prouver qu'aucune route ne casse à l'exécution.

USAGE
-----
    python backend/scripts/api_coverage.py [--base-url http://127.0.0.1:9000] [--json rapport.json]

Dépendances : stdlib uniquement (urllib), pour rester exécutable dans le conteneur
API sans installer quoi que ce soit.

EFFETS DE BORD
--------------
Le script écrit dans le cabinet de démonstration : dossiers, KYC, alertes, DOS,
révisions, documents, commentaires, utilisateur jetable (supprimé en fin de course).
Il provisionne aussi un **cabinet jetable** via le Super-Admin : c'est la seule
façon d'obtenir un jeton de rôle `admin` (l'anti-escalade interdit au Notaire
Principal de débloquer l'admin de démo), et donc de couvrir /api/sanctions,
/api/procedures, /api/scoring/weights et le flux TOTP. Ce cabinet est archivé à la
fin. À n'utiliser que sur un environnement de démonstration/recette.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import mimetypes
import re
import ssl
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timedelta, timezone

# --------------------------------------------------------------------------- #
# Constantes d'environnement
# --------------------------------------------------------------------------- #

DEFAULT_BASE_URL = "http://127.0.0.1:9000"

# Comptes du cabinet de démonstration. L'ordre compte : le sweep générique essaie
# les rôles dans cet ordre jusqu'à obtenir autre chose qu'un 401/403.
ACCOUNTS = [
    ("notaire", "notaire@notaire.local", "Notaire2026!"),
    ("conformite", "conformite@notaire.local", "Conformite2026!"),
    ("clerc", "clerc@notaire.local", "Clerc2026!"),
]
SUPERADMIN = ("superadmin@plateforme.local", "SuperAdmin2026!")

# Le compte admin du cabinet de démo est bloqué sur un mot de passe temporaire, et
# l'anti-escalade interdit au Notaire Principal de le débloquer. Pour couvrir
# quand même les routes `require_admin`, on provisionne un cabinet jetable via le
# Super-Admin : sa création retourne le mot de passe temporaire de SON admin.
QA_PASSWORD = "QaCouverture2026!x"

# `EmailStr` (email_validator) refuse les TLD réservés (.local, .test, .invalid) :
# les comptes créés par le script doivent porter un domaine « réel ».
QA_DOMAIN = "qa-couverture.ci"

# PDF minimal réellement signé : les uploads passent par un contrôle
# extension + content-type + magic-bytes (anti-fichier déguisé).
MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

# Le flux SSE ne se termine jamais : timeout court et statut synthétique.
STREAM_PATHS = {"/api/alertes/stream"}
STREAM_TIMEOUT = 3

# Routes à ne jamais appeler dans le sweep : elles détruiraient l'environnement ou
# la session de test elle-même. Toutes sont rejouées en phase finale sur des
# cibles jetables (utilisateur jetable, cabinet jetable).
SKIP_PATHS = {
    ("post", "/api/auth/logout"),           # révoquerait le jeton en cours
    ("patch", "/api/auth/password"),        # changerait le mot de passe du compte de test
    ("patch", "/api/super-admin/auth/password"),
    ("post", "/api/admin/users/{user_id}/revoke-sessions"),
    ("post", "/api/admin/users/{user_id}/reset-password"),
    ("post", "/api/admin/users/{user_id}/reset-password/temporary"),
    ("delete", "/api/admin/users/{user_id}/totp"),
    ("delete", "/api/users/{user_id}"),
    # Cycle de vie du cabinet : archiver le cabinet jetable en plein sweep
    # invaliderait le jeton admin dont dépendent les routes suivantes.
    ("post", "/api/super-admin/tenants/{tenant_id}/suspend"),
    ("post", "/api/super-admin/tenants/{tenant_id}/activate"),
    ("post", "/api/super-admin/tenants/{tenant_id}/archive"),
}


# --------------------------------------------------------------------------- #
# Client HTTP minimal (stdlib)
# --------------------------------------------------------------------------- #

class Response:
    __slots__ = ("status", "body", "headers", "error")

    def __init__(self, status, body="", headers=None, error=None):
        self.status = status
        self.body = body
        self.headers = headers or {}
        self.error = error

    def json(self):
        try:
            return json.loads(self.body)
        except Exception:
            return None

    def __repr__(self):
        return f"<{self.status} {self.body[:120]!r}>"


_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def request(method, url, token=None, json_body=None, raw_body=None,
            content_type=None, timeout=60, cookies=None, stream_lines=0):
    """Appel HTTP brut. Ne lève jamais : un échec réseau devient un statut 0."""
    data = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif raw_body is not None:
        data = raw_body
        if content_type:
            headers["Content-Type"] = content_type
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if cookies:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            if stream_lines:
                # Flux SSE : il ne se termine jamais. On lit les premières lignes
                # pour vérifier que le générateur produit bien des évènements — un
                # `: error` signifierait une route « 200 mais cassée ».
                chunks = []
                try:
                    for _ in range(stream_lines):
                        line = resp.readline()
                        if not line:
                            break
                        chunks.append(line)
                except Exception:
                    pass
                body = b"".join(chunks).decode("utf-8", "replace")
            else:
                try:
                    body = resp.read(200_000).decode("utf-8", "replace")
                except Exception:
                    body = "(lecture interrompue — statut déjà reçu)"
            return Response(resp.status, body, dict(resp.headers))
    except urllib.error.HTTPError as exc:
        body = exc.read(200_000).decode("utf-8", "replace")
        return Response(exc.code, body, dict(exc.headers or {}))
    except Exception as exc:  # timeout, connexion refusée, SSE qui ne termine pas
        return Response(0, "", error=f"{type(exc).__name__}: {exc}")


def multipart(fields, files):
    """Encode un corps multipart/form-data. `files` = [(champ, nom_fichier, octets)]."""
    boundary = "----qa" + uuid.uuid4().hex
    out = bytearray()
    for name, value in fields.items():
        out += f"--{boundary}\r\n".encode()
        out += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        out += f"{value}\r\n".encode()
    for name, filename, payload in files:
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        out += f"--{boundary}\r\n".encode()
        out += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        out += f"Content-Type: {ctype}\r\n\r\n".encode()
        out += payload + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def extract_refresh_cookie(resp):
    """Le refresh token n'est PAS dans le corps : il arrive en cookie httpOnly."""
    raw = resp.headers.get("Set-Cookie") or resp.headers.get("set-cookie") or ""
    m = re.search(r"refresh_token=([^;]+)", raw)
    return m.group(1) if m else None


def totp_code(secret_b32, at=None):
    """TOTP RFC 6238 en stdlib — évite d'ajouter pyotp juste pour activer une 2FA."""
    pad = "=" * (-len(secret_b32) % 8)
    try:
        key = base64.b32decode(secret_b32.upper() + pad)
    except binascii.Error:
        return "000000"
    counter = int((at or time.time()) // 30)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


# --------------------------------------------------------------------------- #
# Générateur de payload depuis le schéma OpenAPI
# --------------------------------------------------------------------------- #

class SchemaFaker:
    """Fabrique un corps minimal *valide* à partir du schéma OpenAPI.

    POURQUOI : écrire à la main 133 payloads serait ingérable et se périmerait à
    chaque évolution du contrat. On ne garde des surcharges manuelles que pour les
    champs porteurs de sens (identifiants réels, énumérations métier).
    """

    def __init__(self, spec, ctx):
        self.spec = spec
        self.ctx = ctx  # identifiants réels, injectés dans les champs *_id

    def resolve(self, schema):
        seen = 0
        while isinstance(schema, dict) and "$ref" in schema and seen < 10:
            ref = schema["$ref"].split("/")[-1]
            schema = self.spec["components"]["schemas"].get(ref, {})
            seen += 1
        return schema or {}

    def build(self, schema, name="", depth=0):
        schema = self.resolve(schema)
        if depth > 5:
            return None

        # anyOf/oneOf : on prend la première branche non-nulle (le `| None` de
        # Pydantic v2 se traduit systématiquement ainsi).
        for key in ("anyOf", "oneOf"):
            if key in schema:
                branches = [b for b in schema[key]
                            if self.resolve(b).get("type") != "null"]
                if not branches:
                    return None
                return self.build(branches[0], name, depth + 1)
        if "allOf" in schema:
            merged = {}
            for part in schema["allOf"]:
                merged.update(self.resolve(part))
            return self.build(merged, name, depth + 1)

        if "enum" in schema and schema["enum"]:
            return schema["enum"][0]
        if "default" in schema and schema.get("type") != "object":
            return schema["default"]

        typ = schema.get("type")

        if typ == "object" or ("properties" in schema and not typ):
            props = schema.get("properties") or {}
            required = set(schema.get("required") or [])
            if not props:
                # objet libre (`dict`) : un dictionnaire vide suffit
                extra = schema.get("additionalProperties")
                if isinstance(extra, dict):
                    return {"cle": self.build(extra, name, depth + 1)}
                return {}
            out = {}
            for pname, pschema in props.items():
                if pname in required:
                    out[pname] = self.build(pschema, pname, depth + 1)
            return out

        if typ == "array":
            items = schema.get("items", {})
            if schema.get("minItems", 0) > 0:
                return [self.build(items, name, depth + 1)]
            return []

        if typ == "integer":
            lo = schema.get("minimum", 1)
            hi = schema.get("maximum")
            val = int(lo if lo else 1)
            if hi is not None and val > hi:
                val = int(hi)
            return val
        if typ == "number":
            lo = schema.get("minimum", 1)
            hi = schema.get("maximum")
            val = float(lo if lo else 1)
            if hi is not None and val > hi:
                val = float(hi)
            return val
        if typ == "boolean":
            return False
        if typ == "null":
            return None

        return self._string(schema, name)

    def _string(self, schema, name):
        fmt = schema.get("format")
        low = name.lower()
        if fmt == "date":
            return date.today().isoformat()
        if fmt == "date-time":
            return datetime.now(timezone.utc).isoformat()
        if fmt == "email":
            return f"qa.{uuid.uuid4().hex[:8]}@notaire.local"
        if fmt == "uuid":
            return self.ctx.get(low) or str(uuid.uuid4())
        # Un champ `*_id` doit porter un identifiant RÉEL, sinon la route s'arrête
        # sur un 404 et on ne teste rien.
        if low.endswith("_id") and self.ctx.get(low):
            return self.ctx[low]
        if "password" in low:
            return "QaCoverage2026!x"
        if "date" in low or "echeance" in low:
            return (date.today() + timedelta(days=30)).isoformat()
        if low == "pays" or low.startswith("pays"):
            return "CI"
        if low in ("slug",):
            return f"qa{uuid.uuid4().hex[:8]}"
        minlen = schema.get("minLength", 0)
        maxlen = schema.get("maxLength")
        val = "QA couverture"
        if len(val) < minlen:
            val = val + "x" * (minlen - len(val))
        if maxlen and len(val) > maxlen:
            val = val[:maxlen]
        return val

    def body_for(self, op):
        rb = op.get("requestBody")
        if not rb:
            return None, None, None
        content = rb.get("content") or {}
        if "application/json" in content:
            schema = content["application/json"].get("schema", {})
            return self.build(schema), None, None
        if "multipart/form-data" in content:
            schema = self.resolve(content["multipart/form-data"].get("schema", {}))
            fields, files = {}, []
            for pname, pschema in (schema.get("properties") or {}).items():
                ps = self.resolve(pschema)
                if ps.get("format") == "binary":
                    files.append((pname, "qa-couverture.csv", b"nom,type\nQA TEST,PP\n"))
                else:
                    fields[pname] = self.build(pschema, pname)
            raw, ctype = multipart(fields, files)
            return None, raw, ctype
        return None, None, None

    def query_for(self, op):
        """Paramètres de requête obligatoires uniquement (le reste a un défaut)."""
        params = {}
        for p in op.get("parameters", []):
            if p.get("in") == "query" and p.get("required"):
                params[p["name"]] = self.build(p.get("schema", {}), p["name"])
        return params


# --------------------------------------------------------------------------- #
# Journal des résultats
# --------------------------------------------------------------------------- #

class Recorder:
    def __init__(self):
        self.rows = []

    def add(self, phase, method, path, url, role, resp, note=""):
        self.rows.append({
            "phase": phase,
            "method": method.upper(),
            "path": path,
            "url": url,
            "role": role,
            "status": resp.status,
            "body": (resp.body or resp.error or "")[:600],
            "note": note,
        })
        return resp

    @property
    def failures(self):
        return [r for r in self.rows if r["status"] >= 500 or r["status"] == 0]


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #

class Coverage:
    def __init__(self, base_url):
        self.base = base_url.rstrip("/")
        self.tokens = {}
        self.refresh_tokens = {}
        self.ctx = {}          # nom de paramètre de chemin -> identifiant réel
        self.rec = Recorder()
        self.spec = None
        self.tag = uuid.uuid4().hex[:8]
        self.dossier_ref = None
        self.qa_admin_id = None

    # ---- utilitaires ---- #

    def call(self, method, path, role="notaire", phase="seed", note="",
             json_body=None, raw_body=None, content_type=None, query=None,
             timeout=60, cookies=None, stream_lines=0):
        url = self.base + path
        if query:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(query)
        resp = request(method, url, token=self.tokens.get(role), json_body=json_body,
                       raw_body=raw_body, content_type=content_type, timeout=timeout,
                       cookies=cookies, stream_lines=stream_lines)
        # Un flux SSE qui répond 200 puis n'émet que `: error` est un échec
        # silencieux (typiquement : perte du contexte cabinet dans le générateur).
        # On le remonte comme une anomalie, sinon il passerait pour un succès.
        if stream_lines and ": error" in (resp.body or ""):
            resp = Response(598, resp.body, resp.headers)
            note = (note + " | flux SSE en erreur").strip(" |")
        return self.rec.add(phase, method, path, url, role, resp, note)

    def remember(self, key, value):
        if value:
            self.ctx[key] = value

    # ---- phase 0 : authentification ---- #

    def authenticate(self):
        for role, email, pwd in ACCOUNTS:
            r = request("POST", f"{self.base}/api/auth/login",
                        json_body={"email": email, "password": pwd})
            data = r.json() or {}
            if r.status != 200 or not data.get("access_token"):
                print(f"  !! login {role} -> {r.status} {r.body[:200]}")
                continue
            self.tokens[role] = data["access_token"]
            self.refresh_tokens[role] = extract_refresh_cookie(r)
            print(f"  ok login {role}")

        r = request("POST", f"{self.base}/api/super-admin/auth/login",
                    json_body={"email": SUPERADMIN[0], "password": SUPERADMIN[1]})
        data = r.json() or {}
        if data.get("access_token"):
            self.tokens["superadmin"] = data["access_token"]
            print("  ok login superadmin")
        else:
            print(f"  !! login superadmin -> {r.status} {r.body[:200]}")

        if not self.tokens:
            sys.exit("Aucune authentification possible — pile arrêtée ?")

        self.provision_qa_tenant()

    def provision_qa_tenant(self):
        """Cabinet jetable + jeton `admin`, seule voie pour couvrir `require_admin`."""
        if "superadmin" not in self.tokens:
            print("  !! pas de super-admin : les routes require_admin sortiront en 403")
            return
        resp = self.call("POST", "/api/super-admin/tenants", role="superadmin",
                         phase="auth", json_body={
                             "nom_cabinet": f"Cabinet QA {self.tag}",
                             "contact_email": f"contact.{self.tag}@{QA_DOMAIN}",
                             "admin_email": f"admin.{self.tag}@{QA_DOMAIN}",
                             "admin_first_name": "QA", "admin_last_name": "Tenant",
                             "slug": f"qa{self.tag}", "pays": "CI",
                         })
        data = resp.json() or {}
        tenant = data.get("tenant") or {}
        self.remember("tenant_id", tenant.get("id"))
        email, temp = data.get("admin_email"), data.get("admin_temp_password")
        if not (email and temp):
            print(f"  !! cabinet QA non provisionné -> {resp.status} {resp.body[:200]}")
            return
        # Un cabinet naît en statut « configuration » : le portier de /auth/login
        # refuse toute session tant qu'il n'est pas activé.
        self.call("POST", f"/api/super-admin/tenants/{self.ctx['tenant_id']}/activate",
                  role="superadmin", phase="auth", json_body={"motif": "QA couverture"})

        r = request("POST", f"{self.base}/api/auth/login",
                    json_body={"email": email, "password": temp})
        token = (r.json() or {}).get("access_token")
        if not token:
            print(f"  !! login admin QA -> {r.status} {r.body[:200]}")
            return
        self.tokens["admin"] = token
        # Le compte est créé avec `must_change_password` : on solde la contrainte
        # tout de suite, sinon les routes métier peuvent refuser la session.
        request("PATCH", f"{self.base}/api/auth/password", token=token,
                json_body={"current_password": temp, "new_password": QA_PASSWORD})
        r = request("POST", f"{self.base}/api/auth/login",
                    json_body={"email": email, "password": QA_PASSWORD})
        data = r.json() or {}
        if data.get("access_token"):
            self.tokens["admin"] = data["access_token"]
            self.refresh_tokens["admin"] = extract_refresh_cookie(r)
        me = self.call("GET", "/api/users/me", role="admin", phase="auth").json() or {}
        self.qa_admin_id = me.get("id")
        print("  ok login admin (cabinet QA)")

    # ---- phase 1 : jeu de données réel ---- #

    def seed(self):
        c = self.call

        # -- Utilisateur jetable : cible de toutes les routes destructives sur
        #    /users et /admin/users, pour ne jamais casser les comptes de démo.
        self.throwaway_email = f"qa.jetable.{self.tag}@{QA_DOMAIN}"
        u = c("POST", "/api/users", role="notaire", json_body={
            "email": self.throwaway_email,
            "first_name": "QA", "last_name": "Jetable",
            "role": "clercs", "password": QA_PASSWORD,
            "must_change_password": False,
        }).json() or {}
        self.remember("user_id", u.get("id"))
        r = request("POST", f"{self.base}/api/auth/login", json_body={
            "email": self.throwaway_email, "password": QA_PASSWORD})
        self.tokens["jetable"] = (r.json() or {}).get("access_token")
        self.refresh_tokens["jetable"] = extract_refresh_cookie(r)

        # -- Dossier PP (parcours principal) --
        d = c("POST", "/api/dossiers", role="clerc", json_body={
            "type_client": "PP", "type_operation": "vente_immobiliere",
            "montant_transaction": 25_000_000, "mode_paiement": "especes",
            "nb_parties": 2,
        }).json() or {}
        self.remember("dossier_id", d.get("id"))
        # `POST /api/alertes/signaler` prend la RÉFÉRENCE du dossier, pas son UUID.
        self.dossier_ref = d.get("reference") or d.get("reference_interne")
        dossier_id = self.ctx.get("dossier_id")

        # -- Dossier PM (couvre les routes /kyc/pm) --
        d2 = c("POST", "/api/dossiers", role="clerc", json_body={
            "type_client": "PM", "type_operation": "constitution_societe",
            "montant_transaction": 5_000_000, "mode_paiement": "virement",
        }).json() or {}
        self.remember("dossier_pm_id", d2.get("id"))
        dossier_pm = self.ctx.get("dossier_pm_id")

        if not dossier_id:
            print("  !! aucun dossier créé — la couverture sera partielle")
            return

        # -- KYC PP + sous-collections (BE / PPE) --
        c("PUT", f"/api/dossiers/{dossier_id}/kyc/pp", role="clerc", json_body={
            "relation_type": "initiale", "nom": "KOUASSI", "prenoms": "Ama QA",
            "sexe": "F", "date_naissance": "1985-04-12", "lieu_naissance": "Abidjan",
            "nationalite": "CI", "type_piece": "CNI", "numero_piece": "CI-QA-001",
            "pays_residence": "CI", "profession": "Commerçante",
        })
        for i in (1, 2):  # deux exemplaires : un pour PATCH, un pour DELETE
            be = c("POST", f"/api/dossiers/{dossier_id}/kyc/pp/be", role="clerc",
                   json_body={"raison_sociale_nom": f"BE QA {i}",
                              "cni_passeport": f"CI-BE-{i}", "pourcentage": 30.0,
                              "pays_residence": "CI"}).json() or {}
            self.remember("be_id" if i == 1 else "be_id_2", be.get("id"))
            ppe = c("POST", f"/api/dossiers/{dossier_id}/kyc/pp/ppe", role="clerc",
                    json_body={"statut_ppe": "PPE_National", "fonctions": "Maire",
                               "pays_concerne": "CI"}).json() or {}
            self.remember("ppe_id" if i == 1 else "ppe_id_2", ppe.get("id"))

        # -- KYC PM + BE / PPE / actionnaires --
        if dossier_pm:
            c("PUT", f"/api/dossiers/{dossier_pm}/kyc/pm", role="clerc", json_body={
                "relation_type": "initiale",
                "denomination_sociale": "SOCIETE QA SARL",
                "forme_juridique": "SARL", "pays_constitution": "CI",
                "nom_representant_legal": "TRAORE Ali", "numero_rccm": "CI-ABJ-QA-001",
                "objet_social": "Négoce", "adresse": "Abidjan Plateau",
            })
            for i in (1, 2):
                be = c("POST", f"/api/dossiers/{dossier_pm}/kyc/pm/be", role="clerc",
                       json_body={"raison_sociale_nom": f"BE PM QA {i}",
                                  "cni_passeport": f"CI-BEPM-{i}", "pourcentage": 40.0,
                                  "pays_residence": "CI"}).json() or {}
                self.remember("pm_be_id" if i == 1 else "pm_be_id_2", be.get("id"))
                ppe = c("POST", f"/api/dossiers/{dossier_pm}/kyc/pm/ppe", role="clerc",
                        json_body={"statut_ppe": "PPE_Etranger", "fonctions": "Ministre",
                                   "pays_concerne": "FR"}).json() or {}
                self.remember("pm_ppe_id" if i == 1 else "pm_ppe_id_2", ppe.get("id"))
                act = c("POST", f"/api/dossiers/{dossier_pm}/kyc/pm/actionnaires",
                        role="clerc",
                        json_body={"raison_sociale_nom": f"Actionnaire QA {i}",
                                   "type_personne": "PP", "pourcentage": 25.0,
                                   "pays_residence": "CI", "ordre": i}).json() or {}
                self.remember("act_id" if i == 1 else "act_id_2", act.get("id"))

        # -- Transaction + scoring (crée l'évaluation de risque et ses axes) --
        c("PATCH", f"/api/dossiers/{dossier_id}/transaction", role="clerc", json_body={
            "montant_tranche": "plus_15m", "montant_transaction": 25_000_000,
            "mode_paiement": "especes"})
        c("POST", f"/api/dossiers/{dossier_id}/scoring/calculate", role="conformite",
          json_body={"axes": {}, "montant_transaction": 25_000_000,
                     "mode_paiement": "especes", "nb_parties": 2,
                     "sur_liste_sanctions": False, "pays_liste_noire_gafi": False,
                     "pays_liste_grise_gafi": False, "refus_documents": False,
                     "be_non_identifiable": False, "overrides": []})
        # Seuls T5/T6 sont déclenchables à la main (les autres sont calculés).
        c("POST", f"/api/dossiers/{dossier_id}/trigger-manuel", role="conformite",
          json_body={"trigger": "T5", "commentaire": "QA couverture"})

        # -- Commentaire, documents (deux : un pour download, un pour DELETE) --
        c("POST", f"/api/dossiers/{dossier_id}/commentaires", role="clerc",
          json_body={"contenu": "Commentaire QA couverture"})
        for i in (1, 2):
            raw, ctype = multipart({"type_document": "piece_identite"},
                                   [("file", f"qa-doc-{i}.pdf", MINIMAL_PDF)])
            doc = c("POST", f"/api/dossiers/{dossier_id}/documents", role="clerc",
                    raw_body=raw, content_type=ctype).json() or {}
            self.remember("doc_id" if i == 1 else "doc_id_2", doc.get("id"))

        # -- Autorisation dirigeant (WRK09) --
        c("POST", f"/api/dossiers/{dossier_id}/autorisation", role="notaire",
          json_body={"decision": "AUTORISE", "justification": "QA couverture"})

        # -- Alertes (deux : une à traiter, une pour blocage/déblocage) --
        for i, niveau in ((1, "ELEVE"), (2, "MOYEN")):
            a = c("POST", "/api/alertes", role="conformite", json_body={
                "dossier_id": dossier_id, "type_alerte": "T2_ESPECES",
                "niveau": niveau, "description": f"Alerte QA {i}"}).json() or {}
            self.remember("alerte_id" if i == 1 else "alerte_id_2", a.get("id"))
        c("POST", "/api/alertes/signaler", role="clerc",
          json_body={"description": "Signalement interne QA",
                     "dossier_reference": self.dossier_ref})

        # -- DOS : une par dossier (contrainte d'unicité), d'où l'usage du dossier
        #    PM pour disposer d'une seconde DOS jetable (classement, addendums). --
        for i, target in ((1, dossier_id), (2, dossier_pm)):
            if not target:
                continue
            dos = c("POST", "/api/dos", role="conformite",
                    json_body={"dossier_id": target}).json() or {}
            self.remember("dos_id" if i == 1 else "dos_id_2", dos.get("id"))
        dos_id = self.ctx.get("dos_id")
        if dos_id:
            c("PUT", f"/api/dos/{dos_id}", role="conformite", json_body={
                "organisme_libelle": "CENTIF", "statut_operation": "executee",
                "date_detection": date.today().isoformat(),
                "type_soupcon_bc": True,
                "indices_blanchiment": "Espèces > 15M FCFA",
                "detail_transactions": [{"montant": 25_000_000, "devise": "FCFA",
                                         "mode_paiement": "especes",
                                         "date_transaction": date.today().isoformat(),
                                         "description": "QA"}],
            })

        # -- Révisions KYC (deux : une à valider, une à patcher) --
        for i in (1, 2):
            rev = c("POST", "/api/revisions", role="conformite", json_body={
                "dossier_id": dossier_id,
                "date_echeance": (date.today() + timedelta(days=30)).isoformat(),
            }).json() or {}
            self.remember("revision_id" if i == 1 else "revision_id_2", rev.get("id"))

        # -- Procédures, fichiers et listes de sanctions : réservés à l'admin, donc
        #    créés dans le cabinet QA (le seul où le script dispose de ce rôle). --
        proc = c("POST", "/api/procedures", role="admin",
                 json_body={"nom": f"Procédure QA {self.tag}"}).json() or {}
        if isinstance(proc, dict):
            self.remember("procedure_id", proc.get("id"))
        if self.ctx.get("procedure_id"):
            for slot in (1, 2):
                raw, ctype = multipart({"slot": str(slot)},
                                       [("file", f"proc-{slot}.pdf", MINIMAL_PDF)])
                f = c("POST", f"/api/procedures/{self.ctx['procedure_id']}/files",
                      role="admin", raw_body=raw, content_type=ctype).json() or {}
                if isinstance(f, dict):
                    self.remember("file_id" if slot == 1 else "file_id_2", f.get("id"))

        raw, ctype = multipart({"nom": f"Liste QA {self.tag}", "type_liste": "OFAC"},
                               [("file", "sanctions.csv",
                                 b"nom,date_naissance,pays\nQA SUSPECT,1970-01-01,CI\n")])
        lst = c("POST", "/api/sanctions/upload", role="admin",
                raw_body=raw, content_type=ctype).json() or {}
        if isinstance(lst, dict):
            self.remember("liste_id", lst.get("id"))

        # -- Identifiants découverts dynamiquement (registres : clés statiques) --
        regs = c("GET", "/api/registres", role="notaire").json() or {}
        items = regs if isinstance(regs, list) else (regs.get("items") or regs.get("registres") or [])
        if items:
            first = items[0]
            self.remember("registre_id", first.get("id") if isinstance(first, dict) else first)

        self.ctx.setdefault("dos_id", self.ctx.get("dos_id_2"))
        print(f"  contexte : {json.dumps(self.ctx, indent=2, ensure_ascii=False)}")

    # ---- phase 2 : sweep générique de toutes les opérations ---- #

    def substitute(self, path, method):
        """Remplace chaque `{param}` par un identifiant réel du contexte.

        Faute de correspondance, on injecte un UUID : la route répondra 404, ce
        qui reste un signal exploitable (elle n'a pas planté).
        """
        missing = []

        def repl(m):
            name = m.group(1)
            # Les sous-ressources KYC PM vivent sur le dossier PM.
            if name == "dossier_id" and "/kyc/pm" in path:
                return self.ctx.get("dossier_pm_id") or self.ctx.get("dossier_id") or str(uuid.uuid4())
            if "/kyc/pm/be" in path and name == "be_id":
                key = "pm_be_id"
            elif "/kyc/pm/ppe" in path and name == "ppe_id":
                key = "pm_ppe_id"
            else:
                key = name
            # Les DELETE consomment la ressource : on leur réserve le doublon.
            if method == "delete" and self.ctx.get(key + "_2"):
                key = key + "_2"
            val = self.ctx.get(key)
            if not val:
                missing.append(name)
                return str(uuid.uuid4())
            return str(val)

        return re.sub(r"\{([^}]+)\}", repl, path), missing

    def sweep(self):
        faker = SchemaFaker(self.spec, self.ctx)
        # Ordre : lectures d'abord, écritures ensuite, destructions en dernier —
        # une suppression prématurée priverait les autres routes de leur cible.
        order = {"get": 0, "post": 1, "put": 2, "patch": 3, "delete": 9}
        ops = []
        for path, item in self.spec["paths"].items():
            for method, op in item.items():
                if method not in order:
                    continue
                ops.append((order[method], path, method, op))
        ops.sort(key=lambda o: (o[0], o[1]))

        for _, path, method, op in ops:
            if (method, path) in SKIP_PATHS:
                continue
            self.exercise(path, method, op, faker)

    def role_order(self, path):
        """Rôle le plus plausible en premier, puis repli sur TOUS les autres.

        Le repli complet est essentiel : une route laissée en 403 n'aurait jamais
        atteint son code métier, donc n'aurait rien prouvé sur les 5xx.
        """
        if path.startswith("/api/super-admin"):
            return ["superadmin"]
        if path.startswith(("/api/sanctions", "/api/scoring/weights", "/api/procedures",
                            "/api/procedure-files", "/api/admin")):
            head = ["admin"]
        elif path.startswith(("/api/dos", "/api/revisions", "/api/alertes")):
            head = ["conformite", "notaire"]
        else:
            head = ["notaire", "conformite"]
        # `jetable` en dernier : c'est le seul compte dont le script connaît l'id,
        # donc le seul à passer les contrôles « soi-même » (GET /users/{id}).
        return head + [r for r in ("admin", "clerc", "notaire", "conformite", "jetable")
                       if r not in head]

    def exercise(self, path, method, op, faker):
        url_path, missing = self.substitute(path, method)
        json_body, raw_body, ctype = faker.body_for(op)
        query = faker.query_for(op)
        note = f"param sans cible: {','.join(missing)}" if missing else ""

        # Corps « métier » : le faker ne peut pas deviner ces valeurs, et sans
        # elles la route s'arrête en 422 avant d'atteindre le code à tester.
        override = self.body_override(method, path)
        if override is not None:
            json_body = override
        query.update(self.query_override(method, path))

        timeout = STREAM_TIMEOUT if path in STREAM_PATHS else 60

        last = None
        for role in self.role_order(path):
            if role not in self.tokens or not self.tokens[role]:
                continue
            q = dict(query or {})
            cookies = None
            # Le flux SSE ne peut pas porter d'en-tête : son jeton passe en query.
            if path in STREAM_PATHS:
                q["token"] = self.tokens[role]
            # `/auth/refresh` lit le refresh token dans un cookie httpOnly.
            if path == "/api/auth/refresh" and self.refresh_tokens.get(role):
                cookies = {"refresh_token": self.refresh_tokens[role]}
            resp = self.call(method, url_path, role=role, phase="sweep", note=note,
                             json_body=json_body, raw_body=raw_body, content_type=ctype,
                             query=q or None, timeout=timeout, cookies=cookies,
                             stream_lines=4 if path in STREAM_PATHS else 0)
            last = resp
            if resp.status not in (401, 403):
                break
        if last is None:
            print(f"  -- ignoré (aucun jeton) {method.upper()} {path}")

    def query_override(self, method, path):
        """Paramètres de requête « métier » : sans eux la route s'arrête en 422."""
        if path.endswith("/statut") and method == "patch":
            return {"new_statut": "en_analyse", "commentaire": "Sweep QA"}
        return {}

    def body_override(self, method, path):
        """Corps spécifiques : valeurs métier que le schéma seul ne fournit pas."""
        d = self.ctx.get("dossier_id")
        # Identifiants réels : un login au hasard sortirait en 401 sans rien tester.
        if path == "/api/auth/login":
            return {"email": ACCOUNTS[0][1], "password": ACCOUNTS[0][2]}
        if path == "/api/super-admin/auth/login":
            return {"email": SUPERADMIN[0], "password": SUPERADMIN[1]}
        if path.endswith("/scoring/calculate"):
            return {"axes": {}, "montant_transaction": 20_000_000,
                    "mode_paiement": "virement", "nb_parties": 2, "overrides": []}
        if path == "/api/alertes" and method == "post":
            return {"dossier_id": d, "type_alerte": "T4_GAFI", "niveau": "MOYEN",
                    "description": "Sweep QA"}
        if path == "/api/dos" and method == "post":
            return {"dossier_id": d}
        if path == "/api/revisions" and method == "post":
            return {"dossier_id": d,
                    "date_echeance": (date.today() + timedelta(days=60)).isoformat()}
        if path.endswith("/trigger-manuel"):
            return {"trigger": "T6", "commentaire": "Sweep QA"}
        if path == "/api/alertes/signaler":
            return {"description": "Sweep QA signalement",
                    "dossier_reference": getattr(self, "dossier_ref", None)}
        if path == "/api/sanctions/cribler":
            return {"nom": "KOUASSI Ama", "dossier_id": d, "seuil": 85.0}
        if path == "/api/kyc/screening/pre-check":
            return {"nom": "KOUASSI Ama", "date_naissance": "1985-04-12"}
        if path.endswith("/assign") and method == "patch":
            return {"assigned_to": self.ctx.get("user_id")}
        if path.endswith("/traiter"):
            if method == "post":
                return {"justification": "Traitement QA", "action_dossier": None}
            return {"statut": "traitee", "resolution_note": "Traitement QA"}
        if path.endswith("/autorisation") and method == "post":
            return {"decision": "AUTORISE", "justification": "Sweep QA"}
        if path == "/api/scoring/weights" and method == "put":
            return {"weights": {}, "seuil_especes_t2_fcfa": 15_000_000}
        if path.startswith("/api/rapports/") and method == "post":
            return {"date_debut": (date.today() - timedelta(days=90)).isoformat(),
                    "date_fin": date.today().isoformat(),
                    "dossier_id": d, "format": "pdf"}
        if path == "/api/dossiers" and method == "post":
            return {"type_client": "PP", "type_operation": "succession",
                    "montant_transaction": 1_000_000, "mode_paiement": "cheque",
                    "nb_parties": 1}
        # Sur /users et /admin/users, on ne touche jamais aux comptes de démo.
        if path.startswith("/api/users/{user_id}") and method == "patch":
            return {"first_name": "QA", "last_name": "Jetable", "is_active": True}
        return None

    # ---- phase 3 : routes destructives / à effet de bord global ---- #

    def destructive(self):
        c = self.call
        uid = self.ctx.get("user_id")
        tid = self.ctx.get("tenant_id")

        # TOTP : seuls les rôles de supervision d'un cabinet à `totp_required` y ont
        # droit. Le cabinet de démo l'a désactivé — d'où l'admin du cabinet QA.
        # setup -> activate (code recalculé) -> codes de secours -> désactivation.
        if self.tokens.get("admin"):
            s = c("POST", "/api/auth/totp/setup", role="admin", phase="final",
                  json_body={}).json() or {}
            uri = (s or {}).get("provisioning_uri") or ""
            m = re.search(r"secret=([A-Z2-7]+)", uri, re.I)
            secret = m.group(1) if m else None
            if secret:
                c("POST", "/api/auth/totp/activate", role="admin", phase="final",
                  json_body={"code": totp_code(secret)})
                c("POST", "/api/auth/totp/verify", role="admin", phase="final",
                  json_body={"code": totp_code(secret)})
                c("POST", "/api/auth/totp/backup-codes/regenerate", role="admin",
                  phase="final", json_body={})
            if self.qa_admin_id:
                c("DELETE", f"/api/admin/users/{self.qa_admin_id}/totp",
                  role="admin", phase="final")

        if self.tokens.get("jetable"):
            c("PATCH", "/api/auth/password", role="jetable", phase="final",
              json_body={"current_password": QA_PASSWORD,
                         "new_password": QA_PASSWORD[:-1] + "y"})

        if uid:
            c("DELETE", f"/api/admin/users/{uid}/totp", role="notaire", phase="final")
            c("POST", f"/api/admin/users/{uid}/reset-password", role="notaire",
              phase="final", json_body={"new_password": QA_PASSWORD,
                                        "must_change_password": False})
            c("POST", f"/api/admin/users/{uid}/reset-password/temporary",
              role="notaire", phase="final", json_body={})
            c("POST", f"/api/admin/users/{uid}/revoke-sessions", role="notaire",
              phase="final", json_body={})
            c("DELETE", f"/api/users/{uid}", role="notaire", phase="final")

        # Cycle de vie du cabinet jetable (archive en dernier : état terminal).
        if tid:
            c("POST", f"/api/super-admin/tenants/{tid}/suspend", role="superadmin",
              phase="final", json_body={"motif": "QA couverture"})
            c("POST", f"/api/super-admin/tenants/{tid}/activate", role="superadmin",
              phase="final", json_body={"motif": "QA couverture"})
            c("POST", f"/api/super-admin/tenants/{tid}/archive", role="superadmin",
              phase="final", json_body={"motif": "QA couverture"})

        # Déconnexion en dernier : elle invalide le jeton utilisé.
        c("POST", "/api/auth/logout", role="clerc", phase="final", json_body={})

    # ---- exécution ---- #

    def run(self):
        print("== 0. OpenAPI ==")
        r = request("GET", f"{self.base}/openapi.json")
        if r.status != 200:
            sys.exit(f"OpenAPI indisponible : {r.status} {r.error or r.body[:200]}")
        self.spec = r.json()
        total = sum(1 for _, i in self.spec["paths"].items() for m in i
                    if m in ("get", "post", "put", "patch", "delete"))
        print(f"  {len(self.spec['paths'])} chemins, {total} opérations")

        print("== 1. Authentification ==")
        self.authenticate()
        print("== 2. Jeu de données ==")
        self.seed()
        print("== 3. Sweep générique ==")
        self.sweep()
        print("== 4. Routes destructives ==")
        self.destructive()
        return self.report()

    def report(self):
        rows = self.rec.rows
        by_status = {}
        for r in rows:
            by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        covered = {(r["method"], r["path"]) for r in rows}

        print("\n" + "=" * 78)
        print(f"APPELS         : {len(rows)}")
        print(f"ROUTES TOUCHÉES: {len(covered)}")
        print("RÉPARTITION    :")
        for st in sorted(by_status):
            label = "TIMEOUT/RÉSEAU" if st == 0 else st
            print(f"  {str(label):>15} : {by_status[st]}")

        fails = self.rec.failures
        print(f"\n5xx / ÉCHECS : {len(fails)}")
        seen = set()
        for f in fails:
            key = (f["method"], f["path"], f["status"])
            if key in seen:
                continue
            seen.add(key)
            print(f"  [{f['status']}] {f['method']} {f['path']}  (rôle={f['role']})")
            print(f"        {f['body'][:300]}")
        print("=" * 78)
        return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--json", help="Écrit le journal complet des appels dans ce fichier")
    args = ap.parse_args()

    cov = Coverage(args.base_url)
    fails = cov.run()
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(cov.rec.rows, fh, ensure_ascii=False, indent=2)
        print(f"Journal : {args.json}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
