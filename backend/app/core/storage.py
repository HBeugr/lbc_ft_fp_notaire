"""Stockage documentaire MinIO — cloisonné par cabinet.

Troisième niveau de l'isolation multi-tenant (après le schéma PostgreSQL et
l'espace de noms Redis) : chaque cabinet dispose de son **propre bucket**. Un
bucket unique partagé exposerait tous les actes et pièces d'identité derrière
une seule clé S3 — une erreur de `minio_key` suffirait à faire fuiter un
document d'un cabinet vers un autre. Le cloisonnement physique rend la fuite
impossible plutôt que simplement improbable.

Le client MinIO est centralisé ici : il était auparavant dupliqué dans
`routers/documents.py` et `routers/procedures.py`, avec deux façons divergentes
de créer le bucket.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

from minio import Minio

from app.core.config import settings
from app.core.tenant_context import TenantContext, get_current_tenant

_client: Minio | None = None

# Contraintes de nommage S3/MinIO : 3 à 63 caractères, minuscules, chiffres et
# tirets, ni en tête ni en fin.
_BUCKET_MIN_LEN = 3
_BUCKET_MAX_LEN = 63


def get_minio_client() -> Minio:
    """Client MinIO partagé (une seule connexion pool pour tout le process)."""
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
    return _client


def normalize_bucket_name(raw: str) -> str:
    """Rend un nom de bucket conforme aux règles S3/MinIO.

    Le slug d'un cabinet est saisi par le Super-Admin : il peut contenir des
    accents, des espaces ou des majuscules, qu'un bucket S3 refuse. Plutôt que
    de rejeter le provisioning, on normalise de façon **déterministe** (même
    entrée → même bucket, sinon un cabinet perdrait l'accès à ses documents) :

      - translittération ASCII (« étude-koné » → « etude-kone ») ;
      - passage en minuscules, tout caractère hors [a-z0-9] devenant un tiret ;
      - tirets consécutifs fusionnés, tirets de bord supprimés ;
      - au-delà de 63 caractères, troncature suffixée d'une empreinte du nom
        d'origine — deux slugs longs partageant leur préfixe ne peuvent donc pas
        retomber sur le même bucket ;
      - en deçà de 3 caractères, complété par « -cabinet ».
    """
    ascii_name = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower())
    name = re.sub(r"-{2,}", "-", name).strip("-")

    if len(name) > _BUCKET_MAX_LEN:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
        name = f"{name[: _BUCKET_MAX_LEN - len(digest) - 1].rstrip('-')}-{digest}"
    if len(name) < _BUCKET_MIN_LEN:
        name = f"{name}-cabinet".strip("-")
    return name


def bucket_for_slug(slug: str) -> str:
    """Nom de bucket dérivé d'un slug — utilisé au provisioning, avant que le
    cabinet n'existe en contexte."""
    return normalize_bucket_name(f"{settings.MINIO_BUCKET_DOCUMENTS}-{slug}")


def bucket_for(tenant: TenantContext) -> str:
    """Nom du bucket d'un cabinet donné.

    On lit le nom figé à la création (`shared.tenants.storage_bucket`) plutôt que
    de le recalculer : un cabinet qui changerait de slug perdrait sinon l'accès à
    tous ses documents déjà stockés.
    """
    return tenant.storage_bucket or bucket_for_slug(tenant.slug)


def tenant_bucket() -> str:
    """Bucket du cabinet courant.

    Lève `NoTenantContextError` hors contexte tenant : écrire un document sans
    cabinet identifié serait un défaut d'isolation, jamais un cas nominal.
    """
    return bucket_for(get_current_tenant())


def ensure_tenant_bucket(bucket: str) -> None:
    """Crée le bucket s'il n'existe pas — idempotent.

    Appelé au provisioning d'un cabinet, pas au démarrage de l'API : en
    multi-tenant, le process ne connaît pas d'avance la liste des cabinets.
    """
    client = get_minio_client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def ensure_current_tenant_bucket() -> str:
    """Garantit le bucket du cabinet courant et retourne son nom."""
    bucket = tenant_bucket()
    ensure_tenant_bucket(bucket)
    return bucket
