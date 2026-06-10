"""Scoring matrice de risque — champs opération + table evaluations_risque

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-10

Ajoute :
  - dossiers.montant_transaction / mode_paiement / nb_parties
    (alimentent axes 4 & 5 et trigger T2 espèces > 15M — CDC Module 2)
  - table evaluations_risque : résultat horodaté de la matrice (10 axes + 6 triggers
    + overrides justifiés). dossiers.score_base/classification restent un cache
    dénormalisé pour l'affichage liste.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Champs opération sur le dossier ─────────────────────────────────────────
    op.add_column("dossiers", sa.Column("montant_transaction", sa.Numeric(18, 2), nullable=True))
    op.add_column(
        "dossiers",
        sa.Column(
            "mode_paiement",
            sa.Enum("virement", "cheque", "especes", "mix", "paiement_tiers", name="mode_paiement_enum"),
            nullable=True,
        ),
    )
    op.add_column("dossiers", sa.Column("nb_parties", sa.Integer, nullable=False, server_default="1"))

    # ── Table evaluations_risque ────────────────────────────────────────────────
    op.create_table(
        "evaluations_risque",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False, unique=True),
        # 10 axes — chacun {0, 1, 2}
        sa.Column("axe_type_client", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("axe_pays_geographie", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("axe_type_operation", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("axe_montant", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("axe_mode_paiement", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("axe_complexite", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("axe_ppe", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("axe_coherence_doc", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("axe_secteur", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("axe_intermediaires", sa.SmallInteger, nullable=False, server_default="0"),
        # Résultat
        sa.Column("score_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "classification",
            sa.Enum("FAIBLE", "MOYEN", "ELEVE", name="classification_enum"),
            nullable=False,
            server_default="FAIBLE",
        ),
        sa.Column("trigger_principal", sa.String(10), nullable=True),
        sa.Column("triggers_actifs", mysql.JSON, nullable=True),
        sa.Column("force_par_trigger", sa.Boolean, nullable=False, server_default="0"),
        # Flags triggers explicites (saisis par l'agent)
        sa.Column("sur_liste_sanctions", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("pays_liste_noire_gafi", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("pays_liste_grise_gafi", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("refus_documents", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("be_non_identifiable", sa.Boolean, nullable=False, server_default="0"),
        # Audit overrides : [{axe, valeur_auto, valeur_override, justification, user_id, ts}]
        sa.Column("overrides", mysql.JSON, nullable=True),
        sa.Column("evaluated_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    # MySQL : les enums sont inline, supprimés avec leur colonne (pas de DROP TYPE).
    op.drop_table("evaluations_risque")
    op.drop_column("dossiers", "nb_parties")
    op.drop_column("dossiers", "mode_paiement")
    op.drop_column("dossiers", "montant_transaction")
