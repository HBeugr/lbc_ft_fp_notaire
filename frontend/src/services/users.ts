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
    const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$'
    let pwd = ''
    for (let i = 0; i < 10; i++) pwd += chars[Math.floor(Math.random() * chars.length)]
    await api.post(`/admin/users/${userId}/reset-password`, { new_password: pwd, must_change_password: true })
    return { temp_password: pwd }
  },
}
