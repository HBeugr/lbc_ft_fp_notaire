import axios, { type AxiosInstance } from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useSuperAdminStore } from '@/stores/superAdmin'
import { readTenantBlock } from '@/services/tenantBlock'

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.accessToken && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  return config
})

let _isRefreshing = false
let _failedQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = []

function _drainQueue(token?: string, error?: unknown) {
  _failedQueue.forEach(p => (token ? p.resolve(token) : p.reject(error)))
  _failedQueue = []
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    const status = error.response?.status

    // Cabinet bloqué (402 suspendu, 403 en configuration / archivé).
    // On NE déconnecte PAS : l'utilisateur reste identifié, seul l'accès est fermé.
    // `readTenantBlock` accepte les deux formes de réponse du backend (code
    // imbriqué dans `detail` côté routers, à la racine côté middleware).
    const block = readTenantBlock(status, error.response?.data)
    if (block) {
      const auth = useAuthStore()
      auth.applyTenantBlock(block)
      const { default: router } = await import('@/router')
      if (router.currentRoute.value.name !== 'compte-suspendu') {
        router.push({ name: 'compte-suspendu' })
      }
      return Promise.reject(error)
    }

    // 402 sans code de blocage = quota de sièges atteint sur POST /users :
    // laissé au composant appelant (message affiché dans le formulaire).
    if (status === 402) {
      return Promise.reject(error)
    }

    if (status !== 401 || original._retry) {
      return Promise.reject(error)
    }
    if (_isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        _failedQueue.push({ resolve, reject })
      }).then(token => {
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      })
    }
    if (original.url?.includes('/auth/login') || original.url?.includes('/auth/refresh')) {
      return Promise.reject(error)
    }
    original._retry = true
    _isRefreshing = true
    try {
      // Passe par l'instance `api` (baseURL + withCredentials) et non par axios global,
      // sinon la requête échappe à la configuration commune du client.
      const { data } = await api.post<{ access_token: string }>('/auth/refresh')
      const auth = useAuthStore()
      auth.setToken(data.access_token)
      original.headers.Authorization = `Bearer ${data.access_token}`
      _drainQueue(data.access_token)
      return api(original)
    } catch (refreshError) {
      _drainQueue(undefined, refreshError)
      useAuthStore().clearAuth()
      const { default: router } = await import('@/router')
      router.push({ name: 'login' })
      return Promise.reject(refreshError)
    } finally {
      _isRefreshing = false
    }
  },
)

// ── Console d'exploitation ────────────────────────────────────────────
// Instance dédiée : la population Super-Admin est distincte de celle des cabinets.
// Les deux jetons ne doivent jamais se mélanger ni s'écraser, d'où deux instances
// séparées plutôt qu'un en-tête conditionnel sur `api`.
export const superAdminApi: AxiosInstance = axios.create({
  baseURL: '/api/super-admin',
  withCredentials: false,
})

superAdminApi.interceptors.request.use((config) => {
  const sa = useSuperAdminStore()
  if (sa.accessToken && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${sa.accessToken}`
  }
  return config
})

superAdminApi.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    // Pas de refresh côté console : un 401 renvoie simplement à l'écran de connexion.
    if (error.response?.status === 401 && !original?.url?.includes('/auth/login')) {
      useSuperAdminStore().clearSession()
      const { default: router } = await import('@/router')
      if (router.currentRoute.value.name !== 'super-admin-login') {
        router.push({ name: 'super-admin-login' })
      }
    }
    return Promise.reject(error)
  },
)

export const authService = {
  async logout(): Promise<void> {
    await api.post('/auth/logout')
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<any> {
    const { data } = await api.patch('/auth/password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    return data
  },
}

export default api
