import api from './api'

export interface RegistreInfo {
  id: string
  label: string
  confidential: boolean
}

export interface RegistreEntry {
  id: string
  timestamp_utc: string
  action: string
  user_id: string
  entity_type: string
  entity_id: string
  ip: string
  detail: Record<string, unknown> | null
}

export interface RegistrePage {
  registre_id: string
  label: string
  total: number
  page: number
  page_size: number
  items: RegistreEntry[]
}

export const registresService = {
  async list(): Promise<{ registres: RegistreInfo[] }> {
    const { data } = await api.get('/registres')
    return data
  },

  async getPage(registreId: string, page = 1, pageSize = 50): Promise<RegistrePage> {
    const { data } = await api.get<RegistrePage>(`/registres/${registreId}`, {
      params: { page, page_size: pageSize },
    })
    return data
  },

  async exportBlob(registreId: string, format: 'pdf' | 'excel'): Promise<Blob> {
    const { data } = await api.get(`/registres/${registreId}/export`, {
      params: { format },
      responseType: 'blob',
    })
    return data
  },

  async generateReport(reportType: 'conformite' | 'audit' | 'mandats' | 'client'): Promise<Blob> {
    const { data } = await api.post(`/rapports/${reportType}`, {}, { responseType: 'blob' })
    return data
  },
}
