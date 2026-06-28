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
  pourcentage_droits_vote?: number | null
  entite_intermediaire_nom?: string | null
  entite_intermediaire_pct?: number | null
  pays_residence: string | null
  date_naissance: string | null
  lieu_naissance?: string | null
  nationalite: string | null
  lien_avec_client?: string | null
  entreprise_cotee?: boolean
  registre_be_demande?: string | null
  registre_be_resultat?: string | null
  registre_be_note?: string | null
  filtrage_sfc_resultat?: string | null
  filtrage_sfc_listes?: Record<string, unknown> | null
  filtrage_sfc_justification?: string | null
  statut_validation?: string
  commentaire_validation?: string | null
}

export interface KycActData {
  id?: string
  raison_sociale_nom: string
  type_personne?: string | null
  cni_passeport: string | null
  pourcentage: number
  pays_residence: string | null
  ordre: number
}

export interface KycPPEData {
  id?: string
  statut_ppe: string
  fonctions: string | null
  pays_concerne: string | null
  verification_giaba: boolean
  verification_ofac: boolean
  verification_ue: boolean
  ras: boolean
  resultat_presse?: string | null
  details_presse?: string | null
  niveau_exposition?: string | null
  mesures_proposees?: string | null
  statut_validation?: string
  commentaire_validation?: string | null
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
  sexe?: string | null
  statut_matrimonial?: string | null
  type_piece?: string | null
  numero_piece?: string | null
  pays_emetteur_piece?: string | null
  date_emission_piece?: string | null
  date_expiration_piece?: string | null
  mode_verification_piece?: string | null
  adresse_geo?: string | null
  adresse_postale?: string | null
  telephone?: string | null
  whatsapp?: string | null
  email?: string | null
  non_resident?: boolean
  pays_residence?: string | null
  ville_residence?: string | null
  numero_contribuable?: string | null
  profession?: string | null
  profession_5_ans?: string | null
  employeur?: string | null
  secteur_activite?: string | null
  retraite?: boolean
  tranche_revenus?: string | null
  note?: string | null
  mandataire?: MandataireData | null
  est_ppe?: boolean
  est_compte_tiers?: boolean
  ppe_detail?: string | null
  objet_relation?: string | null
  operations_cochees?: OperationsCochees | null
  description_operation?: string | null
  origine_fonds?: OrigineFonds | null
  anciennete_pro?: string | null
  date_signature?: string | null
  photo_path?: string | null
  beneficiaires_effectifs?: KycBEData[]
  ppe_declarations?: KycPPEData[]
}

export interface KycPMData {
  id?: string
  dossier_id?: string
  relation_type?: string
  denomination_sociale?: string
  nom_commercial?: string | null
  forme_juridique?: string | null
  pays_constitution?: string | null
  nom_representant_legal?: string | null
  numero_rccm?: string | null
  date_emission_rccm?: string | null
  date_expiration_rccm?: string | null
  numero_contribuable?: string | null
  objet_social?: string | null
  libelle_activite?: string | null
  ca_annuel?: number | null
  effectif?: number | null
  pays_operations?: string | null
  volume_transactions?: string | null
  representant_statut_ppe?: boolean
  adresse?: string | null
  telephone?: string | null
  whatsapp?: string | null
  email?: string | null
  mandataire?: MandataireData | null
  est_compte_tiers?: boolean
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
  ppe_declarations?: KycPPEData[]
}

export type ModePaiement = 'virement' | 'cheque' | 'especes' | 'mix' | 'paiement_tiers'

