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
          <input v-model="form.raison_sociale" type="text" class="form-input" placeholder="Nom complet de la société" />
          <p v-if="errors.raison_sociale" class="form-error">{{ errors.raison_sociale }}</p>
        </div>
        <div class="form-group">
          <label class="form-label">Forme juridique <span class="req">*</span></label>
          <select v-model="form.forme_juridique" class="form-select">
            <option value="">— Sélectionner —</option>
            <option v-for="f in FORMES_JURIDIQUES" :key="f" :value="f">{{ f }}</option>
          </select>
          <p v-if="errors.forme_juridique" class="form-error">{{ errors.forme_juridique }}</p>
        </div>
        <CountrySelect v-model="form.pays_enregistrement" label="Pays d'enregistrement *" />
        <p v-if="errors.pays_enregistrement" class="form-error" style="grid-column:1/-1">{{ errors.pays_enregistrement }}</p>
        <div class="form-group">
          <label class="form-label">RCCM</label>
          <input v-model="form.rccm" type="text" class="form-input" placeholder="CI-ABJ-2020-B-12345" />
        </div>
        <div class="form-group">
          <label class="form-label">NIF</label>
          <input v-model="form.nif" type="text" class="form-input" placeholder="Numéro d'identification fiscale" />
        </div>
        <div class="form-group">
          <label class="form-label">Date de création</label>
          <input v-model="form.date_creation" type="date" class="form-input" />
        </div>
      </div>
    </div>

    <!-- Step 2 — Siège & activité -->
    <div v-else-if="currentStep === 1" class="step-panel card">
      <h3 class="step-title">Siège social & activité</h3>
      <div class="form-grid">
        <div class="form-group form-group--full">
          <label class="form-label">Adresse du siège social <span class="req">*</span></label>
          <textarea v-model="form.adresse_siege" class="form-textarea" rows="2" placeholder="Adresse complète" />
          <p v-if="errors.adresse_siege" class="form-error">{{ errors.adresse_siege }}</p>
        </div>
        <div class="form-group">
          <label class="form-label">Secteur d'activité <span class="req">*</span></label>
          <select v-model="form.secteur_activite" class="form-select">
            <option value="">— Sélectionner —</option>
            <option v-for="s in SECTEURS" :key="s" :value="s">{{ s }}</option>
          </select>
          <p v-if="errors.secteur_activite" class="form-error">{{ errors.secteur_activite }}</p>
        </div>
        <div class="form-group">
          <label class="form-label">Capital social (FCFA)</label>
          <input v-model.number="form.capital_social" type="number" min="0" class="form-input" placeholder="0" />
        </div>
        <div class="form-group form-group--full">
          <label class="form-label">Description de l'activité</label>
          <textarea v-model="form.description_activite" class="form-textarea" rows="3" placeholder="Décrivez l'activité principale de la société" />
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
          <input v-model="form.representant_nom" type="text" class="form-input" />
          <p v-if="errors.representant_nom" class="form-error">{{ errors.representant_nom }}</p>
        </div>
        <div class="form-group">
          <label class="form-label">Prénoms <span class="req">*</span></label>
          <input v-model="form.representant_prenoms" type="text" class="form-input" />
          <p v-if="errors.representant_prenoms" class="form-error">{{ errors.representant_prenoms }}</p>
        </div>
        <div class="form-group">
          <label class="form-label">Fonction <span class="req">*</span></label>
          <input v-model="form.representant_fonction" type="text" class="form-input" placeholder="DG, PDG, Gérant…" />
          <p v-if="errors.representant_fonction" class="form-error">{{ errors.representant_fonction }}</p>
        </div>
        <CountrySelect v-model="form.representant_nationalite" label="Nationalité" />
        <div class="form-group">
          <label class="form-label">Type de pièce</label>
          <select v-model="form.representant_type_piece" class="form-select">
            <option value="">— Sélectionner —</option>
            <option v-for="p in TYPES_PIECE" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Numéro de pièce</label>
          <input v-model="form.representant_numero_piece" type="text" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Expiration pièce</label>
          <input v-model="form.representant_date_expiration_piece" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Date de naissance</label>
          <input v-model="form.representant_date_naissance" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Lieu d'habitation</label>
          <input v-model="form.representant_lieu_habitation" type="text" class="form-input" placeholder="Ville, Pays" />
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
          <label class="form-label">Objet de la relation d'affaires <span class="req">*</span></label>
          <textarea v-model="form.objet_relation" class="form-textarea" rows="2" placeholder="Décrivez la nature et l'objet de la relation commerciale…" />
          <p v-if="errors.objet_relation" class="form-error">{{ errors.objet_relation }}</p>
        </div>
        <div class="form-group form-group--full">
          <label class="form-label">Origine des fonds <span class="req">*</span></label>
          <textarea v-model="form.origine_fonds" class="form-textarea" rows="2" placeholder="Précisez la source des fonds (salaire, revenus, capital social…)" />
          <p v-if="errors.origine_fonds" class="form-error">{{ errors.origine_fonds }}</p>
        </div>
        <div class="form-group form-group--full">
          <label class="checkbox-row">
            <input v-model="form.est_compte_tiers" type="checkbox" class="checkbox" />
            <span class="form-label" style="margin:0">Opération pour le compte d'un tiers</span>
          </label>
        </div>
      </div>

      <!-- Mandant block -->
      <div v-if="form.est_compte_tiers" class="mandant-block">
        <p class="step-section-label">Informations sur le mandant</p>
        <div class="form-grid">
          <div class="form-group"><label class="form-label">Nom</label><input v-model="mandant.nom" type="text" class="form-input" /></div>
          <div class="form-group"><label class="form-label">Prénoms</label><input v-model="mandant.prenoms" type="text" class="form-input" /></div>
          <div class="form-group"><label class="form-label">Lien avec l'opération</label><input v-model="mandant.lien" type="text" class="form-input" /></div>
          <div class="form-group"><label class="form-label">Contact</label><input v-model="mandant.contact" type="text" class="form-input" /></div>
        </div>
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
import api from '@/services/auth'

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

