<template>
  <div class="kyc-stepper">
    <!-- Progress bar -->
    <div class="stepper-header">
      <div
        v-for="(step, i) in steps"
        :key="i"
        class="step-item"
        :class="{
          'step-item--active':    currentStep === i + 1,
          'step-item--completed': completedSections.has(i + 1),
          'step-item--future':    currentStep < i + 1 && !completedSections.has(i + 1),
        }"
        @click="goToStep(i + 1)"
      >
        <div class="step-circle">
          <svg v-if="completedSections.has(i + 1)" class="step-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <span v-else>{{ i + 1 }}</span>
        </div>
        <span class="step-label">{{ step.label }}</span>
        <div v-if="i < steps.length - 1" class="step-connector" :class="{ 'step-connector--done': completedSections.has(i + 1) }" />
      </div>
    </div>

    <!-- Section content -->
    <div class="stepper-body">
      <!-- Section 1 — État civil -->
      <section v-if="currentStep === 1" class="section-form">
        <h3 class="section-title">État civil</h3>
        <div class="form-row">
          <div class="field-group">
            <label class="field-label">Nom <span class="req">*</span></label>
            <input v-model="local.nom" type="text" class="field-input" :class="{ 'field-input--error': errors.nom }" placeholder="NOM" @input="clearError('nom')" @blur="triggerSanctionsCheck" />
            <p v-if="errors.nom" class="field-error">{{ errors.nom }}</p>
          </div>
          <div class="field-group">
            <label class="field-label">Prénom(s) <span class="req">*</span></label>
            <input v-model="local.prenoms" type="text" class="field-input" :class="{ 'field-input--error': errors.prenoms }" placeholder="Prénom(s)" @input="clearError('prenoms')" @blur="triggerSanctionsCheck" />
            <p v-if="errors.prenoms" class="field-error">{{ errors.prenoms }}</p>
          </div>
        </div>
        <div class="form-row">
          <div class="field-group">
            <label class="field-label">Date de naissance</label>
            <input v-model="local.date_naissance" type="date" class="field-input" @blur="triggerSanctionsCheck" />
          </div>
          <div class="field-group">
            <label class="field-label">Lieu de naissance</label>
            <input v-model="local.lieu_naissance" type="text" class="field-input" placeholder="Ville, Pays" />
          </div>
        </div>
        <div class="form-row">
          <CountrySelect v-model="local.nationalite" label="Nationalité" @blur="triggerSanctionsCheck" />
          <div class="field-group field-group--full">
            <label class="field-label">Adresse de résidence</label>
            <input v-model="local.adresse_residence" type="text" class="field-input" placeholder="Quartier, Commune, Ville" />
          </div>
        </div>
      </section>

      <!-- Section 2 — Pièce d'identité -->
      <section v-else-if="currentStep === 2" class="section-form">
        <h3 class="section-title">Pièce d'identité</h3>
        <div class="form-row">
          <div class="field-group">
            <label class="field-label">Type de pièce <span class="req">*</span></label>
            <select v-model="local.type_piece_identite" class="field-input" :class="{ 'field-input--error': errors.type_piece_identite }">
              <option value="">— Choisir —</option>
              <option value="CNI">Carte Nationale d'Identité</option>
              <option value="PASSEPORT">Passeport</option>
              <option value="TITRE_SEJOUR">Titre de séjour</option>
              <option value="PERMIS">Permis de conduire</option>
              <option value="ATTESTATION">Attestation d'identité</option>
            </select>
            <p v-if="errors.type_piece_identite" class="field-error">{{ errors.type_piece_identite }}</p>
          </div>
          <div class="field-group">
            <label class="field-label">Numéro de pièce <span class="req">*</span></label>
            <input v-model="local.numero_piece" type="text" class="field-input" :class="{ 'field-input--error': errors.numero_piece }" placeholder="CI0000000000" />
            <p v-if="errors.numero_piece" class="field-error">{{ errors.numero_piece }}</p>
          </div>
        </div>
        <div class="form-row">
          <div class="field-group">
            <label class="field-label">Date d'expiration</label>
            <input v-model="local.date_expiration_piece" type="date" class="field-input" />
          </div>
          <CountrySelect v-model="local.pays_emission_piece" label="Pays émetteur" />
        </div>

        <!-- Upload photo / scan pièce d'identité -->
        <div class="field-group" style="margin-top: 1rem;">
          <label class="field-label">Photo / Scan de la pièce d'identité</label>
          <input
            ref="fileInput"
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            style="display: none"
            @change="onFileChange"
          />
          <div
            class="upload-zone"
            :class="{ 'upload-zone--done': uploadedFile, 'upload-zone--error': uploadError }"
            @click="triggerFileInput"
            @drop.prevent="onDrop"
            @dragover.prevent
          >
            <template v-if="uploading">
              <span class="spinner upload-spinner" />
              <span>Upload en cours…</span>
            </template>
            <template v-else-if="uploadedFile">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="upload-icon upload-icon--ok"><polyline points="20 6 9 17 4 12"/></svg>
              <span>{{ uploadedFile.name }}</span>
            </template>
            <template v-else>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="upload-icon"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              <span>Cliquer ou déposer ici — PDF, JPG, PNG (max 20 Mo)</span>
            </template>
          </div>
          <p v-if="uploadError" class="field-error">{{ uploadError }}</p>
        </div>
      </section>

      <!-- Section 3 — Situation professionnelle -->
      <section v-else-if="currentStep === 3" class="section-form">
        <h3 class="section-title">Situation professionnelle & financière</h3>
        <div class="form-row">
          <div class="field-group">
            <label class="field-label">Situation professionnelle</label>
            <select v-model="local.situation_professionnelle" class="field-input">
              <option value="">— Choisir —</option>
              <option value="Salarié">Salarié</option>
              <option value="Indépendant">Indépendant / Entrepreneur</option>
              <option value="Professionnel libéral">Professionnel libéral</option>
              <option value="Retraité">Retraité</option>
              <option value="Étudiant">Étudiant</option>
              <option value="Sans emploi">Sans emploi</option>
              <option value="Autre">Autre</option>
            </select>
          </div>
          <div class="field-group">
            <label class="field-label">Profession / Secteur d'activité</label>
            <input v-model="local.profession" type="text" class="field-input" placeholder="Ex : Commerçant, Fonctionnaire…" />
          </div>
        </div>
        <div class="form-row">
          <div class="field-group">
            <label class="field-label">Employeur / Entreprise</label>
            <input v-model="local.employeur" type="text" class="field-input" placeholder="Nom de l'employeur ou entreprise" />
          </div>
          <div class="field-group">
            <label class="field-label">Revenus annuels estimés (FCFA)</label>
            <input v-model.number="local.revenus_annuels" type="number" min="0" class="field-input" placeholder="Ex : 12000000" />
          </div>
        </div>
      </section>

      <!-- Section 4 — Profil patrimonial -->
      <section v-else-if="currentStep === 4" class="section-form">
        <h3 class="section-title">Profil patrimonial</h3>
        <div class="field-group">
          <label class="field-label">Patrimoine estimé (FCFA)</label>
          <input v-model.number="local.patrimoine_estime" type="number" min="0" class="field-input" placeholder="Ex : 50000000" />
        </div>
        <div class="field-group">
          <label class="field-label">Sources de revenus</label>
          <textarea v-model="local.sources_revenus" class="field-input field-textarea" rows="3" placeholder="Décrivez les sources de revenus du client…" />
        </div>
        <div class="field-group">
          <label class="field-label">Origine des fonds</label>
          <textarea v-model="local.origine_fonds" class="field-input field-textarea" rows="3" placeholder="Ex : salaire, héritage, cession d'actifs, revenus locatifs…" />
        </div>
      </section>

      <!-- Section 5 — Objet de la relation -->
      <section v-else-if="currentStep === 5" class="section-form">
        <h3 class="section-title">Objet de la relation</h3>
        <div class="field-group">
          <label class="field-label">Objet précis de la relation</label>
          <textarea v-model="local.objet_relation" class="field-input field-textarea" rows="3" placeholder="Décrivez l'objet de la relation commerciale…" />
        </div>

        <!-- Statut PPE -->
        <div class="field-group">
          <label class="field-label checkbox-label">
            <input v-model="local.statut_ppe" type="checkbox" class="checkbox" />
            <span>Le client est une Personne Politiquement Exposée (PPE)</span>
          </label>
          <div v-if="local.statut_ppe" class="ppe-banner">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span>Trigger T1 activé — Le dossier sera classifié ÉLEVÉ automatiquement</span>
          </div>
        </div>

        <!-- Compte de tiers -->
        <div class="field-group">
          <label class="field-label checkbox-label">
            <input v-model="local.est_compte_tiers" type="checkbox" class="checkbox" />
            <span>Opération pour compte de tiers (mandant)</span>
          </label>
        </div>

        <!-- Mandant section — conditionally displayed -->
        <div v-if="local.est_compte_tiers" class="mandant-block">
          <h4 class="mandant-title">Informations sur le mandant</h4>
          <div class="form-row">
            <div class="field-group">
              <label class="field-label">Nom du mandant <span class="req">*</span></label>
              <input v-model="mandant.nom" type="text" class="field-input" placeholder="Nom du mandant" @blur="triggerMandantCheck" />
            </div>
            <div class="field-group">
              <label class="field-label">Prénom(s) du mandant</label>
              <input v-model="mandant.prenoms" type="text" class="field-input" placeholder="Prénom(s)" @blur="triggerMandantCheck" />
            </div>
          </div>
          <div class="form-row">
            <div class="field-group">
              <label class="field-label">Date de naissance</label>
              <input v-model="mandant.date_naissance" type="date" class="field-input" @blur="triggerMandantCheck" />
            </div>
            <div class="field-group">
              <label class="field-label">Lieu de naissance</label>
              <input v-model="mandant.lieu_naissance" type="text" class="field-input" placeholder="Ville, Pays" @blur="triggerMandantCheck" />
            </div>
          </div>
          <div class="form-row">
            <div class="field-group">
              <label class="field-label">Lien avec le client</label>
              <input v-model="mandant.lien" type="text" class="field-input" placeholder="Ex : conjoint, parent, employeur" />
            </div>
            <div class="field-group">
              <label class="field-label">Contact</label>
              <input v-model="mandant.contact" type="text" class="field-input" placeholder="Téléphone ou email" />
            </div>
          </div>

          <!-- Résultat criblage mandant -->
          <div v-if="mandantScreening.status === 'checking'" class="mandant-screen mandant-screen--checking">
            <svg class="mandant-screen__spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
            Criblage en cours…
          </div>
          <div v-else-if="mandantScreening.status === 'blocked'" class="mandant-screen mandant-screen--blocked">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
            Mandant présent sur liste de sanctions ({{ mandantScreening.liste }}) — dossier bloqué
          </div>
          <div v-else-if="mandantScreening.status === 'warning'" class="mandant-screen mandant-screen--warning">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            Correspondance possible sur liste {{ mandantScreening.liste }} — précisez la date de naissance
          </div>
          <div v-else-if="mandantScreening.status === 'clear'" class="mandant-screen mandant-screen--clear">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
            Aucune correspondance — mandant non sanctionné
          </div>
        </div>
      </section>
    </div>

    <!-- Sanctions — section 1 uniquement -->
    <template v-if="currentStep === 1">
      <!-- Blocage rouge : nom + DDN confirment la même personne -->
      <div v-if="sanctionsState.status === 'blocked'" class="sanctions-banner sanctions-banner--blocked" role="alert">
        <span class="sanctions-banner__icon">⛔</span>
        <div>
          <p class="sanctions-banner__title">Création impossible</p>
          <p class="sanctions-banner__msg">Cette personne est sur la liste des sanctions financières ciblées</p>
        </div>
      </div>

      <!-- Alerte orange : nom seul, DDN non confirmée → workflow superviseur -->
      <div v-else-if="sanctionsState.status === 'warning'" class="sanctions-banner sanctions-banner--warning" role="alert">
        <span class="sanctions-banner__icon">⚠️</span>
        <div>
          <p class="sanctions-banner__title">Correspondance possible — vérification requise</p>
          <p class="sanctions-banner__msg">
            Correspondance détectée sur liste {{ sanctionsState.liste }}.
            Renseignez la date de naissance pour confirmer ou lever l'alerte.
          </p>
          <button class="btn-submit-review" :disabled="submittingReview" @click="submitForReview">
            <span v-if="submittingReview" class="spinner" />
            {{ submittingReview ? 'Soumission en cours…' : 'Soumettre pour vérification compliance' }}
          </button>
        </div>
      </div>

      <!-- Vert : homonyme confirmé par DDN différente -->
      <div v-else-if="sanctionsState.status === 'clear' && sanctionsState.reason === 'dob_mismatch'" class="sanctions-banner sanctions-banner--clear" role="status">
        <span class="sanctions-banner__icon">✅</span>
        <p class="sanctions-banner__msg">Homonyme confirmé — vérification levée</p>
      </div>

      <!-- Aucune liste chargée — screening inopérant -->
      <div v-else-if="sanctionsState.status === 'no_lists'" class="sanctions-banner sanctions-banner--no-lists" role="alert">
        <span class="sanctions-banner__icon">⚠️</span>
        <div>
          <p class="sanctions-banner__title">Screening sanctions inopérant</p>
          <p class="sanctions-banner__msg">Aucune liste de sanctions n'est chargée. Contactez l'administrateur.</p>
        </div>
      </div>
    </template>

    <!-- Auto-save indicator -->
    <div class="save-status" :class="saveStatusClass">
      <svg v-if="saveStatus === 'saving'" class="save-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0"/></svg>
      <svg v-else-if="saveStatus === 'saved'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="save-icon"><polyline points="20 6 9 17 4 12"/></svg>
      <svg v-else-if="saveStatus === 'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="save-icon"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
      <span>{{ saveStatusLabel }}</span>
    </div>

    <!-- Navigation -->
    <div class="stepper-nav">
      <button type="button" class="btn-ghost-nav" :disabled="currentStep === 1" @click="goToStep(currentStep - 1)">
        ← Précédent
      </button>
      <button
        v-if="currentStep < steps.length"
        type="button"
        class="btn-primary"
        :disabled="(currentStep === 1 && (sanctionsState.status === 'blocked' || sanctionsState.status === 'checking')) || (currentStep === 2 && uploading)"
        @click="saveAndNext"
      >
        <span v-if="currentStep === 1 && sanctionsState.status === 'checking'" class="spinner" />
        Suivant →
      </button>
      <button
        v-else
        type="button"
        class="btn-primary"
        :disabled="saving
          || (currentStep === 1 && sanctionsState.status === 'blocked')
          || (local.est_compte_tiers && (mandantScreening.status === 'blocked' || mandantScreening.status === 'checking'))"
        @click="saveAndFinish"
      >
        <span v-if="saving" class="spinner" />
        Enregistrer le KYC-PP
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { dossiersService, type KycPPData } from '@/services/dossiers'
import CountrySelect from '@/components/common/CountrySelect.vue'

