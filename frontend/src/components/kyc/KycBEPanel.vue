<template>
  <div class="be-panel">
    <div class="panel-header">
      <div>
        <h3 class="panel-title">Bénéficiaires effectifs</h3>
        <p class="panel-subtitle">KYC complet des bénéficiaires effectifs — identité vérifiée, screening PPE, validation RC</p>
      </div>
      <button
        v-if="beList.length < MAX_BE"
        class="btn-primary"
        @click="openForm(null)"
      >
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Ajouter un BE
      </button>
    </div>

    <div v-if="loading" class="panel-loading">Chargement…</div>

    <div v-else-if="beList.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
      <p>Aucun bénéficiaire effectif enregistré</p>
    </div>

    <div v-else class="be-list">
      <div
        v-for="be in beList"
        :key="be.id"
        class="be-card"
      >
        <div class="be-card-left">
          <div class="be-avatar">{{ initials(be) }}</div>
          <div>
            <p class="be-name">{{ be.raison_sociale_nom }}</p>
            <p class="be-meta">
              {{ be.nationalite ?? '—' }}
              <span v-if="be.pays_residence" class="sep">·</span>
              <span v-if="be.pays_residence">{{ be.pays_residence }}</span>
              <span class="sep">·</span>
              <span class="pct-badge">{{ be.pourcentage ?? 0 }}%</span>
              <span v-if="(be.pourcentage ?? 0) >= 25" class="be25-tag">≥ 25%</span>
            </p>
          </div>
        </div>
        <div class="be-card-right">
          <button class="icon-btn" @click="openForm(be)" title="Modifier">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="icon-btn icon-btn--danger" @click="confirmDelete(be)" title="Supprimer">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Limit info -->
    <p v-if="beList.length >= MAX_BE" class="limit-info">
      Limite de {{ MAX_BE }} bénéficiaires effectifs atteinte.
    </p>

    <!-- Delete confirmation -->
    <Teleport to="body">
      <div v-if="beToDelete" class="modal-backdrop" @click.self="beToDelete = null">
        <div class="confirm-modal">
          <p class="confirm-text">Supprimer <strong>{{ beToDelete.raison_sociale_nom }}</strong> ?</p>
          <div class="confirm-actions">
            <button class="btn-ghost" @click="beToDelete = null">Annuler</button>
            <button class="btn-danger" :disabled="deleting" @click="doDelete">
              {{ deleting ? 'Suppression…' : 'Supprimer' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- BE Form modal -->
    <KycBEForm
      v-if="showForm"
      :dossier-id="dossierId"
      :be="editingBE"
      :client-type="clientType"
      @close="showForm = false"
      @saved="handleSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import KycBEForm from './KycBEForm.vue'
import { dossiersService, type KycBEData } from '@/services/dossiers'

const props = defineProps<{ dossierId: string; clientType?: 'PP' | 'PM' }>()

const MAX_BE = 10

const loading   = ref(true)
const beList    = ref<KycBEData[]>([])
const showForm  = ref(false)
const editingBE = ref<KycBEData | null>(null)
const beToDelete = ref<KycBEData | null>(null)
const deleting  = ref(false)

onMounted(async () => {
  await refresh()
})

async function refresh() {
  loading.value = true
  try {
    beList.value = await dossiersService.listKycBE(props.dossierId, props.clientType ?? 'PP')
  } finally {
    loading.value = false
  }
}

function initials(be: KycBEData): string {
  const r = (be.raison_sociale_nom ?? '').trim().split(' ')
  return `${(r[0] ?? '')[0] ?? ''}${(r[1] ?? '')[0] ?? ''}`.toUpperCase()
}

function openForm(be: KycBEData | null) {
  editingBE.value = be
  showForm.value  = true
}

function handleSaved(data: KycBEData) {
  const idx = beList.value.findIndex(b => b.id === data.id)
  if (idx >= 0) beList.value[idx] = data
  else beList.value.push(data)
  showForm.value = false
}

function confirmDelete(be: KycBEData) {
  beToDelete.value = be
}

async function doDelete() {
  if (!beToDelete.value?.id) return
  deleting.value = true
  try {
    await dossiersService.deleteKycBE(props.dossierId, beToDelete.value.id, props.clientType ?? 'PP')
    beList.value = beList.value.filter(b => b.id !== beToDelete.value?.id)
    beToDelete.value = null
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.be-panel { display: flex; flex-direction: column; gap: 1rem; }
.panel-header { display: flex; align-items: flex-start; justify-content: space-between; }
.panel-title { font-size: 0.9375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.panel-subtitle { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0; }

.panel-loading { padding: 2rem; text-align: center; font-size: 0.875rem; color: var(--color-text-muted); }

.empty-state { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 2.5rem 1rem; color: var(--color-text-muted); text-align: center; }
.empty-state svg { width: 36px; height: 36px; stroke: var(--color-border); }
.empty-state p { font-size: 0.875rem; margin: 0; }

.be-list { display: flex; flex-direction: column; gap: 0.5rem; }
.be-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.875rem 1rem; background: var(--color-bg-page); border: 1px solid var(--color-border);
  border-radius: 8px;
}
.be-card-left  { display: flex; align-items: center; gap: 0.75rem; }
.be-card-right { display: flex; align-items: center; gap: 0.5rem; }
.be-avatar {
  width: 36px; height: 36px; border-radius: 50%; background: var(--color-sidebar-bg);
  color: #fff; font-size: 0.75rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.be-name { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); margin: 0 0 0.2rem; }
.be-meta { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0; display: flex; align-items: center; gap: 0.375rem; flex-wrap: wrap; }
.sep { color: var(--color-border); }
.pct-badge { background: rgba(201,162,39,0.12); color: var(--color-sidebar-bg); border-radius: 5px; padding: 1px 5px; font-weight: 700; }
.controle-badge { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 5px; padding: 1px 5px; }
.be25-tag { background: rgba(37,99,235,0.1); color: #2563eb; border-radius: 5px; padding: 1px 5px; font-size: 0.6875rem; font-weight: 700; }

.ppe-chip { background: var(--color-status-bloque-bg); color: var(--color-status-bloque); border-radius: 5px; padding: 2px 6px; font-size: 0.6875rem; font-weight: 700; }
.validation-badge { border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.validation--en_attente { color: var(--color-status-en-analyse); background: var(--color-status-en-analyse-bg); }
.validation--valide     { color: var(--color-status-valide); background: var(--color-status-valide-bg); }
.validation--rejete     { color: var(--color-status-bloque); background: var(--color-status-bloque-bg); }

.icon-btn { background: none; border: none; cursor: pointer; padding: 0.25rem; color: var(--color-text-muted); border-radius: 5px; }
.icon-btn:hover { background: var(--color-bg-card); color: var(--color-text-primary); }
.icon-btn svg { width: 15px; height: 15px; }
.icon-btn--danger:hover { color: var(--color-status-bloque); }

.limit-info { font-size: 0.75rem; color: var(--color-text-secondary); text-align: center; }

.ppe-global-banner { display: flex; align-items: center; gap: 0.625rem; background: var(--color-status-bloque-bg); color: var(--color-status-bloque); border-radius: 8px; padding: 0.625rem 0.875rem; font-size: 0.8125rem; font-weight: 500; }
.ppe-global-banner svg { width: 16px; height: 16px; flex-shrink: 0; }

/* Delete confirm */
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 200; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.confirm-modal { background: var(--color-bg-card); border-radius: 10px; box-shadow: 0 12px 40px rgba(0,0,0,0.15); padding: 1.5rem; max-width: 380px; width: 100%; }
.confirm-text { font-size: 0.9375rem; color: var(--color-text-primary); margin: 0 0 1.25rem; }
.confirm-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }

.btn-primary { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5rem 1rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 8px; font-size: 0.8125rem; font-weight: 600; cursor: pointer; }
.btn-primary:hover { opacity: 0.88; }
.btn-icon { width: 14px; height: 14px; }
.btn-ghost { padding: 0.5rem 0.875rem; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 0.8125rem; cursor: pointer; }
.btn-danger { padding: 0.5rem 0.875rem; border: none; border-radius: 8px; background: var(--color-status-bloque); color: #fff; font-size: 0.8125rem; cursor: pointer; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
