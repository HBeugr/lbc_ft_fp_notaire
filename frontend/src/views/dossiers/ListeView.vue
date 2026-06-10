<template>
  <div class="p-6 space-y-5">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-xl font-semibold text-gray-900">Dossiers clients</h1>
          <p class="text-sm text-gray-500 mt-0.5">{{ dossiers.length }} dossier(s)</p>
        </div>
        <button @click="showCreate = true" class="flex items-center gap-2 bg-[#1a2e4a] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#1a2e4a]/90 transition-colors">
          + Nouveau dossier
        </button>
      </div>

      <!-- Filtres -->
      <div class="flex gap-3 flex-wrap">
        <select v-model="filterStatut" class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30">
          <option value="">Tous les statuts</option>
          <option v-for="s in STATUTS" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <select v-model="filterClass" class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30">
          <option value="">Toutes classifications</option>
          <option value="FAIBLE">Risque faible</option>
          <option value="MOYEN">Risque moyen</option>
          <option value="ELEVE">Risque élevé</option>
        </select>
        <button @click="loadDossiers" class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
          Actualiser
        </button>
      </div>

      <!-- Error -->
      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">{{ error }}</div>

      <!-- Table -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div v-if="loading" class="flex items-center justify-center py-12 text-gray-400 text-sm">Chargement…</div>
        <div v-else-if="dossiers.length === 0" class="flex flex-col items-center justify-center py-12 text-gray-400">
          <span class="text-4xl mb-3">📁</span>
          <p class="text-sm">Aucun dossier. Créez le premier.</p>
        </div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Référence</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Type</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Opération</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Statut</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Risque</th>
              <th class="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="d in dossiers" :key="d.id" class="hover:bg-gray-50 transition-colors">
              <td class="px-4 py-3">
                <span class="font-mono text-xs font-medium text-[#1a2e4a]">{{ d.reference }}</span>
              </td>
              <td class="px-4 py-3">
                <span :class="typeClientBadge(d.type_client)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ d.type_client }}</span>
              </td>
              <td class="px-4 py-3 text-gray-600">{{ operationLabel(d.type_operation) }}</td>
              <td class="px-4 py-3">
                <span :class="statutBadge(d.statut)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ statutLabel(d.statut) }}</span>
              </td>
              <td class="px-4 py-3">
                <span v-if="d.classification" :class="classBadge(d.classification)" class="px-2 py-0.5 rounded-full text-xs font-medium">
                  {{ d.classification }}{{ d.force_par_trigger ? ' ⚡' : '' }} {{ d.score_base !== null ? `(${d.score_base}/20)` : '' }}
                </span>
                <span v-else class="text-gray-400 text-xs">—</span>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-1">
                  <RouterLink
                    :to="kycRoute(d)"
                    class="p-1.5 rounded-lg text-gray-400 hover:text-[#1a2e4a] hover:bg-gray-100 transition-colors"
                    title="Saisir KYC"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                  </RouterLink>
                  <RouterLink
                    :to="`/dossiers/${d.id}`"
                    class="p-1.5 rounded-lg text-gray-400 hover:text-[#1a2e4a] hover:bg-gray-100 transition-colors"
                    title="Voir détail"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                  </RouterLink>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 class="font-semibold text-gray-900">Nouveau dossier</h2>
          <button @click="showCreate = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="submitCreate" class="p-5 space-y-4">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Nature du client</label>
            <select v-model="createForm.type_client" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]">
              <option value="PP">Personne Physique (PP)</option>
              <option value="PM">Personne Morale (PM)</option>
              <option value="Association">Association</option>
              <option value="Indivision">Indivision</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Nature de l'opération</label>
            <select v-model="createForm.type_operation" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]">
              <option value="vente_immobiliere">Vente immobilière</option>
              <option value="manipulation_fonds">Manipulation de fonds</option>
              <option value="constitution_societe">Constitution de société</option>
              <option value="fiducicommis">Fiducicommis</option>
              <option value="succession">Succession</option>
              <option value="donation">Donation</option>
              <option value="autre">Autre</option>
            </select>
          </div>
          <div v-if="createForm.type_operation === 'autre'">
            <label class="block text-xs font-medium text-gray-700 mb-1">Préciser</label>
            <input v-model="createForm.type_operation_detail" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]" />
          </div>
          <div v-if="createError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ createError }}</div>
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" @click="showCreate = false" class="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">Annuler</button>
            <button type="submit" :disabled="creating" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm font-medium rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50 transition-colors">
              {{ creating ? 'Création…' : 'Créer' }}
            </button>
          </div>
        </form>
      </div>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

