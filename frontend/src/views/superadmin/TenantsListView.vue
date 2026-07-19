<template>
  <div class="tenants-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Cabinets notariaux</h1>
        <p class="page-subtitle">{{ tenants.length }} cabinet{{ tenants.length !== 1 ? 's' : '' }} enregistré{{ tenants.length !== 1 ? 's' : '' }}</p>
      </div>
      <div class="header-actions">
        <button class="btn-ghost" :disabled="migrating" @click="confirmMigrate = true">
          <span v-if="migrating" class="spinner spinner--dark" />
          Migrer tous les cabinets
        </button>
        <RouterLink :to="{ name: 'super-admin-tenant-create' }" class="btn-primary">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Nouveau cabinet
        </RouterLink>
      </div>
    </div>

    <!-- Filter bar -->
    <div class="filter-bar">
      <input v-model="search" type="search" class="filter-search" placeholder="Rechercher un cabinet…" />
      <select v-model="statutFilter" class="filter-select">
        <option value="">Tous les statuts</option>
        <option v-for="(label, key) in TENANT_STATUT_LABELS" :key="key" :value="key">{{ label }}</option>
      </select>
    </div>

    <div v-if="loadError" class="alert-error">{{ loadError }}</div>

    <!-- Table -->
    <div class="card table-card">
      <div v-if="loading" class="table-loading">Chargement…</div>
      <table v-else class="tenants-table">
        <thead>
          <tr>
            <th>Cabinet</th>
            <th>Pays</th>
            <th>Sièges</th>
            <th>Statut</th>
            <th>Créé le</th>
            <th class="th-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in filteredTenants" :key="t.id" :class="{ 'row--inactive': t.statut === 'archive' }">
            <td class="td-tenant">
              <div class="tenant-avatar">{{ tenantInitials(t) }}</div>
              <div>
                <RouterLink :to="{ name: 'super-admin-tenant-detail', params: { id: t.id } }" class="tenant-name">
                  {{ t.nom_cabinet }}
                </RouterLink>
                <p class="tenant-slug">{{ t.slug }}</p>
              </div>
            </td>
            <td><span class="role-tag">{{ t.pays }}</span></td>
            <td>{{ t.max_users === 0 ? 'Illimité' : t.max_users }}</td>
            <td><span class="badge" :class="`badge--${t.statut}`">{{ TENANT_STATUT_LABELS[t.statut] }}</span></td>
            <td class="td-muted">{{ formatDate(t.created_at) }}</td>
            <td class="td-actions">
              <RouterLink
                :to="{ name: 'super-admin-tenant-detail', params: { id: t.id } }"
                class="action-btn"
                title="Voir le détail"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              </RouterLink>
              <button
                v-if="t.statut !== 'production' && t.statut !== 'archive'"
                class="action-btn action-btn--success"
                title="Activer"
                @click="handleActivate(t)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              </button>
              <button
                v-if="t.statut === 'production'"
                class="action-btn action-btn--warn"
                title="Suspendre"
                @click="openMotif(t, 'suspend')"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="10" y1="15" x2="10" y2="9"/><line x1="14" y1="15" x2="14" y2="9"/></svg>
              </button>
              <button
                v-if="t.statut !== 'archive'"
                class="action-btn action-btn--danger"
                title="Archiver"
                @click="openMotif(t, 'archive')"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
              </button>
            </td>
          </tr>
          <tr v-if="filteredTenants.length === 0">
            <td colspan="6" class="empty-row">Aucun cabinet trouvé</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modale motif (suspension / archivage) -->
    <Teleport to="body">
      <div v-if="motifTarget" class="modal-overlay" @click.self="closeMotif">
        <div class="modal modal--sm" role="dialog">
          <div class="modal-header">
            <h2 class="modal-title">
              {{ motifAction === 'suspend' ? 'Suspendre ce cabinet ?' : 'Archiver ce cabinet ?' }}
            </h2>
          </div>
          <p class="confirm-body">
            <template v-if="motifAction === 'suspend'">
              Les utilisateurs de <strong>{{ motifTarget.nom_cabinet }}</strong> perdront l'accès à la
              plateforme jusqu'à réactivation. Les données sont conservées.
            </template>
            <template v-else>
              <strong>{{ motifTarget.nom_cabinet }}</strong> sera archivé. Cette action retire
              définitivement l'accès ; les données restent conservées 10 ans (Art. 23).
            </template>
          </p>
          <div class="motif-field">
            <label class="field-label">Motif <span class="field-hint">(facultatif)</span></label>
            <textarea v-model="motif" rows="3" class="field-input" placeholder="Motif communiqué au cabinet…" />
          </div>
          <div v-if="actionError" class="alert-error alert-error--modal">{{ actionError }}</div>
          <div class="modal-actions" style="padding:0 1.5rem 1.5rem;">
            <button class="btn-ghost-modal" @click="closeMotif">Annuler</button>
            <button class="btn-danger" :disabled="submitting" @click="handleMotifConfirm">
              <span v-if="submitting" class="spinner" />
              {{ motifAction === 'suspend' ? 'Suspendre' : 'Archiver' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Confirmation migration -->
    <Teleport to="body">
      <div v-if="confirmMigrate" class="modal-overlay" @click.self="confirmMigrate = false">
        <div class="modal modal--sm" role="dialog">
          <div class="modal-header">
            <h2 class="modal-title">Migrer tous les cabinets ?</h2>
          </div>
          <p class="confirm-body">
            Les migrations de schéma seront appliquées à l'ensemble des cabinets.
            L'opération peut prendre plusieurs minutes.
          </p>
          <div class="modal-actions" style="padding:0 1.5rem 1.5rem;">
            <button class="btn-ghost-modal" @click="confirmMigrate = false">Annuler</button>
            <button class="btn-primary" :disabled="migrating" @click="handleMigrate">
              <span v-if="migrating" class="spinner" />
              Lancer la migration
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Résultats de migration -->
    <Teleport to="body">
      <div v-if="migrationResults" class="modal-overlay" @click.self="migrationResults = null">
        <div class="modal" role="dialog">
          <div class="modal-header">
            <h2 class="modal-title">Résultats de la migration</h2>
            <button class="modal-close" aria-label="Fermer" @click="migrationResults = null">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="migration-body">
            <p class="migration-summary">
              {{ migrationOkCount }} réussite{{ migrationOkCount !== 1 ? 's' : '' }} ·
              {{ migrationKoCount }} échec{{ migrationKoCount !== 1 ? 's' : '' }}
            </p>
            <ul class="migration-list">
              <li v-for="(res, slug) in migrationResults" :key="slug" class="migration-item">
                <span class="migration-slug">{{ slug }}</span>
                <span class="migration-status" :class="res === 'ok' ? 'migration--ok' : 'migration--ko'">{{ res }}</span>
              </li>
            </ul>
          </div>
          <div class="modal-actions" style="padding:0 1.5rem 1.5rem;">
            <button class="btn-primary" @click="migrationResults = null">Fermer</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import {
  superAdminService,
  TENANT_STATUT_LABELS,
  type TenantOut,
} from '@/services/superAdmin'

const tenants = ref<TenantOut[]>([])
const loading = ref(true)
const loadError = ref('')
const search = ref('')
const statutFilter = ref('')

const motifTarget = ref<TenantOut | null>(null)
const motifAction = ref<'suspend' | 'archive'>('suspend')
const motif = ref('')
const submitting = ref(false)
const actionError = ref('')

const confirmMigrate = ref(false)
const migrating = ref(false)
const migrationResults = ref<Record<string, string> | null>(null)

const filteredTenants = computed(() => {
  const q = search.value.toLowerCase()
  return tenants.value.filter(t => {
    if (statutFilter.value && t.statut !== statutFilter.value) return false
    if (!q) return true
    return `${t.nom_cabinet} ${t.slug} ${t.contact_email}`.toLowerCase().includes(q)
  })
})

const migrationOkCount = computed(() =>
  Object.values(migrationResults.value ?? {}).filter(v => v === 'ok').length
)
const migrationKoCount = computed(() =>
  Object.values(migrationResults.value ?? {}).filter(v => v !== 'ok').length
)

function tenantInitials(t: TenantOut) {
  return t.nom_cabinet
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0])
    .join('')
    .toUpperCase()
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

async function loadTenants() {
  loading.value = true
  loadError.value = ''
  try {
    tenants.value = await superAdminService.listTenants()
  } catch (err: any) {
    loadError.value = err?.response?.data?.detail ?? 'Impossible de charger la liste des cabinets.'
  } finally {
    loading.value = false
  }
}

onMounted(() => loadTenants())

/** Remplace un cabinet dans la liste après une action, sans recharger tout le tableau. */
function replaceTenant(updated: TenantOut) {
  const idx = tenants.value.findIndex(t => t.id === updated.id)
  if (idx !== -1) tenants.value[idx] = updated
}

async function handleActivate(t: TenantOut) {
  try {
    replaceTenant(await superAdminService.activateTenant(t.id))
  } catch (err: any) {
    loadError.value = err?.response?.data?.detail ?? "Erreur lors de l'activation."
  }
}

function openMotif(t: TenantOut, action: 'suspend' | 'archive') {
  motifTarget.value = t
  motifAction.value = action
  motif.value = ''
  actionError.value = ''
}

function closeMotif() {
  motifTarget.value = null
  actionError.value = ''
}

async function handleMotifConfirm() {
  if (!motifTarget.value) return
  submitting.value = true
  actionError.value = ''
  try {
    const id = motifTarget.value.id
    const m = motif.value.trim() || undefined
    const updated = motifAction.value === 'suspend'
      ? await superAdminService.suspendTenant(id, m)
      : await superAdminService.archiveTenant(id, m)
    replaceTenant(updated)
    closeMotif()
  } catch (err: any) {
    actionError.value = err?.response?.data?.detail ?? 'Une erreur est survenue.'
  } finally {
    submitting.value = false
  }
}

async function handleMigrate() {
  migrating.value = true
  try {
    const res = await superAdminService.migrateAll()
    migrationResults.value = res.resultats
    confirmMigrate.value = false
  } catch (err: any) {
    loadError.value = err?.response?.data?.detail ?? 'Erreur lors de la migration.'
    confirmMigrate.value = false
  } finally {
    migrating.value = false
  }
}
</script>

<style scoped>
.tenants-page { max-width: 1100px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; gap: 1rem; }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }
.header-actions { display: flex; gap: 0.625rem; flex-shrink: 0; }
.btn-icon { width: 14px; height: 14px; margin-right: 0.375rem; vertical-align: middle; }

