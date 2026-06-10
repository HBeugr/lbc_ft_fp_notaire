<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">Matrice de Risque LBC/FT</h1>
        <p class="page-subtitle">Référentiel d'évaluation des risques de blanchiment de capitaux et financement du terrorisme.</p>
      </div>
    </div>

    <!-- Onglets -->
    <div class="tabs-bar">
      <button
        v-for="tab in TABS" :key="tab.id"
        :class="['tab-btn', { active: activeTab === tab.id }]"
        @click="activeTab = tab.id"
      >{{ tab.label }}</button>
    </div>

    <!-- ── Onglet 1 : Vue d'ensemble ── -->
    <div v-if="activeTab === 'overview'">
      <!-- 3 cartes niveau de risque -->
      <div class="risk-cards-row">
        <div class="risk-card risk-card-faible">
          <div class="risk-card-header">
            <span class="risk-icon risk-icon-faible">🛡</span>
            <span class="risk-card-label">Risque Faible</span>
          </div>
          <p class="risk-card-desc">Dossiers présentant un risque minime. Procédure de vigilance allégée autorisée.</p>
          <div class="risk-card-score faible">Score: 0 – 7 / 20</div>
          <div class="risk-card-count">{{ stats.faible }} dossier{{ stats.faible !== 1 ? 's' : '' }}</div>
        </div>

        <div class="risk-card risk-card-moyen">
          <div class="risk-card-header">
            <span class="risk-icon risk-icon-moyen">🛡</span>
            <span class="risk-card-label">Risque Moyen</span>
          </div>
          <p class="risk-card-desc">Niveau de risque standard. Application de la vigilance normale avec mise à jour annuelle.</p>
          <div class="risk-card-score moyen">Score: 8 – 13 / 20</div>
          <div class="risk-card-count">{{ stats.moyen }} dossier{{ stats.moyen !== 1 ? 's' : '' }}</div>
        </div>

        <div class="risk-card risk-card-eleve">
          <div class="risk-card-header">
            <span class="risk-icon risk-icon-eleve">⚠</span>
            <span class="risk-card-label">Risque Élevé</span>
          </div>
          <p class="risk-card-desc">Risque critique nécessitant une vigilance renforcée, l'approbation de la direction et un suivi continu.</p>
          <div class="risk-card-score eleve">Score: 14 – 20 / 20</div>
          <div class="risk-card-count">{{ stats.eleve }} dossier{{ stats.eleve !== 1 ? 's' : '' }}</div>
        </div>
      </div>

      <!-- Matrice Croisée -->
      <div class="card mt-card">
        <h3 class="section-title">Matrice Croisée (Client × Transaction)</h3>
        <p class="section-sub">Détermination du niveau de vigilance applicable selon le profil et l'opération.</p>

        <div class="matrice-wrap">
          <table class="matrice-table">
            <thead>
              <tr>
                <th class="th-empty"></th>
                <th>Opération Courante</th>
                <th>Opération Complexe</th>
                <th>Opération Sensible (Espèces, Offshore)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="row-header">Client Standard (Local)</td>
                <td class="cell cell-alleg">Vigilance Allégée</td>
                <td class="cell cell-normal">Vigilance Normale</td>
                <td class="cell cell-renforce">Vigilance Renforcée</td>
              </tr>
              <tr>
                <td class="row-header">Client à Risque (Non-résident, Complexe)</td>
                <td class="cell cell-normal">Vigilance Normale</td>
                <td class="cell cell-normal-plus">Vigilance Normale +</td>
                <td class="cell cell-renforce">Vigilance Renforcée</td>
              </tr>
              <tr>
                <td class="row-header">Client Très Sensible (PPE, Sanctions)</td>
                <td class="cell cell-renforce">Vigilance Renforcée</td>
                <td class="cell cell-renforce-pp">Vigilance Renforcée ++</td>
                <td class="cell cell-refus">Refus ou DOS</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Onglet 2 : Critères d'évaluation ── -->
    <div v-else-if="activeTab === 'criteres'" class="card">
      <h3 class="section-title">Catalogue des Facteurs de Risque</h3>
      <p class="section-sub">Référentiel des critères utilisés pour évaluer le niveau de risque LBC/FT de chaque dossier et opération.</p>

      <div class="catalogue-wrap">
        <table class="catalogue-table">
          <thead>
            <tr>
              <th>Catégorie</th>
              <th>Facteur de Risque</th>
              <th>Pondération</th>
              <th>Niveau de Risque</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(f, i) in CATALOGUE_FACTEURS" :key="i">
              <tr>
                <td class="cat-cell">
                  <span v-if="i === 0 || f.categorie !== CATALOGUE_FACTEURS[i - 1].categorie" class="cat-label">{{ f.categorie }}</span>
                </td>
                <td class="facteur-cell">{{ f.facteur }}</td>
                <td class="poids-cell">{{ f.poids }}</td>
                <td>
                  <span :class="['niveau-cat-badge', 'cat-' + f.niveau]">
                    {{ f.niveau === 'eleve' ? 'ÉLEVÉ' : f.niveau === 'moyen' ? 'MOYEN' : 'FAIBLE' }}
                  </span>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Onglet 3 : Simulateur ── -->
    <div v-else-if="activeTab === 'simulateur'" class="sim-layout">
      <div class="card sim-form">
        <h3 class="section-title">Simulateur de Profil</h3>
        <p class="section-sub">Testez une combinaison de facteurs pour évaluer le niveau de vigilance requis.</p>

        <div class="sim-fields">
          <div class="sim-section-label">Profil & Géographie</div>

          <div class="field">
            <label class="field-label">Axe 1 — Profil client</label>
            <select v-model="sim.profil_code" class="field-input">
              <option value="">Sélectionnez un profil client</option>
              <option value="particulier_salarie">Particulier salarié — Score 0 (Faible)</option>
              <option value="profession_liberale">Profession libérale / entrepreneur — Score 1 (Moyen)</option>
              <option value="societe_sarl">Société (SARL, SA) — Score 1 (Moyen)</option>
              <option value="societe_complexe">Société actionnariat complexe — Score 2 (Élevé)</option>
              <option value="structure_atypique">Structure atypique (holding, offshore) — Score 2 (Élevé)</option>
            </select>
          </div>

          <div class="field">
            <label class="field-label">Axe 2 — Origine géographique</label>
            <select v-model="sim.zone_geo" class="field-input">
              <option value="">Sélectionnez une zone géographique</option>
              <option value="cote_ivoire">Côte d'Ivoire — Score 0 (Faible)</option>
              <option value="uemoa">Zone UEMOA (hors CI) — Score 1 (Moyen)</option>
              <option value="europe_regule">Europe / pays régulés — Score 1 (Moyen)</option>
              <option value="gafi">Pays liste grise/noire GAFI — Score 2 (Élevé · T4)</option>
            </select>
          </div>

          <div class="sim-section-label">Transaction</div>

          <div class="field">
            <label class="field-label">Axe 3 — Type d'opération</label>
            <select v-model="sim.type_operation" class="field-input">
              <option value="">Sélectionnez le type d'opération</option>
              <option value="location_simple">Location résidentielle simple — Score 0 (Faible)</option>
              <option value="vente_simple">Vente résidentielle simple — Score 0 (Faible)</option>
              <option value="location_commerciale">Location / vente commerciale — Score 1 (Moyen)</option>
              <option value="gestion_locative">Gestion locative (mandat) — Score 1 (Moyen)</option>
              <option value="vefa">VEFA / programme neuf — Score 1 (Moyen)</option>
              <option value="achat_tiers">Achat pour compte de tiers — Score 2 (Élevé · KYC mandant)</option>
              <option value="partenariat">Partenariat investisseur / lotissement — Score 2 (Élevé)</option>
            </select>
          </div>

          <div class="field">
            <label class="field-label">Axe 4 — Montant</label>
            <select v-model="sim.montant" class="field-input">
              <option value="">Sélectionnez le montant</option>
              <option value="0">&lt; 5M FCFA — Score 0 (Faible)</option>
              <option value="1">5 – 15M FCFA — Score 1 (Moyen)</option>
              <option value="2">&gt; 15M FCFA — Score 2 (Élevé · T2 si espèces)</option>
            </select>
          </div>

          <div class="field">
            <label class="field-label">Axe 5 — Mode de paiement</label>
            <select v-model="sim.mode_paiement_code" class="field-input">
              <option value="">Sélectionnez le mode de paiement</option>
              <option value="virement">Virement bancaire — Score 0 (Faible)</option>
              <option value="cheque_certifie">Chèque certifié — Score 0 (Faible)</option>
              <option value="cheque_simple">Chèque simple / mix — Score 1 (Moyen)</option>
              <option value="especes_hors">Espèces hors seuils — Score 1 (Moyen)</option>
              <option value="especes_15m">Espèces &gt; 15M FCFA — Score 2 (Élevé · T2)</option>
              <option value="especes_art74">Espèces ≥ seuil Art. 74 (immo) — Score 2 (Élevé · T2)</option>
              <option value="tiers_non_identifie">Paiement via tiers non identifié — Score 2 (Élevé · Suspicion)</option>
            </select>
          </div>

          <div class="field">
            <label class="field-label">Axe 6 — Montage juridique</label>
            <select v-model="sim.montage_juridique" class="field-input">
              <option value="">Sélectionnez le montage juridique</option>
              <option value="0">Bail / promesse simple — Score 0 (Faible)</option>
              <option value="1">SCI familiale / VEFA standard — Score 1 (Moyen)</option>
              <option value="2">SCI multi-associés / holding — Score 2 (Élevé)</option>
              <option value="2">Démembrement / fiducie — Score 2 (Élevé)</option>
            </select>
          </div>

          <div class="sim-section-label">Statut PPE</div>

          <div class="field">
            <label class="field-label">Axe 7 — Statut PPE</label>
            <select v-model="sim.is_ppe" class="field-input">
              <option value="">Sélectionnez le statut PPE</option>
              <option value="false">Non-PPE — Score 0 (Faible)</option>
              <option value="true">PPE nationale / étrangère / entourage — Score 2 (Élevé · T1)</option>
            </select>
          </div>

          <div class="sim-section-label">Due Diligence & Secteur</div>

          <div class="field">
            <label class="field-label">Axe 8 — Qualité documentaire</label>
            <select v-model="sim.qualite_code" class="field-input">
              <option value="">Sélectionnez la qualité documentaire</option>
              <option value="complet">Dossier complet et cohérent — Score 0 (Faible)</option>
              <option value="doute">Léger doute documentaire — Score 1 (Moyen)</option>
              <option value="incoherence">Incohérences / refus documentaire — Score 2 (Élevé · Blocage)</option>
              <option value="presse_negative">Presse négative avérée — Score 2 (Élevé · Alerte RC)</option>
            </select>
          </div>

          <div class="field">
            <label class="field-label">Axe 9 — Secteur d'activité</label>
            <select v-model="sim.secteur_activite" class="field-input">
              <option value="">Sélectionnez le secteur d'activité</option>
              <option value="0">Secteur classique (salarié, PME) — Score 0 (Faible)</option>
              <option value="1">Commerce / cash / import-export — Score 1 (Moyen)</option>
              <option value="2">Secteurs sensibles (crypto, jeux) — Score 2 (Élevé · Alerte)</option>
            </select>
          </div>

          <div class="field">
            <label class="field-label">Axe 10 — Réseau de distribution</label>
            <select v-model="sim.reseau_code" class="field-input">
              <option value="">Sélectionnez le réseau de distribution</option>
              <option value="aucun">Aucun intermédiaire — Score 0 (Faible)</option>
              <option value="agent_reglemente">Agent immobilier réglementé — Score 0 (Faible)</option>
              <option value="apporteur">Apporteur d'affaires identifié — Score 1 (Moyen)</option>
              <option value="intermediaire_non_clair">Intermédiaire non clair / multiples — Score 2 (Élevé)</option>
              <option value="intermediaire_pays_risque">Intermédiaire basé pays à risque — Score 2 (Élevé · T4)</option>
            </select>
          </div>
        </div>

        <button class="btn-calculer" :disabled="simLoading || !sim.profil_code" @click="runSim">
          {{ simLoading ? 'Calcul en cours…' : 'Calculer le Risque' }}
        </button>
      </div>

      <!-- Panneau résultat -->
      <div v-if="simResult" class="card sim-result">
        <h3 class="section-title">Résultat de l'Évaluation</h3>
        <p class="section-sub">Le score calculé détermine les obligations déclaratives et le niveau de vigilance.</p>
        <div class="score-circle-wrap">
          <div :class="['score-circle', 'circle-' + simResult.niveau.toLowerCase()]">
            <span class="circle-score">{{ simResult.score_total }}</span>
            <span class="circle-max">/20</span>
          </div>
          <div :class="['niveau-badge', 'badge-' + simResult.niveau.toLowerCase()]">
            {{ niveauLabel(simResult.niveau) }}
          </div>
        </div>
        <div class="axes-result">
          <div v-for="axe in simResult.axes" :key="axe.code" class="axe-row">
            <div class="axe-row-header">
              <span class="axe-row-label">{{ axe.label }}</span>
              <span :class="['axe-score-badge', 'badge-pts-' + axe.score]">{{ axe.score }} pt{{ axe.score > 1 ? 's' : '' }}</span>
            </div>
            <span class="axe-justif">{{ axe.justification }}</span>
          </div>
        </div>
        <div class="nouvelle-sim">
          <a href="#" @click.prevent="resetSim">↺ Nouvelle Simulation</a>
        </div>
      </div>

      <div v-else class="card sim-empty">
        <h3 class="section-title">Résultat de l'Évaluation</h3>
        <p class="section-sub">Le score calculé détermine les obligations déclaratives et le niveau de vigilance.</p>
        <div class="sim-empty-content">
          <div class="sim-empty-icon">ℹ</div>
          <p>Remplissez les critères ci-contre pour générer une évaluation de risque simulée.</p>
        </div>
      </div>
    </div>

    <!-- ── Onglet 4 : Triggers T1-T6 ── -->
    <div v-else-if="activeTab === 'triggers'" class="card triggers-panel">
      <h3 class="section-title">Triggers Absolutoires T1-T6</h3>
      <p class="section-sub">
        Les 6 déclencheurs absolutoires qui forcent automatiquement le niveau ÉLEVÉ, indépendamment
        du score calculé. Non désactivables — verrouillés par l'Ordonnance N°2023-875.
      </p>

      <div class="trigger-list">
        <div v-for="t in TRIGGERS" :key="t.code" class="trigger-card" :class="`trigger--${t.color}`">
          <div class="trigger-header">
            <span class="trigger-code">{{ t.code }}</span>
            <span class="trigger-label">{{ t.label }}</span>
            <span :class="['trigger-niveau', `trigger-niveau--${t.color}`]">{{ t.niveau }}</span>
          </div>
          <p class="trigger-desc">{{ t.description }}</p>
          <div class="trigger-consequence">
            <strong>Conséquence :</strong> {{ t.consequence }}
          </div>
          <div class="trigger-ref">{{ t.ref }}</div>
        </div>
      </div>
    </div>

    <!-- ── Onglet 5 : Seuils (lecture seule — NFR-8) ── -->
    <div v-else-if="activeTab === 'seuils'" class="card">
      <h3 class="section-title">Seuils de Classification du Risque</h3>
      <p class="section-sub">Les seuils sont verrouillés par la réglementation (NFR-8 — Art. 74 UEMOA). Toute modification requiert un avenant réglementaire.</p>

      <div class="seuils-grid">
        <div class="seuil-card seuil-card-faible">
          <div class="seuil-card-header">
            <span class="seuil-icon">🟢</span>
            <span class="seuil-label">Risque Faible</span>
          </div>
          <div class="seuil-range">Score 0 – 7 / 20</div>
          <p class="seuil-desc">Vigilance allégée applicable. Révision périodique annuelle.</p>
          <div class="seuil-locked">🔒 Verrouillé — NFR-8</div>
        </div>

        <div class="seuil-card seuil-card-moyen">
          <div class="seuil-card-header">
            <span class="seuil-icon">🟡</span>
            <span class="seuil-label">Risque Moyen</span>
          </div>
          <div class="seuil-range">Score 8 – 13 / 20</div>
          <p class="seuil-desc">Vigilance standard. Mise à jour documentaire semestrielle.</p>
          <div class="seuil-locked">🔒 Verrouillé — NFR-8</div>
        </div>

        <div class="seuil-card seuil-card-eleve">
          <div class="seuil-card-header">
            <span class="seuil-icon">🔴</span>
            <span class="seuil-label">Risque Élevé</span>
          </div>
          <div class="seuil-range">Score 14 – 20 / 20</div>
          <p class="seuil-desc">Vigilance renforcée obligatoire. Autorisation dirigeant requise (WRK-09). DOS (Déclaration d'Opération Suspecte) à envisager.</p>
          <div class="seuil-locked">🔒 Verrouillé — NFR-8</div>
        </div>
      </div>

      <div class="seuils-note">
        Pour le détail des 10 axes d'évaluation, consultez l'onglet
        <a href="#" @click.prevent="activeTab = 'criteres'" class="seuils-link">Critères d'évaluation</a>.
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dossiersService } from '@/services/dossiers'
import api from '@/services/api'

