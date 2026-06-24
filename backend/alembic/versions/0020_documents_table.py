"""Table documents — métadonnées + intégrité SHA-256 (remplace le stockage fragile via audit-log).

Révision : 0020
Révision précédente : 0019
"""
from alembic import op
import sqlalchemy as sa


revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("type_document", sa.String(80), nullable=False, server_default="autre"),
        sa.Column("nom_fichier", sa.String(500), nullable=False),
        sa.Column("minio_key", sa.Text, nullable=False),
        sa.Column("content_type", sa.String(120), nullable=True),
        sa.Column("taille_octets", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_dossier_id", "documents", ["dossier_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_dossier_id", table_name="documents")
    op.drop_table("documents")
