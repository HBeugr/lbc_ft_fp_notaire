"""Chiffrement au repos (AES-256 via Fernet) des colonnes sensibles — CDC §5.2.

`EncryptedString` est un type SQLAlchemy transparent : chiffrement à l'écriture,
déchiffrement à la lecture. Les valeurs chiffrées sont préfixées par `enc::` afin
de distinguer une donnée chiffrée d'une donnée historique en clair (rétro-
compatibilité : une valeur sans préfixe est renvoyée telle quelle).

La clé est dérivée de `settings.AES_KEY` (32 octets, comme pour le TOTP). Les clés
sont gérées séparément des données (variable d'environnement / secret).
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, Text

from app.core.config import settings

_PREFIX = "enc::"
_fernet_cache: Fernet | None = None


def _fernet() -> Fernet:
    global _fernet_cache
    if _fernet_cache is None:
        # Dérivation robuste d'une clé Fernet de 32 octets quelle que soit la forme
        # de AES_KEY (base64 de 32 octets, hex, ou phrase secrète) : SHA-256.
        key_bytes = hashlib.sha256(settings.AES_KEY.encode("utf-8")).digest()
        _fernet_cache = Fernet(base64.urlsafe_b64encode(key_bytes))
    return _fernet_cache


class EncryptedString(TypeDecorator):
    """Colonne TEXT chiffrée (Fernet/AES-256) — transparent à l'usage."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        token = _fernet().encrypt(str(value).encode("utf-8")).decode("ascii")
        return _PREFIX + token

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.startswith(_PREFIX):
            try:
                return _fernet().decrypt(value[len(_PREFIX):].encode("ascii")).decode("utf-8")
            except (InvalidToken, ValueError):
                return value
        return value  # donnée héritée en clair
