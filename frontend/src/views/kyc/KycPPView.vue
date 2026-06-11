<template>
  <div class="pp-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <button class="breadcrumb-link" @click="router.push({ name: 'kyc-list' })">Dossiers KYC</button>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="breadcrumb-sep"><polyline points="9 18 15 12 9 6"/></svg>
          <button class="breadcrumb-link" @click="router.push({ name: 'kyc-detail', params: { id: dossierId } })">{{ dossierId.slice(0, 8) }}…</button>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="breadcrumb-sep"><polyline points="9 18 15 12 9 6"/></svg>
          <span>KYC Personne Physique</span>
        </div>
        <h1 class="page-title">Formulaire KYC — Personne Physique</h1>
        <p class="page-subtitle">Identification et évaluation du risque client notarial</p>
      </div>
    </div>

    <div v-if="loading" class="card loading-card">Chargement…</div>
    <template v-else>
      <!-- Step bar -->
      <div class="step-bar">
        <div
          v-for="(s, i) in SECTIONS"
          :key="i"
          class="step-item"
          :class="{ 'step-item--done': i < currentStep, 'step-item--active': i === currentStep }"
        >
          <div class="step-dot">
            <svg v-if="i < currentStep" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <span class="step-label">{{ s }}</span>
          <div v-if="i < SECTIONS.length - 1" class="step-connector" />
        </div>
      </div>

      <!-- Save status -->
      <div class="save-status" :class="`save-status--${saveStatus}`">
        <template v-if="saveStatus === 'saving'">
          <svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
          Sauvegarde…
        </template>
        <template v-else-if="saveStatus === 'saved'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          Sauvegardé
        </template>
        <template v-else-if="saveStatus === 'error'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          Erreur de sauvegarde
        </template>
      </div>

      <!-- Pré-check sanctions live (pendant la saisie) + blocage T3 au save -->
      <div v-if="sanctionsBanner" role="alert"
        :style="sanctionsBanner.style + ';border-radius:8px;padding:0.75rem 1rem;font-size:0.875rem;font-weight:600;margin-bottom:1rem'">
        {{ sanctionsBanner.icon }} {{ sanctionsBanner.text }}
      </div>
      <div v-else-if="saveErrorMsg" role="alert"
        style="background:#fee2e2;color:#b91c1c;border:1px solid #fca5a5;border-radius:8px;padding:0.75rem 1rem;font-size:0.875rem;font-weight:600;margin-bottom:1rem">
        ⛔ {{ saveErrorMsg }}
      </div>

      <!-- ── Section 1 — Identité ── -->
      <div v-if="currentStep === 0" class="card section-card">
        <h3 class="section-title">S1 — Identité</h3>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Nom <span class="req">*</span></label>
            <input v-model="form.nom" type="text" class="form-input" placeholder="Nom de famille" @blur="triggerSanctionsCheck" />
            <p v-if="errors.nom" class="form-error">{{ errors.nom }}</p>
          </div>
          <div class="form-group">
            <label class="form-label">Prénoms <span class="req">*</span></label>
            <input v-model="form.prenoms" type="text" class="form-input" placeholder="Tous les prénoms" @blur="triggerSanctionsCheck" />
            <p v-if="errors.prenoms" class="form-error">{{ errors.prenoms }}</p>
          </div>
          <div class="form-group">
            <label class="form-label">Nom de jeune fille</label>
            <input v-model="form.nom_jeune_fille" type="text" class="form-input" placeholder="Si applicable" />
          </div>
          <div class="form-group">
            <label class="form-label">Nom & Prénoms du père</label>
            <input v-model="form.nom_prenoms_pere" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Nom & Prénoms de la mère</label>
            <input v-model="form.nom_prenoms_mere" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Date de naissance</label>
            <input v-model="form.date_naissance" type="date" class="form-input" @blur="triggerSanctionsCheck" @change="triggerSanctionsCheck" />
          </div>
          <div class="form-group">
            <label class="form-label">Lieu de naissance</label>
            <input v-model="form.lieu_naissance" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Type de pièce d'identité</label>
            <select v-model="form.type_piece" class="form-select">
              <option value="">—</option>
              <option value="CNI">CNI</option>
              <option value="Passeport">Passeport</option>
              <option value="Titre_sejour">Titre de séjour</option>
              <option value="Carte_consulaire">Carte consulaire</option>
              <option value="Autre">Autre</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Numéro de pièce</label>
            <input v-model="form.numero_piece" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Nationalité</label>
            <CountrySelect v-model="form.nationalite" label="" />
          </div>
          <div class="form-group">
            <label class="form-label">Autres nationalités</label>
            <input v-model="form.autres_nationalites" type="text" class="form-input" placeholder="Si applicable" />
          </div>
          <div class="form-group">
            <label class="form-label">Statut matrimonial</label>
            <select v-model="form.statut_matrimonial" class="form-select">
              <option value="">—</option>
              <option>Célibataire</option>
              <option>Marié(e)</option>
              <option>Divorcé(e)</option>
              <option>Veuf / Veuve</option>
            </select>
          </div>
        </div>
      </div>

      <!-- ── Section 2 — Coordonnées ── -->
      <div v-else-if="currentStep === 1" class="card section-card">
        <h3 class="section-title">S2 — Coordonnées & Résidence</h3>
        <div class="form-grid">
          <div class="form-group form-group--full">
            <label class="form-label">Adresse géographique</label>
            <input v-model="form.adresse_geo" type="text" class="form-input" placeholder="Quartier, rue, immeuble…" />
          </div>
          <div class="form-group">
            <label class="form-label">Adresse postale / BP</label>
            <input v-model="form.adresse_postale" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Téléphone</label>
            <input v-model="form.telephone" type="tel" class="form-input" placeholder="+225…" />
          </div>
          <div class="form-group">
            <label class="form-label">WhatsApp</label>
            <input v-model="form.whatsapp" type="tel" class="form-input" placeholder="+225…" />
          </div>
          <div class="form-group">
            <label class="form-label">Email</label>
            <input v-model="form.email" type="email" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">N° Compte Contribuable / Identité Fiscale</label>
            <input v-model="form.numero_contribuable" type="text" class="form-input" />
          </div>
          <div class="form-group form-group--full">
            <label class="checkbox-row">
              <input v-model="form.non_resident" type="checkbox" class="checkbox" />
              <span class="form-label" style="margin:0">Client Non Résident (NRI)</span>
            </label>
          </div>
          <div v-if="form.non_resident" class="form-group">
            <label class="form-label">Pays de résidence</label>
            <CountrySelect v-model="form.pays_residence" label="" />
          </div>
        </div>
      </div>

      <!-- ── Section 3 — Activité professionnelle ── -->
      <div v-else-if="currentStep === 2" class="card section-card">
        <h3 class="section-title">S3 — Activité Professionnelle</h3>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Profession actuelle</label>
            <input v-model="form.profession" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Employeur / Entreprise</label>
            <input v-model="form.employeur" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Secteur d'activité</label>
            <input v-model="form.secteur_activite" type="text" class="form-input" />
          </div>
          <div class="form-group form-group--full">
            <label class="form-label">Professions exercées durant les 5 dernières années</label>
            <textarea v-model="form.profession_5_ans" class="form-textarea" rows="3" placeholder="Listez les emplois successifs, entreprises et durées…" />
          </div>
        </div>
      </div>

      <!-- ── Section 4 — Mandataire ── -->
      <div v-else-if="currentStep === 3" class="card section-card">
        <h3 class="section-title">S4 — Mandataire</h3>
        <p class="section-hint">Données du mandataire qui traite l'opération (si applicable)</p>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Prénom & Nom du mandataire</label>
            <input v-model="form.mandataire.prenom_nom" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Type de pièce</label>
            <select v-model="form.mandataire.type_piece" class="form-select">
              <option value="">—</option>
              <option value="CNI">CNI</option>
              <option value="Passeport">Passeport</option>
              <option value="Titre_sejour">Titre de séjour</option>
              <option value="Carte_consulaire">Carte consulaire</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">N° de pièce</label>
            <input v-model="form.mandataire.numero_piece" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Date de naissance</label>
            <input v-model="form.mandataire.date_naissance" type="date" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Nationalité</label>
            <CountrySelect v-model="form.mandataire.nationalite" label="" />
          </div>
          <div class="form-group">
            <label class="form-label">Pays de résidence</label>
            <CountrySelect v-model="form.mandataire.pays_residence" label="" />
          </div>
          <div class="form-group form-group--full">
            <label class="form-label">Fonction</label>
            <div class="radio-group radio-group--inline">
              <label v-for="fn in FONCTIONS_MANDATAIRE" :key="fn" class="radio-label">
                <input v-model="form.mandataire.fonction" type="radio" :value="fn" class="radio-input" />
                {{ fn }}
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Section 5 — PPE & Opération ── -->
      <div v-else-if="currentStep === 4" class="card section-card">
        <h3 class="section-title">S5 — PPE & Description de l'Opération</h3>

        <!-- PPE -->
        <div class="ppe-block" :class="form.est_ppe ? 'ppe-block--active' : ''">
          <p class="form-label">Personne Politiquement Exposée (PPE) <span class="trigger-tag">⚡ Trigger T1</span></p>
          <div class="radio-group radio-group--inline">
            <label class="radio-label radio--non">
              <input v-model="form.est_ppe" type="radio" :value="false" class="radio-input" />
              Non
            </label>
            <label class="radio-label radio--oui">
              <input v-model="form.est_ppe" type="radio" :value="true" class="radio-input" />
              Oui — risque ÉLEVÉ forcé
            </label>
          </div>
          <div v-if="form.est_ppe" class="form-group" style="margin-top:0.75rem">
            <label class="form-label">Détail PPE (fonction, pays, durée…)</label>
            <textarea v-model="form.ppe_detail" class="form-textarea" rows="2" placeholder="Précisez la fonction politique, le pays et la période…" />
          </div>
        </div>

        <!-- Opérations -->
        <div style="margin-top:1.25rem">
          <p class="form-label" style="margin-bottom:0.5rem">Opérations applicables (cochez tout ce qui s'applique)</p>
          <div class="ops-check-grid">
            <label v-for="op in OPERATION_OPTIONS" :key="op.key"
              class="op-check-card"
              :class="{ 'op-check-card--selected': (form.operations_cochees as any)[op.key] }"
            >
              <input v-model="(form.operations_cochees as any)[op.key]" type="checkbox" class="checkbox" />
              <span class="op-check-label">{{ op.label }}</span>
            </label>
          </div>
          <div class="form-group" style="margin-top:0.75rem">
            <label class="form-label">Préciser si autre</label>
            <input v-model="form.operations_cochees.autre_detail" type="text" class="form-input" />
          </div>
        </div>

        <!-- Description opération -->
        <div class="form-group" style="margin-top:0.875rem">
          <label class="form-label">Description détaillée de l'opération</label>
          <textarea v-model="form.description_operation" class="form-textarea" rows="4" placeholder="Objet précis de l'acte, parties, montants, conditions, origine immobilière…" />
        </div>
      </div>

      <!-- ── Section 6 — Origine des fonds ── -->
      <div v-else-if="currentStep === 5" class="card section-card">
        <h3 class="section-title">S6 — Origine des Fonds & Déclaration</h3>
        <p class="section-hint">Le client déclare que les fonds proviennent de :</p>

        <div class="ops-check-grid">
          <label v-for="of in FONDS_OPTIONS" :key="of.key"
            class="op-check-card"
            :class="{ 'op-check-card--selected': (form.origine_fonds as any)[of.key] }"
          >
            <input v-model="(form.origine_fonds as any)[of.key]" type="checkbox" class="checkbox" />
            <span class="op-check-label">{{ of.label }}</span>
          </label>
        </div>

        <div class="form-grid" style="margin-top:0.875rem">
          <div class="form-group">
            <label class="form-label">Autres sources (préciser)</label>
            <input v-model="form.origine_fonds.autres" type="text" class="form-input" />
          </div>

          <!-- Propriété -->
          <div class="form-group form-group--full">
            <label class="form-label">Propriété des fonds</label>
            <div class="radio-group radio-group--inline">
              <label class="radio-label">
                <input v-model="form.origine_fonds.propriete_intervenants" type="radio" :value="true" @change="form.origine_fonds.propriete_tiers = false" class="radio-input" />
                Propriété des intervenants à l'acte
              </label>
              <label class="radio-label">
                <input v-model="form.origine_fonds.propriete_tiers" type="radio" :value="true" @change="form.origine_fonds.propriete_intervenants = false" class="radio-input" />
                Propriété d'un tiers
              </label>
            </div>
          </div>
          <div v-if="form.origine_fonds.propriete_tiers" class="form-group form-group--full">
            <label class="form-label">Identité du tiers bénéficiaire (agit pour le compte de)</label>
            <input v-model="form.origine_fonds.interet_tiers" type="text" class="form-input" placeholder="Nom, qualité du tiers…" />
          </div>

          <!-- Territoire -->
          <div class="form-group form-group--full">
            <label class="form-label">Territoire d'origine des fonds</label>
            <div class="radio-group radio-group--inline">
              <label class="radio-label">
                <input v-model="form.origine_fonds.territoire_ivoirien" type="radio" :value="true" class="radio-input" />
                Territoire ivoirien
              </label>
              <label class="radio-label">
                <input v-model="form.origine_fonds.territoire_ivoirien" type="radio" :value="false" class="radio-input" />
                Hors Côte d'Ivoire
              </label>
            </div>
          </div>
          <div v-if="!form.origine_fonds.territoire_ivoirien" class="form-group">
            <label class="form-label">Pays de provenance</label>
            <CountrySelect v-model="form.origine_fonds.pays_provenance" label="" />
          </div>

          <!-- Ancienneté pro -->
          <div class="form-group form-group--full">
            <label class="form-label">Ancienneté professionnelle</label>
            <div class="radio-group radio-group--inline">
              <label class="radio-label">
                <input v-model="form.anciennete_pro" type="radio" value="moins_1_an" class="radio-input" />
                Moins de 1 an
              </label>
              <label class="radio-label">
                <input v-model="form.anciennete_pro" type="radio" value="1_a_10_ans" class="radio-input" />
                1 à 10 ans
              </label>
              <label class="radio-label">
                <input v-model="form.anciennete_pro" type="radio" value="plus_10_ans" class="radio-input" />
                Plus de 10 ans
              </label>
            </div>
          </div>

          <!-- Relation type -->
          <div class="form-group form-group--full">
            <label class="form-label">Type de relation</label>
            <div class="radio-group radio-group--inline">
              <label class="radio-label">
                <input v-model="form.relation_type" type="radio" value="initiale" class="radio-input" />
                Entrée en relation initiale
              </label>
              <label class="radio-label">
                <input v-model="form.relation_type" type="radio" value="actualisation" class="radio-input" />
                Actualisation
              </label>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Date de signature</label>
            <input v-model="form.date_signature" type="date" class="form-input" />
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="step-nav">
        <button v-if="currentStep > 0" class="btn-ghost" @click="prev">← Précédent</button>
        <span v-else />
        <div class="nav-right">
          <div class="save-indicator">
            <span v-if="kycId" class="saved-chip">✓ Formulaire créé</span>
          </div>
          <button
            v-if="currentStep < SECTIONS.length - 1"
            class="btn-primary"
            :disabled="!canNext || saving"
            @click="next"
          >
            <svg v-if="saving" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
            Suivant →
          </button>
          <button
            v-else
            class="btn-primary"
            :disabled="saving"
            @click="finish"
          >
            {{ saving ? 'Enregistrement…' : 'Terminer & valider' }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { dossiersService, type KycPPData } from '@/services/dossiers'
import CountrySelect from '@/components/common/CountrySelect.vue'
import TriggerBanner from '@/components/kyc/TriggerBanner.vue'

const route  = useRoute()
const router = useRouter()

const dossierId = route.params.id as string

const loading     = ref(true)
const saving      = ref(false)
const saveStatus  = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const saveErrorMsg = ref('')
const errors      = ref<Record<string, string>>({})

// Un blocage T3 sanctions renvoie un detail STRING (HTTPException) ; une erreur
// de validation Pydantic renvoie un detail ARRAY. On affiche le message explicite
// dans le 1er cas (ex. « Client sur liste de sanctions — dossier bloqué »).
function setSaveError(e: any): void {
  const detail = e?.response?.data?.detail
  saveErrorMsg.value = (e?.response?.status === 422 && typeof detail === 'string') ? detail : ''
  saveStatus.value = 'error'
}

// ── Pré-check sanctions temps réel (comme l'assujetti) ────────────────────────
const sanctionsState = ref<{ status: string; liste: string | null; reason: string | null }>(
  { status: 'idle', liste: null, reason: null },
)
let _sancTimer: ReturnType<typeof setTimeout> | null = null

function triggerSanctionsCheck(): void {
  if (!form.nom?.trim() || !form.prenoms?.trim()) {
    sanctionsState.value = { status: 'idle', liste: null, reason: null }
    return
  }
  if (_sancTimer) clearTimeout(_sancTimer)
  _sancTimer = setTimeout(async () => {
    sanctionsState.value = { status: 'checking', liste: null, reason: null }
    try {
      const r = await dossiersService.checkSanctionsPreScreen(
        form.nom!, form.prenoms!,
        form.date_naissance || undefined,
        (form.nationalite as string) || undefined,
      )
      sanctionsState.value = { status: r.level, liste: r.liste, reason: r.reason }
    } catch {
      sanctionsState.value = { status: 'idle', liste: null, reason: null }
    }
  }, 500)
}

watch(() => [form.nom, form.prenoms, form.date_naissance, form.nationalite], triggerSanctionsCheck)

// Bannière sanctions live (pré-check) ; sinon message d'erreur de save.
const sanctionsBanner = computed(() => {
  const s = sanctionsState.value
  if (s.status === 'checking') return { icon: '⏳', text: 'Vérification sanctions en cours…', style: 'background:#f1f5f9;color:#475569;border:1px solid #cbd5e1' }
  if (s.status === 'blocked')  return { icon: '⛔', text: `Client présent sur la liste de sanctions${s.liste ? ' (' + s.liste + ')' : ''} — création bloquée (Trigger T3, Art. 89).`, style: 'background:#fee2e2;color:#b91c1c;border:1px solid #fca5a5' }
  if (s.status === 'warning')  return { icon: '⚠️', text: `Correspondance possible sur liste ${s.liste ?? ''} — précisez la date de naissance, vérification RC requise.`, style: 'background:#fef3c7;color:#92400e;border:1px solid #fcd34d' }
  if (s.status === 'no_lists') return { icon: 'ℹ️', text: 'Aucune liste de sanctions active — criblage inopérant.', style: 'background:#f1f5f9;color:#475569;border:1px solid #cbd5e1' }
  return null
})
const currentStep = ref(0)
const kycId       = ref<string | undefined>(undefined)

const SECTIONS = [
  'Identité', 'Coordonnées', 'Activité', 'Mandataire', 'PPE & Opération', 'Origine fonds',
]

const FONCTIONS_MANDATAIRE = ['PDG', 'DG', 'DGA', 'Administrateur Général', 'Président', 'Gérant', 'Mandataire', 'Autre']

const OPERATION_OPTIONS = [
  { key: 'achat_immo',         label: 'Achat / Vente immobilière' },
  { key: 'manipulation_fonds', label: 'Manipulation de fonds / actifs' },
  { key: 'creation_societe',   label: 'Constitution / gestion de société' },
  { key: 'fiducicommis',       label: 'Fidéicommis / structures analogues' },
  { key: 'succession',         label: 'Succession / Héritage' },
  { key: 'donation',           label: 'Donation' },
]

const FONDS_OPTIONS = [
  { key: 'activite',               label: "Revenus d'activité professionnelle" },
  { key: 'associes',               label: "Apports d'associés" },
  { key: 'vente_immeuble',         label: "Produit de vente d'immeuble" },
  { key: 'bancaire',               label: 'Crédit bancaire' },
]

// ── Reactive form ────────────────────────────────────────────────────────────

const form = reactive<Partial<KycPPData> & {
  mandataire: { prenom_nom: string; type_piece: string; numero_piece: string; date_naissance: string | null; nationalite: string; pays_residence: string; fonction: string }
  operations_cochees: { achat_immo: boolean; manipulation_fonds: boolean; creation_societe: boolean; fiducicommis: boolean; succession: boolean; donation: boolean; autre_detail: string }
  origine_fonds: { activite: boolean; associes: boolean; vente_immeuble: boolean; bancaire: boolean; autres: string; propriete_intervenants: boolean; propriete_tiers: boolean; interet_tiers: boolean; territoire_ivoirien: boolean; pays_provenance: string }
}>({
  relation_type: 'initiale',
  nom: '', prenoms: '', nom_jeune_fille: null, nom_prenoms_pere: null, nom_prenoms_mere: null,
  date_naissance: null, lieu_naissance: null, nationalite: null, autres_nationalites: null, statut_matrimonial: null,
  type_piece: null, numero_piece: null,
  adresse_geo: null, adresse_postale: null, telephone: null, whatsapp: null, email: null,
  non_resident: false, pays_residence: null, numero_contribuable: null,
  profession: null, profession_5_ans: null, employeur: null, secteur_activite: null,
  mandataire: { prenom_nom: '', type_piece: '', numero_piece: '', date_naissance: null, nationalite: '', pays_residence: '', fonction: '' },
  est_ppe: false, ppe_detail: null,
  operations_cochees: { achat_immo: false, manipulation_fonds: false, creation_societe: false, fiducicommis: false, succession: false, donation: false, autre_detail: '' },
  description_operation: null,
  origine_fonds: { activite: false, associes: false, vente_immeuble: false, bancaire: false, autres: '', propriete_intervenants: false, propriete_tiers: false, interet_tiers: false, territoire_ivoirien: true, pays_provenance: '' },
  anciennete_pro: null,
  date_signature: null,
})

// ── Load ──────────────────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    const data = await dossiersService.getKycPP(dossierId)
    if (data.id) kycId.value = data.id
    // Patch simple fields
    const simpleFields: (keyof KycPPData)[] = [
      'relation_type','nom','prenoms','nom_jeune_fille','nom_prenoms_pere','nom_prenoms_mere',
      'date_naissance','lieu_naissance','nationalite','autres_nationalites','statut_matrimonial',
      'type_piece','numero_piece','adresse_geo','adresse_postale','telephone','whatsapp','email',
      'non_resident','pays_residence','numero_contribuable','profession','profession_5_ans',
      'employeur','secteur_activite','est_ppe','ppe_detail','description_operation',
      'anciennete_pro','date_signature',
    ]
    for (const f of simpleFields) {
      if (data[f] !== undefined && data[f] !== null) (form as any)[f] = data[f]
    }
    if (data.mandataire) Object.assign(form.mandataire, data.mandataire)
    if (data.operations_cochees) Object.assign(form.operations_cochees, data.operations_cochees)
    if (data.origine_fonds) Object.assign(form.origine_fonds, data.origine_fonds)
  } catch {
    // 404 → form vierge
  }
  loading.value = false
  // Criblage immédiat si le dossier chargé a déjà nom + prénoms (vérif avant Suivant)
  triggerSanctionsCheck()
})

