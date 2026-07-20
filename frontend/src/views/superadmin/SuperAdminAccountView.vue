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

  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSuperAdminStore } from '@/stores/superAdmin'
import { superAdminService } from '@/services/superAdmin'

const router = useRouter()
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

  // Mémorisé avant l'appel : `setSuperAdmin` remet le drapeau à faux, on ne
  // pourrait plus distinguer ensuite le déverrouillage initial d'un simple
  // changement de mot de passe volontaire.
  const etaitVerrouille = store.mustChangePassword

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

    // Sans cette redirection, l'utilisateur venu du verrou reste sur la page de
    // compte, désormais libre d'en sortir mais sans rien qui le lui indique :
    // l'écran est identique avant et après, ce qui se lit comme un blocage.
    if (etaitVerrouille) {
      router.push({ name: 'super-admin-dashboard' })
    }
  } catch (err: any) {
    pwdError.value = messageDe(err, 'Le changement de mot de passe a échoué.')
  } finally {
    pwdLoading.value = false
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
.card-title { font-size: 0.9375rem; font-weight: 600; color: var(--color-text-primary); margin: 0 0 1rem; }

.form { display: flex; flex-direction: column; gap: 1rem; }
.field { display: flex; flex-direction: column; gap: 0.375rem; }
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
.hint { font-size: 0.75rem; color: var(--color-text-muted); margin: 0; line-height: 1.5; }

.form-actions { display: flex; gap: 0.625rem; align-items: center; }

.btn-primary,
.btn-ghost {
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
.btn-primary:disabled,
.btn-ghost:disabled { opacity: 0.6; cursor: not-allowed; }

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
