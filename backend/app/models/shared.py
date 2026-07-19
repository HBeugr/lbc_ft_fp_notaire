"""Annuaire de routage multi-tenant — schéma `shared`.

Ces tables sont les SEULES qui vivent hors des schémas cabinet. Elles ne
contiennent aucune donnée métier LBC/FT : uniquement de quoi router une
connexion vers le bon schéma et administrer la plateforme.

Le Super-Admin de la plateforme n'a accès qu'à ce schéma — c'est ce qui rend
la séparation « exploitant / données de conformité » structurelle et non
seulement affaire d'interface (cf. confidentialité CENTIF, Art. 63).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import SharedBase

# Cycle de vie d'un cabinet. `suspendu` est le point d'accroche prévu pour un
# futur portier de facturation : accès bloqué, données intégralement conservées.
TENANT_STATUTS = ("configuration", "production", "suspendu", "archive")


class Tenant(SharedBase):
    """Un cabinet notarial abonné à la plateforme."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    nom_cabinet: Mapped[str] = mapped_column(String(255), nullable=False)
    # Schéma PostgreSQL dédié — dérivé de l'id, figé à la création.
    schema_name: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)

    statut: Mapped[str] = mapped_column(
        # Le schéma est explicite : sans lui, PostgreSQL créerait le type dans
        # `public`, hors de portée du `search_path` des sessions de l'annuaire.
        SAEnum(*TENANT_STATUTS, name="tenant_statut_enum", schema=settings.SHARED_SCHEMA),
        nullable=False,
        default="configuration",
    )

    # Isolation niveau 2 : sel propre au cabinet, dont sa clé AES-256 est dérivée
    # (HKDF sur TENANT_MASTER_KEY). Compromettre un cabinet n'expose pas les autres.
    key_salt: Mapped[str] = mapped_column(String(64), nullable=False)
    # Isolation niveau 3 : espace de stockage documentaire dédié.
    storage_bucket: Mapped[str] = mapped_column(String(63), nullable=False)

    # Identification du cabinet (Chambre des Notaires de Côte d'Ivoire)
    numero_agrement: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    pays: Mapped[str] = mapped_column(String(2), nullable=False, default="CI")
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_telephone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    adresse: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Politique appliquée au cabinet (surcharge les défauts globaux)
    totp_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Quota de sièges — 0 = illimité. Support d'un futur plan tarifaire.
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Identité visuelle du cabinet. Le fichier vit dans le bucket du cabinet
    # (isolation de niveau 3) ; seule sa référence est portée par l'annuaire,
    # afin que la barre latérale puisse l'afficher sans ouvrir de session métier.
    logo_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    logo_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    motif_suspension: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_active(self) -> bool:
        return self.statut == "production"


class TenantUser(SharedBase):
    """Aiguillage `email → cabinet`, consulté au login.

    C'est la « réception de l'immeuble » : le seul endroit où l'on peut associer
    un email à un cabinet avant de savoir dans quel schéma chercher.

    L'email est unique au niveau plateforme, ce qui permet un login par simple
    email/mot de passe sans demander le cabinet à l'utilisateur. `user_id`
    référence l'utilisateur dans le schéma du cabinet ; la FK n'est pas
    déclarable (cross-schéma dynamique), la cohérence est maintenue par le
    service de provisioning et la gestion des utilisateurs.
    """

    __tablename__ = "tenant_users"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SuperAdmin(SharedBase):
    """Exploitant de la plateforme — aveugle aux données métier des cabinets.

    Compte volontairement distinct de `users` : un Super-Admin n'existe dans
    aucun schéma cabinet, il ne peut donc pas obtenir de session métier.
    """

    __tablename__ = "super_admins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class TenantAuditLog(SharedBase):
    """Journal des actions d'exploitation (création, suspension, migration).

    Distinct de l'audit métier, qui reste dans le schéma de chaque cabinet et
    demeure inaccessible à l'exploitant.
    """

    __tablename__ = "tenant_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    super_admin_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
