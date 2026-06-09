<template>
  <AppLayout>
    <div class="p-6 space-y-5">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-xl font-semibold text-gray-900">Révisions Périodiques KYC</h1>
          <p class="text-sm text-gray-500 mt-0.5">Art. 19, Ordonnance n° 2023-875 — calendrier de réévaluation</p>
        </div>
        <button @click="showCreate = true" class="flex items-center gap-2 bg-[#1a2e4a] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#1a2e4a]/90 transition-colors">
          + Planifier révision
        </button>
      </div>

      <!-- Alertes en retard -->
      <div v-if="enRetard.length > 0" class="bg-red-50 border border-red-200 rounded-lg p-4">
        <p class="text-sm font-semibold text-red-700 mb-2">⚠️ {{ enRetard.length }} révision(s) en retard</p>
        <div class="space-y-1">
          <div v-for="r in enRetard.slice(0, 5)" :key="r.id" class="text-xs text-red-600 flex items-center gap-2">
            <span class="font-mono">{{ r.dossier_id.substring(0, 8) }}</span>
            <span>— échéance {{ formatDate(r.date_echeance) }}</span>
          </div>
        </div>
      </div>

      <!-- Filtres -->
      <div class="flex gap-3 flex-wrap">
        <select v-model="filterStatut" @change="load" class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none">
          <option value="">Tous les statuts</option>
          <option value="planifiee">Planifiée</option>
          <option value="en_cours">En cours</option>
          <option value="completee">Complétée</option>
          <option value="en_retard">En retard</option>
          <option value="vigilance_renforcee">Vigilance renforcée</option>
          <option value="bloquee">Bloquée</option>
        </select>
        <button @click="load" class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">Actualiser</button>
      </div>

      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">{{ error }}</div>

      <!-- Table -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div v-if="loading" class="flex items-center justify-center py-12 text-gray-400 text-sm">Chargement…</div>
        <div v-else-if="revisions.length === 0" class="flex flex-col items-center justify-center py-12 text-gray-400">
          <span class="text-4xl mb-3">📅</span>
          <p class="text-sm">Aucune révision planifiée.</p>
        </div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Dossier</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Échéance</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Statut</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Classification</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Assignée à</th>
              <th class="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="r in revisions" :key="r.id" class="hover:bg-gray-50 transition-colors">
              <td class="px-4 py-3">
                <RouterLink :to="`/dossiers/${r.dossier_id}`" class="font-mono text-xs text-[#1a2e4a] hover:underline">{{ r.dossier_id.substring(0, 8) }}…</RouterLink>
              </td>
              <td class="px-4 py-3">
                <span :class="isOverdue(r.date_echeance) && r.statut !== 'completee' ? 'text-red-600 font-semibold' : 'text-gray-700'" class="text-xs">
                  {{ formatDate(r.date_echeance) }}
                </span>
              </td>
              <td class="px-4 py-3">
                <span :class="statutBadge(r.statut)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ statutLabel(r.statut) }}</span>
              </td>
              <td class="px-4 py-3">
                <div class="text-xs text-gray-600">
                  <span v-if="r.classification_avant" :class="classBadge(r.classification_avant)" class="px-1.5 py-0.5 rounded text-xs">{{ r.classification_avant }}</span>
                  <span v-if="r.classification_apres" class="text-gray-400 mx-1">→</span>
                  <span v-if="r.classification_apres" :class="classBadge(r.classification_apres)" class="px-1.5 py-0.5 rounded text-xs">{{ r.classification_apres }}</span>
                </div>
              </td>
              <td class="px-4 py-3 text-xs text-gray-500 font-mono">{{ r.assigned_to ? r.assigned_to.substring(0, 8) + '…' : '—' }}</td>
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-1">
                  <button v-if="r.statut !== 'completee'" @click="openEdit(r)" class="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50">Modifier</button>
                  <button v-if="r.statut === 'en_cours'" @click="openValider(r)" class="px-2 py-1 text-xs bg-green-700 text-white rounded hover:bg-green-800">Valider</button>
                </div>
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
          <h2 class="font-semibold text-gray-900">Planifier une révision</h2>
          <button @click="showCreate = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="submitCreate" class="p-5 space-y-4">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">ID Dossier</label>
            <input v-model="createForm.dossier_id" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none" placeholder="UUID du dossier" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Date d'échéance</label>
            <input v-model="createForm.date_echeance" required type="date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none" />
          </div>
          <div v-if="createError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ createError }}</div>
          <div class="flex justify-end gap-3">
            <button type="button" @click="showCreate = false" class="px-4 py-2 text-sm text-gray-600">Annuler</button>
            <button type="submit" :disabled="creating" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm rounded-lg disabled:opacity-50">
              {{ creating ? 'Création…' : 'Planifier' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit modal -->
    <div v-if="showEdit && editTarget" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 class="font-semibold text-gray-900">Modifier la révision</h2>
          <button @click="showEdit = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="submitEdit" class="p-5 space-y-4">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Statut</label>
            <select v-model="editForm.statut" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
              <option value="planifiee">Planifiée</option>
              <option value="en_cours">En cours</option>
              <option value="en_retard">En retard</option>
              <option value="vigilance_renforcee">Vigilance renforcée</option>
              <option value="bloquee">Bloquée</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Justification</label>
            <textarea v-model="editForm.justification" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none h-20 resize-none" />
          </div>
          <div v-if="editError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ editError }}</div>
          <div class="flex justify-end gap-3">
            <button type="button" @click="showEdit = false" class="px-4 py-2 text-sm text-gray-600">Annuler</button>
            <button type="submit" :disabled="editing" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm rounded-lg disabled:opacity-50">
              {{ editing ? 'Enregistrement…' : 'Enregistrer' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Valider modal -->
    <div v-if="showValider && validerTarget" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 class="font-semibold text-gray-900">Valider la révision</h2>
          <button @click="showValider = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="submitValider" class="p-5 space-y-4">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Note de validation</label>
            <textarea v-model="validerJustification" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none h-24 resize-none" placeholder="Résumé de la révision effectuée…" />
          </div>
          <div v-if="validerError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ validerError }}</div>
          <div class="flex justify-end gap-3">
            <button type="button" @click="showValider = false" class="px-4 py-2 text-sm text-gray-600">Annuler</button>
            <button type="submit" :disabled="validant" class="px-4 py-2 bg-green-700 text-white text-sm rounded-lg disabled:opacity-50">
              {{ validant ? 'Validation…' : 'Valider la révision' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import axios from 'axios'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

interface Revision {
  id: string; dossier_id: string; statut: string; date_echeance: string
  date_relance_1: string | null; date_relance_2: string | null; date_validation: string | null
  classification_avant: string | null; classification_apres: string | null
  score_avant: number | null; score_apres: number | null
  assigned_to: string | null; valide_par: string | null; justification: string | null; created_at: string
}

const auth = useAuthStore()
const revisions = ref<Revision[]>([])
const enRetard = ref<Revision[]>([])
const loading = ref(true)
const error = ref('')
const filterStatut = ref('')
const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const createForm = reactive({ dossier_id: '', date_echeance: '' })
const showEdit = ref(false)
const editing = ref(false)
const editError = ref('')
const editTarget = ref<Revision | null>(null)
const editForm = reactive({ statut: '', justification: '' })
const showValider = ref(false)
const validant = ref(false)
const validerError = ref('')
const validerTarget = ref<Revision | null>(null)
const validerJustification = ref('')

function headers() { return auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {} }
function formatDate(s: string) { return new Date(s).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' }) }
function isOverdue(d: string) { return new Date(d) < new Date() }
function statutLabel(s: string) { const m: Record<string, string> = { planifiee: 'Planifiée', en_cours: 'En cours', completee: 'Complétée', en_retard: 'En retard', vigilance_renforcee: 'Vigilance renforcée', bloquee: 'Bloquée' }; return m[s] ?? s }
function statutBadge(s: string) { const m: Record<string, string> = { planifiee: 'bg-blue-100 text-blue-700', en_cours: 'bg-orange-100 text-orange-700', completee: 'bg-green-100 text-green-700', en_retard: 'bg-red-100 text-red-700', vigilance_renforcee: 'bg-purple-100 text-purple-700', bloquee: 'bg-gray-200 text-gray-600' }; return m[s] ?? 'bg-gray-100 text-gray-600' }
function classBadge(c: string) { return c === 'ELEVE' ? 'bg-red-100 text-red-700' : c === 'MOYEN' ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700' }

async function load() {
  loading.value = true; error.value = ''
  try {
    const params: Record<string, string> = {}
    if (filterStatut.value) params.statut = filterStatut.value
    const [revRes, retardRes] = await Promise.all([
      axios.get('/api/revisions', { params, headers: headers() }),
      axios.get('/api/revisions/en-retard', { headers: headers() }),
    ])
    revisions.value = revRes.data
    enRetard.value = retardRes.data
  } catch (e: any) { error.value = e.response?.data?.detail ?? 'Erreur de chargement.' }
  finally { loading.value = false }
}

async function submitCreate() {
  creating.value = true; createError.value = ''
  try {
    const { data } = await axios.post('/api/revisions', { ...createForm }, { headers: headers() })
    revisions.value.unshift(data)
    showCreate.value = false
    Object.assign(createForm, { dossier_id: '', date_echeance: '' })
  } catch (e: any) { createError.value = e.response?.data?.detail ?? 'Erreur.' }
  finally { creating.value = false }
}

function openEdit(r: Revision) {
  editTarget.value = r
  editForm.statut = r.statut
  editForm.justification = r.justification || ''
  showEdit.value = true
}

async function submitEdit() {
  if (!editTarget.value) return
  editing.value = true; editError.value = ''
  try {
    const { data } = await axios.patch(`/api/revisions/${editTarget.value.id}`, { ...editForm }, { headers: headers() })
    const idx = revisions.value.findIndex(r => r.id === editTarget.value!.id)
    if (idx !== -1) revisions.value[idx] = data
    showEdit.value = false
  } catch (e: any) { editError.value = e.response?.data?.detail ?? 'Erreur.' }
  finally { editing.value = false }
}

function openValider(r: Revision) {
  validerTarget.value = r
  validerJustification.value = ''
  showValider.value = true
}

async function submitValider() {
  if (!validerTarget.value) return
  validant.value = true; validerError.value = ''
  try {
    const { data } = await axios.post(`/api/revisions/${validerTarget.value.id}/valider`, { justification: validerJustification.value }, { headers: headers() })
    const idx = revisions.value.findIndex(r => r.id === validerTarget.value!.id)
    if (idx !== -1) revisions.value[idx] = data
    showValider.value = false
  } catch (e: any) { validerError.value = e.response?.data?.detail ?? 'Erreur.' }
  finally { validant.value = false }
}

onMounted(load)
</script>
