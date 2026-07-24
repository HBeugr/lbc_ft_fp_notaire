import uuid
from sqlalchemy import String, Boolean, Enum as SAEnum, DateTime, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

# Rôles reconnus. `role` porte le rôle PRINCIPAL (affichage, audit, en-tête des
# rapports) ; `roles_extra` porte les rôles cumulés.
ROLES_CONNUS = (
    "admin", "notaire_principal", "responsable_conformite",
    "clercs", "declarant_centif", "autre_utilisateur",
)

# Rôles de supervision : vue transversale + 2FA exigée (Art. 29).
ROLES_SUPERVISEURS = ("admin", "notaire_principal", "responsable_conformite")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        SAEnum(
            "admin",
            "notaire_principal",
            "responsable_conformite",
            "clercs",
            "declarant_centif",
            "autre_utilisateur",
            name="user_role_enum",
        ),
        nullable=False,
    )
    # Rôles CUMULÉS en plus de `role`. Une même personne (donc un même email, qui
    # reste la clé de connexion) peut porter plusieurs casquettes sans dupliquer
    # de compte — cas courant en petite étude. NULL/[] = un seul rôle.
    roles_extra: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Codes de secours 2FA (JSON de hachages bcrypt, usage unique)
    totp_backup_codes: Mapped[str | None] = mapped_column(Text, nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def roles(self) -> tuple[str, ...]:
        """Tous les rôles détenus : le principal d'abord, puis les cumulés."""
        extra = [r for r in (self.roles_extra or []) if r in ROLES_CONNUS]
        return tuple(dict.fromkeys([self.role, *extra]))

    def a_role(self, *candidats) -> bool:
        """True si l'utilisateur détient AU MOINS UN des rôles demandés.

        Point de passage unique des autorisations : tester `role` directement
        ignorerait silencieusement le cumul.
        """
        attendus: set[str] = set()
        for c in candidats:
            if isinstance(c, str):
                attendus.add(c)
            else:
                attendus.update(c)
        return not attendus.isdisjoint(self.roles)

    @property
    def is_supervisor(self) -> bool:
        return self.a_role(*ROLES_SUPERVISEURS)

    @property
    def requires_2fa(self) -> bool:
        """2FA obligatoire pour les rôles de supervision (Art. 29).

        La politique est portée par le cabinet, pas par la plateforme : un
        cabinet peut l'exiger là où un autre ne l'a pas encore déployée. Le
        réglage global ne sert plus que de repli hors contexte cabinet.
        """
        from app.core.config import settings
        from app.core.tenant_context import get_current_tenant_or_none

        tenant = get_current_tenant_or_none()
        required = tenant.totp_required if tenant is not None else settings.TOTP_REQUIRED
        if not required:
            return False
        return self.a_role(*ROLES_SUPERVISEURS)
