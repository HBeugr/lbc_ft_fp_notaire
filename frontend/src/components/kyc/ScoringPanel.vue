<template>
  <div class="scoring-panel">

    <!-- Current score banner (if already calculated) -->
    <div v-if="currentScore !== null" class="score-banner" :class="`score-banner--${currentNiveau?.toLowerCase()}`">
      <div class="score-banner-left">
        <span class="score-num">{{ currentScore }}<span class="score-denom">/20</span></span>
        <div>
          <p class="score-niveau">Risque <strong>{{ currentNiveau }}</strong></p>
          <p class="score-hint">Calculé · cliquez sur Recalculer pour mettre à jour</p>
        </div>
      </div>
      <button class="btn-recalc" @click="toggleAndRefresh">
        {{ showForm ? 'Masquer' : 'Recalculer' }}
      </button>
    </div>

    <!-- Empty state when no score yet -->
    <div v-else class="no-score-notice">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
      </svg>
      <p>Aucun score calculé pour ce dossier.</p>
    </div>

    <!-- Scoring form -->
    <div v-if="showForm" class="scoring-form">
      <div class="form-intro">
        <p class="form-intro-text">
          Évaluez chaque axe de risque sur 3 niveaux.
          Le score total (0–20) détermine le niveau FAIBLE / MOYEN / ÉLEVÉ selon les seuils NFR-8.
        </p>
        <div class="thresholds">
          <span class="threshold threshold--faible">FAIBLE 0–7</span>
          <span class="threshold threshold--moyen">MOYEN 8–13</span>
          <span class="threshold threshold--eleve">ÉLEVÉ 14–20</span>
        </div>
      </div>

      <div v-if="prefillLoading" class="prefill-loading">⟳ Calcul automatique en cours…</div>

      <div class="axes-grid">
        <div v-for="axe in axes" :key="axe.code" class="axe-row" :class="{ 'axe-row--auto': isAxeAuto(axe.code) }">
          <div class="axe-label-wrap">
            <span class="axe-label">
              {{ axe.label }}
              <span v-if="isAxeAuto(axe.code)" class="axe-auto-badge" title="Calculé automatiquement depuis les données KYC">🤖</span>
              <span v-if="isAxeAuto(axe.code) && !overrides[axe.code]" class="axe-lock-badge" title="Valeur verrouillée — cliquez pour surcharger">🔒</span>
              <span v-if="overrides[axe.code]" class="axe-override-badge" title="Valeur surchargée manuellement">✏️</span>
            </span>
            <span v-if="isAxeAuto(axe.code) && prefillSource(axe.code)" class="axe-hint axe-hint--auto">
              {{ prefillSource(axe.code) }}
            </span>
            <span v-else-if="axe.hint" class="axe-hint">{{ axe.hint }}</span>
          </div>
          <div class="axe-options">
            <button
              v-for="opt in options"
              :key="opt.value"
              type="button"
              class="axe-btn"
              :class="[`axe-btn--${opt.color}`, { 'axe-btn--active': form[axe.code] === opt.value }]"
              @click="handleAxeClick(axe.code, opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
          <span class="axe-score-val">{{ form[axe.code] }}</span>
        </div>
      </div>

      <!-- Trigger absolutoire warning (T1–T8) -->
      <div v-if="hasAbsolutoire" class="trigger-notice">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="trigger-icon">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        Trigger <strong>{{ existingTrigger }}</strong> actif — le niveau sera forcé à ÉLEVÉ indépendamment du score (absolutoire CDC §2.2).
      </div>

      <!-- Total preview -->
      <div class="total-preview">
        <span class="total-label">Score total estimé</span>
        <span class="total-value" :class="`total-value--${previewNiveau.toLowerCase()}`">
          {{ previewTotal }}/20 — {{ previewNiveau }}
        </span>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <button class="btn-cancel" type="button" @click="resetForm">Réinitialiser</button>
        <button
          class="btn-calculate"
          type="button"
          :disabled="saving"
          @click="calculate"
        >
          <span v-if="saving" class="spinner" />
          {{ saving ? 'Calcul en cours…' : 'Calculer et enregistrer' }}
        </button>
      </div>

      <!-- Error -->
      <p v-if="error" class="calc-error">{{ error }}</p>
    </div>

    <!-- Result breakdown (after calculation) -->
    <div v-if="lastResult" class="result-breakdown">
      <h4 class="breakdown-title">Détail du dernier calcul</h4>
      <div class="breakdown-grid">
        <div v-for="axe in lastResult.axes" :key="axe.code" class="breakdown-row">
          <span class="breakdown-label">{{ axe.label }}</span>
          <div class="breakdown-bar-track">
            <div class="breakdown-bar" :class="`bar--${barColor(axe.score)}`" :style="{ width: `${(axe.score / 2) * 100}%` }" />
          </div>
          <span class="breakdown-val">{{ axe.score }}/2</span>
        </div>
      </div>
    </div>

  </div>

  <!-- Modal de justification pour surcharge d'axe auto (CDC §9.2 AC8) -->
  <Teleport to="body">
    <div v-if="overrideModal.open" class="modal-overlay" @click.self="cancelOverride">
      <div class="modal-box">
        <h3 class="modal-title">⚠️ Surcharge d'axe automatique</h3>
        <p class="modal-desc">
          Vous modifiez l'axe <strong>{{ overrideModal.axeLabel }}</strong> de
          <strong>{{ overrideModal.autoValue }}</strong> → <strong>{{ overrideModal.newValue }}</strong>
          (valeur calculée automatiquement depuis les données KYC).
        </p>
        <p class="modal-desc">Une justification est obligatoire (min. 50 caractères) conformément au CDC §9.2.</p>
        <textarea
          v-model="overrideModal.justification"
          class="modal-textarea"
          placeholder="Justification de la surcharge…"
          rows="4"
        />
        <p class="modal-char-count" :class="{ 'modal-char-count--ok': overrideModal.justification.length >= 50 }">
          {{ overrideModal.justification.length }} / 50 caractères minimum
        </p>
        <p v-if="overrideModal.error" class="modal-error">{{ overrideModal.error }}</p>
        <div class="modal-actions">
          <button class="btn-modal-cancel" @click="cancelOverride">Annuler</button>
          <button
            class="btn-modal-confirm"
            :disabled="overrideModal.justification.length < 50"
            @click="confirmOverride"
          >Confirmer la surcharge</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { dossiersService, type DossierOut, type ScoringPrefill } from '@/services/dossiers'

