<template>
  <AppLayout>
    <div class="p-6 space-y-5">
      <!-- Header -->
      <div class="flex items-center gap-3">
        <RouterLink to="/dossiers" class="text-gray-400 hover:text-gray-600">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
        </RouterLink>
        <div class="flex-1">
          <div class="flex items-center gap-3">
            <h1 class="text-xl font-semibold text-gray-900 font-mono">{{ dossier?.reference }}</h1>
            <span v-if="dossier" :class="statutBadge(dossier.statut)" class="px-2.5 py-0.5 rounded-full text-xs font-medium">{{ statutLabel(dossier.statut) }}</span>
          </div>
          <p class="text-sm text-gray-500 mt-0.5" v-if="dossier">
            {{ typeClientLabel(dossier.type_client) }} · {{ operationLabel(dossier.type_operation) }}
          </p>
        </div>
        <div v-if="dossier?.classification" class="flex items-center gap-2">
          <span :class="classBadge(dossier.classification)" class="px-3 py-1 rounded-full text-sm font-medium">
            {{ dossier.classification }}{{ dossier.force_par_trigger ? ' ⚡' : '' }} — {{ dossier.score_base }}/20
          </span>
        </div>
      </div>

      <div v-if="loading" class="flex items-center justify-center py-12 text-gray-400 text-sm">Chargement…</div>
      <div v-else-if="!dossier" class="text-center py-12 text-gray-400">Dossier introuvable.</div>

      <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <!-- Colonne principale -->
        <div class="lg:col-span-2 space-y-4">

          <!-- KYC Summary card -->
          <div class="bg-white rounded-xl border border-gray-200 p-5">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-sm font-semibold text-gray-700">Fiche KYC</h2>
              <RouterLink :to="kycRoute" class="text-xs text-[#1a2e4a] hover:underline font-medium">
                {{ kycData ? 'Modifier' : 'Saisir KYC' }} →
              </RouterLink>
            </div>
            <div v-if="!kycData" class="flex flex-col items-center py-6 text-gray-400">
              <span class="text-3xl mb-2">📋</span>
              <p class="text-sm">KYC non renseigné.</p>
              <RouterLink :to="kycRoute" class="mt-2 text-xs text-[#1a2e4a] hover:underline">Saisir maintenant →</RouterLink>
            </div>
            <div v-else class="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <template v-if="dossier.type_client !== 'PM'">
                <div><span class="text-xs text-gray-500">Nom complet</span><p class="font-medium text-gray-900">{{ kycData.nom }} {{ kycData.prenoms }}</p></div>
                <div><span class="text-xs text-gray-500">Date de naissance</span><p>{{ kycData.date_naissance ?? '—' }}</p></div>
                <div><span class="text-xs text-gray-500">Nationalité</span><p>{{ kycData.nationalite ?? '—' }}</p></div>
                <div><span class="text-xs text-gray-500">Téléphone</span><p>{{ kycData.telephone ?? '—' }}</p></div>
                <div><span class="text-xs text-gray-500">Profession</span><p>{{ kycData.profession ?? '—' }}</p></div>
                <div><span class="text-xs text-gray-500">PPE</span>
                  <p><span :class="kycData.est_ppe ? 'text-orange-600 font-semibold' : 'text-gray-600'">{{ kycData.est_ppe ? '⚡ Oui' : 'Non' }}</span></p>
                </div>
                <div v-if="kycData.non_resident"><span class="text-xs text-gray-500">Résidence</span><p class="text-amber-600 font-medium">Non-résident · {{ kycData.pays_residence }}</p></div>
              </template>
              <template v-else>
                <div class="col-span-2"><span class="text-xs text-gray-500">Dénomination sociale</span><p class="font-medium text-gray-900">{{ kycData.denomination_sociale }}</p></div>
                <div><span class="text-xs text-gray-500">Forme juridique</span><p>{{ kycData.forme_juridique ?? '—' }}</p></div>
                <div><span class="text-xs text-gray-500">RCCM</span><p>{{ kycData.numero_rccm ?? '—' }}</p></div>
                <div><span class="text-xs text-gray-500">Représentant légal</span><p>{{ kycData.nom_representant_legal ?? '—' }}</p></div>
                <div><span class="text-xs text-gray-500">PPE détectée</span>
                  <p><span :class="kycData.ppe_detectee ? 'text-orange-600 font-semibold' : 'text-gray-600'">{{ kycData.ppe_detectee ? '⚡ Oui' : 'Non' }}</span></p>
                </div>
              </template>
            </div>
          </div>

          <!-- Commentaires internes -->
          <div class="bg-white rounded-xl border border-gray-200 p-5">
            <h2 class="text-sm font-semibold text-gray-700 mb-4">Commentaires internes</h2>
            <div v-if="comments.length === 0" class="text-sm text-gray-400 py-2">Aucun commentaire.</div>
            <div v-else class="space-y-3 mb-4">
              <div v-for="c in comments" :key="c.id" class="flex gap-3">
                <div class="w-7 h-7 rounded-full bg-[#1a2e4a]/10 flex items-center justify-center text-xs font-bold text-[#1a2e4a] flex-shrink-0">C</div>
                <div class="flex-1 bg-gray-50 rounded-lg p-3">
                  <p class="text-sm text-gray-800">{{ c.contenu }}</p>
                  <p class="text-xs text-gray-400 mt-1">{{ formatDate(c.created_at) }}</p>
                </div>
              </div>
            </div>
            <div class="flex gap-2">
              <input v-model="newComment" @keydown.enter.prevent="addComment" class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]" placeholder="Ajouter un commentaire…" />
              <button @click="addComment" :disabled="!newComment.trim()" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-40 transition-colors">Envoyer</button>
            </div>
          </div>
        </div>

        <!-- Colonne droite -->
        <div class="space-y-4">

          <!-- Score card -->
          <div v-if="dossier.classification" class="bg-white rounded-xl border border-gray-200 p-4">
            <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Score de risque</h3>
            <div class="text-center mb-3">
              <div class="text-4xl font-bold" :class="scoreColor(dossier.classification)">{{ dossier.score_base }}<span class="text-lg font-normal text-gray-400">/20</span></div>
              <div :class="classBadge(dossier.classification)" class="inline-flex px-3 py-1 rounded-full text-sm font-medium mt-1">{{ dossier.classification }}</div>
              <div v-if="dossier.force_par_trigger" class="text-xs text-orange-600 mt-1">⚡ Forcé par Trigger {{ dossier.trigger_actif }}</div>
            </div>
            <div class="text-xs text-gray-400 text-center">
              {{ dossier.classification === 'FAIBLE' ? 'Révision dans 5 ans' : dossier.classification === 'MOYEN' ? 'Révision dans 3 ans' : 'Révision dans 2 ans' }}
            </div>
          </div>

          <!-- Workflow actions -->
          <div v-if="isSupervisor" class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
            <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Workflow</h3>
            <div class="space-y-2">
              <button
                v-for="action in workflowActions"
                :key="action.statut"
                @click="changeStatut(action.statut)"
                :disabled="dossier.statut === action.statut || workflowLoading"
                :class="[action.class, 'w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed']"
              >
                {{ action.label }}
              </button>
            </div>
            <div v-if="workflowError" class="text-xs text-red-600">{{ workflowError }}</div>
          </div>

          <!-- Historique -->
          <div class="bg-white rounded-xl border border-gray-200 p-4">
            <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Historique</h3>
            <div v-if="historique.length === 0" class="text-xs text-gray-400">Aucun historique.</div>
            <div v-else class="space-y-2">
              <div v-for="h in historique" :key="h.id" class="flex gap-2 text-xs">
                <div class="w-1.5 h-1.5 rounded-full bg-[#1a2e4a] mt-1.5 flex-shrink-0"></div>
                <div>
                  <span :class="statutBadge(h.statut_apres)" class="px-1.5 py-0.5 rounded text-xs font-medium">{{ statutLabel(h.statut_apres) }}</span>
                  <p class="text-gray-400 mt-0.5">{{ formatDate(h.created_at) }}</p>
                  <p v-if="h.commentaire" class="text-gray-600 italic">{{ h.commentaire }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Info dossier -->
          <div class="bg-white rounded-xl border border-gray-200 p-4">
            <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Informations</h3>
            <div class="space-y-2 text-xs">
              <div class="flex justify-between"><span class="text-gray-500">Type client</span><span :class="typeClientBadge(dossier.type_client)" class="px-1.5 py-0.5 rounded font-medium">{{ dossier.type_client }}</span></div>
              <div class="flex justify-between"><span class="text-gray-500">Opération</span><span class="text-gray-700">{{ operationLabel(dossier.type_operation) }}</span></div>
              <div class="flex justify-between"><span class="text-gray-500">Assigné à</span><span class="text-gray-700">{{ dossier.assigned_to ? dossier.assigned_to.substring(0, 8) + '…' : '—' }}</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import axios from 'axios'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const dossierId = route.params.id as string

interface Dossier {
  id: string; reference: string; type_client: string; type_operation: string
  type_operation_detail: string | null; statut: string; score_base: number | null
  classification: string | null; force_par_trigger: boolean; trigger_actif: string | null
  assigned_to: string | null; created_by: string
}
interface Historique { id: string; statut_avant: string | null; statut_apres: string; commentaire: string | null; created_at: string }
interface Commentaire { id: string; contenu: string; user_id: string; created_at: string }

const dossier = ref<Dossier | null>(null)
const kycData = ref<any>(null)
const historique = ref<Historique[]>([])
const comments = ref<Commentaire[]>([])
const loading = ref(true)
const newComment = ref('')
const workflowLoading = ref(false)
const workflowError = ref('')

const isSupervisor = computed(() => {
  const role = auth.role
  return role === 'admin' || role === 'notaire_principal' || role === 'responsable_conformite'
})

const kycRoute = computed(() => {
  if (!dossier.value) return '/dossiers'
  return dossier.value.type_client === 'PM' ? `/dossiers/${dossierId}/kyc/pm` : `/dossiers/${dossierId}/kyc/pp`
})

const workflowActions = [
  { statut: 'en_analyse', label: 'Passer en analyse', class: 'bg-blue-50 text-blue-700 hover:bg-blue-100' },
  { statut: 'vigilance_renforcee', label: 'Vigilance renforcée', class: 'bg-orange-50 text-orange-700 hover:bg-orange-100' },
  { statut: 'valide', label: 'Valider le dossier', class: 'bg-green-50 text-green-700 hover:bg-green-100' },
  { statut: 'bloque', label: 'Bloquer', class: 'bg-red-50 text-red-700 hover:bg-red-100' },
  { statut: 'traite', label: 'Marquer traité', class: 'bg-teal-50 text-teal-700 hover:bg-teal-100' },
  { statut: 'cloture', label: 'Clôturer', class: 'bg-purple-50 text-purple-700 hover:bg-purple-100' },
]

function headers() { return auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {} }
function formatDate(s: string) { return new Date(s).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }
function classBadge(c: string) { return c === 'ELEVE' ? 'bg-red-100 text-red-700' : c === 'MOYEN' ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700' }
function scoreColor(c: string) { return c === 'ELEVE' ? 'text-red-600' : c === 'MOYEN' ? 'text-orange-500' : 'text-green-600' }
function typeClientBadge(t: string) { return t === 'PP' ? 'bg-blue-100 text-blue-700' : t === 'PM' ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600' }
function typeClientLabel(t: string) { const m: Record<string, string> = { PP: 'Personne Physique', PM: 'Personne Morale', Association: 'Association', Indivision: 'Indivision' }; return m[t] ?? t }
function operationLabel(op: string) { const m: Record<string, string> = { vente_immobiliere: 'Vente immobilière', manipulation_fonds: 'Manipulation fonds', constitution_societe: 'Constitution société', fiducicommis: 'Fiducicommis', succession: 'Succession', donation: 'Donation', autre: 'Autre' }; return m[op] ?? op }
function statutLabel(s: string) { const m: Record<string, string> = { brouillon: 'Brouillon', en_analyse: 'En analyse', vigilance_renforcee: 'Vigilance renforcée', valide: 'Validé', bloque: 'Bloqué', traite: 'Traité', cloture: 'Clôturé', archive: 'Archivé' }; return m[s] ?? s }
function statutBadge(s: string) { const m: Record<string, string> = { brouillon: 'bg-gray-100 text-gray-600', en_analyse: 'bg-blue-100 text-blue-700', vigilance_renforcee: 'bg-orange-100 text-orange-700', valide: 'bg-green-100 text-green-700', bloque: 'bg-red-100 text-red-700', traite: 'bg-teal-100 text-teal-700', cloture: 'bg-purple-100 text-purple-700', archive: 'bg-gray-200 text-gray-500' }; return m[s] ?? 'bg-gray-100 text-gray-600' }

async function loadDossier() {
  loading.value = true
  try {
    const { data: d } = await axios.get(`/api/dossiers/${dossierId}`, { headers: headers() })
    dossier.value = d
    // Load KYC
    try {
      const kycUrl = d.type_client === 'PM' ? `/api/dossiers/${dossierId}/kyc/pm` : `/api/dossiers/${dossierId}/kyc/pp`
      const { data: kyc } = await axios.get(kycUrl, { headers: headers() })
      kycData.value = kyc
    } catch {}
    // Load historique via audit
    try {
      const { data: auditData } = await axios.get(`/api/audit/logs`, {
        params: { entity_type: 'dossier', entity_id: dossierId, limit: 20 },
        headers: headers()
      })
      historique.value = (auditData.items ?? [])
        .filter((l: any) => l.action === 'dossier.statut_change')
        .map((l: any) => ({
          id: l.id,
          statut_avant: l.detail?.statut_avant ?? null,
          statut_apres: l.detail?.statut ?? l.detail?.statut_apres ?? '?',
          commentaire: l.detail?.commentaire ?? null,
          created_at: l.created_at,
        }))
    } catch {}
  } catch {}
  finally { loading.value = false }
}

async function changeStatut(newStatut: string) {
  if (!dossier.value) return
  workflowLoading.value = true; workflowError.value = ''
  try {
    const { data } = await axios.patch(
      `/api/dossiers/${dossierId}/statut`,
      null,
      { params: { new_statut: newStatut }, headers: headers() }
    )
    dossier.value = data
    await loadDossier()
  } catch (e: any) {
    workflowError.value = e.response?.data?.detail ?? 'Erreur changement statut.'
  } finally { workflowLoading.value = false }
}

async function addComment() {
  if (!newComment.value.trim()) return
  try {
    await axios.post(`/api/dossiers/${dossierId}/commentaires`, { contenu: newComment.value }, { headers: headers() })
    comments.value.push({ id: Date.now().toString(), contenu: newComment.value, user_id: auth.user?.id ?? '', created_at: new Date().toISOString() })
    newComment.value = ''
  } catch {}
}

onMounted(loadDossier)
</script>