interface Dossier {
  id: string; reference: string; type_client: string; type_operation: string
  type_operation_detail: string | null; statut: string; score_base: number | null
  classification: string | null; force_par_trigger: boolean; trigger_actif: string | null
  assigned_to: string | null; created_by: string
}

const auth = useAuthStore()
const router = useRouter()
const dossiers = ref<Dossier[]>([])
const loading = ref(true)
const error = ref('')
const filterStatut = ref('')
const filterClass = ref('')
const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')

const createForm = reactive({ type_client: 'PP', type_operation: 'vente_immobiliere', type_operation_detail: '' })

const STATUTS = [
  { value: 'brouillon', label: 'Brouillon' }, { value: 'en_analyse', label: 'En analyse' },
  { value: 'vigilance_renforcee', label: 'Vigilance renforcée' }, { value: 'valide', label: 'Validé' },
  { value: 'bloque', label: 'Bloqué' }, { value: 'traite', label: 'Traité' },
  { value: 'cloture', label: 'Clôturé' }, { value: 'archive', label: 'Archivé' },
]

function headers() { return auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {} }

async function loadDossiers() {
  loading.value = true; error.value = ''
  try {
    const params: Record<string, string> = {}
    if (filterStatut.value) params.statut = filterStatut.value
    if (filterClass.value) params.classification = filterClass.value
    const { data } = await axios.get('/api/dossiers', { params, headers: headers() })
    dossiers.value = data
  } catch (e: any) { error.value = e.response?.data?.detail ?? 'Erreur de chargement.' }
  finally { loading.value = false }
}

watch([filterStatut, filterClass], loadDossiers)

async function submitCreate() {
  creating.value = true; createError.value = ''
  try {
    const { data } = await axios.post('/api/dossiers', {
      type_client: createForm.type_client,
      type_operation: createForm.type_operation,
      type_operation_detail: createForm.type_operation_detail || null,
    }, { headers: headers() })
    showCreate.value = false
    router.push(kycRoute(data))
  } catch (e: any) { createError.value = e.response?.data?.detail ?? 'Erreur lors de la création.' }
  finally { creating.value = false }
}

function kycRoute(d: Dossier) {
  return d.type_client === 'PM' ? `/dossiers/${d.id}/kyc/pm` : `/dossiers/${d.id}/kyc/pp`
}

function operationLabel(op: string) {
  const m: Record<string, string> = {
    vente_immobiliere: 'Vente immobilière', manipulation_fonds: 'Manipulation fonds',
    constitution_societe: 'Constitution société', fiducicommis: 'Fiducicommis',
    succession: 'Succession', donation: 'Donation', autre: 'Autre',
  }
  return m[op] ?? op
}

function typeClientBadge(t: string) {
  return t === 'PP' ? 'bg-blue-100 text-blue-700' : t === 'PM' ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600'
}

function statutLabel(s: string) { return STATUTS.find(x => x.value === s)?.label ?? s }
function statutBadge(s: string) {
  const m: Record<string, string> = {
    brouillon: 'bg-gray-100 text-gray-600', en_analyse: 'bg-blue-100 text-blue-700',
    vigilance_renforcee: 'bg-orange-100 text-orange-700', valide: 'bg-green-100 text-green-700',
    bloque: 'bg-red-100 text-red-700', traite: 'bg-teal-100 text-teal-700',
    cloture: 'bg-purple-100 text-purple-700', archive: 'bg-gray-200 text-gray-500',
  }
  return m[s] ?? 'bg-gray-100 text-gray-600'
}

function classBadge(c: string) {
  return c === 'ELEVE' ? 'bg-red-100 text-red-700' : c === 'MOYEN' ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'
}

onMounted(loadDossiers)
</script>
