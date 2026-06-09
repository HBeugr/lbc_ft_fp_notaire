<template>
  <div class="dos-stepper">

    <!-- Step nav -->
    <div class="stepper-nav">
      <div class="steps-track">
        <button
          v-for="(section, idx) in sections"
          :key="idx"
          class="step-btn"
          :class="{
            active: currentStep === idx,
            completed: completedSteps.has(idx),
            readonly: section.readonly,
          }"
          @click="goToStep(idx)"
        >
          <span class="step-bubble">
            <svg v-if="completedSteps.has(idx) && currentStep !== idx" viewBox="0 0 12 12" fill="none" class="check-icon">
              <path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span v-else>{{ idx + 1 }}</span>
          </span>
          <span class="step-label">{{ section.shortLabel }}</span>
        </button>
      </div>
      <div class="stepper-progress-bar">
        <div class="stepper-progress-fill" :style="{ width: `${((currentStep) / (sections.length - 1)) * 100}%` }" />
      </div>
    </div>

    <!-- Step content -->
    <div class="step-content">
      <div class="step-header">
        <div class="step-header-left">
          <span class="step-number-label">Étape {{ currentStep + 1 }}/{{ sections.length }}</span>
          <h2 class="step-title">{{ sections[currentStep].label }}</h2>
        </div>
        <div class="step-badges">
          <span v-if="sections[currentStep].required" class="badge badge-required">Obligatoire</span>
          <span v-if="sections[currentStep].readonly" class="badge badge-readonly">Pré-remplie</span>
        </div>
      </div>

      <!-- Section 1: Organisme déclarant -->
      <template v-if="currentStep === 0">
        <div class="field-grid">
          <div class="field-block full-span">
            <label class="form-label">Nom de l'organisme <span class="required-star">*</span></label>
            <input v-model="s1.nom_organisme" class="form-input" placeholder="Ex: Cabinet Notarial EPNFD-CI" />
          </div>
          <div class="field-block">
            <label class="form-label">Code profession <span class="required-star">*</span></label>
            <input v-model="s1.code_profession" class="form-input" placeholder="Ex: EPNFD" />
          </div>
          <div class="field-block">
            <label class="form-label">Adresse <span class="required-star">*</span></label>
            <input v-model="s1.adresse" class="form-input" placeholder="Ex: Abidjan, Côte d'Ivoire" />
          </div>
          <div class="field-block">
            <label class="form-label">Téléphone</label>
            <input v-model="s1.telephone" class="form-input" placeholder="Ex: +225 27 XX XX XX XX" />
          </div>
          <div class="field-block">
            <label class="form-label">Email</label>
            <input v-model="s1.email" class="form-input" type="email" placeholder="contact@organisme.ci" />
          </div>
          <div class="field-block full-span">
            <label class="form-label">Responsable LCB-FT</label>
            <input v-model="s1.responsable_lcbft" class="form-input" placeholder="Nom du responsable conformité" />
          </div>
        </div>
      </template>

      <!-- Section 2: Référence -->
      <template v-if="currentStep === 1">
        <div class="info-card">
          <div class="info-card-row">
            <span class="info-card-key">Référence DOS</span>
            <strong class="info-card-val ref-code">{{ dos.reference }}</strong>
          </div>
        </div>
        <p class="hint">Référence auto-générée au format DOS-{AAAA}-{NNN}. Non modifiable.</p>
      </template>

      <!-- Section 3: Objet -->
      <template v-if="currentStep === 2">
        <div class="field-block">
          <label class="form-label">Objet de la déclaration <span class="required-star">*</span></label>
          <textarea
            v-model="form.section_3_objet"
            class="form-textarea"
            rows="5"
            placeholder="Décrivez l'objet de la déclaration d'opération suspecte…"
          />
        </div>
      </template>

      <!-- Section 4: Identité déclarant -->
      <template v-if="currentStep === 3">
        <div class="field-grid">
          <div class="field-block">
            <label class="form-label">Nom et prénom</label>
            <input v-model="declarant.nom" class="form-input" placeholder="Nom complet" />
          </div>
          <div class="field-block">
            <label class="form-label">Fonction</label>
            <input v-model="declarant.fonction" class="form-input" placeholder="Responsable Conformité" />
          </div>
          <div class="field-block full-span">
            <label class="form-label">Email</label>
            <input v-model="declarant.email" class="form-input" type="email" placeholder="rc@cabinet.ci" />
          </div>
        </div>
      </template>

      <!-- Section 5: Contexte -->
      <template v-if="currentStep === 4">
        <div class="field-block">
          <label class="form-label">Contexte de l'opération suspecte <span class="required-star">*</span></label>
          <textarea
            v-model="form.section_5_contexte_operation"
            class="form-textarea"
            rows="6"
            placeholder="Décrivez les circonstances de l'opération suspecte, les dates, les parties impliquées…"
          />
        </div>
      </template>

      <!-- Section 6: Montant -->
      <template v-if="currentStep === 5">
        <div class="field-block field-block--narrow">
          <label class="form-label">Montant estimé (FCFA)</label>
          <div class="input-with-unit">
            <input
              v-model.number="form.section_6_montant_estime"
              class="form-input"
              type="number"
              min="0"
              placeholder="ex. 50 000 000"
            />
            <span class="input-unit">FCFA</span>
          </div>
          <p class="hint">Estimation du montant impliqué dans l'opération suspecte.</p>
        </div>
      </template>

      <!-- Section 7: Intervenants -->
      <template v-if="currentStep === 6">
        <div class="intervenants-wrap">

          <!-- Type badge + référence -->
          <div class="intervenant-header">
            <div class="client-type-badge" :class="s7.type_client === 'PM' ? 'badge-pm' : 'badge-pp'">
              <!-- PM: building icon -->
              <svg v-if="s7.type_client === 'PM'" viewBox="0 0 20 20" fill="none" class="badge-icon">
                <path d="M3 18V5a2 2 0 012-2h10a2 2 0 012 2v13M3 18h14M7 8h2m4 0h-2M7 12h2m4 0h-2M7 16h2m4 0h-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <!-- PP: person icon -->
              <svg v-else viewBox="0 0 20 20" fill="none" class="badge-icon">
                <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span>{{ s7.type_client === 'PM' ? 'Personne Morale' : 'Personne Physique' }}</span>
            </div>

            <div class="dossier-ref-chip">
              <span class="ref-label">Dossier KYC</span>
              <span class="ref-code-badge">{{ s7.dossier_reference }}</span>
            </div>
          </div>

          <!-- PP: détail personne physique -->
          <template v-if="s7.type_client === 'PP' && s7.client">
            <div class="intervenant-fields">
              <div class="field-cell">
                <span class="fc-label">Nom</span>
                <span class="fc-val">{{ s7.client.nom }}</span>
              </div>
              <div class="field-cell">
                <span class="fc-label">Prénom(s)</span>
                <span class="fc-val">{{ s7.client.prenoms }}</span>
              </div>
              <div class="field-cell">
                <span class="fc-label">Date de naissance</span>
                <span class="fc-val">{{ s7.client.date_naissance ? new Date(s7.client.date_naissance).toLocaleDateString('fr-FR') : '—' }}</span>
              </div>
              <div class="field-cell">
                <span class="fc-label">Nationalité</span>
                <span class="fc-val">{{ s7.client.nationalite || '—' }}</span>
              </div>
              <div class="field-cell full-width">
                <span class="fc-label">Pièce d'identité</span>
                <span class="fc-val">
                  <span class="piece-type">{{ s7.client.type_piece }}</span>
                  <span class="piece-num">{{ s7.client.numero_piece }}</span>
                </span>
              </div>
            </div>
          </template>

          <!-- PM: notice explicative -->
          <template v-else-if="s7.type_client === 'PM'">
            <div class="pm-notice">
              <div class="pm-notice-icon">
                <svg viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="1.5"/>
                  <path d="M10 9v5M10 7h.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                </svg>
              </div>
              <div class="pm-notice-body">
                <strong>Personne Morale identifiée</strong>
                <p>Les informations du représentant légal et des actionnaires sont enregistrées dans le dossier KYC associé <span class="ref-inline">{{ s7.dossier_reference }}</span>. Elles seront intégrées automatiquement à la DOS lors de la finalisation.</p>
              </div>
            </div>
          </template>

        </div>
        <p class="hint">Données pré-remplies depuis le dossier KYC associé — lecture seule.</p>
      </template>

      <!-- Section 8: Analyse -->
      <template v-if="currentStep === 7">
        <div class="field-block">
          <label class="form-label">Analyse de l'opération suspecte <span class="required-star">*</span></label>
          <textarea
            v-model="form.section_8_analyse_soupcon"
            class="form-textarea"
            rows="7"
            placeholder="Exposez votre analyse de l'opération suspecte, les éléments factuels et le raisonnement ayant conduit à la déclaration…"
          />
        </div>
      </template>

      <!-- Section 9: Motifs -->
      <template v-if="currentStep === 8">
        <div class="motifs-header">
          <label class="form-label">Motifs de suspicion retenus <span class="required-star">*</span></label>
          <span class="motifs-counter" :class="{ 'has-selection': selectedMotifs.length > 0 }">
            {{ selectedMotifs.length }} / {{ MOTIFS_SUSPICION.length }} sélectionné{{ selectedMotifs.length > 1 ? 's' : '' }}
          </span>
        </div>
        <div class="motifs-grid">
          <label
            v-for="motif in MOTIFS_SUSPICION"
            :key="motif"
            class="motif-item"
            :class="{ 'motif-item--checked': selectedMotifs.includes(motif) }"
          >
            <input
              type="checkbox"
              :value="motif"
              v-model="selectedMotifs"
              class="motif-checkbox"
            />
            <span class="motif-text">{{ motif }}</span>
          </label>
        </div>
      </template>

      <!-- Section 10: Compléments -->
      <template v-if="currentStep === 9">
        <div class="field-block">
          <label class="form-label">Informations complémentaires</label>
          <textarea
            v-model="form.section_10_informations_complementaires"
            class="form-textarea"
            rows="6"
            placeholder="Toute information complémentaire utile pour la CENTIF…"
          />
          <p class="hint">Facultatif — Éléments additionnels susceptibles d'aider la CENTIF dans son analyse.</p>
        </div>
      </template>
    </div>

    <!-- Error -->
    <div v-if="error" class="error-bar">
      <svg viewBox="0 0 16 16" fill="currentColor" class="error-icon"><path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 3.5a.75.75 0 01.75.75v3a.75.75 0 01-1.5 0v-3A.75.75 0 018 4.5zm0 7a.875.875 0 110-1.75.875.875 0 010 1.75z"/></svg>
      {{ error }}
    </div>

    <!-- Actions -->
    <div class="stepper-actions">
      <button class="btn-ghost" @click="emit('close')">
        <svg viewBox="0 0 16 16" fill="none" class="btn-icon"><path d="M4 8h8M4 8l3-3M4 8l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Fermer
      </button>
      <div class="nav-btns">
        <button v-if="currentStep > 0" class="btn-secondary" @click="prev">
          ‹ Précédent
        </button>
        <button
          v-if="!isLastStep"
          class="btn-primary"
          :disabled="saving"
          @click="saveAndNext"
        >
          <span v-if="saving" class="spinner" />
          {{ saving ? 'Enregistrement…' : 'Sauvegarder & Continuer ›' }}
        </button>
        <button
          v-if="isLastStep && dos.statut === 'brouillon'"
          class="btn-finalize"
          :disabled="saving || !canFinalize"
          @click="finalize"
        >
          <span v-if="saving" class="spinner spinner--light" />
          <svg v-else viewBox="0 0 16 16" fill="none" class="btn-icon"><path d="M2.5 8l4 4 7-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          {{ saving ? 'Finalisation…' : 'Finaliser la DOS' }}
        </button>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { dosService, MOTIFS_SUSPICION, type DosOut } from '@/services/dos'

