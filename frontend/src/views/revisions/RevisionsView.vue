<template>
  <div class="revisions-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Révisions Périodiques</h1>
        <p class="page-subtitle">{{ stats.en_attente }} révision(s) à venir dans les 30 jours</p>
      </div>
      <div class="header-actions">
        <select v-model="filters.statut" class="filter-select" @change="load">
          <option value="">Tous statuts</option>
          <option value="PLANIFIEE">Planifiée</option>
          <option value="EN_COURS">En cours</option>
          <option value="EN_RETARD">En retard</option>
          <option value="COMPLETEE">Complétée</option>
        </select>
        <select v-model="filters.niveau_risque" class="filter-select" @change="load">
          <option value="">Tous niveaux</option>
          <option value="FAIBLE">FAIBLE</option>
          <option value="MOYEN">MOYEN</option>
          <option value="ELEVE">ÉLEVÉ</option>
        </select>
      </div>
    </div>

    <!-- Escalade J-30 warning -->
    <div v-if="echeancesProches.length > 0" class="escalade-banner">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="banner-icon">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      <div>
        <p class="banner-title">{{ echeancesProches.length }} dossier(s) arrivent à échéance dans ≤ 30 jours</p>
        <p class="banner-desc">Des alertes J-30 ont été générées automatiquement et assignées au Responsable conformité.</p>
      </div>
    </div>

    <!-- Escalade stages -->
    <div class="escalade-grid">
      <div v-for="stage in STAGES" :key="stage.key" class="stage-card" :class="`stage-card--${stage.color}`">
        <div class="stage-icon">{{ stage.icon }}</div>
        <div class="stage-label">{{ stage.label }}</div>
        <div class="stage-count">{{ stageCount(stage.key) }}</div>
      </div>
    </div>

    <!-- Révisions table -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Planning des révisions ({{ revisions.length }})</h2>
      </div>

      <div v-if="loading" class="skeleton-list">
        <div v-for="i in 8" :key="i" class="skeleton skeleton--row" />
      </div>

      <div v-else-if="revisions.length === 0" class="empty-state">
        <svg class="empty-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>
          <line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
        <p>Aucune révision ne correspond aux filtres.</p>
      </div>

      <table v-else class="data-table">
        <thead>
          <tr>
            <th>Dossier</th>
            <th>Client</th>
            <th>Risque</th>
            <th>Fréquence</th>
            <th>Prochaine révision</th>
            <th>Statut</th>
            <th>Jalon escalade</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="rev in revisions" :key="rev.id" :class="rowClass(rev)">
            <td class="td-ref">
              <a class="dossier-link" @click="goToDossier(rev.dossier_id)">{{ rev.dossier_reference }}</a>
            </td>
            <td>{{ rev.client_nom }}</td>
            <td>
              <span class="risk-badge" :class="riskClass(rev.niveau_risque)">{{ rev.niveau_risque }}</span>
            </td>
            <td class="td-freq">{{ freqLabel(rev.frequence) }}</td>
            <td :class="{ 'td-urgent': isUrgent(rev) }">{{ formatDate(rev.prochaine_revision) }}</td>
            <td>
              <span class="status-pill" :class="statusClass(rev.statut)">{{ rev.statut.replace('_', ' ') }}</span>
            </td>
            <td>
              <span v-if="rev.jalon_actif" class="jalon-badge" :class="jalonClass(rev.jalon_actif)">
                J+{{ rev.jalon_actif }}
              </span>
              <span v-else class="text-muted">—</span>
            </td>
            <td>
              <button
                v-if="rev.statut !== 'COMPLETEE'"
                class="btn-initier"
                @click="initierRevision(rev)"
              >
                Initier
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal — initier révision -->
    <div v-if="revisionEnCours" class="modal-overlay" @click.self="revisionEnCours = null">
      <div class="modal">
        <h3 class="modal-title">Initier la révision — {{ revisionEnCours.dossier_reference }}</h3>
        <p class="modal-desc">
          Confirmer le démarrage de la révision périodique pour ce dossier.
          Cela arrêtera le workflow d'escalade automatique.
        </p>
        <div class="field-group">
          <label class="field-label">Observations (optionnel)</label>
          <textarea v-model="revisionNote" class="field-input field-textarea" rows="3" placeholder="Notes de révision…" />
        </div>
        <div class="modal-actions">
          <button class="btn-ghost" @click="revisionEnCours = null">Annuler</button>
          <button class="btn-primary" :disabled="saving" @click="confirmerRevision">
            <span v-if="saving" class="spinner" />
            Confirmer la révision
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { revisionsService } from '@/services/revisions'

