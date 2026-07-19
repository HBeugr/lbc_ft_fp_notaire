#!/usr/bin/env bash
# =============================================================================
# Sauvegarde PostgreSQL quotidienne chiffrée AES-256 — Notaire LBC/FT/FP
# -----------------------------------------------------------------------------
# SPÉCIFICITÉ MULTI-TENANT
#
# La plateforme isole chaque cabinet notarial dans son propre schéma PostgreSQL
# (`tenant_<uuid>`), l'annuaire de routage vivant dans `shared`. Ce script
# produit donc DEUX familles de sauvegardes :
#
#   1. UN DUMP GLOBAL   — toute la base, pour une reprise après sinistre.
#   2. UN DUMP PAR CABINET — `pg_dump -n "<schema>"`, un fichier par cabinet.
#
# Pourquoi le dump par cabinet est indispensable ici : sans lui, restaurer un
# seul cabinet (erreur de manipulation, corruption, demande d'un client)
# obligerait à restaurer la base entière, donc à écraser les données de TOUS
# les autres cabinets. Sur des données LBC/FT — dossiers KYC, alertes,
# déclarations de soupçon — c'est inacceptable : chaque cabinet répond de ses
# propres écritures et ne doit jamais subir la restauration d'un tiers.
# La granularité par schéma permet un `pg_restore -n tenant_xxx` chirurgical.
#
# Format : `pg_dump -Fc` (custom, compressé). C'est le seul format accepté par
# `pg_restore`, qui autorise la restauration sélective (-n schéma, -t table)
# et le réordonnancement des contraintes. Le format SQL brut de l'ancienne
# version MySQL ne le permettait pas.
#
# Chiffrement, hachage et rétention repris à l'identique de la version MySQL :
#   - OpenSSL AES-256-CBC, IV aléatoire préfixé au fichier chiffré
#   - empreinte SHA-256 à côté de chaque archive (contrôle d'intégrité)
#   - rétention 30 jours
#
# ⚠️ La rétention de 30 jours porte sur les SAUVEGARDES, pas sur les données.
# L'obligation d'archivage de 10 ans (Art. 23) est assurée par la base
# elle-même (suppression physique impossible), pas par ce script.
# =============================================================================
set -euo pipefail

# --- Connexion : variables libpq standard, alimentées par docker-compose ------
export PGHOST="${PGHOST:-db}"
export PGPORT="${PGPORT:-5432}"
export PGDATABASE="${PGDATABASE:-notaire_lbcft}"
export PGUSER="${PGUSER:-notaire_user}"
export PGPASSWORD="${PGPASSWORD:?Définir PGPASSWORD (mot de passe DB_PASSWORD)}"

SHARED_SCHEMA="${SHARED_SCHEMA:-shared}"
AES_KEY="${BACKUP_AES_KEY:?Définir BACKUP_AES_KEY (hex, 64 caractères)}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
mkdir -p "$BACKUP_DIR"

echo "[backup] ============================================================"
echo "[backup] Démarrage — ${TIMESTAMP} — base ${PGDATABASE}@${PGHOST}:${PGPORT}"

# -----------------------------------------------------------------------------
# chiffrer <fichier_dump>
#   Chiffre en AES-256-CBC, préfixe l'IV en clair sur la première ligne
#   (nécessaire au déchiffrement, non secret), calcule l'empreinte SHA-256 et
#   supprime le dump en clair. Le fichier en clair ne survit jamais au script.
# -----------------------------------------------------------------------------
chiffrer() {
    local dump_file="$1"
    local enc_file="${dump_file}.enc"
    local iv

    iv=$(openssl rand -hex 16)
    openssl enc -aes-256-cbc -K "$AES_KEY" -iv "$iv" -in "$dump_file" -out "$enc_file"
    printf "%s\n" "$iv" | cat - "$enc_file" > "${enc_file}.tmp" && mv "${enc_file}.tmp" "$enc_file"
    rm -f "$dump_file"

    sha256sum "$enc_file" > "${enc_file}.sha256"
    echo "[backup]   → $(basename "$enc_file") ($(du -sh "$enc_file" | cut -f1))"
}

