<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="w-full max-w-md bg-white rounded-xl shadow-lg p-8">
      <h1 class="text-2xl font-bold text-center mb-6">Notaire — Conformité LBC/FT/FP</h1>
      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Email</label>
          <input v-model="email" type="email" required class="mt-1 block w-full border rounded-lg px-3 py-2" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Mot de passe</label>
          <input v-model="password" type="password" required class="mt-1 block w-full border rounded-lg px-3 py-2" />
        </div>
        <div v-if="error" class="text-red-600 text-sm">{{ error }}</div>
        <button type="submit" :disabled="loading" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50">
          {{ loading ? 'Connexion...' : 'Se connecter' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const router = useRouter()
const auth = useAuthStore()

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await axios.post('/api/auth/login', { email: email.value, password: password.value }, { withCredentials: true })
    auth.setToken(data.access_token)
    auth.setUser(data.user)
    if (data.totp_pending) {
      router.push({ name: '2fa-verify' })
    } else {
      router.push({ name: 'dashboard' })
    }
  } catch (err: any) {
    error.value = err.response?.data?.message || err.response?.data?.detail || 'Erreur de connexion.'
  } finally {
    loading.value = false
  }
}
</script>
