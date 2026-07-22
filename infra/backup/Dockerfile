# ============================================================================
# Service de sauvegarde — Notaire LBC/FT/FP
# ----------------------------------------------------------------------------
# Basé sur l'image PostgreSQL officielle : elle fournit `pg_dump` et `psql`
# dans la MÊME version majeure que le serveur (16). C'est indispensable —
# un `pg_dump` de version inférieure à celle du serveur refuse de s'exécuter.
#
# Contrairement à l'ancienne image `mysql:8.0` (RHEL, `microdnf`),
# `postgres:16` est basée sur Debian : l'installation de cron passe par apt-get.
# ============================================================================
FROM postgres:16

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron openssl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

# Sauvegarde quotidienne à 02h00 UTC.
RUN echo '0 2 * * * . /etc/container_env; /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1' | crontab -

# cron démarre avec un environnement vide : il ne verrait ni PGPASSWORD ni
# BACKUP_AES_KEY, qui sont injectés par Docker Compose dans le PID 1. On les
# fige donc dans /etc/container_env, sourcé par la crontab ci-dessus.
# `cron -f` (Debian) remplace `crond -n` (RHEL).
CMD ["sh", "-c", "export -p > /etc/container_env && touch /var/log/backup.log && cron && tail -f /var/log/backup.log"]
