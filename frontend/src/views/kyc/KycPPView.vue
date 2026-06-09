<template>
  <AppLayout>
    <div class="p-6 space-y-5">
      <!-- Header -->
      <div class="flex items-center gap-3">
        <RouterLink to="/dossiers" class="text-gray-400 hover:text-gray-600">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
        </RouterLink>
        <div>
          <h1 class="text-xl font-semibold text-gray-900">KYC — Personne Physique</h1>
          <p class="text-sm text-gray-500">Dossier {{ dossierRef || dossierId }}</p>
        </div>
        <div v-if="scoreResult" class="ml-auto">
          <span :class="classBadge(scoreResult.classification)" class="px-3 py-1 rounded-full text-sm font-medium">
            {{ scoreResult.classification }}{{ scoreResult.force_par_trigger ? ' ⚡' : '' }} — {{ scoreResult.score }}/20
          </span>
        </div>
      </div>

      <!-- Stepper tabs -->
      <div class="flex border-b border-gray-200">
        <button
          v-for="(step, i) in steps"
          :key="i"
          @click="currentStep = i"
          :class="[
            'flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px',
            currentStep === i ? 'text-[#1a2e4a] border-[#1a2e4a]' : 'text-gray-500 border-transparent hover:text-gray-700',
          ]"
        >
          <span :class="['w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold', currentStep === i ? 'bg-[#1a2e4a] text-white' : 'bg-gray-200 text-gray-600']">{{ i + 1 }}</span>
          {{ step }}
        </button>
      </div>

      <!-- Messages -->
      <div v-if="saveError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">{{ saveError }}</div>
      <div v-if="saveOk" class="bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3 rounded-lg">KYC enregistré avec succès.</div>

      <!-- Form body -->
      <div class="bg-white rounded-xl border border-gray-200 p-6">

        <!-- 0 — Identité -->
        <div v-show="currentStep === 0" class="space-y-5">
          <h2 class="section-title">Identité</h2>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="label">Type de relation</label>
              <select v-model="form.relation_type" class="input">
                <option value="initiale">Entrée en relation initiale</option>
                <option value="actualisation">Actualisation</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="label">Nom <span class="req">*</span></label><input v-model="form.nom" required class="input" placeholder="Nom de famille" /></div>
            <div><label class="label">Prénoms <span class="req">*</span></label><input v-model="form.prenoms" required class="input" placeholder="Tous les prénoms" /></div>
            <div><label class="label">Nom de jeune fille</label><input v-model="form.nom_jeune_fille" class="input" placeholder="Si applicable" /></div>
            <div><label class="label">Nom & Prénoms du père</label><input v-model="form.nom_prenoms_pere" class="input" /></div>
            <div><label class="label">Nom & Prénoms de la mère</label><input v-model="form.nom_prenoms_mere" class="input" /></div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div><label class="label">Date de naissance</label><input v-model="form.date_naissance" type="date" class="input" /></div>
            <div><label class="label">Lieu de naissance</label><input v-model="form.lieu_naissance" class="input" /></div>
            <div>
              <label class="label">Statut matrimonial</label>
              <select v-model="form.statut_matrimonial" class="input">
                <option value="">—</option>
                <option>Célibataire</option><option>Marié(e)</option><option>Divorcé(e)</option><option>Veuf/Veuve</option>
              </select>
            </div>
            <div><label class="label">Nationalité</label><input v-model="form.nationalite" class="input" placeholder="Ivoirienne…" /></div>
            <div><label class="label">Autres nationalités</label><input v-model="form.autres_nationalites" class="input" /></div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="label">Type de pièce d'identité</label>
              <select v-model="form.type_piece" class="input">
                <option value="">—</option>
                <option value="CNI">CNI</option><option value="Passeport">Passeport</option>
                <option value="Titre_sejour">Titre de séjour</option><option value="Carte_consulaire">Carte consulaire</option><option value="Autre">Autre</option>
              </select>
            </div>
            <div><label class="label">Numéro de pièce</label><input v-model="form.numero_piece" class="input" /></div>
          </div>
        </div>

        <!-- 1 — Coordonnées -->
        <div v-show="currentStep === 1" class="space-y-5">
          <h2 class="section-title">Coordonnées & Résidence</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="md:col-span-2"><label class="label">Adresse géographique</label><input v-model="form.adresse_geo" class="input" placeholder="Quartier, rue, immeuble…" /></div>
            <div><label class="label">Adresse postale / BP</label><input v-model="form.adresse_postale" class="input" /></div>
            <div><label class="label">Téléphone</label><input v-model="form.telephone" class="input" placeholder="+225…" /></div>
            <div><label class="label">WhatsApp</label><input v-model="form.whatsapp" class="input" placeholder="+225…" /></div>
            <div><label class="label">Email</label><input v-model="form.email" type="email" class="input" /></div>
          </div>
          <div class="flex items-center gap-3">
            <input v-model="form.non_resident" type="checkbox" id="nr" class="w-4 h-4 rounded text-[#1a2e4a]" />
            <label for="nr" class="text-sm font-medium text-gray-700">Client Non Résident (NRI)</label>
          </div>
          <div v-if="form.non_resident">
            <label class="label">Pays de résidence</label>
            <input v-model="form.pays_residence" class="input" placeholder="France, Sénégal…" />
          </div>
        </div>

        <!-- 2 — Professionnel & Fiscal -->
        <div v-show="currentStep === 2" class="space-y-5">
          <h2 class="section-title">Situation Professionnelle & Fiscale</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="label">Profession actuelle</label><input v-model="form.profession" class="input" /></div>
            <div><label class="label">Employeur / Entreprise</label><input v-model="form.employeur" class="input" /></div>
            <div><label class="label">Secteur d'activité</label><input v-model="form.secteur_activite" class="input" /></div>
            <div><label class="label">N° Compte Contribuable / Identité Fiscale</label><input v-model="form.numero_contribuable" class="input" /></div>
            <div class="md:col-span-2">
              <label class="label">Professions exercées ces 5 dernières années</label>
              <textarea v-model="form.profession_5_ans" rows="3" class="input resize-none" placeholder="Listez les emplois successifs, entreprises et durées…" />
            </div>
          </div>
          <!-- Mandataire -->
          <div class="border border-gray-200 rounded-lg p-4 space-y-3">
            <label class="flex items-center gap-2 cursor-pointer">
              <input v-model="hasMandataire" type="checkbox" class="w-4 h-4 rounded" />
              <span class="text-sm font-medium text-gray-700">Mandataire / Représentant</span>
            </label>
            <div v-if="hasMandataire" class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div><label class="label">Prénom & Nom</label><input v-model="form.mandataire.prenom_nom" class="input" /></div>
              <div><label class="label">Fonction</label><input v-model="form.mandataire.fonction" class="input" placeholder="Avocat, tuteur…" /></div>
              <div>
                <label class="label">Type de pièce</label>
                <select v-model="form.mandataire.type_piece" class="input">
                  <option value="">—</option><option value="CNI">CNI</option><option value="Passeport">Passeport</option>
                </select>
              </div>
              <div><label class="label">N° de pièce</label><input v-model="form.mandataire.numero_piece" class="input" /></div>
              <div><label class="label">Date de naissance</label><input v-model="form.mandataire.date_naissance" type="date" class="input" /></div>
              <div><label class="label">Nationalité</label><input v-model="form.mandataire.nationalite" class="input" /></div>
              <div><label class="label">Pays de résidence</label><input v-model="form.mandataire.pays_residence" class="input" /></div>
            </div>
          </div>
          <!-- PPE -->
          <div class="border rounded-lg p-4 space-y-3" :class="form.est_ppe ? 'border-orange-300 bg-orange-50' : 'border-gray-200'">
            <label class="flex items-center gap-2 cursor-pointer">
              <input v-model="form.est_ppe" type="checkbox" class="w-4 h-4 rounded" />
              <span class="text-sm font-medium text-gray-700">Personne Politiquement Exposée (PPE)</span>
              <span class="text-xs text-orange-600 font-semibold">⚡ Trigger T1 — force ÉLEVÉ</span>
            </label>
            <div v-if="form.est_ppe">
              <label class="label">Détail PPE (fonctions, pays, durée…)</label>
              <textarea v-model="form.ppe_detail" rows="2" class="input resize-none" />
            </div>
          </div>
        </div>

        <!-- 3 — Opération & Bénéficiaires -->
        <div v-show="currentStep === 3" class="space-y-5">
          <h2 class="section-title">Description de l'Opération</h2>
          <p class="text-xs text-gray-500">Cochez toutes les opérations applicables :</p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label v-for="op in operationOptions" :key="op.key"
              class="flex items-center gap-2 p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors"
              :class="form.operations_cochees[op.key] ? 'border-[#1a2e4a] bg-[#1a2e4a]/5' : 'border-gray-200'">
              <input v-model="form.operations_cochees[op.key]" type="checkbox" class="w-4 h-4 rounded text-[#1a2e4a]" />
              <span class="text-sm text-gray-700">{{ op.label }}</span>
            </label>
          </div>
          <div><label class="label">Préciser si autre</label><input v-model="form.operations_cochees.autre_detail" class="input" /></div>
          <div>
            <label class="label">Description détaillée de l'opération</label>
            <textarea v-model="form.description_operation" rows="4" class="input resize-none" placeholder="Objet précis de l'acte, parties, montants, conditions, origine immobilière…" />
          </div>
          <!-- BE -->
          <div class="border border-gray-200 rounded-lg p-4 space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-medium text-gray-700">Bénéficiaires Effectifs</h3>
              <button type="button" @click="addBE" class="text-xs text-[#1a2e4a] border border-[#1a2e4a] px-2 py-1 rounded hover:bg-[#1a2e4a]/5">+ Ajouter</button>
            </div>
            <p v-if="beList.length === 0" class="text-xs text-gray-400">Aucun bénéficiaire ajouté.</p>
            <div v-for="(be, i) in beList" :key="i" class="grid grid-cols-1 md:grid-cols-3 gap-3 p-3 bg-gray-50 rounded-lg">
              <div><label class="label">Nom / Raison sociale <span class="req">*</span></label><input v-model="be.raison_sociale_nom" class="input" /></div>
              <div><label class="label">N° CNI / Passeport</label><input v-model="be.cni_passeport" class="input" /></div>
              <div><label class="label">% Participation</label><input v-model.number="be.pourcentage" type="number" min="0" max="100" step="0.01" class="input" /></div>
              <div><label class="label">Nationalité</label><input v-model="be.nationalite" class="input" /></div>
              <div><label class="label">Pays de résidence</label><input v-model="be.pays_residence" class="input" /></div>
              <div class="flex items-end"><button type="button" @click="beList.splice(i, 1)" class="text-xs text-red-500 hover:text-red-700 px-2 py-1">Supprimer</button></div>
            </div>
          </div>
        </div>

        <!-- 4 — Origine fonds + Signature -->
        <div v-show="currentStep === 4" class="space-y-5">
          <h2 class="section-title">Origine des Fonds & Déclaration</h2>
          <p class="text-xs text-gray-500">Je déclare que les fonds proviennent de :</p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label v-for="of in fondOptions" :key="of.key"
              class="flex items-center gap-2 p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors"
              :class="form.origine_fonds[of.key] ? 'border-[#1a2e4a] bg-[#1a2e4a]/5' : 'border-gray-200'">
              <input v-model="form.origine_fonds[of.key]" type="checkbox" class="w-4 h-4 rounded text-[#1a2e4a]" />
              <span class="text-sm text-gray-700">{{ of.label }}</span>
            </label>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="label">Autres sources</label><input v-model="form.origine_fonds.autres" class="input" /></div>
            <div><label class="label">Pays de provenance (si hors CI)</label><input v-model="form.origine_fonds.pays_provenance" class="input" /></div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="label">Ancienneté professionnelle</label>
              <select v-model="form.anciennete_pro" class="input">
                <option value="">—</option>
                <option value="moins_1_an">Moins de 1 an</option>
                <option value="1_a_10_ans">1 à 10 ans</option>
                <option value="plus_10_ans">Plus de 10 ans</option>
              </select>
            </div>
            <div><label class="label">Date de signature</label><input v-model="form.date_signature" type="date" class="input" /></div>
          </div>
          <!-- Score preview -->
          <div v-if="scoreResult" class="border rounded-lg p-4 space-y-2"
            :class="scoreResult.classification === 'ELEVE' ? 'border-red-200 bg-red-50' : scoreResult.classification === 'MOYEN' ? 'border-orange-200 bg-orange-50' : 'border-green-200 bg-green-50'">
            <div class="flex items-center gap-2 flex-wrap">
              <span :class="classBadge(scoreResult.classification)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ scoreResult.classification }}</span>
              <span class="text-sm font-medium text-gray-700">Score : {{ scoreResult.score }}/20</span>
              <span v-if="scoreResult.force_par_trigger" class="text-xs text-red-600 font-medium">⚡ Forcé — Trigger {{ scoreResult.trigger_principal }}</span>
            </div>
            <div class="flex gap-1 flex-wrap text-xs">
              <span v-for="(v, k) in scoreResult.triggers_actifs" :key="k" class="bg-red-100 text-red-700 px-2 py-0.5 rounded">{{ k }} actif</span>
            </div>
            <div class="grid grid-cols-5 gap-2 pt-1">
              <div v-for="(v, k) in scoreResult.axes" :key="k" class="text-center">
                <div class="text-xs text-gray-500">Axe {{ k }}</div>
                <div :class="v === 2 ? 'text-red-600' : v === 1 ? 'text-orange-500' : 'text-green-600'" class="font-bold text-sm">{{ v }}/2</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="flex items-center justify-between">
        <button v-if="currentStep > 0" @click="currentStep--" class="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors">← Précédent</button>
        <div v-else />
        <div class="flex gap-3">
          <button @click="save" :disabled="saving" class="px-5 py-2 border border-[#1a2e4a] text-[#1a2e4a] rounded-lg text-sm font-medium hover:bg-[#1a2e4a]/5 disabled:opacity-50 transition-colors">
            {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
          </button>
          <button v-if="currentStep < steps.length - 1" @click="currentStep++" class="px-5 py-2 bg-[#1a2e4a] text-white rounded-lg text-sm font-medium hover:bg-[#1a2e4a]/90 transition-colors">
            Suivant →
          </button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import axios from 'axios'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const dossierId = route.params.id as string

const dossierRef = ref('')
const currentStep = ref(0)
const saving = ref(false)
const saveError = ref('')
const saveOk = ref(false)
const hasMandataire = ref(false)

const steps = ['Identité', 'Coordonnées', 'Professionnel', 'Opération', 'Origine fonds']

const form = reactive({
  relation_type: 'initiale',
  nom: '', prenoms: '', nom_jeune_fille: '', nom_prenoms_pere: '', nom_prenoms_mere: '',
  date_naissance: '', lieu_naissance: '', nationalite: '', autres_nationalites: '', statut_matrimonial: '',
  type_piece: '', numero_piece: '',
  adresse_geo: '', adresse_postale: '', telephone: '', whatsapp: '', email: '',
  non_resident: false, pays_residence: '',
  profession: '', profession_5_ans: '', employeur: '', secteur_activite: '', numero_contribuable: '',
  mandataire: { prenom_nom: '', type_piece: '', numero_piece: '', date_naissance: '', nationalite: '', pays_residence: '', fonction: '' },
  est_ppe: false, ppe_detail: '',
  operations_cochees: { achat_immo: false, manipulation_fonds: false, creation_societe: false, fiducicommis: false, succession: false, donation: false, autre_detail: '' } as Record<string, any>,
  description_operation: '',
  origine_fonds: { activite: false, associes: false, vente_immeuble: false, bancaire: false, autres: '', propriete_intervenants: false, propriete_tiers: false, interet_tiers: false, territoire_ivoirien: true, pays_provenance: '' } as Record<string, any>,
  anciennete_pro: '', date_signature: '',
})

const beList = ref<Array<{ raison_sociale_nom: string; cni_passeport: string; pourcentage: number | null; nationalite: string; pays_residence: string }>>([])

interface ScoreResult { score: number; classification: string; triggers_actifs: Record<string, boolean>; force_par_trigger: boolean; trigger_principal: string | null; axes: Record<string, number> }
const scoreResult = ref<ScoreResult | null>(null)

const operationOptions = [
  { key: 'achat_immo', label: 'Achat / Vente immobilière' },
  { key: 'manipulation_fonds', label: 'Manipulation de fonds' },
  { key: 'creation_societe', label: 'Constitution de société' },
  { key: 'fiducicommis', label: 'Fiducicommis' },
  { key: 'succession', label: 'Succession / Héritage' },
  { key: 'donation', label: 'Donation' },
]

const fondOptions = [
  { key: 'activite', label: "Revenus d'activité professionnelle" },
  { key: 'associes', label: "Apports d'associés" },
  { key: 'vente_immeuble', label: "Vente d'immeuble" },
  { key: 'bancaire', label: 'Crédit bancaire' },
  { key: 'propriete_intervenants', label: 'Propriété des intervenants' },
  { key: 'propriete_tiers', label: "Propriété d'un tiers" },
  { key: 'interet_tiers', label: "Agit pour le compte d'un tiers" },
  { key: 'territoire_ivoirien', label: 'Fonds sur le territoire ivoirien' },
]

function headers() { return auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {} }
function classBadge(c: string) {
  return c === 'ELEVE' ? 'bg-red-100 text-red-700' : c === 'MOYEN' ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'
}
function addBE() {
  beList.value.push({ raison_sociale_nom: '', cni_passeport: '', pourcentage: null, nationalite: '', pays_residence: '' })
}

function buildPayload() {
  const d: any = { ...form }
  if (!hasMandataire.value) d.mandataire = null
  else d.mandataire = { ...form.mandataire }
  d.operations_cochees = { ...form.operations_cochees }
  d.origine_fonds = { ...form.origine_fonds }
  if (!d.date_naissance) d.date_naissance = null
  if (!d.date_signature) d.date_signature = null
  if (!d.anciennete_pro) d.anciennete_pro = null
  if (!d.type_piece) d.type_piece = null
  if (!d.nom_jeune_fille) d.nom_jeune_fille = null
  return d
}

async function save() {
  saving.value = true; saveError.value = ''; saveOk.value = false
  try {
    await axios.put(`/api/dossiers/${dossierId}/kyc/pp`, buildPayload(), { headers: headers() })
    for (const be of beList.value) {
      if (be.raison_sociale_nom) {
        await axios.post(`/api/dossiers/${dossierId}/kyc/pp/be`, be, { headers: headers() })
      }
    }
    beList.value = []
    const { data: s } = await axios.get(`/api/dossiers/${dossierId}/kyc/pp/score`, { headers: headers() })
    scoreResult.value = s
    saveOk.value = true
    setTimeout(() => { saveOk.value = false }, 3000)
  } catch (e: any) {
    saveError.value = e.response?.data?.detail ?? "Erreur lors de l'enregistrement."
  } finally { saving.value = false }
}

async function loadExisting() {
  try {
    const { data: d } = await axios.get(`/api/dossiers/${dossierId}`, { headers: headers() })
    dossierRef.value = d.reference
    if (d.classification) {
      scoreResult.value = { score: d.score_base, classification: d.classification, triggers_actifs: {}, force_par_trigger: d.force_par_trigger, trigger_principal: d.trigger_actif, axes: {} }
    }
  } catch {}
  try {
    const { data: kyc } = await axios.get(`/api/dossiers/${dossierId}/kyc/pp`, { headers: headers() })
    const fields = ['relation_type','nom','prenoms','nom_jeune_fille','nom_prenoms_pere','nom_prenoms_mere',
      'date_naissance','lieu_naissance','nationalite','autres_nationalites','statut_matrimonial',
      'type_piece','numero_piece','adresse_geo','adresse_postale','telephone','whatsapp','email',
      'non_resident','pays_residence','profession','profession_5_ans','employeur','secteur_activite',
      'numero_contribuable','est_ppe','ppe_detail','description_operation','anciennete_pro','date_signature']
    for (const f of fields) if (kyc[f] !== undefined && kyc[f] !== null) (form as any)[f] = kyc[f]
    if (kyc.mandataire) { hasMandataire.value = true; Object.assign(form.mandataire, kyc.mandataire) }
    if (kyc.operations_cochees) Object.assign(form.operations_cochees, kyc.operations_cochees)
    if (kyc.origine_fonds) Object.assign(form.origine_fonds, kyc.origine_fonds)
    if (kyc.beneficiaires_effectifs?.length) {
      beList.value = kyc.beneficiaires_effectifs.map((b: any) => ({
        raison_sociale_nom: b.raison_sociale_nom, cni_passeport: b.cni_passeport ?? '',
        pourcentage: b.pourcentage, nationalite: b.nationalite ?? '', pays_residence: b.pays_residence ?? ''
      }))
    }
  } catch {}
}

onMounted(loadExisting)
</script>

<style scoped>
.section-title { @apply text-sm font-semibold text-gray-700 uppercase tracking-wide border-b border-gray-100 pb-2; }
.label { @apply block text-xs font-medium text-gray-700 mb-1; }
.req { @apply text-red-500; }
.input { @apply w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]; }
</style>
