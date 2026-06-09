<template>
  <div class="audit-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Journal d'audit</h1>
        <p class="page-subtitle">{{ total }} entrée{{ total !== 1 ? 's' : '' }} · lecture seule · immuable (NFR-6)</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <input v-model="filters.action" type="search" class="filter-input" placeholder="Filtrer par action…" @input="debouncedLoad" />
      <select v-model="filters.entity_type" class="filter-select" @change="loadPage(1)">
        <option value="">Tous les types</option>
        <option value="user">Utilisateur</option>
        <option value="dossier">Dossier</option>
        <option value="dos">DOS</option>
        <option value="alerte">Alerte</option>
        <option value="department">Département</option>
      </select>
      <input v-model="filters.user_id" type="search" class="filter-input" placeholder="Filtrer par ID utilisateur…" @input="debouncedLoad" />
      <button class="btn-ghost-sm" @click="clearFilters">Réinitialiser</button>
    </div>

    <!-- Table -->
    <div class="card table-card">
      <div v-if="loading" class="table-loading">Chargement…</div>
      <table v-else class="audit-table">
        <thead>
          <tr>
            <th>Horodatage</th>
            <th>Action</th>
            <th>Type</th>
            <th>Entité</th>
            <th>Utilisateur</th>
            <th>IP</th>
            <th>Détail</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in entries" :key="entry.id">
            <td class="td-ts">{{ formatTs(entry.timestamp_utc) }}</td>
            <td><span class="action-badge" :class="actionClass(entry.action)">{{ entry.action }}</span></td>
            <td class="td-mono">{{ entry.entity_type ?? '—' }}</td>
            <td class="td-mono td-id">{{ entry.entity_id ? entry.entity_id.slice(0, 8) + '…' : '—' }}</td>
            <td class="td-mono td-id" :title="entry.user_id ?? ''">{{ entry.user_id ? entry.user_id.slice(0, 8) + '…' : '—' }}</td>
            <td class="td-mono">{{ entry.ip ?? '—' }}</td>
            <td>
              <button v-if="entry.detail" class="detail-btn" @click="showDetail(entry)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              </button>
              <span v-else class="td-muted">—</span>
            </td>
          </tr>
          <tr v-if="entries.length === 0">
            <td colspan="6" class="empty-row">Aucune entrée</td>
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

    <!-- Detail modal -->
    <Teleport to="body">
      <div v-if="detailEntry" class="modal-overlay" @click.self="detailEntry = null">
        <div class="modal" role="dialog" aria-label="Détail de l'entrée">
          <div class="modal-header">
            <h2 class="modal-title">Détail — {{ detailEntry.action }}</h2>
            <button class="modal-close" @click="detailEntry = null">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="detail-body">
            <div class="detail-meta">
              <span class="meta-item"><strong>Horodatage</strong> {{ formatTs(detailEntry.timestamp_utc) }}</span>
              <span class="meta-item"><strong>IP</strong> {{ detailEntry.ip ?? '—' }}</span>
              <span class="meta-item"><strong>Type</strong> {{ detailEntry.entity_type ?? '—' }}</span>
              <span class="meta-item"><strong>Entité</strong> {{ detailEntry.entity_id ?? '—' }}</span>
            </div>
            <pre class="detail-json">{{ formatDetail(detailEntry.detail) }}</pre>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { auditService, type AuditLogEntry } from '@/services/audit'

const PAGE_SIZE = 50

const entries = ref<AuditLogEntry[]>([])
const total = ref(0)
const loading = ref(true)
const currentPage = ref(1)
const detailEntry = ref<AuditLogEntry | null>(null)

const filters = reactive({ action: '', entity_type: '', user_id: '' })

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

async function loadPage(page: number) {
  loading.value = true
  currentPage.value = page
  try {
    const res = await auditService.list({
      page,
      page_size: PAGE_SIZE,
      action: filters.action || undefined,
      entity_type: filters.entity_type || undefined,
      user_id: filters.user_id || undefined,
    })
    entries.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => loadPage(1), 350)
}

function clearFilters() {
  filters.action = ''
  filters.entity_type = ''
  filters.user_id = ''
  loadPage(1)
}

onMounted(() => loadPage(1))

