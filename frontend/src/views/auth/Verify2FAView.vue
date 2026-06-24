<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <svg xmlns="http://www.w3.org/2000/svg" class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="5" y="11" width="14" height="10" rx="2"/>
            <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
          </svg>
        </div>
        <h1 class="login-title">Vérification 2FA</h1>
        <p class="login-subtitle">
          {{ useBackup
            ? 'Saisissez l\'un de vos codes de secours à usage unique'
            : 'Saisissez le code affiché dans votre application d\'authentification' }}
        </p>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit" novalidate>
        <div v-if="!useBackup" class="field-group">
          <label for="code" class="field-label">Code à 6 chiffres</label>
          <input
            id="code"
            ref="codeInput"
            v-model="code"
            type="text"
            inputmode="numeric"
            pattern="\d{6}"
            maxlength="6"
            class="field-input code-input"
            :class="{ 'field-input--error': error }"
            placeholder="000000"
            autocomplete="one-time-code"
            :disabled="loading"
          />
          <p v-if="error" class="field-error">{{ error }}</p>
        </div>

        <div v-else class="field-group">
          <label for="backup-code" class="field-label">Code de secours</label>
          <input
            id="backup-code"
            ref="backupInput"
            v-model="backupCode"
            type="text"
            maxlength="40"
            class="field-input"
            :class="{ 'field-input--error': error }"
            placeholder="xxxxxxxxxx"
            autocomplete="one-time-code"
            :disabled="loading"
          />
          <p v-if="error" class="field-error">{{ error }}</p>
        </div>

        <button type="submit" class="btn-primary btn-login" :disabled="loading || (useBackup ? backupCode.trim().length < 6 : code.length !== 6)">
          <span v-if="loading" class="spinner" aria-hidden="true" />
          <span>{{ loading ? 'Vérification…' : 'Confirmer' }}</span>
        </button>

        <button type="button" class="btn-ghost" @click="toggleBackup">
          {{ useBackup ? 'Utiliser le code de l\'application' : 'Utiliser un code de secours' }}
        </button>

        <button type="button" class="btn-ghost" @click="handleCancel">
          Annuler la connexion
        </button>
      </form>

      <p class="login-legal">
        Google Authenticator · Microsoft Authenticator · Authy
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()

const code = ref('')
const backupCode = ref('')
const useBackup = ref(false)
const error = ref('')
const loading = ref(false)
const codeInput = ref<HTMLInputElement | null>(null)
const backupInput = ref<HTMLInputElement | null>(null)

onMounted(() => {
  codeInput.value?.focus()
})

function toggleBackup() {
  useBackup.value = !useBackup.value
  error.value = ''
  code.value = ''
  backupCode.value = ''
  nextTick(() => (useBackup.value ? backupInput.value : codeInput.value)?.focus())
}

async function handleSubmit() {
  error.value = ''
  if (!authStore.accessToken) {
    router.push({ name: 'login' })
    return
  }
  loading.value = true
  try {
    const { data } = useBackup.value
      ? await api.post('/auth/totp/verify-backup', { code: backupCode.value })
      : await api.post('/auth/totp/verify', { code: code.value })
    authStore.setToken(data.access_token)
    router.push({ name: 'dashboard' })
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 422 || status === 400) {
      error.value = useBackup.value
        ? 'Code de secours invalide. Réessayez ou utilisez votre application.'
        : 'Code incorrect. Vérifiez votre application et réessayez.'
    } else if (status === 401) {
      authStore.clearAuth()
      router.push({ name: 'login' })
    } else {
      error.value = 'Erreur de vérification. Réessayez.'
    }
    code.value = ''
    backupCode.value = ''
    nextTick(() => (useBackup.value ? backupInput.value : codeInput.value)?.focus())
  } finally {
    loading.value = false
  }
}

async function handleCancel() {
  await api.post('/auth/logout').catch(() => {})
  authStore.clearAuth()
  router.push({ name: 'login' })
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

.login-card {
  width: 100%;
  max-width: 380px;
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  padding: 2.5rem 2rem;
}

.login-header { text-align: center; margin-bottom: 2rem; }

.login-logo {
  width: 56px; height: 56px;
  background: var(--color-sidebar-bg);
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 1rem;
}

.logo-icon { width: 26px; height: 26px; color: var(--color-accent-gold); }

.login-title { font-size: 1.25rem; font-weight: 700; color: var(--color-sidebar-bg); margin: 0 0 0.375rem; }
.login-subtitle { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; line-height: 1.6; }

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

.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

.login-legal { margin: 1.5rem 0 0; text-align: center; font-size: 0.6875rem; color: var(--color-text-muted); }
</style>
