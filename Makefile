COMPOSE = docker compose -f docker-compose.yml -f docker-compose.dev.yml

# Alembic exécuté depuis l'hôte : la base est publiée sur 127.0.0.1:5434 par
# docker-compose.dev.yml (5432 est réservé à une éventuelle instance locale).
ALEMBIC_ENV = cd backend && DB_HOST=127.0.0.1 DB_PORT=5434

# Deux environnements Alembic distincts :
#   ALEMBIC_SHARED → schéma `shared`, l'annuaire. Joué UNE fois par déploiement.
#   ALEMBIC        → schémas `tenant_<uuid>`. Rejoué une fois PAR cabinet.
ALEMBIC_SHARED = $(ALEMBIC_ENV) alembic -c alembic_shared.ini
ALEMBIC        = $(ALEMBIC_ENV) alembic -c alembic.ini

# ── Docker ────────────────────────────────────────────────────────────────────
up:
	$(COMPOSE) up -d

up-build:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

restart-api:
	$(COMPOSE) restart api

config:
	$(COMPOSE) config

# ── Base de données ───────────────────────────────────────────────────────────
# Console psql dans le conteneur db
psql:
	$(COMPOSE) exec db psql -U $${DB_USER:-notaire_user} -d $${DB_NAME:-notaire_lbcft}

# Liste les schémas cabinet connus de l'annuaire
tenants:
	$(COMPOSE) exec db psql -U $${DB_USER:-notaire_user} -d $${DB_NAME:-notaire_lbcft} \
		-c "SELECT slug, schema_name, statut FROM shared.tenants ORDER BY slug;"

# Liste les schémas réellement présents dans la base
schemas:
	$(COMPOSE) exec db psql -U $${DB_USER:-notaire_user} -d $${DB_NAME:-notaire_lbcft} \
		-c "SELECT nspname FROM pg_namespace WHERE nspname = 'shared' OR nspname LIKE 'tenant\\_%' ORDER BY nspname;"

# ── Alembic — annuaire (schéma shared) ────────────────────────────────────────
migrate-shared:
	$(ALEMBIC_SHARED) upgrade head

rollback-shared:
	$(ALEMBIC_SHARED) downgrade -1

status-shared:
	$(ALEMBIC_SHARED) current

history-shared:
	$(ALEMBIC_SHARED) history --verbose

new-migration-shared:
	@read -p "Message de migration (annuaire): " msg; $(ALEMBIC_SHARED) revision --autogenerate -m "$$msg"

# ── Alembic — cabinets (schémas tenant_<uuid>) ────────────────────────────────
# Les schémas cabinet ne sont PAS migrés au démarrage de l'API (voir
# backend/docker-entrypoint.sh). On les migre tous en une passe via le service
# de provisioning, qui journalise l'opération dans shared.tenant_audit_log.
# Équivalent HTTP : POST /api/super-admin/tenants/migrate
migrate-tenants:
	$(COMPOSE) exec api python -c "import asyncio; from app.services import tenant_provisioning as t; print(asyncio.run(t.migrate_all_tenants()))"

# Version Alembic de CHAQUE cabinet. Chaque schéma porte sa propre table
# `alembic_version` : on génère donc la requête avant de l'exécuter (psql ne
# sait pas interpoler un nom de schéma dans une requête statique).
status-tenants:
	@$(COMPOSE) exec -T db psql -U $${DB_USER:-notaire_user} -d $${DB_NAME:-notaire_lbcft} -At \
		-c "SELECT format('SELECT %L AS cabinet, version_num FROM %I.alembic_version', schema_name, schema_name) FROM shared.tenants ORDER BY schema_name;" \
	| $(COMPOSE) exec -T db psql -U $${DB_USER:-notaire_user} -d $${DB_NAME:-notaire_lbcft}

new-migration-tenant:
	@read -p "Message de migration (cabinet): " msg; $(ALEMBIC) revision --autogenerate -m "$$msg"

# Migre l'annuaire PUIS tous les cabinets — ordre impératif : une migration
# cabinet peut dépendre d'une entrée d'annuaire, jamais l'inverse.
migrate: migrate-shared migrate-tenants

# Crée le compte Super-Admin d'exploitation (idempotent). Les migrations de
# l'annuaire doivent être jouées avant : `make migrate-shared`.
seed:
	$(COMPOSE) exec api python seed_platform.py

# Idem + un cabinet de démonstration entièrement provisionné. Jamais en production.
seed-demo:
	$(COMPOSE) exec api python seed_platform.py --demo

# ── Sauvegardes ───────────────────────────────────────────────────────────────
# Déclenche une sauvegarde immédiate (dump global + un dump par cabinet)
backup-now:
	$(COMPOSE) exec backup /usr/local/bin/backup.sh

backup-list:
	$(COMPOSE) exec backup ls -lh /backups

# ── Frontend ──────────────────────────────────────────────────────────────────
install-frontend:
	cd frontend && npm install

.PHONY: up up-build down logs ps restart-api config psql tenants schemas \
	migrate migrate-shared rollback-shared status-shared history-shared \
	new-migration-shared migrate-tenants status-tenants new-migration-tenant \
	seed backup-now backup-list install-frontend
