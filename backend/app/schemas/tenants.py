"""Schémas d'exploitation de la plateforme (console Super-Admin).

Aucun de ces schémas n'expose de donnée métier LBC/FT : le Super-Admin
administre des cabinets, pas des dossiers.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.password_policy import validate_password_strength


class SuperAdminLoginRequest(BaseModel):
    email: str
    password: str


class SuperAdminOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    must_change_password: bool = False

    model_config = {"from_attributes": True}


class SuperAdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    super_admin: SuperAdminOut


class SuperAdminPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)

    @field_validator("new_password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return validate_password_strength(v)


class TenantCreateRequest(BaseModel):
    """Formulaire de création d'un cabinet.

    Le compte administrateur est créé dans la foulée : sans lui, le cabinet
    serait un schéma vide auquel personne ne pourrait se connecter.
    """

    nom_cabinet: str = Field(..., min_length=2, max_length=255)
    contact_email: EmailStr
    admin_email: EmailStr
    admin_first_name: str = Field(..., min_length=1, max_length=100)
    admin_last_name: str = Field(..., min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=64)
    numero_agrement: str | None = Field(default=None, max_length=64)
    pays: str = Field(default="CI", min_length=2, max_length=2)
    contact_telephone: str | None = Field(default=None, max_length=32)
    adresse: str | None = None
    totp_required: bool = True
    # 0 = illimité. Support d'un futur plan tarifaire.
    max_users: int = Field(default=0, ge=0)


class TenantOut(BaseModel):
    id: str
    slug: str
    nom_cabinet: str
    statut: str
    pays: str
    contact_email: str
    contact_telephone: str | None = None
    adresse: str | None = None
    numero_agrement: str | None = None
    totp_required: bool
    max_users: int
    motif_suspension: str | None = None
    logo_updated_at: datetime | None = None
    created_at: datetime | None = None
    activated_at: datetime | None = None
    suspended_at: datetime | None = None

    model_config = {"from_attributes": True}


class TenantCreateResponse(BaseModel):
    """Réponse de provisioning.

    `admin_temp_password` n'est retourné qu'ici, à la création : il n'est stocké
    nulle part en clair et ne peut plus être relu ensuite.
    """

    tenant: TenantOut
    admin_email: str
    admin_temp_password: str


class TenantStatutRequest(BaseModel):
    motif: str | None = Field(default=None, max_length=1000)


class TenantMetricsOut(BaseModel):
    """Métriques d'exploitation — volumétrie uniquement, jamais de contenu."""

    tenant_id: str
    utilisateurs_actifs: int
    utilisateurs_total: int
    quota_utilisateurs: int
    dossiers_total: int


class MigrationResultOut(BaseModel):
    resultats: dict[str, str]


class TenantContextOut(BaseModel):
    """Cabinet de la session courante — alimente le branding et le portier côté client."""

    id: str
    slug: str
    nom_cabinet: str
    statut: str
    totp_required: bool
    max_users: int
    # Identité du cabinet, affichée dans « Mon cabinet ». Ce sont des données
    # d'en-tête, pas des données de conformité : les exposer à ses propres
    # utilisateurs ne rompt aucun cloisonnement.
    pays: str
    numero_agrement: str | None = None
    # Horodatage du logo : sert de « cache-buster » côté interface, pour qu'un
    # changement de logo soit visible immédiatement sans vider le cache navigateur.
    logo_updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class LogoOut(BaseModel):
    """Résultat d'un envoi de logo."""

    logo_updated_at: datetime | None = None
    largeur: int
    hauteur: int
    content_type: str


class LogoContraintesOut(BaseModel):
    """Contraintes d'image, affichées AVANT l'envoi.

    Les exposer évite à l'utilisateur de découvrir la règle par un refus.
    """

    formats: list[str]
    taille_max_octets: int
    dimension_min_px: int
    dimension_max_px: int
    ratio_max: float
