<template>
  <!-- Bandeau global : le cabinet n'est pas en production (suspendu / configuration / archivé). -->
  <div v-if="visible" class="tenant-banner" :class="`tenant-banner--${statut}`" role="status">
    <svg class="banner-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
    <span class="banner-text">
      <strong>{{ label }}</strong>
      <template v-if="auth.tenantMessage"> — {{ auth.tenantMessage }}</template>
    </span>
    <RouterLink
      v-if="route.name !== 'compte-suspendu'"
      :to="{ name: 'compte-suspendu' }"
      class="banner-link"
    >
      En savoir plus
    </RouterLink>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()

const statut = computed(() => auth.tenant?.statut ?? null)

// Rien à signaler tant que l'utilisateur n'est pas identifié ou que tout va bien.
// On s'appuie sur `tenantBlocked` (session identifiée + cabinet hors production)
// et non sur `isAuthenticated` : l'API refuse de renouveler le jeton d'accès d'un
// cabinet bloqué, donc exiger un jeton masquerait le bandeau précisément dans le
// cas qu'il doit signaler.
const visible = computed(() => auth.tenantBlocked)

const LABELS: Record<string, string> = {
  configuration: 'Cabinet en cours de configuration — accès limité',
  suspendu: 'Cabinet suspendu — accès à la plateforme bloqué',
  archive: 'Cabinet archivé — accès en lecture impossible',
}
const label = computed(() => (statut.value ? LABELS[statut.value] ?? '' : ''))
</script>

<style scoped>
/* Bandeau en flux (et non fixed) : il pousse la mise en page vers le bas
   au lieu de recouvrir la barre latérale, qui est elle-même en position fixe. */
.tenant-banner {
  position: relative;
  z-index: 60;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.8125rem;
  line-height: 1.4;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
}
.tenant-banner--suspendu { background: var(--color-risk-high); color: #fff; }
.tenant-banner--configuration { background: var(--color-risk-medium); color: #fff; }
.tenant-banner--archive { background: var(--color-status-cloture); color: #fff; }

.banner-icon { width: 16px; height: 16px; flex-shrink: 0; }
.banner-text { flex: 1; min-width: 0; }

.banner-link {
  flex-shrink: 0;
  color: #fff;
  font-weight: 600;
  text-decoration: underline;
  font-size: 0.75rem;
}
.banner-link:hover { opacity: 0.85; }
</style>
