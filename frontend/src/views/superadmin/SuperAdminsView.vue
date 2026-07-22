<template>
  <div class="admins-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Comptes d'exploitation</h1>
        <p class="page-subtitle">
          {{ admins.length }} compte{{ admins.length !== 1 ? 's' : '' }} · ces comptes administrent
          les cabinets, jamais leurs dossiers
        </p>
      </div>
      <button class="btn-primary" @click="ouvrirFormulaire = !ouvrirFormulaire">
        {{ ouvrirFormulaire ? 'Annuler' : '+ Nouveau super-admin' }}
      </button>
    </div>

    <form v-if="ouvrirFormulaire" class="card form-card" @submit.prevent="creer">
      <div class="form-grid">
        <div class="field">
          <label for="a-prenom" class="label">Prénom</label>
          <input id="a-prenom" v-model="form.first_name" type="text" class="input" :disabled="creating" />
        </div>
        <div class="field">
          <label for="a-nom" class="label">Nom</label>
          <input id="a-nom" v-model="form.last_name" type="text" class="input" :disabled="creating" />
        </div>
        <div class="field">
          <label for="a-email" class="label">Adresse email</label>
          <input id="a-email" v-model="form.email" type="email" class="input" :disabled="creating" />
        </div>
        <div class="field">
          <label for="a-mdp" class="label">Mot de passe initial</label>
          <input id="a-mdp" v-model="form.password" type="password" class="input" :disabled="creating" />
          <p class="hint">
            12 caractères minimum, 4 classes. Son porteur devra le remplacer à la première connexion.
          </p>
        </div>
      </div>

      <p v-if="formError" class="alert-error alert-error--inline">{{ formError }}</p>

      <div class="form-actions">
        <button type="submit" class="btn-primary" :disabled="creating">
          <span v-if="creating" class="spinner" />
          {{ creating ? 'Création…' : 'Créer le compte' }}
        </button>
      </div>
    </form>

    <div v-if="loadError" class="alert-error">{{ loadError }}</div>

    <div class="card table-card">
      <div v-if="loading" class="table-loading">Chargement…</div>
      <table v-else class="admins-table">
        <thead>
          <tr>
            <th>Nom</th>
            <th>Email</th>
            <th>Statut</th>
            <th>Créé le</th>
            <th class="th-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in admins" :key="a.id" :class="{ 'row--inactive': !a.is_active }">
            <td class="td-nom">
              {{ a.first_name }} {{ a.last_name }}
              <span v-if="a.id === moiId" class="tag-moi">vous</span>
            </td>
            <td class="td-muted">{{ a.email }}</td>
            <td>
              <span class="badge" :class="a.is_active ? 'badge--on' : 'badge--off'">
                {{ a.is_active ? 'Actif' : 'Désactivé' }}
              </span>
              <span v-if="a.must_change_password" class="badge badge--warn">Mot de passe à changer</span>
            </td>
            <td class="td-muted">{{ formatDate(a.created_at) }}</td>
            <td class="td-actions">
              <button
                v-if="a.is_active"
                class="btn-mini"
                :disabled="a.id === moiId || busyId === a.id"
                :title="a.id === moiId ? 'Impossible de désactiver son propre compte' : 'Désactiver'"
                @click="demande = a"
              >Désactiver</button>
              <button
                v-else
                class="btn-mini btn-mini--ok"
                :disabled="busyId === a.id"
                @click="basculer(a, true)"
              >Réactiver</button>
            </td>
          </tr>
          <tr v-if="!admins.length">
            <td colspan="5" class="empty-row">Aucun compte d'exploitation.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Désactivation : l'intéressé perd l'accès immédiatement, même session ouverte. -->
    <Teleport to="body">
      <div v-if="demande" class="modal-overlay" @click.self="demande = null">
        <div class="modal" role="dialog" aria-modal="true">
          <h2 class="modal-title">Désactiver ce compte ?</h2>
          <p class="modal-text">
            <strong>{{ demande.email }}</strong> perdra l'accès à la console immédiatement, y compris
            si sa session est ouverte. Le compte est conservé et peut être réactivé.
          </p>
          <div class="modal-actions">
            <button class="btn-ghost" @click="demande = null">Annuler</button>
            <button class="btn-danger" :disabled="busyId !== null" @click="basculer(demande, false)">
              <span v-if="busyId" class="spinner" />
              Désactiver
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useSuperAdminStore } from '@/stores/superAdmin'
import { superAdminService, type SuperAdminListItem } from '@/services/superAdmin'
import { checkPasswordStrength } from '@/utils/passwordPolicy'