const router = useRouter()

interface Revision {
  id: string
  dossier_id: string
  dossier_reference: string
  client_nom: string
  niveau_risque: string
  frequence: string
  prochaine_revision: string
  statut: string
  jalon_actif: number | null
}

const STAGES = [
  { key: 0,   label: 'À venir J-30', icon: '📅', color: 'info' },
  { key: 30,  label: 'Relance J+30', icon: '📨', color: 'warning' },
  { key: 60,  label: 'Escalade RC J+60', icon: '⚠️', color: 'orange' },
  { key: 90,  label: 'Vigilance J+90', icon: '🔒', color: 'high' },
  { key: 120, label: 'Blocage J+120', icon: '🚫', color: 'critical' },
]

const revisions = ref<Revision[]>([])
const loading   = ref(true)
const saving    = ref(false)
const filters   = ref({ statut: '', niveau_risque: '' })
const revisionEnCours = ref<Revision | null>(null)
const revisionNote    = ref('')

const stats = computed(() => ({
  en_attente: revisions.value.filter(r => {
    const d = new Date(r.prochaine_revision)
    const diff = (d.getTime() - Date.now()) / 86400000
    return diff <= 30 && r.statut !== 'COMPLETEE'
  }).length,
}))

const echeancesProches = computed(() =>
  revisions.value.filter(r => {
    const diff = (new Date(r.prochaine_revision).getTime() - Date.now()) / 86400000
    return diff <= 30 && r.statut === 'PLANIFIEE'
  })
)

function stageCount(jalon: number) {
  return revisions.value.filter(r => r.jalon_actif === jalon).length
}

async function load() {
  loading.value = true
  try {
    const resp = await revisionsService.list({
      statut: filters.value.statut || undefined,
      niveau_risque: filters.value.niveau_risque || undefined,
    })
    revisions.value = resp.items
  } finally {
    loading.value = false
  }
}

function goToDossier(id: string) { router.push({ name: 'kyc-detail', params: { id } }) }

function isUrgent(rev: Revision) {
  const diff = (new Date(rev.prochaine_revision).getTime() - Date.now()) / 86400000
  return diff <= 30
}

function formatDate(d: string) {
  return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(d))
}

function freqLabel(f: string) {
  const map: Record<string, string> = {
    FAIBLE: '5 ans', MOYEN: '3 ans', ELEVE: '2 ans', PPE: '3 ans (Art.29)', TRIGGER: '1 an',
  }
  return map[f] ?? f
}

function rowClass(rev: Revision) {
  return { 'row--urgent': rev.jalon_actif != null && rev.jalon_actif >= 90 }
}
function riskClass(n: string)    { return { 'risk--low': n === 'FAIBLE', 'risk--medium': n === 'MOYEN', 'risk--high': n === 'ELEVE' } }
function statusClass(s: string)  { return `status--${s.toLowerCase().replace('_', '-')}` }
function jalonClass(j: number)   { return j >= 90 ? 'jalon--critical' : j >= 60 ? 'jalon--warning' : 'jalon--info' }

function initierRevision(rev: Revision) {
  revisionEnCours.value = rev
  revisionNote.value = ''
}

