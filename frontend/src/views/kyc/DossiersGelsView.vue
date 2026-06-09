<template>
  <div class="gels-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Gel des Avoirs</h1>
        <p class="page-subtitle">Workflow 6 phases — Dossiers soumis à gel des avoirs (criblage sanctions)</p>
      </div>
    </div>

    <!-- Onglets -->
    <div class="tabs">
      <button class="tab" :class="{ 'tab--active': activeTab === 'actifs' }" @click="activeTab = 'actifs'">
        Actifs
        <span v-if="!loading && activeTab === 'actifs'" class="tab-count">{{ items.length }}</span>
      </button>
      <button class="tab" :class="{ 'tab--active': activeTab === 'historique' }" @click="switchToHistorique">
        Historique
        <span v-if="activeTab === 'historique' && !hLoading" class="tab-count">{{ hTotal }}</span>
      </button>
    </div>

    <!-- ═══════════════════════════ TAB ACTIFS ═══════════════════════════ -->
    <template v-if="activeTab === 'actifs'">
      <div class="filter-bar">
        <input v-model="search" type="search" class="filter-search" placeholder="Référence, client…" />
      </div>

      <div v-if="loading" class="loading-state">Chargement…</div>

      <div v-else-if="filtered.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        <p>Aucun dossier gelé</p>
        <span class="empty-sub">Aucun client n'est actuellement soumis à un gel des avoirs</span>
      </div>

      <div v-else class="gel-list">
        <div v-for="item in filtered" :key="item.id" class="gel-card">
          <div class="gel-card-header">
            <div class="gel-card-meta">
              <span class="ref-badge">{{ item.reference }}</span>
              <span class="type-tag">{{ item.type_client }}</span>
              <span v-if="item.niveau_risque" class="risk-badge" :class="`risk--${item.niveau_risque}`">{{ item.niveau_risque }}</span>
            </div>
            <div class="gel-card-actions">
              <button class="btn-link" @click="router.push({ name: 'kyc-detail', params: { id: item.id } })">
                Voir dossier →
              </button>
            </div>
          </div>

          <div class="phase-tracker">
            <div
              v-for="n in 6"
              :key="n"
              class="phase-step"
              :class="{
                'phase--done': n < (item.gel_phase || 1),
                'phase--active': n === (item.gel_phase || 1),
                'phase--pending': n > (item.gel_phase || 1),
              }"
            >
              <div class="phase-circle">
                <svg v-if="n < (item.gel_phase || 1)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" class="phase-icon">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span v-else>{{ n }}</span>
              </div>
              <div class="phase-label">{{ PHASES[n]?.short }}</div>
            </div>
            <div class="phase-connector" />
          </div>

          <div class="phase-current-info">
            <div class="phase-current-label">{{ PHASES[item.gel_phase || 1]?.label }}</div>
            <div class="phase-current-desc">{{ PHASES[item.gel_phase || 1]?.description }}</div>
            <div v-if="item.gel_notes" class="phase-notes">
              <span class="notes-icon">📝</span> {{ item.gel_notes }}
            </div>
          </div>

          <div v-if="isSupervisor" class="gel-card-footer">
            <div v-if="(item.gel_phase || 1) < 6" class="avancer-form">
              <input
                v-model="notesMap[item.id]"
                type="text"
                class="notes-input"
                :placeholder="PHASES[(item.gel_phase || 1) + 1]?.action || 'Notes…'"
              />
              <button
                class="btn-avancer"
                :disabled="advancing === item.id"
                @click="avancerPhase(item)"
              >
                <span v-if="advancing === item.id" class="spinner" />
                {{ advancing === item.id ? 'Avancement…' : `Passer à la phase ${(item.gel_phase || 1) + 1}` }}
              </button>
            </div>
            <div v-else class="phase-finale">
              <button class="btn-lever-gel" :disabled="advancing === item.id" @click="leverGel(item)">
                <span v-if="advancing === item.id" class="spinner" />
                Lever le gel (Art. 74 — décision AGERC)
              </button>
              <button class="btn-maintien-gel" :disabled="advancing === item.id" @click="maintienGel(item)">
                <span v-if="advancing === item.id" class="spinner" />
                Maintien définitif
              </button>
            </div>
          </div>

          <div v-if="errorMap[item.id]" class="error-msg">{{ errorMap[item.id] }}</div>
        </div>
      </div>
    </template>

    <!-- ═══════════════════════════ TAB HISTORIQUE ═══════════════════════════ -->
    <template v-else>
      <!-- Filtres -->
      <div class="filter-bar filter-bar--historique">
        <input v-model="hFilters.reference" type="search" class="filter-search" placeholder="Référence…" @input="debouncedLoad" />
        <select v-model="hFilters.decision" class="filter-select" @change="loadHistorique(1)">
          <option value="">Toutes décisions</option>
          <option value="leve">Levé</option>
          <option value="maintenu">Maintien définitif</option>
        </select>
        <select v-model="hFilters.niveau_risque" class="filter-select" @change="loadHistorique(1)">
          <option value="">Tous niveaux</option>
          <option value="FAIBLE">Faible</option>
          <option value="MOYEN">Moyen</option>
          <option value="ELEVE">Élevé</option>
        </select>
        <input v-model="hFilters.date_from" type="date" class="filter-date" @change="loadHistorique(1)" />
        <span class="date-sep">→</span>
        <input v-model="hFilters.date_to" type="date" class="filter-date" @change="loadHistorique(1)" />
        <button class="btn-export" :disabled="hItems.length === 0" @click="exportCSV">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Exporter CSV
        </button>
      </div>

      <div v-if="hLoading" class="loading-state">Chargement…</div>

      <div v-else-if="hItems.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <p>Aucun historique</p>
        <span class="empty-sub">Aucun gel résolu ne correspond aux filtres sélectionnés</span>
      </div>

      <template v-else>
        <div class="card table-card">
          <table class="h-table">
            <thead>
              <tr>
                <th>Référence</th>
                <th>Type</th>
                <th>Risque</th>
                <th>Décision</th>
                <th>Résolu par</th>
                <th>Date résolution</th>
                <th>Notes</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in hItems" :key="row.dossier_id + row.resolved_at" class="h-row">
                <td><span class="ref-badge">{{ row.reference }}</span></td>
                <td><span class="type-tag">{{ row.type_client }}</span></td>
                <td>
                  <span v-if="row.niveau_risque" class="risk-badge" :class="`risk--${row.niveau_risque}`">{{ row.niveau_risque }}</span>
                  <span v-else class="text-muted">—</span>
                </td>
                <td>
                  <span class="decision-badge" :class="row.decision === 'leve' ? 'decision--leve' : 'decision--maintenu'">
                    {{ row.decision === 'leve' ? 'Levé' : 'Maintien définitif' }}
                  </span>
                </td>
                <td class="cell-actor">{{ row.resolved_by || '—' }}</td>
                <td class="cell-date">{{ formatDate(row.resolved_at) }}</td>
                <td class="cell-notes">{{ row.notes || '—' }}</td>
                <td>
                  <button class="btn-detail" @click="openDetail(row.dossier_id)">Détail</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination Historique -->
        <div class="pagination">
          <button class="page-btn" :disabled="hPage === 1" @click="loadHistorique(hPage - 1)">‹</button>
          <span class="page-info">Page {{ hPage }} / {{ hTotalPages }} — {{ hTotal }} résultat{{ hTotal > 1 ? 's' : '' }}</span>
          <button class="page-btn" :disabled="hPage >= hTotalPages" @click="loadHistorique(hPage + 1)">›</button>
        </div>
      </template>
    </template>

    <!-- ═══════════════════════════ MODAL DÉTAIL ═══════════════════════════ -->
    <Teleport to="body">
      <div v-if="detailModal.open" class="modal-overlay" @click.self="detailModal.open = false">
        <div class="modal-dialog modal-dialog--detail">
          <div class="modal-header">
            <h3 class="modal-title">
              Historique gel — <span class="ref-badge">{{ detailModal.reference }}</span>
            </h3>
            <button class="modal-close" @click="detailModal.open = false">✕</button>
          </div>

          <div v-if="detailModal.loading" class="loading-state">Chargement…</div>

          <div v-else-if="detailModal.events.length === 0" class="empty-state" style="padding:2rem">
            <p>Aucun événement gel trouvé.</p>
          </div>

          <ol v-else class="timeline">
            <li
              v-for="(evt, i) in detailModal.events"
              :key="i"
              class="timeline-item"
              :class="{
                'timeline--final-leve': evt.action === 'gel.leve',
                'timeline--final-maintenu': evt.action === 'gel.maintien_definitif',
              }"
            >
              <div class="timeline-dot" />
              <div class="timeline-body">
                <div class="timeline-label">{{ evt.label }}</div>
                <div class="timeline-meta">
                  <span class="timeline-actor">{{ evt.actor || 'Système' }}</span>
                  <span class="timeline-date">{{ formatDate(evt.timestamp_utc) }}</span>
                </div>
                <div v-if="evt.notes" class="timeline-notes">{{ evt.notes }}</div>
              </div>
            </li>
          </ol>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/auth'

