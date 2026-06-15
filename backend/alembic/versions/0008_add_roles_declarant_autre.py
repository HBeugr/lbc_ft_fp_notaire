"""Ajout des rôles declarant_centif et autre_utilisateur (parité assujetti).

Le Déclarant CENTIF est distinct du Responsable Conformité (Art. 100) et
prépare/transmet les DOS. « Autre utilisateur » couvre les accès en lecture
restreinte. Les rôles existants (admin, notaire_principal,
responsable_conformite, clercs) sont conservés.

Révision : 0008
Révision précédente : 0007
"""
from alembic import op


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_ENUM_NEW = (
    "ENUM('admin','notaire_principal','responsable_conformite','clercs',"
    "'declarant_centif','autre_utilisateur')"
)
_ENUM_OLD = (
    "ENUM('admin','notaire_principal','responsable_conformite','clercs')"
)


def upgrade() -> None:
    op.execute(f"ALTER TABLE users MODIFY COLUMN role {_ENUM_NEW} NOT NULL")


def downgrade() -> None:
    op.execute(f"ALTER TABLE users MODIFY COLUMN role {_ENUM_OLD} NOT NULL")
