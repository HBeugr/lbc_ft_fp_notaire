import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/auth'

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
  }
})
