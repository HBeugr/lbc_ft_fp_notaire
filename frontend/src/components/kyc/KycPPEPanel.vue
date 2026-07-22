<template>
  <div class="ppe-panel">
    <div class="panel-header">
      <div>
        <h3 class="panel-title">Personnes Politiquement Exposées (PPE)</h3>
        <p class="panel-subtitle">Déclarations PPE — statut, fonctions, vérifications listes (GIABA / OFAC / UE)</p>
      </div>
      <!-- openForm() sans argument : sinon l'événement du clic est passé comme PPE à éditer. -->
      <button class="btn-primary" @click="openForm()">
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Ajouter un PPE
      </button>
    </div>

    <div v-if="loading" class="panel-loading">Chargement…</div>

    <div v-else-if="ppeList.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
      <p>Aucune déclaration PPE enregistrée</p>
    </div>

    <div v-else class="ppe-list">
      <div v-for="ppe in ppeList" :key="ppe.id" class="ppe-card">
        <div class="ppe-card-left">
          <span class="statut-badge" :class="`statut--${ppe.statut_ppe}`">{{ STATUT_LABELS[ppe.statut_ppe] ?? ppe.statut_ppe }}</span>
          <div>
            <p class="ppe-name">{{ ppe.fonctions || '—' }}</p>
            <p class="ppe-meta">
              <span v-if="ppe.pays_concerne">{{ ppe.pays_concerne }}<span class="sep">·</span></span>
              <span class="check" :class="{ ok: ppe.verification_giaba }">GIABA</span>
              <span class="check" :class="{ ok: ppe.verification_ofac }">OFAC</span>
              <span class="check" :class="{ ok: ppe.verification_ue }">UE</span>
              <span v-if="ppe.ras" class="ras-tag">RAS</span>
            </p>
          </div>
        </div>
        <div class="card-actions">
          <button class="icon-btn" @click="openForm(ppe)" title="Modifier">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="icon-btn icon-btn--danger" @click="ppeToDelete = ppe" title="Supprimer">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Add modal -->
    <Teleport to="body">
      <div v-if="showForm" class="modal-backdrop" @click.self="showForm = false">
        <div class="modal">
          <div class="modal-header">
            <h2 class="modal-title">{{ editingId ? 'Modifier' : 'Ajouter' }} une déclaration PPE</h2>
            <button class="modal-close" @click="showForm = false">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="form-grid">
              <div class="form-group form-group--full">
                <label class="form-label">Statut PPE <span class="req">*</span></label>
                <select v-model="form.statut_ppe" class="form-input">
                  <option value="Non_PPE">Non PPE</option>
                  <option value="PPE_National">PPE National</option>
                  <option value="PPE_Etranger">PPE Étranger</option>
                  <option value="Entourage_PPE">Entourage PPE</option>
                </select>
              </div>
              <div class="form-group form-group--full">
                <label class="form-label">Fonctions exercées</label>
                <input v-model="form.fonctions" type="text" class="form-input" placeholder="Ex : Ministre, Magistrat, Dirigeant d'entreprise publique…" />
              </div>
              <div class="form-group form-group--full">
                <label class="form-label">Pays concerné</label>
                <input v-model="form.pays_concerne" type="text" class="form-input" />
              </div>
              <div class="form-group form-group--full checks">
                <label class="check-row"><input v-model="form.verification_giaba" type="checkbox" class="checkbox" /> Vérification GIABA-BCEAO</label>
                <label class="check-row"><input v-model="form.verification_ofac" type="checkbox" class="checkbox" /> Vérification OFAC</label>
                <label class="check-row"><input v-model="form.verification_ue" type="checkbox" class="checkbox" /> Vérification UE / CSNU</label>
                <label class="check-row"><input v-model="form.ras" type="checkbox" class="checkbox" /> RAS (rien à signaler)</label>
              </div>

              <!-- Vigilance renforcée (Art. 29) -->
              <div class="form-group form-group--full section-divider">Vigilance renforcée (Art. 29)</div>
              <div class="form-group form-group--full">
                <label class="form-label">Résultat presse négative</label>
                <select v-model="form.resultat_presse" class="form-input">
                  <option :value="null">— Non renseigné —</option>
                  <option value="Negatif">Négatif (rien trouvé)</option>
                  <option value="Positif">Positif (élément défavorable)</option>
                  <option value="Ambigu">Ambigu</option>
                </select>
              </div>
              <div v-if="form.resultat_presse && form.resultat_presse !== 'Negatif'" class="form-group form-group--full">
                <label class="form-label">Détails presse négative</label>
                <textarea v-model="form.details_presse" class="form-input" rows="2" placeholder="Sources, dates, nature des éléments défavorables…" />
              </div>
              <div class="form-group form-group--full">
                <label class="form-label">Niveau d'exposition</label>
                <select v-model="form.niveau_exposition" class="form-input">
                  <option :value="null">— Non renseigné —</option>
                  <option value="Faible">Faible</option>
                  <option value="Moyen">Moyen</option>
                  <option value="Eleve">Élevé</option>
                </select>
              </div>
              <div class="form-group form-group--full">
                <label class="form-label">Mesures de vigilance renforcée proposées</label>
                <textarea v-model="form.mesures_proposees" class="form-input" rows="2" placeholder="Ex : approbation Notaire Principal, justificatifs d'origine des fonds renforcés, suivi périodique…" />
              </div>
              <div class="form-group form-group--full section-divider">Validation (Responsable Conformité)</div>
              <div class="form-group form-group--full">
                <label class="form-label">Statut de validation</label>
                <select v-model="form.statut_validation" class="form-input">
                  <option value="en_attente">En attente</option>
                  <option value="valide">Validé</option>
                  <option value="rejete">Rejeté</option>
                </select>
              </div>
              <div class="form-group form-group--full">
                <label class="form-label">Commentaire de validation</label>
                <textarea v-model="form.commentaire_validation" class="form-input" rows="2" />
              </div>
            </div>
          </div>
          <div v-if="serverError" class="modal-error">{{ serverError }}</div>
          <div class="modal-footer">
            <button class="btn-ghost" @click="showForm = false">Annuler</button>
            <button class="btn-primary" :disabled="saving" @click="save">
              {{ saving ? 'Enregistrement…' : (editingId ? 'Mettre à jour' : 'Ajouter') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete confirm -->
    <Teleport to="body">
      <div v-if="ppeToDelete" class="modal-backdrop" @click.self="ppeToDelete = null">
        <div class="confirm-modal">
          <p class="confirm-text">Supprimer cette déclaration PPE ?</p>
          <div class="confirm-actions">
            <button class="btn-ghost" @click="ppeToDelete = null">Annuler</button>
            <button class="btn-danger" :disabled="deleting" @click="doDelete">
              {{ deleting ? 'Suppression…' : 'Supprimer' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dossiersService, type KycPPEData } from '@/services/dossiers'

const props = defineProps<{ dossierId: string; clientType?: 'PP' | 'PM' }>()

const STATUT_LABELS: Record<string, string> = {
  Non_PPE: 'Non PPE',
  PPE_National: 'PPE National',
  PPE_Etranger: 'PPE Étranger',
  Entourage_PPE: 'Entourage PPE',
}

const loading = ref(true)
const ppeList = ref<KycPPEData[]>([])
const showForm = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)
const serverError = ref('')
const ppeToDelete = ref<KycPPEData | null>(null)
const deleting = ref(false)

const form = ref<Partial<KycPPEData>>({})

function blankForm(): Partial<KycPPEData> {
  return {
    statut_ppe: 'PPE_National',
    fonctions: null,
    pays_concerne: null,
    verification_giaba: false,
    verification_ofac: false,
    verification_ue: false,
    ras: false,
    resultat_presse: null,
    details_presse: null,
    niveau_exposition: null,
    mesures_proposees: null,
    statut_validation: 'en_attente',
    commentaire_validation: null,
  }
}

onMounted(refresh)

async function refresh() {
  loading.value = true
  try {
    ppeList.value = await dossiersService.listKycPPE(props.dossierId, props.clientType ?? 'PP')
  } finally {
    loading.value = false
  }
}

function openForm(ppe?: KycPPEData) {
  if (ppe) {
    editingId.value = ppe.id ?? null
    form.value = { ...ppe }
  } else {
    editingId.value = null
    form.value = blankForm()
  }
  serverError.value = ''
  showForm.value = true
}

async function save() {
  saving.value = true
  serverError.value = ''
  try {
    const ct = props.clientType ?? 'PP'
    if (editingId.value) {
      const updated = await dossiersService.updateKycPPE(props.dossierId, editingId.value, form.value, ct)
      const idx = ppeList.value.findIndex(p => p.id === editingId.value)
      if (idx >= 0) ppeList.value[idx] = updated
    } else {
      const created = await dossiersService.createKycPPE(props.dossierId, form.value, ct)
      ppeList.value.push(created)
    }
    showForm.value = false
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: string } } }
    serverError.value = e?.response?.data?.detail ?? "Erreur lors de l'enregistrement."
  } finally {
    saving.value = false
  }
}

