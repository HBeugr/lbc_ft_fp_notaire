# Rapport de conformité — notaire-platform vs CDC

**Date :** 2026-06-15
**Référence :** `Notaire_Cahier de Charges LCBFT.docx` (Ordonnance N°2023-875)
**Méthode :** revue de conformité **code ↔ CDC** (lecture du code backend FastAPI + frontend Vue).
**Limite :** Docker indisponible sur la machine → l'application **n'a pas pu être exécutée**. Il s'agit d'un audit statique du code, pas d'un test runtime. À compléter par un test fonctionnel au déploiement.

> Légende : ✅ Conforme · 🟠 Partiel · 🔴 Manquant · ⚠️ Écart à arbitrer

## Synthèse

Le socle réglementaire est largement en place (scoring 10 axes, 6 triggers, T2 = 15M, DOS workflow, révision périodique, registres, audit). Les écarts portent surtout sur : **l'architecture** (pas de desktop/offline/sync), des **champs KYC** du CDC, le **chiffrement au repos**, l'**export PDF DOS**, les **pondérations non configurables**, et quelques **permissions**.

| Module | Conformité | Écart clé |
|---|---|---|
| 1 — KYC | 🟠 | Champs CDC manquants (sexe, tranche revenus, CA/effectif PM…), documents non typés |
| 2 — Scoring & Triggers | 🟠 | 10 axes/seuils/6 triggers/T2=15M ✅ ; **pondérations non configurables** |
| 3 — Alertes | ✅ | — |
| 4 — Workflow | 🟠 | 8 états ✅ ; **clôture ouverte au RC** (CDC : Admin+Notaire) |
| 5 — Registres | 🟠 | Manque « Registre des dossiers à risque élevé » ; immuabilité applicative (pas DB) |
| 6 — Reporting | 🟠 | À compléter (widgets réévaluations/DOS agrégés) |
| 7 — Administration | 🟠 | Users = Admin ✅ ; pondérations non paramétrables |
| 8 — DOS | 🟠 | 10 sections + blocage auto ✅ ; **pas d'export PDF**, **pas d'alerte délai 24h**, ⚠️ double validation RC→DG > CDC |
| 9 — Révision KYC | ✅ | Fréquences 5/3/2/3/1 ans + jalons J30/60/90/120 ✅ |
| Sécurité | 🟠 | 2FA ✅ ; **chiffrement au repos absent** ; session 30 min via token mais refresh 8h |
| Architecture | 🔴 | **Pas de desktop Electron / offline SQLite / synchronisation** ; Vue (≠ Next.js), MySQL (≠ PostgreSQL) |

---

## Détail des éléments manquants

### Architecture (CDC §3, §7) — 🔴 écart structurel
- **Aucune version Desktop (Electron)**, aucun **mode hors-ligne (SQLite)**, aucune **synchronisation** web↔local (le CDC §3 et §7.1 l'exigent, avec résolution manuelle des champs critiques : score, statut, DOS, PPE, sanctions). Le notaire est **web-only (Vue + MySQL)**.
- Stack : **Vue.js** au lieu de **Next.js** (CDC) ; **MySQL** au lieu de **PostgreSQL** (CDC). Déviations fonctionnelles à acter ou corriger.

### Module 1 — KYC (🟠)
**PP — manquants :** `sexe`, `retraité`, `note`, **ville de résidence** distincte du pays, pièce : **date d'émission** + **mode de vérification** (Original vu/Copie certifiée/En ligne), **tranche de revenus** (énum <500K/500K-2M/2M-10M/>10M au lieu d'un montant libre). BE PP : **lien avec le client**. Frontend stepper PP : téléphone, email, situation matrimoniale, double nationalité non exposés.
**PM — manquants :** `nom commercial`, `pays de constitution`, **CA annuel**, **effectif**, **pays d'opérations**, **volume des transactions** ; actionnaire : **type PP/PM** ; BE : **entreprise cotée**.
**Documents (1.3) — 🔴 :** pas de modèle de pièce justificative **typé** ni de **conditions** (pièce/photo obligatoires, justif revenus si espèces>10M, formulaire BE si BE≠client, formulaire PPE si PPE, extrait RCCM<3 mois PM). Upload générique MinIO seulement.

### Module 2 — Scoring & Triggers (🟠)
✅ 10 axes notés 0/1/2 ; seuils **verrouillés** 0-7/8-13/14-20 ; 6 triggers absolutoires T1-T6 ; **T2 = 15M FCFA** (`ESPECES_THRESHOLD_FCFA`).
🔴 **Pondérations des 10 axes non configurables par l'Admin** (CDC §2.2 et ADM-03 : paramétrable Admin). Elles sont en dur dans `scoring_service.py`, sans endpoint ni persistance.
🟠 T4 GAFI : la mécanique existe (flags `pays_liste_noire/grise_gafi` dérivés de `pays_residence`) mais la **liste de référence des pays GAFI** (noire/grise) à jour est à fournir/compléter.

