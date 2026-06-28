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

        <div class="modal-body">
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">Nom <span class="req">*</span></label>
              <input v-model="form.nom" type="text" class="form-input" @blur="triggerSanctionsCheck" />
              <p v-if="errors.nom" class="form-error">{{ errors.nom }}</p>
            </div>
            <div class="form-group">
              <label class="form-label">Prénoms</label>
              <input v-model="form.prenoms" type="text" class="form-input" @blur="triggerSanctionsCheck" />
            </div>
            <div class="form-group">
              <label class="form-label">N° pièce (CNI / passeport)</label>
              <input v-model="form.cni_passeport" type="text" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">% de participation <span class="req">*</span></label>
              <input v-model.number="form.pourcentage" type="number" min="0" max="100" step="0.01" class="form-input" placeholder="≥ 25 %" />
              <p v-if="errors.pourcentage" class="form-error">{{ errors.pourcentage }}</p>
            </div>
            <div class="form-group">
              <label class="form-label">Date de naissance</label>
              <input v-model="form.date_naissance" type="date" class="form-input" @blur="triggerSanctionsCheck" />
            </div>
            <CountrySelect v-model="form.nationalite" label="Nationalité" @blur="triggerSanctionsCheck" />
            <CountrySelect v-model="form.pays_residence" label="Pays de résidence" />
          </div>
        </div>

        <!-- Sanctions screening -->
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
import { dossiersService, type KycBEData } from '@/services/dossiers'
import CountrySelect from '@/components/common/CountrySelect.vue'

const props = defineProps<{
  dossierId: string
  be?: KycBEData | null
  clientType?: 'PP' | 'PM'
}>()

const emit = defineEmits<{
  close: []
  saved: [data: KycBEData]
}>()

const saving = ref(false)
const serverError = ref('')
const errors = ref<Record<string, string>>({})

// Champs d'aide nom/prenoms fusionnés en `raison_sociale_nom` au save.
const form = ref<{
  nom: string
  prenoms: string
  cni_passeport: string | null
  pourcentage: number | null
  date_naissance: string | null
  nationalite: string | null
  pays_residence: string | null
}>({
  nom: '',
  prenoms: '',
  cni_passeport: null,
  pourcentage: null,
  date_naissance: null,
  nationalite: null,
  pays_residence: null,
})

watch(() => props.be, (val) => {
  if (val) {
    const parts = (val.raison_sociale_nom ?? '').trim().split(' ')
    form.value.nom = parts[0] ?? ''
    form.value.prenoms = parts.slice(1).join(' ')
    form.value.cni_passeport = val.cni_passeport ?? null
    form.value.pourcentage = val.pourcentage ?? null
    form.value.date_naissance = val.date_naissance ?? null
    form.value.nationalite = val.nationalite ?? null
    form.value.pays_residence = val.pays_residence ?? null
  }
}, { immediate: true })

// ── Sanctions screening ───────────────────────────────────────────────────────
const sanctionsState = ref<{
  status: 'idle' | 'checking' | 'blocked' | 'warning' | 'clear' | 'no_lists'
  liste: string | null
  reason: string | null
}>({ status: 'idle', liste: null, reason: null })

let _sanctionsTimer: ReturnType<typeof setTimeout> | null = null

function triggerSanctionsCheck() {
  if (!form.value.nom?.trim()) return
  if (_sanctionsTimer) clearTimeout(_sanctionsTimer)
  _sanctionsTimer = setTimeout(async () => {
    sanctionsState.value.status = 'checking'
    const result = await dossiersService.checkSanctionsPreScreen(
      form.value.nom,
      form.value.prenoms || form.value.nom,
      form.value.date_naissance || undefined,
      form.value.nationalite || undefined,
    )
    sanctionsState.value.status = result.level
    sanctionsState.value.liste = result.liste
    sanctionsState.value.reason = result.reason
  }, 500)
}

watch(() => form.value.nom, (n) => {
  if (!n?.trim()) sanctionsState.value = { status: 'idle', liste: null, reason: null }
})

function buildBEPayload(): KycBEData {
  const f = form.value
  return {
    raison_sociale_nom: `${f.nom ?? ''} ${f.prenoms ?? ''}`.trim(),
    cni_passeport: f.cni_passeport || null,
    pourcentage: f.pourcentage ?? null,
    pays_residence: f.pays_residence || null,
    date_naissance: f.date_naissance || null,
    nationalite: f.nationalite || null,
  }
}

function validate(): boolean {
  errors.value = {}
  if (!form.value.nom?.trim()) errors.value.nom = 'Champ requis.'
  const pct = Number(form.value.pourcentage)
  if (form.value.pourcentage != null && (pct < 0 || pct > 100)) {
    errors.value.pourcentage = 'Pourcentage entre 0 et 100.'
  }
  return Object.keys(errors.value).length === 0
}

async function handleSave() {
  if (!validate()) return
  saving.value = true
  serverError.value = ''
  try {
    const ct = props.clientType ?? 'PP'
    const result = props.be?.id
      ? await dossiersService.updateKycBE(props.dossierId, props.be.id, buildBEPayload(), ct)
      : await dossiersService.createKycBE(props.dossierId, buildBEPayload(), ct)
    emit('saved', result)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: string } } }
    serverError.value = e?.response?.data?.detail ?? "Erreur lors de l'enregistrement."
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
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem 0.5rem; }
.modal-title  { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.modal-close  { background: none; border: none; cursor: pointer; padding: 0.25rem; color: var(--color-text-muted); }
.modal-close svg { width: 18px; height: 18px; }

.modal-body { padding: 1rem 1.5rem; overflow-y: auto; flex: 1; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem 1rem; }
.form-group { display: flex; flex-direction: column; gap: 0.25rem; }
.form-label { font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); }
.req { color: var(--color-status-bloque); }
.form-input {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; color: var(--color-text-primary); background: var(--color-bg-card); outline: none;
}
.form-input:focus {
  border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12);
}
.form-error { font-size: 0.75rem; color: var(--color-status-bloque); margin: 0; }

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

.modal-error { margin: 0 1.5rem; padding: 0.5rem 0.75rem; background: var(--color-status-bloque-bg); color: var(--color-status-bloque); border-radius: 7px; font-size: 0.8125rem; }

.modal-footer { display: flex; justify-content: flex-end; gap: 0.75rem; padding: 1rem 1.5rem; border-top: 1px solid var(--color-border); }
.btn-ghost { padding: 0.5rem 0.875rem; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 0.8125rem; cursor: pointer; }
.btn-primary { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5625rem 1.25rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-icon { width: 14px; height: 14px; }

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 0.8s linear infinite; }
</style>
