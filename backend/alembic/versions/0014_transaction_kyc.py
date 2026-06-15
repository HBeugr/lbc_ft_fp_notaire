"""Étape Transaction du KYC — tranche de montant + indicateur déclaration espèces,
et ajout du mode de paiement "autre".

Révision : 0014
Révision précédente : 0013
"""
from alembic import op
import sqlalchemy as sa


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

_MODE_NEW = "ENUM('virement','cheque','especes','mix','paiement_tiers','autre')"
_MODE_OLD = "ENUM('virement','cheque','especes','mix','paiement_tiers')"


def upgrade() -> None:
    op.add_column("dossiers", sa.Column(
        "montant_tranche",
        sa.Enum("moins_15m", "plus_15m", name="montant_tranche_enum"),
        nullable=True,
    ))
    op.add_column("dossiers", sa.Column(
        "surveillance_espece", sa.Boolean, nullable=False, server_default="0"
    ))
    op.execute(f"ALTER TABLE dossiers MODIFY COLUMN mode_paiement {_MODE_NEW}")


def downgrade() -> None:
    op.execute(f"ALTER TABLE dossiers MODIFY COLUMN mode_paiement {_MODE_OLD}")
    op.drop_column("dossiers", "surveillance_espece")
    op.drop_column("dossiers", "montant_tranche")
