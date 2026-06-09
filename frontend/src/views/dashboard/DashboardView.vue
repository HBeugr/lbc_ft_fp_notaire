<template>
  <AppLayout>
    <div class="p-6 space-y-6">
      <!-- Welcome banner -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4">
        <div class="w-12 h-12 rounded-full bg-[#1a2e4a] flex items-center justify-center text-white font-bold text-lg uppercase">
          {{ initials }}
        </div>
        <div>
          <h1 class="text-lg font-semibold text-gray-900">
            Bonjour, {{ user?.first_name }} {{ user?.last_name }}
          </h1>
          <p class="text-sm text-gray-500">
            <span :class="roleBadgeClass" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium mr-2">{{ roleLabel }}</span>
            {{ today }}
          </p>
        </div>
        <div v-if="user?.must_change_password" class="ml-auto flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-700 text-sm px-4 py-2 rounded-lg">
          <span>⚠️</span>
          <span>Vous devez changer votre mot de passe.</span>
          <RouterLink to="/settings/password" class="underline font-medium">Modifier</RouterLink>
        </div>
        <div v-else-if="user?.requires_2fa && !user?.totp_enabled" class="ml-auto flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2 rounded-lg">
          <span>🔐</span>
          <span>Configuration 2FA requise.</span>
          <RouterLink to="/2fa/setup" class="underline font-medium">Configurer</RouterLink>
        </div>
      </div>

      <!-- Stats grid -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          v-for="stat in stats"
          :key="stat.label"
          class="bg-white rounded-xl border border-gray-200 p-4 flex items-start gap-3"
        >
          <div :class="stat.iconBg" class="w-10 h-10 rounded-lg flex items-center justify-center text-lg flex-shrink-0">
            {{ stat.icon }}
          </div>
          <div>
            <div class="text-2xl font-bold text-gray-900">{{ stat.value }}</div>
            <div class="text-xs text-gray-500 leading-tight">{{ stat.label }}</div>
          </div>
        </div>
      </div>

      <!-- Quick actions -->
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <h2 class="text-sm font-semibold text-gray-700 mb-4">Accès rapide</h2>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
          <RouterLink
            v-for="action in quickActions"
            :key="action.to"
            :to="action.to"
            class="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:border-[#1a2e4a] hover:bg-[#1a2e4a]/5 transition-colors group"
          >
            <span class="text-xl">{{ action.icon }}</span>
            <span class="text-sm font-medium text-gray-700 group-hover:text-[#1a2e4a]">{{ action.label }}</span>
          </RouterLink>
        </div>
      </div>

      <!-- Réglementation reminder -->
      <div class="bg-[#1a2e4a]/5 border border-[#1a2e4a]/20 rounded-xl p-4 text-sm text-[#1a2e4a]">
        <p class="font-medium">Cadre réglementaire — Ordonnance n° 2023-875</p>
        <p class="mt-1 text-[#1a2e4a]/70">
          Seuil espèces Art. 72 : <strong>15 000 000 FCFA</strong> · Révision KYC Art. 19 : FAIBLE 5 ans · MOYEN 3 ans · ÉLEVÉ 2 ans · Conservation Art. 23 : 10 ans
        </p>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const user = computed(() => auth.user)
const role = computed(() => auth.role)

const today = computed(() => {
  return new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
})

const initials = computed(() => {
  const u = user.value
  if (!u) return '?'
  return `${u.first_name.charAt(0)}${u.last_name.charAt(0)}`.toUpperCase()
})

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    admin: 'Administrateur',
    notaire_principal: 'Notaire Principal',
    responsable_conformite: 'Resp. Conformité',
    clercs: 'Clerc',
  }
  return map[role.value ?? ''] ?? ''
})

const roleBadgeClass = computed(() => {
  const map: Record<string, string> = {
    admin: 'bg-purple-100 text-purple-700',
    notaire_principal: 'bg-blue-100 text-blue-700',
    responsable_conformite: 'bg-teal-100 text-teal-700',
    clercs: 'bg-gray-100 text-gray-600',
  }
  return map[role.value ?? ''] ?? 'bg-gray-100 text-gray-600'
})

const stats = [
  { label: 'Dossiers actifs', value: '—', icon: '📁', iconBg: 'bg-blue-50' },
  { label: 'Alertes en cours', value: '—', icon: '🔔', iconBg: 'bg-amber-50' },
  { label: 'Révisions en retard', value: '—', icon: '🔄', iconBg: 'bg-red-50' },
  { label: 'DOS en attente', value: '—', icon: '🚨', iconBg: 'bg-orange-50' },
]

const allQuickActions = [
  { to: '/dossiers', label: 'Nouveau dossier', icon: '➕', roles: null },
  { to: '/dossiers', label: 'Mes dossiers', icon: '📁', roles: null },
  { to: '/alertes', label: 'Alertes', icon: '🔔', roles: null },
  { to: '/revisions', label: 'Révisions KYC', icon: '🔄', roles: null },
  { to: '/dos', label: 'Décl. suspicion', icon: '🚨', roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
  { to: '/registres', label: 'Registres', icon: '📋', roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
  { to: '/rapports', label: 'Rapports', icon: '📊', roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
  { to: '/admin', label: 'Utilisateurs', icon: '👥', roles: ['admin'] },
]

const quickActions = computed(() =>
  allQuickActions.filter(a => !a.roles || a.roles.includes(role.value ?? ''))
)
</script>
