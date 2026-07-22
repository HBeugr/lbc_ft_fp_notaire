-- ===========================================================================
-- Initialisation PostgreSQL — Notaire LBC/FT/FP (SaaS multi-tenant)
-- ---------------------------------------------------------------------------
-- Exécuté par l'entrypoint officiel `postgres:16` à la création du volume,
-- dans la base ${POSTGRES_DB} et sous l'identité du superutilisateur
-- ${POSTGRES_USER}.
--
-- ATTENTION — PostgreSQL n'a PAS de compte « root » distinct comme MySQL :
-- le superutilisateur EST ${POSTGRES_USER}, c'est-à-dire le compte applicatif
-- (`DB_USER`). Il n'y a donc plus de `MYSQL_ROOT_PASSWORD` à gérer.
--
-- Ce script est volontairement générique : il n'écrit en dur ni le nom de la
-- base ni celui du rôle applicatif. Il s'appuie sur `current_database()` et
-- `current_user`, ce qui le rend valable quelles que soient les valeurs de
-- DB_NAME / DB_USER dans le `.env`.
-- ===========================================================================


-- ---------------------------------------------------------------------------
-- 1. Schéma `shared` — l'annuaire de routage
-- ---------------------------------------------------------------------------
-- Ne contient AUCUNE donnée métier LBC/FT : uniquement la liste des cabinets
-- (`shared.tenants`), l'aiguillage email → cabinet, les comptes Super-Admin et
-- le journal d'exploitation. Les migrations `alembic_shared` le peuplent
-- ensuite ; on le crée ici pour que la toute première connexion de l'API
-- trouve un schéma existant.
CREATE SCHEMA IF NOT EXISTS shared;


-- ---------------------------------------------------------------------------
-- 2. Rôle `dos_user` — privilèges restreints sur les déclarations de soupçon
-- ---------------------------------------------------------------------------
-- POURQUOI CE RÔLE EXISTE (ADR-003 — Art. 63 de l'Ordonnance N°2023-875) :
--
--   Une Déclaration d'Opération Suspecte est un acte à confidentialité absolue.
--   Sa traçabilité doit être opposable : on doit pouvoir prouver qu'une DOS
--   émise n'a jamais été effacée ni réécrite hors de sa piste d'audit.
--
--   Faire reposer cette garantie sur le seul code applicatif serait insuffisant
--   (une régression, une injection SQL ou un accès direct au SGBD la
--   contournerait). Elle est donc déportée dans le SGBD lui-même : l'API se
--   connecte aux tables DOS via un rôle dédié, `dos_user`, qui ne reçoit
--   JAMAIS le privilège DELETE — ni sur `declarations_suspicion`, ni sur
--   `dos_addendums`. L'append-only est ainsi garanti par PostgreSQL, pas par
--   une convention de développement.
--
--   Concrètement, `dos_user` obtient au maximum, et uniquement dans les
--   schémas cabinet :
--     - declarations_suspicion : SELECT, INSERT, UPDATE   (jamais DELETE)
--     - dos_addendums          : SELECT, INSERT           (jamais UPDATE/DELETE)
--
--   Corollaire : une DOS ne se corrige pas, elle s'amende par un addendum.
--   C'est la transposition technique de l'exigence d'inaltérabilité.
--
-- PORTÉE DE CE SCRIPT : il ne fait que créer le rôle, sans privilège et sans
-- mot de passe. Les GRANT ne peuvent pas être posés ici car les schémas
-- cabinet n'existent pas encore à l'initialisation du volume : ils sont créés
-- au fil des provisionnings. C'est l'API qui, à chaque démarrage
-- (`_ensure_dos_grants` dans `app/main.py`), applique le mot de passe
-- (`DOS_DB_PASSWORD`) puis (re)pose les GRANT dans CHAQUE schéma cabinet
-- existant. Un cabinet créé après le boot est couvert par son provisioning.
--
-- Note MySQL → PostgreSQL : `CREATE USER IF NOT EXISTS` n'existe pas, d'où le
-- bloc DO/pg_roles ci-dessous. Il n'y a pas non plus de notion d'hôte dans le
-- nom du rôle (`'dos_user'@'%'` → `dos_user`), ni de `FLUSH PRIVILEGES` : sous
-- PostgreSQL les privilèges sont effectifs immédiatement.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dos_user') THEN
        -- NOLOGIN tant que le mot de passe n'a pas été posé par l'API : un
        -- rôle sans mot de passe ne doit pas pouvoir ouvrir de session.
        CREATE ROLE dos_user NOLOGIN;
        RAISE NOTICE 'Rôle dos_user créé (sans mot de passe, LOGIN activé au boot de l''API).';
    END IF;
END
$$;


-- ---------------------------------------------------------------------------
-- 3. Droits du rôle applicatif — création des schémas cabinet
-- ---------------------------------------------------------------------------
-- Le provisioning d'un cabinet exécute `CREATE SCHEMA tenant_<uuid>` depuis
-- l'API. Le rôle applicatif doit donc porter CREATE sur la base.
--
-- Dans la configuration Docker par défaut ce rôle est ${POSTGRES_USER}, donc
-- superutilisateur : le GRANT est redondant. On le pose malgré tout, car il
-- documente le privilège minimal requis et rend le script réutilisable tel
-- quel sur une base managée (RDS, Cloud SQL, Scaleway…) où le compte
-- applicatif n'est PAS superutilisateur.
DO $$
BEGIN
    EXECUTE format(
        'GRANT CREATE, CONNECT, TEMPORARY ON DATABASE %I TO %I',
        current_database(), current_user
    );
    -- Le rôle DOS ne peut que se connecter : il ne crée jamais rien.
    EXECUTE format(
        'GRANT CONNECT ON DATABASE %I TO dos_user',
        current_database()
    );
END
$$;

-- L'annuaire appartient au rôle applicatif ; `dos_user` n'y a strictement
-- aucun accès (il ne manipule que des données DOS, jamais le routage).
DO $$
BEGIN
    EXECUTE format('ALTER SCHEMA shared OWNER TO %I', current_user);
    EXECUTE format('GRANT USAGE, CREATE ON SCHEMA shared TO %I', current_user);
END
$$;
REVOKE ALL ON SCHEMA shared FROM PUBLIC;


-- ---------------------------------------------------------------------------
-- 4. Verrouillage du schéma `public`
-- ---------------------------------------------------------------------------
-- Aucune table applicative ne vit dans `public` : tout est soit dans `shared`,
-- soit dans un `tenant_<uuid>`. On retire donc à PUBLIC le droit d'y créer
-- quoi que ce soit, pour qu'une table oubliée hors schéma tenant (donc hors
-- périmètre de sauvegarde par cabinet) soit impossible.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- Empêche tout nouveau rôle d'obtenir implicitement un accès aux futures
-- tables de l'annuaire. Les privilèges sur les schémas cabinet, eux, sont
-- posés explicitement au provisioning et au boot de l'API.
DO $$
BEGIN
    EXECUTE format(
        'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA shared REVOKE ALL ON TABLES FROM PUBLIC',
        current_user
    );
    EXECUTE format(
        'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA shared REVOKE ALL ON SEQUENCES FROM PUBLIC',
        current_user
    );
    EXECUTE format(
        'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC',
        current_user
    );
END
$$;


-- ---------------------------------------------------------------------------
-- 5. Extensions
-- ---------------------------------------------------------------------------
-- Génération d'UUID côté SGBD (utile aux migrations et aux scripts de reprise).
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
