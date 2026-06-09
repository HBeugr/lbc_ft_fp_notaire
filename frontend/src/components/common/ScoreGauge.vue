<template>
  <div class="score-gauge">
    <!-- Gauge arc SVG -->
    <div class="gauge-wrap">
      <svg class="gauge-svg" viewBox="0 0 120 72" fill="none">
        <!-- Track -->
        <path d="M10 66 A52 52 0 0 1 110 66" stroke="var(--color-border)" stroke-width="10" stroke-linecap="round"/>
        <!-- Low zone (0–7) -->
        <path d="M10 66 A52 52 0 0 1 110 66" stroke="var(--color-risk-low)" stroke-width="10"
              stroke-linecap="round" stroke-dasharray="163.4" :stroke-dashoffset="163.4 - lowLen" opacity="0.25"/>
        <!-- Medium zone (8–13) -->
        <path d="M10 66 A52 52 0 0 1 110 66" stroke="var(--color-risk-medium)" stroke-width="10"
              stroke-linecap="round" stroke-dasharray="163.4" :stroke-dashoffset="163.4 - mediumLen" opacity="0.25"/>
        <!-- High zone (14–20) -->
        <path d="M10 66 A52 52 0 0 1 110 66" stroke="var(--color-risk-high)" stroke-width="10"
              stroke-linecap="round" stroke-dasharray="163.4" :stroke-dashoffset="163.4 - highLen" opacity="0.25"/>
        <!-- Score fill -->
        <path d="M10 66 A52 52 0 0 1 110 66" :stroke="fillColor" stroke-width="10"
              stroke-linecap="round" stroke-dasharray="163.4" :stroke-dashoffset="163.4 - scoreFill"
              style="transition: stroke-dashoffset 0.6s ease"/>
        <!-- Needle -->
        <line
          :x1="60" :y1="66"
          :x2="needleX" :y2="needleY"
          stroke="var(--color-text-primary)" stroke-width="2" stroke-linecap="round"
          style="transition: x2 0.6s ease, y2 0.6s ease"
        />
        <circle cx="60" cy="66" r="4" fill="var(--color-text-primary)"/>
      </svg>
      <!-- Score value -->
      <div class="gauge-score">
        <span class="score-value" :style="{ color: fillColor }">{{ score }}</span>
        <span class="score-max">/20</span>
      </div>
    </div>

    <!-- Level badge -->
    <div class="gauge-level">
      <RiskBadge :niveau="niveau" />
    </div>

    <!-- Axes breakdown (shown only when showAxes is true) -->
    <div v-if="showAxes && axes.length" class="axes-grid">
      <div v-for="axe in axes" :key="axe.label" class="axe-row">
        <span class="axe-label">{{ axe.label }}</span>
        <div class="axe-bar-track">
          <div class="axe-bar" :style="{ width: `${(axe.valeur / axe.max) * 100}%`, background: fillColor }" />
        </div>
        <span class="axe-val">{{ axe.valeur }}/{{ axe.max }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import RiskBadge from './RiskBadge.vue'

export interface ScoreAxe {
  label: string
  valeur: number
  max: number
}

const props = withDefaults(defineProps<{
  score: number
  axes?: ScoreAxe[]
  showAxes?: boolean
}>(), {
  axes: () => [],
  showAxes: false,
})

// Gauge arc total length ≈ 163.4 (half-circle r=52, π*52)
const ARC_LEN = 163.4

const niveau = computed(() => {
  if (props.score <= 7)  return 'FAIBLE'
  if (props.score <= 13) return 'MOYEN'
  return 'ÉLEVÉ'
})

const fillColor = computed(() => {
  if (props.score <= 7)  return 'var(--color-risk-low)'
  if (props.score <= 13) return 'var(--color-risk-medium)'
  return 'var(--color-risk-high)'
})

const scoreFill  = computed(() => (props.score / 20) * ARC_LEN)
const lowLen     = computed(() => (7  / 20) * ARC_LEN)
const mediumLen  = computed(() => (13 / 20) * ARC_LEN)
const highLen    = computed(() => ARC_LEN)

// Needle — maps score 0-20 to angle 180°-0° along the half-circle
const needleAngle = computed(() => 180 - (props.score / 20) * 180)
const needleX = computed(() => 60 + 44 * Math.cos((needleAngle.value * Math.PI) / 180))
const needleY = computed(() => 66 - 44 * Math.sin((needleAngle.value * Math.PI) / 180))
</script>

<style scoped>
.score-gauge { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.gauge-wrap { position: relative; width: 140px; }
.gauge-svg  { width: 100%; display: block; }
.gauge-score {
  position: absolute; bottom: 4px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: baseline; gap: 2px;
}
.score-value { font-size: 1.625rem; font-weight: 800; line-height: 1; }
.score-max   { font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; }
.gauge-level { margin-top: -0.25rem; }

/* Axes */
.axes-grid { width: 100%; display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.5rem; }
.axe-row   { display: grid; grid-template-columns: 1fr 80px 36px; align-items: center; gap: 0.5rem; }
.axe-label { font-size: 0.6875rem; color: var(--color-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.axe-bar-track { height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; }
.axe-bar       { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.axe-val { font-size: 0.6875rem; font-weight: 600; color: var(--color-text-secondary); text-align: right; }
</style>
