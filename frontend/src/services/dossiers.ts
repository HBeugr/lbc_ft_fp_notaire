import api from './api'

// ── Types ─────────────────────────────────────────────────────────────────────

export type TypeClient = 'PP' | 'PM' | 'Association' | 'Indivision'
export type TypeOperation =
  | 'vente_immobiliere' | 'manipulation_fonds' | 'constitution_societe'
  | 'fiducicommis' | 'succession' | 'donation' | 'autre'

export type StatutDossier =
  | 'brouillon' | 'en_analyse' | 'vigilance_renforcee' | 'valide'
  | 'actif' | 'actif_sous_surveillance' | 'bloque' | 'traite'
  | 'resilie' | 'cloture' | 'archive'

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

export type ModePaiement = 'virement' | 'cheque' | 'especes' | 'mix' | 'paiement_tiers'

export interface DossierOut {
  id: string
  reference: string
  type_client: string
  type_operation: string
  type_operation_detail: string | null
  montant_transaction: number | null
  mode_paiement: string | null
  nb_parties: number
  statut: string
  assigned_to: string | null
  created_by: string
  score_base: number | null
  classification: string | null
  trigger_actif: string | null
  force_par_trigger: boolean
  kyc_pp?: KycPPData | null
  kyc_pm?: KycPMData | null
  kyc_be_list?: KycBEData[]
  kyc_ppe_list?: unknown[]
}

// ── Scoring / Matrice de risque (CDC Module 2) ────────────────────────────────

export interface ScoringAxisPrefill {
  valeur: number
  auto: boolean
  source: string
}

export interface ScoringPrefill {
  axes: Record<string, ScoringAxisPrefill>
}

export interface ScoreOverride {
  axe: string
  valeur_override: number
  justification: string
}

export interface ScoreCalcPayload {
  axes: Record<string, number>
  montant_transaction?: number | null
  mode_paiement?: ModePaiement | null
  nb_parties?: number | null
  sur_liste_sanctions: boolean
  pays_liste_noire_gafi: boolean
  pays_liste_grise_gafi: boolean
  refus_documents: boolean
  be_non_identifiable: boolean
  overrides: ScoreOverride[]
}

export interface ScoreAxisResult {
  code: string
  label: string
  score: number
}

export interface ScoreResult {
  total: number
  niveau: string
  axes: ScoreAxisResult[]
  triggers_actifs: string[]
  force_par_trigger: boolean
  trigger_principal: string | null
}

export interface DossierListResponse {
  items: DossierOut[]
  total: number
}

export interface CommentaireOut {
  id: string
  dossier_id: string
  auteur_id: string
  contenu: string
  created_at: string
}

export interface HistoriqueOut {
  id: string
  dossier_id: string
  action: string
  user_id: string | null
  created_at: string
  detail: Record<string, unknown> | null
}

// ── Service ───────────────────────────────────────────────────────────────────

