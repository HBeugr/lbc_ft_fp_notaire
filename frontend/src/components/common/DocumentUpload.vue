<template>
  <div class="doc-upload">
    <div
      class="drop-zone"
      :class="{ 'drop-zone--drag': isDragging, 'drop-zone--error': uploadError }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
    >
      <input
        ref="inputRef"
        type="file"
        class="file-input"
        :accept="accept"
        @change="onFileChange"
      />

      <div v-if="!uploading && !uploaded" class="drop-content" @click="inputRef?.click()">
        <svg class="drop-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <p class="drop-label">Cliquer ou glisser-déposer</p>
        <p class="drop-hint">PDF, JPG, PNG · Max {{ maxMbLabel }}</p>
      </div>

      <!-- Uploading -->
      <div v-else-if="uploading" class="drop-content">
        <svg class="upload-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0"/>
        </svg>
        <p class="drop-label">Chiffrement et envoi…</p>
        <div class="progress-track"><div class="progress-fill" :style="{ width: `${progress}%` }"/></div>
      </div>

      <!-- Uploaded -->
      <div v-else-if="uploaded" class="upload-done">
        <svg class="done-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <div class="done-info">
          <p class="done-filename">{{ uploaded.filename }}</p>
          <p class="done-meta">{{ uploaded.size }} · SHA-256 : <code class="hash-code">{{ uploaded.sha256.slice(0, 16) }}…</code></p>
        </div>
        <button class="btn-remove" type="button" @click="reset">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Error -->
    <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/services/api'

const props = withDefaults(defineProps<{
  dossierId: string
  documentType: string
  accept?: string
  maxMb?: number
}>(), {
  accept: '.pdf,.jpg,.jpeg,.png',
  maxMb: 20,
})

const emit = defineEmits<{
  uploaded: [{ documentId: string; sha256: string; filename: string }]
}>()

interface UploadedFile {
  filename: string
  size: string
  sha256: string
  documentId: string
}

const inputRef  = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const uploading  = ref(false)
const progress   = ref(0)
const uploaded   = ref<UploadedFile | null>(null)
const uploadError = ref('')

const maxMbLabel = `${props.maxMb} Mo`

function formatSize(bytes: number): string {
  if (bytes < 1024)          return `${bytes} o`
  if (bytes < 1024 * 1024)   return `${(bytes / 1024).toFixed(0)} Ko`
  return `${(bytes / 1024 / 1024).toFixed(1)} Mo`
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) processFile(file)
}

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) processFile(file)
}

async function processFile(file: File) {
  uploadError.value = ''
  if (file.size > props.maxMb * 1024 * 1024) {
    uploadError.value = `Fichier trop volumineux (max ${props.maxMb} Mo).`
    return
  }

  uploading.value = true
  progress.value  = 0

  const formData = new FormData()
  formData.append('file', file)
  formData.append('type_document', props.documentType)

  try {
    const resp = await api.post(
      `/dossiers/${props.dossierId}/documents`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          progress.value = e.total ? Math.round((e.loaded / e.total) * 100) : 50
        },
      },
    )
    uploaded.value = {
      filename:   file.name,
      size:       formatSize(file.size),
      sha256:     resp.data.sha256,
      documentId: resp.data.document_id,
    }
    emit('uploaded', { documentId: resp.data.document_id, sha256: resp.data.sha256, filename: file.name })
  } catch (err: any) {
    uploadError.value = err?.response?.data?.detail ?? 'Erreur lors de l\'envoi. Veuillez réessayer.'
  } finally {
    uploading.value = false
  }
}

function reset() {
  uploaded.value  = null
  uploadError.value = ''
  progress.value  = 0
  if (inputRef.value) inputRef.value.value = ''
}
</script>

<style scoped>
.doc-upload { display: flex; flex-direction: column; gap: 0.375rem; }

.drop-zone {
  border: 2px dashed var(--color-border); border-radius: 8px;
  background: var(--color-bg-page); cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  min-height: 90px; display: flex; align-items: center; justify-content: center;
}
.drop-zone--drag  { border-color: var(--color-accent-gold); background: #fefce8; }
.drop-zone--error { border-color: var(--color-risk-high); }
.drop-zone:hover  { border-color: var(--color-text-secondary); }

.file-input { display: none; }

.drop-content { display: flex; flex-direction: column; align-items: center; gap: 0.375rem; padding: 1.25rem; }
.drop-icon { width: 28px; height: 28px; stroke: var(--color-text-muted); }
.drop-label { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-secondary); margin: 0; }
.drop-hint  { font-size: 0.75rem; color: var(--color-text-muted); margin: 0; }

.upload-spinner { width: 24px; height: 24px; stroke: var(--color-accent-gold); animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.progress-track { width: 120px; height: 4px; background: var(--color-border); border-radius: 2px; overflow: hidden; margin-top: 0.25rem; }
.progress-fill  { height: 100%; background: var(--color-accent-gold); border-radius: 2px; transition: width 0.2s; }

.upload-done {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.625rem 0.875rem; width: 100%;
}
.done-icon { width: 20px; height: 20px; flex-shrink: 0; stroke: var(--color-risk-low); }
.done-info { flex: 1; overflow: hidden; }
.done-filename { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-primary); margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.done-meta     { font-size: 0.6875rem; color: var(--color-text-muted); margin: 0; }
.hash-code     { font-family: monospace; font-size: 0.6875rem; background: var(--color-border); padding: 1px 4px; border-radius: 3px; }

.btn-remove {
  flex-shrink: 0; background: none; border: none; cursor: pointer;
  padding: 4px; border-radius: 4px; color: var(--color-text-muted);
  display: flex; align-items: center; justify-content: center;
}
.btn-remove svg { width: 16px; height: 16px; }
.btn-remove:hover { color: var(--color-risk-high); background: var(--color-risk-high-bg); }

.upload-error { font-size: 0.75rem; color: var(--color-risk-high); margin: 0; }
</style>
