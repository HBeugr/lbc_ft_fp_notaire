"""Ajout du type d'alerte SANCTIONS_PERIMEES (fraîcheur des listes > 95 jours).

Révision : 0021
Révision précédente : 0020
"""
from alembic import op


revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

_VALUES = (
    "T1_PPE","T2_ESPECES","T3_SANCTIONS","T4_GAFI","T5_REFUS_DOC","T6_BE_NON_IDENTIFIABLE",
    "INCOHERENCE_DOC","MONTAGE_COMPLEXE","SIGNALEMENT_INTERNE","DOSSIER_BLOQUE",
    "DOS_ACCUSE_J15","PROLIFERATION_MATCH","RCCM_EXPIRE","SANCTIONS_PERIMEES","AUTRE",
)
_OLD = tuple(v for v in _VALUES if v != "SANCTIONS_PERIMEES")


def _enum(values) -> str:
    return "ENUM(" + ",".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    op.execute(f"ALTER TABLE alertes MODIFY COLUMN type_alerte {_enum(_VALUES)} NOT NULL")


def downgrade() -> None:
    op.execute(f"ALTER TABLE alertes MODIFY COLUMN type_alerte {_enum(_OLD)} NOT NULL")
