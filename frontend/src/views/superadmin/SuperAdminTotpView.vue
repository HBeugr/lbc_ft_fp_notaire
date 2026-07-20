<template>
  <div class="totp-page">
    <div class="totp-card">
      <div class="totp-header">
        <div class="totp-logo"><span class="totp-logo-icon">⚙</span></div>
        <h1 class="totp-title">Vérification en deux étapes</h1>
        <p class="totp-subtitle">
          {{ useBackup
            ? 'Saisissez l’un de vos codes de secours à usage unique.'
            : 'Saisissez le code affiché par votre application d’authentification.' }}
        </p>
      </div>

      <form class="totp-form" @submit.prevent="handleSubmit" novalidate>
        <div class="field-group">
          <label for="code" class="field-label">
            {{ useBackup ? 'Code de secours' : 'Code à 6 chiffres' }}
          </label>
          <input
            id="code"
            ref="codeInput"
            v-model="code"
            type="text"
            class="field-input field-input--code"
            :class="{ 'field-input--error': errorMessage }"
            :inputmode="useBackup ? 'text' : 'numeric'"
            :maxlength="useBackup ? 20 : 6"
            :placeholder="useBackup ? 'XXXX-XXXX' : '000000'"
            autocomplete="one-time-code"
            :disabled="loading"
          />
        </div>

        <div v-if="errorMessage" class="alert-error" role="alert">
          <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {{ errorMessage }}
        </div>

        <button type="submit" class="btn-login" :disabled="loading">
          <span v-if="loading" class="spinner" aria-hidden="true" />
          <span>{{ loading ? 'Vérification…' : 'Vérifier' }}</span>
        </button>
      </form>

      <div class="totp-alt">
        <button type="button" class="link-btn" @click="toggleMode">
          {{ useBackup ? 'Utiliser mon application d’authentification' : 'Utiliser un code de secours' }}
        </button>
        <button type="button" class="link-btn link-btn--muted" @click="abandon">
          Revenir à la connexion
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSuperAdminStore } from '@/stores/superAdmin'
import { superAdminService } from '@/services/superAdmin'

const router = useRouter()
const store = useSuperAdminStore()

const code = ref('')
const useBackup = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const codeInput = ref<HTMLInputElement | null>(null)

onMounted(() => codeInput.value?.focus())

function toggleMode() {
  useBackup.value = !useBackup.value
  code.value = ''
  errorMessage.value = ''
  nextTick(() => codeInput.value?.focus())
}

/** Abandonner l'étape 2 revient à annuler la connexion : le jeton en attente
 *  est révoqué côté serveur, pas seulement oublié côté navigateur. */
async function abandon() {
  try {
    await superAdminService.logout()
  } catch {
    // Session déjà close ou serveur injoignable — sans conséquence ici.
  }
  store.clearSession()
  router.push({ name: 'super-admin-login' })
}

async function handleSubmit() {
  errorMessage.value = ''
  const saisie = code.value.trim()

  if (!saisie) {
    errorMessage.value = 'Saisissez un code.'
    return
  }
  if (!useBackup.value && !/^\d{6}$/.test(saisie)) {
    errorMessage.value = 'Le code doit comporter 6 chiffres.'
    return
  }

  loading.value = true
  try {
    const data = useBackup.value
      ? await superAdminService.totpVerifyBackup(saisie)
      : await superAdminService.totpVerify(saisie)
    // `pending: false` — c'est cette bascule qui rend la session pleinement
    // authentifiée et débloque le garde de route.
    store.setSession(data.access_token, data.super_admin, false)
    router.push({ name: 'super-admin-dashboard' })
  } catch (err: any) {
    const statut = err?.response?.status
    const detail = err?.response?.data?.detail
    if (statut === 422) {
      errorMessage.value = typeof detail === 'string' ? detail : 'Code invalide.'
      code.value = ''
      nextTick(() => codeInput.value?.focus())
    } else if (statut === 429) {
      errorMessage.value =
        typeof detail === 'string' ? detail : 'Trop de tentatives. Réessayez plus tard.'
    } else if (statut === 401) {
      // Le jeton d'attente a expiré : il faut refaire le premier facteur.
      errorMessage.value = 'Session expirée. Reconnectez-vous.'
      store.clearSession()
      window.setTimeout(() => router.push({ name: 'super-admin-login' }), 1500)
    } else if (!err?.response) {
      errorMessage.value = 'Serveur injoignable. Vérifiez votre connexion.'
    } else {
      errorMessage.value = typeof detail === 'string' ? detail : 'La vérification a échoué.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.totp-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  padding: 1.5rem;
}

.totp-card {
  width: 100%;
  max-width: 420px;
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  padding: 2.5rem 2rem;
}

.totp-header { text-align: center; margin-bottom: 2rem; }
.totp-logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--color-sidebar-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
}
.totp-logo-icon { font-size: 1.5rem; color: var(--color-accent-gold); }
.totp-title { font-size: 1.125rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.totp-subtitle {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  margin: 0.5rem 0 0;
  line-height: 1.6;
}

.totp-form { display: flex; flex-direction: column; gap: 1.25rem; }
.field-group { display: flex; flex-direction: column; gap: 0.375rem; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.field-input {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 0.625rem 0.75rem;
  font-size: 0.9375rem;
  color: var(--color-text-primary);
  background: var(--color-bg-card);
}
.field-input:focus { outline: none; border-color: var(--color-sidebar-bg); }
.field-input--error { border-color: var(--color-risk-high); }
.field-input--code {
  text-align: center;
  letter-spacing: 0.35em;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 1.125rem;
}

.alert-error {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  background: var(--color-risk-high-bg);
  color: var(--color-risk-high);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: 8px;
  padding: 0.625rem 0.75rem;
  font-size: 0.8125rem;
  line-height: 1.5;
}
.alert-icon { width: 15px; height: 15px; flex-shrink: 0; margin-top: 1px; }

.btn-login {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: var(--color-btn-primary);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.6875rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}
.btn-login:hover:not(:disabled) { background: var(--color-btn-primary-hover); }
.btn-login:disabled { opacity: 0.6; cursor: not-allowed; }

.totp-alt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1.5rem;
}
.link-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-sidebar-bg);
  cursor: pointer;
  text-decoration: underline;
}
.link-btn--muted { color: var(--color-text-muted); font-weight: 400; }

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
