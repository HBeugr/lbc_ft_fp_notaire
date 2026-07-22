# Bascule MySQL → PostgreSQL — procédure de mise en production

**Cible** : déploiement Dokploy sur le VPS.
**Principe directeur** : la suppression de MySQL est la **dernière** étape, jamais
la première. Tant qu'elle n'est pas franchie, chaque étape est réversible.

> Ce document décrit la bascule du déploiement `notairestackdev`. La même
> procédure vaut pour une pile de production, avec une différence de nature :
> les données y seraient de vrais dossiers de conformité, dont la conservation
> 10 ans est obligatoire (Art. 23) et la destruction pénalement sanctionnée
> (Art. 197). Sur `notairestackdev`, il s'agit du jeu d'amorçage augmenté
> d'activité de recette.

---

## 0. Ce qui n'est PAS encore fait

À la date de rédaction :

- **Aucun commit** — 128 fichiers modifiés/ajoutés en attente sur `develop`.
- **Le VPS fait tourner l'ancien code** : `asyncmy 0.2.9`, `DB_PORT=3306`.
- Les variables d'environnement Dokploy sont encore celles de MySQL.

La bascule ne peut donc pas commencer par la suppression de quoi que ce soit.

---

## 1. Sauvegarde préalable — non négociable

```bash
# Dump complet, rapatrié hors du serveur (aucune écriture côté VPS)
ssh vps-lbcft 'sudo docker exec notaire-notairestackdev-6uatgg-db-1 \
  sh -c "mysqldump -uroot -p\$MYSQL_ROOT_PASSWORD --single-transaction \
         --routines --no-tablespaces notaire_lbcft"' \
  | gzip > notaire_mysql_$(date +%Y%m%dT%H%M%S).sql.gz
```

Conserver ce fichier **hors du VPS** et hors du dépôt. C'est le seul filet si la
bascule échoue à une étape irréversible.

Relever également, et conserver au même endroit, la clé de chiffrement de
l'ancienne plateforme — sans elle les colonnes chiffrées sont définitivement
illisibles :

```bash
ssh vps-lbcft 'sudo docker exec notaire-notairestackdev-6uatgg-api-1 printenv AES_KEY'
```

---

## 2. Variables d'environnement Dokploy

À faire **avant** le déploiement, dans l'interface Dokploy. Le code ne peut pas
s'en charger.

| Variable | Valeur | Remarque |
|---|---|---|
| `DB_PORT` | `5432` | était `3306` |
| `DOS_DB_USER` | `dos_user` | **doit différer de `DB_USER`** — l'application refuse de démarrer les privilèges DOS sinon (séparation Art. 12) |
| `DOS_DB_PASSWORD` | *(secret nouveau)* | |
| `TENANT_MASTER_KEY` | *(secret nouveau, 64 car. hex)* | **À NE JAMAIS MODIFIER ensuite** : les clés de chiffrement de chaque cabinet en sont dérivées. La changer rend illisibles les données de tous les cabinets, sauvegardes comprises. |
| `APP_ENV` | `production` | en `development`, l'écho SQL recopie les requêtes **et leurs paramètres** — donc des données clients — dans les journaux, et `/api/docs` est exposé |
| `SHARED_SCHEMA` | `shared` | |
| `TENANT_SCHEMA_PREFIX` | `tenant_` | |

Conserver `AES_KEY` : elle reste utilisée en repli et pour les secrets TOTP.

---

## 3. Isoler le volume de l'ancienne base

Le `docker-compose.yml` déclare le volume `db_data`, **le même nom** que celui
qui porte aujourd'hui les fichiers MySQL. Le sous-répertoire `PGDATA` empêche
l'écrasement — PostgreSQL s'initialiserait à côté — mais faire cohabiter deux
moteurs dans un volume pendant une bascule est une mauvaise idée : on ne sait
plus ce qu'on sauvegarde ni ce qu'on supprime.

**Avant le déploiement**, renommer le volume dans `docker-compose.yml` :

