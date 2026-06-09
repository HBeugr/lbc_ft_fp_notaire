<template>
  <div class="kyc-new-page">
    <!-- Step: type selection -->
    <template v-if="!dossier">
      <div class="page-header">
        <div>
          <h1 class="page-title">Nouveau dossier KYC</h1>
          <p class="page-subtitle">Sélectionnez le type de client et l'opération</p>
        </div>
        <button class="btn-ghost" @click="router.push({ name: 'kyc-list' })">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><polyline points="15 18 9 12 15 6"/></svg>
          Retour
        </button>
      </div>

      <div class="card setup-card">
        <h2 class="setup-title">Type de client</h2>
        <div class="type-grid">
          <button
            v-for="t in TYPE_CLIENTS"
            :key="t.value"
            class="type-card"
            :class="{ 'type-card--selected': typeClient === t.value }"
            @click="typeClient = t.value; typeOperation = ''"
          >
            <div class="type-card-icon">{{ t.icon }}</div>
            <div class="type-card-label">{{ t.label }}</div>
            <div class="type-card-desc">{{ t.desc }}</div>
          </button>
        </div>

        <template v-if="typeClient">
          <div class="divider" />
          <h2 class="setup-title">Type d'opération</h2>
          <div class="ops-grid">
            <button
              v-for="op in filteredOps"
              :key="op.value"
              class="op-card"
              :class="{ 'op-card--selected': typeOperation === op.value }"
              @click="typeOperation = op.value"
            >
              <div class="op-card-top">
                <span class="op-code">{{ op.value }}</span>
                <span class="op-risque" :class="`op-risque--${op.risque.toLowerCase()}`">{{ op.risque }}</span>
              </div>
              <span class="op-label">{{ op.label }}</span>
            </button>
          </div>
        </template>

        <div v-if="createError" class="form-error">{{ createError }}</div>

        <div class="setup-actions">
          <button
            class="btn-primary"
            :disabled="!typeClient || !typeOperation || creating"
            @click="handleCreate"
          >
            <svg v-if="creating" class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
            {{ creating ? 'Création…' : 'Créer le dossier' }}
          </button>
        </div>
      </div>
    </template>

    <!-- Step: KYC form -->
    <template v-else>
      <div class="page-header">
        <div>
          <h1 class="page-title">
            Formulaire KYC —
            {{ dossier.type_client === 'PP' ? 'Personne physique' : 'Personne morale' }}
          </h1>
          <p class="page-subtitle">
            Dossier <span class="ref-chip">{{ dossier.reference }}</span>
            &nbsp;·&nbsp;
            {{ OPERATION_LABELS[dossier.type_operation] ?? dossier.type_operation }}
          </p>
        </div>
        <button class="btn-ghost" @click="router.push({ name: 'kyc-list' })">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><polyline points="15 18 9 12 15 6"/></svg>
          Retour à la liste
        </button>
      </div>

      <KycStepper
        v-if="dossier.type_client === 'PP'"
        :dossier-id="dossier.id"
        @completed="handleCompleted()"
      />
      <KycPMStepper
        v-else
        :dossier-id="dossier.id"
        @completed="handleCompleted()"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import KycStepper from '@/components/kyc/KycStepper.vue'
import KycPMStepper from '@/components/kyc/KycPMStepper.vue'
import {
  dossiersService,
  type DossierOut,
  type TypeClient,
  type TypeOperation,
  TYPE_OPERATION_LABELS,
  TYPE_OPERATION_RISQUE,
} from '@/services/dossiers'

const router = useRouter()

const typeClient = ref<TypeClient | ''>('')
const typeOperation = ref<TypeOperation | ''>('')
const creating = ref(false)
const createError = ref('')
const dossier = ref<DossierOut | null>(null)

const OPERATION_LABELS = TYPE_OPERATION_LABELS

const TYPE_CLIENTS = [
  { value: 'PP' as TypeClient, icon: '👤', label: 'Personne physique', desc: 'Individu, particulier' },
  { value: 'PM' as TypeClient, icon: '🏢', label: 'Personne morale', desc: 'Société, organisation' },
]

const AG_OPS: { value: TypeOperation; label: string; risque: string }[] = [
  { value: 'AG_01', label: TYPE_OPERATION_LABELS['AG_01'], risque: TYPE_OPERATION_RISQUE['AG_01'] },
  { value: 'AG_02', label: TYPE_OPERATION_LABELS['AG_02'], risque: TYPE_OPERATION_RISQUE['AG_02'] },
  { value: 'AG_03', label: TYPE_OPERATION_LABELS['AG_03'], risque: TYPE_OPERATION_RISQUE['AG_03'] },
  { value: 'AG_04', label: TYPE_OPERATION_LABELS['AG_04'], risque: TYPE_OPERATION_RISQUE['AG_04'] },
  { value: 'AG_05', label: TYPE_OPERATION_LABELS['AG_05'], risque: TYPE_OPERATION_RISQUE['AG_05'] },
  { value: 'AG_06', label: TYPE_OPERATION_LABELS['AG_06'], risque: TYPE_OPERATION_RISQUE['AG_06'] },
  { value: 'AG_07', label: TYPE_OPERATION_LABELS['AG_07'], risque: TYPE_OPERATION_RISQUE['AG_07'] },
]

