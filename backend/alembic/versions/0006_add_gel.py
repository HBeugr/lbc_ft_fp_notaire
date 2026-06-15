"""Gel des avoirs — colonnes is_bloque / gel_phase / gel_notes sur dossiers.

Workflow en 6 phases (ANO-05, Art. 74 Ordonnance 2023-875). L'historique des
phases et des résolutions (levée / maintien définitif) est tracé via la table
audit_logs (actions gel.phase_N, gel.leve, gel.maintien_definitif) — pas de table
dédiée, mirroir du projet assujetti.

Révision : 0006
Révision précédente : 0005
"""
from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dossiers", sa.Column("is_bloque", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("dossiers", sa.Column("gel_phase", sa.SmallInteger, nullable=True))
    op.add_column("dossiers", sa.Column("gel_notes", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("dossiers", "gel_notes")
    op.drop_column("dossiers", "gel_phase")
    op.drop_column("dossiers", "is_bloque")
