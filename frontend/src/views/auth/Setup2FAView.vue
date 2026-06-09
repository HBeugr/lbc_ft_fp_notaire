<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="w-full max-w-md bg-white rounded-xl shadow-lg p-8">
      <h2 class="text-xl font-bold mb-4">Configuration 2FA</h2>
      <p class="text-sm text-gray-600 mb-4">Scannez ce QR code avec votre application d'authentification.</p>
      <div v-if="qrData" class="flex justify-center mb-4">
        <!-- QR code rendered by frontend lib -->
        <canvas ref="qrCanvas"></canvas>
      </div>
      <form @submit.prevent="activate" class="space-y-4">
        <input v-model="code" placeholder="Code 6 chiffres" maxlength="6" class="w-full border rounded-lg px-3 py-2" />
        <div v-if="error" class="text-red-600 text-sm">{{ error }}</div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg">Activer</button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const qrData = ref('')
const code = ref('')
const error = ref('')
const qrCanvas = ref<HTMLCanvasElement | null>(null)
const router = useRouter()

onMounted(async () => {
  const { data } = await axios.post('/api/auth/totp/setup')
  qrData.value = data.qr_data
  if (qrCanvas.value) {
    const QRCode = (await import('qrcode')).default
    await QRCode.toCanvas(qrCanvas.value, data.qr_data)
  }
})

async function activate() {
  error.value = ''
  try {
    await axios.post('/api/auth/totp/activate', { code: code.value })
    router.push({ name: 'dashboard' })
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Code invalide.'
  }
}
</script>
