<template>
  <div class="app-layout">
    <!-- Mobile top bar -->
    <header class="mobile-header">
      <button class="burger-btn" aria-label="Ouvrir le menu" @click="sidebarOpen = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:22px;height:22px">
          <line x1="3" y1="6" x2="21" y2="6"/>
          <line x1="3" y1="12" x2="21" y2="12"/>
          <line x1="3" y1="18" x2="21" y2="18"/>
        </svg>
      </button>

      <!-- Spacer -->
      <div class="mobile-header-spacer" />

      <!-- User info + actions -->
      <div class="mobile-user">
        <div class="mobile-user-avatar">{{ initials }}</div>
        <div class="mobile-user-info">
          <span class="mobile-user-name">{{ fullName }}</span>
          <span class="mobile-user-role">{{ roleLabel }}</span>
        </div>
        <RouterLink
          :to="{ name: 'mon-compte' }"
          class="mobile-action-btn"
          title="Changer mon mot de passe"
          aria-label="Changer mon mot de passe"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0110 0v4"/>
          </svg>
        </RouterLink>
        <button class="mobile-action-btn" title="Se déconnecter" aria-label="Se déconnecter" @click="handleLogout">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- Backdrop overlay (closes sidebar on tap) -->
    <Transition name="fade">
      <div v-if="sidebarOpen" class="sidebar-backdrop" @click="sidebarOpen = false" />
    </Transition>

    <AppSidebar :class="{ 'sidebar--open': sidebarOpen }" @close="sidebarOpen = false" />
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import { useAuthStore } from '@/stores/auth'
import { authService } from '@/services/api'
import { ROLE_LABELS } from '@/utils/roles'

const sidebarOpen = ref(false)
const router = useRouter()
const auth = useAuthStore()

const fullName = computed(() =>
  auth.user ? `${auth.user.first_name} ${auth.user.last_name}` : ''
)

const initials = computed(() => {
  if (!auth.user) return '?'
  return `${auth.user.first_name[0] ?? ''}${auth.user.last_name[0] ?? ''}`.toUpperCase()
})

const roleLabel = computed(() =>
  auth.user ? (ROLE_LABELS[auth.user.role] ?? auth.user.role) : ''
)

async function handleLogout() {
  await authService.logout().catch(() => {})
  auth.clearAuth()
  router.push({ name: 'login' })
}
</script>

<style scoped>
/* Mobile user section */
.mobile-header-spacer {
  flex: 1;
}

.mobile-user {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.mobile-user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-accent-gold);
  color: var(--color-sidebar-bg);
  font-size: 0.6875rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  letter-spacing: 0.02em;
}

.mobile-user-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.2;
}

.mobile-user-name {
  font-size: 0.75rem;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 110px;
}

.mobile-user-role {
  font-size: 0.625rem;
  color: rgba(255, 255, 255, 0.55);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 110px;
}

.mobile-action-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5px;
  border-radius: 6px;
  transition: background 0.12s, color 0.12s;
  flex-shrink: 0;
  text-decoration: none;
}

.mobile-action-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

/* Very small screens — hide name/role, keep avatar + icons */
@media (max-width: 360px) {
  .mobile-user-info { display: none; }
}
</style>
