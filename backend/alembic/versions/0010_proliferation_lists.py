"""Criblage Financement de la Prolifération (M1.2).

- Étend l'enum des types de listes sanctions avec les listes de prolifération
  (ONU_PROLIFERATION, OFAC_WMD, UE_PROLIFERATION, CENTIF_FP).
- Ajoute le type d'alerte PROLIFERATION_MATCH pour distinguer une correspondance
  sur une liste de prolifération d'une correspondance sanctions classique (T3).

Révision : 0010
Révision précédente : 0009
"""
from alembic import op


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_TYPE_LISTE_NEW = (
    "ENUM('GIABA','BCEAO','OFAC','UE_CSDNU','AUTRE',"
    "'ONU_PROLIFERATION','OFAC_WMD','UE_PROLIFERATION','CENTIF_FP')"
)
_TYPE_LISTE_OLD = "ENUM('GIABA','BCEAO','OFAC','UE_CSDNU','AUTRE')"

_ALERTE_NEW = (
    "ENUM('T1_PPE','T2_ESPECES','T3_SANCTIONS','T4_GAFI','T5_REFUS_DOC',"
    "'T6_BE_NON_IDENTIFIABLE','INCOHERENCE_DOC','MONTAGE_COMPLEXE',"
    "'SIGNALEMENT_INTERNE','DOSSIER_BLOQUE','DOS_ACCUSE_J15','PROLIFERATION_MATCH','AUTRE')"
)
_ALERTE_OLD = (
    "ENUM('T1_PPE','T2_ESPECES','T3_SANCTIONS','T4_GAFI','T5_REFUS_DOC',"
    "'T6_BE_NON_IDENTIFIABLE','INCOHERENCE_DOC','MONTAGE_COMPLEXE',"
    "'SIGNALEMENT_INTERNE','DOSSIER_BLOQUE','DOS_ACCUSE_J15','AUTRE')"
)


def upgrade() -> None:
    op.execute(f"ALTER TABLE listes_sanctions MODIFY COLUMN type_liste {_TYPE_LISTE_NEW} NOT NULL")
    op.execute(f"ALTER TABLE alertes MODIFY COLUMN type_alerte {_ALERTE_NEW} NOT NULL")


def downgrade() -> None:
    op.execute(f"ALTER TABLE alertes MODIFY COLUMN type_alerte {_ALERTE_OLD} NOT NULL")
    op.execute(f"ALTER TABLE listes_sanctions MODIFY COLUMN type_liste {_TYPE_LISTE_OLD} NOT NULL")
