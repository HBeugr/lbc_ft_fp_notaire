<template>
  <div class="dash-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Tableau de bord</h1>
        <p class="page-subtitle">Volumétrie de la plateforme — aucun contenu de dossier n'est lu</p>
      </div>
      <button class="btn-ghost" :disabled="loading" @click="load">
        <span v-if="loading" class="spinner spinner--dark" />
        Actualiser
      </button>
    </div>

    <div v-if="loadError" class="alert-error">{{ loadError }}</div>

    <div v-if="loading && !metrics" class="card empty-state">Chargement…</div>

    <template v-else-if="metrics">
      <!-- Comptage partiel : annoncé plutôt que masqué. Un total silencieusement
           faux induirait en erreur sur le dimensionnement. -->
      <div v-if="metrics.cabinets_injoignables.length" class="alert-warning">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <span>
          Totaux partiels : {{ metrics.cabinets_injoignables.length }} cabinet{{ metrics.cabinets_injoignables.length !== 1 ? 's' : '' }}
          n'a pas pu être compté ({{ metrics.cabinets_injoignables.join(', ') }}). Une migration est peut-être en cours.
        </span>
      </div>

      <div class="kpi-grid">
        <div class="card kpi">
          <p class="kpi-label">Cabinets</p>
          <p class="kpi-value">{{ metrics.cabinets_total }}</p>
          <p class="kpi-foot">{{ enProduction }} en production · {{ enConfiguration }} en configuration</p>
        </div>
        <div class="card kpi">
          <p class="kpi-label">Utilisateurs actifs</p>
          <p class="kpi-value">{{ metrics.utilisateurs_actifs }}</p>
          <p class="kpi-foot">sur {{ metrics.utilisateurs_total }} enregistré{{ metrics.utilisateurs_total !== 1 ? 's' : '' }}</p>
        </div>
        <div class="card kpi">
          <p class="kpi-label">Dossiers</p>
          <p class="kpi-value">{{ metrics.dossiers_total }}</p>
          <p class="kpi-foot">tous cabinets confondus</p>
        </div>
        <div class="card kpi" :class="{ 'kpi--alert': aSurveiller > 0 }">
          <p class="kpi-label">À surveiller</p>
          <p class="kpi-value">{{ aSurveiller }}</p>
          <p class="kpi-foot">{{ suspendus }} suspendu{{ suspendus !== 1 ? 's' : '' }} · {{ archives }} archivé{{ archives !== 1 ? 's' : '' }}</p>
        </div>
      </div>

      <!-- Répartition par statut : barre unique proportionnelle, sans librairie
           de graphiques — quatre segments ne justifient pas 500 Ko de bundle. -->
      <div class="card">
        <h2 class="card-title">Répartition des cabinets</h2>
        <div v-if="metrics.cabinets_total > 0" class="repartition">
          <div class="repartition-bar" role="img" :aria-label="repartitionLabel">
            <div
              v-for="seg in segments"
              :key="seg.statut"
              class="repartition-seg"
              :class="`repartition-seg--${seg.statut}`"
              :style="{ width: `${seg.pct}%` }"
              :title="`${seg.label} : ${seg.count}`"
            />
          </div>
          <ul class="legend">
            <li v-for="seg in segments" :key="seg.statut" class="legend-item">
              <span class="legend-dot" :class="`repartition-seg--${seg.statut}`" />
              {{ seg.label }}
              <strong>{{ seg.count }}</strong>
            </li>
          </ul>
        </div>
        <p v-else class="empty-inline">Aucun cabinet enregistré pour l'instant.</p>
      </div>

      <div class="card">
        <div class="card-head">
          <h2 class="card-title">Derniers cabinets créés</h2>
          <RouterLink :to="{ name: 'super-admin-tenants' }" class="card-link">Tout voir</RouterLink>
        </div>
        <table v-if="metrics.cabinets_recents.length" class="mini-table">
          <tbody>
            <tr v-for="t in metrics.cabinets_recents" :key="t.id">
              <td>
                <RouterLink
                  :to="{ name: 'super-admin-tenant-detail', params: { id: t.id } }"
                  class="row-link"
                >{{ t.nom_cabinet }}</RouterLink>
              </td>
              <td class="td-statut">
                <span class="badge" :class="`badge--${t.statut}`">{{ TENANT_STATUT_LABELS[t.statut] }}</span>
              </td>
              <td class="td-date">{{ formatDate(t.created_at) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-inline">
          Aucun cabinet pour l'instant.
          <RouterLink :to="{ name: 'super-admin-tenant-create' }" class="card-link">Créer le premier</RouterLink>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  superAdminService,
  TENANT_STATUT_LABELS,
  type PlatformMetrics,
  type TenantStatut,
} from '@/services/superAdmin'

const metrics = ref<PlatformMetrics | null>(null)
const loading = ref(false)
const loadError = ref('')

const ORDRE: TenantStatut[] = ['production', 'configuration', 'suspendu', 'archive']

function compte(statut: TenantStatut): number {
  return metrics.value?.cabinets_par_statut[statut] ?? 0
}

const enProduction = computed(() => compte('production'))
const enConfiguration = computed(() => compte('configuration'))
const suspendus = computed(() => compte('suspendu'))
const archives = computed(() => compte('archive'))
const aSurveiller = computed(() => suspendus.value + archives.value)

const segments = computed(() => {
  const total = metrics.value?.cabinets_total ?? 0
  if (!total) return []
  return ORDRE.map((statut) => ({
    statut,
    label: TENANT_STATUT_LABELS[statut],
    count: compte(statut),
    pct: (compte(statut) / total) * 100,
  })).filter((s) => s.count > 0)
})

const repartitionLabel = computed(() =>
  segments.value.map((s) => `${s.label} : ${s.count}`).join(', ')
)

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    metrics.value = await superAdminService.platformMetrics()
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    loadError.value =
      typeof detail === 'string' ? detail : 'Impossible de charger les métriques de la plateforme.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.dash-page { max-width: 1100px; }

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0.25rem 0 0; }

