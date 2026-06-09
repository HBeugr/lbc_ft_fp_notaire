<template>
  <AppLayout>
    <div class="p-6 space-y-5">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-xl font-semibold text-gray-900">Alertes</h1>
          <p class="text-sm text-gray-500 mt-0.5">{{ alertes.length }} alerte(s)</p>
        </div>
        <div v-if="isSupervisor" class="flex gap-2">
          <button @click="showCreate = true" class="flex items-center gap-2 bg-[#1a2e4a] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#1a2e4a]/90 transition-colors">
            + Nouvelle alerte
          </button>
        </div>
      </div>

      <!-- Filtres -->
      <div class="flex gap-3 flex-wrap">
        <select v-model="filterStatut" class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none">
          <option value="">Tous les statuts</option>
          <option value="ouverte">Ouvertes</option>
          <option value="en_cours">En cours</option>
          <option value="traitee">Traitées</option>
          <option value="ignoree">Ignorées</option>
        </select>
        <select v-model="filterNiveau" class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none">
          <option value="">Tous les niveaux</option>
          <option value="ELEVE">Élevé</option>
          <option value="MOYEN">Moyen</option>
          <option value="FAIBLE">Faible</option>
        </select>
        <button @click="load" class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">Actualiser</button>
      </div>

      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">{{ error }}</div>

      <!-- Table -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div v-if="loading" class="flex items-center justify-center py-12 text-gray-400 text-sm">Chargement…</div>
        <div v-else-if="alertes.length === 0" class="flex flex-col items-center justify-center py-12 text-gray-400">
          <span class="text-4xl mb-3">🔔</span>
          <p class="text-sm">Aucune alerte.</p>
        </div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Type</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Niveau</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Statut</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Dossier</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Description</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Date</th>
              <th class="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="a in alertes" :key="a.id" class="hover:bg-gray-50 transition-colors">
              <td class="px-4 py-3">
                <span class="font-medium text-gray-900 text-xs">{{ typeLabel(a.type_alerte) }}</span>
              </td>
              <td class="px-4 py-3">
                <span :class="niveauBadge(a.niveau)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ a.niveau }}</span>
              </td>
              <td class="px-4 py-3">
                <span :class="statutBadge(a.statut)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ statutLabel(a.statut) }}</span>
              </td>
              <td class="px-4 py-3">
                <RouterLink :to="`/dossiers/${a.dossier_id}`" class="text-xs font-mono text-[#1a2e4a] hover:underline">{{ a.dossier_id.substring(0, 8) }}…</RouterLink>
              </td>
              <td class="px-4 py-3 text-gray-500 text-xs max-w-xs truncate">{{ a.description ?? '—' }}</td>
              <td class="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">{{ formatDate(a.created_at) }}</td>
              <td class="px-4 py-3">
                <div v-if="isSupervisor && a.statut === 'ouverte'" class="flex items-center justify-end gap-1">
                  <button @click="openTraiter(a, 'en_cours')" class="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded hover:bg-blue-100">En cours</button>
                  <button @click="openTraiter(a, 'traitee')" class="px-2 py-1 text-xs bg-green-50 text-green-700 rounded hover:bg-green-100">Traiter</button>
                  <button @click="openTraiter(a, 'ignoree')" class="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200">Ignorer</button>
                </div>
                <div v-else-if="a.resolution_note" class="text-xs text-gray-400 italic truncate max-w-xs">{{ a.resolution_note }}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Traiter modal -->
    <div v-if="traitModal.show" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 class="font-semibold text-gray-900">Traiter l'alerte</h2>
          <button @click="traitModal.show = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="submitTraiter" class="p-5 space-y-4">
          <p class="text-sm text-gray-600">
            Statut : <span :class="statutBadge(traitModal.statut)" class="px-2 py-0.5 rounded-full text-xs font-medium ml-1">{{ statutLabel(traitModal.statut) }}</span>
          </p>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Note de résolution</label>
            <textarea v-model="traitModal.note" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 resize-none" placeholder="Décrire les actions prises…" />
          </div>
          <div v-if="traitModal.error" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ traitModal.error }}</div>
          <div class="flex justify-end gap-3">
            <button type="button" @click="traitModal.show = false" class="px-4 py-2 text-sm text-gray-600">Annuler</button>
            <button type="submit" :disabled="traitModal.loading" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50">
              {{ traitModal.loading ? 'Enregistrement…' : 'Confirmer' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 class="font-semibold text-gray-900">Nouvelle alerte manuelle</h2>
          <button @click="showCreate = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="submitCreate" class="p-5 space-y-4">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">ID Dossier</label>
            <input v-model="createForm.dossier_id" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Type</label>
            <select v-model="createForm.type_alerte" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
              <option v-for="t in TYPE_OPTIONS" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Niveau</label>
            <select v-model="createForm.niveau" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none">
              <option value="FAIBLE">Faible</option>
              <option value="MOYEN">Moyen</option>
              <option value="ELEVE">Élevé</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Description</label>
            <textarea v-model="createForm.description" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none resize-none" />
          </div>
          <div v-if="createError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ createError }}</div>
          <div class="flex justify-end gap-3">
            <button type="button" @click="showCreate = false" class="px-4 py-2 text-sm text-gray-600">Annuler</button>
            <button type="submit" :disabled="creating" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50">
              {{ creating ? 'Création…' : 'Créer' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import axios from 'axios'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

interface Alerte {
  id: string; dossier_id: string; type_alerte: string; niveau: string; statut: string
  description: string | null; traite_par: string | null; traite_at: string | null
  resolution_note: string | null; created_at: string
}

const auth = useAuthStore()
const alertes = ref<Alerte[]>([])
const loading = ref(true)
const error = ref('')
const filterStatut = ref('')
const filterNiveau = ref('')
const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')

const isSupervisor = computed(() => ['admin', 'notaire_principal', 'responsable_conformite'].includes(auth.role ?? ''))

const traitModal = reactive({ show: false, alerte: null as Alerte | null, statut: '', note: '', loading: false, error: '' })
const createForm = reactive({ dossier_id: '', type_alerte: 'AUTRE', niveau: 'MOYEN', description: '' })

const TYPE_OPTIONS = [
  { value: 'T1_PPE', label: 'T1 — PPE' },
  { value: 'T2_ESPECES', label: 'T2 — Espèces > 15M' },
  { value: 'T3_SANCTIONS', label: 'T3 — Sanctions' },
  { value: 'T4_GAFI', label: 'T4 — Pays GAFI' },
  { value: 'T5_REFUS_DOC', label: 'T5 — Refus documents' },
  { value: 'T6_BE_NON_IDENTIFIABLE', label: 'T6 — BE non identifiable' },
  { value: 'INCOHERENCE_DOC', label: 'Incohérence documentaire' },
  { value: 'MONTAGE_COMPLEXE', label: 'Montage complexe' },
  { value: 'AUTRE', label: 'Autre' },
]

function headers() { return auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {} }
function formatDate(s: string) { return new Date(s).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' }) }
function typeLabel(t: string) { return TYPE_OPTIONS.find(o => o.value === t)?.label ?? t }
function niveauBadge(n: string) { return n === 'ELEVE' ? 'bg-red-100 text-red-700' : n === 'MOYEN' ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700' }
function statutLabel(s: string) { const m: Record<string, string> = { ouverte: 'Ouverte', en_cours: 'En cours', traitee: 'Traitée', ignoree: 'Ignorée' }; return m[s] ?? s }
function statutBadge(s: string) { const m: Record<string, string> = { ouverte: 'bg-red-100 text-red-700', en_cours: 'bg-blue-100 text-blue-700', traitee: 'bg-green-100 text-green-700', ignoree: 'bg-gray-100 text-gray-500' }; return m[s] ?? 'bg-gray-100 text-gray-600' }

async function load() {
  loading.value = true; error.value = ''
  try {
    const params: Record<string, string> = {}
    if (filterStatut.value) params.statut = filterStatut.value
    if (filterNiveau.value) params.niveau = filterNiveau.value
    const { data } = await axios.get('/api/alertes', { params, headers: headers() })
    alertes.value = data
  } catch (e: any) { error.value = e.response?.data?.detail ?? 'Erreur de chargement.' }
  finally { loading.value = false }
}

watch([filterStatut, filterNiveau], load)

function openTraiter(a: Alerte, statut: string) {
  Object.assign(traitModal, { show: true, alerte: a, statut, note: '', loading: false, error: '' })
}

async function submitTraiter() {
  if (!traitModal.alerte) return
  traitModal.loading = true; traitModal.error = ''
  try {
    await axios.patch(`/api/alertes/${traitModal.alerte.id}/traiter`, { statut: traitModal.statut, resolution_note: traitModal.note || null }, { headers: headers() })
    traitModal.show = false
    await load()
  } catch (e: any) { traitModal.error = e.response?.data?.detail ?? 'Erreur.' }
  finally { traitModal.loading = false }
}

async function submitCreate() {
  creating.value = true; createError.value = ''
  try {
    await axios.post('/api/alertes', createForm, { headers: headers() })
    showCreate.value = false
    await load()
  } catch (e: any) { createError.value = e.response?.data?.detail ?? 'Erreur.' }
  finally { creating.value = false }
}

onMounted(load)
</script>