const router = useRouter()
const auth = useAuthStore()

// ── Types ─────────────────────────────────────────────────────────────────────

interface GelItem {
  id: string
  reference: string
  type_client: string
  niveau_risque: string | null
  gel_phase: number | null
  gel_notes: string | null
  created_at: string | null
  phase_info: { label?: string; description?: string; action?: string }
}

interface HistoriqueItem {
  dossier_id: string
  reference: string
  type_client: string
  niveau_risque: string | null
  decision: 'leve' | 'maintenu'
  resolved_at: string
  resolved_by: string | null
  notes: string | null
}

interface PhaseEvent {
  action: string
  label: string
  actor: string | null
  timestamp_utc: string
  notes: string | null
}

// ── Constants ─────────────────────────────────────────────────────────────────

const PHASES: Record<number, { label: string; short: string; description: string; action: string }> = {
  1: { label: 'Phase 1 — Identification', short: 'Identif.', description: 'Positif détecté au criblage sanctions. Initiation du gel des avoirs.', action: 'Confirmer la détection' },
  2: { label: 'Phase 2 — Vérification', short: 'Vérif.', description: 'Vérification de la concordance : faux positif ou match confirmé ?', action: 'Confirmer le match sanctions' },
  3: { label: 'Phase 3 — Exécution du gel', short: 'Exécution', description: 'Blocage effectif des avoirs et opérations du client.', action: 'Attester l\'exécution du gel' },
  4: { label: 'Phase 4 — Déclaration d\'Opération Suspecte', short: 'DOS', description: 'Transmission obligatoire à CENTIF-CI (Art. 74 Ordonnance 2023-875).', action: 'Confirmer la transmission à CENTIF-CI' },
  5: { label: 'Phase 5 — Suivi', short: 'Suivi', description: 'Surveillance continue des avoirs gelés et attente de la décision de l\'autorité.', action: 'Enregistrer un point de suivi' },
  6: { label: 'Phase 6 — Clôture', short: 'Clôture', description: 'Décision finale : levée du gel (autorisation AGERC/Parquet) ou maintien définitif.', action: 'Clôturer le gel des avoirs' },
}

