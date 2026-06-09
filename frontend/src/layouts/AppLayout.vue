<template>
  <div class="flex h-screen bg-gray-50 overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-64 flex-shrink-0 flex flex-col bg-[#1a2e4a] text-white">
      <!-- Logo -->
      <div class="flex items-center gap-3 px-5 py-5 border-b border-white/10">
        <div class="w-8 h-8 rounded-lg bg-[#e8b84b] flex items-center justify-center text-[#1a2e4a] font-bold text-sm">N</div>
        <div>
          <div class="font-semibold text-sm leading-tight">Notaire LBC/FT</div>
          <div class="text-xs text-white/50 leading-tight">Conformité</div>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        <RouterLink
          v-for="item in visibleNav"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/10 transition-colors"
          active-class="!text-white !bg-white/15 font-medium"
        >
          <span class="text-base leading-none">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <!-- User footer -->
      <div class="px-4 py-4 border-t border-white/10">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-[#e8b84b] flex items-center justify-center text-[#1a2e4a] font-bold text-xs uppercase">
            {{ initials }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium leading-tight truncate">{{ user?.first_name }} {{ user?.last_name }}</div>
            <div class="text-xs text-white/50 truncate">{{ roleLabel }}</div>
          </div>
          <button @click="handleLogout" class="text-white/40 hover:text-white/80 transition-colors p-1" title="Déconnexion">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- Main content -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Top bar -->
      <header class="flex-shrink-0 h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
        <div class="text-sm font-medium text-gray-700">{{ pageTitle }}</div>
        <div class="flex items-center gap-3">
          <span :class="roleBadgeClass" class="px-2.5 py-1 rounded-full text-xs font-medium">{{ roleLabel }}</span>
          <div class="w-8 h-8 rounded-full bg-[#1a2e4a] flex items-center justify-center text-white text-xs font-bold uppercase">
            {{ initials }}
          </div>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const user = computed(() => auth.user)
const role = computed(() => auth.role)

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
  return map[role.value ?? ''] ?? role.value ?? ''
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

type NavItem = { to: string; label: string; icon: string; roles?: string[] }

const allNav: NavItem[] = [
  { to: '/dashboard', label: 'Tableau de bord', icon: '🏠' },
  { to: '/dossiers', label: 'Dossiers', icon: '📁' },
  { to: '/alertes', label: 'Alertes', icon: '🔔' },
  { to: '/dos', label: 'Décl. Suspicion', icon: '🚨', roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
  { to: '/registres', label: 'Registres légaux', icon: '📋', roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
  { to: '/revisions', label: 'Révisions KYC', icon: '🔄' },
  { to: '/rapports', label: 'Rapports', icon: '📊', roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
  { to: '/admin', label: 'Administration', icon: '⚙️', roles: ['admin'] },
]

const visibleNav = computed(() =>
  allNav.filter(item => !item.roles || item.roles.includes(role.value ?? ''))
)

const pageTitle = computed(() => {
  const labels: Record<string, string> = {
    dashboard: 'Tableau de bord',
    dossiers: 'Dossiers clients',
    'dossier-detail': 'Détail dossier',
    alertes: 'Alertes',
    dos: 'Déclarations de Soupçon',
    registres: 'Registres légaux',
    revisions: 'Révisions KYC',
    rapports: 'Rapports & Statistiques',
    admin: 'Administration',
  }
  return labels[route.name as string] ?? ''
})

async function handleLogout() {
  try { await axios.post('/api/auth/logout', null, { withCredentials: true }) } catch {}
  auth.clearAuth()
  router.push({ name: 'login' })
}
</script>
