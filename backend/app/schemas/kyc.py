from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from typing import Literal
from datetime import date, datetime


class _BlankToNone(BaseModel):
    """Retire les chaînes vides des selects non renseignés côté UI, pour que les
    valeurs par défaut / None s'appliquent — évite les 422 sur les champs
    Literal/enum laissés vides (ex. type_piece, anciennete_pro, relation_type)."""

    @model_validator(mode="before")
    @classmethod
    def _drop_blanks(cls, data):
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if not (isinstance(v, str) and v.strip() == "")}
        return data


# ── JSON sub-schemas ──────────────────────────────────────────────────────────

class MandataireSchema(BaseModel):
    prenom_nom: str = ""
    type_piece: str = ""
    numero_piece: str = ""
    date_naissance: str | None = None
    nationalite: str = ""
    pays_residence: str = ""
    fonction: str = ""


class OperationsCocheesSchema(BaseModel):
    achat_immo: bool = False
    manipulation_fonds: bool = False
    creation_societe: bool = False
    fiducicommis: bool = False
    succession: bool = False
    donation: bool = False
    autre_detail: str = ""


class OrigineFondsSchema(BaseModel):
    activite: bool = False
    associes: bool = False
    vente_immeuble: bool = False
    bancaire: bool = False
    autres: str = ""
    propriete_intervenants: bool = False
    propriete_tiers: bool = False
    interet_tiers: bool = False
    territoire_ivoirien: bool = True
    pays_provenance: str = ""


# ── KYC PP ───────────────────────────────────────────────────────────────────

class KycPPUpsert(_BlankToNone):
    relation_type: Literal["initiale", "actualisation"] = "initiale"
    # Identité
    nom: str = Field(..., min_length=1)
    prenoms: str = Field(..., min_length=1)
    nom_jeune_fille: str | None = None
    nom_prenoms_pere: str | None = None
    nom_prenoms_mere: str | None = None
    sexe: Literal["M", "F"] | None = None
    date_naissance: date | None = None
    lieu_naissance: str | None = None
    nationalite: str | None = None
    autres_nationalites: str | None = None
    statut_matrimonial: str | None = None
    type_piece: Literal["CNI", "Passeport", "Titre_sejour", "Carte_consulaire", "Autre"] | None = None
    numero_piece: str | None = None
    pays_emetteur_piece: str | None = None
    date_emission_piece: date | None = None
    date_expiration_piece: date | None = None
    mode_verification_piece: Literal["original_vu", "copie_certifiee", "en_ligne"] | None = None
    # Coordonnées
    adresse_geo: str | None = None
    adresse_postale: str | None = None
    telephone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    non_resident: bool = False
    pays_residence: str | None = None
    ville_residence: str | None = None
    # Professionnel & fiscal
    profession: str | None = None
    profession_5_ans: str | None = None
    employeur: str | None = None
    secteur_activite: str | None = None
    retraite: bool = False
    tranche_revenus: Literal["moins_500k", "500k_2m", "2m_10m", "plus_10m"] | None = None
    note: str | None = None
    numero_contribuable: str | None = None
    # Mandataire (JSON)
    mandataire: MandataireSchema | None = None
    # PPE
    est_ppe: bool = False
    ppe_detail: str | None = None
    # Opération
    objet_relation: str | None = None
    operations_cochees: OperationsCocheesSchema | None = None
    description_operation: str | None = None
    # Origine fonds
    origine_fonds: OrigineFondsSchema | None = None
    anciennete_pro: Literal["moins_1_an", "1_a_10_ans", "plus_10_ans"] | None = None
    date_signature: date | None = None


