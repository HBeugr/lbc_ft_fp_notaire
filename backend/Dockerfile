# ============================================================================
# API FastAPI — Notaire LBC/FT/FP (SaaS multi-tenant PostgreSQL)
# ============================================================================
FROM python:3.12-slim

WORKDIR /app

# `libpq5` : bibliothèque client PostgreSQL. asyncpg n'en dépend pas pour
# fonctionner, mais elle est requise si un outil d'exploitation (psql, pg_dump)
# est ajouté au conteneur, et par certaines roues natives.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie l'ensemble du backend. Les DEUX environnements Alembic doivent être
# présents dans l'image :
#   - alembic_shared.ini + alembic_shared/  → annuaire, joué par l'entrypoint
#   - alembic.ini        + alembic/         → schémas cabinet, joué à la demande
#     via POST /api/super-admin/tenants/migrate
# Il n'y a pas de .dockerignore : le `COPY . .` ci-dessous les inclut tous.
COPY . .

# Garde-fou de build : une image sans l'environnement Alembic de l'annuaire
# démarrerait puis échouerait au premier appel. Mieux vaut casser le build.
RUN test -f alembic_shared.ini && test -d alembic_shared/versions \
    && test -f alembic.ini && test -d alembic/versions \
    || (echo "ERREUR : environnements Alembic manquants dans l'image" && exit 1)

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

# Migration de l'annuaire puis uvicorn — voir les commentaires détaillés dans
# docker-entrypoint.sh (notamment pourquoi les migrations cabinet en sont
# exclues).
CMD ["/usr/local/bin/docker-entrypoint.sh"]
