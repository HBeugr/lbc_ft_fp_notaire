<template>
  <div class="account-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Mon compte</h1>
        <p class="page-subtitle">{{ store.superAdmin?.email }}</p>
      </div>
    </div>

    <!-- Verrou : tant que le mot de passe initial est en place, le garde de
         route ramène ici depuis n'importe quelle autre page de la console. -->
    <div v-if="store.mustChangePassword" class="alert-warning">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <span>
        Ce compte utilise encore son mot de passe initial, connu de toute personne ayant accès à la
        configuration de déploiement. Le reste de la console reste fermé tant qu'il n'est pas changé.
      </span>
    </div>

    <!-- ── Mot de passe ─────────────────────────────────────────────── -->
    <div class="card">
      <h2 class="card-title">Mot de passe</h2>

      <form class="form" @submit.prevent="submitPassword">
        <div class="field">
          <label for="current" class="label">Mot de passe actuel</label>
          <input
            id="current"
            v-model="pwd.current"
            type="password"
            class="input"
            autocomplete="current-password"
            :disabled="pwdLoading"
          />
        </div>

        <div class="field">
          <label for="next" class="label">Nouveau mot de passe</label>
          <input
            id="next"
            v-model="pwd.next"
            type="password"
            class="input"
            autocomplete="new-password"
            :disabled="pwdLoading"
          />
          <p class="hint">12 caractères minimum, avec majuscule, minuscule, chiffre et caractère spécial.</p>
        </div>

        <div class="field">
          <label for="confirm" class="label">Confirmer le nouveau mot de passe</label>
          <input
            id="confirm"
            v-model="pwd.confirm"
            type="password"
            class="input"
            autocomplete="new-password"
            :disabled="pwdLoading"
          />
        </div>

        <p v-if="pwdError" class="alert-error">{{ pwdError }}</p>
        <p v-if="pwdSuccess" class="alert-success">{{ pwdSuccess }}</p>

        <div class="form-actions">
          <button type="submit" class="btn-primary" :disabled="pwdLoading">
            <span v-if="pwdLoading" class="spinner" />
            {{ pwdLoading ? 'Enregistrement…' : 'Changer le mot de passe' }}
          </button>
        </div>
      </form>
    </div>

    <!-- ── Double authentification ──────────────────────────────────── -->
    <div class="card">
      <div class="card-head">
        <h2 class="card-title">Double authentification</h2>
        <span class="badge" :class="store.totpEnabled ? 'badge--on' : 'badge--off'">
          {{ store.totpEnabled ? 'Activée' : 'Désactivée' }}
        </span>
      </div>

      <p class="card-intro">
        Ce compte administre l'ensemble des cabinets. Il n'existe aucun compte au-dessus de lui :
        personne ne peut le déverrouiller à sa place, d'où les codes de secours remis à l'activation.
      </p>

      <!-- Activée : seule la désactivation reste possible, code à l'appui. -->
      <template v-if="store.totpEnabled">
        <form class="form form--inline" @submit.prevent="submitDisable">
          <div class="field field--code">
            <label for="disable-code" class="label">Code de votre application</label>
            <input
              id="disable-code"
              v-model="disableCode"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              maxlength="6"
              class="input input--code"
              placeholder="000000"
              :disabled="totpLoading"
            />
            <p class="hint">Exigé même en session ouverte : un poste laissé sans surveillance ne doit pas suffire à retirer la protection.</p>
          </div>
          <button type="submit" class="btn-danger" :disabled="totpLoading">
            <span v-if="totpLoading" class="spinner" />
            Désactiver
          </button>
        </form>
      </template>

      <!-- Étape 1 : rien n'est encore engagé -->
      <template v-else-if="!setupUri">
        <button class="btn-primary" :disabled="totpLoading" @click="startSetup">
          <span v-if="totpLoading" class="spinner" />
          Activer la double authentification
        </button>
      </template>

      <!-- Étape 2 : scan + confirmation par un code -->
      <template v-else>
        <div class="setup">
          <div class="setup-qr">
            <canvas ref="qrCanvas" class="qr" aria-label="QR code de configuration" />
          </div>
          <div class="setup-body">
            <p class="setup-step">
              1. Scannez ce QR code avec votre application d'authentification
              (Google Authenticator, Authy, 1Password…).
            </p>
            <details class="setup-manual">
              <summary>Impossible de scanner ?</summary>
              <p class="hint">Saisissez cette clé manuellement dans votre application :</p>
              <code class="secret">{{ manualSecret }}</code>
            </details>

            <form class="form" @submit.prevent="submitActivate">
              <div class="field field--code">
                <label for="activate-code" class="label">2. Saisissez le code affiché</label>
                <input
                  id="activate-code"
                  v-model="activateCode"
                  type="text"
                  inputmode="numeric"
                  autocomplete="one-time-code"
                  maxlength="6"
                  class="input input--code"
                  placeholder="000000"
                  :disabled="totpLoading"
                />
              </div>
              <div class="form-actions">
                <button type="button" class="btn-ghost" :disabled="totpLoading" @click="cancelSetup">
                  Annuler
                </button>
                <button type="submit" class="btn-primary" :disabled="totpLoading">
                  <span v-if="totpLoading" class="spinner" />
                  Confirmer l'activation
                </button>
              </div>
            </form>
          </div>
        </div>
      </template>

      <p v-if="totpError" class="alert-error">{{ totpError }}</p>
      <p v-if="totpSuccess" class="alert-success">{{ totpSuccess }}</p>
    </div>

    <!-- Codes de secours — affichés une seule fois, à l'activation. -->
    <div v-if="backupCodes.length" class="card card--codes">
      <h2 class="card-title">Codes de secours</h2>
      <p class="card-intro card-intro--strong">
        Conservez-les hors de ce navigateur. Ils ne seront plus jamais affichés, et sans eux la perte
        de votre téléphone rendrait la console définitivement inaccessible.
      </p>
      <ul class="codes">
        <li v-for="code in backupCodes" :key="code" class="code">{{ code }}</li>
      </ul>
      <div class="form-actions">
        <button class="btn-ghost" @click="copyCodes">{{ copyLabel }}</button>
        <button class="btn-primary" @click="backupCodes = []">J'ai conservé ces codes</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref } from 'vue'
