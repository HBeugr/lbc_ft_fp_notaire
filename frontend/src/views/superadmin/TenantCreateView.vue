<template>
  <div class="create-page">
    <div class="page-header">
      <div>
        <RouterLink :to="{ name: 'super-admin-tenants' }" class="back-link">← Retour aux cabinets</RouterLink>
        <h1 class="page-title">Nouveau cabinet</h1>
        <p class="page-subtitle">Création de l'espace et du compte administrateur initial.</p>
      </div>
    </div>

    <form class="card" @submit.prevent="handleSubmit" novalidate>
      <!-- Identité du cabinet -->
      <section class="section">
        <h2 class="section-title">Identité du cabinet</h2>
        <div class="form-grid">
          <div class="field-group">
            <label for="tc-nom" class="field-label">Nom du cabinet</label>
            <input id="tc-nom" v-model="form.nom_cabinet" type="text" class="field-input" :class="{ 'field-input--error': fe.nom_cabinet }" />
            <p v-if="fe.nom_cabinet" class="field-error">{{ fe.nom_cabinet }}</p>
          </div>
          <div class="field-group">
            <label for="tc-slug" class="field-label">
              Identifiant (slug)
              <span class="field-hint">(généré automatiquement si vide)</span>
            </label>
            <input id="tc-slug" v-model="form.slug" type="text" class="field-input" placeholder="cabinet-kouassi" />
          </div>
          <div class="field-group">
            <label for="tc-contact-email" class="field-label">Email de contact</label>
            <input id="tc-contact-email" v-model="form.contact_email" type="email" class="field-input" :class="{ 'field-input--error': fe.contact_email }" />
            <p v-if="fe.contact_email" class="field-error">{{ fe.contact_email }}</p>
          </div>
          <div class="field-group">
            <label for="tc-telephone" class="field-label">Téléphone <span class="field-hint">(facultatif)</span></label>
            <input id="tc-telephone" v-model="form.contact_telephone" type="tel" class="field-input" />
          </div>
          <div class="field-group">
            <label for="tc-pays" class="field-label">Pays</label>
            <input id="tc-pays" v-model="form.pays" type="text" class="field-input" maxlength="2" />
          </div>
          <div class="field-group">
            <label for="tc-agrement" class="field-label">N° d'agrément <span class="field-hint">(facultatif)</span></label>
            <input id="tc-agrement" v-model="form.numero_agrement" type="text" class="field-input" />
          </div>
          <div class="field-group field-group--full">
            <label for="tc-adresse" class="field-label">Adresse <span class="field-hint">(facultatif)</span></label>
            <input id="tc-adresse" v-model="form.adresse" type="text" class="field-input" />
          </div>

          <!--
            Logo : sélectionné ici, mais envoyé APRÈS la création du cabinet —
            l'endpoint est indexé par l'identifiant, qui n'existe pas encore.
          -->
          <div class="field-group field-group--full">
            <label class="field-label">Logo du cabinet <span class="field-hint">(facultatif)</span></label>
            <div class="logo-row">
              <div class="logo-preview" :class="{ 'logo-preview--vide': !logoUrl }">
                <img v-if="logoUrl" class="logo-preview-img" :src="logoUrl" alt="Aperçu du logo" />
                <span v-else class="logo-preview-vide">Aucun logo</span>
              </div>
              <div class="logo-actions">
                <input
                  ref="logoInput"
                  type="file"
                  class="logo-file-input"
                  :accept="acceptLogo"
                  @change="handleLogoPick"
                />
                <div class="logo-buttons">
                  <button type="button" class="btn-ghost" @click="logoInput?.click()">
                    {{ logoFile ? 'Changer le fichier' : 'Choisir un fichier' }}
                  </button>
                  <button v-if="logoFile" type="button" class="btn-ghost" @click="clearLogo">
                    Retirer
                  </button>
                </div>
                <p v-if="logoFile" class="logo-filename">{{ logoFile.name }}</p>
                <ul v-if="contraintes" class="logo-rules">
                  <li>Formats acceptés : {{ formatsLisibles }}</li>
                  <li>Poids maximum : {{ tailleMaxLisible }}</li>
                  <li>
                    Dimensions : de {{ contraintes.dimension_min_px }}×{{ contraintes.dimension_min_px }}
                    à {{ contraintes.dimension_max_px }}×{{ contraintes.dimension_max_px }} pixels
                  </li>
                  <li>Rapport largeur/hauteur : {{ contraintes.ratio_max }}:1 maximum</li>
                </ul>
                <p class="logo-note">
                  Le logo est envoyé après la création du cabinet. Il pourra être posé
                  ou remplacé à tout moment depuis la fiche du cabinet.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Administrateur initial -->
      <section class="section">
        <h2 class="section-title">Administrateur du cabinet</h2>
        <p class="section-desc">
          Ce compte recevra le rôle <strong>admin</strong> et un mot de passe temporaire à changer
          à la première connexion.
        </p>
        <div class="form-grid">
          <div class="field-group">
            <label for="tc-admin-prenom" class="field-label">Prénom</label>
            <input id="tc-admin-prenom" v-model="form.admin_first_name" type="text" class="field-input" :class="{ 'field-input--error': fe.admin_first_name }" />
            <p v-if="fe.admin_first_name" class="field-error">{{ fe.admin_first_name }}</p>
          </div>
          <div class="field-group">
            <label for="tc-admin-nom" class="field-label">Nom</label>
            <input id="tc-admin-nom" v-model="form.admin_last_name" type="text" class="field-input" :class="{ 'field-input--error': fe.admin_last_name }" />
            <p v-if="fe.admin_last_name" class="field-error">{{ fe.admin_last_name }}</p>
          </div>
          <div class="field-group field-group--full">
            <label for="tc-admin-email" class="field-label">Email de l'administrateur</label>
            <input id="tc-admin-email" v-model="form.admin_email" type="email" class="field-input" :class="{ 'field-input--error': fe.admin_email }" />
            <p v-if="fe.admin_email" class="field-error">{{ fe.admin_email }}</p>
          </div>
        </div>
      </section>

      <!-- Paramètres -->
      <section class="section">
        <h2 class="section-title">Paramètres de l'espace</h2>
        <div class="form-grid">
          <div class="field-group">
            <label for="tc-max-users" class="field-label">
              Quota de sièges
              <span class="field-hint">(0 = illimité)</span>
            </label>
            <input id="tc-max-users" v-model.number="form.max_users" type="number" min="0" class="field-input" />
          </div>
          <div class="field-group">
            <label class="field-label">Double authentification</label>
            <label class="checkbox-row">
              <input v-model="form.totp_required" type="checkbox" class="checkbox" />
              <span>2FA obligatoire pour les rôles sensibles (Art. 29)</span>
            </label>
          </div>
        </div>
      </section>

      <!-- Collaborateurs pré-créés -->
      <section class="section">
        <h2 class="section-title">Collaborateurs <span class="section-hint">(facultatif)</span></h2>
        <p class="section-desc">
          Comptes créés en même temps que le cabinet, avec un mot de passe temporaire affiché une
          seule fois. L'administrateur pourra en ajouter d'autres depuis son espace.
        </p>

        <div v-for="(u, i) in form.utilisateurs" :key="i" class="collab-row">
          <input v-model="u.first_name" type="text" class="field-input" placeholder="Prénom" />
          <input v-model="u.last_name" type="text" class="field-input" placeholder="Nom" />
          <input v-model="u.email" type="email" class="field-input" placeholder="email@cabinet.ci" />
          <select v-model="u.role" class="field-input">
            <option v-for="r in ROLES_COLLABORATEUR" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
          <button type="button" class="btn-retirer" title="Retirer cette ligne" @click="form.utilisateurs.splice(i, 1)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <button type="button" class="btn-ghost btn-ghost--sm" @click="ajouterCollaborateur">
          + Ajouter un collaborateur
        </button>
      </section>

      <div v-if="formError" class="alert-error">{{ formError }}</div>

      <div class="form-footer">
        <RouterLink :to="{ name: 'super-admin-tenants' }" class="btn-ghost">Annuler</RouterLink>
        <button type="submit" class="btn-primary" :disabled="submitting">
          <span v-if="submitting" class="spinner" />
          Créer le cabinet
        </button>
      </div>
    </form>

    <!-- Mot de passe temporaire — affiché une seule fois -->
    <Teleport to="body">
      <div v-if="created" class="modal-overlay">
        <div class="modal" role="dialog">
          <div class="modal-header">
            <h2 class="modal-title">Cabinet créé</h2>
          </div>
          <div class="created-body">
            <p class="created-line">
              L'espace <strong>{{ created.tenant.nom_cabinet }}</strong>
              (<code>{{ created.tenant.slug }}</code>) a été créé.
            </p>

            <!--
              Échec du seul envoi de logo : le cabinet, lui, EXISTE bien. On le
              rappelle explicitement pour ne pas laisser croire à un échec global.
            -->
            <div v-if="logoError" class="warn-box warn-box--logo">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>
                Le cabinet a bien été créé, mais <strong>le logo n'a pas pu être enregistré</strong> :
                {{ logoError }} Vous pourrez le poser depuis la fiche du cabinet.
              </span>
            </div>

            <div class="warn-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>
                Ce mot de passe temporaire ne sera <strong>plus jamais affiché</strong>.
                Notez-le et transmettez-le à l'administrateur du cabinet avant de fermer cette fenêtre.
              </span>
            </div>

            <div class="cred-row">
              <span class="cred-label">Identifiant</span>
              <code class="cred-value">{{ created.admin_email }}</code>
            </div>

            <div class="temp-pwd-box">
              <code class="temp-pwd-code">{{ created.admin_temp_password }}</code>
              <button class="btn-copy" :class="{ 'btn-copy--ok': copied }" title="Copier" @click="copyPwd">
                <svg v-if="!copied" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              </button>
            </div>

            <div v-if="created.utilisateurs.length" class="collab-recap">
              <p class="collab-recap-title">
                Collaborateurs créés ({{ created.utilisateurs.length }})
              </p>
              <table class="collab-table">
                <tbody>
                  <tr v-for="u in created.utilisateurs" :key="u.email">
                    <td class="collab-td-mail">{{ u.email }}</td>
                    <td class="collab-td-role">{{ libelleRole(u.role) }}</td>
                    <td><code class="collab-td-pwd">{{ u.temp_password }}</code></td>
                  </tr>
                </tbody>
              </table>
              <button class="btn-ghost btn-ghost--sm" @click="copierTout">{{ labelCopieTout }}</button>
            </div>
          </div>
          <div class="modal-actions" style="padding:0 1.5rem 1.5rem;">
            <button class="btn-primary" @click="finish">J'ai noté les mots de passe</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  superAdminService,
  type TenantCreateResponse,
  type LogoContraintes,
} from '@/services/superAdmin'
import { useObjectUrl } from '@/composables/useObjectUrl'

