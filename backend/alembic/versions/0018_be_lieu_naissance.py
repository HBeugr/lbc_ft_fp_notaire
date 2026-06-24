"""Ajout kyc_be.lieu_naissance — criblage sanctions des bénéficiaires effectifs
sur les 4 champs (nom, prénoms via raison_sociale_nom, date et lieu de naissance).

Révision : 0018
Révision précédente : 0017
"""
from alembic import op
import sqlalchemy as sa


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("kyc_be", sa.Column("lieu_naissance", sa.String(150), nullable=True))


def downgrade() -> None:
    op.drop_column("kyc_be", "lieu_naissance")