// ── Auto-save ─────────────────────────────────────────────────────────────────

let autoSaveTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => { autoSaveTimer = setInterval(autoSave, 30_000) })
onUnmounted(() => { if (autoSaveTimer) clearInterval(autoSaveTimer) })

async function autoSave() {
  if (!kycId.value && !form.nom?.trim()) return
  saveStatus.value = 'saving'
  try {
    await saveSection()
    saveStatus.value = 'saved'
    setTimeout(() => { if (saveStatus.value === 'saved') saveStatus.value = 'idle' }, 3000)
  } catch (e) {
    setSaveError(e)
  }
}

// ── Save ──────────────────────────────────────────────────────────────────────

function buildPayload(): Partial<KycPPData> {
  const p: Partial<KycPPData> = { ...form } as Partial<KycPPData>
  p.mandataire = form.mandataire.prenom_nom ? { ...form.mandataire } : null
  p.operations_cochees = { ...form.operations_cochees }
  p.origine_fonds = { ...form.origine_fonds } as any
  if (!p.date_naissance) p.date_naissance = null
  if (!p.date_signature) p.date_signature = null
  return p
}

async function saveSection(): Promise<void> {
  const saved = await dossiersService.upsertKycPP(dossierId, buildPayload())
  if (saved.id) kycId.value = saved.id
}