const activeTab = ref('overview')
const TABS = [
  { id: 'overview',    label: "Vue d'ensemble" },
  { id: 'criteres',   label: "Critères d'évaluation" },
  { id: 'simulateur', label: 'Simulateur de Risque' },
  { id: 'triggers',   label: 'Triggers T1-T6' },
  { id: 'seuils',     label: '⚙️ Seuils' },
]

// Les 6 triggers absolutoires forcent le niveau ÉLEVÉ indépendamment du score
// calculé (source : scoring_service.calculate — T1..T6, CLAUDE.md verrouillé).
const TRIGGERS = [
  {
    code: 'T1',
    label: 'PPE — Personne Politiquement Exposée',
    niveau: 'ÉLEVÉ',
    color: 'eleve',
    description: 'Client PPE nationale, étrangère, ou membre de son entourage direct.',
    consequence: 'Force automatiquement le niveau ÉLEVÉ. Vigilance renforcée obligatoire et autorisation du Notaire avant poursuite de la relation.',
    ref: 'Art. 47-50 Ordonnance 2023-875',
  },
  {
    code: 'T2',
    label: 'Transaction espèces > 15M FCFA',
    niveau: 'ÉLEVÉ',
    color: 'eleve',
    description: 'Paiement partiel ou total en espèces dépassant 15 000 000 FCFA.',
    consequence: 'Force ÉLEVÉ. Justification de l\'origine des fonds obligatoire. DOS (Déclaration d\'Opération Suspecte) à envisager.',
    ref: 'Art. 72 Ordonnance 2023-875',
  },
  {
    code: 'T3',
    label: 'Client sur liste de sanctions',
    niveau: 'CRITIQUE',
    color: 'critique',
    description: 'Le client figure sur une liste de sanctions (OFAC, UE-CSNU, GIABA-BCEAO).',
    consequence: 'Force ÉLEVÉ. Blocage immédiat et gel des avoirs. DOS obligatoire.',
    ref: 'Art. 89 Ordonnance 2023-875 ; Résolutions ONU 1267/1373',
  },
  {
    code: 'T4',
    label: 'Pays liste noire / grise GAFI',
    niveau: 'ÉLEVÉ',
    color: 'eleve',
    description: 'Client ou fonds liés à un pays figurant sur la liste grise ou noire du GAFI.',
    consequence: 'Force ÉLEVÉ. Due diligence approfondie sur l\'origine des fonds. Approbation du Responsable Conformité requise.',
    ref: 'Recommandation GAFI 19 ; Art. 51 Ordonnance 2023-875',
  },
  {
    code: 'T5',
    label: 'Refus documentaire',
    niveau: 'ÉLEVÉ',
    color: 'eleve',
    description: 'Refus du client de fournir les documents KYC, ou documents incohérents / falsifiés.',
    consequence: 'Force ÉLEVÉ. Mise en attente du dossier. Signalement interne immédiat au RC. DOS possible si soupçon fondé.',
    ref: 'Art. 45 Ordonnance 2023-875',
  },
  {
    code: 'T6',
    label: 'Bénéficiaire effectif non identifiable',
    niveau: 'ÉLEVÉ',
    color: 'eleve',
    description: 'Impossibilité d\'identifier le(s) bénéficiaire(s) effectif(s) réel(s) (≥ 25%) de l\'opération.',
    consequence: 'Force ÉLEVÉ. Vigilance renforcée. Poursuite conditionnée à l\'identification effective du bénéficiaire.',
    ref: 'Ordonnance 2023-875 — identification du bénéficiaire effectif',
  },
]

