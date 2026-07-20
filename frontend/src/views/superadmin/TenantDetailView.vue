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
        <div class="card-head">
          <h2 class="card-title">Informations du cabinet</h2>
          <button v-if="!editing" class="btn-ghost btn-ghost--sm" @click="startEdit">Modifier</button>
        </div>

        <!-- Lecture -->
        <div v-if="!editing" class="info-grid">
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
            <span class="info-label">Quota de sièges</span>
            <span class="info-val">{{ tenant.max_users === 0 ? 'Illimité' : tenant.max_users }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">2FA obligatoire</span>
            <span class="info-val">
              <span v-if="tenant.totp_required" class="badge-ok">Oui</span>
              <span v-else class="badge-off">Non</span>
            </span>
          </div>
        </div>

        <!-- Édition. `slug` reste en lecture seule : il nomme le schéma
             PostgreSQL du cabinet, le changer casserait le routage. -->
        <form v-else class="edit-form" @submit.prevent="submitEdit">
          <div class="edit-grid">
            <div class="edit-field">
              <label for="e-nom" class="edit-label">Nom du cabinet</label>
              <input id="e-nom" v-model="form.nom_cabinet" type="text" class="edit-input" :disabled="saving" />
            </div>
            <div class="edit-field">
              <label for="e-slug" class="edit-label">Identifiant</label>
              <input id="e-slug" :value="tenant.slug" type="text" class="edit-input edit-input--locked" disabled />
              <p class="edit-hint">Figé : il nomme le schéma de base de données du cabinet.</p>
            </div>
            <div class="edit-field">
              <label for="e-pays" class="edit-label">Pays</label>
              <input id="e-pays" v-model="form.pays" type="text" maxlength="2" class="edit-input" :disabled="saving" />
            </div>
            <div class="edit-field">
              <label for="e-agrement" class="edit-label">N° d'agrément</label>
              <input id="e-agrement" v-model="form.numero_agrement" type="text" class="edit-input" :disabled="saving" />
            </div>
            <div class="edit-field">
              <label for="e-email" class="edit-label">Email de contact</label>
              <input id="e-email" v-model="form.contact_email" type="email" class="edit-input" :disabled="saving" />
            </div>
            <div class="edit-field">
              <label for="e-tel" class="edit-label">Téléphone</label>
              <input id="e-tel" v-model="form.contact_telephone" type="text" class="edit-input" :disabled="saving" />
            </div>
            <div class="edit-field edit-field--wide">
              <label for="e-adresse" class="edit-label">Adresse</label>
              <input id="e-adresse" v-model="form.adresse" type="text" class="edit-input" :disabled="saving" />
            </div>
            <div class="edit-field">
              <label for="e-quota" class="edit-label">Quota de sièges</label>
              <input id="e-quota" v-model.number="form.max_users" type="number" min="0" class="edit-input" :disabled="saving" />
              <p class="edit-hint">0 = illimité.</p>
            </div>
            <div class="edit-field">
              <span class="edit-label">2FA obligatoire</span>
              <label class="edit-check">
                <input v-model="form.totp_required" type="checkbox" :disabled="saving" />
                <span>Imposer la double authentification aux rôles sensibles</span>
              </label>
            </div>
          </div>

          <p v-if="editError" class="alert-error alert-error--inline">{{ editError }}</p>

          <div class="edit-actions">
            <button type="button" class="btn-ghost" :disabled="saving" @click="cancelEdit">Annuler</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              <span v-if="saving" class="spinner" />
              {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
            </button>
          </div>
        </form>
      </div>

      <!-- Accès administrateur du cabinet -->
      <div class="card">
        <h2 class="card-title">Accès administrateur</h2>
        <p class="card-desc">
          Réémet un mot de passe temporaire pour le compte administrateur de ce cabinet. Seul recours
          quand le mot de passe remis à la création a été perdu — sans lui, personne à l'intérieur du
          cabinet ne peut ouvrir de session pour réparer.
        </p>
        <p class="card-desc card-desc--warn">
          La double authentification de ce compte est également remise à zéro : rien ne permet de
          vérifier que le téléphone associé est toujours entre les mêmes mains. Les comptes métier
          (notaire, conformité, clercs) ne sont pas touchés — ils relèvent de l'admin du cabinet.
        </p>

        <div v-if="resetResult" class="reset-result">
          <p class="reset-title">Nouveau mot de passe temporaire</p>
          <div class="reset-row">
            <span class="reset-label">Compte</span>
            <code class="reset-value">{{ resetResult.admin_email }}</code>
          </div>
          <div class="reset-row">
            <span class="reset-label">Mot de passe</span>
            <code class="reset-value reset-value--secret">{{ resetResult.admin_temp_password }}</code>
          </div>
          <p class="reset-warn">
            Transmettez-le par un canal sûr et notez-le maintenant : il n'est stocké nulle part et ne
            sera plus jamais affiché.
          </p>
          <div class="edit-actions">
            <button class="btn-ghost" @click="copyResetPassword">{{ copyLabel }}</button>
            <button class="btn-primary" @click="resetResult = null">J'ai noté</button>
          </div>
        </div>

        <button v-else class="btn-ghost" :disabled="resetting" @click="confirmReset = true">
          <span v-if="resetting" class="spinner spinner--dark" />
          Réinitialiser le mot de passe administrateur
        </button>

        <p v-if="resetError" class="alert-error alert-error--inline">{{ resetError }}</p>
      </div>

      <!-- Confirmation du reset : action irréversible pour le mot de passe en cours. -->
      <div v-if="confirmReset" class="modal-overlay" @click.self="confirmReset = false">
        <div class="modal modal--sm" role="dialog" aria-modal="true">
          <div class="modal-header">
            <h2 class="modal-title">Réinitialiser l'accès administrateur ?</h2>
          </div>
          <p class="confirm-body">
            Le mot de passe actuel de l'administrateur de <strong>{{ tenant.nom_cabinet }}</strong>
            cessera immédiatement de fonctionner, et sa double authentification sera désactivée.
            L'action est journalisée.
          </p>
          <div class="modal-actions" style="padding:0 1.5rem 1.5rem;">
            <button class="btn-ghost-modal" @click="confirmReset = false">Annuler</button>
            <button class="btn-danger" :disabled="resetting" @click="handleReset">
              <span v-if="resetting" class="spinner" />
              Réinitialiser
            </button>
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
import { ref, computed, onMounted, reactive } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  superAdminService,
  TENANT_STATUT_LABELS,
  type TenantOut,
  type TenantMetrics,
  type TenantAdminReset,
  type TenantUpdatePayload,
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

// ── Édition des informations ─────────────────────────────────────────
const editing = ref(false)
const saving = ref(false)
const editError = ref('')
const form = reactive({
  nom_cabinet: '',
  contact_email: '',
  contact_telephone: '',
  adresse: '',
  numero_agrement: '',
  pays: '',
  totp_required: false,
  max_users: 0,
})

function startEdit() {
  if (!tenant.value) return
  editError.value = ''
  // Les champs nuls deviennent des chaînes vides : un `null` dans un `<input>`
  // afficherait littéralement « null ».
  form.nom_cabinet = tenant.value.nom_cabinet
  form.contact_email = tenant.value.contact_email
  form.contact_telephone = tenant.value.contact_telephone ?? ''
  form.adresse = tenant.value.adresse ?? ''
  form.numero_agrement = tenant.value.numero_agrement ?? ''
  form.pays = tenant.value.pays
  form.totp_required = tenant.value.totp_required
  form.max_users = tenant.value.max_users
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  editError.value = ''
}

/** Chaîne vide → `null` : l'API distingue « champ vidé » de « champ absent ». */
function ouNull(valeur: string): string | null {
  const v = valeur.trim()
  return v === '' ? null : v
}

async function submitEdit() {
  if (!tenant.value) return
  editError.value = ''

  if (!form.nom_cabinet.trim() || form.nom_cabinet.trim().length < 2) {
    editError.value = 'Le nom du cabinet est requis (2 caractères minimum).'
    return
  }
  if (!form.contact_email.trim()) {
    editError.value = "L'email de contact est requis."
    return
  }
  if (form.pays.trim().length !== 2) {
    editError.value = 'Le pays doit être un code à 2 lettres (ex. CI).'
    return
  }

  // PATCH partiel : on ne transmet que les champs réellement modifiés. Envoyer
  // le formulaire entier reviendrait à faire revalider par l'API des valeurs
  // que l'utilisateur n'a pas touchées — un cabinet dont l'email de contact est
  // hérité d'un import ou d'un seed (domaine `.local`, par exemple) deviendrait
  // alors impossible à modifier, même pour changer son seul numéro de téléphone.
  const actuel = tenant.value
  const payload: TenantUpdatePayload = {}

  const nom = form.nom_cabinet.trim()
  if (nom !== actuel.nom_cabinet) payload.nom_cabinet = nom

  const email = form.contact_email.trim()
  if (email !== actuel.contact_email) payload.contact_email = email

  const pays = form.pays.trim().toUpperCase()
  if (pays !== actuel.pays) payload.pays = pays

  const tel = ouNull(form.contact_telephone)
  if (tel !== actuel.contact_telephone) payload.contact_telephone = tel

  const adresse = ouNull(form.adresse)
  if (adresse !== actuel.adresse) payload.adresse = adresse

  const agrement = ouNull(form.numero_agrement)
  if (agrement !== actuel.numero_agrement) payload.numero_agrement = agrement

  if (form.totp_required !== actuel.totp_required) payload.totp_required = form.totp_required

  const quota = Number(form.max_users) || 0
  if (quota !== actuel.max_users) payload.max_users = quota

  // Rien à envoyer : l'API refuse une modification vide, autant fermer.
  if (Object.keys(payload).length === 0) {
    editing.value = false
    return
  }

  saving.value = true
  try {
    tenant.value = await superAdminService.updateTenant(tenantId, payload)
    editing.value = false
  } catch (err: any) {
    editError.value = messageDe(err, "L'enregistrement a échoué.")
  } finally {
    saving.value = false
  }
}

// ── Réinitialisation de l'accès administrateur ───────────────────────
const confirmReset = ref(false)
const resetting = ref(false)
const resetError = ref('')
const resetResult = ref<TenantAdminReset | null>(null)
const copyLabel = ref('Copier le mot de passe')

async function handleReset() {
  resetError.value = ''
  resetting.value = true
  try {
    resetResult.value = await superAdminService.resetTenantAdminPassword(tenantId)
    confirmReset.value = false
  } catch (err: any) {
    resetError.value = messageDe(err, 'La réinitialisation a échoué.')
    confirmReset.value = false
  } finally {
    resetting.value = false
  }
}

async function copyResetPassword() {
  if (!resetResult.value) return
  try {
    await navigator.clipboard.writeText(resetResult.value.admin_temp_password)
    copyLabel.value = 'Copié'
  } catch {
    copyLabel.value = 'Copie impossible'
  }
  window.setTimeout(() => (copyLabel.value = 'Copier le mot de passe'), 2000)
}

/** Aplatit les trois formes d'erreur FastAPI en une phrase lisible. */
function messageDe(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item: any) => {
        const champ = Array.isArray(item?.loc) ? item.loc.slice(1).join('.') : ''
        const msg = (item?.msg ?? '').replace(/^Value error,\s*/, '')
        return champ ? `${champ} : ${msg}` : msg
      })
      .filter(Boolean)
      .join(' · ')
  }
  if (!err?.response) return 'Serveur injoignable. Vérifiez votre connexion.'
  return fallback
}

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
.spinner--dark { border-color: var(--color-border); border-top-color: var(--color-text-secondary); }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Édition des informations ── */
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.card-head .card-title { margin-bottom: 1rem; }
.btn-ghost--sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
.card-desc--warn { color: var(--color-risk-medium); }

