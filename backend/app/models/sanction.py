import uuid
from sqlalchemy import String, Boolean, Integer, Enum as SAEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ListeSanctions(Base):
    """Liste de sanctions importée (GIABA, BCEAO, OFAC, UE/CSDNU…).

    Reproduit la logique de criblage du projet assujetti : les entrées sont
    normalisées à l'import (NFKD + majuscules) puis criblées par similarité floue
    (rapidfuzz token_sort_ratio, seuil 85) avec désambiguïsation DDN / lieu.
    """
    __tablename__ = "listes_sanctions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    type_liste: Mapped[str] = mapped_column(
        SAEnum("GIABA", "BCEAO", "OFAC", "UE_CSDNU", "AUTRE", name="type_liste_sanctions_enum"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    total_entrees: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    activated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntreeSanction(Base):
    """Entrée individuelle (personne/entité) d'une liste de sanctions.

    `nom` est stocké normalisé (majuscules, sans diacritiques). `date_naissance`
    conserve le format natif de la liste (DD/MM/YYYY ou année seule) pour la
    désambiguïsation au criblage.
    """
    __tablename__ = "entrees_sanctions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    liste_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("listes_sanctions.id", ondelete="CASCADE"), nullable=False
    )
    nom: Mapped[str] = mapped_column(String(500), nullable=False)
    date_naissance: Mapped[str | None] = mapped_column(String(40), nullable=True)
    nationalite: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lieu_naissance: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
