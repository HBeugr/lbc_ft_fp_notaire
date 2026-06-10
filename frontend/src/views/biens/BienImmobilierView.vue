<template>
  <div class="biens-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Biens Immobiliers</h1>
        <p class="page-subtitle">Fiches biens + détection des transactions multiples (FR-5)</p>
      </div>
      <button class="btn-primary" @click="showCreateModal = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="btn-icon">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        Nouveau bien
      </button>
    </div>

    <!-- Table -->
    <div class="card">
      <div v-if="loading" class="skeleton-list">
        <div v-for="i in 6" :key="i" class="skeleton skeleton--row" />
      </div>

      <div v-else-if="biens.length === 0" class="empty-state">
        <svg class="empty-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
        <p>Aucun bien immobilier enregistré.</p>
      </div>

      <table v-else class="data-table">
        <thead>
          <tr>
            <th>Référence</th>
            <th>Adresse / Ville</th>
            <th>Type / Sous-type</th>
            <th>Valeur (FCFA)</th>
            <th>Mode paiement</th>
            <th>Situation</th>
            <th>Dossiers</th>
            <th>Alertes</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="bien in biens" :key="bien.id" :class="{ 'row--alert': bien.alert_transactions || bien.alerte_especes }">
            <td class="td-ref">{{ bien.reference }}</td>
            <td class="td-adresse">
              <div>{{ bien.adresse }}</div>
              <div v-if="bien.ville" class="td-sub">{{ bien.ville }}</div>
            </td>
            <td>
              <div>{{ bien.type_bien }}</div>
              <div v-if="bien.sous_type" class="td-sub">{{ bien.sous_type }}</div>
            </td>
            <td>{{ bien.valeur_estimee_fcfa ? formatMontant(bien.valeur_estimee_fcfa) : '—' }}</td>
            <td>{{ bien.mode_paiement || '—' }}</td>
            <td>{{ bien.situation_juridique || '—' }}</td>
            <td>
              <div class="dossier-chips">
                <span v-for="id in bien.dossier_ids.slice(0, 2)" :key="id" class="chip" @click="goToDossier(id)">
                  {{ id.slice(-8) }}
                </span>
                <span v-if="bien.dossier_ids.length > 2" class="chip chip--more">+{{ bien.dossier_ids.length - 2 }}</span>
              </div>
            </td>
            <td>
              <div class="alerts-col">
                <span v-if="bien.alert_transactions" class="alert-pill">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="alert-icon">
                    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                  &gt;2 tx
                </span>
                <span v-if="bien.alerte_especes" class="alert-pill alert-pill--especes">
                  Espèces ≥20M
                </span>
              </div>
            </td>
            <td>
              <button class="btn-edit" @click="editBien(bien)">Modifier</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create/Edit Modal -->
    <div v-if="showCreateModal || bienEdite" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h3 class="modal-title">{{ bienEdite ? 'Modifier le bien' : 'Nouveau bien immobilier' }}</h3>
        <div class="form-grid">
          <!-- Adresse -->
          <div class="field-group field-group--full">
            <label class="field-label">Adresse complète <span class="req">*</span></label>
            <input v-model="form.adresse" type="text" class="field-input" placeholder="Numéro, rue, quartier, commune" />
          </div>
          <!-- Ville -->
          <div class="field-group">
            <label class="field-label">Ville <span class="req">*</span></label>
            <input v-model="form.ville" type="text" class="field-input" placeholder="Ex : Abidjan" />
          </div>
          <!-- Propriétaire -->
          <div class="field-group">
            <label class="field-label">Propriétaire actuel <span class="req">*</span></label>
            <input v-model="form.proprietaire_actuel" type="text" class="field-input" placeholder="Nom du propriétaire" />
          </div>
          <!-- Type de bien -->
          <div class="field-group">
            <label class="field-label">Type de bien <span class="req">*</span></label>
            <select v-model="form.type_bien" class="field-input" @change="form.sous_type = ''">
              <option value="">— Choisir —</option>
              <option value="Résidentiel">Résidentiel</option>
              <option value="Commercial">Commercial</option>
              <option value="Industriel">Industriel</option>
              <option value="Foncier">Foncier</option>
            </select>
          </div>
          <!-- Sous-type -->
          <div class="field-group">
            <label class="field-label">Sous-type <span class="req">*</span></label>
            <select v-model="form.sous_type" class="field-input">
              <option value="">— Choisir —</option>
              <template v-if="form.type_bien === 'Résidentiel'">
                <option>Villa</option><option>Appartement</option><option>Studio</option><option>Duplex</option>
              </template>
              <template v-else-if="form.type_bien === 'Commercial'">
                <option>Bureau</option><option>Local commercial</option><option>Entrepôt</option><option>Immeuble</option>
              </template>
              <template v-else-if="form.type_bien === 'Industriel'">
                <option>Usine</option><option>Zone industrielle</option><option>Hangar</option>
              </template>
              <template v-else-if="form.type_bien === 'Foncier'">
                <option>Terrain nu</option><option>Terrain agricole</option><option>Lotissement</option>
              </template>
              <option v-else value="Autre">Autre</option>
            </select>
          </div>
          <!-- Surface -->
          <div class="field-group">
            <label class="field-label">Surface (m²)</label>
            <input v-model.number="form.surface_m2" type="number" min="0" class="field-input" placeholder="Ex : 120" />
          </div>
          <!-- Valeur estimée -->
          <div class="field-group">
            <label class="field-label">Valeur estimée (FCFA) <span class="req">*</span></label>
            <input v-model.number="form.valeur_estimee_fcfa" type="number" min="0" class="field-input" placeholder="Ex : 45000000" />
            <span v-if="form.valeur_estimee_fcfa && form.valeur_estimee_fcfa >= 20000000" class="field-hint field-hint--warn">
              Valeur ≥ 20M FCFA — paiement en espèces interdit (§80a)
            </span>
          </div>
          <!-- Mode de paiement -->
          <div class="field-group">
            <label class="field-label">Mode de paiement prévu <span class="req">*</span></label>
            <select v-model="form.mode_paiement" class="field-input" :class="{ 'field-input--warn': alerteEspeces }">
              <option value="">— Choisir —</option>
              <option value="Virement">Virement</option>
              <option value="Chèque">Chèque</option>
              <option :value="'Espèces'" :disabled="form.valeur_estimee_fcfa >= 20000000">
                Espèces{{ form.valeur_estimee_fcfa >= 20000000 ? ' (interdit ≥ 20M)' : '' }}
              </option>
              <option value="Mixte">Mixte</option>
            </select>
          </div>
          <!-- Situation juridique -->
          <div class="field-group">
            <label class="field-label">Situation juridique <span class="req">*</span></label>
            <select v-model="form.situation_juridique" class="field-input">
              <option value="">— Choisir —</option>
              <option value="Libre">Libre</option>
              <option value="Hypothèque">Hypothèque</option>
              <option value="Litige">Litige</option>
              <option value="Inconnu">Inconnu</option>
            </select>
          </div>
          <!-- Référence cadastrale -->
          <div class="field-group">
            <label class="field-label">Titre foncier / Réf. cadastrale</label>
            <input v-model="form.reference_cadastrale" type="text" class="field-input" placeholder="Ex : CI-ABJ-001-0042" />
          </div>
        </div>
        <!-- Alerte espèces bloquante -->
        <div v-if="alerteEspeces" class="especes-block">
          Tout paiement pour un bien ≥ 20 millions FCFA doit être effectué par virement ou chèque — Lignes Directrices Immo CENTIF-CI §80a.
        </div>
        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
        <div class="modal-actions">
          <button class="btn-ghost" @click="closeModal">Annuler</button>
          <button class="btn-primary-modal" :disabled="saving || !form.adresse || !form.type_bien || !form.ville || !form.proprietaire_actuel || alerteEspeces" @click="submit">
            <span v-if="saving" class="spinner" />
            {{ bienEdite ? 'Enregistrer' : 'Créer le bien' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

const router = useRouter()

interface Bien {
  id: string
  reference: string
  adresse: string
  ville: string | null
  type_bien: string
  sous_type: string | null
  surface_m2: number | null
  reference_cadastrale: string | null
  valeur_estimee_fcfa: number | null
  mode_paiement: string | null
  situation_juridique: string | null
  proprietaire_actuel: string | null
  dossier_ids: string[]
  alert_transactions?: boolean
  alerte_especes?: boolean
}

const biens  = ref<Bien[]>([])
const loading = ref(true)
const saving  = ref(false)
const showCreateModal = ref(false)
const bienEdite = ref<Bien | null>(null)
const errorMsg = ref<string | null>(null)

const form = reactive({
  adresse: '',
  ville: '',
  type_bien: '',
  sous_type: '',
  surface_m2: null as number | null,
  reference_cadastrale: '',
  valeur_estimee_fcfa: null as number | null,
  mode_paiement: '',
  situation_juridique: '',
  proprietaire_actuel: '',
})

const alerteEspeces = computed(() =>
  form.mode_paiement === 'Espèces' && (form.valeur_estimee_fcfa ?? 0) >= 20_000_000
)

async function load() {
  loading.value = true
  try {
    const r = await api.get('/biens-immobiliers')
    biens.value = r.data.items
  } finally {
    loading.value = false
  }
}

function editBien(bien: Bien) {
  bienEdite.value = bien
  Object.assign(form, {
    adresse: bien.adresse,
    ville: bien.ville ?? '',
    type_bien: bien.type_bien,
    sous_type: bien.sous_type ?? '',
    surface_m2: bien.surface_m2,
    reference_cadastrale: bien.reference_cadastrale ?? '',
    valeur_estimee_fcfa: bien.valeur_estimee_fcfa,
    mode_paiement: bien.mode_paiement ?? '',
    situation_juridique: bien.situation_juridique ?? '',
    proprietaire_actuel: bien.proprietaire_actuel ?? '',
  })
}

function closeModal() { showCreateModal.value = false; bienEdite.value = null; errorMsg.value = null; resetForm() }
function resetForm()  {
  Object.assign(form, {
    adresse: '', ville: '', type_bien: '', sous_type: '', surface_m2: null,
    reference_cadastrale: '', valeur_estimee_fcfa: null,
    mode_paiement: '', situation_juridique: '', proprietaire_actuel: '',
  })
}

async function submit() {
  saving.value = true
  errorMsg.value = null
  try {
    const payload = { ...form }
    if (bienEdite.value) {
      await api.patch(`/biens-immobiliers/${bienEdite.value.id}`, payload)
    } else {
      await api.post('/biens-immobiliers', payload)
    }
    closeModal()
    await load()
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail ?? 'Une erreur est survenue. Veuillez réessayer.'
  } finally {
    saving.value = false
  }
}

function goToDossier(id: string) { router.push({ name: 'kyc-detail', params: { id } }) }

function formatMontant(v: number) {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XOF', maximumFractionDigits: 0 }).format(v)
}

onMounted(load)
</script>

<style scoped>
.biens-page { display: flex; flex-direction: column; gap: 1.25rem; }
.page-header { display: flex; align-items: center; justify-content: space-between; }
.page-title  { font-size: 1.375rem; font-weight: 800; color: var(--color-sidebar-bg); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }

.btn-primary {
  display: flex; align-items: center; gap: 0.375rem;
  padding: 0.5625rem 1rem; background: var(--color-sidebar-bg); color: #fff;
  border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer;
}
.btn-primary:hover { background: var(--color-btn-primary-hover); }
.btn-icon { width: 16px; height: 16px; }

.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 10px; overflow: hidden; }

.data-table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
.data-table th { background: var(--color-bg-page); padding: 0.625rem 0.875rem; font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); text-align: left; }
.data-table td { padding: 0.625rem 0.875rem; border-bottom: 1px solid var(--color-border); }
.data-table tr.row--alert td { background: #fff7ed; }

.td-ref { font-family: monospace; font-weight: 700; color: var(--color-sidebar-bg); font-size: 0.8125rem; }
.td-adresse { max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.dossier-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.chip { font-size: 0.6875rem; background: #dbeafe; color: #2563eb; padding: 2px 6px; border-radius: 4px; cursor: pointer; font-family: monospace; }
.chip:hover { background: #bfdbfe; }
.chip--more { background: #f1f5f9; color: var(--color-text-muted); cursor: default; }

.alert-pill { display: inline-flex; align-items: center; gap: 4px; font-size: 0.6875rem; font-weight: 700; background: var(--color-risk-high-bg); color: var(--color-risk-high); padding: 2px 7px; border-radius: 5px; }
.alert-icon { width: 11px; height: 11px; }

.btn-edit { font-size: 0.75rem; padding: 3px 10px; background: none; border: 1px solid var(--color-border); border-radius: 5px; cursor: pointer; }
.btn-edit:hover { border-color: var(--color-sidebar-bg); color: var(--color-sidebar-bg); }

/* Skeleton */
.skeleton-list { padding: 0.75rem 1.25rem; display: flex; flex-direction: column; gap: 0.75rem; }
.skeleton--row { height: 40px; background: #f1f5f9; border-radius: 7px; animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 3rem; color: var(--color-text-muted); }
.empty-icon-svg { width: 40px; height: 40px; stroke: var(--color-text-muted); }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 12px; padding: 1.5rem; width: 500px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); display: flex; flex-direction: column; gap: 1.125rem; }
.modal-title { font-size: 1.0625rem; font-weight: 800; color: var(--color-sidebar-bg); margin: 0; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.field-group { display: flex; flex-direction: column; gap: 0.25rem; }
.field-group--full { grid-column: 1 / -1; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.field-input { padding: 0.5625rem 0.75rem; border: 1px solid var(--color-border); border-radius: 7px; font-size: 0.875rem; width: 100%; }
.req { color: var(--color-risk-high); }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
.btn-ghost { padding: 0.5rem 1rem; background: none; border: 1px solid var(--color-border); border-radius: 7px; font-size: 0.875rem; cursor: pointer; }
.btn-primary-modal { display: flex; align-items: center; gap: 0.375rem; padding: 0.5rem 1.25rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 7px; font-size: 0.875rem; font-weight: 600; cursor: pointer; }
.btn-primary-modal:disabled { opacity: 0.5; cursor: not-allowed; }
.spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-msg { font-size: 0.8125rem; color: var(--color-risk-high); background: var(--color-risk-high-bg); border-radius: 6px; padding: 0.5rem 0.75rem; margin: 0; }

/* ANO-01 enrichissement */
.td-sub { font-size: 0.75rem; color: var(--color-text-secondary); margin-top: 2px; }
.alerts-col { display: flex; flex-direction: column; gap: 4px; }
.alert-pill--especes { background: #fef3c7; color: #92400e; }
.especes-block {
  font-size: 0.8125rem; font-weight: 600;
  background: #fff3cd; color: #7c4a03;
  border: 1px solid #f59e0b; border-radius: 7px;
  padding: 0.625rem 0.875rem;
}
.field-hint { font-size: 0.75rem; color: var(--color-text-secondary); }
.field-hint--warn { color: #c2410c; font-weight: 600; }
.field-input--warn { border-color: #f59e0b !important; background: #fffbeb; }
</style>
