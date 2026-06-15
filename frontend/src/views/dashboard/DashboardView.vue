<template>
  <div class="dashboard">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Tableau de bord</h1>
        <p class="page-subtitle">
          Bonjour, {{ auth.user?.first_name }} · {{ roleLabel }}
          <span v-if="!['admin','notaire_principal','responsable_conformite'].includes(auth.user?.role ?? '')" class="dept-tag">{{ deptLabel }}</span>
        </p>
      </div>
      <span class="today-date">{{ todayFormatted }}</span>
    </div>

    <!-- KPI cards -->
    <div class="kpi-grid">
      <div v-for="kpi in kpis" :key="kpi.label" class="kpi-card">
        <div class="kpi-icon" :style="{ background: kpi.iconBg }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path :d="kpi.icon" />
          </svg>
        </div>
        <div class="kpi-body">
          <p class="kpi-value">{{ kpi.value }}</p>
          <p class="kpi-label">{{ kpi.label }}</p>
        </div>
        <div v-if="kpi.delta !== undefined" class="kpi-delta" :class="kpi.deltaClass">
          {{ kpi.delta }}
        </div>
      </div>
    </div>

    <!-- Supervisor section: risk distribution -->
    <div v-if="['admin','notaire_principal','responsable_conformite'].includes(auth.user?.role ?? '')" class="section-grid">
      <!-- Risk breakdown -->
      <div class="card">
        <h2 class="card-title">Répartition par niveau de risque</h2>
        <div class="risk-bars">
          <div class="risk-row">
            <span class="risk-label">
              <span class="badge-risk-faible">FAIBLE</span>
            </span>
            <div class="risk-bar-track">
              <div class="risk-bar risk-bar--low" :style="{ width: risquePct(risqueFaible) }" />
            </div>
            <span class="risk-count">{{ risqueFaible }}</span>
          </div>
          <div class="risk-row">
            <span class="risk-label">
              <span class="badge-risk-moyen">MOYEN</span>
            </span>
            <div class="risk-bar-track">
              <div class="risk-bar risk-bar--medium" :style="{ width: risquePct(risqueMoyen) }" />
            </div>
            <span class="risk-count">{{ risqueMoyen }}</span>
          </div>
          <div class="risk-row">
            <span class="risk-label">
              <span class="badge-risk-eleve">ÉLEVÉ</span>
            </span>
            <div class="risk-bar-track">
              <div class="risk-bar risk-bar--high" :style="{ width: risquePct(risqueEleve) }" />
            </div>
            <span class="risk-count">{{ risqueEleve }}</span>
          </div>
        </div>
      </div>

      <!-- Recent alerts -->
      <div class="card">
        <div class="card-header-row">
          <h2 class="card-title" style="margin:0">Dernières alertes</h2>
          <RouterLink v-if="(stats?.alertes_ouvertes ?? 0) > 0" :to="{ name: 'alertes' }" class="card-link">Voir toutes →</RouterLink>
        </div>
        <div v-if="(stats?.alertes_ouvertes ?? 0) > 0" class="alerte-summary">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="alerte-icon">
            <path d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          </svg>
          <div>
            <p class="alerte-count">{{ stats?.alertes_ouvertes }} alerte{{ (stats?.alertes_ouvertes ?? 0) > 1 ? 's' : '' }} ouverte{{ (stats?.alertes_ouvertes ?? 0) > 1 ? 's' : '' }}</p>
            <p class="alerte-hint">Consultez la liste des alertes pour traiter ces signalements.</p>
          </div>
        </div>
        <div v-else class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
          </svg>
          <p>Aucune alerte active</p>
        </div>
      </div>
    </div>

    <!-- Charts grid (supervisor only) -->
    <div v-if="['admin','notaire_principal','responsable_conformite'].includes(auth.user?.role ?? '') && stats" class="charts-grid">
      <div class="card chart-card">
        <h2 class="card-title">Statuts dossiers</h2>
        <apexchart type="donut" :options="donutOptions" :series="donutSeries" height="260" />
      </div>
      <div class="card chart-card">
        <h2 class="card-title">Soumissions dossiers par mois</h2>
        <apexchart type="bar" :options="barOptions" :series="barSeries" height="260" />
      </div>
      <div class="card chart-card">
        <h2 class="card-title">Dossiers validés / Risqués</h2>
        <apexchart type="area" :options="areaOptions" :series="areaSeries" height="260" />
      </div>
    </div>

    <!-- Operational section: recent files -->
    <div class="card" :class="{ 'mt-section': ['admin','notaire_principal','responsable_conformite'].includes(auth.user?.role ?? '') }">
      <div class="card-header-row">
        <h2 class="card-title" style="margin:0">
          {{ ['admin','notaire_principal','responsable_conformite'].includes(auth.user?.role ?? '') ? 'Dossiers récents' : 'Mes dossiers récents' }}
        </h2>
        <RouterLink :to="{ name: 'kyc-list' }" class="card-link">Voir tous →</RouterLink>
      </div>

      <div v-if="recentDossiers.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        <p>Aucun dossier KYC pour le moment</p>
        <RouterLink v-if="canCreateDossier" :to="{ name: 'kyc-new' }" class="btn-primary empty-action">
          Créer un premier dossier
        </RouterLink>
      </div>

      <table v-else class="recent-table">
        <thead>
          <tr>
            <th>Référence</th>
            <th>Type</th>
            <th>Statut</th>
            <th>Risque</th>
            <th>Créé le</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="d in recentDossiers"
            :key="d.id"
            class="recent-row"
            @click="router.push({ name: 'kyc-detail', params: { id: d.id } })"
          >
            <td class="td-ref">{{ d.reference }}</td>
            <td><span class="type-tag">{{ d.type_client }}</span></td>
            <td>
              <span class="statut-badge" :class="`statut--${d.statut}`">
                {{ STATUT_LABELS[d.statut] ?? d.statut }}
              </span>
            </td>
            <td>
              <span v-if="d.niveau_risque" class="risk-badge" :class="`risk--${d.niveau_risque}`">
                {{ d.niveau_risque }}
              </span>
              <span v-else class="td-muted">—</span>
            </td>
            <td class="td-date">{{ formatDate(d.created_at) }}</td>
            <td class="td-arrow">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'