const props = defineProps<{ dossier: DossierOut }>()
const emit = defineEmits<{ scored: [{ score: number; niveau: string }] }>()

const saving = ref(false)
const error = ref('')
const showForm = ref(true)

interface AxeResult { code: string; label: string; score: number; weight: number }
interface ScoreResult { total: number; niveau: string; axes: AxeResult[]; triggers_actifs: string[] }

const lastResult = ref<ScoreResult | null>(null)

const currentScore = computed(() => props.dossier.score_risque ?? null)
const currentNiveau = computed(() => props.dossier.niveau_risque ?? null)

watch(currentScore, (v) => { if (v !== null) showForm.value = false }, { immediate: true })

const ALL_ABSOLUTOIRES = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8']
const hasTriggerT1 = computed(() => props.dossier.trigger_actif === 'T1')
const existingTrigger = computed(() => props.dossier.trigger_actif ?? null)
const hasAbsolutoire = computed(() =>
  existingTrigger.value !== null && ALL_ABSOLUTOIRES.includes(existingTrigger.value)
)

const AXES = [
  { code: 'profil_client',        label: 'Profil client',          hint: 'Résident / Non-résident / Personne morale complexe' },
  { code: 'origine_geographique', label: 'Origine géographique',   hint: 'Zone GIABA / pays tiers / zone à risque' },
  { code: 'type_operation',       label: "Type d'opération",       hint: 'Location / Vente / Cession de parts' },
  { code: 'montant',              label: 'Montant de la transaction', hint: '< 5M / 5–15M / > 15M FCFA' },
  { code: 'mode_paiement',        label: 'Mode de paiement',       hint: 'Virement / Chèque / Espèces / Mixte' },
  { code: 'montage_juridique',    label: 'Montage juridique',      hint: 'Simple / Intermédiaire / Complexe (trust, SCI…)' },
  { code: 'statut_ppe',           label: 'Statut PPE',             hint: 'Aucun PPE / PPE détecté' },
  { code: 'qualite_documentaire', label: 'Qualité documentaire',   hint: 'Complet / Incomplet / Suspect' },
  { code: 'presse_negative',      label: 'Presse négative',        hint: 'Aucune / Ambigüe / Négative avérée' },
  { code: 'secteur_activite',     label: "Secteur d'activité",     hint: 'Immobilier résidentiel / Commercial / Offshore' },
] as const

type AxeCode = typeof AXES[number]['code']
type FormState = Record<AxeCode, number>

const axes = AXES

