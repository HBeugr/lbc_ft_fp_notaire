import uuid
from datetime import date
from sqlalchemy import String, Boolean, Enum as SAEnum, ForeignKey, DateTime, Date, Text, Numeric, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Dossier(Base):
    __tablename__ = "dossiers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    type_client: Mapped[str] = mapped_column(
        SAEnum("PP", "PM", "Association", "Indivision", name="type_client_enum"),
        nullable=False,
    )
    type_operation: Mapped[str] = mapped_column(
        SAEnum(
            "vente_immobiliere",
            "manipulation_fonds",
            "constitution_societe",
            "fiducicommis",
            "succession",
            "donation",
            "autre",
            name="type_operation_enum",
        ),
        nullable=False,
    )
    type_operation_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    statut: Mapped[str] = mapped_column(
        SAEnum(
            "brouillon", "en_analyse", "vigilance_renforcee",
            "valide", "bloque", "traite", "cloture", "archive",
            name="statut_dossier_enum",
        ),
        nullable=False,
        default="brouillon",
    )
    assigned_to: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    score_base: Mapped[int | None] = mapped_column(nullable=True)
    classification: Mapped[str | None] = mapped_column(
        SAEnum("FAIBLE", "MOYEN", "ELEVE", name="classification_enum"), nullable=True
    )
    trigger_actif: Mapped[str | None] = mapped_column(String(10), nullable=True)
    force_par_trigger: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vigilance_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    archivage_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    archivage_expiration: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    kyc_pp: Mapped["KycPP | None"] = relationship("KycPP", back_populates="dossier", uselist=False)
    kyc_pm: Mapped["KycPM | None"] = relationship("KycPM", back_populates="dossier", uselist=False)
    historique: Mapped[list["DossierHistorique"]] = relationship("DossierHistorique", back_populates="dossier")
    commentaires: Mapped[list["CommentaireInterne"]] = relationship("CommentaireInterne", back_populates="dossier")


