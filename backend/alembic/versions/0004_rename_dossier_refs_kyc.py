"""Renomme les références des dossiers KYC : DOS-XXXX -> KYC-XXXX.

Les références de dossiers KYC étaient générées avec le préfixe « DOS- »,
prêtant à confusion avec les Déclarations d'Opération Suspecte (DOS).
Les dossiers KYC utilisent désormais le préfixe « KYC- ».

Révision : 0004
Révision précédente : 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE dossiers "
        "SET reference = CONCAT('KYC-', SUBSTRING(reference, 5)) "
        "WHERE reference LIKE 'DOS-%'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE dossiers "
        "SET reference = CONCAT('DOS-', SUBSTRING(reference, 5)) "
        "WHERE reference LIKE 'KYC-%'"
    )