.btn-primary {
  display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.5rem 1.25rem;
  background: var(--color-btn-primary);
  color: #fff; border: none; border-radius: 7px;
  font-size: 0.875rem; font-weight: 600;
  cursor: pointer; text-decoration: none;
  transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: var(--color-btn-primary-hover); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-ghost {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 1rem;
  background: none; border: 1px solid var(--color-border); border-radius: 7px;
  font-size: 0.875rem; color: var(--color-text-secondary);
  cursor: pointer; transition: border-color 0.12s;
}
.btn-ghost:hover:not(:disabled) { border-color: var(--color-text-secondary); }
.btn-ghost:disabled { opacity: 0.6; cursor: not-allowed; }

.filter-bar { display: flex; gap: 0.75rem; margin-bottom: 1rem; }
.filter-select, .filter-search {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; color: var(--color-text-primary); background: var(--color-bg-card); outline: none; width: auto;
}
.filter-select:focus, .filter-search:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.filter-search { min-width: 220px; }

.alert-error {
  background: var(--color-risk-high-bg); color: var(--color-risk-high);
  border-radius: 7px; padding: 0.625rem 0.875rem; font-size: 0.8125rem; margin-bottom: 1rem;
}
.alert-error--modal { margin: 0 1.5rem 1rem; }

.table-card { padding: 0; overflow: hidden; }
.table-loading { padding: 3rem; text-align: center; color: var(--color-text-muted); font-size: 0.875rem; }
.tenants-table { width: 100%; border-collapse: collapse; }
.tenants-table th {
  background: var(--color-bg-page); padding: 0.625rem 1rem; text-align: left;
  font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary);
  text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--color-border);
}
.tenants-table td {
  padding: 0.875rem 1rem; font-size: 0.8125rem; color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border); vertical-align: middle;
}
.tenants-table tr:last-child td { border-bottom: none; }
.tenants-table tr.row--inactive td { opacity: 0.55; }
.th-actions, .td-actions { text-align: right; white-space: nowrap; }
.td-muted { color: var(--color-text-secondary); }

