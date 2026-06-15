"""Remove dossiers.nature_relation (étape Nature de la relation d'affaires retirée du KYC)

La sélection Ponctuelle / Durable est supprimée du parcours KYC. La colonne
nature_relation (enum) est retirée de la table dossiers.

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-15
"""
import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("dossiers", "nature_relation")


def downgrade() -> None:
    op.add_column("dossiers", sa.Column(
        "nature_relation",
        sa.Enum("ponctuelle", "durable", name="nature_relation_enum"),
        nullable=True,
    ))
