import api from './api'

export interface DosAddendumOut {
  id: string
  dos_id: string
  auteur_id: string
  contenu: string
  created_at: string
}

export interface DosOut {
  id: string
  dossier_id: string
  reference: string
  section_1_organisme: Record<string, string> | null
  section_2_reference_auto: string | null
  section_3_objet: string | null
  section_4_identite_declarant: Record<string, string> | null
  section_5_contexte_operation: string | null
  section_6_montant_estime: number | null
  section_7_intervenants: Record<string, unknown> | null
  section_8_analyse_soupcon: string | null
  section_9_motifs: string[] | null
  section_10_informations_complementaires: string | null
  statut: 'brouillon' | 'finalisee'
  created_by: string
  finalized_by: string | null
  finalized_at: string | null
  minio_path: string | null
  created_at: string
  addendums: DosAddendumOut[]
}

export interface DosListResponse {
  items: DosOut[]
  total: number
}

export interface DosSectionUpdate {
  section_3_objet?: string
  section_4_identite_declarant?: Record<string, string>
  section_5_contexte_operation?: string
  section_6_montant_estime?: number
  section_7_intervenants?: Record<string, unknown>
  section_8_analyse_soupcon?: string
  section_9_motifs?: string[]
  section_10_informations_complementaires?: string
}

export const MOTIFS_SUSPICION = [
  "Opération sans justification économique apparente",
  "Refus de fournir des documents justificatifs",
  "Utilisation de faux documents",
  "Opération avec pays ou territoire non coopératif",
  "Montage juridique complexe sans raison légitime",
  "Client n'agissant pas pour son propre compte",
  "Transactions en espèces inhabituelles",
  "Opération impliquant une personne politiquement exposée (PPE)",
  "Transactions fractionnées (structuring)",
  "Changements soudains de comportement financier",
  "Opération ne correspondant pas au profil client",
  "Source de fonds inexpliquée ou invérifiable",
  "Opération en rapport avec une activité illicite suspectée",
  "Toute autre circonstance laissant soupçonner un blanchiment",
]

export const dosService = {
  async create(dossierId: string): Promise<DosOut> {
    const { data } = await api.post<DosOut>(`/dossiers/${dossierId}/dos`)
    return data
  },

  async list(dossierId: string): Promise<DosListResponse> {
    const { data } = await api.get<DosListResponse>(`/dossiers/${dossierId}/dos`)
    return data
  },

  async listAll(params?: { page?: number; page_size?: number; reference?: string; statut?: string }): Promise<DosListResponse> {
    const { data } = await api.get<DosListResponse | DosOut[]>('/dos', { params })
    if (Array.isArray(data)) {
      return { items: data, total: data.length }
    }
    return data
  },

  async get(dosId: string): Promise<DosOut> {
    const { data } = await api.get<DosOut>(`/dos/${dosId}`)
    return data
  },

  async updateSections(dosId: string, update: DosSectionUpdate): Promise<DosOut> {
    const { data } = await api.patch<DosOut>(`/dos/${dosId}/sections`, update)
    return data
  },

  async finaliser(dosId: string): Promise<DosOut> {
    const { data } = await api.post<DosOut>(`/dos/${dosId}/finaliser`)
    return data
  },

  async downloadPdfBlob(dosId: string): Promise<Blob> {
    const { data } = await api.get(`/dos/${dosId}/pdf`, { responseType: 'blob' })
    return data
  },

  async addAddendum(dosId: string, contenu: string): Promise<DosAddendumOut> {
    const { data } = await api.post<DosAddendumOut>(`/dos/${dosId}/addendum`, { contenu })
    return data
  },
}
