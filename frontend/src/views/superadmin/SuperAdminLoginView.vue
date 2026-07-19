<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <span class="login-logo-icon">⚙</span>
        </div>
        <h1 class="login-title">Console d'exploitation</h1>
        <p class="login-subtitle">Administration de la plateforme — accès réservé</p>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit" novalidate>
        <div class="field-group">
          <label for="sa-email" class="field-label">Adresse email</label>
          <input
            id="sa-email"
            v-model="form.email"
            type="email"
            class="field-input"
            :class="{ 'field-input--error': errors.email }"
            autocomplete="email"
            :disabled="loading"
          />
          <p v-if="errors.email" class="field-error">{{ errors.email }}</p>
        </div>

        <div class="field-group">
          <label for="sa-password" class="field-label">Mot de passe</label>
          <div class="password-wrapper">
            <input
              id="sa-password"
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              class="field-input"
              :class="{ 'field-input--error': errors.password }"
              placeholder="••••••••"
              autocomplete="current-password"
              :disabled="loading"
            />
            <button
              type="button"
              class="password-toggle"
              :aria-label="showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
              @click="showPassword = !showPassword"
            >
              <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
          <p v-if="errors.password" class="field-error">{{ errors.password }}</p>
        </div>

        <div v-if="globalError" class="alert-error" role="alert">
          <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {{ globalError }}
        </div>

        <button type="submit" class="btn-login" :disabled="loading">
          <span v-if="loading" class="spinner" aria-hidden="true" />
          <span>{{ loading ? 'Connexion en cours…' : 'Se connecter' }}</span>
        </button>
      </form>

      <p class="login-legal">
        Console distincte de l'espace cabinet · Toutes les actions sont journalisées
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useSuperAdminStore } from '@/stores/superAdmin'
import { superAdminService } from '@/services/superAdmin'

const router = useRouter()
const store = useSuperAdminStore()

const form = reactive({ email: '', password: '' })
const errors = reactive({ email: '', password: '' })
const globalError = ref('')
const loading = ref(false)
const showPassword = ref(false)

function validate(): boolean {
  errors.email = ''
  errors.password = ''
  if (!form.email) {
    errors.email = "L'adresse email est requise."
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.email = "L'adresse email est invalide."
  }
  if (!form.password) errors.password = 'Le mot de passe est requis.'
  return !errors.email && !errors.password
}

async function handleSubmit() {
  globalError.value = ''
  if (!validate()) return

  loading.value = true
  try {
    const data = await superAdminService.login(form.email, form.password)
    store.setSession(data.access_token, data.super_admin)
    router.push({ name: 'super-admin-tenants' })
  } catch (err: any) {
    const status = err?.response?.status
    const detail = err?.response?.data?.detail
    if (status === 401) {
      globalError.value = typeof detail === 'string' ? detail : 'Email ou mot de passe incorrect.'
    } else if (status === 429) {
      globalError.value = typeof detail === 'string' ? detail : 'Trop de tentatives. Réessayez plus tard.'
    } else {
      globalError.value = 'Impossible de contacter le serveur. Vérifiez votre connexion.'
    }
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
  background: var(--color-sidebar-darker);
  padding: 1.5rem;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.24);
  padding: 2.5rem 2rem;
}

.login-header { text-align: center; margin-bottom: 2rem; }

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
.login-logo-icon { font-size: 1.75rem; color: var(--color-accent-gold); }

.login-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-sidebar-bg);
  margin: 0 0 0.25rem;
  letter-spacing: -0.01em;
}
.login-subtitle { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; }

.login-form { display: flex; flex-direction: column; gap: 1.25rem; }
.field-group { display: flex; flex-direction: column; gap: 0.375rem; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }

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
}
.field-input:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201, 162, 39, 0.12); }
.field-input--error { border-color: var(--color-risk-high); }
.field-input:disabled { opacity: 0.6; cursor: not-allowed; }
.field-error { font-size: 0.75rem; color: var(--color-risk-high); margin: 0; }

.password-wrapper { position: relative; }
.password-wrapper .field-input { padding-right: 2.75rem; }
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
.password-toggle:hover { color: var(--color-text-secondary); }
.password-toggle svg { width: 16px; height: 16px; }

.alert-error {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.8125rem;
  line-height: 1.5;
  background: var(--color-risk-high-bg);
  color: var(--color-risk-high);
  border: 1px solid rgba(220, 38, 38, 0.2);
}
.alert-icon { width: 16px; height: 16px; flex-shrink: 0; margin-top: 1px; }

.btn-login {
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--color-btn-primary);
  color: #fff;
  font-size: 0.875rem;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: background 0.15s;
  margin-top: 0.25rem;
}
.btn-login:hover:not(:disabled) { background: var(--color-btn-primary-hover); }
.btn-login:disabled { opacity: 0.65; cursor: not-allowed; }

.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

.login-legal {
  margin: 1.5rem 0 0;
  text-align: center;
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}
</style>