class KycPP(Base):
    """KYC Personne Physique — Chambre des Notaires de Côte d'Ivoire (Mai 2025)."""
    __tablename__ = "kyc_pp"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id: Mapped[str] = mapped_column(String(36), ForeignKey("dossiers.id"), nullable=False, unique=True)

    # Section 1 — Identité
    relation_type: Mapped[str] = mapped_column(
        SAEnum("initiale", "actualisation", name="relation_type_enum"), nullable=False, default="initiale"
    )
    nom: Mapped[str] = mapped_column(String(150), nullable=False)
    prenoms: Mapped[str] = mapped_column(String(150), nullable=False)
    nom_jeune_fille: Mapped[str | None] = mapped_column(String(150), nullable=True)
    nom_prenoms_pere: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nom_prenoms_mere: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_naissance: Mapped[Date | None] = mapped_column(Date, nullable=True)
    lieu_naissance: Mapped[str | None] = mapped_column(String(150), nullable=True)
    adresse_geo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    adresse_postale: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type_piece: Mapped[str | None] = mapped_column(
        SAEnum("CNI", "Passeport", "Titre_sejour", "Carte_consulaire", "Autre", name="type_piece_pp_enum"),
        nullable=True,
    )
    numero_piece: Mapped[str | None] = mapped_column(String(100), nullable=True)
    numero_contribuable: Mapped[str | None] = mapped_column(String(100), nullable=True)
    non_resident: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pays_residence: Mapped[str | None] = mapped_column(String(100), nullable=True)
    statut_matrimonial: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nationalite: Mapped[str | None] = mapped_column(String(100), nullable=True)
    autres_nationalites: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profession: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profession_5_ans: Mapped[str | None] = mapped_column(Text, nullable=True)
    employeur: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secteur_activite: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Section 2 — Mandataire (JSON : nom, cni_passeport, date_naissance, nationalite, pays_residence, fonction)
    mandataire: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Section 3 — PPE
    est_ppe: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ppe_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Section 4 — Description de l'opération
    # JSON : {achat_immo, manipulation_fonds, creation_societe, fiducicommis, autre_detail}
    operations_cochees: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description_operation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Section 5 — Origine des fonds
    # JSON : {activite, associes, vente_immeuble, bancaire, autres, propriete_intervenants,
    #         propriete_tiers, interet_tiers, territoire_ivoirien, pays_provenance}
    origine_fonds: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    anciennete_pro: Mapped[str | None] = mapped_column(
        SAEnum("moins_1_an", "1_a_10_ans", "plus_10_ans", name="anciennete_pp_enum"), nullable=True
    )
    date_signature: Mapped[Date | None] = mapped_column(Date, nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    dossier: Mapped["Dossier"] = relationship("Dossier", back_populates="kyc_pp")
    beneficiaires_effectifs: Mapped[list["KycBE"]] = relationship("KycBE", back_populates="kyc_pp")
    ppe_declarations: Mapped[list["KycPPE"]] = relationship("KycPPE", back_populates="kyc_pp")


class KycPM(Base):
    """KYC Personne Morale — Chambre des Notaires de Côte d'Ivoire (Mai 2025)."""
    __tablename__ = "kyc_pm"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id: Mapped[str] = mapped_column(String(36), ForeignKey("dossiers.id"), nullable=False, unique=True)

    # Section 1 — Identité PM
    relation_type: Mapped[str] = mapped_column(
        SAEnum("initiale", "actualisation", name="relation_type_pm_enum"), nullable=False, default="initiale"
    )
    denomination_sociale: Mapped[str] = mapped_column(String(255), nullable=False)
    forme_juridique: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nom_representant_legal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    numero_rccm: Mapped[str | None] = mapped_column(String(100), nullable=True)
    numero_contribuable: Mapped[str | None] = mapped_column(String(100), nullable=True)
    libelle_activite: Mapped[str | None] = mapped_column(String(500), nullable=True)
    adresse: Mapped[str | None] = mapped_column(String(500), nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Section 2 — Représentant légal / Mandataire (JSON : même structure que PP)
    mandataire: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Section 5 — PPE (présence PPE parmi BE/dirigeants)
    ppe_detectee: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ppe_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Section 6 — Description de l'opération (même JSON que PP)
    operations_cochees: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description_operation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Section 7 — Origine des fonds (même JSON que PP)
    origine_fonds: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Informations PM complémentaires
    # JSON : {domaine_activite, nature_pm, cotee, marche_reglemente}
    infos_pm: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    anciennete_pro: Mapped[str | None] = mapped_column(
        SAEnum("moins_1_an", "1_a_10_ans", "plus_10_ans", name="anciennete_pm_enum"), nullable=True
    )
    date_signature: Mapped[Date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    dossier: Mapped["Dossier"] = relationship("Dossier", back_populates="kyc_pm")
    beneficiaires_effectifs: Mapped[list["KycBE"]] = relationship("KycBE", back_populates="kyc_pm")
    actionnaires: Mapped[list["KycActionnaire"]] = relationship("KycActionnaire", back_populates="kyc_pm")
    ppe_declarations: Mapped[list["KycPPE"]] = relationship("KycPPE", back_populates="kyc_pm")


class KycBE(Base):
    """Bénéficiaire Effectif — partagé PP (tout BE) et PM (seuil ≥ 25%, Art. 12b)."""
    __tablename__ = "kyc_be"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kyc_pp_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("kyc_pp.id"), nullable=True)
    kyc_pm_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("kyc_pm.id"), nullable=True)
    raison_sociale_nom: Mapped[str] = mapped_column(String(255), nullable=False)
    cni_passeport: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pourcentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    pays_residence: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_naissance: Mapped[Date | None] = mapped_column(Date, nullable=True)
    nationalite: Mapped[str | None] = mapped_column(String(100), nullable=True)

    kyc_pp: Mapped["KycPP | None"] = relationship("KycPP", back_populates="beneficiaires_effectifs")
    kyc_pm: Mapped["KycPM | None"] = relationship("KycPM", back_populates="beneficiaires_effectifs")


class KycActionnaire(Base):
    """Structure de propriété — actionnaires/associés PM (ordre décroissant)."""
    __tablename__ = "kyc_actionnaires"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kyc_pm_id: Mapped[str] = mapped_column(String(36), ForeignKey("kyc_pm.id"), nullable=False)
    raison_sociale_nom: Mapped[str] = mapped_column(String(255), nullable=False)
    cni_passeport: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pourcentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    pays_residence: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ordre: Mapped[int] = mapped_column(nullable=False, default=1)

    kyc_pm: Mapped["KycPM"] = relationship("KycPM", back_populates="actionnaires")


class KycPPE(Base):
    """Déclaration PPE détaillée."""
    __tablename__ = "kyc_ppe"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kyc_pp_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("kyc_pp.id"), nullable=True)
    kyc_pm_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("kyc_pm.id"), nullable=True)
    statut_ppe: Mapped[str] = mapped_column(
        SAEnum("Non_PPE", "PPE_National", "PPE_Etranger", "Entourage_PPE", name="statut_ppe_enum"),
        nullable=False,
        default="Non_PPE",
    )
    fonctions: Mapped[str | None] = mapped_column(Text, nullable=True)
    pays_concerne: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verification_giaba: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_ofac: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_ue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ras: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    kyc_pp: Mapped["KycPP | None"] = relationship("KycPP", back_populates="ppe_declarations")
    kyc_pm: Mapped["KycPM | None"] = relationship("KycPM", back_populates="ppe_declarations")


class DossierHistorique(Base):
    """Piste d'audit des changements d'état — append-only."""
    __tablename__ = "dossiers_historique"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id: Mapped[str] = mapped_column(String(36), ForeignKey("dossiers.id"), nullable=False)
    statut_avant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    statut_apres: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    commentaire: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dossier: Mapped["Dossier"] = relationship("Dossier", back_populates="historique")


class CommentaireInterne(Base):
    """Commentaires internes horodatés — confidentiels, append-only."""
    __tablename__ = "commentaires_internes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id: Mapped[str] = mapped_column(String(36), ForeignKey("dossiers.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    contenu: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dossier: Mapped["Dossier"] = relationship("Dossier", back_populates="commentaires")