const props = defineProps<{ dos: DosOut }>()
const emit = defineEmits<{
  (e: 'save', updated: DosOut): void
  (e: 'finalized', updated: DosOut): void
  (e: 'close'): void
}>()

const sections = [
  { label: 'Organisme déclarant', shortLabel: 'Organisme', readonly: false, required: true },
  { label: 'Référence', shortLabel: 'Référence', readonly: true, required: false },
  { label: 'Objet de la déclaration', shortLabel: 'Objet', readonly: false, required: true },
  { label: 'Identité du déclarant', shortLabel: 'Déclarant', readonly: false, required: false },
  { label: 'Contexte de l\'opération', shortLabel: 'Contexte', readonly: false, required: true },
  { label: 'Montant estimé', shortLabel: 'Montant', readonly: false, required: false },
  { label: 'Identification des intervenants', shortLabel: 'Intervenants', readonly: true, required: false },
  { label: 'Analyse de l\'opération suspecte', shortLabel: 'Analyse', readonly: false, required: true },
  { label: 'Motifs de suspicion', shortLabel: 'Motifs', readonly: false, required: true },
  { label: 'Informations complémentaires', shortLabel: 'Compléments', readonly: false, required: false },
]

const currentStep = ref(0)
const completedSteps = ref(new Set<number>([1, 6]))
const saving = ref(false)
const error = ref('')