### Module 4 — Workflow (🟠)
✅ 8 états CDC présents (`brouillon, en_analyse, vigilance_renforcee, valide, bloque, traite, cloture, archive`), assignation, commentaires, historique.
⚠️ **WRK-04 (clôture)** : `PATCH /dossiers/{id}/statut` est gardé par `require_rc` → le **Responsable Conformité peut clôturer**, alors que le CDC réserve la clôture à **Admin + Notaire Principal**.

### Module 5 — Registres (🟠)
✅ 6 registres (KYC, alertes, DOS confidentiel, changements de statut, révisions, journal) + export PDF + accès confidentiel DOS.
🔴 Manque le **« Registre des dossiers à risque élevé »** (score ≥ 14/20) explicitement listé au CDC §5.1.
🟠 Immuabilité = **applicative** (append-only sur `audit_logs`), pas de garantie **au niveau base** ; suppression physique non bloquée en DB (Art. 197/23) ; rétention 10 ans des logs non automatisée.

### Module 6 — Reporting (🟠)
Tableau de bord présent (KPI). À vérifier/compléter vs CDC : widget **réévaluations** (à venir/en retard/vigilance/bloquées), **DOS agrégés anonymisés**, dossiers bloqués. Rapports conformité/client/audit/réévaluation à confirmer.

### Module 8 — DOS (🟠)
✅ 10 sections CENTIF (organisme, type soupçon BC/FT/Prolif, 14 motifs, statut opérations, transactions, indices, identification, relations, supports, autres), **blocage auto du dossier** à la création, confidentialité Art. 63 (guard `require_dos_access`), `statut_operation`/`date_detection`, décision/classement, transmission CENTIF, alerte J+15.
🔴 **Pas d'export PDF du DOS** (endpoint `/dos/{id}/pdf` absent ; le frontend `dos.ts` l'appelle pourtant → cassé). DOS-05 non couvert.
🔴 **Pas d'alerte « délai légal 24h »** (Art. 2 §58) entre détection et soumission.
⚠️ **Double validation RC→DG** : le code impose Déclarant → RC (`/valider`) → Notaire (`/transmettre`, distinct du RC). Le **CDC §8.2 autorise le RC OU le Notaire à tout faire seul** (initier→soumettre). Notre circuit est **plus strict** (séparation Art. 12) — **à confirmer** : garder (sécurité renforcée) ou simplifier pour coller au CDC.
🟠 Vues DOS frontend désalignées (schéma immo fantôme) — à reconcilier.

### Sécurité (CDC §5) (🟠)
✅ 2FA obligatoire Notaire Principal + RC ; listes sanctions GIABA/BCEAO/OFAC/UE + alerte >95j ; logs (user/rôle/action/UTC/IP) ; ADM-01 users = Admin only.
🔴 **Chiffrement AES-256 au repos absent** : seules les données TOTP sont chiffrées ; identité/scores/DOS restent en clair en base (CDC §5.2). Écart majeur.
🟠 **Session 30 min** : token d'accès 30 min ✅ mais refresh 8h prolonge la session → pas une vraie inactivité de 30 min.
🟠 Rétention logs 10 ans non automatisée ; TLS 1.3 dépend de la config nginx (non vérifiable dans le code).

---

## Recommandations priorisées

**P0 (conformité réglementaire directe)**
1. Chiffrement au repos AES-256 des colonnes sensibles (identité, scores, DOS).
2. Export PDF du DOS (`/dos/{id}/pdf`) + corriger l'appel frontend.
3. Restreindre la **clôture** (WRK-04) à Admin + Notaire Principal (retirer au RC).
4. Ajouter le **Registre des dossiers à risque élevé** (score ≥ 14).

**P1 (champs & paramétrage CDC)**
5. KYC : compléter les champs manquants (PP : sexe, tranche revenus, date émission pièce, mode vérification, lien BE ; PM : nom commercial, pays constitution, CA/effectif/pays opérations/volume, type actionnaire, entreprise cotée).
6. Pondérations des 10 axes **configurables par l'Admin** + persistées en base.
7. Documents : modèle typé + règles conditionnelles (1.3).
8. Alerte délai 24h DOS ; liste pays GAFI de référence (T4).

**P2 (arbitrages)**
9. ⚠️ Décider du circuit DOS : conserver la double validation RC→DG ou s'aligner sur le CDC (RC **ou** Notaire seul).
10. Architecture : statuer sur Desktop Electron + offline SQLite + synchronisation (gros chantier) et sur Vue/MySQL vs Next.js/PostgreSQL.
11. Immuabilité DB des logs/dossiers (trigger/contrainte) + rétention 10 ans automatisée ; vraie session d'inactivité 30 min.

---

## Correctifs appliqués (2026-06-15) — migrations 0012 & 0013