const router = useRouter()

const form = reactive({
  nom_cabinet: '',
  slug: '',
  contact_email: '',
  contact_telephone: '',
  adresse: '',
  numero_agrement: '',
  pays: 'CI',
  admin_email: '',
  admin_first_name: '',
  admin_last_name: '',
  utilisateurs: [] as { first_name: string; last_name: string; email: string; role: string }[],
  totp_required: true,
  max_users: 0,
})

const fe = reactive({
  nom_cabinet: '',
  contact_email: '',
  admin_email: '',
  admin_first_name: '',
  admin_last_name: '',
})

const formError = ref('')
const submitting = ref(false)
const created = ref<TenantCreateResponse | null>(null)
const copied = ref(false)

// ── Logo ─────────────────────────────────────────────────────────────
// Le fichier est retenu localement (aperçu par URL d'objet) et envoyé une fois
// le cabinet créé : l'endpoint exige son identifiant.
const { url: logoUrl, set: setLogoUrl } = useObjectUrl()
const logoFile = ref<File | null>(null)
const logoInput = ref<HTMLInputElement | null>(null)
const contraintes = ref<LogoContraintes | null>(null)
/** Message du refus serveur — la création, elle, a réussi. */
const logoError = ref('')

const acceptLogo = computed(() => contraintes.value?.formats.join(',') ?? 'image/*')

