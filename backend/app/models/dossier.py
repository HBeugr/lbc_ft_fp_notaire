import uuid
from datetime import date
from sqlalchemy import String, Boolean, Enum as SAEnum, ForeignKey, DateTime, Date, Text, Numeric, SmallInteger, Integer, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.crypto import EncryptedString


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
    # Nature de la relation d'affaires anticipée (M4) — une relation durable impose le KYC complet (Type B)
    nature_relation: Mapped[str | None] = mapped_column(
        SAEnum("ponctuelle", "durable", name="nature_relation_enum"), nullable=True
    )
    # Données opération alimentant la matrice (axes 4 & 5, trigger T2) — CDC Module 2
    montant_transaction: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    # Tranche de montant (étape Transaction du KYC) — sélecteur < 15M / > 15M
    montant_tranche: Mapped[str | None] = mapped_column(
        SAEnum("moins_15m", "plus_15m", name="montant_tranche_enum"), nullable=True
    )
    mode_paiement: Mapped[str | None] = mapped_column(
        SAEnum("virement", "cheque", "especes", "mix", "paiement_tiers", "autre", name="mode_paiement_enum"),
        nullable=True,
    )
    # Déclaration systématique de transaction en espèces (espèces > 15M FCFA) — opération à surveiller
    surveillance_espece: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    nb_parties: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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
    # Blocage du dossier (sanctions T3 / DOS)
    is_bloque: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
    evaluation: Mapped["EvaluationRisque | None"] = relationship("EvaluationRisque", back_populates="dossier", uselist=False)


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
    # Champs sensibles chiffrés au repos (AES-256, CDC §5.2)
    adresse_geo: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    adresse_postale: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    telephone: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    email: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    type_piece: Mapped[str | None] = mapped_column(
        SAEnum("CNI", "Passeport", "Titre_sejour", "Carte_consulaire", "Autre", name="type_piece_pp_enum"),
        nullable=True,
    )
    numero_piece: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    pays_emetteur_piece: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_emission_piece: Mapped[Date | None] = mapped_column(Date, nullable=True)
    date_expiration_piece: Mapped[Date | None] = mapped_column(Date, nullable=True)
    mode_verification_piece: Mapped[str | None] = mapped_column(
        SAEnum("original_vu", "copie_certifiee", "en_ligne", name="mode_verification_piece_enum"), nullable=True
    )
    numero_contribuable: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    # Identité complémentaire (CDC Module 1.1)
    sexe: Mapped[str | None] = mapped_column(SAEnum("M", "F", name="sexe_enum"), nullable=True)
    non_resident: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pays_residence: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ville_residence: Mapped[str | None] = mapped_column(String(150), nullable=True)
    statut_matrimonial: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nationalite: Mapped[str | None] = mapped_column(String(100), nullable=True)
    autres_nationalites: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profession: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profession_5_ans: Mapped[str | None] = mapped_column(Text, nullable=True)
    employeur: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secteur_activite: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retraite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Tranche réglementaire de revenus (CDC : <500K / 500K-2M / 2M-10M / >10M FCFA)
    tranche_revenus: Mapped[str | None] = mapped_column(
        SAEnum("moins_500k", "500k_2m", "2m_10m", "plus_10m", name="tranche_revenus_enum"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Section 2 — Mandataire (JSON : nom, cni_passeport, date_naissance, nationalite, pays_residence, fonction)
    mandataire: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Section 3 — PPE
    est_ppe: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ppe_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Section 4 — Description de l'opération
    # Objet de la relation d'affaires (finalité anticipée — obligatoire pour une relation durable)
    objet_relation: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    nom_commercial: Mapped[str | None] = mapped_column(String(255), nullable=True)
    forme_juridique: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pays_constitution: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nom_representant_legal: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    numero_rccm: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    # RCCM — validité 90 jours (M7) : date d'émission saisie, expiration calculée (+90 j) au save
    date_emission_rccm: Mapped[Date | None] = mapped_column(Date, nullable=True)
    date_expiration_rccm: Mapped[Date | None] = mapped_column(Date, nullable=True)
    numero_contribuable: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    objet_social: Mapped[str | None] = mapped_column(Text, nullable=True)
    libelle_activite: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Profil financier (CDC Module 1.2)
    ca_annuel: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    effectif: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pays_operations: Mapped[str | None] = mapped_column(String(255), nullable=True)
    volume_transactions: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Le représentant légal est-il une PPE ? (M5)
    representant_statut_ppe: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    adresse: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    telephone: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    email: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)

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
    cni_passeport: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    pourcentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    # % de droits de vote (distinct de la détention du capital)
    pourcentage_droits_vote: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    # Contrôle indirect via entité intermédiaire (chaîne de détention)
    entite_intermediaire_nom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entite_intermediaire_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    pays_residence: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_naissance: Mapped[Date | None] = mapped_column(Date, nullable=True)
    nationalite: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Lien avec le client (CDC 1.1 BE PP) + entreprise cotée (CDC 1.2 BE PM)
    lien_avec_client: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entreprise_cotee: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Registre officiel des bénéficiaires effectifs (greffe / RCCM)
    registre_be_demande: Mapped[str | None] = mapped_column(
        SAEnum("oui", "non", "en_cours", name="registre_be_demande_enum"), nullable=True
    )
    registre_be_resultat: Mapped[str | None] = mapped_column(
        SAEnum("conforme", "divergence", "non_trouve", name="registre_be_resultat_enum"), nullable=True
    )
    registre_be_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Filtrage SFC (Sanctions / Fichiers de Criblage) structuré
    filtrage_sfc_resultat: Mapped[str | None] = mapped_column(
        SAEnum("aucune", "faux_positif", "correspondance", name="filtrage_sfc_resultat_enum"), nullable=True
    )
    filtrage_sfc_listes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    filtrage_sfc_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filtrage_sfc_justification: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Validation du BE par le Responsable Conformité (gate : PM non validable sans ≥1 BE validé)
    statut_validation: Mapped[str] = mapped_column(
        SAEnum("en_attente", "valide", "rejete", name="statut_validation_be_enum"),
        nullable=False, default="en_attente",
    )
    commentaire_validation: Mapped[str | None] = mapped_column(Text, nullable=True)

    kyc_pp: Mapped["KycPP | None"] = relationship("KycPP", back_populates="beneficiaires_effectifs")
    kyc_pm: Mapped["KycPM | None"] = relationship("KycPM", back_populates="beneficiaires_effectifs")


class KycActionnaire(Base):
    """Structure de propriété — actionnaires/associés PM (ordre décroissant)."""
    __tablename__ = "kyc_actionnaires"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kyc_pm_id: Mapped[str] = mapped_column(String(36), ForeignKey("kyc_pm.id"), nullable=False)
    raison_sociale_nom: Mapped[str] = mapped_column(String(255), nullable=False)
    type_personne: Mapped[str | None] = mapped_column(
        SAEnum("PP", "PM", name="type_personne_actionnaire_enum"), nullable=True
    )
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
    # Recherche de presse négative (adverse media)
    resultat_presse: Mapped[str | None] = mapped_column(
        SAEnum("Negatif", "Positif", "Ambigu", name="resultat_presse_enum"), nullable=True
    )
    details_presse: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Évaluation du niveau d'exposition + mesures de vigilance renforcée
    niveau_exposition: Mapped[str | None] = mapped_column(
        SAEnum("Faible", "Moyen", "Eleve", name="niveau_exposition_ppe_enum"), nullable=True
    )
    mesures_proposees: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Validation par le Responsable Conformité
    statut_validation: Mapped[str] = mapped_column(
        SAEnum("en_attente", "valide", "rejete", name="statut_validation_ppe_enum"),
        nullable=False, default="en_attente",
    )
    commentaire_validation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    kyc_pp: Mapped["KycPP | None"] = relationship("KycPP", back_populates="ppe_declarations")
    kyc_pm: Mapped["KycPM | None"] = relationship("KycPM", back_populates="ppe_declarations")


class EvaluationRisque(Base):
    """Résultat horodaté de la matrice de risque (CDC Module 2).

    10 axes × {0,1,2} → score /20 ; 6 triggers absolutoires forcent ELEVE.
    `dossier.score_base`/`classification` sont un cache dénormalisé de cette table.
    """
    __tablename__ = "evaluations_risque"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id: Mapped[str] = mapped_column(String(36), ForeignKey("dossiers.id"), nullable=False, unique=True)

    # 10 axes canoniques (ordre CDC v4)
    axe_type_client: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    axe_pays_geographie: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    axe_type_operation: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    axe_montant: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    axe_mode_paiement: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    axe_complexite: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    axe_ppe: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    axe_coherence_doc: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    axe_secteur: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    axe_intermediaires: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # Résultat
    score_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    classification: Mapped[str] = mapped_column(
        SAEnum("FAIBLE", "MOYEN", "ELEVE", name="classification_enum"), nullable=False, default="FAIBLE"
    )
    trigger_principal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    triggers_actifs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    force_par_trigger: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Flags triggers explicites (saisis par l'agent)
    sur_liste_sanctions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pays_liste_noire_gafi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pays_liste_grise_gafi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    refus_documents: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    be_non_identifiable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Audit overrides : [{axe, valeur_auto, valeur_override, justification, user_id, ts}]
    overrides: Mapped[list | None] = mapped_column(JSON, nullable=True)
    evaluated_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    evaluated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    dossier: Mapped["Dossier"] = relationship("Dossier", back_populates="evaluation")


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