.btn-primary {
  display: inline-flex; align-items: center; gap: 0.4375rem;
  padding: 0.5rem 1rem; background: var(--color-btn-primary); color: #fff;
  border: 1px solid transparent; border-radius: 7px;
  font-size: 0.875rem; font-weight: 600; cursor: pointer;
}
.btn-primary:hover:not(:disabled) { background: var(--color-btn-primary-hover); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.edit-form { display: flex; flex-direction: column; gap: 1.25rem; }
.edit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}
.edit-field { display: flex; flex-direction: column; gap: 0.3125rem; }
.edit-field--wide { grid-column: 1 / -1; }
.edit-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.edit-input {
  padding: 0.5rem 0.6875rem; border: 1px solid var(--color-border); border-radius: 7px;
  font-size: 0.875rem; color: var(--color-text-primary); background: #fff;
  outline: none; font-family: inherit; width: 100%;
}
.edit-input:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.edit-input--locked { background: var(--color-bg-page); color: var(--color-text-muted); cursor: not-allowed; }
.edit-input:disabled { opacity: 0.65; }
.edit-hint { font-size: 0.6875rem; color: var(--color-text-muted); margin: 0; line-height: 1.45; }
.edit-check {
  display: flex; align-items: flex-start; gap: 0.5rem;
  font-size: 0.8125rem; color: var(--color-text-secondary); line-height: 1.45;
}
.edit-check input { margin-top: 2px; flex-shrink: 0; }
.edit-actions { display: flex; justify-content: flex-end; gap: 0.625rem; align-items: center; }
.alert-error--inline { margin: 0; }

/* ── Réinitialisation de l'accès administrateur ── */
.reset-result {
  border: 1px solid var(--color-accent-gold);
  border-radius: 8px;
  padding: 1rem 1.125rem;
  background: rgba(201, 162, 39, 0.05);
  display: flex; flex-direction: column; gap: 0.625rem;
}
.reset-title { font-size: 0.8125rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.reset-row { display: flex; align-items: baseline; gap: 0.75rem; flex-wrap: wrap; }
.reset-label {
  font-size: 0.75rem; color: var(--color-text-muted);
  min-width: 96px; flex-shrink: 0;
}
.reset-value {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8125rem; color: var(--color-text-primary);
  background: #fff; border: 1px solid var(--color-border);
  border-radius: 5px; padding: 0.25rem 0.5rem; word-break: break-all;
}
.reset-value--secret { font-weight: 700; letter-spacing: 0.02em; }
.reset-warn {
  font-size: 0.75rem; color: var(--color-risk-medium);
  margin: 0; line-height: 1.5;
}

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