import { ROLE_LABELS } from '@/utils/roles'

const auth = useAuthStore()
const router = useRouter()

const DEPT_LABELS: Record<string, string> = {
  AGENCE:     'Agence',
  PROMOTION:  'Promotion',
  TRANSVERSAL:'Transversal',
}

const roleLabel = computed(() =>
  auth.user ? (ROLE_LABELS[auth.user.role] ?? auth.user.role) : ''
)

const deptLabel = computed(() =>
  ''
)

const canCreateDossier = computed(() =>
  ['notaire_principal', 'responsable_conformite', 'clercs'].includes(
    auth.user?.role ?? ''
  )
)

const todayFormatted = computed(() =>
  new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
)

interface RecentDossier {
  id: string
  reference: string
  type_client: string
  statut: string
  niveau_risque: string | null
  created_at: string
}

interface MonthlyData { mois: string; soumissions: number; valides: number; risques: number }

interface DashboardStats {
  role: string
  scope: string
  dossiers_by_statut?: Record<string, number>
  mes_dossiers_by_statut?: Record<string, number>
  risque_distribution?: Record<string, number>
  alertes_ouvertes?: number
  revisions_dues_30j?: number
  wrk09_en_attente?: number
  recent_dossiers?: RecentDossier[]
  monthly_data?: MonthlyData[]
}

const stats = ref<DashboardStats | null>(null)

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

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d.getTime()) ? '—' : d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const recentDossiers = computed<RecentDossier[]>(() => stats.value?.recent_dossiers ?? [])

onMounted(async () => {
  try {
    const { data } = await api.get<DashboardStats>('/dashboard/stats')
    stats.value = data
  } catch {
    // Degrade gracefully — show '—' if API unreachable
  }
})

function totalDossiers(): string {
  if (!stats.value) return '—'
  const s = stats.value.dossiers_by_statut ?? stats.value.mes_dossiers_by_statut ?? {}
  const total = Object.values(s).reduce((a, b) => a + b, 0)
  return String(total)
}

const ICON_KYC   = 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
const ICON_ALERT = 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9'
const ICON_RISK  = 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
const ICON_REV   = 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z'
const ICON_WRK09 = 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4'

const kpis = computed(() => {
  const s = stats.value
  const base = [
    {
      label: 'Dossiers en cours',
      value: totalDossiers(),
      icon: ICON_KYC, iconBg: '#dbeafe', delta: undefined, deltaClass: '',
    },
    {
      label: 'Alertes actives',
      value: s ? String(s.alertes_ouvertes ?? 0) : '—',
      icon: ICON_ALERT, iconBg: '#fef3c7', delta: undefined, deltaClass: '',
    },
  ]
  if (['admin','notaire_principal','responsable_conformite'].includes(auth.user?.role ?? '')) {
    const risque = s?.risque_distribution ?? {}
    base.push(
      {
        label: 'Dossiers risque élevé',
        value: s ? String(risque['ELEVE'] ?? 0) : '—',
        icon: ICON_RISK, iconBg: '#fee2e2', delta: undefined, deltaClass: '',
      },
      {
        label: 'Révisions dues (retard + 30j)',
        value: s ? String(s.revisions_dues_30j ?? 0) : '—',
        icon: ICON_REV, iconBg: '#ede9fe', delta: undefined, deltaClass: '',
      },
      {
        label: 'WRK09 en attente',
        value: s ? String(s.wrk09_en_attente ?? 0) : '—',
        icon: ICON_WRK09, iconBg: '#fce7f3', delta: undefined, deltaClass: '',
      },
    )
  }
  return base
})

