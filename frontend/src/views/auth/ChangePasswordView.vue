<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <span class="login-logo-icon">⚖</span>
        </div>
        <h1 class="login-title">Définir votre mot de passe</h1>
        <p class="login-subtitle">
          Pour des raisons de sécurité, vous devez définir un mot de passe personnel avant d'accéder à la plateforme.
        </p>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit" novalidate>
        <div class="field-group">
          <label for="current" class="field-label">Mot de passe temporaire</label>
          <div class="password-wrapper">
            <input
              id="current"
              v-model="form.currentPassword"
              :type="show.current ? 'text' : 'password'"
              class="field-input"
              :class="{ 'field-input--error': errors.currentPassword }"
              autocomplete="current-password"
              :disabled="loading"
            />
            <button type="button" class="password-toggle" @click="show.current = !show.current">
              <svg v-if="!show.current" xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
          <p v-if="errors.currentPassword" class="field-error">{{ errors.currentPassword }}</p>
        </div>

        <div class="field-group">
          <label for="new" class="field-label">Nouveau mot de passe</label>
          <div class="password-wrapper">
            <input
              id="new"
              v-model="form.newPassword"
              :type="show.new ? 'text' : 'password'"
              class="field-input"
              :class="{ 'field-input--error': errors.newPassword }"
              autocomplete="new-password"
              :disabled="loading"
            />
            <button type="button" class="password-toggle" @click="show.new = !show.new">
              <svg v-if="!show.new" xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>

          <!-- Indicateur de robustesse -->
          <div v-if="form.newPassword" class="strength-block">
            <div class="strength-bars">
              <span v-for="i in 4" :key="i" class="strength-bar" :class="strengthBarClass(i)" />
            </div>
            <span class="strength-label" :class="strength.labelClass">{{ strength.label }}</span>
          </div>

          <!-- Critères -->
          <ul v-if="form.newPassword" class="criteria-list">
            <li v-for="c in criteria" :key="c.key" :class="c.met ? 'met' : 'unmet'">
              <span class="criteria-dot" />{{ c.label }}
            </li>
          </ul>

          <p v-if="errors.newPassword" class="field-error">{{ errors.newPassword }}</p>
        </div>

        <div class="field-group">
          <label for="confirm" class="field-label">Confirmer le nouveau mot de passe</label>
          <div class="password-wrapper">
            <input
              id="confirm"
              v-model="form.confirmPassword"
              :type="show.confirm ? 'text' : 'password'"
              class="field-input"
              :class="{
                'field-input--error': errors.confirmPassword || (form.confirmPassword && !passwordsMatch),
                'field-input--ok': form.confirmPassword && passwordsMatch
              }"
              autocomplete="new-password"
              :disabled="loading"
            />
            <button type="button" class="password-toggle" @click="show.confirm = !show.confirm">
              <svg v-if="!show.confirm" xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
          <!-- Feedback temps réel -->
          <div v-if="form.confirmPassword" class="match-feedback" :class="passwordsMatch ? 'match-ok' : 'match-fail'">
            <svg viewBox="0 0 16 16" fill="none" class="match-icon">
              <path v-if="passwordsMatch" d="M3 8l3.5 3.5L13 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path v-else d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span>{{ passwordsMatch ? 'Les mots de passe correspondent' : 'Les mots de passe ne correspondent pas' }}</span>
          </div>
          <p v-if="errors.confirmPassword" class="field-error">{{ errors.confirmPassword }}</p>
        </div>

        <p v-if="globalError" class="global-error">{{ globalError }}</p>

        <button type="submit" class="btn-submit" :disabled="loading">
          <span v-if="loading">Enregistrement…</span>
          <span v-else>Accéder à la plateforme</span>
        </button>
      </form>

      <p class="login-footer">Accès réservé aux collaborateurs autorisés · Art. 63 Ord. N°2023-875</p>

      <!-- Sortie de secours : sans elle, un utilisateur forcé au changement de
           mot de passe (compte temporaire) reste piégé sur cet écran. -->
      <button type="button" class="login-back-link" @click="handleLogout">← Se déconnecter</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authService } from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ currentPassword: '', newPassword: '', confirmPassword: '' })
const show = reactive({ current: false, new: false, confirm: false })
const errors = reactive({ currentPassword: '', newPassword: '', confirmPassword: '' })
const globalError = ref('')
const loading = ref(false)

const passwordsMatch = computed(() =>
  form.confirmPassword.length > 0 && form.newPassword === form.confirmPassword
)

// ── Password strength ────────────────────────────────────────────────────────
const criteria = computed(() => [
  { key: 'len',     label: '12 caractères minimum',          met: form.newPassword.length >= 12 },
  { key: 'upper',   label: 'Une lettre majuscule',           met: /[A-Z]/.test(form.newPassword) },
  { key: 'lower',   label: 'Une lettre minuscule',           met: /[a-z]/.test(form.newPassword) },
  { key: 'digit',   label: 'Un chiffre',                     met: /\d/.test(form.newPassword) },
  { key: 'special', label: 'Un caractère spécial (!@#$…)',   met: /[^A-Za-z0-9]/.test(form.newPassword) },
])

const strengthScore = computed(() => criteria.value.filter(c => c.met).length)