export const dossiersService = {
  // Dossiers CRUD
  async list(params: { statut?: string; classification?: string; reference?: string; page?: number; page_size?: number } = {}): Promise<DossierListResponse> {
    const { data } = await api.get<DossierOut[]>('/dossiers', { params })
    if (Array.isArray(data)) return { items: data, total: data.length }
    return data as unknown as DossierListResponse
  },

  get: (id: string) => api.get<DossierOut>(`/dossiers/${id}`).then(r => r.data),

  create: (payload: { type_client: TypeClient; type_operation: TypeOperation; type_operation_detail?: string }) =>
    api.post<DossierOut>('/dossiers', payload).then(r => r.data),

  // KYC PP
  getKycPP: (dossierId: string) =>
    api.get<KycPPData>(`/dossiers/${dossierId}/kyc/pp`).then(r => r.data),

  upsertKycPP: (dossierId: string, payload: Partial<KycPPData>) =>
    api.put<KycPPData>(`/dossiers/${dossierId}/kyc/pp`, payload).then(r => r.data),

  async saveKycPP(dossierId: string, _section: number, payload: Partial<KycPPData>): Promise<KycPPData> {
    const { data } = await api.put<KycPPData>(`/dossiers/${dossierId}/kyc/pp`, payload)
    return data
  },

  // KYC PP — Bénéficiaires effectifs
  addBePP: (dossierId: string, payload: KycBEData) =>
    api.post<KycBEData>(`/dossiers/${dossierId}/kyc/pp/be`, payload).then(r => r.data),
  deleteBePP: (dossierId: string, beId: string) =>
    api.delete(`/dossiers/${dossierId}/kyc/pp/be/${beId}`),

  // KYC PM
  getKycPM: (dossierId: string) =>
    api.get<KycPMData>(`/dossiers/${dossierId}/kyc/pm`).then(r => r.data),

  upsertKycPM: (dossierId: string, payload: Partial<KycPMData>) =>
    api.put<KycPMData>(`/dossiers/${dossierId}/kyc/pm`, payload).then(r => r.data),

  async saveKycPM(dossierId: string, _section: number, payload: Partial<KycPMData>): Promise<KycPMData> {
    const { data } = await api.put<KycPMData>(`/dossiers/${dossierId}/kyc/pm`, payload)
    return data
  },

  // KYC PM — Bénéficiaires effectifs
  addBePM: (dossierId: string, payload: KycBEData) =>
    api.post<KycBEData>(`/dossiers/${dossierId}/kyc/pm/be`, payload).then(r => r.data),
  deleteBePM: (dossierId: string, beId: string) =>
    api.delete(`/dossiers/${dossierId}/kyc/pm/be/${beId}`),

  // KYC PM — Actionnaires
  addActionnaire: (dossierId: string, payload: KycActData) =>
    api.post<KycActData>(`/dossiers/${dossierId}/kyc/pm/actionnaires`, payload).then(r => r.data),
  deleteActionnaire: (dossierId: string, actId: string) =>
    api.delete(`/dossiers/${dossierId}/kyc/pm/actionnaires/${actId}`),

  // Scoring / Matrice de risque
  getScoringPrefill: (dossierId: string) =>
    api.get<ScoringPrefill>(`/dossiers/${dossierId}/scoring/prefill`).then(r => r.data),

  calculateScore: (dossierId: string, payload: ScoreCalcPayload) =>
    api.post<ScoreResult>(`/dossiers/${dossierId}/scoring/calculate`, payload).then(r => r.data),

  // Commentaires
  async listCommentaires(dossierId: string): Promise<CommentaireOut[]> {
    const { data } = await api.get<CommentaireOut[]>(`/dossiers/${dossierId}/commentaires`)
    return data
  },

  async addCommentaire(dossierId: string, contenu: string): Promise<CommentaireOut> {
    const { data } = await api.post<CommentaireOut>(`/dossiers/${dossierId}/commentaires`, { contenu })
    return data
  },

  async getHistorique(_dossierId: string): Promise<HistoriqueOut[]> {
    return []
  },

  // Statut transition
  async transition(id: string, statut: StatutDossier, commentaire?: string): Promise<DossierOut> {
    const { data } = await api.patch<DossierOut>(`/dossiers/${id}/statut`, { statut, commentaire })
    return data
  },

  // Assignation — utilisateurs assignables (Notaire Principal + Clerc)
  async getAssignables(_dossierId: string): Promise<{ id: string; full_name: string; role: string }[]> {
    const { data } = await api.get<{ id: string; full_name: string; role: string }[]>('/dossiers/assignables')
    return data
  },

  // Assigner le dossier à un utilisateur
  async assign(dossierId: string, userId: string): Promise<DossierOut> {
    const { data } = await api.patch<DossierOut>(`/dossiers/${dossierId}/assign`, null, {
      params: { user_id: userId },
    })
    return data
  },
}
