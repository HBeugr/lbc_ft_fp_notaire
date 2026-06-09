<template>
  <div class="trigger-banner">
    <div class="trigger-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
    </div>
    <div class="trigger-content">
      <div class="trigger-headline">
        <span class="trigger-code">TRIGGER {{ trigger }}</span>
        <span class="trigger-risk">Risque ÉLEVÉ — Classification forcée</span>
      </div>
      <p class="trigger-desc">{{ description }}</p>
    </div>
    <span v-if="showBadge" class="risk-locked">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
      ÉLEVÉ
    </span>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  trigger?: string
  description?: string
  showBadge?: boolean
}>(), {
  trigger: 'T1',
  description: 'Personne Politiquement Exposée détectée — vigilance renforcée obligatoire. Ce dossier ne peut pas être validé sans complétion du KYC-PPE.',
  showBadge: true,
})
</script>

<style scoped>
.trigger-banner {
  display: flex; align-items: flex-start; gap: 0.875rem;
  background: var(--color-risk-high-bg);
  border: 1.5px solid var(--color-risk-high);
  border-radius: 10px; padding: 0.875rem 1.125rem;
}
.trigger-icon { flex-shrink: 0; margin-top: 1px; }
.trigger-icon svg { width: 20px; height: 20px; stroke: var(--color-risk-high); }
.trigger-content { flex: 1; }
.trigger-headline { display: flex; align-items: center; gap: 0.625rem; margin-bottom: 0.25rem; }
.trigger-code {
  font-size: 0.6875rem; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase;
  background: var(--color-risk-high); color: #fff; border-radius: 4px; padding: 2px 6px;
}
.trigger-risk { font-size: 0.8125rem; font-weight: 700; color: var(--color-risk-high); }
.trigger-desc { font-size: 0.75rem; color: var(--color-risk-high); margin: 0; opacity: 0.85; }
.risk-locked {
  flex-shrink: 0; display: flex; align-items: center; gap: 0.25rem;
  font-size: 0.6875rem; font-weight: 800; letter-spacing: 0.04em;
  color: var(--color-risk-high); background: var(--color-risk-high-bg);
  border: 1.5px solid var(--color-risk-high); border-radius: 6px; padding: 3px 8px;
}
</style>
