<template>
  <div class="p-6 space-y-5 max-w-4xl mx-auto">
      <!-- Bannière Art. 63 -->
      <div class="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 flex items-start gap-3">
        <span class="text-amber-500 mt-0.5">⚠️</span>
        <div class="text-xs text-amber-800">
          <strong>Confidentialité absolue — Art. 63.</strong> Cette déclaration ne doit en aucun cas être communiquée au client ni à des tiers. Statut confidentiel — visible uniquement RC, Notaire, Admin.
        </div>
      </div>

      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2">
            <RouterLink to="/dos" class="text-sm text-gray-400 hover:text-[#1a2e4a]">← DOS</RouterLink>
            <span class="text-gray-300">/</span>
            <span class="text-sm font-medium text-gray-700 font-mono">{{ dos?.reference_interne }}</span>
            <span :class="statutBadge(dos?.statut)" class="px-2 py-0.5 rounded-full text-xs font-medium ml-1">{{ statutLabel(dos?.statut) }}</span>
          </div>
          <h1 class="text-xl font-semibold text-gray-900 mt-1">Déclaration de Soupçon</h1>
        </div>
        <div class="flex gap-2">
          <button v-if="dos?.statut !== 'soumis' && dos?.statut !== 'accuse_recu'" @click="saveAll" :disabled="saving" class="px-4 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50">
            {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
          </button>
          <button v-if="dos?.statut === 'brouillon' || dos?.statut === 'en_cours'" @click="showSoumettre = true" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm rounded-lg hover:bg-[#1a2e4a]/90">
            Soumettre CENTIF
          </button>
          <button v-if="dos?.statut === 'soumis'" @click="showAccuse = true" class="px-4 py-2 bg-green-700 text-white text-sm rounded-lg hover:bg-green-800">
            Accusé de réception
          </button>
        </div>
      </div>

      <div v-if="loadError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">{{ loadError }}</div>

      <div v-if="loading" class="flex items-center justify-center py-20 text-gray-400 text-sm">Chargement…</div>

      <template v-else-if="dos">
        <!-- Navigation sections -->
        <div class="flex gap-1 flex-wrap bg-gray-100 p-1 rounded-xl">
          <button v-for="(s, i) in SECTIONS" :key="i" @click="activeSection = i"
            :class="activeSection === i ? 'bg-white text-[#1a2e4a] shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700'"
            class="flex-1 min-w-[120px] px-3 py-2 rounded-lg text-xs transition-all text-center">
            <span class="text-xs">{{ i + 1 }}.</span> {{ s }}
          </button>
        </div>

        <!-- Section 1: Organisme déclarant -->
        <div v-show="activeSection === 0" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 class="text-sm font-semibold text-[#1a2e4a]">Section 1 — Organisme déclarant</h2>
          <div class="grid grid-cols-2 gap-4">
            <div><label class="label">Dénomination</label><input v-model="form.organisme_denomination" class="input" /></div>
            <div><label class="label">Forme juridique</label><input v-model="form.organisme_forme_juridique" class="input" /></div>
            <div><label class="label">RCCM / N° Agrément</label><input v-model="form.organisme_rccm" class="input" /></div>
            <div><label class="label">Adresse siège</label><input v-model="form.organisme_adresse" class="input" /></div>
            <div><label class="label">Téléphone</label><input v-model="form.organisme_telephone" class="input" type="tel" /></div>
            <div><label class="label">Email</label><input v-model="form.organisme_email" class="input" type="email" /></div>
            <div class="col-span-2"><label class="label">Responsable désigné</label><input v-model="form.organisme_responsable" class="input" /></div>
          </div>
        </div>

        <!-- Section 2: Identification du client -->
        <div v-show="activeSection === 1" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 class="text-sm font-semibold text-[#1a2e4a]">Section 2 — Identification du client</h2>
          <div class="grid grid-cols-2 gap-4">
            <div class="col-span-2"><label class="label">Nom complet / Dénomination</label><input v-model="form.client_nom" class="input" /></div>
            <div><label class="label">Date de naissance / Création</label><input v-model="form.client_date_naissance" class="input" type="date" /></div>
            <div><label class="label">Nationalité / Pays d'incorporation</label><input v-model="form.client_nationalite" class="input" /></div>
            <div class="col-span-2"><label class="label">Adresse</label><input v-model="form.client_adresse" class="input" /></div>
            <div><label class="label">Pièce d'identité — type</label><input v-model="form.client_piece_type" class="input" /></div>
            <div><label class="label">Numéro pièce</label><input v-model="form.client_piece_numero" class="input" /></div>
            <div><label class="label">Profession / Activité</label><input v-model="form.client_profession" class="input" /></div>
            <div><label class="label">N° compte contribuable</label><input v-model="form.client_compte_contribuable" class="input" /></div>
            <div class="col-span-2"><label class="label">Nature de la relation d'affaires</label><textarea v-model="form.client_nature_relation" class="input h-20 resize-none" /></div>
          </div>
        </div>

        <!-- Section 3: Type de soupçon -->
        <div v-show="activeSection === 2" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 class="text-sm font-semibold text-[#1a2e4a]">Section 3 — Type de soupçon</h2>
          <p class="text-xs text-gray-500">Cochez le ou les types applicables (au moins un obligatoire).</p>
          <div class="space-y-3">
            <label class="flex items-start gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
              <input type="checkbox" v-model="form.type_soupcon_bc" class="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#1a2e4a]" />
              <div>
                <p class="text-sm font-medium text-gray-900">Blanchiment de capitaux (BC)</p>
                <p class="text-xs text-gray-500 mt-0.5">Opérations susceptibles de provenir d'activités illicites ou de dissimuler leur origine.</p>
              </div>
            </label>
            <label class="flex items-start gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
              <input type="checkbox" v-model="form.type_soupcon_ft" class="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#1a2e4a]" />
              <div>
                <p class="text-sm font-medium text-gray-900">Financement du terrorisme (FT)</p>
                <p class="text-xs text-gray-500 mt-0.5">Opérations pouvant financer des actes ou organisations terroristes.</p>
              </div>
            </label>
            <label class="flex items-start gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
              <input type="checkbox" v-model="form.type_soupcon_prolif" class="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#1a2e4a]" />
              <div>
                <p class="text-sm font-medium text-gray-900">Financement de la prolifération (FP)</p>
                <p class="text-xs text-gray-500 mt-0.5">Opérations liées à la prolifération d'armes de destruction massive.</p>
              </div>
            </label>
          </div>
        </div>

        <!-- Section 4: Motifs CENTIF -->
        <div v-show="activeSection === 3" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 class="text-sm font-semibold text-[#1a2e4a]">Section 4 — Motifs CENTIF</h2>
          <p class="text-xs text-gray-500">Cochez les indicateurs déclencheurs du soupçon.</p>
          <div class="grid grid-cols-1 gap-2">
            <label v-for="m in MOTIFS" :key="m.key" class="flex items-start gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
              <input type="checkbox" v-model="form.motifs_centif[m.key]" class="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#1a2e4a]" />
              <span class="text-sm text-gray-700">{{ m.label }}</span>
            </label>
          </div>
          <div>
            <label class="label">Autre motif (préciser)</label>
            <textarea v-model="form.motifs_centif.autre" class="input h-20 resize-none" placeholder="Si autre, précisez…" />
          </div>
        </div>

        <!-- Section 5: Statut des opérations -->
        <div v-show="activeSection === 4" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 class="text-sm font-semibold text-[#1a2e4a]">Section 5 — Statut des opérations</h2>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">Statut de l'opération</label>
              <select v-model="form.statut_operations.statut" class="input">
                <option value="">Sélectionner…</option>
                <option value="en_cours">En cours</option>
                <option value="realisee">Réalisée</option>
                <option value="tentee">Tentée (refusée ou suspendue)</option>
              </select>
            </div>
            <div>
              <label class="label">Date de l'opération</label>
              <input v-model="form.statut_operations.date_operation" class="input" type="date" />
            </div>
            <div class="col-span-2">
              <label class="label">Montant approximatif (FCFA)</label>
              <input v-model="form.statut_operations.montant_fcfa" class="input" type="number" step="1000" />
            </div>
            <div class="col-span-2">
              <label class="label">Description de l'opération</label>
              <textarea v-model="form.statut_operations.description" class="input h-28 resize-none" placeholder="Décrivez précisément la nature et les circonstances de l'opération suspecte…" />
            </div>
          </div>
        </div>

        <!-- Section 6: Détail des transactions -->
        <div v-show="activeSection === 5" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 class="text-sm font-semibold text-[#1a2e4a]">Section 6 — Détail des transactions</h2>
          <div v-for="(t, i) in form.transactions" :key="i" class="border border-gray-200 rounded-lg p-4 space-y-3 relative">
            <button @click="form.transactions.splice(i, 1)" class="absolute top-3 right-3 text-red-400 hover:text-red-600 text-xs">Supprimer</button>
            <div class="grid grid-cols-3 gap-3">
              <div><label class="label">Date</label><input v-model="t.date" class="input" type="date" /></div>
              <div><label class="label">Montant (FCFA)</label><input v-model="t.montant" class="input" type="number" /></div>
              <div>
                <label class="label">Mode de paiement</label>
                <select v-model="t.mode_paiement" class="input">
                  <option value="especes">Espèces</option>
                  <option value="virement">Virement bancaire</option>
                  <option value="cheque">Chèque</option>
                  <option value="mobile_money">Mobile Money</option>
                  <option value="autre">Autre</option>
                </select>
              </div>
              <div class="col-span-3"><label class="label">Description</label><input v-model="t.description" class="input" placeholder="Objet de la transaction…" /></div>
            </div>
          </div>
          <button @click="addTransaction" class="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-[#1a2e4a] hover:text-[#1a2e4a] transition-colors">
            + Ajouter une transaction
          </button>
        </div>

        <!-- Section 7: Indices de blanchiment -->
        <div v-show="activeSection === 6" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 class="text-sm font-semibold text-[#1a2e4a]">Section 7 — Indices de blanchiment</h2>
          <p class="text-xs text-gray-500">Décrivez les indices, faits et comportements qui fondent votre soupçon, au-delà des indicateurs cochés.</p>
          <div class="space-y-4">
            <div>
              <label class="label">Comportement du client</label>
              <textarea v-model="form.indices_blanchiment.comportement_client" class="input h-24 resize-none" placeholder="Comportement inhabituel, hésitations, refus de fournir des informations…" />
            </div>
            <div>
              <label class="label">Incohérences documentaires</label>
              <textarea v-model="form.indices_blanchiment.incoherences_documentaires" class="input h-24 resize-none" placeholder="Documents présentant des anomalies, incohérences entre déclarations et preuves…" />
            </div>
            <div>
              <label class="label">Facteurs contextuels</label>
              <textarea v-model="form.indices_blanchiment.facteurs_contextuels" class="input h-24 resize-none" placeholder="Localisation des fonds, secteur d'activité atypique, réseaux de tiers suspects…" />
            </div>
            <div>
              <label class="label">Analyse globale du soupçon</label>
              <textarea v-model="form.indices_blanchiment.analyse_globale" class="input h-32 resize-none" placeholder="Synthèse expliquant pourquoi les éléments ci-dessus constituent un soupçon de blanchiment…" />
            </div>
          </div>
        </div>

        <!-- Section 8: Relations d'affaires -->
        <div v-show="activeSection === 7" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 class="text-sm font-semibold text-[#1a2e4a]">Section 8 — Relations d'affaires</h2>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">Durée de la relation</label>
              <input v-model="form.relations_affaires.duree_relation" class="input" placeholder="ex: 2 ans" />
            </div>
            <div>
              <label class="label">Ancienneté client (années)</label>
              <input v-model="form.relations_affaires.anciennete_annees" class="input" type="number" />
            </div>
            <div class="col-span-2">
              <label class="label">Historique des opérations</label>
              <textarea v-model="form.relations_affaires.historique_operations" class="input h-24 resize-none" placeholder="Résumé des opérations antérieures avec ce client…" />
            </div>
            <div class="col-span-2">
              <label class="label">Mesures préalables prises</label>
              <textarea v-model="form.relations_affaires.mesures_prises" class="input h-24 resize-none" placeholder="Vigilances renforcées, demandes de justificatifs, entretiens avec le client…" />
            </div>
            <div class="col-span-2 flex items-start gap-3 p-3 border border-gray-200 rounded-lg">
              <input type="checkbox" v-model="form.relations_affaires.relation_en_cours" class="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#1a2e4a]" id="rel_en_cours" />
              <label for="rel_en_cours" class="text-sm text-gray-700 cursor-pointer">La relation d'affaires est encore en cours</label>
            </div>
          </div>
        </div>

        <!-- Section 9: Supports utilisés -->
        <div v-show="activeSection === 8" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 class="text-sm font-semibold text-[#1a2e4a]">Section 9 — Supports utilisés</h2>
          <p class="text-xs text-gray-500">Indiquez les instruments financiers ou modes de transfert impliqués dans les opérations suspectes.</p>
          <div class="grid grid-cols-2 gap-2">
            <label v-for="s in SUPPORTS" :key="s.key" class="flex items-center gap-2 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
              <input type="checkbox" v-model="form.supports[s.key]" class="h-4 w-4 rounded border-gray-300 text-[#1a2e4a]" />
              <span class="text-sm text-gray-700">{{ s.label }}</span>
            </label>
          </div>
          <div>
            <label class="label">Autre support (préciser)</label>
            <input v-model="form.supports.autre_detail" class="input" />
          </div>
        </div>

        <!-- Section 10: Autres informations + Addendums -->
        <div v-show="activeSection === 9" class="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
          <div class="space-y-4">
            <h2 class="text-sm font-semibold text-[#1a2e4a]">Section 10 — Autres informations</h2>
            <div>
              <label class="label">Informations complémentaires</label>
              <textarea v-model="form.autres_informations" class="input h-32 resize-none" placeholder="Tout élément supplémentaire jugé pertinent pour la CENTIF…" />
            </div>
          </div>

          <!-- Addendums (après soumission) -->
          <div class="border-t border-gray-200 pt-6 space-y-4">
            <h3 class="text-sm font-semibold text-[#1a2e4a]">Addendums</h3>
            <p class="text-xs text-gray-500">Les addendums permettent d'ajouter des informations complémentaires même après soumission.</p>
            <div v-for="a in dos.addendums" :key="a.id" class="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-medium text-gray-600">Addendum {{ a.id.substring(0, 8) }}</span>
                <span class="text-xs text-gray-400">{{ formatDate(a.created_at) }}</span>
              </div>
              <p class="text-sm text-gray-700">{{ a.contenu }}</p>
            </div>
            <div class="space-y-2">
              <textarea v-model="newAddendum" class="input h-20 resize-none" placeholder="Rédigez un addendum à la déclaration…" />
              <button @click="submitAddendum" :disabled="!newAddendum.trim() || addingAddendum" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50">
                {{ addingAddendum ? 'Envoi…' : 'Ajouter un addendum' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Error / success -->
        <div v-if="saveError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">{{ saveError }}</div>
        <div v-if="saveOk" class="bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3 rounded-lg">Enregistré avec succès.</div>

        <!-- Navigation bas -->
        <div class="flex justify-between">
          <button v-if="activeSection > 0" @click="activeSection--" class="px-4 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50">← Précédent</button>
          <div v-else></div>
          <button v-if="activeSection < SECTIONS.length - 1" @click="activeSection++" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm rounded-lg hover:bg-[#1a2e4a]/90">Suivant →</button>
        </div>
      </template>
    </div>

    <!-- Soumettre modal -->
    <div v-if="showSoumettre" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 class="font-semibold text-gray-900">Soumettre à la CENTIF</h2>
          <button @click="showSoumettre = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <div class="p-5 space-y-4">
          <div class="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <p class="text-xs text-amber-800">Après soumission, la DOS ne peut plus être modifiée. Seuls des addendums peuvent y être ajoutés.</p>
            <p class="text-xs text-amber-800 mt-1 font-semibold">⏱ Délai légal : 24h après détection (Art. 2 §58).</p>
          </div>
          <div v-if="!form.type_soupcon_bc && !form.type_soupcon_ft && !form.type_soupcon_prolif" class="bg-red-50 border border-red-200 rounded-lg p-3">
            <p class="text-xs text-red-700">⚠️ Au moins un type de soupçon doit être sélectionné (Section 3).</p>
          </div>
          <div v-if="soumettreError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ soumettreError }}</div>
          <div class="flex justify-end gap-3">
            <button @click="showSoumettre = false" class="px-4 py-2 text-sm text-gray-600">Annuler</button>
            <button @click="submitSoumettre" :disabled="soumettant || (!form.type_soupcon_bc && !form.type_soupcon_ft && !form.type_soupcon_prolif)" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm rounded-lg disabled:opacity-50">
              {{ soumettant ? 'Envoi…' : 'Confirmer la soumission' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Accusé de réception modal -->
    <div v-if="showAccuse" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 class="font-semibold text-gray-900">Enregistrer l'accusé de réception</h2>
          <button @click="showAccuse = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <div class="p-5 space-y-4">
          <div>
            <label class="label">Référence CENTIF</label>
            <input v-model="accuseRef" class="input" placeholder="Référence attribuée par la CENTIF" />
          </div>
          <div v-if="accuseError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ accuseError }}</div>
          <div class="flex justify-end gap-3">
            <button @click="showAccuse = false" class="px-4 py-2 text-sm text-gray-600">Annuler</button>
            <button @click="submitAccuse" :disabled="!accuseRef.trim() || accusant" class="px-4 py-2 bg-green-700 text-white text-sm rounded-lg disabled:opacity-50">
              {{ accusant ? 'Enregistrement…' : 'Enregistrer' }}
            </button>
          </div>
        </div>
      </div>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const dosId = route.params.id as string

interface Addendum { id: string; contenu: string; created_at: string }
interface DosData {
  id: string; reference_interne: string; dossier_id: string; statut: string
  type_soupcon_bc: boolean; type_soupcon_ft: boolean; type_soupcon_prolif: boolean
  soumis_at: string | null; addendums: Addendum[]
  [key: string]: any
}

const dos = ref<DosData | null>(null)
const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const saveError = ref('')
const saveOk = ref(false)
const activeSection = ref(0)
const showSoumettre = ref(false)
const soumettant = ref(false)
const soumettreError = ref('')
const showAccuse = ref(false)
const accusant = ref(false)
const accuseError = ref('')
const accuseRef = ref('')
const newAddendum = ref('')
const addingAddendum = ref(false)

const SECTIONS = [
  'Organisme déclarant', 'Identification client', 'Type soupçon',
  'Motifs CENTIF', 'Statut opérations', 'Transactions',
  'Indices BC', 'Relations affaires', 'Supports', 'Autres / Addendums',
]

const MOTIFS = [
  { key: 'operations_insolites', label: 'Opérations inhabituelles ou insolites sans justification économique apparente' },
  { key: 'montants_incoherents', label: 'Montants incohérents avec le profil économique du client' },
  { key: 'identite_douteuse', label: 'Doutes sur la véritable identité du client ou du bénéficiaire effectif' },
  { key: 'origine_fonds_inconnue', label: 'Origine des fonds inconnue ou douteuse' },
  { key: 'comportement_suspect', label: 'Comportement suspect du client (nervosité, réticence, incohérences)' },
  { key: 'structure_complexe', label: 'Montage juridique ou financier complexe sans justification apparente' },
  { key: 'pays_risque', label: 'Pays ou territoires à risque (GAFI, liste noire/grise)' },
  { key: 'ppe_implique', label: 'Personne politiquement exposée (PPE) impliquée' },
  { key: 'sanctions_liste', label: 'Client ou tiers figurant sur une liste de sanctions (OFAC, UE-CSDNU, GIABA-BCEAO)' },
  { key: 'beneficiaire_non_identifiable', label: 'Bénéficiaire effectif non identifiable ou structure opaque' },
  { key: 'refus_documents', label: 'Refus ou impossibilité de fournir les documents requis' },
  { key: 'paiement_especes', label: 'Paiement en espèces important ou fractionné' },
  { key: 'interposition_tiers', label: 'Interposition de tiers sans raison économique claire' },
  { key: 'changement_soudain', label: 'Changement soudain et inexpliqué de comportement ou de patrimoine' },
]

const SUPPORTS = [
  { key: 'especes', label: 'Espèces' },
  { key: 'virement_bancaire', label: 'Virement bancaire' },
  { key: 'cheque', label: 'Chèque' },
  { key: 'mobile_money', label: 'Mobile Money' },
  { key: 'cryptomonnaie', label: 'Cryptomonnaie' },
  { key: 'titres_valeurs', label: 'Titres et valeurs' },
  { key: 'immobilier', label: 'Bien immobilier' },
  { key: 'societe_ecran', label: 'Société écran / holding' },
  { key: 'fiducie', label: 'Fiducie / Trust' },
  { key: 'assurance_vie', label: 'Assurance-vie' },
]

const form = reactive({
  organisme_denomination: '', organisme_forme_juridique: '', organisme_rccm: '',
  organisme_adresse: '', organisme_telephone: '', organisme_email: '', organisme_responsable: '',
  client_nom: '', client_date_naissance: '', client_nationalite: '', client_adresse: '',
  client_piece_type: '', client_piece_numero: '', client_profession: '', client_compte_contribuable: '',
  client_nature_relation: '',
  type_soupcon_bc: false, type_soupcon_ft: false, type_soupcon_prolif: false,
  motifs_centif: {
    operations_insolites: false, montants_incoherents: false, identite_douteuse: false,
    origine_fonds_inconnue: false, comportement_suspect: false, structure_complexe: false,
    pays_risque: false, ppe_implique: false, sanctions_liste: false,
    beneficiaire_non_identifiable: false, refus_documents: false, paiement_especes: false,
    interposition_tiers: false, changement_soudain: false, autre: '',
  } as Record<string, any>,
  statut_operations: { statut: '', date_operation: '', montant_fcfa: null as number | null, description: '' },
  transactions: [] as { date: string; montant: number | null; mode_paiement: string; description: string }[],
  indices_blanchiment: { comportement_client: '', incoherences_documentaires: '', facteurs_contextuels: '', analyse_globale: '' },
  relations_affaires: { duree_relation: '', anciennete_annees: null as number | null, historique_operations: '', mesures_prises: '', relation_en_cours: false },
  supports: {
    especes: false, virement_bancaire: false, cheque: false, mobile_money: false,
    cryptomonnaie: false, titres_valeurs: false, immobilier: false, societe_ecran: false,
    fiducie: false, assurance_vie: false, autre_detail: '',
  } as Record<string, any>,
  autres_informations: '',
})

function headers() { return auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {} }
function formatDate(s: string) { return new Date(s).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' }) }
function statutLabel(s?: string) { const m: Record<string, string> = { brouillon: 'Brouillon', en_cours: 'En cours', soumis: 'Soumis CENTIF', accuse_recu: 'Accusé reçu' }; return s ? (m[s] ?? s) : '' }
function statutBadge(s?: string) { const m: Record<string, string> = { brouillon: 'bg-gray-100 text-gray-600', en_cours: 'bg-blue-100 text-blue-700', soumis: 'bg-orange-100 text-orange-700', accuse_recu: 'bg-green-100 text-green-700' }; return s ? (m[s] ?? 'bg-gray-100 text-gray-600') : 'bg-gray-100 text-gray-600' }

function addTransaction() {
  form.transactions.push({ date: '', montant: null, mode_paiement: 'especes', description: '' })
}

function fillFromDos(data: DosData) {
  const src = data as any
  // Map backend fields to form fields
  if (src.organisme_libelle) form.organisme_denomination = src.organisme_libelle
  if (src.organisme_adresse) form.organisme_adresse = src.organisme_adresse
  if (src.organisme_telephone) form.organisme_telephone = src.organisme_telephone
  if (src.organisme_email) form.organisme_email = src.organisme_email
  // Client identification is stored as a JSON dict in backend
  const id = src.identification || {}
  if (id.nom) form.client_nom = id.nom
  if (id.date_naissance) form.client_date_naissance = id.date_naissance
  if (id.nationalite) form.client_nationalite = id.nationalite
  if (id.adresse) form.client_adresse = id.adresse
  if (id.piece_type) form.client_piece_type = id.piece_type
  if (id.piece_numero) form.client_piece_numero = id.piece_numero
  if (id.profession) form.client_profession = id.profession
  if (id.compte_contribuable) form.client_compte_contribuable = id.compte_contribuable
  if (id.nature_relation) form.client_nature_relation = id.nature_relation
  // Direct fields
  form.type_soupcon_bc = src.type_soupcon_bc ?? false
  form.type_soupcon_ft = src.type_soupcon_ft ?? false
  form.type_soupcon_prolif = src.type_soupcon_prolif ?? false
  if (src.autres_informations) form.autres_informations = src.autres_informations
  // Nested JSON schemas
  if (src.motifs) Object.assign(form.motifs_centif, src.motifs)
  if (src.statut_operations) Object.assign(form.statut_operations, src.statut_operations)
  if (src.detail_transactions) form.transactions = src.detail_transactions
  if (src.indices_blanchiment) form.indices_blanchiment.analyse_globale = src.indices_blanchiment
  if (src.relations_affaires) Object.assign(form.relations_affaires, src.relations_affaires)
  if (src.supports) Object.assign(form.supports, src.supports)
}

async function load() {
  loading.value = true; loadError.value = ''
  try {
    const { data } = await axios.get(`/api/dos/${dosId}`, { headers: headers() })
    dos.value = data
    fillFromDos(data)
  } catch (e: any) { loadError.value = e.response?.data?.detail ?? 'Erreur de chargement.' }
  finally { loading.value = false }
}

function buildPayload() {
  return {
    organisme_libelle: form.organisme_denomination,
    organisme_adresse: form.organisme_adresse,
    organisme_telephone: form.organisme_telephone,
    organisme_email: form.organisme_email,
    type_soupcon_bc: form.type_soupcon_bc,
    type_soupcon_ft: form.type_soupcon_ft,
    type_soupcon_prolif: form.type_soupcon_prolif,
    motifs: { ...form.motifs_centif },
    statut_operations: { ...form.statut_operations },
    detail_transactions: form.transactions,
    indices_blanchiment: form.indices_blanchiment.analyse_globale,
    identification: {
      nom: form.client_nom,
      date_naissance: form.client_date_naissance,
      nationalite: form.client_nationalite,
      adresse: form.client_adresse,
      piece_type: form.client_piece_type,
      piece_numero: form.client_piece_numero,
      profession: form.client_profession,
      compte_contribuable: form.client_compte_contribuable,
      nature_relation: form.client_nature_relation,
      organisme_forme_juridique: form.organisme_forme_juridique,
      organisme_rccm: form.organisme_rccm,
      organisme_responsable: form.organisme_responsable,
    },
    relations_affaires: { ...form.relations_affaires },
    supports: { ...form.supports },
    autres_informations: form.autres_informations,
  }
}

async function saveAll() {
  saving.value = true; saveError.value = ''; saveOk.value = false
  try {
    const { data } = await axios.put(`/api/dos/${dosId}`, buildPayload(), { headers: headers() })
    dos.value = data
    saveOk.value = true
    setTimeout(() => { saveOk.value = false }, 3000)
  } catch (e: any) { saveError.value = e.response?.data?.detail ?? 'Erreur lors de l\'enregistrement.' }
  finally { saving.value = false }
}

async function submitSoumettre() {
  soumettant.value = true; soumettreError.value = ''
  try {
    await saveAll()
    const { data } = await axios.post(`/api/dos/${dosId}/soumettre`, {}, { headers: headers() })
    dos.value = data
    showSoumettre.value = false
  } catch (e: any) { soumettreError.value = e.response?.data?.detail ?? 'Erreur lors de la soumission.' }
  finally { soumettant.value = false }
}

async function submitAccuse() {
  accusant.value = true; accuseError.value = ''
  try {
    const { data } = await axios.patch(`/api/dos/${dosId}/accuse-recu`, null, { params: { reference_centif: accuseRef.value }, headers: headers() })
    dos.value = data
    showAccuse.value = false
  } catch (e: any) { accuseError.value = e.response?.data?.detail ?? 'Erreur.' }
  finally { accusant.value = false }
}

async function submitAddendum() {
  if (!newAddendum.value.trim()) return
  addingAddendum.value = true
  try {
    const { data } = await axios.post(`/api/dos/${dosId}/addendums`, { contenu: newAddendum.value }, { headers: headers() })
    if (dos.value) dos.value.addendums.push(data)
    newAddendum.value = ''
  } catch (e: any) { saveError.value = e.response?.data?.detail ?? 'Erreur addendum.' }
  finally { addingAddendum.value = false }
}

onMounted(load)
</script>

<style scoped>
@reference "tailwindcss";
.label { @apply block text-xs font-medium text-gray-700 mb-1; }
.input { @apply w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]; }
</style>
