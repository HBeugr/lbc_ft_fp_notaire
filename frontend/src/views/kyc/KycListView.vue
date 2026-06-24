<template>
  <div class="kyc-list-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Dossiers KYC</h1>
        <p class="page-subtitle">{{ total }} dossier{{ total !== 1 ? 's' : '' }}</p>
      </div>
      <button class="btn-primary" @click="router.push({ name: 'kyc-new' })">
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Nouveau dossier
      </button>
    </div>

    <!-- Onglets Tous / Mes dossiers (superviseur uniquement) -->
    <div v-if="auth.isSupervisor" class="tabs-nav">
      <button class="tabs-nav-item" :class="{ 'tabs-nav-item--active': !mine }" @click="setMine(false)">Tous les dossiers</button>
      <button class="tabs-nav-item" :class="{ 'tabs-nav-item--active': mine }" @click="setMine(true)">Mes dossiers</button>
    </div>

    <!-- Filter bar -->
    <div class="filter-bar">
      <select v-model="filterStatut" class="filter-select" @change="loadPage(1)">
        <option value="">Tous les statuts</option>
        <option v-for="(label, val) in STATUT_LABELS" :key="val" :value="val">{{ label }}</option>
      </select>
      <select v-model="filterClassification" class="filter-select" @change="loadPage(1)">
        <option value="">Tous les risques</option>
        <option value="FAIBLE">Faible</option>
        <option value="MOYEN">Moyen</option>
        <option value="ELEVE">Élevé</option>
      </select>
      <input v-model="search" type="search" class="filter-search" placeholder="Référence, client…" />
    </div>

    <!-- Table -->
    <div class="card table-card">
      <div v-if="loading" class="table-loading">Chargement…</div>
      <table v-else class="dossiers-table">
        <thead>
          <tr>
            <th>Référence</th>
            <th>Type</th>
            <th>Client</th>
            <th>Opération</th>
            <th>Statut</th>
            <th>Risque</th>
            <th>Assignation</th>
            <th>Créé le</th>
            <th class="th-actions">Accès</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="d in filteredDossiers"
            :key="d.id"
            class="table-row"
            @click="router.push({ name: 'kyc-detail', params: { id: d.id } })"
          >
            <td class="td-ref">{{ d.reference }}</td>
            <td><span class="type-tag">{{ d.type_client }}</span></td>
            <td class="td-client">{{ clientName(d) }}</td>
            <td class="td-op">{{ OPERATION_LABELS[d.type_operation] ?? d.type_operation }}</td>
            <td>
              <span class="statut-badge" :class="`statut--${d.statut}`">
                {{ STATUT_LABELS[d.statut] ?? d.statut }}
              </span>
            </td>
            <td>
              <span v-if="d.classification" class="risk-badge" :class="`risk--${d.classification}`">
                {{ d.classification }}
              </span>
              <span v-else class="td-muted">—</span>
            </td>
            <td>
              <span v-if="d.assigned_to" class="assign-chip">{{ d.assigned_to_name || '—' }}</span>
              <span v-else class="td-muted">Non assigné</span>
            </td>
            <td class="td-date">{{ formatDate(d.created_at) }}</td>
            <td class="td-actions">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="row-arrow"><polyline points="9 18 15 12 9 6"/></svg>
            </td>
          </tr>
          <tr v-if="filteredDossiers.length === 0">
            <td colspan="9" class="empty-row">
              <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                <p>Aucun dossier KYC</p>
                <button class="btn-primary" style="margin-top:0.5rem;font-size:0.8125rem;" @click="router.push({ name: 'kyc-new' })">Créer un dossier</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="pagination">
      <button class="page-btn" :disabled="currentPage === 1" @click="loadPage(currentPage - 1)">←</button>
      <span class="page-info">Page {{ currentPage }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="currentPage === totalPages" @click="loadPage(currentPage + 1)">→</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { dossiersService, type DossierOut, TYPE_OPERATION_LABELS } from '@/services/dossiers'

const router = useRouter()
const auth = useAuthStore()
const PAGE_SIZE = 10
const dossiers = ref<DossierOut[]>([])
const total = ref(0)
const loading = ref(true)
const currentPage = ref(1)
const filterStatut = ref('')
const filterClassification = ref('')
const mine = ref(false)
const search = ref('')

function setMine(v: boolean) {
  mine.value = v
  loadPage(1)
}

const OPERATION_LABELS: Record<string, string> = TYPE_OPERATION_LABELS

const STATUT_LABELS: Record<string, string> = {
  brouillon:               'Brouillon',
  en_analyse:              'En analyse',
  vigilance_renforcee:     'Vigilance renforcée',
  valide:                  'Validé',
  actif:                   'Actif',
  actif_sous_surveillance: 'Sous surveillance',
  bloque:                  'Bloqué',
  traite:                  'Traité',
  resilie:                 'Résilié',
  cloture:                 'Clôturé',
  archive:                 'Archivé',
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

const filteredDossiers = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return dossiers.value
  return dossiers.value.filter(d =>
    d.reference.toLowerCase().includes(q) ||
    clientName(d).toLowerCase().includes(q)
  )
})

function clientName(d: DossierOut): string {
  if (d.kyc_pp?.nom) return `${d.kyc_pp.nom} ${d.kyc_pp.prenoms ?? ''}`.trim()
  if (d.kyc_pm?.denomination_sociale) return d.kyc_pm.denomination_sociale
  return '—'
}

