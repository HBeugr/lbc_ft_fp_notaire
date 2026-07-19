<template>
  <aside class="sidebar" role="navigation" aria-label="Navigation principale">
    <!-- Logo -->
    <div class="sidebar-logo">
      <!--
        Zone de taille fixe : `object-fit: contain` garantit qu'un logo très large
        ou très haut n'écrase jamais la mise en page de la barre latérale.
        Sans logo défini, on garde l'icône générique.
      -->
      <img
        v-if="branding.logoUrl"
        class="logo-img"
        :src="branding.logoUrl"
        :alt="`Logo — ${cabinetName}`"
      />
      <div v-else class="logo-mark">⚖</div>
      <div class="logo-text">
        <span class="logo-title" :title="cabinetName">{{ cabinetName }}</span>
        <span class="logo-sub">LBC/FT/FP — CONFORMITÉ NOTARIALE</span>
      </div>
      <button class="sidebar-close-btn" aria-label="Fermer le menu" @click="emit('close')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>

    <!-- Navigation -->
    <nav class="sidebar-nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="{ name: item.to }"
        class="nav-item"
        active-class=""
        exact-active-class="nav-item--active"
        @click="emit('close')"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path :d="item.icon" />
        </svg>
        <span class="nav-label">{{ item.label }}</span>
        <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
      </RouterLink>
    </nav>

    <!-- Spacer -->
    <div class="sidebar-spacer" />

    <!-- User footer -->
    <div class="sidebar-footer">
      <div class="user-avatar" :title="fullName">
        {{ initials }}
      </div>
      <div class="user-info">
        <p class="user-name">{{ fullName }}</p>
        <p class="user-role">{{ roleLabel }}</p>
      </div>
      <RouterLink
        :to="{ name: 'mon-compte' }"
        class="logout-btn"
        title="Changer mon mot de passe"
        aria-label="Changer mon mot de passe"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0110 0v4"/>
        </svg>
      </RouterLink>
      <button class="logout-btn" title="Se déconnecter" aria-label="Se déconnecter" @click="handleLogout">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
          <polyline points="16 17 21 12 16 7"/>
          <line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useBrandingStore } from '@/stores/branding'
import { authService } from '@/services/api'
import { useNav } from '@/composables/useNav'
import { ROLE_LABELS } from '@/utils/roles'

const emit = defineEmits<{ close: [] }>()

const router = useRouter()
const auth = useAuthStore()
const branding = useBrandingStore()
const { navItems } = useNav()

// Branding par cabinet : le nom du tenant remplace l'ancien libellé en dur.
const cabinetName = computed(() => auth.tenantName ?? 'LBC/FT/FP')

/**
 * Le bloc `tenant` renvoyé par le login ne porte pas l'horodatage du logo : juste
 * après une connexion, l'information vaut `undefined` (inconnue) et non `null`
 * (pas de logo). On complète alors depuis /tenant/me, sinon le logo n'apparaîtrait
 * qu'au rechargement de la page.
 */
onMounted(() => {
  if (auth.isAuthenticated && auth.tenantLogoUpdatedAt === undefined) {
    auth.fetchTenant()
  }
})

// Le logo suit l'horodatage : un envoi depuis Paramètres le rafraîchit ici sans
// rechargement. À la déconnexion, l'URL d'objet est révoquée.
watch(
  () => (auth.isAuthenticated ? auth.tenantLogoUpdatedAt : null),
  (version) => { branding.charger(version) },
  { immediate: true },
)

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
/* ── Logo ── */
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 0.5rem;
}

.logo-mark {
  font-size: 1.375rem;
  color: var(--color-accent-gold);
  line-height: 1;
}

/* Logo du cabinet : gabarit fixe, l'image s'y inscrit sans jamais le déformer. */
.logo-img {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  object-fit: contain;
  border-radius: 4px;
  display: block;
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  min-width: 0; /* autorise l'ellipse sur un nom de cabinet long */
}

.logo-title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logo-sub {
  font-size: 0.6875rem;
  color: rgba(255, 255, 255, 0.45);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Nav ── */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 0.5rem;
}

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
  position: relative;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.07);
  color: rgba(255, 255, 255, 0.9);
}

.nav-item--active {
  background: rgba(201, 162, 39, 0.14);
  color: var(--color-accent-gold);
  font-weight: 600;
}

.nav-item--active .nav-icon {
  stroke: var(--color-accent-gold);
}

.nav-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  stroke: currentColor;
}

.nav-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-badge {
  background: var(--color-risk-high);
  color: #fff;
  font-size: 0.625rem;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
  flex-shrink: 0;
}

/* ── Spacer ── */
.sidebar-spacer {
  flex: 1;
}

/* ── Footer ── */
.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin: 0 0 0.25rem;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(201, 162, 39, 0.2);
  color: var(--color-accent-gold);
  font-size: 0.6875rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  letter-spacing: 0.02em;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 0.8125rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
  line-height: 1.3;
}

.user-role {
  font-size: 0.6875rem;
  color: rgba(255, 255, 255, 0.42);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
  line-height: 1.3;
}

.logout-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.35);
  display: flex;
  align-items: center;
  padding: 4px;
  border-radius: 5px;
  transition: color 0.12s, background 0.12s;
  flex-shrink: 0;
}

.logout-btn:hover {
  color: rgba(255, 255, 255, 0.75);
  background: rgba(255, 255, 255, 0.08);
}

.logout-btn svg {
  width: 15px;
  height: 15px;
}

/* Mobile close button — hidden on desktop */
.sidebar-close-btn {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  padding: 4px;
  border-radius: 5px;
  margin-left: auto;
  flex-shrink: 0;
  transition: color 0.12s;
}

.sidebar-close-btn svg {
  width: 16px;
  height: 16px;
  display: block;
}

.sidebar-close-btn:hover {
  color: rgba(255, 255, 255, 0.9);
}

@media (max-width: 768px) {
  .sidebar-close-btn {
    display: flex;
    align-items: center;
  }
}
</style>
