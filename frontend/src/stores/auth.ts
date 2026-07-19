import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { readTenantBlock, type TenantBlock } from '@/services/tenantBlock'

export interface UserInfo {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
  totp_enabled: boolean
  requires_2fa: boolean
  must_change_password?: boolean
}

export type TenantStatut = 'configuration' | 'production' | 'suspendu' | 'archive'

/** Bloc `tenant` renvoyé par POST /api/auth/login (SaaS multi-tenant). */
export interface TenantInfo {
  id: string
  slug: string
  nom: string
  statut: TenantStatut
  /**
   * Horodatage du logo du cabinet.
   *
   * Trois états distincts, à ne pas confondre :
   *   - `undefined` : inconnu (le bloc `tenant` du login ne le porte pas) ;
   *   - `null`      : aucun logo défini — l'interface garde l'icône générique ;
   *   - chaîne ISO  : logo présent, valeur utilisée comme « cache-buster ».
   */
  logo_updated_at?: string | null
}

/** Réponse de GET /api/tenant/me — plus riche que le bloc du login. */
export interface TenantMe {
  id: string
  slug: string
  nom_cabinet: string
  statut: TenantStatut
  totp_required: boolean
  max_users: number
  /** Code pays ISO du cabinet (ex. « CI ») — toujours renseigné côté backend. */
  pays: string
  /** N° d'agrément à la Chambre des Notaires — facultatif tant qu'il n'est pas saisi. */
  numero_agrement: string | null
  /** Horodatage du dernier logo posé — `null` quand le cabinet n'en a pas. */
  logo_updated_at: string | null
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<UserInfo | null>(null)
  const tenant = ref<TenantInfo | null>(null)
  // Motif de suspension éventuel remonté par le backend (402/403) — affiché sur /compte-suspendu.
  const tenantMessage = ref<string | null>(null)

  let _bootstrapResolve: (() => void) | null = null
  const bootstrapReady = new Promise<void>((resolve) => { _bootstrapResolve = resolve })

  function resolveBootstrap() {
    _bootstrapResolve?.()
  }

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const role = computed(() => user.value?.role ?? null)
  const mustChangePassword = computed(() => !!user.value?.must_change_password)

  const isSupervisor = computed(() =>
    ['admin', 'notaire_principal', 'responsable_conformite'].includes(user.value?.role ?? '')
  )

  const tenantName = computed(() => tenant.value?.nom ?? null)
  /** `undefined` tant que l'information n'a pas été chargée (cf. `TenantInfo`). */
  const tenantLogoUpdatedAt = computed<string | null | undefined>(() =>
    tenant.value ? tenant.value.logo_updated_at : undefined
  )
  const tenantStatut = computed<TenantStatut | null>(() => tenant.value?.statut ?? null)
  // Seul le statut `production` autorise l'usage normal de la plateforme.
  const tenantActive = computed(() => tenant.value?.statut === 'production')

  /**
   * Session identifiée dont le cabinet est bloqué (suspendu, en configuration,
   * archivé). Volontairement indépendant de `accessToken` : l'API refuse de
   * renouveler le jeton d'un cabinet bloqué, or l'utilisateur doit malgré tout
   * accéder à la page d'explication au lieu d'être renvoyé sur le formulaire de
   * connexion sans motif.
   */
  const tenantBlocked = computed(() => !!user.value && !!tenant.value && !tenantActive.value)

  function setToken(token: string) {
    accessToken.value = token
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }

  function setUser(u: UserInfo) {
    user.value = u
  }

  /**
   * Fixe le cabinet courant. Si l'identifiant diffère de celui persisté, on purge
   * le state hérité : sur un poste partagé, un utilisateur d'un autre cabinet ne
   * doit jamais voir les restes du précédent (nom du cabinet, profil, jetons).
   */
  function setTenant(t: TenantInfo | null) {
    const previousId = tenant.value?.id
    if (t && previousId && previousId !== t.id) {
      purgePersistedState()
    }
    tenant.value = t
    if (t && t.statut === 'production') {
      tenantMessage.value = null
    }
  }

  function setTenantMessage(msg: string | null) {
    tenantMessage.value = msg
  }

  /** Applique la réponse de GET /api/tenant/me au bloc tenant du store. */
  function setTenantFromMe(me: TenantMe) {
    setTenant({
      id: me.id,
      slug: me.slug,
      nom: me.nom_cabinet,
      statut: me.statut,
      logo_updated_at: me.logo_updated_at ?? null,
    })
  }