export interface DossierOut {
  id: string
  reference: string
  type_client: string
  type_operation: string
  type_operation_detail: string | null
  montant_transaction: number | null
  montant_tranche?: 'moins_15m' | 'plus_15m' | null
  mode_paiement: string | null
  surveillance_espece?: boolean
  nb_parties: number
  statut: string
  assigned_to: string | null
  assigned_to_name?: string | null
  created_by: string
  score_base: number | null
  classification: string | null
  trigger_actif: string | null
  force_par_trigger: boolean
  created_at?: string | null
  updated_at?: string | null
  kyc_pp?: KycPPData | null
  kyc_pm?: KycPMData | null
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

export interface DocumentOut {
  id: string
  dossier_id: string
  nom_fichier: string
  type_document: string
  taille_octets: number
  created_at: string
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
  async list(params: { statut?: string; classification?: string; reference?: string; search?: string; mine?: boolean; page?: number; page_size?: number } = {}): Promise<DossierListResponse> {
    const { data } = await api.get<DossierOut[]>('/dossiers', { params })
    if (Array.isArray(data)) return { items: data, total: data.length }
    return data as unknown as DossierListResponse
  },

  get: (id: string) => api.get<DossierOut>(`/dossiers/${id}`).then(r => r.data),

  create: (payload: { type_client: TypeClient; type_operation: TypeOperation; type_operation_detail?: string }) =>
    api.post<DossierOut>('/dossiers', payload).then(r => r.data),

  async saveTransaction(dossierId: string, payload: {
    montant_tranche?: 'moins_15m' | 'plus_15m'
    montant_transaction?: number
    mode_paiement?: 'especes' | 'cheque' | 'virement' | 'mix' | 'paiement_tiers' | 'autre'
  }): Promise<DossierOut> {
    const { data } = await api.patch<DossierOut>(`/dossiers/${dossierId}/transaction`, payload)
    return data
  },

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

  // KYC BE — API unifiée selon le contexte client (PP ou PM)
  async createKycBE(dossierId: string, payload: KycBEData, clientType: 'PP' | 'PM' = 'PP'): Promise<KycBEData> {
    const seg = clientType === 'PM' ? 'pm' : 'pp'
    const { data } = await api.post<KycBEData>(`/dossiers/${dossierId}/kyc/${seg}/be`, payload)
    return data
  },
  async listKycBE(dossierId: string, clientType: 'PP' | 'PM' = 'PP'): Promise<KycBEData[]> {
    try {
      const kyc = clientType === 'PM'
        ? await api.get<KycPMData>(`/dossiers/${dossierId}/kyc/pm`).then(r => r.data)
        : await api.get<KycPPData>(`/dossiers/${dossierId}/kyc/pp`).then(r => r.data)
      return (kyc.beneficiaires_effectifs ?? []) as KycBEData[]
    } catch {
      return []
    }
  },
  async updateKycBE(dossierId: string, beId: string, payload: Partial<KycBEData>, clientType: 'PP' | 'PM' = 'PP'): Promise<KycBEData> {
    const seg = clientType === 'PM' ? 'pm' : 'pp'
    const { data } = await api.patch<KycBEData>(`/dossiers/${dossierId}/kyc/${seg}/be/${beId}`, payload)
    return data
  },
  deleteKycBE(dossierId: string, beId: string, clientType: 'PP' | 'PM' = 'PP') {
    const seg = clientType === 'PM' ? 'pm' : 'pp'
    return api.delete(`/dossiers/${dossierId}/kyc/${seg}/be/${beId}`)
  },

  // KYC PPE — API unifiée selon le contexte client (PP ou PM)
  async createKycPPE(dossierId: string, payload: Partial<KycPPEData>, clientType: 'PP' | 'PM' = 'PP'): Promise<KycPPEData> {
    const seg = clientType === 'PM' ? 'pm' : 'pp'
    const { data } = await api.post<KycPPEData>(`/dossiers/${dossierId}/kyc/${seg}/ppe`, payload)
    return data
  },
  async listKycPPE(dossierId: string, clientType: 'PP' | 'PM' = 'PP'): Promise<KycPPEData[]> {
    try {
      const kyc = clientType === 'PM'
        ? await api.get<KycPMData>(`/dossiers/${dossierId}/kyc/pm`).then(r => r.data)
        : await api.get<KycPPData>(`/dossiers/${dossierId}/kyc/pp`).then(r => r.data)
      return (kyc.ppe_declarations ?? []) as KycPPEData[]
    } catch {
      return []
    }
  },
  async updateKycPPE(dossierId: string, ppeId: string, payload: Partial<KycPPEData>, clientType: 'PP' | 'PM' = 'PP'): Promise<KycPPEData> {
    const seg = clientType === 'PM' ? 'pm' : 'pp'
    const { data } = await api.patch<KycPPEData>(`/dossiers/${dossierId}/kyc/${seg}/ppe/${ppeId}`, payload)
    return data
  },
  deleteKycPPE(dossierId: string, ppeId: string, clientType: 'PP' | 'PM' = 'PP') {
    const seg = clientType === 'PM' ? 'pm' : 'pp'
    return api.delete(`/dossiers/${dossierId}/kyc/${seg}/ppe/${ppeId}`)
  },

