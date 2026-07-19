<template>
  <TenantStatusBanner />
  <RouterView />
  <ToastContainer />
</template>

<script setup lang="ts">
import { watch, onMounted, onUnmounted } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import ToastContainer from '@/components/common/ToastContainer.vue'
import TenantStatusBanner from '@/components/layout/TenantStatusBanner.vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'

const auth = useAuthStore()
const notifications = useNotificationsStore()
const router = useRouter()

// Le rafraîchissement silencieux vit dans le store : il doit distinguer un échec
// d'authentification (session purgée) d'un cabinet bloqué (session conservée,
// pour que la page d'explication reste atteignable).

// On page reload or new tab: Pinia resets but the httpOnly refresh_token cookie
// survives. Attempt a silent refresh to restore the access token before the
// router guard runs (guard awaits bootstrapReady).
onMounted(async () => {
  if (auth.user && !auth.accessToken) {
    await auth.silentRefresh()
  }
  // Recharge le cabinet : son statut a pu changer (suspension) pendant que l'onglet
  // était fermé, et le tenant persisté doit être confronté à celui du serveur.
  // `tenantBlocked` est inclus : un cabinet suspendu n'a pas de jeton d'accès, mais
  // /api/tenant/me reste ouvert pour lui présenter son statut.
  if (auth.isAuthenticated || auth.tenantBlocked) {
    await auth.fetchTenant()
  }
  auth.resolveBootstrap()
})

// Proactive token refresh — 5 minutes before the 30-minute access token expires.
const PROACTIVE_REFRESH_MS = 25 * 60 * 1000

let proactiveRefreshTimer: ReturnType<typeof setInterval> | null = null

function startProactiveRefresh() {
  if (proactiveRefreshTimer) return
  proactiveRefreshTimer = setInterval(async () => {
    if (!auth.isAuthenticated) { stopProactiveRefresh(); return }
    const ok = await auth.silentRefresh()
    if (!ok) {
      stopProactiveRefresh()
      // Cabinet bloqué en cours de session : on explique plutôt que de déconnecter.
      router.push({ name: auth.tenantBlocked ? 'compte-suspendu' : 'login' })
    }
  }, PROACTIVE_REFRESH_MS)
}

function stopProactiveRefresh() {
  if (proactiveRefreshTimer) { clearInterval(proactiveRefreshTimer); proactiveRefreshTimer = null }
}

watch(
  () => auth.isAuthenticated,
  (isAuth) => {
    if (isAuth) {
      startProactiveRefresh()
      notifications.startAlertsStream(auth.accessToken)
    } else {
      stopProactiveRefresh()
      notifications.stopAlertsStream()
    }
  },
  { immediate: true },
)

// Notifications polling for scoring weights update — only for RC and Notaire Principal
const POLL_INTERVAL_MS = 60_000

let pollTimer: ReturnType<typeof setInterval> | null = null

function startPolling() {
  if (pollTimer) return
  notifications.checkWeightsUpdate()
  pollTimer = setInterval(() => notifications.checkWeightsUpdate(), POLL_INTERVAL_MS)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

watch(
  () => auth.user?.role,
  (role) => {
    if (role === 'responsable_conformite' || role === 'notaire_principal') {
      startPolling()
    } else {
      stopPolling()
    }
  },
  { immediate: true },
)

// Déconnexion automatique après inactivité (Art. 29 — 30 min tous rôles)
const IDLE_TIMEOUT_MS = 30 * 60 * 1000
let idleTimer: ReturnType<typeof setTimeout> | null = null

function resetIdleTimer() {
  if (!auth.isAuthenticated) return
  if (idleTimer) clearTimeout(idleTimer)
  idleTimer = setTimeout(() => {
    auth.clearAuth()
    router.push({ name: 'login' })
  }, IDLE_TIMEOUT_MS)
}

function startIdleDetection() {
  const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart']
  events.forEach(e => window.addEventListener(e, resetIdleTimer, { passive: true }))
  resetIdleTimer()
}

function stopIdleDetection() {
  if (idleTimer) { clearTimeout(idleTimer); idleTimer = null }
  const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart']
  events.forEach(e => window.removeEventListener(e, resetIdleTimer))
}

watch(
  () => auth.isAuthenticated,
  (isAuth) => {
    if (isAuth) startIdleDetection()
    else stopIdleDetection()
  },
  { immediate: true },
)

onUnmounted(() => {
  stopPolling()
  stopProactiveRefresh()
  stopIdleDetection()
})
</script>