  /**
   * Met à jour le seul horodatage du logo, après un envoi ou une suppression
   * depuis la page Paramètres. Évite un aller-retour sur /tenant/me.
   */
  function setTenantLogoUpdatedAt(value: string | null) {
    if (tenant.value) {
      tenant.value = { ...tenant.value, logo_updated_at: value }
    }
  }

  /**
   * Vide le stockage local du store. Appelé au changement de cabinet et à la
   * déconnexion, pour ne laisser aucune donnée d'un tenant visible à un autre.
   */
  function purgePersistedState() {
    user.value = null
    tenant.value = null
    tenantMessage.value = null
    try {
      localStorage.removeItem('auth')
    } catch {
      // Stockage indisponible (mode privé) — rien à purger.
    }
  }

  function clearAuth() {
    accessToken.value = null
    user.value = null
    tenant.value = null
    tenantMessage.value = null
    delete axios.defaults.headers.common['Authorization']
    try {
      localStorage.removeItem('auth')
    } catch {
      // Ignoré volontairement.
    }
  }

  async function fetchMe() {
    const { data } = await axios.get<UserInfo>('/api/users/me')
    setUser(data)
  }

  /**
   * Applique un blocage de cabinet sans détruire la session : l'utilisateur reste
   * identifié, seul l'accès aux données est fermé.
   */
  function applyTenantBlock(block: TenantBlock) {
    tenantMessage.value = block.message
    if (tenant.value) {
      tenant.value = { ...tenant.value, statut: block.statut }
    }
  }

  /**
   * Renouvelle le jeton d'accès à partir du cookie httpOnly `refresh_token`.
   *
   * Distingue deux échecs que l'ancienne implémentation confondait :
   *   - cabinet bloqué (402/403) → la session est CONSERVÉE, le statut est
   *     enregistré et le routeur peut afficher la page d'explication ;
   *   - échec d'authentification → la session est purgée, retour au login.
   */
  async function silentRefresh(): Promise<boolean> {
    try {
      const { data } = await axios.post<{ access_token: string }>(
        '/api/auth/refresh',
        null,
        { withCredentials: true },
      )
      setToken(data.access_token)
      return true
    } catch (err: unknown) {
      const res = (err as { response?: { status?: number; data?: unknown } }).response
      const block = readTenantBlock(res?.status, res?.data)
      if (block) {
        applyTenantBlock(block)
        return false
      }
      // Aucune réponse du serveur = échec réseau (navigation qui interrompt la
      // requête, coupure) : la session n'est pas en cause, on la conserve pour
      // une nouvelle tentative plutôt que de déconnecter l'utilisateur.
      if (!res) return false
      clearAuth()
      return false
    }
  }

  /**
   * Recharge le cabinet courant depuis l'API. Appelé au bootstrap pour rafraîchir
   * un statut qui aurait changé (suspension) pendant que l'onglet était fermé, et
   * depuis la page de blocage pour détecter une réactivation.
   *
   * Si le jeton d'accès manque (rafraîchissement refusé pour cause de cabinet
   * bloqué), on retente d'abord de l'obtenir : c'est ce qui permet de sortir de la
   * page de blocage dès que le cabinet est réactivé, sans reconnexion.
   */
  async function fetchTenant(): Promise<TenantMe | null> {
    if (!accessToken.value && user.value) {
      await silentRefresh()
    }
    try {
      const { data } = await axios.get<TenantMe>('/api/tenant/me')
      setTenantFromMe(data)
      return data
    } catch (err: unknown) {
      const res = (err as { response?: { status?: number; data?: unknown } }).response
      const block = readTenantBlock(res?.status, res?.data)
      if (block) applyTenantBlock(block)
      return null
    }
  }

  return {
    accessToken,
    user,
    tenant,
    tenantMessage,
    isAuthenticated,
    mustChangePassword,
    role,
    isSupervisor,
    tenantName,
    tenantLogoUpdatedAt,
    tenantStatut,
    tenantActive,
    tenantBlocked,
    bootstrapReady,
    resolveBootstrap,
    setToken,
    setUser,
    setTenant,
    setTenantFromMe,
    setTenantLogoUpdatedAt,
    setTenantMessage,
    applyTenantBlock,
    purgePersistedState,
    clearAuth,
    fetchMe,
    silentRefresh,
    fetchTenant,
  }
}, { persist: { paths: ['user', 'tenant'] } })