const store = useSuperAdminStore()
const moiId = store.superAdmin?.id ?? ''

const admins = ref<SuperAdminListItem[]>([])
const loading = ref(true)
const loadError = ref('')

const ouvrirFormulaire = ref(false)
const creating = ref(false)
const formError = ref('')
const form = reactive({ first_name: '', last_name: '', email: '', password: '' })

const demande = ref<SuperAdminListItem | null>(null)
const busyId = ref<string | null>(null)

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  })
}

async function charger() {
  loading.value = true
  loadError.value = ''
  try {
    admins.value = await superAdminService.listAdmins()
  } catch (err: any) {
    loadError.value = messageDe(err, 'Impossible de charger les comptes.')
  } finally {
    loading.value = false
  }
}

async function creer() {
  formError.value = ''
  if (!form.first_name.trim() || !form.last_name.trim()) {
    formError.value = 'Prénom et nom sont requis.'
    return
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    formError.value = "L'adresse email est invalide."
    return
  }
  const motifMdp = checkPasswordStrength(form.password)
  if (motifMdp) {
    formError.value = motifMdp
    return
  }

  creating.value = true
  try {
    await superAdminService.createAdmin({
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      password: form.password,
    })
    Object.assign(form, { first_name: '', last_name: '', email: '', password: '' })
    ouvrirFormulaire.value = false
    await charger()
  } catch (err: any) {
    formError.value = messageDe(err, 'La création a échoué.')
  } finally {
    creating.value = false
  }
}

async function basculer(cible: SuperAdminListItem, actif: boolean) {
  busyId.value = cible.id
  loadError.value = ''
  try {
    const maj = await superAdminService.setAdminActive(cible.id, actif)
    const i = admins.value.findIndex((a) => a.id === maj.id)
    if (i !== -1) admins.value[i] = maj
    demande.value = null
  } catch (err: any) {
    loadError.value = messageDe(err, "L'action a échoué.")
    demande.value = null
  } finally {
    busyId.value = null
  }
}

/** Aplatit les trois formes d'erreur FastAPI en une phrase lisible. */
function messageDe(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item: any) => {
        const champ = Array.isArray(item?.loc) ? item.loc.slice(1).join('.') : ''
        const msg = (item?.msg ?? '').replace(/^Value error,\s*/, '')
        return champ ? `${champ} : ${msg}` : msg
      })
      .filter(Boolean)
      .join(' · ')
  }
  if (!err?.response) return 'Serveur injoignable. Vérifiez votre connexion.'
  return fallback
}

onMounted(charger)
</script>

<style scoped>
.admins-page { max-width: 1100px; }

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 1rem; margin-bottom: 1.5rem;
}
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0.25rem 0 0; }

.card {
  background: var(--color-bg-card);
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}
.form-card { margin-bottom: 1.25rem; }
.table-card { padding: 0; overflow: hidden; }
.table-loading { padding: 3rem; text-align: center; color: var(--color-text-muted); }

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}
.field { display: flex; flex-direction: column; gap: 0.3125rem; }
.label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.input {
  padding: 0.5rem 0.6875rem; border: 1px solid var(--color-border); border-radius: 7px;
  font-size: 0.875rem; color: var(--color-text-primary); background: #fff; outline: none; width: 100%;
}
.input:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201, 162, 39, 0.12); }
.hint { font-size: 0.6875rem; color: var(--color-text-muted); margin: 0; line-height: 1.45; }
.form-actions { display: flex; justify-content: flex-end; margin-top: 1.25rem; }

