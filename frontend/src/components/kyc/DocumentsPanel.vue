<template>
  <div class="docs-panel">

    <!-- Header summary -->
    <div class="panel-header">
      <div>
        <h3 class="panel-title">Pièces justificatives</h3>
        <p class="panel-subtitle">
          <span class="summary-ok">{{ uploadedCount }} fourni{{ uploadedCount > 1 ? 's' : '' }}</span>
          <span class="sep">·</span>
          <span :class="missingMandatory > 0 ? 'summary-missing' : 'summary-ok'">
            {{ missingMandatory }} manquant{{ missingMandatory > 1 ? 's' : '' }} obligatoire{{ missingMandatory > 1 ? 's' : '' }}
          </span>
        </p>
      </div>
      <div v-if="missingMandatory === 0 && applicableDocs.length > 0" class="compliant-badge">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
        Dossier documentaire complet
      </div>
    </div>

    <div v-if="loading" class="panel-loading">Chargement des documents…</div>

    <template v-else>
      <!-- Required documents checklist -->
      <div class="doc-group">
        <div
          v-for="req in applicableDocs"
          :key="req.key"
          class="doc-row"
          :class="{ 'doc-row--ok': docsForType(req.key).length > 0 }"
        >
          <!-- Status + info -->
          <div class="doc-row-main" @click="toggleExpand(req.key)">
            <div class="doc-status-icon">
              <svg v-if="docsForType(req.key).length > 0" class="icon-ok" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/></svg>
              <svg v-else class="icon-missing" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            </div>
            <div class="doc-info">
              <p class="doc-label">{{ req.label }}</p>
              <p class="doc-condition">{{ req.conditionLabel }}</p>
            </div>
            <span class="oblig-chip" :class="req.obligatoire === true ? 'oblig--required' : 'oblig--optional'">
              {{ req.obligatoire === true ? 'Obligatoire' : 'Selon cas' }}
            </span>
            <button v-if="docsForType(req.key).length === 0" class="add-chip" @click.stop="toggleExpand(req.key)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Ajouter
            </button>
            <button v-else class="add-chip add-chip--secondary" @click.stop="toggleExpand(req.key)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Autre version
            </button>
          </div>

          <!-- Uploaded files for this type -->
          <div v-if="docsForType(req.key).length" class="doc-files">
            <div v-for="doc in docsForType(req.key)" :key="doc.id" class="doc-file">
              <svg class="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <span class="file-name">{{ doc.nom_fichier }}</span>
              <span class="file-size">{{ formatSize(doc.taille_octets) }}</span>
              <span class="file-date">{{ formatDate(doc.created_at) }}</span>
              <button class="dl-btn" @click="downloadDoc(doc)" title="Télécharger">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              </button>
              <button v-if="canDelete" class="del-btn" @click="confirmDelete(doc)" title="Supprimer">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/></svg>
              </button>
            </div>
          </div>

          <!-- Inline upload zone -->
          <div v-if="expanded === req.key" class="doc-upload-zone">
            <label class="upload-label">Sélectionner ou glisser un fichier (PDF, JPG, PNG · max 20 Mo)</label>
            <div
              class="drop-area"
              :class="{ 'drop-area--drag': dragging === req.key }"
              @dragover.prevent="dragging = req.key"
              @dragleave.prevent="dragging = ''"
              @drop.prevent="(e) => onDrop(e, req.key)"
              @click="triggerInput(req.key)"
            >
              <input :ref="(el) => setInputRef(req.key, el)" type="file" accept=".pdf,.jpg,.jpeg,.png" class="hidden-input" @change="(e) => onFileChange(e, req.key)" />
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="drop-icon"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              <span class="drop-text">Cliquer ou déposer ici</span>
            </div>
            <div v-if="uploadProgress[req.key] !== undefined" class="upload-progress">
              <div class="progress-bar" :style="{ width: uploadProgress[req.key] + '%' }"/>
            </div>
            <p v-if="uploadErrors[req.key]" class="upload-err">{{ uploadErrors[req.key] }}</p>
          </div>
        </div>
      </div>

      <!-- Other / free documents -->
      <div v-if="otherDocs.length > 0" class="doc-group doc-group--other">
        <h4 class="group-title">Autres documents</h4>
        <div v-for="doc in otherDocs" :key="doc.id" class="doc-file doc-file--other">
          <svg class="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <div class="file-info">
            <span class="file-name">{{ doc.nom_fichier }}</span>
            <span class="file-type-tag">{{ doc.type_document }}</span>
          </div>
          <span class="file-size">{{ formatSize(doc.taille_octets) }}</span>
          <span class="file-date">{{ formatDate(doc.created_at) }}</span>
          <button class="dl-btn" @click="downloadDoc(doc)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          </button>
          <button v-if="canDelete" class="del-btn" @click="confirmDelete(doc)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/></svg>
          </button>
        </div>
      </div>
    </template>

    <!-- Delete confirm modal -->
    <Teleport to="body">
      <div v-if="docToDelete" class="modal-backdrop" @click.self="docToDelete = null">
        <div class="confirm-modal">
          <p class="confirm-text">Supprimer <strong>{{ docToDelete.nom_fichier }}</strong> ?</p>
          <p class="confirm-note">Le fichier est conservé dans les archives (traçabilité LBC-FT).</p>
          <div class="confirm-actions">
            <button class="btn-ghost" @click="docToDelete = null">Annuler</button>
            <button class="btn-danger" :disabled="deleting" @click="doDelete">
              {{ deleting ? 'Suppression…' : 'Supprimer' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { dossiersService, type DossierOut, type DocumentOut } from '@/services/dossiers'

const props = defineProps<{ dossier: DossierOut }>()

const auth = useAuthStore()
const canDelete = computed(() => auth.user?.role === 'admin' || auth.user?.role === 'responsable_conformite')

// ── Required document definitions ─────────────────────────────────────────────

interface ReqDoc {
  key: string
  label: string
  conditionLabel: string
  obligatoire: boolean | 'selon_cas'
}

const applicableDocs = computed((): ReqDoc[] => {
  const d = props.dossier
  const isPM = d.type_client === 'PM'
  const hasPPE = d.trigger_actif === 'T1'
  const hasCompteTiers = !!(d.kyc_pp?.est_compte_tiers || d.kyc_pm?.est_compte_tiers)
  const list: ReqDoc[] = []

  list.push({ key: 'piece_identite',         label: "Pièce d'identité en cours de validité",  conditionLabel: 'Toujours',                              obligatoire: true })
  list.push({ key: 'justificatif_domicile',   label: 'Justificatif de domicile (<3 mois)',      conditionLabel: 'Toujours',                              obligatoire: true })
  list.push({ key: 'declaration_origine_fonds', label: 'Déclaration origine des fonds',         conditionLabel: 'Transaction >15M FCFA ou espèces',     obligatoire: true })

  if (hasPPE) {
    list.push({ key: 'declaration_ppe_signee',      label: 'Déclaration statut PPE signée',          conditionLabel: 'PPE détecté (Trigger T1)', obligatoire: true })
    list.push({ key: 'recherche_presse_negative',   label: 'Recherche presse négative (Niveau 2)',   conditionLabel: 'PPE détecté (Trigger T1)', obligatoire: true })
    list.push({ key: 'formulaire_kyc_ppe',          label: 'Formulaire KYC-PPE complété',            conditionLabel: 'PPE détecté (Trigger T1)', obligatoire: true })
  }

  if (isPM) {
    list.push({ key: 'extrait_rccm',                label: 'Extrait RCCM (<3 mois)',                 conditionLabel: 'Personne morale — toujours',       obligatoire: true })
    list.push({ key: 'formulaire_kyc_be_organigramme', label: 'Formulaire KYC-BE + organigramme',    conditionLabel: 'Personne morale avec BE ≥25%',     obligatoire: true })
  }

  if (hasCompteTiers) {
    list.push({ key: 'procuration_mandat', label: 'Procuration / Mandat', conditionLabel: 'Client pour compte de tiers', obligatoire: 'selon_cas' })
  }

  return list
})

// ── State ──────────────────────────────────────────────────────────────────────

const loading  = ref(true)
const allDocs  = ref<DocumentOut[]>([])
const expanded = ref('')
const dragging = ref('')
const uploadProgress = ref<Record<string, number>>({})
const uploadErrors   = ref<Record<string, string>>({})
const docToDelete    = ref<DocumentOut | null>(null)
const deleting       = ref(false)
const inputRefs      = ref<Record<string, HTMLInputElement | null>>({})

// ── Computed ───────────────────────────────────────────────────────────────────

const knownKeys = computed(() => new Set(applicableDocs.value.map(d => d.key)))

function docsForType(key: string): DocumentOut[] {
  return allDocs.value.filter(d => d.type_document === key)
}

const otherDocs = computed(() =>
  allDocs.value.filter(d => !knownKeys.value.has(d.type_document))
)

const uploadedCount = computed(() =>
  applicableDocs.value.filter(r => docsForType(r.key).length > 0).length
)

const missingMandatory = computed(() =>
  applicableDocs.value.filter(r => r.obligatoire === true && docsForType(r.key).length === 0).length
)

// ── Lifecycle ──────────────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    allDocs.value = await dossiersService.listDocuments(props.dossier.id)
  } finally {
    loading.value = false
  }
})