async function doDelete() {
  if (!ppeToDelete.value?.id) return
  deleting.value = true
  try {
    await dossiersService.deleteKycPPE(props.dossierId, ppeToDelete.value.id, props.clientType ?? 'PP')
    ppeList.value = ppeList.value.filter(p => p.id !== ppeToDelete.value?.id)
    ppeToDelete.value = null
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.ppe-panel { display: flex; flex-direction: column; gap: 1rem; }
.panel-header { display: flex; align-items: flex-start; justify-content: space-between; }
.panel-title { font-size: 0.9375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.panel-subtitle { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0; }
.panel-loading { padding: 2rem; text-align: center; font-size: 0.875rem; color: var(--color-text-muted); }

.empty-state { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 2.5rem 1rem; color: var(--color-text-muted); text-align: center; }
.empty-state svg { width: 36px; height: 36px; stroke: var(--color-border); }
.empty-state p { font-size: 0.875rem; margin: 0; }

.ppe-list { display: flex; flex-direction: column; gap: 0.5rem; }
.ppe-card { display: flex; align-items: center; justify-content: space-between; padding: 0.875rem 1rem; background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 8px; }
.ppe-card-left { display: flex; align-items: center; gap: 0.75rem; }
.ppe-name { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); margin: 0 0 0.2rem; }
.ppe-meta { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0; display: flex; align-items: center; gap: 0.375rem; flex-wrap: wrap; }
.sep { color: var(--color-border); margin: 0 0.125rem; }
.check { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 5px; padding: 1px 5px; font-size: 0.6875rem; opacity: 0.5; }
.check.ok { opacity: 1; color: var(--color-status-valide); border-color: var(--color-status-valide); }
.ras-tag { background: var(--color-status-valide-bg); color: var(--color-status-valide); border-radius: 5px; padding: 1px 5px; font-size: 0.6875rem; font-weight: 700; }

.statut-badge { border-radius: 10px; padding: 3px 9px; font-size: 0.6875rem; font-weight: 700; flex-shrink: 0; }
.statut--Non_PPE { color: var(--color-text-secondary); background: var(--color-bg-card); }
.statut--PPE_National { color: var(--color-status-vigilance); background: var(--color-status-vigilance-bg); }
.statut--PPE_Etranger { color: var(--color-status-bloque); background: var(--color-status-bloque-bg); }
.statut--Entourage_PPE { color: var(--color-status-en-analyse); background: var(--color-status-en-analyse-bg); }

.card-actions { display: flex; align-items: center; gap: 0.25rem; }
.icon-btn { background: none; border: none; cursor: pointer; padding: 0.25rem; color: var(--color-text-muted); border-radius: 5px; }
.icon-btn:hover { background: var(--color-bg-card); }
.icon-btn svg { width: 15px; height: 15px; }
.icon-btn--danger:hover { color: var(--color-status-bloque); }

.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 200; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.modal { background: var(--color-bg-card); border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); width: 100%; max-width: 520px; max-height: 90vh; display: flex; flex-direction: column; overflow: hidden; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem 0.5rem; }
.modal-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.modal-close { background: none; border: none; cursor: pointer; padding: 0.25rem; color: var(--color-text-muted); }
.modal-close svg { width: 18px; height: 18px; }
.modal-body { padding: 1rem 1.5rem; overflow-y: auto; flex: 1; }
.form-grid { display: grid; grid-template-columns: 1fr; gap: 0.75rem; }
.form-group { display: flex; flex-direction: column; gap: 0.25rem; }
.form-group--full { grid-column: 1 / -1; }
.section-divider { font-size: 0.75rem; font-weight: 700; color: var(--color-sidebar-bg); text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--color-border); padding-bottom: 0.25rem; margin-top: 0.5rem; }
.form-label { font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); }
.req { color: var(--color-status-bloque); }
.form-input { padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px; font-size: 0.8125rem; color: var(--color-text-primary); background: var(--color-bg-card); outline: none; }
.form-input:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.checks { gap: 0.5rem; }
.check-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: var(--color-text-primary); cursor: pointer; }
.checkbox { width: 15px; height: 15px; accent-color: var(--color-sidebar-bg); cursor: pointer; }
.modal-error { margin: 0 1.5rem; padding: 0.5rem 0.75rem; background: var(--color-status-bloque-bg); color: var(--color-status-bloque); border-radius: 7px; font-size: 0.8125rem; }
.modal-footer { display: flex; justify-content: flex-end; gap: 0.75rem; padding: 1rem 1.5rem; border-top: 1px solid var(--color-border); }

.confirm-modal { background: var(--color-bg-card); border-radius: 10px; box-shadow: 0 12px 40px rgba(0,0,0,0.15); padding: 1.5rem; max-width: 380px; width: 100%; }
.confirm-text { font-size: 0.9375rem; color: var(--color-text-primary); margin: 0 0 1.25rem; }
.confirm-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }

.btn-primary { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5rem 1rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 8px; font-size: 0.8125rem; font-weight: 600; cursor: pointer; }
.btn-primary:hover { opacity: 0.88; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-icon { width: 14px; height: 14px; }
.btn-ghost { padding: 0.5rem 0.875rem; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 0.8125rem; cursor: pointer; }
.btn-danger { padding: 0.5rem 0.875rem; border: none; border-radius: 8px; background: var(--color-status-bloque); color: #fff; font-size: 0.8125rem; cursor: pointer; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
