#!/bin/sh
# =============================================================================
# Point d'entrée du conteneur API — Notaire LBC/FT/FP (SaaS multi-tenant)
# -----------------------------------------------------------------------------
# La plateforme a DEUX jeux de migrations Alembic distincts, et un seul est
# joué au démarrage :
#
#   alembic_shared.ini → schéma `shared`   : l'ANNUAIRE (cabinets, routage
#                        email → cabinet, comptes Super-Admin, journal
#                        d'exploitation). Un seul schéma, donc une seule
#                        exécution par déploiement. JOUÉ ICI.
#
#   alembic.ini        → schémas `tenant_<uuid>` : les données MÉTIER LBC/FT
#                        d'un cabinet. Rejoué une fois PAR CABINET.
#                        VOLONTAIREMENT PAS JOUÉ ICI (voir plus bas).
#
# POURQUOI LES MIGRATIONS CABINET NE SONT PAS JOUÉES AU BOOT :
#
#   1. Durée non bornée — avec N cabinets, le boot exécuterait N séries de
#      migrations. Le healthcheck du conteneur expirerait, l'orchestrateur
#      redémarrerait l'API en pleine migration, et une migration interrompue
#      sur des données de conformité est bien pire qu'une migration différée.
#   2. Sinistre en cascade — une migration défaillante sur UN cabinet
#      empêcherait le démarrage de l'API pour TOUS les autres.
#   3. Besoin de traçabilité — la migration d'un schéma cabinet est un acte
#      d'exploitation qui doit être déclenché, horodaté et journalisé
#      nominativement (`shared.tenant_audit_log`).
#
#   Elles sont donc déclenchées explicitement par un Super-Admin, une fois
#   l'API démarrée et saine :
#
#       POST /api/super-admin/tenants/migrate
#
#   Ce point d'entrée applique `alembic upgrade head` à chaque schéma cabinet
#   et retourne le résultat cabinet par cabinet. Un cabinet nouvellement
#   provisionné est, lui, migré directement par son provisioning.
#
#   ⇒ Après tout déploiement porteur d'une migration métier, appeler cet
#     endpoint fait partie de la procédure (voir DEPLOY.md).
# =============================================================================
set -e

echo "[entrypoint] Migration de l'annuaire (schéma shared)…"

# Bloquant et obligatoire : sans annuaire, l'API ne peut router aucune requête
# vers un cabinet. Un échec ici doit arrêter le conteneur (set -e), pas
# démarrer une API dégradée qui répondrait 500 à chaque appel.
#
# Petite tolérance au démarrage : docker-compose attend déjà `pg_isready` via
# `depends_on: service_healthy`, mais PostgreSQL peut encore refuser les
# connexions quelques instants après (rejeu WAL). On retente brièvement plutôt
# que de faire échouer le déploiement sur une course au démarrage.
ATTEMPT=1
MAX_ATTEMPTS=10
until alembic -c alembic_shared.ini upgrade head; do
    if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
        echo "[entrypoint] ÉCHEC : migration de l'annuaire impossible après ${MAX_ATTEMPTS} tentatives."
        exit 1
    fi
    echo "[entrypoint] Base indisponible — nouvelle tentative ${ATTEMPT}/${MAX_ATTEMPTS} dans 3 s…"
    ATTEMPT=$((ATTEMPT + 1))
    sleep 3
done

echo "[entrypoint] Annuaire à jour."
echo "[entrypoint] Migrations cabinet : NON jouées au boot."
echo "[entrypoint]   → déclencher POST /api/super-admin/tenants/migrate après déploiement."
echo "[entrypoint] Démarrage d'uvicorn…"

# `exec` : uvicorn devient PID 1 et reçoit directement SIGTERM, ce qui permet
# un arrêt propre (fermeture des connexions en cours) au lieu d'un SIGKILL.
exec uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8000}"
