import { superAdminApi } from './api'
import type { LogoContraintes, LogoOut } from './tenant'

export type { LogoContraintes, LogoOut }

export type TenantStatut = 'configuration' | 'production' | 'suspendu' | 'archive'

export interface SuperAdminOut {
  id: string
  email: string
  first_name: string
  last_name: string
  must_change_password: boolean
  totp_enabled: boolean
}

export interface SuperAdminLoginResponse {
  access_token: string
  token_type: string
  super_admin: SuperAdminOut
  /** Vrai tant que le code TOTP n'a pas été fourni : le jeton n'ouvre alors que /auth/totp/verify*. */
  totp_pending: boolean
}

export interface SuperAdminTotpSetup {
  provisioning_uri: string
}

/** Codes de secours — retournés une seule fois, à l'activation. */
export interface SuperAdminTotpActivate {
  backup_codes: string[]
}

export interface SuperAdminTotpVerify {
  access_token: string
  token_type: string
  super_admin: SuperAdminOut
}

export interface TenantOut {
  id: string
  slug: string
  nom_cabinet: string
  statut: TenantStatut
  pays: string
  contact_email: string
  contact_telephone: string | null
  adresse: string | null
  numero_agrement: string | null
  totp_required: boolean
  max_users: number
  motif_suspension: string | null
  created_at: string
  activated_at: string | null
  suspended_at: string | null
  /** Horodatage du dernier logo posé — sert de « cache-buster » à l'affichage. */
  logo_updated_at: string | null
}

export interface TenantCreatePayload {
  nom_cabinet: string
  contact_email: string
  admin_email: string
  admin_first_name: string
  admin_last_name: string
  slug?: string
  numero_agrement?: string
  pays?: string
  contact_telephone?: string
  adresse?: string
  totp_required?: boolean
  max_users?: number
}

/** Le mot de passe temporaire n'est renvoyé qu'ici, une seule fois. */
export interface TenantCreateResponse {
  tenant: TenantOut
  admin_email: string
  admin_temp_password: string
}

/** Champs modifiables après création — slug, schéma et sel de chiffrement sont figés. */
export interface TenantUpdatePayload {
  nom_cabinet?: string
  contact_email?: string
  contact_telephone?: string | null
  adresse?: string | null
  numero_agrement?: string | null
  pays?: string
  totp_required?: boolean
  max_users?: number
}

/** Même contrat qu'à la création : le mot de passe n'est lisible qu'ici. */
export interface TenantAdminReset {
  admin_email: string
  admin_temp_password: string
}

export interface TenantMetrics {
  tenant_id: string
  utilisateurs_actifs: number
  utilisateurs_total: number
  quota_utilisateurs: number
  dossiers_total: number
}

export interface PlatformMetrics {
  cabinets_total: number
  cabinets_par_statut: Partial<Record<TenantStatut, number>>
  utilisateurs_total: number
  utilisateurs_actifs: number
  dossiers_total: number
  /** Cabinets dont le comptage a échoué : le total affiché est alors partiel. */
  cabinets_injoignables: string[]
  cabinets_recents: TenantOut[]
}

export interface ExploitationAuditEntry {
  id: string
  tenant_id: string | null
  super_admin_id: string | null
  action: string
  detail: string | null
  created_at: string
}

export interface MigrationResult {
  resultats: Record<string, string>
}