.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 0.5rem 0.875rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-primary);
  cursor: pointer;
  flex-shrink: 0;
}
.btn-ghost:hover:not(:disabled) { border-color: var(--color-text-secondary); }
.btn-ghost:disabled { opacity: 0.6; cursor: not-allowed; }

.alert-error,
.alert-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  border-radius: 8px;
  padding: 0.75rem 0.875rem;
  font-size: 0.8125rem;
  margin-bottom: 1.25rem;
}
.alert-error {
  background: var(--color-risk-high-bg);
  color: var(--color-risk-high);
  border: 1px solid rgba(220, 38, 38, 0.2);
}
.alert-warning {
  background: var(--color-risk-medium-bg);
  color: var(--color-risk-medium);
  border: 1px solid rgba(217, 119, 6, 0.2);
}
.alert-warning svg { width: 16px; height: 16px; flex-shrink: 0; margin-top: 1px; }

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.kpi { padding: 1.125rem 1.25rem; }
.kpi-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  margin: 0;
}
.kpi-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text-primary);
  line-height: 1.15;
  margin: 0.375rem 0 0;
}
.kpi-foot { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0.25rem 0 0; }
.kpi--alert .kpi-value { color: var(--color-risk-medium); }

.card { margin-bottom: 1.25rem; }
.card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; }
.card-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 1rem;
}
.card-head .card-title { margin-bottom: 1rem; }
.card-link {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-sidebar-bg);
  text-decoration: none;
}
.card-link:hover { text-decoration: underline; }

.repartition-bar {
  display: flex;
  height: 12px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--color-bg-page);
}
.repartition-seg { height: 100%; }
.repartition-seg--production { background: var(--color-risk-low); }
.repartition-seg--configuration { background: var(--color-accent-gold); }
.repartition-seg--suspendu { background: var(--color-risk-medium); }
.repartition-seg--archive { background: var(--color-text-muted); }

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem 1.25rem;
  list-style: none;
  padding: 0;
  margin: 0.875rem 0 0;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 0.4375rem;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
.legend-item strong { color: var(--color-text-primary); }
.legend-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }

.mini-table { width: 100%; border-collapse: collapse; }
.mini-table td {
  padding: 0.625rem 0;
  border-bottom: 1px solid var(--color-border);
  font-size: 0.8125rem;
  color: var(--color-text-primary);
}
.mini-table tr:last-child td { border-bottom: none; }
.row-link { color: var(--color-text-primary); text-decoration: none; font-weight: 500; }
.row-link:hover { text-decoration: underline; }
.td-statut { width: 1%; white-space: nowrap; }
.td-date { width: 1%; white-space: nowrap; color: var(--color-text-muted); text-align: right; }

.badge {
  display: inline-block;
  padding: 0.1875rem 0.5rem;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 600;
  white-space: nowrap;
}
.badge--production { background: var(--color-risk-low-bg); color: var(--color-risk-low); }
.badge--configuration { background: rgba(201, 162, 39, 0.15); color: #8a6d10; }
.badge--suspendu { background: var(--color-risk-medium-bg); color: var(--color-risk-medium); }
.badge--archive { background: var(--color-bg-page); color: var(--color-text-muted); }

.empty-state { text-align: center; padding: 2.75rem; color: var(--color-text-muted); }
.empty-inline {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
}

.spinner--dark {
  width: 13px;
  height: 13px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-text-secondary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
