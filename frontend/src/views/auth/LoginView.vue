<template>
  <div class="login-page">
    <div class="login-card">
      <!-- Logo / En-tête -->
      <div class="login-header">
        <div class="login-logo">
          <span class="login-logo-icon">⚖</span>
        </div>
        <h1 class="login-title">LBC/FT/FP Conformité</h1>
        <p class="login-subtitle">Plateforme notariale — Chambre des Notaires de Côte d'Ivoire</p>
      </div>

      <!-- Formulaire -->
      <form class="login-form" @submit.prevent="handleSubmit" novalidate>
        <!-- Email -->
        <div class="field-group">
          <label for="email" class="field-label">Adresse email</label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            class="field-input"
            :class="{ 'field-input--error': errors.email }"
            placeholder="prenom.nom@notaire.ci"
            autocomplete="email"
            :disabled="loading"
          />
          <p v-if="errors.email" class="field-error">{{ errors.email }}</p>
        </div>

        <!-- Mot de passe -->
        <div class="field-group">
          <label for="password" class="field-label">Mot de passe</label>
          <div class="password-wrapper">
            <input
              id="password"
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
              <svg v-if="!showPassword" xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
          <p v-if="errors.password" class="field-error">{{ errors.password }}</p>
        </div>

        <!-- Erreur globale -->
        <div v-if="globalError" class="alert-error" role="alert">
          <svg xmlns="http://www.w3.org/2000/svg" class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {{ globalError }}
        </div>

        <!-- Tentatives restantes -->
        <div v-if="attemptsWarning" class="alert-warning" role="alert">
          <svg xmlns="http://www.w3.org/2000/svg" class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {{ attemptsWarning }}
        </div>

        <!-- Bouton connexion -->
        <button type="submit" class="btn-primary btn-login" :disabled="loading">
          <span v-if="loading" class="spinner" aria-hidden="true" />
          <span>{{ loading ? 'Connexion en cours…' : 'Se connecter' }}</span>
        </button>
      </form>

      <!-- Footer mention réglementaire -->
      <p class="login-legal">
        Accès réservé aux collaborateurs autorisés · Art. 63 Ord. N°2023-875
      </p>

      <!-- Accès console super-administrateur (opérateur SaaS).
           Même présentation que l'assujetti immo/foncier, pour que les deux
           produits s'ouvrent de la même façon. -->
      <RouterLink :to="{ name: 'super-admin-login' }" class="login-admin-link" rel="nofollow">
        <span aria-hidden="true">🛡️</span> Accès super-administrateur
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ email: '', password: '' })
const errors = reactive({ email: '', password: '' })
const globalError = ref('')
const attemptsWarning = ref('')
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

  if (!form.password) {
    errors.password = 'Le mot de passe est requis.'
  }

  return !errors.email && !errors.password
}

async function handleSubmit() {
  globalError.value = ''
  attemptsWarning.value = ''

  if (!validate()) return

  loading.value = true
  try {
    const { data } = await api.post('/auth/login', {
      email: form.email,
      password: form.password,
    })

    // Le cabinet est posé avant l'utilisateur : setTenant purge le state persisté
    // si l'on se connecte à un autre cabinet sur ce navigateur.
    authStore.setTenant(data.tenant ?? null)
    authStore.setToken(data.access_token)
    authStore.setUser(data.user)

    if (data.totp_pending) {
      router.push({ name: '2fa-verify' })
    } else if (data.user?.must_change_password) {
      router.push({ name: 'change-password' })
    } else if (data.user?.requires_2fa && !data.user?.totp_enabled) {
      router.push({ name: '2fa-setup' })
    } else {
      router.push({ name: 'dashboard' })
    }
  } catch (err: any) {
    const httpStatus = err?.response?.status
    const detail = err?.response?.data?.detail

    if (httpStatus === 402 || httpStatus === 403) {
      // Cabinet suspendu / en configuration / archivé : le message vient du backend.
      const code = typeof detail === 'object' ? detail?.code : undefined
      const msg = typeof detail === 'object' ? detail?.message : detail
      globalError.value = msg ?? "L'accès de votre cabinet à la plateforme est indisponible."
      if (code === 'tenant_configuration') {
        attemptsWarning.value = "Votre espace est en cours de configuration par l'administrateur de la plateforme."
      }
    } else if (httpStatus === 429) {
      globalError.value = typeof detail === 'string' ? detail : 'Trop de tentatives. Réessayez dans 15 minutes.'
    } else if (httpStatus === 401) {
      const msg = typeof detail === 'object' ? detail?.message : (detail ?? 'Email ou mot de passe incorrect.')
      const remaining: number | undefined = typeof detail === 'object' ? detail?.remaining_attempts : undefined
      globalError.value = msg
      if (remaining !== undefined && remaining > 0) {
        attemptsWarning.value = `${remaining} tentative${remaining > 1 ? 's' : ''} restante${remaining > 1 ? 's' : ''} avant blocage temporaire (15 min).`
      } else if (remaining === 0) {
        attemptsWarning.value = 'Compte temporairement bloqué. Réessayez dans 15 minutes.'
      } else {
        attemptsWarning.value = 'Après 5 tentatives incorrectes, votre accès sera temporairement bloqué.'
      }
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
}

.field-input:focus {
  border-color: var(--color-sidebar-bg);
  box-shadow: 0 0 0 3px rgba(201, 162, 39, 0.12);
}

.field-input--error {
  border-color: var(--color-risk-high);
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

.alert-error,
.alert-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.alert-error {
  background: var(--color-risk-high-bg);
  color: var(--color-risk-high);
  border: 1px solid rgba(220, 38, 38, 0.2);
}

.alert-warning {
  background: var(--color-risk-medium-bg);
  color: var(--color-risk-medium);
  border: 1px solid rgba(217, 119, 6, 0.2);
}

.alert-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}

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

.btn-login:hover:not(:disabled) {
  background: var(--color-btn-primary-hover);
}

.btn-login:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.login-legal {
  margin: 1.5rem 0 0;
  text-align: center;
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}

/* Volontairement effacé : l'exploitant sait qu'il existe, le collaborateur
   de cabinet n'a aucune raison de cliquer. */
/* Repris tel quel de l'assujetti immo/foncier (LoginView.vue) : filet de
   séparation puis lien discret, plutôt qu'une pilule. `:focus-visible` est
   ajouté — l'original ne donne aucun retour au clavier. */
.login-admin-link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  text-decoration: none;
}

.login-admin-link:hover,
.login-admin-link:focus-visible {
  color: var(--color-sidebar-bg);
}
</style>
