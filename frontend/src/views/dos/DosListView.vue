<template>
  <AppLayout>
    <div class="p-6 space-y-5">
      <!-- Bannière confidentialité Art. 63 -->
      <div class="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 flex items-start gap-3">
        <span class="text-amber-500 text-lg mt-0.5">⚠️</span>
        <div class="text-sm text-amber-800">
          <strong>Confidentialité absolue — Art. 63, Ordonnance n° 2023-875.</strong>
          Les informations relatives aux déclarations de soupçon ne doivent en aucun cas être divulguées au client ou aux tiers. Toute divulgation est pénalement sanctionnée.
        </div>
      </div>

      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-xl font-semibold text-gray-900">Déclarations de Soupçon</h1>
          <p class="text-sm text-gray-500 mt-0.5">{{ dosList.length }} DOS enregistrée(s)</p>
        </div>
        <button @click="showCreate = true" class="flex items-center gap-2 bg-[#1a2e4a] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#1a2e4a]/90 transition-colors">
          + Nouvelle DOS
        </button>
      </div>

      <!-- Filtres -->
      <div class="flex gap-3">
        <select v-model="filterStatut" class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none">
          <option value="">Tous les statuts</option>
          <option value="brouillon">Brouillon</option>
          <option value="en_cours">En cours</option>
          <option value="soumis">Soumis CENTIF</option>
          <option value="accuse_recu">Accusé reçu</option>
        </select>
        <button @click="load" class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">Actualiser</button>
      </div>

      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">{{ error }}</div>

      <!-- Table -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div v-if="loading" class="flex items-center justify-center py-12 text-gray-400 text-sm">Chargement…</div>
        <div v-else-if="dosList.length === 0" class="flex flex-col items-center justify-center py-12 text-gray-400">
          <span class="text-4xl mb-3">🚨</span>
          <p class="text-sm">Aucune DOS enregistrée.</p>
        </div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Référence</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Dossier</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Type soupçon</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Statut</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Délai</th>
              <th class="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="d in filteredList" :key="d.id" class="hover:bg-gray-50 transition-colors">
              <td class="px-4 py-3">
                <span class="font-mono text-xs font-medium text-[#1a2e4a]">{{ d.reference_interne }}</span>
              </td>
              <td class="px-4 py-3">
                <RouterLink :to="`/dossiers/${d.dossier_id}`" class="text-xs text-[#1a2e4a] hover:underline font-mono">{{ d.dossier_id.substring(0, 8) }}…</RouterLink>
              </td>
              <td class="px-4 py-3">
                <div class="flex gap-1 flex-wrap">
                  <span v-if="d.type_soupcon_bc" class="bg-red-100 text-red-700 px-1.5 py-0.5 rounded text-xs">BC</span>
                  <span v-if="d.type_soupcon_ft" class="bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded text-xs">FT</span>
                  <span v-if="d.type_soupcon_prolif" class="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded text-xs">Prolif.</span>
                  <span v-if="!d.type_soupcon_bc && !d.type_soupcon_ft && !d.type_soupcon_prolif" class="text-gray-400 text-xs">—</span>
                </div>
              </td>
              <td class="px-4 py-3">
                <span :class="statutBadge(d.statut)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ statutLabel(d.statut) }}</span>
              </td>
              <td class="px-4 py-3">
                <span v-if="d.statut === 'brouillon' || d.statut === 'en_cours'" :class="isUrgent(d.created_at) ? 'text-red-600 font-semibold' : 'text-gray-500'" class="text-xs">
                  {{ delaiLabel(d.created_at) }}
                </span>
                <span v-else-if="d.soumis_at" class="text-xs text-gray-400">Soumis {{ formatDate(d.soumis_at) }}</span>
                <span v-else class="text-gray-400 text-xs">—</span>
              </td>
              <td class="px-4 py-3 text-right">
                <RouterLink :to="`/dos/${d.id}`" class="px-3 py-1 text-xs bg-[#1a2e4a]/10 text-[#1a2e4a] rounded hover:bg-[#1a2e4a]/20 font-medium">
                  Voir / Modifier
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 class="font-semibold text-gray-900">Initier une DOS</h2>
          <button @click="showCreate = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="submitCreate" class="p-5 space-y-4">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">ID du dossier concerné</label>
            <input v-model="createDossierId" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30" placeholder="UUID du dossier" />
          </div>
          <p class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
            ⏱ Délai légal : <strong>24h</strong> maximum après détection de la suspicion (Art. 2 §58).
          </p>
          <div v-if="createError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ createError }}</div>
          <div class="flex justify-end gap-3">
            <button type="button" @click="showCreate = false" class="px-4 py-2 text-sm text-gray-600">Annuler</button>
            <button type="submit" :disabled="creating" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50">
              {{ creating ? 'Création…' : 'Initier' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import axios from 'axios'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

interface DOS {
  id: string; dossier_id: string; reference_interne: string; statut: string
  type_soupcon_bc: boolean; type_soupcon_ft: boolean; type_soupcon_prolif: boolean
  soumis_at: string | null; created_at: string
}

const auth = useAuthStore()
const router = useRouter()
const dosList = ref<DOS[]>([])
const loading = ref(true)
const error = ref('')
const filterStatut = ref('')
const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const createDossierId = ref('')

const filteredList = computed(() =>
  filterStatut.value ? dosList.value.filter(d => d.statut === filterStatut.value) : dosList.value
)

function headers() { return auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {} }
function formatDate(s: string) { return new Date(s).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' }) }
function statutLabel(s: string) { const m: Record<string, string> = { brouillon: 'Brouillon', en_cours: 'En cours', soumis: 'Soumis CENTIF', accuse_recu: 'Accusé reçu' }; return m[s] ?? s }
function statutBadge(s: string) { const m: Record<string, string> = { brouillon: 'bg-gray-100 text-gray-600', en_cours: 'bg-blue-100 text-blue-700', soumis: 'bg-orange-100 text-orange-700', accuse_recu: 'bg-green-100 text-green-700' }; return m[s] ?? 'bg-gray-100 text-gray-600' }

function delaiLabel(createdAt: string) {
  const diffH = (Date.now() - new Date(createdAt).getTime()) / 3600000
  if (diffH >= 24) return `⚠️ ${Math.floor(diffH)}h — délai dépassé`
  const remaining = Math.ceil(24 - diffH)
  return `${remaining}h restante(s)`
}

function isUrgent(createdAt: string) {
  return (Date.now() - new Date(createdAt).getTime()) / 3600000 >= 20
}

async function load() {
  loading.value = true; error.value = ''
  try {
    const { data } = await axios.get('/api/dos', { headers: headers() })
    dosList.value = data
  } catch (e: any) { error.value = e.response?.data?.detail ?? 'Erreur de chargement.' }
  finally { loading.value = false }
}

async function submitCreate() {
  creating.value = true; createError.value = ''
  try {
    const { data } = await axios.post('/api/dos', { dossier_id: createDossierId.value }, { headers: headers() })
    showCreate.value = false
    router.push(`/dos/${data.id}`)
  } catch (e: any) { createError.value = e.response?.data?.detail ?? 'Erreur.' }
  finally { creating.value = false }
}

onMounted(load)
</script>
