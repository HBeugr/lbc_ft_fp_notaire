<template>
  <div class="dos-view">
    <!-- Confidentiality header -->
    <div class="confidential-banner">
      <span>⚠ CONFIDENTIEL — </span>
      <button class="art63-link" @click="showArt63 = true">Article 63</button>
      <span> — Usage strictement interne</span>
    </div>

    <!-- Article 63 modal -->
    <Teleport to="body">
      <div v-if="showArt63" class="modal-overlay" @click.self="showArt63 = false">
        <div class="modal art63-modal">
          <div class="art63-modal-header">
            <h2 class="art63-title">Article 63 — Ordonnance N°2023-875 relative à la LBC/FT/FP</h2>
            <button class="modal-close-btn" @click="showArt63 = false">✕</button>
          </div>
          <div class="art63-body">
            <p class="art63-chapeau">
              <strong>Obligation de déclaration de soupçon et de confidentialité</strong>
            </p>
            <p>
              Les personnes assujetties sont tenues de déclarer à la Cellule Nationale de Traitement des
              Informations Financières (CENTIF-CI) les sommes inscrites dans leurs livres ou les opérations
              portant sur des sommes dont elles savent, soupçonnent ou ont de bonnes raisons de soupçonner
              qu'elles proviennent d'une infraction ou sont liées au financement du terrorisme ou à la
              prolifération des armes de destruction massive.
            </p>
            <p>
              <strong>Obligation de secret :</strong> Les personnes assujetties, leurs dirigeants et leurs
              préposés sont tenus au secret professionnel en ce qui concerne les déclarations de soupçon
              effectuées. Il leur est interdit de porter à la connaissance du propriétaire des fonds ou de
              toute autre personne, l'existence d'une déclaration de soupçon ou d'une transmission
              d'informations à la CENTIF, ou de donner des informations sur les suites qui leur ont été
              réservées.
            </p>
            <p>
              <strong>Protection du déclarant :</strong> Aucune poursuite pénale, civile ou disciplinaire
              ne peut être intentée contre une personne assujettie, ses dirigeants ou ses préposés ayant
              effectué de bonne foi une déclaration de soupçon, même si les investigations ultérieures
              n'ont décelé aucun acte délictueux.
            </p>
            <p>
              <strong>Accès réservé :</strong> Les déclarations de soupçon et leur contenu sont
              strictement confidentiels. Seuls le Responsable Conformité, le Déclarant CENTIF désigné,
              le Dirigeant et l'Administrateur système sont habilités à consulter, créer ou modifier
              ces déclarations au sein de la plateforme.
            </p>
            <p class="art63-ref">
              Référence : Ordonnance N°2023-875 du 23 octobre 2023 relative à la lutte contre le
              blanchiment de capitaux, le financement du terrorisme et la prolifération des armes de
              destruction massive en République de Côte d'Ivoire.
            </p>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── LIST VIEW ─────────────────────────────────────────────────────── -->
      <!-- Main header -->
      <div class="view-header">
        <div>
          <h1 class="page-title">Déclarations d'Opérations Suspectes</h1>
          <p class="page-subtitle">DOS — Finalisation réservée RC / Déclarant / Dirigeant / Admin</p>
        </div>
        <button v-if="canCreate" class="btn-primary" @click="showNewDosForm = !showNewDosForm">
          {{ showNewDosForm ? '✕ Annuler' : '+ Nouvelle DOS' }}
        </button>
      </div>

      <!-- New DOS inline panel -->
      <div v-if="showNewDosForm && canCreate" class="new-dos-panel">
        <h2 class="panel-title">Créer une nouvelle Déclaration d'Opération Suspecte</h2>
        <p class="panel-desc">
          Indiquez la référence du dossier KYC concerné. Le formulaire DOS s'ouvrira immédiatement.
        </p>
        <div class="panel-row">
          <div class="field-wrap">
            <label class="field-label">Référence dossier KYC <span class="req">*</span></label>
            <input
              v-model="newDosRef"
              type="text"
              class="form-input"
              placeholder="Ex: KYC-202605-635336 ou coller l'UUID"
              @keyup.enter="startNewDos"
            />
            <span v-if="newDosError" class="field-error">{{ newDosError }}</span>
          </div>
          <button class="btn-primary" :disabled="newDosLoading || !newDosRef.trim()" @click="startNewDos">
            <span v-if="newDosLoading" class="spinner" />
            {{ newDosLoading ? 'Création…' : 'Ouvrir le formulaire DOS' }}
          </button>
        </div>
      </div>

      <!-- Search & Filters -->
      <div class="search-toolbar">
        <div class="search-fields">
          <div class="field-wrap">
            <label class="search-label">Référence DOS</label>
            <input
              v-model="filterRef"
              class="form-input search-input"
              placeholder="Ex: DOS-2026-001"
              @keyup.enter="applyFilters"
            />
          </div>
          <div class="field-wrap field-wrap--sm">
            <label class="search-label">Statut</label>
            <select v-model="filterStatut" class="form-input">
              <option value="">Tous</option>
              <option value="brouillon">Brouillon</option>
              <option value="en_cours">En cours</option>
              <option value="en_validation">En validation</option>
              <option value="validee_rc">Validée conformité</option>
              <option value="transmise">Transmise CENTIF</option>
              <option value="classee">Classée sans suite</option>
              <option value="accuse_recu">Accusé reçu</option>
            </select>
          </div>
          <div class="search-actions">
            <button class="btn-primary" :disabled="loading" @click="applyFilters">
              Rechercher
            </button>
            <button v-if="filterRef || filterStatut" class="btn-link" @click="resetFilters">
              Réinitialiser
            </button>
          </div>
        </div>
        <span v-if="searchError" class="field-error">{{ searchError }}</span>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-state">
        <span class="spinner spinner--dark" /> Chargement…
      </div>

      <!-- Table -->
      <template v-if="!loading">
        <div class="table-meta">
          <span class="list-count">{{ total }} déclaration{{ total > 1 ? 's' : '' }}</span>
        </div>

        <div v-if="dosList.length > 0" class="table-wrapper">
          <table class="dos-table">
            <thead>
              <tr>
                <th>Référence</th>
                <th>Statut</th>
                <th>Date de création</th>
                <th>Transmission CENTIF</th>
                <th>Annexes</th>
                <th class="col-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="dos in dosList"
                :key="dos.id"
                class="dos-row"
                :class="{ 'row--finalisee': isLocked(dos.statut) }"
              >
                <td class="cell-ref">{{ dos.reference_interne }}</td>
                <td>
                  <span class="statut-badge" :class="statutClass(dos.statut)">
                    {{ dosStatutLabel(dos.statut) }}
                  </span>
                </td>
                <td class="cell-date">{{ formatDate(dos.created_at) }}</td>
                <td class="cell-date">{{ dos.date_transmission_centif ? formatDate(dos.date_transmission_centif) : '—' }}</td>
                <td class="cell-annexes">
                  <span v-if="dos.addendums.length" class="annexe-count">
                    {{ dos.addendums.length }}
                  </span>
                  <span v-else class="no-annexe">—</span>
                </td>
                <td class="cell-actions">
                  <button class="action-btn action-btn--view" @click="openDos(dos)" title="Ouvrir la DOS">
                    Ouvrir
                  </button>
                  <button class="action-btn action-btn--pdf" @click="downloadPdf(dos.id)" title="Télécharger PDF">
                    PDF
                  </button>
                  <button
                    v-if="isLocked(dos.statut) && canCreate"
                    class="action-btn action-btn--annexe"
                    @click="openAddendumModal(dos)"
                    title="Ajouter une annexe"
                  >
                    + Annexe
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Empty state -->
        <div v-if="dosList.length === 0" class="empty-state">
          <div class="empty-icon">📋</div>
          <p v-if="filterRef || filterStatut">Aucune DOS ne correspond à votre recherche.</p>
          <p v-else>Aucune déclaration d'opération suspecte enregistrée.</p>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="pagination">
          <button
            class="pag-btn"
            :disabled="currentPage === 1"
            @click="goToPage(currentPage - 1)"
          >←</button>
          <button
            v-for="p in paginationPages"
            :key="p"
            class="pag-btn"
            :class="{ active: p === currentPage }"
            @click="goToPage(p)"
          >{{ p }}</button>
          <button
            class="pag-btn"
            :disabled="currentPage === totalPages"
            @click="goToPage(currentPage + 1)"
          >→</button>
        </div>
      </template>

    <!-- Addendum Modal -->
    <Teleport to="body">
      <div v-if="addendumModal.visible" class="modal-overlay" @click.self="addendumModal.visible = false">
        <div class="modal">
          <h2 class="modal-title">Annexe — {{ addendumModal.dos?.reference_interne }}</h2>
          <p class="modal-desc">Ajoutez une annexe (complément d'information) — append-only, non supprimable.</p>
          <textarea
            v-model="addendumModal.contenu"
            class="form-textarea"
            rows="5"
            placeholder="Informations complémentaires…"
          />
          <div v-if="addendumModal.error" class="error-msg">{{ addendumModal.error }}</div>
          <div class="modal-actions">
            <button class="btn-secondary" @click="addendumModal.visible = false">Annuler</button>
            <button class="btn-primary" :disabled="addendumModal.loading" @click="submitAddendum">
              {{ addendumModal.loading ? 'Enregistrement…' : 'Ajouter l\'annexe' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { dosService, dosStatutLabel, type DosOut } from '@/services/dos'
import { dossiersService } from '@/services/dossiers'

const PAGE_SIZE = 15

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// Accès DOS (Art. 63) — aligné sur le backend require_dos_access.
const DOS_ROLES = ['admin', 'notaire_principal', 'responsable_conformite', 'declarant_centif']
const canCreate = computed(() => !!auth.user && DOS_ROLES.includes(auth.user.role))

// Statuts « verrouillés » : la DOS est engagée dans le circuit (plus un simple brouillon).
const LOCKED_STATUTS = ['en_validation', 'validee_rc', 'soumis', 'transmise', 'classee', 'accuse_recu']
function isLocked(statut: string): boolean { return LOCKED_STATUTS.includes(statut) }
function statutClass(statut: string): string { return isLocked(statut) ? 'finalisee' : 'brouillon' }

// ── Global list state ────────────────────────────────────────────────────────
const allDos = ref<DosOut[]>([])
const currentPage = ref(1)
const loading = ref(false)
const searchError = ref('')

// ── Filters ──────────────────────────────────────────────────────────────────
const filterRef = ref('')
const filterStatut = ref('')

// Filtrage client (le backend liste tout ; la recherche par référence est locale).
const filteredDos = computed(() => {
  const ref_ = filterRef.value.trim().toLowerCase()
  return allDos.value.filter(d =>
    (!filterStatut.value || d.statut === filterStatut.value) &&
    (!ref_ || d.reference_interne.toLowerCase().includes(ref_))
  )
})
const total = computed(() => filteredDos.value.length)
const totalPages = computed(() => Math.ceil(total.value / PAGE_SIZE))
const dosList = computed(() =>
  filteredDos.value.slice((currentPage.value - 1) * PAGE_SIZE, currentPage.value * PAGE_SIZE)
)

// ── Modals ───────────────────────────────────────────────────────────────────
const showArt63 = ref(false)
const addendumModal = ref({
  visible: false,
  dos: null as DosOut | null,
  contenu: '',
  error: '',
  loading: false,
})

// ── New DOS form ─────────────────────────────────────────────────────────────
const showNewDosForm = ref(false)
const newDosRef = ref('')
const newDosError = ref('')
const newDosLoading = ref(false)

// ── Pagination ────────────────────────────────────────────────────────────────
const paginationPages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

// ── Load list ────────────────────────────────────────────────────────────────
async function loadDos(page = 1) {
  loading.value = true
  searchError.value = ''
  currentPage.value = page
  try {
    const resp = await dosService.listAll()
    allDos.value = resp.items
  } catch {
    searchError.value = 'Erreur lors du chargement des DOS.'
  } finally {
    loading.value = false
  }
}

function applyFilters() { currentPage.value = 1 }

function resetFilters() {
  filterRef.value = ''
  filterStatut.value = ''
  currentPage.value = 1
}

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
}

// ── Resolve dossier reference → UUID ─────────────────────────────────────────
async function resolveDossierId(query: string): Promise<string | null> {
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
  if (UUID_RE.test(query)) return query
  const resp = await dossiersService.list({ reference: query, page_size: 1 })
  return resp.items[0]?.id ?? null
}

// ── New DOS ───────────────────────────────────────────────────────────────────
async function startNewDos() {
  const raw = newDosRef.value.trim()
  if (!raw) return
  newDosError.value = ''
  newDosLoading.value = true
  try {
    const resolved = await resolveDossierId(raw)
    if (!resolved) {
      newDosError.value = `Dossier « ${raw} » introuvable. Vérifiez la référence KYC.`
      return
    }
    const dos = await dosService.create(resolved)
    showNewDosForm.value = false
    newDosRef.value = ''
    // Ouvre directement le formulaire DOS (page /dos/:id, câblée au backend CENTIF).
    router.push({ name: 'dos-detail', params: { id: dos.id } })
  } catch (e: any) {
    newDosError.value = e?.response?.data?.detail ?? 'Erreur lors de la création de la DOS.'
  } finally {
    newDosLoading.value = false
  }
}

// ── Ouvrir une DOS (consultation / édition) ───────────────────────────────────
function openDos(dos: DosOut) {
  router.push({ name: 'dos-detail', params: { id: dos.id } })
}

// ── PDF download ──────────────────────────────────────────────────────────────
async function downloadPdf(dosId: string) {
  try {
    const blob = await dosService.downloadPdfBlob(dosId)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `DOS_${dosId}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    // error handled by interceptor
  }
}

// ── Addendum ──────────────────────────────────────────────────────────────────
function openAddendumModal(dos: DosOut) {
  addendumModal.value = { visible: true, dos, contenu: '', error: '', loading: false }
}

async function submitAddendum() {
  const modal = addendumModal.value
  if (!modal.dos || !modal.contenu.trim()) {
    modal.error = 'Le contenu ne peut pas être vide.'
    return
  }
  modal.loading = true
  modal.error = ''
  try {
    await dosService.addAddendum(modal.dos.id, modal.contenu)
    modal.visible = false
    await loadDos(currentPage.value)
  } catch (e: any) {
    modal.error = e.response?.data?.detail ?? 'Erreur lors de l\'ajout de l\'annexe.'
  } finally {
    modal.loading = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-CI', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// ── On mount ──────────────────────────────────────────────────────────────────
onMounted(async () => {
  const dossierIdFromQuery = route.query.dossier_id as string | undefined
  if (dossierIdFromQuery) {
    newDosRef.value = dossierIdFromQuery
    if (route.query.action === 'create' && canCreate.value) {
      showNewDosForm.value = true
    }
  }
  await loadDos(1)
})
</script>

<style scoped>
.dos-view { padding: 0; max-width: 1100px; margin: 0 auto; }

/* ── Confidential banner ─────────────────────────────────────────────────── */
.confidential-banner {
  background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5;
  border-radius: 6px; padding: 0.5rem 1rem; font-size: 0.8rem; font-weight: 600;
  text-align: center; margin-bottom: 1.25rem;
  display: flex; align-items: center; justify-content: center; gap: 0;
}
.art63-link {
  background: rgba(220,38,38,0.12); border: 1px solid #fca5a5; color: #dc2626;
  font-size: 0.8rem; font-weight: 700; cursor: pointer;
  text-decoration: underline; text-decoration-style: solid;
  padding: 1px 6px; border-radius: 4px; line-height: inherit;
  transition: background 0.15s;
}
.art63-link:hover { background: rgba(220,38,38,0.22); }

/* ── Article 63 modal ────────────────────────────────────────────────────── */
.art63-modal {
  max-width: 640px; width: 95vw; max-height: 80vh;
  display: flex; flex-direction: column; padding: 0;
}
.art63-modal-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 1rem; padding: 1.25rem 1.5rem; border-bottom: 1px solid #fca5a5;
  background: #fef2f2; border-radius: 12px 12px 0 0; flex-shrink: 0;
}
.art63-title { font-size: 0.9rem; font-weight: 700; color: #dc2626; margin: 0; line-height: 1.4; }
.art63-body {
  padding: 1.25rem 1.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 0.875rem;
}
.art63-body p { font-size: 0.875rem; color: #1e293b; line-height: 1.6; margin: 0; }
.art63-chapeau { font-size: 0.9375rem !important; color: #1b2b4b !important; }
.art63-ref {
  font-size: 0.75rem !important; color: #64748b !important;
  border-top: 1px solid #e2e8f0; padding-top: 0.75rem; font-style: italic;
}

/* ── Stepper header (back button) ────────────────────────────────────────── */
.stepper-header {
  display: flex; align-items: center; gap: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap;
}
.btn-back {
  background: #f1f5f9; color: #1b2b4b; border: 1px solid #e2e8f0;
  border-radius: 6px; padding: 0.45rem 1rem; font-size: 0.875rem; font-weight: 600;
  cursor: pointer; white-space: nowrap; transition: background 0.15s;
}
.btn-back:hover { background: #e2e8f0; }
.stepper-title-wrap { display: flex; align-items: center; gap: 0.75rem; }
.stepper-page-title { font-size: 1.1rem; font-weight: 700; color: #1b2b4b; margin: 0; }

/* ── View header ─────────────────────────────────────────────────────────── */
.view-header {
  display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem;
}
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary, #1b2b4b); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.85rem; color: var(--color-text-secondary, #64748b); margin: 0; }

/* ── New DOS panel ───────────────────────────────────────────────────────── */
.new-dos-panel {
  background: #f0f9ff; border: 1px solid #bae6fd;
  border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;
}
.panel-title { font-size: 1rem; font-weight: 700; color: #1b2b4b; margin: 0 0 0.4rem; }
.panel-desc { font-size: 0.85rem; color: #475569; margin: 0 0 1rem; }
.panel-row { display: flex; gap: 0.75rem; align-items: flex-end; flex-wrap: wrap; }

/* ── Search toolbar ──────────────────────────────────────────────────────── */
.search-toolbar {
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
  padding: 1rem 1.25rem; margin-bottom: 1.25rem;
}
.search-fields { display: flex; gap: 0.75rem; align-items: flex-end; flex-wrap: wrap; }
.search-label { font-size: 0.8125rem; font-weight: 500; color: #64748b; }
.search-input { min-width: 220px; }
.search-actions { display: flex; gap: 0.5rem; align-items: center; padding-top: 1.25rem; }

/* ── Table meta ──────────────────────────────────────────────────────────── */
.table-meta {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;
}
.list-count { font-size: 0.82rem; color: #64748b; }

/* ── Table ───────────────────────────────────────────────────────────────── */
.table-wrapper {
  border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden;
  background: #fff;
}
.dos-table {
  width: 100%; border-collapse: collapse; font-size: 0.875rem;
}
.dos-table thead tr {
  background: #f1f5f9; border-bottom: 2px solid #e2e8f0;
}
.dos-table th {
  padding: 0.75rem 1rem; text-align: left;
  font-size: 0.78rem; font-weight: 700; color: #475569;
  text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap;
}
.dos-table th.col-actions { text-align: right; }
.dos-table tbody tr { border-bottom: 1px solid #f1f5f9; transition: background 0.12s; }
.dos-table tbody tr:last-child { border-bottom: none; }
.dos-table tbody tr:hover { background: #f8fafc; }
.dos-table td { padding: 0.75rem 1rem; vertical-align: middle; }

.dos-row.row--finalisee .cell-ref { border-left: 3px solid #16a34a; padding-left: calc(1rem - 3px); }

.cell-ref { font-weight: 700; color: #1b2b4b; }
.cell-date { color: #475569; white-space: nowrap; }
.cell-annexes { text-align: center; }
.annexe-count {
  background: #ede9fe; color: #7c3aed; font-size: 0.75rem;
  font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 99px;
}
.no-annexe { color: #cbd5e1; }

.cell-actions { text-align: right; white-space: nowrap; }

/* ── Action buttons (inline in table) ───────────────────────────────────── */
.action-btn {
  display: inline-flex; align-items: center;
  border-radius: 5px; padding: 0.3rem 0.7rem;
  font-size: 0.8rem; font-weight: 600; cursor: pointer;
  border: 1px solid transparent; margin-left: 0.35rem;
  transition: background 0.12s, opacity 0.12s;
  white-space: nowrap;
}
.action-btn--view {
  background: #f1f5f9; color: #1b2b4b; border-color: #e2e8f0;
}
.action-btn--view:hover { background: #e2e8f0; }

.action-btn--edit {
  background: #c9a227; color: #fff;
}
.action-btn--edit:hover { background: #a87d1a; }

.action-btn--pdf {
  background: #fff; color: #475569; border-color: #e2e8f0;
}
.action-btn--pdf:hover { background: #f1f5f9; }

.action-btn--annexe {
  background: #ede9fe; color: #7c3aed; border-color: #ddd6fe;
}
.action-btn--annexe:hover { background: #ddd6fe; }

/* ── Statut badge ────────────────────────────────────────────────────────── */
.statut-badge {
  font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.65rem; border-radius: 99px;
  display: inline-block;
}
.statut-badge.finalisee { background: #dcfce7; color: #15803d; }
.statut-badge.brouillon { background: #fef9c3; color: #854d0e; }

/* ── Pagination ──────────────────────────────────────────────────────────── */
.pagination {
  display: flex; gap: 0.4rem; justify-content: center;
  margin-top: 1.5rem; flex-wrap: wrap;
}
.pag-btn {
  min-width: 36px; height: 36px; padding: 0 0.5rem;
  border: 1px solid #e2e8f0; border-radius: 6px; background: #fff;
  font-size: 0.875rem; color: #1b2b4b; cursor: pointer; transition: background 0.12s;
}
.pag-btn:hover:not(:disabled) { background: #f1f5f9; }
.pag-btn.active { background: #1b2b4b; color: #fff; border-color: #1b2b4b; font-weight: 700; }
.pag-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Consult Modal ───────────────────────────────────────────────────────── */
.consult-modal {
  max-width: 680px; width: 95vw; max-height: 85vh;
  display: flex; flex-direction: column; padding: 0;
}
.consult-modal-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 1rem; padding: 1.25rem 1.5rem; border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.consult-header-left { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.consult-body {
  flex: 1; overflow-y: auto; padding: 1.25rem 1.5rem;
  display: flex; flex-direction: column; gap: 1rem;
}
.consult-meta { font-size: 0.8rem; color: #64748b; }
.consult-section { display: flex; flex-direction: column; gap: 0.35rem; }
.consult-section-label {
  font-size: 0.75rem; font-weight: 700; color: #64748b;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.consult-section-value {
  font-size: 0.875rem; color: #1e293b; line-height: 1.55;
  background: #f8fafc; border-radius: 6px; padding: 0.6rem 0.75rem;
  white-space: pre-wrap;
}
.motifs-list {
  margin: 0; padding-left: 1.25rem;
  display: flex; flex-direction: column; gap: 0.25rem;
}
.motifs-list li { font-size: 0.875rem; color: #1e293b; }
.addendum-item {
  background: #f8fafc; border-radius: 6px; padding: 0.6rem 0.75rem;
  display: flex; flex-direction: column; gap: 0.25rem;
}
.addendum-date { font-size: 0.75rem; color: #94a3b8; }
.addendum-content { font-size: 0.875rem; color: #1e293b; white-space: pre-wrap; }
.consult-empty { font-size: 0.875rem; color: #94a3b8; font-style: italic; }

/* ── Common buttons ──────────────────────────────────────────────────────── */
.btn-primary {
  background: #1b2b4b; color: #fff; border: none; border-radius: 6px;
  padding: 0.5rem 1.1rem; font-size: 0.875rem; font-weight: 600; cursor: pointer;
  display: flex; align-items: center; gap: 0.375rem; white-space: nowrap;
  transition: background 0.15s;
}
.btn-primary:hover { background: #c9a227; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-secondary {
  background: #f1f5f9; color: #1b2b4b; border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 0.45rem 1rem; font-size: 0.875rem; font-weight: 500; cursor: pointer; white-space: nowrap;
}
.btn-secondary:hover { background: #e2e8f0; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-edit {
  background: #c9a227; color: #fff; border: none; border-radius: 6px;
  padding: 0.45rem 1rem; font-size: 0.875rem; font-weight: 600; cursor: pointer;
}
.btn-edit:hover { background: #a87d1a; }

.btn-link {
  background: none; border: none; color: #c9a227; font-size: 0.82rem;
  cursor: pointer; text-decoration: underline; padding: 0;
}

/* ── Fields ──────────────────────────────────────────────────────────────── */
.field-wrap { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; min-width: 220px; }
.field-wrap--sm { flex: 0 0 160px; min-width: 0; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: #1e293b; }
.req { color: #dc2626; }
.field-error { color: #dc2626; font-size: 0.8rem; margin-top: 0.2rem; }

.form-input {
  border: 1px solid #cbd5e1; border-radius: 6px; padding: 0.5rem 0.75rem;
  font-size: 0.9rem; background: #fff;
}
.form-input:focus { outline: none; border-color: #1b2b4b; }

.form-textarea {
  width: 100%; border: 1px solid #cbd5e1; border-radius: 6px;
  padding: 0.6rem 0.75rem; font-size: 0.9rem; resize: vertical;
  box-sizing: border-box;
}

/* ── Empty / Loading ─────────────────────────────────────────────────────── */
.empty-state { text-align: center; padding: 3rem; color: #64748b; }
.empty-icon { font-size: 2.5rem; margin-bottom: 0.75rem; }
.loading-state {
  display: flex; align-items: center; gap: 0.6rem; justify-content: center;
  padding: 2.5rem; color: #94a3b8; font-size: 0.9rem;
}

/* ── Spinner ─────────────────────────────────────────────────────────────── */
.spinner {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff; border-radius: 50%;
  animation: spin 0.7s linear infinite; display: inline-block;
}
.spinner--dark {
  border-color: rgba(100,116,139,0.2); border-top-color: #64748b;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Modal shared ────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: #fff; border-radius: 12px; padding: 1.75rem 2rem;
  width: 520px; max-width: 95vw;
}
.modal-title { font-size: 1.1rem; font-weight: 700; color: #1b2b4b; margin: 0 0 0.4rem; }
.modal-desc { font-size: 0.85rem; color: #64748b; margin: 0 0 1rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.25rem; }
.modal-close-btn {
  background: none; border: none; color: #64748b; cursor: pointer;
  font-size: 1rem; padding: 0; flex-shrink: 0; line-height: 1;
}
.error-msg { color: #dc2626; font-size: 0.85rem; margin: 0.5rem 0; }
</style>
