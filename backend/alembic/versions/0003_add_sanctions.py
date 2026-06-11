"""Listes de sanctions & criblage — tables listes_sanctions + entrees_sanctions

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-11

Module Sanctions & Criblage (T3) : import de listes (CSV/PDF/HTML), criblage flou
des noms (rapidfuzz). Logique reproduite du projet assujetti.
"""
from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listes_sanctions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column(
            "type_liste",
            sa.Enum("GIABA", "BCEAO", "OFAC", "UE_CSDNU", "AUTRE", name="type_liste_sanctions_enum"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("total_entrees", sa.Integer, nullable=False, server_default="0"),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "entrees_sanctions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "liste_id", sa.String(36),
            sa.ForeignKey("listes_sanctions.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("nom", sa.String(500), nullable=False),
        sa.Column("date_naissance", sa.String(40), nullable=True),
        sa.Column("nationalite", sa.String(120), nullable=True),
        sa.Column("lieu_naissance", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_entrees_sanctions_liste_id", "entrees_sanctions", ["liste_id"])


def downgrade() -> None:
    op.drop_index("ix_entrees_sanctions_liste_id", table_name="entrees_sanctions")
    op.drop_table("entrees_sanctions")
    op.drop_table("listes_sanctions")
