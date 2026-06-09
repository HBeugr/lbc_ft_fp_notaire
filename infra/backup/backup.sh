#!/usr/bin/env bash
# Backup MySQL quotidien chiffré AES-256 — rétention 30 jours
set -euo pipefail

DB_HOST="${MYSQL_HOST:-db}"
DB_PORT="${MYSQL_PORT:-3306}"
DB_NAME="${MYSQL_DATABASE:-notaire_lbcft}"
DB_USER="${MYSQL_USER:-notaire_user}"
DB_PASS="${MYSQL_PASSWORD:?Définir MYSQL_PASSWORD}"
AES_KEY="${BACKUP_AES_KEY:?Définir BACKUP_AES_KEY (hex 64 chars)}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS=30

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
DUMP_FILE="${BACKUP_DIR}/notaire_${TIMESTAMP}.sql.gz"
ENC_FILE="${DUMP_FILE}.enc"
CHECKSUM_FILE="${ENC_FILE}.sha256"

mkdir -p "$BACKUP_DIR"

echo "[backup] Démarrage — ${TIMESTAMP}"

mysqldump \
  --host="$DB_HOST" --port="$DB_PORT" \
  --user="$DB_USER" --password="$DB_PASS" \
  --single-transaction --routines --triggers --add-drop-table \
  "$DB_NAME" | gzip -9 > "$DUMP_FILE"

echo "[backup] Dump OK — $(du -sh "$DUMP_FILE" | cut -f1)"

IV=$(openssl rand -hex 16)
openssl enc -aes-256-cbc -K "$AES_KEY" -iv "$IV" -in "$DUMP_FILE" -out "$ENC_FILE"
printf "%s\n" "$IV" | cat - "$ENC_FILE" > "${ENC_FILE}.tmp" && mv "${ENC_FILE}.tmp" "$ENC_FILE"
rm -f "$DUMP_FILE"

echo "[backup] Chiffrement AES-256 OK — $(du -sh "$ENC_FILE" | cut -f1)"

sha256sum "$ENC_FILE" > "$CHECKSUM_FILE"

find "$BACKUP_DIR" -name "notaire_*.sql.gz.enc" -mtime "+${RETENTION_DAYS}" -delete
find "$BACKUP_DIR" -name "notaire_*.sql.gz.enc.sha256" -mtime "+${RETENTION_DAYS}" -delete

KEPT=$(find "$BACKUP_DIR" -name "notaire_*.sql.gz.enc" | wc -l)
echo "[backup] Rétention : ${KEPT} sauvegarde(s) conservée(s) — Terminé"