const formatsLisibles = computed(() =>
  (contraintes.value?.formats ?? []).map(f => f.replace('image/', '').toUpperCase()).join(', ')
)

const tailleMaxLisible = computed(() => {
  const octets = contraintes.value?.taille_max_octets
  if (!octets) return '—'
  const mo = octets / (1024 * 1024)
  return mo >= 1 ? `${Number(mo.toFixed(2))} Mo` : `${Math.round(octets / 1024)} Ko`
})

function handleLogoPick(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  input.value = ''
  logoFile.value = file
  setLogoUrl(file)
}

function clearLogo() {
  logoFile.value = null
  setLogoUrl(null)
}

onMounted(async () => {
  try {
    contraintes.value = await superAdminService.logoContraintes()
  } catch {
    // Contraintes indisponibles : on n'affiche pas de règles inventées.
    contraintes.value = null
  }
})

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// `admin` est absent : il est créé par les champs dédiés ci-dessus, et l'API
// refuse un second administrateur à la création.
const ROLES_COLLABORATEUR = [
  { value: 'notaire_principal', label: 'Notaire principal' },
  { value: 'responsable_conformite', label: 'Responsable conformité' },
  { value: 'clercs', label: 'Clerc' },
  { value: 'declarant_centif', label: 'Déclarant CENTIF' },
  { value: 'autre_utilisateur', label: 'Autre utilisateur' },
]