### P0 (corrigés)
- ✅ **Chiffrement au repos AES-256** (`app/core/crypto.py`, type `EncryptedString` Fernet) sur les colonnes sensibles : KYC-PP (n° pièce, n° contribuable, contacts, adresses), KYC-PM (RCCM, n° contribuable, contacts, adresse, représentant), KYC-BE (CNI), DOS (indices de blanchiment, autres informations). Migration **0012** (colonnes → TEXT). *Note : scores/classifications non chiffrés (filtrage risque élevé/agrégats) ; noms en clair (criblage/affichage).*
- ✅ **Export PDF du DOS** : `GET /dos/{id}/pdf` (confidentiel Art. 63, 10 sections) — **réservé Admin + Notaire Principal** (DOS-05).
- ✅ **Clôture (WRK-04)** réservée à Admin + Notaire Principal (retirée au RC).
- ✅ **Registre des dossiers à risque élevé** (`risque_eleve`, score ≥ 14 / classification ÉLEVÉ) + export PDF.

### Champs KYC du CDC (ajoutés, migration 0013)
- **PP** : `sexe`, `ville_residence`, `retraite`, `note`, pièce (`pays_emetteur_piece`, `date_emission_piece`, `date_expiration_piece`, `mode_verification_piece`), `tranche_revenus` (énum réglementaire). + `objet_relation` (lot précédent).
- **PM** : `nom_commercial`, `pays_constitution`, `ca_annuel`, `effectif`, `pays_operations`, `volume_transactions`. + `objet_social`, RCCM 90j, `representant_statut_ppe` (lot précédent).
- **BE** : `lien_avec_client`, `entreprise_cotee`. + droits de vote, entité intermédiaire, registre BE, filtrage SFC, validation (lot précédent).
- **Actionnaire** : `type_personne` (PP/PM).
- Modèle + schémas + interfaces TS du service mis à jour. 🟡 **Reste : exposer ces champs dans les steppers KYC** (`KycStepper`/`KycPMStepper`/`KycBEForm`) — API/modèle prêts.

> Validation runtime des migrations 0012/0013 à faire au déploiement (Docker indisponible au développement).

---

## Validation runtime (2026-06-15, services Docker démarrés)

Après **rebuild** des images (l'image en cours était périmée — migration 0001 seulement) :
- ✅ **Migrations 0002 → 0013** appliquées sur la base MySQL réelle (`alembic current = 0013 (head)`), API *healthy*. Valide gel retiré, rôles, workflow DOS, prolifération, enrichissements KYC, **chiffrement**, champs CDC.
- ✅ Nouveaux endpoints présents : `/api/dos/{id}/pdf`, `/valider`, `/transmettre`, etc.
- ✅ **Parcours KYC-PP testé de bout en bout** (login → création dossier → save → relecture) : tous les champs CDC (sexe, tranche_revenus, mode_verification_piece, ville_residence, objet_relation) persistent.
- ✅ **Chiffrement au repos vérifié** : `numero_piece`/`telephone` stockés en base sous forme `enc::…` (Fernet) et relus déchiffrés ; champs non sensibles en clair.

### Correctifs réalisés pendant la validation
- 🐛 **Bug pré-existant corrigé** : `POST /dossiers` renvoyait 500 (`MissingGreenlet` — lazy-load des relations KYC à la sérialisation). La création re-fetch désormais avec eager-load (`get_by_id`). La création de dossier ne fonctionnait pas auparavant.
- 🔑 **AES_KEY robuste** : `app/core/crypto.py` dérive la clé Fernet par SHA-256 (l'`AES_KEY` du `.env` était en hex → 24 octets, invalide pour Fernet ; le TOTP aurait le même défaut s'il était sollicité). Indépendant du format de la clé.

### Steppers KYC frontend — état
Les trois steppers étaient des reliquats de la migration immo, non câblés au backend notaire (noms de champs erronés → saves silencieusement ignorés ou 422 ; méthodes service inexistantes). **Tous réalignés et validés end-to-end** :
- ✅ **Stepper PP (`KycStepper.vue`)** : réaligné + champs CDC (sexe, coordonnées, résidence pays/ville, pièce + dates + mode de vérification, tranche de revenus, retraité, note, objet de la relation, PPE, mandataire).
- ✅ **Stepper PM (`KycPMStepper.vue`)** : réaligné (`denomination_sociale`, `pays_constitution`, `adresse`, représentant → JSON `mandataire` + `nom_representant_legal` + `representant_statut_ppe`) + champs CDC (nom commercial, date émission RCCM → calcul 90j validé, CA, effectif, pays d'opérations, volume, objet social). Actionnaires/BE ≥25% persistés via les endpoints dédiés.
- ✅ **BE (`KycBEForm.vue` + `KycBEPanel.vue`)** : formulaire réaligné (`raison_sociale_nom`, `pourcentage`) + champs CDC (lien avec le client, entreprise cotée, % droits de vote, entité intermédiaire) + registre BE (greffe) + filtrage SFC structuré + validation RC. Méthodes service manquantes ajoutées (`createKycBE`/`listKycBE`/`deleteKycBE`, contexte PP/PM).
- ✅ **Édition BE** : endpoints `PATCH /kyc/pp/be/{id}` et `PATCH /kyc/pm/be/{id}` ajoutés (mise à jour partielle `KycBEUpdate`, `exclude_unset`) + service `updateKycBE` ; le formulaire édite désormais un BE existant. Smoke-test PATCH validé.