const CATALOGUE_FACTEURS = [
  { categorie: 'Profil Client',       facteur: 'Personne Politiquement Exposée (PPE)',                     poids: 'Score 2 / 2', niveau: 'eleve'  },
  { categorie: 'Profil Client',       facteur: 'Personne Morale avec structure complexe',                  poids: 'Score 1 / 2', niveau: 'moyen'  },
  { categorie: 'Profil Client',       facteur: 'Personne Physique salariée (local)',                       poids: 'Score 0 / 2', niveau: 'faible' },
  { categorie: 'Géographie',          facteur: 'Pays sous contre-mesures GAFI (liste noire)',              poids: 'Score 2 / 2', niveau: 'eleve'  },
  { categorie: 'Géographie',          facteur: 'Pays sous surveillance GAFI (liste grise)',                poids: 'Score 1 / 2', niveau: 'moyen'  },
  { categorie: 'Géographie',          facteur: 'Pays UEMOA / zone réglementée',                           poids: 'Score 0 / 2', niveau: 'faible' },
  { categorie: 'Transaction',         facteur: 'Paiement en espèces > seuil Art. 74',                     poids: 'Score 2 / 2', niveau: 'eleve'  },
  { categorie: 'Transaction',         facteur: 'Transaction immobilière sans financement bancaire',        poids: 'Score 1 / 2', niveau: 'moyen'  },
  { categorie: 'Transaction',         facteur: 'Virement bancaire traçable',                              poids: 'Score 0 / 2', niveau: 'faible' },
  { categorie: 'Documentation',       facteur: 'Identité non vérifiable / aucun document fourni',         poids: 'Score 2 / 2', niveau: 'eleve'  },
  { categorie: 'Documentation',       facteur: 'Dossier partiel — checklist incomplète',                  poids: 'Score 1 / 2', niveau: 'moyen'  },
  { categorie: 'Documentation',       facteur: 'Dossier complet et cohérent',                             poids: 'Score 0 / 2', niveau: 'faible' },
  { categorie: 'Structure juridique', facteur: 'Montage multi-niveaux / offshore',                        poids: 'Score 2 / 2', niveau: 'eleve'  },
  { categorie: 'Structure juridique', facteur: 'Société avec actionnaires partiellement identifiés',      poids: 'Score 1 / 2', niveau: 'moyen'  },
  { categorie: 'Structure juridique', facteur: 'Entreprise individuelle locale',                          poids: 'Score 0 / 2', niveau: 'faible' },
]

