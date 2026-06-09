<template>
  <div class="sanctions-view">
    <div class="view-header">
      <div>
        <h1 class="page-title">Gestion des Sanctions & Criblage</h1>
        <p class="page-subtitle">Listes GIABA · BCEAO · OFAC · UE/CSDNU — Criblage automatique par similarité</p>
      </div>
      <button v-if="isAdmin" class="btn-primary" @click="openUploadModal">
        + Importer une liste
      </button>
    </div>

    <!-- Stale alert -->
    <div v-if="hasStale" class="stale-alert">
      ⚠ Une ou plusieurs listes de sanctions n'ont pas été mises à jour depuis plus de 95 jours. Mise à jour requise.
    </div>

    <!-- Lists table -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Listes actives ({{ listes.length }})</span>
        <button class="btn-icon" @click="loadListes" title="Actualiser">↻</button>
      </div>
      <div v-if="loading" class="loading-state">Chargement…</div>
      <table v-else-if="listes.length" class="sanctions-table">
        <thead>
          <tr>
            <th>Nom</th>
            <th>Type</th>
            <th>Entrées</th>
            <th>Activée le</th>
            <th>Âge (jours)</th>
            <th>Statut</th>
            <th v-if="isAdmin">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="liste in listes" :key="liste.id" :class="{ stale: liste.is_stale }">
            <td>{{ liste.nom }}</td>
            <td><span class="type-badge">{{ liste.type_liste }}</span></td>
            <td>{{ liste.total_entrees.toLocaleString() }}</td>
            <td>{{ formatDate(liste.activated_at) }}</td>
            <td :class="{ 'stale-days': liste.is_stale }">{{ liste.age_jours }}j</td>
            <td>
              <span v-if="liste.is_stale" class="badge badge-danger">Périmée</span>
              <span v-else class="badge badge-ok">Active</span>
            </td>
            <td v-if="isAdmin">
              <button
                class="btn-deactivate"
                :disabled="deactivatingId === liste.id"
                @click="confirmDeactivate(liste)"
              >
                {{ deactivatingId === liste.id ? '…' : 'Désactiver' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">Aucune liste de sanctions importée.</div>
    </div>

    <!-- Criblage manuel -->
    <div class="card" style="margin-top:1.25rem;">
      <div class="card-header">
        <span class="card-title">Criblage manuel</span>
      </div>
      <div class="criblage-form">
        <div class="criblage-identity">
          <div class="identity-row">
            <div class="field">
              <label class="form-label">Nom <span class="required">*</span></label>
              <input v-model="criblageNom" class="form-input" placeholder="ex. DIALLO" @keyup.enter="runCriblage" />
            </div>
            <div class="field">
              <label class="form-label">Prénom(s) <span class="required">*</span></label>
              <input v-model="criblagePrenoms" class="form-input" placeholder="ex. Ibrahim" @keyup.enter="runCriblage" />
            </div>
          </div>
          <div class="identity-row">
            <div class="field">
              <label class="form-label">Date de naissance <span class="hint">(recommandé — permet d'écarter les homonymes)</span></label>
              <input v-model="criblageDdn" class="form-input" type="date" />
            </div>
            <div class="field">
              <label class="form-label">Lieu de naissance <span class="hint">(utilisé si DDN absente)</span></label>
              <input v-model="criblageLieu" class="form-input" placeholder="ex. BOUAKE" />
            </div>
          </div>
        </div>
        <div class="seuil-row">
          <label class="form-label">Seuil de similarité :</label>
          <input
            v-model.number="criblageThreshold"
            type="range" min="0" max="100" step="5"
            class="seuil-slider"
            :style="`--fill: ${criblageThreshold}%`"
          />
          <span>{{ criblageThreshold }}%</span>
        </div>
        <button class="btn-primary" :disabled="!criblageNom.trim() || !criblagePrenoms.trim() || criblageRunning" @click="runCriblage">
          {{ criblageRunning ? 'Criblage en cours…' : 'Cribler' }}
        </button>
      </div>

      <!-- Results -->
      <div v-if="criblageResult" class="criblage-results">
        <div class="result-summary" :class="criblageResult.has_match ? 'match' : 'no-match'">
          <strong>{{ criblageResult.has_match ? '⚠ Correspondance détectée' : '✓ Aucune correspondance' }}</strong>
          — « {{ criblageResult.nom_crible }} »
        </div>
        <table v-if="criblageResult.results.length" class="results-table">
          <thead>
            <tr><th>Liste</th><th>Type</th><th>Score</th><th>Nom correspondant</th><th>Résultat</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in criblageResult.results" :key="r.liste" :class="r.niveau">
              <td>{{ r.liste }}</td>
              <td>{{ r.type_liste }}</td>
              <td>{{ r.score.toFixed(1) }}%</td>
              <td>{{ r.nom_correspondant ?? '—' }}</td>
              <td>
                <span class="badge" :class="niveauBadgeClass(r.niveau)">{{ niveauLabel(r.niveau) }}</span>
                <span v-if="r.ddn_detail" class="ddn-hint">{{ ddnDetailLabel(r.ddn_detail) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Upload Modal -->
    <div v-if="uploadModal.visible" class="modal-overlay" @click.self="uploadModal.visible = false">
      <div class="modal">
        <h2 class="modal-title">Importer une liste de sanctions</h2>
        <div class="field-group">
          <div class="field">
            <label class="form-label">Nom de la liste</label>
            <input v-model="uploadModal.nom" class="form-input" placeholder="ex. GIABA 2026-Q1" autocomplete="off" />
          </div>
          <div class="field">
            <label class="form-label">Type</label>
            <select v-model="uploadModal.type_liste" class="form-input">
              <option value="GIABA">GIABA</option>
              <option value="BCEAO">BCEAO</option>
              <option value="OFAC">OFAC</option>
              <option value="UE_CSDNU">UE / CSDNU</option>
              <option value="AUTRE">Autre</option>
            </select>
          </div>
          <div class="field">
            <label class="form-label">Fichier CSV, PDF ou HTML (liste native acceptée)</label>
            <input type="file" accept=".csv,.pdf,.html,.htm" @change="onFileChange" />
          </div>
        </div>
        <div v-if="uploadModal.warning" class="warning-msg">⚠️ {{ uploadModal.warning }}</div>
        <div v-if="uploadModal.error" class="error-msg">{{ uploadModal.error }}</div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="uploadModal.visible = false">Annuler</button>
          <button
            class="btn-primary"
            :disabled="!uploadModal.nom || !uploadModal.file || uploadModal.loading"
            @click="submitUpload"
          >
            {{ uploadModal.loading ? 'Import en cours…' : 'Importer' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { revisionsService, type ListeSanctions, type CriblageResponse } from '@/services/revisions'

const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')
const listes = ref<ListeSanctions[]>([])
const loading = ref(false)
const hasStale = computed(() => listes.value.some(l => l.is_stale))

const deactivatingId = ref<string | null>(null)

async function confirmDeactivate(liste: ListeSanctions) {
  if (!confirm(`Désactiver « ${liste.nom} » ? Elle ne sera plus utilisée pour le criblage.`)) return
  deactivatingId.value = liste.id
  try {
    await revisionsService.deactivateSanctions(liste.id)
    await loadListes()
  } catch {
    alert('Erreur lors de la désactivation.')
  } finally {
    deactivatingId.value = null
  }
}

const criblageNom = ref('')
const criblagePrenoms = ref('')
const criblageDdn = ref('')
const criblageLieu = ref('')
const criblageThreshold = ref(85)
const criblageRunning = ref(false)
const criblageResult = ref<CriblageResponse | null>(null)

const uploadModal = ref({
  visible: false,
  nom: '',
  type_liste: 'GIABA',
  file: null as File | null,
  error: '',
  warning: '',
  loading: false,
})

function openUploadModal() {
  uploadModal.value = { visible: true, nom: '', type_liste: 'GIABA', file: null, error: '', warning: '', loading: false }
}

async function loadListes() {
  loading.value = true
  try {
    const resp = await revisionsService.listSanctions()
    listes.value = resp.items
  } finally {
    loading.value = false
  }
}

async function runCriblage() {
  if (!criblageNom.value.trim() || !criblagePrenoms.value.trim()) return
  criblageRunning.value = true
  criblageResult.value = null
  const nomComplet = `${criblageNom.value.trim()} ${criblagePrenoms.value.trim()}`
  try {
    criblageResult.value = await revisionsService.cribler(nomComplet, {
      dateNaissance: criblageDdn.value || undefined,
      lieuNaissance: criblageLieu.value || undefined,
      seuil: criblageThreshold.value,
    })
  } finally {
    criblageRunning.value = false
  }
}

function niveauBadgeClass(niveau: string): string {
  if (niveau === 'match') return 'badge-danger'
  if (niveau === 'warning') return 'badge-warning'
  return 'badge-ok'
}

function niveauLabel(niveau: string): string {
  if (niveau === 'match') return 'Correspondance'
  if (niveau === 'warning') return 'À vérifier'
  return 'OK'
}

function ddnDetailLabel(detail: string | null): string {
  if (!detail) return ''
  const labels: Record<string, string> = {
    ddn_confirmee: '· DDN confirmée',
    annee_seule: '· Année seule',
    homonymie_confirmee: '· Homonyme écarté',
    ddn_absente_liste: '· DDN absente de la liste',
  }
  return labels[detail] ?? ''
}

function onFileChange(e: Event) {
  uploadModal.value.file = (e.target as HTMLInputElement).files?.[0] ?? null
}

async function submitUpload() {
  const m = uploadModal.value
  if (!m.nom || !m.file) return
  m.loading = true
  m.error = ''
  try {
    const result = await revisionsService.uploadSanctions(m.nom, m.type_liste, m.file)
    m.warning = result?.warning ?? ''
    if (!m.warning) m.visible = false
    await loadListes()
  } catch (e: any) {
    m.error = e.response?.data?.detail ?? 'Erreur lors de l\'import.'
  } finally {
    m.loading = false
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-CI', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

onMounted(loadListes)
</script>

<style scoped>
.sanctions-view { padding: 0; max-width: 1100px; margin: 0 auto; }
.view-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
.page-title { font-size: 1.375rem; font-weight: 700; color: #1b2b4b; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.85rem; color: #64748b; margin: 0; }

.stale-alert {
  background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5;
  border-radius: 6px; padding: 0.75rem 1rem; font-size: 0.875rem; font-weight: 600;
  margin-bottom: 1.25rem;
}

.card { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }
.card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.875rem 1.25rem; border-bottom: 1px solid #e2e8f0; background: #f8fafc;
}
.card-title { font-weight: 700; color: #1b2b4b; font-size: 0.95rem; }
.btn-icon { background: none; border: none; cursor: pointer; font-size: 1.1rem; color: #64748b; }

.sanctions-table, .results-table {
  width: 100%; border-collapse: collapse; font-size: 0.875rem;
}
.sanctions-table th, .results-table th {
  background: #f8fafc; padding: 0.6rem 1rem; text-align: left;
  font-size: 0.75rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
}
.sanctions-table td, .results-table td {
  padding: 0.65rem 1rem; border-top: 1px solid #f1f5f9;
}
.sanctions-table tr.stale td { background: #fff5f5; }
.results-table tr.match td { background: #fff5f5; }
.stale-days { color: #dc2626; font-weight: 700; }

.type-badge {
  background: #dbeafe; color: #1d4ed8; font-size: 0.7rem; font-weight: 700;
  padding: 0.1rem 0.5rem; border-radius: 99px;
}
.badge { font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 99px; }
.badge-ok { background: #dcfce7; color: #15803d; }
.badge-danger { background: #fee2e2; color: #dc2626; }

.criblage-form { padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem; }
.criblage-identity { display: flex; flex-direction: column; gap: 0.75rem; }
.identity-row { display: flex; gap: 1rem; }
.identity-row .field { flex: 1; display: flex; flex-direction: column; gap: 0.3rem; }
.identity-row .form-input { width: 100%; box-sizing: border-box; }
.required { color: #dc2626; }
.hint { font-weight: 400; color: #94a3b8; font-size: 0.78rem; margin-left: 0.3rem; }
.badge-warning { background: #fef3c7; color: #92400e; }
.ddn-hint { font-size: 0.72rem; color: #64748b; margin-left: 0.4rem; }
.seuil-row { display: flex; align-items: center; gap: 0.75rem; font-size: 0.875rem; }
.seuil-slider {
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
  flex: 1;
  background: linear-gradient(
    to right,
    #1b2b4b 0%,
    #1b2b4b var(--fill),
    #e2e8f0 var(--fill),
    #e2e8f0 100%
  );
}
.seuil-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: #1b2b4b;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  cursor: pointer;
}
.seuil-slider::-moz-range-thumb {
  width: 16px; height: 16px;
  border-radius: 50%;
  background: #1b2b4b;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  cursor: pointer;
}
.form-input { border: 1px solid #cbd5e1; border-radius: 6px; padding: 0.5rem 0.75rem; font-size: 0.9rem; }
.form-label { font-size: 0.875rem; font-weight: 600; color: #374151; }

.criblage-results { padding: 0 1.25rem 1.25rem; }
.result-summary {
  padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.9rem; margin-bottom: 1rem;
}
.result-summary.match { background: #fee2e2; color: #dc2626; }
.result-summary.no-match { background: #dcfce7; color: #15803d; }

.empty-state { padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.9rem; }
.loading-state { padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.9rem; }
.btn-deactivate {
  background: none; border: 1px solid #fca5a5; color: #dc2626; border-radius: 5px;
  padding: 0.2rem 0.6rem; font-size: 0.75rem; font-weight: 600; cursor: pointer;
}
.btn-deactivate:hover:not(:disabled) { background: #fee2e2; }
.btn-deactivate:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-primary {
  background: #1b2b4b; color: #fff; border: none; border-radius: 6px;
  padding: 0.5rem 1.1rem; font-size: 0.875rem; font-weight: 600; cursor: pointer;
}
.btn-primary:hover { background: #c9a227; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary {
  background: #f1f5f9; color: #1b2b4b; border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 0.5rem 1rem; font-size: 0.875rem; cursor: pointer;
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal { background: #fff; border-radius: 12px; padding: 1.75rem 2rem; width: 520px; max-width: 95vw; }
.modal-title { font-size: 1.1rem; font-weight: 700; color: #1b2b4b; margin: 0 0 1.25rem; }
.field-group { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.35rem; }
.warning-msg { color: #92400e; background: #fffbeb; border: 1px solid #fcd34d; border-radius: 6px; padding: 0.5rem 0.75rem; font-size: 0.85rem; margin-bottom: 0.5rem; }
.error-msg { color: #dc2626; font-size: 0.85rem; margin: 0.5rem 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.25rem; }
</style>