class KycBECreate(BaseModel):
    raison_sociale_nom: str = Field(..., min_length=1)
    cni_passeport: str | None = None
    pourcentage: float | None = Field(None, ge=0, le=100)
    pourcentage_droits_vote: float | None = Field(None, ge=0, le=100)
    entite_intermediaire_nom: str | None = None
    entite_intermediaire_pct: float | None = Field(None, ge=0, le=100)
    pays_residence: str | None = None
    date_naissance: date | None = None
    nationalite: str | None = None
    lien_avec_client: str | None = None
    entreprise_cotee: bool = False
    # Registre BE (greffe)
    registre_be_demande: Literal["oui", "non", "en_cours"] | None = None
    registre_be_resultat: Literal["conforme", "divergence", "non_trouve"] | None = None
    registre_be_note: str | None = None
    # Filtrage SFC structuré
    filtrage_sfc_resultat: Literal["aucune", "faux_positif", "correspondance"] | None = None
    filtrage_sfc_listes: dict | None = None
    filtrage_sfc_justification: str | None = None
    # Validation RC
    statut_validation: Literal["en_attente", "valide", "rejete"] = "en_attente"
    commentaire_validation: str | None = None


class KycBEUpdate(BaseModel):
    """Mise à jour partielle d'un bénéficiaire effectif (PATCH) — tous champs optionnels."""
    raison_sociale_nom: str | None = Field(None, min_length=1)
    cni_passeport: str | None = None
    pourcentage: float | None = Field(None, ge=0, le=100)
    pourcentage_droits_vote: float | None = Field(None, ge=0, le=100)
    entite_intermediaire_nom: str | None = None
    entite_intermediaire_pct: float | None = Field(None, ge=0, le=100)
    pays_residence: str | None = None
    date_naissance: date | None = None
    nationalite: str | None = None
    lien_avec_client: str | None = None
    entreprise_cotee: bool | None = None
    registre_be_demande: Literal["oui", "non", "en_cours"] | None = None
    registre_be_resultat: Literal["conforme", "divergence", "non_trouve"] | None = None
    registre_be_note: str | None = None
    filtrage_sfc_resultat: Literal["aucune", "faux_positif", "correspondance"] | None = None
    filtrage_sfc_listes: dict | None = None
    filtrage_sfc_justification: str | None = None
    statut_validation: Literal["en_attente", "valide", "rejete"] | None = None
    commentaire_validation: str | None = None


class KycPPECreate(BaseModel):
    statut_ppe: Literal["Non_PPE", "PPE_National", "PPE_Etranger", "Entourage_PPE"] = "Non_PPE"
    fonctions: str | None = None
    pays_concerne: str | None = None
    verification_giaba: bool = False
    verification_ofac: bool = False
    verification_ue: bool = False
    ras: bool = False
    # Presse négative + exposition + validation
    resultat_presse: Literal["Negatif", "Positif", "Ambigu"] | None = None
    details_presse: str | None = None
    niveau_exposition: Literal["Faible", "Moyen", "Eleve"] | None = None
    mesures_proposees: str | None = None
    statut_validation: Literal["en_attente", "valide", "rejete"] = "en_attente"
    commentaire_validation: str | None = None


class KycBEOut(BaseModel):
    id: str
    raison_sociale_nom: str
    cni_passeport: str | None
    pourcentage: float | None
    pourcentage_droits_vote: float | None = None
    entite_intermediaire_nom: str | None = None
    entite_intermediaire_pct: float | None = None
    pays_residence: str | None
    date_naissance: date | None
    nationalite: str | None
    lien_avec_client: str | None = None
    entreprise_cotee: bool = False
    registre_be_demande: str | None = None
    registre_be_resultat: str | None = None
    registre_be_note: str | None = None
    filtrage_sfc_resultat: str | None = None
    filtrage_sfc_listes: dict | None = None
    filtrage_sfc_justification: str | None = None
    statut_validation: str = "en_attente"
    commentaire_validation: str | None = None
    model_config = {"from_attributes": True}


class KycPPEOut(BaseModel):
    id: str
    statut_ppe: str
    fonctions: str | None
    pays_concerne: str | None
    verification_giaba: bool
    verification_ofac: bool
    verification_ue: bool
    ras: bool
    resultat_presse: str | None = None
    details_presse: str | None = None
    niveau_exposition: str | None = None
    mesures_proposees: str | None = None
    statut_validation: str = "en_attente"
    commentaire_validation: str | None = None
    model_config = {"from_attributes": True}


