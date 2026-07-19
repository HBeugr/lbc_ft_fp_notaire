<template>
  <div class="detail-page">
    <div v-if="loading" class="loading-state">Chargement…</div>

    <template v-else-if="tenant">
      <!-- Header -->
      <div class="page-header">
        <div>
          <RouterLink :to="{ name: 'super-admin-tenants' }" class="back-link">← Retour aux cabinets</RouterLink>
          <h1 class="page-title">{{ tenant.nom_cabinet }}</h1>
          <p class="page-subtitle">
            <code class="slug">{{ tenant.slug }}</code>
            <span class="badge" :class="`badge--${tenant.statut}`">{{ TENANT_STATUT_LABELS[tenant.statut] }}</span>
          </p>
        </div>
        <div class="header-actions">
          <button
            v-if="tenant.statut !== 'production' && tenant.statut !== 'archive'"
            class="btn-success"
            :disabled="submitting"
            @click="handleActivate"
          >
            Activer
          </button>
          <button
            v-if="tenant.statut === 'production'"
            class="btn-ghost"
            @click="openMotif('suspend')"
          >
            Suspendre
          </button>
          <button
            v-if="tenant.statut !== 'archive'"
            class="btn-danger"
            @click="openMotif('archive')"
          >
            Archiver
          </button>
        </div>
      </div>

      <div v-if="actionError" class="alert-error">{{ actionError }}</div>

      <!-- Métriques -->
      <div class="metrics-grid">
        <div class="metric-card">
          <span class="metric-label">Utilisateurs actifs</span>
          <span class="metric-value">{{ metrics?.utilisateurs_actifs ?? '—' }}</span>
          <span class="metric-sub">sur {{ metrics?.utilisateurs_total ?? '—' }} comptes</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Quota de sièges</span>
          <span class="metric-value">{{ quotaLabel }}</span>
          <span class="metric-sub">{{ quotaSubLabel }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Dossiers</span>
          <span class="metric-value">{{ metrics?.dossiers_total ?? '—' }}</span>
          <span class="metric-sub">total enregistré</span>
        </div>
      </div>

      <!-- Informations -->
      <div class="card">
        <h2 class="card-title">Informations du cabinet</h2>
        <div class="info-grid">
          <div class="info-row">
            <span class="info-label">Nom</span>
            <span class="info-val">{{ tenant.nom_cabinet }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Identifiant</span>
            <span class="info-val info-val--mono">{{ tenant.slug }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Pays</span>
            <span class="info-val">{{ tenant.pays }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">N° d'agrément</span>
            <span class="info-val">{{ tenant.numero_agrement || '—' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Email de contact</span>
            <span class="info-val">{{ tenant.contact_email }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Téléphone</span>
            <span class="info-val">{{ tenant.contact_telephone || '—' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Adresse</span>
            <span class="info-val">{{ tenant.adresse || '—' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">2FA obligatoire</span>
            <span class="info-val">
              <span v-if="tenant.totp_required" class="badge-ok">Oui</span>
              <span v-else class="badge-off">Non</span>
            </span>
          </div>
        </div>
      </div>

      <!-- Logo du cabinet -->
      <div class="card">
        <h2 class="card-title">Logo du cabinet</h2>
        <p class="card-desc">
          Affiché dans la barre latérale des utilisateurs de ce cabinet.
        </p>

        <div class="logo-row">
          <!-- Gabarit fixe : `contain` évite qu'un logo large déforme la fiche. -->
          <div class="logo-preview" :class="{ 'logo-preview--vide': !logoUrl }">
            <img v-if="logoUrl" class="logo-preview-img" :src="logoUrl" alt="Logo du cabinet" />
            <span v-else class="logo-preview-vide">Aucun logo</span>
          </div>

          <div class="logo-actions">
            <input
              ref="logoInput"
              type="file"
              class="logo-file-input"
              :accept="acceptLogo"
              @change="handleLogoChange"
            />
            <div class="logo-buttons">
              <button type="button" class="btn-success" :disabled="logoBusy" @click="logoInput?.click()">
                <span v-if="logoBusy" class="spinner" />
                {{ logoUrl ? 'Remplacer le logo' : 'Envoyer un logo' }}
              </button>
              <button v-if="logoUrl" type="button" class="btn-ghost" :disabled="logoBusy" @click="handleLogoDelete">
                Supprimer
              </button>
            </div>

            <!-- Contraintes servies par l'API, jamais recopiées en dur. -->
            <ul v-if="contraintes" class="logo-rules">
              <li>Formats acceptés : {{ formatsLisibles }}</li>
              <li>Poids maximum : {{ tailleMaxLisible }}</li>
              <li>
                Dimensions : de {{ contraintes.dimension_min_px }}×{{ contraintes.dimension_min_px }}
                à {{ contraintes.dimension_max_px }}×{{ contraintes.dimension_max_px }} pixels
              </li>
              <li>Rapport largeur/hauteur : {{ contraintes.ratio_max }}:1 maximum</li>
            </ul>

            <!-- Message 422 du serveur, explicite et en français. -->
            <p v-if="logoMsg" class="logo-msg" :class="logoMsgClass">{{ logoMsg }}</p>
          </div>
        </div>
      </div>

      <!-- Cycle de vie -->
      <div class="card">
        <h2 class="card-title">Cycle de vie</h2>
        <div class="info-grid">
          <div class="info-row">
            <span class="info-label">Créé le</span>
            <span class="info-val">{{ formatDateTime(tenant.created_at) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Activé le</span>
            <span class="info-val">{{ formatDateTime(tenant.activated_at) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Suspendu le</span>
            <span class="info-val">{{ formatDateTime(tenant.suspended_at) }}</span>
          </div>
          <div v-if="tenant.motif_suspension" class="info-row">
            <span class="info-label">Motif</span>
            <span class="info-val">{{ tenant.motif_suspension }}</span>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="alert-error">{{ loadError || 'Cabinet introuvable.' }}</div>

    <!-- Modale motif -->
    <Teleport to="body">
      <div v-if="motifAction" class="modal-overlay" @click.self="motifAction = null">
        <div class="modal modal--sm" role="dialog">
          <div class="modal-header">
            <h2 class="modal-title">
              {{ motifAction === 'suspend' ? 'Suspendre ce cabinet ?' : 'Archiver ce cabinet ?' }}
            </h2>
          </div>
          <p class="confirm-body">
            <template v-if="motifAction === 'suspend'">
              Les utilisateurs perdront l'accès jusqu'à réactivation. Les données sont conservées.
            </template>
            <template v-else>
              L'accès est retiré définitivement ; les données restent conservées 10 ans (Art. 23).
            </template>
          </p>
          <div class="motif-field">
            <label class="field-label">Motif <span class="field-hint">(facultatif)</span></label>
            <textarea v-model="motif" rows="3" class="field-input" placeholder="Motif communiqué au cabinet…" />
          </div>
          <div class="modal-actions" style="padding:0 1.5rem 1.5rem;">
            <button class="btn-ghost-modal" @click="motifAction = null">Annuler</button>
            <button class="btn-danger" :disabled="submitting" @click="handleMotifConfirm">
              <span v-if="submitting" class="spinner" />
              {{ motifAction === 'suspend' ? 'Suspendre' : 'Archiver' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  superAdminService,
  TENANT_STATUT_LABELS,
  type TenantOut,
  type TenantMetrics,
  type LogoContraintes,
} from '@/services/superAdmin'
import { useObjectUrl } from '@/composables/useObjectUrl'

const route = useRoute()
const tenantId = String(route.params.id)

const tenant = ref<TenantOut | null>(null)
const metrics = ref<TenantMetrics | null>(null)
const loading = ref(true)
const loadError = ref('')
const actionError = ref('')
const submitting = ref(false)

const motifAction = ref<'suspend' | 'archive' | null>(null)
const motif = ref('')

const quotaLabel = computed(() => {
  const q = metrics.value?.quota_utilisateurs
  if (q === undefined) return '—'
  return q === 0 ? 'Illimité' : String(q)
})

const quotaSubLabel = computed(() => {
  const m = metrics.value
  if (!m) return ''
  if (m.quota_utilisateurs === 0) return `${m.utilisateurs_actifs} siège(s) consommé(s)`
  return `${m.utilisateurs_actifs} / ${m.quota_utilisateurs} consommé(s)`
})

// ── Logo du cabinet ──────────────────────────────────────────────────
// L'endpoint exige l'en-tête `Authorization` de la console : l'image passe par
// l'instance axios dédiée puis par une URL d'objet, jamais par `<img src="/api…">`.
const { url: logoUrl, set: setLogoUrl } = useObjectUrl()
const contraintes = ref<LogoContraintes | null>(null)
const logoInput = ref<HTMLInputElement | null>(null)
const logoBusy = ref(false)
const logoMsg = ref('')
const logoMsgClass = ref('')

const acceptLogo = computed(() => contraintes.value?.formats.join(',') ?? 'image/*')

const formatsLisibles = computed(() =>
  (contraintes.value?.formats ?? []).map(f => f.replace('image/', '').toUpperCase()).join(', ')
)

const tailleMaxLisible = computed(() => {
  const octets = contraintes.value?.taille_max_octets
  if (!octets) return '—'
  const mo = octets / (1024 * 1024)
  return mo >= 1 ? `${Number(mo.toFixed(2))} Mo` : `${Math.round(octets / 1024)} Ko`
})

/**
 * Charge l'aperçu. `version` (horodatage) sert de « cache-buster » ; à `null`,
 * aucune requête n'est émise — le cabinet n'a pas de logo.
 */
async function chargerLogo(version: string | null) {
  if (!version) { setLogoUrl(null); return }
  try {
    setLogoUrl(await superAdminService.logoBlob(tenantId, version))
  } catch {
    setLogoUrl(null)
  }
}

async function chargerContraintes() {
  try {
    contraintes.value = await superAdminService.logoContraintes()
  } catch {
    contraintes.value = null
  }
}

async function handleLogoChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  // Réinitialisé aussitôt pour que le même fichier puisse être renvoyé.
  input.value = ''
  if (!file) return

  logoBusy.value = true
  logoMsg.value = ''
  try {
    const res = await superAdminService.uploadLogo(tenantId, file)
    if (tenant.value) tenant.value = { ...tenant.value, logo_updated_at: res.logo_updated_at }
    await chargerLogo(res.logo_updated_at)
    logoMsg.value = `Logo enregistré (${res.largeur}×${res.hauteur} px).`
    logoMsgClass.value = 'logo-msg--ok'
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    logoMsg.value = typeof detail === 'string' ? detail : "Impossible d'envoyer ce logo."
    logoMsgClass.value = 'logo-msg--err'
  } finally {
    logoBusy.value = false
  }
}

async function handleLogoDelete() {
  logoBusy.value = true
  logoMsg.value = ''
  try {
    await superAdminService.deleteLogo(tenantId)
    if (tenant.value) tenant.value = { ...tenant.value, logo_updated_at: null }
    setLogoUrl(null)
    logoMsg.value = 'Logo supprimé.'
    logoMsgClass.value = 'logo-msg--ok'
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    logoMsg.value = typeof detail === 'string' ? detail : 'Impossible de supprimer le logo.'
    logoMsgClass.value = 'logo-msg--err'
  } finally {
    logoBusy.value = false
  }
}

function formatDateTime(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    // Les métriques sont accessoires : leur échec ne doit pas masquer la fiche.
    const [t, m] = await Promise.all([
      superAdminService.getTenant(tenantId),
      superAdminService.tenantMetrics(tenantId).catch(() => null),
    ])
    tenant.value = t
    metrics.value = m
    await chargerLogo(t.logo_updated_at)
  } catch (err: any) {
    loadError.value = err?.response?.data?.detail ?? 'Impossible de charger ce cabinet.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  chargerContraintes()
})

async function handleActivate() {
  submitting.value = true
  actionError.value = ''
  try {
    tenant.value = await superAdminService.activateTenant(tenantId)
  } catch (err: any) {
    actionError.value = err?.response?.data?.detail ?? "Erreur lors de l'activation."
  } finally {
    submitting.value = false
  }
}

function openMotif(action: 'suspend' | 'archive') {
  motifAction.value = action
  motif.value = ''
  actionError.value = ''
}

async function handleMotifConfirm() {
  if (!motifAction.value) return
  submitting.value = true
  try {
    const m = motif.value.trim() || undefined
    tenant.value = motifAction.value === 'suspend'
      ? await superAdminService.suspendTenant(tenantId, m)
      : await superAdminService.archiveTenant(tenantId, m)
    motifAction.value = null
  } catch (err: any) {
    actionError.value = err?.response?.data?.detail ?? 'Une erreur est survenue.'
    motifAction.value = null
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.detail-page { max-width: 900px; display: flex; flex-direction: column; gap: 1.25rem; }
.loading-state { color: var(--color-text-secondary); font-size: 0.875rem; padding: 2rem 0; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
.back-link { font-size: 0.8125rem; color: var(--color-text-secondary); text-decoration: none; }
.back-link:hover { color: var(--color-text-primary); }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0.5rem 0 0.375rem; }
.page-subtitle { display: flex; align-items: center; gap: 0.625rem; margin: 0; }
.slug { font-family: monospace; font-size: 0.8125rem; color: var(--color-text-secondary); }

.header-actions { display: flex; gap: 0.5rem; flex-shrink: 0; }

.badge { border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.badge--production { color: var(--color-risk-low); background: var(--color-risk-low-bg); }
.badge--configuration { color: var(--color-status-en-analyse); background: var(--color-status-en-analyse-bg); }
.badge--suspendu { color: var(--color-risk-high); background: var(--color-risk-high-bg); }
.badge--archive { color: var(--color-status-cloture); background: var(--color-status-cloture-bg); }
.badge-ok { color: var(--color-risk-low); background: var(--color-risk-low-bg); border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.badge-off { color: var(--color-text-muted); background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; }

.metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.875rem; }
.metric-card {
  background: var(--color-bg-card); border: 1px solid var(--color-border);
  border-radius: 12px; padding: 1.125rem 1.25rem;
  display: flex; flex-direction: column; gap: 0.25rem;
}
.metric-label { font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
.metric-value { font-size: 1.5rem; font-weight: 700; color: var(--color-text-primary); line-height: 1.2; }
.metric-sub { font-size: 0.75rem; color: var(--color-text-muted); }

.card {
  background: var(--color-bg-card); border: 1px solid var(--color-border);
  border-radius: 12px; padding: 1.25rem 1.5rem;
  display: flex; flex-direction: column; gap: 1rem;
}
.card-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.card-desc  { font-size: 0.8125rem; color: var(--color-text-secondary); margin: -0.5rem 0 0; }
.info-grid { display: flex; flex-direction: column; gap: 0.5rem; }
.info-row { display: flex; gap: 1rem; font-size: 0.875rem; align-items: baseline; }
.info-label { min-width: 160px; color: var(--color-text-secondary); font-weight: 500; flex-shrink: 0; }
.info-val { color: var(--color-text-primary); }
.info-val--mono { font-family: monospace; }

.alert-error {
  background: var(--color-risk-high-bg); color: var(--color-risk-high);
  border-radius: 7px; padding: 0.625rem 0.875rem; font-size: 0.8125rem;
}

.btn-ghost {
  padding: 0.5rem 1rem; background: none; border: 1px solid var(--color-border);
  border-radius: 7px; font-size: 0.875rem; color: var(--color-text-secondary);
  cursor: pointer; transition: border-color 0.12s;
}
.btn-ghost:hover { border-color: var(--color-text-secondary); }
.btn-ghost:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-success {
  padding: 0.5rem 1.25rem; background: var(--color-risk-low); color: #fff;
  border: none; border-radius: 7px; font-size: 0.875rem; font-weight: 600; cursor: pointer;
}
.btn-success:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-danger {
  padding: 0.5rem 1.25rem; background: var(--color-risk-high); color: #fff;
  border: none; border-radius: 7px; font-size: 0.875rem; font-weight: 600;
  cursor: pointer; display: inline-flex; align-items: center; gap: 0.4rem;
}
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 1.5rem;
}
.modal {
  background: var(--color-bg-card); border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.16);
  width: 100%; max-width: 520px; max-height: 90vh; overflow-y: auto;
}
.modal--sm { max-width: 420px; }
.modal-header { padding: 1.25rem 1.5rem 0; }
.modal-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.confirm-body { padding: 0.75rem 1.5rem; font-size: 0.875rem; color: var(--color-text-secondary); line-height: 1.6; margin: 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.625rem; }
.motif-field { padding: 0 1.5rem 1rem; display: flex; flex-direction: column; gap: 0.3rem; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.field-hint { font-size: 0.75rem; color: var(--color-text-muted); font-weight: 400; margin-left: 0.25rem; }
.field-input {
  padding: 0.5625rem 0.75rem; border: 1px solid var(--color-border); border-radius: 7px;
  font-size: 0.875rem; color: var(--color-text-primary); background: #fff; outline: none;
  width: 100%; font-family: inherit; resize: vertical;
}
.field-input:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.btn-ghost-modal {
  padding: 0.5rem 1rem; background: none; border: 1px solid var(--color-border);
  border-radius: 7px; font-size: 0.875rem; color: var(--color-text-secondary); cursor: pointer;
}
.btn-ghost-modal:hover { border-color: var(--color-text-secondary); }

.spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Logo du cabinet ── */
.logo-row { display: flex; align-items: flex-start; gap: 1.25rem; flex-wrap: wrap; }
.logo-preview {
  width: 120px; height: 120px; flex-shrink: 0;
  border: 1px solid var(--color-border); border-radius: 10px;
  background: var(--color-bg-page); display: flex;
  align-items: center; justify-content: center; padding: 0.5rem; overflow: hidden;
}
.logo-preview--vide { border-style: dashed; }
.logo-preview-img  { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
.logo-preview-vide { font-size: 0.75rem; color: var(--color-text-muted); }
.logo-actions { flex: 1; min-width: 240px; display: flex; flex-direction: column; gap: 0.75rem; }
.logo-file-input { display: none; }
.logo-buttons { display: flex; gap: 0.625rem; flex-wrap: wrap; }
.logo-rules {
  margin: 0; padding: 0.75rem 0.875rem 0.75rem 1.75rem;
  background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.75rem; color: var(--color-text-secondary); line-height: 1.7;
}
.logo-msg { font-size: 0.8125rem; margin: 0; }
.logo-msg--ok  { color: var(--color-risk-low); }
.logo-msg--err { color: var(--color-risk-high); }

@media (max-width: 768px) {
  .metrics-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; }
}
</style>
