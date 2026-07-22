<template>
  <div class="procedures-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Mes procédures</h1>
        <p class="page-sub">Référentiel des procédures internes — jusqu'à {{ NB_SLOTS_PROCEDURE }} pièces par procédure.</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ Nouvelle procédure</button>
    </div>

    <div class="toolbar">
      <input v-model="search" type="search" class="filter-search" placeholder="Rechercher une procédure…" />
    </div>

    <div v-if="loading" class="loading-state">Chargement…</div>

    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Nom</th>
          <th>Pièces</th>
          <th>Créée le</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in procedures" :key="p.id" class="row" @click="openDetail(p.id)">
          <td class="td-nom">{{ p.nom }}</td>
          <td>
            <span class="chip" :class="p.nb_pieces >= NB_SLOTS_PROCEDURE ? 'chip--full' : 'chip--muted'">
              {{ p.nb_pieces }} / {{ NB_SLOTS_PROCEDURE }}
            </span>
          </td>
          <td>{{ formatDate(p.created_at) }}</td>
          <td class="td-actions" @click.stop>
            <button class="btn-link" @click="openDetail(p.id)">Ouvrir</button>
            <button class="btn-link btn-danger" @click="remove(p)">Supprimer</button>
          </td>
        </tr>
        <tr v-if="!procedures.length">
          <td colspan="4" class="empty">Aucune procédure.</td>
        </tr>
      </tbody>
    </table>

    <div v-if="totalPages > 1" class="pagination">
      <button class="btn-page" :disabled="currentPage <= 1" @click="loadPage(currentPage - 1)">‹</button>
      <span>Page {{ currentPage }} / {{ totalPages }}</span>
      <button class="btn-page" :disabled="currentPage >= totalPages" @click="loadPage(currentPage + 1)">›</button>
    </div>

    <!-- Modal création -->
    <div v-if="createModal.open" class="modal-overlay" @click.self="createModal.open = false">
      <div class="modal">
        <h2 class="modal-title">Nouvelle procédure</h2>
        <input v-model="createModal.nom" class="field-input" placeholder="Nom de la procédure" @keyup.enter="confirmCreate" />
        <div class="modal-footer">
          <button class="btn-ghost" @click="createModal.open = false">Annuler</button>
          <button class="btn-primary" :disabled="!createModal.nom.trim() || createModal.saving" @click="confirmCreate">Créer</button>
        </div>
      </div>
    </div>

    <!-- Modal détail -->
    <div v-if="detail" class="modal-overlay" @click.self="detail = null">
      <div class="modal modal--lg">
        <div class="modal-head">
          <input v-model="detailNom" class="field-input detail-name" @blur="renameIfChanged" />
          <button class="btn-close" @click="detail = null">✕</button>
        </div>
        <div class="slots">
          <div v-for="slot in NB_SLOTS_PROCEDURE" :key="slot" class="slot-row">
            <span class="slot-num">{{ slot }}</span>
            <template v-if="fileForSlot(slot)">
              <span class="slot-file">{{ fileForSlot(slot)!.nom_fichier }}</span>
              <div class="slot-actions">
                <button class="btn-link" @click="download(fileForSlot(slot)!)">Télécharger</button>
                <button class="btn-link btn-danger" @click="deleteFile(fileForSlot(slot)!)">Supprimer</button>
              </div>
            </template>
            <template v-else>
              <span class="slot-empty">— vide —</span>
              <label class="btn-link upload-label">
                Téléverser
                <input type="file" accept=".pdf,.jpg,.jpeg,.png" hidden @change="onUpload($event, slot)" />
              </label>
            </template>
          </div>
        </div>
        <p v-if="uploadMsg" class="upload-msg">{{ uploadMsg }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  proceduresService, NB_SLOTS_PROCEDURE,
  type ProcedureOut, type ProcedureDetail, type ProcedureFileOut,
} from '@/services/procedures'

const PAGE_SIZE = 20
const procedures = ref<ProcedureOut[]>([])
const total = ref(0)
const currentPage = ref(1)
const loading = ref(true)
const search = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

const createModal = ref<{ open: boolean; nom: string; saving: boolean }>({ open: false, nom: '', saving: false })
const detail = ref<ProcedureDetail | null>(null)
const detailNom = ref('')
const uploadMsg = ref('')

function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d.getTime()) ? '—' : d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function fileForSlot(slot: number): ProcedureFileOut | undefined {
  return detail.value?.files.find(f => f.slot === slot)
}

async function loadPage(page: number) {
  loading.value = true
  currentPage.value = page
  try {
    const res = await proceduresService.list({ page, page_size: PAGE_SIZE, search: search.value.trim() || undefined })
    procedures.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadPage(1), 300)
})

function openCreate() {
  createModal.value = { open: true, nom: '', saving: false }
}

async function confirmCreate() {
  if (!createModal.value.nom.trim()) return
  createModal.value.saving = true
  try {
    await proceduresService.create(createModal.value.nom.trim())
    createModal.value.open = false
    await loadPage(1)
  } finally {
    createModal.value.saving = false
  }
}