const risqueFaible = computed(() => stats.value?.risque_distribution?.['FAIBLE'] ?? 0)
const risqueMoyen  = computed(() => stats.value?.risque_distribution?.['MOYEN']  ?? 0)
const risqueEleve  = computed(() => stats.value?.risque_distribution?.['ELEVE']  ?? 0)
const risqueTotal  = computed(() => risqueFaible.value + risqueMoyen.value + risqueEleve.value)
function risquePct(n: number): string {
  return risqueTotal.value ? `${Math.round((n / risqueTotal.value) * 100)}%` : '0%'
}

// ── ApexCharts ─────────────────────────────────────────────────────────────

const CHART_STATUT_COLORS: Record<string, string> = {
  en_analyse:              '#3b82f6',
  valide:                  '#22c55e',
  vigilance_renforcee:     '#f59e0b',
  bloque:                  '#ef4444',
  traite:                  '#06b6d4',
  cloture:                 '#8b5cf6',
  archive:                 '#94a3b8',
  brouillon:               '#64748b',
  actif:                   '#10b981',
  actif_sous_surveillance: '#f97316',
  resilie:                 '#e11d48',
}

const donutSeries = computed(() =>
  Object.values(stats.value?.dossiers_by_statut ?? {}),
)
const donutOptions = computed(() => {
  const keys = Object.keys(stats.value?.dossiers_by_statut ?? {})
  return {
    labels: keys.map(k => STATUT_LABELS[k] ?? k),
    colors: keys.map(k => CHART_STATUT_COLORS[k] ?? '#94a3b8'),
    legend: { position: 'bottom', fontSize: '11px', itemMargin: { horizontal: 6, vertical: 2 } },
    dataLabels: { formatter: (val: number) => `${Math.round(val)}%` },
    plotOptions: { pie: { donut: { size: '65%' } } },
    chart: { toolbar: { show: false }, fontFamily: 'inherit' },
    stroke: { width: 2 },
  }
})

const monthLabels = computed(() => stats.value?.monthly_data?.map(m => m.mois) ?? [])

const barSeries = computed(() => [{
  name: 'Soumissions',
  data: stats.value?.monthly_data?.map(m => m.soumissions) ?? [],
}])
const barOptions = computed(() => ({
  chart: { toolbar: { show: false }, fontFamily: 'inherit' },
  xaxis: { categories: monthLabels.value },
  yaxis: { title: { text: 'Nombre de dossiers', style: { fontSize: '11px', fontWeight: 400 } } },
  colors: ['#6366f1'],
  dataLabels: { enabled: false },
  plotOptions: { bar: { borderRadius: 4, columnWidth: '55%' } },
  grid: { strokeDashArray: 4 },
}))

const areaSeries = computed(() => [
  { name: 'Dossiers risqués', data: stats.value?.monthly_data?.map(m => m.risques) ?? [] },
  { name: 'Dossiers validés', data: stats.value?.monthly_data?.map(m => m.valides) ?? [] },
])
const areaOptions = computed(() => ({
  chart: { toolbar: { show: true }, fontFamily: 'inherit' },
  xaxis: { categories: monthLabels.value },
  colors: ['#ef4444', '#22c55e'],
  fill: { type: 'gradient', gradient: { opacityFrom: 0.45, opacityTo: 0.05 } },
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 2 },
  legend: { position: 'bottom', fontSize: '11px' },
  grid: { strokeDashArray: 4 },
}))
</script>

<style scoped>
.dashboard {
  max-width: 1100px;
}

/* Header */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1.75rem;
}

.page-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 0.25rem;
  letter-spacing: -0.01em;
}

