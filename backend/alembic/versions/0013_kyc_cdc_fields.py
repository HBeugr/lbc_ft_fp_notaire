"""Champs KYC manquants du CDC (Module 1).

PP : sexe, ville de résidence, retraité, note, pièce (pays émetteur, dates
émission/expiration, mode de vérification), tranche de revenus réglementaire.
PM : nom commercial, pays de constitution, CA annuel, effectif, pays
d'opérations, volume des transactions.
BE : lien avec le client, entreprise cotée. Actionnaire : type PP/PM.

Révision : 0013
Révision précédente : 0012
"""
from alembic import op
import sqlalchemy as sa


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # KYC-PP
    op.add_column("kyc_pp", sa.Column("pays_emetteur_piece", sa.String(100), nullable=True))
    op.add_column("kyc_pp", sa.Column("date_emission_piece", sa.Date, nullable=True))
    op.add_column("kyc_pp", sa.Column("date_expiration_piece", sa.Date, nullable=True))
    op.add_column("kyc_pp", sa.Column(
        "mode_verification_piece",
        sa.Enum("original_vu", "copie_certifiee", "en_ligne", name="mode_verification_piece_enum"),
        nullable=True,
    ))
    op.add_column("kyc_pp", sa.Column("sexe", sa.Enum("M", "F", name="sexe_enum"), nullable=True))
    op.add_column("kyc_pp", sa.Column("ville_residence", sa.String(150), nullable=True))
    op.add_column("kyc_pp", sa.Column("retraite", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("kyc_pp", sa.Column(
        "tranche_revenus",
        sa.Enum("moins_500k", "500k_2m", "2m_10m", "plus_10m", name="tranche_revenus_enum"),
        nullable=True,
    ))
    op.add_column("kyc_pp", sa.Column("note", sa.Text, nullable=True))

    # KYC-PM
    op.add_column("kyc_pm", sa.Column("nom_commercial", sa.String(255), nullable=True))
    op.add_column("kyc_pm", sa.Column("pays_constitution", sa.String(100), nullable=True))
    op.add_column("kyc_pm", sa.Column("ca_annuel", sa.Numeric(18, 2), nullable=True))
    op.add_column("kyc_pm", sa.Column("effectif", sa.Integer, nullable=True))
    op.add_column("kyc_pm", sa.Column("pays_operations", sa.String(255), nullable=True))
    op.add_column("kyc_pm", sa.Column("volume_transactions", sa.String(255), nullable=True))

    # KYC-BE
    op.add_column("kyc_be", sa.Column("lien_avec_client", sa.String(255), nullable=True))
    op.add_column("kyc_be", sa.Column("entreprise_cotee", sa.Boolean, nullable=False, server_default="0"))

    # Actionnaires
    op.add_column("kyc_actionnaires", sa.Column(
        "type_personne", sa.Enum("PP", "PM", name="type_personne_actionnaire_enum"), nullable=True
    ))


def downgrade() -> None:
    op.drop_column("kyc_actionnaires", "type_personne")
    op.drop_column("kyc_be", "entreprise_cotee")
    op.drop_column("kyc_be", "lien_avec_client")
    for col in ("volume_transactions", "pays_operations", "effectif", "ca_annuel",
                "pays_constitution", "nom_commercial"):
        op.drop_column("kyc_pm", col)
    for col in ("note", "tranche_revenus", "retraite", "ville_residence", "sexe",
                "mode_verification_piece", "date_expiration_piece", "date_emission_piece",
                "pays_emetteur_piece"):
        op.drop_column("kyc_pp", col)
