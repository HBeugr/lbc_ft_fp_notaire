"""Alertes : prise en charge (en_cours tracé) + niveaux CRITIQUE/INFO (parité immo).

Révision : 0024
Révision précédente : 0023
"""
import sqlalchemy as sa
from alembic import op


revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

_NEW = ("CRITIQUE", "ELEVE", "MOYEN", "FAIBLE", "INFO")
_OLD = ("FAIBLE", "MOYEN", "ELEVE")


def _enum(values) -> str:
    return "ENUM(" + ",".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    op.add_column("alertes", sa.Column("prise_en_charge_par", sa.String(36), nullable=True))
    op.add_column("alertes", sa.Column("prise_en_charge_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(f"ALTER TABLE alertes MODIFY COLUMN niveau {_enum(_NEW)} NOT NULL")


def downgrade() -> None:
    op.execute(f"ALTER TABLE alertes MODIFY COLUMN niveau {_enum(_OLD)} NOT NULL")
    op.drop_column("alertes", "prise_en_charge_at")
    op.drop_column("alertes", "prise_en_charge_par")
