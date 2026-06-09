<template>
  <div class="users-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Gestion des utilisateurs</h1>
        <p class="page-subtitle">{{ total }} compte{{ total !== 1 ? 's' : '' }} enregistré{{ total !== 1 ? 's' : '' }}</p>
      </div>
      <button v-if="!isReadOnly" class="btn-primary" @click="openCreate">
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Nouvel utilisateur
      </button>
    </div>

    <!-- Filter bar -->
    <div class="filter-bar">
      <select v-model="filterDept" class="filter-select" @change="loadUsers">
        <option value="">Tous les départements</option>
        <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
      </select>
      <input v-model="search" type="search" class="filter-search" placeholder="Rechercher…" />
    </div>

    <!-- Table -->
    <div class="card table-card">
      <div v-if="loading" class="table-loading">Chargement…</div>
      <table v-else class="users-table">
        <thead>
          <tr>
            <th>Utilisateur</th>
            <th>Rôle</th>
            <th>Département</th>
            <th>2FA</th>
            <th>Statut</th>
            <th class="th-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in filteredUsers" :key="u.id" :class="{ 'row--inactive': !u.is_active }">
            <td class="td-user">
              <div class="user-avatar-sm">{{ initials(u) }}</div>
              <div>
                <p class="user-fullname">{{ u.first_name }} {{ u.last_name }}</p>
                <p class="user-email">{{ u.email }}</p>
              </div>
            </td>
            <td><span class="role-tag">{{ ROLE_LABELS[u.role] ?? u.role }}</span></td>
            <td>{{ deptName(u.department_id) }}</td>
            <td>
              <span v-if="u.totp_enabled" class="badge-ok">Activé</span>
              <span v-else class="badge-off">Non activé</span>
            </td>
            <td>
              <span v-if="u.is_active" class="badge-active">Actif</span>
              <span v-else class="badge-inactive">Désactivé</span>
            </td>
            <td class="td-actions">
              <button class="action-btn" title="Voir les autorisations" @click.stop="openPerms(u)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              </button>
              <button v-if="isAdmin || u.role !== 'admin'" class="action-btn" title="Modifier" @click="openEdit(u)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button
                v-if="u.is_active && (isAdmin || u.role !== 'admin')"
                class="action-btn action-btn--danger"
                title="Désactiver"
                @click="confirmDeactivate(u)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              </button>
              <button
                v-else
                class="action-btn action-btn--success"
                title="Réactiver"
                @click="handleReactivate(u)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              </button>
              <button
                v-if="u.totp_enabled && isAdmin"
                class="action-btn action-btn--warn"
                title="Réinitialiser 2FA"
                @click="handleResetTotp(u)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
              </button>
              <button
                class="action-btn action-btn--warn"
                title="Réinitialiser le mot de passe"
                @click="confirmResetPassword(u)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
              </button>
            </td>
          </tr>
          <tr v-if="filteredUsers.length === 0">
            <td colspan="6" class="empty-row">Aucun utilisateur trouvé</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal création / édition -->
    <Teleport to="body">
      <div v-if="modal.open" class="modal-overlay" @click.self="closeModal">
        <div class="modal" role="dialog">
          <div class="modal-header">
            <h2 class="modal-title">{{ modal.mode === 'create' ? 'Nouvel utilisateur' : 'Modifier l\'utilisateur' }}</h2>
            <button class="modal-close" aria-label="Fermer" @click="closeModal">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <form class="modal-form" @submit.prevent="handleSubmit" novalidate>
            <div class="form-row">
              <div class="field-group">
                <label class="field-label">Prénom</label>
                <input v-model="form.first_name" type="text" class="field-input" :class="{ 'field-input--error': fe.first_name }" />
                <p v-if="fe.first_name" class="field-error">{{ fe.first_name }}</p>
              </div>
              <div class="field-group">
                <label class="field-label">Nom</label>
                <input v-model="form.last_name" type="text" class="field-input" :class="{ 'field-input--error': fe.last_name }" />
                <p v-if="fe.last_name" class="field-error">{{ fe.last_name }}</p>
              </div>
            </div>

            <div class="field-group">
              <label class="field-label">Email</label>
              <input v-model="form.email" type="email" class="field-input" :class="{ 'field-input--error': fe.email }" :disabled="modal.mode === 'edit'" />
              <p v-if="fe.email" class="field-error">{{ fe.email }}</p>
            </div>

            <div class="form-row">
              <div class="field-group">
                <label class="field-label">Rôle</label>
                <select v-model="form.role" class="field-input" :class="{ 'field-input--error': fe.role }">
                  <option value="">— Choisir —</option>
                  <option v-for="(label, key) in availableRoles" :key="key" :value="key">{{ label }}</option>
                </select>
                <p v-if="fe.role" class="field-error">{{ fe.role }}</p>
              </div>
              <div class="field-group">
                <label class="field-label">Département</label>
                <select v-model="form.department_id" class="field-input" :class="{ 'field-input--error': fe.department_id }">
                  <option value="">— Choisir —</option>
                  <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
                </select>
                <p v-if="fe.department_id" class="field-error">{{ fe.department_id }}</p>
              </div>
            </div>

            <div class="field-group">
              <label class="field-label">
                Mot de passe
                <span v-if="modal.mode === 'edit'" class="field-hint">(laisser vide pour conserver)</span>
              </label>
              <input v-model="form.password" type="password" class="field-input" :class="{ 'field-input--error': fe.password }" autocomplete="new-password" />
              <p v-if="fe.password" class="field-error">{{ fe.password }}</p>
            </div>

            <div v-if="formError" class="alert-error">{{ formError }}</div>

            <div class="modal-actions">
              <button type="button" class="btn-ghost-modal" @click="closeModal">Annuler</button>
              <button type="submit" class="btn-primary" :disabled="submitting">
                <span v-if="submitting" class="spinner" />
                {{ modal.mode === 'create' ? 'Créer le compte' : 'Enregistrer' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Confirm reset password -->
    <Teleport to="body">
      <div v-if="resetPwdTarget && !resetPwdResult" class="modal-overlay" @click.self="resetPwdTarget = null">
        <div class="modal modal--sm" role="dialog">
          <div class="modal-header">
            <h2 class="modal-title">Réinitialiser le mot de passe ?</h2>
          </div>
          <p class="confirm-body">
            Un mot de passe temporaire sera généré pour
            <strong>{{ resetPwdTarget.first_name }} {{ resetPwdTarget.last_name }}</strong>.
            Toutes ses sessions actives seront révoquées et il devra changer son mot de passe à la prochaine connexion.
          </p>
          <div class="modal-actions" style="padding:0 1.5rem 1.5rem;">
            <button class="btn-ghost-modal" @click="resetPwdTarget = null">Annuler</button>
            <button class="btn-danger" :disabled="submitting" @click="handleResetPassword">
              <span v-if="submitting" class="spinner" />
              Générer un mot de passe temporaire
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Show generated temp password (one-shot) -->
    <Teleport to="body">
      <div v-if="resetPwdResult" class="modal-overlay">
        <div class="modal modal--sm" role="dialog">
          <div class="modal-header">
            <h2 class="modal-title">Mot de passe temporaire</h2>
          </div>
          <p class="confirm-body">
            Communiquez ce mot de passe à <strong>{{ resetPwdTarget?.first_name }} {{ resetPwdTarget?.last_name }}</strong>.
            Il ne sera plus affiché après fermeture de cette fenêtre.
          </p>
          <div class="temp-pwd-box">
            <code class="temp-pwd-code">{{ resetPwdResult }}</code>
            <button class="btn-copy" :class="{ 'btn-copy--ok': copied }" @click="copyTempPwd">
              <svg v-if="!copied" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
            </button>
          </div>
          <div class="modal-actions" style="padding:0 1.5rem 1.5rem;">
            <button class="btn-primary" @click="closeResetPwd">J'ai noté le mot de passe</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Confirm deactivation -->
    <Teleport to="body">
      <div v-if="confirmTarget" class="modal-overlay" @click.self="confirmTarget = null">
        <div class="modal modal--sm" role="dialog">
          <div class="modal-header">
            <h2 class="modal-title">Désactiver ce compte ?</h2>
          </div>
          <p class="confirm-body">
            Le compte de <strong>{{ confirmTarget.first_name }} {{ confirmTarget.last_name }}</strong>
            sera désactivé et toutes ses sessions actives révoquées immédiatement.
          </p>
          <div class="modal-actions" style="padding:0 1.5rem 1.5rem;">
            <button class="btn-ghost-modal" @click="confirmTarget = null">Annuler</button>
            <button class="btn-danger" :disabled="submitting" @click="handleDeactivate">
              <span v-if="submitting" class="spinner" />
              Désactiver
            </button>
          </div>
        </div>
      </div>
    </Teleport>
    <!-- Modal permissions utilisateur -->
    <Teleport to="body">
      <div v-if="permsTarget" class="modal-overlay" @click.self="permsTarget = null">
        <div class="modal modal--perms" role="dialog">
          <div class="modal-header">
            <h2 class="modal-title">Autorisations — {{ permsTarget.first_name }} {{ permsTarget.last_name }}</h2>
            <button class="modal-close" @click="permsTarget = null">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="perms-body">
            <div class="perms-role">
              <span class="perms-label">Rôle :</span>
              <span class="role-tag">{{ ROLE_LABELS[permsTarget.role] ?? permsTarget.role }}</span>
            </div>
            <div class="perms-section">
              <p class="perms-section-title">Modules accessibles</p>
              <ul class="perms-list">
                <li v-for="m in rolePermissions(permsTarget.role).modules" :key="m">{{ m }}</li>
              </ul>
            </div>
            <div v-if="rolePermissions(permsTarget.role).operations.length > 0" class="perms-section">
              <p class="perms-section-title">Types d'opérations autorisés</p>
              <ul class="perms-list">
                <li v-for="op in rolePermissions(permsTarget.role).operations" :key="op">{{ op }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { usersService, type UserOut, type Department } from '@/services/users'
import { ROLE_LABELS } from '@/utils/roles'

const auth = useAuthStore()
const isReadOnly = computed(() => auth.user?.role === 'responsable_conformite')
const isAdmin   = computed(() => auth.user?.role === 'admin')
const canManageUsers = computed(() => auth.user?.role === 'admin' || auth.user?.role === 'notaire_principal')

// Rôles disponibles selon CDC : Admin → tous ; Dirigeant → tous sauf admin
const availableRoles = computed(() =>
  isAdmin.value
    ? ROLE_LABELS
    : Object.fromEntries(Object.entries(ROLE_LABELS).filter(([k]) => k !== 'admin'))
)

const ROLE_PERMISSIONS: Record<string, { modules: string[]; operations: string[] }> = {
  admin: {
    modules: ['Tableau de bord', 'Dossiers KYC', 'Dossiers de Gels', 'Matrice de risque', 'Alertes', 'Décl. Op. Suspecte', 'Screening sanctions', 'Registres légaux', 'Journal d\'audit', 'Utilisateurs', 'Paramètres'],
    operations: [],
  },
  notaire_principal: {
    modules: ['Tableau de bord', 'Dossiers KYC', 'Dossiers de Gels', 'Matrice de risque', 'Alertes', 'Décl. Op. Suspecte', 'Screening sanctions', 'Registres légaux', 'Journal d\'audit', 'Paramètres'],
    operations: [],
  },
  responsable_conformite: {
    modules: ['Tableau de bord', 'Dossiers KYC', 'Dossiers de Gels', 'Matrice de risque', 'Alertes', 'Décl. Op. Suspecte', 'Screening sanctions', 'Registres légaux', 'Journal d\'audit', 'Utilisateurs (lecture seule)'],
    operations: [],
  },
  clercs: {
    modules: ['Tableau de bord', 'Dossiers KYC', 'Signalement alerte'],
    operations: [],
  },
}

function rolePermissions(role: string) {
  return ROLE_PERMISSIONS[role] ?? { modules: [], operations: [] }
}

const permsTarget = ref<UserOut | null>(null)
function openPerms(u: UserOut) { permsTarget.value = u }

const users = ref<UserOut[]>([])
const departments = ref<Department[]>([])
const loading = ref(true)
const total = ref(0)
const filterDept = ref('')
const search = ref('')

const modal = reactive({ open: false, mode: 'create' as 'create' | 'edit', userId: '' })
const form = reactive({ first_name: '', last_name: '', email: '', role: '', department_id: '', password: '' })
const fe = reactive({ first_name: '', last_name: '', email: '', role: '', department_id: '', password: '' })
const formError = ref('')
const submitting = ref(false)
const confirmTarget = ref<UserOut | null>(null)
const resetPwdTarget = ref<UserOut | null>(null)
const resetPwdResult = ref<string | null>(null)
const copied = ref(false)

const filteredUsers = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return users.value
  return users.value.filter(u =>
    `${u.first_name} ${u.last_name} ${u.email}`.toLowerCase().includes(q)
  )
})

function initials(u: UserOut) {
  return `${u.first_name[0] ?? ''}${u.last_name[0] ?? ''}`.toUpperCase()
}

function deptName(id: string) {
  return departments.value.find(d => d.id === id)?.name ?? '—'
}

async function loadUsers() {
  loading.value = true
  try {
    const res = await usersService.list(filterDept.value || undefined)
    users.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const [, deps] = await Promise.all([loadUsers(), usersService.listDepartments()])
  departments.value = deps
})

function resetForm() {
  Object.assign(form, { first_name: '', last_name: '', email: '', role: '', department_id: '', password: '' })
  Object.assign(fe,   { first_name: '', last_name: '', email: '', role: '', department_id: '', password: '' })
  formError.value = ''
}

function openCreate() { resetForm(); modal.mode = 'create'; modal.open = true }

function openEdit(u: UserOut) {
  resetForm()
  Object.assign(form, { first_name: u.first_name, last_name: u.last_name, email: u.email, role: u.role, department_id: u.department_id, password: '' })
  modal.mode = 'edit'; modal.userId = u.id; modal.open = true
}

function closeModal() { modal.open = false }

function validate(): boolean {
  Object.keys(fe).forEach(k => (fe as any)[k] = '')
  let ok = true
  if (!form.first_name)    { fe.first_name    = 'Requis.'; ok = false }
  if (!form.last_name)     { fe.last_name     = 'Requis.'; ok = false }
  if (modal.mode === 'create' && !form.email) { fe.email = 'Requis.'; ok = false }
  if (modal.mode === 'create' && form.password.length < 8) { fe.password = 'Minimum 8 caractères.'; ok = false }
  if (!form.role)          { fe.role          = 'Requis.'; ok = false }
  if (!form.department_id) { fe.department_id = 'Requis.'; ok = false }
  return ok
}

async function handleSubmit() {
  if (!validate()) return
  formError.value = ''; submitting.value = true
  try {
    if (modal.mode === 'create') {
      const created = await usersService.create({ email: form.email, password: form.password, first_name: form.first_name, last_name: form.last_name, role: form.role, department_id: form.department_id })
      users.value.unshift(created); total.value++
    } else {
      const payload: Record<string, string> = { first_name: form.first_name, last_name: form.last_name, role: form.role, department_id: form.department_id }
      if (form.password) payload.password = form.password
      const updated = await usersService.update(modal.userId, payload)
      const idx = users.value.findIndex(u => u.id === modal.userId)
      if (idx !== -1) users.value[idx] = updated
    }
    closeModal()
  } catch (err: any) {
    formError.value = err?.response?.data?.detail ?? 'Une erreur est survenue.'
  } finally {
    submitting.value = false
  }
}

function confirmDeactivate(u: UserOut) { confirmTarget.value = u }

async function handleDeactivate() {
  if (!confirmTarget.value) return
  submitting.value = true
  try {
    const updated = await usersService.deactivate(confirmTarget.value.id)
    const idx = users.value.findIndex(u => u.id === updated.id)
    if (idx !== -1) users.value[idx] = updated
    confirmTarget.value = null
  } catch (err: any) {
    formError.value = err?.response?.data?.detail ?? 'Erreur.'
  } finally {
    submitting.value = false
  }
}

async function handleReactivate(u: UserOut) {
  try {
    const updated = await usersService.reactivate(u.id)
    const idx = users.value.findIndex(x => x.id === updated.id)
    if (idx !== -1) users.value[idx] = updated
  } catch { /* silent */ }
}

async function handleResetTotp(u: UserOut) {
  if (!confirm(`Réinitialiser la 2FA de ${u.first_name} ${u.last_name} ? L'utilisateur devra reconfigurer son authentificateur à la prochaine connexion.`)) return
  try {
    const updated = await usersService.resetTotp(u.id)
    const idx = users.value.findIndex(x => x.id === updated.id)
    if (idx !== -1) users.value[idx] = updated
  } catch (err: any) {
    alert(err?.response?.data?.detail ?? 'Erreur lors de la réinitialisation 2FA.')
  }
}

function confirmResetPassword(u: UserOut) {
  resetPwdTarget.value = u
  resetPwdResult.value = null
  copied.value = false
}

async function handleResetPassword() {
  if (!resetPwdTarget.value) return
  submitting.value = true
  try {
    const res = await usersService.resetPassword(resetPwdTarget.value.id)
    resetPwdResult.value = res.temp_password
  } catch (err: any) {
    alert(err?.response?.data?.detail ?? 'Erreur lors de la réinitialisation.')
    resetPwdTarget.value = null
  } finally {
    submitting.value = false
  }
}

async function copyTempPwd() {
  if (!resetPwdResult.value) return
  await navigator.clipboard.writeText(resetPwdResult.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function closeResetPwd() {
  resetPwdTarget.value = null
  resetPwdResult.value = null
  copied.value = false
}
</script>

<style scoped>
.users-page { max-width: 1100px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }
.btn-icon { width: 14px; height: 14px; margin-right: 0.375rem; vertical-align: middle; }

.filter-bar { display: flex; gap: 0.75rem; margin-bottom: 1rem; }
.filter-select, .filter-search {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; color: var(--color-text-primary); background: var(--color-bg-card); outline: none; width: auto;
}
.filter-select:focus, .filter-search:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.filter-search { min-width: 200px; }

.table-card { padding: 0; overflow: hidden; }
.table-loading { padding: 3rem; text-align: center; color: var(--color-text-muted); font-size: 0.875rem; }
.users-table { width: 100%; border-collapse: collapse; }
.users-table th { background: var(--color-bg-page); padding: 0.625rem 1rem; text-align: left; font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--color-border); }
.users-table td { padding: 0.875rem 1rem; font-size: 0.8125rem; color: var(--color-text-primary); border-bottom: 1px solid var(--color-border); vertical-align: middle; }
.users-table tr:last-child td { border-bottom: none; }
.users-table tr.row--inactive td { opacity: 0.55; }
.th-actions, .td-actions { text-align: right; }
.td-user { display: flex; align-items: center; gap: 0.75rem; }
.user-avatar-sm { width: 30px; height: 30px; border-radius: 50%; background: rgba(27,43,75,0.1); color: var(--color-sidebar-bg); font-size: 0.6875rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.user-fullname { font-weight: 500; margin: 0; line-height: 1.3; }
.user-email { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0; }
.role-tag { background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 5px; padding: 2px 8px; font-size: 0.75rem; color: var(--color-text-secondary); white-space: nowrap; }
.badge-ok     { color: var(--color-risk-low);  background: var(--color-risk-low-bg);  border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.badge-off    { color: var(--color-text-muted); background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; }
.badge-active { color: var(--color-risk-low);  background: var(--color-risk-low-bg);  border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.badge-inactive { color: var(--color-risk-high); background: var(--color-risk-high-bg); border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.action-btn { background: none; border: none; cursor: pointer; color: var(--color-text-secondary); padding: 4px; border-radius: 5px; transition: background 0.12s, color 0.12s; margin-left: 2px; }
.action-btn svg { width: 15px; height: 15px; display: block; }
.action-btn:hover { background: var(--color-bg-page); color: var(--color-text-primary); }
.action-btn--danger:hover { color: var(--color-risk-high); }
.action-btn--success:hover { color: var(--color-risk-low); }
.action-btn--warn:hover { color: var(--color-risk-medium); }
.empty-row { text-align: center; color: var(--color-text-muted); padding: 2.5rem !important; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 1.5rem; }
.modal { background: var(--color-bg-card); border-radius: 12px; box-shadow: 0 8px 40px rgba(0,0,0,0.16); width: 100%; max-width: 520px; max-height: 90vh; overflow-y: auto; }
.modal--sm { max-width: 400px; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem 0; }
.modal-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.modal-close { background: none; border: none; cursor: pointer; color: var(--color-text-muted); display: flex; }
.modal-close svg { width: 18px; height: 18px; }
.modal-close:hover { color: var(--color-text-primary); }
.modal-form { padding: 1.25rem 1.5rem 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.field-group { display: flex; flex-direction: column; gap: 0.3rem; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.field-hint { font-size: 0.75rem; color: var(--color-text-muted); font-weight: 400; margin-left: 0.25rem; }
.field-input { padding: 0.5625rem 0.75rem; border: 1px solid var(--color-border); border-radius: 7px; font-size: 0.875rem; color: var(--color-text-primary); background: #fff; outline: none; width: 100%; transition: border-color 0.15s, box-shadow 0.15s; }
.field-input:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.field-input--error { border-color: var(--color-risk-high); }
.field-input:disabled { opacity: 0.6; cursor: not-allowed; background: var(--color-bg-page); }
.field-error { font-size: 0.75rem; color: var(--color-risk-high); margin: 0; }
.alert-error { background: var(--color-risk-high-bg); color: var(--color-risk-high); border-radius: 7px; padding: 0.625rem 0.875rem; font-size: 0.8125rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.625rem; padding-top: 0.25rem; }
.btn-ghost-modal { padding: 0.5rem 1rem; background: none; border: 1px solid var(--color-border); border-radius: 7px; font-size: 0.875rem; color: var(--color-text-secondary); cursor: pointer; transition: border-color 0.12s; }
.btn-ghost-modal:hover { border-color: var(--color-text-secondary); }
.btn-danger { padding: 0.5rem 1.25rem; background: var(--color-risk-high); color: #fff; border: none; border-radius: 7px; font-size: 0.875rem; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 0.4rem; transition: opacity 0.12s; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.confirm-body { padding: 0.75rem 1.5rem; font-size: 0.875rem; color: var(--color-text-secondary); line-height: 1.6; margin: 0; }
.spinner { width: 14px; height: 14px; flex-shrink: 0; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.temp-pwd-box { margin: 0 1.5rem 1rem; display: flex; align-items: center; gap: 0.5rem; background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 7px; padding: 0.625rem 0.875rem; }
.temp-pwd-code { flex: 1; font-family: monospace; font-size: 1rem; font-weight: 700; color: var(--color-text-primary); letter-spacing: 0.05em; word-break: break-all; }
.btn-copy { background: none; border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer; color: var(--color-text-secondary); padding: 4px 6px; display: flex; align-items: center; transition: border-color 0.12s, color 0.12s; flex-shrink: 0; }
.btn-copy svg { width: 14px; height: 14px; display: block; }
.btn-copy:hover { border-color: var(--color-sidebar-bg); color: var(--color-sidebar-bg); }
.btn-copy--ok { border-color: var(--color-risk-low); color: var(--color-risk-low); }

.modal--perms { max-width: 460px; }
.perms-body { padding: 1rem 1.5rem 1.5rem; display: flex; flex-direction: column; gap: 1.25rem; }
.perms-role { display: flex; align-items: center; gap: 0.75rem; font-size: 0.875rem; }
.perms-label { color: var(--color-text-secondary); }
.perms-section-title { font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; margin: 0 0 0.5rem; }
.perms-list { margin: 0; padding-left: 1.25rem; display: flex; flex-direction: column; gap: 0.3rem; }
.perms-list li { font-size: 0.8125rem; color: var(--color-text-primary); }
</style>
