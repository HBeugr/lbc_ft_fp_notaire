"""Initial schema — Notaire LBC/FT/FP

Revision ID: 0001
Revises:
Create Date: 2026-06-09

Tables créées :
  - users
  - dossiers
  - kyc_pp (KYC Personne Physique notarial)
  - kyc_pm (KYC Personne Morale notarial)
  - kyc_be (Bénéficiaires effectifs)
  - kyc_actionnaires (Structure de propriété PM)
  - kyc_ppe (Déclarations PPE)
  - dossiers_historique
  - commentaires_internes
  - alertes
  - audit_logs (append-only, immuable)
  - declarations_suspicion (DOS — accès restreint)
  - dos_addendums
  - revisions_kyc
  - biens_immobiliers

Contraintes de sécurité :
  - Trigger MySQL anti-suppression dossiers archivés (Art. 23, Art. 197)
  - Grants dos_user sur tables DOS uniquement (isolation ADR-003)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── USERS ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "notaire_principal", "responsable_conformite", "clercs", name="user_role_enum"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("totp_secret", sa.Text, nullable=True),
        sa.Column("totp_enabled", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("must_change_password", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── DOSSIERS ─────────────────────────────────────────────────────────────
    op.create_table(
        "dossiers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reference", sa.String(50), nullable=False, unique=True),
        sa.Column(
            "type_client",
            sa.Enum("PP", "PM", "Association", "Indivision", name="type_client_enum"),
            nullable=False,
        ),
        sa.Column(
            "type_operation",
            sa.Enum(
                "vente_immobiliere", "manipulation_fonds", "constitution_societe",
                "fiducicommis", "succession", "donation", "autre",
                name="type_operation_enum",
            ),
            nullable=False,
        ),
        sa.Column("type_operation_detail", sa.String(255), nullable=True),
        sa.Column(
            "statut",
            sa.Enum(
                "brouillon", "en_analyse", "vigilance_renforcee",
                "valide", "bloque", "traite", "cloture", "archive",
                name="statut_dossier_enum",
            ),
            nullable=False,
            server_default="brouillon",
        ),
        sa.Column("assigned_to", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("score_base", sa.Integer, nullable=True),
        sa.Column(
            "classification",
            sa.Enum("FAIBLE", "MOYEN", "ELEVE", name="classification_enum"),
            nullable=True,
        ),
        sa.Column("trigger_actif", sa.String(10), nullable=True),
        sa.Column("force_par_trigger", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("vigilance_justification", sa.Text, nullable=True),
        sa.Column("archivage_date", sa.Date, nullable=True),
        sa.Column("archivage_expiration", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── KYC PP ───────────────────────────────────────────────────────────────
    op.create_table(
        "kyc_pp",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False, unique=True),
        sa.Column("relation_type", sa.Enum("initiale", "actualisation", name="relation_type_enum"), nullable=False, server_default="initiale"),
        sa.Column("nom", sa.String(150), nullable=False),
        sa.Column("prenoms", sa.String(150), nullable=False),
        sa.Column("nom_jeune_fille", sa.String(150), nullable=True),
        sa.Column("nom_prenoms_pere", sa.String(255), nullable=True),
        sa.Column("nom_prenoms_mere", sa.String(255), nullable=True),
        sa.Column("date_naissance", sa.Date, nullable=True),
        sa.Column("lieu_naissance", sa.String(150), nullable=True),
        sa.Column("adresse_geo", sa.String(500), nullable=True),
        sa.Column("adresse_postale", sa.String(255), nullable=True),
        sa.Column("telephone", sa.String(30), nullable=True),
        sa.Column("whatsapp", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("type_piece", sa.Enum("CNI", "Passeport", "Titre_sejour", "Carte_consulaire", "Autre", name="type_piece_pp_enum"), nullable=True),
        sa.Column("numero_piece", sa.String(100), nullable=True),
        sa.Column("numero_contribuable", sa.String(100), nullable=True),
        sa.Column("non_resident", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("pays_residence", sa.String(100), nullable=True),
        sa.Column("statut_matrimonial", sa.String(100), nullable=True),
        sa.Column("nationalite", sa.String(100), nullable=True),
        sa.Column("autres_nationalites", sa.String(255), nullable=True),
        sa.Column("profession", sa.String(255), nullable=True),
        sa.Column("profession_5_ans", sa.Text, nullable=True),
        sa.Column("employeur", sa.String(255), nullable=True),
        sa.Column("secteur_activite", sa.String(255), nullable=True),
        sa.Column("mandataire", mysql.JSON, nullable=True),
        sa.Column("est_ppe", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("ppe_detail", sa.Text, nullable=True),
        sa.Column("operations_cochees", mysql.JSON, nullable=True),
        sa.Column("description_operation", sa.Text, nullable=True),
        sa.Column("origine_fonds", mysql.JSON, nullable=True),
        sa.Column("anciennete_pro", sa.Enum("moins_1_an", "1_a_10_ans", "plus_10_ans", name="anciennete_pp_enum"), nullable=True),
        sa.Column("date_signature", sa.Date, nullable=True),
        sa.Column("photo_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── KYC PM ───────────────────────────────────────────────────────────────
    op.create_table(
        "kyc_pm",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False, unique=True),
        sa.Column("relation_type", sa.Enum("initiale", "actualisation", name="relation_type_pm_enum"), nullable=False, server_default="initiale"),
        sa.Column("denomination_sociale", sa.String(255), nullable=False),
        sa.Column("forme_juridique", sa.String(50), nullable=True),
        sa.Column("nom_representant_legal", sa.String(255), nullable=True),
        sa.Column("numero_rccm", sa.String(100), nullable=True),
        sa.Column("numero_contribuable", sa.String(100), nullable=True),
        sa.Column("libelle_activite", sa.String(500), nullable=True),
        sa.Column("adresse", sa.String(500), nullable=True),
        sa.Column("telephone", sa.String(30), nullable=True),
        sa.Column("whatsapp", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("mandataire", mysql.JSON, nullable=True),
        sa.Column("ppe_detectee", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("ppe_detail", sa.Text, nullable=True),
        sa.Column("operations_cochees", mysql.JSON, nullable=True),
        sa.Column("description_operation", sa.Text, nullable=True),
        sa.Column("origine_fonds", mysql.JSON, nullable=True),
        sa.Column("infos_pm", mysql.JSON, nullable=True),
        sa.Column("anciennete_pro", sa.Enum("moins_1_an", "1_a_10_ans", "plus_10_ans", name="anciennete_pm_enum"), nullable=True),
        sa.Column("date_signature", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── KYC BE ───────────────────────────────────────────────────────────────
    op.create_table(
        "kyc_be",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kyc_pp_id", sa.String(36), sa.ForeignKey("kyc_pp.id"), nullable=True),
        sa.Column("kyc_pm_id", sa.String(36), sa.ForeignKey("kyc_pm.id"), nullable=True),
        sa.Column("raison_sociale_nom", sa.String(255), nullable=False),
        sa.Column("cni_passeport", sa.String(100), nullable=True),
        sa.Column("pourcentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("pays_residence", sa.String(100), nullable=True),
        sa.Column("date_naissance", sa.Date, nullable=True),
        sa.Column("nationalite", sa.String(100), nullable=True),
    )

    # ── KYC ACTIONNAIRES ─────────────────────────────────────────────────────
    op.create_table(
        "kyc_actionnaires",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kyc_pm_id", sa.String(36), sa.ForeignKey("kyc_pm.id"), nullable=False),
        sa.Column("raison_sociale_nom", sa.String(255), nullable=False),
        sa.Column("cni_passeport", sa.String(100), nullable=True),
        sa.Column("pourcentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("pays_residence", sa.String(100), nullable=True),
        sa.Column("ordre", sa.Integer, nullable=False, server_default="1"),
    )

    # ── KYC PPE ──────────────────────────────────────────────────────────────
    op.create_table(
        "kyc_ppe",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kyc_pp_id", sa.String(36), sa.ForeignKey("kyc_pp.id"), nullable=True),
        sa.Column("kyc_pm_id", sa.String(36), sa.ForeignKey("kyc_pm.id"), nullable=True),
        sa.Column("statut_ppe", sa.Enum("Non_PPE", "PPE_National", "PPE_Etranger", "Entourage_PPE", name="statut_ppe_enum"), nullable=False, server_default="Non_PPE"),
        sa.Column("fonctions", sa.Text, nullable=True),
        sa.Column("pays_concerne", sa.String(100), nullable=True),
        sa.Column("verification_giaba", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("verification_ofac", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("verification_ue", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("ras", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── DOSSIERS HISTORIQUE ───────────────────────────────────────────────────
    op.create_table(
        "dossiers_historique",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("statut_avant", sa.String(50), nullable=True),
        sa.Column("statut_apres", sa.String(50), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("commentaire", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── COMMENTAIRES INTERNES ─────────────────────────────────────────────────
    op.create_table(
        "commentaires_internes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("contenu", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── ALERTES ──────────────────────────────────────────────────────────────
    op.create_table(
        "alertes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("type_alerte", sa.Enum(
            "T1_PPE", "T2_ESPECES", "T3_SANCTIONS", "T4_GAFI",
            "T5_REFUS_DOC", "T6_BE_NON_IDENTIFIABLE", "INCOHERENCE_DOC", "MONTAGE_COMPLEXE", "AUTRE",
            name="type_alerte_enum",
        ), nullable=False),
        sa.Column("niveau", sa.Enum("FAIBLE", "MOYEN", "ELEVE", name="niveau_alerte_enum"), nullable=False),
        sa.Column("statut", sa.Enum("ouverte", "en_cours", "traitee", "ignoree", name="statut_alerte_enum"), nullable=False, server_default="ouverte"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("traite_par", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("traite_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── AUDIT LOGS (append-only, immuable) ────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("user_role", sa.String(50), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("detail", mysql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── DOS — DÉCLARATIONS DE SUSPICION ───────────────────────────────────────
    op.create_table(
        "declarations_suspicion",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("reference_interne", sa.String(50), nullable=False, unique=True),
        sa.Column("statut", sa.Enum("brouillon", "en_cours", "soumis", "accuse_recu", name="statut_dos_enum"), nullable=False, server_default="brouillon"),
        sa.Column("organisme_libelle", sa.String(255), nullable=True),
        sa.Column("organisme_adresse", sa.Text, nullable=True),
        sa.Column("organisme_email", sa.String(255), nullable=True),
        sa.Column("organisme_telephone", sa.String(30), nullable=True),
        sa.Column("type_soupcon_bc", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("type_soupcon_ft", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("type_soupcon_prolif", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("motifs", mysql.JSON, nullable=True),
        sa.Column("statut_operations", mysql.JSON, nullable=True),
        sa.Column("detail_transactions", mysql.JSON, nullable=True),
        sa.Column("indices_blanchiment", sa.Text, nullable=True),
        sa.Column("identification", mysql.JSON, nullable=True),
        sa.Column("relations_affaires", mysql.JSON, nullable=True),
        sa.Column("supports", mysql.JSON, nullable=True),
        sa.Column("autres_informations", sa.Text, nullable=True),
        sa.Column("initie_par", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("valide_par", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("soumis_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accuse_recu_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accuse_recu_ref", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "dos_addendums",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dos_id", sa.String(36), sa.ForeignKey("declarations_suspicion.id"), nullable=False),
        sa.Column("contenu", sa.Text, nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── RÉVISIONS KYC ────────────────────────────────────────────────────────
    op.create_table(
        "revisions_kyc",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("classification_avant", sa.String(10), nullable=True),
        sa.Column("classification_apres", sa.String(10), nullable=True),
        sa.Column("score_avant", sa.Integer, nullable=True),
        sa.Column("score_apres", sa.Integer, nullable=True),
        sa.Column("statut", sa.Enum(
            "planifiee", "en_cours", "completee", "en_retard",
            "vigilance_renforcee", "bloquee", name="statut_revision_enum",
        ), nullable=False, server_default="planifiee"),
        sa.Column("date_echeance", sa.Date, nullable=False),
        sa.Column("date_relance_1", sa.Date, nullable=True),
        sa.Column("date_relance_2", sa.Date, nullable=True),
        sa.Column("date_validation", sa.Date, nullable=True),
        sa.Column("assigned_to", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("valide_par", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("justification", sa.Text, nullable=True),
        sa.Column("documents_mis_a_jour", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── BIENS IMMOBILIERS ────────────────────────────────────────────────────
    op.create_table(
        "biens_immobiliers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dossier_id", sa.String(36), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("nature", sa.String(255), nullable=True),
        sa.Column("adresse", sa.String(500), nullable=True),
        sa.Column("valeur", sa.Numeric(15, 0), nullable=True),
        sa.Column("mode_financement", sa.Enum(
            "virement_bancaire", "cheque", "especes", "mix", "paiement_tiers", "autre",
            name="mode_financement_enum",
        ), nullable=True),
        sa.Column("titres_fonciers", sa.Text, nullable=True),
        sa.Column("observations", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── TRIGGER ANTI-SUPPRESSION DOSSIERS ARCHIVÉS (Art. 23, Art. 197) ───────
    op.execute("""
        CREATE TRIGGER prevent_archive_delete
        BEFORE DELETE ON dossiers
        FOR EACH ROW
        BEGIN
            IF OLD.statut = 'archive' THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Suppression impossible : dossier archivé — Art. 23 Ordonnance 2023-875 (Art. 197 : sanction pénale)';
            END IF;
        END
    """)

    # ── INDEX DE PERFORMANCE ─────────────────────────────────────────────────
    op.create_index("ix_dossiers_statut", "dossiers", ["statut"])
    op.create_index("ix_dossiers_classification", "dossiers", ["classification"])
    op.create_index("ix_dossiers_assigned_to", "dossiers", ["assigned_to"])
    op.create_index("ix_alertes_statut", "alertes", ["statut"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_revisions_kyc_date_echeance", "revisions_kyc", ["date_echeance"])


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS prevent_archive_delete")
    for table in [
        "biens_immobiliers", "revisions_kyc", "dos_addendums",
        "declarations_suspicion", "audit_logs", "alertes",
        "commentaires_internes", "dossiers_historique",
        "kyc_ppe", "kyc_actionnaires", "kyc_be",
        "kyc_pm", "kyc_pp", "dossiers", "users",
    ]:
        op.drop_table(table)
