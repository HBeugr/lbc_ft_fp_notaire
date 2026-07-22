/**
 * Lecture des réponses de blocage de cabinet (portier multi-tenant).
 *
 * Le backend signale un cabinet non utilisable de deux façons selon la couche
 * qui répond :
 *   - `app/routers/auth.py` imbrique le code : `{ detail: { code, message } }` ;
 *   - `app/core/tenant_middleware.py` le place à la racine : `{ code, detail }`.
 *
 * Ce module normalise les deux formes, pour qu'un même blocage produise toujours
 * le même statut de cabinet côté interface, quelle que soit la route appelée.
 */
import type { TenantStatut } from '@/stores/auth'

/** Codes de blocage émis par le backend, et statut de cabinet correspondant. */
const CODE_TO_STATUT: Record<string, TenantStatut> = {
  tenant_suspended: 'suspendu',
  tenant_configuration: 'configuration',
  tenant_archived: 'archive',
}

export interface TenantBlock {
  code: string
  statut: TenantStatut
  message: string | null
}

/** Extrait le code métier, qu'il soit imbriqué dans `detail` ou à la racine. */
export function readCode(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null
  const root = data as { code?: unknown; detail?: unknown }
  if (typeof root.code === 'string') return root.code
  const detail = root.detail
  if (detail && typeof detail === 'object' && 'code' in detail) {
    const c = (detail as { code: unknown }).code
    if (typeof c === 'string') return c
  }
  return null
}

/** Extrait le message destiné à l'utilisateur (motif de régularisation). */
export function readMessage(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null
  const root = data as { message?: unknown; detail?: unknown }
  if (typeof root.message === 'string') return root.message
  const detail = root.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    const d = detail as { message?: unknown; detail?: unknown }
    if (typeof d.message === 'string') return d.message
    if (typeof d.detail === 'string') return d.detail
  }
  return null
}

/**
 * Reconnaît un blocage de cabinet dans une réponse d'erreur.
 * Retourne `null` pour toute autre erreur (401 de session, 402 de quota de
 * sièges…), qui doit suivre son traitement habituel.
 */
export function readTenantBlock(status: number | undefined, data: unknown): TenantBlock | null {
  if (status !== 402 && status !== 403) return null
  const code = readCode(data)
  if (!code) return null
  const statut = CODE_TO_STATUT[code]
  if (!statut) return null
  return { code, statut, message: readMessage(data) }
}
