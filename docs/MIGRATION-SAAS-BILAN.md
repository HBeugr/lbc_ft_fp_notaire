# Bilan de la migration SaaS multi-tenant PostgreSQL

**Date :** 2026-07-18
**Portée :** passage de `notaire-platform` de MySQL mono-tenant à PostgreSQL SaaS multi-tenant (un schéma par cabinet).
**Décisions cadrantes :** voir [ADR-001](ADR-001-isolation-schema-par-tenant.md).

Ce document consigne ce qui a été **vérifié par exécution**, les **défauts trouvés
et corrigés** au passage, et les **constats résiduels** à arbitrer. Il n'est pas
un plan : tout ce qui y figure a été exercé.

---

## 1. Défauts trouvés et corrigés

Aucun de ces défauts n'était visible au typecheck, à la compilation ou à la
revue de code. Tous ont été révélés en exécutant réellement la plateforme —
c'est la justification principale de la démarche de recette décrite en §2.

| # | Défaut | Conséquence si non corrigé | Correctif |
|---|---|---|---|
| 1 | `search_path` + cache de requêtes préparées asyncpg | `cannot cast type tenant_a.user_role_enum to user_role_enum` — une connexion réutilisée par un autre cabinet rejouait les types du précédent. **Le schéma-par-tenant ne fonctionnait pas.** | Caches désactivés (`statement_cache_size`, `prepared_statement_cache_size`) — `core/database.py` |
| 2 | Tableau de bord filtrant sur `resilie` | Statut absent de `statut_dossier_enum` (résidu du vertical immobilier). MySQL tolérait, PostgreSQL rejette : **500 sur la page d'accueil, tous rôles** | `routers/dashboard.py` |
| 3 | `DOS_DB_USER` = rôle applicatif dans `.env` | Séparation de privilèges Art. 63 annulée, et l'`ALTER ROLE` de démarrage réinitialisait le mot de passe du compte applicatif — **verrouillage hors de sa propre base** | Garde-fou bloquant + `.env` corrigé — `core/dos_privileges.py` |
| 4 | Mot de passe en clair dans les journaux | PostgreSQL n'admet aucun paramètre lié en DDL ; sous `echo=True` le DDL de rôle était recopié intégralement | Écho coupé sur le moteur le temps du DDL |
| 5 | `alembic` invoqué via le PATH | Provisioning dépendant de l'environnement de lancement (superviseur, cron, tests) | `sys.executable -m alembic` + `cwd` explicite |
| 6 | Ports de développement en collision | 5433 et 9010 déjà pris par le vertical assujetti : **les deux piles ne pouvaient pas coexister** | 5434 / 9020-9021 — `docker-compose.dev.yml` |
| 7 | MinIO publié sur l'hôte en production | Actes et pièces d'identité joignables derrière une simple clé S3, sans nécessité (seule l'API le consomme) | Publication retirée du `docker-compose.yml` |
| 8 | `APP_ENV=development` sur la pile déployée | Écho SQL actif (**requêtes et paramètres**, donc données clients, dans les journaux) et `/api/docs` exposé | `APP_ENV=production` + commentaire explicatif |
| 9 | 500 au lieu de 401 sans jeton | `get_db` levait `NoTenantContextError` avant le contrôle d'authentification | Gestionnaire d'exception — `main.py` |
| 10 | Suite de tests fuyant des buckets MinIO | Un bucket orphelin par exécution, en local comme en intégration continue | Nettoyage au teardown — `tests/conftest.py` |
| 11 | **Flux SSE hors contexte cabinet** | Le générateur est consommé APRÈS la sortie du middleware : chaque lecture repartait sur le schéma par défaut. **Échec silencieux** — HTTP 200, mais flux mort et badge d'alertes muet | Capture du cabinet dans l'endpoint + `tenant_scope` refermé avant chaque `yield` — `routers/alertes.py` |
| 12 | `DosOut.detail_transactions` typé `dict` | `DosUpsert` y écrit une liste : dès qu'une DOS était renseignée elle devenait illisible, et **la liste des DOS cassait pour tout le cabinet** (6 routes en 500) | `list[TransactionSchema] \| dict \| None` — `schemas/dos.py` |
| 13 | Export PDF des DOS | fpdf2 ≥ 2.6 laisse le curseur à droite après `multi_cell` : la largeur automatique de la ligne suivante tombait à zéro. Toute section de plus d'une ligne plantait | `new_x="LMARGIN", new_y="NEXT"` — `routers/dos.py` |
| 14 | **Un cabinet suspendu déconnectait l'utilisateur** | `silentRefresh` traitait le 402 comme un jeton invalide et purgeait la session. Le jeton d'accès n'étant jamais persisté, c'était le chemin **normal** au moindre rechargement : `/compte-suspendu`, le bandeau et le message de régularisation étaient **du code mort** | `stores/auth.ts`, `services/tenantBlock.ts`, `router/index.ts`, `services/api.ts` |
| 15 | Bandeau de suspension conditionné à `isAuthenticated` | Masqué exactement dans le cas qu'il doit signaler | `components/layout/TenantStatusBanner.vue` |
| 16 | Cabinet archivé : 403 **sans code** | Contrairement au 402 suspendu, le client ne pouvait pas distinguer un blocage d'un défaut d'authentification | `code: "tenant_archived"` — `core/tenant_middleware.py` |
| 17 | Erreurs 422 illisibles à la création de cabinet | `detail` est un tableau d'erreurs par champ : l'interface affichait « Impossible de créer le cabinet », sans dire lequel | `views/superadmin/TenantCreateView.vue` |
| 18 | Suite de tests non rejouable | Une exécution interrompue laissait des cabinets orphelins ; l'unicité **plateforme** des emails faisait alors échouer en 409 toute création ultérieure | Purge des résidus au démarrage — `tests/conftest.py` |

Les défauts 11 et 14 méritent une mention particulière : c'est le seul à s'être manifesté
par un **succès apparent** : une réponse 200 accompagnée d'un flux vide ne
déclenche aucune alerte de supervision et ne casse aucun test de code de statut.
Le 14, lui, rendait tout le dispositif de suspension inatteignable — la
fonctionnalité était livrée, testée côté API, et pourtant impossible à observer
en conditions réelles. Ce sont les deux classes de défauts les plus coûteuses à
découvrir tardivement, et aucune des deux n'était visible sans exécuter le
produit de bout en bout.

Les défauts 1 à 8 sont verrouillés par
[`tests/integration/test_regressions_migration.py`](../backend/tests/integration/test_regressions_migration.py),
y compris les invariants de configuration (compose, `.env`). Le 11 l'est par la
recette E2E (contrôle du **contenu** du flux), les 14 à 17 par la spec
navigateur [`e2e/saas-multitenant.spec.ts`](../e2e/saas-multitenant.spec.ts).

---

## 2. Ce qui a été vérifié, et comment

| Périmètre | Méthode | Résultat |
|---|---|---|
| Étanchéité inter-cabinets | 23 tests dédiés, PostgreSQL réel, pile ASGI complète | schéma, jeton, chiffrement, Redis, config métier, annuaire, portier, exploitation |
| Étanchéité **sous concurrence** | 40 requêtes entrelacées entre 2 cabinets + chiffrement concurrent | aucun débordement de contexte ni de clé |
| Non-régressions de migration | 11 tests (code + configuration) | les 8 premiers défauts ne peuvent plus revenir |
| Suite complète | `pytest` avec environnement **vierge** (`env -i`) | aucune dépendance à une configuration locale |
| Parcours SaaS | [`scripts/e2e_saas.sh`](../backend/scripts/e2e_saas.sh) contre une API démarrée | provisioning → portier → activation → isolation → suspension → réactivation |
| Surface d'API | **133/133 opérations OpenAPI** exercées avec un jeu de données réel (188 appels, tous rôles) | zéro 5xx, zéro trace serveur |
| Frontend | **7 parcours navigateur** (Playwright) : branding, « Mon cabinet », console Super-Admin, création de cabinet, étanchéité des sessions, suspension/réactivation | tous verts, **zéro erreur JS** |
| Services | pile Docker complète (6 services) | tous *healthy*, frontend servi par nginx, proxy `/api` fonctionnel |
| Sauvegarde | exécution réelle du service `backup` | dump global + **un dump par cabinet** + annuaire, chiffrés et hachés |
| Restauration d'un cabinet | `pg_restore` d'un schéma seul | cabinet voisin intact (procédure corrigée dans `DEPLOY.md`) |
| **Reprise de données** | base MySQL héritée reconstituée depuis git, puis migrée | 27 contrôles : volumétrie, **changement de clé de chiffrement**, types, annuaire, intégrité référentielle |

**Validation finale consolidée**, pile Docker complète, après tous les correctifs :
53 tests pytest (deux passages consécutifs, rejouabilité prouvée) · recette E2E
22/22 · 133 routes d'API, 188 appels, zéro 5xx · 7 parcours navigateur.

### Reprise de données — validation

Le script de reprise a été éprouvé sur une **vraie base MySQL** reconstituée à
partir du code d'avant la migration (extrait de git), incluant colonnes
chiffrées, JSON, booléens et énumérations. Quatre conversions ne vont pas de soi
et sont toutes couvertes :

1. **Colonnes chiffrées** — déchiffrées avec l'ancienne clé globale
   (SHA-256 de `AES_KEY`), rechiffrées avec la clé propre au cabinet (HKDF).
   Vérifié : lisibles dans leur cabinet, illisibles avec la clé d'un autre.
2. `TINYINT(1)` → `BOOLEAN` (PostgreSQL refuse l'entier).
3. `DATETIME` naïf → `TIMESTAMPTZ` (qualifié en UTC).
4. Chaîne JSON du pilote MySQL → structure `JSONB`.

Après une reprise réelle, lancer
[`scripts/verifier_reprise.py`](../backend/scripts/verifier_reprise.py) avant
toute décision concernant l'ancienne base.

---

## 3. Constats résiduels

### 3.1 Le rôle DOS restreint n'est pas utilisé par l'application

Les privilèges sont **correctement posés** dans chaque schéma cabinet — vérifié
en base : `INSERT, SELECT, UPDATE` sur `declarations_suspicion`,
`INSERT, SELECT` sur `dos_addendums`, **aucun DELETE nulle part**.

Mais `get_dos_db()` n'est injecté par **aucun** endpoint : le router DOS utilise
la session applicative ordinaire. La garantie append-only existe donc au niveau
du SGBD sans être exercée par le code.

C'est un écart **antérieur à cette migration** (code mort hérité), pas une
régression. Le corriger n'est pas mécanique : `routers/dos.py` touche aussi
`users`, `dossiers` et `alertes`, tables sur lesquelles `dos_user` n'a — à
raison — aucun privilège. Un branchement direct casserait le module.

**Recommandation** : session double dans le router DOS — session restreinte pour
les écritures sur les deux tables DOS, session ordinaire pour le reste. À
arbitrer séparément.

### 3.2 Identité visuelle du cabinet (logo)

Ajoutée après la migration. Le fichier est stocké dans le **bucket du cabinet**
(isolation de niveau 3) et n'est jamais exposé par URL de stockage : il transite
par l'API, qui vérifie l'appartenance de l'appelant. Seule sa référence
(`logo_key`, `logo_content_type`, `logo_updated_at`) figure dans l'annuaire, afin
que la barre latérale puisse l'afficher sans ouvrir de session métier.

| Qui | Peut |
|---|---|
| Super-Admin | Poser / remplacer / retirer le logo de n'importe quel cabinet, y compris à la création |
| Admin du cabinet | Poser / remplacer / retirer le logo de SON cabinet |
| Tous les autres rôles | Le voir uniquement |

Contraintes appliquées, validées sur le **contenu réel** de l'image et non sur le
type déclaré (un fichier arbitraire renommé en `.png` est refusé) : PNG, JPEG ou
WebP ; ≤ 1 Mo ; de 64×64 à 2048×2048 px ; rapport largeur/hauteur ≤ 4:1.

Deux choix méritent d'être explicités :

- **SVG exclu.** Un SVG peut embarquer du script et serait servi depuis notre
  propre origine. Le bénéfice visuel ne vaut pas cette surface d'attaque.
- **Verrou `require_admin`, pas `require_user_manager`.** Les deux sont
  aujourd'hui équivalents (Admin seul), mais le logo relève du paramétrage du
  cabinet (ADM-07), pas de la gestion des utilisateurs (ADM-01, séparation des
  fonctions Art. 12). Les adosser aurait élargi silencieusement l'accès au logo
  si cette règle de séparation venait à évoluer.

### 3.3 Facturation

Hors périmètre par décision. Les points d'accroche existent et sont exercés :
`tenants.statut` (`suspendu` = accès coupé, données conservées — testé) et
`tenants.max_users` (quota appliqué à la création d'utilisateur, 402 au-delà).

### 3.4 Compte administrateur supplémentaire après reprise

Le provisioning crée un compte admin avant l'import : un cabinet repris compte
donc **un utilisateur de plus** que l'ancienne base. C'est voulu — si aucun mot
de passe hérité n'était connu de l'exploitant, le cabinet serait inaccessible
malgré des données intactes.

---

## 3.5 Reprise réelle exécutée depuis le VPS (2026-07-18)

La reprise a été **effectivement jouée** sur les données du déploiement, et pas
seulement sur un jeu reconstitué.

**Source** : `notaire-notairestackdev-6uatgg-db-1` sur le VPS Dokploy —
MySQL 8.0.46, base `notaire_lbcft`, révision Alembic **0024** (soit exactement
l'état final que la migration PostgreSQL squashée reproduit). Le dump a été
rapatrié **par flux** : aucune écriture, aucune suppression, aucun redémarrage
côté serveur.

**Volume repris** : 2 949 lignes — 40 dossiers · 26 KYC PP · 3 KYC PM · 89 alertes ·
3 DOS · 435 entrées d'audit · 2 301 entrées de listes de sanctions · 5 utilisateurs.

**Résultat** : 23/23 contrôles, puis lecture effective à travers l'API après
activation du cabinet (40 dossiers, 89 alertes, tableau de bord cohérent),
déchiffrées avec la clé propre au cabinet.

Trois enseignements de cette exécution réelle :

1. **Le chiffrement de la source est partiel.** Les lignes antérieures à la
   migration 0012 sont restées en clair (0 téléphone chiffré sur 2, 1 numéro de
   pièce en clair sur 3, 2 emails en clair sur 5). La reprise les chiffre au
   passage — c'est un gain, pas une perte.
2. **Une collision d'adresses arrêtait la reprise APRÈS la copie**, laissant un
   cabinet à moitié peuplé : données présentes, annuaire incomplet, personne ne
   pouvant se connecter. Un contrôle préalable a été ajouté
   (`verifier_collisions_emails`) : la reprise refuse désormais de démarrer, sans
   rien écrire, et nomme les adresses et le cabinet en cause.
3. **Les données du VPS sont le jeu d'amorçage augmenté d'activité de recette**
   (adresses `@notaire.local`, aucun organisme renseigné) — ce n'est pas un
   corpus client. Il n'existe d'ailleurs pas de pile de production notaire sur ce
   serveur, seulement `notairestackdev`.

**Non repris** : les fichiers documentaires (8 documents référencés) résident
dans le MinIO du VPS, hors de portée du script depuis le poste local. Leur copie
est à faire au moment de la bascule réelle, avec accès au stockage distant.

---

## 4. Avant mise en production

- [ ] Reprise réelle des données, précédée d'un `--dry-run` et d'une sauvegarde
      MySQL conservée hors ligne.
- [ ] `scripts/verifier_reprise.py` exécuté et vert.
- [ ] Recette métier par un utilisateur du cabinet sur les données reprises.
- [ ] **`TENANT_MASTER_KEY` sauvegardée hors de la plateforme** — sa perte rend
      les données de tous les cabinets définitivement illisibles, sauvegardes
      comprises.
- [ ] Ancienne base MySQL **conservée** jusqu'à validation complète. Sa
      destruction relève de l'Art. 197 (conservation 10 ans).

---

## 5. Campagne de conformité au cahier des charges

Recette systématique des 9 modules du CDC, de la matrice de permissions §7.3 et
de la section 5 « Sécurité & Conformité ». **294 tests** répartis en trois
fichiers (`test_cdc_modules_1_2_3.py`, `_4_5_6.py`, `_7_8_9.py`).

### 5.1 Non-conformités réglementaires trouvées et corrigées

| Exigence CDC | Ce qui se passait | Portée |
|---|---|---|
| §2.3 — triggers « non paramétrables » (Art. 72) | Le seuil espèces T2 était **relevable sans limite** : porté à 100 M FCFA, il **désactivait T2** de 15 M à 100 M | Plafond légal appliqué **au calcul**, pas seulement à la saisie |
| §5.1 — registre des alertes | `generate_alertes()` **n'était appelé de nulle part** : T1, T2, T4, T5 et T6 reclassaient en ÉLEVÉ sans produire **aucune alerte** | Détection branchée sur les deux chemins de scoring |
| Art. 89 — gel des avoirs | T3 (liste de sanctions) ne **bloquait pas** le dossier depuis l'écran de scoring | Blocage effectif |
| Art. 23 — conservation 10 ans | `archivage_date` / `archivage_expiration` **n'étaient écrits nulle part** : un dossier archivé ne portait aucune échéance opposable | Posé à la clôture, dans la même transaction |
| §5.2 — archivé = lecture seule | Quatre surfaces d'écriture restaient ouvertes (transaction, assignation, commentaire, KYC) | Verrou sur les 4 + 16 endpoints KYC |
| §7.3 ADM-01/02 (Art. 12) | Le **Notaire Principal gérait comptes et rôles** — celui qui valide et clôture pouvait se fabriquer des comptes | Admin seul |
| §7.3 ADM-06 | Le **Responsable Conformité lisait les journaux d'audit** | Admin + Notaire Principal |
| §7.3 KYC-04 | Un **clerc pouvait réécrire une fiche validée**, invalidant a posteriori une diligence engageant le notaire | Verrou sur les états validés |
| §7.3 SCO-01 P² | Le **détail des 10 axes** était exposé aux clercs (CDC : label seul) | Ventilation masquée |
| §7.3 REG-01/02 | Registres KYC, alertes, statuts et révisions **lisibles et exportables par un clerc** | Repli restrictif |
| §7.3 P³ + DOS-04 + Art. 63 | Le tableau de bord d'un clerc exposait le **volume déclaratif DOS du cabinet** | Compteur neutralisé |

Deux constats de fond se dégagent :

- **Les fonctionnalités écrites mais jamais branchées sont la faille dominante
  de ce projet.** Trois cas indépendants : la détection d'alertes, la session
  DOS à privilèges restreints, l'écriture des échéances d'archivage. Aucun n'est
  visible en lecture de code — chacun se présente comme du code correct.
- **Les permissions dérivaient vers le trop large**, par report du vertical
  immobilier (rôle « dirigeant ») sur un rôle notarial que le CDC ne dote pas
  des mêmes droits.

### 5.2 Écarts CDC signalés, non corrigés

Ils appellent un arbitrage, pas un correctif — les inventer aurait été pire que
les signaler. Les quatre premiers sont marqués `xfail` **strict** : le jour où
ils sont traités, la suite le signale d'elle-même.

| Écart | Nature |
|---|---|
| ALE-01 — clercs : CDC dit N, l'API répond 200 (périmètre restreint aux dossiers assignés) | Un test existant exige ce 200 : arbitrage métier |
| WRK-05 — clercs : CDC dit N, la chaîne d'assignation autorise l'auto-assignation | Décision produit datée en commentaire, en conflit avec le CDC |
| DOS-01 — Notaire Principal et RC exclus du flag interne | Permission trop **étroite** : gêne fonctionnelle, pas un risque |
| SCO-01 P² — `score_base` numérique encore exposé aux clercs | Masquer le champ touche le frontend |
| §5.2 — `nom`, `prenoms`, `score_base` et `classification` **non chiffrés** | Chiffrer les patronymes casserait le criblage des sanctions, qui les lit en clair |
| §6.2 — rapport « réévaluation » absent | Fonctionnalité non développée |
| §5.2 — alerte J-180 avant échéance des 10 ans | Non développée ; l'ancrage (`archivage_expiration`) existe désormais |

### 5.3 Conformités vérifiées

Seuils de classification aux bornes exactes (7/8/13/14) et **verrouillés pour
tous les rôles, admin compris** · les 6 triggers forcent ÉLEVÉ sur un score de
base de 2/20 · T2 discrimine 15 000 000 de 15 000 001 · 8 états de workflow et
transitions interdites · suppression d'un dossier archivé bloquée **au niveau
SGBD** · 5 registres exposés, 10 exports validés par signature binaire ·
confidentialité DOS étanche jusque dans les flux PDF décompressés · blocage
immédiat du dossier à l'initiation d'un DOS (Art. 61) · fréquences de révision
§9.1 et jalons J+30/60/90/120 · 2FA des rôles de supervision · session 30 min ·
journaux immuables (aucune route d'écriture pour aucun rôle) · chiffrement au
repos vérifié en `SELECT` brut sur le schéma du cabinet.

### 5.4 Validation finale

Base propre, environnement vierge, après tous les correctifs :

| Couche | Résultat |
|---|---|
| pytest | **347 passés, 4 xfailed, 0 échec** |
| Recette SaaS de bout en bout | **22/22** |
| Couverture d'API | **135 routes, 200 appels, 0 erreur serveur** |
| Parcours navigateur | **14/14** |
