<template>
  <AppLayout>
    <div class="p-6 space-y-6">
      <!-- Header -->
      <div>
        <h1 class="text-xl font-semibold text-gray-900">Rapports & Tableaux de bord</h1>
        <p class="text-sm text-gray-500 mt-0.5">Conformité LBC/FT/FP — Art. 23, Ordonnance n° 2023-875</p>
      </div>

      <div v-if="statsError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">{{ statsError }}</div>

      <!-- KPIs -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div v-for="kpi in kpis" :key="kpi.label" class="bg-white rounded-xl border border-gray-200 p-5">
          <div class="flex items-center justify-between mb-3">
            <span class="text-2xl">{{ kpi.icon }}</span>
            <span v-if="kpi.badge" :class="kpi.badgeClass" class="text-xs px-2 py-0.5 rounded-full font-medium">{{ kpi.badge }}</span>
          </div>
          <div v-if="statsLoading" class="h-8 bg-gray-200 rounded animate-pulse mb-1"></div>
          <div v-else class="text-2xl font-bold text-[#1a2e4a]">{{ kpi.value }}</div>
          <p class="text-xs text-gray-500 mt-0.5">{{ kpi.label }}</p>
        </div>
      </div>

      <!-- Charts -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Classification -->
        <div class="bg-white rounded-xl border border-gray-200 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-4">Dossiers par classification</h3>
          <div v-if="statsLoading" class="h-48 bg-gray-100 rounded animate-pulse"></div>
          <apexchart v-else-if="classChartSeries.length > 0" type="donut" :options="classChartOpts" :series="classChartSeries" height="200" />
          <div v-else class="flex items-center justify-center h-48 text-gray-400 text-sm">Aucune donnée</div>
        </div>

        <!-- Statuts -->
        <div class="bg-white rounded-xl border border-gray-200 p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-4">Dossiers par statut</h3>
          <div v-if="statsLoading" class="h-48 bg-gray-100 rounded animate-pulse"></div>
          <apexchart v-else-if="statutChartSeries.length > 0" type="bar" :options="statutChartOpts" :series="[{ name: 'Dossiers', data: statutChartSeries.map(s => s.y) }]" height="200" />
          <div v-else class="flex items-center justify-center h-48 text-gray-400 text-sm">Aucune donnée</div>
        </div>
      </div>

      <!-- Exports -->
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">Exporter un rapport PDF</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- Rapport conformité -->
          <div class="border border-gray-200 rounded-lg p-4 space-y-3">
            <div class="flex items-center gap-2">
              <span class="text-xl">📊</span>
              <h4 class="text-sm font-medium text-gray-900">Rapport de conformité</h4>
            </div>
            <p class="text-xs text-gray-500">Synthèse périodique des dossiers, alertes et classifications.</p>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="block text-xs text-gray-500 mb-1">Début période</label>
                <input v-model="conformiteForm.date_debut" type="date" class="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none" />
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">Fin période</label>
                <input v-model="conformiteForm.date_fin" type="date" class="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none" />
              </div>
            </div>
            <button @click="exportConformite" :disabled="exportingConformite" class="w-full py-2 bg-[#1a2e4a] text-white text-xs rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50">
              {{ exportingConformite ? 'Génération…' : '⬇ Télécharger' }}
            </button>
          </div>

          <!-- Rapport client -->
          <div class="border border-gray-200 rounded-lg p-4 space-y-3">
            <div class="flex items-center gap-2">
              <span class="text-xl">👤</span>
              <h4 class="text-sm font-medium text-gray-900">Rapport client</h4>
            </div>
            <p class="text-xs text-gray-500">Dossier complet sans information DOS (Art. 63).</p>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Référence dossier</label>
              <input v-model="clientRef" placeholder="ex: DOS-ABCD1234" class="w-full border border-gray-300 rounded px-2 py-1.5 text-xs focus:outline-none" />
            </div>
            <button @click="exportClient" :disabled="exportingClient || !clientRef.trim()" class="w-full py-2 bg-[#1a2e4a] text-white text-xs rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50">
              {{ exportingClient ? 'Génération…' : '⬇ Télécharger' }}
            </button>
          </div>

          <!-- Rapport audit -->
          <div class="border border-gray-200 rounded-lg p-4 space-y-3">
            <div class="flex items-center gap-2">
              <span class="text-xl">🔍</span>
              <h4 class="text-sm font-medium text-gray-900">Piste d'audit</h4>
            </div>
            <p class="text-xs text-gray-500">500 dernières actions — logs immuables (Art. 23).</p>
            <div class="py-4"></div>
            <button @click="exportAudit" :disabled="exportingAudit" class="w-full py-2 bg-[#1a2e4a] text-white text-xs rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50">
              {{ exportingAudit ? 'Génération…' : '⬇ Télécharger' }}
            </button>
          </div>
        </div>

        <div v-if="exportError" class="mt-3 bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ exportError }}</div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import axios from 'axios'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

