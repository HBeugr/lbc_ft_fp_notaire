"""Add procedures + procedure_documents tables

Référentiel institutionnel « Mes Procédures » : chaque procédure porte un nom
et jusqu'à 7 pièces jointes (slots 1 à 7). Stockage des fichiers dans MinIO
(bucket documents), intégrité SHA-256 conservée inline.

Révision : 0017
Révision précédente : 0016
"""
import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "procedures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "procedure_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("procedure_id", sa.String(36), sa.ForeignKey("procedures.id"), nullable=False),
        sa.Column("slot", sa.Integer, nullable=False),  # 1..7
        sa.Column("nom_fichier", sa.String(500), nullable=False),
        sa.Column("minio_key", sa.Text, nullable=False),
        sa.Column("taille_octets", sa.Integer, nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_procedure_documents_procedure_id",
        "procedure_documents",
        ["procedure_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_procedure_documents_procedure_id", table_name="procedure_documents")
    op.drop_table("procedure_documents")
    op.drop_table("procedures")