import QRCode from 'qrcode'
import { useSuperAdminStore } from '@/stores/superAdmin'
import { superAdminService } from '@/services/superAdmin'

const store = useSuperAdminStore()

// ── Mot de passe ──────────────────────────────────────────────────────
const pwd = reactive({ current: '', next: '', confirm: '' })
const pwdLoading = ref(false)
const pwdError = ref('')
const pwdSuccess = ref('')

async function submitPassword() {
  pwdError.value = ''
  pwdSuccess.value = ''

  if (!pwd.current || !pwd.next) {
    pwdError.value = 'Renseignez le mot de passe actuel et le nouveau.'
    return
  }
  if (pwd.next !== pwd.confirm) {
    pwdError.value = 'La confirmation ne correspond pas au nouveau mot de passe.'
    return
  }
  if (pwd.next === pwd.current) {
    pwdError.value = 'Le nouveau mot de passe doit être différent de l’actuel.'
    return
  }

  pwdLoading.value = true
  try {
    const updated = await superAdminService.changePassword(pwd.current, pwd.next)
    // Met `must_change_password` à false côté client : c'est ce qui relâche le
    // garde de route et rouvre le reste de la console.
    store.setSuperAdmin(updated)
    pwd.current = ''
    pwd.next = ''
    pwd.confirm = ''
    pwdSuccess.value = 'Mot de passe modifié.'
  } catch (err: any) {
    pwdError.value = messageDe(err, 'Le changement de mot de passe a échoué.')
  } finally {
    pwdLoading.value = false
  }
}