class KycPPOut(BaseModel):
    id: str
    dossier_id: str
    relation_type: str
    nom: str
    prenoms: str
    nom_jeune_fille: str | None
    nom_prenoms_pere: str | None
    nom_prenoms_mere: str | None
    sexe: str | None = None
    date_naissance: date | None
    lieu_naissance: str | None
    adresse_geo: str | None
    adresse_postale: str | None
    telephone: str | None
    whatsapp: str | None
    email: str | None
    type_piece: str | None
    numero_piece: str | None
    pays_emetteur_piece: str | None = None
    date_emission_piece: date | None = None
    date_expiration_piece: date | None = None
    mode_verification_piece: str | None = None
    numero_contribuable: str | None
    non_resident: bool
    pays_residence: str | None
    ville_residence: str | None = None
    statut_matrimonial: str | None
    nationalite: str | None
    autres_nationalites: str | None
    profession: str | None
    profession_5_ans: str | None
    employeur: str | None
    secteur_activite: str | None
    retraite: bool = False
    tranche_revenus: str | None = None
    note: str | None = None
    mandataire: dict | None
    est_ppe: bool
    ppe_detail: str | None
    objet_relation: str | None = None
    operations_cochees: dict | None
    description_operation: str | None
    origine_fonds: dict | None
    anciennete_pro: str | None
    date_signature: date | None
    photo_path: str | None
    beneficiaires_effectifs: list[KycBEOut] = []
    ppe_declarations: list[KycPPEOut] = []
    model_config = {"from_attributes": True}


# ── KYC PM ───────────────────────────────────────────────────────────────────

class InfosPMSchema(BaseModel):
    domaine_activite: str = ""
    nature_pm: str = ""
    cotee: bool = False
    marche_reglemente: str = ""


class KycActCreate(BaseModel):
    raison_sociale_nom: str = Field(..., min_length=1)
    type_personne: Literal["PP", "PM"] | None = None
    cni_passeport: str | None = None
    pourcentage: float = Field(..., ge=0, le=100)
    pays_residence: str | None = None
    ordre: int = 1


class KycActOut(BaseModel):
    id: str
    raison_sociale_nom: str
    type_personne: str | None = None
    cni_passeport: str | None
    pourcentage: float
    pays_residence: str | None
    ordre: int
    model_config = {"from_attributes": True}


class KycPMUpsert(_BlankToNone):
    relation_type: Literal["initiale", "actualisation"] = "initiale"
    denomination_sociale: str = Field(..., min_length=1)
    nom_commercial: str | None = None
    forme_juridique: str | None = None
    pays_constitution: str | None = None
    nom_representant_legal: str | None = None
    numero_rccm: str | None = None
    date_emission_rccm: date | None = None
    numero_contribuable: str | None = None
    objet_social: str | None = None
    libelle_activite: str | None = None
    ca_annuel: float | None = None
    effectif: int | None = None
    pays_operations: str | None = None
    volume_transactions: str | None = None
    representant_statut_ppe: bool = False
    adresse: str | None = None
    telephone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    mandataire: MandataireSchema | None = None
    ppe_detectee: bool = False
    ppe_detail: str | None = None
    operations_cochees: OperationsCocheesSchema | None = None
    description_operation: str | None = None
    origine_fonds: OrigineFondsSchema | None = None
    infos_pm: InfosPMSchema | None = None
    anciennete_pro: Literal["moins_1_an", "1_a_10_ans", "plus_10_ans"] | None = None
    date_signature: date | None = None


class KycPMOut(BaseModel):
    id: str
    dossier_id: str
    relation_type: str
    denomination_sociale: str
    nom_commercial: str | None = None
    forme_juridique: str | None
    pays_constitution: str | None = None
    nom_representant_legal: str | None
    numero_rccm: str | None
    date_emission_rccm: date | None = None
    date_expiration_rccm: date | None = None
    numero_contribuable: str | None
    objet_social: str | None = None
    libelle_activite: str | None
    ca_annuel: float | None = None
    effectif: int | None = None
    pays_operations: str | None = None
    volume_transactions: str | None = None
    representant_statut_ppe: bool = False
    adresse: str | None
    telephone: str | None
    whatsapp: str | None
    email: str | None
    mandataire: dict | None
    ppe_detectee: bool
    ppe_detail: str | None
    operations_cochees: dict | None
    description_operation: str | None
    origine_fonds: dict | None
    infos_pm: dict | None
    anciennete_pro: str | None
    date_signature: date | None
    beneficiaires_effectifs: list[KycBEOut] = []
    actionnaires: list[KycActOut] = []
    ppe_declarations: list[KycPPEOut] = []
    model_config = {"from_attributes": True}


