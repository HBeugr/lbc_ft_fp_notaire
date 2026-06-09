<template>
  <AppLayout>
    <div class="p-6 space-y-5">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-xl font-semibold text-gray-900">Gestion des utilisateurs</h1>
          <p class="text-sm text-gray-500 mt-0.5">{{ users.length }} utilisateur(s) enregistré(s)</p>
        </div>
        <button @click="showCreateModal = true" class="flex items-center gap-2 bg-[#1a2e4a] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#1a2e4a]/90 transition-colors">
          <span>+</span> Nouvel utilisateur
        </button>
      </div>

      <!-- Error banner -->
      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">{{ error }}</div>

      <!-- Table -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div v-if="loading" class="flex items-center justify-center py-12 text-gray-400 text-sm">Chargement…</div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Utilisateur</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Rôle</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Statut</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">2FA</th>
              <th class="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="u in users" :key="u.id" class="hover:bg-gray-50 transition-colors">
              <td class="px-4 py-3">
                <div class="flex items-center gap-3">
                  <div class="w-7 h-7 rounded-full bg-[#1a2e4a] flex items-center justify-center text-white text-xs font-bold uppercase">
                    {{ u.first_name.charAt(0) }}{{ u.last_name.charAt(0) }}
                  </div>
                  <div>
                    <div class="font-medium text-gray-900">{{ u.first_name }} {{ u.last_name }}</div>
                    <div class="text-xs text-gray-500">{{ u.email }}</div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3">
                <span :class="roleBadge(u.role)" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ roleLabel(u.role) }}</span>
              </td>
              <td class="px-4 py-3">
                <span :class="u.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'" class="px-2 py-0.5 rounded-full text-xs font-medium">
                  {{ u.is_active ? 'Actif' : 'Inactif' }}
                </span>
                <span v-if="u.must_change_password" class="ml-1 bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full text-xs">MDP requis</span>
              </td>
              <td class="px-4 py-3">
                <span v-if="u.totp_enabled" class="bg-teal-100 text-teal-700 px-2 py-0.5 rounded-full text-xs font-medium">✓ Activé</span>
                <span v-else-if="u.requires_2fa" class="bg-red-100 text-red-600 px-2 py-0.5 rounded-full text-xs">Non configuré</span>
                <span v-else class="text-gray-400 text-xs">—</span>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-1">
                  <button @click="openEdit(u)" class="p-1.5 rounded-lg text-gray-400 hover:text-[#1a2e4a] hover:bg-gray-100 transition-colors" title="Modifier">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                  </button>
                  <button @click="openResetPassword(u)" class="p-1.5 rounded-lg text-gray-400 hover:text-amber-600 hover:bg-amber-50 transition-colors" title="Réinitialiser MDP">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>
                  </button>
                  <button @click="revokeSessions(u)" class="p-1.5 rounded-lg text-gray-400 hover:text-orange-600 hover:bg-orange-50 transition-colors" title="Révoquer sessions">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/></svg>
                  </button>
                  <button v-if="u.totp_enabled" @click="disableTotp(u)" class="p-1.5 rounded-lg text-gray-400 hover:text-purple-600 hover:bg-purple-50 transition-colors" title="Désactiver 2FA">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
                  </button>
                  <button v-if="u.is_active" @click="deactivateUser(u)" class="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors" title="Désactiver compte">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create / Edit Modal -->
    <div v-if="showCreateModal || showEditModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 class="font-semibold text-gray-900">{{ showEditModal ? 'Modifier l\'utilisateur' : 'Nouvel utilisateur' }}</h2>
          <button @click="closeModals" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="showEditModal ? submitEdit() : submitCreate()" class="p-5 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">Prénom</label>
              <input v-model="form.first_name" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">Nom</label>
              <input v-model="form.last_name" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]" />
            </div>
          </div>
          <div v-if="showCreateModal">
            <label class="block text-xs font-medium text-gray-700 mb-1">Email</label>
            <input v-model="form.email" type="email" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Rôle</label>
            <select v-model="form.role" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]">
              <option value="admin">Administrateur</option>
              <option value="notaire_principal">Notaire Principal</option>
              <option value="responsable_conformite">Resp. Conformité</option>
              <option value="clercs">Clerc</option>
            </select>
          </div>
          <div v-if="showCreateModal">
            <label class="block text-xs font-medium text-gray-700 mb-1">Mot de passe provisoire</label>
            <input v-model="form.password" type="password" required minlength="8" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]" />
          </div>
          <div v-if="showEditModal" class="flex items-center gap-2">
            <input v-model="form.is_active" type="checkbox" id="is_active" class="rounded" />
            <label for="is_active" class="text-sm text-gray-700">Compte actif</label>
          </div>
          <div v-if="modalError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ modalError }}</div>
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" @click="closeModals" class="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">Annuler</button>
            <button type="submit" :disabled="submitting" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm font-medium rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50 transition-colors">
              {{ submitting ? 'Enregistrement…' : (showEditModal ? 'Enregistrer' : 'Créer') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Reset password modal -->
    <div v-if="showResetModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-sm">
        <div class="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 class="font-semibold text-gray-900">Réinitialiser le mot de passe</h2>
          <button @click="showResetModal = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <form @submit.prevent="submitResetPassword" class="p-5 space-y-4">
          <p class="text-sm text-gray-600">Nouveau mot de passe pour <strong>{{ selectedUser?.first_name }} {{ selectedUser?.last_name }}</strong></p>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Nouveau mot de passe</label>
            <input v-model="resetForm.new_password" type="password" required minlength="8" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2e4a]/30 focus:border-[#1a2e4a]" />
          </div>
          <div v-if="modalError" class="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">{{ modalError }}</div>
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" @click="showResetModal = false" class="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">Annuler</button>
            <button type="submit" :disabled="submitting" class="px-4 py-2 bg-[#1a2e4a] text-white text-sm font-medium rounded-lg hover:bg-[#1a2e4a]/90 disabled:opacity-50 transition-colors">
              {{ submitting ? 'Enregistrement…' : 'Réinitialiser' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import axios from 'axios'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

interface UserItem {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
  totp_enabled: boolean
  requires_2fa: boolean
  must_change_password: boolean
}

const auth = useAuthStore()
const users = ref<UserItem[]>([])
const loading = ref(true)
const error = ref('')
const submitting = ref(false)
const modalError = ref('')

const showCreateModal = ref(false)
const showEditModal = ref(false)
const showResetModal = ref(false)
const selectedUser = ref<UserItem | null>(null)

const form = reactive({
  first_name: '',
  last_name: '',
  email: '',
  role: 'clercs' as string,
  password: '',
  is_active: true,
})

const resetForm = reactive({ new_password: '' })

function roleLabel(r: string) {
  const map: Record<string, string> = {
    admin: 'Admin',
    notaire_principal: 'Notaire Principal',
    responsable_conformite: 'Resp. Conformité',
    clercs: 'Clerc',
  }
  return map[r] ?? r
}

function roleBadge(r: string) {
  const map: Record<string, string> = {
    admin: 'bg-purple-100 text-purple-700',
    notaire_principal: 'bg-blue-100 text-blue-700',
    responsable_conformite: 'bg-teal-100 text-teal-700',
    clercs: 'bg-gray-100 text-gray-600',
  }
  return map[r] ?? 'bg-gray-100 text-gray-600'
}

function authHeaders() {
  return auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {}
}

async function loadUsers() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await axios.get('/api/users', { headers: authHeaders() })
    users.value = data.items
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'Erreur lors du chargement.'
  } finally {
    loading.value = false
  }
}

function closeModals() {
  showCreateModal.value = false
  showEditModal.value = false
  modalError.value = ''
  Object.assign(form, { first_name: '', last_name: '', email: '', role: 'clercs', password: '', is_active: true })
}

function openEdit(u: UserItem) {
  selectedUser.value = u
  Object.assign(form, { first_name: u.first_name, last_name: u.last_name, role: u.role, is_active: u.is_active })
  showEditModal.value = true
  modalError.value = ''
}

function openResetPassword(u: UserItem) {
  selectedUser.value = u
  resetForm.new_password = ''
  showResetModal.value = true
  modalError.value = ''
}

async function submitCreate() {
  submitting.value = true
  modalError.value = ''
  try {
    await axios.post('/api/users', {
      email: form.email,
      first_name: form.first_name,
      last_name: form.last_name,
      role: form.role,
      password: form.password,
    }, { headers: authHeaders() })
    closeModals()
    await loadUsers()
  } catch (e: any) {
    modalError.value = e.response?.data?.detail ?? 'Erreur lors de la création.'
  } finally {
    submitting.value = false
  }
}

async function submitEdit() {
  if (!selectedUser.value) return
  submitting.value = true
  modalError.value = ''
  try {
    await axios.patch(`/api/users/${selectedUser.value.id}`, {
      first_name: form.first_name,
      last_name: form.last_name,
      role: form.role,
      is_active: form.is_active,
    }, { headers: authHeaders() })
    closeModals()
    await loadUsers()
  } catch (e: any) {
    modalError.value = e.response?.data?.detail ?? 'Erreur lors de la modification.'
  } finally {
    submitting.value = false
  }
}

async function submitResetPassword() {
  if (!selectedUser.value) return
  submitting.value = true
  modalError.value = ''
  try {
    await axios.post(`/api/admin/users/${selectedUser.value.id}/reset-password`, {
      new_password: resetForm.new_password,
    }, { headers: authHeaders() })
    showResetModal.value = false
  } catch (e: any) {
    modalError.value = e.response?.data?.detail ?? 'Erreur lors de la réinitialisation.'
  } finally {
    submitting.value = false
  }
}

async function revokeSessions(u: UserItem) {
  if (!confirm(`Révoquer toutes les sessions de ${u.first_name} ${u.last_name} ?`)) return
  try {
    await axios.post(`/api/admin/users/${u.id}/revoke-sessions`, null, { headers: authHeaders() })
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'Erreur lors de la révocation.'
  }
}

async function disableTotp(u: UserItem) {
  if (!confirm(`Désactiver le 2FA de ${u.first_name} ${u.last_name} ?`)) return
  try {
    await axios.delete(`/api/admin/users/${u.id}/totp`, { headers: authHeaders() })
    await loadUsers()
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'Erreur lors de la désactivation du 2FA.'
  }
}

async function deactivateUser(u: UserItem) {
  if (!confirm(`Désactiver le compte de ${u.first_name} ${u.last_name} ?`)) return
  try {
    await axios.delete(`/api/users/${u.id}`, { headers: authHeaders() })
    await loadUsers()
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'Erreur lors de la désactivation.'
  }
}

onMounted(loadUsers)
</script>
