import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

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

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<UserInfo | null>(null)

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

  function setToken(token: string) {
    accessToken.value = token
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }

  function setUser(u: UserInfo) {
    user.value = u
  }

  function clearAuth() {
    accessToken.value = null
    user.value = null
    delete axios.defaults.headers.common['Authorization']
  }

  async function fetchMe() {
    const { data } = await axios.get<UserInfo>('/api/users/me')
    setUser(data)
  }

  return {
    accessToken,
    user,
    isAuthenticated,
    mustChangePassword,
    role,
    isSupervisor,
    bootstrapReady,
    resolveBootstrap,
    setToken,
    setUser,
    clearAuth,
    fetchMe,
  }
}, { persist: { paths: ['user'] } })
