<template>
  <div class="app-layout">
    <aside class="sidebar" role="navigation" aria-label="Navigation console d'exploitation">
      <div class="sidebar-logo">
        <div class="logo-mark">⚙</div>
        <div class="logo-text">
          <span class="logo-title">EXPLOITATION</span>
          <span class="logo-sub">CONSOLE PLATEFORME</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <RouterLink :to="{ name: 'super-admin-tenants' }" class="nav-item" active-class="nav-item--active">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6"/>
          </svg>
          <span class="nav-label">Cabinets</span>
        </RouterLink>
        <RouterLink :to="{ name: 'super-admin-audit' }" class="nav-item" active-class="nav-item--active">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <span class="nav-label">Journal d'exploitation</span>
        </RouterLink>
      </nav>

      <div class="sidebar-spacer" />

      <div class="sidebar-footer">
        <div class="user-avatar" :title="store.fullName">{{ initials }}</div>
        <div class="user-info">
          <p class="user-name">{{ store.fullName }}</p>
          <p class="user-role">Super-Administrateur</p>
        </div>
        <button class="logout-btn" title="Se déconnecter" aria-label="Se déconnecter" @click="handleLogout">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </aside>

    <main class="main-content">
      <!-- Rappel tant que le mot de passe initial n'a pas été changé -->
      <div v-if="store.mustChangePassword" class="banner-warning">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        Votre mot de passe est encore le mot de passe initial. Changez-le dès que possible.
      </div>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useSuperAdminStore } from '@/stores/superAdmin'

const router = useRouter()
const store = useSuperAdminStore()

const initials = computed(() => {
  const a = store.superAdmin
  if (!a) return '?'
  return `${a.first_name[0] ?? ''}${a.last_name[0] ?? ''}`.toUpperCase()
})

function handleLogout() {
  store.clearSession()
  router.push({ name: 'super-admin-login' })
}
</script>

<style scoped>
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 0.5rem;
}
.logo-mark { font-size: 1.375rem; color: var(--color-accent-gold); line-height: 1; }
.logo-text { display: flex; flex-direction: column; line-height: 1.2; }
.logo-title { font-size: 0.9375rem; font-weight: 700; color: #fff; letter-spacing: 0.02em; }
.logo-sub {
  font-size: 0.6875rem;
  color: rgba(255, 255, 255, 0.45);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.sidebar-nav { display: flex; flex-direction: column; gap: 2px; padding: 0 0.5rem; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5625rem 0.75rem;
  border-radius: 7px;
  color: rgba(255, 255, 255, 0.62);
  text-decoration: none;
  font-size: 0.8125rem;
  font-weight: 450;
  transition: background 0.12s, color 0.12s;
}
.nav-item:hover { background: rgba(255, 255, 255, 0.07); color: rgba(255, 255, 255, 0.9); }
.nav-item--active {
  background: rgba(201, 162, 39, 0.14);
  color: var(--color-accent-gold);
  font-weight: 600;
}
.nav-item--active .nav-icon { stroke: var(--color-accent-gold); }
.nav-icon { width: 16px; height: 16px; flex-shrink: 0; stroke: currentColor; }
.nav-label { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.sidebar-spacer { flex: 1; }

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin: 0 0 0.25rem;
}
.user-avatar {
  width: 32px; height: 32px;
  border-radius: 50%;
  background: rgba(201, 162, 39, 0.2);
  color: var(--color-accent-gold);
  font-size: 0.6875rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.user-info { flex: 1; min-width: 0; }
.user-name {
  font-size: 0.8125rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin: 0; line-height: 1.3;
}
.user-role { font-size: 0.6875rem; color: rgba(255, 255, 255, 0.42); margin: 0; line-height: 1.3; }
.logout-btn {
  background: none; border: none; cursor: pointer;
  color: rgba(255, 255, 255, 0.35);
  display: flex; align-items: center;
  padding: 4px; border-radius: 5px;
  transition: color 0.12s, background 0.12s;
  flex-shrink: 0;
}
.logout-btn:hover { color: rgba(255, 255, 255, 0.75); background: rgba(255, 255, 255, 0.08); }
.logout-btn svg { width: 15px; height: 15px; }

.banner-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--color-risk-medium-bg);
  color: var(--color-risk-medium);
  border: 1px solid rgba(217, 119, 6, 0.2);
  border-radius: 8px;
  padding: 0.625rem 0.875rem;
  font-size: 0.8125rem;
  margin-bottom: 1.25rem;
}
.banner-warning svg { width: 16px; height: 16px; flex-shrink: 0; }
</style>
