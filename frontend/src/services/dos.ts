import api from './api'

// ── Modèle backend notaire (CENTIF) — aligné sur app/schemas/dos.py ───────────
export interface DosAddendumOut {
  id: string
  dos_id: string
  user_id: string
  contenu: string
  created_at: string
}

export interface DosOut {
  id: string
  dossier_id: string
  reference_interne: string
  statut: string
  statut_operation: string | null
  date_detection: string | null
  organisme_libelle: string | null
  organisme_adresse: string | null
  organisme_email: string | null
  organisme_telephone: string | null
  type_soupcon_bc: boolean
  type_soupcon_ft: boolean
  type_soupcon_prolif: boolean
  motifs: Record<string, unknown> | null
  statut_operations: Record<string, unknown> | null
  detail_transactions: unknown
  indices_blanchiment: string | null
  identification: Record<string, unknown> | null
  relations_affaires: Record<string, unknown> | null
  supports: Record<string, unknown> | null
  autres_informations: string | null
  decision: string | null
  motif_classement: string | null
  initie_par: string
  valide_par: string | null
  valide_par_rc: string | null
  valide_rc_at: string | null
  valide_par_dg: string | null
  valide_dg_at: string | null
  date_transmission_centif: string | null
  transmis_par: string | null
  soumis_at: string | null
  accuse_recu_at: string | null
  accuse_recu_ref: string | null
  accuse_alerte_j15_envoyee: boolean
  created_at: string
  updated_at: string
  addendums: DosAddendumOut[]
}

export interface DosListResponse {
  items: DosOut[]
  total: number
}

export const dosService = {
  // Création — le backend attend { dossier_id } sur POST /dos et génère la référence.
  async create(dossierId: string): Promise<DosOut> {
    const { data } = await api.post<DosOut>('/dos', { dossier_id: dossierId })
    return data
  },

  // Liste globale — GET /dos renvoie un tableau (paramètres statut / limit / offset).
  async listAll(params?: { statut?: string; limit?: number; offset?: number }): Promise<DosListResponse> {
    const { data } = await api.get<DosOut[]>('/dos', { params })
    return { items: data, total: data.length }
  },

  // Le backend n'expose pas de liste par dossier : on filtre côté client (1 DOS max par dossier).
  async listForDossier(dossierId: string): Promise<DosListResponse> {
    const { data } = await api.get<DosOut[]>('/dos', { params: { limit: 200 } })
    const items = data.filter(d => d.dossier_id === dossierId)
    return { items, total: items.length }
  },

  async get(dosId: string): Promise<DosOut> {
    const { data } = await api.get<DosOut>(`/dos/${dosId}`)
    return data
  },

  async downloadPdfBlob(dosId: string): Promise<Blob> {
    const { data } = await api.get(`/dos/${dosId}/pdf`, { responseType: 'blob' })
    return data
  },

  async addAddendum(dosId: string, contenu: string): Promise<DosAddendumOut> {
    const { data } = await api.post<DosAddendumOut>(`/dos/${dosId}/addendums`, { contenu })
    return data
  },

  // --- Workflow CENTIF : soumettre → valider (RC) → transmettre (DG) / classer → accusé ---
  async soumettre(dosId: string): Promise<DosOut> {
    const { data } = await api.post<DosOut>(`/dos/${dosId}/soumettre`)
    return data
  },

  async valider(dosId: string): Promise<DosOut> {
    const { data } = await api.post<DosOut>(`/dos/${dosId}/valider`)
    return data
  },

  async transmettre(dosId: string): Promise<DosOut> {
    const { data } = await api.post<DosOut>(`/dos/${dosId}/transmettre`)
    return data
  },

  async classer(dosId: string, motif: string): Promise<DosOut> {
    const { data } = await api.post<DosOut>(`/dos/${dosId}/classer`, { motif })
    return data
  },

  async accuseRecu(dosId: string, referenceCentif: string): Promise<DosOut> {
    const { data } = await api.patch<DosOut>(`/dos/${dosId}/accuse-recu`, null, {
      params: { reference_centif: referenceCentif },
    })
    return data
  },
}

// Libellés de statut CENTIF (partagés par la liste et le formulaire).
export const DOS_STATUT_LABELS: Record<string, string> = {
  brouillon: 'Brouillon',
  en_cours: 'En cours',
  en_validation: 'En validation',
  soumis: 'Soumise',
  validee_rc: 'Validée conformité',
  transmise: 'Transmise CENTIF',
  classee: 'Classée sans suite',
  accuse_recu: 'Accusé reçu',
}

export function dosStatutLabel(statut: string): string {
  return DOS_STATUT_LABELS[statut] ?? statut
}
