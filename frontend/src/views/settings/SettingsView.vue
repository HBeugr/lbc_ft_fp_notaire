<template>
  <div class="settings-page">
    <div class="page-header">
      <h1 class="page-title">Paramètres</h1>
      <p class="page-sub">Configuration de la plateforme — réservé aux administrateurs.</p>
    </div>

    <!-- Pondérations scoring (FR-26) -->
    <div class="card">
      <div class="card-header">
        <div>
          <h2 class="card-title">Pondérations des axes de scoring</h2>
          <p class="card-desc">
            Ajustez le poids relatif de chaque axe (0.1 – 5.0).
            Les seuils FAIBLE / MOYEN / ÉLEVÉ sont verrouillés réglementairement (NFR-8).
          </p>
        </div>
        <span class="badge-locked">Seuils verrouillés</span>
      </div>

      <div v-if="loading" class="loading-state">Chargement des pondérations…</div>

      <form v-else class="weights-form" @submit.prevent="saveWeights">
        <div class="axes-grid">
          <div
            v-for="axe in axes"
            :key="axe.code"
            class="axe-row"
          >
            <div class="axe-info">
              <span class="axe-label">{{ axe.label }}</span>
              <span class="axe-code">{{ axe.code }}</span>
            </div>
            <div class="axe-control">
              <input
                v-model.number="weights[axe.code]"
                type="range"
                min="0.1"
                max="5"
                step="0.1"
                class="slider"
                :disabled="!isAdmin || saving"
              />
              <span class="axe-value" :class="weightClass(weights[axe.code])">
                × {{ weights[axe.code]?.toFixed(1) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Seuil Art. 74 -->
        <div class="threshold-row">
          <label class="field-label">
            Seuil espèces Art. 74 (FCFA)
            <span class="field-hint">Trigger T7 automatique au-dessus de ce montant</span>
          </label>
          <input
            v-model.number="seuilArt74"
            type="number"
            step="500000"
            min="1000000"
            class="field-input"
            :disabled="!isAdmin || saving"
          />
        </div>

        <!-- Seuils verrouillés (lecture seule) -->
        <div class="locked-thresholds">
          <h3 class="locked-title">Seuils de classification (verrouillés — NFR-8)</h3>
          <div class="thresholds-grid">
            <div class="threshold-chip chip--low">FAIBLE : 0 – 7</div>
            <div class="threshold-chip chip--medium">MOYEN : 8 – 13</div>
            <div class="threshold-chip chip--high">ÉLEVÉ : 14 – 20</div>
          </div>
        </div>

        <div class="form-footer">
          <span v-if="saveMsg" class="save-msg" :class="saveMsgClass">{{ saveMsg }}</span>
          <button
            v-if="isAdmin"
            type="submit"
            class="btn-save"
            :disabled="saving"
          >
            <span v-if="saving" class="spinner" />
            Enregistrer les pondérations
          </button>
          <p v-else class="read-only-notice">Lecture seule — seul un administrateur peut modifier les pondérations.</p>
        </div>
      </form>
    </div>

    <!-- Informations système -->
    <div class="card card--info">
      <h2 class="card-title">Informations système</h2>
      <div class="info-grid">
        <div class="info-row">
          <span class="info-label">Version API</span>
          <span class="info-val">1.0.0</span>
        </div>
        <div class="info-row">
          <span class="info-label">Réglementation</span>
          <span class="info-val">Ordonnance N°2023-875 (CI)</span>
        </div>
        <div class="info-row">
          <span class="info-label">Archivage</span>
          <span class="info-val">10 ans — irréversible (NFR-13)</span>
        </div>
        <div class="info-row">
          <span class="info-label">Chiffrement</span>
          <span class="info-val">AES-256 au repos · TLS 1.3 en transit</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'

const auth = useAuthStore()
const notif = useNotificationsStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const loading = ref(true)
const saving  = ref(false)
const saveMsg = ref('')
const saveMsgClass = ref('')

const seuilArt74 = ref(20_000_000)
const weights = ref<Record<string, number>>({})

const axes = [
  { code: 'profil_client',        label: 'Profil client' },
  { code: 'origine_geographique', label: 'Origine géographique' },
  { code: 'type_operation',       label: "Type d'opération" },
  { code: 'montant',              label: 'Montant' },
  { code: 'mode_paiement',        label: 'Mode de paiement' },
  { code: 'montage_juridique',    label: 'Montage juridique' },
  { code: 'statut_ppe',           label: 'Statut PPE' },
  { code: 'qualite_documentaire', label: 'Qualité documentaire' },
  { code: 'presse_negative',      label: 'Presse négative' },
  { code: 'secteur_activite',     label: "Secteur d'activité" },
]

function weightClass(v: number) {
  if (!v) return ''
  if (v >= 3)   return 'weight--high'
  if (v >= 1.5) return 'weight--medium'
  return 'weight--low'
}

async function loadWeights() {
  try {
    const { data } = await api.get('/scoring/weights')
    axes.forEach(a => {
      weights.value[a.code] = data[a.code] ?? 1.0
    })
    seuilArt74.value = data.seuil_art74_fcfa ?? 20_000_000
  } catch {
    // Defaults if endpoint unavailable
    axes.forEach(a => { weights.value[a.code] = 1.0 })
  } finally {
    loading.value = false
  }
}

async function saveWeights() {
  if (!isAdmin.value) return
  saving.value = true
  saveMsg.value = ''
  try {
    await api.put('/scoring/weights', {
      weights: { ...weights.value },
    })
    saveMsg.value = 'Pondérations enregistrées avec succès.'
    saveMsgClass.value = 'msg--ok'
    setTimeout(() => { saveMsg.value = '' }, 4000)
  } catch (err: any) {
    saveMsg.value = err?.response?.data?.detail ?? 'Erreur lors de la sauvegarde.'
    saveMsgClass.value = 'msg--err'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadWeights()
  notif.dismissWeightsBadge()
})
</script>

<style scoped>
.settings-page { display: flex; flex-direction: column; gap: 1.25rem; }
.page-header   { display: flex; flex-direction: column; gap: 0.25rem; }
.page-title    { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.page-sub      { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.card--info { background: var(--color-surface-alt, #f8fafc); }

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}
.card-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.card-desc  { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0.25rem 0 0; }

.badge-locked {
  flex-shrink: 0;
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 3px 8px;
  background: #fef3c7;
  color: #92400e;
  border-radius: 6px;
  border: 1px solid #fde68a;
  letter-spacing: 0.02em;
}

.loading-state { color: var(--color-text-secondary); font-size: 0.875rem; }

/* Axes grid */
.axes-grid { display: flex; flex-direction: column; gap: 0.625rem; }
.axe-row   { display: flex; align-items: center; gap: 1rem; }
.axe-info  { min-width: 210px; display: flex; flex-direction: column; gap: 2px; }
.axe-label { font-size: 0.875rem; font-weight: 500; color: var(--color-text-primary); }
.axe-code  { font-size: 0.6875rem; color: var(--color-text-secondary); font-family: monospace; }

.axe-control { display: flex; align-items: center; gap: 0.75rem; flex: 1; }
.slider      { flex: 1; accent-color: var(--color-accent, #c9a227); cursor: pointer; }
.slider:disabled { opacity: 0.5; cursor: not-allowed; }

.axe-value { min-width: 40px; font-size: 0.875rem; font-weight: 700; text-align: right; }
.weight--low    { color: #16a34a; }
.weight--medium { color: #d97706; }
.weight--high   { color: #dc2626; }

/* Seuil Art.74 */
.threshold-row  { display: flex; flex-direction: column; gap: 0.375rem; max-width: 320px; }
.field-label    { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); }
.field-hint     { display: block; font-size: 0.75rem; font-weight: 400; color: var(--color-text-secondary); margin-top: 2px; }
.field-input    { padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px; font-size: 0.875rem; width: 100%; }
.field-input:disabled { background: #f1f5f9; cursor: not-allowed; }

/* Locked thresholds */
.locked-thresholds { background: #f8fafc; border: 1px solid var(--color-border); border-radius: 8px; padding: 0.875rem 1rem; }
.locked-title { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-secondary); margin: 0 0 0.625rem; }
.thresholds-grid { display: flex; gap: 0.625rem; flex-wrap: wrap; }
.threshold-chip { font-size: 0.75rem; font-weight: 700; padding: 4px 12px; border-radius: 6px; }
.chip--low    { background: #dcfce7; color: #166534; }
.chip--medium { background: #fef9c3; color: #854d0e; }
.chip--high   { background: #fee2e2; color: #991b1b; }

/* Footer */
.form-footer { display: flex; align-items: center; justify-content: flex-end; gap: 1rem; padding-top: 0.25rem; }
.save-msg    { font-size: 0.8125rem; }
.msg--ok  { color: #16a34a; }
.msg--err { color: #dc2626; }
.btn-save {
  display: flex; align-items: center; gap: 0.375rem;
  padding: 0.5625rem 1.25rem;
  background: var(--color-accent, #c9a227);
  color: #fff;
  border: none; border-radius: 8px;
  font-size: 0.875rem; font-weight: 600;
  cursor: pointer;
}
.btn-save:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
.read-only-notice { font-size: 0.8125rem; color: var(--color-text-secondary); }

/* Info grid */
.info-grid { display: flex; flex-direction: column; gap: 0.5rem; }
.info-row  { display: flex; gap: 1rem; font-size: 0.875rem; }
.info-label { min-width: 160px; color: var(--color-text-secondary); font-weight: 500; }
.info-val   { color: var(--color-text-primary); }
</style>
