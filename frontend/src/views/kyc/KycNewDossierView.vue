<template>
  <div class="kyc-new-page">
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
              <span class="op-label">{{ op.label }}</span>
              <span class="op-risque" :class="`op-risque--${op.risque.toLowerCase()}`">{{ op.risque }}</span>
            </div>
          </button>
        </div>
        <div class="divider" />
        <h2 class="setup-title">Nature de la relation d'affaires</h2>
        <p class="page-subtitle" style="margin-bottom: 0.75rem;">Une relation durable impose une vigilance et un KYC complet (Type B).</p>
        <div class="ops-grid">
          <button
            v-for="nr in NATURE_RELATIONS"
            :key="nr.value"
            class="op-card"
            :class="{ 'op-card--selected': natureRelation === nr.value }"
            @click="natureRelation = nr.value"
          >
            <div class="op-card-top">
              <span class="op-label">{{ nr.label }}</span>
            </div>
            <div class="type-card-desc">{{ nr.desc }}</div>
          </button>
        </div>
      </template>

      <div v-if="createError" class="form-error">{{ createError }}</div>

      <div class="setup-actions">
        <button
          class="btn-primary"
          :disabled="!typeClient || !typeOperation || !natureRelation || creating"
          @click="handleCreate"
        >
          <svg v-if="creating" class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
          {{ creating ? 'Création…' : 'Créer le dossier' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  dossiersService,
  type TypeClient,
  type TypeOperation,
  TYPE_OPERATION_LABELS,
  TYPE_OPERATION_RISQUE,
} from '@/services/dossiers'

const router = useRouter()

const typeClient     = ref<TypeClient | ''>('')
const typeOperation  = ref<TypeOperation | ''>('')
const natureRelation = ref<'ponctuelle' | 'durable' | ''>('')
const creating       = ref(false)
const createError    = ref('')

const NATURE_RELATIONS = [
  { value: 'ponctuelle' as const, label: 'Ponctuelle', desc: 'Acte unique, sans relation suivie' },
  { value: 'durable' as const,    label: 'Durable',    desc: 'Relation suivie — vigilance et KYC complet (Type B)' },
]

const TYPE_CLIENTS = [
  { value: 'PP' as TypeClient, icon: '👤', label: 'Personne physique', desc: 'Individu, particulier' },
  { value: 'PM' as TypeClient, icon: '🏢', label: 'Personne morale',   desc: 'Société, organisation' },
]

// Opérations notariales — toutes disponibles pour PP et PM
const ALL_OPS: { value: TypeOperation; label: string; risque: string }[] = [
  { value: 'vente_immobiliere',    label: TYPE_OPERATION_LABELS['vente_immobiliere'],    risque: TYPE_OPERATION_RISQUE['vente_immobiliere'] },
  { value: 'manipulation_fonds',   label: TYPE_OPERATION_LABELS['manipulation_fonds'],   risque: TYPE_OPERATION_RISQUE['manipulation_fonds'] },
  { value: 'constitution_societe', label: TYPE_OPERATION_LABELS['constitution_societe'], risque: TYPE_OPERATION_RISQUE['constitution_societe'] },
  { value: 'fiducicommis',         label: TYPE_OPERATION_LABELS['fiducicommis'],         risque: TYPE_OPERATION_RISQUE['fiducicommis'] },
  { value: 'succession',           label: TYPE_OPERATION_LABELS['succession'],           risque: TYPE_OPERATION_RISQUE['succession'] },
  { value: 'donation',             label: TYPE_OPERATION_LABELS['donation'],             risque: TYPE_OPERATION_RISQUE['donation'] },
  { value: 'autre',                label: TYPE_OPERATION_LABELS['autre'],                risque: TYPE_OPERATION_RISQUE['autre'] },
]

// Pas de filtrage par rôle — toutes les opérations pour PP et PM
const filteredOps = computed(() => ALL_OPS)

async function handleCreate() {
  if (!typeClient.value || !typeOperation.value) return
  creating.value = true
  createError.value = ''
  try {
    const created = await dossiersService.create({
      type_client: typeClient.value,
      type_operation: typeOperation.value as TypeOperation,
      nature_relation: natureRelation.value || undefined,
    })
    if (created.type_client === 'PP') {
      router.push({ name: 'kyc-pp', params: { id: created.id } })
    } else {
      router.push({ name: 'kyc-pm', params: { id: created.id } })
    }
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: string } } }
    createError.value = e?.response?.data?.detail ?? 'Erreur lors de la création du dossier.'
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.kyc-new-page { max-width: 860px; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
.page-title  { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }

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
.type-card-icon  { font-size: 1.75rem; }
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
.op-card-top { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 0.5rem; }
.op-label  { font-size: 0.8125rem; color: var(--color-text-primary); font-weight: 500; }
.op-risque { font-size: 0.6rem; font-weight: 700; padding: 1px 5px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap; flex-shrink: 0; }
.op-risque--faible  { background: #d1fae5; color: #065f46; }
.op-risque--moyen   { background: #fef3c7; color: #92400e; }
.op-risque--élevé   { background: #fee2e2; color: #991b1b; }

.form-error { color: var(--color-status-bloque); font-size: 0.8125rem; margin-top: 0.875rem; }

.setup-actions { display: flex; justify-content: flex-end; margin-top: 1.5rem; }
.btn-primary { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5625rem 1.25rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { opacity: 0.88; }

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 0.8s linear infinite; }
</style>