// ── Interactions ───────────────────────────────────────────────────────────────

function toggleExpand(key: string) {
  expanded.value = expanded.value === key ? '' : key
}

function setInputRef(key: string, el: unknown) {
  inputRefs.value[key] = el as HTMLInputElement | null
}

function triggerInput(key: string) {
  inputRefs.value[key]?.click()
}

function onDrop(e: DragEvent, key: string) {
  dragging.value = ''
  const file = e.dataTransfer?.files?.[0]
  if (file) upload(file, key)
}

function onFileChange(e: Event, key: string) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) upload(file, key)
}

async function upload(file: File, key: string) {
  if (file.size > 20 * 1024 * 1024) {
    uploadErrors.value[key] = 'Fichier trop volumineux (max 20 Mo).'
    return
  }
  uploadErrors.value[key] = ''
  uploadProgress.value[key] = 0

  try {
    const form = new FormData()
    form.append('file', file)
    form.append('type_document', key)

    const { default: api } = await import('@/services/auth')
    const { data } = await api.post<DocumentOut>(
      `/dossiers/${props.dossier.id}/documents`,
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          uploadProgress.value[key] = e.total ? Math.round((e.loaded / e.total) * 100) : 50
        },
      }
    )
    allDocs.value.push(data)
    expanded.value = ''
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: string } } }
    uploadErrors.value[key] = e?.response?.data?.detail ?? 'Erreur lors de l\'envoi.'
  } finally {
    delete uploadProgress.value[key]
    if (inputRefs.value[key]) inputRefs.value[key]!.value = ''
  }
}