const form = ref({
  section_3_objet: props.dos.section_3_objet ?? '',
  section_5_contexte_operation: props.dos.section_5_contexte_operation ?? '',
  section_6_montant_estime: props.dos.section_6_montant_estime ?? null,
  section_8_analyse_soupcon: props.dos.section_8_analyse_soupcon ?? '',
  section_10_informations_complementaires: props.dos.section_10_informations_complementaires ?? '',
})

const declarant = ref<Record<string, string>>(
  (props.dos.section_4_identite_declarant as Record<string, string>) ?? {}
)

const selectedMotifs = ref<string[]>(props.dos.section_9_motifs ?? [])

const s1 = ref<Record<string, string>>({
  nom_organisme: (props.dos.section_1_organisme as any)?.nom_organisme ?? '',
  code_profession: (props.dos.section_1_organisme as any)?.code_profession ?? '',
  adresse: (props.dos.section_1_organisme as any)?.adresse ?? '',
  telephone: (props.dos.section_1_organisme as any)?.telephone ?? '',
  email: (props.dos.section_1_organisme as any)?.email ?? '',
  responsable_lcbft: (props.dos.section_1_organisme as any)?.responsable_lcbft ?? '',
})
const s7 = computed(() => (props.dos.section_7_intervenants ?? {}) as any)
const isLastStep = computed(() => currentStep.value === sections.length - 1)

