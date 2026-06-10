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
          {{ dossier.type_client === 'PP' ? clientName : dossier.kyc_pm?.raison_sociale ?? dossier.reference }}
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
        description="Client figurant sur une liste de sanctions (OFAC / UE-CSNU / GIABA-BCEAO) — blocage et gel des avoirs, DOS obligatoire."
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

      <!-- Panneau de transitions -->
      <div v-if="availableTransitions.length || isRC" class="transition-bar">
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
          <span class="meta-value">{{ OPERATION_LABELS[dossier.type_operation] ?? dossier.type_operation }}</span>
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
              {{ assignedUserName || dossier.assigned_to.slice(0, 8) + '…' }}
            </span>
            <span v-else class="meta-value" style="color:var(--color-text-muted);font-style:italic">Non assigné</span>
          </span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Créé le</span>
          <span class="meta-value">{{ formatDate(dossier.created_at) }}</span>
        </div>
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
            <div v-if="!ppEdit" style="display:flex;gap:0.5rem">
              <button class="btn-ghost btn-sm" @click="startPPEdit">Modifier</button>
            </div>
            <div v-else style="display:flex;gap:0.5rem;align-items:center">
              <button class="btn-ghost btn-sm" @click="ppEdit=false;ppError=''">Annuler</button>
              <button class="btn-primary btn-sm-primary" :disabled="ppSaving" @click="savePP">
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
              <div class="info-item"><span class="info-label">Date de naissance</span><span class="info-value">{{ dossier.kyc_pp.date_naissance ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Lieu de naissance</span><span class="info-value">{{ dossier.kyc_pp.lieu_naissance ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Nationalité</span><span class="info-value">{{ dossier.kyc_pp.nationalite ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Pièce d'identité</span><span class="info-value">{{ dossier.kyc_pp.type_piece_identite ?? '—' }} {{ dossier.kyc_pp.numero_piece ?? '' }}</span></div>
              <div class="info-item"><span class="info-label">Situation professionnelle</span><span class="info-value">{{ dossier.kyc_pp.situation_professionnelle ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Revenus annuels</span><span class="info-value">{{ dossier.kyc_pp.revenus_annuels ? formatAmount(dossier.kyc_pp.revenus_annuels) : '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Adresse</span><span class="info-value">{{ dossier.kyc_pp.adresse_residence ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Statut PPE</span><span class="info-value" :class="{ 'ppe-flag': dossier.kyc_pp.statut_ppe }">{{ dossier.kyc_pp.statut_ppe ? '⚠ PPE' : 'Non' }}</span></div>
              <div class="info-item"><span class="info-label">Opération tiers</span><span class="info-value">{{ dossier.kyc_pp.est_compte_tiers ? 'Oui — mandant renseigné' : 'Non' }}</span></div>
            </div>
            <template v-if="dossier.kyc_pp.est_compte_tiers && dossier.kyc_pp.mandant_info">
              <h4 class="subsection-title">Mandant (opération pour compte de tiers)</h4>
              <div class="mandant-detail-block">
                <div class="info-grid">
                  <div class="info-item"><span class="info-label">Nom & Prénoms</span><span class="info-value">{{ (dossier.kyc_pp.mandant_info['nom'] || '') + (dossier.kyc_pp.mandant_info['prenoms'] ? ' ' + dossier.kyc_pp.mandant_info['prenoms'] : '') || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Date de naissance</span><span class="info-value">{{ dossier.kyc_pp.mandant_info['date_naissance'] || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Lieu de naissance</span><span class="info-value">{{ dossier.kyc_pp.mandant_info['lieu_naissance'] || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Lien avec le client</span><span class="info-value">{{ dossier.kyc_pp.mandant_info['lien'] || '—' }}</span></div>
                  <div class="info-item"><span class="info-label">Contact</span><span class="info-value">{{ dossier.kyc_pp.mandant_info['contact'] || '—' }}</span></div>
                </div>
              </div>
            </template>
          </template>

          <!-- Edit mode -->
          <template v-else>
            <div class="edit-grid">
              <div class="edit-field">
                <label class="info-label">Nom <span class="req">*</span></label>
                <input v-model="ppForm.nom" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Prénoms <span class="req">*</span></label>
                <input v-model="ppForm.prenoms" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Date de naissance</label>
                <input v-model="ppForm.date_naissance" type="date" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Lieu de naissance</label>
                <input v-model="ppForm.lieu_naissance" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Nationalité</label>
                <input v-model="ppForm.nationalite" type="text" class="field-input" />
              </div>
              <div class="edit-field edit-field--full">
                <label class="info-label">Adresse de résidence</label>
                <input v-model="ppForm.adresse_residence" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Type de pièce d'identité</label>
                <select v-model="ppForm.type_piece_identite" class="field-input">
                  <option value="">— Choisir —</option>
                  <option>Carte nationale d'identité</option>
                  <option>Passeport</option>
                  <option>Titre de séjour</option>
                  <option>Autre</option>
                </select>
              </div>
              <div class="edit-field">
                <label class="info-label">Numéro de pièce</label>
                <input v-model="ppForm.numero_piece" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Date d'expiration pièce</label>
                <input v-model="ppForm.date_expiration_piece" type="date" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Pays d'émission</label>
                <input v-model="ppForm.pays_emission_piece" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Situation professionnelle</label>
                <input v-model="ppForm.situation_professionnelle" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Revenus annuels (FCFA)</label>
                <input v-model.number="ppForm.revenus_annuels" type="number" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Patrimoine estimé (FCFA)</label>
                <input v-model.number="ppForm.patrimoine_estime" type="number" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Source des revenus</label>
                <input v-model="ppForm.sources_revenus" type="text" class="field-input" />
              </div>
              <div class="edit-field edit-field--full">
                <label class="info-label">Origine des fonds</label>
                <input v-model="ppForm.origine_fonds" type="text" class="field-input" />
              </div>
              <div class="edit-field edit-field--full">
                <label class="info-label">Objet de la relation</label>
                <input v-model="ppForm.objet_relation" type="text" class="field-input" />
              </div>
              <div class="edit-field edit-field--full" style="display:flex;align-items:center;gap:0.75rem">
                <input type="checkbox" id="ppStatutPPE" v-model="ppForm.statut_ppe" style="width:1rem;height:1rem" />
                <label for="ppStatutPPE" class="info-label" style="margin:0;cursor:pointer">Statut PPE (Personne Politiquement Exposée)</label>
              </div>
              <div class="edit-field edit-field--full" style="display:flex;align-items:center;gap:0.75rem">
                <input type="checkbox" id="ppEstCompteTiers" v-model="ppForm.est_compte_tiers" style="width:1rem;height:1rem" />
                <label for="ppEstCompteTiers" class="info-label" style="margin:0;cursor:pointer">Opération pour compte de tiers (mandant)</label>
              </div>
            </div>

            <template v-if="ppForm.est_compte_tiers">
              <h4 class="subsection-title" style="margin-top:1.25rem">Informations du mandant</h4>
              <div class="edit-grid">
                <div class="edit-field">
                  <label class="info-label">Nom du mandant</label>
                  <input v-model="ppMandant.nom" type="text" class="field-input" />
                </div>
                <div class="edit-field">
                  <label class="info-label">Prénoms du mandant</label>
                  <input v-model="ppMandant.prenoms" type="text" class="field-input" />
                </div>
                <div class="edit-field">
                  <label class="info-label">Date de naissance</label>
                  <input v-model="ppMandant.date_naissance" type="date" class="field-input" />
                </div>
                <div class="edit-field">
                  <label class="info-label">Lieu de naissance</label>
                  <input v-model="ppMandant.lieu_naissance" type="text" class="field-input" />
                </div>
                <div class="edit-field">
                  <label class="info-label">Lien avec le client</label>
                  <input v-model="ppMandant.lien" type="text" class="field-input" />
                </div>
                <div class="edit-field">
                  <label class="info-label">Contact</label>
                  <input v-model="ppMandant.contact" type="text" class="field-input" />
                </div>
              </div>
            </template>
          </template>
        </template>
        <div v-else class="empty-section">
          <p>Le formulaire KYC-PP n'a pas encore été rempli.</p>
          <button v-if="dossier.statut === 'brouillon'" class="btn-primary btn-sm-primary" style="margin-top:1rem" @click="router.push({ name: 'kyc-edit', params: { id: dossier.id } })">
            Remplir le formulaire KYC
          </button>
        </div>
      </div>

      <!-- ── KYC-PM — Informations société ── -->
      <div v-else-if="activeSection === 'kyc-pm'" class="card section-card">
        <template v-if="dossier.kyc_pm">
          <div class="section-header">
            <h3 class="section-title">Informations société</h3>
            <div v-if="!pmEdit" style="display:flex;gap:0.5rem">
              <button class="btn-ghost btn-sm" @click="startPMEdit">Modifier</button>
            </div>
            <div v-else style="display:flex;gap:0.5rem;align-items:center">
              <button class="btn-ghost btn-sm" @click="pmEdit=false;pmError=''">Annuler</button>
              <button class="btn-primary btn-sm-primary" :disabled="pmSaving" @click="savePMCompany">
                <svg v-if="pmSaving" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                {{ pmSaving ? '…' : 'Enregistrer' }}
              </button>
            </div>
          </div>
          <p v-if="pmError" class="save-error">{{ pmError }}</p>

          <!-- View mode -->
          <template v-if="!pmEdit">
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Raison sociale</span><span class="info-value">{{ dossier.kyc_pm.raison_sociale }}</span></div>
              <div class="info-item"><span class="info-label">Forme juridique</span><span class="info-value">{{ dossier.kyc_pm.forme_juridique ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">RCCM</span><span class="info-value mono">{{ dossier.kyc_pm.rccm ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">NIF</span><span class="info-value mono">{{ dossier.kyc_pm.nif ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Pays d'enregistrement</span><span class="info-value">{{ dossier.kyc_pm.pays_enregistrement ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Date de création</span><span class="info-value">{{ dossier.kyc_pm.date_creation ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Capital social</span><span class="info-value">{{ dossier.kyc_pm.capital_social ? formatAmount(dossier.kyc_pm.capital_social) : '—' }}</span></div>
              <div class="info-item"><span class="info-label">Secteur d'activité</span><span class="info-value">{{ dossier.kyc_pm.secteur_activite ?? '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Siège social</span><span class="info-value">{{ dossier.kyc_pm.adresse_siege ?? '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Description de l'activité</span><span class="info-value">{{ dossier.kyc_pm.description_activite ?? '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Objet de la relation</span><span class="info-value">{{ dossier.kyc_pm.objet_relation ?? '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Origine des fonds</span><span class="info-value">{{ dossier.kyc_pm.origine_fonds ?? '—' }}</span></div>
            </div>
          </template>

          <!-- Edit mode -->
          <template v-else>
            <div class="edit-grid">
              <div class="edit-field edit-field--full">
                <label class="info-label">Raison sociale <span class="req">*</span></label>
                <input v-model="pmForm.raison_sociale" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Forme juridique</label>
                <input v-model="pmForm.forme_juridique" type="text" class="field-input" placeholder="SA, SARL, SAS…" />
              </div>
              <div class="edit-field">
                <label class="info-label">RCCM</label>
                <input v-model="pmForm.rccm" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">NIF</label>
                <input v-model="pmForm.nif" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Pays d'enregistrement</label>
                <input v-model="pmForm.pays_enregistrement" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Date de création</label>
                <input v-model="pmForm.date_creation" type="date" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Capital social (FCFA)</label>
                <input v-model.number="pmForm.capital_social" type="number" min="0" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Secteur d'activité</label>
                <input v-model="pmForm.secteur_activite" type="text" class="field-input" />
              </div>
              <div class="edit-field edit-field--full">
                <label class="info-label">Siège social</label>
                <textarea v-model="pmForm.adresse_siege" class="field-textarea" rows="2" />
              </div>
              <div class="edit-field edit-field--full">
                <label class="info-label">Description de l'activité</label>
                <textarea v-model="pmForm.description_activite" class="field-textarea" rows="2" />
              </div>
              <div class="edit-field edit-field--full">
                <label class="info-label">Objet de la relation</label>
                <textarea v-model="pmForm.objet_relation" class="field-textarea" rows="2" />
              </div>
              <div class="edit-field edit-field--full">
                <label class="info-label">Origine des fonds</label>
                <textarea v-model="pmForm.origine_fonds" class="field-textarea" rows="2" />
              </div>
            </div>
          </template>
        </template>
        <div v-else class="empty-section">
          <p>Le formulaire KYC-PM n'a pas encore été rempli.</p>
          <button v-if="dossier.statut === 'brouillon'" class="btn-primary btn-sm-primary" style="margin-top:1rem" @click="router.push({ name: 'kyc-edit', params: { id: dossier.id } })">
            Remplir le formulaire KYC
          </button>
        </div>
      </div>

      <!-- ── Représentant légal ── -->
      <div v-else-if="activeSection === 'representant'" class="card section-card">
        <template v-if="dossier.kyc_pm">
          <div class="section-header">
            <h3 class="section-title">Représentant légal</h3>
            <div v-if="!repEdit" style="display:flex;gap:0.5rem">
              <button class="btn-ghost btn-sm" @click="startRepEdit">Modifier</button>
            </div>
            <div v-else style="display:flex;gap:0.5rem;align-items:center">
              <button class="btn-ghost btn-sm" @click="repEdit=false;repError=''">Annuler</button>
              <button class="btn-primary btn-sm-primary" :disabled="repSaving" @click="saveRep">
                <svg v-if="repSaving" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                {{ repSaving ? '…' : 'Enregistrer' }}
              </button>
            </div>
          </div>
          <p v-if="repError" class="save-error">{{ repError }}</p>

          <template v-if="!repEdit">
            <div v-if="!dossier.kyc_pm.representant_nom" class="empty-section" style="padding:1.5rem 0">
              <p>Aucun représentant légal renseigné.</p>
              <button class="btn-ghost btn-sm" style="margin-top:0.5rem" @click="startRepEdit">Renseigner</button>
            </div>
            <div v-else class="info-grid">
              <div class="info-item"><span class="info-label">Nom</span><span class="info-value">{{ dossier.kyc_pm.representant_nom ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Prénoms</span><span class="info-value">{{ dossier.kyc_pm.representant_prenoms ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Fonction</span><span class="info-value">{{ dossier.kyc_pm.representant_fonction ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Nationalité</span><span class="info-value">{{ dossier.kyc_pm.representant_nationalite ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Type de pièce</span><span class="info-value">{{ dossier.kyc_pm.representant_type_piece ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Numéro de pièce</span><span class="info-value mono">{{ dossier.kyc_pm.representant_numero_piece ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Expiration pièce</span><span class="info-value">{{ dossier.kyc_pm.representant_date_expiration_piece ?? '—' }}</span></div>
              <div class="info-item"><span class="info-label">Date de naissance</span><span class="info-value">{{ dossier.kyc_pm.representant_date_naissance ?? '—' }}</span></div>
              <div class="info-item info-item--full"><span class="info-label">Lieu d'habitation</span><span class="info-value">{{ dossier.kyc_pm.representant_lieu_habitation ?? '—' }}</span></div>
            </div>
          </template>

          <template v-else>
            <div class="edit-grid">
              <div class="edit-field">
                <label class="info-label">Nom <span class="req">*</span></label>
                <input v-model="repForm.representant_nom" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Prénoms <span class="req">*</span></label>
                <input v-model="repForm.representant_prenoms" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Fonction</label>
                <input v-model="repForm.representant_fonction" type="text" class="field-input" placeholder="DG, PDG, Gérant…" />
              </div>
              <div class="edit-field">
                <label class="info-label">Nationalité</label>
                <input v-model="repForm.representant_nationalite" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Type de pièce</label>
                <select v-model="repForm.representant_type_piece" class="field-input">
                  <option value="">— Sélectionner —</option>
                  <option>CNI</option>
                  <option>Passeport</option>
                  <option>Titre de séjour</option>
                  <option>Carte de résident</option>
                </select>
              </div>
              <div class="edit-field">
                <label class="info-label">Numéro de pièce</label>
                <input v-model="repForm.representant_numero_piece" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Expiration pièce</label>
                <input v-model="repForm.representant_date_expiration_piece" type="date" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Date de naissance</label>
                <input v-model="repForm.representant_date_naissance" type="date" class="field-input" />
              </div>
              <div class="edit-field edit-field--full">
                <label class="info-label">Lieu d'habitation</label>
                <input v-model="repForm.representant_lieu_habitation" type="text" class="field-input" placeholder="Ville, Pays" />
              </div>
            </div>
          </template>
        </template>
        <div v-else class="empty-section">
          <p>Le formulaire KYC-PM doit être rempli en premier.</p>
        </div>
      </div>

      <!-- ── Autres dirigeants ── -->
      <div v-else-if="activeSection === 'dirigeants'" class="card section-card">
        <template v-if="dossier.kyc_pm">
          <div class="section-header">
            <h3 class="section-title">Autres dirigeants</h3>
            <div style="display:flex;gap:0.5rem;align-items:center">
              <template v-if="!dirigEdit">
                <button class="btn-ghost btn-sm" @click="startDirigEdit">Modifier</button>
              </template>
              <template v-else>
                <button class="btn-ghost btn-sm btn-add-row" @click="addDirigeant">+ Ajouter</button>
                <button class="btn-ghost btn-sm" @click="dirigEdit=false;dirigError=''">Annuler</button>
                <button class="btn-primary btn-sm-primary" :disabled="dirigSaving" @click="saveDirig">
                  <svg v-if="dirigSaving" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                  {{ dirigSaving ? '…' : 'Enregistrer' }}
                </button>
              </template>
            </div>
          </div>
          <p v-if="dirigError" class="save-error">{{ dirigError }}</p>

          <!-- View mode -->
          <template v-if="!dirigEdit">
            <div v-if="!dossier.kyc_pm.dirigeants?.length" class="empty-section" style="padding:1.5rem 0">
              <p>Aucun autre dirigeant renseigné.</p>
              <button class="btn-ghost btn-sm" style="margin-top:0.5rem" @click="startDirigEdit">Ajouter</button>
            </div>
            <div v-else class="persons-list">
              <div v-for="(d, i) in dossier.kyc_pm.dirigeants" :key="i" class="person-row">
                <div class="person-avatar">{{ (d.nom ?? '')[0]?.toUpperCase() }}{{ (d.prenoms ?? '')[0]?.toUpperCase() }}</div>
                <div class="person-info">
                  <span class="person-name">{{ d.nom }} {{ d.prenoms }}</span>
                  <div class="person-tags">
                    <span v-if="d.fonction" class="person-tag">{{ d.fonction }}</span>
                    <span v-if="d.nationalite" class="person-nat">{{ d.nationalite }}</span>
                    <span v-if="d.date_naissance" class="person-nat">né·e {{ d.date_naissance }}</span>
                    <span v-if="d.lieu_habitation" class="person-nat">{{ d.lieu_habitation }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- Edit mode -->
          <template v-else>
            <div v-if="dirigRows.length === 0" class="empty-section" style="padding:1rem 0">
              <p>Aucun dirigeant — cliquez sur "+ Ajouter".</p>
            </div>
            <div v-for="(d, i) in dirigRows" :key="i" class="entity-edit-block">
              <div class="entity-edit-header">
                <span class="entity-edit-num">Dirigeant {{ i + 1 }}</span>
                <button class="btn-remove-row" @click="removeDirigeant(i)">Supprimer</button>
              </div>
              <div class="edit-grid">
                <div class="edit-field">
                  <label class="info-label">Nom</label>
                  <input v-model="d.nom" type="text" class="field-input" />
                </div>
                <div class="edit-field">
                  <label class="info-label">Prénoms</label>
                  <input v-model="d.prenoms" type="text" class="field-input" />
                </div>
                <div class="edit-field">
                  <label class="info-label">Fonction</label>
                  <input v-model="d.fonction" type="text" class="field-input" placeholder="DG, Administrateur…" />
                </div>
                <div class="edit-field">
                  <label class="info-label">Nationalité</label>
                  <input v-model="d.nationalite" type="text" class="field-input" />
                </div>
                <div class="edit-field">
                  <label class="info-label">Date de naissance</label>
                  <input v-model="d.date_naissance" type="date" class="field-input" />
                </div>
                <div class="edit-field">
                  <label class="info-label">Lieu d'habitation</label>
                  <input v-model="d.lieu_habitation" type="text" class="field-input" placeholder="Ville, Pays" />
                </div>
              </div>
            </div>
          </template>
        </template>
        <div v-else class="empty-section">
          <p>Le formulaire KYC-PM doit être rempli en premier.</p>
        </div>
      </div>

      <!-- ── Actionnaires / BEs ── -->
      <div v-else-if="activeSection === 'actionnaires-be'" class="card section-card">
        <!-- Actionnaires (kyc_pm.beneficiaires_effectifs) -->
        <div class="section-header">
          <h3 class="section-title">Actionnaires / Associés</h3>
          <div style="display:flex;gap:0.5rem;align-items:center">
            <template v-if="!actEdit">
              <button class="btn-ghost btn-sm" @click="startActEdit">Modifier</button>
            </template>
            <template v-else>
              <button class="btn-ghost btn-sm btn-add-row" @click="addActionnaire">+ Ajouter</button>
              <button class="btn-ghost btn-sm" @click="actEdit=false;actError=''">Annuler</button>
              <button class="btn-primary btn-sm-primary" :disabled="actSaving" @click="saveAct">
                <svg v-if="actSaving" class="spin btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                {{ actSaving ? '…' : 'Enregistrer' }}
              </button>
            </template>
          </div>
        </div>
        <p v-if="actError" class="save-error">{{ actError }}</p>

        <!-- View mode actionnaires -->
        <template v-if="!actEdit">
          <div v-if="!dossier.kyc_pm?.beneficiaires_effectifs?.filter((a: any) => a.nom?.trim() || a.prenoms?.trim()).length" class="empty-section" style="padding:1rem 0">
            <p>Aucun actionnaire renseigné.</p>
            <button class="btn-ghost btn-sm" style="margin-top:0.5rem" @click="startActEdit">Ajouter</button>
          </div>
          <div v-else class="persons-list" style="margin-bottom:0.5rem">
            <div v-for="(a, i) in dossier.kyc_pm!.beneficiaires_effectifs!.filter((a: any) => a.nom?.trim() || a.prenoms?.trim())" :key="i" class="person-row">
              <div class="person-avatar">{{ String(a.nom ?? '')[0]?.toUpperCase() }}{{ String(a.prenoms ?? '')[0]?.toUpperCase() }}</div>
              <div class="person-info">
                <span class="person-name">{{ a.nom }} {{ a.prenoms }}</span>
                <div class="person-tags">
                  <span class="person-tag pct-tag">{{ a.pourcentage }}%</span>
                  <span v-if="a.nationalite" class="person-nat">{{ a.nationalite }}</span>
                  <span v-if="a.statut_ppe" class="ppe-mini">PPE</span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Edit mode actionnaires -->
        <template v-else>
          <div v-if="actRows.length === 0" class="empty-section" style="padding:1rem 0">
            <p>Aucun actionnaire — cliquez sur "+ Ajouter".</p>
          </div>
          <div v-for="(a, i) in actRows" :key="i" class="entity-edit-block">
            <div class="entity-edit-header">
              <span class="entity-edit-num">Actionnaire {{ i + 1 }}</span>
              <button class="btn-remove-row" @click="removeActionnaire(i)">Supprimer</button>
            </div>
            <div class="edit-grid">
              <div class="edit-field">
                <label class="info-label">Nom</label>
                <input v-model="a.nom" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Prénoms</label>
                <input v-model="a.prenoms" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">Nationalité</label>
                <input v-model="a.nationalite" type="text" class="field-input" />
              </div>
              <div class="edit-field">
                <label class="info-label">% de détention</label>
                <input v-model.number="a.pourcentage" type="number" min="0" max="100" class="field-input" />
              </div>
              <div class="edit-field" style="display:flex;align-items:center;gap:0.5rem;padding-top:1.25rem">
                <input v-model="a.statut_ppe" type="checkbox" class="checkbox" :id="`ppe-act-${i}`" />
                <label :for="`ppe-act-${i}`" class="info-label" style="margin:0;cursor:pointer">PPE</label>
              </div>
            </div>
          </div>
        </template>

        <!-- BEs formels (KycBEPanel) -->
        <div class="be-separator">
          <h4 class="subsection-title">Bénéficiaires effectifs — KYC-BE</h4>
        </div>
        <KycBEPanel :dossier-id="dossier.id" />
      </div>

      <!-- ── KYC-PPE ── -->
      <div v-else-if="activeSection === 'kyc-ppe'" class="card section-card">
        <div class="section-header">
          <h3 class="section-title">Personnes Politiquement Exposées (PPE)</h3>
          <button
            v-if="ppeSources.length > dossier.kyc_ppe_list.length"
            class="btn-primary btn-sm-primary"
            @click="openPPENew"
          >
            + Créer un KYC-PPE
          </button>
        </div>

        <div v-if="dossier.kyc_ppe_list.length === 0" class="empty-section">
          <p>Aucun formulaire KYC-PPE créé.</p>
          <p v-if="ppeSources.length > 0" style="margin-top:0.25rem;font-size:0.8125rem">{{ ppeSources.length }} PPE détecté(s) — cliquez sur "Créer un KYC-PPE".</p>
        </div>

        <div v-else class="ppe-list">
          <div v-for="ppe in dossier.kyc_ppe_list" :key="ppe.id" class="ppe-row">
            <div class="ppe-row-left">
              <div class="be-avatar">{{ (ppe.nom ?? '')[0] }}{{ (ppe.prenoms ?? '')[0] }}</div>
              <div>
                <p class="ppe-name">{{ ppe.nom }} {{ ppe.prenoms }}</p>
                <p class="ppe-meta">
                  Source : <strong>{{ ppe.source === 'PP' ? 'Personne physique' : 'Bénéficiaire effectif' }}</strong>
                  <span class="sep">·</span>
                  {{ ppe.fonction_actuelle ?? '—' }}
                </p>
              </div>
            </div>
            <div class="ppe-row-right">
              <span v-if="ppe.resultat_presse && ppe.resultat_presse !== 'Negatif'" class="presse-chip" :class="`presse--${ppe.resultat_presse?.toLowerCase()}`">
                Presse {{ ppe.resultat_presse }}
              </span>
              <span class="validation-badge" :class="`validation--${ppe.statut_validation}`">
                {{ VALIDATION_LABELS[ppe.statut_validation ?? 'en_attente'] }}
              </span>
              <button class="btn-ghost btn-sm" @click="router.push({ name: 'kyc-ppe', params: { id: dossier.id, ppeId: ppe.id } })">
                Ouvrir
              </button>
            </div>
          </div>
        </div>

        <div v-if="pendingPPESources.length > 0" class="pending-ppe">
          <p class="pending-label">PPE détectés sans formulaire :</p>
          <div v-for="src in pendingPPESources" :key="src.sourceId" class="pending-row">
            <span class="pending-name">{{ src.nom }} {{ src.prenoms }}</span>
            <span class="pending-source">{{ src.source === 'PP' ? 'Personne physique' : 'BE' }}</span>
            <button class="btn-ghost btn-sm" @click="openPPEForSource(src)">Créer KYC-PPE</button>
          </div>
        </div>
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
                <span v-if="h.statut_precedent" class="statut-chip statut-chip--prev">{{ h.statut_precedent }}</span>
                <span v-if="h.statut_precedent" class="arrow">→</span>
                <span class="statut-chip statut-chip--next">{{ h.statut_suivant }}</span>
              </p>
              <p v-if="h.commentaire" class="historique-comment">{{ h.commentaire }}</p>
              <p class="historique-meta">{{ formatDate(h.created_at) }} · {{ h.auteur_id }}</p>
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
                <p class="dos-ref">{{ dos.reference }}</p>
                <p class="dos-meta">
                  Créée le {{ formatDate(dos.created_at) }}
                  <span v-if="dos.finalized_at"> · Finalisée le {{ formatDate(dos.finalized_at) }}</span>
                </p>
              </div>
            </div>
            <div class="dos-row-right">
              <span class="dos-statut" :class="`dos-statut--${dos.statut}`">
                {{ dos.statut === 'finalisee' ? 'Finalisée' : 'Brouillon' }}
              </span>
              <button class="btn-ghost btn-sm" @click="router.push({ name: 'dos', query: { dosId: dos.id } })">
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
import DocumentsPanel from '@/components/kyc/DocumentsPanel.vue'
import ScoringPanel from '@/components/kyc/ScoringPanel.vue'
import TriggerBanner from '@/components/kyc/TriggerBanner.vue'
import { dossiersService, type DossierOut, type CommentaireOut, type HistoriqueOut, type StatutDossier, type KycPMData, type KycPPData, TYPE_OPERATION_LABELS } from '@/services/dossiers'
import { dosService, type DosOut } from '@/services/dos'
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
    const ppeCount = dossier.value.kyc_ppe_list?.length ?? 0
    tabs.push({ id: 'kyc-ppe', label: ppeCount > 0 ? `PPE ⚠ (${ppeCount})` : 'PPE' })
  } else {
    tabs.push({ id: 'kyc-pm', label: 'KYC Personne morale' })
    tabs.push({ id: 'representant', label: 'Représentant légal' })
    tabs.push({ id: 'dirigeants', label: 'Autres dirigeants' })
    const beCount = dossier.value.kyc_be_list?.length ?? 0
    tabs.push({ id: 'actionnaires-be', label: `Actionnaires / BEs (${beCount})` })
    const ppeCount = dossier.value.kyc_ppe_list?.length ?? 0
    tabs.push({ id: 'kyc-ppe', label: ppeCount > 0 ? `PPE (${ppeCount})` : 'PPE' })
  }
  if (!isAgent.value) {
    tabs.push({ id: 'scoring', label: 'Scoring risque' })
  }
  tabs.push({ id: 'documents', label: 'Documents' })
  tabs.push({ id: 'historique', label: 'Historique' })
  tabs.push({ id: 'dos', label: 'DOS' })
  return tabs
})

onMounted(async () => {
  try {
    dossier.value = await dossiersService.get(route.params.id as string)
    activeSection.value = dossier.value.type_client === 'PP' ? 'kyc-pp' : 'kyc-pm'
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
      const r = await dosService.list(id)
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

// ── PP edit ───────────────────────────────────────────────────────────────────

const ppEdit   = ref(false)
const ppForm   = ref<Partial<KycPPData>>({})
const ppMandant = ref<Record<string, string>>({})
const ppSaving = ref(false)
const ppError  = ref('')

function startPPEdit() {
  ppForm.value    = { ...dossier.value!.kyc_pp }
  ppMandant.value = { ...(dossier.value!.kyc_pp?.mandant_info ?? {}) }
  ppEdit.value    = true
  ppError.value   = ''
}

async function savePP() {
  if (!dossier.value) return
  ppSaving.value = true
  ppError.value  = ''
  try {
    const f = ppForm.value
    await dossiersService.saveKycPP(dossier.value.id, 5, {
      nom:                       f.nom,
      prenoms:                   f.prenoms,
      date_naissance:            f.date_naissance,
      lieu_naissance:            f.lieu_naissance,
      nationalite:               f.nationalite,
      adresse_residence:         f.adresse_residence,
      type_piece_identite:       f.type_piece_identite,
      numero_piece:              f.numero_piece,
      date_expiration_piece:     f.date_expiration_piece,
      pays_emission_piece:       f.pays_emission_piece,
      situation_professionnelle: f.situation_professionnelle,
      revenus_annuels:           f.revenus_annuels,
      patrimoine_estime:         f.patrimoine_estime,
      sources_revenus:           f.sources_revenus,
      origine_fonds:             f.origine_fonds,
      objet_relation:            f.objet_relation,
      statut_ppe:                f.statut_ppe,
      est_compte_tiers:          f.est_compte_tiers,
      mandant_info:              f.est_compte_tiers ? ppMandant.value : null,
    })
    dossier.value = await dossiersService.get(dossier.value.id)
    ppEdit.value  = false
  } catch (e: any) {
    ppError.value = e?.response?.data?.detail ?? 'Erreur lors de la sauvegarde.'
  } finally {
    ppSaving.value = false
  }
}

// ── PM Company edit ───────────────────────────────────────────────────────────

const pmEdit = ref(false)
const pmForm = ref<Partial<KycPMData>>({})
const pmSaving = ref(false)
const pmError = ref('')

function startPMEdit() {
  pmForm.value = { ...dossier.value!.kyc_pm }
  pmEdit.value = true
  pmError.value = ''
}

async function savePMCompany() {
  if (!dossier.value) return
  pmSaving.value = true
  pmError.value = ''
  try {
    const f = pmForm.value
    await dossiersService.saveKycPM(dossier.value.id, 1, {
      raison_sociale:       f.raison_sociale,
      forme_juridique:      f.forme_juridique,
      rccm:                 f.rccm,
      nif:                  f.nif,
      date_creation:        f.date_creation,
      pays_enregistrement:  f.pays_enregistrement,
      adresse_siege:        f.adresse_siege,
      secteur_activite:     f.secteur_activite,
      description_activite: f.description_activite,
      capital_social:       f.capital_social,
      objet_relation:       f.objet_relation,
      origine_fonds:        f.origine_fonds,
    })
    dossier.value = await dossiersService.get(dossier.value.id)
    pmEdit.value = false
  } catch (e: any) {
    pmError.value = e?.response?.data?.detail ?? 'Erreur lors de la sauvegarde.'
  } finally {
    pmSaving.value = false
  }
}

// ── Représentant légal edit ───────────────────────────────────────────────────

const repEdit = ref(false)
const repForm = ref<Partial<KycPMData>>({})
const repSaving = ref(false)
const repError = ref('')

function startRepEdit() {
  repForm.value = { ...dossier.value!.kyc_pm }
  repEdit.value = true
  repError.value = ''
}

async function saveRep() {
  if (!dossier.value) return
  repSaving.value = true
  repError.value = ''
  try {
    const f = repForm.value
    await dossiersService.saveKycPM(dossier.value.id, 3, {
      representant_nom:                    f.representant_nom,
      representant_prenoms:                f.representant_prenoms,
      representant_fonction:               f.representant_fonction,
      representant_nationalite:            f.representant_nationalite,
      representant_type_piece:             f.representant_type_piece,
      representant_numero_piece:           f.representant_numero_piece,
      representant_date_expiration_piece:  f.representant_date_expiration_piece,
      representant_date_naissance:         f.representant_date_naissance,
      representant_lieu_habitation:        f.representant_lieu_habitation,
    })
    dossier.value = await dossiersService.get(dossier.value.id)
    repEdit.value = false
  } catch (e: any) {
    repError.value = e?.response?.data?.detail ?? 'Erreur lors de la sauvegarde.'
  } finally {
    repSaving.value = false
  }
}

// ── Dirigeants edit ───────────────────────────────────────────────────────────

type DirigeantRow = { nom: string; prenoms: string; fonction: string; nationalite: string; date_naissance: string; lieu_habitation: string }

const dirigEdit  = ref(false)
const dirigRows  = ref<DirigeantRow[]>([])
const dirigSaving = ref(false)
const dirigError  = ref('')

function startDirigEdit() {
  dirigRows.value = (dossier.value!.kyc_pm?.dirigeants ?? []).map((d: any) => ({
    nom:             d.nom ?? '',
    prenoms:         d.prenoms ?? '',
    fonction:        d.fonction ?? '',
    nationalite:     d.nationalite ?? '',
    date_naissance:  d.date_naissance ?? '',
    lieu_habitation: d.lieu_habitation ?? '',
  }))
  dirigEdit.value = true
  dirigError.value = ''
}

function addDirigeant() {
  dirigRows.value.push({ nom: '', prenoms: '', fonction: '', nationalite: '', date_naissance: '', lieu_habitation: '' })
}

function removeDirigeant(i: number) {
  dirigRows.value.splice(i, 1)
}

async function saveDirig() {
  if (!dossier.value) return
  dirigSaving.value = true
  dirigError.value = ''
  try {
    await dossiersService.saveKycPM(dossier.value.id, 3, {
      dirigeants: dirigRows.value.filter(d => d.nom.trim() || d.prenoms.trim()),
    })
    dossier.value = await dossiersService.get(dossier.value.id)
    dirigEdit.value = false
  } catch (e: any) {
    dirigError.value = e?.response?.data?.detail ?? 'Erreur lors de la sauvegarde.'
  } finally {
    dirigSaving.value = false
  }
}

// ── Actionnaires edit ─────────────────────────────────────────────────────────

type ActionnaireRow = { nom: string; prenoms: string; nationalite: string; pourcentage: number; statut_ppe: boolean }

const actEdit  = ref(false)
const actRows  = ref<ActionnaireRow[]>([])
const actSaving = ref(false)
const actError  = ref('')

function startActEdit() {
  actRows.value = (dossier.value!.kyc_pm?.beneficiaires_effectifs ?? []).map((a: any) => ({
    nom:         a.nom ?? '',
    prenoms:     a.prenoms ?? '',
    nationalite: a.nationalite ?? '',
    pourcentage: a.pourcentage ?? 0,
    statut_ppe:  a.statut_ppe ?? false,
  }))
  actEdit.value = true
  actError.value = ''
}

function addActionnaire() {
  actRows.value.push({ nom: '', prenoms: '', nationalite: '', pourcentage: 0, statut_ppe: false })
}

function removeActionnaire(i: number) {
  actRows.value.splice(i, 1)
}

async function saveAct() {
  if (!dossier.value) return
  actSaving.value = true
  actError.value = ''
  try {
    await dossiersService.saveKycPM(dossier.value.id, 4, {
      beneficiaires_effectifs: actRows.value.filter(a => a.nom.trim() || a.prenoms.trim()),
    })
    dossier.value = await dossiersService.get(dossier.value.id)
    actEdit.value = false
  } catch (e: any) {
    actError.value = e?.response?.data?.detail ?? 'Erreur lors de la sauvegarde.'
  } finally {
    actSaving.value = false
  }
}

// ── PPE ───────────────────────────────────────────────────────────────────────

const VALIDATION_LABELS: Record<string, string> = {
  en_attente: 'En attente RC', valide: 'Validé', rejete: 'Rejeté',
}

type PPESource = { source: 'PP' | 'BE'; sourceId: string; nom: string; prenoms: string }

const ppeSources = computed((): PPESource[] => {
  if (!dossier.value) return []
  const sources: PPESource[] = []
  if (dossier.value.kyc_pp?.statut_ppe && dossier.value.kyc_pp.id) {
    sources.push({ source: 'PP', sourceId: dossier.value.kyc_pp.id, nom: dossier.value.kyc_pp.nom ?? '', prenoms: dossier.value.kyc_pp.prenoms ?? '' })
  }
  for (const be of dossier.value.kyc_be_list ?? []) {
    if (be.statut_ppe && be.id) {
      sources.push({ source: 'BE', sourceId: be.id, nom: be.nom ?? '', prenoms: be.prenoms ?? '' })
    }
  }
  return sources
})

const pendingPPESources = computed((): PPESource[] => {
  if (!dossier.value) return []
  const existingSourceIds = new Set((dossier.value.kyc_ppe_list ?? []).map(p => p.source_id))
  return ppeSources.value.filter(s => !existingSourceIds.has(s.sourceId))
})

function openPPENew() {
  if (pendingPPESources.value.length > 0) openPPEForSource(pendingPPESources.value[0])
}

function openPPEForSource(src: PPESource) {
  router.push({
    name: 'kyc-ppe-new',
    params: { id: dossier.value!.id },
    query: { source: src.source, sourceId: src.sourceId, nom: src.nom, prenoms: src.prenoms },
  })
}

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
  const hasKyc = d.type_client === 'PP' ? !!d.kyc_pp?.nom : !!d.kyc_pm?.raison_sociale
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
const ALL_ROLES        = [...CLERCS_ROLES, ...CONFORMITE_ROLES]
// Seuls admin et notaire_principal peuvent assigner un dossier
const ASSIGNER_ROLES   = ['admin', 'notaire_principal']

const isAgent    = computed(() => CLERCS_ROLES.includes(auth.user?.role ?? ''))
const isRC       = computed(() => CONFORMITE_ROLES.includes(auth.user?.role ?? ''))
const canAssign  = computed(() => ASSIGNER_ROLES.includes(auth.user?.role ?? ''))
const canCreateDos = computed(() => !!auth.user)

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
    { to: 'actif',   label: 'Mettre en actif', color: 'success', roles: ALL_ROLES },
    { to: 'bloque',  label: 'Bloquer',          color: 'danger',  roles: CONFORMITE_ROLES },
  ],
  actif: [
    { to: 'actif_sous_surveillance', label: 'Mettre sous surveillance', color: 'warning', roles: CONFORMITE_ROLES },
    { to: 'resilie',                 label: 'Résilier',                  color: 'danger',  roles: CONFORMITE_ROLES },
    { to: 'cloture',                 label: 'Clôturer',                  color: 'neutral', roles: CONFORMITE_ROLES },
  ],
  actif_sous_surveillance: [
    { to: 'actif',   label: 'Retour à actif',  color: 'success', roles: CONFORMITE_ROLES },
    { to: 'bloque',  label: 'Bloquer',          color: 'danger',  roles: CONFORMITE_ROLES },
    { to: 'resilie', label: 'Résilier',          color: 'danger',  roles: CONFORMITE_ROLES },
    { to: 'cloture', label: 'Clôturer',          color: 'neutral', roles: CONFORMITE_ROLES },
  ],
  bloque:  [{ to: 'en_analyse', label: 'Réouvrir pour analyse', color: 'success', roles: CONFORMITE_ROLES }],
  traite:  [{ to: 'cloture',  label: 'Clôturer',  color: 'neutral', roles: CONFORMITE_ROLES }],
  resilie: [{ to: 'cloture',  label: 'Clôturer',  color: 'neutral', roles: CONFORMITE_ROLES }],
  cloture: [{ to: 'archive',  label: 'Archiver',   color: 'neutral', roles: CONFORMITE_ROLES }],
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