function libelleRole(valeur: string): string {
  return ROLES_COLLABORATEUR.find((r) => r.value === valeur)?.label ?? valeur
}

function ajouterCollaborateur() {
  form.utilisateurs.push({ first_name: '', last_name: '', email: '', role: 'clercs' })
}

const labelCopieTout = ref('Copier tous les identifiants')

async function copierTout() {
  if (!created.value) return
  const lignes = [
    `${created.value.admin_email}\tadmin\t${created.value.admin_temp_password}`,
    ...created.value.utilisateurs.map((u) => `${u.email}\t${u.role}\t${u.temp_password}`),
  ]
  try {
    await navigator.clipboard.writeText(lignes.join('\n'))
    labelCopieTout.value = 'Copié'
  } catch {
    labelCopieTout.value = 'Copie impossible'
  }
  window.setTimeout(() => (labelCopieTout.value = 'Copier tous les identifiants'), 2000)
}

function validate(): boolean {
  Object.keys(fe).forEach(k => { (fe as Record<string, string>)[k] = '' })
  let ok = true
  if (!form.nom_cabinet) { fe.nom_cabinet = 'Requis.'; ok = false }
  if (!form.contact_email) { fe.contact_email = 'Requis.'; ok = false }
  else if (!EMAIL_RE.test(form.contact_email)) { fe.contact_email = 'Adresse invalide.'; ok = false }
  if (!form.admin_email) { fe.admin_email = 'Requis.'; ok = false }
  else if (!EMAIL_RE.test(form.admin_email)) { fe.admin_email = 'Adresse invalide.'; ok = false }
  if (!form.admin_first_name) { fe.admin_first_name = 'Requis.'; ok = false }
  if (!form.admin_last_name) { fe.admin_last_name = 'Requis.'; ok = false }

  // Lignes collaborateur : le formulaire les valide avant l'envoi, sinon le
  // rejet n'arriverait qu'après la création du schéma côté serveur.
  const vus = new Set<string>([form.admin_email.trim().toLowerCase()])
  form.utilisateurs.forEach((u, i) => {
    const mail = u.email.trim().toLowerCase()
    if (!u.first_name.trim() || !u.last_name.trim() || !mail) {
      formError.value = `Collaborateur ${i + 1} : prénom, nom et email sont requis.`
      ok = false
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) {
      formError.value = `Collaborateur ${i + 1} : adresse email invalide.`
      ok = false
    } else if (vus.has(mail)) {
      formError.value = `L'adresse « ${mail} » apparaît deux fois.`
      ok = false
    }
    vus.add(mail)
  })
  return ok
}

async function handleSubmit() {
  if (!validate()) return
  formError.value = ''
  logoError.value = ''
  submitting.value = true
  try {
    // Les champs facultatifs vides sont omis pour laisser jouer les défauts serveur.
    const reponse = await superAdminService.createTenant({
      nom_cabinet: form.nom_cabinet,
      contact_email: form.contact_email,
      admin_email: form.admin_email,
      admin_first_name: form.admin_first_name,
      admin_last_name: form.admin_last_name,
      utilisateurs: form.utilisateurs.map((u) => ({
        first_name: u.first_name.trim(),
        last_name: u.last_name.trim(),
        email: u.email.trim().toLowerCase(),
        role: u.role,
      })),
      pays: form.pays || 'CI',
      totp_required: form.totp_required,
      max_users: form.max_users || 0,
      ...(form.slug ? { slug: form.slug } : {}),
      ...(form.numero_agrement ? { numero_agrement: form.numero_agrement } : {}),
      ...(form.contact_telephone ? { contact_telephone: form.contact_telephone } : {}),
      ...(form.adresse ? { adresse: form.adresse } : {}),
    })

    // Le logo ne peut être envoyé qu'ensuite : l'endpoint est indexé par l'id du
    // cabinet. Un refus ici n'annule PAS la création — on l'annonce comme tel.
    if (logoFile.value) {
      try {
        await superAdminService.uploadLogo(reponse.tenant.id, logoFile.value)
      } catch (err: any) {
        const detail = err?.response?.data?.detail
        logoError.value = typeof detail === 'string' ? detail : 'refus du serveur.'
      }
    }

    created.value = reponse
  } catch (err: any) {
    formError.value = messageErreur(err?.response?.data?.detail)
  } finally {
    submitting.value = false
  }
}

