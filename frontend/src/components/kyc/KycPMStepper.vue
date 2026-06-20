<template>
  <div class="kyc-pm-stepper">
    <!-- Step indicator -->
    <div class="step-bar">
      <div
        v-for="(step, idx) in STEPS"
        :key="idx"
        class="step-item"
        :class="{
          'step-item--done':    idx < currentStep,
          'step-item--active':  idx === currentStep,
        }"
      >
        <div class="step-dot">
          <svg v-if="idx < currentStep" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          <span v-else>{{ idx + 1 }}</span>
        </div>
        <span class="step-label">{{ step.label }}</span>
        <div v-if="idx < STEPS.length - 1" class="step-connector" />
      </div>
    </div>

    <!-- Save status -->
    <div class="save-status" :class="`save-status--${saveStatus}`">
      <template v-if="saveStatus === 'saving'">
        <svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
        Sauvegarde…
      </template>
      <template v-else-if="saveStatus === 'saved'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
        Sauvegardé
      </template>
      <template v-else-if="saveStatus === 'error'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        Erreur de sauvegarde
      </template>
    </div>

    <!-- Step 1 — Identification -->
    <div v-if="currentStep === 0" class="step-panel card">
      <h3 class="step-title">Identification de la personne morale</h3>
      <div class="form-grid">
        <div class="form-group form-group--full">
          <label class="form-label">Raison sociale <span class="req">*</span></label>
          <input v-model="form.denomination_sociale" type="text" class="form-input" placeholder="Nom complet de la société" />
          <p v-if="errors.denomination_sociale" class="form-error">{{ errors.denomination_sociale }}</p>
        </div>
        <div class="form-group">
          <label class="form-label">Nom commercial</label>
          <input v-model="form.nom_commercial" type="text" class="form-input" placeholder="Enseigne / nom commercial" />
        </div>
        <div class="form-group">
          <label class="form-label">Forme juridique <span class="req">*</span></label>
          <select v-model="form.forme_juridique" class="form-select">
            <option value="">— Sélectionner —</option>
            <option v-for="f in FORMES_JURIDIQUES" :key="f" :value="f">{{ f }}</option>
          </select>
          <p v-if="errors.forme_juridique" class="form-error">{{ errors.forme_juridique }}</p>
        </div>
        <CountrySelect v-model="form.pays_constitution" label="Pays de constitution *" />
        <p v-if="errors.pays_constitution" class="form-error" style="grid-column:1/-1">{{ errors.pays_constitution }}</p>
        <div class="form-group">
          <label class="form-label">RCCM</label>
          <input v-model="form.numero_rccm" type="text" class="form-input" placeholder="CI-ABJ-2020-B-12345" />
        </div>
        <div class="form-group">
          <label class="form-label">Date d'émission RCCM</label>
          <input v-model="form.date_emission_rccm" type="date" class="form-input" />
          <span class="field-hint">Validité 90 jours (M7) — alerte au-delà</span>
        </div>
        <div class="form-group">
          <label class="form-label">NIF</label>
          <input v-model="form.numero_contribuable" type="text" class="form-input" placeholder="Numéro d'identification fiscale" />
        </div>
      </div>
    </div>

    <!-- Step 2 — Siège & activité -->
    <div v-else-if="currentStep === 1" class="step-panel card">
      <h3 class="step-title">Siège social & activité</h3>
      <div class="form-grid">
        <div class="form-group form-group--full">
          <label class="form-label">Adresse du siège social <span class="req">*</span></label>
          <textarea v-model="form.adresse" class="form-textarea" rows="2" placeholder="Adresse complète" />
          <p v-if="errors.adresse" class="form-error">{{ errors.adresse }}</p>
        </div>
        <div class="form-group">
          <label class="form-label">Secteur d'activité <span class="req">*</span></label>
          <select v-model="form.libelle_activite" class="form-select">
            <option value="">— Sélectionner —</option>
            <option v-for="s in SECTEURS" :key="s" :value="s">{{ s }}</option>
          </select>
          <p v-if="errors.libelle_activite" class="form-error">{{ errors.libelle_activite }}</p>
        </div>
        <div class="form-group">
          <label class="form-label">Téléphone</label>
          <input v-model="form.telephone" type="text" class="form-input" placeholder="+225…" />
        </div>
        <div class="form-group">
          <label class="form-label">E-mail</label>
          <input v-model="form.email" type="email" class="form-input" placeholder="contact@societe.ci" />
        </div>
        <div class="form-group">
          <label class="form-label">Chiffre d'affaires annuel (FCFA)</label>
          <input v-model.number="form.ca_annuel" type="number" min="0" class="form-input" placeholder="0" />
        </div>
        <div class="form-group">
          <label class="form-label">Effectif</label>
          <input v-model.number="form.effectif" type="number" min="0" class="form-input" placeholder="Nombre d'employés" />
        </div>
        <div class="form-group">
          <label class="form-label">Pays d'opérations</label>
          <input v-model="form.pays_operations" type="text" class="form-input" placeholder="Pays où la société opère" />
        </div>
        <div class="form-group">
          <label class="form-label">Volume des transactions</label>
          <input v-model="form.volume_transactions" type="text" class="form-input" placeholder="Ex : 50M FCFA/an" />
        </div>
        <div class="form-group form-group--full">
          <label class="form-label">Objet social / Description de l'activité</label>
          <textarea v-model="form.objet_social" class="form-textarea" rows="3" placeholder="Objet social et activité principale de la société" />
        </div>
      </div>
    </div>

    <!-- Step 3 — Représentant légal & dirigeants -->
    <div v-else-if="currentStep === 2" class="step-panel card">
      <h3 class="step-title">Représentant légal & dirigeants</h3>
      <p class="step-section-label">Représentant légal habilité</p>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Nom <span class="req">*</span></label>
          <input v-model="representant.nom" type="text" class="form-input" />
          <p v-if="errors.representant_nom" class="form-error">{{ errors.representant_nom }}</p>
        </div>
        <div class="form-group">
          <label class="form-label">Prénoms <span class="req">*</span></label>
          <input v-model="representant.prenoms" type="text" class="form-input" />
          <p v-if="errors.representant_prenoms" class="form-error">{{ errors.representant_prenoms }}</p>
        </div>
        <div class="form-group">
          <label class="form-label">Fonction <span class="req">*</span></label>
          <input v-model="representant.fonction" type="text" class="form-input" placeholder="DG, PDG, Gérant…" />
          <p v-if="errors.representant_fonction" class="form-error">{{ errors.representant_fonction }}</p>
        </div>
        <CountrySelect v-model="representant.nationalite" label="Nationalité" />
        <div class="form-group">
          <label class="form-label">Type de pièce</label>
          <select v-model="representant.type_piece" class="form-select">
            <option value="">— Sélectionner —</option>
            <option v-for="p in TYPES_PIECE" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Numéro de pièce</label>
          <input v-model="representant.numero_piece" type="text" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Expiration pièce</label>
          <input v-model="representant.date_expiration_piece" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Date de naissance</label>
          <input v-model="representant.date_naissance" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Lieu d'habitation</label>
          <input v-model="representant.lieu_habitation" type="text" class="form-input" placeholder="Ville, Pays" />
        </div>
        <div class="form-group form-group--full">
          <label class="checkbox-row">
            <input v-model="form.representant_statut_ppe" type="checkbox" class="checkbox" />
            <span class="form-label" style="margin:0">Le représentant légal est une Personne Politiquement Exposée (PPE)</span>
          </label>
        </div>
      </div>

      <!-- SFC Screening banner pour le représentant légal -->
      <div v-if="sfcState.status === 'checking'" class="sanctions-banner sanctions-banner--checking">
        Vérification SFC en cours…
      </div>
      <div v-else-if="sfcState.status === 'blocked'" class="sanctions-banner sanctions-banner--blocked">
        <span>⛔</span>
        <div>
          <p class="sanctions-banner__title">Création impossible</p>
          <p class="sanctions-banner__msg">Le représentant légal figure sur la liste des sanctions financières ciblées.</p>
        </div>
      </div>
      <div v-else-if="sfcState.status === 'warning'" class="sanctions-banner sanctions-banner--warning">
        <span>⚠️</span>
        <p class="sanctions-banner__msg">Correspondance possible sur liste {{ sfcState.liste }} — soumettez pour vérification compliance.</p>
      </div>

      <div class="divider" />
      <div class="section-header">
        <p class="step-section-label" style="margin:0">Autres dirigeants</p>
        <button class="btn-add" @click="addDirigeant">+ Ajouter</button>
      </div>
      <div v-for="(d, i) in dirigeants" :key="i" class="entity-row">
        <div class="form-grid">
          <div class="form-group"><label class="form-label">Nom</label><input v-model="d.nom" type="text" class="form-input" @blur="triggerDirigeantCheck(i)" /></div>
          <div class="form-group"><label class="form-label">Prénoms</label><input v-model="d.prenoms" type="text" class="form-input" @blur="triggerDirigeantCheck(i)" /></div>
          <div class="form-group"><label class="form-label">Fonction</label><input v-model="d.fonction" type="text" class="form-input" /></div>
          <CountrySelect v-model="d.nationalite" label="Nationalité" />
          <div class="form-group"><label class="form-label">Date de naissance</label><input v-model="d.date_naissance" type="date" class="form-input" @blur="triggerDirigeantCheck(i)" /></div>
          <div class="form-group"><label class="form-label">Lieu d'habitation</label><input v-model="d.lieu_habitation" type="text" class="form-input" placeholder="Ville, Pays" @blur="triggerDirigeantCheck(i)" /></div>
        </div>
        <div v-if="dirigeantScreenings[i]?.status === 'checking'" class="screening-badge screening-badge--checking">Criblage en cours…</div>
        <div v-else-if="dirigeantScreenings[i]?.status === 'blocked'" class="screening-badge screening-badge--blocked">⛔ Présent sur liste {{ dirigeantScreenings[i].liste }} — dossier bloqué</div>
        <div v-else-if="dirigeantScreenings[i]?.status === 'warning'" class="screening-badge screening-badge--warning">⚠️ Correspondance possible sur liste {{ dirigeantScreenings[i].liste }}</div>
        <div v-else-if="dirigeantScreenings[i]?.status === 'clear'" class="screening-badge screening-badge--clear">✓ Aucune correspondance sanctions</div>
        <button class="btn-remove" @click="removeDirigeant(i)">Supprimer</button>
      </div>
    </div>

    <!-- Step 4 — Bénéficiaires effectifs & relation -->
    <div v-else-if="currentStep === 3" class="step-panel card">
      <h3 class="step-title">Actionnaires / Associés & objet de la relation</h3>

      <div class="section-header">
        <p class="step-section-label" style="margin:0">Actionnaires / Associés (tous pourcentages)</p>
        <button class="btn-add" @click="addBE">+ Ajouter</button>
      </div>
      <div v-if="hasBE25" class="be25-notice">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;flex-shrink:0"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        Un actionnaire avec ≥ 25% de détention est détecté — veuillez compléter le module <strong>KYC-BE (Bénéficiaire effectif)</strong> après soumission.
      </div>
      <div v-for="(be, i) in beneficiaires" :key="i" class="entity-row">
        <div class="form-grid">
          <div class="form-group"><label class="form-label">Nom</label><input v-model="be.nom" type="text" class="form-input" @blur="triggerBECheck(i)" /></div>
          <div class="form-group"><label class="form-label">Prénoms</label><input v-model="be.prenoms" type="text" class="form-input" @blur="triggerBECheck(i)" /></div>
          <CountrySelect v-model="be.nationalite" label="Nationalité" />
          <div class="form-group"><label class="form-label">Date naissance</label><input v-model="be.date_naissance" type="date" class="form-input" @blur="triggerBECheck(i)" /></div>
          <div class="form-group"><label class="form-label">Lieu d'habitation</label><input v-model="be.lieu_habitation" type="text" class="form-input" placeholder="Ville, Pays" @blur="triggerBECheck(i)" /></div>
          <div class="form-group"><label class="form-label">% détention</label><input v-model.number="be.pourcentage" type="number" min="0" max="100" class="form-input" /></div>
          <div class="form-group" style="align-self:end">
            <label class="checkbox-row">
              <input v-model="be.statut_ppe" type="checkbox" class="checkbox" />
              <span class="form-label" style="margin:0">PPE</span>
            </label>
          </div>
        </div>
        <div v-if="beScreenings[i]?.status === 'checking'" class="screening-badge screening-badge--checking">Criblage en cours…</div>
        <div v-else-if="beScreenings[i]?.status === 'blocked'" class="screening-badge screening-badge--blocked">⛔ Présent sur liste {{ beScreenings[i].liste }} — dossier bloqué</div>
        <div v-else-if="beScreenings[i]?.status === 'warning'" class="screening-badge screening-badge--warning">⚠️ Correspondance possible sur liste {{ beScreenings[i].liste }}</div>
        <div v-else-if="beScreenings[i]?.status === 'clear'" class="screening-badge screening-badge--clear">✓ Aucune correspondance sanctions</div>
        <div v-if="be.statut_ppe" class="ppe-banner">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          Personne politiquement exposée — vigilance renforcée obligatoire
        </div>
        <button class="btn-remove" @click="removeBE(i)">Supprimer</button>
      </div>

      <div class="divider" />
      <div class="form-grid">
        <div class="form-group form-group--full">
          <label class="form-label">Objet de la relation / opération <span class="req">*</span></label>
          <textarea v-model="form.description_operation" class="form-textarea" rows="2" placeholder="Décrivez la nature et l'objet de la relation commerciale…" />
          <p v-if="errors.description_operation" class="form-error">{{ errors.description_operation }}</p>
        </div>
      </div>
    </div>

    <!-- Step 5 — Transaction -->
    <div v-else-if="currentStep === 4" class="step-panel card">
      <h3 class="step-title">Transaction</h3>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Montant de la transaction</label>
          <select v-model="transaction.montant_tranche" class="form-select">
            <option value="">— Choisir —</option>
            <option value="moins_15m">Montant &lt; 15M FCFA</option>
            <option value="plus_15m">Montant &gt; 15M FCFA</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Montant exact (FCFA)</label>
          <input v-model.number="transaction.montant_transaction" type="number" min="0" class="form-input" placeholder="Ex : 25000000" />
        </div>
        <div class="form-group">
          <label class="form-label">Mode de paiement</label>
          <select v-model="transaction.mode_paiement" class="form-select">
            <option value="">— Choisir —</option>
            <option value="especes">Espèces</option>
            <option value="cheque">Chèque</option>
            <option value="virement">Virement</option>
            <option value="autre">Autre</option>
          </select>
        </div>
      </div>
      <div v-if="surveillanceEspece" class="espece-banner">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        <span>Déclaration systématique de transaction en espèce à faire. Opération à surveiller.</span>
      </div>
    </div>

    <!-- Navigation -->
    <div class="step-nav">
      <button v-if="currentStep > 0" class="btn-ghost" @click="prev">← Précédent</button>
      <span v-else />
      <div class="nav-right">
        <button
          v-if="currentStep < STEPS.length - 1"
          class="btn-primary"
          :disabled="!canNext"
          @click="next"
        >
          Suivant →
        </button>
        <button
          v-else
          class="btn-primary"
          :disabled="saving"
          @click="finish"
        >
          <svg v-if="saving" class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
          {{ saving ? 'Enregistrement…' : 'Terminer le KYC' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { dossiersService, type KycPMData } from '@/services/dossiers'
import CountrySelect from '@/components/common/CountrySelect.vue'
import api from '@/services/api'

const props = defineProps<{
  dossierId: string
  initialData?: KycPMData
}>()

const emit = defineEmits<{
  saved: [data: KycPMData]
  completed: [data: KycPMData]
}>()

// ── Constants ─────────────────────────────────────────────────────────────────

const STEPS = [
  { label: 'Identification' },
  { label: 'Siège & activité' },
  { label: 'Représentant' },
  { label: 'Actionnaires' },
  { label: 'Transaction' },
]

const FORMES_JURIDIQUES = ['SA', 'SARL', 'SNC', 'SCS', 'GIE', 'Association', 'Coopérative', 'Autre']
const SECTEURS = ['Immobilier', 'BTP & Construction', 'Commerce', 'Industrie', 'Services', 'Agriculture', 'Finance', 'Autre']
const TYPES_PIECE = ["Carte Nationale d'Identité", 'Passeport', 'Titre de séjour', 'Permis de conduire']

// ── State ─────────────────────────────────────────────────────────────────────

const currentStep = ref(0)
const saveStatus  = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const saving      = ref(false)
const errors      = ref<Record<string, string>>({})

type Dirigeant = { nom: string; prenoms: string; fonction: string; nationalite: string; date_naissance: string; lieu_habitation: string }
type BE = { nom: string; prenoms: string; nationalite: string; date_naissance: string; lieu_habitation: string; pourcentage: number | null; statut_ppe: boolean }

// Étape Transaction (montant + mode de paiement) — niveau dossier
const transaction = ref<{
  montant_tranche: 'moins_15m' | 'plus_15m' | ''
  montant_transaction: number | null
  mode_paiement: 'especes' | 'cheque' | 'virement' | 'autre' | ''
}>({ montant_tranche: '', montant_transaction: null, mode_paiement: '' })
const surveillanceEspece = computed(() =>
  transaction.value.mode_paiement === 'especes' &&
  (transaction.value.montant_tranche === 'plus_15m' || Number(transaction.value.montant_transaction || 0) > 15_000_000),
)

// Aligné sur le schéma backend notaire (KycPMUpsert)
const form = ref<Partial<KycPMData>>({
  denomination_sociale: '',
  nom_commercial: '',
  forme_juridique: '',
  pays_constitution: '',
  numero_rccm: '',
  date_emission_rccm: null,
  numero_contribuable: '',
  adresse: '',
  telephone: '',
  email: '',
  libelle_activite: '',
  objet_social: '',
  ca_annuel: null,
  effectif: null,
  pays_operations: '',
  volume_transactions: '',
  representant_statut_ppe: false,
  description_operation: '',
})

// Représentant légal (sérialisé en JSON `mandataire` + `nom_representant_legal`)
const representant = ref({ nom: '', prenoms: '', fonction: '', nationalite: '', type_piece: '', numero_piece: '', date_expiration_piece: '', date_naissance: '', lieu_habitation: '' })

const dirigeants   = ref<Dirigeant[]>([])
const beneficiaires = ref<BE[]>([])

// ── SFC Screening — représentant légal ───────────────────────────────────────
const sfcState = ref<{ status: 'idle' | 'checking' | 'clear' | 'warning' | 'blocked'; liste: string | null }>({
  status: 'idle', liste: null,
})
let _sfcTimer: ReturnType<typeof setTimeout> | null = null

watch(
  () => [representant.value.nom, representant.value.prenoms],
  ([nom, prenoms]) => {
    if (_sfcTimer) clearTimeout(_sfcTimer)
    const full = `${nom ?? ''} ${prenoms ?? ''}`.trim()
    if (full.length < 4) { sfcState.value = { status: 'idle', liste: null }; return }
    sfcState.value = { status: 'checking', liste: null }
    _sfcTimer = setTimeout(async () => {
      try {
        const r = await api.post('/kyc/screening/pre-check', { nom, prenoms })
        sfcState.value = { status: r.data.level, liste: r.data.liste }
      } catch {
        sfcState.value = { status: 'idle', liste: null }
      }
    }, 600)
  },
)

// ── Screening par dirigeant ───────────────────────────────────────────────────
const dirigeantScreenings = ref<Array<{ status: 'idle'|'checking'|'blocked'|'warning'|'clear'|'no_lists'; liste: string|null }>>([])
const _dirigeantTimers: Record<number, ReturnType<typeof setTimeout>> = {}

function triggerDirigeantCheck(i: number) {
  const d = dirigeants.value[i]
  if (!d?.nom?.trim() || !d?.prenoms?.trim()) return
  clearTimeout(_dirigeantTimers[i])
  _dirigeantTimers[i] = setTimeout(async () => {
    if (!dirigeantScreenings.value[i]) return
    dirigeantScreenings.value[i].status = 'checking'
    try {
      const result = await dossiersService.checkSanctionsPreScreen(
        d.nom, d.prenoms,
        d.date_naissance || undefined,
        undefined,
      )
      dirigeantScreenings.value[i].status = result.level
      dirigeantScreenings.value[i].liste  = result.liste
    } catch {
      dirigeantScreenings.value[i].status = 'idle'
    }
  }, 500)
}

// ── Screening par actionnaire (BE) ────────────────────────────────────────────
const beScreenings = ref<Array<{ status: 'idle'|'checking'|'blocked'|'warning'|'clear'|'no_lists'; liste: string|null }>>([])
const _beTimers: Record<number, ReturnType<typeof setTimeout>> = {}

function triggerBECheck(i: number) {
  const be = beneficiaires.value[i]
  if (!be?.nom?.trim() || !be?.prenoms?.trim()) return
  clearTimeout(_beTimers[i])
  _beTimers[i] = setTimeout(async () => {
    if (!beScreenings.value[i]) return
    beScreenings.value[i].status = 'checking'
    try {
      const result = await dossiersService.checkSanctionsPreScreen(
        be.nom, be.prenoms,
        be.date_naissance || undefined,
        undefined,
      )
      beScreenings.value[i].status = result.level
      beScreenings.value[i].liste  = result.liste
    } catch {
      beScreenings.value[i].status = 'idle'
    }
  }, 500)
}

// ── Init from initialData ─────────────────────────────────────────────────────

onMounted(async () => {
  let data = props.initialData
  if (!data) {
    try {
      data = await dossiersService.getKycPM(props.dossierId)
    } catch {
      // no existing data yet
    }
  }
  if (data) {
    Object.assign(form.value, data)
    if (data.beneficiaires_effectifs) {
      beneficiaires.value = data.beneficiaires_effectifs as unknown as BE[]
      beScreenings.value = beneficiaires.value.map(() => ({ status: 'idle' as const, liste: null }))
    }
    // Représentant légal stocké en JSON `mandataire`
    const m = data.mandataire as Record<string, string> | null | undefined
    if (m) {
      representant.value.nom = m.nom ?? ''
      representant.value.prenoms = m.prenoms ?? ''
      representant.value.fonction = m.fonction ?? ''
      representant.value.nationalite = m.nationalite ?? ''
      representant.value.type_piece = m.type_piece ?? ''
      representant.value.numero_piece = m.numero_piece ?? ''
      representant.value.date_naissance = m.date_naissance ?? ''
      representant.value.lieu_habitation = m.lieu_habitation ?? ''
    }
  }
  // Pré-remplissage de l'étape Transaction depuis le dossier
  try {
    const d = await dossiersService.get(props.dossierId)
    if (d.montant_tranche) transaction.value.montant_tranche = d.montant_tranche
    if (d.montant_transaction != null) transaction.value.montant_transaction = d.montant_transaction
    if (d.mode_paiement && ['especes','cheque','virement','autre'].includes(d.mode_paiement)) {
      transaction.value.mode_paiement = d.mode_paiement as 'especes' | 'cheque' | 'virement' | 'autre'
    }
  } catch { /* dossier non chargé */ }
})

// ── Validation ────────────────────────────────────────────────────────────────

// FR-2 : détecte les actionnaires avec ≥25% de détention
const hasBE25 = computed(() => beneficiaires.value.some(b => Number(b.pourcentage) >= 25))

const canNext = computed(() => {
  const f = form.value
  const r = representant.value
  if (currentStep.value === 0)
    return !!f.denomination_sociale?.trim() && !!f.forme_juridique && !!f.pays_constitution
  if (currentStep.value === 1)
    return !!f.adresse?.trim() && !!f.libelle_activite
  if (currentStep.value === 2)
    return !!r.nom?.trim() && !!r.prenoms?.trim() && !!r.fonction?.trim()
      && sfcState.value.status !== 'blocked'
  if (currentStep.value === 3)
    return !!f.description_operation?.trim()
  return true
})

function validateStep(): boolean {
  errors.value = {}
  const f = form.value
  const r = representant.value
  if (currentStep.value === 0) {
    if (!f.denomination_sociale?.trim()) { errors.value.denomination_sociale = 'La raison sociale est obligatoire.'; return false }
    if (!f.forme_juridique)              { errors.value.forme_juridique = 'La forme juridique est obligatoire.'; return false }
    if (!f.pays_constitution)            { errors.value.pays_constitution = 'Le pays de constitution est obligatoire.'; return false }
  }
  if (currentStep.value === 1) {
    if (!f.adresse?.trim())        { errors.value.adresse = 'L\'adresse du siège est obligatoire.'; return false }
    if (!f.libelle_activite)       { errors.value.libelle_activite = 'Le secteur d\'activité est obligatoire.'; return false }
  }
  if (currentStep.value === 2) {
    if (!r.nom?.trim())      { errors.value.representant_nom = 'Le nom du représentant est obligatoire.'; return false }
    if (!r.prenoms?.trim())  { errors.value.representant_prenoms = 'Les prénoms sont obligatoires.'; return false }
    if (!r.fonction?.trim()) { errors.value.representant_fonction = 'La fonction est obligatoire.'; return false }
  }
  if (currentStep.value === 3) {
    if (!f.description_operation?.trim()) { errors.value.description_operation = 'L\'objet de la relation est obligatoire (LBC/FT Art. 42).'; return false }
  }
  return true
}

// ── Auto-save ─────────────────────────────────────────────────────────────────

let autoSaveTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  autoSaveTimer = setInterval(autoSave, 30_000)
})
onUnmounted(() => {
  if (autoSaveTimer) clearInterval(autoSaveTimer)
})

