import uuid
from sqlalchemy import String, Boolean, Enum as SAEnum, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


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
    def is_supervisor(self) -> bool:
        return self.role in ("admin", "notaire_principal", "responsable_conformite")

    @property
    def requires_2fa(self) -> bool:
        from app.core.config import settings
        if not settings.TOTP_REQUIRED:
            return False
        return self.role in ("notaire_principal", "responsable_conformite")
