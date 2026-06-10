<template>
  <div class="registres-view">
    <!-- Header -->
    <div class="rv-header">
      <div>
        <h1 class="rv-title">Registres Légaux</h1>
        <p class="rv-subtitle">8 registres LBC/FT — Ordonnance N°2023-875</p>
      </div>
      <div v-if="activeRegistre" class="rv-export-bar">
        <button class="btn-export" :disabled="loading" @click="exportRegistre('excel')">
          <span>⬇</span> Excel
        </button>
        <button class="btn-export" :disabled="loading" @click="exportRegistre('pdf')">
          <span>⬇</span> PDF
        </button>
      </div>
    </div>

    <div class="rv-body">
      <!-- Left: list of registres -->
      <aside class="rv-sidebar">
        <p v-if="loadingList" class="rv-loading">Chargement…</p>
        <div
          v-for="reg in registres"
          :key="reg.id"
          class="rv-reg-item"
          :class="{ active: activeRegistre?.id === reg.id }"
          @click="selectRegistre(reg)"
        >
          <div class="rv-reg-info">
            <span class="rv-reg-label">{{ reg.label }}</span>
            <span v-if="REGISTRE_DESCRIPTIONS[reg.id]" class="rv-reg-desc">{{ REGISTRE_DESCRIPTIONS[reg.id] }}</span>
          </div>
          <span v-if="reg.confidential" class="rv-badge-conf">Conf.</span>
        </div>

        <div class="rv-separator" />

        <!-- Reports section -->
        <p class="rv-section-title">Rapports PDF</p>
        <div
          v-for="rep in REPORT_TYPES"
          :key="rep.id"
          class="rv-reg-item rv-report-item"
          @click="downloadReport(rep.id)"
        >
          <span class="rv-reg-label">{{ rep.label }}</span>
          <span v-if="generatingReport === rep.id" class="rv-spinner-sm" />
        </div>
      </aside>

      <!-- Right: entries table -->
      <section class="rv-main">
        <template v-if="!activeRegistre">
          <div class="rv-empty">
            <span class="rv-empty-icon">📋</span>
            <p>Sélectionnez un registre pour consulter ses entrées.</p>
          </div>
        </template>

        <template v-else>
          <div class="rv-table-header">
            <h2 class="rv-reg-title">{{ activeRegistre.label }}</h2>
            <span class="rv-total">{{ total }} entrée{{ total !== 1 ? 's' : '' }}</span>
          </div>

          <p v-if="loading" class="rv-loading">Chargement…</p>
          <p v-else-if="error" class="rv-error">{{ error }}</p>

          <div v-else class="rv-table-wrap">
            <table class="rv-table">
              <thead>
                <tr>
                  <th>Horodatage</th>
                  <th>Action</th>
                  <th>Type entité</th>
                  <th>Entité ID</th>
                  <th>Utilisateur</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="entries.length === 0">
                  <td colspan="6" class="rv-no-data">
                    Aucune entrée pour l'instant — ce registre se remplira automatiquement
                    au fur et à mesure des opérations effectuées dans la plateforme.
                  </td>
                </tr>
                <tr v-for="e in entries" :key="e.id">
                  <td class="rv-mono">{{ formatDate(e.timestamp_utc) }}</td>
                  <td><span class="rv-action-badge">{{ e.action }}</span></td>
                  <td>{{ e.entity_type }}</td>
                  <td class="rv-mono rv-id">{{ e.entity_id }}</td>
                  <td class="rv-mono rv-id">{{ e.user_id }}</td>
                  <td class="rv-mono">{{ e.ip }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination -->
          <div v-if="totalPages > 1" class="rv-pagination">
            <button class="rv-page-btn" :disabled="page === 1" @click="changePage(page - 1)">‹</button>
            <span class="rv-page-info">Page {{ page }} / {{ totalPages }}</span>
            <button class="rv-page-btn" :disabled="page >= totalPages" @click="changePage(page + 1)">›</button>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { registresService, type RegistreInfo, type RegistreEntry } from '@/services/registres'

const PAGE_SIZE = 50

const REGISTRE_DESCRIPTIONS: Record<string, string> = {
  kyc:                    'Dossiers KYC ouverts dans la plateforme',
  alertes:                'Alertes LBC/FT générées (auto ou manuelles)',
  dossiers_risque:        'Dossiers bloqués ou à risque élevé',
  dos:                    'Déclarations d\'Opérations Suspectes — Art. 63',
  journal_actions:        'Toutes les actions système (piste d\'audit)',
  transactions_surveillees: 'Dossiers ayant déclenché un trigger T1–T5',
  mandats:                'Création et suivi des mandats',
  autorisations_dirigeant: 'Décisions WRK-09 Dirigeant sur dossiers PPE',
}

const REPORT_TYPES = [
  { id: 'conformite', label: 'Rapport de Conformité Périodique' },
  { id: 'audit',      label: 'Piste d\'Audit Complète' },
  { id: 'mandats',    label: 'Registre des Mandats Actifs' },
  { id: 'client',     label: 'Rapport Client (dossier complet)' },
] as const

const registres = ref<RegistreInfo[]>([])
const activeRegistre = ref<RegistreInfo | null>(null)
const entries = ref<RegistreEntry[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const loadingList = ref(false)
const error = ref('')
const generatingReport = ref<string | null>(null)

const totalPages = computed(() => Math.ceil(total.value / PAGE_SIZE))

onMounted(async () => {
  loadingList.value = true
  try {
    const res = await registresService.list()
    registres.value = res.registres
  } catch {
    error.value = 'Impossible de charger la liste des registres.'
  } finally {
    loadingList.value = false
  }
})

async function selectRegistre(reg: RegistreInfo) {
  activeRegistre.value = reg
  page.value = 1
  await loadEntries()
}

async function loadEntries() {
  if (!activeRegistre.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await registresService.getPage(activeRegistre.value.id, page.value, PAGE_SIZE)
    entries.value = res.items
    total.value = res.total
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? 'Erreur lors du chargement.'
  } finally {
    loading.value = false
  }
}

async function changePage(p: number) {
  page.value = p
  await loadEntries()
}

async function exportRegistre(format: 'pdf' | 'excel') {
  if (!activeRegistre.value) return
  loading.value = true
  try {
    const blob = await registresService.exportBlob(activeRegistre.value.id, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${activeRegistre.value.id}.${format === 'excel' ? 'xlsx' : 'pdf'}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    error.value = 'Erreur lors de l\'export.'
  } finally {
    loading.value = false
  }
}

async function downloadReport(reportType: string) {
  generatingReport.value = reportType
  try {
    const blob = await registresService.generateReport(reportType as any)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `rapport_${reportType}_${new Date().toISOString().slice(0, 10)}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    error.value = 'Erreur lors de la génération du rapport.'
  } finally {
    generatingReport.value = null
  }
}

function formatDate(iso: string): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-CI', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<style scoped>
.registres-view {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.rv-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.rv-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1b2b4b;
  margin: 0 0 0.2rem;
}

.rv-subtitle {
  font-size: 0.8rem;
  color: #64748b;
  margin: 0;
}

.rv-export-bar {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.btn-export {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  background: #1b2b4b;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.4rem 0.875rem;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-export:hover { background: #c9a227; }
.btn-export:disabled { opacity: 0.5; cursor: not-allowed; }

.rv-body {
  display: flex;
  gap: 1.25rem;
  flex: 1;
  min-height: 0;
}

/* ── Sidebar ── */
.rv-sidebar {
  width: 220px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.75rem 0.5rem;
  overflow-y: auto;
}

.rv-reg-item {
  padding: 0.5rem 0.75rem;
  border-radius: 7px;
  cursor: pointer;
  transition: background 0.12s;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.rv-reg-item:hover { background: #f1f5f9; }
.rv-reg-item.active { background: rgba(27, 43, 75, 0.08); }

.rv-reg-info {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  flex: 1;
  min-width: 0;
}

.rv-reg-label {
  font-size: 0.78rem;
  font-weight: 500;
  color: #1b2b4b;
  line-height: 1.3;
}

.rv-reg-desc {
  font-size: 0.68rem;
  color: #94a3b8;
  line-height: 1.2;
  white-space: normal;
}

.rv-badge-conf {
  font-size: 0.62rem;
  font-weight: 700;
  background: #fee2e2;
  color: #dc2626;
  padding: 1px 5px;
  border-radius: 99px;
  flex-shrink: 0;
}

.rv-separator {
  border-top: 1px solid #e2e8f0;
  margin: 0.75rem 0.5rem;
}

.rv-section-title {
  font-size: 0.68rem;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0 0.75rem;
  margin: 0 0 0.25rem;
}

.rv-report-item { color: #475569; }
.rv-report-item .rv-reg-label { color: #475569; }

.rv-spinner-sm {
  width: 10px;
  height: 10px;
  border: 2px solid #c9a227;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

/* ── Main content ── */
.rv-main {
  flex: 1;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.rv-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  gap: 0.75rem;
}

.rv-empty-icon { font-size: 2.5rem; }
.rv-empty p { font-size: 0.875rem; margin: 0; }

.rv-table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.rv-reg-title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #1b2b4b;
  margin: 0;
}

.rv-total {
  font-size: 0.78rem;
  color: #64748b;
  background: #f1f5f9;
  padding: 0.2rem 0.6rem;
  border-radius: 99px;
}

.rv-table-wrap {
  flex: 1;
  overflow: auto;
}

.rv-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.rv-table th {
  background: #f8fafc;
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.5rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  position: sticky;
  top: 0;
}

.rv-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  vertical-align: middle;
}

.rv-table tr:last-child td { border-bottom: none; }

.rv-mono { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.72rem; }
.rv-id { color: #94a3b8; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.rv-action-badge {
  background: #f1f5f9;
  color: #475569;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.rv-no-data {
  text-align: center;
  color: #94a3b8;
  padding: 2rem;
}

/* ── Pagination ── */
.rv-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 0.75rem;
  border-top: 1px solid #f1f5f9;
}

.rv-page-btn {
  background: none;
  border: 1px solid #e2e8f0;
  border-radius: 5px;
  width: 28px;
  height: 28px;
  cursor: pointer;
  font-size: 1rem;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rv-page-btn:hover:not(:disabled) { border-color: #1b2b4b; color: #1b2b4b; }
.rv-page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.rv-page-info { font-size: 0.8rem; color: #64748b; }

/* ── States ── */
.rv-loading { padding: 1rem 1.25rem; color: #94a3b8; font-size: 0.85rem; }
.rv-error { padding: 1rem 1.25rem; color: #dc2626; font-size: 0.85rem; }

@keyframes spin { to { transform: rotate(360deg); } }
</style>
