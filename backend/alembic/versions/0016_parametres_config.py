"""Table parametres_config — seuils & pondérations configurables (Admin, FR-26).

Clé/valeur numérique persistée : seuil espèces Art. 72 (T2) et pondérations des
10 axes de scoring (clés ``poids_<code_axe>``). Chargée en cache au démarrage par
app.core.runtime_config.

Révision : 0016
Révision précédente : 0015
"""
from alembic import op
import sqlalchemy as sa


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parametres_config",
        sa.Column("cle", sa.String(64), primary_key=True),
        sa.Column("valeur", sa.Numeric(20, 2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("parametres_config")
