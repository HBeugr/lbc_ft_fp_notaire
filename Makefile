COMPOSE = docker compose -f docker-compose.yml -f docker-compose.dev.yml
ALEMBIC = cd backend && DB_HOST=127.0.0.1 alembic

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

# ── Alembic ───────────────────────────────────────────────────────────────────
migrate:
	$(ALEMBIC) upgrade head

rollback:
	$(ALEMBIC) downgrade -1

migration-status:
	$(ALEMBIC) current

migration-history:
	$(ALEMBIC) history --verbose

new-migration:
	@read -p "Message de migration: " msg; $(ALEMBIC) revision --autogenerate -m "$$msg"

seed:
	$(COMPOSE) exec api python seed_admin.py

# ── Frontend ──────────────────────────────────────────────────────────────────
install-frontend:
	cd frontend && npm install

.PHONY: up up-build down logs ps restart-api migrate rollback migration-status migration-history new-migration seed install-frontend
