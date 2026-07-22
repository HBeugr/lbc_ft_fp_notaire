"""Référentiel institutionnel « Mes Procédures ».

Ces tables étaient jusqu'ici définies uniquement en migration et manipulées en
SQL brut depuis `routers/procedures.py`. Elles sont désormais déclarées dans
l'ORM afin que `Base.metadata` soit complet : c'est ce qui permet de générer le
schéma d'un nouveau cabinet et de tenir les migrations multi-schémas. Le SQL
brut existant continue de fonctionner tel quel — il est résolu par le
`search_path` comme le reste.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Procedure(Base):
    __tablename__ = "procedures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcedureDocument(Base):
    __tablename__ = "procedure_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    procedure_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("procedures.id"), nullable=False, index=True
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..7
    nom_fichier: Mapped[str] = mapped_column(String(500), nullable=False)
    minio_key: Mapped[str] = mapped_column(Text, nullable=False)
    taille_octets: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
