<template>
  <span class="risk-badge" :class="badgeClass">
    <svg v-if="niveau === 'ÉLEVÉ'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
    <svg v-else-if="niveau === 'MOYEN'" class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
    <svg v-else class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
    {{ niveau }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ niveau: 'FAIBLE' | 'MOYEN' | 'ÉLEVÉ' | string }>()

const badgeClass = computed(() => ({
  'risk-badge--low':    props.niveau === 'FAIBLE',
  'risk-badge--medium': props.niveau === 'MOYEN',
  'risk-badge--high':   props.niveau === 'ÉLEVÉ',
}))
</script>

<style scoped>
.risk-badge {
  display: inline-flex; align-items: center; gap: 0.3rem;
  font-size: 0.6875rem; font-weight: 800; letter-spacing: 0.06em;
  text-transform: uppercase; border-radius: 6px;
  padding: 3px 8px; white-space: nowrap;
}
.badge-icon { width: 12px; height: 12px; flex-shrink: 0; }
.risk-badge--low    { background: var(--color-risk-low-bg);    color: var(--color-risk-low); }
.risk-badge--medium { background: var(--color-risk-medium-bg); color: var(--color-risk-medium); }
.risk-badge--high   { background: var(--color-risk-high-bg);   color: var(--color-risk-high); }
</style>