function formatTs(iso: string): string {
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function formatDetail(raw: string | null): string {
  if (!raw) return ''
  try { return JSON.stringify(JSON.parse(raw), null, 2) } catch { return raw }
}

function showDetail(entry: AuditLogEntry) { detailEntry.value = entry }

function actionClass(action: string): string {
  if (action.includes('deactivate') || action.includes('unauthorized')) return 'action--danger'
  if (action.includes('create') || action.includes('reactivate'))       return 'action--success'
  if (action.includes('update') || action.includes('login'))            return 'action--info'
  return 'action--default'
}
</script>

<style scoped>
.audit-page { max-width: 1100px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }

.filter-bar { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }
.filter-input, .filter-select {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; color: var(--color-text-primary); background: var(--color-bg-card);
  outline: none; width: auto;
}
.filter-input { min-width: 220px; }
.filter-input:focus, .filter-select:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.btn-ghost-sm { padding: 0.5rem 0.875rem; background: none; border: 1px solid var(--color-border); border-radius: 7px; font-size: 0.8125rem; color: var(--color-text-secondary); cursor: pointer; }
.btn-ghost-sm:hover { border-color: var(--color-text-secondary); }

.table-card { padding: 0; overflow: hidden; }
.table-loading { padding: 3rem; text-align: center; color: var(--color-text-muted); font-size: 0.875rem; }
.audit-table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
.audit-table th { background: var(--color-bg-page); padding: 0.5rem 0.875rem; text-align: left; font-size: 0.7rem; font-weight: 600; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--color-border); }
.audit-table td { padding: 0.625rem 0.875rem; color: var(--color-text-primary); border-bottom: 1px solid var(--color-border); vertical-align: middle; }
.audit-table tr:last-child td { border-bottom: none; }
.audit-table tr:hover td { background: var(--color-bg-page); }

.td-ts { white-space: nowrap; color: var(--color-text-secondary); font-size: 0.75rem; }
.td-mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem; }
.td-id { color: var(--color-text-muted); }
.td-muted { color: var(--color-text-muted); }
.empty-row { text-align: center; color: var(--color-text-muted); padding: 2.5rem !important; }

.action-badge { display: inline-block; padding: 2px 8px; border-radius: 5px; font-size: 0.6875rem; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.action--danger  { background: var(--color-risk-high-bg);   color: var(--color-risk-high); }
.action--success { background: var(--color-risk-low-bg);    color: var(--color-risk-low); }
.action--info    { background: var(--color-status-en-analyse-bg); color: var(--color-status-en-analyse); }
.action--default { background: var(--color-bg-page); color: var(--color-text-secondary); border: 1px solid var(--color-border); }

.detail-btn { background: none; border: none; cursor: pointer; color: var(--color-text-muted); display: flex; padding: 2px; }
.detail-btn svg { width: 15px; height: 15px; }
.detail-btn:hover { color: var(--color-sidebar-bg); }

.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1rem; }
.page-btn { padding: 0.375rem 0.875rem; border: 1px solid var(--color-border); border-radius: 7px; background: var(--color-bg-card); cursor: pointer; font-size: 0.875rem; color: var(--color-text-primary); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-btn:not(:disabled):hover { border-color: var(--color-sidebar-bg); }
.page-info { font-size: 0.8125rem; color: var(--color-text-secondary); }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 1.5rem; }
.modal { background: var(--color-bg-card); border-radius: 12px; box-shadow: 0 8px 40px rgba(0,0,0,0.16); width: 100%; max-width: 560px; max-height: 80vh; overflow: hidden; display: flex; flex-direction: column; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--color-border); flex-shrink: 0; }
.modal-title { font-size: 0.9375rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.modal-close { background: none; border: none; cursor: pointer; color: var(--color-text-muted); display: flex; }
.modal-close svg { width: 18px; height: 18px; }
.detail-body { padding: 1.25rem 1.5rem; overflow-y: auto; }
.detail-meta { display: flex; flex-wrap: wrap; gap: 0.75rem 1.5rem; margin-bottom: 1rem; }
.meta-item { font-size: 0.8125rem; color: var(--color-text-secondary); }
.meta-item strong { color: var(--color-text-primary); margin-right: 0.25rem; }
.detail-json { background: var(--color-bg-page); border-radius: 7px; padding: 1rem; font-size: 0.75rem; line-height: 1.6; overflow-x: auto; margin: 0; color: var(--color-text-primary); font-family: 'JetBrains Mono', 'Fira Code', monospace; }
</style>
