<template>
  <div class="kyc-detail-page">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <button class="breadcrumb-link" @click="router.push({ name: 'kyc-list' })">Dossiers KYC</button>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="breadcrumb-sep"><polyline points="9 18 15 12 9 6"/></svg>
          <span v-if="dossier">{{ dossier.reference }}</span>
        </div>
        <h1 class="page-title" v-if="dossier">
          {{ dossier.type_client === 'PP' ? clientName : dossier.kyc_pm?.denomination_sociale ?? dossier.reference }}
        </h1>
      </div>
      <div class="header-actions" v-if="dossier">
        <button class="btn-back" @click="router.push({ name: 'kyc-list' })">
          <svg class="btn-back-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          Retour
        </button>
        <span class="header-sep" />
        <span class="statut-badge" :class="`statut--${dossier.statut}`">
          {{ STATUT_LABELS[dossier.statut] ?? dossier.statut }}
        </span>
        <span v-if="dossier.classification" class="risk-badge" :class="`risk--${dossier.classification}`">
          {{ dossier.classification }}
        </span>
        <button
          v-if="dossier.statut === 'brouillon'"
          class="btn-submit-analyse"
          :disabled="submittingAnalyse"
          @click="submitForAnalyse"
        >
          <svg v-if="submittingAnalyse" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
          <svg v-else class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22 11 13 2 9l20-7z"/></svg>
          {{ submittingAnalyse ? 'Envoi…' : 'Soumettre pour analyse' }}
        </button>
        <button
          v-if="canAssign"
          class="btn-assign"
          @click="openAssignModal"
        >
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
          Assigner
        </button>
        <button
          v-if="canCreateDos"
          class="btn-dos"
          @click="router.push({ name: 'dos', query: { dossier_id: dossier.id, action: 'create' } })"
        >
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
          Créer une DOS
        </button>
      </div>
    </div>
    <div v-if="analyseError" class="analyse-error-banner">{{ analyseError }}</div>

    <div v-if="loading" class="card loading-card">Chargement…</div>
    <div v-else-if="error" class="card error-card">{{ error }}</div>

    <template v-else-if="dossier">
      <!-- Modal d'assignation -->
      <Teleport to="body">
        <div v-if="assignModal.open" class="modal-overlay" @click.self="assignModal.open = false">
          <div class="modal-dialog">
            <h3 class="modal-title">Assigner le dossier</h3>
            <p class="modal-subtitle">Dossier <span class="mono">{{ dossier.reference }}</span></p>
            <div v-if="assignModal.loading" class="assign-loading">Chargement des agents…</div>
            <div v-else>
              <label class="modal-label">Sélectionner un responsable <span class="required-star">*</span></label>
              <select v-model="assignModal.selectedId" class="field-input" style="width:100%;margin-bottom:0.75rem;">
                <option value="">— Choisir un responsable —</option>
                <option v-for="u in assignModal.users" :key="u.id" :value="u.id">
                  {{ u.full_name }} ({{ ROLE_LABELS[u.role] ?? u.role }})
                </option>
              </select>
              <p v-if="assignModal.error" class="modal-error">{{ assignModal.error }}</p>
              <div class="modal-actions">
                <button class="btn-ghost" @click="assignModal.open = false">Annuler</button>
                <button
                  class="btn-transition-confirm btn-transition-confirm--primary"
                  :disabled="assignModal.saving || !assignModal.selectedId"
                  @click="confirmAssign"
                >
                  <svg v-if="assignModal.saving" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                  {{ assignModal.saving ? '…' : 'Confirmer l\'assignation' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Modal de transition -->
      <Teleport to="body">
        <div v-if="transitionModal.open" class="modal-overlay" @click.self="transitionModal.open = false">
          <div class="modal-dialog">
            <h3 class="modal-title">{{ transitionModal.label }}</h3>
            <p class="modal-subtitle">Dossier <span class="mono">{{ dossier.reference }}</span></p>
            <div v-if="transitionModal.wrk09Warning" class="modal-wrk09-warn">
              ⚠ Trigger {{ dossier.trigger_actif }} actif — seul le Notaire Principal peut valider ce dossier (WRK-09).
            </div>
            <label class="modal-label">Motif / commentaire <span class="required-star">*</span></label>
            <textarea
              v-model="transitionModal.commentaire"
              class="field-textarea"
              rows="3"
              placeholder="Décrivez le motif de cette transition…"
            />
            <p v-if="transitionModal.error" class="modal-error">{{ transitionModal.error }}</p>
            <div class="modal-actions">
              <button class="btn-ghost" @click="transitionModal.open = false">Annuler</button>
              <button
                class="btn-transition-confirm"
                :class="`btn-transition-confirm--${transitionModal.color}`"
                :disabled="transitionModal.loading || !transitionModal.commentaire.trim()"
                @click="confirmTransition"
              >
                <svg v-if="transitionModal.loading" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                {{ transitionModal.loading ? '…' : 'Confirmer' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Trigger banners — alignés sur les 6 triggers absolutoires backend (T1-T6) -->
      <TriggerBanner v-if="dossier.trigger_actif === 'T1'" />
      <TriggerBanner
        v-else-if="dossier.trigger_actif === 'T2'"
        trigger="T2"
        description="Paiement en espèces supérieur au seuil réglementaire (> 15M FCFA) détecté — opération à risque élevé de blanchiment."
      />
      <TriggerBanner
        v-else-if="dossier.trigger_actif === 'T3'"
        trigger="T3"
        description="Client figurant sur une liste de sanctions (OFAC / UE-CSNU / GIABA-BCEAO) — blocage du dossier, DOS obligatoire."
      />
      <TriggerBanner
        v-else-if="dossier.trigger_actif === 'T4'"
        trigger="T4"
        description="Pays sur liste grise/noire GAFI détecté dans les données KYC — vigilance renforcée obligatoire (FATF Rec. 19/21)."
      />
      <TriggerBanner
        v-else-if="dossier.trigger_actif === 'T5'"
        trigger="T5"
        description="Refus documentaire ou documents incohérents — dossier mis en attente, signalement interne au Responsable Conformité."
      />
      <TriggerBanner
        v-else-if="dossier.trigger_actif === 'T6'"
        trigger="T6"
        description="Bénéficiaire effectif (≥ 25%) non identifiable — vigilance renforcée, poursuite conditionnée à son identification."
      />

      <!-- Triggers actifs sur le dossier (plusieurs possibles) -->
      <div v-if="triggersActifs.length" class="triggers-actifs-row">
        <span class="triggers-actifs-label">
          <svg class="triggers-actifs-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
          Triggers actifs
        </span>
        <span
          v-for="t in triggersActifs"
          :key="t"
          class="trigger-chip"
          :class="{ 'trigger-chip--ppe': t === 'T1' }"
          :title="t === 'T1' ? 'PPE — autorisation Notaire Principal obligatoire (WRK-09)' : 'Trigger réglementaire actif sur ce dossier'"
        >{{ t }}{{ t === 'T1' ? ' · PPE' : '' }}</span>
      </div>

      <!-- Alertes liées au dossier -->
      <div v-if="dossierAlertes.length" class="card alertes-liees-card">
        <button class="alertes-liees-header alertes-liees-toggle" @click="alertesCollapsed = !alertesCollapsed">
          <span class="alertes-toggle-left">
            <svg class="alertes-chevron" :class="{ 'alertes-chevron--open': !alertesCollapsed }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            <h3 class="section-title" style="margin:0">Alertes liées ({{ dossierAlertes.length }})</h3>
          </span>
          <span v-if="alertesOuvertesCritiques > 0" class="alertes-warn-badge">
            ⚠ {{ alertesOuvertesCritiques }} alerte(s) ÉLEVÉ non traitée(s) — validation bloquée
          </span>
        </button>
        <template v-if="!alertesCollapsed">
          <ul class="alertes-liees-list">
            <li v-for="a in dossierAlertes" :key="a.id" class="alerte-liee-item">
              <span class="alerte-liee-niveau" :class="`niv-${a.niveau.toLowerCase()}`">{{ a.niveau }}</span>
              <span class="alerte-liee-type">{{ a.type_alerte }}</span>
              <span class="alerte-liee-statut" :class="`st-${a.statut.toLowerCase()}`">
                {{ a.statut === 'traitee' ? 'Traitée' : (a.statut === 'en_cours' ? 'En cours' : (a.statut === 'ignoree' ? 'Ignorée' : 'Ouverte')) }}
              </span>
              <span class="alerte-liee-desc">{{ a.description }}</span>
            </li>
          </ul>
          <p class="alertes-liees-hint">Le traitement des alertes se fait dans le module <strong>Alertes</strong>.</p>
        </template>
      </div>

      <!-- Panneau de transitions -->
      <div v-if="(availableTransitions.length || isRC) && canModify" class="transition-bar">
        <span class="transition-bar-label">Actions :</span>
        <button
          v-for="t in availableTransitions"
          :key="t.to"
          class="btn-transition"
          :class="`btn-transition--${t.color}`"
          @click="openTransitionModal(t)"
        >{{ t.label }}</button>
        <template v-if="isRC && !['T5','T6'].includes(dossier.trigger_actif ?? '')">
          <span class="transition-sep" />
          <button class="btn-trigger-manual" @click="openTriggerModal('T5')">⚑ Trigger T5</button>
          <button class="btn-trigger-manual" @click="openTriggerModal('T6')">⚑ Trigger T6</button>
        </template>
      </div>

      <!-- Modal T5/T6 -->
      <Teleport to="body">
        <div v-if="triggerModal.open" class="modal-overlay" @click.self="triggerModal.open = false">
          <div class="modal-dialog">
            <h3 class="modal-title">Déclenchement manuel — Trigger {{ triggerModal.trigger }}</h3>
            <p class="modal-subtitle">
              <span v-if="triggerModal.trigger === 'T5'">T5 — Refus documentaire explicite du client</span>
              <span v-else>T6 — Bénéficiaire effectif non identifiable</span>
            </p>
            <label class="modal-label">Motif <span class="required-star">*</span></label>
            <textarea v-model="triggerModal.commentaire" class="field-textarea" rows="3" placeholder="Décrivez le motif…" />
            <p v-if="triggerModal.error" class="modal-error">{{ triggerModal.error }}</p>
            <div class="modal-actions">
              <button class="btn-ghost" @click="triggerModal.open = false">Annuler</button>
              <button
                class="btn-transition-confirm btn-transition-confirm--danger"
                :disabled="triggerModal.loading || !triggerModal.commentaire.trim()"
                @click="confirmTriggerManuel"
              >
                <svg v-if="triggerModal.loading" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                {{ triggerModal.loading ? '…' : 'Déclencher' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Meta strip -->
      <div class="meta-strip card">
        <div class="meta-item">
          <span class="meta-label">Référence</span>
          <span class="meta-value mono">{{ dossier.reference }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Type client</span>
          <span class="meta-value">{{ dossier.type_client === 'PP' ? 'Personne physique' : 'Personne morale' }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Opération</span>
          <span class="meta-value">{{ operationLabel(dossier.type_operation) }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Transaction</span>
          <span class="meta-value">
            <template v-if="dossier.montant_transaction != null || dossier.montant_tranche || dossier.mode_paiement">
              {{ dossier.montant_transaction != null ? Number(dossier.montant_transaction).toLocaleString('fr-FR') + ' FCFA' : (dossier.montant_tranche === 'plus_15m' ? '> 15M FCFA' : '< 15M FCFA') }}
              <span v-if="dossier.mode_paiement"> · {{ MODE_PAIEMENT_LABELS[dossier.mode_paiement] ?? dossier.mode_paiement }}</span>
            </template>
            <span v-else style="color:var(--color-text-muted);font-style:italic">Non renseignée</span>
          </span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Score risque</span>
          <template v-if="dossier.score_base !== null && dossier.score_base !== undefined">
            <span class="meta-value">
              <span class="score-pill" :class="`score-pill--${(dossier.classification ?? 'FAIBLE').toLowerCase()}`">
                <template v-if="!isAgent">{{ dossier.score_base }}/20 — </template>{{ dossier.classification }}
              </span>
            </span>
          </template>
          <template v-else>
            <button v-if="!isAgent" class="score-empty-btn" @click="activeSection = 'scoring'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Calculer
            </button>
            <span v-else class="meta-value" style="color:var(--color-text-muted);font-style:italic">Non calculé</span>
          </template>
        </div>
        <div class="meta-item">
          <span class="meta-label">Assigné à</span>
          <span class="meta-value">
            <span v-if="dossier.assigned_to" class="assigned-chip">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="assigned-icon"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
              {{ dossier.assigned_to_name || assignedUserName || dossier.assigned_to.slice(0, 8) + '…' }}
            </span>
            <span v-else class="meta-value" style="color:var(--color-text-muted);font-style:italic">Non assigné</span>
          </span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Créé le</span>
          <span class="meta-value">{{ dossier.created_at ? formatDate(dossier.created_at) : '—' }}</span>
        </div>
      </div>

      <!-- Verrou édition : dossier assigné à un autre utilisateur → lecture seule -->
      <div v-if="dossier && !canModify" class="readonly-banner">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="readonly-icon"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        <span>Lecture seule — ce dossier est assigné à un autre utilisateur. Vous pouvez le consulter mais pas le modifier.</span>
      </div>

      <!-- Déclaration systématique espèces (> 15M réglé en espèces) -->
      <div v-if="dossier.surveillance_espece" class="surveillance-espece-banner">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        <span>Déclaration systématique de transaction en espèce à faire. Opération à surveiller.</span>
      </div>

      <!-- ── Onglets de navigation plats ── -->
      <div class="tabs-nav">
        <button
          v-for="tab in visibleTabs"
          :key="tab.id"
          class="tabs-nav-item"
          :class="{ 'tabs-nav-item--active': activeSection === tab.id }"
          @click="activeSection = tab.id"
        >{{ tab.label }}</button>
      </div>

      <!-- ── KYC-PP ── -->
      <div v-if="activeSection === 'kyc-pp'" class="card section-card">
        <template v-if="dossier.kyc_pp">
          <div class="section-header">
            <h3 class="section-title">Fiche KYC — Personne physique</h3>
            <div v-if="!ppEdit && canModify" style="display:flex;gap:0.5rem">
              <button class="btn-ghost btn-sm" @click="startPpEdit">Modifier</button>
            </div>
            <div v-else-if="ppEdit" style="display:flex;gap:0.5rem;align-items:center">
              <button class="btn-ghost btn-sm" @click="ppEdit=false;ppError=''">Annuler</button>
              <button class="btn-primary btn-sm-primary" :disabled="ppSaving" @click="savePp">
                <svg v-if="ppSaving" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                {{ ppSaving ? '…' : 'Enregistrer' }}
              </button>
            </div>
          </div>
          <p v-if="ppError" class="save-error">{{ ppError }}</p>

          <!-- View mode -->
          <template v-if="!ppEdit">
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Nom & Prénoms</span><span class="info-value">{{ clientName }}</span></div>
              <div class="info-item"><span class="info-label">Nom de jeune fille</span><span class="info-value">{{ dossier.kyc_pp.nom_jeune_fille ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Nom & Prénoms du père</span><span class="info-value">{{ dossier.kyc_pp.nom_prenoms_pere ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Nom & Prénoms de la mère</span><span class="info-value">{{ dossier.kyc_pp.nom_prenoms_mere ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Date de naissance</span><span class="info-value">{{ dossier.kyc_pp.date_naissance ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Lieu de naissance</span><span class="info-value">{{ dossier.kyc_pp.lieu_naissance ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Nationalité</span><span class="info-value">{{ dossier.kyc_pp.nationalite ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Autres nationalités</span><span class="info-value">{{ dossier.kyc_pp.autres_nationalites ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Statut matrimonial</span><span class="info-value">{{ dossier.kyc_pp.statut_matrimonial ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Pièce d'identité</span><span class="info-value">{{ dossier.kyc_pp.type_piece ?? '—' }} {{ dossier.kyc_pp.numero_piece ?? '' }}</span></div>
              <div class="info-item"><span class="info-label">N° Compte Contribuable</span><span class="info-value mono">{{ dossier.kyc_pp.numero_contribuable ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Profession</span><span class="info-value">{{ dossier.kyc_pp.profession ?? '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Professions (5 dernières années)</span><span class="info-value">{{ dossier.kyc_pp.profession_5_ans ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Employeur</span><span class="info-value">{{ dossier.kyc_pp.employeur ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Secteur d'activité</span><span class="info-value">{{ dossier.kyc_pp.secteur_activite ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Ancienneté professionnelle</span><span class="info-value">{{ dossier.kyc_pp.anciennete_pro ?? '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Adresse géographique</span><span class="info-value">{{ dossier.kyc_pp.adresse_geo ?? '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Adresse postale</span><span class="info-value">{{ dossier.kyc_pp.adresse_postale ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Téléphone</span><span class="info-value">{{ dossier.kyc_pp.telephone ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">WhatsApp</span><span class="info-value">{{ dossier.kyc_pp.whatsapp ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Email</span><span class="info-value">{{ dossier.kyc_pp.email ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Non résident</span><span class="info-value">{{ dossier.kyc_pp.non_resident ? 'Oui' : 'Non' }}{{ dossier.kyc_pp.non_resident && dossier.kyc_pp.pays_residence ? ' — ' + dossier.kyc_pp.pays_residence : '' }}</span></div>
              <div class="info-item"><span class="info-label">Statut PPE</span><span class="info-value" :class="{ 'ppe-flag': dossier.kyc_pp.est_ppe }">{{ dossier.kyc_pp.est_ppe ? '⚠ PPE' : 'Non' }}</span></div>
            </div>

            <template v-if="dossier.kyc_pp.mandataire">
              <h4 class="subsection-title">Mandataire</h4>
              <div class="mandant-detail-block">
                <div class="info-grid">
                  <div class="info-item"><span class="info-label">Prénom & Nom</span><span class="info-value">{{ dossier.kyc_pp.mandataire.prenom_nom || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Pièce d'identité</span><span class="info-value">{{ dossier.kyc_pp.mandataire.type_piece || '—' }} {{ dossier.kyc_pp.mandataire.numero_piece || '' }}</span></div>
                  <div class="info-item"><span class="info-label">Date de naissance</span><span class="info-value">{{ dossier.kyc_pp.mandataire.date_naissance || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Nationalité</span><span class="info-value">{{ dossier.kyc_pp.mandataire.nationalite || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Pays de résidence</span><span class="info-value">{{ dossier.kyc_pp.mandataire.pays_residence || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Fonction</span><span class="info-value">{{ dossier.kyc_pp.mandataire.fonction || '—' }}</span></div>
                </div>
              </div>
            </template>

            <!-- Déclaration PPE (CDC : la fiche PP ne comporte pas de table BE) -->
            <div class="be-separator">
              <h4 class="subsection-title">Personnes Politiquement Exposées (PPE)</h4>
            </div>
            <KycPPEPanel :dossier-id="dossier.id" client-type="PP" />
          </template>

          <!-- Edit mode -->
          <template v-else>
            <div class="edit-grid">
              <div class="edit-field"><label class="info-label">Nom <span class="req">*</span></label><input v-model="ppForm.nom" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Prénoms <span class="req">*</span></label><input v-model="ppForm.prenoms" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Nom de jeune fille</label><input v-model="ppForm.nom_jeune_fille" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Nom & Prénoms du père</label><input v-model="ppForm.nom_prenoms_pere" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Nom & Prénoms de la mère</label><input v-model="ppForm.nom_prenoms_mere" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Date de naissance</label><input v-model="ppForm.date_naissance" type="date" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Lieu de naissance</label><input v-model="ppForm.lieu_naissance" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Nationalité</label><input v-model="ppForm.nationalite" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Autres nationalités</label><input v-model="ppForm.autres_nationalites" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Statut matrimonial</label><input v-model="ppForm.statut_matrimonial" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Type de pièce</label><input v-model="ppForm.type_piece" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Numéro de pièce</label><input v-model="ppForm.numero_piece" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">N° Compte Contribuable</label><input v-model="ppForm.numero_contribuable" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Profession</label><input v-model="ppForm.profession" type="text" class="field-input" /></div>
              <div class="edit-field edit-field--full"><label class="info-label">Professions (5 dernières années)</label><input v-model="ppForm.profession_5_ans" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Employeur</label><input v-model="ppForm.employeur" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Secteur d'activité</label><input v-model="ppForm.secteur_activite" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Ancienneté professionnelle</label><input v-model="ppForm.anciennete_pro" type="text" class="field-input" /></div>
              <div class="edit-field edit-field--full"><label class="info-label">Adresse géographique</label><input v-model="ppForm.adresse_geo" type="text" class="field-input" /></div>
              <div class="edit-field edit-field--full"><label class="info-label">Adresse postale</label><input v-model="ppForm.adresse_postale" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Téléphone</label><input v-model="ppForm.telephone" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">WhatsApp</label><input v-model="ppForm.whatsapp" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Email</label><input v-model="ppForm.email" type="email" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Pays de résidence</label><input v-model="ppForm.pays_residence" type="text" class="field-input" /></div>
              <div class="edit-field" style="display:flex;align-items:center;gap:0.5rem;padding-top:1.25rem">
                <input id="pp-non-resident" v-model="ppForm.non_resident" type="checkbox" class="checkbox" />
                <label for="pp-non-resident" class="info-label" style="margin:0;cursor:pointer">Non résident</label>
              </div>
              <div class="edit-field" style="display:flex;align-items:center;gap:0.5rem;padding-top:1.25rem">
                <input id="pp-est-ppe" v-model="ppForm.est_ppe" type="checkbox" class="checkbox" />
                <label for="pp-est-ppe" class="info-label" style="margin:0;cursor:pointer">Statut PPE</label>
              </div>
            </div>
          </template>
        </template>
        <div v-else class="empty-section">
          <p>Le formulaire KYC-PP n'a pas encore été rempli.</p>
          <button v-if="dossier.statut === 'brouillon'" class="btn-primary btn-sm-primary" style="margin-top:1rem" @click="router.push({ name: 'kyc-pp', params: { id: dossier.id } })">
            Remplir le formulaire KYC
          </button>
        </div>
      </div>

      <!-- ── KYC-PM — Informations société ── -->
      <div v-else-if="activeSection === 'kyc-pm'" class="card section-card">
        <template v-if="dossier.kyc_pm">
          <div class="section-header">
            <h3 class="section-title">Informations société</h3>
            <div v-if="!pmEdit && canModify" style="display:flex;gap:0.5rem">
              <button class="btn-ghost btn-sm" @click="startPmEdit">Modifier</button>
            </div>
            <div v-else-if="pmEdit" style="display:flex;gap:0.5rem;align-items:center">
              <button class="btn-ghost btn-sm" @click="pmEdit=false;pmError=''">Annuler</button>
              <button class="btn-primary btn-sm-primary" :disabled="pmSaving" @click="savePm">
                <svg v-if="pmSaving" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                {{ pmSaving ? '…' : 'Enregistrer' }}
              </button>
            </div>
          </div>
          <p v-if="pmError" class="save-error">{{ pmError }}</p>

          <!-- View mode -->
          <template v-if="!pmEdit">
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Dénomination sociale</span><span class="info-value">{{ dossier.kyc_pm.denomination_sociale ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Forme juridique</span><span class="info-value">{{ dossier.kyc_pm.forme_juridique ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">N° RCCM</span><span class="info-value mono">{{ dossier.kyc_pm.numero_rccm ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">N° Compte Contribuable</span><span class="info-value mono">{{ dossier.kyc_pm.numero_contribuable ?? '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Libellé d'activité</span><span class="info-value">{{ dossier.kyc_pm.libelle_activite ?? '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Adresse</span><span class="info-value">{{ dossier.kyc_pm.adresse ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Téléphone</span><span class="info-value">{{ dossier.kyc_pm.telephone ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">WhatsApp</span><span class="info-value">{{ dossier.kyc_pm.whatsapp ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Email</span><span class="info-value">{{ dossier.kyc_pm.email ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Représentant légal</span><span class="info-value">{{ dossier.kyc_pm.nom_representant_legal ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Ancienneté professionnelle</span><span class="info-value">{{ dossier.kyc_pm.anciennete_pro ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">PPE détectée</span><span class="info-value" :class="{ 'ppe-flag': dossier.kyc_pm.ppe_detectee }">{{ dossier.kyc_pm.ppe_detectee ? '⚠ Oui' : 'Non' }}</span></div>
              <template v-if="dossier.kyc_pm.infos_pm">
                <div class="info-item"><span class="info-label">Domaine d'activité</span><span class="info-value">{{ dossier.kyc_pm.infos_pm.domaine_activite || '—' }}</span></div>
                <div class="info-item"><span class="info-label">Nature de la PM</span><span class="info-value">{{ dossier.kyc_pm.infos_pm.nature_pm || '—' }}</span></div>
                <div class="info-item"><span class="info-label">Société cotée</span><span class="info-value">{{ dossier.kyc_pm.infos_pm.cotee ? 'Oui' : 'Non' }}</span></div>
                <div class="info-item"><span class="info-label">Marché réglementé</span><span class="info-value">{{ dossier.kyc_pm.infos_pm.marche_reglemente || '—' }}</span></div>
              </template>
            </div>

            <template v-if="dossier.kyc_pm.mandataire">
              <h4 class="subsection-title">Mandataire</h4>
              <div class="mandant-detail-block">
                <div class="info-grid">
                  <div class="info-item"><span class="info-label">Prénom & Nom</span><span class="info-value">{{ dossier.kyc_pm.mandataire.prenom_nom || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Pièce d'identité</span><span class="info-value">{{ dossier.kyc_pm.mandataire.type_piece || '—' }} {{ dossier.kyc_pm.mandataire.numero_piece || '' }}</span></div>
                  <div class="info-item"><span class="info-label">Date de naissance</span><span class="info-value">{{ dossier.kyc_pm.mandataire.date_naissance || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Nationalité</span><span class="info-value">{{ dossier.kyc_pm.mandataire.nationalite || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Pays de résidence</span><span class="info-value">{{ dossier.kyc_pm.mandataire.pays_residence || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Fonction</span><span class="info-value">{{ dossier.kyc_pm.mandataire.fonction || '—' }}</span></div>
                </div>
              </div>
            </template>

            <!-- Déclarations PPE (ajout direct depuis la fiche) -->
            <div class="be-separator">
              <h4 class="subsection-title">Personnes Politiquement Exposées (PPE)</h4>
            </div>
            <KycPPEPanel :dossier-id="dossier.id" client-type="PM" />
          </template>

          <!-- Edit mode -->
          <template v-else>
            <div class="edit-grid">
              <div class="edit-field edit-field--full"><label class="info-label">Dénomination sociale <span class="req">*</span></label><input v-model="pmForm.denomination_sociale" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Forme juridique</label><input v-model="pmForm.forme_juridique" type="text" class="field-input" placeholder="SA, SARL, SAS…" /></div>
              <div class="edit-field"><label class="info-label">N° RCCM</label><input v-model="pmForm.numero_rccm" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">N° Compte Contribuable</label><input v-model="pmForm.numero_contribuable" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Représentant légal</label><input v-model="pmForm.nom_representant_legal" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Ancienneté professionnelle</label><input v-model="pmForm.anciennete_pro" type="text" class="field-input" /></div>
              <div class="edit-field edit-field--full"><label class="info-label">Libellé d'activité</label><input v-model="pmForm.libelle_activite" type="text" class="field-input" /></div>
              <div class="edit-field edit-field--full"><label class="info-label">Adresse</label><textarea v-model="pmForm.adresse" class="field-textarea" rows="2" /></div>
              <div class="edit-field"><label class="info-label">Téléphone</label><input v-model="pmForm.telephone" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">WhatsApp</label><input v-model="pmForm.whatsapp" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Email</label><input v-model="pmForm.email" type="email" class="field-input" /></div>
              <div class="edit-field" style="display:flex;align-items:center;gap:0.5rem;padding-top:1.25rem">
                <input id="pm-ppe-detectee" v-model="pmForm.ppe_detectee" type="checkbox" class="checkbox" />
                <label for="pm-ppe-detectee" class="info-label" style="margin:0;cursor:pointer">PPE détectée</label>
              </div>
            </div>
            <h4 class="subsection-title">Informations complémentaires PM</h4>
            <div class="edit-grid">
              <div class="edit-field"><label class="info-label">Domaine d'activité</label><input v-model="pmForm.infos_pm.domaine_activite" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Nature de la PM</label><input v-model="pmForm.infos_pm.nature_pm" type="text" class="field-input" /></div>
              <div class="edit-field"><label class="info-label">Marché réglementé</label><input v-model="pmForm.infos_pm.marche_reglemente" type="text" class="field-input" /></div>
              <div class="edit-field" style="display:flex;align-items:center;gap:0.5rem;padding-top:1.25rem">
                <input id="pm-cotee" v-model="pmForm.infos_pm.cotee" type="checkbox" class="checkbox" />
                <label for="pm-cotee" class="info-label" style="margin:0;cursor:pointer">Société cotée</label>
              </div>
            </div>
          </template>
        </template>
        <div v-else class="empty-section">
          <p>Le formulaire KYC-PM n'a pas encore été rempli.</p>
          <button v-if="dossier.statut === 'brouillon'" class="btn-primary btn-sm-primary" style="margin-top:1rem" @click="router.push({ name: 'kyc-pm', params: { id: dossier.id } })">
            Remplir le formulaire KYC
          </button>
        </div>
      </div>

      <!-- ── Représentant légal ── -->
      <div v-else-if="activeSection === 'representant'" class="card section-card">
        <template v-if="dossier.kyc_pm">
          <div class="section-header">
            <h3 class="section-title">Représentant légal</h3>
            <button class="btn-ghost btn-sm" @click="router.push({ name: 'kyc-pm', params: { id: dossier.id } })">Modifier</button>
          </div>

          <div v-if="!dossier.kyc_pm.nom_representant_legal && !dossier.kyc_pm.mandataire" class="empty-section" style="padding:1.5rem 0">
            <p>Aucun représentant légal renseigné.</p>
            <button class="btn-ghost btn-sm" style="margin-top:0.5rem" @click="router.push({ name: 'kyc-pm', params: { id: dossier.id } })">Renseigner</button>
          </div>
          <template v-else>
            <div class="info-grid">
              <div class="info-item info-item--full"><span class="info-label">Nom du représentant légal</span><span class="info-value">{{ dossier.kyc_pm.nom_representant_legal ?? '—' }}</span></div>
            </div>
            <template v-if="dossier.kyc_pm.mandataire">
              <h4 class="subsection-title">Mandataire</h4>
              <div class="mandant-detail-block">
                <div class="info-grid">
                  <div class="info-item"><span class="info-label">Prénom & Nom</span><span class="info-value">{{ dossier.kyc_pm.mandataire.prenom_nom || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Pièce d'identité</span><span class="info-value">{{ dossier.kyc_pm.mandataire.type_piece || '—' }} {{ dossier.kyc_pm.mandataire.numero_piece || '' }}</span></div>
                  <div class="info-item"><span class="info-label">Date de naissance</span><span class="info-value">{{ dossier.kyc_pm.mandataire.date_naissance || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Nationalité</span><span class="info-value">{{ dossier.kyc_pm.mandataire.nationalite || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Pays de résidence</span><span class="info-value">{{ dossier.kyc_pm.mandataire.pays_residence || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Fonction</span><span class="info-value">{{ dossier.kyc_pm.mandataire.fonction || '—' }}</span></div>
                </div>
              </div>
            </template>
          </template>
        </template>
        <div v-else class="empty-section">
          <p>Le formulaire KYC-PM doit être rempli en premier.</p>
        </div>
      </div>

      <!-- ── Actionnaires / BEs ── -->
      <div v-else-if="activeSection === 'actionnaires-be'" class="card section-card">
        <!-- Actionnaires (kyc_pm.actionnaires) -->
        <div class="section-header">
          <h3 class="section-title">Actionnaires / Associés</h3>
          <button class="btn-ghost btn-sm" @click="router.push({ name: 'kyc-pm', params: { id: dossier.id } })">Modifier</button>
        </div>

        <div v-if="!dossier.kyc_pm?.actionnaires?.length" class="empty-section" style="padding:1rem 0">
          <p>Aucun actionnaire renseigné.</p>
        </div>
        <div v-else class="persons-list" style="margin-bottom:0.5rem">
          <div v-for="(a, i) in dossier.kyc_pm.actionnaires" :key="i" class="person-row">
            <div class="person-avatar">{{ String(a.raison_sociale_nom ?? '')[0]?.toUpperCase() }}</div>
            <div class="person-info">
              <span class="person-name">{{ a.raison_sociale_nom }}</span>
              <div class="person-tags">
                <span class="person-tag pct-tag">{{ a.pourcentage }}%</span>
                <span v-if="a.cni_passeport" class="person-nat">{{ a.cni_passeport }}</span>
                <span v-if="a.pays_residence" class="person-nat">{{ a.pays_residence }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- BEs formels (KycBEPanel) -->
        <div class="be-separator">
          <h4 class="subsection-title">Bénéficiaires effectifs — KYC-BE</h4>
        </div>
        <KycBEPanel :dossier-id="dossier.id" client-type="PM" />
      </div>

      <!-- ── KYC-PPE ── -->
      <div v-else-if="activeSection === 'kyc-ppe'" class="card section-card">
        <div class="section-header">
          <h3 class="section-title">Personnes Politiquement Exposées (PPE)</h3>
        </div>
        <KycPPEPanel :dossier-id="dossier.id" :client-type="dossier.type_client === 'PM' ? 'PM' : 'PP'" />
      </div>

      <!-- ── Transaction ── -->
      <div v-else-if="activeSection === 'transaction'" class="card section-card">
        <div class="section-header">
          <h3 class="section-title">Transaction</h3>
          <div v-if="!txEdit && canModify" style="display:flex;gap:0.5rem">
            <button class="btn-ghost btn-sm" @click="startTxEdit">Modifier</button>
          </div>
          <div v-else-if="txEdit" style="display:flex;gap:0.5rem;align-items:center">
            <button class="btn-ghost btn-sm" @click="txEdit=false;txError=''">Annuler</button>
            <button class="btn-primary btn-sm-primary" :disabled="txSaving" @click="saveTransaction">
              <svg v-if="txSaving" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
              {{ txSaving ? '…' : 'Enregistrer' }}
            </button>
          </div>
        </div>
        <p v-if="txError" class="save-error">{{ txError }}</p>

        <!-- View mode -->
        <template v-if="!txEdit">
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Tranche de montant</span>
              <span class="info-value">{{ dossier.montant_tranche ? (dossier.montant_tranche === 'plus_15m' ? '> 15M FCFA' : '< 15M FCFA') : '—' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Montant exact</span>
              <span class="info-value">{{ dossier.montant_transaction != null ? Number(dossier.montant_transaction).toLocaleString('fr-FR') + ' FCFA' : '—' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Mode de paiement</span>
              <span class="info-value">{{ dossier.mode_paiement ? (MODE_PAIEMENT_LABELS[dossier.mode_paiement] ?? dossier.mode_paiement) : '—' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Déclaration systématique espèces</span>
              <span class="info-value" :class="{ 'ppe-flag': dossier.surveillance_espece }">{{ dossier.surveillance_espece ? '⚠ À déclarer' : 'Non' }}</span>
            </div>
          </div>
          <div v-if="dossier.surveillance_espece" class="surveillance-espece-banner">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span>Déclaration systématique de transaction en espèce à faire. Opération à surveiller.</span>
          </div>
        </template>

        <!-- Edit mode -->
        <template v-else>
          <div class="edit-grid">
            <div class="edit-field">
              <label class="info-label">Tranche de montant</label>
              <select v-model="txForm.montant_tranche" class="field-input">
                <option value="">— Choisir —</option>
                <option value="moins_15m">Montant &lt; 15M FCFA</option>
                <option value="plus_15m">Montant &gt; 15M FCFA</option>
              </select>
            </div>
            <div class="edit-field">
              <label class="info-label">Montant exact (FCFA)</label>
              <input v-model.number="txForm.montant_transaction" type="number" min="0" class="field-input" placeholder="Ex : 25000000" />
            </div>
            <div class="edit-field">
              <label class="info-label">Mode de paiement</label>
              <select v-model="txForm.mode_paiement" class="field-input">
                <option value="">— Choisir —</option>
                <option value="especes">Espèces</option>
                <option value="cheque">Chèque</option>
                <option value="virement">Virement</option>
                <option value="mix">Mixte</option>
                <option value="paiement_tiers">Paiement via tiers</option>
                <option value="autre">Autre</option>
              </select>
            </div>
          </div>
          <div v-if="txSurveillanceEspece" class="surveillance-espece-banner">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span>Déclaration systématique de transaction en espèce à faire. Opération à surveiller.</span>
          </div>
        </template>
      </div>

      <!-- ── Scoring risque ── -->
      <div v-else-if="activeSection === 'scoring'" class="card section-card">
        <div class="section-header">
          <h3 class="section-title">Évaluation du risque — Matrice 10 axes</h3>
        </div>
        <ScoringPanel :dossier="dossier" @scored="onScored" />
      </div>

      <!-- ── Documents ── -->
      <div v-else-if="activeSection === 'documents'" class="card section-card">
        <DocumentsPanel :dossier="dossier" />
      </div>

      <!-- ── Historique & Commentaires ── -->
      <div v-else-if="activeSection === 'historique'" class="card section-card">
        <div class="section-header">
          <h3 class="section-title">Historique & Commentaires internes</h3>
        </div>

        <h4 class="subsection-title">Historique du cycle de vie</h4>
        <div v-if="historiqueLoading" class="loading-inline">Chargement…</div>
        <div v-else-if="historique.length === 0" class="empty-section">
          <p>Aucun changement d'état enregistré.</p>
        </div>
        <div v-else class="historique-list">
          <div v-for="h in historique" :key="h.id" class="historique-row">
            <div class="historique-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M4 12h4m8 0h4"/></svg>
            </div>
            <div class="historique-body">
              <p class="historique-transition">
                <span class="statut-chip statut-chip--next">{{ h.action }}</span>
              </p>
              <p class="historique-meta">{{ formatDate(h.created_at) }}<span v-if="h.user_id"> · {{ h.user_id }}</span></p>
            </div>
          </div>
        </div>

        <h4 class="subsection-title" style="margin-top:1.5rem;">Commentaires internes <span class="confidential-tag">Confidentiel</span></h4>
        <div v-if="commentairesLoading" class="loading-inline">Chargement…</div>
        <div v-else>
          <div v-if="commentaires.length === 0" class="empty-section">
            <p>Aucun commentaire interne.</p>
          </div>
          <div v-else class="commentaires-list">
            <div v-for="c in commentaires" :key="c.id" class="commentaire-row">
              <div class="commentaire-avatar">{{ c.auteur_id.slice(0, 2).toUpperCase() }}</div>
              <div class="commentaire-body">
                <p class="commentaire-contenu">{{ c.contenu }}</p>
                <p class="commentaire-meta">{{ formatDate(c.created_at) }}</p>
              </div>
            </div>
          </div>
          <div class="add-commentaire">
            <textarea
              v-model="newCommentaire"
              class="field-textarea"
              rows="3"
              placeholder="Ajouter un commentaire interne confidentiel…"
            />
            <button
              class="btn-primary btn-sm-primary"
              :disabled="!newCommentaire.trim() || commentaireSubmitting"
              @click="submitCommentaire"
            >
              <span v-if="commentaireSubmitting">…</span>
              <span v-else>Ajouter</span>
            </button>
          </div>
        </div>
      </div>

      <!-- ── DOS — Déclarations d'Opérations Suspectes ── -->
      <div v-else-if="activeSection === 'dos'" class="card section-card">
        <div class="section-header">
          <h3 class="section-title">Déclarations d'Opérations Suspectes (DOS)</h3>
          <button
            v-if="canCreateDos"
            class="btn-dos btn-sm-dos"
            @click="router.push({ name: 'dos', query: { dossier_id: dossier.id, action: 'create' } })"
          >
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Nouvelle DOS
          </button>
        </div>

        <div v-if="dosLoading" class="loading-inline">Chargement…</div>
        <div v-else-if="dosList.length === 0" class="empty-section">
          <p>Aucune Déclaration d'Opération Suspecte enregistrée pour ce dossier.</p>
          <button v-if="canCreateDos" class="btn-dos btn-sm-dos" style="margin-top:1rem" @click="router.push({ name: 'dos', query: { dossier_id: dossier.id, action: 'create' } })">
            Créer une DOS
          </button>
        </div>
        <div v-else class="dos-list">
          <div v-for="dos in dosList" :key="dos.id" class="dos-row">
            <div class="dos-row-left">
              <div class="dos-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              </div>
              <div>
                <p class="dos-ref">{{ dos.reference_interne }}</p>
                <p class="dos-meta">
                  Créée le {{ formatDate(dos.created_at) }}
                  <span v-if="dos.date_transmission_centif"> · Transmise le {{ formatDate(dos.date_transmission_centif) }}</span>
                </p>
              </div>
            </div>
            <div class="dos-row-right">
              <span class="dos-statut" :class="dosStatutCategory(dos.statut)">
                {{ dosStatutLabel(dos.statut) }}
              </span>
              <button class="btn-ghost btn-sm" @click="router.push({ name: 'dos-detail', params: { id: dos.id } })">
                Ouvrir
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Fallback -->
      <div v-else class="card section-card">
        <p class="placeholder-text">Section non disponible.</p>
      </div>

    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ROLE_LABELS } from '@/utils/roles'
import KycBEPanel from '@/components/kyc/KycBEPanel.vue'
import KycPPEPanel from '@/components/kyc/KycPPEPanel.vue'
import DocumentsPanel from '@/components/kyc/DocumentsPanel.vue'
import ScoringPanel from '@/components/kyc/ScoringPanel.vue'
import TriggerBanner from '@/components/kyc/TriggerBanner.vue'
import { dossiersService, type DossierOut, type CommentaireOut, type HistoriqueOut, type StatutDossier, type KycPPData, type KycPMData, type TypeOperation, TYPE_OPERATION_LABELS } from '@/services/dossiers'
import { dosService, dosStatutLabel, type DosOut } from '@/services/dos'

// Catégorie visuelle du statut DOS (verrouillée = engagée dans le circuit CENTIF).
const DOS_LOCKED = ['en_validation', 'validee_rc', 'soumis', 'transmise', 'classee', 'accuse_recu']
function dosStatutCategory(statut: string): string {
  return `dos-statut--${DOS_LOCKED.includes(statut) ? 'finalisee' : 'brouillon'}`
}
import { useAuthStore } from '@/stores/auth'

const route  = useRoute()
const router = useRouter()
const auth   = useAuthStore()

const dossier = ref<DossierOut | null>(null)
const loading = ref(true)
const error   = ref('')
const activeSection = ref('')

const historique = ref<HistoriqueOut[]>([])
const historiqueLoading = ref(false)
const commentaires = ref<CommentaireOut[]>([])
const commentairesLoading = ref(false)
const newCommentaire = ref('')
const commentaireSubmitting = ref(false)

const OPERATION_LABELS = TYPE_OPERATION_LABELS

function operationLabel(op: string): string {
  return OPERATION_LABELS[op as TypeOperation] ?? op
}

const MODE_PAIEMENT_LABELS: Record<string, string> = {
  especes: 'Espèces', cheque: 'Chèque', virement: 'Virement',
  mix: 'Mixte', paiement_tiers: 'Paiement via tiers', autre: 'Autre',
}

const STATUT_LABELS: Record<string, string> = {
  brouillon:               'Brouillon',
  en_analyse:              'En analyse',
  vigilance_renforcee:     'Vigilance renforcée',
  valide:                  'Validé',
  actif:                   'Actif',
  actif_sous_surveillance: 'Sous surveillance',
  bloque:                  'Bloqué',
  traite:                  'Traité',
  resilie:                 'Résilié',
  cloture:                 'Clôturé',
  archive:                 'Archivé',
}

const clientName = computed(() => {
  const pp = dossier.value?.kyc_pp
  if (!pp) return dossier.value?.reference ?? '—'
  return `${pp.nom ?? ''} ${pp.prenoms ?? ''}`.trim()
})

const visibleTabs = computed(() => {
  if (!dossier.value) return []
  const tabs: { id: string; label: string }[] = []
  if (dossier.value.type_client === 'PP') {
    tabs.push({ id: 'kyc-pp', label: 'KYC Personne physique' })
    const ppeCount = dossier.value.kyc_pp?.ppe_declarations?.length ?? 0
    tabs.push({ id: 'kyc-ppe', label: ppeCount > 0 ? `PPE ⚠ (${ppeCount})` : 'PPE' })
  } else {
    tabs.push({ id: 'kyc-pm', label: 'KYC Personne morale' })
    tabs.push({ id: 'representant', label: 'Représentant légal' })
    const beCount = dossier.value.kyc_pm?.beneficiaires_effectifs?.length ?? 0
    tabs.push({ id: 'actionnaires-be', label: `Actionnaires / BEs (${beCount})` })
    const ppeCount = dossier.value.kyc_pm?.ppe_declarations?.length ?? 0
    tabs.push({ id: 'kyc-ppe', label: ppeCount > 0 ? `PPE (${ppeCount})` : 'PPE' })
  }
  tabs.push({ id: 'transaction', label: 'Transaction' })
  if (!isAgent.value) {
    tabs.push({ id: 'scoring', label: 'Scoring risque' })
  }
  tabs.push({ id: 'documents', label: 'Documents' })
  tabs.push({ id: 'historique', label: 'Historique' })
  tabs.push({ id: 'dos', label: 'DOS' })
  return tabs
})

// ── Alertes liées + triggers actifs ─────────────────────────────────────────────
const dossierAlertes = ref<Array<{ id: string; type_alerte: string; niveau: string; statut: string; description: string; resolution_note: string | null; created_at: string | null }>>([])
const alertesCollapsed = ref(true)

// PPE détecté sur le dossier (PP, représentant PM, ou déclarations KYC-PPE)
const isPPE = computed(() => {
  const d = dossier.value as any
  if (!d) return false
  return !!(d.kyc_pp?.est_ppe || d.kyc_pm?.ppe_detectee || d.kyc_pm?.representant_statut_ppe
    || d.kyc_pp?.ppe_declarations?.length || d.kyc_pm?.ppe_declarations?.length)
})

// Liste de tous les triggers actifs (T1 ajouté si PPE, + ceux issus des alertes)
const triggersActifs = computed<string[]>(() => {
  const set = new Set<string>()
  if (dossier.value?.trigger_actif) set.add(dossier.value.trigger_actif)
  for (const a of dossierAlertes.value) {
    const m = a.type_alerte.match(/^TRIGGER_(T\d)$/)
    if (m) set.add(m[1])
  }
  if (isPPE.value) set.add('T1')
  return Array.from(set).sort()
})

const alertesOuvertesCritiques = computed(() =>
  dossierAlertes.value.filter(a => !['traitee', 'ignoree'].includes(a.statut) && a.niveau === 'ELEVE').length
)

async function loadDossierAlertes() {
  if (!dossier.value) return
  try { dossierAlertes.value = await dossiersService.getAlertes(dossier.value.id) } catch { /* ignore */ }
}

onMounted(async () => {
  try {
    dossier.value = await dossiersService.get(route.params.id as string)
    activeSection.value = dossier.value.type_client === 'PP' ? 'kyc-pp' : 'kyc-pm'
    await loadDossierAlertes()
  } catch {
    error.value = 'Dossier introuvable.'
  } finally {
    loading.value = false
  }
})

watch(activeSection, async (section) => {
  if (!dossier.value) return
  const id = dossier.value.id

  if (section === 'historique') {
    historiqueLoading.value = true
    commentairesLoading.value = true
    try {
      const [h, c] = await Promise.all([
        dossiersService.getHistorique(id),
        dossiersService.listCommentaires(id),
      ])
      historique.value = h
      commentaires.value = c
    } finally {
      historiqueLoading.value = false
      commentairesLoading.value = false
    }
  }

  if (section === 'dos') {
    dosLoading.value = true
    try {
      const r = await dosService.listForDossier(id)
      dosList.value = r.items
    } finally {
      dosLoading.value = false
    }
  }
})

async function submitCommentaire() {
  if (!dossier.value || !newCommentaire.value.trim()) return
  commentaireSubmitting.value = true
  try {
    const c = await dossiersService.addCommentaire(dossier.value.id, newCommentaire.value.trim())
    commentaires.value.push(c)
    newCommentaire.value = ''
  } finally {
    commentaireSubmitting.value = false
  }
}

// ── DOS state ─────────────────────────────────────────────────────────────────

const dosList = ref<DosOut[]>([])
const dosLoading = ref(false)

// ── Scoring ───────────────────────────────────────────────────────────────────

async function onScored(_result: { score: number; niveau: string }) {
  if (dossier.value) {
    dossier.value = await dossiersService.get(dossier.value.id)
  }
}

// ── Soumettre pour analyse ────────────────────────────────────────────────────

const submittingAnalyse = ref(false)
const analyseError = ref('')

async function submitForAnalyse() {
  if (!dossier.value) return
  const d = dossier.value
  const hasKyc = d.type_client === 'PP' ? !!d.kyc_pp?.nom : !!d.kyc_pm?.denomination_sociale
  if (!hasKyc) {
    analyseError.value = 'Le formulaire KYC doit être complété avant de soumettre le dossier pour analyse.'
    return
  }
  submittingAnalyse.value = true
  analyseError.value = ''
  try {
    const docs = await dossiersService.listDocuments(d.id)
    if (docs.length === 0) {
      analyseError.value = 'Veuillez joindre au moins un document justificatif avant de soumettre pour analyse.'
      return
    }
    dossier.value = await dossiersService.transition(d.id, 'en_analyse')
  } catch (e: any) {
    analyseError.value = e?.response?.data?.detail ?? 'Erreur lors de la soumission.'
  } finally {
    submittingAnalyse.value = false
  }
}

// ── RBAC ──────────────────────────────────────────────────────────────────────

const CLERCS_ROLES     = ['clercs']
const CONFORMITE_ROLES = ['responsable_conformite', 'notaire_principal', 'admin']
// Clôture / archivage (WRK-04, back: _CLOTURE) : Notaire Principal + Admin uniquement (séparation Art. 12).
const CLOTURE_ROLES    = ['notaire_principal', 'admin']
// Seuls admin et notaire_principal peuvent assigner un dossier
const ASSIGNER_ROLES   = ['admin', 'notaire_principal']

const isAgent    = computed(() => CLERCS_ROLES.includes(auth.user?.role ?? ''))
const isRC       = computed(() => CONFORMITE_ROLES.includes(auth.user?.role ?? ''))
const canAssign  = computed(() => ASSIGNER_ROLES.includes(auth.user?.role ?? ''))
// Accès DOS (Art. 63) — aligné sur le backend require_dos_access.
const DOS_ROLES = ['admin', 'notaire_principal', 'responsable_conformite', 'declarant_centif']
const canCreateDos = computed(() => DOS_ROLES.includes(auth.user?.role ?? ''))
// Édition : superviseur (RC/notaire principal/admin) ou assigné courant (aligné backend is_supervisor)
const canModify = computed(() =>
  isRC.value || (!!dossier.value?.assigned_to && dossier.value.assigned_to === auth.user?.id),
)

// ── Transaction edit ──────────────────────────────────────────────────────────

type ModePaiement = '' | 'especes' | 'cheque' | 'virement' | 'mix' | 'paiement_tiers' | 'autre'
const txEdit   = ref(false)
const txForm   = ref<{ montant_tranche: '' | 'moins_15m' | 'plus_15m'; montant_transaction: number | null; mode_paiement: ModePaiement }>({ montant_tranche: '', montant_transaction: null, mode_paiement: '' })
const txSaving = ref(false)
const txError  = ref('')

const txSurveillanceEspece = computed(() =>
  txForm.value.mode_paiement === 'especes' &&
  (txForm.value.montant_tranche === 'plus_15m' || Number(txForm.value.montant_transaction || 0) > 15_000_000),
)

function startTxEdit() {
  const d = dossier.value!
  txForm.value = {
    montant_tranche:     (d.montant_tranche as any) ?? '',
    montant_transaction: d.montant_transaction ?? null,
    mode_paiement:       (d.mode_paiement as any) ?? '',
  }
  txEdit.value  = true
  txError.value = ''
}

async function saveTransaction() {
  if (!dossier.value) return
  txSaving.value = true
  txError.value  = ''
  try {
    const f = txForm.value
    await dossiersService.saveTransaction(dossier.value.id, {
      montant_tranche:     f.montant_tranche || undefined,
      montant_transaction: f.montant_transaction != null ? f.montant_transaction : undefined,
      mode_paiement:       f.mode_paiement || undefined,
    })
    dossier.value = await dossiersService.get(dossier.value.id)
    txEdit.value  = false
  } catch (e: any) {
    txError.value = e?.response?.data?.detail ?? 'Erreur lors de la sauvegarde.'
  } finally {
    txSaving.value = false
  }
}

// ── KYC-PP edit (inline) ────────────────────────────────────────────────────────

const ppEdit   = ref(false)
const ppSaving = ref(false)
const ppError  = ref('')
const ppForm   = ref<Partial<KycPPData>>({})

function startPpEdit() {
  const pp = dossier.value!.kyc_pp ?? {}
  ppForm.value = {
    nom: pp.nom ?? '',
    prenoms: pp.prenoms ?? '',
    nom_jeune_fille: pp.nom_jeune_fille ?? '',
    nom_prenoms_pere: pp.nom_prenoms_pere ?? '',
    nom_prenoms_mere: pp.nom_prenoms_mere ?? '',
    date_naissance: pp.date_naissance ?? '',
    lieu_naissance: pp.lieu_naissance ?? '',
    nationalite: pp.nationalite ?? '',
    autres_nationalites: pp.autres_nationalites ?? '',
    statut_matrimonial: pp.statut_matrimonial ?? '',
    type_piece: pp.type_piece ?? '',
    numero_piece: pp.numero_piece ?? '',
    numero_contribuable: pp.numero_contribuable ?? '',
    profession: pp.profession ?? '',
    profession_5_ans: pp.profession_5_ans ?? '',
    employeur: pp.employeur ?? '',
    secteur_activite: pp.secteur_activite ?? '',
    adresse_geo: pp.adresse_geo ?? '',
    adresse_postale: pp.adresse_postale ?? '',
    telephone: pp.telephone ?? '',
    whatsapp: pp.whatsapp ?? '',
    email: pp.email ?? '',
    non_resident: pp.non_resident ?? false,
    pays_residence: pp.pays_residence ?? '',
    est_ppe: pp.est_ppe ?? false,
    anciennete_pro: pp.anciennete_pro ?? '',
  }
  ppEdit.value  = true
  ppError.value = ''
}

async function savePp() {
  if (!dossier.value) return
  ppSaving.value = true
  ppError.value  = ''
  try {
    // nom + prenoms toujours présents (requis backend)
    await dossiersService.upsertKycPP(dossier.value.id, { ...ppForm.value })
    dossier.value = await dossiersService.get(dossier.value.id)
    ppEdit.value  = false
  } catch (e: any) {
    ppError.value = e?.response?.data?.detail ?? 'Erreur lors de la sauvegarde.'
  } finally {
    ppSaving.value = false
  }
}

// ── KYC-PM edit (inline) ────────────────────────────────────────────────────────

type InfosPm = { domaine_activite: string; nature_pm: string; cotee: boolean; marche_reglemente: string }
type PmFormType = Partial<KycPMData> & { infos_pm: InfosPm }

const pmEdit   = ref(false)
const pmSaving = ref(false)
const pmError  = ref('')
const pmForm   = ref<PmFormType>({ infos_pm: { domaine_activite: '', nature_pm: '', cotee: false, marche_reglemente: '' } })

function startPmEdit() {
  const pm = dossier.value!.kyc_pm ?? {}
  const infos = pm.infos_pm ?? null
  pmForm.value = {
    denomination_sociale: pm.denomination_sociale ?? '',
    forme_juridique: pm.forme_juridique ?? '',
    numero_rccm: pm.numero_rccm ?? '',
    numero_contribuable: pm.numero_contribuable ?? '',
    libelle_activite: pm.libelle_activite ?? '',
    adresse: pm.adresse ?? '',
    telephone: pm.telephone ?? '',
    whatsapp: pm.whatsapp ?? '',
    email: pm.email ?? '',
    nom_representant_legal: pm.nom_representant_legal ?? '',
    ppe_detectee: pm.ppe_detectee ?? false,
    anciennete_pro: pm.anciennete_pro ?? '',
    infos_pm: {
      domaine_activite: infos?.domaine_activite ?? '',
      nature_pm: infos?.nature_pm ?? '',
      cotee: infos?.cotee ?? false,
      marche_reglemente: infos?.marche_reglemente ?? '',
    },
  }
  pmEdit.value  = true
  pmError.value = ''
}

async function savePm() {
  if (!dossier.value) return
  pmSaving.value = true
  pmError.value  = ''
  try {
    // denomination_sociale toujours présente (requise backend)
    await dossiersService.upsertKycPM(dossier.value.id, { ...pmForm.value })
    dossier.value = await dossiersService.get(dossier.value.id)
    pmEdit.value  = false
  } catch (e: any) {
    pmError.value = e?.response?.data?.detail ?? 'Erreur lors de la sauvegarde.'
  } finally {
    pmSaving.value = false
  }
}

// ── Assignation ───────────────────────────────────────────────────────────────

interface AssignableUser { id: string; full_name: string; role: string }

const assignModal = ref({
  open: false, loading: false, saving: false, selectedId: '',
  users: [] as AssignableUser[], error: '',
})

const assignedUserName = computed(() => {
  if (!dossier.value?.assigned_to) return null
  const u = assignModal.value.users.find(u => u.id === dossier.value!.assigned_to)
  return u ? u.full_name : null
})

async function openAssignModal() {
  if (!dossier.value) return
  assignModal.value.open     = true
  assignModal.value.error    = ''
  assignModal.value.selectedId = dossier.value.assigned_to ?? ''
  if (assignModal.value.users.length === 0) {
    assignModal.value.loading = true
    try {
      assignModal.value.users = await dossiersService.getAssignables(dossier.value!.id)
    } catch {
      assignModal.value.error = 'Impossible de charger la liste des agents.'
    } finally {
      assignModal.value.loading = false
    }
  }
}

async function confirmAssign() {
  if (!dossier.value || !assignModal.value.selectedId) return
  assignModal.value.saving = true
  assignModal.value.error  = ''
  try {
    await dossiersService.assign(dossier.value.id, assignModal.value.selectedId)
    dossier.value = { ...dossier.value, assigned_to: assignModal.value.selectedId }
    assignModal.value.open = false
  } catch (e: any) {
    assignModal.value.error = e?.response?.data?.detail ?? 'Erreur lors de l\'assignation.'
  } finally {
    assignModal.value.saving = false
  }
}

// ── Transitions ───────────────────────────────────────────────────────────────

type TransitionDef = {
  to: StatutDossier
  label: string
  color: 'success' | 'warning' | 'danger' | 'neutral'
  roles: string[]
  wrk09?: boolean
}

const TRANSITIONS_CONFIG: Record<string, TransitionDef[]> = {
  en_analyse: [
    { to: 'vigilance_renforcee', label: 'Vigilance renforcée',    color: 'warning', roles: CONFORMITE_ROLES },
    { to: 'valide',              label: 'Valider',                 color: 'success', roles: CONFORMITE_ROLES, wrk09: true },
    { to: 'bloque',              label: 'Bloquer',                 color: 'danger',  roles: CONFORMITE_ROLES },
    { to: 'brouillon',           label: 'Renvoyer en correction',  color: 'neutral', roles: CONFORMITE_ROLES },
  ],
  vigilance_renforcee: [
    { to: 'valide',  label: 'Valider',  color: 'success', roles: CONFORMITE_ROLES },
    { to: 'bloque',  label: 'Bloquer',  color: 'danger',  roles: CONFORMITE_ROLES },
  ],
  valide: [
    { to: 'traite',  label: 'Marquer traité', color: 'success', roles: CONFORMITE_ROLES },
    { to: 'bloque',  label: 'Bloquer',         color: 'danger',  roles: CONFORMITE_ROLES },
  ],
  bloque:  [{ to: 'en_analyse', label: 'Réouvrir pour analyse', color: 'success', roles: CONFORMITE_ROLES }],
  traite:  [{ to: 'cloture',  label: 'Clôturer',  color: 'neutral', roles: CLOTURE_ROLES }],
  cloture: [{ to: 'archive',  label: 'Archiver',   color: 'neutral', roles: CLOTURE_ROLES }],
}

const availableTransitions = computed((): TransitionDef[] => {
  if (!dossier.value || !auth.user) return []
  const role = auth.user.role
  const statut = dossier.value.statut
  const trigger = dossier.value.trigger_actif
  return (TRANSITIONS_CONFIG[statut] ?? []).filter(t => {
    if (!t.roles.includes(role)) return false
    // Tout trigger absolutoire (T1-T6) force ÉLEVÉ → autorisation Notaire Principal requise (WRK-09)
    if (t.wrk09 && trigger && role !== 'notaire_principal') return false
    return true
  })
})

const transitionModal = ref({
  open: false, to: '' as StatutDossier, label: '', color: 'success' as TransitionDef['color'],
  wrk09Warning: false, commentaire: '', loading: false, error: '',
})

function openTransitionModal(t: TransitionDef) {
  const trigger = dossier.value?.trigger_actif
  transitionModal.value = {
    open: true, to: t.to, label: t.label, color: t.color,
    wrk09Warning: !!t.wrk09 && !!trigger,
    commentaire: '', loading: false, error: '',
  }
}

const triggerModal = ref({ open: false, trigger: '' as 'T5' | 'T6', commentaire: '', loading: false, error: '' })

function openTriggerModal(t: 'T5' | 'T6') {
  triggerModal.value = { open: true, trigger: t, commentaire: '', loading: false, error: '' }
}

async function confirmTriggerManuel() {
  if (!dossier.value || !triggerModal.value.commentaire.trim()) return
  triggerModal.value.loading = true
  triggerModal.value.error = ''
  try {
    await dossiersService.triggerManuel(dossier.value.id, triggerModal.value.trigger, triggerModal.value.commentaire.trim())
    dossier.value = await dossiersService.get(dossier.value.id)
    await loadDossierAlertes()
    triggerModal.value.open = false
  } catch (e: any) {
    triggerModal.value.error = e?.response?.data?.detail ?? 'Erreur lors du déclenchement.'
  } finally {
    triggerModal.value.loading = false
  }
}

async function confirmTransition() {
  if (!dossier.value || !transitionModal.value.commentaire.trim()) return
  transitionModal.value.loading = true
  transitionModal.value.error = ''
  try {
    dossier.value = await dossiersService.transition(
      dossier.value.id, transitionModal.value.to, transitionModal.value.commentaire.trim(),
    )
    await loadDossierAlertes()
    transitionModal.value.open = false
  } catch (e: any) {
    transitionModal.value.error = e?.response?.data?.detail ?? 'Erreur lors de la transition.'
  } finally {
    transitionModal.value.loading = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function formatAmount(n: number | string): string {
  return Number(n).toLocaleString('fr-FR', { style: 'decimal' }) + ' FCFA'
}
</script>

<style scoped>
.kyc-detail-page { max-width: 1000px; }

/* ── Header ── */
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.25rem; }
.breadcrumb { display: flex; align-items: center; gap: 0.25rem; margin-bottom: 0.25rem; }
.breadcrumb-link { background: none; border: none; cursor: pointer; font-size: 0.8125rem; color: var(--color-text-secondary); padding: 0; }
.breadcrumb-link:hover { color: var(--color-sidebar-bg); }
.breadcrumb-sep { width: 14px; height: 14px; color: var(--color-border); }
.breadcrumb span { font-size: 0.8125rem; color: var(--color-text-primary); font-family: monospace; }
.page-title { font-size: 1.375rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.header-actions { display: flex; align-items: center; gap: 0.5rem; padding-top: 1.75rem; flex-wrap: wrap; }

/* ── Status badges ── */
.statut-badge { display: inline-block; border-radius: 10px; padding: 3px 10px; font-size: 0.6875rem; font-weight: 600; }
.statut--brouillon               { color: var(--color-status-brouillon); background: var(--color-status-brouillon-bg); }
.statut--en_analyse              { color: var(--color-status-en-analyse); background: var(--color-status-en-analyse-bg); }
.statut--vigilance_renforcee     { color: var(--color-status-vigilance); background: var(--color-status-vigilance-bg); }
.statut--valide, .statut--actif  { color: var(--color-status-valide); background: var(--color-status-valide-bg); }
.statut--actif_sous_surveillance { color: var(--color-status-vigilance); background: var(--color-status-vigilance-bg); }
.statut--bloque                  { color: var(--color-status-bloque); background: var(--color-status-bloque-bg); }
.statut--traite                  { color: var(--color-status-traite); background: var(--color-status-traite-bg); }
.statut--resilie, .statut--cloture, .statut--archive { color: var(--color-status-cloture); background: var(--color-status-cloture-bg); }
.risk-badge { display: inline-block; border-radius: 10px; padding: 3px 10px; font-size: 0.6875rem; font-weight: 700; }
.risk--FAIBLE { color: var(--color-risk-low);    background: var(--color-risk-low-bg); }
.risk--MOYEN  { color: var(--color-risk-medium); background: var(--color-risk-medium-bg); }
.risk--ELEVE  { color: var(--color-risk-high);   background: var(--color-risk-high-bg); }

/* ── Meta strip ── */
.meta-strip { padding: 0.875rem 1.25rem; display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 0; }
.surveillance-espece-banner { display: flex; align-items: center; gap: 0.5rem; background: #fef2f2; border: 1px solid #fca5a5; color: #b91c1c; border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.8125rem; font-weight: 600; margin: 1rem 0; }
.surveillance-espece-banner svg { width: 18px; height: 18px; flex-shrink: 0; }
.readonly-banner { display: flex; align-items: center; gap: 0.5rem; background: #f8fafc; border: 1px solid #cbd5e1; color: #475569; border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.8125rem; font-weight: 600; margin: 1rem 0; }
.readonly-icon { width: 18px; height: 18px; flex-shrink: 0; }

/* ── Triggers actifs ── */
.triggers-actifs-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; padding: 0.55rem 0.85rem; background: var(--color-bg-card); border: 1px solid var(--color-border); border-left: 3px solid var(--color-risk-high); border-radius: 10px; }
.triggers-actifs-label { display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; font-weight: 600; color: var(--color-text-secondary); }
.triggers-actifs-icon { width: 15px; height: 15px; color: var(--color-risk-high); flex-shrink: 0; }
.trigger-chip { font-size: 0.72rem; font-weight: 700; padding: 4px 11px; border-radius: 99px; background: var(--color-risk-high-bg); color: var(--color-risk-high); letter-spacing: 0.03em; }
.trigger-chip--ppe { background: #fee2e2; color: #b91c1c; }

/* ── Alertes liées ── */
.alertes-liees-card { margin-bottom: 1rem; }
.alertes-liees-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
.alertes-liees-toggle { width: 100%; background: none; border: none; cursor: pointer; padding: 0; text-align: left; }
.alertes-toggle-left { display: inline-flex; align-items: center; gap: 0.5rem; }
.alertes-chevron { width: 16px; height: 16px; color: var(--color-text-secondary); transition: transform 0.15s; flex-shrink: 0; }
.alertes-chevron--open { transform: rotate(90deg); }
.alertes-warn-badge { font-size: 0.75rem; font-weight: 700; color: #b91c1c; background: #fee2e2; padding: 0.25rem 0.6rem; border-radius: 6px; }
.alertes-liees-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.4rem; }
.alerte-liee-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; flex-wrap: wrap; }
.alerte-liee-niveau { font-weight: 700; font-size: 0.7rem; padding: 1px 6px; border-radius: 4px; }
.niv-critique { background: #fee2e2; color: #dc2626; } .niv-eleve { background: #ffedd5; color: #c2410c; }
.niv-moyen { background: #fef3c7; color: #92400e; } .niv-faible { background: #dbeafe; color: #1e40af; }
.alerte-liee-type { font-weight: 600; }
.alerte-liee-statut { font-size: 0.7rem; font-weight: 700; padding: 1px 6px; border-radius: 999px; }
.st-ouverte { background: #fee2e2; color: #dc2626; } .st-en_cours { background: #fef3c7; color: #92400e; } .st-traitee { background: #d1fae5; color: #065f46; } .st-ignoree { background: #e2e8f0; color: #475569; }
.alerte-liee-desc { color: var(--color-text-muted); flex: 1 1 100%; }
.alertes-liees-hint { font-size: 0.7rem; color: var(--color-text-muted); margin: 0.5rem 0 0; }
.meta-item  { display: flex; flex-direction: column; gap: 0.125rem; }
.meta-label { font-size: 0.6875rem; font-weight: 600; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
.meta-value { font-size: 0.8125rem; color: var(--color-text-primary); font-weight: 500; }
.meta-value.mono, .mono { font-family: monospace; }

.score-pill { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.875rem; font-weight: 700; }
.score-pill--faible { background: var(--color-risk-low-bg);    color: var(--color-risk-low); }
.score-pill--moyen  { background: var(--color-risk-medium-bg); color: var(--color-risk-medium); }
.score-pill--eleve,
.score-pill--élevé  { background: var(--color-risk-high-bg);   color: var(--color-risk-high); }
.score-empty-btn {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 2px 8px; border: 1px dashed var(--color-border); border-radius: 6px;
  background: none; cursor: pointer; font-size: 0.75rem; font-weight: 600; color: var(--color-text-muted);
}
.score-empty-btn svg { width: 11px; height: 11px; }
.score-empty-btn:hover { border-color: var(--color-sidebar-bg); color: var(--color-sidebar-bg); }

/* ── Flat tabs ── */
.tabs-nav {
  display: flex; align-items: stretch; gap: 0;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 8px 8px 0 0;
  border-bottom: none;
  padding: 0 0.25rem;
  overflow-x: auto;
  margin-top: 0.75rem;
  scrollbar-width: none;
}
.tabs-nav::-webkit-scrollbar { display: none; }
.tabs-nav-item {
  padding: 0.6875rem 1rem;
  font-size: 0.8125rem; font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer; border: none; background: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  white-space: nowrap;
  transition: color 0.15s, border-color 0.15s;
  flex-shrink: 0;
}
.tabs-nav-item--active {
  color: var(--color-text-primary); font-weight: 700;
  border-bottom-color: var(--color-sidebar-bg);
}
.tabs-nav-item:hover:not(.tabs-nav-item--active) { color: var(--color-text-primary); }

/* ── Section cards ── */
.section-card {
  padding: 1.25rem 1.5rem; margin-top: 0;
  border-top-left-radius: 0; border-top-right-radius: 0;
}
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.section-title { font-size: 0.9375rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }

/* ── Info grid (view mode) ── */
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem 1.5rem; }
.info-item { display: flex; flex-direction: column; gap: 0.125rem; }
.info-item--full { grid-column: 1 / -1; }
.info-label { font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--color-text-secondary); }
.info-value { font-size: 0.875rem; color: var(--color-text-primary); }
.info-value.ppe-flag { color: var(--color-status-bloque); font-weight: 700; }

/* ── Edit grid (edit mode) ── */
.edit-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem 1.25rem; }
.edit-field { display: flex; flex-direction: column; gap: 0.25rem; }
.edit-field--full { grid-column: 1 / -1; }
.req { color: var(--color-status-bloque); }
.field-input {
  padding: 0.4375rem 0.625rem; font-size: 0.875rem;
  border: 1px solid var(--color-border); border-radius: 7px;
  background: var(--color-input-bg, #fff); color: var(--color-text-primary); font-family: inherit;
  width: 100%;
}
.field-input:focus { outline: none; border-color: var(--color-sidebar-bg); }
select.field-input { appearance: auto; }
.field-textarea {
  width: 100%; padding: 0.5rem 0.75rem; font-size: 0.875rem;
  border: 1px solid var(--color-border); border-radius: 8px; resize: vertical;
  font-family: inherit; background: var(--color-input-bg, #fff); color: var(--color-text-primary);
}
.field-textarea:focus { outline: none; border-color: var(--color-sidebar-bg); }
.save-error { font-size: 0.8125rem; color: var(--color-status-bloque); margin: 0 0 0.75rem; }

/* ── Persons list ── */
.persons-list { display: flex; flex-direction: column; gap: 0.5rem; }
.person-row {
  display: flex; align-items: flex-start; gap: 0.75rem;
  padding: 0.625rem 0.875rem; background: var(--color-bg-page);
  border: 1px solid var(--color-border); border-radius: 8px;
}
.person-avatar {
  width: 34px; height: 34px; border-radius: 50%; background: var(--color-sidebar-bg); color: #fff;
  font-size: 0.6875rem; font-weight: 700; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; text-transform: uppercase;
}
.person-info { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.person-name { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-primary); }
.person-tags { display: flex; align-items: center; gap: 0.375rem; flex-wrap: wrap; }
.person-tag { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 5px; padding: 1px 6px; font-size: 0.6875rem; color: var(--color-text-secondary); }
.pct-tag { background: rgba(201,162,39,0.1); border-color: transparent; color: var(--color-sidebar-bg); font-weight: 700; }
.person-nat { font-size: 0.75rem; color: var(--color-text-muted); }
.ppe-mini { background: var(--color-status-bloque-bg); color: var(--color-status-bloque); border-radius: 4px; padding: 1px 5px; font-size: 0.625rem; font-weight: 700; }

/* ── Entity edit blocks ── */
.entity-edit-block {
  border: 1px solid var(--color-border); border-radius: 8px;
  padding: 0.875rem 1rem; margin-bottom: 0.75rem; background: var(--color-bg-subtle, #f9fafb);
}
.entity-edit-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }
.entity-edit-num { font-size: 0.75rem; font-weight: 700; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
.btn-remove-row {
  padding: 0.1875rem 0.625rem; border: 1px solid var(--color-status-bloque);
  border-radius: 6px; background: none; color: var(--color-status-bloque);
  font-size: 0.6875rem; font-weight: 600; cursor: pointer;
}
.btn-remove-row:hover { background: var(--color-status-bloque-bg); }
.btn-add-row { color: var(--color-sidebar-bg); border-color: var(--color-sidebar-bg); }

/* ── BE separator ── */
.be-separator { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--color-border); }

/* ── Subsection ── */
.subsection-title { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-secondary); margin: 1.25rem 0 0.625rem; border-top: 1px solid var(--color-border); padding-top: 1rem; }
.mandant-detail-block { background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 8px; padding: 0.875rem 1rem; }

/* ── PPE section ── */
.ppe-list  { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
.ppe-row   { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; background: var(--color-bg-page); border: 1px solid var(--color-border); border-radius: 8px; }
.ppe-row-left  { display: flex; align-items: center; gap: 0.75rem; }
.ppe-row-right { display: flex; align-items: center; gap: 0.5rem; }
.be-avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--color-risk-high); color: #fff; font-size: 0.6875rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; text-transform: uppercase; }
.ppe-name { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); margin: 0 0 0.125rem; }
.ppe-meta { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0; }
.sep { color: var(--color-border); margin: 0 0.25rem; }
.presse-chip { border-radius: 5px; padding: 2px 6px; font-size: 0.6875rem; font-weight: 700; }
.presse--positif { background: var(--color-risk-high-bg); color: var(--color-risk-high); }
.presse--ambigu  { background: var(--color-risk-medium-bg); color: var(--color-risk-medium); }
.validation-badge { border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.validation--en_attente { color: var(--color-status-en-analyse); background: var(--color-status-en-analyse-bg); }
.validation--valide     { color: var(--color-status-valide); background: var(--color-status-valide-bg); }
.validation--rejete     { color: var(--color-status-bloque); background: var(--color-status-bloque-bg); }
.pending-ppe  { background: var(--color-risk-high-bg); border-radius: 8px; padding: 0.75rem 1rem; }
.pending-label { font-size: 0.75rem; font-weight: 700; color: var(--color-risk-high); margin: 0 0 0.5rem; text-transform: uppercase; letter-spacing: 0.04em; }
.pending-row  { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.375rem; }
.pending-name { font-size: 0.8125rem; font-weight: 600; color: var(--color-text-primary); flex: 1; }
.pending-source { font-size: 0.6875rem; background: var(--color-risk-high); color: #fff; border-radius: 4px; padding: 1px 5px; font-weight: 700; }

/* ── DOS section ── */
.dos-list { display: flex; flex-direction: column; gap: 0.5rem; }
.dos-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1rem; background: var(--color-bg-page);
  border: 1px solid var(--color-border); border-radius: 8px;
}
.dos-row-left  { display: flex; align-items: center; gap: 0.75rem; }
.dos-row-right { display: flex; align-items: center; gap: 0.5rem; }
.dos-icon {
  width: 32px; height: 32px; border-radius: 8px; background: rgba(27,43,75,0.08);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.dos-icon svg { width: 16px; height: 16px; color: var(--color-sidebar-bg); }
.dos-ref { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); margin: 0 0 0.125rem; font-family: monospace; }
.dos-meta { font-size: 0.75rem; color: var(--color-text-secondary); margin: 0; }
.dos-statut { border-radius: 10px; padding: 2px 8px; font-size: 0.6875rem; font-weight: 600; }
.dos-statut--finalisee { color: var(--color-status-valide); background: var(--color-status-valide-bg); }
.dos-statut--brouillon { color: var(--color-status-brouillon); background: var(--color-status-brouillon-bg); }

/* ── Historique & Commentaires ── */
.loading-inline { font-size: 0.875rem; color: var(--color-text-secondary); padding: 0.5rem 0; }
.historique-list { display: flex; flex-direction: column; gap: 0; }
.historique-row { display: flex; gap: 0.75rem; padding: 0.625rem 0; border-bottom: 1px solid var(--color-border); }
.historique-row:last-child { border-bottom: none; }
.historique-icon { width: 28px; height: 28px; border-radius: 50%; background: var(--color-sidebar-bg); display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px; }
.historique-icon svg { width: 14px; height: 14px; color: #fff; }
.historique-body { flex: 1; }
.historique-transition { display: flex; align-items: center; gap: 0.375rem; margin: 0 0 0.25rem; }
.statut-chip { font-size: 0.6875rem; font-weight: 600; padding: 2px 7px; border-radius: 8px; background: var(--color-border); color: var(--color-text-secondary); }
.statut-chip--next { background: var(--color-status-valide-bg); color: var(--color-status-valide); }
.arrow { font-size: 0.875rem; color: var(--color-text-secondary); }
.historique-comment { font-size: 0.8125rem; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.historique-meta { font-size: 0.6875rem; color: var(--color-text-muted); margin: 0; }
.commentaires-list { display: flex; flex-direction: column; gap: 0.625rem; margin-bottom: 1rem; }
.commentaire-row { display: flex; gap: 0.75rem; }
.commentaire-avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--color-sidebar-bg); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 0.6875rem; font-weight: 700; flex-shrink: 0; }
.commentaire-body { flex: 1; background: var(--color-bg-subtle, #f9fafb); border-radius: 8px; padding: 0.5rem 0.75rem; }
.commentaire-contenu { font-size: 0.875rem; color: var(--color-text-primary); margin: 0 0 0.25rem; white-space: pre-wrap; }
.commentaire-meta { font-size: 0.6875rem; color: var(--color-text-muted); margin: 0; }
.confidential-tag { display: inline-block; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; background: var(--color-risk-medium-bg); color: var(--color-risk-medium); border-radius: 4px; padding: 1px 5px; margin-left: 0.375rem; vertical-align: middle; }
.add-commentaire { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.75rem; }

/* ── States ── */
.loading-card { padding: 3rem; text-align: center; font-size: 0.875rem; color: var(--color-text-muted); }
.error-card   { padding: 3rem; text-align: center; font-size: 0.875rem; color: var(--color-status-bloque); }
.empty-section { padding: 2rem; text-align: center; font-size: 0.875rem; color: var(--color-text-muted); }
.placeholder-text { font-size: 0.875rem; color: var(--color-text-secondary); font-style: italic; }

/* ── Buttons ── */
.btn-ghost { padding: 0.375rem 0.75rem; border: 1px solid var(--color-border); border-radius: 7px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 0.75rem; cursor: pointer; }
.btn-ghost:hover { border-color: var(--color-sidebar-bg); color: var(--color-text-primary); }
.btn-sm { font-size: 0.75rem; padding: 0.25rem 0.625rem; }
.btn-primary { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5rem 1rem; background: var(--color-sidebar-bg); color: #fff; border: none; border-radius: 8px; font-size: 0.8125rem; font-weight: 600; cursor: pointer; }
.btn-primary:hover { opacity: 0.88; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm-primary { font-size: 0.75rem; padding: 0.3125rem 0.75rem; }
.btn-back {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0.3125rem 0.625rem;
  background: none; border: 1px solid var(--color-border); border-radius: 7px;
  font-size: 0.75rem; font-weight: 500; color: var(--color-text-secondary); cursor: pointer; white-space: nowrap;
}
.btn-back:hover { border-color: var(--color-sidebar-bg); color: var(--color-text-primary); }
.btn-back-icon { width: 14px; height: 14px; flex-shrink: 0; }
.header-sep { width: 1px; height: 1.25rem; background: var(--color-border); }
.btn-submit-analyse {
  display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.4375rem 1rem; background: var(--color-sidebar-bg); color: #fff;
  border: none; border-radius: 8px; font-size: 0.8125rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s;
}
.btn-submit-analyse:hover:not(:disabled) { opacity: 0.88; }
.btn-submit-analyse:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-assign {
  display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.4375rem 0.875rem; background: #f1f5f9; color: var(--color-text-primary);
  border: 1px solid var(--color-border); border-radius: 8px;
  font-size: 0.8125rem; font-weight: 600; cursor: pointer; transition: background 0.15s, border-color 0.15s;
}
.btn-assign:hover { background: var(--color-sidebar-bg); color: #fff; border-color: var(--color-sidebar-bg); }
.btn-dos {
  display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.4375rem 0.875rem; background: #1b2b4b; color: #c9a227;
  border: 1px solid #1b2b4b; border-radius: 8px;
  font-size: 0.8125rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s;
}
.btn-dos:hover { opacity: 0.88; }
.btn-sm-dos { font-size: 0.75rem; padding: 0.3125rem 0.75rem; }
.btn-icon { width: 15px; height: 15px; flex-shrink: 0; }
.checkbox { width: 15px; height: 15px; cursor: pointer; }

/* ── Transition bar ── */
.transition-bar {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
  padding: 0.625rem 1rem; background: var(--color-bg-card); border: 1px solid var(--color-border);
  border-radius: 8px; margin-bottom: 0.75rem;
}
.transition-bar-label { font-size: 0.6875rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--color-text-secondary); margin-right: 0.25rem; }
.btn-transition {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0.3125rem 0.75rem; border-radius: 7px;
  font-size: 0.75rem; font-weight: 600; cursor: pointer; border: 1.5px solid transparent;
}
.btn-transition--success { background: var(--color-status-valide-bg);   color: var(--color-status-valide);   border-color: var(--color-status-valide); }
.btn-transition--warning { background: var(--color-status-vigilance-bg); color: var(--color-status-vigilance); border-color: var(--color-status-vigilance); }
.btn-transition--danger  { background: var(--color-status-bloque-bg);   color: var(--color-status-bloque);   border-color: var(--color-status-bloque); }
.btn-transition--neutral { background: var(--color-border);              color: var(--color-text-secondary);  border-color: var(--color-border); }
.btn-transition:hover { opacity: 0.82; }
.transition-sep { width: 1px; height: 1.25rem; background: var(--color-border); margin: 0 0.25rem; }
.btn-trigger-manual {
  padding: 0.3125rem 0.75rem; border-radius: 7px;
  font-size: 0.75rem; font-weight: 600; cursor: pointer;
  background: transparent; border: 1.5px dashed var(--color-status-bloque); color: var(--color-status-bloque);
}
.btn-trigger-manual:hover { background: var(--color-status-bloque-bg); }

/* ── Assign chip ── */
.assigned-chip { display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.8125rem; font-weight: 500; color: var(--color-text-primary); }
.assigned-icon { width: 13px; height: 13px; color: var(--color-text-secondary); }

/* ── Modals ── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal-dialog {
  background: var(--color-bg-card); border-radius: 12px;
  padding: 1.5rem; width: 420px; max-width: 95vw;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.modal-title    { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0 0 0.25rem; }
.modal-subtitle { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0 0 1rem; }
.modal-label    { display: block; font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); margin-bottom: 0.375rem; text-transform: uppercase; letter-spacing: 0.04em; }
.required-star  { color: var(--color-status-bloque); margin-left: 2px; }
.modal-error    { font-size: 0.8125rem; color: var(--color-status-bloque); margin: 0.5rem 0 0; }
.modal-wrk09-warn { background: var(--color-risk-high-bg); color: var(--color-risk-high); border-radius: 7px; padding: 0.5rem 0.75rem; font-size: 0.8125rem; font-weight: 500; margin-bottom: 0.75rem; }
.modal-actions  { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem; }
.btn-transition-confirm {
  display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.4375rem 1rem; border: none; border-radius: 8px;
  font-size: 0.8125rem; font-weight: 600; cursor: pointer;
}
.btn-transition-confirm--success { background: var(--color-status-valide);   color: #fff; }
.btn-transition-confirm--warning { background: var(--color-status-vigilance); color: #fff; }
.btn-transition-confirm--danger  { background: var(--color-status-bloque);   color: #fff; }
.btn-transition-confirm--neutral { background: var(--color-text-secondary);  color: #fff; }
.btn-transition-confirm--primary { background: var(--color-sidebar-bg); color: #fff; }
.btn-transition-confirm:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-transition-confirm:hover:not(:disabled) { opacity: 0.88; }
.assign-loading { padding: 1rem 0; text-align: center; font-size: 0.875rem; color: var(--color-text-secondary); }

/* ── Error banner ── */
.analyse-error-banner {
  margin: -0.75rem 0 0.75rem; padding: 0.5rem 1rem;
  background: var(--color-risk-high-bg); color: var(--color-risk-high);
  border-radius: 8px; font-size: 0.8125rem; font-weight: 500;
}

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 0.9s linear infinite; }
</style>
