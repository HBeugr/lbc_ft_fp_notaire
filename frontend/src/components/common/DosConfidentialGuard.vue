<template>
  <!-- Art. 63 guard — slot content only rendered for authorized roles -->
  <slot v-if="canView" />
  <div v-else class="guard-block">
    <svg class="guard-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0110 0v4"/>
    </svg>
    <div>
      <p class="guard-title">Accès restreint — Art. 63</p>
      <p class="guard-desc">Les informations relatives aux Déclarations d'Opérations Suspectes sont confidentielles et inaccessibles à votre rôle.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const AUTHORIZED_ROLES = ['responsable_conformite', 'notaire_principal', 'admin']

const canView = computed(() =>
  auth.user?.role != null && AUTHORIZED_ROLES.includes(auth.user.role),
)
</script>

<style scoped>
.guard-block {
  display: flex; align-items: flex-start; gap: 0.875rem;
  background: var(--color-status-brouillon-bg);
  border: 1.5px solid var(--color-border);
  border-radius: 10px; padding: 1rem 1.25rem;
}
.guard-icon { width: 28px; height: 28px; flex-shrink: 0; stroke: var(--color-text-muted); margin-top: 2px; }
.guard-title { font-size: 0.875rem; font-weight: 700; color: var(--color-text-secondary); margin: 0 0 0.25rem; }
.guard-desc  { font-size: 0.8125rem; color: var(--color-text-muted); margin: 0; line-height: 1.5; }
</style>
