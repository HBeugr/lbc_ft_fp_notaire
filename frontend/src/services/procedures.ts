import api from '@/services/api'

export const NB_SLOTS_PROCEDURE = 7

export interface ProcedureFileOut {
  id: string
  procedure_id: string
  slot: number
  nom_fichier: string
  taille_octets: number
  sha256_hash: string
  uploaded_by: string
  created_at: string
}

export interface ProcedureOut {
  id: string
  nom: string
  created_by: string
  created_at: string
  updated_at: string
  nb_pieces: number
}

export interface ProcedureDetail extends ProcedureOut {
  files: ProcedureFileOut[]
}

export interface ProcedureListResponse {
  items: ProcedureOut[]
  total: number
  page: number
  page_size: number
}

export const proceduresService = {
  async list(params: { page?: number; page_size?: number; search?: string } = {}): Promise<ProcedureListResponse> {
    const { data } = await api.get<ProcedureListResponse>('/procedures', { params })
    return data
  },

  async get(id: string): Promise<ProcedureDetail> {
    const { data } = await api.get<ProcedureDetail>(`/procedures/${id}`)
    return data
  },

  async create(nom: string): Promise<ProcedureOut> {
    const { data } = await api.post<ProcedureOut>('/procedures', { nom })
    return data
  },

  async rename(id: string, nom: string): Promise<ProcedureOut> {
    const { data } = await api.patch<ProcedureOut>(`/procedures/${id}`, { nom })
    return data
  },

  async remove(id: string): Promise<void> {
    await api.delete(`/procedures/${id}`)
  },

  async uploadFile(
    id: string,
    slot: number,
    file: File,
    onProgress?: (pct: number) => void,
  ): Promise<ProcedureFileOut> {
    const form = new FormData()
    form.append('file', file)
    form.append('slot', String(slot))
    const { data } = await api.post<ProcedureFileOut>(`/procedures/${id}/files`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress) onProgress(e.total ? Math.round((e.loaded / e.total) * 100) : 50)
      },
    })
    return data
  },

  async deleteFile(fileId: string): Promise<void> {
    await api.delete(`/procedure-files/${fileId}`)
  },

  async downloadFile(fileId: string, filename: string): Promise<void> {
    const { data } = await api.get(`/procedure-files/${fileId}/download`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  },
}
