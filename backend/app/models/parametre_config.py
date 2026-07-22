"""Paramètres système configurables et PERSISTÉS (clé/valeur numérique).

Source de persistance des paramètres modifiables par l'Administrateur (FR-26) :
- seuil espèces Art. 72 (Trigger T2)
- pondérations des 10 axes de scoring (clés ``poids_<code_axe>``)

Les valeurs survivent aux redémarrages ; au démarrage, ``app.core.runtime_config``
charge ces lignes en cache mémoire (lecture synchrone rapide pour le scoring).
"""
from sqlalchemy import String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ParametreConfig(Base):
    __tablename__ = "parametres_config"

    cle: Mapped[str] = mapped_column(String(64), primary_key=True)
    valeur: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