export const superAdminService = {
  async login(email: string, password: string): Promise<SuperAdminLoginResponse> {
    const { data } = await superAdminApi.post<SuperAdminLoginResponse>('/auth/login', { email, password })
    return data
  },

  /** Révoque le jeton côté serveur. Tolère l'échec : la session locale part de toute façon. */
  async logout(): Promise<void> {
    await superAdminApi.post('/auth/logout')
  },

  async me(): Promise<SuperAdminOut> {
    const { data } = await superAdminApi.get<SuperAdminOut>('/auth/me')
    return data
  },

  // ── 2FA du compte d'exploitation ─────────────────────────────────────

  async totpSetup(): Promise<SuperAdminTotpSetup> {
    const { data } = await superAdminApi.post<SuperAdminTotpSetup>('/auth/totp/setup')
    return data
  },

  async totpActivate(code: string): Promise<SuperAdminTotpActivate> {
    const { data } = await superAdminApi.post<SuperAdminTotpActivate>('/auth/totp/activate', { code })
    return data
  },

  async totpDisable(code: string): Promise<SuperAdminOut> {
    const { data } = await superAdminApi.post<SuperAdminOut>('/auth/totp/disable', { code })
    return data
  },

  async totpVerify(code: string): Promise<SuperAdminTotpVerify> {
    const { data } = await superAdminApi.post<SuperAdminTotpVerify>('/auth/totp/verify', { code })
    return data
  },

  async totpVerifyBackup(code: string): Promise<SuperAdminTotpVerify> {
    const { data } = await superAdminApi.post<SuperAdminTotpVerify>('/auth/totp/verify-backup', { code })
    return data
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<SuperAdminOut> {
    const { data } = await superAdminApi.patch<SuperAdminOut>('/auth/password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    return data
  },

  async listTenants(): Promise<TenantOut[]> {
    const { data } = await superAdminApi.get<TenantOut[]>('/tenants')
    return data
  },

  async getTenant(id: string): Promise<TenantOut> {
    const { data } = await superAdminApi.get<TenantOut>(`/tenants/${id}`)
    return data
  },

  async createTenant(payload: TenantCreatePayload): Promise<TenantCreateResponse> {
    const { data } = await superAdminApi.post<TenantCreateResponse>('/tenants', payload)
    return data
  },

  async updateTenant(id: string, payload: TenantUpdatePayload): Promise<TenantOut> {
    const { data } = await superAdminApi.patch<TenantOut>(`/tenants/${id}`, payload)
    return data
  },

  async resetTenantAdminPassword(id: string): Promise<TenantAdminReset> {
    const { data } = await superAdminApi.post<TenantAdminReset>(`/tenants/${id}/admin-password-reset`)
    return data
  },

  async activateTenant(id: string): Promise<TenantOut> {
    const { data } = await superAdminApi.post<TenantOut>(`/tenants/${id}/activate`)
    return data
  },

  async suspendTenant(id: string, motif?: string): Promise<TenantOut> {
    const { data } = await superAdminApi.post<TenantOut>(`/tenants/${id}/suspend`, { motif })
    return data
  },

  async archiveTenant(id: string, motif?: string): Promise<TenantOut> {
    const { data } = await superAdminApi.post<TenantOut>(`/tenants/${id}/archive`, { motif })
    return data
  },

  async tenantMetrics(id: string): Promise<TenantMetrics> {
    const { data } = await superAdminApi.get<TenantMetrics>(`/tenants/${id}/metrics`)
    return data
  },

  async platformMetrics(): Promise<PlatformMetrics> {
    const { data } = await superAdminApi.get<PlatformMetrics>('/metrics')
    return data
  },

  async migrateAll(): Promise<MigrationResult> {
    const { data } = await superAdminApi.post<MigrationResult>('/tenants/migrate')
    return data
  },

  async audit(limit = 100): Promise<ExploitationAuditEntry[]> {
    const { data } = await superAdminApi.get<ExploitationAuditEntry[]>('/audit', { params: { limit } })
    return data
  },

  // ── Logo d'un cabinet ────────────────────────────────────────────────
  // Mêmes formes que côté cabinet, avec le jeton de la console : les deux
  // populations sont distinctes, chacune passe par son instance axios.

  async logoContraintes(): Promise<LogoContraintes> {
    const { data } = await superAdminApi.get<LogoContraintes>('/logo/contraintes')
    return data
  },

  /** L'endpoint exige `Authorization` : on récupère un blob, jamais une URL d'image directe. */
  async logoBlob(tenantId: string, version?: string | null): Promise<Blob> {
    const { data } = await superAdminApi.get(`/tenants/${tenantId}/logo`, {
      responseType: 'blob',
      params: version ? { v: version } : undefined,
    })
    return data as Blob
  },

  async uploadLogo(tenantId: string, file: File): Promise<LogoOut> {
    const form = new FormData()
    form.append('file', file)
    const { data } = await superAdminApi.put<LogoOut>(`/tenants/${tenantId}/logo`, form)
    return data
  },

  async deleteLogo(tenantId: string): Promise<void> {
    await superAdminApi.delete(`/tenants/${tenantId}/logo`)
  },
}

export const TENANT_STATUT_LABELS: Record<TenantStatut, string> = {
  configuration: 'En configuration',
  production: 'En production',
  suspendu: 'Suspendu',
  archive: 'Archivé',
}