const canFinalize = computed(() =>
  !!(form.value.section_3_objet?.trim() &&
    form.value.section_5_contexte_operation?.trim() &&
    form.value.section_8_analyse_soupcon?.trim() &&
    selectedMotifs.value.length > 0)
)

function goToStep(idx: number) { currentStep.value = idx }
function prev() { if (currentStep.value > 0) currentStep.value-- }

async function saveAndNext() {
  error.value = ''
  const payload = buildPayload()
  if (Object.keys(payload).length > 0) {
    saving.value = true
    try {
      const updated = await dosService.updateSections(props.dos.id, payload)
      completedSteps.value.add(currentStep.value)
      emit('save', updated)
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Erreur lors de la sauvegarde.'
      return
    } finally {
      saving.value = false
    }
  } else {
    completedSteps.value.add(currentStep.value)
  }
  currentStep.value++
}

async function finalize() {
  error.value = ''
  const payload = buildPayload()
  saving.value = true
  try {
    if (Object.keys(payload).length > 0) {
      await dosService.updateSections(props.dos.id, payload)
    }
    const finalized = await dosService.finaliser(props.dos.id)
    emit('finalized', finalized)
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'Erreur lors de la finalisation.'
  } finally {
    saving.value = false
  }
}

function buildPayload(): Record<string, unknown> {
  const p: Record<string, unknown> = {}
  if (s1.value.nom_organisme || s1.value.code_profession || s1.value.adresse) p.section_1_organisme = { ...s1.value }
  if (form.value.section_3_objet) p.section_3_objet = form.value.section_3_objet
  if (Object.keys(declarant.value).length) p.section_4_identite_declarant = declarant.value
  if (form.value.section_5_contexte_operation) p.section_5_contexte_operation = form.value.section_5_contexte_operation
  if (form.value.section_6_montant_estime != null) p.section_6_montant_estime = form.value.section_6_montant_estime
  if (form.value.section_8_analyse_soupcon) p.section_8_analyse_soupcon = form.value.section_8_analyse_soupcon
  if (selectedMotifs.value.length) p.section_9_motifs = selectedMotifs.value
  if (form.value.section_10_informations_complementaires)
    p.section_10_informations_complementaires = form.value.section_10_informations_complementaires
  return p
}
</script>

