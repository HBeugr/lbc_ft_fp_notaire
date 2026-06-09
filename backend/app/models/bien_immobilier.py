import uuid
from sqlalchemy import String, Enum as SAEnum, ForeignKey, DateTime, Text, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BienImmobilier(Base):
    """Bien immobilier lié à un dossier — opérations notariales."""
    __tablename__ = "biens_immobiliers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id: Mapped[str] = mapped_column(String(36), ForeignKey("dossiers.id"), nullable=False)
    nature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    adresse: Mapped[str | None] = mapped_column(String(500), nullable=True)
    valeur: Mapped[float | None] = mapped_column(Numeric(15, 0), nullable=True)
    mode_financement: Mapped[str | None] = mapped_column(
        SAEnum(
            "virement_bancaire", "cheque", "especes", "mix", "paiement_tiers", "autre",
            name="mode_financement_enum",
        ),
        nullable=True,
    )
    titres_fonciers: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
