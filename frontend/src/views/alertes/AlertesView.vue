<template>
  <div class="alerts-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Alertes & Supervision</h1>
        <p class="page-subtitle">{{ stats.ouvertes }} alerte(s) ouverte(s) · mise à jour toutes les 10s</p>
      </div>
      <div class="header-actions">
        <select v-model="filters.niveau" class="filter-select" @change="loadAlertes">
          <option value="">Tous les niveaux</option>
          <option value="CRITIQUE">Critique</option>
          <option value="ELEVE">Élevé</option>
          <option value="MOYEN">Moyen</option>
          <option value="INFO">Info</option>
        </select>
        <select v-model="filters.statut" class="filter-select" @change="loadAlertes">
          <option value="">Tous les statuts</option>
          <option value="OUVERTE">Ouvertes</option>
          <option value="TRAITEE">Traitées</option>
        </select>
        <select v-model="filters.type_alerte" class="filter-select" @change="loadAlertes">
          <option value="">Tous les types</option>
          <option v-for="t in ALERT_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>
        <select v-model="filters.dossier_statut" class="filter-select" @change="loadAlertes">
          <option value="">Tous les dossiers</option>
          <option value="bloque">Dossiers bloqués</option>
          <option value="en_analyse">Dossiers en analyse</option>
        </select>
      </div>
    </div>

    <!-- WRK-09 Pending section (Notaire Principal only) -->
    <section v-if="isNotairePrincipal && pendingWrk09.length > 0" class="wrk09-section">
      <div class="section-header">
        <span class="section-badge critique">WRK-09</span>
        <h2 class="section-title">Autorisations Notaire Principal PPE en attente ({{ pendingWrk09.length }})</h2>
      </div>
      <div class="wrk09-list">
        <div v-for="item in pendingWrk09" :key="item.dossier_id" class="wrk09-card">
          <div class="wrk09-info">
            <span class="wrk09-ref">{{ item.dossier_reference }}</span>
            <span class="risk-badge" :class="riskClass(item.niveau_risque)">{{ item.niveau_risque ?? 'N/A' }}</span>
            <span class="wrk09-type">{{ item.type_dossier }}</span>
            <span class="wrk09-date">{{ formatDate(item.created_at) }}</span>
          </div>
          <div class="wrk09-actions">
            <button class="btn-autoriser" @click="openWrk09Dialog(item, 'AUTORISE')">✓ Autoriser</button>
            <button class="btn-refuser" @click="openWrk09Dialog(item, 'REFUSE')">✗ Refuser</button>
          </div>
        </div>
      </div>
    </section>

    <!-- Alertes list -->
    <section class="alertes-section">
      <div v-if="loading" class="alertes-list">
        <div class="skeleton" v-for="i in 5" :key="i"></div>
      </div>

      <div v-else-if="alertes.length === 0" class="empty-state">
        <div class="empty-icon">✓</div>
        <p>Aucune alerte correspondant aux filtres sélectionnés.</p>
      </div>

      <div v-else class="alertes-list">
        <div
          v-for="alerte in alertes"
          :key="alerte.id"
          class="alerte-card"
          :class="{ 'is-traitee': alerte.statut === 'TRAITEE' }"
        >
          <div class="alerte-level" :class="levelClass(alerte.niveau)"></div>

          <div class="alerte-body">
            <div class="alerte-header">
              <span class="alerte-type">{{ typeLabel(alerte.type_alerte) }}</span>
              <span v-if="alerte.dossier_reference" class="alerte-dossier">
                Dossier : <strong>{{ alerte.dossier_reference }}</strong>
              </span>
              <span class="alerte-date">{{ formatDate(alerte.created_at) }}</span>
              <span class="alerte-statut" :class="alerte.statut === 'TRAITEE' ? 'statut-traitee' : 'statut-ouverte'">
                {{ alerte.statut === 'TRAITEE' ? 'Traitée' : 'Ouverte' }}
              </span>
            </div>
            <p class="alerte-description">{{ alerte.description }}</p>
            <p v-if="alerte.statut === 'TRAITEE' && alerte.justification_traitement" class="alerte-justification">
              <em>Justification :</em> {{ alerte.justification_traitement }}
            </p>
          </div>

          <div v-if="alerte.statut === 'OUVERTE'" class="alerte-actions">
            <button class="btn-traiter" @click="openTraiterDialog(alerte)">Traiter</button>
            <button
              v-if="alerte.dossier_id && alerte.dossier_statut !== 'bloque'"
              class="btn-bloquer"
              @click="confirmBloquer(alerte)"
            >Bloquer dossier</button>
            <button
              v-if="alerte.dossier_id && alerte.dossier_statut === 'bloque'"
              class="btn-debloquer"
              @click="confirmDebloquer(alerte)"
            >Débloquer dossier</button>
          </div>
        </div>
      </div>

      <div v-if="!loading" class="pagination">
        <button :disabled="page === 1" class="btn-page" @click="changePage(page - 1)">←</button>
        <span class="page-info">Page {{ page }} / {{ totalPages }} · {{ total }} alerte(s)</span>
        <button :disabled="page >= totalPages" class="btn-page" @click="changePage(page + 1)">→</button>
      </div>
    </section>

    <!-- Traiter Dialog -->
    <div v-if="traiterDialog.open" class="dialog-overlay" @click.self="traiterDialog.open = false">
      <div class="dialog">
        <h3 class="dialog-title">Traiter l'alerte</h3>
        <p class="dialog-subtitle">{{ typeLabel(traiterDialog.alerte?.type_alerte ?? '') }}</p>
        <label class="dialog-label">Justification <span class="required">*</span></label>
        <textarea
          v-model="traiterDialog.justification"
          class="dialog-textarea"
          placeholder="Décrivez l'action menée et le résultat de votre analyse..."
          rows="4"
        ></textarea>
        <p v-if="traiterDialog.error" class="dialog-error">{{ traiterDialog.error }}</p>
        <div class="dialog-footer">
          <button class="btn-cancel" @click="traiterDialog.open = false">Annuler</button>
          <button class="btn-confirm" :disabled="traiterDialog.loading" @click="submitTraiter">
            {{ traiterDialog.loading ? 'Enregistrement…' : 'Confirmer traitement' }}
          </button>
        </div>
      </div>
    </div>

    <!-- WRK-09 Dialog -->
    <div v-if="wrk09Dialog.open" class="dialog-overlay" @click.self="wrk09Dialog.open = false">
      <div class="dialog dialog-wrk09">
        <div class="wrk09-header">
          <span class="wrk09-badge">WRK-09</span>
          <h3 class="dialog-title">
            {{ wrk09Dialog.decision === 'AUTORISE' ? 'Autoriser le dossier PPE' : 'Refuser le dossier PPE' }}
          </h3>
        </div>
        <p class="dialog-subtitle">Dossier : <strong>{{ wrk09Dialog.item?.dossier_reference }}</strong></p>
        <p class="wrk09-warning">
          Cette décision est <strong>non délégable et non modifiable</strong>. Elle sera enregistrée dans le Registre des autorisations Notaire Principal.
        </p>
        <label class="dialog-label">
          Justification<span v-if="wrk09Dialog.decision === 'REFUSE'" class="required"> *</span>
        </label>
        <textarea
          v-model="wrk09Dialog.justification"
          class="dialog-textarea"
          :placeholder="wrk09Dialog.decision === 'REFUSE' ? 'Motif du refus (obligatoire)…' : 'Observations (optionnel)…'"
          rows="3"
        ></textarea>
        <p v-if="wrk09Dialog.error" class="dialog-error">{{ wrk09Dialog.error }}</p>
        <div class="dialog-footer">
          <button class="btn-cancel" @click="wrk09Dialog.open = false">Annuler</button>
          <button
            :class="wrk09Dialog.decision === 'AUTORISE' ? 'btn-autoriser' : 'btn-refuser'"
            :disabled="wrk09Dialog.loading"
            @click="submitWrk09"
          >
            {{ wrk09Dialog.loading ? 'Enregistrement…' : (wrk09Dialog.decision === 'AUTORISE' ? '✓ Confirmer autorisation' : '✗ Confirmer refus') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { alertesService, type AlerteOut, type PendingWrk09Item } from '@/services/alertes'

const auth = useAuthStore()
const isNotairePrincipal = computed(() => auth.user?.role === 'notaire_principal')

const alertes = ref<AlerteOut[]>([])
const pendingWrk09 = ref<PendingWrk09Item[]>([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const stats = ref({ ouvertes: 0 })

const filters = ref({ niveau: '', statut: 'OUVERTE', type_alerte: '', dossier_statut: '' })
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const traiterDialog = ref({
  open: false, alerte: null as AlerteOut | null,
  justification: '', loading: false, error: '',
})
const wrk09Dialog = ref({
  open: false, item: null as PendingWrk09Item | null,
  decision: 'AUTORISE' as 'AUTORISE' | 'REFUSE',
  justification: '', loading: false, error: '',
})

async function loadAlertes(silent = false) {
  if (!silent) loading.value = true
  try {
    const res = await alertesService.list({
      page: page.value, page_size: pageSize,
      ...(filters.value.niveau ? { niveau: filters.value.niveau } : {}),
      ...(filters.value.statut ? { statut: filters.value.statut } : {}),
      ...(filters.value.type_alerte ? { type_alerte: filters.value.type_alerte } : {}),
      ...(filters.value.dossier_statut ? { dossier_statut: filters.value.dossier_statut } : {}),
    })
    alertes.value = res.items
    total.value = res.total
  } finally {
    if (!silent) loading.value = false
  }
}

async function loadStats() {
  try {
    const res = await alertesService.list({ statut: 'OUVERTE', page_size: 1 })
    stats.value.ouvertes = res.total
  } catch { /* ignore */ }
}

async function loadPendingWrk09() {
  if (!isNotairePrincipal.value) return
  try { pendingWrk09.value = await alertesService.pendingWrk09() } catch { /* ignore */ }
}

async function loadAll(silent = false) {
  await Promise.all([loadAlertes(silent), loadStats(), loadPendingWrk09()])
}

let pollInterval: ReturnType<typeof setInterval>
onMounted(() => { loadAll(); pollInterval = setInterval(() => loadAll(true), 10_000) })
onUnmounted(() => clearInterval(pollInterval))

function changePage(p: number) { page.value = p; loadAlertes() }

function openTraiterDialog(alerte: AlerteOut) {
  traiterDialog.value = { open: true, alerte, justification: '', loading: false, error: '' }
}

async function submitTraiter() {
  const d = traiterDialog.value
  if (!d.alerte) return
  if (!d.justification.trim()) { d.error = 'La justification est obligatoire.'; return }
  d.loading = true; d.error = ''
  try {
    await alertesService.traiter(d.alerte.id, d.justification)
    d.open = false
    await Promise.all([loadAlertes(), loadStats()])
  } catch (err: unknown) {
    d.error = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur serveur.'
  } finally { d.loading = false }
}

async function confirmBloquer(alerte: AlerteOut) {
  if (!confirm(`Bloquer le dossier ${alerte.dossier_reference ?? alerte.dossier_id} ?`)) return
  try {
    await alertesService.bloquerDossier(alerte.id)
    await loadAlertes()
  } catch (err: unknown) {
    alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur serveur.')
  }
}

async function confirmDebloquer(alerte: AlerteOut) {
  if (!confirm(`Débloquer le dossier ${alerte.dossier_reference ?? alerte.dossier_id} ?`)) return
  try {
    await alertesService.debloquerDossier(alerte.id)
    await loadAlertes()
  } catch (err: unknown) {
    alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur serveur.')
  }
}

function openWrk09Dialog(item: PendingWrk09Item, decision: 'AUTORISE' | 'REFUSE') {
  wrk09Dialog.value = { open: true, item, decision, justification: '', loading: false, error: '' }
}

async function submitWrk09() {
  const d = wrk09Dialog.value
  if (!d.item) return
  if (d.decision === 'REFUSE' && !d.justification.trim()) {
    d.error = 'La justification est obligatoire en cas de refus.'; return
  }
  d.loading = true; d.error = ''
  try {
    await alertesService.createAutorisation(d.item.dossier_id, d.decision, d.justification || undefined)
    pendingWrk09.value = pendingWrk09.value.filter(i => i.dossier_id !== d.item!.dossier_id)
    d.open = false
    await loadAlertes()
  } catch (err: unknown) {
    d.error = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur serveur.'
  } finally { d.loading = false }
}

const ALERT_TYPES = [
  { value: 'TRIGGER_T1', label: 'T1 — PPE détecté' },
  { value: 'TRIGGER_T2', label: 'T2 — Espèces > 15M FCFA' },
  { value: 'TRIGGER_T3', label: 'T3 — Sanctions (Blocage Art. 89)' },
  { value: 'TRIGGER_T4', label: 'T4 — Pays liste grise GAFI' },
  { value: 'TRIGGER_T5', label: 'T5 — Refus documentaire' },
  { value: 'TRIGGER_T6', label: 'T6 — BE non identifiable' },
  { value: 'TRIGGER_T7', label: 'T7 — Espèces ≥ Art. 74 (immo)' },
  { value: 'TRIGGER_T8', label: 'T8 — Pays liste noire GAFI' },
  { value: 'PRESSE_NEGATIVE', label: 'Presse négative PPE' },
  { value: 'BIEN_TRANSACTIONS', label: '>2 transactions / 24 mois (même bien)' },
  { value: 'INCOHERENCE_DOC', label: 'Incohérence documentaire (Axe 8)' },
  { value: 'MANDANT_NON_IDENTIFIE', label: 'Mandant non identifié (compte tiers)' },
  { value: 'SANCTIONS_PERIMEES', label: 'Correspondance listes de sanctions' },
  { value: 'SIGNALEMENT_INTERNE', label: 'Signalement interne (agent)' },
]

function typeLabel(type: string) {
  return ALERT_TYPES.find(t => t.value === type)?.label ?? type
}
function levelClass(niveau: string) {
  return ({ CRITIQUE: 'level-critique', ELEVE: 'level-eleve', MOYEN: 'level-moyen', INFO: 'level-info' } as Record<string, string>)[niveau] ?? ''
}
function riskClass(niveau: string | null) {
  return ({ ELEVE: 'risk-high', MOYEN: 'risk-medium', FAIBLE: 'risk-low' } as Record<string, string>)[niveau ?? ''] ?? ''
}
function formatDate(iso: string) {
  return new Date(iso).toLocaleString('fr-CI', { dateStyle: 'short', timeStyle: 'short' })
}
</script>

<style scoped>
.alerts-page { display: flex; flex-direction: column; gap: 1.5rem; }

.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; flex-wrap: wrap; }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.813rem; color: var(--color-text-secondary); margin: 0; }
.header-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.filter-select {
  padding: 0.4rem 0.75rem; border: 1.5px solid var(--color-border);
  border-radius: 6px; font-size: 0.813rem; background: var(--color-bg-card);
  color: var(--color-text-primary); cursor: pointer;
}

.wrk09-section { background: #fff8f0; border: 2px solid #d97706; border-radius: 8px; padding: 1rem 1.25rem; }
.section-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; }
.section-badge { font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; }
.section-badge.critique { background: #fee2e2; color: #dc2626; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--color-text-primary); margin: 0; }
.wrk09-list { display: flex; flex-direction: column; gap: 0.5rem; }
.wrk09-card {
  display: flex; justify-content: space-between; align-items: center;
  background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 0.625rem 1rem; gap: 1rem;
}
.wrk09-info { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.wrk09-ref { font-weight: 600; font-size: 0.875rem; color: var(--color-text-primary); }
.wrk09-type, .wrk09-date { font-size: 0.75rem; color: var(--color-text-muted); }
.wrk09-actions { display: flex; gap: 0.5rem; }

.risk-badge { font-size: 0.688rem; font-weight: 700; padding: 2px 8px; border-radius: 12px; }
.risk-high { background: #fee2e2; color: #dc2626; }
.risk-medium { background: #fef3c7; color: #d97706; }
.risk-low { background: #dcfce7; color: #16a34a; }

.alertes-section { display: flex; flex-direction: column; gap: 0.75rem; }
.alertes-list { display: flex; flex-direction: column; gap: 0.5rem; }
.alerte-card {
  display: flex; align-items: stretch; background: var(--color-bg-card);
  border: 1px solid var(--color-border); border-radius: 8px; overflow: hidden; transition: box-shadow 0.15s;
}
.alerte-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.alerte-card.is-traitee { opacity: 0.65; }
.alerte-level { width: 8px; flex-shrink: 0; }
.level-critique { background: #dc2626; }
.level-eleve { background: #d97706; }
.level-moyen { background: #f59e0b; }
.level-info { background: #2563eb; }
.alerte-body { flex: 1; padding: 0.75rem 1rem; }
.alerte-header { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.25rem; }
.alerte-type { font-size: 0.813rem; font-weight: 600; color: var(--color-text-primary); }
.alerte-dossier { font-size: 0.75rem; color: var(--color-text-secondary); }
.alerte-date { font-size: 0.75rem; color: var(--color-text-muted); margin-left: auto; }
.alerte-statut { font-size: 0.688rem; font-weight: 600; padding: 2px 8px; border-radius: 12px; }
.statut-ouverte { background: #fee2e2; color: #dc2626; }
.statut-traitee { background: #dcfce7; color: #16a34a; }
.alerte-description { font-size: 0.813rem; color: var(--color-text-secondary); margin: 0; }
.alerte-justification { font-size: 0.75rem; color: var(--color-text-muted); margin: 0.25rem 0 0; }
.alerte-actions {
  display: flex; flex-direction: column; justify-content: center; gap: 0.375rem;
  padding: 0.75rem; border-left: 1px solid var(--color-border);
}

.skeleton {
  height: 64px; border-radius: 8px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

.empty-state { display: flex; flex-direction: column; align-items: center; padding: 3rem; color: var(--color-text-muted); gap: 0.5rem; }
.empty-icon { font-size: 2.5rem; color: #16a34a; }
.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; padding: 0.5rem 0; }
.page-info { font-size: 0.813rem; color: var(--color-text-secondary); }

.btn-traiter, .btn-bloquer, .btn-debloquer, .btn-autoriser, .btn-refuser, .btn-cancel, .btn-confirm, .btn-page {
  padding: 0.375rem 0.75rem; border-radius: 6px; font-size: 0.75rem;
  font-weight: 600; cursor: pointer; border: none; white-space: nowrap;
}
.btn-traiter { background: #1b2b4b; color: #fff; }
.btn-traiter:hover { background: #243750; }
.btn-bloquer { background: #fee2e2; color: #dc2626; }
.btn-bloquer:hover { background: #fecaca; }
.btn-debloquer { background: #dcfce7; color: #16a34a; }
.btn-debloquer:hover { background: #bbf7d0; }
.btn-autoriser { background: #16a34a; color: #fff; }
.btn-autoriser:hover:not(:disabled) { background: #15803d; }
.btn-refuser { background: #dc2626; color: #fff; }
.btn-refuser:hover:not(:disabled) { background: #b91c1c; }
.btn-cancel { background: #f1f5f9; color: var(--color-text-secondary); }
.btn-confirm { background: var(--color-accent-gold, #c9a227); color: #fff; }
.btn-confirm:disabled, .btn-autoriser:disabled, .btn-refuser:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-page { background: var(--color-bg-card); border: 1px solid var(--color-border); }
.btn-page:disabled { opacity: 0.4; cursor: not-allowed; }

.dialog-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.dialog {
  background: var(--color-bg-card); border-radius: 12px; padding: 1.5rem;
  width: 100%; max-width: 480px; display: flex; flex-direction: column; gap: 0.75rem;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}
.dialog-wrk09 { max-width: 520px; }
.wrk09-header { display: flex; align-items: center; gap: 0.75rem; }
.wrk09-badge { font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 4px; background: #fef3c7; color: #d97706; }
.dialog-title { font-size: 1.1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.dialog-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }
.wrk09-warning {
  font-size: 0.813rem; background: #fff8f0; border: 1px solid #f59e0b;
  border-radius: 6px; padding: 0.625rem; color: #92400e; margin: 0;
}
.dialog-label { font-size: 0.813rem; font-weight: 600; color: var(--color-text-primary); }
.required { color: #dc2626; }
.dialog-textarea {
  width: 100%; border: 1.5px solid var(--color-border); border-radius: 8px;
  padding: 0.625rem; font-size: 0.875rem; resize: vertical; font-family: inherit;
  background: #f8fafc; box-sizing: border-box;
}
.dialog-textarea:focus { outline: none; border-color: var(--color-accent-gold, #c9a227); }
.dialog-error { font-size: 0.813rem; color: #dc2626; margin: 0; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.25rem; }
</style>