<style scoped>
/* ── Wrapper ─────────────────────────────────────────────────────────────── */
.dos-stepper {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 24px rgba(27, 43, 75, 0.07);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── Step nav ────────────────────────────────────────────────────────────── */
.stepper-nav {
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  position: relative;
}

.steps-track {
  display: flex;
  overflow-x: auto;
  padding: 0.85rem 1.5rem 0;
  gap: 0.25rem;
  scrollbar-width: none;
}
.steps-track::-webkit-scrollbar { display: none; }

.step-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 0 0.65rem 0.85rem;
  border: none;
  background: none;
  cursor: pointer;
  min-width: 68px;
  flex-shrink: 0;
  border-bottom: 2px solid transparent;
  transition: border-color 0.2s;
  position: relative;
  z-index: 1;
}
.step-btn:hover .step-bubble { background: #e2e8f0; }
.step-btn.active { border-bottom-color: #c9a227; }
.step-btn.active .step-bubble { background: #1b2b4b; color: #fff; box-shadow: 0 0 0 3px rgba(27,43,75,0.15); }
.step-btn.completed .step-bubble { background: #16a34a; color: #fff; }
.step-btn.readonly .step-bubble { background: #dbeafe; color: #1d4ed8; }

.step-bubble {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #64748b;
  font-size: 0.7rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, color 0.2s, box-shadow 0.2s;
}
.check-icon { width: 12px; height: 12px; }
.step-label {
  font-size: 0.62rem;
  text-align: center;
  line-height: 1.2;
  color: #94a3b8;
  white-space: nowrap;
}
.step-btn.active .step-label { color: #1b2b4b; font-weight: 600; }
.step-btn.completed .step-label { color: #16a34a; }

.stepper-progress-bar {
  height: 2px;
  background: #e2e8f0;
  margin: 0;
}
.stepper-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #1b2b4b, #c9a227);
  transition: width 0.35s ease;
}

/* ── Step content ────────────────────────────────────────────────────────── */
.step-content {
  padding: 1.75rem 2rem;
  min-height: 300px;
  flex: 1;
}

.step-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  gap: 1rem;
}
.step-header-left { display: flex; flex-direction: column; gap: 0.2rem; }
.step-number-label { font-size: 0.72rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
.step-title { font-size: 1.1rem; font-weight: 700; color: #1b2b4b; margin: 0; }
.step-badges { display: flex; gap: 0.5rem; padding-top: 0.25rem; }

.badge {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.2rem 0.6rem;
  border-radius: 99px;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.badge-required { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.badge-readonly  { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }

/* ── Info card (readonly sections) ──────────────────────────────────────── */
.info-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
}
.info-card-row {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  padding: 0.7rem 1.25rem;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.875rem;
}
.info-card-row:last-child { border-bottom: none; }
.info-card-key { color: #64748b; min-width: 130px; flex-shrink: 0; }
.info-card-val { color: #1b2b4b; font-weight: 600; }
.ref-code { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.9rem; color: #1b2b4b; letter-spacing: 0.03em; }

/* ── Form fields ─────────────────────────────────────────────────────────── */
.form-label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.5rem;
}
.required-star { color: #dc2626; margin-left: 2px; }

.form-input {
  width: 100%;
  border: 1.5px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.55rem 0.85rem;
  font-size: 0.9rem;
  color: #1b2b4b;
  background: #fff;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}
.form-input:focus {
  outline: none;
  border-color: #1b2b4b;
  box-shadow: 0 0 0 3px rgba(27, 43, 75, 0.1);
}

.form-textarea {
  width: 100%;
  border: 1.5px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.65rem 0.85rem;
  font-size: 0.9rem;
  color: #1b2b4b;
  background: #fff;
  resize: vertical;
  font-family: inherit;
  line-height: 1.6;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}
.form-textarea:focus {
  outline: none;
  border-color: #1b2b4b;
  box-shadow: 0 0 0 3px rgba(27, 43, 75, 0.1);
}

.field-block { margin-bottom: 0.25rem; }
.field-block--narrow { max-width: 340px; }

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.full-span { grid-column: 1 / -1; }

.input-with-unit { display: flex; align-items: center; }
.input-with-unit .form-input { border-radius: 8px 0 0 8px; border-right: none; }
.input-unit {
  padding: 0.55rem 0.85rem;
  background: #f1f5f9;
  border: 1.5px solid #cbd5e1;
  border-left: none;
  border-radius: 0 8px 8px 0;
  font-size: 0.82rem;
  color: #64748b;
  font-weight: 600;
  white-space: nowrap;
}

.hint { font-size: 0.78rem; color: #94a3b8; margin: 0.6rem 0 0; line-height: 1.5; }

/* ── Section 7 Intervenants ──────────────────────────────────────────────── */
.intervenants-wrap {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.intervenant-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.client-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 1rem;
  border-radius: 99px;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.badge-icon { width: 16px; height: 16px; }
.badge-pm {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1.5px solid #bfdbfe;
}
.badge-pp {
  background: #f0fdf4;
  color: #15803d;
  border: 1.5px solid #bbf7d0;
}

.dossier-ref-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.4rem 0.85rem;
}
.ref-label {
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 500;
}
.ref-code-badge {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 0.82rem;
  font-weight: 700;
  color: #1b2b4b;
  letter-spacing: 0.04em;
}

.intervenant-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.field-cell {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.65rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.field-cell.full-width { grid-column: 1 / -1; }
.fc-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.fc-val {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1b2b4b;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.piece-type {
  font-size: 0.75rem;
  font-weight: 700;
  background: #e2e8f0;
  color: #475569;
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  text-transform: uppercase;
}
.piece-num {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 0.88rem;
  color: #1b2b4b;
  font-weight: 600;
}

.pm-notice {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 1rem 1.25rem;
}
.pm-notice-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  background: #dbeafe;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1d4ed8;
}
.pm-notice-icon svg { width: 18px; height: 18px; }
.pm-notice-body { flex: 1; }
.pm-notice-body strong { font-size: 0.88rem; color: #1e3a8a; display: block; margin-bottom: 0.3rem; }
.pm-notice-body p { font-size: 0.82rem; color: #3b82f6; margin: 0; line-height: 1.55; }
.ref-inline {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-weight: 700;
  font-size: 0.8rem;
  background: #dbeafe;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  color: #1d4ed8;
}

/* ── Motifs (Section 9) ──────────────────────────────────────────────────── */
.motifs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}
.motifs-header .form-label { margin-bottom: 0; }
.motifs-counter {
  font-size: 0.78rem;
  font-weight: 600;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 0.2rem 0.65rem;
  border-radius: 99px;
  transition: background 0.2s, color 0.2s;
}
.motifs-counter.has-selection { background: #dcfce7; color: #15803d; }

.motifs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.motif-item {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  padding: 0.65rem 0.85rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background: #fff;
}
.motif-item:hover { border-color: #1b2b4b; background: #f8fafc; }
.motif-item--checked { border-color: #1b2b4b; background: #f0f4ff; }

.motif-checkbox {
  margin-top: 1px;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  accent-color: #1b2b4b;
  cursor: pointer;
}
.motif-text {
  font-size: 0.82rem;
  color: #374151;
  line-height: 1.45;
}
.motif-item--checked .motif-text { color: #1b2b4b; font-weight: 500; }

/* ── Error bar ───────────────────────────────────────────────────────────── */
.error-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 2rem;
  padding: 0.6rem 0.85rem;
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 8px;
  color: #dc2626;
  font-size: 0.84rem;
  font-weight: 500;
}
.error-icon { width: 16px; height: 16px; flex-shrink: 0; }

/* ── Actions ─────────────────────────────────────────────────────────────── */
.stepper-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}
.nav-btns { display: flex; gap: 0.6rem; align-items: center; }

.btn-icon { width: 14px; height: 14px; }

.btn-ghost {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: none;
  border: none;
  color: #64748b;
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0.45rem 0.6rem;
  border-radius: 6px;
  transition: background 0.15s, color 0.15s;
}
.btn-ghost:hover { background: #e2e8f0; color: #1b2b4b; }

.btn-secondary {
  background: #fff;
  color: #1b2b4b;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.btn-secondary:hover { border-color: #1b2b4b; background: #f8fafc; }

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  background: #1b2b4b;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover { background: #c9a227; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }

.btn-finalize {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  background: #15803d;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.5rem 1.4rem;
  font-size: 0.875rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
  box-shadow: 0 2px 8px rgba(21, 128, 61, 0.25);
}
.btn-finalize:hover { background: #166534; }
.btn-finalize:disabled { opacity: 0.55; cursor: not-allowed; box-shadow: none; }

/* ── Spinner ─────────────────────────────────────────────────────────────── */
.spinner {
  display: inline-block;
  width: 13px;
  height: 13px;
  border: 2px solid rgba(27, 43, 75, 0.2);
  border-top-color: #1b2b4b;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
.spinner--light {
  border-color: rgba(255,255,255,0.3);
  border-top-color: #fff;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