async function autoSave() {
  if (!form.value.denomination_sociale?.trim()) return
  saveStatus.value = 'saving'
  try {
    await saveCurrentSection()
    saveStatus.value = 'saved'
    setTimeout(() => { if (saveStatus.value === 'saved') saveStatus.value = 'idle' }, 3000)
  } catch {
    saveStatus.value = 'error'
  }
}

async function saveCurrentSection(): Promise<KycPMData> {
  // Étape Transaction → sauvegarde au niveau dossier
  if (currentStep.value === 4) {
    await dossiersService.saveTransaction(props.dossierId, {
      montant_tranche: transaction.value.montant_tranche || undefined,
      montant_transaction: transaction.value.montant_transaction ?? undefined,
      mode_paiement: transaction.value.mode_paiement || undefined,
    })
    return form.value as KycPMData
  }
  const section = currentStep.value + 1
  const payload = buildPayload()
  const result = await dossiersService.saveKycPM(props.dossierId, section, payload)
  emit('saved', result)
  return result
}

function buildPayload(): Partial<KycPMData> {
  const p: Partial<KycPMData> = { ...form.value }
  // Pydantic rejette "" pour les dates → null
  if ((p as Record<string, unknown>).date_emission_rccm === '') (p as Record<string, unknown>).date_emission_rccm = null
  // Représentant légal → JSON `mandataire` + libellé `nom_representant_legal`
  const r = representant.value
  if (r.nom?.trim() || r.prenoms?.trim()) {
    p.nom_representant_legal = `${r.prenoms ?? ''} ${r.nom ?? ''}`.trim()
    p.mandataire = { ...r } as unknown as KycPMData['mandataire']
  }
  return p
}