async function openDetail(id: string) {
  detail.value = await proceduresService.get(id)
  detailNom.value = detail.value.nom
  uploadMsg.value = ''
}

async function renameIfChanged() {
  if (!detail.value) return
  const nom = detailNom.value.trim()
  if (!nom || nom === detail.value.nom) return
  await proceduresService.rename(detail.value.id, nom)
  detail.value.nom = nom
  await loadPage(currentPage.value)
}

async function onUpload(e: Event, slot: number) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !detail.value) return
  uploadMsg.value = 'Téléversement…'
  try {
    await proceduresService.uploadFile(detail.value.id, slot, file)
    detail.value = await proceduresService.get(detail.value.id)
    uploadMsg.value = 'Pièce ajoutée.'
    await loadPage(currentPage.value)
  } catch (err: any) {
    uploadMsg.value = err?.response?.data?.detail ?? 'Erreur lors du téléversement.'
  } finally {
    input.value = ''
  }
}

async function download(f: ProcedureFileOut) {
  await proceduresService.downloadFile(f.id, f.nom_fichier)
}

async function deleteFile(f: ProcedureFileOut) {
  if (!detail.value) return
  if (!confirm(`Supprimer la pièce « ${f.nom_fichier} » ?`)) return
  await proceduresService.deleteFile(f.id)
  detail.value = await proceduresService.get(detail.value.id)
  await loadPage(currentPage.value)
}

async function remove(p: ProcedureOut) {
  if (!confirm(`Supprimer la procédure « ${p.nom} » et ses pièces ?`)) return
  await proceduresService.remove(p.id)
  await loadPage(currentPage.value)
}

onMounted(() => loadPage(1))
</script>

<style scoped>
.procedures-page { max-width: 1000px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.25rem; }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-sub { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }
.toolbar { margin-bottom: 1rem; }
.filter-search { padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px; font-size: 0.875rem; min-width: 280px; }
.loading-state { color: var(--color-text-secondary); font-size: 0.875rem; }

.data-table { width: 100%; border-collapse: collapse; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; overflow: hidden; }
.data-table th { text-align: left; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.03em; color: var(--color-text-secondary); padding: 0.75rem 1rem; border-bottom: 1px solid var(--color-border); }
.data-table td { padding: 0.75rem 1rem; border-bottom: 1px solid var(--color-border); font-size: 0.875rem; color: var(--color-text-primary); }
.row { cursor: pointer; }
.row:hover td { background: var(--color-surface-alt, #f8fafc); }
.td-nom { font-weight: 600; }
.td-actions { text-align: right; white-space: nowrap; }
.empty { text-align: center; color: var(--color-text-secondary); }

.chip { font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 6px; }
.chip--full { background: #dcfce7; color: #166534; }
.chip--muted { background: #f1f5f9; color: #64748b; }

.btn-primary { background: var(--color-accent, #c9a227); color: #fff; border: none; border-radius: 8px; padding: 0.5625rem 1.1rem; font-size: 0.875rem; font-weight: 600; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-ghost { background: transparent; border: 1px solid var(--color-border); border-radius: 8px; padding: 0.5rem 1rem; font-size: 0.875rem; cursor: pointer; }
.btn-link { background: none; border: none; color: var(--color-accent, #c9a227); font-size: 0.8125rem; font-weight: 600; cursor: pointer; padding: 0 0.4rem; }
.btn-danger { color: #dc2626; }
.upload-label { cursor: pointer; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1rem; font-size: 0.875rem; color: var(--color-text-secondary); }
.btn-page { border: 1px solid var(--color-border); background: var(--color-surface); border-radius: 6px; width: 32px; height: 32px; cursor: pointer; }
.btn-page:disabled { opacity: 0.4; cursor: not-allowed; }

.modal-overlay { position: fixed; inset: 0; background: rgba(15,23,42,0.45); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: var(--color-surface); border-radius: 12px; padding: 1.5rem; width: 100%; max-width: 420px; display: flex; flex-direction: column; gap: 1rem; }
.modal--lg { max-width: 640px; }
.modal-title { font-size: 1.125rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.modal-head { display: flex; align-items: center; gap: 0.75rem; }
.field-input { padding: 0.55rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px; font-size: 0.875rem; width: 100%; }
.detail-name { font-weight: 600; }
.btn-close { background: none; border: none; font-size: 1.1rem; cursor: pointer; color: var(--color-text-secondary); }
.modal-footer { display: flex; justify-content: flex-end; gap: 0.75rem; }

.slots { display: flex; flex-direction: column; gap: 0.5rem; }
.slot-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.6rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px; }
.slot-num { width: 22px; height: 22px; border-radius: 50%; background: var(--color-surface-alt, #f1f5f9); color: var(--color-text-secondary); font-size: 0.75rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.slot-file { flex: 1; font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.slot-empty { flex: 1; font-size: 0.8125rem; color: var(--color-text-secondary); font-style: italic; }
.slot-actions { display: flex; gap: 0.25rem; flex-shrink: 0; }
.upload-msg { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; }
</style>