function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d.getTime()) ? '—' : d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

async function loadPage(page: number) {
  loading.value = true
  currentPage.value = page
  try {
    const res = await dossiersService.list({
      page,
      page_size: PAGE_SIZE,
      statut: filterStatut.value || undefined,
      classification: filterClassification.value || undefined,
      mine: mine.value || undefined,
      search: search.value.trim() || undefined,
    })
    dossiers.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// Recherche serveur (référence + nom client) avec debounce — couvre tous les
// dossiers, pas seulement la page courante.
let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadPage(1), 300)
})

onMounted(() => loadPage(1))
</script>

<style scoped>
.kyc-list-page { max-width: 1100px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }
.btn-icon { width: 14px; height: 14px; margin-right: 0.375rem; vertical-align: middle; }

.tabs-nav { display: flex; gap: 0.25rem; margin-bottom: 1rem; border-bottom: 1px solid var(--color-border); }
.tabs-nav-item { padding: 0.5rem 0.875rem; background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; font-size: 0.8125rem; font-weight: 600; color: var(--color-text-secondary); }
.tabs-nav-item--active { color: var(--color-sidebar-bg); border-bottom-color: var(--color-sidebar-bg); }
.assign-chip { font-size: 0.7rem; font-weight: 600; color: var(--color-text-secondary); background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 5px; padding: 1px 7px; }

.filter-bar { display: flex; gap: 0.75rem; margin-bottom: 1rem; }
.filter-select, .filter-search {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; color: var(--color-text-primary); background: var(--color-bg-card); outline: none; width: auto;
}
.filter-select:focus, .filter-search:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.filter-search { min-width: 220px; }

.table-card { padding: 0; overflow: hidden; }
.table-loading { padding: 3rem; text-align: center; color: var(--color-text-muted); font-size: 0.875rem; }
.dossiers-table { width: 100%; border-collapse: collapse; }
.dossiers-table th { background: var(--color-bg-page); padding: 0.5rem 0.875rem; text-align: left; font-size: 0.7rem; font-weight: 600; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--color-border); }
.dossiers-table td { padding: 0.75rem 0.875rem; font-size: 0.8125rem; color: var(--color-text-primary); border-bottom: 1px solid var(--color-border); vertical-align: middle; }
.dossiers-table tr:last-child td { border-bottom: none; }
.table-row { cursor: pointer; transition: background 0.1s; }
.table-row:hover td { background: var(--color-bg-page); }
.th-actions, .td-actions { text-align: right; }
.td-ref { font-family: monospace; font-weight: 600; font-size: 0.8125rem; }
.td-client { font-weight: 500; }
.td-op { font-size: 0.75rem; color: var(--color-text-secondary); }
.td-date { font-size: 0.75rem; color: var(--color-text-secondary); white-space: nowrap; }
.td-muted { color: var(--color-text-muted); }
.row-arrow { width: 14px; height: 14px; color: var(--color-text-muted); }

.type-tag { background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 5px; padding: 2px 6px; font-size: 0.6875rem; font-weight: 700; color: var(--color-sidebar-bg); }

/* Statut badges */
.statut-badge { display: inline-block; border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.statut--brouillon               { color: var(--color-status-brouillon); background: var(--color-status-brouillon-bg); }
.statut--en_analyse              { color: var(--color-status-en-analyse); background: var(--color-status-en-analyse-bg); }
.statut--vigilance_renforcee     { color: var(--color-status-vigilance); background: var(--color-status-vigilance-bg); }
.statut--valide                  { color: var(--color-status-valide); background: var(--color-status-valide-bg); }
.statut--actif                   { color: var(--color-status-valide); background: var(--color-status-valide-bg); }
.statut--actif_sous_surveillance { color: var(--color-status-vigilance); background: var(--color-status-vigilance-bg); }
.statut--bloque                  { color: var(--color-status-bloque); background: var(--color-status-bloque-bg); }
.statut--traite                  { color: var(--color-status-traite); background: var(--color-status-traite-bg); }
.statut--resilie, .statut--cloture, .statut--archive { color: var(--color-status-cloture); background: var(--color-status-cloture-bg); }

/* Risk badges — palette verrouillée */
.risk-badge { display: inline-block; border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 700; }
.risk--FAIBLE { color: var(--color-risk-low);    background: var(--color-risk-low-bg); }
.risk--MOYEN  { color: var(--color-risk-medium); background: var(--color-risk-medium-bg); }
.risk--ELEVE  { color: var(--color-risk-high);   background: var(--color-risk-high-bg); }

.empty-row { padding: 0 !important; }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 3rem 1rem; color: var(--color-text-muted); }
.empty-state svg { width: 40px; height: 40px; stroke: var(--color-border); }
.empty-state p { font-size: 0.875rem; margin: 0; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1rem; }
.page-btn { padding: 0.375rem 0.875rem; border: 1px solid var(--color-border); border-radius: 7px; background: var(--color-bg-card); cursor: pointer; font-size: 0.875rem; }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-btn:not(:disabled):hover { border-color: var(--color-sidebar-bg); }
.page-info { font-size: 0.8125rem; color: var(--color-text-secondary); }
</style>