async function downloadDoc(doc: DocumentOut) {
  try {
    const blob = await dossiersService.downloadDocument(doc.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = doc.nom_fichier
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    // silent
  }
}

function confirmDelete(doc: DocumentOut) {
  docToDelete.value = doc
}

async function doDelete() {
  if (!docToDelete.value) return
  deleting.value = true
  try {
    await dossiersService.deleteDocument(docToDelete.value.id)
    allDocs.value = allDocs.value.filter(d => d.id !== docToDelete.value?.id)
    docToDelete.value = null
  } finally {
    deleting.value = false
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`
  return `${(bytes / 1024 / 1024).toFixed(1)} Mo`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}
</script>

<style scoped>
.docs-panel { display: flex; flex-direction: column; gap: 1.25rem; }

/* Header */
.panel-header { display: flex; align-items: center; justify-content: space-between; }
.panel-title  { font-size: 0.9375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.panel-subtitle { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0; display: flex; gap: 0.375rem; align-items: center; }
.sep { color: var(--color-border); }
.summary-ok      { color: var(--color-status-valide); font-weight: 600; }
.summary-missing { color: var(--color-risk-high); font-weight: 600; }
.compliant-badge { display: flex; align-items: center; gap: 0.375rem; background: var(--color-status-valide-bg); color: var(--color-status-valide); border-radius: 8px; padding: 0.375rem 0.75rem; font-size: 0.75rem; font-weight: 600; }
.compliant-badge svg { width: 14px; height: 14px; }

.panel-loading { padding: 2rem; text-align: center; font-size: 0.875rem; color: var(--color-text-muted); }

/* Document group */
.doc-group { display: flex; flex-direction: column; gap: 0.5rem; }
.doc-group--other { border-top: 1px solid var(--color-border); padding-top: 1rem; }
.group-title { font-size: 0.6875rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); margin: 0 0 0.5rem; }

/* Document row */
.doc-row { border: 1px solid var(--color-border); border-radius: 9px; overflow: hidden; background: var(--color-bg-card); }
.doc-row--ok { border-color: var(--color-status-valide); background: var(--color-status-valide-bg); }
.doc-row--ok .doc-row-main { background: var(--color-status-valide-bg); }

.doc-row-main { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; cursor: pointer; user-select: none; }
.doc-row-main:hover { background: var(--color-bg-page); }
.doc-row--ok .doc-row-main:hover { background: color-mix(in srgb, var(--color-status-valide-bg) 80%, white); }

.doc-status-icon { flex-shrink: 0; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; }
.icon-ok      { width: 20px; height: 20px; stroke: var(--color-status-valide); }
.icon-missing { width: 20px; height: 20px; stroke: var(--color-risk-medium); }

.doc-info { flex: 1; min-width: 0; }
.doc-label     { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-primary); margin: 0 0 0.125rem; }
.doc-condition { font-size: 0.6875rem; color: var(--color-text-muted); margin: 0; }

.oblig-chip { border-radius: 10px; padding: 2px 8px; font-size: 0.625rem; font-weight: 700; flex-shrink: 0; }
.oblig--required { background: rgba(201,162,39,0.12); color: var(--color-sidebar-bg); }
.oblig--optional { background: var(--color-bg-page); color: var(--color-text-secondary); border: 1px solid var(--color-border); }

.add-chip { display: inline-flex; align-items: center; gap: 0.25rem; border: none; border-radius: 7px; padding: 0.25rem 0.625rem; font-size: 0.6875rem; font-weight: 600; cursor: pointer; background: var(--color-sidebar-bg); color: #fff; flex-shrink: 0; }
.add-chip--secondary { background: var(--color-bg-page); color: var(--color-text-secondary); border: 1px solid var(--color-border); }
.add-chip svg { width: 11px; height: 11px; }
.add-chip:hover { opacity: 0.85; }

/* Uploaded files */
.doc-files { display: flex; flex-direction: column; gap: 0; border-top: 1px solid var(--color-border); }
.doc-file { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; font-size: 0.8125rem; background: rgba(255,255,255,0.5); border-bottom: 1px solid var(--color-border); }
.doc-file:last-child { border-bottom: none; }
.doc-file--other { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; }
.file-icon { width: 15px; height: 15px; stroke: var(--color-text-muted); flex-shrink: 0; }
.file-name { flex: 1; font-weight: 500; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.125rem; }
.file-type-tag { font-size: 0.6875rem; color: var(--color-text-muted); }
.file-size { font-size: 0.6875rem; color: var(--color-text-muted); white-space: nowrap; }
.file-date { font-size: 0.6875rem; color: var(--color-text-muted); white-space: nowrap; }
.dl-btn, .del-btn { background: none; border: none; cursor: pointer; padding: 3px; border-radius: 4px; display: flex; }
.dl-btn  { color: var(--color-sidebar-bg); }
.del-btn { color: var(--color-text-muted); }
.dl-btn:hover  { background: rgba(201,162,39,0.1); }
.del-btn:hover { color: var(--color-risk-high); background: var(--color-risk-high-bg); }
.dl-btn svg, .del-btn svg { width: 15px; height: 15px; }

/* Inline upload zone */
.doc-upload-zone { border-top: 1px dashed var(--color-border); padding: 0.875rem 1rem; background: var(--color-bg-page); display: flex; flex-direction: column; gap: 0.5rem; }
.upload-label { font-size: 0.75rem; color: var(--color-text-secondary); }
.hidden-input { display: none; }
.drop-area {
  border: 2px dashed var(--color-border); border-radius: 8px;
  display: flex; align-items: center; justify-content: center; gap: 0.625rem;
  padding: 1rem; cursor: pointer; transition: border-color 0.12s, background 0.12s;
}
.drop-area:hover, .drop-area--drag { border-color: var(--color-accent-gold); background: rgba(201,162,39,0.04); }
.drop-icon { width: 20px; height: 20px; stroke: var(--color-text-muted); }
.drop-text { font-size: 0.8125rem; color: var(--color-text-secondary); font-weight: 500; }
.upload-progress { height: 4px; background: var(--color-border); border-radius: 2px; overflow: hidden; }
.progress-bar { height: 100%; background: var(--color-accent-gold); border-radius: 2px; transition: width 0.2s; }
.upload-err { font-size: 0.75rem; color: var(--color-risk-high); margin: 0; }

/* Delete modal */
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 300; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.confirm-modal { background: var(--color-bg-card); border-radius: 10px; box-shadow: 0 12px 40px rgba(0,0,0,0.15); padding: 1.5rem; max-width: 380px; width: 100%; }
.confirm-text { font-size: 0.9375rem; color: var(--color-text-primary); margin: 0 0 0.5rem; }
.confirm-note { font-size: 0.75rem; color: var(--color-text-muted); margin: 0 0 1.25rem; }
.confirm-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
.btn-ghost  { padding: 0.5rem 0.875rem; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 0.8125rem; cursor: pointer; }
.btn-danger { padding: 0.5rem 0.875rem; border: none; border-radius: 8px; background: var(--color-status-bloque); color: #fff; font-size: 0.8125rem; cursor: pointer; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
