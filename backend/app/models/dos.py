import uuid
from sqlalchemy import String, Boolean, Enum as SAEnum, ForeignKey, DateTime, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeclarationSuspicion(Base):
    """DOS — Déclaration d'Opération Suspecte (Art. 60-68, Ordonnance 2023-875).
    Accès restreint : responsable_conformite + notaire_principal + admin.
    Confidentialité absolue — Art. 63.
    """
    __tablename__ = "declarations_suspicion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id: Mapped[str] = mapped_column(String(36), ForeignKey("dossiers.id"), nullable=False)
    reference_interne: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    statut: Mapped[str] = mapped_column(
        SAEnum("brouillon", "en_cours", "soumis", "accuse_recu", name="statut_dos_enum"),
        nullable=False,
        default="brouillon",
    )

    # Section 1 — Organisme déclarant (pré-rempli)
    organisme_libelle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organisme_adresse: Mapped[str | None] = mapped_column(Text, nullable=True)
    organisme_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organisme_telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Section 3 — Analyse
    type_soupcon_bc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    type_soupcon_ft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    type_soupcon_prolif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # JSON : liste des 14 motifs officiels CENTIF cochés
    motifs: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Section 4 — Statut des opérations (JSON)
    statut_operations: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Section 5 — Détail transactions (JSON)
    detail_transactions: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Section 6 — Indices de blanchiment
    indices_blanchiment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Section 7 — Identification (JSON — fiche PP ou PM pré-remplie)
    identification: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Section 8 — Relations d'affaires (JSON)
    relations_affaires: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Section 9 — Supports utilisés (JSON)
    supports: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Section 10 — Autres informations
    autres_informations: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Suivi
    initie_par: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    valide_par: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    soumis_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accuse_recu_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accuse_recu_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    addendums: Mapped[list["DosAddendum"]] = relationship("DosAddendum", back_populates="dos")


class DosAddendum(Base):
    """Complément de DOS — append-only."""
    __tablename__ = "dos_addendums"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dos_id: Mapped[str] = mapped_column(String(36), ForeignKey("declarations_suspicion.id"), nullable=False)
    contenu: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dos: Mapped["DeclarationSuspicion"] = relationship("DeclarationSuspicion", back_populates="addendums")
