"""Chiffrement au repos (AES-256 via Fernet) des colonnes sensibles — CDC §5.2.

`EncryptedString` est un type SQLAlchemy transparent : chiffrement à l'écriture,
déchiffrement à la lecture. Les valeurs chiffrées sont préfixées par `enc::` afin
de distinguer une donnée chiffrée d'une donnée historique en clair (rétro-
compatibilité : une valeur sans préfixe est renvoyée telle quelle).

**Isolation multi-tenant (niveau 2)** : chaque cabinet possède sa propre clé,
dérivée par HKDF-SHA256 de la clé maîtresse et du sel du cabinet
(`shared.tenants.key_salt`). Conséquence directe : la compromission des données
d'un cabinet n'expose aucun autre cabinet, et un défaut de routage de schéma se
solde par un échec de déchiffrement bruyant plutôt que par une fuite silencieuse.

La clé maîtresse ne chiffre jamais elle-même de données métier ; elle ne sert
qu'à la dérivation. Elle est gérée hors base (variable d'environnement / secret).
"""
import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy.types import Text, TypeDecorator

from app.core.config import settings
from app.core.tenant_context import get_current_tenant

_PREFIX = "enc::"
_HKDF_INFO = b"notaire-lbcft:column-encryption:v1"

# Cache des clés dérivées, par cabinet. La dérivation HKDF est peu coûteuse mais
# se produirait sur chaque colonne chiffrée de chaque ligne sans ce cache.
_fernet_cache: dict[str, Fernet] = {}


class TenantKeyError(RuntimeError):
    """Déchiffrement impossible avec la clé du cabinet courant.

    Signale soit une corruption, soit — bien plus grave — une donnée lue depuis
    le schéma d'un AUTRE cabinet. Ne jamais rattraper silencieusement.
    """


class MasterKeyManquante(RuntimeError):
    """`TENANT_MASTER_KEY` n'est pas configurée alors qu'elle est exigée."""


def _master_key() -> str:
    """Secret racine dont dérivent les clés de chiffrement de chaque cabinet.

    Le repli sur `AES_KEY` n'est toléré qu'en dehors de la production, et c'est
    délibéré : il constitue un piège différé. Si l'on démarre en production sans
    `TENANT_MASTER_KEY`, les données se chiffrent avec des clés dérivées d'`AES_KEY` ;
    le jour où quelqu'un renseigne enfin la variable — geste qui paraît anodin,
    voire vertueux — l'intégralité des données de TOUS les cabinets devient
    illisible, sauvegardes comprises, sans message d'erreur au moment de la faute.
    On refuse donc de démarrer plutôt que d'armer cette bombe.
    """
    if settings.TENANT_MASTER_KEY:
        return settings.TENANT_MASTER_KEY
    if settings.APP_ENV == "production":
        raise MasterKeyManquante(
            "TENANT_MASTER_KEY doit être définie en production. Les clés de "
            "chiffrement de chaque cabinet en dérivent : la renseigner APRÈS "
            "avoir écrit des données rendrait celles-ci définitivement illisibles. "
            "Générez-la une fois (`openssl rand -hex 32`), conservez-la hors de "
            "la plateforme, et ne la modifiez jamais."
        )
    return settings.AES_KEY


def derive_tenant_fernet(key_salt: str) -> Fernet:
    """Dérive la clé Fernet d'un cabinet à partir de la clé maîtresse et de son sel.

    Point d'entrée unique de la dérivation : tout ce qui chiffre des données d'un
    cabinet (colonnes sensibles, secrets TOTP) doit passer par ici, sous peine de
    voir réapparaître les dérivations divergentes que cette migration corrige.
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=key_salt.encode("utf-8"),
        info=_HKDF_INFO,
    )
    return Fernet(base64.urlsafe_b64encode(hkdf.derive(_master_key().encode("utf-8"))))


def _fernet() -> Fernet:
    tenant = get_current_tenant()
    cached = _fernet_cache.get(tenant.id)
    if cached is None:
        cached = derive_tenant_fernet(tenant.key_salt)
        _fernet_cache[tenant.id] = cached
    return cached


def forget_tenant_key(tenant_id: str) -> None:
    """Purge la clé d'un cabinet du cache (suspension, rotation, suppression)."""
    _fernet_cache.pop(tenant_id, None)


class EncryptedString(TypeDecorator):
    """Colonne TEXT chiffrée (Fernet/AES-256) — transparent à l'usage."""

    impl = Text
    # Le chiffrement dépend du cabinet courant : la valeur liée ne peut pas être
    # mise en cache dans le cache de requêtes compilées de SQLAlchemy.
    cache_ok = False

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
            except (InvalidToken, ValueError) as exc:
                # Auparavant on renvoyait le chiffré tel quel. En multi-tenant ce
                # serait le symptôme exact d'une lecture cross-cabinet : on échoue.
                raise TenantKeyError(
                    "Déchiffrement impossible avec la clé du cabinet courant — "
                    "défaut d'isolation ou donnée corrompue."
                ) from exc
        return value  # donnée héritée en clair