// ── 2FA ───────────────────────────────────────────────────────────────
const setupUri = ref('')
const manualSecret = ref('')
const activateCode = ref('')
const disableCode = ref('')
const backupCodes = ref<string[]>([])
const totpLoading = ref(false)
const totpError = ref('')
const totpSuccess = ref('')
const qrCanvas = ref<HTMLCanvasElement | null>(null)
const copyLabel = ref('Copier les codes')

/** Extrait le secret de l'URI otpauth pour la saisie manuelle. */
function secretDepuisUri(uri: string): string {
  try {
    return new URL(uri).searchParams.get('secret') ?? ''
  } catch {
    return ''
  }
}

async function startSetup() {
  totpError.value = ''
  totpSuccess.value = ''
  totpLoading.value = true
  try {
    const { provisioning_uri } = await superAdminService.totpSetup()
    setupUri.value = provisioning_uri
    manualSecret.value = secretDepuisUri(provisioning_uri)
    // Le canvas n'existe qu'une fois `setupUri` rendu.
    await nextTick()
    if (qrCanvas.value) {
      await QRCode.toCanvas(qrCanvas.value, provisioning_uri, { width: 176, margin: 1 })
    }
  } catch (err: any) {
    totpError.value = messageDe(err, "L'initialisation de la double authentification a échoué.")
  } finally {
    totpLoading.value = false
  }
}

function cancelSetup() {
  setupUri.value = ''
  manualSecret.value = ''
  activateCode.value = ''
  totpError.value = ''
}

async function submitActivate() {
  totpError.value = ''
  if (!/^\d{6}$/.test(activateCode.value)) {
    totpError.value = 'Le code doit comporter 6 chiffres.'
    return
  }
  totpLoading.value = true
  try {
    const { backup_codes } = await superAdminService.totpActivate(activateCode.value)
    backupCodes.value = backup_codes
    cancelSetup()
    // Recharge le profil : `totp_enabled` pilote l'affichage de cette section
    // et la bannière du layout.
    store.setSuperAdmin(await superAdminService.me())
    totpSuccess.value = 'Double authentification activée.'
  } catch (err: any) {
    totpError.value = messageDe(err, "L'activation a échoué.")
  } finally {
    totpLoading.value = false
  }
}

async function submitDisable() {
  totpError.value = ''
  totpSuccess.value = ''
  if (!/^\d{6}$/.test(disableCode.value)) {
    totpError.value = 'Le code doit comporter 6 chiffres.'
    return
  }
  totpLoading.value = true
  try {
    const updated = await superAdminService.totpDisable(disableCode.value)
    store.setSuperAdmin(updated)
    disableCode.value = ''
    totpSuccess.value = 'Double authentification désactivée.'
  } catch (err: any) {
    totpError.value = messageDe(err, 'La désactivation a échoué.')
  } finally {
    totpLoading.value = false
  }
}

async function copyCodes() {
  try {
    await navigator.clipboard.writeText(backupCodes.value.join('\n'))
    copyLabel.value = 'Copié'
    window.setTimeout(() => (copyLabel.value = 'Copier les codes'), 2000)
  } catch {
    copyLabel.value = 'Copie impossible'
    window.setTimeout(() => (copyLabel.value = 'Copier les codes'), 2000)
  }
}

/** Aplatit les trois formes d'erreur FastAPI en une phrase lisible. */
function messageDe(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item: any) => (item?.msg ?? '').replace(/^Value error,\s*/, ''))
      .filter(Boolean)
      .join(' · ')
  }
  if (!err?.response) return 'Serveur injoignable. Vérifiez votre connexion.'
  return fallback
}
</script>

<style scoped>
.account-page { max-width: 680px; }

.page-header { margin-bottom: 1.5rem; }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0.25rem 0 0; }

.card { margin-bottom: 1.25rem; }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.card-title { font-size: 0.9375rem; font-weight: 600; color: var(--color-text-primary); margin: 0 0 1rem; }
.card-head .card-title { margin-bottom: 1rem; }
.card-intro { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0 0 1rem; line-height: 1.6; }
.card-intro--strong { color: var(--color-text-primary); }
.card--codes { border: 1px solid var(--color-accent-gold); }