  // Scoring / Matrice de risque
  getScoringPrefill: (dossierId: string) =>
    api.get<ScoringPrefill>(`/dossiers/${dossierId}/scoring/prefill`).then(r => r.data),

  calculateScore: (dossierId: string, payload: ScoreCalcPayload) =>
    api.post<ScoreResult>(`/dossiers/${dossierId}/scoring/calculate`, payload).then(r => r.data),

  // Documents (stockage chiffré, accès API uniquement)
  async listDocuments(dossierId: string): Promise<DocumentOut[]> {
    const { data } = await api.get<DocumentOut[]>(`/dossiers/${dossierId}/documents`)
    return data
  },

  async uploadDocument(dossierId: string, file: File, typeDocument: string): Promise<DocumentOut> {
    const form = new FormData()
    form.append('file', file)
    form.append('type_document', typeDocument)
    const { data } = await api.post<DocumentOut>(`/dossiers/${dossierId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async downloadDocument(docId: string): Promise<Blob> {
    const { data } = await api.get(`/documents/${docId}/download`, { responseType: 'blob' })
    return data as Blob
  },

  async deleteDocument(docId: string): Promise<void> {
    await api.delete(`/documents/${docId}`)
  },

  // Déclenchement manuel d'un trigger (T5 refus documentaire / T6 BE non identifiable)
  async triggerManuel(dossierId: string, trigger: 'T5' | 'T6', commentaire: string): Promise<DossierOut> {
    const { data } = await api.post<DossierOut>(`/dossiers/${dossierId}/trigger-manuel`, { trigger, commentaire })
    return data
  },

  // Commentaires
  async listCommentaires(dossierId: string): Promise<CommentaireOut[]> {
    const { data } = await api.get<CommentaireOut[]>(`/dossiers/${dossierId}/commentaires`)
    return data
  },

  async addCommentaire(dossierId: string, contenu: string): Promise<CommentaireOut> {
    const { data } = await api.post<CommentaireOut>(`/dossiers/${dossierId}/commentaires`, { contenu })
    return data
  },

  async getHistorique(dossierId: string): Promise<HistoriqueOut[]> {
    const { data } = await api.get<HistoriqueOut[]>(`/dossiers/${dossierId}/historique`)
    return data
  },

  // Alertes liées à un dossier (pour la fiche KYC)
  async getAlertes(dossierId: string): Promise<Array<{
    id: string; type_alerte: string; niveau: string; statut: string;
    description: string; resolution_note: string | null; created_at: string | null
  }>> {
    const { data } = await api.get(`/dossiers/${dossierId}/alertes`)
    return data
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

  // Pré-vérification sanctions temps réel pendant la saisie KYC (sans audit ni T3)
  async checkSanctionsPreScreen(
    nom: string,
    prenoms: string,
    dateNaissance?: string,
    nationalite?: string,
    lieuNaissance?: string,
  ): Promise<{ level: 'blocked' | 'warning' | 'clear' | 'no_lists'; score: number; liste: string | null; reason: string | null }> {
    const { data } = await api.post('/kyc/screening/pre-check', {
      nom,
      prenoms,
      date_naissance: dateNaissance || null,
      lieu_naissance: lieuNaissance || null,
      nationalite: nationalite || null,
    })
    return data
  },
}