.td-tenant { display: flex; align-items: center; gap: 0.75rem; }
.tenant-avatar {
  width: 30px; height: 30px; border-radius: 50%;
  background: rgba(27,43,75,0.1); color: var(--color-sidebar-bg);
  font-size: 0.6875rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.tenant-name { font-weight: 500; margin: 0; line-height: 1.3; color: var(--color-text-primary); text-decoration: none; }
.tenant-name:hover { color: var(--color-sidebar-bg); text-decoration: underline; }
.tenant-slug { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0; font-family: monospace; }

.role-tag {
  background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 5px;
  padding: 2px 8px; font-size: 0.75rem; color: var(--color-text-secondary); white-space: nowrap;
}
.badge { border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; white-space: nowrap; }
.badge--production { color: var(--color-risk-low); background: var(--color-risk-low-bg); }
.badge--configuration { color: var(--color-status-en-analyse); background: var(--color-status-en-analyse-bg); }
.badge--suspendu { color: var(--color-risk-high); background: var(--color-risk-high-bg); }
.badge--archive { color: var(--color-status-cloture); background: var(--color-status-cloture-bg); }

.action-btn {
  background: none; border: none; cursor: pointer;
  color: var(--color-text-secondary); padding: 4px; border-radius: 5px;
  transition: background 0.12s, color 0.12s; margin-left: 2px;
  display: inline-flex;
}
.action-btn svg { width: 15px; height: 15px; display: block; }
.action-btn:hover { background: var(--color-bg-page); color: var(--color-text-primary); }
.action-btn--danger:hover { color: var(--color-risk-high); }
.action-btn--success:hover { color: var(--color-risk-low); }
.action-btn--warn:hover { color: var(--color-risk-medium); }
.empty-row { text-align: center; color: var(--color-text-muted); padding: 2.5rem !important; }

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 1.5rem;
}
.modal {
  background: var(--color-bg-card); border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.16);
  width: 100%; max-width: 520px; max-height: 90vh; overflow-y: auto;
}
.modal--sm { max-width: 420px; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem 0; }
.modal-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.modal-close { background: none; border: none; cursor: pointer; color: var(--color-text-muted); display: flex; }
.modal-close svg { width: 18px; height: 18px; }
.modal-close:hover { color: var(--color-text-primary); }
.confirm-body { padding: 0.75rem 1.5rem; font-size: 0.875rem; color: var(--color-text-secondary); line-height: 1.6; margin: 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.625rem; padding-top: 0.25rem; }