const AXES_LABELS = [
  { code: 'Axe 1',  label: 'Profil client',           description: 'PP salarié = 0 | Entrepreneur/PM = 1 | PPE = 2' },
  { code: 'Axe 2',  label: 'Origine géographique',    description: 'UEMOA/CI = 0 | Liste grise GAFI = 1 | Liste noire GAFI = 2' },
  { code: 'Axe 3',  label: "Type d'opération",        description: 'Location/Vente simple = 0 | Commercial/VEFA/Gestion = 1 | Achat tiers/Lotissement = 2' },
  { code: 'Axe 4',  label: 'Montant',                 description: '< 5M FCFA = 0 | 5–15M FCFA = 1 | > 15M FCFA = 2' },
  { code: 'Axe 5',  label: 'Mode de paiement',        description: 'Virement = 0 | Chèque/Mix = 1 | Espèces/Tiers = 2' },
  { code: 'Axe 6',  label: 'Montage juridique',       description: 'Acte simple = 0 | 2–3 parties = 1 | Schéma complexe = 2' },
  { code: 'Axe 7',  label: 'Statut PPE',              description: 'Non-PPE = 0 | PPE national/étranger = 2' },
  { code: 'Axe 8',  label: 'Qualité documentaire',    description: 'Dossier complet = 0 | Partiel = 1 | Aucun document = 2' },
  { code: 'Axe 9',  label: "Secteur d'activité",      description: "Sectoriel classique/PME = 0 | Commerce/cash/import = 1 | Crypto/Jeux sensibles = 2" },
  { code: 'Axe 10', label: 'Réseau de distribution',  description: "Aucun intermédiaire/Agent réglementé = 0 | Apporteur identifié = 1 | Intermédiaire non clair = 2" },
]

