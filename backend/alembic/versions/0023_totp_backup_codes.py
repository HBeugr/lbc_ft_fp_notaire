"""Ajout de la colonne totp_backup_codes (codes de secours 2FA, usage unique).

Révision : 0023
Révision précédente : 0022
"""
import sqlalchemy as sa
from alembic import op


revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_backup_codes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "totp_backup_codes")