// ── Validation ────────────────────────────────────────────────────────────────

const canNext = computed(() => {
  if (currentStep.value === 0) {
    if (sanctionsState.value.status === 'blocked' || sanctionsState.value.status === 'checking') return false
    return !!form.nom?.trim() && !!form.prenoms?.trim()
  }
  return true
})

function validateStep(): boolean {
  errors.value = {}
  if (currentStep.value === 0) {
    if (!form.nom?.trim()) errors.value.nom = 'Champ requis.'
    if (!form.prenoms?.trim()) errors.value.prenoms = 'Champ requis.'
  }
  return Object.keys(errors.value).length === 0
}

// ── Navigation ────────────────────────────────────────────────────────────────

async function next() {
  if (!validateStep()) return
  saving.value = true
  saveStatus.value = 'saving'
  try {
    await saveSection()
    saveStatus.value = 'saved'
    setTimeout(() => { if (saveStatus.value === 'saved') saveStatus.value = 'idle' }, 2000)
    currentStep.value++
  } catch (e) {
    setSaveError(e)
  } finally {
    saving.value = false
  }
}

function prev() { currentStep.value-- }

async function finish() {
  if (!validateStep()) return
  saving.value = true
  try {
    await saveSection()
    router.push({ name: 'kyc-detail', params: { id: dossierId } })
  } catch (e) {
    setSaveError(e)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.pp-page { max-width: 860px; display: flex; flex-direction: column; gap: 1.25rem; }

.page-header { margin-bottom: 0; }
.breadcrumb { display: flex; align-items: center; gap: 0.25rem; margin-bottom: 0.25rem; }
.breadcrumb-link { background: none; border: none; cursor: pointer; font-size: 0.8125rem; color: var(--color-text-secondary); padding: 0; }
.breadcrumb-link:hover { color: var(--color-sidebar-bg); }
.breadcrumb-sep { width: 14px; height: 14px; color: var(--color-border); }
.breadcrumb span { font-size: 0.8125rem; color: var(--color-text-primary); }
.page-title   { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }

/* Step bar */
.step-bar { display: flex; align-items: flex-start; flex-wrap: wrap; gap: 0.25rem 0; }
.step-item { display: flex; align-items: center; gap: 0.375rem; }
.step-dot { width: 24px; height: 24px; border-radius: 50%; border: 2px solid var(--color-border); background: var(--color-bg-card); display: flex; align-items: center; justify-content: center; font-size: 0.6875rem; font-weight: 700; color: var(--color-text-muted); flex-shrink: 0; }
.step-dot svg { width: 11px; height: 11px; }
.step-item--done .step-dot  { border-color: var(--color-status-valide); background: var(--color-status-valide-bg); color: var(--color-status-valide); }
.step-item--active .step-dot { border-color: var(--color-sidebar-bg); background: var(--color-sidebar-bg); color: #fff; }
.step-label { font-size: 0.6875rem; font-weight: 500; color: var(--color-text-muted); white-space: nowrap; }
.step-item--active .step-label { color: var(--color-sidebar-bg); font-weight: 700; }
.step-item--done .step-label  { color: var(--color-text-secondary); }
.step-connector { width: 20px; height: 2px; background: var(--color-border); flex-shrink: 0; }

/* Save status */
.save-status { display: flex; align-items: center; gap: 0.375rem; font-size: 0.75rem; height: 1.25rem; color: transparent; }
.save-status svg { width: 13px; height: 13px; }
.save-status--saving { color: var(--color-text-secondary); }
.save-status--saved  { color: var(--color-status-valide); }
.save-status--error  { color: var(--color-status-bloque); }

/* Section card */
.section-card { padding: 1.5rem; }
.section-title { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.375rem; display: flex; align-items: center; gap: 0.625rem; }
.section-hint { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0 0 1rem; }

/* Form */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem 1.25rem; }
.form-group { display: flex; flex-direction: column; gap: 0.25rem; }
.form-group--full { grid-column: 1 / -1; }
.form-label { font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); }
.req { color: var(--color-status-bloque); }
.form-input, .form-select, .form-textarea {
  padding: 0.5rem 0.75rem; border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; color: var(--color-text-primary); background: var(--color-bg-card); outline: none;
}
.form-input:focus, .form-select:focus, .form-textarea:focus {
  border-color: var(--color-sidebar-bg); box-shadow: 0 0 0 3px rgba(201,162,39,0.12);
}
.form-textarea { resize: vertical; }
.form-error { font-size: 0.75rem; color: var(--color-status-bloque); margin: 0; }
.checkbox-row { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.checkbox { width: 15px; height: 15px; accent-color: var(--color-sidebar-bg); cursor: pointer; }

/* PPE block */
.ppe-block { border: 1.5px solid var(--color-border); border-radius: 10px; padding: 1rem; }
.ppe-block--active { border-color: var(--color-risk-high); background: var(--color-risk-high-bg); }
.trigger-tag { font-size: 0.6875rem; font-weight: 800; background: var(--color-risk-high); color: #fff; border-radius: 4px; padding: 2px 6px; letter-spacing: 0.04em; }

/* Ops check grid */
.ops-check-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
.op-check-card { display: flex; align-items: center; gap: 0.5rem; padding: 0.625rem 0.875rem; border: 1.5px solid var(--color-border); border-radius: 8px; cursor: pointer; transition: border-color 0.15s; }
.op-check-card:hover { border-color: var(--color-sidebar-bg); }
.op-check-card--selected { border-color: var(--color-sidebar-bg); background: rgba(201,162,39,0.06); }
.op-check-label { font-size: 0.8125rem; color: var(--color-text-primary); }

/* Radio */
.radio-group { display: flex; flex-direction: column; gap: 0.5rem; }
.radio-group--inline { flex-direction: row; flex-wrap: wrap; gap: 0.5rem; }
.radio-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; cursor: pointer; padding: 0.5rem 0.75rem; border-radius: 7px; border: 1px solid var(--color-border); }
.radio-label:has(.radio-input:checked) { border-color: var(--color-sidebar-bg); background: rgba(201,162,39,0.06); }
.radio--oui { color: var(--color-risk-high); }
.radio--oui:has(.radio-input:checked) { border-color: var(--color-risk-high); background: var(--color-risk-high-bg); }
.radio-input { accent-color: var(--color-sidebar-bg); }

/* Navigation */
.step-nav { display: flex; align-items: center; justify-content: space-between; }
.nav-right { display: flex; align-items: center; gap: 0.75rem; }
.save-indicator { font-size: 0.75rem; }
.saved-chip { color: var(--color-status-valide); font-weight: 600; }
.btn-ghost { padding: 0.5rem 0.875rem; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 0.8125rem; cursor: pointer; }
.btn-primary { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5625rem 1.25rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { opacity: 0.88; }
.btn-icon { width: 14px; height: 14px; }

.loading-card { padding: 3rem; text-align: center; font-size: 0.875rem; color: var(--color-text-muted); }

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 0.8s linear infinite; }
</style>
