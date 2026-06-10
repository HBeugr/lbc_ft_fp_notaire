import api from './api'

// ── Types ─────────────────────────────────────────────────────────────────────

export type TypeClient = 'PP' | 'PM' | 'Association' | 'Indivision'
export type TypeOperation =
  | 'vente_immobiliere' | 'manipulation_fonds' | 'constitution_societe'
  | 'fiducicommis' | 'succession' | 'donation' | 'autre'

export const TYPE_OPERATION_LABELS: Record<TypeOperation, string> = {
  vente_immobiliere: 'Vente immobilière',
  manipulation_fonds: 'Manipulation de fonds / actifs',
  constitution_societe: 'Constitution / gestion de société',
  fiducicommis: 'Fidéicommis / structures analogues',
  succession: 'Succession',
  donation: 'Donation',
  autre: 'Autre',
}

export const TYPE_OPERATION_RISQUE: Record<TypeOperation, string> = {
  vente_immobiliere: 'Élevé',
  manipulation_fonds: 'Élevé',
  constitution_societe: 'Moyen',
  fiducicommis: 'Élevé',
  succession: 'Moyen',
  donation: 'Faible',
  autre: 'Moyen',
}

export interface MandataireData {
  prenom_nom: string
  type_piece: string
  numero_piece: string
  date_naissance: string | null
  nationalite: string
  pays_residence: string
  fonction: string
}

export interface OperationsCochees {
  achat_immo: boolean
  manipulation_fonds: boolean
  creation_societe: boolean
  fiducicommis: boolean
  succession: boolean
  donation: boolean
  autre_detail: string
}

export interface OrigineFonds {
  activite: boolean
  associes: boolean
  vente_immeuble: boolean
  bancaire: boolean
  autres: string
  propriete_intervenants: boolean
  propriete_tiers: boolean
  interet_tiers: boolean
  territoire_ivoirien: boolean
  pays_provenance: string
}

export interface KycBEData {
  id?: string
  raison_sociale_nom: string
  cni_passeport: string | null
  pourcentage: number | null
  pays_residence: string | null
  date_naissance: string | null
  nationalite: string | null
}

export interface KycActData {
  id?: string
  raison_sociale_nom: string
  cni_passeport: string | null
  pourcentage: number
  pays_residence: string | null
  ordre: number
}

export interface KycPPData {
  id?: string
  dossier_id?: string
  relation_type?: string
  nom?: string
  prenoms?: string
  nom_jeune_fille?: string | null
  nom_prenoms_pere?: string | null
  nom_prenoms_mere?: string | null
  date_naissance?: string | null
  lieu_naissance?: string | null
  nationalite?: string | null
  autres_nationalites?: string | null
  statut_matrimonial?: string | null
  type_piece?: string | null
  numero_piece?: string | null
  adresse_geo?: string | null
  adresse_postale?: string | null
  telephone?: string | null
  whatsapp?: string | null
  email?: string | null
  non_resident?: boolean
  pays_residence?: string | null
  numero_contribuable?: string | null
  profession?: string | null
  profession_5_ans?: string | null
  employeur?: string | null
  secteur_activite?: string | null
  mandataire?: MandataireData | null
  est_ppe?: boolean
  ppe_detail?: string | null
  operations_cochees?: OperationsCochees | null
  description_operation?: string | null
  origine_fonds?: OrigineFonds | null
  anciennete_pro?: string | null
  date_signature?: string | null
  beneficiaires_effectifs?: KycBEData[]
}

export interface KycPMData {
  id?: string
  dossier_id?: string
  relation_type?: string
  denomination_sociale?: string
  forme_juridique?: string | null
  nom_representant_legal?: string | null
  numero_rccm?: string | null
  numero_contribuable?: string | null
  libelle_activite?: string | null
  adresse?: string | null
  telephone?: string | null
  whatsapp?: string | null
  email?: string | null
  mandataire?: MandataireData | null
  ppe_detectee?: boolean
  ppe_detail?: string | null
  operations_cochees?: OperationsCochees | null
  description_operation?: string | null
  origine_fonds?: OrigineFonds | null
  infos_pm?: { domaine_activite: string; nature_pm: string; cotee: boolean; marche_reglemente: string } | null
  anciennete_pro?: string | null
  date_signature?: string | null
  beneficiaires_effectifs?: KycBEData[]
  actionnaires?: KycActData[]
}

export interface DossierOut {
  id: string
  reference: string
  type_client: string
  type_operation: string
  type_operation_detail: string | null
  statut: string
  assigned_to: string | null
  created_by: string
  score_base: number | null
  classification: string | null
  trigger_actif: string | null
  force_par_trigger: boolean
}

// ── Service ───────────────────────────────────────────────────────────────────

export const dossiersService = {
  // Dossiers CRUD
  list: () => api.get<DossierOut[]>('/v1/dossiers').then(r => r.data),
  get: (id: string) => api.get<DossierOut>(`/v1/dossiers/${id}`).then(r => r.data),
  create: (payload: { type_client: TypeClient; type_operation: TypeOperation; type_operation_detail?: string }) =>
    api.post<DossierOut>('/v1/dossiers', payload).then(r => r.data),

  // KYC PP
  getKycPP: (dossierId: string) =>
    api.get<KycPPData>(`/v1/dossiers/${dossierId}/kyc/pp`).then(r => r.data),
  upsertKycPP: (dossierId: string, payload: Partial<KycPPData>) =>
    api.put<KycPPData>(`/v1/dossiers/${dossierId}/kyc/pp`, payload).then(r => r.data),

  // KYC PP — Bénéficiaires effectifs
  addBePP: (dossierId: string, payload: KycBEData) =>
    api.post<KycBEData>(`/v1/dossiers/${dossierId}/kyc/pp/be`, payload).then(r => r.data),
  deleteBePP: (dossierId: string, beId: string) =>
    api.delete(`/v1/dossiers/${dossierId}/kyc/pp/be/${beId}`),

  // KYC PM
  getKycPM: (dossierId: string) =>
    api.get<KycPMData>(`/v1/dossiers/${dossierId}/kyc/pm`).then(r => r.data),
  upsertKycPM: (dossierId: string, payload: Partial<KycPMData>) =>
    api.put<KycPMData>(`/v1/dossiers/${dossierId}/kyc/pm`, payload).then(r => r.data),

  // KYC PM — Bénéficiaires effectifs
  addBePM: (dossierId: string, payload: KycBEData) =>
    api.post<KycBEData>(`/v1/dossiers/${dossierId}/kyc/pm/be`, payload).then(r => r.data),
  deleteBePM: (dossierId: string, beId: string) =>
    api.delete(`/v1/dossiers/${dossierId}/kyc/pm/be/${beId}`),

  // KYC PM — Actionnaires
  addActionnaire: (dossierId: string, payload: KycActData) =>
    api.post<KycActData>(`/v1/dossiers/${dossierId}/kyc/pm/actionnaires`, payload).then(r => r.data),
  deleteActionnaire: (dossierId: string, actId: string) =>
    api.delete(`/v1/dossiers/${dossierId}/kyc/pm/actionnaires/${actId}`),
}