const GEL_ROLES = ['responsable_conformite', 'notaire_principal', 'admin']

// ── Onglets ───────────────────────────────────────────────────────────────────

const activeTab = ref<'actifs' | 'historique'>('actifs')

function switchToHistorique() {
  activeTab.value = 'historique'
  if (hItems.value.length === 0 && !hLoading.value) loadHistorique(1)
}

// ── Onglet Actifs ─────────────────────────────────────────────────────────────

const items = ref<GelItem[]>([])
const loading = ref(true)
const search = ref('')
const advancing = ref<string | null>(null)
const notesMap = reactive<Record<string, string>>({})
const errorMap = reactive<Record<string, string>>({})

const isSupervisor = computed(() => auth.user && GEL_ROLES.includes(auth.user.role))

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return items.value
  return items.value.filter(d => d.reference.toLowerCase().includes(q))
})

async function load() {
  loading.value = true
  try {
    const r = await api.get('/gels')
    items.value = r.data.items
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function avancerPhase(item: GelItem) {
  advancing.value = item.id
  errorMap[item.id] = ''
  try {
    const r = await api.post(`/dossiers/${item.id}/gel/avancer`, { notes: notesMap[item.id] || null })
    const updated = items.value.find(i => i.id === item.id)
    if (updated) {
      updated.gel_phase = r.data.gel_phase
      updated.gel_notes = r.data.gel_notes
    }
    notesMap[item.id] = ''
  } catch (e: any) {
    errorMap[item.id] = e?.response?.data?.detail ?? 'Erreur lors de l\'avancement de phase.'
  } finally {
    advancing.value = null
  }
}

async function leverGel(item: GelItem) {
  advancing.value = item.id
  errorMap[item.id] = ''
  try {
    await api.delete(`/dossiers/${item.id}/gel`, { data: { notes: notesMap[item.id] || null } })
    items.value = items.value.filter(i => i.id !== item.id)
  } catch (e: any) {
    errorMap[item.id] = e?.response?.data?.detail ?? 'Erreur lors de la levée du gel.'
  } finally {
    advancing.value = null
  }
}

async function maintienGel(item: GelItem) {
  advancing.value = item.id
  errorMap[item.id] = ''
  try {
    await api.post(`/dossiers/${item.id}/gel/maintien`, { notes: notesMap[item.id] || null })
    items.value = items.value.filter(i => i.id !== item.id)
  } catch (e: any) {
    errorMap[item.id] = e?.response?.data?.detail ?? 'Erreur lors du maintien définitif.'
  } finally {
    advancing.value = null
  }
}

// ── Onglet Historique ─────────────────────────────────────────────────────────

const hItems = ref<HistoriqueItem[]>([])
const hLoading = ref(false)
const hTotal = ref(0)
const hPage = ref(1)
const PAGE_SIZE = 20
const hTotalPages = computed(() => Math.max(1, Math.ceil(hTotal.value / PAGE_SIZE)))

const hFilters = reactive({
  reference: '',
  decision: '',
  niveau_risque: '',
  date_from: '',
  date_to: '',
})

async function loadHistorique(page = 1) {
  hLoading.value = true
  hPage.value = page
  try {
    const params: Record<string, string | number> = { page, page_size: PAGE_SIZE }
    if (hFilters.reference) params.reference = hFilters.reference
    if (hFilters.decision) params.decision = hFilters.decision
    if (hFilters.niveau_risque) params.niveau_risque = hFilters.niveau_risque
    if (hFilters.date_from) params.date_from = hFilters.date_from
    if (hFilters.date_to) params.date_to = hFilters.date_to
    const r = await api.get('/gels/historique', { params })
    hItems.value = r.data.items
    hTotal.value = r.data.total
  } catch {
    hItems.value = []
    hTotal.value = 0
  } finally {
    hLoading.value = false
  }
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => loadHistorique(1), 350)
}

// ── Export CSV ────────────────────────────────────────────────────────────────

function exportCSV() {
  const headers = ['Référence', 'Type', 'Risque', 'Décision', 'Résolu par', 'Date résolution', 'Notes']
  const rows = hItems.value.map(r => [
    r.reference,
    r.type_client,
    r.niveau_risque ?? '',
    r.decision === 'leve' ? 'Levé' : 'Maintien définitif',
    r.resolved_by ?? '',
    formatDate(r.resolved_at),
    r.notes ?? '',
  ])
  const csv = [headers, ...rows].map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `historique_gels_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ── Modal Détail ──────────────────────────────────────────────────────────────

const detailModal = reactive({
  open: false,
  loading: false,
  reference: '',
  events: [] as PhaseEvent[],
})

async function openDetail(dossierId: string) {
  detailModal.open = true
  detailModal.loading = true
  detailModal.events = []
  detailModal.reference = hItems.value.find(r => r.dossier_id === dossierId)?.reference ?? dossierId
  try {
    const r = await api.get(`/gels/${dossierId}/phases`)
    detailModal.events = r.data.events
    detailModal.reference = r.data.reference
  } catch {
    detailModal.events = []
  } finally {
    detailModal.loading = false
  }
}

// ── Utilitaires ───────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

onMounted(load)
</script>

<style scoped>
.gels-page { display: flex; flex-direction: column; gap: 1.25rem; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }

/* ── Onglets ── */
.tabs { display: flex; gap: 0; border-bottom: 2px solid var(--color-border); }
.tab {
  padding: 0.5rem 1.25rem; background: none; border: none; cursor: pointer;
  font-size: 0.875rem; font-weight: 600; color: var(--color-text-secondary);
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  display: flex; align-items: center; gap: 0.375rem;
}
.tab--active { color: var(--color-sidebar-bg); border-bottom-color: var(--color-sidebar-bg); }
.tab-count {
  background: var(--color-bg-page); border: 1px solid var(--color-border);
  border-radius: 10px; padding: 1px 7px; font-size: 0.6875rem; font-weight: 700;
}
.tab--active .tab-count { background: var(--color-sidebar-bg); color: #fff; border-color: transparent; }

/* ── Filtres ── */
.filter-bar { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; }
.filter-bar--historique { align-items: center; }
.filter-search {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; color: var(--color-text-primary); background: var(--color-bg-card);
  outline: none; width: 180px; flex-shrink: 0;
}
.filter-search:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.filter-select {
  padding: 0.5rem 0.625rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; background: var(--color-bg-card); color: var(--color-text-primary);
  outline: none; cursor: pointer; width: 160px; flex-shrink: 0;
}
.filter-date {
  padding: 0.5rem 0.625rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; background: var(--color-bg-card); color: var(--color-text-primary);
  outline: none; cursor: pointer; width: 140px; flex-shrink: 0;
}
.filter-select:focus, .filter-date:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.date-sep { font-size: 0.75rem; color: var(--color-text-muted); flex-shrink: 0; }
.btn-export {
  display: flex; align-items: center; gap: 0.375rem;
  padding: 0.5rem 0.875rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; font-weight: 600; background: var(--color-bg-card);
  color: var(--color-text-primary); cursor: pointer; margin-left: auto; flex-shrink: 0;
}
.btn-export:hover:not(:disabled) { background: var(--color-bg-page); }
.btn-export:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-icon { width: 14px; height: 14px; }

.loading-state { text-align: center; padding: 3rem; color: var(--color-text-muted); }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 4rem 1rem; color: var(--color-text-muted); }
.empty-state svg { width: 40px; height: 40px; stroke: var(--color-border); }
.empty-state p { font-weight: 600; margin: 0; }
.empty-sub { font-size: 0.8125rem; text-align: center; }

/* ── Gel cards (actifs) ── */
.gel-list { display: flex; flex-direction: column; gap: 1rem; }
.gel-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 1.25rem;
  display: flex; flex-direction: column; gap: 1rem;
}
.gel-card-header { display: flex; align-items: center; justify-content: space-between; }
.gel-card-meta { display: flex; align-items: center; gap: 0.5rem; }
.ref-badge { font-family: monospace; font-weight: 700; color: var(--color-sidebar-bg); font-size: 0.875rem; }
.type-tag { background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 5px; padding: 2px 6px; font-size: 0.6875rem; font-weight: 700; color: var(--color-sidebar-bg); }
.risk-badge { border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 700; }
.risk--FAIBLE { color: var(--color-risk-low); background: var(--color-risk-low-bg); }
.risk--MOYEN  { color: var(--color-risk-medium); background: var(--color-risk-medium-bg); }
.risk--ELEVE  { color: var(--color-risk-high); background: var(--color-risk-high-bg); }

.btn-link { background: none; border: none; color: var(--color-sidebar-bg); font-size: 0.8125rem; cursor: pointer; font-weight: 600; }
.btn-link:hover { text-decoration: underline; }

/* Phase tracker */
.phase-tracker {
  position: relative;
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 0 0.25rem;
}
.phase-connector {
  position: absolute; top: 15px; left: 5%; right: 5%; height: 2px;
  background: var(--color-border); z-index: 0;
}
.phase-step {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  flex: 1; position: relative; z-index: 1;
}
.phase-circle {
  width: 30px; height: 30px; border-radius: 50%; border: 2px solid var(--color-border);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700; background: var(--color-bg-card);
}
.phase--done .phase-circle { background: #166534; border-color: #166534; color: #fff; }
.phase--done .phase-icon { width: 14px; height: 14px; stroke: #fff; }
.phase--active .phase-circle { background: var(--color-sidebar-bg); border-color: var(--color-sidebar-bg); color: #fff; }
.phase--pending .phase-circle { color: var(--color-text-muted); }
.phase-label { font-size: 0.625rem; color: var(--color-text-secondary); text-align: center; max-width: 60px; line-height: 1.2; }
.phase--active .phase-label { color: var(--color-sidebar-bg); font-weight: 700; }
.phase--done .phase-label { color: #166534; }

.phase-current-info {
  background: var(--color-bg-page);
  border-left: 3px solid var(--color-sidebar-bg);
  border-radius: 0 6px 6px 0;
  padding: 0.625rem 0.875rem;
  display: flex; flex-direction: column; gap: 0.25rem;
}
.phase-current-label { font-size: 0.8125rem; font-weight: 700; color: var(--color-sidebar-bg); }
.phase-current-desc { font-size: 0.75rem; color: var(--color-text-secondary); }
.phase-notes { font-size: 0.75rem; color: var(--color-text-primary); margin-top: 0.25rem; }
.notes-icon { font-style: normal; }

.gel-card-footer { display: flex; align-items: center; gap: 0.75rem; }
.avancer-form { display: flex; align-items: center; gap: 0.5rem; width: 100%; }
.notes-input {
  flex: 1; padding: 0.4375rem 0.625rem; border: 1px solid var(--color-border);
  border-radius: 6px; font-size: 0.8125rem;
}
.btn-avancer {
  display: flex; align-items: center; gap: 0.375rem;
  padding: 0.4375rem 0.875rem; background: var(--color-sidebar-bg); color: #fff;
  border: none; border-radius: 6px; font-size: 0.8125rem; font-weight: 600; cursor: pointer; white-space: nowrap;
}
.btn-avancer:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-lever-gel {
  display: flex; align-items: center; gap: 0.375rem;
  padding: 0.4375rem 0.875rem; background: #166534; color: #fff;
  border: none; border-radius: 6px; font-size: 0.8125rem; font-weight: 600; cursor: pointer;
}
.btn-lever-gel:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-maintien-gel {
  display: flex; align-items: center; gap: 0.375rem;
  padding: 0.4375rem 0.875rem; background: #92400e; color: #fff;
  border: none; border-radius: 6px; font-size: 0.8125rem; font-weight: 600; cursor: pointer;
}
.btn-maintien-gel:disabled { opacity: 0.5; cursor: not-allowed; }
.phase-finale { display: flex; align-items: center; gap: 0.5rem; }

.spinner { width: 12px; height: 12px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-msg { font-size: 0.8125rem; color: var(--color-risk-high); background: var(--color-risk-high-bg); border-radius: 6px; padding: 0.375rem 0.625rem; }

/* ── Tableau historique ── */
.table-card { padding: 0; overflow: hidden; }
.h-table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
.h-table th {
  background: var(--color-bg-page); padding: 0.5rem 0.875rem; text-align: left;
  font-size: 0.7rem; font-weight: 600; color: var(--color-text-secondary);
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid var(--color-border); white-space: nowrap;
}
.h-row { border-bottom: 1px solid var(--color-border); transition: background 0.1s; }
.h-row:last-child { border-bottom: none; }
.h-row:hover td { background: var(--color-bg-page); }
.h-table td { padding: 0.75rem 0.875rem; font-size: 0.8125rem; color: var(--color-text-primary); vertical-align: middle; }
.cell-actor { color: var(--color-text-secondary); white-space: nowrap; }
.cell-date { color: var(--color-text-secondary); white-space: nowrap; font-size: 0.75rem; }
.cell-notes { color: var(--color-text-muted); font-size: 0.75rem; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.text-muted { color: var(--color-text-muted); }

.decision-badge { border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 700; }
.decision--leve { color: #166534; background: #dcfce7; }
.decision--maintenu { color: #92400e; background: #fef3c7; }

.btn-detail {
  padding: 0.25rem 0.625rem; border: 1px solid var(--color-border); border-radius: 5px;
  font-size: 0.75rem; font-weight: 600; background: none; cursor: pointer;
  color: var(--color-sidebar-bg);
}
.btn-detail:hover { background: var(--color-bg-page); }

/* Pagination */
.pagination { display: flex; align-items: center; justify-content: center; gap: 0.75rem; padding: 0.5rem 0; }
.page-btn {
  padding: 0.25rem 0.625rem; border: 1px solid var(--color-border); border-radius: 6px;
  background: var(--color-bg-card); font-size: 1rem; cursor: pointer; color: var(--color-text-primary);
}
.page-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.page-info { font-size: 0.8125rem; color: var(--color-text-secondary); }

/* ── Modal détail ── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-dialog--detail {
  background: var(--color-bg-card); border-radius: 12px;
  width: 100%; max-width: 560px; max-height: 80vh; overflow-y: auto;
  display: flex; flex-direction: column; gap: 1rem; padding: 1.5rem;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.modal-header { display: flex; align-items: center; justify-content: space-between; }
.modal-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; display: flex; align-items: center; gap: 0.5rem; }
.modal-close { background: none; border: none; font-size: 1rem; cursor: pointer; color: var(--color-text-muted); padding: 0.25rem; }

/* Timeline */
.timeline { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0; position: relative; }
.timeline::before { content: ''; position: absolute; left: 11px; top: 12px; bottom: 12px; width: 2px; background: var(--color-border); }
.timeline-item {
  display: flex; gap: 0.875rem; padding: 0.5rem 0; position: relative;
}
.timeline-dot {
  width: 24px; height: 24px; border-radius: 50%; background: var(--color-bg-card);
  border: 2px solid var(--color-border); flex-shrink: 0; margin-top: 2px; position: relative; z-index: 1;
}
.timeline--final-leve .timeline-dot { background: #166534; border-color: #166534; }
.timeline--final-maintenu .timeline-dot { background: #92400e; border-color: #92400e; }
.timeline-body { display: flex; flex-direction: column; gap: 2px; }
.timeline-label { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); }
.timeline--final-leve .timeline-label { color: #166534; }
.timeline--final-maintenu .timeline-label { color: #92400e; }
.timeline-meta { display: flex; gap: 0.75rem; font-size: 0.75rem; color: var(--color-text-secondary); }
.timeline-notes { font-size: 0.75rem; color: var(--color-text-muted); margin-top: 2px; }
</style>