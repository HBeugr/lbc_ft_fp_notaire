from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # App
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"  # nosec B104 — bind volontaire (conteneur derrière reverse-proxy)
    APP_PORT: int = 8000
    APP_CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Database — PostgreSQL (SaaS multi-tenant : 1 schéma par cabinet)
    DB_HOST: str = "db"
    DB_PORT: int = 5432
    DB_NAME: str = "notaire_lbcft"
    DB_USER: str
    DB_PASSWORD: str
    DB_ROOT_PASSWORD: str = ""
    DOS_DB_USER: str
    DOS_DB_PASSWORD: str

    # Multi-tenant
    SHARED_SCHEMA: str = "shared"
    TENANT_SCHEMA_PREFIX: str = "tenant_"
    # Clé maîtresse : les clés AES par tenant en sont dérivées (HKDF). Ne jamais
    # réutiliser AES_KEY directement pour des données métier en multi-tenant.
    TENANT_MASTER_KEY: str = ""

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_DOCUMENTS: str = "notaire-documents"
    MINIO_USE_SSL: bool = False

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_HOURS: int = 8

    # Encryption
    AES_KEY: str

    # 2FA — désactivé par défaut sur develop. Réactiver en prod via env var TOTP_REQUIRED=true.
    TOTP_ISSUER: str = "Notaire-LBC-FT-FP"
    TOTP_REQUIRED: bool = False

    # Scoring — T2 : espèces > 15M FCFA (Art. 72, verrouillé)
    ESPECES_THRESHOLD_FCFA: int = 15_000_000

    @property
    def DB_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


    def tenant_schema(self, tenant_id: str) -> str:
        """Nom du schéma PostgreSQL d'un tenant. Un tenant_id est un UUID :
        les tirets sont remplacés car un identifiant PG non quoté ne les admet pas."""
        return f"{self.TENANT_SCHEMA_PREFIX}{tenant_id.replace('-', '')}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
