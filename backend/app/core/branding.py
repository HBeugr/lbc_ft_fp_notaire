"""Logo du cabinet — validation et stockage.

Le logo est une donnée d'identité du cabinet, pas une donnée métier : il est
néanmoins stocké dans le **bucket du cabinet**, comme tout fichier, afin de ne
pas créer d'exception au cloisonnement de l'isolation de niveau 3.

Les contraintes de format sont volontairement strictes : le logo est affiché
dans la barre latérale de chaque page et dans les exports. Accepter n'importe
quelle image conduirait à des interfaces déformées et à des pages inutilement
lourdes.
"""
from __future__ import annotations

import io

from app.core.storage import bucket_for, ensure_tenant_bucket, get_minio_client
from app.core.tenant_context import TenantContext

# Emplacement dans le bucket du cabinet. Un chemin fixe : un cabinet n'a qu'un
# logo, et l'écraser doit remplacer l'ancien plutôt que l'accumuler.
LOGO_PREFIX = "branding/logo"

# SVG volontairement exclu : un SVG peut embarquer du script, et il serait servi
# depuis notre propre origine. Le bénéfice visuel ne vaut pas la surface d'attaque.
FORMATS_ACCEPTES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

TAILLE_MAX_OCTETS = 1024 * 1024          # 1 Mo
DIMENSION_MIN = 64                        # px — en deçà, illisible une fois affiché
DIMENSION_MAX = 2048                      # px — au-delà, poids inutile
RATIO_MAX = 4.0                           # largeur/hauteur, dans un sens comme dans l'autre


class LogoInvalide(ValueError):
    """Le fichier fourni ne satisfait pas les contraintes d'affichage."""


def valider_logo(contenu: bytes, content_type: str | None) -> tuple[str, str, int, int]:
    """Valide un logo et retourne (content_type, extension, largeur, hauteur).

    Le type déclaré par le client n'est pas cru sur parole : c'est le contenu
    réel de l'image qui fait foi, sinon un fichier arbitraire renommé en `.png`
    passerait.
    """
    if not contenu:
        raise LogoInvalide("Fichier vide.")
    if len(contenu) > TAILLE_MAX_OCTETS:
        raise LogoInvalide(
            f"Fichier trop volumineux ({len(contenu) // 1024} Ko) — maximum "
            f"{TAILLE_MAX_OCTETS // 1024} Ko."
        )

    try:
        from PIL import Image

        with Image.open(io.BytesIO(contenu)) as image:
            image.verify()  # détecte les fichiers corrompus ou falsifiés
        with Image.open(io.BytesIO(contenu)) as image:
            largeur, hauteur = image.size
            format_pil = (image.format or "").upper()
    except LogoInvalide:
        raise
    except Exception as exc:
        raise LogoInvalide("Fichier illisible : ce n'est pas une image valide.") from exc

    type_reel = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}.get(format_pil)
    if type_reel is None:
        raise LogoInvalide(
            f"Format non accepté ({format_pil or 'inconnu'}) — utilisez PNG, JPEG ou WebP."
        )
    if content_type and content_type not in FORMATS_ACCEPTES:
        raise LogoInvalide(f"Type déclaré non accepté ({content_type}).")

    if largeur < DIMENSION_MIN or hauteur < DIMENSION_MIN:
        raise LogoInvalide(
            f"Image trop petite ({largeur}×{hauteur} px) — minimum "
            f"{DIMENSION_MIN}×{DIMENSION_MIN} px."
        )
    if largeur > DIMENSION_MAX or hauteur > DIMENSION_MAX:
        raise LogoInvalide(
            f"Image trop grande ({largeur}×{hauteur} px) — maximum "
            f"{DIMENSION_MAX}×{DIMENSION_MAX} px."
        )

    ratio = max(largeur / hauteur, hauteur / largeur)
    if ratio > RATIO_MAX:
        raise LogoInvalide(
            f"Proportions trop allongées ({largeur}×{hauteur}) — le rapport ne doit pas "
            f"dépasser {RATIO_MAX:g}:1. Un logo carré ou légèrement large s'affiche le mieux."
        )

    return type_reel, FORMATS_ACCEPTES[type_reel], largeur, hauteur


def enregistrer_logo(tenant: TenantContext, contenu: bytes, content_type: str, extension: str) -> str:
    """Écrit le logo dans le bucket du cabinet et retourne sa clé."""
    bucket = bucket_for(tenant)
    ensure_tenant_bucket(bucket)
    cle = f"{LOGO_PREFIX}{extension}"

    client = get_minio_client()
    # Un cabinet peut changer de format (PNG → JPEG) : on retire l'ancien fichier
    # pour ne pas laisser d'orphelin dans le bucket.
    for ext in FORMATS_ACCEPTES.values():
        if ext != extension:
            try:
                client.remove_object(bucket, f"{LOGO_PREFIX}{ext}")
            except Exception:
                pass

    client.put_object(
        bucket, cle, io.BytesIO(contenu), length=len(contenu), content_type=content_type
    )
    return cle


def lire_logo(tenant: TenantContext, cle: str) -> bytes:
    """Relit le logo depuis le bucket du cabinet."""
    reponse = get_minio_client().get_object(bucket_for(tenant), cle)
    try:
        return reponse.read()
    finally:
        reponse.close()
        reponse.release_conn()


def supprimer_logo(tenant: TenantContext, cle: str) -> None:
    try:
        get_minio_client().remove_object(bucket_for(tenant), cle)
    except Exception:
        pass


def contraintes() -> dict:
    """Contraintes exposées à l'interface, pour qu'elle les affiche à l'utilisateur
    plutôt que de le laisser découvrir l'erreur après l'envoi."""
    return {
        "formats": sorted(FORMATS_ACCEPTES),
        "taille_max_octets": TAILLE_MAX_OCTETS,
        "dimension_min_px": DIMENSION_MIN,
        "dimension_max_px": DIMENSION_MAX,
        "ratio_max": RATIO_MAX,
    }
