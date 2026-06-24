"""Validation centralisée des pièces uploadées (défense en profondeur).

Trois niveaux : extension, content-type déclaré, et magic-bytes (signature réelle
via python-magic si disponible — sinon repli gracieux sur extension/content-type).
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

_DETAIL = "Format non autorisé ou contenu ne correspondant pas à l'extension (fichier déguisé)."


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


def ensure_allowed_upload(filename: str | None, content_type: str | None, content: bytes) -> None:
    """Lève HTTP 400 si le fichier n'est pas d'un format autorisé (ou est déguisé)."""
    if not _ext_or_type_ok(filename, content_type):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_DETAIL)
    detected = _magic_mime(content)
    if detected is not None and detected not in ACCEPTED_MAGIC_MIME:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_DETAIL)