/**
 * Restitue l'erreur renvoyée par l'API.
 *
 * Sur un 422, FastAPI renvoie `detail` sous forme de TABLEAU d'erreurs par
 * champ. L'ancien code n'affichait alors qu'un message générique, laissant
 * l'exploitant deviner quel champ posait problème — un TLD d'email refusé, par
 * exemple, était indiscernable d'une panne serveur.
 */
function messageErreur(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const champs = detail
      .map((e: any) => {
        const champ = Array.isArray(e?.loc) ? e.loc[e.loc.length - 1] : null
        return champ ? `${champ} : ${e.msg}` : e?.msg
      })
      .filter(Boolean)
    if (champs.length) return champs.join(' · ')
  }
  if (detail && typeof detail === 'object' && 'message' in (detail as any)) {
    return String((detail as any).message)
  }
  return 'Impossible de créer le cabinet.'
}

async function copyPwd() {
  if (!created.value) return
  await navigator.clipboard.writeText(created.value.admin_temp_password)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function finish() {
  const id = created.value?.tenant.id
  created.value = null
  router.push(id
    ? { name: 'super-admin-tenant-detail', params: { id } }
    : { name: 'super-admin-tenants' })
}
</script>

<style scoped>
.create-page { max-width: 860px; }
.page-header { margin-bottom: 1.5rem; }
.back-link { font-size: 0.8125rem; color: var(--color-text-secondary); text-decoration: none; }
.back-link:hover { color: var(--color-text-primary); }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0.5rem 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }

.card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

.section { display: flex; flex-direction: column; gap: 0.875rem; }
.section-hint { font-weight: 400; font-size: 0.8125rem; color: var(--color-text-muted); }

/* Lignes collaborateur : grille alignée, qui retombe en colonne sur mobile. */
.collab-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1.6fr 1.2fr auto;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}
@media (max-width: 760px) { .collab-row { grid-template-columns: 1fr; } }
.btn-retirer {
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; flex-shrink: 0;
  border: 1px solid var(--color-border); border-radius: 7px;
  background: #fff; color: var(--color-text-muted); cursor: pointer;
}
.btn-retirer:hover { border-color: var(--color-risk-high); color: var(--color-risk-high); }
.btn-retirer svg { width: 14px; height: 14px; }
.btn-ghost--sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }

/* Récapitulatif des comptes pré-créés, dans la modale de succès. */
.collab-recap { margin-top: 1.25rem; border-top: 1px solid var(--color-border); padding-top: 1rem; }
.collab-recap-title {
  font-size: 0.8125rem; font-weight: 600; color: var(--color-text-primary); margin: 0 0 0.625rem;
}
.collab-table { width: 100%; border-collapse: collapse; margin-bottom: 0.75rem; }
.collab-table td {
  padding: 0.375rem 0.5rem 0.375rem 0;
  border-bottom: 1px solid var(--color-border);
  font-size: 0.75rem; vertical-align: middle;
}
.collab-table tr:last-child td { border-bottom: none; }
.collab-td-mail { color: var(--color-text-primary); }
.collab-td-role { color: var(--color-text-muted); white-space: nowrap; }
.collab-td-pwd {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 700; color: var(--color-text-primary);
  background: var(--color-bg-page); border-radius: 4px; padding: 0.125rem 0.375rem;
}

.section-title {
  font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary);
  text-transform: uppercase; letter-spacing: 0.04em; margin: 0;
  padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border);
}
.section-desc { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem; }
.field-group { display: flex; flex-direction: column; gap: 0.3rem; }
.field-group--full { grid-column: 1 / -1; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.field-hint { font-size: 0.75rem; color: var(--color-text-muted); font-weight: 400; margin-left: 0.25rem; }
.field-input {
  padding: 0.5625rem 0.75rem; border: 1px solid var(--color-border); border-radius: 7px;
  font-size: 0.875rem; color: var(--color-text-primary); background: #fff; outline: none;
  width: 100%; transition: border-color 0.15s, box-shadow 0.15s;
}
.field-input:focus { border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12); }
.field-input--error { border-color: var(--color-risk-high); }
.field-error { font-size: 0.75rem; color: var(--color-risk-high); margin: 0; }

.checkbox-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: var(--color-text-secondary); }
.checkbox { width: auto; accent-color: var(--color-accent-gold); }

