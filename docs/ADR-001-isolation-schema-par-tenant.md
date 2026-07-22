# ADR-001 — Isolation multi-tenant : un schéma PostgreSQL par cabinet

> **Statut** : Retenu et implémenté
> **Date** : 2026-07-18
> **Contexte** : `SaaS-analyse-LBCFT.pdf` (analyse de décision), Ordonnance N°2023-875, CDC Chambre des Notaires de Côte d'Ivoire.

## Contexte

La plateforme était mono-tenant : conçue pour une seule étude, avec tout ce qui
en découle — une base, une clé de chiffrement, un bucket documentaire, un cache
de configuration. Le passage en SaaS demande d'insérer une couche « cabinet »
au-dessus des données et d'en faire descendre tout le métier.

L'analyse SaaS jointe recommandait **une base de données par client**. Ce
raisonnement est cohérent — mais il a été mené dans une optique MySQL, où
« un schéma = une base ». Le document laisse d'ailleurs la porte ouverte :
« envisager Postgres si une isolation par schéma plus fine est souhaitée ».
Le choix de PostgreSQL ouvre précisément cette troisième voie.

## Options considérées

| Option | Isolation | Exploitation | Verdict |
|---|---|---|---|
| **A.** Table partagée + colonne `tenant_id` | ❌ Faible — un seul `WHERE` oublié = fuite inter-cabinets | Simple | ❌ Inacceptable pour des données LBC/FT |
| **B.** Schéma-par-tenant (1 instance PG) | ✅ Forte — objets physiquement séparés, `search_path` par transaction | ✅ Migrations et sauvegardes par schéma | ✅ **Retenu** |
| **C.** Base-par-tenant | ✅ Très forte | ⚠️ Lourde — N pools de connexions, N jobs de migration et de sauvegarde | ⚠️ Surdimensionné en PostgreSQL |

## Décision

**Option B — un schéma `tenant_<uuid>` par cabinet, dans une instance PostgreSQL partagée.**

- Un schéma `shared`, non métier, porte l'annuaire de routage : cabinets,
  aiguillage `email → cabinet`, comptes d'exploitation, journal d'exploitation.
- Le routage passe par un `ContextVar` posé par `TenantMiddleware` à partir du
  claim `tid` du JWT, puis par un `SET LOCAL search_path` à l'ouverture de chaque
  transaction.
- **Le code métier reste inchangé** : les repositories, routers et requêtes SQL
  brutes existants continuent de fonctionner tels quels, à l'intérieur du bon
  schéma. C'était l'objectif central, et il est tenu — les points d'injection de
  session (`Depends(get_db)`) n'ont pas été touchés.

## Justification

1. **Isolation réelle, pas déclarative.** L'option A fait reposer la
   confidentialité sur la discipline du développeur ; pour un outil qui héberge
   des déclarations de soupçon, ce n'est pas défendable devant un audit.
2. **Sauvegarde et restauration granulaires.** `pg_dump -n tenant_x` permet de
   restaurer un cabinet sans toucher aux autres — vérifié en conditions réelles
   (cf. `DEPLOY.md`).
3. **Coût d'exploitation.** L'option C multiplie les pools de connexions et les
   jobs par le nombre de cabinets. Le schéma-par-tenant mutualise le pool tout en
   séparant les objets : le bon compromis pour la cible visée (dizaines à
   quelques centaines de cabinets).
4. **Évolutivité.** Ajouter un cabinet = `CREATE SCHEMA` + migrations, sans
   modification de code.
5. **Réversibilité.** Si un cabinet exigeait un jour un hébergement séparé, la
   bascule schéma → base est mécanique (`pg_dump` du schéma → nouvelle base).

## Défense en profondeur

L'isolation ne repose pas sur un seul mécanisme. Chaque barrière est testée
séparément dans `tests/integration/test_tenant_isolation.py`, afin qu'une
régression sur l'une reste visible même si les autres tiennent.

| Barrière | Mécanisme |
|---|---|
| Données | Schéma PostgreSQL dédié, `search_path` par transaction |
| Jeton | Claim `tid` obligatoire ; revérifié dans `deps.py` contre le cabinet servi |
| Chiffrement | Clé AES-256 dérivée par HKDF du sel propre au cabinet — un déchiffrement croisé échoue **bruyamment** |
| Stockage | Un bucket MinIO par cabinet |
| Cache | Espaces de noms Redis préfixés par cabinet |
| Configuration métier | Seuils et pondérations de scoring en cache par cabinet |
| Exploitation | Comptes Super-Admin hors de tout schéma cabinet, portée de jeton distincte |

## Conséquences

### Positives

- Isolation forte, argument opposable en audit et devant un DPO.
- Code métier réutilisé sans réécriture.
- Onboarding outillé (`tenant_provisioning`), là où il était manuel.
- Le statut `suspendu` prépare un futur portier de facturation sans le coder.

### À gérer

- **Migrations par schéma.** `alembic upgrade head` ne suffit plus : chaque
  schéma porte sa propre table de versions. Deux environnements Alembic
  coexistent — `alembic_shared.ini` (annuaire, joué une fois) et `alembic.ini`
  (métier, rejoué par cabinet, via `POST /api/super-admin/tenants/migrate`).
- **Cache de requêtes préparées désactivé.** asyncpg met en cache les plans avec
  les OID des types résolus. Or chaque schéma possède ses propres types `ENUM`,
  désignés sans qualification dans les requêtes. Une connexion réutilisée par un
  autre cabinet rejouerait un plan pointant les types du précédent
  (`cannot cast type tenant_a.user_role_enum to user_role_enum`). Les deux
  caches sont donc désactivés — c'est aussi la configuration requise derrière un
  pooler transactionnel type PgBouncer. Coût de performance modéré, non
  négociable ici.
- **Unicité des emails au niveau plateforme.** C'est ce qui permet un login par
  simple email/mot de passe, sans demander son cabinet à l'utilisateur. En
  contrepartie, une même adresse ne peut pas appartenir à deux cabinets.
- **Types ENUM à supprimer explicitement** dans les `downgrade()` : contrairement
  à MySQL, ils survivent au `DROP TABLE`.

## Périmètre non couvert

La **facturation** (Stripe, formules, quotas payants) est hors périmètre de
cette migration, par décision explicite. Le provisioning est piloté par le
Super-Admin. Les points d'accroche existent déjà et n'appelleront pas de
refonte : `tenants.statut` (`suspendu` = accès bloqué, données conservées) et
`tenants.max_users` (quota de sièges, déjà appliqué à la création d'utilisateur).