const props = defineProps<{
  dossierId: string
  initialData?: KycPPData | null
}>()

// ── Upload pièce d'identité (Section 2) ──────────────────────────────────────
const fileInput = ref<HTMLInputElement | null>(null)
const uploadedFile = ref<{ name: string } | null>(null)
const uploading = ref(false)
const uploadError = ref('')

function triggerFileInput() { fileInput.value?.click() }

function onDrop(e: DragEvent) {
  const file = e.dataTransfer?.files?.[0]
  if (file) doUpload(file)
}

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) doUpload(file)
}

async function doUpload(file: File) {
  uploadError.value = ''
  const MAX = 20 * 1024 * 1024
  const ALLOWED = ['application/pdf', 'image/jpeg', 'image/png']
  if (file.size > MAX) { uploadError.value = 'Fichier trop volumineux (max 20 Mo).'; return }
  if (!ALLOWED.includes(file.type)) { uploadError.value = 'Format non supporté (PDF, JPG, PNG).'; return }
  uploading.value = true
  try {
    await dossiersService.uploadDocument(props.dossierId, file, 'piece_identite')
    uploadedFile.value = { name: file.name }
  } catch {
    uploadError.value = 'Erreur lors de l\'upload. Veuillez réessayer.'
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

const emit = defineEmits<{
  saved: [data: KycPPData]
  completed: [data: KycPPData]
}>()

const STEPS = [
  { label: 'État civil' },
  { label: 'Pièce d\'identité' },
  { label: 'Situation pro.' },
  { label: 'Patrimoine' },
  { label: 'Objet relation' },
]

const steps = STEPS
const currentStep = ref(1)
const completedSections = ref<Set<number>>(new Set())
const errors = reactive<Record<string, string>>({})
const saving = ref(false)
const saveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
let autoSaveTimer: ReturnType<typeof setInterval>

// ── Sanctions screening ───────────────────────────────────────────────────────
const router = useRouter()

const sanctionsState = ref<{
  status: 'idle' | 'checking' | 'blocked' | 'warning' | 'clear' | 'no_lists'
  liste: string | null
  reason: string | null
}>({ status: 'idle', liste: null, reason: null })

const submittingReview = ref(false)

let _sanctionsTimer: ReturnType<typeof setTimeout> | null = null

function triggerSanctionsCheck() {
  if (!local.nom?.trim() || !local.prenoms?.trim()) return
  if (_sanctionsTimer) clearTimeout(_sanctionsTimer)
  _sanctionsTimer = setTimeout(async () => {
    sanctionsState.value.status = 'checking'
    const result = await dossiersService.checkSanctionsPreScreen(
      local.nom!,
      local.prenoms!,
      local.date_naissance || undefined,
      (local.nationalite as string) || undefined,
    )
    sanctionsState.value.status = result.level
    sanctionsState.value.liste  = result.liste
    sanctionsState.value.reason = result.reason
  }, 500)
}

async function submitForReview() {
  submittingReview.value = true
  try {
    // saveSection déclenche le backend qui appelle _handle_sanctions_warning
    // → transition automatique brouillon → en_analyse.
    // Pas d'appel séparé à dossiersService.transition() — évite la double-transition.
    const result = await saveSection(currentStep.value)
    if (result !== null) {
      router.push({ name: 'kyc-detail', params: { id: props.dossierId } })
    }
  } finally {
    submittingReview.value = false
  }
}

// Réinitialiser si nom ou prénom vidé
watch([() => local.nom, () => local.prenoms], ([n, p]) => {
  if (!n?.trim() || !p?.trim()) {
    sanctionsState.value = { status: 'idle', liste: null, reason: null }
  }
})

// Form state — mirrors KycPPData fields flat
const local = reactive<KycPPData>({
  nom: '', prenoms: '',
  date_naissance: null, lieu_naissance: null, nationalite: null, adresse_residence: null,
  type_piece_identite: null, numero_piece: null, date_expiration_piece: null, pays_emission_piece: null,
  situation_professionnelle: null, profession: null, employeur: null, revenus_annuels: null,
  patrimoine_estime: null, sources_revenus: null, origine_fonds: null,
  objet_relation: null, est_compte_tiers: false, statut_ppe: false, mandant_info: null,
})

// Mandant helper object (merged into mandant_info on save)
const mandant = reactive({ nom: '', prenoms: '', date_naissance: '', lieu_naissance: '', lien: '', contact: '' })

// ── Mandant screening ─────────────────────────────────────────────────────────
const mandantScreening = ref<{
  status: 'idle' | 'checking' | 'blocked' | 'warning' | 'clear' | 'no_lists'
  liste: string | null
}>({ status: 'idle', liste: null })

let _mandantTimer: ReturnType<typeof setTimeout> | null = null

function triggerMandantCheck() {
  if (!mandant.nom?.trim() || !mandant.prenoms?.trim()) return
  if (_mandantTimer) clearTimeout(_mandantTimer)
  _mandantTimer = setTimeout(async () => {
    mandantScreening.value.status = 'checking'
    const result = await dossiersService.checkSanctionsPreScreen(
      mandant.nom,
      mandant.prenoms,
      mandant.date_naissance || undefined,
      undefined,
      mandant.lieu_naissance || undefined,
    )
    mandantScreening.value.status = result.level
    mandantScreening.value.liste  = result.liste
  }, 500)
}

watch([() => mandant.nom, () => mandant.prenoms], ([n, p]) => {
  if (!n?.trim() || !p?.trim()) {
    mandantScreening.value = { status: 'idle', liste: null }
  }
})

// Init from existing data
onMounted(() => {
  if (props.initialData) {
    Object.assign(local, props.initialData)
    if (props.initialData.mandant_info) {
      Object.assign(mandant, props.initialData.mandant_info)
    }
    // Mark sections complete based on filled data
    if (local.nom && local.prenoms) completedSections.value.add(1)
    if (local.type_piece_identite && local.numero_piece) completedSections.value.add(2)
    if (local.situation_professionnelle) completedSections.value.add(3)
    if (local.origine_fonds || local.sources_revenus) completedSections.value.add(4)
    if (local.objet_relation) completedSections.value.add(5)
  }

  // Auto-save every 30 seconds
  autoSaveTimer = setInterval(() => autoSave(), 30_000)
})

onUnmounted(() => clearInterval(autoSaveTimer))

const saveStatusLabel = computed(() => ({
  idle: '',
  saving: 'Sauvegarde…',
  saved: 'Sauvegardé',
  error: 'Erreur de sauvegarde',
})[saveStatus.value])

const saveStatusClass = computed(() => ({
  'save-status--saving': saveStatus.value === 'saving',
  'save-status--saved':  saveStatus.value === 'saved',
  'save-status--error':  saveStatus.value === 'error',
}))

function clearError(field: string) { delete errors[field] }

function validateSection(step: number): boolean {
  Object.keys(errors).forEach(k => delete errors[k])
  if (step === 1) {
    if (!local.nom?.trim())     { errors.nom     = 'Requis.'; return false }
    if (!local.prenoms?.trim()) { errors.prenoms = 'Requis.'; return false }
  }
  if (step === 2) {
    if (!local.type_piece_identite) { errors.type_piece_identite = 'Requis.'; return false }
    if (!local.numero_piece?.trim()) { errors.numero_piece = 'Requis.'; return false }
  }
  return true
}

function buildPayload(): KycPPData {
  const payload = { ...local }
  if (local.est_compte_tiers && (mandant.nom || mandant.prenoms)) {
    payload.mandant_info = { ...mandant }
  }
  return payload
}

async function saveSection(step: number): Promise<KycPPData | null> {
  saveStatus.value = 'saving'
  try {
    const data = await dossiersService.saveKycPP(props.dossierId, step, buildPayload())
    completedSections.value.add(step)
    saveStatus.value = 'saved'
    emit('saved', data)
    setTimeout(() => { if (saveStatus.value === 'saved') saveStatus.value = 'idle' }, 3000)
    return data
  } catch {
    saveStatus.value = 'error'
    return null
  }
}

async function autoSave() {
  if (saveStatus.value === 'saving') return
  // Ne pas auto-sauvegarder en section 1 si une alerte sanctions est active :
  // évite de spammer criblage_resultats et alertes avec chaque tick de 30s.
  const sanctionsActive = currentStep.value === 1 &&
    (sanctionsState.value.status === 'blocked' || sanctionsState.value.status === 'warning')
  if (sanctionsActive) return
  await saveSection(currentStep.value)
}

function goToStep(step: number) {
  // Allow going back freely; going forward only if current is valid or completed
  if (step > currentStep.value && !completedSections.value.has(currentStep.value)) {
    if (!validateSection(currentStep.value)) return
  }
  currentStep.value = step
}

async function saveAndNext() {
  if (!validateSection(currentStep.value)) return
  saving.value = true
  const result = await saveSection(currentStep.value)
  saving.value = false
  if (result !== null) {
    currentStep.value = Math.min(currentStep.value + 1, steps.length)
  }
}

async function saveAndFinish() {
  if (!validateSection(currentStep.value)) return
  saving.value = true
  const result = await saveSection(currentStep.value)
  saving.value = false
  if (result !== null) {
    emit('completed', result)
  }
}
</script>

<style scoped>
.kyc-stepper { display: flex; flex-direction: column; gap: 1.5rem; }

/* ── Upload zone ── */
.upload-zone {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 0.875rem 1rem;
  border: 1.5px dashed var(--color-border);
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  background: var(--color-bg-page);
  transition: border-color 0.15s, background 0.15s;
  min-height: 46px;
}
.upload-zone:hover { border-color: var(--color-sidebar-bg); background: rgba(201,162,39,0.04); }
.upload-zone--done { border-style: solid; border-color: var(--color-risk-low); color: var(--color-risk-low); background: var(--color-risk-low-bg); }
.upload-zone--error { border-color: var(--color-risk-high); }
.upload-icon { width: 16px; height: 16px; flex-shrink: 0; }
.upload-icon--ok { stroke: var(--color-risk-low); }
.upload-spinner { width: 14px; height: 14px; border: 2px solid rgba(0,0,0,0.1); border-top-color: var(--color-sidebar-bg); border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }

/* ── Progress header ── */
.stepper-header {
  display: flex;
  align-items: flex-start;
  gap: 0;
  padding: 0 0.25rem;
  overflow-x: auto;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
  flex: 1;
  position: relative;
  cursor: pointer;
  min-width: 80px;
}

.step-circle {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.8125rem; font-weight: 700;
  background: var(--color-border);
  color: var(--color-text-secondary);
  transition: background 0.2s, color 0.2s;
  position: relative; z-index: 1;
  flex-shrink: 0;
}

.step-item--active .step-circle {
  background: var(--color-sidebar-bg);
  color: #fff;
}

.step-item--completed .step-circle {
  background: var(--color-risk-low);
  color: #fff;
}

.step-check { width: 14px; height: 14px; }

.step-label {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  text-align: center;
  line-height: 1.3;
  white-space: nowrap;
}

.step-item--active .step-label   { color: var(--color-sidebar-bg); font-weight: 600; }
.step-item--completed .step-label { color: var(--color-risk-low); }

.step-connector {
  position: absolute;
  top: 16px;
  left: calc(50% + 16px);
  right: calc(-50% + 16px);
  height: 2px;
  background: var(--color-border);
  z-index: 0;
}
.step-connector--done { background: var(--color-risk-low); }

/* ── Section form ── */
.stepper-body {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 1.5rem;
}

.section-title {
  font-size: 1rem; font-weight: 700;
  color: var(--color-sidebar-bg);
  margin: 0 0 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--color-accent-gold);
  display: inline-block;
}

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
.field-group { display: flex; flex-direction: column; gap: 0.3rem; }
.field-group--full { grid-column: 1 / -1; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.req { color: var(--color-risk-high); }
.field-input {
  padding: 0.5625rem 0.75rem; border: 1px solid var(--color-border); border-radius: 7px;
  font-size: 0.875rem; color: var(--color-text-primary); background: #fff; outline: none; width: 100%;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field-input:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.field-input--error { border-color: var(--color-risk-high); }
.field-textarea { resize: vertical; min-height: 80px; }
.field-error { font-size: 0.75rem; color: var(--color-risk-high); margin: 0; }

/* Checkbox */
.checkbox-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.checkbox { width: 16px; height: 16px; flex-shrink: 0; accent-color: var(--color-sidebar-bg); cursor: pointer; }

/* Sanctions banners */
.sanctions-banner {
  display: flex; align-items: flex-start; gap: 0.75rem;
  border-radius: 8px; padding: 0.875rem 1rem;
}
.sanctions-banner__icon { font-size: 1.25rem; flex-shrink: 0; line-height: 1.3; }
.sanctions-banner__title { font-weight: 700; font-size: 0.875rem; margin: 0 0 0.25rem; }
.sanctions-banner__msg { font-size: 0.8125rem; margin: 0; }

.sanctions-banner--blocked { background: #fef2f2; border: 1px solid #fca5a5; }
.sanctions-banner--blocked .sanctions-banner__title { color: #991b1b; }
.sanctions-banner--blocked .sanctions-banner__msg { color: #b91c1c; }

.sanctions-banner--warning { background: #fffbeb; border: 1px solid #fcd34d; }
.sanctions-banner--warning .sanctions-banner__title { color: #92400e; }
.sanctions-banner--warning .sanctions-banner__msg { color: #b45309; }

.sanctions-banner--clear { background: #f0fdf4; border: 1px solid #86efac; }
.sanctions-banner--clear .sanctions-banner__msg { color: #15803d; font-weight: 600; }

.sanctions-banner--no-lists { background: #fefce8; border: 1px solid #fde047; }
.sanctions-banner--no-lists .sanctions-banner__title { color: #854d0e; }
.sanctions-banner--no-lists .sanctions-banner__msg { color: #a16207; }

.btn-submit-review {
  margin-top: 0.625rem; display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.4rem 0.875rem; background: #b45309; color: #fff;
  border: none; border-radius: 6px; font-size: 0.8rem; font-weight: 600;
  cursor: pointer; transition: opacity 0.15s;
}
.btn-submit-review:disabled { opacity: 0.6; cursor: not-allowed; }

/* PPE banner */
.ppe-banner {
  display: flex; align-items: center; gap: 0.5rem;
  background: var(--color-risk-high-bg); color: var(--color-risk-high);
  border: 1px solid rgba(220,38,38,0.25); border-radius: 7px;
  padding: 0.625rem 0.875rem; font-size: 0.8125rem; font-weight: 600;
  margin-top: 0.5rem;
}
.ppe-banner svg { width: 16px; height: 16px; flex-shrink: 0; }

/* Mandant block */
.mandant-block {
  background: var(--color-bg-page); border: 1px solid var(--color-border);
  border-radius: 8px; padding: 1rem; margin-top: 0.75rem;
}
.mandant-title { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); margin: 0 0 0.875rem; }

.mandant-screen {
  display: flex; align-items: center; gap: 0.5rem;
  margin-top: 0.75rem; padding: 0.625rem 0.875rem;
  border-radius: 7px; font-size: 0.8125rem; font-weight: 500;
}
.mandant-screen svg { width: 15px; height: 15px; flex-shrink: 0; }
.mandant-screen__spinner { animation: spin 1s linear infinite; }
.mandant-screen--checking { background: var(--color-bg-card); color: var(--color-text-secondary); border: 1px solid var(--color-border); }
.mandant-screen--blocked  { background: #fef2f2; color: #b91c1c; border: 1px solid #fca5a5; }
.mandant-screen--warning  { background: #fffbeb; color: #92400e; border: 1px solid #fcd34d; }
.mandant-screen--clear    { background: #f0fdf4; color: #166534; border: 1px solid #86efac; }

/* Save status */
.save-status {
  display: flex; align-items: center; gap: 0.375rem;
  font-size: 0.75rem; color: var(--color-text-muted);
  min-height: 20px;
}
.save-status--saving { color: var(--color-text-secondary); }
.save-status--saved  { color: var(--color-risk-low); }
.save-status--error  { color: var(--color-risk-high); }
.save-icon { width: 13px; height: 13px; }
.save-spinner { width: 13px; height: 13px; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Nav buttons */
.stepper-nav { display: flex; justify-content: space-between; align-items: center; padding-top: 0.25rem; }
.btn-ghost-nav {
  padding: 0.5rem 1rem; background: none; border: 1px solid var(--color-border);
  border-radius: 7px; font-size: 0.875rem; color: var(--color-text-secondary);
  cursor: pointer; transition: border-color 0.12s;
}
.btn-ghost-nav:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-ghost-nav:not(:disabled):hover { border-color: var(--color-text-secondary); }
.spinner {
  width: 14px; height: 14px; flex-shrink: 0;
  border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block;
}
</style>