const options = [
  { value: 0, label: 'Faible',  color: 'low'    },
  { value: 1, label: 'Modéré',  color: 'medium' },
  { value: 2, label: 'Élevé',   color: 'high'   },
]

function defaultForm(): FormState {
  const f: Partial<FormState> = {}
  for (const axe of AXES) {
    f[axe.code] = axe.code === 'statut_ppe' && hasTriggerT1.value ? 2 : 0
  }
  return f as FormState
}

const form = reactive<FormState>(defaultForm())
const prefill = ref<ScoringPrefill | null>(null)
const prefillLoading = ref(false)

// Overrides: axeCode → justification (CDC §9.2 AC8 audit trail)
const overrides = reactive<Record<string, string>>({})

// Override modal state
const overrideModal = reactive({
  open: false,
  axeCode: '',
  axeLabel: '',
  autoValue: 0,
  newValue: 0,
  justification: '',
  error: '',
})

function resetForm() {
  const d = defaultForm()
  for (const k of Object.keys(d) as AxeCode[]) form[k] = d[k]
  for (const k of Object.keys(overrides)) delete overrides[k]
}

function isAxeAuto(code: string): boolean {
  return prefill.value?.axes[code]?.auto === true
}

function prefillSource(code: string): string {
  return prefill.value?.axes[code]?.source ?? ''
}

function handleAxeClick(code: string, newValue: number) {
  const axe = AXES.find(a => a.code === code)
  if (!axe) return

  // Non-auto axes: set directly
  if (!isAxeAuto(code)) {
    (form as any)[code] = newValue
    return
  }

  const autoValue = prefill.value?.axes[code]?.valeur ?? 0

  // Same value: no modal needed
  if (newValue === (form as any)[code]) return

  // Downgrade of an auto axe → require justification
  if (newValue < autoValue && !overrides[code]) {
    overrideModal.open = true
    overrideModal.axeCode = code
    overrideModal.axeLabel = axe.label
    overrideModal.autoValue = autoValue
    overrideModal.newValue = newValue
    overrideModal.justification = ''
    overrideModal.error = ''
    return
  }

  // Upgrade or re-override: allow freely
  (form as any)[code] = newValue
}

function cancelOverride() {
  overrideModal.open = false
}

function confirmOverride() {
  if (overrideModal.justification.length < 50) {
    overrideModal.error = 'La justification doit contenir au moins 50 caractères.'
    return
  }
  overrides[overrideModal.axeCode] = overrideModal.justification
  ;(form as any)[overrideModal.axeCode] = overrideModal.newValue
  overrideModal.open = false
}

async function loadPrefill() {
  prefillLoading.value = true
  try {
    prefill.value = await dossiersService.getScoringPrefill(props.dossier.id)
    for (const [code, axe] of Object.entries(prefill.value.axes)) {
      if (code in form && !overrides[code]) {
        (form as any)[code] = axe.valeur
      }
    }
  } catch {
    // prefill non critique — formulaire reste utilisable
  } finally {
    prefillLoading.value = false
  }
}

onMounted(() => { loadPrefill() })

async function toggleAndRefresh() {
  showForm.value = !showForm.value
  if (showForm.value) await loadPrefill()
}

const previewTotal = computed(() => {
  const sum = (Object.values(form) as number[]).reduce((a, b) => a + b, 0)
  return Math.min(20, Math.max(0, Math.round(sum)))
})

const previewNiveau = computed(() => {
  if (hasAbsolutoire.value) return 'ÉLEVÉ'
  if (previewTotal.value <= 7) return 'FAIBLE'
  if (previewTotal.value <= 13) return 'MOYEN'
  return 'ÉLEVÉ'
})

function barColor(score: number): string {
  if (score === 0) return 'low'
  if (score === 1) return 'medium'
  return 'high'
}

