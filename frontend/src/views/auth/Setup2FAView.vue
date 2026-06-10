<template>
  <div class="login-page">
    <div class="setup-card">
      <!-- Étape 1 : scanner le QR code -->
      <template v-if="step === 'scan'">
        <div class="login-header">
          <div class="login-logo">
            <svg xmlns="http://www.w3.org/2000/svg" class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="5" y="11" width="14" height="10" rx="2"/>
              <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
            </svg>
          </div>
          <h1 class="login-title">Configurer l'authentification à deux facteurs</h1>
          <p class="login-subtitle">
            Obligatoire pour votre rôle · Scannez ce QR code avec votre application
          </p>
        </div>

        <div v-if="loadingSetup" class="qr-placeholder">
          <div class="spinner-lg" />
        </div>
        <div v-else-if="setupError" class="alert-error">{{ setupError }}</div>
        <div v-else class="qr-block">
          <div class="qr-frame">
            <canvas ref="qrCanvas" />
          </div>
          <p class="qr-hint">
            Utilisez <strong>Google Authenticator</strong>, <strong>Microsoft Authenticator</strong>
            ou <strong>Authy</strong>
          </p>
          <details class="manual-entry">
            <summary>Saisie manuelle</summary>
            <code class="manual-code">{{ manualSecret }}</code>
          </details>
        </div>

        <button
          class="btn-primary btn-login"
          :disabled="loadingSetup || !!setupError"
          @click="step = 'confirm'"
        >
          J'ai scanné le QR code — Continuer
        </button>
      </template>

      <!-- Étape 2 : confirmer avec le premier code -->
      <template v-else-if="step === 'confirm'">
        <div class="login-header">
          <div class="login-logo">
            <svg xmlns="http://www.w3.org/2000/svg" class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <h1 class="login-title">Confirmer l'activation</h1>
          <p class="login-subtitle">Saisissez le code généré par votre application pour valider</p>
        </div>

        <form class="login-form" @submit.prevent="handleActivate" novalidate>
          <div class="field-group">
            <label for="confirm-code" class="field-label">Code à 6 chiffres</label>
            <input
              id="confirm-code"
              ref="confirmInput"
              v-model="confirmCode"
              type="text"
              inputmode="numeric"
              pattern="\d{6}"
              maxlength="6"
              class="field-input code-input"
              :class="{ 'field-input--error': confirmError }"
              placeholder="000000"
              autocomplete="one-time-code"
              :disabled="activating"
            />
            <p v-if="confirmError" class="field-error">{{ confirmError }}</p>
          </div>

          <button type="submit" class="btn-primary btn-login" :disabled="activating || confirmCode.length !== 6">
            <span v-if="activating" class="spinner" aria-hidden="true" />
            <span>{{ activating ? 'Activation…' : 'Activer le 2FA' }}</span>
          </button>

          <button type="button" class="btn-ghost" @click="step = 'scan'">
            ← Retour au QR code
          </button>
        </form>
      </template>

      <!-- Étape 3 : succès -->
      <template v-else-if="step === 'done'">
        <div class="done-block">
          <div class="done-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <h1 class="login-title">2FA activé avec succès</h1>
          <p class="login-subtitle">
            Votre compte est désormais protégé par l'authentification à deux facteurs.
          </p>
          <button class="btn-primary btn-login" style="margin-top:1.5rem" @click="goToDashboard">
            Accéder au tableau de bord
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import QRCode from 'qrcode'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'

type Step = 'scan' | 'confirm' | 'done'

const router = useRouter()
const authStore = useAuthStore()

const step = ref<Step>('scan')
const qrData = ref('')
const manualSecret = ref('')
const loadingSetup = ref(true)
const setupError = ref('')
const confirmCode = ref('')
const confirmError = ref('')
const activating = ref(false)
const confirmInput = ref<HTMLInputElement | null>(null)
const qrCanvas = ref<HTMLCanvasElement | null>(null)

async function renderQr() {
  if (!qrCanvas.value || !qrData.value) return
  await QRCode.toCanvas(qrCanvas.value, qrData.value, { width: 200, margin: 1 })
}

watch(qrCanvas, renderQr)
watch(qrData, renderQr)

onMounted(async () => {
  if (!authStore.accessToken) {
    router.push({ name: 'login' })
    return
  }
  try {
    const { data } = await api.post('/auth/totp/setup')
    qrData.value = data.qr_data
    const match = data.provisioning_uri?.match(/secret=([A-Z2-7]+)/i)
    manualSecret.value = match ? match[1] : ''
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 409) {
      router.push({ name: 'dashboard' })
    } else {
      setupError.value = 'Impossible de générer le QR code. Contactez votre administrateur.'
    }
  } finally {
    loadingSetup.value = false
  }
})

