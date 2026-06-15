import uuid
from sqlalchemy import String, Boolean, Enum as SAEnum, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Alerte(Base):
    __tablename__ = "alertes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("dossiers.id"), nullable=True)
    type_alerte: Mapped[str] = mapped_column(
        SAEnum(
            "T1_PPE", "T2_ESPECES", "T3_SANCTIONS", "T4_GAFI",
            "T5_REFUS_DOC", "T6_BE_NON_IDENTIFIABLE",
            "INCOHERENCE_DOC", "MONTAGE_COMPLEXE", "SIGNALEMENT_INTERNE",
            "DOSSIER_BLOQUE", "DOS_ACCUSE_J15", "PROLIFERATION_MATCH", "RCCM_EXPIRE", "AUTRE",
            name="type_alerte_enum",
        ),
        nullable=False,
    )
    signaleur_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    niveau: Mapped[str] = mapped_column(
        SAEnum("FAIBLE", "MOYEN", "ELEVE", name="niveau_alerte_enum"), nullable=False
    )
    statut: Mapped[str] = mapped_column(
        SAEnum("ouverte", "en_cours", "traitee", "ignoree", name="statut_alerte_enum"),
        nullable=False,
        default="ouverte",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    traite_par: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    traite_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