# ── Dossier ───────────────────────────────────────────────────────────────────

TypeClient = Literal["PP", "PM", "Association", "Indivision"]
TypeOperation = Literal[
    "vente_immobiliere", "manipulation_fonds", "constitution_societe",
    "fiducicommis", "succession", "donation", "autre"
]

ModePaiement = Literal["virement", "cheque", "especes", "mix", "paiement_tiers"]


class DossierCreate(BaseModel):
    type_client: TypeClient
    type_operation: TypeOperation
    type_operation_detail: str | None = None
    nature_relation: Literal["ponctuelle", "durable"] | None = None
    montant_transaction: float | None = None
    mode_paiement: ModePaiement | None = None
    nb_parties: int = 1


class DossierTransactionRequest(BaseModel):
    montant_tranche: Literal["moins_15m", "plus_15m"] | None = None
    montant_transaction: float | None = Field(None, ge=0)
    mode_paiement: Literal["especes", "cheque", "virement", "autre"] | None = None


class DossierOut(BaseModel):
    id: str
    reference: str
    type_client: str
    type_operation: str
    type_operation_detail: str | None
    nature_relation: str | None = None
    montant_transaction: float | None
    montant_tranche: str | None = None
    mode_paiement: str | None
    surveillance_espece: bool = False
    nb_parties: int
    statut: str
    assigned_to: str | None
    assigned_to_name: str | None = None
    created_by: str
    score_base: int | None
    classification: str | None
    trigger_actif: str | None
    force_par_trigger: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    kyc_pp: KycPPOut | None = None
    kyc_pm: KycPMOut | None = None
    model_config = {"from_attributes": True}


# ── Scoring / Matrice de risque (CDC Module 2) ─────────────────────────────────

AxisCode = Literal[
    "type_client", "pays_geographie", "type_operation", "montant", "mode_paiement",
    "complexite", "ppe", "coherence_doc", "secteur", "intermediaires",
]


class ScoringAxisPrefill(BaseModel):
    valeur: int
    auto: bool
    source: str = ""


class ScoringPrefillOut(BaseModel):
    axes: dict[str, ScoringAxisPrefill]


class OverrideIn(BaseModel):
    axe: str
    valeur_override: int = Field(..., ge=0, le=2)
    justification: str = Field(..., min_length=50)


class ScoreCalcIn(BaseModel):
    axes: dict[str, int] = Field(default_factory=dict)
    # Données opération (persistées sur le dossier)
    montant_transaction: float | None = None
    mode_paiement: ModePaiement | None = None
    nb_parties: int | None = None
    # Triggers explicites saisis par l'agent (T3–T6 ; T1/T2 dérivés)
    sur_liste_sanctions: bool = False
    pays_liste_noire_gafi: bool = False
    pays_liste_grise_gafi: bool = False
    refus_documents: bool = False
    be_non_identifiable: bool = False
    overrides: list[OverrideIn] = Field(default_factory=list)


class ScoreAxisOut(BaseModel):
    code: str
    label: str
    score: int


class ScoreResultOut(BaseModel):
    total: int
    niveau: str
    axes: list[ScoreAxisOut]
    triggers_actifs: list[str]
    force_par_trigger: bool
    trigger_principal: str | None


# ── Simulateur stateless (onglet « Simulateur de Risque ») ─────────────────────

class SimulateurIn(BaseModel):
    profil_code: str = ""
    zone_geo: str = ""
    type_operation: str = ""
    montant: int = Field(0, ge=0, le=2)
    mode_paiement_code: str = ""
    montage_juridique: int = Field(0, ge=0, le=2)
    is_ppe: bool = False
    qualite_code: str = ""
    secteur_activite: int = Field(0, ge=0, le=2)
    reseau_code: str = ""


class SimAxeOut(BaseModel):
    code: str
    label: str
    score: int
    justification: str = ""


class SimResultOut(BaseModel):
    score_total: int
    niveau: str
    axes: list[SimAxeOut]