// ── Navigation ────────────────────────────────────────────────────────────────

async function next() {
  if (!validateStep()) return
  saveStatus.value = 'saving'
  try {
    await saveCurrentSection()
    saveStatus.value = 'saved'
    setTimeout(() => { if (saveStatus.value === 'saved') saveStatus.value = 'idle' }, 2000)
    currentStep.value++
  } catch {
    saveStatus.value = 'error'
  }
}

function prev() {
  currentStep.value--
}

async function persistActionnaires() {
  // Persiste les actionnaires/associés (et BE ≥25%) via les endpoints dédiés.
  const rows = beneficiaires.value.filter(b => (b.nom?.trim() || b.prenoms?.trim()))
  for (let i = 0; i < rows.length; i++) {
    const b = rows[i]
    const nomComplet = `${b.prenoms ?? ''} ${b.nom ?? ''}`.trim()
    const pct = Number(b.pourcentage) || 0
    try {
      await dossiersService.addActionnaire(props.dossierId, {
        raison_sociale_nom: nomComplet,
        type_personne: 'PP',
        cni_passeport: null,
        pourcentage: pct,
        pays_residence: b.nationalite || null,
        ordre: i + 1,
      })
      // Un actionnaire ≥ 25% est aussi un bénéficiaire effectif (Art. 12b)
      if (pct >= 25) {
        await dossiersService.addBePM(props.dossierId, {
          raison_sociale_nom: nomComplet,
          cni_passeport: null,
          pourcentage: pct,
          pays_residence: b.nationalite || null,
          date_naissance: b.date_naissance || null,
          nationalite: b.nationalite || null,
        })
      }
    } catch {
      // best-effort : ne bloque pas la finalisation du KYC-PM
    }
  }
}

