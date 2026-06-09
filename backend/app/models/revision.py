import uuid
from sqlalchemy import String, Enum as SAEnum, ForeignKey, DateTime, Date, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RevisionKyc(Base):
    """Révision périodique KYC (Art. 19, Ordonnance 2023-875)."""
    __tablename__ = "revisions_kyc"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id: Mapped[str] = mapped_column(String(36), ForeignKey("dossiers.id"), nullable=False)
    classification_avant: Mapped[str | None] = mapped_column(String(10), nullable=True)
    classification_apres: Mapped[str | None] = mapped_column(String(10), nullable=True)
    score_avant: Mapped[int | None] = mapped_column(nullable=True)
    score_apres: Mapped[int | None] = mapped_column(nullable=True)
    statut: Mapped[str] = mapped_column(
        SAEnum(
            "planifiee", "en_cours", "completee", "en_retard",
            "vigilance_renforcee", "bloquee",
            name="statut_revision_enum",
        ),
        nullable=False,
        default="planifiee",
    )
    date_echeance: Mapped[Date] = mapped_column(Date, nullable=False)
    date_relance_1: Mapped[Date | None] = mapped_column(Date, nullable=True)
    date_relance_2: Mapped[Date | None] = mapped_column(Date, nullable=True)
    date_validation: Mapped[Date | None] = mapped_column(Date, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    valide_par: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    documents_mis_a_jour: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
