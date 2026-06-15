"""Signalement interne d'alerte : colonne signaleur_id, dossier_id nullable,
valeur d'enum SIGNALEMENT_INTERNE.

Permet aux clercs de signaler une suspicion (avec ou sans dossier rattaché)
au Responsable Conformité (mirroir du projet assujetti).

Révision : 0005
Révision précédente : 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_TYPE_ENUM_NEW = (
    "T1_PPE", "T2_ESPECES", "T3_SANCTIONS", "T4_GAFI",
    "T5_REFUS_DOC", "T6_BE_NON_IDENTIFIABLE",
    "INCOHERENCE_DOC", "MONTAGE_COMPLEXE", "SIGNALEMENT_INTERNE", "AUTRE",
)
_TYPE_ENUM_OLD = (
    "T1_PPE", "T2_ESPECES", "T3_SANCTIONS", "T4_GAFI",
    "T5_REFUS_DOC", "T6_BE_NON_IDENTIFIABLE",
    "INCOHERENCE_DOC", "MONTAGE_COMPLEXE", "AUTRE",
)


def upgrade() -> None:
    # Étend l'enum type_alerte avec SIGNALEMENT_INTERNE
    op.alter_column(
        "alertes", "type_alerte",
        type_=sa.Enum(*_TYPE_ENUM_NEW, name="type_alerte_enum"),
        existing_nullable=False,
    )
    # dossier_id devient optionnel (signalement sans dossier rattaché)
    op.alter_column(
        "alertes", "dossier_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    # Auteur du signalement (clerc)
    op.add_column(
        "alertes",
        sa.Column("signaleur_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("alertes", "signaleur_id")
    op.alter_column(
        "alertes", "dossier_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    op.alter_column(
        "alertes", "type_alerte",
        type_=sa.Enum(*_TYPE_ENUM_OLD, name="type_alerte_enum"),
        existing_nullable=False,
    )