async function handleActivate() {
  confirmError.value = ''
  if (!authStore.accessToken) return

  activating.value = true
  try {
    await api.post('/auth/totp/activate', { code: confirmCode.value })
    step.value = 'done'
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 422) {
      confirmError.value = 'Code incorrect. Vérifiez votre application.'
    } else if (status === 400) {
      confirmError.value = 'Session expirée. Rechargez la page pour recommencer.'
    } else {
      confirmError.value = "Erreur lors de l'activation."
    }
    confirmCode.value = ''
    await nextTick()
    confirmInput.value?.focus()
  } finally {
    activating.value = false
  }
}

function goToDashboard() {
  router.push({ name: 'dashboard' })
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  padding: 1.5rem;
}

.setup-card {
  width: 100%;
  max-width: 440px;
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  padding: 2.5rem 2rem;
}

.login-header { text-align: center; margin-bottom: 1.75rem; }

.login-logo {
  width: 56px; height: 56px;
  background: var(--color-sidebar-bg);
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 1rem;
}

.logo-icon { width: 26px; height: 26px; color: var(--color-accent-gold); }
.login-title { font-size: 1.125rem; font-weight: 700; color: var(--color-sidebar-bg); margin: 0 0 0.375rem; }
.login-subtitle { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; line-height: 1.6; }

.qr-placeholder { display: flex; justify-content: center; padding: 3rem 0; }

.qr-block { display: flex; flex-direction: column; align-items: center; gap: 1rem; margin-bottom: 1.5rem; }

.qr-frame { padding: 1rem; background: #fff; border: 2px solid var(--color-border); border-radius: 10px; }

.qr-hint { font-size: 0.8125rem; color: var(--color-text-secondary); text-align: center; margin: 0; }

.manual-entry { width: 100%; }
.manual-entry summary { font-size: 0.75rem; color: var(--color-text-muted); cursor: pointer; text-align: center; }
.manual-code {
  display: block; margin-top: 0.5rem; padding: 0.5rem 0.75rem;
  background: var(--color-bg-page); border-radius: 6px;
  font-size: 0.8125rem; letter-spacing: 0.1em; word-break: break-all;
  text-align: center; color: var(--color-text-primary);
}

.done-block { text-align: center; padding: 1rem 0; }
.done-icon {
  width: 64px; height: 64px;
  background: var(--color-risk-low-bg); border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 1.25rem;
}
.done-icon svg { width: 30px; height: 30px; color: var(--color-risk-low); }

.login-form { display: flex; flex-direction: column; gap: 1.25rem; }
.field-group { display: flex; flex-direction: column; gap: 0.375rem; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }

.field-input {
  width: 100%; padding: 0.625rem 0.875rem;
  border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.875rem; color: var(--color-text-primary); background: #fff;
  outline: none; transition: border-color 0.15s, box-shadow 0.15s;
}
.field-input:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201, 162, 39, 0.12); }
.field-input--error { border-color: var(--color-risk-high); }

.code-input { text-align: center; font-size: 1.5rem; font-weight: 700; letter-spacing: 0.35em; padding: 0.75rem; }
.field-error { font-size: 0.75rem; color: var(--color-risk-high); margin: 0; text-align: center; }

.btn-login {
  width: 100%; padding: 0.75rem 1rem;
  background: var(--color-btn-primary); color: #fff;
  font-size: 0.875rem; font-weight: 600; border: none; border-radius: 8px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  gap: 0.5rem; transition: background 0.15s;
}
.btn-login:hover:not(:disabled) { background: var(--color-btn-primary-hover); }
.btn-login:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-ghost {
  width: 100%; padding: 0.5rem; background: none; border: none;
  color: var(--color-text-secondary); font-size: 0.8125rem; cursor: pointer;
  text-decoration: underline; text-underline-offset: 2px;
}
.btn-ghost:hover { color: var(--color-text-primary); }

.alert-error { padding: 0.75rem 1rem; border-radius: 8px; background: var(--color-risk-high-bg); color: var(--color-risk-high); font-size: 0.8125rem; margin-bottom: 1rem; }

.spinner-lg {
  width: 36px; height: 36px;
  border: 3px solid var(--color-border); border-top-color: var(--color-sidebar-bg);
  border-radius: 50%; animation: spin 0.7s linear infinite;
}

.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
