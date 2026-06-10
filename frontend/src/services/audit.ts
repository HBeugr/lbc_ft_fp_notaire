import api from './api'

export interface AuditLogEntry {
  id: string
  user_id: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  ip: string | null
  detail: string | null
  timestamp_utc: string
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  total: number
}

export interface AuditLogFilters {
  page?: number
  page_size?: number
  action?: string
  entity_type?: string
  entity_id?: string
  user_id?: string
}

export const auditService = {
  async list(filters: AuditLogFilters = {}): Promise<AuditLogListResponse> {
    const params: Record<string, string | number> = {}
    if (filters.page)        params.page        = filters.page
    if (filters.page_size)   params.page_size   = filters.page_size
    if (filters.action)      params.action      = filters.action
    if (filters.entity_type) params.entity_type = filters.entity_type
    if (filters.entity_id)   params.entity_id   = filters.entity_id
    if (filters.user_id)     params.user_id     = filters.user_id
    const { data } = await api.get<AuditLogListResponse>('/audit/logs', { params })
    return data
  },
}
