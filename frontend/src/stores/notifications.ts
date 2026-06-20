import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

const LS_KEY = 'lbc_seen_weights_version'

export interface Toast {
  id: string
  message: string
  type: 'warning' | 'info' | 'success'
}

export const useNotificationsStore = defineStore('notifications', () => {
  const toasts = ref<Toast[]>([])
  const weightsVersion = ref<number>(0)
  const seenVersion = ref<number>(parseInt(localStorage.getItem(LS_KEY) ?? '0', 10))

  // ── Compteur d'alertes temps réel (badge) ──────────────────────────────────
  const alertCount = ref<number>(0)
  let alertSource: EventSource | null = null
  let alertPollTimer: ReturnType<typeof setInterval> | null = null

  async function refreshAlertCount() {
    try {
      const { data } = await api.get<{ count: number }>('/alertes/mon-compteur')
      alertCount.value = data.count ?? 0
    } catch {
      // silent — non-blocking
    }
  }

  function startAlertsStream(token: string | null) {
    stopAlertsStream()
    if (!token) return
    try {
      alertSource = new EventSource(`/api/alertes/stream?token=${encodeURIComponent(token)}`)
      alertSource.addEventListener('count', (e: MessageEvent) => {
        const n = parseInt(e.data, 10)
        if (!Number.isNaN(n)) alertCount.value = n
      })
      alertSource.onerror = () => {
        // SSE indisponible (proxy, réseau) → bascule en polling
        stopAlertsStream()
        if (!alertPollTimer) {
          refreshAlertCount()
          alertPollTimer = setInterval(refreshAlertCount, 30_000)
        }
      }
    } catch {
      // EventSource non supporté → polling
      refreshAlertCount()
      alertPollTimer = setInterval(refreshAlertCount, 30_000)
    }
  }

  function stopAlertsStream() {
    if (alertSource) { alertSource.close(); alertSource = null }
    if (alertPollTimer) { clearInterval(alertPollTimer); alertPollTimer = null }
  }

  const hasPendingWeightsUpdate = computed(() => weightsVersion.value > seenVersion.value)

  function addToast(message: string, type: Toast['type'] = 'warning') {
    const id = `${Date.now()}-${Math.random()}`
    toasts.value.push({ id, message, type })
    setTimeout(() => removeToast(id), 9000)
  }

  function removeToast(id: string) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  function dismissWeightsBadge() {
    seenVersion.value = weightsVersion.value
    localStorage.setItem(LS_KEY, String(seenVersion.value))
  }

  async function checkWeightsUpdate() {
    try {
      const { data } = await api.get<{ version: number; updated_at: string | null }>('/scoring/weights/version')
      if (data.version > weightsVersion.value) {
        weightsVersion.value = data.version
        if (data.version > seenVersion.value) {
          addToast('Les pondérations de scoring ont été modifiées par un Administrateur. Les scores de risque seront recalculés lors de la prochaine évaluation.')
        }
      }
    } catch {
      // silent — non-blocking
    }
  }

  return {
    toasts,
    hasPendingWeightsUpdate,
    addToast,
    removeToast,
    dismissWeightsBadge,
    checkWeightsUpdate,
    alertCount,
    refreshAlertCount,
    startAlertsStream,
    stopAlertsStream,
  }
})