async function finish() {
  if (!validateStep()) return
  saving.value = true
  try {
    const result = await saveCurrentSection()
    await persistActionnaires()
    emit('completed', result)
  } catch {
    saveStatus.value = 'error'
  } finally {
    saving.value = false
  }
}

// ── Dynamic lists ─────────────────────────────────────────────────────────────

function addDirigeant() {
  dirigeants.value.push({ nom: '', prenoms: '', fonction: '', nationalite: '', date_naissance: '', lieu_habitation: '' })
  dirigeantScreenings.value.push({ status: 'idle', liste: null })
}
function removeDirigeant(i: number) {
  dirigeants.value.splice(i, 1)
  dirigeantScreenings.value.splice(i, 1)
}

function addBE() {
  beneficiaires.value.push({ nom: '', prenoms: '', nationalite: '', date_naissance: '', lieu_habitation: '', pourcentage: null, statut_ppe: false })
  beScreenings.value.push({ status: 'idle', liste: null })
}
function removeBE(i: number) {
  beneficiaires.value.splice(i, 1)
  beScreenings.value.splice(i, 1)
}
</script>

<style scoped>
.kyc-pm-stepper { display: flex; flex-direction: column; gap: 1.25rem; }

/* Step bar */
.step-bar { display: flex; align-items: flex-start; gap: 0; }
.step-item { display: flex; align-items: center; gap: 0.5rem; flex: 1; position: relative; }
.step-dot {
  width: 28px; height: 28px; border-radius: 50%; border: 2px solid var(--color-border);
  background: var(--color-bg-card); display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700; color: var(--color-text-muted); flex-shrink: 0; z-index: 1;
}
.step-dot svg { width: 13px; height: 13px; }
.step-item--done .step-dot  { border-color: var(--color-status-valide); background: var(--color-status-valide-bg); color: var(--color-status-valide); }
.step-item--active .step-dot { border-color: var(--color-sidebar-bg); background: var(--color-sidebar-bg); color: #fff; }
.step-label { font-size: 0.75rem; font-weight: 500; color: var(--color-text-muted); white-space: nowrap; }
.step-item--active .step-label  { color: var(--color-sidebar-bg); font-weight: 700; }
.step-item--done .step-label    { color: var(--color-text-secondary); }
.step-connector { flex: 1; height: 2px; background: var(--color-border); margin: 0 0.25rem; align-self: center; }
.step-item--done + .step-item .step-connector,
.step-item--done .step-connector { background: var(--color-status-valide); }

/* Save status */
.save-status { display: flex; align-items: center; gap: 0.375rem; font-size: 0.75rem; height: 1.25rem; color: transparent; }
.save-status svg { width: 14px; height: 14px; }
.save-status--saving { color: var(--color-text-secondary); }
.save-status--saved  { color: var(--color-status-valide); }
.save-status--error  { color: var(--color-status-bloque); }

/* Form */
.step-panel { padding: 1.5rem; }
.step-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 1.25rem; }
.step-section-label { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-secondary); margin: 0 0 0.75rem; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem 1.25rem; }
.form-group { display: flex; flex-direction: column; gap: 0.25rem; }
.form-group--full { grid-column: 1 / -1; }
.form-label { font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); }
.req { color: var(--color-status-bloque); }
.form-input, .form-select, .form-textarea {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; color: var(--color-text-primary); background: var(--color-bg-card); outline: none;
}
.form-input:focus, .form-select:focus, .form-textarea:focus {
  border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12);
}
.form-textarea { resize: vertical; }
.form-error { font-size: 0.75rem; color: var(--color-status-bloque); margin: 0; }
.checkbox-row { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.checkbox { width: 15px; height: 15px; cursor: pointer; accent-color: var(--color-sidebar-bg); }
.divider { border: none; border-top: 1px solid var(--color-border); margin: 1rem 0; }

/* Entities */
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }
.entity-row { background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 8px; padding: 0.875rem; margin-bottom: 0.75rem; position: relative; }
.btn-add { font-size: 0.75rem; font-weight: 600; color: var(--color-sidebar-bg); background: none; border: 1px solid var(--color-sidebar-bg); border-radius: 6px; padding: 0.25rem 0.625rem; cursor: pointer; }
.btn-add:hover { background: rgba(201,162,39,0.08); }
.btn-remove { margin-top: 0.625rem; font-size: 0.75rem; color: var(--color-status-bloque); background: none; border: none; cursor: pointer; padding: 0; }

