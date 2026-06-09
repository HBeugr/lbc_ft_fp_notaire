<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="w-full max-w-sm bg-white rounded-xl shadow-lg p-8">
      <h2 class="text-xl font-bold mb-4">Vérification 2FA</h2>
      <form @submit.prevent="verify" class="space-y-4">
        <input v-model="code" placeholder="Code 6 chiffres" maxlength="6" class="w-full border rounded-lg px-3 py-2 text-center text-2xl tracking-widest" />
        <div v-if="error" class="text-red-600 text-sm">{{ error }}</div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg">Vérifier</button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const code = ref('')
const error = ref('')
const router = useRouter()
const auth = useAuthStore()

async function verify() {
  error.value = ''
  try {
    const { data } = await axios.post('/api/auth/totp/verify', { code: code.value })
    auth.setToken(data.access_token)
    router.push({ name: 'dashboard' })
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Code invalide.'
  }
}
</script>