.alert-error {
  background: var(--color-risk-high-bg); color: var(--color-risk-high);
  border-radius: 7px; padding: 0.625rem 0.875rem; font-size: 0.8125rem;
}

.form-footer { display: flex; justify-content: flex-end; gap: 0.625rem; }
.btn-ghost {
  display: inline-flex; align-items: center;
  padding: 0.5rem 1rem; background: none;
  border: 1px solid var(--color-border); border-radius: 7px;
  font-size: 0.875rem; color: var(--color-text-secondary);
  cursor: pointer; text-decoration: none; transition: border-color 0.12s;
}
.btn-ghost:hover { border-color: var(--color-text-secondary); }
.btn-primary {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 1.25rem; background: var(--color-btn-primary);
  color: #fff; border: none; border-radius: 7px;
  font-size: 0.875rem; font-weight: 600; cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: var(--color-btn-primary-hover); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 1.5rem;
}
.modal {
  background: var(--color-bg-card); border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.16);
  width: 100%; max-width: 520px; max-height: 90vh; overflow-y: auto;
}
.modal-header { padding: 1.25rem 1.5rem 0; }
.modal-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.625rem; }

.created-body { padding: 0.75rem 1.5rem 1rem; display: flex; flex-direction: column; gap: 0.875rem; }
.created-line { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; line-height: 1.6; }
.created-line code { font-family: monospace; font-size: 0.8125rem; }

.warn-box {
  display: flex; align-items: flex-start; gap: 0.5rem;
  background: var(--color-risk-medium-bg); color: var(--color-risk-medium);
  border: 1px solid rgba(217, 119, 6, 0.2); border-radius: 8px;
  padding: 0.75rem 0.875rem; font-size: 0.8125rem; line-height: 1.5;
}
.warn-box svg { width: 16px; height: 16px; flex-shrink: 0; margin-top: 1px; }
.warn-box--logo {
  background: var(--color-risk-high-bg); color: var(--color-risk-high);
  border-color: rgba(220, 38, 38, 0.2);
}

/* ── Logo ── */
.logo-row { display: flex; align-items: flex-start; gap: 1rem; flex-wrap: wrap; }
.logo-preview {
  width: 104px; height: 104px; flex-shrink: 0;
  border: 1px solid var(--color-border); border-radius: 10px;
  background: var(--color-bg-page); display: flex;
  align-items: center; justify-content: center; padding: 0.5rem; overflow: hidden;
}
.logo-preview--vide { border-style: dashed; }
.logo-preview-img  { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
.logo-preview-vide { font-size: 0.75rem; color: var(--color-text-muted); }
.logo-actions { flex: 1; min-width: 240px; display: flex; flex-direction: column; gap: 0.5rem; }
.logo-file-input { display: none; }
.logo-buttons { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.logo-filename { font-size: 0.75rem; color: var(--color-text-primary); margin: 0; word-break: break-all; }
.logo-rules {
  margin: 0; padding: 0.625rem 0.875rem 0.625rem 1.75rem;
  background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.75rem; color: var(--color-text-secondary); line-height: 1.7;
}
.logo-note { font-size: 0.75rem; color: var(--color-text-muted); margin: 0; line-height: 1.5; }

.cred-row { display: flex; align-items: center; gap: 0.75rem; font-size: 0.8125rem; }
.cred-label { color: var(--color-text-secondary); min-width: 90px; font-weight: 500; }
.cred-value { font-family: monospace; color: var(--color-text-primary); }

.temp-pwd-box {
  display: flex; align-items: center; gap: 0.5rem;
  background: var(--color-bg-page); border: 1px solid var(--color-border);
  border-radius: 7px; padding: 0.625rem 0.875rem;
}
.temp-pwd-code {
  flex: 1; font-family: monospace; font-size: 1rem; font-weight: 700;
  color: var(--color-text-primary); letter-spacing: 0.05em; word-break: break-all;
}
.btn-copy {
  background: none; border: 1px solid var(--color-border); border-radius: 6px;
  cursor: pointer; color: var(--color-text-secondary); padding: 4px 6px;
  display: flex; align-items: center; transition: border-color 0.12s, color 0.12s; flex-shrink: 0;
}
.btn-copy svg { width: 14px; height: 14px; display: block; }
.btn-copy:hover { border-color: var(--color-sidebar-bg); color: var(--color-sidebar-bg); }
.btn-copy--ok { border-color: var(--color-risk-low); color: var(--color-risk-low); }

.spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .form-grid { grid-template-columns: 1fr; }
}
</style>