async function calculate() {
  saving.value = true
  error.value = ''
  try {
    const triggersPayload: string[] = []
    if (existingTrigger.value && ALL_ABSOLUTOIRES.includes(existingTrigger.value)) {
      triggersPayload.push(existingTrigger.value)
    }
    const overridesList = Object.entries(overrides).map(([axe, justification]) => ({
      axe,
      valeur_override: (form as any)[axe] as number,
      justification,
    }))
    const payload = {
      ...form,
      triggers_actifs: triggersPayload,
      overrides: overridesList,
    }
    const result = await dossiersService.calculateScore(props.dossier.id, payload)
    lastResult.value = result
    showForm.value = false
    emit('scored', { score: result.total, niveau: result.niveau })
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'Erreur lors du calcul.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.scoring-panel { display: flex; flex-direction: column; gap: 1.25rem; }

/* Score banner */
.score-banner {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 1.25rem; border-radius: 10px; border: 1.5px solid;
}
.score-banner--faible { background: var(--color-risk-low-bg);    border-color: var(--color-risk-low);    }
.score-banner--moyen  { background: var(--color-risk-medium-bg); border-color: var(--color-risk-medium); }
.score-banner--élevé,
.score-banner--eleve  { background: var(--color-risk-high-bg);   border-color: var(--color-risk-high);   }

.score-banner-left { display: flex; align-items: center; gap: 1rem; }
.score-num { font-size: 2.25rem; font-weight: 800; color: var(--color-text-primary); line-height: 1; }
.score-denom { font-size: 1rem; font-weight: 500; color: var(--color-text-muted); }
.score-niveau { font-size: 0.9375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.125rem; }
.score-hint { font-size: 0.75rem; color: var(--color-text-muted); margin: 0; }

.btn-recalc {
  padding: 0.375rem 0.875rem; border: 1px solid var(--color-border); border-radius: 7px;
  background: var(--color-bg-card); font-size: 0.8125rem; cursor: pointer; color: var(--color-text-secondary);
}
.btn-recalc:hover { border-color: var(--color-sidebar-bg); color: var(--color-sidebar-bg); }

/* No score */
.no-score-notice {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 1rem 1.25rem; background: var(--color-bg-page); border-radius: 8px;
  border: 1px dashed var(--color-border); color: var(--color-text-muted); font-size: 0.875rem;
}
.no-score-notice svg { width: 24px; height: 24px; flex-shrink: 0; stroke: var(--color-text-muted); }
.no-score-notice p { margin: 0; }

/* Form */
.scoring-form { display: flex; flex-direction: column; gap: 1rem; }

.form-intro { display: flex; flex-direction: column; gap: 0.5rem; }
.form-intro-text { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; }
.thresholds { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.threshold { padding: 2px 8px; border-radius: 5px; font-size: 0.6875rem; font-weight: 700; }
.threshold--faible { background: var(--color-risk-low-bg);    color: var(--color-risk-low); }
.threshold--moyen  { background: var(--color-risk-medium-bg); color: var(--color-risk-medium); }
.threshold--eleve  { background: var(--color-risk-high-bg);   color: var(--color-risk-high); }

/* Prefill loading */
.prefill-loading {
  font-size: 0.8125rem; color: var(--color-text-muted); padding: 0.5rem 0.75rem;
  background: var(--color-bg-page); border-radius: 6px; border: 1px solid var(--color-border);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* Axes */
.axes-grid { display: flex; flex-direction: column; gap: 0; border: 1px solid var(--color-border); border-radius: 8px; overflow: hidden; }
.axe-row {
  display: grid; grid-template-columns: 1fr auto auto;
  align-items: center; gap: 0.75rem; padding: 0.625rem 1rem;
  border-bottom: 1px solid var(--color-border);
}
.axe-row:last-child { border-bottom: none; }
.axe-row:nth-child(even) { background: var(--color-bg-page); }
.axe-row--auto { background: #f0f7ff !important; }

.axe-label-wrap { display: flex; flex-direction: column; gap: 0.125rem; min-width: 0; }
.axe-label { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-primary); }
.axe-hint  { font-size: 0.6875rem; color: var(--color-text-muted); }
.axe-hint--auto { color: #2563eb; font-style: italic; }
.axe-auto-badge { font-size: 0.75rem; margin-left: 4px; }
.axe-lock-badge { font-size: 0.65rem; margin-left: 2px; opacity: 0.7; }
.axe-override-badge { font-size: 0.65rem; margin-left: 2px; }

.axe-options { display: flex; gap: 3px; }
.axe-btn {
  padding: 4px 10px; border-radius: 5px; border: 1.5px solid var(--color-border);
  background: var(--color-bg-card); font-size: 0.75rem; font-weight: 500;
  cursor: pointer; color: var(--color-text-secondary); transition: all 0.1s;
}
.axe-btn--low.axe-btn--active    { background: var(--color-risk-low-bg);    border-color: var(--color-risk-low);    color: var(--color-risk-low); }
.axe-btn--medium.axe-btn--active { background: var(--color-risk-medium-bg); border-color: var(--color-risk-medium); color: var(--color-risk-medium); }
.axe-btn--high.axe-btn--active   { background: var(--color-risk-high-bg);   border-color: var(--color-risk-high);   color: var(--color-risk-high); }
.axe-btn:hover:not(.axe-btn--active) { border-color: var(--color-text-muted); color: var(--color-text-primary); }

.axe-score-val { font-size: 0.8125rem; font-weight: 700; color: var(--color-text-secondary); width: 18px; text-align: right; }

/* Trigger notice */
.trigger-notice {
  display: flex; align-items: center; gap: 0.5rem; padding: 0.625rem 0.875rem;
  background: var(--color-risk-high-bg); border: 1px solid var(--color-risk-high);
  border-radius: 7px; font-size: 0.8125rem; color: var(--color-risk-high); font-weight: 500;
}
.trigger-icon { width: 16px; height: 16px; flex-shrink: 0; }

/* Total preview */
.total-preview {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1rem; background: var(--color-bg-page);
  border: 1px solid var(--color-border); border-radius: 8px;
}
.total-label { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-secondary); }
.total-value { font-size: 0.9375rem; font-weight: 800; }
.total-value--faible { color: var(--color-risk-low); }
.total-value--moyen  { color: var(--color-risk-medium); }
.total-value--élevé,
.total-value--eleve  { color: var(--color-risk-high); }

/* Actions */
.form-actions { display: flex; gap: 0.625rem; justify-content: flex-end; }
.btn-cancel {
  padding: 0.5rem 1rem; border: 1px solid var(--color-border); border-radius: 8px;
  background: none; font-size: 0.8125rem; cursor: pointer; color: var(--color-text-secondary);
}
.btn-cancel:hover { background: var(--color-bg-page); }
.btn-calculate {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 1.25rem; background: var(--color-sidebar-bg); color: #fff;
  border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer;
}
.btn-calculate:hover:not(:disabled) { opacity: 0.88; }
.btn-calculate:disabled { opacity: 0.55; cursor: not-allowed; }
.spinner {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

.calc-error { font-size: 0.8125rem; color: var(--color-risk-high); margin: 0; }

/* Result breakdown */
.result-breakdown { border-top: 1px solid var(--color-border); padding-top: 1rem; }
.breakdown-title { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-secondary); margin: 0 0 0.75rem; }
.breakdown-grid { display: flex; flex-direction: column; gap: 0.375rem; }
.breakdown-row { display: grid; grid-template-columns: 1fr 120px 40px; align-items: center; gap: 0.75rem; }
.breakdown-label { font-size: 0.75rem; color: var(--color-text-secondary); }
.breakdown-bar-track { height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; }
.breakdown-bar { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.bar--low    { background: var(--color-risk-low); }
.bar--medium { background: var(--color-risk-medium); }
.bar--high   { background: var(--color-risk-high); }
.breakdown-val { font-size: 0.75rem; font-weight: 700; color: var(--color-text-secondary); text-align: right; }

/* Override modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 1000;
  display: flex; align-items: center; justify-content: center; padding: 1rem;
}
.modal-box {
  background: var(--color-bg-card); border-radius: 12px; padding: 1.5rem;
  width: 100%; max-width: 480px; box-shadow: 0 20px 60px rgba(0,0,0,0.25);
}
.modal-title { font-size: 1rem; font-weight: 700; margin: 0 0 0.75rem; color: var(--color-text-primary); }
.modal-desc { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0 0 0.75rem; }
.modal-textarea {
  width: 100%; box-sizing: border-box; padding: 0.625rem; border: 1.5px solid var(--color-border);
  border-radius: 8px; font-size: 0.8125rem; resize: vertical; min-height: 80px;
  color: var(--color-text-primary); background: var(--color-bg-page);
}
.modal-textarea:focus { outline: none; border-color: var(--color-sidebar-bg); }
.modal-char-count { font-size: 0.75rem; color: var(--color-text-muted); margin: 0.25rem 0 0.75rem; }
.modal-char-count--ok { color: var(--color-risk-low); }
.modal-error { font-size: 0.75rem; color: var(--color-risk-high); margin: 0 0 0.5rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.625rem; margin-top: 0.75rem; }
.btn-modal-cancel {
  padding: 0.5rem 1rem; border: 1px solid var(--color-border); border-radius: 8px;
  background: none; cursor: pointer; font-size: 0.8125rem; color: var(--color-text-secondary);
}
.btn-modal-confirm {
  padding: 0.5rem 1.25rem; background: var(--color-sidebar-bg); color: #fff;
  border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer;
}
.btn-modal-confirm:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
