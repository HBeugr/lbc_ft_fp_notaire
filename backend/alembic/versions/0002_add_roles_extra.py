"""cumul de rôles : colonne users.roles_extra

Une même personne (donc un même email, qui reste la clé de connexion) peut porter
plusieurs casquettes sans dupliquer de compte — cas courant en petite étude où le
notaire principal tient aussi la conformité. `role` continue de porter le rôle
PRINCIPAL (affichage, journal d'audit, en-tête des rapports), `roles_extra` les
rôles cumulés.

Colonne plutôt que table d'association : le nombre de rôles est fermé (6) et
toujours chargé avec l'utilisateur ; une jointure par contrôle d'accès
n'apporterait rien.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-24

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL = aucun rôle cumulé. Pas de rétro-remplissage avec [role] : le rôle
    # principal vit déjà dans `role`, le dupliquer ferait diverger les deux
    # colonnes dès le premier changement de rôle.
    op.add_column("users", sa.Column("roles_extra", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "roles_extra")
