<template>
  <div class="suspended-page">
    <div class="suspended-card">
      <div class="suspended-header">
        <div class="suspended-logo" :class="`suspended-logo--${statut}`">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <h1 class="suspended-title">{{ title }}</h1>
        <p class="suspended-subtitle">{{ subtitle }}</p>
      </div>

      <div class="info-grid">
        <div class="info-row">
          <span class="info-label">Cabinet</span>
          <span class="info-val">{{ auth.tenant?.nom ?? '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Identifiant</span>
          <span class="info-val info-val--mono">{{ auth.tenant?.slug ?? '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Statut</span>
          <span class="info-val"><span class="badge" :class="`badge--${statut}`">{{ statutLabel }}</span></span>
        </div>
      </div>

      <div v-if="auth.tenantMessage" class="alert-motif">
        <span class="alert-motif-label">Motif communiqué</span>
        {{ auth.tenantMessage }}
      </div>

      <p class="suspended-help">
        Contactez l'administrateur de la plateforme pour rétablir l'accès de votre cabinet.
        Vos données restent conservées conformément à l'Art. 23 (archivage 10 ans).
      </p>

      <div class="suspended-actions">
        <button class="btn-ghost" :disabled="checking" @click="recheck">
          <span v-if="checking" class="spinner spinner--dark" />
          Vérifier à nouveau
        </button>
        <button class="btn-primary" @click="handleLogout">Se déconnecter</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authService } from '@/services/api'

const auth = useAuthStore()
const router = useRouter()
const checking = ref(false)

const statut = computed(() => auth.tenant?.statut ?? 'suspendu')

const STATUT_LABELS: Record<string, string> = {
  configuration: 'En configuration',
  production: 'En production',
  suspendu: 'Suspendu',
  archive: 'Archivé',
}
const statutLabel = computed(() => STATUT_LABELS[statut.value] ?? statut.value)

const title = computed(() => {
  if (statut.value === 'configuration') return 'Cabinet en cours de configuration'
  if (statut.value === 'archive') return 'Cabinet archivé'
  return 'Accès suspendu'
})

const subtitle = computed(() => {
  if (statut.value === 'configuration') {
    return "Votre espace est en cours de préparation. L'accès sera ouvert dès son activation."
  }
  if (statut.value === 'archive') {
    return "Cet espace a été archivé et n'est plus accessible en consultation."
  }
  return "L'accès de votre cabinet à la plateforme a été temporairement suspendu."
})

// Permet de sortir de la page sans recharger si le statut a été rétabli entre-temps.
async function recheck() {
  checking.value = true
  try {
    await auth.fetchTenant()
    if (auth.tenantActive) router.push({ name: 'dashboard' })
  } finally {
    checking.value = false
  }
}

async function handleLogout() {
  await authService.logout().catch(() => {})
  auth.clearAuth()
  router.push({ name: 'login' })
}
</script>

<style scoped>
.suspended-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  padding: 1.5rem;
}

.suspended-card {
  width: 100%;
  max-width: 480px;
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  padding: 2.5rem 2rem;
}

.suspended-header { text-align: center; margin-bottom: 1.75rem; }

.suspended-logo {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  background: var(--color-risk-high-bg);
  color: var(--color-risk-high);
}
.suspended-logo--configuration { background: var(--color-risk-medium-bg); color: var(--color-risk-medium); }
.suspended-logo--archive { background: var(--color-status-cloture-bg); color: var(--color-status-cloture); }
.suspended-logo svg { width: 26px; height: 26px; }

.suspended-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-sidebar-bg);
  margin: 0 0 0.375rem;
  letter-spacing: -0.01em;
}

.suspended-subtitle {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0.875rem 1rem;
}
.info-row { display: flex; gap: 1rem; font-size: 0.8125rem; align-items: center; }
.info-label { min-width: 110px; color: var(--color-text-secondary); font-weight: 500; }
.info-val { color: var(--color-text-primary); }
.info-val--mono { font-family: monospace; }

.badge { border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.badge--suspendu { color: var(--color-risk-high); background: var(--color-risk-high-bg); }
.badge--configuration { color: var(--color-risk-medium); background: var(--color-risk-medium-bg); }
.badge--archive { color: var(--color-status-cloture); background: var(--color-status-cloture-bg); }
.badge--production { color: var(--color-risk-low); background: var(--color-risk-low-bg); }

.alert-motif {
  margin-top: 1rem;
  background: var(--color-risk-high-bg);
  color: var(--color-risk-high);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  font-size: 0.8125rem;
  line-height: 1.5;
}
.alert-motif-label {
  display: block;
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.25rem;
  opacity: 0.85;
}

.suspended-help {
  margin: 1.25rem 0 0;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.suspended-actions {
  display: flex;
  gap: 0.625rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.btn-ghost {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: border-color 0.12s;
}
.btn-ghost:hover:not(:disabled) { border-color: var(--color-text-secondary); }
.btn-ghost:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-primary {
  padding: 0.5rem 1.25rem;
  background: var(--color-btn-primary);
  color: #fff;
  border: none;
  border-radius: 7px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover { background: var(--color-btn-primary-hover); }

.spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
.spinner--dark {
  border-color: rgba(100, 116, 139, 0.3);
  border-top-color: var(--color-text-secondary);
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
