<template>
  <RouterView />
</template>

<script setup lang="ts">
import { watch, onMounted, onUnmounted } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

async function silentRefresh(): Promise<boolean> {
  try {
    const { data } = await axios.post<{ access_token: string }>('/api/auth/refresh', null, { withCredentials: true })
    auth.setToken(data.access_token)
    return true
  } catch {
    auth.clearAuth()
    return false
  }
}

onMounted(async () => {
  if (auth.user && !auth.accessToken) {
    await silentRefresh()
  }
  auth.resolveBootstrap()
})

const PROACTIVE_REFRESH_MS = 25 * 60 * 1000
let proactiveRefreshTimer: ReturnType<typeof setInterval> | null = null

function startProactiveRefresh() {
  if (proactiveRefreshTimer) return
  proactiveRefreshTimer = setInterval(async () => {
    if (!auth.isAuthenticated) { stopProactiveRefresh(); return }
    const ok = await silentRefresh()
    if (!ok) { stopProactiveRefresh(); router.push({ name: 'login' }) }
  }, PROACTIVE_REFRESH_MS)
}

function stopProactiveRefresh() {
  if (proactiveRefreshTimer) { clearInterval(proactiveRefreshTimer); proactiveRefreshTimer = null }
}

watch(() => auth.isAuthenticated, (isAuth) => {
  if (isAuth) startProactiveRefresh()
  else stopProactiveRefresh()
}, { immediate: true })

const IDLE_TIMEOUT_MS = 30 * 60 * 1000
let idleTimer: ReturnType<typeof setTimeout> | null = null

function resetIdleTimer() {
  if (!auth.isAuthenticated) return
  if (idleTimer) clearTimeout(idleTimer)
  idleTimer = setTimeout(() => { auth.clearAuth(); router.push({ name: 'login' }) }, IDLE_TIMEOUT_MS)
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

watch(() => auth.isAuthenticated, (isAuth) => {
  if (isAuth) startIdleDetection()
  else stopIdleDetection()
}, { immediate: true })

onUnmounted(() => { stopProactiveRefresh(); stopIdleDetection() })
</script>
