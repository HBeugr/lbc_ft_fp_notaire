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
  statut: 'OUVERTE' | 'EN_COURS' | 'TRAITEE' | 'IGNOREE'
  prise_en_charge_par: string | null
  prise_en_charge_at: string | null
  justification_traitement: string | null
  traitee_par: string | null
  traitee_at: string | null
  created_at: string
}

export interface TimelineEvent {
  label: string
  at: string | null
  par: string | null
  note?: string | null
}

export interface AlerteTimeline {
  alerte_id: string
  statut: string
  type_alerte: string
  events: TimelineEvent[]
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
  categorie?: 'conformite' | 'notification' | 'historique'
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

  async traiter(id: string, justification: string, actionDossier?: string): Promise<AlerteOut> {
    const { data } = await api.post<AlerteOut>(`/alertes/${id}/traiter`, {
      justification,
      action_dossier: actionDossier || null,
    })
    return data
  },

  async prendre(id: string): Promise<AlerteOut> {
    const { data } = await api.post<AlerteOut>(`/alertes/${id}/prendre`)
    return data
  },

  async timeline(id: string): Promise<AlerteTimeline> {
    const { data } = await api.get<AlerteTimeline>(`/alertes/${id}/timeline`)
    return data
  },

  async exportAlertes(format: 'excel' | 'pdf', filters: AlerteFilters = {}): Promise<Blob> {
    const params = Object.fromEntries(
      Object.entries({ format, ...filters }).filter(([, v]) => v !== undefined && v !== ''),
    )
    const { data } = await api.get('/alertes/export', { params, responseType: 'blob' })
    return data as Blob
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
