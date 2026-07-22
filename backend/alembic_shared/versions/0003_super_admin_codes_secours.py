"""Codes de secours 2FA du Super-Admin

Les colonnes `totp_secret` / `totp_enabled` existaient depuis 0001 mais aucun
code ne les exploitait. L'activation de la 2FA sur le compte d'exploitation
impose d'ajouter les codes de secours : le Super-Admin est le seul compte de la
plateforme sans recours externe — personne ne peut le déverrouiller à sa place.
Sans codes de secours, un téléphone perdu rendrait la console définitivement
inaccessible.

Stockés hachés et en JSON, comme pour les utilisateurs de cabinet
(`users.totp_backup_codes`).

Révision : 0003
Révision précédente : 0002
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'super_admins',
        sa.Column('totp_backup_codes', sa.Text(), nullable=True),
        schema='shared',
    )


def downgrade() -> None:
    op.drop_column('super_admins', 'totp_backup_codes', schema='shared')
