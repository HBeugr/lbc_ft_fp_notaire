# Transfert des modifications LBC/FT/FP — Immobilier → Notaire

**Projet source (référence) :** `lbcft-platform` (assujetti immobilier/foncier), migrations head = 0038
**Projet cible :** `notaire-platform`, migrations head = 0006
**Date :** 2026-06-15

> Ce document liste les corrections et fonctionnalités développées sur la plateforme immobilière et **leur applicabilité au notaire**. On garde l'identité **notariale** : actes notariés (ventes, successions, donations, constitutions de sociétés) à la place des « biens immobiliers », terminologie notaire.

## Modèle de rôles (décision actée)

On **garde** les rôles existants du notaire et on **ajoute** 2 rôles (parité immo) :

| Rôle notaire | Équivalent immo | Rôle |
|---|---|---|
| `admin` | admin | Administration |
| `notaire_principal` | dirigeant (DG) | Autorisation finale, validation DOS finale, transmission CENTIF |
| `responsable_conformite` | RC | Préparation/contrôle conformité, 1re validation DOS |
| `clercs` | (agents) | Opérationnel, saisie KYC |
| `declarant_centif` *(ajouté)* | declarant_centif | Déclarant CENTIF, distinct du RC (Art. 100) |
| `autre_utilisateur` *(ajouté)* | autre_utilisateur | Lecture seule / accès restreint |

**Double validation DOS :** `responsable_conformite` (RC) prépare et valide la conformité → `notaire_principal` (DG) autorise et transmet à la CENTIF.

---

## Légende statut transfert

- ✅ **Déjà présent** dans le notaire — rien à faire
- 🟠 **Partiel** — présent mais à enrichir
- 🔴 **À implémenter** — absent du notaire
- ⚪ **Hors périmètre** — décision produit (retiré)

---

## Priorité 1 — KYC (Identification client)