const form = ref<Partial<KycPMData>>({
  raison_sociale: '',
  forme_juridique: '',
  rccm: '',
  nif: '',
  date_creation: '',
  pays_enregistrement: '',
  adresse_siege: '',
  secteur_activite: '',
  description_activite: '',
  capital_social: null,
  representant_nom: '',
  representant_prenoms: '',
  representant_fonction: '',
  representant_nationalite: '',
  representant_type_piece: '',
  representant_numero_piece: '',
  representant_date_expiration_piece: '',
  representant_date_naissance: '',
  representant_lieu_habitation: '',
  objet_relation: '',
  origine_fonds: '',
  est_compte_tiers: false,
})

const dirigeants   = ref<Dirigeant[]>([])
const beneficiaires = ref<BE[]>([])
const mandant      = ref({ nom: '', prenoms: '', lien: '', contact: '' })

// ── SFC Screening — représentant légal ───────────────────────────────────────
const sfcState = ref<{ status: 'idle' | 'checking' | 'clear' | 'warning' | 'blocked'; liste: string | null }>({
  status: 'idle', liste: null,
})
let _sfcTimer: ReturnType<typeof setTimeout> | null = null

watch(
  () => [form.value.representant_nom, form.value.representant_prenoms],
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
        d.lieu_habitation || undefined,
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
        be.lieu_habitation || undefined,
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
    if (data.dirigeants) {
      dirigeants.value = data.dirigeants as unknown as Dirigeant[]
      dirigeantScreenings.value = dirigeants.value.map(() => ({ status: 'idle' as const, liste: null }))
    }
    if (data.beneficiaires_effectifs) {
      beneficiaires.value = data.beneficiaires_effectifs as unknown as BE[]
      beScreenings.value = beneficiaires.value.map(() => ({ status: 'idle' as const, liste: null }))
    }
    if (data.mandant_info) Object.assign(mandant.value, data.mandant_info)
  }
})