# -----------------------------------------------------------------------------
# 1. Dump global — reprise après sinistre complète
# -----------------------------------------------------------------------------
GLOBAL_DUMP="${BACKUP_DIR}/notaire_global_${TIMESTAMP}.dump"

echo "[backup] [1/2] Dump global de la base…"
pg_dump --format=custom --compress=9 --no-owner --no-privileges \
        --file="$GLOBAL_DUMP" "$PGDATABASE"
chiffrer "$GLOBAL_DUMP"

# -----------------------------------------------------------------------------
# 2. Un dump par cabinet — restauration chirurgicale
# -----------------------------------------------------------------------------
# Les schémas cabinet sont énumérés depuis l'annuaire `shared.tenants`
# (colonne `schema_name`), et non depuis `information_schema` : l'annuaire est
# la source de vérité, et cela évite de sauvegarder un schéma orphelin laissé
# par un provisioning interrompu.
#
# Tous les cabinets sont sauvegardés, y compris ceux en statut `suspendu` ou
# `archive` : un cabinet archivé reste soumis à la conservation de 10 ans.
echo "[backup] [2/2] Dump par cabinet…"

SCHEMAS=""
if ! SCHEMAS=$(psql --no-align --tuples-only --quiet \
        --command "SELECT schema_name FROM ${SHARED_SCHEMA}.tenants ORDER BY schema_name;" \
        2>/dev/null); then
    # Cas normal au tout premier démarrage : les migrations de l'annuaire
    # n'ont pas encore créé shared.tenants. Le dump global suffit alors.
    echo "[backup]   ⚠ Annuaire ${SHARED_SCHEMA}.tenants introuvable — aucun dump par cabinet."
    SCHEMAS=""
fi

NB_CABINETS=0
if [ -n "$SCHEMAS" ]; then
    while IFS= read -r schema; do
        [ -z "$schema" ] && continue

        # Garde-fou : le nom de schéma est interpolé dans une commande shell.
        # On refuse tout ce qui n'est pas [a-z0-9_] pour écarter toute
        # injection via une ligne d'annuaire corrompue.
        if ! printf '%s' "$schema" | grep -Eq '^[a-zA-Z0-9_]+$'; then
            echo "[backup]   ⚠ Schéma ignoré (nom invalide) : ${schema}"
            continue
        fi

        tenant_dump="${BACKUP_DIR}/notaire_tenant_${schema}_${TIMESTAMP}.dump"
        pg_dump --format=custom --compress=9 --no-owner --no-privileges \
                --schema="$schema" --file="$tenant_dump" "$PGDATABASE"
        chiffrer "$tenant_dump"
        NB_CABINETS=$((NB_CABINETS + 1))
    done <<< "$SCHEMAS"
fi

# L'annuaire lui-même est sauvegardé séparément : sans lui, un dump de cabinet
# restauré serait inexploitable (aucun routage email → cabinet, aucun sel de
# chiffrement, donc données AES illisibles).
SHARED_DUMP="${BACKUP_DIR}/notaire_annuaire_${TIMESTAMP}.dump"
pg_dump --format=custom --compress=9 --no-owner --no-privileges \
        --schema="$SHARED_SCHEMA" --file="$SHARED_DUMP" "$PGDATABASE"
chiffrer "$SHARED_DUMP"

echo "[backup] ${NB_CABINETS} cabinet(s) sauvegardé(s) individuellement + annuaire."

# -----------------------------------------------------------------------------
# 3. Rétention — 30 jours glissants
# -----------------------------------------------------------------------------
find "$BACKUP_DIR" -name "notaire_*.dump.enc"        -mtime "+${RETENTION_DAYS}" -delete
find "$BACKUP_DIR" -name "notaire_*.dump.enc.sha256" -mtime "+${RETENTION_DAYS}" -delete

KEPT=$(find "$BACKUP_DIR" -name "notaire_*.dump.enc" | wc -l)
echo "[backup] Rétention ${RETENTION_DAYS} j : ${KEPT} archive(s) conservée(s)."
echo "[backup] Terminé — ${TIMESTAMP}"
echo "[backup] ============================================================"
