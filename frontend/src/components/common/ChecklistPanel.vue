<template>
  <div class="checklist-panel">
    <div class="checklist-header">
      <div class="checklist-title-row">
        <h3 class="checklist-title">Complétude du dossier</h3>
        <span class="checklist-pct" :class="pctClass">{{ pct }}%</span>
      </div>
      <div class="progress-bar-track">
        <div class="progress-bar-fill" :class="pctClass" :style="{ width: `${pct}%` }" />
      </div>
    </div>

    <ul class="checklist-list">
      <li v-for="item in items" :key="item.id" class="checklist-item" :class="itemClass(item)">
        <span class="item-status-icon">
          <svg v-if="item.statut === 'ok'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <svg v-else-if="item.statut === 'manquant'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        </span>
        <span class="item-label">{{ item.label }}</span>
        <span class="item-tag" :class="tagClass(item)">
          {{ item.statut === 'ok' ? 'OK' : item.statut === 'manquant' ? 'Manquant' : 'Bloquant' }}
        </span>
      </li>
    </ul>

    <!-- Submit blocker tooltip -->
    <div v-if="bloquants.length" class="submit-blocker">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="blocker-icon">
        <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>
      </svg>
      <div>
        <p class="blocker-title">Soumission bloquée</p>
        <p class="blocker-desc">{{ bloquants.length }} document{{ bloquants.length > 1 ? 's' : '' }} obligatoire{{ bloquants.length > 1 ? 's' : '' }} manquant{{ bloquants.length > 1 ? 's' : '' }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export type ChecklistStatut = 'ok' | 'manquant' | 'bloquant'

export interface ChecklistItem {
  id: string
  label: string
  statut: ChecklistStatut
  obligatoire?: boolean
}

const props = defineProps<{ items: ChecklistItem[] }>()

const ok       = computed(() => props.items.filter(i => i.statut === 'ok'))
const bloquants = computed(() => props.items.filter(i => i.statut === 'bloquant'))
const pct      = computed(() => props.items.length === 0 ? 0 : Math.round((ok.value.length / props.items.length) * 100))

const pctClass = computed(() => {
  if (pct.value === 100) return 'pct--ok'
  if (pct.value >= 60)   return 'pct--medium'
  return 'pct--low'
})

function itemClass(item: ChecklistItem) {
  return {
    'item--ok':       item.statut === 'ok',
    'item--manquant': item.statut === 'manquant',
    'item--bloquant': item.statut === 'bloquant',
  }
}
function tagClass(item: ChecklistItem) {
  return {
    'tag--ok':       item.statut === 'ok',
    'tag--manquant': item.statut === 'manquant',
    'tag--bloquant': item.statut === 'bloquant',
  }
}
</script>

<style scoped>
.checklist-panel {
  background: var(--color-bg-card); border: 1px solid var(--color-border);
  border-radius: 10px; padding: 1rem 1.125rem; display: flex; flex-direction: column; gap: 0.875rem;
}

.checklist-header { display: flex; flex-direction: column; gap: 0.5rem; }
.checklist-title-row { display: flex; align-items: center; justify-content: space-between; }
.checklist-title { font-size: 0.875rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }

.checklist-pct { font-size: 1rem; font-weight: 800; }
.pct--ok     { color: var(--color-risk-low); }
.pct--medium { color: var(--color-risk-medium); }
.pct--low    { color: var(--color-risk-high); }

.progress-bar-track { height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; }
.progress-bar-fill  { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.progress-bar-fill.pct--ok     { background: var(--color-risk-low); }
.progress-bar-fill.pct--medium { background: var(--color-risk-medium); }
.progress-bar-fill.pct--low    { background: var(--color-risk-high); }

.checklist-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.375rem; }

.checklist-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.375rem 0.5rem; border-radius: 6px;
  font-size: 0.8125rem;
}
.item--ok       { background: var(--color-risk-low-bg); }
.item--manquant { background: var(--color-risk-medium-bg); }
.item--bloquant { background: var(--color-risk-high-bg); }

.item-status-icon { flex-shrink: 0; width: 16px; height: 16px; }
.item-status-icon svg { width: 100%; height: 100%; }
.item--ok       .item-status-icon svg { stroke: var(--color-risk-low); }
.item--manquant .item-status-icon svg { stroke: var(--color-risk-medium); }
.item--bloquant .item-status-icon svg { stroke: var(--color-risk-high); }

.item-label { flex: 1; color: var(--color-text-primary); }
.item-tag {
  font-size: 0.6875rem; font-weight: 700; border-radius: 4px;
  padding: 1px 6px; text-transform: uppercase; letter-spacing: 0.04em;
}
.tag--ok       { background: var(--color-risk-low);    color: #fff; }
.tag--manquant { background: var(--color-risk-medium);  color: #fff; }
.tag--bloquant { background: var(--color-risk-high);    color: #fff; }

.submit-blocker {
  display: flex; align-items: flex-start; gap: 0.625rem;
  background: var(--color-risk-high-bg); border: 1px solid rgba(220,38,38,0.3);
  border-radius: 8px; padding: 0.625rem 0.75rem;
}
.blocker-icon { width: 16px; height: 16px; flex-shrink: 0; stroke: var(--color-risk-high); margin-top: 2px; }
.blocker-title { font-size: 0.8125rem; font-weight: 700; color: var(--color-risk-high); margin: 0 0 1px; }
.blocker-desc  { font-size: 0.75rem; color: var(--color-risk-high); margin: 0; opacity: 0.85; }
</style>
