<template>
  <div class="settings-page">
    <div class="page-header">
      <h1 class="page-title">Paramètres</h1>
      <p class="page-sub">Configuration de la plateforme — réservé aux administrateurs.</p>
    </div>

    <!-- Mon cabinet (SaaS multi-tenant) — lecture seule -->
    <div class="card">
      <div class="card-header">
        <div>
          <h2 class="card-title">Mon cabinet</h2>
          <p class="card-desc">
            Informations de l'espace du cabinet. Modifiables uniquement par l'administrateur
            de la plateforme.
          </p>
        </div>
        <span v-if="tenantStatut" class="badge-statut" :class="`badge-statut--${tenantStatut}`">
          {{ TENANT_STATUT_LABELS[tenantStatut] }}
        </span>
      </div>

      <div class="info-grid">
        <div class="info-row">
          <span class="info-label">Nom du cabinet</span>
          <span class="info-val">{{ tenantMe?.nom_cabinet ?? auth.tenantName ?? '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Identifiant</span>
          <span class="info-val info-val--mono">{{ tenantMe?.slug ?? auth.tenant?.slug ?? '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Pays</span>
          <span class="info-val">{{ tenantMe?.pays ?? '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">N° agrément</span>
          <!-- `numero_agrement` est nullable côté backend tant qu'il n'a pas été saisi. -->
          <span class="info-val">{{ tenantMe?.numero_agrement ?? '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Quota de sièges</span>
          <span class="info-val">
            {{ tenantMe && tenantMe.max_users > 0 ? tenantMe.max_users : 'Illimité' }}
          </span>
        </div>
        <div class="info-row">
          <span class="info-label">2FA obligatoire</span>
          <span class="info-val">{{ tenantMe?.totp_required ? 'Oui' : 'Non' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Sièges utilisés</span>
          <span class="info-val">
            <template v-if="quota">
              {{ quota.utilisateurs_actifs }}
              <template v-if="quota.quota_utilisateurs > 0"> / {{ quota.quota_utilisateurs }}</template>
              <span class="info-muted">
                ({{ quota.quota_utilisateurs === 0 ? 'quota illimité' : `${quotaRestant} restant(s)` }})
              </span>
            </template>
            <template v-else>—</template>
          </span>
        </div>
        <div v-if="quota" class="info-row">
          <span class="info-label">Dossiers enregistrés</span>
          <span class="info-val">{{ quota.dossiers_total }}</span>
        </div>
      </div>

      <!-- Jauge de consommation des sièges (masquée si quota illimité) -->
      <div v-if="quota && quota.quota_utilisateurs > 0" class="quota-bar">
        <div class="quota-fill" :class="quotaClass" :style="{ width: `${quotaPct}%` }" />
      </div>

      <!-- Logo du cabinet -->
      <div class="logo-section">
        <h3 class="sub-title">Logo du cabinet</h3>
        <p class="sub-desc">
          Affiché dans la barre latérale, à côté du nom du cabinet.
        </p>

        <div class="logo-row">
          <!-- Aperçu : gabarit fixe, l'image s'y inscrit sans déformation. -->
          <div class="logo-preview" :class="{ 'logo-preview--vide': !branding.logoUrl }">
            <img v-if="branding.logoUrl" class="logo-preview-img" :src="branding.logoUrl" alt="Logo du cabinet" />
            <span v-else class="logo-preview-vide">Aucun logo</span>
          </div>

          <div class="logo-actions">
            <template v-if="peutGererLogo">
              <input
                ref="logoInput"
                type="file"
                class="logo-file-input"
                :accept="acceptLogo"
                @change="handleLogoChange"
              />
              <div class="logo-buttons">
                <button type="button" class="btn-save" :disabled="logoBusy" @click="logoInput?.click()">
                  <span v-if="logoBusy" class="spinner" />
                  {{ branding.logoUrl ? 'Remplacer le logo' : 'Envoyer un logo' }}
                </button>
                <button
                  v-if="branding.logoUrl"
                  type="button"
                  class="btn-ghost-danger"
                  :disabled="logoBusy"
                  @click="handleLogoDelete"
                >
                  Supprimer
                </button>
              </div>
            </template>
            <p v-else class="read-only-notice">
              Lecture seule — seul un administrateur peut modifier le logo du cabinet.
            </p>

            <!-- Contraintes servies par l'API : jamais recopiées en dur dans l'interface. -->
            <ul v-if="contraintes" class="logo-rules">
              <li>Formats acceptés : {{ formatsLisibles }}</li>
              <li>Poids maximum : {{ tailleMaxLisible }}</li>
              <li>
                Dimensions : de {{ contraintes.dimension_min_px }}×{{ contraintes.dimension_min_px }}
                à {{ contraintes.dimension_max_px }}×{{ contraintes.dimension_max_px }} pixels
              </li>
              <li>Rapport largeur/hauteur : {{ contraintes.ratio_max }}:1 maximum</li>
            </ul>

            <!-- Le 422 du serveur est explicite et en français : on l'affiche tel quel. -->
            <p v-if="logoMsg" class="save-msg" :class="logoMsgClass">{{ logoMsg }}</p>
          </div>
        </div>
      </div>
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

        <!-- Seuil espèces Art. 72 (Trigger T2) -->
        <div class="threshold-row">
          <label class="field-label">
            Seuil espèces Art. 72 (FCFA)
            <span class="field-hint">Trigger T2 automatique (espèces) au-dessus de ce montant</span>
          </label>
          <input
            v-model.number="seuilEspeces"
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
import { tenantService, type TenantQuota, type LogoContraintes } from '@/services/tenant'
import { TENANT_STATUT_LABELS } from '@/services/superAdmin'
import { useBrandingStore } from '@/stores/branding'
import type { TenantMe } from '@/stores/auth'

const auth = useAuthStore()
const notif = useNotificationsStore()
const branding = useBrandingStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

// ── Mon cabinet ────────────────────────────────────────────────────
const tenantMe = ref<TenantMe | null>(null)
const quota = ref<TenantQuota | null>(null)

const tenantStatut = computed(() => tenantMe.value?.statut ?? auth.tenant?.statut ?? null)
// Note : pays et n° d'agrément ne sont pas exposés par /api/tenant/me — ils restent
// visibles uniquement depuis la console d'exploitation.

const quotaRestant = computed(() => {
  const q = quota.value
  if (!q || q.quota_utilisateurs === 0) return 0
  return Math.max(0, q.quota_utilisateurs - q.utilisateurs_actifs)
})

const quotaPct = computed(() => {
  const q = quota.value
  if (!q || q.quota_utilisateurs === 0) return 0
  return Math.min(100, Math.round((q.utilisateurs_actifs / q.quota_utilisateurs) * 100))
})

const quotaClass = computed(() => {
  if (quotaPct.value >= 100) return 'quota-fill--high'
  if (quotaPct.value >= 80) return 'quota-fill--medium'
  return 'quota-fill--low'
})

async function loadTenant() {
  try {
    const me = await tenantService.me()
    tenantMe.value = me
    auth.setTenantFromMe(me)
  } catch {
    // Endpoint indisponible — on retombe sur les informations du store.
  }
  // Le quota est réservé aux rôles admin / notaire principal.
  if (auth.user?.role === 'admin' || auth.user?.role === 'notaire_principal') {
    try {
      quota.value = await tenantService.quota()
    } catch {
      quota.value = null
    }
  }
}

// ── Logo du cabinet ────────────────────────────────────────────────
// Droits alignés sur ce que l'API applique RÉELLEMENT : les routes
// PUT/DELETE /api/tenant/logo dépendent de `require_user_manager`, qui
// n'autorise que l'Administrateur (ADM-01, séparation des fonctions Art. 12).
// Le notaire principal reçoit un 403 : lui afficher les boutons reviendrait à
// promettre une action qui échoue systématiquement. Il voit donc l'aperçu seul,
// comme les autres rôles.
const peutGererLogo = computed(() => auth.user?.role === 'admin')

const contraintes = ref<LogoContraintes | null>(null)
const logoInput = ref<HTMLInputElement | null>(null)
const logoBusy = ref(false)
const logoMsg = ref('')
const logoMsgClass = ref('')

/** Filtre du sélecteur de fichiers, déduit des formats annoncés par l'API. */
const acceptLogo = computed(() => contraintes.value?.formats.join(',') ?? 'image/*')

const formatsLisibles = computed(() =>
  (contraintes.value?.formats ?? [])
    .map(f => f.replace('image/', '').toUpperCase())
    .join(', ')
)

const tailleMaxLisible = computed(() => {
  const octets = contraintes.value?.taille_max_octets
  if (!octets) return '—'
  const mo = octets / (1024 * 1024)
  return mo >= 1 ? `${Number(mo.toFixed(2))} Mo` : `${Math.round(octets / 1024)} Ko`
})

async function loadContraintes() {
  try {
    contraintes.value = await tenantService.logoContraintes()
  } catch {
    // Endpoint indisponible : le bloc de rappel est masqué plutôt que d'afficher
    // des valeurs inventées, qui pourraient contredire le serveur.
    contraintes.value = null
  }
}

async function handleLogoChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  // On vide tout de suite la sélection : renvoyer deux fois le même fichier doit
  // redéclencher l'événement `change`.
  input.value = ''
  if (!file) return

  logoBusy.value = true
  logoMsg.value = ''
  try {
    const res = await tenantService.uploadLogo(file)
    auth.setTenantLogoUpdatedAt(res.logo_updated_at)
    await branding.charger(res.logo_updated_at)
    logoMsg.value = `Logo enregistré (${res.largeur}×${res.hauteur} px).`
    logoMsgClass.value = 'msg--ok'
  } catch (err: any) {
    // Le 422 du serveur porte un message explicite en français : on le restitue.
    const detail = err?.response?.data?.detail
    logoMsg.value = typeof detail === 'string' ? detail : "Impossible d'envoyer ce logo."
    logoMsgClass.value = 'msg--err'
  } finally {
    logoBusy.value = false
  }
}

async function handleLogoDelete() {
  logoBusy.value = true
  logoMsg.value = ''
  try {
    await tenantService.deleteLogo()
    auth.setTenantLogoUpdatedAt(null)
    await branding.charger(null)
    logoMsg.value = 'Logo supprimé.'
    logoMsgClass.value = 'msg--ok'
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    logoMsg.value = typeof detail === 'string' ? detail : 'Impossible de supprimer le logo.'
    logoMsgClass.value = 'msg--err'
  } finally {
    logoBusy.value = false
  }
}

const loading = ref(true)
const saving  = ref(false)
const saveMsg = ref('')
const saveMsgClass = ref('')

const seuilEspeces = ref(15_000_000)
const weights = ref<Record<string, number>>({})

// Axes alignés sur scoring_service.AXIS_CODES (CDC v4, Module 2 — notaire)
const axes = [
  { code: 'type_client',     label: 'Type de client' },
  { code: 'pays_geographie', label: 'Pays / Géographie' },
  { code: 'type_operation',  label: "Nature de l'opération" },
  { code: 'montant',         label: 'Montant de la transaction' },
  { code: 'mode_paiement',   label: 'Mode de paiement' },
  { code: 'complexite',      label: 'Complexité juridique' },
  { code: 'ppe',             label: 'Personne Politiquement Exposée' },
  { code: 'coherence_doc',   label: 'Cohérence documentaire' },
  { code: 'secteur',         label: "Secteur d'activité" },
  { code: 'intermediaires',  label: 'Intermédiaires' },
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
    seuilEspeces.value = data.seuil_especes_t2_fcfa ?? 15_000_000
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
      seuil_especes_t2_fcfa: seuilEspeces.value,
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
  loadTenant()
  loadContraintes()
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
.info-val--mono { font-family: monospace; }
.info-muted { color: var(--color-text-muted); font-size: 0.8125rem; margin-left: 0.25rem; }

/* Mon cabinet — statut + jauge de sièges */
.badge-statut {
  flex-shrink: 0;
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  letter-spacing: 0.02em;
}
.badge-statut--production    { background: var(--color-risk-low-bg); color: var(--color-risk-low); }
.badge-statut--configuration { background: var(--color-status-en-analyse-bg); color: var(--color-status-en-analyse); }
.badge-statut--suspendu      { background: var(--color-risk-high-bg); color: var(--color-risk-high); }
.badge-statut--archive       { background: var(--color-status-cloture-bg); color: var(--color-status-cloture); }

.quota-bar {
  height: 6px;
  border-radius: 3px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  overflow: hidden;
}
.quota-fill { height: 100%; transition: width 0.2s; }

/* Mon cabinet — logo */
.logo-section { border-top: 1px solid var(--color-border); padding-top: 1.125rem; }
.sub-title { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); margin: 0; }
.sub-desc  { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0.25rem 0 0.875rem; }

.logo-row { display: flex; align-items: flex-start; gap: 1.25rem; flex-wrap: wrap; }

/* Gabarit fixe : `contain` empêche tout logo large ou haut de casser la mise en page. */
.logo-preview {
  width: 120px; height: 120px; flex-shrink: 0;
  border: 1px solid var(--color-border); border-radius: 10px;
  background: var(--color-bg-page, #f8fafc);
  display: flex; align-items: center; justify-content: center;
  padding: 0.5rem; overflow: hidden;
}
.logo-preview--vide { border-style: dashed; }
.logo-preview-img  { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
.logo-preview-vide { font-size: 0.75rem; color: var(--color-text-muted); }

.logo-actions { flex: 1; min-width: 240px; display: flex; flex-direction: column; gap: 0.75rem; }
.logo-file-input { display: none; }
.logo-buttons { display: flex; gap: 0.625rem; flex-wrap: wrap; }

.btn-ghost-danger {
  padding: 0.5625rem 1rem; background: none;
  border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.875rem; font-weight: 500; color: var(--color-risk-high);
  cursor: pointer; transition: border-color 0.12s;
}
.btn-ghost-danger:hover:not(:disabled) { border-color: var(--color-risk-high); }
.btn-ghost-danger:disabled { opacity: 0.6; cursor: not-allowed; }

.logo-rules {
  margin: 0; padding: 0.75rem 0.875rem 0.75rem 1.75rem;
  background: #f8fafc; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.75rem; color: var(--color-text-secondary); line-height: 1.7;
}
.quota-fill--low    { background: var(--color-risk-low); }
.quota-fill--medium { background: var(--color-risk-medium); }
.quota-fill--high   { background: var(--color-risk-high); }
</style>
