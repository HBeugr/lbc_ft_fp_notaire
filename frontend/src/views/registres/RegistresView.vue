<template>
  <AppLayout>
    <div class="p-6 space-y-5">
      <div>
        <h1 class="text-xl font-semibold text-gray-900">Registres Légaux</h1>
        <p class="text-sm text-gray-500 mt-0.5">Art. 23, Ordonnance n° 2023-875 — conservation 10 ans</p>
      </div>

      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">{{ error }}</div>

      <!-- Liste des registres -->
      <div v-if="!activeRegistre" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-if="loading" v-for="i in 4" :key="i" class="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-2/3 mb-2"></div>
          <div class="h-3 bg-gray-200 rounded w-1/2"></div>
        </div>
        <button
          v-for="r in registres"
          :key="r.id"
          @click="openRegistre(r)"
          class="bg-white rounded-xl border border-gray-200 p-5 text-left hover:border-[#1a2e4a] hover:shadow-sm transition-all"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="w-10 h-10 bg-[#1a2e4a]/10 rounded-lg flex items-center justify-center text-xl">
              {{ registreIcon(r.id) }}
            </div>
            <span v-if="r.confidential" class="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full font-medium">Confidentiel</span>
          </div>
          <h3 class="text-sm font-semibold text-gray-900">{{ r.label }}</h3>
          <p class="text-xs text-gray-400 mt-1">Cliquer pour consulter →</p>
        </button>
      </div>

      <!-- Détail registre -->
      <div v-else class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <button @click="activeRegistre = null" class="text-sm text-gray-400 hover:text-[#1a2e4a]">← Registres</button>
            <h2 class="text-base font-semibold text-gray-900">{{ activeRegistre.label }}</h2>
            <span v-if="activeRegistre.confidential" class="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">Confidentiel</span>
          </div>
          <div class="flex gap-2">
            <button @click="loadEntries" class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">Actualiser</button>
            <button @click="exportPdf" :disabled="exporting" class="px-3 py-1.5 bg-[#1a2e4a] text-white text-sm rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50">
              {{ exporting ? 'Export…' : '⬇ Export PDF' }}
            </button>
          </div>
        </div>

        <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div v-if="entriesLoading" class="flex items-center justify-center py-12 text-gray-400 text-sm">Chargement…</div>
          <div v-else-if="entries.length === 0" class="flex items-center justify-center py-12 text-gray-400 text-sm">Aucune entrée dans ce registre.</div>
          <div v-else>
            <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <span class="text-xs text-gray-500">{{ total }} entrée(s) au total</span>
              <div class="flex gap-2">
                <button :disabled="offset === 0" @click="prevPage" class="px-2 py-1 text-xs border border-gray-200 rounded disabled:opacity-40 hover:bg-gray-50">← Préc.</button>
                <span class="px-2 py-1 text-xs text-gray-500">{{ Math.floor(offset / LIMIT) + 1 }}</span>
                <button :disabled="offset + LIMIT >= total" @click="nextPage" class="px-2 py-1 text-xs border border-gray-200 rounded disabled:opacity-40 hover:bg-gray-50">Suiv. →</button>
              </div>
            </div>
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-gray-100">
                  <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Date/Heure</th>
                  <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Action</th>
                  <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Entité</th>
                  <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">ID Entité</th>
                  <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Utilisateur</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr v-for="e in entries" :key="e.id" class="hover:bg-gray-50">
                  <td class="px-4 py-2.5 text-xs text-gray-500 font-mono">{{ formatTs(e.timestamp) }}</td>
                  <td class="px-4 py-2.5"><span class="text-xs bg-[#1a2e4a]/10 text-[#1a2e4a] px-2 py-0.5 rounded font-mono">{{ e.action }}</span></td>
                  <td class="px-4 py-2.5 text-xs text-gray-600">{{ e.entity_type }}</td>
                  <td class="px-4 py-2.5 text-xs font-mono text-gray-500">{{ e.entity_id ? e.entity_id.substring(0, 12) + '…' : '—' }}</td>
                  <td class="px-4 py-2.5 text-xs font-mono text-gray-500">{{ e.user_id ? e.user_id.substring(0, 10) + '…' : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

interface RegistreMeta { id: string; label: string; confidential: boolean }
interface Entry { id: string; timestamp: string; action: string; entity_type: string; entity_id: string; user_id: string }

const LIMIT = 50
const auth = useAuthStore()
const registres = ref<RegistreMeta[]>([])
const loading = ref(true)
const error = ref('')
const activeRegistre = ref<RegistreMeta | null>(null)
const entries = ref<Entry[]>([])
const entriesLoading = ref(false)
const total = ref(0)
const offset = ref(0)
const exporting = ref(false)

function headers() { return auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {} }
function formatTs(s: string) { return new Date(s).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }
function registreIcon(id: string) { const m: Record<string, string> = { kyc: '👤', alertes: '⚠️', dos: '🚨', statuts: '🔄', revisions: '📅', journal: '📋' }; return m[id] ?? '📁' }

async function loadRegistres() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/registres', { headers: headers() })
    registres.value = data.registres
  } catch (e: any) { error.value = e.response?.data?.detail ?? 'Erreur de chargement.' }
  finally { loading.value = false }
}

async function openRegistre(r: RegistreMeta) {
  activeRegistre.value = r
  offset.value = 0
  await loadEntries()
}

async function loadEntries() {
  if (!activeRegistre.value) return
  entriesLoading.value = true
  try {
    const { data } = await axios.get(`/api/registres/${activeRegistre.value.id}`, {
      params: { limit: LIMIT, offset: offset.value },
      headers: headers(),
    })
    entries.value = data.items
    total.value = data.total
  } catch (e: any) { error.value = e.response?.data?.detail ?? 'Erreur.' }
  finally { entriesLoading.value = false }
}

async function exportPdf() {
  if (!activeRegistre.value) return
  exporting.value = true
  try {
    const response = await axios.get(`/api/registres/${activeRegistre.value.id}/export`, {
      params: { format: 'pdf' },
      headers: headers(),
      responseType: 'blob',
    })
    const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `registre-${activeRegistre.value.id}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) { error.value = 'Erreur lors de l\'export.' }
  finally { exporting.value = false }
}

function prevPage() { offset.value = Math.max(0, offset.value - LIMIT); loadEntries() }
function nextPage() { offset.value += LIMIT; loadEntries() }

onMounted(loadRegistres)
</script>