.motif-field { padding: 0 1.5rem 1rem; display: flex; flex-direction: column; gap: 0.3rem; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.field-hint { font-size: 0.75rem; color: var(--color-text-muted); font-weight: 400; margin-left: 0.25rem; }
.field-input {
  padding: 0.5625rem 0.75rem; border: 1px solid var(--color-border); border-radius: 7px;
  font-size: 0.875rem; color: var(--color-text-primary); background: #fff; outline: none;
  width: 100%; font-family: inherit; resize: vertical;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field-input:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }

.btn-ghost-modal {
  padding: 0.5rem 1rem; background: none; border: 1px solid var(--color-border);
  border-radius: 7px; font-size: 0.875rem; color: var(--color-text-secondary);
  cursor: pointer; transition: border-color 0.12s;
}
.btn-ghost-modal:hover { border-color: var(--color-text-secondary); }
.btn-danger {
  padding: 0.5rem 1.25rem; background: var(--color-risk-high); color: #fff;
  border: none; border-radius: 7px; font-size: 0.875rem; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; gap: 0.4rem;
}
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

.migration-body { padding: 1rem 1.5rem; display: flex; flex-direction: column; gap: 0.75rem; }
.migration-summary { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; }
.migration-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.25rem; }
.migration-item {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding: 0.5rem 0.75rem; background: var(--color-bg-page);
  border: 1px solid var(--color-border); border-radius: 7px; font-size: 0.8125rem;
}
.migration-slug { font-family: monospace; color: var(--color-text-primary); }
.migration-status { font-weight: 600; font-size: 0.75rem; text-align: right; }
.migration--ok { color: var(--color-risk-low); }
.migration--ko { color: var(--color-risk-high); }

.spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
}
.spinner--dark { border-color: rgba(100,116,139,0.3); border-top-color: var(--color-text-secondary); }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
