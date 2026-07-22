<template>
  <div class="signalement-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Signalement d'alerte interne</h1>
        <p class="page-subtitle">Signalez un comportement ou une situation suspecte au Responsable Conformité</p>
      </div>
    </div>

    <div class="card form-card">
      <form @submit.prevent="handleSubmit" novalidate>
        <div class="field-group">
          <label class="field-label">Description de la situation suspecte <span class="req">*</span></label>
          <textarea
            v-model="description"
            class="field-textarea"
            :class="{ 'field-input--error': errors.description }"
            rows="5"
            placeholder="Décrivez le comportement ou la situation qui vous paraît suspect (identité du client, nature de la transaction, incohérences constatées…)"
          />
          <p v-if="errors.description" class="field-error">{{ errors.description }}</p>
        </div>

        <div class="field-group">
          <label class="field-label">Référence dossier concerné <span class="field-hint">(optionnel)</span></label>
          <input
            v-model="dossierRef"
            type="text"
            class="field-input"
            placeholder="Ex : KYC-2026-00042"
          />
          <p class="field-hint-text">Si le signalement est lié à un dossier client, indiquez sa référence.</p>
        </div>

        <div v-if="successMsg" class="alert-success">{{ successMsg }}</div>
        <div v-if="errorMsg" class="alert-error">{{ errorMsg }}</div>

        <div class="form-actions">
          <button type="submit" class="btn-primary" :disabled="submitting">
            <span v-if="submitting" class="spinner" />
            {{ submitting ? 'Envoi en cours…' : 'Envoyer le signalement' }}
          </button>
        </div>
      </form>
    </div>

    <!-- Historique des signalements de l'agent -->
    <div v-if="history.length > 0" class="card history-card">
      <h2 class="history-title">Vos signalements récents</h2>
      <table class="history-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Statut</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in history" :key="a.id">
            <td class="td-date">{{ formatDate(a.created_at) }}</td>
            <td class="td-desc">{{ a.description }}</td>
            <td>
              <span class="statut-badge" :class="a.statut === 'TRAITEE' ? 'badge--traitee' : 'badge--ouverte'">
                {{ a.statut === 'TRAITEE' ? 'Traité' : 'En cours' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { alertesService } from '@/services/alertes'

const description = ref('')
const dossierRef = ref('')
const submitting = ref(false)
const successMsg = ref('')
const errorMsg = ref('')
const errors = ref<{ description?: string }>({})
const history = ref<{ id: string; created_at: string; description: string; statut: string }[]>([])

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

async function handleSubmit() {
  errors.value = {}
  successMsg.value = ''
  errorMsg.value = ''
  if (!description.value.trim()) {
    errors.value.description = 'La description est obligatoire.'
    return
  }
  submitting.value = true
  try {
    const alerte = await alertesService.signalerInterne(description.value.trim(), dossierRef.value.trim() || undefined)
    history.value.unshift(alerte as any)
    description.value = ''
    dossierRef.value = ''
    successMsg.value = 'Votre signalement a été transmis au Responsable Conformité.'
  } catch (err: any) {
    errorMsg.value = err?.response?.data?.detail ?? 'Une erreur est survenue lors de l\'envoi.'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const items = await alertesService.mesSignalements()
    history.value = items.map(a => ({
      id: a.id,
      created_at: a.created_at,
      description: a.description,
      statut: a.statut,
    }))
  } catch { /* silently ignore — history non-critical */ }
})
</script>

<style scoped>
.signalement-page { max-width: 720px; }
.page-header { margin-bottom: 1.5rem; }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }

.form-card { padding: 1.75rem; }
.field-group { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 1.25rem; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.req { color: var(--color-risk-high); }
.field-hint { font-size: 0.75rem; color: var(--color-text-muted); font-weight: 400; margin-left: 0.25rem; }
.field-hint-text { font-size: 0.75rem; color: var(--color-text-muted); margin: 0.25rem 0 0; }
.field-input, .field-textarea {
  padding: 0.5625rem 0.75rem; border: 1px solid var(--color-border); border-radius: 7px;
  font-size: 0.875rem; color: var(--color-text-primary); background: #fff; outline: none;
  width: 100%; transition: border-color 0.15s, box-shadow 0.15s; resize: vertical;
}
.field-input:focus, .field-textarea:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.field-input--error { border-color: var(--color-risk-high); }
.field-error { font-size: 0.75rem; color: var(--color-risk-high); margin: 0; }
.alert-success { background: var(--color-risk-low-bg); color: var(--color-risk-low); border-radius: 7px; padding: 0.625rem 0.875rem; font-size: 0.8125rem; margin-bottom: 1rem; }
.alert-error { background: var(--color-risk-high-bg); color: var(--color-risk-high); border-radius: 7px; padding: 0.625rem 0.875rem; font-size: 0.8125rem; margin-bottom: 1rem; }
.form-actions { display: flex; justify-content: flex-end; }
.spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; margin-right: 0.375rem; vertical-align: middle; }
@keyframes spin { to { transform: rotate(360deg); } }

.history-card { padding: 1.5rem; margin-top: 1.5rem; }
.history-title { font-size: 0.875rem; font-weight: 600; color: var(--color-text-secondary); margin: 0 0 1rem; text-transform: uppercase; letter-spacing: 0.04em; }
.history-table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
.history-table th { text-align: left; font-size: 0.7rem; font-weight: 600; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; padding: 0.375rem 0.5rem; border-bottom: 1px solid var(--color-border); }
.history-table td { padding: 0.625rem 0.5rem; border-bottom: 1px solid var(--color-border); vertical-align: top; }
.history-table tr:last-child td { border-bottom: none; }
.td-date { white-space: nowrap; color: var(--color-text-secondary); }
.td-desc { max-width: 400px; }
.statut-badge { display: inline-block; border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.badge--ouverte { color: var(--color-status-en-analyse); background: var(--color-status-en-analyse-bg); }
.badge--traitee { color: var(--color-risk-low); background: var(--color-risk-low-bg); }
</style>