const strength = computed(() => {
  const s = strengthScore.value
  if (s <= 1) return { label: 'Très faible', labelClass: 'str--1' }
  if (s === 2) return { label: 'Faible',      labelClass: 'str--2' }
  if (s === 3) return { label: 'Moyen',       labelClass: 'str--3' }
  if (s === 4) return { label: 'Fort',        labelClass: 'str--4' }
  return              { label: 'Très fort',   labelClass: 'str--5' }
})

function strengthBarClass(i: number) {
  const s = strengthScore.value
  if (s <= 1) return i <= 1 ? 'bar--1' : 'bar--empty'
  if (s === 2) return i <= 2 ? 'bar--2' : 'bar--empty'
  if (s === 3) return i <= 3 ? 'bar--3' : 'bar--empty'
  return 'bar--4'
}

function validate(): boolean {
  errors.currentPassword = form.currentPassword ? '' : 'Champ requis.'

  const unmet = criteria.value.filter(c => !c.met)
  errors.newPassword = unmet.length > 0
    ? `Critère non respecté : ${unmet[0].label.toLowerCase()}.`
    : ''

  errors.confirmPassword = form.newPassword === form.confirmPassword ? '' : 'Les mots de passe ne correspondent pas.'
  return !errors.currentPassword && !errors.newPassword && !errors.confirmPassword
}

async function handleLogout() {
  await authService.logout().catch(() => {})
  authStore.clearAuth()
  router.push({ name: 'login' })
}

async function handleSubmit() {
  globalError.value = ''
  if (!validate()) return

  loading.value = true
  try {
    const res = await authService.changePassword(form.currentPassword, form.newPassword)

    authStore.setToken(res.access_token)
    if (res.user) authStore.setUser(res.user)

    router.push({ name: 'dashboard' })
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    globalError.value = typeof detail === 'string' ? detail : 'Une erreur est survenue.'
  } finally {
    loading.value = false
  }
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
  max-width: 420px;
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  padding: 2.5rem 2rem;
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-logo {
  width: 56px;
  height: 56px;
  background: var(--color-sidebar-bg);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
}

.login-logo-icon {
  font-size: 1.75rem;
  color: var(--color-accent-gold);
}

.login-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-sidebar-bg);
  margin: 0 0 0.25rem;
  letter-spacing: -0.01em;
}

.login-subtitle {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-primary);
}

.field-input {
  width: 100%;
  padding: 0.625rem 0.875rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 0.875rem;
  color: var(--color-text-primary);
  background: #fff;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: var(--color-sidebar-bg);
  box-shadow: 0 0 0 3px rgba(201, 162, 39, 0.12);
}

.field-input--error {
  border-color: var(--color-risk-high);
}
.field-input--ok {
  border-color: #16a34a;
}

.field-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.field-error {
  font-size: 0.75rem;
  color: var(--color-risk-high);
  margin: 0;
}

.password-wrapper {
  position: relative;
}

.password-wrapper .field-input {
  padding-right: 2.75rem;
}

.password-toggle {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  padding: 0;
}

.password-toggle:hover {
  color: var(--color-text-secondary);
}

.icon {
  width: 16px;
  height: 16px;
}

/* Strength indicator */
.strength-block {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.25rem;
}

.strength-bars {
  display: flex;
  gap: 3px;
  flex: 1;
}

.strength-bar {
  height: 4px;
  flex: 1;
  border-radius: 2px;
  background: var(--color-border);
  transition: background 0.2s;
}

.bar--1 { background: #dc2626; }
.bar--2 { background: #f97316; }
.bar--3 { background: #eab308; }
.bar--4 { background: #16a34a; }
.bar--empty { background: var(--color-border); }

.strength-label { font-size: 0.6875rem; font-weight: 600; white-space: nowrap; }
.str--1 { color: #dc2626; }
.str--2 { color: #f97316; }
.str--3 { color: #eab308; }
.str--4 { color: #16a34a; }
.str--5 { color: #15803d; }

/* Criteria */
.criteria-list {
  list-style: none;
  margin: 0.25rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.criteria-list li {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
}

.criteria-list .met   { color: #16a34a; }
.criteria-list .unmet { color: var(--color-text-muted); }

.criteria-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: currentColor;
}

.global-error {
  font-size: 0.8125rem;
  color: var(--color-risk-high);
  background: var(--color-risk-high-bg);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin: 0;
}

.btn-submit {
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--color-btn-primary);
  color: #fff;
  font-size: 0.875rem;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 0.25rem;
}

.btn-submit:hover:not(:disabled) {
  background: var(--color-btn-primary-hover);
}

.btn-submit:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

/* Match feedback */
.match-feedback {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  font-weight: 500;
  margin-top: 0.25rem;
}
.match-ok  { color: #16a34a; }
.match-fail { color: var(--color-risk-high); }
.match-icon { width: 14px; height: 14px; flex-shrink: 0; }

.login-footer {
  margin: 1.5rem 0 0;
  text-align: center;
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.login-back-link {
  display: block;
  width: 100%;
  margin-top: 1.25rem;
  padding-top: 1rem;
  border: none;
  border-top: 1px solid var(--color-border);
  background: none;
  text-align: center;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.login-back-link:hover { color: var(--color-sidebar-bg); }
</style>
