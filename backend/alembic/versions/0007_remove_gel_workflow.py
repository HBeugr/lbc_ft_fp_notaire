"""Retrait du module Gel des avoirs (décision produit).

Le workflow Gel en 6 phases est supprimé : on retire les colonnes
`gel_phase` et `gel_notes` de la table dossiers. Le blocage du dossier
reste assuré par `is_bloque` (+ statut `bloque`), alimenté par les
sanctions (T3) et la création d'une DOS.

Révision : 0007
Révision précédente : 0006
"""
from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("dossiers", "gel_phase")
    op.drop_column("dossiers", "gel_notes")


def downgrade() -> None:
    op.add_column("dossiers", sa.Column("gel_notes", sa.Text, nullable=True))
    op.add_column("dossiers", sa.Column("gel_phase", sa.SmallInteger, nullable=True))
