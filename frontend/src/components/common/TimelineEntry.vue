<template>
  <div class="timeline-entry" :class="{ 'timeline-entry--last': isLast }">
    <!-- Line -->
    <div class="timeline-line-wrap">
      <div class="timeline-dot" :style="{ borderColor: dotColor, background: dot.filled ? dotColor : 'white' }">
        <svg v-if="dot.icon === 'check'" class="dot-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <svg v-else-if="dot.icon === 'lock'" class="dot-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>
        </svg>
        <svg v-else-if="dot.icon === 'alert'" class="dot-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <svg v-else-if="dot.icon === 'comment'" class="dot-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
      </div>
      <div v-if="!isLast" class="timeline-connector" />
    </div>

    <!-- Content -->
    <div class="timeline-body">
      <div class="timeline-header">
        <span class="timeline-action">{{ action }}</span>
        <span class="timeline-date">{{ formattedDate }}</span>
      </div>
      <p v-if="auteur" class="timeline-meta">
        Par <strong>{{ auteur }}</strong>
        <span v-if="fromStatut && toStatut" class="statut-transition">
          · {{ fromStatut }} <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg> {{ toStatut }}
        </span>
      </p>
      <p v-if="detail" class="timeline-detail">{{ detail }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export type TimelineDotIcon = 'default' | 'check' | 'lock' | 'alert' | 'comment'

export interface TimelineDot {
  icon?: TimelineDotIcon
  color?: string
  filled?: boolean
}

const props = withDefaults(defineProps<{
  action: string
  date: string
  auteur?: string
  fromStatut?: string
  toStatut?: string
  detail?: string
  isLast?: boolean
  dotConfig?: TimelineDot
}>(), {
  isLast: false,
  dotConfig: () => ({ icon: 'default', filled: false }),
})

const dot = computed((): Required<TimelineDot> => ({
  icon:   props.dotConfig?.icon   ?? 'default',
  color:  props.dotConfig?.color  ?? 'var(--color-text-muted)',
  filled: props.dotConfig?.filled ?? false,
}))

const dotColor = computed(() => props.dotConfig?.color ?? 'var(--color-text-muted)')

const formattedDate = computed(() => {
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    }).format(new Date(props.date))
  } catch {
    return props.date
  }
})
</script>

<style scoped>
.timeline-entry { display: flex; gap: 0.75rem; padding-bottom: 1rem; }
.timeline-entry--last { padding-bottom: 0; }

.timeline-line-wrap { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; }

.timeline-dot {
  width: 28px; height: 28px; border-radius: 50%;
  border: 2px solid; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  z-index: 1;
}
.dot-icon { width: 12px; height: 12px; }

.timeline-connector { flex: 1; width: 2px; background: var(--color-border); margin-top: 2px; min-height: 16px; }

.timeline-body { flex: 1; padding-top: 3px; }

.timeline-header { display: flex; align-items: baseline; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.25rem; }
.timeline-action { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); }
.timeline-date   { font-size: 0.6875rem; color: var(--color-text-muted); white-space: nowrap; flex-shrink: 0; }

.timeline-meta { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0 0 0.25rem; display: flex; align-items: center; gap: 0.25rem; flex-wrap: wrap; }
.statut-transition { display: inline-flex; align-items: center; gap: 0.2rem; }
.arrow-icon { width: 12px; height: 12px; stroke: var(--color-text-muted); }

.timeline-detail { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; line-height: 1.5; background: var(--color-bg-page); border-left: 3px solid var(--color-border); padding: 0.375rem 0.625rem; border-radius: 0 6px 6px 0; }
</style>
