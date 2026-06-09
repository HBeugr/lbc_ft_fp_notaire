<template>
  <Teleport to="body">
    <div class="modal-backdrop" @click.self="$emit('close')">
      <div class="modal">
        <div class="modal-header">
          <h2 class="modal-title">{{ be?.id ? 'Modifier' : 'Ajouter' }} un bénéficiaire effectif</h2>
          <button class="modal-close" @click="$emit('close')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <!-- Step tabs -->
        <div class="tabs">
          <button
            v-for="(t, i) in TABS"
            :key="i"
            class="tab"
            :class="{ 'tab--active': activeTab === i }"
            @click="activeTab = i"
          >{{ t }}</button>
        </div>

        <div class="modal-body">
          <!-- Tab 1 — Identification -->
          <div v-if="activeTab === 0" class="form-grid">
            <div class="form-group">
              <label class="form-label">Nom <span class="req">*</span></label>
              <input v-model="form.nom" type="text" class="form-input" @blur="triggerSanctionsCheck" />
              <p v-if="errors.nom" class="form-error">{{ errors.nom }}</p>
            </div>
            <div class="form-group">
              <label class="form-label">Prénoms <span class="req">*</span></label>
              <input v-model="form.prenoms" type="text" class="form-input" @blur="triggerSanctionsCheck" />
              <p v-if="errors.prenoms" class="form-error">{{ errors.prenoms }}</p>
            </div>
            <div class="form-group">
              <label class="form-label">Date de naissance</label>
              <input v-model="form.date_naissance" type="date" class="form-input" @blur="triggerSanctionsCheck" />
            </div>
            <div class="form-group">
              <label class="form-label">Lieu de naissance</label>
              <input v-model="form.lieu_naissance" type="text" class="form-input" />
            </div>
            <CountrySelect v-model="form.nationalite" label="Nationalité" @blur="triggerSanctionsCheck" />
            <div class="form-group form-group--full">
              <label class="form-label">Adresse de résidence</label>
              <textarea v-model="form.adresse_residence" class="form-textarea" rows="2" />
            </div>
            <div class="form-group">
              <label class="form-label">Type de pièce</label>
              <select v-model="form.type_piece_identite" class="form-select">
                <option value="">— Sélectionner —</option>
                <option v-for="p in TYPES_PIECE" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Numéro de pièce</label>
              <input v-model="form.numero_piece" type="text" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">Date d'expiration</label>
              <input v-model="form.date_expiration_piece" type="date" class="form-input" />
            </div>
            <CountrySelect v-model="form.pays_emission_piece" label="Pays d'émission" />
          </div>

          <!-- Tab 2 — Qualification -->
          <div v-else-if="activeTab === 1" class="form-grid">
            <div class="form-group">
              <label class="form-label">% de détention <span class="req">*</span></label>
              <input v-model.number="form.pourcentage_detention" type="number" min="25" max="100" step="0.01" class="form-input" placeholder="≥ 25 %" />
              <p v-if="errors.pourcentage_detention" class="form-error">{{ errors.pourcentage_detention }}</p>
            </div>
            <div class="form-group">
              <label class="form-label">Type de contrôle</label>
              <select v-model="form.type_controle" class="form-select">
                <option value="">— Sélectionner —</option>
                <option value="Direct">Direct</option>
                <option value="Indirect">Indirect</option>
                <option value="Mixte">Mixte</option>
              </select>
            </div>
            <div class="form-group form-group--full">
              <label class="form-label">Nature du contrôle</label>
              <textarea v-model="form.nature_controle" class="form-textarea" rows="3" placeholder="Décrivez la nature et les modalités du contrôle exercé" />
            </div>
          </div>

          <!-- Tab 3 — Statut PPE -->
          <div v-else-if="activeTab === 2" class="form-grid">
            <div class="form-group form-group--full">
              <label class="checkbox-row">
                <input v-model="form.statut_ppe" type="checkbox" class="checkbox" />
                <span class="form-label" style="margin:0">Personne Politiquement Exposée (PPE)</span>
              </label>
            </div>
            <template v-if="form.statut_ppe">
              <div class="form-group form-group--full">
                <div class="ppe-banner">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                  <div>
                    <strong>Vigilance renforcée obligatoire (Trigger T1)</strong>
                    <p>Un sous-module KYC-PPE devra être complété pour ce bénéficiaire.</p>
                  </div>
                </div>
              </div>
              <div class="form-group form-group--full">
                <label class="form-label">Fonctions politiques exercées</label>
                <textarea v-model="form.fonctions_politiques" class="form-textarea" rows="3" placeholder="Décrivez les fonctions politiques actuelles ou passées" />
              </div>
              <div class="form-group form-group--full">
                <label class="form-label">Pays d'exposition</label>
                <input v-model="form.pays_exposition" type="text" class="form-input" placeholder="Pays dans lequel les fonctions sont/étaient exercées" />
              </div>
            </template>
            <div v-else class="form-group form-group--full">
              <p class="info-text">Cochez si ce bénéficiaire est ou a été une personne politiquement exposée (chef d'État, ministre, parlementaire, etc.)</p>
            </div>
          </div>
        </div>

        <!-- Sanctions bannières -->
        <div v-if="sanctionsState.status === 'blocked'" class="sanctions-banner sanctions-banner--blocked" role="alert">
          <span class="sanctions-banner__icon">⛔</span>
          <div>
            <p class="sanctions-banner__title">Création impossible</p>
            <p class="sanctions-banner__msg">Cette personne est sur la liste des sanctions financières ciblées</p>
          </div>
        </div>
        <div v-else-if="sanctionsState.status === 'warning'" class="sanctions-banner sanctions-banner--warning" role="alert">
          <span class="sanctions-banner__icon">⚠️</span>
          <div>
            <p class="sanctions-banner__title">Correspondance possible — vérification requise</p>
            <p class="sanctions-banner__msg">
              Correspondance détectée sur liste {{ sanctionsState.liste }}.
              Renseignez la date de naissance pour confirmer ou lever l'alerte.
            </p>
            <button class="btn-submit-review" :disabled="submittingReview" @click="submitForReview">
              <span v-if="submittingReview" class="spin btn-icon" style="display:inline-block;width:12px;height:12px;border:2px solid #fff;border-top-color:transparent;border-radius:50%" />
              {{ submittingReview ? 'Soumission…' : 'Soumettre pour vérification compliance' }}
            </button>
          </div>
        </div>
        <div v-else-if="sanctionsState.status === 'clear' && sanctionsState.reason === 'dob_mismatch'" class="sanctions-banner sanctions-banner--clear" role="status">
          <span class="sanctions-banner__icon">✅</span>
          <p class="sanctions-banner__msg">Homonyme confirmé — vérification levée</p>
        </div>

        <div v-if="serverError" class="modal-error">{{ serverError }}</div>

        <div class="modal-footer">
          <button class="btn-ghost" @click="$emit('close')">Annuler</button>
          <button
            class="btn-primary"
            :disabled="saving || sanctionsState.status === 'blocked' || sanctionsState.status === 'checking'"
            @click="handleSave"
          >
            <svg v-if="saving" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
            {{ saving ? 'Enregistrement…' : (be?.id ? 'Mettre à jour' : 'Ajouter') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { dossiersService, type KycBEData } from '@/services/dossiers'
import CountrySelect from '@/components/common/CountrySelect.vue'

const props = defineProps<{
  dossierId: string
  be?: KycBEData | null
}>()

const emit = defineEmits<{
  close: []
  saved: [data: KycBEData]
}>()

const TABS = ['Identification', 'Qualification', 'Statut PPE']
const TYPES_PIECE = ["Carte Nationale d'Identité", 'Passeport', 'Titre de séjour']

const router = useRouter()
const activeTab  = ref(0)
const saving     = ref(false)
const submittingReview = ref(false)
const serverError = ref('')
const errors     = ref<Record<string, string>>({})

// ── Sanctions screening ───────────────────────────────────────────────────────
const sanctionsState = ref<{
  status: 'idle' | 'checking' | 'blocked' | 'warning' | 'clear'
  liste: string | null
  reason: string | null
}>({ status: 'idle', liste: null, reason: null })

let _sanctionsTimer: ReturnType<typeof setTimeout> | null = null

function triggerSanctionsCheck() {
  if (!form.value.nom?.trim() || !form.value.prenoms?.trim()) return
  if (_sanctionsTimer) clearTimeout(_sanctionsTimer)
  _sanctionsTimer = setTimeout(async () => {
    sanctionsState.value.status = 'checking'
    const result = await dossiersService.checkSanctionsPreScreen(
      form.value.nom!,
      form.value.prenoms!,
      form.value.date_naissance || undefined,
      (form.value.nationalite as string) || undefined,
    )
    sanctionsState.value.status = result.level
    sanctionsState.value.liste  = result.liste
    sanctionsState.value.reason = result.reason
  }, 500)
}

watch([() => form.value.nom, () => form.value.prenoms], ([n, p]) => {
  if (!n?.trim() || !p?.trim()) {
    sanctionsState.value = { status: 'idle', liste: null, reason: null }
  }
})

const form = ref<Partial<KycBEData>>({
  nom: '',
  prenoms: '',
  date_naissance: null,
  lieu_naissance: null,
  nationalite: null,
  adresse_residence: null,
  type_piece_identite: '',
  numero_piece: null,
  date_expiration_piece: null,
  pays_emission_piece: null,
  pourcentage_detention: undefined,
  type_controle: null,
  nature_controle: null,
  statut_ppe: false,
  fonctions_politiques: null,
  pays_exposition: null,
})

watch(() => props.be, (val) => {
  if (val) Object.assign(form.value, val)
}, { immediate: true })

function validate(): boolean {
  errors.value = {}
  if (!form.value.nom?.trim()) errors.value.nom = 'Champ requis.'
  if (!form.value.prenoms?.trim()) errors.value.prenoms = 'Champ requis.'
  const pct = Number(form.value.pourcentage_detention)
  if (!pct || pct < 0 || pct > 100) errors.value.pourcentage_detention = 'Pourcentage entre 0 et 100 requis.'
  return Object.keys(errors.value).length === 0
}

async function submitForReview() {
  if (!validate()) {
    activeTab.value = Object.keys(errors.value).some(k => ['nom', 'prenoms'].includes(k)) ? 0 : 1
    return
  }
  submittingReview.value = true
  serverError.value = ''
  try {
    // Le save déclenche _handle_sanctions_warning côté backend → transition automatique
    // vers en_analyse. Pas d'appel séparé à dossiersService.transition() pour éviter
    // la double-transition (dossier déjà en en_analyse après le save).
    if (props.be?.id) {
      await dossiersService.updateKycBE(props.dossierId, props.be.id, form.value)
    } else {
      await dossiersService.createKycBE(
        props.dossierId,
        form.value as Parameters<typeof dossiersService.createKycBE>[1],
      )
    }
    router.push({ name: 'kyc-detail', params: { id: props.dossierId } })
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: { message?: string } | string } } }
    const detail = e?.response?.data?.detail
    serverError.value = (typeof detail === 'object' && detail !== null ? detail.message : detail as string)
      ?? 'Erreur lors de la soumission pour vérification.'
  } finally {
    submittingReview.value = false
  }
}