interface Stats {
  total_dossiers: number; alertes_ouvertes: number; revisions_en_retard: number
  by_classification: { classification: string; count: number }[]
  dos_total?: number; dos_en_cours?: number
}

const stats = ref<Stats | null>(null)
const statsLoading = ref(true)
const statsError = ref('')
const exportError = ref('')
const exportingConformite = ref(false)
const exportingClient = ref(false)
const exportingAudit = ref(false)
const conformiteForm = reactive({ date_debut: '', date_fin: '' })
const clientRef = ref('')

function headers() { return auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {} }

const kpis = computed(() => {
  const s = stats.value
  return [
    { icon: '📁', label: 'Dossiers actifs', value: s?.total_dossiers ?? '—', badge: null, badgeClass: '' },
    { icon: '⚠️', label: 'Alertes ouvertes', value: s?.alertes_ouvertes ?? '—', badge: s && s.alertes_ouvertes > 0 ? 'Attention' : null, badgeClass: 'bg-orange-100 text-orange-700' },
    { icon: '📅', label: 'Révisions en retard', value: s?.revisions_en_retard ?? '—', badge: s && s.revisions_en_retard > 0 ? 'En retard' : null, badgeClass: 'bg-red-100 text-red-700' },
    { icon: '🚨', label: 'DOS en cours', value: s?.dos_en_cours ?? '—', badge: null, badgeClass: '' },
  ]
})

const classChartSeries = computed(() => {
  if (!stats.value?.by_classification) return []
  return stats.value.by_classification.map(c => c.count)
})

const classChartOpts = computed(() => ({
  labels: stats.value?.by_classification.map(c => c.classification) ?? [],
  colors: ['#22c55e', '#f97316', '#ef4444', '#94a3b8'],
  legend: { position: 'bottom' as const, fontSize: '11px' },
  dataLabels: { enabled: true },
  chart: { toolbar: { show: false } },
}))

const statutChartSeries = computed<{ x: string; y: number }[]>(() => [])

const statutChartOpts = computed(() => ({
  xaxis: { categories: statutChartSeries.value.map(s => s.x) },
  colors: ['#1a2e4a'],
  chart: { toolbar: { show: false } },
  plotOptions: { bar: { borderRadius: 4 } },
  dataLabels: { enabled: false },
}))

async function loadStats() {
  statsLoading.value = true; statsError.value = ''
  try {
    const { data } = await axios.get('/api/registres/dashboard/stats', { headers: headers() })
    stats.value = data
  } catch (e: any) { statsError.value = e.response?.data?.detail ?? 'Erreur de chargement.' }
  finally { statsLoading.value = false }
}

async function downloadBlob(url: string, body: object, filename: string) {
  const response = await axios.post(url, body, { headers: headers(), responseType: 'blob' })
  const blobUrl = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
  const a = document.createElement('a'); a.href = blobUrl; a.download = filename; a.click()
  URL.revokeObjectURL(blobUrl)
}

async function exportConformite() {
  exportingConformite.value = true; exportError.value = ''
  try { await downloadBlob('/api/rapports/conformite', { ...conformiteForm }, 'rapport-conformite.pdf') }
  catch (e: any) { exportError.value = e.response?.data?.detail ?? 'Erreur lors de l\'export.' }
  finally { exportingConformite.value = false }
}

async function exportClient() {
  exportingClient.value = true; exportError.value = ''
  try { await downloadBlob('/api/rapports/client', { dossier_reference: clientRef.value }, `rapport-client-${clientRef.value}.pdf`) }
  catch (e: any) { exportError.value = e.response?.data?.detail ?? 'Erreur lors de l\'export.' }
  finally { exportingClient.value = false }
}

async function exportAudit() {
  exportingAudit.value = true; exportError.value = ''
  try { await downloadBlob('/api/rapports/audit', {}, 'rapport-audit.pdf') }
  catch (e: any) { exportError.value = e.response?.data?.detail ?? 'Erreur lors de l\'export.' }
  finally { exportingAudit.value = false }
}

onMounted(loadStats)
</script>
