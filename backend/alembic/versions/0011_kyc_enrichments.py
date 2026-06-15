"""Enrichissements KYC — nature de relation, RCCM 90j, objet social, registre BE,
filtrage SFC structuré, validation BE/PPE, presse négative & exposition PPE.

Conserve le modèle KYC notarial (Chambre des Notaires, Mai 2025) et ajoute les
champs réglementaires manquants identifiés au regard du CDC.

Révision : 0011
Révision précédente : 0010
"""
from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

_ALERTE_NEW = (
    "ENUM('T1_PPE','T2_ESPECES','T3_SANCTIONS','T4_GAFI','T5_REFUS_DOC',"
    "'T6_BE_NON_IDENTIFIABLE','INCOHERENCE_DOC','MONTAGE_COMPLEXE',"
    "'SIGNALEMENT_INTERNE','DOSSIER_BLOQUE','DOS_ACCUSE_J15','PROLIFERATION_MATCH','RCCM_EXPIRE','AUTRE')"
)
_ALERTE_OLD = (
    "ENUM('T1_PPE','T2_ESPECES','T3_SANCTIONS','T4_GAFI','T5_REFUS_DOC',"
    "'T6_BE_NON_IDENTIFIABLE','INCOHERENCE_DOC','MONTAGE_COMPLEXE',"
    "'SIGNALEMENT_INTERNE','DOSSIER_BLOQUE','DOS_ACCUSE_J15','PROLIFERATION_MATCH','AUTRE')"
)


def upgrade() -> None:
    op.execute(f"ALTER TABLE alertes MODIFY COLUMN type_alerte {_ALERTE_NEW} NOT NULL")

    # Dossier — nature de la relation d'affaires (M4)
    op.add_column("dossiers", sa.Column(
        "nature_relation",
        sa.Enum("ponctuelle", "durable", name="nature_relation_enum"),
        nullable=True,
    ))

    # KYC-PP — objet de la relation
    op.add_column("kyc_pp", sa.Column("objet_relation", sa.Text, nullable=True))

    # KYC-PM — RCCM 90j, objet social, représentant PPE
    op.add_column("kyc_pm", sa.Column("date_emission_rccm", sa.Date, nullable=True))
    op.add_column("kyc_pm", sa.Column("date_expiration_rccm", sa.Date, nullable=True))
    op.add_column("kyc_pm", sa.Column("objet_social", sa.Text, nullable=True))
    op.add_column("kyc_pm", sa.Column(
        "representant_statut_ppe", sa.Boolean, nullable=False, server_default="0"
    ))

    # KYC-BE — droits de vote, entité intermédiaire, registre BE, filtrage SFC, validation
    op.add_column("kyc_be", sa.Column("pourcentage_droits_vote", sa.Numeric(5, 2), nullable=True))
    op.add_column("kyc_be", sa.Column("entite_intermediaire_nom", sa.String(255), nullable=True))
    op.add_column("kyc_be", sa.Column("entite_intermediaire_pct", sa.Numeric(5, 2), nullable=True))
    op.add_column("kyc_be", sa.Column(
        "registre_be_demande",
        sa.Enum("oui", "non", "en_cours", name="registre_be_demande_enum"), nullable=True,
    ))
    op.add_column("kyc_be", sa.Column(
        "registre_be_resultat",
        sa.Enum("conforme", "divergence", "non_trouve", name="registre_be_resultat_enum"), nullable=True,
    ))
    op.add_column("kyc_be", sa.Column("registre_be_note", sa.Text, nullable=True))
    op.add_column("kyc_be", sa.Column(
        "filtrage_sfc_resultat",
        sa.Enum("aucune", "faux_positif", "correspondance", name="filtrage_sfc_resultat_enum"), nullable=True,
    ))
    op.add_column("kyc_be", sa.Column("filtrage_sfc_listes", sa.JSON, nullable=True))
    op.add_column("kyc_be", sa.Column("filtrage_sfc_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("kyc_be", sa.Column("filtrage_sfc_justification", sa.Text, nullable=True))
    op.add_column("kyc_be", sa.Column(
        "statut_validation",
        sa.Enum("en_attente", "valide", "rejete", name="statut_validation_be_enum"),
        nullable=False, server_default="en_attente",
    ))
    op.add_column("kyc_be", sa.Column("commentaire_validation", sa.Text, nullable=True))

    # KYC-PPE — presse négative, exposition, validation
    op.add_column("kyc_ppe", sa.Column(
        "resultat_presse",
        sa.Enum("Negatif", "Positif", "Ambigu", name="resultat_presse_enum"), nullable=True,
    ))
    op.add_column("kyc_ppe", sa.Column("details_presse", sa.Text, nullable=True))
    op.add_column("kyc_ppe", sa.Column(
        "niveau_exposition",
        sa.Enum("Faible", "Moyen", "Eleve", name="niveau_exposition_ppe_enum"), nullable=True,
    ))
    op.add_column("kyc_ppe", sa.Column("mesures_proposees", sa.Text, nullable=True))
    op.add_column("kyc_ppe", sa.Column(
        "statut_validation",
        sa.Enum("en_attente", "valide", "rejete", name="statut_validation_ppe_enum"),
        nullable=False, server_default="en_attente",
    ))
    op.add_column("kyc_ppe", sa.Column("commentaire_validation", sa.Text, nullable=True))


def downgrade() -> None:
    for col in ("commentaire_validation", "statut_validation", "mesures_proposees",
                "niveau_exposition", "details_presse", "resultat_presse"):
        op.drop_column("kyc_ppe", col)
    for col in ("commentaire_validation", "statut_validation", "filtrage_sfc_justification",
                "filtrage_sfc_date", "filtrage_sfc_listes", "filtrage_sfc_resultat",
                "registre_be_note", "registre_be_resultat", "registre_be_demande",
                "entite_intermediaire_pct", "entite_intermediaire_nom", "pourcentage_droits_vote"):
        op.drop_column("kyc_be", col)
    for col in ("representant_statut_ppe", "objet_social", "date_expiration_rccm", "date_emission_rccm"):
        op.drop_column("kyc_pm", col)
    op.drop_column("kyc_pp", "objet_relation")
    op.drop_column("dossiers", "nature_relation")
    op.execute(f"ALTER TABLE alertes MODIFY COLUMN type_alerte {_ALERTE_OLD} NOT NULL")