async function handleSave() {
  if (!validate()) {
    activeTab.value = Object.keys(errors.value).some(k => ['nom', 'prenoms'].includes(k)) ? 0 : 1
    return
  }
  saving.value = true
  serverError.value = ''
  try {
    let result: KycBEData
    if (props.be?.id) {
      result = await dossiersService.updateKycBE(props.dossierId, props.be.id, form.value)
    } else {
      result = await dossiersService.createKycBE(props.dossierId, form.value as Parameters<typeof dossiersService.createKycBE>[1])
    }
    emit('saved', result)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: string } } }
    serverError.value = e?.response?.data?.detail ?? 'Erreur lors de l\'enregistrement.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 200;
  display: flex; align-items: center; justify-content: center; padding: 1rem;
}
.modal {
  background: var(--color-bg-card); border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  width: 100%; max-width: 600px; max-height: 90vh; display: flex; flex-direction: column; overflow: hidden;
}
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem 0; }
.modal-title  { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.modal-close  { background: none; border: none; cursor: pointer; padding: 0.25rem; color: var(--color-text-muted); }
.modal-close svg { width: 18px; height: 18px; }

.tabs { display: flex; gap: 0; border-bottom: 1px solid var(--color-border); margin: 1rem 1.5rem 0; }
.tab { padding: 0.5rem 1rem; font-size: 0.8125rem; font-weight: 500; color: var(--color-text-secondary); background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; }
.tab--active { color: var(--color-sidebar-bg); border-bottom-color: var(--color-sidebar-bg); font-weight: 700; }

.modal-body { padding: 1.25rem 1.5rem; overflow-y: auto; flex: 1; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem 1rem; }
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
.checkbox { width: 15px; height: 15px; accent-color: var(--color-sidebar-bg); cursor: pointer; }
.info-text { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; }

.ppe-banner {
  display: flex; gap: 0.75rem; align-items: flex-start;
  background: var(--color-status-bloque-bg); color: var(--color-status-bloque);
  border-radius: 8px; padding: 0.75rem 1rem; font-size: 0.8125rem;
}
.ppe-banner svg { width: 18px; height: 18px; flex-shrink: 0; margin-top: 1px; }
.ppe-banner strong { font-weight: 700; display: block; margin-bottom: 0.25rem; }
.ppe-banner p { margin: 0; font-size: 0.75rem; }

.sanctions-banner {
  display: flex; align-items: flex-start; gap: 0.625rem;
  border-radius: 8px; margin: 0 1.5rem 0.5rem; padding: 0.75rem 1rem;
}
.sanctions-banner__icon { font-size: 1.1rem; flex-shrink: 0; }
.sanctions-banner__title { font-weight: 700; font-size: 0.8125rem; margin: 0 0 0.2rem; }
.sanctions-banner__msg { font-size: 0.75rem; margin: 0; }

.sanctions-banner--blocked { background: #fef2f2; border: 1px solid #fca5a5; }
.sanctions-banner--blocked .sanctions-banner__title { color: #991b1b; }
.sanctions-banner--blocked .sanctions-banner__msg { color: #b91c1c; }

.sanctions-banner--warning { background: #fffbeb; border: 1px solid #fcd34d; }
.sanctions-banner--warning .sanctions-banner__title { color: #92400e; }
.sanctions-banner--warning .sanctions-banner__msg { color: #b45309; }

.sanctions-banner--clear { background: #f0fdf4; border: 1px solid #86efac; }
.sanctions-banner--clear .sanctions-banner__msg { color: #15803d; font-weight: 600; }

.btn-submit-review {
  margin-top: 0.5rem; display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.35rem 0.75rem; background: #b45309; color: #fff;
  border: none; border-radius: 6px; font-size: 0.75rem; font-weight: 600;
  cursor: pointer; transition: opacity 0.15s;
}
.btn-submit-review:disabled { opacity: 0.6; cursor: not-allowed; }

.modal-error { margin: 0 1.5rem; padding: 0.5rem 0.75rem; background: var(--color-status-bloque-bg); color: var(--color-status-bloque); border-radius: 7px; font-size: 0.8125rem; }

.modal-footer { display: flex; justify-content: flex-end; gap: 0.75rem; padding: 1rem 1.5rem; border-top: 1px solid var(--color-border); }
.btn-ghost { padding: 0.5rem 0.875rem; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 0.8125rem; cursor: pointer; }
.btn-primary { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5625rem 1.25rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-icon { width: 14px; height: 14px; }

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 0.8s linear infinite; }
</style>
