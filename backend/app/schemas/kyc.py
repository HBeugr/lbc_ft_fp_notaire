from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
from datetime import date


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

class KycPPUpsert(BaseModel):
    relation_type: Literal["initiale", "actualisation"] = "initiale"
    # Identité
    nom: str = Field(..., min_length=1)
    prenoms: str = Field(..., min_length=1)
    nom_jeune_fille: str | None = None
    nom_prenoms_pere: str | None = None
    nom_prenoms_mere: str | None = None
    date_naissance: date | None = None
    lieu_naissance: str | None = None
    nationalite: str | None = None
    autres_nationalites: str | None = None
    statut_matrimonial: str | None = None
    type_piece: Literal["CNI", "Passeport", "Titre_sejour", "Carte_consulaire", "Autre"] | None = None
    numero_piece: str | None = None
    # Coordonnées
    adresse_geo: str | None = None
    adresse_postale: str | None = None
    telephone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    non_resident: bool = False
    pays_residence: str | None = None
    # Professionnel & fiscal
    profession: str | None = None
    profession_5_ans: str | None = None
    employeur: str | None = None
    secteur_activite: str | None = None
    numero_contribuable: str | None = None
    # Mandataire (JSON)
    mandataire: MandataireSchema | None = None
    # PPE
    est_ppe: bool = False
    ppe_detail: str | None = None
    # Opération
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
    pays_residence: str | None = None
    date_naissance: date | None = None
    nationalite: str | None = None


class KycPPECreate(BaseModel):
    statut_ppe: Literal["Non_PPE", "PPE_National", "PPE_Etranger", "Entourage_PPE"] = "Non_PPE"
    fonctions: str | None = None
    pays_concerne: str | None = None
    verification_giaba: bool = False
    verification_ofac: bool = False
    verification_ue: bool = False
    ras: bool = False


class KycBEOut(BaseModel):
    id: str
    raison_sociale_nom: str
    cni_passeport: str | None
    pourcentage: float | None
    pays_residence: str | None
    date_naissance: date | None
    nationalite: str | None
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
    date_naissance: date | None
    lieu_naissance: str | None
    adresse_geo: str | None
    adresse_postale: str | None
    telephone: str | None
    whatsapp: str | None
    email: str | None
    type_piece: str | None
    numero_piece: str | None
    numero_contribuable: str | None
    non_resident: bool
    pays_residence: str | None
    statut_matrimonial: str | None
    nationalite: str | None
    autres_nationalites: str | None
    profession: str | None
    profession_5_ans: str | None
    employeur: str | None
    secteur_activite: str | None
    mandataire: dict | None
    est_ppe: bool
    ppe_detail: str | None
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
    cni_passeport: str | None = None
    pourcentage: float = Field(..., ge=0, le=100)
    pays_residence: str | None = None
    ordre: int = 1


class KycActOut(BaseModel):
    id: str
    raison_sociale_nom: str
    cni_passeport: str | None
    pourcentage: float
    pays_residence: str | None
    ordre: int
    model_config = {"from_attributes": True}


class KycPMUpsert(BaseModel):
    relation_type: Literal["initiale", "actualisation"] = "initiale"
    denomination_sociale: str = Field(..., min_length=1)
    forme_juridique: str | None = None
    nom_representant_legal: str | None = None
    numero_rccm: str | None = None
    numero_contribuable: str | None = None
    libelle_activite: str | None = None
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
    forme_juridique: str | None
    nom_representant_legal: str | None
    numero_rccm: str | None
    numero_contribuable: str | None
    libelle_activite: str | None
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
    montant_transaction: float | None = None
    mode_paiement: ModePaiement | None = None
    nb_parties: int = 1


class DossierOut(BaseModel):
    id: str
    reference: str
    type_client: str
    type_operation: str
    type_operation_detail: str | None
    montant_transaction: float | None
    mode_paiement: str | None
    nb_parties: int
    statut: str
    assigned_to: str | None
    created_by: str
    score_base: int | None
    classification: str | None
    trigger_actif: str | None
    force_par_trigger: bool
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
