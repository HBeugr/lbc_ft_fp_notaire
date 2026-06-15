"""Workflow DOS CENTIF — double validation RC+DG, transmission, J+15, blocage auto.

- Étend le cycle de statut DOS (en_validation, validee_rc, transmise, classee).
- Ajoute la nature de l'opération (statut_operation), date de détection,
  la décision motivée, la double validation RC/DG, la transmission CENTIF et
  le flag d'alerte J+15.
- Étend l'enum des alertes (DOSSIER_BLOQUE, DOS_ACCUSE_J15) pour le blocage
  automatique du dossier à la création de la DOS et la relance J+15.

Révision : 0009
Révision précédente : 0008
"""
from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_STATUT_NEW = (
    "ENUM('brouillon','en_cours','soumis','accuse_recu',"
    "'en_validation','validee_rc','transmise','classee')"
)
_STATUT_OLD = "ENUM('brouillon','en_cours','soumis','accuse_recu')"

_ALERTE_NEW = (
    "ENUM('T1_PPE','T2_ESPECES','T3_SANCTIONS','T4_GAFI','T5_REFUS_DOC',"
    "'T6_BE_NON_IDENTIFIABLE','INCOHERENCE_DOC','MONTAGE_COMPLEXE',"
    "'SIGNALEMENT_INTERNE','DOSSIER_BLOQUE','DOS_ACCUSE_J15','AUTRE')"
)
_ALERTE_OLD = (
    "ENUM('T1_PPE','T2_ESPECES','T3_SANCTIONS','T4_GAFI','T5_REFUS_DOC',"
    "'T6_BE_NON_IDENTIFIABLE','INCOHERENCE_DOC','MONTAGE_COMPLEXE',"
    "'SIGNALEMENT_INTERNE','AUTRE')"
)


def upgrade() -> None:
    op.execute(f"ALTER TABLE declarations_suspicion MODIFY COLUMN statut {_STATUT_NEW} NOT NULL DEFAULT 'brouillon'")
    op.execute("ALTER TABLE alertes MODIFY COLUMN type_alerte " + _ALERTE_NEW + " NOT NULL")

    op.add_column("declarations_suspicion", sa.Column(
        "statut_operation",
        sa.Enum("executee", "en_cours", "tentee", name="statut_operation_dos_enum"),
        nullable=True,
    ))
    op.add_column("declarations_suspicion", sa.Column("date_detection", sa.Date, nullable=True))
    op.add_column("declarations_suspicion", sa.Column(
        "decision",
        sa.Enum("transmettre", "classer", name="decision_dos_enum"),
        nullable=True,
    ))
    op.add_column("declarations_suspicion", sa.Column("motif_classement", sa.Text, nullable=True))
    op.add_column("declarations_suspicion", sa.Column("valide_par_rc", sa.String(36), nullable=True))
    op.add_column("declarations_suspicion", sa.Column("valide_rc_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("declarations_suspicion", sa.Column("valide_par_dg", sa.String(36), nullable=True))
    op.add_column("declarations_suspicion", sa.Column("valide_dg_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("declarations_suspicion", sa.Column("date_transmission_centif", sa.DateTime(timezone=True), nullable=True))
    op.add_column("declarations_suspicion", sa.Column("transmis_par", sa.String(36), nullable=True))
    op.add_column("declarations_suspicion", sa.Column(
        "accuse_alerte_j15_envoyee", sa.Boolean, nullable=False, server_default="0"
    ))


def downgrade() -> None:
    for col in (
        "accuse_alerte_j15_envoyee", "transmis_par", "date_transmission_centif",
        "valide_dg_at", "valide_par_dg", "valide_rc_at", "valide_par_rc",
        "motif_classement", "decision", "date_detection", "statut_operation",
    ):
        op.drop_column("declarations_suspicion", col)
    op.execute(f"ALTER TABLE alertes MODIFY COLUMN type_alerte {_ALERTE_OLD} NOT NULL")
    op.execute(f"ALTER TABLE declarations_suspicion MODIFY COLUMN statut {_STATUT_OLD} NOT NULL DEFAULT 'brouillon'")