.page-subtitle {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.dept-tag {
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  padding: 1px 7px;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.today-date {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  text-transform: capitalize;
  padding-top: 0.25rem;
}

/* KPI grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.kpi-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 1.125rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.kpi-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-icon svg {
  width: 20px;
  height: 20px;
  stroke: var(--color-text-secondary);
}

.kpi-body {
  flex: 1;
}

.kpi-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.kpi-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin: 0;
}

/* Section grid */
.section-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

@media (max-width: 768px) {
  .section-grid {
    grid-template-columns: 1fr;
  }
}

.mt-section {
  margin-top: 0;
}

/* Risk bars */
.card-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 1rem;
}

.risk-bars {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.risk-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.risk-label {
  width: 72px;
  flex-shrink: 0;
}

.risk-bar-track {
  flex: 1;
  height: 8px;
  background: var(--color-bg-page);
  border-radius: 4px;
  overflow: hidden;
}

.risk-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.risk-bar--low    { background: var(--color-risk-low); }
.risk-bar--medium { background: var(--color-risk-medium); }
.risk-bar--high   { background: var(--color-risk-high); }

.risk-count {
  width: 28px;
  text-align: right;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

/* Charts grid */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
}

@media (max-width: 1024px) {
  .charts-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
  .charts-grid { grid-template-columns: 1fr; }
}

.chart-card { padding: 1.125rem 1rem 0.5rem; }

.card-note {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin: 0;
}

/* Alerte summary */
.alerte-summary {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background: var(--color-status-vigilance-bg, #fffbeb);
  border: 1px solid var(--color-risk-medium, #f59e0b);
  border-radius: 8px;
}

.alerte-icon {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  stroke: var(--color-risk-medium, #f59e0b);
  margin-top: 1px;
}

.alerte-count {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 0.2rem;
}

.alerte-hint {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin: 0;
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.625rem;
  padding: 2rem 1rem;
  color: var(--color-text-muted);
}

.empty-state svg {
  width: 36px;
  height: 36px;
  stroke: var(--color-border);
}

.empty-state p {
  font-size: 0.875rem;
  margin: 0;
}

.empty-action {
  margin-top: 0.5rem;
  font-size: 0.8125rem;
  text-decoration: none;
}

/* Card header row */
.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.card-link {
  font-size: 0.8125rem;
  color: var(--color-sidebar-bg);
  text-decoration: none;
}
.card-link:hover { text-decoration: underline; }

/* Recent dossiers table */
.recent-table {
  width: 100%;
  border-collapse: collapse;
}
.recent-table th {
  padding: 0.375rem 0.75rem;
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}
.recent-table td {
  padding: 0.625rem 0.75rem;
  font-size: 0.8125rem;
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}
.recent-table tr:last-child td { border-bottom: none; }
.recent-row { cursor: pointer; transition: background 0.1s; }
.recent-row:hover td { background: var(--color-bg-page); }

.td-ref { font-family: monospace; font-weight: 600; font-size: 0.8125rem; }
.td-date { font-size: 0.75rem; color: var(--color-text-secondary); white-space: nowrap; }
.td-muted { color: var(--color-text-muted); }
.td-arrow svg { width: 14px; height: 14px; color: var(--color-text-muted); }

.type-tag {
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  padding: 2px 6px;
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-sidebar-bg);
}

.statut-badge {
  display: inline-block;
  border-radius: 10px;
  padding: 2px 8px;
  font-size: 0.6875rem;
  font-weight: 600;
}
.statut--brouillon               { color: var(--color-status-brouillon); background: var(--color-status-brouillon-bg); }
.statut--en_analyse              { color: var(--color-status-en-analyse); background: var(--color-status-en-analyse-bg); }
.statut--vigilance_renforcee     { color: var(--color-status-vigilance); background: var(--color-status-vigilance-bg); }
.statut--valide                  { color: var(--color-status-valide); background: var(--color-status-valide-bg); }
.statut--actif                   { color: var(--color-status-valide); background: var(--color-status-valide-bg); }
.statut--actif_sous_surveillance { color: var(--color-status-vigilance); background: var(--color-status-vigilance-bg); }
.statut--bloque                  { color: var(--color-status-bloque); background: var(--color-status-bloque-bg); }
.statut--traite                  { color: var(--color-status-traite); background: var(--color-status-traite-bg); }
.statut--resilie, .statut--cloture, .statut--archive { color: var(--color-status-cloture); background: var(--color-status-cloture-bg); }

.risk-badge {
  display: inline-block;
  border-radius: 10px;
  padding: 2px 8px;
  font-size: 0.6875rem;
  font-weight: 700;
}
.risk--FAIBLE { color: var(--color-risk-low);    background: var(--color-risk-low-bg); }
.risk--MOYEN  { color: var(--color-risk-medium); background: var(--color-risk-medium-bg); }
.risk--ELEVE  { color: var(--color-risk-high);   background: var(--color-risk-high-bg); }
</style>