.form { display: flex; flex-direction: column; gap: 1rem; }
.form--inline { flex-direction: row; align-items: flex-start; gap: 1rem; }
.field { display: flex; flex-direction: column; gap: 0.375rem; }
.field--code { flex: 1; }
.label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.input {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 0.5625rem 0.75rem;
  font-size: 0.875rem;
  color: var(--color-text-primary);
  background: var(--color-bg-card);
}
.input:focus { outline: none; border-color: var(--color-sidebar-bg); }
.input--code { letter-spacing: 0.3em; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.hint { font-size: 0.75rem; color: var(--color-text-muted); margin: 0; line-height: 1.5; }

.form-actions { display: flex; gap: 0.625rem; align-items: center; }
.form--inline > .btn-danger { margin-top: 1.5rem; }

.btn-primary,
.btn-ghost,
.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 0.4375rem;
  border-radius: 6px;
  padding: 0.5625rem 1rem;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}
.btn-primary { background: var(--color-btn-primary); color: #fff; }
.btn-primary:hover:not(:disabled) { background: var(--color-btn-primary-hover); }
.btn-ghost {
  background: var(--color-bg-card);
  border-color: var(--color-border);
  color: var(--color-text-primary);
}
.btn-ghost:hover:not(:disabled) { border-color: var(--color-text-secondary); }
.btn-danger { background: var(--color-risk-high); color: #fff; }
.btn-danger:hover:not(:disabled) { filter: brightness(0.93); }
.btn-primary:disabled,
.btn-ghost:disabled,
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

.badge {
  padding: 0.1875rem 0.5625rem;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 600;
  white-space: nowrap;
}
.badge--on { background: var(--color-risk-low-bg); color: var(--color-risk-low); }
.badge--off { background: var(--color-risk-medium-bg); color: var(--color-risk-medium); }

.setup { display: flex; gap: 1.5rem; flex-wrap: wrap; }
.setup-qr {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0.625rem;
  align-self: flex-start;
}
.qr { display: block; width: 176px; height: 176px; }
.setup-body { flex: 1; min-width: 240px; display: flex; flex-direction: column; gap: 1rem; }
.setup-step { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; line-height: 1.6; }
.setup-manual summary {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.secret {
  display: inline-block;
  margin-top: 0.375rem;
  padding: 0.375rem 0.5rem;
  background: var(--color-bg-page);
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
  word-break: break-all;
}

.codes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 0.5rem;
  list-style: none;
  padding: 0;
  margin: 0 0 1.25rem;
}
.code {
  background: var(--color-bg-page);
  border-radius: 5px;
  padding: 0.5rem;
  text-align: center;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8125rem;
  letter-spacing: 0.04em;
}

.alert-error,
.alert-success,
.alert-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  border-radius: 8px;
  padding: 0.75rem 0.875rem;
  font-size: 0.8125rem;
  margin: 0 0 1.25rem;
  line-height: 1.55;
}
.form .alert-error,
.form .alert-success { margin: 0; }
.card > .alert-error,
.card > .alert-success { margin: 1rem 0 0; }
.alert-error {
  background: var(--color-risk-high-bg);
  color: var(--color-risk-high);
  border: 1px solid rgba(220, 38, 38, 0.2);
}
.alert-success {
  background: var(--color-risk-low-bg);
  color: var(--color-risk-low);
  border: 1px solid rgba(22, 163, 74, 0.2);
}
.alert-warning {
  background: var(--color-risk-medium-bg);
  color: var(--color-risk-medium);
  border: 1px solid rgba(217, 119, 6, 0.2);
}
.alert-warning svg { width: 16px; height: 16px; flex-shrink: 0; margin-top: 1px; }

.spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.btn-ghost .spinner { border-color: var(--color-border); border-top-color: var(--color-text-secondary); }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