```yaml
    volumes:
      - type: volume
        source: pg_data          # au lieu de db_data
        target: /var/lib/postgresql/data
volumes:
  pg_data:
  # db_data conservé : il porte encore les fichiers MySQL, à supprimer à l'étape 8
```

L'ancien volume reste alors intact et identifiable, et sa suppression devient un
geste explicite.

---

## 4. Déploiement

```bash
git add -A && git commit          # cf. §0 — validation requise
git push origin develop           # Dokploy redéploie automatiquement
```

L'entrypoint joue **seulement** les migrations de l'annuaire (`shared`) :

```
alembic -c alembic_shared.ini upgrade head
```

Les schémas cabinet ne sont pas migrés au démarrage — un boot en N migrations
dépasserait le healthcheck, et un cabinet en échec bloquerait toute la
plateforme. Ils le sont par `POST /api/super-admin/tenants/migrate`.

**Contrôle** : l'API doit répondre `{"status":"ok","env":"production"}` et
`/api/docs` doit renvoyer 404.

---

## 5. Amorcer la plateforme et reprendre les données

```bash
# Compte d'exploitation
docker compose exec api python seed_platform.py

# Reprise — le contrôle préalable refuse de démarrer en cas de collision
# d'adresses, SANS rien écrire.
docker compose exec api python scripts/migrate_mysql_to_tenant.py \
  --nom-cabinet "<nom réel du cabinet>" --slug <slug> \
  --contact-email <contact> --admin-email <admin> \
  --dry-run                      # d'abord à blanc : comparer les volumes
```

Variables attendues par le script : `LEGACY_MYSQL_HOST/PORT/USER/PASSWORD/DATABASE`
et `LEGACY_AES_KEY` (la clé relevée à l'étape 1).

Puis sans `--dry-run`.

---

## 6. Vérification — le point de non-retour

```bash
docker compose exec api python scripts/verifier_reprise.py \
  --slug <slug> --attendu users=N,dossiers=N,kyc_pp=N,...
```

Les volumes attendus se relèvent **sur l'ancienne base avant bascule**.
Rappel : le cabinet compte **un utilisateur de plus** que la source — le compte
administrateur créé par le provisioning.

Puis, et c'est ce qui compte le plus : **faire ouvrir la plateforme par un
utilisateur du cabinet**. Un contrôle automatique valide des volumes et des
types ; seul un humain valide que les dossiers sont les bons.

---

## 7. Fichiers documentaires

Les métadonnées sont reprises, **pas les fichiers**. Ils vivent dans le MinIO
de l'ancien déploiement et doivent être recopiés vers le bucket du cabinet
(`notaire-documents-<slug>`), en conservant les clés d'objet à l'identique —
`documents.minio_key` et `procedure_documents.minio_key` ne sont pas réécrits.

---

## 8. Retrait de MySQL — seulement ici

Conditions **cumulatives** :

- [ ] Étape 6 verte, y compris la recette humaine
- [ ] Fichiers documentaires accessibles depuis la nouvelle plateforme
- [ ] Sauvegarde de l'étape 1 conservée hors du VPS, et **restaurabilité testée**
- [ ] Période d'observation écoulée en conditions réelles d'utilisation

Alors seulement :

```bash
ssh vps-lbcft 'sudo docker rm -f <conteneur-mysql>'
ssh vps-lbcft 'sudo docker volume rm notaire-notairestackdev-6uatgg_db_data'
```

Sur une pile de **production**, ne pas franchir cette étape sans arbitrage écrit :
la conservation des données de conformité est de 10 ans (Art. 23) et leur
destruction constitue une infraction (Art. 197). Conserver la sauvegarde
chiffrée pour toute la durée légale, même après retrait du moteur.

---

## Retour arrière

| Étape atteinte | Comment revenir |
|---|---|
| 1 à 3 | Rien n'a changé |
| 4 (déployé) | Redéployer le commit précédent ; le volume MySQL est intact (§3) |
| 5-6 (données reprises) | Supprimer le cabinet et son schéma, redéployer l'ancien code |
| 8 (MySQL supprimé) | **Uniquement** par restauration de la sauvegarde de l'étape 1 |