interface SimAxe { code: string; label: string; score: number; justification: string }
interface SimResult { score_total: number; niveau: string; axes: SimAxe[] }

const stats = ref({ faible: 0, moyen: 0, eleve: 0 })
const sim = ref({
  profil_code: '',        // Axe 1
  zone_geo: '',           // Axe 2
  type_operation: '',     // Axe 3
  montant: '',            // Axe 4
  mode_paiement_code: '', // Axe 5
  montage_juridique: '',  // Axe 6
  is_ppe: '',             // Axe 7
  qualite_code: '',       // Axe 8
  secteur_activite: '',   // Axe 9
  reseau_code: '',        // Axe 10
})
const simResult  = ref<SimResult | null>(null)
const simLoading = ref(false)

function niveauLabel(n: string) {
  return ({ FAIBLE: 'Risque Faible', MOYEN: 'Risque Moyen', ELEVE: 'Risque Élevé' } as Record<string, string>)[n] ?? n
}
function resetSim() {
  sim.value = {
    profil_code: '', zone_geo: '', type_operation: '',
    montant: '', mode_paiement_code: '', montage_juridique: '',
    is_ppe: '', qualite_code: '', secteur_activite: '', reseau_code: '',
  }
  simResult.value = null
}

async function runSim() {
  simLoading.value = true
  simResult.value  = null
  try {
    const toInt = (v: string) => v !== '' ? parseInt(v) : 0
    const { data } = await api.post<SimResult>('/scoring/simuler', {
      profil_code:        sim.value.profil_code        || 'particulier_salarie',
      zone_geo:           sim.value.zone_geo           || 'cote_ivoire',
      type_operation:     sim.value.type_operation     || 'location_simple',
      montant:            toInt(sim.value.montant),
      mode_paiement_code: sim.value.mode_paiement_code || 'virement',
      montage_juridique:  toInt(sim.value.montage_juridique),
      is_ppe:             sim.value.is_ppe === 'true',
      qualite_code:       sim.value.qualite_code       || 'complet',
      secteur_activite:   toInt(sim.value.secteur_activite),
      reseau_code:        sim.value.reseau_code        || 'aucun',
    })
    simResult.value = data
  } catch (err: any) {
    alert('Erreur simulateur : ' + (err.response?.data?.detail ?? err.message))
  } finally {
    simLoading.value = false
  }
}

