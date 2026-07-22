import api from './api'

export interface UserOut {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
  totp_enabled: boolean
  requires_2fa: boolean
  must_change_password: boolean
}

export interface UserCreatePayload {
  email: string
  password: string
  first_name: string
  last_name: string
  role: string
}

export interface UserUpdatePayload {
  first_name?: string
  last_name?: string
  role?: string
  is_active?: boolean
}

export interface UserListResponse {
  items: UserOut[]
  total: number
}

export const usersService = {
  async list(): Promise<UserListResponse> {
    const { data } = await api.get<UserListResponse>('/users')
    return data
  },

  async create(payload: UserCreatePayload): Promise<UserOut> {
    const { data } = await api.post<UserOut>('/users', payload)
    return data
  },

  async update(userId: string, payload: UserUpdatePayload): Promise<UserOut> {
    const { data } = await api.patch<UserOut>(`/users/${userId}`, payload)
    return data
  },

  async deactivate(userId: string): Promise<UserOut> {
    const { data } = await api.patch<UserOut>(`/users/${userId}`, { is_active: false })
    return data
  },

  async reactivate(userId: string): Promise<UserOut> {
    const { data } = await api.patch<UserOut>(`/users/${userId}`, { is_active: true })
    return data
  },

  async resetTotp(userId: string): Promise<UserOut> {
    await api.delete(`/admin/users/${userId}/totp`)
    const { data } = await api.get<UserOut>(`/users/${userId}`)
    return data
  },

  async resetPassword(userId: string): Promise<{ temp_password: string }> {
    const pwd = strongTempPassword()
    await api.post(`/admin/users/${userId}/reset-password`, { new_password: pwd, must_change_password: true })
    return { temp_password: pwd }
  },
}

// Génère un mot de passe temporaire conforme à la politique serveur (≥12 + 4 classes),
// avec un PRNG cryptographique (crypto.getRandomValues).
function strongTempPassword(): string {
  const UPPER = 'ABCDEFGHJKMNPQRSTUVWXYZ'
  const LOWER = 'abcdefghjkmnpqrstuvwxyz'
  const DIGIT = '23456789'
  const SPECIAL = '!@#$%&*?'
  const ALL = UPPER + LOWER + DIGIT + SPECIAL
  const rnd = (max: number) => {
    const a = new Uint32Array(1)
    crypto.getRandomValues(a)
    return a[0] % max
  }
  const pick = (set: string) => set[rnd(set.length)]
  // Garantit au moins une occurrence de chaque classe
  const chars = [pick(UPPER), pick(LOWER), pick(DIGIT), pick(SPECIAL)]
  for (let i = chars.length; i < 14; i++) chars.push(pick(ALL))
  // Mélange (Fisher–Yates)
  for (let i = chars.length - 1; i > 0; i--) {
    const j = rnd(i + 1)
    ;[chars[i], chars[j]] = [chars[j], chars[i]]
  }
  return chars.join('')
}