const PR_OPS: { value: TypeOperation; label: string; risque: string }[] = [
  { value: 'PR_01', label: TYPE_OPERATION_LABELS['PR_01'], risque: TYPE_OPERATION_RISQUE['PR_01'] },
  { value: 'PR_02', label: TYPE_OPERATION_LABELS['PR_02'], risque: TYPE_OPERATION_RISQUE['PR_02'] },
  { value: 'PR_03', label: TYPE_OPERATION_LABELS['PR_03'], risque: TYPE_OPERATION_RISQUE['PR_03'] },
  { value: 'PR_04', label: TYPE_OPERATION_LABELS['PR_04'], risque: TYPE_OPERATION_RISQUE['PR_04'] },
]

// In notaire all roles see all operations (no commercial_promotion / gestionnaire_locatif roles)
const filteredOps = computed(() => {
  if (typeClient.value === 'PM') return PR_OPS
  return [...AG_OPS, ...PR_OPS]
})

async function handleCreate() {
  if (!typeClient.value || !typeOperation.value) return
  creating.value = true
  createError.value = ''
  try {
    dossier.value = await dossiersService.create({
      type_client: typeClient.value,
      type_operation: typeOperation.value as TypeOperation,
    })
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: string } } }
    createError.value = e?.response?.data?.detail ?? 'Erreur lors de la création du dossier.'
  } finally {
    creating.value = false
  }
}

function handleCompleted() {
  if (dossier.value) {
    router.push({ name: 'kyc-detail', params: { id: dossier.value.id } })
  }
}
</script>

<style scoped>
.kyc-new-page { max-width: 860px; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
.page-title  { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }
.ref-chip { font-family: monospace; font-weight: 600; color: var(--color-sidebar-bg); background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 5px; padding: 1px 6px; font-size: 0.8125rem; }

.btn-ghost { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.5rem 0.875rem; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 0.8125rem; cursor: pointer; }
.btn-ghost:hover { border-color: var(--color-sidebar-bg); color: var(--color-text-primary); }
.btn-icon { width: 14px; height: 14px; }

.setup-card { padding: 1.75rem; }
.setup-title { font-size: 0.875rem; font-weight: 600; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 1rem; }
.divider { border: none; border-top: 1px solid var(--color-border); margin: 1.5rem 0; }

.type-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem; }
.type-card {
  display: flex; flex-direction: column; align-items: center; gap: 0.375rem;
  padding: 1.25rem; border: 2px solid var(--color-border); border-radius: 10px;
  background: var(--color-bg-card); cursor: pointer; text-align: center; transition: border-color 0.15s;
}
.type-card:hover { border-color: var(--color-sidebar-bg); }
.type-card--selected { border-color: var(--color-sidebar-bg); background: rgba(201,162,39,0.06); }
.type-card-icon { font-size: 1.75rem; }
.type-card-label { font-size: 0.9375rem; font-weight: 600; color: var(--color-text-primary); }
.type-card-desc  { font-size: 0.75rem; color: var(--color-text-secondary); }

.ops-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.625rem; }
.op-card {
  display: flex; flex-direction: column; gap: 0.25rem; align-items: flex-start;
  padding: 0.75rem 1rem; border: 2px solid var(--color-border); border-radius: 8px;
  background: var(--color-bg-card); cursor: pointer; text-align: left; transition: border-color 0.15s;
}
.op-card:hover { border-color: var(--color-sidebar-bg); }
.op-card--selected { border-color: var(--color-sidebar-bg); background: rgba(201,162,39,0.06); }
.op-card-top { display: flex; align-items: center; justify-content: space-between; width: 100%; }
.op-code  { font-family: monospace; font-size: 0.6875rem; font-weight: 700; color: var(--color-sidebar-bg); }
.op-label { font-size: 0.8125rem; color: var(--color-text-primary); font-weight: 500; }
.op-risque { font-size: 0.6rem; font-weight: 700; padding: 1px 5px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.04em; }
.op-risque--faible  { background: #d1fae5; color: #065f46; }
.op-risque--moyen   { background: #fef3c7; color: #92400e; }
.op-risque--Élevé,
.op-risque--élevé   { background: #fee2e2; color: #991b1b; }

.form-error { color: var(--color-status-bloque); font-size: 0.8125rem; margin-top: 0.875rem; }

.setup-actions { display: flex; justify-content: flex-end; margin-top: 1.5rem; }
.btn-primary { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5625rem 1.25rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { opacity: 0.88; }

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 0.8s linear infinite; }
</style>
