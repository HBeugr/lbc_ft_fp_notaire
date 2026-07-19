"""Validation centralisée des pièces uploadées (défense en profondeur).

Trois niveaux, du plus faible au plus fort :

1. **extension** déclarée dans le nom de fichier ;
2. **content-type** déclaré par le client ;
3. **signature réelle** (magic-bytes) lue dans le contenu.

Les deux premiers niveaux sont *déclaratifs* : un attaquant les contrôle
entièrement (il suffit de renommer un fichier ou de forger l'en-tête
`Content-Type`). Seul le troisième fait foi. Il est ici implémenté **en Python
pur**, sans dépendre de `libmagic` : la bibliothèque `python-magic` n'est pas
garantie présente dans l'image (elle repose sur une bibliothèque C système), et
un contrôle de sécurité ne doit pas *échouer en silence en laissant passer* (« fail
open ») quand une dépendance optionnelle manque. `libmagic`, s'il est présent,
n'est plus qu'une vérification supplémentaire — jamais l'unique rempart.

Règle appliquée : le fichier est refusé si le nom/type déclaré n'est pas
autorisé, OU si son contenu réel ne correspond à AUCUN format autorisé (fichier
déguisé : HTML/script/exécutable renommé en `.pdf`, etc.).
"""
from fastapi import HTTPException, status

ACCEPTED_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx")
ACCEPTED_CONTENT_TYPES = {
    "application/pdf", "image/jpeg", "image/jpg", "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",  # docx/xlsx sont des conteneurs zip
}
# MIME détectés par libmagic acceptés (pdf/jpg/png signés ; docx/xlsx = zip)
ACCEPTED_MAGIC_MIME = {"application/pdf", "image/jpeg", "image/png", "application/zip"}

# Familles de signatures réellement autorisées pour les documents KYC.
# 'zip' couvre les conteneurs OOXML (docx/xlsx).
ACCEPTED_SIGNATURE_FAMILIES = frozenset({"pdf", "jpeg", "png", "zip"})

_DETAIL = "Format non autorisé ou contenu ne correspondant pas à l'extension (fichier déguisé)."


def sniff_signature(content: bytes) -> str | None:
    """Détecte le format réel d'un fichier à partir de ses octets de tête.

    Retourne 'pdf' | 'jpeg' | 'png' | 'zip' | None. En Python pur : aucun binaire
    externe requis, donc aucune dégradation silencieuse. Le résultat fait foi,
    contrairement à l'extension et au content-type qui sont déclaratifs.
    """
    if not content:
        return None
    head = content[:16]
    # PNG : 89 50 4E 47 0D 0A 1A 0A
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    # JPEG : FF D8 FF
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    # ZIP (docx/xlsx OOXML) : "PK" suivi de 03 04 / 05 06 / 07 08
    if head.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    # PDF : la spec (§7.5.2) autorise jusqu'à ~1 Ko d'en-tête avant "%PDF".
    # On tolère cette latitude tout en restant borné.
    if b"%PDF" in content[:1024]:
        return "pdf"
    return None


def _ext_or_type_ok(filename: str | None, content_type: str | None) -> bool:
    ext_ok = bool(filename) and filename.lower().endswith(ACCEPTED_EXTENSIONS)
    type_ok = (content_type or "").lower() in ACCEPTED_CONTENT_TYPES
    return ext_ok or type_ok


def _magic_mime(content: bytes) -> str | None:
    try:
        import magic  # python-magic
    except Exception:
        return None
    try:
        return magic.from_buffer(content[:4096], mime=True)
    except Exception:
        return None


def ensure_allowed_upload(
    filename: str | None,
    content_type: str | None,
    content: bytes,
    allowed_families: frozenset[str] = ACCEPTED_SIGNATURE_FAMILIES,
) -> None:
    """Lève HTTP 400 si le fichier n'est pas d'un format autorisé (ou est déguisé).

    Le contrôle décisif est la **signature réelle** du contenu : le nom et le type
    déclarés ne suffisent jamais à eux seuls.
    """
    if not _ext_or_type_ok(filename, content_type):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_DETAIL)
    # Rempart principal : le contenu doit RÉELLEMENT être d'un format autorisé.
    family = sniff_signature(content)
    if family is None or family not in allowed_families:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_DETAIL)
    # Défense supplémentaire si libmagic est présent — mais jamais l'unique rempart.
    detected = _magic_mime(content)
    if detected is not None and detected not in ACCEPTED_MAGIC_MIME:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_DETAIL)