// ── Validation ────────────────────────────────────────────────────────────────

// FR-2 : détecte les actionnaires avec ≥25% de détention
const hasBE25 = computed(() => beneficiaires.value.some(b => Number(b.pourcentage) >= 25))

const canNext = computed(() => {
  const f = form.value
  if (currentStep.value === 0)
    return !!f.raison_sociale?.trim() && !!f.forme_juridique && !!f.pays_enregistrement
  if (currentStep.value === 1)
    return !!f.adresse_siege?.trim() && !!f.secteur_activite
  if (currentStep.value === 2)
    return !!f.representant_nom?.trim() && !!f.representant_prenoms?.trim() && !!f.representant_fonction?.trim()
      && sfcState.value.status !== 'blocked'
  if (currentStep.value === 3)
    return !!f.objet_relation?.trim() && !!f.origine_fonds?.trim()
  return true
})

function validateStep(): boolean {
  errors.value = {}
  const f = form.value
  if (currentStep.value === 0) {
    if (!f.raison_sociale?.trim()) { errors.value.raison_sociale = 'La raison sociale est obligatoire.'; return false }
    if (!f.forme_juridique)        { errors.value.forme_juridique = 'La forme juridique est obligatoire.'; return false }
    if (!f.pays_enregistrement)    { errors.value.pays_enregistrement = 'Le pays d\'enregistrement est obligatoire.'; return false }
  }
  if (currentStep.value === 1) {
    if (!f.adresse_siege?.trim()) { errors.value.adresse_siege = 'L\'adresse du siège est obligatoire.'; return false }
    if (!f.secteur_activite)      { errors.value.secteur_activite = 'Le secteur d\'activité est obligatoire.'; return false }
  }
  if (currentStep.value === 2) {
    if (!f.representant_nom?.trim())      { errors.value.representant_nom = 'Le nom du représentant est obligatoire.'; return false }
    if (!f.representant_prenoms?.trim())  { errors.value.representant_prenoms = 'Les prénoms sont obligatoires.'; return false }
    if (!f.representant_fonction?.trim()) { errors.value.representant_fonction = 'La fonction est obligatoire.'; return false }
  }
  if (currentStep.value === 3) {
    if (!f.objet_relation?.trim()) { errors.value.objet_relation = 'L\'objet de la relation est obligatoire (LBC/FT Art. 42).'; return false }
    if (!f.origine_fonds?.trim())  { errors.value.origine_fonds = 'L\'origine des fonds est obligatoire (LBC/FT Art. 43).'; return false }
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
  if (!form.value.raison_sociale?.trim()) return
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
  const section = currentStep.value + 1
  const payload = buildPayload()
  const result = await dossiersService.saveKycPM(props.dossierId, section, payload)
  emit('saved', result)
  return result
}

const DATE_FIELDS: (keyof KycPMData)[] = ['date_creation', 'representant_date_expiration_piece']

function buildPayload(): Partial<KycPMData> {
  const p: Partial<KycPMData> = { ...form.value }
  // Pydantic rejects "" for date fields — send null instead
  for (const f of DATE_FIELDS) {
    if ((p as Record<string, unknown>)[f] === '') (p as Record<string, unknown>)[f] = null
  }
  const nonEmptyDirigeants = dirigeants.value.filter(d => d.nom?.trim() || d.prenoms?.trim())
  p.dirigeants = nonEmptyDirigeants.length ? nonEmptyDirigeants as unknown as Record<string, string>[] : undefined
  const nonEmptyBE = beneficiaires.value.filter(be => be.nom?.trim() || be.prenoms?.trim())
  p.beneficiaires_effectifs = nonEmptyBE.length ? nonEmptyBE as unknown as Record<string, string | number | boolean>[] : undefined
  if (form.value.est_compte_tiers && (mandant.value.nom || mandant.value.prenoms)) {
    p.mandant_info = { ...mandant.value }
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

async function finish() {
  if (!validateStep()) return
  saving.value = true
  try {
    const result = await saveCurrentSection()
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