| Item | Statut notaire | Action |
|---|---|---|
| KYC-PP état civil enrichi (nom jeune fille, parents, coordonnées, matrimonial, profession 5 ans) | ✅ | — (déjà plus riche que l'immo) |
| KYC-PP `objet_relation` (obligatoire) | 🔴 | Ajouter colonne + champ obligatoire stepper |
| Dossier `nature_relation` (ponctuelle/durable → force Type B) | 🔴 | Ajouter colonne + sélecteur création dossier |
| KYC-PM `objet_social` (obligatoire) | 🔴 | Colonne + textarea Step 2 |
| KYC-PM `ca_annuel`, `effectif`, `pays_operations` | 🔴 | Colonnes + inputs Step 2 |
| KYC-PM RCCM validité 90j (`date_emission_rccm` → `date_expiration_rccm` + alerte `RCCM_EXPIRE`) | 🔴 | Colonnes + calcul au save + alerte |
| KYC-PM docs (`statuts_doc_ref`, `declaration_origine_fonds_ref`, `pacte_associes`) | 🔴 | Colonnes + uploads |
| KYC-PM `representant_statut_ppe` + détail représentant | 🟠 | Enrichir (DDN, lieu, pièce, est PPE ?) |
| KYC-BE `pourcentage_droits_vote` (distinct de détention) | 🔴 | Colonne + champ |
| KYC-BE `entite_intermediaire` (contrôle indirect) | 🔴 | Colonnes |
| KYC-BE registre BE greffe (`registre_be_*`) | 🔴 | 4 colonnes + UI |
| KYC-BE filtrage SFC structuré (`filtrage_sfc_*`) | 🔴 | 4 colonnes + UI |
| KYC-BE `statut_validation` + gate « PM non validable sans ≥1 BE validé » | 🔴 | Colonne + règle service |
| KYC-PPE 10 sections (presse négative, exposition, mesures, validation RC) | 🟠 → 🔴 | Enrichir le modèle (4 flags actuels → presse + exposition + validation) |

## Priorité 2 — DOS (Déclaration d'Opération Suspecte)

| Item | Statut notaire | Action |
|---|---|---|
| Création DOS depuis dossier | ✅ | — |
| `nature_infraction` (Blanchiment / FT / Prolifération) | 🔴 | Colonne + champs stepper |
| `statut_operation` (exécutée / en cours / tentée) | 🔴 | Colonne + champ |
| `date_detection` | 🔴 | Colonne + champ |
| Cycle statut complet (brouillon → en_validation → transmise/classée) | 🟠 | Aligner (4→5 états) |
| Double validation RC + DG (`valide_par_rc`, `valide_par_dg`) | 🔴 | Colonnes + endpoints |
| Décision motivée (`decision`, `motif_classement`) | 🔴 | Colonnes |
| Transmission CENTIF (`date_transmission_centif`, `transmis_par`) | 🟠 | Distinguer du simple « soumis » |
| Accusé réception + **alerte J+15** | 🟠 | Ajouter flag `accuse_alerte_j15_envoyee` + check |
| **Blocage auto du dossier à la création DOS** | 🔴 | Service + alerte `DOSSIER_BLOQUE` |
| Endpoints `/valider`, `/transmettre`, `/classer` | 🔴 | Ajouter |
| Confidentialité Art. 63 (guard rôle, pas de fuite DTO) | 🟠 | Guard `_require_dos_role` dédié |
| Validation par étape (bouton désactivé si champ vide) | 🟠 | Rendre montant + champs clés obligatoires |

## Priorité 3 — Criblage / Sanctions

| Item | Statut notaire | Action |
|---|---|---|
| Listes UEMOA (GIABA/BCEAO/OFAC/UE) + upload Admin | ✅ | — |
| Parser PDF/HTML/CSV + normalisation nom/DDN/lieu | ✅ | — |
| Criblage auto KYC (PP + BE) + T3 blocage | ✅ | — |
| Alerte listes périmées >95j | 🟠 | Vérifier type d'alerte dédié |
| **Listes prolifération M1.2** (ONU_PROLIFERATION, OFAC_WMD, UE_PROLIFERATION, CENTIF_FP) | 🔴 | Étendre enum `type_liste` + option upload |
| Alerte `PROLIFERATION_MATCH` | 🔴 | Ajouter type d'alerte |
| Listes GAFI pays (noire/grise → risque pays) | 🔴 | Absent des deux projets — backlog |

---

## Autres modules (parité immo, hors priorités immédiates)

| Module | Statut notaire | Note |
|---|---|---|
| **Gel des avoirs** | ⚪ **Retiré** | Décision produit : supprimé (blocage assuré par statut dossier) |
| Alertes temps réel SSE + badge + onglets Tous/Mes dossiers | 🟠 | À vérifier/aligner |
| Triggers | ✅ | Notaire = T1–T6 absolutoires (modèle propre, ≠ immo T1–T7) |
| Workflow & assignation hiérarchique intra-département | 🟠 | Présent (assignation Notaire/Clerc) |
| 2FA TOTP (notaire_principal / RC) | ✅ | Présent |
| Déconnexion auto 15 min | 🟠 | À vérifier |
| Chiffrement au repos AES-256 | 🔴 | Écart immo non résolu — à prévoir |
| Registres légaux alimentés + export PDF/Excel | 🟠 | À vérifier |
| Dashboard KPI ciblés | 🟠 | À adapter au notariat |

---

## Suivi d'implémentation (notaire)

> Mis à jour au fil des lots. Migrations auto-appliquées au démarrage (`alembic upgrade head`, head = **0011**).

- [x] **Lot 0 — Suppression module Gel** : `gel.py`/`gel_repo.py`/`schemas/gel.py`/`DossiersGelsView.vue` supprimés ; colonnes `gel_phase`/`gel_notes` retirées (migration 0007) ; `is_bloque` conservé ; nav/router/UsersView nettoyés.
- [x] **Lot 0 — Rôles** : `declarant_centif` + `autre_utilisateur` ajoutés (migration 0008). Double validation DOS = RC (`responsable_conformite`) → DG (`notaire_principal`).
- [x] **Lot 1 — DOS workflow CENTIF** (backend complet, migration 0009) : `statut_operation`, `date_detection`, cycle `brouillon→en_validation→validee_rc→transmise/classee`, double validation RC+DG distincte (Art. 100), `decision`/`motif_classement`, transmission CENTIF, **alerte J+15**, **blocage auto** du dossier à la création (`DOSSIER_BLOQUE`). Endpoints `soumettre|valider|transmettre|classer|accuse-recu`, guard `require_dos_access`. Méthodes service front ajoutées. 🟡 Vues DOS à reconcilier (schéma immo fantôme — API prête).
- [x] **Lot 3 — Criblage prolifération M1.2** (migration 0010) : types `ONU_PROLIFERATION`/`OFAC_WMD`/`UE_PROLIFERATION`/`CENTIF_FP` (modèle + router + UI upload) ; alerte `PROLIFERATION_MATCH` (escalade auto liste FP).
- [x] **Lot 2 — KYC** (backend complet, migration 0011) : dossier `nature_relation` (câblé au formulaire), KYC-PP `objet_relation`, KYC-PM `objet_social`/RCCM 90j (`RCCM_EXPIRE`)/`representant_statut_ppe`, KYC-BE droits de vote/entité intermédiaire/registre BE/filtrage SFC/validation, KYC-PPE presse négative/exposition/validation. 🟡 Steppers PM/BE/PPE à câbler (API prête) ; gate « ≥1 BE validé » à brancher.

### Reste à faire
- Reconciliation des vues DOS au schéma backend notaire.
- Câblage frontend des champs KYC enrichis (steppers PM/BE/PPE) + gate « ≥1 BE validé » pour valider une PM.
- Chiffrement au repos (AES-256) — écart commun aux deux projets.
- Validation des migrations en environnement Docker (indisponible lors du développement).