async function confirmerRevision() {
  if (!revisionEnCours.value) return
  saving.value = true
  try {
    await revisionsService.initier(revisionEnCours.value.dossier_id, { note: revisionNote.value })
    revisionEnCours.value = null
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.revisions-page { display: flex; flex-direction: column; gap: 1.25rem; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; }
.page-title { font-size: 1.375rem; font-weight: 800; color: var(--color-sidebar-bg); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }
.header-actions { display: flex; gap: 0.5rem; }
.filter-select { padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 7px; font-size: 0.8125rem; background: #fff; }

/* Escalade banner */
.escalade-banner {
  display: flex; align-items: flex-start; gap: 0.875rem;
  background: var(--color-risk-medium-bg); border: 1.5px solid var(--color-risk-medium);
  border-radius: 10px; padding: 0.875rem 1.125rem;
}
.banner-icon { width: 20px; height: 20px; flex-shrink: 0; stroke: var(--color-risk-medium); margin-top: 2px; }
.banner-title { font-size: 0.875rem; font-weight: 700; color: var(--color-risk-medium); margin: 0 0 2px; }
.banner-desc  { font-size: 0.8125rem; color: var(--color-risk-medium); margin: 0; opacity: 0.85; }

/* Stages grid */
.escalade-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.75rem; }
.stage-card {
  background: var(--color-bg-card); border: 1.5px solid var(--color-border);
  border-radius: 10px; padding: 0.875rem; text-align: center; display: flex; flex-direction: column; gap: 0.25rem;
}
.stage-icon  { font-size: 1.25rem; }
.stage-label { font-size: 0.6875rem; color: var(--color-text-secondary); font-weight: 500; }
.stage-count { font-size: 1.25rem; font-weight: 800; color: var(--color-sidebar-bg); }
.stage-card--critical { border-color: var(--color-risk-high); background: var(--color-risk-high-bg); }
.stage-card--high     { border-color: #f97316; background: #fff7ed; }
.stage-card--warning  { border-color: var(--color-risk-medium); background: var(--color-risk-medium-bg); }

/* Card */
.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 10px; overflow: hidden; }
.card-header { padding: 1rem 1.25rem; border-bottom: 1px solid var(--color-border); }
.card-title  { font-size: 1rem; font-weight: 700; color: var(--color-sidebar-bg); margin: 0; }

/* Table */
.data-table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
.data-table th { background: var(--color-bg-page); padding: 0.625rem 0.875rem; text-align: left; font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); }
.data-table td { padding: 0.625rem 0.875rem; border-bottom: 1px solid var(--color-border); color: var(--color-text-primary); }
.data-table tr.row--urgent td { background: #fff7ed; }

.td-ref .dossier-link { color: var(--color-sidebar-bg); font-weight: 600; cursor: pointer; text-decoration: none; }
.td-ref .dossier-link:hover { text-decoration: underline; }
.td-urgent { color: var(--color-risk-high); font-weight: 700; }
.td-freq   { color: var(--color-text-secondary); font-size: 0.75rem; }

.risk-badge { font-size: 0.6875rem; font-weight: 700; padding: 2px 7px; border-radius: 5px; letter-spacing: 0.04em; }
.risk--low    { background: var(--color-risk-low-bg);    color: var(--color-risk-low); }
.risk--medium { background: var(--color-risk-medium-bg); color: var(--color-risk-medium); }
.risk--high   { background: var(--color-risk-high-bg);   color: var(--color-risk-high); }

.status-pill { font-size: 0.6875rem; font-weight: 600; padding: 2px 8px; border-radius: 5px; text-transform: capitalize; }
.status--planifiee   { background: #dbeafe; color: #2563eb; }
.status--en-cours    { background: #fef3c7; color: #d97706; }
.status--en-retard   { background: var(--color-risk-high-bg); color: var(--color-risk-high); }
.status--completee   { background: var(--color-risk-low-bg); color: var(--color-risk-low); }

.jalon-badge { font-size: 0.6875rem; font-weight: 700; padding: 2px 7px; border-radius: 5px; }
.jalon--critical { background: var(--color-risk-high-bg); color: var(--color-risk-high); }
.jalon--warning  { background: var(--color-risk-medium-bg); color: var(--color-risk-medium); }
.jalon--info     { background: #dbeafe; color: #2563eb; }

.btn-initier { font-size: 0.75rem; padding: 4px 10px; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 5px; cursor: pointer; }
.btn-initier:hover { background: var(--color-btn-primary-hover); }

.text-muted { color: var(--color-text-muted); }

/* Skeleton */
.skeleton-list { padding: 0.75rem 1.25rem; display: flex; flex-direction: column; gap: 0.75rem; }
.skeleton--row { height: 40px; background: #f1f5f9; border-radius: 7px; animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }

/* Empty */
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 3rem; color: var(--color-text-muted); }
.empty-icon-svg { width: 40px; height: 40px; stroke: var(--color-text-muted); }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 12px; padding: 1.5rem; width: 440px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); display: flex; flex-direction: column; gap: 1rem; }
.modal-title { font-size: 1.0625rem; font-weight: 800; color: var(--color-sidebar-bg); margin: 0; }
.modal-desc  { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; }
.field-group { display: flex; flex-direction: column; gap: 0.3rem; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.field-input { padding: 0.5625rem 0.75rem; border: 1px solid var(--color-border); border-radius: 7px; font-size: 0.875rem; width: 100%; }
.field-textarea { resize: vertical; min-height: 70px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
.btn-ghost   { padding: 0.5rem 1rem; background: none; border: 1px solid var(--color-border); border-radius: 7px; font-size: 0.875rem; cursor: pointer; }
.btn-primary { display: flex; align-items: center; gap: 0.375rem; padding: 0.5rem 1.25rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 7px; font-size: 0.875rem; font-weight: 600; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
