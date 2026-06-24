"""Table autorisations_dirigeant — registre WRK-09 (décisions Notaire Principal sur dossiers T1/PPE).

Révision : 0019
Révision précédente : 0018
"""
from alembic import op
import sqlalchemy as sa


revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "autorisations_dirigeant",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("dirigeant_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.Enum("AUTORISE", "REFUSE", name="decision_wrk09_enum"), nullable=False),
        sa.Column("justification", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_autorisations_dirigeant_dossier_id", "autorisations_dirigeant", ["dossier_id"])


def downgrade() -> None:
    op.drop_index("ix_autorisations_dirigeant_dossier_id", table_name="autorisations_dirigeant")
    op.drop_table("autorisations_dirigeant")