/* PPE banner */
.ppe-banner { display: flex; align-items: center; gap: 0.5rem; background: var(--color-status-bloque-bg); color: var(--color-status-bloque); border-radius: 6px; padding: 0.5rem 0.75rem; font-size: 0.75rem; font-weight: 600; margin-top: 0.5rem; }
.ppe-banner svg { width: 14px; height: 14px; flex-shrink: 0; }

/* FR-2 — BE ≥25% notice */
.be25-notice { display: flex; align-items: flex-start; gap: 0.5rem; background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; border-radius: 8px; padding: 0.625rem 0.875rem; font-size: 0.8125rem; font-weight: 500; margin-bottom: 0.75rem; }
.espece-banner { display: flex; align-items: center; gap: 0.5rem; background: #fef2f2; color: #b91c1c; border: 1px solid #fca5a5; border-radius: 8px; padding: 0.75rem 0.875rem; font-size: 0.8125rem; font-weight: 600; margin-top: 1rem; }
.espece-banner svg { width: 18px; height: 18px; flex-shrink: 0; }

/* Mandant */
.mandant-block { background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 8px; padding: 0.875rem; margin-top: 0.75rem; }

/* Navigation */
.step-nav { display: flex; align-items: center; justify-content: space-between; padding-top: 0.25rem; }
.nav-right { display: flex; gap: 0.75rem; }
.btn-ghost { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.5rem 0.875rem; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 0.8125rem; cursor: pointer; }
.btn-ghost:hover { border-color: var(--color-sidebar-bg); color: var(--color-text-primary); }
.btn-primary { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5625rem 1.25rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { opacity: 0.88; }
.btn-icon { width: 14px; height: 14px; }

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 0.8s linear infinite; }

/* Sanctions/SFC banners */
.sanctions-banner { display: flex; align-items: flex-start; gap: 0.625rem; border-radius: 8px; padding: 0.625rem 0.875rem; font-size: 0.8125rem; margin: 0.75rem 0; }
.sanctions-banner--blocked  { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
.sanctions-banner--warning  { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
.sanctions-banner--checking { background: var(--color-bg-page); color: var(--color-text-muted); font-style: italic; }
.sanctions-banner__title { font-weight: 700; margin: 0 0 0.2rem; }
.sanctions-banner__msg { margin: 0; line-height: 1.5; }

/* Criblage par dirigeant / actionnaire */
.screening-badge { font-size: 0.75rem; font-weight: 600; border-radius: 6px; padding: 0.3rem 0.625rem; margin-top: 0.5rem; display: inline-block; }
.screening-badge--checking { background: var(--color-bg-page); color: var(--color-text-muted); font-style: italic; }
.screening-badge--blocked   { background: #fee2e2; color: #991b1b; }
.screening-badge--warning   { background: #fff7ed; color: #c2410c; }
.screening-badge--clear     { background: #d1fae5; color: #065f46; }
</style>
