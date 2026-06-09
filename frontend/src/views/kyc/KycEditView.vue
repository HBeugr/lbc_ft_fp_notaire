<template>
  <div class="kyc-edit-page">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <button class="breadcrumb-link" @click="router.push({ name: 'kyc-list' })">Dossiers KYC</button>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="breadcrumb-sep"><polyline points="9 18 15 12 9 6"/></svg>
          <button class="breadcrumb-link" @click="router.push({ name: 'kyc-detail', params: { id: dossierId } })">{{ dossier?.reference ?? '…' }}</button>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="breadcrumb-sep"><polyline points="9 18 15 12 9 6"/></svg>
          <span>Formulaire KYC</span>
        </div>
        <h1 class="page-title">
          {{ dossier?.type_client === 'PP' ? 'Formulaire KYC — Personne physique' : 'Formulaire KYC — Personne morale' }}
        </h1>
        <p class="page-subtitle">{{ dossier?.reference }}</p>
      </div>
    </div>

    <div v-if="loading" class="card loading-card">Chargement…</div>
    <div v-else-if="error" class="card error-card">{{ error }}</div>
    <template v-else-if="dossier">
      <KycStepper
        v-if="dossier.type_client === 'PP'"
        :dossier-id="dossierId"
        :initial-data="dossier.kyc_pp ?? null"
        @completed="onDone"
        @saved="onSaved"
      />
      <KycPMStepper
        v-else
        :dossier-id="dossierId"
        :initial-data="dossier.kyc_pm ?? undefined"
        @completed="onDone"
        @saved="onSaved"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import KycStepper from '@/components/kyc/KycStepper.vue'
import KycPMStepper from '@/components/kyc/KycPMStepper.vue'
import { dossiersService, type DossierOut } from '@/services/dossiers'

const route = useRoute()
const router = useRouter()

const dossierId = route.params.id as string
const dossier = ref<DossierOut | null>(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    dossier.value = await dossiersService.get(dossierId)
  } catch {
    error.value = 'Dossier introuvable.'
  } finally {
    loading.value = false
  }
})

function onSaved() {
  // Refresh local dossier data silently after each step save
  dossiersService.get(dossierId).then(d => { dossier.value = d }).catch(() => {})
}

function onDone() {
  router.push({ name: 'kyc-detail', params: { id: dossierId } })
}
</script>

<style scoped>
.kyc-edit-page { max-width: 860px; }

.page-header { margin-bottom: 1.5rem; }
.breadcrumb {
  display: flex; align-items: center; gap: 0.35rem;
  font-size: 0.8rem; color: var(--color-text-muted); margin-bottom: 0.5rem;
}
.breadcrumb-link {
  background: none; border: none; padding: 0; cursor: pointer;
  color: var(--color-text-muted); font-size: 0.8rem;
  transition: color 0.15s;
}
.breadcrumb-link:hover { color: var(--color-text-primary); }
.breadcrumb-sep { width: 14px; height: 14px; }

.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-muted); margin: 0; font-family: monospace; }

.loading-card, .error-card {
  padding: 2rem; text-align: center;
  background: var(--color-bg-card); border-radius: 10px;
  border: 1px solid var(--color-border);
}
.error-card { color: var(--color-risk-high); }
</style>
