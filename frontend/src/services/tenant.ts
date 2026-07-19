import api from './api'
import type { TenantMe } from '@/stores/auth'

/** Consommation du quota de sièges du cabinet (admin / notaire principal). */
export interface TenantQuota {
  tenant_id: string
  utilisateurs_actifs: number
  utilisateurs_total: number
  quota_utilisateurs: number
  dossiers_total: number
}

/** Règles de format du logo, servies par l'API pour ne pas les figer dans l'interface. */
export interface LogoContraintes {
  formats: string[]
  taille_max_octets: number
  dimension_min_px: number
  dimension_max_px: number
  ratio_max: number
}

/** Résultat d'un envoi de logo. */
export interface LogoOut {
  logo_updated_at: string | null
  largeur: number
  hauteur: number
  content_type: string
}

export const tenantService = {
  async me(): Promise<TenantMe> {
    const { data } = await api.get<TenantMe>('/tenant/me')
    return data
  },

  async quota(): Promise<TenantQuota> {
    const { data } = await api.get<TenantQuota>('/tenant/quota')
    return data
  },

  async logoContraintes(): Promise<LogoContraintes> {
    const { data } = await api.get<LogoContraintes>('/tenant/logo/contraintes')
    return data
  },

  /**
   * Récupère l'image du logo.
   *
   * L'endpoint exige l'en-tête `Authorization` : une balise `<img src="/api/…">`
   * ne l'enverrait pas. On passe donc par l'instance axios et l'appelant convertit
   * le blob en URL d'objet.
   *
   * `version` (horodatage du logo) casse le cache navigateur (`max-age=300`) dès
   * qu'un nouveau logo est posé.
   */
  async logoBlob(version?: string | null): Promise<Blob> {
    const { data } = await api.get('/tenant/logo', {
      responseType: 'blob',
      params: version ? { v: version } : undefined,
    })
    return data as Blob
  },

  async uploadLogo(file: File): Promise<LogoOut> {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.put<LogoOut>('/tenant/logo', form)
    return data
  },

  async deleteLogo(): Promise<void> {
    await api.delete('/tenant/logo')
  },
}