async function loadStats() {
  try {
    let faible = 0, moyen = 0, eleve = 0
    const PAGE_SIZE = 100
    let page = 1, fetched = 0, total = Infinity
    while (fetched < total) {
      const resp = await dossiersService.list({ page, page_size: PAGE_SIZE })
      total = resp.total
      for (const d of resp.items) {
        const n = (d.niveau_risque ?? '').toUpperCase()
        if (n === 'FAIBLE') faible++
        else if (n === 'MOYEN') moyen++
        else if (n === 'ELEVE') eleve++
      }
      fetched += resp.items.length
      if (resp.items.length < PAGE_SIZE) break
      page++
    }
    stats.value = { faible, moyen, eleve }
  } catch { /* silencieux */ }
}

onMounted(() => { loadStats() })
</script>

<style scoped>
.page-container { max-width: 1300px; }
.page-header    { margin-bottom: 1.5rem; }
.page-title     { font-size: 1.625rem; font-weight: 700; color: var(--color-text-primary); }
.page-subtitle  { font-size: 0.9rem; color: var(--color-text-secondary); margin-top: 0.3rem; }

/* ── Tabs ── */
.tabs-bar {
  display: flex; gap: 0; margin-bottom: 1.5rem;
  border: 1px solid var(--color-border); border-radius: 8px;
  overflow: hidden; background: #fff; width: fit-content;
}
.tab-btn {
  padding: 0.7rem 1.5rem; font-size: 0.875rem; font-weight: 500;
  border: none; background: transparent; color: var(--color-text-secondary);
  cursor: pointer; transition: background 0.15s, color 0.15s;
  border-right: 1px solid var(--color-border); white-space: nowrap;
}
.tab-btn:last-child  { border-right: none; }
.tab-btn.active      { background: var(--color-sidebar-bg); color: #fff; }
.tab-btn:not(.active):hover { background: #f8fafc; color: var(--color-text-primary); }

/* ── Risk cards ── */
.risk-cards-row {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem; margin-bottom: 1.25rem;
}
.risk-card {
  background: #fff; border-radius: 10px; padding: 1.5rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.07); border-left: 4px solid transparent;
}
.risk-card-faible { border-left-color: var(--color-risk-low); }
.risk-card-moyen  { border-left-color: var(--color-risk-medium); }
.risk-card-eleve  { border-left-color: var(--color-risk-high); }
.risk-card-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; }
.risk-icon        { font-size: 1.1rem; }
.risk-icon-faible { color: var(--color-risk-low); }
.risk-icon-moyen  { color: var(--color-risk-medium); }
.risk-icon-eleve  { color: var(--color-risk-high); }
.risk-card-label  { font-size: 1rem; font-weight: 600; color: var(--color-text-primary); }
.risk-card-desc   { font-size: 0.8125rem; color: var(--color-text-secondary); line-height: 1.5; margin-bottom: 1rem; min-height: 3.5rem; }
.risk-card-score  { font-size: 1.25rem; font-weight: 700; margin-bottom: 0.35rem; }
.risk-card-score.faible { color: var(--color-risk-low); }
.risk-card-score.moyen  { color: var(--color-risk-medium); }
.risk-card-score.eleve  { color: var(--color-risk-high); }
.risk-card-count  { font-size: 0.8rem; color: var(--color-text-secondary); }

/* ── Card shared ── */
.card         { background: #fff; border-radius: 10px; padding: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }
.mt-card      { margin-top: 0; }
.section-title{ font-size: 1.125rem; font-weight: 700; color: var(--color-text-primary); margin-bottom: 0.35rem; }
.section-sub  { font-size: 0.8125rem; color: var(--color-text-secondary); margin-bottom: 1.25rem; }

/* ── Matrice croisée ── */
.matrice-wrap  { overflow-x: auto; }
.matrice-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.matrice-table th {
  background: #f8fafc; padding: 0.85rem 1rem; text-align: center;
  font-size: 0.8125rem; font-weight: 600; color: var(--color-text-secondary);
  border: 1px solid #e2e8f0;
}
.th-empty     { background: #fff; border: none; }
.matrice-table td { padding: 0.85rem 1rem; border: 1px solid #e2e8f0; text-align: center; font-size: 0.875rem; }
.row-header   { font-weight: 600; color: var(--color-text-primary); text-align: left !important; background: #f8fafc; }
.cell-alleg      { color: var(--color-risk-low); font-weight: 500; background: #f0fdf4; }
.cell-normal     { color: var(--color-text-primary); }
.cell-normal-plus{ color: var(--color-text-primary); }
.cell-renforce   { color: var(--color-risk-high); font-weight: 500; background: #fff7f7; }
.cell-renforce-pp{ color: var(--color-risk-high); font-weight: 700; background: #fff0f0; }
.cell-refus      { color: var(--color-risk-high); font-weight: 700; background: #fde8e8; }

/* ── Catalogue ── */
.catalogue-wrap  { overflow-x: auto; }
.catalogue-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.catalogue-table thead tr { background: #f8fafc; }
.catalogue-table th {
  padding: 0.75rem 1rem; text-align: left; font-size: 0.75rem; font-weight: 600;
  color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.04em;
  border-bottom: 2px solid var(--color-border); white-space: nowrap;
}
.catalogue-table td { padding: 0.7rem 1rem; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
.cat-cell    { width: 170px; }
.cat-label   { font-size: 0.8125rem; font-weight: 700; color: var(--color-text-primary); white-space: nowrap; }
.facteur-cell{ color: var(--color-text-primary); font-size: 0.875rem; }
.poids-cell  { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-secondary); white-space: nowrap; text-align: center; }
.niveau-cat-badge { display: inline-block; padding: 0.2rem 0.65rem; border-radius: 4px; font-size: 0.7rem; font-weight: 800; letter-spacing: 0.05em; color: #fff; }
.cat-faible  { background: var(--color-risk-low); }
.cat-moyen   { background: var(--color-risk-medium); }
.cat-eleve   { background: var(--color-risk-high); }

/* ── Simulateur ── */
.sim-layout  { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; align-items: start; }
.sim-fields  { display: flex; flex-direction: column; gap: 0.85rem; margin-bottom: 1.5rem; }
.sim-section-label {
  font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em;
  color: var(--color-text-secondary); padding: 0.35rem 0 0.1rem;
  border-top: 1px solid var(--color-border); margin-top: 0.25rem;
}
.sim-fields .sim-section-label:first-child { border-top: none; margin-top: 0; }
.field       { display: flex; flex-direction: column; gap: 0.35rem; }
.field-label { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-primary); }
.field-input {
  padding: 0.6rem 0.875rem; border: 1px solid var(--color-border); border-radius: 6px;
  font-size: 0.875rem; background: #fff; color: var(--color-text-primary); transition: border-color 0.15s;
}
.field-input:focus { outline: none; border-color: var(--color-sidebar-bg); }
.field-readonly {
  padding: 0.6rem 0.875rem; border: 1px dashed var(--color-border); border-radius: 6px;
  font-size: 0.875rem; background: #f8fafc; display: flex; justify-content: space-between; align-items: center;
}
.readonly-faible { color: var(--color-risk-low, #16a34a); border-color: var(--color-risk-low, #16a34a); }
.readonly-eleve  { color: var(--color-risk-high, #dc2626); border-color: var(--color-risk-high, #dc2626); }
.readonly-hint   { font-size: 0.7rem; color: var(--color-text-secondary); font-style: italic; }
.btn-calculer {
  width: 100%; padding: 0.8rem; border: none; border-radius: 8px;
  background: var(--color-sidebar-bg); color: #fff; font-size: 0.9375rem;
  font-weight: 600; cursor: pointer; transition: opacity 0.15s;
}
.btn-calculer:disabled          { opacity: 0.55; cursor: not-allowed; }
.btn-calculer:not(:disabled):hover { opacity: 0.9; }

.sim-result       { display: flex; flex-direction: column; gap: 1.25rem; }
.score-circle-wrap{ display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 1.25rem 0; }
.score-circle {
  width: 110px; height: 110px; border-radius: 50%; border: 7px solid #e2e8f0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.circle-faible { border-color: var(--color-risk-low); }
.circle-moyen  { border-color: var(--color-risk-medium); }
.circle-eleve  { border-color: var(--color-risk-high); }
.circle-score  { font-size: 2rem; font-weight: 800; line-height: 1; color: var(--color-text-primary); }
.circle-max    { font-size: 0.75rem; color: var(--color-text-secondary); }
.niveau-badge  { padding: 0.3rem 1.25rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 600; }
.badge-faible  { background: var(--color-risk-low-bg, #f0fdf4); color: var(--color-risk-low, #16a34a); }
.badge-moyen   { background: var(--color-risk-medium-bg, #fef9c3); color: var(--color-risk-medium, #d97706); }
.badge-eleve   { background: var(--color-risk-high-bg, #fee2e2); color: var(--color-risk-high, #dc2626); }

.axes-result     { display: flex; flex-direction: column; gap: 0.5rem; }
.axe-row         { padding: 0.625rem 0.75rem; background: #f8fafc; border-radius: 6px; }
.axe-row-header  { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem; }
.axe-row-label   { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-primary); }
.axe-score-badge { font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 9999px; }
.badge-pts-0 { background: #f1f5f9; color: #64748b; }
.badge-pts-1 { background: var(--color-risk-medium-bg, #fef9c3); color: var(--color-risk-medium, #b45309); }
.badge-pts-2 { background: var(--color-risk-high-bg, #fee2e2); color: var(--color-risk-high, #dc2626); }
.axe-justif  { font-size: 0.75rem; color: #64748b; }
.nouvelle-sim  { text-align: center; padding-top: 0.5rem; border-top: 1px solid var(--color-border); }
.nouvelle-sim a{ font-size: 0.875rem; color: var(--color-text-secondary); text-decoration: none; }
.nouvelle-sim a:hover { color: var(--color-sidebar-bg); }
.sim-empty     { display: flex; align-items: center; justify-content: center; min-height: 300px; }
.sim-empty-content { text-align: center; color: var(--color-text-secondary); }
.sim-empty-icon    { font-size: 3rem; margin-bottom: 1rem; opacity: 0.4; }
.sim-empty-content p { font-size: 0.875rem; line-height: 1.7; }

/* ── Seuils ── */
.seuils-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
.seuil-card  { border-radius: 8px; padding: 1.25rem; border: 1px solid #e2e8f0; }
.seuil-card-faible { background: var(--color-risk-low-bg, #f0fdf4); border-color: var(--color-risk-low, #16a34a); }
.seuil-card-moyen  { background: var(--color-risk-medium-bg, #fef9c3); border-color: var(--color-risk-medium, #d97706); }
.seuil-card-eleve  { background: var(--color-risk-high-bg, #fee2e2); border-color: var(--color-risk-high, #dc2626); }
.seuil-card-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.seuil-icon   { font-size: 1.25rem; }
.seuil-label  { font-size: 0.9375rem; font-weight: 700; color: var(--color-text-primary); }
.seuil-range  { font-size: 1.1rem; font-weight: 800; color: var(--color-text-primary); margin-bottom: 0.5rem; }
.seuil-desc   { font-size: 0.8125rem; color: var(--color-text-secondary); line-height: 1.5; margin-bottom: 0.75rem; }
.seuil-locked { font-size: 0.75rem; font-weight: 600; color: #64748b; background: rgba(0,0,0,0.05); border-radius: 4px; padding: 0.2rem 0.5rem; display: inline-block; }

/* ── Axes grid ── */
.axes-grid   { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; margin-top: 1rem; }
.axe-card    { background: #f8fafc; border-radius: 6px; padding: 0.75rem 1rem; }
.axe-card-code  { font-size: 0.75rem; font-weight: 700; color: var(--color-sidebar-bg); margin-bottom: 0.15rem; text-transform: uppercase; letter-spacing: 0.04em; }
.axe-card-label { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); margin-bottom: 0.25rem; }
.axe-card-desc  { font-size: 0.75rem; color: var(--color-text-secondary); line-height: 1.5; }

/* ── Seuils note ── */
.seuils-note { margin-top: 1.5rem; font-size: 0.875rem; color: var(--color-text-secondary); }
.seuils-link { color: var(--color-sidebar-bg); font-weight: 600; }
.seuils-link:hover { text-decoration: underline; }

/* ── Triggers T1-T6 ── */
.triggers-panel { }
.trigger-list { display: flex; flex-direction: column; gap: 0.875rem; margin-top: 1rem; }
.trigger-card {
  border-radius: 8px; padding: 1rem 1.25rem;
  border-left: 4px solid transparent;
  background: var(--color-bg-page);
  display: flex; flex-direction: column; gap: 0.375rem;
}
.trigger--eleve   { border-left-color: var(--color-risk-high, #dc2626); }
.trigger--critique{ border-left-color: #7c0000; background: #fff1f1; }
.trigger--moyen   { border-left-color: var(--color-risk-medium, #d97706); }
.trigger-header { display: flex; align-items: center; gap: 0.625rem; flex-wrap: wrap; }
.trigger-code {
  font-family: monospace; font-weight: 800; font-size: 0.875rem;
  background: var(--color-sidebar-bg); color: #fff;
  border-radius: 4px; padding: 1px 8px;
}
.trigger-label { font-size: 0.9375rem; font-weight: 700; color: var(--color-text-primary); flex: 1; }
.trigger-niveau { font-size: 0.6875rem; font-weight: 700; border-radius: 10px; padding: 2px 8px; }
.trigger-niveau--eleve   { background: var(--color-risk-high-bg, #fee2e2); color: var(--color-risk-high, #dc2626); }
.trigger-niveau--critique{ background: #fecaca; color: #7c0000; }
.trigger-niveau--moyen   { background: var(--color-risk-medium-bg, #fef9c3); color: var(--color-risk-medium, #d97706); }
.trigger-desc { font-size: 0.8125rem; color: var(--color-text-secondary); line-height: 1.5; }
.trigger-consequence { font-size: 0.8125rem; color: var(--color-text-primary); line-height: 1.5; }
.trigger-ref { font-size: 0.75rem; color: var(--color-text-muted); font-style: italic; margin-top: 0.125rem; }

@media (max-width: 900px) {
  .risk-cards-row { grid-template-columns: 1fr; }
  .sim-layout     { grid-template-columns: 1fr; }
  .seuils-grid    { grid-template-columns: 1fr; }
  .axes-grid      { grid-template-columns: 1fr; }
}
</style>
