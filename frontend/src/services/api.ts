import axios, { type AxiosInstance } from 'axios'
import { useAuthStore } from '@/stores/auth'

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
    if (error.response?.status !== 401 || original._retry) {
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
      const { data } = await axios.post<{ access_token: string }>('/api/auth/refresh', null, { withCredentials: true })
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