.admins-table { width: 100%; border-collapse: collapse; }
.admins-table th {
  text-align: left; padding: 0.75rem 1rem;
  font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--color-text-muted); border-bottom: 1px solid var(--color-border);
}
.admins-table td {
  padding: 0.75rem 1rem; border-bottom: 1px solid var(--color-border);
  font-size: 0.8125rem; color: var(--color-text-primary);
}
.admins-table tbody tr:last-child td { border-bottom: none; }
.row--inactive { opacity: 0.55; }
.td-nom { font-weight: 500; }
.td-muted { color: var(--color-text-secondary); }
.th-actions, .td-actions { text-align: right; white-space: nowrap; }
.empty-row { text-align: center; color: var(--color-text-muted); padding: 2.5rem; }

.tag-moi {
  margin-left: 0.375rem; padding: 0.0625rem 0.375rem; border-radius: 999px;
  background: var(--color-bg-page); color: var(--color-text-muted);
  font-size: 0.625rem; font-weight: 600; text-transform: uppercase;
}
.badge {
  display: inline-block; padding: 0.1875rem 0.5rem; border-radius: 999px;
  font-size: 0.6875rem; font-weight: 600; white-space: nowrap;
}
.badge--on { background: var(--color-risk-low-bg); color: var(--color-risk-low); }
.badge--off { background: var(--color-risk-high-bg); color: var(--color-risk-high); }
.badge--warn { background: var(--color-risk-medium-bg); color: var(--color-risk-medium); margin-left: 0.375rem; }

.btn-primary, .btn-ghost, .btn-danger {
  display: inline-flex; align-items: center; gap: 0.4375rem;
  border-radius: 7px; padding: 0.5rem 1rem;
  font-size: 0.875rem; font-weight: 600; cursor: pointer; border: 1px solid transparent;
}
.btn-primary { background: var(--color-btn-primary); color: #fff; flex-shrink: 0; }
.btn-primary:hover:not(:disabled) { background: var(--color-btn-primary-hover); }
.btn-ghost { background: #fff; border-color: var(--color-border); color: var(--color-text-secondary); }
.btn-ghost:hover { border-color: var(--color-text-secondary); }
.btn-danger { background: var(--color-risk-high); color: #fff; }
.btn-danger:hover:not(:disabled) { filter: brightness(0.93); }
.btn-primary:disabled, .btn-ghost:disabled, .btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-mini {
  border: 1px solid var(--color-border); background: #fff; color: var(--color-text-primary);
  border-radius: 6px; padding: 0.25rem 0.625rem; font-size: 0.75rem; cursor: pointer;
}
.btn-mini:hover:not(:disabled) { background: var(--color-bg-page); }
.btn-mini:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-mini--ok { color: var(--color-risk-low); border-color: var(--color-risk-low); }

.alert-error {
  background: var(--color-risk-high-bg); color: var(--color-risk-high);
  border: 1px solid rgba(220, 38, 38, 0.2); border-radius: 8px;
  padding: 0.75rem 0.875rem; font-size: 0.8125rem; margin-bottom: 1.25rem;
}
.alert-error--inline { margin: 1rem 0 0; }

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 1.5rem;
}
.modal {
  background: var(--color-bg-card); border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.16);
  width: 100%; max-width: 420px; padding: 1.25rem 1.5rem 1.5rem;
}
.modal-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.6rem; }
.modal-text { font-size: 0.875rem; color: var(--color-text-secondary); line-height: 1.6; margin: 0 0 1.25rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.625rem; }

.spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(255, 255, 255, 0.35); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
