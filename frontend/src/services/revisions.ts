import api from './api'

export interface RevisionInfo {
  has_revision: boolean
  dossier_id: string
  prochaine_revision_at?: string
  frequence_mois?: number
  motif?: string
  alerte_j30_envoyee?: boolean
  escalade_jalon?: number
  revision_initiee_at?: string | null
}

export interface ListeSanctions {
  id: string
  nom: string
  type_liste: 'GIABA' | 'BCEAO' | 'OFAC' | 'UE_CSDNU' | 'AUTRE'
  total_entrees: number
  activated_at: string
  age_jours: number
  is_stale: boolean
}

export interface SanctionsListResponse {
  items: ListeSanctions[]
  total: number
}

export interface CriblageResult {
  liste: string
  type_liste: string
  score: number
  statut: 'match' | 'no_match'
  niveau: 'match' | 'warning' | 'clear' | 'no_match'
  ddn_detail: 'ddn_confirmee' | 'annee_seule' | 'homonymie_confirmee' | 'ddn_absente_liste' | null
  nom_correspondant: string | null
}

export interface CriblageResponse {
  nom_crible: string
  has_match: boolean
  results: CriblageResult[]
}

export interface RevisionListItem {
  id: string
  dossier_id: string
  dossier_reference: string
  client_nom: string
  niveau_risque: string
  frequence: string
  prochaine_revision: string
  statut: string
  jalon_actif: number | null
}

export interface RevisionListResponse {
  items: RevisionListItem[]
  total: number
}

export const revisionsService = {
  async list(params?: { statut?: string; niveau_risque?: string }): Promise<RevisionListResponse> {
    const { data } = await api.get<RevisionListResponse | RevisionListItem[]>('/revisions', { params })
    if (Array.isArray(data)) {
      return { items: data, total: data.length }
    }
    return data
  },

  async initier(dossierId: string, _opts?: { note?: string }): Promise<{ status: string }> {
    const { data } = await api.post(`/dossiers/${dossierId}/revision/initier`)
    return data
  },

  async getRevision(dossierId: string): Promise<RevisionInfo> {
    const { data } = await api.get<RevisionInfo>(`/dossiers/${dossierId}/revision`)
    return data
  },

  async initierRevision(dossierId: string): Promise<{ status: string }> {
    const { data } = await api.post(`/dossiers/${dossierId}/revision/initier`)
    return data
  },

  async runSchedulerCheck(): Promise<{ j30_alerts_sent: number; escalades_processed: number; sanctions_fresh: boolean }> {
    const { data } = await api.post('/scheduler/revisions/check')
    return data
  },

  async listSanctions(): Promise<SanctionsListResponse> {
    const { data } = await api.get<SanctionsListResponse>('/sanctions')
    return data
  },

  async uploadSanctions(nom: string, typeListe: string, file: File): Promise<ListeSanctions & { warning?: string }> {
    const form = new FormData()
    form.append('nom', nom)
    form.append('type_liste', typeListe)
    form.append('file', file)
    const { data } = await api.post('/sanctions/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async cribler(
    nom: string,
    opts?: { dateNaissance?: string; lieuNaissance?: string; dossierId?: string; seuil?: number },
  ): Promise<CriblageResponse> {
    const { data } = await api.post<CriblageResponse>('/sanctions/cribler', {
      nom,
      date_naissance: opts?.dateNaissance || null,
      lieu_naissance: opts?.lieuNaissance || null,
      dossier_id: opts?.dossierId || null,
      seuil: opts?.seuil ?? 85,
    })
    return data
  },

  async deactivateSanctions(id: string): Promise<void> {
    await api.patch(`/sanctions/${id}/deactivate`)
  },
}
