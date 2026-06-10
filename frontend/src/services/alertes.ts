import api from './api'

export interface AlerteOut {
  id: string
  dossier_id: string | null
  dossier_reference: string | null
  dossier_statut: string | null
  type_alerte: string
  niveau: string
  description: string
  assigned_to_rc: string | null
  assigned_to_dirigeant: string | null
  statut: 'OUVERTE' | 'TRAITEE'
  justification_traitement: string | null
  traitee_par: string | null
  traitee_at: string | null
  created_at: string
}

export interface AlerteListResponse {
  items: AlerteOut[]
  total: number
  page: number
  page_size: number
}

export interface PendingWrk09Item {
  dossier_id: string
  dossier_reference: string
  type_dossier: string
  niveau_risque: string | null
  created_at: string
  alerte_id: string | null
}

export interface AutorisationOut {
  id: string
  dossier_id: string
  dirigeant_id: string
  decision: 'AUTORISE' | 'REFUSE'
  justification: string | null
  created_at: string
}

export interface AlerteFilters {
  page?: number
  page_size?: number
  statut?: string
  niveau?: string
  type_alerte?: string
  dossier_id?: string
  dossier_statut?: string
}

export const alertesService = {
  async list(filters: AlerteFilters = {}): Promise<AlerteListResponse> {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== undefined && v !== ''),
    )
    const { data } = await api.get<AlerteListResponse | AlerteOut[]>('/alertes', { params })
    if (Array.isArray(data)) {
      return { items: data, total: data.length, page: 1, page_size: data.length }
    }
    return data
  },

  async get(id: string): Promise<AlerteOut> {
    const { data } = await api.get<AlerteOut>(`/alertes/${id}`)
    return data
  },

  async traiter(id: string, justification: string): Promise<AlerteOut> {
    const { data } = await api.post<AlerteOut>(`/alertes/${id}/traiter`, { justification })
    return data
  },

  async bloquerDossier(alerteId: string): Promise<{ status: string; dossier_id: string }> {
    const { data } = await api.post(`/alertes/${alerteId}/bloquer-dossier`)
    return data
  },

  async debloquerDossier(alerteId: string): Promise<{ status: string; dossier_id: string }> {
    const { data } = await api.post(`/alertes/${alerteId}/debloquer-dossier`)
    return data
  },

  async pendingWrk09(): Promise<PendingWrk09Item[]> {
    const { data } = await api.get<PendingWrk09Item[]>('/autorisations/wrk09/pending')
    return data
  },

  async signalerInterne(description: string, dossierReference?: string): Promise<AlerteOut> {
    const { data } = await api.post<AlerteOut>('/alertes/signaler', {
      description,
      dossier_reference: dossierReference || null,
    })
    return data
  },

  async mesSignalements(): Promise<AlerteOut[]> {
    const { data } = await api.get<AlerteOut[]>('/alertes/mes-signalements')
    return data
  },

  async createAutorisation(
    dossierId: string,
    decision: 'AUTORISE' | 'REFUSE',
    justification?: string,
  ): Promise<AutorisationOut> {
    const { data } = await api.post<AutorisationOut>(`/dossiers/${dossierId}/autorisation`, {
      decision,
      justification,
    })
    return data
  },
}
